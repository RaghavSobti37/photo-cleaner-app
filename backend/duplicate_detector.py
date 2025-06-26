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
    for path in tqdm(image_paths, desc="🧠 Hashing for duplicates", unit="img"):
        h = compute_hash(path)
        if h:
            hash_map[h].append(path)

    return [group for group in hash_map.values() if len(group) > 1]

# Optimized find_similar_images to avoid redundant hash computations and O(N^2) loop
def find_similar_images(image_paths, threshold=5):
    print("\n[LOG] 🤖 Finding visually similar images...\n")
    
    # 1. Pre-compute all hashes to avoid redundant calculations
    hashes = []
    for path in tqdm(image_paths, desc="🧠 Hashing for similarity", unit="img"):
        try:
            image = Image.open(path).convert("RGB")
            h = imagehash.phash(image) # Store the actual hash object
            hashes.append((path, h))
        except Exception:
            continue

    # 2. Group similar images efficiently
    groups = []
    processed_indices = set() # Keep track of images already assigned to a group
    for i in tqdm(range(len(hashes)), desc="🔍 Comparing", unit="img"):
        if i in processed_indices: # Skip if already processed
            continue
        
        path1, h1 = hashes[i]
        current_group = {path1}
        processed_indices.add(i)
        
        for j in range(i + 1, len(hashes)):
            if j in processed_indices: # Skip if already processed
                continue
            
            path2, h2 = hashes[j]
            if h1 - h2 <= threshold: # Compare hash objects directly
                current_group.add(path2)
                processed_indices.add(j)
        
        if len(current_group) > 1:
            groups.append(list(current_group))
            
    return groups
