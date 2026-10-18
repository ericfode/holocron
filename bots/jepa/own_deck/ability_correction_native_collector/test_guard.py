"""Portable source/proof/cleanup tests. No process, engine or model execution."""
import ast
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('ability_guard_test',HERE/'supervise.py')
G=importlib.util.module_from_spec(loader);loader.loader.exec_module(G)

def action(card=None,arg=None,label=''):
    return dict(kind='card'if card else 'button',card=card,arg=arg,label=label)

def capture(decision='Window',actions=(),selection=()):
    settled=decision=='Window'
    return dict(terminal=False,settled=settled,decision=decision,offeredActions=list(actions),
        abilityProgramPlusOne=0 if settled else 3,abilityPc=0 if settled else 1,abilitySelection=list(selection),sourceInstance='c0',
        settlement=dict(decision=decision,ability_program=0 if settled else 3,death_depth=0,death_pending=0,death_window=0,pending_programs=0,pending_triggers=0,after_attack_triggers=0,after_attack_programs=0,event_group_active=False,support_pending=False))

def bank():
    worlds=[];cases=[];journal=[dict(schema='jepa-ability-correction-apply-journal/1',maxApplyCalls=32,planSha256='x')];counter=0;validation=[]
    for i in range(8):
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
    return dict(worlds=worlds),dict(schema='jepa-ability-correction-native/1',collectionComplete=True,cases=cases,applyCalls=counter,collectionPlanSha256='x',fixtureValidation=validation),journal


class Tests(unittest.TestCase):
    def proof(self, mutate=None):
        plan, raw, journal = bank()
        if mutate:
            mutate(plan, raw, journal)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'plan.json'; p.write_text(json.dumps(plan))
            j = Path(directory) / 'journal.jsonl'; j.write_text(''.join(json.dumps(r) + '\n' for r in journal))
            return G.P.verify_complete_cases(raw, dict(collection_plan=G.pin(p)), j)

    def test_all_eight_actions_and_observation_only(self):
        out = self.proof()
        self.assertEqual(out['completed_roots'], 8)
        self.assertTrue(out['unoffered_prompt_only_future_unknown'])

    def test_wrong_intent_and_second_pick_rejected(self):
        with self.assertRaises(ValueError):
            self.proof(lambda p, r, j: r['cases'][3].__setitem__('targetAction', action('c2', label='B')))
        with self.assertRaises(ValueError):
            self.proof(lambda p, r, j: r['cases'][0]['selectionWitness'].__setitem__('abilitySelection', ['c1', 'c2']))

    def test_prompt_only_has_no_after_and_must_cancel_if_available(self):
        with self.assertRaises(ValueError):
            self.proof(lambda p, r, j: r['cases'][1].__setitem__('final', capture()))
        with self.assertRaises(ValueError):
            self.proof(lambda p, r, j: r['cases'][1]['targetPrompt']['offeredActions'].append(action(arg='cancel', label='Cancel')))

    def test_all_fixture_roundtrips_required(self):
        with self.assertRaises(ValueError):
            self.proof(lambda p, r, j: r['fixtureValidation'][7].__setitem__('publicSnapshotRoundtripExact', False))

    def test_partial_journal_keeps_only_known_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'journal'
            p.write_text(json.dumps(dict(schema='jepa-ability-correction-apply-journal/1', maxApplyCalls=32)) + '\n' + json.dumps(dict(phase='beforeApply', applyCall=1)) + '\n{')
            out = G.P.trace_exposure(p, True)
            self.assertFalse(out['verified']); self.assertEqual(out['known_calls'], 1)

    def test_exact_copied_proof_function_delta(self):
        old = G.PRIOR.read_text(); new = (HERE / 'native_proof.py').read_text()
        old_ast, new_ast = ast.parse(old), ast.parse(new)
        for name in ('settled_capture', 'trace_exposure', 'verify_success_journal', 'verify_complete_cases'):
            a = next(n for n in old_ast.body if isinstance(n, ast.FunctionDef) and n.name == name)
            b = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == name)
            original = '\n'.join(old.splitlines()[a.lineno - 1:a.end_lineno])
            current = '\n'.join(new.splitlines()[b.lineno - 1:b.end_lineno])
            self.assertEqual(current, original.replace('jepa-semantic-discrimination-', 'jepa-ability-correction-').replace('128', '32').replace('33', '8'))

    def test_new_binary_copied_inside_campaign_and_frozen_descriptors(self):
        d = G.descriptors('/tmp/new-campaign', '/usr/bin/python3')
        root = Path('/tmp/new-campaign').resolve()
        self.assertEqual(d['build']['outputs'], [str(root / 'build-1')])
        self.assertEqual(d['native']['outputs'], [str(root / 'native-attempt-1')])
        self.assertEqual(G.child_command('native', '/tmp/new-campaign')[0], str(root / 'build-1/ability-correction-native-collector'))
        self.assertIn('--offline', G.child_command('build', '/tmp/new-campaign'))
        self.assertIn('--locked', G.child_command('build', '/tmp/new-campaign'))

    def test_cleanup_unknown_retains_pending_without_finish(self):
        run = mock.Mock()
        run.pending_failure.return_value = dict(pending=True)
        receipt = dict(stage='native', status='failed', error='EPERM')
        G.cleanup_and_close(run, receipt, [], False)
        run.finish.assert_not_called(); run.pending_failure.assert_called_once()
        self.assertEqual(receipt['status'], 'pending-failure')

    def test_authoritative_finish_downgrade_propagates(self):
        run = mock.Mock()
        run.finish.return_value = dict(completed=['build'], failures=1)
        receipt = dict(stage='native', status='completed')
        G.cleanup_and_close(run, receipt, [], True)
        self.assertEqual(receipt['status'], 'failed')

    def test_external_native_intent_precedes_spawn_and_complete_follows_proof(self):
        source = (HERE / 'supervise.py').read_text()
        body = source[source.index('def run(args):'):]
        self.assertLess(body.index("session.intent('native_applies', 32)"), body.index('subprocess.Popen('))
        self.assertLess(body.index('summary = verify_native('), body.index('session.complete(token,'))
        self.assertIn("actual=summary['actual_native_applies']", body)

    def accounted_prelaunch_failure(self, *, bad_invocation=False, bad_contract=False):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            args = SimpleNamespace(spec=root / 'campaign-spec.json', stage='native',
                manifest=root / 'metadata-1/native-source-manifest.json', out=root / 'native-attempt-1', execute=True)
            reserve = dict(seconds=15., native_applies=32, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
            expected = dict(reserve); expected.pop('seconds'); expected['native_applies'] = None
            descriptor = dict(argv=[str(Path(G.sys.executable).absolute()), str(Path(G.__file__).resolve()), '--expected'],
                reservation=reserve, expected=expected, external_counters=[] if bad_contract else ['native_applies'])
            class Session:
                state = dict(proofs={}, pending=None)
                def begin(self, stage, **kw):
                    self.state['pending'] = dict(stage=stage); events.append(('begin', kw))
                def finish(self, status, **kw):
                    events.append(('finish', status)); self.state['pending'] = None
                    return dict(completed=[], failures=1, charged=dict(native_applies=32, seconds=15.), last_sha256='closed')
            session = Session()
            class Budget:
                frozen = {}
                spec = dict(stages={'native': descriptor}, guard=dict(rss_bytes=1024 ** 3, cpu_workers=1))
                @contextmanager
                def lease(self):
                    yield session
            with mock.patch.object(G, 'load', return_value=SimpleNamespace(Budget=lambda p: Budget())), \
                 mock.patch.object(G.sys, 'argv', ['supervise.py', '--different' if bad_invocation else '--expected']), \
                 mock.patch.object(G, 'preflight') as preflight, mock.patch.object(G.subprocess, 'Popen') as spawn:
                receipt = G.run(args)
            preflight.assert_not_called(); spawn.assert_not_called()
            self.assertEqual([event[0] for event in events], ['begin', 'finish'])
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['accounting']['charged']['native_applies'], 32)
            self.assertFalse(args.out.exists())
            return receipt

    def test_wrong_invocation_is_charged_after_durable_begin(self):
        receipt = self.accounted_prelaunch_failure(bad_invocation=True)
        self.assertIn('actual wrapper invocation', receipt['error'])
        self.assertIn('--different', receipt['actual_wrapper_argv'])

    def test_missing_metadata_is_charged_after_durable_begin(self):
        receipt = self.accounted_prelaunch_failure()
        self.assertIn('completed metadata/build', receipt['error'])

    def test_external_native_contract_rejected_before_child_inside_reservation(self):
        receipt = self.accounted_prelaunch_failure(bad_contract=True)
        self.assertIn('external capped32', receipt['error'])

    def test_provisional_receipt_is_pinned_before_finish_and_never_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = dict(stage='native', status='completed'); proofs = []
            item = G.provisional_receipt(directory, receipt, proofs)
            before = Path(item['path']).read_bytes()
            class Session:
                def finish(self, status, **kw):
                    self.proofs = kw['proofs']
                    if item not in self.proofs or G.pin(item['path']) != item:
                        raise AssertionError('execution receipt must be immutable proof before finish')
                    return dict(completed=['build'], failures=1, last_sha256='failed-final')
            G.cleanup_and_close(Session(), receipt, proofs, True)
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['status_source'], 'sealed-budget-ledger')
            self.assertEqual(receipt['ledger_final_sha256'], 'failed-final')
            self.assertEqual(Path(item['path']).read_bytes(), before)
            self.assertEqual(json.loads(before)['status'], 'provisional-awaiting-accounting')


if __name__ == '__main__':
    unittest.main()
