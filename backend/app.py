import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from .build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)


@app.route('/')
def index():
    return "APK Builder Backend - POST /api/build to start a build"


# ---------------------------------------------------------
# GET: 返回浏览器可直接使用的表单
# POST: 创建构建任务
# ---------------------------------------------------------
@app.route('/api/build', methods=['GET', 'POST'])
def build():
    # ---------- GET：返回 HTML 表单 ----------
    if request.method == 'GET':
        return render_template_string("""
            <!doctype html>
            <html>
            <head><meta charset="utf-8"><title>Test build (POST)</title></head>
            <body>
              <h2>Test build (POST)</h2>

              <form method="post" enctype="multipart/form-data">
                <label>API Key (可选，但生产环境必须): 
                    <input name="api_key"></label><br><br>

                <label>H5 URL: 
                    <input name="h5_url" value="https://example.com" style="width:400px"></label><br><br>

                <label>App name: <input name="app_name" value="测试App"></label><br><br>

                <label>Package name: <input name="package_name" value="com.example.test"></label><br><br>

                <label>Adjust App Token: <input name="adjust_app_token"></label><br><br>

                <label>Icon file: <input type="file" name="icon"></label><br><br>

                <label>google-services.json: <input type="file" name="google_services"></label><br><br>

                <button type="submit">Submit</button>
              </form>

              <p>提交后会返回 task_id，可在 <code>/api/status/&lt;task_id&gt;</code> 查看状态。</p>
            </body>
            </html>
        """)

    # ---------- POST：构建 API ----------
    # 1) API-Key 校验
    api_key_expected = os.environ.get("API_KEY")
    if api_key_expected:
        provided = (
            request.headers.get("X-API-KEY")
            or request.form.get("api_key")
            or request.args.get("api_key")
        )
        if not provided or provided != api_key_expected:
            return jsonify({"error": "Unauthorized - invalid API key"}), 401

    # 2) 接收参数与文件
    data = request.form.to_dict()
    icon = request.files.get("icon")
    gs = (
        request.files.get("google_services")
        or request.files.get("google-services")
        or request.files.get("google-services.json")
    )

    # 3) 创建 task_id + 工作目录
    task_id = str(uuid.uuid4())
    workdir = os.path.join("/tmp/build_tasks", task_id)
    os.makedirs(workdir, exist_ok=True)

    # 4) 保存上传文件
    if icon:
        icon_path = os.path.join(workdir, "icon.png")
        icon.save(icon_path)

    if gs:
        gs_path = os.path.join(workdir, "google-services.json")
        gs.save(gs_path)

    # 5) 保存元数据
    meta = {"id": task_id, "params": data, "workdir": workdir}
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)

    # 6) 进入后台线程构建
    enqueue_build_task(meta)

    return jsonify({"task_id": task_id}), 202


# ---------------------------------------------------------
# 查询构建状态
# ---------------------------------------------------------
@app.route('/api/status/<task_id>', methods=['GET'])
def status(task_id):
    workdir = os.path.join("/tmp/build_tasks", task_id)

    # 优先读取 GitHub 上传后的 URL
    output_url = os.path.join(workdir, "output_url.txt")
    if os.path.exists(output_url):
        try:
            url = open(output_url, encoding="utf-8").read().strip()
            return jsonify({"status": "done", "apk_url": url})
        except:
            pass

    # 读取本地 APK（仅 Render 容器里存在）
    apk_path = os.path.join(TASK_OUTPUT_DIR, f"{task_id}.apk")
    if os.path.exists(apk_path):
        return jsonify(
            {
                "status": "done",
                "apk_url": f"/output/{task_id}.apk",
                "note": "This URL is temporary because Render disk is ephemeral. GitHub upload is recommended."
            }
        )

    # 读取错误文件
    err_file = os.path.join(workdir, "error.txt")
    if os.path.exists(err_file):
        try:
            msg = open(err_file, encoding="utf-8").read()
        except:
            msg = "Error occurred, but log unreadable."
        return jsonify({"status": "error", "message": msg})

    return jsonify({"status": "pending"})


# ---------------------------------------------------------
# 提供本地 APK 下载
# --------------------------------------------------------
@app.route('/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(TASK_OUTPUT_DIR, filename, as_attachment=True)


# ---------------------------------------------------------
# 启动 Flask（Render 会自动设置 PORT）
# ---------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
