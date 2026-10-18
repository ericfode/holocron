"""Fixed one-input HP projection, with fresh state cells and reserved card families."""
import argparse
import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE=Path(__file__).resolve().parent
ROOT=D.EXPERIMENTS/'real-ir-hp-projection-v1'
PRIOR=D.EXPERIMENTS/'real-ir-failure-diagnostic-v1'
OLD=D.EXPERIMENTS/'real-ir-transfer-v1'
CRATE=HERE/'real_ir_hp_projection_native_collector'
ENGINE=Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
ZERO=dict(native_applies=0,neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
SECONDS=dict(build=20.,native=30.,prep=10.,fit=60.,verify=10.)


def read(path):return json.loads(Path(path).read_text())


def prepare():
    import real_ir_hp_projection_plan as P
    S.require(not ROOT.exists(),'new canonical allocation only')
    prior=S.Budget(PRIOR/'campaign-spec.json');state=prior.inspect();closure=read(PRIOR/'experiment-closure.json')
    S.require(state['completed']==['diagnose']and not state['failures']and state['pending']is None
        and state['cumulative']==closure['cumulative']==dict(charged_native_applies=919,charged_seconds=296.9465001246426,observed_native_applies=None),'exact closed diagnostic parent required')
    S.require(closure['status']=='closed-saved-diagnostic','saved diagnosis must precede correction freeze')
    reservation_path=D.EXPERIMENTS/'real-ir-hp-fresh-reservation.json'
    reservation=read(reservation_path)
    S.require(reservation['status']=='reserved-no-new-outcomes' and reservation['reserved_codes']==['ASH_259','HMW_158','LOF_259','SOR_132'],'four future sources must remain reserved')
    plan=P.build(read(OLD/'metadata-1/native-plan.json'))
    ROOT.mkdir();metadata=ROOT/'metadata-1';metadata.mkdir();plan_pin=D.write_new(metadata/'native-plan.json',plan)
    parent=copy.deepcopy(prior.parent);parent['carry']=state['cumulative'];pins={p['path']:p for p in parent['pins']}
    for p in list(prior.frozen.values())+[S.pin(p)for p in PRIOR.rglob('*')if p.is_file()]:
        S.verify_pin(p);S.require(p['path']not in pins or pins[p['path']]==p,'immutable parent conflict');pins[p['path']]=p
    parent['pins']=[pins[k]for k in sorted(pins)];parent['protected_roots'].append(str(PRIOR));parent['closed_journals'].append(D.closed_journal(prior.ledger))
    pm=D.write_new(ROOT/'parent-manifest.json',parent)
    scientific=read(D.EXPERIMENTS/'compositional-typed-saved-v1/campaign-spec.json')
    py=scientific['stages']['fit']['argv'][0];stages={}
    for name,seconds in SECONDS.items():
        counts=dict(ZERO)
        if name=='native':counts['native_applies']=168
        if name=='fit':counts.update(neural_forwards=1815,backwards=1800,optimizer_updates=1800,numerical_fits=0)
        stages[name]=dict(argv=[py,str(Path(__file__).resolve()),'run','--stage',name,'--spec',str(ROOT/'campaign-spec.json')],
            outputs=[str(ROOT/(name+'-1')),str(ROOT/(name+'-1-stage-receipt.json'))],reservation=dict(seconds=seconds,**counts),
            expected=dict(counts,**({'native_applies':None}if name=='native'else{})),external_counters=['native_applies']if name=='native'else[])
    names=('real_ir_hp_projection_campaign.py','real_ir_hp_projection_plan.py','real_ir_hp_projection_data.py',
        'real_ir_hp_projection_model.py','real_ir_hp_projection_fit.py','real_ir_hp_projection_verify.py',
        'test_real_ir_hp_projection_plan.py','test_real_ir_hp_projection_data.py','test_real_ir_hp_projection_model.py',
        'test_real_ir_hp_projection_fit.py','test_real_ir_hp_projection_verify.py','REAL_IR_HP_PROJECTION_PROTOCOL.md',
        'effect_identifiability_fit.py','semantic_discrimination_native_collector/supervise_v2.py')
    files=[HERE/name for name in names]+[Path(py),Path('/Users/ericfode/.cargo/bin/cargo'),metadata/'native-plan.json',reservation_path]
    files +=[p for p in CRATE.rglob('*')if p.is_file()and '__pycache__'not in p.parts and 'target'not in p.parts]
    files +=[ENGINE/'Cargo.toml',ENGINE/'Cargo.lock']
    spec=dict(schema=S.SPEC_SCHEMA,status='sealed-awaiting-root-GO',source=S.pin(S.__file__),primitives=S.pin(S._PATH),parent_manifest=pm,
        ledger_path=str(ROOT/'campaign-ledger.jsonl'),caps=dict(seconds=130.,**dict(ZERO,native_applies=168,neural_forwards=1815,backwards=1800,optimizer_updates=1800,numerical_fits=0)),
        guard=dict(cpu_workers=1,rss_bytes=1024**3),stage_order=list(stages),stages=stages,pins=[S.pin(p)for p in sorted(set(files))],
        environment=scientific['environment'],financial=prior.spec['financial'],protocol=S.pin(HERE/'REAL_IR_HP_PROJECTION_PROTOCOL.md'),
        source_freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),prior_root=str(OLD),prelabel_reservation=S.pin(reservation_path),native_plan=plan_pin,
        scope='HP-only endpoint projection. Original TRAIN40 only; fresh state cells on seven exposed event IDs. Four fresh whenPlayed sources preserved untouched. No new card-family or deck-embedding qualification.')
    D.write_new(ROOT/'campaign-spec.json',spec);S.Budget(ROOT/'campaign-spec.json').verify();return S.pin(ROOT/'campaign-spec.json')


def native_worker():
    path=CRATE/'supervise.py';loader=importlib.util.spec_from_file_location('real_ir_transfer_owned_process',path)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module);return module


def stage(args):
    budget=S.Budget(args.spec);args.root=ROOT;args.plan=ROOT/'metadata-1/native-plan.json';args.out=ROOT/(args.stage+'-1')
    receipt_path=ROOT/(args.stage+'-1-stage-receipt.json')
    with budget.lease()as run:
        status='failed';guard=None;receipt=dict(stage=args.stage,cleanup_verified=True)
        try:
            descriptor=budget.spec['stages'][args.stage]
            run.begin(args.stage,argv=descriptor['argv'],guard=budget.spec['guard'],inputs=list(run.state['proofs'].values()))
            S.require([str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]==descriptor['argv']and args.spec.resolve()==ROOT/'campaign-spec.json','exact sealed runtime command required')
            S.require(all(os.environ.get(k)==v for k,v in budget.spec['environment'].items()),'exact sealed scientific environment required')
            receipt['source']=S.pin(__file__);args.out.mkdir();E=importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds())as guard:
                if args.stage in('build','native'):native_worker().worker(args,run,receipt)
                elif args.stage=='prep':
                    import numpy as np
                    C=importlib.import_module('real_ir_hp_projection_data')
                    arrays,manifest=C.prepare(np,OLD,ROOT)
                    np.savez_compressed(args.out/'dataset.npz',**arrays);D.write_new(args.out/'manifest.json',manifest)
                    S.require(manifest['fit_admitted'],'native/reference gate blocks learning: '+str(manifest['fit_blockers']))
                    receipt['reference']=manifest['reference'];receipt['support']=manifest['support']
                elif args.stage=='fit':
                    args.dataset=ROOT/'prep-1/dataset.npz';args.manifest=ROOT/'prep-1/manifest.json';args.prior=OLD
                    receipt['result']=importlib.import_module('real_ir_hp_projection_fit').worker(args,run)
                elif args.stage=='verify':
                    import numpy as np
                    receipt['verification']=importlib.import_module('real_ir_hp_projection_verify').verify(np,ROOT,args.out)
                else:raise ValueError('unallocated stage')
            status='completed'
        except BaseException as error:
            if run.state['pending']is None:raise
            receipt['error']=dict(type=type(error).__name__,message=str(error))
        receipt.update(status=status,guard=guard.receipt()if guard else None);rp=None
        try:rp=D.write_new(receipt_path,receipt)
        except BaseException as error:status='failed';receipt['receipt_write_error']=dict(type=type(error).__name__,message=str(error))
        if receipt.get('cleanup_verified')is not True:
            run.pending_failure('owned cleanup/execution not positively confirmed: '+str(receipt.get('error')))
            raise RuntimeError('owned execution status unresolved; retain full reservation and stop')
        proofs=[S.pin(p)for p in sorted(args.out.rglob('*'))if p.is_file()]+([rp]if rp else[])
        state=run.finish(status,proofs=proofs,cleanup_verified=True,execution_ended=True)
        S.require(status=='completed'and args.stage in state['completed'],'allocation failed; full reservation preserved: '+str(receipt.get('error')))
        return dict(stage=args.stage,receipt=rp,charged=state['charged'],cumulative=state['cumulative'])


def close():
    budget=S.Budget(ROOT/'campaign-spec.json');state=budget.inspect()
    S.require(state['completed']==budget.spec['stage_order']and not state['failures']and state['pending']is None,'all verified stages required')
    verified=read(ROOT/'verify-1/verification-result.json');fit=read(ROOT/'fit-1/result.json');data=read(ROOT/'prep-1/manifest.json')
    S.require(verified['verified']is True and data['fit_admitted']and data['reference']['mismatch_count']==0,'saved verification and native/reference exactness required')
    value=dict(schema='jepa-real-ir-hp-projection-closure/1',status='closed-verified-hp-projection',source_freeze_commit=budget.spec['source_freeze_commit'],
        prelabel_reservation=budget.spec['prelabel_reservation'],native_plan=budget.spec['native_plan'],native=S.pin(ROOT/'native-1/receipt.json'),
        data_manifest=S.pin(ROOT/'prep-1/manifest.json'),fit_result=S.pin(ROOT/'fit-1/result.json'),verification=S.pin(ROOT/'verify-1/verification-result.json'),
        decisions=fit['decisions'],reference=data['reference'],journal=S.pin(budget.ledger),final_chain=state['last_sha256'],
        new_charged=state['charged'],new_observed=state['observed'],cumulative=state['cumulative'],financial=budget.spec['financial'],
        production_changed=False,opponent_execution=False,card_conversion_run=False,generic_card_embedding_qualified=False,semantic_validated=False)
    return D.write_new(ROOT/'experiment-closure.json',value)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','initialize','run','status','close']);p.add_argument('--stage',choices=list(SECONDS));p.add_argument('--spec',type=Path,default=ROOT/'campaign-spec.json');a=p.parse_args()
    if a.action=='run':
        b=S.Budget(a.spec);argv=b.spec['stages'][a.stage]['argv'];env=dict(os.environ,**b.spec['environment'])
        if str(Path(sys.executable).resolve())!=argv[0]or any(os.environ.get(k)!=v for k,v in b.spec['environment'].items()):
            os.execve(argv[0],argv,env)  # Before lease/begin; no scientific import has occurred.
    value=prepare()if a.action=='prepare'else S.Budget(a.spec).initialize(root_go=True)if a.action=='initialize'else stage(a)if a.action=='run'else close()if a.action=='close'else S.Budget(a.spec).inspect();print(json.dumps(value,indent=2,allow_nan=False))
if __name__=='__main__':main()
