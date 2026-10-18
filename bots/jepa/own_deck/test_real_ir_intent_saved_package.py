"""Synthetic temporary bytes only; no real campaigns, arrays or scientific calls."""
import ast
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import real_ir_intent_saved_package as H

ZERO = dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0,
            numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)


def write(path, value): path.write_bytes(H.P.encode(value))


def campaign(root, carry, source, reservation, failure=False):
    root.mkdir(); role = H.NAMES.index(root.name); original = root.parent / H.NAMES[1]
    parent = dict(carry=carry, pins=[])
    if role == 2:
        parent['pins'] = [H.pin(original / n) for n in ('campaign-spec.json', 'campaign-ledger.jsonl', 'experiment-closure.json')]
    write(root / 'parent-manifest.json', parent)
    names = ['diagnose'] if role == 0 else list(H.STAGES) if role == 1 else ['verify']
    stages = {n: dict(argv=['/fixed-python', n], outputs=[str(root / (n + '-1')), str(root / (n + '-1-stage-receipt.json'))],
        reservation=dict(seconds=20. if role == 2 else 10. if n == 'verify' else 1.,
            **dict(ZERO, native_applies=2 if n.endswith('native') else 0)),
        expected=dict(ZERO, **({'native_applies': None} if n.endswith('native') else {})),
        external_counters=['native_applies'] if n.endswith('native') else []) for n in names}
    spec = dict(schema='jepa-sealed-budget-spec/1', source_freeze_commit='abc'[role] * 40,
        ledger_path=str(root / 'campaign-ledger.jsonl'), parent_manifest=H.pin(root / 'parent-manifest.json'),
        stage_order=names, stages=stages, guard={},
        caps=dict(seconds=20. if role == 2 else 17. if role == 1 else 1., **dict(ZERO, native_applies=4 if role == 1 else 0)),
        pins=[H.pin(source)])
    if role == 1:
        rp = H.pin(reservation); spec['prelabel_reservation'] = rp; metadata = root / 'metadata-1'; metadata.mkdir()
        for panel in ('development', 'terminal'):
            write(metadata / (panel + '-plan.json'), dict(panel_role=panel,
                selected_whole_cards=['SOR_132', 'TOY_HELPER'] if panel == 'terminal' else ['TOY_HELPER'],
                terminal_outcomes_after_all_checkpoints=panel == 'terminal', programs=[dict(code='SOR_132')] if panel == 'terminal' else []))
        write(metadata / 'preregistration.json', dict(schema='jepa-real-ir-intent-reservation-amendment/1',
            status='terminal-release-preregistered', original_reservation=rp,
            old_reservation_sha256=H.P.digest(H.P.canonical(json.loads(reservation.read_text()))), released_terminal_source='SOR_132',
            remaining_reserved_codes=H.REMAINING, remaining_conservative_groups=[['ASH_259', 'LOF_259'], ['HMW_158']],
            native_outcome_order=['development', 'all-fitted-checkpoints-sealed', 'terminal']))
        spec['native_plans'] = {panel: H.pin(metadata / (panel + '-plan.json')) for panel in ('development', 'terminal')}
        spec['reservation_amendment'] = H.pin(metadata / 'preregistration.json')
        spec['pins'] += list(spec['native_plans'].values()) + [spec['reservation_amendment']]
    if role == 2:
        spec.update(original_root=str(original), failed_closure=H.pin(original / 'experiment-closure.json'),
            original_source_freeze_commit=json.loads((original / 'campaign-spec.json').read_text())['source_freeze_commit'])
    write(root / 'campaign-spec.json', spec); rows=[]
    def add(event, data):
        body=dict(schema='jepa-sealed-budget-journal/1', sequence=len(rows),
            previous_sha256=rows[-1]['record_sha256'] if rows else '0'*64,event=event,data=data)
        rows.append(dict(body,record_sha256=H.P.digest(H.P.canonical(body))))
    add('initialized',dict(spec=H.pin(root/'campaign-spec.json')))
    charged=dict(seconds=0.,**ZERO);observed=dict(ZERO)
    for n in names:
        add('begin',dict(stage=n,argv=stages[n]['argv'],guard={}))
        out=root/(n+'-1');out.mkdir();write(out/'result.json',dict(synthetic=True));proofs=[]
        if n=='build':
            binary=root/H.BINARY;binary.write_bytes(b'opaque binary never executed');proofs.append(H.pin(binary))
        bad=role==1 and n=='verify';elapsed=10. if bad else .125
        if bad:
            receipt=root/'verify-1-stage-receipt.json'
            write(receipt,dict(stage='verify',status='failed',cleanup_verified=True,error=dict(type='KeyError',message="'schema'")))
            proofs.append(H.pin(receipt))
        if role==2:
            write(out/'verification-result.json',dict(verified=True,mismatches=0,semantic_validated=False,
                lineage=dict(original_failure_preserved=True,scientific_arithmetic_unchanged=True),
                calls={k:0 for k in ZERO if k!='paid_spend_usd'}))
            proofs.append(H.pin(out/'verification-result.json'))
        amount=dict(seconds=elapsed,**ZERO)
        add('finish',dict(status='failed' if bad else 'completed',cleanup_verified=True,execution_ended=True,
            seconds=elapsed,charged=amount,durable_intents=ZERO,durable_completed=ZERO,proofs=proofs))
        for k,v in amount.items():charged[k]+=v
    (root/'campaign-ledger.jsonl').write_bytes(b''.join(H.P.canonical(row)+b'\n' for row in rows))
    cumulative=dict(charged_native_applies=carry['charged_native_applies']+charged['native_applies'],
        charged_seconds=carry['charged_seconds']+charged['seconds'],observed_native_applies=None)
    closure=dict(status=('closed-saved-diagnostic','closed-failed-saved-verification','closed-verified-saved-intent')[role],
        source_freeze_commit=spec['source_freeze_commit'],journal=H.pin(root/'campaign-ledger.jsonl'),
        final_chain=rows[-1]['record_sha256'],new_charged=charged,new_observed=observed,cumulative=cumulative,production_changed=False)
    if role==1:
        closure.update(schema='jepa-real-ir-intent-failed-closure/1',completed_stages=list(H.STAGES[:-1]),failed_stage='verify',
            failed_stage_receipt=H.pin(root/'verify-1-stage-receipt.json'),decisions_independently_verified=False,
            original_ledger_reopened=False,failed_charge_credited=False)
    if role==2:
        closure.update(schema='jepa-real-ir-intent-saved-closure/1',original_failed_closure=spec['failed_closure'],
            original_source_freeze_commit=spec['original_source_freeze_commit'],verification=H.pin(root/'verify-1/verification-result.json'),
            original_ledger_reopened=False,failed_charge_credited=False)
    write(root/'experiment-closure.json',closure)
    return cumulative


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name).resolve()
        self.exp = self.base / 'experiments'; self.exp.mkdir(); self.own = self.base / 'own'; self.own.mkdir()
        for name in ('real_ir_intent_diagnostic.py', 'real_ir_intent_model.py',
                     'real_ir_intent_package.py', 'test_real_ir_intent_package.py', 'real_ir_intent_saved_package.py',
                     'test_real_ir_intent_saved_package.py', 'real_ir_intent_verify_v2.py', 'compositional_typed_package.py'):
            (self.own / name).write_bytes(b'# synthetic source bytes only\n')
        self.report = self.own / 'REAL_IR_INTENT_RESULTS.md'; self.report.write_bytes(b'# synthetic closed result\n')
        depdir = self.own / 'real-ir-hp-projection-evidence'; depdir.mkdir(); self.dependency = depdir / 'manifest.json'
        self.dependency.write_bytes(b'{"opaque": "prior dependency"}\n')
        self.reservation = self.exp / 'real-ir-hp-fresh-reservation.json'
        write(self.reservation, dict(status='reserved-no-new-outcomes', reserved_codes=H.RESERVED))
        carry = dict(charged_native_applies=1031, charged_seconds=312., observed_native_applies=None)
        self.carry = campaign(self.exp / H.NAMES[0], carry, self.own / 'real_ir_intent_diagnostic.py', self.reservation)
        second_carry = campaign(self.exp / H.NAMES[1], self.carry, self.own / 'real_ir_intent_model.py', self.reservation)
        campaign(self.exp / H.NAMES[2], second_carry, self.own / 'real_ir_intent_verify_v2.py', self.reservation)
        for name, value in (('HERE', self.own), ('PRIOR_SHA', H.pin(self.dependency)['sha256']),
            ('RESERVATION_SHA', H.pin(self.reservation)['sha256']),
            ('ORIGINAL_HELPER_SHA', H.pin(self.own / 'real_ir_intent_package.py')['sha256']),
            ('ORIGINAL_TEST_SHA', H.pin(self.own / 'test_real_ir_intent_package.py')['sha256']),
            ('DIAGNOSTIC_SHA', H.pin(self.exp / H.NAMES[0] / 'experiment-closure.json')['sha256'])):
            context = patch.object(H, name, value); context.start(); self.addCleanup(context.stop)
        self.out = self.base / 'packet'

    def args(self): return dict(experiments=self.exp, out=self.out, report=self.report)

    def test_prepare_is_readonly_and_only_declared_sources_are_copied(self):
        plan = H.prepare(**self.args()); self.assertFalse(self.out.exists())
        self.assertEqual([h['disposition'] for h in plan['histories'].values()], ['completed', 'failed', 'completed'])
        self.assertEqual(len(plan['excluded']), 1); self.assertEqual(plan['excluded'][0]['relative_path'], H.BINARY)
        self.assertEqual(len(plan['frozen_source_pins']), 3)
        self.assertFalse(any('real-ir-hp-projection-evidence/' in e['url'] for e in plan['files']))

    def test_exact_opaque_npz_offline_and_deterministic_gzip(self):
        p = self.exp / H.NAMES[1] / 'fit-1' / 'opaque.npz'; blob = b'not-a-numerical-archive\x00\x01'; p.write_bytes(blob)
        first = H.build(**self.args()); other = self.base / 'second'
        second = H.build(self.exp, other, self.report); self.assertEqual(first['manifest_sha256'], second['manifest_sha256'])
        self.assertEqual((self.out / 'payload/campaigns' / H.NAMES[1] / 'fit-1/opaque.npz').read_bytes(), blob)
        for path in self.out.rglob('*.gz'): self.assertEqual(path.read_bytes()[4:8], b'\0\0\0\0')
        shutil.rmtree(self.exp); shutil.rmtree(self.own)
        self.assertEqual(H.verify(self.out, first['manifest_sha256']), first)
        stored=json.loads((self.out/'manifest.json').read_text())
        self.assertEqual(tuple(stored['histories']), tuple(sorted(H.NAMES)))
        self.assertNotEqual(tuple(stored['histories']), H.NAMES)
        self.assertEqual(stored['root_order'], list(H.NAMES))

    def test_failed_original_charge_cannot_be_laundered(self):
        plan=H.prepare(**self.args());h=plan['histories'][H.NAMES[1]]
        self.assertEqual(h['statuses'],['completed']*7+['failed'])
        self.assertEqual(h['charged']['seconds'],10.875)
        self.assertEqual(plan['recovery']['preserved_failed_charge_seconds'],10.)
        self.assertIsNone(h['cumulative']['observed_native_applies'])
        path=self.exp/H.NAMES[1]/'experiment-closure.json';value=json.loads(path.read_text())
        value['failed_charge_credited']=True;write(path,value)
        with self.assertRaisesRegex(ValueError,'original must retain'):H.prepare(**self.args())

    def test_sidecar_pending_or_unverified_cannot_become_success(self):
        path=self.exp/H.NAMES[2]/'campaign-ledger.jsonl';old=path.read_bytes()
        path.write_bytes(b'\n'.join(old.splitlines()[:-1])+b'\n')
        with self.assertRaisesRegex(ValueError,'closed ended'):H.prepare(**self.args())
        path.write_bytes(old);path=self.exp/H.NAMES[2]/'verify-1/verification-result.json'
        value=json.loads(path.read_text());value['verified']=False;write(path,value)
        with self.assertRaisesRegex(ValueError,'closure pin differs'):H.prepare(**self.args())

    def test_original_packaging_bytes_are_preserved(self):
        path=self.own/'real_ir_intent_package.py';path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'original package helper'):H.prepare(**self.args())

    def test_terminal_release_and_order_cannot_silently_expand(self):
        root = self.exp / H.NAMES[1]; plan = H.prepare(**self.args())
        self.assertEqual(plan['release']['released_terminal_source'], 'SOR_132')
        self.assertEqual(plan['release']['remaining_reserved_codes'], H.REMAINING)
        path = root / 'metadata-1/preregistration.json'; original = path.read_bytes(); amendment = json.loads(original)
        amendment['released_terminal_source'] = 'ASH_259'; write(path, amendment)
        with self.assertRaisesRegex(ValueError, 'frozen before'): H.prepare(**self.args())
        path.write_bytes(original); path = root / 'campaign-spec.json'; spec = json.loads(path.read_text())
        order = spec['stage_order']; order[3], order[4] = order[4], order[3]; write(path, spec)
        with self.assertRaisesRegex(ValueError, 'fixed stage'): H.prepare(**self.args())

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
        source = self.own / 'real_ir_intent_model.py'; old = source.read_bytes(); source.write_bytes(b'changed')
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

    def test_recovery_proof_rejects_carry_reset_and_missing_original_parent(self):
        histories={};specs=[]
        for name in H.NAMES:
            h,spec,_=H.history(self.exp/name);histories[name]=h;specs.append(spec)
        before=copy.deepcopy(histories)
        histories[H.NAMES[2]]['carry']['charged_seconds']-=10.
        with self.assertRaisesRegex(ValueError,'linked parent charge reset'):
            H.recovery_proof(self.exp,histories,specs)
        path=self.exp/H.NAMES[2]/'parent-manifest.json';parent=json.loads(path.read_text());parent['pins']=[];write(path,parent)
        with self.assertRaisesRegex(ValueError,'parent must preserve'):
            H.recovery_proof(self.exp,before,specs)

    def test_source_has_no_scientific_or_process_execution_surface(self):
        tree = ast.parse(Path(H.__file__).read_text())
        names = {a.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
        self.assertFalse(names & {'numpy', 'torch', 'subprocess', 'real_ir_intent_fit', 'sealed_budget'})
        self.assertEqual(H.LIMITS, dict(file_bytes=64 * 1024**2, total_raw_bytes=256 * 1024**2,
            total_stored_bytes=256 * 1024**2, files=1000, manifest_bytes=4 * 1024**2))


if __name__ == '__main__': unittest.main()
