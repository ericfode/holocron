"""Pure quota/accounting checks; never build or launch the native collector."""
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

SPEC = importlib.util.spec_from_file_location("literal_collect_guard", Path(__file__).with_name("supervise.py"))
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class GuardTests(unittest.TestCase):
    def test_failed_attempt_remains_charged(self):
        rows = [dict(event="stage-start", stage_id="a"),
                dict(event="stage-finish", stage_id="a", status="failed", active_seconds=3.5,
                     engine_apply_attempts=7, completed_or_reserved_updates=0)]
        self.assertEqual(GUARD.ledger_totals(rows), dict(active_seconds=3.5, engine_apply_attempts=7, updates=0))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            with GUARD.CampaignLedger(path) as ledger:
                with self.assertRaisesRegex(RuntimeError, "quota"):
                    ledger.start("collect", 74, 0, {})
                with self.assertRaisesRegex(RuntimeError, "quota"):
                    ledger.start("collect", 0, 1, {})

    def test_unfinished_and_malformed_ledger_cannot_reset(self):
        for rows in ([dict(event="stage-start", stage_id="a")],
                     [dict(event="credit", active_seconds=-1)],
                     [dict(event="stage-start", stage_id="a"), dict(event="stage-finish", stage_id="b")],
                     [dict(event="stage-start", stage_id="a"),
                      dict(event="stage-finish", stage_id="a", active_seconds=float("nan"), engine_apply_attempts=0, completed_or_reserved_updates=0)]):
            with self.subTest(rows=rows), self.assertRaises(RuntimeError):
                GUARD.ledger_totals(rows)

    def test_durable_attempts_include_failed_engine_call(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "native.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in [
                dict(phase="beforeApply", applyCall=1), dict(phase="afterApply", applyCall=1),
                dict(phase="beforeApply", applyCall=2)]) + "\n")
            self.assertEqual(GUARD.count_applies(path), 2)
            path.write_text(json.dumps(dict(phase="beforeApply", applyCall=2)) + "\n")
            with self.assertRaisesRegex(RuntimeError, "nonsequential"):
                GUARD.count_applies(path)

    def test_guard_has_no_fit_or_evaluation_mode(self):
        self.assertEqual((GUARD.MAX_SECONDS, GUARD.MAX_APPLIES, GUARD.MAX_UPDATES, GUARD.MAX_BYTES), (60., 80, 0, 1024**3))
        for stage in ("fit", "evaluate", "credit"):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "collect"):
                GUARD.run(types.SimpleNamespace(stage=stage))


if __name__ == "__main__":
    unittest.main()
