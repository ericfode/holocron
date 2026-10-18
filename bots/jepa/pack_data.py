"""Compressed training packs for tx_train_torch.py (card tokens cut to --tmax, the rest unchanged).

python3 pack_data.py --replays data/jepa/replays.npz --branches data/jepa/branch-real.npz --out-dir <dir> [--tmax 24]
    [--rank data/jepa/rank-v1-ev.npz --tok data/jepa/rank-v1-tok.npz] [--name pack-b]
Writes <dir>/pack-r.npz (recorded rows) and <dir>/<name>.npz (branch points), each about 50 MB for 3,000 branch games,
each only when its input is given (so a big branch set can be packed in parts: tx_train_torch.py joins them), and with --rank
<dir>/pack-e.npz: the rank data's settled positions with the fitted evaluator's logit (tx_train_torch.py --pack-e) and
whether they belong to a held-out game (rank_train.py's split, which fit_veval.py measures on).
"""
import argparse
import os

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--replays", default=None)
ap.add_argument("--branches", default=None)
ap.add_argument("--name", default="pack-b", help="file name of the branch pack")
ap.add_argument("--out-dir", required=True)
ap.add_argument("--tmax", type=int, default=24)
ap.add_argument("--rank", default=None)
ap.add_argument("--tok", default=None)
a = ap.parse_args()
T = a.tmax
os.makedirs(a.out_dir, exist_ok=True)
written = []
if a.replays:
    with np.load(a.replays) as z:
        r = {k: z[k] for k in ("state", "act", "aid", "win", "game", "nxt1", "nxt4")}
        # Deck context has independent capacity. It must never be sliced by
        # --tmax or reconstructed from the older unseen/omniscient label arrays.
        if "own_deck" in z.files:
            if z["own_deck"].shape != (len(r["state"]), 2, 207):
                raise ValueError("own_deck must have shape [rows, 2, 207]")
            r["own_deck"] = z["own_deck"].astype(np.float32)
            for key in ("gid", "seat", "seq"):
                if key in z.files:
                    r[key] = z[key]
        r["tok_ids"] = z["tok_ids"][:, :T]
        r["tok_feats"] = z["tok_feats"][:, :T]
        r["tok_mask"] = z["tok_mask"][:, :T]
    r["win"] = r["win"].astype(np.int8)
    np.savez_compressed(os.path.join(a.out_dir, "pack-r.npz"), **r)
    written.append("pack-r.npz")
if a.branches:
    b = dict(np.load(a.branches))
    for k in list(b):
        if k.endswith("ids") or k.endswith("mask"):
            b[k] = b[k][..., :T]
        elif k.endswith("feats"):
            b[k] = b[k][..., :T, :]
    np.savez_compressed(os.path.join(a.out_dir, a.name + ".npz"), **b)
    written.append(a.name + ".npz")
if a.rank:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rank_train as RT
    data = RT.Data(a.rank)
    tok = np.load(a.tok)
    n = len(tok["ids"])
    ev = np.zeros(n, np.float32)
    has = np.zeros(n, bool)
    held = np.zeros(n, bool)
    for w in range(len(data.win_lo)):
        z = data.leaf_z[data.win_lo[w]:data.win_hi[w]]
        e = data.leaf_ev[data.win_lo[w]:data.win_hi[w]]
        live = z >= 0
        ev[z[live]] = e[live]
        has[z[live]] = True
        held[z[live]] = data.is_held[w]
    np.savez_compressed(os.path.join(a.out_dir, "pack-e.npz"), state=tok["state"].astype(np.float32), tok_ids=tok["ids"][:, :T],
                        tok_feats=tok["feats"][:, :T], tok_mask=tok["mask"][:, :T], ev=ev, has=has, held=held)
    written.append("pack-e.npz")
for f in written:
    print(f, os.path.getsize(os.path.join(a.out_dir, f)) // 1_000_000, "MB")
