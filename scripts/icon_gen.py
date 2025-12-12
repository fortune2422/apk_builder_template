# small helper (alternative icon generator) - imported if needed
from PIL import Image
import os

def generate_icons(input_path, out_res_dir):
    sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192,
    }
    img = Image.open(input_path).convert('RGBA')
    for folder, size in sizes.items():
        dst = os.path.join(out_res_dir, folder)
        os.makedirs(dst, exist_ok=True)
        img.resize((size, size), Image.LANCZOS).save(os.path.join(dst, 'ic_launcher.png'))
