"""Artificial lists and source contracts only; no numerical/model execution."""
import ast
import copy
from pathlib import Path
import unittest
import real_ir_transfer_fit as F


def tiny():
    y=[[[1.,2.],[0.,0.]],[[1.,3.],[0.,0.]],[[1.,-1.],[0.,0.]],[[1.,0.],[1.,0.]]]
    m=[[[1.,1.],[1.,0.]],[[1.,1.],[1.,0.]],[[1.,1.],[1.,0.]],[[1.,1.],[1.,0.]]]
    meta=[dict(operator='damage',intent_domain='unit',healthy_intent=False),
          dict(operator='damage',intent_domain='base',healthy_intent=False),
          dict(operator='heal',intent_domain='unit',healthy_intent=False),
          dict(operator='heal',intent_domain='base',healthy_intent=True)]
    return y,m,meta


class FitPrimitiveTest(unittest.TestCase):
    def test_exact_counter_panel_and_no_top_numerical_imports(self):
        self.assertEqual(F.CONFIG['neural_forwards'],3*3*(300+2))
        self.assertEqual(F.CONFIG['optimizer_updates'],2700)
        self.assertEqual(F.CONFIG['numerical_fits'],2)
        tree=ast.parse(Path(F.__file__).read_text())
        names=[a.name for n in tree.body if isinstance(n,ast.Import) for a in n.names]
        self.assertFalse(any(x in names for x in ('numpy','torch','real_ir_transfer_model')))
        worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='worker')
        self.assertTrue(any(isinstance(n,ast.Import)and any(a.name=='torch'for a in n.names)for n in ast.walk(worker)))

    def test_common_class_weights_ignore_poisoned_held_labels(self):
        y,m,_=tiny();original=F.class_statistics(y,m,[0,1,2])
        self.assertEqual(original['class_counts'],[3,3])
        y[3]=[['private-label-poison',None]]
        self.assertEqual(F.class_statistics(y,m,[0,1,2]),original)

    def test_held_forward_is_after_complete_training_barrier(self):
        text=Path(F.__file__).read_text()
        barrier=text.index("require(counts['optimizer_updates']==2700")
        evaluation=text.index('with torch.no_grad(): output=tracked_forward')
        self.assertLess(barrier,evaluation)
        tree=ast.parse(text)
        calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='tracked_forward']
        self.assertEqual(len(calls),2)  # One fixed training site, one deferred evaluation site.

    def test_json_normalization_handles_saved_scalar_like_values(self):
        class Scalar:
            def item(self):return 7
        self.assertEqual(F.native({'root':Scalar(),'slices':(Scalar(),None)}),{'root':7,'slices':[7,None]})

    def test_three_train_strata_and_no_held_composition_weight(self):
        y,m,meta=tiny();s=F.stratum_statistics(y,m,[0,1,2],meta)
        self.assertEqual(s['counts'],{'damage|unit':1,'damage|base':1,'heal|unit':1})
        self.assertEqual(s['absent_train_strata'],['heal|base'])
        self.assertNotIn('heal|base',s['weights'])
        meta[3]['operator']='poison';y[3]='poison';m[3]='poison'
        self.assertEqual(F.stratum_statistics(y,m,[0,1,2],meta),s)
        with self.assertRaisesRegex(ValueError,'three'):F.stratum_statistics(y,m,[0,1],meta)

    def test_raw_physical_endpoint_and_all_positive_eligibility(self):
        y,m,meta=tiny();p=copy.deepcopy(y);p[3][0]=[.9,.05]
        p[3][1]=[.9,999.]  # Unknown/unintended endpoint must not contribute.
        out=F.evaluate(p,y,m,meta,[3])
        self.assertAlmostEqual(out['endpoint_mae']['pooled'],.05)
        self.assertIsNone(out['eligibility']['balanced_accuracy'])
        self.assertIsNone(out['eligibility']['specificity'])
        self.assertEqual(out['eligibility']['positive_recall'],1.)
        self.assertEqual(out['healthy_max_abs'],.05)

    def test_sign_accuracy_uses_known_nonzero_native_effects(self):
        y,m,meta=tiny();p=copy.deepcopy(y);p[0][0][1]=-2.;p[2][0][1]=-.5
        out=F.evaluate(p,y,m,meta,[0,1,2])
        self.assertEqual(out['nonzero_support'],3)
        self.assertAlmostEqual(out['nonzero_sign_accuracy'],2/3)
        self.assertEqual(out['endpoint_mae']['base'],0.)

    def test_no_post_training_semantic_claim_in_decision(self):
        y,m,meta=tiny();perfect=F.evaluate(y,y,m,meta,[0,1,2,3]);results={}
        for seed in F.SEEDS:
            for arm in F.ARMS:
                metrics=copy.deepcopy(perfect)
                if arm=='new-printed-only':metrics['endpoint_mae']={k:1. for k in metrics['endpoint_mae']}
                results[f's{seed}:{arm}']=dict(evaluations={'300':dict(held=metrics)})
        result=F.decisions(results)
        self.assertTrue(result['usability_passed']);self.assertTrue(result['architecture_diagnostic_passed'])
        self.assertFalse(result['semantic_validated'])
        self.assertTrue(all(not r['eligibility_discrimination_qualified']for r in result['per_seed'].values()))
        results['s29:new-full']['evaluations']['300']['held']['healthy_max_abs']=.11
        self.assertFalse(F.decisions(results)['usability_passed'])

    def test_zero_printed_error_cannot_pass_relative_improvement(self):
        y,m,meta=tiny();metrics=F.evaluate(y,y,m,meta,[0,1,2,3])
        results={f's{s}:{a}':dict(evaluations={'300':dict(held=copy.deepcopy(metrics))})for s in F.SEEDS for a in F.ARMS}
        d=F.decisions(results);self.assertIsNone(d['relative_improvement_vs_printed']);self.assertFalse(d['architecture_diagnostic_passed'])


if __name__=='__main__':unittest.main()
