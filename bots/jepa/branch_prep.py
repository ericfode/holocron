"""Branch data (branches.js shards) -> raw encodings for training a JEPA from scratch on them.

python3 branch_prep.py --out data/jepa/branch-real.npz data/branch/real-rush [more dirs]
Per branch point (up to K moves): the root's state and card tokens, each move's action row, and the encoded h1, h4 and
settled (st) futures (state + tokens), with masks m1, m4, mt; a move that ends the game first has `over` = 1 win / 0 loss for the mover.
"""
import argparse
import glob
import gzip
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

K = 12
T = F.MAX_TOKENS
DB = None
# a settled board is encoded the way jepa_bot.py's planner encodes a position where the opponent acts: as my action
# window with the root's actions, so only the board differs between a point's moves
WAIT_PROMPT = {"type": "actionWindow", "actionWindow": True, "selectCardMode": None, "selected": []}


def _lines(f):
    """Lines of whole games; a shard cut off mid-write (a stopped run) ends at its last complete game."""
    game = []
    try:
        with gzip.open(f, "rt") as fh:
            for line in fh:
                game.append(line)
                if line.startswith('{"t":"end"'):
                    yield from game
                    game = []
    except (EOFError, OSError, ValueError):
        pass


def enc_file(f):
    global DB
    if DB is None:
        DB = F.load_cards()
    pts = []
    for line in _lines(f):
            o = json.loads(line)
            if o["t"] != "b" or len(o["br"]) < 2:
                continue
            if o.get("rollout") and os.environ.get("BRANCH_PREP_BASE_ONLY"):
                continue  # --base-only: leave out the extra passes of branches.js --extra-rollouts
            e = F.encode(o, DB)
            p = {"seed": o["seed"], "root": (e["state"], e["tok_ids"], e["tok_feats"], e["tok_mask"]),
                 "act": [], "aid": [], "h1": [], "h4": [], "st": [], "over": []}
            for b in o["br"][:K]:
                p["act"].append(e["actions"][b["i"]])
                p["aid"].append(int(e["aids"][b["i"]]))
                for h in ("h1", "h4"):
                    if b.get(h):
                        x = F.encode(b[h], DB)
                        p[h].append((x["state"], x["tok_ids"], x["tok_feats"], x["tok_mask"]))
                    else:
                        p[h].append(None)
                if b.get("st"):
                    x = F.encode({"you": o["you"], "prompt": WAIT_PROMPT, "state": b["st"]["state"], "actions": o["actions"]}, DB)
                    p["st"].append((x["state"], x["tok_ids"], x["tok_feats"], x["tok_mask"]))
                else:
                    p["st"].append(None)
                ov = b.get("over")
                p["over"].append(1.0 if ov == o["you"] else (0.0 if ov in ("p1", "p2") else -1.0))
            pts.append(p)
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--base-only", action="store_true", help="leave out the extra passes of branches.js --extra-rollouts (a control)")
    a = ap.parse_args()
    if a.base_only:
        os.environ["BRANCH_PREP_BASE_ONLY"] = "1"  # read by the worker processes (inherited under fork and spawn)
    files = sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    with Pool(a.procs) as pool:
        pts = [p for ps in pool.map(enc_file, files) for p in ps]
    P = len(pts)
    TD = F.TOKEN_DIM
    out = {"state": np.zeros((P, F.STATE_DIM), np.float32), "ids": np.zeros((P, T), np.int16), "feats": np.zeros((P, T, TD), np.float16),
           "mask": np.zeros((P, T), np.uint8), "act": np.zeros((P, K, F.ACTION_DIM), np.float32), "aid": np.zeros((P, K), np.int32),
           "nmove": np.zeros(P, np.int32), "over": np.full((P, K), -1.0, np.float32), "game": np.zeros(P, np.int64)}
    for h in ("h1", "h4", "st"):
        out[h + "_state"] = np.zeros((P, K, F.STATE_DIM), np.float32)
        out[h + "_ids"] = np.zeros((P, K, T), np.int16)
        out[h + "_feats"] = np.zeros((P, K, T, TD), np.float16)
        out[h + "_mask"] = np.zeros((P, K, T), np.uint8)
        out["m" + h[1]] = np.zeros((P, K), np.float32)  # m1, m4, mt
    for i, p in enumerate(pts):
        s, ids, ft, m = p["root"]
        out["state"][i], out["ids"][i], out["feats"][i], out["mask"][i] = s, ids, ft, m
        out["game"][i] = p["seed"]
        n = len(p["act"])
        out["nmove"][i] = n
        out["act"][i, :n] = np.stack(p["act"])
        out["aid"][i, :n] = p["aid"]
        out["over"][i, :n] = p["over"]
        for h in ("h1", "h4", "st"):
            for k, x in enumerate(p[h]):
                if x is not None:
                    out[h + "_state"][i, k], out[h + "_ids"][i, k], out[h + "_feats"][i, k], out[h + "_mask"][i, k] = x
                    out["m" + h[1]][i, k] = 1.0
    np.savez(a.out, **out)
    print(f"{P} branch points, {int(out['m1'].sum())} h1, {int(out['m4'].sum())} h4 and {int(out['mt'].sum())} settled targets, "
          f"{int((out['over'] >= 0).sum())} moves that end the game first -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
