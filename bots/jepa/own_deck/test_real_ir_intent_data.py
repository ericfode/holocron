"""Artificial JSON/list-only data regressions; no real outcomes or arrays."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import real_ir_intent_data as I
import real_ir_hp_projection_data as H
from test_real_ir_transfer_data import ListOnlyNP, fixture, raw_row
from test_real_ir_hp_projection_data import artificial_saved_pair


DESCRIPTIONS = [('heal', 5, 'unit', 'anyAttackable'), ('heal', 2, 'unit', 'anyAttackable'),
    ('damage', 3, 'unit', 'anyAttackable'), ('damage', 4, 'unit', 'anyAttackable'),
    ('damage', 2, 'any', 'base'), ('heal', 3, 'any', 'anyAttackable'), ('damage', 2, 'any', 'anyAttackable')]


def terminal_row():
    row = raw_row(I.TERMINAL, kind='unit', zone='arena', op='damage', amount=3)
    row['baseClass'] = 'NonLeaderUnitCard'
    row['card'].update(types=['unit'], arena='space', hp=2, power=3, cost=4)
    row['abilities']['card'][0].update(trigger='whenPlayed', optional=True)
    row['abilities']['card'][0]['targetResolver']['arena'] = 'space'
    row['requiredCapabilities'] = ['cardType:unit', 'trigger:whenPlayed', 'targetType:unit', 'targetZone:arena', 'ir:const', 'ir:damage']
    return row


def grid_case(code, description, variant, terminal=False, decline=True):
    op, amount, kind, zone = description
    own = variant % 4 in (0, 2); role = ('p1_space' if own else 'p2_space') if variant < 4 else ('own_base' if own else 'opponent_base')
    sample, _, catalogue = fixture(kind=kind, zone=zone, op=op, amount=amount, role=role)
    source = terminal_row() if terminal else raw_row(code, kind=kind, zone=zone, op=op, amount=amount)
    catalogue.pop('FAKE_EVENT'); catalogue[code] = source
    before = copy.deepcopy(sample['before']); refs = sample['refs']; level = (0, 1, 4, 6)[variant % 4]
    before['projections']['source']['code'] = code
    before['projections']['source'].update(is_unit=terminal)
    specs = {}
    for q, r in enumerate(I.D.ROLES):
        p = before['projections'][r]
        p['damage'] = 1 if level == 0 and r in ('p2_space', 'opponent_base') else level
        if q < 4: specs[r] = dict(code=p['code'], owner=p['owner'], arena=p['zone'], damage=p['damage'], exhausted=False)
    prompt = copy.deepcopy(before); prompt.update(decision='AbilityTarget', settled=False)
    if terminal:
        prompt['projections']['source'].update(zone='space', in_arena=True, exhausted=True, hp=2, power=3, damage=0)
        prompt['projections']['source']['known']['exhausted'] = True
        prompt['state']['players']['p1']['hand'] = []
        prompt['state']['players']['p1']['space'].append(dict(id=refs['source']))
    available = list(I.D.ROLES[2:4]) if terminal else list(I.D.ROLES) if kind == 'any' and zone == 'anyAttackable' else list(I.D.ROLES[4:]) if zone == 'base' else list(I.D.ROLES[:4])
    prompt['offeredActions'] = [dict(kind='choose', card=refs[r]) for r in available]
    if terminal: prompt['offeredActions'].append(dict(kind='choose', card=refs['source']))
    decline_action = dict(kind='button', arg='passAbility' if terminal else 'cancel', label='Pass' if terminal else 'Cancel')
    if decline: prompt['offeredActions'].append(decline_action)
    offered = role in available; action = dict(kind='choose', card=refs[role]) if offered else decline_action if decline else None
    steps = [dict(stage='play-own-hand', before=before, action=before['offeredActions'][0], after=prompt)]
    final = None
    if action is not None:
        final = copy.deepcopy(prompt); final.update(decision='Window', settled=True, offeredActions=[])
        if not terminal: final['projections']['source']['zone'] = 'discard' if offered else 'hand'
        if offered:
            p = final['projections'][role]; p['damage'] += amount if op == 'damage' else -min(amount, p['damage'])
            if p['is_unit'] and p['damage'] >= p['hp']:
                final['state']['players'][p['owner']][p['zone']] = [c for c in final['state']['players'][p['owner']][p['zone']] if c['id'] != p['id']]
                p.update(zone='discard', in_arena=False, attackable=False, damage=None, hp=None)
                p['known'].update(damage=False, hp=False)
        steps.append(dict(stage='chosen-target' if offered else 'decline-unoffered-optional' if terminal else 'decline-unoffered-target', before=prompt, action=action, after=final))
    case = dict(sample, card=code, before=before, root_variant=variant, playAction=before['offeredActions'][0], targetPrompt=prompt,
        targetAction=action if offered else None, declineAction=action if not offered else None, steps=steps, final=final,
        lastObserved=final if final is not None else prompt, intentOffered=offered, intendedTargetCommitted=offered,
        terminalClassification='settled-committed' if offered else 'settled-declined' if decline else 'unoffered-prompt-only',
        completion='settled' if action is not None else 'unoffered-observation-only',
        intentResolution='committed' if offered else 'unoffered-declined' if decline else 'unoffered-observation-only', applyCalls=len(steps))
    case['declared_intent'] = dict(ref=role, id=refs[role], requires_target=True)
    world = dict(id=0, source_code=code, root_variant=variant, program_index=0, intent_ref=role,
        arena_cards=specs, own_base_damage=before['projections']['own_base']['damage'], opponent_base_damage=before['projections']['opponent_base']['damage'])
    return case, world, catalogue


def artificial_panel(terminal=False):
    programs, cases, worlds, catalogue = [], [], [], {}
    definitions = [(I.TERMINAL, ('damage', 3, 'unit', 'arena'))] if terminal else list(zip(I.EVENTS, DESCRIPTIONS))
    role = 'terminal' if terminal else 'development'; partition = 'terminal-card' if terminal else 'developmental-state'
    for q, (code, description) in enumerate(definitions):
        for variant in range(8):
            case, world, rows = grid_case(code, description, variant, terminal)
            case.update(world_id=q * 8 + variant, program_index=q, partition=partition)
            world.update(id=q * 8 + variant, program_index=q, partition=partition)
            cases.append(case); worlds.append(world); catalogue.update(rows)
        row = catalogue[code]
        programs.append(dict(index=q, code=code, raw_card=row, canonical_program=I.A.adapt_row(row)['canonical_program'], partition=partition))
    plan = dict(schema='jepa-real-ir-intent-plan/1', panel_role=role, programs=programs, worlds=worlds,
        selected_whole_rows=catalogue, candidate_order=list(I.D.ROLES), source_revision='toy-source', collector_max_engine_applies=40 if terminal else 200)
    validation = [dict(world_id=i, card=c['card'], before=c['before'], publicSnapshotRoundtripExact=True,
        legalActionsRoundtripExact=True, allProgramsAdmitted=True, applyCalls=0, actionsApplied=0) for i, c in enumerate(cases)]
    raw = dict(schema='jepa-real-ir-intent-native/1', collectionComplete=True, collectionPlan=plan, collectionPlanSha256='toy-pin',
        programs=programs, candidateOrder=list(I.D.ROLES), sourceRevision='toy-source', synthetic=False, realCatalogueRowsUnchanged=True,
        cases=cases, fixtureValidation=validation, applyCalls=sum(c['applyCalls'] for c in cases))
    trace = [dict(schema='jepa-real-ir-intent-apply-journal/1', planSha256='toy-pin', sourceRevision='toy-source', expectedCases=len(cases),
        maxApplyCalls=plan['collector_max_engine_applies'], fixtureValidation=validation)]
    counter = 0
    for c in cases:
        context = 'world-' + str(c['world_id']) + '-' + c['card']
        for s in c['steps']:
            counter += 1
            trace.extend([dict(phase='beforeApply', applyCall=counter, context=context, branch=s['stage'], before=s['before'], offeredAction=s['action']),
                dict(phase='afterApply', applyCall=counter, context=context, branch=s['stage'], after=s['after'])])
        trace.append(dict(phase='contextComplete', case=c))
    return plan, raw, trace


class Tests(unittest.TestCase):
    def test_imports_and_calls_are_stdlib_saved_projection_only(self):
        tree = ast.parse(Path(I.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'copy', 'json', 'real_ir_adapter', 'real_ir_transfer_data', 'real_ir_transfer_verify'})
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ('make_model', 'backward', 'fit_head', 'mean', 'std', 'apply', 'worker') for n in ast.walk(tree)))
        self.assertNotIn('np', vars(I))

    def test_event_projection_identical_and_optional_whenplayed_preserved(self):
        event = I.A.adapt_row(raw_row())['canonical_program']
        self.assertEqual(I.project_program(event), I.D.encode_program(event))
        p = I.A.adapt_row(terminal_row())['canonical_program']; saved = copy.deepcopy(p)
        self.assertEqual(I.project_program(p)[2:8], [1., 1., 0., 0., 1., 0.])
        self.assertEqual(p, saved); self.assertEqual(p['trigger'], 'whenPlayed'); self.assertTrue(p['optional'])
        bad = copy.deepcopy(p); bad['coordinate'] = True
        with self.assertRaisesRegex(ValueError, 'unsupported'): I.project_program(bad)

    def test_cancelled_event_hand_and_optional_pass_paid_space(self):
        for terminal in (False, True):
            case, _, rows = grid_case(I.TERMINAL if terminal else 'FAKE_EVENT', ('damage', 3, 'unit', 'arena'), 4, terminal)
            p = I.A.adapt_row(rows[case['card']])['canonical_program']; value = I.derive(case, p)
            self.assertFalse(value['committed']); self.assertTrue(all(m == [1., 0.] for m in value['mask']))
            self.assertEqual(case['final']['projections']['source']['zone'], 'space' if terminal else 'hand')
            bad = copy.deepcopy(case); bad['final']['projections']['source']['zone'] = 'discard'
            with self.assertRaisesRegex(ValueError, 'source disposition'): I.derive(bad, p)
            bad = copy.deepcopy(case); bad['steps'][1]['action']['arg'] = 'invented'
            with self.assertRaises(ValueError): I.derive(bad, p)
            if terminal:
                bad = copy.deepcopy(case); bad['final']['projections']['source']['known']['exhausted'] = False
                with self.assertRaisesRegex(ValueError, 'exhausted'): I.derive(bad, p)

    def test_lethal_counter_unknown_and_physical_removal_separate(self):
        case, world, rows = grid_case('FAKE_EVENT', ('damage', 4, 'unit', 'anyAttackable'), 3)
        I.fixture(case, world, rows); result = I.derive(case, I.A.adapt_row(rows['FAKE_EVENT'])['canonical_program'])
        self.assertTrue(result['removed']); self.assertEqual(result['mask'][3], [1., 0.]); self.assertEqual(result['targets'][3][1], 0.)
        # Stored zero is a masked placeholder; reference remains the literal +4.
        _, records, _ = I.D.public_scene(case, I.D.ROLES, rows)
        self.assertEqual(I.reference(I.A.adapt_row(rows['FAKE_EVENT'])['canonical_program'], records)[3][1], 4.)

    def test_prompt_only_has_no_manufactured_future_or_pass(self):
        case, _, rows = grid_case('FAKE_EVENT', ('damage', 3, 'unit', 'arena'), 4, decline=False)
        p = I.A.adapt_row(rows['FAKE_EVENT'])['canonical_program']; result = I.derive(case, p)
        self.assertFalse(result['committed']); self.assertTrue(all(m[1] == 0. for m in result['mask']))

    def test_full_artificial_panels_reference_masks_and_source_scope(self):
        for terminal, expected in ((False, (371, 35, 1)), (True, (52, 4, 0))):
            p, r, j = artificial_panel(terminal); arrays, manifest = I.panel(p, r, j)
            self.assertEqual(manifest['blockers'], [])
            self.assertEqual(tuple(manifest['reference'][k] for k in ('known_coordinates', 'known_intended_deltas', 'removed_count')), expected)
            self.assertEqual(manifest['reference']['mismatch_count'], 0)
            self.assertTrue(all(len(c) == 6 for c in arrays['targets']))
            if terminal:
                self.assertTrue(all(m['extra_source_offered'] for m in manifest['root_metadata']))
                self.assertEqual([x[0] for x in arrays['targets'][0]], [0., 0., 1., 1., 0., 0.])

    def test_trace_validation_and_native_mismatch_fail_closed(self):
        p, r, j = artificial_panel(); bad = copy.deepcopy(j); bad[0]['fixtureValidation'] = []
        with self.assertRaisesRegex(ValueError, 'fixture/header'): I.panel(p, r, bad)
        bad = copy.deepcopy(j); bad[2]['phase'] = 'applyError'
        with self.assertRaisesRegex(ValueError, 'application pair'): I.panel(p, r, bad)
        p, r, j = artificial_panel(); r['cases'][0]['final']['projections']['p1_space']['damage'] += 1
        arrays, manifest = I.panel(p, r, j)
        self.assertIn('native-reference-mismatch', manifest['blockers']); self.assertEqual(arrays['targets'][0][2][1], 1.)

    def test_complete_mock_saved112_and120_merge_train40_primary29_replay6(self):
        old, om, fresh, fm = artificial_saved_pair(); hp, hm = H.combine(ListOnlyNP, old, om, fresh, fm)
        dp, dr, dj = artificial_panel(); tp, tr, tj = artificial_panel(True)
        datasets = {'/old/prep-1/dataset.npz': old, '/hp/prep-1/dataset.npz': hp}
        docs = {'/old/prep-1/manifest.json': om, '/hp/prep-1/manifest.json': hm,
            '/new/metadata-1/development-plan.json': dp, '/new/metadata-1/terminal-plan.json': tp,
            '/new/dev-native-1/receipt.json': dr, '/new/terminal-native-1/receipt.json': tr,
            '/old/fit-1/loss-weights.json': {'artificial_train_only': True}}
        def fakepin(p): return dict(path=str(p), sha256='toy-pin', bytes=1)
        def fake_npz(np, p): return copy.deepcopy(datasets[str(p)])
        def fakeread(p): return copy.deepcopy(docs[str(p)])
        def faketrace(p): return copy.deepcopy(dj if 'dev-native' in str(p) else tj)
        with patch.object(I.V, 'npz', fake_npz), patch.object(I, 'read', fakeread), patch.object(I.V, 'pin', fakepin), patch.object(I.V, 'rows', faketrace):
            combined, manifest = I.prepare_development(ListOnlyNP, '/old', '/hp', '/new')
            self.assertTrue(manifest['fit_admitted'], manifest['fit_blockers'])
            self.assertEqual(manifest['support'], dict(development_known_endpoints=35, primary=29, replay=6, removed=1))
            self.assertEqual(combined['targets'][:56], old['targets']); self.assertEqual(combined['train_idx'], list(range(40)))
            self.assertEqual(len(combined['program_features']), 8); self.assertEqual(combined['terminal_idx'], [])
            self.assertTrue(all(c == [0., 0.] for row in combined['primary_target_mask'][:56] for c in row))
            datasets['/new/prep-1/dataset.npz'] = combined; docs['/new/prep-1/manifest.json'] = manifest
            final, final_manifest = I.prepare_terminal(ListOnlyNP, '/new')
            self.assertEqual(len(final['targets']), 120); self.assertEqual(final['targets'][:112], combined['targets'])
            self.assertEqual(final['program_indices'][112:], [7] * 8); self.assertEqual(final['train_idx'], list(range(40)))
            self.assertEqual(final['terminal_idx'], list(range(112, 120))); self.assertTrue(final_manifest['terminal_admitted'])
            self.assertEqual(final_manifest['terminal_reference']['known_coordinates'], 52)
            self.assertEqual(len(final_manifest['public_before_records']), 120)
            self.assertTrue(all(c == [0., 0.] for row in final['primary_target_mask'][112:] for c in row))
            docs['/old/prep-1/manifest.json']['reference']['mismatch_count'] = 1
            with self.assertRaisesRegex(ValueError, 'closed original/HP'): I.prepare_development(ListOnlyNP, '/old', '/hp', '/new')


if __name__ == '__main__': unittest.main()
