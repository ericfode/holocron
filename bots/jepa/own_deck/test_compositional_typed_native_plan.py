"""Portable synthetic grammar/fixture-source tests; no native or model calls."""
import copy
import itertools
import json
from pathlib import Path
import unittest

import compositional_typed_native_plan as P

HERE = Path(__file__).resolve().parent
CRATE = HERE / 'compositional_typed_native_collector'


def catalog():
    return json.loads((CRATE / 'fixtures/source-templates.json').read_text())


class Tests(unittest.TestCase):
    def test_complete_five_bit_factorial_and_parity_holdouts(self):
        plan = P.build_plan(catalog()); programs = plan['programs']
        self.assertEqual([p['bits'] for p in programs], [list(v) for v in itertools.product((0, 1), repeat=5)])
        self.assertEqual(len({p['program_hash'] for p in programs}), 32)
        train = [p for p in programs if p['partition'] == 'train']
        held = [p for p in programs if p['partition'] == 'held']
        self.assertEqual((len(train), len(held)), (16, 16))
        for width in range(1, 5):
            for coordinates in itertools.combinations(range(5), width):
                a = {tuple(p['bits'][i] for i in coordinates) for p in train}
                b = {tuple(p['bits'][i] for i in coordinates) for p in held}
                self.assertEqual(a, b)
                self.assertEqual(len(a), 2 ** width)

    def test_identical_printed_source_semantics_and_explicit_synthetic_status(self):
        original = catalog(); before = copy.deepcopy(original); plan = P.build_plan(original)
        self.assertEqual(original, before)
        profiles = []
        for program in plan['programs']:
            row = program['raw_card']; card = copy.deepcopy(row['card'])
            for key in ('id', 'setId', 'setCodes'):
                card.pop(key)
            profiles.append(card)
            provenance = plan['synthetic_definition_provenance'][program['code']]
            self.assertTrue(provenance['laboratory_definition'])
            self.assertFalse(provenance['real_card_claim'])
            self.assertFalse(provenance['compiler_conversion_run'])
            self.assertIsNone(row['sourcePath']); self.assertIsNone(row['sourceHash'])
            self.assertEqual(row['baseClass'], 'EventCard')
            self.assertEqual(row['abilities'], dict(card=[P.elementary_ability(program['factors'])], unit=[], leader=[]))
        self.assertTrue(all(p == profiles[0] for p in profiles))
        self.assertFalse(plan['actual_card_coverage_claim'])

    def test_six_plain_anchor_definitions_and_exact_sixteen_unit_lattice(self):
        plan = P.build_plan(catalog()); anchors = [r for c, r in plan['selected_whole_rows'].items() if c.startswith('SYNTH_ANCHOR_')]
        self.assertEqual(len(anchors), 6)
        for row in anchors:
            self.assertEqual((row['card']['hp'], row['card']['power']), (10, 0))
            self.assertEqual(row['abilities'], dict(card=[], unit=[], leader=[]))
            self.assertEqual(row['keywordValues'], {})
        for world in plan['worlds']:
            self.assertEqual(set(world['arena_cards']), set(P.ROLES))
            counts = {}
            for value in world['arena_cards'].values():
                self.assertEqual(value['cost'], value['printed_cost'])
                key = (value['owner'], value['arena'], value['cost'])
                counts[key] = counts.get(key, 0) + 1
            expected = {(owner, arena, cost): 2 if cost == 2 else 1
                for owner, arena, cost in itertools.product(('p1', 'p2'), ('ground', 'space'), (2, 3, 4))}
            self.assertEqual(counts, expected)

    def test_four_variant_intents_damage_and_live_survival(self):
        plan = P.build_plan(catalog())
        self.assertEqual([w['id'] for w in plan['worlds']], list(range(128)))
        for program in plan['programs']:
            worlds = plan['worlds'][program['index'] * 4:program['index'] * 4 + 4]
            self.assertEqual([w['root_variant'] for w in worlds], [0, 1, 2, 3])
            self.assertEqual([w['arena_cards'][w['intent_ref']]['damage'] for w in worlds], [3, 1, 0, 3])
            self.assertNotEqual(worlds[0]['intent_ref'], worlds[1]['intent_ref'])
            self.assertEqual(worlds[0]['arena_cards'], worlds[1]['arena_cards'])
            self.assertEqual(worlds[0]['arena_cards'], worlds[3]['arena_cards'])
            self.assertEqual(worlds[1]['arena_cards'][worlds[1]['intent_ref']]['cost'], program['factors']['cap'])
            for world in worlds:
                self.assertTrue(all(c['damage'] + 3 < c['hp'] for c in world['arena_cards'].values()))

    def test_healthy_intent_does_not_remove_all_changed_heal_candidates(self):
        plan = P.build_plan(catalog())
        for program in plan['programs']:
            world = plan['worlds'][program['index'] * 4 + 2]
            intended = world['arena_cards'][world['intent_ref']]
            self.assertEqual(intended['damage'], 0)
            alternatives = [card for role, card in world['arena_cards'].items() if role != world['intent_ref'] and
                card['arena'] == program['factors']['arena'] and card['cost'] <= program['factors']['cap'] and
                (program['factors']['owner'] == 'any' or card['owner'] == 'p2') and card['damage'] > 0]
            self.assertTrue(alternatives)

    def test_complete_native_grammar_and_constructor_support_preserved(self):
        source = catalog(); plan = P.build_plan(source)
        for code in P.SUPPORT_CODES:
            self.assertEqual(plan['selected_whole_rows'][code], next(r for r in source['cards'] if r['setCode'] == code))
        self.assertEqual(plan['selected_whole_rows']['TOKEN_SHIELD']['status'], 'unsupported')
        for p in plan['programs']:
            a = p['raw_card']['abilities']['card'][0]
            self.assertEqual(a['targetResolver']['zone'], 'arena')
            self.assertNotIn('optional', a)
            self.assertNotIn('mode', a['targetResolver'])
            self.assertEqual(a['costs'], [])

    def test_native_source_caps_validation_first_and_one_apply_entrypoint(self):
        source = (CRATE / 'src/main.rs').read_text()
        self.assertEqual(source.count('e.apply('), 1)
        self.assertIn('const MAX_APPLY:usize=512;', source)
        self.assertIn('const MAX_SECONDS:u64=30;', source)
        run = source[source.index('fn run(plan_path:'):]
        self.assertLess(run.index('let validation=validate_fixtures'), run.index('let mut budget=Budget'))
        self.assertIn('worlds.len()!=128', source)
        self.assertIn('programs.len()!=32', source)
        self.assertIn('if b.calls-start>=4', source)
        self.assertIn('if !ok{break;}', source)

    def test_native_trace_is_paired_fsynced_and_never_substitutes_target(self):
        source = (CRATE / 'src/main.rs').read_text()
        apply = source[source.index('fn apply(&mut self'):source.index('fn run_case(')]
        self.assertLess(apply.index('"phase":"beforeApply"'), apply.index('e.apply('))
        self.assertIn('"phase":"afterApply"', apply)
        self.assertIn('"branch":stage', apply)
        self.assertIn('f.sync_all()', source)
        self.assertIn('offered(e,&s,intended)?', source)
        self.assertIn('unoffered-observation-only', source)
        self.assertIn('unreviewed-continuation-', source)
        self.assertNotIn('accept-optional-trigger', source)

    def test_primitive_tests_do_not_prepare_actual_plan_or_invoke_runtime(self):
        plan = P.build_plan(catalog())
        self.assertEqual((plan['native_applies'], plan['neural_forwards'], plan['optimizer_updates']), (0, 0, 0))
        self.assertEqual((plan['expected_cases'], plan['collector_max_engine_applies']), (128, 512))
        self.assertTrue(plan['root_go_required'])
        self.assertFalse(plan['semantic_validated'])

    def test_all_programs_use_frozen_whole_card_frontend_without_adapters(self):
        import effect_identifiability_fit as E
        plan = P.build_plan(catalog())
        for program in plan['programs']:
            raw = program['raw_card']
            self.assertFalse(set(raw) & {'diagnostics', 'piloting', 'synthetic'})
            self.assertFalse(set(raw['card']) & {'deployCost', 'pilotBox', 'pilotingBox'})
            document, audit = E.canonical_document(raw)
            expected = copy.deepcopy(raw['abilities'])
            expected['card'][0].pop('title')
            self.assertEqual(document['abilities'], expected)
            self.assertFalse(audit['callback_occurrences'])
            self.assertGreater(len(E.prior().tokens(document)), 0)


if __name__ == '__main__':
    unittest.main()
