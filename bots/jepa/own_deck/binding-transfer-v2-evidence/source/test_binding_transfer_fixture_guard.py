import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import binding_transfer_fixture_guard as G


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name in('ROOT','CONFIG','LEDGER'):
            value=self.root if name=='ROOT'else self.root/('config.json'if name=='CONFIG'else'campaign-ledger.jsonl')
            p=patch.object(G,name,value);p.start();self.addCleanup(p.stop)
        self.input=self.root/'source';self.input.write_text('immutable')
        self.binary=self.root/'target'/'debug'/G.BIN;self.binary.parent.mkdir(parents=True);self.binary.write_text('synthetic-not-executable')
        stages={}
        for stage,seconds in G.STAGES.items():
            out=self.root/(stage+'-1');argv=['/cargo','build','--offline','--locked','--manifest-path','/crate/Cargo.toml','--bin',G.BIN,'-j','1']if stage=='build'else[str(self.binary),'--validate-fixtures-only',str(out/'validation.json')]
            stages[stage]=dict(argv=argv,cwd=str(self.root),out=str(out),receipt=str(self.root/(stage+'-1-stage-receipt.json')),seconds=seconds)
        self.config=dict(schema='jepa-zero-apply-fixture-guard/1',root=str(self.root),ledger_path=str(G.LEDGER),caps=G.CAPS,
            helper=dict(sha256=G.HELPER_SHA),source=G.pin(G.__file__),pins=[G.pin(self.input)],stages=stages,
            binary=str(self.binary),target_dir=str(self.binary.parent.parent),collection_plan=str(self.input),parent=dict(charged_native_applies=160,charged_seconds=110.10179149871692))
        self.save_config()

    def save_config(self):
        self.config.pop('config_sha256',None);self.config['config_sha256']=G.digest(self.config)
        G.CONFIG.write_text(json.dumps(self.config))

    def start(self,stage='build'):
        G.initialize()
        with G.LEDGER.open('r+')as stream:
            rows=G.read_lines(G.LEDGER);stream.seek(0,2)
            G.append(stream,rows,'stage-start',dict(stage=stage,owner_pid=123,reserved_seconds=G.STAGES[stage],reserved_calls=G.ZERO))
        return rows

    def test_import_has_no_neural_or_numerical_import(self):
        code='import sys; import binding_transfer_fixture_guard; assert "torch" not in sys.modules and "numpy" not in sys.modules'
        subprocess.run([sys.executable,'-B','-c',code],cwd=Path(G.__file__).parent,check=True,capture_output=True)

    def test_unique_forced_cli_and_fixed_caps(self):
        G.validate_config(self.config)
        self.assertEqual(G.CAPS['seconds'],25.);self.assertEqual(G.ZERO['engine_apply_invocations'],0)
        self.config['stages']['validate']['argv'][1]='--collect';self.save_config()
        with self.assertRaisesRegex(ValueError,'forced zero-call'):G.validate_config(self.config)

    def test_canonical_copy_and_initialize_reset_rejected(self):
        with self.assertRaisesRegex(ValueError,'canonical'):G.initialize(self.root/'copied-config.json')
        G.initialize();before=G.LEDGER.read_bytes()
        with self.assertRaises(FileExistsError):G.initialize()
        self.assertEqual(before,G.LEDGER.read_bytes())
        self.config['ledger_path']=str(self.root/'copied-ledger');self.save_config()
        with self.assertRaisesRegex(ValueError,'canonical'):G.validate_config(self.config)

    def test_pending_blocks_new_stages_and_chain_tampering(self):
        self.start()
        with self.assertRaisesRegex(RuntimeError,'pending'):
            with G.lease():self.fail('must not acquire pending work')
        rows=G.read_lines(G.LEDGER);rows[-1]['data']['reserved_seconds']=0
        with self.assertRaisesRegex(ValueError,'chain'):G.state(rows)

    def test_failed_stage_full_debit_and_no_retry(self):
        rows=self.start()
        with G.LEDGER.open('a')as stream:
            G.append(stream,rows,'stage-finish',dict(stage='build',status='failed',active_seconds=.1,charged_seconds=15.,cleanup_verified=True,observed_calls=G.ZERO,proofs=[]))
        self.assertEqual(G.state(rows)['charged_seconds'],15.)
        with self.assertRaisesRegex(RuntimeError,'once-only'):G.run('build')

    def test_receipt_write_time_downgrades_authoritative_status(self):
        self.assertEqual(G.terminal_status('completed',15.01,15.),('failed',15.01))
        self.assertEqual(G.terminal_status('completed',14.,15.),('completed',14.))
        self.assertEqual(G.terminal_status('failed',.1,15.),('failed',15.))

    def test_changed_input_reserves_and_closes_failure_before_launch(self):
        G.initialize();self.input.write_text('changed')
        with patch.object(G.subprocess,'Popen',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(RuntimeError,'failed zero-call'):G.run('build')
        rows=G.read_lines(G.LEDGER);state=G.state(rows)
        self.assertIsNone(state['pending']);self.assertEqual(state['charged_seconds'],15.)
        self.assertEqual(rows[1]['event'],'stage-start');self.assertTrue((self.root/'build-1-stage-receipt.json').exists());self.assertFalse((self.root/'build-1').exists())

    def test_cleanup_uncertainty_retains_pending_and_receipt(self):
        G.initialize()
        helper=SimpleNamespace(process_readers=lambda:(lambda _pid:1,lambda _pgid:[123]),build_environment=lambda _target:{},
            read_owned_rss=lambda *_args:(_ for _ in()).throw(OSError('read uncertainty')),cleanup_owned=lambda *_args:False)
        with patch.object(G,'load_helper',return_value=helper),patch.object(G.subprocess,'Popen',return_value=SimpleNamespace(pid=123)):
            with self.assertRaisesRegex(RuntimeError,'cleanup uncertain'):G.run('build')
        rows=G.read_lines(G.LEDGER);self.assertEqual(len(rows),2);self.assertIsNotNone(G.state(rows)['pending'])
        receipt=G.read(self.root/'build-1-stage-receipt.json');self.assertFalse(receipt['cleanup_verified']);self.assertEqual(receipt['charged_seconds'],15.)

    def test_complete_zero_call_witness_types_and_count(self):
        plan=self.root/'plan.json';plan.write_text(json.dumps(dict(worlds=[dict(id=i,source_code='a')for i in range(26)])))
        cases=[dict(world_id=i,card='a',publicSnapshotRoundtripExact=True,legalActionsRoundtripExact=True,applyCalls=0,actionsApplied=0,attachmentChronology=[],fixtureAttachmentWitnesses=[])for i in range(26)]
        raw=dict(schema='jepa-binding-transfer-fixture-validation/1',validationComplete=True,cases=cases,applyCalls=0,engineApplyInvocations=0,actionsApplied=0,nativeJournalCreated=False,neuralForwards=0,optimizerUpdates=0,collectionPlan=G.read(plan),collectionPlanSha256=G.pin(plan)['sha256'])
        G.validate_receipt(raw,plan)
        for key,value in(('cases',cases[:25]),('applyCalls',1),('engineApplyInvocations',False),('nativeJournalCreated',True),('validationComplete',False),('collectionPlanSha256','wrong')):
            with self.subTest(key=key),self.assertRaises(ValueError):G.validate_receipt(dict(raw,**{key:value}),plan)


if __name__=='__main__':unittest.main()
