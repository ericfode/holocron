"""Primitive saved-verifier regressions; no NumPy, model, engine or real data."""
import ast
import copy
from pathlib import Path
import unittest

import real_ir_hp_projection_verify as H


def scores(mae):
    return dict(endpoint_mae={k: mae for k in ('pooled', 'unit', 'base', 'damage', 'heal')},
        undefined=[], nonzero_sign_accuracy=1., healthy_count=2, healthy_max_abs=0.,
        eligibility=dict(positive_recall=1.))


def methods(candidate=.1, baseline=1., train=.1):
    values = {}
    for seed in H.SEEDS:
        for arm, error in (('baseline', baseline), ('effect-hp-invariant', candidate)):
            values[f's{seed}:{arm}'] = {'300': dict(fresh_primary=dict(raw=scores(error)),
                train=dict(routed=scores(train if arm == 'effect-hp-invariant' else .1)), old_dev=dict(routed=scores(error)))}
    return values


def events(updates=2, evaluations=1):
    names = [k for _ in range(updates) for k in ('neural_forwards', 'backwards', 'optimizer_updates')]
    names += ['neural_forwards'] * evaluations
    result = []
    for i, name in enumerate(names):
        token = 100 + 2 * i
        result.extend([dict(event='intent', sequence=token, data=dict(token=token, counter=name, amount=1)),
            dict(event='complete', sequence=token + 1, data=dict(token=token, actual=None, proofs=[]))])
    return result


class Tests(unittest.TestCase):
    def test_no_model_worker_engine_import_or_calls(self):
        tree = ast.parse(Path(H.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'math', 'os', 'real_ir_transfer_verify', 'real_ir_hp_projection_data'})
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in
            ('make_model', 'backward', 'step', 'evaluate', 'decisions', 'fit_head') for n in ast.walk(tree)))
        self.assertNotIn('np', vars(H))

    def test_conditional_raw_division_preserves_sign_and_zero_probability_unknown(self):
        prediction = [[[.5, -1.], [.25, .5]], [[0., 0.], [1., 0.]]]
        labels = [[[1., -2.], [1., 2.]], [[1., 3.], [1., 0.]]]
        masks = [[[0., 1.], [0., 1.]], [[0., 1.], [0., 1.]]]
        meta = [dict(operator='heal', intent_domain='unit', healthy_intent=False),
            dict(operator='heal', intent_domain='base', healthy_intent=True)]
        actual = H.raw_scores(prediction, labels, masks, meta, [0, 1])
        self.assertEqual(actual['endpoint_mae']['pooled'], 0.)
        self.assertEqual(actual['endpoint_support']['pooled'], 3)
        self.assertEqual(actual['undefined'], [[1, 0]])
        self.assertEqual(actual['healthy_max_abs'], 0.)
        self.assertEqual(actual['endpoints'][0]['prediction'], -2.)
        self.assertEqual(actual['endpoints'][1]['prediction'], 2.)

    def test_unknown_future_never_enters_raw_score(self):
        prediction = [[[.5, 1.], [0., 999.]]]
        labels = [[[1., 2.], [1., -999.]]]; masks = [[[0., 1.], [0., 0.]]]
        meta = [dict(operator='damage', intent_domain='unit', healthy_intent=False)]
        actual = H.raw_scores(prediction, labels, masks, meta, [0])
        self.assertEqual(actual['endpoint_support']['pooled'], 1)
        self.assertEqual(actual['undefined'], [])
        self.assertEqual(actual['endpoint_mae']['pooled'], 0.)

    def test_primary_all_seed_absolute_relative_sign_and_train_gates(self):
        values = methods(); actual = H.gates(values)
        self.assertTrue(actual['primary_passed']); self.assertFalse(actual['semantic_validated'])
        values['s29:effect-hp-invariant']['300']['fresh_primary']['raw']['endpoint_mae']['base'] = .3
        actual = H.gates(values)
        self.assertFalse(actual['primary_passed']); self.assertFalse(actual['per_seed']['29']['raw_endpoint_slices_passed'])
        self.assertTrue(actual['per_seed']['17']['primary_passed'])
        self.assertFalse(H.gates(methods(train=.2))['primary_passed'])

    def test_no_zero_denominator_fallback_and_no_undefined_support_pass(self):
        actual = H.gates(methods(candidate=0., baseline=0.))
        self.assertIsNone(actual['per_seed']['17']['relative_raw_mae_improvement'])
        self.assertFalse(actual['primary_passed'])
        values = methods(); values['s17:effect-hp-invariant']['300']['fresh_primary']['raw']['undefined'] = [[56, 0]]
        self.assertFalse(H.gates(values)['primary_passed'])

    def test_original_routed_usability_stays_separate_from_raw_primary(self):
        values = methods()
        values['s17:effect-hp-invariant']['300']['old_dev']['routed']['healthy_max_abs'] = .5
        actual = H.gates(values)
        self.assertTrue(actual['primary_passed'])
        self.assertFalse(actual['per_seed']['17']['old_dev_original_usability']['effect-hp-invariant']['usable_endpoint_gate_passed'])
        self.assertFalse(actual['per_seed']['17']['old_dev_original_usability']['effect-hp-invariant']['eligibility_discrimination_qualified'])

    def test_zero_refits_and_deferred_evaluation_counter_order(self):
        rows = events(); self.assertEqual(H.counter_panel(rows, updates=2, evaluations=1)['numerical_fits'], 0)
        bad = copy.deepcopy(rows); bad[0]['data']['counter'] = 'numerical_fits'
        with self.assertRaisesRegex(ValueError, 'barrier'): H.counter_panel(bad, updates=2, evaluations=1)
        bad = copy.deepcopy(rows); bad[4]['data']['counter'] = 'neural_forwards'
        with self.assertRaisesRegex(ValueError, 'barrier'): H.counter_panel(bad, updates=2, evaluations=1)
        with self.assertRaisesRegex(ValueError, 'missing'): H.counter_panel(rows[:-1], updates=2, evaluations=1)

    def test_exact_saved_inventory_has_only_fixed_readouts(self):
        names = H.output_inventory(); self.assertEqual(len(names), 36)
        self.assertIn('s43-old-printed-only-step300-predictions.npz', names)
        self.assertNotIn('s43-old-printed-only-step0-predictions.npz', names)
        self.assertNotIn('s17-baseline-step150-predictions.npz', names)


if __name__ == '__main__': unittest.main()
