"""Does knowing the game so far and both deck lists help the JEPA represent the situation? (Eric, 2026-10-15: feed the
model the whole game as a sequence of moves and train it on how well it represents the situation; and it needs to know
all the possible cards, as humans do.)

python3 hist_train.py --pack data/pack-h.npz --target models/tx-t10.safetensors --out runs/hist [--steps 6000]

The pack comes from data.py --labels on games written by from_replays.js --labels (the opponent's hand is the label).
Four models of the same width and depth, seed and batches, differing in what they read at a decision (each tensor is
drawn from its own seed, so the layers they share start with the same weights):
  base  what tx-t10 reads: the state vector and the card tokens (leaders, bases, both boards, my hand)
  snap  base + both discard piles (public, but no model reads them today)
  pool  snap + the unseen cards of both deck lists, one token per distinct card with the copies left: what my deck
        can still draw and what the opponent's hand and deck can hold (the protocol's hello gives both lists)
  hist  pool + the seat's own earlier decisions in this game, one token per decision: its state vector then, the move
        it chose, its cards then (pooled) and how the state changed until its next decision (what the opponent did
        meanwhile). Only what the seat saw, so the same history exists when the bot plays.
Each learns from its latent z (pool and hist add their hand guess to the card-counting one below):
  the JEPA futures: the frozen target model's latent (--target) of this seat's next and 4th next decision after its
  move; who wins; the opponent's hand (a set of card ids); the opponent's next move (its hashed id).
Held-out games (--hold) report: moves explained at h1 and h4 (1 - error / error of "nothing changes"), win log-loss
and accuracy, opponent-hand log-loss (nats per position, over the 2,048 card buckets) and recall at hand size (the
share of the true cards among the top-n guesses, n = the hand's distinct cards), and the opponent's next move
(log-loss, top-1, top-5). The prior row knows only the opponent's leader (frequencies on the training games); the
count row counts cards as a human does (the hand is handCount cards drawn from the opponent's unseen cards); the
target row is the target model's own forecasts and value head.
--probe-only trains the win, hand and next-move heads on a detached z, so the latent is shaped by the JEPA losses
alone and the heads read what those put there.
Packs without --labels skip the hand; packs without `disc` or `pool` (older data.py, games without deck lists) skip
those tokens.
"""
import argparse
import json
import math
import os
import sys
import time
import zlib

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402
import model as M  # noqa: E402
import tx_model as X  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pack", required=True, help="data.py output (with --labels for the hand)")
ap.add_argument("--target", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "tx-t10.safetensors"))
ap.add_argument("--out", required=True, help="writes <out>.json and <out>-<variant>.pt")
ap.add_argument("--variants", default="base,snap,pool,hist")
ap.add_argument("--steps", type=int, default=6000)
ap.add_argument("--batch", type=int, default=256)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--dm", type=int, default=64)
ap.add_argument("--layers", type=int, default=2)
ap.add_argument("--heads", type=int, default=4)
ap.add_argument("--hmax", type=int, default=48, help="earlier decisions of the seat in the history (the most recent)")
ap.add_argument("--hold", type=float, default=0.1, help="share of games held out")
ap.add_argument("--w-win", type=float, default=0.5)
ap.add_argument("--w-hand", type=float, default=1.0)
ap.add_argument("--w-move", type=float, default=0.5)
ap.add_argument("--probe-only", action="store_true")
ap.add_argument("--eval-every", type=int, default=1000)
ap.add_argument("--eval-rows", type=int, default=20000)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--device", default=None)
a = ap.parse_args()

dev = torch.device(a.device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"))
NB = F.ID_BUCKETS
OPP_LEADER = F.TOKEN_SLOTS.index("oppLeader")

# ---- data ----
t0 = time.time()
with np.load(a.pack) as z:
    d = {k: z[k] for k in z.files if k not in ("bot",)}
N = len(d["state"])
target, tmeta = X.load(a.target)
T = int(tmeta.get("tmax", d["tok_ids"].shape[1]))
for k in ("tok_ids", "tok_feats", "tok_mask"):
    d[k] = d[k][:, :T]
HAS_HAND = "ohand" in d
HAS_DISC = "disc" in d
HAS_POOL = "pool" in d and bool((d["pool"] >= 0).any())
variants = [v for v in a.variants.split(",") if v]
if not HAS_DISC:
    print("no discard piles in this pack (older data.py): snap and hist read no discards", file=sys.stderr)
if not HAS_POOL:
    print("no deck lists in this pack (from_replays.js before deck lists, or older data.py): pool and hist read no unseen cards", file=sys.stderr)
if not HAS_HAND:
    print("no opponent hands in this pack (data.py --labels): the hand head is off", file=sys.stderr)

n1 = d["nxt1"].astype(np.int64)
prev = np.full(N, -1, np.int64)
prev[n1[n1 >= 0]] = np.nonzero(n1 >= 0)[0]
if "gid" in d and "seat" in d:
    gid, seat = d["gid"].astype(np.int64), d["seat"].astype(np.int64)
else:
    # older packs: a game is a run of equal `game` values; its seats are the two nxt1 chains, p1's starting first
    gid = np.cumsum(np.r_[0, d["game"][1:] != d["game"][:-1]])
    root = np.arange(N)
    for r in range(N):
        if prev[r] >= 0:
            root[r] = root[prev[r]]
    first = np.r_[0, np.nonzero(gid[1:] != gid[:-1])[0] + 1]
    seat = (root != first[gid]).astype(np.int64)

# history: the seat's earlier decisions, the most recent last; -1 pads the front
H = a.hmax
hidx = np.full((N, H), -1, np.int64)
cur = prev.copy()
for k in range(H - 1, -1, -1):
    hidx[:, k] = cur
    cur = np.where(cur >= 0, prev[np.maximum(cur, 0)], -1)
# the decision that follows each history entry (the next one in the history, or the current row)
hnext = np.concatenate([hidx[:, 1:], np.arange(N)[:, None]], 1)
hnext = np.where(hidx >= 0, np.where(hnext >= 0, hnext, np.arange(N)[:, None]), -1)

# the opponent's next decision in the game
onext = np.full(N, -1, np.int64)
nx = [-1, -1]
for r in range(N - 1, -1, -1):
    if r == N - 1 or gid[r] != gid[r + 1]:
        nx = [-1, -1]
    onext[r] = nx[1 - seat[r]]
    nx[seat[r]] = r
oaid = np.where(onext >= 0, d["aid"][np.maximum(onext, 0)], -1).astype(np.int64)

# opponent leader bucket (for the prior)
lead_pos = d["tok_feats"][:, :, OPP_LEADER].astype(np.float32) * d["tok_mask"]
oleader = np.where(lead_pos.max(1) > 0, d["tok_ids"][np.arange(N), lead_pos.argmax(1)], -1).astype(np.int64)

# held out by the game's seed, so a game recorded twice (same seed, decks and bots) never sits on both sides
ugames = np.unique(gid)
useeds = np.unique(d["game"])
perm = np.random.default_rng(a.seed).permutation(useeds)
held_seeds = set(perm[:max(1, int(len(useeds) * a.hold))].tolist())
held = np.array([s in held_seeds for s in d["game"].tolist()])
held_games = set(gid[held].tolist())
tr_rows, te_rows = np.nonzero(~held)[0], np.nonzero(held)[0]
te_eval = te_rows if len(te_rows) <= a.eval_rows else np.sort(np.random.default_rng(a.seed + 1).choice(te_rows, a.eval_rows, replace=False))


def hand_hot(rows):
    y = np.zeros((len(rows), NB), np.float32)
    if HAS_HAND:
        oh = d["ohand"][rows].astype(np.int64)
        r, c = np.nonzero(oh >= 0)
        y[r, oh[r, c]] = 1.0
    return y


# ---- frozen targets: the target model's latent of every row ----
cache, fresh = X.latent_cache(a.pack, a.target)
if fresh and np.load(cache, mmap_mode="r").shape[0] == N:
    zt = np.load(cache)
else:
    zt = np.concatenate([target.forward(d["state"][k:k + 2048], d["tok_ids"][k:k + 2048].astype(np.int64),
                                        d["tok_feats"][k:k + 2048].astype(np.float32), d["tok_mask"][k:k + 2048].astype(np.float32))[0]
                         for k in range(0, N, 2048)]).astype(np.float32)
    np.save(cache, zt)
print(f"{N} rows, {len(ugames)} games ({len(held_games)} held out), hand labels {HAS_HAND}, discards {HAS_DISC}, unseen cards {HAS_POOL}, "
      f"targets from {os.path.basename(a.target)} in {time.time() - t0:.0f}s, device {dev}", file=sys.stderr)


# ---- prior: the opponent's leader only ----
leaders, lidx = np.unique(oleader[tr_rows], return_inverse=True)
hand_sum = np.zeros((len(leaders), NB))  # per opponent leader: positions whose opponent holds each card
for k in range(0, len(tr_rows), 8192):
    li = lidx[k:k + 8192]
    np.add.at(hand_sum, li, hand_hot(tr_rows[k:k + 8192]))
lead_n = np.bincount(lidx, minlength=len(leaders)).astype(np.float64)
glob_h = (hand_sum.sum(0) + 0.5) / (len(tr_rows) + 1.0)
mv = oaid[tr_rows]
glob_m = np.bincount(mv[mv >= 0], minlength=NB).astype(np.float64) + 0.1
glob_m /= glob_m.sum()


def prior_metrics():
    alpha = 5.0
    ph, pm = {}, {}
    for j, lid in enumerate(leaders):
        sel = lidx == j
        ph[lid] = (hand_sum[j] + alpha * glob_h) / (lead_n[j] + alpha)
        c = np.bincount(mv[sel & (mv >= 0)], minlength=NB).astype(np.float64)
        pm[lid] = (c + alpha * glob_m) / (c.sum() + alpha)
    rows = te_eval
    hp = np.stack([ph.get(l, glob_h) for l in oleader[rows]]).clip(1e-6, 1 - 1e-6)
    mp = np.stack([pm.get(l, glob_m) for l in oleader[rows]])
    return score(rows, logit_h=np.log(hp) - np.log1p(-hp), logp_m=np.log(mp))


def count_logits(rows):
    """card counting, as a human does it: the opponent's hand is handCount cards drawn from their unseen cards.
    [len(rows), NB] logits of each card bucket being in the opponent's hand."""
    pc = d["pool"][rows, 1].astype(np.int64)
    pk = d["poolk"][rows, 1].astype(np.float64)
    left = pk.sum(1, keepdims=True).clip(min=1.0)
    h = np.rint(d["state"][rows, F.SIDE + 5] * 10.0)[:, None]  # opponent's handCount (features.side_features)
    p = 1.0 - (1.0 - pk / left) ** h
    P = np.full((len(rows), NB), 1e-4)
    r, c = np.nonzero(pc >= 0)
    np.maximum.at(P, (r, pc[r, c]), p[r, c])
    P = P.clip(1e-6, 1 - 1e-6)
    return (np.log(P) - np.log1p(-P)).astype(np.float32)


def count_metrics():
    return score(te_eval, logit_h=count_logits(te_eval))


def target_metrics():
    """the target model itself: its h1/h4 forecasts of the chosen move and its value head (no hand or move heads)"""
    z1, z4 = [], []
    for k in range(0, len(te_eval), 1024):
        r = te_eval[k:k + 1024]
        _, zp = target.forward(d["state"][r], d["tok_ids"][r].astype(np.int64), d["tok_feats"][r].astype(np.float32),
                               d["tok_mask"][r].astype(np.float32), d["act"][r][:, None], d["aid"][r][:, None].astype(np.int64), hsel=[0, 1])
        z1.append(zp[:, 0, 0])
        z4.append(zp[:, 0, 1])
    return score(te_eval, np.concatenate(z1), np.concatenate(z4), target.value(zt[te_eval]))


def score(rows, z1=None, z4=None, vlogit=None, logit_h=None, logp_m=None):
    out = {}
    if z1 is not None:
        for h, zp, nxt in ((1, z1, d["nxt1"]), (4, z4, d["nxt4"])):
            nn_ = nxt[rows]
            ok = nn_ >= 0
            tgt = zt[nn_[ok]]
            out[f"explained_h{h}"] = float(1.0 - ((zp[ok] - tgt) ** 2).sum() / ((zt[rows[ok]] - tgt) ** 2).sum())
    if vlogit is not None:
        y = d["win"][rows].astype(np.float32)
        p = 1.0 / (1.0 + np.exp(-vlogit))
        out["win_logloss"] = float(-(y * np.log(p + 1e-7) + (1 - y) * np.log(1 - p + 1e-7)).mean())
        out["win_acc"] = float(((p > 0.5) == (y > 0.5)).mean())
    if logit_h is not None and HAS_HAND:
        y = hand_hot(rows)
        lp = -np.logaddexp(0, -logit_h)
        lq = -np.logaddexp(0, logit_h)
        out["hand_logloss"] = float(-(y * lp + (1 - y) * lq).sum(1).mean())
        n = y.sum(1).astype(np.int64)
        has = n > 0
        top = np.argsort(-logit_h[has], 1)
        yh, nh = y[has], n[has]  # once: indexing inside the loop copied the whole array for every row
        hits = [yh[i, top[i, :nh[i]]].sum() / nh[i] for i in range(len(nh))]
        out["hand_recall"] = float(np.mean(hits)) if hits else float("nan")
    if logp_m is not None:
        ok = oaid[rows] >= 0
        t = oaid[rows][ok]
        lp = logp_m[ok]
        out["move_logloss"] = float(-lp[np.arange(len(t)), t].mean())
        rank = (lp > lp[np.arange(len(t)), t][:, None]).sum(1)
        out["move_top1"] = float((rank < 1).mean())
        out["move_top5"] = float((rank < 5).mean())
    return out


# ---- model ----
def shapes(variant):
    dm = a.dm
    s = {**{k: (n, M.EMB) for k, n in M.EMB_TABLES.items()},
         "tin.w": (F.TOKEN_DIM + M.EMB, dm), "tin.b": (dm,), "sin.w": (F.STATE_DIM, dm), "sin.b": (dm,)}
    if variant in ("snap", "pool", "hist") and HAS_DISC:
        s.update({"din.w": (M.EMB, dm), "din.b": (dm,), "dslot": (2, dm)})
    if variant in ("pool", "hist") and HAS_POOL:
        s.update({"pin.w": (M.EMB + 1, dm), "pin.b": (dm,), "pslot": (2, dm)})
    if variant == "hist":
        s.update({"hin.w": (2 * F.STATE_DIM + F.ACTION_DIM + M.EMB + dm, dm), "hin.b": (dm,), "hpos": (H, dm)})
    for i in range(a.layers):
        s.update({f"b{i}.ln1.g": (dm,), f"b{i}.ln1.b": (dm,), f"b{i}.ln2.g": (dm,), f"b{i}.ln2.b": (dm,),
                  f"b{i}.f1.w": (dm, 2 * dm), f"b{i}.f1.b": (2 * dm,), f"b{i}.f2.w": (2 * dm, dm), f"b{i}.f2.b": (dm,)})
        for p in "qkvo":
            s.update({f"b{i}.{p}.w": (dm, dm), f"b{i}.{p}.b": (dm,)})
    s.update({"lnf.g": (dm,), "lnf.b": (dm,), "zo1.w": (2 * dm + F.STATE_DIM, 256), "zo1.b": (256,), "zo2.w": (256, M.D), "zo2.b": (M.D,),
              "ain.w": (F.ACTION_DIM + M.EMB, dm), "ain.b": (dm,), "hor": (2, dm),
              "p1.w": (M.D + dm, 256), "p1.b": (256,), "p2.w": (256, M.D), "p2.b": (M.D,),
              "v1.w": (M.D, 64), "v1.b": (64,), "v2.w": (64, 1), "v2.b": (1,),
              "oh1.w": (M.D, 256), "oh1.b": (256,), "oh2.w": (256, NB), "oh2.b": (NB,),
              "om1.w": (M.D, 256), "om1.b": (256,), "om2.w": (256, NB), "om2.b": (NB,)})
    return s


def init(variant, seed):
    p = {}
    for name, shape in shapes(variant).items():
        g = np.random.default_rng([seed, zlib.crc32(name.encode())])  # per tensor: shared layers start equal in every variant
        if name in M.EMB_TABLES:
            p[name] = g.normal(0, 0.1, shape)
        elif name.endswith(".g"):
            p[name] = np.ones(shape)
        elif name in ("hor", "dslot", "pslot", "hpos"):
            p[name] = g.normal(0, 0.5 if name == "hor" else 0.1, shape)
        elif name.endswith(".w"):
            p[name] = g.uniform(-1, 1, shape) * np.sqrt(6.0 / (shape[0] + shape[1]))
        else:
            p[name] = np.zeros(shape)
    # start from the base rates, or, in a model that knows the lists, from counting cards (heads adds it)
    p["oh2.b"] = np.zeros(NB) if "pin.w" in p else np.log(glob_h) - np.log1p(-glob_h)
    p["om2.b"] = np.log(glob_m)
    return {k: torch.tensor(v, dtype=torch.float32, device=dev, requires_grad=True) for k, v in p.items()}


def lin(w, name, x):
    return x @ w[name + ".w"] + w[name + ".b"]


def ln(x, w, name):
    return torch.nn.functional.layer_norm(x, (x.shape[-1],), w[name + ".g"], w[name + ".b"], 1e-5)


def tt(x, dtype=torch.float32):
    return torch.as_tensor(np.ascontiguousarray(x), dtype=dtype, device=dev)


def cards(w, rows):
    """card tokens of rows (any shape S): [*S, T, dm] and their mask [*S, T]"""
    ids = tt(d["tok_ids"][rows].astype(np.int64), torch.long)
    return lin(w, "tin", torch.cat([tt(d["tok_feats"][rows].astype(np.float32)), M.embed(w, ids)], -1)), tt(d["tok_mask"][rows].astype(np.float32))


def encode(w, variant, rows):
    B = len(rows)
    dm, nh = a.dm, a.heads
    st = tt(d["state"][rows])
    ct, cm = cards(w, rows)
    xs, ms = [lin(w, "sin", st).unsqueeze(1), ct], [torch.ones(B, 1, device=dev), cm]
    if "din.w" in w:
        dc = d["disc"][rows].astype(np.int64)  # [B, 2, DISC]
        dt = lin(w, "din", M.embed(w, tt(np.maximum(dc, 0), torch.long))) + w["dslot"].reshape(1, 2, 1, dm)
        dmk = tt((dc >= 0).astype(np.float32))
        xs.append(dt.reshape(B, -1, dm))
        ms.append(dmk.reshape(B, -1))
    if "pin.w" in w:
        pc = d["pool"][rows].astype(np.int64)  # [B, 2, POOL]
        pk = tt(d["poolk"][rows].astype(np.float32) / 3.0).unsqueeze(-1)
        pt = lin(w, "pin", torch.cat([M.embed(w, tt(np.maximum(pc, 0), torch.long)), pk], -1)) + w["pslot"].reshape(1, 2, 1, dm)
        pmk = tt((pc >= 0).astype(np.float32))
        xs.append(pt.reshape(B, -1, dm))
        ms.append(pmk.reshape(B, -1))
    nctx = sum(m.shape[1] for m in ms[1:])
    if variant == "hist":
        hi = hidx[rows]
        hk = np.maximum(hi, 0)
        hn = np.maximum(hnext[rows], 0)
        hc, hm = cards(w, hk)  # [B, H, T, dm]
        hpool = (hc * hm.unsqueeze(-1)).sum(2) / hm.sum(2, keepdim=True).clamp(min=1.0)
        hs = d["state"][hk]
        feats = torch.cat([tt(hs), tt(d["act"][hk]), M.embed(w, tt(d["aid"][hk].astype(np.int64), torch.long)), hpool,
                           tt(d["state"][hn] - hs)], -1)
        xs.append(lin(w, "hin", feats) + w["hpos"].unsqueeze(0))
        ms.append(tt((hi >= 0).astype(np.float32)))
    x = torch.cat(xs, 1)
    kval = torch.cat(ms, 1)
    S = x.shape[1]
    bias = ((kval - 1.0) * 1e9).reshape(B, 1, 1, S)
    hd = dm // nh
    for i in range(a.layers):
        y = ln(x, w, f"b{i}.ln1")
        q, k, v = (lin(w, f"b{i}.{p}", y).reshape(B, S, nh, hd).transpose(1, 2) for p in "qkv")
        att = torch.softmax(q @ k.transpose(-2, -1) / math.sqrt(hd) + bias, -1)
        x = x + lin(w, f"b{i}.o", (att @ v).transpose(1, 2).reshape(B, S, dm))
        x = x + lin(w, f"b{i}.f2", torch.relu(lin(w, f"b{i}.f1", ln(x, w, f"b{i}.ln2"))))
    x = ln(x, w, "lnf")
    kv = kval[:, 1:1 + nctx].unsqueeze(-1)
    mean = (x[:, 1:1 + nctx] * kv).sum(1) / kv.sum(1).clamp(min=1.0)
    return lin(w, "zo2", torch.relu(lin(w, "zo1", torch.cat([x[:, 0], mean, st], -1))))


def heads(w, rows, z, variant):
    av = lin(w, "ain", torch.cat([tt(d["act"][rows]), M.embed(w, tt(d["aid"][rows].astype(np.int64), torch.long))], -1))
    zh = z.detach() if a.probe_only else z
    out = {}
    for h in (0, 1):
        out[f"z{h}"] = z + lin(w, "p2", torch.relu(lin(w, "p1", torch.cat([z, av + w["hor"][h]], -1))))
    out["v"] = lin(w, "v2", torch.relu(lin(w, "v1", zh)))[:, 0]
    out["hand"] = lin(w, "oh2", torch.relu(lin(w, "oh1", zh)))
    if "pin.w" in w and HAS_HAND:
        out["hand"] = out["hand"] + tt(count_logits(rows))  # a model that knows the lists starts from counting cards
    out["move"] = lin(w, "om2", torch.relu(lin(w, "om1", zh)))
    return out


def loss(w, variant, rows):
    o = heads(w, rows, encode(w, variant, rows), variant)
    parts = {}
    for h, nxt in ((0, d["nxt1"]), (1, d["nxt4"])):
        nn_ = nxt[rows]
        m = tt((nn_ >= 0).astype(np.float32))
        tgt = tt(zt[np.maximum(nn_, 0)])
        parts[f"h{h}"] = (((o[f"z{h}"] - tgt) ** 2).mean(1) * m).sum() / m.sum().clamp(min=1.0)
    parts["win"] = torch.nn.functional.binary_cross_entropy_with_logits(o["v"], tt(d["win"][rows].astype(np.float32)))
    total = parts["h0"] + parts["h1"] + a.w_win * parts["win"]
    if HAS_HAND:
        parts["hand"] = torch.nn.functional.binary_cross_entropy_with_logits(o["hand"], tt(hand_hot(rows)), reduction="none").sum(1).mean() / 10.0
        total = total + a.w_hand * parts["hand"]
    om = oaid[rows]
    if (om >= 0).any():
        sel = np.nonzero(om >= 0)[0]
        parts["move"] = torch.nn.functional.cross_entropy(o["move"][tt(sel, torch.long)], tt(om[sel], torch.long))
        total = total + a.w_move * parts["move"]
    return total, parts


@torch.no_grad()
def evaluate(w, variant):
    z1, z4, v, hl, ml = [], [], [], [], []
    for k in range(0, len(te_eval), 1024):
        rows = te_eval[k:k + 1024]
        o = heads(w, rows, encode(w, variant, rows), variant)
        z1.append(o["z0"].cpu().numpy())
        z4.append(o["z1"].cpu().numpy())
        v.append(o["v"].cpu().numpy())
        hl.append(o["hand"].cpu().numpy())
        ml.append(torch.log_softmax(o["move"], -1).cpu().numpy())
    cat = np.concatenate
    return score(te_eval, cat(z1), cat(z4), cat(v), cat(hl), cat(ml))


def train(variant):
    torch.manual_seed(a.seed)
    w = init(variant, a.seed)
    opt = torch.optim.AdamW(list(w.values()), lr=a.lr, weight_decay=1e-4)
    g = np.random.default_rng(a.seed + 7)  # the same batches for every variant
    curve = []
    t = time.time()
    run = {}
    for step in range(1, a.steps + 1):
        for pg in opt.param_groups:
            pg["lr"] = a.lr * min(1.0, step / 200) * 0.5 * (1 + math.cos(math.pi * step / a.steps))
        rows = g.choice(tr_rows, a.batch)
        total, parts = loss(w, variant, rows)
        opt.zero_grad()
        total.backward()
        opt.step()
        for k, v in parts.items():
            run[k] = run.get(k, 0.0) + float(v.detach())
        if step % a.eval_every == 0 or step == a.steps:
            ev = evaluate(w, variant)
            tr = {k: v / a.eval_every for k, v in run.items()}
            run = {}
            curve.append({"step": step, "train": tr, "held": ev})
            print(f"{variant} {step}: " + " ".join(f"{k} {v:.3f}" for k, v in ev.items()) + f"  ({time.time() - t:.0f}s)", file=sys.stderr)
    torch.save({k: v.detach().cpu() for k, v in w.items()}, f"{a.out}-{variant}.pt")
    return curve


os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
res = {"args": vars(a), "rows": int(N), "games": int(len(ugames)), "held_games": len(held_games), "held_rows": int(len(te_rows)),
       "prior": prior_metrics(), "target": target_metrics(), "variants": {}}
if HAS_POOL and HAS_HAND:
    res["count"] = count_metrics()
for name in ("prior", "count", "target"):
    if name not in res:
        continue
    print(f"{name}: " + " ".join(f"{k} {v:.3f}" for k, v in res[name].items()), file=sys.stderr)
for v in variants:
    res["variants"][v] = train(v)
    with open(a.out + ".json", "w") as fh:
        json.dump(res, fh, indent=1)

keys = ["explained_h1", "explained_h4", "win_logloss", "win_acc", "hand_logloss", "hand_recall", "move_logloss", "move_top1", "move_top5"]
print("\n" + f"{'':6s}" + "".join(f"{k:>14s}" for k in keys))
for name, m in [(k, res[k]) for k in ("prior", "count", "target") if k in res] + [(v, c[-1]["held"]) for v, c in res["variants"].items()]:
    print(f"{name:6s}" + "".join(f"{m[k]:14.3f}" if k in m else f"{'':>14s}" for k in keys))
print(f"wrote {a.out}.json")
