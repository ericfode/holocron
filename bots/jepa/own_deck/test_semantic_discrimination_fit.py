"""Synthetic-only learner contract checks; never constructs a Torch model."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import semantic_discrimination_fit as F


def synthetic_fit():
    result={'results':{}}
    for seed in F.SEEDS:
        for arm in F.ARMS:
            error=.1 if arm=='learned-full'else 1.
            value=dict(primary={g:dict(mae=error)for g in('ASH_081','IBH_104')},paired_contrasts=dict(pairs=[dict(known=True,direction_correct=True)for _ in range(4)],eligible_action_rank_pairs=0,action_outcome_rank_accuracy=None))
            swapped=copy.deepcopy(value)
            for g in swapped['primary']:swapped['primary'][g]['mae']=.3 if arm=='learned-full'else error
            result['results'][f's{seed}:{arm}']=dict(evaluations={'200':value},ability_swapped_evaluation=swapped,ability_swap_prediction_identical=arm in('printed-only','ID-only','public-only'))
    baseline=dict(evaluations={a:dict(primary={g:dict(mae=1.)for g in('ASH_081','IBH_104')})for a in('zero','train_mean','public_ridge')})
    return result,baseline


class StaticContract(unittest.TestCase):
    def test_exact_exposure_and_ridge(self):
        self.assertEqual(5*3*200,F.CONFIG['optimizer_updates']);self.assertEqual(3000+30+15,F.CONFIG['neural_forwards'])
        self.assertEqual((75,0,16),(F.BASE_CONFIG['feature_columns'],F.BASE_CONFIG['train_id_columns'],F.BASE_CONFIG['head_fit_attempts']))
        self.assertEqual(45.,F.SECONDS['fit'])

    def test_module_import_does_not_import_torch_or_numpy(self):
        source=ast.parse(Path(F.__file__).read_text())
        imports=[n for n in source.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        names=[a.name for n in imports for a in n.names]
        self.assertFalse(set(names)&{'torch','numpy'})

    def test_static_forward_schedule_and_common_clone(self):
        source=Path(F.__file__).read_text();tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='fit_worker');text=ast.get_source_segment(source,fn)
        self.assertIn('range(1,201)',text);self.assertIn('model.load_state_dict(initial,strict=True)',text)
        self.assertIn("predict(model,banks[flavor],representation,arm,seed,0,'correct')",text)
        self.assertIn("predict(model,banks[flavor],representation,arm,seed,200,'correct')",text)
        self.assertIn("predict(model,banks[swap_flavor],representation,arm,seed,200,'ability-swapped')",text)
        self.assertLess(text.index("event='optimizer-intent'"),text.index('optimizer.step()'))
        self.assertIn('arrays[k][batch].copy()',text)

    def test_printed_and_public_control_routing_without_model(self):
        class Dummy:
            def card_bank(self,bank):return bank
        model=Dummy();calls=[];M=types.SimpleNamespace(configure_arm=lambda m,a:calls.append(a))
        self.assertEqual('rich-untrained-typed',F.configure_model(model,'public-only',M));self.assertEqual(0.,model.card_bank(12.))
        self.assertEqual(['rich-untrained-typed'],calls)
        with self.assertRaises(ValueError):F.configure_model(Dummy(),'unknown',M)

    def test_primary_gate_does_not_require_rank_and_zero_is_control(self):
        fit,base=synthetic_fit();gate=F.gate_results(fit,base)
        self.assertTrue(gate['primary_behavior_gate_passed']);self.assertFalse(gate['actual_rank_diagnostic_passed']);self.assertTrue(gate['ability_sensitivity_gate_passed']);self.assertFalse(gate['semantic_validated'])
        base['evaluations']['zero']['primary']['ASH_081']['mae']=.01
        self.assertFalse(F.gate_results(fit,base)['primary_behavior_gate_passed'])

    def test_every_group_seed_and_pooled_reduction_required(self):
        fit,base=synthetic_fit();fit['results']['s29:learned-full']['evaluations']['200']['primary']['IBH_104']['mae']=1.01
        self.assertFalse(F.gate_results(fit,base)['primary_behavior_gate_passed'])
        fit,base=synthetic_fit()
        for seed in F.SEEDS:fit['results'][f's{seed}:learned-full']['evaluations']['200']['primary']['ASH_081']['mae']=.95
        self.assertFalse(F.gate_results(fit,base)['primary_behavior_gate_passed'])

    def test_ability_sensitivity_and_invariants_separate(self):
        fit,base=synthetic_fit();fit['results']['s43:ID-only']['ability_swap_prediction_identical']=False
        gate=F.gate_results(fit,base);self.assertTrue(gate['primary_behavior_gate_passed']);self.assertFalse(gate['ability_sensitivity_gate_passed'])
        fit['results']['s17:learned-full']['evaluations']['200']['paired_contrasts']['pairs'][0]['direction_correct']=False
        self.assertFalse(F.gate_results(fit,base)['primary_behavior_gate_passed'])
        fit,base=synthetic_fit()
        for seed in F.SEEDS:fit['results'][f's{seed}:learned-full']['evaluations']['200']['primary']['ASH_081']['mae']=0.
        gate=F.gate_results(fit,base);self.assertFalse(gate['ability_sensitivity_gate_passed'])
        pooled=[v for v in gate['ability_sensitivity']if v['group']=='ASH_081'and v['seed']=='pooled'][0];self.assertIsNone(pooled['worsening'])

    def test_serializer_rejects_before_creating_file(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'new.json'
            with self.assertRaises(TypeError):F.write_new(p,dict(unknown=object()))
            self.assertFalse(p.exists())
            with self.assertRaises(ValueError):F.write_new(p,dict(nonfinite=float('nan')))
            self.assertFalse(p.exists());F.write_new(p,dict(ok=[1,True,None]));self.assertEqual({'ok':[1,True,None]},F.read(p))
            with self.assertRaises(FileExistsError):F.write_new(p,{})

    def test_stage_reservation_before_validation_and_success_counter_only(self):
        tree=ast.parse(Path(F.__file__).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run_stage');text=ast.unparse(fn)
        self.assertLess(text.index('C.start('),text.index("actual ="));self.assertLess(text.index('C.start('),text.index('args.out.exists()'))
        self.assertIn("stage == 'metadata'",text);self.assertIn('args.native_plan.resolve()',text)
        self.assertIn("status == 'completed' and progress",text);self.assertIn('counter_proof=counter',text)
        self.assertIn("stage in finished['completed_stages']",text)


@unittest.skipUnless(importlib.util.find_spec('numpy'),'NumPy optional synthetic checks')
class NumericalContract(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.np=np

    def test_nested_native_scalar_json_regression(self):
        np=self.np
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'roots.json';F.write_new(p,dict(families=dict(example=dict(roots=[np.int64(3),np.int64(9)],mae=np.float32(.25),flag=np.bool_(True)))),np)
            self.assertEqual({'families':{'example':{'roots':[3,9],'mae':.25,'flag':True}}},F.read(p))
            with self.assertRaises(TypeError):F.json_native(np.asarray([1]),np)

    def test_root_balanced_primary_only_two_anchors(self):
        np=self.np;n=33;order=['source','helper','other','anchor_a','anchor_b','x','own_base','opponent_base']
        names=['target_allowed','target_removed','target_damage_delta','exhaust','shield','power','hp'];cards=np.asarray(['TRAIN']*25+['ASH_081']*4+['IBH_104']*4)
        arrays=dict(source_cards=cards,targets=np.zeros((n,8,7),np.float32),target_mask=np.ones((n,8,7),np.float32),primary_target_mask=np.zeros((n,8,7),np.float32))
        arrays['primary_target_mask'][25:29,3:5,2]=1;arrays['primary_target_mask'][29:33,3:5,:2]=1
        branch=np.ones((n,8,7),np.float32);branch[:,0]=9999
        split=dict(root_partitions=dict(train=list(range(13)),state_held=list(range(13,25)),family_held=[25,26,29,30],joint=[27,28,31,32]))
        values=F.primary_scores(branch,arrays,dict(target_names=names,candidate_order=order),dict(split=split))
        self.assertEqual(1.,values['ASH_081']['mae']);self.assertEqual(1.,values['IBH_104']['mae']);self.assertEqual(4,values['ASH_081']['heads']['target_damage_delta']['known_roots'])

    def test_public_ridge_has_no_id_and_train_mean_ignores_held(self):
        np=self.np;arrays=dict(selected_candidate_indices=np.asarray([0,1]),source_targets=np.asarray([[1.,2.],[99.,99.]]),source_mask=np.ones((2,2)),targets=np.zeros((2,8,1)),target_mask=np.ones((2,8,1)))
        x=np.ones((2,32),np.float32);c=np.ones((2,8,43),np.float32)
        with mock.patch.object(F,'input_arrays',return_value=(x,c)):
            sx,bx=F.baseline_features(arrays,{},dict(scalers={}));self.assertEqual((2,75),sx.shape);self.assertEqual((2,8,75),bx.shape)
        means=F.constants(arrays,np.asarray([0]))['train_mean'][0];self.assertEqual([[1.,2.],[1.,2.]],means.tolist())

    def test_observed_rank_requires_both_committed_and_nontie(self):
        np=self.np;order=['source','helper','other','anchor_a','anchor_b','x','own_base','opponent_base'];names=['target_allowed','target_removed','target_damage_delta','exhaust','shield','power','hp']
        arrays=dict(targets=np.zeros((2,8,7),np.float32),target_mask=np.ones((2,8,7),np.float32),chosen_only_target_mask=np.zeros((2,8,7),np.float32),selected_candidate_indices=np.asarray([3,4]))
        arrays['targets'][0,3,2]=-3;arrays['targets'][1,4,2]=-1
        plan=dict(primary_spec=dict(rank_pairs=[dict(id='fixed',left_root=0,right_root=1,anchors=['anchor_a','anchor_b'],head='target_damage_delta',utility_sign=-1.)]))
        manifest=dict(target_names=names,candidate_order=order)
        self.assertEqual(0,F.paired_scores(arrays['targets'],arrays,manifest,plan)['eligible_action_rank_pairs'])
        arrays['chosen_only_target_mask'][0,3,2]=arrays['chosen_only_target_mask'][1,4,2]=1
        value=F.paired_scores(arrays['targets'],arrays,manifest,plan);self.assertEqual(1.,value['action_outcome_rank_accuracy'])


if __name__=='__main__':unittest.main()
