import os, uuid, json
from flask import Flask, request, jsonify, send_from_directory
from build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)

@app.route('/')
def index():
    return "APK Builder Backend - POST /api/build to start a build"

@app.route('/api/build', methods=['POST'])
def build():
    # Accept form fields and files
    data = request.form.to_dict()
    icon = request.files.get('icon')
    gs = request.files.get('google_services') or request.files.get('google-services') or request.files.get('google-services.json')
    task_id = str(uuid.uuid4())
    workdir = os.path.join('/tmp/build_tasks', task_id)
    os.makedirs(workdir, exist_ok=True)
    # Save uploaded files
    if icon:
        icon.save(os.path.join(workdir, 'icon.png'))
    if gs:
        gs.save(os.path.join(workdir, 'google-services.json'))
    # Save metadata
    meta = {'id': task_id, 'params': data, 'workdir': workdir}
    with open(os.path.join(workdir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    # Enqueue build
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
        return jsonify({'status': 'error', 'message': open(errf,encoding="utf-8").read()})
    return jsonify({'status': 'pending'})

@app.route('/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(TASK_OUTPUT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs('/home/project/output', exist_ok=True)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

