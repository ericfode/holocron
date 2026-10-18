"""Source and synthetic-array checks only; no model, native or real data."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import ability_correction as C


class SourceTests(unittest.TestCase):
    def test_fixed_zero_learning_contract_and_import_safety(self):
        self.assertEqual((6,0,0,0),(C.CONFIG['neural_forwards'],C.CONFIG['optimizer_updates'],C.CONFIG['native_applies'],C.CONFIG['numerical_fits']))
        tree=ast.parse(Path(C.__file__).read_text());names=[a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names];self.assertFalse(set(names)&{'torch','numpy'})
        text=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='worker'))
        self.assertIn("(('original', tc), ('neutral_all_heads', tn))",text)
        self.assertLess(text.index("run.intent('neural_forwards')"),text.index('model(tx, cc'))
        self.assertLess(text.index('model(tx, cc'),text.index('run.complete(token)'))
        self.assertNotIn('optimizer',text);self.assertNotIn('backward(',text)
        self.assertIn('strict=True',text);self.assertIn("old['semantic_signatures']['full']",text)

    def test_source_reservation_before_input_reads_and_guard_imports(self):
        tree=ast.parse(Path(C.__file__).read_text());text=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute'))
        self.assertLess(text.index('run.begin('),text.index('len(inputs)'))
        self.assertLess(text.index('run.begin('),text.index("import_module('effect_identifiability_fit')"))
        self.assertIn('run.remaining_seconds()',text);self.assertIn("args.stage in finished['completed']",text)

    def test_json_scalar_strictness_and_exclusive_write(self):
        with tempfile.TemporaryDirectory()as temp:
            p=Path(temp)/'value.json'
            with self.assertRaises(TypeError):C.write_new(p,object())
            self.assertFalse(p.exists());C.write_new(p,dict(ok=[1,True,None]));self.assertEqual({'ok':[1,True,None]},C.read(p))
            with self.assertRaises(FileExistsError):C.write_new(p,{})


@unittest.skipUnless(importlib.util.find_spec('numpy'),'NumPy optional synthetic tests')
class ArrayTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.np=np;self.names=['target_allowed','target_removed','target_damage_delta','target_exhausted_delta','target_shield_delta','target_power_delta','target_hp_delta'];self.roles=['source','own_helper','opponent_helper','anchor_a','anchor_b','auxiliary','own_base','opponent_base']
        self.manifest=dict(target_names=self.names,source_head_names=['s'+str(i)for i in range(9)],candidate_order=self.roles,intent_pairs=[dict(id=str(i),left_root=i,right_root=i+1)for i in range(0,8,2)])
        self.a=dict(context_features=np.zeros((8,18),np.float32),candidate_features=np.zeros((8,8,34),np.float32),source_targets=np.zeros((8,9),np.float32),source_mask=np.ones((8,9),np.float32),targets=np.zeros((8,8,7),np.float32),target_mask=np.ones((8,8,7),np.float32),selected_candidate_indices=np.asarray([3,4]*4,np.int64),source_cards=np.asarray(['IBH_104']*8))
        self.a['targets'][:,4,0]=1;self.old=dict(codes=['TRAIN'+str(i)for i in range(6)]+['ASH_081','IBH_104'],train_codes=['TRAIN'+str(i)for i in range(6)],scalers=dict(targets=[dict(name=n)for n in self.names],source_targets=[dict(name=n)for n in self.manifest['source_head_names']]))
        self.x=np.zeros((8,32),np.float32);self.c=np.zeros((8,8,43),np.float32)
        self.c[::2,3,41]=1;self.c[1::2,4,41]=1;self.c[...,42]=1

    def test_pair_validation_and_native_invariance_failure(self):
        self.assertEqual([3,4],C.validate(self.a,self.manifest,self.old,self.x,self.c))
        changed=self.c.copy();changed[1,3,40]=1
        with self.assertRaisesRegex(ValueError,'non-relation'):C.validate(self.a,self.manifest,self.old,self.x,changed)
        self.a['targets'][1,3,0]=1
        with self.assertRaisesRegex(ValueError,'native eligibility'):C.validate(self.a,self.manifest,self.old,self.x,self.c)

    def test_mixed_view_preserves_other15_heads_exactly(self):
        np=self.np;os=np.arange(72,dtype=np.float32).reshape(8,9);ob=np.arange(448,dtype=np.float32).reshape(8,8,7);ns=-os;nb=-ob
        source,branch=C.mixed_view(os,ob,ns,nb,0)
        np.testing.assert_array_equal(source,os);np.testing.assert_array_equal(branch[...,1:],ob[...,1:]);np.testing.assert_array_equal(branch[...,0],nb[...,0]);self.assertFalse(np.shares_memory(source,os));self.assertFalse(np.shares_memory(branch,ob))

    def test_invariance_flip_and_root_balanced_mae(self):
        np=self.np;p=self.a['targets'].copy();self.assertTrue(C.invariance(p,self.a,self.manifest,[3,4])['passed']);self.assertEqual(1.,C.eligibility_metrics(p,self.a,self.manifest,[3,4])['balanced_accuracy'])
        p[1,3,0]=.9;inv=C.invariance(p,self.a,self.manifest,[3,4]);self.assertFalse(inv['passed']);self.assertAlmostEqual(.9,inv['max_abs_difference']);self.assertGreater(inv['mean_threshold_flip_fraction'],0.)

    def test_noninferiority_and_all_head_controls(self):
        np=self.np;truth=self.a['targets'];original=truth.copy();original[::2,3,0]=.8;source=self.a['source_targets'];neutral=truth.copy();mixed=C.mixed_view(source,original,source+1,neutral,0)
        fake=types.SimpleNamespace(head_metrics=lambda *args:{'synthetic':True})
        with mock.patch.object(C.importlib,'import_module',return_value=fake):
            report=C.report_views(dict(original=(source,original),neutral_all_heads=(source+1,neutral),corrected=mixed),self.a,self.manifest,self.old,[3,4])
        self.assertTrue(report['primary']['passed']);self.assertTrue(all(report['controls'].values()));self.assertFalse(report['semantic_validated'])
        wrong=truth.copy();wrong[:,:,0]=1-truth[:,:,0];mixed=C.mixed_view(source,truth,source,wrong,0)
        with mock.patch.object(C.importlib,'import_module',return_value=fake):
            report=C.report_views(dict(original=(source,truth),neutral_all_heads=(source,wrong),corrected=mixed),self.a,self.manifest,self.old,[3,4])
        self.assertTrue(report['primary']['intent_invariant']);self.assertFalse(report['primary']['mae_noninferior']);self.assertFalse(report['primary']['balanced_accuracy_noninferior']);self.assertFalse(report['primary']['passed'])


if __name__=='__main__':unittest.main()
