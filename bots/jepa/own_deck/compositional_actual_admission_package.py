"""Bounded byte-only archive of the closed actual-admission audit.

No parser/model/native code is imported or rerun. Historical pins are opaque;
only the explicit audit, catalogue, prior receipt, and source inputs are copied.
"""
import argparse
import json
import os
from pathlib import Path

import compositional_typed_package as P

SCHEMA='jepa-compositional-actual-admission-evidence/1'
COMMIT='3914582462ecea3368ef6a60f74f08424dfb288b'
OLD_PACKET='70536441fce9f4cd1a3b59dd1781548a0a023adf96996d7f43e260298e9065a6'
P_SHA='bd96392b146b88d048809bce825b0b56ccd540304a1f6cc1f0624c16a67aabfd'
LIMITS=dict(file_bytes=P.MAX_FILE,total_raw_bytes=128*1024**2,total_stored_bytes=128*1024**2,files=100,manifest_bytes=P.MAX_MANIFEST)
SOURCES=('compositional_actual_admission.py','compositional_actual_admission_verify.py',
    'compositional_actual_admission_campaign.py','COMPOSITIONAL_ACTUAL_ADMISSION_PROTOCOL.md','compositional_typed_model.py')


def load(path):return json.loads(P.read_limited(path,P.MAX_FILE))
def pin(path):
    p=P.transfer(path,'identity');return dict(path=str(path),sha256=p['raw_sha256'],bytes=p['raw_bytes'])
def check(entries,size=0):
    P.check_entries(entries,size)
    P.require(len(entries)+1<=100 and sum(e['raw_bytes']for e in entries)+size<=LIMITS['total_raw_bytes']and
        sum(e['bytes']for e in entries)+size<=LIMITS['total_stored_bytes'],'100-file/128MiB packet limit')


def closed(root):
    spec=load(root/'campaign-spec.json');parent=load(root/'parent-manifest.json');closure=load(root/'experiment-closure.json')
    P.require(spec['schema']=='jepa-sealed-budget-spec/1'and spec['source_freeze_commit']==COMMIT and
        spec['stage_order']==['audit','verify']and spec['ledger_path']==str(root/'campaign-ledger.jsonl')and
        spec['parent_manifest']==pin(root/'parent-manifest.json'),'exact frozen audit/spec route required')
    zero={k:0 for k in spec['caps']if k!='seconds'}
    P.require(all(spec['caps'][k]==0 for k in zero),'audit cannot allocate scientific exposure')
    rows=[json.loads(v)for v in P.read_limited(root/'campaign-ledger.jsonl',P.MAX_FILE).splitlines()if v.strip()]
    previous='0'*64;pending=None;finished=[];seconds=0.;proofs=[]
    for i,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'};d=row['data'];event=row['event']
        P.require(row['schema']=='jepa-sealed-budget-journal/1'and row['sequence']==i and row['previous_sha256']==previous and
            P.digest(P.canonical(body))==row['record_sha256'],'damaged audit ledger chain');previous=row['record_sha256']
        if event=='initialized':P.require(i==0 and d==dict(spec=pin(root/'campaign-spec.json')),'once-only frozen initialization required')
        elif event=='begin':
            P.require(i>0 and pending is None and len(finished)<2 and d['stage']==spec['stage_order'][len(finished)]and
                d['argv']==spec['stages'][d['stage']]['argv']and d['guard']==spec['guard'],'ordered exact audit stages required')
            pending=d['stage'];proofs.extend(d.get('inputs',[]))
        elif event=='finish':
            P.require(pending is not None and d['status']=='completed'and d['cleanup_verified']is True and d['execution_ended']is True and
                P.number(d['seconds'])and d['seconds']<=spec['stages'][pending]['reservation']['seconds']and
                d['charged']==dict(seconds=d['seconds'],**zero)and d['durable_intents']==d['durable_completed']==zero,
                'closed zero-science audit stage required')
            seconds+=d['seconds'];finished.append(pending);pending=None;proofs.extend(d['proofs'])
        else:raise ValueError('unreviewed event or scientific intent in byte-audit journal')
    P.require(finished==['audit','verify']and pending is None and rows[-1]['event']=='finish'and seconds<=spec['caps']['seconds'],'both audit stages must complete')
    P.require(closure['journal']==pin(root/'campaign-ledger.jsonl')and closure['final_chain']==previous and
        closure['source_freeze_commit']==COMMIT and closure['new_charged']==dict(seconds=seconds,**zero)and closure['new_observed']==zero,
        'closure/source/counters differ')
    carry=parent['carry'];P.require(closure['cumulative']==dict(charged_native_applies=carry['charged_native_applies'],
        charged_seconds=carry['charged_seconds']+seconds,observed_native_applies=carry['observed_native_applies']),'parent carry changed')
    for key in('report','verification'):P.require(pin(Path(closure[key]['path']))==closure[key],'closure output pin differs')
    return spec,closure,proofs


def prepare(campaign,out):
    P.require(not Path(campaign).is_symlink()and not Path(out).is_symlink(),'root/destination symlink forbidden')
    root=Path(campaign).resolve(strict=True);out=Path(out).resolve()
    P.require(root.name=='compositional-actual-admission-v1'and not out.exists()and
        not out.is_relative_to(root)and not root.is_relative_to(out),'exact closed campaign and exclusive outside destination required')
    spec,closure,proofs=closed(root);files={};inputs=[]
    for path in sorted(root.rglob('*')):
        P.require(not path.is_symlink(),'campaign symlink forbidden')
        if path.is_file():
            relative=path.relative_to(root).as_posix();P.safe_name(relative)
            P.require(path.suffix in P.EXTENSIONS,'unexpected campaign payload');files['campaign/'+relative]=path
    by_name={}
    for item in spec['pins']:by_name.setdefault(Path(item['path']).name,[]).append(item)
    selections=[('sources/'+name,name)for name in SOURCES]+[
        ('inputs/catalogue/cards.json','cards.json'),('inputs/catalogue/runtime-admission.json','runtime-admission.json'),
        ('inputs/prior/native-plan.json','native-plan.json'),('inputs/prior/receipt.json','receipt.json'),
        ('inputs/compositional-typed-publication-complete.json','compositional-typed-publication-complete.json')]
    for url,name in selections:
        P.require(len(by_name.get(name,[]))==1,'one explicit frozen input required: '+name)
        expected=by_name[name][0];path=Path(expected['path']);P.require(pin(path)==expected,'frozen input bytes differ: '+name)
        inputs.append(expected);files[url]=path
    publication=load(files['inputs/compositional-typed-publication-complete.json'])
    P.require(publication['packet_manifest']['sha256']==OLD_PACKET,'exact prior packet reference required')
    shared=Path(P.__file__).resolve();P.require(pin(shared)['sha256']==P_SHA,'frozen byte primitives changed')
    files['sources/'+shared.name]=shared;files['sources/'+Path(__file__).name]=Path(__file__).resolve()
    entries=[]
    for url,path in files.items():
        encoding='identity'if path.suffix=='.npz'else'gzip'
        entries.append(dict(url='payload/'+url+('.gz'if encoding=='gzip'else''),provenance=dict(original_path=str(path)),**P.transfer(path,encoding)));check(entries)
    mapping={e['provenance']['original_path']:e for e in entries}
    for expected in proofs+[closure['report'],closure['verification']]:
        actual=mapping.get(expected['path']);P.require(actual is not None and expected['sha256']==actual['raw_sha256']and expected['bytes']==actual['raw_bytes'],'closed output proof not copied exactly')
    plan=dict(schema=SCHEMA,limits=LIMITS,source_freeze_commit=COMMIT,prior_packet_manifest=publication['packet_manifest'],
        closure_pin=pin(root/'experiment-closure.json'),closed_journal=dict(records=5,final_chain=closure['final_chain'],completed_stages=['audit','verify']),
        frozen_copied_inputs=inputs,files=entries,semantic_validated=False,
        scope='Byte-only admission-audit archive; no parser/model/native/evaluation rerun. Historical parent pins remain opaque provenance.')
    documents(plan);return plan


def documents(plan):
    index=P.encode(dict(schema=SCHEMA,source_freeze_commit=COMMIT,artifacts=plan['files'],prior_packet_manifest=plan['prior_packet_manifest'],semantic_validated=False))
    P.require(len(index)<=P.MAX_MANIFEST,'index metadata limit')
    manifest=dict(plan,files=plan['files']+[dict(url='index.json',encoding='identity',bytes=len(index),raw_bytes=len(index),sha256=P.digest(index),raw_sha256=P.digest(index))])
    raw=P.encode(manifest);P.require(len(raw)<=P.MAX_MANIFEST,'4MiB manifest limit');check(manifest['files'],len(raw));return index,raw


def build(campaign,out):
    plan=prepare(campaign,out);index,manifest=documents(plan);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    for entry in plan['files']:
        path=out/entry['url'];path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as stream:
            actual=P.transfer(Path(entry['provenance']['original_path']),entry['encoding'],stream);stream.flush();os.fsync(stream.fileno())
        P.require(all(actual[k]==entry[k]for k in actual),'source changed during byte copy')
    P.require(prepare(campaign,out.parent/(out.name+'-source-check'))==plan,'source membership/content changed during copy')
    for name,raw in(('index.json',index),('manifest.json',manifest)):
        with(out/name).open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return verify(out)


def verify(out,expected_manifest_sha=None):
    out=Path(out);P.require(not out.is_symlink(),'packet symlink forbidden');out=out.resolve(strict=True)
    P.require(not(out/'manifest.json').is_symlink(),'manifest symlink forbidden');raw=P.read_limited(out/'manifest.json',P.MAX_MANIFEST)
    if expected_manifest_sha is not None:P.require(P.digest(raw)==expected_manifest_sha,'manifest pin mismatch')
    m=json.loads(raw);P.require(m['schema']==SCHEMA and m['limits']==LIMITS and m['source_freeze_commit']==COMMIT and
        m['prior_packet_manifest']['sha256']==OLD_PACKET and m['semantic_validated']is False,'exact packet identity required');check(m['files'],len(raw));expected={'manifest.json'}
    for entry in m['files']:
        name=P.safe_name(entry['url']);P.require(name not in expected,'duplicate payload');expected.add(name);path=out/name
        P.require(path.resolve().is_relative_to(out)and not any(p.is_symlink()for p in[path,*path.parents]if p.is_relative_to(out)),'packet path/symlink escape')
        P.verify_payload(path,entry)
    actual=set()
    for path in out.rglob('*'):
        P.require(not path.is_symlink(),'packet symlink forbidden')
        if path.is_file():actual.add(path.relative_to(out).as_posix())
    P.require(actual==expected,'packet membership differs')
    return dict(status='verified-bytes-only',manifest_sha256=P.digest(raw),files=len(actual),
        raw_bytes=sum(e['raw_bytes']for e in m['files'])+len(raw),stored_bytes=sum(e['bytes']for e in m['files'])+len(raw),
        source_freeze_commit=COMMIT,prior_packet_manifest_sha256=OLD_PACKET,semantic_validated=False,scientific_calls=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--build',action='store_true');g.add_argument('--verify',action='store_true')
    p.add_argument('--campaign',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-manifest-sha');a=p.parse_args()
    if a.verify:value=verify(a.out,a.expected_manifest_sha)
    else:P.require(a.campaign is not None,'campaign required');value=(build if a.build else prepare)(a.campaign,a.out)
    print(json.dumps(value,sort_keys=True,indent=2,allow_nan=False))
if __name__=='__main__':main()
