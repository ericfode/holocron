"""Synthetic bookkeeping only: no real campaign, scientific import or process."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("campaign_accounting", Path(__file__).with_name("semantic_discrimination_accounting.py"))
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.old = self.root / "old"
        self.old.mkdir()
        self.protected = self.old / "protected"
        self.protected.write_text("unchanged")
        self.entry = self.root / "worker.py"
        self.entry.write_text("# never executed\n")
        self.prior = self.root / "prior.json"
        self.prior.write_text(json.dumps(dict(schema="jepa-campaign-prior-manifest/1",
            carry=dict(charged_native_applies=208, charged_seconds=188.08889674965758, observed_native_applies=None),
            pins=[], closed_journals=[], protected_files=[A.pin(self.protected)],
            protected_roots=[str(self.old)], original_workspaces=[])))
        self.campaign = self.root / "new"
        self.campaign.mkdir()
        descriptors = {s: dict(argv=[str(Path(sys.executable).resolve()), str(self.entry)],
            outputs=[str(self.campaign / s)]) for s in A.STAGE_SECONDS}
        self.spec = A.make_spec(self.campaign, A.pin(self.prior), descriptors,
                               [A.pin(sys.executable), A.pin(self.entry)], sealed=True)
        self.spec_path = self.campaign / "campaign-spec.json"
        self.save_spec()

    def tearDown(self):
        self.tmp.cleanup()

    def save_spec(self):
        self.spec_path.write_text(json.dumps(self.spec))
        self.c = A.Campaign(self.spec_path)

    def initialize(self):
        return self.c.initialize(root_go=True)

    def complete(self, stage):
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, stage, self.c.metadata(stage))
            proof = Path(self.spec["stage_descriptors"][stage]["outputs"][0])
            proof.write_text("ended-and-owned-cleanup")
            if stage in ("build", "native"):
                self.c.child_intent(stream, rows, self.spec["stage_descriptors"][stage]["argv"])
                self.c.child_started(stream, rows, 123, 123, "synthetic-launch-identity")
                self.c.child_ended(stream, rows, [A.pin(proof)], cleanup_verified=True, execution_ended=True)
            return self.c.finish(stream, rows, "completed", 0., A.zero_counts(), [A.pin(proof)],
                                 cleanup_verified=True, execution_ended=True)

    def test_construction_inspection_no_initialization(self):
        result = self.c.inspect()
        self.assertFalse(result["ledger_initialized"])
        self.assertFalse(self.c.LEDGER.exists())
        with self.assertRaisesRegex(ValueError, "root freeze"):
            self.c.initialize()

    def test_exclusive_initialization_and_chain_tamper(self):
        self.initialize()
        with self.assertRaises(ValueError):
            self.initialize()
        with self.c.lease() as (_, rows, state):
            self.assertEqual(state["cumulative"]["charged_native_applies"], 208)
            damaged = copy.deepcopy(rows)
            damaged[0]["data"]["spec"]["caps"]["seconds"] = 999
            with self.assertRaisesRegex(ValueError, "hash chain"):
                self.c.state(damaged)

    def test_stage_order_once_and_lease_exclusion(self):
        self.initialize()
        with self.c.lease() as (stream, rows, _):
            with self.assertRaises(BlockingIOError):
                with self.c.lease():
                    pass
            with self.assertRaisesRegex(ValueError, "prior ordered"):
                self.c.start(stream, rows, "fit", self.c.metadata("fit"))
        self.complete("metadata")
        with self.c.lease() as (stream, rows, _):
            with self.assertRaisesRegex(ValueError, "once-only"):
                self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))

    def test_preflight_failure_reserved_before_checks(self):
        self.spec["stage_descriptors"]["metadata"]["argv"][1] = str(self.root / "missing.py")
        self.save_spec()
        self.initialize()
        with self.c.lease() as (stream, rows, _):
            with self.assertRaisesRegex(ValueError, "entrypoint"):
                self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))
            self.assertEqual(self.c.state(rows)["pending_reserved_exposure"]["seconds"], 3.)
            state = self.c.finish(stream, rows, "failed", .01, A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
            self.assertEqual(state["charged"]["seconds"], 3.)

    def test_failed_native_unknown_fullcharge_without_partial_proof(self):
        self.initialize()
        for stage in ("metadata", "build"):
            self.complete(stage)
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, "native", self.c.metadata("native"))
            raw = self.campaign / "native"
            raw.write_text('{"phase":"beforeApply","applyCall":1}\n')
            observed = A.zero_counts()
            observed["native_applies"] = None
            state = self.c.finish(stream, rows, "failed", .01, observed, [A.pin(raw)],
                cleanup_verified=True, execution_ended=True, observed_verified=False, durable_prefix=dict(A.zero_counts(), native_applies=1))
            self.assertEqual(state["charged"]["native_applies"], 128)
            self.assertIsNone(state["observed"]["native_applies"])
            self.assertEqual(state["durable_prefix"]["native_applies"], 1)
            self.assertEqual(state["cumulative"]["charged_native_applies"], 336)
            self.assertIsNone(state["cumulative"]["observed_native_applies"])

    def test_cleanup_unknown_stays_pending(self):
        self.initialize()
        self.complete("metadata")
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, "build", self.c.metadata("build"))
            self.c.child_intent(stream, rows, self.c.metadata("build")["argv"])
            self.c.child_started(stream, rows, 123, 123, "launch")
            self.c.note_pending_failure(stream, rows, "owned cleanup uncertain")
            state = self.c.state(rows)
            self.assertEqual(state["pending_reserved_exposure"]["seconds"], 10.)
            with self.assertRaises(ValueError):
                self.c.finish(stream, rows, "failed", 0., A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
        with self.assertRaisesRegex(ValueError, "ended unbreached"):
            with self.c.lease():
                pass

    def test_child_lifecycle_success_required(self):
        self.initialize()
        self.complete("metadata")
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, "build", self.c.metadata("build"))
            with self.assertRaisesRegex(ValueError, "owned child"):
                self.c.finish(stream, rows, "completed", 0., A.zero_counts(), [], cleanup_verified=True, execution_ended=True)

    def test_protected_output_and_changed_source_fail_closed(self):
        self.spec["stage_descriptors"]["metadata"]["outputs"] = [str(self.old)]
        self.save_spec()
        self.initialize()
        with self.c.lease() as (stream, rows, _):
            with self.assertRaisesRegex(ValueError, "protected"):
                self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))
        self.protected.write_text("mutated")
        with self.assertRaisesRegex(ValueError, "changed pinned"):
            self.c.inspect()

    def test_memory_spec_mutation_rejected(self):
        self.c.config["environment"]["mutated"] = "yes"
        with self.assertRaisesRegex(ValueError, "in-memory"):
            self.c.inspect()

    def test_fit_paired_progress_3000_3045(self):
        path = self.root / "progress"
        rows = []
        for i in range(1, 3001):
            rows.append(dict(event="forward-intent", global_forward=i, kind="train"))
            model = dict(global_update=i, seed=17, arm="correct", arm_update=i)
            rows.extend([dict(event="optimizer-intent", **model), dict(event="optimizer-update", **model)])
        rows.extend(dict(event="forward-intent", global_forward=i, kind="evaluate") for i in range(3001, 3046))
        path.write_text("\n".join(json.dumps(r) for r in rows))
        self.assertEqual(self.c.progress_counts(path, "fit"), self.c.config["counter_contracts"]["fit"])
        path.write_text(path.read_text() + '\n{"event":"optimizer-intent","global_update":3001}')
        with self.assertRaisesRegex(ValueError, "paired"):
            self.c.progress_counts(path, "fit")

    def test_native128_pairs33_roots_and_perroot_cap(self):
        rows = [dict(schema="jepa-semantic-discrimination-apply-journal/1", maxApplyCalls=128)]
        for context in range(33):
            for _ in range(4 if context < 32 else 0):
                n = sum(r.get("phase") == "beforeApply" for r in rows) + 1
                rows.extend(dict(phase=p, applyCall=n, context=str(context)) for p in ("beforeApply", "afterApply"))
            rows.append(dict(phase="contextComplete", context=str(context)))
        path = self.root / "native-journal"
        path.write_text("\n".join(json.dumps(r) for r in rows))
        self.assertEqual(self.c.progress_counts(path, "native"), dict(native_applies=128))
        rows[2]["phase"] = "applyError"
        path.write_text("\n".join(json.dumps(r) for r in rows))
        with self.assertRaisesRegex(ValueError, "successful applies"):
            self.c.progress_counts(path, "native")

    def test_baseline16_and_nonfinite_rejection(self):
        path = self.root / "ridge"
        path.write_text("\n".join(json.dumps(dict(event="numerical-fit-intent", global_fit=i)) for i in range(1, 17)))
        self.assertEqual(self.c.progress_counts(path, "baselines"), dict(numerical_fits=16))
        with self.assertRaises(ValueError):
            A.encoded(dict(x=float("nan")))
        with self.assertRaises(ValueError):
            A.counts(dict(A.zero_counts(), optimizer_updates=True))

    def test_actual_overrun_charges_actual_and_blocks_new_work(self):
        self.initialize()
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))
            state = self.c.finish(stream, rows, "completed", 4., A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
            self.assertEqual(state["charged"]["seconds"], 4.)
            self.assertTrue(state["violated"])
            self.assertEqual(state["failures"], 1)
        with self.assertRaises(ValueError):
            with self.c.lease():
                pass

    def test_failed_proof_is_opaque_not_strictly_reparsed(self):
        self.initialize()
        with self.c.lease() as (stream, rows, _):
            self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))
            raw = self.campaign / "metadata"
            raw.write_text("partial malformed journal")
            with self.assertRaisesRegex(ValueError, "failed incomplete"):
                self.c.finish(stream, rows, "failed", 0., A.zero_counts(), [A.pin(raw)], counter_proof=A.pin(raw),
                    cleanup_verified=True, execution_ended=True)
            state = self.c.finish(stream, rows, "failed", 0., A.zero_counts(), [A.pin(raw)],
                    cleanup_verified=True, execution_ended=True)
            self.assertEqual(state["charged"]["seconds"], 3.)

    def test_new_output_preexists_is_accounted_failure(self):
        self.initialize()
        (self.campaign / "metadata").write_text("old result")
        with self.c.lease() as (stream, rows, _):
            with self.assertRaisesRegex(ValueError, "exclusive NEW"):
                self.c.start(stream, rows, "metadata", self.c.metadata("metadata"))
            self.assertEqual(self.c.state(rows)["pending"]["stage"], "metadata")

    def test_spec_file_change_before_initialize_rejected(self):
        self.spec_path.write_text(self.spec_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "spec changed"):
            self.initialize()
        self.assertFalse(self.c.LEDGER.exists())

    def test_legacy_parent_without_schema_and_null_genesis(self):
        parent = self.old / "closed.jsonl"
        body = dict(sequence=0, previous_sha256=None, event="finished", data=dict(observed=None))
        row = dict(body, record_sha256=A.digest(body))
        parent.write_text(json.dumps(row) + "\n")
        prior = json.loads(self.prior.read_text())
        prior["closed_journals"] = [dict(pin=A.pin(parent), records=1, final_chain=row["record_sha256"],
                                         closed_event="finished", genesis_previous=None)]
        self.prior.write_text(json.dumps(prior))
        self.spec["prior_manifest"] = A.pin(self.prior)
        self.save_spec()
        self.assertFalse(self.c.inspect()["ledger_initialized"])


if __name__ == "__main__":
    unittest.main()
