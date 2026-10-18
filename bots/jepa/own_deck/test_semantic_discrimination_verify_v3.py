"""Synthetic-only independent verifier tests; no actual campaign or model."""
import ast
import copy
from pathlib import Path
import unittest

import numpy as np
import semantic_discrimination_verify_v3 as V


def scores(value):
    return {str(s): {g: dict(mae=value) for g in V.HELD} for s in V.SEEDS}


def native_fixture(mode='committed', up_to=False, removed=False):
    from test_semantic_discrimination_data import fixture
    import semantic_discrimination_data as D
    case, world, _, rows = fixture(mode,up_to,removed)
    labels = D.derive_labels(case,world,{},rows)
    cases, worlds = [], []
    for i in range(33):
        c,w = copy.deepcopy(case),copy.deepcopy(world); c['world_id']=w['id']=i
        cases.append(c); worlds.append(w)
    arrays = {k:np.repeat(labels[key][None],33,axis=0) for k,key in (
        ('source_targets','source'),('source_mask','source_mask'),('targets','targets'),('target_mask','target_mask'),('chosen_only_target_mask','chosen_only_target_mask'))}
    arrays.update(source_cards=np.asarray([case['card']]*33),selected_candidate_indices=np.asarray([labels['selected']]*33))
    records = [V.public_before_allowlist(c) for c in cases]
    manifest = dict(candidate_order=list(D.ROLES),plan=dict(worlds=worlds),public_before_records=records,
        native_status=[dict(committed=labels['committed'],terminal=labels['terminal']) for _ in cases],
        terminal_counts={labels['terminal']:33},native_apply_calls=sum(c['applyCalls'] for c in cases))
    raw = dict(cases=cases,collectionComplete=True,applyCalls=manifest['native_apply_calls'])
    return arrays,manifest,raw


class DecisionTests(unittest.TestCase):
    def test_versioned_copy_preserves_scoring_and_gate_functions(self):
        import semantic_discrimination_verify_v2 as original
        self.assertEqual(V.PREDECESSOR_VERIFIER_SHA,V.pin(original.__file__)['sha256'])
        old=ast.parse(Path(original.__file__).read_text());new=ast.parse(Path(V.__file__).read_text())
        old_functions={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)}
        new_functions={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
        amended={'run','main','verify_saved','native_labels','legacy_public'}
        for name,node in old_functions.items():
            if name in amended:continue
            self.assertEqual(ast.dump(node,include_attributes=False),ast.dump(new_functions[name],include_attributes=False),name)
        source=ast.get_source_segment(Path(original.__file__).read_text(),old_functions['verify_saved'])
        source=source.replace("native = native_labels(np,checks,read(manifest['native_receipt']['path']),arrays,manifest)","raw = read(manifest['native_receipt']['path'])\n    native = native_labels(np,checks,raw,arrays,manifest)").replace('legacy_public(np, arrays, manifest)','legacy_public(np, arrays, manifest, raw)')
        class StripProvenance(ast.NodeTransformer):
            def visit_Call(self,node):
                self.generic_visit(node);node.keywords=[k for k in node.keywords if k.arg!='supplemental_provenance'];return node
        expected=ast.parse(source).body[0];actual=StripProvenance().visit(copy.deepcopy(new_functions['verify_saved']))
        self.assertEqual(ast.dump(expected,include_attributes=False),ast.dump(actual,include_attributes=False))

    def test_closed_old_entrypoint_cannot_be_reused(self):
        with self.assertRaisesRegex(RuntimeError,'never reopen'):V.run(None)

    def test_group_seed_control_gate_and_zero_denominator(self):
        c=scores(.5); controls={name:scores(1.) for name in ('frozen-full','printed-only','ID-only','public-only','zero','train_mean','public_ridge')}
        self.assertTrue(V.primary_decision(c,controls)['supported'])
        controls['zero']['29']['ASH_081']['mae']=.4
        self.assertFalse(V.primary_decision(c,controls)['supported'])
        self.assertFalse(V.primary_decision(scores(.95),{'printed-only':scores(1.)})['supported'])
        zero=V.primary_decision(scores(0.),{'zero':scores(0.)})
        self.assertIsNone(zero['comparisons'][0]['pooled_relative_reduction']);self.assertFalse(zero['supported'])

    def test_wrong_ir_separate_every_seed_and_relative_support(self):
        self.assertTrue(V.swap_decision(scores(.5),scores(1.))['supported'])
        self.assertFalse(V.swap_decision(scores(.5),scores(.52))['supported'])
        bad=scores(1.);bad['43']['IBH_104']['mae']=.5
        self.assertFalse(V.swap_decision(scores(.5),bad)['supported'])
        self.assertIsNone(V.swap_decision(scores(0.),scores(1.))['groups']['ASH_081']['pooled_relative_worsening'])

    def test_root_balancing_and_unknown_coordinates(self):
        value=V.H.head_metrics(np,np.asarray([[3.,999,999],[1,1,1]]),np.zeros((2,3)),np.asarray([[1,0,0],[1,1,1]]),np.arange(2),dict(binary=False,scale=2.))
        self.assertEqual(2.,value['mae']);self.assertEqual(1.,value['train_scaled_mae'])
        self.assertEqual(4,value['known_coordinates'])

    def test_four_d_pairs_are_two_nested_scenarios(self):
        order=['source','h','other','anchor_a','anchor_b','x','base','base2'];y=np.zeros((8,8,7),np.float32)
        pairs=[];codes=[]
        for i in range(4):
            codes.extend(['IBH_104','LOF_077']);left,right=2*i,2*i+1
            y[left,3 if i>=2 else 4,0]=1;y[right,4 if i>=2 else 3,0]=1
            pairs.append(dict(id=str(i),left_root=left,right_root=right,expected_D=-2. if i<2 else 2.))
        arrays=dict(source_cards=np.asarray(codes),targets=y,target_mask=np.ones_like(y))
        result=V.paired(np,y,arrays,dict(candidate_order=order,target_names=['target_allowed']+list('abcdef')),dict(primary_pairs=pairs))
        self.assertTrue(result['both_directions_correct']);self.assertEqual(4,len(result['pairs']))
        wrong=y.copy();wrong[0,:,0]=0;wrong[1,:,0]=0
        self.assertFalse(V.paired(np,wrong,arrays,dict(candidate_order=order,target_names=['target_allowed']+list('abcdef')),dict(primary_pairs=pairs))['both_directions_correct'])

    def test_actual_rank_requires_committed_complete_nontie(self):
        order=['source','h','other','anchor_a','anchor_b','x','base','base2'];y=np.zeros((2,8,7),np.float32);y[0,3,2]=-3;y[1,4,2]=-1
        arrays=dict(source_cards=np.asarray(['ASH_081']*2),targets=y,target_mask=np.ones_like(y))
        manifest=dict(candidate_order=order,target_names=['allowed','removed','target_damage_delta']+list('abcd'),native_status=[dict(committed=True,terminal='settled-committed')]*2)
        plan=dict(primary_spec=dict(rank_pairs=[dict(left_root=0,right_root=1)]))
        self.assertTrue(V.action_rank(np,y,arrays,manifest,plan)['supported'])
        manifest['native_status'][1]=dict(committed=False,terminal='unoffered-prompt-only')
        self.assertIsNone(V.action_rank(np,y,arrays,manifest,plan)['accuracy'])


class DataTests(unittest.TestCase):
    def test_native_labels_signed_healing_and_departure(self):
        for removed in (False,True):
            arrays,manifest,raw=native_fixture(removed=removed);checks=V.H.Checks()
            result=V.native_labels(np,checks,raw,arrays,manifest)
            self.assertFalse(checks.mismatches);self.assertEqual(33,result['roots'])
            self.assertEqual(-3.,arrays['targets'][0,6,2])
            if removed:self.assertFalse(arrays['target_mask'][0,3,2:].any())

    def test_prompt_only_and_cancel_never_fabricate_future(self):
        for mode in ('prompt-only','cancelled'):
            arrays,manifest,raw=native_fixture(mode);checks=V.H.Checks();V.native_labels(np,checks,raw,arrays,manifest)
            self.assertFalse(checks.mismatches);self.assertFalse(arrays['target_mask'][:,:,1:].any())
            arrays['target_mask'][0,3,2]=1;checks=V.H.Checks();V.native_labels(np,checks,raw,arrays,manifest)
            self.assertTrue(checks.mismatches)

    def test_upTo_done_requires_single_intended_selection(self):
        arrays,manifest,raw=native_fixture(up_to=True);checks=V.H.Checks();V.native_labels(np,checks,raw,arrays,manifest)
        self.assertFalse(checks.mismatches)
        raw['cases'][0]['selectionWitness']['abilitySelection'].append('b')
        with self.assertRaisesRegex(ValueError,'exactly one'):V.native_labels(np,V.H.Checks(),raw,arrays,manifest)

    def test_independent_banks_mask_positions_holdout_and_shared_scale(self):
        import semantic_discrimination_bank as B
        from test_semantic_discrimination_bank import documents
        docs=documents()*2
        for i,d in enumerate(docs):d['abilities']['card'][0]['effect']['amount']['value']=i+1
        codes=['TST_'+str(i) for i in range(8)];train=codes[:6];symbols=B.frontend().symbols_for(docs);donors=B.fixed_donors(codes,train)
        banks=B.make_banks(docs,codes,train,symbols,donors);restricted=B.make_banks(docs,codes,train,symbols,donors,True)
        numbers=[v for d in docs[:6] for _,k,v in V.typed_tokens(d) if k in ('number','length')]
        plan=dict(codes=codes,train_codes=train,documents=docs,printed_documents=[dict(printed=d['printed']) for d in docs],swapped_documents=B.swapped_documents(docs,codes,train,donors),vocabularies=symbols,numeric_scale=max(1.,float(np.std(numbers))))
        saved={f+'_'+k:v for f,b in banks.items() for k,v in b.items()};saved.update({'restricted_'+f+'_'+k:v for f,b in restricted.items() for k,v in b.items()})
        checks=V.H.Checks();signatures=V.check_banks(np,checks,plan,saved);self.assertFalse(checks.mismatches)
        self.assertEqual(signatures['printed'],signatures['swapped_printed'])
        saved['restricted_full_slot_mask'][6]=1;checks=V.H.Checks();V.check_banks(np,checks,plan,saved);self.assertTrue(checks.mismatches)

    def test_public_projection_33_roots_before_only(self):
        from test_binding_transfer_report_verify import public_fixture
        arrays,manifest=public_fixture();arrays={k:np.concatenate((v,v[:7])) for k,v in arrays.items()};manifest['public_before_records']+=copy.deepcopy(manifest['public_before_records'][:7])
        arrays['source_cards']=np.asarray(['TEST']*33)
        x,c=V.public_projection(np,arrays,manifest);self.assertEqual((33,32),x.shape);self.assertEqual((33,8,43),c.shape)
        self.assertEqual(2.,x[0,19]);self.assertEqual(1.,c[0,1,41]);self.assertEqual(0.,x[0,22])
        manifest['public_before_records'][0]['after']=dict(label=1)
        with self.assertRaises(ValueError):V.public_projection(np,arrays,manifest)

    def test_helper_is_readonly_and_imports_no_scientific_library(self):
        source=Path(V.__file__).read_text();tree=ast.parse(source)
        fn=ast.get_source_segment(source,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_saved'))
        self.assertNotIn('.start(',fn);self.assertNotIn('.finish(',fn);self.assertNotIn('.lease(',fn)
        self.assertNotIn('write_new(',fn)
        self.assertIn('public-ridge-75-columns',source);self.assertNotIn('public-ridge-held-IDs',source)
        imports=[a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names]
        self.assertFalse(set(imports)&{'numpy','torch','scipy','sklearn'})

    def test_allowlist_strips_menus_private_future_and_physical_counter_fields(self):
        from test_semantic_discrimination_data import fixture
        import binding_transfer_data_v2 as D
        case,_,_,_=fixture();record=V.public_before_allowlist(case)
        self.assertEqual(record,D.public_before_record(case))
        self.assertEqual({'projections','state'},set(record['before']))
        self.assertEqual({'identity','owner','printed_aspects'},set(record['before']['projections']['source']['known']))
        poison=copy.deepcopy(case);poison['before']['offeredActions']=[dict(secret='menu')]
        poison['before']['state']['players']['p2']['hand']=[dict(secret='opponent-private')]
        poison['before']['state']['players']['p1']['deck']=[dict(secret='draw-order')]
        poison['before']['projections']['source']['hp']=999;poison['future']=dict(label=999)
        self.assertEqual(record,V.public_before_allowlist(poison))
        arrays,manifest,raw=native_fixture();manifest['public_before_records'][0]['before']['offeredActions']=[]
        with self.assertRaisesRegex(ValueError,'allowlisted'):V.native_labels(np,V.H.Checks(),raw,arrays,manifest)

    def test_legacy_features_use_raw_before_and_cr_uses_stripped_record(self):
        from test_semantic_discrimination_data import fixture
        import binding_transfer_data_v2 as D
        case,_,_,rows=fixture();source=case['before']['projections']['source']
        source.update(power=4,hp=5);source['known'].update(power=False,hp=False)
        record=V.public_before_allowlist(case)
        manifest=dict(candidate_order=list(D.ROLES),public_before_records=[record],public_catalog_rows=rows)
        x,c=V.legacy_public(np,{},manifest,dict(cases=[case]))
        self.assertEqual((1,18),x.shape);self.assertEqual((1,8,34),c.shape)
        self.assertEqual([4.,5.,0.,0.],x[0,10:14].tolist());self.assertEqual([0.,0.,0.,0.],x[0,14:18].tolist())
        np.testing.assert_array_equal(x[0],D.V.legacy_context(case['before'],rows))
        for j,role in enumerate(D.ROLES):np.testing.assert_array_equal(c[0,j],D.V.legacy_candidate(case['before']['projections'][role],case['refs']['source'],rows))
        arrays=dict(context_features=x,candidate_features=c,source_cards=np.asarray([case['card']]))
        cx,cc=V.public_projection(np,arrays,manifest)
        self.assertEqual((1,32),cx.shape);self.assertEqual((1,8,43),cc.shape)
        self.assertNotIn('resources',record['before']['state']['players']['p1'])



if __name__=='__main__':unittest.main()
