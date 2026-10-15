"""Tiered branch data (branches.js --macros) -> raw encodings for the round tiers of the transformer JEPA.

python3 tier_prep.py --out data/jepa/tier-0.npz data/branch/tier-0 [more dirs] [--eval linear-deck-g4 --decks decks/ash-meta-2026-09.json]

Per branch point: the root's state and card tokens, the R moves that were played once per macro action (macros.js),
and for each (move, macro) the encoded board where this round's action phase ended (`rd`) and where the next round's
did (`rd2`), with masks mr, mr2 [P, R, C]; `over` [P, R, C] is 1 / 0 when the game ended first (won / lost by the
mover), else -1. `macros` names the C macro actions in order. Boards are encoded as branch_prep.py encodes settled
boards (my action window with the root's actions), so only the board differs between a point's lines.
--eval adds a fixed judge for yardstick.py --tiers: evr, evr2 [P, R, C], the evaluator's logit of every real board as
the mover (NaN where there is none). Judge only test data: it is slow (one evaluator call per point).
"""
import argparse
import glob
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import branch_prep as BP  # noqa: E402
import features as F  # noqa: E402

R = 4
T = F.MAX_TOKENS
TIERS = ("rd", "rd2")
MASK = {"rd": "mr", "rd2": "mr2"}
JUDGE = {"rd": "evr", "rd2": "evr2"}
DB = None


def enc_board(o, state):
    msg = {"you": o["you"], "prompt": BP.WAIT_PROMPT, "state": state, "actions": o["actions"]}
    ids, ft, m = F.encode_tokens(msg, DB)
    return np.asarray(F.encode_state(msg, DB), np.float32), ids, ft, m


def lines_of(o, macros):
    """The point's moves (up to R, in record order) and its usable lines [(move index, macro index, line)]."""
    moves = []
    for m in o.get("mac") or []:
        if m["i"] not in moves:
            moves.append(m["i"])
    moves = moves[:R]
    return moves, [(moves.index(m["i"]), macros.index(m["c"]), m) for m in o.get("mac") or []
                   if m["i"] in moves and m["c"] in macros and not m.get("err")]


def enc_file(job):
    f, macros = job
    global DB
    if DB is None:
        DB = F.load_cards()
    pts = []
    for line in BP._lines(f):
        o = json.loads(line)
        if o["t"] != "b":
            continue
        moves, lines = lines_of(o, macros)
        if not lines:
            continue
        e = F.encode(o, DB)
        p = {"seed": o["seed"], "root": (e["state"], e["tok_ids"], e["tok_feats"], e["tok_mask"]),
             "act": [e["actions"][i] for i in moves], "aid": [int(e["aids"][i]) for i in moves], "lines": []}
        for k, c, m in lines:
            ov = m.get("over")
            line = {"k": k, "c": c, "over": 1.0 if ov == o["you"] else (0.0 if ov in ("p1", "p2") else -1.0)}
            for t in TIERS:
                if m.get(t):
                    line[t] = enc_board(o, m[t]["state"])
            p["lines"].append(line)
        pts.append(p)
    return pts


def judge(a, out, macros):
    """evr / evr2: the evaluator's logit of every real round-end board, as the mover (judge_prep.py's way)."""
    from jepa_bot import EvalHelper  # noqa: E402
    lists = {d["metadata"]["name"]: [c["id"] for c in d["deck"] for _ in range(int(c.get("count", 1)))] for d in json.load(open(a.decks))}
    helper = EvalHelper(a.eval)
    P = len(out["game"])
    for t in TIERS:
        out[JUDGE[t]] = np.full((P, R, len(macros)), np.nan, np.float32)
    i = 0
    flat = None
    for f in sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz"))):
        for line in BP._lines(f):
            o = json.loads(line)
            if o["t"] == "game":
                names = o.get("decks")
                flat = {"p1": lists[names[0]], "p2": lists[names[1]]} if names else None
                continue
            if o["t"] != "b":
                continue
            _, lines = lines_of(o, macros)
            if not lines:
                continue  # as enc_file
            states, where = [], []
            for k, c, m in lines:
                for t in TIERS:
                    if m.get(t):
                        states.append(m[t]["state"])
                        where.append((t, k, c))
            if out["game"][i] != o["seed"]:
                raise SystemExit(f"point {i}: seed {o['seed']} in the shards, {out['game'][i]} encoded")
            if states:
                # a round-end board is the regroup phase: nobody is in the action phase, as rank_train.py judges it
                for (t, k, c), lg in zip(where, helper.logits(o["you"], flat, states, [None] * len(states))):
                    out[JUDGE[t]][i, k, c] = lg
            i += 1
    if i != P:
        raise SystemExit(f"{i} points judged, {P} encoded")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--macros", default="face,trade,hold", help="the macro actions to keep, in this order")
    ap.add_argument("--eval", default=None, help="also judge every real board with this lab/eval evaluator (test data)")
    ap.add_argument("--decks", default="decks/ash-meta-2026-09.json")
    a = ap.parse_args()
    macros = a.macros.split(",")
    C = len(macros)
    files = sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    with Pool(a.procs) as pool:
        pts = [p for ps in pool.map(enc_file, [(f, macros) for f in files]) for p in ps]
    P = len(pts)
    TD = F.TOKEN_DIM
    out = {"state": np.zeros((P, F.STATE_DIM), np.float32), "ids": np.zeros((P, T), np.int16), "feats": np.zeros((P, T, TD), np.float16),
           "mask": np.zeros((P, T), np.uint8), "act": np.zeros((P, R, F.ACTION_DIM), np.float32), "aid": np.zeros((P, R), np.int32),
           "nmove": np.zeros(P, np.int32), "over": np.full((P, R, C), -1.0, np.float32), "game": np.zeros(P, np.int64),
           "macros": np.array(macros)}
    for t in TIERS:
        out[t + "_state"] = np.zeros((P, R, C, F.STATE_DIM), np.float32)
        out[t + "_ids"] = np.zeros((P, R, C, T), np.int16)
        out[t + "_feats"] = np.zeros((P, R, C, T, TD), np.float16)
        out[t + "_mask"] = np.zeros((P, R, C, T), np.uint8)
        out[MASK[t]] = np.zeros((P, R, C), np.float32)
    for i, p in enumerate(pts):
        s, ids, ft, m = p["root"]
        out["state"][i], out["ids"][i], out["feats"][i], out["mask"][i] = s, ids, ft, m
        out["game"][i] = p["seed"]
        n = len(p["act"])
        out["nmove"][i] = n
        out["act"][i, :n] = np.stack(p["act"])
        out["aid"][i, :n] = p["aid"]
        for ln in p["lines"]:
            k, c = ln["k"], ln["c"]
            out["over"][i, k, c] = ln["over"]
            for t in TIERS:
                if t in ln:
                    out[t + "_state"][i, k, c], out[t + "_ids"][i, k, c], out[t + "_feats"][i, k, c], out[t + "_mask"][i, k, c] = ln[t]
                    out[MASK[t]][i, k, c] = 1.0
    if a.eval:
        judge(a, out, macros)
    np.savez(a.out, **out)
    print(f"{P} tier points, {int(out['nmove'].sum())} moves x {C} macros: {int(out['mr'].sum())} round-end and "
          f"{int(out['mr2'].sum())} next-round-end boards, {int((out['over'] >= 0).sum())} lines that end the game first"
          + (f", judged by {a.eval}" if a.eval else "") + f" -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
