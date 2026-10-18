"""Artificial JSON capture tests only: no real arrays, models, or engine calls."""
import ast
import copy
from pathlib import Path
import unittest

import real_ir_adapter as A
import real_ir_transfer_data as D


def raw_row(code='FAKE_EVENT', *, kind='unit', zone='anyAttackable', op='damage', amount=2, profile=None):
    card = dict(title='Artificial', subtitle='', text='', cost=1, hp=None, power=None,
        types=['event'], aspects=[], traits=[], keywords=[], unique=False, upgradePower=None, upgradeHp=None)
    abilities = dict(card=[dict(trigger='event', title='Artificial test effect', costs=[],
        targetResolver=dict(owner='any', type=kind, zone=zone),
        effect=dict(kind=op, target='chosen', amount=dict(kind='const', value=amount)))], unit=[], leader=[])
    if profile:
        card.update(profile); abilities['card'] = []
    source_class = {'event': 'EventCard', 'unit': 'NonLeaderUnitCard', 'base': 'BaseCard'}[card['types'][0]]
    return dict(setCode=code, id='artificial-' + code, status='supported', baseClass=source_class,
        card=card, abilities=abilities, keywordValues={}, attachCondition=None,
        requiredCapabilities=['cardType:' + card['types'][0]] + ([] if profile else ['trigger:event', 'targetType:' + kind,
            'targetZone:' + zone, 'ir:const', 'ir:' + op]))


def fixture(*, kind='unit', zone='anyAttackable', op='damage', amount=2, role='p1_ground', healthy=False, cancel=True):
    source = raw_row(kind=kind, zone=zone, op=op, amount=amount)
    ground = raw_row('FAKE_G', profile=dict(types=['unit'], arena='ground', hp=8, power=8, cost=7))
    space = raw_row('FAKE_S', profile=dict(types=['unit'], arena='space', hp=10, power=4, cost=6))
    base = raw_row('FAKE_BASE', profile=dict(types=['base'], hp=30, power=None, cost=None))
    catalogue = {r['setCode']: r for r in (source, ground, space, base)}
    refs = dict(source='source'); projections = dict(source=dict(id='source', code='FAKE_EVENT', owner='p1', zone='hand',
        present=True, is_unit=False, is_base=False, known=dict(identity=True, owner=True, hp=False, damage=False)))
    players = {p: dict(deck=[], hand=[], resources=[], ground=[], space=[], discard=[]) for p in ('p1', 'p2')}
    players['p1']['hand'] = [dict(id='source')]
    players['p1']['resources'] = [dict(id='resource-' + str(i)) for i in range(12)]; specs = {}
    for i, name in enumerate(D.ROLES):
        owner = 'p1' if name.startswith('p1_') or name == 'own_base' else 'p2'
        unit = i < 4; arena = ('ground' if i < 2 else 'space') if unit else 'base'
        row = ground if arena == 'ground' else space if arena == 'space' else base
        physical = 'id-' + name; refs[name] = physical
        damage = (3 if arena == 'ground' else 5) if not (healthy and name == role) else 0
        p = dict(id=physical, code=row['setCode'], owner=owner, zone=arena, present=True,
            is_unit=unit, is_base=not unit, in_arena=unit, attackable=True,
            damage=damage, hp=row['card']['hp'], power=row['card']['power'], printed_cost=row['card']['cost'],
            exhausted=False, shield_count=0, xp_count=0,
            known=dict(identity=True, owner=True, damage=True, hp=True, printed_cost=unit))
        projections[name] = p
        if unit:
            players[owner][arena].append(dict(id=physical))
            specs[name] = dict(code=row['setCode'], owner=owner, arena=arena, damage=damage, exhausted=False)
        else: players[owner]['base'] = dict(id=physical)
    play = dict(kind='play', card='source')
    before = dict(decision='Window', settled=True, state=dict(players=players), projections=projections, offeredActions=[play])
    prompt = copy.deepcopy(before); prompt.update(decision='AbilityTarget', settled=False)
    available = list(D.ROLES) if kind == 'any' and zone == 'anyAttackable' else list(D.ROLES[4:]) if zone == 'base' else list(D.ROLES[:4])
    prompt['offeredActions'] = [dict(kind='choose', card=refs[r]) for r in available]
    decline = dict(kind='button', arg='cancel', label='Cancel')
    if cancel: prompt['offeredActions'].append(decline)
    offered = role in available; target_action = dict(kind='choose', card=refs[role]) if offered else None
    steps = [dict(stage='play-own-hand', before=before, action=play, after=prompt)]
    final = copy.deepcopy(prompt); final.update(decision='Window', settled=True, offeredActions=[])
    final['projections']['source']['zone'] = 'discard' if offered else 'hand'
    if offered:
        old = projections[role]['damage']; final['projections'][role]['damage'] = old + amount if op == 'damage' else max(0, old - amount)
        steps.append(dict(stage='chosen-target', before=prompt, action=target_action, after=final))
        terminal, resolution, completion = 'settled-committed', 'committed', 'settled'
    elif cancel:
        steps.append(dict(stage='decline-unoffered-target', before=prompt, action=decline, after=final))
        terminal, resolution, completion = 'settled-cancelled', 'unoffered-declined', 'settled'
    else:
        final = None; terminal = 'unoffered-prompt-only'; resolution = completion = 'unoffered-observation-only'
    case = dict(world_id=0, card='FAKE_EVENT', program_index=0, root_variant=0, partition='train', refs=refs,
        declared_intent=dict(ref=role, id=refs[role], requires_target=True), observation_refs=list(D.ROLES),
        before=before, publicSnapshotRoundtripExact=True, playAction=play, targetPrompt=prompt, targetAction=target_action,
        declineAction=decline if cancel and not offered else None, steps=steps, final=final, lastObserved=steps[-1]['after'],
        intentOffered=offered, intendedTargetCommitted=offered, terminalClassification=terminal,
        intentResolution=resolution, completion=completion, engineError=None, applyCalls=len(steps))
    world = dict(id=0, source_code='FAKE_EVENT', arena_cards=specs, own_base_damage=projections['own_base']['damage'],
                 opponent_base_damage=projections['opponent_base']['damage'])
    return case, world, catalogue


class ListOnlyNP:
    """Array constructor stand-in: returns JSON lists, not numerical arrays."""
    float32 = 'float32'
    int64 = 'int64'

    @staticmethod
    def asarray(value, dtype=None): return copy.deepcopy(value)

    @staticmethod
    def arange(value, dtype=None): return list(range(value))

    @staticmethod
    def ones(shape, dtype=None): return [[1.] * shape[1] for _ in range(shape[0])]


def artificial_cohort():
    descriptions = [('heal', 5, 'unit', 'anyAttackable'), ('heal', 2, 'unit', 'anyAttackable'),
        ('damage', 3, 'unit', 'anyAttackable'), ('damage', 4, 'unit', 'anyAttackable'),
        ('damage', 2, 'any', 'base'), ('heal', 3, 'any', 'anyAttackable'), ('damage', 2, 'any', 'anyAttackable')]
    programs, cases, worlds, catalogue = [], [], [], {}
    intents = [*D.ROLES, 'p1_ground', 'own_base']
    for q, (code, (op, amount, kind, zone)) in enumerate(zip([*D.TRAIN, *D.HELD], descriptions)):
        source = raw_row(code, kind=kind, zone=zone, op=op, amount=amount); catalogue[code] = source
        programs.append(dict(index=q, code=code, raw_card=source, canonical_program=A.adapt_row(source)['canonical_program'],
                             partition='train' if q < 5 else 'held'))
        for variant, intent in enumerate(intents):
            case, world, entries = fixture(kind=kind, zone=zone, op=op, amount=amount, role=intent, healthy=variant >= 6)
            catalogue.update({k: v for k, v in entries.items() if k != 'FAKE_EVENT'})
            case.update(world_id=q * 8 + variant, card=code, program_index=q, root_variant=variant,
                        partition=programs[-1]['partition'])
            world.update(id=q * 8 + variant, source_code=code, program_index=q, root_variant=variant,
                         partition=case['partition'], intent_ref=intent)
            for capture in [case['before'], case['targetPrompt'], case['final'], case['lastObserved'],
                            *[s[k] for s in case['steps'] for k in ('before', 'after')]]:
                if capture is not None: capture['projections']['source']['code'] = code
            cases.append(case); worlds.append(world)
    plan = dict(schema='jepa-real-ir-transfer-plan/1', synthetic=False, source_revision='toy-source',
        programs=programs, worlds=worlds, candidate_order=list(D.ROLES), selected_whole_rows=catalogue,
        selected_whole_cards=sorted(catalogue))
    validation = [dict(world_id=i, card=c['card'], before=c['before'], publicSnapshotRoundtripExact=True,
        legalActionsRoundtripExact=True, allProgramsAdmitted=True, applyCalls=0, actionsApplied=0) for i, c in enumerate(cases)]
    receipt = dict(schema='jepa-real-ir-transfer-native/1', synthetic=False, collectionComplete=True,
        collectionPlan=plan, collectionPlanSha256='toy-plan-byte-pin', programs=programs,
        candidateOrder=list(D.ROLES), sourceRevision='toy-source', cases=cases, fixtureValidation=validation, applyCalls=112,
        realCatalogueRowsUnchanged=True)
    records = [dict(schema='jepa-real-ir-transfer-apply-journal/1', planSha256='toy-plan-byte-pin',
                    sourceRevision='toy-source', maxApplyCalls=168, expectedCases=56)]
    call = 0
    for case in cases:
        context = 'world-' + str(case['world_id']) + '-' + case['card']
        for step in case['steps']:
            call += 1
            records.extend([dict(phase='beforeApply', applyCall=call, context=context, branch=step['stage'],
                before=step['before'], offeredAction=step['action']), dict(phase='afterApply', applyCall=call,
                context=context, branch=step['stage'], after=step['after'])])
        records.append(dict(phase='contextComplete', case=case))
    return plan, receipt, records


class Tests(unittest.TestCase):
    def program(self, **kwargs):
        adapted = A.adapt_row(raw_row(**kwargs)); self.assertTrue(adapted['full_card_supported'])
        return adapted['canonical_program']

    def test_import_no_numerical_or_engine_dependencies(self):
        tree = ast.parse(Path(D.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'copy', 'hashlib', 'json', 'math', 'real_ir_adapter', 'real_ir_reservation_v3'})
        self.assertFalse(any(isinstance(n, ast.ImportFrom) for n in ast.walk(tree)))
        self.assertNotIn('np', vars(D))

    def test_program13_keeps_union_as_allowed_sets_and_unbounded_literals(self):
        unit = self.program(); union = self.program(kind='any', amount=4); base = self.program(kind='any', zone='base')
        u, a, b = (D.encode_program(p) for p in (unit, union, base))
        self.assertEqual(len(a), 13); self.assertEqual(u[2:5], [1., 1., 0.]); self.assertEqual(a[2:5], [1., 1., 1.])
        self.assertEqual(a[5:8], [1., 1., 1.]); self.assertEqual(b[5:8], [0., 0., 1.])
        self.assertEqual(a[8:10], [0., 0.]); self.assertEqual(a[-1], 4.)
        capped = copy.deepcopy(unit); capped['selector']['cost_cap'] = dict(present=True, value=7)
        self.assertEqual(D.encode_program(capped)[8:10], [1., 7.])
        restricted = copy.deepcopy(unit); restricted['selector']['arena'] = dict(present=True, values=['space'])
        self.assertEqual(D.encode_program(restricted)[5:8], [0., 1., 0.])

    def test_initial_task_rejects_trigger_protocol_and_extra_control_semantics(self):
        p = self.program()
        for key, value in (('trigger', 'whenPlayed'), ('optional', True), ('coordinate', True)):
            bad = copy.deepcopy(p); bad[key] = value
            with self.assertRaisesRegex(ValueError, 'complete simple event'): D.encode_program(bad)
        bad = copy.deepcopy(p); bad['selector']['count'] = 2
        with self.assertRaisesRegex(ValueError, 'selection'): D.encode_program(bad)

    def test_candidate17_natural_physics_and_base_cost_applicability(self):
        case, _, catalogue = fixture(); features, records, audit = D.public_scene(case, D.ROLES, catalogue)
        self.assertEqual(len(features[0]), 17); self.assertEqual(features[0][9:16], [7., 1., 1., 3., 1., 8., 1.])
        self.assertEqual(features[4][9:16], [0., 0., 0., 5., 1., 30., 1.])
        self.assertIsNone(records[4]['printed_cost']); self.assertFalse(records[4]['cost_applicable'])
        self.assertEqual(audit['original_sha256'], audit['renamed_sha256']); self.assertTrue(audit['invariant'])
        poisoned = copy.deepcopy(case); poisoned['final'] = {'poison': True}; poisoned['targetPrompt'] = {'poison': True}
        self.assertEqual(D.public_scene(poisoned, D.ROLES, catalogue)[0], features)

    def test_unknown_or_fabricated_base_cost_and_boolean_stats_reject(self):
        case, _, catalogue = fixture(); p = case['before']['projections']['own_base']
        for key, value in (('printed_cost', 0), ('damage', True), ('hp', float('nan'))):
            changed = copy.deepcopy(p); changed[key] = value
            with self.assertRaises(ValueError): D.encode_candidate(changed, case['declared_intent']['id'], 'p1', catalogue['FAKE_BASE'])
        p = copy.deepcopy(case['before']['projections']['p1_ground']); p['known']['damage'] = False
        with self.assertRaisesRegex(ValueError, 'complete known'): D.encode_candidate(p, p['id'], 'p1', catalogue['FAKE_G'])
        p = copy.deepcopy(case['before']['projections']['p1_ground']); p['printed_cost'] = 2
        with self.assertRaisesRegex(ValueError, 'intact public row'): D.encode_candidate(p, p['id'], 'p1', catalogue['FAKE_G'])

    def test_typed_reference_unit_base_union_and_clipped_heal(self):
        case, _, catalogue = fixture(role='own_base'); _, candidates, _ = D.public_scene(case, D.ROLES, catalogue)
        unit = D.reference(self.program(kind='unit'), candidates)
        base = D.reference(self.program(kind='any', zone='base'), candidates)
        union = D.reference(self.program(kind='any'), candidates)
        self.assertEqual([p[0] for p in unit], [1.] * 4 + [0., 0.])
        self.assertEqual([p[0] for p in base], [0.] * 4 + [1., 1.])
        self.assertEqual([p[0] for p in union], [1.] * 6); self.assertEqual(union[4][1], 2.)
        heal = self.program(kind='any', op='heal', amount=5)
        candidates[4]['damage'] = 1; self.assertEqual(D.reference(heal, candidates)[4][1], -1.)
        candidates[4]['damage'] = 0; self.assertEqual(D.reference(heal, candidates)[4][1], 0.)
        candidates[4]['damage'] = 5; self.assertEqual(D.reference(heal, candidates)[4][1], -5.)

    def test_native_observations_only_intended_future_known(self):
        case, _, _ = fixture(amount=2); result = D.derive_labels(case, D.ROLES)
        j = result['selected']; self.assertEqual(result['targets'][j], [1., 2.]); self.assertEqual(result['target_mask'][j], [1., 1.])
        self.assertTrue(all(mask == [1., 0.] for k, mask in enumerate(result['target_mask']) if k != j))
        case['final']['projections'][D.ROLES[j]]['damage'] += 1
        self.assertEqual(D.derive_labels(case, D.ROLES)['targets'][j][1], 3.)  # independent native evidence, not reference replacement

    def test_native_healthy_heal_is_observed_zero_and_unoffered_future_unknown(self):
        for role in ('p1_ground', 'own_base'):
            case, _, _ = fixture(kind='any', op='heal', amount=3, role=role, healthy=True)
            result = D.derive_labels(case, D.ROLES)
            self.assertEqual(result['targets'][result['selected']], [1., 0.]); self.assertEqual(result['target_mask'][result['selected']], [1., 1.])
        for cancel in (True, False):
            case, _, _ = fixture(kind='unit', role='own_base', cancel=cancel)
            result = D.derive_labels(case, D.ROLES)
            self.assertEqual(result['targets'][4][0], 0.); self.assertTrue(all(mask[1] == 0. for mask in result['target_mask']))

    def test_unoffered_substitution_unsettled_or_unselected_side_effect_reject(self):
        for mutate in (lambda c: c['steps'][1].update(action=dict(card='unoffered')),
                       lambda c: c['final'].update(settled=False),
                       lambda c: c['final']['projections']['p2_space'].update(damage=6)):
            case, _, _ = fixture(); mutate(case)
            with self.assertRaises(ValueError): D.derive_labels(case, D.ROLES)

    def test_fixture_checks_real_natural_stats_privacy_and_live_damage4_support(self):
        case, world, catalogue = fixture(); D.fixture_proof(case, world, D.ROLES, catalogue)
        bad = copy.deepcopy(case); bad['before']['projections']['p1_ground']['hp'] = 10
        with self.assertRaisesRegex(ValueError, 'natural unit'): D.fixture_proof(bad, world, D.ROLES, catalogue)
        bad = copy.deepcopy(case); bad['before']['state']['players']['p2']['hand'] = [dict(id='hidden')]
        with self.assertRaisesRegex(ValueError, 'private'): D.fixture_proof(bad, world, D.ROLES, catalogue)

    def test_printed_control_only_ten_declared_values(self):
        adapted = A.adapt_row(raw_row()); vector = D.encode_printed(adapted)
        self.assertEqual(vector, [1., 1., 0., 0., 0., 0., 0., 1., 0., 0.])
        changed = copy.deepcopy(adapted); changed['raw_row']['card']['title'] = 'Secret spelling'
        self.assertEqual(D.encode_printed(changed), vector)

    def test_journal_exact_pairs_and_error_events_reject(self):
        case, _, _ = fixture(); receipt = dict(collectionPlanSha256='plan', sourceRevision='source', cases=[case], applyCalls=2)
        records = [dict(schema='jepa-real-ir-transfer-apply-journal/1', planSha256='plan', sourceRevision='source', maxApplyCalls=168, expectedCases=56)]
        for i, step in enumerate(case['steps'], 1):
            records.extend([dict(phase='beforeApply', applyCall=i, context='world-0-FAKE_EVENT', branch=step['stage'], before=step['before'], offeredAction=step['action']),
                            dict(phase='afterApply', applyCall=i, context='world-0-FAKE_EVENT', branch=step['stage'], after=step['after'])])
        records.append(dict(phase='contextComplete', case=case))
        self.assertEqual(D.journal_proof(records, receipt)['native_applies'], 2)
        broken = copy.deepcopy(records); broken[2]['phase'] = 'applyError'
        with self.assertRaisesRegex(ValueError, 'boundary'): D.journal_proof(broken, receipt)

    def test_entire_artificial56_case_flow_without_numpy_or_real_rows(self):
        plan, receipt, journal = artificial_cohort()
        arrays, manifest = D.prepare_data(ListOnlyNP, plan, receipt, journal)
        self.assertTrue(manifest['fit_admitted'], manifest['fit_blockers'])
        self.assertEqual(len(arrays['program_features']), 7); self.assertEqual(len(arrays['program_features'][0]), 13)
        self.assertEqual(len(arrays['source_printed_features'][0]), 10)
        self.assertEqual(len(arrays['candidate_features']), 56); self.assertEqual(len(arrays['candidate_features'][0][0]), 17)
        self.assertEqual((len(arrays['train_idx']), len(arrays['held_idx'])), (40, 16))
        self.assertEqual(arrays['target_mask'], arrays['primary_target_mask'])
        self.assertEqual(manifest['reference']['known_eligibility'], 336)
        self.assertEqual(manifest['reference']['known_intended_deltas'], 39)
        self.assertEqual(manifest['reference']['mismatch_count'], 0)
        self.assertEqual(manifest['support']['train']['target_damage_delta']['known'], 23)
        self.assertEqual(manifest['support']['held']['target_damage_delta']['known'], 16)
        self.assertEqual(manifest['support']['held']['target_allowed']['zero'], 0)
        self.assertIsNone(manifest['held_eligibility']['balanced_accuracy'])
        self.assertEqual(len(manifest['mechanism_groups']['train']), 3)
        self.assertEqual(len(manifest['mechanism_groups']['held']), 2)
        self.assertEqual(manifest['input_conflicts']['count'], 0)
        self.assertGreater(manifest['numeric_printed_control_input_conflicts']['count'], 0)

    def test_artificial_pipeline_reference_mismatch_blocks_fit_without_relabeling(self):
        plan, receipt, journal = artificial_cohort()
        case = receipt['cases'][40]; role = case['declared_intent']['ref']
        case['final']['projections'][role]['damage'] += 1
        arrays, manifest = D.prepare_data(ListOnlyNP, plan, receipt, journal)
        self.assertFalse(manifest['fit_admitted']); self.assertIn('native-reference-mismatch', manifest['fit_blockers'])
        self.assertEqual(arrays['targets'][40][0][1], -2.)
        self.assertEqual(arrays['baseline_predictions'][40][0][1], -3.)


if __name__ == '__main__': unittest.main()
