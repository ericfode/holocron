"""Synthetic adapter tests; no actual campaign initialization/science."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("repair_accounting", Path(__file__).with_name("semantic_discrimination_repair_accounting.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.entry = self.root / "never-run.py"
        self.entry.write_text("raise RuntimeError('not executed')\n")
        self.prior = self.root / "prior.json"
        self.p = dict(schema="jepa-campaign-prior-manifest/1", carry=dict(charged_native_applies=208,
            charged_seconds=191.08889674965758, observed_native_applies=None), pins=[], protected_files=[],
            protected_roots=[], original_workspaces=[], closed_journals=[], repair_parent=dict(charged_seconds=3.,
            charged_native_applies=0, charged_neural_forwards=0, charged_optimizer_updates=0,
            final_chain="5edada95312903f7fadd809e311d42cf5cc1eeb080adc6d94e262cbbb0381f88"))
        self.prior.write_text(json.dumps(self.p))
        self.path = self.root / "campaign-spec.json"
        self.value = A.make_spec(self.root, A.pin(self.prior), {s:dict(argv=[str(Path(sys.executable).resolve()),str(self.entry)],
            outputs=[str(self.root / (s + "-out"))]) for s in A.STAGE_SECONDS}, [A.pin(sys.executable), A.pin(self.entry)], sealed=True)
        self.path.write_text(json.dumps(self.value))

    def tearDown(self):
        self.tmp.cleanup()

    def test_honest_core_adapter_pins_and_no_initialization(self):
        c = A.Campaign(self.path)
        self.assertEqual(c.config["source"], A.CORE_SOURCE)
        self.assertEqual(c.config["provenance"]["accounting_adapter"], A.pin(A.__file__))
        self.assertFalse(c.inspect()["ledger_initialized"])

    def test_old_carry_cannot_reset_three_seconds(self):
        self.p["carry"]["charged_seconds"] -= 3.
        self.prior.write_text(json.dumps(self.p))
        self.value["prior_manifest"] = A.pin(self.prior)
        self.path.write_text(json.dumps(self.value))
        with self.assertRaisesRegex(ValueError, "metadata charge"):
            A.Campaign(self.path)

    def test_missing_adapter_pin_rejected(self):
        self.value["provenance"].pop("accounting_adapter")
        self.path.write_text(json.dumps(self.value))
        with self.assertRaisesRegex(ValueError, "adapter routes"):
            A.Campaign(self.path)

    def test_same_core_failure_reservations_and_new_cumulative_ceiling(self):
        c = A.Campaign(self.path)
        c.initialize(root_go=True)  # TEMP synthetic journal only.
        with c.lease() as (stream, rows, _):
            c.start(stream, rows, "metadata", c.metadata("metadata"))
            state = c.finish(stream, rows, "failed", .001, A.zero_counts(), [], cleanup_verified=True, execution_ended=True)
            self.assertEqual(state["charged"]["seconds"], 3.)
            self.assertEqual(state["cumulative"]["charged_native_applies"], 208)
            self.assertEqual(state["cumulative"]["native_ceiling"], 336)
            self.assertEqual(state["cumulative"]["seconds_ceiling"], 309.0888967496576)
            self.assertIsNone(state["cumulative"]["observed_native_applies"])


if __name__ == "__main__":
    unittest.main()
