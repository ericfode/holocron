"""Saved-only continuation; the failed native allocation is never reopened.

Recovery uses exact durable contextComplete cases, not the truncated pretty JSON.
Fixture validation is a frozen source/control-flow inference, not invented saved
per-fixture captures. Only root may prepare/initialize/run the new allocation.
"""
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D
import compositional_typed_campaign as C

HERE=Path(__file__).resolve().parent
OLD=C.ROOT;ROOT=D.EXPERIMENTS/'compositional-typed-saved-v1'
SECONDS=dict(recover=10.,prep=5.,fit=120.,verify=10.)
ZERO=dict(C.ZERO)
COLLECTOR=HERE/'compositional_typed_native_collector/src/main.rs'
BINARY=OLD/'build-1/compositional-typed-native-collector'
SCOPE='source-control-flow-attestation-only; no persisted per-fixture validation records'


def read(path):return json.loads(Path(path).read_text())
def write_new(path,value):
    raw=S.encoded(value)+b'\n'
    with Path(path).open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return S.pin(path)
def copy_new(source,target):
    with Path(source).open('rb')as src,Path(target).open('xb')as dst:shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
    p=S.pin(target);S.require(p['sha256']==S.pin(source)['sha256']and p['bytes']==S.pin(source)['bytes'],'exact source byte copy required');return p
def source_inference(source):
    validation='let validation=validate_fixtures(&engine,&plan)?;'
    creation='let mut journal=fs::OpenOptions::new().write(true).create_new(true).open(journal_path)'
    S.require(source.count(validation)==source.count(creation)==1 and source.index(validation)<source.index(creation),'reviewed validation-before-header control flow differs')
    return dict(scope=SCOPE,per_fixture_validation_records_persisted=False,validated_fixtures_inferred=128,
        validation_call_offset=source.index(validation),journal_creation_offset=source.index(creation),
        reason='The exact reviewed binary/source reaches journal creation only after successful all128 validate_fixtures return; individual validation captures were lost with truncated final serialization.')


def reconstruct(plan,plan_pin,records,provenance,source):
    """Pure JSON reconstruction; callers own the guard, byte pins and writes."""
    S.require(records and records[0]['schema']=='jepa-compositional-typed-apply-journal/1','native header required')
    header=records[0];S.require(header['planSha256']==plan_pin['sha256']and header['sourceRevision']==plan['source_revision']and header['maxApplyCalls']==512 and header['expectedCases']==128,'exact original source/plan header required')
    S.require(len(plan['worlds'])==128 and all(r.get('phase')in('beforeApply','afterApply','contextComplete')for r in records[1:]),'all reviewed roots/phases required')
    cases=[r['case']for r in records if r.get('phase')=='contextComplete'];before=[r for r in records if r.get('phase')=='beforeApply'];after=[r for r in records if r.get('phase')=='afterApply']
    S.require(len(cases)==128 and [c['world_id']for c in cases]==list(range(128))and len(before)==len(after)==256,'all128 completed contexts and256 actual pairs required')
    S.require([r['applyCall']for r in before]==[r['applyCall']for r in after]==list(range(1,257))and[(r['phase'],r['applyCall'])for r in records[1:]if r['phase']!='contextComplete']==[(p,i)for i in range(1,257)for p in('beforeApply','afterApply')],'durable paired native chronology differs')
    cursor=0
    for world,case in zip(plan['worlds'],cases):
        complete=case.get('engineError')is None and((case['completion']=='settled'and case['intentResolution']in('committed','unoffered-declined'))or(case['completion']=='unoffered-observation-only'and case['intentOffered']is False and case['final']is None))
        terminal={'committed':'settled-committed','unoffered-declined':'settled-cancelled','unoffered-observation-only':'unoffered-prompt-only'}.get(case['intentResolution'])
        S.require(complete and case['terminalClassification']==terminal and case['world_id']==world['id']and case['card']==world['source_code']and 0<len(case['steps'])==case['applyCalls']<=4,'native completed typed root differs')
        for step in case['steps']:
            left,right=before[cursor],after[cursor];cursor+=1
            S.require(left['before']==step['before']and left['offeredAction']==step['action']and right['after']==step['after']and left['branch']==right['branch']==step['stage']and left['context']==right['context'],'journal/case action-state bytes differ')
    S.require(cursor==256,'case apply total differs');inference=source_inference(source)
    proof=dict(provenance,fixture_validation_scope=SCOPE,fixture_validation_inference=inference,
        source_observed_native_applies=256,source_charged_native_applies=512,new_native_applies=0,no_credit=True,
        per_fixture_validation_records_persisted=False,truncated_pretty_receipt_reparsed=False)
    return dict(schema='jepa-compositional-typed-native/1',synthetic=True,sourceRevision=header['sourceRevision'],
        collectionPlan=plan,collectionPlanSha256=header['planSha256'],candidateOrder=plan['candidate_order'],
        programs=plan['programs'],selectedWholeCards=plan['selected_whole_cards'],cases=cases,collectionComplete=True,
        applyCalls=256,maxApplyCalls=512,elapsedSeconds=None,selectedCatalogueSha256=None,
        recovery_provenance=proof),proof


def prepare():
    S.require(not ROOT.exists(),'new continuation root only; never reset old failure')
    prior=S.Budget(OLD/'campaign-spec.json');state=prior.inspect();closure=read(OLD/'experiment-closure.json')
    S.require(state['pending']is None and state['completed']==['metadata','build']and state['failures']==1 and state['cumulative']==closure['cumulative'],'exact closed failed native parent required')
    S.require(state['charged']['native_applies']==512 and state['charged']['seconds']==31.28667466691695 and state['cumulative']==dict(charged_native_applies=807,charged_seconds=254.2131857079221,observed_native_applies=None),'all failed reservations/carry retained')
    S.require(state['charged']['seconds']+sum(SECONDS.values())<=prior.spec['caps']['seconds'],'saved continuation must fit original185-second envelope without credit')
    S.require(all(state['charged'][k]==0 for k in('neural_forwards','backwards','optimizer_updates','numerical_fits','paid_jobs','paid_spend_usd')),'no prior fitting may be hidden')
    ROOT.mkdir();parent=copy.deepcopy(prior.parent);parent['carry']=state['cumulative']
    additions=list(prior.frozen.values())+list(state['proofs'].values())+[S.pin(p)for p in OLD.rglob('*')if p.is_file()]
    unique={p['path']:p for p in parent['pins']}
    for p in additions:S.verify_pin(p);S.require(p['path']not in unique or unique[p['path']]==p,'conflicting preserved pin');unique[p['path']]=p
    parent['pins']=[unique[k]for k in sorted(unique)];parent['closed_journals'].append(D.closed_journal(prior.ledger));parent['protected_roots'].append(str(OLD));pm=write_new(ROOT/'parent-manifest.json',parent)
    py=prior.spec['stages']['metadata']['argv'][0];stages={}
    for name,seconds in SECONDS.items():
        counts=dict(ZERO)
        if name=='fit':counts.update(neural_forwards=3624,backwards=3600,optimizer_updates=3600,numerical_fits=2)
        out=ROOT/(name+'-1');outputs=[str(out),str(ROOT/(name+'-1-stage-receipt.json'))]
        if name=='recover':outputs +=[str(ROOT/'metadata-1'),str(ROOT/'native-1')]
        stages[name]=dict(argv=[py,str(Path(__file__).resolve()),'run','--stage',name,'--spec',str(ROOT/'campaign-spec.json')],outputs=outputs,reservation=dict(seconds=seconds,**counts),expected=counts,external_counters=[])
    files=[Path(__file__),HERE/'test_compositional_typed_saved_campaign.py',HERE/'compositional_typed_saved_verify.py',HERE/'test_compositional_typed_saved_verify.py',HERE/'COMPOSITIONAL_TYPED_SAVED_RECOVERY.md',Path(py)]
    pins={p['path']:p for p in prior.spec['pins']}
    for path in files:p=S.pin(path);S.require(p['path']not in pins or pins[p['path']]==p,'conflicting runtime source pin');pins[p['path']]=p
    spec=dict(schema=S.SPEC_SCHEMA,status='sealed-awaiting-root-GO',source=S.pin(S.__file__),primitives=S.pin(S._PATH),parent_manifest=pm,
        ledger_path=str(ROOT/'campaign-ledger.jsonl'),caps=dict(seconds=145.,**dict(ZERO,neural_forwards=3624,backwards=3600,optimizer_updates=3600,numerical_fits=2)),
        guard=prior.spec['guard'],stage_order=list(stages),stages=stages,pins=[pins[k]for k in sorted(pins)],environment=prior.spec['environment'],financial=prior.spec['financial'],
        source_freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
        scope='Saved-only continuation after native serialization timeout; source journal observed256 remains distinct from failed512 charged. Zero new engine calls; frozen original science unchanged.')
    write_new(ROOT/'campaign-spec.json',spec);S.Budget(ROOT/'campaign-spec.json').verify();return S.pin(ROOT/'campaign-spec.json')


def recover(run,out):
    inputs=dict(source_journal=OLD/'native-1/transitions.jsonl',source_plan=OLD/'metadata-1/native-plan.json',failed_ledger=OLD/'campaign-ledger.jsonl',failed_stage_receipt=OLD/'native-1-stage-receipt.json',built_binary=BINARY,collector_source=COLLECTOR,source_campaign_spec=OLD/'campaign-spec.json',truncated_pretty_receipt=OLD/'native-1/receipt.json')
    allowed=dict(run.owner.frozen,**run.state['proofs']);provenance={}
    for key,path in inputs.items():p=S.pin(path);S.require(allowed.get(p['path'])==p,'recovery input not sealed: '+key);provenance[key]=p
    receipt=read(inputs['failed_stage_receipt']);S.require(receipt['stage']=='native'and receipt['status']=='failed'and receipt['cleanup_verified']is True,'original closed cleanup failure retained')
    rows=[json.loads(line)for line in inputs['source_journal'].read_text().splitlines()if line.strip()];plan=read(inputs['source_plan'])
    raw,proof=reconstruct(plan,provenance['source_plan'],rows,provenance,COLLECTOR.read_text())
    metadata=ROOT/'metadata-1';native=ROOT/'native-1';metadata.mkdir();native.mkdir()
    copy_new(inputs['source_plan'],metadata/'native-plan.json');copy_new(inputs['source_journal'],native/'transitions.jsonl')
    rp=write_new(native/'receipt.json',raw);pp=write_new(native/'recovery-provenance.json',proof);write_new(out/'recovery-provenance.json',proof)
    return dict(recovered_receipt=rp,recovery_provenance=pp,source_observed_native_applies=256,new_native_applies=0,fixture_validation_scope=SCOPE)


def stage(args):
    budget=S.Budget(args.spec);args.out=ROOT/(args.stage+'-1');receipt_path=ROOT/(args.stage+'-1-stage-receipt.json')
    with budget.lease()as run:
        status='failed';guard=None;created=False;receipt=dict(stage=args.stage,cleanup_verified=True,source=S.pin(__file__))
        try:
            descriptor=budget.spec['stages'][args.stage];actual=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
            run.begin(args.stage,argv=descriptor['argv'],guard=budget.spec['guard'],inputs=list(run.state['proofs'].values()))
            S.require(actual==descriptor['argv'],'actual command differs after durable reservation')
            S.require(args.spec.resolve()==ROOT/'campaign-spec.json'and descriptor['reservation']['native_applies']==0,'canonical saved-only zero-native allocation')
            args.out.mkdir();created=True;E=importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds())as guard:
                if args.stage=='recover':receipt['result']=recover(run,args.out)
                elif args.stage=='prep':
                    import numpy as np
                    T=importlib.import_module('compositional_typed_data');arrays,manifest=T.prepare_data(np,read(ROOT/'metadata-1/native-plan.json'),read(ROOT/'native-1/receipt.json'),[json.loads(v)for v in(ROOT/'native-1/transitions.jsonl').read_text().splitlines()])
                    np.savez_compressed(args.out/'dataset.npz',**arrays);write_new(args.out/'manifest.json',manifest)
                elif args.stage=='fit':
                    args.plan=ROOT/'metadata-1/native-plan.json';args.dataset=ROOT/'prep-1/dataset.npz';args.manifest=ROOT/'prep-1/manifest.json';F=importlib.import_module('compositional_typed_fit');receipt['result']=F.worker(args,run)
                elif args.stage=='verify':
                    import numpy as np
                    V=importlib.import_module('compositional_typed_saved_verify');receipt['result']=V.verify(np,ROOT,args.out)
                else:raise ValueError('unallocated saved-only stage')
            status='completed'
        except BaseException as error:
            if run.state['pending']is None:raise
            receipt['error']=dict(type=type(error).__name__,message=str(error))
        receipt.update(status=status,guard=guard.receipt()if guard else None)
        outputs=[Path(p)for p in budget.spec['stages'][args.stage]['outputs']if Path(p)!=receipt_path]
        artifacts=[S.pin(p)for directory in outputs if directory.exists()for p in sorted(directory.rglob('*'))if p.is_file()];rp=None
        try:rp=write_new(receipt_path,receipt)
        except BaseException as error:status='failed';receipt['receipt_write_error']=dict(type=type(error).__name__,message=str(error))
        state=run.finish(status,proofs=artifacts+([rp]if rp else[]),cleanup_verified=True,execution_ended=True)
        S.require(status=='completed'and args.stage in state['completed'],'saved continuation failed; full reservation retained: '+str(receipt.get('error')))
        return dict(stage=args.stage,status='completed',receipt=rp,cumulative=state['cumulative'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','initialize','status','run']);p.add_argument('--stage',choices=list(SECONDS));p.add_argument('--spec',type=Path,default=ROOT/'campaign-spec.json');a=p.parse_args()
    value=prepare()if a.action=='prepare'else S.Budget(a.spec).initialize(root_go=True)if a.action=='initialize'else stage(a)if a.action=='run'else S.Budget(a.spec).inspect();print(json.dumps(value,indent=2,allow_nan=False))
if __name__=='__main__':main()
