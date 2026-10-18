"""Sealed synthetic compositional comparison; source/primitive tests only by default.

The root wrapper owns begin/Guard/finish. worker(args,run) imports numerical
libraries and constructs models only inside that authorized guarded stage.
No optimizer/model construction occurs at import or --describe.
"""
import argparse
import copy
import hashlib
import importlib
import itertools
import json
import math
import os
from pathlib import Path

SCHEMA='jepa-compositional-typed-fit/1'
SEEDS=(17,29,43)
ARMS=('old-no-id','old-with-id','new-no-id','new-with-id')
BITS=('owner_opponent','arena_space','cap_is_3','amount_is_3','op_heal')
CONFIG=dict(seeds=list(SEEDS),arms=list(ARMS),updates_per_arm=300,training_forwards=3600,evaluation_forwards=24,
    neural_forwards=3624,backwards=3600,optimizer_updates=3600,numerical_fits=2,export_forwards=0,
    native_applies=0,paid_jobs=0,paid_spend_usd=0.,seconds=120.,rss_bytes=1073741824,cpu_workers=1,
    learning_rate=.003,weight_decay=.0001,clip_l2=1.,optimizer='AdamW',batch='all64TRAINroots-frozen-order',
    eligibility_loss=.5,damage_loss=.5,damage_objective='raw-native SmoothL1 at committed intended only',
    candidate_scales=[1.,1.,1.,1.,4.,4.,10.,1.],metrics_after_all_updates=True,semantic_validated=False)


def require(value,message):
    if not value:raise ValueError(message)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def pin(path):
    p=Path(path).resolve();raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def read(path):return json.loads(Path(path).read_text())
def write_new(path,value):
    with Path(path).open('x')as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def journal(path,value):
    with Path(path).open('a')as f:f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def sha_array(a):return hashlib.sha256(str(a.dtype).encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
def state_hash(values):return digest({k:sha_array(values[k])for k in sorted(values)})
def load_npz(np,path):
    with np.load(path,allow_pickle=False)as data:return{k:data[k].copy()for k in data.files}


def describe():
    return dict(schema=SCHEMA,config=CONFIG,
        worker_args=['plan','dataset','manifest','out','spec'],stage='fit',out='Root creates an empty exclusive output directory before worker.',
        old='E path-pool16/context18constant0/candidate8 latefusion80→32→7. Eligibility uses intended=0; damage uses full intended. Heads0/2 only; unused allocated source/other heads receive no objective.',
        new='Frozen compositional_typed_model role binders. Explicit predicted-eligibility/intended endpoint gating is an architectural difference.',
        identity='Same allocated named initialization within each family/seed; only fixed additive-ID gate0/1 differs. TRAIN1..16; HELDUNK0.',
        objective='Half class-balanced root-mean eligibility BCE; half raw SmoothL1 on native-known committed intended damage, root/OP×amount×zero weights TRAIN-only.',
        fit_counts=['E.make_bank original TRAIN numeric std:1','common TRAIN class/stratum statistics:1'],
        evaluation='Exactly initial/final outputs for each arm/seed; no metrics or gates until all3600 updates finish.',
        metadata='Synthetic factorial only; no actual-card/deck/playing-strength claim.',semantic_validated=False)


def parity_audit(bits):
    require(len(bits)==32 and all(len(row)==5 and all(type(b)is int and b in(0,1)for b in row)for row in bits),'full five-bit factorial required')
    require({tuple(row)for row in bits}==set(itertools.product((0,1),repeat=5)),'all32unique combinations required')
    train=[i for i,b in enumerate(bits)if sum(b)%2==0];held=[i for i,b in enumerate(bits)if sum(b)%2]
    for size in range(1,5):
        for axes in itertools.combinations(range(5),size):
            expected=set(itertools.product((0,1),repeat=size))
            require(all({tuple(bits[i][j]for j in axes)for i in group}==expected for group in(train,held)),'proper-subset coverage failed')
    return dict(train_programs=train,held_programs=held,proper_subsets_covered=True)


def loss_weights(targets,masks,selected,q,fields,train):
    """List-only TRAIN statistics; one explicitly charged preprocessing fit."""
    counts=[0,0];strata={};known=[];damage_weights=[0.]*len(targets)
    for i in train:
        for y,m in zip(targets[i],masks[i]):
            if m[0]:require(y[0]in(0,1),'binary native eligibility required');counts[int(y[0])]+=1
        j=selected[i]
        if masks[i][j][1]:
            y=float(targets[i][j][1]);f=fields[q[i]];key=('heal'if f[6]else'damage',int(f[7]),'zero'if y==0 else'nonzero')
            strata.setdefault(key,[]).append(i);known.append(dict(root=i,value=y,stratum=list(key)))
    require(all(counts)and known,'both eligibility classes and known intended damage required')
    total=sum(counts);class_weights=[total/(2*n)for n in counts]
    for indices in strata.values():
        for i in indices:damage_weights[i]=len(known)/(len(strata)*len(indices))
    require(math.isclose(sum(damage_weights),len(known),rel_tol=1e-12),'normalized root/stratum weights required')
    return dict(eligibility_class_counts=counts,eligibility_class_weights=class_weights,damage_weights=damage_weights,
        damage_observations=known,strata=[dict(key=list(k),roots=v,count=len(v),weight=damage_weights[v[0]])for k,v in sorted(strata.items())],
        train_roots=list(train),scope='TRAIN only. Equal root mean then OP/amount/zero stratum balance. Unknown/invalid/uncommitted intended futures get no loss.')


def metric_slice(eligibility,damage,targets,masks,selected,indices):
    pos=neg=tp=tn=0;errors=[];sign_good=0;classes={k:[0,0]for k in('positive','negative','zero')}
    sign=lambda v:1 if v>.25 else-1 if v<-.25 else 0
    truth_sign=lambda v:1 if v>0 else-1 if v<0 else 0
    for i in indices:
        for j in range(len(targets[i])):
            if masks[i][j][0]:
                y=targets[i][j][0];p=eligibility[i][j];pos+=int(y==1);neg+=int(y==0);tp+=int(y==1 and p>=.5);tn+=int(y==0 and p<.5)
        j=selected[i]
        if masks[i][j][1]:
            y=float(targets[i][j][1]);p=float(damage[i][j]);errors.append(abs(p-y));ok=truth_sign(y)==sign(p);sign_good+=int(ok)
            name='positive'if truth_sign(y)>0 else'negative'if truth_sign(y)<0 else'zero';classes[name][0]+=1;classes[name][1]+=int(ok)
    return dict(roots=len(indices),eligibility=dict(positive=pos,negative=neg,true_positive=tp,true_negative=tn,
        balanced_accuracy=(tp/pos+tn/neg)/2 if pos and neg else None),
        damage=dict(known=len(errors),mae=sum(errors)/len(errors)if errors else None,max_abs_error=max(errors)if errors else None,
            sign_accuracy=sign_good/len(errors)if errors else None,classes={k:dict(count=v[0],recall=v[1]/v[0]if v[0]else None)for k,v in classes.items()}))


def evaluate(prediction,arrays,bits,train,held):
    targets,masks,selected,q=(arrays[k]for k in('targets','target_mask','selected_candidate_indices','program_indices'))
    score=lambda ix:metric_slice(prediction['eligibility'],prediction['damage'],targets,masks,selected,ix)
    axes={f'{name}={value}':score([i for i in held if bits[q[i]][axis]==value])for axis,name in enumerate(BITS)for value in(0,1)}
    damage={f'op_heal={op},amount_is_3={amount}':score([i for i in held if bits[q[i]][4]==op and bits[q[i]][3]==amount])for op in(0,1)for amount in(0,1)}
    return dict(train=score(train),held=score(held),held_axes=axes,held_op_amount=damage)


def success_gate(noid,withid,require_id_drop=True):
    checks=[]
    for key,metric in noid['held_axes'].items():
        value=metric['eligibility']['balanced_accuracy'];other=withid['held_axes'][key]['eligibility']['balanced_accuracy']
        checks.append(dict(panel=key,head='eligibility',value=value,ID_on=other,absolute=value is not None and value>=.95,
            identity_drop=value is not None and other is not None and other-value<=.02+1e-12))
    for key,metric in noid['held_op_amount'].items():
        d=metric['damage'];other=withid['held_op_amount'][key]['damage'];zero=d['classes']['zero']['recall']
        heal=key.startswith('op_heal=1,');zero_ok=zero is not None and zero>=.95 if heal else d['classes']['zero']['count']==0
        checks.append(dict(panel=key,head='damage',mae=d['mae'],sign_accuracy=d['sign_accuracy'],zero_recall=zero,
            zero_scope='Required healthy-zero recall'if heal else'Predeclared N/A: damage op has no native-zero intended outcomes',
            absolute=d['mae']is not None and d['mae']<=.25 and d['sign_accuracy']is not None and d['sign_accuracy']>=.95 and zero_ok,
            identity_drop=d['mae']is not None and other['mae']is not None and d['mae']-other['mae']<=.05+1e-12))
    absolute=all(c['absolute']for c in checks);identity=all(c['identity_drop']for c in checks)
    return dict(passed=absolute and(identity or not require_id_drop),absolute_passed=absolute,identity_passed=identity,identity_required=require_id_drop,
        checks=checks,scope='Every held factor/OP×amount slice; required support missing fails. Damage-op zero recall N/A. NEW identity gap mandatory; OLD descriptive. Rename equality is additionally mandatory.')


def make_old(torch,symbols,identity_enabled):
    """Reuse E modules/path-pool and late fusion; only public width/routing adapt."""
    require(type(identity_enabled)is bool,'fixed identity gate must be boolean')
    E=importlib.import_module('effect_identifiability_fit');nn=torch.nn
    class Old(nn.Module):
        def __init__(self):
            super().__init__();self.base=E.make_model(torch,symbols,32,16);self.base.candidate[0]=nn.Linear(8,16);self.identity_enabled=identity_enabled
        def forward(self,fields,candidates,identity_indices,q,bank):
            semantic=self.base.card_bank(bank);p=semantic[q]+float(self.identity_enabled)*torch.nn.functional.layer_norm(self.base.identity(identity_indices),(16,))
            x=torch.zeros((len(candidates),18),dtype=candidates.dtype,device=candidates.device);s=self.base.context(x)
            scales=torch.as_tensor(CONFIG['candidate_scales'],dtype=candidates.dtype,device=candidates.device);c=candidates/scales
            neutral=c.clone();neutral[...,7]=0.;full=self.base.candidate(c);elig=self.base.candidate(neutral)
            def branch(t):
                pp=p[:,None,:].expand_as(t);ss=s[:,None,:].expand_as(t)
                return self.base.branch_head(torch.cat((pp,ss,t,pp*ss,pp*t),-1))
            # Two routed branch evaluations are one predeclared adapter call;
            # no source/lifecycle objective or new learned head is introduced.
            return dict(eligibility_logits=branch(elig)[...,0],signed_damage=branch(full)[...,2])
    return Old()


def worker(args,run):
    """Root already holds the canonical lease and active120s/1GiB E.Guard."""
    require(run.state.get('pending')is not None and run.remaining_seconds()>0,'root-owned active stage/Guard required')
    out=Path(args.out);require(out.is_dir()and not list(out.iterdir()),'root supplies one empty exclusive output directory')
    for key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    import numpy as np
    import torch
    E=importlib.import_module('effect_identifiability_fit');M=importlib.import_module('compositional_typed_model')
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    counts=dict(neural_forwards=0,training_forwards=0,evaluation_forwards=0,backwards=0,optimizer_updates=0,numerical_fits=0)
    progress=out/'fit-progress.jsonl';plan=read(args.plan);manifest=read(args.manifest);arrays=load_npz(np,args.dataset)
    programs=plan['programs'];codes=[p['code']for p in programs];bits=[p['bits']for p in programs];audit=parity_audit(bits)
    require(len(set(codes))==32 and all(p['partition']==('train'if sum(p['bits'])%2==0 else'held')for p in programs),'program parity partition differs')
    for key,shape in dict(candidate_features=(128,16,8),targets=(128,16,2),target_mask=(128,16,2),selected_candidate_indices=(128,),program_indices=(128,)).items():
        require(key in arrays and arrays[key].shape==shape,'exact native array ABI required: '+key)
        if arrays[key].dtype.kind in'fi':require(np.isfinite(arrays[key]).all(),'finite native array required')
    require(arrays['candidate_features'].dtype==arrays['targets'].dtype==arrays['target_mask'].dtype==np.float32 and np.isin(arrays['target_mask'],[0,1]).all(),'float32 public/labels and explicit masks required')
    q=arrays['program_indices'];selected=arrays['selected_candidate_indices'];require(q.dtype==selected.dtype==np.int64 and np.array_equal(q,np.repeat(np.arange(32),4))and np.all((selected>=0)&(selected<16)),'program/root/intended ordering differs')
    require(np.all(arrays['candidate_features'][...,7].sum(1)==1)and np.all(arrays['candidate_features'][np.arange(128),selected,7]==1),'one explicit BEFORE intended relation required')
    require(manifest.get('fit_admitted')is True and not manifest.get('fit_blockers'),'native/reference/privacy admission must pass before neural fitting')
    require('primary_target_mask'in arrays and arrays['primary_target_mask'].shape==arrays['target_mask'].shape and np.isin(arrays['primary_target_mask'],[0,1]).all(),'explicit committed-intended supervision mask required')
    primary=arrays['primary_target_mask'];require(np.array_equal(primary[...,0],arrays['target_mask'][...,0])and np.all(primary<=arrays['target_mask']),'primary masks must retain native eligibility and only native-known outcomes')
    outside=np.ones((128,16),bool);outside[np.arange(128),selected]=False;require(not primary[...,1][outside].any(),'no unchosen future damage in primary supervision')
    train=np.asarray([i for i in range(128)if sum(bits[int(q[i])])%2==0],np.int64);held=np.asarray([i for i in range(128)if sum(bits[int(q[i])])%2],np.int64);require(len(train)==len(held)==64,'64/64 grouped root split required')
    train_codes=[codes[i]for i in audit['train_programs']];documents=[E.canonical_document(p['raw_card'])[0]for p in programs];fields=np.asarray([M.encode_program(p['raw_card'])for p in programs],np.float32)
    require([M.extract_program_bits(p['raw_card'])for p in programs]==bits,'public bit labels must equal actual typed IR')
    require(all(doc['printed']==documents[0]['printed']for doc in documents)and documents[0]['printed']['types']==['event'],'identical source printed metadata across all synthetic events required')
    require(np.array_equal(arrays['program_bits'],np.asarray(bits,np.int64))and np.array_equal(arrays['typed_features'],fields),'converter/public program fields differ from strict IR parser')
    require(np.array_equal(arrays['train_idx'],train)and np.array_equal(arrays['held_idx'],held)and np.array_equal(arrays['world_ids'],np.arange(128)),'converter group/root split differs')
    require(arrays['program_ids'].astype(str).tolist()==codes and arrays['source_cards'].astype(str).tolist()==[codes[int(i)]for i in q],'provenance identity/order differs')
    require(tuple(CONFIG['candidate_scales'])==M.CANDIDATE_SCALES,'OLD/NEW physical scales must match')
    baseline=arrays['baseline_predictions'];require(baseline.shape==arrays['targets'].shape and np.isfinite(baseline).all()and np.array_equal(baseline[arrays['target_mask']>0],arrays['targets'][arrays['target_mask']>0]),'typed baseline/native admission disagreement blocks learning')
    # Alias/code/title renaming is an input-serialization equality proof, not an
    # extra neural forward. Semantic documents and typed fields must be exact.
    renamed=[]
    for i,p in enumerate(programs):
        raw=copy.deepcopy(p['raw_card']);raw['setCode']='RENAMED_'+str(i)
        for name in('id','title','internalName'):
            if name in raw['card']:raw['card'][name]='opaque-renamed-'+str(i)
        if'setCodes'in raw['card']:raw['card']['setCodes']=[]
        doc=E.canonical_document(raw)[0];require(doc==documents[i]and M.encode_program(raw)==fields[i].tolist(),'semantic rename invariance failed');renamed.append(digest(doc))
    symbols=E.symbols_for(documents);train_symbols=E.symbols_for([documents[i]for i in audit['train_programs']])
    require(symbols==train_symbols,'HELD-only atoms are not admitted by this factorial test')
    token=run.intent('numerical_fits');counts['numerical_fits']+=1;bank,numeric_scale=E.make_bank(documents,codes,train_codes,symbols,False);run.complete(token)
    lists={key:value.tolist()for key,value in arrays.items()};lists['target_mask']=primary.tolist();token=run.intent('numerical_fits');counts['numerical_fits']+=1
    weights=loss_weights(lists['targets'],lists['target_mask'],lists['selected_candidate_indices'],lists['program_indices'],fields.tolist(),train.tolist());run.complete(token)
    identity=bank['identity_indices'];require(all(identity[i]==0 for i in audit['held_programs'])and sorted(int(identity[i])for i in audit['train_programs'])==list(range(1,17)),'held identity must beUNK0')
    restricted={k:v.copy()for k,v in bank.items()}
    for v in restricted.values():v[audit['held_programs']]=0
    np.savez_compressed(out/'consumed-inputs.npz',candidate_features=arrays['candidate_features'],program_fields=fields,program_bits=np.asarray(bits,np.int64),program_indices=q,identity_indices=identity,selected_candidate_indices=selected,
        targets=arrays['targets'],target_mask=arrays['target_mask'],primary_target_mask=primary,**{'old_'+k:v for k,v in bank.items()},**{'old_train_'+k:v for k,v in restricted.items()})
    np.savez_compressed(out/'training-schedule.npz',train_indices=train,held_indices=held,seeds=np.asarray(SEEDS,np.int64),arms=np.asarray(ARMS),program_indices=q,selected_candidate_indices=selected)
    write_new(out/'loss-weights.json',weights)
    label_hashes={k:sha_array(arrays[k])for k in('targets','target_mask')};public_hash=sha_array(arrays['candidate_features'])
    candidates=torch.as_tensor(arrays['candidate_features']);fields_tensor=torch.as_tensor(fields[q]);q_tensor=torch.as_tensor(q);id_tensor=torch.as_tensor(identity[q]);bank_tensor={k:torch.as_tensor(v)for k,v in bank.items()};restricted_tensor={k:torch.as_tensor(v)for k,v in restricted.items()}
    y=torch.as_tensor(arrays['targets'][train]);mask=torch.as_tensor(primary[train]);selected_train=torch.as_tensor(selected[train]);cw=torch.as_tensor(weights['eligibility_class_weights'],dtype=torch.float32);dw=torch.as_tensor(np.asarray(weights['damage_weights'],np.float32)[train]);row=torch.arange(len(train))
    predictions={};initials={};metadata={};checkpoints={}
    def forward(model,family,indices,training,seed,arm,step):
        counts['neural_forwards']+=1;counts['training_forwards'if training else'evaluation_forwards']+=1
        require(counts['neural_forwards']<=3624,'forward cap exceeded');token=run.intent('neural_forwards')
        journal(progress,dict(event='forward-intent',global_forward=counts['neural_forwards'],seed=seed,arm=arm,step=step,kind='train'if training else'evaluate',budget_token=token))
        if family=='old':pred=model(fields_tensor[indices],candidates[indices],id_tensor[indices],q_tensor[indices],restricted_tensor if training else bank_tensor)
        else:pred=model(fields_tensor[indices],candidates[indices],id_tensor[indices])
        run.complete(token);journal(progress,dict(event='forward-complete',global_forward=counts['neural_forwards'],seed=seed,arm=arm,step=step));return pred
    def capture(model,family,seed,arm,step):
        model.eval()
        with torch.inference_mode():pred=forward(model,family,np.arange(128),False,seed,arm,step);eligibility=torch.sigmoid(pred['eligibility_logits']).detach().numpy().copy();damage=pred['signed_damage'].detach().numpy().copy()
        require(np.isfinite(eligibility).all()and np.isfinite(damage).all(),'nonfinite evaluation prediction')
        payload=dict(eligibility=eligibility,damage=damage,program_indices=q,selected_candidate_indices=selected)
        np.savez_compressed(out/f's{seed}-{arm}-step{step}-predictions.npz',**payload);predictions[(seed,arm,step)]=dict(eligibility=eligibility.tolist(),damage=damage.tolist())
    for seed in SEEDS:
        for family in('old','new'):
            torch.manual_seed(seed);template=make_old(torch,symbols,False)if family=='old'else M.make_model(torch,16,False)
            initial={k:v.detach().clone()for k,v in template.state_dict().items()};initial_numpy={k:v.numpy().copy()for k,v in initial.items()};initials[f'{seed}:{family}']=state_hash(initial_numpy)
            np.savez_compressed(out/f's{seed}-{family}-initial-checkpoint.npz',**initial_numpy);del template
            for enabled in(False,True):
                arm=family+('-with-id'if enabled else'-no-id');model=make_old(torch,symbols,enabled)if family=='old'else M.make_model(torch,16,enabled);model.load_state_dict(initial,strict=True)
                loaded=state_hash({k:v.detach().numpy()for k,v in model.state_dict().items()});require(loaded==initials[f'{seed}:{family}'],'paired identity arms require identical family initialization')
                metadata[f'{seed}:{arm}']=dict(initial_state_sha256=loaded,allocated_parameters=sum(p.numel()for p in model.parameters()),trainable_parameters=sum(p.numel()for p in model.parameters()if p.requires_grad),identity_enabled=enabled)
                optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001);capture(model,family,seed,arm,0)
                for step in range(1,301):
                    model.train();optimizer.zero_grad(set_to_none=True);pred=forward(model,family,train,True,seed,arm,step)
                    logits=pred['eligibility_logits'];damage=pred['signed_damage'];elig_loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y[...,0],reduction='none')*cw[y[...,0].long()]*mask[...,0]
                    support=mask[...,0].sum(1);elig=(elig_loss.sum(1)/support.clamp(min=1))[support>0].mean()
                    dmask=mask[row,selected_train,1];dloss=torch.nn.functional.smooth_l1_loss(damage[row,selected_train],y[row,selected_train,1],reduction='none');effect=(dloss*dw*dmask).sum()/dmask.sum().clamp(min=1);objective=.5*elig+.5*effect
                    require(bool(torch.isfinite(objective)),'nonfinite common loss');token=run.intent('backwards');journal(progress,dict(event='backward-intent',global_backward=counts['backwards']+1,seed=seed,arm=arm,step=step,budget_token=token));objective.backward();run.complete(token);counts['backwards']+=1
                    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.);require(bool(torch.isfinite(norm)),'nonfinite gradient')
                    token=run.intent('optimizer_updates');journal(progress,dict(event='optimizer-intent',global_update=counts['optimizer_updates']+1,seed=seed,arm=arm,step=step,budget_token=token));optimizer.step();run.complete(token);counts['optimizer_updates']+=1
                    journal(progress,dict(event='optimizer-complete',global_update=counts['optimizer_updates'],seed=seed,arm=arm,step=step,loss=float(objective.detach()),eligibility_loss=float(elig.detach()),damage_loss=float(effect.detach()),preclip_gradient_norm=float(norm)))
                capture(model,family,seed,arm,300);saved={k:v.detach().numpy().copy()for k,v in model.state_dict().items()};path=out/f's{seed}-{arm}-checkpoint.npz';np.savez_compressed(path,**saved);checkpoints[f'{seed}:{arm}']=dict(pin=pin(path),state_sha256=state_hash(saved))
                metadata[f'{seed}:{arm}']['gradients_at_final_update']={k:dict(rms=float(p.grad.square().mean().sqrt()),elements=p.numel())for k,p in model.named_parameters()if p.grad is not None}
    require(counts=={k:CONFIG[k]for k in counts},'exact fixed comparison exposure required')
    require(label_hashes=={k:sha_array(arrays[k])for k in label_hashes}and public_hash==sha_array(arrays['candidate_features']),'native labels/masks/public inputs changed')
    # First supervised metrics/held gates happen only after every update/call.
    results={};gates={}
    for seed in SEEDS:
        for arm in ARMS:results[f'{seed}:{arm}']={str(step):evaluate(predictions[(seed,arm,step)],lists,bits,train.tolist(),held.tolist())for step in(0,300)}
        for family in('old','new'):gates[f'{seed}:{family}']=success_gate(results[f'{seed}:{family}-no-id']['300'],results[f'{seed}:{family}-with-id']['300'],require_id_drop=family=='new')
    passing={family:all(gates[f'{seed}:{family}']['passed']for seed in SEEDS)for family in('old','new')}
    advantage=[]
    for seed in SEEDS:
        old=results[f'{seed}:old-no-id']['300']['held'];new=results[f'{seed}:new-no-id']['300']['held'];ob=old['eligibility']['balanced_accuracy'];nb=new['eligibility']['balanced_accuracy'];od=old['damage']['mae'];nd=new['damage']['mae']
        complete=all(v is not None for v in(ob,nb,od,nd));oe=((1-ob)+od/3)/2 if complete else None;ne=((1-nb)+nd/3)/2 if complete else None
        advantage.append(dict(seed=seed,old_balanced_accuracy=ob,new_balanced_accuracy=nb,old_damage_mae=od,new_damage_mae=nd,old_composite_error=oe,new_composite_error=ne,
            relative_supported=complete and oe>0,passed=complete and oe>0 and ne<=.9*oe and nb>=ob-1e-6 and nd<=od+1e-6,
            zero_denominator='e_old0 has no supported relative advantage claim. Both adequate models prefer OLD simplicity.'))
    relative=all(v['passed']for v in advantage)
    decision='retain-old-research-only'if passing['old']else'support-new-research-architecture-only'if passing['new']and relative else'stop-composition-comparison-insufficient'
    contract=dict(schema=SCHEMA,config=CONFIG,new_model=M.contract(),old=describe()['old'],symbols=symbols,documents=documents,numeric_scale=numeric_scale,identity_indices=identity.tolist(),
        program_fields=fields.tolist(),program_bits=bits,program_codes=codes,parity_audit=audit,semantic_rename_sha256=renamed,semantic_rename_invariance=True,
        typed_reference_admission=dict(known_coordinates=int(arrays['target_mask'].sum()),mismatches=0,scope='Native-known admission only; analytical values never become training labels.'),
        source_pins=[pin(Path(__file__)),pin(M.__file__),pin(E.__file__),pin(E.prior().__file__)],input_pins=[pin(args.plan),pin(args.dataset),pin(args.manifest)])
    write_new(out/'contract.json',contract)
    result=dict(schema=SCHEMA,status='completed',config=CONFIG,counts=counts,results=results,gates=gates,passing_families=passing,decision=decision,strict_new_advantage=relative and passing['new']and not passing['old'],advantage=advantage,
        initial_state_hashes=initials,arm_metadata=metadata,checkpoints=checkpoints,label_hashes=label_hashes,public_input_sha256=public_hash,semantic_rename_invariance=True,
        metrics_scope='Native eligibility allcandidates; damage ONLYobserved intended. Held metrics firstcomputedafterall3600updates; sourceheadsunused. Syntheticcomposition is notactualcard/decktransfer.',semantic_validated=False)
    write_new(out/'result.json',result)
    return dict(result=pin(out/'result.json'),contract=pin(out/'contract.json'),counts=counts,decision=decision,semantic_validated=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--describe',action='store_true',required=True);parser.parse_args();print(json.dumps(describe(),indent=2))


if __name__=='__main__':main()
