"""Find every photo, group RAW+JPG pairs into one "shot", read metadata, extract RAW previews."""
import re
from pathlib import Path

from .journal import WORKDIR
from .metadata import IMG_EXT, RAW_EXT, extract_previews, read_metadata

THUMB = re.compile(r"T0\d$", re.I)          # Sony/XAVC clip thumbnails: C0001T01.JPG, 093_0885T01.JPG
SKIP_DIRS = {WORKDIR, "$RECYCLE.BIN", "System Volume Information"}


def shot_key(rel_stem):
    return rel_stem.replace("/", "__")


def scan(ws, et, log=print):
    """(Re)build ws.shots from disk. Existing shots keep their key; new files get new shots."""
    known = {f: k for k, s in ws.shots.items() for f in s["files"]}
    groups = {}
    for p in ws.root.rglob("*"):
        if not p.is_file() or any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(ws.root).parts):
            continue
        ext = p.suffix.lower()
        if ext not in IMG_EXT | RAW_EXT:
            continue
        rel = p.relative_to(ws.root).as_posix()
        groups.setdefault(rel[: -len(p.suffix)], []).append(rel)
    shots = {}
    for stem, files in groups.items():
        key = next((known[f] for f in files if f in known), shot_key(stem))
        old = ws.shots.get(key, {})
        shots[key] = {**old, "files": sorted(files)}
    ws.state["shots"] = shots
    # metadata for anything we have not read yet
    need = [k for k, s in shots.items() if "time" not in s]
    if need:
        log(f"Reading capture times for {len(need)} shots…")
        meta = read_metadata(et, [ws.path(shots[k]["files"][0]) for k in need])
        for k in need:
            m = meta.get(str(ws.path(shots[k]["files"][0]).resolve()), {})
            shots[k].update(time=m.get("time"), model=m.get("model", ""), orientation=m.get("orientation", 1))
    for k, s in shots.items():
        s["thumbnail"] = bool(THUMB.search(Path(s["files"][0]).stem)) and len(s["files"]) == 1 \
            and s["files"][0].lower().endswith(".jpg")
    # RAW-only shots: analyse the embedded preview
    raws = []
    for k, s in shots.items():
        if not any(Path(f).suffix.lower() in IMG_EXT for f in s["files"]):
            raw = next((f for f in s["files"] if Path(f).suffix.lower() in RAW_EXT), None)
            if raw:
                raws.append((k, ws.path(raw)))
    if raws:
        log(f"Extracting embedded previews from {len(raws)} RAW files…")
        extract_previews(et, raws, ws.dir / "previews")
    ws.save()
    return shots


def analysis_image(ws, key):
    """Path of the image to analyse + whether orientation must be applied manually."""
    s = ws.shots[key]
    for f in s["files"]:
        if Path(f).suffix.lower() in IMG_EXT:
            return ws.path(f), False
    p = ws.dir / "previews" / f"{key}.jpg"
    return (p if p.exists() else None), True
