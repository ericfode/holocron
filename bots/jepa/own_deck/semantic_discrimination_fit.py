"""Fixed-capacity semantic-discrimination assay; coordinator freeze/GO only.

All five arms use identical corrected C1R1 public inputs. Only the card
representation/control changes. Importing this module performs no numerical or
neural operation, campaign initialization, data conversion or execution.
"""
import os
for _key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/'experiments'/'semantic-discrimination-v1'
ARMS=('learned-full','frozen-full','printed-only','ID-only','public-only')
SEEDS=(17,29,43)
SECONDS=dict(metadata=3.,prep=5.,fit=45.,baselines=5.)
CONFIG=dict(arms=list(ARMS),seeds=list(SEEDS),updates_per_arm=200,batch='complete-TRAIN-frozen-order',
    optimizer_updates=3000,training_forwards=3000,correct_evaluation_forwards=30,ability_swapped_evaluation_forwards=15,evaluation_forwards=45,neural_forwards=3045,backwards=3000,
    export_forwards=0,native_applies=0,numerical_fits=0,learning_rate=.003,weight_decay=.0001,clip_l2=1.,seconds=45.,cpu_workers=1,rss_bytes=1073741824,
    context_width=32,candidate_width=43,card_width=16,head_width=32,task='actual-intent-endpoints',semantic_validated=False)
BASE_CONFIG=dict(head_fit_attempts=16,ridge_lambda=1.,intercept_penalized=False,feature_columns=75,train_id_columns=0,seconds=5.,neural_forwards=0,optimizer_updates=0,native_applies=0)


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def read(path):return json.loads(Path(path).read_text())
def require(value,message):
    if not value:raise ValueError(message)
def sha_array(value):return hashlib.sha256(str(value.dtype).encode()+str(value.shape).encode()+value.tobytes()).hexdigest()
def state_hash(values):return hashlib.sha256(json.dumps({n:sha_array(values[n])for n in sorted(values)},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def json_native(value,np=None):
    if np is not None and isinstance(value,np.generic):return json_native(value.item(),np)
    if isinstance(value,dict):return{json_native(k,np):json_native(v,np)for k,v in value.items()}
    if isinstance(value,(tuple,list)):return[json_native(v,np)for v in value]
    if value is None or type(value)in(bool,int,float,str):return value
    raise TypeError('unsupported JSON value, no stringify/array fallback: '+type(value).__name__)
def write_new(path,value,np=None):
    encoded=json.dumps(json_native(value,np),indent=2,allow_nan=False)+'\n'
    with Path(path).open('x')as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
def journal(path,value):
    with Path(path).open('a')as stream:stream.write(json.dumps(value,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
def npz(np,path):
    with np.load(path,allow_pickle=False)as values:return{k:values[k].copy()for k in values.files}
def modules():return tuple(importlib.import_module(n)for n in('effect_identifiability_fit','public_input_binding_model_v1','semantic_discrimination_bank'))
def campaign(spec):
    A=importlib.import_module('semantic_discrimination_accounting');return A,A.Campaign(spec)


def partitions(arrays,split):
    import numpy as np
    result={k:np.asarray(split['root_partitions'][k],np.int64)for k in('train','state_held','family_held','joint')}
    flat=[int(i)for values in result.values()for i in values]
    require(sorted(flat)==list(range(len(arrays['source_cards'])))and len(set(flat))==len(flat),'explicit disjoint complete root partitions required')
    return result


def validate_data(arrays,manifest,plan):
    import numpy as np
    n=len(arrays['source_cards']);require(n==33 and len(plan['codes'])==8 and len(plan['train_codes'])==6,'frozen33-root/eight-card/six-TRAIN cohort required')
    for key,shape in dict(context_features=(n,18),candidate_features=(n,8,34),source_targets=(n,9),source_mask=(n,9),targets=(n,8,7),target_mask=(n,8,7),selected_candidate_indices=(n,),state_families=(n,)).items():
        require(arrays[key].shape==shape,'array shape differs: '+key)
        if arrays[key].dtype.kind in'fi':require(np.isfinite(arrays[key]).all(),'nonfinite array: '+key)
    require(arrays['selected_candidate_indices'].dtype==np.int64 and np.all((arrays['selected_candidate_indices']>=0)&(arrays['selected_candidate_indices']<8)),'pre-action selected index required')
    for key in('source_mask','target_mask'):require(np.isin(arrays[key],[0,1]).all(),'binary known masks required')
    require(set(arrays['source_cards'].astype(str))==set(plan['codes']),'source identities differ')
    parts=partitions(arrays,plan['split']);require([len(v)for v in parts.values()]==[13,12,4,4],'frozen13/12/4/4 root split differs')
    train=set(plan['train_codes']);codes=arrays['source_cards'].astype(str)
    require(set(codes[parts['train']])==train and all(codes[i]in train for k in('train','state_held')for i in parts[k])and all(codes[i]not in train for k in('family_held','joint')for i in parts[k]),'card/TRAIN split differs')
    require(not manifest.get('fit_blockers')and not manifest.get('errors',0),'native blockers stop fit; unknown futures remain masks0')
    require(manifest['public_binding_contract']['task']==CONFIG['task'],'actual-intent task only')
    for y,m,n,b in(('source_targets','source_mask','source_head_names','source_binary_heads'),('targets','target_mask','target_names','binary_heads')):
        for name in manifest[b]:
            h=manifest[n].index(name);require(np.isin(arrays[y][...,h][arrays[m][...,h]>0],[0,1]).all(),'known binary labels must be0/1')
    return parts


def metrics(source,branch,arrays,manifest,plan):
    import numpy as np
    E=importlib.import_module('effect_identifiability_fit');result={}
    for cell,indices in partitions(arrays,plan['split']).items():
        heads=E.head_metrics(source,branch,arrays,manifest,plan['scalers'],indices)
        for p,ykey,mkey,skey in((source,'source_targets','source_mask','source_targets'),(branch,'targets','target_mask','targets')):
            for h,spec in enumerate(plan['scalers'][skey]):
                y=arrays[ykey][indices,...,h];prediction=p[indices,...,h];known=arrays[mkey][indices,...,h]>0;v=(prediction-y)[known]
                sign=lambda x:np.where(x>.25,1,np.where(x<-.25,-1,0))
                heads[spec['name']].update(rmse=float(np.sqrt(np.mean(v*v)))if len(v)else None,max_abs_error=float(np.max(abs(v)))if len(v)else None,
                    zero_sign_accuracy=float((sign(prediction)[known]==sign(y)[known]).mean())if len(v)and not spec['binary']else None)
        per_card={code:E.head_metrics(source,branch,arrays,manifest,plan['scalers'],[int(i)for i in indices if str(arrays['source_cards'][i])==code])for code in sorted(set(arrays['source_cards'][indices].astype(str)))}
        result[cell]=dict(heads=heads,per_card=per_card,source_scope='Auxiliary source lifecycle, not the held behavioral primary.')
    return result


def primary_scores(branch,arrays,manifest,plan):
    """Two predeclared held-card groups, native-unit root-balanced errors."""
    import numpy as np
    parts=partitions(arrays,plan['split']);held=np.concatenate((parts['family_held'],parts['joint']));codes=arrays['source_cards'].astype(str);output={}
    spec={'ASH_081':['target_damage_delta'],'IBH_104':['target_allowed','target_removed']}
    for code,names in spec.items():
        heads={}
        for name in names:
            h=manifest['target_names'].index(name);roots=[]
            for i in held:
                if codes[i]!=code:continue
                mask=arrays['target_mask'][i,:,h]>0
                if 'primary_target_mask'in arrays:mask&=arrays['primary_target_mask'][i,:,h]>0
                else:
                    mask&=arrays['candidate_features'][i,:,6]==0
                    mask&=np.asarray([r in('anchor_a','anchor_b')for r in manifest['candidate_order']])
                if mask.any():
                    truth=arrays['targets'][i,:,h][mask];prediction=branch[i,:,h][mask];roots.append(dict(root=int(i),known=int(mask.sum()),mae=float(abs(prediction-truth).mean()),truth=truth.tolist(),prediction=prediction.tolist()))
            heads[name]=dict(roots=roots,known_roots=len(roots),mae=float(np.mean([r['mae']for r in roots]))if roots else None)
        values=[r['mae']for r in heads.values()]
        output[code]=dict(heads=heads,mae=float(np.mean(values))if all(v is not None for v in values)else None,scope='Equal head means of root-balanced known native coordinates; unknown removal/futures excluded.')
    return output


def paired_scores(branch,arrays,manifest,plan):
    """Eligibility difference-of-differences; not a legal-action ranking claim."""
    import numpy as np
    pairs=[];allowed=manifest['target_names'].index('target_allowed');order=manifest['candidate_order']
    for pair in plan.get('primary_pairs',[]):
        left=int(pair['left_root']);right=int(pair['right_root']);a=order.index(pair.get('anchor_a','anchor_a'));b=order.index(pair.get('anchor_b','anchor_b'))
        known=all(arrays['target_mask'][i,j,allowed]>0 for i in(left,right)for j in(a,b))
        row=dict(id=pair['id'],left_root=left,right_root=right,known=known)
        if known:
            truth=float((arrays['targets'][left,a,allowed]-arrays['targets'][left,b,allowed])-(arrays['targets'][right,a,allowed]-arrays['targets'][right,b,allowed]))
            prediction=float((branch[left,a,allowed]-branch[left,b,allowed])-(branch[right,a,allowed]-branch[right,b,allowed]));row.update(truth=truth,prediction=prediction,absolute_error=abs(prediction-truth),direction_correct=bool(prediction*truth>0))
        pairs.append(row)
    known_pairs=[p for p in pairs if p['known']]
    # Eligibility ranking is scored separately on genuinely differing known
    # membership labels. No unexecuted action outcome is manufactured here.
    rankings=[]
    for pair in plan.get('primary_pairs',[]):
        for i in(int(pair['left_root']),int(pair['right_root'])):
            a=order.index(pair.get('anchor_a','anchor_a'));b=order.index(pair.get('anchor_b','anchor_b'))
            if arrays['target_mask'][i,a,allowed]and arrays['target_mask'][i,b,allowed]:
                truth=float(arrays['targets'][i,a,allowed]-arrays['targets'][i,b,allowed])
                if truth:rankings.append(dict(root=i,correct=bool((branch[i,a,allowed]-branch[i,b,allowed])*truth>0)))
    action_ranks=[]
    for pair in plan.get('primary_spec',{}).get('rank_pairs',[]):
        left=int(pair['left_root']);right=int(pair['right_root']);h=manifest['target_names'].index(pair['head']);anchors=[order.index(r)for r in pair['anchors']]
        known=all(arrays['target_mask'][i,j,h]>0 for i in(left,right)for j in anchors)
        committed='chosen_only_target_mask'in arrays and all(arrays['chosen_only_target_mask'][i,arrays['selected_candidate_indices'][i],h]>0 for i in(left,right))
        row=dict(id=pair['id'],left_root=left,right_root=right,known=bool(known),both_committed=bool(committed),eligible=False)
        if known and committed:
            sign=float(pair['utility_sign']);truth=[float(sign*arrays['targets'][i,anchors,h].sum())for i in(left,right)];pred=[float(sign*branch[i,anchors,h].sum())for i in(left,right)]
            difference=truth[0]-truth[1];row.update(native_utilities=truth,predicted_utilities=pred,native_difference=difference,predicted_difference=pred[0]-pred[1])
            if abs(difference)>.25:row.update(eligible=True,correct=bool((pred[0]-pred[1])*difference>0))
        action_ranks.append(row)
    eligible=[r for r in action_ranks if r['eligible']]
    return dict(pairs=pairs,known_pairs=len(known_pairs),direction_accuracy=float(np.mean([p['direction_correct']for p in known_pairs]))if known_pairs else None,
        eligibility_rankings=rankings,eligibility_rank_accuracy=float(np.mean([p['correct']for p in rankings]))if rankings else None,
        action_outcome_rank_pairs=action_ranks,eligible_action_rank_pairs=len(eligible),action_outcome_rank_accuracy=float(np.mean([r['correct']for r in eligible]))if eligible else None,
        action_outcome_rank_scope='Predeclared ASH081 world1 two actually committed intent outcomes only; utility is negative total anchor damage delta. Eligibility ranking is separate; unsupported futures are never fabricated.')


def evaluation(source,branch,arrays,manifest,plan):return dict(cells=metrics(source,branch,arrays,manifest,plan),primary=primary_scores(branch,arrays,manifest,plan),paired_contrasts=paired_scores(branch,arrays,manifest,plan))


def configure_model(model,arm,M):
    require(arm in ARMS,'unreviewed representation arm')
    control='rich-id-only'if arm=='ID-only'else'rich-untrained-typed'if arm in('frozen-full','public-only')else'rich-typed'
    M.configure_arm(model,control);original=model.card_bank;gate=0. if arm=='public-only'else 1.
    model.card_bank=lambda bank:original(bank)*gate
    return control


def gate_results(fit,baselines):
    """Fixed group-by-seed control gate plus separate ability-sensitivity gate."""
    groups=('ASH_081','IBH_104');controls=ARMS[1:]+('zero','train_mean','public_ridge');comparisons=[];pooled=[];sensitivity=[];invariants=[];paired=[]
    for group in groups:
        for control in controls:
            learned=[];other=[]
            for seed in SEEDS:
                left=fit['results'][f's{seed}:learned-full']['evaluations']['200']['primary'][group]['mae']
                right=(fit['results'][f's{seed}:{control}']['evaluations']['200']if control in ARMS else baselines['evaluations'][control])['primary'][group]['mae']
                comparisons.append(dict(group=group,seed=seed,control=control,learned=left,control_error=right,passed=bool(left is not None and right is not None and left<right)))
                learned.append(left);other.append(right)
            valid=all(v is not None for v in learned+other);l=sum(learned)/3 if valid else None;r=sum(other)/3 if valid else None
            pooled.append(dict(group=group,control=control,learned=l,control_error=r,reduction=(r-l)/r if valid and r>0 else None,passed=bool(valid and r>0 and l<=.9*r)))
        correct=[];swapped=[]
        for seed in SEEDS:
            item=fit['results'][f's{seed}:learned-full'];a=item['evaluations']['200']['primary'][group]['mae'];b=item['ability_swapped_evaluation']['primary'][group]['mae'];correct.append(a);swapped.append(b)
            sensitivity.append(dict(group=group,seed=seed,correct=a,ability_swapped=b,passed=bool(a is not None and b is not None and b>a)))
        valid=all(v is not None for v in correct+swapped);a=sum(correct)/3 if valid else None;b=sum(swapped)/3 if valid else None
        sensitivity.append(dict(group=group,seed='pooled',correct=a,ability_swapped=b,worsening=(b-a)/a if valid and a>0 else None,passed=bool(valid and a>0 and b>a and b>=1.1*a)))
    for seed in SEEDS:
        item=fit['results'][f's{seed}:learned-full']['evaluations']['200']['paired_contrasts'];pairs=item['pairs']
        d_ok=len(pairs)==4 and all(p['known']and p.get('direction_correct')for p in pairs)
        ranking=item['action_outcome_rank_accuracy'];rank_supported=item['eligible_action_rank_pairs']>0
        paired.append(dict(seed=seed,D_passed=d_ok,actual_rank_supported=rank_supported,actual_rank_accuracy=ranking,rank_passed=bool(rank_supported and ranking>=.75)))
        for arm in('printed-only','ID-only','public-only'):invariants.append(dict(seed=seed,arm=arm,passed=fit['results'][f's{seed}:{arm}']['ability_swap_prediction_identical']))
    primary=all(c['passed']for c in comparisons+pooled)and all(p['D_passed']for p in paired)
    return dict(primary_behavior_gate_passed=primary,control_comparisons=comparisons,pooled_group_reductions=pooled,paired_requirements=paired,
        ability_sensitivity_gate_passed=all(r['passed']for r in sensitivity+invariants),ability_sensitivity=sensitivity,invariant_controls=invariants,
        actual_rank_diagnostic_passed=all(p['rank_passed']for p in paired),actual_rank_scope='Separate diagnostic; never part of the primary control/D gate.',
        semantic_validated=False,scope='Selected two held actual-card groups and predeclared native scenarios only; unique printed profiles and correlated observations prevent a broad semantic claim.')


def input_arrays(arrays,manifest,scalers=None):
    M=importlib.import_module('public_input_binding_model_v1');return M.project_arrays(arrays,manifest,'C1R1',scalers=scalers)


def run_stage(args,stage,inputs,worker,progress=None):
    A,C=campaign(args.spec)
    with C.lease()as(stream,rows,current):
        allowed=C.allowed_pins(rows);expected=[allowed.get(str(Path(p).resolve()))for p in inputs];receipt_path=args.out.parent/(args.out.name+'-stage-receipt.json')
        meta=C.metadata(stage,[p for p in expected if p is not None]);started=time.monotonic();status='failed';error=None;created=False;guard=None;result=None
        observed=A.zero_counts()
        try:
            C.start(stream,rows,stage,meta)
            actual=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
            outputs=([str(args.native_plan.resolve())]if stage=='metadata'else[])+[str(args.out.resolve())]+([str(progress.resolve())]if progress else[])+[str(receipt_path.resolve())]
            require(meta['argv']==actual and meta['outputs']==outputs,'actual command/output paths differ from frozen stage')
            require(all(p is not None for p in expected),'all stage inputs must have frozen/completed pins')
            require(not args.out.exists()and not receipt_path.exists()and(not progress or not progress.exists())and(stage!='metadata'or not args.native_plan.exists()),'all attempt paths exclusive; no retry/reset')
            pending=C.state(rows)['pending'];remaining=SECONDS[stage]-(time.monotonic()-pending['started_monotonic_seconds']);require(remaining>0,'stage startup exhausted allocation')
            E=importlib.import_module('effect_identifiability_fit');remaining=SECONDS[stage]-(time.monotonic()-pending['started_monotonic_seconds']);require(remaining>0,'safe frontend import exhausted allocation')
            guard=E.Guard(remaining);args.out.mkdir(parents=True);created=True
            args._source_freeze_commit=C.config.get('provenance',{}).get('source_freeze_commit')
            with guard:
                result=worker(args,allowed)
                observed=json_native(result.pop('_observed',A.zero_counts()),sys.modules.get('numpy'))
                result=json_native(result,sys.modules.get('numpy'))
            status='completed'
        except BaseException as exc:
            pending=C.state(rows)['pending']
            if pending is None or pending['stage']!=stage or pending['owner_pid']!=os.getpid():raise
            error=dict(type=type(exc).__name__,message=str(exc))
            if stage=='fit':observed.update(neural_forwards=None,optimizer_updates=None)
            if stage=='baselines':observed['numerical_fits']=None
        elapsed=time.monotonic()-started
        if elapsed>SECONDS[stage]:status='failed';error=error or dict(type='BudgetExceeded',message=stage+' wall reservation exceeded')
        artifacts=[pin(p)for p in sorted(args.out.rglob('*'))if p.is_file()]if created else[]
        if created and stage=='metadata'and args.native_plan.exists():artifacts.append(pin(args.native_plan))
        receipt=dict(status=status,error=error,active_seconds=elapsed,observed=observed,outputs=result,artifact_pins=artifacts,source=pin(__file__),guard=guard.receipt()if guard else None,semantic_validated=False,
            accounting_authority='Canonical ledger controls final status including receipt/proof writes. Failed reserved exposure is retained; no retry or credit.')
        receipt_pin=None
        try:write_new(receipt_path,receipt);receipt_pin=pin(receipt_path)
        except BaseException as exc:status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        proofs=artifacts+([receipt_pin]if receipt_pin else[])+([pin(progress)]if progress and progress.exists()else[])
        counter=pin(progress)if status=='completed'and progress else None
        finished=C.finish(stream,rows,status,elapsed,observed,proofs,cleanup_verified=True,execution_ended=True,observed_verified=status=='completed',counter_proof=counter)
        require(status=='completed'and stage in finished['completed_stages'],'failed bounded '+stage+' retained; ledger is authoritative: '+str(error))
        return receipt


def metadata_worker(args,allowed):
    import numpy as np
    E,M,B=modules();P=importlib.import_module('semantic_discrimination_plan')
    native=P.prepare_plan();write_new(args.native_plan,native,np)
    prepared=B.prepare_bank_metadata(native)
    prepared.update(fit_schema='jepa-semantic-discrimination-fit/1',status='prepared-no-neural-execution',config=CONFIG,
        native_plan=pin(args.native_plan),split=native['split'],primary_pairs=native['primary_pairs'],primary_spec=native['primary_spec'],semantic_validated=False)
    counts=prepared['parameters'];prepared['arm_parameters']={arm:dict(allocated=counts['allocated'],trainable=counts['trainable']['rich-id-only'if arm=='ID-only'else'rich-untrained-typed'if arm in('frozen-full','public-only')else'rich-typed'])for arm in ARMS}
    banks=B.banks_from_metadata(prepared,training=False);restricted=B.banks_from_metadata(prepared,training=True)
    np.savez_compressed(args.out/'program-inputs.npz',**{flavor+'_'+key:value for flavor,bank in banks.items()for key,value in bank.items()},**{'restricted_'+flavor+'_'+key:value for flavor,bank in restricted.items()for key,value in bank.items()})
    sources=[Path(__file__),HERE/'test_semantic_discrimination_fit.py',HERE/'semantic_discrimination_bank.py',HERE/'test_semantic_discrimination_bank.py',HERE/'semantic_discrimination_plan.py',HERE/'semantic_discrimination_data.py',HERE/'semantic_discrimination_accounting.py',HERE/'public_input_binding_model_v1.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',args.native_plan]
    prepared['pins']=[pin(p)for p in sources];write_new(args.out/'learner-prepared.json',prepared,np)
    source=HERE/'semantic_discrimination_native_collector'/'supervise.py'
    import importlib.util
    spec=importlib.util.spec_from_file_location('semantic_native_metadata_writer',source);native_guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(native_guard)
    manifest=native_guard.write_source_manifest(args.native_plan,args.out/'native-source-manifest.json',ROOT,args._source_freeze_commit)
    return dict(prepared=pin(args.out/'learner-prepared.json'),bank_inputs=pin(args.out/'program-inputs.npz'),native_plan=pin(args.native_plan),native_source_manifest=manifest,semantic_validated=False)


def consumed_audits(arrays,manifest,plan,banks,x,c):
    import numpy as np
    E,M,_=modules();report={};full=dict(zip(plan['codes'],E.tensor_signatures(banks['full'])));printed=dict(zip(plan['codes'],E.tensor_signatures(banks['printed'])))
    for arm in ARMS:
        signatures=[]
        for code in arrays['source_cards'].astype(str):signatures.append('PUBLIC-ZERO'if arm=='public-only'else'ID:'+str(plan['train_codes'].index(code)+1 if code in plan['train_codes']else 0)if arm=='ID-only'else printed[code]if arm=='printed-only'else full[code])
        inputs=M.consumed_input_hashes(x,c,signatures,arrays['selected_candidate_indices']);seen={};conflicts=[]
        for kind,ykey,mkey,names in(('source','source_targets','source_mask',manifest['source_head_names']),('candidate','targets','target_mask',manifest['target_names'])):
            for i in range(len(x)):
                y=arrays[ykey][i:i+1]if kind=='source'else arrays[ykey][i];mask=arrays[mkey][i:i+1]if kind=='source'else arrays[mkey][i]
                for j in range(len(y)):
                    signature=inputs[i]['source']if kind=='source'else inputs[i]['candidate'][j]
                    for h,name in enumerate(names):
                        if not mask[j,h]:continue
                        key=(kind,signature,name);value=float(y[j,h])
                        if key in seen and seen[key][0]!=value:conflicts.append(dict(kind=kind,head=name,root=i,candidate=j,old_root=seen[key][1],old_value=seen[key][0],value=value))
                        else:seen[key]=(value,i)
        report[arm]=dict(conflict_count=len(conflicts),conflicts=conflicts,consumed_signatures=inputs)
    return report


def prep_worker(args,allowed):
    import numpy as np
    E,M,B=modules();D=importlib.import_module('semantic_discrimination_data');plan=read(args.metadata);native=read(args.native_plan)
    E.verify_pins(plan['pins']);require(plan['config']==CONFIG and plan['native_plan']==pin(args.native_plan),'prepared frozen science differs')
    raw=read(args.native_receipt);assembled=D.G.assembled_catalog(D.G.PINNED_KESSEL/'compiler/generated')
    arrays,manifest=D.convert_receipt(raw,native,assembled,args.journal)
    parts=validate_data(arrays,manifest,plan);x,c=input_arrays(arrays,manifest);expanded=dict(arrays,context_features=x,candidate_features=c)
    plan['scalers']=E.common_scalers(expanded,manifest,parts['train']);scaledx,scaledc=input_arrays(arrays,manifest,plan['scalers'])
    banks=B.banks_from_metadata(plan,training=False);plan['input_audits']=consumed_audits(arrays,manifest,plan,banks,scaledx,scaledc)
    require(plan['input_audits']['learned-full']['conflict_count']==0,'correct full consumed input/known-label contradictions stop fit')
    damage=manifest['target_names'].index('target_damage_delta');base=manifest['candidate_order'].index('own_base');train_values=arrays['targets'][parts['train'],base,damage][arrays['target_mask'][parts['train'],base,damage]>0]
    require(-3. in train_values and -1. in train_values,'observed native TRAIN own-base heal3/heal1 support required')
    paired=paired_scores(arrays['targets'],arrays,manifest,plan);require(len(paired['pairs'])==4 and all(p['known']for p in paired['pairs'])and sorted(set(p['truth']for p in paired['pairs']))==[-2.,2.],'predeclared native eligibility D support differs')
    for pair in plan['primary_pairs']:
        a,b=int(pair['left_root']),int(pair['right_root'])
        require(np.array_equal(x[a],x[b])and np.array_equal(c[a,1:],c[b,1:])and np.array_equal(scaledx[a],scaledx[b])and np.array_equal(scaledc[a,1:],scaledc[b,1:]),'paired PUBLIC consumed non-source inputs differ; source-row0 may differ')
    anchors=[manifest['candidate_order'].index(r)for r in('anchor_a','anchor_b')]
    require('primary_target_mask'in arrays,'explicit frozen primary coordinate mask required')
    expected=np.zeros_like(arrays['target_mask'])
    for i,code in enumerate(arrays['source_cards'].astype(str)):
        names=['target_damage_delta']if code=='ASH_081'else['target_allowed','target_removed']if code=='IBH_104'else[]
        for name in names:
            h=manifest['target_names'].index(name);expected[i,anchors,h]=arrays['target_mask'][i,anchors,h]
    require(np.array_equal(arrays['primary_target_mask'],expected),'primary masks must be exactly known held-card anchor coordinates')
    dataset=args.out/'dataset.npz';mp=args.out/'dataset.manifest.json';sealed=args.out/'sealed-fit-plan.json'
    np.savez_compressed(dataset,**arrays);manifest.update(source_pins=[pin(__file__),pin(HERE/'semantic_discrimination_data.py'),pin(args.metadata),pin(args.native_plan),pin(args.native_receipt),pin(args.journal)],native_receipt=pin(args.native_receipt),journal=pin(args.journal),artifact=pin(dataset));write_new(mp,manifest,np)
    plan.update(status='sealed-awaiting-root-GO',dataset=str(dataset.resolve()),manifest=str(mp.resolve()),metadata=pin(args.metadata),native_support=dict(train_base_damage_values=sorted(set(float(v)for v in train_values)),eligibility=paired),semantic_validated=False)
    plan['pins'] +=[pin(dataset),pin(mp)];write_new(sealed,plan,np)
    return dict(dataset=pin(dataset),manifest=pin(mp),sealed_plan=pin(sealed),fit_admitted=True,semantic_validated=False)


def load_sealed(path):
    import numpy as np
    E,_,_=modules();plan=read(path);E.verify_pins(plan['pins'])
    require(plan['status']=='sealed-awaiting-root-GO'and plan['config']==CONFIG and plan['fit_schema']=='jepa-semantic-discrimination-fit/1','exact sealed fit contract required')
    arrays=npz(np,plan['dataset']);manifest=read(plan['manifest']);parts=validate_data(arrays,manifest,plan)
    return plan,arrays,manifest,parts


def immutable_hashes(arrays):return{k:sha_array(arrays[k])for k in('targets','target_mask','source_targets','source_mask','selected_candidate_indices')}


def fit_worker(args,allowed):
    import numpy as np
    import torch
    E,M,B=modules();torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    plan,arrays,manifest,parts=load_sealed(args.plan);batch=parts['train'];hashes=immutable_hashes(arrays)
    raw_banks=B.banks_from_metadata(plan,training=False);raw_restricted=B.banks_from_metadata(plan,training=True)
    np.savez_compressed(args.out/'program-inputs.npz',**{flavor+'_'+key:value for flavor,bank in raw_banks.items()for key,value in bank.items()},**{'restricted_'+flavor+'_'+key:value for flavor,bank in raw_restricted.items()for key,value in bank.items()})
    banks={name:{k:torch.as_tensor(v)for k,v in bank.items()}for name,bank in raw_banks.items()};restricted={name:{k:torch.as_tensor(v)for k,v in bank.items()}for name,bank in raw_restricted.items()}
    ix,ic=input_arrays(arrays,manifest,plan['scalers']);x,c=map(torch.as_tensor,(ix,ic));q=torch.as_tensor([plan['codes'].index(str(code))for code in arrays['source_cards']]);selected=torch.as_tensor(arrays['selected_candidate_indices'])
    np.savez_compressed(args.out/'consumed-inputs.npz',context=ix,candidate=ic)
    np.savez_compressed(args.out/'training-schedule.npz',train_indices=batch,seeds=np.asarray(SEEDS,np.int64),arms=np.asarray(ARMS),selected_candidate_indices=arrays['selected_candidate_indices'],source_cards=arrays['source_cards'],donor_indices=np.asarray([plan['codes'].index(plan['donors'][code])for code in plan['codes']],np.int64))
    labels={k:torch.as_tensor(arrays[k][batch].copy())for k in('source_targets','source_mask','targets','target_mask')};results={};counts=dict(optimizer_updates=0,training_forwards=0,evaluation_forwards=0,correct_evaluation_forwards=0,ability_swapped_evaluation_forwards=0,backwards=0)
    def forward_intent(kind,arm,seed,step,variant=None):
        key='training_forwards'if kind=='train'else'evaluation_forwards';counts[key]+=1
        if kind=='evaluate':counts['ability_swapped_evaluation_forwards'if variant=='ability-swapped'else'correct_evaluation_forwards']+=1
        require(counts[key]<=CONFIG[key],'fixed forward ceiling exceeded')
        journal(args.progress,dict(event='forward-intent',kind=kind,arm=arm,seed=seed,step=step,eval_variant=variant,global_forward=counts['training_forwards']+counts['evaluation_forwards']))
    def predict(model,bank,representation,arm,seed,step,variant):
        model.eval();forward_intent('evaluate',arm,seed,step,variant)
        with torch.inference_mode():sp,bp,vectors=model(x,c,q,bank,representation,selected);source,branch=E.prior().decode(torch,sp,bp,plan['scalers'])
        vectors=vectors.detach().numpy().copy();require(all(np.isfinite(v).all()for v in(source,branch,vectors)),'nonfinite predictions/vectors')
        suffix='-ability-swapped'if variant=='ability-swapped'else'';path=args.out/f's{seed}-{arm}-step{step}{suffix}-predictions.npz'
        np.savez_compressed(path,source=source,branch=branch,card_vectors=vectors,source_cards=arrays['source_cards'],state_families=arrays['state_families'],selected_candidate_indices=arrays['selected_candidate_indices'])
        return evaluation(source,branch,arrays,manifest,plan),(source.copy(),branch.copy(),vectors)
    for seed in SEEDS:
        torch.manual_seed(seed);template=M.make_model(torch,plan['vocabularies'],len(plan['codes']),len(plan['train_codes']));initial={n:v.detach().clone()for n,v in template.state_dict().items()};initial_np={n:v.numpy()for n,v in initial.items()};master=state_hash(initial_np)
        np.savez_compressed(args.out/f's{seed}-initial-checkpoint.npz',**initial_np);del template
        for arm in ARMS:
            model=M.make_model(torch,plan['vocabularies'],len(plan['codes']),len(plan['train_codes']));model.load_state_dict(initial,strict=True);loaded=state_hash({n:v.detach().numpy()for n,v in model.state_dict().items()});require(loaded==master,'arm full initialization differs')
            representation=configure_model(model,arm,M);flavor='printed'if arm=='printed-only'else'full';swap_flavor='swapped_printed'if arm=='printed-only'else'swapped_full'
            optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=CONFIG['learning_rate'],weight_decay=CONFIG['weight_decay']);evaluations={};gradients={}
            evaluations['0'],_=predict(model,banks[flavor],representation,arm,seed,0,'correct')
            for step in range(1,201):
                model.train();optimizer.zero_grad(set_to_none=True);forward_intent('train',arm,seed,step)
                sp,bp,_=model(x[batch],c[batch],q[batch],restricted[flavor],representation,selected[batch]);objective=E.fixed_loss(torch,sp,bp,labels,plan['scalers']);require(bool(torch.isfinite(objective)),'nonfinite fixed objective');objective.backward();counts['backwards']+=1
                if step==200:gradients={n:dict(rms=float(p.grad.square().mean().sqrt()),nonzero=int(torch.count_nonzero(p.grad)),elements=p.numel())for n,p in model.named_parameters()if p.grad is not None}
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),CONFIG['clip_l2']);require(bool(torch.isfinite(norm)),'nonfinite gradient')
                journal(args.progress,dict(event='optimizer-intent',global_update=counts['optimizer_updates']+1,arm=arm,seed=seed,arm_update=step));optimizer.step();counts['optimizer_updates']+=1
                journal(args.progress,dict(event='optimizer-update',global_update=counts['optimizer_updates'],arm=arm,seed=seed,arm_update=step,loss=float(objective.detach()),preclip_gradient_norm=float(norm)))
            evaluations['200'],correct=predict(model,banks[flavor],representation,arm,seed,200,'correct');swapped_evaluation,swapped=predict(model,banks[swap_flavor],representation,arm,seed,200,'ability-swapped')
            weights={n:v.detach().numpy().copy()for n,v in model.state_dict().items()};checkpoint=args.out/f's{seed}-{arm}-checkpoint.npz';np.savez_compressed(checkpoint,**weights)
            movement={n:dict(delta_l2=float(np.linalg.norm((v-initial_np[n]).astype(np.float64))),changed=int(np.count_nonzero(v!=initial_np[n])),elements=v.size)for n,v in weights.items()}
            results[f's{seed}:{arm}']=dict(evaluations=evaluations,ability_swapped_evaluation=swapped_evaluation,ability_swap_prediction_identical=all(np.array_equal(a,b)for a,b in zip(correct,swapped)),checkpoint=pin(checkpoint),initial_state_sha256=loaded,master_initial_state_sha256=master,weight_movement=movement,last_step_preclip_gradients=gradients)
    require(all(counts[k]==CONFIG[k]for k in counts),'exact 3000 train/backward/update +30correct/15swap exposure required');require(hashes==immutable_hashes(arrays),'true labels/masks/intent changed');E.verify_pins(plan['pins'])
    contract=dict(plan=pin(args.plan),source=pin(__file__),config=CONFIG,scalers=plan['scalers'],parameters=plan['parameters'],arm_parameters=plan['arm_parameters'],vocabularies=plan['vocabularies'],donors=plan['donors'],bank_contract=plan['bank_contract']);write_new(args.out/'contract.json',contract,np)
    result=dict(status='completed',config=CONFIG,counts=counts,results=results,true_label_hashes=hashes,all_inputs_unchanged=True,input_audits=plan['input_audits'],semantic_validated=False,task=CONFIG['task'],scope='All arms use identical corrected C1R1 inputs and actual-intent masks. Held unique printed profiles make shortcut controls empirical, not a logical impossibility proof. Source-self excluded from held primary.')
    write_new(args.out/'result.json',result,np)
    return dict(result=pin(args.out/'result.json'),counts=counts,_observed=dict(native_applies=0,neural_forwards=3045,optimizer_updates=3000,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.),semantic_validated=False)


def baseline_features(arrays,manifest,plan):
    import numpy as np
    x,c=input_arrays(arrays,manifest,plan['scalers']);selected=arrays['selected_candidate_indices'];source=np.concatenate((x,c[np.arange(len(x)),selected]),-1);branch=np.concatenate((np.broadcast_to(x[:,None,:],(*c.shape[:2],x.shape[-1])),c),-1)
    require(source.shape[-1]==branch.shape[-1]==75,'public-only32+43 columns; no ID/IR')
    return source.astype(np.float64),branch.astype(np.float64)


def constants(arrays,train):
    import numpy as np
    outputs=[]
    for key,mkey in(('source_targets','source_mask'),('targets','target_mask')):
        values=[]
        for h in range(arrays[key].shape[-1]):
            known=arrays[key][train,...,h][arrays[mkey][train,...,h]>0];values.append(float(known.mean())if len(known)else 0.)
        outputs.append(np.broadcast_to(np.asarray(values,np.float32),arrays[key].shape).copy())
    return dict(zero=(np.zeros_like(arrays['source_targets']),np.zeros_like(arrays['targets'])),train_mean=tuple(outputs))


def baseline_worker(args,allowed):
    import numpy as np
    import learning_sanity_data as R
    E,_,_=modules();plan,arrays,manifest,parts=load_sealed(args.plan);train=parts['train'];hashes=immutable_hashes(arrays);evaluations={};fits={};attempts=0;solver_calls=0
    for name,(source,branch)in constants(arrays,train).items():
        evaluations[name]=evaluation(source,branch,arrays,manifest,plan);np.savez_compressed(args.out/(name+'-predictions.npz'),source=source,branch=branch)
    sx,bx=baseline_features(arrays,manifest,plan);predictions=[];raw_predictions=[]
    for design,key,mkey in((sx,'source_targets','source_mask'),(bx,'targets','target_mask')):
        output=np.zeros_like(arrays[key],np.float64);raw=np.zeros_like(output)
        for h,spec in enumerate(plan['scalers'][key]):
            attempts+=1;require(attempts<=16,'fixed sixteen head-fit ceiling')
            journal(args.progress,dict(event='numerical-fit-intent',global_fit=attempts,head=spec['name'],ridge_lambda=1.))
            prediction,native,fit=R.fit_head(design,arrays[key][...,h],arrays[mkey][...,h],spec,train);solver_calls+=int(fit['status']=='fitted-fixed-lambda');output[...,h]=prediction;raw[...,h]=native;fits[spec['name']]=fit
        predictions.append(output);raw_predictions.append(raw)
    source,branch=predictions;evaluations['public_ridge']=evaluation(source,branch,arrays,manifest,plan)
    np.savez_compressed(args.out/'public_ridge-predictions.npz',source=source,branch=branch,raw_source=raw_predictions[0],raw_branch=raw_predictions[1],source_design=sx,branch_design=bx)
    require(attempts==16 and hashes==immutable_hashes(arrays),'baseline quota/label preservation differs');E.verify_pins(plan['pins'])
    result=dict(status='completed',config=BASE_CONFIG,evaluations=evaluations,fits=fits,head_fit_attempts=attempts,actual_lstsq_solver_calls=solver_calls,unsupported_head_slots=attempts-solver_calls,original_label_hashes=hashes,semantic_validated=False,card_information='Only corrected public context32 and candidate43; no card ID, typed IR, or source printed document.',plan=pin(args.plan),fit_result=pin(args.fit_result))
    result['gates']=gate_results(read(args.fit_result),result);write_new(args.out/'result.json',result,np)
    return dict(result=pin(args.out/'result.json'),head_fit_attempts=attempts,actual_solver_calls=solver_calls,_observed=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=16,paid_jobs=0,paid_spend_usd=0.),semantic_validated=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path,default=ROOT/'campaign-spec.json');commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('metadata');p.add_argument('--native-plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p=commands.add_parser('prep')
    for name in('native-receipt','journal','native-plan','metadata','out'):p.add_argument('--'+name,type=Path,required=True)
    for name in('fit','baselines'):
        p=commands.add_parser(name);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--progress',type=Path,required=True)
        if name=='baselines':p.add_argument('--fit-result',type=Path,required=True)
    args=parser.parse_args();inputs=[]
    if args.command=='prep':inputs=[args.native_receipt,args.journal,args.native_plan,args.metadata]
    elif args.command in('fit','baselines'):
        # The sealed plan path is itself a completed-preparation proof. Its
        # transitive pins are checked only after the durable reservation.
        inputs=[args.plan]+([args.fit_result]if args.command=='baselines'else[])
    worker=dict(metadata=metadata_worker,prep=prep_worker,fit=fit_worker,baselines=baseline_worker)[args.command]
    receipt=run_stage(args,args.command,inputs,worker,getattr(args,'progress',None));print(json.dumps(receipt,indent=2,allow_nan=False))


if __name__=='__main__':main()
