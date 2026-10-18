"""Separate synthetic exact-profile IR-module assay; no neural/native execution."""
import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"
import argparse
from collections import Counter, defaultdict
import copy
import itertools
import json
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_retrieval_controls as C

OUT = C.ROOT / "experiments/independent-controls/module-v2"
SEED = 314160
CONSTRUCTION_TERMS = ("deckbuilding", "deck building", "deck construction", "in your deck", "in your main deck", "deck may contain", "deck size", "minimum deck")


def strict_signature(row):
    card = row["card"]
    return (card.get("cost"), tuple(sorted(card.get("types") or [])), card.get("arena"),
            tuple(sorted(card.get("aspects") or [])), card.get("power"), card.get("hp"))


def plan():
    return dict(schema="jepa-independent-module-plan/2", seed=SEED, source_indices=list(C.SOURCES),
                module_pool="All uniquely resolved allowed-set main-card printings from the pinned catalogue; sourceIr/dataOnly complete runtime admission; no flagged construction text; canonical and name/subtitle aliases grouped.",
                strict_match=["cost", "types", "arena", "aspects", "power", "hp"], keywords="Recorded as exact/changed separately; never assumed equal or used for lexicographic selection.",
                module_selection="For source10,14,25 in order, lexicographic A/near/far code tuple with IR(A,near)<IR(A,far)-1e-12; all module names absent background; all9 module identities disjoint. Lexicographically first feasible joint assignment, no vectors/review judgments used.",
                anchor="Synthetic: remove first3 expanded copies in sorted raw-code order; add3A. Background leader/base/size retained. New profile may differ from authored original.",
                variants="Replace1 or2 A copies by near/far card, exact full-deck cost/type/arena/aspects/power/HP profile versus synthetic anchor and equal count overlap;3anchors+12variants+6permutation/split invariances=21rows.",
                minimum_modules=3, maximum_new_rows=21, maximum_combined_rows=40, first_phase="Publish all strict groups, eligibility reasons, distances and disjoint-module feasibility before deck generation.",
                interpretation="New conditional IR-structural proxy assay, not a relaxed v1 primary test, behavioral truth, coherence or strength. V1 failures remain unchanged.",
                ir_proxy=C.fixed_plan()["proxy"], model_forward_calls=0, neighbor_metrics=0, native_calls=0, optimizer_updates=0, paid_spend_usd=0)


def load():
    base = C.ROOT / "experiments/independent-controls"
    old = C.read(base / "deck-controls.manifest.json")
    for item in old["sources"]:
        C.pin(item["path"], item["sha256"])
    bank = C.read(C.ROOT / "experiments/data/real-decks.manifest.json")
    catalog_pin = next(p for p in old["sources"] if p["path"].endswith("/compiler/generated/cards.json"))
    runtime_pin = next(p for p in old["sources"] if p["path"].endswith("/compiler/generated/runtime-admission.json"))
    decks_pin = next(p for p in old["sources"] if p["path"].endswith("/ash-meta-2026-09.json"))
    policy_pin = next(p for p in old["sources"] if p["path"].endswith("/admission-policy.json"))
    catalog, runtime, decks, policy = (C.read(p["path"]) for p in (catalog_pin, runtime_pin, decks_pin, policy_pin))
    cards, _ = C.R.printed_catalog(catalog)
    aliases, metadata = C.R.catalog_index(cards)
    printings = C.F.raw_printings(catalog)
    admitted = {r["setCode"]: r for r in runtime["runtimeAdmittedCards"]}
    return old, bank, catalog, cards, decks, policy, aliases, metadata, printings, admitted


def profile(deck, printings):
    counts = Counter()
    for entry in deck["deck"]:
        counts[json.dumps(strict_signature(printings[entry["id"]]), separators=(",", ":"))] += entry["count"]
    return dict(sorted(counts.items()))


def feasibility(out):
    started = time.monotonic()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    if (out / "feasibility.json").exists():
        raise ValueError("refuse overwriting frozen feasibility")
    old, bank, catalog, cards, decks, policy, aliases, metadata, printings, admitted = load()
    groups, exclusions, by_name = defaultdict(list), [], {}
    for code, row in sorted(printings.items()):
        card = row["card"]
        if code.split("_", 1)[0] not in policy["allowed_printed_sets"]:
            continue
        reasons = []
        if not set(card.get("types") or []) & {"unit", "event", "upgrade"} or set(card.get("types") or []) & {"leader", "base", "token"}:
            reasons.append("not an ordinary main-card type")
        if metadata.get(aliases.get(code)) is None:
            reasons.append("ambiguous/incomplete printed metadata")
        text = " ".join(str(card.get(k) or "") for k in ("text", "rules", "epicAction", "deployBox")).casefold()
        flagged = [word for word in CONSTRUCTION_TERMS if word in text]
        if flagged:
            reasons.append("unreviewed construction-related text: " + ",".join(flagged))
        descriptor = C.descriptor(row, admitted)
        if not descriptor["known"]:
            reasons.extend(descriptor["reasons"])
        if reasons:
            exclusions.append(dict(code=code, reasons=reasons)); continue
        name = C.F.name_key(card)
        if name in by_name:
            exclusions.append(dict(code=code, reasons=["reprint/name alias represented by lexicographically first printing"], representative=by_name[name])); continue
        by_name[name] = code
        groups[strict_signature(row)].append(dict(code=code, canonical_id=aliases[code], name_key=list(name),
            ir=descriptor, keywords=sorted(card.get("keywords") or []), runtime_admission=admitted[row["setCode"]]))
    distance_cache = {}
    def distance(a, b):
        key = tuple(sorted((a["code"], b["code"])))
        if key not in distance_cache:
            distance_cache[key] = C.ir_distance(a["ir"], b["ir"])
        return distance_cache[key]
    reports, possible = [], {source: [] for source in C.SOURCES}
    background_names = {source: {C.F.name_key(printings[e["id"]]["card"]) for e in decks[source]["deck"]} for source in C.SOURCES}
    for sig, members in sorted(groups.items(), key=lambda p: json.dumps(p[0])):
        members.sort(key=lambda m: m["code"])
        group_id = "strict-" + C.R.fingerprint({m["code"]: 1 for m in members})[:16]
        report = dict(id=group_id, signature=list(sig), members=[dict(code=m["code"], canonical_id=m["canonical_id"], keywords=m["keywords"], runtime_admission=m["runtime_admission"]) for m in members],
                      canonical_identities=len({m["canonical_id"] for m in members}), source_feasible_triples={}, reason=None)
        if len(members) < 3:
            report["reason"] = "fewer than3 distinct admitted canonical main identities"; reports.append(report); continue
        valid = []
        for a, near, far in itertools.permutations(members, 3):
            if len({a["canonical_id"], near["canonical_id"], far["canonical_id"]}) != 3:
                continue
            dn, df = distance(a, near), distance(a, far)
            if not dn["distance"] < df["distance"] - 1e-12:
                continue
            item = dict(group_id=group_id, a=a["code"], near=near["code"], far=far["code"],
                        canonical_ids=[a["canonical_id"], near["canonical_id"], far["canonical_id"]],
                        near_ir=dn, far_ir=df, exact_keywords=a["keywords"] == near["keywords"] == far["keywords"])
            valid.append((a, near, far, item))
        report["valid_ordered_triples"] = len(valid)
        if not valid:
            report["reason"] = "no strictly different anchor-to-alternative IR distances"
        for source in C.SOURCES:
            eligible = [item for a, near, far, item in valid if not {tuple(a["name_key"]), tuple(near["name_key"]), tuple(far["name_key"])} & background_names[source]]
            possible[source].extend(eligible)
            report["source_feasible_triples"][str(source)] = len(eligible)
        reports.append(report)
    for source in C.SOURCES:
        possible[source].sort(key=lambda v: (v["a"], v["near"], v["far"]))
    def assign(index, used):
        if index == len(C.SOURCES):
            return []
        source = C.SOURCES[index]
        for item in possible[source]:
            ids = set(item["canonical_ids"])
            if ids & used:
                continue
            tail = assign(index + 1, used | ids)
            if tail is not None:
                return [dict(source_index=source, **item)] + tail
        return None
    selected = assign(0, set())
    evidence = dict(schema="jepa-independent-module-feasibility/2", status="feasible" if selected else "insufficient-strict-modules", plan=plan(),
        source=C.pin(__file__), input_v1_manifest=C.pin(C.ROOT / "experiments/independent-controls/deck-controls.manifest.json"),
        protected_v1={str(p): C.sha(p) for p in (C.ROOT / "experiments/independent-controls").iterdir() if p.is_file()},
        pinned_inputs=old["sources"], groups=reports, exclusions=exclusions,
        counts=dict(unique_eligible_main_identities=len(by_name), strict_groups=len(reports), groups_with_at_least3=sum(r["canonical_identities"] >= 3 for r in reports),
                    groups_with_ir_contrast=sum(r.get("valid_ordered_triples", 0) > 0 for r in reports),
                    feasible_ordered_triples_by_source={str(s): len(v) for s,v in possible.items()}, disjoint_modules=len(selected or [])),
        selected_modules=selected or [], all_within_group_ir_distances=[dict(codes=list(k), **v) for k,v in sorted(distance_cache.items())],
        elapsed_seconds=time.monotonic()-started, model_forward_calls=0, neighbor_metrics=0, native_calls=0, optimizer_updates=0)
    C.write(out / "feasibility.json", evidence)
    C.write(out / "plan.json", plan())
    return evidence


def generate(out):
    started = time.monotonic(); out = Path(out)
    evidence = C.read(out / "feasibility.json")
    C.pin(__file__, evidence["source"]["sha256"])
    for path, expected in evidence["protected_v1"].items():
        C.pin(path, expected)
    if evidence["counts"]["disjoint_modules"] != 3:
        raise ValueError("no3-module admission; no pool relaxation")
    if (out / "combined-controls.manifest.json").exists():
        raise ValueError("refuse overwrite")
    old, bank, catalog, cards, decks, policy, aliases, metadata, printings, admitted = load()
    rows, features = [], []
    declarations = {r["source_index"]: r for r in bank["declarations"]}
    def append(deck, source, kind, identity, anchor_id, module, mechanical=None, dose=0):
        admission = C.F.eligibility(deck, printings, policy)
        if not admission["admitted"]:
            raise ValueError("synthetic control failed pinned declaration policy")
        counts = C.row_counts(deck, aliases)
        feature = C.R.O.as_array(C.R.O.encode_hello({"deck": deck, "cards": cards}))[0]
        if feature[0,3] != 1 or not np.array_equal(feature[1], C.R.O.neutral_features(1)[0,1]):
            raise ValueError("unknown printed metadata or remaining composition leak")
        row = dict(id=identity, source_index=source, family_id=declarations[source]["family_id"], kind=kind, assay="v2-synthetic", anchor_id=anchor_id,
            canonical_card_counts=counts, raw_declared_cards=deck["deck"], leader=deck["leader"], base=deck["base"], sideboard=[],
            composition_fingerprint=C.R.fingerprint(counts), lineage=dict(seed=SEED, source_card=module["a"], copies=dose, anchor_id=anchor_id,
                anchor_source="synthetic-module", background_source_index=source, module=module, inherited_partition="validation", stratum="strict-power-hp"),
            mechanical_labels=mechanical or dict(scope="synthetic anchor/invariance; no authored/quality label"), admission=admission,
            invariance_group=anchor_id if kind in ("module-anchor", "permutation", "split-entries") else None)
        rows.append(row); features.append(feature)
    for module in evidence["selected_modules"]:
        source = module["source_index"]; background = C.F.changed_deck(decks[source], [], [])
        copies = [e["id"] for e in sorted(background["deck"], key=lambda e:e["id"]) for _ in range(e["count"])]
        anchor = C.F.changed_deck(background, copies[:3], [module["a"]]*3)
        anchor_id = f"module-source-{source:02}-anchor"; anchor_index = len(rows)
        append(anchor, source, "module-anchor", anchor_id, anchor_id, module)
        rows[-1]["lineage"].update(removed_background_copies=copies[:3], added_module_copies=[module["a"]]*3, synthetic=True)
        anchor_counts = rows[-1]["canonical_card_counts"]
        for dose in (1,2):
            pair = []
            for kind, code, dist in (("ir-near", module["near"], module["near_ir"]), ("ir-far", module["far"], module["far_ir"])):
                deck = C.F.changed_deck(anchor, [module["a"]]*dose, [code]*dose)
                append(deck, source, kind, f"module-{source:02}-n{dose}-{kind}", anchor_id, module,
                    dict(label=kind, scope="IR-structural proxy ordering, not behavioral truth", ir_only=dist, exact_power_hp=True, strict_primary=True,
                         exact_keywords=sorted(printings[module["a"]]["card"].get("keywords") or []) == sorted(printings[code]["card"].get("keywords") or []),
                         printed_mechanics_unselected=C.printed_distance(C.printed_descriptor(printings[module["a"]]), C.printed_descriptor(printings[code]))), dose)
                rows[-1]["lineage"]["replacement_card"] = code
                rows[-1]["count_baseline"] = C.count_baseline(anchor_counts, rows[-1]["canonical_card_counts"])
                if profile(deck,printings) != profile(anchor,printings):
                    raise ValueError("strict full-deck profile mismatch")
                pair.append(rows[-1])
            if pair[0]["count_baseline"] != pair[1]["count_baseline"]:
                raise ValueError("near/far count confound")
        for kind in ("permutation", "split-entries"):
            variant = copy.deepcopy(anchor)
            if kind == "permutation":
                np.random.default_rng(SEED+source).shuffle(variant["deck"])
            else:
                variant["deck"] = [dict(id=e["id"],count=1) for e in reversed(anchor["deck"]) for _ in range(e["count"])]
            append(variant,source,kind,f"module-{source:02}-{kind}",anchor_id,module)
            if rows[-1]["canonical_card_counts"] != anchor_counts or not np.array_equal(features[-1],features[anchor_index]):
                raise ValueError("synthetic invariance failed")
    if len(rows) != 21:
        raise ValueError("expected21 new rows")
    def save(path, bank_features, bank_rows):
        np.savez_compressed(path,deck_features=np.asarray(bank_features,np.float32),row_ids=np.asarray([r["id"] for r in bank_rows],str),source_indices=np.asarray([r["source_index"] for r in bank_rows],np.int64))
    save(out / "module-controls.npz",features,rows)
    with np.load(old["artifact"]["path"],allow_pickle=False) as pack:
        previous_features = pack["deck_features"].copy()
    previous_rows = copy.deepcopy(old["rows"])
    for row in previous_rows:
        row["assay"] = "v1-authored"; row["anchor_id"] = f"independent-source-{row['source_index']:02}"
        row["lineage"]["anchor_id"] = row["anchor_id"]; row["lineage"]["anchor_source"] = "authored-original"
    combined_rows = previous_rows + rows; combined_features=np.concatenate([previous_features,np.stack(features)])
    if len(combined_rows)>40:
        raise ValueError("combined control cap exceeded")
    save(out / "combined-controls.npz",combined_features,combined_rows)
    for path,expected in evidence["protected_v1"].items():
        C.pin(path,expected)
    manifest=dict(schema="jepa-independent-combined-controls/2",status="prepared-awaiting-root-go",artifact=C.pin(out/"combined-controls.npz"),rows=combined_rows,
        module_artifact=C.pin(out/"module-controls.npz"),feasibility=C.pin(out/"feasibility.json"),source=C.pin(__file__),sources=old["sources"],
        anchor_indices=old["anchor_indices"],synthetic_anchor_indices=[len(previous_rows)+i for i,r in enumerate(rows) if r["kind"]=="module-anchor"],
        v1=dict(manifest=C.pin(C.ROOT/"experiments/independent-controls/deck-controls.manifest.json"),rows=len(previous_rows),minimum_family_support_satisfied=False,strict_primary_satisfied=False),
        v2=dict(assay="synthetic conditional mechanics proxy",modules=3,background_families=3,rows=21,modified_rows=12,strict_power_hp=True,keyword_exact_modules=sum(m["exact_keywords"] for m in evidence["selected_modules"])),
        counts=dict(rows=len(combined_rows),unique_source_compositions=len({(r["source_index"],r["composition_fingerprint"]) for r in combined_rows}),unique_feature_rows=len({v.tobytes() for v in combined_features})),
        model_forward_calls=0,neighbor_metrics=0,native_calls=0,optimizer_updates=0,preparation_elapsed_seconds=time.monotonic()-started,
        limitations=C.LIMITATIONS+["V2 anchors are synthetic planted modules; this does not rescue the failed v1 authored-deck primary criterion. Exact-profile AST-proxy order is not strategic quality or validated behavior."])
    C.write(out/"combined-controls.manifest.json",manifest)
    return manifest


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("phase",choices=("feasibility","generate"));parser.add_argument("--out",type=Path,default=OUT);args=parser.parse_args()
    result=feasibility(args.out) if args.phase=="feasibility" else generate(args.out)
    print(json.dumps(result.get("counts",{}),indent=2))
