import subprocess
import sys
from pathlib import Path
import unittest
import tempfile
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import binding_transfer_baselines as B


class BaselinePreparationTests(unittest.TestCase):
    def test_postreservation_failure_retains_unknown_fits_without_success_parser(self):
        import os
        class A:
            calls=[]
            @staticmethod
            @contextmanager
            def lease():yield None,[],dict(config=dict(pins=[]))
            @staticmethod
            def start(*_):raise ValueError('postreservation-input-failure')
            @staticmethod
            def state(_):return dict(pending=dict(stage='baselines',owner_pid=os.getpid()))
            @staticmethod
            def verify_output_protection(_):pass
            @staticmethod
            def finish(*args,**kwargs):A.calls.append((args,kwargs));return dict(completed_stages=[])
        with tempfile.TemporaryDirectory()as name:
            root=Path(name)
            with patch.object(B.F,'accounting',return_value=A):
                with self.assertRaisesRegex(RuntimeError,'failed bounded baseline'):B.run(root/'unread-plan.json',root/'baselines',root/'progress.jsonl')
            self.assertEqual(len(A.calls),1);self.assertEqual(A.calls[0][0][2],'failed');self.assertIsNone(A.calls[0][1]['counter_proof'])
            self.assertIsNone(A.calls[0][1]['observed']['numerical_fits']);self.assertFalse((root/'baselines').exists())

    def test_import_has_no_neural_or_fit_side_effect(self):
        code='import sys; import binding_transfer_baselines; assert "torch" not in sys.modules; assert "learning_sanity_data" not in sys.modules'
        subprocess.run([sys.executable,'-B','-c',code],cwd=Path(B.__file__).parent,check=True,capture_output=True)

    def test_fixed_four_design_sixteen_head_allocation(self):
        self.assertEqual(len(B.CONFIG['input_cells'])*16,B.CONFIG['head_fit_attempts']);self.assertEqual(B.CONFIG['ridge_lambda'],1.)
        self.assertEqual(B.CONFIG['neural_forwards'],0);self.assertEqual(B.CONFIG['seconds'],10.)

    def test_held_identity_unknown_and_source_intent_gather(self):
        arrays=dict(source_cards=np.asarray(['a','held']),selected_candidate_indices=np.asarray([1,0],np.int64));plan=dict(train_codes=list('abcde'),scalers={})
        x=np.zeros((2,32),np.float32);c=np.zeros((2,8,43),np.float32);c[0,1,0]=7
        with patch.object(B.F,'projected_arrays',return_value=(x,c)):
            source,branch=B.features(arrays,{},plan,'C1R1')
        self.assertEqual(source.shape,(2,80));self.assertEqual(branch.shape,(2,8,80));self.assertEqual(source[0,32],7)
        self.assertEqual(source[0,-5],1);self.assertFalse(source[1,-5:].any());self.assertFalse(branch[1,:,-5:].any())

    def test_constants_use_only_known_train_labels(self):
        a=dict(source_targets=np.asarray([[2.,99.],[888.,888.]],np.float32),source_mask=np.asarray([[1.,0.],[1.,1.]],np.float32),
            targets=np.asarray([[[3.],[5.]],[[888.],[888.]]],np.float32),target_mask=np.asarray([[[1.],[0.]],[[1.],[1.]]],np.float32))
        result=B.constants(a,np.asarray([0]));s,t=result['train_mean'];self.assertEqual(s.tolist(),[[2.,0.],[2.,0.]]);self.assertEqual(t.tolist(),[[[3.],[3.]],[[3.],[3.]]])
        self.assertFalse(result['zero'][0].any())


if __name__=='__main__':unittest.main()
