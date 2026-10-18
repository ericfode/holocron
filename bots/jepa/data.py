"""Builds JEPA training arrays from "swu-traj/1" games (see /mnt/project-files/learn/README.md).

    python3 bots/jepa/data.py --out data/jepa/mix-v1.npz data/traj/rr data/traj/rush-random ...

Every recorded decision becomes one row: the state vector, card tokens, the chosen action, who won, and the
row index of the same seat's next recorded decision (+1) and its 4th next decision (+4), which are the targets
the predictor must reach in latent space. Rows keep game order; `gid` numbers the games in the pack and `seat` is
0 for p1, 1 for p2; `disc` [N, 2, 24] holds the hashed ids of the last 24 cards of my discard pile and the
opponent's (public; -1 pads). With deck lists in the game line (from_replays.js writes them; the protocol's hello gives
both lists to each bot), `pool` [N, 2, 32] holds the distinct cards of my list and the opponent's that the seat has not
seen yet (mine: not in my hand, resources, board or discard, or captured by their units; theirs: not on their board, in
their discard or captured by my units), with `poolk` the copies left; -1 pads, and games without lists get only pads.
Games that ended in ERROR, STEP_CAP or a draw are skipped.

--labels (games written by from_replays.js --labels) adds the opponent's hand at each decision, a target the
acting seat cannot see: `ohand` [N, 12] hashed card ids (features.hash_id("card:<code>"), -1 pads) and `ohn`, the
hand's size.
"""
import argparse
import glob
import gzip
import json
import os
import sys
from functools import partial
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

HORIZONS = (1, 4)
OHAND = 12
DISC = 24
POOL = 32
_db = None
_own_variant = None
_own_cards = None


def _init(card_data, own_variant=None, own_cards=None):
    global _db, _own_variant, _own_cards
    _db = F.load_cards(card_data)
    _own_variant, _own_cards = own_variant, []
    if own_cards:
        with open(own_cards, encoding="utf8") as fh:
            _own_cards = json.load(fh)
        if not isinstance(_own_cards, list):
            raise ValueError("--own-deck-cards must be a JSON array of printed card metadata")


def original_contexts(game):
    """Only the selected seat's original main list enters its dedicated context.

    Trajectory headers contain original lists, not draw-pile snapshots. The
    ordinary decision, labels, opponent list and hidden-state fields are never
    passed to the context encoder. Missing lists remain explicitly unknown.
    """
    if _own_variant is None:
        return None
    from own_deck import own_deck_from_hello, INPUT_DIM
    decks = game.get("decks") or {}
    out = {}
    for seat in ("p1", "p2"):
        deck = decks.get(seat)
        # from_replays.js writes bare main-list arrays. Also accept the native
        # hello-shaped selected list, without its sideboard or arbitrary fields.
        if isinstance(deck, list):
            deck = {"deck": deck}
        elif isinstance(deck, dict):
            deck = {"deck": deck.get("deck")}
        context = own_deck_from_hello({"deck": deck, "cards": _own_cards}, _own_variant)
        out[seat] = np.asarray(context["features"], np.float32).reshape(2, INPUT_DIM)
    return out


def iter_games(path):
    """Yields (header, [decision lines], end) per game; tolerates a truncated last member."""
    game, ds = None, []
    with gzip.open(path, "rt", encoding="utf8") as fh:
        try:
            for line in fh:
                o = json.loads(line)
                if o["t"] == "game":
                    game, ds = o, []
                elif o["t"] == "d":
                    ds.append(o)
                elif o["t"] == "end" and game is not None:
                    yield game, ds, o
                    game, ds = None, []
        except (EOFError, OSError, ValueError):
            return


def discards(d):
    """[2, DISC] hashed ids of the last DISC cards of my discard pile, then the opponent's; -1 pads."""
    out = np.full((2, DISC), -1, np.int16)
    players = (d.get("state") or {}).get("players") or {}
    for k, seat in enumerate((d["you"], "p2" if d["you"] == "p1" else "p1")):
        pile = [c.get("s") for c in (players.get(seat) or {}).get("discard") or [] if isinstance(c, dict) and isinstance(c.get("s"), str)]
        ids = [F.hash_id(f"card:{c}") for c in pile[-DISC:]]
        out[k, :len(ids)] = ids
    return out


def unseen(d, decks):
    """([2, POOL] ids, [2, POOL] copies) of the cards of my list and the opponent's not yet seen by the deciding seat"""
    ids = np.full((2, POOL), -1, np.int16)
    left = np.zeros((2, POOL), np.int8)
    if not decks:
        return ids, left
    players = (d.get("state") or {}).get("players") or {}
    for k, seat in enumerate((d["you"], "p2" if d["you"] == "p1" else "p1")):
        rest = {}
        for c in decks.get(seat) or []:
            rest[c["id"]] = rest.get(c["id"], 0) + int(c.get("count", 1))
        p = players.get(seat) or {}
        units = (p.get("ground") or []) + (p.get("space") or [])
        other = players.get("p2" if seat == "p1" else "p1") or {}
        captured = [c for x in (other.get("ground") or []) + (other.get("space") or []) for c in (x.get("cap") or [])]  # held by their units
        seen = units + [u for x in units for u in (x.get("u") or [])] + (p.get("discard") or []) + captured
        if k == 0:
            seen += (p.get("hand") or []) + (p.get("resources") or [])
        for c in seen:
            code = c.get("s") if isinstance(c, dict) else None
            if rest.get(code, 0) > 0:
                rest[code] -= 1
        cards = [(code, n) for code, n in rest.items() if n > 0][:POOL]
        for j, (code, n) in enumerate(cards):
            ids[k, j] = F.hash_id(f"card:{code}")
            left[k, j] = n
    return ids, left


def encode_file(path, labels=False):
    cols = {k: [] for k in ("state", "tok_ids", "tok_feats", "tok_mask", "act", "aid", "nact", "win", "game", "nxt1", "nxt4", "seq", "bot", "gid", "seat", "disc", "pool", "poolk")}
    if labels:
        cols["ohand"], cols["ohn"] = [], []
    if _own_variant is not None:
        cols["own_deck"] = []
    n = 0
    games = 0
    for game, ds, end in iter_games(path):
        if end.get("winner") not in ("p1", "p2"):
            continue
        games += 1
        seats = {"p1": [], "p2": []}
        own_context = original_contexts(game)
        start = n
        for d in ds:
            if not (0 <= d.get("i", -1) < len(d.get("actions") or [])):
                continue
            e = F.encode(d, _db)
            k = d["i"]
            cols["state"].append(e["state"])
            cols["tok_ids"].append(e["tok_ids"].astype(np.int16))
            cols["tok_feats"].append(e["tok_feats"].astype(np.float16))
            cols["tok_mask"].append(e["tok_mask"].astype(np.uint8))
            cols["act"].append(e["actions"][k])
            cols["aid"].append(e["aids"][k])
            cols["nact"].append(len(d["actions"]))
            cols["win"].append(1 if end["winner"] == d["you"] else 0)
            cols["game"].append(end["seed"])
            cols["seq"].append(d.get("seq", 0))
            seat_bot = game["bots"][0 if d["you"] == "p1" else 1]
            cols["bot"].append(seat_bot)
            cols["gid"].append(games - 1)  # local game number; made global by the caller
            cols["seat"].append(0 if d["you"] == "p1" else 1)
            cols["disc"].append(discards(d))
            pi, pk = unseen(d, game.get("decks"))
            cols["pool"].append(pi)
            cols["poolk"].append(pk)
            if own_context is not None:
                cols["own_deck"].append(own_context[d["you"]])
            if labels:
                if "oh" not in d:
                    raise SystemExit(f"{path}: --labels needs games written by from_replays.js --labels")
                oh = np.full(OHAND, -1, np.int16)
                ids = [F.hash_id(f"card:{c}") for c in d["oh"] if isinstance(c, str)][:OHAND]
                oh[:len(ids)] = ids
                cols["ohand"].append(oh)
                cols["ohn"].append(len(d["oh"]))
            seats[d["you"]].append(n - start)
            n += 1
        nx = {h: [-1] * (n - start) for h in HORIZONS}
        for rows in seats.values():
            for j, r in enumerate(rows):
                for h in HORIZONS:
                    if j + h < len(rows):
                        nx[h][r] = rows[j + h]
        cols["nxt1"] += nx[1]  # local index within the game; made global by the caller
        cols["nxt4"] += nx[4]
        cols.setdefault("gstart", []).extend([start] * (n - start))
    return path, games, cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--card-data", default=os.environ.get("SWU_CARD_DATA", "forceteki/test/json"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--labels", action="store_true", help="add the opponent's hand (games from from_replays.js --labels)")
    ap.add_argument("--own-deck", choices=("neutral", "original", "original-plus-remaining"),
                    help="opt-in independent original-deck rows; remaining is explicitly unknown")
    ap.add_argument("--own-deck-cards", help="pinned hello.cards-compatible JSON array of printed metadata")
    ap.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    if a.own_deck not in (None, "neutral") and not a.own_deck_cards:
        ap.error("--own-deck-cards is required for original-deck preparation")
    if a.own_deck_cards and a.own_deck is None:
        ap.error("--own-deck-cards requires --own-deck")
    files = sorted(f for d in a.dirs for f in (glob.glob(os.path.join(d, "*.jsonl.gz")) if os.path.isdir(d) else [d]))
    out = {}
    offset = 0
    total_games = 0
    with Pool(a.workers, initializer=_init, initargs=(a.card_data, a.own_deck, a.own_deck_cards)) as pool:
        for path, games, cols in pool.imap(partial(encode_file, labels=a.labels), files):
            m = len(cols["state"])
            gstart = np.asarray(cols.pop("gstart", []), np.int64) + offset
            cols["gid"] = np.asarray(cols["gid"], np.int32) + total_games
            for h in HORIZONS:
                loc = np.asarray(cols[f"nxt{h}"], np.int64)
                cols[f"nxt{h}"] = np.where(loc >= 0, loc + gstart, -1)
            for k, v in cols.items():
                out.setdefault(k, []).append(np.asarray(v, dtype="U32") if k == "bot" else np.asarray(v, dtype=np.int16).reshape(-1, OHAND) if k == "ohand" else np.asarray(v))
            offset += m
            total_games += games
            print(f"{path}: {games} games, {m} decisions", file=sys.stderr)
    arrays = {k: np.concatenate(v) for k, v in out.items()}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, **arrays)
    print(f"wrote {a.out}: {total_games} games, {offset} decisions", file=sys.stderr)


if __name__ == "__main__":
    main()
