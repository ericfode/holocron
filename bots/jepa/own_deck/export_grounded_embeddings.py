"""Publish saved ABI program vectors without importing or executing a model."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VERSION = "grounded-contrast-v1"
SPACE = "grounded-typed-action-program-z16-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    payload = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def normalized_vectors(vectors):
    vectors = np.asarray(vectors)
    if vectors.dtype != np.float32 or vectors.shape != (12, 16) or not np.isfinite(vectors).all():
        raise ValueError("expected twelve finite float32 saved program vectors")
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    units = np.divide(vectors.astype(np.float64), norms[:, None], out=np.zeros_like(vectors, dtype=np.float64), where=norms[:, None] > 1e-12)
    return norms, units


def verified_bundle(fit, dataset_manifest, guard):
    fit, dataset_manifest, guard = Path(fit), Path(dataset_manifest), Path(guard)
    result = read(fit / "result.json")
    if result["status"] != "completed" or result["counts"] != dict(optimizer_updates=2400, heldout_validation_batches=8, usage_batches=2, abi_embedding_batches=4):
        raise ValueError("completed fixed-allocation fit receipt required")
    receipt = read(guard)
    if receipt["status"] != "completed" or receipt["completed_or_reserved_updates"] != 2400:
        raise ValueError("completed shared guard receipt required")
    arm = next(a for a in result["arms"] if a["arm"] == "correct-ir")
    paths = dict(checkpoint=fit / "correct-ir.npz", contract=fit / "correct-ir-contract.json", golden=fit / "correct-ir-golden.npz")
    for name, path in paths.items():
        if sha(path) != arm[name + "_sha256"]:
            raise ValueError(name + " hash mismatch")
    contract = read(paths["contract"])
    if contract["checkpoint_sha256"] != sha(paths["checkpoint"]) or contract["golden_sha256"] != sha(paths["golden"]):
        raise ValueError("contract/checkpoint/golden linkage mismatch")
    manifest = read(dataset_manifest)
    dataset = Path(manifest["artifact"]["path"])
    if sha(dataset_manifest) != result["manifest_sha256"] or sha(dataset_manifest) != contract["source_pins"]["manifest_sha256"]:
        raise ValueError("dataset manifest linkage mismatch")
    if sha(dataset) != manifest["artifact"]["sha256"] or sha(dataset) != result["dataset_sha256"] or sha(dataset) != contract["source_pins"]["dataset_sha256"]:
        raise ValueError("native dataset linkage mismatch")
    model_source = HERE / "grounded_contrast_model.py"
    if sha(model_source) != result["source_sha256"] or sha(model_source) != contract["source_pins"]["model_sha256"]:
        raise ValueError("executed model source mismatch")
    with np.load(paths["golden"], allow_pickle=False) as pack:
        codes = pack["known_program_codes"].astype(str).tolist()
        vector_bank = pack["semantic_program_vectors"].copy()
        statuses = pack["bank_status"].copy()
    if codes != sorted(manifest["programs"]) or len(codes) != 12 or vector_bank.shape != (16, 16):
        raise ValueError("saved program order/shape mismatch")
    if not np.array_equal(statuses[:12], np.tile([1, 0, 0, 0, 0], (12, 1))) or not np.array_equal(statuses[12:], np.eye(5)[1:]):
        raise ValueError("known versus diagnostic status slots differ")
    vectors = vector_bank[:12].copy()
    norms, units = normalized_vectors(vectors)
    split = manifest["identity_program_split"]
    if len(split["train_codes"]) != 10 or len(split["heldout_codes"]) != 2 or set(split["train_codes"]) & set(split["heldout_codes"]) or set(codes) != set(split["train_codes"]) | set(split["heldout_codes"]):
        raise ValueError("ten/two identity split mismatch")
    return dict(result=result, arm=arm, paths=paths, contract=contract, manifest=manifest, dataset=dataset,
                dataset_manifest=dataset_manifest, guard=guard, codes=codes, vectors=vectors, norms=norms, units=units)


def schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Saved grounded typed-action program embeddings v1",
            "type": "object", "required": ["schema", "space_id", "dimension", "semantic_validated", "rows"],
            "properties": {"schema": {"const": "jepa-card-program-embedding-export/2"}, "space_id": {"const": SPACE},
                           "dimension": {"const": 16}, "semantic_validated": {"const": False},
                           "rows": {"type": "array", "minItems": 12, "maxItems": 12, "items": {"type": "object", "required": ["id", "vector", "unit_vector", "l2_norm", "held_out_identity"],
                                     "properties": {"vector": {"type": "array", "minItems": 16, "maxItems": 16, "items": {"type": "number"}},
                                                    "unit_vector": {"type": "array", "minItems": 16, "maxItems": 16, "items": {"type": "number"}},
                                                    "held_out_identity": {"type": "boolean"}}}}}}


def export(fit, dataset_manifest, guard, index_path):
    started = time.monotonic()
    bundle = verified_bundle(fit, dataset_manifest, guard)
    index_path = Path(index_path)
    before = index_path.read_bytes()
    index = json.loads(before)
    if index["schema"] != "jepa-embedding-browser-index/1":
        raise ValueError("unknown stable browser index schema")
    out = index_path.parent / VERSION
    if out.exists():
        raise ValueError("versioned export already exists; preserve it")
    # Preserve all old vector/manifest bytes; only the final index pointer changes.
    protected = {}
    for space in index["spaces"].values():
        for name in ("vectors_path", "manifest_path"):
            if space.get(name):
                protected[space[name]] = sha(space[name])
    manifest, contract, split = bundle["manifest"], bundle["contract"], bundle["manifest"]["identity_program_split"]
    rows = []
    for position, code in enumerate(bundle["codes"]):
        program = manifest["programs"][code]
        held = code in split["heldout_codes"]
        rows.append(dict(id=code, name=code, canonical_card_id=program["canonical_card_id"], aliases=program["aliases"],
                         ability_path=["abilities", program["side"], program["index"]], program_group_id=program["program_group_id"],
                         split="heldout-program" if held else "training-program", held_out_identity=held, seen_in_training=not held,
                         training_state_families=[] if held else list(range(10)), evaluation_state_families=list(range(14)) if held else list(range(10, 14)),
                         sourceHash=program["source_hash"], sourcePath=program["source_path"],
                         vector=bundle["vectors"][position].tolist(), unit_vector=bundle["units"][position].tolist(),
                         l2_norm=float(bundle["norms"][position]), cosine_available=bool(bundle["norms"][position] > 1e-12)))
    out.mkdir(parents=True, exist_ok=False)
    (out / "previous-index.json").write_bytes(before)
    artifact = out / "card-embeddings.json"
    write(artifact, dict(schema="jepa-card-program-embedding-export/2", version=VERSION, space_id=SPACE, entity_type="card", dimension=16,
                         semantic_validated=False, vector_origin="Saved correct-ir ABI forward's actual encode_program_bank output; no export forward",
                         context_conditioning="Static selected-program vector before public context/candidate fusion; does not adapt to a current board.", rows=rows))
    write(out / "schema.json", schema())
    limitations = ["Twelve selected already-native-supported activated programs, not whole-card/persistent/deck representations.",
                   "Ten program identities trained, two held out; four held-out state families. Single-seed small native-fixture evidence only.",
                   "Proximity/cosine/Euclidean neighborhoods have not been independently behaviorally validated; semantic_validated remains false.",
                   "Heldout programs target disjoint domains, limiting same-candidate committed-delta comparisons; all joint per-head metrics have low-support flags.",
                   "These16d vectors are a new checkpoint/encoder space; distances across old two-card or96d deck spaces are undefined."]
    export_manifest = dict(schema="jepa-grounded-card-embedding-manifest/1", version=VERSION, semantic_validated=False,
                           artifact=pin(artifact), schema_artifact=pin(out / "schema.json"),
                           checkpoint=pin(bundle["paths"]["checkpoint"]), saved_golden=pin(bundle["paths"]["golden"]), encoder_contract=pin(bundle["paths"]["contract"]),
                           fit_result=pin(Path(fit) / "result.json"), guard_receipt=pin(guard), dataset=pin(bundle["dataset"]), dataset_manifest=pin(dataset_manifest),
                           model_source=pin(HERE / "grounded_contrast_model.py"), export_source=pin(__file__),
                           training_commit=bundle["result"]["commit"], source_revision=manifest["source_revision"], vocabulary_sha256=contract["vocabulary_sha256"],
                           program_order=bundle["codes"], training_programs=split["train_codes"], heldout_programs=split["heldout_codes"],
                           raw_tensor=dict(shape=[12, 16], dtype="float32", little_endian_bytes_sha256=hashlib.sha256(bundle["vectors"].astype("<f4").tobytes()).hexdigest()),
                           normalization=dict(raw="unchanged saved float32 vectors", unit="float64 raw/L2norm where norm>1e-12; otherwise zeros and cosine unavailable", fitted=False),
                           optimizer_updates_during_export=0, model_forward_calls=0, native_engine_calls=0, paid_jobs=0, paid_spend_usd=0,
                           original_capture=dict(per_arm_reference_batches=1, total_fit_reference_batches=4, combined_status_and_embedding_batch=True),
                           previous_index=pin(out / "previous-index.json"), preserved_files=protected, limitations=limitations)
    manifest_path = out / "card-embeddings.manifest.json"
    write(manifest_path, export_manifest)
    # Verify serialization, raw coordinates and linked artifacts before publication.
    saved = read(artifact)
    if not np.array_equal(np.asarray([r["vector"] for r in saved["rows"]], np.float32), bundle["vectors"]):
        raise ValueError("serialized raw coordinates differ")
    for path, expected in protected.items():
        if sha(path) != expected:
            raise ValueError("legacy artifact changed during export")
    if index_path.read_bytes() != before:
        raise ValueError("concurrent stable index change; preserve staged export and stop")
    new_index = copy.deepcopy(index)
    new_index.setdefault("space_history", {}).setdefault("card", []).append(copy.deepcopy(index["spaces"]["card"]))
    new_index["updated_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_index["spaces"]["card"] = dict(id=SPACE, version=VERSION, entity_type="card", status="available", entity_count=12, dimension=16,
                                        vector_kind="actual saved learned typed-program encoder output", semantic_validated=False,
                                        relative_file=str(artifact.relative_to(index_path.parent)), vectors_path=str(artifact), manifest_path=str(manifest_path),
                                        artifact_sha256=sha(artifact), manifest_sha256=sha(manifest_path), checkpoint=export_manifest["checkpoint"],
                                        limitation="Small12-program native-fixture contrast with2heldout identities; no validated neighborhood/strength claim.")
    write(index_path, new_index)
    if read(index_path)["spaces"]["deck"] != index["spaces"]["deck"]:
        raise AssertionError("deck pointer changed")
    receipt = dict(schema="jepa-grounded-embedding-export-receipt/1", status="completed", artifact=pin(artifact), manifest=pin(manifest_path),
                   stable_index=pin(index_path), previous_index=pin(out / "previous-index.json"), elapsed_seconds=time.monotonic() - started,
                   model_forward_calls=0, optimizer_updates=0, native_engine_calls=0, paid_jobs=0, all_legacy_files_unchanged=True)
    write(out / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.fit, args.dataset_manifest, args.guard, args.index), indent=2))


if __name__ == "__main__":
    main()
