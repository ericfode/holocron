"""Temporary opaque bytes/accounting fixtures; no scientific inputs or calls."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import real_ir_transfer_package as R


ZERO=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)


def write(path,value):path.write_bytes(R.P.encode(value))


def campaign(root,mode,carry):
    root.mkdir();parent=root/'parent-manifest.json';write(parent,dict(carry=carry))
    stages=['build','native','prep','fit','verify']if root.name==R.NAMES[3]else['coverage','verify']
    stage={n:dict(argv=['/fixed-python',n],guard={},outputs=[str(root/(n+'-1')),str(root/(n+'-1-stage-receipt.json'))],
        reservation=dict(seconds=10.,**ZERO),expected=ZERO,external_counters=[])for n in stages}
    spec=dict(schema='jepa-sealed-budget-spec/1',source_freeze_commit=R.COMMITS[root.name],
        ledger_path=str(root/'campaign-ledger.jsonl'),parent_manifest=R.pin(parent),stage_order=stages,
        stages=stage,guard={},caps=dict(seconds=10.*len(stages),**ZERO),pins=[])
    write(root/'campaign-spec.json',spec)
    if mode=='unstarted':
        write(root/'prelaunch-closure.json',dict(status='unstarted-preflight-rejected',ledger_initialized=False,
            root_go=False,charged_seconds=0,engine_calls=0,neural_calls=0,paid_spend_usd=0,
            spec=R.pin(root/'campaign-spec.json'),source_commit=R.COMMITS[root.name][:7]));return carry
    journal=[]
    def add(event,data):
        body=dict(schema='jepa-sealed-budget-journal/1',sequence=len(journal),previous_sha256=journal[-1]['record_sha256']if journal else'0'*64,event=event,data=data)
        journal.append(dict(body,record_sha256=R.P.digest(R.P.canonical(body))))
    add('initialized',dict(spec=R.pin(root/'campaign-spec.json')))
    charged=dict(seconds=0.,**ZERO);statuses=[]
    for n in(stages[:1]if mode=='failed'else stages):
        add('begin',dict(stage=n,argv=stage[n]['argv'],guard={}))
        elapsed=10. if mode=='failed'else.125
        amount=dict(seconds=elapsed,**ZERO)
        add('finish',dict(status='failed'if mode=='failed'else'completed',cleanup_verified=True,execution_ended=True,
            seconds=elapsed,charged=amount,durable_intents=ZERO,durable_completed=ZERO,proofs=[]))
        charged['seconds']+=elapsed;statuses.append(n)
    (root/'campaign-ledger.jsonl').write_bytes(b''.join(R.P.canonical(row)+b'\n'for row in journal))
    cumulative=dict(carry,charged_seconds=carry['charged_seconds']+charged['seconds'])
    status='closed-failed-before-outcomes'if mode=='failed'else'closed-verified-local-transfer'if root.name==R.NAMES[3]else'closed-verified-coverage-and-reservation'
    write(root/'experiment-closure.json',dict(status=status,source_freeze_commit=spec['source_freeze_commit'],
        journal=R.pin(root/'campaign-ledger.jsonl'),final_chain=journal[-1]['record_sha256'],new_charged=charged,new_observed=ZERO,
        cumulative=cumulative,production_changed=False,outcomes_collected=False))
    return cumulative


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        self.exp=self.base/'experiments';self.exp.mkdir();carry=dict(charged_native_applies=807,charged_seconds=100.,observed_native_applies=None)
        for name,mode in zip(R.NAMES,R.DISPOSITIONS):carry=campaign(self.exp/name,mode,carry)
        self.dep=self.base/'prior.json';self.dep.write_bytes(b'public prior manifest\n')
        self.patch=patch.object(R,'PRIOR_SHA',R.P.digest(self.dep.read_bytes()));self.patch.start();self.addCleanup(self.patch.stop)
        self.own=self.base/'own';self.own.mkdir();herepatch=patch.object(R,'HERE',self.own);herepatch.start();self.addCleanup(herepatch.stop)
        for name in('test_real_ir_transfer_package.py','compositional_typed_package.py'):(self.own/name).write_bytes(b'# synthetic source bytes\n')
        self.report=self.own/'REAL_IR_TRANSFER_RESULTS.md';self.report.write_bytes(b'# synthetic final report\n')
        self.lineage=self.exp/'real-ir-adapter-lineage-review.json';write(self.lineage,dict(status='synthetic-byte-fixture'))
        self.out=self.base/'packet'

    def args(self):return dict(experiments=self.exp,out=self.out,reports=[self.report],dependency=self.dep,lineage_review=self.lineage)

    def test_prepare_is_readonly_and_failed_unstarted_are_distinct(self):
        plan=R.prepare(**self.args());self.assertFalse(self.out.exists())
        self.assertFalse(plan['histories'][R.NAMES[0]]['ledger_initialized'])
        self.assertEqual(plan['histories'][R.NAMES[1]]['statuses'],['failed'])
        self.assertEqual(plan['histories'][R.NAMES[1]]['charged']['seconds'],10.)
        self.assertIsNone(plan['histories'][R.NAMES[3]]['cumulative']['observed_native_applies'])

    def test_exact_bytes_opaque_npz_and_offline_originals_absent(self):
        blob=b'opaque-not-numerically-loaded\x00\x01';stage=self.exp/R.NAMES[3]/'fit-1';stage.mkdir();(stage/'array.npz').write_bytes(blob)
        result=R.build(**self.args());self.assertEqual(result['scientific_calls'],0)
        self.assertEqual((self.out/'payload/campaigns'/R.NAMES[3]/'fit-1/array.npz').read_bytes(),blob)
        shutil.rmtree(self.exp);self.dep.unlink()
        self.assertEqual(R.verify(self.out,result['manifest_sha256']),result)

    def test_existing_output_and_old_dependency_preserved(self):
        before=self.dep.read_bytes();R.build(**self.args());manifest=(self.out/'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'exclusive'):R.build(**self.args())
        self.assertEqual((self.out/'manifest.json').read_bytes(),manifest);self.assertEqual(self.dep.read_bytes(),before)

    def test_unstarted_ledger_and_pending_completed_root_rejected(self):
        (self.exp/R.NAMES[0]/'campaign-ledger.jsonl').write_bytes(b'not allowed')
        with self.assertRaisesRegex(ValueError,'absent'):R.prepare(**self.args())
        (self.exp/R.NAMES[0]/'campaign-ledger.jsonl').unlink()
        path=self.exp/R.NAMES[3]/'campaign-ledger.jsonl';lines=path.read_bytes().splitlines();path.write_bytes(b'\n'.join(lines[:-1])+b'\n')
        with self.assertRaisesRegex(ValueError,'closed ended'):R.prepare(**self.args())

    def test_bad_closure_charge_and_commit_rejected(self):
        p=self.exp/R.NAMES[1]/'experiment-closure.json';v=json.loads(p.read_text());v['new_charged']['seconds']=0;write(p,v)
        with self.assertRaisesRegex(ValueError,'closure'):R.prepare(**self.args())

    def test_traversal_corrupt_payload_and_extra_file_reject(self):
        receipt=R.build(**self.args());(self.out/'extra.txt').write_text('unexpected')
        with self.assertRaisesRegex(ValueError,'membership'):R.verify(self.out,receipt['manifest_sha256'])
        (self.out/'extra.txt').unlink();mp=self.out/'manifest.json';m=json.loads(mp.read_text());m['files'][0]['url']='../escape';write(mp,m)
        with self.assertRaisesRegex(ValueError,'path traversal'):R.verify(self.out)

    def test_limits_and_truncated_gzip_are_checked_before_acceptance(self):
        R.build(**self.args());mp=self.out/'manifest.json';m=json.loads(mp.read_text());m['files'][0]['raw_bytes']=R.P.MAX_FILE+1;write(mp,m)
        with self.assertRaisesRegex(ValueError,'64MiB'):R.verify(self.out)

    def test_symlink_payload_fails_closed(self):
        (self.exp/R.NAMES[3]/'alias.json').symlink_to(self.dep)
        with self.assertRaisesRegex(ValueError,'symlink'):R.prepare(**self.args())

    def test_unrelated_json_or_directory_payload_is_not_silently_packaged(self):
        for relative in('unrelated.json','misc/unrelated.md'):
            path=self.exp/R.NAMES[3]/relative;path.parent.mkdir(exist_ok=True);path.write_bytes(b'not declared research output')
            with self.assertRaisesRegex(ValueError,'unreviewed campaign path'):R.prepare(**self.args())
            path.unlink()


if __name__=='__main__':unittest.main()
