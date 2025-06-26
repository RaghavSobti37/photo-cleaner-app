import cv2
import numpy as np
from PIL import Image
import face_recognition

def get_sharpness(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    return cv2.Laplacian(img, cv2.CV_64F).var()

def get_face_score(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        return len(face_locations)  # More faces = better?
    except Exception:
        return 0

def score_image(image_path):
    sharpness = get_sharpness(image_path)
    faces = get_face_score(image_path)
    return sharpness + (faces * 100)  # Weight faces more heavily

def select_best_image(image_paths):
    scored = [(path, score_image(path)) for path in image_paths]
    best = max(scored, key=lambda x: x[1])
    return best[0]
