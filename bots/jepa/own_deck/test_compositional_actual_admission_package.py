"""Synthetic byte fixtures only; never import scientific audit code."""
import ast
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compositional_actual_admission_package as K

P=K.P


class PackageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.root=self.base/'compositional-actual-admission-v1';self.root.mkdir();self.out=self.base/'packet'
        def put(path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return K.pin(path)
        self.put=put;inputs=self.base/'inputs';pins=[]
        for name in(*K.SOURCES,'cards.json','runtime-admission.json','native-plan.json','receipt.json'):
            pins.append(put(inputs/name,b'{"opaque":['if name=='receipt.json'else b'synthetic bytes; no interpretation'))
        pins.append(put(inputs/'compositional-typed-publication-complete.json',P.encode(dict(packet_manifest=dict(path='/opaque/old/manifest.json',sha256=K.OLD_PACKET,bytes=123)))))
        carry=dict(charged_native_applies=807,charged_seconds=266.,observed_native_applies=None)
        parent=put(self.root/'parent-manifest.json',P.encode(dict(carry=carry,pins=[dict(path='/opaque/never-fetch',sha256='f'*64,bytes=123)])))
        zero=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0)
        spec=dict(schema='jepa-sealed-budget-spec/1',source_freeze_commit=K.COMMIT,stage_order=['audit','verify'],ledger_path=str(self.root/'campaign-ledger.jsonl'),
            parent_manifest=parent,caps=dict(seconds=20.,**zero),guard=dict(cpu_workers=1),pins=pins,stages={})
        for stage in spec['stage_order']:spec['stages'][stage]=dict(argv=['/synthetic/never-execute',stage],reservation=dict(seconds=10.,**zero))
        sp=put(self.root/'campaign-spec.json',P.encode(spec));rows=[];proofs=[]
        def append(event,data):
            body=dict(schema='jepa-sealed-budget-journal/1',sequence=len(rows),previous_sha256=rows[-1]['record_sha256']if rows else'0'*64,event=event,data=data)
            rows.append(dict(body,record_sha256=P.digest(P.canonical(body))))
        append('initialized',dict(spec=sp))
        for stage in spec['stage_order']:
            append('begin',dict(stage=stage,argv=spec['stages'][stage]['argv'],guard=spec['guard'],inputs=[]))
            name='admission-report.json'if stage=='audit'else'verification-result.json'
            proof=put(self.root/(stage+'-1')/name,P.encode(dict(synthetic=True)))
            receipt=put(self.root/(stage+'-1-stage-receipt.json'),P.encode(dict(status='completed')));proofs.append(proof)
            append('finish',dict(status='completed',cleanup_verified=True,execution_ended=True,seconds=.01,charged=dict(seconds=.01,**zero),durable_intents=zero,durable_completed=zero,proofs=[proof,receipt]))
        jp=put(self.root/'campaign-ledger.jsonl',b''.join(P.canonical(row)+b'\n'for row in rows))
        put(self.root/'experiment-closure.json',P.encode(dict(journal=jp,final_chain=rows[-1]['record_sha256'],source_freeze_commit=K.COMMIT,
            new_charged=dict(seconds=.02,**zero),new_observed=zero,cumulative=dict(carry,charged_seconds=266.02),report=proofs[0],verification=proofs[1])))

    def test_byte_only_source_prepare_and_pin_mismatch(self):
        names=[a.name for n in ast.walk(ast.parse(Path(K.__file__).read_text()))if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(names)&{'numpy','torch','subprocess','sealed_budget','compositional_actual_admission'})
        K.prepare(self.root,self.out);self.assertFalse(self.out.exists())
        (self.base/'inputs/cards.json').write_bytes(b'changed')
        with self.assertRaises(ValueError):K.build(self.root,self.out)
        self.assertFalse(self.out.exists())

    def test_build_roundtrip_offline_and_exact_membership(self):
        result=K.build(self.root,self.out);self.assertEqual(result['scientific_calls'],0)
        manifest=json.loads((self.out/'manifest.json').read_text());entry=next(e for e in manifest['files']if e['url'].endswith('/prior/receipt.json.gz'))
        self.assertEqual(gzip.decompress((self.out/entry['url']).read_bytes()),b'{"opaque":[')
        self.root.rename(self.base/'root-gone');(self.base/'inputs').rename(self.base/'inputs-gone')
        K.verify(self.out,result['manifest_sha256'])
        with self.assertRaises(ValueError):K.verify(self.out,'0'*64)
        (self.out/'extra').write_bytes(b'x')
        with self.assertRaises(ValueError):K.verify(self.out)

    def test_metadata_allocation_checked_before_writes_and_no_overwrite(self):
        plan=K.prepare(self.root,self.out);limit=max(sum(e[k]for e in plan['files'])for k in('bytes','raw_bytes'))
        with patch.dict(K.LIMITS,total_raw_bytes=limit,total_stored_bytes=limit):
            with self.assertRaises(ValueError):K.build(self.root,self.out)
        self.assertFalse(self.out.exists());K.build(self.root,self.out)
        with self.assertRaises(ValueError):K.build(self.root,self.out)

    def test_corrupt_chain_and_symlink_rejected(self):
        p=self.root/'campaign-ledger.jsonl';raw=p.read_bytes();p.write_bytes(raw.replace(b'completed',b'failed',1))
        with self.assertRaises(ValueError):K.prepare(self.root,self.out)
        p.write_bytes(raw);(self.root/'extra.json').symlink_to(self.root/'campaign-spec.json')
        with self.assertRaises(ValueError):K.prepare(self.root,self.out)


if __name__=='__main__':unittest.main()
