"""The oracle yardstick (branch_train.py) on raw branch arrays (branch_prep.py), for either JEPA format:
over the moves of each branch point, does V(ẑ_h(move)) rank them like V(z(real future after the move))?

python3 yardstick.py <model.safetensors> <branches.npz> [--judge judge.npz]   (the held-out points tx_train_torch.py uses)

The real futures are judged by the model's own value head unless --judge gives one evaluator's scores (judge_prep.py);
only a fixed judge makes top-1 rates comparable between models.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
import tx_model as X  # noqa: E402


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def encode(net, st, ids, ft, mk, chunk=2048):
    out = []
    for k in range(0, len(st), chunk):
        out.append(net.encode(st[k:k + chunk], ids[k:k + chunk].astype(np.int64), ft[k:k + chunk].astype(np.float32), mk[k:k + chunk].astype(np.float32)))
    return np.concatenate(out) if out else np.zeros((0, M.D), np.float32)


# horizon -> (target arrays prefix, mask) in the branch arrays
TARGETS = {1: ("h1", "m1"), 4: ("h4", "m4"), "s": ("st", "mt")}


def imagine(net, B, p):
    """ẑ for every move of point p: [n, len(horizons), D]"""
    n = int(B["nmove"][p])
    args = (B["state"][p:p + 1], B["ids"][p:p + 1].astype(np.int64), B["feats"][p:p + 1].astype(np.float32), B["mask"][p:p + 1].astype(np.float32))
    act, aid = B["act"][p, :n], B["aid"][p, :n].astype(np.int64)
    if isinstance(net, X.NumpyTx):
        _, pr = net.forward(*args, act[None], aid[None])
        return pr[0]  # [n, len(net.horizons), D]
    z = net.encode(*args)
    av = net.action(act, aid)
    return np.stack([net.predict(z, av, 1), net.predict(z, av, 4)], 1)


def _score(ims, hi, real, m, B, idx):
    """top-1 / chance / Spearman of the imagined values at horizon index hi against real values `real[(p, k)]`"""
    top, chance, rho, sp_im, sp_re = [], [], [], [], []
    for p in idx:
        p = int(p)
        n = int(B["nmove"][p])
        okk = [k for k in range(n) if (B[m][p, k] > 0 and (p, k) in real) or B["over"][p, k] >= 0]
        if len(okk) < 2:
            continue
        im = ims[p][okk, hi]
        re = np.array([real[(p, k)] if B[m][p, k] > 0 and (p, k) in real else float(B["over"][p, k]) for k in okk])
        best_re = set(np.flatnonzero(re >= re.max() - 1e-6))
        best_im = np.flatnonzero(im >= im.max() - 1e-6)
        top.append(np.mean([i in best_re for i in best_im]))
        chance.append(len(best_re) / len(re))
        r = spearman(im, re)
        if r is not None:
            rho.append(r)
        sp_im.append(im.std())
        sp_re.append(re.std())
    if not top:
        return None
    return {"points": len(top), "top1": float(np.mean(top)), "chance": float(np.mean(chance)),
            "rho_median": float(np.median(rho)), "spread_imagined": float(np.median(sp_im)), "spread_real": float(np.median(sp_re))}


def yardstick(net, B, idx, judge=None):
    """{"h1": ..., "h4": ..., "hs": ...}: each horizon's imagined ranking against the real futures at that horizon.
    judge None: the real futures are scored by the model's own value head (so the judge differs between models).
    judge {1: ev1, 4: ev4, "s": evt} (judge_prep.py's logits): one fixed judge for every model, plus "h<h>_vs_settled":
    each horizon's imagined ranking against the judge's score of the board where each move really settled."""
    all_hs = net.horizons if isinstance(net, X.NumpyTx) else [1, 4]
    real = {}
    for h, (t, m) in TARGETS.items():
        if m not in B or (judge is None and h not in all_hs) or (judge is not None and judge.get(h) is None):
            continue
        sel = [(p, k) for p in idx for k in range(int(B["nmove"][p])) if B[m][p, k] > 0]
        if not sel:
            real[h] = {}
            continue
        ps, ks = np.array([s[0] for s in sel]), np.array([s[1] for s in sel])
        if judge is None:
            z = encode(net, B[f"{t}_state"][ps, ks], B[f"{t}_ids"][ps, ks], B[f"{t}_feats"][ps, ks], B[f"{t}_mask"][ps, ks])
            v = M.sigmoid(net.value(z))
        else:
            v = M.sigmoid(judge[h][ps, ks])
        real[h] = {(int(p), int(k)): float(x) for p, k, x in zip(ps, ks, v) if np.isfinite(x)}
    ims = {int(p): M.sigmoid(net.value(imagine(net, B, p))) for p in idx}  # [n, len(all_hs)]
    res = {}
    for h in all_hs:
        if h in real:
            r = _score(ims, all_hs.index(h), real[h], TARGETS[h][1], B, idx)
            if r:
                res[f"h{h}"] = r
        if judge is not None and h != "s" and "s" in real:
            r = _score(ims, all_hs.index(h), real["s"], TARGETS["s"][1], B, idx)
            if r:
                res[f"h{h}_vs_settled"] = r
    return res


def held_points(B, seed=0):
    games = np.unique(B["game"])
    held = set(np.random.default_rng(seed + 1).choice(games, max(1, int(len(games) * 0.1)), replace=False).tolist())
    return np.flatnonzero(np.isin(B["game"], list(held)))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("branches")
    ap.add_argument("--judge", default=None, help="judge_prep.py's output for these branches: grade every model by one evaluator")
    a = ap.parse_args()
    net, meta = X.load(a.model)
    B = dict(np.load(a.branches))
    idx = held_points(B)
    judge = None
    if a.judge:
        J = np.load(a.judge)
        if not np.array_equal(J["game"], B["game"]):
            raise SystemExit(f"{a.judge} was made from other branch data")
        idx = idx[J["judged"][idx]]
        judge = {1: J["ev1"], 4: J["ev4"], "s": J["evt"]}
    for h, v in yardstick(net, B, idx, judge).items():
        print(f"{h}: top-1 {v['top1']:.3f} (chance {v['chance']:.3f}) median rho {v['rho_median']:.2f} "
              f"spread imagined {v['spread_imagined'] * 100:.1f} / real {v['spread_real'] * 100:.1f} pts ({v['points']} points)")
