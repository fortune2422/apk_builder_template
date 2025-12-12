import os, re
from PIL import Image

def apply_replacements(project_dir, params, workdir):
    # 1) Replace app name in strings.xml if present
    app_name = params.get('app_name') or params.get('app') or params.get('appName')
    if app_name:
        strings_file = os.path.join(project_dir, 'app', 'src', 'main', 'res', 'values', 'strings.xml')
        if os.path.exists(strings_file):
            s = open(strings_file, 'r', encoding='utf-8').read()
            s_new = re.sub(r'<string name="app_name">.*?</string>',
                           f'<string name="app_name">{app_name}</string>', s, flags=re.S)
            open(strings_file, 'w', encoding='utf-8').write(s_new)

    # 2) Replace H5 url in MainActivity (adjust path to your MainActivity)
    h5_url = params.get('h5_url') or params.get('h5') or params.get('url')
    if h5_url:
        # NOTE: adjust this path to match your package and file name
        possible_main = [
            os.path.join(project_dir, 'app', 'src', 'main', 'java'),
        ]
        # naive: scan for files that contain loadUrl(
        for root, dirs, files in os.walk(os.path.join(project_dir, 'app', 'src', 'main', 'java')):
            for fname in files:
                if fname.endswith('.java') or fname.endswith('.kt'):
                    p = os.path.join(root, fname)
                    try:
                        txt = open(p, 'r', encoding='utf-8').read()
                        if 'loadUrl(' in txt and 'WebView' in txt:
                            txt2 = re.sub(r'loadUrl\([^)]*\)',
                                          f'loadUrl("{h5_url}")', txt)
                            open(p, 'w', encoding='utf-8').write(txt2)
                    except Exception:
                        pass

    # 3) Replace applicationId in app/build.gradle
    package_name = params.get('package_name') or params.get('applicationId') or params.get('package')
    if package_name:
        gradle_file = os.path.join(project_dir, 'app', 'build.gradle')
        if os.path.exists(gradle_file):
            s = open(gradle_file, 'r', encoding='utf-8').read()
            s_new = re.sub(r'applicationId\s+"[^"]+"', f'applicationId "{package_name}"', s)
            open(gradle_file, 'w', encoding='utf-8').write(s_new)

    # 4) Generate icons from uploaded icon.png (if any)
    icon_src = os.path.join(workdir, 'icon.png')
    if os.path.exists(icon_src):
        gen_icons(icon_src, project_dir)

def gen_icons(icon_src, project_dir):
    sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192,
    }
    img = Image.open(icon_src).convert('RGBA')
    res_dir = os.path.join(project_dir, 'app', 'src', 'main', 'res')
    for folder, size in sizes.items():
        dst = os.path.join(res_dir, folder)
        os.makedirs(dst, exist_ok=True)
        out = os.path.join(dst, 'ic_launcher.png')
        img.resize((size, size), Image.LANCZOS).save(out, format='PNG')
