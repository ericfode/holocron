"""Prepare or execute one fixed, externally supervised transition replication seed.

Preflight imports NumPy and the hash-pinned, import-safe old model definitions;
it never imports Torch, constructs a neural model, or runs an optimizer/native call.
Only the coordinator launches --fit after reviewing the frozen preflight.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
MODEL_PATH = HERE / "grounded_contrast_model.py"
MODEL_SHA = "473bc2324cf62c0437effd631e8fec3cc5930d2aeee0d00255da3bd08747eaf2"
VOCAB_SHA = "29ba5cd39c3262bee8b2cd93719efdd96545d3e66d4f410084ca6a4048d660ce"
ORIGINAL_DATA_SHA = "83a0ec4125e3d97b54ebd910925558bed0c18b779b706417991a650da1dfed52"
ORIGINAL_MANIFEST_SHA = "c0206e0638a995b8237574cb11a697c35a0711d9a9f5dd9741314431bd4aea20"
SCHEMA = "jepa-transition-replication/1"
ARMS = ("correct-ir", "id-only", "wrong-ir", "context-only")
SEEDS = {"original": (29, 43), "fresh": (17, 29, 43)}
UPDATE_OFFSETS = {("original", 29): 0, ("original", 43): 2400}
ORIGINAL_TRAIN_CODES = ("SOR_011", "ASH_011", "IBH_053", "IBH_016", "LOF_134", "TWI_056", "SHD_196", "SOR_094", "LOF_004", "SOR_007")
EXPECTED_COUNTS = dict(optimizer_updates=2400, training_forward_batches=2400,
                       backward_batches=2400, heldout_validation_batches=8,
                       usage_batches=0, abi_embedding_batches=0, native_calls=0, paid_jobs=0)
EVALUATION_COUNTS = {name: 0 for name in EXPECTED_COUNTS}
EVALUATION_COUNTS["heldout_validation_batches"] = 4
CONTEXT_COLUMNS = ("ready_resources", "source_exhausted")
CANDIDATE_COLUMNS = ("owner_self", "owner_opponent", "is_unit", "is_base", "zone_ground", "zone_space", "same_source", "present",
                     "damage", "hp", "remaining_hp", "power", "exhausted", "shield_count", "xp_count", "known_damage", "known_hp",
                     "known_remaining_hp", "known_power", "known_exhausted", "known_shield_count", "known_xp_count", "trait_imperial",
                     "trait_creature", "trait_spectre", "known_traits")
CANDIDATE_ROLES = ("own_base", "opponent_base", "friendly_ground", "enemy_ground", "enemy_space", "friendly_imperial", "friendly_creature", "source")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def model_definitions():
    if sha(MODEL_PATH) != MODEL_SHA:
        raise ValueError("frozen model/loss source changed")
    spec = importlib.util.spec_from_file_location("frozen_transition_replication_model", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_program(ability):
    value = copy.deepcopy(ability)
    value.pop("title", None)
    return value


def validate_axes(manifest):
    """Use explicit reviewed manifest axes; never infer a state-ID threshold."""
    split = manifest["numeric_contract"]["split"]
    train_codes, held_codes = split["train_codes"], split["heldout_codes"]
    train_states, held_states = split["train_state_families"], split["heldout_state_families"]
    if (len(train_codes), len(held_codes), len(train_states), len(held_states)) != (10, 2, 10, 4):
        raise ValueError("fixed12program/14state allocation required")
    for train, held in ((train_codes, held_codes), (train_states, held_states)):
        if len(set(train)) != len(train) or len(set(held)) != len(held) or set(train) & set(held):
            raise ValueError("overlapping or duplicate split axes")
    if any(type(state) is not int for state in train_states + held_states):
        raise ValueError("state family IDs must be integers")
    if set(train_codes + held_codes) != set(manifest["programs"]):
        raise ValueError("program bank differs from explicit split")
    if split.get("primary") != "joint-held":
        raise ValueError("joint-held is the fixed primary cell")
    return split


def native_settled_commits(manifest, source, states):
    """Read measured native evidence only; labels are never derived from IR."""
    records = manifest["records"]
    if len(records) != len(source):
        raise ValueError("native root record count differs")
    settled = np.zeros((len(source), 8), bool)
    for i, record in enumerate(records):
        if record["source_card"] != source[i] or record["state_family"] != int(states[i]):
            raise ValueError("native record order differs from tensor roots")
        queries = record["raw_native_case"]["queries"]
        if len(queries) != 8:
            raise ValueError("expected8 independently branched native candidates")
        for j, query in enumerate(queries):
            if query["chosen_ref"] != CANDIDATE_ROLES[j]:
                raise ValueError("native candidate order differs")
            after = query["after"]
            settled[i, j] = bool(query["targetAction"] is not None and not query["engineError"] and after is not None and after.get("settled") is True)
    return settled


def load_data(dataset, manifest_path, vocabulary_contract, seed):
    M = model_definitions()
    manifest = read(manifest_path)
    if sha(dataset) != manifest["artifact"]["sha256"] or manifest.get("root_cases") != 168:
        raise ValueError("dataset hash/root count differs from manifest")
    if sha(vocabulary_contract) != VOCAB_SHA:
        raise ValueError("original fixed9020parameter vocabulary contract required")
    frozen = read(vocabulary_contract)
    symbols = frozen["vocabularies"]
    if {k: len(v) for k, v in symbols.items()} != dict(path=26, type=8, value=43):
        raise ValueError("frozen vocabulary dimensions differ")
    if frozen["source_pins"]["model_sha256"] != MODEL_SHA:
        raise ValueError("frozen vocabulary/model source pin differs")
    if tuple(manifest["target_names"]) != M.TARGET_NAMES or tuple(manifest["context_feature_names"]) != CONTEXT_COLUMNS or tuple(manifest["candidate_feature_names"]) != CANDIDATE_COLUMNS:
        raise ValueError("ordered input/output ABI differs")
    split = validate_axes(manifest)
    with np.load(dataset, allow_pickle=False) as bank:
        arrays = {name: value.copy() for name, value in bank.items()}
    shapes = dict(context_features=(168, 2), candidate_features=(168, 8, 26), candidate_mask=(168, 8), primary_candidate_mask=(168, 8),
                  source_use=(168,), source_use_mask=(168,), candidate_allowed=(168, 8), candidate_allowed_mask=(168, 8), targets=(168, 8, 11), target_mask=(168, 8, 11))
    for name, shape in shapes.items():
        value = arrays[name]
        if value.shape != shape or value.dtype != np.float32 or not np.isfinite(value).all():
            raise ValueError("invalid dense tensor " + name)
        if name.endswith("mask") and not np.isin(value, [0, 1]).all():
            raise ValueError("invalid mask " + name)
    if not np.array_equal(arrays["primary_candidate_mask"], np.tile([1.] * 7 + [0.], (168, 1))) or np.any(arrays["target_mask"][..., :2]):
        raise ValueError("source-self exclusion or standalone label ownership differs")
    source, states = arrays["source_cards"].astype(str), arrays["state_families"]
    if source.shape != (168,) or states.shape != (168,) or states.dtype != np.int64 or len(set(zip(source, states.tolist()))) != 168:
        raise ValueError("duplicate/malformed native roots")
    if set(states.tolist()) != set(split["train_state_families"] + split["heldout_state_families"]):
        raise ValueError("state bank differs from split")
    codes = sorted(manifest["programs"])
    if set(source.tolist()) != set(codes):
        raise ValueError("source identity bank differs")
    records = [dict(manifest["programs"][code], code=code) for code in codes]
    groups, identities = {}, {}
    for record in records:
        code = record["code"]
        group = M.digest(normalized_program(record["raw_ability"]))
        if group != record["program_group_id"]:
            raise ValueError("normalized program digest differs")
        groups[code] = group
        identities[code] = set(record["aliases"]) | {record["canonical_card_id"]}
        M.structural_tokens(record["raw_ability"])
    for a in split["train_codes"]:
        for b in split["heldout_codes"]:
            if groups[a] == groups[b] or identities[a] & identities[b]:
                raise ValueError("program duplicate/reprint identity crosses holdout")
    query = np.asarray([codes.index(code) for code in source], np.int64)
    if arrays["program_group_ids"].astype(str).tolist() != [groups[code] for code in source]:
        raise ValueError("root program group labels differ")
    expected_counts = dict(train=100, **{"program-held": 20, "state-held": 40, "joint-held": 8})
    for cell, key in M.CELL_ARRAYS.items():
        expected = [i for i, (code, state) in enumerate(zip(source, states)) if
                    (code in split["train_codes"]) == (cell in ("train", "state-held")) and
                    (int(state) in split["train_state_families"]) == (cell in ("train", "program-held"))]
        if arrays[key].dtype != np.int64 or arrays[key].tolist() != expected or len(expected) != expected_counts[cell]:
            raise ValueError("four-cell indices differ from explicit axes")
        if any(str(arrays["partition"][i]) != cell for i in expected):
            raise ValueError("root partition evidence differs")
    for state in split["train_state_families"] + split["heldout_state_families"]:
        rows = np.flatnonzero(states == state)
        if len(rows) != 12 or any(not np.array_equal(arrays["context_features"][i], arrays["context_features"][rows[0]]) or
                                 not np.array_equal(arrays["candidate_features"][i, :7], arrays["candidate_features"][rows[0], :7]) for i in rows):
            raise ValueError("primary contexts/candidates differ across same-state programs")
    for head in M.BINARY_HEADS:
        values, mask = ((arrays["source_use"], arrays["source_use_mask"]) if head == 0 else
                        (arrays["candidate_allowed"], arrays["candidate_allowed_mask"]) if head == 1 else (arrays["targets"][..., head], arrays["target_mask"][..., head]))
        if not np.isin(values[mask.astype(bool)], [0, 1]).all():
            raise ValueError("nonbinary known label")
    settled = native_settled_commits(manifest, source, states)
    if np.any(arrays["target_mask"][..., 2:].any(-1) & ~settled):
        raise ValueError("future labels require actual settled committed native branch")
    train_codes = split["train_codes"]
    train_programs = np.asarray([codes.index(code) for code in train_codes], np.int64)
    held_programs = np.asarray([codes.index(code) for code in split["heldout_codes"]], np.int64)
    numeric_scale = M.fit_numeric_scale(records, train_codes)
    _, bank = M.encode_program_bank(records, symbols, train_codes, numeric_scale)
    if bank["identity_indices"][held_programs].any():
        raise ValueError("held-out identity must be fixedUNK0")
    restricted = M.training_program_bank(bank, train_programs)
    if any(value[held_programs].any() for value in restricted.values()):
        raise ValueError("held-out bank content reached training bank")
    train = arrays["train_idx"]
    input_scaling = M.fit_input_scaling(arrays["context_features"], arrays["candidate_features"], train, arrays["primary_candidate_mask"])
    context, candidates = M.apply_input_scaling(arrays["context_features"], arrays["candidate_features"], input_scaling)
    head_scaling = M.fit_head_scaling(arrays["source_use"], arrays["source_use_mask"], arrays["candidate_allowed"], arrays["candidate_allowed_mask"], arrays["targets"], arrays["target_mask"], train, arrays["primary_candidate_mask"])
    group_ids = [record["program_group_id"] for record in records]
    rng = np.random.default_rng(seed + 3)
    wrong_eval = np.asarray([M.draw_wrong_programs([index], train_programs if index in train_programs else held_programs, group_ids, rng)[0] for index in query], np.int64)
    return dict(arrays=arrays, manifest=manifest, manifest_sha256=sha(manifest_path), dataset_sha256=sha(dataset), records=records, codes=codes,
                train_codes=train_codes, query=query, train_programs=train_programs, held_programs=held_programs, symbols=symbols,
                numeric_scale=numeric_scale, bank=bank, context=context, candidates=candidates, input_scaling=input_scaling,
                head_scaling=head_scaling, wrong_eval=wrong_eval, group_ids=group_ids, settled_commits=settled)


def schedules(data, seed):
    M = model_definitions()
    schedule = np.random.default_rng(seed + 1).choice(data["arrays"]["train_idx"], (600, 16), replace=True)
    wrong = np.stack([M.draw_wrong_programs(data["query"][rows], data["train_programs"], data["group_ids"], np.random.default_rng(seed + 2 + step)) for step, rows in enumerate(schedule)])
    return schedule, wrong


def array_digest(value):
    return hashlib.sha256(str(value.dtype).encode() + str(value.shape).encode() + value.tobytes()).hexdigest()


def validate_cohort(data, cohort, seed):
    if seed not in SEEDS.get(cohort, ()):
        raise ValueError("only original29/43 or fresh17/29/43 are allocated; historical original17 is not rerun")
    original = data["dataset_sha256"] == ORIGINAL_DATA_SHA and data["manifest_sha256"] == ORIGINAL_MANIFEST_SHA
    if (cohort == "original") != original or cohort == "fresh" and data["dataset_sha256"] == ORIGINAL_DATA_SHA:
        raise ValueError("cohort does not match immutable original/new dataset")
    split = data["manifest"]["numeric_contract"]["split"]
    if tuple(split["train_codes"]) != ORIGINAL_TRAIN_CODES:
        raise ValueError("the original ten training programs and identity order must be retained")
    if cohort == "fresh" and set(split["heldout_codes"]) != {"SHD_004", "TWI_206"}:
        raise ValueError("fresh held-program identities differ from predeclared pair")


def training_equivalence(original, fresh):
    """Exact canonical100-root proof is required before reusing saved weights."""
    fields = ("context_features", "candidate_features", "candidate_mask", "primary_candidate_mask", "source_use", "source_use_mask",
              "candidate_allowed", "candidate_allowed_mask", "targets", "target_mask")
    keys = lambda d: {(str(d["arrays"]["source_cards"][i]), int(d["arrays"]["state_families"][i])): int(i) for i in d["arrays"]["train_idx"]}
    before, after = keys(original), keys(fresh)
    if len(before) != 100 or set(before) != set(after) or original["train_codes"] != fresh["train_codes"]:
        raise ValueError("checkpoint reuse requires identical100training program/state roots and identity order")
    fingerprints = {}
    for field in fields:
        left = np.stack([original["arrays"][field][before[key]] for key in sorted(before)])
        right = np.stack([fresh["arrays"][field][after[key]] for key in sorted(before)])
        if left.dtype != right.dtype or not np.array_equal(left, right):
            raise ValueError("checkpoint reuse training tensor differs: " + field)
        fingerprints[field] = array_digest(left)
    if original["symbols"] != fresh["symbols"] or original["numeric_scale"] != fresh["numeric_scale"] or original["head_scaling"] != fresh["head_scaling"]:
        raise ValueError("checkpoint reuse requires identical vocab/numeric/head scalers")
    clean_scaling = lambda d: {key: value for key, value in d["input_scaling"].items() if key != "fit_rows"}
    if clean_scaling(original) != clean_scaling(fresh):
        raise ValueError("checkpoint reuse input scalers differ")
    bank_fingerprints = {}
    for code in original["train_codes"]:
        left_record = original["records"][original["codes"].index(code)]
        right_record = fresh["records"][fresh["codes"].index(code)]
        if normalized_program(left_record["raw_ability"]) != normalized_program(right_record["raw_ability"]) or any(left_record.get(key) != right_record.get(key) for key in ("program_group_id", "canonical_card_id", "aliases", "side", "index", "source_hash", "source_path")):
            raise ValueError("checkpoint reuse training program differs: " + code)
        for field in original["bank"]:
            left = np.asarray(original["bank"][field][original["codes"].index(code)])
            right = np.asarray(fresh["bank"][field][fresh["codes"].index(code)])
            if left.dtype != right.dtype or not np.array_equal(left, right):
                raise ValueError("checkpoint reuse training semantic/identity bank differs: " + code + "/" + field)
            bank_fingerprints[code + "/" + field] = array_digest(left)
    return dict(status="exact100training-roots-scalers-programs-and-encoded-bank-equivalent", roots=100, fields=fingerprints,
                bank_fields=bank_fingerprints, canonical_roots=[list(key) for key in sorted(before)],
                input_scaling=clean_scaling(fresh), head_scaling=fresh["head_scaling"], numeric_scale=fresh["numeric_scale"],
                note="Root/query indices and physical bank slots may differ; program-addressed inputs, identity indices and tensors match exactly. No retraining fallback is authorized.")


def saved_checkpoints(reference_result, seed):
    """Validate named arrays and provenance without constructing any model."""
    result = read(reference_result)
    if result["status"] != "completed" or result["config"]["seed"] != seed or result["updates_completed"] != 2400 or result["counts"]["optimizer_updates"] != 2400:
        raise ValueError("reference result must be completed matched4x600 seed")
    if result["dataset_sha256"] != ORIGINAL_DATA_SHA or result["manifest_sha256"] != ORIGINAL_MANIFEST_SHA:
        raise ValueError("reference weights must come from immutable original training dataset")
    if seed == 17:
        if result.get("source_sha256") != MODEL_SHA or sha(reference_result) != "733ce9aeecc373d5e17a4363b99970f2076e65ed753a9e5c338d4dad9fc0d68e":
            raise ValueError("historical17 reference evidence differs")
    elif result.get("frozen_model_source_sha256") != MODEL_SHA or result.get("runner_source_sha256") != sha(__file__) or result["config"].get("cohort") != "original":
        raise ValueError("new seed reference source/cohort differs")
    if [arm["arm"] for arm in result["arms"]] != list(ARMS):
        raise ValueError("reference arm order differs")
    if not result.get("initializations_identical") or len({arm["initialization_sha256"] for arm in result["arms"]}) != 1:
        raise ValueError("reference arms do not prove matched initialization")
    validated = {}
    for arm in result["arms"]:
        name = arm["arm"]
        checkpoint, contract_path = Path(reference_result).parent / (name + ".npz"), Path(reference_result).parent / (name + "-contract.json")
        if arm["updates"] != 600 or arm["parameters"] != 9020 or sha(checkpoint) != arm["checkpoint_sha256"] or sha(contract_path) != arm["contract_sha256"]:
            raise ValueError("reference checkpoint/contract hash or allocation differs")
        contract = read(contract_path)
        if contract["arm"] != name or contract["source_pins"]["model_sha256"] != MODEL_SHA:
            raise ValueError("reference named-weight contract source differs")
        with np.load(checkpoint, allow_pickle=False) as pack:
            arrays = {key: value.copy() for key, value in pack.items()}
        if set(arrays) != set(contract["named_weights"]) or sum(value.size for value in arrays.values()) != 9020:
            raise ValueError("reference named-weight set/count differs")
        for key, value in arrays.items():
            if list(value.shape) != contract["named_weights"][key]["shape"] or value.dtype != np.float32 or not np.isfinite(value).all():
                raise ValueError("reference weight shape/dtype/finite contract differs")
        validated[name] = dict(checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint), contract=str(contract_path), contract_sha256=sha(contract_path),
                               initialization_sha256=arm["initialization_sha256"], arrays=arrays)
    return validated


def worker_command(args):
    command = [str(Path(sys.executable).absolute()), str(Path(__file__).resolve()), "--fit" if args.cohort == "original" else "--evaluate"]
    for field in ("dataset", "manifest", "vocabulary_contract", "plan", "ledger", "progress", "events", "out", "seed", "cohort", "update_offset", "run_id", "campaign_id"):
        command.extend(["--" + field.replace("_", "-"), str(getattr(args, field))])
    if args.cohort == "fresh":
        for field in ("reference_dataset", "reference_manifest", "reference_result"):
            command.extend(["--" + field.replace("_", "-"), str(getattr(args, field))])
    return command


def dependency_paths(args):
    paths = [Path(__file__), MODEL_PATH, HERE / "run_events.py", HERE / "run_local_experiments.py", args.dataset, args.manifest, args.vocabulary_contract]
    if args.cohort == "fresh":
        paths += [args.reference_dataset, args.reference_manifest, args.reference_result]
        paths += [args.reference_result.parent / (arm + suffix) for arm in ARMS for suffix in (".npz", "-contract.json")]
    return paths


def make_preflight(args):
    data = load_data(args.dataset, args.manifest, args.vocabulary_contract, args.seed)
    validate_cohort(data, args.cohort, args.seed)
    expected_offset = UPDATE_OFFSETS[(args.cohort, args.seed)] if args.cohort == "original" else 4800
    if args.update_offset != expected_offset:
        raise ValueError("fit original29/43 then evaluate fresh17/29/43 with global4800 baseline required")
    if args.plan.exists() or args.out.exists():
        raise FileExistsError("new plan/output paths required; preserve all attempts")
    schedule, wrong = schedules(data, args.seed) if args.cohort == "original" else (None, None)
    config = copy.deepcopy(model_definitions().FIT_CONFIG)
    config.update(seed=args.seed, cohort=args.cohort, arms=list(ARMS), parameters_per_arm=9020, updates_per_arm=600,
                  batch_size=16, batch_seed=args.seed + 1, wrong_train_seed=args.seed + 2, wrong_eval_seed=args.seed + 3,
                  learning_rate=.003, weight_decay=.0001, gradient_clip_l2=1., optimizer="AdamW", final_checkpoint_only=True,
                  expected_counts=EXPECTED_COUNTS if args.cohort == "original" else EVALUATION_COUNTS, cumulative_campaign_updates=4800, cumulative_campaign_seconds=240,
                  sampled_rss_bytes=2147483648, cpu_workers=1, heldout_labels_used_in_training=False, search=False,
                  max_collection_fit_seconds=240, postfit_usage_batches=0, abi_embedding_batches=0)
    config.update(execution_mode="fit" if args.cohort == "original" else "evaluate", max_updates=2400 if args.cohort == "original" else 0,
                  max_updates_per_arm=600 if args.cohort == "original" else 0, updates_per_arm=600 if args.cohort == "original" else 0, final_validation_batches=8 if args.cohort == "original" else 4)
    config["update_offset"] = args.update_offset
    config["new_primary"] = dict(cell="joint-held", orientation="SHD_004 minus TWI_206", candidate_slots=list(range(7)),
                                 heads=["cost_resource", "xp_delta", "target_exhausted_delta"],
                                 admission="same state and candidate, both actual native legal/settled/known", aggregation="natural-unit per-head MAE plus equal train-scale head macro")
    plan = dict(schema=SCHEMA, status="preflight-no-neural-execution", config=config,
                sources=[dict(path=str(path.resolve()), sha256=sha(path)) for path in dependency_paths(args)],
                inputs=dict(dataset=str(args.dataset.resolve()), manifest=str(args.manifest.resolve()), vocabulary_contract=str(args.vocabulary_contract.resolve())),
                split=data["manifest"]["numeric_contract"]["split"], input_scaling=data["input_scaling"], head_scaling=data["head_scaling"], numeric_scale=data["numeric_scale"],
                schedule_sha256=array_digest(schedule) if schedule is not None else None, wrong_schedule_sha256=array_digest(wrong) if wrong is not None else None, wrong_eval_sha256=array_digest(data["wrong_eval"]),
                paths={key: str(getattr(args, key).resolve()) for key in ("out", "progress", "ledger", "events")},
                run_id=args.run_id, campaign_id=args.campaign_id,
                limitation="Historical originalseed17 remains descriptive; fresh3seed checkpoint reuse tests a separate held split, conditional on exact100training-root equivalence. Seeds do not add independent held-out cards.",
                execution="Coordinator GO and one owned shared-ledger stage required; preflight never imports Torch or constructs a model.")
    if args.cohort == "fresh":
        original = load_data(args.reference_dataset, args.reference_manifest, args.vocabulary_contract, args.seed)
        if original["dataset_sha256"] != ORIGINAL_DATA_SHA or original["manifest_sha256"] != ORIGINAL_MANIFEST_SHA:
            raise ValueError("reuse reference dataset is not immutable original")
        plan["training_equivalence"] = training_equivalence(original, data)
        references = saved_checkpoints(args.reference_result, args.seed)
        plan["reference_checkpoints"] = {arm: {key: value for key, value in row.items() if key != "arrays"} for arm, row in references.items()}
    plan["worker_command"] = worker_command(args)
    plan["supervisor_command"] = [str(Path(sys.executable).absolute()), str(HERE / "transition_replication_collector/supervise.py"),
                                  "--stage", config["execution_mode"], "--ledger", str(args.ledger), "--out", str(args.out.with_name(args.out.name + "-guard")),
                                  "--progress", str(args.progress), "--max-updates", str(config["max_updates"]), "--execute", "--command"] + plan["worker_command"]
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    for name, original in (("model-source.py", MODEL_PATH), ("runner-source.py", Path(__file__))):
        path = args.plan.with_name(args.plan.stem + "-" + name)
        if path.exists():
            raise FileExistsError("source snapshots must not be replaced")
        path.write_bytes(original.read_bytes())
    write(args.plan, plan)
    return plan


def root_errors(source_prediction, branch_prediction, data):
    M = model_definitions()
    a, scales = data["arrays"], data["head_scaling"]
    result = {}
    for cell, key in M.CELL_ARRAYS.items():
        if cell == "train":
            continue
        heads = {}
        for head, name in enumerate(M.TARGET_NAMES):
            rows = []
            for i in a[key]:
                target = a["source_use"][i:i+1] if head == 0 else a["candidate_allowed"][i] if head == 1 else a["targets"][i, :, head]
                predicted = source_prediction[i:i+1] if head == 0 else branch_prediction[i, :, head]
                known = a["source_use_mask"][i:i+1] if head == 0 else (a["candidate_allowed_mask"][i] if head == 1 else a["target_mask"][i, :, head]) * a["primary_candidate_mask"][i]
                if known.any():
                    error = float((abs(predicted - target) * known).sum() / known.sum())
                    rows.append(dict(root_index=int(i), code=str(a["source_cards"][i]), state_family=int(a["state_families"][i]),
                                     known_coordinates=int(known.sum()), native_values=np.unique(target[known.astype(bool)]).tolist(),
                                     mae=error, train_scaled_mae=error / scales["scale"][head]))
            heads[name] = rows
        result[cell] = heads
    return result


def paired_native_errors(source_prediction, branch_prediction, data):
    """Static differences of saved native labels/predictions; no new forward."""
    M = model_definitions()
    a, result = data["arrays"], {}
    for cell, key in M.CELL_ARRAYS.items():
        if cell == "train":
            continue
        pairs = []
        for state in sorted(set(a["state_families"][a[key]].tolist())):
            rows = [int(i) for i in a[key] if a["state_families"][i] == state]
            for offset, left in enumerate(rows):
                for right in rows[offset + 1:]:
                    if a["program_group_ids"][left] == a["program_group_ids"][right]:
                        continue
                    for head, name in enumerate(M.TARGET_NAMES):
                        for candidate in ((None,) if head == 0 else range(7)):
                            if head == 0:
                                if not a["source_use_mask"][[left, right]].all():
                                    continue
                                target, predicted = a["source_use"][[left, right]], source_prediction[[left, right]]
                            elif head == 1:
                                if not a["candidate_allowed_mask"][[left, right], candidate].all():
                                    continue
                                target, predicted = a["candidate_allowed"][[left, right], candidate], branch_prediction[[left, right], candidate, head]
                            else:
                                if not (a["target_mask"][[left, right], candidate, head].all() and data["settled_commits"][[left, right], candidate].all()
                                        and a["candidate_allowed_mask"][[left, right], candidate].all() and a["candidate_allowed"][[left, right], candidate].all()):
                                    continue
                                target, predicted = a["targets"][[left, right], candidate, head], branch_prediction[[left, right], candidate, head]
                            target_delta, predicted_delta = float(target[0] - target[1]), float(predicted[0] - predicted[1])
                            error = abs(predicted_delta - target_delta)
                            pairs.append(dict(head=name, left_root=left, right_root=right, left_code=str(a["source_cards"][left]), right_code=str(a["source_cards"][right]),
                                              state_family=int(state), candidate=candidate, native_delta=target_delta, predicted_delta=predicted_delta,
                                              native_varies=target_delta != 0, absolute_contrast_error=error, train_scaled_error=error / data["head_scaling"]["scale"][head],
                                              kind="settled-both-legal-transition" if head > 1 else "source-availability" if head == 0 else "native-target-membership"))
        summary = {}
        for name in M.TARGET_NAMES:
            groups = {}
            for varies in (True, False):
                selected = [pair for pair in pairs if pair["head"] == name and pair["native_varies"] == varies]
                groups["varying_native" if varies else "invariant_native"] = dict(pairs=len(selected), states=len({p["state_family"] for p in selected}),
                    program_pairs=len({tuple(sorted((p["left_code"], p["right_code"]))) for p in selected}),
                    mean_train_scaled_error=float(np.mean([p["train_scaled_error"] for p in selected])) if selected else None)
            summary[name] = groups
        result[cell] = dict(summary=summary, pairs=pairs, caveat="Dependent same-state/candidate program pairs; no independent-sample or causal population claim. Committed outcomes require both offered/legal/settled; availability contrasts are separate.")
    return result


def fresh_primary(paired):
    selected = paired["joint-held"]["pairs"]
    heads = {}
    for head in ("cost_resource", "xp_delta", "target_exhausted_delta"):
        rows = [dict(pair) for pair in selected if pair["head"] == head and {pair["left_code"], pair["right_code"]} == {"SHD_004", "TWI_206"}]
        for row in rows:
            if row["left_code"] != "SHD_004":
                for key in ("native_delta", "predicted_delta"):
                    row[key] *= -1
                row["left_code"], row["right_code"] = row["right_code"], row["left_code"]
                row["left_root"], row["right_root"] = row["right_root"], row["left_root"]
        heads[head] = dict(pairs=len(rows), states=len({row["state_family"] for row in rows}),
                           mae=float(np.mean([row["absolute_contrast_error"] for row in rows])) if rows else None,
                           train_scaled_mae=float(np.mean([row["train_scaled_error"] for row in rows])) if rows else None,
                           native_deltas=sorted({row["native_delta"] for row in rows}), detail=rows)
    available = [row["train_scaled_mae"] for row in heads.values() if row["pairs"]]
    return dict(orientation="SHD_004 minus TWI_206", heads=heads, requested_heads=3, supported_heads=len(available),
                macro_train_scaled_mae=float(np.mean(available)) if len(available) == 3 else None,
                limitation="Same four authored held-state families/two held programs; dependent pairs. No exact power4-vs3 boundary support. Source-use allpositive joint cell is diagnostic.")


def progress_baseline(path):
    if not Path(path).exists():
        return 0
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if [row["updates_completed"] for row in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("global durable journal must be exact1..N")
    if any(rows[i]["monotonic"] >= rows[i+1]["monotonic"] for i in range(len(rows)-1)):
        raise ValueError("global durable journal monotonic timestamps differ")
    return len(rows)


def progress(path, global_step, local_step, arm, arm_step, args):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(dict(updates_completed=global_step, seed_updates_completed=local_step, seed=args.seed,
                                     cohort=args.cohort, run_id=args.run_id, arm=arm, arm_step=arm_step, monotonic=time.monotonic())) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_plan(args):
    plan = read(args.plan)
    if plan["config"]["seed"] != args.seed or plan["config"]["cohort"] != args.cohort or plan["config"]["update_offset"] != args.update_offset:
        raise ValueError("seed/cohort differs from frozen preflight")
    if len(plan["sources"]) != len(dependency_paths(args)) or {row["path"] for row in plan["sources"]} != {str(path.resolve()) for path in dependency_paths(args)}:
        raise ValueError("frozen preflight lacks exact required source/input pins")
    for row in plan["sources"]:
        if sha(row["path"]) != row["sha256"]:
            raise ValueError("frozen source/input changed: " + row["path"])
    for field in ("dataset", "manifest", "vocabulary_contract"):
        if str(getattr(args, field).resolve()) != plan["inputs"][field]:
            raise ValueError("input path differs from preflight")
    for field, path in plan["paths"].items():
        if str(getattr(args, field).resolve()) != path:
            raise ValueError("output/ledger path differs from preflight")
    if (args.run_id, args.campaign_id) != (plan["run_id"], plan["campaign_id"]):
        raise ValueError("run identity differs from preflight")
    ledger = [json.loads(line) for line in args.ledger.read_text().splitlines() if line.strip()]
    latest = ledger[-1]
    metadata = latest.get("metadata", {})
    stage, reservation = ("fit", 2400) if args.cohort == "original" else ("evaluate", 0)
    if latest.get("event") != "stage-start" or latest.get("stage") != stage or latest.get("reserved_updates") != reservation:
        raise ValueError("one active externally guarded replication stage required")
    if metadata.get("max_updates") != 4800 or metadata.get("max_active_seconds") != 240 or metadata.get("max_sampled_bytes") != 2147483648 or metadata.get("max_engine_apply_attempts") != 2048:
        raise ValueError("replication shared campaign allowance differs")
    if Path(metadata.get("campaign_ledger", "")).resolve() != args.ledger.resolve():
        raise ValueError("guard ledger path differs")
    if latest.get("prior", {}).get("updates") != args.update_offset or progress_baseline(args.progress) != args.update_offset:
        raise ValueError("global journal and charged ledger baseline must equal planned offset")
    if metadata.get("initial_progress_updates") != args.update_offset:
        raise ValueError("guard did not record the global journal baseline")
    if metadata.get("commands") != [[stage, plan["worker_command"]]]:
        raise ValueError("guard worker command differs from structured preflight")
    if args.out.exists():
        raise FileExistsError("output must be fresh")
    return plan


def fit(args):
    if args.cohort != "original":
        raise ValueError("only two original-data seeds may fit; fresh split is evaluate-only")
    plan = verify_plan(args)
    M = model_definitions()
    data = load_data(args.dataset, args.manifest, args.vocabulary_contract, args.seed)
    validate_cohort(data, args.cohort, args.seed)
    schedule, wrong = schedules(data, args.seed)
    if (array_digest(schedule), array_digest(wrong), array_digest(data["wrong_eval"])) != (plan["schedule_sha256"], plan["wrong_schedule_sha256"], plan["wrong_eval_sha256"]):
        raise ValueError("seeded schedules differ from frozen preflight")
    args.out.mkdir(parents=True, exist_ok=False)
    contract = M.numerical_contract(data)
    contract["config"] = plan["config"]
    contract["replication_runner_sha256"] = sha(__file__)
    contract["frozen_model_source_sha256"] = MODEL_SHA
    contract["replication_allocation"] = "8initial/final validation batches;0usage/ABI extras; final checkpoint only"
    write(args.out / "contract.json", contract)
    write(args.out / "preflight.json", plan)
    np.save(args.out / "batch-schedule.npy", schedule)
    np.save(args.out / "wrong-program-schedule.npy", wrong)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    from run_events import RunEvents
    writer = RunEvents(args.events, run_id=args.run_id, commit=commit, config=plan["config"],
                       dataset=dict(npz_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"], shared_ledger=str(args.ledger), frozen_model_source_sha256=MODEL_SHA),
                       limitations=["Three seeds do not add independent held-out cards; fresh split is a separate experiment, not a pure old-distribution replication.",
                                    "Historical originalseed17 was already observed; all new seeds are reported without selection."], parent_run_id=args.campaign_id)
    counts = {name: 0 for name in EXPECTED_COUNTS}
    started, arms, initial_hash = time.monotonic(), [], None
    writer.emit("status", "preparing", 0, status="running")
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        x, c, q = torch.as_tensor(data["context"]), torch.as_tensor(data["candidates"]), torch.as_tensor(data["query"])
        all_bank = M.torch_bank(torch, data["bank"])
        train_bank = M.torch_bank(torch, M.training_program_bank(data["bank"], data["train_programs"]))
        labels = {name: torch.as_tensor(data["arrays"][name]) for name in ("source_use", "source_use_mask", "candidate_allowed", "candidate_allowed_mask", "targets", "target_mask", "primary_candidate_mask")}
        eval_rows = np.concatenate([data["arrays"][key] for cell, key in M.CELL_ARRAYS.items() if cell != "train"])
        for arm in ARMS:
            torch.manual_seed(args.seed)
            model = M.make_contrast_model(torch, data["symbols"])
            parameters = sum(p.numel() for p in model.parameters())
            if parameters != 9020:
                raise ValueError("replication architecture must have exactly9020parameters")
            state = {name: value.detach().numpy().copy() for name, value in model.state_dict().items()}
            state_hash = hashlib.sha256(b"".join(name.encode() + value.tobytes() for name, value in sorted(state.items()))).hexdigest()
            if initial_hash is not None and initial_hash != state_hash:
                raise AssertionError("matched arms need identical initialization")
            initial_hash = state_hash
            optimizer = torch.optim.AdamW(model.parameters(), lr=.003, weight_decay=.0001)
            def evaluate():
                if counts["heldout_validation_batches"] >= 8:
                    raise RuntimeError("eight validation batches exhausted")
                counts["heldout_validation_batches"] += 1
                query = torch.as_tensor(data["wrong_eval"][eval_rows]) if arm == "wrong-ir" else q[eval_rows]
                with torch.no_grad():
                    source, branch = M.predictions(torch, model(x[eval_rows], c[eval_rows], query, all_bank, arm), data["head_scaling"])
                sf, bf = np.zeros(168, np.float32), np.zeros((168, 8, 11), np.float32)
                sf[eval_rows], bf[eval_rows] = source, branch
                return M.metric_cells(sf, bf, data), sf, bf
            initial, initial_source, initial_branch = evaluate()
            gradients = []
            for step, rows in enumerate(schedule, 1):
                optimizer.zero_grad(set_to_none=True)
                query = torch.as_tensor(wrong[step - 1]) if arm == "wrong-ir" else q[rows]
                counts["training_forward_batches"] += 1
                output = model(x[rows], c[rows], query, train_bank, arm)
                loss, _ = M.balanced_head_loss(torch, *output, {name: value[rows] for name, value in labels.items()}, data["head_scaling"])
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError("nonfinite training loss")
                counts["backward_batches"] += 1
                loss.backward()
                if step in (1, 600):
                    gradients.append(dict(arm_step=step, module_preclip_gradients=M.gradient_summary(model)))
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                if not bool(torch.isfinite(norm)):
                    raise FloatingPointError("nonfinite gradient")
                optimizer.step()
                counts["optimizer_updates"] += 1
                progress(args.progress, args.update_offset + counts["optimizer_updates"], counts["optimizer_updates"], arm, step, args)
                if step % 100 == 0:
                    writer.emit("metric", arm, counts["optimizer_updates"], arm=arm, arm_step=step,
                                metrics=dict(train_loss=float(loss.detach()), grad_norm=float(norm), **counts))
            final, source, branch = evaluate()
            checkpoint = args.out / (arm + ".npz")
            np.savez(checkpoint, **{name: value.detach().numpy() for name, value in model.state_dict().items()})
            predictions_path = args.out / (arm + "-predictions.npz")
            np.savez_compressed(predictions_path, source_predictions=source[eval_rows], branch_predictions=branch[eval_rows],
                initial_source_predictions=initial_source[eval_rows], initial_branch_predictions=initial_branch[eval_rows], root_indices=eval_rows,
                source_targets=data["arrays"]["source_use"][eval_rows], source_mask=data["arrays"]["source_use_mask"][eval_rows],
                candidate_targets=data["arrays"]["candidate_allowed"][eval_rows], candidate_mask=data["arrays"]["candidate_allowed_mask"][eval_rows],
                targets=data["arrays"]["targets"][eval_rows], target_mask=data["arrays"]["target_mask"][eval_rows],
                primary_candidate_mask=data["arrays"]["primary_candidate_mask"][eval_rows], program_groups=data["arrays"]["program_group_ids"][eval_rows],
                state_families=data["arrays"]["state_families"][eval_rows], partition=data["arrays"]["partition"][eval_rows])
            evidence_path = args.out / (arm + "-evaluation-evidence.json")
            paired = paired_native_errors(source, branch, data)
            evidence = dict(root_errors=root_errors(source, branch, data), paired_native_errors=paired)
            if args.cohort == "fresh":
                evidence["predeclared_fresh_primary"] = fresh_primary(paired)
            write(evidence_path, evidence)
            arm_contract = dict(contract, arm=arm, checkpoint_sha256=sha(checkpoint), named_weights={name: dict(shape=list(value.shape), dtype=str(value.dtype)) for name, value in model.state_dict().items()},
                                reference_forward="unchanged grounded_contrast_model.make_contrast_model().forward", no_extra_reference_forward=True)
            contract_path = args.out / (arm + "-contract.json")
            write(contract_path, arm_contract)
            arm_result = dict(arm=arm, updates=600, parameters=parameters, initialization_sha256=state_hash, gradient_snapshots=gradients,
                             initial=initial, final=final, checkpoint_sha256=sha(checkpoint), predictions_sha256=sha(predictions_path),
                             contract_sha256=sha(contract_path), evaluation_evidence_sha256=sha(evidence_path))
            if args.cohort == "fresh":
                arm_result["predeclared_fresh_primary"] = evidence["predeclared_fresh_primary"]
            arms.append(arm_result)
            writer.emit("metric", arm, counts["optimizer_updates"], arm=arm, arm_step=600, metrics=M._flat_scores(final))
        if counts != EXPECTED_COUNTS:
            raise AssertionError("fixed per-seed counters differ")
        result = dict(schema=SCHEMA, status="completed", counts=counts, arms=arms, config=plan["config"], baselines=M.no_fit_baselines(data),
                      updates_completed=counts["optimizer_updates"], global_updates_completed=args.update_offset + counts["optimizer_updates"], dataset_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"],
                      preflight_sha256=sha(args.plan), contract_sha256=sha(args.out / "contract.json"), runner_source_sha256=sha(__file__), frozen_model_source_sha256=MODEL_SHA,
                      commit=commit, runtime=M.G.runtime_metadata(torch), fit_seconds=time.monotonic() - started,
                      heldout_labels_used_in_training=False, fixed_wrong_id_permutation=False, initializations_identical=True,
                      no_extra_usage_or_abi_forwards=True, final_checkpoint_only=True)
        write(args.out / "result.json", result)
        writer.emit("artifact", "completed", counts["optimizer_updates"], status="completed", artifacts=dict(result=str(args.out / "result.json")))
        return result
    except BaseException as exc:
        write(args.out / "error.json", dict(error=repr(exc), counts=counts, updates_completed=counts["optimizer_updates"]))
        writer.emit("status", "failed", counts["optimizer_updates"], status="failed", error=repr(exc))
        raise


def evaluate(args):
    if args.cohort != "fresh":
        raise ValueError("evaluate-only mode is allocated to the fresh held split")
    plan = verify_plan(args)
    M = model_definitions()
    data = load_data(args.dataset, args.manifest, args.vocabulary_contract, args.seed)
    original = load_data(args.reference_dataset, args.reference_manifest, args.vocabulary_contract, args.seed)
    validate_cohort(data, "fresh", args.seed)
    equivalence = training_equivalence(original, data)
    if equivalence != plan["training_equivalence"] or array_digest(data["wrong_eval"]) != plan["wrong_eval_sha256"]:
        raise ValueError("checkpoint-reuse proof or evaluation control differs from preflight")
    references = saved_checkpoints(args.reference_result, args.seed)
    progress_before = args.progress.read_bytes()
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out / "preflight.json", plan)
    write(args.out / "training-equivalence.json", equivalence)
    contract = M.numerical_contract(data)
    contract.update(config=plan["config"], replication_runner_sha256=sha(__file__), frozen_model_source_sha256=MODEL_SHA,
                    reference_result_sha256=sha(args.reference_result), reference_result=str(args.reference_result), checkpoint_reuse=True,
                    replication_allocation="four final heldout batches, zero training/usage/ABI extras")
    write(args.out / "contract.json", contract)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    from run_events import RunEvents
    writer = RunEvents(args.events, run_id=args.run_id, commit=commit, config=plan["config"],
                       dataset=dict(npz_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"], shared_ledger=str(args.ledger),
                                    reference_result_sha256=sha(args.reference_result), training_equivalence_sha256=sha(args.out / "training-equivalence.json")),
                       limitations=["Fresh held split reuses saved weights only after exact100training-root equivalence. Two held IDs/four authored states are not independent population support.",
                                    "Historicalseed17 and new29/43 are all reported without seed selection."], parent_run_id=args.campaign_id)
    counts = {name: 0 for name in EVALUATION_COUNTS}
    started, arms = time.monotonic(), []
    writer.emit("status", "preparing", 4800, status="running")
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        x, c, q = torch.as_tensor(data["context"]), torch.as_tensor(data["candidates"]), torch.as_tensor(data["query"])
        all_bank = M.torch_bank(torch, data["bank"])
        eval_rows = np.concatenate([data["arrays"][key] for cell, key in M.CELL_ARRAYS.items() if cell != "train"])
        for arm in ARMS:
            torch.manual_seed(args.seed)
            model = M.make_contrast_model(torch, data["symbols"])
            reference = references[arm]
            if sum(parameter.numel() for parameter in model.parameters()) != 9020:
                raise ValueError("reference architecture must have9020parameters")
            model.load_state_dict({name: torch.as_tensor(value) for name, value in reference["arrays"].items()}, strict=True)
            model.eval()
            query = torch.as_tensor(data["wrong_eval"][eval_rows]) if arm == "wrong-ir" else q[eval_rows]
            counts["heldout_validation_batches"] += 1
            if counts["heldout_validation_batches"] > 4:
                raise RuntimeError("four final evaluation batches exhausted")
            with torch.no_grad():
                sp, bp = M.predictions(torch, model(x[eval_rows], c[eval_rows], query, all_bank, arm), data["head_scaling"])
            source, branch = np.zeros(168, np.float32), np.zeros((168, 8, 11), np.float32)
            source[eval_rows], branch[eval_rows] = sp, bp
            if any(not np.array_equal(value.detach().numpy(), reference["arrays"][name]) for name, value in model.state_dict().items()):
                raise ValueError("evaluate-only model state changed")
            final = M.metric_cells(source, branch, data)
            predictions_path = args.out / (arm + "-predictions.npz")
            np.savez_compressed(predictions_path, source_predictions=sp, branch_predictions=bp, root_indices=eval_rows,
                source_targets=data["arrays"]["source_use"][eval_rows], source_mask=data["arrays"]["source_use_mask"][eval_rows],
                candidate_targets=data["arrays"]["candidate_allowed"][eval_rows], candidate_mask=data["arrays"]["candidate_allowed_mask"][eval_rows],
                targets=data["arrays"]["targets"][eval_rows], target_mask=data["arrays"]["target_mask"][eval_rows],
                primary_candidate_mask=data["arrays"]["primary_candidate_mask"][eval_rows], program_groups=data["arrays"]["program_group_ids"][eval_rows],
                state_families=data["arrays"]["state_families"][eval_rows], partition=data["arrays"]["partition"][eval_rows])
            paired = paired_native_errors(source, branch, data)
            primary = fresh_primary(paired)
            evidence_path = args.out / (arm + "-evaluation-evidence.json")
            write(evidence_path, dict(root_errors=root_errors(source, branch, data), paired_native_errors=paired, predeclared_fresh_primary=primary))
            contract_path = args.out / (arm + "-contract.json")
            write(contract_path, dict(contract, arm=arm, reference_checkpoint_sha256=reference["checkpoint_sha256"],
                                      reference_checkpoint=reference["checkpoint"], reference_contract_sha256=reference["contract_sha256"],
                                      named_weights={name: dict(shape=list(value.shape), dtype=str(value.dtype)) for name, value in model.state_dict().items()}))
            arms.append(dict(arm=arm, updates=0, checkpoint_reused=True, parameters=9020, initialization_sha256=reference["initialization_sha256"],
                             reference_checkpoint_sha256=reference["checkpoint_sha256"], reference_contract_sha256=reference["contract_sha256"], final=final,
                             predictions_sha256=sha(predictions_path), contract_sha256=sha(contract_path), evaluation_evidence_sha256=sha(evidence_path),
                             predeclared_fresh_primary=primary))
            writer.emit("metric", arm, 4800, arm=arm, arm_step=600, metrics=M._flat_scores(final))
        if counts != EVALUATION_COUNTS or args.progress.read_bytes() != progress_before:
            raise ValueError("evaluation count/journal invariance failed")
        for row in plan["sources"]:
            if sha(row["path"]) != row["sha256"]:
                raise ValueError("reference source/input/checkpoint changed during evaluation")
        result = dict(schema=SCHEMA, status="completed", counts=counts, arms=arms, config=plan["config"], baselines=M.no_fit_baselines(data),
                      updates_completed=0, global_updates_completed=4800, dataset_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"],
                      preflight_sha256=sha(args.plan), contract_sha256=sha(args.out / "contract.json"), runner_source_sha256=sha(__file__), frozen_model_source_sha256=MODEL_SHA,
                      reference_result_sha256=sha(args.reference_result), training_equivalence_sha256=sha(args.out / "training-equivalence.json"), checkpoint_reuse=True,
                      commit=commit, runtime=M.G.runtime_metadata(torch), evaluate_seconds=time.monotonic() - started, journal_unchanged=True,
                      heldout_labels_used_in_training=False, no_extra_usage_or_abi_forwards=True, model_states_unchanged=True)
        write(args.out / "result.json", result)
        writer.emit("artifact", "completed", 4800, status="completed", artifacts=dict(result=str(args.out / "result.json")))
        return result
    except BaseException as exc:
        write(args.out / "error.json", dict(error=repr(exc), counts=counts, updates_completed=0))
        writer.emit("status", "failed", 4800, status="failed", error=repr(exc))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--fit", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    for key in ("dataset", "manifest", "vocabulary-contract", "plan", "ledger", "progress", "events", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--update-offset", type=int, required=True)
    parser.add_argument("--cohort", choices=list(SEEDS), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--campaign-id", required=True)
    for key in ("reference-dataset", "reference-manifest", "reference-result"):
        parser.add_argument("--" + key, type=Path)
    args = parser.parse_args()
    for field in ("dataset", "manifest", "vocabulary_contract", "plan", "ledger", "progress", "events", "out"):
        if not getattr(args, field).is_absolute():
            parser.error("absolute paths required for " + field)
    if args.cohort == "fresh":
        for field in ("reference_dataset", "reference_manifest", "reference_result"):
            if getattr(args, field) is None or not getattr(args, field).is_absolute():
                parser.error("fresh evaluate/preflight requires absolute " + field)
    elif any(getattr(args, field) is not None for field in ("reference_dataset", "reference_manifest", "reference_result")):
        parser.error("original fits do not accept checkpoint reuse references")
    if args.preflight:
        plan = make_preflight(args)
        print(json.dumps(dict(status=plan["status"], plan=str(args.plan), plan_sha256=sha(args.plan), expected_counts=plan["config"]["expected_counts"]), indent=2))
    elif args.fit:
        fit(args)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
