"""Synthetic bookkeeping/metadata contracts only; no actual campaign or science."""
import ast
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import real_ir_intent_campaign as C


class CampaignContracts(unittest.TestCase):
    def descriptors(self):
        return C.descriptors('/toy/python3', Path('/toy/new'), Path('/toy/wrapper.py'))

    def test_fixed_order_and_counters_no_fit_evaluation(self):
        stages = self.descriptors()
        self.assertEqual(list(stages), ['build', 'dev-native', 'prep', 'fit',
            'terminal-native', 'terminal-prep', 'score', 'verify'])
        self.assertEqual({k: sum(d['reservation'][k] for d in stages.values()) for k in C.CAPS}, C.CAPS)
        self.assertEqual(stages['fit']['reservation'], dict(C.ZERO, seconds=90.,
            neural_forwards=2700, backwards=2700, optimizer_updates=2700))
        self.assertEqual(stages['score']['reservation'], dict(C.ZERO, seconds=20., neural_forwards=24))
        self.assertLess(list(stages).index('fit'), list(stages).index('terminal-native'))
        self.assertLess(list(stages).index('terminal-prep'), list(stages).index('score'))

    def test_native_actual_unknown_and_other_counts_exact(self):
        stages = self.descriptors()
        for name, d in stages.items():
            self.assertEqual(d['argv'], ['/toy/python3', '/toy/wrapper.py', 'run', '--stage', name,
                '--spec', '/toy/new/campaign-spec.json'])
            self.assertEqual(d['outputs'], ['/toy/new/' + name + '-1', '/toy/new/' + name + '-1-stage-receipt.json'])
            native = name in ('dev-native', 'terminal-native')
            self.assertEqual(d['external_counters'], ['native_applies'] if native else [])
            self.assertEqual(d['expected']['native_applies'], None if native else 0)
            self.assertEqual(d['expected']['numerical_fits'], 0)
            self.assertEqual(d['expected']['paid_jobs'], 0)
        self.assertEqual(stages['dev-native']['reservation']['native_applies'], 200)
        self.assertEqual(stages['terminal-native']['reservation']['native_applies'], 40)

    def test_reservation_amendment_preserves_old_and_two_future_groups(self):
        old = dict(status='reserved-no-new-outcomes', reserved_codes=['ASH_259', 'HMW_158', 'LOF_259', 'SOR_132'], cards=[dict(opaque='whole raw rows')])
        p = dict(path='/toy/reservation.json', sha256=C.RESERVATION_SHA, bytes=39954)
        declaration = dict(schema='jepa-real-ir-intent-reservation-amendment/1', released_terminal_source='SOR_132',
            remaining_reserved_codes=['ASH_259', 'LOF_259', 'HMW_158'],
            native_outcome_order=['development', 'all-fitted-checkpoints-sealed', 'terminal'])
        snapshot = copy.deepcopy((old, p, declaration)); result = C.amendment(old, p, declaration)
        self.assertEqual((old, p, declaration), snapshot)
        self.assertEqual(result['original_reservation'], p)
        self.assertEqual(result['remaining_reserved_codes'], ['ASH_259', 'HMW_158', 'LOF_259'])
        self.assertEqual(result['remaining_conservative_groups'], [['ASH_259', 'LOF_259'], ['HMW_158']])
        self.assertFalse(result['semantic_validated'])
        for change in ('release', 'pin', 'order'):
            a, b, d = copy.deepcopy(snapshot)
            if change == 'release': d['released_terminal_source'] = 'HMW_158'
            if change == 'pin': b['sha256'] = '0' * 64
            if change == 'order': d['native_outcome_order'].reverse()
            with self.assertRaises(ValueError): C.amendment(a, b, d)

    def test_panel_roles_quantities_and_no_unreleased_source(self):
        panels = dict(preregistration={})
        for name, n, cap, seconds in (('development', 56, 200, 30), ('terminal', 8, 40, 15)):
            panels[name] = dict(panel_role=name, expected_cases=n, worlds=[{}] * n,
                collector_max_engine_applies=cap, collector_max_seconds=seconds,
                terminal_outcomes_after_all_checkpoints=name == 'terminal',
                selected_whole_cards=['TOY_HELPER'] + (['SOR_132'] if name == 'terminal' else []))
        C.validate_panels(panels)
        for name, key, value in (('development', 'expected_cases', 55),
                ('terminal', 'terminal_outcomes_after_all_checkpoints', False),
                ('terminal', 'selected_whole_cards', ['SOR_132', 'LOF_259'])):
            wrong = copy.deepcopy(panels); wrong[name][key] = value
            with self.assertRaises(ValueError): C.validate_panels(wrong)

    def test_quantity_and_reference_admission_is_fail_closed(self):
        m = dict(schema='jepa-real-ir-intent-data/1', fit_admitted=True, fit_blockers=[],
            reference=dict(known_coordinates=371, known_eligibility=336, known_intended_deltas=35,
                mismatch_count=0, removed_count=1, removal_mismatch_count=0),
            support=dict(development_known_endpoints=35, primary=29, replay=6, removed=1),
            terminal_admitted=True, terminal_blockers=[], terminal_reference=dict(known_coordinates=52,
                known_eligibility=48, known_intended_deltas=4, mismatch_count=0, removed_count=0, removal_mismatch_count=0))
        C.admit_data(m); C.admit_data(m, terminal=True)
        m['reference']['mismatches'] = []; m['terminal_reference']['mismatches'] = []
        C.admit_data(m, terminal=True)
        for key, value in (('fit_admitted', False), ('fit_blockers', ['unknown']),
                ('support', dict(development_known_endpoints=36, primary=30, replay=6, removed=0)),
                ('reference', dict(mismatch_count=1)), ('terminal_admitted', False),
                ('terminal_reference', dict(mismatch_count=1)),
                ('reference', dict(m['reference'], mismatches=[dict(opaque='disagreement')]))):
            wrong = copy.deepcopy(m); wrong[key] = value
            with self.assertRaises(ValueError): C.admit_data(wrong, terminal=True)

    def test_import_has_no_writes_or_scientific_imports(self):
        original = Path.open
        def readonly(path, mode='r', *args, **kwargs):
            self.assertFalse(any(c in mode for c in 'wax+'), 'source import must not create files')
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', readonly):
            loader = importlib.util.spec_from_file_location('intent_campaign_import_test', C.__file__)
            module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
        tree = ast.parse(Path(C.__file__).read_text())
        top_imports = [alias.name.split('.')[0] for node in tree.body if isinstance(node, ast.Import) for alias in node.names]
        self.assertNotIn('numpy', top_imports); self.assertNotIn('torch', top_imports)
        self.assertEqual(C.CARRY, dict(charged_native_applies=1031, charged_seconds=313.4962767929537, observed_native_applies=None))

    def test_runtime_mismatch_is_after_begin_and_before_guard_import(self):
        tree = ast.parse(Path(C.__file__).read_text()); stage = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'stage')
        body = ast.unparse(stage)
        self.assertLess(body.index('run.begin('), body.index('exact sealed runtime command required'))
        self.assertLess(body.index('exact sealed runtime command required'), body.index("importlib.import_module('effect_identifiability_fit')"))
        self.assertIn("argv=descriptor['argv']", body)
        self.assertIn('E.Guard(run.remaining_seconds())', body)
        self.assertIn('run.pending_failure(', body)

    def test_toy_ledger_cannot_collect_terminal_before_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve(); script = base / 'toy.py'; script.write_text('# never executed\n')
            parent = base / 'parent.json'; parent.write_bytes(C.S.encoded(dict(carry=C.CARRY, pins=[],
                protected_files=[], protected_roots=[], closed_journals=[])))
            root = base / 'new'; root.mkdir(); py = str(Path(sys.executable).resolve())
            stages = C.descriptors(py, root, script)
            spec = dict(schema=C.S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=C.S.pin(C.S.__file__),
                primitives=C.S.pin(C.S._PATH), ledger_path=str(root / 'campaign-ledger.jsonl'), caps=C.CAPS,
                guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=list(stages), stages=stages,
                parent_manifest=C.S.pin(parent), pins=[C.S.pin(py), C.S.pin(script)])
            path = root / 'campaign-spec.json'; path.write_bytes(C.S.encoded(spec)); budget = C.S.Budget(path)
            budget.initialize(root_go=True)
            with budget.lease() as run:
                with self.assertRaises(ValueError): run.begin('terminal-native', argv=stages['terminal-native']['argv'], guard=spec['guard'])
            self.assertEqual(budget.inspect()['completed'], [])
            self.assertIsNone(budget.inspect()['pending'])
            self.assertEqual(budget.inspect()['cumulative'], C.CARRY)


if __name__ == '__main__': unittest.main()
