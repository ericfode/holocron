#!/usr/bin/env python3
"""The Python side of parity.js: for each `decide` message on stdin (one JSON per line), what jepa_bot.py reads and
thinks: the state vector, the move rows and ids, the card tokens, each move's imagined score and the resource choice.

    python3 bots/jepa/js/parity.py --model M [--window-model M] [--window-horizon s] [--follow-horizon s] [--mix 0] [--resource c-clock]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import features as F  # noqa: E402
import jepa_bot as J  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--window-model", default=None)
    ap.add_argument("--window-horizon", default="1")
    ap.add_argument("--follow-horizon", default="1")
    ap.add_argument("--mix", type=float, default=0.5)
    ap.add_argument("--resource", default=None)
    a = ap.parse_args()
    db = F.load_cards()
    player = J.JepaPlayer(a.model, db, a.mix, window_model=a.window_model, window_horizon=a.window_horizon, follow_horizon=a.follow_horizon,
                          resource=a.resource)
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        e = F.encode(msg, db)
        n = int(e["tok_mask"].sum())
        t = player.think(msg)
        res = player.resource.choose(msg) if player.resource is not None else None
        out = {"state": e["state"].tolist(), "rows": e["actions"].reshape(-1).tolist(), "aids": e["aids"].tolist(),
               "tok_ids": e["tok_ids"][:n].tolist(), "tok_feats": e["tok_feats"][:n].reshape(-1).tolist(),
               "score": [float(x) for x in t["score"]], "resource": res}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
