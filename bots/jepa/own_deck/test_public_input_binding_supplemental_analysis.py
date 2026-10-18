from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

import public_input_binding_supplemental_analysis as S


class SupplementalTests(unittest.TestCase):
    def fixture(self, root):
        verifier=root/'new-verifier.py';verifier.write_text('raise AssertionError("preview must not execute")\n')
        parent=root/'ended-ledger.jsonl';parent.write_text('immutable parent bytes\n')
        inputs=[]
        for name in ('plan.json','native.json','native.jsonl','predictions.json','predictor.py'):
            p=root/name;p.write_text('{}\n');inputs.append(p)
        output=root/'independent-verification-supplemental.json';journal=root/'supplemental-verification-ledger.jsonl'
        argv=[str(root/'old-verifier.py')]
        for option,p in zip(('--plan','--receipt','--journal','--predictions','--predictor-source'),inputs):argv.extend((option,str(p)))
        argv.extend(('--out',str(root/'old-output.json')))
        current=dict(config=dict(analysis_commands={'analysis-verification':dict(argv=argv,outputs=[argv[-1]])}))
        value=dict(schema=S.SCHEMA,seconds=12.,argv=[str(verifier),*argv[1:-1],str(output)],outputs=[str(output)],
            pins=[S.A.pin(p) for p in [Path(S.__file__),Path(S.A.__file__),S.GUARD,verifier,parent,*inputs]])
        descriptor=root/'descriptor.json';descriptor.write_text(json.dumps(value))
        return descriptor,value,current,verifier,parent,output,journal

    @contextmanager
    def patched(self, fixture):
        _,_,_,verifier,parent,output,journal=fixture
        with patch.object(S,'VERIFIER',verifier),patch.object(S,'VERIFIER_SHA',S.A.pin(verifier)['sha256']),patch.object(S,'PARENT',S.A.pin(parent)),patch.object(S.A,'LEDGER',parent),patch.object(S,'OUTPUT',output),patch.object(S,'JOURNAL',journal):yield

    def test_exact_new_checker_and_output_only(self):
        with tempfile.TemporaryDirectory() as name:
            f=self.fixture(Path(name).resolve())
            with self.patched(f):self.assertEqual(S.descriptor(f[0],f[2])['argv'],f[1]['argv'])
            for field in ('argv','outputs'):
                value=copy.deepcopy(f[1]);value[field][-1]=str(Path(name)/'adapted.json');f[0].write_text(json.dumps(value))
                with self.patched(f),self.assertRaises(ValueError):S.descriptor(f[0],f[2])

    def test_changed_inputs_and_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            f=self.fixture(Path(name).resolve());f[3].write_text('changed source')
            with self.patched(f),self.assertRaises(ValueError):S.descriptor(f[0],f[2])

    def test_any_previous_attempt_or_output_blocks_retry(self):
        with tempfile.TemporaryDirectory() as name:
            f=self.fixture(Path(name).resolve())
            for p in (f[5],f[6]):
                p.write_text('historical bytes')
                with self.patched(f),self.assertRaises(FileExistsError):S.descriptor(f[0],f[2])
                self.assertEqual(p.read_text(),'historical bytes');p.unlink()

    def test_failure_is_charged_full_reservation_and_no_repeat_finish(self):
        with tempfile.TemporaryFile(mode='w+') as stream:
            rows=[];S.append(stream,rows,'intent',dict(parent=S.PARENT))
            row=S.finish(stream,rows,'failed',.1,error={'type':'CheckerFailure'})
            self.assertEqual(row['data']['charged_seconds'],12.)
            self.assertEqual(row['data']['observed_seconds'],.1)
            self.assertEqual(row['data']['native_applies'],0)
            self.assertEqual(S.A.chain(rows),row['record_sha256'])
            with self.assertRaises(ValueError):S.finish(stream,rows,'completed',.2)

    def test_observed_overrun_is_failed_without_resetting_time(self):
        with tempfile.TemporaryFile(mode='w+') as stream:
            rows=[];S.append(stream,rows,'intent',{})
            result=S.finish(stream,rows,'completed',12.2)['data']
            self.assertEqual(result['status'],'failed');self.assertEqual(result['charged_seconds'],12.2)

    def test_preview_has_no_script_execution_or_journal_write(self):
        with tempfile.TemporaryDirectory() as name:
            f=self.fixture(Path(name).resolve())
            @contextmanager
            def lease():yield None,[],f[2]
            with self.patched(f),patch.object(S.A,'lease',lease),patch.object(S,'parent_state',return_value=15.1543761659413576),patch.object(S.runpy,'run_path') as run:
                result=S.run(f[0]);run.assert_not_called()
            self.assertEqual(result['status'],'preview-only');self.assertLess(result['shared_analysis_max_after'],30.)
            self.assertFalse(f[5].exists());self.assertFalse(f[6].exists())

    def test_shared_original_budget_cannot_be_reset(self):
        current=dict(pending=None,completed_stages=['native-build','native-collect','analysis-controls'],
            seen_stages=['native-build','native-collect','analysis-controls','analysis-verification'],
            config=dict(pins=[]),phase_charged_seconds=dict(analysis=18.01))
        records=[dict(event='attempt-finish',data=dict(status='failed'))]
        with patch.object(S.A,'verify_pins'),patch.object(S.A,'chain',return_value=S.PARENT_CHAIN),patch.object(S.A,'verify_parents'),patch.object(S.A,'recovery_parent'),self.assertRaises(ValueError):
            S.parent_state(records,current)

    def test_neural_fit_process_network_and_foreign_signals_forbidden(self):
        for event,args in [('import',('torch',)),('import',('sklearn',)),('subprocess.Popen',()),('os.fork',()),('socket.connect',()),('os.killpg',(123,15)),('os.kill',(123,15))]:
            with self.subTest(event=event),self.assertRaises(RuntimeError):S.audit_event(event,args)
        S.audit_event('import',('numpy',));S.audit_event('os.kill',(os.getpid(),signal.SIGALRM))


if __name__=='__main__':unittest.main()
