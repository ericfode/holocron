"""Synthetic stdlib tests only: temporary journals, no actual campaign or science."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import binding_transfer_next_accounting as A


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name).resolve()
        self.ledger = self.root / "synthetic-ledger.jsonl"
        self.main = self.root / "synthetic-main"
        self.main.write_text("This file is never executed.\n")
        self.parent = self.root / "synthetic-protection.json"
        self.parent.write_text(json.dumps(dict(protected_files=[], additional_protected_artifacts=[],
            closed_current_study_accounting=dict(charged_native_applies=112,
                total_charged_seconds=79.26753083174117, observed_native_applies=None,
                observed_v2_native_applies=32))))
        self.patches = [patch.object(A, "LEDGER", self.ledger), patch.object(A, "PRESERVATION", A.pin(self.parent)),
            patch.object(A, "CLOSED_PARENT_JOURNALS", []), patch.object(A, "PARENT_ARTIFACT_PINS", []),
            patch.object(A, "INHERITED_CORE", A.pin(self.main)), patch.object(A, "IMMUTABLE_PARENT_ROOTS", []),
            patch.object(A, "verify_failed_archive", lambda: None)]
        for value in self.patches:
            value.start()
        self.descriptors = {stage: dict(argv=[str(self.main)], outputs=[str(self.root / stage)]) for stage in A.STAGES}
        self.config = A.make_config(self.descriptors, [A.pin(self.main)], sealed=True)
        self.config_path = self.root / "synthetic-config.json"
        self.config_path.write_bytes(A.encoded(self.config))

    def tearDown(self):
        for value in reversed(self.patches):
            value.stop()
        self.directory.cleanup()

    def row(self, rows, event, data):
        body = dict(schema=A.SCHEMA, sequence=len(rows), previous_sha256=A.chain(rows), event=event, data=copy.deepcopy(data))
        rows.append(dict(body, record_sha256=A.digest(body)))

    def metadata(self, stage):
        return dict(**self.descriptors[stage], input_pins=[A.pin(self.main)], guard=copy.deepcopy(A.GUARD))

    def initialized_rows(self):
        rows = []
        self.row(rows, "initialized", dict(config=self.config, config_file=A.pin(self.config_path)))
        return rows

    def stage(self, rows, name, failed=False, unknown=False, elapsed=None, observed=None):
        reserve = A.STAGES[name]
        self.row(rows, "stage-start", dict(stage=name, reservation=reserve,
            metadata=self.metadata(name), started_monotonic_seconds=1., owner_pid=os.getpid()))
        values = {key: reserve[key] for key in A.COUNTERS} if observed is None else observed
        if unknown:
            values = {key: None if reserve[key] else 0 for key in A.COUNTERS}
        elapsed = reserve["seconds"] if elapsed is None else elapsed
        charge = dict(seconds=max(elapsed, reserve["seconds"]) if failed else elapsed)
        charge.update({key: max(values[key] or 0, reserve[key]) if failed else values[key] for key in A.COUNTERS})
        measured = ({"native_applies": values["native_applies"]} if name == "native" else
            self.config["fit_success_counts"] if name == "fit" else
            {"numerical_fits": values["numerical_fits"]} if name == "baselines" else None)
        self.row(rows, "stage-finish", dict(stage=name, status="failed" if failed else "completed",
            active_seconds=elapsed, observed=values, observed_verified=not unknown,
            charged=charge, proofs=[], cleanup_verified=True, execution_ended=True,
            counter_measurements=measured, counter_proof=A.pin(self.main) if measured is not None else None))

    def test_exact_caps_keep_carried_failure_and_unknown(self):
        rows = self.initialized_rows()
        for name in A.STAGES:
            self.stage(rows, name)
        result = A.state(rows)
        self.assertEqual(result["charged"]["seconds"], 125.)
        self.assertEqual(result["charged"]["numerical_fits"], 64)
        self.assertEqual(result["cumulative"]["charged_native_applies"], 208)
        self.assertEqual(result["cumulative"]["charged_seconds"], 236.76578145672102)
        self.assertIsNone(result["cumulative"]["observed_native_applies"])
        self.assertEqual(result["observed"]["native_applies"], 48)
        self.assertFalse(result["violated"])

    def test_closed_parent_chain_accepts_null_genesis_and_rejects_tamper(self):
        path = self.root / "closed-parent.jsonl"
        first = dict(sequence=0, previous_sha256=None, event="initialized", data={})
        first["record_sha256"] = A.digest(first)
        last = dict(sequence=1, previous_sha256=first["record_sha256"], event="stage-finish", data={})
        last["record_sha256"] = A.digest(last)
        path.write_text(json.dumps(first) + "\n" + json.dumps(last) + "\n")
        link = dict(pin=A.pin(path), records=2, first_previous_sha256=None,
                    final_record_sha256=last["record_sha256"], final_event="stage-finish")
        A.verify_closed_parent(link)
        wrong = copy.deepcopy(link)
        wrong["final_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "final"):
            A.verify_closed_parent(wrong)
        path.write_text(path.read_text().replace("stage-finish", "stage-start"))
        with self.assertRaisesRegex(ValueError, "changed"):
            A.verify_closed_parent(link)

    def test_outputs_cannot_enter_or_cover_closed_parent_roots(self):
        root = self.root / "immutable-parent"
        with patch.object(A, "IMMUTABLE_PARENT_ROOTS", [str(root)]):
            for value in (root / "new-output", root, self.root):
                with self.assertRaisesRegex(ValueError, "closed parent"):
                    A.verify_output_protection([str(value)])
            A.verify_output_protection([str(self.root / "new-campaign-output")])

    def test_failed_native_charges_full_reservation_and_keeps_unknown(self):
        rows = self.initialized_rows()
        self.stage(rows, "build", elapsed=.1)
        self.stage(rows, "native", failed=True, unknown=True, elapsed=.2)
        result = A.state(rows)
        self.assertEqual(result["charged"]["native_applies"], 48)
        self.assertEqual(result["charged"]["seconds"], 30.1)
        self.assertIsNone(result["observed"]["native_applies"])
        self.assertEqual(result["durable_prefix"]["native_applies"], 0)

    def test_failed_fit_charges_all_updates_forwards_and_time(self):
        rows = self.initialized_rows()
        for name in ("build", "native", "prep"):
            self.stage(rows, name, elapsed=.01)
        self.stage(rows, "fit", failed=True, unknown=True, elapsed=.2)
        result = A.state(rows)
        self.assertEqual(result["charged"]["optimizer_updates"], 5400)
        self.assertEqual(result["charged"]["neural_forwards"], 5436)
        self.assertIsNone(result["observed"]["optimizer_updates"])

    def test_pending_reservation_is_conservatively_counted(self):
        rows = self.initialized_rows()
        self.row(rows, "stage-start", dict(stage="build", reservation=A.STAGES["build"],
            metadata=self.metadata("build"), started_monotonic_seconds=1.))
        result = A.state(rows)
        self.assertEqual(result["conservative_including_pending"]["seconds"], 15.)
        self.assertEqual(result["cumulative"]["charged_seconds"], 126.76578145672102)
        self.assertIsNotNone(result["pending"])

    def test_tamper_unknown_event_retry_and_skip_fail_closed(self):
        rows = self.initialized_rows()
        damaged = copy.deepcopy(rows)
        damaged[0]["data"]["config"]["caps"]["seconds"] = 126.
        with self.assertRaises(ValueError):
            A.state(damaged)
        bad = copy.deepcopy(rows)
        self.row(bad, "credit", dict(seconds=-15.))
        with self.assertRaises(ValueError):
            A.state(bad)
        bad = copy.deepcopy(rows)
        self.stage(bad, "native")
        with self.assertRaises(ValueError):
            A.state(bad)
        self.stage(rows, "build")
        self.stage(rows, "build")
        with self.assertRaises(ValueError):
            A.state(rows)

    def test_zero_paid_cap_cannot_be_changed(self):
        config = copy.deepcopy(self.config)
        config["caps"]["paid_spend_usd"] = 1.
        with self.assertRaises(ValueError):
            A.validate_config(config)
        for bad in (True, float("nan"), -1):
            values = A.zero_counts(); values["native_applies"] = bad
            with self.assertRaises(ValueError):
                A.counts(values)

    def test_actual_overrun_is_preserved_as_breach_not_erased(self):
        rows = self.initialized_rows()
        self.stage(rows, "build", failed=True, elapsed=16.)
        self.assertTrue(A.state(rows)["violated"])
        self.assertEqual(A.state(rows)["charged"]["seconds"], 16.)

    def test_initialize_requires_go_and_never_overwrites(self):
        with self.assertRaises(ValueError):
            A.initialize(self.config_path, self.ledger)
        self.assertFalse(self.ledger.exists())
        A.initialize(self.config_path, self.ledger, root_go=True)
        original = self.ledger.read_bytes()
        with self.assertRaises(ValueError):
            A.initialize(self.config_path, self.ledger, root_go=True)
        self.assertEqual(original, self.ledger.read_bytes())

    def test_lease_is_nonblocking(self):
        A.initialize(self.config_path, self.ledger, root_go=True)
        with A.lease(self.ledger):
            with self.assertRaises(BlockingIOError):
                with A.lease(self.ledger):
                    self.fail("second lease entered")

    def test_preflight_failure_is_already_reserved_and_durable(self):
        self.descriptors["build"]["argv"] = ["/usr/bin/python3", "relative-missing.py"]
        self.config = A.make_config(self.descriptors, [A.pin(self.main)], sealed=True)
        self.config_path.write_bytes(A.encoded(self.config))
        A.initialize(self.config_path, self.ledger, root_go=True)
        with A.lease(self.ledger) as (stream, rows, _):
            with self.assertRaises(ValueError):
                A.start(stream, rows, "build", self.metadata("build"))
            self.assertIsNotNone(A.state(A.read_rows(stream))["pending"])
            done = A.finish(stream, rows, "failed", .01, A.zero_counts(), [], cleanup_verified=True,
                            execution_ended=True, observed_verified=True)
            self.assertEqual(done["charged"]["seconds"], 15.)

    def test_uncertain_cleanup_cannot_finish_or_resume(self):
        A.initialize(self.config_path, self.ledger, root_go=True)
        with A.lease(self.ledger) as (stream, rows, _):
            A.start(stream, rows, "build", self.metadata("build"))
            with self.assertRaises(ValueError):
                A.finish(stream, rows, "failed", .01, A.zero_counts(), [], execution_ended=True)
            A.note_pending_failure(stream, rows, "owned cleanup could not be verified")
            with self.assertRaises(ValueError):
                A.finish(stream, rows, "failed", .01, A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
        with self.assertRaises(ValueError):
            with A.lease(self.ledger):
                self.fail("pending ledger resumed")

    def test_changed_protected_bytes_block_initialization(self):
        value = json.loads(self.parent.read_text())
        value["closed_current_study_accounting"]["charged_native_applies"] = 0
        self.parent.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            A.initialize(self.config_path, self.ledger, root_go=True)
        self.assertFalse(self.ledger.exists())

    def test_progress_matches_exact_fitter_interoperability(self):
        path = self.root / "fit-progress.jsonl"
        rows = [dict(event="forward-intent", kind="train" if i <= 5400 else "evaluate", global_forward=i)
                for i in range(1, 5437)]
        rows += [dict(event=event, global_update=i, seed=17, arm="synthetic", arm_update=(i - 1) % 300 + 1)
                 for i in range(1, 5401) for event in ("optimizer-intent", "optimizer-update")]
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        self.assertEqual(A.progress_counts(path, "fit"), self.config["fit_success_counts"])
        rows[-1]["global_update"] = 5402
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        with self.assertRaises(ValueError):
            A.progress_counts(path, "fit")

    def test_native_and_fit_intents_are_counted_with_gaps_rejected(self):
        path = self.root / "native.jsonl"
        path.write_text(json.dumps(dict(schema="jepa-binding-transfer-apply-journal/1", maxApplyCalls=48)) + "\n" +
            json.dumps(dict(phase="beforeApply", applyCall=1)) + "\n")
        self.assertEqual(A.progress_counts(path, "native"), dict(native_applies=1))
        path.write_text(json.dumps(dict(phase="beforeApply", applyCall=1)) + "\n")
        with self.assertRaises(ValueError):
            A.progress_counts(path, "native")
        path.write_text(json.dumps(dict(event="numerical-fit-intent", global_fit=2)) + "\n")
        with self.assertRaises(ValueError):
            A.progress_counts(path, "baselines")

    def test_unpinned_main_never_passes_postreservation_preflight(self):
        self.config["pins"] = []
        self.config_path.write_bytes(A.encoded(self.config))
        A.initialize(self.config_path, self.ledger, root_go=True)
        with A.lease(self.ledger) as (stream, rows, _):
            metadata = self.metadata("build"); metadata["input_pins"] = []
            with self.assertRaisesRegex(ValueError, "entrypoint"):
                A.start(stream, rows, "build", metadata)
            self.assertIsNotNone(A.state(rows)["pending"])

    def test_protected_output_and_original_workspace_are_forbidden(self):
        protected = self.root / "immutable"; protected.write_text("unchanged")
        value = json.loads(self.parent.read_text())
        value["protected_files"] = [A.pin(protected)]
        value["original_workspaces"] = [dict(path=str(self.root / "original-workspace"))]
        self.parent.write_text(json.dumps(value))
        for output in (str(protected), str(self.root), str(self.root / "original-workspace/new-file")):
            with self.assertRaises(ValueError):
                A.verify_output_protection([output])
        A.verify_output_protection([str(self.root / "fresh-output")])

    def test_failed_fit_closes_with_raw_unpaired_intent_proof_only(self):
        rows = self.initialized_rows()
        for name in ("build", "native", "prep"):
            self.stage(rows, name, elapsed=.001)
        self.ledger.write_text("\n".join(A.encoded(row).decode() for row in rows) + "\n")
        with A.lease(self.ledger) as (stream, rows, _):
            A.start(stream, rows, "fit", self.metadata("fit"))
            directory = self.root / "fit"; directory.mkdir()
            progress = directory / "progress.jsonl"
            progress.write_text(json.dumps(dict(event="optimizer-intent", global_update=1,
                seed=17, arm="synthetic", arm_update=1)) + "\n")
            observed = A.zero_counts(); observed.update(optimizer_updates=None, neural_forwards=None)
            result = A.finish(stream, rows, "failed", .01, observed, [A.pin(progress)],
                cleanup_verified=True, execution_ended=True, counter_proof=None)
            self.assertIsNone(result["pending"])
            self.assertEqual(result["charged"]["optimizer_updates"], 5400)
            self.assertEqual(result["charged"]["neural_forwards"], 5436)
            self.assertIsNone(result["observed"]["optimizer_updates"])
            self.assertEqual(rows[-1]["data"]["proofs"], [A.pin(progress)])
            self.assertIsNone(rows[-1]["data"]["counter_proof"])

    def test_failed_native_closes_with_raw_partial_journal_and_unknown_count(self):
        rows = self.initialized_rows(); self.stage(rows, "build", elapsed=.001)
        self.ledger.write_text("\n".join(A.encoded(row).decode() for row in rows) + "\n")
        with A.lease(self.ledger) as (stream, rows, _):
            A.start(stream, rows, "native", self.metadata("native"))
            directory = self.root / "native"; directory.mkdir()
            progress = directory / "native-transitions.jsonl"
            progress.write_text('{"schema":"jepa-binding-transfer-apply-journal/1","maxApplyCalls":48}\n'
                '{"phase":"beforeApply","applyCall":1}\nPARTIAL')
            observed = A.zero_counts(); observed["native_applies"] = None
            result = A.finish(stream, rows, "failed", .01, observed, [A.pin(progress)],
                cleanup_verified=True, execution_ended=True, counter_proof=None)
            self.assertIsNone(result["pending"])
            self.assertEqual(result["charged"]["native_applies"], 48)
            self.assertIsNone(result["observed"]["native_applies"])
            self.assertEqual(rows[-1]["data"]["proofs"], [A.pin(progress)])


if __name__ == "__main__":
    unittest.main()
