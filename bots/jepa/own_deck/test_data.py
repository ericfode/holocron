"""Synthetic trajectory-to-pack boundary checks; no engine or game execution."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

JEPA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(JEPA))
import data as D
import own_deck as O


CARDS = [dict(setId=dict(set="SOR", number=n), setCodes=[dict(set="SOR", number=n)],
              cost=cost, power=2, hp=3, types=["unit"], keywords=[], traits=["rebel"],
              aspects=["heroism"], arena="ground") for n, cost in [(1, 1), (2, 7)]]


class DataBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cards = self.root / "cards.json"
        self.cards.write_text(json.dumps(CARDS))
        D._init(str(self.root / "no-card-folder"), "original", str(self.cards))
        self.game = {"t": "game", "seed": 73, "bots": ["synthetic-a", "synthetic-b"],
                     "decks": {"p1": [{"id": "SOR_001", "count": 3}],
                               "p2": [{"id": "SOR_002", "count": 3}]}}

    def tearDown(self):
        D._init(str(self.root / "no-card-folder"))
        self.temp.cleanup()

    def test_only_the_selected_original_list_enters_each_row(self):
        context = D.original_contexts(self.game)
        self.assertEqual(context["p1"].shape, (2, 207))
        self.assertTrue(context["p1"][0, 3])
        self.assertNotEqual(context["p1"][0, 8], context["p2"][0, 8])
        changed = copy.deepcopy(self.game)
        changed["decks"]["p2"] = [{"id": "SOR_001", "count": 99}]
        changed["oh"] = ["SOR_002"]
        changed["state"] = {"drawOrder": ["SOR_002", "SOR_001"]}
        np.testing.assert_array_equal(context["p1"], D.original_contexts(changed)["p1"])
        missing = copy.deepcopy(self.game)
        del missing["decks"]["p1"]
        self.assertEqual(D.original_contexts(missing)["p1"][0, 3], 0)
        native = copy.deepcopy(self.game)
        native["decks"]["p1"] = {"deck": native["decks"]["p1"],
                                   "sideboard": [{"id": "SOR_002", "count": 50}]}
        np.testing.assert_array_equal(context["p1"], D.original_contexts(native)["p1"])

    def test_independent_context_survives_trajectory_and_tmax_packing(self):
        source = self.root / "synthetic.jsonl.gz"
        rows = [self.game]
        for i, seat in enumerate(("p1", "p2", "p1")):
            rows.append({"t": "d", "you": seat, "seq": i, "i": 0,
                         "state": {"players": {"p1": {"deck": 40}, "p2": {"deck": 40}}},
                         "prompt": {"type": "actionWindow", "actionWindow": True},
                         "actions": [{"kind": "button", "label": "Pass", "arg": "pass"}]})
        rows.append({"t": "end", "winner": "p1", "seed": 73})
        with gzip.open(source, "wt") as out:
            out.write("\n".join(json.dumps(r) for r in rows) + "\n")
        raw = self.root / "raw.npz"
        command = [sys.executable, str(JEPA / "data.py"), "--out", str(raw), "--workers", "1",
                   "--card-data", str(self.root / "no-card-folder"), "--own-deck", "original",
                   "--own-deck-cards", str(self.cards), str(source)]
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        packed = self.root / "packed"
        subprocess.run([sys.executable, str(JEPA / "pack_data.py"), "--replays", str(raw),
                        "--out-dir", str(packed), "--tmax", "1"],
                       check=True, capture_output=True, timeout=30)
        with np.load(raw) as a, np.load(packed / "pack-r.npz") as b:
            self.assertEqual(b["tok_ids"].shape, (3, 1))
            self.assertEqual(b["own_deck"].shape, (3, 2, O.INPUT_DIM))
            np.testing.assert_array_equal(a["own_deck"], b["own_deck"])
            np.testing.assert_array_equal(b["own_deck"][0], b["own_deck"][2])
            self.assertFalse(np.array_equal(b["own_deck"][0], b["own_deck"][1]))
            self.assertEqual(b["seat"].tolist(), [0, 1, 0])
        # The opt-in path must not appear in a legacy preparation.
        command = command[:command.index("--own-deck")] + [str(source)]
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        with np.load(raw) as legacy:
            self.assertNotIn("own_deck", legacy.files)


if __name__ == "__main__":
    unittest.main()
