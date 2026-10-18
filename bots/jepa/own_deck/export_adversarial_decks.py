"""Bounded scorer-adversarial deck coherence counterfactuals; no quality oracle.

Generate before scoring, then score once with each existing frozen head. Search
minima use the full head only. A disjoint source/generator family is never ranked.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export_deckiness as E

SEED = 271828
FAMILIES = ("search-uniform", "search-trait-preferred", "reserved-balanced")
LEVELS = (1, 4, 8, "max_replaceable")
LIMITATIONS = [
    "Scorer-adversarial exploratory counterfactuals, not true incoherence, optimal corruption, strength or causal evidence about strategic synergy.",
    "The full frozen authored-versus-constructed scorer is weak; selecting its minimum is deliberately adaptive to that scorer and is not independent validation.",
    "The identity-masked saved head is an unselected diagnostic with shared training provenance, not statistically independent quality truth.",
    "The reserved generator uses disjoint inherited-validation source identities and is not ranked, selected or included in minima summaries; shared card identities remain.",
    "All modifications preserve exact printed cost/type/arena/aspect counts, leader/base, size, canonical copy cap and the pinned policy, but metadata equivalence does not establish strategic equivalence.",
    "max_replaceable is the feasible maximum within the fixed novel-name exact-metadata source-bank pool, not a global minimum over all legal decks or all possible substitutions.",
    "Reviewed trait-target witnesses cover only three explicit IR patterns; unknown interactions and native runtime behavior are not imputed.",
    "No fit, model update, native engine call, game, paid job, deployment, hidden draw order or opponent private state is used.",
]


def score_hash(rows):
    return hashlib.sha256(json.dumps([r["scores"] for r in rows], sort_keys=True).encode()).hexdigest()


def protected_legacy(root):
    names = ("deckiness-scores.json", "receipt.json", "preflight.json", "review-candidates.json", "review-pairs.json",
             "metadata-amendment.json", "export-source.executed.py")
    return {str(root / n): E.sha(root / n) for n in names} | {str(HERE / "export_deckiness.py"): E.sha(HERE / "export_deckiness.py")}


def expanded(deck):
    return [e["id"] for e in sorted(deck["deck"], key=lambda e: e["id"]) for _ in range(e["count"])]


def coarse_counts(deck, aliases, metadata):
    return dict(sorted(Counter(json.dumps(E.F.signature(metadata[aliases[e["id"]]]), separators=(",", ":"))
                               for e in deck["deck"] for _ in range(e["count"])).items()))


def alternatives(source, pool, aliases, metadata, printings):
    """Novel name/subtitle alternatives make changed-copy counts unambiguous.

    Signature buckets are disjoint and each alternative identity has capacity3.
    The sum of min(source bucket copies, alternative capacity) is consequently
    an exact cardinality maximum within this explicitly restricted pool.
    """
    original_names = {E.F.name_key(printings[e["id"]]["card"]) for e in source["deck"]}
    by_signature = defaultdict(dict)
    for code in pool:
        if E.F.name_key(printings[code]["card"]) in original_names:
            continue
        meta = metadata[aliases[code]]
        if meta is not None:
            by_signature[E.F.signature(meta)].setdefault(E.F.name_key(printings[code]["card"]), code)
    buckets = {key: sorted(values.values()) for key, values in by_signature.items()}
    original = Counter(E.F.signature(metadata[aliases[code]]) for code in expanded(source))
    maximum = sum(min(n, 3 * len(buckets.get(sig, []))) for sig, n in original.items())
    return buckets, maximum


def path(source, buckets, family, seed, aliases, metadata):
    rng = np.random.default_rng(seed)
    slots = expanded(source)
    rng.shuffle(slots)
    used = Counter()
    removals, additions = [], []
    for slot, code in enumerate(slots):
        original = metadata[aliases[code]]
        choices = [c for c in buckets.get(E.F.signature(original), []) if used[c] < 3]
        if not choices:
            continue
        if family == "search-trait-preferred":
            def rank(candidate):
                meta = metadata[aliases[candidate]]
                a, b = set(original["traits"]), set(meta["traits"])
                return (a != b, -len(a & b), set(original["keywords"]) != set(meta["keywords"]),
                        abs(original["power"] - meta["power"]) + abs(original["hp"] - meta["hp"]))
            best = min(rank(c) for c in choices)
            choices = [c for c in choices if rank(c) == best]
            choice = choices[int(rng.integers(len(choices)))]
        elif family == "reserved-balanced":
            # Balanced capacity use is a whole distinct deterministic generator;
            # its path is not chosen or changed in response to either scorer.
            minimum = min(used[c] for c in choices)
            choices = [c for c in choices if used[c] == minimum]
            choice = choices[(slot + seed) % len(choices)]
        else:
            choice = choices[int(rng.integers(len(choices)))]
        removals.append(code)
        additions.append(choice)
        used[choice] += 1
    return removals, additions


def diagnostic(deck, catalog_rows, aliases, metadata, printings):
    traits, keywords = Counter(), Counter()
    supported, unknown, total = 0, 0, sum(e["count"] for e in deck["deck"])
    for entry in deck["deck"]:
        code, count = entry["id"], entry["count"]
        meta = metadata[aliases[code]]
        traits.update({t: count for t in meta["traits"]})
        keywords.update({k: count for k in meta["keywords"]})
        status = printings[code].get("status")
        supported += count * (status == "supported")
        unknown += count * (status != "supported")
    witnesses = defaultdict(lambda: dict(body_codes=set(), shared_traits=set(), evidence=None))
    for removed, _, evidence in E.F.package_candidates(deck, metadata, aliases, printings):
        row = witnesses[evidence["payoff"]]
        row["body_codes"].add(evidence["body"])
        row["shared_traits"].update(evidence["shared_traits"])
        row["evidence"] = {k: evidence[k] for k in ("source_path", "source_hash", "data_hash", "ir_status", "predicate", "owner", "effect", "mechanism")}
    known = [dict(payoff=code, body_codes=sorted(v["body_codes"]), shared_traits=sorted(v["shared_traits"]), evidence=v["evidence"])
             for code, v in sorted(witnesses.items())]
    return dict(trait_copy_counts=dict(sorted(traits.items())), keyword_copy_counts=dict(sorted(keywords.items())),
                catalog_compiler_supported_copies=supported, compiler_unsupported_or_unknown_copies=unknown, total_copies=total,
                compiler_support_is_native_admission=False, reviewed_trait_target_patterns=len(E.F.WITNESSES),
                reviewed_witnesses_present=known, reviewed_witness_count=len(known),
                unknown_trait_target_interactions="All card interactions outside the three explicit reviewed patterns remain unknown; absence of a witness is not absence of synergy.",
                witness_scope="Actual pinned IR condition/ownership/effect nodes plus printed body traits; no execution, utility, strength or beneficial-synergy claim.")


def prepare():
    _, _, provenance, frozen, _ = E.prepare()
    decks = E.read(provenance["source_decks"]["path"])
    catalog = E.read(provenance["catalog"]["path"])
    bank = E.read(provenance["inherited_bank"]["path"])
    policy = E.read(provenance["policy"]["path"])
    cards, _ = E.R.printed_catalog(catalog)
    aliases, metadata = E.R.catalog_index(cards)
    printings = E.F.raw_printings(catalog)
    pool = sorted({e["id"] for d in decks for e in d["deck"]})
    split = provenance["split"]
    source_records = {r["source_index"]: r for r in bank["declarations"]}
    coverage, usable = [], {}
    for i, original in enumerate(decks):
        source = E.F.changed_deck(original, [], [])
        admission = E.F.eligibility(source, printings, policy)
        if not admission["admitted"]:
            coverage.append(dict(source_index=i, admitted=False, reasons=admission["reasons"]))
            continue
        buckets, maximum = alternatives(source, pool, aliases, metadata, printings)
        coverage.append(dict(source_index=i, admitted=True, max_replaceable=maximum,
                             total_count=sum(e["count"] for e in source["deck"])))
        usable[i] = (source, buckets, maximum)
    train = set(split["source_train_indices"])
    validation = set(split["source_val_indices"])
    search = sorted((i for i in usable if i in train), key=lambda i: (-usable[i][2], i))[:4]
    reserved = sorted(i for i in usable if i in validation)
    if len(search) != 4 or len(reserved) != 4 or set(search) & set(reserved):
        raise ValueError("expected four search and four disjoint reserved source identities")
    if set(source_records[i]["family_id"] for i in search) & set(source_records[i]["family_id"] for i in reserved):
        raise ValueError("search/reserved source families overlap")
    rows, declarations = [], []

    def append(deck, source_index, identity, generation):
        source, _, maximum = usable[source_index]
        admission = E.F.eligibility(deck, printings, policy)
        before, after = E.deck_record(source, aliases), E.deck_record(deck, aliases)
        changed = sum(max(v - after["canonical_card_counts"].get(k, 0), 0) for k, v in before["canonical_card_counts"].items())
        constraints = dict(leader_unchanged=deck["leader"] == source["leader"], base_unchanged=deck["base"] == source["base"],
                           main_size_unchanged=before["total_count"] == after["total_count"],
                           exact_cost_type_arena_aspect_multiset=coarse_counts(deck, aliases, metadata) == coarse_counts(source, aliases, metadata),
                           canonical_name_subtitle_copy_cap=admission["admitted"], pinned_policy_admitted=admission["admitted"])
        if not all(constraints.values()):
            raise ValueError("counterfactual violated a fixed construction constraint")
        rows.append(dict(id=identity, source_index=source_index, source_deck_id=f"deck-source-{source_index:02}",
                         source_name=decks[source_index]["metadata"]["name"], source_urls=[E.fixture_url(decks[source_index]["metadata"]["name"])],
                         family_id=source_records[source_index]["family_id"], inherited_source_split="train" if source_index in train else "validation",
                         **after, generation=generation, actual_replaced_copies=changed, max_replaceable_in_fixed_pool=maximum,
                         constraints=constraints, admission=admission, diagnostics=diagnostic(deck, catalog, aliases, metadata, printings),
                         selected_by_full_scorer=False, annotations=[]))
        declarations.append(deck)

    for source_index in sorted(search + reserved):
        append(usable[source_index][0], source_index, f"anchor-{source_index:02}", dict(family="original-anchor", selection_role="anchor"))
    for family_index, family in enumerate(FAMILIES):
        for source_index in reserved if family == "reserved-balanced" else search:
            source, buckets, maximum = usable[source_index]
            for replica in range(3):
                seed = SEED + family_index * 100000 + source_index * 100 + replica
                removals, additions = path(source, buckets, family, seed, aliases, metadata)
                if len(removals) != maximum:
                    raise ValueError("path did not reach its exact fixed-pool capacity maximum")
                for level in LEVELS:
                    n = maximum if level == "max_replaceable" else min(level, maximum)
                    deck = E.F.changed_deck(source, removals[:n], additions[:n])
                    append(deck, source_index, f"counterfactual-{family}-{source_index:02}-r{replica}-{level}",
                           dict(family=family, selection_role="reserved-unranked" if family == "reserved-balanced" else "search",
                                seed=seed, replica=replica, requested_level=level, realized_prefix_copies=n,
                                removed_printed_ids=removals[:n], added_printed_ids=additions[:n],
                                nested_path=True, original_main_name_subtitle_alternatives_excluded=True,
                                algorithm="uniform available exact-metadata novel identities" if family_index == 0 else
                                  "exact metadata with trait equality/overlap, keyword equality and stat-distance preference" if family_index == 1 else
                                  "independent balanced round-robin novel identity capacity, no scorer selection"))
                    if rows[-1]["actual_replaced_copies"] != n:
                        raise ValueError("declared copy changes disagree with fixed nested path")
    if len(rows) > 152 or len(rows) > 192:
        raise ValueError("candidate allocation exceeded")
    features = np.stack([E.P.O.as_array(E.P.O.encode_hello({"deck": d, "cards": cards}))[0] for d in declarations])
    if not np.all(features[:, 0, 3] == 1) or not np.array_equal(features[:, 1], E.P.O.neutral_features(len(rows))[:, 1]):
        raise ValueError("unknown metadata or remaining-deck leakage")
    plan = dict(seed=SEED, max_rows=152, max_modified_candidates=144, max_forward_calls=2, max_seconds=20, max_rss_mib=2048,
                cpu_threads=1, paid_spend_usd=0, optimizer_updates=0, native_calls=0, levels=list(LEVELS), paths_per_source_family=3,
                search_sources=search, reserved_sources=reserved, source_selection="Four admitted training sources with highest exact-metadata novel-name replacement capacity, tie source index; all four admitted validation sources reserved. No score used.",
                source_coverage_before_scoring=coverage, families=list(FAMILIES), actual_rows=len(rows),
                replacement_pool_printed_ids=pool, replacement_pool_scope="Pinned source-bank main cards; choose one printing per name/subtitle per signature; alternative names absent original main.",
                cardinality_maximum="Per exact signature, min(original copy slots, 3 times novel alternative identity count); disjoint signatures make sum exact within fixed pool.",
                selection="Full head minimum within SEARCH source/family/requested-level only; tie stable candidate ID; reserved family and masked head never selected/ranked.")
    return rows, features, provenance, frozen, plan


def blind_packets(rows, old_pairs):
    """Metrics and generator labels live only in the separate analysis join."""
    packets, joins = [], []
    def entity(row):
        identity = hashlib.sha256(json.dumps([row["leader"], row["base"], row["canonical_card_counts"]], sort_keys=True).encode()).hexdigest()[:20]
        return dict(opaque_entity_id="entity-" + identity, leader=row["leader"], base=row["base"],
                    cards=row["raw_declared_cards"], canonical_card_counts=row["canonical_card_counts"], source_public_references=row["source_urls"])
    def append(left, right, private):
        opaque = "pair-" + hashlib.sha256(("blind-v1:" + private["original_pair_id"]).encode()).hexdigest()[:20]
        if int(opaque[-1], 16) % 2:
            left, right = right, left
        packets.append(dict(opaque_pair_id=opaque, left=entity(left), right=entity(right), annotations=[]))
        joins.append(dict(opaque_pair_id=opaque, left_entity_id=packets[-1]["left"]["opaque_entity_id"],
                          right_entity_id=packets[-1]["right"]["opaque_entity_id"], **private))
    entities = {row["id"]: row for row in old_pairs["entities"]}
    for pair in old_pairs["pairs"]:
        append(entities[pair["a"]], entities[pair["b"]], dict(original_pair_id=pair["id"], scope="existing-embedding-pair",
                 provenance_and_metrics=pair))
    anchors = {row["source_index"]: row for row in rows if row["generation"]["family"] == "original-anchor"}
    for row in rows:
        if row["generation"]["family"] == "original-anchor":
            continue
        append(anchors[row["source_index"]], row, dict(original_pair_id="adversarial:" + row["id"], scope="counterfactual-pair",
                 source_index=row["source_index"], candidate_id=row["id"], generation=row["generation"],
                 scores=row["scores"], selected_by_full_scorer=row["selected_by_full_scorer"], diagnostics=row["diagnostics"]))
    # Stable opaque order reveals neither model rank nor family sequence.
    packets.sort(key=lambda p: p["opaque_pair_id"])
    joins.sort(key=lambda p: p["opaque_pair_id"])
    return (dict(schema="jepa-blind-deck-annotation-packets/1", packet_count=len(packets), annotations_created=False,
                 instruction="Review each pair using declared card contents and public sources. Record your assessment independently.", packets=packets),
            dict(schema="jepa-blind-deck-annotation-analysis-join/1", not_for_reviewers=True, rows=joins))


def run(out, prior_preparation_seconds=0.):
    if not 0 <= prior_preparation_seconds < 20:
        raise ValueError("invalid cumulative preparation accounting")
    started = time.monotonic() - prior_preparation_seconds
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("refuse existing campaign directory; no automatic repeated forwards")
    legacy = E.ROOT / "experiments/deckiness-export"
    legacy_index = legacy / "index.json"
    old_index_bytes = legacy_index.read_bytes()
    old_index_hash = hashlib.sha256(old_index_bytes).hexdigest()
    protected = protected_legacy(legacy)
    rows, features, provenance, frozen, plan = prepare()
    plan["prior_preparation_seconds"] = prior_preparation_seconds
    protected.update(frozen)
    out.mkdir(parents=True)
    (out / "legacy-index.before.json").write_bytes(old_index_bytes)
    E.write(out / "candidate-inputs.json", dict(schema="jepa-adversarial-deck-inputs/1", plan=plan, provenance=provenance, rows=rows, limitations=LIMITATIONS))
    np.savez_compressed(out / "candidate-features.npz", features=features)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=E.REPO, text=True).strip()
    source = E.pinned(__file__)
    preflight = dict(schema="jepa-adversarial-deck-preflight/1", source=source, commit=commit, plan=plan,
                     candidate_inputs=E.pinned(out / "candidate-inputs.json"), features=E.pinned(out / "candidate-features.npz"),
                     protected_before=protected, legacy_index_before_sha256=old_index_hash, provenance=provenance, limitations=LIMITATIONS)
    E.write(out / "preflight.json", preflight)
    writer = E.RunEvents(out / "run-events.jsonl", "adversarial-deck-search-v1-s271828", commit, plan, provenance, LIMITATIONS)
    writer.emit("status", "frozen_scoring", 0, status="running")
    try:
        measured = E.G.supervise_worker(E._worker, (features, provenance, started), writer, 20., started, 20., 2048.)
        if measured["model_forward_calls"] != 2:
            raise ValueError("unexpected frozen forward count")
        for i, row in enumerate(rows):
            row["scores"] = {arm: measured["scores"][arm][i] for arm in E.P.ARMS}
        originals = {row["id"]: row for row in E.read(legacy / "deckiness-scores.json")["rows"]}
        anchor_errors = [abs(row["scores"][arm] - originals[row["source_deck_id"]]["scores"][arm])
                         for row in rows if row["generation"]["family"] == "original-anchor" for arm in E.P.ARMS]
        if max(anchor_errors) > 1e-6:
            raise ValueError("original anchor score failed prior export reproduction")
        anchors = {row["source_index"]: row for row in rows if row["generation"]["family"] == "original-anchor"}
        selected = []
        for family in FAMILIES[:2]:
            for source_index in plan["search_sources"]:
                for level in LEVELS:
                    candidates = [r for r in rows if r["generation"]["family"] == family and r["source_index"] == source_index and r["generation"]["requested_level"] == level]
                    minimum = min(candidates, key=lambda r: (r["scores"][E.P.ARMS[0]], r["id"]))
                    minimum["selected_by_full_scorer"] = True
                    selected.append(dict(candidate_id=minimum["id"], source_index=source_index, generator_family=family,
                                         requested_level=level, actual_replaced_copies=minimum["actual_replaced_copies"],
                                         full_score=minimum["scores"][E.P.ARMS[0]],
                                         full_delta_vs_source=minimum["scores"][E.P.ARMS[0]] - anchors[source_index]["scores"][E.P.ARMS[0]],
                                         masked_score_unselected=minimum["scores"][E.P.ARMS[1]],
                                         masked_delta_vs_source_unselected=minimum["scores"][E.P.ARMS[1]] - anchors[source_index]["scores"][E.P.ARMS[1]],
                                         selection_scope="minimum of three fixed SEARCH candidates for this source/family/level; no quality claim"))
        if any(row["selected_by_full_scorer"] for row in rows if row["generation"]["family"] == "reserved-balanced"):
            raise ValueError("reserved generator contaminated by selection")
        after = {p: E.sha(p) for p in protected}
        if protected != after:
            raise ValueError("prior score exports or frozen artifacts changed")
        data = dict(schema="jepa-adversarial-deck-export/1", version="v1", metric_display_name=E.METRIC_DISPLAY_NAME,
                    claim="scorer-adversarial exploratory counterfactual", quality_or_strength_validated=False,
                    plan=plan, provenance=provenance, rows=rows, search_minima=selected,
                    reserved_policy="All 48 reserved scores are in fixed candidate order, never ranked/selected/summarized as minima; do not tune on them.",
                    limitations=LIMITATIONS)
        E.write(out / "counterfactuals.json", data)
        old_pairs = E.read(legacy / "review-pairs.json")
        packets, joins = blind_packets(rows, old_pairs)
        E.write(out / "blind_annotation_packets.json", packets)
        E.write(out / "annotation_analysis_join.json", joins)
        for name in ("LICENSE.TCGEngine", "LICENSE.Kessel"):
            shutil.copyfile(legacy / name, out / name)
        receipt = dict(schema="jepa-adversarial-deck-receipt/1", status="completed", source=source, commit=commit, plan=plan,
                       **{k: v for k, v in measured.items() if k != "scores"}, completed_elapsed_seconds=time.monotonic()-started,
                       protected_before=protected, protected_after=after, protected_unchanged=True,
                       source_anchor_score_max_absolute_error=max(anchor_errors), search_minima_count=len(selected),
                       reserved_candidates=sum(r["generation"]["family"] == "reserved-balanced" for r in rows),
                       candidate_support=dict(total_rows=len(rows), original_anchors=len(anchors),
                           modified=sum(r["generation"]["family"] != "original-anchor" for r in rows),
                           unique_modified_compositions=len({(r["source_index"], r["composition_fingerprint"]) for r in rows if r["generation"]["family"] != "original-anchor"}),
                           actual_replaced_range=[min(r["actual_replaced_copies"] for r in rows if r["generation"]["family"] != "original-anchor"),
                                                 max(r["actual_replaced_copies"] for r in rows)]),
                       artifacts={n: E.pinned(out / n) for n in ("counterfactuals.json", "candidate-inputs.json", "candidate-features.npz", "blind_annotation_packets.json", "annotation_analysis_join.json", "legacy-index.before.json")},
                       limitations=LIMITATIONS)
        E.write(out / "receipt.json", receipt)
        E.write(out / "index.json", dict(schema="jepa-adversarial-deck-index/1", version="v1", status="available", claim=data["claim"],
                    metric_display_name=E.METRIC_DISPLAY_NAME, counterfactuals=receipt["artifacts"]["counterfactuals.json"],
                    blind_annotation_packets=receipt["artifacts"]["blind_annotation_packets.json"], analysis_join_not_for_reviewers=receipt["artifacts"]["annotation_analysis_join.json"],
                    receipt=E.pinned(out / "receipt.json"), support=receipt["candidate_support"], annotations_created=False, limitations=LIMITATIONS))
        if E.sha(legacy_index) != old_index_hash:
            raise ValueError("legacy index changed concurrently; versioned artifacts remain saved without replacing its pointer")
        index = json.loads(old_index_bytes)
        index["adversarial_counterfactuals"] = dict(version="v1", **E.pinned(out / "index.json"),
                                                   previous_index_archive=E.pinned(out / "legacy-index.before.json"))
        E.write(legacy_index, index)
        writer.emit("artifact", "completed", 0, status="completed", metrics=dict(model_forward_calls=2, scored_rows=len(rows), optimizer_updates=0, paid_spend_usd=0),
                    artifacts=dict(index=str(out / "index.json"), receipt=str(out / "receipt.json")))
        return receipt
    except BaseException as exc:
        E.write(out / "error.json", dict(status="failed", error=str(exc), guard=getattr(exc, "guard", None),
                                        protected_before=protected, protected_after={p: E.sha(p) for p in protected}))
        writer.emit("error", "aborted", 0, status="failed", reason=str(exc))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=E.ROOT / "experiments/deckiness-export/adversarial-v1")
    parser.add_argument("--plan-only", action="store_true", help="Pure preparation/constraint checks; zero model forwards or files")
    parser.add_argument("--prior-preparation-seconds", type=float, default=0., help="Count prior pure preparation against the same cumulative20s cap")
    args = parser.parse_args()
    if args.plan_only:
        rows, features, provenance, frozen, plan = prepare()
        print(json.dumps(dict(plan=plan, feature_shape=list(features.shape), model_forward_calls=0), indent=2))
    else:
        result = run(args.out, args.prior_preparation_seconds)
        print(json.dumps({k: result[k] for k in ("status", "model_forward_calls", "completed_elapsed_seconds", "candidate_support", "guard", "artifacts")}, indent=2))
