"""Artificial JSON/list-only regressions; no real arrays, models or outcomes."""
import ast
import copy
from pathlib import Path
import unittest

import real_ir_hp_projection_data as H
from test_real_ir_transfer_data import ListOnlyNP, artificial_cohort


def artificial_saved_pair():
    oldplan, oldraw, oldtrace = artificial_cohort()
    old, om = H.D.prepare_data(ListOnlyNP, oldplan, oldraw, oldtrace)
    plan, raw, trace = artificial_cohort()
    for case, world in zip(raw['cases'], plan['worlds']):
        initial = {}
        for q, role in enumerate(H.D.ROLES):
            value = 1 if q < 2 else 2 if q < 4 else 4
            if case['root_variant'] == 6 and q == 0 or case['root_variant'] == 7 and q == 4: value = 0
            initial[role] = value
            if q < 4: world['arena_cards'][role]['damage'] = value
            else: world['own_base_damage' if q == 4 else 'opponent_base_damage'] = value
        effect = plan['programs'][case['program_index']]['canonical_program']['effect']
        captures = [case['before'], case['targetPrompt'], case['final'], case['lastObserved']]
        captures.extend(capture for step in case['steps'] for capture in (step['before'], step['after']))
        for capture in captures:
            if capture is None: continue
            resolved = capture['projections']['source']['zone'] == 'discard'
            for role, value in initial.items():
                after = value
                if resolved and role == case['declared_intent']['ref']:
                    amount = effect['amount']['value']
                    after = value + amount if effect['operator'] == 'damage' else max(0, value - amount)
                capture['projections'][role]['damage'] = after
    fresh, fm = H.D.prepare_data(ListOnlyNP, plan, raw, trace)
    return old, om, fresh, fm


class Tests(unittest.TestCase):
    def test_stdlib_import_no_fits_models_or_native_calls(self):
        tree = ast.parse(Path(H.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'copy', 'hashlib', 'json', 'real_ir_transfer_data'})
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in
            ('make_model', 'backward', 'fit_head', 'mean', 'std', 'apply', 'worker') for n in ast.walk(tree)))
        self.assertNotIn('np', vars(H))

    def test_full_artificial112_merge_and_no_fresh_training(self):
        a, om, b, fm = artificial_saved_pair()
        out, m = H.combine(ListOnlyNP, a, om, b, fm)
        self.assertTrue(m['fit_admitted'], m['fit_blockers'])
        self.assertEqual(len(out['candidate_features']), 112)
        self.assertEqual(out['candidate_features'][:56], a['candidate_features'])
        self.assertEqual(out['targets'][:56], a['targets'])
        self.assertEqual(out['target_mask'][:56], a['target_mask'])
        self.assertEqual(out['train_idx'], list(range(40)))
        self.assertEqual(out['old_dev_idx'], list(range(40, 56)))
        self.assertEqual(out['old_all_idx'], list(range(56)))
        self.assertEqual(out['fresh_all_idx'], list(range(56, 112)))
        self.assertEqual(m['support'], dict(fresh_known_endpoints=39, primary=30, replay=9))
        self.assertEqual(m['reference']['known_coordinates'], 375)
        self.assertEqual(m['reference']['mismatch_count'], 0)
        self.assertTrue(all(x['partition'] == 'fresh' for x in m['root_metadata'][56:]))
        self.assertEqual(m['root_metadata'][56]['native_source_partition'], 'train')
        self.assertTrue(all(x['root'] == i for i, x in enumerate(m['root_metadata'])))

    def test_primary_excludes_all_old_exposure_not_only_training(self):
        a, om, b, fm = artificial_saved_pair(); out, m = H.combine(ListOnlyNP, a, om, b, fm)
        self.assertEqual(m['replay_roots'], [62, 70, 78, 86, 95, 102, 103, 110, 111])
        # Root103 is a fresh healthy-base heal3 tuple, known only on old HELD47.
        self.assertTrue(out['replay_target_mask'][103][4][1])
        self.assertEqual(out['primary_target_mask'][103][4], [0., 0.])
        self.assertEqual(out['target_mask'][103][4], [1., 1.])
        self.assertEqual(out['targets'][103][4][1], 0.)
        self.assertTrue(all(c == [0., 0.] for root in out['primary_target_mask'][:56] for c in root))
        self.assertTrue(all(c[0] == 0. for root in out['primary_target_mask'] for c in root))
        self.assertEqual(sum(c[1] for root in out['primary_target_mask'] for c in root), 30)
        self.assertEqual(sum(c[1] for root in out['replay_target_mask'] for c in root), 9)

    def test_only_declared_before_damage_changes_are_allowed(self):
        a, om, b, fm = artificial_saved_pair()
        for column, value in ((9, 2.), (14, 10.), (13, 0.), (16, 0.)):
            bad = copy.deepcopy(b); bad['candidate_features'][0][0][column] = value
            with self.assertRaisesRegex(ValueError, 'beyond declared damage'): H.combine(ListOnlyNP, a, om, bad, fm)
        bad = copy.deepcopy(b); bad['candidate_features'][0][0][12] = 3.
        with self.assertRaisesRegex(ValueError, 'ground1/space2/base4'): H.combine(ListOnlyNP, a, om, bad, fm)

    def test_semantic_or_printed_bank_change_rejects(self):
        a, om, b, fm = artificial_saved_pair()
        for key in ('program_features', 'source_printed_features'):
            bad = copy.deepcopy(b); bad[key][0][0] += 1
            with self.assertRaisesRegex(ValueError, 'source bank changed'): H.combine(ListOnlyNP, a, om, bad, fm)

    def test_support_or_reference_failure_blocks_without_relabeling(self):
        a, om, b, fm = artificial_saved_pair()
        bad = copy.deepcopy(b); bad['target_mask'][0][0][1] = 0.
        out, m = H.combine(ListOnlyNP, a, om, bad, fm)
        self.assertFalse(m['fit_admitted']); self.assertIn('fresh30primary9replay-support', m['fit_blockers'])
        self.assertEqual(out['targets'][56][0], b['targets'][0][0])
        altered = copy.deepcopy(fm); altered['reference']['mismatch_count'] = 1
        out, m = H.combine(ListOnlyNP, a, om, b, altered)
        self.assertFalse(m['fit_admitted']); self.assertIn('fresh-native-reference-admission', m['fit_blockers'])
        self.assertEqual(out['targets'][56:], b['targets'])


if __name__ == '__main__': unittest.main()
