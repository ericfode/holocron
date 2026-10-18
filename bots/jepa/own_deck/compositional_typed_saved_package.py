"""Byte-only failed-native plus completed saved-recovery evidence adapter.

Never parse the old truncated native receipt, run a scientific worker, or follow
historical source paths. The original full-six-stage packager stays unchanged.
"""
import argparse
import gzip
import json
import os
from pathlib import Path

import compositional_typed_package as P

SCHEMA='jepa-compositional-typed-saved-evidence/1'
NAMES=('compositional-typed-v1','compositional-typed-saved-v1')
OLD_STAGES=('metadata','build','native','prep','fit','verify')
NEW_STAGES=('recover','prep','fit','verify')


def load(path): return json.loads(P.read_limited(path,P.MAX_FILE))
def pin(path):
    value=P.transfer(path,'identity')
    return dict(path=str(path),sha256=value['raw_sha256'],bytes=value['raw_bytes'])


def history(root,failed,payloads=None):
    """Replay only the declared journal, not native/model outputs."""
    def raw(path):return P.read_limited(path,P.MAX_FILE)if payloads is None else payloads[str(path)]
    def pinned(path):
        value=raw(path);return dict(path=str(path),sha256=P.digest(value),bytes=len(value))
    spec=json.loads(raw(root/'campaign-spec.json'));parent=json.loads(raw(root/'parent-manifest.json'));closure=json.loads(raw(root/'experiment-closure.json'))
    stages=OLD_STAGES if failed else NEW_STAGES;commit=spec['source_freeze_commit']
    P.require(len(commit)==40 and all(c in'0123456789abcdef'for c in commit),'exact source commit required')
    P.require(spec['schema']=='jepa-sealed-budget-spec/1'and tuple(spec['stage_order'])==stages and
        spec['ledger_path']==str(root/'campaign-ledger.jsonl')and spec['parent_manifest']==pinned(root/'parent-manifest.json'),
        'exact root/spec/parent route required')
    rows=[json.loads(line)for line in raw(root/'campaign-ledger.jsonl').splitlines()if line.strip()]
    keys=set(spec['caps'])-{'seconds'};charged={k:0 for k in spec['caps']};observed={k:0 for k in keys}
    previous='0'*64;finished=[];statuses=[];pending=None;in_root_pins=[]
    for sequence,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'};d=row['data'];event=row['event']
        P.require(row['schema']=='jepa-sealed-budget-journal/1'and row['sequence']==sequence and
            row['previous_sha256']==previous and P.digest(P.canonical(body))==row['record_sha256'],'journal chain differs')
        previous=row['record_sha256']
        if event=='initialized':
            P.require(sequence==0 and d==dict(spec=pinned(root/'campaign-spec.json')),'exact initialized spec pin required')
        elif event=='begin':
            P.require(sequence>0 and pending is None and 'failed'not in statuses and len(finished)<len(stages)and
                d['stage']==stages[len(finished)]and d['argv']==spec['stages'][d['stage']]['argv']and d['guard']==spec['guard'],
                'once-only ordered stage command/guard required')
            P.require(all(charged[k]+spec['stages'][d['stage']]['reservation'][k]<=spec['caps'][k]for k in charged),'reservation exceeds sealed cap')
            pending=dict(stage=d['stage'],open={},intents={k:0 for k in keys},done={k:0 for k in keys})
            in_root_pins.extend(d.get('inputs',[]))
        elif event=='intent':
            P.require(pending is not None and d['token']==sequence and d['counter']in keys and
                P.number(d['amount'])and d['amount']>0,'invalid durable intent')
            k=d['counter'];pending['intents'][k]+=d['amount']
            P.require(pending['intents'][k]<=spec['stages'][pending['stage']]['reservation'][k],'intent exceeds reservation')
            pending['open'][d['token']]=(k,d['amount'])
        elif event=='complete':
            P.require(pending is not None and d['token']in pending['open'],'completion needs durable intent')
            k,n=pending['open'].pop(d['token']);external=k in spec['stages'][pending['stage']]['external_counters'];actual=d['actual']
            P.require((external and P.number(actual)and actual<=n and len({p['path']for p in d['proofs']})>=2)or
                (not external and actual is None and not d['proofs']),'external/ordinary completion differs')
            pending['done'][k]+=actual if external else n;in_root_pins.extend(d['proofs'])
        elif event=='finish':
            P.require(pending is not None and d['status']in('completed','failed')and d['cleanup_verified']is True and
                d['execution_ended']is True and P.number(d['seconds']),'known ended stage required')
            stage=spec['stages'][pending['stage']];bad=d['status']=='failed'
            P.require(bad or(not pending['open']and d['seconds']<=stage['reservation']['seconds']and
                all(v is None or pending['done'][k]==v for k,v in stage['expected'].items())),'completed quota/time differs')
            expected={k:max(stage['reservation'][k],pending['intents'][k])if bad else pending['done'][k]for k in keys}
            expected['seconds']=max(stage['reservation']['seconds'],d['seconds'])if bad else d['seconds']
            P.require(d['charged']==expected and d['durable_intents']==pending['intents']and
                d['durable_completed']==pending['done'],'failed reservations/durable counts rewritten')
            for k,v in expected.items():charged[k]+=v
            for k in keys:observed[k]=None if bad and stage['reservation'][k]else None if observed[k]is None else observed[k]+pending['done'][k]
            finished.append(pending['stage']);statuses.append(d['status']);in_root_pins.extend(d['proofs']);pending=None
        else:raise ValueError('unclosed/unreviewed journal event')
    P.require(rows and pending is None and rows[-1]['event']=='finish','closed ledger required')
    expected_stages=list(OLD_STAGES[:3])if failed else list(NEW_STAGES)
    P.require(finished==expected_stages and statuses==(['completed','completed','failed']if failed else['completed']*4),
        'failed native history and completed recovery must remain separate')
    if failed:P.require(charged['native_applies']==512 and observed['native_applies']is None and
        all(charged[k]==0 for k in('neural_forwards','backwards','optimizer_updates','numerical_fits')),'original failed native reservation/exposure differs')
    else:P.require(charged['native_applies']==0 and observed['native_applies']==0 and
        all(spec['stages'][s]['reservation']['native_applies']==0 for s in stages),'saved recovery cannot authorize native calls')
    P.require(closure['journal']==pinned(root/'campaign-ledger.jsonl')and closure['final_chain']==previous and
        closure['new_charged']==charged and closure['new_observed']==observed and
        closure['source_freeze_commit']==commit,'closure/ledger/pin disagreement')
    carry=parent['carry'];cumulative=dict(charged_native_applies=carry['charged_native_applies']+charged['native_applies'],
        charged_seconds=carry['charged_seconds']+charged['seconds'],observed_native_applies=None if
        carry['observed_native_applies']is None or observed['native_applies']is None else carry['observed_native_applies']+observed['native_applies'])
    P.require(closure['cumulative']==cumulative and charged['paid_jobs']==charged['paid_spend_usd']==0,'cumulative/financial history differs')
    return dict(source_freeze_commit=commit,records=len(rows),final_chain=previous,stages=finished,statuses=statuses,
        charged=charged,observed=observed,cumulative=cumulative,closure_pin=pinned(root/'experiment-closure.json'),
        ledger_pin=pinned(root/'campaign-ledger.jsonl'),spec_pin=pinned(root/'campaign-spec.json')),spec,parent,closure,in_root_pins


def declared_pins(value):
    if isinstance(value,dict):
        if {'path','sha256','bytes'}<=value.keys():yield {k:value[k]for k in('path','sha256','bytes')}
        for child in value.values():yield from declared_pins(child)
    elif isinstance(value,list):
        for child in value:yield from declared_pins(child)


def inventory(old,new):
    roots=(old,new);histories=[];all_pins=[];specs=[];parents=[];closures=[]
    for root,failed in zip(roots,(True,False)):
        h,s,p,c,pins=history(root,failed);histories.append(h);specs.append(s);parents.append(p);closures.append(c)
        all_pins.extend(pins+list(declared_pins([s,p,c]))+[h['ledger_pin'],h['closure_pin']])
    P.require(parents[1]['carry']==histories[0]['cumulative'],'new cycle must retain the failed native carry')
    parent_pins=parents[1].get('pins',[])
    P.require(histories[0]['ledger_pin']in parent_pins and histories[0]['closure_pin']in parent_pins,'new parent must pin old failed ledger and closure')
    files=[];excluded=[]
    for root in roots:
        for path in sorted(root.rglob('*')):
            relative=path.relative_to(root).as_posix();P.safe_name(relative)
            P.require(not path.is_symlink(),'campaign symlink forbidden')
            if '__pycache__'in path.parts:continue
            if not path.is_file():continue
            if relative==P.BINARY:
                excluded.append(dict(provenance=dict(original_path=str(path)),campaign=root.name,relative_path=relative,reason='compiled binary excluded; pin retained',**P.transfer(path,'identity')));continue
            P.require(path.suffix in P.EXTENSIONS,'unreviewed campaign file: '+relative)
            encoding='gzip'if path.suffix in P.TEXT else'identity'
            files.append(dict(url='payload/'+root.name+'/'+relative+('.gz'if encoding=='gzip'else''),
                provenance=dict(original_path=str(path),campaign=root.name,relative_path=relative),**P.transfer(path,encoding)))
            P.check_entries(files)
    mapping={e['provenance']['original_path']:e for e in files+excluded};verified=0;opaque=0
    for expected in all_pins:
        path=Path(expected['path'])
        if any(path.is_relative_to(root)for root in roots):
            actual=mapping.get(str(path));P.require(actual is not None and expected['sha256']==actual['raw_sha256']and
                expected['bytes']==actual['raw_bytes'],'in-campaign pin differs: '+str(path));verified+=1
        else:opaque+=1
    # Do not JSON-decode the partial receipt, including during pin verification.
    partial=closures[0]['partial_receipt'];actual=mapping.get(partial['path'])
    P.require(actual is not None and actual['raw_sha256']==partial['sha256']and actual['raw_bytes']==partial['bytes'],'opaque partial receipt pin differs')
    required=('recover-1','prep-1','fit-1','verify-1')
    P.require(all(any(e['provenance']['campaign']==new.name and e['provenance']['relative_path'].startswith(stage+'/')for e in files)
                  for stage in required),'all successful recovery stage outputs required')
    return dict(schema=P.SCHEMA,adapter_schema=SCHEMA,limits=P.LIMITS,files=files,excluded=excluded,
        source_freeze_commit=histories[1]['source_freeze_commit'],source_freeze_commits={r.name:h['source_freeze_commit']for r,h in zip(roots,histories)},
        histories={r.name:h for r,h in zip(roots,histories)},pin_checks=dict(in_campaign_verified=verified,historical_outside_campaign_opaque=opaque),
        original_partial_receipt=dict(partial,handling='Opaque original bytes; intentionally never parsed or repaired'),
        fixture_evidence_scope='Recovered cases come from journalled native before/after/contextComplete records. Complete pre-apply fixture validation is control-flow inference from frozen source, not fabricated observed fixtureValidation records.',
        packager_source=dict(provenance=dict(original_path=str(Path(__file__).resolve())),**P.transfer(Path(__file__).resolve(),'identity')),
        shared_byte_primitives=dict(provenance=dict(original_path=str(Path(P.__file__).resolve())),**P.transfer(Path(P.__file__).resolve(),'identity')),
        semantic_validated=False,scope='Failed native attempt retained with full charges and unknown official exposure; subsequent saved-data recovery is separately completed. Byte packaging performs no science.')


def documents(plan):
    index=dict(schema=SCHEMA,manifest='manifest.json',artifacts=plan['files'],histories=plan['histories'],
        source_freeze_commits=plan['source_freeze_commits'],semantic_validated=False)
    raw=P.encode(index);P.require(len(raw)<=P.MAX_MANIFEST,'index metadata limit')
    manifest=dict(plan,files=plan['files']+[dict(url='index.json',encoding='identity',sha256=P.digest(raw),bytes=len(raw),raw_sha256=P.digest(raw),raw_bytes=len(raw))])
    encoded=P.encode(manifest);P.require(len(encoded)<=P.MAX_MANIFEST,'manifest limit');P.check_entries(manifest['files'],len(encoded))
    return raw,encoded


def prepare(old,new,out):
    P.require(not any(Path(p).is_symlink()for p in(old,new,out)),'root/destination symlink forbidden')
    old,new=Path(old).resolve(strict=True),Path(new).resolve(strict=True);out=Path(out).resolve()
    P.require((old.name,new.name)==NAMES and old!=new and not out.exists()and
        all(not out.is_relative_to(r)and not r.is_relative_to(out)for r in(old,new)),'exact two roots and exclusive outside destination required')
    plan=inventory(old,new);documents(plan);return plan


def build(old,new,out):
    plan=prepare(old,new,out);index,manifest=documents(plan);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    for entry in plan['files']:
        path=out/entry['url'];path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as stream:
            actual=P.transfer(Path(entry['provenance']['original_path']),entry['encoding'],stream);stream.flush();os.fsync(stream.fileno())
        P.require(all(actual[k]==entry[k]for k in actual),'source changed during copying')
    P.require(inventory(Path(old).resolve(),Path(new).resolve())==plan,'source membership/content changed during copying')
    for name,raw in(('index.json',index),('manifest.json',manifest)):
        with(out/name).open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return verify(out)


def verify(out,expected_manifest_sha=None):
    result=P.verify(out,expected_manifest_sha);m=json.loads(P.read_limited(Path(out)/'manifest.json',P.MAX_MANIFEST))
    P.require(m.get('adapter_schema')==SCHEMA and set(m['histories'])==set(NAMES)and
        m['histories'][NAMES[0]]['statuses']==['completed','completed','failed']and
        m['histories'][NAMES[1]]['statuses']==['completed']*4 and
        m['histories'][NAMES[0]]['charged']['native_applies']==512 and
        m['histories'][NAMES[0]]['observed']['native_applies']is None and
        m['histories'][NAMES[1]]['charged']['native_applies']==0,'failure/recovery distinction missing')
    # Decode only four bounded accounting documents per root, never the partial
    # native receipt or numerical payloads; historical provenance is not opened.
    payloads={};parents={}
    for name,h in m['histories'].items():
        root=Path(h['spec_pin']['path']).parent
        for relative in('campaign-spec.json','parent-manifest.json','campaign-ledger.jsonl','experiment-closure.json'):
            entry=next(e for e in m['files']if e.get('provenance',{}).get('original_path')==str(root/relative))
            path=Path(out)/entry['url']
            with(gzip.open(path,'rb')if entry['encoding']=='gzip'else path.open('rb'))as stream:
                payloads[str(root/relative)]=stream.read(entry['raw_bytes']+1)
            P.require(len(payloads[str(root/relative)])==entry['raw_bytes'],'accounting payload size differs')
        replay,_,parent,_,_=history(root,name==NAMES[0],payloads);parents[name]=parent
        P.require(replay==h and m['source_freeze_commits'][name]==h['source_freeze_commit'],'packaged history/source replay differs')
    old=m['histories'][NAMES[0]];new_parent=parents[NAMES[1]]
    P.require(new_parent['carry']==old['cumulative']and old['ledger_pin']in new_parent['pins']and
        old['closure_pin']in new_parent['pins'],'packaged parent carry/pins differ')
    return dict(result,adapter_schema=SCHEMA,source_freeze_commits=m['source_freeze_commits'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group()
    g.add_argument('--prepare',action='store_true');g.add_argument('--build',action='store_true');g.add_argument('--verify',action='store_true')
    parser.add_argument('--old',type=Path);parser.add_argument('--new',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--expected-manifest-sha');a=parser.parse_args()
    if a.verify:value=verify(a.out,a.expected_manifest_sha)
    else:P.require(a.old is not None and a.new is not None,'both roots required');value=(build if a.build else prepare)(a.old,a.new,a.out)
    print(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))


if __name__=='__main__':main()
