import os
import time
import asyncio
from backend.scanner import scan_images
from tqdm import tqdm
from backend.duplicate_detector import find_duplicates, find_similar_images
from backend.image_ranker import select_best_image
from backend.utils import log_progress
from backend.organizer import organize_images_by_date

async def scan(input_dir):
    log_progress("Scanning all images...")
    return scan_images(input_dir)

async def detect_duplicates(images):
    log_progress("Phase 1: Finding exact duplicates...")
    return find_duplicates(images)

async def detect_similars(images):
    log_progress("Phase 2: Finding visually similar images from candidates...")
    return find_similar_images(images)

async def organize_final_selection(images, output_dir):
    log_progress("Phase 3: Organizing final images by date...")
    organize_images_by_date(images, output_dir)

async def main():
    input_dir = input("Enter path to photo folder: ").strip()
    if not os.path.isdir(input_dir):
        print("Error: Invalid folder path.")
        return

    output_dir = os.path.join(input_dir, "CleanedPhotos")
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()
    log_progress("Pipeline start")

    # Step 1: Scan all images in the directory
    all_images = await scan(input_dir)
    if not all_images:
        log_progress("No images found in the specified directory.")
        return

    # Step 2: Find groups of exact duplicates
    duplicate_groups = await detect_duplicates(all_images)
    log_progress(f"Found {len(duplicate_groups)} groups of duplicate images.")

    # Step 3: Select the single best image from each duplicate group
    best_from_duplicates = []
    if duplicate_groups:
        log_progress("Selecting the best photo from each duplicate group...")
        with tqdm(total=len(duplicate_groups), desc="✨ Selecting from duplicates", unit="group", dynamic_ncols=True) as pbar:
            for group in duplicate_groups:
                best_image = select_best_image(group)
                best_from_duplicates.append(best_image)
                pbar.update(1)
    
    # Also include all non-duplicate images
    processed_in_duplicates = {img for group in duplicate_groups for img in group}
    non_duplicates = [img for img in all_images if img not in processed_in_duplicates]
    log_progress(f"Found {len(non_duplicates)} non-duplicate images.")
    
    # The pool of images for similarity check is the best from duplicates + all non-duplicates
    candidate_images = best_from_duplicates + non_duplicates
    log_progress(f"Checking {len(candidate_images)} images for visual similarity...")

    # Step 4: Find groups of visually similar images from the candidates
    similar_groups = await detect_similars(candidate_images)
    log_progress(f"Found {len(similar_groups)} groups of visually similar images.")

    # Step 5: Select the single best image from each similar group
    final_selection = []
    processed_in_similar = set()
    if similar_groups:
        log_progress("Selecting the best photo from each similar group...")
        with tqdm(total=len(similar_groups), desc="✨ Selecting from similars", unit="group", dynamic_ncols=True) as pbar:
            for group in similar_groups:
                best_image = select_best_image(group)
                final_selection.append(best_image)
                processed_in_similar.update(group)
                pbar.update(1)

    # Step 6: Add images that were candidates but not in any similar group
    unique_candidates = [img for img in candidate_images if img not in processed_in_similar]
    final_selection.extend(unique_candidates)
    log_progress(f"Keeping {len(unique_candidates)} unique-looking images.")
    log_progress(f"Total final selection: {len(final_selection)} images.")

    # Step 7: Organize the final selection into date-based folders
    if final_selection:
        await organize_final_selection(final_selection, output_dir)
    else:
        log_progress("No images were selected for the final output.")

    log_progress("Processing complete")
    print(f"[Done] Elapsed: {time.time() - start_time:.2f}s")
    print(f"Cleaned photos are available in: {output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
