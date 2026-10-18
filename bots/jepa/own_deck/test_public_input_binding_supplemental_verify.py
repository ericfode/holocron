"""Synthetic-only verifier tests; no native/model execution or actual receipts."""
import copy
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('public_binding_verify',Path(__file__).with_name('public_input_binding_supplemental_verify.py'))
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)


def row(aspects=None):
    return dict(card=dict(cost=3,hp=8,power=2,unique=False,upgradePower=None,upgradeHp=None,aspects=aspects or [],traits=[],arena='ground',keywords=[],types=['unit']),abilities=dict(card=[],unit=[],leader=[]),keywordValues={})


def projection(identity,code='C',owner='p1',zone='ground',damage=0):
    return dict(id=identity,code=code,owner=owner,zone=zone,present=True,in_arena=zone in('ground','space'),is_unit=True,is_base=False,damage=damage,hp=8,power=2,exhausted=False,shield_count=0,xp_count=0,known={f:True for f in V.NUMERIC})


def capture():
    cards=[dict(id='source',setCode='C',damage=0,hp=8,power=2,exhausted=False,upgrades=[]),dict(id='helper',setCode='H',damage=0,hp=8,power=2,exhausted=False,upgrades=[])]
    def player():return dict(deck=[],hand=[],ground=[],space=[],discard=[],resources=[],base=None,leader=None)
    p1,p2=player(),player();p1['hand']=[cards[0]];p1['ground']=[cards[1]]
    for role in('base','leader'):p1[role]=dict(id=role,setCode='B',damage=0,hp=30,upgrades=[])
    c=dict(state=dict(players=dict(p1=p1,p2=p2)),projections=dict(source=projection('source',zone='hand'),helper=projection('helper','H'),unused=None),settlement={k:0 for k in('ability_program','death_depth','death_pending','death_window','pending_programs','pending_triggers','after_attack_triggers','after_attack_programs')},decision='Window',abilityProgramPlusOne=0,terminal=False,settled=True)
    c['settlement'].update(decision='Window',event_group_active=False,support_pending=False)
    return c


class Tests(unittest.TestCase):
    def test_semantic_key_order_alpha_and_sequence_order(self):
        a=row();a['abilities']['card']=[dict(trigger='whenPlayed',effect=dict(kind='sequence',effects=[dict(kind='damage',amount=1),dict(kind='ready')]))]
        b=copy.deepcopy(a);b['abilities']['card'][0]['title']='UI only'
        self.assertEqual(V.source_program_hash(a),V.source_program_hash(b))
        b['abilities']['card'][0]['effect']['effects'].reverse()
        self.assertNotEqual(V.source_program_hash(a),V.source_program_hash(b))
        x=dict(kind='dataPath',root=['event'],argumentBinding=dict(id='callback:12:1',bindAt='callbackInvocation',readAt='expressionEvaluation'))
        a['abilities']['card'][0]['value']=x;b=copy.deepcopy(a);b['abilities']['card'][0]['value']['argumentBinding']['id']='callback:90:3'
        self.assertEqual(V.source_program_hash(a),V.source_program_hash(b))

    def test_legacy_omits_helper_aspect_while_corrected_public_binds_owner(self):
        c=capture();rows=dict(C=row(),H=row(['command']),B=row())
        x=V.legacy_context(c,rows);q=V.legacy_candidate(c['projections']['helper'],'source',rows)
        changed=copy.deepcopy(rows);changed['H']['card']['aspects']=['cunning']
        np.testing.assert_array_equal(x,V.legacy_context(c,changed));np.testing.assert_array_equal(q,V.legacy_candidate(c['projections']['helper'],'source',changed))
        self.assertNotEqual(V.digest(V.corrected_public_features(c,rows,'helper','helper')),V.digest(V.corrected_public_features(c,changed,'helper','helper')))
        c2=copy.deepcopy(c);unit=c2['state']['players']['p1']['ground'].pop();c2['state']['players']['p2']['ground'].append(unit);c2['projections']['helper']['owner']='p2'
        self.assertNotEqual(V.digest(V.corrected_public_features(c,rows,'helper','helper')),V.digest(V.corrected_public_features(c2,rows,'helper','helper')))

    def test_physical_identity_order_and_intent_relation(self):
        c=capture();rows=dict(C=row(),H=row(),B=row());base=V.digest(V.corrected_public_features(c,rows,'helper','helper'))
        renamed=copy.deepcopy(c)
        for p in renamed['state']['players'].values():
            for zone in('hand','ground','space','discard','resources'):
                for card in p[zone]:card['id']='renamed-'+card['id']
            for zone in('base','leader'):
                if p[zone]:p[zone]['id']='renamed-'+p[zone]['id']
        for p in renamed['projections'].values():
            if p:p['id']='renamed-'+p['id']
        self.assertEqual(base,V.digest(V.corrected_public_features(renamed,rows,'renamed-helper','renamed-helper')))
        self.assertNotEqual(base,V.digest(V.corrected_public_features(c,rows,'source','helper')))

    def test_observed_outcome_never_fills_unknown_or_removed_numeric(self):
        b=capture();a=copy.deepcopy(b);a['projections']['helper']['damage']=3
        self.assertEqual(V.observed_deltas(b,a,'helper')['target_damage_delta'],dict(known=True,value=3.))
        a['projections']['helper']['known']['damage']=False
        self.assertEqual(V.observed_deltas(b,a,'helper')['target_damage_delta'],dict(known=False,value=None))
        a['projections']['helper']['present']=False
        self.assertTrue(all(not v['known']and v['value']is None for v in V.observed_deltas(b,a,'helper').values()))

    def test_hash_collision_only_coobserved_same_head(self):
        records=[dict(case=str(i),ref='host',kind='expanded-branch',input_sha256='same',head='hp',known=k,value=v)for i,(k,v)in enumerate(((True,3),(False,8),(True,0)))]
        r=V.collision_records(records);self.assertEqual(len(r),1);self.assertEqual((r[0]['left_value'],r[0]['right_value']),(3,0))

    def test_privacy_and_settlement_fail_closed(self):
        c=capture();refs=dict(source='source',helper='helper',unused=None)
        self.assertTrue(V.validate_capture(c,refs))
        hidden=copy.deepcopy(c);hidden['state']['players']['p2']['hand']=[dict(id='secret')]
        with self.assertRaisesRegex(ValueError,'hidden'):V.validate_capture(hidden,refs)
        pending=copy.deepcopy(c);pending['settlement']['pending_programs']=1
        with self.assertRaisesRegex(ValueError,'settled'):V.validate_capture(pending,refs)
        duplicate=copy.deepcopy(c);duplicate['state']['players']['p2']['ground']=[copy.deepcopy(duplicate['state']['players']['p1']['ground'][0])]
        with self.assertRaisesRegex(ValueError,'duplicate'):V.validate_capture(duplicate,refs)

    def test_saved_prediction_contract_checks_independent_features_and_labels(self):
        before=capture();rows=dict(C=row(),H=row(),B=row());case=dict(card='C',before=before,refs=dict(source='source',helper='helper'),declared_intent=dict(ref='helper',id='helper'),observation_refs=['helper'])
        context=V.legacy_context(before,rows).tolist();candidate=V.legacy_candidate(before['projections']['helper'],'source',rows).tolist();program=V.semantic_document(rows['C'])
        feature=dict(relations=dict(candidate_is_intended_host_or_target=True,candidate_is_source=False),anchor_traits=[],anchor_aspects=[],own_arena_aspect_counts={a:0 for a in V.ASPECTS},opponent_arena_aspect_counts={a:0 for a in V.ASPECTS})
        projected=dict(program=program,legacy_context18=context,anchors=dict(helper=dict(legacy34=candidate,legacy_branch_hash=V.digest(dict(program=program,globals=context,candidate=candidate)),legacy_source_hash=V.digest(dict(program=program,globals=context,intended_candidate=candidate)),features=feature,repaired_hash=V.digest(dict(program=program,features=feature)))))
        native={h:dict(known=True,value=0.)for h in V.DELTA_HEADS};record=dict(legacy_context18=context,intended_legacy34=candidate,anchors=dict(helper=dict(legacy34=candidate,native=native)))
        predictions={control:dict(control=control,status='unknown'if control=='legacy-omission'else'known',observations=dict(helper=dict(values=[0.]*7,mask=[0]*7 if control=='legacy-omission'else[0,1,1,1,1,1,1],keywords_added={})),projector=copy.deepcopy(projected))for control in('bound','legacy-omission','same-info-unbound','wrong-owner')}
        result=V.compare_predictions(predictions,case,record,rows)
        self.assertEqual(result['bound']['target_hp_delta']['known'],1)
        self.assertEqual(result['legacy-omission']['target_hp_delta']['unknown'],1)
        bad=copy.deepcopy(predictions);bad['bound']['observations']['helper']['values'][6]=3
        with self.assertRaisesRegex(ValueError,'exact'):V.compare_predictions(bad,case,record,rows)
        bad=copy.deepcopy(predictions);bad['bound']['projector']['legacy_context18'][0]+=1
        with self.assertRaisesRegex(ValueError,'18 feature'):V.compare_predictions(bad,case,record,rows)

    def test_balanced_pair_error_floor_has_no_estimator_fit(self):
        def record(i,value):
            native={h:dict(known=True,value=float(value)if h=='target_damage_delta'else 0.)for h in V.DELTA_HEADS}
            return dict(world_id=i,anchors=dict(victim=dict(native=native,legacy_branch_hash='same',corrected_public_hash=str(i))))
        records=[record(0,3),record(1,5)]
        predictions={i:{c:dict(observations={})for c in('bound','same-info-unbound','wrong-owner')}for i in(0,1)}
        r=V.paired_results(dict(declared_pairs=[dict(kind='own-public-aspect-flip',worlds=[0,1])]),records,predictions)
        damage=next(x for x in r[0]['comparisons']if x['head']=='target_damage_delta')
        self.assertEqual(damage['balanced_pair_absolute_error_floor'],1.)

    def test_controls_are_known_and_exact_public_transformations(self):
        case=dict(card='C',cohort='own-aspect-condition',before=capture(),declared_intent=dict(ref='helper',id='helper'))
        rows=dict(C=row(),H=row(['command']),B=row())
        def pred(damage):return dict(status='known',observations=dict(helper=dict(mask=[0,1,1,1,1,1,1],values=[0.,0.,damage,0.,0.,0.,0.])))
        predictions=dict(bound=pred(5.),**{'wrong-owner':pred(3.),'same-info-unbound':pred(5.)})
        result=V.verify_control_transformations(case,rows,predictions)
        self.assertEqual(result['condition_scope'],dict(p1=True,p2=False))
        bad=copy.deepcopy(predictions);bad['wrong-owner']['observations']['helper']['values'][2]=5.
        with self.assertRaisesRegex(ValueError,'transformation'):V.verify_control_transformations(case,rows,bad)
        bad=copy.deepcopy(predictions);bad['wrong-owner']['status']='unknown'
        with self.assertRaisesRegex(ValueError,'known coverage'):V.verify_control_transformations(case,rows,bad)
        case['cohort']='attachment-parent-binding';rows['C']['card'].update(upgradePower=1,upgradeHp=3)
        for name in predictions:
            observations=predictions[name]['observations'];observations['helper']['values']=[0.,0.,0.,0.,0.,1.,3.]
            observations['other']=dict(mask=[0,1,1,1,1,1,1],values=[0.,0.,0.,0.,0.,1.,3.]if name=='same-info-unbound'else[0.]*7)
        V.verify_control_transformations(case,rows,predictions)

    def test_zone_specific_bare_hand_is_not_a_zero_default(self):
        c=capture();c['state']['players']['p1']['hand'][0]={k:v for k,v in c['state']['players']['p1']['hand'][0].items()if k in('id','setCode')}
        refs=dict(source='source',helper='helper',unused=None)
        self.assertTrue(V.validate_capture(c,refs))
        # Sparse hand refs alone do not justify physical zero. Only the frozen
        # fresh own-source constructor permits this explicit projection check.
        bad=copy.deepcopy(c);bad['projections']['source']['damage']=2
        with self.assertRaisesRegex(ValueError,'fresh source default'):V.validate_capture(bad,refs)
        bad=copy.deepcopy(c);bad['projections']['source']['exhausted']=True
        with self.assertRaisesRegex(ValueError,'fresh source default'):V.validate_capture(bad,refs)
        c['state']['players']['p1']['hand'][0]['damage']=1
        with self.assertRaisesRegex(ValueError,'physical damage mismatch'):V.validate_capture(c,refs)

    def test_required_arena_and_base_counters_never_default_or_skip(self):
        refs=dict(source='source',helper='helper',unused=None)
        for field in('damage','exhausted','hp','power'):
            c=capture();del c['state']['players']['p1']['ground'][0][field]
            # Even a false native known flag cannot relax serialized arena shape.
            c['projections']['helper']['known'][field]=False
            with self.assertRaisesRegex(ValueError,'serialized arena/base'):V.validate_capture(c,refs)
        for field in('damage','hp'):
            c=capture();c['projections']['base']=projection('base','B',zone='base');c['projections']['base'].update(is_base=True,is_unit=False,hp=30)
            c['projections']['base']['known'].update(power=False,exhausted=False,shield_count=False,xp_count=False)
            extended=dict(refs,base='base');del c['state']['players']['p1']['base'][field]
            with self.assertRaisesRegex(ValueError,'serialized arena/base'):V.validate_capture(c,extended)

    def test_bare_hand_known_counter_non_source_is_unsupported(self):
        c=capture();card=c['state']['players']['p1']['ground'].pop()
        c['state']['players']['p1']['hand'].append({k:v for k,v in card.items()if k in('id','setCode')})
        c['projections']['helper'].update(zone='hand',in_arena=False)
        with self.assertRaisesRegex(ValueError,'outside fresh own-hand source'):V.validate_capture(c,dict(source='source',helper='helper',unused=None))


if __name__=='__main__':unittest.main()
