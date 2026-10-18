"""Once-only zero-outcome adapter coverage and holdout-reservation allocation."""
import argparse
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE=Path(__file__).resolve().parent
ROOT=D.EXPERIMENTS/'real-ir-coverage-v3'
PRIOR=D.EXPERIMENTS/'real-ir-coverage-v2'
ZERO=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)


def read(path):return json.loads(Path(path).read_text())


def prepare():
    import real_ir_reservation_v3 as R
    S.require(not ROOT.exists(),'new canonical campaign only')
    prior=S.Budget(PRIOR/'campaign-spec.json');state=prior.inspect();closure=read(PRIOR/'experiment-closure.json')
    S.require(state['completed']==[]and state['failures']==1 and state['pending']is None
        and state['charged']['seconds']==10. and state['cumulative']==closure['cumulative']==dict(charged_native_applies=807,charged_seconds=278.03031941584777,observed_native_applies=None),'exact failed parent charge retained')
    S.require(closure['status']=='closed-failed-before-outcomes'and state['charged']['native_applies']==state['charged']['neural_forwards']==state['charged']['numerical_fits']==0,'metadata-only failure required')
    ROOT.mkdir();parent=copy.deepcopy(prior.parent);parent['carry']=state['cumulative'];pins={p['path']:p for p in parent['pins']}
    for p in list(prior.frozen.values())+[S.pin(p)for p in PRIOR.rglob('*')if p.is_file()]:
        S.verify_pin(p);S.require(p['path']not in pins or pins[p['path']]==p,'conflicting protected bytes');pins[p['path']]=p
    preflight=D.EXPERIMENTS/'real-ir-coverage-v1';unstarted=S.Budget(preflight/'campaign-spec.json')
    S.require(unstarted.inspect().get('ledger_initialized')is False,'preflight allocation must never have started')
    for q in list(unstarted.frozen.values())+[S.pin(q)for q in preflight.rglob('*')if q.is_file()]:
        S.verify_pin(q);S.require(q['path']not in pins or pins[q['path']]==q,'preflight immutable pin conflict');pins[q['path']]=q
    parent['protected_roots'].append(str(preflight))
    parent['pins']=[pins[k]for k in sorted(pins)];parent['closed_journals'].append(D.closed_journal(prior.ledger));parent['protected_roots'].append(str(PRIOR))
    pm=D.write_new(ROOT/'parent-manifest.json',parent);py=str(Path(sys.executable).resolve());stages={}
    for name in('coverage','verify'):
        stages[name]=dict(argv=[py,str(Path(__file__).resolve()),'run','--stage',name,'--spec',str(ROOT/'campaign-spec.json')],
            outputs=[str(ROOT/(name+'-1')),str(ROOT/(name+'-1-stage-receipt.json'))],reservation=dict(seconds=5.,**ZERO),expected=dict(ZERO),external_counters=[])
    files=[HERE/n for n in('real_ir_adapter.py','real_ir_adapter_fixtures.json','test_real_ir_adapter.py','real_ir_reservation_v3.py','test_real_ir_reservation_v3.py',
        'real_ir_coverage_v3.py','real_ir_coverage_campaign_v3.py','REAL_IR_ADAPTER_PROTOCOL.md','REAL_IR_ADAPTER_RECOVERY.md','effect_identifiability_fit.py')]
    files +=[R.CATALOGUE,R.RUNTIME,R.COVERAGE,Path(py),*R.source_paths(),R.EXP/'grounded-contrast/inventory.json',
        R.EXP/'compositional-actual-admission-v1/audit-1/admission-report.json',HERE/'TRANSFER_ATTRIBUTION_DESIGN_REVIEW.md']
    spec=dict(schema=S.SPEC_SCHEMA,status='sealed-awaiting-root-GO',source=S.pin(S.__file__),primitives=S.pin(S._PATH),parent_manifest=pm,
        ledger_path=str(ROOT/'campaign-ledger.jsonl'),caps=dict(seconds=10.,**ZERO),guard=dict(cpu_workers=1,rss_bytes=1024**3),stage_order=list(stages),stages=stages,
        pins=[S.pin(p)for p in sorted(set(files))],environment=prior.spec['environment'],financial=prior.spec['financial'],
        source_freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
        scope='Full fixed2458/1178 adapter/card/copy coverage and prelabel alias/family reservation. No outcome collection or neural work allocated.')
    D.write_new(ROOT/'campaign-spec.json',spec);S.Budget(ROOT/'campaign-spec.json').verify();return S.pin(ROOT/'campaign-spec.json')


def stage(args):
    budget=S.Budget(args.spec);out=ROOT/(args.stage+'-1');receipt_path=ROOT/(args.stage+'-1-stage-receipt.json')
    with budget.lease()as run:
        status='failed';guard=None;receipt=dict(stage=args.stage,cleanup_verified=True)
        try:
            descriptor=budget.spec['stages'][args.stage]
            run.begin(args.stage,argv=descriptor['argv'],guard=budget.spec['guard'],inputs=list(run.state['proofs'].values()))
            S.require([str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]==descriptor['argv']and args.spec.resolve()==ROOT/'campaign-spec.json','exact sealed command')
            receipt['source']=S.pin(__file__);out.mkdir();E=importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds())as guard:
                C=importlib.import_module('real_ir_coverage_v3')
                if args.stage=='coverage':
                    report=C.coverage();receipt['report']=D.write_new(out/'coverage-report.json',report)
                    receipt['catalogue']=report['catalogue'];receipt['runtime']=report['runtime'];receipt['main_corpus']=report['main_corpus']
                    reservation=C.reserve();receipt['reservation']=D.write_new(out/'holdout-reservation.json',reservation)
                elif args.stage=='verify':
                    result=C.verify(ROOT/'coverage-1/coverage-report.json',ROOT/'coverage-1/holdout-reservation.json')
                    receipt['verification']=D.write_new(out/'verification-result.json',result)
                else:raise ValueError('unallocated stage')
            status='completed'
        except BaseException as error:
            if run.state['pending']is None:raise
            receipt['error']=dict(type=type(error).__name__,message=str(error))
        receipt.update(status=status,guard=guard.receipt()if guard else None);rp=None
        try:rp=D.write_new(receipt_path,receipt)
        except BaseException as error:status='failed';receipt['receipt_write_error']=dict(type=type(error).__name__,message=str(error))
        proofs=[S.pin(p)for p in sorted(out.rglob('*'))if p.is_file()]+([rp]if rp else[])
        state=run.finish(status,proofs=proofs,cleanup_verified=True,execution_ended=True)
        S.require(status=='completed'and args.stage in state['completed'],'coverage allocation failed; full reservation retained: '+str(receipt.get('error')))
        return dict(stage=args.stage,receipt=rp,cumulative=state['cumulative'])


def close():
    budget=S.Budget(ROOT/'campaign-spec.json');state=budget.inspect()
    S.require(state['completed']==budget.spec['stage_order']and not state['failures']and state['pending']is None,'closed verified stages required')
    report=read(ROOT/'coverage-1/coverage-report.json');reserved=read(ROOT/'coverage-1/holdout-reservation.json');verified=read(ROOT/'verify-1/verification-result.json')
    S.require(verified['verified']and reserved['status']=='metadata-reserved-no-outcomes','prelabel reservation/verification required')
    return D.write_new(ROOT/'experiment-closure.json',dict(schema='jepa-real-ir-coverage-closure/1',status='closed-verified-coverage-and-reservation',
        source_freeze_commit=budget.spec['source_freeze_commit'],report=S.pin(ROOT/'coverage-1/coverage-report.json'),reservation=S.pin(ROOT/'coverage-1/holdout-reservation.json'),
        verification=S.pin(ROOT/'verify-1/verification-result.json'),journal=S.pin(budget.ledger),final_chain=state['last_sha256'],
        catalogue=report['catalogue'],runtime=report['runtime'],main_corpus=report['main_corpus'],new_charged=state['charged'],cumulative=state['cumulative'],
        financial=budget.spec['financial'],production_changed=False,outcomes_collected=False,learned_vector_claim=False,
        original_failed_charge_seconds=10.,combined_new_charged_seconds=10.+state['charged']['seconds'],combined_new_seconds_ceiling=20.))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','initialize','run','status','close']);p.add_argument('--stage',choices=['coverage','verify']);p.add_argument('--spec',type=Path,default=ROOT/'campaign-spec.json');a=p.parse_args()
    value=prepare()if a.action=='prepare'else S.Budget(a.spec).initialize(root_go=True)if a.action=='initialize'else stage(a)if a.action=='run'else close()if a.action=='close'else S.Budget(a.spec).inspect();print(json.dumps(value,indent=2,allow_nan=False))
if __name__=='__main__':main()
