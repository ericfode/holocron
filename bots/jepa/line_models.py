"""Numpy inference for the line test's models (the bot runs without torch).

RootNP: line_root.py's model. ẑ = zb + MLP([z, zb, token]): where a root move settles under the planner's best
        follow-ups, from the move alone (what the bot knows at an action window).
LineNP: line_train.py's "resid" model. ẑ = zb + MLP([z, zb, line]), the line encoded by a small post-norm transformer
        over its action tokens (the root move, then each follow-up choice where it was made).
Both read tx-t10's latents (z, the window; zb, its settle prediction for the root move) and are scored with tx-t10's
value head on ẑ.
"""
import numpy as np


def _lin(x, w, name):
    return x @ w[name + ".weight"].T + w[name + ".bias"]


def _ln(x, w, name, eps=1e-5):
    mu = x.mean(-1, keepdims=True)
    var = ((x - mu) ** 2).mean(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * w[name + ".weight"] + w[name + ".bias"]


class RootNP:
    def __init__(self, path):
        self.w = {k: v.astype(np.float32) for k, v in np.load(path).items()}

    def predict(self, z, zb, rows, aids):
        """z [D], zb [n, D], rows [n, 62], aids [n] -> ẑ [n, D]"""
        w = self.w
        t = np.maximum(_lin(np.concatenate([rows, w["emb.weight"][aids]], -1), w, "inp"), 0.0)
        h = np.maximum(_lin(np.concatenate([np.broadcast_to(z, zb.shape), zb, t], -1), w, "l1"), 0.0)
        return zb + _lin(h, w, "l2")


class LineNP:
    def __init__(self, path, heads=4):
        self.w = {k: v.astype(np.float32) for k, v in np.load(path).items()}
        self.heads = heads
        self.layers = len({k.split(".")[2] for k in self.w if k.startswith("tx.layers.")})

    def predict(self, z, zb, rows, aids):
        """z [D], zb [D], rows [n, L, 62], aids [n, L] (n lines of the same length L) -> ẑ [n, D]"""
        w = self.w
        n, L = aids.shape
        x = _lin(np.concatenate([rows, w["emb.weight"][aids]], -1), w, "inp") + w["pos"][:L]
        dm = x.shape[-1]
        hd = dm // self.heads
        for i in range(self.layers):
            p = f"tx.layers.{i}."
            qkv = x @ w[p + "self_attn.in_proj_weight"].T + w[p + "self_attn.in_proj_bias"]
            q, k, v = (qkv[..., j * dm:(j + 1) * dm].reshape(n, L, self.heads, hd).transpose(0, 2, 1, 3) for j in range(3))
            att = q @ k.transpose(0, 1, 3, 2) / np.sqrt(hd)
            att = np.exp(att - att.max(-1, keepdims=True))
            att /= att.sum(-1, keepdims=True)
            sa = (att @ v).transpose(0, 2, 1, 3).reshape(n, L, dm)
            x = _ln(x + _lin(sa, w, p + "self_attn.out_proj"), w, p + "norm1")
            x = _ln(x + _lin(np.maximum(_lin(x, w, p + "linear1"), 0.0), w, p + "linear2"), w, p + "norm2")
        line = x.mean(1)
        zbb = np.broadcast_to(zb, (n, zb.shape[-1]))
        h = np.maximum(_lin(np.concatenate([np.broadcast_to(z, zbb.shape), zbb, line], -1), w, "pred.0"), 0.0)
        return zbb + _lin(h, w, "pred.2")
