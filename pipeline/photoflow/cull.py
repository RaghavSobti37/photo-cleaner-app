"""Decide which shots stay as the final selection and which go to Archive/<reason>.

Order (same as the photo-cleaner pipeline, extended):
  1. camera video thumbnails      -> Archive/Video Thumbnails
  2. black / no-detail frames     -> Archive/Blurry or Too Dark
  3. byte-identical copies        -> Archive/Duplicates            (best copy stays)
  4. bursts (same frame)          -> Archive/Similar Shots (Not Best)
  5. look-alike groups (~50%)     -> keep best N, rest to Archive/Similar Shots (Not Best)
Everything that survives is flattened into the root folder (no date folders).
"""
import hashlib
import numpy as np
import imagehash

ARCHIVE = "Archive"
THUMBS = f"{ARCHIVE}/Video Thumbnails"
BAD = f"{ARCHIVE}/Blurry or Too Dark"
DUPS = f"{ARCHIVE}/Duplicates"
SIMILAR = f"{ARCHIVE}/Similar Shots (Not Best)"


def score(f):
    """photo-cleaner image_ranker: sharpness + 100 per open-eyes/smile hit."""
    return f["sharp"] + 100 * f.get("fscore", 0)


def similarity(a, b):
    """0..1 look-alike score: perceptual hash + colour histogram + coarse layout."""
    ph = 1 - (a["_ph"] - b["_ph"]) / 64
    hi = float(np.minimum(a["_hist"], b["_hist"]).sum())
    co = max(0.0, float(a["_lay"] @ b["_lay"]) / len(a["_lay"]))
    return 0.4 * ph + 0.3 * hi + 0.3 * co


def _fingerprint(path):
    h, size = hashlib.sha1(), path.stat().st_size
    with open(path, "rb") as fh:
        for off in (0, size // 2, max(0, size - (4 << 20))):
            fh.seek(off)
            h.update(fh.read(4 << 20))
    return f"{size}:{h.hexdigest()}"


def _chain(items, link, gap):
    """Group shots shot one after another (same camera, same day) when `link(new, recent)` holds."""
    import datetime as dt
    items = sorted(items, key=lambda r: (r["model"], r["time"]))
    groups, cur = [], []
    for r in items:
        if cur and r["model"] == cur[-1]["model"] and r["time"] - cur[-1]["time"] <= gap \
                and dt.date.fromtimestamp(r["time"]) == dt.date.fromtimestamp(cur[-1]["time"]) \
                and any(link(r, x) for x in cur[-8:]):
            cur.append(r)
        else:
            if cur:
                groups.append(cur)
            cur = [r]
    if cur:
        groups.append(cur)
    return groups


def plan(ws, feats, st, log=print):
    dest, recs = {}, []
    for k, s in ws.shots.items():
        if s.get("thumbnail"):
            dest[k] = THUMBS
            continue
        f = feats.get(k)
        if not f or "error" in f:
            dest[k] = ""  # unreadable / unsupported (e.g. HEIC without pillow-heif): keep, never archive
            continue
        if f["bright"] < st.dark_brightness or f["detail"] < st.min_detail:
            dest[k] = BAD
            continue
        recs.append({"k": k, "f": f, "score": score(f), "time": s.get("time"), "model": s.get("model", ""),
                     "_ph": imagehash.hex_to_hash(f["ph"]), "_hist": np.array(f["hist"]),
                     "_lay": np.array(f["layout"])})
    # 3. exact duplicates (same picture hash, then confirm bytes)
    by_ph = {}
    for r in recs:
        by_ph.setdefault(r["f"]["ph"], []).append(r)
    for grp in (g for g in by_ph.values() if len(g) > 1):
        by_fp = {}
        for r in grp:
            by_fp.setdefault(_fingerprint(ws.path(ws.shots[r["k"]]["files"][0])), []).append(r)
        for same in (g for g in by_fp.values() if len(g) > 1):
            same.sort(key=lambda r: -r["score"])
            for r in same[1:]:
                dest[r["k"]] = DUPS
    live = [r for r in recs if r["k"] not in dest]
    timed = [r for r in live if r["time"]]
    # 4. bursts
    for g in _chain(timed, lambda a, b: (a["_ph"] - b["_ph"]) <= st.burst_phash, st.burst_seconds):
        for r in sorted(g, key=lambda r: -r["score"])[1:]:
            dest[r["k"]] = SIMILAR
    # 5. best N per look-alike group
    timed = [r for r in timed if r["k"] not in dest]
    groups = _chain(timed, lambda a, b: similarity(a, b) >= st.similar_threshold, st.similar_gap_seconds)
    n_groups = 0
    for g in groups:
        if len(g) > st.keep_per_group:
            n_groups += 1
            for r in sorted(g, key=lambda r: -r["score"])[st.keep_per_group:]:
                dest[r["k"]] = SIMILAR
    for r in recs:
        dest.setdefault(r["k"], "")  # keepers -> root
    log(f"Look-alike groups trimmed to best {st.keep_per_group}: {n_groups}")
    return dest
