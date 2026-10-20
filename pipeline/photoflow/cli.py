"""photoflow — the full shoot-sorting workflow in one command.

  python -m photoflow run "D:\\Photos"                 # everything (safe: moves only, logged)
  python -m photoflow run "D:\\Photos" --dry-run       # show what would happen
  python -m photoflow apply-names "D:\\Photos" names.csv
  python -m photoflow undo "D:\\Photos" [--stage faces]
"""
import argparse
import collections
import os
import sys
from pathlib import Path

from . import analyze as an
from . import catalog, cull, faces, naming, studio
from .config import Settings
from .journal import WORKDIR, Workspace, undo
from .metadata import find_exiftool

SORTED_TOPS = ("People/", "Group Photos/", "360/")


def log(msg):
    print(msg, flush=True)


def folder_of(ws, key):
    parent = Path(ws.shots[key]["files"][0]).parent.as_posix()
    return "" if parent == "." else parent


def apply(ws, dest, stage, dry):
    moves = {k: d for k, d in dest.items() if folder_of(ws, k) != d}
    summary = collections.Counter(d or "(final selection)" for d in moves.values())
    for d, n in sorted(summary.items()):
        log(f"  {'would move' if dry else 'moved'} {n:5d} -> {d}")
    if dry:
        return
    taken = set()
    for k, d in moves.items():
        ws.move_shot(k, d, stage, taken)
    ws.save()


def tidy(root):
    """Remove folders that are now completely empty (never removes a file)."""
    for dirpath, _, _ in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p != Path(root) and WORKDIR not in p.parts and not any(p.iterdir()):
            p.rmdir()


def cmd_run(a):
    st = Settings.from_overrides(a.set)
    ws = Workspace(a.folder)
    et = find_exiftool(a.exiftool)
    if not et:
        log("! exiftool not found: RAW-only photos cannot be analysed and capture times are missing. "
            "Install exiftool or pass --exiftool.")
    skip = set((a.skip or "").split(","))
    log("1/5 Scanning")
    catalog.scan(ws, et, log)
    log(f"    {len(ws.shots)} shots")
    log("2/5 Scoring (sharpness, eyes/smiles, look-alike fingerprints)")
    feats = an.analyze(ws, st, log)
    log("3/5 Culling: duplicates, bursts, best %d per look-alike group, bad frames" % st.keep_per_group)
    dest = cull.plan(ws, feats, st, log)
    dest = {k: d for k, d in dest.items() if not (d == "" and folder_of(ws, k).startswith(tuple(t.rstrip("/") for t in SORTED_TOPS)))}
    apply(ws, dest, "cull", a.dry_run)
    if "studio" not in skip:
        log("4/5 Studio backdrop -> 360")
        keys = [k for k in ws.shots if folder_of(ws, k) == ""]
        apply(ws, studio.plan(ws, keys, st, log), "360", a.dry_run)
    if "faces" not in skip:
        log("5/5 Faces -> People / Group Photos")
        keys = [k for k in ws.shots if folder_of(ws, k) == "" or folder_of(ws, k).startswith(SORTED_TOPS)
                or folder_of(ws, k) == "360"]
        found = faces.detect(ws, keys, st, log)
        dest, people = faces.plan(ws, found, st, log)
        apply(ws, dest, "faces", a.dry_run)
        if not a.dry_run:
            page = naming.write_page(ws, people, st)
            log(f"\nName people here: {page}")
    if not a.dry_run:
        tidy(ws.root)
    log("Done. Every move is logged in %s (undo with: photoflow undo)" % ws.journal_path)


def cmd_apply(a):
    ws = Workspace(a.folder)
    naming.apply_names(ws, Path(a.names).read_text("utf-8-sig"), log)


def cmd_undo(a):
    n = undo(a.folder, a.stage)
    log(f"Restored {n} files/folders to where they were.")


def cmd_models(a):
    log("Models ready: %s, %s" % faces.models(log))


def main(argv=None):
    p = argparse.ArgumentParser(prog="photoflow", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="sort a shoot folder end to end")
    r.add_argument("folder")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--exiftool", help='e.g. "perl C:/sortphotos/src/Image-ExifTool/exiftool"')
    r.add_argument("--skip", help="comma list: studio,faces")
    r.add_argument("--set", action="append", metavar="KEY=VALUE", help="override a setting (see config.py)")
    r.set_defaults(fn=cmd_run)
    n = sub.add_parser("apply-names", help="rename Person ### folders from names.csv / text")
    n.add_argument("folder")
    n.add_argument("names")
    n.set_defaults(fn=cmd_apply)
    u = sub.add_parser("undo", help="put files back (newest moves first)")
    u.add_argument("folder")
    u.add_argument("--stage", choices=["cull", "360", "faces", "apply-names"])
    u.set_defaults(fn=cmd_undo)
    m = sub.add_parser("models", help="download face models now")
    m.set_defaults(fn=cmd_models)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
