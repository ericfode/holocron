import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import binding_transfer_fit as F


def synthetic():
    a=dict(source_cards=np.asarray(['a']*6+['b']*4+['c']*4+['d']*2+['e']*2+['f']*4+['g']*4),state_families=np.arange(26,dtype=np.int64),
        context_features=np.zeros((26,18),np.float32),candidate_features=np.zeros((26,8,34),np.float32),
        source_targets=np.zeros((26,9),np.float32),source_mask=np.ones((26,9),np.float32),targets=np.zeros((26,8,7),np.float32),target_mask=np.zeros((26,8,7),np.float32),selected_candidate_indices=np.zeros(26,np.int64))
    m=dict(candidate_order=list('abcdefgh'),target_names=['target_allowed','target_removed','target_damage_delta','target_exhausted_delta','target_shield_delta','target_power_delta','target_hp_delta'],
        source_head_names=['s'+str(i)for i in range(9)],source_binary_heads=[],binary_heads=['target_allowed','target_removed'],family_ids=['family']*26,template_ids=['one']*4+['two']*22,
        public_binding_contract=dict(task='actual-intent-endpoints'),public_before_records=[dict(declared_intent=dict(requires_target=True))for _ in range(26)])
    p=dict(codes=list('abcdefg'),train_codes=list('abcde'),split=dict(root_partitions=dict(train=[0,1,2,3,6,8,10,12,14,15,16,17],family_held=[18,20,22,24],state_held=[4,5,7,9,11,13],joint=[19,21,23,25])),primary_mechanics=['damage','stats'])
    return a,m,p


class PreparationTests(unittest.TestCase):
    def test_postreservation_preflight_failure_finishes_without_neural_import(self):
        import os
        class A:
            calls=[]
            @staticmethod
            @contextmanager
            def lease():yield None,[],dict(config=dict(pins=[]))
            @staticmethod
            def start(*_):raise ValueError('postreservation-pin-failure')
            @staticmethod
            def state(_):return dict(pending=dict(stage='fit',owner_pid=os.getpid()))
            @staticmethod
            def verify_output_protection(_):pass
            @staticmethod
            def finish(*args,**kwargs):A.calls.append((args,kwargs));return dict(completed_stages=[])
        with tempfile.TemporaryDirectory()as name:
            root=Path(name)
            with patch.object(F,'accounting',return_value=A),patch.object(F,'model_module',side_effect=AssertionError('model must not be opened')):
                with self.assertRaisesRegex(RuntimeError,'failed bounded fit'):F.execute(root/'unread-plan.json',root/'fit',root/'progress.jsonl')
            self.assertEqual(len(A.calls),1);self.assertEqual(A.calls[0][0][2],'failed');self.assertIsNone(A.calls[0][1]['counter_proof'])
            self.assertIsNone(A.calls[0][1]['observed']['neural_forwards']);self.assertTrue((root/'fit-stage-receipt.json').is_file());self.assertFalse((root/'fit').exists())

    def test_import_does_not_import_torch(self):
        code='import sys; import binding_transfer_fit; assert "torch" not in sys.modules'
        subprocess.run([sys.executable,'-B','-c',code],cwd=Path(F.__file__).parent,check=True,capture_output=True)

    def test_exact_fixed_exposure_and_arm_contracts(self):
        c=F.expected_exposure();self.assertEqual(c['optimizer_updates'],5400);self.assertEqual(c['neural_forwards'],5436);self.assertEqual(c['evaluation_forwards'],36)
        for arm in F.MAIN:self.assertEqual(F.arm_contract(arm),(arm,'rich-typed'))
        self.assertEqual(F.arm_contract('ID-only'),('C1R1','rich-id-only'))
        with self.assertRaises(ValueError):F.arm_contract('extra-search')

    def test_explicit_partitions_reject_overlap_or_cartesian_inference(self):
        a,m,p=synthetic();self.assertEqual([len(v)for v in F.cells(a,p['split']).values()],[12,4,6,4])
        bad=dict(root_partitions={k:list(v)for k,v in p['split']['root_partitions'].items()});bad['root_partitions']['train'][0]=23
        with self.assertRaises(ValueError):F.cells(a,bad)
        with self.assertRaises(ValueError):F.cells(a,dict(train_codes=['a']))

    def test_actual_task_masks_and_native_errors_fail_closed(self):
        a,m,p=synthetic();F.validate_data(a,m,p)
        with self.assertRaises(ValueError):F.validate_data(a,dict(m,errors=1),p)
        wrong=dict(m,public_binding_contract=dict(task='conditional-choose-candidate'))
        with self.assertRaises(ValueError):F.validate_data(a,wrong,p)
        a['target_mask'][0,0,0]=.5
        with self.assertRaises(ValueError):F.validate_data(a,m,p)

    def test_two_independent_zero_nonzero_templates_required(self):
        a,m,p=synthetic()
        for h in(2,5,6):a['target_mask'][:8,:2,h]=1;a['targets'][:8,0,h]=1
        self.assertTrue(F.observed_support(a,m,np.arange(8),p)['passed'])
        a['targets'][4:8,:,2]=0
        self.assertFalse(F.observed_support(a,m,np.arange(8),p)['passed'])
        a['targets'][:8,0,2]=-1
        self.assertFalse(F.observed_support(a,m,np.arange(8),p)['passed'])

    def test_passive_source_reference_is_not_a_chosen_anchor(self):
        a,m,p=synthetic();a['target_mask'][:]=1;m['public_before_records'][0]['declared_intent']['requires_target']=False
        mask=F.chosen_only_mask(a,m);self.assertFalse(mask[0].any());self.assertTrue(mask[1,0].all());self.assertFalse(mask[1,1:].any())

    def test_common_transforms_never_fit_held_statistics(self):
        a,m,p=synthetic();train=np.arange(8)
        def raw(values,*_args,**_kwargs):return np.pad(values['context_features'],((0,0),(0,14))),np.pad(values['candidate_features'],((0,0),(0,0),(0,9)))
        with patch.object(F,'projected_arrays',side_effect=raw):
            first=F.common_scalers(a,m,train);a['context_features'][8:]=999;a['targets'][8:]=999
            second=F.common_scalers(a,m,train)
        self.assertEqual(first,second);self.assertEqual(len(first['context_features']['center']),32);self.assertEqual(len(first['candidate_features']['center']),43)

    def test_label_hash_protects_dtype_shape_and_values(self):
        a=np.zeros((2,2),np.float32)
        self.assertNotEqual(F.sha_array(a),F.sha_array(a.astype(np.float64)))
        self.assertNotEqual(F.sha_array(a),F.sha_array(a.reshape(4)))
        b=a.copy();b[0,0]=1;self.assertNotEqual(F.sha_array(a),F.sha_array(b))

    def test_named_initial_state_hash_is_order_independent_and_complete(self):
        a=np.zeros((2,2),np.float32);b=np.ones((2,),np.float32)
        self.assertEqual(F.named_state_sha256({'a':a,'b':b}),F.named_state_sha256({'b':b,'a':a}))
        changed=b.copy();changed[0]=2
        self.assertNotEqual(F.named_state_sha256({'a':a,'b':b}),F.named_state_sha256({'a':a,'b':changed}))
        self.assertNotEqual(F.named_state_sha256({'a':a,'b':b}),F.named_state_sha256({'a':a}))

    def test_failed_incomplete_update_intent_never_uses_success_counter_parser(self):
        with tempfile.TemporaryDirectory()as name:
            progress=Path(name)/'progress.jsonl'
            F.E.append_journal(progress,dict(event='forward-intent',kind='train',global_forward=1))
            F.E.append_journal(progress,dict(event='optimizer-intent',global_update=1))
            prefix=F.E.journal_counts(progress)
            self.assertEqual(prefix['optimizer_updates'],0);self.assertEqual(prefix['training_forwards'],1)
            self.assertIsNone(F.success_counter_proof('failed',progress))
            self.assertEqual(F.success_counter_proof('completed',progress),F.pin(progress))

    def test_preexisting_output_never_receives_attempt_receipt(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);out=root/'old';out.mkdir();(out/'original').write_text('preserve')
            F.save_stage_receipt(root/'stage.json',out,dict(status='failed'),copy_into_out=False)
            self.assertEqual(sorted(p.name for p in out.iterdir()),['original'])

    def test_quantity_range_requires_frozen_train_and_held_values(self):
        a,m,p=synthetic();train=p['split']['root_partitions']['train'];held=p['split']['root_partitions']['family_held']+p['split']['root_partitions']['joint']
        for h,values in((5,[1,2]),(6,[1,3])):
            a['target_mask'][train,0,h]=1;a['targets'][train,0,h]=np.resize(values,len(train))
            a['target_mask'][held,0,h]=1;a['targets'][held,0,h]=2 if h==5 else np.resize([2,3],len(held))
        self.assertTrue(F.quantity_admission(a,m,p)['passed'])
        a['targets'][train,0,6]=1
        self.assertFalse(F.quantity_admission(a,m,p)['passed'])


if __name__=='__main__':unittest.main()
