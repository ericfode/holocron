"""The window part of the line test: a root-move model for the bot without the simulator, which sees only the root
move at an action window (its follow-up options appear after it is played).

    python3 bots/jepa/line_root.py --data data/lines/pl1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/root1

For each (window, root move) the target is the real settled board of the root move's best line (the one the planner
would follow, by tx-t10's value head on the real boards). Input: the window's latent z, the model's own settle prediction
for the move zb, and the move's action token. ẑ = zb + MLP([z, zb, token]); loss as line_train.py. Held out by game
(the same split). Root moves are ranked within each window by tx-t10's value head on ẑ, against the real root values
(the best line's) and against the baseline zb; 95% intervals by game. --export also writes the weights as .npz for
jepa_bot.py --root-model.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402
import model as M  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--steps", type=int, default=8000)
ap.add_argument("--windows", type=int, default=256)
ap.add_argument("--hidden", type=int, default=256)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--w-diff", type=float, default=4.0)
ap.add_argument("--hold", type=float, default=0.1)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--boot", type=int, default=1000)
a = ap.parse_args()
t0 = time.time()
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(a.seed)
D = dict(np.load(a.data))
w, _ = M.load_safetensors(a.model)
win = D["win"].astype(np.int64)
NW = len(D["z"])
vr_all = 1.0 / (1.0 + np.exp(-(np.maximum(D["z_real"] @ w["v1.w"] + w["v1.b"], 0.0) @ w["v2.w"])[:, 0] - w["v2.b"][0]))
# one example per (window, root move): its best line
key = win * 64 + D["root_slot"].astype(np.int64)
order = np.lexsort((-vr_all, key))
first = np.r_[True, key[order][1:] != key[order][:-1]]
best = order[first]  # index of the best line of each (window, root)
ew = win[best]
rootv = vr_all[best]  # the real root value: its best line's
start = np.searchsorted(ew, np.arange(NW))
count = np.bincount(ew, minlength=NW)
wgame = D["w_game"]
games = np.unique(wgame)
held = set(np.random.default_rng(a.seed).permutation(games)[:max(1, int(len(games) * a.hold))].tolist())
w_held = np.isin(wgame, list(held))
tr_w, te_w = np.nonzero(~w_held & (count >= 2))[0], np.nonzero(w_held & (count >= 2))[0]
print(f"{len(best)} (window, root move) examples in {NW} windows ({len(tr_w)} train / {len(te_w)} held out with 2+ roots)", file=sys.stderr, flush=True)
tt = lambda x, dt=torch.float32: torch.as_tensor(np.ascontiguousarray(x), dtype=dt, device=dev)
Z, ZB, ZR = tt(D["z"][ew]), tt(D["zb"][best]), tt(D["z_real"][best])
TOK, TID, EW = tt(D["act"][best, 0].astype(np.float32)), tt(D["aid"][best, 0], torch.long), tt(ew, torch.long)
V = {k: tt(w[k]) for k in ("v1.w", "v1.b", "v2.w", "v2.b")}
value = lambda x: (torch.relu(x @ V["v1.w"] + V["v1.b"]) @ V["v2.w"])[..., 0] + V["v2.b"][0]


class RootModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = torch.nn.Embedding(F.ID_BUCKETS, 16)
        self.inp = torch.nn.Linear(F.ACTION_DIM + 16, 64)
        self.l1 = torch.nn.Linear(2 * M.D + 64, a.hidden)
        self.l2 = torch.nn.Linear(a.hidden, M.D)

    def forward(self, i):
        t = torch.relu(self.inp(torch.cat([TOK[i], self.emb(TID[i])], -1)))
        return ZB[i] + self.l2(torch.relu(self.l1(torch.cat([Z[i], ZB[i], t], -1))))


def rows_of(ws):
    return np.concatenate([np.arange(start[k], start[k] + count[k]) for k in ws])


def loss_fn(pred, i):
    tgt = ZR[i]
    plain = ((pred - tgt) ** 2).mean()
    uniq, inv = torch.unique(EW[i], return_inverse=True)
    cnt = torch.zeros(len(uniq), device=dev).index_add_(0, inv, torch.ones(len(i), device=dev))[:, None]
    mp = torch.zeros(len(uniq), M.D, device=dev).index_add_(0, inv, pred) / cnt
    mt = torch.zeros(len(uniq), M.D, device=dev).index_add_(0, inv, tgt) / cnt
    return plain + a.w_diff * (((pred - mp[inv]) - (tgt - mt[inv])) ** 2).mean()


def wmetrics(score, real):
    bestm = real >= real.max() - 1e-9
    top = score >= score.max() - 1e-9
    o = np.argsort(np.argsort(score)), np.argsort(np.argsort(real))
    rho = None if score.std() == 0 or real.std() == 0 else float(np.corrcoef(o[0], o[1])[0, 1])
    return float(bestm[top].mean()), rho, float(real.max() - real[top].mean())


net = RootModel().to(dev)
opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
rng = np.random.default_rng(a.seed)
te_i = torch.as_tensor(rows_of(te_w), device=dev)
bestm = None
for step in range(1, a.steps + 1):
    for g in opt.param_groups:
        g["lr"] = a.lr * min(1.0, step / 300) * 0.5 * (1 + math.cos(math.pi * step / a.steps))
    i = torch.as_tensor(rows_of(rng.choice(tr_w, a.windows, replace=False)), device=dev)
    l = loss_fn(net(i), i)
    opt.zero_grad(set_to_none=True)
    l.backward()
    opt.step()
    if step % 500 == 0 or step == a.steps:
        with torch.no_grad():
            hl = float(loss_fn(net(te_i), te_i))
        print(f"root {step}: held loss {hl:.4f}", file=sys.stderr, flush=True)
        if bestm is None or hl < bestm[0]:
            bestm = (hl, step, {k: v.detach().clone() for k, v in net.state_dict().items()})
net.load_state_dict(bestm[2])
with torch.no_grad():
    vp = torch.sigmoid(value(net(torch.arange(len(best), device=dev)))).cpu().numpy()
    vb = torch.sigmoid(value(ZB)).cpu().numpy()
rows = []
for k in te_w:
    s = slice(start[k], start[k] + count[k])
    rows.append((wgame[k], wmetrics(vb[s], rootv[s]), wmetrics(vp[s], rootv[s])))
g = np.array([r[0] for r in rows])
ug = np.unique(g)
gi = {x: np.nonzero(g == x)[0] for x in ug}
br = np.random.default_rng(a.seed + 5)
boot_idx = [np.concatenate([gi[x] for x in br.choice(ug, len(ug))]) for _ in range(a.boot)]


def ci(vals):
    vals = np.asarray(vals, np.float64)
    b = np.array([np.nanmean(vals[ix]) for ix in boot_idx])
    return [float(np.nanmean(vals)), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


res = {"examples": int(len(best)), "held_windows": len(rows), "best_step": bestm[1]}
for name, j in (("baseline", 1), ("root_model", 2)):
    res[name] = {"top1": ci([r[j][0] for r in rows]), "rho": ci([np.nan if r[j][1] is None else r[j][1] for r in rows]),
                 "lost_pts": ci([r[j][2] * 100 for r in rows])}
res["diff"] = {"top1": ci([r[2][0] - r[1][0] for r in rows]), "lost_pts": ci([(r[2][2] - r[1][2]) * 100 for r in rows])}
fmt = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
print(f"root moves, held-out {len(rows)} windows: baseline top-1 {fmt(res['baseline']['top1'])} lost {fmt(res['baseline']['lost_pts'])} pts; "
      f"root model top-1 {fmt(res['root_model']['top1'])} lost {fmt(res['root_model']['lost_pts'])} pts; "
      f"difference top-1 {fmt(res['diff']['top1'])}, lost {fmt(res['diff']['lost_pts'])} pts", file=sys.stderr)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
json.dump(res, open(a.out + ".json", "w"), indent=1)
np.savez(a.out + ".npz", **{k: v.cpu().numpy() for k, v in bestm[2].items()})
print(f"wrote {a.out}.json and .npz in {time.time() - t0:.0f}s", file=sys.stderr)
