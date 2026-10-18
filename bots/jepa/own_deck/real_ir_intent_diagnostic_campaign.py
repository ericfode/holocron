"""Once-only saved-evidence diagnosis before choosing a corrected card model."""
import argparse
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE=Path(__file__).resolve().parent
ROOT=D.EXPERIMENTS/'real-ir-intent-diagnostic-v1'
PRIOR=D.EXPERIMENTS/'real-ir-hp-projection-v1'
OLD=D.EXPERIMENTS/'real-ir-transfer-v1'
ZERO=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)

def read(path):return json.loads(Path(path).read_text())

def prepare():
    S.require(not ROOT.exists(),'one new immutable diagnostic allocation')
    prior=S.Budget(PRIOR/'campaign-spec.json');state=prior.inspect();closure=read(PRIOR/'experiment-closure.json')
    S.require(state['completed']==prior.spec['stage_order']and not state['failures']and state['pending']is None and
        state['cumulative']==closure['cumulative']==dict(charged_native_applies=1031,charged_seconds=312.50895287597086,observed_native_applies=None),'exact closed HP projection parent')
    ROOT.mkdir();parent=copy.deepcopy(prior.parent);parent['carry']=state['cumulative'];pins={p['path']:p for p in parent['pins']}
    additions=list(prior.frozen.values())+[S.pin(p)for p in PRIOR.rglob('*')if p.is_file()]
    additions +=[S.pin(D.EXPERIMENTS/n)for n in('real-ir-hp-handoff.json','real-ir-hp-publication-complete.json','real-ir-hp-lineage-review.json','real-ir-hp-fresh-reservation.json')]
    additions +=[S.pin(p)for p in(HERE/'real-ir-hp-projection-evidence').rglob('*')if p.is_file()]
    additions +=[S.pin(HERE/n)for n in('REAL_IR_HP_PROJECTION_RESULTS.md','REAL_IR_HP_EVIDENCE.md')]
    for p in additions:
        S.verify_pin(p);S.require(p['path']not in pins or pins[p['path']]==p,'immutable parent conflict');pins[p['path']]=p
    parent['pins']=[pins[k]for k in sorted(pins)];parent['protected_roots'] +=[str(PRIOR),str(HERE/'real-ir-hp-projection-evidence')]
    parent['closed_journals'].append(D.closed_journal(prior.ledger));pm=D.write_new(ROOT/'parent-manifest.json',parent)
    py=prior.spec['stages']['fit']['argv'][0]
    stage=dict(argv=[py,str(Path(__file__).resolve()),'run','--spec',str(ROOT/'campaign-spec.json')],
        outputs=[str(ROOT/'diagnose-1'),str(ROOT/'diagnose-1-stage-receipt.json')],reservation=dict(seconds=10.,**ZERO),expected=dict(ZERO),external_counters=[])
    files=[HERE/n for n in('real_ir_intent_diagnostic_campaign.py','real_ir_intent_diagnostic.py','test_real_ir_intent_diagnostic.py','REAL_IR_INTENT_DIAGNOSTIC_PROTOCOL.md','effect_identifiability_fit.py')]
    spec=dict(schema=S.SPEC_SCHEMA,status='sealed-awaiting-root-GO',source=S.pin(S.__file__),primitives=S.pin(S._PATH),parent_manifest=pm,
        ledger_path=str(ROOT/'campaign-ledger.jsonl'),caps=dict(seconds=10.,**ZERO),guard=dict(cpu_workers=1,rss_bytes=1024**3),stage_order=['diagnose'],stages=dict(diagnose=stage),
        pins=[S.pin(p)for p in files+[Path(py)]],environment=prior.spec['environment'],financial=prior.spec['financial'],
        source_freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
        scope='Original TRAIN40 saved-only magnitude diagnosis. Slice before calculations; no held outcomes, new neural/native calls, numerical fitting, or qualification.')
    D.write_new(ROOT/'campaign-spec.json',spec);S.Budget(ROOT/'campaign-spec.json').verify();return S.pin(ROOT/'campaign-spec.json')

def stage(args):
    b=S.Budget(args.spec);out=ROOT/'diagnose-1';rp=ROOT/'diagnose-1-stage-receipt.json'
    with b.lease()as run:
        status='failed';guard=None;receipt=dict(cleanup_verified=True)
        try:
            d=b.spec['stages']['diagnose'];run.begin('diagnose',argv=d['argv'],guard=b.spec['guard'],inputs=list(run.state['proofs'].values()))
            S.require([str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]==d['argv']and args.spec.resolve()==ROOT/'campaign-spec.json','exact sealed runtime')
            S.require(all(os.environ.get(k)==v for k,v in b.spec['environment'].items()),'sealed environment')
            out.mkdir();E=importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds())as guard:
                import numpy as np
                C=importlib.import_module('real_ir_intent_diagnostic')
                result=C.worker(np,OLD,PRIOR)
                receipt['result']=D.write_new(out/'diagnostic.json',result)
            status='completed'
        except BaseException as error:
            if run.state['pending']is None:raise
            receipt['error']=dict(type=type(error).__name__,message=str(error))
        receipt.update(status=status,guard=guard.receipt()if guard else None);proof=D.write_new(rp,receipt)
        state=run.finish(status,proofs=[S.pin(p)for p in out.rglob('*')if p.is_file()]+[proof],cleanup_verified=True,execution_ended=True)
        S.require(status=='completed'and 'diagnose' in state['completed'],'failed diagnostic; retain full reservation: '+str(receipt.get('error')))
        return dict(receipt=proof,charged=state['charged'],cumulative=state['cumulative'])

def close():
    b=S.Budget(ROOT/'campaign-spec.json');state=b.inspect()
    S.require(state['completed']==['diagnose']and not state['failures']and state['pending']is None,'completed diagnosis required')
    return D.write_new(ROOT/'experiment-closure.json',dict(schema='jepa-real-ir-intent-diagnostic-closure/1',status='closed-saved-diagnostic',
        source_freeze_commit=b.spec['source_freeze_commit'],diagnostic=S.pin(ROOT/'diagnose-1/diagnostic.json'),journal=S.pin(b.ledger),final_chain=state['last_sha256'],
        new_charged=state['charged'],cumulative=state['cumulative'],financial=b.spec['financial'],production_changed=False,semantic_validated=False))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','initialize','run','close']);p.add_argument('--spec',type=Path,default=ROOT/'campaign-spec.json');a=p.parse_args()
    if a.action=='run':
        b=S.Budget(a.spec);argv=b.spec['stages']['diagnose']['argv'];env=dict(os.environ,**b.spec['environment'])
        if str(Path(sys.executable).resolve())!=argv[0]or any(os.environ.get(k)!=v for k,v in b.spec['environment'].items()):os.execve(argv[0],argv,env)
    value=prepare()if a.action=='prepare'else S.Budget(a.spec).initialize(root_go=True)if a.action=='initialize'else stage(a)if a.action=='run'else close()
    print(json.dumps(value,indent=2,allow_nan=False))
if __name__=='__main__':main()
