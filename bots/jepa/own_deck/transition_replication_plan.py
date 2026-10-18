"""Prepare an independent, overlapping-target replication; no native/NN execution.

The original dataset, collector and fitted artifacts remain byte-pinned. The
shared receipt validator is loaded into a private module namespace so that this
plan's declared identities/state recipe cannot change the original contract.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grounded_contrast_data as G
import grounded_contrast_model as M

EXPERIMENTS = Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments")
ORIGINAL = EXPERIMENTS / "grounded-contrast"
HELDOUT_CODES = ("SHD_004", "TWI_206")
TRAIN_CODES = G.TRAIN_CODES
CORE_CODES = (*TRAIN_CODES, *HELDOUT_CODES)
NEW_NATIVE_SCHEMA = "jepa-transition-replication-native/1"


def configured_contract():
    """Isolated shared validator; original module/constants are never mutated."""
    spec = importlib.util.spec_from_file_location("_replication_frozen_data_contract", HERE / "grounded_contrast_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CORE_CODES = CORE_CODES
    module.TRAIN_CODES = TRAIN_CODES
    module.HELDOUT_CODES = HELDOUT_CODES
    states = copy.deepcopy(module.STATE_FAMILIES)
    states[12]["name"] = "held-space-damaged-ready-resources"
    states[12]["overrides"]["ready_resources"] = 2
    module.STATE_FAMILIES = states
    return module


def vocabulary_coverage(records, contract):
    symbols = contract["vocabularies"]
    result = {}
    for record in records:
        tokens = M.structural_tokens(record["raw_ability"])
        paths = {("index:" if type(k) is int else "key:") + str(k) for path, _, _ in tokens for k in path}
        values = {"NUMBER" if kind in ("number", "length") else kind + ":" + str(value) for _, kind, value in tokens}
        missing = dict(path=sorted(paths - set(symbols["path"])), value=sorted(values - set(symbols["value"])))
        if any(missing.values()):
            raise ValueError("replication would change the fixed architecture vocabulary: " + record["code"])
        result[record["code"]] = dict(tokens=len(tokens), missing=missing)
    return result


def make_plan(catalog, runtime, original_manifest, original_contract):
    base = configured_contract()
    report = base.inventory(catalog, runtime)
    split = base.split_plan(report)
    if tuple(original_manifest["identity_program_split"]["train_codes"]) != TRAIN_CODES:
        raise ValueError("original ten training programs changed")
    old_programs = original_manifest["programs"]
    records = {p["code"]: p for p in split["programs"]}
    for code in TRAIN_CODES:
        if records[code] != old_programs[code]:
            raise ValueError("replication changed a retained training program: " + code)
    if set(HELDOUT_CODES) & set(old_programs):
        raise ValueError("fresh held identity appeared in original collection")
    old_groups = {p["program_group_id"] for p in old_programs.values()}
    old_aliases = {a for p in old_programs.values() for a in p["aliases"]}
    old_ids = {p["canonical_card_id"] for p in old_programs.values()}
    for code in HELDOUT_CODES:
        p = records[code]
        if p["program_group_id"] in old_groups or p["canonical_card_id"] in old_ids or set(p["aliases"]) & old_aliases:
            raise ValueError("fresh identity/program/reprint group appeared in original collection")
        if p["index"] != 0 or p["all_side_ability_counts"][p["side"]] != 1:
            raise ValueError("fresh active-side public menu binding is ambiguous")
    contract_vocab = vocabulary_coverage(split["programs"], original_contract)
    run_matrix = [dict(dataset=dataset, seed=seed, action="fit" if dataset == "original" else "evaluate-only",
                       arms=list(M.CONTRAST_ARMS), updates_per_arm=600 if dataset == "original" else 0,
                       updates=2400 if dataset == "original" else 0,
                       reuse_original_dataset_checkpoint=dataset == "fresh")
                  for dataset, seeds in (("original", (29, 43)), ("fresh", (17, 29, 43))) for seed in seeds]
    contexts = []
    for state in base.STATE_FAMILIES:
        override = state["overrides"]
        contexts.append(dict(id=state["id"], name=state["name"], partition="train" if state["id"] < 10 else "state-holdout",
                             ready_resources=override.get("ready_resources", 2), source_exhausted=override.get("source", {}).get("exhausted", False),
                             overrides={k: v for k, v in override.items() if k not in ("ready_resources", "source")}))
    return dict(schema="jepa-transition-replication-plan/1", status="prepared-not-authorized-for-execution",
                source_revision=G.REVISION, train_codes=list(TRAIN_CODES), heldout_codes=list(HELDOUT_CODES),
                train_state_families=list(range(10)), heldout_state_families=list(range(10, 14)),
                programs=split["programs"], identity_program_split=split, numeric_contract=base.numeric_contract(), contexts=contexts,
                prior_unexecuted_action_inventory=report["runtime_admitted_action_abilities"] - len(old_programs),
                original_training_programs_identical=True, fresh_id_program_alias_overlap_with_prior=0,
                vocabulary_coverage=contract_vocab, frozen_vocabulary_sha256=original_contract["vocabulary_sha256"],
                architecture=dict(parameters=9020, hidden=16, vocabularies={k: len(v) for k, v in original_contract["vocabularies"].items()}, changes=False),
                shared_validator=dict(path=str(HERE / "grounded_contrast_data.py"), sha256=G.sha(HERE / "grounded_contrast_data.py"),
                                      private_namespace=True, original_module_globals_modified=False,
                                      adapter_changes=["declared two fresh held identities", "state12 ready-resource count0 becomes2 for fresh dataset only", "native receipt schema envelope"]),
                primary_overlap_witness=dict(status="predeclared-context-and-program-evidence-not-native-outcome-labels",
                    candidate_roles=["friendly_ground", "enemy_ground"], whole_helper="LOF_256", public_power=1, public_hp=4,
                    SHD_004=dict(ability_path=["abilities", "leader", 0], resources=1, effect="giveExperience(chosen,1)", target="any unit with power<=2"),
                    TWI_206=dict(ability_path=["abilities", "card", 0], resources=2, effect="exhaust(chosen)", target="any unit with power<=4"),
                    independent_labels_required="Both targets must actually be offered and separately committed from untouched native prompts. Never label from this overlap description.",
                    primary_head_comparisons=["target_allowed", "cost_resource", "target_exhausted_delta", "xp_delta"],
                    four_effect_state_intent="Fresh held states10..13 all have ready resources>=2 and ready source. Validate actual common candidate commits in all four after collection; do not fabricate missing support."),
                primary_paired_metric=dict(name="held-program same-target contrast MAE", partition="joint-held",
                    orientation="SHD_004 minus TWI_206", heads=["cost_resource", "xp_delta", "target_exhausted_delta"],
                    eligibility="Same held state family and same primary helper/base candidate slot; both actual target prompts offer that exact reference; both independent commits settle; both native head masks known.",
                    value="abs((prediction_SHD004-prediction_TWI206)-(native_SHD004-native_TWI206)); mean over admitted state/candidate pairs per head, natural units.",
                    aggregation="Report each head MAE/support and train-scale-normalized macro separately. Pair branches correlate within four state roots; no independent-sample confidence claim.",
                    secondary="Retain all original four-cell/per-head metrics, constant-head flags, invalid candidate memberships and source-negative support. Do not select new seeds/heads after seeing results."),
                replication_design=dict(run_matrix=run_matrix, new_updates_max=sum(r["updates"] for r in run_matrix),
                    historical_seed17_original="Reuse existing saved result as historical reference only; do not count as fresh independent replicate.",
                    matched_arms=list(M.CONTRAST_ARMS), updates_per_fit_arm=600, fresh_evaluation_forwards=12, no_hyperparameter_selection=True,
                    selection_rule="Same frozen architecture/config, train-only scaling/class balance, deterministic per-seed schedules and matched controls. No reusing saved trained weights as initialization.",
                    fresh_dataset_independence="Fresh program identity groups and one predeclared held-state recipe change; ten training programs and most public states are shared deliberately. This is not an independent training-world sample.",
                    mandatory_reuse_gate="Before any fresh evaluation, prove canonical bit-exact equality of all100 training input/label/mask rows including all8candidates, full training programs by code, effective input/head/literal scaling, fixed vocabulary and encoded training bank by code. Stop on mismatch; no adaptation or fresh retraining.",
                    prelaunch_superseded_proposal=dict(path=str(EXPERIMENTS / "transition-replication/replication-plan.proposal-12000.prelaunch.json"), sha256="28b5a0bc73b1c0b6c04518756de1adc3af18a49b3265b47a734b85d63b914916", executed=False)),
                proposed_campaign_limits=dict(native_applies=2048, collection_fit_active_seconds=240, optimizer_updates=4800,
                    cpu_workers=1, sampled_rss_stop_bytes=2147483648, paid_jobs=0, paid_spend_usd=0, requires_root_go=True),
                native_masks_settlement_and_error_policy="Reuse strict observed native masks, settlement witnesses and journal accounting; no final labels on unresolved/error branches. Source once/root; primary slots0..6, source-self auxiliary0.1.",
                limitations=["Threshold4 is a new numeric literal and positioned composition although all vocabulary symbols and primitives are familiar.",
                    "Fixed helper powers1/3/5 do not distinguish threshold4 from threshold3. No exact-threshold4 generalization claim is supported.",
                    "XP effects and exhaustion/cost differ on overlapping targets; this is not a direct damage-quantity replication.",
                    "All four fresh joint effect states intend source availability; source-use can be constant positive in the joint cell. Training retains source-exhausted and no-resource negative families.",
                    "Candidate branches are correlated within card/state roots. Report root, candidate and per-head support separately.",
                    "No gameplay, real authored-deck synergy, policy-strength or semantic-neighbor validation follows from this auxiliary prediction task."],
                model_forwards=0, optimizer_updates=0, native_applies=0)


TRAIN_TENSORS = ("context_features", "candidate_features", "candidate_mask", "primary_candidate_mask", "source_diagnostic_mask",
                 "source_use", "source_use_mask", "candidate_allowed", "candidate_allowed_mask", "targets", "target_mask")


def tensor_hash(array):
    array = np.ascontiguousarray(array)
    header = json.dumps(dict(dtype=array.dtype.str, shape=list(array.shape)), sort_keys=True).encode()
    return hashlib.sha256(header + b"\0" + array.tobytes()).hexdigest()


def training_equivalence(original, fresh, original_manifest, fresh_manifest, original_contract):
    """Fail closed on exact training-content/scaling/bank mismatch; NumPy only."""
    def canonical_indices(arrays):
        idx = np.asarray(arrays["train_idx"])
        if idx.dtype != np.int64 or len(idx) != 100 or len(set(idx.tolist())) != 100:
            raise ValueError("exact100 distinct training roots required")
        keyed = [(str(arrays["source_cards"][i]), int(arrays["state_families"][i]), int(i)) for i in idx]
        if {(c, f) for c, f, _ in keyed} != {(c, f) for c in TRAIN_CODES for f in range(10)}:
            raise ValueError("training root identities/families differ")
        keyed.sort(key=lambda row: (row[1], row[0]))
        return np.asarray([row[2] for row in keyed], np.int64), [(c, f) for c, f, _ in keyed]
    old_idx, old_keys = canonical_indices(original)
    new_idx, new_keys = canonical_indices(fresh)
    if old_keys != new_keys:
        raise ValueError("canonical training root keys differ")
    hashes = {}
    for name in TRAIN_TENSORS:
        a, b = np.asarray(original[name])[old_idx], np.asarray(fresh[name])[new_idx]
        if a.dtype != b.dtype or a.shape != b.shape or a.tobytes() != b.tobytes():
            raise ValueError("bit-exact training tensor differs: " + name)
        hashes[name] = tensor_hash(a)
    for name in ("context_feature_names", "candidate_feature_names", "target_names", "context_feature_units", "candidate_feature_units", "target_units"):
        if original_manifest[name] != fresh_manifest[name]:
            raise ValueError("ordered tensor contract differs: " + name)
    for code in TRAIN_CODES:
        if original_manifest["programs"][code] != fresh_manifest["programs"][code]:
            raise ValueError("full training program differs by code: " + code)
    def fitted(arrays, manifest, idx):
        records = [dict(manifest["programs"][code], code=code) for code in sorted(manifest["programs"])]
        vocabulary_coverage(records, original_contract)
        input_scale = M.fit_input_scaling(arrays["context_features"], arrays["candidate_features"], idx, arrays["primary_candidate_mask"])
        input_scale.pop("fit_rows")  # Full168row positions differ; canonical rows above are exact.
        head_scale = M.fit_head_scaling(arrays["source_use"], arrays["source_use_mask"], arrays["candidate_allowed"], arrays["candidate_allowed_mask"], arrays["targets"], arrays["target_mask"], idx, arrays["primary_candidate_mask"])
        literal_scale = M.fit_numeric_scale(records, list(TRAIN_CODES))
        codes, bank = M.encode_program_bank(records, original_contract["vocabularies"], list(TRAIN_CODES), literal_scale)
        bank_by_code = {code: {name: tensor_hash(value[codes.index(code)]) for name, value in bank.items()} for code in TRAIN_CODES}
        return dict(input_scaling=input_scale, head_scaling=head_scale, literal_scaling=literal_scale, training_bank_by_code=bank_by_code)
    old_fit = fitted(original, original_manifest, old_idx)
    new_fit = fitted(fresh, fresh_manifest, new_idx)
    if old_fit != new_fit:
        raise ValueError("effective training scaling/program-bank equality failed")
    contract_input = copy.deepcopy(original_contract["input_scaling"])
    contract_input.pop("fit_rows")
    if old_fit["input_scaling"] != contract_input or old_fit["head_scaling"] != original_contract["head_scaling"] or old_fit["literal_scaling"] != original_contract["literal_scaling"]["scale"]:
        raise ValueError("training scaling differs from saved original checkpoint contract")
    return dict(schema="jepa-transition-training-equivalence/1", status="PASS_EXACT_TRAIN_CONTENT_REUSE_ADMITTED", training_roots=100,
                canonical_root_keys=[list(k) for k in old_keys], tensor_sha256=hashes, all8candidate_inputs_labels_masks=True,
                program_sha256={code: G.digest(original_manifest["programs"][code]) for code in TRAIN_CODES},
                effective_training=old_fit, frozen_vocabulary_sha256=original_contract["vocabulary_sha256"],
                canonical_training_sha256=G.digest(dict(root_keys=old_keys, tensors=hashes, programs={code: G.digest(original_manifest["programs"][code]) for code in TRAIN_CODES}, effective=old_fit)),
                original_row_indices=old_idx.tolist(), fresh_row_indices=new_idx.tolist(), source_bank_slot_positions_may_differ=True,
                semantic_bank_alignment="All ten training banks match bit-for-bit by code under fixed symbols and literal scaling; padding/source slot positions are bookkeeping only.",
                reuse_policy="Reuse original seed17historical or new originalseed29/43 matched checkpoints; fresh split evaluates only. Mismatch requires STOP, never adaptation/retraining.",
                native_applies=0, model_forwards=0, optimizer_updates=0)


def convert_receipt(receipt, report, collection_plan, catalog, plan_sha256):
    """Adapt only the schema envelope; shared strict native checks remain intact."""
    if receipt.get("schema") != NEW_NATIVE_SCHEMA:
        raise ValueError("new replication receipt schema required")
    base = configured_contract()
    adapted = copy.deepcopy(receipt)
    adapted["schema"] = "jepa-grounded-native-transitions/1"
    adapted["collectionPlan"] = copy.deepcopy(collection_plan)
    adapted["collectionPlan"]["schema"] = "grounded-native-collection-plan/1"
    if receipt["collectionPlan"] != collection_plan:
        raise ValueError("replication receipt/plan differs before schema adaptation")
    arrays, manifest = base.convert_receipt(adapted, report, adapted["collectionPlan"], catalog, plan_sha256)
    manifest.update(schema="jepa-transition-replication-data/1", native_receipt_schema=NEW_NATIVE_SCHEMA,
                    split=dict(train_codes=list(TRAIN_CODES), heldout_codes=list(HELDOUT_CODES), train_state_families=list(range(10)), heldout_state_families=list(range(10, 14))),
                    shared_schema_adapter="Only schema envelope normalized; original raw receipt/records, plan bytes and source pins retained.")
    return arrays, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=EXPERIMENTS / "transition-replication")
    parser.add_argument("--native-receipt", type=Path)
    parser.add_argument("--collection-plan", type=Path, default=HERE / "transition_replication_collector/collection-plan.json")
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "--no-optional-locks", "-C", str(G.PINNED_KESSEL), "rev-parse", "HEAD"], text=True).strip()
    if revision != G.REVISION:
        raise ValueError("pinned source changed")
    subprocess.run(["git", "--no-optional-locks", "-C", str(G.PINNED_KESSEL), "diff", "--quiet", "HEAD", "--", "compiler/generated", "crates/kessel", "Cargo.lock", "Cargo.toml"], check=True)
    generated = G.PINNED_KESSEL / "compiler/generated"
    catalog = json.loads((generated / "cards.json").read_text())
    runtime = json.loads((generated / "runtime-admission.json").read_text())
    original_manifest = ORIGINAL / "grounded-contrast.manifest.json"
    original_contract = ORIGINAL / "fit-1/contract.json"
    plan = make_plan(catalog, runtime, json.loads(original_manifest.read_text()), json.loads(original_contract.read_text()))
    pins = [original_manifest, ORIGINAL / "grounded-contrast.npz", original_contract, ORIGINAL / "fit-1/result.json", Path(__file__),
            HERE / "grounded_contrast_data.py", HERE / "grounded_contrast_model.py", generated / "cards.json", generated / "runtime-admission.json", generated / "manifest.json"]
    plan["source_pins"] = [dict(path=str(p), sha256=G.sha(p)) for p in pins]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "replication-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    core = configured_contract().split_plan(configured_contract().inventory(catalog, runtime))
    (args.out_dir / "core-programs.json").write_text(json.dumps(core, indent=2) + "\n")
    (args.out_dir / "data-contract.json").write_text(json.dumps(plan["numeric_contract"], indent=2) + "\n")
    if args.native_receipt:
        report = configured_contract().inventory(catalog, runtime)
        report["sources"] = plan["source_pins"]
        arrays, manifest = convert_receipt(json.loads(args.native_receipt.read_text()), report, json.loads(args.collection_plan.read_text()), G.assembled_catalog(generated), G.sha(args.collection_plan))
        output = args.out_dir / "transition-replication.npz"
        np.savez_compressed(output, **arrays)
        manifest.update(artifact=dict(path=str(output), sha256=G.sha(output)), native_receipt=dict(path=str(args.native_receipt), sha256=G.sha(args.native_receipt)),
                        collection_plan=dict(path=str(args.collection_plan), sha256=G.sha(args.collection_plan)), replication_plan_sha256=G.sha(args.out_dir / "replication-plan.json"))
        (args.out_dir / "transition-replication.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(plan=str(args.out_dir / "replication-plan.json"), sha256=G.sha(args.out_dir / "replication-plan.json"), fresh_codes=list(HELDOUT_CODES), execution=False)))


if __name__ == "__main__":
    main()
