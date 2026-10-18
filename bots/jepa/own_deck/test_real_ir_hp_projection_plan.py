"""Pure artificial metadata and source-diff tests; no engine/model/actual plan."""
import copy
from pathlib import Path
import unittest

import real_ir_hp_projection_plan as P


def toy():
    rows = {code: dict(setCode=code, card=dict(title='opaque', id=code)) for code in P.CODES}
    for key, hp, arena in (('ground', 8, 'ground'), ('space', 10, 'space'), ('base', 30, None)):
        rows[P.HELPERS[key]] = dict(card=dict(hp=hp, unique=False, keywords=[], arena=arena))
    for code in (*P.HELPERS.values(), 'TOKEN_SHIELD'):
        rows.setdefault(code, dict(opaque=True))
    programs = [dict(index=i, code=code, raw_card=rows[code], canonical_program=dict(opaque=i),
        aliases=['alias-' + code], partition='train' if i < 5 else 'held') for i, code in enumerate(P.CODES)]
    worlds = []
    for i in range(56):
        v = i % 8; board = {}
        for role in P.ROLES[:4]:
            owner, arena = role.split('_')
            board[role] = dict(code=P.HELPERS[arena], owner=owner, arena=arena, exhausted=False,
                damage=0 if v == 6 and role == 'p1_ground' else 3 if arena == 'ground' else 5)
        worlds.append(dict(id=i, program_index=i // 8, root_variant=v, source_code=P.CODES[i // 8],
            partition=programs[i // 8]['partition'], max_applies=3, requires_target=True, ready_resources=12,
            intent_ref=P.ROLES[v if v < 6 else 0 if v == 6 else 4], arena_cards=board,
            own_base_damage=0 if v == 7 else 5, opponent_base_damage=5))
    return dict(schema='jepa-real-ir-transfer-plan/1', synthetic=False, source_revision=P.REVISION,
        catalogue_sha256=P.CATALOGUE_SHA, runtime_sha256=P.RUNTIME_SHA, runtime_admitted_snapshot=1178,
        candidate_order=list(P.ROLES), helpers=copy.deepcopy(P.HELPERS), collector_max_engine_applies=168,
        expected_apply_count=112, collector_max_seconds=30, expected_count_is_not_observed=True,
        programs=programs, worlds=worlds, selected_whole_rows=rows, selected_whole_cards=sorted(rows),
        fit_source_policy='original historically held policy', source_pins=[dict(opaque='unchanged')])


class ProjectionPlan(unittest.TestCase):
    def test_damage_projection_and_healthy_exceptions(self):
        plan = P.build(toy())
        for i, w in enumerate(plan['worlds']):
            self.assertEqual(w['arena_cards']['p1_ground']['damage'], 0 if i % 8 == 6 else 1)
            self.assertEqual(w['arena_cards']['p2_ground']['damage'], 1)
            self.assertEqual(w['arena_cards']['p1_space']['damage'], 2)
            self.assertEqual(w['arena_cards']['p2_space']['damage'], 2)
            self.assertEqual(w['own_base_damage'], 0 if i % 8 == 7 else 4)
            self.assertEqual(w['opponent_base_damage'], 4)

    def test_deep_copy_preserves_source_aliases_pins_and_order(self):
        old = toy(); snapshot = copy.deepcopy(old); new = P.build(old)
        self.assertEqual(old, snapshot)
        for key in ('programs', 'selected_whole_rows', 'selected_whole_cards', 'source_pins', 'helpers', 'candidate_order'):
            self.assertEqual(old[key], new[key]); self.assertIsNot(old[key], new[key])
        new['programs'][0]['raw_card']['card']['title'] = 'changed'
        self.assertEqual(old, snapshot)

    def test_all_sources_developmental_and_unselected_preserved(self):
        p = P.build(toy()); f = p['freshness_scope']
        self.assertTrue(f['new_state_composition_only']); self.assertFalse(f['fresh_source_programs'])
        self.assertEqual(set(f['source_program_status']), set(P.CODES))
        self.assertTrue(all('DEVELOPMENTAL' in v for v in f['source_program_status'].values()))
        self.assertEqual(tuple(f['fresh_whenPlayed_sources_preserved_not_selected']), P.PRESERVED_NOT_SELECTED)
        self.assertFalse(set(P.PRESERVED_NOT_SELECTED) & set(p['selected_whole_cards']))
        self.assertTrue(p['native_collector_requirement']['new_collector_required'])
        self.assertFalse(p['native_collector_requirement']['unchanged_old_collector_compatible'])

    def test_wrong_old_grid_rejected(self):
        p = toy(); p['worlds'][0]['arena_cards']['p1_ground']['damage'] = 1
        with self.assertRaises(ValueError): P.build(p)

    def test_newer_runtime_or_edited_natural_hp_rejected(self):
        p = toy(); p['runtime_admitted_snapshot'] = 1316
        with self.assertRaises(ValueError): P.build(p)
        p = toy(); p['selected_whole_rows']['HMW_093']['card']['hp'] = 10
        with self.assertRaises(ValueError): P.build(p)

    def test_new_collector_has_only_declared_baseline_source_deltas(self):
        here = Path(__file__).resolve().parent
        old = here / 'real_ir_transfer_native_collector'; new = here / P.NEW_COLLECTOR
        expected = (old / 'src/main.rs').read_text()
        for a, b in (
            ('else if arena=="ground"{3}else{5}', 'else if arena=="ground"{1}else{2}'),
            ('shared 3/5-damage public board differs', 'shared 1/2-damage public board differs'),
            ('world["root_variant"]==7&&owner==Seat::P1{0}else{5}', 'world["root_variant"]==7&&owner==Seat::P1{0}else{4}'),
            ('shared 5-damage base board differs', 'shared 4-damage base board differs'),
            ('real-ir-transfer-native-collector PLAN', P.NEW_BINARY + ' PLAN')):
            self.assertEqual(expected.count(a), 1); expected = expected.replace(a, b)
        self.assertEqual((new / 'src/main.rs').read_text(), expected)
        self.assertEqual((new / 'supervise.py').read_text(), (old / 'supervise.py').read_text().replace(
            "BINARY = 'real-ir-transfer-native-collector'", "BINARY = '" + P.NEW_BINARY + "'"))
        self.assertEqual((new / 'Cargo.lock').read_bytes(), (old / 'Cargo.lock').read_bytes())
        self.assertEqual((new / 'Cargo.toml').read_text(), (old / 'Cargo.toml').read_text().replace(
            'name = "real-ir-transfer-native-collector"', 'name = "' + P.NEW_BINARY + '"'))


if __name__ == '__main__': unittest.main()
