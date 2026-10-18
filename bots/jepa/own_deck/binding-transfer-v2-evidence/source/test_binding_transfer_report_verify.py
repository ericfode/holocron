"""Synthetic saved-array checks only; no actual campaign, engine or model."""
import ast
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
import binding_transfer_report_verify as V


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
            accounting = root/'new-accounting.py'; accounting.write_text('synthetic byte pin only')
            events = []
            @contextmanager
            def lease():
                yield None, [], dict(config=dict(source=V.pin(accounting), pins=[dict(path=str(p), sha256='synthetic', bytes=0) for p in
                    (root/'plan.json', root/'recovered.json', root/'base/result.json', root/'fit.jsonl', root/'base.jsonl', root/'old-ledger.jsonl', root/'old-receipt.json')]))
            fake = SimpleNamespace(__file__=str(accounting), lease=lease,
                start=lambda *a: events.append('start'),
                state=lambda rows: dict(pending=dict(stage='verify', owner_pid=os.getpid())),
                zero_counts=lambda: {},
                finish=lambda *a, **kw: (events.append('finish-'+a[2]) or dict(completed_stages=[])))
            args = SimpleNamespace(plan=root/'plan.json', fit_dir=root/'fit', baselines_dir=root/'base',
                fit_progress=root/'fit.jsonl', baseline_progress=root/'base.jsonl',
                out=root/'result.json', receipt=root/'receipt.json', recovered_result=root/'recovered.json',
                failed_fit_ledger=root/'old-ledger.jsonl', failed_fit_receipt=root/'old-receipt.json')
            with patch.dict('sys.modules', binding_transfer_report_accounting=fake,
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

    def test_exact_reviewed_source_delta_preserves_all_scientific_code(self):
        old = Path(V.__file__).with_name('binding_transfer_repair_verify.py').read_text()
        actual = Path(V.__file__).read_text()
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), V.PREDECESSOR_VERIFIER_SHA)
        old_ast, new_ast = ast.parse(old), ast.parse(actual)
        expected = old.replace(ast.get_source_segment(old, old_ast.body[0]),
                               ast.get_source_segment(actual, new_ast.body[0]), 1)
        substitutions = [('binding_transfer_repair_accounting', 'binding_transfer_report_accounting', 3),
 ("current['cumulative']['charged_seconds'] <= 198.01331695669796",
  "current['cumulative']['charged_seconds'] <= 197.01759783166926",
  1),
 ("current['config']['caps']['seconds'] == 75.", "current['config']['caps']['seconds'] == 13.", 1),
 ("current['config']['parent']['charged_seconds'] == 123.01331695669796",
  "current['config']['parent']['charged_seconds'] == 184.01759783166926",
  1),
 ("PREDECESSOR_VERIFIER_SHA = '2adaed75d90abdc019e13685db84cf475ffdfa505e670f7bfd9e6c8cd219571f'",
  "PREDECESSOR_VERIFIER_SHA = 'cb0661bd71feeedfbacf8656d18bf9cd8013de87219e2b633d8546af90fbd675'\n"
  "PRIOR_LINKED_VERIFIER_SHA = '2adaed75d90abdc019e13685db84cf475ffdfa505e670f7bfd9e6c8cd219571f'",
  1),
 ("            require(pin(HERE/'binding_transfer_next_verify.py')['sha256'] == PREDECESSOR_VERIFIER_SHA, "
  "'exact frozen repair predecessor verifier')",
  "            require(pin(HERE/'binding_transfer_next_verify.py')['sha256'] == PRIOR_LINKED_VERIFIER_SHA, "
  "'exact frozen linked verifier')\n"
  "            require(pin(HERE/'binding_transfer_repair_verify.py')['sha256'] == PREDECESSOR_VERIFIER_SHA, "
  "'exact frozen report predecessor verifier')",
  1),
 ("                    predecessor=pin(HERE/'binding_transfer_next_verify.py'),",
  "                    predecessor=pin(HERE/'binding_transfer_repair_verify.py'),\n"
  "                    prior_linked=pin(HERE/'binding_transfer_next_verify.py'),",
  1),
 ("args.fit_dir/'result.json'", 'args.recovered_result', 3),
 ("        required = [args.plan, args.recovered_result, args.baselines_dir/'result.json', "
  'args.fit_progress, args.baseline_progress]',
  "        required = [args.plan, args.recovered_result, args.baselines_dir/'result.json', "
  'args.fit_progress, args.baseline_progress, args.failed_fit_ledger, args.failed_fit_receipt]',
  1),
 ("'all five verifier inputs must be frozen or completed-stage proofs'",
  "'all seven verifier inputs must be exact frozen or completed-stage pins'",
  1),
 ("for name in ('plan', 'fit-dir', 'fit-progress', 'baselines-dir', 'baseline-progress', 'out', 'receipt'):",
  "for name in ('plan', 'fit-dir', 'fit-progress', 'baselines-dir', 'baseline-progress', 'out', 'receipt', "
  "'recovered-result', 'failed-fit-ledger', 'failed-fit-receipt'):",
  1),
 ('    plan, fit, base = read(args.plan), read(args.recovered_result), '
  "read(args.baselines_dir/'result.json')",
  '    plan, fit, base = read(args.plan), read(args.recovered_result), '
  "read(args.baselines_dir/'result.json')\n"
  '    failed_origin = recovered_fit_origin(args, fit, allowed, current)',
  1),
 ('                input_pins=list(inputs.values()), semantic_validated=False, '
  "generic_semantic_gate='UNSUPPORTED',",
  '                input_pins=list(inputs.values()), recovered_failed_fit_origin=failed_origin,\n'
  "                saved_fit_journal_scope='Historical durable prefix only; original failed fit observations "
  "remain unknown and no new neural work is allocated.',\n"
  "                semantic_validated=False, generic_semantic_gate='UNSUPPORTED',",
  1),
 ("change_scope='Two budget/carry checks and explicit accounting/provenance only; scientific checks "
  "unchanged.'",
  "change_scope='Accounting/budgets, explicit recovered-result route and failed-fit provenance only; "
  "scientific checks unchanged.'",
  1)]
        for before, after, count in substitutions:
            self.assertEqual(expected.count(before), count)
            expected = expected.replace(before, after)
        # The only new helper is the separately tested stdlib provenance audit.
        helper = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'recovered_fit_origin')
        expected = expected.replace('def verify_saved(np, args, allowed, current):',
                                    ast.get_source_segment(actual, helper) + '\n\n\ndef verify_saved(np, args, allowed, current):', 1)
        self.assertEqual(expected, actual)

    def test_new_budget_checks_accept_only_the_linked_amended_envelope(self):
        source = Path(V.__file__).read_text()
        tree = ast.parse(source)
        names = {'carried-global-local-bound', 'unchanged-cumulative-cap-failed-charge-dollar-carry'}
        expressions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'check':
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and node.args[1].value in names:
                    expressions[node.args[1].value] = compile(ast.Expression(node.args[0]), '<budget-check>', 'eval')
        self.assertEqual(set(expressions), names)
        current = dict(cumulative=dict(charged_native_applies=208, charged_seconds=197.01759783166926,
                                       observed_native_applies=None),
            config=dict(caps=dict(seconds=13., native_applies=0), parent=dict(
                charged_native_applies=208, charged_seconds=184.01759783166926,
                historical_modal_ceiling_usd=100., historical_modal_minimum_reserve_usd=25., paid_spend_usd=0.)))
        def evaluate(value):
            return {k: eval(code, {'__builtins__': {}}, {'current': value}) for k, code in expressions.items()}
        self.assertTrue(all(evaluate(current).values()))
        wrong = copy.deepcopy(current); wrong['cumulative']['charged_native_applies'] = 209
        self.assertFalse(evaluate(wrong)['carried-global-local-bound'])
        wrong = copy.deepcopy(current); wrong['cumulative']['charged_seconds'] += .01
        self.assertFalse(evaluate(wrong)['carried-global-local-bound'])
        wrong = copy.deepcopy(current); wrong['cumulative']['observed_native_applies'] = 0
        self.assertFalse(evaluate(wrong)['carried-global-local-bound'])
        wrong = copy.deepcopy(current); wrong['config']['parent']['charged_native_applies'] = 112
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['parent']['charged_seconds'] = 110.10179149871692
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['parent']['charged_seconds'] -= 5.
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['parent']['charged_native_applies'] = 160
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['caps']['native_applies'] = 48
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['caps']['seconds'] = 125.
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])
        wrong = copy.deepcopy(current); wrong['config']['parent']['paid_spend_usd'] = 1.
        self.assertFalse(evaluate(wrong)['unchanged-cumulative-cap-failed-charge-dollar-carry'])

    def test_exact_failed_origin_stays_failed_unknown_and_gradients_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt_path, ledger_path, progress_path = (root/n for n in ('receipt.json', 'ledger.jsonl', 'progress.jsonl'))
            receipt = dict(status='failed', error=dict(type='TypeError', message='Object of type int64 is not JSON serializable'),
                           observed=dict(neural_forwards=None, optimizer_updates=None))
            receipt_path.write_text(json.dumps(receipt)); progress_path.write_text('{"synthetic":true}\n')
            records = []
            previous = '0'*64
            for event, data in [('initialized', {}), ('stage-finish', dict(stage='fit', status='failed',
                    charged=dict(seconds=60.), observed=dict(neural_forwards=None, optimizer_updates=None),
                    proofs=[V.pin(receipt_path)]))]:
                body = dict(sequence=len(records), previous_sha256=previous, event=event, data=data)
                encoded = json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                previous = hashlib.sha256(encoded).hexdigest()
                records.append(dict(body, record_sha256=previous))
            ledger_path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            args = SimpleNamespace(failed_fit_ledger=ledger_path, failed_fit_receipt=receipt_path, fit_progress=progress_path)
            pins = {k: V.pin(p) for k, p in [('failed_fit_ledger', ledger_path), ('failed_fit_receipt', receipt_path), ('fit_progress', progress_path)]}
            allowed = {p['path']: p for p in pins.values()}
            current = dict(config=dict(closed_parent_journals=[dict(pin=pins['failed_fit_ledger'], final_record_sha256=previous)]))
            fit = dict(status='recovered-from-saved-artifacts', original_fit_status='failed', recovery_provenance=pins,
                       results={'synthetic-arm': dict(last_step_preclip_gradients=None)})
            result = V.recovered_fit_origin(args, fit, allowed, current)
            self.assertEqual(result['original_fit_status'], 'failed')
            self.assertIsNone(result['observed_neural_forwards'])
            self.assertEqual(result['full_failed_charge_seconds'], 60.)
            changed = copy.deepcopy(fit); changed['status'] = 'completed'
            with self.assertRaises(ValueError): V.recovered_fit_origin(args, changed, allowed, current)
            changed = copy.deepcopy(fit); changed['results']['synthetic-arm']['last_step_preclip_gradients'] = {'fabricated': 0}
            with self.assertRaises(ValueError): V.recovered_fit_origin(args, changed, allowed, current)
            changed = copy.deepcopy(fit); changed['recovery_provenance']['failed_fit_receipt']['sha256'] = '0'*64
            with self.assertRaises(ValueError): V.recovered_fit_origin(args, changed, allowed, current)
            receipt['observed']['neural_forwards'] = 0
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError): V.recovered_fit_origin(args, fit, allowed, current)


if __name__ == '__main__':
    unittest.main()
