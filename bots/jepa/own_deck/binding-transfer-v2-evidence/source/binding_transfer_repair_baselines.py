"""One separately guarded zero/TRAIN-mean/fixed-ridge stage; no neural imports.

Four public C/R designs, sixteen head-fit attempts each, lambda1 and an
unpenalized intercept. Actual solver calls and unsupported head slots are saved.
"""
import os
for _key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import argparse
import json
from pathlib import Path
import sys
import time

import binding_transfer_fit as F

CONFIG=dict(input_cells=list(F.MAIN),ridge_lambda=1.,intercept_penalized=False,head_fit_attempts=64,max_solver_calls=64,
    source_columns=80,branch_columns=80,train_id_columns=5,feature_scale='Common C1R1 TRAIN transforms; ablate after normalization; IDs unscaled',
    objective='SUM original relative TRAIN sign/root weights times squared normalized residual + lambda1 squared slopes',
    neural_forwards=0,native_applies=0,optimizer_updates=0,seconds=5.,cpu_workers=1,rss_bytes=1073741824,paid_jobs=0)


def features(arrays,manifest,plan,arm):
    import numpy as np
    x,c=F.projected_arrays(arrays,manifest,plan['scalers'],arm);ids=np.zeros((len(x),len(plan['train_codes'])),np.float64)
    for i,code in enumerate(arrays['source_cards'].astype(str)):
        if code in plan['train_codes']:ids[i,plan['train_codes'].index(code)]=1
    selected=arrays['selected_candidate_indices'];source=np.concatenate((x,c[np.arange(len(x)),selected],ids),-1)
    branch=np.concatenate((np.broadcast_to(x[:,None,:],(*c.shape[:2],x.shape[-1])),c,np.broadcast_to(ids[:,None,:],(*c.shape[:2],ids.shape[-1]))),-1)
    if source.shape[-1]!=80 or branch.shape[-1]!=80:raise ValueError('fixed32+43+5 public/identity ridge columns required')
    return source.astype(np.float64),branch.astype(np.float64)


def constants(arrays,train):
    import numpy as np
    mean=[]
    for key,mkey in(('source_targets','source_mask'),('targets','target_mask')):
        values=[]
        for h in range(arrays[key].shape[-1]):
            known=arrays[key][train,...,h][arrays[mkey][train,...,h]>0];values.append(float(known.mean())if len(known)else 0.)
        mean.append(np.broadcast_to(np.asarray(values,np.float32),arrays[key].shape).copy())
    return dict(zero=(np.zeros_like(arrays['source_targets']),np.zeros_like(arrays['targets'])),train_mean=tuple(mean))


def run(plan_path,out,progress):
    A=F.accounting()
    with A.lease()as(stream,rows,current):
        metadata,expected_plan,stage_receipt=F.stage_metadata(current,rows,plan_path,out,progress,__file__)
        guard=F.E.Guard(5.);start=time.monotonic();status='failed';error=None;attempts=0;solver_calls=0;created_out=False
        try:
            A.start(stream,rows,'baselines',metadata)
            if expected_plan is None:raise ValueError('sealed plan is not a frozen or completed-preparation proof')
            plan=F.read(plan_path);F.E.verify_pins(plan['pins'])
            if plan['status']!='sealed-awaiting-root-GO'or plan['source_sha256']!=F.sha(F.__file__)or plan['config']!=F.CONFIG:raise ValueError('exact sealed learner plan required')
            if out.exists()or progress.exists()or stage_receipt.exists():raise FileExistsError('baseline attempts retained; no retry/reset')
            out.mkdir(parents=True);created_out=True;remaining=5.-(time.monotonic()-start)
            if remaining<=0:raise RuntimeError('baseline startup exhausted its stage reservation')
            guard=F.E.Guard(remaining)
            with guard:
                import numpy as np
                import learning_sanity_data as R
                with np.load(plan['dataset'],allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
                manifest=F.read(plan['manifest']);parts=F.validate_data(arrays,manifest,plan);train=parts['train'];evaluations={};fits={}
                hashes={k:F.sha_array(arrays[k])for k in('targets','target_mask','source_targets','source_mask','selected_candidate_indices')}
                for name,(source,branch)in constants(arrays,train).items():
                    evaluations[name]=dict(cells=F.evaluate(source,branch,arrays,manifest,plan),narrow_estimands=F.narrow_estimands(source,branch,arrays,manifest,plan))
                    np.savez_compressed(out/(name+'-predictions.npz'),source=source,branch=branch)
                for arm in F.MAIN:
                    sx,bx=features(arrays,manifest,plan,arm);predictions=[];raw_predictions=[];arm_fits={}
                    for x,key,mkey in((sx,'source_targets','source_mask'),(bx,'targets','target_mask')):
                        output=np.zeros_like(arrays[key],np.float64);raw=np.zeros_like(output)
                        for h,spec in enumerate(plan['scalers'][key]):
                            attempts+=1
                            if attempts>64:raise ValueError('fixed64 head-fit attempts exceeded')
                            F.E.append_journal(progress,dict(event='numerical-fit-intent',global_fit=attempts,arm=arm,head=spec['name'],ridge_lambda=1.))
                            prediction,native,fit=R.fit_head(x,arrays[key][...,h],arrays[mkey][...,h],spec,train)
                            solver_calls+=int(fit['status']=='fitted-fixed-lambda');output[...,h]=prediction;raw[...,h]=native;arm_fits[spec['name']]=fit
                        predictions.append(output);raw_predictions.append(raw)
                    source,branch=predictions;evaluations[arm]=dict(cells=F.evaluate(source,branch,arrays,manifest,plan),narrow_estimands=F.narrow_estimands(source,branch,arrays,manifest,plan));fits[arm]=arm_fits
                    np.savez_compressed(out/(arm+'-predictions.npz'),source=source,branch=branch,raw_source=raw_predictions[0],raw_branch=raw_predictions[1],source_design=sx,branch_design=bx)
                if attempts!=64 or hashes!={k:F.sha_array(arrays[k])for k in hashes}:raise ValueError('baseline quota or immutable labels changed')
                F.E.verify_pins(plan['pins']);F.write(out/'result.json',dict(status='completed',config=CONFIG,evaluations=evaluations,fits=fits,
                    head_fit_attempts=attempts,actual_lstsq_solver_calls=solver_calls,unsupported_head_slots=attempts-solver_calls,
                    original_label_hashes=hashes,semantic_validated=False,card_information='TRAIN-only ID one-hot; held IDs allzero. No typed-program/literal oracle in ridge.',
                    source=F.pin(__file__),plan=F.pin(plan_path),task=F.CONFIG['task']))
            status='completed'
        except BaseException as exc:
            pending=A.state(rows)['pending']
            if pending is None or pending['stage']!='baselines'or pending['owner_pid']!=os.getpid():raise
            error=dict(type=type(exc).__name__,message=str(exc))
        elapsed=time.monotonic()-start
        if elapsed>5:status='failed';error=error or dict(type='BudgetExceeded',message='owned baseline stage exceeded5seconds')
        observed=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=attempts if status=='completed'else None,paid_jobs=0,paid_spend_usd=0.)
        artifact_pins=[F.pin(p)for p in sorted(out.rglob('*'))if p.is_file()]if created_out else[]
        receipt=dict(status=status,error=error,active_seconds=elapsed,observed=observed,known_head_fit_intents=attempts,actual_lstsq_solver_calls=solver_calls,artifact_pins=artifact_pins,guard=guard.receipt(),semantic_validated=False)
        try:
            A.verify_output_protection([str(stage_receipt.resolve())]);receipt_pin=F.save_stage_receipt(stage_receipt,out,receipt,copy_into_out=created_out)
        except BaseException as exc:
            receipt_pin=None;status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True);observed['numerical_fits']=None
        proofs=([receipt_pin]if receipt_pin else[])+([F.pin(progress)]if created_out and progress.exists()else[])+([F.pin(p)for p in sorted(out.rglob('*'))if p.is_file()]if created_out else[])
        finished=A.finish(stream,rows,status,elapsed,observed=observed,proofs=proofs,cleanup_verified=True,execution_ended=True,counter_proof=F.success_counter_proof(status,progress))
        if status!='completed'or 'baselines'not in finished['completed_stages']:raise RuntimeError('failed bounded baseline stage retained; ledger status controls completion: '+str(error))
        return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--progress',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.plan,a.out,a.progress),indent=2))

if __name__=='__main__':main()
