# backend/app.py
import os
import json
import uuid
from flask import Flask, request, jsonify, redirect

from .build_utils import enqueue_build_task, TASK_OUTPUT_DIR

app = Flask(__name__)

# =========================
# 首页
# =========================
@app.route("/")
def index():
    return "<h2>APK Builder Backend (GitHub Actions Mode)</h2>"

# =========================
# 创建构建任务
# =========================
@app.route("/api/build", methods=["POST"])
def api_build():
    api_key = request.headers.get("X-API-Key")
    required_key = os.environ.get("API_KEY")

    if required_key and api_key != required_key:
        return jsonify({"error": "Invalid API Key"}), 401

    data = request.json or {}

    # 你可以按需校验字段
    required_fields = ["h5_url", "app_name", "package_name"]
    for f in required_fields:
        if f not in data:
            return jsonify({"error": f"Missing field: {f}"}), 400

    task_id = enqueue_build_task({
        "h5_url": data["h5_url"],
        "app_name": data["app_name"],
        "package_name": data["package_name"],
    })

    return jsonify({
        "task_id": task_id,
        "status": "queued"
    }), 202

# =========================
# 查询状态
# =========================
@app.route("/api/status/<task_id>", methods=["GET"])
def api_status(task_id):
    status_file = f"/tmp/build_tasks/{task_id}/status.json"

    if not os.path.exists(status_file):
        return jsonify({"error": "task not found"}), 404

    with open(status_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

# =========================
# 下载 APK（跳 GitHub Release）
# =========================
@app.route("/api/download/<task_id>", methods=["GET"])
def api_download(task_id):
    github_repo = os.environ.get("GITHUB_REPO")
    if not github_repo:
        return jsonify({"error": "GITHUB_REPO not set"}), 500

    url = f"https://github.com/{github_repo}/releases/tag/{task_id}"
    return redirect(url, code=302)

# =========================
# 本地调试入口（Render 不用）
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
