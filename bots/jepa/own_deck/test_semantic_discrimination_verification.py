"""Synthetic journal/fence tests only; no saved experiment/helper invocation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import types
import unittest

spec = importlib.util.spec_from_file_location("postprocess", Path(__file__).with_name("semantic_discrimination_verification.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        # Synthetic Journal object; production constructor still enforces its
        # canonical root. No production ledger/spec is created by these tests.
        self.j = V.Journal.__new__(V.Journal)
        self.j.ledger = self.root / "ledger.jsonl"
        self.j.path = self.root / "spec.json"
        self.j.path.write_text("{}")
        self.j.spec_pin = V.pin(self.j.path)
        self.j.spec = dict(argv=["/never-executed", "run"], pins=[], source=V.pin(V.__file__), helper=V.pin(V.__file__),
                           guard=V.pin(V.__file__), parent_ledger=V.pin(self.j.path))

    def tearDown(self):
        self.tmp.cleanup()

    def begin(self):
        stream = self.j.ledger.open("x+")
        rows = []
        self.j.append(stream, rows, "initialized", dict(spec=self.j.spec_pin, parent=V.PARENT, reservation_seconds=5.))
        self.j.append(stream, rows, "verify-start", dict(argv=self.j.spec["argv"], reservation_seconds=5.,
            started_monotonic_seconds=time.monotonic(), owner_pid=1))
        return stream, rows

    def test_failed_full_five_charge_parent_unchanged(self):
        stream, rows = self.begin()
        with stream:
            state = self.j.append(stream, rows, "verify-finish", dict(status="failed", active_seconds=.1,
                charged_seconds=5., cleanup_verified=True, new_exposure=V.zero_counts()))
        self.assertEqual(state["charged_seconds"], 5.)
        self.assertEqual(state["cumulative"]["charged_native_applies"], 275)
        self.assertEqual(state["cumulative"]["charged_seconds"], 219.23341095773503)
        self.assertIsNone(state["cumulative"]["observed_native_applies"])

    def test_once_only_and_pending_cannot_be_cleared(self):
        stream, rows = self.begin()
        with stream:
            self.j.append(stream, rows, "pending-failure", dict(error="cleanup unknown"))
            with self.assertRaises(ValueError):
                self.j.append(stream, rows, "verify-finish", dict(status="failed", active_seconds=.1,
                    charged_seconds=5., cleanup_verified=True, new_exposure=V.zero_counts()))
        with self.assertRaises(ValueError):
            with self.j.lease():
                pass

    def test_actual_overrun_and_nonzero_science_rejected(self):
        stream, rows = self.begin()
        with stream:
            with self.assertRaises(ValueError):
                self.j.append(stream, rows, "verify-finish", dict(status="completed", active_seconds=6.,
                    charged_seconds=6., cleanup_verified=True, new_exposure=V.zero_counts()))
            with self.assertRaises(ValueError):
                self.j.append(stream, rows, "verify-finish", dict(status="failed", active_seconds=1.,
                    charged_seconds=5., cleanup_verified=True, new_exposure=dict(V.zero_counts(), neural_forwards=1)))
            state = self.j.append(stream, rows, "verify-finish", dict(status="failed", active_seconds=6.,
                charged_seconds=6., cleanup_verified=True, new_exposure=V.zero_counts()))
            self.assertEqual(state["charged_seconds"], 6.)

    def test_nan_serialization_before_creation_and_tamper(self):
        out = self.root / "output"
        with self.assertRaises(ValueError):
            V.write_new(out, dict(x=float("nan")))
        self.assertFalse(out.exists())
        stream, rows = self.begin()
        with stream:
            rows[-1]["data"]["reservation_seconds"] = 0.
            with self.assertRaisesRegex(ValueError, "damaged"):
                self.j.state(rows)

    def test_science_fence_restores_fit_functions(self):
        def original(*_):
            return "not-called"
        fake = types.SimpleNamespace(linalg=types.SimpleNamespace(lstsq=original, solve=original, pinv=original))
        with V.science_fence(fake) as violations:
            with self.assertRaisesRegex(RuntimeError, "no numerical fits"):
                fake.linalg.lstsq()
            self.assertEqual(violations, ["numerical-fit"])
        self.assertIs(fake.linalg.lstsq, original)

    def test_scientific_fail_result_is_preserved_before_failure(self):
        path = self.root / "saved-failure.json"
        result = dict(status="FAIL-saved-verification", mismatches=[dict(check="synthetic", got=2, expected=1)])
        with self.assertRaisesRegex(ValueError, "did not pass"):
            V.preserve_verification_result(path, result)
        self.assertEqual(json.loads(path.read_text()), result)


if __name__ == "__main__":
    unittest.main()
