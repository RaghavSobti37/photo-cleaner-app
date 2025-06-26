# backend/face_quality.py

import cv2

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")

def analyze_face_quality(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    score = 0
    for (x, y, w, h) in faces:
        face_region = gray[y:y+h, x:x+w]

        eyes = eye_cascade.detectMultiScale(face_region)
        smiles = smile_cascade.detectMultiScale(face_region, scaleFactor=1.8, minNeighbors=20)

        if len(eyes) >= 2:
            score += 1  # both eyes open
        if len(smiles) >= 1:
            score += 1  # smile detected

    return score
