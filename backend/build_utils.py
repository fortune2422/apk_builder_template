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
