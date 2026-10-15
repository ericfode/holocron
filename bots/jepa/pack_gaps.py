"""Action gaps of branch packs, for tx_train_torch.py --gap-weight: <pack>.gap.npy next to each pack.

python3 pack_gaps.py packs/b-0.npz [packs/b-1.npz ...] [--model models/tx-s10a-e.safetensors]

A point's action gap is its best move's real value minus its worst move's: each move is worth the model's value of the
board where it really settled (V(z(settled board)), as yardstick.py judges the settled horizon), or the game's result
when the game ended first. Points with fewer than two such moves get 0. The default judge is tx-s10a-e, the model whose
value head was fitted to the evaluator (fit_veval.py), as in the pivotal-moments runs (notes/pivots/pack-gaps.txt).
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
import tx_model as X  # noqa: E402
from yardstick import encode  # noqa: E402


def gaps(net, B):
    ps, ks = np.nonzero(B["mt"] > 0)
    v = np.full(B["mt"].shape, np.nan, np.float32)
    if len(ps):
        v[ps, ks] = M.sigmoid(net.value(encode(net, B["st_state"][ps, ks], B["st_ids"][ps, ks], B["st_feats"][ps, ks], B["st_mask"][ps, ks])))
    v = np.where((B["mt"] == 0) & (B["over"] >= 0), B["over"], v)  # a move whose game ended before it settled
    v[np.arange(v.shape[1])[None, :] >= B["nmove"][:, None]] = np.nan
    ok = np.isfinite(v).sum(1) >= 2
    g = np.zeros(len(v), np.float32)
    g[ok] = np.nanmax(v[ok], 1) - np.nanmin(v[ok], 1)
    return g, len(ps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("packs", nargs="+")
    ap.add_argument("--model", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "tx-s10a-e.safetensors"))
    a = ap.parse_args()
    net, _ = X.load(a.model)
    for f in a.packs:
        t = time.time()
        B = dict(np.load(f))
        g, boards = gaps(net, B)
        out = f.replace(".npz", ".gap.npy")
        np.save(out, g)
        q = np.percentile(g[g > 0], [50, 80, 95]) * 100 if (g > 0).any() else [0, 0, 0]
        print(f"{os.path.basename(f)}: {len(g)} points, {boards} settled boards in {time.time() - t:.0f}s; gap median {q[0]:.1f}, "
              f"80th {q[1]:.1f}, 95th {q[2]:.1f} pts; {np.mean(g > 0.10) * 100:.0f}% of points over 10 pts -> {out}")


if __name__ == "__main__":
    main()
