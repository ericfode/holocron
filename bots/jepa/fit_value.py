"""A new value head for a tx model, fitted on who won from recorded decisions (data.py packs), on the frozen encoder.

    python3 bots/jepa/fit_value.py --model runs/tx-t10.safetensors --pack data/hist/pack-h.npz --out runs/tx-t10-w.safetensors

The hybrid planner (jepa_bot.py --score plan) judges each line's real settled board with --plan-model's value head.
tx-t10's own head (trained on who won in its recorded games, mostly rush and random bots) judged better than the
evaluator copy (tx-t10-e). This refits that head on games against c-clock (the opponent the bot plays), with the encoder
frozen, so only v1/v2 change and the model file is otherwise the same. The latent of every row is cached next to the
pack (<pack>.<model>-<hash>.zt.npy, the same cache hist_train.py writes). Held out by game seed; the closing line compares
the model's own head and the new one on the held-out rows.
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
ap.add_argument("--model", required=True)
ap.add_argument("--pack", required=True, help="data.py output (state, tokens, win, game)")
ap.add_argument("--out", required=True)
ap.add_argument("--steps", type=int, default=6000)
ap.add_argument("--batch", type=int, default=4096)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--hold", type=float, default=0.1)
ap.add_argument("--seed", type=int, default=1)
a = ap.parse_args()

t0 = time.time()
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
net, meta = X.load(a.model)
w, _ = M.load_safetensors(a.model)
z = np.load(a.pack)
win, game = z["win"].astype(np.float32), z["game"]
N = len(win)
cache, fresh = X.latent_cache(a.pack, a.model)
if fresh and np.load(cache, mmap_mode="r").shape[0] == N:
    zt = np.load(cache)
else:
    st, ids, ft, mk = z["state"], z["tok_ids"], z["tok_feats"], z["tok_mask"]
    T = int(meta.get("tmax", ids.shape[1]))
    zt = np.concatenate([net.encode(st[k:k + 2048], ids[k:k + 2048, :T].astype(np.int64), ft[k:k + 2048, :T].astype(np.float32),
                                    mk[k:k + 2048, :T].astype(np.float32)) for k in range(0, N, 2048)]).astype(np.float32)
    np.save(cache, zt)
useeds = np.unique(game)
held_seeds = set(np.random.default_rng(a.seed).permutation(useeds)[:max(1, int(len(useeds) * a.hold))].tolist())
held = np.array([s in held_seeds for s in game.tolist()])
tr, te = np.nonzero(~held)[0], np.nonzero(held)[0]
print(f"{N} rows ({len(tr)} train, {len(te)} held out), latents in {time.time() - t0:.0f}s", file=sys.stderr, flush=True)

Z = torch.tensor(zt, device=dev)
Y = torch.tensor(win, device=dev)
bce = torch.nn.functional.binary_cross_entropy_with_logits


def head(p, x):
    return (torch.relu(x @ p["v1.w"] + p["v1.b"]) @ p["v2.w"])[:, 0] + p["v2.b"][0]


old = {k: torch.tensor(w[k], device=dev) for k in ("v1.w", "v1.b", "v2.w", "v2.b")}
te_t = torch.tensor(te, device=dev)
with torch.no_grad():
    lo = head(old, Z[te_t])
    old_bce, old_acc = float(bce(lo, Y[te_t])), float(((lo > 0).float() == Y[te_t]).float().mean())
g = torch.Generator(device="cpu").manual_seed(a.seed)
p = {k: v.clone().requires_grad_(True) for k, v in old.items()}  # start from the model's own head
opt = torch.optim.AdamW(list(p.values()), lr=a.lr, weight_decay=1e-2)
tr_t = torch.tensor(tr, device=dev)
best = None
for step in range(1, a.steps + 1):
    idx = tr_t[torch.randint(0, len(tr), (a.batch,), generator=g).to(dev)]
    l = bce(head(p, torch.nn.functional.dropout(Z[idx], 0.1)), Y[idx])
    opt.zero_grad(set_to_none=True)
    l.backward()
    opt.step()
    if step % 200 == 0 or step == a.steps:
        with torch.no_grad():
            lg = head(p, Z[te_t])
            hb, ha = float(bce(lg, Y[te_t])), float(((lg > 0).float() == Y[te_t]).float().mean())
        if best is None or hb < best[0]:
            best = (hb, ha, step, {k: v.detach().cpu().numpy().copy() for k, v in p.items()})
w.update(best[3])
M.save_safetensors(a.out, w, {**meta, "value": f"refit on who won in {os.path.basename(a.pack)} (fit_value.py)"})
print(f"held-out win: the model's own head BCE {old_bce:.4f} acc {old_acc:.3f}; refit BCE {best[0]:.4f} acc {best[1]:.3f} (step {best[2]}) "
      f"-> {a.out} in {time.time() - t0:.0f}s", file=sys.stderr)
