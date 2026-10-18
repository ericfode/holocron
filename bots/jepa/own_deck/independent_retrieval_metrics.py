"""Freeze score-blind retrieval metrics, then analyze one saved vector artifact.

Preparation reads lineage and hashes only. Execution performs matrix arithmetic;
it never imports a neural model, changes transforms, or supplies semantic labels.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EPSILON = 1e-10
SPACES = ("full_z96", "frozen_train22_centered", "frozen_train22_alpha01_whitened",
          "original_branch64", "original_branch64_train22_centered", "original_branch64_train22_alpha01_whitened")
BASELINES = ("canonical_count_jaccard", "printed_five_group", "typed_ir_proxy_oracle")
GROUPS = ((8, 11), (11, 16), (16, 25), (25, 35), (35, 41))
SCHEMA = "jepa-independent-retrieval-metrics/1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def comparison_groups(rows):
    anchors, anchors_by_id, groups = {}, {}, {}
    for index, row in enumerate(rows):
        source = row["source_index"]
        if row["kind"] == "anchor":
            if source in anchors:
                raise ValueError("duplicate source anchor")
            anchors[source] = index
        if row["kind"] in ("anchor", "synthetic-anchor", "module-anchor"):
            if row["id"] in anchors_by_id:
                raise ValueError("duplicate anchor identity")
            anchors_by_id[row["id"]] = index
    for index, row in enumerate(rows):
        source = row["source_index"]
        if row["kind"] in ("ir-near", "ir-far"):
            lineage = row["lineage"]
            assay = row.get("assay", lineage.get("assay", "v1-authored"))
            anchor_id = row.get("anchor_id", lineage.get("anchor_id"))
            if anchor_id is None:
                if assay != "v1-authored":
                    raise ValueError("synthetic comparisons require explicit anchor_id")
                anchor_id = rows[anchors[source]]["id"]
            if anchor_id not in anchors_by_id or rows[anchors_by_id[anchor_id]]["source_index"] != source:
                raise ValueError("comparison anchor is absent or belongs to another source")
            module = row.get("module_id", lineage.get("module_id"))
            key = assay, anchor_id, source, lineage["source_card"], module, lineage["copies"]
            group = groups.setdefault(key, {})
            if row["kind"] in group:
                raise ValueError("duplicate near/far comparison")
            group[row["kind"]] = index
    if set(anchors) != {10, 14, 25}:
        raise ValueError("three frozen held-out anchors required")
    comparisons = []
    for (assay, anchor_id, source, slot, module, dose), group in sorted(groups.items(), key=lambda item: str(item[0])):
        if set(group) != {"ir-near", "ir-far"} or dose not in (1, 2):
            raise ValueError("incomplete or unexpected comparison")
        near, far = rows[group["ir-near"]], rows[group["ir-far"]]
        if near["lineage"]["stratum"] != far["lineage"]["stratum"]:
            raise ValueError("mixed strict/fallback comparison")
        if near["count_baseline"] != far["count_baseline"]:
            raise ValueError("near/far canonical overlap differs")
        if near["mechanical_labels"]["ir_only"]["distance"] >= far["mechanical_labels"]["ir_only"]["distance"]:
            raise ValueError("declared proxy order differs")
        comparisons.append(dict(assay=assay, anchor_id=anchor_id, module_id=module,
                                source_index=source, source_card=slot, dose=dose,
                                stratum=near["lineage"]["stratum"], anchor=anchors_by_id[anchor_id],
                                near=group["ir-near"], far=group["ir-far"]))
    if not comparisons:
        raise ValueError("no score-blind comparisons available")
    return comparisons


def order_result(near, far, epsilon=EPSILON):
    if near is None or far is None:
        return dict(near_score=near, far_score=far, gap=None, result="unknown", near_rank=None,
                    far_rank=None, near_reciprocal_rank=None, half_credit=None)
    gap = float(near - far)
    result = "near" if gap > epsilon else "far" if gap < -epsilon else "tie"
    rank = 1. if result == "near" else 2. if result == "far" else 1.5
    return dict(near_score=float(near), far_score=float(far), gap=gap, result=result,
                near_rank=rank, far_rank=3-rank, near_reciprocal_rank=1/rank,
                half_credit=1. if result == "near" else 0. if result == "far" else .5)


def aggregate(records):
    """Equal slots within family, then equal source families; no row pooling."""
    known = [r for r in records if r["result"] != "unknown"]
    slot_groups = {}
    for row in known:
        slot_groups.setdefault((row["source_index"], row.get("anchor_id"), row["source_card"], row.get("module_id")), []).append(row)
    slots = [dict(source_index=source, anchor_id=anchor, source_card=slot, module_id=module, comparisons=len(values),
                  half_credit=sum(r["half_credit"] for r in values)/len(values),
                  near_rank=sum(r["near_rank"] for r in values)/len(values),
                  near_reciprocal_rank=sum(r["near_reciprocal_rank"] for r in values)/len(values),
                  mean_gap=sum(r["gap"] for r in values)/len(values))
             for (source, anchor, slot, module), values in sorted(slot_groups.items(), key=lambda item: str(item[0]))]
    families = []
    for source in sorted({s["source_index"] for s in slots}):
        values = [s for s in slots if s["source_index"] == source]
        families.append(dict(source_index=source, slots=len(values),
                             half_credit=sum(s["half_credit"] for s in values)/len(values),
                             near_rank=sum(s["near_rank"] for s in values)/len(values),
                             near_reciprocal_rank=sum(s["near_reciprocal_rank"] for s in values)/len(values),
                             mean_gap=sum(s["mean_gap"] for s in values)/len(values)))
    mean = lambda values: sum(values)/len(values) if values else None
    return dict(comparisons=len(records), known_comparisons=len(known), unknown_comparisons=len(records)-len(known),
                near_wins=sum(r["result"] == "near" for r in known), far_wins=sum(r["result"] == "far" for r in known),
                ties=sum(r["result"] == "tie" for r in known), source_families=len(families), unique_slots=len(slots),
                slot_macro_half_credit=mean([s["half_credit"] for s in slots]),
                family_macro_half_credit=mean([s["half_credit"] for s in families]),
                slot_macro_near_rank=mean([s["near_rank"] for s in slots]),
                family_macro_near_rank=mean([s["near_rank"] for s in families]),
                slot_macro_near_reciprocal_rank=mean([s["near_reciprocal_rank"] for s in slots]),
                family_macro_near_reciprocal_rank=mean([s["near_reciprocal_rank"] for s in families]),
                family_macro_gap=mean([s["mean_gap"] for s in families]), slots=slots, families=families)


def prepare(manifest_path, embedding_plan_path, out):
    started = time.monotonic()
    manifest, embedding_plan = read(manifest_path), read(embedding_plan_path)
    if sha(manifest_path) != embedding_plan["controls_manifest"]["sha256"]:
        raise ValueError("embedding/control plan lineage differs")
    if (Path(embedding_plan_path).parent / "vectors.npz").exists():
        raise ValueError("metrics must freeze before new vector outcomes")
    comparisons = comparison_groups(manifest["rows"])
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "plan.json").exists():
        raise FileExistsError("preserve prior frozen metrics plan")
    protected = [Path(__file__), HERE / "embedding_geometry_audit.py", Path(manifest_path), Path(embedding_plan_path),
                 Path(manifest["artifact"]["path"]), ROOT / "experiments/embedding-export/deck-embeddings.json",
                 HERE / "embedding-geometry-evidence/train-transform.npz"]
    plan = dict(schema=SCHEMA, status="frozen-before-new-vector-outcomes", sources=[pin(p) for p in protected],
                controls_manifest=str(Path(manifest_path).resolve()), embedding_plan=str(Path(embedding_plan_path).resolve()),
                comparisons=comparisons, representations=list(SPACES), baselines=list(BASELINES), tie_epsilon=EPSILON,
                primary="Separate authored-v1 and synthetic-module-v2 assays; explicit anchor_id/module_id, strict-power-hp primary within each. Fallback confounded, never pooled.",
                score="anchor cosine to near minus anchor cosine to far, float64; positive means near preferred; tie abs(gap)<=1e-10; zero norm<=1e-12 unknown",
                aggregation="Report all rows/pairs, doses1/2 separately, equal-slot and equal-family macro. Midranks for ties; half-credit ties. Three source roots, nested dependent doses/slots/views.",
                printed_baseline=dict(groups=[list(g) for g in GROUPS], rule="negative equal mean of five within-group mean absolute coordinate differences, actual ownDeck original metadata"),
                ir_oracle="negative per-card fixed typed IR distance; proxy defines labels, so success is tautological structural positive control, not semantic validation",
                noise="Per-space identity/invariance cosine deficit; full96 old-anchor parity gap perturbation under same new variants; report gaps/floors, branch old-parity unavailable. Fixed epsilon is minimum floor.",
                invariance="Canonical/permutation/split/reprint views only correctness, excluded from near/far accuracy. Report all unique encoded/composition counts and all declared invariant pairs.",
                selection="No labels from reviewer examples; no method/seed/transform selection or tuning after metrics; all six latent and three baseline methods reported.",
                bounds=dict(worker_active_seconds=20, shared_retrieval_seconds=60, stages="generator20 + oneforward/transforms20 + metrics20; no compute overlap",
                            sampled_rss_bytes=512*1024*1024, compute_threads=1, neural_forwards=0, native_calls=0, optimizer_updates=0, paid_jobs=0))
    write(out / "plan.json", plan)
    write(out / "prepare-receipt.json", dict(status="prepared", elapsed_seconds=time.monotonic()-started, plan_sha256=sha(out / "plan.json"), neural_forwards=0, native_calls=0, optimizer_updates=0))
    return plan


def execute(plan_path):
    from embedding_geometry_audit import Guard
    plan_path = Path(plan_path)
    plan, out = read(plan_path), plan_path.parent
    if (out / "attempt-started.json").exists():
        raise FileExistsError("preserve attempted metrics stage; no replay")
    write(out / "attempt-started.json", dict(plan_sha256=sha(plan_path)))
    guard = Guard(out)
    try:
        with guard:
            import numpy as np
            for item in plan["sources"]:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("frozen metrics input/source changed: " + item["path"])
            manifest = read(plan["controls_manifest"])
            rows = manifest["rows"]
            embedding_dir = Path(plan["embedding_plan"]).parent
            embedding_result = read(embedding_dir / "result.json")
            if embedding_result["status"] != "completed" or embedding_result["plan_sha256"] != sha(plan["embedding_plan"]):
                raise ValueError("completed frozen single-forward artifact required")
            vector_path = Path(embedding_result["artifact"]["path"])
            if sha(vector_path) != embedding_result["artifact"]["sha256"]:
                raise ValueError("saved vector hash differs")
            with np.load(vector_path, allow_pickle=False) as bank:
                indices = bank["control_indices"].copy()
                ids = bank["row_ids"][indices].astype(str).tolist()
                if ids != [r["id"] for r in rows]:
                    raise ValueError("saved vector/control row order differs")
                values = {space: np.asarray(bank[space][indices], np.float64) for space in SPACES}
            with np.load(manifest["artifact"]["path"], allow_pickle=False) as pack:
                features = pack["deck_features"].astype(np.float64)
                if pack["row_ids"].astype(str).tolist() != ids:
                    raise ValueError("metadata/control row order differs")
            for name, value in values.items():
                if value.shape != (len(rows), 96 if name in SPACES[:3] else 64) or not np.isfinite(value).all():
                    raise ValueError("invalid saved vector space: " + name)
            def cosine(a, b):
                denominator = float(np.linalg.norm(a)*np.linalg.norm(b))
                return float(np.clip(a @ b / denominator, -1., 1.)) if denominator > 1e-24 and min(np.linalg.norm(a), np.linalg.norm(b)) > 1e-12 else None
            def similarity(method, a, b):
                if method in values:
                    return cosine(values[method][a], values[method][b])
                if method == "canonical_count_jaccard":
                    x, y = rows[a]["canonical_card_counts"], rows[b]["canonical_card_counts"]
                    keys = set(x)|set(y)
                    denominator = sum(max(x.get(k, 0), y.get(k, 0)) for k in keys)
                    return sum(min(x.get(k, 0), y.get(k, 0)) for k in keys)/denominator if denominator else 1.
                if method == "printed_five_group":
                    return -sum(float(abs(features[a, 0, lo:hi]-features[b, 0, lo:hi]).mean()) for lo, hi in GROUPS)/len(GROUPS)
                return -rows[b]["mechanical_labels"]["ir_only"]["distance"]
            invariant_pairs = [(a,b) for a in range(len(rows)) for b in range(a) if rows[a].get("invariance_group") is not None and rows[a]["invariance_group"] == rows[b].get("invariance_group")]
            invariance, floors = [], {space: EPSILON for space in SPACES}
            for a, b in invariant_pairs:
                if rows[a]["canonical_card_counts"] != rows[b]["canonical_card_counts"] or not np.array_equal(features[a], features[b]):
                    raise ValueError("declared invariant changes canonical counts or features")
                scores = {space: cosine(values[space][a], values[space][b]) for space in SPACES}
                errors = {space: float(abs(values[space][a]-values[space][b]).max()) for space in SPACES}
                if max(errors[SPACES[0]], errors[SPACES[3]]) > 1e-6:
                    raise ValueError("identical-input latent invariance exceeds fixed1e-6")
                for space, score in scores.items():
                    if score is not None:
                        floors[space] = max(floors[space], 2*abs(1-score))
                invariance.append(dict(left=rows[a]["id"], right=rows[b]["id"], cosine=scores, max_abs_error=errors))
            old = read(ROOT / "experiments/embedding-export/deck-embeddings.json")
            old_by_source = {r["source_index"]: np.asarray(r["vector"], np.float64) for r in old["rows"]}
            with np.load(HERE / "embedding-geometry-evidence/train-transform.npz", allow_pickle=False) as transform:
                mean, white = transform["train_mean"], transform["whitening"]
            comparisons = []
            historical_reference_ids = {reference["row_id"] for reference in embedding_result["anchors"]}
            for group in plan["comparisons"]:
                a, near, far = group["anchor"], group["near"], group["far"]
                for method in (*SPACES, *BASELINES):
                    order = order_result(similarity(method, a, near), similarity(method, a, far), plan["tie_epsilon"])
                    floor = floors.get(method, EPSILON)
                    parity = None
                    historical_available = method in SPACES[:3] and rows[a]["kind"] == "anchor" and rows[a]["id"] in historical_reference_ids
                    if historical_available:
                        anchor = old_by_source[group["source_index"]]
                        if method == SPACES[1]:
                            anchor = anchor-mean
                        elif method == SPACES[2]:
                            anchor = (anchor-mean) @ white
                        old_near, old_far = cosine(anchor, values[method][near]), cosine(anchor, values[method][far])
                        if old_near is not None and old_far is not None and order["gap"] is not None:
                            parity = abs(order["gap"]-(old_near-old_far))
                            floor = max(floor, parity)
                    comparisons.append(dict(group, method=method, **order, anchor_id=rows[a]["id"], near_id=rows[near]["id"], far_id=rows[far]["id"],
                                            invariance_floor=floors.get(method), old_anchor_parity_gap_perturbation=parity,
                                            historical_anchor_parity_available=historical_available,
                                            effective_empirical_gap_floor=floor, gap_exceeds_floor=abs(order["gap"]) > floor if order["gap"] is not None else None,
                                            caveat="Empirical numerical diagnostic, not a statistical bound. Historical parity applies only to original full96 anchors; branch/synthetic parity is unavailable."))
            summaries = {}
            for assay in sorted({r["assay"] for r in comparisons}):
                summaries[assay] = {}
                for stratum in ("strict-power-hp", "exploratory-power-hp-confounded"):
                    summaries[assay][stratum] = {method: {str(dose): aggregate([r for r in comparisons if r["assay"] == assay and r["stratum"] == stratum and r["method"] == method and r["dose"] == dose]) for dose in (1,2)} for method in (*SPACES, *BASELINES)}
            if any(r["result"] != "tie" for r in comparisons if r["method"] == "canonical_count_jaccard"):
                raise ValueError("canonical count baseline must tie within matched-dose comparisons")
            for item in plan["sources"]:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("protected input changed during metrics")
            result = dict(schema=SCHEMA, status="completed", plan_sha256=sha(plan_path), source_sha256=sha(__file__), vector_artifact=pin(vector_path),
                          controls_manifest=pin(plan["controls_manifest"]), row_ids=ids, input_rows=rows, comparisons=comparisons, summaries=summaries,
                          invariance=invariance, invariance_floors=floors, anchor_source_families=3,
                          compared_source_families=len({r["source_index"] for r in comparisons}),
                          declared_support={key: manifest[key] for key in ("assays", "v1", "v2", "support", "minimum_strict_primary_support_satisfied", "minimum_family_support_satisfied") if key in manifest}, counts=manifest["counts"],
                          interpretation="Independent fixed structural-proxy assay, not native behavior, synergy, semantic truth or playing strength. Doses/slots/views correlated within three held-out source roots.",
                          neural_forwards=0, native_calls=0, optimizer_updates=0, paid_jobs=0)
            write(out / "result.json", result)
        receipt = dict(status="completed", plan=pin(plan_path), result=pin(out / "result.json"), guard=guard.receipt(), neural_forwards=0, native_calls=0, optimizer_updates=0, paid_jobs=0)
    except BaseException as exc:
        write(out / "receipt.json", dict(status="failed", plan=pin(plan_path), error=repr(exc), guard=guard.receipt(), neural_forwards=0, native_calls=0, optimizer_updates=0, paid_jobs=0))
        raise
    write(out / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--embedding-plan", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.prepare:
        if any(value is None for value in (args.manifest, args.embedding_plan, args.out)):
            parser.error("prepare requires --manifest --embedding-plan --out")
        result = prepare(args.manifest, args.embedding_plan, args.out)
    else:
        result = execute(args.execute)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
