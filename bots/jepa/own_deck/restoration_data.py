"""Bounded authored-list restoration fixtures, never quality or gameplay labels.

Primary paths keep main-deck size, printed cost/type/arena/aspects fixed. Separate
incomplete-list paths are diagnostics, not legal remaining game states or negative
training examples. Source-family assignments are inherited without repartition.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unicodedata

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import real_deck_data as R
import own_deck as O

SCHEMA = "jepa-authored-restoration-data/1"
WITNESSES = (
    dict(payoff="ASH_103", trait="imperial", body_unit=True,
         predicate="/abilities/card/0/targetResolver/predicate", owner="/abilities/card/0/targetResolver/owner",
         effect="/abilities/card/0/ifYouDo/effect", mechanism="friendly Imperial defeat condition followed by own resource effect"),
    dict(payoff="LAW_229", trait="gambit", body_unit=False,
         predicate="/abilities/card/0/effect/match/value/left", owner="/abilities/card/0/targetController",
         effect="/abilities/card/0/effect", mechanism="own first Gambit cost adjustment; printed Gambit body"),
    dict(payoff="SEC_101", trait=None, body_unit=True,
         predicate="/abilities/card/1/onlyIfYouDoEffect/targetResolver/predicate/right",
         owner="/abilities/card/1/onlyIfYouDoEffect/targetResolver/predicate/left/left/right",
         effect="/abilities/card/1", mechanism="other friendly unit sharing a source trait can enable contingent damage prevention"),
)


def pointer(value, path):
    for part in path.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def name_key(card):
    return tuple(" ".join(unicodedata.normalize("NFKC", str(card.get(key) or "")).casefold().split()) for key in ("title", "subtitle"))


def raw_printings(catalog):
    choices = defaultdict(dict)
    for row in catalog["cards"]:
        card = row.get("card") or {}
        codes = {code for raw in card.get("setCodes", []) if isinstance(raw, dict) and (code := O.normalized_code(raw))}
        preferred = O.normalized_code(card.get("setId"))
        if preferred:
            codes.add(preferred)
        for code in codes:
            key = (str(card.get("id")), name_key(card))
            choices[code].setdefault(key, row)
    return {code: next(iter(rows.values())) for code, rows in choices.items() if len(rows) == 1}


def eligibility(deck, printings, policy):
    """Audited declaration-construction scope only; no rules execution claim."""
    reasons = []
    if policy.get("primary_construction_scope_supported") is not True:
        reasons.append("admission policy is not approved for primary construction scope")
    allowed = set(policy.get("allowed_printed_sets", []))
    suspended = set(policy.get("suspended_codes", []))
    suspended_ids = set(map(str, policy.get("suspended_card_ids", [])))
    entries = [*(deck.get("deck") or []), *(deck.get("sideboard") or [])]
    sideboard = deck.get("sideboard") or []
    if any(type(x.get("count")) is not int or x["count"] <= 0 for x in sideboard):
        reasons.append("invalid sideboard count")
    if sum(x["count"] for x in sideboard if type(x.get("count")) is int) > policy.get("maximum_sideboard_count", 10):
        reasons.append("sideboard exceeds 10 copies")
    if deck.get("secondleader"):
        reasons.append("second leader unsupported in this Premier fixture")
    for slot, kind in (("leader", "leader"), ("base", "base")):
        entry = deck.get(slot) or {}
        code = O.normalized_code(entry.get("id"))
        row = printings.get(code)
        if type(entry.get("count", 1)) is not int or entry.get("count", 1) != 1 or row is None or kind not in row["card"].get("types", []):
            reasons.append(f"unresolved or invalid {slot}")
    copies = Counter()
    for entry in entries + [deck.get("leader") or {}, deck.get("base") or {}]:
        code = O.normalized_code(entry.get("id"))
        row = printings.get(code)
        if code is None or row is None:
            reasons.append(f"unresolved or ambiguous declared printing: {code}")
            continue
        if code.split("_", 1)[0] not in allowed:
            reasons.append(f"declared printing not admitted under pinned set policy: {code}")
        if code in suspended or str(row["card"].get("id")) in suspended_ids:
            reasons.append(f"suspended card: {code}")
    for entry in entries:
        code, count = O.normalized_code(entry.get("id")), entry.get("count")
        if type(count) is not int or count <= 0 or code not in printings:
            reasons.append("invalid main/sideboard count or identity")
            continue
        card = printings[code]["card"]
        if any(kind in card.get("types", []) for kind in ("leader", "base", "token")):
            reasons.append(f"ineligible main/sideboard card type: {code}")
        copies[name_key(card)] += count
    if any(count > policy.get("max_same_name_subtitle_copies", 3) for count in copies.values()):
        reasons.append("same name and subtitle exceeds canonical copy cap")
    base = O.normalized_code((deck.get("base") or {}).get("id"))
    minimum = policy.get("base_min_overrides", {}).get(base, policy.get("minimum_main_count", 50))
    total = sum(e.get("count", 0) for e in deck.get("deck") or [] if type(e.get("count")) is int)
    if total < minimum:
        reasons.append(f"main deck has {total} copies below admitted minimum {minimum}")
    return dict(admitted=not reasons, reasons=sorted(set(reasons)), main_count=total, minimum_main_count=minimum,
                scope="new declared Premier main plus explicitly empty sideboard; no playability or strategy certification")


def signature(meta):
    return meta["cost"], tuple(meta["types"]), meta["space"], tuple(meta["aspects"])


def canonical_counts(deck, aliases):
    counts = Counter()
    for entry in deck["deck"]:
        counts[aliases[O.normalized_code(entry["id"])]] += entry["count"]
    return counts


def changed_deck(source, removals, additions):
    counts = Counter()
    for entry in source["deck"]:
        counts[entry["id"]] += entry["count"]
    for code in removals:
        if counts[code] <= 0:
            raise ValueError("removal exceeds declared copies")
        counts[code] -= 1
    counts.update(additions)
    result = copy.deepcopy(source)
    result["sideboard"] = []  # A new explicit declaration, not reconstruction of the source event's sideboard.
    result["deck"] = [dict(id=code, count=n) for code, n in sorted(counts.items()) if n]
    return result


def choose_alternatives(source, removed, pool, aliases, metadata, printings, policy, break_traits=None):
    """Deterministic matched substitutions, with canonical copy-cap admission."""
    additions, controls = [], []
    blocked_names = {name_key(printings[code]["card"]) for code in removed}
    break_traits = break_traits or {}
    for slot, code in enumerate(removed):
        original = metadata[aliases[code]]
        candidates = []
        for alternative in sorted(pool):
            candidate = metadata.get(aliases.get(alternative))
            if candidate is None or name_key(printings[alternative]["card"]) in blocked_names or signature(candidate) != signature(original):
                continue
            if set(candidate["traits"]) & set(break_traits.get(slot, [])):
                continue
            trial = changed_deck(source, removed[:slot + 1], additions + [alternative])
            admission = eligibility(trial, printings, policy)
            if not admission["admitted"]:
                continue
            existing = canonical_counts(source, aliases)
            changed = canonical_counts(trial, aliases)
            rank = (set(candidate["traits"]) != set(original["traits"]),
                    len(existing) != len(changed), candidate["keywords"] != original["keywords"],
                    abs(candidate["power"] - original["power"]) + abs(candidate["hp"] - original["hp"]), alternative)
            candidates.append((rank, alternative, candidate))
        if not candidates:
            return None, dict(reason="no admitted equal-cost/type/arena/aspect alternative with copy capacity", slot=slot, card=code)
        _, alternative, candidate = min(candidates, key=lambda x: x[0])
        additions.append(alternative)
        controls.append(dict(removed=code, alternative=alternative, copies=1,
                             exact_cost_type_arena_aspects=True, exact_traits=set(candidate["traits"]) == set(original["traits"]),
                             exact_keywords=candidate["keywords"] == original["keywords"],
                             source_traits=original["traits"], alternative_traits=candidate["traits"],
                             intentionally_absent_traits=break_traits.get(slot, [])))
    return (additions, controls), None


def package_candidates(source, metadata, aliases, printings):
    own = sorted(e["id"] for e in source["deck"])
    for witness in WITNESSES:
        if witness["payoff"] not in own:
            continue
        row = printings[witness["payoff"]]
        try:
            predicate, owner, effect = (pointer(row, witness[key]) for key in ("predicate", "owner", "effect"))
        except (KeyError, IndexError, TypeError):
            continue
        if row.get("status") != "supported":
            continue
        trait = witness["trait"]
        if trait is not None:
            if owner != "self" or predicate.get("name") != "hasSomeTrait" or not any(a.get("value") == trait for a in predicate.get("args", [])):
                continue
            traits = {trait}
        else:
            if predicate.get("kind") != "collection" or predicate.get("receiver", {}).get("value", {}).get("path") != ["source", "traits"]:
                continue
            if owner.get("left", {}).get("path") != ["card", "controller"] or owner.get("right", {}).get("path") != ["player"]:
                continue
            traits = set(metadata[aliases[witness["payoff"]]]["traits"])
        bodies = [code for code in own if code != witness["payoff"] and metadata[aliases[code]] is not None
                  and (not witness["body_unit"] or metadata[aliases[code]]["unit"])
                  and set(metadata[aliases[code]]["traits"]) & traits]
        for body in bodies:
            shared = sorted(set(metadata[aliases[body]]["traits"]) & traits)
            evidence = {**witness, "shared_traits": shared, "body": body, "source_path": row["sourcePath"],
                        "source_hash": row["sourceHash"], "data_hash": row["dataHash"], "ir_status": row["status"],
                        "predicate_node": predicate, "ownership_node": owner, "effect_node": effect,
                        "claim_scope": "explicit source trait-dependent interaction, not demonstrated beneficial synergy or gameplay value"}
            # Body first, payoff last: restoration ordering is recorded, never a quality target.
            yield [body, witness["payoff"]], {0: sorted(traits)}, evidence


def construct(decks, catalog, bank_manifest, policy):
    cards, _ = R.printed_catalog(catalog)
    aliases, metadata = R.catalog_index(cards)
    printings = raw_printings(catalog)
    source_rows = {r["source_index"]: r for r in bank_manifest["declarations"]}
    train_sources = {bank_manifest["declarations"][i]["source_index"] for i in bank_manifest["split"]["train_idx"]}
    val_sources = {bank_manifest["declarations"][i]["source_index"] for i in bank_manifest["split"]["val_idx"]}
    if train_sources & val_sources:
        raise ValueError("inherited source partitions overlap")
    partitions = {i: "train" if i in train_sources else "val" for i in source_rows}
    authored_fingerprints = {R.fingerprint(canonical_counts(d, aliases)) for d in decks}
    pools = {part: {entry["id"] for i, deck in enumerate(decks) if partitions.get(i) == part for entry in deck["deck"]
                    if entry["id"] in printings and entry["id"].split("_", 1)[0] in policy.get("allowed_printed_sets", [])}
             for part in ("train", "val")}
    fit, evaluation, groups, excluded, gaps = [], [], {}, [], []

    def record(source_idx, deck, group_id, kind, step, removed_count, context="fit"):
        features = O.as_array(O.encode_hello({"deck": deck, "cards": cards}))[0]
        if features[0, 3] != 1:
            raise ValueError("incomplete printed metadata in constructed fixture")
        fp = R.fingerprint(canonical_counts(deck, aliases))
        variant = group_id + ":" + kind + ":" + str(step)
        return dict(features=features, source_idx=source_idx, family_id=source_rows[source_idx]["family_id"],
                    partition=partitions[source_idx], variant_id=variant, fingerprint=fp, group_id=group_id, kind=kind,
                    restored_copies=step, curve_step=step,
                    actual_original_copies_restored=0 if kind in ("matched-alternative", "matched-constructed-record") else step,
                    removed_copies=removed_count, total_count=sum(e["count"] for e in deck["deck"]),
                    interpretation="incomplete original diagnostic; not a remaining game state" if kind == "incomplete-diagnostic" else "complete original declaration",
                    main_multiset=deck["deck"], rule_eligibility=eligibility(deck, printings, policy) if kind != "incomplete-diagnostic" else {"admitted": False, "reason": "diagnostic only; no legality or bad-state label"})

    for source_idx, historical_source in enumerate(decks):
        source = changed_deck(historical_source, [], [])
        if source_idx not in source_rows:
            excluded.append(dict(source_idx=source_idx, reason="not included in pinned original-deck bank")); continue
        admission = eligibility(source, printings, policy)
        if not admission["admitted"]:
            excluded.append(dict(source_idx=source_idx, source_name=source_rows[source_idx]["name"], admission=admission)); continue
        original_fp = R.fingerprint(canonical_counts(source, aliases))
        if original_fp != source_rows[source_idx]["fingerprint"]:
            raise ValueError("source multiset differs from pinned family-split bank")
        candidates = []
        for code in sorted(e["id"] for e in source["deck"]):
            match, failure = choose_alternatives(source, [code], pools[partitions[source_idx]], aliases, metadata, printings, policy)
            if match is not None:
                candidates.append(([code], match, None)); break
        if not candidates:
            gaps.append(dict(source_idx=source_idx, kind="individual", reason="no admitted exact coarse-metadata match"))
        package_found = False
        for removed, broken, evidence in package_candidates(source, metadata, aliases, printings):
            match, failure = choose_alternatives(source, removed, pools[partitions[source_idx]], aliases, metadata, printings, policy, broken)
            if match is not None:
                candidates.append((removed, match, evidence)); package_found = True; break
            gaps.append(dict(source_idx=source_idx, kind="rule-grounded-package", witness=evidence["payoff"], body=evidence["body"], reason=failure))
        if not package_found:
            gaps.append(dict(source_idx=source_idx, kind="rule-grounded-package", reason="no admitted matched trait-dependent package; shared trait alone is not substituted as proof"))
        for removed, (alternatives, controls), evidence in candidates:
            kind = "individual" if evidence is None else "rule-grounded-package"
            gid = f"source-{source_idx:02}-{kind}-{hashlib.sha256(json.dumps(removed).encode()).hexdigest()[:12]}"
            negative = changed_deck(source, removed, alternatives)
            if not eligibility(negative, printings, policy)["admitted"]:
                raise ValueError("complete matched declaration failed construction admission")
            if R.fingerprint(canonical_counts(negative, aliases)) == original_fp:
                raise ValueError("matched control did not change the authored multiset")
            if R.fingerprint(canonical_counts(negative, aliases)) in authored_fingerprints:
                gaps.append(dict(source_idx=source_idx, kind=kind, removed_codes=removed, alternatives=alternatives,
                                 reason="constructed negative equals an authored source multiset; whole group skipped"))
                continue
            groups[gid] = dict(source_idx=source_idx, source_name=source_rows[source_idx]["name"], family_id=source_rows[source_idx]["family_id"],
                               partition=partitions[source_idx], kind=kind, removed_codes=removed, removed_copies=len(removed), alternatives=alternatives,
                               controls=controls, rule_witness=evidence, fixed_N=True, original_count=sum(e["count"] for e in source["deck"]),
                               control_path="fixed admitted matched-alternative anchor at every nominal restoration step; actual original copies restored always zero",
                               quality_ordering_label=None, positive_claim="authored-record provenance only", source_admission=admission)
            for label, deck, label_name in ((1, changed_deck(source, [], []), "authored-record"), (0, negative, "matched-constructed-record")):
                row = record(source_idx, deck, gid, label_name, len(removed) if label else 0, len(removed))
                row["label"] = label
                fit.append(row)
            if partitions[source_idx] != "val":
                continue
            for step in range(len(removed) + 1):
                # Fixed-size restoration substitutes authored cards back for their matched alternatives.
                restored = changed_deck(source, removed, removed[:step] + alternatives[step:])
                incomplete = changed_deck(source, removed, removed[:step])
                for path_kind, deck in (("true-restoration", restored), ("matched-alternative", negative), ("incomplete-diagnostic", incomplete)):
                    row = record(source_idx, deck, gid, path_kind, step, len(removed), "eval")
                    if path_kind != "incomplete-diagnostic" and not row["rule_eligibility"]["admitted"]:
                        raise ValueError("graded fixed-size variant failed construction admission")
                    evaluation.append(row)

    arrays = {}
    for prefix, rows in (("fit", fit), ("eval", evaluation)):
        arrays[prefix + "_features"] = np.stack([r["features"] for r in rows]) if rows else np.zeros((0, 2, 207), np.float32)
        for key in ("source_idx", "restored_copies", "curve_step", "actual_original_copies_restored", "removed_copies", "total_count"):
            arrays[prefix + "_" + key] = np.asarray([r[key] for r in rows], np.int64)
        for key in ("family_id", "partition", "variant_id", "fingerprint", "group_id", "kind"):
            arrays[prefix + "_" + ({"family_id": "family_ids", "variant_id": "variant_ids", "group_id": "group_ids", "fingerprint": "fingerprints"}.get(key, key))] = np.asarray([r[key] for r in rows], dtype=str)
    arrays["fit_labels"] = np.asarray([r["label"] for r in fit], np.float32)
    arrays["train_idx"] = np.flatnonzero(arrays["fit_partition"] == "train").astype(np.int64)
    arrays["val_idx"] = np.flatnonzero(arrays["fit_partition"] == "val").astype(np.int64)
    train_families = set(arrays["fit_family_ids"][arrays["train_idx"]])
    val_families = set(arrays["fit_family_ids"][arrays["val_idx"]])
    if train_families & val_families:
        raise ValueError("constructed fixture family leakage")
    if set(arrays["fit_fingerprints"][arrays["train_idx"]]) & set(arrays["fit_fingerprints"][arrays["val_idx"]]):
        raise ValueError("constructed fixture multiset crosses inherited source partitions")
    authored_cards = {part: {aliases[e["id"]] for i, d in enumerate(decks) if partitions.get(i) == part for e in d["deck"]} for part in ("train", "val")}
    manifest = dict(schema=SCHEMA, primary_experiment_admitted=bool(policy.get("primary_construction_scope_supported") and len(train_families) >= 2 and len(val_families) >= 2 and evaluation),
                    admission_policy=policy, excluded_source_lineages=excluded, coverage_gaps=gaps, curve_groups=groups,
                    fit_records=[{k: v for k, v in r.items() if k != "features"} for r in fit],
                    eval_records=[{k: v for k, v in r.items() if k != "features"} for r in evaluation],
                    inherited_split=dict(rule=bank_manifest["split"]["rule"], source_train_indices=sorted(train_sources), source_val_indices=sorted(val_sources), repartitioned=False),
                    declaration_scope=dict(sideboard="Every new fixture explicitly declares an empty sideboard; omitted historical event sideboards are not reconstructed.",
                                           original_sideboards=[dict(source_idx=i, supplied="sideboard" in d, value=d.get("sideboard")) for i, d in enumerate(decks)]),
                    fit_label_semantics="Balanced authored-record versus constructed matched-record provenance, never deck quality or winning probability",
                    eval_label_semantics="No quality labels or required restoration score ordering; heldout paths are inspected only",
                    identity_overlap=dict(train_authored_canonical_cards=sorted(authored_cards["train"]), val_authored_canonical_cards=sorted(authored_cards["val"]),
                                          shared_authored_canonical_cards=sorted(authored_cards["train"] & authored_cards["val"]), unseen_card_generalization_claim=False),
                    controls=dict(primary_constant_main_size=True, exact_printed_cost_type_arena_aspects=True, canonical_same_name_subtitle_copy_cap=3,
                                  traits="Exact where available for individuals; rule-target body traits intentionally absent for package alternatives, individually recorded",
                                  candidate_universe="Printed, individually admissible main cards from the same inherited partition of the existing deck bank, including cards from lineages excluded for unrelated base admission",
                                  family_names_leaders_bases_model_inputs=False, incomplete_lists_fit_labels=False, remaining_game_state_claim=False),
                    limitations=["Printed matching and construction admission do not demonstrate strategic equivalence or superiority.",
                                 "IR witness records an explicit trait-dependent source interaction, not verified beneficial synergy or executed rules.",
                                 "Authored lists are provenance positives, not ground-truth optimal lists.",
                                 "Shared card identities may cross heldout families; compare identity-masked and full inputs.",
                                 "Incomplete original paths are distribution/size diagnostics, never negative remaining-game labels."],
                    training_launched=False, games_executed=False)
    return arrays, manifest


def prepare(decks_path, kessel, bank_path, policy_path, out_dir):
    decks_path, kessel, bank_path, policy_path, out_dir = map(Path, (decks_path, kessel, bank_path, policy_path, out_dir))
    if R.git(kessel, "rev-parse", "HEAD") != R.KESSEL_COMMIT:
        raise ValueError("Kessel source revision changed")
    catalog_path = kessel / "compiler/generated/cards.json"
    if R.git(kessel, "rev-parse", f"{R.KESSEL_COMMIT}:compiler/generated/cards.json") != R.git(kessel, "hash-object", str(catalog_path)):
        raise ValueError("pinned catalog bytes changed")
    bank = json.loads(bank_path.read_text())
    if R.sha256(decks_path) != next(s["sha256"] for s in bank["sources"] if Path(s["path"]).name == decks_path.name):
        raise ValueError("source deck bank changed after family split")
    policy = json.loads(policy_path.read_text())
    arrays, manifest = construct(json.loads(decks_path.read_text()), json.loads(catalog_path.read_text()), bank, policy)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "restoration-data.npz"
    np.savez_compressed(target, **arrays)
    paths = [decks_path, catalog_path, bank_path, policy_path, Path(__file__), HERE / "real_deck_data.py", O.__file__]
    manifest["sources"] = [dict(path=str(p), sha256=R.sha256(p)) for p in paths]
    manifest["provenance"] = bank["provenance"]
    manifest["artifact"] = dict(path=str(target), sha256=R.sha256(target), arrays={k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in arrays.items()})
    for name in ("LICENSE.TCGEngine", "LICENSE.Kessel"):
        shutil.copyfile(bank_path.parent / name, out_dir / name)
    output = out_dir / "restoration-data.manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    return target, output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decks", type=Path, default=R.REPO / "decks/ash-meta-2026-09.json")
    parser.add_argument("--kessel-dir", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--admission-policy", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    a = parser.parse_args()
    dataset, manifest_path, manifest = prepare(a.decks, a.kessel_dir, a.bank_manifest, a.admission_policy, a.out_dir)
    print(json.dumps(dict(dataset=str(dataset), manifest=str(manifest_path), sha256=manifest["artifact"]["sha256"],
                          admitted=manifest["primary_experiment_admitted"], fit=len(manifest["fit_records"]), evaluation=len(manifest["eval_records"]), groups=len(manifest["curve_groups"]))))


if __name__ == "__main__":
    main()
