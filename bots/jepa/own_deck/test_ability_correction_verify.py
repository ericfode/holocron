"""Harmless stdlib-only synthetic verifier tests, never saved-array analysis."""
import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import ability_correction_verify as V


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.pairs=[dict(left_root=i,right_root=i+1)for i in range(0,8,2)]

    def test_import_and_verifier_have_no_scientific_execution(self):
        tree=ast.parse(Path(V.__file__).read_text())
        imports=[alias.name for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))for alias in node.names]
        self.assertFalse(set(imports)&{'torch','numpy','ability_correction'})
        text=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute'))
        self.assertLess(text.index('run.begin('),text.index("import_module('effect_identifiability_fit')"))
        self.assertLess(text.index('with guard:'),text.index('import numpy'))
        self.assertIn("write_new(args.out / 'result.json', result)",text)
        self.assertNotIn('run.intent(',text);self.assertNotIn('report_views',Path(V.__file__).read_text())

    def test_root_balanced_mae_and_binary_accuracy(self):
        truth=[[0.,1.]for _ in range(8)];mask=[[1,1]for _ in range(8)];pred=[[.2,.8]for _ in range(8)]
        e,i=V.metric(pred,truth,mask,[0,1],self.pairs)
        self.assertAlmostEqual(e['mae'],.2);self.assertEqual(e['known'],16);self.assertEqual(e['balanced_accuracy'],1.);self.assertTrue(i['passed'])
        mask[0]=[0,1];pred[0][0]=999.
        e,_=V.metric(pred,truth,mask,[0,1],self.pairs)
        self.assertAlmostEqual(e['mae'],.2);self.assertEqual(e['known'],15)

    def test_per_anchor_no_class_support_stays_null(self):
        truth=[[0.,1.]for _ in range(8)];mask=[[1,1]for _ in range(8)]
        a,_=V.metric(truth,truth,mask,[0],self.pairs);b,_=V.metric(truth,truth,mask,[1],self.pairs)
        self.assertIsNone(a['balanced_accuracy']);self.assertIsNone(b['balanced_accuracy'])
        self.assertEqual(a['negative'],8);self.assertEqual(b['positive'],8)

    def test_invariance_uses_fixed_pairs_and_threshold_flips(self):
        truth=[[0.,1.]for _ in range(8)];mask=[[1,1]for _ in range(8)];pred=[r[:]for r in truth];pred[1][0]=.75
        _,i=V.metric(pred,truth,mask,[0],self.pairs)
        self.assertFalse(i['passed']);self.assertEqual(i['max_abs_difference'],.75);self.assertEqual(i['mean_threshold_flip_fraction'],.25)
        mask[0]=[0,0];mask[1]=[0,0]
        _,i=V.metric(pred,truth,mask,[0],self.pairs);self.assertFalse(i['passed'])

    def synthetic_native(self):
        cases=[];records=[dict(schema='jepa-ability-correction-apply-journal/1',maxApplyCalls=32,planSha256='toy')];call=0
        for world in range(8):
            steps=[]
            for local in range(3 if world<4 else 2):
                call+=1;s=dict(before={'toy':call},action={'card':'c'+str(world)},after={'toy':call+1});steps.append(s)
                records.extend([dict(phase='beforeApply',applyCall=call,before=s['before'],offeredAction=s['action']),dict(phase='afterApply',applyCall=call,after=s['after'])])
            case=dict(world_id=world,steps=steps);cases.append(case);records.append(dict(phase='contextComplete',case=case))
        return dict(schema='jepa-ability-correction-native/1',collectionComplete=True,collectionPlanSha256='toy',applyCalls=20,cases=cases),records

    def test_native_journal_reconstruction_and_bad_order(self):
        raw,rows=self.synthetic_native();bad=[];V.journal_check(raw,rows,lambda ok,label:bad.append(label)if not ok else None);self.assertEqual(bad,[])
        rows[1],rows[2]=rows[2],rows[1];V.journal_check(raw,rows,lambda ok,label:bad.append(label)if not ok else None);self.assertIn('native chronology without errors',bad)

    def test_closed_chain_counts_and_tamper(self):
        rows=[];previous='0'*64;counts=dict(neural_forwards=6,native_applies=20,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
        for i,(event,data)in enumerate((('initialized',{}),('finish',dict(status='completed',charged=counts)))):
            body=dict(schema='jepa-sealed-budget-journal/1',sequence=i,previous_sha256=previous,event=event,data=data);previous=hashlib.sha256(V.encoded(body)).hexdigest();rows.append(dict(body,record_sha256=previous))
        bad=[];self.assertEqual(V.closed_counts(rows,lambda ok,label:bad.append(label)if not ok else None),counts);self.assertEqual(bad,[])
        rows[-1]['data']['status']='failed';V.closed_counts(rows,lambda ok,label:bad.append(label)if not ok else None);self.assertIn('closed chain',bad);self.assertIn('closed successful stage',bad)

    def test_weight_hash_does_not_load_or_execute_model(self):
        class Bytes:
            dtype='float32';shape=(1,)
            def tobytes(self):return b'\0\0\0\0'
        value=V.state_hash({'b':Bytes(),'a':Bytes()});self.assertEqual(value,V.state_hash({'a':Bytes(),'b':Bytes()}));self.assertEqual(len(value),64)

    def execute_toy(self,verify):
        class Run:
            state={'pending':None,'proofs':{}}
            def begin(self,*args,**kw):self.state['pending']={'stage':'verify'}
            def remaining_seconds(self):return 3.
            def finish(self,status,**kw):self.finished=status;return {'completed':['verify']if status=='completed'else[]}
        run=Run()
        class Guard:
            def __init__(self,seconds):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def receipt(self):return {'toy':True}
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp).resolve()/'verify-1';receipt=Path(temp).resolve()/'verify-1-stage-receipt.json'
            class Budget:
                frozen={}
                spec=dict(guard=dict(cpu_workers=1,rss_bytes=1073741824),stages=dict(verify=dict(reservation=dict(seconds=3,neural_forwards=0,native_applies=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.),outputs=[str(out),str(receipt)])))
                def __init__(self,path):pass
                @contextmanager
                def lease(self):yield run
            modules={'sealed_budget':types.SimpleNamespace(Budget=Budget),'effect_identifiability_fit':types.SimpleNamespace(Guard=Guard)}
            with patch.object(V.importlib,'import_module',side_effect=lambda n:modules[n]),patch.object(V,'paths',return_value=[]),patch.object(V,'verify',side_effect=verify),patch.dict(sys.modules,{'numpy':types.ModuleType('numpy')}):
                try:V.execute(types.SimpleNamespace(spec=Path(temp)/'spec',out=out))
                except ValueError:pass
            return json.loads((out/'result.json').read_text()),run.finished

    def test_scientific_mismatch_is_preserved_before_error(self):
        result,status=self.execute_toy(lambda *_:dict(status='FAIL',mismatches=['toy wrong label']))
        self.assertEqual(result['mismatches'],['toy wrong label']);self.assertEqual(status,'failed')

    def test_fatal_saved_input_error_also_preserved(self):
        def fail(*_):raise ValueError('toy bad shape')
        result,status=self.execute_toy(fail);self.assertEqual(result['status'],'FAIL');self.assertEqual(result['error']['message'],'toy bad shape');self.assertEqual(status,'failed')


if __name__=='__main__':unittest.main()
