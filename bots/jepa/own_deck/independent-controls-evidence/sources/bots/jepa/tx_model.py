"""The transformer JEPA (format swu-jepa-tx/1): layers, and the numpy forward pass the bot plays with.

    [state] [card 1] ... [card T] [move 1, h1] [move 1, h4] ... [move K, h4]   one sequence, L pre-norm attention layers
    cards and the state token attend to each other (never to the moves)  -> z = readout(state token, mean of cards, state)
    each move token attends to every card, the state token and itself     -> its change: ẑ_h = z + P(z, move token)
So the change a move makes is computed from the cards the move is looking at, and many moves share one encoding.
Horizons: h = 1 and 4 (the mover's next and 4th next decision) and, in models trained with settled branches (meta
"settle"), h = "s": the board where the move has settled (anyone's next action window or the end of the action phase),
the position jepa_bot.py's planner simulates and judges.
Round tiers (meta "tiers" and "macros", models trained with tier_prep.py data): h = "r:<macro>" is the board where this
round's action phase ends if I play the move and then the rest of the round in that style (macros.js), and
h = "r2:<macro>" where the next round's action phase ends after that. Each horizon is one learned row added to the
move token, so a model with 3 macros has 3 + 6 tokens per move; `forward(hsel=...)` runs only the ones asked for.
"""
import hashlib
import os

import numpy as np

import features as F
import model as M

D = M.D           # latent size, as the v1 JEPA (the value head and the planner keep their shapes)
EMB = M.EMB
HORIZONS = M.HORIZONS
SETTLE = "s"


def _names(v):
    return [x for x in (v.split(",") if isinstance(v, str) else list(v or [])) if x]


def horizons(meta):
    """The horizons a model predicts, in the order of its move tokens."""
    base = list(HORIZONS) + ([SETTLE] if str(meta.get("settle", "0")) in ("1", "True") else [])
    return base + [f"{t}:{c}" for t in _names(meta.get("tiers")) for c in _names(meta.get("macros"))]


def macros(meta):
    return _names(meta.get("macros"))


def shapes(dm=64, layers=2, hz=len(HORIZONS)):
    ff = 2 * dm
    enc = {**{k: (n, EMB) for k, n in M.EMB_TABLES.items()},
           "tin.w": (F.TOKEN_DIM + EMB, dm), "tin.b": (dm,), "sin.w": (F.STATE_DIM, dm), "sin.b": (dm,)}
    for i in range(layers):
        enc.update({f"b{i}.ln1.g": (dm,), f"b{i}.ln1.b": (dm,), f"b{i}.ln2.g": (dm,), f"b{i}.ln2.b": (dm,),
                    f"b{i}.f1.w": (dm, ff), f"b{i}.f1.b": (ff,), f"b{i}.f2.w": (ff, dm), f"b{i}.f2.b": (dm,)})
        for p in "qkvo":
            enc.update({f"b{i}.{p}.w": (dm, dm), f"b{i}.{p}.b": (dm,)})
    enc.update({"lnf.g": (dm,), "lnf.b": (dm,), "zo1.w": (2 * dm + F.STATE_DIM, 256), "zo1.b": (256,), "zo2.w": (256, D), "zo2.b": (D,)})
    heads = {"ain.w": (F.ACTION_DIM + EMB, dm), "ain.b": (dm,), "hor": (hz, dm),
             "p1.w": (D + dm, 256), "p1.b": (256,), "p2.w": (256, D), "p2.b": (D,),
             "v1.w": (D, 64), "v1.b": (64,), "v2.w": (64, 1), "v2.b": (1,)}
    return enc, heads


def struct_mask(c, k, hz=len(HORIZONS)):
    """[S, S] additive mask for C context tokens then hz*K move tokens: a move token is seen only by itself."""
    s = c + hz * k
    m = np.zeros((s, s), np.float32)
    m[:, c:] = -1e9
    m[np.arange(c, s), np.arange(c, s)] = 0.0
    return m


def _ln(x, g, b):
    mu = x.mean(-1, keepdims=True)
    v = ((x - mu) ** 2).mean(-1, keepdims=True)
    return (x - mu) / np.sqrt(v + 1e-5) * g + b


def _softmax(x):
    x = x - x.max(-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(-1, keepdims=True)


class NumpyTx:
    """Same calls as model.NumpyJepa. `action` only packs the move rows; `predict` runs them as move tokens against the
    position of the last `encode` (one position at a time, as the bot asks), or use `forward` for batches."""

    def __init__(self, w, meta):
        self.w = w
        self.L = int(meta["layers"])
        self.H = int(meta["heads"])
        self.T = int(meta["tmax"])
        self.dm = int(meta["dm"])
        self.horizons = horizons(meta)
        self.macros = macros(meta)
        # horizons are run in groups: the move's own (1, 4, s) and, in tiered models, all round tiers together
        base = [i for i, h in enumerate(self.horizons) if not (isinstance(h, str) and ":" in h)]
        tiers = [i for i in range(len(self.horizons)) if i not in base]
        self.groups = [g for g in (base, tiers) if g]
        self._ctx = None
        self._cache = {}

    def lin(self, name, x):
        return x @ self.w[name + ".w"] + self.w[name + ".b"]

    def _ffn(self, i, x):
        w = self.w
        return self.lin(f"b{i}.f2", M.relu(self.lin(f"b{i}.f1", _ln(x, w[f"b{i}.ln2.g"], w[f"b{i}.ln2.b"]))))

    def _initial_context(self, state, ids, feats, mask, own_deck):
        """Extension point: legacy models retain precisely their original context."""
        if own_deck is not None:
            raise ValueError("own_deck requires the explicit own-deck model format")
        x = np.concatenate([self.lin("sin", state)[:, None], self.lin("tin", np.concatenate([feats, M.embed(self.w, ids)], -1))], 1)
        return x, np.concatenate([np.ones((len(state), 1), np.float32), mask], 1)

    def forward(self, state, ids, feats, mask, act=None, aid=None, hsel=None, *, own_deck=None):
        """state [B,73], ids/feats/mask [B,T..], act [B,K,62], aid [B,K] -> z [B,D], ẑ [B,K,len(hsel),D] or None.
        hsel: indexes into self.horizons of the move tokens to run (default all).
        Same numbers as one masked attention over [context, move tokens] (struct_mask, as the trainer runs it): context
        tokens never see the moves and a move token sees the context and itself, so the moves are computed beside the
        context in O(moves x context) instead of attending over the whole sequence."""
        w, T, dm, H = self.w, self.T, self.dm, self.H
        hors = list(range(len(self.horizons))) if hsel is None else list(hsel)
        hz = len(hors)
        ids, feats, mask = ids[:, :T], feats[:, :T].astype(np.float32), mask[:, :T].astype(np.float32)
        B, t = ids.shape
        x, kval = self._initial_context(state, ids, feats, mask, own_deck)
        c = x.shape[1]
        k = 0
        xm = None
        if act is not None:
            k = act.shape[1]
            a = self.lin("ain", np.concatenate([act, M.embed(w, aid)], -1))
            xm = (a[:, :, None, :] + w["hor"][hors][None, None]).reshape(B, hz * k, dm)
        bias = ((kval - 1.0) * 1e9)[:, None, None, :]  # [B,1,1,c]: padded cards are never seen
        hd = dm // H
        sc = 1.0 / float(np.sqrt(hd))  # a numpy float64 scalar would turn it all float64
        heads = lambda v, n: v.reshape(B, n, H, hd).transpose(0, 2, 1, 3)
        for i in range(self.L):
            y = _ln(x, w[f"b{i}.ln1.g"], w[f"b{i}.ln1.b"])
            q, kk, v = (heads(self.lin(f"b{i}.{p}", y), c) for p in "qkv")
            att = _softmax(q @ kk.transpose(0, 1, 3, 2) * sc + bias)
            if k:
                ym = _ln(xm, w[f"b{i}.ln1.g"], w[f"b{i}.ln1.b"])
                qm, km, vm = (heads(self.lin(f"b{i}.{p}", ym), hz * k) for p in "qkv")
                am = _softmax(np.concatenate([qm @ kk.transpose(0, 1, 3, 2) * sc + bias, (qm * km).sum(-1, keepdims=True) * sc], -1))
                om = am[..., :c] @ v + am[..., c:] * vm
                xm = xm + self.lin(f"b{i}.o", om.transpose(0, 2, 1, 3).reshape(B, hz * k, dm))
                xm = xm + self._ffn(i, xm)
            x = x + self.lin(f"b{i}.o", (att @ v).transpose(0, 2, 1, 3).reshape(B, c, dm))
            x = x + self._ffn(i, x)
        x = _ln(x, w["lnf.g"], w["lnf.b"])
        kv = kval[:, :, None]
        mean = (x * kv).sum(1) / kv.sum(1)
        z = self.lin("zo2", M.relu(self.lin("zo1", np.concatenate([x[:, 0], mean, state], -1))))
        if not k:
            return z, None
        ao = _ln(xm, w["lnf.g"], w["lnf.b"]).reshape(B, k, hz, dm)
        zb = np.broadcast_to(z[:, None, None, :], (B, k, hz, D))
        return z, zb + self.lin("p2", M.relu(self.lin("p1", np.concatenate([zb, ao], -1))))

    def encode(self, state, tok_ids, tok_feats, tok_mask, *, own_deck=None):
        z, _ = self.forward(state, tok_ids, tok_feats, tok_mask, own_deck=own_deck)
        self._ctx = (state, tok_ids, tok_feats, tok_mask) if len(state) == 1 else None
        self._own_deck = own_deck
        self._cache = {}
        return z

    def action(self, act, aid):
        return (np.asarray(act, np.float32), np.asarray(aid, np.int64))

    # move tokens per forward pass, so memory stays flat when a prompt offers ~2,000 options (a move token sees only
    # the position and itself, so chunks give the same predictions)
    CHUNK_TOKENS = 1024

    def predict(self, z, a, h):
        """ẑ_h for every move of `a` against the last encoded position: [n, D]. Runs the whole group of horizons h
        belongs to (the move's own, or the round tiers) once per set of moves and keeps it."""
        if self._ctx is None:
            raise ValueError("NumpyTx.predict needs the single position of the last encode (use forward for batches)")
        hi = self.horizons.index(h)
        g = next(n for n, grp in enumerate(self.groups) if hi in grp)
        if g not in self._cache or self._cache[g][0] is not a:
            act, aid = a
            grp = self.groups[g]
            step = max(1, self.CHUNK_TOKENS // len(grp))
            parts = [self.forward(*self._ctx, act[None, k:k + step], aid[None, k:k + step], hsel=grp, own_deck=self._own_deck)[1][0] for k in range(0, len(act), step)]
            self._cache[g] = (a, np.concatenate(parts) if parts else np.zeros((0, len(grp), D), np.float32))
        return self._cache[g][1][:, self.groups[g].index(hi)]

    def value(self, z):
        return self.lin("v2", M.relu(self.lin("v1", z)))[..., 0]

    def probe(self, z):
        if "probe.w" not in self.w:
            return None
        return z @ self.w["probe.w"] + self.w["probe.b"]


def load(path):
    """A JEPA file of either format: NumpyTx for swu-jepa-tx/1, else model.NumpyJepa."""
    w, meta = M.load_safetensors(path)
    if meta.get("format") == "swu-jepa-tx/1":
        return NumpyTx(w, meta), meta
    if meta.get("format") == "swu-jepa-tx-own-deck/1":
        from own_deck_model import NumpyOwnDeckTx
        return NumpyOwnDeckTx(w, meta), meta
    return M.NumpyJepa(w), meta


def latent_cache(pack, model_path):
    """Where hist_train.py and fit_value.py keep a model's latents of every row of a pack, and whether that file is usable.
    The name carries a hash of the model file, and a cache older than the pack is stale, so a pack rebuilt in place or
    another model with the same file name is encoded again."""
    with open(model_path, "rb") as f:
        tag = hashlib.sha256(f.read()).hexdigest()[:12]
    path = f"{pack}.{os.path.basename(model_path).replace('.safetensors', '')}-{tag}.zt.npy"
    return path, os.path.exists(path) and os.path.getmtime(path) >= os.path.getmtime(pack)
