"""Score every shot once and cache the result (re-runs only analyse new photos)."""
import json
from multiprocessing import Pool

from .catalog import analysis_image
from .imaging import features, load


def _work(args):
    key, path, orient, size = args
    try:
        return key, features(load(path, size, orient))
    except Exception as e:  # unreadable / corrupt file
        return key, {"error": str(e)[:200]}


def analyze(ws, settings, log=print):
    cache = ws.dir / "cache" / "features.jsonl"
    done = {}
    if cache.exists():
        for line in open(cache, encoding="utf-8"):
            try:
                k, v = json.loads(line)
                done[k] = v
            except ValueError:
                pass
    jobs = []
    for k, s in ws.shots.items():
        if k in done or s.get("thumbnail"):
            continue
        path, manual = analysis_image(ws, k)
        if path is None:
            continue
        jobs.append((k, str(path), s.get("orientation", 1) if manual else None, settings.work_size))
    if jobs:
        log(f"Analysing {len(jobs)} photos with {settings.workers} workers…")
        with open(cache, "a", encoding="utf-8") as fh, Pool(settings.workers) as pool:
            for i, (k, feat) in enumerate(pool.imap_unordered(_work, jobs, chunksize=4), 1):
                fh.write(json.dumps([k, feat]) + "\n")
                done[k] = feat
                if i % 250 == 0:
                    log(f"  {i}/{len(jobs)}")
    return done
