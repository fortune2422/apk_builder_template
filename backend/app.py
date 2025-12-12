import os, uuid, json
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)

@app.route('/')
def index():
    return "APK Builder Backend - POST /api/build to start a build"

@app.route('/api/build', methods=['GET', 'POST'])
def build():
    # 如果是 GET，返回一个简洁的 HTML 表单，方便在浏览器直接测试
    if request.method == 'GET':
        return render_template_string("""
            <!doctype html>
            <html>
            <head><meta charset="utf-8"><title>Test /api/build</title></head>
            <body>
              <h2>Test build (POST)</h2>
              <form method="post" enctype="multipart/form-data">
                <label>H5 URL: <input name="h5_url" value="https://example.com" style="width:400px"></label><br><br>
                <label>App name: <input name="app_name" value="测试App"></label><br><br>
                <label>Package name: <input name="package_name" value="com.example.test"></label><br><br>
                <label>Adjust App Token: <input name="adjust_app_token"></label><br><br>
                <label>Icon file: <input type="file" name="icon"></label><br><br>
                <label>google-services.json: <input type="file" name="google_services"></label><br><br>
                <button type="submit">Submit</button>
              </form>
              <p>提交后会返回一个 <code>task_id</code>，可在 <code>/api/status/&lt;task_id&gt;</code> 查看状态。</p>
            </body>
            </html>
        """)
    # POST 走原有逻辑：接受表单和文件，写入临时工作目录并入队构建
    data = request.form.to_dict()
    icon = request.files.get('icon')
    gs = request.files.get('google_services') or request.files.get('google-services') or request.files.get('google-services.json')
    task_id = str(uuid.uuid4())
    workdir = os.path.join('/tmp/build_tasks', task_id)
    os.makedirs(workdir, exist_ok=True)
    # Save uploaded files
    if icon:
        icon_path = os.path.join(workdir, 'icon.png')
        icon.save(icon_path)
    if gs:
        gs_path = os.path.join(workdir, 'google-services.json')
        gs.save(gs_path)
    # Save metadata
    meta = {'id': task_id, 'params': data, 'workdir': workdir}
    with open(os.path.join(workdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    # Enqueue build (this will run in background thread in our current template)
    enqueue_build_task(meta)
    return jsonify({'task_id': task_id}), 202

@app.route('/api/status/<task_id>', methods=['GET'])
def status(task_id):
    # Very simple status: check if output APK exists
    apk_path = os.path.join(TASK_OUTPUT_DIR, f'{task_id}.apk')
    if os.path.exists(apk_path):
        return jsonify({'status': 'done', 'apk_url': f'/output/{task_id}.apk'})
    # Or check for error file
    errf = os.path.join('/tmp/build_tasks', task_id, 'error.txt')
    if os.path.exists(errf):
        try:
            with open(errf, encoding='utf-8') as fh:
                msg = fh.read()
        except Exception:
            msg = "Could not read error file."
        return jsonify({'status': 'error', 'message': msg})
    return jsonify({'status': 'pending'})

@app.route('/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(TASK_OUTPUT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs('/home/project/output', exist_ok=True)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
