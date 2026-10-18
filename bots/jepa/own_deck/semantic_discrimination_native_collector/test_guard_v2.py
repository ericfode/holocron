"""Portable stdlib proof tests; no build, engine process, snapshot or model call."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('semantic_native_guard',HERE/'supervise_v2.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)

def action(card=None,arg=None,label=''):
    return dict(kind='card'if card else 'button',card=card,arg=arg,label=label)

def capture(decision='Window',actions=(),selection=()):
    settled=decision=='Window'
    return dict(terminal=False,settled=settled,decision=decision,offeredActions=list(actions),
        abilityProgramPlusOne=0 if settled else 3,abilityPc=0 if settled else 1,abilitySelection=list(selection),sourceInstance='c0',
        settlement=dict(decision=decision,ability_program=0 if settled else 3,death_depth=0,death_pending=0,death_window=0,pending_programs=0,pending_triggers=0,after_attack_triggers=0,after_attack_programs=0,event_group_active=False,support_pending=False))

def bank():
    worlds=[];cases=[];journal=[dict(schema='jepa-semantic-discrimination-apply-journal/1',maxApplyCalls=128,planSha256='x')];counter=0;validation=[]
    for i in range(33):
        mode='exactly-one-upTo'if i==0 else 'single-target';kind='observation'if i==1 else 'cancel'if i==2 else 'commit'
        world=dict(id=i,source_code='X',cohort='fixture',partition='train',template_id='template',state_family=0,observation_mode='actual-action-endpoints',selection_mode=mode,scenario=0,intent_ref='anchor_a',requires_target=True,observation_refs=['anchor_a','anchor_b'],max_applies=4)
        refs=dict(source='c0',anchor_a='c1',anchor_b='c2');play=action('c0',label='X');target=action('c1',label='A');cancel=action(arg='cancel',label='Cancel');done=action(arg='done',label='Done')
        before=capture(actions=[play]);offers=[target]if kind=='commit'else[cancel]if kind=='cancel'else[action('c2',label='B')]
        prompt=capture('AbilityTarget',offers);steps=[dict(stage='play-own-hand',before=before,action=play,after=prompt)]
        row=dict(card='X',world_id=i,cohort='fixture',partition='train',template_id='template',state_family=0,observation_mode=world['observation_mode'],selection_mode=mode,scenario=0,refs=refs,declared_intent=dict(ref='anchor_a',id='c1',requires_target=True),observation_refs=world['observation_refs'],before=before,playAction=play,targetPrompt=prompt,targetAction=None,selectionDoneAction=None,selectionWitness=None,declineAction=None,intentOffered=kind=='commit',engineError=None)
        if kind=='commit':
            end=capture()
            if mode=='exactly-one-upTo':
                witness=capture('AbilityTarget',[done,target],['c1']);steps.append(dict(stage='chosen-target',before=prompt,action=target,after=witness));steps.append(dict(stage='commit-one-selection',before=witness,action=done,after=end));row.update(selectionDoneAction=done,selectionWitness=witness)
            else:steps.append(dict(stage='chosen-target',before=prompt,action=target,after=end))
            row.update(targetAction=target,intendedTargetCommitted=True,intentResolution='committed',terminalClassification='settled-committed',completion='settled',final=end,lastObserved=end)
        elif kind=='cancel':
            end=capture();steps.append(dict(stage='decline-unoffered-target',before=prompt,action=cancel,after=end));row.update(declineAction=cancel,intendedTargetCommitted=False,intentResolution='unoffered-declined',terminalClassification='settled-cancelled',completion='settled',final=end,lastObserved=end)
        else:row.update(intendedTargetCommitted=False,intentResolution='unoffered-observation-only',terminalClassification='unoffered-prompt-only',completion='unoffered-observation-only',final=None,lastObserved=prompt)
        row.update(steps=steps,applyCalls=len(steps));worlds.append(world);cases.append(row)
        validation.append(dict(world_id=i,card='X',before=before,publicSnapshotRoundtripExact=True,legalActionsRoundtripExact=True,applyCalls=0,actionsApplied=0))
        context=f'world-{i}-X'
        for step in steps:
            counter+=1;journal.extend([dict(phase='beforeApply',applyCall=counter,context=context,branch=step['stage'],before=step['before'],offeredAction=step['action']),dict(phase='afterApply',applyCall=counter,context=context,branch=step['stage'],after=step['after'])])
        journal.append(dict(phase='contextComplete',context=context,case=row))
    return dict(worlds=worlds),dict(schema='jepa-semantic-discrimination-native/1',collectionComplete=True,cases=cases,applyCalls=counter,collectionPlanSha256='x',fixtureValidation=validation),journal

class GuardTests(unittest.TestCase):
    def run_proof(self,mutate=None):
        plan,raw,journal=bank()
        if mutate:mutate(plan,raw,journal)
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'plan.json';p.write_text(json.dumps(plan));j=Path(d)/'journal.jsonl';j.write_text(''.join(json.dumps(r)+'\n'for r in journal))
            return G.verify_complete_cases(raw,dict(collection_plan=G.pin(p)),j)
    def test_full_bank_up_to_cancel_and_prompt_only(self):
        out=self.run_proof();self.assertEqual(out['completed_roots'],33);self.assertTrue(out['unoffered_prompt_only_future_unknown'])
    def test_two_picks_rejected(self):
        with self.assertRaisesRegex(ValueError,'exactly-one'):self.run_proof(lambda p,r,j:r['cases'][0]['selectionWitness'].__setitem__('abilitySelection',['c1','c2']))
    def test_substituted_target_rejected(self):
        with self.assertRaises(ValueError):self.run_proof(lambda p,r,j:r['cases'][3].__setitem__('targetAction',action('c2',label='B')))
    def test_prompt_only_cannot_claim_future(self):
        with self.assertRaisesRegex(ValueError,'observation-only'):self.run_proof(lambda p,r,j:r['cases'][1].__setitem__('final',capture()))
    def test_prompt_only_must_use_available_cancel(self):
        def change(p,r,j):r['cases'][1]['targetPrompt']['offeredActions'].append(action(arg='cancel',label='Cancel'))
        with self.assertRaisesRegex(ValueError,'Cancel'):self.run_proof(change)
    def test_every_fixture_roundtrip_required(self):
        with self.assertRaisesRegex(ValueError,'roundtrip'):self.run_proof(lambda p,r,j:r['fixtureValidation'][8].__setitem__('legalActionsRoundtripExact',False))
    def test_partial_journal_retains_known_prefix(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'j';p.write_text(json.dumps(dict(schema='jepa-semantic-discrimination-apply-journal/1',maxApplyCalls=128))+'\n'+json.dumps(dict(phase='beforeApply',applyCall=1))+'\n{')
            out=G.trace_exposure(p,True);self.assertFalse(out['verified']);self.assertEqual(out['known_calls'],1)
    def test_historical_pid_peaks_are_not_concurrent_memory(self):
        r=dict(observed_per_pid_peak_bytes={});G.memory_sample(r,{1:20,2:500},1,20);out=G.memory_sample(r,{1:20,3:500},1,20)
        self.assertEqual(out,520);self.assertEqual(sum(r['observed_per_pid_peak_bytes'].values()),1020)
    def test_frozen_full_plan_tamper_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'plan.json';p.write_text('{"worlds":[1]}');m=dict(collection_plan=G.pin(p));raw=dict(collectionPlanSha256=m['collection_plan']['sha256'],collectionPlan=dict(worlds=[2]))
            with self.assertRaisesRegex(ValueError,'full collection plan'):G.verify_frozen_plan(raw,m)
    def test_public_privacy_rejects_opponent_hand(self):
        player=dict(deck=[],hand=[],resources=[],discard=[]);cap=dict(state=dict(players=dict(p1=copy.deepcopy(player),p2=copy.deepcopy(player))),projections=dict(source=dict(id='c0')))
        raw=dict(cases=[dict(before=cap)]);self.assertEqual(G.verify_fixture_privacy(raw)['captures_checked'],1)
        cap['state']['players']['p2']['hand']=[dict(id='secret')]
        with self.assertRaisesRegex(ValueError,'private'):G.verify_fixture_privacy(raw)
    def test_failed_prefix_never_becomes_completed_counter_proof(self):
        observed={}
        class Account:
            def finish(self,*args,**kw):
                observed.update(status=args[2],counts=args[4],proof=kw['counter_proof'])
                return dict(completed_stages=[],charged=dict(native_applies=128,seconds=45),last_record_sha256='x')
        receipt=dict(status='failed',stage='native')
        G.close_accounted_attempt(Account(),None,[],receipt,1.,dict(known_calls=2,verified=True),[],True,counter_proof=dict(path='partial'))
        self.assertIsNone(observed['proof']);self.assertEqual(observed['counts']['native_applies'],2)
        self.assertEqual(receipt['charged_native_applies'],128)
    def test_cleanup_eperm_retains_pending_and_still_waits(self):
        proc=mock.Mock(pid=123)
        receipt={}
        with mock.patch.object(G.os,'killpg',side_effect=PermissionError('denied')):
            self.assertFalse(G.cleanup_owned(proc,123,lambda pg:[],receipt))
        proc.wait.assert_called_once();self.assertEqual(receipt['cleanup_errors'][0]['operation'],'kill-owned-group')
        class Account:
            def note_pending_failure(self,*a):return dict(pending=dict(reservation={'native_applies':128}),conservative_including_pending={'native_applies':128},cumulative={})
            def finish(self,*a,**kw):raise AssertionError('uncertain cleanup must never finish')
        G.close_accounted_attempt(Account(),None,[],receipt,1.,dict(known_calls=0,verified=False),[],False)
        self.assertTrue(receipt['pending_attempt_preserved'])
    def test_unfrozen_catalogue_and_compiler_overrides_rejected(self):
        for key in ('SWU_RULES_CATALOGUE','RUSTC_WRAPPER','CARGO_PROFILE_DEV_CODEGEN_UNITS'):
            with mock.patch.dict(G.os.environ,{key:'unreviewed'},clear=True):
                with self.assertRaisesRegex(ValueError,'override'):G.build_environment(Path('/tmp/cache'))
    def test_child_descriptors_have_unique_binary_and_exclusive_stage_outputs(self):
        d=G.child_descriptors('/tmp/new-campaign')
        self.assertIn('semantic-discrimination-native-collector',d['build']['argv'])
        self.assertEqual(Path(d['native']['argv'][0]).name,'semantic-discrimination-native-collector')
        self.assertEqual(d['native']['outputs'],[str(Path('/tmp/new-campaign/native-attempt-1').resolve())])
        self.assertNotIn(str(G.TARGET_DIR),d['build']['outputs'])
    def test_versioned_routes_preserve_frozen_predecessors(self):
        self.assertEqual(G.sha(HERE/'supervise.py'),'36e32622ff8ff715e8a9aa7ab79d221b0ee0c0ab096c1c7447726810cdcaff88')
        self.assertEqual(G.sha(HERE/'src/main.rs'),'f5a54313c9d33fa2f2e1755d63d60cf2a22bf53d71b752c9f174b2f551df948e')
        self.assertEqual(G.ACCOUNTING_SOURCE.name,'semantic_discrimination_repair_accounting.py')
        self.assertEqual(G.ACCOUNTING_CORE_SOURCE.name,'semantic_discrimination_accounting.py')
        self.assertEqual(G.SPEC_PATH.parent.name,'semantic-discrimination-repair-v1')
        self.assertEqual(G.MANIFEST_PATH,G.SPEC_PATH.parent/'metadata-1/native-source-manifest.json')
        source=(HERE/'supervise_v2.py').read_text()
        self.assertIn('"supervise_v2.py","test_guard_v2.py"',source)
        self.assertNotIn('sys.modules[',source)
    def test_source_preapply_gate_and_single_apply_entrypoint(self):
        source=(HERE/'src/main.rs').read_text();self.assertEqual(source.count('e.apply('),1)
        run=source[source.index('fn run(validate_only:'):]
        self.assertLess(run.index('let fixture_validation=validate_fixtures'),run.index('let mut budget=Budget'))
        self.assertIn('worlds.len()!=33',source);self.assertIn('const MAX_APPLY:usize=128',source)
        self.assertIn('unoffered-observation-only',source)

if __name__=='__main__':unittest.main()
