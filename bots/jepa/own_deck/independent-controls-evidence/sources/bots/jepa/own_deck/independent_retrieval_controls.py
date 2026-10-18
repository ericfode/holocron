"""Prepare score-blind retrieval controls; never run a model or engine.

Near/far labels are order under a fixed IR structural proxy, not behavioral
similarity or strategic quality. Printed mechanics are a separate baseline.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import real_deck_data as R
import restoration_data as F

ROOT = R.REPO.parent
KESSEL = Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source")
SOURCES = (10, 14, 25)
SEED = 314159
IR_GROUPS = ("costs", "conditions_targets", "effects", "trigger_structure")
PRINTED_MECHANICS = ("traits", "keywords", "power", "hp", "upgradePower", "upgradeHp", "unique")
LIMITATIONS = [
    "Near/far is defined by a fixed IR structural proxy, not behavioral distance, beneficial synergy, semantic ground truth or strength.",
    "Selecting proxy extremes makes that proxy an oracle for its own labels. It is a declared comparison baseline, not independent validation of semantic correctness.",
    "Strict exact-power/HP controls and prespecified power/HP-confounded fallback controls must be reported separately, never pooled as an unconfounded primary result.",
    "Three source families are the independent roots; doses, variants and invariance views are dependent observations, not an enlarged population sample.",
    "Unreviewed means absent from selected reviewer examples and their whole source families. Original vectors were already part of the global27-deck inventory; no claim of never-inspected original vectors is made.",
    "Whole-card runtime admission is loader/schema evidence, not gameplay conformance or measured effects. No native runtime execution is performed here.",
    "Unsupported/incomplete IR is explicitly unknown, never the zero-effect program. Shared unknown unchanged deck cards limit full-deck proxy coverage.",
    "Canonical identity/permutation/reprint controls test representation correctness, not strategic quality; several views have the same composition.",
    "No neural forward, neighbor metric, classifier, fit, engine call, paid job or opponent/private-state access occurs during preparation.",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def pin(path, expected=None):
    path = Path(path).resolve()
    value = sha(path)
    if expected is not None and value != expected:
        raise ValueError(f"pinned source changed: {path}")
    return dict(path=str(path), sha256=value)


def normalized_program(abilities):
    """Remove only documented root ability display titles; retain all roles/order."""
    if not isinstance(abilities, dict):
        raise ValueError("missing complete all-side ability map")
    result = copy.deepcopy(abilities)
    for side, programs in result.items():
        if not isinstance(side, str) or not isinstance(programs, list):
            raise ValueError("invalid all-side ability map")
        for program in programs:
            if not isinstance(program, dict):
                raise ValueError("invalid ability object")
            program.pop("title", None)
    return result


def atoms(value, path=()):
    """Typed, positioned leaves plus container shape; JSON order is semantic."""
    if isinstance(value, dict):
        yield path + ("$container",), ("object", None)
        for key in sorted(value):
            yield from atoms(value[key], path + (key,))
    elif isinstance(value, list):
        yield path + ("$container",), ("array", len(value))
        for index, item in enumerate(value):
            yield from atoms(item, path + (index,))
    elif value is None:
        yield path, ("null", None)
    elif type(value) is bool:
        yield path, ("boolean", value)
    elif type(value) in (int, float) and math.isfinite(value):
        yield path, ("number", value)
    elif isinstance(value, str):
        yield path, ("string", value)
    else:
        raise ValueError("IR must contain finite typed JSON values")


def role(path):
    words = [str(v).casefold() for v in path]
    if any("cost" in v for v in words):
        return "costs"
    if any(any(k in v for k in ("condition", "predicate", "target", "selector")) for v in words):
        return "conditions_targets"
    if any(any(k in v for k in ("effect", "then", "ifyoudo")) for v in words):
        return "effects"
    return "trigger_structure"


def descriptor(row, admitted):
    code = row.get("setCode")
    why = []
    if row.get("status") != "supported":
        why.append("catalog conversion is not supported")
    admission = admitted.get(code)
    # nativeAdapters may implement behavior outside the exported IR; do not
    # substitute an empty/data-only tree for the complete native implementation.
    if admission is None:
        why.append("whole card is not runtime-admitted")
    elif admission.get("implementation") not in ("sourceIr", "dataOnly"):
        why.append("native adapter has no complete exported behavior contract")
    try:
        program = normalized_program(row.get("abilities"))
    except ValueError as exc:
        why.append(str(exc)); program = None
    if why:
        return dict(known=False, reasons=why, groups=None, normalized_program=None)
    groups = {name: {} for name in IR_GROUPS}
    for path, value in atoms(program):
        groups[role(path)][path] = value
    return dict(known=True, reasons=[], groups=groups, normalized_program=program,
                runtime_implementation=admission["implementation"])


def value_distance(a, b):
    if a[0] != b[0]:
        return 1.
    if a[0] == "number":
        return abs(a[1] - b[1]) / max(1., abs(a[1]), abs(b[1]))
    return float(a[1] != b[1])


def group_distance(a, b):
    paths = set(a) | set(b)
    if not paths:
        return 0.
    return sum(1. if p not in a or p not in b else value_distance(a[p], b[p]) for p in paths) / len(paths)


def ir_distance(a, b):
    if not a["known"] or not b["known"]:
        return dict(known=False, distance=None, parts=None, reason="unknown complete IR is not a zero program")
    parts = {g: group_distance(a["groups"][g], b["groups"][g]) for g in IR_GROUPS}
    return dict(known=True, distance=sum(parts.values()) / len(IR_GROUPS), parts=parts)


def printed_descriptor(row):
    card = row.get("card") or {}
    result, unknown = {}, []
    unit = "unit" in (card.get("types") or [])
    for key in PRINTED_MECHANICS:
        value = card.get(key)
        if key in ("traits", "keywords"):
            if not isinstance(value, list):
                unknown.append(key); continue
            value = sorted(set(value))
        elif key in ("power", "hp") and unit and value is None:
            unknown.append(key); continue
        elif key == "unique" and type(value) is not bool:
            unknown.append(key); continue
        result[key] = value
    return dict(values=result, unknown_fields=unknown)


def printed_distance(a, b):
    parts, unknown = {}, []
    for key in PRINTED_MECHANICS:
        if key not in a["values"] or key not in b["values"]:
            unknown.append(key); continue
        x, y = a["values"][key], b["values"][key]
        if key in ("traits", "keywords"):
            union = set(x) | set(y)
            parts[key] = 1. - len(set(x) & set(y)) / len(union) if union else 0.
        elif type(x) in (int, float) and type(y) in (int, float):
            parts[key] = abs(x-y) / max(1., abs(x), abs(y))
        else:
            parts[key] = float(x != y)
    return dict(parts=parts, distance=sum(parts.values()) / len(parts) if parts else None, unknown_fields=unknown,
                used_for_near_far_selection=False)


def count_baseline(a, b):
    keys = set(a) | set(b)
    shared = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return dict(shared_copies=shared, union_copies=union, weighted_jaccard=shared / union if union else 1.,
                l1_copies=sum(abs(a.get(k, 0)-b.get(k, 0)) for k in keys))


def family_exclusion(declarations, reviewed_ids):
    by_source = {d["source_index"]: d["family_id"] for d in declarations}
    reviewed_sources = {int(v.rsplit("-", 1)[1]) for v in reviewed_ids}
    forbidden = {by_source[i] for i in reviewed_sources}
    if any(by_source[i] in forbidden for i in SOURCES):
        raise ValueError("planned source belongs to a reviewed family")
    return dict(reviewed_source_indices=sorted(reviewed_sources), excluded_family_ids=sorted(forbidden),
                all_source_indices_in_excluded_families=sorted(i for i, f in by_source.items() if f in forbidden))


def row_counts(deck, aliases):
    return dict(sorted(F.canonical_counts(deck, aliases).items()))


def stat_key(row):
    card = row["card"]
    return card.get("power"), card.get("hp")


def fixed_plan():
    return dict(schema="jepa-independent-retrieval-control-plan/1", seed=SEED, source_indices=list(SOURCES),
                maximum_modified=24, maximum_rows=36, minimum_primary_families=3, minimum_slots_per_family=1,
                maximum_slots_per_source=2, doses=[1, 2],
                source_choice="Fixed held-out source families10/14/25; exclude all selected reviewed examples and their complete families, including02/03.",
                candidate_universe="Main-deck printings in the pinned27-list source bank; exact cost/type/arena/aspect signature, novel canonical name/subtitle absent source, admitted full resulting declaration and complete sourceIr/dataOnly runtime-admitted IR.",
                pool_rule="For each slot use exact-power/HP pool if it has>=2 alternatives with different IR distances; otherwise exact-core pool is a separately labeled confounded exploratory stratum. Choose strict slots first, then source code. No vector results used.",
                selection="At most2 slots/source, source count>=2; independently min/max IR-only distance with printed-code tie break; no printed traits/keywords/stats in that selection distance.",
                proxy=dict(groups=list(IR_GROUPS), weights=[.25]*4, path_matching="exact typed all-side ordered JSON path, containers retained; object keys sorted; root ability display title excluded",
                           numeric="abs(x-y)/max(1,abs(x),abs(y)); unmatched path/type is1; categorical mismatch is1; each group mean then equal group mean",
                           semantics="Structural proxy only, no execution or strategic meaning; no textual similarity or learned parameters"),
                invariance="Original anchor, reordered entries, expanded/split entries, and one genuine policy-admitted reprint if available; canonical and encoded-feature equality checked.",
                prior_controls="New fixed operators/seeds; exclude any candidate composition identical to a previous reserved counterfactual; no prior scores/ranks read or used.",
                preparation_only=True, model_forward_calls=0, neighbor_metrics=0, optimizer_updates=0, native_calls=0, paid_spend_usd=0)


def prepare(out):
    started = time.monotonic()
    out = Path(out).resolve()
    if (out / "deck-controls.manifest.json").exists():
        raise ValueError("refuse overwriting frozen controls")
    bank_path = ROOT / "experiments/data/real-decks.manifest.json"
    pin(bank_path, "1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622")
    bank = read(bank_path)
    source_pin = next(s for s in bank["sources"] if Path(s["path"]).name == "ash-meta-2026-09.json")
    catalog_pin = next(s for s in bank["sources"] if s["path"].endswith("/compiler/generated/cards.json"))
    pin(source_pin["path"], source_pin["sha256"]); pin(catalog_pin["path"], catalog_pin["sha256"])
    runtime_path = KESSEL / "compiler/generated/runtime-admission.json"
    policy_path = ROOT / "experiments/restoration/admission-policy.json"
    review_path = ROOT / "experiments/deckiness-export/adversarial-v1/reviews-v2/joined-annotations.json"
    prior_path = ROOT / "experiments/deckiness-export/adversarial-v1/counterfactuals.json"
    pin(policy_path, "0e9826aa46c2932d4856c9f5087c41beb06ca60805205cb852e061b2cca18e07")
    pin(review_path, "4ebb903b8777fc3a8f6950ae22fef88aa28c451df6126895a405af729cdb8123")
    pin(prior_path, "2e35574a5ac4f19bb43c450ac0fea02f0b54676eeb6691bbe654297402793cfe")
    if R.git(KESSEL, "rev-parse", "HEAD") != R.KESSEL_COMMIT or R.git(KESSEL, "rev-parse", f"{R.KESSEL_COMMIT}:compiler/generated/runtime-admission.json") != R.git(KESSEL, "hash-object", str(runtime_path)):
        raise ValueError("runtime-admission bytes differ from pinned source revision")
    review, prior = read(review_path), read(prior_path)
    reviewed_ids = {deck for pair in review["pairs_by_id"] for deck in pair.split("--")}
    exclusion = family_exclusion(bank["declarations"], reviewed_ids)
    forbidden_compositions = {(r["source_index"], r["composition_fingerprint"]) for r in prior["rows"]
                              if r["generation"]["family"] == "reserved-balanced"}
    if not set(SOURCES) <= set(bank["declarations"][i]["source_index"] for i in bank["split"]["val_idx"]):
        raise ValueError("planned sources are not inherited validation roots")
    declarations = {d["source_index"]: d for d in bank["declarations"]}
    decks, catalog, runtime, policy = read(source_pin["path"]), read(catalog_pin["path"]), read(runtime_path), read(policy_path)
    original_dataset = ROOT / "experiments/data/real-decks.npz"
    pin(original_dataset, bank["artifact"]["sha256"])
    paths = [Path(__file__), HERE / "real_deck_data.py", HERE / "restoration_data.py", R.O.__file__, bank_path, source_pin["path"], catalog_pin["path"], runtime_path, policy_path, review_path, prior_path, original_dataset]
    pins = [pin(p) for p in paths]
    protected_before = {p["path"]: p["sha256"] for p in pins}
    cards, _ = R.printed_catalog(catalog)
    aliases, metadata = R.catalog_index(cards)
    printings = F.raw_printings(catalog)
    admitted = {r["setCode"]: r for r in runtime["runtimeAdmittedCards"]}
    pool = sorted({entry["id"] for deck in decks for entry in deck["deck"]})
    descriptors = {code: descriptor(printings[code], admitted) for code in pool}
    printed = {code: printed_descriptor(printings[code]) for code in pool}
    plan = fixed_plan()
    records, inputs, eligible_inventory, gaps, anchor_idx = [], [], [], [], {}

    def append(deck, source_index, kind, identity, lineage, mechanical_labels=None):
        source = F.changed_deck(decks[source_index], [], [])
        admission = F.eligibility(deck, printings, policy)
        if not admission["admitted"]:
            raise ValueError("control declaration failed pinned policy")
        counts, source_counts = row_counts(deck, aliases), row_counts(source, aliases)
        features = R.O.as_array(R.O.encode_hello({"deck": deck, "cards": cards}))[0]
        if features[0, 3] != 1 or not np.array_equal(features[1], R.O.neutral_features(1)[0, 1]):
            raise ValueError("unknown printed features or remaining-composition leak")
        for entry in deck["deck"]:
            if entry["id"] not in descriptors:
                descriptors[entry["id"]] = descriptor(printings[entry["id"]], admitted)
                printed[entry["id"]] = printed_descriptor(printings[entry["id"]])
        known_copies = sum(e["count"] for e in deck["deck"] if descriptors[e["id"]]["known"])
        unknown_cards = [dict(code=e["id"], copies=e["count"], reasons=descriptors[e["id"]]["reasons"])
                         for e in deck["deck"] if not descriptors[e["id"]]["known"]]
        row = dict(id=identity, source_index=source_index, kind=kind, family_id=declarations[source_index]["family_id"],
                   canonical_card_counts=counts, raw_declared_cards=deck["deck"], leader=deck["leader"], base=deck["base"], sideboard=[],
                   composition_fingerprint=R.fingerprint(counts), original_source_fingerprint=R.fingerprint(source_counts),
                   lineage=lineage, mechanical_labels=mechanical_labels or dict(scope="identity invariant; correctness only"),
                   invariance_group=f"source-{source_index:02}-canonical-original" if kind in ("anchor", "permutation", "split-entries", "reprint") else None,
                   count_baseline=count_baseline(source_counts, counts), admission=admission,
                   complete_ir_coverage=dict(known_copies=known_copies, unknown_copies=sum(e["count"] for e in deck["deck"])-known_copies,
                                             unknown_cards=unknown_cards, whole_deck_semantics_known=not unknown_cards),
                   source_urls=["https://github.com/TCG-Engine/TCGEngine/blob/" + R.UPSTREAM_DECK_COMMIT +
                                "/SWUSim/Tests/BotFixtures/ash-meta-2026-09/" + decks[source_index]["metadata"]["name"] + ".txt"])
        records.append(row); inputs.append(features)

    for source_index in SOURCES:
        source = F.changed_deck(decks[source_index], [], [])
        if not F.eligibility(source, printings, policy)["admitted"]:
            raise ValueError("fixed source not admitted")
        anchor_idx[source_index] = len(records)
        append(source, source_index, "anchor", f"independent-source-{source_index:02}", dict(source_index=source_index, seed=SEED, inherited_partition="validation", reviewed=False))
        source_names = {F.name_key(printings[e["id"]]["card"]) for e in source["deck"]}
        available = []
        for entry in source["deck"]:
            code = entry["id"]
            if entry["count"] < 2:
                gaps.append(dict(source_index=source_index, code=code, reason="fewer than two source copies")); continue
            if not descriptors[code]["known"]:
                gaps.append(dict(source_index=source_index, code=code, reason="unknown complete source IR", detail=descriptors[code]["reasons"])); continue
            candidates = []
            for alternate in pool:
                if metadata.get(aliases.get(alternate)) is None:
                    continue
                if aliases[alternate] in row_counts(source, aliases) or F.name_key(printings[alternate]["card"]) in source_names:
                    continue
                if F.signature(metadata[aliases[alternate]]) != F.signature(metadata[aliases[code]]):
                    continue
                if not descriptors[alternate]["known"]:
                    continue
                trials = [F.changed_deck(source, [code]*dose, [alternate]*dose) for dose in (1, 2)]
                if any(not F.eligibility(d, printings, policy)["admitted"] for d in trials):
                    continue
                if any((source_index, R.fingerprint(row_counts(d, aliases))) in forbidden_compositions for d in trials):
                    gaps.append(dict(source_index=source_index, code=code, alternate=alternate, reason="would duplicate previous reserved composition")); continue
                distance = ir_distance(descriptors[code], descriptors[alternate])
                candidates.append(dict(code=alternate, canonical_id=aliases[alternate], ir_proxy=distance,
                                       exact_power_hp=stat_key(printings[code]) == stat_key(printings[alternate]),
                                       printed_baseline=printed_distance(printed[code], printed[alternate]),
                                       whole_card_runtime_admission=admitted[printings[alternate]["setCode"]],
                                       normalized_program=descriptors[alternate]["normalized_program"]))
            strict = [c for c in candidates if c["exact_power_hp"]]
            def usable(values):
                return len({c["canonical_id"] for c in values}) >= 2 and len({c["ir_proxy"]["distance"] for c in values}) >= 2
            chosen_pool, stratum = (strict, "strict-power-hp") if usable(strict) else (candidates, "exploratory-power-hp-confounded")
            inventory = dict(source_index=source_index, source_card=code, source_canonical_id=aliases[code], source_copies=entry["count"],
                             source_program=descriptors[code]["normalized_program"], source_runtime_admission=admitted[printings[code]["setCode"]],
                             eligible_alternatives=candidates, exact_power_hp_candidates=len(strict), selected_stratum=stratum,
                             usable=usable(chosen_pool), selected_slot=False)
            eligible_inventory.append(inventory)
            if usable(chosen_pool):
                available.append((stratum != "strict-power-hp", code, chosen_pool, inventory))
            else:
                gaps.append(dict(source_index=source_index, code=code, reason="fewer than two distinct complete-IR alternatives with different IR distances", eligible=len(candidates), exact_power_hp=len(strict)))
        for _, code, candidates, inventory in sorted(available, key=lambda x: (x[0], x[1]))[:2]:
            inventory["selected_slot"] = True
            near = min(candidates, key=lambda c: (c["ir_proxy"]["distance"], c["code"]))
            far = min(candidates, key=lambda c: (-c["ir_proxy"]["distance"], c["code"]))
            if near["canonical_id"] == far["canonical_id"]:
                raise ValueError("near/far extremes are aliases of the same canonical identity")
            if near["ir_proxy"]["distance"] >= far["ir_proxy"]["distance"]:
                raise ValueError("near/far proxy has no contrast")
            for dose in (1, 2):
                pair_ids = []
                for label, candidate in (("ir-near", near), ("ir-far", far)):
                    deck = F.changed_deck(source, [code]*dose, [candidate["code"]]*dose)
                    identity = f"independent-{source_index:02}-{code.lower()}-n{dose}-{label}"
                    append(deck, source_index, label, identity,
                           dict(seed=SEED, source_card=code, replacement_card=candidate["code"], copies=dose,
                                new_operator="fixed-IR-structural-extreme-exact-printed-core", inherited_partition="validation", stratum=inventory["selected_stratum"]),
                           dict(label=label, scope="proxy-defined structural order, not behavioral truth", ir_only=candidate["ir_proxy"],
                                printed_mechanics_unselected=candidate["printed_baseline"], exact_power_hp=candidate["exact_power_hp"],
                                strict_primary=inventory["selected_stratum"] == "strict-power-hp"))
                    pair_ids.append(len(records)-1)
                if records[pair_ids[0]]["count_baseline"] != records[pair_ids[1]]["count_baseline"]:
                    raise ValueError("near/far count-distance confound")
        permutation = copy.deepcopy(source)
        rng = np.random.default_rng(SEED + source_index)
        rng.shuffle(permutation["deck"])
        append(permutation, source_index, "permutation", f"independent-{source_index:02}-permutation", dict(seed=SEED + source_index, operation="main-entry permutation"))
        split = copy.deepcopy(source)
        split["deck"] = [dict(id=e["id"], count=1) for e in reversed(source["deck"]) for _ in range(e["count"])]
        append(split, source_index, "split-entries", f"independent-{source_index:02}-split", dict(seed=SEED, operation="expanded one-copy entries in reverse printed order"))
        reprints = []
        for entry in source["deck"]:
            for alternate, raw in sorted(printings.items()):
                if alternate == entry["id"] or aliases.get(alternate) != aliases[entry["id"]]:
                    continue
                if alternate.split("_", 1)[0] not in policy["allowed_printed_sets"]:
                    continue
                reprint = F.changed_deck(source, [entry["id"]]*entry["count"], [alternate]*entry["count"])
                if F.eligibility(reprint, printings, policy)["admitted"]:
                    reprints.append((entry["id"], alternate, reprint))
        if reprints:
            old, new, reprint = min(reprints, key=lambda v: (v[0], v[1]))
            append(reprint, source_index, "reprint", f"independent-{source_index:02}-reprint", dict(seed=SEED, operation="genuine admitted raw reprint alias", original_printing=old, replacement_printing=new))
        else:
            gaps.append(dict(source_index=source_index, kind="reprint", reason="no alternative raw printing passes pinned current declaration policy"))
    if len(records) > 36:
        raise ValueError("frozen row allocation exceeded")
    features = np.stack(inputs).astype(np.float32)
    with np.load(original_dataset, allow_pickle=False) as old:
        for source_index in SOURCES:
            index = next(i for i, d in enumerate(bank["declarations"]) if d["source_index"] == source_index)
            if not np.array_equal(features[anchor_idx[source_index]], old["deck_features"][index]):
                raise ValueError("anchor differs from original pinned dataset")
    for row, feature in zip(records, features):
        if row["invariance_group"] is not None and (row["canonical_card_counts"] != records[anchor_idx[row["source_index"]]]["canonical_card_counts"] or
                not np.array_equal(feature, features[anchor_idx[row["source_index"]]])):
            raise ValueError("invariance control failed canonical/feature equality")
    support = {str(source): dict(slots=sum(r["source_index"] == source and r["selected_slot"] for r in eligible_inventory),
                                strict_slots=sum(r["source_index"] == source and r["selected_slot"] and r["selected_stratum"] == "strict-power-hp" for r in eligible_inventory),
                                modified_rows=sum(r["source_index"] == source and r["kind"] in ("ir-near", "ir-far") for r in records)) for source in SOURCES}
    sufficient = all(v["slots"] >= 1 for v in support.values())
    strict_sufficient = all(v["strict_slots"] >= 1 for v in support.values())
    feature_groups = {}
    for row, feature in zip(records, features):
        feature_groups.setdefault(feature.tobytes(), []).append(row)
    collisions = [dict(row_ids=[r["id"] for r in values], distinct_compositions=len({r["composition_fingerprint"] for r in values}))
                  for values in feature_groups.values() if len({r["composition_fingerprint"] for r in values}) > 1]
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "deck-controls.npz", deck_features=features, row_ids=np.asarray([r["id"] for r in records], dtype=str),
                        source_indices=np.asarray([r["source_index"] for r in records], np.int64))
    protected_after = {p: sha(p) for p in protected_before}
    if protected_after != protected_before:
        raise ValueError("protected input/source changed during preparation")
    descriptor_data = {code: dict(known=v["known"], reasons=v["reasons"], normalized_program=v["normalized_program"], printed_mechanics=printed[code],
                                 row_sha256=hashlib.sha256(json.dumps(printings[code], sort_keys=True).encode()).hexdigest(),
                                 source_path=printings[code].get("sourcePath"), source_hash=printings[code].get("sourceHash"),
                                 runtime_admission=admitted.get(printings[code]["setCode"])) for code, v in descriptors.items()}
    write(out / "mechanical-inventory.json", dict(schema="jepa-independent-mechanical-inventory/1", plan=plan,
                                                 descriptors=descriptor_data, eligible_slots=eligible_inventory, exclusions=gaps))
    manifest = dict(schema="jepa-independent-deck-controls/1", status="prepared-awaiting-root-go", plan=plan, rows=records,
                    artifact=pin(out / "deck-controls.npz"), mechanical_inventory=pin(out / "mechanical-inventory.json"), sources=pins,
                    anchor_indices={str(k): v for k, v in anchor_idx.items()}, family_exclusion=exclusion, support=support,
                    minimum_family_support_satisfied=sufficient, minimum_strict_primary_support_satisfied=strict_sufficient,
                    distinct_composition_feature_collisions=collisions,
                    counts=dict(rows=len(records), modified=sum(r["kind"] in ("ir-near", "ir-far") for r in records),
                                unique_source_compositions=len({(r["source_index"], r["composition_fingerprint"]) for r in records}),
                                unique_feature_rows=len({v.tobytes() for v in features})),
                    inherited_validation_source_family_ids=[declarations[i]["family_id"] for i in SOURCES],
                    baseline_fields=dict(count="Exact canonical copy intersection/union/L1; expected near/far tie at dose1/2", ir="Per-card fixed typed ordered proxy; unknown is None", printed="Separate fixed printed mechanics comparison; not used to select extrema"),
                    preparation_elapsed_seconds=time.monotonic()-started, model_forward_calls=0, neighbor_metrics=0, optimizer_updates=0, native_calls=0, paid_spend_usd=0,
                    protected_before=protected_before, protected_after=protected_after, protected_unchanged=True,
                    limitations=LIMITATIONS)
    write(out / "deck-controls.manifest.json", manifest)
    write(out / "plan.json", plan)
    write(out / "preparation-receipt.json", dict(status="prepared", source=pin(__file__), commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=R.REPO, text=True).strip(),
             manifest=pin(out / "deck-controls.manifest.json"), artifact=manifest["artifact"], support=support,
             minimum_family_support_satisfied=sufficient, minimum_strict_primary_support_satisfied=strict_sufficient,
             elapsed_seconds=manifest["preparation_elapsed_seconds"], model_forward_calls=0, neighbor_metrics=0, optimizer_updates=0, native_calls=0, paid_spend_usd=0))
    for license_name in ("LICENSE.TCGEngine", "LICENSE.Kessel"):
        shutil.copyfile(ROOT / "experiments/data" / license_name, out / license_name)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Root-authorized pure preparation; no encoder or NN calls")
    parser.add_argument("--out", type=Path, default=ROOT / "experiments/independent-controls")
    args = parser.parse_args()
    if args.prepare:
        launch_started = time.monotonic()
        args.out.mkdir(parents=True, exist_ok=True)
        try:
            manifest = prepare(args.out)
        except BaseException as exc:
            write(args.out / "preparation-error.json", dict(status="failed", reason=str(exc), elapsed_seconds=time.monotonic()-launch_started,
                  source=pin(__file__), artifacts_already_saved=[pin(p) for p in args.out.iterdir() if p.is_file()],
                  model_forward_calls=0, neighbor_metrics=0, optimizer_updates=0, native_calls=0, paid_spend_usd=0))
            raise
        print(json.dumps({k: manifest[k] for k in ("status", "support", "counts", "minimum_family_support_satisfied", "minimum_strict_primary_support_satisfied", "preparation_elapsed_seconds")}, indent=2))
    else:
        print(json.dumps(fixed_plan(), indent=2))
