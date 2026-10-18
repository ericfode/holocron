from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

import public_input_binding_analysis as R


class AnalysisTests(unittest.TestCase):
    def fixture(self,root):
        script=root/'pure.py';script.write_text('raise AssertionError("must never execute during preview")\n')
        argv=[str(script),'--input',str(root/'future-native.json'),'--out',str(root/'predictions.json')]
        outputs=[str(root/'predictions.json')]
        value=dict(stage='analysis-controls',argv=argv,pins=[R.A.pin(script)],outputs=outputs)
        p=root/'descriptor.json';p.write_text(json.dumps(value))
        current=dict(completed_stages=['native-collect'],seen_stages=[],config=dict(
            pins=[R.A.pin(script),R.A.pin(Path(R.__file__)),R.A.pin(R.GUARD)],
            analysis_commands={'analysis-controls':dict(argv=argv,outputs=outputs)}))
        return p,value,current

    def test_preview_runs_no_script_or_accounting_mutation(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name).resolve();p,_,current=self.fixture(root)
            @contextmanager
            def fake_lease():yield None,[],current
            with patch.object(R.A,'CAMPAIGN',root),patch.object(R.A,'lease',fake_lease),patch.object(R.A,'start')as start:
                self.assertEqual(R.run(p)['status'],'preview-only');start.assert_not_called()
            self.assertFalse((root/'predictions.json').exists())

    def test_postlabel_argv_or_output_changes_and_retry_are_rejected(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name).resolve();p,value,current=self.fixture(root)
            for field in('argv','outputs'):
                changed=copy.deepcopy(value);changed[field][-1]=str(root/'adapted.json');p.write_text(json.dumps(changed))
                with patch.object(R.A,'CAMPAIGN',root),self.assertRaises(ValueError):R.descriptor(p,current)
            p.write_text(json.dumps(value));current['seen_stages']=['analysis-controls']
            with patch.object(R.A,'CAMPAIGN',root),self.assertRaises(ValueError):R.descriptor(p,current)

    def test_dependencies_unknown_stage_and_changed_source_fail(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name).resolve();p,value,current=self.fixture(root);current['completed_stages']=[]
            with patch.object(R.A,'CAMPAIGN',root),self.assertRaises(ValueError):R.descriptor(p,current)
            current['completed_stages']=['native-collect'];Path(value['argv'][0]).write_text('changed')
            with patch.object(R.A,'CAMPAIGN',root),self.assertRaises(ValueError):R.descriptor(p,current)

    def test_audit_blocks_neural_fit_spawn_network_and_foreign_signals(self):
        for event,args in [('import',('torch',)),('import',('sklearn.linear_model',)),('subprocess.Popen',()),('os.fork',()),('socket.connect',()),('os.killpg',(123,15)),('os.kill',(123,15))]:
            with self.subTest(event=event),self.assertRaises(RuntimeError):R.audit_event(event,args)
        R.audit_event('import',('numpy',));R.audit_event('os.kill',(os.getpid(),signal.SIGALRM))


if __name__=='__main__':unittest.main()
