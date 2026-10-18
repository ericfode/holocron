"""Artificial dictionaries/lists only; no arrays, learner or engine execution."""
import ast
import copy
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest

import compositional_typed_verify as V


def program(bits, index=0):
    f = dict(owner='opponent' if bits[0] else 'any', arena='space' if bits[1] else 'ground',
             cap=3 if bits[2] else 2, amount=3 if bits[3] else 1, op='heal' if bits[4] else 'damage')
    ability = dict(trigger='event', title='Elementary effect', costs=[],
        targetResolver=dict(owner=f['owner'], type='unit', zone='arena', arena=f['arena'],
            predicate=dict(kind='binary', op='<=', left=dict(kind='ref', path=['card', 'cost']),
                           right=dict(kind='const', value=f['cap']))),
        effect=dict(kind=f['op'], target='chosen', amount=dict(kind='const', value=f['amount'])))
    abilities = dict(card=[ability], unit=[], leader=[])
    return dict(index=index, code='opaque-' + str(index), bits=list(bits), factors=f,
        raw_card=dict(card=dict(cost=1, types=['event'], aspects=[], unique=False), abilities=abilities),
        synthetic=True, program_hash=V.digest(abilities), partition='held' if sum(bits) % 2 else 'train')


def good():
    axes = {f'{name}={value}': dict(eligibility=dict(balanced_accuracy=1.)) for name in V.AXES for value in (0, 1)}
    damage = {f'op_heal={op},amount_is_3={amount}': dict(damage=dict(mae=0., sign_accuracy=1.,
        classes=dict(zero=dict(count=4 if op else 0, recall=1. if op else None)))) for op in (0, 1) for amount in (0, 1)}
    return dict(held_axes=axes, held_op_amount=damage)


class Tests(unittest.TestCase):
    def test_verifier_has_only_stdlib_imports_and_no_scientific_calls(self):
        tree = ast.parse(Path(V.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'copy', 'hashlib', 'itertools', 'json', 'math', 'os'})
        self.assertFalse(any(isinstance(n, ast.ImportFrom) and n.module != 'pathlib' for n in ast.walk(tree)))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        forbidden = ('make_model', 'forward', 'backward', 'step', 'apply', 'prepare_data', 'evaluate', 'success_gate')
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in forbidden for n in calls))
        self.assertNotIn('torch', sys.modules)

    def test_complete_program_parse_checks_syntax_not_labels(self):
        p = program([1, 0, 1, 1, 0]); self.assertEqual(V.parse_program(p), [0., 1., 1., 0., 3., 1., 0., 3.])
        renamed = copy.deepcopy(p); renamed['code'] = 'renamed'; renamed['raw_card']['card']['id'] = 'new'
        self.assertEqual(V.parse_program(renamed), V.parse_program(p))
        broken = copy.deepcopy(p); broken['raw_card']['abilities']['card'][0]['effect']['kind'] = 'heal'
        with self.assertRaisesRegex(ValueError, 'complete literal'): V.parse_program(broken)

    def test_parity_atomic_pairwise_and_printed_profile_support(self):
        ps = [program(b, i) for i, b in enumerate(itertools.product((0, 1), repeat=5))]
        self.assertEqual(len(V.parity(ps)), 32)
        bad = copy.deepcopy(ps); bad[31]['partition'] = 'train'
        with self.assertRaisesRegex(ValueError, 'parity'): V.parity(bad)
        bad = copy.deepcopy(ps); bad[31]['raw_card']['card']['cost'] = 3
        with self.assertRaisesRegex(ValueError, 'printed'): V.parity(bad)
        bad = copy.deepcopy(ps); bad[31] = bad[0]
        with self.assertRaisesRegex(ValueError, 'product'): V.parity(bad)

    def test_reference_is_typed_and_bound_and_clips_heal(self):
        fields = [0., 1., 1., 0., 2., 0., 1., 3.]
        candidates = [[0, 1, 1, 0, 2, 1, 10, 1], [1, 0, 1, 0, 2, 3, 10, 0],
                      [0, 1, 0, 1, 2, 3, 10, 0], [0, 1, 1, 0, 3, 3, 10, 0]]
        self.assertEqual(V.reference(fields, candidates), [[1., -1], [0., 0.], [0., 0.], [0., 0.]])
        candidates[0][5] = 0; self.assertEqual(V.reference(fields, candidates)[0], [1., 0.])
        fields[5:7] = [1., 0.]; self.assertEqual(V.reference(fields, candidates)[0], [1., 3.])

    def test_metrics_masks_intended_only_and_exact_native_sign(self):
        targets = [[[1, 0], [0, 999]], [[1, -.1], [0, 999]], [[0, 100], [1, 999]]]
        masks = [[[1, 1], [1, 0]], [[1, 1], [1, 0]], [[1, 0], [1, 0]]]
        pred = dict(eligibility=[[.9, .1], [.9, .1], [.1, .9]], damage=[[.25, -999], [-.3, -999], [999, -999]])
        m = V.score(pred, targets, masks, [0, 0, 0], [0, 1, 2])
        self.assertEqual(m['eligibility']['balanced_accuracy'], 1.)
        self.assertEqual(m['damage']['known'], 2); self.assertAlmostEqual(m['damage']['mae'], .225)
        self.assertEqual(m['damage']['sign_accuracy'], 1.)  # truth -.1 is negative, never native-zero
        self.assertEqual(m['damage']['classes']['zero']['recall'], 1.)
        self.assertIsNone(m['damage']['classes']['positive']['recall'])

    def test_all_factor_slices_and_heal_zero_are_required(self):
        a = good(); self.assertTrue(V.gate(a, a, True)['passed'])
        missing = copy.deepcopy(a); missing['held_axes']['arena_space=1']['eligibility']['balanced_accuracy'] = None
        self.assertFalse(V.gate(missing, a, True)['passed'])
        missing = copy.deepcopy(a); missing['held_op_amount']['op_heal=1,amount_is_3=1']['damage']['classes']['zero'] = dict(count=0, recall=None)
        self.assertFalse(V.gate(missing, a, True)['passed'])
        self.assertIsNone(a['held_op_amount']['op_heal=0,amount_is_3=1']['damage']['classes']['zero']['recall'])

    def test_new_identity_gap_is_primary_old_gap_descriptive(self):
        noid, withid = good(), good(); noid['held_axes']['cap_is_3=0']['eligibility']['balanced_accuracy'] = .95
        self.assertFalse(V.gate(noid, withid, True)['passed'])
        self.assertTrue(V.gate(noid, withid, False)['passed'])
        self.assertFalse(V.gate(noid, withid, False)['identity_passed'])

    def test_composite_improvement_requires_noninferiority_and_nonzero_denominator(self):
        m = lambda ba, error: dict(eligibility=dict(balanced_accuracy=ba), damage=dict(mae=error))
        self.assertTrue(V.comparative(m(.8, .6), m(.9, .3))['passed'])
        self.assertFalse(V.comparative(m(1., 0.), m(1., 0.))['relative_supported'])
        self.assertFalse(V.comparative(m(.8, .6), m(.79, .1))['passed'])
        self.assertFalse(V.comparative(m(.8, .6), m(.99, .61))['passed'])

    def test_statistics_use_train_only_native_known_intended(self):
        y = [[[1, 1], [0, 999]], [[1, 0], [0, 999]], [[1, -3], [0, 999]], [[0, 100], [1, 999]]]
        mask = [[[1, 1], [1, 0]] for _ in range(4)]
        fields = [[1, 0, 1, 0, 2, 1, 0, 1], [1, 0, 1, 0, 2, 0, 1, 3]]
        a = V.loss_statistics(y, mask, [0] * 4, [0, 1, 1, 0], fields, [0, 1, 2])
        poisoned = copy.deepcopy(y); poisoned[3] = [[1, -1e9], [1, 1e9]]
        self.assertEqual(a, V.loss_statistics(poisoned, mask, [0] * 4, [0, 1, 1, 0], fields, [0, 1, 2]))
        self.assertEqual(a['eligibility_class_counts'], [3, 3]); self.assertEqual(a['damage_weights'][3], 0.)

    def test_json_knownness_corruption_and_exclusive_output(self):
        V.close(dict(a=[1., None, True]), dict(a=[1, None, True]))
        with self.assertRaises(ValueError): V.close(dict(a=[1., 0., True]), dict(a=[1., None, True]))
        with self.assertRaises(ValueError): V.close(float('nan'), 0.)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'proof.json'; V.write_new(path, dict(status='passed'))
            first = V.pin(path); path.write_text(json.dumps(dict(status='failed')))
            self.assertNotEqual(first['sha256'], V.pin(path)['sha256'])
            with self.assertRaises(FileExistsError): V.write_new(path, dict(status='passed'))

    def test_native_trace_requires_exact_action_membership_chain_and_completion(self):
        before = dict(offeredActions=[dict(card='source')]); after = dict(decision='AbilityTarget')
        step = dict(stage='play-own-hand', before=before, action=dict(card='source'), after=after)
        case = dict(world_id=0, card='p', steps=[step]); raw = dict(collectionPlanSha256='pin', sourceRevision='rev', cases=[case], applyCalls=1)
        trace = [dict(schema='jepa-compositional-typed-apply-journal/1', planSha256='pin', sourceRevision='rev'),
            dict(phase='beforeApply', applyCall=1, context='world-0-p', branch='play-own-hand', before=before, offeredAction=step['action']),
            dict(phase='afterApply', applyCall=1, context='world-0-p', branch='play-own-hand', after=after),
            dict(phase='contextComplete', case=case)]
        self.assertEqual(V.native_journal(trace, raw)['native_applies'], 1)
        corrupt = copy.deepcopy(trace); corrupt[2]['applyCall'] = 2
        with self.assertRaisesRegex(ValueError, 'physical action'): V.native_journal(corrupt, raw)
        with self.assertRaises((ValueError, IndexError)): V.native_journal(trace[:-1], raw)

    def test_independent_native_derivation_surviving_healthy_and_invalid(self):
        # Reuse only artificial capture construction, never the converter's
        # labels, metrics, reference or implementation under test.
        from test_compositional_typed_data import fixture, ROLES
        for healthy in (False, True):
            case, world = fixture(heal=True, healthy=healthy)
            world['root_variant'] = 2 if healthy else 0
            result = V.native_case(case, world, ROLES); j = result['selected']
            self.assertEqual(result['targets'][j], [1., 0. if healthy else -3.])
            self.assertEqual(result['mask'][j], [1., 1.])
        for cancel in (False, True):
            case, world = fixture(intent='p2_space_c2a', cancel=cancel, prompt_only=not cancel)
            world['root_variant'] = 3
            result = V.native_case(case, world, ROLES)
            self.assertTrue(all(mask == [1., 0.] for mask in result['mask']))

    def test_independent_native_labels_are_not_replaced_by_reference(self):
        from test_compositional_typed_data import fixture, ROLES
        case, world = fixture(); world['root_variant'] = 0
        role = case['declared_intent']['ref']; case['final']['projections'][role]['damage'] += 1
        result = V.native_case(case, world, ROLES)
        self.assertEqual(result['targets'][result['selected']][1], 4.)
        tampered = copy.deepcopy(case); tampered['steps'][1]['action'] = {'card': 'unoffered-identity'}
        with self.assertRaisesRegex(ValueError, 'unoffered'): V.native_case(tampered, world, ROLES)

    def test_head_local_conflicts_cannot_hide_behind_intent_or_unused_fields(self):
        fields = [[0., 1., 1., 0., 2., 1., 0., 1.]]
        features = [[[0., 1., 1., 0., 2., 1., 10., 1.]],
                    [[0., 1., 1., 0., 2., 3., 10., 0.]]]
        mask = [[[1., 0.]], [[1., 0.]]]
        self.assertEqual(V.consumed_conflicts(fields, features, [[[1., 0.]], [[1., 0.]]], mask), {'old': 0, 'new': 0})
        with self.assertRaisesRegex(ValueError, 'actually consumed'):
            V.consumed_conflicts(fields, features, [[[1., 0.]], [[0., 0.]]], mask)


if __name__ == '__main__': unittest.main()
