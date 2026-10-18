"""Synthetic saved-array checks only; no actual campaign, engine or model."""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import binding_transfer_verify as V


def public_fixture():
    order = ['source', 'a', 'b', 'enemy', 'none1', 'none2', 'none3', 'none4']
    def unit(identity, code, owner, zone='ground'):
        return dict(id=identity, code=code, owner=owner, zone=zone, is_unit=True, present=True,
                    known=dict(identity=True, owner=True, printed_aspects=True))
    p = dict(source=unit('s', 'SRC', 'p1', 'hand'), a=unit('a', 'HOST', 'p1'),
             b=unit('b', 'HOST', 'p1'), enemy=unit('e', 'ENEMY', 'p2'))
    p.update({k: None for k in order[4:]})
    refs = {k: v['id'] if v else None for k, v in p.items()}
    record = dict(before=dict(projections=p, state=dict(players=dict(
        p1=dict(ground=[dict(id='a'), dict(id='b')], space=[]),
        p2=dict(ground=[dict(id='e')], space=[])))), refs=refs,
        declared_intent=dict(ref='a', id='a', requires_target=True), observation_refs=['a', 'b'])
    arrays = dict(context_features=np.zeros((26, 18), np.float32), candidate_features=np.zeros((26, 8, 34), np.float32))
    manifest = dict(candidate_order=order, public_before_records=[copy.deepcopy(record) for _ in range(26)],
                    public_catalog_rows={c: dict(card=dict(aspects=a)) for c, a in
                                         [('SRC', ['heroism']), ('HOST', ['command']), ('ENEMY', ['vigilance'])]})
    return arrays, manifest


class VerificationTests(unittest.TestCase):
    def test_root_average_is_not_coordinate_average(self):
        y = np.zeros((2, 3), np.float32)
        p = np.asarray([[3, 999, 999], [1, 1, 1]], np.float32)
        m = np.asarray([[1, 0, 0], [1, 1, 1]], np.float32)
        r = V.head_metrics(np, p, y, m, np.asarray([0, 1]), dict(binary=False, scale=2.))
        self.assertEqual(r['mae'], 2.)
        self.assertEqual(r['train_scaled_mae'], 1.)
        self.assertEqual(r['known_coordinates'], 4)
        self.assertAlmostEqual(r['rmse'], np.sqrt(3.), places=6)
        self.assertEqual(r['zero_sign_accuracy'], 0.)

    def test_binary_balance_and_unknowns(self):
        r = V.head_metrics(np, np.asarray([.9, .2, 999.]), np.asarray([1., 0., 0.]),
                           np.asarray([1., 1., 0.]), np.arange(3), dict(binary=True, scale=1.))
        self.assertEqual(r['balanced_accuracy'], 1.)
        self.assertEqual(r['observed_roots'], 2)
        self.assertIsNone(r['zero_sign_accuracy'])
        empty = V.head_metrics(np, np.zeros(3), np.zeros(3), np.zeros(3), np.asarray([], np.int64), dict(binary=False, scale=1.))
        self.assertIsNone(empty['mae'])
        self.assertEqual(empty['known_coordinates'], 0)

    def test_baseline_zero_relative_gain_is_null(self):
        self.assertIsNone(V.improvement(0., 0.)['relative_error_reduction'])
        self.assertIsNone(V.improvement(1., 0.)['ten_percent_improvement'])
        self.assertTrue(V.improvement(.8, 1.)['ten_percent_improvement'])
        self.assertEqual((V.sign(-.25), V.sign(.25), V.sign(.251)), (0, 0, 1))

    def test_public_owner_counts_intent_passive_and_no_future(self):
        arrays, manifest = public_fixture()
        x, c = V.public_projection(np, arrays, manifest)
        self.assertEqual(x[0, 19], 2)  # self command count
        self.assertEqual(x[0, 25], 1)  # opposing vigilance count
        self.assertEqual(x[0, 22], 0)  # own hand source is not inserted
        self.assertEqual(c[0, 1, 41], 1)
        changed = copy.deepcopy(manifest)
        for row in changed['public_before_records']:
            row['before']['state']['players']['p2']['hand'] = ['private-poison']
            row['before']['unused_after_state'] = dict(label=999)
        a, b = V.public_projection(np, arrays, changed)
        np.testing.assert_array_equal(x, a); np.testing.assert_array_equal(c, b)
        changed['public_before_records'][0]['declared_intent']['requires_target'] = False
        self.assertFalse(V.public_projection(np, arrays, changed)[1][0, :, 41:].any())
        changed['public_before_records'][0]['after'] = dict(label=1)
        with self.assertRaises(ValueError):
            V.public_projection(np, arrays, changed)

    def test_masks_are_applied_after_shared_nonzero_center(self):
        arrays, manifest = public_fixture(); x, c = V.public_projection(np, arrays, manifest)
        scalers = {key: dict(center=[.5]*width, scale=[2.]*width) for key, width in
                   [('context_features', 32), ('candidate_features', 43)]}
        a, b = V.normalized_inputs(np, x, c, scalers, 'C0R0')
        self.assertFalse(a[:, 18:].any()); self.assertFalse(b[:, :, 34:].any())
        self.assertEqual(a[0, 0], -.25)

    def test_independent_hash_chain_rejects_tamper(self):
        body = dict(sequence=0, previous_sha256='0'*64, event='synthetic', data=dict(x=1))
        row = dict(body, record_sha256=hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.assertEqual(V.independent_chain([row]), row['record_sha256'])
        row['data']['x'] = 2
        with self.assertRaises(ValueError):
            V.independent_chain([row])

    def test_complete_named_initialization_hash(self):
        first = dict(a=np.asarray([1, 2], np.float32), b=np.asarray([3], np.int64))
        self.assertEqual(V.named_tensor_hash(first), V.named_tensor_hash(dict(reversed(list(first.items())))))
        other = dict(first); other['a'] = first['a'].copy(); other['a'][0] = 0
        self.assertNotEqual(V.named_tensor_hash(first), V.named_tensor_hash(other))
        self.assertNotEqual(V.named_tensor_hash(first), V.named_tensor_hash(dict(a=first['a'])))

    def test_guard_validation_failure_is_already_reserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bad = root/'wrong-guard.py'; bad.write_text('not executed')
            events = []
            @contextmanager
            def lease():
                yield None, [], dict(config=dict(pins=[dict(path=str(p), sha256='synthetic', bytes=0) for p in
                    (root/'plan.json', root/'fit/result.json', root/'base/result.json', root/'fit.jsonl', root/'base.jsonl')]))
            fake = SimpleNamespace(lease=lease,
                start=lambda *a: events.append('start'),
                state=lambda rows: dict(pending=dict(stage='verify', owner_pid=os.getpid())),
                zero_counts=lambda: {},
                finish=lambda *a, **kw: (events.append('finish-'+a[2]) or dict(completed_stages=[])))
            args = SimpleNamespace(plan=root/'plan.json', fit_dir=root/'fit', baselines_dir=root/'base',
                fit_progress=root/'fit.jsonl', baseline_progress=root/'base.jsonl',
                out=root/'result.json', receipt=root/'receipt.json')
            with patch.dict('sys.modules', binding_transfer_accounting=fake,
                            effect_identifiability_fit=SimpleNamespace(__file__=str(bad))):
                with self.assertRaises(ValueError):
                    V.run(args)
            self.assertEqual(events, ['start', 'finish-failed'])
            self.assertEqual(json.loads(args.receipt.read_text())['status'], 'failed')

    def test_forbidden_imports_and_process_actions(self):
        for event, args in [('import', ('torch',)), ('subprocess.Popen', ())]:
            with self.assertRaises(RuntimeError):
                V.audit_event(event, args)
        V.audit_event('import', ('numpy',))


if __name__ == '__main__':
    unittest.main()
