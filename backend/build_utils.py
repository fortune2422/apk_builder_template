import os
import shutil
import subprocess
import threading
import json
import traceback
import time
from pathlib import Path

import requests  # optional: for GitHub upload

ROOT = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(ROOT, '..', 'template')
TASK_OUTPUT_DIR = '/home/project/output'
os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)

# -----------------------
# Build concurrency control
# -----------------------
try:
    MAX_CONCURRENT_BUILDS = int(os.environ.get('MAX_CONCURRENT_BUILDS', '1'))
except Exception:
    MAX_CONCURRENT_BUILDS = 1
_build_semaphore = threading.Semaphore(MAX_CONCURRENT_BUILDS)


# -----------------------
# Helpers
# -----------------------
def write_status(workdir, status, extra=None):
    """Write task status.json"""
    s = {"status": status}
    if extra:
        s.update(extra)
    with open(os.path.join(workdir, "status.json"), "w", encoding="utf-8") as f:
        json.dump(s, f)
    print(f"[STATUS] {workdir}: {s}", flush=True)


def enqueue_build_task(task_meta):
    """Start build in background thread."""
    tid = task_meta.get("id")
    print(f"[ENQUEUE] Task enqueue: {tid}", flush=True)
    t = threading.Thread(target=process_build, args=(task_meta,))
    t.daemon = True
    t.start()
    print(f"[ENQUEUE] Thread started for {tid}", flush=True)
    return tid


# -----------------------
# Main Build Logic
# -----------------------
def process_build(task_meta):
    tid = task_meta["id"]
    workdir = task_meta["workdir"]
    params = task_meta.get("params", {})

    print(f"[{tid}] Build thread started. workdir={workdir}", flush=True)
    write_status(workdir, "running")

    lock_acquired = False

    try:
        # -----------------------
        # Acquire semaphore
        # -----------------------
        _build_semaphore.acquire()
        lock_acquired = True
        print(f"[{tid}] Semaphore acquired", flush=True)

        # -----------------------
        # Prepare directories
        # -----------------------
        build_dir = os.path.join(workdir, 'project')

        if not os.path.exists(TEMPLATE_DIR):
            raise FileNotFoundError(f"TEMPLATE_DIR missing: {TEMPLATE_DIR}")

        # Clean stale build
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

        print(f"[{tid}] Copying template...", flush=True)
        shutil.copytree(TEMPLATE_DIR, build_dir)
        print(f"[{tid}] Template copied.", flush=True)

        # -----------------------
        # Apply replacements
        # -----------------------
        try:
            from scripts.replace_vars import apply_replacements
            apply_replacements(build_dir, params, workdir)
            print(f"[{tid}] apply_replacements OK", flush=True)
        except Exception as e:
            w = os.path.join(workdir, "replace_warning.txt")
            with open(w, "w", encoding="utf-8") as f:
                f.write(str(e) + "\n")
                f.write(traceback.format_exc())
            print(f"[{tid}] WARNING in replacements: {e}", flush=True)

        # -----------------------
        # google-services.json (optional)
        # -----------------------
        gs_src = os.path.join(workdir, "google-services.json")
        if os.path.exists(gs_src):
            dst = os.path.join(build_dir, "app", "google-services.json")
            shutil.copy(gs_src, dst)
            print(f"[{tid}] google-services.json copied", flush=True)

        # -----------------------
        # Gradle Setup
        # -----------------------
        gradlew = os.path.join(build_dir, "gradlew")
        if not os.path.exists(gradlew):
            raise FileNotFoundError("gradlew not found in template")

        os.chmod(gradlew, 0o755)

        env = os.environ.copy()
        env["ANDROID_SDK_ROOT"] = env.get("ANDROID_SDK_ROOT", "/opt/android-sdk")
        env["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"

        # -----------------------
        # Run gradlew
        # -----------------------
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"[{tid}] Running gradlew attempt {attempt}", flush=True)
                subprocess.check_call([gradlew, "clean", "assembleRelease"], cwd=build_dir, env=env)
                print(f"[{tid}] Gradle success", flush=True)
                break
            except subprocess.CalledProcessError as cpe:
                # real gradle error
                efile = os.path.join(workdir, "error.txt")
                with open(efile, "w", encoding="utf-8") as f:
                    f.write("Gradle failed:\n")
                    f.write(str(cpe) + "\n")
                    f.write(traceback.format_exc())
                print(f"[{tid}] Gradle failed. See error.txt", flush=True)
                write_status(workdir, "failed")
                return
            except Exception as ose:
                # file descriptor error / temp FS problem
                print(f"[{tid}] OSError attempt {attempt}: {ose}", flush=True)
                time.sleep(1 + attempt)
        else:
            efile = os.path.join(workdir, "error.txt")
            with open(efile, "a", encoding="utf-8") as f:
                f.write("Repeated gradle OSError\n")
            print(f"[{tid}] Gradle failed permanently", flush=True)
            write_status(workdir, "failed")
            return

        # -----------------------
        # Locate APK
        # -----------------------
        release_dir = os.path.join(build_dir, "app", "build", "outputs", "apk", "release")
        apk_file = None
        for p in Path(release_dir).glob("*.apk"):
            apk_file = str(p)
            break

        if not apk_file:
            raise FileNotFoundError("APK not produced!")

        out_apk = os.path.join(TASK_OUTPUT_DIR, f"{tid}.apk")
        shutil.copy(apk_file, out_apk)

        print(f"[{tid}] APK copied to {out_apk}", flush=True)

        # -----------------------
        # Optional: GitHub upload
        # -----------------------
        github_token = os.environ.get("GITHUB_TOKEN")
        github_repo = os.environ.get("GITHUB_REPO")

        if github_token and github_repo:
            try:
                url = upload_apk_to_github(out_apk, github_repo, github_token)
                with open(os.path.join(workdir, "output_url.txt"), "w", encoding="utf-8") as f:
                    f.write(url)
                print(f"[{tid}] Uploaded to GitHub: {url}", flush=True)
            except Exception as e:
                print(f"[{tid}] GitHub upload failed: {e}", flush=True)

        write_status(workdir, "done", {"apk": out_apk})
        print(f"[{tid}] Build finished successfully", flush=True)

    except Exception as e:
        # -----------------------
        # General handler
        # -----------------------
        print(f"[{tid}] Fatal exception: {e}", flush=True)
        efile = os.path.join(workdir, "error.txt")
        with open(efile, "w", encoding="utf-8") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
        write_status(workdir, "failed")

    finally:
        if lock_acquired:
            _build_semaphore.release()
        print(f"[{tid}] Thread ended", flush=True)


# -----------------------
# GitHub release uploader
# -----------------------
def upload_apk_to_github(apk_path, repo_full, token, tag_name=None):
    """Upload APK to GitHub Releases."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    if not tag_name:
        tag_name = f"auto-build-{int(time.time())}"

    owner, repo = repo_full.split("/", 1)

    # Create release
    create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    body = {"tag_name": tag_name, "name": tag_name, "draft": False, "prerelease": False}

    r = requests.post(create_url, json=body, headers=headers)
    if r.status_code >= 300:
        raise RuntimeError(f"Failed to create release: {r.text}")

    release = r.json()
    upload_url = release["upload_url"].split("{")[0] + f"?name={os.path.basename(apk_path)}"

    # Upload file
    with open(apk_path, "rb") as fh:
        data = fh.read()

    upload_headers = dict(headers)
    upload_headers["Content-Type"] = "application/vnd.android.package-archive"

    r2 = requests.post(upload_url, data=data, headers=upload_headers)
    if r2.status_code >= 300:
        raise RuntimeError(f"Upload failed: {r2.text}")

    asset = r2.json()
    return asset["browser_download_url"]
