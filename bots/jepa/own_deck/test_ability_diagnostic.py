"""Standard-library synthetic tests only: no array/model/scientific imports."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import ability_diagnostic as D


def documents():
    return [dict(printed=dict(hp=4),abilities=dict(card=[dict(trigger='event',targetResolver=dict(owner='opponent',mode='upTo',count=dict(kind='const',value=2),predicate=dict(kind='binary',op='<=',left=dict(kind='ref',path=['card','cost']),right=dict(kind='const',value=3))),effect=dict(kind='defeat',target='chosen'))],unit=[],leader=[])),
            dict(printed=dict(hp=6),abilities=dict(card=[dict(trigger='whenPlayed',targetResolver=dict(owner='any'),effect=dict(kind='heal',target='chosen',amount=dict(kind='const',value=3)))],unit=[],leader=[])),
            dict(printed=dict(hp=3),abilities=dict(card=[dict(trigger='whenPlayed',effect=dict(kind='select',targetResolver=dict(owner='opponent'),effect=dict(kind='damage',amount=dict(kind='const',value=1),target='chosen')))],unit=[],leader=[]))]


def public_fixture():
    sc={k:dict(center=[2.]*n,scale=[2.]*n)for k,n in(('context_features',32),('candidate_features',43))}
    norm=lambda v:(v-2)/2
    x=[[norm(0.)for _ in range(32)]for _ in range(33)];c=[[[norm(0.)for _ in range(43)]for _ in range(8)]for _ in range(33)];selected=[]
    for i in range(33):
        target=3+(i%2)if i<32 else 3;selected.append(target)
        for h,v in((10,4),(11,6),(14,1),(15,1)):x[i][h]=norm(v)
        for j in range(8):
            c[i][j][26]=norm(2 if j%2 else 3);c[i][j][27]=norm(1);c[i][j][41]=norm(int(j==target));c[i][j][42]=norm(1)
    return x,c,selected,sc


class Tests(unittest.TestCase):
    def test_fixed_exposure_no_training(self):
        result=D.describe();self.assertEqual(len(result['panels']),11);self.assertEqual(len(D.SEEDS)*len(D.PANELS),33)
        self.assertEqual(D.CONFIG['neural_forwards'],33);self.assertEqual(D.CONFIG['seconds'],15.)
        for k in('optimizer_updates','backwards','native_applies','numerical_fits','export_forwards','paid_jobs'):self.assertEqual(D.CONFIG[k],0)

    def test_describe_is_stdlib_only_in_fresh_interpreter(self):
        code="import ability_diagnostic as d,sys; d.describe(); assert not({'numpy','torch','effect_identifiability_fit','semantic_discrimination_bank'} & set(sys.modules))"
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(D.__file__).parent,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_exact_ir_fields_only_predeclared_source(self):
        original=documents();codes=['IBH_104','ASH_081','ASH_071']
        for panel in D.IR_PANELS:
            changed,audit=D.mutate_documents(original,panel,codes);target=codes.index(D.MUTATION_TARGETS[panel]);self.assertEqual(len(audit),1)
            self.assertEqual(original,documents());self.assertEqual(changed[target]['printed'],original[target]['printed'])
            for i in range(3):
                if i!=target:self.assertEqual(changed[i],original[i])
        out,_=D.mutate_documents(original,'cost-cap3-to2',codes)
        resolver=out[0]['abilities']['card'][0]['targetResolver'];self.assertEqual(resolver['predicate']['right']['value'],2);self.assertEqual(resolver['count']['value'],2)
        out,_=D.mutate_documents(original,'upTo-count2-to1',codes)
        self.assertEqual(out[0]['abilities']['card'][0]['targetResolver']['count']['value'],1)

    def test_mutation_never_silently_extends_schema_or_empty_target(self):
        with self.assertRaisesRegex(ValueError,'predeclared'):D.mutate_documents(documents(),'cost-cap3-to2',['OTHER','ASH_081','ASH_071'])
        docs=documents();docs[0]['abilities']['card'][0]['targetResolver']['predicate']['right']['value']=7
        with self.assertRaisesRegex(ValueError,'changed no'):D.mutate_documents(docs,'cost-cap3-to2',['IBH_104','ASH_081','ASH_071'])

    def test_source_stat_neutral_is_one_known_coordinate_only(self):
        x,c,s,sc=public_fixture();x[1][15]=(0-2)/2
        xx,cc,ss,changes=D.public_probe('source-hp-neutral',x,c,s,sc)
        self.assertEqual(xx[0][11],0.);self.assertEqual(xx[1],x[1]);self.assertEqual(cc,c);self.assertEqual(ss,s)
        for i in range(33):self.assertEqual(xx[i][:11]+xx[i][12:],x[i][:11]+x[i][12:])
        self.assertNotIn([1,11],changes)

    def test_cost_flip_known_nonsource_only_and_no_flag_change(self):
        x,c,s,sc=public_fixture();c[0][2][27]=-1.
        xx,cc,ss,_=D.public_probe('candidate-cost2-swap3',x,c,s,sc)
        self.assertEqual(xx,x);self.assertEqual(ss,s);self.assertEqual(cc[0][0],c[0][0]);self.assertEqual(cc[0][2],c[0][2])
        self.assertEqual(cc[0][1][26],.5)
        for i in range(33):
            for j in range(8):self.assertEqual(cc[i][j][:26]+cc[i][j][27:],c[i][j][:26]+c[i][j][27:])

    def test_coherent_relation_swap_and_auxiliary_unchanged(self):
        x,c,s,sc=public_fixture();xx,cc,ss,changes=D.public_probe('coherent-intent-swap',x,c,s,sc)
        self.assertEqual(len(changes),32);self.assertEqual((xx[32],cc[32],ss[32]),(x[32],c[32],s[32]))
        for i in range(32):self.assertEqual((xx[i],cc[i],ss[i]),(x[i^1],c[i^1],s[i^1]))

    def test_normalized_relation_zero_is_not_raw_false_or_new_selection(self):
        x,c,s,sc=public_fixture();xx,cc,ss,_=D.public_probe('intent-neutral',x,c,s,sc)
        self.assertEqual(xx,x);self.assertEqual(ss,s)
        self.assertEqual(cc[0][3][41:],[0.,0.]);self.assertNotEqual(cc[0][3][41],(0.-2)/2)
        for i in range(33):
            for j in range(8):self.assertEqual(cc[i][j][:41],c[i][j][:41])

    def test_reference_metrics_respect_native_and_analytical_knownness(self):
        reference=[dict(observations={'anchor_a':dict(values=[1.,0.,-1.,0.,0.,0.,0.],mask=[1,0,1,0,0,0,0])})]
        arrays=dict(source_cards=['X'],targets=[[[1.,1.,-3.,0.,0.,0.,0.]]],target_mask=[[[1,1,1,0,0,0,0]]])
        manifest=dict(target_names=['target_allowed','target_removed','target_damage_delta','x3','x4','x5','x6'],binary_heads=['target_allowed','target_removed'],candidate_order=['anchor_a'])
        r=D.reference_score(reference,arrays,manifest,dict(root_partitions=dict(train=[0])))['cells']['train']['X']
        self.assertEqual(r['target_allowed']['classification_accuracy'],1.);self.assertEqual(r['target_damage_delta']['root_balanced_mae'],2.)
        self.assertEqual(r['target_removed']['coobserved'],0);self.assertIsNone(r['target_removed']['coordinate_mae'])

    def test_intent_invariance_reports_flip_and_rejects_label_contradiction(self):
        predictions=[[[.9 if i%2==0 else .1]]for i in range(33)];native=[[[1.]]for _ in range(33)];mask=[[[1.]]for _ in range(33)]
        result=D.intent_pair_stats(predictions,native,mask,['X']*33,['anchor_a'])['groups'][0]
        self.assertEqual(result['pairs'],16);self.assertEqual(result['classification_flip_rate'],1.);self.assertAlmostEqual(result['max_abs_intent_difference'],.8)
        native[1][0][0]=0
        with self.assertRaisesRegex(ValueError,'eligibility changes'):D.intent_pair_stats(predictions,native,mask,['X']*33,['anchor_a'])

    def test_durable_budget_precedes_science_and_every_forward_has_pair(self):
        source=Path(D.__file__).read_text();tree=ast.parse(source)
        self.assertIn("run.begin('diagnose'",source);self.assertIn('run.remaining_seconds()',source)
        execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute')
        begins=[n for n in ast.walk(execute)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='begin']
        self.assertEqual(len(begins),1);self.assertNotIn('pin(plan_path)',ast.get_source_segment(source,begins[0]))
        self.assertLess(source.index('with E.Guard('),source.index('import numpy as np'))
        self.assertLess(source.index("run.intent('neural_forwards')"),source.index('with torch.inference_mode():'))
        self.assertIn('run.complete(token)',source);self.assertIn('semantic_discrimination_fit_v2',source)
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom))and any(a.name in('torch','numpy')for a in n.names)for n in tree.body))


if __name__=='__main__':unittest.main()
