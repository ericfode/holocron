"""Pure list/AST contracts only; no numerical imports or model construction."""
import ast
import copy
from pathlib import Path
import unittest
import real_ir_hp_projection_fit as F


def decision_fixture():
    usability=dict(endpoint_mae={k:.1 for k in('pooled','unit','base','damage','heal')},
        nonzero_sign_accuracy=1.,healthy_count=2,healthy_max_abs=.05,eligibility={'positive_recall':1.})
    result={}
    for seed in F.SEEDS:
        for arm in F.ARMS:
            raw=dict(endpoint_mae={k:.1 if arm=='effect-hp-invariant' else 1. for k in usability['endpoint_mae']},
                     undefined=[],nonzero_sign_accuracy=1.)
            result[f's{seed}:{arm}']=dict(evaluations={'300':dict(fresh_primary={'raw':raw},
                train={'routed':copy.deepcopy(usability)},old_dev={'routed':copy.deepcopy(usability)})})
    return result


class ProjectionFitTest(unittest.TestCase):
    def test_counter_plan_and_numerical_imports_inside_guarded_worker_only(self):
        self.assertEqual(F.CONFIG['neural_forwards'],3*2*(300+2)+3)
        self.assertEqual(F.CONFIG['optimizer_updates'],1800)
        self.assertEqual(F.CONFIG['numerical_fits'],0)
        tree=ast.parse(Path(F.__file__).read_text());worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='worker')
        top=[a.name for n in tree.body if isinstance(n,ast.Import)for a in n.names]
        self.assertFalse(set(top)&{'numpy','torch','real_ir_transfer_fit','real_ir_hp_projection_model'})
        nested=[a.name for n in ast.walk(worker)if isinstance(n,ast.Import)for a in n.names]
        self.assertIn('numpy',nested);self.assertIn('torch',nested)

    def test_every_held_forward_after_complete_update_barrier(self):
        source=Path(F.__file__).read_text()
        barrier=source.index("require(counts['optimizer_updates']==1800")
        self.assertLess(barrier,source.index('with torch.no_grad():value=forward'))
        self.assertLess(barrier,source.index("H.M.make_model(torch,'new-printed-only')"))
        self.assertIn("mask=torch.from_numpy(a['target_mask'])",source)
        self.assertNotIn('F.class_statistics(',source);self.assertNotIn('F.stratum_statistics(',source)
        self.assertIn('baseline must reproduce frozen final checkpoint exactly',source)

    def test_conditional_readout_preserves_signed_effect_and_healthy_zero(self):
        pred=[[[.25,-.5],[.9,99.]],[[.5,.1],[.4,0.]]]
        labels=[[[1.,-2.],[0.,123.]],[[1.,0.],[1.,999.]]]
        mask=[[[0.,1.],[0.,0.]],[[0.,1.],[1.,0.]]]
        meta=[dict(operator='heal',intent_domain='unit',healthy_intent=False),
              dict(operator='heal',intent_domain='base',healthy_intent=True)]
        result=F.raw_metrics(pred,labels,mask,meta,[0,1])
        self.assertEqual(result['endpoint_support']['pooled'],2)
        self.assertEqual(result['endpoints'][0]['prediction'],-2.)
        self.assertAlmostEqual(result['healthy_max_abs'],.2)
        self.assertEqual(result['nonzero_sign_accuracy'],1.)

    def test_p_zero_unknown_not_false_zero_and_nonallowed_endpoint_rejected(self):
        meta=[dict(operator='damage',intent_domain='unit',healthy_intent=False)]
        result=F.raw_metrics([[[0.,0.]]],[[[1.,2.]]],[[[0.,1.]]],meta,[0])
        self.assertEqual(result['undefined'],[[0,0]]);self.assertIsNone(result['endpoint_mae']['pooled'])
        with self.assertRaisesRegex(ValueError,'actually allowed'):
            F.raw_metrics([[[.5,1.]]],[[[0.,2.]]],[[[0.,1.]]],meta,[0])

    def test_each_seed_requires_all_slices_sign_improvement_and_train_nonregression(self):
        result=decision_fixture();d=F.decisions(result)
        self.assertTrue(d['primary_passed']);self.assertFalse(d['semantic_validated'])
        result['s29:effect-hp-invariant']['evaluations']['300']['fresh_primary']['raw']['endpoint_mae']['base']=.251
        self.assertFalse(F.decisions(result)['primary_passed'])
        result=decision_fixture();result['s43:effect-hp-invariant']['evaluations']['300']['train']['routed']['endpoint_mae']['pooled']=.151
        self.assertFalse(F.decisions(result)['per_seed']['43']['train_routed_nonregression'])

    def test_zero_baseline_denominator_cannot_claim_improvement(self):
        result=decision_fixture()
        result['s17:baseline']['evaluations']['300']['fresh_primary']['raw']['endpoint_mae']['pooled']=0.
        d=F.decisions(result)['per_seed']['17'];self.assertIsNone(d['relative_raw_mae_improvement'])
        self.assertFalse(d['raw_improvement_passed'])

    def test_original_routed_usability_is_separate_from_oracle_raw_gate(self):
        result=decision_fixture();result['s17:effect-hp-invariant']['evaluations']['300']['old_dev']['routed']['healthy_max_abs']=.2
        d=F.decisions(result);self.assertTrue(d['per_seed']['17']['primary_passed'])
        self.assertFalse(d['per_seed']['17']['old_dev_original_usability']['effect-hp-invariant']['usable_endpoint_gate_passed'])


if __name__=='__main__':unittest.main()
