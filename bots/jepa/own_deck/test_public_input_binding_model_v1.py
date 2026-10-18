"""Pure synthetic input/contract checks; no Torch, model construction or forward."""
import copy
import unittest

import numpy as np

import public_input_binding_model_v1 as M


def fixture():
    rows={code:dict(card=dict(aspects=aspects)) for code,aspects in
          [('SRC',['heroism']),('HELPER',['vigilance']),('ENEMY',['aggression']),('HOST',['command'])]}
    def p(identity,code,owner,zone):
        return dict(id=identity,code=code,owner=owner,zone=zone,is_unit=True,present=True,
                    known=dict(identity=True,owner=True))
    projections=dict(source=p('s','SRC','p1','hand'),helper=p('u','HELPER','p1','ground'),
        enemy=p('e','ENEMY','p2','space'),host_a=p('a','HOST','p1','ground'),host_b=p('b','HOST','p1','ground'))
    refs={role:value['id'] for role,value in projections.items()}
    before=dict(projections=projections,state=dict(players=dict(
        p1=dict(ground=[{'id':'u'},{'id':'a'},{'id':'b'}],space=[],hand=['s'],deck=[]),
        p2=dict(ground=[],space=[{'id':'e'}],hand=[],deck=[]))))
    record=dict(before=before,refs=refs,declared_intent=dict(ref='host_a',id='a',requires_target=True),observation_refs=['host_a','host_b'])
    order=list(projections)
    arrays=dict(context_features=np.arange(18,dtype=np.float32)[None,:],
        candidate_features=np.tile(np.arange(34,dtype=np.float32),(1,len(order),1)))
    manifest=dict(public_binding_contract=dict(schema=M.SCHEMA,task='actual-intent-endpoints',
        aspect_vocabulary=list(M.ASPECTS),metadata_mode='printed-static-fixture-only'),
        public_before_records=[record],public_catalog_rows=rows,candidate_order=order)
    return arrays,manifest


def identity_scalers():
    return {key:dict(center=[0.]*width,scale=[1.]*width) for key,width in
            [('context_features',32),('candidate_features',43)]}


class PublicBindingInputTests(unittest.TestCase):
    def test_final_abi_and_pure_parameter_formula(self):
        self.assertEqual((M.CONTEXT_WIDTH,M.CANDIDATE_WIDTH),(32,43))
        spec=M.contract();self.assertEqual(spec['extra_input_parameters'],368)
        symbols=dict(path=['PAD','key:a'],value=['PAD','enum:b'],type=list(range(7)))
        counts=M.parameter_counts(symbols,4)
        old_allocated=9200+16*5+16*4
        self.assertEqual(counts['allocated'],old_allocated+368)
        self.assertEqual(counts['trainable']['rich-typed'],counts['allocated']-counts['identity'])
        self.assertIn('No added Jedi',spec['unaddressed'])

    def test_prefix_and_named_owner_counts_are_exact(self):
        arrays,manifest=fixture();x,c=M.project_arrays(arrays,manifest)
        np.testing.assert_array_equal(x[:,:18],arrays['context_features'])
        np.testing.assert_array_equal(c[:,:,:34],arrays['candidate_features'])
        self.assertEqual((x.shape,c.shape),((1,32),(1,5,43)))
        own=dict(zip(M.CONTEXT_EXTENSION,x[0,18:]));self.assertEqual(own['self_aspect_count_vigilance'],1)
        self.assertEqual(own['self_aspect_count_command'],2);self.assertEqual(own['opponent_aspect_count_aggression'],1)
        self.assertEqual(own['self_aspect_count_heroism'],0)  # own hand source is NOT prospectively inserted

    def test_factorial_masks_after_shared_nonzero_normalization(self):
        arrays,manifest=fixture();scalers=identity_scalers()
        for key in scalers:scalers[key]['center']=[.25]*len(scalers[key]['center'])
        full=M.project_arrays(arrays,manifest,scalers=scalers)
        for arm in M.ARMS:
            x,c=M.project_arrays(arrays,manifest,arm,scalers)
            np.testing.assert_array_equal(x[:,:18],full[0][:,:18]);np.testing.assert_array_equal(c[:,:,:34],full[1][:,:,:34])
            if arm[1]=='0':self.assertFalse(x[:,18:].any());self.assertFalse(c[:,:,34:41].any())
            else:np.testing.assert_array_equal(x,full[0]);np.testing.assert_array_equal(c[:,:,34:41],full[1][:,:,34:41])
            if arm[3]=='0':self.assertFalse(c[:,:,41:].any())
            else:np.testing.assert_array_equal(c[:,:,41:],full[1][:,:,41:])
        with self.assertRaises(ValueError):M.project_arrays(arrays,manifest,'C0R0')

    def test_public_aspect_flip_changes_only_content_owner_block(self):
        arrays,manifest=fixture();changed=copy.deepcopy(manifest)
        changed['public_catalog_rows']['HELPER']['card']['aspects']=['cunning']
        x,c=M.project_arrays(arrays,manifest);y,d=M.project_arrays(arrays,changed)
        self.assertFalse(np.array_equal(x[:,18:25],y[:,18:25]));np.testing.assert_array_equal(x[:,25:],y[:,25:])
        for arm in ('C0R0','C0R1'):
            a=M.mask_scaled_inputs(x,c,arm);b=M.mask_scaled_inputs(y,d,arm)
            np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1])

    def test_predeclared_host_swap_is_a_relation_only_contrast(self):
        arrays,manifest=fixture();changed=copy.deepcopy(manifest)
        changed['public_before_records'][0]['declared_intent']=dict(ref='host_b',id='b',requires_target=True)
        x,c=M.project_arrays(arrays,manifest);y,d=M.project_arrays(arrays,changed)
        np.testing.assert_array_equal(x,y);np.testing.assert_array_equal(c[:,:,:41],d[:,:,:41])
        self.assertEqual(c[0,3,41],1);self.assertEqual(d[0,3,41],0)
        for arm in ('C0R0','C1R0'):
            a=M.mask_scaled_inputs(x,c,arm);b=M.mask_scaled_inputs(y,d,arm)
            np.testing.assert_array_equal(a[1],b[1])
        hashes=M.consumed_input_hashes(x,c,['typed-tensor-signature'],np.asarray([3],np.int64))
        swapped=M.consumed_input_hashes(y,d,['typed-tensor-signature'],np.asarray([4],np.int64))
        self.assertNotEqual(hashes[0]['candidate'][3],swapped[0]['candidate'][3])

    def test_registration_order_identity_renaming_and_reprint_alias_invariance(self):
        arrays,manifest=fixture();changed=copy.deepcopy(manifest);r=changed['public_before_records'][0]
        rename={old:'renamed-'+old for old in r['refs'].values()}
        for p in r['before']['projections'].values():p['id']=rename[p['id']]
        r['before']['projections']=dict(reversed(list(r['before']['projections'].items())))
        r['refs']={key:rename[value] for key,value in r['refs'].items()};r['declared_intent']['id']=rename['a']
        for player in r['before']['state']['players'].values():
            for zone in ('ground','space'):
                player[zone]=[dict(id=rename[p['id']]) for p in reversed(player[zone])]
        changed['public_catalog_rows']['ALIAS']=changed['public_catalog_rows'].pop('HELPER')
        r['before']['projections']['helper']['code']='ALIAS'
        for a,b in zip(M.project_arrays(arrays,manifest),M.project_arrays(arrays,changed)):np.testing.assert_array_equal(a,b)

    def test_duplicate_physical_projection_does_not_duplicate_count(self):
        arrays,manifest=fixture();changed=copy.deepcopy(manifest);r=changed['public_before_records'][0]
        r['before']['projections']['alias']=copy.deepcopy(r['before']['projections']['helper']);r['refs']['alias']='u'
        np.testing.assert_array_equal(M.project_arrays(arrays,manifest)[0],M.project_arrays(arrays,changed)[0])
        r['before']['projections']['alias']['owner']='p2'
        with self.assertRaises(ValueError):M.project_arrays(arrays,changed)

    def test_unknown_metadata_or_partial_arena_never_becomes_known_zero(self):
        arrays,manifest=fixture();unknown=copy.deepcopy(manifest);del unknown['public_catalog_rows']['HELPER']
        x,c=M.project_arrays(arrays,unknown)
        self.assertEqual(x[0,24],0);self.assertFalse(x[0,18:24].any());self.assertEqual(x[0,31],1)
        self.assertEqual(c[0,1,40],0);self.assertFalse(c[0,1,34:40].any())
        partial=copy.deepcopy(manifest);partial['public_before_records'][0]['before']['state']['players']['p2']['ground']=[dict(id='unprojected-public-unit')]
        x,_=M.project_arrays(arrays,partial);self.assertFalse(x[0,18:].any())
        dynamic=copy.deepcopy(manifest);dynamic['public_before_records'][0]['before']['projections']['helper']['dynamic_aspects']=True
        self.assertEqual(M.project_arrays(arrays,dynamic)[0][0,24],0)
        invalid=copy.deepcopy(manifest);invalid['public_catalog_rows']['HELPER']['card']['aspects']=['unrecognized-aspect']
        self.assertEqual(M.project_arrays(arrays,invalid)[0][0,24],0)
        stale=copy.deepcopy(manifest);stale['public_before_records'][0]['before']['projections']['helper']['known']['printed_aspects']=False
        self.assertEqual(M.project_arrays(arrays,stale)[0][0,24],0)

    def test_private_future_and_label_fields_cannot_supply_features(self):
        arrays,manifest=fixture();poisoned=copy.deepcopy(manifest)
        poisoned['public_before_records'][0]['before']['state']['players']['p2'].update(hand=['hidden-opponent-card'],deck=['hidden-next-card'])
        labels=copy.deepcopy(arrays);labels['targets']=np.full((1,5,7),9999,np.float32)
        for a,b in zip(M.project_arrays(arrays,manifest),M.project_arrays(labels,poisoned)):np.testing.assert_array_equal(a,b)
        bad=copy.deepcopy(manifest);bad['public_before_records'][0]['after']={'parent':'label'}
        with self.assertRaises(ValueError):M.project_arrays(arrays,bad)
        bad=copy.deepcopy(manifest);bad['public_before_records'][0]['before']['projections']['enemy']['zone']='hand'
        with self.assertRaises(ValueError):M.project_arrays(arrays,bad)

    def test_unknown_intent_does_not_mean_known_nonmatch(self):
        arrays,manifest=fixture();manifest['public_before_records'][0]['declared_intent']={}
        _,c=M.project_arrays(arrays,manifest);self.assertFalse(c[:,:,41:].any())
        for value in (1,None,'true'):
            manifest['public_before_records'][0]['declared_intent']=dict(ref='host_a',id='a',requires_target=value)
            with self.assertRaises(ValueError):M.project_arrays(arrays,manifest)

    def test_explicit_passive_no_target_is_neutral_na_without_source_fallback(self):
        arrays,manifest=fixture();manifest['public_before_records'][0]['declared_intent']=dict(kind='passive',ref='source',id='s',requires_target=False)
        _,c=M.project_arrays(arrays,manifest);self.assertFalse(c[:,:,41:].any())
        self.assertIn('N/A [0,0]',M.contract()['relation_status'])

    def test_known_empty_opponent_is_distinct_from_missing_public_arena(self):
        arrays,manifest=fixture();r=manifest['public_before_records'][0]
        r['before']['projections']['enemy']=None;r['refs']['enemy']=None;r['before']['state']['players']['p2']['space']=[]
        x,_=M.project_arrays(arrays,manifest)
        self.assertFalse(x[0,25:31].any());self.assertEqual(x[0,31],1)
        del r['before']['state']['players']['p2']['ground']
        x,_=M.project_arrays(arrays,manifest);self.assertFalse(x[0,18:].any())

    def test_contract_dtype_scale_and_hash_bounds_are_strict(self):
        arrays,manifest=fixture();bad=copy.deepcopy(manifest);bad['public_binding_contract']['task']='mixed'
        with self.assertRaises(ValueError):M.project_arrays(arrays,bad)
        bad=copy.deepcopy(arrays);bad['context_features']=bad['context_features'].astype(np.float64)
        with self.assertRaises(ValueError):M.project_arrays(bad,manifest)
        scale=identity_scalers();scale['context_features']['scale'][0]=0
        with self.assertRaises(ValueError):M.project_arrays(arrays,manifest,scalers=scale)
        x,c=M.project_arrays(arrays,manifest)
        with self.assertRaises(ValueError):M.consumed_input_hashes(x,c,['sig'],np.asarray([99],np.int64))


if __name__=='__main__':unittest.main()
