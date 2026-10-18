"""Opt-in deck-aware JEPA: NumPy inference and import-safe PyTorch training.

Legacy weights/shapes are reused unchanged. The three supplemental tensors add
exactly two context slots after the 24 live-card slots. Role/status-bearing
neutral and unknown rows remain visible, including during the mean readout.
"""
import numpy as np

import model as M
import own_deck as O
import tx_model as X

FORMAT = "swu-jepa-tx-own-deck/1"


def supplemental_shapes(dm=64):
    return {"din.w": (O.META_DIM + M.EMB, dm), "din.b": (dm,), "drole": (O.ROLES, dm)}


def supplement(seed=17, dm=64):
    rng = np.random.default_rng(seed)
    # Fixed initialization is engineering scaffolding, never a trained candidate.
    return {"din.w": rng.normal(0, 0.02, (O.META_DIM + M.EMB, dm)).astype(np.float32),
            "din.b": np.zeros(dm, np.float32),
            "drole": rng.normal(0, 0.02, (O.ROLES, dm)).astype(np.float32)}


def load_extended(checkpoint, supplemental):
    weights, meta = M.load_safetensors(checkpoint)
    extras, emeta = M.load_safetensors(supplemental)
    if emeta.get("format") != FORMAT or set(extras) != set(supplemental_shapes(int(meta["dm"]))):
        raise ValueError("invalid supplemental own-deck checkpoint")
    for key, shape in supplemental_shapes(int(meta["dm"])).items():
        if extras[key].shape != shape or not np.isfinite(extras[key]).all():
            raise ValueError(f"invalid own-deck supplemental tensor: {key}")
    return {**weights, **extras}, {**meta, "format": FORMAT, "own_deck_version": "1"}


def pooled_identity(w, deck):
    """Exactly sum(count/60 * shared card embedding), without a deck-size cap."""
    return deck[..., 50:114] @ w["emb_a"] + deck[..., 114:146] @ w["emb_b"] + deck[..., 146:207] @ w["emb_c"]


class NumpyOwnDeckTx(X.NumpyTx):
    supports_own_deck = True

    def __init__(self, w, meta):
        for key, shape in supplemental_shapes(int(meta["dm"])).items():
            if key not in w or w[key].shape != shape:
                raise ValueError(f"missing/invalid own-deck tensor: {key}")
        super().__init__(w, meta)

    def _initial_context(self, state, ids, feats, mask, own_deck):
        x, kval = super()._initial_context(state, ids, feats, mask, None)
        deck = O.as_array(own_deck, len(state))
        tokens = self.lin("din", np.concatenate([deck[..., :O.META_DIM], pooled_identity(self.w, deck)], -1)) + self.w["drole"][None]
        return np.concatenate([x, tokens], 1), np.concatenate([kval, np.ones((len(state), O.ROLES), np.float32)], 1)


def run_torch(w, meta, state, ids, feats, mask, act=None, aid=None, hsel=None, *, own_deck=None):
    """Differentiable training forward; no CLI, dataset, device or optimizer side effects.

    `w` is a dict of torch tensors. Full encoder, action prediction and value-head
    objectives can use this function. Freeze base tensors for a supplemental-only
    matched diagnostic; do not interpret a synthetic update as strength training.
    """
    import torch
    B, t = ids.shape
    T, dm, H, L = (int(meta[k]) for k in ("tmax", "dm", "heads", "layers"))
    ids, feats, mask = ids[:, :T], feats[:, :T], mask[:, :T]
    t, hd = ids.shape[1], dm // H
    hors = X.horizons(meta)
    selected = list(range(len(hors))) if hsel is None else list(hsel)
    hz = len(selected)
    lin = lambda name, x: x @ w[name + ".w"] + w[name + ".b"]
    ln = lambda name, x: torch.nn.functional.layer_norm(x, (dm,), w[name + ".g"], w[name + ".b"], 1e-5)
    embed = lambda ids: w["emb_a"][ids % 64] + w["emb_b"][ids // 64] + w["emb_c"][(ids * 7 + 3) % 61]
    if own_deck is None:
        deck = torch.as_tensor(O.neutral_features(B), device=state.device, dtype=state.dtype)
    elif isinstance(own_deck, torch.Tensor):
        deck = own_deck
        if tuple(deck.shape) != (B, O.ROLES, O.INPUT_DIM):
            raise ValueError("own_deck must have shape [B,2,207]")
        if not torch.isfinite(deck).all():
            raise ValueError("own_deck must be finite")
    else:
        deck = torch.as_tensor(O.as_array(own_deck, B), device=state.device, dtype=state.dtype)
    pooled = pooled_identity(w, deck)
    dt = lin("din", torch.cat([deck[..., :O.META_DIM], pooled], -1)) + w["drole"][None]
    x = torch.cat([lin("sin", state).unsqueeze(1), lin("tin", torch.cat([feats, embed(ids)], -1)), dt], 1)
    kval = torch.cat([torch.ones(B, 1, device=state.device), mask, torch.ones(B, O.ROLES, device=state.device)], 1)
    c, k = x.shape[1], 0
    if act is not None:
        k = act.shape[1]
        av = lin("ain", torch.cat([act, embed(aid)], -1))
        av = (av.unsqueeze(2) + w["hor"][selected].reshape(1, 1, hz, dm)).reshape(B, hz*k, dm)
        x = torch.cat([x, av], 1)
        kval = torch.cat([kval, torch.ones(B, hz*k, device=state.device)], 1)
    size = x.shape[1]
    bias = ((kval-1) * 1e9).reshape(B, 1, 1, size)
    if k:
        bias = bias + torch.as_tensor(X.struct_mask(c, k, hz), device=state.device).reshape(1, 1, size, size)
    for i in range(L):
        y = ln(f"b{i}.ln1", x)
        q, kk, v = (lin(f"b{i}.{p}", y).reshape(B, size, H, hd).transpose(1, 2) for p in "qkv")
        att = torch.softmax(q @ kk.transpose(-2, -1) / hd**0.5 + bias, -1)
        x = x + lin(f"b{i}.o", (att @ v).transpose(1, 2).reshape(B, size, dm))
        x = x + lin(f"b{i}.f2", torch.relu(lin(f"b{i}.f1", ln(f"b{i}.ln2", x))))
    x = ln("lnf", x)
    m = kval[:, :c, None]
    mean = (x[:, :c] * m).sum(1) / m.sum(1)
    z = lin("zo2", torch.relu(lin("zo1", torch.cat([x[:, 0], mean, state], -1))))
    if not k:
        return z, None
    ao = x[:, c:].reshape(B, k, hz, dm)
    zb = z.reshape(B, 1, 1, M.D).expand(B, k, hz, M.D)
    return z, zb + lin("p2", torch.relu(lin("p1", torch.cat([zb, ao], -1))))


def value_torch(w, z):
    import torch
    return (torch.relu(z @ w["v1.w"] + w["v1.b"]) @ w["v2.w"] + w["v2.b"])[..., 0]
