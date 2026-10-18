"""Prepare additive consumer records from immutable evidence; never select/publish a pointer."""
import copy
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

import publication_checkpoint as P
from publication_portable import PROVENANCE_KEYS, safe_url

READABLE_ROLES = {'data','scores','causal-pairs','encoding-controls','contract','verification','accounting'}


def pinned_read(expected):
    path=Path(expected['path']);raw=path.read_bytes()
    if P.digest(raw)!=expected['sha256']or len(raw)!=expected['bytes']:
        raise ValueError('immutable source pin differs: '+str(path))
    return path.resolve(),raw


class ConsumerAdapter:
    """All changes are reference rewrites; original archive/data remain byte-exact."""
    def __init__(self,index_pin,manifest_pin,destination):
        self.index_path,index_raw=pinned_read(index_pin);manifest_path,raw=pinned_read(manifest_pin)
        self.root=self.index_path.parent
        if manifest_path.parent!=self.root:raise ValueError('index and manifest must share immutable bundle root')
        self.index=P.read_json(index_raw);manifest=P.read_json(raw)
        self.files={}
        for record in manifest['files']:
            url=safe_url(record['url'])
            if url in self.files:raise ValueError('duplicate manifest URL')
            self.files[url]=record
        self.destination=Path(destination).resolve();self.stage=self.destination.with_name(self.destination.name+'.staging')
        if self.destination.is_relative_to(self.root):raise ValueError('adapter cannot write inside immutable original archive')
        if self.destination.exists()or self.stage.exists():raise FileExistsError('new immutable adapter directory required')
        self.cache={};self.active=set();self.rewrites=[];self.checked={};self.originals={}
        for record in self.index.get('artifacts',[]):
            original=record.get('provenance',{}).get('original_path')
            raw_sha=record.get('raw_sha256',record.get('original_sha256'))
            if original and raw_sha:
                key=(str(Path(original).resolve()),raw_sha)
                if key not in self.originals or record.get('role')in READABLE_ROLES:self.originals[key]=record
        self.source_pins=[index_pin,manifest_pin]

    def resolve(self,url,origin):
        relative=safe_url(url);candidate=Path(origin).parent/relative
        if candidate.is_symlink():raise ValueError('symlink evidence reference forbidden')
        path=candidate.resolve()
        if not path.is_relative_to(self.root)or not path.is_file():raise ValueError('missing/outside evidence URL')
        key=path.relative_to(self.root).as_posix()
        if key not in self.files:raise ValueError('URL absent from complete manifest')
        raw=path.read_bytes();expected=self.files[key]
        if P.digest(raw)!=expected['sha256']or len(raw)!=expected['bytes']:raise ValueError('manifest payload mismatch')
        self.checked[key]=dict(path=str(path),sha256=expected['sha256'],bytes=expected['bytes'])
        return path,raw

    def convert(self,value,origin):
        if isinstance(value,list):return [self.convert(v,origin)for v in value]
        if not isinstance(value,dict):return value
        if isinstance(value.get('url'),str):
            path,raw=self.resolve(value['url'],origin)
            # Present hash/byte pairs are always interpreted as STORED bytes.
            if 'sha256'in value and (value['sha256']!=P.digest(raw)or value.get('bytes')!=len(raw)):
                raise ValueError('URL record differs from stored payload pin')
            readable=value.get('role')in READABLE_ROLES
            target=self.copy_file(path,raw,readable=readable,record=value)
            extra={k:self.convert(v,origin)for k,v in value.items()if k not in('url','sha256','bytes','provenance')}
            extra.update(target)
            if target.get('status')=='consumer-derived-reference-view':
                for field in('original_sha256','original_bytes'):extra.pop(field,None)
                extra.update(encoding='identity',raw_sha256=target['sha256'],raw_bytes=target['bytes'],
                             status='consumer-derived-reference-view')
            extra['provenance']={'original_reference':value,'reference_rewrite':'verified archive URL to explicit consumer path pin'}
            self.rewrites.append(dict(origin=str(origin),url=value['url'],target=target))
            return extra
        if isinstance(value.get('path'),str)and isinstance(value.get('sha256'),str):
            original=Path(value['path']);original=original if original.is_absolute()else Path(origin).parent/original
            record=self.originals.get((str(original.resolve()),value['sha256']))
            if record is None:raise ValueError('unmapped active original path pin; explicit archive mapping required: '+str(original))
            path,raw=self.resolve(record['url'],self.index_path)
            return self.copy_file(path,raw,readable=record.get('role')in READABLE_ROLES,record=record)
        result={}
        for key,child in value.items():
            if key in PROVENANCE_KEYS or key in('provenance_only','original_path','original_paths','build_cache_disclosure')or(key in('source','base')and isinstance(child,dict)and'path'in child):
                result.setdefault('provenance',{})[key]=child
            else:result[key]=self.convert(child,origin)
        return result

    def copy_file(self,path,raw,readable=False,record=None):
        record=record or {}
        # The immutable exporter may store JSONL/NDJSON under a .json[.gz]
        # filename. Its original-path metadata, rather than the stored suffix,
        # determines whether this is a sequence of documents.
        original_suffix=Path(record.get('provenance',{}).get('original_path','')).suffix.lower()
        line_format=original_suffix[1:]if original_suffix in('.jsonl','.ndjson')else None
        source_opaque=record.get('role')=='source'
        key=(str(path),P.digest(raw),readable,line_format,source_opaque)
        if key in self.cache:return self.cache[key]
        if key in self.active:raise ValueError('cyclic active evidence references')
        self.active.add(key);decoded=raw
        if record.get('encoding')=='gzip'and(readable or line_format or source_opaque):
            decoded=gzip.decompress(raw)
            expected=record.get('raw_sha256',record.get('original_sha256'))
            count=record.get('raw_bytes',record.get('original_bytes'))
            if not expected or P.digest(decoded)!=expected or len(decoded)!=count:
                raise ValueError('decoded science JSON pin mismatch')
        if line_format:
            expected=record.get('raw_sha256',record.get('original_sha256'))
            count=record.get('raw_bytes',record.get('original_bytes'))
            if expected!=P.digest(decoded)or count!=len(decoded):raise ValueError('JSON lines raw pin mismatch')
        is_json=not line_format and not source_opaque and(path.suffix=='.json'or(readable and record.get('encoding')=='gzip'))
        if is_json or(line_format and readable):
            if line_format:
                records=[];line_numbers=[];lines=decoded.splitlines()
                for number,line in enumerate(lines,1):
                    if not line.strip():continue
                    try:value=P.read_json(line)
                    except(ValueError,UnicodeError)as error:raise ValueError('invalid '+line_format+' record at line '+str(number))from error
                    records.append(self.convert(value,path));line_numbers.append(number)
                value=dict(schema='jepa-consumable-json-lines/1',format=line_format,records=records,record_count=len(records),
                    provenance=dict(original_raw_sha256=P.digest(decoded),original_raw_bytes=len(decoded),
                                    original_line_numbers=line_numbers,blank_lines_ignored=len(lines)-len(records)))
            else:value=self.convert(P.read_json(decoded),path)
            if isinstance(value,dict):value.setdefault('provenance',{})['consumer_adapter']=dict(schema='jepa-consumable-evidence-adapter/1',original_payload_sha256=P.digest(decoded),scientific_numbers_recomputed=False)
            adapted=P.encoded(value);name=hashlib.sha256((str(path)+P.digest(raw)+str(readable)+str(line_format)).encode()).hexdigest()[:24]+'.json'
            P._write_exclusive(self.stage/name,adapted)
            original_name=P.digest(raw)+'.original.bin'
            if not (self.stage/original_name).exists():P._write_exclusive(self.stage/original_name,raw)
            result=dict(path=str(self.destination/name),sha256=P.digest(adapted),bytes=len(adapted),
                        raw_download=dict(path=str(self.destination/original_name),sha256=P.digest(raw),bytes=len(raw)),
                        status='consumer-derived-reference-view')
            if line_format:
                decoded_name=P.digest(decoded)+'.original.bin'
                if not(self.stage/decoded_name).exists():P._write_exclusive(self.stage/decoded_name,decoded)
                result['decoded_raw_download']=dict(path=str(self.destination/decoded_name),sha256=P.digest(decoded),bytes=len(decoded))
        elif line_format or source_opaque:
            # Opaque line-oriented evidence must also lose the misleading .json
            # suffix before the existing portable closure sees it.
            name=P.digest(raw)+'.original.bin'
            if not(self.stage/name).exists():P._write_exclusive(self.stage/name,raw)
            result=dict(path=str(self.destination/name),sha256=P.digest(raw),bytes=len(raw),format=line_format or 'opaque-source',
                        encoding=record.get('encoding','identity'),raw_sha256=P.digest(decoded),raw_bytes=len(decoded),
                        payload_role='raw-download-no-embedded-fetches')
        else:result=dict(path=str(path),sha256=P.digest(raw),bytes=len(raw))
        self.cache[key]=result;self.active.remove(key);return result

    def build(self):
        actual={p.relative_to(self.root).as_posix()for p in self.root.rglob('*')if p.is_file()}
        if actual!=set(self.files)|{'manifest.json'}:raise ValueError('manifest must describe exact immutable archive closure')
        for url in self.files:self.resolve(url,self.index_path)
        self.stage.mkdir(parents=True)
        expected=self.files.get(self.index_path.name)
        if expected is None:raise ValueError('manifest must pin original root index')
        path,raw=self.resolve(self.index_path.name,self.index_path)
        root=self.copy_file(path,raw,readable=True)
        for item in self.checked.values():pinned_read(item)
        for item in self.source_pins:pinned_read(item)
        record=dict(schema='jepa-consumable-adapter-manifest/1',root=root,
                    references_rewritten=self.rewrites,verified_archive_payloads=list(self.checked.values()),
                    provenance=dict(original_sources=self.source_pins,old_archive_unchanged=True),
                    semantic_validated=False,neural_forwards=0,optimizer_updates=0,native_applies=0,numerical_fits=0)
        P._write_exclusive(self.stage/'adapter-manifest.json',P.encoded(record));os.rename(self.stage,self.destination)
        return record


def prepare_browser_bank(bank_pin,destination):
    """Add browser row metadata to saved, already consumer-adapted vectors; no forward/fit."""
    _,raw=pinned_read(bank_pin);bank=P.read_json(raw)
    def no_unadapted_urls(value):
        if isinstance(value,list):
            for child in value:no_unadapted_urls(child)
        elif isinstance(value,dict):
            if 'url'in value:raise ValueError('consumer-adapt the original archive before preparing browser rows')
            for key,child in value.items():
                if key not in PROVENANCE_KEYS and key!='provenance_only':no_unadapted_urls(child)
    no_unadapted_urls(bank)
    if bank.get('semantic_validated')is not False:raise ValueError('unqualified status must stay explicit')
    dimension=bank['dimension'];seen=set();result=copy.deepcopy(bank)
    if type(dimension)is not int or dimension<1:raise ValueError('positive integer vector dimension required')
    for row in result['rows']:
        identity=row['id'];vector=row['vector']
        if not isinstance(identity,str)or not identity or identity in seen:raise ValueError('unique row IDs required')
        if len(vector)!=dimension or any(type(v)not in(int,float)or not math.isfinite(v)for v in vector):raise ValueError('finite exact-width raw vector required')
        seen.add(identity);norm=math.sqrt(sum(v*v for v in vector))
        if not math.isfinite(norm):raise ValueError('nonfinite vector norm')
        row.update(l2_norm=norm,cosine_available=norm>0,unit_vector=[v/norm for v in vector]if norm else None,semantic_validated=False)
    result.setdefault('provenance',{})['browser_view']=dict(saved_bank=bank_pin,neural_forwards=0,raw_vectors_unchanged=True)
    target=Path(destination)
    if not target.is_absolute()or target.exists():raise ValueError('new versioned bank destination required')
    raw=P.encoded(result);space=dict(id=result['space_id'],status='available',entity_type=result.get('entity_type','card'),
        dimension=dimension,entity_count=len(result['rows']),semantic_validated=False,
        vectors_path=str(target),artifact_sha256=P.digest(raw),vectors_bytes=len(raw),
        limitation='Saved diagnostic checkpoint space; distinct basis and no semantic/neighborhood validation.')
    return dict(value=result,raw=raw,space=space,publish_performed=False)


def prepare_registry(index_pin,embedding_pin,*,artifacts,spaces,new_embedding_path,
                     expected_old_artifact_ids,expected_old_space_ids,
                     expected_final_artifact_ids,expected_final_space_ids):
    """Return reviewable bytes; no writes, CI claims, stable-pointer changes or deployment."""
    _,raw=pinned_read(index_pin);index=P.read_json(raw)
    _,raw=pinned_read(embedding_pin);embedding=P.read_json(raw)
    if index['schema']!='jepa-research-handoff-index/1'or embedding['schema']!='jepa-embedding-browser-index/1':raise ValueError('existing consumer schemas required')
    if index['artifacts']['embedding_index']!=embedding_pin:raise ValueError('use pinned current ten-space index, not stale mutable index')
    old_keys=set(expected_old_artifact_ids);old_spaces=set(expected_old_space_ids)
    for expected in (expected_old_artifact_ids,expected_old_space_ids,expected_final_artifact_ids,expected_final_space_ids):
        if len(expected)!=len(set(expected)):raise ValueError('frozen ID lists cannot contain duplicates')
    if len(old_keys)!=38 or len(old_spaces)!=10 or set(index['artifacts'])!=old_keys or {v['id']for v in embedding['spaces'].values()}!=old_spaces:
        raise ValueError('exact original38 artifact and10 space IDs required')
    result=copy.deepcopy(index);banks=copy.deepcopy(embedding)
    for key,value in artifacts.items():
        if key in old_keys:raise ValueError('existing artifact records cannot be overwritten')
        pinned_read(value);result['artifacts'][key]=copy.deepcopy(value)
    for key,value in spaces.items():
        if key in banks['spaces']or value.get('semantic_validated')is not False:raise ValueError('new unique explicitly unqualified space required')
        for field in('id','dimension','entity_count','vectors_path','artifact_sha256'):value[field]
        pinned_read(dict(path=value['vectors_path'],sha256=value['artifact_sha256'],bytes=Path(value['vectors_path']).stat().st_size))
        banks['spaces'][key]=copy.deepcopy(value)
    ids=[v['id']for v in banks['spaces'].values()]
    if len(ids)!=len(set(ids))or set(ids)!=set(expected_final_space_ids)or set(result['artifacts'])!=set(expected_final_artifact_ids):
        raise ValueError('exact final artifact/space IDs and counts must be frozen')
    if 'space_groups'in banks:
        banks.setdefault('space_group_history',[]).append(copy.deepcopy(banks['space_groups']))
        banks['space_groups']['registered_space_count']=len(ids)
        banks['space_groups']['additive_publication_spaces']=[v['id']for v in spaces.values()]
        banks['space_groups']['current_assay_space_count']=len(ids)-len(banks['space_groups'].get('legacy',[]))
        result['space_groups']=copy.deepcopy(banks['space_groups'])
    new_embedding_path=Path(new_embedding_path)
    if not new_embedding_path.is_absolute()or new_embedding_path.exists():raise ValueError('new versioned embedding index path required')
    bank_raw=P.encoded(banks);result['artifacts']['embedding_index']=P.pinned(new_embedding_path,bank_raw)
    result.setdefault('provenance',{})['consumer_registry_extension']=dict(previous_index=index_pin,previous_embedding_index=embedding_pin,existing_records_preserved=True)
    result['counts']['registered_embedding_spaces']=len(ids)
    if 'space_groups'in banks:result['counts']['current_assay_embedding_spaces']=banks['space_groups']['current_assay_space_count']
    result['previous_publication']=copy.deepcopy(index.get('publication',{}))
    result['publication']={'status':'pending-new-checked-head-ci-merge-metadata'}
    result['status']='prepared-additive-registry-not-published'
    return dict(index=result,embedding_index=banks,embedding_bytes=bank_raw,index_bytes=P.encoded(result),
                artifact_count=len(result['artifacts']),space_count=len(ids),publish_performed=False)
