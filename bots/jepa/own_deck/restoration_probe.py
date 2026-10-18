"""Bounded frozen-latent authored-versus-constructed probe; execute only after GO.

No world-model objective, game rollout, win target, or remaining-deck label is
used. Restoration scores are empirical classifier outputs, never forced ranks.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np

HERE = Path(__file__).resolve().parent
JEPA = HERE.parent
REPO = JEPA.parents[1]
sys.path.insert(0, str(JEPA))
import own_deck_model as D
import own_deck as O
from run_events import RunEvents
import run_local_experiments as G

ARMS = ("frozen-latent", "printed-only-frozen-latent")
SCORE_NAME = "authored-vs-constructed score"
LIMITATIONS = [
    "Classifier of authored versus constructed declarations, not deck quality, legality, win probability, or playing strength.",
    "Frozen baseline plus original engineering initialization; independent of auxiliary declaration fits.",
    "No dynamic remaining-deck ledger, transition/effect objective, world-model fit, game, or opponent execution.",
    "One seed, small inherited family holdout, and shared card identities limit generalization claims.",
    "Incomplete-original-size curves are out-of-distribution diagnostics, never remaining-pile bad labels.",
    "An IR trait-target relation grounds a package fixture, not strategic gain; the frozen encoder consumes printed traits, not program semantics.",
]


@dataclass(frozen=True)
class Config:
    seed: int = 17
    steps: int = 200
    learning_rate: float = 0.05
    ridge: float = 0.001
    max_seconds: float = 60.0
    max_rss_mib: float = 2048.0

    def validate(self):
        if self.seed != 17 or type(self.steps) is not int or not 1 <= self.steps <= 200:
            raise ValueError("allocation admits seed17 and 1..200 steps per arm")
        if self.learning_rate != 0.05 or self.ridge != 0.001:
            raise ValueError("fixed classifier hyperparameters; no search")
        if not 0 < self.max_seconds <= 60 or not 0 < self.max_rss_mib <= 2048:
            raise ValueError("resource caps exceed the proposed allocation")
        return self


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate_dataset(pack, manifest):
    """Admit family-held-out fit rows and unlabelled held-out restoration rows."""
    p = dict(pack)
    for prefix in ("fit", "eval"):
        rows = np.asarray(p[f"{prefix}_features"], np.float32)
        n = len(rows)
        if not 1 <= n <= 4096 or rows.shape != (n, 2, 207) or not np.isfinite(rows).all():
            raise ValueError(f"invalid {prefix} feature bank")
        p[f"{prefix}_features"] = rows
        if not np.array_equal(rows[:, 1], O.neutral_features(n)[:, 1]):
            raise ValueError("remaining composition must stay disabled and unknown")
        for field in ("source_idx", "family_ids", "partition", "variant_ids"):
            if np.asarray(p[f"{prefix}_{field}"]).shape != (n,):
                raise ValueError(f"bad {prefix}_{field}")
        if len(set(map(str, p[f"{prefix}_variant_ids"]))) != n:
            raise ValueError("variant IDs must be unique within each bank")
    labels = np.asarray(p["fit_labels"], np.float64)
    if labels.shape != (len(p["fit_features"]),) or not np.isin(labels, [0, 1]).all():
        raise ValueError("fit labels must be binary authored-record provenance")
    p["fit_labels"] = labels
    partitions = np.asarray(p["fit_partition"]).astype(str)
    train, val = np.flatnonzero(partitions == "train"), np.flatnonzero(partitions == "val")
    if len(train) < 2 or len(val) < 2 or len(train) + len(val) != len(labels):
        raise ValueError("need complete, nonempty train/val partition")
    for name, indices in (("train_idx", train), ("val_idx", val)):
        if name in p and not np.array_equal(np.asarray(p[name]), indices):
            raise ValueError("index aliases disagree with partitions")
        p[name] = indices
    families = np.asarray(p["fit_family_ids"]).astype(str)
    sources = np.asarray(p["fit_source_idx"])
    if set(families[train]) & set(families[val]) or set(sources[train]) & set(sources[val]):
        raise ValueError("source/family leakage across fit partitions")
    fingerprints = np.asarray(p["fit_fingerprints"]).astype(str)
    if fingerprints.shape != labels.shape or set(fingerprints[train]) & set(fingerprints[val]):
        raise ValueError("composition leakage across partitions")
    if set(labels[train]) != {0., 1.}:
        raise ValueError("training needs both authored and constructed examples")
    coarse = [8, *range(11, 25), *range(35, 41)]
    source_families = {}
    for source in set(sources):
        group = p["fit_features"][sources == source]
        assigned = set(families[sources == source])
        if len(assigned) != 1:
            raise ValueError("one source must inherit one family")
        source_families[source] = next(iter(assigned))
        if not np.allclose(group[:, 0, 4], group[0, 0, 4], atol=1e-7, rtol=0):
            raise ValueError("primary fit controls must match original copy count per source")
        if not np.allclose(group[:, 0, coarse], group[0, 0, coarse], atol=1e-6, rtol=0):
            raise ValueError("fit controls must match printed cost/type/arena/aspects")
    if not np.all(p["fit_features"][:, 0, 3] == 1):
        raise ValueError("fit declarations must have complete metadata")
    e = len(p["eval_features"])
    for field in ("group_ids", "kind", "restored_copies", "removed_copies", "total_count"):
        if np.asarray(p[f"eval_{field}"]).shape != (e,):
            raise ValueError(f"bad eval_{field}")
    if set(np.asarray(p["eval_partition"]).astype(str)) != {"val"}:
        raise ValueError("restoration evaluation must be held-out only")
    if not set(map(str, p["eval_family_ids"])) <= set(families[val]):
        raise ValueError("restoration family is not in the inherited holdout")
    if not set(p["eval_source_idx"]) <= set(sources[val]):
        raise ValueError("restoration source is not held out")
    if any(source_families[source] != str(family) for source, family in zip(p["eval_source_idx"], p["eval_family_ids"])):
        raise ValueError("restoration source/family assignment changed")
    kinds = np.asarray(p["eval_kind"]).astype(str)
    if not set(kinds) <= {"true-restoration", "matched-alternative", "incomplete-diagnostic"}:
        raise ValueError("unsupported restoration kind")
    for group in set(map(str, p["eval_group_ids"])):
        selected = np.asarray(p["eval_group_ids"]).astype(str) == group
        if len(set(p["eval_source_idx"][selected])) != 1 or len(set(map(str, p["eval_family_ids"][selected]))) != 1:
            raise ValueError("one restoration group cannot combine sources/families")
        primary = selected & (kinds != "incomplete-diagnostic")
        counts = np.asarray(p["eval_total_count"])[primary]
        if len(counts) and not np.all(counts == counts[0]):
            raise ValueError("primary restoration and alternatives must have fixed equal count")
        primary_rows = p["eval_features"][primary]
        if len(primary_rows) and not np.allclose(primary_rows[:, 0, coarse], primary_rows[0, 0, coarse], atol=1e-6, rtol=0):
            raise ValueError("primary restoration must retain printed cost/type/arena/aspect controls")
    if manifest.get("training_launched") is True:
        raise ValueError("dataset manifest must describe preparation, not claim a fit")
    return p


def load_dataset(path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("artifact", {}).get("sha256") != sha(path):
        raise ValueError("dataset does not match its manifest hash")
    with np.load(path, allow_pickle=False) as data:
        return validate_dataset(data, manifest), manifest


def context_without_size(rows, printed_only=False):
    """Remove explicit size fields and factor mass; retain printed trait summaries."""
    result = np.asarray(rows, np.float32).copy()
    result[:, 0, [4, 5, 6, 49]] = 0
    for start, end in ((50, 114), (114, 146), (146, 207)):
        values = result[:, 0, start:end]
        mass = values.sum(1, keepdims=True)
        np.divide(values, mass, out=values, where=mass != 0)
    if printed_only:
        result[:, :, 50:] = 0
    return result


def latent_bank(model, rows, printed_only=False, check=lambda: None):
    context = context_without_size(rows, printed_only)
    result = []
    for start in range(0, len(rows), 32):
        check()
        deck = context[start:start+32]
        n = len(deck)
        z = model.encode(np.zeros((n, 73), np.float32), np.zeros((n, 24), np.int64),
                         np.zeros((n, 24, 21), np.float32), np.zeros((n, 24), np.float32), own_deck=deck)
        result.append(z)
        check()
    return np.concatenate(result).astype(np.float64)


def sigmoid(logits):
    return 1 / (1 + np.exp(-np.clip(logits, -60, 60)))


def logistic_terms(x, y, weight, bias, ridge):
    """Class-balanced full-batch logistic objective; no restoration labels."""
    balance = np.where(y == 1, 0.5 / np.sum(y == 1), 0.5 / np.sum(y == 0))
    logits = x @ weight + bias
    residual = balance * (sigmoid(logits) - y)
    loss = np.sum(balance * (np.logaddexp(0, logits) - y * logits)) + 0.5 * ridge * (weight @ weight)
    return float(loss), x.T @ residual + ridge * weight, float(residual.sum())


def curve_report(scores, data, manifest):
    """Preserve every observed score; descriptive deltas have no ordering constraint."""
    scores = np.asarray(scores, np.float64)
    groups, measurements = {}, []
    ids = np.asarray(data["eval_group_ids"]).astype(str)
    for group in sorted(set(ids)):
        rows = np.flatnonzero(ids == group)
        points = []
        for i in sorted(rows, key=lambda i: (str(data["eval_kind"][i]), int(data["eval_restored_copies"][i]), str(data["eval_variant_ids"][i]))):
            kind = str(data["eval_kind"][i])
            step = int(data["eval_restored_copies"][i])
            actual = int(data["eval_actual_original_copies_restored"][i]) if "eval_actual_original_copies_restored" in data else (0 if kind == "matched-alternative" else step)
            points.append(dict(variant_id=str(data["eval_variant_ids"][i]), kind=str(data["eval_kind"][i]),
                               paired_restoration_step=step, restored_copies=step,
                               actual_original_copies_restored=actual, constant_anchor=kind == "matched-alternative",
                               removed_copies=int(data["eval_removed_copies"][i]),
                               total_count=int(data["eval_total_count"][i]), score=float(scores[i]),
                               out_of_distribution=bool(data["eval_kind"][i] == "incomplete-diagnostic")))
        main = [p for p in points if p["kind"] == "true-restoration"]
        deltas = np.diff([p["score"] for p in main])
        alternatives = {p["restored_copies"]: p["score"] for p in points if p["kind"] == "matched-alternative"}
        source, family = int(data["eval_source_idx"][rows[0]]), str(data["eval_family_ids"][rows[0]])
        paired = [dict(restored_copies=p["restored_copies"], restoration_fraction=p["restored_copies"]/max(p["removed_copies"], 1),
                       score=p["score"], matched_score=alternatives[p["restored_copies"]], delta=p["score"]-alternatives[p["restored_copies"]])
                  for p in main if p["restored_copies"] in alternatives]
        groups[group] = dict(source_idx=source, family_id=family, metadata=manifest.get("curve_groups", {}).get(group, {}), points=points,
                             restoration_endpoint_delta=float(main[-1]["score"]-main[0]["score"]) if len(main)>1 else None,
                             adjacent_score_deltas=deltas.tolist(), decreases=int(np.sum(deltas < 0)),
                             nondecreasing_adjacent_fraction=float(np.mean(deltas >= 0)) if len(deltas) else None, paired_same_count=paired)
        for point in paired:
            measurements.append(dict(source=source, family=family, group=group, **point))
    # Variant points are dependent: average groups within source, then sources
    # within family, before computing macro means or reporting support.
    def aggregate(items):
        family_values = {}
        for family in sorted({m["family"] for m in items}):
            own = [m for m in items if m["family"] == family]
            source_values = []
            for source in sorted({m["source"] for m in own}):
                each = [m for m in own if m["source"] == source]
                group_values = [np.mean([m["delta"] for m in each if m["group"] == group]) for group in {m["group"] for m in each}]
                source_values.append(float(np.mean(group_values)))
            family_values[family] = float(np.mean(source_values))
        return dict(mean_same_count_delta=float(np.mean(list(family_values.values()))) if family_values else None,
                    family_mean_deltas=family_values, n_families=len(family_values),
                    n_sources=len({m["source"] for m in items}), n_restoration_groups=len({m["group"] for m in items}),
                    n_packages=sum(manifest.get("curve_groups", {}).get(group, {}).get("kind") == "rule-grounded-package" for group in {m["group"] for m in items}),
                    n_dependent_points=len(items))
    per_fraction = {str(f): aggregate([m for m in measurements if round(m["restoration_fraction"], 8) == f])
                    for f in sorted({round(m["restoration_fraction"], 8) for m in measurements})}
    return dict(score_name=SCORE_NAME, calibration="Balanced authored-vs-constructed training prior; not a calibrated quality/win probability.",
                groups=groups, family_first_same_count_aggregate=aggregate(measurements), per_restoration_fraction=per_fraction,
                uncertainty="Tiny inherited family holdout; no independent-variant sample claim or reliable population confidence interval.",
                matched_control="The full-size matched-alternative deck is a constant anchor repeated at each paired step; it restores zero authored copies and provides no independent repeated observations.",
                incomplete_diagnostics="Reported separately in group points; excluded from same-count aggregates and all fit labels.")


def identity_overlap(data):
    """Report hashed-factor overlap separately from exact card-code overlap in lineage."""
    train = data["fit_features"][data["train_idx"], 0, 50:]
    val = data["fit_features"][data["val_idx"], 0, 50:]
    a, b = np.any(train > 0, axis=0), np.any(val > 0, axis=0)
    return dict(train_active_factor_bins=int(a.sum()), val_active_factor_bins=int(b.sum()),
                shared_factor_bins=int((a & b).sum()), note="Factor-bin overlap has hash collisions; exact card overlap must be reported from dataset lineage.")


def emit_curve_events(writer, curves, arm, step):
    """Publish existing final scores; feed rows are dependent curve observations."""
    for group, record in curves["groups"].items():
        for point in record["points"]:
            writer.emit("metric", "restoration_curve", step,
                        metrics=dict(score=point["score"],
                                     true_arm_restoration_step=point["paired_restoration_step"],
                                     actual_original_copies_restored=point["actual_original_copies_restored"],
                                     deck_size=point["total_count"],
                                     is_primary=int(not point["out_of_distribution"])),
                        arm=arm, curve_group=group, family_id=record["family_id"],
                        source_idx=str(record["source_idx"]), curve_kind=point["kind"],
                        fixture_kind=record["metadata"].get("kind", "unspecified"),
                        variant_id=point["variant_id"], score_name=SCORE_NAME,
                        observation_scope="dependent final-score curve point; constant anchors are repeated controls")

    aggregates = [("all-steps", None, curves["family_first_same_count_aggregate"])]
    aggregates.extend(("paired-restoration-fraction", float(fraction), values)
                      for fraction, values in curves["per_restoration_fraction"].items())
    for name, fraction, values in aggregates:
        metrics = {key: values[key] for key in ("mean_same_count_delta", "n_families", "n_sources", "n_packages", "n_restoration_groups", "n_dependent_points")
                   if values.get(key) is not None}
        if fraction is not None:
            metrics["restoration_fraction"] = fraction
        writer.emit("metric", "restoration_curve_aggregate", step, metrics=metrics,
                    arm=arm, aggregation=name, curve_kind="family-first-same-count-delta",
                    observation_scope="groups within source, then sources within family; repeated anchors are not independent samples")


def emit_classification_diagnostic(writer, values, arm, step, point):
    """Log an already computed baseline/final provenance diagnostic."""
    writer.emit("metric", "provenance_diagnostic", step,
                metrics={key: values[key] for key in ("family_macro_log_loss", "family_macro_accuracy", "n_families", "n_sources")},
                arm=arm, diagnostic_point=point, used_for_selection=False,
                target_scope="authored-record provenance, not quality or winning probability")


def prepare(args, config):
    data, manifest = load_dataset(args.dataset, args.manifest)
    base = JEPA / "models/tx-t10.safetensors"
    init = JEPA / "wasm/generated-own-deck/deck-init.safetensors"
    provenance = dict(npz_path=str(args.dataset.resolve()), npz_sha256=sha(args.dataset),
                      manifest_path=str(args.manifest.resolve()), manifest_sha256=sha(args.manifest),
                      base_checkpoint_sha256=sha(base), engineering_initialization_sha256=sha(init),
                      train_examples=len(data["train_idx"]), heldout_examples=len(data["val_idx"]),
                      heldout_restoration_points=len(data["eval_features"]),
                      primary_experiment_admitted=manifest.get("primary_experiment_admitted") is True,
                      train_family_ids=sorted(set(map(str, data["fit_family_ids"][data["train_idx"]]))),
                      val_family_ids=sorted(set(map(str, data["fit_family_ids"][data["val_idx"]]))),
                      source_sha256={str(p.relative_to(JEPA)): sha(p) for p in (Path(__file__), HERE / "run_events.py", HERE / "run_local_experiments.py", JEPA / "own_deck_model.py", JEPA / "own_deck.py", JEPA / "tx_model.py")})
    return data, manifest, base, init, provenance


def classification_diagnostic(x, y, weight, bias, indices, families, sources):
    """One baseline/final diagnostic; no selection or restoration ranking label."""
    probabilities = sigmoid(x[indices] @ weight+bias)
    targets = y[indices]
    losses = np.logaddexp(0, x[indices] @ weight+bias) - targets*(x[indices] @ weight+bias)
    per_family = {}
    for family in sorted(set(map(str, families[indices]))):
        selected = np.asarray(families[indices]).astype(str) == family
        source_losses, source_accuracies = [], []
        for source in sorted(set(sources[indices][selected])):
            own = selected & (sources[indices] == source)
            source_losses.append(float(losses[own].mean()))
            source_accuracies.append(float(np.mean((probabilities[own] >= .5) == targets[own])))
        per_family[family] = dict(log_loss=float(np.mean(source_losses)),
                                  accuracy=float(np.mean(source_accuracies)), n_sources=len(source_losses),
                                  n_dependent_rows=int(selected.sum()))
    return dict(family_macro_log_loss=float(np.mean([v["log_loss"] for v in per_family.values()])),
                family_macro_accuracy=float(np.mean([v["accuracy"] for v in per_family.values()])),
                n_families=len(per_family), n_sources=len(set(sources[indices])), per_family=per_family,
                label="authored-record provenance; may reflect construction artifacts")


def train_probe(data, manifest, config, outdir, base, init, preview, started, writer):
    """One child, two frozen feature extractions and at most 400 head updates."""
    updates = 0
    results = {}
    frozen = {str(base): sha(base), str(init): sha(init)}

    def check():
        if time.monotonic()-started > config.max_seconds:
            raise RuntimeError("60-second cumulative wall threshold")
        if G.peak_rss_mib() > config.max_rss_mib:
            raise RuntimeError("2GiB worker peak-RSS threshold")

    try:
        check()
        weights, meta = D.load_extended(base, init)
        model = D.NumpyOwnDeckTx(weights, meta)
        bank = np.concatenate([data["fit_features"], data["eval_features"]])
        n = len(data["fit_features"])
        for arm in ARMS:
            check()
            z = latent_bank(model, bank, arm == ARMS[1], check)
            train = data["train_idx"]
            mean, scale = z[train].mean(0), z[train].std(0)
            scale = np.maximum(scale, 1e-6)
            x = (z-mean)/scale
            y = data["fit_labels"][train]
            rng = np.random.default_rng(config.seed)
            weight, bias = rng.normal(0, 0.01, 96), 0.
            baseline = classification_diagnostic(x, data["fit_labels"], weight, bias,
                                                 data["val_idx"], data["fit_family_ids"], data["fit_source_idx"])
            emit_classification_diagnostic(writer, baseline, arm, updates, "baseline")
            losses = []
            for step in range(1, config.steps+1):
                check()
                loss, grad, db = logistic_terms(x[train], y, weight, bias, config.ridge)
                if not np.isfinite(loss) or not np.isfinite(grad).all() or not np.isfinite(db):
                    raise FloatingPointError("nonfinite logistic objective/gradient")
                weight -= config.learning_rate*grad
                bias -= config.learning_rate*db
                updates += 1
                metrics = {"arm_update": step, "updates_completed": updates, "elapsed_seconds": time.monotonic()-started}
                metric = step == 1 or step % 20 == 0 or step == config.steps
                if metric: metrics["train_objective_before_update"] = loss
                writer.emit("metric" if metric else "status", arm, updates, metrics=metrics, status="running")
                losses.append(loss)
            check()
            scores = sigmoid(x[n:] @ weight+bias)
            curves = curve_report(scores, data, manifest)
            final = classification_diagnostic(x, data["fit_labels"], weight, bias,
                                              data["val_idx"], data["fit_family_ids"], data["fit_source_idx"])
            emit_classification_diagnostic(writer, final, arm, updates, "final")
            emit_curve_events(writer, curves, arm, updates)
            checkpoint = outdir / (arm+".npz")
            np.savez(checkpoint, weight=weight, bias=np.asarray(bias), train_mean=mean, train_scale=scale)
            results[arm] = dict(curves=curves, train_objective_before_first_update=losses[0],
                                train_objective_before_final_update=losses[-1], updates=config.steps,
                                validation_provenance_diagnostics=dict(baseline=baseline, final=final, evaluations=2,
                                                                      used_for_selection=False),
                                frozen_train_latent_mean_std=float(z[train].std(0).mean()), checkpoint=dict(path=str(checkpoint), sha256=sha(checkpoint)))
        if frozen != {p: sha(p) for p in frozen}: raise AssertionError("frozen checkpoint bytes changed")
        return dict(schema="own-deck-restoration-probe/1", status="completed", **preview,
                    updates_completed=updates, elapsed_seconds=time.monotonic()-started, arms=results,
                    frozen_checkpoints_unchanged=True, immutable_before=frozen,
                    immutable_after={p: sha(p) for p in frozen})
    except BaseException as exc:
        writer.emit("error", "aborted", updates, status="failed", reason=str(exc),
                    metrics={"updates_completed": updates, "elapsed_seconds": time.monotonic()-started},
                    immutable_before=frozen, immutable_after={p: sha(p) for p in frozen})
        raise


def _restoration_worker(messages, acknowledged, data, manifest, config, outdir, base, init, preview, started):
    """IPC worker: terminal results wait for the parent's final RSS/exit checks."""
    writer = G.WorkerEvents(messages)
    stop = threading.Event()

    def report():
        while not stop.wait(1.): writer.report_rss()

    thread = threading.Thread(target=report, daemon=True)
    thread.start()
    try:
        writer.report_rss()
        result = train_probe(data, manifest, config, outdir, base, init, preview, started, writer)
        writer.report_rss()
        messages.put(("result", G.json_primitives(result)))
        if not acknowledged.wait(timeout=3.):
            raise RuntimeError("parent did not acknowledge terminal result")
    except BaseException as exc:
        messages.put(("failure", dict(reason=str(exc), type=type(exc).__name__, step=writer.step)))
        acknowledged.wait(timeout=3.)
    finally:
        stop.set(); thread.join(timeout=2)


def run(args):
    config = Config(steps=args.steps).validate()
    started = time.monotonic()
    data, manifest, base, init, provenance = prepare(args, config)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    settings = {**asdict(config), "arms": ARMS, "objective": "class-balanced logistic + L2 on frozen96d latent",
                "training_rows": "fit_partition=train only", "size_fields_masked": [4,5,6,49],
                "identity_mass": "each factor normalized to1", "printed_only_masks": "identity50:207; printed traits retained",
                "selection": "fixed final step; no CV or checkpoint search", "cpu_threads": 1,
                "scope": "historical structural diagnostic only" if args.historical_diagnostic else "admitted construction fixture probe",
                "guard": "one owned NumPy worker for both arms; parent-enforced 60s campaign and 2048MiB sampled process-tree threshold",
                "validation_diagnostics": "baseline and final only per arm; four total, never selection"}
    preview = dict(commit=commit, config=settings, dataset=provenance, limitations=LIMITATIONS,
                   factor_identity_overlap=identity_overlap(data), exact_identity_overlap=manifest.get("identity_overlap", "See dataset lineage; not inferred from collision-prone factor bins."))
    if not args.execute:
        print(json.dumps(preview, indent=2, allow_nan=False))
        return preview
    if manifest.get("primary_experiment_admitted") is not True and not args.historical_diagnostic:
        raise ValueError("primary format admission is not established; historical diagnostic needs an explicit separate launch")
    preview["historical_structural_diagnostic_only"] = bool(args.historical_diagnostic)
    args.out.mkdir(parents=True, exist_ok=False)
    json_write(args.out / "preflight.json", preview)
    writer = RunEvents(args.events, args.run_id, commit, settings, provenance, LIMITATIONS, args.parent_run_id)
    writer.emit("status", "encoding", 0, status="running", artifacts={"preflight": str(args.out / "preflight.json")})
    frozen = {str(base): sha(base), str(init): sha(init)}
    try:
        result = G.supervise_worker(_restoration_worker,
                                    (data, manifest, config, args.out, base, init, preview, started),
                                    writer, config.max_seconds, started, config.max_seconds, config.max_rss_mib)
        after = {p: sha(p) for p in frozen}
        if frozen != after: raise AssertionError("frozen checkpoint bytes changed")
        result.update(immutable_before=frozen, immutable_after=after)
        json_write(args.out / "result.json", result)
        writer.emit("artifact", "completed", result["updates_completed"], status="completed",
                    metrics={"updates_completed": result["updates_completed"], "elapsed_seconds": time.monotonic()-started},
                    artifacts={"result": str(args.out / "result.json"), "sha256": sha(args.out / "result.json")})
        return result
    except BaseException as exc:
        receipt = dict(status="failed", error=str(exc), updates_journaled=writer.step,
                       update_accounting="On forced termination the last durable IPC event is a lower bound; no completed-result claim.",
                       elapsed_seconds=time.monotonic()-started, guard=getattr(exc, "guard", None),
                       immutable_before=frozen, immutable_after={p: sha(p) for p in frozen})
        json_write(args.out / "error.json", receipt)
        writer.emit("error", "aborted", writer.step, status="failed", reason=str(exc),
                    metrics={"updates_journaled": writer.step, "elapsed_seconds": receipt["elapsed_seconds"]},
                    artifacts={"error_receipt": str(args.out / "error.json")})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--execute", action="store_true", help="Real classifier updates; requires the separately authorized bounded launch.")
    parser.add_argument("--historical-diagnostic", action="store_true", help="Explicitly withhold primary current-format claim; requires separate launch authorization.")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--parent-run-id")
    args = parser.parse_args()
    if args.execute and (args.out is None or args.events is None or not args.run_id):
        parser.error("--execute requires --out, --events, --run-id")
    run(args)


if __name__ == "__main__":
    main()
