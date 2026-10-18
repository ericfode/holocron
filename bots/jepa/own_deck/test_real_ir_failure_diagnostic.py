"""Artificial JSON/list fixtures only; never open saved research artifacts."""
import ast
import copy
import json
from pathlib import Path
import unittest
import real_ir_failure_diagnostic as D


def fixture():
    selector=dict(owner='any',target_kind='any',zone={'value':'anyAttackable'},
                  arena={'present':False,'values':None},cost_cap={'present':False,'value':None})
    program=dict(selector=selector,effect=dict(operator='heal',amount={'value':3}))
    public=[];metadata=[]
    for i,(damage,hp,zone) in enumerate(((2,10,'space'),(2,30,'base'),(2,10,'space'),(0,30,'base'))):
        public.append([dict(is_intended=True,is_base=zone=='base',is_unit=zone!='base',is_leader=False,
            owner='p1',zone=zone,damage=damage,hp=hp,known={'damage':True,'hp':True})])
        metadata.append(dict(program_index=0,operator='heal',amount=3,source_card='PUBLIC_001'))
    manifest=dict(root_metadata=metadata,public_before_records=public,canonical_programs=[program],
                  source_printed_profiles=[{'cost':2}],split=dict(train=[0],held=[1,2,3]))
    predictions=[[[.5,-1.]],[[.25,-.5]],[[.5,-1.]],[[.5,.2]]]
    def cell(indices,kind):
        rows=[]
        for i in indices:
            truth=0. if i==3 else -2.
            prediction=truth if kind=='reference' else 0. if kind=='zero' else predictions[i][0][1]
            rows.append(dict(root=i,candidate=0,truth=truth,prediction=prediction,domain='base' if i in (1,3) else 'unit'))
        return dict(endpoints=rows,eligibility={'positive_recall':1.},
            endpoint_mae=dict(pooled=1.,unit=1.,base=1.,damage=None,heal=1.),
            nonzero_sign_accuracy=1.,healthy_count=1,healthy_max_abs=.2)
    def evaluation(kind):return {'train':cell([0],kind),'held':cell([1,2,3],kind)}
    result=dict(results={f's{s}:{a}':{'evaluations':{'300':evaluation('learned')}}for s in D.SEEDS for a in D.ARMS},
        baseline_evaluations={'deterministic-reference':evaluation('reference'),
                             'all-ones-eligibility-zero-effect':evaluation('zero')},
        decisions=dict(per_seed={str(s):dict(endpoint_slices_passed=False,healthy_max_abs_passed=False,
            eligibility_discrimination_qualified=False)for s in D.SEEDS}))
    saved={f's{s}:{a}':copy.deepcopy(predictions)for s in D.SEEDS for a in D.ARMS}
    labels=dict(targets=[[[1.,-2.]],[[1.,-2.]],[[1.,-2.]],[[1.,0.]]],
                primary_target_mask=[[[1.,1.]]] * 4)
    features=dict(program_indices=[0]*4,program_features=[[0.]*10+[0.,1.,3.]],
        source_printed_features=[[2.,1.,0.,0.,0.,0.,0.,1.,0.,0.]],candidate_features=[])
    for scene in public:
        c=[0.]*17;c[12:17]=[scene[0]['damage'],1.,scene[0]['hp'],1.,1.]
        features['candidate_features'].append([c])
    return {'worlds':[{}]*4},manifest,result,saved,labels,features


class SavedDiagnosticTest(unittest.TestCase):
    def run_fixture(self):
        p,m,r,s,l,f=fixture()
        return D.diagnose(p,m,r,saved_predictions=s,saved_labels=l,feature_inputs=f)

    def test_import_safe_and_worker_only_saved_loads(self):
        tree=ast.parse(Path(D.__file__).read_text())
        imports=[a.name for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names]
        self.assertFalse(set(imports)&{'numpy','torch','real_ir_transfer_fit','real_ir_transfer_model'})
        worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='worker')
        loads=[n for n in ast.walk(worker)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='load']
        self.assertTrue(loads)
        self.assertTrue(all(any(k.arg=='allow_pickle'and k.value.value is False for k in n.keywords)for n in loads))

    def test_train_support_excludes_held_composition(self):
        out=self.run_fixture()
        self.assertEqual(out['support']['joint'],[['heal',3.,2.,10.]])
        rows=out['endpoint_rows'][:4]
        self.assertTrue(rows[0]['train_joint_seen']);self.assertFalse(rows[1]['train_joint_seen'])
        self.assertTrue(rows[2]['train_joint_seen']);self.assertFalse(rows[3]['train_joint_seen'])
        self.assertEqual(out['support']['op_targetkind'],[['heal','unit']])
        self.assertFalse(rows[1]['train_op_targetkind_seen'])

    def test_saved_oracle_gate_is_division_not_sign_repair(self):
        out=self.run_fixture();row=out['endpoint_rows'][1]
        self.assertEqual(row['prediction'],-.5);self.assertEqual(row['conditional_raw'],-2.)
        self.assertTrue(row['gate_sign_preserved'])
        panel=out['panels']['s17:new-full']['held']
        self.assertLess(panel['oracle_eligibility']['mae'],panel['routed']['mae'])
        self.assertEqual(out['counts']['neural_forwards'],0)
        self.assertFalse(out['semantic_validated'])

    def test_zero_probability_is_undefined_and_mismatch_rejected(self):
        p,m,r,s,l,f=fixture();s['s17:new-full'][1][0][0]=0.
        out=D.diagnose(p,m,r,saved_predictions=s)
        self.assertIsNone(out['endpoint_rows'][1]['conditional_raw'])
        self.assertEqual(out['endpoint_rows'][1]['conditional_unavailable_reason'],'p=0; no imputation')
        s['s17:new-full'][1][0][1]=99.
        with self.assertRaisesRegex(ValueError,'JSON/NPZ'):D.diagnose(p,m,r,saved_predictions=s)

    def test_native_mask_not_missing_as_zero(self):
        p,m,r,s,l,f=fixture()
        for i in range(4):
            m['public_before_records'][i].append(dict(m['public_before_records'][i][0],is_intended=False))
            l['primary_target_mask'][i].append([0.,0.]);l['targets'][i].append([0.,0.])
            for values in s.values():values[i].append([.9,0.])
        out=D.diagnose(p,m,r,saved_predictions=s,saved_labels=l)
        row=next(x for x in out['eligibility_rows']if x['method']=='s17:new-full'and x['root']==1 and x['candidate']==1)
        self.assertFalse(row['native_known']);self.assertIsNone(row['native_truth']);self.assertIsNone(row['error'])

    def test_oracle_gate_requires_actual_known_eligible_native_endpoint(self):
        p,m,r,s,l,f=fixture();l['targets'][1][0][0]=0.
        with self.assertRaisesRegex(ValueError,'committed/eligible'):D.diagnose(p,m,r,saved_labels=l)

    def test_space_base_input_comparison_keeps_source_and_state(self):
        out=self.run_fixture()
        pair=next(x for x in out['space_base_pairs']if x['method']=='s17:new-full')
        self.assertEqual((pair['space_hp'],pair['base_hp']),(10.,30.))
        self.assertTrue(pair['saved_endpoint_inputs_except_hp_equal'])
        p,m,r,s,l,f=fixture();f['candidate_features'][1][0][13]=0.
        with self.assertRaisesRegex(ValueError,'actual saved endpoint'):D.diagnose(p,m,r,feature_inputs=f)

    def test_gate_failure_preserves_discrimination_unqualified(self):
        out=self.run_fixture();gate=out['gate_failures']['17']
        self.assertEqual(gate['thresholds']['endpoint_mae_max'],.25)
        self.assertNotIn('eligibility_discrimination_qualified',gate['failed_flags'])
        self.assertFalse(gate['saved_decision']['eligibility_discrimination_qualified'])
        self.assertIn('base',gate['mae_violations'])
        json.dumps(out,allow_nan=False)


if __name__=='__main__':unittest.main()
