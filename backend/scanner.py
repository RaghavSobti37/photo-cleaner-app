# backend/scanner.py

import os

SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic', '.tiff', '.webp', '.bmp', '.cr2', '.nef', '.arw')

def scan_images(directory):
    image_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_EXTENSIONS):
                image_paths.append(os.path.join(root, file))
    return image_paths

# backend/utils.py

from tqdm import tqdm

def log_progress(message):
    print(f"[LOG] {message}")
