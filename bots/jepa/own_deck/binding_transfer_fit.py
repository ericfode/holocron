"""Matched public-content/intended-target input ablation. Preparation only until root GO.

All four factorial cells use one padded graph and one cloned initialization per
seed. The new task predicts actual endpoints under one declared action. Its
chosen-anchor subset is not a replay of the historical conditional objective.
"""
import os
for _key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

import effect_identifiability_fit as E

HERE=Path(__file__).resolve().parent
DEFAULT=E.ROOT/'binding-transfer-v1'
MAIN=('C0R0','C1R0','C0R1','C1R1')
ARMS=(*MAIN,'ID-only','untrained-typed')
SEEDS=(17,29,43)
CONFIG=dict(seeds=list(SEEDS),arms=list(ARMS),updates_per_arm=300,batch='complete-TRAIN-in-frozen-row-order',
    optimizer_updates=5400,training_forwards=5400,evaluation_forwards=36,neural_forwards=5436,backwards=5400,
    export_forwards=0,native_applies=0,numerical_fits=0,paid_jobs=0,seconds=60.,rss_bytes=1073741824,cpu_workers=1,
    learning_rate=.003,weight_decay=.0001,clip_l2=1.,context_width=32,candidate_width=43,card_width=16,head_width=32,
    task='actual-intent-endpoints',semantic_validated=False)
MECHANICS={'damage':('target_damage_delta',),'exhaustion':('target_exhausted_delta',),'shield':('target_shield_delta',),
    'stats':('target_power_delta','target_hp_delta')}
sha=E.sha;read=E.read;pin=E.pin;write=E.write


def model_module():return importlib.import_module('public_input_binding_model_v1')
def accounting():return importlib.import_module('binding_transfer_accounting')
def success_counter_proof(status,progress):return pin(progress)if status=='completed'else None


def stage_metadata(current,rows,plan_path,out,progress,entrypoint):
    """Use already-frozen expected pins without opening actual-stage inputs."""
    allowed={p['path']:p for p in current['config']['pins']}
    for row in rows:
        if row['event']=='stage-finish'and row['data']['status']=='completed':
            for expected in row['data']['proofs']:allowed[expected['path']]=expected
    expected=allowed.get(str(plan_path.resolve()));stage_receipt=out.parent/(out.name+'-stage-receipt.json')
    metadata=dict(argv=[str(Path(sys.executable).resolve()),str(Path(entrypoint).resolve()),*sys.argv[1:]],
        outputs=[str(out.resolve()),str(progress.resolve()),str(stage_receipt.resolve())],input_pins=[expected]if expected else[],
        guard=dict(cpu_workers=1,rss_bytes=CONFIG['rss_bytes']))
    return metadata,expected,stage_receipt


def save_stage_receipt(path,out,value,copy_into_out=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    if copy_into_out and out.is_dir()and not(out/'receipt.json').exists():write(out/'receipt.json',value)
    return pin(path)


def arm_contract(arm):
    if arm in MAIN:return arm,'rich-typed'
    if arm=='ID-only':return 'C1R1','rich-id-only'
    if arm=='untrained-typed':return 'C1R1','rich-untrained-typed'
    raise ValueError('unreviewed ablation arm')


def expected_exposure():
    updates=len(SEEDS)*len(ARMS)*CONFIG['updates_per_arm'];evaluations=2*len(SEEDS)*len(ARMS)
    return dict(optimizer_updates=updates,training_forwards=updates,evaluation_forwards=evaluations,
        neural_forwards=updates+evaluations,backwards=updates,export_forwards=0,native_applies=0,numerical_fits=0,paid_jobs=0)


def cells(arrays,split):
    import numpy as np
    if 'root_partitions'not in split:raise ValueError('explicit frozen per-root partitions required; no Cartesian split inference')
    result={key:np.asarray(split['root_partitions'][key],np.int64)for key in('train','family_held','state_held','joint')}
    indices=[int(i)for values in result.values()for i in values]
    if sorted(indices)!=list(range(len(arrays['source_cards'])))or len(set(indices))!=len(indices):raise ValueError('root partitions must cover each root exactly once')
    return result


def validate_data(arrays,manifest,plan):
    import numpy as np
    n=len(arrays['source_cards']);k=len(manifest['candidate_order'])
    if n!=26 or k!=8:raise ValueError('frozen26roots/eightcandidate ABI required')
    for key,shape in dict(context_features=(n,18),candidate_features=(n,k,34),source_targets=(n,9),source_mask=(n,9),targets=(n,k,7),target_mask=(n,k,7),selected_candidate_indices=(n,),state_families=(n,)).items():
        if arrays[key].shape!=shape:raise ValueError('array shape differs: '+key)
        if arrays[key].dtype.kind in'fi'and not np.isfinite(arrays[key]).all():raise ValueError('nonfinite array: '+key)
    if arrays['selected_candidate_indices'].dtype!=np.int64 or np.any(arrays['selected_candidate_indices']<0)or np.any(arrays['selected_candidate_indices']>=k):raise ValueError('explicit pre-action intended indices required')
    for key in('source_mask','target_mask'):
        if not np.isin(arrays[key],[0,1]).all():raise ValueError('binary observed masks required')
    for ykey,mkey,names,binary in(('source_targets','source_mask',manifest['source_head_names'],manifest['source_binary_heads']),('targets','target_mask',manifest['target_names'],manifest['binary_heads'])):
        for name in binary:
            h=names.index(name)
            if not np.isin(arrays[ykey][...,h][arrays[mkey][...,h]>0],[0,1]).all():raise ValueError('known binary labels must be0or1: '+name)
    if set(arrays['source_cards'].astype(str))!=set(plan['codes'])or len(plan['codes'])!=7:raise ValueError('exact frozen seven-card cohort required')
    if manifest.get('errors',0)or manifest.get('pending',0)or manifest.get('fit_blockers'):raise ValueError('native errors/pending/fit blockers stop fitting')
    if manifest.get('public_binding_contract',{}).get('task')!=CONFIG['task']:raise ValueError('this fit only predicts actual declared-action endpoints')
    if len(manifest.get('family_ids',[]))!=n or len(manifest.get('template_ids',[]))!=n:raise ValueError('frozen per-root family/template metadata required')
    result=cells(arrays,plan['split'])
    if not len(result['train']):raise ValueError('nonempty frozen TRAIN required')
    codes=arrays['source_cards'].astype(str);train_codes=set(plan['train_codes'])
    if len(train_codes)!=5 or set(codes[result['train']])!=train_codes:raise ValueError('all five frozen training identities require TRAIN roots')
    if any(codes[i]not in train_codes for cell in('train','state_held')for i in result[cell])or any(codes[i]in train_codes for cell in('family_held','joint')for i in result[cell]):raise ValueError('per-root program partition disagrees with frozen card split')
    if [len(result[k])for k in('train','state_held','family_held','joint')]!=[12,6,4,4]:raise ValueError('exact final12/6/4/4 partitions required')
    return result


def projected_arrays(arrays,manifest,scalers=None,arm='C1R1'):
    M=model_module();input_arm,_=arm_contract(arm)
    x,c=M.project_arrays(arrays,manifest,input_arm,scalers=scalers)
    return x,c


def common_scalers(arrays,manifest,train):
    x,c=projected_arrays(arrays,manifest);expanded=dict(arrays,context_features=x,candidate_features=c)
    result=E.common_scalers(expanded,manifest,train)
    result['control_information']='All arms share C1R1 TRAIN-only transforms, sign weights and fixed head coefficients. C/R channels are zeroed AFTER normalization. No held-label/statistic fitting.'
    return result


def consumed_conflicts(arrays,manifest,plan,arm):
    import numpy as np
    M=model_module();x,c=projected_arrays(arrays,manifest,plan['scalers'],arm)
    _,representation=arm_contract(arm)
    signatures=plan['semantic_tensor_sha256']
    visible=[]
    for code in arrays['source_cards'].astype(str):
        visible.append('ID:'+str(plan['train_codes'].index(code)+1 if code in plan['train_codes']else 0)if representation=='rich-id-only'else signatures[plan['codes'].index(code)])
    # Hash exactly the source-intended or branch-own candidate input consumed;
    # masks, split names, catalog IDs and unconsumed sibling inputs never enter.
    signatures=M.consumed_input_hashes(x,c,visible,arrays['selected_candidate_indices'])
    seen={};conflicts=[]
    for kind,targets,masks,names in(('source',arrays['source_targets'],arrays['source_mask'],manifest['source_head_names']),('candidate',arrays['targets'],arrays['target_mask'],manifest['target_names'])):
        for i in range(len(targets)):
            values=targets[i:i+1]if kind=='source'else targets[i];known=masks[i:i+1]if kind=='source'else masks[i]
            for j in range(len(values)):
                signature=signatures[i]['source']if kind=='source'else signatures[i]['candidate'][j]
                for h,name in enumerate(names):
                    if not known[j,h]:continue
                    key=(kind,signature,name);value=float(values[j,h])
                    if key in seen and seen[key][0]!=value:conflicts.append(dict(kind=kind,head=name,root=i,candidate=j,old_root=seen[key][1],old_value=seen[key][0],value=value))
                    else:seen[key]=(value,i)
    return dict(conflict_count=len(conflicts),conflicts=conflicts,consumed_signatures=signatures)


def observed_support(arrays,manifest,train,plan):
    import numpy as np
    report={}
    templates=manifest['template_ids']
    for mechanic,names in MECHANICS.items():
        heads={}
        for name in names:
            h=manifest['target_names'].index(name);m=arrays['target_mask'][train,:,h]>0;y=arrays['targets'][train,:,h]
            by_template={}
            for t in sorted({str(templates[i])for i in train}):
                indices=[i for i in train if str(templates[i])==t];v=arrays['targets'][indices,:,h][arrays['target_mask'][indices,:,h]>0]
                by_template[t]=dict(zero=int((v==0).sum()),nonzero=int((v!=0).sum()),negative=int((v<0).sum()),positive=int((v>0).sum()))
            v=y[m];supported=[t for t,s in by_template.items()if s['zero']and s['positive']]
            heads[name]=dict(zero=int((v==0).sum()),nonzero=int((v!=0).sum()),by_template=by_template,independent_supported_templates=supported,
                eligible=bool((v==0).sum()>=2 and(v!=0).sum()>=2 and len(supported)>=2))
        report[mechanic]=dict(heads=heads,eligible=all(s['eligible']for s in heads.values()))
    required=plan['primary_mechanics']
    return dict(mechanics=report,required=required,passed=all(report[k]['eligible']for k in required))


def quantity_admission(arrays,manifest,plan):
    import numpy as np
    parts=cells(arrays,plan['split']);held=np.concatenate((parts['family_held'],parts['joint']));report={}
    for name,train_expected,held_expected in(('target_power_delta',[1.,2.],[2.]),('target_hp_delta',[1.,3.],[2.,3.])):
        h=manifest['target_names'].index(name);sets=[]
        for indices in(parts['train'],held):
            known=arrays['targets'][indices,:,h][arrays['target_mask'][indices,:,h]>0];sets.append(sorted(set(float(v)for v in known if v>0)))
        report[name]=dict(train_positive_values=sets[0],held_positive_values=sets[1],expected_train=train_expected,expected_held=held_expected,
            passed=sets[0]==train_expected and sets[1]==held_expected)
    return dict(heads=report,passed=all(r['passed']for r in report.values()),scope='Frozen public-program quantity-support check, not a held prediction/performance criterion; failure stops this cohort.')


def chosen_only_mask(arrays,manifest):
    import numpy as np
    mask=np.zeros_like(arrays['target_mask']);q=arrays['selected_candidate_indices']
    for i,record in enumerate(manifest['public_before_records']):
        if record['declared_intent'].get('requires_target')is True:mask[i,q[i]]=arrays['target_mask'][i,q[i]]
    if 'chosen_only_target_mask'in arrays and not np.array_equal(mask,arrays['chosen_only_target_mask']):raise ValueError('converter chosen-only mask differs from actual explicit intent')
    return mask


def evaluate(source,branch,arrays,manifest,plan):
    import numpy as np
    result={}
    for cell,indices in cells(arrays,plan['split']).items():
        panels={}
        for panel in('actual_endpoints','chosen_only_subset'):
            selected=dict(arrays)
            if panel=='chosen_only_subset':
                selected['target_mask']=chosen_only_mask(arrays,manifest)
            heads=E.head_metrics(source,branch,selected,manifest,plan['scalers'],indices)
            for prediction,ykey,mkey,skey in((source,'source_targets','source_mask','source_targets'),(branch,'targets','target_mask','targets')):
                for h,spec in enumerate(plan['scalers'][skey]):
                    y=selected[ykey][indices,...,h];p=prediction[indices,...,h];m=selected[mkey][indices,...,h]>0
                    labels=np.where(y>.25,1,np.where(y<-.25,-1,0));predicted=np.where(p>.25,1,np.where(p<-.25,-1,0));v=(p-y)[m]
                    heads[spec['name']].update(rmse=float(np.sqrt(np.mean(v*v)))if len(v)else None,max_abs_error=float(np.max(abs(v)))if len(v)else None,
                        zero_sign_accuracy=float((labels[m]==predicted[m]).mean())if len(v)and not spec['binary']else None)
            families={}
            for family in sorted({str(manifest['family_ids'][i])for i in indices}):
                rows=[i for i in indices if str(manifest['family_ids'][i])==family]
                fm=E.head_metrics(source,branch,selected,manifest,plan['scalers'],rows);mechanics={}
                for mechanic in plan['primary_mechanics']:
                    errors=[fm[name]['train_scaled_mae']for name in MECHANICS[mechanic]if fm[name]['train_scaled_mae']is not None]
                    mechanics[mechanic]=float(np.mean(errors))if errors else None
                known=[v for v in mechanics.values()if v is not None];families[family]=dict(roots=rows,mechanics=mechanics,mae=float(np.mean(known))if known else None)
            known=[f['mae']for f in families.values()if f['mae']is not None]
            by_card={code:E.head_metrics(source,branch,selected,manifest,plan['scalers'],[i for i in indices if str(arrays['source_cards'][i])==code])for code in sorted({str(arrays['source_cards'][i])for i in indices})}
            panels[panel]=dict(heads=heads,families=families,per_card=by_card,family_first_mae=float(np.mean(known))if known else None,
                source_scope='Common source-lifecycle heads; source-reference index on passive roots is not a chosen target.')
        result[cell]=panels
    return result


def narrow_estimands(source,branch,arrays,manifest,plan):
    """Fixed small task-specific readouts; no universal semantic success flag."""
    import numpy as np
    partitions=cells(arrays,plan['split']);codes=arrays['source_cards'].astype(str);q=arrays['selected_candidate_indices']
    c_rows=[i for i in partitions['state_held']if codes[i]=='LAW_045'];r_rows=[i for cell in('family_held','joint')for i in partitions[cell]if codes[i]in('LOF_053','LOF_261')]
    damage=manifest['target_names'].index('target_damage_delta');c=[]
    for i in c_rows:
        if arrays['target_mask'][i,q[i],damage]:c.append(dict(root=int(i),truth=float(arrays['targets'][i,q[i],damage]),prediction=float(branch[i,q[i],damage]),absolute_error=float(abs(branch[i,q[i],damage]-arrays['targets'][i,q[i],damage]))))
    r={}
    for code in('LOF_053','LOF_261'):
        rows=[];pairs=[]
        for i in r_rows:
            if codes[i]!=code:continue
            for name in('target_power_delta','target_hp_delta'):
                h=manifest['target_names'].index(name);known=np.flatnonzero(arrays['target_mask'][i,:,h]>0)
                for j in known:rows.append(dict(root=int(i),candidate=int(j),head=name,intended=bool(j==q[i]),truth=float(arrays['targets'][i,j,h]),prediction=float(branch[i,j,h]),absolute_error=float(abs(branch[i,j,h]-arrays['targets'][i,j,h]))))
                for j in known:
                    if j==q[i]or not arrays['target_mask'][i,q[i],h]:continue
                    truth=float(arrays['targets'][i,q[i],h]-arrays['targets'][i,j,h]);prediction=float(branch[i,q[i],h]-branch[i,j,h])
                    sign=lambda v:1 if v>.25 else -1 if v<-.25 else 0
                    pairs.append(dict(root=int(i),head=name,intended=int(q[i]),other=int(j),native_contrast=truth,predicted_contrast=prediction,absolute_error=abs(prediction-truth),direction_correct=sign(prediction)==sign(truth)))
        r[code]=dict(observations=rows,mae=float(np.mean([v['absolute_error']for v in rows]))if rows else None,pairs=pairs,
            contrast_mae=float(np.mean([p['absolute_error']for p in pairs]))if pairs else None,direction_accuracy=float(np.mean([p['direction_correct']for p in pairs]))if pairs else None,
            support_scope='Power/HP are correlated heads; repeated roots and two card variants are one broad parent-stat family.')
    return dict(C_LAW045_new_states_chosen_damage=dict(observations=c,mae=float(np.mean([v['absolute_error']for v in c]))if c else None),R_fresh_positive_parent_stat_variants_actual_endpoints=r,
        generic_semantic_gate='UNSUPPORTED: two held variants of one broad parent-stat family; no fresh aspect-numeric program or independent multi-family qualification.',semantic_validated=False)


def factorial_contrasts(results):
    output={}
    for seed in SEEDS:
        metrics={arm:results[f's{seed}:{arm}']['evaluations']['300']['narrow_estimands']for arm in MAIN}
        panels={'C_LAW045_new_states_chosen_damage':{a:m['C_LAW045_new_states_chosen_damage']['mae']for a,m in metrics.items()}}
        for code in('LOF_053','LOF_261'):
            for measure in('mae','contrast_mae','direction_accuracy'):
                panels[f'R_{code}_{measure}']={a:m['R_fresh_positive_parent_stat_variants_actual_endpoints'][code][measure]for a,m in metrics.items()}
        output[str(seed)]={}
        for name,v in panels.items():
            derived=None
            if all(v[a]is not None for a in MAIN):derived=dict(C_at_R0=v['C0R0']-v['C1R0'],C_at_R1=v['C0R1']-v['C1R1'],R_at_C0=v['C0R0']-v['C0R1'],R_at_C1=v['C1R0']-v['C1R1'],interaction=v['C1R0']+v['C0R1']-v['C0R0']-v['C1R1'])
            output[str(seed)][name]=dict(cells=v,differences=derived,formula='C/R differences are 0-minus-1; interaction=e10+e01-e00-e11. Positive means error reduction for MAE, but direction accuracy uses the opposite desirability. No pooled semantic gate.')
    return output


def prepare(native_plan,output,primary_mechanics=('damage','stats')):
    if output.exists():raise FileExistsError('new versioned preparation required')
    M=model_module();native=read(native_plan);codes=[r['code']for r in native['cards']];train=native['split']['train_codes']
    if len(codes)!=7 or len(train)!=5:raise ValueError('seven-source/fiveTRAIN frozen cohort required')
    documents=[E.canonical_document(r['raw_card'])[0]for r in native['cards']];symbols=E.symbols_for(documents)
    bank,numeric_scale=E.make_bank(documents,codes,train,symbols,False)
    paths=[Path(__file__),HERE/'test_binding_transfer_fit.py',HERE/'BINDING_TRANSFER_LEARNER_PROTOCOL.md',HERE/'BINDING_TRANSFER_PREREGISTRATION.md',HERE/'public_input_binding_model_v1.py',HERE/'test_public_input_binding_model_v1.py',HERE/'binding_transfer_accounting.py',HERE/'binding_transfer_baselines.py',HERE/'test_binding_transfer_baselines.py',HERE/'learning_sanity_data.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',native_plan]
    paths.extend(Path(p['path'])for p in native.get('source_pins',[]))
    plan=dict(schema='jepa-binding-transfer-fit/1',status='prepared-no-neural-execution',source_sha256=sha(__file__),config=CONFIG,
        native_plan=str(native_plan.resolve()),codes=codes,train_codes=train,split=native['split'],documents=documents,vocabularies=symbols,
        semantic_tensor_sha256=E.tensor_signatures(bank),numeric_scale=numeric_scale,parameters=M.parameter_counts(symbols,len(train)),
        primary_mechanics=list(primary_mechanics),pins=[pin(p)for p in sorted(set(p.resolve()for p in paths))],semantic_validated=False)
    output.parent.mkdir(parents=True,exist_ok=True);write(output,plan);return plan


def seal(prepared,dataset,manifest_path,output):
    import numpy as np
    if output.exists():raise FileExistsError('new immutable sealed plan required')
    plan=read(prepared);E.verify_pins(plan['pins'])
    if plan['source_sha256']!=sha(__file__)or plan['config']!=CONFIG:raise ValueError('prepared source/config changed')
    with np.load(dataset,allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
    manifest=read(manifest_path);parts=validate_data(arrays,manifest,plan);plan['scalers']=common_scalers(arrays,manifest,parts['train'])
    plan['support']=observed_support(arrays,manifest,parts['train'],plan)
    if not plan['support']['passed']:raise ValueError('planned mechanics lack two independent zero/nonzero TRAIN templates')
    plan['quantity_support']=quantity_admission(arrays,manifest,plan)
    if not plan['quantity_support']['passed']:raise ValueError('predeclared positive TRAIN/held stat quantity support differs')
    plan['input_audits']={arm:consumed_conflicts(arrays,manifest,plan,arm)for arm in ARMS}
    if plan['input_audits']['C1R1']['conflict_count']:raise ValueError('repaired actual consumed inputs retain co-known label conflicts')
    plan.update(status='sealed-awaiting-root-GO',prepared=pin(prepared),dataset=str(dataset.resolve()),manifest=str(manifest_path.resolve()))
    plan['pins'] += [pin(dataset),pin(manifest_path)]
    write(output,plan);return plan


def execute(plan_path,out,progress):
    A=accounting()
    with A.lease()as(stream,rows,current):
        metadata,expected_plan,stage_receipt=stage_metadata(current,rows,plan_path,out,progress,__file__)
        start=time.monotonic();guard=E.Guard(60.)
        counts=dict(optimizer_updates=0,training_forwards=0,evaluation_forwards=0,export_forwards=0,backwards=0);status='failed';error=None;created_out=False
        def forward(kind,arm,seed,step):
            key='training_forwards'if kind=='train'else'evaluation_forwards';counts[key]+=1
            if counts[key]>CONFIG[key]:raise ValueError('fixed forward ceiling exceeded')
            E.append_journal(progress,dict(event='forward-intent',kind=kind,arm=arm,seed=seed,step=step,global_forward=counts['training_forwards']+counts['evaluation_forwards']))
        try:
            A.start(stream,rows,'fit',metadata)
            if expected_plan is None:raise ValueError('sealed plan is not a frozen or completed-preparation proof')
            plan=read(plan_path);E.verify_pins(plan['pins'])
            if plan['status']!='sealed-awaiting-root-GO'or plan['source_sha256']!=sha(__file__)or plan['config']!=CONFIG:raise ValueError('sealed exact source/config required')
            if out.exists()or progress.exists()or stage_receipt.exists():raise FileExistsError('all prior attempt paths retained; no retry/reset')
            out.mkdir(parents=True);created_out=True;M=model_module();remaining=60.-(time.monotonic()-start)
            if remaining<=0:raise RuntimeError('fit startup exhausted its stage reservation')
            guard=E.Guard(remaining)
            with guard:
                import numpy as np
                import torch
                torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
                with np.load(plan['dataset'],allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
                manifest=read(plan['manifest']);parts=validate_data(arrays,manifest,plan);batch=parts['train']
                true_hashes={k:sha_array(arrays[k])for k in('targets','target_mask','source_targets','source_mask','selected_candidate_indices')}
                full,_=E.make_bank(plan['documents'],plan['codes'],plan['train_codes'],plan['vocabularies'],False);restricted,_=E.make_bank(plan['documents'],plan['codes'],plan['train_codes'],plan['vocabularies'],True)
                np.savez_compressed(out/'program-inputs.npz',**{'full_'+k:v for k,v in full.items()},**{'restricted_'+k:v for k,v in restricted.items()})
                full={k:torch.as_tensor(v)for k,v in full.items()};restricted={k:torch.as_tensor(v)for k,v in restricted.items()}
                q=torch.as_tensor([plan['codes'].index(str(c))for c in arrays['source_cards']]);selected=torch.as_tensor(arrays['selected_candidate_indices'])
                labels={k:torch.as_tensor(arrays[k][batch].copy())for k in('source_targets','source_mask','targets','target_mask')};results={}
                inputs={}
                for arm in ARMS:
                    ix,ic=projected_arrays(arrays,manifest,plan['scalers'],arm);inputs['x_'+arm]=ix;inputs['c_'+arm]=ic
                np.savez_compressed(out/'consumed-inputs.npz',**inputs)
                np.savez_compressed(out/'training-schedule.npz',train_indices=batch,seeds=np.asarray(SEEDS,np.int64),arms=np.asarray(ARMS),selected_candidate_indices=arrays['selected_candidate_indices'],source_cards=arrays['source_cards'])
                for seed in SEEDS:
                    torch.manual_seed(seed);template=M.make_model(torch,plan['vocabularies'],len(plan['codes']),len(plan['train_codes']));initial={n:v.detach().clone()for n,v in template.state_dict().items()}
                    master_initial_hash=named_state_sha256({n:v.numpy()for n,v in initial.items()})
                    np.savez_compressed(out/f's{seed}-initial-checkpoint.npz',**{n:v.numpy()for n,v in initial.items()});del template
                    for arm in ARMS:
                        input_arm,representation=arm_contract(arm);x,c=map(torch.as_tensor,projected_arrays(arrays,manifest,plan['scalers'],arm))
                        model=M.make_model(torch,plan['vocabularies'],len(plan['codes']),len(plan['train_codes']));model.load_state_dict(initial,strict=True)
                        loaded_initial_hash=named_state_sha256({n:v.detach().numpy()for n,v in model.state_dict().items()})
                        if loaded_initial_hash!=master_initial_hash:raise ValueError('arm initialization differs from the saved per-seed master')
                        M.configure_arm(model,representation)
                        optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=.003,weight_decay=.0001);evaluations={};gradients={}
                        for step in range(301):
                            if step in(0,300):
                                model.eval();forward('evaluate',arm,seed,step)
                                with torch.inference_mode():sp,bp,vectors=model(x,c,q,full,representation,selected);source,branch=E.prior().decode(torch,sp,bp,plan['scalers'])
                                if not np.isfinite(source).all()or not np.isfinite(branch).all():raise ValueError('nonfinite predictions')
                                evaluations[str(step)]=dict(cells=evaluate(source,branch,arrays,manifest,plan),narrow_estimands=narrow_estimands(source,branch,arrays,manifest,plan))
                                np.savez_compressed(out/f's{seed}-{arm}-step{step}-predictions.npz',source=source,branch=branch,card_vectors=vectors.detach().numpy(),source_cards=arrays['source_cards'],state_families=arrays['state_families'],selected_candidate_indices=arrays['selected_candidate_indices'])
                            if step==300:break
                            model.train();optimizer.zero_grad(set_to_none=True);forward('train',arm,seed,step+1)
                            sp,bp,_=model(x[batch],c[batch],q[batch],restricted,representation,selected[batch]);objective=E.fixed_loss(torch,sp,bp,labels,plan['scalers'])
                            if not bool(torch.isfinite(objective)):raise ValueError('nonfinite fixed objective')
                            objective.backward();counts['backwards']+=1
                            if step==299:gradients={n:dict(rms=float(p.grad.square().mean().sqrt()),nonzero=int(torch.count_nonzero(p.grad)),elements=p.numel())for n,p in model.named_parameters()if p.grad is not None}
                            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                            if not bool(torch.isfinite(norm)):raise ValueError('nonfinite gradient')
                            E.append_journal(progress,dict(event='optimizer-intent',global_update=counts['optimizer_updates']+1,arm=arm,seed=seed,arm_update=step+1))
                            optimizer.step();counts['optimizer_updates']+=1;E.append_journal(progress,dict(event='optimizer-update',global_update=counts['optimizer_updates'],arm=arm,seed=seed,arm_update=step+1,loss=float(objective.detach()),preclip_gradient_norm=float(norm)))
                        weights={n:v.detach().numpy().copy()for n,v in model.state_dict().items()};checkpoint=out/f's{seed}-{arm}-checkpoint.npz';np.savez_compressed(checkpoint,**weights)
                        movement={n:dict(delta_l2=float(np.linalg.norm((v-initial[n].numpy()).astype(np.float64))),changed=int(np.count_nonzero(v!=initial[n].numpy())),elements=v.size)for n,v in weights.items()}
                        results[f's{seed}:{arm}']=dict(evaluations=evaluations,checkpoint=pin(checkpoint),initial_state_sha256=loaded_initial_hash,master_initial_state_sha256=master_initial_hash,last_step_preclip_gradients=gradients,weight_movement=movement)
                durable=E.journal_counts(progress)
                if any(counts[k]!=CONFIG[k]for k in counts)or any(durable[k]!=CONFIG[k]for k in durable):raise ValueError('exact5400/5436 durable exposure differs')
                if true_hashes!={k:sha_array(arrays[k])for k in true_hashes}:raise ValueError('TRUE labels/masks/intent changed')
                E.verify_pins(plan['pins']);write(out/'contract.json',dict(plan=pin(plan_path),source=pin(__file__),config=CONFIG,scalers=plan['scalers'],parameters=plan['parameters'],vocabularies=plan['vocabularies']))
                write(out/'result.json',dict(status='completed',config=CONFIG,counts=counts,results=results,factorial_contrasts=factorial_contrasts(results),all_inputs_unchanged=True,true_label_hashes=true_hashes,
                    semantic_validated=False,task=CONFIG['task'],chosen_subset_scope='Same actual applied actions restricted to chosen anchors; not historical conditional-objective replication.',
                    prior_baselines_scope='Fresh matched C0R0/ID/untrained rerun. Prior wrong/shuffle/checkpoint results remain historical descriptive evidence; no extra old-checkpoint forwards.'))
            status='completed'
        except BaseException as exc:
            pending=A.state(rows)['pending']
            if pending is None or pending['stage']!='fit'or pending['owner_pid']!=os.getpid():raise
            error=dict(type=type(exc).__name__,message=str(exc))
        elapsed=time.monotonic()-start
        if elapsed>60:status='failed';error=error or dict(type='BudgetExceeded',message='owned fit exceeded60seconds')
        observed=dict(native_applies=0,neural_forwards=counts['training_forwards']+counts['evaluation_forwards']if status=='completed'else None,optimizer_updates=counts['optimizer_updates']if status=='completed'else None,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
        try:durable_prefix=E.journal_counts(progress)if created_out and progress.exists()else None
        except BaseException as exc:durable_prefix=None;status='failed';error=dict(type=type(exc).__name__,message=str(exc),journal_unverified=True);observed.update(neural_forwards=None,optimizer_updates=None)
        artifact_pins=[pin(p)for p in sorted(out.rglob('*'))if p.is_file()]if created_out else[]
        receipt=dict(status=status,error=error,active_seconds=elapsed,observed=observed,durable_prefix=durable_prefix,artifact_pins=artifact_pins,guard=guard.receipt(),source=pin(__file__),plan=expected_plan,semantic_validated=False)
        try:
            A.verify_output_protection([str(stage_receipt.resolve())]);receipt_pin=save_stage_receipt(stage_receipt,out,receipt,copy_into_out=created_out)
        except BaseException as exc:
            receipt_pin=None;status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True);observed.update(neural_forwards=None,optimizer_updates=None)
        proofs=([receipt_pin]if receipt_pin else[])+([pin(progress)]if created_out and progress.exists()else[])+([pin(p)for p in sorted(out.rglob('*'))if p.is_file()]if created_out else[])
        finished=A.finish(stream,rows,status,elapsed,observed=observed,proofs=proofs,cleanup_verified=True,execution_ended=True,counter_proof=success_counter_proof(status,progress))
        if status!='completed'or 'fit'not in finished['completed_stages']:raise RuntimeError('failed bounded fit retained; authoritative ledger controls status: '+str(error))
        return receipt


def sha_array(value):return hashlib.sha256(str(value.dtype).encode()+str(value.shape).encode()+value.tobytes()).hexdigest()


def named_state_sha256(state):return E.digest({name:sha_array(state[name])for name in sorted(state)})


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--native-plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('seal');a.add_argument('--prepared',type=Path,required=True);a.add_argument('--dataset',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('execute');a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--progress',type=Path,required=True)
    a=sub.add_parser('preflight');a.add_argument('--plan',type=Path,required=True)
    args=p.parse_args()
    if args.command=='prepare':result=prepare(args.native_plan,args.out)
    elif args.command=='seal':result=seal(args.prepared,args.dataset,args.manifest,args.out)
    elif args.command=='execute':result=execute(args.plan,args.out,args.progress)
    else:
        plan=read(args.plan);E.verify_pins(plan['pins']);result=dict(status='pure-preflight',source=pin(__file__),plan=pin(args.plan),config=CONFIG,expected_exposure=expected_exposure(),no_execution=True)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
