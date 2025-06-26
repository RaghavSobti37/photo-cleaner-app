import cv2
import numpy as np
from PIL import Image
from backend.face_quality import analyze_face_quality # Import the new face quality analysis function

def get_sharpness(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    return cv2.Laplacian(img, cv2.CV_64F).var()

def get_face_score(image_path):
    # Use the analyze_face_quality function from backend.face_quality
    return analyze_face_quality(image_path)

def score_image(image_path):
    sharpness = get_sharpness(image_path)
    faces = get_face_score(image_path)
    return sharpness + (faces * 100)  # Weight faces more heavily

def select_best_image(image_paths):
    scored = [(path, score_image(path)) for path in image_paths]
    best = max(scored, key=lambda x: x[1])
    return best[0]

def score_and_sort_images(image_paths):
    """
    Scores all images in the list and returns them sorted by score in descending order.
    """
    scored_images = [(path, score_image(path)) for path in image_paths]
    # Sort by score in descending order
    sorted_images = sorted(scored_images, key=lambda x: x[1], reverse=True)
    return [path for path, score in sorted_images]
