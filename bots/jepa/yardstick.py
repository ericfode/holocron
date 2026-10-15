"""The oracle yardstick (branch_train.py) on raw branch arrays (branch_prep.py), for either JEPA format:
over the moves of each branch point, does V(ẑ_h(move)) rank them like V(z(real future after the move))?

python3 yardstick.py <model.safetensors> <branches.npz> [--judge judge.npz]   (the held-out points tx_train_torch.py uses)
python3 yardstick.py <tiered model.safetensors> --tiers <tier_prep.py --eval output>   (round tiers, every point, judged)

The real futures are judged by the model's own value head unless --judge gives one evaluator's scores (judge_prep.py);
only a fixed judge makes top-1 rates comparable between models. regret = the judged win chance lost, on average, by
playing the move the model imagines best; blunders = how often that loss is over 5 points.
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
        _, pr = net.forward(*args, act[None], aid[None], hsel=net.groups[0])
        return pr[0]  # [n, len(base horizons), D]: the move's own horizons (1, 4, s), not the round tiers
    z = net.encode(*args)
    av = net.action(act, aid)
    return np.stack([net.predict(z, av, 1), net.predict(z, av, 4)], 1)


def _score(ims, hi, real, m, B, idx):
    """top-1 / chance / Spearman of the imagined values at horizon index hi against real values `real[(p, k)]`"""
    top, chance, rho, sp_im, sp_re, regret = [], [], [], [], [], []
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
        regret.append(float(re.max() - re[best_im].mean()))  # value lost by playing the imagined best move
        chance.append(len(best_re) / len(re))
        r = spearman(im, re)
        if r is not None:
            rho.append(r)
        sp_im.append(im.std())
        sp_re.append(re.std())
    if not top:
        return None
    regret = np.array(regret)
    return {"points": len(top), "top1": float(np.mean(top)), "chance": float(np.mean(chance)),
            "rho_median": float(np.median(rho)), "spread_imagined": float(np.median(sp_im)), "spread_real": float(np.median(sp_re)),
            "regret": float(regret.mean()), "blunders": float((regret > 0.05).mean())}


def yardstick(net, B, idx, judge=None):
    """{"h1": ..., "h4": ..., "hs": ...}: each horizon's imagined ranking against the real futures at that horizon.
    judge None: the real futures are scored by the model's own value head (so the judge differs between models).
    judge {1: ev1, 4: ev4, "s": evt} (judge_prep.py's logits): one fixed judge for every model, plus "h<h>_vs_settled":
    each horizon's imagined ranking against the judge's score of the board where each move really settled."""
    all_hs = [net.horizons[i] for i in net.groups[0]] if isinstance(net, X.NumpyTx) else [1, 4]
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


TIER_TARGETS = {"r": ("rd", "mr"), "r2": ("rd2", "mr2")}


def tier_yardstick(net, Q, idx, judge=None):
    """Round tiers of a tiered model on tier_prep.py points, per tier t (r: this round's end, r2: the next round's):
    lines  over a point's (move, macro) lines, V(ẑ_t:macro(move)) against the real round-end boards
    macro  per move: is the imagined best macro the real best one
    move   per point, each move worth its best real line: the move whose imagined best line is highest, and as a
           baseline the move the settled horizon (V(ẑ_s), if the model has it) ranks first; regret = real value lost
    judge None: real boards scored by the model's value head; {"r": evr, "r2": evr2}: by one evaluator (logits)."""
    macros = net.macros
    C = len(macros)
    idx = [int(p) for p in idx]
    res = {}
    real = {}
    for t, (h, m) in TIER_TARGETS.items():
        sel = [(p, k, c) for p in idx for k in range(int(Q["nmove"][p])) for c in range(C) if Q[m][p, k, c] > 0]
        v = np.full((len(Q["game"]), Q["act"].shape[1], C), np.nan, np.float32)
        if sel:
            ps, ks, cs = (np.array(x) for x in zip(*sel))
            if judge is None:
                z = encode(net, Q[f"{h}_state"][ps, ks, cs], Q[f"{h}_ids"][ps, ks, cs], Q[f"{h}_feats"][ps, ks, cs], Q[f"{h}_mask"][ps, ks, cs])
                v[ps, ks, cs] = M.sigmoid(net.value(z))
            else:
                v[ps, ks, cs] = M.sigmoid(judge[t][ps, ks, cs])
        real[t] = np.where(Q["over"] >= 0, Q["over"], v)  # a line whose game ended first is worth its result
    s_i = net.horizons.index("s") if "s" in net.horizons else None
    acc = {t: {k: [] for k in ("l_top", "l_chance", "l_rho", "l_regret", "m_top", "m_chance", "mv_top", "mv_chance", "mv_regret", "s_top", "s_regret")}
           for t in TIER_TARGETS}
    for p in idx:
        n = int(Q["nmove"][p])
        args = (Q["state"][p:p + 1], Q["ids"][p:p + 1].astype(np.int64), Q["feats"][p:p + 1].astype(np.float32), Q["mask"][p:p + 1].astype(np.float32))
        _, pr = net.forward(*args, Q["act"][p:p + 1, :n], Q["aid"][p:p + 1, :n].astype(np.int64))
        V = M.sigmoid(net.value(pr[0]))  # [n, len(horizons)]
        for t in TIER_TARGETS:
            im = V[:, [net.horizons.index(f"{t}:{c}") for c in macros]]  # [n, C]
            re = real[t][p, :n]
            a = acc[t]
            ok = np.isfinite(re)
            if ok.sum() >= 2:
                li, lr = im[ok], re[ok]
                best = set(np.flatnonzero(lr >= lr.max() - 1e-6))
                pick = np.flatnonzero(li >= li.max() - 1e-6)
                a["l_top"].append(np.mean([i in best for i in pick]))
                a["l_chance"].append(len(best) / len(lr))
                a["l_regret"].append(float(lr.max() - lr[pick].mean()))
                r = spearman(li, lr)
                if r is not None:
                    a["l_rho"].append(r)
            for k in range(n):
                okc = np.isfinite(re[k])
                if okc.sum() >= 2 and np.ptp(re[k][okc]) > 1e-6:
                    best = set(np.flatnonzero(re[k][okc] >= re[k][okc].max() - 1e-6))
                    pick = np.flatnonzero(im[k][okc] >= im[k][okc].max() - 1e-6)
                    a["m_top"].append(np.mean([i in best for i in pick]))
                    a["m_chance"].append(len(best) / okc.sum())
            mv = np.array([np.nanmax(re[k]) if np.isfinite(re[k]).any() else np.nan for k in range(n)])
            okm = np.flatnonzero(np.isfinite(mv))
            if len(okm) >= 2:
                rv = mv[okm]
                best = set(np.flatnonzero(rv >= rv.max() - 1e-6))
                imv = np.array([np.max(np.where(np.isfinite(re[k]), im[k], -np.inf)) for k in okm])
                pick = np.flatnonzero(imv >= imv.max() - 1e-6)
                a["mv_top"].append(np.mean([i in best for i in pick]))
                a["mv_chance"].append(len(best) / len(rv))
                a["mv_regret"].append(float(rv.max() - rv[pick].mean()))
                if s_i is not None:
                    sv = V[okm, s_i]
                    pick = np.flatnonzero(sv >= sv.max() - 1e-6)
                    a["s_top"].append(np.mean([i in best for i in pick]))
                    a["s_regret"].append(float(rv.max() - rv[pick].mean()))
    for t, a in acc.items():
        if not a["l_top"]:
            continue
        mean = lambda k: float(np.mean(a[k])) if a[k] else float("nan")
        res[t] = {"points": len(a["l_top"]), "lines_top1": mean("l_top"), "lines_chance": mean("l_chance"),
                  "lines_rho_median": float(np.median(a["l_rho"])) if a["l_rho"] else float("nan"), "lines_regret": mean("l_regret"),
                  "macro_moves": len(a["m_top"]), "macro_top1": mean("m_top"), "macro_chance": mean("m_chance"),
                  "move_top1": mean("mv_top"), "move_chance": mean("mv_chance"), "move_regret": mean("mv_regret"),
                  "move_blunders": float((np.array(a["mv_regret"]) > 0.05).mean()) if a["mv_regret"] else float("nan"),
                  "settled_move_top1": mean("s_top"), "settled_move_regret": mean("s_regret"),
                  "settled_move_blunders": float((np.array(a["s_regret"]) > 0.05).mean()) if a["s_regret"] else float("nan")}
    return res


def report_tiers(res, label, out):
    for t, v in res.items():
        print(f"  {label} {t}: lines top-1 {v['lines_top1']:.3f} (chance {v['lines_chance']:.3f}) rho {v['lines_rho_median']:.2f} "
              f"regret {v['lines_regret'] * 100:.2f} pts; macro top-1 {v['macro_top1']:.3f} (chance {v['macro_chance']:.3f}, "
              f"{v['macro_moves']} moves where the macro matters); move pick by tier: top-1 {v['move_top1']:.3f} (chance {v['move_chance']:.3f}) "
              f"regret {v['move_regret'] * 100:.2f} pts, blunders {v['move_blunders'] * 100:.1f}%; by settled horizon: top-1 "
              f"{v['settled_move_top1']:.3f} regret {v['settled_move_regret'] * 100:.2f} pts, blunders {v['settled_move_blunders'] * 100:.1f}% "
              f"({v['points']} points)", file=out)


def held_points(B, seed=0):
    games = np.unique(B["game"])
    held = set(np.random.default_rng(seed + 1).choice(games, max(1, int(len(games) * 0.1)), replace=False).tolist())
    return np.flatnonzero(np.isin(B["game"], list(held)))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("branches", nargs="?")
    ap.add_argument("--judge", default=None, help="judge_prep.py's output for these branches: grade every model by one evaluator")
    ap.add_argument("--tiers", default=None, help="tier_prep.py --eval output: grade the round tiers on all its points")
    ap.add_argument("--all", action="store_true", help="every point of the branches, not only the held-out games (a test set no run trains on)")
    a = ap.parse_args()
    net, meta = X.load(a.model)
    if a.tiers:
        Q = dict(np.load(a.tiers))
        if [str(x) for x in Q["macros"]] != net.macros:
            raise SystemExit(f"{a.tiers} has macros {list(Q['macros'])}, the model {net.macros}")
        report_tiers(tier_yardstick(net, Q, np.arange(len(Q["game"])), {"r": Q["evr"], "r2": Q["evr2"]}), "fixed judge", sys.stdout)
        if not a.branches:
            sys.exit(0)
    B = dict(np.load(a.branches))
    idx = np.arange(len(B["game"])) if a.all else held_points(B)
    judge = None
    if a.judge:
        J = np.load(a.judge)
        if not np.array_equal(J["game"], B["game"]):
            raise SystemExit(f"{a.judge} was made from other branch data")
        idx = idx[J["judged"][idx]]
        judge = {1: J["ev1"], 4: J["ev4"], "s": J["evt"]}
    for h, v in yardstick(net, B, idx, judge).items():
        print(f"{h}: top-1 {v['top1']:.3f} (chance {v['chance']:.3f}) median rho {v['rho_median']:.2f} "
              f"spread imagined {v['spread_imagined'] * 100:.1f} / real {v['spread_real'] * 100:.1f} pts, "
              f"regret {v['regret'] * 100:.2f} pts, blunders {v['blunders'] * 100:.1f}% ({v['points']} points)")
