import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PHOTOFLOW_HOME"] = tempfile.mkdtemp()

from photoflow.config import Settings  # noqa: E402
from photoflow.faces import chinese_whispers  # noqa: E402
from photoflow.journal import Workspace, undo  # noqa: E402
from photoflow.naming import clean_name, parse_names  # noqa: E402


class Naming(unittest.TestCase):
    def test_csv(self):
        self.assertEqual(parse_names("number,name\n1,Arjun\n12,\"Meera K\"\n7,\n"),
                         [("Person 001", "Arjun"), ("Person 012", "Meera K")])

    def test_free_text(self):
        text = "#1 Arjun\nPerson 012 - Meera\n3: =#1\n"
        self.assertEqual(parse_names(text), [("Person 001", "Arjun"), ("Person 012", "Meera"), ("Person 003", "=#1")])

    def test_clean_name(self):
        self.assertEqual(clean_name('Ritika / "Ritam".'), "Ritika  Ritam")


class Clustering(unittest.TestCase):
    def test_two_people(self):
        rng = np.random.default_rng(0)
        a, b = rng.normal(size=128), rng.normal(size=128)
        E = np.array([a + rng.normal(scale=0.3, size=128) for _ in range(5)] +
                     [b + rng.normal(scale=0.3, size=128) for _ in range(4)])
        E /= np.linalg.norm(E, axis=1, keepdims=True)
        lab = chinese_whispers(E, 0.5)
        self.assertEqual(len(set(lab[:5])), 1)
        self.assertEqual(len(set(lab[5:])), 1)
        self.assertNotEqual(lab[0], lab[5])


class SafeMoves(unittest.TestCase):
    def test_move_never_overwrites_and_undo(self):
        root = Path(tempfile.mkdtemp())
        (root / "day1").mkdir()
        (root / "day2").mkdir()
        for d in ("day1", "day2"):
            (root / d / "DSC1.JPG").write_bytes(d.encode())
            (root / d / "DSC1.ARW").write_bytes(d.encode() * 2)
        ws = Workspace(root)
        ws.state["shots"] = {"a": {"files": ["day1/DSC1.ARW", "day1/DSC1.JPG"]},
                             "b": {"files": ["day2/DSC1.ARW", "day2/DSC1.JPG"]}}
        ws.move_shot("a", "", "test")
        ws.move_shot("b", "", "test")
        ws.save()
        names = sorted(p.name for p in root.iterdir() if p.is_file())
        self.assertEqual(names, ["DSC1 (2).ARW", "DSC1 (2).JPG", "DSC1.ARW", "DSC1.JPG"])  # pair kept together
        self.assertEqual(undo(root), 4)
        self.assertEqual((root / "day2" / "DSC1.JPG").read_bytes(), b"day2")

    def test_settings_override(self):
        s = Settings.from_overrides(["keep_per_group=5", "similar_threshold=0.6"])
        self.assertEqual((s.keep_per_group, s.similar_threshold), (5, 0.6))


if __name__ == "__main__":
    unittest.main()
