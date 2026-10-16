"""Lines for the move choice at an action window, offline (the bot without the simulator knows only the root move there).

    python3 bots/jepa/line_move.py --lines data/lines/pl1.npz --line-model bots/jepa/notes/lines/l1-resid.npz \
        --root-model bots/jepa/notes/lines/root1.npz --model bots/jepa/models/tx-t10.safetensors data/plog/pl1

On the held-out games of line_train.py's split, each window's root moves (those the planner judged) are ranked by:
  baseline   tx-t10's own settle prediction zb (the bot without the simulator today)
  root       the root model (line_root.py)
  line1      the line model on the root move alone
  synth      the line model's best line over synthesized follow-ups: the root move alone, or the root move then one card
             read off the root board (each unit in play, both bases, both leaders), encoded as a card option
  synth-u    the same with units in play only (no bases or leaders)
against the real root values (each root move worth its best judged line, tx-t10's value head on the real settled
boards, as the planner judges). Reports top-1 and the real value lost, with 95% intervals by game.
"""
import argparse
import glob
import json
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402
import line_models as LM  # noqa: E402
import model as M  # noqa: E402
import tx_model as X  # noqa: E402

A = None
SYNTH_PROMPT = {"type": "select", "actionWindow": False, "selectCardMode": "single", "selected": []}


def records(path):
    raw = open(path, "rb").read()
    text = b""
    while raw:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            text += d.decompress(raw)
        except zlib.error:
            break
        raw = d.unused_data
    for line in text.decode("utf8", "ignore").split("\n"):
        if line.strip():
            try:
                yield json.loads(line)
            except ValueError:
                pass


def synth_options(state, units_only):
    """card options read off the board: each unit in play (both sides), and unless units_only both bases and leaders"""
    out = []
    for seat, p in (state.get("players") or {}).items():
        for zone, key in (("groundArena", "ground"), ("spaceArena", "space")):
            for u in p.get(key) or []:
                if isinstance(u, dict) and isinstance(u.get("id"), str):
                    out.append({"kind": "card", "label": str(u.get("n", "")), "cardUuid": u["id"],
                                "card": {"id": u["id"], "s": u.get("s"), "zone": zone, "ctl": seat}})
        if not units_only:
            for zone, key in (("base", "base"), ("leader", "leader")):
                c = p.get(key)
                if isinstance(c, dict) and isinstance(c.get("id"), str):
                    out.append({"kind": "card", "label": str(c.get("n", "")), "cardUuid": c["id"],
                                "card": {"id": c["id"], "s": c.get("s"), "zone": zone, "ctl": seat}})
    return out


def one_file(args):
    path, fi, held = args
    net, meta = X.load(A.model)
    T = int(meta.get("tmax", 24))
    hs = net.horizons.index("s")
    db = F.load_cards()
    lm, rm = LM.LineNP(A.line_model), LM.RootNP(A.root_model)
    val = lambda zz: 1.0 / (1.0 + np.exp(-net.value(zz)))
    rows = []
    games = 0
    cur, you = [], None
    for r in records(path):
        t = r.get("t")
        if t == "hello":
            cur, you = [], r.get("you")
        elif t == "pw":
            cur.append(r)
        elif t == "over" and you is not None:
            if r.get("winner") not in ("p1", "p2"):
                cur = []
                continue
            g = fi * 100000 + games
            games += 1
            if g not in held:
                cur = []
                continue
            for w in cur:
                msg = w["msg"]
                lines = [e for e in w["leaves"] if e.get("pos") and e.get("line")]
                if len(lines) < 2:
                    continue
                roots = sorted({int(e["move"]) for e in lines})
                if len(roots) < 2:
                    continue
                e0 = F.encode(msg, db)
                act = e0["actions"][roots].astype(np.float32)
                aid = e0["aids"][roots].astype(np.int64)
                z, pr = net.forward(e0["state"][None], e0["tok_ids"][None, :T].astype(np.int64), e0["tok_feats"][None, :T].astype(np.float32),
                                    e0["tok_mask"][None, :T].astype(np.float32), act[None], aid[None], hsel=[hs])
                z, zb = z[0], pr[0, :, 0]
                # the real root values: each root move's best judged line
                pos = [{"you": msg["you"], "prompt": e["pos"]["prompt"], "state": e["pos"]["state"],
                        "actions": e["pos"]["actions"] if e["pos"].get("actions") is not None else msg["actions"]} for e in lines]
                es = [F.encode(m, db) for m in pos]
                zr = net.encode(np.stack([x["state"] for x in es]), np.stack([x["tok_ids"][:T] for x in es]).astype(np.int64),
                                np.stack([x["tok_feats"][:T] for x in es]).astype(np.float32), np.stack([x["tok_mask"][:T] for x in es]).astype(np.float32))
                vr = val(zr)
                real = np.array([max(vr[k] for k, e in enumerate(lines) if int(e["move"]) == rt) for rt in roots])
                base = val(zb)
                root = val(rm.predict(z, zb, act, aid))
                line1 = np.array([val(lm.predict(z, zb[j], act[j][None, None], aid[j][None, None]))[0] for j in range(len(roots))])
                res = {"baseline": base, "root": root, "line1": line1}
                smsg = {"you": msg["you"], "prompt": SYNTH_PROMPT, "state": msg["state"]}
                for name, uo in (("synth", False), ("synth-u", True)):
                    opts = synth_options(msg.get("state") or {}, uo)
                    sc = line1.copy()
                    if opts:
                        srows, sids = F.encode_actions({**smsg, "actions": opts}, db)
                        srows, sids = np.asarray(srows, np.float32), np.asarray(sids, np.int64)
                        n = len(sids)
                        for j in range(len(roots)):
                            lr = np.concatenate([np.repeat(act[j][None, None], n, 0), srows[:, None]], 1)
                            la = np.concatenate([np.repeat(aid[j][None, None], n, 0), sids[:, None]], 1)
                            sc[j] = max(sc[j], float(val(lm.predict(z, zb[j], lr, la)).max()))
                    res[name] = sc
                rows.append({"game": g, "real": real.tolist(), **{k: np.asarray(v, float).tolist() for k, v in res.items()}})
            cur = []
    return rows


def metrics(score, real):
    best = real >= real.max() - 1e-9
    top = score >= score.max() - 1e-9
    return float(best[top].mean()), float(real.max() - real[top].mean())


def main():
    global A
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--lines", required=True, help="line_data.py output (for the held-out split)")
    ap.add_argument("--line-model", required=True)
    ap.add_argument("--root-model", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--hold", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--procs", type=int, default=14)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--out", default=None)
    A = ap.parse_args()
    wg = np.load(A.lines)["w_game"]
    games = np.unique(wg)
    held = set(np.random.default_rng(A.seed).permutation(games)[:max(1, int(len(games) * A.hold))].tolist())
    files = sorted(f for d in A.dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
    with Pool(min(A.procs, len(files)), initializer=_init, initargs=(A,)) as pool:
        parts = pool.map(one_file, [(f, i, held) for i, f in enumerate(files)])
    rows = [r for p in parts for r in p]
    names = ["baseline", "root", "line1", "synth", "synth-u"]
    m = {n: np.array([metrics(np.array(r[n]), np.array(r["real"])) for r in rows]) for n in names}
    g = np.array([r["game"] for r in rows])
    ug = np.unique(g)
    gi = {x: np.nonzero(g == x)[0] for x in ug}
    rng = np.random.default_rng(A.seed + 5)
    boots = [np.concatenate([gi[x] for x in rng.choice(ug, len(ug))]) for _ in range(A.boot)]
    ci = lambda v: (float(v.mean()), float(np.percentile([v[b].mean() for b in boots], 2.5)), float(np.percentile([v[b].mean() for b in boots], 97.5)))
    fmt = lambda c: f"{c[0]:.3f} [{c[1]:.3f}, {c[2]:.3f}]"
    out = {"windows": len(rows), "games": len(ug)}
    print(f"held-out {len(rows)} windows of {len(ug)} games (root moves the planner judged; each worth its best real line)")
    for n in names:
        out[n] = {"top1": ci(m[n][:, 0]), "lost_pts": ci(m[n][:, 1] * 100)}
        d = {"top1": ci(m[n][:, 0] - m["baseline"][:, 0]), "lost_pts": ci((m[n][:, 1] - m["baseline"][:, 1]) * 100)}
        out[n + "_vs_baseline"] = d
        print(f"  {n:9s} top-1 {fmt(out[n]['top1'])}  lost {fmt(out[n]['lost_pts'])} pts   vs baseline: top-1 {fmt(d['top1'])}, lost {fmt(d['lost_pts'])} pts")
    if A.out:
        json.dump(out, open(A.out, "w"), indent=1)


def _init(a):
    global A
    A = a


if __name__ == "__main__":
    main()
