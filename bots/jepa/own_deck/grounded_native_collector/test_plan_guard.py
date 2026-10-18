"""Pure plan/quota boundaries: no compiler, engine, workers, or fitting."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("grounded_supervise",HERE/"supervise.py")
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


class PlanAndQuotaTests(unittest.TestCase):
    def test_predeclared_four_cells_and_real_distinct_states(self):
        plan=json.loads((HERE/"collection-plan.json").read_text())
        self.assertEqual(len(plan["programs"]),12);self.assertEqual(len(plan["contexts"]),14)
        self.assertEqual((len(plan["train_codes"]),len(plan["heldout_codes"])),(10,2))
        self.assertFalse(set(plan["train_codes"])&set(plan["heldout_codes"]))
        actual=[json.dumps({k:v for k,v in context.items() if k not in ("id","partition")},sort_keys=True) for context in plan["contexts"]]
        self.assertEqual(len(set(actual)),14,"a target-focus label is not a new physical world state")
        self.assertEqual((10*10,2*10,10*4,2*4),(100,20,40,8))
        bound=len(plan["programs"])*len(plan["contexts"])*(1+1+1+len(plan["candidate_order"])+1)
        self.assertEqual(bound,2016);self.assertEqual(bound,plan["collector_max_engine_applies"])
        self.assertLessEqual(bound,S.MAX_APPLIES)

    def test_prior_failed_attempt_debits_never_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ledger.jsonl"
            with S.CampaignLedger(path) as ledger:
                ledger.start("collect",2016,0,{})
                ledger.finish(40,0,"failed")
            with S.CampaignLedger(path) as ledger:
                self.assertEqual(ledger.totals["engine_apply_attempts"],40)
                with self.assertRaises(RuntimeError):ledger.start("collect",2016,0,{})
                ledger.start("fit",0,2400,{})
                ledger.finish(0,2400,"failed")
            with S.CampaignLedger(path) as ledger:
                with self.assertRaises(RuntimeError):ledger.start("fit-retry",0,1,{})

    def test_attempt_journals_count_only_real_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"applies.jsonl"
            rows=[dict(phase="beforeApply",applyCall=1),dict(phase="applyError",applyCall=1),dict(phase="beforeApply",applyCall=2)]
            path.write_text(''.join(json.dumps(row)+"\n" for row in rows))
            self.assertEqual(S.count_applies(path),2)
            path.write_text(''.join(json.dumps(dict(updates_completed=i))+"\n" for i in range(1,2401)))
            self.assertEqual(S.update_debit(path,2400,"completed"),(2400,"completed","exact completed-step journal"))
            self.assertEqual(S.update_debit(path,2400,"failed")[0],2400)

    def test_python_entrypoints_checked_without_running_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/"main.py";script.write_text("raise RuntimeError('must never execute')\n")
            self.assertTrue(S.python_main_entry(["python3",str(script)])["path"].is_file())
            with self.assertRaises(ValueError):S.python_main_entry(["python3",str(script.parent/"missing.py")])
            with self.assertRaises(ValueError):S.python_main_entry(["python3","-c","print('no')"])


if __name__=="__main__":unittest.main()
