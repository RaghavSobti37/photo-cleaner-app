from PIL import Image
import imagehash
from collections import defaultdict
from tqdm import tqdm
import os

def compute_hash(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        return str(imagehash.phash(image))
    except Exception:
        return None

def find_duplicates(image_paths):
    print("\n[LOG] 🤖 Finding duplicate images by perceptual hash...\n")
    hash_map = defaultdict(list)
    for path in tqdm(image_paths, desc="🧠 Hashing", unit="img"):
        print(f"[FILE] Hashing: {os.path.basename(path)}")
        h = compute_hash(path)
        if h:
            hash_map[h].append(path)

    return [group for group in hash_map.values() if len(group) > 1]

def find_similar_images(image_paths, threshold=5):
    print("\n[LOG] 🤖 Finding visually similar images...\n")
    hash_map = {}
    similar_groups = []

    for i, path1 in enumerate(tqdm(image_paths, desc="🔍 Comparing", unit="img")):
        h1 = compute_hash(path1)
        if not h1:
            continue

        group = [path1]
        for j in range(i + 1, len(image_paths)):
            path2 = image_paths[j]
            h2 = compute_hash(path2)
            if not h2:
                continue

            if imagehash.hex_to_hash(h1) - imagehash.hex_to_hash(h2) <= threshold:
                group.append(path2)

        if len(group) > 1:
            similar_groups.append(group)

    return similar_groups

from backend.face_quality import analyze_face_quality

def select_best_image(image_group):
    scored = [(img, analyze_face_quality(img)) for img in image_group]
    scored.sort(key=lambda x: x[1], reverse=True)  # Highest score = best
    return scored[0][0] if scored else image_group[0]
