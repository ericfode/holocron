"""Small synthetic data/matrix tests only; no actual experiment input or NN."""
import copy
import importlib.util
from pathlib import Path
import unittest
import numpy as np

SPEC=importlib.util.spec_from_file_location("learning_sanity_data",Path(__file__).with_name("learning_sanity_data.py"))
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)


def spec(binary=False):
    return dict(name="synthetic",binary=binary,center=0.,scale=1.,loss_coefficient=1/12,
                class_weights={"-1":2.,"0":.5,"1":1.})


def packets():
    y=np.zeros((48,8,7),np.float32);m=np.zeros_like(y)
    selected=np.arange(48,dtype=np.int64)%8
    for i in range(14):y[i,selected[i],2:]=[i,i+1,-i,2*i,3*i];m[i,selected[i],2:]=1
    arrays=dict(targets=y,target_mask=m,source_targets=np.zeros((48,9),np.float32),source_mask=np.ones((48,9),np.float32),selected_candidate_indices=selected)
    shared=dict(shuffle_roots=list(range(14)),fixed_mapping=list(range(1,14))+[0],effect_columns=list(range(2,7)))
    return arrays,shared


class DataSanityTests(unittest.TestCase):
    def test_joint_immutable_packet_assignment(self):
        arrays,shared=packets();before=copy.deepcopy(arrays);out=D.fixed_assignment(arrays,shared,np.arange(21))
        for i,source in enumerate(shared["fixed_mapping"]):
            np.testing.assert_array_equal(out["targets"][i,arrays["selected_candidate_indices"][i],2:],before["targets"][source,arrays["selected_candidate_indices"][source],2:])
        for k,v in arrays.items():np.testing.assert_array_equal(v,before[k])
        np.testing.assert_array_equal(out["target_mask"],before["target_mask"])
        np.testing.assert_array_equal(out["targets"][21:],before["targets"][21:])

    def test_partial_known_or_nontrain_or_not_deranged_rejected(self):
        arrays,shared=packets();arrays["target_mask"][14,arrays["selected_candidate_indices"][14],2]=1
        with self.assertRaisesRegex(ValueError,"partially known"):D.fixed_assignment(arrays,shared,np.arange(21))
        arrays,shared=packets();shared["fixed_mapping"]=list(range(14))
        with self.assertRaisesRegex(ValueError,"derangement"):D.fixed_assignment(arrays,shared,np.arange(21))

    def test_ridge_mass_omits_neural_coefficient_and_root_denominator(self):
        y=np.asarray([[1.,0.,999.],[-1.,999.,999.]])
        m=np.asarray([[1,1,0],[1,0,0]])
        base=D.ridge_weights(y,m,spec());nn,counts,nroots=D.weights_for(y,m,spec(),np.asarray([0,1]))
        np.testing.assert_allclose(base,[[.5,.25,0],[2,0,0]])
        np.testing.assert_allclose(nn,base*(1/12)/2)
        np.testing.assert_array_equal(counts,[2,1]);self.assertEqual(nroots,2)

    def test_intercept_unpenalized_and_lambda_one_sum_solution(self):
        x=np.asarray([[-1.],[0.],[1.],[100.]])
        y=np.asarray([1.,3.,5.,999.]);m=np.asarray([1.,1.,1.,0.])
        p,raw,fit=D.fit_head(x,y,m,spec(),np.arange(3))
        np.testing.assert_allclose(fit["coefficients"],[3.,4/3],atol=1e-12)
        self.assertAlmostEqual(fit["ridge_weight_sum"],3.)
        self.assertAlmostEqual(fit["original_neural_weight_sum"],1/12)
        self.assertFalse(fit["intercept_penalized"])
        self.assertAlmostEqual(raw[1],3.)

    def test_binary_clip_scoring_only_and_numeric_not_clipped(self):
        x=np.asarray([[-1.],[0.],[1.],[100.]])
        y=np.asarray([0.,0.,1.,0.]);m=np.asarray([1.,1.,1.,0.])
        p,raw,fit=D.fit_head(x,y,m,spec(True),np.arange(3))
        self.assertTrue(raw[-1]>1);self.assertEqual(p[-1],1.)
        p2,raw2,_=D.fit_head(x,y,m,spec(False),np.arange(3))
        np.testing.assert_array_equal(p2,raw2);self.assertTrue(p2[-1]>1)

    def test_features_branch_no_intent_and_held_ids_remain_zero(self):
        arrays=dict(context_features=np.zeros((48,18),np.float32),candidate_features=np.arange(48*8*34,dtype=np.float32).reshape(48,8,34),
                    source_cards=np.asarray(["A"]*21+["HELD"]*27),selected_candidate_indices=np.zeros(48,np.int64))
        prior=dict(train_codes=list("ABCDEFG"))
        source,branch=D.features(arrays,prior)
        changed=copy.deepcopy(arrays);changed["selected_candidate_indices"][:]=1
        source2,branch2=D.features(changed,prior)
        self.assertFalse(np.array_equal(source,source2));np.testing.assert_array_equal(branch,branch2)
        standardized,stats=D.standardize(branch,np.arange(21))
        self.assertFalse(standardized[21:,:,-7:].any())
        self.assertTrue(np.isfinite(standardized).all());self.assertEqual(stats["observations"],168)
        np.testing.assert_allclose(np.asarray(stats["center"])[-7:],0)

    def test_population_variance_unknown_not_zero_and_half_thresholds(self):
        y=np.asarray([0.,-1.,2.,999.]);m=np.asarray([1.,1.,1.,0.])
        record=D.support(y,m)
        self.assertEqual(record["values"],[ -1.,0.,2.]);self.assertEqual(record["unknown_coordinates"],1)
        self.assertAlmostEqual(record["variance"],14/9)
        metric=D.metrics(np.asarray([.25,-.26,.26,0.]),y,m,spec(),3)
        self.assertEqual(metric["sign_accuracy"],1.)
        binary=D.metrics(np.asarray([.5,-1.]),np.asarray([1.,0.]),np.ones(2),spec(True),2)
        self.assertEqual(binary["sign_accuracy"],1.)

    def test_conflict_audit_uses_saved_consumed_keys_not_masks_or_labels(self):
        arrays=dict(source_targets=np.asarray([[0.],[1.]]),source_mask=np.ones((2,1)),targets=np.zeros((2,8,1)),target_mask=np.zeros((2,8,1)))
        prior=dict(scalers=dict(source_targets=[dict(name="s")],targets=[dict(name="t")]),input_audits=dict(typed=dict(input_records=[
            dict(root=0,kind="source",candidate=None,input_sha256="same",mask=[1]),
            dict(root=1,kind="source",candidate=None,input_sha256="same",mask=[0])])) )
        result=D.consumed_input_conflicts(arrays,prior,np.asarray([0,1]))
        self.assertEqual(result["conflict_count"],1)
        arrays["source_mask"][1]=0
        self.assertEqual(D.consumed_input_conflicts(arrays,prior,np.asarray([0,1]))["conflict_count"],0)


if __name__=="__main__":unittest.main()
