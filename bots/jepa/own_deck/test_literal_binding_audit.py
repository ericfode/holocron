"""Pure token/plan contracts; no neural/model/native execution."""
from pathlib import Path
import sys
import unittest
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parent))
import literal_binding_audit as A


class BindingTests(unittest.TestCase):
    def test_exact_frozen_budget_and_head_order(self):
        self.assertEqual(A.COUNTS,dict(model_forwards=6,backwards=0,optimizer_updates=0,native_calls=0,paid_jobs=0))
        self.assertEqual((A.HEADS[2],A.HEADS[5],A.HEADS[7]),("cost_resource","target_exhausted_delta","xp_delta"))

    def test_numeric_roles_do_not_conflate_list_length_cost_effect_selector(self):
        self.assertEqual(A.role(("costs",0,"amount","value"),"number"),"activation-cost")
        self.assertEqual(A.role(("effect","amount","value"),"number"),"effect-payload")
        self.assertEqual(A.role(("targetResolver","predicate","right","value"),"number"),"target-selector")
        self.assertEqual(A.role(("costs",),"length"),"structural-list-length")

    def test_tensor_literal_roundtrip_and_distinct_semantic_programs(self):
        data,_,_=A.references()
        trace=A.tensor_binding_trace(data)
        self.assertEqual(trace["distinct_input_signatures"],12)
        self.assertFalse(trace["collisions"])
        by={row["code"]:row for row in trace["programs"]}
        self.assertNotEqual(by["SHD_004"]["semantic_tensor_sha256"],by["TWI_206"]["semantic_tensor_sha256"])
        for row in trace["programs"]:
            for literal in row["numeric_literals"]:self.assertAlmostEqual(literal["physical_value"],literal["recovered_first_channel"],places=5)

    def test_local_input_novelty_does_not_use_board_fingerprint(self):
        self.assertEqual(A.input_signature("p",[2,0],[0,1]),A.input_signature("p",[2,0],[0,1]))
        self.assertNotEqual(A.input_signature("p",[2,0],[0,1]),A.input_signature("p",[1,0],[0,1]))
        self.assertNotEqual(A.input_signature("p",[2,0],[0,1]),A.input_signature("q",[2,0],[0,1]))

    def test_pure_import_and_saved_artifacts_do_not_import_torch(self):
        code="import sys; sys.path.insert(0,sys.argv[1]); import literal_binding_audit as a; d,_,_=a.references(); a.tensor_binding_trace(d); assert not any(x=='torch' or x.startswith('torch.') for x in sys.modules)"
        subprocess.run([sys.executable,"-B","-c",code,str(Path(A.__file__).parent)],check=True,capture_output=True,text=True)

    def test_all_negative_heads_signed_bias_and_binary_accuracy_are_retained(self):
        import numpy as np
        arrays=dict(source_use=np.zeros(16),source_use_mask=np.ones(16),candidate_allowed=np.ones((16,8)),candidate_allowed_mask=np.ones((16,8)),
                    targets=np.zeros((16,8,11)),target_mask=np.ones((16,8,11)),primary_candidate_mask=np.tile([1.]*7+[0.],(16,1)),
                    state_families=np.repeat(np.arange(8),2),source_cards=np.tile(["SHD_004","TWI_206"],8))
        native=dict(arrays=arrays,source_new=np.ones(16,bool),candidate_new=np.ones((16,8),bool),context=np.zeros((16,2)),candidates=np.zeros((16,8,26)),settled=np.ones((16,8),bool))
        result=A.metrics(np.full(16,.2),np.full((16,8,11),.6),native,dict(head_scaling=dict(scale=[1.]*11)))
        self.assertEqual(len(result["heads"]["primary"]),11)
        self.assertEqual(result["heads"]["primary"]["terminal"]["all"]["binary_accuracy_at_point5"],0.)
        self.assertAlmostEqual(result["heads"]["primary"]["damage_delta"]["all"]["signed_mean_residual"],.6)
        self.assertEqual(len(result["mutually_legal_settled_pairs"]),24)
        self.assertEqual(result["fixed_three_head_train_scaled_macro"],0.)


if __name__=="__main__":unittest.main()
