"""Read verified JSON metrics and ledgers only; no array/model/fit imports."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWN = HERE.parents[1] / "holocron-deck-context/bots/jepa/own_deck"
SEEDS = (17, 29, 43)
ARMS = ("C0R0", "C1R0", "C0R1", "C1R1", "ID-only", "untrained-typed")
VARIANTS = ("LOF_053", "LOF_261")


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def mean(values):
    return sum(values) / len(values) if values and all(v is not None for v in values) else None


def ledger(path):
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    previous = "0" * 64
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        assert row["sequence"] == i and row["previous_sha256"] == previous
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        previous = hashlib.sha256(encoded).hexdigest()
        assert row["record_sha256"] == previous
    return rows


def main():
    paths = dict(verification=HERE / "verify-result.json", recovered_report=HERE / "recover-1/result.json",
                 baselines=HERE / "baselines-1/result.json", ledger=HERE / "campaign-ledger.jsonl",
                 v2_ledger=HERE.parent / "binding-transfer-v2/campaign-ledger.jsonl",
                 failed_fit_ledger=HERE.parent / "binding-transfer-repair-v1/campaign-ledger.jsonl",
                 preregistration=OWN / "BINDING_TRANSFER_V2_PROTOCOL.md",
                 repair_protocol=OWN / "BINDING_TRANSFER_REPAIR_PROTOCOL.md",
                 report_recovery_protocol=OWN / "BINDING_TRANSFER_REPORT_RECOVERY_PROTOCOL.md",
                 verifier_source=OWN / "binding_transfer_report_verify.py", audit_source=Path(__file__))
    before = {key: pin(path) for key, path in paths.items()}
    v, f, b = (read(paths[k]) for k in ("verification", "recovered_report", "baselines"))
    assert v["status"] == "PASS" and v["check_count"] == 93471 and not v["mismatches"]
    assert f["status"] == "recovered-from-saved-artifacts" and f["original_fit_status"] == "failed"
    assert not v["semantic_validated"] and not f["semantic_validated"] and not b["semantic_validated"]
    primary = {}
    for correction in ("C", "R"):
        selected = [v["per_seed_contrasts"][str(seed)][correction] for seed in SEEDS]
        baseline = [p["baseline_mae"] for p in selected]
        corrected = [p["repaired_mae"] for p in selected]
        reduction = (sum(baseline) - sum(corrected)) / sum(baseline) if sum(baseline) > 0 else None
        primary[correction] = dict(per_seed={str(s): p for s, p in zip(SEEDS, selected)},
            baseline_seed_mean_mae=mean(baseline), corrected_seed_mean_mae=mean(corrected),
            aggregate_relative_reduction=reduction, improves_every_seed=all(a < z for a, z in zip(corrected, baseline)),
            narrow_benefit_supported=all(a < z for a, z in zip(corrected, baseline)) and reduction is not None and reduction >= .10,
            rule="Strict lower MAE in every seed AND (sum baseline - sum corrected)/sum baseline >= .10; zero denominator is undefined.")
    comparisons = []
    base_names = ("zero", "train_mean", "C0R0", "C1R0", "C0R1", "C1R1")
    for seed in SEEDS:
        learned = v["narrow_estimands"][f"s{seed}:C1R1"]["300"]
        for variant in VARIANTS:
            corrected = learned["R"][variant]["mae"]
            for name in (*base_names, "ID-only", "untrained-typed"):
                control = (b["evaluations"][name]["narrow_estimands"]["R_fresh_positive_parent_stat_variants_actual_endpoints"][variant]["mae"]
                           if name in base_names else v["narrow_estimands"][f"s{seed}:{name}"]["300"]["R"][variant]["mae"])
                comparisons.append(dict(seed=seed, variant=variant, control=name, learned_mae=corrected,
                    control_mae=control, learned_minus_control=corrected-control, strictly_better=corrected < control))
    failures = [p for p in comparisons if not p["strictly_better"]]
    summaries, primary_heads = {}, {}
    for arm in ARMS:
        summaries[arm], primary_heads[arm] = {}, {}
        for cell in ("train", "state_held", "family_held", "joint"):
            values = [f["results"][f"s{s}:{arm}"]["evaluations"]["300"]["cells"][cell]["actual_endpoints"] for s in SEEDS]
            summaries[arm][cell] = dict(seed_values=[p["family_first_mae"] for p in values],
                                      seed_mean=mean([p["family_first_mae"] for p in values]))
            primary_heads[arm][cell] = {head: dict(seed_values=[p["heads"][head]["mae"] for p in values],
                seed_mean_native_mae=mean([p["heads"][head]["mae"] for p in values]))
                for head in ("target_damage_delta", "target_power_delta", "target_hp_delta")}
    post_rows, repair_rows, v2_rows = (ledger(paths[k]) for k in ("ledger", "failed_fit_ledger", "v2_ledger"))
    stage_rows = lambda rr: [r["data"] for r in rr if r["event"] == "stage-finish"]
    post = stage_rows(post_rows)
    assert [r["stage"] for r in post] == ["recover", "baselines", "verify"] and all(r["status"] == "completed" for r in post)
    phase_b = [r for r in stage_rows(v2_rows) if r["stage"] == "prep"] + stage_rows(repair_rows) + post
    phase_b_seconds = sum(r["charged"]["seconds"] for r in phase_b)
    post_seconds = sum(r["charged"]["seconds"] for r in post)
    assert repair_rows[-1]["data"]["status"] == "failed" and repair_rows[-1]["data"]["charged"]["seconds"] == 60.
    assert repair_rows[-1]["data"]["observed"]["neural_forwards"] is None
    assert all(r["observed"][k] == 0 for r in post for k in ("native_applies", "neural_forwards", "optimizer_updates", "paid_spend_usd"))
    audit = dict(schema="jepa-binding-transfer-json-decision-audit/1", status="completed-json-only-review",
        source_pins=before, official_verification=dict(status=v["status"], checks=v["check_count"], mismatches=0),
        scope="Only saved verified JSON metrics, comparisons, means and ledger arithmetic; no prediction, label, array, model or fit evaluation.",
        primary_corrections=primary,
        stronger_typed_transfer=dict(supported=not failures, required_comparisons=len(comparisons),
            passed_comparisons=len(comparisons)-len(failures), failures=failures, comparisons=comparisons,
            rule="C1R1 R MAE must be strictly below every zero/mean/four-ridge/ID/frozen-encoder control for each variant and seed."),
        all_arm_final_family_first_train_scaled_mae=summaries,
        family_first_scope="Saved family-first mean of TRAIN-scaled primary damage/stats errors; equal three-seed averages only. Dependent roots/heads/variants, no inference or new metric evaluation.",
        all_arm_final_primary_head_native_mae=primary_heads,
        native_support=v["training_support"], partitions=v["partitions"],
        descriptive_controls=dict(C_ID_beats_typed_all_seeds=all(v["narrow_estimands"][f"s{s}:ID-only"]["300"]["C"]["mae"] < v["narrow_estimands"][f"s{s}:C1R1"]["300"]["C"]["mae"] for s in SEEDS),
            corrected_R_direction={str(s): {code: v["narrow_estimands"][f"s{s}:C1R1"]["300"]["R"][code]["direction_accuracy"] for code in VARIANTS} for s in SEEDS},
            untrained_means_frozen_card_encoder_with_trained_readout=True,
            joint_damage_zero_baseline_mae=b["evaluations"]["zero"]["cells"]["joint"]["actual_endpoints"]["heads"]["target_damage_delta"]["mae"],
            joint_damage_corrected_seed_mean_mae=primary_heads["C1R1"]["joint"]["target_damage_delta"]["seed_mean_native_mae"]),
        accounting=dict(postprocess_stage_charges=[dict(stage=r["stage"], status=r["status"], seconds=r["charged"]["seconds"]) for r in post],
            postprocess_charged_seconds=post_seconds, cumulative_charged_native_applications=208,
            cumulative_charged_seconds=184.01759783166926+post_seconds, historical_observed_native_applications=None,
            phase_B_charges=[dict(stage=r["stage"], status=r["status"], seconds=r["charged"]["seconds"]) for r in phase_b],
            phase_B_charged_seconds=phase_b_seconds, phase_B_allocation_seconds=80., phase_B_remaining_seconds=80.-phase_b_seconds,
            postprocess_native_calls=0, postprocess_neural_forwards=0, postprocess_optimizer_updates=0,
            postprocess_head_fit_attempts=b["head_fit_attempts"], actual_baseline_solver_calls=b["actual_lstsq_solver_calls"],
            original_fit_status="failed", failed_fit_charged_seconds=60., failed_fit_observed_neural_forwards=None,
            failed_fit_observed_optimizer_updates=None, durable_saved_fit_prefix=v["counter_proofs"]["fit"],
            postprocess_final_chain=post_rows[-1]["record_sha256"], new_paid_spend_usd=0.),
        semantic_validated=False, generic_semantic_gate="UNSUPPORTED",
        limitations=["C is seen-program fresh-state transfer; R is two positive-stat variants within one broad family.",
            "Three seeds, repeated roots and correlated HP/power coordinates are dependent; no confidence interval or significance claim.",
            "Actual-endpoint training and chosen-only rescoring do not replicate the old conditional task or prove its failure cause.",
            "The original fit remains failed; recovered metadata does not recover unsaved final gradients or original report checksums.",
            "Stronger typed-learning advantage is not established despite positive content/relation ablations; no capacity/strength/full-card claim."])
    assert before == {key: pin(path) for key, path in paths.items()}, "source changed during JSON audit"
    with (HERE / "decision-audit.json").open("x") as stream:
        json.dump(audit, stream, sort_keys=True, indent=2, allow_nan=False); stream.write("\n")
    c, r = primary["C"], primary["R"]
    lines = ["# Independent saved-JSON decision review", "",
        f"Official saved-output verification passed {v['check_count']:,} checks with zero mismatches. Both predeclared narrow benefits are supported: C reduces seed-mean MAE from {c['baseline_seed_mean_mae']:.6f} to {c['corrected_seed_mean_mae']:.6f} ({100*c['aggregate_relative_reduction']:.2f}%); R from {r['baseline_seed_mean_mae']:.6f} to {r['corrected_seed_mean_mae']:.6f} ({100*r['aggregate_relative_reduction']:.2f}%). Every corresponding seed improves.", "",
        "The stronger typed-transfer criterion fails. The learned typed model beats all six zero/mean/ridge designs for each R variant in every seed, but ID-only has lower LOF_053 error in all three seeds. The frozen random card encoder with a trained readout also beats it on both variants at seed29. ID-only beats the corrected model on the C panel in all three seeds. Routing direction is correct throughout the corrected R panel, but the ID and frozen-encoder controls also achieve this; it is not unique evidence of learned program semantics.", "",
        "| Seed | C baseline | C corrected | R baseline | R corrected |", "|---|---:|---:|---:|---:|"]
    for seed in SEEDS:
        cc, rr = c["per_seed"][str(seed)], r["per_seed"][str(seed)]
        lines.append(f"| {seed} | {cc['baseline_mae']:.6f} | {cc['repaired_mae']:.6f} | {rr['baseline_mae']:.6f} | {rr['repaired_mae']:.6f} |")
    lines += ["", "The saved corrected-model family-first, TRAIN-scaled primary-error mean across seeds is " +
        ", ".join(f"{cell} {summaries['C1R1'][cell]['seed_mean']:.6f}" for cell in ("train", "state_held", "family_held", "joint")) +
        ". The joint damage head also remains inaccurate on native zero outcomes: corrected mean MAE " +
        f"{primary_heads['C1R1']['joint']['target_damage_delta']['seed_mean_native_mae']:.6f} versus zero-baseline MAE 0. These are descriptive, separate from the narrow R stat panel.", "",
        f"Phase B charged {phase_b_seconds:.14f}s of 80s, retaining failed prep5s and failed fit60s. The new report/baseline/verification stages charged {post_seconds:.15f}s with zero new native calls, neural forwards or updates; {b['head_fit_attempts']} head-fit attempts used {b['actual_lstsq_solver_calls']} solver calls. Cumulative binding accounting remains 208 charged applications / {184.01759783166926+post_seconds:.14f}s, with historical observed applications unknown. The original fit remains failed with observed neural counters unknown; the durable 5,400-update/5,436-forward prefix and saved outputs are separate evidence. Unsaved gradients remain unavailable. New paid spending is $0.", "",
        "C covers one seen damage program on fresh states; R covers two positive-stat variants within one broad family. Repeated contexts, correlated heads and three seeds are not independent family trials. Generic semantics remain unsupported/false. This does not establish capacity, playing strength, complete-card semantics or the cause of the earlier conditional-task failure.", "",
        "This review used JSON and simple arithmetic only: no model/NumPy imports, prediction evaluation, numerical fit or new metric run. [decision-audit.json](decision-audit.json) contains every control comparison, saved-metric summaries, exact source SHA-256/byte pins and ledger arithmetic. [decision_audit_json_only.py](decision_audit_json_only.py) is the review source.", ""]
    (HERE / "DECISION_AUDIT.md").write_text("\n".join(lines))
    print(json.dumps(dict(audit=pin(HERE / "decision-audit.json"), report=pin(HERE / "DECISION_AUDIT.md"),
                         primary_C=c["narrow_benefit_supported"], primary_R=r["narrow_benefit_supported"],
                         stronger_typed_transfer=not failures, failed_control_comparisons=len(failures),
                         phase_B_seconds=phase_b_seconds), sort_keys=True))


if __name__ == "__main__":
    main()
