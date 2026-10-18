"""Source-only fixed real-event comparison; no imports with numerical effects.

The ROOT campaign calls worker(args, run) INSIDE its already active time/RSS
guard and durable fit reservation. args.dataset/manifest are frozen prep files;
args.out is its existing empty output directory. No standalone unguarded CLI.
"""
import hashlib
import json
import math
import os
from pathlib import Path

SEEDS = (17, 29, 43)
ARMS = ('new-full', 'old-late-fusion', 'new-printed-only')
CONFIG = dict(seeds=list(SEEDS), arms=list(ARMS), updates_per_arm=300,
    training_forwards=2700, evaluation_forwards=18, neural_forwards=2718,
    backwards=2700, optimizer_updates=2700, numerical_fits=2,
    learning_rate=.003, weight_decay=.0001, clip_l2=1.,
    eligibility_loss_coefficient=.5, endpoint_loss_coefficient=.5,
    endpoint_huber_beta=1., fixed_physics=True, hyperparameter_search=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def native(value):
    if isinstance(value, dict): return {str(k): native(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [native(v) for v in value]
    if hasattr(value, 'tolist'): return native(value.tolist())
    if hasattr(value, 'item'): return native(value.item())
    return value


def write(path, value):
    raw=(json.dumps(native(value),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as f: f.write(raw);f.flush();os.fsync(f.fileno())


def sha_array(array):
    return hashlib.sha256(str(array.dtype).encode()+str(array.shape).encode()+array.tobytes(order='C')).hexdigest()


def state_hash(state):
    value={k:sha_array(v) for k,v in sorted(state.items())}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def class_statistics(labels, masks, train):
    """Fit1: common TRAIN binary-class weights, no held reads."""
    counts=[0,0]
    for i in train:
        for y,m in zip(labels[i],masks[i]):
            if m[0]:
                require(y[0] in (0.,1.), 'binary native eligibility required')
                counts[int(y[0])]+=1
    require(all(counts), 'both TRAIN eligibility classes required')
    n=sum(counts)
    return dict(class_counts=counts, weights=[n/(2*v) for v in counts],
        scope='TRAIN-only inverse class frequency; per-root known-coordinate mean then root mean.')


def stratum_statistics(labels, masks, train, metadata):
    """Fit2: equal observed TRAIN operator×intended-domain endpoint mass."""
    counts={}
    for i in train:
        key=metadata[i]['operator']+'|'+metadata[i]['intent_domain']
        n=sum(bool(m[1]) for m in masks[i])
        require(n<=1, 'only actual committed intended endpoints may train')
        if n: counts[key]=counts.get(key,0)+n
    expected={'damage|unit','damage|base','heal|unit'}
    require(set(counts)==expected, 'exact three observed TRAIN strata required; heal|base is held composition')
    n=sum(counts.values())
    return dict(counts=counts,weights={k:n/(len(counts)*v) for k,v in counts.items()},
        absent_train_strata=['heal|base'],known_endpoints=n,
        scope='TRAIN-only equal mass over three observed operator×domain strata, raw physical SmoothL1; held heal|base contributes no fitted weight.')


def mean(values): return sum(values)/len(values) if values else None


def evaluate(predictions, labels, masks, metadata, rows):
    """Saved natural-unit observations only; coordinates are nested in roots."""
    endpoint=[];positive=[];negative=[];eligibility_errors=[]
    for i in rows:
        root_errors=[]
        for q,(p,y,m) in enumerate(zip(predictions[i],labels[i],masks[i])):
            if m[0]:
                (positive if y[0] else negative).append(p[0]>=.5 if y[0] else p[0]<.5)
                root_errors.append(abs(float(p[0])-float(y[0])))
            if m[1]:
                endpoint.append(dict(root=int(i),candidate=q,truth=float(y[1]),prediction=float(p[1]),
                    error=abs(float(p[1])-float(y[1])),operator=metadata[i]['operator'],
                    domain=metadata[i]['intent_domain'],healthy=bool(metadata[i]['healthy_intent']) and metadata[i]['operator']=='heal'))
        if root_errors: eligibility_errors.append(mean(root_errors))
    groups={'pooled':endpoint}
    groups.update({v:[x for x in endpoint if x['domain']==v] for v in ('unit','base')})
    groups.update({v:[x for x in endpoint if x['operator']==v] for v in ('damage','heal')})
    healthy=[x for x in endpoint if x['healthy']]
    require(all(x['truth']==0. for x in healthy), 'healthy native endpoints must remain observed zeros')
    nonzero=[x for x in endpoint if x['truth']!=0.]
    recall=mean([float(v) for v in positive]);specificity=mean([float(v) for v in negative])
    return dict(endpoint_mae={k:mean([x['error'] for x in v]) for k,v in groups.items()},
        endpoint_support={k:len(v) for k,v in groups.items()},
        nonzero_sign_accuracy=mean([float(x['truth']*x['prediction']>0.) for x in nonzero]),
        nonzero_support=len(nonzero),healthy_count=len(healthy),
        healthy_mean_abs=mean([abs(x['prediction']) for x in healthy]),
        healthy_max_abs=max([abs(x['prediction']) for x in healthy],default=None),
        eligibility=dict(positive_recall=recall,specificity=specificity,
            rootbalanced_mae=mean(eligibility_errors),
            balanced_accuracy=(recall+specificity)/2 if recall is not None and specificity is not None else None,
            positive_count=len(positive),negative_count=len(negative),
            all_ones_positive_recall=1. if positive else None,
            scope='All-positive HELD eligibility has undefined specificity/BA; recall alone cannot establish discrimination.'),
        endpoints=endpoint)


def decisions(results):
    per_seed={}; full=[];printed=[]
    for seed in SEEDS:
        new=results[f's{seed}:new-full']['evaluations']['300']['held']
        old=results[f's{seed}:old-late-fusion']['evaluations']['300']['held']
        control=results[f's{seed}:new-printed-only']['evaluations']['300']['held']
        maes=new['endpoint_mae']
        endpoint=all(v is not None and v<=.25 for v in maes.values())
        sign=new['nonzero_sign_accuracy'] is not None and new['nonzero_sign_accuracy']>=.95
        healthy=new['healthy_count']>0 and new['healthy_max_abs']<=.1
        recall=new['eligibility']['positive_recall'] is not None and new['eligibility']['positive_recall']>=.95
        nonregression=maes['pooled'] is not None and old['endpoint_mae']['pooled'] is not None and maes['pooled']<=old['endpoint_mae']['pooled']+.05
        per_seed[str(seed)]=dict(endpoint_slices_passed=endpoint,nonzero_sign_passed=sign,
            healthy_max_abs_passed=healthy,positive_recall_descriptive_passed=recall,
            usable_endpoint_gate_passed=endpoint and sign and healthy and recall,
            old_endpoint_nonregression=nonregression,
            eligibility_discrimination_qualified=False)
        full.append(maes['pooled']);printed.append(control['endpoint_mae']['pooled'])
    fullmean=mean(full) if all(v is not None for v in full) else None
    printedmean=mean(printed) if all(v is not None for v in printed) else None
    reduction=1-fullmean/printedmean if fullmean is not None and printedmean is not None and printedmean>0 else None
    return dict(per_seed=per_seed,pooled_three_seed_new_mae=fullmean,
        pooled_three_seed_printed_mae=printedmean,relative_improvement_vs_printed=reduction,
        usability_passed=all(x['usable_endpoint_gate_passed'] for x in per_seed.values()),
        architecture_diagnostic_passed=reduction is not None and reduction>=.2 and all(x['old_endpoint_nonregression'] for x in per_seed.values()),
        deterministic_reference='Native/reference exactness is an admission prerequisite; learned performance cannot beat the perfect reference.',
        semantic_validated=False,scope='Two exposed-at-evaluation held cards and one selector form; no broad semantic or statistical qualification.')


def worker(args, run):
    """ROOT must already hold its lease, durable begin and active E.Guard."""
    require(run.state.get('pending') is not None and run.remaining_seconds()>0, 'active sealed fit stage required')
    import numpy as np
    import torch
    import real_ir_transfer_model as M
    import sys
    torch.set_num_threads(1)
    out=Path(args.out);require(out.is_dir() and not any(out.iterdir()),'existing empty declared fit directory required')
    with np.load(args.dataset,allow_pickle=False) as handle: a={k:handle[k] for k in handle.files}
    manifest=json.loads(Path(args.manifest).read_text());require(manifest['schema']=='jepa-real-ir-transfer-data/1' and manifest['fit_admitted'] is True,'native/reference data gate must pass before learning')
    required={'program_features':(7,13),'source_printed_features':(7,10),'candidate_features':(56,6,17),
              'targets':(56,6,2),'target_mask':(56,6,2),'primary_target_mask':(56,6,2),'program_indices':(56,)}
    for k,shape in required.items(): require(a[k].shape==shape and np.isfinite(a[k]).all(),'finite frozen array ABI differs: '+k)
    require(all(a[k].dtype==np.float32 for k in required if k!='program_indices') and
            all(a[k].dtype==np.int64 for k in ('program_indices','train_idx','held_idx')),
            'exact float32 features/labels and int64 indices required; never truncate identifiers')
    train=a['train_idx'].astype(np.int64);held=a['held_idx'].astype(np.int64)
    require(len(train)==40 and len(held)==16 and sorted(train.tolist()+held.tolist())==list(range(56)), 'exact40/16 whole-program split required')
    require(np.array_equal(a['target_mask'],a['primary_target_mask']), 'only actual intended endpoint damage may enter fit/evaluation masks')
    require(np.isin(a['primary_target_mask'],[0.,1.]).all(),'explicit binary native-known masks required')
    require(a['baseline_predictions'].shape==(56,6,2) and np.isfinite(a['baseline_predictions']).all() and
            np.array_equal(a['baseline_mask'],a['primary_target_mask']) and
            np.array_equal(a['baseline_predictions'][a['baseline_mask']>0],a['targets'][a['baseline_mask']>0]),
            'exact co-known deterministic/native reference is an admission prerequisite')
    labels=a['targets'].tolist(); masks=a['primary_target_mask'].tolist(); metadata=manifest['root_metadata']
    require(len(metadata)==56 and all(sum(bool(x[1]) for x in masks[i])<=1 for i in range(56)), 'one actual intended effect maximum per root')
    token=run.intent('numerical_fits');cw=class_statistics(labels,masks,train.tolist());run.complete(token)
    token=run.intent('numerical_fits');sw=stratum_statistics(labels,masks,train.tolist(),metadata);run.complete(token)
    write(out/'loss-weights.json',dict(class_statistics=cw,stratum_statistics=sw))
    index=a['program_indices'].astype(np.int64);require(index.min()>=0 and index.max()<7,'program index is provenance lookup only')
    p=torch.from_numpy(a['program_features'][index].astype(np.float32));c=torch.from_numpy(a['candidate_features'].astype(np.float32));s=torch.from_numpy(a['source_printed_features'][index].astype(np.float32))
    y=torch.from_numpy(a['targets'].astype(np.float32));mask=torch.from_numpy(a['primary_target_mask'].astype(np.float32));ix=torch.from_numpy(train)
    endpoint_weights=torch.tensor([sw['weights'].get(m['operator']+'|'+m['intent_domain'],0.) for m in metadata],dtype=torch.float32)[:,None]
    class_weights=torch.tensor(cw['weights'],dtype=torch.float32)
    np.savez_compressed(out/'consumed-inputs.npz',program_features=a['program_features'],source_printed_features=a['source_printed_features'],candidate_features=a['candidate_features'],program_indices=index,train_idx=train,held_idx=held)
    np.savez_compressed(out/'training-schedule.npz',train_indices=train,seeds=np.asarray(SEEDS),arms=np.asarray(ARMS),updates=np.arange(1,301))
    write(out/'contract.json',dict(config=CONFIG,model=M.contract(),source_dataset=str(Path(args.dataset).resolve()),source_manifest=str(Path(args.manifest).resolve()),
        runtime=dict(python_version=sys.version,python_executable=str(Path(sys.executable).resolve()),
            numpy_version=np.__version__,torch_version=str(torch.__version__),
            module_paths=dict(numpy=str(Path(np.__file__).resolve()),torch=str(Path(torch.__file__).resolve()),
                              model=str(Path(M.__file__).resolve()),fit=str(Path(__file__).resolve()))),
        held_policy='Every initial and final forward deferred until all2700updates across all9arms finish; no intermediate held readout.',
        objective='0.5 TRAIN-balanced BCE root mean +0.5 raw SmoothL1 intended-endpoint operator×domain balanced mean. No fitted public normalization.'))
    models={};initials={};results={};counts=dict(neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=2)
    def arrays(model): return {k:v.detach().cpu().numpy().copy() for k,v in model.state_dict().items()}
    def tracked_forward(model,pp,cc,ss):
        token=run.intent('neural_forwards');value=model(pp,cc,ss);run.complete(token);counts['neural_forwards']+=1
        require(all(torch.isfinite(v).all().item() for v in value.values()),'finite predictions required')
        return value
    progress=out/'fit-progress.jsonl'
    with progress.open('x') as log:
        for seed in SEEDS:
            torch.manual_seed(seed);master=M.make_model(torch,'new-full');master_state={k:v.detach().clone() for k,v in master.state_dict().items()};master_hash=state_hash(arrays(master))
            for arm in ARMS:
                torch.manual_seed(seed);model=M.make_model(torch,arm)
                if arm!='old-late-fusion':model.load_state_dict(master_state,strict=True)
                initial=arrays(model);initials[(seed,arm)]=initial;models[(seed,arm)]=model
                if arm!='old-late-fusion': require(state_hash(initial)==master_hash,'NEW arm must load complete common initial state before training')
                np.savez_compressed(out/f's{seed}-{arm}-initial-checkpoint.npz',**initial)
                results[f's{seed}:{arm}']=dict(initial_state_sha256=state_hash(initial),master_initial_state_sha256=master_hash if arm!='old-late-fusion' else None,evaluations={},losses=[])
                optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001)
                for update in range(1,301):
                    optimizer.zero_grad(set_to_none=True);pred=tracked_forward(model,p[ix],c[ix],s[ix])
                    binary=torch.nn.functional.binary_cross_entropy_with_logits(pred['eligibility_logits'],y[ix,:,0],reduction='none')
                    weights=class_weights[y[ix,:,0].long()]*mask[ix,:,0]
                    eligibility=((binary*weights).sum(1)/mask[ix,:,0].sum(1).clamp_min(1)).mean()
                    distance=torch.nn.functional.smooth_l1_loss(pred['signed_damage'],y[ix,:,1],reduction='none',beta=1.)
                    endpoint=(distance*mask[ix,:,1]*endpoint_weights[ix]).sum()/mask[ix,:,1].sum().clamp_min(1)
                    loss=.5*eligibility+.5*endpoint
                    require(torch.isfinite(loss).item(),'finite training loss required before backward')
                    token=run.intent('backwards');loss.backward();run.complete(token);counts['backwards']+=1
                    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                    require(torch.isfinite(norm).item(),'finite gradient norm required before optimizer step')
                    token=run.intent('optimizer_updates');optimizer.step();run.complete(token);counts['optimizer_updates']+=1
                    row=dict(seed=seed,arm=arm,update=update,loss=float(loss.item()),eligibility_loss=float(eligibility.item()),endpoint_loss=float(endpoint.item()),preclip_gradient_l2=float(norm.item()))
                    log.write(json.dumps(row,allow_nan=False)+'\n');log.flush();os.fsync(log.fileno())
                    results[f's{seed}:{arm}']['losses'].append(row['loss'])
                final=arrays(model);np.savez_compressed(out/f's{seed}-{arm}-checkpoint.npz',**final)
                results[f's{seed}:{arm}']['final_state_sha256']=state_hash(final)
        require(counts['optimizer_updates']==2700,'all training must finish before any held forward')
        # Saved initial/final evaluation happens only now, with zero updates.
        for seed in SEEDS:
            for arm in ARMS:
                model=models[(seed,arm)];final={k:v.detach().clone() for k,v in model.state_dict().items()}
                for step,state in ((0,{k:torch.from_numpy(v) for k,v in initials[(seed,arm)].items()}),(300,final)):
                    model.load_state_dict(state,strict=True);model.eval()
                    with torch.no_grad(): output=tracked_forward(model,p,c,s)
                    logits=output['eligibility_logits'].cpu().numpy();prob=torch.sigmoid(output['eligibility_logits']).cpu().numpy();damage=output['signed_damage'].cpu().numpy()
                    prediction=np.stack((prob,damage),axis=-1)
                    np.savez_compressed(out/f's{seed}-{arm}-step{step}-predictions.npz',predictions=prediction,eligibility_logits=logits,program_indices=index)
                    results[f's{seed}:{arm}']['evaluations'][str(step)]={name:evaluate(prediction.tolist(),labels,masks,metadata,rows.tolist()) for name,rows in(('train',train),('held',held))}
    require(counts==dict(neural_forwards=2718,backwards=2700,optimizer_updates=2700,numerical_fits=2),'exact fixed counter panel required')
    require(all(results[f's{seed}:new-full']['initial_state_sha256']==results[f's{seed}:new-printed-only']['initial_state_sha256'] for seed in SEEDS),'NEW full/printed common initialization failed')
    baseline_evaluations={}
    for name,prediction in (('deterministic-reference',a['baseline_predictions']),
                           ('all-ones-eligibility-zero-effect',np.stack((np.ones((56,6),np.float32),np.zeros((56,6),np.float32)),axis=-1))):
        np.savez_compressed(out/f'{name}-predictions.npz',predictions=prediction,program_indices=index)
        baseline_evaluations[name]={part:evaluate(prediction.tolist(),labels,masks,metadata,rows.tolist()) for part,rows in(('train',train),('held',held))}
    result=dict(schema='jepa-real-ir-transfer-fit/1',config=CONFIG,counts=counts,results=results,decisions=decisions(results),
        baseline_evaluations=baseline_evaluations,
        native_applies=0,paid_jobs=0,semantic_validated=False,held_samples=dict(cards=2,roots=16,
            eligibility_all_positive=all(labels[int(i)][q][0]==1. for i in held for q in range(6) if masks[int(i)][q][0])),
        limitation='S10 numeric printed control only. OLD is an architecture comparator with different parameter count. No hyperparameter search or checkpoint reuse.')
    write(out/'result.json',result)
    return dict(result_path=str(out/'result.json'),counts=counts,semantic_validated=False)
