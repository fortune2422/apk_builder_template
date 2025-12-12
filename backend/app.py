import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory, render_template_string

# 相对导入，保证 gunicorn backend.app:app 时能找到 build_utils
from .build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>APK Builder Backend Running</h1>"

# 浏览器测试表单（保留方便调试）
@app.route("/api/build", methods=["GET", "POST"])
def build_route():
    if request.method == "GET":
        return render_template_string("""
            <h2>Test build (POST)</h2>
            <form method="post" enctype="multipart/form-data">
              <label>H5 URL: <input name="h5_url" value="https://example.com" style="width:400px"></label><br><br>
              <label>App name: <input name="app_name" value="测试App"></label><br><br>
              <label>Package name: <input name="package_name" value="com.example.test"></label><br><br>
              <label>Icon file: <input type="file" name="icon"></label><br><br>
              <label>google-services.json: <input type="file" name="google_services"></label><br><br>
              <label>API Key (如果启用): <input name="api_key"></label><br><br>
              <button type="submit">Submit</button>
            </form>
            <p>提交后会返回 task_id，可在 /api/status/&lt;task_id&gt; 查看状态。</p>
        """)

    # POST - 创建任务
    api_key_expected = os.environ.get("API_KEY")
    if api_key_expected:
        provided = request.headers.get("X-API-KEY") or request.form.get("api_key") or request.args.get("api_key")
        if not provided or provided != api_key_expected:
            return jsonify({"error": "Unauthorized - invalid API key"}), 401

    # 读取表单字段 & 文件
    params = {}
    params.update(request.form.to_dict())
    # for JSON clients
    if request.is_json:
        params.update(request.get_json())

    icon = request.files.get("icon")
    gs = (request.files.get("google_services") or request.files.get("google-services") or request.files.get("google-services.json"))

    # 生成 task_id，准备工作目录
    task_id = str(uuid.uuid4())
    workdir = os.path.join("/tmp/build_tasks", task_id)
    os.makedirs(workdir, exist_ok=True)

    # 保存上传文件到 workdir（若有）
    if icon:
        icon_path = os.path.join(workdir, "icon.png")
        icon.save(icon_path)
        params['icon_path'] = icon_path

    if gs:
        gs_path = os.path.join(workdir, "google-services.json")
        gs.save(gs_path)
        params['google_services'] = gs_path

    # 构造 meta 并写入
    meta = {"id": task_id, "params": params, "workdir": workdir}
    meta_path = os.path.join(workdir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    # 把 meta 传给 enqueue_build_task（该函数会启动后台线程）
    enqueue_build_task(meta)

    return jsonify({"task_id": task_id}), 202


# 查询构建状态
@app.route("/api/status/<task_id>", methods=["GET"])
def status(task_id):
    workdir = os.path.join("/tmp/build_tasks", task_id)

    # 优先读取 output_url.txt（如果 GitHub 上传成功）
    outurl = os.path.join(workdir, "output_url.txt")
    if os.path.exists(outurl):
        try:
            url = open(outurl, encoding="utf-8").read().strip()
            return jsonify({"status": "done", "apk_url": url})
        except:
            pass

    # 本地 APK（临时）
    apk_local = os.path.join("/home/project/output", f"{task_id}.apk")
    if os.path.exists(apk_local):
        return jsonify({"status": "done", "apk_url": f"/output/{task_id}.apk",
                        "note": "Local file is ephemeral on Render. Use GitHub upload for persistence."})

    # 错误日志
    errf = os.path.join(workdir, "error.txt")
    if os.path.exists(errf):
        msg = open(errf, encoding="utf-8").read()
        return jsonify({"status": "error", "message": msg})

    # 若都没有，则认为仍在排队/进行中
    return jsonify({"status": "pending"})


# 提供本地 APK 下载（Render 容器内临时文件）
@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory("/home/project/output", filename, as_attachment=True)


if __name__ == "__main__":
    # 本地 dev 用，Render 会用 gunicorn 启动
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
