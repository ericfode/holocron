"""Standard-library primitive tests; never constructs a model or numerical bank."""
import ast
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest
import compositional_typed_fit as F


def good_evaluation():
    elig=dict(eligibility=dict(balanced_accuracy=1.))
    axes={f'{name}={v}':copy.deepcopy(elig)for name in F.BITS for v in(0,1)}
    damage={}
    for op in(0,1):
        for amount in(0,1):
            damage[f'op_heal={op},amount_is_3={amount}']=dict(damage=dict(mae=0.,sign_accuracy=1.,classes=dict(zero=dict(count=4 if op else 0,recall=1. if op else None))))
    return dict(held_axes=axes,held_op_amount=damage)


class Tests(unittest.TestCase):
    def test_schedule_exact_counts(self):
        self.assertEqual(len(F.SEEDS)*len(F.ARMS)*F.CONFIG['updates_per_arm'],3600)
        self.assertEqual(len(F.SEEDS)*len(F.ARMS)*2,24)
        self.assertEqual(F.CONFIG['neural_forwards'],3624);self.assertEqual(F.CONFIG['numerical_fits'],2)
        for key in('native_applies','paid_jobs','export_forwards'):self.assertEqual(F.CONFIG[key],0)

    def test_import_and_describe_no_scientific_imports(self):
        result=subprocess.run([sys.executable,'-c',"import compositional_typed_fit as f,sys; f.describe(); assert not({'numpy','torch','effect_identifiability_fit','compositional_typed_model'}&set(sys.modules))"],cwd=Path(F.__file__).parent,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_parity_full_factorial_and_every_proper_subset(self):
        bits=[list(b)for b in itertools.product((0,1),repeat=5)];audit=F.parity_audit(bits)
        self.assertEqual(len(audit['train_programs']),16);self.assertEqual(len(audit['held_programs']),16);self.assertTrue(audit['proper_subsets_covered'])
        broken=copy.deepcopy(bits);broken[-1]=broken[0]
        with self.assertRaisesRegex(ValueError,'unique'):F.parity_audit(broken)

    def test_weight_statistics_train_only_and_committed_intended_only(self):
        fields=[[1,0,1,0,2,1,0,1],[1,0,1,0,2,0,1,3]]
        targets=[[[1.,1.],[0.,999.]],[[1.,3.],[0.,999.]],[[1.,0.],[0.,999.]],[[1.,-3.],[0.,999.]],[[0.,999.],[0.,999.]]]
        mask=[[[1,1],[1,0]]for _ in range(5)];mask[4][0][1]=0
        selected=[0]*5;q=[0,0,1,1,0];train=[0,1,2,3]
        a=F.loss_weights(targets,mask,selected,q,fields,train);self.assertEqual(a['eligibility_class_counts'],[4,4]);self.assertEqual(a['eligibility_class_weights'],[1.,1.])
        self.assertAlmostEqual(sum(a['damage_weights']),4.);self.assertEqual(a['damage_weights'][4],0.)
        poisoned=copy.deepcopy(targets);poisoned[4]=[[1.,-100000.],[1.,-999.]]
        self.assertEqual(a,F.loss_weights(poisoned,mask,selected,q,fields,train))
        self.assertEqual({tuple(v['key'])for v in a['strata']},{('damage',1,'nonzero'),('heal',3,'zero'),('heal',3,'nonzero')})

    def test_metrics_intended_only_known_masks_and_exact_truth_sign(self):
        targets=[[[1,0],[0,100]],[[1,-3],[0,100]],[[0,1],[1,100]]];mask=[[[1,1],[1,0]],[[1,1],[1,0]],[[1,0],[1,0]]]
        result=F.metric_slice([[.8,.2],[.9,.1],[.1,.9]],[[.25,-100],[-2.8,-100],[999,-100]],targets,mask,[0,0,0],[0,1,2])
        self.assertEqual(result['eligibility']['balanced_accuracy'],1.);self.assertEqual(result['damage']['known'],2)
        self.assertAlmostEqual(result['damage']['mae'],.225);self.assertEqual(result['damage']['sign_accuracy'],1.)
        self.assertEqual(result['damage']['classes']['zero']['recall'],1.);self.assertIsNone(result['damage']['classes']['positive']['recall'])

    def test_no_zero_class_is_na_only_for_damage_op(self):
        good=good_evaluation();self.assertTrue(F.success_gate(good,good)['passed'])
        missing=copy.deepcopy(good);missing['held_op_amount']['op_heal=1,amount_is_3=0']['damage']['classes']['zero']=dict(count=0,recall=None)
        self.assertFalse(F.success_gate(missing,good)['passed'])

    def test_new_identity_gap_required_old_gap_descriptive(self):
        noid=good_evaluation();withid=good_evaluation();noid['held_axes']['arena_space=0']['eligibility']['balanced_accuracy']=.95
        self.assertFalse(F.success_gate(noid,withid,True)['passed']);self.assertTrue(F.success_gate(noid,withid,False)['passed'])
        self.assertFalse(F.success_gate(noid,withid,False)['identity_passed'])

    def test_required_missing_class_fails(self):
        a=good_evaluation();a['held_axes']['owner_opponent=1']['eligibility']['balanced_accuracy']=None
        self.assertFalse(F.success_gate(a,good_evaluation())['passed'])

    def test_source_ast_budget_intents_and_late_metrics(self):
        source=Path(F.__file__).read_text();tree=ast.parse(source)
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom))and any(a.name in('numpy','torch')for a in n.names)for n in tree.body))
        for counter in('neural_forwards','backwards','optimizer_updates','numerical_fits'):self.assertIn("run.intent('"+counter+"')",source)
        self.assertEqual(source.count("run.intent('numerical_fits')"),2)
        self.assertLess(source.index("require(counts=={k:CONFIG[k]for k in counts}"),source.index('results={};gates={}'))
        self.assertIn("neutral[...,7]=0.",source);self.assertIn("branch(elig)[...,0]",source);self.assertIn("branch(full)[...,2]",source)
        self.assertNotIn('optimizer.step()',source[:source.index('def worker(')])


if __name__=='__main__':unittest.main()
