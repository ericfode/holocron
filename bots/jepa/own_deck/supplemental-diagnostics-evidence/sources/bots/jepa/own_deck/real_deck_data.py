"""Prepare auxiliary declaration labels from pinned local lists and printed metadata.

No games, private observations, human win rates, rule execution or training enter
this dataset. Unknown metadata excludes a row explicitly rather than inventing a
cost/type label. The encoded model features contain only the original own list.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

JEPA = Path(__file__).resolve().parents[1]
REPO = JEPA.parents[1]
sys.path.insert(0, str(JEPA))
import own_deck as O

SCHEMA = "jepa-real-own-deck-data/1"
KESSEL_COMMIT = "c7ee39554901278cee70f61fd8b26fb1920696b3"
UPSTREAM_DECK_COMMIT = "a2df9722314b1233d16747f7e56186071106799c"
TARGET_NAMES = ["total_count_per_60", "mean_cost_per_10", "low_cost_le_2_fraction",
                *[f"cost_{n}_fraction" for n in range(8)], "cost_8_plus_fraction", "initial_draw_unit_probability"]
PRINTED_FIELDS = ("setId", "setCodes", "cost", "power", "hp", "upgradePower", "upgradeHp",
                  "types", "aspects", "traits", "keywords", "arena")
SPLIT_SEED = "own-deck-real-declarations-v1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(counts):
    return hashlib.sha256(json.dumps(sorted((k, int(v)) for k, v in counts.items() if v), separators=(",", ":")).encode()).hexdigest()


def printed_catalog(catalog):
    """Extract printed fields only; null nonunit stats mean not applicable.

    Kessel preserves JSON null for event/upgrade statistics. The existing feature
    contract uses absent nonunit statistics as zero, so remove those null fields.
    Unit null statistics and null costs remain unknown. Ability IR is discarded.
    """
    if catalog.get("schema") != "swu-card-ir-cards/v1" or not isinstance(catalog.get("cards"), list):
        raise ValueError("unsupported Kessel printed catalog")
    result, normalized_nulls = [], 0
    for row in catalog["cards"]:
        card = row.get("card")
        if not isinstance(card, dict):
            continue
        card = {key: card[key] for key in PRINTED_FIELDS if key in card}
        if "unit" not in card.get("types", []):
            for key in ("power", "hp", "upgradePower", "upgradeHp"):
                if key in card and card[key] is None:
                    del card[key]
                    normalized_nulls += 1
        result.append(card)
    return result, normalized_nulls


def catalog_index(cards):
    aliases, metadata = defaultdict(set), {}
    for card in cards:
        codes = {code for value in card.get("setCodes", []) if isinstance(value, dict) and (code := O.normalized_code(value))}
        canonical = O.normalized_code(card.get("setId")) or min(codes, default=None)
        if canonical is None:
            continue
        for code in codes | {canonical}:
            aliases[code].add(canonical)
        parsed = O._metadata(card)  # Reuse the pinned, cross-language-verified printed contract.
        if canonical not in metadata:
            metadata[canonical] = parsed
        elif metadata[canonical] != parsed:
            metadata[canonical] = None
    return {code: next(iter(names)) for code, names in aliases.items() if len(names) == 1}, metadata


def encode_declaration(deck, cards, aliases, metadata, source_index):
    context = O.as_array(O.encode_hello({"deck": deck, "cards": cards}))[0]
    name = str((deck.get("metadata") or {}).get("name", f"source-index-{source_index}"))
    if context[0, 3] != 1 or context[0, 4] <= 0:
        return None, dict(name=name, source_index=source_index, reason="missing, malformed or incomplete own printed metadata",
                          known_metadata_fraction=float(context[0, 7]), unknown_metadata_copies=float(context[0, 5] * 60))
    counts = Counter()
    for entry in deck["deck"]:
        code = O.normalized_code(entry["id"])
        if code not in aliases:
            return None, dict(name=name, source_index=source_index, reason="unresolved or ambiguous own card alias", card=code)
        counts[aliases[code]] += entry["count"]
    total = sum(counts.values())
    costs, curve, low, units = 0., np.zeros(9, np.float64), 0, 0
    for code, count in sorted(counts.items()):
        card = metadata[code]
        if card is None:
            raise ValueError("known context disagrees with pinned printed metadata")
        costs += count * card["cost"]
        curve[min(int(card["cost"]), 8)] += count
        low += count * (card["cost"] <= 2)
        units += count * card["unit"]
    targets = np.asarray([total / 60, costs / total / 10, low / total, *(curve / total), units / total], np.float32)
    leader = O.normalized_code((deck.get("leader") or {}).get("id"))
    base = O.normalized_code((deck.get("base") or {}).get("id"))
    if leader not in aliases or base not in aliases:
        return None, dict(name=name, source_index=source_index, reason="missing or ambiguous leader/base family identity")
    return dict(name=name, source_index=source_index, features=context, targets=targets, counts=counts,
                fingerprint=fingerprint(counts), leader=aliases[leader], base=aliases[base], total_count=total,
                metadata_known_fraction=float(context[0, 7])), None


def family_components(records, nearclone_threshold=0.8):
    """Keep exact copies, leader/base siblings and >=80% copy-overlap clones together."""
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    edges = []
    for i, a in enumerate(records):
        for j, b in enumerate(records[:i]):
            overlap = sum((a["counts"] & b["counts"]).values()) / min(a["total_count"], b["total_count"])
            reasons = [key for key in ("leader", "base", "fingerprint") if a[key] == b[key]]
            if overlap >= nearclone_threshold:
                reasons.append("nearclone-copy-overlap")
            if reasons:
                parent[find(i)] = find(j)
                edges.append(dict(a=i, b=j, reasons=reasons, copy_overlap=overlap))
    grouped = defaultdict(list)
    for i in range(len(records)):
        grouped[find(i)].append(i)
    groups = {}
    for members in grouped.values():
        key = hashlib.sha256(json.dumps(sorted(set(records[i]["fingerprint"] for i in members)), separators=(",", ":")).encode()).hexdigest()
        groups["family-" + key] = members
    return groups, edges


def grouped_split(groups, size, validation_target=5, seed=SPLIT_SEED):
    if len(groups) < 4:
        raise ValueError("need at least four independent families for train/validation and wrong-own controls")
    ordered = sorted(groups, key=lambda key: hashlib.sha256((seed + key).encode()).hexdigest())
    # Small deterministic knapsack over whole groups, never over target values.
    states = {(0, 0): ()}
    for group in ordered:
        for (count, n), selected in list(states.items()):
            key = (count + len(groups[group]), n + 1)
            candidate = selected + (group,)
            states[key] = min(states.get(key, candidate), candidate)
    candidates = [(abs(count - validation_target), hashlib.sha256("|".join(selected).encode()).hexdigest(), selected)
                  for (count, n), selected in states.items() if 0 < count < size and 2 <= n <= len(groups) - 2]
    if not candidates:
        raise ValueError("no family-separated split with at least two families per partition")
    validation_groups = set(min(candidates)[2])
    val = sorted(i for key, members in groups.items() if key in validation_groups for i in members)
    train = sorted(set(range(size)) - set(val))
    return np.asarray(train, np.int64), np.asarray(val, np.int64)


def wrong_own_indices(records, family_ids, partitions):
    """Fixed within-partition bijection: another owned list, no opponent data."""
    output, modes = np.full(len(records), -1, np.int64), []
    for partition in partitions:
        partition = list(map(int, partition))
        found = None
        for require_curve_change in (True, False):
            candidates = {i: [j for j in partition if family_ids[i] != family_ids[j]
                              and records[i]["fingerprint"] != records[j]["fingerprint"]
                              and (not require_curve_change or not np.array_equal(records[i]["targets"][1:12], records[j]["targets"][1:12]))]
                          for i in partition}
            matched = {}

            def assign(i, seen):
                for j in sorted(candidates[i], key=lambda j: hashlib.sha256(f"{SPLIT_SEED}:{records[i]['fingerprint']}:{records[j]['fingerprint']}".encode()).hexdigest()):
                    if j in seen:
                        continue
                    seen.add(j)
                    if j not in matched or assign(matched[j], seen):
                        matched[j] = i
                        return True
                return False

            if all(assign(i, set()) for i in sorted(partition, key=lambda i: len(candidates[i]))):
                found = {i: j for j, i in matched.items()}
                modes.append("different-family-fingerprint-and-curve" if require_curve_change else "different-family-and-fingerprint")
                break
        if found is None:
            raise ValueError("cannot construct a within-partition wrong-own permutation without family leakage")
        for i, j in found.items():
            output[i] = j
    return output, modes


def build_dataset(decks, catalog):
    cards, normalized_nulls = printed_catalog(catalog)
    aliases, metadata = catalog_index(cards)
    records, excluded = [], []
    for i, deck in enumerate(decks):
        record, reason = encode_declaration(deck, cards, aliases, metadata, i)
        (records if record is not None else excluded).append(record if record is not None else reason)
    groups, edges = family_components(records)
    train, val = grouped_split(groups, len(records))
    family_ids = np.asarray([next(key for key, members in groups.items() if i in members) for i in range(len(records))])
    wrong, modes = wrong_own_indices(records, family_ids, (train, val))
    arrays = dict(deck_features=np.stack([r["features"] for r in records]), targets=np.stack([r["targets"] for r in records]),
                  train_idx=train, val_idx=val, wrong_idx=wrong, fingerprints=np.asarray([r["fingerprint"] for r in records]),
                  family_ids=family_ids, deck_names=np.asarray([r["name"] for r in records]), target_names=np.asarray(TARGET_NAMES))
    manifest = dict(schema=SCHEMA, source_deck_count=len(decks), included_deck_count=len(records), excluded=excluded,
                    printed_metadata_coverage="All included own main-deck copies have complete printed metadata; no rules capability claim.",
                    printed_metadata_adapter=dict(fields=list(PRINTED_FIELDS), removed_nonunit_null_stat_fields=normalized_nulls,
                                                  rule="null nonunit power/hp/upgrade stats are not-applicable; remove them for documented zero defaults"),
                    target_names=TARGET_NAMES, target_groups=dict(count=[0], curve=list(range(1, 12)), draw=[12]),
                    target_units=["copies / 60", "printed mean cost / 10", *["fraction"] * 10, "initial unordered one-card unit probability"],
                    target_constant_flags=[bool(np.ptp(arrays["targets"][:, i]) == 0) for i in range(len(TARGET_NAMES))],
                    split=dict(rule="Connected components: same canonical leader OR base OR main-multiset fingerprint OR shared copies / smaller main count >= 0.8; deterministic whole-group knapsack, no target values",
                               seed=SPLIT_SEED, target_validation_rows=5, train_idx=train.tolist(), val_idx=val.tolist(), family_count=len(groups),
                               train_family_count=len(set(family_ids[train])), val_family_count=len(set(family_ids[val])), edges=edges),
                    wrong_own=dict(rule="Within-partition bijection to a different owned-list fingerprint and family; prefer different curve targets", modes=modes, indices=wrong.tolist(), opponent_data_used=False),
                    declarations=[{k: v for k, v in r.items() if k not in ("features", "targets", "counts")} | {"family_id": str(family_ids[i])} for i, r in enumerate(records)],
                    model_observation="Runner must use a single synthetic fixed board/hand/state independent of declarations and labels.",
                    remaining_supported=False, hidden_draw_order_used=False, gameplay_outcomes_used=False, training_launched=False)
    return arrays, manifest


def git(kessel, *args):
    return subprocess.check_output(["git", "-C", str(kessel), *args], text=True,
                                   env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).strip()


def prepare(decks_path, kessel, out_dir, expected_commit=KESSEL_COMMIT):
    decks_path, kessel, out_dir = Path(decks_path).resolve(), Path(kessel).resolve(), Path(out_dir).resolve()
    head = git(kessel, "rev-parse", "HEAD")
    if head != expected_commit:
        raise ValueError(f"Kessel revision mismatch: expected {expected_commit}, found {head}")
    catalog_path = kessel / "compiler/generated/cards.json"
    if git(kessel, "rev-parse", f"{expected_commit}:compiler/generated/cards.json") != git(kessel, "hash-object", str(catalog_path)):
        raise ValueError("Kessel printed catalog differs from the pinned commit")
    arrays, manifest = build_dataset(json.loads(decks_path.read_text()), json.loads(catalog_path.read_text()))
    license_path, readme = decks_path.parent / "LICENSE.TCGEngine", decks_path.parent / "README.md"
    source_paths = [decks_path, readme, license_path, catalog_path, kessel / "compiler/generated/manifest.json", kessel / "compiler/generated/inputs.json", kessel / "LICENSE", Path(__file__).resolve(), JEPA / "own_deck.py"]
    manifest["sources"] = [dict(path=str(p), sha256=sha256(p), bytes=p.stat().st_size) for p in source_paths]
    manifest["provenance"] = dict(deck_upstream="TCGEngine / SWU Stats; public Premier event lists, September 2026",
                                  deck_upstream_commit=UPSTREAM_DECK_COMMIT, deck_upstream_folder="SWUSim/Tests/BotFixtures/ash-meta-2026-09",
                                  deck_license="MIT, Copyright (c) 2025 TCG-Engine; notice copied next to derived dataset",
                                  kessel_commit=head, kessel_catalog_schema="swu-card-ir-cards/v1", catalog_use="Printed card metadata only; discard abilities and capability/runtime admission data",
                                  kessel_code_license="MIT; game card data retains source game intellectual-property scope",
                                  network_or_fresh_scrape=False, human_results_or_player_identifiers_used=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "real-decks.npz"
    np.savez_compressed(target, **arrays)
    shutil.copyfile(license_path, out_dir / "LICENSE.TCGEngine")
    shutil.copyfile(kessel / "LICENSE", out_dir / "LICENSE.Kessel")
    manifest["artifact"] = dict(path=str(target), sha256=sha256(target), bytes=target.stat().st_size,
                                arrays={key: dict(shape=list(value.shape), dtype=str(value.dtype)) for key, value in arrays.items()})
    output = out_dir / "real-decks.manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    return target, output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decks", type=Path, default=REPO / "decks/ash-meta-2026-09.json")
    parser.add_argument("--kessel-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    dataset, manifest_path, manifest = prepare(args.decks, args.kessel_dir, args.out_dir)
    print(json.dumps(dict(dataset=str(dataset), manifest=str(manifest_path), sha256=manifest["artifact"]["sha256"],
                          rows=manifest["included_deck_count"], excluded=len(manifest["excluded"]),
                          train=len(manifest["split"]["train_idx"]), validation=len(manifest["split"]["val_idx"]))))


if __name__ == "__main__":
    main()
