"""Pure quota/journal checks. No compiler, engine, worker, or optimizer runs."""
import importlib.util
import ast
import argparse
import copy
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location("supported_supervise",Path(__file__).with_name("supervise.py"))
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)


def missing_main_fixture(root):
    ledger=root/"ledger.jsonl"; guard=root/"guard"; guard.mkdir()
    progress=root/"progress.jsonl"; output=root/"fit"; events=root/"events.jsonl"
    events.write_text('{"run_id":"some-other-run"}\n')
    script=root/"absent"/"trainer.py"
    command=["env","OMP_NUM_THREADS=1",sys.executable,str(script),"--progress",str(progress),"--out",str(output),
             "--events",str(events),"--run-id","never-started","--ledger",str(ledger)]
    prior=dict(active_seconds=2.,engine_apply_attempts=32,updates=0)
    start=dict(event="stage-start",stage="fit",stage_id="fit-test",reserved_applies=0,reserved_updates=600,prior=prior,
               metadata=dict(commands=[["fit",command]],campaign_ledger=str(ledger)))
    finish=dict(event="stage-finish",stage_id="fit-test",status="failed",active_seconds=.05,engine_apply_attempts=0,completed_or_reserved_updates=600)
    rows=[start,finish]
    ledger.write_text(''.join(json.dumps(row)+"\n" for row in rows))
    receipt=guard/"supervisor-receipt.json"
    value=dict(stage="fit",status="failed",commands=[["fit",command]],prior_campaign_debits=prior,campaign_ledger=str(ledger),
               reserved_updates=600,completed_or_reserved_updates=600,engine_apply_attempts=0,error="RuntimeError: fit exited 2",
               phases=[dict(name="fit",command=command,exit_code=2)])
    receipt.write_text(json.dumps(value))
    stderr=guard/"fit.stderr.log"; stdout=guard/"fit.stdout.log"
    stderr.write_text(f"{sys.executable}: can't open file '{script}': [Errno 2] No such file or directory\n")
    stdout.write_bytes(b"")
    return dict(rows=rows,ledger=ledger,receipt=receipt,stderr=stderr,stdout=stdout,script=script,
                progress=progress,output=output,events=events)


def proof(f):
    return S.verify_missing_main_credit(f["rows"],f["ledger"],f["receipt"],S.sha(f["receipt"]),S.sha(f["stderr"]))


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
                    record=eval(compile(expression,"<actual trainer progress>","eval"),{"completed":completed,"total":completed,"arm":"correct-ir","step":completed,"dict":dict})
                    stream.write(json.dumps(record)+"\n")
            self.assertEqual(S.update_debit(path,600,"completed"),(600,"completed","exact completed-step journal"))
            path.write_text('{"updates_completed":1}\n')
            debit,status,_=S.update_debit(path,600,"failed")
            self.assertEqual((debit,status),(600,"failed"))
            debit,status,_=S.update_debit(path,600,"completed")
            self.assertEqual((debit,status),(600,"failed"))

    def test_missing_main_credit_preserves_raw_failure_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=missing_main_fixture(Path(tmp)); before=f["ledger"].read_bytes()
            result=S.missing_main_credit(f["ledger"],f["receipt"],S.sha(f["receipt"]),S.sha(f["stderr"]))
            self.assertEqual(f["ledger"].read_bytes(),before)
            self.assertEqual(result["before"]["updates"],600)
            self.assertEqual(result["after"]["updates"],0)
            self.assertEqual(result["before"]["active_seconds"],result["after"]["active_seconds"])
            self.assertEqual(result["before"]["engine_apply_attempts"],result["after"]["engine_apply_attempts"])
            self.assertEqual(result["credit_event"]["proof"]["actual_updates_verified"],0)
            self.assertEqual(f["rows"][-1]["completed_or_reserved_updates"],600)

    def test_credit_rejects_any_trainer_entry_or_progress_evidence(self):
        for evidence in ("progress-empty","progress-update","output","events","main","stdout"):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as tmp:
                f=missing_main_fixture(Path(tmp))
                if evidence=="progress-empty": f["progress"].touch()
                if evidence=="progress-update": f["progress"].write_text('{"updates_completed":1}\n')
                if evidence=="output": f["output"].mkdir()
                if evidence=="events": f["events"].write_text('{"run_id":"never-started","step":0}\n')
                if evidence=="main": f["script"].parent.mkdir(); f["script"].touch()
                if evidence=="stdout": f["stdout"].write_text("trainer started\n")
                with self.assertRaises(ValueError): proof(f)

    def test_credit_rejects_altered_hashes_diagnostics_and_runtime_failure(self):
        for changed in ("receipt-hash","stderr-hash","diagnostic","exit","runtime"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                f=missing_main_fixture(Path(tmp))
                receipt_hash,stderr_hash=S.sha(f["receipt"]),S.sha(f["stderr"])
                if changed=="receipt-hash": f["receipt"].write_text(f["receipt"].read_text()+" ")
                if changed=="stderr-hash": f["stderr"].write_text(f["stderr"].read_text()+" ")
                if changed=="diagnostic": f["stderr"].write_text("Traceback: trainer failed\n"); stderr_hash=S.sha(f["stderr"])
                if changed in ("exit","runtime"):
                    value=json.loads(f["receipt"].read_text())
                    if changed=="exit": value["phases"][0]["exit_code"]=1
                    else: value["error"]="RuntimeError: optimizer stopped"
                    f["receipt"].write_text(json.dumps(value)); receipt_hash=S.sha(f["receipt"])
                with self.assertRaises(ValueError): S.verify_missing_main_credit(f["rows"],f["ledger"],f["receipt"],receipt_hash,stderr_hash)

    def test_credit_rejects_duplicate_later_or_unfinished_stage_and_forged_amount(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=missing_main_fixture(Path(tmp)); credit=proof(f)
            with self.assertRaises((ValueError,RuntimeError)): S.verify_missing_main_credit([*f["rows"],credit],f["ledger"],f["receipt"],S.sha(f["receipt"]),S.sha(f["stderr"]))
            with self.assertRaises(RuntimeError): S.ledger_totals([*f["rows"],credit,credit])
            extra=dict(event="stage-start",stage="fit",stage_id="new",reserved_updates=600)
            with self.assertRaises((ValueError,RuntimeError)): S.verify_missing_main_credit([*f["rows"],extra],f["ledger"],f["receipt"],S.sha(f["receipt"]),S.sha(f["stderr"]))
            altered=copy.deepcopy(credit); altered["updates_credited"]=601
            with self.assertRaises(RuntimeError): S.ledger_totals([*f["rows"],altered])
            altered=copy.deepcopy(credit); altered["proof"]["finish_record_sha256"]="0"*64
            with self.assertRaises(RuntimeError): S.ledger_totals([*f["rows"],altered])

    def test_missing_python_entrypoint_rejects_before_stage_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            args=argparse.Namespace(stage="fit",command=[sys.executable,str(root/"missing.py")],progress=root/"progress",max_updates=600,target_dir=root)
            with mock.patch.object(S,"preflight",return_value={}), mock.patch.object(S,"CampaignLedger") as lease:
                with self.assertRaisesRegex(ValueError,"main entrypoint does not exist"): S.run(args)
            lease.assert_not_called()


if __name__=="__main__": unittest.main()
