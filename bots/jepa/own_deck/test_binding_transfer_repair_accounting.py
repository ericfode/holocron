"""Temporary synthetic accounting only; no real ledger, model or native calls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import binding_transfer_repair_accounting as A


class RepairAccountingTests(unittest.TestCase):
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

    def test_exact_zero_native_four_stage_caps_and_carried_unknown(self):
        self.assertEqual(tuple(A.STAGES), ("prep", "fit", "baselines", "verify"))
        self.assertEqual([v["seconds"] for v in A.STAGES.values()], [5., 60., 5., 5.])
        self.assertEqual(A.CAPS["native_applies"], 0)
        rows = self.initialized()
        for stage in A.STAGES:
            self.complete(rows, stage)
        state = A.state(rows)
        self.assertEqual(state["charged"]["seconds"], 75.)
        self.assertEqual(state["charged"]["native_applies"], 0)
        self.assertEqual(state["charged"]["neural_forwards"], 5436)
        self.assertEqual(state["charged"]["optimizer_updates"], 5400)
        self.assertEqual(state["charged"]["numerical_fits"], 64)
        self.assertEqual(state["cumulative"]["charged_native_applies"], 208)
        self.assertEqual(state["cumulative"]["charged_seconds"], 198.01331695669796)
        self.assertIsNone(state["cumulative"]["observed_native_applies"])

    def test_configuration_does_not_initialize_and_requires_go(self):
        self.assertFalse(self.ledger.exists())
        with self.assertRaises(ValueError):
            A.initialize(self.config_path, self.ledger)
        self.assertFalse(self.ledger.exists())
        A.initialize(self.config_path, self.ledger, root_go=True)
        with self.assertRaisesRegex(ValueError, "immutable"):
            A.initialize(self.config_path, self.ledger, root_go=True)

    def test_build_native_skipped_retried_and_credit_events_rejected(self):
        for stage in ("build", "native", "fit"):
            rows = self.initialized()
            self.append(rows, "stage-start", dict(stage=stage, reservation=A.STAGES.get(stage, A.STAGES["prep"]),
                metadata=self.metadata("prep"), started_monotonic_seconds=1.))
            with self.assertRaises(ValueError):
                A.state(rows)
        rows = self.initialized()
        self.complete(rows, "prep")
        self.complete(rows, "prep")
        with self.assertRaises(ValueError):
            A.state(rows)
        rows = self.initialized()
        self.append(rows, "credit", dict(seconds=-5))
        with self.assertRaises(ValueError):
            A.state(rows)

    def test_failed_prep_keeps_five_seconds_and_blocks_fit(self):
        rows = self.initialized()
        self.complete(rows, "prep", failed=True)
        state = A.state(rows)
        self.assertEqual(state["charged"]["seconds"], 5.)
        self.assertEqual(state["charged"]["native_applies"], 0)
        self.started(rows, "fit")
        with self.assertRaises(ValueError):
            A.state(rows)

    def test_failed_fit_full_reservations_and_nullable_actual_counts(self):
        rows = self.initialized()
        self.complete(rows, "prep")
        self.complete(rows, "fit", failed=True, unknown=True)
        state = A.state(rows)
        self.assertEqual(state["charged"]["seconds"], 65.)
        self.assertEqual(state["charged"]["optimizer_updates"], 5400)
        self.assertEqual(state["charged"]["neural_forwards"], 5436)
        self.assertIsNone(state["observed"]["neural_forwards"])

    def test_pending_exposure_and_cleanup_unknown_cannot_be_finished(self):
        rows = self.initialized()
        self.started(rows, "prep")
        state = A.state(rows)
        self.assertEqual(state["conservative_including_pending"]["seconds"], 5.)
        self.assertIsNotNone(state["pending"])
        with self.assertRaises(ValueError):
            A.finish(None, rows, "failed", .1, A.zero_counts(), [], cleanup_verified=False, execution_ended=True)

    def test_paid_or_native_caps_cannot_be_increased(self):
        for key in ("native_applies", "paid_jobs", "paid_spend_usd"):
            changed = copy.deepcopy(self.config)
            changed["caps"][key] = 1
            with self.assertRaises(ValueError):
                A.validate_config(changed)

    def test_unpaired_failed_fit_can_close_without_counter_proof(self):
        A.initialize(self.config_path, self.ledger, root_go=True)
        with A.lease(self.ledger) as (stream, rows, _):
            A.start(stream, rows, "prep", self.metadata("prep"))
            A.finish(stream, rows, "completed", .001, A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
            A.start(stream, rows, "fit", self.metadata("fit"))
            path = self.root / "fit" / "progress.jsonl"
            path.parent.mkdir()
            path.write_text(json.dumps(dict(event="optimizer-intent", global_update=1)) + "\n")
            unknown = A.zero_counts()
            unknown.update(optimizer_updates=None, neural_forwards=None)
            state = A.finish(stream, rows, "failed", .001, unknown, [A.pin(path)],
                cleanup_verified=True, execution_ended=True, observed_verified=False, counter_proof=None)
            self.assertIsNone(state["pending"])
            self.assertEqual(state["charged"]["optimizer_updates"], 5400)


if __name__ == "__main__":
    unittest.main()
