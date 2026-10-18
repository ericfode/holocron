"""Synthetic byte files only; no numerical/model/native execution."""
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import compositional_typed_package as P


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'compositional-typed-v1';self.root.mkdir();self.out=self.base/'packet';self.commit='a'*40
        self.put('parent-manifest.json',P.encode(dict(pins=[dict(path='/provenance-only/not-a-file',sha256='f'*64,bytes=123)])))
        parent=(self.root/'parent-manifest.json').read_bytes();zero=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
        self.spec=dict(schema='jepa-sealed-budget-spec/1',source_freeze_commit=self.commit,ledger_path=str(self.root/'campaign-ledger.jsonl'),
            stage_order=list(P.STAGES),guard=dict(cpu_workers=1,rss_bytes=1024**3),parent_manifest=dict(path=str(self.root/'parent-manifest.json'),sha256=P.digest(parent),bytes=len(parent)),stages={})
        for stage in P.STAGES:
            self.spec['stages'][stage]=dict(argv=['/synthetic/never-executed',stage],reservation=dict(seconds=1.,**zero),expected=dict(zero),external_counters=[])
            self.put(stage+'-1-stage-receipt.json',P.encode(dict(stage=stage,status='completed',synthetic=True)))
            self.put(stage+'-1/receipt.json',P.encode(dict(synthetic=True)))
        self.put('campaign-spec.json',P.encode(self.spec))
        spec_raw=(self.root/'campaign-spec.json').read_bytes();rows=[]
        def append(event,data):
            body=dict(schema='jepa-sealed-budget-journal/1',sequence=len(rows),previous_sha256=rows[-1]['record_sha256']if rows else'0'*64,event=event,data=data)
            rows.append(dict(body,record_sha256=P.digest(P.canonical(body))))
        append('initialized',dict(spec=dict(path=str(self.root/'campaign-spec.json'),sha256=P.digest(spec_raw),bytes=len(spec_raw))))
        for stage in P.STAGES:
            append('begin',dict(stage=stage,argv=self.spec['stages'][stage]['argv'],guard=self.spec['guard']))
            append('finish',dict(status='completed',cleanup_verified=True,execution_ended=True,charged=dict(seconds=.01,**zero),seconds=.01))
        self.rows=rows;self.write_rows()
        for name in('metadata-1/native-plan.json','native-1/native-verification.json','prep-1/manifest.json','fit-1/result.json','verify-1/result.json'):
            self.put(name,P.encode(dict(synthetic=True,status='PASS')))
        self.put('native-1/transitions.jsonl',b'{"synthetic":true}\n');self.put('native-1/stdout.log',b'toy stdout\n');self.put('native-1/stderr.log',b'')
        self.put('prep-1/dataset.npz',b'PK synthetic NPZ bytes, never interpreted')
        self.put('fit-1/toy-checkpoint.npz',b'PK synthetic frozen bytes');self.put('fit-1/progress.jsonl',b'{"toy":true}\n')
        self.put(P.BINARY,b'not an executable; excluded synthetic binary')

    def put(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)

    def write_rows(self):
        previous='0'*64
        for i,row in enumerate(self.rows):
            row.update(sequence=i,previous_sha256=previous);body={k:v for k,v in row.items()if k!='record_sha256'};previous=P.digest(P.canonical(body));row['record_sha256']=previous
        self.put('campaign-ledger.jsonl',b''.join(P.canonical(row)+b'\n'for row in self.rows))

    def manifest(self):return json.loads((self.out/'manifest.json').read_text())
    def save_manifest(self,m):
        (self.out/'manifest.json').write_bytes(P.encode(m))

    def test_import_and_source_are_byte_only(self):
        tree=ast.parse(Path(P.__file__).read_text());names=[a.name for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(names)&{'numpy','torch','subprocess','sealed_budget'})
        self.assertNotIn('eval(',Path(P.__file__).read_text());self.assertNotIn('exec(',Path(P.__file__).read_text())

    def test_prepare_no_writes_and_closed_gate(self):
        before={str(p):p.read_bytes()for p in self.root.rglob('*')if p.is_file()}
        plan=P.prepare(self.root,self.out,self.commit)
        self.assertFalse(self.out.exists());self.assertEqual(before,{str(p):p.read_bytes()for p in self.root.rglob('*')if p.is_file()})
        self.assertEqual(plan['source_freeze_commit'],self.commit);self.assertEqual(plan['closed_journal']['completed_stages'],list(P.STAGES))
        self.rows.pop();self.write_rows()
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,self.commit)
        self.assertFalse(self.out.exists())

    def test_build_exact_roundtrip_binary_pin_and_offline_provenance(self):
        result=P.build(self.root,self.out,self.commit);m=self.manifest()
        self.assertEqual(result['status'],'verified-bytes-only');self.assertEqual(len(m['excluded']),1)
        self.assertEqual(m['excluded'][0]['raw_sha256'],P.digest((self.root/P.BINARY).read_bytes()))
        self.assertFalse((self.out/'payload'/P.BINARY).exists())
        original={e['provenance']['original_path']:e for e in m['files']if 'provenance'in e}
        for path,e in original.items():
            raw=(self.out/e['url']).read_bytes();decoded=gzip.decompress(raw)if e['encoding']=='gzip'else raw
            self.assertEqual(decoded,Path(path).read_bytes())
        for e in m['files']:
            if 'provenance'in e:e['provenance']['original_path']='/this/external/path/must/not/be/fetched'
        self.save_manifest(m);P.verify(self.out)
        with self.assertRaises(ValueError):P.build(self.root,self.out,self.commit)

    def test_deterministic_gzip_and_manifest_pin(self):
        P.build(self.root,self.out,self.commit);other=self.base/'second';P.build(self.root,other,self.commit)
        a={p.relative_to(self.out).as_posix():p.read_bytes()for p in self.out.rglob('*')if p.is_file()}
        b={p.relative_to(other).as_posix():p.read_bytes()for p in other.rglob('*')if p.is_file()}
        self.assertEqual(a,b);P.verify(self.out,P.digest(a['manifest.json']))
        with self.assertRaises(ValueError):P.verify(self.out,'0'*64)

    def test_declared_limits_checked_before_payload_fetch(self):
        good=dict(url='toy',encoding='identity',sha256='a'*64,raw_sha256='a'*64,bytes=0,raw_bytes=0)
        e=dict(good,raw_bytes=P.MAX_FILE+1)
        with self.assertRaises(ValueError):P.check_entries([e])
        with self.assertRaises(ValueError):P.check_entries([dict(good,url=str(i))for i in range(P.MAX_FILES)])
        with self.assertRaises(ValueError):P.check_entries([dict(good,url=str(i),bytes=P.MAX_FILE,raw_bytes=P.MAX_FILE)for i in range(4)],1)

    def test_metadata_total_preflight_precedes_destination_creation(self):
        plan=P.prepare(self.root,self.out,self.commit);payload_total=max(sum(e[k]for e in plan['files'])for k in('bytes','raw_bytes'))
        with patch.object(P,'MAX_TOTAL',payload_total):
            with self.assertRaises(ValueError):P.build(self.root,self.out,self.commit)
        self.assertFalse(self.out.exists())

    def test_traversal_duplicate_and_extra_members_rejected(self):
        P.build(self.root,self.out,self.commit);original=self.manifest()
        for name in('../outside','/absolute','a/../b','a//b','a\\b','a:b','./file'):
            m=copy.deepcopy(original);m['files'][0]['url']=name;self.save_manifest(m)
            with self.assertRaises(ValueError):P.verify(self.out)
        m=copy.deepcopy(original);m['files'].append(m['files'][0]);self.save_manifest(m)
        with self.assertRaises(ValueError):P.verify(self.out)
        self.save_manifest(original);(self.out/'unexpected').write_text('synthetic')
        with self.assertRaises(ValueError):P.verify(self.out)

    def test_gzip_truncated_excess_and_stored_corruption_rejected(self):
        P.build(self.root,self.out,self.commit);original=self.manifest();entry=next(e for e in original['files']if e['encoding']=='gzip');path=self.out/entry['url'];saved=path.read_bytes()
        for blob,raw_bytes in((saved[:-4],entry['raw_bytes']),(gzip.compress(b'x'*10000,mtime=0),1)):
            m=copy.deepcopy(original);e=next(v for v in m['files']if v['url']==entry['url']);path.write_bytes(blob);e.update(bytes=len(blob),sha256=P.digest(blob),raw_bytes=raw_bytes);self.save_manifest(m)
            with self.assertRaises(ValueError):P.verify(self.out)
        path.write_bytes(saved+b'junk');self.save_manifest(original)
        with self.assertRaises(ValueError):P.verify(self.out)

    def test_identity_raw_cap_and_symlinks(self):
        P.build(self.root,self.out,self.commit);m=self.manifest();e=next(e for e in m['files']if e['url'].endswith('.npz'));e['raw_bytes']=0;self.save_manifest(m)
        with self.assertRaises(ValueError):P.verify(self.out)
        self.out.joinpath(e['url']).unlink();self.out.joinpath(e['url']).symlink_to(self.root/'prep-1/dataset.npz')
        with self.assertRaises(ValueError):P.verify(self.out)

    def test_failed_or_uninitialized_campaign_never_packaged(self):
        self.rows[-1]['data']['status']='failed';self.write_rows()
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,self.commit)
        self.rows[-1]['data']['status']='completed';self.rows.pop(0);self.write_rows()
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,self.commit)

    def test_wrong_commit_changed_parent_missing_required_and_overlap(self):
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,'b'*40)
        with self.assertRaises(ValueError):P.prepare(self.root,self.root/'packet',self.commit)
        alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):P.prepare(alias,self.out,self.commit)
        destination=self.base/'dangling';destination.symlink_to(self.base/'not-created',target_is_directory=True)
        with self.assertRaises(ValueError):P.prepare(self.root,destination,self.commit)
        parent=self.root/'parent-manifest.json';original=parent.read_bytes();parent.write_bytes(original+b' ')
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,self.commit)
        parent.write_bytes(original);(self.root/'fit-1/result.json').unlink()
        with self.assertRaises(ValueError):P.prepare(self.root,self.out,self.commit)

    def test_manifest_cap_source_symlink_and_unknown_file(self):
        P.build(self.root,self.out,self.commit)
        with patch.object(P,'MAX_MANIFEST',10):
            with self.assertRaises(ValueError):P.verify(self.out)
        self.put('fit-1/unknown.env',b'synthetic placeholder, no credential')
        with self.assertRaises(ValueError):P.prepare(self.root,self.base/'unused',self.commit)
        (self.root/'fit-1/unknown.env').unlink();(self.root/'fit-1/link.json').symlink_to(self.root/'fit-1/result.json')
        with self.assertRaises(ValueError):P.prepare(self.root,self.base/'unused',self.commit)


if __name__=='__main__':unittest.main()
