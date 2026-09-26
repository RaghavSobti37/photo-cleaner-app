# backend/organizer.py

import os
from PIL import Image
from PIL.ExifTags import TAGS
import shutil
from datetime import datetime
from tqdm import tqdm

def get_image_date(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return None

def organize_images_by_date(image_paths, output_dir):
    print("\n[LOG] 📆 Organizing images by date...\n")
    for path in tqdm(image_paths, desc="📂 Organizing", unit="img"):
        date_taken = get_image_date(path)
        if not date_taken:
            folder = os.path.join(output_dir, 'UnknownDate')
        else:
            folder = os.path.join(output_dir, date_taken.strftime('%Y-%m-%d'))

        os.makedirs(folder, exist_ok=True)
        shutil.copy2(path, folder)