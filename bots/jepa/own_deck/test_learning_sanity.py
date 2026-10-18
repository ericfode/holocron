"""Pure data, gate, provenance and ledger tests; no Torch/model/optimizer."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import learning_sanity as S
import numpy as np

class SanityTests(unittest.TestCase):
    def data(self):
        arrays=dict(targets=np.arange(21*8*7,dtype=np.float32).reshape(21,8,7),target_mask=np.ones((21,8,7),np.float32),source_targets=np.zeros((21,9),np.float32),source_mask=np.ones((21,9),np.float32),selected_candidate_indices=np.arange(21,dtype=np.int64)%8)
        arrays['target_mask'][:,:,2:]=0
        for i in range(14):arrays['target_mask'][i,arrays['selected_candidate_indices'][i],2:]=1
        plan=dict(train_indices=list(range(21)),shuffle_roots=list(range(14)),effect_columns=list(range(2,7)),scalers=dict(targets=[dict(name='head'+str(i),scale=1.)for i in range(7)]));return arrays,plan
    def test_fixed_and_fresh_are_reproducible_derangements(self):
        fixed,fresh=S.derangements();f2,r2=S.derangements();self.assertTrue(np.array_equal(fixed,f2));self.assertTrue(np.array_equal(fresh,r2));self.assertEqual(fresh.shape,(300,14))
        for mapping in [fixed,*fresh]:self.assertEqual(sorted(mapping.tolist()),list(range(14)));self.assertTrue(np.all(mapping!=np.arange(14)))
    def test_joint_packets_only_move_to_recipient_anchor(self):
        arrays,plan=self.data();before={k:v.copy()for k,v in arrays.items()};fixed,_=S.derangements();shuffled=S.shuffle_labels(arrays,plan,fixed);roots,packets=S.effect_packets(arrays,plan)
        for i,r in enumerate(roots):self.assertTrue(np.array_equal(shuffled['targets'][r,arrays['selected_candidate_indices'][r],2:],packets[fixed[i]]))
        changed=np.zeros_like(arrays['targets'],dtype=bool)
        for r in roots:changed[r,arrays['selected_candidate_indices'][r],2:]=True
        self.assertTrue(np.array_equal(shuffled['targets'][~changed],arrays['targets'][~changed]))
        for k in arrays:self.assertTrue(np.array_equal(arrays[k],before[k]));self.assertTrue(k=='targets'or np.array_equal(shuffled[k],arrays[k]))
    def test_unknown_or_held_root_never_enters_shuffle(self):
        arrays,plan=self.data();arrays['target_mask'][0,0,3]=0
        with self.assertRaises(ValueError):S.effect_packets(arrays,plan)
        arrays,plan=self.data();arrays['target_mask'][14,arrays['selected_candidate_indices'][14],2]=1
        with self.assertRaises(ValueError):S.effect_packets(arrays,plan)
        arrays,plan=self.data();plan['train_indices']=list(range(1,21))
        with self.assertRaises(ValueError):S.effect_packets(arrays,plan)
    def test_invalid_mapping_rejects_without_mutating_labels(self):
        arrays,plan=self.data()
        for mapping in (np.arange(14),np.zeros(14,np.int64),np.arange(13),np.arange(14,dtype=np.int32)):
            with self.assertRaises(ValueError):S.shuffle_labels(arrays,plan,mapping)
    def test_duplicate_packets_report_real_fraction(self):
        packets=np.zeros((14,5),np.float32);fixed,_=S.derangements();report=S.shuffle_change_report(packets,fixed);self.assertEqual(report['coordinate_fraction'],0);self.assertEqual(report['vector_fraction'],0)
        packets[:,0]=np.arange(14);report=S.shuffle_change_report(packets,fixed);self.assertEqual(report['vector_fraction'],1.);self.assertEqual(report['coordinate_fraction'],.2)
    def test_gate_per_head_and_zero_initial_ratio(self):
        initial={str(i):dict(normalized_mae=1.)for i in range(5)};final={str(i):dict(normalized_mae=.04,zero_sign_accuracy=1.)for i in range(5)};self.assertTrue(S.overfit_gate(initial,final)['passed'])
        final['4']['zero_sign_accuracy']=13/14;self.assertFalse(S.overfit_gate(initial,final)['passed']);final['4']['zero_sign_accuracy']=1.;final['4']['normalized_mae']=.051;self.assertFalse(S.overfit_gate(initial,final)['passed'])
        final['4']['normalized_mae']=.04;initial['4']['normalized_mae']=0.;gate=S.overfit_gate(initial,final);self.assertTrue(gate['passed']);self.assertIsNone(gate['per_head']['4']['final_initial_ratio'])
    def test_native_deadband_is_per_head_14_root_accuracy(self):
        arrays,plan=self.data();arrays['targets'][:]=0;prediction=np.zeros_like(arrays['targets']);prediction[0,0,2]=.26;m=S.sanity_metrics(prediction,arrays,plan);self.assertEqual(m['head2']['zero_sign_accuracy'],13/14);self.assertEqual(m['head3']['zero_sign_accuracy'],1.)
        prediction[0,0,2]=.25;self.assertEqual(S.sanity_metrics(prediction,arrays,plan)['head2']['zero_sign_accuracy'],1.)
    def test_new_ledger_parent_link_single_attempt_and_failed_debit(self):
        with tempfile.TemporaryDirectory()as d:
            plan=Path(d)/'plan.json';plan.write_text('{}');path=Path(d)/'ledger.jsonl'
            with patch.object(S,'DEFAULT',Path(d)),path.open('w+')as f:
                rows=[];S.append_ledger(f,rows,plan,'initialized',dict(plan=S.pin(plan),config=S.CONFIG,ledger_path=str((Path(d)/'campaign-ledger.jsonl').resolve()),parent_final_record=S.PARENT_LAST));S.append_ledger(f,rows,plan,'attempt-start',dict(reservation=dict(seconds=30.,optimizer_updates=900,training_forwards=900,evaluation_forwards=6,export_forwards=0,native_applies=0)))
                self.assertTrue(S.ledger_state(rows,plan)['pending'])
                S.append_ledger(f,rows,plan,'attempt-finish',dict(status='failed',charged_optimizer_updates=900,charged_training_forwards=900,charged_evaluation_forwards=6,active_seconds=.1,counts={}))
                self.assertTrue(S.ledger_state(rows,plan)['finished'])
                with self.assertRaises(ValueError):S.append_ledger(f,rows,plan,'attempt-start',{})
                damaged=copy.deepcopy(rows);damaged[1]['data']['reservation']['optimizer_updates']=0
                with self.assertRaises(ValueError):S.ledger_state(damaged,plan)
    def test_canonical_path_and_copied_ledger_reject(self):
        with tempfile.TemporaryDirectory()as d,patch.object(S,'DEFAULT',Path(d)):
            canonical=Path(d)/'campaign-ledger.jsonl';self.assertEqual(S.canonical_ledger(canonical),canonical.resolve())
            for copied in(Path(d)/'copy.jsonl',Path(d)/'other/campaign-ledger.jsonl'):
                with self.assertRaises(ValueError):S.canonical_ledger(copied)
                with self.assertRaises(ValueError):S.initialize(copied,Path(d)/'nonexistent-plan.json')
    def test_real_prior_parent_initialization_and_support_pins(self):
        S.validate_parent();p=S.read(S.PRIOR/'learner-plan.json');self.assertEqual(p['parameters']['allocated'],11856)
        with np.load(S.PRIOR/'fit-1/initial-checkpoint.npz',allow_pickle=False)as z:self.assertEqual(sum(z[k].size for k in z.files),11856)
        with np.load(p['dataset'],allow_pickle=False)as z:a={k:z[k]for k in z.files}
        train=S.E.partition(a,p['split'])['train'];cols=list(range(2,7));roots=[int(i)for i in train if a['target_mask'][i,a['selected_candidate_indices'][i],cols].all()];self.assertEqual(len(roots),14);self.assertEqual(len(train),21)
    def test_import_and_data_helpers_have_no_neural_import(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import learning_sanity as s;s.derangements();assert 'torch' not in sys.modules"
        subprocess.run([sys.executable,'-B','-c',code,str(S.HERE)],check=True,capture_output=True,text=True)
if __name__=='__main__':unittest.main()
