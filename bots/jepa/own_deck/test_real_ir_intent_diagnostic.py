"""Artificial TRAIN JSON/list fixtures only; never inspect real arrays or metrics."""
import ast
import copy
from pathlib import Path
import unittest
import real_ir_intent_diagnostic as D


def fixture():
    selector=dict(target_kind='unit',owner='any',cost_cap=dict(present=False,value=None))
    programs=[dict(selector=selector,effect=dict(operator='heal',amount={'value':v}))for v in(1.,3.)]
    p=[]
    for amount in(1.,3.):
        x=[0.]*13;x[11:]=[1.,amount];p.append(x)
    data=dict(program_features=p,source_printed_features=[[0.]*10,[1.]+[0.]*9],program_indices=[0,1,0,1],
              candidate_features=[],targets=[],target_mask=[],baseline_predictions=[])
    metadata=[];pred=[]
    for i,(amount,damage,truth)in enumerate(((1.,2.,-1.),(3.,2.,-2.),(1.,0.,0.),(3.,0.,0.))):
        c=[0.]*17;c[0]=c[2]=c[6]=c[8]=1.;c[12:]=[damage,1.,10.,1.,1.]
        other=list(c);other[16]=0.
        labels=[[float(i!=3),truth],[0.,0.]];mask=[[1.,float(i!=3)],[1.,0.]]
        data['candidate_features'].append([c,other]);data['targets'].append(labels)
        data['target_mask'].append(mask);data['baseline_predictions'].append(copy.deepcopy(labels))
        metadata.append(dict(root=i,partition='train',operator='heal',amount=amount,intent_domain='unit',source_card='TRAIN_'+str(i%2)))
        pred.append([[.5,-.25 if truth else .05],[.1,0.]])
    weights=dict(class_statistics=dict(class_counts=[5,3],weights=[.8,8/6]),
                 stratum_statistics=dict(counts={'heal|unit':3},weights={'heal|unit':1.}))
    scales=dict(program=[1.]*12+[3.],candidate=[1.]*12+[4.,1.,10.,1.,1.])
    return data,metadata,programs,[{},{}],{'s17:baseline':pred},weights,scales


class TrainOnlyDiagnosticTest(unittest.TestCase):
    def test_magnitude_clipping_and_physical_units_are_distinct(self):
        result=D.diagnose(*fixture());algebra=result['scaling_algebra']
        self.assertEqual(algebra['clipped_literal_mismatches'],0)
        self.assertEqual(algebra['signed_literal_mismatches'],2)
        self.assertEqual(algebra['reference_known_mismatches'],[])
        self.assertTrue(all(algebra['frozen_weight_arithmetic'].values()))
        self.assertEqual(result['support']['operator_ranges']['heal']['amount'],[1.,3.])
        self.assertEqual(result['support']['known_endpoints'],3)

    def test_conditional_and_routed_residuals_do_not_fit(self):
        result=D.diagnose(*fixture());panel=result['panels']['s17:baseline']
        self.assertNotEqual(panel['raw']['mae'],panel['routed']['mae'])
        self.assertEqual(result['endpoint_rows'][0]['raw'],-.5)
        self.assertAlmostEqual(result['endpoint_rows'][0]['endpoint_loss_coordinate_weight'],.5/3)
        self.assertTrue(all(v==0 for v in result['counts'].values()))
        self.assertTrue(result['training_only']);self.assertFalse(result['semantic_validated'])

    def test_same_state_amount_contrast_exposes_printed_confound(self):
        result=D.diagnose(*fixture());pair=result['same_state_amount_contrasts'][0]
        self.assertEqual(pair['roots'],[0,1]);self.assertEqual(pair['native_difference'],-1.)
        self.assertEqual(pair['raw_difference'],0.)
        self.assertTrue(pair['selector_fields_equal']);self.assertFalse(pair['source_printed_equal'])

    def test_unknown_endpoint_never_treated_as_zero(self):
        args=list(fixture());args[0]['targets'][3][0][1]='unknown-poison'
        args[0]['baseline_predictions'][3][0][1]='different-poison'
        args[4]['s17:baseline'][3][0][1]='unobserved-prediction'
        self.assertEqual(D.diagnose(*args)['support']['known_endpoints'],3)

    def test_held_metadata_and_extra_bank_reject(self):
        args=list(fixture());args[1][1]['partition']='held'
        with self.assertRaisesRegex(ValueError,'TRAIN metadata'):D.diagnose(*args)
        args=list(fixture());args[0]['program_features'].append([0.]*13)
        with self.assertRaisesRegex(ValueError,'TRAIN program banks'):D.diagnose(*args)
        args=list(fixture());args[1][1]['root']=40
        with self.assertRaisesRegex(ValueError,'TRAIN metadata'):D.diagnose(*args)

    def test_wrong_scale_or_native_units_report_not_repaired(self):
        args=list(fixture());args[-1]['program'][12]=4.
        with self.assertRaisesRegex(ValueError,'physics scales'):D.diagnose(*args)
        args=list(fixture());args[0]['targets'][0][0][1]=-.25
        result=D.diagnose(*args)
        self.assertEqual(result['scaling_algebra']['reference_known_mismatches'],[[0,0,1]])
        self.assertGreater(result['scaling_algebra']['clipped_literal_mismatches'],0)

    def test_zero_probability_is_undefined(self):
        args=list(fixture());args[4]['s17:baseline'][0][0]=[0.,0.]
        result=D.diagnose(*args)
        self.assertIsNone(result['endpoint_rows'][0]['raw'])
        self.assertEqual(result['panels']['s17:baseline']['undefined_conditional'],1)

    def test_worker_slices_before_list_conversion_and_has_no_science_calls(self):
        source=Path(D.__file__).read_text();tree=ast.parse(source)
        imports={a.name for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names}
        self.assertFalse(imports&{'numpy','torch','real_ir_transfer_fit','real_ir_transfer_model'})
        self.assertIn("h[k][:40].tolist()",source)
        self.assertIn("h['predictions'][:40].tolist()",source)
        self.assertIn("bank_indices=sorted(set(a['program_indices']))",source)
        self.assertNotIn('fit_result',source)
        loads=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='load']
        self.assertTrue(all(any(k.arg=='allow_pickle'and k.value.value is False for k in n.keywords)for n in loads))


if __name__=='__main__':unittest.main()
