"""Pure quota/journal checks. No compiler, engine, worker, or optimizer runs."""
import importlib.util
import ast
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("supported_supervise",Path(__file__).with_name("supervise.py"))
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)


class QuotaTests(unittest.TestCase):
    def test_prior_failed_attempts_spend_time_and_calls(self):
        rows=[dict(event="stage-start",stage_id="a"),dict(event="stage-finish",stage_id="a",active_seconds=3.2,engine_apply_attempts=7,completed_or_reserved_updates=0,status="failed"),
              dict(event="stage-start",stage_id="b"),dict(event="stage-finish",stage_id="b",active_seconds=4.,engine_apply_attempts=0,completed_or_reserved_updates=600,status="failed")]
        self.assertEqual(S.ledger_totals(rows),dict(active_seconds=7.2,engine_apply_attempts=7,updates=600))

    def test_unfinished_or_nonfinite_ledgers_fail_closed(self):
        for rows in ([dict(event="stage-start",stage_id="a")],[dict(event="stage-start",stage_id="a"),dict(event="stage-finish",stage_id="a",active_seconds=float("nan"),engine_apply_attempts=0,completed_or_reserved_updates=0)]):
            with self.assertRaises(RuntimeError): S.ledger_totals(rows)

    def test_lease_preserves_debits_and_rejects_quota_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ledger.jsonl"
            with S.CampaignLedger(path) as lease:
                lease.start("collect",64,0,{})
                lease.finish(34,0,"completed")
            with S.CampaignLedger(path) as lease:
                self.assertEqual(lease.totals["engine_apply_attempts"],34)
                with self.assertRaises(RuntimeError): lease.start("collect-retry",64,0,{})
                lease.start("fit",0,600,{})
                lease.finish(0,600,"failed")
            with S.CampaignLedger(path) as lease:
                with self.assertRaises(RuntimeError): lease.start("fit-retry",0,1,{})

    def test_before_apply_and_progress_records_are_counted_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"apply.jsonl"
            path.write_text('\n'.join(json.dumps(row) for row in [dict(phase="beforeApply",applyCall=1),dict(phase="applyError",applyCall=1),dict(phase="beforeApply",applyCall=2)])+'\n')
            self.assertEqual(S.count_applies(path),2)
            path.write_text(''.join(json.dumps(dict(updates_completed=i))+"\n" for i in range(1,6)))
            self.assertEqual(S.count_updates(path),5)
            path.write_text('{"updates_completed":5}\n{"updates_completed":4}\n')
            with self.assertRaises(RuntimeError): S.count_updates(path)

    def test_actual_trainer_progress_record_interoperates_and_failure_keeps_reservation(self):
        trainer=Path(__file__).parents[1]/"train_structured_transition.py"
        syntax=ast.parse(trainer.read_text())
        records=[node for node in ast.walk(syntax) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="dict"
                 and {key.arg for key in node.keywords}=={"updates_completed","arm","arm_step"}]
        self.assertEqual(len(records),1,"trainer's dedicated progress schema changed")
        expression=ast.Expression(records[0]); ast.fix_missing_locations(expression)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"progress.jsonl"
            with path.open("w") as stream:
                for completed in range(1,601):
                    record=eval(compile(expression,"<actual trainer progress>","eval"),{"completed":completed,"arm":"correct-ir","step":completed,"dict":dict})
                    stream.write(json.dumps(record)+"\n")
            self.assertEqual(S.update_debit(path,600,"completed"),(600,"completed","exact completed-step journal"))
            path.write_text('{"updates_completed":1}\n')
            debit,status,_=S.update_debit(path,600,"failed")
            self.assertEqual((debit,status),(600,"failed"))
            debit,status,_=S.update_debit(path,600,"completed")
            self.assertEqual((debit,status),(600,"failed"))


if __name__=="__main__": unittest.main()
