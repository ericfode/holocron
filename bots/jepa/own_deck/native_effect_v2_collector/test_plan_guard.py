"""Pure quota/accounting checks; never build or launch the native collector."""
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("native_effect_v2_collect_guard", Path(__file__).with_name("supervise.py"))
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class GuardTests(unittest.TestCase):
    def initialized(self,path,frozen=True):
        a=GUARD.accounting();a.initialize(path,{"test":True})
        if frozen:
            config=dict(limits=a.CAPS,arms=["a","b","c","d"],updates_per_arm=1,optimizer_updates=4,
                        training_forwards=4,evaluation_forwards=0,export_forwards=0,pins=[{"test":"pure"}])
            config["config_sha256"]=a.digest(config)
            with a.lease(path) as (stream,rows,current):a.append(stream,rows,path,"frozen",config)
        return a

    def test_failed_attempt_remains_charged(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            a=self.initialized(path)
            with GUARD.CampaignLedger(path) as ledger:
                ledger.start("collect",240,0,{"test":True})
                ledger.finish(7,0,"failed",True)
            with GUARD.CampaignLedger(path) as ledger:
                self.assertEqual(ledger.totals["engine_apply_attempts"],7)
                self.assertGreater(ledger.totals["active_seconds"],0)
                with self.assertRaisesRegex(ValueError, "allocation"):
                    ledger.start("collect", 250, 0, {})
                with self.assertRaisesRegex(ValueError, "collect"):
                    ledger.start("collect", 0, 1, {})

    def test_unfinished_and_malformed_ledger_cannot_reset(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"ledger.jsonl";a=self.initialized(path)
            with GUARD.CampaignLedger(path) as ledger:ledger.start("collect",240,0,{})
            with self.assertRaisesRegex(ValueError,"unfinished"):
                with GUARD.CampaignLedger(path):pass
            rows=[json.loads(line)for line in path.read_text().splitlines()]
            rows[0]["data"]["metadata"]={"tampered":True}
            with self.assertRaisesRegex(ValueError,"hash chain"):
                a.state(rows,path)

    def test_unfrozen_campaign_and_overlapping_leases_block_launch(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"ledger.jsonl";self.initialized(path,False)
            with GUARD.CampaignLedger(path)as ledger:
                with self.assertRaisesRegex(ValueError,"frozen"):
                    ledger.start("collect",240,0,{})
                with self.assertRaises(BlockingIOError):
                    with GUARD.CampaignLedger(path):pass

    def test_missing_collector_journal_conservatively_debits_reservation(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"trace.jsonl"
            self.assertEqual(GUARD.journal_debit(p,False,240),(0,True))
            self.assertEqual(GUARD.journal_debit(p,True,240),(240,False))
            p.write_text('{"phase":"beforeApply","applyCall":2}\n')
            self.assertEqual(GUARD.journal_debit(p,True,240),(240,False))

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
        self.assertEqual((GUARD.MAX_SECONDS, GUARD.MAX_APPLIES, GUARD.MAX_UPDATES, GUARD.MAX_BYTES), (90., 256, 0, 1024**3))
        for stage in ("fit", "evaluate", "credit"):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "collect"):
                GUARD.run(types.SimpleNamespace(stage=stage))

    def test_sequential_compilers_do_not_accumulate_as_concurrent_memory(self):
        mib=1024**2;receipt=dict(observed_per_pid_peak_bytes={})
        first=GUARD.memory_sample(receipt,{1:100*mib,2:600*mib},1,100*mib)
        second=GUARD.memory_sample(receipt,{1:100*mib,3:600*mib},1,100*mib)
        self.assertEqual((first,second),(700*mib,700*mib))
        self.assertGreater(sum(receipt['observed_per_pid_peak_bytes'].values()),GUARD.MAX_BYTES)
        self.assertLess(second,GUARD.MAX_BYTES)
        concurrent=GUARD.memory_sample(receipt,{1:100*mib,2:600*mib,3:600*mib},1,100*mib)
        self.assertEqual(concurrent,1300*mib)
        self.assertGreater(concurrent,GUARD.MAX_BYTES)

    def test_rusage_supplements_live_peak_without_summing_dead_children(self):
        mib=1024**2
        self.assertEqual(GUARD.final_memory_bound(700*mib,120*mib,700*mib),820*mib)
        self.assertEqual(GUARD.final_memory_bound(900*mib,120*mib,700*mib),900*mib)
        with self.assertRaises(RuntimeError):
            GUARD.memory_sample(dict(observed_per_pid_peak_bytes={}),{2:600*mib},1,100*mib)

    def test_only_confirmed_exited_owned_pid_skips_are_recorded(self):
        def rss(pid):
            if pid==2:raise OSError(3,'owned PID vanished')
            if pid==3:raise OSError(1,'permission denied')
            return 100
        receipt={}
        self.assertEqual(GUARD.read_owned_rss(receipt,[2,4],rss,1,.25),{1:100,4:100})
        row=receipt['exited_owned_pid_skips'][0]
        self.assertEqual((row['pid'],row['errno'],row['elapsed_seconds']),(2,3,.25))
        self.assertIn('vanished',row['error'])
        with self.assertRaises(PermissionError):GUARD.read_owned_rss({},[3],rss,1,.3)

    def test_build_restores_cached_partitioning_without_semantic_flag_changes(self):
        with patch.dict(GUARD.os.environ,{},clear=True):
            env=GUARD.build_environment(Path('/tmp/guard-test-cache'))
        self.assertEqual(env['CARGO_BUILD_JOBS'],'1')
        self.assertEqual(env['CARGO_PROFILE_DEV_DEBUG'],'0')
        self.assertEqual(env['CARGO_PROFILE_DEV_INCREMENTAL'],'false')
        self.assertNotIn('CARGO_PROFILE_DEV_CODEGEN_UNITS',env)
        self.assertNotIn('RUSTFLAGS',env);self.assertNotIn('CARGO_ENCODED_RUSTFLAGS',env)
        for key,value in [('RUSTFLAGS','-C panic=abort'),('CARGO_PROFILE_DEV_CODEGEN_UNITS','1'),('CARGO_PROFILE_DEV_OPT_LEVEL','2')]:
            with self.subTest(key=key),patch.dict(GUARD.os.environ,{key:value},clear=True),self.assertRaisesRegex(ValueError,'unfrozen'):
                GUARD.build_environment(Path('/tmp/guard-test-cache'))


if __name__ == "__main__":
    unittest.main()
