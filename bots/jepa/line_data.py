"""Lines from the planner's logs (jepa_bot.py --plan-log with line tokens) for a line-conditioned predictor.

    python3 bots/jepa/line_data.py --model bots/jepa/models/tx-t10.safetensors --out data/lines/pl1.npz data/plog/pl1

Per planned window: the latent of the position (z), and for each root move its lines lead with, the model's own
prediction of where that move settles (zb: what the bot without the simulator scores today, root move only). Per judged
line with a real settled board: the line as action tokens (my choices from the root move on, at most --steps of them),
the latent of the real settled board the simulation reached (z_real, the model's encoder, as the planner judges it),
and the window and game it belongs to. One process per log file.
"""
import argparse
import glob
import json
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402
import model as M  # noqa: E402
import tx_model as X  # noqa: E402

WAIT_PROMPT = {"type": "actionWindow", "actionWindow": True, "selectCardMode": None, "selected": []}
A = None


def records(path):
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


def encode_batch(net, T, msgs, db):
    es = [F.encode(m, db) for m in msgs]
    return net.encode(np.stack([e["state"] for e in es]), np.stack([e["tok_ids"][:T] for e in es]).astype(np.int64),
                      np.stack([e["tok_feats"][:T] for e in es]).astype(np.float32), np.stack([e["tok_mask"][:T] for e in es]).astype(np.float32))


def one_file(args):
    path, fi = args
    net, meta = X.load(A.model)
    T = int(meta.get("tmax", 24))
    hs = net.horizons.index("s")
    db = F.load_cards()
    L = A.steps
    out = {k: [] for k in ("z", "w_game", "w_round", "zb", "z_real", "v_log", "act", "aid", "lmask", "llen", "win", "root_slot")}
    games = 0
    cur, you = [], None
    for r in records(path):
        t = r.get("t")
        if t == "hello":
            cur, you = [], r.get("you")
        elif t == "pw":
            cur.append(r)
        elif t == "over" and you is not None:
            if r.get("winner") not in ("p1", "p2"):
                cur = []
                continue
            g = fi * 100000 + games
            games += 1
            for w in cur:
                msg = w["msg"]
                lines = [e for e in w["leaves"] if e.get("pos") and e.get("line")]
                if len(lines) < 2:
                    continue
                roots = sorted({int(e["move"]) for e in lines})
                e0 = F.encode(msg, db)
                act = e0["actions"][roots][None].astype(np.float32)
                aid = e0["aids"][roots][None].astype(np.int64)
                z, pr = net.forward(e0["state"][None], e0["tok_ids"][None, :T].astype(np.int64), e0["tok_feats"][None, :T].astype(np.float32),
                                    e0["tok_mask"][None, :T].astype(np.float32), act, aid, hsel=[hs])
                wi = len(out["z"])
                out["z"].append(z[0]); out["w_game"].append(g); out["w_round"].append(w.get("round") or 0)
                pos = []
                for e in lines:
                    p = e["pos"]
                    pos.append({"you": msg["you"], "prompt": p["prompt"], "state": p["state"],
                                "actions": p["actions"] if p.get("actions") is not None else msg["actions"]})
                zr = encode_batch(net, T, pos, db)
                for k, e in enumerate(lines):
                    toks = e["line"][:L]
                    a = np.zeros((L, F.ACTION_DIM), np.float16)
                    ai = np.zeros(L, np.int64)
                    m = np.zeros(L, np.float32)
                    for j, (tid, row) in enumerate(toks):
                        a[j] = row
                        ai[j] = tid
                        m[j] = 1.0
                    out["zb"].append(pr[0, roots.index(int(e["move"])), 0]); out["z_real"].append(zr[k]); out["v_log"].append(e["v"])
                    out["act"].append(a); out["aid"].append(ai); out["lmask"].append(m); out["llen"].append(len(e["line"]))
                    out["win"].append(wi); out["root_slot"].append(roots.index(int(e["move"])))
            cur = []
    return out, games


def main():
    global A
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=4, help="action tokens kept per line (my choices from the root move on)")
    ap.add_argument("--procs", type=int, default=14)
    A = ap.parse_args()
    files = sorted(f for d in A.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    with Pool(min(A.procs, len(files)), initializer=_init, initargs=(A,)) as pool:
        parts = pool.map(one_file, [(f, i) for i, f in enumerate(files)])
    res = {}
    off = 0
    for out, _ in parts:
        out["win"] = [w + off for w in out["win"]]
        off += len(out["z"])
        for k, v in out.items():
            res.setdefault(k, []).extend(v)
    games = sum(g for _, g in parts)
    arr = {k: np.asarray(v) for k, v in res.items()}
    arr["z"] = arr["z"].astype(np.float32)
    os.makedirs(os.path.dirname(os.path.abspath(A.out)), exist_ok=True)
    np.savez(A.out, **arr)
    ll = arr["llen"]
    print(f"{len(files)} logs, {games} decided games, {len(arr['z'])} windows, {len(ll)} lines (with follow-ups: {(ll > 1).mean() * 100:.0f}%) -> {A.out}",
          file=sys.stderr)


def _init(a):
    global A
    A = a


if __name__ == "__main__":
    main()
