"""Artificial metadata tests only; no actual plans, parser, engine or arrays."""
import copy
import unittest

import real_ir_intent_plan as P


def inputs():
    rows = {c: dict(setCode=c, card=dict(title='artificial')) for c in P.EVENTS}
    for c in (*P.HELPERS.values(), 'TOKEN_SHIELD'):
        rows.setdefault(c, dict(setCode=c, card=dict(title='artificial helper')))
    old = dict(schema='jepa-real-ir-transfer-plan/1', synthetic=False, source_revision=P.REVISION,
        catalogue_sha256=P.CATALOGUE_SHA, runtime_sha256=P.RUNTIME_SHA, runtime_admitted_snapshot=1178,
        helpers=copy.deepcopy(P.HELPERS), candidate_order=list(P.ROLES), selected_whole_rows=rows,
        selected_whole_cards=sorted(rows), hidden_policy='unchanged', source_pins=[dict(artificial=True)])
    old['programs'] = [dict(index=i, code=c, partition='train' if i < 5 else 'held',
        raw_card=rows[c], canonical_program=dict(artificial=i)) for i, c in enumerate(P.EVENTS)]
    row = dict(setCode='SOR_132', id='9002021213', card=dict(types=['unit'], hp=2, arena='space', keywords=[]),
        abilities=dict(card=[dict(trigger='whenPlayed', optional=True,
            targetResolver=dict(owner='any', type='unit', zone='arena', arena='space'),
            effect=dict(kind='damage', target='chosen', amount=dict(kind='const', value=3)))], leader=[], unit=[]))
    reserved = dict(status='reserved-no-new-outcomes', reserved_codes=[P.TERMINAL, *P.PRESERVED],
        cards=[dict(code=c, raw_row=row if c == P.TERMINAL else dict(untouched=c),
            whole_row_sha256=P.digest(row) if c == P.TERMINAL else 'not-selected',
            canonical_program=dict(artificial='terminal'), aliases=[c], exact_program_key='fixture-key',
            numeric_abstracted_family_key='fixture-family') for c in (P.TERMINAL, *P.PRESERVED)])
    return old, reserved


class Plan(unittest.TestCase):
    def test_separate_panels_and_budgets(self):
        result = P.build(*inputs()); dev, terminal = result['development'], result['terminal']
        self.assertEqual((len(dev['worlds']), len(dev['programs']), dev['collector_max_engine_applies']), (56, 7, 200))
        self.assertEqual((len(terminal['worlds']), len(terminal['programs']), terminal['collector_max_engine_applies']), (8, 1, 40))
        self.assertEqual(dev['expected_apply_count'] + terminal['expected_apply_count'], 128)
        self.assertTrue(terminal['terminal_outcomes_after_all_checkpoints'])
        self.assertEqual(terminal['programs'][0]['index'], 0)

    def test_grid_fallback_and_common_public_boards(self):
        result = P.build(*inputs()); dev, terminal = result['development'], result['terminal']
        for i, w in enumerate(dev['worlds']):
            v = i % 8; level = P.LEVELS[v % 4]
            self.assertEqual(w['damage_level'], level)
            self.assertEqual(w['arena_cards'], dev['worlds'][v]['arena_cards'])
            self.assertEqual(w['arena_cards'], terminal['worlds'][v]['arena_cards'])
            self.assertEqual(w['arena_cards']['p2_space']['damage'], 1 if level == 0 else level)
            self.assertEqual(w['opponent_base_damage'], 1 if level == 0 else level)
            selected = w['intent_ref']
            value = w['arena_cards'][selected]['damage'] if selected in w['arena_cards'] else w['own_base_damage'] if selected == 'own_base' else w['opponent_base_damage']
            self.assertEqual(value, level)

    def test_no_old_mutation_and_no_other_reserved_sources(self):
        old, reservation = inputs(); saved = copy.deepcopy((old, reservation)); result = P.build(old, reservation)
        self.assertEqual((old, reservation), saved)
        for name in ('development', 'terminal'):
            self.assertFalse(set(P.PRESERVED) & set(result[name]['selected_whole_cards']))
        self.assertNotIn(P.TERMINAL, result['development']['selected_whole_cards'])
        self.assertIn(P.TERMINAL, result['terminal']['selected_whole_cards'])
        self.assertEqual(result['preregistration']['grouped_untouched_sources'], ['ASH_259', 'LOF_259'])
        self.assertEqual(result['terminal']['programs'][0]['raw_card'], reservation['cards'][0]['raw_row'])

    def test_old_source_rows_and_programs_remain_equal_except_metadata_partition(self):
        old, reservation = inputs(); new = P.build(old, reservation)['development']
        for original, projected in zip(old['programs'], new['programs']):
            expected = copy.deepcopy(original); expected['legacy_partition'] = expected['partition']; expected['partition'] = 'developmental-state'
            self.assertEqual(projected, expected)
        self.assertEqual(new['selected_whole_rows'], old['selected_whole_rows'])

    def test_already_consumed_or_wrong_terminal_rejected(self):
        old, reservation = inputs(); reservation['status'] = 'consumed'
        with self.assertRaises(ValueError): P.build(old, reservation)
        old, reservation = inputs(); reservation['cards'][0]['raw_row']['card']['hp'] = 10
        with self.assertRaises(ValueError): P.build(old, reservation)

    def test_newer_runtime_rejected(self):
        old, reservation = inputs(); old['runtime_admitted_snapshot'] = 1316
        with self.assertRaises(ValueError): P.build(old, reservation)


if __name__ == '__main__': unittest.main()
