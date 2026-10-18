"""Portable whole-row/source proof tests; no engine, snapshot or model calls."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

import ability_correction_native_plan as P

HERE = Path(__file__).resolve().parent
CRATE = HERE / 'ability_correction_native_collector'


def inputs():
    fixture = json.loads((CRATE / 'fixtures/whole-rows.json').read_text())
    return dict(cards=fixture['cards']), dict(runtimeAdmittedCards=fixture['runtimeAdmittedCards'])


class Tests(unittest.TestCase):
    def test_exact_eight_roots_and_controlled_intents(self):
        plan = P.build_plan(*inputs())
        self.assertEqual([w['id'] for w in plan['worlds']], list(range(8)))
        self.assertEqual([p['anchor_membership_hypothesis'] for p in plan['intent_pairs']],
            [[True, False], [True, True], [False, False], [False, True]])
        self.assertEqual([(p['left_root'], p['right_root']) for p in plan['intent_pairs']], [(0, 1), (2, 3), (4, 5), (6, 7)])
        for a, b in zip(plan['worlds'][::2], plan['worlds'][1::2]):
            aa, bb = copy.deepcopy(a), copy.deepcopy(b)
            for key in ('id', 'intent_ref'):
                aa.pop(key); bb.pop(key)
            self.assertEqual(aa, bb)
            self.assertEqual((a['intent_ref'], b['intent_ref']), ('anchor_a', 'anchor_b'))

    def test_full_rows_and_prior_exposure_preserved(self):
        catalog, admission = inputs(); before = copy.deepcopy(catalog)
        source = next(r for r in catalog['cards'] if r['setCode'] == 'IBH_104')
        prior = dict(selected_whole_rows={'IBH_104': copy.deepcopy(source)})
        plan = P.build_plan(catalog, admission, prior)
        self.assertEqual(catalog, before)
        self.assertEqual(plan['cards'][0]['raw_card'], source)
        self.assertFalse(plan['source_program_transfer_claim'])
        self.assertFalse(plan['semantic_validated'])
        prior['selected_whole_rows']['IBH_104']['card']['text'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'prior exposed'):
            P.build_plan(catalog, admission, prior)

    def test_helpers_are_intact_plain_and_wholly_admitted(self):
        catalog, admission = inputs()
        plan = P.build_plan(catalog, admission)
        card = plan['selected_whole_rows']['ASH_061']['card']
        self.assertEqual((card['cost'], card['hp'], card['arena']), (4, 5, 'ground'))
        admission['runtimeAdmittedCards'] = [r for r in admission['runtimeAdmittedCards'] if r['setCode'] != 'ASH_061']
        with self.assertRaisesRegex(ValueError, 'runtime admission'):
            P.build_plan(catalog, admission)
        catalog, admission = inputs()
        next(r for r in catalog['cards'] if r['setCode'] == 'ASH_061')['keywordValues'] = {'sentinel': 1}
        with self.assertRaisesRegex(ValueError, 'plain complete'):
            P.build_plan(catalog, admission)

    def test_constructor_support_and_quota_are_explicit(self):
        plan = P.build_plan(*inputs())
        self.assertEqual(plan['selected_whole_rows']['TOKEN_SHIELD']['status'], 'unsupported')
        self.assertEqual((plan['collector_max_engine_applies'], plan['collector_max_seconds'], plan['native_build_max_seconds']), (32, 15, 10))
        self.assertEqual(sum(w['max_applies'] for w in plan['worlds']), 32)
        self.assertTrue(all(w['selection_mode'] == 'exactly-one-upTo' for w in plan['worlds']))

    def test_legacy_collector_exact_and_new_diff_is_declared(self):
        old = (HERE / 'semantic_discrimination_native_collector/src/main.rs').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(), P.PRIOR_COLLECTOR_SHA)
        expected = old.decode()
        changes = [
            ('const MAX_APPLY:usize=128;', 'const MAX_APPLY:usize=32;'),
            ('const MAX_SECONDS:u64=45;', 'const MAX_SECONDS:u64=15;'),
            ('33 predeclared own-hand semantic-discrimination fixtures from eight complete actual-corpus cards', '8 predeclared own-hand state-transfer diagnostic fixtures from one previously exposed complete actual-corpus card'),
            ('33', '8'), ('SEMANTIC_DISCRIMINATION_PLAN', 'ABILITY_CORRECTION_PLAN'),
            ('SEMANTIC_DISCRIMINATION_NATIVE_TRACE', 'ABILITY_CORRECTION_NATIVE_TRACE'),
            ('jepa-semantic-discrimination-', 'jepa-ability-correction-'),
            ('semantic-discrimination-native-collector', 'ability-correction-native-collector'),
            ('//! Whole existing definitions, native action menus, independent public branches.', '//! Versioned exposed-IBH104 fresh-state diagnostic. No new program-transfer claim.'),
        ]
        for a, b in changes:
            self.assertIn(a, expected)
            expected = expected.replace(a, b)
        self.assertEqual((CRATE / 'src/main.rs').read_text(), expected)

    def test_no_prevalidation_apply_and_no_unreviewed_prompt_substitution(self):
        source = (CRATE / 'src/main.rs').read_text()
        self.assertEqual(source.count('e.apply('), 1)
        run = source[source.index('fn run(validate_only:'):]
        self.assertLess(run.index('let fixture_validation=validate_fixtures'), run.index('let mut budget=Budget'))
        self.assertIn('worlds.len()!=8', source)
        self.assertIn('const MAX_APPLY:usize=32', source)
        self.assertIn('unoffered-observation-only', source)
        self.assertIn('unreviewed-second-target-prompt', source)
        self.assertIn('s.ability_selection.len!=1', source)


if __name__ == '__main__':
    unittest.main()
