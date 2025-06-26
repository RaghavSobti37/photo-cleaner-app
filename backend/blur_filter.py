# # backend/blur_filter.py

# import os
# import cv2
# from tqdm import tqdm
# import time

# def is_blurry(image_path, threshold=100):
#     img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
#     if img is None:
#         return True  # If unreadable, mark blurry
#     laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
#     return laplacian_var < threshold

# def remove_blurry_images(image_paths):
#     clean_images = []
#     start_time = time.time()

#     print("\n[LOG] 🧹 Checking for blurry images...\n")

#     for image_path in tqdm(image_paths, desc="🔍 Blurry Check", unit="img"):
#         print(f"[FILE] Checking: {os.path.basename(image_path)}")
#         if not is_blurry(image_path):
#             clean_images.append(image_path)

#     total_time = time.time() - start_time
#     print(f"\n[SUMMARY] 🧹 Blurry removal complete in {total_time:.2f}s")
#     return clean_images
