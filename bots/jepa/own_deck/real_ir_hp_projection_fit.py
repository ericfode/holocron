"""Matched HP-input projection fit. Import is stdlib; ROOT owns guard and ledger.

Only worker(args, run) imports numerical libraries or constructs models. All
evaluation forwards, including initial checkpoints, follow all 1,800 updates.
"""
import hashlib
import json
import math
import os
from pathlib import Path

SEEDS=(17,29,43)
ARMS=('baseline','effect-hp-invariant')
CONFIG=dict(seeds=list(SEEDS),arms=list(ARMS),updates_per_arm=300,
    training_forwards=1800,evaluation_forwards=15,neural_forwards=1815,
    backwards=1800,optimizer_updates=1800,numerical_fits=0,
    learning_rate=.003,weight_decay=.0001,clip_l2=1.,
    eligibility_loss_coefficient=.5,endpoint_loss_coefficient=.5,endpoint_huber_beta=1.,
    hyperparameter_search=False,statistics='Exact frozen PR45 TRAIN loss-weights.json; zero new statistics fits.')


def require(ok,message):
    if not ok:raise ValueError(message)


def mean(values):return sum(values)/len(values) if values else None


def raw_metrics(predictions,labels,masks,metadata,rows):
    """Algebra on saved routed delta/p at actual known intended endpoints only."""
    points=[];undefined=[]
    for i in rows:
        for q,(pred,truth,mask) in enumerate(zip(predictions[i],labels[i],masks[i])):
            if not mask[1]:continue
            require(truth[0]==1.,'raw oracle eligibility requires an actually allowed committed endpoint')
            p,delta=map(float,pred);require(math.isfinite(p)and math.isfinite(delta)and 0<=p<=1,'finite probability/delta required')
            if p==0.:undefined.append([int(i),q]);continue
            raw=delta/p;require(math.isfinite(raw),'conditional output overflow')
            require(raw==delta==0. or raw*delta>0.,'positive eligibility cannot change effect sign')
            m=metadata[i];points.append(dict(root=int(i),candidate=q,truth=float(truth[1]),prediction=raw,
                routed_prediction=delta,eligibility_probability=p,error=abs(raw-float(truth[1])),
                operator=m['operator'],domain=m['intent_domain'],
                healthy=bool(m['healthy_intent'])and m['operator']=='heal',division_near_zero=p<1e-6))
    groups={'pooled':points}
    groups.update({v:[p for p in points if p['domain']==v]for v in('unit','base')})
    groups.update({v:[p for p in points if p['operator']==v]for v in('damage','heal')})
    nz=[p for p in points if p['truth']!=0.];healthy=[p for p in points if p['healthy']]
    return dict(endpoint_mae={k:mean([p['error']for p in v])for k,v in groups.items()},
        endpoint_support={k:len(v)for k,v in groups.items()},undefined=undefined,
        nonzero_sign_accuracy=mean([float(p['truth']*p['prediction']>0.)for p in nz]),
        healthy_max_abs=max((abs(p['prediction'])for p in healthy),default=None),endpoints=points,
        scope='Float32 saved delta/p oracle-eligibility arithmetic, not a new neural prediction or retained preactivation; p=0 remains undefined.')


def usability(metrics):
    mae=all(v is not None and v<=.25 for v in metrics['endpoint_mae'].values())
    sign=metrics['nonzero_sign_accuracy']is not None and metrics['nonzero_sign_accuracy']>=.95
    healthy=metrics['healthy_count']>0 and metrics['healthy_max_abs']<=.1
    recall=metrics['eligibility']['positive_recall']is not None and metrics['eligibility']['positive_recall']>=.95
    return dict(endpoint_slices_passed=mae,nonzero_sign_passed=sign,healthy_max_abs_passed=healthy,
        positive_recall_descriptive_passed=recall,usable_endpoint_gate_passed=mae and sign and healthy and recall,
        eligibility_discrimination_qualified=False)


def decisions(results):
    panel={}
    for seed in SEEDS:
        base=results[f's{seed}:baseline']['evaluations']['300']
        candidate=results[f's{seed}:effect-hp-invariant']['evaluations']['300']
        a,b=candidate['fresh_primary']['raw'],base['fresh_primary']['raw']
        mae=all(v is not None and v<=.25 for v in a['endpoint_mae'].values())and not a['undefined']
        sign=a['nonzero_sign_accuracy']is not None and a['nonzero_sign_accuracy']>=.95
        av,bv=a['endpoint_mae']['pooled'],b['endpoint_mae']['pooled']
        improvement=1-av/bv if av is not None and bv is not None and bv>0 else None
        train=candidate['train']['routed']['endpoint_mae']['pooled'];control=base['train']['routed']['endpoint_mae']['pooled']
        nonregression=train is not None and control is not None and train<=control+.05
        passed=mae and sign and improvement is not None and improvement>=.2 and nonregression
        panel[str(seed)]=dict(raw_endpoint_slices_passed=mae,raw_nonzero_sign_passed=sign,
            relative_raw_mae_improvement=improvement,raw_improvement_passed=improvement is not None and improvement>=.2,
            train_routed_nonregression=nonregression,primary_passed=passed,
            old_dev_original_usability={arm:usability(results[f's{seed}:{arm}']['evaluations']['300']['old_dev']['routed'])for arm in ARMS})
    return dict(per_seed=panel,primary_passed=all(p['primary_passed']for p in panel.values()),
        thresholds=dict(raw_mae_max=.25,raw_nonzero_sign_min=.95,raw_relative_improvement_min=.2,train_routed_mae_allowance=.05),
        scope='Fresh nonreplay30 known endpoints are primary; replay9 and exposed olddev16 are separate. Oracle-eligibility raw gate and original fully routed usability are different decisions.',
        semantic_validated=False)


def worker(args,run):
    """ROOT invokes inside its active one-CPU/1GiB guard and durable reservation."""
    require(run.state.get('pending')is not None and run.remaining_seconds()>0,'active sealed fit stage required')
    import numpy as np
    import torch
    import sys
    import real_ir_transfer_fit as F
    import real_ir_hp_projection_model as H
    torch.set_num_threads(1)
    out=Path(args.out);prior=Path(args.prior)
    require(out.is_dir()and not any(out.iterdir()),'existing empty declared fit directory required')
    manifest=json.loads(Path(args.manifest).read_text());weights=json.loads((prior/'fit-1/loss-weights.json').read_text())
    require(manifest['schema']=='jepa-real-ir-hp-projection-data/1'and manifest['fit_admitted']is True,'new native/reference admission required before training')
    require(not manifest['fit_blockers']and all(manifest[k]['known_coordinates']==375 and
        manifest[k]['known_eligibility']==336 and manifest[k]['known_intended_deltas']==39 and
        manifest[k]['mismatch_count']==0 for k in('reference','old_reference')),
        'both complete375-coordinate native/reference checks must pass before fit')
    require(manifest['support']==dict(fresh_known_endpoints=39,primary=30,replay=9),'fixed fresh/replay endpoint support required')
    require(manifest['old_loss_weights']==weights,'only exact old TRAIN loss weights may be reused')
    with np.load(args.dataset,allow_pickle=False)as h:a={k:h[k]for k in h.files}
    with np.load(prior/'prep-1/dataset.npz',allow_pickle=False)as h:old={k:h[k]for k in h.files}
    for key in('program_features','source_printed_features'):
        require(a[key].dtype==old[key].dtype==np.float32 and np.array_equal(a[key],old[key]),'frozen program/printed banks differ: '+key)
    for key in('candidate_features','targets','target_mask','program_indices'):
        require(np.array_equal(a[key][:56],old[key]),'old rows must be byte-identical: '+key)
    for key in('candidate_features','targets','target_mask','primary_target_mask','replay_target_mask'):
        require(a[key].shape==((112,6,17)if key=='candidate_features'else(112,6,2))and a[key].dtype==np.float32 and np.isfinite(a[key]).all(),'exact finite combined ABI: '+key)
    expected={'train_idx':list(range(40)),'old_dev_idx':list(range(40,56)),
              'old_all_idx':list(range(56)),'fresh_all_idx':list(range(56,112))}
    for key,value in expected.items():require(a[key].dtype==np.int64 and a[key].tolist()==value,'frozen root partition: '+key)
    require(np.isin(a['target_mask'],[0.,1.]).all()and np.isin(a['primary_target_mask'],[0.,1.]).all()and
        np.isin(a['replay_target_mask'],[0.,1.]).all(),'explicit known masks required')
    require(a['primary_target_mask'][...,0].sum()==a['replay_target_mask'][...,0].sum()==0 and
        a['primary_target_mask'][...,1].sum()==30 and a['replay_target_mask'][...,1].sum()==9 and
        not a['primary_target_mask'][:56].any()and not a['replay_target_mask'][:56].any()and
        not (a['primary_target_mask']*a['replay_target_mask']).any()and
        (a['primary_target_mask']<=a['target_mask']).all()and(a['replay_target_mask']<=a['target_mask']).all(),
        'fresh primary/replay masks must preserve native unknowns')
    require(a['baseline_predictions'].shape==(112,6,2)and np.isfinite(a['baseline_predictions']).all()and
        np.array_equal(a['baseline_predictions'][a['target_mask']>0],a['targets'][a['target_mask']>0]),
        'all co-known old/fresh native-reference coordinates must be exact before fit')
    metadata=manifest['root_metadata'];require(len(metadata)==112,'combined public metadata required')
    require(np.array_equal(a['train_idx'],old['train_idx']),'TRAIN update order must equal the frozen old order')
    labels=a['targets'].tolist();masks=a['target_mask'].tolist();train=a['train_idx'];index=a['program_indices']
    require(index.shape==(112,)and index.dtype==np.int64 and index.min()>=0 and index.max()<7,'program lookup indices only')
    p=torch.from_numpy(a['program_features'][index]);c=torch.from_numpy(a['candidate_features']);s=torch.from_numpy(a['source_printed_features'][index])
    y=torch.from_numpy(a['targets']);mask=torch.from_numpy(a['target_mask']);ix=torch.from_numpy(train)
    cw=torch.tensor(weights['class_statistics']['weights'],dtype=torch.float32)
    sw=weights['stratum_statistics']['weights']
    ew=torch.tensor([sw.get(m['operator']+'|'+m['intent_domain'],0.)for m in metadata],dtype=torch.float32)[:,None]
    F.write(out/'loss-weights.json',weights)
    np.savez_compressed(out/'consumed-inputs.npz',**{k:a[k]for k in('program_features','source_printed_features','candidate_features','program_indices','train_idx','old_dev_idx','old_all_idx','fresh_all_idx')})
    np.savez_compressed(out/'training-schedule.npz',train_indices=train,seeds=np.asarray(SEEDS),arms=np.asarray(ARMS),updates=np.arange(1,301))
    def pin(path):
        path=Path(path);raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    inputs=[Path(args.dataset),Path(args.manifest),prior/'prep-1/dataset.npz',prior/'fit-1/loss-weights.json',Path(F.__file__),Path(H.__file__),Path(H.M.__file__),Path(__file__)]
    inputs +=[prior/'fit-1'/f's{seed}-{name}.npz'for seed in SEEDS for name in('new-full-initial-checkpoint','new-full-checkpoint','new-printed-only-checkpoint')]
    F.write(out/'input-pins.json',[pin(path)for path in inputs])
    F.write(out/'contract.json',dict(config=CONFIG,model=H.contract(),runtime=dict(python_version=sys.version,python_executable=str(Path(sys.executable).resolve()),
        numpy_version=np.__version__,torch_version=str(torch.__version__),numpy_path=str(Path(np.__file__).resolve()),torch_path=str(Path(torch.__file__).resolve())),
        held_policy='Every initial/final/printed evaluation is deferred until all1800updates finish.',
        objective='Exact frozen PR45 fullTRAIN loss/weights; full native target_mask for TRAIN, fresh primary mask only for scoring.',semantic_validated=False))
    counts=dict(neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0);models={};initials={};results={}
    def arrays(model):return{k:v.detach().cpu().numpy().copy()for k,v in model.state_dict().items()}
    def load(path):
        with np.load(path,allow_pickle=False)as h:return{k:torch.from_numpy(h[k].copy())for k in h.files}
    def forward(model,pp,cc,ss):
        token=run.intent('neural_forwards');value=model(pp,cc,ss);run.complete(token);counts['neural_forwards']+=1
        require(all(torch.isfinite(v).all().item()for v in value.values()),'finite predictions required');return value
    with (out/'fit-progress.jsonl').open('x')as log:
        for seed in SEEDS:
            initial=load(prior/'fit-1'/f's{seed}-new-full-initial-checkpoint.npz')
            old_initial_hash=F.state_hash({k:v.numpy()for k,v in initial.items()})
            for arm in ARMS:
                torch.manual_seed(seed);model=H.make_model(torch,arm);model.load_state_dict(initial,strict=True)
                state=arrays(model);initials[(seed,arm)]=state;models[(seed,arm)]=model
                require(F.state_hash(state)==old_initial_hash,'both arms must load the complete old initial checkpoint')
                np.savez_compressed(out/f's{seed}-{arm}-initial-checkpoint.npz',**state)
                results[f's{seed}:{arm}']=dict(initial_state_sha256=F.state_hash(state),old_initial_state_sha256=old_initial_hash,evaluations={},losses=[])
                optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001)
                for update in range(1,301):
                    optimizer.zero_grad(set_to_none=True);pred=forward(model,p[ix],c[ix],s[ix])
                    binary=torch.nn.functional.binary_cross_entropy_with_logits(pred['eligibility_logits'],y[ix,:,0],reduction='none')
                    w=cw[y[ix,:,0].long()]*mask[ix,:,0]
                    eligibility=((binary*w).sum(1)/mask[ix,:,0].sum(1).clamp_min(1)).mean()
                    distance=torch.nn.functional.smooth_l1_loss(pred['signed_damage'],y[ix,:,1],reduction='none',beta=1.)
                    endpoint=(distance*mask[ix,:,1]*ew[ix]).sum()/mask[ix,:,1].sum().clamp_min(1)
                    loss=.5*eligibility+.5*endpoint;require(torch.isfinite(loss).item(),'finite loss before backward')
                    token=run.intent('backwards');loss.backward();run.complete(token);counts['backwards']+=1
                    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.);require(torch.isfinite(norm).item(),'finite gradient before update')
                    token=run.intent('optimizer_updates');optimizer.step();run.complete(token);counts['optimizer_updates']+=1
                    row=dict(seed=seed,arm=arm,update=update,loss=float(loss.item()),eligibility_loss=float(eligibility.item()),endpoint_loss=float(endpoint.item()),preclip_gradient_l2=float(norm.item()))
                    log.write(json.dumps(row,allow_nan=False)+'\n');log.flush();os.fsync(log.fileno())
                    results[f's{seed}:{arm}']['losses'].append(row['loss'])
                state=arrays(model);results[f's{seed}:{arm}']['final_state_sha256']=F.state_hash(state)
                np.savez_compressed(out/f's{seed}-{arm}-checkpoint.npz',**state)
                if arm=='baseline':
                    oldfinal=load(prior/'fit-1'/f's{seed}-new-full-checkpoint.npz')
                    require(set(state)==set(oldfinal)and all(np.array_equal(state[k],oldfinal[k].numpy())for k in state),'baseline must reproduce frozen final checkpoint exactly')
                    results[f's{seed}:{arm}']['old_final_checkpoint_exact']=True
    require(counts['optimizer_updates']==1800,'all updates must precede every evaluation forward')
    def panels(pred):
        result={};values=pred.tolist()
        for name,rows,pmask in(('train',train,masks),('old_dev',a['old_dev_idx'],masks),('fresh_all',a['fresh_all_idx'],masks),
            ('fresh_primary',a['fresh_all_idx'],a['primary_target_mask'].tolist()),('fresh_replay',a['fresh_all_idx'],a['replay_target_mask'].tolist())):
            result[name]=dict(routed=F.evaluate(values,labels,pmask,metadata,rows.tolist()),raw=raw_metrics(values,labels,pmask,metadata,rows.tolist()))
        return result
    def evaluate(model,seed,arm,step):
        model.eval()
        with torch.no_grad():value=forward(model,p,c,s)
        logits=value['eligibility_logits'].cpu().numpy();prob=torch.sigmoid(value['eligibility_logits']).cpu().numpy()
        pred=np.stack((prob,value['signed_damage'].cpu().numpy()),axis=-1)
        np.savez_compressed(out/f's{seed}-{arm}-step{step}-predictions.npz',predictions=pred,eligibility_logits=logits,program_indices=index)
        return panels(pred)
    for seed in SEEDS:
        for arm in ARMS:
            model=models[(seed,arm)];final={k:v.detach().clone()for k,v in model.state_dict().items()}
            for step,state in((0,{k:torch.from_numpy(v)for k,v in initials[(seed,arm)].items()}),(300,final)):
                model.load_state_dict(state,strict=True);results[f's{seed}:{arm}']['evaluations'][str(step)]=evaluate(model,seed,arm,step)
        model=H.M.make_model(torch,'new-printed-only');model.load_state_dict(load(prior/'fit-1'/f's{seed}-new-printed-only-checkpoint.npz'),strict=True)
        results[f's{seed}:old-printed-only']=dict(frozen_checkpoint=pin(prior/'fit-1'/f's{seed}-new-printed-only-checkpoint.npz'),evaluations={'300':evaluate(model,seed,'old-printed-only',300)})
    require(counts==dict(neural_forwards=1815,backwards=1800,optimizer_updates=1800,numerical_fits=0),'exact bounded counter plan required')
    baselines={}
    for name,pred in(('deterministic-reference',a['baseline_predictions']),
        ('all-ones-eligibility-zero-effect',np.stack((np.ones((112,6),np.float32),np.zeros((112,6),np.float32)),axis=-1))):
        np.savez_compressed(out/f'{name}-predictions.npz',predictions=pred,program_indices=index)
        baselines[name]=panels(pred)
    result=dict(schema='jepa-real-ir-hp-projection-fit/1',config=CONFIG,counts=counts,results=results,decisions=decisions(results),
        baseline_evaluations=baselines,
        native_applies=0,paid_jobs=0,semantic_validated=False,baseline_reproduction='All3 baseline final named checkpoints exactly equal frozen PR45 arrays.',
        limitation='Same seven exposed programs; new states, not fresh card families. Healing amounts2/5 both clip at damage1/2, so this grid cannot distinguish those healing literals. Fixed HP dependency projection does not validate whole-card semantics or eligibility discrimination.')
    F.write(out/'result.json',result);return dict(result_path=str(out/'result.json'),counts=counts,semantic_validated=False)
