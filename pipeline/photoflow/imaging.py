"""Image loading + per-shot quality features (photo-cleaner scoring: sharpness + eyes/smiles)."""
import numpy as np
from PIL import Image, ImageOps

try:
    import pillow_heif  # optional HEIC support
    pillow_heif.register_heif_opener()
except ImportError:
    pass

_ROT = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}


def load(path, size, orientation=None):
    """Open at roughly `size` long edge, upright. orientation=None -> use the file's own EXIF."""
    im = Image.open(path)
    im.draft("RGB", (size, size))
    if orientation is None:
        im = ImageOps.exif_transpose(im)
    elif orientation in _ROT:
        im = im.transpose(_ROT[orientation])
    im = im.convert("RGB")
    im.thumbnail((size, size))
    return im


_cascades = None


def _haar():
    global _cascades
    if _cascades is None:
        import cv2
        base = getattr(getattr(cv2, "data", None), "haarcascades", "")
        try:
            _cascades = tuple(cv2.CascadeClassifier(base + n) for n in (
                "haarcascade_frontalface_default.xml", "haarcascade_eye.xml", "haarcascade_smile.xml"))
            if _cascades[0].empty():
                _cascades = ()
        except Exception:
            _cascades = ()
    return _cascades


def face_quality(gray):
    """Same rule as legacy-cli/backend/face_quality.py: +1 per face with two open eyes, +1 per smile."""
    c = _haar()
    if not c:
        return 0
    face, eye, smile = c
    score = 0
    for (x, y, w, h) in face.detectMultiScale(gray, 1.3, 5):
        roi = gray[y:y + h, x:x + w]
        if len(eye.detectMultiScale(roi)) >= 2:
            score += 1
        if len(smile.detectMultiScale(roi, scaleFactor=1.8, minNeighbors=20)) >= 1:
            score += 1
    return score


def features(im):
    import cv2
    import imagehash
    g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(g, cv2.CV_64F)
    h, w = g.shape
    th, tw = max(1, h // 6), max(1, w // 6)
    tiles = [lap[i:i + th, j:j + tw].var() for i in range(0, h - th + 1, th) for j in range(0, w - tw + 1, tw)]
    small = im.resize((64, 48))
    hsv = np.asarray(small.convert("HSV")).reshape(-1, 3)
    hist, _ = np.histogramdd(hsv, bins=(12, 4, 4), range=((0, 256),) * 3)
    lay = np.asarray(small.convert("L").resize((16, 12)), dtype=float).ravel()
    lay = (lay - lay.mean()) / (lay.std() + 1e-6)
    half = cv2.resize(g, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    return {
        "ph": str(imagehash.phash(im)),
        "sharp": float(lap.var()),
        "detail": float(np.percentile(tiles, 90)),
        "bright": float(g.mean()),
        "fscore": face_quality(half),
        "hist": (hist / hist.sum()).ravel().round(4).tolist(),
        "layout": lay.round(2).tolist(),
    }
