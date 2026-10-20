"""Capture time, camera, orientation and RAW previews via exiftool.

Any exiftool works: one on PATH, `exiftool.exe` on Windows, or the copy bundled in the
sortphotos repo (`--exiftool "perl sortphotos/src/Image-ExifTool/exiftool"`).
"""
import csv
import datetime as dt
import io
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

RAW_EXT = {".arw", ".cr2", ".cr3", ".nef", ".raf", ".dng", ".orf", ".rw2"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
TAGS = ["-Model", "-DateTimeOriginal", "-SubSecTimeOriginal", "-Orientation#"]


def find_exiftool(explicit=None):
    if explicit:
        return shlex.split(explicit, posix=(not explicit[1:3] == ":\\"))
    for name in ("exiftool", "exiftool.exe", "exiftool(-k).exe"):
        p = shutil.which(name)
        if p:
            return [p]
    here = Path(__file__).resolve().parents[2]
    for cand in (here.parent / "sortphotos/src/Image-ExifTool/exiftool", here / "sortphotos/src/Image-ExifTool/exiftool"):
        if cand.exists() and shutil.which("perl"):
            return ["perl", str(cand)]
    return None


def _run(et, args, files, batch=400):
    out = []
    for i in range(0, len(files), batch):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write("\n".join(str(f) for f in files[i:i + batch]))
        r = subprocess.run(et + ["-charset", "filename=utf8", "-q", "-q"] + args + ["-@", fh.name],
                           capture_output=True)
        Path(fh.name).unlink(missing_ok=True)
        out.append(r.stdout)
    return out


def read_metadata(et, files):
    """Returns {abs_path: {'time': epoch|None, 'model': str, 'orientation': int}}."""
    res = {}
    if not et:
        return res
    for blob in _run(et, ["-fast2", "-csv"] + TAGS, files):
        for row in csv.DictReader(io.StringIO(blob.decode("utf-8", "replace"))):
            t = None
            v = row.get("DateTimeOriginal") or ""
            try:
                t = dt.datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S").timestamp()
                t += float("0." + (row.get("SubSecTimeOriginal") or "0").strip())
            except ValueError:
                pass
            try:
                o = int(row.get("Orientation#") or row.get("Orientation") or 1)
            except ValueError:
                o = 1
            res[str(Path(row["SourceFile"]).resolve())] = {"time": t, "model": row.get("Model") or "", "orientation": o}
    return res


def extract_previews(et, raw_files, out_dir):
    """Writes <out_dir>/<shot_key>.jpg for each (shot_key, raw_path). Skips existing ones."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [(k, p) for k, p in raw_files if not (out_dir / f"{k}.jpg").exists()]
    if not et or not todo:
        return
    # one exiftool process per source folder: keys are "<folder key>__<stem>", so -w can name them
    by_dir = {}
    for k, p in [t for t in todo if not t[0].endswith(Path(t[1]).stem)]:  # renamed shots: one by one
        data = subprocess.run(et + ["-q", "-q", "-b", "-PreviewImage", str(p)], capture_output=True).stdout
        if len(data) > 1000:
            (out_dir / f"{k}.jpg").write_bytes(data)
    todo = [t for t in todo if t[0].endswith(Path(t[1]).stem)]
    for k, p in todo:
        prefix = k[: len(k) - len(Path(p).stem)]
        by_dir.setdefault((Path(p).parent, prefix), []).append(p)
    for tag in ("-PreviewImage", "-JpgFromRaw"):  # JpgFromRaw = fallback for other camera brands
        for (folder, prefix), paths in by_dir.items():
            missing = [p for p in paths if not (out_dir / f"{prefix}{Path(p).stem}.jpg").exists()]
            if missing:
                pattern = str(out_dir / (prefix.replace("%", "%%") + "%f.jpg"))
                _run(et, ["-b", tag, "-w", pattern], missing)
