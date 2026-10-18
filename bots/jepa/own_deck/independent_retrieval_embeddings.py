"""One frozen declaration-context batch for independent retrieval controls.

--prepare makes a hash-pinned plan without importing or calling a model.
--execute requires coordinating root GO and the unchanged prepared bank.
No optimizers, native engine calls, games, ranking or paid compute occur here.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCHEMA = "jepa-independent-retrieval-embedding/1"
ANCHORS = (10, 14, 25)
EXPORT = ROOT / "experiments/embedding-export"
DATA = ROOT / "experiments/data"
GEOMETRY = HERE / "embedding-geometry-evidence"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def write(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def input_row_hash(np, deck):
    """Identical row-level state/IDs/livefeatures/mask/deck bytes, batch agnostic."""
    tensors = (("state", np.zeros(73, np.float32)), ("ids", np.zeros(24, np.int64)),
               ("features", np.zeros((24, 21), np.float32)), ("mask", np.zeros(24, np.float32)),
               ("own_deck", np.asarray(deck, np.float32)))
    digest = hashlib.sha256()
    for name, value in tensors:
        digest.update(name.encode())
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(list(value.shape)).encode())
        digest.update(value.tobytes())
    return digest.hexdigest()


def load_controls(np, pack_path, manifest_path):
    manifest = read(manifest_path)
    if sha(pack_path) != manifest["artifact"]["sha256"] or Path(manifest["artifact"]["path"]).resolve() != Path(pack_path).resolve():
        raise ValueError("control bank/manifest linkage differs")
    with np.load(pack_path, allow_pickle=False) as pack:
        features, ids, source = pack["deck_features"].copy(), pack["row_ids"].astype(str), pack["source_indices"].copy()
    n = len(features)
    if features.dtype != np.float32 or features.shape != (n, 2, 207) or not 3 <= n <= 40 or not np.isfinite(features).all():
        raise ValueError("expected finite float32[N,2,207], at most40controlrows")
    if ids.shape != (n,) or len(set(ids.tolist())) != n or source.dtype != np.int64 or source.shape != (n,):
        raise ValueError("invalid ordered row IDs/source indices")
    if not set(source.tolist()) <= set(ANCHORS):
        raise ValueError("independent source families are frozen to10/14/25")
    rows = manifest["rows"]
    if len(rows) != n or [r["id"] for r in rows] != ids.tolist() or [r["source_index"] for r in rows] != source.tolist():
        raise ValueError("control lineage row order differs")
    # Original anchors alone are historical references. Planted module anchors
    # are new declarations even when they share a background source_index.
    anchors = [i for i, row in enumerate(rows) if row["kind"] == "anchor"]
    if len(anchors) != 3 or set(source[anchors].tolist()) != set(ANCHORS):
        raise ValueError("exactly three original anchors10/14/25 required")
    with np.load(DATA / "real-decks.npz", allow_pickle=False) as prior:
        original = prior["deck_features"].copy()
        train, validation = prior["train_idx"].tolist(), prior["val_idx"].tolist()
    prior_manifest = read(DATA / "real-decks.manifest.json")
    by_source = {row["source_index"]: i for i, row in enumerate(prior_manifest["declarations"])}
    for index in anchors:
        if not np.array_equal(features[index], original[by_source[int(source[index])]]):
            raise ValueError("anchor ownDeck input differs from frozen old27 bank")
    for index in range(n):
        if not np.array_equal(features[index, 1], original[by_source[int(source[index])], 1]):
            raise ValueError("remaining row must stay exactly the old unknown role")
    invariance = {}
    for index, row in enumerate(rows):
        group = row.get("invariance_group")
        if group:
            if group in invariance and not np.array_equal(features[index], features[invariance[group]]):
                raise ValueError("declared permutation/reprint positive changes actual encoding")
            invariance.setdefault(group, index)
    if any(by_source[int(source[i])] not in validation for i in anchors) or len(train) != 22:
        raise ValueError("original22/5 split differs")
    return dict(features=features, ids=ids, source_indices=source, rows=rows, manifest=manifest,
                anchor_indices=anchors, by_source=by_source, train=train, validation=validation,
                row_input_sha256=[input_row_hash(np, row) for row in features],
                exact_unique_encoded_inputs=len({row.tobytes() for row in features}), original_features=original,
                original_source_indices=[row["source_index"] for row in prior_manifest["declarations"]])


def ordered_forward_bank(np, controls):
    """One bank: inherited training22 references, then frozen independent controls."""
    train = np.asarray(controls["train"], np.int64)
    features = np.concatenate((controls["original_features"][train], controls["features"]), 0)
    ids = np.asarray([f"train-reference-{controls['original_source_indices'][i]:02}" for i in train] + controls["ids"].tolist())
    source = np.asarray([controls["original_source_indices"][i] for i in train] + controls["source_indices"].tolist(), np.int64)
    if len(features) > 64 or len(set(ids.tolist())) != len(ids):
        raise ValueError("forward bank exceeds64rows or has colliding row IDs")
    return dict(features=features, ids=ids, source_indices=source,
                train_reference_indices=np.arange(22, dtype=np.int64), control_indices=np.arange(22, len(features), dtype=np.int64),
                reference_indices=np.r_[np.arange(22), 22 + np.asarray(controls["anchor_indices"])].astype(np.int64),
                row_input_sha256=[input_row_hash(np, row) for row in features])


def verified_prior(np):
    export = read(EXPORT / "deck-embeddings.json")
    manifest = read(EXPORT / "deck-embeddings.manifest.json")
    if sha(EXPORT / "deck-embeddings.json") != manifest["artifact"]["sha256"]:
        raise ValueError("old exported27vectors changed")
    for key in ("base", "supplement", "input_dataset", "input_manifest"):
        if sha(manifest[key]["path"]) != manifest[key]["sha256"]:
            raise ValueError("old protected source changed: " + key)
    for source in manifest["encoder_sources"]:
        if sha(source["path"]) != source["sha256"]:
            raise ValueError("old encoder implementation changed")
    vectors = np.asarray([row["vector"] for row in export["rows"]], np.float64)
    geometry_result = read(GEOMETRY / "result.json")
    geometry_receipt = read(GEOMETRY / "receipt.json")
    if sha(GEOMETRY / "result.json") != geometry_receipt["result_sha256"]:
        raise ValueError("prior static transform receipt changed")
    transform_path = GEOMETRY / "train-transform.npz"
    if sha(transform_path) != geometry_result["numerical_artifacts"]["train_transform_sha256"]:
        raise ValueError("frozen training transform changed")
    plan = read(GEOMETRY / "plan.json")
    if plan["transformations"]["shrinkage_alpha"] != .1 or len(plan["train_indices"]) != 22:
        raise ValueError("fixed alpha.1 training22 transform required")
    with np.load(transform_path, allow_pickle=False) as pack:
        mean, whitening, covariance = (pack[key].copy() for key in ("train_mean", "whitening", "training_covariance"))
    expected_mean = vectors[plan["train_indices"]].mean(0)
    residual = vectors[plan["train_indices"]] - expected_mean
    if mean.shape != (96,) or whitening.shape != (96, 96) or not np.array_equal(mean, expected_mean) or not np.array_equal(covariance, residual.T @ residual / 21):
        raise ValueError("saved transform is not exactly the original training22 fit")
    if not np.isfinite(whitening).all():
        raise ValueError("nonfinite frozen transform")
    return dict(export=export, manifest=manifest, vectors=vectors, train=plan["train_indices"], mean=mean,
                whitening=whitening, transform_path=transform_path)


def _prepare(np, pack_path, manifest_path, out, control_prep, control_seconds):
    controls, prior = load_controls(np, pack_path, manifest_path), verified_prior(np)
    bank = ordered_forward_bank(np, controls)
    out = Path(out)
    protected_paths = [EXPORT / "deck-embeddings.json", EXPORT / "deck-embeddings.manifest.json", DATA / "real-decks.npz", DATA / "real-decks.manifest.json",
                       prior["transform_path"], GEOMETRY / "result.json", GEOMETRY / "receipt.json", GEOMETRY / "plan.json", HERE / "embedding_geometry_audit.py"]
    protected_paths += [Path(prior["manifest"][key]["path"]) for key in ("base", "supplement")]
    protected_paths += [Path(source["path"]) for source in prior["manifest"]["encoder_sources"]]
    if "v1" in controls["manifest"]:
        old = controls["manifest"]["v1"]["manifest"]
        if sha(old["path"]) != old["sha256"]:
            raise ValueError("preserved v1 failed-coverage manifest changed")
        protected_paths += [Path(old["path"]), Path(read(old["path"])["artifact"]["path"])]
    plan = dict(schema=SCHEMA, status="prepared-no-model-call", source=pin(__file__), controls=pin(pack_path), controls_manifest=pin(manifest_path),
                controls_preparation_receipt=pin(control_prep), controls_preparation_elapsed_seconds=control_seconds,
                protected=[pin(path) for path in dict.fromkeys(protected_paths)], rows=len(bank["features"]), control_rows=len(controls["features"]), training_reference_rows=22,
                row_ids=bank["ids"].tolist(), source_indices=bank["source_indices"].tolist(), reference_indices=bank["reference_indices"].tolist(),
                train_reference_indices=bank["train_reference_indices"].tolist(), control_indices=bank["control_indices"].tolist(),
                row_input_sha256=bank["row_input_sha256"], exact_unique_control_inputs=controls["exact_unique_encoded_inputs"],
                control_anchor_scope="Only kind=anchor denotes the3old original declarations; synthetic module anchors are new inputs and never old-vector parity references.",
                control_assays={key: controls["manifest"][key] for key in ("v1", "v2") if key in controls["manifest"]},
                reference_old_input_sha256=[dict(row_index=int(i), source_index=int(bank["source_indices"][i]),
                    sha256=input_row_hash(np, controls["original_features"][controls["by_source"][int(bank["source_indices"][i])]])) for i in bank["reference_indices"]],
                input_contract=dict(state=["N", 73], ids=["N", 24], features=["N", 24, 21], mask=["N", 24], own_deck=["N", 2, 207],
                                    context="exactfloat32zero73, int64zero24 IDs, float32zero24x21livefeatures/24mask; declaration originalknown+remainingunknown",
                                    anchor_tolerance_max_abs=1e-6, failure="stop and preserve outputs/receipt; no context tuning or second call"),
                representations=dict(full_z96="actual saved-model readout", initial_deck_tokens64="actual din projection+role before transformer;2roles",
                                     final_deck_tokens64="actual final lnf context tokens after two transformer layers;2roles; unknown remaining role may carry original context, never depletion information"),
                transformations=dict(full_z96=["raw", "raw_l2_unit", "frozen_train22_centered", "frozen_train22_centered_l2_unit", "frozen_train22_alpha.1_whitened", "frozen_train22_alpha.1_whitened_l2_unit"],
                                     original_final_deck_token64=["raw", "l2_unit", "train22_centered", "train22_centered_l2_unit", "train22_alpha.1_whitened", "train22_alpha.1_whitened_l2_unit"],
                                     original_branch_fit="mean/covariance from22training references captured in this sameforward only; unbiased denominator21, Creg=.9C+.1trace(C)/64I",
                                     other_role_and_initial_tokens=["raw", "l2_unit; diagnostic export only, not retrieval candidates"],
                                     frozen_transform=pin(prior["transform_path"]), train_indices=prior["train"], control_labels_used_for_fitting=False),
                hooks="observe initial context and final lnf returned values without altering operations; encode/forward exactly once",
                bounds=dict(neural_forward_attempts=1, max_batch_rows=64, embedding_slice_wall_seconds=20, embedding_slice_cpu_seconds=20,
                            preparation_slice_seconds=20, metrics_slice_seconds=20,
                            parent_shared_active_seconds=60, parent_scope="prep20+singleforward/transforms20+matrixmetrics20, allattempts; parent coordinates aggregate, never a fresh60second quota",
                            compute_threads=1, sampled_rss_stop_bytes=512 * 1024 * 1024,
                            optimizer_updates=0, native_calls=0, paid_jobs=0),
                scope="Vector export and fixed coordinate transforms only. No retrieval ranking, relevance labels, model tuning, semantic success or adaptive query selection.")
    write(out / "plan.json", plan)
    return plan


def preparation_elapsed(receipt):
    value = receipt.get("aggregate_preparation_attempt_seconds", receipt.get("elapsed_seconds"))
    if receipt.get("status") not in ("prepared", "completed") or type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < 20:
        raise ValueError("control preparation must have a successful timed receipt below shared20second preparation allowance")
    return float(value)


def prepare(pack_path, manifest_path, out, control_prep):
    """One timed preparation attempt; failed receipts remain and cannot reset."""
    from embedding_geometry_audit import Guard
    started, out = time.monotonic(), Path(out)
    if out.exists():
        raise ValueError("refuse to replace an existing preparation attempt")
    out.mkdir(parents=True)
    write(out / "prepare-started.json", dict(source=pin(__file__), controls=str(pack_path), manifest=str(manifest_path), controls_preparation_receipt=str(control_prep)))
    guard, control_seconds = Guard(out), 0.
    try:
        with guard:
            control_receipt = read(control_prep)
            control_seconds = preparation_elapsed(control_receipt)
            if control_receipt["artifact"]["sha256"] != sha(pack_path) or control_receipt["manifest"]["sha256"] != sha(manifest_path):
                raise ValueError("control preparation receipt does not bind this bank/manifest")
            remaining = 20 - control_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise ValueError("shared preparation allowance already exhausted")
            signal.setitimer(signal.ITIMER_REAL, remaining)
            import numpy as np
            plan = _prepare(np, pack_path, manifest_path, out, control_prep, control_seconds)
            if time.monotonic() - started + control_seconds > 20:
                raise ValueError("combined control/embedding preparation exceeded20seconds")
        receipt = dict(status="prepared", elapsed_seconds=time.monotonic() - started, control_preparation_seconds=control_seconds,
                       total_preparation_seconds=time.monotonic() - started + control_seconds, plan_sha256=sha(out / "plan.json"),
                       guard=guard.receipt(), neural_forward_attempts=0, optimizer_updates=0, native_calls=0)
    except BaseException as exc:
        write(out / "prepare-receipt.json", dict(status="failed", error=f"{type(exc).__name__}: {exc}", elapsed_seconds=time.monotonic() - started,
                   control_preparation_seconds=control_seconds, total_preparation_seconds=time.monotonic() - started + control_seconds,
                   guard=guard.receipt(), neural_forward_attempts=0, optimizer_updates=0, native_calls=0, retry_authorized=False))
        raise
    write(out / "prepare-receipt.json", receipt)
    return plan


def capture_once(np, model, tx_module, features, counters):
    """Observe production calculations; no duplicate custom forward implementation."""
    captured = {}
    original_context, original_forward, original_ln = model._initial_context, model.forward, tx_module._ln
    def context(*args, **kwargs):
        output, mask = original_context(*args, **kwargs)
        captured["initial_deck_tokens64"] = output[:, -2:].copy()
        counters["initial_context_calls"] += 1
        return output, mask
    def forward(*args, **kwargs):
        if counters["neural_forward_attempts"] >= 1:
            raise RuntimeError("the sole authorized neural forward was already attempted")
        counters["neural_forward_attempts"] += 1
        return original_forward(*args, **kwargs)
    def layer_norm(x, gain, bias):
        output = original_ln(x, gain, bias)
        if gain is model.w["lnf.g"] and bias is model.w["lnf.b"]:
            captured["final_deck_tokens64"] = output[:, -2:].copy()
            counters["final_context_capture_calls"] += 1
        return output
    model._initial_context, model.forward, tx_module._ln = context, forward, layer_norm
    try:
        n = len(features)
        captured["full_z96"] = model.encode(np.zeros((n, 73), np.float32), np.zeros((n, 24), np.int64),
                                            np.zeros((n, 24, 21), np.float32), np.zeros((n, 24), np.float32), own_deck=features)
    finally:
        model._initial_context, model.forward, tx_module._ln = original_context, original_forward, original_ln
    if counters != dict(neural_forward_attempts=1, initial_context_calls=1, final_context_capture_calls=1):
        raise RuntimeError("unexpected forward/context capture count")
    return captured


def unit(np, values):
    values = np.asarray(values, np.float64)
    norms = np.linalg.norm(values, axis=-1, keepdims=True)
    return np.divide(values, norms, out=np.zeros_like(values), where=norms > 1e-12)


def train_branch_transform(np, vectors, train):
    """Frozen alpha.1 training-reference-only transform; no control statistics."""
    training = np.asarray(vectors, np.float64)[train]
    if training.shape != (22, 64) or not np.isfinite(training).all():
        raise ValueError("branch transform requires exactly22 finite64d training rows")
    mean = training.mean(0)
    residual = training - mean
    covariance = residual.T @ residual / 21
    eigen, eigenvectors = np.linalg.eigh(covariance)
    if eigen[-1] > 0 and eigen[0] < -eigen[-1] * 1e-10:
        raise ValueError("unexpected negative branch covariance eigenvalue")
    eigen = np.maximum(eigen, 0)
    ridge = .9 * eigen + .1 * eigen.sum() / 64
    if not np.all(ridge > 0):
        raise ValueError("zero-variance branch cannot be whitened; no fallback tuning")
    whitening = (eigenvectors * (1 / np.sqrt(ridge))) @ eigenvectors.T
    return dict(train_mean=mean, training_covariance=covariance, regularized_eigenvalues=ridge, whitening=whitening)


def execute(plan_path):
    from embedding_geometry_audit import Guard
    plan_path = Path(plan_path)
    out, plan = plan_path.parent, read(plan_path)
    if (out / "attempt-started.json").exists():
        raise ValueError("the sole planned attempt already started; no replay")
    counters = dict(neural_forward_attempts=0, initial_context_calls=0, final_context_capture_calls=0)
    guard = Guard(out)
    write(out / "attempt-started.json", dict(plan_sha256=sha(plan_path), counters=counters))
    try:
        with guard:
            import numpy as np
            preparation = read(out / "prepare-receipt.json")
            if preparation["status"] != "prepared" or preparation["plan_sha256"] != sha(plan_path) or preparation["total_preparation_seconds"] > 20:
                raise ValueError("successful within-budget frozen preparation receipt required")
            if sha(plan["controls_preparation_receipt"]["path"]) != plan["controls_preparation_receipt"]["sha256"]:
                raise ValueError("control preparation receipt changed")
            if sha(__file__) != plan["source"]["sha256"]:
                raise ValueError("prepared source changed")
            for item in [*plan["protected"], plan["controls"], plan["controls_manifest"]]:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("prepared input changed: " + item["path"])
            controls = load_controls(np, plan["controls"]["path"], plan["controls_manifest"]["path"])
            bank = ordered_forward_bank(np, controls)
            prior = verified_prior(np)
            if bank["row_input_sha256"] != plan["row_input_sha256"] or len(bank["features"]) != plan["rows"]:
                raise ValueError("prepared row-level input bytes differ")
            sys.path.insert(0, str(HERE.parent))
            import own_deck_model as D
            weights, metadata = D.load_extended(prior["manifest"]["base"]["path"], prior["manifest"]["supplement"]["path"])
            model = D.NumpyOwnDeckTx(weights, metadata)
            captured = capture_once(np, model, D.X, bank["features"], counters)
            n = len(bank["features"])
            for key, shape in (("full_z96", (n, 96)), ("initial_deck_tokens64", (n, 2, 64)), ("final_deck_tokens64", (n, 2, 64))):
                if captured[key].shape != shape or captured[key].dtype != np.float32 or not np.isfinite(captured[key]).all():
                    raise ValueError("invalid actual captured representation: " + key)
            np.savez_compressed(out / "captured.partial.npz", **captured, row_ids=bank["ids"], source_indices=bank["source_indices"])
            old_by_source = {row["source_index"]: i for i, row in enumerate(prior["export"]["rows"])}
            anchors = []
            for index in bank["reference_indices"]:
                source = int(bank["source_indices"][index])
                expected = prior["vectors"][old_by_source[source]].astype(np.float32)
                maximum = float(abs(captured["full_z96"][index] - expected).max())
                anchors.append(dict(row_id=str(bank["ids"][index]), source_index=source, max_abs_error=maximum, input_sha256=bank["row_input_sha256"][index]))
            if max(row["max_abs_error"] for row in anchors) > plan["input_contract"]["anchor_tolerance_max_abs"]:
                write(out / "anchor-failure.json", dict(anchors=anchors))
                raise ValueError("training/anchor reproduction exceeds fixed1e-6 tolerance; no retry")
            z = captured["full_z96"].astype(np.float64)
            centered = z - prior["mean"]
            whitened = centered @ prior["whitening"]
            original_branch = captured["final_deck_tokens64"][:, 0].astype(np.float64)
            branch_transform = train_branch_transform(np, original_branch, bank["train_reference_indices"])
            branch_centered = original_branch - branch_transform["train_mean"]
            branch_whitened = branch_centered @ branch_transform["whitening"]
            np.savez_compressed(out / "branch-train-transform.npz", **branch_transform)
            vectors = dict(captured, raw_l2_unit=unit(np, z), frozen_train22_centered=centered,
                           frozen_train22_centered_l2_unit=unit(np, centered), frozen_train22_alpha01_whitened=whitened,
                           frozen_train22_alpha01_whitened_l2_unit=unit(np, whitened),
                           initial_deck_tokens64_l2_unit=unit(np, captured["initial_deck_tokens64"]), final_deck_tokens64_l2_unit=unit(np, captured["final_deck_tokens64"]),
                           original_branch64=original_branch, original_branch64_l2_unit=unit(np, original_branch),
                           original_branch64_train22_centered=branch_centered, original_branch64_train22_centered_l2_unit=unit(np, branch_centered),
                           original_branch64_train22_alpha01_whitened=branch_whitened, original_branch64_train22_alpha01_whitened_l2_unit=unit(np, branch_whitened))
            np.savez_compressed(out / "vectors.npz", **vectors, row_ids=bank["ids"], source_indices=bank["source_indices"],
                                train_reference_indices=bank["train_reference_indices"], control_indices=bank["control_indices"])
            invariance = []
            for first in range(n):
                for second in range(first):
                    if np.array_equal(bank["features"][first], bank["features"][second]):
                        errors = {key: float(abs(captured[key][first] - captured[key][second]).max()) for key in captured}
                        if max(errors.values()) > 1e-6:
                            raise ValueError("identical actual inputs produced different captured representations")
                        invariance.append(dict(first=str(bank["ids"][first]), second=str(bank["ids"][second]), max_abs_errors=errors))
            for item in [*plan["protected"], plan["controls"], plan["controls_manifest"], plan["controls_preparation_receipt"]]:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("protected old artifact changed during export")
            result = dict(schema=SCHEMA, status="completed", plan_sha256=sha(plan_path), source_sha256=sha(__file__),
                          artifact=pin(out / "vectors.npz"), controls_manifest=plan["controls_manifest"], rows=n,
                          control_rows=len(controls["features"]), exact_unique_control_inputs=controls["exact_unique_encoded_inputs"], reproduced_reference_rows=len(anchors),
                          anchors=anchors, exact_input_collision_invariance=invariance,
                          tensors={name: dict(shape=list(value.shape), dtype=str(value.dtype)) for name, value in vectors.items()},
                          full_z_frozen_train_transform=pin(prior["transform_path"]), full_z_transform_refits=0,
                          original_branch_train22_transform=pin(out / "branch-train-transform.npz"), branch_transform_fits=1, branch_control_rows_used_for_fit=0, counters=counters,
                          model_forward_calls=1, optimizer_updates=0, native_calls=0, paid_jobs=0,
                          branch_scope="Two actual role tokens, before/after joint-context transformer. Unknown remaining-role token is contextual, not a remaining-composition estimate.",
                          retrieval_metrics_computed=False, semantic_validated=False, all_protected_hashes_unchanged=True)
            write(out / "result.json", result)
        receipt = dict(schema=SCHEMA, status="completed", result=pin(out / "result.json"), plan=pin(plan_path), guard=guard.receipt(), counters=counters,
                       optimizer_updates=0, native_calls=0, paid_jobs=0)
    except BaseException as exc:
        receipt = dict(schema=SCHEMA, status="failed", error=f"{type(exc).__name__}: {exc}", plan=pin(plan_path), guard=guard.receipt(), counters=counters,
                       optimizer_updates=0, native_calls=0, paid_jobs=0, retry_authorized=False)
        write(out / "receipt.json", receipt)
        raise
    write(out / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", type=Path)
    parser.add_argument("--controls", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--controls-prep-receipt", type=Path)
    args = parser.parse_args()
    if args.prepare:
        if any(value is None for value in (args.controls, args.manifest, args.out, args.controls_prep_receipt)):
            parser.error("--prepare requires controls, manifest, controls-prep-receipt and out")
        result = prepare(args.controls, args.manifest, args.out, args.controls_prep_receipt)
    else:
        result = execute(args.execute)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
