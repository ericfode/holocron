"""Synthetic primitive regressions only; no NumPy, model, native, or saved data."""
import ast
import copy
import math
from pathlib import Path
import unittest

import real_ir_intent_verify as I


def events(updates=2, evaluations=1):
    names = [k for _ in range(updates) for k in ('neural_forwards', 'backwards', 'optimizer_updates')]
    names += ['neural_forwards'] * evaluations
    result = []
    for i, name in enumerate(names):
        token = 100 + 2 * i
        result.extend([dict(event='intent', sequence=token, data=dict(token=token, counter=name, amount=1)),
            dict(event='complete', sequence=token + 1, data=dict(token=token, actual=None, proofs=[]))])
    return result


def metric(mae=.1):
    return dict(endpoint_mae={k: mae for k in ('pooled', 'unit', 'base', 'damage', 'heal')},
        undefined=[], nonzero_sign_accuracy=1., healthy_max_abs=0.,
        eligibility=dict(balanced_accuracy=1., positive_recall=1.))


def panel(mae=.1, programs=7):
    return dict(raw=metric(mae), routed=metric(mae), typed_intent=dict(programs=programs, identity_accuracy=1., amount_mae=0.))


def methods():
    result = {}
    for seed in I.SEEDS:
        for arm in I.ARMS:
            result[f's{seed}:{arm}'] = dict(evaluations={'300': dict(train=panel(), exposed=panel(),
                development_primary=panel(1. if arm == 'matched-aux-latent' else .1), terminal=panel(programs=1))})
    return result


class Tests(unittest.TestCase):
    def test_no_numeric_model_training_or_engine_imports(self):
        tree = ast.parse(Path(I.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'math', 'os', 'real_ir_transfer_verify', 'real_ir_intent_data'})
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in
            ('make_model', 'backward', 'step', 'fit_head', 'fit_worker', 'score_worker') for n in ast.walk(tree)))
        self.assertNotIn('np', vars(I))

    def test_parameter_keys_and_nominal_counts(self):
        original = I.shapes('current')
        self.assertEqual(sum(math.prod(s) for s in original.values()), 1458)
        a, b = I.shapes('matched-aux-latent'), I.shapes('factorized-intent')
        self.assertEqual(a, b)
        self.assertEqual(sum(math.prod(s) for s in a.values()), 1517)
        self.assertTrue(set(original) < set(a))
        with self.assertRaises(ValueError): I.shapes('invented')

    def test_only_fixed18_checkpoints_and24_scores(self):
        self.assertEqual(len(I.fit_inventory()), 25)
        self.assertEqual(len(I.score_prediction_inventory()), 24)
        self.assertNotIn('s17-current-step0-predictions.npz', I.fit_inventory())
        self.assertNotIn('s17-frozen-printed-step0-predictions.npz', I.score_prediction_inventory())

    def test_training_then_separate_score_call_panels(self):
        self.assertEqual(I.counter_panel(events(), updates=2, evaluations=1)['evaluation_forwards'], 1)
        self.assertEqual(I.counter_panel(events(0, 2), updates=0, evaluations=2)['backwards'], 0)
        bad = events(); bad[0]['data']['counter'] = 'numerical_fits'
        with self.assertRaisesRegex(ValueError, 'barrier'): I.counter_panel(bad, updates=2, evaluations=1)
        with self.assertRaisesRegex(ValueError, 'missing'): I.counter_panel(events()[:-1], updates=2, evaluations=1)

    def test_raw_known_native_only_zero_probability_undefined(self):
        prediction = [[[.5, -1.], [0., 999.]], [[0., 0.], [1., 0.]]]
        labels = [[[1., -2.], [0., 123.]], [[1., 3.], [1., 0.]]]
        masks = [[[1., 1.], [1., 0.]], [[1., 1.], [1., 1.]]]
        metadata = [dict(operator='heal', intent_domain='unit', healthy_intent=False),
            dict(operator='heal', intent_domain='base', healthy_intent=True)]
        actual = I.raw_scores(prediction, labels, masks, metadata, [0, 1])
        self.assertEqual(actual['endpoint_mae']['pooled'], 0.)
        self.assertEqual(actual['endpoint_support']['pooled'], 2)
        self.assertEqual(actual['undefined'], [[1, 0]])
        self.assertEqual(actual['healthy_max_abs'], 0.)
        self.assertEqual(actual['endpoints'][0]['prediction'], -2.)

    def test_unique_program_typed_support_and_state_invariance(self):
        programs = [[0.] * 10 + [1., 0., 3.], [0.] * 10 + [0., 1., 2.]]
        actual = I.typed_scores([[2., 0.], [2., 0.], [0., 1.]], [3., 3., 2.], [0, 0, 1], programs, [0, 1, 2])
        self.assertEqual(actual['programs'], 2)
        self.assertEqual(actual['identity_accuracy'], 1.)
        self.assertEqual(actual['amount_mae'], 0.)
        self.assertEqual(actual['per_program'][0]['roots'], 2)
        with self.assertRaisesRegex(ValueError, 'public states'):
            I.typed_scores([[2., 0.], [2., .1]], [3., 3.], [0, 0], programs, [0, 1])
        self.assertIsNone(I.typed_scores(None, None, [], [], []))

    def test_cached_slices_preserve_source_joint_and_terminal_seen_unknown(self):
        points = [dict(root=0, candidate=0, truth=3., prediction=2., error=1., operator='damage', domain='unit', healthy=False),
            dict(root=112, candidate=0, truth=3., prediction=-1., error=4., operator='damage', domain='unit', healthy=False)]
        raw = dict(endpoints=[dict(root=0, candidate=0, prediction=3., error=0.)])
        metadata = [dict(source_card='event', amount=3, program_index=0)] + [{}] * 111 + [dict(source_card='SOR_132', amount=3, program_index=0)]
        public = [[dict(owner='p1', zone='space', damage=1, hp=10)]] + [[]] * 111 + [[dict(owner='p2', zone='space', damage=4, hp=10)]]
        programs = [dict(selector=dict(cost_cap=dict(present=False, value=None)))]
        actual = I.endpoint_slices(dict(endpoints=points), raw, metadata, public, programs, [])
        self.assertEqual(actual['tables']['source_card']['event']['raw_mae'], 0.)
        self.assertIsNone(actual['tables']['source_card']['SOR_132']['raw_mae'])
        self.assertIsNone(actual['rows'][1]['prior_seen'])
        self.assertEqual(actual['tables']['operator']['damage']['routed_mae'], 2.5)
        self.assertEqual(actual['tables']['operator']['damage']['sources'], 2)
        self.assertEqual(len(actual['tables']['joint']), 2)

    def test_separate_development_terminal_and_undefined_gates(self):
        values = methods(); decision = I.decisions(values)
        self.assertTrue(decision['development_passed']); self.assertTrue(decision['terminal_passed'])
        values['s29:factorized-intent']['evaluations']['300']['terminal']['routed']['eligibility']['balanced_accuracy'] = None
        decision = I.decisions(values)
        self.assertTrue(decision['development_passed']); self.assertFalse(decision['terminal_passed'])
        values['s17:factorized-intent']['evaluations']['300']['development_primary']['raw']['undefined'] = [[56, 2]]
        self.assertFalse(I.decisions(values)['development_passed'])
        values = methods()
        values['s43:matched-aux-latent']['evaluations']['300']['development_primary']['routed']['endpoint_mae']['pooled'] = 0.
        decision = I.decisions(values)
        self.assertFalse(decision['development_passed'])
        self.assertIsNone(decision['per_seed']['43']['development_routed_relative_improvement'])

    def test_no_missing_slice_or_missing_typed_support_pass(self):
        values = methods()
        values['s17:factorized-intent']['evaluations']['300']['development_primary']['raw']['endpoint_mae']['base'] = None
        self.assertFalse(I.decisions(values)['development_passed'])
        values = methods()
        values['s29:factorized-intent']['evaluations']['300']['exposed']['typed_intent']['programs'] = 0
        self.assertFalse(I.decisions(values)['development_passed'])
        gate = I.endpoint_gate(dict(metric(), healthy_max_abs=None), require_all_slices=True)
        self.assertIsNone(gate['healthy_max_abs_passed'])

    def test_all_checkpoint_pins_must_precede_terminal(self):
        proofs = [dict(path='/scratch/' + n, sha256=str(i).zfill(64), bytes=1) for i, n in enumerate(sorted(I.fit_inventory()))]
        names = [p['path'] for p in proofs]
        self.assertTrue(I.terminal_boundary(proofs, copy.deepcopy(proofs), names))
        with self.assertRaisesRegex(ValueError, 'before terminal'):
            I.terminal_boundary(proofs, proofs[:-1], names)
        bad = copy.deepcopy(proofs); bad[0]['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'before terminal'):
            I.terminal_boundary(proofs, bad, names)

    def test_chain_detects_rewrite_and_truncation_claim(self):
        records = []
        previous = '0' * 64
        for i, event in enumerate(('initialized', 'finish')):
            body = dict(schema='synthetic/1', sequence=i, previous_sha256=previous, event=event, data={})
            previous = I.V.sha(body); records.append(dict(body, record_sha256=previous))
        self.assertEqual(I.chain(records), previous)
        records[0]['data']['rewritten'] = True
        with self.assertRaisesRegex(ValueError, 'chain'): I.chain(records)


if __name__ == '__main__': unittest.main()
