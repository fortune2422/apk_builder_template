import os, shutil, subprocess, threading, json, traceback
from pathlib import Path

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'template')
TASK_OUTPUT_DIR = '/home/project/output'
os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)

def enqueue_build_task(task_meta):
    t = threading.Thread(target=process_build, args=(task_meta,))
    t.daemon = True
    t.start()

def process_build(task_meta):
    tid = task_meta['id']
    workdir = task_meta['workdir']
    params = task_meta.get('params', {})
    try:
        build_dir = os.path.join(workdir, 'project')
        shutil.copytree(TEMPLATE_DIR, build_dir)

        # Import local scripts (they assume project structure)
        from scripts.replace_vars import apply_replacements
        apply_replacements(build_dir, params, workdir)

        # copy google-services.json if provided
        gs_src = os.path.join(workdir, 'google-services.json')
        if os.path.exists(gs_src):
            dst = os.path.join(build_dir, 'app', 'google-services.json')
            shutil.copy(gs_src, dst)

        # run gradle build
        gradlew = os.path.join(build_dir, 'gradlew')
        if not os.path.exists(gradlew):
            raise FileNotFoundError('gradlew not found in template project. Make sure template includes gradlew.')
        os.chmod(gradlew, 0o755)
        env = os.environ.copy()
        # ensure ANDROID_SDK_ROOT is set in container environment or inherited
        if 'ANDROID_SDK_ROOT' not in env:
            env['ANDROID_SDK_ROOT'] = '/opt/android-sdk'
        # Execute build (assembleRelease)
        subprocess.check_call([gradlew, 'clean', 'assembleRelease'], cwd=build_dir, env=env)

        # copy output apk
        apk_src = os.path.join(build_dir, 'app', 'build', 'outputs', 'apk', 'release')
        # find any apk in the release folder
        apk_path = None
        for p in Path(apk_src).glob('*.apk'):
            apk_path = str(p)
            break
        if not apk_path:
            raise FileNotFoundError('No APK produced in expected output path: ' + apk_src)
        out_apk = os.path.join(TASK_OUTPUT_DIR, f'{tid}.apk')
        shutil.copy(apk_path, out_apk)
    except Exception as e:
        # write error for status endpoint
        errf = os.path.join(workdir, 'error.txt')
        with open(errf, 'w', encoding='utf-8') as f:
            f.write('Exception:\n')
            f.write(traceback.format_exc())
