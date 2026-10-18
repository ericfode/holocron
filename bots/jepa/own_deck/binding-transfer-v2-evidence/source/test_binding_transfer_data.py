"""Synthetic native-like receipts only; no engine/model/optimizer execution."""
import copy
import unittest
from unittest import mock
import numpy as np
import binding_transfer_data as D


def row(code,types=('unit',),hp=4,power=2,aspects=('vigilance',),traits=(),upgrade_hp=None,upgrade_power=None):
    return dict(setCode=code,card=dict(id=code,setCodes=[dict(set='TEST',number=1)],types=list(types),hp=hp,power=power,cost=1,unique=False,aspects=list(aspects),traits=list(traits),keywords=[],arena='ground'if types==('unit',)else None,upgradeHp=upgrade_hp,upgradePower=upgrade_power),abilities=dict(card=[],unit=[],leader=[]),keywordValues={})


def projection(identity,code,rows,zone='ground',owner='p1',damage=0,exhausted=False):
    card=rows[code]['card'];unit='unit'in card['types'];base='base'in card['types'];physical=unit and zone in('ground','space','hand');numeric=dict(damage=damage,hp=card['hp']or 0,power=card['power']or 0,exhausted=exhausted,shield_count=0,xp_count=0)
    known=dict(identity=True,owner=True,damage=unit or base,hp=unit or base,power=unit,exhausted=unit,shield_count=unit,xp_count=unit)
    for f in('aspects','traits','types','keywords'):known['printed_'+f]=True
    p=dict(id=identity,code=code,owner=owner,zone=zone,present=True,in_arena=zone in('ground','space'),is_unit=unit,is_base=base,known=known,**numeric)
    for f in('aspects','traits','types','keywords'):p['printed_'+f]=card[f]
    return p


def wire(identity,code,rows,damage=0,exhausted=False):
    c=rows[code]['card'];return dict(id=identity,setCode=code,damage=damage,exhausted=exhausted,hp=c['hp'],power=c['power'],upgrades=[])


def fixture(aura=False):
    source='JTL_085'if aura else'ASH_228';rows={source:row(source,('unit',)if aura else('upgrade',),hp=4 if aura else 1,power=2,upgrade_hp=None if aura else 1,upgrade_power=None if aura else 2),'HOST':row('HOST',traits=('force',)),'BASE':row('BASE',('base',),hp=30,power=None),'LEADER':row('LEADER',('leader',)),'RESOURCE':row('RESOURCE')}
    def player():return dict(deck=[],hand=[],ground=[],space=[],discard=[],resources=[],base=None,leader=None)
    p1,p2=player(),player()
    for seat,p in(('p1',p1),('p2',p2)):
        p['base']=dict(id=seat+'base',setCode='BASE',damage=0,hp=30);p['leader']=dict(id=seat+'leader',setCode='LEADER',exhausted=False)
    p1['hand']=[dict(id='s',setCode=source)];zone='space'if aura else'ground';p1[zone]=[wire('a','HOST',rows)]
    (p2 if aura else p1)[zone].append(wire('b','HOST',rows))
    p1['resources']=[dict(id='r'+str(i),setCode='RESOURCE',exhausted=False)for i in range(12)]
    refs=dict(zip(D.ROLES,('s',None,None,'a','b',None,'p1base','p2base')))
    ps=dict(source=projection('s',source,rows,zone='hand'),own_helper=None,opponent_helper=None,anchor_a=projection('a','HOST',rows,zone=zone),anchor_b=projection('b','HOST',rows,zone=zone,owner='p2'if aura else'p1'),auxiliary=None,own_base=projection('p1base','BASE',rows,zone='base'),opponent_base=projection('p2base','BASE',rows,zone='base',owner='p2'))
    b=dict(projections=ps,state=dict(players=dict(p1=p1,p2=p2)),decision='Window',abilityProgramPlusOne=0,terminal=False,settled=True,offeredActions=[dict(kind='card',card='s')])
    b['settlement']=dict(decision='Window',**{k:0 for k in('ability_program','death_depth','death_pending','death_window','pending_programs','pending_triggers','after_attack_triggers','after_attack_programs')},event_group_active=False,support_pending=False)
    world=dict(id=0,source_code=source,partition='train',state_family=0,template_id='aura'if aura else'parent',cohort='friendly-space-aura'if aura else'attachment-parent-binding',intent_ref='source'if aura else'anchor_a',requires_target=not aura,observation_mode='passive-aura'if aura else'attachment-parent',observation_refs=['anchor_a','anchor_b'],ready_resources=12,anchor_damage=0,own_anchor='anchor_a')
    plan=dict(candidate_order=list(D.ROLES),helpers=dict(host='HOST',aura_space='HOST'))
    final=copy.deepcopy(b);final['offeredActions']=[];final['state']['players']['p1']['hand']=[]
    for r in final['state']['players']['p1']['resources'][:2]:r['exhausted']=True
    case=dict(card=source,world_id=0,cohort=world['cohort'],partition='train',state_family=0,template_id=world['template_id'],refs=refs,declared_intent=dict(ref=world['intent_ref'],id='s'if aura else'a',requires_target=not aura),observation_refs=world['observation_refs'],observation_mode=world['observation_mode'],before=b,publicSnapshotRoundtripExact=True,fixtureAttachmentWitnesses=[],playAction=b['offeredActions'][0],engineError=None,completion='settled',targetPrompt=None,targetAction=None,intendedTargetCommitted=not aura)
    if aura:
        final['state']['players']['p1']['space'].append(wire('s',source,rows,exhausted=True));final['projections']['source'].update(zone='space',in_arena=True,exhausted=True)
        host=final['state']['players']['p1']['space'][0];host['hp']+=1;host['power']+=1;final['projections']['anchor_a']['hp']+=1;final['projections']['anchor_a']['power']+=1
        case['steps']=[dict(stage='play-own-hand',before=b,action=case['playAction'],after=final)];case['final_source_parent']=None
    else:
        prompt=copy.deepcopy(b);prompt['decision']='UpgradeTarget';prompt['settlement']['decision']='UpgradeTarget';prompt['settled']=False;prompt['sourceInstance']='s';prompt['offeredActions']=[dict(kind='card',card='a'),dict(kind='card',card='b')]
        host=final['state']['players']['p1']['ground'][0];host.update(hp=5,power=4,exhausted=True);host['upgrades']=[dict(id='s',setCode=source,token=False,owner='p1')]
        final['projections']['source'].update(zone='upgrade',in_arena=False);final['projections']['anchor_a'].update(hp=5,power=4,exhausted=True)
        case['targetPrompt']=prompt;case['targetAction']=prompt['offeredActions'][0];case['final_source_parent']='a'
        case['steps']=[dict(stage='play-own-hand',before=b,action=case['playAction'],after=prompt),dict(stage='attach-intended-host',before=prompt,action=case['targetAction'],after=final)]
    case.update(final=final,lastObserved=final,applyCalls=len(case['steps']))
    return case,world,plan,rows


class Tests(unittest.TestCase):
    def test_quantity_support_is_frozen_source_and_independent_native_gate(self):
        specs=[('aura',1,1,'train'),('parent2',2,1,'train'),('parent3',1,3,'train'),('held2',2,2,'family_held'),('held3',2,3,'joint')]
        cards=[];worlds=[]
        for i,(code,power,hp,partition)in enumerate(specs):
            r=row(code,('unit',)if i==0 else('upgrade',),upgrade_power=power,upgrade_hp=hp)
            if i==0:r['abilities']['card']=[dict(trigger='constant',effect=dict(kind='modifyStats',power=dict(kind='const',value=1),hp=dict(kind='const',value=1)))]
            cards.append(dict(code=code,raw_card=r));worlds.append(dict(id=i,source_code=code,partition=partition,observation_refs=['anchor_a','anchor_b'],intent_ref='anchor_a',own_anchor='anchor_a',observation_mode='passive-aura'if i==0 else'attachment-parent'))
        declaration=dict(training_positive_power=[1,2],training_positive_hp=[1,3],held_positive_power=[2],held_positive_hp=[2,3])
        plan=dict(cards=cards,worlds=worlds,numeric_support_prelabel=declaration,candidate_order=list(D.ROLES),split=dict(root_partitions=dict(train=[0,1,2],family_held=[3],joint=[4])))
        self.assertTrue(D.quantity_support(plan)['passed'])
        y=np.zeros((5,8,7),np.float32);mask=np.zeros_like(y);mask[:,3:5,5:]=1
        for i,(_,power,hp,_)in enumerate(specs):y[i,3,5:]=[power,hp]
        arrays=dict(targets=y,target_mask=mask);report=D.quantity_support(plan,arrays)
        self.assertTrue(report['passed']);self.assertEqual(len(report['native_observed']['per_anchor']),20)
        arrays['targets'][3,3,6]=4
        self.assertFalse(D.quantity_support(plan,arrays)['passed'])
        arrays['targets'][3,3,6]=2;arrays['target_mask'][3,3,6]=0
        self.assertFalse(D.quantity_support(plan,arrays)['passed'])
        bad=copy.deepcopy(plan);bad['cards'][3]['raw_card']['card']['upgradeHp']=4
        with self.assertRaisesRegex(ValueError,'source-literal'):D.quantity_support(bad)

    def test_actual_parent_endpoints_and_chosen_subset(self):
        case,world,plan,rows=fixture();r=D.derive_labels(case,world,plan,rows)
        self.assertEqual(r['fit_blockers'],[]);self.assertEqual(r['source'][1],1);self.assertEqual(r['source'][2],2)
        a,b=3,4;np.testing.assert_array_equal(r['targets'][a,2:],[0,1,0,2,1]);np.testing.assert_array_equal(r['targets'][b,2:],np.zeros(5))
        self.assertTrue(r['target_mask'][a,1:].all()and r['target_mask'][b,1:].all());self.assertFalse(r['chosen_only_target_mask'][b].any());self.assertTrue(r['chosen_only_target_mask'][a,1:].all())
        self.assertFalse(r['source_mask'][6:].any())

    def test_passive_aura_has_no_fictional_target_or_chosen_future(self):
        case,world,plan,rows=fixture(True);r=D.derive_labels(case,world,plan,rows)
        self.assertEqual(r['fit_blockers'],[]);self.assertEqual(r['selected'],0);self.assertFalse(r['chosen_only_target_mask'].any());self.assertFalse(r['target_mask'][:,0].any())
        np.testing.assert_array_equal(r['targets'][3,5:],[1,1]);np.testing.assert_array_equal(r['targets'][4,5:],[0,0])
        record=D.public_before_record(case);x,c=D.M.project_record(record,list(D.ROLES),rows);self.assertFalse(np.asarray(c)[:,7:].any())

    def test_unknown_counter_is_masked_and_blocks_planned_full_support(self):
        case,world,plan,rows=fixture();case['final']['projections']['anchor_a']['known']['hp']=False
        r=D.derive_labels(case,world,plan,rows);self.assertEqual(r['target_mask'][3,6],0);self.assertIn('planned-numeric-anchor-observation-unknown',r['fit_blockers'])
        self.assertEqual(r['target_mask'][3,5],1)

    def test_pending_does_not_fill_future_zero(self):
        case,world,plan,rows=fixture();case['steps']=case['steps'][:1];case.update(final=None,lastObserved=case['targetPrompt'],targetAction=None,intendedTargetCommitted=False,completion='unreviewed-continuation',applyCalls=1)
        r=D.derive_labels(case,world,plan,rows);self.assertFalse(r['source_mask'][1:].any());self.assertFalse(r['target_mask'][:,1:].any());self.assertIn('pending-native-outcome',r['fit_blockers'])

    def test_successful_action_and_physical_parent_required(self):
        case,world,plan,rows=fixture();case['final_source_parent']='b'
        with self.assertRaisesRegex(ValueError,'physical parent'):D.derive_labels(case,world,plan,rows)
        case,world,plan,rows=fixture();case['steps'][1]['action']=dict(kind='card',card='b')
        with self.assertRaisesRegex(ValueError,'commitment'):D.derive_labels(case,world,plan,rows)

    def test_redaction_removes_future_private_and_oracle_fields(self):
        case,_,_,rows=fixture();r=D.public_before_record(case)
        self.assertEqual(set(r),D.M.RECORD_FIELDS);self.assertEqual(set(r['before']),{'state','projections'})
        self.assertEqual(set(r['before']['state']['players']['p1']),{'ground','space'})
        poisoned=copy.deepcopy(case);poisoned['before']['state']['players']['p2']['hand']=[dict(id='private')];poisoned['before']['state']['players']['p1']['deck']=[dict(id='secret-order')];poisoned['before']['offeredActions']=[];poisoned['final_source_parent']='secretfuture';poisoned['final']={}
        self.assertEqual(r,D.public_before_record(poisoned))
        x,c=D.M.project_record(r,list(D.ROLES),rows);xx,cc=D.M.project_record(D.public_before_record(poisoned),list(D.ROLES),rows)
        self.assertEqual(x,xx);self.assertEqual(c,cc)
        with self.assertRaisesRegex(ValueError,'hidden'):D.validate_capture(poisoned['before'],poisoned['refs'],rows)

    def test_per_head_support_signed_roots_and_two_template_gate(self):
        y=np.zeros((4,8,7),np.float32);m=np.zeros_like(y);m[:,:2,2:]=1;y[0,0,2]=1;y[1,0,2]=3;y[2,0,5:]=[1,1];y[3,0,5:]=[2,1]
        arrays=dict(targets=y,target_mask=m,source_targets=np.zeros((4,9),np.float32),source_mask=np.ones((4,9),np.float32));manifest=dict(template_ids=['d1','d2','s1','s2'])
        report=D.support_gate(arrays,manifest,[0,1,2,3]);self.assertTrue(report['passed'])
        support=D.support(arrays,manifest,np.arange(4));self.assertEqual(support['target_damage_delta']['positive_roots'],2);self.assertEqual(support['target_power_delta']['negative'],0)
        manifest['template_ids'][3]='s1';self.assertFalse(D.support_gate(arrays,manifest,[0,1,2,3])['passed'])

    def test_journal_detects_reordered_missing_and_unoffered_attempt(self):
        case,_,_,_=fixture();receipt=dict(sourceRevision='rev',collectionPlanSha256='plan',selectedWholeCards=['ASH_228'],cases=[case],applyCalls=2)
        key='world-0-ASH_228';journal=[dict(schema='jepa-binding-transfer-apply-journal/1',sourceRevision='rev',planSha256='plan',selectedWholeCards=['ASH_228'])]
        for n,step in enumerate(case['steps'],1):journal.extend([dict(phase='beforeApply',applyCall=n,context=key,branch=step['stage'],before=step['before'],offeredAction=step['action']),dict(phase='afterApply',applyCall=n,context=key,branch=step['stage'],after=step['after'])])
        journal.append(dict(phase='contextComplete',context=key,case=case));self.assertEqual(D.validate_journal(journal,receipt)['apply_calls'],2)
        broken=copy.deepcopy(journal);broken[3]['applyCall']=8
        with self.assertRaisesRegex(ValueError,'sequence'):D.validate_journal(broken,receipt)
        with self.assertRaisesRegex(ValueError,'count'):D.validate_journal(journal[:-2]+journal[-1:],receipt)

    def test_unavailable_play_preserves_only_observed_availability(self):
        case,world,plan,rows=fixture();case['before']['offeredActions']=[]
        case.update(playAction=None,steps=[],final=None,lastObserved=case['before'],targetPrompt=None,targetAction=None,intendedTargetCommitted=False,completion='play-unavailable',applyCalls=0)
        result=D.derive_labels(case,world,plan,rows)
        self.assertEqual(result['source'][0],0);self.assertEqual(result['source_mask'][0],1)
        self.assertFalse(result['source_mask'][1:].any());self.assertFalse(result['target_mask'].any());self.assertIn('planned-play-unavailable',result['fit_blockers'])

    def test_consumed_conflicts_distinguish_intent_ablation_without_rejecting_it(self):
        case,world,plan,rows=fixture();other=copy.deepcopy(case);other['declared_intent'].update(ref='anchor_b',id='b')
        records=[D.public_before_record(case),D.public_before_record(other)]
        x=np.asarray([D.V.legacy_context(case['before'],rows)]*2,np.float32)
        c=np.asarray([[D.V.legacy_candidate(case['before']['projections'][r],'s',rows)if case['before']['projections'][r]is not None else np.zeros(34,np.float32)for r in D.ROLES]]*2,np.float32)
        y=np.zeros((2,8,7),np.float32);m=np.zeros_like(y);m[:,3:5,5:]=1;y[0,3,5:]=[2,1];y[1,4,5:]=[2,1]
        arrays=dict(context_features=x,candidate_features=c,source_cards=np.array(['ASH_228']*2),selected_candidate_indices=np.array([3,4],np.int64),source_targets=np.zeros((2,9),np.float32),source_mask=np.zeros((2,9),np.float32),targets=y,target_mask=m)
        manifest=dict(public_before_records=records,public_catalog_rows=rows,candidate_order=list(D.ROLES),public_binding_contract=dict(schema=D.M.SCHEMA,task='actual-intent-endpoints',aspect_vocabulary=list(D.M.ASPECTS),metadata_mode='printed-static-fixture-only'),source_head_names=list(D.SOURCE_HEADS),source_binary_heads=list(D.SOURCE_BINARY),target_names=list(D.TARGET_HEADS),binary_heads=list(D.TARGET_BINARY))
        plan=dict(cards=[dict(code='ASH_228',raw_card=rows['ASH_228'])],train_codes=['ASH_228'],split=dict(root_partitions=dict(train=[0,1])))
        with mock.patch.object(D.E,'canonical_document',return_value=({},{})),mock.patch.object(D.E,'symbols_for',return_value={}),mock.patch.object(D.E,'make_bank',return_value=({},1)),mock.patch.object(D.E,'tensor_signatures',return_value=['fixed-program']):
            conflicts,_,xx,cc,_=D.input_conflicts(arrays,manifest,plan)
        self.assertGreater(conflicts['C0R0']['conflict_count'],0);self.assertGreater(conflicts['C1R0']['conflict_count'],0)
        self.assertEqual(conflicts['C0R1']['conflict_count'],0);self.assertEqual(conflicts['C1R1']['conflict_count'],0)
        np.testing.assert_array_equal(xx[:,:18],x);np.testing.assert_array_equal(cc[:,:,:34],c)

    def test_LAW_state_damage3_setup_matches_frozen_world(self):
        refs=dict(zip(D.ROLES,('s','oh','eh','a','b',None,'base1','base2')))
        q=lambda uid:dict(decision='UpgradeTarget',sourceInstance=uid,offeredActions=[dict(kind='card',card='a')])
        world=dict(id=4,source_code='LAW_045',partition='state_held',state_family=4,template_id='conditional',cohort='own-aspect-condition',intent_ref='anchor_a',requires_target=True,observation_mode='chosen-target',observation_refs=['anchor_a','anchor_b'],ready_resources=12,victim_damage=3,own_helper='H',opponent_helper='M')
        before=dict(decision='Window',state=dict(players=dict(p1=dict(resources=[{}]*12))),projections=dict(source=dict(code='LAW_045',owner='p1',zone='hand'),own_helper=dict(code='H'),opponent_helper=dict(code='M'),anchor_a=dict(id='a',code='HOST',owner='p2',hp=10,damage=3),anchor_b={}))
        case=dict(card='LAW_045',partition='state_held',state_family=4,template_id='conditional',cohort=world['cohort'],before=before,refs=refs,publicSnapshotRoundtripExact=True,declared_intent=dict(ref='anchor_a',id='a',requires_target=True),observation_mode='chosen-target',observation_refs=world['observation_refs'],fixtureAttachmentWitnesses=[dict(upgrade=uid,host='a',code=code,publicTargetQuery=q(uid),offeredHost=dict(kind='card',card='a'))for uid,code in(('u1','UP1'),('u2','UP2'))])
        objects={uid:dict(zone='upgrade',parent='a',card=dict(setCode=code))for uid,code in(('u1','UP1'),('u2','UP2'))}
        with mock.patch.object(D,'validate_capture',return_value=True),mock.patch.object(D.V,'physical',return_value=objects),mock.patch.object(D.V,'ready',return_value=12):
            self.assertIs(D.validate_setup(case,world,dict(helpers=dict(victim='HOST',victim_upgrades=['UP1','UP2'])),{}),before)
            case['before']['projections']['anchor_a']['damage']=2
            with self.assertRaisesRegex(ValueError,'planned-damage'):D.validate_setup(case,world,dict(helpers=dict(victim='HOST',victim_upgrades=['UP1','UP2'])),{})


if __name__=='__main__':unittest.main()
