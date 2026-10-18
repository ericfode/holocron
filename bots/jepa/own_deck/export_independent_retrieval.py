"""Serialize the one saved independent-control batch; never imports a model.

Each representation/transform is a separate browser space. No ranking, new
transform fit, neural forward, optimizer update or native operation occurs.
"""
import argparse
import copy
import datetime
import hashlib
import json
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_key] = "1"
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VERSION = "independent-controls-v1"
SPACES = (
    ("full-raw-z96", "full_z96", "raw_l2_unit", 96, "Full declaration-context readout, raw"),
    ("full-centered-z96", "frozen_train22_centered", "frozen_train22_centered_l2_unit", 96, "Full readout, frozen training22 centering"),
    ("full-whitened-z96", "frozen_train22_alpha01_whitened", "frozen_train22_alpha01_whitened_l2_unit", 96, "Full readout, frozen training22 alpha.1 whitening"),
    ("original-token-raw-z64", "original_branch64", "original_branch64_l2_unit", 64, "Final original-deck context token, raw"),
    ("original-token-centered-z64", "original_branch64_train22_centered", "original_branch64_train22_centered_l2_unit", 64, "Final original-deck token, training22 centering"),
    ("original-token-whitened-z64", "original_branch64_train22_alpha01_whitened", "original_branch64_train22_alpha01_whitened_l2_unit", 64, "Final original-deck token, training22 alpha.1 whitening"),
)


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


def export(independent, index_path):
    independent, index_path = Path(independent), Path(index_path)
    embedding = independent / "embedding-run"
    result = read(embedding / "result.json")
    receipt = read(embedding / "receipt.json")
    metrics = read(independent / "metrics-run/result.json")
    if result["status"] != "completed" or receipt["status"] != "completed" or metrics["status"] != "completed":
        raise ValueError("completed frozen embedding and metrics receipts required")
    if result["counters"] != dict(neural_forward_attempts=1, initial_context_calls=1, final_context_capture_calls=1) or result["rows"] != 60 or result["control_rows"] != 38:
        raise ValueError("expected the sole60row batch with38controls")
    vector_path = Path(result["artifact"]["path"])
    if sha(vector_path) != result["artifact"]["sha256"] or sha(vector_path) != metrics["vector_artifact"]["sha256"]:
        raise ValueError("saved vectors/result/metrics hash linkage differs")
    if sha(embedding / "result.json") != receipt["result"]["sha256"]:
        raise ValueError("embedding receipt linkage differs")
    control_path = Path(result["controls_manifest"]["path"])
    if sha(control_path) != result["controls_manifest"]["sha256"]:
        raise ValueError("control provenance changed")
    control = read(control_path)
    old_path = index_path.parent / "deck-embeddings.json"
    old_manifest_path = index_path.parent / "deck-embeddings.manifest.json"
    old, old_manifest = read(old_path), read(old_manifest_path)
    if sha(old_path) != old_manifest["artifact"]["sha256"]:
        raise ValueError("old27deck export changed")
    old_by_source = {row["source_index"]: row for row in old["rows"]}
    with np.load(vector_path, allow_pickle=False) as pack:
        ids = pack["row_ids"].astype(str).tolist()
        source_indices = pack["source_indices"].tolist()
        train_indices, control_indices = pack["train_reference_indices"].tolist(), pack["control_indices"].tolist()
        arrays = {key: pack[key].copy() for _, key, unit_key, _, _ in SPACES for key in (key, unit_key)}
    if train_indices != list(range(22)) or control_indices != list(range(22, 60)) or ids[22:] != [row["id"] for row in control["rows"]]:
        raise ValueError("saved row roles/order differ")
    if len(set(ids)) != 60:
        raise ValueError("duplicate exported row IDs")
    for _, key, unit_key, dim, _ in SPACES:
        if any(arrays[k].shape != (60, dim) or not np.isfinite(arrays[k]).all() for k in (key, unit_key)):
            raise ValueError("invalid saved representation " + key)
    before = index_path.read_bytes()
    index = json.loads(before)
    out = index_path.parent / VERSION
    if out.exists():
        raise FileExistsError("preserve the versioned export; no overwrite")
    protected = {str(old_path): sha(old_path), str(old_manifest_path): sha(old_manifest_path)}
    for existing in index["spaces"].values():
        for key in ("vectors_path", "manifest_path"):
            if existing.get(key):
                protected[existing[key]] = sha(existing[key])
    for key in ("base", "supplement"):
        path = old_manifest[key]["path"]
        if sha(path) != old_manifest[key]["sha256"]:
            raise ValueError("frozen checkpoint changed")
        protected[path] = sha(path)
    out.mkdir()
    (out / "previous-index.json").write_bytes(before)
    common = []
    for position, identity in enumerate(ids):
        source = source_indices[position]
        original = old_by_source[source]
        if position < 22:
            row = copy.deepcopy(original)
            row.update(id=identity, name="[training reference] " + original["name"], kind="training-reference", row_role="training-reference", split="train", assay="training-reference",
                       synthetic=False, historical_original_reference=True, inherited_partition="train", anchor_id=None, module_id=None)
        else:
            row = copy.deepcopy(control["rows"][position - 22])
            row.update(name=original["name"] + " / " + identity, row_role="independent-control", split="independent-control",
                       inherited_partition="validation", synthetic=row.get("assay") == "v2-synthetic", historical_original_reference=row["kind"] == "anchor")
            row["background_source_deck_id"] = original["id"]
        row["source_index"] = source
        row["cards"] = [dict(id=code, count=count) for code, count in sorted(row["canonical_card_counts"].items())]
        row["total_count"] = sum(row["canonical_card_counts"].values())
        row["original_known"], row["remaining_known"] = True, False
        for key in ("vector", "unit_vector", "l2_norm", "cosine_available"):
            row.pop(key, None)
        common.append(row)
    artifacts, pointers = [], {}
    manifest_path = out / "manifest.json"
    for slug, key, unit_key, dim, label in SPACES:
        space_id = "independent-controls-v1-" + slug
        rows = []
        for position, metadata in enumerate(common):
            rows.append(dict(metadata, vector=arrays[key][position].tolist(), unit_vector=arrays[unit_key][position].tolist(),
                             l2_norm=float(np.linalg.norm(arrays[key][position].astype(np.float64))), cosine_available=bool(np.any(arrays[unit_key][position]))))
        path = out / (slug + ".json")
        write(path, dict(schema="jepa-deck-embedding-export/1", version=VERSION, space_id=space_id, entity_type="deck", dimension=dim,
                         semantic_validated=False, representation=label, vector_origin="Copied from the previously saved sole60row forward and frozen transforms; no export forward",
                         compatible_distance_scope="Only rows within this exact space_id. Never compare coordinates/distances across transforms, full96/originaltoken64, older card16 or other spaces.",
                         rows=rows))
        serialized = read(path)["rows"]
        if not np.array_equal(np.asarray([row["vector"] for row in serialized], dtype=arrays[key].dtype), arrays[key]) or not np.array_equal(np.asarray([row["unit_vector"] for row in serialized]), arrays[unit_key]):
            raise ValueError("saved-to-JSON vector coordinate roundtrip differs")
        artifacts.append(dict(id=space_id, vector_key=key, unit_vector_key=unit_key, dimension=dim, artifact=pin(path), rows=60,
                              raw_tensor_dtype=str(arrays[key].dtype), raw_tensor_bytes_sha256=hashlib.sha256(arrays[key].tobytes()).hexdigest()))
        pointers["independent_controls_" + slug.replace("-", "_")] = dict(id=space_id, entity_type="deck", status="available", version=VERSION,
                       entity_count=60, training_reference_count=22, independent_control_count=38, dimension=dim, vector_kind=label, semantic_validated=False,
                       relative_file=str(path.relative_to(index_path.parent)), vectors_path=str(path), artifact_sha256=sha(path), manifest_path=str(manifest_path),
                       limitation="Small independent conditional mechanics-proxy assay; synthetic module anchors are not authored originals. No semantic-neighbor, deck-quality or strength validation.")
    export_manifest = dict(schema="jepa-independent-retrieval-browser-export/1", version=VERSION, semantic_validated=False,
                           artifacts=artifacts, rows=dict(total=60, training_references=22, controls=38, v1_authored_cohort=17, v2_synthetic_cohort=21,
                                                          old_historical_references=25, new_synthetic_module_anchors=3),
                           sources=dict(saved_vectors=pin(vector_path), embedding_result=pin(embedding / "result.json"), embedding_receipt=pin(embedding / "receipt.json"),
                                        embedding_plan=pin(embedding / "plan.json"), metrics_result=pin(independent / "metrics-run/result.json"), metrics_plan=pin(independent / "metrics-run/plan.json"),
                                        controls=pin(control_path), frozen_full_transform=result["full_z_frozen_train_transform"], original_branch_transform=result["original_branch_train22_transform"],
                                        original27export=pin(old_path), original27manifest=pin(old_manifest_path), base=old_manifest["base"], supplement=old_manifest["supplement"], export_source=pin(__file__)),
                           normalization="Raw/transformed vectors and their corresponding already-saved L2-unit vectors are copied separately. No normalization/whitening refit during export.",
                           previous_index=pin(out / "previous-index.json"), protected_before=protected,
                           model_forward_calls=0, optimizer_updates=0, native_calls=0, paid_jobs=0,
                           limitations=["Every representation/transform is a distinct coordinate space; cross-space distances are undefined.",
                                        "Training references are calibration/provenance rows, not extra independent control roots.",
                                        "V1 failed its primary coverage gate. V2 uses planted synthetic anchors and a fixed structural IR proxy; neither establishes deck quality.",
                                        "Exactly3newmodule-anchor rows are newsynthetic declarations, not oldvector parity references.",
                                        "The unknown remaining-role token was excluded from retrieval and is not exported as a remaining-composition representation."])
    write(manifest_path, export_manifest)
    for path, digest in protected.items():
        if sha(path) != digest:
            raise ValueError("protected old artifact changed during export")
    if index_path.read_bytes() != before:
        raise ValueError("stable index changed concurrently; leave staged exports, do not publish")
    updated = copy.deepcopy(index)
    if set(pointers) & set(updated["spaces"]):
        raise ValueError("new versioned space keys already present")
    for pointer in pointers.values():
        pointer["manifest_sha256"] = sha(manifest_path)
    updated["spaces"].update(pointers)
    updated["updated_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(index_path, updated)
    output = dict(schema="jepa-independent-retrieval-browser-export-receipt/1", status="completed", manifest=pin(manifest_path), stable_index=pin(index_path),
                  previous_index=pin(out / "previous-index.json"), artifacts=artifacts, old_files_unchanged=True, old_space_pointers_unchanged=True,
                  added_spaces=6, rows_per_space=60, model_forward_calls=0, optimizer_updates=0, native_calls=0, paid_jobs=0)
    write(out / "receipt.json", output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--independent", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.independent, args.index)
    print(json.dumps(dict(status=result["status"], manifest=result["manifest"], stable_index=result["stable_index"], added_spaces=6, rows_per_space=60, model_forward_calls=0), indent=2))


if __name__ == "__main__":
    main()
