"""Artificial metadata/temporary byte fixtures only; no actual saved analysis."""
import ast
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import real_ir_intent_recovery_campaign as C


def failure():
    state = dict(completed=C.ORDER[:-1], failures=1, pending=None, violated=False, last_sha256='a' * 64)
    last = dict(event='finish', record_sha256='a' * 64,
        data=dict(status='failed', cleanup_verified=True, execution_ended=True, integrity_error=None,
            charged=dict(seconds=10., **C.ZERO), durable_intents=dict(C.ZERO), durable_completed=dict(C.ZERO)))
    receipt = dict(stage='verify', status='failed', cleanup_verified=True, error=dict(type='KeyError', message="'schema'"))
    return state, last, receipt


class RecoveryContracts(unittest.TestCase):
    def test_only_exact_ended_original_failure_is_admitted(self):
        values = failure(); C.original_failure(*values)
        snapshot = copy.deepcopy(values); self.assertEqual(values, snapshot)
        for path, value in ((('state', 'completed'), C.ORDER), (('state', 'pending'), {}),
                (('state', 'failures'), 2), (('last', 'status'), 'completed'),
                (('last', 'charged'), dict(seconds=0., **C.ZERO)),
                (('last', 'durable_completed'), dict(C.ZERO, neural_forwards=1)),
                (('receipt', 'error'), dict(type='KeyError', message="'other'"))):
            a, b, c = copy.deepcopy(values)
            obj = a if path[0] == 'state' else b['data'] if path[0] == 'last' else c
            obj[path[1]] = value
            with self.assertRaises(ValueError): C.original_failure(a, b, c)

    def test_descriptor_is_single20second_zero_call_stage(self):
        d = C.descriptor('/toy/python3', '/toy/wrapper.py', '/toy/new')
        self.assertEqual(d['argv'], ['/toy/python3', '/toy/wrapper.py', 'run', '--spec', '/toy/new/campaign-spec.json'])
        self.assertEqual(d['outputs'], ['/toy/new/verify-1', '/toy/new/verify-1-stage-receipt.json'])
        self.assertEqual(d['reservation'], dict(seconds=20., **C.ZERO)); self.assertEqual(d['expected'], C.ZERO)
        self.assertEqual(d['external_counters'], [])

    def test_import_writes_nothing_and_loads_no_scientific_framework(self):
        original = Path.open
        def readonly(path, mode='r', *args, **kwargs):
            self.assertFalse(any(c in mode for c in 'wax+'))
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', readonly):
            loader = importlib.util.spec_from_file_location('saved_intent_import_test', C.__file__)
            module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
        tree = ast.parse(Path(C.__file__).read_text())
        top = [a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names]
        self.assertNotIn('numpy', top); self.assertNotIn('torch', top)

    def test_only_new_sidecar_opens_lease_and_old_root_is_read_only(self):
        tree = ast.parse(Path(C.__file__).read_text()); functions = {n.name: ast.unparse(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertNotIn('.lease(', functions['closed_original']); self.assertNotIn('.initialize(', functions['closed_original'])
        self.assertIn("D.write_new(ORIGINAL / 'experiment-closure.json'", functions['close_failed'])
        self.assertIn("parent['protected_roots'].append(str(ORIGINAL))", functions['prepare'])
        self.assertIn('D.closed_journal(prior.ledger)', functions['prepare'])
        self.assertLess(functions['stage'].index('run.begin('), functions['stage'].index('exact sealed saved-verification runtime required'))
        self.assertIn("importlib.import_module('real_ir_intent_verify_v2').verify(np, ORIGINAL, out)", functions['stage'])
        self.assertIn('E.Guard(run.remaining_seconds())', functions['stage'])
        self.assertNotIn('run.intent(', functions['stage'])

    def test_zero_call_toy_sidecar_carries_prior_charge_and_unknownness(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve(); root = base / 'saved'; root.mkdir()
            script = base / 'toy.py'; script.write_text('# never executed\n')
            parent = base / 'parent.json'; carry = dict(charged_native_applies=999, charged_seconds=123.5, observed_native_applies=None)
            parent.write_bytes(C.S.encoded(dict(carry=carry, pins=[], protected_files=[], protected_roots=[], closed_journals=[])))
            py = str(Path(sys.executable).resolve()); descriptor = C.descriptor(py, script, root)
            spec = dict(schema=C.S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=C.S.pin(C.S.__file__),
                primitives=C.S.pin(C.S._PATH), ledger_path=str(root / 'campaign-ledger.jsonl'), caps=dict(seconds=20., **C.ZERO),
                guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=['verify'], stages=dict(verify=descriptor),
                parent_manifest=C.S.pin(parent), pins=[C.S.pin(py), C.S.pin(script)])
            path = root / 'campaign-spec.json'; path.write_bytes(C.S.encoded(spec)); budget = C.S.Budget(path)
            budget.initialize(root_go=True)
            with budget.lease() as run:
                run.begin('verify', argv=descriptor['argv'], guard=spec['guard'])
                self.assertEqual(abs(-4), 4)  # harmless stand-in, never a saved artifact analysis
                state = run.finish('completed', cleanup_verified=True, execution_ended=True)
            self.assertEqual(state['completed'], ['verify']); self.assertEqual(state['charged']['native_applies'], 0)
            self.assertEqual(state['charged']['neural_forwards'], 0); self.assertEqual(state['cumulative']['charged_native_applies'], 999)
            self.assertGreater(state['cumulative']['charged_seconds'], 123.5)
            self.assertIsNone(state['cumulative']['observed_native_applies'])
            with self.assertRaises(ValueError): budget.initialize(root_go=True)


if __name__ == '__main__': unittest.main()
