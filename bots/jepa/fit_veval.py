"""Refit a JEPA's value head to copy the fitted evaluator on settled positions (rank data), keeping its encoder.

python3 fit_veval.py --model <in.safetensors> --out <out.safetensors> [--rank data/jepa/rank-v1-ev.npz --tok data/jepa/rank-v1-tok.npz]

The planner judges a move by the board where it has settled. rank_train.py's evaluator copy (jepa-v1d) did that on the
v1 latent; here the same targets train a value head on any JEPA's latent (either format), so a bot without a simulator
can score imagined settled boards (ẑ_s, jepa_bot.py --window-horizon s) the way the evaluator scores real ones.
Reports, on held-out games' windows: how often the head picks the evaluator's move (same_as_eval) and the teacher's
move (move_top1), for the model's own value head and for the refitted one. Needs PyTorch.
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
ap.add_argument("--rank", default="data/jepa/rank-v1-ev.npz")
ap.add_argument("--tok", default="data/jepa/rank-v1-tok.npz", help="card tokens of the rank positions, in the order of --rank's Z")
ap.add_argument("--steps", type=int, default=4000)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
torch.manual_seed(a.seed)

net, meta = X.load(a.model)
data = RT.Data(a.rank)
tok = np.load(a.tok)
Z = np.concatenate([net.encode(tok["state"][k:k + 4096].astype(np.float32), tok["ids"][k:k + 4096].astype(np.int64),
                               tok["feats"][k:k + 4096].astype(np.float32), tok["mask"][k:k + 4096].astype(np.float32))
                    for k in range(0, len(tok["ids"]), 4096)]).astype(np.float32)
ev = np.zeros(len(Z), np.float32)
ok = data.leaf_z >= 0
ev[data.leaf_z[ok]] = data.leaf_ev[ok]
held = np.flatnonzero(data.is_held)
train_w = np.flatnonzero(~data.is_held)
pos = lambda ws: np.unique(np.concatenate([data.leaf_z[data.win_lo[w]:data.win_hi[w]] for w in ws]))
tr = pos(train_w)
tr = tr[tr >= 0]
own = net.value(Z)
print("own value head:", RT.metrics(data, held, own, ev), file=sys.stderr, flush=True)

D = Z.shape[1]
P = {"v1.w": torch.tensor(np.random.default_rng(a.seed).normal(0, 1 / np.sqrt(D), (D, 64)).astype(np.float32), requires_grad=True),
     "v1.b": torch.zeros(64, requires_grad=True),
     "v2.w": torch.tensor(np.random.default_rng(a.seed + 1).normal(0, 1 / 8, (64, 1)).astype(np.float32), requires_grad=True),
     "v2.b": torch.zeros(1, requires_grad=True)}
opt = torch.optim.AdamW(list(P.values()), lr=1e-3, weight_decay=1e-3)
Zt, yt = torch.from_numpy(Z[tr]), torch.from_numpy(1 / (1 + np.exp(-ev[tr])))
V = lambda z: (torch.relu(z @ P["v1.w"] + P["v1.b"]) @ P["v2.w"])[:, 0] + P["v2.b"][0]
best = None
for it in range(1, a.steps + 1):
    idx = torch.randint(0, len(Zt), (1024,))
    loss = torch.nn.functional.binary_cross_entropy_with_logits(V(Zt[idx]), yt[idx])
    opt.zero_grad()
    loss.backward()
    opt.step()
    if it % 250 == 0:
        with torch.no_grad():
            v = V(torch.from_numpy(Z)).numpy()
        r = RT.metrics(data, held, v, ev)
        if best is None or r["same_as_eval"] > best[0]["same_as_eval"]:
            best = (r, it, {k: t.detach().numpy().copy() for k, t in P.items()})
print(f"evaluator copy (best at step {best[1]}):", best[0], file=sys.stderr, flush=True)
w = dict(net.w)
w.update(best[2])
M.save_safetensors(a.out, w, {**meta, "value": "evaluator copy on settled rank positions (fit_veval.py)"})
print(f"wrote {a.out}", file=sys.stderr)
