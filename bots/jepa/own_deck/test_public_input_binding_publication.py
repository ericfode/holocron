import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import publication_checkpoint as P
import public_input_binding_export as X
import public_input_binding_publication as U
from publication_portable import Closure


def save(path,value):
    raw=P.encoded(value);path.write_bytes(raw);return P.pinned(path,raw)


class PublicationTests(unittest.TestCase):
    def archive(self,root):
        root.mkdir();(root/'raw').mkdir();decoded=P.encoded(dict(score=1.,known=[1,0],semantic_validated=False))
        packed=gzip.compress(decoded,mtime=0);(root/'raw/data.json.gz').write_bytes(packed)
        item=dict(id='scores',role='scores',url='raw/data.json.gz',sha256=P.digest(packed),bytes=len(packed),encoding='gzip',raw_sha256=P.digest(decoded),raw_bytes=len(decoded))
        vector=save(root/'vectors.json',dict(rows=[dict(id='a',vector=[1.,2.])],source_array=item,semantic_validated=False))
        index=save(root/'index.json',dict(schema='jepa-public-input-binding-evidence/1',artifacts=[item],spaces=[dict(url='vectors.json',sha256=vector['sha256'],bytes=vector['bytes'])]))
        files=[dict(url=str(p.relative_to(root)),sha256=P.digest(p.read_bytes()),bytes=p.stat().st_size)for p in root.rglob('*')if p.is_file()]
        manifest=save(root/'manifest.json',dict(files=files))
        return index,manifest

    def test_nested_urls_and_gzip_science_become_verified_path_pins(self):
        with tempfile.TemporaryDirectory()as name:
            base=Path(name);index,manifest=self.archive(base/'archive');before={str(p):p.read_bytes()for p in(base/'archive').rglob('*')if p.is_file()}
            result=U.ConsumerAdapter(index,manifest,base/'adapter').build();path,raw=U.pinned_read(result['root']);value=json.loads(raw)
            score=value['artifacts'][0];_,raw=U.pinned_read(score);decoded=json.loads(raw)
            self.assertEqual(decoded['score'],1.);self.assertEqual(decoded['known'],[1,0])
            self.assertEqual(score['encoding'],'identity');U.pinned_read(score['raw_download'])
            _,raw=U.pinned_read(value['spaces'][0]);vector=json.loads(raw);U.pinned_read(vector['source_array'])
            portable=base/'portable';portable.mkdir();closure=Closure(portable);closure.copy(result['root'],path)
            self.assertGreater(closure.verify_sources_unchanged(),1)
            self.assertTrue(all(Path(p).read_bytes()==b for p,b in before.items()))

    def test_tamper_and_traversal_fail_without_original_rewrites(self):
        with tempfile.TemporaryDirectory()as name:
            base=Path(name);index,manifest=self.archive(base/'archive');adapter=U.ConsumerAdapter(index,manifest,base/'adapter')
            with self.assertRaises(ValueError):adapter.resolve('../outside',Path(index['path']))
            (base/'archive/raw/data.json.gz').write_bytes(b'tampered')
            with self.assertRaises(ValueError):adapter.build()

    def journal_archive(self,root,suffix,threshold):
        source=root/'values.json';save(source,dict(value=7,semantic_validated=False))
        journal=root/('ledger'+suffix)
        records=[dict(event='start',evidence=X.file_pin(source)),dict(event='finish',count=2)]
        journal.write_bytes(json.dumps(records[0]).encode()+b'\n\n'+json.dumps(records[1]).encode()+b'\n')
        config=root/'config.json';save(config,dict(schema='synthetic',pins=[X.file_pin(journal)]))
        artifacts=[X.artifact(role,role,journal if role=='accounting'else source)for role in sorted(X.REQUIRED)]
        artifacts.append(X.artifact('raw-journal','source',journal))
        result=X.build(config,root/'archive',artifacts,gzip_threshold=threshold)
        return result,records,journal

    def test_multiline_journals_keep_order_raw_bytes_and_portable_closure(self):
        for suffix in('.jsonl','.ndjson'):
            for threshold in(0,999999):
                with self.subTest(suffix=suffix,gzip=threshold==0),tempfile.TemporaryDirectory()as name:
                    root=Path(name);bundle,records,journal=self.journal_archive(root,suffix,threshold)
                    before={p:p.read_bytes()for p in(root/'archive').rglob('*')if p.is_file()}
                    result=U.ConsumerAdapter(bundle['index'],bundle['manifest'],root/'adapter').build()
                    path,raw=U.pinned_read(result['root']);index=json.loads(raw)
                    item=next(x for x in index['artifacts']if x['id']=='accounting')
                    _,raw=U.pinned_read(item);view=json.loads(raw)
                    self.assertEqual(view['format'],suffix[1:]);self.assertEqual(view['record_count'],2)
                    self.assertEqual([x['event']for x in view['records']],['start','finish'])
                    self.assertEqual(view['provenance']['original_line_numbers'],[1,3])
                    self.assertEqual(view['records'][1],records[1])
                    _,raw=U.pinned_read(view['records'][0]['evidence']);self.assertEqual(json.loads(raw)['value'],7)
                    _,raw=U.pinned_read(item['decoded_raw_download']);self.assertEqual(raw,journal.read_bytes())
                    _,stored=U.pinned_read(item['raw_download'])
                    self.assertEqual(gzip.decompress(stored)if threshold==0 else stored,journal.read_bytes())
                    portable=root/'portable';portable.mkdir();closure=Closure(portable);closure.copy(result['root'],path)
                    self.assertGreater(closure.verify_sources_unchanged(),1)
                    self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))

    def test_opaque_multiline_journal_is_not_parsed_or_mislabeled_json(self):
        for suffix in('.jsonl','.ndjson'):
            for threshold in(0,999999):
                with self.subTest(suffix=suffix,gzip=threshold==0),tempfile.TemporaryDirectory()as name:
                    root=Path(name);bundle,_,journal=self.journal_archive(root,suffix,threshold)
                    result=U.ConsumerAdapter(bundle['index'],bundle['manifest'],root/'adapter').build()
                    path,raw=U.pinned_read(result['root']);index=json.loads(raw)
                    opaque=next(x for x in index['artifacts']if x['id']=='raw-journal')
                    self.assertEqual(Path(opaque['path']).suffix,'.bin')
                    _,stored=U.pinned_read(opaque)
                    self.assertEqual(gzip.decompress(stored)if threshold==0 else stored,journal.read_bytes())
                    self.assertEqual(opaque['format'],suffix[1:]);self.assertEqual(opaque['raw_sha256'],P.digest(journal.read_bytes()))
                    self.assertEqual(opaque['encoding'],'gzip'if threshold==0 else'identity')
                    portable=root/'portable';portable.mkdir();closure=Closure(portable);closure.copy(result['root'],path)
                    closure.verify_sources_unchanged()

    def test_source_index_with_its_own_relative_urls_remains_opaque(self):
        for threshold in(0,999999):
            with self.subTest(gzip=threshold==0),tempfile.TemporaryDirectory()as name:
                root=Path(name);old=root/'old-index.json'
                save(old,dict(artifacts=[dict(url='raw/old-only.json',sha256='0'*64,bytes=1)]))
                cache=dict(fingerprint=dict(path='/unarchived/cargo/lib-kessel.json',sha256='0'*64,bytes=646))
                config=root/'config.json';save(config,dict(pins=[X.file_pin(old)]))
                data=root/'data.json';save(data,dict(value=1))
                artifacts=[X.artifact(role,role,data)for role in sorted(X.REQUIRED)]
                bundle=X.build(config,root/'archive',artifacts,gzip_threshold=threshold)
                adapter=U.ConsumerAdapter(bundle['index'],bundle['manifest'],root/'adapter')
                metadata=adapter.convert(dict(metadata=dict(build_cache_disclosure=cache)),Path(bundle['index']['path']))
                self.assertEqual(metadata['metadata']['provenance']['build_cache_disclosure'],cache)
                result=adapter.build()
                path,raw=U.pinned_read(result['root']);index=json.loads(raw)
                _,raw=U.pinned_read(next(x for x in index['artifacts']if x['id']=='campaign-config'))
                value=json.loads(raw);pin=value['pins'][0];self.assertEqual(Path(pin['path']).suffix,'.bin')
                _,stored=U.pinned_read(pin)
                self.assertEqual(gzip.decompress(stored)if threshold==0 else stored,old.read_bytes())
                portable=root/'portable';portable.mkdir();closure=Closure(portable);closure.copy(result['root'],path)
                closure.verify_sources_unchanged()

    def registry(self,root):
        vectors=save(root/'vectors.json',dict(rows=[dict(vector=[1.,2.])]))
        banks=dict(schema='jepa-embedding-browser-index/1',spaces={f'old{i}':dict(id=f'old-space-{i}',semantic_validated=False)for i in range(10)})
        embedding=save(root/'embedding.json',banks)
        artifacts={f'old{i}':vectors for i in range(37)};artifacts['embedding_index']=embedding
        index=save(root/'research.json',dict(schema='jepa-research-handoff-index/1',artifacts=artifacts,counts={}))
        return index,embedding,artifacts,banks,vectors

    def test_additive_registry_keeps_all_old_records_and_exact_ids(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);index,embedding,old,banks,vectors=self.registry(root)
            space=dict(id='new-space',dimension=2,entity_count=1,vectors_path=vectors['path'],artifact_sha256=vectors['sha256'],semantic_validated=False)
            kwargs=dict(artifacts={'new-proof':vectors},spaces={'new':space},new_embedding_path=root/'next-embedding.json',expected_old_artifact_ids=list(old),expected_old_space_ids=[v['id']for v in banks['spaces'].values()],expected_final_artifact_ids=[*old,'new-proof'],expected_final_space_ids=[*[v['id']for v in banks['spaces'].values()],'new-space'])
            result=U.prepare_registry(index,embedding,**kwargs)
            self.assertEqual(result['artifact_count'],39);self.assertEqual(result['space_count'],11)
            for k,v in old.items():
                if k!='embedding_index':self.assertEqual(result['index']['artifacts'][k],v)
            for k,v in banks['spaces'].items():self.assertEqual(result['embedding_index']['spaces'][k],v)
            self.assertFalse((root/'next-embedding.json').exists())
            wrong=copy.deepcopy(kwargs);wrong['expected_final_space_ids']=wrong['expected_final_space_ids'][:-1]
            with self.assertRaises(ValueError):U.prepare_registry(index,embedding,**wrong)
            wrong=copy.deepcopy(kwargs);wrong['artifacts']={'old0':vectors}
            with self.assertRaises(ValueError):U.prepare_registry(index,embedding,**wrong)

    def test_unmapped_active_host_path_is_not_a_fallback(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);index,manifest=self.archive(root/'archive');adapter=U.ConsumerAdapter(index,manifest,root/'adapter')
            with self.assertRaises(ValueError):adapter.convert(dict(path='/private/unknown.json',sha256='0'*64,bytes=1),Path(index['path']))

    def test_browser_view_preserves_saved_vectors_and_zero_norm_status(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);source=save(root/'bank.json',dict(space_id='saved-test',dimension=2,semantic_validated=False,rows=[dict(id='a',vector=[3.,4.]),dict(id='b',vector=[0.,0.])]))
            result=U.prepare_browser_bank(source,root/'new-bank.json');rows=result['value']['rows']
            self.assertEqual(rows[0]['vector'],[3.,4.]);self.assertEqual(rows[0]['l2_norm'],5.)
            self.assertEqual(rows[0]['unit_vector'],[.6,.8]);self.assertFalse(rows[1]['cosine_available']);self.assertIsNone(rows[1]['unit_vector'])
            self.assertFalse((root/'new-bank.json').exists())


if __name__=='__main__':unittest.main()
