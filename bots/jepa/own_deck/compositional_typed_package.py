"""Bounded byte-only packet for a COMPLETED compositional-typed campaign.

Default CLI preparation writes nothing. Build is explicit and exclusive. Offline
verification never opens provenance paths or imports numerical/model libraries.
Historical source/pin lists are opaque metadata, not recursively copied inputs.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath

MAX_FILE=64*1024**2;MAX_TOTAL=256*1024**2;MAX_FILES=1000;MAX_MANIFEST=4*1024**2;CHUNK=1024**2
LIMITS=dict(file_bytes=MAX_FILE,total_raw_bytes=MAX_TOTAL,total_stored_bytes=MAX_TOTAL,files=MAX_FILES,manifest_bytes=MAX_MANIFEST)
STAGES=('metadata','build','native','prep','fit','verify')
TEXT={'.json','.jsonl','.log','.txt'};EXTENSIONS=TEXT|{'.npz'}
BINARY='build-1/compositional-typed-native-collector'
SCHEMA='jepa-compositional-typed-evidence/1'


def require(value,message):
    if not value:raise ValueError(message)
def encode(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(value):return hashlib.sha256(value).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read_limited(path,limit):
    require(path.stat().st_size<=limit,'file exceeds declared limit: '+str(path))
    with path.open('rb')as f:raw=f.read(limit+1)
    require(len(raw)<=limit,'file grew beyond limit');return raw
def number(value):return type(value)in(int,float)and math.isfinite(value)and value>=0
def sha(value):return type(value)is str and len(value)==64 and all(c in'0123456789abcdef'for c in value)
def safe_name(name):
    require(type(name)is str and name and '\\'not in name and ':'not in name and all(ord(c)>=32 for c in name),'invalid relative URL')
    p=PurePosixPath(name);require(not p.is_absolute()and p.as_posix()==name and not set(p.parts)&{'.','..'},'path traversal/normalization rejected');return name


class Sink:
    def __init__(self,stream=None):self.stream=stream;self.hash=hashlib.sha256();self.count=0
    def write(self,data):
        self.count+=len(data);require(self.count<=MAX_FILE,'stored file exceeds64MiB');self.hash.update(data)
        if self.stream is not None:self.stream.write(data)
        return len(data)
    def flush(self):
        if self.stream is not None:self.stream.flush()


def transfer(source,encoding,stream=None):
    """Incremental original+stored pins; gzip has fixed mtime and no filename."""
    require(not source.is_symlink()and source.is_file()and source.stat().st_size<=MAX_FILE,'invalid/oversize source')
    raw_hash=hashlib.sha256();size=0;sink=Sink(stream)
    compressed=gzip.GzipFile(filename='',mode='wb',compresslevel=9,mtime=0,fileobj=sink)if encoding=='gzip'else None
    with source.open('rb')as f:
        while True:
            block=f.read(min(CHUNK,MAX_FILE-size+1))
            if not block:break
            size+=len(block);require(size<=MAX_FILE,'raw file grew beyond64MiB');raw_hash.update(block)
            (compressed if compressed is not None else sink).write(block)
    if compressed is not None:compressed.close()
    sink.flush();return dict(raw_sha256=raw_hash.hexdigest(),raw_bytes=size,sha256=sink.hash.hexdigest(),bytes=sink.count,encoding=encoding)


def closed(campaign,commit):
    require(type(commit)is str and len(commit)==40 and all(c in'0123456789abcdef'for c in commit),'exact source-freeze40SHA required')
    spec=json.loads(read_limited(campaign/'campaign-spec.json',MAX_FILE))
    require(spec['schema']=='jepa-sealed-budget-spec/1'and spec['source_freeze_commit']==commit and tuple(spec['stage_order'])==STAGES,'frozen campaign/source mismatch')
    require(spec['ledger_path']==str(campaign/'campaign-ledger.jsonl'),'canonical closed ledger required')
    parent=campaign/'parent-manifest.json';raw=read_limited(parent,MAX_FILE);p=spec['parent_manifest']
    require(p==dict(path=str(parent),sha256=digest(raw),bytes=len(raw)),'exact parent metadata pin required')
    rows=[json.loads(v)for v in read_limited(campaign/'campaign-ledger.jsonl',MAX_FILE).splitlines()if v.strip()]
    require(rows and rows[0]['event']=='initialized','once-only initialization required')
    previous='0'*64;finished=[];pending=None
    for sequence,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'};d=row['data'];event=row['event']
        require(row['schema']=='jepa-sealed-budget-journal/1'and row['sequence']==sequence and row['previous_sha256']==previous and digest(canonical(body))==row['record_sha256'],'damaged closed journal')
        previous=row['record_sha256']
        if event=='initialized':require(sequence==0 and d['spec']==dict(path=str(campaign/'campaign-spec.json'),sha256=digest(read_limited(campaign/'campaign-spec.json',MAX_FILE)),bytes=(campaign/'campaign-spec.json').stat().st_size),'wrong initialization pin')
        elif event=='begin':
            require(pending is None and len(finished)<len(STAGES)and d['stage']==STAGES[len(finished)]and d['argv']==spec['stages'][d['stage']]['argv']and d['guard']==spec['guard'],'incorrect stage order/command')
            pending=dict(stage=d['stage'],open={},done={k:0 for k in spec['stages'][d['stage']]['expected']})
        elif event=='intent':
            require(pending is not None and d['token']==sequence and d['counter']in pending['done']and number(d['amount'])and d['amount']>0,'invalid intent');pending['open'][d['token']]=(d['counter'],d['amount'])
        elif event=='complete':
            require(pending is not None and d['token']in pending['open'],'completion without intent');k,n=pending['open'].pop(d['token']);actual=d['actual']
            require(actual is None or(k in spec['stages'][pending['stage']]['external_counters']and number(actual)and actual<=n),'unreviewed partial completion');pending['done'][k]+=n if actual is None else actual
        elif event=='finish':
            require(pending is not None and d['status']=='completed'and d['cleanup_verified']is True and d['execution_ended']is True and not pending['open'],'failed/pending stage cannot be packaged')
            stage=spec['stages'][pending['stage']]
            require(all((v is None or pending['done'][k]==v)and d['charged'][k]==pending['done'][k]for k,v in stage['expected'].items())and number(d['seconds'])and d['seconds']<=stage['reservation']['seconds'],'completed counters/time mismatch')
            finished.append(pending['stage']);pending=None
        else:raise ValueError('unclosed/unreviewed journal event')
    require(finished==list(STAGES)and pending is None and rows[-1]['event']=='finish','all six stages must be closed completed')
    return spec,dict(records=len(rows),final_chain=previous,completed_stages=finished)


def selected(campaign):
    required={'campaign-spec.json','parent-manifest.json','campaign-ledger.jsonl','metadata-1/native-plan.json','native-1/receipt.json','native-1/transitions.jsonl','prep-1/dataset.npz','prep-1/manifest.json','fit-1/result.json'}
    required|={s+'-1-stage-receipt.json'for s in STAGES};found={};excluded=[]
    for path in sorted(campaign.rglob('*')):
        relative=path.relative_to(campaign).as_posix();parts=PurePosixPath(relative).parts
        require(not path.is_symlink(),'campaign symlink forbidden: '+relative)
        if not path.is_file():continue
        if relative==BINARY:
            excluded.append(dict(relative_path=relative,reason='compiled binary excluded; byte pin only',**transfer(path,'identity')));continue
        top=len(parts)==1 and(relative in required or relative=='experiment-closure.json')
        stage=len(parts)>=2 and parts[0]in{s+'-1'for s in STAGES}
        require(top or stage,'unexpected campaign file: '+relative)
        require(path.suffix in EXTENSIONS,'unreviewed file type: '+relative)
        found[relative]=path;require(len(found)<=MAX_FILES-2,'file-count limit exceeded')
    require(required<=set(found),'missing required campaign artifacts: '+str(sorted(required-set(found))))
    require(any(n.startswith('verify-1/')and n.endswith('.json')for n in found),'saved independent verification output required')
    return found,excluded


def check_entries(entries,manifest_size=0):
    require(type(entries)is list and len(entries)+1<=MAX_FILES,'1000-file limit')
    for e in entries:
        safe_name(e['url']);require(e['encoding']in('identity','gzip')and sha(e['sha256'])and sha(e['raw_sha256']),'invalid stored/decoded pin')
        require(all(type(e[k])is int and 0<=e[k]<=MAX_FILE for k in('bytes','raw_bytes')),'64MiB/file limit')
    require(sum(e['bytes']for e in entries)+manifest_size<=MAX_TOTAL and sum(e['raw_bytes']for e in entries)+manifest_size<=MAX_TOTAL,'256MiB total limit')


def inventory(campaign,commit):
    require(not Path(campaign).is_symlink(),'campaign root symlink forbidden');campaign=Path(campaign).resolve(strict=True)
    spec,closure=closed(campaign,commit);files,excluded=selected(campaign);entries=[]
    for name,path in files.items():
        encoding='gzip'if path.suffix in TEXT else'identity'
        entries.append(dict(url='payload/'+name+('.gz'if encoding=='gzip'else''),provenance=dict(original_path=str(path)),**transfer(path,encoding)))
        check_entries(entries)
    return dict(schema=SCHEMA,limits=LIMITS,files=entries,excluded=excluded,closed_journal=closure,source_freeze_commit=commit,
        packager_source=dict(provenance=dict(original_path=str(Path(__file__).resolve())),**transfer(Path(__file__).resolve(),'identity')),
        source_pin_scope='Frozen source pins and historical paths remain opaque provenance in campaign spec/parent metadata; no recursive fetching.',
        semantic_validated=False,scope='Byte-only evidence packet, not an engine/model/evaluation execution.')


def documents(plan,source_freeze_commit):
    index=dict(schema=SCHEMA,manifest='manifest.json',source_freeze_commit=source_freeze_commit,artifacts=plan['files'],semantic_validated=False)
    index_raw=encode(index);require(len(index_raw)<=MAX_MANIFEST,'index metadata limit')
    manifest=dict(plan,files=plan['files']+[dict(url='index.json',encoding='identity',sha256=digest(index_raw),bytes=len(index_raw),raw_sha256=digest(index_raw),raw_bytes=len(index_raw))])
    manifest_raw=encode(manifest);require(len(manifest_raw)<=MAX_MANIFEST,'4MiB manifest limit');check_entries(manifest['files'],len(manifest_raw))
    return index_raw,manifest_raw


def prepare(campaign,out,source_freeze_commit):
    require(not Path(campaign).is_symlink()and not Path(out).is_symlink(),'campaign/destination symlink forbidden')
    campaign=Path(campaign).resolve(strict=True);out=Path(out).resolve()
    require(not out.exists()and not out.is_symlink()and not out.is_relative_to(campaign)and not campaign.is_relative_to(out),'exclusive NEW destination outside campaign required')
    plan=inventory(campaign,source_freeze_commit);documents(plan,source_freeze_commit);return plan


def build(campaign,out,source_freeze_commit):
    plan=prepare(campaign,out,source_freeze_commit);index_raw,manifest_raw=documents(plan,source_freeze_commit);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    for entry in plan['files']:
        target=out/entry['url'];target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as f:
            actual=transfer(Path(entry['provenance']['original_path']),entry['encoding'],f);f.flush();os.fsync(f.fileno())
        require(all(actual[k]==entry[k]for k in actual),'source changed during byte copy')
    require(inventory(campaign,source_freeze_commit)==plan,'campaign membership/content changed during packaging')
    for name,raw in(('index.json',index_raw),('manifest.json',manifest_raw)):
        with(out/name).open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return verify(out)


def verify_payload(path,entry):
    require(not path.is_symlink()and path.stat().st_size==entry['bytes'],'stored size/symlink mismatch');h=hashlib.sha256();count=0
    with path.open('rb')as f:
        while True:
            block=f.read(min(CHUNK,entry['bytes']-count+1))
            if not block:break
            count+=len(block);require(count<=entry['bytes'],'stored bytes exceeded declaration');h.update(block)
    require(count==entry['bytes']and h.hexdigest()==entry['sha256'],'stored SHA/bytes mismatch');h=hashlib.sha256();count=0
    try:
        with path.open('rb')as f:
            stream=gzip.GzipFile(fileobj=f,mode='rb')if entry['encoding']=='gzip'else f
            try:
                while True:
                    block=stream.read(min(CHUNK,entry['raw_bytes']-count+1))
                    if not block:break
                    count+=len(block);require(count<=entry['raw_bytes'],'decoded bytes exceeded declaration');h.update(block)
            finally:
                if stream is not f:stream.close()
    except (EOFError,OSError)as error:raise ValueError('truncated/invalid gzip')from error
    require(count==entry['raw_bytes']and h.hexdigest()==entry['raw_sha256'],'decoded SHA/bytes mismatch')


def verify(out,expected_manifest_sha=None):
    out=Path(out);require(not out.is_symlink()and not(out/'manifest.json').is_symlink(),'packet symlink forbidden');out=out.resolve(strict=True);raw=read_limited(out/'manifest.json',MAX_MANIFEST)
    if expected_manifest_sha is not None:require(digest(raw)==expected_manifest_sha,'manifest pin mismatch')
    m=json.loads(raw);require(m['schema']==SCHEMA and m['limits']==LIMITS,'packet schema/limits mismatch');check_entries(m['files'],len(raw));expected={'manifest.json'}
    for e in m['files']:
        name=safe_name(e['url']);require(name not in expected,'duplicate payload');expected.add(name);path=out/name
        parts=PurePosixPath(name).parts
        require(path.resolve().is_relative_to(out)and not any(out.joinpath(*parts[:i]).is_symlink()for i in range(1,len(parts)+1)),'packet path escapes through symlink');verify_payload(path,e)
    actual=set()
    for p in out.rglob('*'):
        require(not p.is_symlink(),'packet symlink forbidden')
        if p.is_file():actual.add(p.relative_to(out).as_posix())
    require(actual==expected,'packet membership mismatch')
    return dict(status='verified-bytes-only',manifest_sha256=digest(raw),files=len(actual),raw_bytes=sum(e['raw_bytes']for e in m['files'])+len(raw),stored_bytes=sum(e['bytes']for e in m['files'])+len(raw),source_freeze_commit=m['source_freeze_commit'],semantic_validated=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--prepare',action='store_true');g.add_argument('--build',action='store_true');g.add_argument('--verify',action='store_true');p.add_argument('--campaign',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-freeze-commit');p.add_argument('--expected-manifest-sha');a=p.parse_args()
    if a.verify:value=verify(a.out,a.expected_manifest_sha)
    else:require(a.campaign is not None and a.source_freeze_commit is not None,'campaign/source freeze required');value=(build if a.build else prepare)(a.campaign,a.out,a.source_freeze_commit)
    print(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))
if __name__=='__main__':main()
