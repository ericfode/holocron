"""A small policy head that copies the hybrid planner's choice at action windows (expert iteration with the world
model frozen): plan_data.py's policy pack in, a head file out for jepa_bot.py --policy.

    python3 bots/jepa/policy_train.py --pack data/plan/pd1-policy.npz --model bots/jepa/models/tx-t10-e.safetensors --out runs/pol-1.safetensors

The window model (the one jepa_bot.py uses at action windows) is frozen: for each window it gives the position's latent z
and each candidate move's imagined settled latent ẑ_s and win chance v = V(ẑ_s), the bot's own score. The head reads
[z, ẑ_s, ẑ_s - z, v] per candidate and gives a logit; a softmax over the window's candidates is trained to put the
planner's pick first. Training the world model toward the planner's picks bent its forecasts (tx-o1d), so only this
head learns. Held out by game: agreement with the planner of the head's pick and of the imagined best (the bot without
the planner), and the planner's own value lost by each pick on windows where it judged both.
"""
import argparse
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402
import tx_model as X  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pack", required=True)
ap.add_argument("--model", required=True, help="the window model (frozen)")
ap.add_argument("--out", required=True)
ap.add_argument("--steps", type=int, default=6000)
ap.add_argument("--batch", type=int, default=512)
ap.add_argument("--hidden", type=int, default=128)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--hold", type=float, default=0.1)
ap.add_argument("--seed", type=int, default=1)
a = ap.parse_args()

t0 = time.time()
P = dict(np.load(a.pack))
net, meta = X.load(a.model)
hs = net.horizons.index("s")
W, K = len(P["pick"]), P["act"].shape[1]
T = int(meta.get("tmax", P["tok_ids"].shape[1]))
Z, ZS = np.zeros((W, M.D), np.float32), np.zeros((W, K, M.D), np.float32)
for k in range(0, W, 256):
    s = slice(k, k + 256)
    z, pr = net.forward(P["state"][s], P["tok_ids"][s, :T].astype(np.int64), P["tok_feats"][s, :T].astype(np.float32),
                        P["tok_mask"][s, :T].astype(np.float32), P["act"][s].astype(np.float32), P["aid"][s].astype(np.int64), hsel=[hs])
    Z[s], ZS[s] = z, pr[:, :, 0]
V = M.sigmoid(net.value(ZS.reshape(-1, M.D))).reshape(W, K).astype(np.float32)
mask = np.arange(K)[None, :] < P["nmove"][:, None]
print(f"{W} windows, {K} candidates each at most, latents in {time.time() - t0:.0f}s", file=sys.stderr, flush=True)

games = np.unique(P["game"])
held = set(np.random.default_rng(a.seed).permutation(games)[:max(1, int(len(games) * a.hold))].tolist())
is_held = np.isin(P["game"], list(held))
tr, te = np.nonzero(~is_held)[0], np.nonzero(is_held)[0]
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tt = lambda x: torch.as_tensor(np.ascontiguousarray(x), device=dev)
Zt, ZSt, Vt, Mt, Yt = tt(Z), tt(ZS), tt(V), tt(mask), tt(P["pick"].astype(np.int64))
DIN = 3 * M.D + 1
g = np.random.default_rng(a.seed)
p = {"pol1.w": (g.uniform(-1, 1, (DIN, a.hidden)) * np.sqrt(6.0 / (DIN + a.hidden))).astype(np.float32), "pol1.b": np.zeros(a.hidden, np.float32),
     "pol2.w": (g.uniform(-1, 1, (a.hidden, 1)) * np.sqrt(6.0 / (a.hidden + 1))).astype(np.float32), "pol2.b": np.zeros(1, np.float32)}
p = {k: torch.tensor(v, device=dev, requires_grad=True) for k, v in p.items()}


def logits(w, idx):
    z, zs, v = Zt[idx], ZSt[idx], Vt[idx]
    x = torch.cat([z[:, None].expand_as(zs), zs, zs - z[:, None], v[..., None]], -1)
    lg = (torch.relu(x @ w["pol1.w"] + w["pol1.b"]) @ w["pol2.w"])[..., 0] + w["pol2.b"][0]
    return torch.where(Mt[idx], lg, torch.full_like(lg, -1e9))


def agree(pick, idx):
    return float((pick == P["pick"][idx]).mean())


def lost(pick, idx):
    """the planner's own value lost by `pick`, on windows where the planner judged both moves"""
    pl = P["plan"][idx]
    a_, b_ = pl[np.arange(len(idx)), P["pick"][idx]], pl[np.arange(len(idx)), pick]
    ok = (a_ >= 0) & (b_ >= 0)
    return float((a_[ok] - b_[ok]).mean()), float(ok.mean())


opt = torch.optim.AdamW(list(p.values()), lr=a.lr, weight_decay=1e-3)
te_t = tt(te)
best = None
for step in range(1, a.steps + 1):
    idx = tt(g.choice(tr, a.batch))
    l = torch.nn.functional.cross_entropy(logits(p, idx), Yt[idx])
    opt.zero_grad(set_to_none=True)
    l.backward()
    opt.step()
    if step % 250 == 0 or step == a.steps:
        with torch.no_grad():
            lt = logits(p, te_t)
            ce = float(torch.nn.functional.cross_entropy(lt, Yt[te_t]))
        if best is None or ce < best[0]:
            best = (ce, step, {k: v.detach().cpu().numpy().copy() for k, v in p.items()}, lt.argmax(1).cpu().numpy())
im_pick = np.where(mask, P["imag"], -9.0).argmax(1)  # the imagined best (the bot without the planner)
v_pick = np.where(mask, V, -9.0).argmax(1)
print(f"held-out {len(te)} windows of {len(held)} games: agreement with the planner: imagined best {agree(im_pick[te], te):.3f} "
      f"(recomputed {agree(v_pick[te], te):.3f}), policy head {agree(best[3], te):.3f} (CE {best[0]:.3f} at step {best[1]}); "
      f"planner value lost: imagined {lost(im_pick[te], te)[0] * 100:.2f} pts, policy {lost(best[3], te)[0] * 100:.2f} pts "
      f"({lost(best[3], te)[1] * 100:.0f}% of windows judged both)", file=sys.stderr)
M.save_safetensors(a.out, best[2], {"format": "swu-jepa-policy/1", "window_model": os.path.basename(a.model), "inputs": "z,zs,zs-z,v",
                                    "k": str(K), "hidden": str(a.hidden)})
print(f"wrote {a.out} in {time.time() - t0:.0f}s", file=sys.stderr)
