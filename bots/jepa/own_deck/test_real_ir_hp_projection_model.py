"""Pure metadata, AST and fake-state tests; no Torch/model construction."""
import ast
import copy
from pathlib import Path
import unittest

import real_ir_hp_projection_model as H


class FakeState:
    def __init__(self,values):
        self.values=copy.deepcopy(values)
        self.shape=(len(values),len(values[0]),len(values[0][0]))
    def clone(self):return FakeState(self.values)
    def __setitem__(self,key,value):
        if key!=(Ellipsis,2):raise AssertionError('only HP coordinate may change')
        for root in self.values:
            for candidate in root:candidate[2]=value


class ProjectionTests(unittest.TestCase):
    def test_only_hp_changes_original_and_knownness_preserved(self):
        values=[[[.75,1.,1.,1.],[1.25,1.,3.,1.]],[[0.,1.,.8,1.],[.5,1.,3.,0.]]]
        original=FakeState(values);result=H.project_endpoint_state(None,(original,))
        self.assertIsInstance(result,tuple);self.assertEqual(len(result),1);self.assertIsNot(result[0],original)
        self.assertEqual(original.values,values)
        for before_root,after_root in zip(values,result[0].values):
            for before,after in zip(before_root,after_root):self.assertEqual(after,[before[0],before[1],0.,before[3]])

    def test_hp_only_counterfactual_becomes_identical_at_state_input(self):
        space=FakeState([[[1.25,1.,1.,1.]]]);base=FakeState([[[1.25,1.,3.,1.]]])
        self.assertNotEqual(space.values,base.values)
        self.assertEqual(H.project_endpoint_state(None,(space,))[0].values,H.project_endpoint_state(None,(base,))[0].values)

    def test_bad_hook_inputs_fail_closed(self):
        with self.assertRaises(ValueError):H.project_endpoint_state(None,())
        with self.assertRaises(ValueError):H.project_endpoint_state(None,(FakeState([[[1.,1.,1.]]]),))
        with self.assertRaises(ValueError):H.project_endpoint_state(None,[FakeState([[[1.,1.,1.,1.]]])])

    def test_contract_keeps_frozen_named_weights_and_single_projection(self):
        c=H.contract();self.assertEqual(c['base_source']['sha256'],H.BASE_SHA256)
        self.assertEqual(c['parameters'],H.M.contract()['parameters']['new-full'])
        self.assertEqual(c['parameters']['allocated'],1458);self.assertEqual(c['added_parameters'],0)
        self.assertEqual(c['projection']['zero_columns'],[2]);self.assertEqual(c['projection']['originating_candidate_column'],14)
        self.assertEqual(c['card_effect_api']['output_width'],8);self.assertFalse(c['semantic_validated'])

    def test_factory_delegates_once_no_new_modules_or_framework_imports(self):
        tree=ast.parse(Path(H.__file__).read_text());factory=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='make_model')
        calls=[n for n in ast.walk(factory)if isinstance(n,ast.Call)]
        base_calls=[n for n in calls if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='M'and n.func.attr=='make_model']
        self.assertEqual(len(base_calls),1);self.assertEqual(ast.literal_eval(base_calls[0].args[1]),'new-full')
        hooks=[n for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='register_forward_pre_hook']
        self.assertEqual(len(hooks),1);self.assertEqual(ast.unparse(hooks[0].func.value),'model.state')
        branch=next(n for n in factory.body if isinstance(n,ast.If));self.assertEqual(ast.unparse(branch.test),"arm == 'effect-hp-invariant'")
        imports=[a.name for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(imports)&{'torch','numpy','subprocess'})
        self.assertFalse(any(isinstance(n,ast.ClassDef)for n in tree.body))


if __name__=='__main__':unittest.main()
