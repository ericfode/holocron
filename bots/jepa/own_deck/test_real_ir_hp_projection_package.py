"""Synthetic temporary bytes only; no real campaigns, arrays or scientific calls."""
import ast
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import real_ir_hp_projection_package as H

ZERO = dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0,
            numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)


def write(path, value): path.write_bytes(H.P.encode(value))


def campaign(root, carry, source, reservation, failure=False):
    root.mkdir(); write(root / 'parent-manifest.json', dict(carry=carry))
    names = ['diagnose'] if root.name == H.NAMES[0] else ['build', 'native', 'prep', 'fit', 'verify']
    stages = {n: dict(argv=['/fixed-python', n], outputs=[str(root / (n + '-1')), str(root / (n + '-1-stage-receipt.json'))],
        reservation=dict(seconds=1., **dict(ZERO, native_applies=2 if n == 'native' else 0)),
        expected=dict(ZERO, **({'native_applies': None} if n == 'native' else {})),
        external_counters=['native_applies'] if n == 'native' else []) for n in names}
    spec = dict(schema='jepa-sealed-budget-spec/1', source_freeze_commit=('a' if root.name == H.NAMES[0] else 'b') * 40,
        ledger_path=str(root / 'campaign-ledger.jsonl'), parent_manifest=H.pin(root / 'parent-manifest.json'),
        stage_order=names, stages=stages, guard={}, caps=dict(seconds=float(len(names)), **dict(ZERO, native_applies=2 if 'native' in names else 0)),
        pins=[H.pin(source)])
    if root.name == H.NAMES[1]: spec['prelabel_reservation'] = H.pin(reservation)
    write(root / 'campaign-spec.json', spec); rows = []
    def add(event, data):
        body = dict(schema='jepa-sealed-budget-journal/1', sequence=len(rows), previous_sha256=rows[-1]['record_sha256'] if rows else '0' * 64,
                    event=event, data=data)
        rows.append(dict(body, record_sha256=H.P.digest(H.P.canonical(body))))
    add('initialized', dict(spec=H.pin(root / 'campaign-spec.json')))
    charged = dict(seconds=0., **ZERO); observed = dict(ZERO)
    for n in names:
        add('begin', dict(stage=n, argv=stages[n]['argv'], guard={}))
        out = root / (n + '-1'); out.mkdir(); write(out / 'result.json', dict(synthetic=True))
        proofs = []
        if n == 'build':
            binary = root / H.BINARY; binary.write_bytes(b'synthetic opaque binary, never executed'); proofs.append(H.pin(binary))
        bad = failure and n == 'native'; elapsed = 1. if bad else .125
        count = dict(ZERO, native_applies=2 if bad else 0)
        amount = dict(seconds=elapsed, **count)
        add('finish', dict(status='failed' if bad else 'completed', cleanup_verified=True, execution_ended=True, seconds=elapsed,
            charged=amount, durable_intents=ZERO, durable_completed=ZERO, proofs=proofs))
        for k, value in amount.items(): charged[k] += value
        if bad: observed['native_applies'] = None; break
    (root / 'campaign-ledger.jsonl').write_bytes(b''.join(H.P.canonical(row) + b'\n' for row in rows))
    cumulative = dict(charged_native_applies=carry['charged_native_applies'] + charged['native_applies'],
                      charged_seconds=carry['charged_seconds'] + charged['seconds'], observed_native_applies=None)
    status = 'closed-failed-hp-projection' if failure else 'closed-saved-diagnostic' if root.name == H.NAMES[0] else 'closed-verified-hp-projection'
    write(root / 'experiment-closure.json', dict(status=status, source_freeze_commit=spec['source_freeze_commit'],
        journal=H.pin(root / 'campaign-ledger.jsonl'), final_chain=rows[-1]['record_sha256'], new_charged=charged,
        new_observed=observed, cumulative=cumulative, production_changed=False))
    return cumulative


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name).resolve()
        self.exp = self.base / 'experiments'; self.exp.mkdir(); self.own = self.base / 'own'; self.own.mkdir()
        for name in ('real_ir_failure_diagnostic.py', 'real_ir_hp_projection_model.py',
                     'real_ir_hp_projection_package.py', 'test_real_ir_hp_projection_package.py', 'compositional_typed_package.py'):
            (self.own / name).write_bytes(b'# synthetic source bytes only\n')
        self.report = self.own / 'REAL_IR_HP_PROJECTION_RESULTS.md'; self.report.write_bytes(b'# synthetic closed result\n')
        depdir = self.own / 'real-ir-transfer-evidence'; depdir.mkdir(); self.dependency = depdir / 'manifest.json'
        self.dependency.write_bytes(b'{"opaque": "prior dependency"}\n')
        self.reservation = self.exp / 'real-ir-hp-fresh-reservation.json'
        write(self.reservation, dict(status='reserved-no-new-outcomes', reserved_codes=H.RESERVED))
        carry = dict(charged_native_applies=919, charged_seconds=296., observed_native_applies=None)
        self.carry = campaign(self.exp / H.NAMES[0], carry, self.own / 'real_ir_failure_diagnostic.py', self.reservation)
        campaign(self.exp / H.NAMES[1], self.carry, self.own / 'real_ir_hp_projection_model.py', self.reservation)
        for name, value in (('HERE', self.own), ('PRIOR_SHA', H.pin(self.dependency)['sha256']),
            ('RESERVATION_SHA', H.pin(self.reservation)['sha256']),
            ('DIAGNOSTIC_SHA', H.pin(self.exp / H.NAMES[0] / 'experiment-closure.json')['sha256'])):
            context = patch.object(H, name, value); context.start(); self.addCleanup(context.stop)
        self.out = self.base / 'packet'

    def args(self): return dict(experiments=self.exp, out=self.out, report=self.report)

    def test_prepare_is_readonly_and_only_declared_sources_are_copied(self):
        plan = H.prepare(**self.args()); self.assertFalse(self.out.exists())
        self.assertEqual([h['disposition'] for h in plan['histories'].values()], ['completed', 'completed'])
        self.assertEqual(len(plan['excluded']), 1); self.assertEqual(plan['excluded'][0]['relative_path'], H.BINARY)
        self.assertEqual(len(plan['frozen_source_pins']), 2)
        self.assertFalse(any('real-ir-transfer-evidence/' in e['url'] for e in plan['files']))

    def test_exact_opaque_npz_offline_and_deterministic_gzip(self):
        p = self.exp / H.NAMES[1] / 'fit-1' / 'opaque.npz'; blob = b'not-a-numerical-archive\x00\x01'; p.write_bytes(blob)
        first = H.build(**self.args()); other = self.base / 'second'
        second = H.build(self.exp, other, self.report); self.assertEqual(first['manifest_sha256'], second['manifest_sha256'])
        self.assertEqual((self.out / 'payload/campaigns' / H.NAMES[1] / 'fit-1/opaque.npz').read_bytes(), blob)
        for path in self.out.rglob('*.gz'): self.assertEqual(path.read_bytes()[4:8], b'\0\0\0\0')
        shutil.rmtree(self.exp); shutil.rmtree(self.own)
        self.assertEqual(H.verify(self.out, first['manifest_sha256']), first)

    def test_failed_followup_preserves_full_charge_and_unknown_observations(self):
        root = self.exp / H.NAMES[1]; shutil.rmtree(root)
        campaign(root, self.carry, self.own / 'real_ir_hp_projection_model.py', self.reservation, failure=True)
        plan = H.prepare(**self.args()); h = plan['histories'][H.NAMES[1]]
        self.assertEqual(h['disposition'], 'failed'); self.assertEqual(h['statuses'], ['completed', 'failed'])
        self.assertEqual(h['charged']['native_applies'], 2); self.assertEqual(h['charged']['seconds'], 1.125)
        self.assertIsNone(h['observed']['native_applies']); self.assertIsNone(h['cumulative']['observed_native_applies'])
        self.assertEqual(H.build(**self.args())['dispositions'][H.NAMES[1]], 'failed')

    def test_pending_or_forged_closure_rejects(self):
        p = self.exp / H.NAMES[1] / 'campaign-ledger.jsonl'; old = p.read_bytes(); p.write_bytes(b'\n'.join(old.splitlines()[:-1]) + b'\n')
        with self.assertRaisesRegex(ValueError, 'closed ended'): H.prepare(**self.args())
        p.write_bytes(old); p = self.exp / H.NAMES[1] / 'experiment-closure.json'; value = json.loads(p.read_text()); value['new_charged']['seconds'] = 0; write(p, value)
        with self.assertRaisesRegex(ValueError, 'closure'): H.prepare(**self.args())

    def test_undeclared_files_symlinks_and_existing_destination_reject(self):
        root = self.exp / H.NAMES[1]; extra = root / 'unrelated.json'; extra.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'unreviewed campaign path'): H.prepare(**self.args())
        extra.unlink(); extra.symlink_to(self.reservation)
        with self.assertRaisesRegex(ValueError, 'symlink'): H.prepare(**self.args())
        extra.unlink(); H.build(**self.args()); before = (self.out / 'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'exclusive'): H.build(**self.args())
        self.assertEqual((self.out / 'manifest.json').read_bytes(), before)

    def test_prior_packet_cannot_be_an_output_parent(self):
        before = self.dependency.read_bytes()
        with self.assertRaisesRegex(ValueError, 'prior packet'):
            H.prepare(self.exp, self.dependency.parent / 'new-child', self.report)
        self.assertEqual(self.dependency.read_bytes(), before)
        self.assertFalse((self.dependency.parent / 'new-child').exists())

    def test_source_and_prior_dependency_pin_drift_reject(self):
        source = self.own / 'real_ir_hp_projection_model.py'; old = source.read_bytes(); source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'frozen source'): H.prepare(**self.args())
        source.write_bytes(old); self.dependency.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'opaque prior'): H.prepare(**self.args())

    def test_packet_tampering_limits_and_membership_reject(self):
        result = H.build(**self.args()); mp = self.out / 'manifest.json'; original = mp.read_bytes(); value = json.loads(original)
        value['files'][0]['url'] = '../escape'; write(mp, value)
        with self.assertRaisesRegex(ValueError, 'path traversal'): H.verify(self.out)
        value = json.loads(original); value['files'][0]['raw_bytes'] = H.P.MAX_FILE + 1; write(mp, value)
        with self.assertRaisesRegex(ValueError, '64MiB'): H.verify(self.out)
        mp.write_bytes(original); entry = value['files'][1]; path = self.out / entry['url']; data = path.read_bytes(); path.write_bytes(data[:-1])
        with self.assertRaises(ValueError): H.verify(self.out, result['manifest_sha256'])
        path.write_bytes(data); (self.out / 'extra.txt').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'membership'): H.verify(self.out)

    def test_source_has_no_scientific_or_process_execution_surface(self):
        tree = ast.parse(Path(H.__file__).read_text())
        names = {a.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
        self.assertFalse(names & {'numpy', 'torch', 'subprocess', 'real_ir_hp_projection_fit', 'sealed_budget'})
        self.assertEqual(H.LIMITS, dict(file_bytes=64 * 1024**2, total_raw_bytes=256 * 1024**2,
            total_stored_bytes=256 * 1024**2, files=1000, manifest_bytes=4 * 1024**2))


if __name__ == '__main__': unittest.main()
