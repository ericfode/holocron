"""Synthetic temporary bookkeeping only; no actual saved-fit analysis."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import binding_transfer_report_accounting as A

class ReportAccountingTests(unittest.TestCase):
    def setUp(self):
            self.directory = tempfile.TemporaryDirectory()
            self.root = Path(self.directory.name).resolve()
            self.ledger = self.root / "synthetic.jsonl"
            self.main = self.root / "never-executed-main"
            self.main.write_text("synthetic bytes, never executed")
            self.protected = self.root / "protected.json"
            self.protected.write_text(json.dumps(dict(protected_files=[], additional_protected_artifacts=[],
                closed_current_study_accounting=dict(charged_native_applies=112,
                    total_charged_seconds=79.26753083174117, observed_native_applies=None,
                    observed_v2_native_applies=32))))
            self.patches = [patch.object(A, "LEDGER", self.ledger),
                patch.object(A, "PRESERVATION", A.pin(self.protected)),
                patch.object(A, "INHERITED_CORE", A.pin(self.main)),
                patch.object(A, "CLOSED_PARENT_JOURNALS", []), patch.object(A, "PARENT_ARTIFACT_PINS", []),
                patch.object(A, "IMMUTABLE_PARENT_ROOTS", []), patch.object(A, "verify_failed_archive", lambda: None)]
            for value in self.patches:
                value.start()
            self.descriptors = {name: dict(argv=[str(self.main)], outputs=[str(self.root / name)]) for name in A.STAGES}
            self.config = A.make_config(self.descriptors, [A.pin(self.main)], sealed=True)
            self.config_path = self.root / "config.json"
            self.config_path.write_bytes(A.encoded(self.config))

    def tearDown(self):
            for value in reversed(self.patches):
                value.stop()
            self.directory.cleanup()

    def append(self, rows, event, data):
            body = dict(schema=A.SCHEMA, sequence=len(rows), previous_sha256=A.chain(rows), event=event, data=data)
            rows.append(dict(body, record_sha256=A.digest(body)))

    def initialized(self):
            rows = []
            self.append(rows, "initialized", dict(config=self.config, config_file=A.pin(self.config_path)))
            return rows

    def metadata(self, stage):
            return dict(**self.descriptors[stage], input_pins=[A.pin(self.main)], guard=copy.deepcopy(A.GUARD))

    def started(self, rows, stage):
            self.append(rows, "stage-start", dict(stage=stage, reservation=A.STAGES[stage],
                metadata=self.metadata(stage), started_monotonic_seconds=1., owner_pid=os.getpid()))

    def complete(self, rows, stage, failed=False, unknown=False):
            self.started(rows, stage)
            reserve = A.STAGES[stage]
            observed = {key: (None if unknown and reserve[key] else reserve[key]) for key in A.COUNTERS}
            charged = dict(seconds=reserve["seconds"], **{key: max(observed[key] or 0, reserve[key]) if failed else observed[key] for key in A.COUNTERS})
            measured = (self.config["fit_success_counts"] if stage == "fit" else
                        dict(numerical_fits=64) if stage == "baselines" else None)
            self.append(rows, "stage-finish", dict(stage=stage, status="failed" if failed else "completed",
                active_seconds=reserve["seconds"], charged=charged, observed=observed,
                observed_verified=not unknown, proofs=[], cleanup_verified=True, execution_ended=True,
                counter_measurements=measured, counter_proof=A.pin(self.main) if measured and not failed else None))

    def test_three_stages_zero_neural_update_native_and_retained_unknown(self):
        self.assertEqual(tuple(A.STAGES), ("recover", "baselines", "verify"))
        self.assertEqual([v["seconds"] for v in A.STAGES.values()], [3., 5., 5.])
        rows = self.initialized()
        for stage in A.STAGES:
            self.complete(rows, stage)
        state = A.state(rows)
        self.assertEqual(state["charged"]["seconds"], 13.)
        for key in ("native_applies", "neural_forwards", "optimizer_updates", "paid_jobs", "paid_spend_usd"):
            self.assertEqual(state["charged"][key], 0)
        self.assertEqual(state["charged"]["numerical_fits"], 64)
        self.assertEqual(state["cumulative"]["charged_native_applies"], 208)
        self.assertEqual(state["cumulative"]["charged_seconds"], 197.01759783166926)
        self.assertIsNone(state["cumulative"]["observed_native_applies"])
        self.assertIsNone(self.config["parent"]["failed_fit_observed_neural_forwards"])
        self.assertEqual(self.config["parent"]["durable_saved_fit_neural_forwards"], 5436)
        self.assertIn("Historical", self.config["fit_counts_scope"])

    def test_no_fit_prep_native_build_skip_retry_or_credit_stage(self):
        for stage in ("fit", "prep", "native", "build", "baselines"):
            rows = self.initialized()
            self.append(rows, "stage-start", dict(stage=stage, reservation=A.STAGES.get(stage, A.STAGES["recover"]),
                metadata=self.metadata("recover"), started_monotonic_seconds=1.))
            with self.assertRaises(ValueError):
                A.state(rows)
        rows = self.initialized()
        self.complete(rows, "recover")
        self.complete(rows, "recover")
        with self.assertRaises(ValueError):
            A.state(rows)
        rows = self.initialized()
        self.append(rows, "credit", dict(seconds=-3))
        with self.assertRaises(ValueError):
            A.state(rows)

    def test_failed_baseline_full_fits_and_time_nullable_actuals(self):
        rows = self.initialized()
        self.complete(rows, "recover")
        self.complete(rows, "baselines", failed=True, unknown=True)
        state = A.state(rows)
        self.assertEqual(state["charged"]["seconds"], 8.)
        self.assertEqual(state["charged"]["numerical_fits"], 64)
        self.assertIsNone(state["observed"]["numerical_fits"])
        self.started(rows, "verify")
        with self.assertRaises(ValueError):
            A.state(rows)

    def test_metadata_only_no_initialization_or_overwrite_without_go(self):
        self.assertFalse(self.ledger.exists())
        with self.assertRaises(ValueError):
            A.initialize(self.config_path, self.ledger)
        A.initialize(self.config_path, self.ledger, root_go=True)
        with self.assertRaisesRegex(ValueError, "immutable"):
            A.initialize(self.config_path, self.ledger, root_go=True)

    def test_pending_and_uncertain_cleanup_preserve_reservation(self):
        rows = self.initialized()
        self.started(rows, "recover")
        state = A.state(rows)
        self.assertEqual(state["conservative_including_pending"]["seconds"], 3.)
        with self.assertRaises(ValueError):
            A.finish(None, rows, "failed", .01, A.zero_counts(), [], cleanup_verified=False, execution_ended=True)

    def test_zero_scientific_and_paid_caps_cannot_expand(self):
        for key in ("native_applies", "neural_forwards", "optimizer_updates", "paid_jobs", "paid_spend_usd"):
            value = copy.deepcopy(self.config)
            value["caps"][key] = 1
            with self.assertRaises(ValueError):
                A.validate_config(value)


if __name__ == "__main__":
    unittest.main()
