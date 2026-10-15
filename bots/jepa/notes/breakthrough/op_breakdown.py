"""Where the imagined ranking loses value, on judged branch points (replay_branches.js data, judge_prep.py --all):
per point, the judged win chance lost by the model's imagined best move (settled horizon, as the bot picks at action
windows) and by the move the recorded bot really played, broken down by round, number of moves, the kind of the
judge's best move and the size of the gap between the best and worst move.
python op_breakdown.py <model> <packed npz> <judge npz> <branch dir>... [--json out.json]"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, HERE)
import branch_prep as BP  # noqa: E402
import model as M  # noqa: E402
import tx_model as X  # noqa: E402
import yardstick as Y  # noqa: E402

args = [x for x in sys.argv[1:] if not x.startswith("--")]
jout = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
if jout:
    args.remove(jout)
model, packed, judge, dirs = args[0], args[1], args[2], args[3:]
net, _ = X.load(model)
B = dict(np.load(packed))
J = np.load(judge)
assert np.array_equal(J["game"], B["game"])
hs = [net.horizons[i] for i in net.groups[0]].index("s")


def kind(a):
    if a.get("kind") == "button":
        lab = str(a.get("label", "")).lower()
        return "pass" if lab == "pass" else "claim initiative" if "initiative" in lab else "other button"
    if a.get("kind") == "card":
        z = (a.get("card") or {}).get("zone", "")
        return {"hand": "play from hand", "groundArena": "unit in play (attack/ability)", "spaceArena": "unit in play (attack/ability)",
                "base": "leader/base", "resource": "from resources"}.get(z, "leader/base" if "leader" in z.lower() else f"card {z}")
    return a.get("kind", "?")


meta = []
files = sorted(f for d in dirs for f in glob.glob(os.path.join(d, "*.jsonl.gz")))
for f in files:
    for line in BP._lines(f):
        o = json.loads(line)
        if o["t"] != "b" or len(o["br"]) < 2:
            continue
        br = o["br"][:BP.K]
        meta.append({"round": o["state"].get("round"), "kinds": [kind(o["actions"][b["i"]]) for b in br],
                     "main": next((k for k, b in enumerate(br) if b["i"] == o["main"]), None), "nlegal": len(o["actions"])})
assert len(meta) == len(B["game"]), (len(meta), len(B["game"]))

rows = []
for p in range(len(meta)):
    n = int(B["nmove"][p])
    ok = [k for k in range(n) if (B["mt"][p, k] > 0 and np.isfinite(J["evt"][p, k])) or B["over"][p, k] >= 0]
    if len(ok) < 2:
        continue
    re = np.array([M.sigmoid(J["evt"][p, k]) if B["mt"][p, k] > 0 and np.isfinite(J["evt"][p, k]) else float(B["over"][p, k]) for k in ok])
    im = M.sigmoid(net.value(Y.imagine(net, B, p)))[ok, hs]
    pick = np.flatnonzero(im >= im.max() - 1e-9)
    best = int(np.argmax(re))
    m = meta[p]
    mk = ok.index(m["main"]) if m["main"] in ok else None
    rows.append({"round": m["round"], "n": len(ok), "nlegal": m["nlegal"], "kind": m["kinds"][ok[best]], "gap": float(re.max() - re.min()),
                 "regret": float(re.max() - re[pick].mean()), "top1": float(np.mean([re[i] >= re.max() - 1e-6 for i in pick])),
                 "main_regret": float(re.max() - re[mk]) if mk is not None else None, "rand_regret": float(re.max() - re.mean()),
                 "chance": float(np.mean(re >= re.max() - 1e-6))})
R = rows
print(f"{model} on {packed}: {len(R)} points; model regret {np.mean([r['regret'] for r in R]) * 100:.2f} pts, top-1 {np.mean([r['top1'] for r in R]):.3f} "
      f"(chance {np.mean([r['chance'] for r in R]):.3f}); recorded bot's own move regret "
      f"{np.mean([r['main_regret'] for r in R if r['main_regret'] is not None]) * 100:.2f} pts; random move {np.mean([r['rand_regret'] for r in R]) * 100:.2f} pts")
print("share of all lost value = how much of the model's total regret falls in this group")
tot = sum(r["regret"] for r in R)
out = {"points": len(R), "regret": tot / len(R)}


def table(key, title, order=None):
    g = defaultdict(list)
    for r in R:
        g[key(r)].append(r)
    keys = order or sorted(g, key=lambda k: -sum(x["regret"] for x in g[k]))
    print(f"\n{title}")
    print(f"  {'':34s} {'points':>7s} {'regret':>7s} {'share':>6s} {'top-1':>6s} {'chance':>6s} {'bot move':>8s} {'random':>7s}")
    res = {}
    for k in keys:
        v = g.get(k)
        if not v:
            continue
        rg = np.mean([x["regret"] for x in v])
        mr = [x["main_regret"] for x in v if x["main_regret"] is not None]
        res[str(k)] = {"points": len(v), "regret": rg, "share": sum(x["regret"] for x in v) / tot, "top1": np.mean([x["top1"] for x in v])}
        print(f"  {str(k):34s} {len(v):7d} {rg * 100:6.2f}  {sum(x['regret'] for x in v) / tot * 100:5.1f}% {np.mean([x['top1'] for x in v]):6.3f} "
              f"{np.mean([x['chance'] for x in v]):6.3f} {np.mean(mr) * 100 if mr else float('nan'):7.2f}  {np.mean([x['rand_regret'] for x in v]) * 100:6.2f}")
    out[title] = res


rb = lambda r: "1-2" if r["round"] <= 2 else "3-4" if r["round"] <= 4 else "5-6" if r["round"] <= 6 else "7+"
table(rb, "by round", ["1-2", "3-4", "5-6", "7+"])
nb = lambda r: "2-3 moves" if r["n"] <= 3 else "4-6 moves" if r["n"] <= 6 else "7-9 moves" if r["n"] <= 9 else "10-12 moves"
table(nb, "by number of moves branched", ["2-3 moves", "4-6 moves", "7-9 moves", "10-12 moves"])
table(lambda r: r["kind"], "by the kind of the judge's best move")
gb = lambda r: "gap < 2 pts" if r["gap"] < 0.02 else "gap 2-5" if r["gap"] < 0.05 else "gap 5-10" if r["gap"] < 0.10 else "gap 10-20" if r["gap"] < 0.20 else "gap >= 20"
table(gb, "by the gap between the best and the worst move", ["gap < 2 pts", "gap 2-5", "gap 5-10", "gap 10-20", "gap >= 20"])
if jout:
    json.dump(out, open(jout, "w"), indent=1, default=float)
