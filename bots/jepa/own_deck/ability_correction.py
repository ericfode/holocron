"""Frozen-weight eligibility-only relation exclusion; root freeze/GO required.

Two original model forwards per seed: original corrected C1R1 input, then the
same normalized input with only candidate columns41:43 zero. The corrected
output borrows only eligibility from the second view. No training, extra model
parameters, new program symbols, scaler fitting, native calls or exports.
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
SEEDS=(17,29,43)
RELATION_COLUMNS=(41,42)
TOLERANCE=1e-6
CONFIG=dict(seeds=list(SEEDS),rows=8,neural_forwards=6,forwards_per_seed=2,optimizer_updates=0,numerical_fits=0,native_applies=0,export_forwards=0,paid_jobs=0,paid_spend_usd=0.,relation_columns=list(RELATION_COLUMNS),tolerance=TOLERANCE,primary_roles=['anchor_a','anchor_b'],semantic_validated=False,
    task='Fresh states of the exposed IBH_104 program; no new-program transfer claim',correction='O unchanged except target_allowed=N.target_allowed, N zeros only normalized candidate relation columns41:43')


def require(ok,message):
    if not ok:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text())
def pin(path):
    path=Path(path).resolve();raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def native(value,np=None):
    if np is not None and isinstance(value,np.generic):return native(value.item(),np)
    if isinstance(value,dict):return{native(k,np):native(v,np)for k,v in value.items()}
    if isinstance(value,(tuple,list)):return[native(v,np)for v in value]
    if value is None or type(value)in(bool,int,float,str):return value
    raise TypeError('unsupported JSON type; no string/array fallback: '+type(value).__name__)
def write_new(path,value,np=None):
    raw=(json.dumps(native(value,np),indent=2,allow_nan=False)+'\n').encode()
    with Path(path).open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
def array_sha(value):return hashlib.sha256(str(value.dtype).encode()+str(value.shape).encode()+value.tobytes()).hexdigest()
def state_sha(values):return hashlib.sha256(json.dumps({k:array_sha(values[k])for k in sorted(values)},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load_npz(np,path):
    with np.load(path,allow_pickle=False)as values:return{k:values[k].copy()for k in values.files}


def validate(arrays,manifest,old_plan,x,c):
    import numpy as np
    n=8
    for key,shape in dict(context_features=(n,18),candidate_features=(n,8,34),source_targets=(n,9),source_mask=(n,9),targets=(n,8,7),target_mask=(n,8,7),selected_candidate_indices=(n,)).items():
        require(arrays[key].shape==shape,'fixed fresh8 shape differs: '+key)
        if arrays[key].dtype.kind in'fi':require(np.isfinite(arrays[key]).all(),'nonfinite '+key)
    require(x.shape==(8,32)and c.shape==(8,8,43)and x.dtype==c.dtype==np.float32,'unchanged normalized32/43 float32 ABI required')
    require(np.isfinite(x).all()and np.isfinite(c).all(),'nonfinite consumed input')
    require(arrays['selected_candidate_indices'].dtype==np.int64 and np.all((arrays['selected_candidate_indices']>=0)&(arrays['selected_candidate_indices']<8)),'public pre-action selected index required')
    require(arrays['source_cards'].astype(str).tolist()==['IBH_104']*8,'exposed IBH program only; no fresh-program claim')
    require(old_plan['codes'].index('IBH_104')==7 and len(old_plan['codes'])==8 and len(old_plan['train_codes'])==6,'exact original bank/table cardinalities required')
    require(not manifest.get('errors',0)and not manifest.get('fit_blockers')and not manifest.get('pending',0),'native observation failure stops fixed-weight test')
    require(manifest['target_names']==[s['name']for s in old_plan['scalers']['targets']]and manifest['source_head_names']==[s['name']for s in old_plan['scalers']['source_targets']],'frozen output order required')
    for key in('source_mask','target_mask'):require(np.isin(arrays[key],[0,1]).all(),'known masks must be0/1')
    h=manifest['target_names'].index('target_allowed');require(np.isin(arrays['targets'][...,h][arrays['target_mask'][...,h]>0],[0,1]).all(),'known eligibility binary required')
    pairs=manifest['intent_pairs'];require([(int(p['left_root']),int(p['right_root']))for p in pairs]==[(0,1),(2,3),(4,5),(6,7)],'four fixed intent pairs required')
    anchors=[manifest['candidate_order'].index(r)for r in CONFIG['primary_roles']]
    for pair in pairs:
        a,b=int(pair['left_root']),int(pair['right_root'])
        require(np.array_equal(x[a],x[b])and np.array_equal(c[a,:,:41],c[b,:,:41]),'pair differs in actual consumed non-relation inputs')
        require({int(arrays['selected_candidate_indices'][a]),int(arrays['selected_candidate_indices'][b])}==set(anchors),'pair must vary intended anchorA/B only')
        known=(arrays['target_mask'][a,:,h]>0)&(arrays['target_mask'][b,:,h]>0)
        require(known[anchors].all()and np.array_equal(arrays['targets'][a,known,h],arrays['targets'][b,known,h]),'co-known native eligibility must be intent-invariant; no fabricated labels')
    return anchors


def mixed_view(original_source,original_branch,neutral_source,neutral_branch,allowed):
    """No operation can change a source or non-eligibility endpoint prediction."""
    source=original_source.copy();branch=original_branch.copy();branch[...,allowed]=neutral_branch[...,allowed]
    return source,branch


def eligibility_metrics(branch,arrays,manifest,roles):
    import numpy as np
    h=manifest['target_names'].index('target_allowed');y=arrays['targets'][...,h];p=branch[...,h];mask=arrays['target_mask'][...,h]>0;selected=np.zeros(mask.shape,bool);selected[:,roles]=True;mask&=selected;counts=mask.sum(-1);valid=counts>0
    positive=mask&(y==1);negative=mask&(y==0);np_=int(positive.sum());nn=int(negative.sum());tp=int(((p>=.5)&positive).sum());tn=int(((p<.5)&negative).sum());sensitivity=tp/np_ if np_ else None;specificity=tn/nn if nn else None
    return dict(known=int(mask.sum()),known_roots=int(valid.sum()),positive=np_,negative=nn,mae=float(((abs(p-y)*mask).sum(-1)/np.maximum(counts,1))[valid].mean())if valid.any()else None,
        balanced_accuracy=(sensitivity+specificity)/2 if np_ and nn else None,sensitivity=sensitivity,specificity=specificity)


def invariance(branch,arrays,manifest,roles):
    import numpy as np
    h=manifest['target_names'].index('target_allowed');pairs=[]
    for pair in manifest['intent_pairs']:
        a,b=int(pair['left_root']),int(pair['right_root']);known=(arrays['target_mask'][a,roles,h]>0)&(arrays['target_mask'][b,roles,h]>0);js=np.asarray(roles)[known]
        delta=abs(branch[a,js,h]-branch[b,js,h]);flips=(branch[a,js,h]>=.5)!=(branch[b,js,h]>=.5)
        pairs.append(dict(id=pair.get('id',str(a)+'-'+str(b)),left_root=a,right_root=b,known=int(known.sum()),mean_abs_difference=float(delta.mean())if len(delta)else None,max_abs_difference=float(delta.max())if len(delta)else None,threshold_flip_fraction=float(flips.mean())if len(delta)else None))
    observed=[p for p in pairs if p['known']]
    return dict(pairs=pairs,mean_abs_difference=sum(p['mean_abs_difference']for p in observed)/len(observed)if observed else None,max_abs_difference=max(p['max_abs_difference']for p in observed)if observed else None,
        mean_threshold_flip_fraction=sum(p['threshold_flip_fraction']for p in observed)/len(observed)if observed else None,passed=len(observed)==4 and all(p['max_abs_difference']<=TOLERANCE for p in observed),tolerance=TOLERANCE)


def report_views(views,arrays,manifest,old_plan,anchors):
    import numpy as np
    E=importlib.import_module('effect_identifiability_fit');h=manifest['target_names'].index('target_allowed');other=[i for i in range(7)if i!=h];output={}
    scopes=dict(anchors=anchors,all_known=list(range(8)),non_source=[i for i,r in enumerate(manifest['candidate_order'])if r!='source'])
    for name,(source,branch)in views.items():
        require(np.isfinite(source).all()and np.isfinite(branch).all(),'finite decoded outputs required')
        output[name]=dict(heads=E.head_metrics(source,branch,arrays,manifest,old_plan['scalers'],np.arange(8)),eligibility={scope:eligibility_metrics(branch,arrays,manifest,roles)for scope,roles in scopes.items()},intent_invariance={scope:invariance(branch,arrays,manifest,roles)for scope,roles in scopes.items()})
    o,n,c=views['original'],views['neutral_all_heads'],views['corrected'];controls=dict(source9_bit_identical_to_original=bool(np.array_equal(c[0],o[0])),other6_branch_heads_bit_identical_to_original=bool(np.array_equal(c[1][...,other],o[1][...,other])),eligibility_bit_identical_to_neutral=bool(np.array_equal(c[1][...,h],n[1][...,h])))
    before=output['original']['eligibility']['anchors'];after=output['corrected']['eligibility']['anchors'];mae_ok=before['mae']is not None and after['mae']is not None and after['mae']<=before['mae']+TOLERANCE
    balanced_supported=before['balanced_accuracy']is not None and after['balanced_accuracy']is not None;balanced_ok=balanced_supported and after['balanced_accuracy']>=before['balanced_accuracy']-TOLERANCE
    return dict(views=output,controls=controls,primary=dict(intent_invariant=output['corrected']['intent_invariance']['anchors']['passed'],mae_noninferior=mae_ok,balanced_accuracy_supported=balanced_supported,balanced_accuracy_noninferior=balanced_ok,
        passed=all(controls.values())and output['corrected']['intent_invariance']['anchors']['passed']and mae_ok and balanced_ok,scope='Fixed freshSTATE anchor panel; deterministic noninferiority at1e-6, not population evidence or new-program semantic qualification.'),semantic_validated=False)


def worker(args,run):
    import numpy as np
    import torch
    E=importlib.import_module('effect_identifiability_fit');M=importlib.import_module('public_input_binding_model_v1');B=importlib.import_module('semantic_discrimination_bank')
    torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    old=read(args.old_plan);E.verify_pins(old['pins']);require(old['status']=='sealed-awaiting-root-GO','original sealed plan required');arrays=load_npz(np,args.dataset);manifest=read(args.manifest)
    x,c=M.project_arrays(arrays,manifest,'C1R1',old['scalers']);anchors=validate(arrays,manifest,old,x,c);neutral_c=c.copy();neutral_c[...,41:43]=0
    hashes={k:array_sha(arrays[k])for k in('source_targets','source_mask','targets','target_mask','selected_candidate_indices')};bank_np=B.banks_from_metadata(old,training=False)['full'];require(E.tensor_signatures(bank_np)==old['semantic_signatures']['full'],'original full semantic tensor bank changed');bank={k:torch.as_tensor(v)for k,v in bank_np.items()}
    np.savez_compressed(args.out/'consumed-inputs.npz',context=x,original_candidate=c,neutral_candidate=neutral_c);np.savez_compressed(args.out/'program-inputs.npz',**bank_np)
    tx,tc,tn=map(torch.as_tensor,(x,c,neutral_c));q=torch.full((8,),7,dtype=torch.int64);selected=torch.as_tensor(arrays['selected_candidate_indices']);results={}
    for seed in SEEDS:
        checkpoint=args.fit_dir/f's{seed}-learned-full-checkpoint.npz';weights=load_npz(np,checkpoint);require(all(np.isfinite(v).all()for v in weights.values()),'nonfinite frozen checkpoint');model=M.make_model(torch,old['vocabularies'],8,6);model.load_state_dict({k:torch.as_tensor(v)for k,v in weights.items()},strict=True);M.configure_arm(model,'rich-typed');model.eval();before=state_sha({k:v.detach().numpy()for k,v in model.state_dict().items()});require(before==state_sha(weights),'exact original checkpoint load required');views={};vectors={}
        for name,cc in(('original',tc),('neutral_all_heads',tn)):
            token=run.intent('neural_forwards')
            with torch.inference_mode():sp,bp,p=model(tx,cc,q,bank,'rich-typed',selected)
            run.complete(token);source,branch=E.prior().decode(torch,sp,bp,old['scalers']);views[name]=(source,branch);vectors[name]=p.detach().numpy().copy()
        h=manifest['target_names'].index('target_allowed');views['corrected']=mixed_view(*views['original'],*views['neutral_all_heads'],h)
        after=state_sha({k:v.detach().numpy()for k,v in model.state_dict().items()});require(before==after,'frozen model tensors changed');require(np.array_equal(vectors['original'],vectors['neutral_all_heads']),'input-only relation exclusion cannot change card vectors')
        for name,(source,branch)in views.items():np.savez_compressed(args.out/f's{seed}-{name}-predictions.npz',source=source,branch=branch,card_vectors=vectors['original'],source_cards=arrays['source_cards'],selected_candidate_indices=arrays['selected_candidate_indices'])
        results[str(seed)]=report_views(views,arrays,manifest,old,anchors);results[str(seed)].update(checkpoint=pin(checkpoint),state_sha256_before=before,state_sha256_after=after)
    require(hashes=={k:array_sha(arrays[k])for k in hashes},'native labels/masks/intent changed')
    result=dict(schema='jepa-ability-correction/1',status='completed',config=CONFIG,old_plan=pin(args.old_plan),dataset=pin(args.dataset),manifest=pin(args.manifest),results=results,all_seed_primary_passed=all(v['primary']['passed']for v in results.values()),native_label_hashes=hashes,semantic_validated=False,
        scope='No learning or fresh program. Two original shared-weight forwards per seed; synthetic corrected view only replaces eligibility. All old exposed negatives retained.')
    write_new(args.out/'result.json',result,np);return dict(result=pin(args.out/'result.json'),neural_forwards=6,semantic_validated=False)


def execute(args):
    A=importlib.import_module('sealed_budget');budget=A.Budget(args.spec)
    with budget.lease()as run:
        paths=[args.old_plan,args.dataset,args.manifest]+[args.fit_dir/f's{seed}-learned-full-checkpoint.npz'for seed in SEEDS];allowed=dict(budget.frozen,**run.state['proofs']);inputs=[allowed[str(p.resolve())]for p in paths if str(p.resolve())in allowed];status='failed';error=None;guard=None;created=False;result=None;receipt=args.out.parent/(args.out.name+'-stage-receipt.json')
        try:
            run.begin(args.stage,argv=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]],guard=budget.spec['guard'],inputs=inputs)
            require(len(inputs)==len(paths),'every old/fresh input must be frozen/completed proof');require(budget.spec['stages'][args.stage]['outputs']==[str(args.out.resolve()),str(receipt.resolve())],'exact output directory/receipt descriptor required')
            require(budget.spec['guard']==dict(cpu_workers=1,rss_bytes=1073741824),'audited E.Guard fixed1CPU/1GiB contract required')
            E=importlib.import_module('effect_identifiability_fit');remaining=run.remaining_seconds();require(remaining>0,'startup exhausted stage wall allocation');guard=E.Guard(remaining);args.out.mkdir(parents=True,exist_ok=False);created=True
            with guard:result=native(worker(args,run),sys.modules.get('numpy'))
            status='completed'
        except BaseException as exc:
            if run.state['pending']is None:raise
            error=dict(type=type(exc).__name__,message=str(exc))
        artifacts=[pin(p)for p in sorted(args.out.rglob('*'))if p.is_file()]if created else[];receipt_data=dict(status=status,error=error,result=result,source=pin(__file__),artifact_pins=artifacts,guard=guard.receipt()if guard else None,semantic_validated=False,authority='Final shared ledger may downgrade completion after receipt/proof writes; failures retain full reservation.')
        receipt_pin=None
        try:write_new(receipt,receipt_data);receipt_pin=pin(receipt)
        except BaseException as exc:status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        finished=run.finish(status,proofs=artifacts+([receipt_pin]if receipt_pin else[]),cleanup_verified=True,execution_ended=True)
        require(status=='completed'and args.stage in finished['completed'],'bounded correction failed; ledger remains authoritative: '+str(error));return receipt_data


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--stage',default='correction')
    for name in('old-plan','fit-dir','dataset','manifest','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(execute(args),indent=2,allow_nan=False))


if __name__=='__main__':main()
