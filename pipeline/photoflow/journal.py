"""Safe file moves. Nothing is ever deleted or overwritten; every move is logged so it can be undone."""
import csv
import datetime as dt
import json
import os
from pathlib import Path

WORKDIR = "_photoflow"


class Workspace:
    """Holds the run state for one photo folder (<root>/_photoflow)."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.dir = self.root / WORKDIR
        self.dir.mkdir(exist_ok=True)
        (self.dir / "cache").mkdir(exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.journal_path = self.dir / "journal.tsv"
        self.state = json.loads(self.state_path.read_text("utf-8")) if self.state_path.exists() else {"shots": {}}

    # -- state ---------------------------------------------------------------
    @property
    def shots(self):
        return self.state["shots"]

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=1), "utf-8")
        os.replace(tmp, self.state_path)

    def path(self, rel):
        return self.root / rel

    # -- moving --------------------------------------------------------------
    def _free_name(self, folder, stem, exts, taken):
        n = 1
        while True:
            sfx = "" if n == 1 else f" ({n})"
            names = [f"{stem}{sfx}{e}" for e in exts]
            if not any((folder / x).exists() or str(folder / x).lower() in taken for x in names):
                return sfx
            n += 1

    def move_shot(self, shot_id, dest_folder, stage, taken=None):
        """Move every file of a shot (e.g. RAW + JPG pair) into dest_folder (relative to root), keeping
        them together under one name. Returns the new relative paths."""
        taken = taken if taken is not None else set()
        shot = self.shots[shot_id]
        folder = self.root / dest_folder
        files = [Path(f) for f in shot["files"]]
        if all(f.parent.as_posix() == Path(dest_folder).as_posix() for f in files):
            return shot["files"]
        folder.mkdir(parents=True, exist_ok=True)
        stem = Path(files[0].name).stem
        for f in files:  # keep the shortest shared stem (pairs share it)
            stem = min(stem, Path(f.name).stem, key=len)
        sfx = self._free_name(folder, stem, [f.suffix for f in files], taken)
        new = []
        with open(self.journal_path, "a", encoding="utf-8", newline="") as jf:
            w = csv.writer(jf, delimiter="\t")
            for f in files:
                src = self.root / f
                dst = folder / f"{stem}{sfx}{f.suffix}"
                if dst.exists():
                    raise RuntimeError(f"refusing to overwrite {dst}")
                size = src.stat().st_size
                os.rename(src, dst)
                if dst.stat().st_size != size:
                    raise RuntimeError(f"size changed while moving {src}")
                rel = dst.relative_to(self.root).as_posix()
                taken.add(str(dst).lower())
                w.writerow([dt.datetime.now().isoformat(timespec="seconds"), stage, f.as_posix(), rel, size])
                new.append(rel)
        shot["files"] = new
        return new

    def rename_folder(self, old_rel, new_rel, stage):
        src, dst = self.root / old_rel, self.root / new_rel
        if not src.exists():
            return
        if dst.exists():  # merge folder contents
            for shot_id, shot in self.shots.items():
                if any(Path(f).parent.as_posix() == Path(old_rel).as_posix() for f in shot["files"]):
                    self.move_shot(shot_id, new_rel, stage)
            for leftover in src.iterdir():
                os.rename(leftover, dst / leftover.name) if not (dst / leftover.name).exists() else None
            try:
                src.rmdir()
            except OSError:
                pass
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.rename(src, dst)
        with open(self.journal_path, "a", encoding="utf-8", newline="") as jf:
            csv.writer(jf, delimiter="\t").writerow([dt.datetime.now().isoformat(timespec="seconds"), stage, old_rel + "/", new_rel + "/", 0])
        pre = Path(old_rel).as_posix() + "/"
        for shot in self.shots.values():
            shot["files"] = [Path(new_rel).as_posix() + "/" + f[len(pre):] if f.startswith(pre) else f for f in shot["files"]]


def undo(root, stage=None):
    """Reverse moves from the journal (newest first). Optionally only one stage."""
    ws = Workspace(root)
    rows = list(csv.reader(open(ws.journal_path, encoding="utf-8"), delimiter="\t")) if ws.journal_path.exists() else []
    keep, undone = [], 0
    for row in reversed(rows):
        ts, st, src, dst = row[:4]
        if stage and st != stage:
            keep.append(row)
            continue
        s, d = ws.path(dst.rstrip("/")), ws.path(src.rstrip("/"))
        if s.exists() and not d.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            os.rename(s, d)
            undone += 1
            for shot in ws.shots.values():
                if dst.endswith("/"):  # folder rename
                    shot["files"] = [src + f[len(dst):] if f.startswith(dst) else f for f in shot["files"]]
                else:
                    shot["files"] = [src if f == dst else f for f in shot["files"]]
        else:
            keep.append(row)
    with open(ws.journal_path, "w", encoding="utf-8", newline="") as jf:
        csv.writer(jf, delimiter="\t").writerows(reversed(keep))
    ws.save()
    # tidy empty folders left behind (never touches non-empty ones)
    for p in sorted(ws.root.rglob("*"), key=lambda p: -len(p.parts)):
        if p.is_dir() and WORKDIR not in p.parts and not any(p.iterdir()):
            p.rmdir()
    return undone
