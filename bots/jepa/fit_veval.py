"""Refit a JEPA's value head to copy the fitted evaluator on settled positions (rank data), keeping its encoder.

python3 fit_veval.py --model <in.safetensors> --out <out.safetensors> [--rank data/jepa/rank-v1-ev.npz --tok data/jepa/rank-v1-tok.npz]
    [--rank A.npz B.npz --tok A-tok.npz B-tok.npz] [--gap-weight 1]

The planner judges a move by the board where it has settled. rank_train.py's evaluator copy (jepa-v1d) did that on the
v1 latent; here the same targets train a value head on any JEPA's latent (either format), so a bot without a simulator
can score imagined settled boards (ẑ_s, jepa_bot.py --window-horizon s) the way the evaluator scores real ones.
Reports, on held-out games' windows: how often the head picks the evaluator's move (same_as_eval) and the teacher's
move (move_top1), and the evaluator's win chance lost by the head's pick (ev_regret, ev_blunders = share over 5 points),
for the model's own value head and for the refitted one. Needs PyTorch.

Several --rank/--tok pairs are joined (e.g. the teachers' windows plus the bot's own windows from its recorded games,
rank_data.js --teachers <bot>); each is reported on its own held-out windows, and the best step is the one with the
highest mean same_as_eval over them. --gap-weight a samples training positions in proportion to (window gap / median
gap)^a, clipped to [0.1, 10], where a window's gap is its best minus its worst move under the evaluator: the windows
where the choice matters most count more (0, the default, samples uniformly).
"""
import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
import rank_train as RT  # noqa: E402
import tx_model as X  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--rank", nargs="+", default=["data/jepa/rank-v1-ev.npz"])
ap.add_argument("--tok", nargs="+", default=["data/jepa/rank-v1-tok.npz"], help="card tokens of each --rank's positions, in its Z's order")
ap.add_argument("--steps", type=int, default=4000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--gap-weight", type=float, default=0.0, help="sample positions by (window gap / median gap)^a; 0 = uniform")
a = ap.parse_args()
if len(a.rank) != len(a.tok):
    sys.exit("give one --tok file per --rank file")
torch.manual_seed(a.seed)
net, meta = X.load(a.model)


def move_values(data, w, lg):
    """{move: win chance of its best line} for window w and logits lg (the planner keeps a move's best line)"""
    roots = data.leaf_root[data.win_lo[w]:data.win_hi[w]]
    p = 1 / (1 + np.exp(-lg))
    out = {}
    for k, r in enumerate(roots):
        out[r] = max(out.get(r, -1.0), p[k])
    return out


def ev_scores(data, wins, v, ev):
    """the evaluator's win chance lost by the head's pick, per window, and each window's gap (best minus worst move)"""
    reg, gap = [], []
    for w in wins:
        mv = move_values(data, w, RT.window_logits(data, w, ev))
        best = max(mv.values())
        reg.append(best - mv[RT.pick(data, w, RT.window_logits(data, w, v))])
        gap.append(best - min(mv.values()))
    return np.array(reg), np.array(gap)


sets = []
for rank, tokf in zip(a.rank, a.tok):
    data = RT.Data(rank)
    tok = np.load(tokf)
    Z = np.concatenate([net.encode(tok["state"][k:k + 4096].astype(np.float32), tok["ids"][k:k + 4096].astype(np.int64),
                                   tok["feats"][k:k + 4096].astype(np.float32), tok["mask"][k:k + 4096].astype(np.float32))
                        for k in range(0, len(tok["ids"]), 4096)]).astype(np.float32)
    ev = np.zeros(len(Z), np.float32)
    ok = data.leaf_z >= 0
    ev[data.leaf_z[ok]] = data.leaf_ev[ok]
    held = np.flatnonzero(data.is_held)
    train_w = np.flatnonzero(~data.is_held)
    # training positions, each with its window's gap (a position belongs to one window)
    _, gaps = ev_scores(data, train_w, ev, ev)
    tr, tw = [], []
    for w, g in zip(train_w, gaps):
        zs = data.leaf_z[data.win_lo[w]:data.win_hi[w]]
        zs = zs[zs >= 0]
        tr.append(zs)
        tw.append(np.full(len(zs), g))
    tr, tw = np.concatenate(tr), np.concatenate(tw)
    tr, first = np.unique(tr, return_index=True)
    tw = tw[first]
    sets.append({"name": os.path.basename(rank), "data": data, "Z": Z, "ev": ev, "held": held, "tr": tr, "gap": tw})
    own = net.value(Z)
    r, _ = ev_scores(data, held, own, ev)
    print(f"{os.path.basename(rank)}: {len(train_w)} train / {len(held)} held windows, {len(tr)} train positions; own value head:",
          {**RT.metrics(data, held, own, ev), "ev_regret": round(float(r.mean()), 4), "ev_blunders": round(float((r > 0.05).mean()), 4)},
          file=sys.stderr, flush=True)

Zall = np.concatenate([s["Z"][s["tr"]] for s in sets])
yall = np.concatenate([1 / (1 + np.exp(-s["ev"][s["tr"]])) for s in sets]).astype(np.float32)
gall = np.concatenate([s["gap"] for s in sets])
weights = None
if a.gap_weight:
    med = max(float(np.median(gall)), 1e-3)
    weights = torch.from_numpy(np.clip((gall / med) ** a.gap_weight, 0.1, 10.0).astype(np.float64))
    print(f"gap weighting a={a.gap_weight}: median window gap {med * 100:.1f} pts; weight quartiles "
          f"{np.round(np.quantile(weights.numpy(), [0.25, 0.5, 0.75]), 2).tolist()}", file=sys.stderr, flush=True)

D = Zall.shape[1]
P = {"v1.w": torch.tensor(np.random.default_rng(a.seed).normal(0, 1 / np.sqrt(D), (D, 64)).astype(np.float32), requires_grad=True),
     "v1.b": torch.zeros(64, requires_grad=True),
     "v2.w": torch.tensor(np.random.default_rng(a.seed + 1).normal(0, 1 / 8, (64, 1)).astype(np.float32), requires_grad=True),
     "v2.b": torch.zeros(1, requires_grad=True)}
opt = torch.optim.AdamW(list(P.values()), lr=1e-3, weight_decay=1e-3)
Zt, yt = torch.from_numpy(Zall), torch.from_numpy(yall)
V = lambda z: (torch.relu(z @ P["v1.w"] + P["v1.b"]) @ P["v2.w"])[:, 0] + P["v2.b"][0]
best = None
for it in range(1, a.steps + 1):
    idx = torch.randint(0, len(Zt), (1024,)) if weights is None else torch.multinomial(weights, 1024, replacement=True)
    loss = torch.nn.functional.binary_cross_entropy_with_logits(V(Zt[idx]), yt[idx])
    opt.zero_grad()
    loss.backward()
    opt.step()
    if it % 250 == 0:
        rs = []
        for s in sets:
            with torch.no_grad():
                v = V(torch.from_numpy(s["Z"])).numpy()
            r = RT.metrics(s["data"], s["held"], v, s["ev"])
            reg, _ = ev_scores(s["data"], s["held"], v, s["ev"])
            r.update(ev_regret=round(float(reg.mean()), 4), ev_blunders=round(float((reg > 0.05).mean()), 4))
            rs.append(r)
        score = float(np.mean([r["same_as_eval"] for r in rs]))
        if best is None or score > best[0]:
            best = (score, it, rs, {k: t.detach().numpy().copy() for k, t in P.items()})
for s, r in zip(sets, best[2]):
    print(f"evaluator copy (best at step {best[1]}) on {s['name']}:", r, file=sys.stderr, flush=True)
w = dict(net.w)
w.update(best[3])
M.save_safetensors(a.out, w, {**meta, "value": "evaluator copy on settled rank positions (fit_veval.py)"})
print(f"wrote {a.out}", file=sys.stderr)
