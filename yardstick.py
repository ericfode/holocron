"""The oracle yardstick (branch_train.py) on raw branch arrays (branch_prep.py), for either JEPA format:
over the moves of each branch point, does V(ẑ_h(move)) rank them like V(z(real future after the move))?

python3 yardstick.py <model.safetensors> <branches.npz> [--held-seed 1]   (the held-out points tx_train.py uses)
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


def imagine(net, B, p):
    """ẑ for every move of point p: [n, 2, D]"""
    n = int(B["nmove"][p])
    args = (B["state"][p:p + 1], B["ids"][p:p + 1].astype(np.int64), B["feats"][p:p + 1].astype(np.float32), B["mask"][p:p + 1].astype(np.float32))
    act, aid = B["act"][p, :n], B["aid"][p, :n].astype(np.int64)
    if isinstance(net, X.NumpyTx):
        _, pr = net.forward(*args, act[None], aid[None])
        return pr[0]
    z = net.encode(*args)
    av = net.action(act, aid)
    return np.stack([net.predict(z, av, 1), net.predict(z, av, 4)], 1)


def yardstick(net, B, idx):
    res = {}
    real = {}
    for h in ("1", "4"):
        sel = [(p, k) for p in idx for k in range(int(B["nmove"][p])) if B["m" + h][p, k] > 0]
        if sel:
            ps, ks = np.array([s[0] for s in sel]), np.array([s[1] for s in sel])
            z = encode(net, B[f"h{h}_state"][ps, ks], B[f"h{h}_ids"][ps, ks], B[f"h{h}_feats"][ps, ks], B[f"h{h}_mask"][ps, ks])
            v = M.sigmoid(net.value(z))
            real[h] = {(int(p), int(k)): float(x) for p, k, x in zip(ps, ks, v)}
        else:
            real[h] = {}
    ims = {int(p): M.sigmoid(net.value(imagine(net, B, p))) for p in idx}  # [n, 2]
    for hi, h in enumerate(("1", "4")):
        top, chance, rho, sp_im, sp_re = [], [], [], [], []
        for p in idx:
            p = int(p)
            n = int(B["nmove"][p])
            okk = [k for k in range(n) if B["m" + h][p, k] > 0 or B["over"][p, k] >= 0]
            if len(okk) < 2:
                continue
            im = ims[p][okk, hi]
            re = np.array([real[h][(p, k)] if B["m" + h][p, k] > 0 else float(B["over"][p, k]) for k in okk])
            best_re = set(np.flatnonzero(re >= re.max() - 1e-6))
            best_im = np.flatnonzero(im >= im.max() - 1e-6)
            top.append(np.mean([i in best_re for i in best_im]))
            chance.append(len(best_re) / len(re))
            r = spearman(im, re)
            if r is not None:
                rho.append(r)
            sp_im.append(im.std())
            sp_re.append(re.std())
        res[f"h{h}"] = {"points": len(top), "top1": float(np.mean(top)), "chance": float(np.mean(chance)),
                        "rho_median": float(np.median(rho)), "spread_imagined": float(np.median(sp_im)), "spread_real": float(np.median(sp_re))}
    return res


def held_points(B, seed=0):
    games = np.unique(B["game"])
    held = set(np.random.default_rng(seed + 1).choice(games, max(1, int(len(games) * 0.1)), replace=False).tolist())
    return np.flatnonzero(np.isin(B["game"], list(held)))


if __name__ == "__main__":
    net, meta = X.load(sys.argv[1])
    B = dict(np.load(sys.argv[2]))
    idx = held_points(B)
    for h, v in yardstick(net, B, idx).items():
        print(f"{h}: top-1 {v['top1']:.3f} (chance {v['chance']:.3f}) median rho {v['rho_median']:.2f} "
              f"spread imagined {v['spread_imagined'] * 100:.1f} / real {v['spread_real'] * 100:.1f} pts ({v['points']} points)")
