"""Stdlib-only temporary fixtures; no historical ledger or scientific call."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location("sealed_budget_test_subject", HERE / "sealed_budget.py")
S = importlib.util.module_from_spec(loader)
loader.loader.exec_module(S)


def write(path, value):
    path.write_bytes(S.encoded(value))


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "new"; self.root.mkdir()
        self.script = self.base / "toy.py"; self.script.write_text("# Harmless test descriptor, never executed.\n")
        self.input = self.base / "input.txt"; self.input.write_text("toy input")
        self.parent = self.base / "parent.json"
        self.old = self.base / "old.jsonl"
        body = dict(schema="toy-old/1", sequence=0, previous_sha256="0"*64, event="closed", data={})
        row = dict(body, record_sha256=S.digest(body)); self.old.write_bytes(S.encoded(row) + b"\n")
        self.history = dict(carry=dict(charged_native_applies=275, charged_seconds=215.3528530828189,
            observed_native_applies=None), pins=[], protected_files=[S.pin(self.input)], protected_roots=[],
            closed_journals=[dict(pin=S.pin(self.old), records=1, genesis_previous="0"*64,
                final_chain=row["record_sha256"], closed_event="closed")])
        write(self.parent, self.history)
        self.argv = [str(Path(sys.executable).resolve()), str(self.script)]
        self.spec_path = self.root / "spec.json"
        self.spec = dict(schema=S.SPEC_SCHEMA, status="sealed-awaiting-root-GO", source=S.pin(S.__file__),
            primitives=S.pin(S._PATH), ledger_path=str(self.root / "campaign-ledger.jsonl"),
            caps=dict(seconds=40, **{k: 0 for k in S.STANDARD}), guard=dict(cpu_workers=1, rss_bytes=1024**3),
            stage_order=["toy"], stages={}, parent_manifest=S.pin(self.parent),
            pins=[S.pin(self.argv[0]), S.pin(self.script)])
        self.add_stage("toy", neural_forwards=1)

    def add_stage(self, name, external=False, **counts):
        reserve = dict(seconds=20, **{k: 0 for k in S.STANDARD}); reserve.update(counts)
        self.spec["stages"][name] = dict(argv=self.argv, outputs=[str(self.root / (name + "-out"))],
            reservation=reserve, expected={k: (None if external and k == "native_applies" else v)
                for k, v in reserve.items() if k != "seconds"}, external_counters=["native_applies"] if external else [])
        for k in self.spec["caps"]: self.spec["caps"][k] = sum(v["reservation"][k] for v in self.spec["stages"].values())

    def budget(self, initialize=True):
        write(self.spec_path, self.spec)
        budget = S.Budget(self.spec_path)
        if initialize: budget.initialize(root_go=True)
        return budget

    def begin(self, run, name="toy"):
        return run.begin(name, argv=self.argv, guard=self.spec["guard"], inputs=[S.pin(self.input)])

    def finish(self, run, status="completed", **kw):
        return run.finish(status, cleanup_verified=True, execution_ended=True, **kw)

    def test_import_and_constructor_write_nothing(self):
        original = Path.open
        def readonly(path, mode="r", *args, **kw):
            self.assertFalse(any(c in mode for c in "wax+"), "module import wrote a file")
            return original(path, mode, *args, **kw)
        with patch.object(Path, "open", readonly):
            spec = importlib.util.spec_from_file_location("sealed_budget_reimport", HERE / "sealed_budget.py")
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        budget = self.budget(False)
        self.assertFalse(budget.inspect()["ledger_initialized"])
        with self.assertRaises(ValueError): budget.initialize()
        self.assertFalse(budget.ledger.exists())

    def test_order_once_fsync_and_toy_call(self):
        self.spec["stage_order"].append("second"); self.add_stage("second", numerical_fits=1)
        b = self.budget()
        with b.lease() as run:
            with self.assertRaises(ValueError): self.begin(run, "second")
            with patch.object(S.os, "fsync", wraps=S.os.fsync) as fsync:
                self.begin(run)
                token = run.intent("neural_forwards")
                rows = [json.loads(v) for v in b.ledger.read_text().splitlines()]
                self.assertEqual(rows[-1]["event"], "intent")
                self.assertEqual(abs(-3), 3)  # Harmless stand-in after durable intent.
                run.complete(token); self.finish(run)
                self.assertGreaterEqual(fsync.call_count, 4)
            with self.assertRaises(ValueError): self.begin(run)
        with b.lease() as run:
            self.begin(run, "second"); token = run.intent("numerical_fits")
            self.assertEqual(sum([1, 2]), 3); run.complete(token)
            state = self.finish(run)
        self.assertEqual(state["completed"], ["toy", "second"])
        self.assertEqual(b.inspect()["observed"]["neural_forwards"], 1)
        self.assertIsNone(state["cumulative"]["observed_native_applies"])
        with self.assertRaises(ValueError): b.initialize(root_go=True)

    def test_counter_limit_precedes_call_and_completion_is_once(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards")
            before = b.ledger.read_bytes()
            with self.assertRaises(ValueError): run.intent("neural_forwards")
            self.assertEqual(before, b.ledger.read_bytes())
            run.complete(token)
            with self.assertRaises(ValueError): run.complete(token)
            self.finish(run)

    def test_failed_stage_full_charge_null_and_durable_prefix(self):
        self.add_stage("toy", neural_forwards=3, native_applies=2)
        b = self.budget()
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards"); run.complete(token)
            state = self.finish(run, "failed")
        self.assertEqual(state["charged"]["seconds"], 20)
        self.assertEqual(state["charged"]["neural_forwards"], 3)
        self.assertEqual(state["charged"]["native_applies"], 2)
        self.assertIsNone(state["observed"]["neural_forwards"])
        last = json.loads(b.ledger.read_text().splitlines()[-1])
        self.assertEqual(last["data"]["durable_completed"]["neural_forwards"], 1)
        with self.assertRaises(ValueError):
            with b.lease(): pass

    def test_incomplete_intent_cannot_complete_stage(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); run.intent("neural_forwards")
            with self.assertRaises(ValueError): self.finish(run)
            self.finish(run, "failed")

    def test_begin_checks_after_durable_reservation(self):
        b = self.budget()
        self.input.write_text("changed")
        with b.lease() as run:
            with self.assertRaises(ValueError): self.begin(run)
            state = b.snapshot(run.state)
            self.assertEqual(state["conservative_including_pending"]["neural_forwards"], 1)
            self.assertEqual(state["pending"]["stage"], "toy")
            self.finish(run, "failed")
        self.assertEqual(b.inspect(verify=False)["charged"]["seconds"], 20)

    def test_changed_parent_or_history_rejected(self):
        b = self.budget()
        raw = self.parent.read_bytes(); self.parent.write_bytes(raw + b" ")
        with self.assertRaises(ValueError): b.inspect()
        self.parent.write_bytes(raw); self.old.write_text("{}\n")
        with self.assertRaises(ValueError): b.inspect()

    def test_unknown_cleanup_remains_pending_full_reservation(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); state = run.pending_failure("cleanup unknown")
            self.assertEqual(state["conservative_including_pending"]["seconds"], 20)
            with self.assertRaises(ValueError): self.finish(run, "failed")
        with self.assertRaises(ValueError):
            with b.lease(): pass

    def test_unpinned_entrypoint_rejected_after_reservation(self):
        self.spec["pins"] = [S.pin(self.argv[0])]
        b = self.budget()
        with b.lease() as run:
            with self.assertRaises(ValueError): self.begin(run)
            self.assertIsNotNone(run.state["pending"])
            self.finish(run, "failed")

    def test_existing_output_and_protected_paths(self):
        out = self.root / "toy-out"; out.mkdir()
        b = self.budget()
        with b.lease() as run:
            with self.assertRaises(ValueError): self.begin(run)
            self.finish(run, "failed")
        for path in (self.input, self.base, self.root, self.spec_path, b.ledger):
            with self.assertRaises(ValueError): b.protect([str(path)])

    def test_nested_nonblocking_lease_and_chain_tamper(self):
        b = self.budget()
        with b.lease():
            with self.assertRaises(BlockingIOError):
                with b.lease(): pass
        rows = b.ledger.read_text().splitlines(); row = json.loads(rows[0]); row["data"] = {}
        b.ledger.write_text(json.dumps(row) + "\n")
        with self.assertRaises(ValueError): b.inspect()

    def test_touched_source_at_finish_closes_failed(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards"); run.complete(token)
            self.script.write_text("changed source")
            state = self.finish(run)
        self.assertEqual(state["failures"], 1)
        self.assertIsNone(state["observed"]["neural_forwards"])

    def test_invalid_output_proof_closes_failed(self):
        b = self.budget()
        outside = self.base / "outside"; outside.write_text("not declared")
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards"); run.complete(token)
            state = self.finish(run, proofs=[S.pin(outside)])
        self.assertEqual(state["failures"], 1)

    def test_wall_overrun_is_not_credited(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards"); run.complete(token)
            with patch.object(S.time, "monotonic", return_value=run.state["pending"]["started"] + 30):
                state = self.finish(run)
        self.assertEqual(state["charged"]["seconds"], 30)
        self.assertTrue(state["violated"])

    def external(self):
        self.add_stage("toy", external=True, native_applies=32)
        b = self.budget()
        out = self.root / "toy-out"
        return b, out

    def external_proofs(self, out):
        out.mkdir(); trace = out / "trace.jsonl"; trace.write_text("toy external trace only\n")
        summary = out / "verification.json"; write(summary, {"verified_by": "toy frozen worker"})
        return [S.pin(trace), S.pin(summary)]

    def test_external_success_observes_actual_not_reserved(self):
        b, out = self.external()
        with b.lease() as run:
            self.begin(run); token = run.intent("native_applies", 32)
            proofs = self.external_proofs(out)
            run.complete(token, actual=20, proofs=proofs)
            state = self.finish(run)
        self.assertEqual(state["charged"]["native_applies"], 20)
        self.assertEqual(state["observed"]["native_applies"], 20)
        self.assertEqual(state["cumulative"]["charged_native_applies"], 295)
        self.assertIsNone(state["cumulative"]["observed_native_applies"])
        last = json.loads(b.ledger.read_text().splitlines()[-1])["data"]
        self.assertEqual(last["durable_intents"]["native_applies"], 32)
        self.assertEqual(len(last["proofs"]), 2)

    def test_external_count_and_proof_limits(self):
        b, out = self.external()
        with b.lease() as run:
            self.begin(run); token = run.intent("native_applies", 32); proofs = self.external_proofs(out)
            with self.assertRaises(ValueError): run.complete(token, actual=33, proofs=proofs)
            with self.assertRaises(ValueError): run.complete(token, actual=20, proofs=[])
            unknown = self.base / "unknown"; unknown.write_text("opaque")
            with self.assertRaises(ValueError): run.complete(token, actual=20, proofs=[S.pin(unknown), proofs[0]])
            run.complete(token, actual=0, proofs=proofs)
            state = self.finish(run)
        self.assertEqual(state["observed"]["native_applies"], 0)

    def test_ordinary_counter_cannot_partial_complete(self):
        b = self.budget()
        with b.lease() as run:
            self.begin(run); token = run.intent("neural_forwards")
            with self.assertRaises(ValueError): run.complete(token, actual=0)
            run.complete(token); self.finish(run)

    def test_external_trace_rechecked_at_finish(self):
        b, out = self.external()
        with b.lease() as run:
            self.begin(run); token = run.intent("native_applies", 32); proofs = self.external_proofs(out)
            run.complete(token, actual=20, proofs=proofs)
            Path(proofs[0]["path"]).write_text("changed trace")
            state = self.finish(run)
        self.assertEqual(state["charged"]["native_applies"], 32)
        self.assertIsNone(state["observed"]["native_applies"])

    def test_spec_invalid_numbers_paid_and_external_policy(self):
        original = copy.deepcopy(self.spec)
        for mutation in (lambda s: s["caps"].update(paid_jobs=1),
                lambda s: s["caps"].update(neural_forwards=True),
                lambda s: s["stages"]["toy"].update(external_counters=["neural_forwards"]),
                lambda s: s["stages"]["toy"]["expected"].update(neural_forwards=2)):
            self.spec = copy.deepcopy(original); mutation(self.spec)
            with self.assertRaises(ValueError): self.budget(False)


if __name__ == "__main__":
    unittest.main()
