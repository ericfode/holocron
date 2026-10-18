"""Fixed typed-intent experiment: TRAIN-only fit, then a separate terminal score.

Import is stdlib. ROOT owns both durable stages and active time/RSS guards.
No evaluation forward occurs in fit_worker; score_worker never updates/fits.
"""
import hashlib
import json
import math
import os
from pathlib import Path

SEEDS=(17,29,43)
ARMS=('current','matched-aux-latent','factorized-intent')
CONFIG=dict(seeds=list(SEEDS),arms=list(ARMS),updates_per_arm=300,training_forwards=2700,
    evaluation_forwards=24,neural_forwards=2724,backwards=2700,optimizer_updates=2700,numerical_fits=0,
    learning_rate=.003,weight_decay=.0001,clip_l2=1.,eligibility_loss_coefficient=.5,
    endpoint_loss_coefficient=.5,identity_loss_coefficient=.25,amount_loss_coefficient=.25,
    smooth_l1_beta=1.,hyperparameter_search=False,statistics='Frozen original TRAIN weights; no new statistics fits.')


def require(ok,message):
    if not ok:raise ValueError(message)


def mean(values):return sum(values)/len(values)if values else None


def pin(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def reference_admitted(ref,terminal=False):
    expected=dict(known_coordinates=52 if terminal else 371,known_eligibility=48 if terminal else 336,
        known_intended_deltas=4 if terminal else 35,mismatch_count=0,removed_count=0 if terminal else 1,removal_mismatch_count=0)
    return all(ref.get(k)==v for k,v in expected.items())and ref.get('mismatches',[])==[]


def typed_scores(identity,amount,indices,programs,rows):
    """One readout per unique public program, not one sample per repeated board."""
    if identity is None:return None
    result=[]
    for k in sorted({indices[i]for i in rows}):
        members=[i for i in rows if indices[i]==k];i=members[0]
        require(programs[k][10:12]in([1.,0.],[0.,1.]),'known public syntax identity required')
        truth=0 if programs[k][10] else 1
        predicted=max(range(2),key=lambda c:identity[i][c]);literal=float(amount[i])
        require(math.isfinite(literal)and all(math.isfinite(float(v))for v in identity[i]),'finite intent readout required')
        result.append(dict(program_index=int(k),root_representative=int(i),roots=len(members),
            identity_truth=truth,identity_prediction=predicted,identity_correct=predicted==truth,
            amount_truth=float(programs[k][12]),amount_prediction=literal,amount_error=abs(literal-float(programs[k][12])),
            repeated_root_max_amount_difference=max(abs(float(amount[j])-literal)for j in members),
            repeated_root_max_logit_difference=max(abs(float(identity[j][c])-float(identity[i][c]))for j in members for c in range(2))))
    return dict(programs=len(result),identity_accuracy=mean([float(r['identity_correct'])for r in result]),
        amount_mae=mean([r['amount_error']for r in result]),per_program=result,
        scope='Unique public syntax readouts; repeated boards are not extra semantic samples.')


def endpoint_gate(panel,all_slices):
    result={}
    for name in('raw','routed'):
        m=panel[name];values=m['endpoint_mae']if all_slices else{'pooled':m['endpoint_mae']['pooled']}
        absolute=all(v is not None and v<=.25 for v in values.values())and not m.get('undefined',[])
        sign=m['nonzero_sign_accuracy']is not None and m['nonzero_sign_accuracy']>=.95
        healthy=m.get('healthy_max_abs');result[name]=dict(mae_passed=absolute,nonzero_sign_passed=sign,
            healthy_max_passed=None if healthy is None else healthy<=.1)
    return result


def endpoint_slices(routed,raw,metadata,public,programs,replay):
    """Cached prediction grouping only; no labels or predictions are regenerated."""
    raw_lookup={(r['root'],r['candidate']):r for r in raw['endpoints']};points=[]
    for original in routed['endpoints']:
        r=dict(original);i,q=r['root'],r['candidate'];m=metadata[i];p=public[i][q]
        cap=programs[m['program_index']]['selector']['cost_cap'];conditional=raw_lookup.get((i,q))
        r.update(source_card=m['source_card'],amount=m['amount'],owner=p['owner'],arena=p['zone'],
            damage=p['damage'],hp=p['hp'],cap=cap['value']if cap['present']else'absent',
            prior_seen=True if i<56 else bool(replay[i][q][1])if i<112 else None,
            raw_prediction=conditional['prediction']if conditional else None,
            raw_error=conditional['error']if conditional else None)
        r['joint']='|'.join(str(r[k])for k in('operator','amount','domain','owner','arena','healthy','damage','hp','cap'))
        points.append(r)
    tables={}
    for field in('operator','amount','domain','owner','arena','healthy','damage','hp','cap','prior_seen','source_card','joint'):
        groups={}
        for r in points:groups.setdefault(str(r[field]),[]).append(r)
        tables[field]={k:dict(endpoints=len(v),roots=len({r['root']for r in v}),sources=len({r['source_card']for r in v}),
            routed_mae=mean([r['error']for r in v]),raw_mae=mean([r['raw_error']for r in v if r['raw_error']is not None]))for k,v in groups.items()}
    return dict(rows=points,tables=tables,scope='Descriptive cached endpoints; seeds/boards are not independent cards. Prior-seen applies to original or development effect/state tuples; terminal is unscoped/null.')


def decisions(results):
    per_seed={}
    for seed in SEEDS:
        c=results[f's{seed}:current']['evaluations']['300'];a=results[f's{seed}:matched-aux-latent']['evaluations']['300']
        f=results[f's{seed}:factorized-intent']['evaluations']['300'];dev=endpoint_gate(f['development_primary'],True)
        x=f['development_primary']['routed']['endpoint_mae']['pooled'];y=a['development_primary']['routed']['endpoint_mae']['pooled']
        reduction=1-x/y if x is not None and y is not None and y>0 else None
        train=f['train']['routed']['endpoint_mae']['pooled'];current=c['train']['routed']['endpoint_mae']['pooled']
        nonreg=train is not None and current is not None and train<=current+.05
        syntax=f['exposed']['typed_intent'];typed=syntax is not None and syntax['programs']==7 and syntax['identity_accuracy']==1. and syntax['amount_mae']<=.25
        dev_pass=all(z['mae_passed']and z['nonzero_sign_passed']and z['healthy_max_passed']is not False for z in dev.values())
        development=dev_pass and reduction is not None and reduction>=.2 and nonreg and typed
        t=f['terminal'];terminal=endpoint_gate(t,False);e=t['routed']['eligibility'];s=t['typed_intent']
        eligibility=e['balanced_accuracy']is not None and e['balanced_accuracy']>=.95 and e['positive_recall']is not None and e['positive_recall']>=.95
        terminal_typed=s is not None and s['programs']==1 and s['identity_accuracy']==1. and s['amount_mae']<=.25
        terminal_pass=all(z['mae_passed']and z['nonzero_sign_passed']for z in terminal.values())and eligibility and terminal_typed
        per_seed[str(seed)]=dict(development_endpoint=dev,development_routed_relative_improvement=reduction,
            development_improvement_passed=reduction is not None and reduction>=.2,train_routed_nonregression=nonreg,
            exposed_unique_program_typed_passed=typed,development_passed=development,terminal_endpoint=terminal,
            terminal_eligibility_passed=eligibility,terminal_unique_program_typed_passed=terminal_typed,terminal_passed=terminal_pass)
    return dict(per_seed=per_seed,development_passed=all(p['development_passed']for p in per_seed.values()),
        terminal_passed=all(p['terminal_passed']for p in per_seed.values()),
        thresholds=dict(endpoint_mae_max=.25,nonzero_sign_min=.95,healthy_heal_max=.1,routed_improvement_min=.2,
            train_routed_allowance=.05,identity_accuracy=1.,amount_mae_max=.25,terminal_balanced_accuracy_min=.95,terminal_positive_recall_min=.95),
        scope='Development29 nonreplay effects and terminal one-card outcome are separate gates. Unsupported slices remain null; no whole-card/deck qualification follows.',semantic_validated=False)


def fit_worker(args,run):
    require(run.state.get('pending')is not None and run.remaining_seconds()>0,'active sealed fit guard required')
    import numpy as np
    import torch
    import sys
    import real_ir_transfer_fit as F
    import real_ir_intent_model as M
    torch.set_num_threads(1);prior=Path(args.prior);out=Path(args.out)
    require(out.is_dir()and not any(out.iterdir()),'existing empty fit output required')
    admission=json.loads(Path(args.manifest).read_text());ref=admission['reference']
    require(admission['schema']=='jepa-real-ir-intent-data/1'and admission['fit_admitted']and not admission['fit_blockers']and
        reference_admitted(ref)and
        admission['support']==dict(development_known_endpoints=35,primary=29,replay=6,removed=1),'complete development admission before fit')
    with np.load(prior/'prep-1/dataset.npz',allow_pickle=False)as h:
        require(h['train_idx'].tolist()==list(range(40)),'original TRAIN40 order only')
        a={k:h[k][:40].copy()for k in('candidate_features','targets','target_mask','program_indices')}
        for k in('program_features','source_printed_features'):a[k]=h[k][:5].copy()
    require(set(a['program_indices'].tolist())==set(range(5))and all(np.isfinite(v).all()for v in a.values()),'finite original five-program TRAIN bank')
    metadata=json.loads((prior/'prep-1/manifest.json').read_text())['root_metadata'][:40]
    weights=json.loads((prior/'fit-1/loss-weights.json').read_text());index=a['program_indices']
    p=torch.from_numpy(a['program_features'][index]);c=torch.from_numpy(a['candidate_features']);s=torch.from_numpy(a['source_printed_features'][index])
    y=torch.from_numpy(a['targets']);mask=torch.from_numpy(a['target_mask']);cw=torch.tensor(weights['class_statistics']['weights'],dtype=torch.float32)
    ew=torch.tensor([weights['stratum_statistics']['weights'].get(m['operator']+'|'+m['intent_domain'],0.)for m in metadata],dtype=torch.float32)[:,None]
    identity=p[:,10:12].argmax(-1);amount=p[:,12]
    F.write(out/'contract.json',dict(config=CONFIG,model=M.contract(),admission_manifest=pin(args.manifest),
        runtime=dict(python=sys.version,executable=str(Path(sys.executable).resolve()),numpy=np.__version__,torch=str(torch.__version__)),
        scope='Fit originalTRAIN40 only; no development/terminal numerical labels, initial/final evaluations, or numerical statistics fits.'))
    F.write(out/'loss-weights.json',weights);np.savez_compressed(out/'consumed-train-inputs.npz',**a)
    np.savez_compressed(out/'training-schedule.npz',train_indices=np.arange(40),seeds=np.asarray(SEEDS),arms=np.asarray(ARMS),updates=np.arange(1,301))
    paths=[Path(args.manifest),prior/'prep-1/dataset.npz',prior/'prep-1/manifest.json',prior/'fit-1/loss-weights.json',Path(F.__file__),Path(M.__file__),Path(__file__)]
    paths +=[prior/'fit-1'/f's{seed}-new-full-{suffix}.npz'for seed in SEEDS for suffix in('initial-checkpoint','checkpoint')]
    F.write(out/'input-pins.json',[pin(v)for v in paths]);counts=dict(neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0);results={}
    def arrays(model):return{k:v.detach().cpu().numpy().copy()for k,v in model.state_dict().items()}
    def load(path):
        with np.load(path,allow_pickle=False)as h:return{k:torch.from_numpy(h[k].copy())for k in h.files}
    with(out/'fit-progress.jsonl').open('x')as log:
        for seed in SEEDS:
            initial=load(prior/'fit-1'/f's{seed}-new-full-initial-checkpoint.npz');old_hash=F.state_hash({k:v.numpy()for k,v in initial.items()});aux_hash=None
            for arm in ARMS:
                torch.manual_seed(seed);model=M.make_model(torch,arm);loaded=model.load_state_dict(initial,strict=arm=='current')
                extra=set(M.parameter_shapes(arm))-set(initial)
                require(set(loaded.missing_keys)==extra and not loaded.unexpected_keys,'complete original backbone initializer required')
                state=arrays(model);initial_hash=F.state_hash(state)
                require(F.state_hash({k:state[k]for k in initial})==old_hash,'original backbone bytes differ')
                if arm!='current':
                    if aux_hash is None:aux_hash=initial_hash
                    require(initial_hash==aux_hash,'complete shared1517 auxiliary initialization required')
                np.savez_compressed(out/f's{seed}-{arm}-initial-checkpoint.npz',**state)
                key=f's{seed}:{arm}';results[key]=dict(initial_state_sha256=initial_hash,old_initial_state_sha256=old_hash,
                    aux_initial_state_sha256=aux_hash if arm!='current'else None,losses=[],evaluations={})
                optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001)
                for update in range(1,301):
                    optimizer.zero_grad(set_to_none=True);token=run.intent('neural_forwards');pred=model(p,c,s);run.complete(token);counts['neural_forwards']+=1
                    require(all(torch.isfinite(v).all().item()for v in pred.values()),'finite model outputs')
                    binary=torch.nn.functional.binary_cross_entropy_with_logits(pred['eligibility_logits'],y[...,0],reduction='none')
                    w=cw[y[...,0].long()]*mask[...,0];eligibility=((binary*w).sum(1)/mask[...,0].sum(1).clamp_min(1)).mean()
                    distance=torch.nn.functional.smooth_l1_loss(pred['signed_damage'],y[...,1],reduction='none',beta=1.)
                    endpoint=(distance*mask[...,1]*ew).sum()/mask[...,1].sum().clamp_min(1)
                    loss=.5*eligibility+.5*endpoint;identity_loss=amount_loss=None
                    if arm!='current':
                        identity_loss=torch.nn.functional.cross_entropy(pred['intent_identity_logits'],identity)
                        amount_loss=torch.nn.functional.smooth_l1_loss(pred['intent_amount_native'],amount,reduction='mean',beta=1.)
                        loss=loss+.25*identity_loss+.25*amount_loss
                    require(torch.isfinite(loss).item(),'finite loss before backward')
                    token=run.intent('backwards');loss.backward();run.complete(token);counts['backwards']+=1
                    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.);require(torch.isfinite(norm).item(),'finite gradient before optimizer')
                    token=run.intent('optimizer_updates');optimizer.step();run.complete(token);counts['optimizer_updates']+=1
                    row=dict(seed=seed,arm=arm,update=update,loss=float(loss.item()),eligibility_loss=float(eligibility.item()),endpoint_loss=float(endpoint.item()),
                        identity_loss=float(identity_loss.item())if identity_loss is not None else None,
                        amount_loss=float(amount_loss.item())if amount_loss is not None else None,preclip_gradient_l2=float(norm.item()))
                    log.write(json.dumps(row,allow_nan=False)+'\n');log.flush();os.fsync(log.fileno());results[key]['losses'].append(row['loss'])
                state=arrays(model);np.savez_compressed(out/f's{seed}-{arm}-checkpoint.npz',**state);results[key]['final_state_sha256']=F.state_hash(state)
                if arm=='current':
                    old=load(prior/'fit-1'/f's{seed}-new-full-checkpoint.npz')
                    require(set(state)==set(old)and all(np.array_equal(state[k],old[k].numpy())for k in state),'current must reproduce original final checkpoint exactly')
                    results[key]['current_exact_reproduction']=True
    require(counts==dict(neural_forwards=2700,backwards=2700,optimizer_updates=2700,numerical_fits=0),'fixed TRAIN-only budget')
    F.write(out/'result.json',dict(schema='jepa-real-ir-intent-fit/1',config=CONFIG,counts=counts,results=results,
        fit_sealed_before_terminal=True,semantic_validated=False,native_applies=0,paid_jobs=0))
    return dict(result_path=str(out/'result.json'),counts=counts)


def score_worker(args,run):
    require(run.state.get('pending')is not None and run.remaining_seconds()>0,'active sealed score guard required')
    import numpy as np
    import torch
    import real_ir_transfer_fit as F
    import real_ir_hp_projection_fit as HF
    import real_ir_hp_projection_model as HP
    import real_ir_intent_model as M
    torch.set_num_threads(1);out=Path(args.out);root=Path(args.root);fit=root/'fit-1'
    require(out.is_dir()and not any(out.iterdir()),'existing empty score output required')
    with np.load(args.dataset,allow_pickle=False)as h:a={k:h[k]for k in h.files}
    manifest=json.loads(Path(args.manifest).read_text());fit_result=json.loads((fit/'result.json').read_text())
    require(manifest['fit_admitted']and not manifest['fit_blockers']and len(manifest['root_metadata'])==120 and
        reference_admitted(manifest['terminal_reference'],True),
        'actual terminal52/native admission required before any evaluation')
    require(fit_result['counts']==dict(neural_forwards=2700,backwards=2700,optimizer_updates=2700,numerical_fits=0)and
        fit_result['fit_sealed_before_terminal']is True,'all fixed training must precede scoring')
    require(a['candidate_features'].shape==(120,6,17)and a['targets'].shape==a['target_mask'].shape==(120,6,2)and
        a['program_features'].shape==(8,13)and a['source_printed_features'].shape==(8,10),'final120 P13/C17/S10 ABI')
    for name in('program_features','source_printed_features','candidate_features','targets','target_mask','primary_target_mask','replay_target_mask','terminal_target_mask'):
        require(a[name].dtype==np.float32 and np.isfinite(a[name]).all(),'finite float32 final data: '+name)
    for name in('target_mask','primary_target_mask','replay_target_mask','terminal_target_mask'):
        require(a[name].shape==(120,6,2)and np.isin(a[name],[0.,1.]).all(),'explicit known native masks: '+name)
    require(a['primary_target_mask'][...,1].sum()==29 and a['replay_target_mask'][...,1].sum()==6 and
        a['terminal_target_mask'][...,0].sum()==48 and a['terminal_target_mask'][...,1].sum()==4 and
        all((a[k]<=a['target_mask']).all()for k in('primary_target_mask','replay_target_mask','terminal_target_mask')),
        'fixed29/6/48+4 known panel support')
    expected=dict(train_idx=list(range(40)),old_dev_idx=list(range(40,56)),old_all_idx=list(range(56)),
                  development_all_idx=list(range(56,112)),terminal_idx=list(range(112,120)))
    for name,values in expected.items():require(a[name].tolist()==values,'fixed score partition: '+name)
    with np.load(fit/'consumed-train-inputs.npz',allow_pickle=False)as h:
        for k in('candidate_features','targets','target_mask','program_indices'):require(np.array_equal(a[k][:40],h[k]),'originalTRAIN scoring input changed')
        for k in('program_features','source_printed_features'):require(np.array_equal(a[k][:5],h[k]),'TRAIN bank changed')
    labels=a['targets'].tolist();masks=a['target_mask'].tolist();metadata=manifest['root_metadata'];index=a['program_indices']
    p=torch.from_numpy(a['program_features'][index]);c=torch.from_numpy(a['candidate_features']);s=torch.from_numpy(a['source_printed_features'][index])
    panels=dict(train=(a['train_idx'],masks),old_dev=(a['old_dev_idx'],masks),exposed=(a['old_all_idx'],masks),
        development_all=(a['development_all_idx'],masks),development_primary=(a['development_all_idx'],a['primary_target_mask'].tolist()),
        development_replay=(a['development_all_idx'],a['replay_target_mask'].tolist()),terminal=(a['terminal_idx'],a['terminal_target_mask'].tolist()))
    results={};counts=dict(neural_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0)
    def load(path):
        with np.load(path,allow_pickle=False)as h:return{k:torch.from_numpy(h[k].copy())for k in h.files}
    paths=[Path(args.dataset),Path(args.manifest),fit/'result.json',fit/'contract.json',fit/'consumed-train-inputs.npz',Path(M.__file__),Path(HP.__file__),Path(F.__file__),Path(HF.__file__),Path(__file__)]
    def evaluate(model,seed,arm,step):
        model.eval();token=run.intent('neural_forwards')
        with torch.no_grad():v=model(p,c,s)
        run.complete(token);counts['neural_forwards']+=1;require(all(torch.isfinite(x).all().item()for x in v.values()),'finite score outputs')
        logits=v['eligibility_logits'].cpu().numpy();pred=np.stack((torch.sigmoid(v['eligibility_logits']).cpu().numpy(),v['signed_damage'].cpu().numpy()),axis=-1)
        extra={k:v[k].cpu().numpy()for k in('intent_identity_logits','intent_amount_native','card_effect','application_effect')if k in v}
        np.savez_compressed(out/f's{seed}-{arm}-step{step}-predictions.npz',predictions=pred,eligibility_logits=logits,program_indices=index,**extra)
        return score_values(pred,extra)
    def score_values(pred,extra):
        values=pred.tolist();identity=extra['intent_identity_logits'].tolist()if 'intent_identity_logits'in extra else None
        amount=extra['intent_amount_native'].tolist()if 'intent_amount_native'in extra else None
        evaluated={}
        for name,(rows,mask)in panels.items():
            routed=F.evaluate(values,labels,mask,metadata,rows.tolist());raw=HF.raw_metrics(values,labels,mask,metadata,rows.tolist())
            evaluated[name]=dict(routed=routed,raw=raw,
                typed_intent=typed_scores(identity,amount,index.tolist(),a['program_features'].tolist(),rows.tolist()),
                slices=endpoint_slices(routed,raw,metadata,manifest['public_before_records'],manifest['canonical_programs'],a['replay_target_mask'].tolist()))
        return evaluated
    for seed in SEEDS:
        for arm in ARMS:
            model=M.make_model(torch,arm);item=results[f's{seed}:{arm}']=dict(evaluations={})
            for step,suffix in((0,'initial-checkpoint'),(300,'checkpoint')):
                path=fit/f's{seed}-{arm}-{suffix}.npz';paths.append(path);model.load_state_dict(load(path),strict=True)
                item['evaluations'][str(step)]=evaluate(model,seed,arm,step)
        for arm,path,model in(('frozen-hp-projected',Path(args.hp_prior)/'fit-1'/f's{seed}-effect-hp-invariant-checkpoint.npz',HP.make_model(torch,'effect-hp-invariant')),
            ('frozen-printed',Path(args.prior)/'fit-1'/f's{seed}-new-printed-only-checkpoint.npz',HP.M.make_model(torch,'new-printed-only'))):
            paths.append(path);model.load_state_dict(load(path),strict=True)
            results[f's{seed}:{arm}']=dict(frozen_checkpoint=pin(path),evaluations={'300':evaluate(model,seed,arm,300)})
    require(counts==dict(neural_forwards=24,backwards=0,optimizer_updates=0,numerical_fits=0),'exact terminal score budget')
    baselines={}
    for name,pred in(('deterministic-reference',a['baseline_predictions']),('all-ones-eligibility-zero-effect',np.stack((np.ones((120,6),np.float32),np.zeros((120,6),np.float32)),axis=-1))):
        np.savez_compressed(out/f'{name}-predictions.npz',predictions=pred,program_indices=index);baselines[name]=score_values(pred,{})
    np.savez_compressed(out/'consumed-inputs.npz',**{k:a[k]for k in('program_features','source_printed_features','candidate_features','program_indices',
        'train_idx','old_dev_idx','old_all_idx','development_all_idx','terminal_idx')})
    F.write(out/'input-pins.json',[pin(path)for path in paths])
    result=dict(schema='jepa-real-ir-intent-score/1',config=CONFIG,counts=counts,results=results,baseline_evaluations=baselines,
        decisions=decisions(results),fit_result=pin(fit/'result.json'),native_applies=0,paid_jobs=0,semantic_validated=False)
    F.write(out/'result.json',result);return dict(result_path=str(out/'result.json'),counts=counts)
