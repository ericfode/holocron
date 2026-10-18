"""Own-deck input contract v1: two independent 207-float rows.

Only the own hello.deck.deck list and public printed card metadata are read.
Neither observations, opponent.deck, sideboards nor simulation hidden state enter
this function. The remaining row is explicitly unknown until a ledger exists.
"""
import math
import re

import numpy as np

import features as F

VERSION = 1
META_DIM = 50
INPUT_DIM = 207
ROLES = 2
VARIANTS = ("neutral", "original", "original-plus-remaining")
ASPECTS = ("vigilance", "command", "aggression", "cunning", "heroism", "villainy")


def neutral_features(batch=None):
    rows = np.zeros((ROLES, INPUT_DIM), np.float32)
    rows[0, 0] = rows[1, 1] = 1.0
    return rows if batch is None else np.broadcast_to(rows, (batch, ROLES, INPUT_DIM)).copy()


def normalized_code(value):
    if isinstance(value, dict):
        number, set_name = value.get("number"), value.get("set")
        if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= 18_446_744_073_709_551_615 or not isinstance(set_name, str):
            return None
        value = f"{set_name}_{number}"
    if not isinstance(value, str):
        return None
    if not value.isascii():
        return None
    match = re.fullmatch(r"([A-Z0-9]+)_([0-9]+)", value.strip().upper())
    if not match:
        return None
    digits = match[2].lstrip("0") or "0"
    return f"{match[1]}_{digits.zfill(3)}"


def _number(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and abs(v) <= float(np.finfo(np.float32).max) / 128 and math.isfinite(v)


def _metadata(v):
    if not isinstance(v, dict):
        return None
    if any(not isinstance(v.get(k), list) or any(not isinstance(s, str) for s in v[k]) for k in ("types", "keywords", "traits", "aspects")):
        return None
    lists = {k: [s.strip().lower() for s in v[k]] for k in ("types", "keywords", "traits", "aspects")}
    if any(not s for values in lists.values() for s in values):
        return None
    for key in ("types", "keywords", "traits"):
        lists[key] = sorted(set(lists[key]))
    lists["aspects"].sort()
    if not lists["types"] or not _number(v.get("cost")) or v["cost"] < 0:
        return None
    has = lambda text: any(text in s for s in lists["types"])
    if any(has(text) for text in ("leader", "base", "token")):
        return None
    if any(k in v and not _number(v[k]) for k in ("power", "hp")) or (has("unit") and any(k not in v for k in ("power", "hp"))):
        return None
    power, hp = v.get("power", 0), v.get("hp", 0)
    if has("upgrade") and power == 0:
        power, hp = v.get("upgradePower", 0), v.get("upgradeHp", 0)
        if not _number(power) or not _number(hp):
            return None
    return dict(cost=v["cost"], power=power, hp=hp, unit=has("unit"), event=has("event"), upgrade=has("upgrade"),
                space=v.get("arena") == "space", **lists)


def own_deck_from_hello(hello, variant="original"):
    """Return the serializable controller shape, without retaining the hello.

    Invalid/missing metadata retains count-aware identity and marks known=0.
    Explicit empty deck differs from unknown; neutral has no content information.
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown own-deck variant: {variant}")
    rows = neutral_features()
    if variant == "neutral":
        return dict(version=VERSION, variant=variant, features=rows.reshape(-1).tolist())
    rows[0, 2] = 1
    if variant == "original-plus-remaining":
        rows[1, 2] = 1  # enabled but known=0: no guessed depletion state
    aliases, metadata = {}, {}
    for card in hello.get("cards", []) if isinstance(hello.get("cards"), list) else []:
        if not isinstance(card, dict):
            continue
        codes = {c for raw in card.get("setCodes", []) if isinstance(raw, dict) and (c := normalized_code(raw))} if isinstance(card.get("setCodes"), list) else set()
        canonical = (normalized_code(card.get("setId")) if isinstance(card.get("setId"), dict) else None) or min(codes, default=None)
        if canonical:
            codes.add(canonical)
            for code in codes:
                aliases.setdefault(code, set()).add(canonical)
            parsed = _metadata(card)
            if canonical not in metadata:
                metadata[canonical] = parsed
            elif metadata[canonical] != parsed:
                metadata[canonical] = None
    source = hello.get("deck")
    entries = source.get("deck") if isinstance(source, dict) else None
    malformed = 0 if isinstance(entries, list) else 1
    counts, resolved_metadata = {}, {}
    for entry in entries if isinstance(entries, list) else []:
        code = normalized_code(entry.get("id")) if isinstance(entry, dict) and isinstance(entry.get("id"), str) else None
        count = entry.get("count") if isinstance(entry, dict) else None
        if not code or not isinstance(count, int) or isinstance(count, bool) or not 0 < count <= 9_007_199_254_740_991:
            malformed += 1
            continue
        names = aliases.get(code, set())
        canonical = next(iter(names)) if len(names) == 1 else code
        parsed = metadata.get(canonical) if len(names) == 1 else None
        if canonical not in resolved_metadata:
            resolved_metadata[canonical] = parsed
        elif resolved_metadata[canonical] != parsed:
            resolved_metadata[canonical] = None
        counts[canonical] = counts.get(canonical, 0) + count
    for canonical, count in list(counts.items()):
        if count > 9_007_199_254_740_991:
            del counts[canonical]
            malformed += 1
    # Accumulate in float64 in the same sorted order as Rust, cast only once.
    row, total, unknown = rows[0].astype(np.float64), sum(counts.values()), 0
    row[4], row[6], row[49] = total / 60, len(counts) / 60, malformed / 60
    for code, count in sorted(counts.items()):
        ident, weight = F.hash_id("card:" + code), count / 60
        row[50 + ident % 64] += weight
        row[114 + ident // 64] += weight
        row[146 + (ident * 7 + 3) % 61] += weight
        m = resolved_metadata.get(code)
        if m is None:
            unknown += count
            continue
        frac = count / total
        row[8:11] += np.asarray([m["cost"], m["power"], m["hp"]], np.float64) * frac / 10
        row[11:16] += np.asarray([m["unit"], m["event"], m["upgrade"], m["unit"] and not m["space"], m["unit"] and m["space"]], np.float64) * frac
        row[16 + min(int(m["cost"]), 8)] += frac
        for i, keyword in enumerate(F.KEYWORDS):
            row[25+i] += frac * (keyword in m["keywords"])
        for aspect in m["aspects"]:
            if aspect in ASPECTS:
                row[35 + ASPECTS.index(aspect)] += frac
        for trait in set(m["traits"]):
            row[41 + F.hash_id(trait) % 8] += frac
    row[3] = float(malformed == 0 and unknown == 0)
    row[5] = unknown / 60
    row[7] = (total - unknown) / total if total else float(malformed == 0)
    rows[0] = row
    return dict(version=VERSION, variant=variant, features=rows.reshape(-1).tolist())


def as_array(context, batch=1):
    """Validate the serialized feature boundary; no implicit perfect-state fallback."""
    if context is None:
        return neutral_features(batch)
    if isinstance(context, dict):
        if type(context.get("version")) is not int or context.get("version") != VERSION or context.get("variant") not in VARIANTS:
            raise ValueError("unsupported own-deck context contract")
        context = context["features"]
    values = np.asarray(context, np.float32)
    if values.size == ROLES * INPUT_DIM:
        values = np.broadcast_to(values.reshape(1, ROLES, INPUT_DIM), (batch, ROLES, INPUT_DIM)).copy()
    if values.shape != (batch, ROLES, INPUT_DIM) or not np.isfinite(values).all():
        raise ValueError(f"own-deck features must be finite [{batch},2,{INPUT_DIM}]")
    return values


encode_hello = own_deck_from_hello
