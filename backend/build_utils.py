# backend/build_utils.py
import os
import json
import uuid
import time
import requests
from pathlib import Path

# =========================
# 基础目录
# =========================
TASK_BASE_DIR = "/tmp/build_tasks"
TASK_OUTPUT_DIR = "/home/project/output"

os.makedirs(TASK_BASE_DIR, exist_ok=True)
os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)

# =========================
# 工具函数
# =========================
def _task_dir(task_id: str) -> str:
    return os.path.join(TASK_BASE_DIR, task_id)

def _status_file(task_id: str) -> str:
    return os.path.join(_task_dir(task_id), "status.json")

def _write_status(task_id: str, status: str, extra: dict | None = None):
    data = {
        "task_id": task_id,
        "status": status,
        "updated_at": int(time.time())
    }
    if extra:
        data.update(extra)

    Path(_task_dir(task_id)).mkdir(parents=True, exist_ok=True)
    with open(_status_file(task_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================
# GitHub Actions 触发器
# =========================
def trigger_github_action(task_id: str, params: dict):
    """
    触发 GitHub Actions workflow_dispatch
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPO")  # fortune2422/apk_builder_template
    workflow_file = os.environ.get("GITHUB_WORKFLOW", "build-apk.yml")
    branch = os.environ.get("GITHUB_BRANCH", "main")

    if not github_token or not github_repo:
        raise RuntimeError("GITHUB_TOKEN or GITHUB_REPO not set")

    url = f"https://api.github.com/repos/{github_repo}/actions/workflows/{workflow_file}/dispatches"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "ref": branch,
        "inputs": {
            "task_id": task_id,
            **params
        }
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"Trigger workflow failed: {r.status_code} {r.text}")

# =========================
# 对外主入口
# =========================
def enqueue_build_task(params: dict) -> str:
    """
    创建任务 + 触发 GitHub Actions
    """
    task_id = str(uuid.uuid4())

    print(f"[ENQUEUE] Create task {task_id}", flush=True)
    _write_status(task_id, "queued")

    try:
        trigger_github_action(task_id, params)
        _write_status(task_id, "running")
        print(f"[ENQUEUE] GitHub Action triggered for {task_id}", flush=True)
    except Exception as e:
        _write_status(task_id, "failed", {"error": str(e)})
        print(f"[ERROR] Trigger action failed: {e}", flush=True)

    return task_id
