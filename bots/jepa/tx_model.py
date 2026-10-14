"""The transformer JEPA (format swu-jepa-tx/1): layers, and the numpy forward pass the bot plays with.

    [state] [card 1] ... [card T] [move 1, h1] [move 1, h4] ... [move K, h4]   one sequence, L pre-norm attention layers
    cards and the state token attend to each other (never to the moves)  -> z = readout(state token, mean of cards, state)
    each move token attends to every card, the state token and itself     -> its change: ẑ_h = z + P(z, move token)
So the change a move makes is computed from the cards the move is looking at, and many moves share one encoding.
Horizons: h = 1 and 4 (the mover's next and 4th next decision) and, in models trained with settled branches (meta
"settle"), h = "s": the board where the move has settled (anyone's next action window or the end of the action phase),
the position jepa_bot.py's planner simulates and judges.
"""
import numpy as np

import features as F
import model as M

D = M.D           # latent size, as the v1 JEPA (the value head and the planner keep their shapes)
EMB = M.EMB
HORIZONS = M.HORIZONS
SETTLE = "s"


def horizons(meta):
    """The horizons a model predicts, in the order of its move tokens."""
    return list(HORIZONS) + ([SETTLE] if str(meta.get("settle", "0")) in ("1", "True") else [])


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
        self._ctx = None
        self._cache = None

    def lin(self, name, x):
        return x @ self.w[name + ".w"] + self.w[name + ".b"]

    def forward(self, state, ids, feats, mask, act=None, aid=None):
        """state [B,73], ids/feats/mask [B,T..], act [B,K,62], aid [B,K] -> z [B,D], ẑ [B,K,len(self.horizons),D] or None"""
        w, T, dm, H = self.w, self.T, self.dm, self.H
        hz = len(self.horizons)
        ids, feats, mask = ids[:, :T], feats[:, :T].astype(np.float32), mask[:, :T].astype(np.float32)
        B, t = ids.shape
        x = np.concatenate([self.lin("sin", state)[:, None], self.lin("tin", np.concatenate([feats, M.embed(w, ids)], -1))], 1)
        kval = np.concatenate([np.ones((B, 1), np.float32), mask], 1)
        c = 1 + t
        k = 0
        if act is not None:
            k = act.shape[1]
            a = self.lin("ain", np.concatenate([act, M.embed(w, aid)], -1))
            a = (a[:, :, None, :] + w["hor"][None, None]).reshape(B, hz * k, dm)
            x = np.concatenate([x, a], 1)
            kval = np.concatenate([kval, np.ones((B, hz * k), np.float32)], 1)
        S = x.shape[1]
        bias = ((kval - 1.0) * 1e9)[:, None, None, :]
        if k:
            bias = bias + struct_mask(c, k, hz)[None, None]
        hd = dm // H
        for i in range(self.L):
            y = _ln(x, w[f"b{i}.ln1.g"], w[f"b{i}.ln1.b"])
            q = self.lin(f"b{i}.q", y).reshape(B, S, H, hd).transpose(0, 2, 1, 3)
            kk = self.lin(f"b{i}.k", y).reshape(B, S, H, hd).transpose(0, 2, 1, 3)
            v = self.lin(f"b{i}.v", y).reshape(B, S, H, hd).transpose(0, 2, 1, 3)
            att = _softmax(q @ kk.transpose(0, 1, 3, 2) / float(np.sqrt(hd)) + bias)  # a numpy float64 scalar would turn it all float64
            x = x + self.lin(f"b{i}.o", (att @ v).transpose(0, 2, 1, 3).reshape(B, S, dm))
            x = x + self.lin(f"b{i}.f2", M.relu(self.lin(f"b{i}.f1", _ln(x, w[f"b{i}.ln2.g"], w[f"b{i}.ln2.b"]))))
        x = _ln(x, w["lnf.g"], w["lnf.b"])
        kv = kval[:, :c, None]
        mean = (x[:, :c] * kv).sum(1) / kv.sum(1)
        z = self.lin("zo2", M.relu(self.lin("zo1", np.concatenate([x[:, 0], mean, state], -1))))
        if not k:
            return z, None
        ao = x[:, c:].reshape(B, k, hz, dm)
        zb = np.broadcast_to(z[:, None, None, :], (B, k, hz, D))
        return z, zb + self.lin("p2", M.relu(self.lin("p1", np.concatenate([zb, ao], -1))))

    def encode(self, state, tok_ids, tok_feats, tok_mask):
        z, _ = self.forward(state, tok_ids, tok_feats, tok_mask)
        self._ctx = (state, tok_ids, tok_feats, tok_mask) if len(state) == 1 else None
        self._cache = None
        return z

    def action(self, act, aid):
        return (np.asarray(act, np.float32), np.asarray(aid, np.int64))

    def predict(self, z, a, h):
        if self._ctx is None:
            raise ValueError("NumpyTx.predict needs the single position of the last encode (use forward for batches)")
        if self._cache is None or self._cache[0] is not a:
            act, aid = a
            _, p = self.forward(*self._ctx, act[None], aid[None])
            self._cache = (a, p[0])
        return self._cache[1][:, self.horizons.index(h)]

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
    return M.NumpyJepa(w), meta
