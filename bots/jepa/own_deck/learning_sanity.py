"""Fixed-capacity training sanity; preparation is pure, execution requires root GO."""
import os
for _k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_k]='1'
import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import effect_identifiability_fit as E
ROOT=E.ROOT
DEFAULT=ROOT/'learning-sanity-v1'
PRIOR=ROOT/'effect-identifiability-v2'
PARENT_LAST='a4ebccf072b203af8242004155be55dd0f8b34ba4ec68532aa12d172986a1cf0'
PARENT_LEDGER_SHA='e69410d8caa5c5219f46107a6238e4c811125c65cead3db15d970b9a25133259'
E_SHA='90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
INITIAL_SHA='b2f0f1a486c91a0f1d23ac26c2d47e27c08d855859a1207f9ab2642dcd096981'
ARMS=('correct','fixed-shuffle','fresh-shuffle')
CONFIG=dict(seed=17,arms=list(ARMS),updates_per_arm=300,batch='all21TRAINinoriginalorder',optimizer_updates=900,training_forwards=900,backwards=900,evaluation_forwards=6,export_forwards=0,native_applies=0,paid_jobs=0,seconds=30.,rss_bytes=1073741824,threads=1,learning_rate=.003,weight_decay=.0001,clip_l2=1.,fixed_shuffle_seed=1017,fresh_shuffle_seed=2017,normalized_mae_max=.05,relative_initial_error_max=.05,native_sign_accuracy_min=.95,native_zero_deadband=.25)
sha=E.sha;read=E.read;write=E.write;pin=E.pin;digest=E.digest

def effect_packets(arrays,plan):
    import numpy as np
    roots=np.asarray(plan['shuffle_roots'],np.int64);cols=plan['effect_columns'];selected=arrays['selected_candidate_indices']
    if len(roots)!=14 or len(set(roots.tolist()))!=14 or not set(roots.tolist())<=set(plan['train_indices'])or any(not arrays['target_mask'][r,selected[r],cols].all()for r in roots):raise ValueError('exact14jointly-known TRAIN anchors required')
    if any({r for r in plan['train_indices']if arrays['target_mask'][r,:,h].any()}!=set(roots.tolist())for h in cols):raise ValueError('all five observed TRAIN sets must equal exact14; no partial-known roots dropped')
    return roots,np.asarray([arrays['targets'][r,selected[r],cols]for r in roots],np.float32)

def shuffle_labels(arrays,plan,mapping):
    import numpy as np
    roots,packets=effect_packets(arrays,plan);mapping=np.asarray(mapping)
    if mapping.dtype!=np.int64 or mapping.shape!=(14,)or sorted(mapping.tolist())!=list(range(14))or np.any(mapping==np.arange(14)):raise ValueError('fixed-length packet derangement required')
    result=dict(arrays);result['targets']=arrays['targets'].copy()
    for dst,src in zip(roots,mapping):result['targets'][dst,arrays['selected_candidate_indices'][dst],plan['effect_columns']]=packets[src]
    return result

def derangements():
    import numpy as np
    def draw(rng):
        while True:
            candidate=rng.permutation(14).astype(np.int64)
            if np.all(candidate!=np.arange(14)):return candidate
    fixed=draw(np.random.default_rng(CONFIG['fixed_shuffle_seed']));rng=np.random.default_rng(CONFIG['fresh_shuffle_seed'])
    return fixed,np.asarray([draw(rng)for _ in range(300)],np.int64)

def shuffle_change_report(packets,mapping):
    import numpy as np
    changed=packets[np.asarray(mapping)]!=packets
    return dict(root_index_derangement=True,changed_vectors=int(changed.any(-1).sum()),vector_fraction=float(changed.any(-1).mean()),changed_coordinates=int(changed.sum()),coordinate_fraction=float(changed.mean()),per_head_changed_fraction=changed.mean(0).tolist(),joint_multiset_preserved=True)

def sanity_metrics(branch,arrays,plan):
    import numpy as np
    roots,truth=effect_packets(arrays,plan);cols=plan['effect_columns'];prediction=np.asarray([branch[r,arrays['selected_candidate_indices'][r],cols]for r in roots]);result={}
    for j,h in enumerate(cols):
        spec=plan['scalers']['targets'][h];y=truth[:,j];p=prediction[:,j];zero=y==0;sign=np.where(p>CONFIG['native_zero_deadband'],1,np.where(p< -CONFIG['native_zero_deadband'],-1,0));correct=sign==np.sign(y)
        result[spec['name']]=dict(known_roots=14,mae=float(abs(p-y).mean()),normalized_mae=float(abs(p-y).mean()/spec['scale']),max_absolute_error=float(abs(p-y).max()),zero_sign_accuracy=float(correct.mean()),zero_accuracy=float(correct[zero].mean())if zero.any()else None,nonzero_sign_accuracy=float(correct[~zero].mean())if (~zero).any()else None,positive=int((y>0).sum()),negative=int((y<0).sum()),zero=int(zero.sum()),signed_residual=float((p-y).mean()))
    return result

def overfit_gate(initial,final):
    details={}
    for name,after in final.items():
        before=initial[name]['normalized_mae'];absolute=after['normalized_mae']<=.05;relative=before==0 or after['normalized_mae']<=.05*before;sign=after['zero_sign_accuracy']>=.95
        details[name]=dict(passed=absolute and relative and sign,initial_normalized_mae=before,final_normalized_mae=after['normalized_mae'],final_initial_ratio=None if before==0 else after['normalized_mae']/before,absolute_pass=absolute,relative_pass=relative,sign_pass=sign,zero_sign_accuracy=after['zero_sign_accuracy'])
    return dict(passed=all(v['passed']for v in details.values()),per_head=details,interpretation='TRAIN memorization sanity only. Correct/fixed can both overfit; fresh labels are inconsistent by design. Failure within fixed300updates does not isolate capacity; no extension or held tuning.')

def validate_parent():
    if sha(HERE/'effect_identifiability_fit.py')!=E_SHA or sha(PRIOR/'campaign-ledger.jsonl')!=PARENT_LEDGER_SHA or sha(PRIOR/'fit-1/initial-checkpoint.npz')!=INITIAL_SHA:raise ValueError('immutable prior science/initialization/closed ledger differs')
    rows=[json.loads(line)for line in(PRIOR/'campaign-ledger.jsonl').read_text().splitlines()]
    if rows[-1]['record_sha256']!=PARENT_LAST or rows[-1]['event']!='attempt-finish':raise ValueError('prior final accounting reference differs')

def prepare(path):
    import numpy as np
    if path.exists():raise FileExistsError('preserve prepared sanity plan')
    validate_parent();prior=read(PRIOR/'learner-plan.json');E.verify_pins(prior['pins'])
    with np.load(prior['dataset'],allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
    manifest=E.joined_manifest(read(prior['manifest']),prior);cells=E.validate_data(arrays,manifest,prior);train=cells['train'].tolist();cols=[manifest['target_names'].index(n)for n in E.TARGET_EFFECTS]
    roots=[int(i)for i in train if arrays['target_mask'][i,int(arrays['selected_candidate_indices'][i]),cols].all()]
    fixed,fresh=derangements();plan=dict(schema='learning-sanity/1',status='prepared-no-neural-execution',source_sha256=sha(__file__),base_commit='1fff058ee0373d5ac015e4271b551a392794a05e',config=CONFIG,prior_plan=str((PRIOR/'learner-plan.json').resolve()),initial_checkpoint=str((PRIOR/'fit-1/initial-checkpoint.npz').resolve()),dataset=prior['dataset'],manifest=prior['manifest'],codes=prior['codes'],train_codes=prior['train_codes'],split=prior['split'],documents=prior['documents'],vocabularies=prior['vocabularies'],scalers=prior['scalers'],parameters=prior['parameters'],train_indices=train,shuffle_roots=roots,effect_columns=cols,target_names=manifest['target_names'],fixed_mapping=fixed.tolist(),fresh_mappings=fresh.tolist(),parent_final_record=PARENT_LAST,parent_final_ledger_sha256=PARENT_LEDGER_SHA,semantic_validated=False)
    if len(train)!=21:raise ValueError('all21TRAIN required')
    _,packets=effect_packets(arrays,plan);plan['packet_sha256']=hashlib.sha256(packets.tobytes()).hexdigest();plan['shuffle_changes']=dict(fixed=shuffle_change_report(packets,fixed),fresh=[shuffle_change_report(packets,m)for m in fresh]);assigned=shuffle_labels(arrays,plan,fixed)
    x,c=E.scale_inputs(arrays,plan['scalers']);audits={}
    for name,labels in(('correct',arrays),('fixed-shuffle',assigned)):
        subset={k:v[train]if v.shape[:1]==(48,)else v for k,v in labels.items()}
        audits[name]=E.exact_input_conflicts(subset,manifest,plan['documents'],plan['codes'],x[train],c[train],train_codes=plan['train_codes'])
    if audits['correct']['conflict_count']:raise ValueError('correct TRAIN input-label contradiction')
    plan['TRAIN_input_conflicts']=audits
    fresh_packets=packets[fresh];plan['fresh_dynamic_conflicts']=dict(intentional=True,root_head_coordinates_with_multiple_assigned_values=int(sum(len(np.unique(fresh_packets[:,r,h]))>1 for r in range(14)for h in range(5))),total_coordinates=70,interpretation='Same input intentionally receives changing labels acrossupdates. Fixed contradictions, if any, remain reported without permutation reselection.')
    paths=[Path(__file__),HERE/'test_learning_sanity.py',HERE/'LEARNING_SANITY_PROTOCOL.md',PRIOR/'learner-plan.json',PRIOR/'fit-1/initial-checkpoint.npz',PRIOR/'fit-1/result.json',PRIOR/'campaign-ledger.jsonl']+[Path(p['path'])for p in prior['pins']]
    plan['pins']=[pin(p)for p in sorted(set(p.resolve()for p in paths))];path.parent.mkdir(parents=True,exist_ok=True);write(path,plan);return plan

# One new allocation, explicitly linked to the CLOSED previous campaign.
# This ledger cannot reset/retry or debit the earlier allocation.
def canonical_ledger(path):
    expected=(DEFAULT/'campaign-ledger.jsonl').resolve()
    if Path(path).resolve()!=expected:raise ValueError('one fixed canonical sanity ledger required; copied quota paths cannot reset exposure')
    return expected

def ledger_state(rows,plan_path):
    previous='0'*64;pending=False;finished=False
    for i,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'}
        if row['sequence']!=i or row['previous_sha256']!=previous or digest(body)!=row['record_sha256']:raise ValueError('sanity ledger hash chain damaged')
        event=row['event'];data=row['data']
        if i==0:
            if event!='initialized'or data['plan']!=pin(plan_path)or data['config']!=CONFIG or data['parent_final_record']!=PARENT_LAST or data.get('ledger_path')!=str((DEFAULT/'campaign-ledger.jsonl').resolve()):raise ValueError('one exact new plan, canonical ledger and prior final reference required')
        elif i==1:
            if event!='attempt-start'or data['reservation']!=dict(seconds=30.,optimizer_updates=900,training_forwards=900,evaluation_forwards=6,export_forwards=0,native_applies=0):raise ValueError('one fixed sanity attempt required')
            pending=True
        elif i==2:
            if event!='attempt-finish'or data['status']not in('completed','failed')or data['charged_optimizer_updates']!=900 or data['charged_training_forwards']!=900 or data['charged_evaluation_forwards']!=6:raise ValueError('failed work retains full fixed exposure')
            if data['active_seconds']<0 or not __import__('math').isfinite(data['active_seconds']):raise ValueError('finite nonnegative actual elapsed required')
            if data['status']=='completed'and(data['active_seconds']>30 or data['counts']!=dict(optimizer_updates=900,training_forwards=900,evaluation_forwards=6,export_forwards=0,backwards=900)):raise ValueError('completed fixed counters/time differ')
            pending=False;finished=True
        else:raise ValueError('no retry/reset/credit event supported')
        previous=row['record_sha256']
    if not rows:raise ValueError('explicit root initialization required')
    return dict(pending=pending,finished=finished,last_hash=previous)

def append_ledger(stream,rows,plan_path,event,data):
    body=dict(sequence=len(rows),previous_sha256=rows[-1]['record_sha256']if rows else'0'*64,event=event,data=data);row=dict(body,record_sha256=digest(body));ledger_state([*rows,row],plan_path)
    stream.seek(0,2);stream.write(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno());rows.append(row)

def initialize(ledger,plan_path):
    ledger=canonical_ledger(ledger)
    plan=read(plan_path);E.verify_pins(plan['pins']);validate_parent()
    ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open('x+')as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);append_ledger(stream,[],plan_path,'initialized',dict(plan=pin(plan_path),config=CONFIG,ledger_path=str(ledger),parent_final_record=PARENT_LAST,parent_ledger=pin(PRIOR/'campaign-ledger.jsonl')))

def execute(plan_path,out,ledger,progress):
    ledger=canonical_ledger(ledger)
    plan=read(plan_path);E.verify_pins(plan['pins']);validate_parent()
    if plan['source_sha256']!=sha(__file__)or plan['config']!=CONFIG:raise ValueError('exact frozen sanity source/config required')
    if out.exists()or progress.exists():raise FileExistsError('prior attempt artifacts preserved; no retry/reset')
    with ledger.open('r+')as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);rows=[json.loads(x)for x in stream if x.strip()];state=ledger_state(rows,plan_path)
        if len(rows)!=1 or state['pending']or state['finished']:raise ValueError('single fresh root-initialized sanity allocation only')
        out.mkdir(parents=True);progress.parent.mkdir(parents=True,exist_ok=True)
        append_ledger(stream,rows,plan_path,'attempt-start',dict(reservation=dict(seconds=30.,optimizer_updates=900,training_forwards=900,evaluation_forwards=6,export_forwards=0,native_applies=0),source=pin(__file__),pins=plan['pins'],out=str(out.resolve()),progress=str(progress.resolve())))
        start=time.monotonic();guard=E.Guard(30.);counts=dict(optimizer_updates=0,training_forwards=0,evaluation_forwards=0,export_forwards=0,backwards=0);status='failed';error=None
        def forward(kind,arm,step):
            key='training_forwards'if kind=='train'else'evaluation_forwards';counts[key]+=1
            if counts[key]>CONFIG[key]:raise RuntimeError('fixed forward ceiling exceeded')
            E.append_journal(progress,dict(event='forward-intent',kind=kind,arm=arm,step=step,global_forward=counts['training_forwards']+counts['evaluation_forwards']))
        try:
            with guard:
                import numpy as np
                import torch
                torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
                with np.load(plan['dataset'],allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
                true_hashes={k:hashlib.sha256(arrays[k].tobytes()).hexdigest()for k in('targets','target_mask','source_targets','source_mask','selected_candidate_indices')}
                prior=read(plan['prior_plan']);manifest=E.joined_manifest(read(plan['manifest']),prior);E.validate_data(arrays,manifest,prior)
                full,_=E.make_bank(plan['documents'],plan['codes'],plan['train_codes'],plan['vocabularies'],False);restricted,_=E.make_bank(plan['documents'],plan['codes'],plan['train_codes'],plan['vocabularies'],True);full={k:torch.as_tensor(v)for k,v in full.items()};restricted={k:torch.as_tensor(v)for k,v in restricted.items()}
                x,c=map(torch.as_tensor,E.scale_inputs(arrays,plan['scalers']));q=torch.as_tensor([plan['codes'].index(str(code))for code in arrays['source_cards']]);selected=torch.as_tensor(arrays['selected_candidate_indices']);batch=np.asarray(plan['train_indices'],np.int64)
                with np.load(plan['initial_checkpoint'],allow_pickle=False)as p:initial={k:torch.as_tensor(p[k].copy())for k in p.files}
                import shutil
                shutil.copyfile(plan['initial_checkpoint'],out/'initial-checkpoint.npz');np.savez_compressed(out/'shuffle-schedules.npz',train_indices=batch,shuffle_roots=np.asarray(plan['shuffle_roots'],np.int64),fixed_mapping=np.asarray(plan['fixed_mapping'],np.int64),fresh_mappings=np.asarray(plan['fresh_mappings'],np.int64))
                assigned_fixed=shuffle_labels(arrays,plan,np.asarray(plan['fixed_mapping'],np.int64));results={};snapshots={}
                for arm in ARMS:
                    model=E.make_model(torch,plan['vocabularies'],12,7)
                    if set(model.state_dict())!=set(initial)or sum(v.numel()for v in initial.values())!=11856:raise ValueError('strict saved11856named initialization required')
                    model.load_state_dict(initial,strict=True);E.configure_arm(model,'rich-typed');optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=.003,weight_decay=.0001);evaluations={};group_gradients={}
                    if sum(p.numel()for p in model.parameters()if p.requires_grad)!=11728:raise ValueError('matched typed trainable count differs')
                    for step in range(301):
                        if step in(0,300):
                            model.eval();forward('evaluate',arm,step)
                            with torch.inference_mode():sp,bp,vectors=model(x,c,q,full,'rich-typed',selected);source,branch=E.prior().decode(torch,sp,bp,plan['scalers'])
                            evaluations[str(step)]=dict(true_targets=E.evaluate_metrics(source,branch,arrays,manifest,prior),true_TRAIN_effects=sanity_metrics(branch,arrays,plan))
                            if arm=='fixed-shuffle':evaluations[str(step)]['assigned_TRAIN_effects']=sanity_metrics(branch,assigned_fixed,plan)
                            np.savez_compressed(out/f'{arm}-step{step}-predictions.npz',source=source,branch=branch,card_vectors=vectors.detach().numpy(),source_cards=arrays['source_cards'],state_families=arrays['state_families'],selected_candidate_indices=arrays['selected_candidate_indices'])
                        if step==300:break
                        labels=arrays if arm=='correct'else assigned_fixed if arm=='fixed-shuffle'else shuffle_labels(arrays,plan,np.asarray(plan['fresh_mappings'][step],np.int64))
                        tensors={k:torch.as_tensor(labels[k][batch])for k in('source_targets','source_mask','targets','target_mask')};model.train();optimizer.zero_grad(set_to_none=True);forward('train',arm,step+1)
                        sp,bp,_=model(x[batch],c[batch],q[batch],restricted,'rich-typed',selected[batch]);objective=E.fixed_loss(torch,sp,bp,tensors,plan['scalers'])
                        if not bool(torch.isfinite(objective)):raise ValueError('nonfinite sanity objective')
                        objective.backward();counts['backwards']+=1
                        if step==299:group_gradients={n:dict(rms=float(p.grad.square().mean().sqrt()),nonzero=int(torch.count_nonzero(p.grad)),elements=p.numel())for n,p in model.named_parameters()if p.grad is not None}
                        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                        if not bool(torch.isfinite(norm)):raise ValueError('nonfinite gradient')
                        optimizer.step();counts['optimizer_updates']+=1;E.append_journal(progress,dict(event='optimizer-update',global_update=counts['optimizer_updates'],arm=arm,arm_update=step+1,loss=float(objective.detach()),preclip_gradient_norm=float(norm)))
                    weights={n:p.detach().numpy().copy()for n,p in model.state_dict().items()};np.savez_compressed(out/f'{arm}-checkpoint.npz',**weights)
                    movement={n:dict(delta_l2=float(np.linalg.norm((v-initial[n].numpy()).astype(np.float64))),changed=int(np.count_nonzero(v!=initial[n].numpy())),elements=v.size)for n,v in weights.items()}
                    results[arm]=dict(evaluations=evaluations,checkpoint=pin(out/f'{arm}-checkpoint.npz'),last_step_preclip_gradients=group_gradients,weight_movement=movement)
                E.verify_pins(plan['pins']);validate_parent();durable=E.journal_counts(progress)
                if true_hashes!={k:hashlib.sha256(arrays[k].tobytes()).hexdigest()for k in true_hashes}:raise ValueError('in-memory original TRUE labels/masks/anchors changed')
                if durable!={k:CONFIG[k]for k in durable}or counts['backwards']!=900:raise ValueError('exact900updates906forwards durable journal differs')
                gate=overfit_gate(results['correct']['evaluations']['0']['true_TRAIN_effects'],results['correct']['evaluations']['300']['true_TRAIN_effects'])
                write(out/'contract.json',dict(plan=pin(plan_path),source=pin(__file__),config=CONFIG,scalers=plan['scalers'],parameters=plan['parameters'],parent_final_record=PARENT_LAST))
                write(out/'result.json',dict(status='completed',counts=counts,results=results,correct_overfit_gate=gate,shuffle_changes=plan['shuffle_changes'],TRAIN_input_conflicts=plan['TRAIN_input_conflicts'],fresh_dynamic_conflicts=plan['fresh_dynamic_conflicts'],true_label_array_sha256=true_hashes,source=pin(__file__),plan=pin(plan_path),initial_checkpoint=pin(out/'initial-checkpoint.npz'),all_inputs_unchanged=True,semantic_validated=False,limitations='Diagnostic on previously observed TRAIN data. No held stopping, hyperparameter/capacity search, production qualification or new representation. Fixed and correct may both memorize; fresh targets conflict acrossupdates.'))
            status='completed'
        except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
        elapsed=time.monotonic()-start
        if elapsed>30:status='failed';error=error or dict(type='BudgetExceeded',message='total owned worker time exceeded30s')
        try:durable=E.journal_counts(progress)
        except BaseException as exc:durable=None;status='failed';error=dict(type=type(exc).__name__,message=str(exc),journal_unverified=True)
        receipt=dict(status=status,error=error,active_seconds=elapsed,counts=counts,durable_counts=durable,charged_optimizer_updates=900,charged_training_forwards=900,charged_evaluation_forwards=6,guard=guard.receipt(),source=pin(__file__),plan=pin(plan_path),progress=pin(progress)if progress.exists()else None,result=pin(out/'result.json')if(out/'result.json').exists()else None,native_applies=0,paid_jobs=0,parent_final_record=PARENT_LAST)
        write(out/'receipt.json',receipt);append_ledger(stream,rows,plan_path,'attempt-finish',dict(status=status,active_seconds=elapsed,counts=counts,charged_optimizer_updates=900,charged_training_forwards=900,charged_evaluation_forwards=6,receipt=pin(out/'receipt.json')))
        if status!='completed':raise RuntimeError('failed sanity attempt retained: '+str(error))
        return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    for key in('prepare','initialize-ledger','preflight','execute'):mode.add_argument('--'+key,action='store_true')
    p.add_argument('--plan',type=Path,default=DEFAULT/'sanity-plan.json');p.add_argument('--ledger',type=Path,default=DEFAULT/'campaign-ledger.jsonl');p.add_argument('--out',type=Path,default=DEFAULT/'fit-1');p.add_argument('--progress',type=Path,default=DEFAULT/'fit-progress.jsonl');a=p.parse_args()
    if a.prepare:prepare(a.plan);print(json.dumps(pin(a.plan)))
    elif a.initialize_ledger:initialize(a.ledger,a.plan);print(json.dumps(pin(a.ledger)))
    elif a.preflight:
        plan=read(a.plan);E.verify_pins(plan['pins']);validate_parent();print(json.dumps(dict(status='pure-preflight',plan=pin(a.plan),config=CONFIG,parameters=plan['parameters'],no_execution=True)))
    else:print(json.dumps(execute(a.plan,a.out,a.ledger,a.progress),allow_nan=False))
if __name__=='__main__':main()
