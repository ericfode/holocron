"""Primitive saved-verifier regressions; no NumPy, model, engine or real files."""
import ast
import copy
import hashlib
import math
from pathlib import Path
import unittest

import real_ir_transfer_verify as V


def observations():
    labels = [[[1., -3.], [1., 0.]], [[1., 0.], [1., 0.]],
              [[1., 2.], [0., 0.]], [[0., 0.], [1., 3.]]]
    masks = [[[1., 1.], [1., 0.]], [[1., 0.], [1., 1.]],
             [[1., 1.], [1., 0.]], [[1., 0.], [1., 1.]]]
    metadata = [dict(operator='heal', intent_domain='unit', healthy_intent=False),
                dict(operator='heal', intent_domain='base', healthy_intent=True),
                dict(operator='damage', intent_domain='base', healthy_intent=False),
                dict(operator='damage', intent_domain='unit', healthy_intent=False)]
    return labels, masks, metadata


def gate_inputs(full=.1, old=.1, printed=1.):
    evaluations = {}
    for seed in V.SEEDS:
        for arm, mae in zip(V.ARMS, (full, old, printed)):
            evaluations[f's{seed}:{arm}'] = {'300': {'held': dict(
                endpoint_mae={k: mae for k in ('pooled', 'unit', 'base', 'damage', 'heal')},
                nonzero_sign_accuracy=1., healthy_count=2, healthy_max_abs=0.,
                eligibility=dict(positive_recall=1.))}}
    return evaluations


def counter_events(updates=2, evaluations=1):
    names = ['numerical_fits', 'numerical_fits']
    names += [name for _ in range(updates) for name in ('neural_forwards', 'backwards', 'optimizer_updates')]
    names += ['neural_forwards'] * evaluations
    result = []
    for i, name in enumerate(names):
        sequence = 2 * i + 100
        result.append(dict(event='intent', sequence=sequence,
            data=dict(counter=name, amount=1, token=sequence)))
        result.append(dict(event='complete', sequence=sequence + 1,
            data=dict(token=sequence, actual=None, proofs=[])))
    return result


class FakeArray:
    dtype = 'float32'
    shape = (1,)

    def __init__(self, raw): self.raw = raw
    def tobytes(self, order):
        assert order == 'C'
        return self.raw


class Tests(unittest.TestCase):
    def test_import_and_verification_never_import_model_or_scoring_worker(self):
        tree = ast.parse(Path(V.__file__).read_text())
        imports = {a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names}
        self.assertEqual(imports, {'hashlib', 'json', 'math', 'os', 'real_ir_transfer_data'})
        self.assertFalse(any(isinstance(node, ast.Attribute) and node.attr in
            ('make_model', 'backward', 'step', 'evaluate', 'decisions', 'fit_head') for node in ast.walk(tree)))
        self.assertNotIn('np', vars(V))

    def test_known_masks_preserve_native_zeros_and_ignore_unobserved_future(self):
        labels, masks, metadata = observations(); prediction = copy.deepcopy(labels)
        prediction[0][1][1] = 999.; prediction[1][0][1] = -999.
        score = V.scores(prediction, labels, masks, metadata, [0, 1])
        self.assertEqual(score['endpoint_mae']['pooled'], 0.)
        self.assertEqual(score['endpoint_support']['pooled'], 2)
        self.assertEqual(score['nonzero_sign_accuracy'], 1.)
        self.assertEqual(score['healthy_count'], 1); self.assertEqual(score['healthy_max_abs'], 0.)
        self.assertIsNone(score['eligibility']['balanced_accuracy'])
        self.assertIsNone(score['eligibility']['specificity'])
        self.assertEqual(score['eligibility']['positive_recall'], 1.)

    def test_wrong_native_signed_effect_and_recall_are_measured_independently(self):
        labels, masks, metadata = observations(); prediction = copy.deepcopy(labels)
        prediction[0][0] = [.4, 3.]
        score = V.scores(prediction, labels, masks, metadata, [0])
        self.assertEqual(score['endpoint_mae']['pooled'], 6.)
        self.assertEqual(score['nonzero_sign_accuracy'], 0.)
        self.assertEqual(score['eligibility']['positive_recall'], .5)
        bad = copy.deepcopy(labels); bad[1][1][1] = -1.
        with self.assertRaisesRegex(ValueError, 'observed native zero'): V.scores(prediction, bad, masks, metadata, [1])

    def test_damage_on_initially_healthy_target_is_not_healthy_heal_zero(self):
        labels, masks, metadata = observations(); metadata[2]['healthy_intent'] = True
        score = V.scores(labels, labels, masks, metadata, [2])
        self.assertEqual(score['healthy_count'], 0); self.assertIsNone(score['healthy_max_abs'])

    def test_gate_all_seeds_all_slices_and_separate_architecture_diagnostic(self):
        values = gate_inputs(); gate = V.gates(values)
        self.assertTrue(gate['usability_passed']); self.assertTrue(gate['architecture_diagnostic_passed'])
        self.assertFalse(gate['semantic_validated'])
        values['s29:new-full']['300']['held']['endpoint_mae']['base'] = .3
        gate = V.gates(values)
        self.assertFalse(gate['usability_passed']); self.assertTrue(gate['architecture_diagnostic_passed'])
        self.assertFalse(gate['per_seed']['29']['endpoint_slices_passed'])
        self.assertFalse(gate['per_seed']['17']['eligibility_discrimination_qualified'])

    def test_zero_printed_denominator_has_no_relative_improvement_fallback(self):
        gate = V.gates(gate_inputs(full=0., old=0., printed=0.))
        self.assertTrue(gate['usability_passed']); self.assertIsNone(gate['relative_improvement_vs_printed'])
        self.assertFalse(gate['architecture_diagnostic_passed'])
        gate = V.gates(gate_inputs(full=.2, old=.1, printed=1.))
        self.assertTrue(gate['usability_passed']); self.assertFalse(gate['architecture_diagnostic_passed'])

    def test_train_statistics_use_only_three_observed_strata(self):
        labels, masks, metadata = observations()
        saved = V.weight_statistics(labels, masks, [0, 2, 3], metadata)
        self.assertEqual(saved['class_statistics']['class_counts'], [2, 4])
        self.assertEqual(saved['class_statistics']['weights'], [1.5, .75])
        self.assertEqual(saved['stratum_statistics']['weights'], {'heal|unit': 1., 'damage|base': 1., 'damage|unit': 1.})
        self.assertEqual(saved['stratum_statistics']['absent_train_strata'], ['heal|base'])
        # HELD heal-base can have arbitrary unknown labels without entering counts.
        labels[1] = [[0., 77.], [0., -77.]]
        self.assertEqual(saved, V.weight_statistics(labels, masks, [0, 2, 3], metadata))
        with self.assertRaisesRegex(ValueError, 'stratum'): V.weight_statistics(labels, masks, [0, 1, 2, 3], metadata)

    def test_deferred_eval_counter_barrier_and_partial_completion_reject(self):
        events = counter_events()
        proof = V.counter_panel(events, updates=2, evaluations=1)
        self.assertTrue(proof['all_evaluation_after_last_update'])
        self.assertEqual(proof['training_forwards'], 2)
        bad = copy.deepcopy(events); bad[6]['data']['counter'] = 'neural_forwards'
        with self.assertRaisesRegex(ValueError, 'barrier'): V.counter_panel(bad, updates=2, evaluations=1)
        bad = copy.deepcopy(events); bad[-1]['data']['token'] += 1
        with self.assertRaisesRegex(ValueError, 'barrier'): V.counter_panel(bad, updates=2, evaluations=1)
        with self.assertRaisesRegex(ValueError, 'missing'): V.counter_panel(events[:-1], updates=2, evaluations=1)

    def test_checkpoint_named_hash_is_order_invariant_and_detects_corruption(self):
        first = dict(z=FakeArray(b'first'), a=FakeArray(b'second'))
        self.assertEqual(V.state_hash(first), V.state_hash(dict(reversed(list(first.items())))))
        self.assertNotEqual(V.state_hash(first), V.state_hash(dict(z=FakeArray(b'changed'), a=first['a'])))
        expected = {k: hashlib.sha256(b'float32(1,)' + a.raw).hexdigest() for k, a in first.items()}
        self.assertEqual(V.state_hash(first), V.sha(expected))

    def test_inherited_source_pin_is_required_and_conflicting_copies_reject(self):
        old = dict(path='/artificial/adapter.py', sha256='a' * 64, bytes=1)
        current = dict(path='/artificial/verifier.py', sha256='b' * 64, bytes=2)
        spec = dict(pins=[current], source=current, primitives=current)
        parent = dict(pins=[old], protected_files=[old])
        self.assertEqual(V.source_pins(spec, parent), {old['path']: old, current['path']: current})
        bad = copy.deepcopy(spec); bad['pins'].append(dict(old, sha256='c' * 64))
        with self.assertRaisesRegex(ValueError, 'conflicting'): V.source_pins(bad, parent)

    def test_exact_output_inventory_has_no_unallocated_checkpoint(self):
        files = V.fit_inventory()
        self.assertEqual(len(files), 44)
        self.assertIn('s17-new-full-step300-predictions.npz', files)
        self.assertNotIn('s17-new-full-step150-predictions.npz', files)

    def test_expected_graph_shapes_disclose_capacity_and_match_new_control(self):
        full = V.expected_shapes('new-full'); printed = V.expected_shapes('new-printed-only'); old = V.expected_shapes('old-late-fusion')
        self.assertEqual(full, printed)
        self.assertEqual(sum(math.prod(v) for v in full.values()), 1458)
        self.assertEqual(sum(math.prod(v) for v in old.values()), 1506)
        self.assertEqual(full['kind.0.weight'], (8, 6))
        self.assertEqual(old['paths.weight'], (23, 16))

    def test_claim_tree_rejects_hash_key_missing_nonfinite_and_boolean_number(self):
        V.close({'value': [1., None, False]}, {'value': [1., None, False]}, tolerance=0.)
        for bad in ({'value': [True, None, False]}, {'value': [float('nan'), None, False]}, {'other': [1., None, False]}):
            with self.assertRaises(ValueError): V.close(bad, {'value': [1., None, False]})


if __name__ == '__main__': unittest.main()
