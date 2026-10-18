"""Primitive artificial dictionaries only; no arrays, model or native execution."""
import ast
import copy
import itertools
from pathlib import Path
import unittest

import compositional_typed_data as D


ROLES = tuple(owner + '_' + arena + '_' + suffix
              for owner, arena in itertools.product(('p1', 'p2'), ('ground', 'space'))
              for suffix in ('c2a', 'c2b', 'c3', 'c4'))


def program(bits):
    f = D.factors_from_bits(bits)
    ability = dict(trigger='event', title='Elementary effect', costs=[], targetResolver=dict(
        owner=f['owner'], type='unit', zone='arena', arena=f['arena'], predicate=dict(
            kind='binary', op='<=', left=dict(kind='ref', path=['card', 'cost']),
            right=dict(kind='const', value=f['cap']))),
        effect=dict(kind=f['op'], target='chosen', amount=dict(kind='const', value=f['amount'])))
    return dict(code='OPAQUE', bits=bits, factors=f, synthetic=True,
                raw_card=dict(card=dict(id='opaque', setCodes=['OPAQUE']),
                              abilities=dict(card=[ability], unit=[], leader=[])))


def fixture(intent='p2_ground_c2a', heal=False, healthy=False, cancel=False, prompt_only=False):
    refs = dict(source='source-id', own_base='base-p1', opponent_base='base-p2')
    projections = dict(source=dict(id=refs['source'], code='OPAQUE', owner='p1', zone='hand',
                                  known=dict(identity=True, owner=True)))
    players = {seat: dict(deck=[], hand=[], resources=[], ground=[], space=[]) for seat in ('p1', 'p2')}
    players['p1']['hand'] = [dict(id=refs['source'])]
    specs = {}
    for i, role in enumerate(ROLES):
        owner, arena, suffix = role.split('_'); cost = int(suffix[1]); physical = 'unit-' + str(i)
        damage = 0 if healthy and role == intent else (3 if suffix in ('c2a', 'c4') else 1)
        p = dict(id=physical, code='PUBLIC-' + str(i), present=True, is_unit=True,
                 in_arena=True, owner=owner, zone=arena, printed_cost=cost,
                 damage=damage, hp=10, power=0, known={k: True for k in D.KNOWN})
        refs[role] = physical; projections[role] = p; players[owner][arena].append(dict(id=physical))
        specs[role] = dict(code=p['code'], owner=owner, arena=arena, cost=cost, printed_cost=cost, damage=damage)
    play = dict(kind='play', card=refs['source'])
    before = dict(decision='Window', projections=projections, state=dict(players=players),
                  offeredActions=[play], settled=True)
    prompt = copy.deepcopy(before); prompt['decision'] = 'AbilityTarget'; prompt['settled'] = False
    prompt['offeredActions'] = [dict(kind='choose', card=refs[r]) for r in ROLES
        if r.startswith('p2_ground_') and projections[r]['printed_cost'] <= 2]
    decline = dict(kind='button', arg='cancel', label='Cancel')
    allowed = any(a.get('card') == refs[intent] for a in prompt['offeredActions'])
    if cancel:
        prompt['offeredActions'].append(decline)
    steps = [dict(stage='play-own-hand', before=before, action=play, after=prompt)]
    final = copy.deepcopy(prompt); final.update(decision='Window', offeredActions=[], settled=True)
    action = dict(kind='choose', card=refs[intent]) if allowed else None
    if allowed:
        p = final['projections'][intent]
        p['damage'] = max(0, p['damage'] - 3) if heal else p['damage'] + 3
        steps.append(dict(stage='chosen-target', before=prompt, action=action, after=final))
        terminal, resolution, completion = 'settled-committed', 'committed', 'settled'
    elif cancel:
        steps.append(dict(stage='decline-unoffered-target', before=prompt, action=decline, after=final))
        terminal, resolution, completion = 'settled-cancelled', 'unoffered-declined', 'settled'
    else:
        assert prompt_only
        final = None
        terminal, resolution, completion = 'unoffered-prompt-only', 'unoffered-observation-only', 'unoffered-observation-only'
    case = dict(world_id=0, card='OPAQUE', program_index=0, root_variant=0, partition='train',
        refs=refs, declared_intent=dict(ref=intent, id=refs[intent], requires_target=True),
        before=before, publicSnapshotRoundtripExact=True, steps=steps, playAction=play,
        targetPrompt=prompt, targetAction=action, declineAction=decline if cancel else None,
        lastObserved=steps[-1]['after'], final=final, intentOffered=allowed,
        intendedTargetCommitted=allowed, terminalClassification=terminal,
        intentResolution=resolution, completion=completion, engineError=None, applyCalls=len(steps))
    world = dict(id=0, source_code='OPAQUE', arena_cards=specs, intent_ref=intent)
    return case, world


class PrimitiveDataTest(unittest.TestCase):
    def test_import_has_only_standard_library_dependencies(self):
        tree = ast.parse(Path(D.__file__).read_text())
        imports = {a.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names}
        self.assertEqual(imports, {'copy', 'hashlib', 'itertools', 'json', 'math'})
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))
        self.assertNotIn('np', vars(D))

    def test_features_have_only_known_public_before_fields(self):
        case, world = fixture(); rows, record = D.public_inputs(case, ROLES)
        self.assertEqual(len(rows), 16); self.assertTrue(all(len(r) == 8 for r in rows))
        self.assertEqual(sum(r[7] for r in rows), 1)
        self.assertEqual(record['candidates'][8]['arena'], 'ground')
        self.assertEqual(set(record['candidates'][8]), {'owner', 'arena', 'printed_cost', 'damage', 'hp', 'is_intended', 'known'})
        self.assertTrue(D.fixture_proof(case, world, ROLES)['empty_private_piles'])

    def test_unknown_nonfinite_boolean_or_dead_fields_fail_closed(self):
        case, _ = fixture(); p = case['before']['projections'][ROLES[0]]
        for key in D.KNOWN:
            changed = copy.deepcopy(p); changed['known'][key] = False
            with self.assertRaisesRegex(ValueError, 'unknown'): D.candidate(changed, p['id'], 'p1')
        for key, value in (('printed_cost', True), ('damage', float('nan')), ('hp', float('inf')), ('damage', 10)):
            changed = copy.deepcopy(p); changed[key] = value
            with self.assertRaises(ValueError): D.candidate(changed, p['id'], 'p1')

    def test_identity_menu_future_private_poison_is_input_invariant(self):
        case, _ = fixture(); audit = D.identity_audit(case, ROLES)
        self.assertEqual(audit['original_sha256'], audit['renamed_sha256'])
        self.assertTrue(audit['physical_id_and_code_renaming_invariant'])
        self.assertTrue(audit['menu_future_private_poison_invariant'])

    def test_program_strict_parse_ignores_code_not_operators(self):
        p = program([1, 0, 1, 1, 0]); fields = D.program_fields(p)
        self.assertEqual(fields, [0., 1., 1., 0., 3., 1., 0., 3.])
        alias = copy.deepcopy(p); alias['code'] = 'RENAMED'; alias['raw_card']['card']['id'] = 'new-id'
        self.assertEqual(D.program_fields(alias), fields)
        for change in ('unknown', 'amount_boolean', 'wrong_operation'):
            bad = copy.deepcopy(p); ability = bad['raw_card']['abilities']['card'][0]
            if change == 'unknown': ability['condition'] = dict(kind='const', value=True)
            elif change == 'amount_boolean': ability['effect']['amount']['value'] = True
            else: ability['effect']['kind'] = 'heal'
            with self.assertRaisesRegex(ValueError, 'strict grammar'): D.program_fields(bad)

    def test_parity_is_whole_program_and_balances_atoms_and_pairs(self):
        programs = [program(list(b)) for b in itertools.product((0, 1), repeat=5)]
        report = D.split_report(programs)
        self.assertEqual(report['train']['programs'], 16)
        self.assertTrue(all(v == [8, 8] for v in report['held']['atom_counts'].values()))
        self.assertTrue(all(v == [4, 4, 4, 4] for v in report['held']['pair_counts'].values()))
        programs[-1] = copy.deepcopy(programs[0])
        with self.assertRaisesRegex(ValueError, 'complete unique'): D.split_report(programs)

    def test_primitive_crosses_owner_arena_cost_and_clips_healthy_heal(self):
        case, _ = fixture(); rows, _ = D.public_inputs(case, ROLES); q = ROLES.index('p2_ground_c2a')
        f = dict(owner='opponent', arena='ground', cap=2, amount=3, op='damage')
        pred = D.primitive(f, rows, q)
        self.assertEqual(sum(r[0] for r in pred), 2)
        self.assertEqual(pred[q], [1., 3.]); self.assertEqual(pred[q + 1], [1., 0.])
        rows[q][5] = 1.; f['op'] = 'heal'
        self.assertEqual(D.primitive(f, rows, q)[q], [1., -1.])
        rows[q][5] = 0.
        self.assertEqual(D.primitive(f, rows, q)[q], [1., 0.])

    def test_native_membership_and_damage_are_observed_not_primitive_labels(self):
        case, _ = fixture(); q = ROLES.index(case['declared_intent']['ref'])
        case['final']['projections'][ROLES[q]]['damage'] += 1  # Deliberate native/comparator disagreement.
        out = D.derive_labels(case, ROLES)
        self.assertEqual(out['targets'][q], [1., 4.]); self.assertEqual(out['target_mask'][q], [1., 1.])
        self.assertEqual(sum(r[0] for r in out['targets']), 2)
        self.assertTrue(all(r[1] == 1. for r in out['target_mask']))

    def test_healthy_heal_known_zero_is_not_excluded(self):
        case, _ = fixture(heal=True, healthy=True); out = D.derive_labels(case, ROLES)
        q = out['selected']; self.assertEqual(out['targets'][q], [1., 0.])
        self.assertEqual(out['target_mask'][q], [1., 1.])

    def test_invalid_cancel_and_prompt_only_have_no_future_labels(self):
        for cancel in (True, False):
            case, _ = fixture(intent='p2_space_c2a', cancel=cancel, prompt_only=not cancel)
            out = D.derive_labels(case, ROLES)
            self.assertEqual(out['targets'][out['selected']][0], 0.)
            self.assertTrue(all(row == [1., 0.] for row in out['target_mask']))
            self.assertFalse(out['committed'])

    def test_unoffered_selection_and_fabricated_cancel_rejected(self):
        case, _ = fixture(); case['steps'][1]['action'] = dict(kind='choose', card='not-offered')
        with self.assertRaisesRegex(ValueError, 'unoffered'): D.derive_labels(case, ROLES)
        case, _ = fixture(intent='p2_space_c2a', prompt_only=True)
        case['targetPrompt']['offeredActions'].append(dict(arg='cancel', label='Cancel'))
        with self.assertRaisesRegex(ValueError, 'invent Cancel'): D.derive_labels(case, ROLES)

    def test_hidden_or_unrepresented_units_reject_fixture(self):
        for field in ('hand', 'deck', 'resources', 'ground'):
            case, world = fixture(); case['before']['state']['players']['p2'][field].append(dict(id='extra-private-or-unrepresented'))
            with self.assertRaises(ValueError): D.fixture_proof(case, world, ROLES)


if __name__ == '__main__':
    unittest.main()
