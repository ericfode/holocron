"""Pure artificial metrics/JSON and source contracts; no arrays or model calls."""
import ast
import copy
from pathlib import Path
import unittest
import real_ir_intent_fit as F


def metric(terminal=False):
    mae={k:.1 for k in('pooled','unit','base','damage','heal')}
    if terminal:mae['base']=mae['heal']=None
    return dict(endpoint_mae=mae,nonzero_sign_accuracy=1.,healthy_max_abs=None if terminal else .05,
                eligibility=dict(balanced_accuracy=1.,positive_recall=1.),undefined=[])


def fixture():
    results={}
    for seed in F.SEEDS:
        for arm in F.ARMS:
            panels={}
            for name in('train','old_dev','exposed','development_all','development_primary','development_replay','terminal'):
                panels[name]=dict(raw=metric(name=='terminal'),routed=metric(name=='terminal'),
                    typed_intent=dict(programs=1 if name=='terminal' else 7,identity_accuracy=1.,amount_mae=.1))
            if arm=='matched-aux-latent':panels['development_primary']['routed']['endpoint_mae']['pooled']=.5
            results[f's{seed}:{arm}']=dict(evaluations={'300':panels})
    return results


class IntentFitTest(unittest.TestCase):
    def test_exact_phase_counts_and_no_top_numerical_imports(self):
        self.assertEqual(F.CONFIG['training_forwards'],3*3*300)
        self.assertEqual(F.CONFIG['evaluation_forwards'],3*(3*2+2))
        self.assertEqual(F.CONFIG['neural_forwards'],2724)
        self.assertEqual(F.CONFIG['numerical_fits'],0)
        tree=ast.parse(Path(F.__file__).read_text())
        top={a.name for n in tree.body if isinstance(n,ast.Import)for a in n.names}
        self.assertFalse(top&{'numpy','torch','real_ir_intent_model'})
        functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
        for name in('fit_worker','score_worker'):
            imports={a.name for n in ast.walk(functions[name])if isinstance(n,ast.Import)for a in n.names}
            self.assertTrue({'numpy','torch'}<=imports)
        fit=ast.get_source_segment(Path(F.__file__).read_text(),functions['fit_worker'])
        score=ast.get_source_segment(Path(F.__file__).read_text(),functions['score_worker'])
        self.assertNotIn('no_grad',fit);self.assertNotIn('.eval()',fit);self.assertNotIn('args.dataset',fit)
        self.assertNotIn('.backward()',score);self.assertNotIn('optimizer.step',score)
        self.assertIn("h[k][:40].copy()",fit);self.assertIn("h[k][:5].copy()",fit)
        self.assertIn(".get(m['operator']+'|'+m['intent_domain'],0.)",fit)
        self.assertIn('current must reproduce original final checkpoint exactly',fit)

    def test_reference_keeps_empty_witness_details(self):
        ref=dict(known_coordinates=371,known_eligibility=336,known_intended_deltas=35,mismatch_count=0,
                 removed_count=1,removal_mismatch_count=0,mismatches=[])
        self.assertTrue(F.reference_admitted(ref))
        ref['mismatches']=[{'synthetic':'disagreement'}];self.assertFalse(F.reference_admitted(ref))
        terminal=dict(known_coordinates=52,known_eligibility=48,known_intended_deltas=4,mismatch_count=0,
                      removed_count=0,removal_mismatch_count=0,mismatches=[])
        self.assertTrue(F.reference_admitted(terminal,True));self.assertFalse(F.reference_admitted(terminal))

    def test_typed_accuracy_counts_unique_programs_not_boards(self):
        p=[[0.]*13,[0.]*13];p[0][10:]=[1.,0.,3.];p[1][10:]=[0.,1.,2.]
        result=F.typed_scores([[1.,0.],[1.,0.],[0.,1.],[0.,1.]],[3.,3.,2.,2.],[0,0,1,1],p,[0,1,2,3])
        self.assertEqual(result['programs'],2);self.assertEqual(result['identity_accuracy'],1.)
        self.assertEqual(result['amount_mae'],0.);self.assertEqual(result['per_program'][0]['roots'],2)
        self.assertIsNone(F.typed_scores(None,None,None,None,None))
        tie=F.typed_scores([[0.,0.]],[3.],[0],p,[0]);self.assertEqual(tie['per_program'][0]['identity_prediction'],0)

    def test_development_and_terminal_decisions_separate(self):
        result=fixture();d=F.decisions(result)
        self.assertTrue(d['development_passed']);self.assertTrue(d['terminal_passed']);self.assertFalse(d['semantic_validated'])
        result['s29:factorized-intent']['evaluations']['300']['development_primary']['raw']['endpoint_mae']['base']=.251
        d=F.decisions(result);self.assertFalse(d['development_passed']);self.assertTrue(d['terminal_passed'])
        result=fixture();result['s17:factorized-intent']['evaluations']['300']['terminal']['routed']['eligibility']['balanced_accuracy']=None
        d=F.decisions(result);self.assertTrue(d['development_passed']);self.assertFalse(d['terminal_passed'])

    def test_relative_zero_and_missing_typed_support_cannot_pass(self):
        result=fixture();result['s43:matched-aux-latent']['evaluations']['300']['development_primary']['routed']['endpoint_mae']['pooled']=0.
        d=F.decisions(result)['per_seed']['43'];self.assertIsNone(d['development_routed_relative_improvement']);self.assertFalse(d['development_passed'])
        result=fixture();result['s17:factorized-intent']['evaluations']['300']['exposed']['typed_intent']=None
        self.assertFalse(F.decisions(result)['development_passed'])

    def test_train_nonregression_and_healthy_fail_independently(self):
        result=fixture();result['s17:factorized-intent']['evaluations']['300']['train']['routed']['endpoint_mae']['pooled']=.151
        self.assertFalse(F.decisions(result)['per_seed']['17']['train_routed_nonregression'])
        result=fixture();result['s17:factorized-intent']['evaluations']['300']['development_primary']['routed']['healthy_max_abs']=.101
        self.assertFalse(F.decisions(result)['development_passed'])

    def test_terminal_unsupported_slices_null_not_fabricated_passes(self):
        panel=dict(raw=metric(True),routed=metric(True));gate=F.endpoint_gate(panel,False)
        self.assertIsNone(panel['raw']['endpoint_mae']['base']);self.assertIsNone(gate['raw']['healthy_max_passed'])
        self.assertTrue(gate['raw']['mae_passed']);self.assertFalse(F.endpoint_gate(panel,True)['raw']['mae_passed'])

    def test_detailed_slice_rows_keep_unknown_raw_and_terminal_novelty_unscoped(self):
        point=dict(root=112,candidate=0,truth=3.,prediction=2.,error=1.,operator='damage',domain='unit',healthy=False)
        meta=[dict(program_index=0,source_card='PUBLIC',amount=3.)for _ in range(113)]
        public=[[dict(owner='p1',zone='space',damage=0.,hp=10.)]for _ in range(113)]
        programs=[dict(selector=dict(cost_cap=dict(present=False,value=None)))]
        result=F.endpoint_slices({'endpoints':[point]},{'endpoints':[]},meta,public,programs,[[[0.,0.]]] * 113)
        self.assertIsNone(result['rows'][0]['raw_error']);self.assertIsNone(result['rows'][0]['prior_seen'])
        self.assertEqual(result['rows'][0]['cap'],'absent');self.assertIsNone(result['tables']['joint'][result['rows'][0]['joint']]['raw_mae'])


if __name__=='__main__':unittest.main()
