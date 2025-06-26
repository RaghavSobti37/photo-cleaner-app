import os
import time
import asyncio
import shutil
from backend.scanner import scan_images
from backend.duplicate_detector import find_duplicates, find_similar_images, select_best_image
from backend.organizer import organize_images_by_date
from backend.utils import log_progress

async def scan(input_dir):
    log_progress("🔍 Scanning for image files...")
    return scan_images(input_dir)

async def detect_duplicates(images):
    log_progress("🧬 Detecting duplicate images...")
    return find_duplicates(images)

async def detect_similars(images):
    log_progress("🤝 Finding similar-looking images...")
    return find_similar_images(images)

async def retain_best_images(groups, output_dir, label):
    log_progress(f"🏆 Selecting best images in {label}...")
    best_dir = os.path.join(output_dir, label)
    os.makedirs(best_dir, exist_ok=True)

    for group in groups:
        log_progress(f"📂 Reviewing group:")
        for path in group:
            log_progress(f"📄 {os.path.basename(path)}")

        best = select_best_image(group)
        shutil.copy2(best, best_dir)
        log_progress(f"✅ Selected best: {os.path.basename(best)}")

async def organize(images, output_dir):
    log_progress("📁 Organizing original images by date...")
    organize_images_by_date(images, output_dir)

async def main():
    input_dir = input("Enter the path to your photo folder: ").strip()
    output_dir = os.path.join(input_dir, "CleanedPhotos")
    os.makedirs(output_dir, exist_ok=True)

    total_start_time = time.time()
    log_progress("🚀 Starting processing pipeline")

    image_paths = await scan(input_dir)
    clear_images = image_paths  # No blur filtering

    # Run duplicate/similar finding concurrently
    duplicate_task = asyncio.create_task(detect_duplicates(clear_images))
    similar_task = asyncio.create_task(detect_similars(clear_images))

    # Wait for detection results
    duplicate_groups = await duplicate_task
    similar_groups = await similar_task

    # Select best from groups
    await retain_best_images(duplicate_groups, output_dir, "BestDuplicates")
    await retain_best_images(similar_groups, output_dir, "BestSimilar")

    # Organize originals last
    await organize(clear_images, output_dir)

    log_progress("🎉 All processing complete!")
    print(f"\n[LOG] 🕒 Total processing time: {time.time() - total_start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
