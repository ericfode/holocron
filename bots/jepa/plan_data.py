"""Training data from the planner's logs (jepa_bot.py --plan-log): one judge pack and one policy pack.

    python3 bots/jepa/plan_data.py --out data/plan/pd1 data/plog/pd1

<out>-judge.npz  per planned window, the settled board of the picked move's best line (the board the planner judged
                 best, which the game then followed), from the mover's seat, encoded as the planner encodes it, with
                 win = did the mover win the game. Same fields as data.py packs (state, tok_ids, tok_feats, tok_mask,
                 win, game), so fit_value.py reads it with --pack.
<out>-policy.npz per planned window, the window's position and up to K candidate moves (the imagined best first, the
                 planner's pick always in), with the pick, the imagined scores and the planner's scores: data for a
                 policy head that copies the planner's choice (policy_train.py).
A game is one log file's hello..over run; games without a result are left out. `game` numbers games in file order.
"""
import argparse
import glob
import json
import os
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

WAIT_PROMPT = {"type": "actionWindow", "actionWindow": True, "selectCardMode": None, "selected": []}


def records(path):
    """JSON records of a gzip log, tolerant of a cut-off last member."""
    raw = open(path, "rb").read()
    text = b""
    while raw:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            text += d.decompress(raw)
        except zlib.error:
            break
        raw = d.unused_data
    for line in text.decode("utf8", "ignore").split("\n"):
        if line.strip():
            try:
                yield json.loads(line)
            except ValueError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=24, help="candidate moves per window in the policy pack")
    a = ap.parse_args()
    db = F.load_cards()
    files = sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    J = {"state": [], "ids": [], "feats": [], "mask": [], "win": [], "game": []}
    P = {"state": [], "ids": [], "feats": [], "mask": [], "act": [], "aid": [], "nmove": [], "pick": [], "imag": [], "plan": [], "game": [], "round": []}
    games = kept = windows = 0
    for f in files:
        cur, you = [], None
        for r in records(f):
            t = r.get("t")
            if t == "hello":
                cur, you = [], r.get("you")
            elif t == "pw":
                cur.append(r)
            elif t == "over" and you is not None:
                games += 1
                if r.get("winner") not in ("p1", "p2"):
                    cur = []
                    continue
                won = float(r["winner"] == you)
                g = kept
                kept += 1
                for w in cur:
                    msg = w["msg"]
                    pick = int(w["pick"])
                    # the judge: the picked move's best judged line
                    best = None
                    for e in w["leaves"]:
                        if e.get("move") == pick and e.get("pos") and e.get("v") is not None and (best is None or e["v"] > best["v"]):
                            best = e
                    if best is not None:
                        pos = best["pos"]
                        m = {"you": msg["you"], "prompt": pos["prompt"], "state": pos["state"],
                             "actions": pos["actions"] if pos.get("actions") is not None else msg["actions"]}
                        e = F.encode(m, db)
                        J["state"].append(e["state"]); J["ids"].append(e["tok_ids"]); J["feats"].append(e["tok_feats"]); J["mask"].append(e["tok_mask"])
                        J["win"].append(won); J["game"].append(g)
                    # the policy: the window and its candidates
                    e = F.encode(msg, db)
                    imag = np.asarray(w["imagined"], np.float32)
                    order = [int(i) for i in np.argsort(-imag)]
                    cand = order[:a.k]
                    if pick not in cand:
                        cand = cand[:a.k - 1] + [pick]
                    k = len(cand)
                    act = np.zeros((a.k, e["actions"].shape[1]), np.float32)
                    aid = np.zeros(a.k, np.int64)
                    im = np.zeros(a.k, np.float32)
                    pl = np.full(a.k, -1.0, np.float32)
                    act[:k] = e["actions"][cand]
                    aid[:k] = e["aids"][cand]
                    im[:k] = imag[cand]
                    pl[:k] = np.asarray(w["planned"], np.float32)[cand]
                    P["state"].append(e["state"]); P["ids"].append(e["tok_ids"]); P["feats"].append(e["tok_feats"]); P["mask"].append(e["tok_mask"])
                    P["act"].append(act); P["aid"].append(aid); P["nmove"].append(k); P["pick"].append(cand.index(pick))
                    P["imag"].append(im); P["plan"].append(pl); P["game"].append(g); P["round"].append(w.get("round") or 0)
                    windows += 1
                cur = []
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez_compressed(a.out + "-judge.npz", state=np.stack(J["state"]), tok_ids=np.stack(J["ids"]), tok_feats=np.stack(J["feats"]),
                        tok_mask=np.stack(J["mask"]), win=np.asarray(J["win"], np.int64), game=np.asarray(J["game"], np.int64))
    np.savez_compressed(a.out + "-policy.npz", state=np.stack(P["state"]), tok_ids=np.stack(P["ids"]), tok_feats=np.stack(P["feats"]),
                        tok_mask=np.stack(P["mask"]), act=np.stack(P["act"]), aid=np.stack(P["aid"]), nmove=np.asarray(P["nmove"]),
                        pick=np.asarray(P["pick"]), imag=np.stack(P["imag"]), plan=np.stack(P["plan"]), game=np.asarray(P["game"]),
                        round=np.asarray(P["round"]))
    print(f"{len(files)} logs, {games} games ({kept} with a winner), {windows} planned windows, {len(J['win'])} judged boards "
          f"-> {a.out}-judge.npz, {a.out}-policy.npz", file=sys.stderr)


if __name__ == "__main__":
    main()
