"""Deck par from many c-clock mirrors on fresh deals: par of a game = c-clock's win rate with the same deck pairing and
seats, averaged over the mirrors (rd/par/mirror-par-*). Per deck: the bot's score minus par (how the bot handles the
deck compared with c-clock), with a standard error from the bot's games (par's own error is about sqrt(10) smaller).
python par2.py <rd dir> <bot>..."""
import glob
import json
import math
import os
import sys
from collections import defaultdict

rd, bots = sys.argv[1], sys.argv[2:]
dec = lambda g: g.get("outcome") == "won" and g.get("winnerSeat") in ("p1", "p2")
par = defaultdict(lambda: [0, 0])  # (p1 deck, p2 deck) -> [p1 wins, decided]
mirrors = sorted(glob.glob(os.path.join(rd, "par", "mirror-par-*", "index.json")))
for f in mirrors:
    for g in json.load(open(f))["games"]:
        if dec(g):
            k = (g["decks"]["p1"], g["decks"]["p2"])
            par[k][0] += g["winnerSeat"] == "p1"
            par[k][1] += 1
print(f"par from {len(mirrors)} mirrors, {sum(v[1] for v in par.values())} decided games, {len(par)} deck pairings")

summary = {}
for bot in bots:
    rows = []
    for g in json.load(open(os.path.join(rd, f"test-{bot}-1", "index.json")))["games"]:
        if not dec(g):
            continue
        k = (g["decks"]["p1"], g["decks"]["p2"])
        if not par[k][1]:
            continue
        seat = "p1" if g["p1"] == bot else "p2"
        p1rate = par[k][0] / par[k][1]
        rows.append({"deck": g["decks"][seat], "opp": g["decks"]["p2" if seat == "p1" else "p1"], "seat": seat,
                     "x": int(g["winnerSeat"] == seat) - (p1rate if seat == "p1" else 1 - p1rate)})
    mu = sum(r["x"] for r in rows) / len(rows)
    print(f"\n{bot}: {len(rows)} games, score minus par {mu * 100:+.1f} pts")
    for key, title in ((lambda r: r["deck"], "deck we hold"), (lambda r: r["opp"], "opponent's deck")):
        grp = defaultdict(list)
        for r in rows:
            grp[key(r)].append(r["x"])
        chi, out = 0.0, []
        for name, v in grp.items():
            m = len(v)
            mean = sum(v) / m
            var = sum((x - mean) ** 2 for x in v) / max(m - 1, 1)
            se = math.sqrt(var / m)
            chi += (mean - mu) ** 2 / max(var / m, 1e-9)
            out.append((mean - mu, se, m, name))
        print(f"  by {title}: chi-square {chi:.1f} on {len(grp) - 1} df (noise alone: about {len(grp) - 1} +- {math.sqrt(2 * (len(grp) - 1)):.0f})")
        summary.setdefault(title, {})[bot] = {name: d for d, _, _, name in out}
        for d, se, m, name in sorted(out):
            print(f"    {name:42s} n={m:3d}  {d * 100:+6.1f} +- {se * 100:4.1f}")

for title, per in summary.items():
    if len(per) < 2:
        continue
    names = sorted(set.intersection(*[set(v) for v in per.values()]))
    bl = list(per)
    print(f"\ncorrelation between bots of the per-deck numbers ({title}; par no longer shared noise):")
    for a in bl:
        row = []
        for b in bl:
            x = [per[a][n] for n in names]
            y = [per[b][n] for n in names]
            mx, my = sum(x) / len(x), sum(y) / len(y)
            sxy = sum((p - mx) * (q - my) for p, q in zip(x, y))
            sx = math.sqrt(sum((p - mx) ** 2 for p in x))
            sy = math.sqrt(sum((q - my) ** 2 for q in y))
            row.append(f"{sxy / (sx * sy):+.2f}")
        print(f"  {a:14s} " + " ".join(row))
