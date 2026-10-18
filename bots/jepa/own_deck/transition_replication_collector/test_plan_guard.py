"""Pure plan/quota boundaries: no compiler, engine, workers, or fitting."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("replication_supervise",HERE/"supervise.py")
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


class PlanAndQuotaTests(unittest.TestCase):
    def test_predeclared_four_cells_and_real_distinct_states(self):
        plan=json.loads((HERE/"collection-plan.json").read_text())
        self.assertEqual(len(plan["programs"]),12);self.assertEqual(len(plan["contexts"]),14)
        self.assertEqual((len(plan["train_codes"]),len(plan["heldout_codes"])),(10,2))
        self.assertFalse(set(plan["train_codes"])&set(plan["heldout_codes"]))
        actual=[json.dumps({k:v for k,v in context.items() if k not in ("id","name","partition")},sort_keys=True) for context in plan["contexts"]]
        self.assertEqual(len(set(actual)),14,"a target-focus label is not a new physical world state")
        self.assertEqual((10*10,2*10,10*4,2*4),(100,20,40,8))
        bound=len(plan["programs"])*len(plan["contexts"])*(1+1+1+len(plan["candidate_order"])+1)
        self.assertEqual(bound,2016);self.assertEqual(bound,plan["collector_max_engine_applies"])
        self.assertLessEqual(bound,S.MAX_APPLIES)

    def test_replication_identity_and_budget_contract(self):
        plan=json.loads((HERE/"collection-plan.json").read_text())
        prior=json.loads((HERE.parent/"grounded_native_collector/collection-plan.json").read_text())
        self.assertEqual(set(plan["heldout_codes"]),{"SHD_004","TWI_206"})
        self.assertFalse(set(plan["heldout_codes"])&{p["code"] for p in prior["programs"]})
        self.assertEqual(plan["train_codes"],prior["train_codes"])
        self.assertEqual((plan["campaign_max_seconds"],plan["campaign_max_updates"],plan["campaign_max_engine_applies"]),
                         (S.MAX_SECONDS,S.MAX_UPDATES,S.MAX_APPLIES))
        expected=json.loads(json.dumps(prior["contexts"]))
        expected[12]["ready_resources"]=2
        self.assertEqual([{k:v for k,v in c.items() if k!="name"} for c in plan["contexts"]],expected)
        aliases={"train":set(),"heldout":set()}
        groups={"train":set(),"heldout":set()}
        for program in plan["programs"]:
            partition=program["partition"]
            aliases[partition].update(program["aliases"])
            groups[partition].add(program["program_group_id"])
            self.assertEqual(program["index"],0)
            self.assertEqual(program["all_side_ability_counts"][program["side"]],1)
            self.assertEqual(program["raw_ability"]["trigger"],"action")
        self.assertFalse(aliases["train"]&aliases["heldout"])
        self.assertFalse(groups["train"]&groups["heldout"])

    def test_prior_failed_attempt_debits_never_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ledger.jsonl"
            with S.CampaignLedger(path) as ledger:
                ledger.start("collect",2016,0,{})
                ledger.finish(40,0,"failed")
            with S.CampaignLedger(path) as ledger:
                self.assertEqual(ledger.totals["engine_apply_attempts"],40)
                with self.assertRaises(RuntimeError):ledger.start("collect",2016,0,{})
                ledger.start("fit",0,4800,{})
                ledger.finish(0,4800,"failed")
            with S.CampaignLedger(path) as ledger:
                with self.assertRaises(RuntimeError):ledger.start("fit-retry",0,1,{})

    def test_attempt_journals_count_only_real_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"applies.jsonl"
            rows=[dict(phase="beforeApply",applyCall=1),dict(phase="applyError",applyCall=1),dict(phase="beforeApply",applyCall=2)]
            path.write_text(''.join(json.dumps(row)+"\n" for row in rows))
            self.assertEqual(S.count_applies(path),2)
            path.write_text(''.join(json.dumps(dict(updates_completed=i))+"\n" for i in range(1,S.MAX_UPDATES+1)))
            self.assertEqual(S.update_debit(path,4800,"completed"),(4800,"completed","exact completed-step journal"))
            self.assertEqual(S.update_debit(path,4800,"failed")[0],4800)

    def test_python_entrypoints_checked_without_running_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/"main.py";script.write_text("raise RuntimeError('must never execute')\n")
            self.assertTrue(S.python_main_entry(["python3",str(script)])["path"].is_file())
            with self.assertRaises(ValueError):S.python_main_entry(["python3",str(script.parent/"missing.py")])
            with self.assertRaises(ValueError):S.python_main_entry(["python3","-c","print('no')"])

    def test_global_journal_stage_deltas_and_conservative_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"updates.jsonl"
            rows=lambda n: b''.join((json.dumps(dict(updates_completed=i))+"\n").encode() for i in range(1,n+1))
            initial=rows(2400)
            path.write_bytes(rows(4800))
            self.assertEqual(S.update_debit(path,2400,"completed",2400,initial),
                             (2400,"completed","exact completed-step journal"))
            path.write_bytes(rows(2500))
            self.assertEqual(S.update_debit(path,2400,"failed",2400,initial)[0],2400)
            self.assertEqual(S.update_debit(path,2400,"completed",2400,initial)[1],"failed")
            path.write_bytes(rows(4800).replace(b'{"updates_completed": 1}',b'{"updates_completed": 1,"changed":true}',1))
            self.assertEqual(S.update_debit(path,2400,"completed",2400,initial)[1],"failed")

    def test_fit_offset_ledger_and_journal_must_reconcile_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"updates.jsonl";ledger=Path(tmp)/"campaign.jsonl"
            path.write_text(''.join(json.dumps(dict(updates_completed=i))+"\n" for i in range(1,2401)))
            entry={"arguments":["--fit","--update-offset","2400","--progress",str(path),"--ledger",str(ledger)]}
            self.assertEqual(S.fit_progress_baseline(path,2400,entry,ledger)[0],2400)
            with self.assertRaises(ValueError):S.fit_progress_baseline(path,4800,entry,ledger)
            entry["arguments"][2]="0"
            with self.assertRaises(ValueError):S.fit_progress_baseline(path,2400,entry,ledger)
            entry["arguments"][2]="2400";entry["arguments"][-1]=str(Path(tmp)/"different.jsonl")
            with self.assertRaises(ValueError):S.fit_progress_baseline(path,2400,entry,ledger)

    def test_evaluation_is_zero_update_and_byte_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"updates.jsonl";ledger=Path(tmp)/"ledger.jsonl"
            initial=b''.join((json.dumps(dict(updates_completed=i))+"\n").encode() for i in range(1,4801))
            path.write_bytes(initial)
            entry={"arguments":["--evaluate","--update-offset","4800","--progress",str(path),"--ledger",str(ledger)]}
            self.assertEqual(S.fit_progress_baseline(path,4800,entry,ledger,evaluate=True)[0],4800)
            self.assertEqual(S.evaluation_debit(path,"completed",4800,initial),
                             (0,"completed","evaluation global update journal byte-identical; zero new updates"))
            path.write_bytes(initial+b'{"updates_completed":4801}\n')
            self.assertEqual(S.evaluation_debit(path,"completed",4800,initial)[:2],(0,"failed"))
            path.write_bytes(initial.replace(b'{"updates_completed": 1}',b'{"updates_completed": 1,"changed":true}',1))
            self.assertEqual(S.evaluation_debit(path,"completed",4800,initial)[:2],(0,"failed"))
            path.unlink()
            self.assertEqual(S.evaluation_debit(path,"completed",4800,initial)[:2],(0,"failed"))


if __name__=="__main__":unittest.main()
