import os
import shutil
import subprocess
import threading
import json
import traceback
import time
from pathlib import Path

# Optional network upload
import requests

# Configuration
ROOT = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(ROOT, '..', 'template')
TASK_OUTPUT_DIR = '/home/project/output'
os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)

# Concurrency control: limit number of simultaneous builds
try:
    MAX_CONCURRENT_BUILDS = int(os.environ.get('MAX_CONCURRENT_BUILDS', '1'))
except Exception:
    MAX_CONCURRENT_BUILDS = 1
_build_semaphore = threading.Semaphore(MAX_CONCURRENT_BUILDS)

def enqueue_build_task(task_meta):
    """
    Start a background thread to process the build.
    Uses a semaphore to limit concurrent builds.
    """
    t = threading.Thread(target=process_build, args=(task_meta,))
    t.daemon = True
    t.start()

def process_build(task_meta):
    tid = task_meta['id']
    workdir = task_meta['workdir']
    params = task_meta.get('params', {})
    lock_acquired = False
    try:
        # Acquire semaphore (may block until a slot is free)
        _build_semaphore.acquire()
        lock_acquired = True
        print(f"[{tid}] Starting build, workspace: {workdir}")

        build_dir = os.path.join(workdir, 'project')
        # Copy template project into working directory
        if not os.path.exists(TEMPLATE_DIR):
            raise FileNotFoundError(f"TEMPLATE_DIR not found: {TEMPLATE_DIR}")
        shutil.copytree(TEMPLATE_DIR, build_dir)

        # Apply replacements (assumes scripts.replace_vars.apply_replacements exists)
        try:
            from scripts.replace_vars import apply_replacements
            apply_replacements(build_dir, params, workdir)
        except Exception as e:
            print(f"[{tid}] Warning: apply_replacements failed: {e}")

        # copy google-services.json if provided
        gs_src = os.path.join(workdir, 'google-services.json')
        if os.path.exists(gs_src):
            dst = os.path.join(build_dir, 'app', 'google-services.json')
            try:
                shutil.copy(gs_src, dst)
                print(f"[{tid}] Copied google-services.json to project.")
            except Exception as e:
                print(f"[{tid}] Failed to copy google-services.json: {e}")

        # Prepare gradlew
        gradlew = os.path.join(build_dir, 'gradlew')
        if not os.path.exists(gradlew):
            raise FileNotFoundError('gradlew not found in template project. Make sure template includes gradlew.')
        os.chmod(gradlew, 0o755)

        env = os.environ.copy()
        if 'ANDROID_SDK_ROOT' not in env:
            env['ANDROID_SDK_ROOT'] = '/opt/android-sdk'
        if 'JAVA_HOME' not in env:
            # common location in our Dockerfile; adjust if necessary
            env['JAVA_HOME'] = '/usr/lib/jvm/java-11-openjdk-amd64' if os.path.exists('/usr/lib/jvm/java-11-openjdk-amd64') else env.get('JAVA_HOME','')

        # Run Gradle assembleRelease
        print(f"[{tid}] Running gradle assembleRelease...")
        try:
            subprocess.check_call([gradlew, 'clean', 'assembleRelease'], cwd=build_dir, env=env, stdout=subprocess.STDOUT, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # capture gradle error
            errf = os.path.join(workdir, 'error.txt')
            with open(errf, 'w', encoding='utf-8') as f:
                f.write("Gradle build failed:\n")
                f.write(str(e) + "\n")
                f.write(traceback.format_exc())
            print(f"[{tid}] Gradle build failed. See {errf}")
            return

        # find the produced apk
        apk_src_dir = os.path.join(build_dir, 'app', 'build', 'outputs', 'apk', 'release')
        apk_path = None
        for p in Path(apk_src_dir).glob('*.apk'):
            apk_path = str(p)
            break
        if not apk_path:
            raise FileNotFoundError('No APK produced in expected output path: ' + apk_src_dir)

        out_apk = os.path.join(TASK_OUTPUT_DIR, f'{tid}.apk')
        shutil.copy(apk_path, out_apk)
        print(f"[{tid}] APK copied to {out_apk}")

        # Optionally upload to GitHub Releases if env provided
        github_token = os.environ.get('GITHUB_TOKEN')
        github_repo = os.environ.get('GITHUB_REPO')  # format: owner/repo
        if github_token and github_repo:
            try:
                public_url = upload_apk_to_github(out_apk, github_repo, github_token)
                meta_file = os.path.join(workdir, 'output_url.txt')
                with open(meta_file, 'w', encoding='utf-8') as f:
                    f.write(public_url)
                print(f"[{tid}] Uploaded APK to GitHub Releases: {public_url}")
            except Exception as e:
                # log upload failure but don't fail main build
                with open(os.path.join(workdir, 'error.txt'), 'a', encoding='utf-8') as f:
                    f.write("\nGitHub upload failed:\n")
                    f.write(str(e) + "\n")
                    f.write(traceback.format_exc())
                print(f"[{tid}] GitHub upload failed: {e}")

    except Exception as e:
        # generic exception handling - write to error file
        errf = os.path.join(workdir, 'error.txt')
        with open(errf, 'w', encoding='utf-8') as f:
            f.write("Exception during build:\n")
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
        print(f"[{tid}] Exception during build: {e}")
    finally:
        # release semaphore if acquired
        if lock_acquired:
            _build_semaphore.release()
        print(f"[{tid}] Build thread finished.")

# --------------------------
# Helper: upload to GitHub Releases
# --------------------------
def upload_apk_to_github(apk_path, repo_full, token, tag_name=None):
    """
    Upload apk_path to repo_full (format: 'owner/repo') Releases.
    Creates a release (non-draft) and uploads the asset.
    Returns browser_download_url on success.
    """
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    if not tag_name:
        tag_name = f"auto-build-{int(time.time())}"
    owner_repo = repo_full.strip()
    if '/' not in owner_repo:
        raise ValueError("GITHUB_REPO must be in form 'owner/repo'")
    owner, repo = owner_repo.split('/', 1)

    # Step 1: create release
    create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    body = {"tag_name": tag_name, "name": tag_name, "draft": False, "prerelease": False}
    r = requests.post(create_url, json=body, headers=headers, timeout=30)
    if not (200 <= r.status_code < 300):
        # If release already exists for this tag, try to find it (rare)
        raise RuntimeError(f"Failed to create release: {r.status_code} {r.text}")
    release = r.json()
    upload_url_template = release.get("upload_url")  # template with {?name,label}
    if not upload_url_template:
        raise RuntimeError("No upload_url in create release response")

    # Step 2: upload asset
    name = os.path.basename(apk_path)
    upload_url = upload_url_template.split("{")[0] + f"?name={name}"
    with open(apk_path, "rb") as fh:
        data = fh.read()
    upload_headers = {**headers, "Content-Type": "application/vnd.android.package-archive"}
    r2 = requests.post(upload_url, data=data, headers=upload_headers, timeout=120)
    if not (200 <= r2.status_code < 300):
        raise RuntimeError(f"Failed to upload asset: {r2.status_code} {r2.text}")
    asset = r2.json()
    return asset.get("browser_download_url")

