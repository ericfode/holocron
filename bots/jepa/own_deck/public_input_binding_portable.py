"""Versioned publication wrapper with explicit immutable historical-reference pins.

The original portable builder and all scientific records remain unchanged.
Only exact declared (absolute path, SHA256, bytes) triples can resolve to an
explicit archived payload. Unmapped references use the original strict check.
"""
import argparse
import gzip
import json
from pathlib import Path
import re

import publication_portable as B
import publication_checkpoint as P

SCHEMA='jepa-historical-publication-reference-map/1'
BASE_CLOSURE=B.Closure
ORIGINAL_PACKAGE_BYTES=512*1024*1024
PACKAGE_BYTES=1024*1024*1024
PACKAGE_FILES=4000


def file_pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),sha256=P.digest(raw),bytes=len(raw))


def exact_key(pin):
    if not isinstance(pin.get('path'),str)or not Path(pin['path']).is_absolute():raise ValueError('absolute declared historical path required')
    if not re.fullmatch(r'[0-9a-f]{64}',str(pin.get('sha256'))):raise ValueError('historical SHA256 required')
    if type(pin.get('bytes'))is not int or pin['bytes']<0:raise ValueError('historical byte count required')
    return(str(Path(pin['path']).resolve()),pin['sha256'],pin['bytes'])


class HistoricalClosure(BASE_CLOSURE):
    def __init__(self,stage,mapping,**kwargs):
        if any(key not in('max_bytes','max_files')for key in kwargs)or kwargs.get('max_bytes',PACKAGE_BYTES)!=PACKAGE_BYTES or kwargs.get('max_files',PACKAGE_FILES)!=PACKAGE_FILES:
            raise ValueError('fixed publication-only1GiB/4000file bounds required')
        super().__init__(stage,max_bytes=PACKAGE_BYTES,max_files=PACKAGE_FILES)
        self.mapping_pin=file_pin(mapping);self.mapping=json.loads(Path(mapping).read_bytes())
        if self.mapping.get('schema')!=SCHEMA:raise ValueError('historical mapping schema differs')
        self.historical={};self.historical_reads={};self.archive_pins={}
        for item in self.mapping['entries']:
            key=exact_key(item['declared']);archive=item['archive'];exact_key(archive)
            if key in self.historical:raise ValueError('duplicate historical declared reference')
            if item.get('encoding','identity')not in('identity','gzip'):raise ValueError('unsupported historical encoding')
            self.historical[key]=item
        for pin in self.mapping.get('authority_pins',[]):
            exact_key(pin)
            if file_pin(pin['path'])!=pin:raise ValueError('historical mapping authority changed')
            self.archive_pins[pin['path']]=pin

    def data_pin(self,record,origin):
        source=self.original_path(record['path'],origin)
        key=(str(source),record.get('sha256'),record.get('bytes'))
        item=self.historical.get(key)
        if item is None:return super().data_pin(record,origin)
        archive=item['archive'];actual=file_pin(archive['path'])
        if actual!=archive:raise ValueError('historical archived payload pin mismatch')
        raw=Path(archive['path']).read_bytes()
        decoded=gzip.decompress(raw)if item.get('encoding')=='gzip'else raw
        if P.digest(decoded)!=key[1]or len(decoded)!=key[2]:raise ValueError('historical decoded payload does not match declared reference')
        self.archive_pins[archive['path']]=archive
        self.historical_reads[key]=dict(declared=item['declared'],archive=archive,encoding=item.get('encoding','identity'),
            authority=item.get('authority'),resolution='exact archived bytes; original logical path retained for relative-reference semantics')
        # Keep the original logical origin, including its suffix and relative
        # reference scope. Never read the later host file for a mapped key.
        return source,decoded

    def verify_sources_unchanged(self):
        count=super().verify_sources_unchanged()
        if file_pin(self.mapping_pin['path'])!=self.mapping_pin:raise ValueError('historical mapping changed')
        for pin in self.archive_pins.values():
            if file_pin(pin['path'])!=pin:raise ValueError('historical archive changed')
        return count+len(self.archive_pins)+1

    def store(self,relative,raw):
        if relative=='manifest.json':
            value=P.read_json(raw)
            mapping_raw=Path(self.mapping_pin['path']).read_bytes();wrapper_pin=file_pin(__file__);wrapper_raw=Path(__file__).read_bytes()
            mapping_copy=super().store('provenance/raw/historical-map-'+self.mapping_pin['sha256']+'.json',mapping_raw)
            wrapper_copy=super().store('provenance/raw/historical-wrapper-'+wrapper_pin['sha256']+'.py',wrapper_raw)
            value.setdefault('provenance',{})['historical_reference_resolution']=dict(mapping=self.mapping_pin,mapping_raw_download=mapping_copy,
                wrapper_source=wrapper_pin,wrapper_raw_download=wrapper_copy,resolutions=list(self.historical_reads.values()),
                policy='Only exact declared path+sha256+bytes mapping; no hash bypass, search or current-host fallback.')
            bounds=dict(original_byte_ceiling=ORIGINAL_PACKAGE_BYTES,authorized_byte_ceiling=PACKAGE_BYTES,file_ceiling=PACKAGE_FILES,
                final_measured_payload_bytes=0,scope='Local artifact copies including manifest; checksum self-file and ZIP excluded as in original builder. Scientific, analysis and paid-compute caps unchanged.')
            value['provenance']['local_artifact_copy_bound']=bounds
            for _ in range(8):
                measured=self.total_bytes+len(P.encoded(value))
                if measured==bounds['final_measured_payload_bytes']:break
                bounds['final_measured_payload_bytes']=measured
            else:raise ValueError('manifest byte measurement failed to stabilize')
            raw=P.encoded(value)
        return super().store(relative,raw)


def check_references(value,origin,bundle):
    if isinstance(value,list):
        for child in value:check_references(child,origin,bundle)
    elif isinstance(value,dict):
        if isinstance(value.get('url'),str):
            target=B.resolve_url(bundle,origin,value['url']);raw=target.read_bytes()
            if P.digest(raw)!=value['sha256']or len(raw)!=value['bytes']:raise ValueError('relative URL pin mismatch')
        for key,child in value.items():
            if key in('provenance','provenance_only'):continue
            if key in('vectors_url','manifest_url'):
                target=B.resolve_url(bundle,origin,child);raw=target.read_bytes();sha_key='artifact_sha256'if key=='vectors_url'else'manifest_sha256'
                if P.digest(raw)!=value[sha_key]or len(raw)!=value[key+'_bytes']:raise ValueError('paired URL pin mismatch')
            elif key!='url':check_references(child,origin,bundle)
    elif isinstance(value,str)and(B.LOCAL.search(value)or value.startswith('file:')):raise ValueError('UI host path escaped provenance')


def preflight(index,mapping,out,expected_space_ids):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('new immutable preflight directory required')
    out.mkdir(parents=True);closure=HistoricalClosure(out,mapping)
    pin=file_pin(index);root=closure.copy(pin,index,'research-index.json');value=closure.values[root['url']]
    entry=value['artifacts']['embedding_index'];embedding=closure.values['assets/'+Path(entry['url']).name]
    selected=B.select_vector_spaces(value['artifacts'],embedding,expected_artifact_count=54,expected_space_count=18,
        all_registered_spaces=True,expected_space_ids=expected_space_ids)
    for name,value in closure.values.items():check_references(value,out/name,out)
    for record in closure.records.values():
        raw=(out/record['url']).read_bytes()
        if P.digest(raw)!=record['sha256']or len(raw)!=record['bytes']:raise ValueError('preflight stored bytes differ')
    count=closure.verify_sources_unchanged()
    result=dict(schema='jepa-public-input-portable-preflight/1',status='PASS',publication_status='pending-real-ci-merge',
        index=pin,historical_mapping=closure.mapping_pin,historical_resolutions=list(closure.historical_reads.values()),
        artifacts=54,spaces=18,selected_spaces=selected,portable_files=len(closure.records),portable_bytes=closure.total_bytes,
        original_source_pins_rechecked=count,semantic_validated=False,stable_pointer_writes=0,neural_forwards=0,native_applies=0,optimizer_updates=0,numerical_fits=0)
    result['local_artifact_copy_bound']=dict(original_byte_ceiling=ORIGINAL_PACKAGE_BYTES,authorized_byte_ceiling=PACKAGE_BYTES,file_ceiling=PACKAGE_FILES,
        final_measured_payload_bytes=closure.total_bytes,scope='Local artifact copies before preflight receipt only; scientific, analysis and paid-compute caps unchanged.')
    P._write_exclusive(out/'preflight.json',P.encoded(result));return result


def build(pointer,mapping,out,expected_space_ids):
    """Reuse the unchanged final builder after real CI/merge pointer verification."""
    created=[]
    def factory(stage,**kwargs):
        closure=HistoricalClosure(stage,mapping,**kwargs);created.append(closure);return closure
    original=B.Closure;B.Closure=factory
    try:result=B.build(pointer,out,expected_artifact_count=54,expected_space_count=18,all_registered_spaces=True,expected_space_ids=expected_space_ids)
    finally:B.Closure=original
    result['historical_mapping']=file_pin(mapping);result['historical_reference_resolutions']=[r for c in created for r in c.historical_reads.values()]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('preflight','build'))
    parser.add_argument('--index',type=Path);parser.add_argument('--pointer',type=Path);parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--space-manifest',type=Path,required=True)
    args=parser.parse_args();ids=P.read_json(args.space_manifest.read_bytes())['expected_final_space_ids']
    result=preflight(args.index,args.mapping,args.out,ids)if args.mode=='preflight'else build(args.pointer,args.mapping,args.out,ids)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
