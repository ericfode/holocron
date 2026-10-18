"""Source transforms and temporary byte/provenance examples only; no science."""
import ast
import copy
import inspect
import json
from pathlib import Path
import tempfile
import unittest

import compositional_typed_saved_verify as S
import compositional_typed_verify as V


def normal(source):
    return ast.dump(ast.parse(source), include_attributes=False)


class Tests(unittest.TestCase):
    def test_original_independent_verifier_and_scientific_helpers_are_unchanged(self):
        self.assertEqual(V.pin(V.__file__)['sha256'], S.ORIGINAL_VERIFIER_SHA256)
        for name in ('parse_program', 'parity', 'public_features', 'reference', 'native_case',
                     'native_journal', 'score', 'evaluations', 'gate', 'comparative',
                     'loss_statistics', 'bank_audit', 'progress_audit', 'consumed_conflicts'):
            if hasattr(S, name): self.assertIs(getattr(S, name), getattr(V, name))

    def test_verify_exact_transform_changes_only_missing_fixture_and_new_budget_provenance(self):
        old = inspect.getsource(V.verify)
        old = old.replace("        require(len(raw['fixtureValidation']) == 128, 'every fixture must be validated before the first apply')",
                          '        recovery = recovery_audit(root, raw, plan_path, trace_path, spec)')
        block = """            fixture = raw['fixtureValidation'][i]
            require(fixture['world_id'] == i and fixture['card'] == case['card'] and
                    fixture['publicSnapshotRoundtripExact'] is True and fixture['legalActionsRoundtripExact'] is True and
                    fixture['allProgramsAdmitted'] is True and fixture['applyCalls'] == fixture['actionsApplied'] == 0 and
                    fixture['before'] == case['before'], 'pre-apply admission/fixture roundtrip witness differs')
"""
        self.assertEqual(old.count(block), 1); old = old.replace(block, '')
        old = old.replace("        require(budget['native_applies'] == native['native_applies'], 'official native count disagrees with physical trace')",
            "        require(budget['native_applies'] == 0 and native['native_applies'] == recovery['source_observed_native_applies'] == 256,\n"
            "                'recovery must not charge new calls or invent/credit original native calls')")
        old = old.replace("        report.update(status='passed', native=native, reference=",
            "        report.update(status='passed', native=native, recovery=recovery, original_verifier=pin(V.__file__), reference=")
        self.assertEqual(normal(old), normal(inspect.getsource(S.verify)))

    def test_budget_exact_transform_keeps_every_forward_update_and_fit_check(self):
        old = inspect.getsource(V.budget_audit)
        old = old.replace("list(stages) == ['metadata', 'build', 'native', 'prep', 'fit']", "list(stages) == ['recover', 'prep', 'fit']")
        old = old.replace("native_applies=stages['native']['durable_completed']['native_applies']",
                          "native_applies=sum(stage['durable_completed']['native_applies'] for stage in stages.values())")
        self.assertEqual(normal(old), normal(inspect.getsource(S.budget_audit)))

    def test_adapter_imports_no_scientific_module_and_has_no_execution_api(self):
        tree = ast.parse(Path(S.__file__).read_text())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imports, {'copy', 'json', 'math', 'compositional_typed_verify'})
        forbidden = ('make_model', 'forward', 'backward', 'apply', 'step', 'prepare_data', 'Popen')
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                             n.func.attr in forbidden for n in ast.walk(tree)))

    def test_failed_source_hash_chain_rejects_mutation(self):
        previous = '0' * 64; rows = []
        for sequence, event in enumerate(('initialized', 'begin', 'finish')):
            row = dict(schema='jepa-sealed-budget-journal/1', sequence=sequence,
                       previous_sha256=previous, event=event, data=dict(status='failed', charged=512))
            row['record_sha256'] = V.digest(row); previous = row['record_sha256']; rows.append(row)
        self.assertEqual(S.checked_chain(rows), previous)
        rows[-1]['data']['charged'] = 256
        with self.assertRaisesRegex(ValueError, 'chain changed'): S.checked_chain(rows)

    def test_synthetic_recovery_preserves_failed_charge_and_qualified_validation_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); old = root / 'old'; new = root / 'new'; old.mkdir(); new.mkdir()
            def write(path, value):
                path.write_text(json.dumps(value)); return V.pin(path)
            source = Path(S.__file__).with_name('compositional_typed_native_collector') / 'src/main.rs'
            source_pin = V.pin(source)
            binary = old / 'built'; binary.write_bytes(b'not-executed-toy-binary'); binary_pin = V.pin(binary)
            plan = old / 'plan.json'; plan.write_bytes(b'{}\n'); plan_pin = V.pin(plan)
            trace = old / 'trace.jsonl'; trace.write_bytes(b'temporary provenance bytes only\n'); trace_pin = V.pin(trace)
            (new / 'plan.json').write_bytes(plan.read_bytes()); (new / 'trace.jsonl').write_bytes(trace.read_bytes())
            old_parent_pin = write(old / 'parent.json', dict(carry=dict(charged_native_applies=295,
                charged_seconds=222.92651104100514, observed_native_applies=None)))
            old_spec_pin = write(old / 'spec.json', dict(parent_manifest=old_parent_pin, pins=[source_pin]))
            failed_receipt_pin = write(old / 'stage-receipt.json', dict(stage='native', status='failed',
                cleanup_verified=True, child_argv=[str(binary), str(plan), str(old / 'truncated.json'), str(trace)]))
            events = [('initialized', dict(spec=old_spec_pin))]
            for stage, seconds, status in (('metadata', .1, 'completed'), ('build', 1., 'completed'), ('native', 30.2, 'failed')):
                events.extend([('begin', dict(stage=stage)), ('finish', dict(status=status,
                    charged=dict(native_applies=512 if stage == 'native' else 0, seconds=seconds),
                    durable_intents=dict(native_applies=512 if stage == 'native' else 0),
                    durable_completed=dict(native_applies=0), cleanup_verified=True, execution_ended=True,
                    proofs=[binary_pin] if stage == 'build' else [trace_pin, failed_receipt_pin] if stage == 'native' else []))])
            previous = '0' * 64; ledger = []
            for i, (event, data) in enumerate(events):
                row = dict(schema='jepa-sealed-budget-journal/1', sequence=i,
                           previous_sha256=previous, event=event, data=data)
                row['record_sha256'] = V.digest(row); previous = row['record_sha256']; ledger.append(row)
            ledger_path = old / 'ledger.jsonl'; ledger_path.write_text('\n'.join(json.dumps(r) for r in ledger))
            provenance = dict(source_journal=trace_pin, source_plan=plan_pin, failed_ledger=V.pin(ledger_path),
                failed_stage_receipt=failed_receipt_pin, built_binary=binary_pin, collector_source=source_pin,
                source_campaign_spec=old_spec_pin, fixture_validation_scope=S.FIXTURE_SCOPE,
                per_fixture_validation_records_persisted=False, source_observed_native_applies=256,
                source_charged_native_applies=512, new_native_applies=0, no_credit=True)
            pins = [v for v in provenance.values() if isinstance(v, dict)]
            parent_pin = write(new / 'parent.json', dict(pins=pins, carry=dict(charged_native_applies=807,
                charged_seconds=222.92651104100514 + .1 + 1. + 30.2, observed_native_applies=None)))
            spec = dict(parent_manifest=parent_pin, pins=pins); raw = dict(recovery_provenance=provenance)
            output = S.recovery_audit(new, raw, new / 'plan.json', new / 'trace.jsonl', spec)
            self.assertEqual(output['source_observed_native_applies'], 256)
            self.assertEqual(output['source_charged_native_applies'], 512)
            self.assertEqual(output['new_native_applies'], 0)
            self.assertFalse(output['per_fixture_validation_records_persisted'])
            bad = copy.deepcopy(raw); bad['fixtureValidation'] = []
            with self.assertRaisesRegex(ValueError, 'fabricate'): S.recovery_audit(new, bad, new / 'plan.json', new / 'trace.jsonl', spec)
            bad = copy.deepcopy(raw); bad['recovery_provenance']['source_charged_native_applies'] = 256
            with self.assertRaisesRegex(ValueError, 'charge distinction'): S.recovery_audit(new, bad, new / 'plan.json', new / 'trace.jsonl', spec)
            (new / 'trace.jsonl').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'byte exact'): S.recovery_audit(new, raw, new / 'plan.json', new / 'trace.jsonl', spec)


if __name__ == '__main__': unittest.main()
