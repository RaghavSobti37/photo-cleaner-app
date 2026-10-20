"""Face detection (YuNet) + recognition (SFace), clustering into people, and the face library.

Folders produced:
  People/<Name | Person 012>   photos with 1-2 faces, filed under the biggest face
  People/Others                people who appear in fewer than `main_person_min_photos` photos
  Group Photos                 3+ clearly visible faces
  360/<same names>             studio shots get the same split inside 360/
The face library (~/.photoflow/face_library.json) remembers everyone you have named, so the next
shoot is named automatically and only new main people need a name.
"""
import json
import os
import random
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

from .catalog import analysis_image
from .imaging import load

HOME = Path(os.environ.get("PHOTOFLOW_HOME", Path.home() / ".photoflow"))
MODELS = {
    "yunet.onnx": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface.onnx": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
PEOPLE, GROUPS, OTHERS = "People", "Group Photos", "Others"


def models(log=print):
    d = HOME / "models"
    d.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        if not (d / name).exists() or (d / name).stat().st_size < 100_000:
            log(f"Downloading {name}…")
            tmp = d / (name + ".part")
            req = urllib.request.Request(url, headers={"User-Agent": "photoflow/2.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
                while chunk := r.read(1 << 20):
                    fh.write(chunk)
            os.replace(tmp, d / name)
    return d / "yunet.onnx", d / "sface.onnx"


# ---------------------------------------------------------------- library
def load_library():
    p = HOME / "face_library.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else {}


def save_library(lib):
    HOME.mkdir(parents=True, exist_ok=True)
    p = HOME / "face_library.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(lib), "utf-8")
    os.replace(tmp, p)


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


# ---------------------------------------------------------------- detection
def detect(ws, keys, st, log=print):
    import cv2
    ydet, srec = models(log)
    det = cv2.FaceDetectorYN.create(str(ydet), "", (320, 320), 0.75, 0.3, 5000)
    rec = cv2.FaceRecognizerSF.create(str(srec), "")
    cache_p = ws.dir / "cache" / "faces.jsonl"
    crops = ws.dir / "crops"
    crops.mkdir(exist_ok=True)
    cache = {}
    if cache_p.exists():
        for line in open(cache_p, encoding="utf-8"):
            k, v = json.loads(line)
            cache[k] = v
    todo = [k for k in keys if k not in cache]
    if todo:
        log(f"Finding faces in {len(todo)} photos…")
    with open(cache_p, "a", encoding="utf-8") as fh:
        for i, k in enumerate(todo, 1):
            path, manual = analysis_image(ws, k)
            faces = []
            if path is not None:
                try:
                    im = load(path, st.work_size, ws.shots[k].get("orientation", 1) if manual else None)
                    a = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
                    det.setInputSize((a.shape[1], a.shape[0]))
                    _, found = det.detect(a)
                    for j, fc in enumerate(found if found is not None else []):
                        item = {"w": float(fc[2]), "score": float(fc[14]), "emb": None}
                        if fc[2] >= st.face_id_min_px and fc[14] >= st.face_min_score:
                            al = rec.alignCrop(a, fc)
                            item["emb"] = rec.feature(al)[0].round(4).tolist()
                            item["crop"] = f"{k}_{j}.jpg"
                            cv2.imwrite(str(crops / item["crop"]), al)
                        faces.append(item)
                except Exception as e:
                    log(f"  skipped {k}: {e}")
            cache[k] = faces
            fh.write(json.dumps([k, faces]) + "\n")
            if i % 250 == 0:
                log(f"  {i}/{len(todo)}")
    return {k: cache[k] for k in keys}


# ---------------------------------------------------------------- clustering
def chinese_whispers(E, threshold, iterations=30, seed=0):
    """Graph clustering used by dlib for faces: link faces above `threshold`, let labels spread."""
    S = E @ E.T
    nb = [np.where(S[i] >= threshold)[0] for i in range(len(E))]
    lab = np.arange(len(E))
    rnd = random.Random(seed)
    for _ in range(iterations):
        order = list(range(len(E)))
        rnd.shuffle(order)
        changed = 0
        for i in order:
            w = defaultdict(float)
            for j in nb[i]:
                if j != i:
                    w[lab[j]] += S[i, j]
            if w:
                best = max(w, key=w.get)
                if best != lab[i]:
                    lab[i], changed = best, changed + 1
        if not changed:
            break
    return lab


def plan(ws, faces, st, log=print):
    """Returns (dest per shot, people summary for naming)."""
    visible = {k: [f for f in fs if f["w"] >= st.face_min_px and f["score"] >= st.face_min_score] for k, fs in faces.items()}
    ids = [(k, f) for k, fs in visible.items() for f in fs if f.get("emb")]
    if not ids:
        return {}, {}
    E = np.array([_unit(f["emb"]) for _, f in ids])
    lab = chinese_whispers(E, st.face_match)
    clusters = defaultdict(list)
    for i, l in enumerate(lab):
        clusters[int(l)].append(i)
    face_cluster = {id(ids[i][1]): l for l, m in clusters.items() for i in m}
    # match clusters against the face library
    lib = load_library()
    lib_c = {name: _unit(np.mean([_unit(e) for e in embs], axis=0)) for name, embs in lib.items() if embs}
    names = {}
    for l, m in clusters.items():
        c = _unit(E[m].mean(0))
        if lib_c:
            best = max(lib_c, key=lambda n: float(c @ lib_c[n]))
            if float(c @ lib_c[best]) >= st.library_match:
                names[l] = best
    # who is the main person of each photo
    main = {}
    for k, fs in visible.items():
        if 0 < len(fs) < st.group_min_faces:
            top = max(fs, key=lambda f: f["w"])
            main[k] = face_cluster.get(id(top))
    count = defaultdict(int)
    for l in main.values():
        if l is not None:
            count[l] += 1
    order = sorted((l for l in count if l not in names and count[l] >= st.main_person_min_photos), key=lambda l: -count[l])
    label = {l: f"Person {n:03d}" for n, l in enumerate(order, 1)}
    label.update(names)
    dest = {}
    for k, fs in visible.items():
        in_studio = ws.shots[k]["files"][0].startswith("360/")
        if len(fs) >= st.group_min_faces:
            folder = GROUPS
        elif k in main:
            folder = f"{PEOPLE}/{label.get(main[k], OTHERS)}"
        else:
            continue
        dest[k] = ("360/" + folder.replace(PEOPLE + "/", "")) if in_studio else folder
    # summary for the naming page
    people = {}
    for l, lb in label.items():
        m = clusters[l]
        faces_sorted = sorted(m, key=lambda i: -ids[i][1]["w"])
        people[lb] = {"photos": count[l], "named": l in names, "crops": [ids[i][1]["crop"] for i in faces_sorted[:4]],
                      "centroid": _unit(E[m].mean(0)).round(4).tolist(),
                      "sample_embs": [ids[i][1]["emb"] for i in faces_sorted[:20]]}
    others = sum(1 for k, l in main.items() if l not in label)
    log(f"People: {len(names)} recognised from your library, {len(order)} new main people to name, "
        f"{others} photos of occasional faces -> People/{OTHERS}")
    return dest, people
