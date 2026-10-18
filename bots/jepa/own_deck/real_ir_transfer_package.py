"""Bounded byte-only real-IR evidence; no scientific imports or publication.

Prepare is read-only and requires all four explicit campaigns already closed.
Build writes one exclusive new directory. Offline verify never fetches original
paths or the declared prior-packet dependency. NPZ files remain opaque bytes.
"""
import argparse
import gzip
import json
import os
from pathlib import Path

import compositional_typed_package as P

SCHEMA='jepa-real-ir-transfer-evidence/1'
HERE=Path(__file__).resolve().parent
NAMES=('real-ir-coverage-v1','real-ir-coverage-v2','real-ir-coverage-v3','real-ir-transfer-v1')
PRIOR_SHA='0131a7169b9b4b789077b3f7348c3f968d9557cad2f75d3ece200a65269892f1'
LIMITS=dict(P.LIMITS)
EXTENSIONS={'.json','.jsonl','.log','.txt','.md','.npz','.py','.rs','.toml','.lock','.patch','.diff'}
TEXT=EXTENSIONS-{'.npz'}
BINARY='build-1/real-ir-transfer-native-collector'
DISPOSITIONS=('unstarted','failed','completed','completed')
COMMITS=dict(zip(NAMES,('f492f93c149cb26a11e1ab817ac0a78e6dc7fe7f','19942efeca1357cdbddef97013a0e08c71cbee90',
    'c44be0871cad71e5026e75e7a5f2fcac4f5b5733','b663fe8b282b43f35f41d147f27472bd604b2c96')))


def load(path): return json.loads(P.read_limited(Path(path),P.MAX_FILE))
def pin(path):
    path=Path(path).resolve(strict=True);v=P.transfer(path,'identity')
    return dict(path=str(path),sha256=v['raw_sha256'],bytes=v['raw_bytes'])
def require_pin(value):
    P.require(type(value)is dict and set(value)=={'path','sha256','bytes'} and Path(value['path']).is_absolute()and
        P.sha(value['sha256'])and type(value['bytes'])is int and value['bytes']>=0,'exact absolute byte pin required')
def commit(value):
    P.require(type(value)is str and len(value)==40 and all(c in'0123456789abcdef'for c in value),'exact full source commit required')
    return value


def history(root,disposition,read_bytes=None):
    """Accounting-only replay; no labels, predictions, arrays or parser calls."""
    root=Path(root);raw=lambda name:P.read_limited(root/name,P.MAX_FILE)if read_bytes is None else read_bytes(name)
    doc=lambda name:json.loads(raw(name))
    localpin=lambda name:dict(path=str(root/name),sha256=P.digest(raw(name)),bytes=len(raw(name)))
    spec,parent=doc('campaign-spec.json'),doc('parent-manifest.json')
    source=commit(spec['source_freeze_commit']);require_pin(spec['parent_manifest'])
    P.require(spec['schema']=='jepa-sealed-budget-spec/1'and spec['ledger_path']==str(root/'campaign-ledger.jsonl')and
        spec['parent_manifest']==localpin('parent-manifest.json'),'canonical spec/parent route differs')
    carry=parent['carry'];P.require(carry['observed_native_applies']is None,'unknown historical observed count must remain unknown')
    if disposition=='unstarted':
        closure=doc('prelaunch-closure.json')
        P.require(closure['status']=='unstarted-preflight-rejected'and closure['ledger_initialized']is False and
            closure['root_go']is False and closure['charged_seconds']==closure['engine_calls']==closure['neural_calls']==closure['paid_spend_usd']==0 and
            closure['spec']==localpin('campaign-spec.json')and 7<=len(closure['source_commit'])<=40 and source.startswith(closure['source_commit']),
            'unstarted allocation must retain its exact zero-call prelaunch closure')
        return dict(disposition=disposition,source_freeze_commit=source,closure=localpin('prelaunch-closure.json'),
            ledger_initialized=False,carry=carry,cumulative=carry,charged=None,observed=None,final_chain=None),spec,parent,[]
    P.require(disposition in('failed','completed'),'explicit closed disposition required')
    closure=doc('experiment-closure.json');journal=raw('campaign-ledger.jsonl')
    rows=[json.loads(line)for line in journal.splitlines()if line.strip()]
    keys=set(spec['caps'])-{'seconds'};charged={k:0 for k in spec['caps']};observed={k:0 for k in keys}
    previous='0'*64;finished=[];statuses=[];pending=None;proofs=[]
    for sequence,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'};d=row['data'];event=row['event']
        P.require(row['schema']=='jepa-sealed-budget-journal/1'and row['sequence']==sequence and row['previous_sha256']==previous and
            P.digest(P.canonical(body))==row['record_sha256'],'closed journal hashchain differs');previous=row['record_sha256']
        if event=='initialized':P.require(sequence==0 and d==dict(spec=localpin('campaign-spec.json')),'once-only exact spec initialization required')
        elif event=='begin':
            P.require(sequence>0 and pending is None and 'failed'not in statuses and len(finished)<len(spec['stage_order'])and
                d['stage']==spec['stage_order'][len(finished)]and d['argv']==spec['stages'][d['stage']]['argv']and d['guard']==spec['guard'],
                'once-only closed stage command/order differs')
            pending=dict(stage=d['stage'],open={},intents={k:0 for k in keys},done={k:0 for k in keys})
        elif event=='intent':
            P.require(pending is not None and d['token']==sequence and d['counter']in keys and P.number(d['amount'])and d['amount']>0,'invalid durable intent')
            k=d['counter'];pending['intents'][k]+=d['amount']
            P.require(pending['intents'][k]<=spec['stages'][pending['stage']]['reservation'][k],'intent exceeds reservation')
            pending['open'][d['token']]=(k,d['amount'])
        elif event=='complete':
            P.require(pending is not None and d['token']in pending['open'],'unpaired counter completion')
            k,n=pending['open'].pop(d['token']);external=k in spec['stages'][pending['stage']]['external_counters']
            P.require((external and P.number(d['actual'])and d['actual']<=n and len({p['path']for p in d['proofs']})>=2)or
                (not external and d['actual']is None and not d['proofs']),'ordinary/external completion differs')
            pending['done'][k]+=d['actual']if external else n;proofs+=d['proofs']
        elif event=='finish':
            P.require(pending is not None and d['status']in('completed','failed')and d['cleanup_verified']is True and
                d['execution_ended']is True and P.number(d['seconds']),'unresolved cleanup/execution cannot be packaged')
            stage=spec['stages'][pending['stage']];bad=d['status']=='failed'
            P.require(bad or(not pending['open']and d['seconds']<=stage['reservation']['seconds']and
                all(v is None or pending['done'][k]==v for k,v in stage['expected'].items())),'completed panel/ceiling differs')
            expected={k:max(stage['reservation'][k],pending['intents'][k])if bad else pending['done'][k]for k in keys}
            expected['seconds']=max(stage['reservation']['seconds'],d['seconds'])if bad else d['seconds']
            P.require(d['charged']==expected and d['durable_intents']==pending['intents']and d['durable_completed']==pending['done'],'failed reservation or observed prefix rewritten')
            for k,v in expected.items():charged[k]+=v
            for k in keys:observed[k]=None if bad and stage['reservation'][k]else None if observed[k]is None else observed[k]+pending['done'][k]
            finished.append(pending['stage']);statuses.append(d['status']);proofs+=d['proofs'];pending=None
        else:raise ValueError('pending failure/unreviewed accounting event')
    P.require(rows and pending is None and rows[-1]['event']=='finish','closed ended ledger required')
    if disposition=='failed':
        P.require(closure['status']=='closed-failed-before-outcomes'and finished==['coverage']and statuses==['failed']and
            charged['seconds']==10. and all(v==0 for k,v in charged.items()if k!='seconds')and closure['outcomes_collected']is False,
            'coverage-v2 full failed10s/zero-science disposition must remain exact')
    else:
        expected_status='closed-verified-local-transfer'if root.name=='real-ir-transfer-v1'else'closed-verified-coverage-and-reservation'
        P.require(closure['status']==expected_status and finished==spec['stage_order']and statuses==['completed']*len(finished),'all declared stages must be completed')
    cumulative=dict(charged_native_applies=carry['charged_native_applies']+charged['native_applies'],
        charged_seconds=carry['charged_seconds']+charged['seconds'],observed_native_applies=None)
    P.require(closure['source_freeze_commit']==source and closure['journal']==localpin('campaign-ledger.jsonl')and closure['final_chain']==previous and
        closure['new_charged']==charged and closure['cumulative']==cumulative and closure['production_changed']is False and
        charged['paid_jobs']==charged['paid_spend_usd']==0,'closure/source/carry/counter mismatch')
    if 'new_observed'in closure:P.require(closure['new_observed']==observed,'official observed knownness differs')
    return dict(disposition=disposition,source_freeze_commit=source,closure=localpin('experiment-closure.json'),
        ledger=localpin('campaign-ledger.jsonl'),records=len(rows),stages=finished,statuses=statuses,final_chain=previous,
        carry=carry,cumulative=cumulative,charged=charged,observed=observed),spec,parent,proofs


def source_pins(specs):
    """Copy explicit new research source pins, never recurse into historical pins."""
    result={}
    for spec in specs:
        for p in spec['pins']:
            path=Path(p['path'])
            if not path.is_relative_to(HERE):continue
            name=path.relative_to(HERE).parts[0]
            if not name.startswith(('real_ir_','test_real_ir_','REAL_IR_')):continue
            require_pin(p);P.require(p['path']not in result or result[p['path']]==p,'conflicting frozen source versions')
            result[p['path']]=p
    return result


def inventory(experiments,reports,dependency,lineage_review,validation_receipt=None):
    experiments=Path(experiments).resolve(strict=True);entries=[];excluded=[];histories={};specs=[];parents=[];proofs=[]
    def add(path,url,category,expected=None):
        if expected is not None:P.require(pin(path)==expected,'frozen source bytes differ')
        encoding='gzip'if path.suffix in TEXT else'identity'
        entries.append(dict(url=P.safe_name(url+('.gz'if encoding=='gzip'else'')),category=category,
            provenance=dict(original_path=str(path)),**P.transfer(path,encoding)));P.check_entries(entries)
    for name,disposition in zip(NAMES,DISPOSITIONS):
        root=experiments/name;P.require(root.is_dir()and not root.is_symlink(),'exact campaign root required')
        h,s,parent,pr=history(root,disposition);histories[name]=h;specs.append(s);parents.append(parent);proofs+=pr
        P.require(h['source_freeze_commit']==COMMITS[name],'declared historical freeze commit differs')
        if disposition=='unstarted':P.require(not(root/'campaign-ledger.jsonl').exists(),'unstarted ledger must remain absent')
        canonical={root/n for n in('campaign-spec.json','parent-manifest.json','campaign-ledger.jsonl',
            'experiment-closure.json','prelaunch-closure.json')}
        if name=='real-ir-transfer-v1':canonical.add(root/'metadata-1/native-plan.json')
        outputs=[Path(o)for stage in s['stages'].values()for o in stage['outputs']]
        P.require(all(p.is_absolute()and p.is_relative_to(root)and p.resolve()==p for p in outputs),'canonical in-root declared outputs required')
        for path in sorted(root.rglob('*')):
            P.require(not path.is_symlink(),'campaign symlink forbidden')
            if not path.is_file():continue
            P.require(path in canonical or any(path==p or path.is_relative_to(p)for p in outputs),'unreviewed campaign path outside metadata/declared stage outputs')
            relative=path.relative_to(root).as_posix()
            if relative==BINARY:
                excluded.append(dict(campaign=name,relative_path=relative,reason='compiled binary excluded; byte pin retained',
                    provenance=dict(original_path=str(path)),**P.transfer(path,'identity')));continue
            P.require(path.suffix in EXTENSIONS and not set(path.relative_to(root).parts)&{'target','__pycache__','.git','.venv'},'unexpected campaign payload')
            add(path,'payload/campaigns/'+name+'/'+relative,'campaign')
    P.require(histories[NAMES[0]]['cumulative']==histories[NAMES[1]]['carry']and
        all(histories[NAMES[i-1]]['cumulative']==histories[NAMES[i]]['carry']for i in(2,3)), 'linked parent charge reset')
    sources=source_pins(specs)
    for p in sources.values():add(Path(p['path']),'payload/sources/'+Path(p['path']).relative_to(HERE).as_posix(),'frozen-source',p)
    # Packager itself and its bounded primitive dependency are additive source,
    # not assertions that either was part of an earlier scientific freeze.
    for path in(Path(__file__).resolve(),HERE/'test_real_ir_transfer_package.py',HERE/'compositional_typed_package.py'):
        if str(path)not in sources:add(path,'payload/sources/'+path.name,'packaging-source')
    P.require(reports,'at least one final new report required')
    for path in sorted({Path(p).resolve(strict=True)for p in reports}):
        P.require(path.is_relative_to(HERE)and path.suffix=='.md'and path.name.startswith('REAL_IR_'),'new research report only')
        if str(path)not in sources:add(path,'payload/reports/'+path.name,'final-report')
    lineage_review=Path(lineage_review).resolve(strict=True)
    P.require(lineage_review==experiments/'real-ir-adapter-lineage-review.json','exact independent lineage review required')
    add(lineage_review,'payload/reviews/'+lineage_review.name,'lineage-review')
    if validation_receipt is not None:
        validation_receipt=Path(validation_receipt).resolve(strict=True)
        P.require(validation_receipt==experiments/'real-ir-adapter-local-validation.json','exact opaque local-validation receipt required')
        add(validation_receipt,'payload/reviews/'+validation_receipt.name,'local-validation')
    dependency=Path(dependency).resolve(strict=True);dp=pin(dependency)
    P.require(dp['sha256']==PRIOR_SHA,'exact prior publication dependency required; never recursively copy old trials')
    by_path={e['provenance']['original_path']:e for e in entries+excluded}
    for p in proofs:
        require_pin(p)
        if any(Path(p['path']).is_relative_to(experiments/name)for name in NAMES):
            e=by_path.get(p['path']);P.require(e is not None and e['raw_sha256']==p['sha256']and e['raw_bytes']==p['bytes'],'in-root completed proof absent/changed')
    return dict(schema=SCHEMA,limits=LIMITS,files=entries,excluded=excluded,histories=histories,
        source_freeze_commits={name:h['source_freeze_commit']for name,h in histories.items()},
        frozen_source_pins=list(sources.values()),
        dependency=dict(relative_manifest='../compositional-actual-admission-evidence/manifest.json',pin=dp,scope='Explicit prior publication dependency; not recursively fetched or copied.'),
        semantic_validated=False,scientific_calls=0,
        scope='Exact byte preservation of three coverage dispositions and one closed transfer; no model/array/native execution or publication/pointer mutation.')


def documents(plan):
    index=P.encode(dict(schema=SCHEMA,manifest='manifest.json',histories=plan['histories'],dependency=plan['dependency'],semantic_validated=False))
    P.require(len(index)<=P.MAX_MANIFEST,'index metadata limit')
    manifest=dict(plan,files=plan['files']+[dict(url='index.json',encoding='identity',sha256=P.digest(index),bytes=len(index),raw_sha256=P.digest(index),raw_bytes=len(index),category='index')])
    raw=P.encode(manifest);P.require(len(raw)<=P.MAX_MANIFEST,'4MiB manifest limit');P.check_entries(manifest['files'],len(raw))
    return index,raw


def prepare(experiments,out,reports,dependency,lineage_review,validation_receipt=None):
    out=Path(out);P.require(not out.is_symlink(),'destination symlink forbidden');out=out.resolve()
    P.require(not out.exists()and all(not out.is_relative_to(Path(experiments).resolve()/name)and
        not(Path(experiments).resolve()/name).is_relative_to(out)for name in NAMES),'exclusive destination outside evidence roots required')
    plan=inventory(experiments,reports,dependency,lineage_review,validation_receipt);documents(plan);return plan


def build(experiments,out,reports,dependency,lineage_review,validation_receipt=None):
    plan=prepare(experiments,out,reports,dependency,lineage_review,validation_receipt);index,manifest=documents(plan);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    for e in plan['files']:
        target=out/e['url'];target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as f:
            actual=P.transfer(Path(e['provenance']['original_path']),e['encoding'],f);f.flush();os.fsync(f.fileno())
        P.require(all(actual[k]==e[k]for k in actual),'source changed during byte copy')
    P.require(inventory(experiments,reports,dependency,lineage_review,validation_receipt)==plan,'source inventory changed while copying')
    for name,data in(('index.json',index),('manifest.json',manifest)):
        with(out/name).open('xb')as f:f.write(data);f.flush();os.fsync(f.fileno())
    return verify(out)


def verify(out,expected_manifest_sha=None):
    out=Path(out);P.require(not out.is_symlink()and not(out/'manifest.json').is_symlink(),'packet symlink forbidden');out=out.resolve(strict=True)
    raw=P.read_limited(out/'manifest.json',P.MAX_MANIFEST)
    if expected_manifest_sha is not None:P.require(P.digest(raw)==expected_manifest_sha,'manifest pin differs')
    m=json.loads(raw);P.require(m['schema']==SCHEMA and m['limits']==LIMITS and m['dependency']['pin']['sha256']==PRIOR_SHA and
        m['source_freeze_commits']==COMMITS and m['semantic_validated']is False and m['scientific_calls']==0,'packet identity/scope differs');P.check_entries(m['files'],len(raw));expected={'manifest.json'}
    by_original={}
    for e in m['files']:
        name=P.safe_name(e['url']);P.require(name not in expected,'duplicate packet URL');expected.add(name);path=out/name
        P.require(path.resolve().is_relative_to(out)and not any(p.is_symlink()for p in(path,*path.parents)if p.is_relative_to(out)),'packet symlink/path escape')
        P.verify_payload(path,e)
        if 'provenance'in e:by_original[e['provenance']['original_path']]=e
    actual=set()
    for path in out.rglob('*'):
        P.require(not path.is_symlink(),'packet symlink forbidden')
        if path.is_file():actual.add(path.relative_to(out).as_posix())
    P.require(actual==expected and tuple(m['histories'])==NAMES,'packet membership/root inventory differs')
    for name,disposition in zip(NAMES,DISPOSITIONS):
        h=m['histories'][name];root=Path(h['closure']['path']).parent
        def read_bytes(relative):
            e=by_original[str(root/relative)];path=out/e['url']
            with(gzip.open(path,'rb')if e['encoding']=='gzip'else path.open('rb'))as f:data=f.read(e['raw_bytes']+1)
            P.require(len(data)==e['raw_bytes'],'bounded accounting payload differs');return data
        rebuilt,_,_,_=history(root,disposition,read_bytes)
        P.require(rebuilt==h and m['source_freeze_commits'][name]==h['source_freeze_commit'],'offline history/commit differs')
        if disposition=='unstarted':P.require(str(root/'campaign-ledger.jsonl')not in by_original,'unstarted root gained a ledger')
    P.require(m['histories'][NAMES[0]]['cumulative']==m['histories'][NAMES[1]]['carry']and
        all(m['histories'][NAMES[i-1]]['cumulative']==m['histories'][NAMES[i]]['carry']for i in(2,3)),'offline carry lineage differs')
    return dict(status='verified-bytes-only',manifest_sha256=P.digest(raw),files=len(actual),
        raw_bytes=sum(e['raw_bytes']for e in m['files'])+len(raw),stored_bytes=sum(e['bytes']for e in m['files'])+len(raw),
        source_freeze_commits=m['source_freeze_commits'],semantic_validated=False,scientific_calls=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--build',action='store_true');g.add_argument('--verify',action='store_true')
    p.add_argument('--experiments',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,action='append',default=[])
    p.add_argument('--dependency',type=Path,default=HERE/'compositional-actual-admission-evidence/manifest.json');p.add_argument('--lineage-review',type=Path);p.add_argument('--validation-receipt',type=Path);p.add_argument('--expected-manifest-sha');a=p.parse_args()
    if a.verify:value=verify(a.out,a.expected_manifest_sha)
    else:P.require(a.experiments is not None and a.lineage_review is not None,'exact experiments parent/lineage review required');value=(build if a.build else prepare)(a.experiments,a.out,a.report,a.dependency,a.lineage_review,a.validation_receipt)
    print(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))
if __name__=='__main__':main()
