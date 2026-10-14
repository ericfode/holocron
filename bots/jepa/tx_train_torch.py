"""Trains the transformer JEPA (tx_model.py, --arch tx) or a pooled twin (--arch pool: model.py's v1 layers) in PyTorch, on
a GPU (CUDA, Apple MPS) or the CPU: the JEPA loss of train.py on recorded rows, plus every legal move of the branch
points (branch_prep.py), read from compressed packs (pack_data.py).

python tx_train_torch.py --arch tx|pool --pack-r data/pack-r.npz --pack-b data/pack-b.npz --out runs/tx [--steps 5000]
Writes <out>.safetensors (what the bot loads: tx_model.load reads both formats) and <out>.log.json (curves, value head,
the move-ranking yardstick on held-out branch points).
--settle (tx only) adds a third move token per move, trained on branch points to predict the board where the move has
settled (branches.js `st`): the position the simulating planner judges, so a bot without a simulator can judge the
whole move at its action windows (jepa_bot.py --window-horizon s).
--pack-e with --w-eval > 0 adds a loss that keeps "who is winning" in the latent: a small head on the online z learns
to copy the fitted evaluator on the rank data's settled positions (training games only), and its gradient reaches the
encoder. Without it the JEPA latent copies the evaluator ~77% at best (fit_veval.py), where a network trained for it
directly reaches ~91%.
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
import tx_model as X  # noqa: E402
from yardstick import held_points, yardstick  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--arch", choices=["tx", "pool"], required=True)
ap.add_argument("--pack-r", required=True, help="recorded rows (pack_data.py)")
ap.add_argument("--pack-b", required=True, nargs="+", help="branch points (pack_data.py); several packs are joined")
ap.add_argument("--out", required=True)
ap.add_argument("--steps", type=int, default=5000)
ap.add_argument("--rb", type=int, default=256)
ap.add_argument("--groups", type=int, default=32)
ap.add_argument("--dm", type=int, default=64)
ap.add_argument("--layers", type=int, default=2)
ap.add_argument("--heads", type=int, default=4)
ap.add_argument("--lr", type=float, default=None)
ap.add_argument("--warmup", type=int, default=300)
ap.add_argument("--ema", type=float, default=0.995)
ap.add_argument("--w-var", type=float, default=1.0)
ap.add_argument("--w-cov", type=float, default=0.04)
ap.add_argument("--w-branch", type=float, default=1.0)
ap.add_argument("--w-diff", type=float, default=4.0)
ap.add_argument("--token-dropout", type=float, default=0.15)
ap.add_argument("--value-steps", type=int, default=3000)
ap.add_argument("--eval-every", type=int, default=500)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--device", default=None)
ap.add_argument("--settle", action="store_true", help="also predict where each move settles (needs branch data with st_ arrays)")
ap.add_argument("--pack-e", default=None, help="settled positions with the evaluator's logit (pack_data.py --rank)")
ap.add_argument("--w-eval", type=float, default=0.0, help="weight of the evaluator-copy loss on the encoder")
ap.add_argument("--eb", type=int, default=256, help="evaluator-copy positions per batch")
ap.add_argument("--yard-points", type=int, default=8000, help="held-out branch points the closing yardstick reads at most")
ap.add_argument("--test-pack", default=None, help="branch pack of games no run trains on, for the fixed-judge yardstick")
ap.add_argument("--test-judge", default=None, help="judge_prep.py's scores of --test-pack's held-out points")
a = ap.parse_args()
lr0 = a.lr if a.lr is not None else (5e-4 if a.arch == "tx" else 1e-3)
dev = torch.device(a.device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"))
torch.backends.cuda.matmul.allow_tf32 = False  # the bot plays in float32 numpy; keep training numerics close to it
torch.backends.cudnn.allow_tf32 = False
torch.manual_seed(a.seed)
K = 12
HZ = len(M.HORIZONS) + (1 if a.settle else 0)
assert not (a.settle and a.arch == "pool"), "--settle needs --arch tx"
t0 = time.time()
rng = np.random.default_rng(a.seed)

R = dict(np.load(a.pack_r))
packs = [dict(np.load(f)) for f in a.pack_b]
Bd = {k: np.concatenate([p[k] for p in packs]) for k in packs[0]} if len(packs) > 1 else packs[0]
del packs
T = R["tok_ids"].shape[1]
d = {"state": R["state"], "tok_ids": R["tok_ids"].astype(np.int64), "tok_feats": R["tok_feats"], "tok_mask": R["tok_mask"], "act": R["act"],
     "aid": R["aid"], "win": R["win"], "game": R["game"], "nxt1": R["nxt1"], "nxt4": R["nxt4"]}
games = np.unique(d["game"])
held_games = set(rng.choice(games, max(1, int(len(games) * 0.1)), replace=False).tolist())  # same draw as train.py
is_held = np.isin(d["game"], list(held_games))
ok = d["nxt1"] >= 0
r_train, r_held = np.flatnonzero(ok & ~is_held), np.flatnonzero(ok & is_held)
E = None
if a.pack_e and a.w_eval > 0:
    E = dict(np.load(a.pack_e))
    E["tok_ids"] = E["tok_ids"].astype(np.int64)
    e_train = np.flatnonzero(E["has"] & ~E["held"])
bgames = np.unique(Bd["game"])
bheld = set(np.random.default_rng(a.seed + 1).choice(bgames, max(1, int(len(bgames) * 0.1)), replace=False).tolist())
b_is_held = np.isin(Bd["game"], list(bheld))
b_train, b_held = np.flatnonzero(~b_is_held), np.flatnonzero(b_is_held)
print(f"device {dev}; {len(r_train)} recorded train / {len(r_held)} held rows; {len(b_train)} branch train / {len(b_held)} held points "
      f"({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)

if a.arch == "tx":
    ENC, HEADS = X.shapes(a.dm, a.layers, HZ)
else:
    ENC, HEADS = M.ENCODER, M.HEADS
if E is not None:
    HEADS = {**HEADS, "ve1.w": (M.D, 64), "ve1.b": (64,), "ve2.w": (64, 1), "ve2.b": (1,)}


def init(rng):
    p = {}
    for name, shape in {**ENC, **HEADS}.items():
        if name in M.EMB_TABLES:
            p[name] = rng.normal(0, 0.1, shape).astype(np.float32)
        elif name.endswith(".g"):
            p[name] = np.ones(shape, np.float32)
        elif name == "hor":
            p[name] = rng.normal(0, 0.5, shape).astype(np.float32)
        elif name.endswith(".w"):
            p[name] = (rng.uniform(-1, 1, shape) * np.sqrt(6.0 / (shape[0] + shape[1]))).astype(np.float32)
        else:
            p[name] = np.zeros(shape, np.float32)
    return p


params = init(rng)
P = {k: torch.tensor(v, device=dev, requires_grad=True) for k, v in params.items()}
Tg = {k: torch.tensor(params[k].copy(), device=dev) for k in ENC}


def lin(w, name, x):
    return x @ w[name + ".w"] + w[name + ".b"]


def ln(x, w, name):
    return torch.nn.functional.layer_norm(x, (x.shape[-1],), w[name + ".g"], w[name + ".b"], 1e-5)


STRUCT = {}


def run_tx(w, state, ids, feats, mask, act=None, aid=None):
    B, t = ids.shape
    dm, H = a.dm, a.heads
    hd = dm // H
    x = torch.cat([lin(w, "sin", state).unsqueeze(1), lin(w, "tin", torch.cat([feats, M.embed(w, ids)], -1))], 1)
    kval = torch.cat([torch.ones(B, 1, device=dev), mask], 1)
    c = 1 + t
    k = 0
    if act is not None:
        k = act.shape[1]
        av = lin(w, "ain", torch.cat([act, M.embed(w, aid)], -1))
        av = (av.unsqueeze(2) + w["hor"].reshape(1, 1, HZ, dm)).reshape(B, HZ * k, dm)
        x = torch.cat([x, av], 1)
        kval = torch.cat([kval, torch.ones(B, HZ * k, device=dev)], 1)
    S = c + HZ * k
    bias = ((kval - 1.0) * 1e9).reshape(B, 1, 1, S)
    if k:
        if (c, k) not in STRUCT:
            STRUCT[(c, k)] = torch.tensor(X.struct_mask(c, k, HZ), device=dev).reshape(1, 1, S, S)
        bias = bias + STRUCT[(c, k)]
    for i in range(a.layers):
        y = ln(x, w, f"b{i}.ln1")
        q = lin(w, f"b{i}.q", y).reshape(B, S, H, hd).transpose(1, 2)
        kk = lin(w, f"b{i}.k", y).reshape(B, S, H, hd).transpose(1, 2)
        v = lin(w, f"b{i}.v", y).reshape(B, S, H, hd).transpose(1, 2)
        att = torch.softmax(q @ kk.transpose(-2, -1) / math.sqrt(hd) + bias, -1)
        x = x + lin(w, f"b{i}.o", (att @ v).transpose(1, 2).reshape(B, S, dm))
        x = x + lin(w, f"b{i}.f2", torch.relu(lin(w, f"b{i}.f1", ln(x, w, f"b{i}.ln2"))))
    x = ln(x, w, "lnf")
    kv = kval[:, :c].unsqueeze(-1)
    mean = (x[:, :c] * kv).sum(1) / kv.sum(1)
    z = lin(w, "zo2", torch.relu(lin(w, "zo1", torch.cat([x[:, 0], mean, state], -1))))
    if not k:
        return z, None
    ao = x[:, c:].reshape(B, k, HZ, dm)
    zb = z.reshape(B, 1, 1, M.D).expand(B, k, HZ, M.D)
    return z, zb + lin(w, "p2", torch.relu(lin(w, "p1", torch.cat([zb, ao], -1))))


def run_pool(w, state, ids, feats, mask, act=None, aid=None):
    h = torch.relu(lin(w, "tok2", torch.relu(lin(w, "tok1", torch.cat([feats, M.embed(w, ids)], -1)))))
    m = mask.unsqueeze(-1)
    cnt = m.sum(1)
    mean = (h * m).sum(1) / cnt.clamp(min=1.0)
    mx = (h + (m - 1.0) * 1e4).max(1).values * (cnt > 0).float()
    z = lin(w, "st2", torch.relu(lin(w, "st1", torch.cat([state, mean, mx], -1))))
    if act is None:
        return z, None
    B, k = act.shape[0], act.shape[1]
    av = torch.relu(lin(w, "act2", torch.relu(lin(w, "act1", torch.cat([act.reshape(B * k, -1), M.embed(w, aid.reshape(B * k))], -1)))))
    zb = z.reshape(B, 1, M.D).expand(B, k, M.D).reshape(B * k, M.D)
    outs = []
    for hi in range(HZ):
        hz = torch.zeros(B * k, HZ, device=dev)
        hz[:, hi] = 1.0
        outs.append(zb + lin(w, "p3", torch.relu(lin(w, "p2", torch.relu(lin(w, "p1", torch.cat([zb, av, hz], -1)))))))
    return z, torch.stack(outs, 1).reshape(B, k, HZ, M.D)


run = run_tx if a.arch == "tx" else run_pool


def branch_parts(pred, tgt, m):
    mm = m.unsqueeze(-1)
    n = m.sum().clamp(min=1.0)
    plain = (((pred - tgt) ** 2).mean(-1) * m).sum() / n
    cnt = mm.sum(1, keepdim=True).clamp(min=1.0)
    cp = pred - (pred * mm).sum(1, keepdim=True) / cnt
    ct = tgt - (tgt * mm).sum(1, keepdim=True) / cnt
    diff = (((cp - ct) ** 2).mean(-1) * m).sum() / n
    size = ((ct ** 2).mean(-1) * m).sum() / n
    return plain, diff, size


def losses(b):
    G = b["g_state"].shape[0]
    zr, pr = run(P, b["r_state"], b["r_ids"], b["r_feats"], b["r_mask"], b["r_act"], b["r_aid"])
    with torch.no_grad():
        y1 = run(Tg, b["y1_state"], b["y1_ids"], b["y1_feats"], b["y1_mask"])[0]
        y4 = run(Tg, b["y4_state"], b["y4_ids"], b["y4_feats"], b["y4_mask"])[0]
        t1 = run(Tg, b["t1_state"], b["t1_ids"], b["t1_feats"], b["t1_mask"])[0].reshape(G, K, M.D)
        t4 = run(Tg, b["t4_state"], b["t4_ids"], b["t4_feats"], b["t4_mask"])[0].reshape(G, K, M.D)
        ts = run(Tg, b["ts_state"], b["ts_ids"], b["ts_feats"], b["ts_mask"])[0].reshape(G, K, M.D) if a.settle else None
    l_p1 = ((pr[:, 0, 0] - y1) ** 2).mean()
    l_p4 = (((pr[:, 0, 1] - y4) ** 2).mean(1) * b["r_m4"]).sum() / b["r_m4"].sum().clamp(min=1.0)
    zc = zr - zr.mean(0)
    std = (zc.square().mean(0) + 1e-4).sqrt()
    l_var = torch.relu(1.0 - std).mean()
    cov = zc.T @ zc / (zr.shape[0] - 1)
    l_cov = (cov.square().sum() - torch.diagonal(cov).square().sum()) / M.D
    l_copy = ((zr.detach() - y1) ** 2).mean()
    _, pg = run(P, b["g_state"], b["g_ids"], b["g_feats"], b["g_mask"], b["g_act"], b["g_aid"])
    bp1, bd1, bs1 = branch_parts(pg[:, :, 0], t1, b["m1"])
    bp4, bd4, bs4 = branch_parts(pg[:, :, 1], t4, b["m4"])
    total = l_p1 + l_p4 + a.w_var * l_var + a.w_cov * l_cov + a.w_branch * (bp1 + bp4 + a.w_diff * (bd1 + bd4))
    parts = [l_p1, l_p4, l_var, l_cov, l_copy, bp1, bd1, bs1, bp4, bd4, bs4]
    if a.settle:
        bpt, bdt, bst = branch_parts(pg[:, :, 2], ts, b["mt"])
        total = total + a.w_branch * (bpt + a.w_diff * bdt)
        parts += [bpt, bdt, bst]
    if E is not None:
        ze, _ = run(P, b["e_state"], b["e_ids"], b["e_feats"], b["e_mask"])
        lg = (torch.relu(ze @ P["ve1.w"] + P["ve1.b"]) @ P["ve2.w"])[:, 0] + P["ve2.b"][0]
        l_e = torch.nn.functional.binary_cross_entropy_with_logits(lg, torch.sigmoid(b["e_ev"]))
        total = total + a.w_eval * l_e
        parts += [l_e]
    return total, parts


NAMES = ["total", "pred1", "pred4", "var", "cov", "copy1", "br_p1", "br_d1", "br_s1", "br_p4", "br_d4", "br_s4"] + (["br_pt", "br_dt", "br_st"] if a.settle else []) + (["eval_bce"] if E is not None else [])
opt = torch.optim.AdamW([v for k, v in P.items() if k.split(".")[0] not in ("v1", "v2")], lr=lr0, weight_decay=1e-4)  # V: stage 2


def rows(prefix, idx, drop=0.0):
    m = d["tok_mask"][idx].astype(np.float32)
    if drop:
        m = m * (rng.random(m.shape) >= drop)
    return {prefix + "_state": d["state"][idx], prefix + "_ids": d["tok_ids"][idx], prefix + "_feats": d["tok_feats"][idx].astype(np.float32), prefix + "_mask": m}


def make_batch(ridx, gidx, drop):
    b = rows("r", ridx, drop)
    b["r_act"] = d["act"][ridx][:, None]
    b["r_aid"] = d["aid"][ridx][:, None].astype(np.int64)
    n1, n4 = d["nxt1"][ridx], d["nxt4"][ridx]
    b.update(rows("y1", n1))
    b.update(rows("y4", np.where(n4 >= 0, n4, n1)))
    b["r_m4"] = (n4 >= 0).astype(np.float32)
    G = len(gidx)
    gm = Bd["mask"][gidx].astype(np.float32)
    if drop:
        gm = gm * (rng.random(gm.shape) >= drop)
    b.update({"g_state": Bd["state"][gidx], "g_ids": Bd["ids"][gidx].astype(np.int64), "g_feats": Bd["feats"][gidx].astype(np.float32), "g_mask": gm,
              "g_act": Bd["act"][gidx], "g_aid": Bd["aid"][gidx].astype(np.int64), "m1": Bd["m1"][gidx], "m4": Bd["m4"][gidx]})
    if a.settle:
        b["mt"] = Bd["mt"][gidx]
    if E is not None:
        e = rng.choice(e_train, a.eb, replace=False)
        b.update({"e_state": E["state"][e], "e_ids": E["tok_ids"][e], "e_feats": E["tok_feats"][e].astype(np.float32),
                  "e_mask": E["tok_mask"][e].astype(np.float32), "e_ev": E["ev"][e]})
    for h, t in (("h1", "t1"), ("h4", "t4")) + ((("st", "ts"),) if a.settle else ()):
        b[t + "_state"] = Bd[h + "_state"][gidx].reshape(G * K, F.STATE_DIM)
        b[t + "_ids"] = Bd[h + "_ids"][gidx].reshape(G * K, T).astype(np.int64)
        b[t + "_feats"] = Bd[h + "_feats"][gidx].reshape(G * K, T, F.TOKEN_DIM).astype(np.float32)
        b[t + "_mask"] = Bd[h + "_mask"][gidx].reshape(G * K, T).astype(np.float32)
    return {k: torch.from_numpy(np.ascontiguousarray(v)).to(dev, non_blocking=True) for k, v in b.items()}


erng = np.random.default_rng(1)
eval_batches = [(erng.choice(r_held, a.rb, replace=False), erng.choice(b_held, a.groups, replace=False)) for _ in range(8)]
log = {"args": vars(a), "device": str(dev), "curve": [], "evals": []}
acc = np.zeros(len(NAMES))
t1 = time.time()
for it in range(1, a.steps + 1):
    for g in opt.param_groups:
        g["lr"] = lr0 * min(1.0, it / a.warmup)
    b = make_batch(rng.choice(r_train, a.rb, replace=False), rng.choice(b_train, a.groups, replace=False), a.token_dropout)
    total, parts = losses(b)
    opt.zero_grad(set_to_none=True)
    total.backward()
    opt.step()
    with torch.no_grad():
        for k in ENC:
            Tg[k].mul_(a.ema).add_(P[k].detach(), alpha=1.0 - a.ema)
    acc += np.array([float(total.detach())] + [float(x.detach()) for x in parts])
    if it % 100 == 0:
        row = {"step": it, **{k: float(v / 100) for k, v in zip(NAMES, acc)}}
        acc[:] = 0
        log["curve"].append(row)
        el = time.time() - t1
        print(f"step {it} {el:.0f}s ({it / el:.1f} it/s) " + " ".join(f"{k}={row[k]:.4f}" for k in NAMES), file=sys.stderr, flush=True)
    if it % a.eval_every == 0 or it == a.steps:
        with torch.no_grad():
            vals = np.mean([[float(total)] + [float(x) for x in parts] for total, parts in (losses(make_batch(r, g, 0.0)) for r, g in eval_batches)], axis=0)
        row = {"step": it, **{k: float(v) for k, v in zip(NAMES, vals)}}
        row["moves_explained_h1"] = 1.0 - row["br_d1"] / max(row["br_s1"], 1e-9)
        row["moves_explained_h4"] = 1.0 - row["br_d4"] / max(row["br_s4"], 1e-9)
        if a.settle:
            row["moves_explained_settled"] = 1.0 - row["br_dt"] / max(row["br_st"], 1e-9)
        log["evals"].append(row)
        print("  held-out " + " ".join(f"{k}={v:.4f}" for k, v in row.items() if k != "step"), file=sys.stderr, flush=True)
        json.dump(log, open(a.out + ".log.json", "w"))

# ---- stage 2: value head on frozen latents ------------------------------------------------------------------------
w = {k: v.detach().cpu().numpy().copy() for k, v in P.items()}
if a.arch == "tx":
    meta = {"format": "swu-jepa-tx/1", "D": M.D, "dm": a.dm, "layers": a.layers, "heads": a.heads, "tmax": T, "settle": int(a.settle),
            "horizons": list(M.HORIZONS), "state_dim": F.STATE_DIM, "action_dim": F.ACTION_DIM, "token_dim": F.TOKEN_DIM}
    net = X.NumpyTx(w, meta)
else:
    meta = {"format": "swu-jepa/1", "D": M.D, "horizons": list(M.HORIZONS), "state_dim": F.STATE_DIM, "action_dim": F.ACTION_DIM, "token_dim": F.TOKEN_DIM}
    net = M.NumpyJepa(w)

# the numpy forward the bot plays with must match the trained layers
chk = r_held[:16]
args = (d["state"][chk], d["tok_ids"][chk], d["tok_feats"][chk].astype(np.float32), d["tok_mask"][chk].astype(np.float32))
with torch.no_grad():
    zt, pt = run(P, *(torch.from_numpy(np.ascontiguousarray(x)).to(dev) for x in args), torch.from_numpy(d["act"][chk][:, None]).to(dev),
                 torch.from_numpy(d["aid"][chk][:, None].astype(np.int64)).to(dev))
if a.arch == "tx":
    zn, pn = net.forward(*args, d["act"][chk][:, None], d["aid"][chk][:, None].astype(np.int64))
    pt = pt[:, :, :pn.shape[2]]
else:
    zn = net.encode(*args)
    av = net.action(d["act"][chk], d["aid"][chk].astype(np.int64))
    pn = np.stack([net.predict(zn, av, 1), net.predict(zn, av, 4)], 1)[:, None]
err = max(float(np.abs(zt.cpu().numpy() - zn).max()), float(np.abs(pt.cpu().numpy() - pn).max()))
print(f"numpy forward vs torch: max difference {err:.2e}", file=sys.stderr, flush=True)
assert err < 1e-3, "numpy forward does not match the trained layers"


def latents(rws, chunk=4096):
    zs, p1s, p4s = [], [], []
    with torch.no_grad():
        for k in range(0, len(rws), chunk):
            r = rws[k:k + chunk]
            tt = lambda x: torch.from_numpy(np.ascontiguousarray(x)).to(dev)
            z, p = run(P, tt(d["state"][r]), tt(d["tok_ids"][r]), tt(d["tok_feats"][r].astype(np.float32)), tt(d["tok_mask"][r].astype(np.float32)),
                       tt(d["act"][r][:, None]), tt(d["aid"][r][:, None].astype(np.int64)))
            zs.append(z.cpu().numpy())
            p1s.append(p[:, 0, 0].cpu().numpy())
            p4s.append(p[:, 0, 1].cpu().numpy())
    return np.concatenate(zs), np.concatenate(p1s), np.concatenate(p4s)


tv = time.time()
tr = rng.choice(r_train, min(300000, len(r_train)), replace=False)
he = rng.choice(r_held, min(60000, len(r_held)), replace=False)
zt_ = torch.from_numpy(np.concatenate(latents(tr))).to(dev)
yt_ = torch.from_numpy(np.tile(d["win"][tr].astype(np.float32), 3)).to(dev)
zh_ = torch.from_numpy(np.concatenate(latents(he))).to(dev)
yh_ = torch.from_numpy(np.tile(d["win"][he].astype(np.float32), 3)).to(dev)
print(f"value stage: {len(zt_)} train / {len(zh_)} held latents in {time.time() - tv:.0f}s", file=sys.stderr, flush=True)
vr = np.random.default_rng(a.seed + 7)
vp = {}
for k in ("v1.w", "v2.w"):
    sh = HEADS[k]
    vp[k] = torch.tensor((vr.uniform(-1, 1, sh) * np.sqrt(6.0 / (sh[0] + sh[1]))).astype(np.float32), device=dev, requires_grad=True)
for k in ("v1.b", "v2.b"):
    vp[k] = torch.zeros(HEADS[k], device=dev, requires_grad=True)
vopt = torch.optim.AdamW(list(vp.values()), lr=1e-3, weight_decay=1e-2)
V = lambda z: (torch.relu(z @ vp["v1.w"] + vp["v1.b"]) @ vp["v2.w"])[:, 0] + vp["v2.b"][0]
bce = torch.nn.functional.binary_cross_entropy_with_logits
best, vcurve = None, []
for it in range(1, a.value_steps + 1):
    idx = torch.randint(0, len(zt_), (2048,), device=dev)
    l = bce(V(torch.nn.functional.dropout(zt_[idx], 0.1)), yt_[idx])
    vopt.zero_grad(set_to_none=True)
    l.backward()
    vopt.step()
    if it % 100 == 0:
        with torch.no_grad():
            lg = V(zh_)
            loss = float(bce(lg, yh_))
            n = len(he)
            accs = [float(((lg[q * n:(q + 1) * n] > 0).float() == yh_[q * n:(q + 1) * n]).float().mean()) for q in range(3)]
        vcurve.append({"step": it, "held_bce": loss, "acc": accs})
        if best is None or loss < best[0]:
            best = (loss, it, {k: v.detach().cpu().numpy().copy() for k, v in vp.items()}, accs)
w.update(best[2])
print(f"value head: best held-out BCE {best[0]:.4f} at step {best[1]}, accuracy on z / ẑ1 / ẑ4: " + " / ".join(f"{x:.3f}" for x in best[3]),
      file=sys.stderr, flush=True)
log["value"] = {"best_step": best[1], "held_bce": best[0], "acc": best[3], "curve": vcurve}

yard = b_held if len(b_held) <= a.yard_points else np.sort(np.random.default_rng(a.seed + 2).choice(b_held, a.yard_points, replace=False))
ys = yardstick(net, Bd, yard)
log["yardstick"] = ys
for h, v in ys.items():
    print(f"  yardstick {h}: top-1 {v['top1']:.3f} (chance {v['chance']:.3f}) median rho {v['rho_median']:.2f} "
          f"spread imagined {v['spread_imagined'] * 100:.1f} / real {v['spread_real'] * 100:.1f} pts ({v['points']} points)", file=sys.stderr)
if a.test_pack and a.test_judge:
    # one evaluator grades every model (yardstick.py --judge) on games outside this run's data
    TB = dict(np.load(a.test_pack))
    J = np.load(a.test_judge)
    assert np.array_equal(J["game"], TB["game"]), "--test-judge was made from other branch data"
    tidx = held_points(TB)
    tidx = tidx[J["judged"][tidx]]
    ys = yardstick(net, TB, tidx, {1: J["ev1"], 4: J["ev4"], "s": J["evt"]})
    log["yardstick_fixed"] = ys
    for h, v in ys.items():
        print(f"  fixed judge {h}: top-1 {v['top1']:.3f} (chance {v['chance']:.3f}) median rho {v['rho_median']:.2f} ({v['points']} points)", file=sys.stderr)
M.save_safetensors(a.out + ".safetensors", w, meta)
log["seconds"] = round(time.time() - t0)
json.dump(log, open(a.out + ".log.json", "w"))
print(f"wrote {a.out}.safetensors in {time.time() - t0:.0f}s", file=sys.stderr)
