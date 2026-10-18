"""Temporary synthetic bytes/journals only; no numerical or scientific calls."""
import ast
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compositional_typed_saved_package as K

P=K.P
ZERO=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)


def put(root,name,raw):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return K.pin(path)


def fixture(root,failed,parent=None):
    root.mkdir();stages=K.OLD_STAGES if failed else K.NEW_STAGES
    if parent is None:parent=dict(carry=dict(charged_native_applies=295,charged_seconds=222.,observed_native_applies=None),pins=[dict(path='/opaque/history/never-open',sha256='a'*64,bytes=123)])
    pp=put(root,'parent-manifest.json',P.encode(parent));descriptors={}
    for stage in stages:
        counts=dict(ZERO)
        if failed and stage=='native':counts['native_applies']=512
        if not failed and stage=='fit':counts.update(neural_forwards=3624,backwards=3600,optimizer_updates=3600,numerical_fits=2)
        descriptors[stage]=dict(argv=['/synthetic/never-execute',stage],reservation=dict(seconds=5.,**counts),expected=dict(counts),external_counters=['native_applies']if counts['native_applies']else[])
    caps=dict(seconds=185.,**dict(ZERO,native_applies=512,neural_forwards=3624,backwards=3600,optimizer_updates=3600,numerical_fits=2))
    spec=dict(schema='jepa-sealed-budget-spec/1',source_freeze_commit=('a'if failed else'b')*40,ledger_path=str(root/'campaign-ledger.jsonl'),
        parent_manifest=pp,caps=caps,guard=dict(cpu_workers=1,rss_bytes=1024**3),stage_order=list(stages),stages=descriptors,pins=[])
    sp=put(root,'campaign-spec.json',P.encode(spec));rows=[]
    def append(event,data):
        body=dict(schema='jepa-sealed-budget-journal/1',sequence=len(rows),previous_sha256=rows[-1]['record_sha256']if rows else'0'*64,event=event,data=data)
        rows.append(dict(body,record_sha256=P.digest(P.canonical(body))))
    append('initialized',dict(spec=sp));charged={k:0 for k in caps};observed=dict(ZERO)
    for stage in(stages[:3]if failed else stages):
        append('begin',dict(stage=stage,argv=descriptors[stage]['argv'],guard=spec['guard'],inputs=[]));done=dict(ZERO);intents=dict(ZERO)
        broken=failed and stage=='native';proofs=[]
        if stage=='build':proofs=[put(root,P.BINARY,b'synthetic binary excluded from payload')]
        if broken:
            proofs +=[put(root,'native-1/receipt.json',b'{"truncated":['),put(root,'native-1/transitions.jsonl',b'{"synthetic":true}\n')]
        else:proofs +=[put(root,stage+'-1/result.json',P.encode(dict(status='synthetic-completed')))]
        for counter,amount in descriptors[stage]['expected'].items():
            if not amount:continue
            token=len(rows);append('intent',dict(token=token,counter=counter,amount=amount));intents[counter]+=amount
            if not broken:append('complete',dict(token=token,actual=None,proofs=[]));done[counter]+=amount
        charge=dict(descriptors[stage]['reservation'])if broken else dict(seconds=.01,**done)
        status='failed'if broken else'completed';proofs +=[put(root,stage+'-1-stage-receipt.json',P.encode(dict(stage=stage,status=status,cleanup_verified=True)))]
        append('finish',dict(status=status,seconds=charge['seconds'],charged=charge,durable_intents=intents,durable_completed=done,
            cleanup_verified=True,execution_ended=True,proofs=proofs))
        for k,v in charge.items():charged[k]+=v
        for k in observed:observed[k]=None if broken and descriptors[stage]['reservation'][k]else observed[k]+done[k]
    jp=put(root,'campaign-ledger.jsonl',b''.join(P.canonical(row)+b'\n'for row in rows))
    cumulative=dict(charged_native_applies=parent['carry']['charged_native_applies']+charged['native_applies'],charged_seconds=parent['carry']['charged_seconds']+charged['seconds'],observed_native_applies=None)
    closure=dict(journal=jp,final_chain=rows[-1]['record_sha256'],new_charged=charged,new_observed=observed,cumulative=cumulative,source_freeze_commit=spec['source_freeze_commit'])
    if failed:closure['partial_receipt']=K.pin(root/'native-1/receipt.json')
    cp=put(root,'experiment-closure.json',P.encode(closure));return dict(carry=cumulative,pins=[jp,cp,K.pin(root/P.BINARY)]if failed else[jp,cp])


class SavedPackageTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.old=self.base/K.NAMES[0];self.new=self.base/K.NAMES[1];self.out=self.base/'packet'
        parent=fixture(self.old,True);fixture(self.new,False,parent)

    def test_source_imports_only_byte_primitives(self):
        tree=ast.parse(Path(K.__file__).read_text());names=[a.name for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(names)&{'numpy','torch','subprocess','sealed_budget'})

    def test_prepare_preserves_failed_unknown_and_writes_nothing(self):
        before={str(p):p.read_bytes()for r in(self.old,self.new)for p in r.rglob('*')if p.is_file()}
        plan=K.prepare(self.old,self.new,self.out);self.assertFalse(self.out.exists())
        self.assertEqual(before,{str(p):p.read_bytes()for r in(self.old,self.new)for p in r.rglob('*')if p.is_file()})
        h=plan['histories'];self.assertEqual(h[K.NAMES[0]]['charged']['native_applies'],512)
        self.assertIsNone(h[K.NAMES[0]]['observed']['native_applies']);self.assertEqual(h[K.NAMES[1]]['charged']['neural_forwards'],3624)
        self.assertEqual(h[K.NAMES[1]]['charged']['native_applies'],0);self.assertEqual(len(plan['excluded']),1)

    def test_roundtrip_partial_receipt_opaque_and_offline_chain_replay(self):
        result=K.build(self.old,self.new,self.out);manifest=json.loads((self.out/'manifest.json').read_text())
        self.assertEqual(result['status'],'verified-bytes-only')
        entry=next(e for e in manifest['files']if e.get('provenance',{}).get('original_path')==str(self.old/'native-1/receipt.json'))
        self.assertEqual(gzip.decompress((self.out/entry['url']).read_bytes()),b'{"truncated":[')
        self.assertFalse(any(e['url'].endswith(P.BINARY)for e in manifest['files']))
        self.old.rename(self.base/'old-unavailable');self.new.rename(self.base/'new-unavailable')
        K.verify(self.out,P.digest((self.out/'manifest.json').read_bytes()))
        with self.assertRaises(ValueError):K.verify(self.out,'0'*64)

    def test_missing_closure_or_pending_stage_rejected_before_writes(self):
        (self.new/'experiment-closure.json').unlink()
        with self.assertRaises(FileNotFoundError):K.build(self.old,self.new,self.out)
        self.assertFalse(self.out.exists())

    def test_chain_corruption_and_failed_reservation_cannot_be_rewritten(self):
        path=self.old/'campaign-ledger.jsonl';rows=[json.loads(v)for v in path.read_text().splitlines()]
        rows[-1]['data']['charged']['native_applies']=0;path.write_bytes(b''.join(P.canonical(row)+b'\n'for row in rows))
        with self.assertRaises(ValueError):K.prepare(self.old,self.new,self.out)
        self.assertFalse(self.out.exists())

    def test_pin_mismatch_is_not_historical_path_fallback(self):
        (self.old/P.BINARY).write_bytes(b'changed binary')
        with self.assertRaises(ValueError):K.prepare(self.old,self.new,self.out)
        self.assertFalse(self.out.exists())

    def test_metadata_limit_preflight_and_exclusive_safe_destination(self):
        plan=K.prepare(self.old,self.new,self.out);total=max(sum(e[k]for e in plan['files'])for k in('bytes','raw_bytes'))
        with patch.object(P,'MAX_TOTAL',total):
            with self.assertRaises(ValueError):K.build(self.old,self.new,self.out)
        self.assertFalse(self.out.exists())
        with self.assertRaises(ValueError):K.prepare(self.old,self.new,self.old/'overlap')
        alias=self.base/'alias';alias.symlink_to(self.base/'missing',target_is_directory=True)
        with self.assertRaises(ValueError):K.prepare(self.old,self.new,alias)

    def test_deterministic_bytes_exact_membership_and_bounded_decode(self):
        K.build(self.old,self.new,self.out);second=self.base/'second';K.build(self.old,self.new,second)
        self.assertEqual({p.relative_to(self.out).as_posix():p.read_bytes()for p in self.out.rglob('*')if p.is_file()},
            {p.relative_to(second).as_posix():p.read_bytes()for p in second.rglob('*')if p.is_file()})
        (self.out/'unregistered.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):K.verify(self.out)


if __name__=='__main__':unittest.main()
