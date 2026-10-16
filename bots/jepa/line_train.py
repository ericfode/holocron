"""Does a predictor conditioned on the whole line rank the planner's lines closer to their real results than the
one-click model? Offline test on line_data.py output.

    python3 bots/jepa/line_train.py --data data/lines/pl1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/l1

tx-t10's encoder (and so the targets) stay frozen: z is the window's latent, z_real the latent of the real settled board
of each line, zb the model's own settle prediction for the line's root move (what the bot without the simulator scores).
New parts: a line encoder (each action token = its 62-number row and its id embedding, a position embedding, a small
transformer over the line, masked mean) and a predictor.
  variant "line":  ẑ = z  + MLP([z, line])          (the spec: the latent now and the line)
  variant "resid": ẑ = zb + MLP([z, zb, line])      (the root move's own prediction plus what the follow-ups change)
Loss: the error of ẑ against z_real plus --w-diff times the error after removing each window's mean (what tells lines
apart), as the branch losses of tx_train_torch.py. Held out by game. Every line is ranked within its window by
tx-t10's value head on ẑ, on zb (the baseline; lines of one root move tie) and on z_real (the planner's ranking):
top-1 agreement, Spearman, the real value lost by the predicted top line and the latent error, with 95% intervals by game.
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
ap.add_argument("--variants", default="line,resid")
ap.add_argument("--steps", type=int, default=8000)
ap.add_argument("--windows", type=int, default=256, help="windows per batch (all their lines)")
ap.add_argument("--dm", type=int, default=64)
ap.add_argument("--layers", type=int, default=2)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--w-diff", type=float, default=4.0)
ap.add_argument("--hold", type=float, default=0.1)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--ids-only", action="store_true",
                help="follow-up tokens keep only their identity (which option: card or button), not their 62-number rows, which were "
                     "read after the root move was played in the simulation; the root move's row is kept")
a = ap.parse_args()
t0 = time.time()
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(a.seed)
D = dict(np.load(a.data))
w, _ = M.load_safetensors(a.model)
win = D["win"].astype(np.int64)
NW, NL, L = len(D["z"]), len(win), D["act"].shape[1]
start = np.searchsorted(win, np.arange(NW))
count = np.bincount(win, minlength=NW)
assert np.all(np.diff(win) >= 0), "lines must be grouped by window"
wgame = D["w_game"]
games = np.unique(wgame)
held = set(np.random.default_rng(a.seed).permutation(games)[:max(1, int(len(games) * a.hold))].tolist())
w_held = np.isin(wgame, list(held))
tr_w, te_w = np.nonzero(~w_held & (count >= 2))[0], np.nonzero(w_held & (count >= 2))[0]
print(f"{NW} windows ({len(tr_w)} train / {len(te_w)} held out, {len(held)} held-out games), {NL} lines, "
      f"{(D['llen'] > 1).mean() * 100:.0f}% with follow-ups", file=sys.stderr, flush=True)

tt = lambda x, dt=torch.float32: torch.as_tensor(np.ascontiguousarray(x), dtype=dt, device=dev)
Z, ZB, ZR = tt(D["z"]), tt(D["zb"]), tt(D["z_real"])
act = D["act"].astype(np.float32)
if a.ids_only:
    act[:, 1:] = 0.0
ACT, AID, LM, WIN = tt(act), tt(D["aid"], torch.long), tt(D["lmask"]), tt(win, torch.long)
del act
V = {k: tt(w[k]) for k in ("v1.w", "v1.b", "v2.w", "v2.b")}
value = lambda x: (torch.relu(x @ V["v1.w"] + V["v1.b"]) @ V["v2.w"])[..., 0] + V["v2.b"][0]


class LineModel(torch.nn.Module):
    def __init__(self, variant):
        super().__init__()
        self.variant = variant
        dm = a.dm
        self.emb = torch.nn.Embedding(F.ID_BUCKETS, 16)
        self.inp = torch.nn.Linear(F.ACTION_DIM + 16, dm)
        self.pos = torch.nn.Parameter(torch.randn(L, dm) * 0.1)
        layer = torch.nn.TransformerEncoderLayer(dm, 4, 2 * dm, dropout=0.0, batch_first=True)
        self.tx = torch.nn.TransformerEncoder(layer, a.layers)
        din = M.D + dm + (M.D if variant == "resid" else 0)
        self.pred = torch.nn.Sequential(torch.nn.Linear(din, 256), torch.nn.ReLU(), torch.nn.Linear(256, M.D))

    def forward(self, idx):
        x = self.inp(torch.cat([ACT[idx], self.emb(AID[idx])], -1)) + self.pos
        m = LM[idx]
        x = self.tx(x, src_key_padding_mask=m < 0.5)
        line = (x * m[..., None]).sum(1) / m.sum(1, keepdim=True).clamp(min=1.0)
        z = Z[WIN[idx]]
        if self.variant == "resid":
            return ZB[idx] + self.pred(torch.cat([z, ZB[idx], line], -1))
        return z + self.pred(torch.cat([z, line], -1))


def lines_of(ws):
    return np.concatenate([np.arange(start[k], start[k] + count[k]) for k in ws])


def losses(pred, idx):
    tgt = ZR[idx]
    plain = ((pred - tgt) ** 2).mean()
    wi = WIN[idx]
    uniq, inv = torch.unique(wi, return_inverse=True)
    cnt = torch.zeros(len(uniq), device=dev).index_add_(0, inv, torch.ones(len(idx), device=dev))[:, None]
    mp = torch.zeros(len(uniq), M.D, device=dev).index_add_(0, inv, pred) / cnt
    mt = torch.zeros(len(uniq), M.D, device=dev).index_add_(0, inv, tgt) / cnt
    diff = (((pred - mp[inv]) - (tgt - mt[inv])) ** 2).mean()
    return plain + a.w_diff * diff, plain, diff


def rank(x):
    """average ranks (ties share)"""
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    for v in np.unique(x):
        s = x == v
        if s.sum() > 1:
            r[s] = r[s].mean()
    return r


def window_metrics(score, real):
    """per window: top-1 (ties averaged), Spearman (None if constant), value lost"""
    best = real >= real.max() - 1e-9
    top = score >= score.max() - 1e-9
    t1 = float(best[top].mean())
    lost = float(real.max() - real[top].mean())
    rs, rr = rank(score), rank(real)
    rho = None if rs.std() == 0 or rr.std() == 0 else float(np.corrcoef(rs, rr)[0, 1])
    return t1, rho, lost


def evaluate(pred_all):
    """metrics on the held-out windows for the given per-line predictions (None = the baseline zb)"""
    with torch.no_grad():
        vr = torch.sigmoid(value(ZR)).cpu().numpy()
        vb = torch.sigmoid(value(ZB)).cpu().numpy()
        vp = torch.sigmoid(value(pred_all)).cpu().numpy() if pred_all is not None else None
    rows, roots = [], []
    for k in te_w:
        s = slice(start[k], start[k] + count[k])
        follow = bool((D["llen"][s] > 1).any())
        rows.append((wgame[k], follow, window_metrics(vb[s], vr[s]), window_metrics(vp[s], vr[s]) if vp is not None else None))
        # the window's decision: each root move worth its best line (as the planner scores it), the baseline's root value
        slot = D["root_slot"][s]
        us = np.unique(slot)
        if len(us) >= 2:
            rr = np.array([vr[s][slot == u].max() for u in us])
            rb = np.array([vb[s][slot == u][0] for u in us])
            rp = np.array([vp[s][slot == u].max() for u in us]) if vp is not None else None
            roots.append((wgame[k], follow, window_metrics(rb, rr), window_metrics(rp, rr) if rp is not None else None))
    return rows, roots


def summarize(rows, which, subset=None):
    sel = [r for r in rows if subset is None or r[1] == subset]
    g = np.array([r[0] for r in sel])
    m = np.array([[r[which][0], np.nan if r[which][1] is None else r[which][1], r[which][2]] for r in sel], dtype=np.float64)
    ug = np.unique(g)
    gi = {x: np.nonzero(g == x)[0] for x in ug}
    rng = np.random.default_rng(a.seed + 5)
    boots = []
    for _ in range(a.boot):
        idx = np.concatenate([gi[x] for x in rng.choice(ug, len(ug))])
        boots.append(np.nanmean(m[idx], 0))
    boots = np.array(boots)
    est = np.nanmean(m, 0)
    lo, hi = np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0)
    return {"windows": len(sel), "top1": [est[0], lo[0], hi[0]], "rho": [est[1], lo[1], hi[1]], "lost_pts": [est[2] * 100, lo[2] * 100, hi[2] * 100]}


def paired_diff(rows, subset=None):
    """line model minus baseline, per window, 95% interval by game"""
    sel = [r for r in rows if subset is None or r[1] == subset]
    g = np.array([r[0] for r in sel])
    d = np.array([[r[3][0] - r[2][0], r[3][2] - r[2][2]] for r in sel])
    ug = np.unique(g)
    gi = {x: np.nonzero(g == x)[0] for x in ug}
    rng = np.random.default_rng(a.seed + 6)
    boots = np.array([d[np.concatenate([gi[x] for x in rng.choice(ug, len(ug))])].mean(0) for _ in range(a.boot)])
    est = d.mean(0)
    return {"top1": [est[0], *np.percentile(boots[:, 0], [2.5, 97.5])], "lost_pts": [est[1] * 100, *(np.percentile(boots[:, 1], [2.5, 97.5]) * 100)]}


te_lines = torch.as_tensor(lines_of(te_w), device=dev)
with torch.no_grad():
    base_err = float(((ZB[te_lines] - ZR[te_lines]) ** 2).mean())
    stay_err = float(((Z[WIN[te_lines]] - ZR[te_lines]) ** 2).mean())
report = {"ids_only": a.ids_only, "data": a.data, "windows": NW, "lines": NL, "held_games": len(held), "baseline_latent_mse": base_err, "nochange_latent_mse": stay_err}
base_rows, base_roots = evaluate(None)
for sub, name in ((None, "all"), (True, "with_follow_ups"), (False, "root_only")):
    report[f"baseline_{name}"] = summarize(base_rows, 2, sub)
report["baseline_roots"] = summarize(base_roots, 2)
fmt = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
print(f"baseline (zb, root move only): latent MSE {base_err:.4f} (no change {stay_err:.4f}); all windows: top-1 {fmt(report['baseline_all']['top1'])}, "
      f"rho {fmt(report['baseline_all']['rho'])}, lost {fmt(report['baseline_all']['lost_pts'])} pts", file=sys.stderr, flush=True)

os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
rng = np.random.default_rng(a.seed)
for variant in [v for v in a.variants.split(",") if v]:
    net = LineModel(variant).to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
    best = None
    curve = []
    t1 = time.time()
    for step in range(1, a.steps + 1):
        for gr in opt.param_groups:
            gr["lr"] = a.lr * min(1.0, step / 300) * 0.5 * (1 + math.cos(math.pi * step / a.steps))
        idx = torch.as_tensor(lines_of(rng.choice(tr_w, a.windows, replace=False)), device=dev)
        loss, plain, diff = losses(net(idx), idx)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % 500 == 0 or step == a.steps:
            with torch.no_grad():
                pred = net(te_lines)
                l, p, dd = losses(pred, te_lines)
            curve.append({"step": step, "held_loss": float(l), "held_mse": float(p), "held_diff": float(dd)})
            print(f"{variant} {step}: held loss {float(l):.4f} mse {float(p):.4f} diff {float(dd):.4f} ({time.time() - t1:.0f}s)", file=sys.stderr, flush=True)
            if best is None or float(l) < best[0]:
                best = (float(l), step, {k: v.detach().clone() for k, v in net.state_dict().items()})
    net.load_state_dict(best[2])
    with torch.no_grad():
        full = torch.zeros(NL, M.D, device=dev)
        for k in range(0, NL, 65536):
            ix = torch.arange(k, min(NL, k + 65536), device=dev)
            full[ix] = net(ix)
        mse = float(((full[te_lines] - ZR[te_lines]) ** 2).mean())
    rows, roots = evaluate(full)
    r = {"best_step": best[1], "latent_mse": mse, "curve": curve, "roots": summarize(roots, 3), "vs_baseline_roots": paired_diff(roots)}
    for sub, name in ((None, "all"), (True, "with_follow_ups"), (False, "root_only")):
        r[name] = summarize(rows, 3, sub)
        r[f"vs_baseline_{name}"] = paired_diff(rows, sub)
    report[variant] = r
    torch.save(best[2], f"{a.out}-{variant}.pt")
    np.savez(f"{a.out}-{variant}.npz", **{k: v.cpu().numpy() for k, v in best[2].items()})  # for jepa_bot.py --line-model (resid; line_models.LineNP)
    print(f"{variant} (best step {best[1]}): latent MSE {mse:.4f}; all windows: top-1 {fmt(r['all']['top1'])}, rho {fmt(r['all']['rho'])}, "
          f"lost {fmt(r['all']['lost_pts'])} pts; vs baseline top-1 {fmt(r['vs_baseline_all']['top1'])}, lost {fmt(r['vs_baseline_all']['lost_pts'])} pts; "
          f"windows with follow-ups: vs baseline top-1 {fmt(r['vs_baseline_with_follow_ups']['top1'])}; ROOT MOVES: top-1 {fmt(r['roots']['top1'])} "
          f"(baseline {fmt(report['baseline_roots']['top1'])}), lost {fmt(r['roots']['lost_pts'])} (baseline {fmt(report['baseline_roots']['lost_pts'])}) pts, "
          f"vs baseline top-1 {fmt(r['vs_baseline_roots']['top1'])}, lost {fmt(r['vs_baseline_roots']['lost_pts'])} pts", file=sys.stderr, flush=True)
json.dump(report, open(a.out + ".json", "w"), indent=1, default=float)
print(f"wrote {a.out}.json in {time.time() - t0:.0f}s", file=sys.stderr)
