import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory, render_template_string

# relative import (CRITICAL for gunicorn backend.app:app)
from .build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)

# simple homepage
@app.route("/")
def index():
    return "<h1>APK Builder Backend Running</h1>"

# build API (protected by API_KEY)
@app.route("/api/build", methods=["POST"])
def api_build():
    api_key = request.headers.get("X-API-Key")
    required_key = os.environ.get("API_KEY")

    if required_key and api_key != required_key:
        return jsonify({"error": "Invalid API Key"}), 401

    data = request.json or {}

    task_id = enqueue_build_task(data)
    return jsonify({"task_id": task_id, "status": "queued"}), 202

# status API
@app.route("/api/status/<task_id>", methods=["GET"])
def api_status(task_id):
    status_file = os.path.join(TASK_OUTPUT_DIR, f"{task_id}/status.json")
    if not os.path.exists(status_file):
        return jsonify({"error": "task not found"}), 404

    with open(status_file, "r") as f:
        status = json.load(f)
    return jsonify(status)

# download APK
@app.route("/api/download/<task_id>", methods=["GET"])
def api_download(task_id):
    task_dir = os.path.join(TASK_OUTPUT_DIR, task_id)
    apk_path = os.path.join(task_dir, "output.apk")

    if not os.path.exists(apk_path):
        return jsonify({"error": "apk not ready"}), 404

    return send_from_directory(task_dir, "output.apk", as_attachment=True)


# entry point (not used by gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
