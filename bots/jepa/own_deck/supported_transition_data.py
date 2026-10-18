"""Pinned existing-runtime transition bank; labels come only from native receipts.

Planning scans typed parser support independently of whole-card runtime admission.
The bounded pilot retains two already verified leader bindings, groups all cards
and branches by context family, and makes no held-out-card or strength claim.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import typed_ir_alignment as T

SCHEMA = "jepa-supported-transition-data/1"
NATIVE_SCHEMA = "jepa-supported-native-transitions/1"
SELECTED = ("ASH_011", "IBH_053")
TARGET_NAMES = ("source_use", "target_allowed", "cost_resource", "damage_delta", "source_exhausted_after", "followup_source_offered", "terminal")
CONTEXT_FEATURE_NAMES = ("ready_resources", "physical_resources", "source_exhausted", "source_deployed",
                         "chosen_own", "chosen_unit", "chosen_base", "chosen_ground", "chosen_space",
                         "chosen_hp_per30", "chosen_damage_per30", "chosen_remaining_hp_per30", "chosen_shields",
                         "own_base_damage_per30", "opponent_base_damage_per30", "own_ground_count", "opponent_ground_count",
                         "own_space_count", "opponent_space_count")
CONTEXT_FAMILIES = (
    dict(id=0, name="baseline", resource_ready=True, source_exhausted=False, first_owner="p2", first_damage=2, second_damage=3, own_base_damage=0, opponent_base_damage=0),
    dict(id=1, name="no-ready-resource", resource_ready=False, source_exhausted=False, first_owner="p2", first_damage=2, second_damage=3, own_base_damage=0, opponent_base_damage=0),
    dict(id=2, name="source-exhausted", resource_ready=True, source_exhausted=True, first_owner="p2", first_damage=2, second_damage=3, own_base_damage=0, opponent_base_damage=0),
    dict(id=3, name="invalid-chosen-target", resource_ready=True, source_exhausted=False, first_owner="p2", first_damage=3, second_damage=2, own_base_damage=0, opponent_base_damage=0),
    dict(id=4, name="friendly-terminal-train", resource_ready=True, source_exhausted=False, first_owner="p1", first_damage=0, second_damage=3, own_base_damage=29, opponent_base_damage=0),
    dict(id=5, name="near-terminal", resource_ready=True, source_exhausted=False, first_owner="p2", first_damage=2, second_damage=3, own_base_damage=0, opponent_base_damage=29),
    dict(id=6, name="resource-and-invalid-target", resource_ready=False, source_exhausted=False, first_owner="p2", first_damage=3, second_damage=2, own_base_damage=0, opponent_base_damage=0),
    dict(id=7, name="exhausted-and-friendly", resource_ready=True, source_exhausted=True, first_owner="p1", first_damage=1, second_damage=3, own_base_damage=2, opponent_base_damage=0),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def scan_catalog(catalog, admission):
    admitted = {r["setCode"]: r for r in admission["runtimeAdmittedCards"]}
    rejected = {r["setCode"]: r for r in admission["runtimeRejectedCards"]}
    parseable, failures = [], Counter()
    for row in catalog["cards"]:
        for side, abilities in (row.get("abilities") or {}).items():
            if not isinstance(abilities, list):
                failures[(side, "ability side is not an ordered list")] += 1
                continue
            for index, raw in enumerate(abilities):
                try:
                    program = T.ability(raw)
                except (T.UnknownIR, KeyError, TypeError) as exc:
                    failures[(side, str(exc))] += 1
                    continue
                parseable.append(dict(card=row["setCode"], ability_path=["abilities", side, index],
                                      whole_card_runtime_admitted=row["setCode"] in admitted,
                                      runtime_admission=admitted.get(row["setCode"], rejected.get(row["setCode"], {"reason": "not in admission report"})),
                                      program=program, raw_ability=copy.deepcopy(raw), sourceHash=row.get("sourceHash"), sourcePath=row.get("sourcePath"),
                                      card_row_sha256=fingerprint(row)))
    return dict(parseable_selected_abilities=parseable,
                parser_rejections=[dict(side=side, reason=reason, count=count) for (side, reason), count in sorted(failures.items())],
                parser_parseable_count=len(parseable), runtime_admitted_parseable_count=sum(r["whole_card_runtime_admitted"] for r in parseable))


def make_plan(catalog, admission):
    scan = scan_catalog(catalog, admission)
    programs = {}
    for code in SELECTED:
        matches = [p for p in scan["parseable_selected_abilities"] if p["card"] == code and p["ability_path"] == ["abilities", "leader", 0]]
        if len(matches) != 1 or not matches[0]["whole_card_runtime_admitted"]:
            raise ValueError("selected exact whole-card/ability admission failed: " + code)
        row = next(r for r in catalog["cards"] if r["setCode"] == code)
        if len(row["abilities"]["leader"]) != 1:
            raise ValueError("selected source has an unreviewed ability selection menu")
        programs[code] = {**matches[0], "canonical_card_id": str(row["card"]["id"]),
                          "identity_aliases": row["card"].get("setCodes", []),
                          "complete_definition_preserved": True,
                          "all_side_ability_counts": {k: len(v) for k, v in row["abilities"].items()}}
    not_selected = []
    for p in scan["parseable_selected_abilities"]:
        if p["card"] in SELECTED:
            continue
        not_selected.append({**{k: v for k, v in p.items() if k not in ("program", "raw_ability")},
                             "reason": "whole-card runtime rejected despite parseable selected ability" if not p["whole_card_runtime_admitted"] else
                                       "unit/card source-form action binding outside the existing verified leader microprobe; no runtime primitive expansion required"})
    return dict(schema=SCHEMA, status="planned-native-labels-not-collected", sourceRevision=T.PINNED_KESSEL_COMMIT,
                maximum_card_goal=8, selected_card_count=len(programs), maximum_is_not_an_admission_gate=True,
                programs=programs, coverage_scan=scan, excluded_selected_abilities=not_selected,
                complete_runtime_definition_codes=[*SELECTED, "ASH_019", "LOF_256", "TOKEN_SHIELD"],
                native_token_exception="Exact unmodified TOKEN_SHIELD row remains compiler-unsupported and is admitted by the existing native token adapter.",
                context_families=list(CONTEXT_FAMILIES), context_feature_names=list(CONTEXT_FEATURE_NAMES), target_names=list(TARGET_NAMES),
                context_feature_units=["count", "count", "boolean", "boolean", "boolean", "boolean", "boolean", "boolean", "boolean",
                                       "HP/30", "damage/30", "remaining HP/30", "count", "damage/30", "damage/30", "count", "count", "count", "count"],
                prediction_time="Pre-action source-use query with a predeclared chosen public reference; no native offered mask or later state is an input.",
                target_units=["boolean", "boolean", "copies of ready resources paid", "damage counters after minus before", "boolean", "boolean", "boolean"],
                target_normalization=[1.] * len(TARGET_NAMES),
                target_semantics=dict(source_use="source appears in native initial offered actions",
                                      target_allowed="chosen reference appears in actual native target prompt; unknown when source cannot enter prompt",
                                      cost_resource="before ready count minus committed after ready count",
                                      damage_delta="chosen after damage minus before damage, including settled terminal commit",
                                      source_exhausted_after="committed after source exhaustion",
                                      followup_source_offered="actual subsequent own window offers source, unknown when terminal/no follow-up",
                                      terminal="native settled committed state terminal status"),
                split=dict(train_context_families=[0, 1, 2, 3, 4], val_context_families=[5, 6, 7],
                           rule="Group both card identities and all source/cancel/commit/follow-up branches by full context family; no row-random split.",
                           held_out_card_ids=False, reprints_kept_with_canonical_identity=True),
                collection=dict(max_context_cases=16, max_engine_applies_including_failures=64, parent_total_apply_ceiling=96,
                                current_contexts_also_query_native_exhaustion_resource_and_target_boundaries=True,
                                label_source="Engine::legal_actions and observed native snapshots only; no labels from typed parser, structural overlap or synthetic_transition"),
                inputs=dict(only_pre_action_public_scalars=True, actual_offered_masks_are_targets_not_inputs=True,
                            card_titles_source_paths_instance_ids_and_context_ids_model_inputs=False,
                            hidden_draw_order_or_opponent_private_inputs=False),
                target_mask_scope="The learned target_allowed coordinate is one predeclared chosen-reference boolean; complete native candidate masks are preserved in raw records, not claimed as a learned full-mask head.",
                capability_bag=dict(scope="One-count selected source program is a synthetic capability bag, not an original deck declaration; no deck-synergy evidence.",
                                    count_order_invariant=True),
                limitations=["Two familiar IDs occur in both partitions: held-out-context diagnostic only, not held-out-card semantics.",
                             "With two IDs, ID-only and fixed wrong-IR controls may memorize or invert the program mapping.",
                             "Friendly terminal and enemy terminal contexts are predeclared in train and validation respectively; this remains a very small context bank.",
                             "Runtime admission and typed selected-ability coverage are distinct; no unsupported card side is removed.",
                             "No game, seven-loss reproduction, policy strength or paid job is part of this data preparation."])


def source_plan(kessel):
    kessel = Path(kessel)
    head = subprocess.check_output(["git", "--no-optional-locks", "-C", str(kessel), "rev-parse", "HEAD"], text=True).strip()
    if head != T.PINNED_KESSEL_COMMIT:
        raise ValueError("Kessel source commit changed")
    subprocess.run(["git", "--no-optional-locks", "-C", str(kessel), "diff", "--quiet", "HEAD", "--", "crates/kessel", "compiler/generated", "Cargo.toml", "Cargo.lock"], check=True)
    generated = kessel / "compiler/generated"
    plan = make_plan(json.loads((generated / "cards.json").read_text()), json.loads((generated / "runtime-admission.json").read_text()))
    paths = [generated / "cards.json", generated / "runtime-admission.json", generated / "manifest.json", HERE / "typed_ir_alignment.py", Path(__file__)]
    for relative in ("Cargo.toml", "Cargo.lock", "crates/kessel/src/lib.rs", "crates/kessel/src/model.rs", "crates/kessel/src/generic_runtime.rs"):
        paths.append(kessel / relative)
    plan["sources"] = [dict(path=str(p), sha256=sha(p)) for p in paths]
    return plan


def public_card(snapshot, identity):
    matches = []
    for seat in ("p1", "p2"):
        p = snapshot["players"][seat]
        for zone, cards in (("base", [p["base"]]), ("leader", [p["leader"]]), ("ground", p["ground"]), ("space", p["space"])):
            matches.extend((seat, zone, c) for c in cards if c["id"] == identity)
    if len(matches) != 1:
        raise ValueError("public reference must resolve once")
    return matches[0]


def context_features(case):
    """Only the pre-action public view enters these fixed named coordinates."""
    state = case["before"]["state"]
    refs = case["refs"]
    source_seat, source_zone, source = public_card(state, refs["source"])
    chosen_seat, chosen_zone, chosen = public_card(state, refs["chosen"])
    if source_seat != "p1" or source_zone != "leader" or source["deployed"]:
        raise ValueError("only reviewed undeployed own leader source forms")
    own, opponent = state["players"]["p1"], state["players"]["p2"]
    values = [sum(not c["exhausted"] for c in own["resources"]), len(own["resources"]), source["exhausted"], source["deployed"],
              chosen_seat == "p1", chosen_zone in ("ground", "space"), chosen_zone == "base", chosen_zone == "ground", chosen_zone == "space",
              chosen["hp"] / 30, chosen["damage"] / 30, (chosen["hp"] - chosen["damage"]) / 30,
              sum(c["setCode"] == "TOKEN_SHIELD" for c in chosen["upgrades"]) if chosen_zone in ("ground", "space") else 0,
              own["base"]["damage"] / 30, opponent["base"]["damage"] / 30,
              len(own["ground"]), len(opponent["ground"]), len(own["space"]), len(opponent["space"])]
    features = np.asarray(values, np.float32)
    if features.shape != (len(CONTEXT_FEATURE_NAMES),) or not np.isfinite(features).all():
        raise ValueError("invalid public scalar context")
    return features


def convert_receipt(receipt, plan):
    if receipt.get("schema") != NATIVE_SCHEMA or receipt.get("sourceRevision") != plan["sourceRevision"]:
        raise ValueError("native receipt source/schema mismatch")
    if type(receipt.get("applyCalls")) is not int or not 0 <= receipt["applyCalls"] <= plan["collection"]["max_engine_applies_including_failures"]:
        raise ValueError("native apply accounting outside fixed allocation")
    if set(receipt.get("selectedWholeCards", [])) != set(plan["complete_runtime_definition_codes"]):
        raise ValueError("native whole-card selection differs from reviewed plan")
    if not isinstance(receipt.get("selectedCatalogueSha256"), str) or len(receipt["selectedCatalogueSha256"]) != 64:
        raise ValueError("missing exact native selected catalogue hash")
    provenance = receipt.get("provenance", [])
    for code, program in plan["programs"].items():
        rows = [r for r in provenance if r.get("card") == code]
        if len(rows) != 1 or rows[0].get("sourceHash") != program["sourceHash"] or rows[0].get("sourcePath") != program["sourcePath"] or rows[0].get("abilityPath") != program["ability_path"] or rows[0].get("actualUnmodifiedAbility") != program["raw_ability"]:
            raise ValueError("native exact selected-program provenance differs: " + code)
    cases = sorted(receipt["cases"], key=lambda c: (c["card"], c["context_family"]))
    expected = {(code, i) for code in SELECTED for i in range(len(CONTEXT_FAMILIES))}
    if len(cases) != len(expected) or {(c["card"], c["context_family"]) for c in cases} != expected:
        raise ValueError("expected exact fixed card/context bank without duplicate or missing rows")
    contexts, targets, masks, records = [], [], [], []
    for case in cases:
        program = plan["programs"][case["card"]]
        if case["abilityPath"] != program["ability_path"]:
            raise ValueError("native source/program path changed")
        source = public_card(case["before"]["state"], case["refs"]["source"])[2]
        if source["setCode"] != case["card"]:
            raise ValueError("source card identity differs from binding witness")
        offered_before = case["before"]["offeredActions"]
        observed_source = any(a.get("kind") == "card" and a.get("card") == case["refs"]["source"] for a in offered_before)
        if not case["target_mask"].get("source_use") or case["targets"].get("source_use") != observed_source:
            raise ValueError("native source-use label differs from actual initial offers")
        prompt = case.get("targetPrompt")
        if prompt is not None:
            if case.get("sourceAction") not in offered_before:
                raise ValueError("source action is not an exact native offered tuple")
            allowed = any(a.get("kind") == "card" and a.get("card") == case["refs"]["chosen"] for a in prompt["offeredActions"])
            if not case["target_mask"].get("target_allowed") or case["targets"].get("target_allowed") != allowed:
                raise ValueError("target label differs from actual native prompt")
        elif case["target_mask"].get("target_allowed"):
            raise ValueError("unobserved native target prompt must remain unknown")
        after = case.get("after")
        committed_names = ("cost_resource", "damage_delta", "source_exhausted_after", "terminal")
        if after is None and any(case["target_mask"].get(k) for k in committed_names):
            raise ValueError("uncommitted native outcomes must remain unknown")
        if after is not None:
            if prompt is None or case.get("targetAction") not in prompt["offeredActions"]:
                raise ValueError("committed target is not an exact offered tuple")
            before_state, after_state = case["before"]["state"], after["state"]
            after_source = public_card(after_state, case["refs"]["source"])[2]
            before_chosen = public_card(before_state, case["refs"]["chosen"])[2]
            after_chosen = public_card(after_state, case["refs"]["chosen"])[2]
            ready = lambda state: sum(not c["exhausted"] for c in state["players"]["p1"]["resources"])
            observed = dict(cost_resource=ready(before_state) - ready(after_state), damage_delta=after_chosen["damage"] - before_chosen["damage"],
                            source_exhausted_after=after_source["exhausted"], terminal=after["terminal"])
            for name, value in observed.items():
                if not case["target_mask"].get(name) or case["targets"].get(name) != value:
                    raise ValueError("native committed label differs from snapshot: " + name)
        following = case.get("following")
        if following is None and case["target_mask"].get("followup_source_offered"):
            raise ValueError("unobserved native follow-up must remain unknown")
        if following is not None:
            offered = any(a.get("kind") == "card" and a.get("card") == case["refs"]["source"] for a in following["offeredActions"])
            if not case["target_mask"].get("followup_source_offered") or case["targets"].get("followup_source_offered") != offered:
                raise ValueError("native follow-up label differs from observed offers")
        if set(case["targets"]) != set(TARGET_NAMES) or set(case["target_mask"]) != set(TARGET_NAMES):
            raise ValueError("unknown or missing target coordinates")
        vector, mask, unknown = [], [], []
        for name in TARGET_NAMES:
            known, value = case["target_mask"][name], case["targets"][name]
            if type(known) not in (bool, int) or known not in (False, True, 0, 1):
                raise ValueError("target mask must be explicit boolean")
            if known:
                if type(value) not in (bool, int, float) or not math.isfinite(value):
                    raise ValueError("known native target must be finite")
                if name not in ("cost_resource", "damage_delta") and value not in (0, 1):
                    raise ValueError("native boolean target outside 0/1")
                vector.append(float(value))
            else:
                # Explicit masked placeholder, never an invented observed zero.
                vector.append(0.)
                unknown.append(name)
            mask.append(float(known))
        contexts.append(context_features(case)); targets.append(vector); masks.append(mask)
        records.append(dict(source_card=case["card"], context_family=case["context_family"],
                            fingerprint=fingerprint(dict(card=case["card"], context=contexts[-1].tolist())),
                            context_fingerprint=fingerprint(contexts[-1].tolist()), unknown_targets=unknown,
                            raw_native_case=case))
    families = np.asarray([c["context_family"] for c in cases], np.int64)
    source_cards = np.asarray([c["card"] for c in cases], dtype=str)
    counts = np.zeros((len(cases), len(SELECTED)), np.float32)
    for i, code in enumerate(source_cards):
        counts[i, SELECTED.index(code)] = 1.
    arrays = dict(context_features=np.stack(contexts), targets=np.asarray(targets, np.float32), target_mask=np.asarray(masks, np.float32),
                  source_cards=source_cards, context_groups=families, fingerprints=np.asarray([r["fingerprint"] for r in records], dtype=str),
                  context_fingerprints=np.asarray([r["context_fingerprint"] for r in records], dtype=str), deck_counts=counts,
                  train_idx=np.flatnonzero(families < 5).astype(np.int64), val_idx=np.flatnonzero(families >= 5).astype(np.int64))
    if set(arrays["context_fingerprints"][arrays["train_idx"]]) & set(arrays["context_fingerprints"][arrays["val_idx"]]):
        raise ValueError("identical public scalar contexts cross family holdout")
    manifest = {**copy.deepcopy(plan), "status": "native-labels-collected", "records": records,
                "native_apply_calls": receipt["applyCalls"], "native_receipt_schema": receipt["schema"],
                "selected_catalogue_sha256": receipt["selectedCatalogueSha256"],
                "train_rows": len(arrays["train_idx"]), "val_rows": len(arrays["val_idx"]),
                "unknown_target_payload": "0 is only a masked placeholder when target_mask=0; unknown coordinates must be excluded from losses/metrics.",
                "target_variation": {name: {part: sorted(set(arrays["targets"][idx, j][arrays["target_mask"][idx, j].astype(bool)].tolist()))
                                           for part, idx in (("train", arrays["train_idx"]), ("val", arrays["val_idx"]))}
                                     for j, name in enumerate(TARGET_NAMES)},
                "target_known_support": {name: {part: int(arrays["target_mask"][idx, j].sum()) for part, idx in (("train", arrays["train_idx"]), ("val", arrays["val_idx"]))} for j, name in enumerate(TARGET_NAMES)}}
    return arrays, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kessel-dir", type=Path, default=T.PINNED_SOURCE)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path)
    args = parser.parse_args()
    plan = source_plan(args.kessel_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = args.out_dir / "supported-transition-plan.json"
    if args.native_receipt is None:
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        print(json.dumps(dict(plan=str(plan_path), sha256=sha(plan_path), selected=list(SELECTED), labels_collected=False)))
        return
    arrays, manifest = convert_receipt(json.loads(args.native_receipt.read_text()), plan)
    dataset = args.out_dir / "supported-transitions.npz"
    np.savez_compressed(dataset, **arrays)
    manifest["native_receipt"] = dict(path=str(args.native_receipt), sha256=sha(args.native_receipt))
    manifest["artifact"] = dict(path=str(dataset), sha256=sha(dataset), arrays={k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in arrays.items()})
    output = args.out_dir / "supported-transitions.manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(dataset=str(dataset), manifest=str(output), sha256=sha(dataset), train=manifest["train_rows"], val=manifest["val_rows"], native_applies=manifest["native_apply_calls"])))


if __name__ == "__main__":
    main()
