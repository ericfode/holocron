"""Synthetic wire/action chains only; no actual native/conversion/model run."""
import copy
import unittest
from unittest import mock
import numpy as np
import semantic_discrimination_data as D
from test_binding_transfer_data import row,projection,wire


def fixture(mode='committed',up_to=False,removed=False):
    code='JTL_140'if up_to else'LAW_133'
    rows={code:row(code,('event',),hp=None,power=None),'HOST':row('HOST',hp=6),'BASE':row('BASE',('base',),hp=30,power=None),'LEADER':row('LEADER',('leader',)),'RESOURCE':row('RESOURCE')}
    def player(seat):return dict(deck=[],hand=[],ground=[],space=[],discard=[],resources=[],base=dict(id=seat+'base',setCode='BASE',damage=3 if seat=='p1'else 0,hp=30),leader=dict(id=seat+'leader',setCode='LEADER',exhausted=False))
    p1,p2=player('p1'),player('p2');p1['hand']=[dict(id='s',setCode=code)];p1['resources']=[dict(id='r'+str(i),setCode='RESOURCE',exhausted=False)for i in range(12)]
    refs=dict(zip(D.ROLES,('s','oh','eh','a','b','aux','p1base','p2base')))
    ps=dict(source=projection('s',code,rows,zone='hand'))
    for role,uid,owner in(('own_helper','oh','p1'),('opponent_helper','eh','p2'),('anchor_a','a','p1'),('anchor_b','b','p2'),('auxiliary','aux','p2')):
        (p1 if owner=='p1'else p2)['ground'].append(wire(uid,'HOST',rows,damage=1))
        ps[role]=projection(uid,'HOST',rows,owner=owner,damage=1)
    for role,owner in(('own_base','p1'),('opponent_base','p2')):ps[role]=projection(owner+'base','BASE',rows,zone='base',owner=owner,damage=3 if owner=='p1'else 0)
    counters={k:0 for k in('ability_program','death_depth','death_pending','death_window','pending_programs','pending_triggers','after_attack_triggers','after_attack_programs')}
    before=dict(projections=ps,state=dict(players=dict(p1=p1,p2=p2)),decision='Window',abilityProgramPlusOne=0,abilityPc=0,abilitySelection=[],terminal=False,settled=True,offeredActions=[dict(kind='card',card='s')],settlement=dict(decision='Window',**counters,event_group_active=False,support_pending=False))
    world=dict(id=0,source_code=code,cohort='synthetic',partition='train',state_family=0,template_id='synthetic',scenario=0,selection_mode='exactly-one-upTo'if up_to else'single-target',observation_mode='actual-action-endpoints',intent_ref='anchor_a',observation_refs=list(D.ROLES),ready_resources=12,own_base_damage=3,opponent_base_damage=0,arena_cards={r:dict(code='HOST',owner=ps[r]['owner'],damage=1,exhausted=False)for r in D.ROLES[1:6]})
    prompt=copy.deepcopy(before);prompt.update(decision='AbilityTarget',settled=False,abilityProgramPlusOne=1);prompt['settlement'].update(decision='AbilityTarget',ability_program=1)
    prompt['offeredActions']=[dict(kind='card',card='b')]+([dict(kind='card',card='a')]if mode=='committed'else[])
    final=copy.deepcopy(before);final['offeredActions']=[];final['state']['players']['p1']['hand']=[];final['state']['players']['p1']['discard']=[dict(id='s',setCode=code)];final['projections']['source']['zone']='discard'
    for r in final['state']['players']['p1']['resources'][:2]:r['exhausted']=True
    final['state']['players']['p1']['base']['damage']=0;final['projections']['own_base']['damage']=0
    if removed:
        final['state']['players']['p1']['ground']=[u for u in final['state']['players']['p1']['ground']if u['id']!='a'];final['state']['players']['p1']['discard'].append(dict(id='a',setCode='HOST'))
        final['projections']['anchor_a'].update(zone='discard',in_arena=False)
        for k in('damage','hp','power','exhausted','shield_count','xp_count'):final['projections']['anchor_a']['known'][k]=False
    case=dict(card=code,world_id=0,cohort='synthetic',partition='train',state_family=0,template_id='synthetic',scenario=0,selection_mode=world['selection_mode'],observation_mode=world['observation_mode'],refs=refs,declared_intent=dict(ref='anchor_a',id='a',requires_target=True),observation_refs=list(D.ROLES),before=before,publicSnapshotRoundtripExact=True,fixtureAttachmentWitnesses=[],playAction=before['offeredActions'][0],engineError=None,targetPrompt=prompt,targetAction=None,selectionDoneAction=None,selectionWitness=None,declineAction=None,final_source_parent=None,intentOffered=mode=='committed')
    steps=[dict(stage='play-own-hand',before=before,action=case['playAction'],after=prompt)]
    if mode=='committed':
        action=dict(kind='card',card='a');case['targetAction']=action
        if up_to:
            selection=copy.deepcopy(prompt);selection['abilitySelection']=['a'];selection['offeredActions']=[dict(kind='button',arg='done',label='Done')]
            case.update(selectionWitness=selection,selectionDoneAction=selection['offeredActions'][0]);steps.extend([dict(stage='chosen-target',before=prompt,action=action,after=selection),dict(stage='commit-one-selection',before=selection,action=case['selectionDoneAction'],after=final)])
        else:steps.append(dict(stage='chosen-target',before=prompt,action=action,after=final))
        case.update(final=final,lastObserved=final,completion='settled',terminalClassification='settled-committed',intentResolution='committed',intendedTargetCommitted=True)
    elif mode=='cancelled':
        action=dict(kind='button',arg='cancel',label='Cancel');prompt['offeredActions'].append(action);case['declineAction']=action
        steps.append(dict(stage='decline-unoffered-target',before=prompt,action=action,after=final));case.update(final=final,lastObserved=final,completion='settled',terminalClassification='settled-cancelled',intentResolution='unoffered-declined',intendedTargetCommitted=False)
    else:case.update(final=None,lastObserved=prompt,completion='unoffered-observation-only',terminalClassification='unoffered-prompt-only',intentResolution='unoffered-observation-only',intendedTargetCommitted=False)
    case.update(steps=steps,applyCalls=len(steps));return case,world,{},rows


class Tests(unittest.TestCase):
    def test_actual_stable_base_heal_signed_and_nonchosen_endpoints(self):
        case,w,p,rows=fixture();r=D.derive_labels(case,w,p,rows)
        self.assertEqual(r['fit_blockers'],[]);self.assertTrue(r['paid']and r['committed'])
        self.assertEqual((r['targets'][6,2],r['target_mask'][6,2]),(-3,1))
        self.assertFalse(r['chosen_only_target_mask'][6].any());self.assertTrue(r['target_mask'][4,2:].all())
        self.assertFalse(r['target_mask'][0,2:].any())

    def test_prompt_only_has_membership_but_no_fictional_future(self):
        case,w,p,rows=fixture('prompt-only');r=D.derive_labels(case,w,p,rows)
        self.assertEqual(r['fit_blockers'],[]);self.assertEqual((r['targets'][3,0],r['target_mask'][3,0]),(0,1))
        self.assertFalse(r['target_mask'][:,1:].any());self.assertFalse(r['source_mask'][1:].any());self.assertFalse(r['chosen_only_target_mask'].any())
        case['targetPrompt']['offeredActions'].append(dict(kind='button',arg='cancel',label='Cancel'))
        with self.assertRaisesRegex(ValueError,'absent-Cancel'):D.derive_labels(case,w,p,rows)

    def test_actual_cancel_records_source_but_no_target_future(self):
        case,w,p,rows=fixture('cancelled');r=D.derive_labels(case,w,p,rows)
        self.assertEqual(r['source'][2],2);self.assertTrue(r['source_mask'][1:6].all());self.assertFalse(r['target_mask'][:,1:].any())

    def test_removed_known_numeric_after_departure_unknown(self):
        case,w,p,rows=fixture(removed=True);r=D.derive_labels(case,w,p,rows)
        self.assertEqual((r['targets'][3,1],r['target_mask'][3,1]),(1,1));self.assertFalse(r['target_mask'][3,2:].any())

    def test_upTo_exactly_one_done_requires_full_program_selection_proof(self):
        case,w,p,rows=fixture(up_to=True);r=D.derive_labels(case,w,p,rows);self.assertTrue(r['committed'])
        case['selectionWitness']['abilitySelection'].append('b')
        with self.assertRaisesRegex(ValueError,'one selection'):D.derive_labels(case,w,p,rows)

    def test_unknown_counter_and_pending_endpoint_never_get_numeric_zero_labels(self):
        case,w,p,rows=fixture();case['final']['projections']['anchor_a']['known']['hp']=False
        r=D.derive_labels(case,w,p,rows);self.assertEqual(r['target_mask'][3,6],0)
        case,w,p,rows=fixture();case['final']['settled']=False;case['final']['decision']='AbilityTarget';case['final']['abilityProgramPlusOne']=1;case['final']['settlement'].update(decision='AbilityTarget',ability_program=1)
        with self.assertRaisesRegex(ValueError,'settled endpoint'):D.derive_labels(case,w,p,rows)

    def test_public_allowlist_excludes_menus_futures_and_private_piles(self):
        case,w,p,rows=fixture();saved=D.public_before_record(case);poisoned=copy.deepcopy(case)
        poisoned['before']['state']['players']['p2']['hand']=[dict(id='secret')];poisoned['before']['state']['players']['p1']['deck']=[dict(id='ordered-secret')];poisoned['final']={};poisoned['before']['offeredActions']=[]
        self.assertEqual(saved,D.public_before_record(poisoned));self.assertEqual(set(saved),D.M.RECORD_FIELDS)
        with self.assertRaisesRegex(ValueError,'hidden'):D.validate_capture(poisoned['before'],poisoned['refs'],rows)

    def test_primary_masks_are_only_two_physical_held_anchors(self):
        arrays=dict(source_cards=np.array(['ASH_081','IBH_104','LOF_077']),target_mask=np.ones((3,8,7),np.float32))
        manifest=dict(plan=dict(primary_spec=dict(masks={'ASH_081':['target_damage_delta'],'IBH_104':['target_allowed','target_removed']})))
        mask=D.primary_mask(arrays,manifest);self.assertEqual(int(mask.sum()),6);self.assertFalse(mask[:,0].any());self.assertFalse(mask[:,6:].any())

    def test_journal_requires_durable_complete_exact_boundaries(self):
        case,_,_,_=fixture();receipt=dict(collectionPlanSha256='p',sourceRevision='s',selectedWholeCards=['LAW_133'],cases=[case],applyCalls=2)
        context='world-0-LAW_133';journal=[dict(schema='jepa-semantic-discrimination-apply-journal/1',planSha256='p',sourceRevision='s',selectedWholeCards=['LAW_133'])]
        for i,step in enumerate(case['steps'],1):journal.extend([dict(phase='beforeApply',applyCall=i,context=context,branch=step['stage'],before=step['before'],offeredAction=step['action']),dict(phase='afterApply',applyCall=i,context=context,branch=step['stage'],after=step['after'])])
        journal.append(dict(phase='contextComplete',context=context,case=case));self.assertEqual(D.journal_proof(journal,receipt)['apply_calls'],2)
        bad=copy.deepcopy(journal);bad[3]['applyCall']=7
        with self.assertRaisesRegex(ValueError,'sequence'):D.journal_proof(bad,receipt)


if __name__=='__main__':unittest.main()
