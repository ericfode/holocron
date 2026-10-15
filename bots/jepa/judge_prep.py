"""One fixed judge for the yardstick: a lab/eval evaluator's score of every real future in branch data.

python3 judge_prep.py --branches data/jepa/branch-real-st.npz --out data/jepa/judge-real-st.npz data/branch/real-rush-st
    [--eval linear-deck-g4] [--decks decks/ash-meta-2026-09.json] [--all]

yardstick.py's own judge is each model's value head on its own encoding of the real futures, so two models are graded
by different judges and their top-1 rates do not compare. This scores the same futures (h1, h4 and the settled board)
with one evaluator, as the mover, so every model is graded the same way (`yardstick.py --judge`). Reads the shards in
branch_prep.py's order and checks it against --branches; by default only the held-out points yardstick.py uses.
Writes ev1, ev4, evt [P, K]: the evaluator's logit, NaN where the move has no such future.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import branch_prep as BP  # noqa: E402
import yardstick as Y  # noqa: E402
from jepa_bot import EvalHelper  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--branches", required=True, help="branch_prep.py's output for the same dirs (point order check, held-out points)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--eval", default="linear-deck-g4")
    ap.add_argument("--decks", default="decks/ash-meta-2026-09.json", help="deck lists the branch games name (branches.js --decks)")
    ap.add_argument("--all", action="store_true", help="every point, not only the held-out ones")
    a = ap.parse_args()
    B = np.load(a.branches)
    game, P = B["game"], len(B["game"])
    want = np.ones(P, bool) if a.all else np.isin(np.arange(P), Y.held_points({"game": game}))
    lists = {d["metadata"]["name"]: [c["id"] for c in d["deck"] for _ in range(int(c.get("count", 1)))] for d in json.load(open(a.decks))}
    helper = EvalHelper(a.eval)
    out = {k: np.full((P, BP.K), np.nan, np.float32) for k in ("ev1", "ev4", "evt")}
    files = sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    i = 0
    flat = None
    for f in files:
        for line in BP._lines(f):
            o = json.loads(line)
            if o["t"] == "game":
                names = o.get("decks")
                # deck names (branches.js), or whole deck lists (replay_branches.js data made before it wrote names)
                deck = lambda d: lists[d] if isinstance(d, str) else [c["id"] for c in d["deck"] for _ in range(int(c.get("count", 1)))]
                flat = {"p1": deck(names[0]), "p2": deck(names[1])} if names else None
                continue
            if o["t"] != "b" or len(o["br"]) < 2:
                continue
            if game[i] != o["seed"]:
                raise SystemExit(f"point {i}: seed {o['seed']} in the shards, {game[i]} in {a.branches} (different dirs or order?)")
            if want[i]:
                you = o["you"]
                opp = "p2" if you == "p1" else "p1"
                states, to_act, where = [], [], []
                for k, b in enumerate(o["br"][:BP.K]):
                    for key, h in (("ev1", "h1"), ("ev4", "h4")):
                        if b.get(h):
                            states.append(b[h]["state"])
                            to_act.append(you)  # the mover's own decision
                            where.append((key, k))
                    if b.get("st"):
                        s = b["st"]["state"]
                        states.append(s)
                        to_act.append(opp if (s or {}).get("phase") == "action" else None)  # as rank_train.py judges a settled move
                        where.append(("evt", k))
                if states:
                    for (key, k), lg in zip(where, helper.logits(you, flat, states, to_act)):
                        out[key][i, k] = lg
            i += 1
    if i != P:
        raise SystemExit(f"{i} points in the shards, {P} in {a.branches}")
    np.savez(a.out, game=game, judged=want, **out)
    print(f"{int(want.sum())} of {P} points judged by {a.eval}: {int(np.isfinite(out['ev1']).sum())} h1, "
          f"{int(np.isfinite(out['ev4']).sum())} h4, {int(np.isfinite(out['evt']).sum())} settled -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
