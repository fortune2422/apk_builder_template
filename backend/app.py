# 诊断版 app.py — 用于查清导入/路径问题
import os
import sys
import uuid
import json
import traceback
from flask import Flask, request, jsonify, send_from_directory, render_template_string

# --- diagnostic prints to logs (so we can see what the worker sees) ---
print("===== STARTUP DIAGNOSTICS for backend.app =====")
try:
    print("cwd:", os.getcwd())
    print("__file__:", __file__)
except Exception as e:
    print("cwd/__file__ print failed:", e)
print("sys.executable:", sys.executable)
print("sys.path:")
for p in sys.path:
    print("  ", p)

# show backend dir listing if available
try:
    backend_dir = os.path.join(os.path.dirname(__file__))
    print("backend_dir:", backend_dir)
    if os.path.exists(backend_dir):
        print("backend listing:")
        for name in sorted(os.listdir(backend_dir)):
            print("   -", name)
    else:
        print("backend_dir does not exist.")
except Exception as e:
    print("Failed to list backend dir:", e)

# Try relative import first (correct for package), fallback to absolute import (for debug)
enqueue_build_task = None
TASK_OUTPUT_DIR = "/home/project/output"  # default, may be overwritten by module
_import_error = None
try:
    # Attempt relative import
    from .build_utils import enqueue_build_task as _ebt, TASK_OUTPUT_DIR as _tod
    enqueue_build_task = _ebt
    TASK_OUTPUT_DIR = _tod
    print("Imported .build_utils successfully (relative import).")
except Exception as e_rel:
    _import_error = e_rel
    print("Relative import failed:", repr(e_rel))
    try:
        # Attempt absolute import (should NOT be needed if package import used)
        from build_utils import enqueue_build_task as _ebt2, TASK_OUTPUT_DIR as _tod2
        enqueue_build_task = _ebt2
        TASK_OUTPUT_DIR = _tod2
        print("Imported build_utils as top-level module SUCCESSFULLY (absolute import).")
    except Exception as e_abs:
        print("Absolute import also failed:", repr(e_abs))
        print("Traceback (relative import):")
        traceback.print_exc()
        print("Traceback (absolute import):")
        traceback.print_exc()

print("enqueue_build_task is", "set" if enqueue_build_task else "NOT set")
print("TASK_OUTPUT_DIR:", TASK_OUTPUT_DIR)
print("===== END STARTUP DIAGNOSTICS =====")

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>APK Builder Backend (diagnostic) Running</h1>"

@app.route("/api/build", methods=["GET", "POST"])
def build_route():
    # minimal create-task wrapper (will only queue if enqueue_build_task available)
    if request.method == "GET":
        return render_template_string("<p>Diagnostic build endpoint. POST to create a task.</p>")
    data = request.get_json(force=False, silent=True) or request.form.to_dict() or {}
    task_id = str(uuid.uuid4())
    workdir = os.path.join("/tmp/build_tasks", task_id)
    os.makedirs(workdir, exist_ok=True)
    meta = {"id": task_id, "workdir": workdir, "params": data}
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    if enqueue_build_task:
        try:
            enqueue_build_task(meta)
            return jsonify({"task_id": task_id, "status": "queued"}), 202
        except Exception as e:
            return jsonify({"error": "enqueue failed", "detail": str(e), "trace": traceback.format_exc()}), 500
    else:
        return jsonify({"task_id": task_id, "status": "not queued", "reason": "enqueue_build_task not available", "import_error": repr(_import_error)}), 500

@app.route("/api/status/<task_id>", methods=["GET"])
def status(task_id):
    workdir = os.path.join("/tmp/build_tasks", task_id)
    errf = os.path.join(workdir, "error.txt")
    outurl = os.path.join(workdir, "output_url.txt")
    apk_local = os.path.join("/home/project/output", f"{task_id}.apk")
    if os.path.exists(outurl):
        return jsonify({"status": "done", "apk_url": open(outurl, encoding="utf-8").read().strip()})
    if os.path.exists(apk_local):
        return jsonify({"status": "done", "apk_url": f"/output/{task_id}.apk"})
    if os.path.exists(errf):
        return jsonify({"status": "error", "message": open(errf, encoding="utf-8").read()})
    return jsonify({"status": "pending"})

@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory("/home/project/output", filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
