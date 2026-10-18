"""Frozen-weight response probes. Import/--describe use the standard library only.

Execution requires a separately frozen root allocation. No optimizer, engine,
new native labels, vocabulary growth, fitted transform or checkpoint writes.
Synthetic interventions measure response; saved native outcomes stay immutable.
"""
import argparse
import copy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
SCHEMA='jepa-ability-diagnostic/1'
SEEDS=(17,29,43)
PANELS=('factual-replay','ability-swap-replay','selector-opponent-to-any','cost-cap3-to2',
        'heal-amount3-to1','upTo-count2-to1','source-hp-neutral','source-power-neutral',
        'candidate-cost2-swap3','coherent-intent-swap','intent-neutral')
IR_PANELS=PANELS[2:6]
PUBLIC_PANELS=PANELS[6:]
MUTATION_TARGETS=dict(zip(IR_PANELS,('IBH_104','IBH_104','ASH_081','IBH_104')))
CONFIG=dict(seeds=list(SEEDS),panels=list(PANELS),rows_per_forward=33,neural_forwards=33,
    optimizer_updates=0,backwards=0,native_applies=0,numerical_fits=0,export_forwards=0,
    seconds=15.,rss_bytes=1073741824,cpu_threads=1,paid_jobs=0,replay_atol=1e-6,
    eligibility_head=0,relation_columns=[41,42],semantic_validated=False)


def require(value,message):
    if not value:raise ValueError(message)
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def pin(path):
    p=Path(path).resolve();raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write_new(path,value):
    with Path(path).open('x')as f:f.write(json.dumps(value,indent=2,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def journal(path,value):
    with Path(path).open('a')as f:f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def describe():
    return dict(schema=SCHEMA,config=CONFIG,panels=[dict(id=p,scope=(
        'Same-backend replay against immutable saved output; must pass before response interpretation.'if p in PANELS[:2]else
        'Synthetic IR intervention; response/analytical expectation only. No native counterfactual label.'if p in IR_PANELS else
        'Known source stat coordinate set to TRAIN mean after normalization; printed IR/other features unchanged. Off-manifold shortcut sensitivity.'if p in PANELS[6:8]else
        'Only known non-source cost coordinate raw2<->3; other printed metadata unchanged. Synthetic sensitivity, no new native label.'if p=='candidate-cost2-swap3'else
        'Main roots0..31 relation/gather A<->B; require exact paired factual input equality. Auxiliary32 unchanged.'if p=='coherent-intent-swap'else
        'Both normalized relation coordinates set0, meaning TRAIN means. Reuse output for all-head control and eligibility-only splice; no learned mask.'))for p in PANELS],
        hybrid='source9 and six noneligibility branch heads byte-identical factual; only branch target_allowed from intent-neutral.',
        reference='Generic typed selector/operator/amount prediction baseline; independently saved native labels/masks are never replaced.',
        upTo='Changing maximum2->1 is an expected-null diagnostic under exactly-one selection; null response is not evidence of ignoring rules.',
        outputs=['forward-journal.jsonl','result.json','receipt.json','s{seed}-{panel}-predictions.npz','s{seed}-eligibility-only-neutral-predictions.npz','typed-reference.json'],
        no_new_held_claim=True,semantic_validated=False)


def mutate_documents(documents,panel,codes):
    """Predeclared source-slot intervention, then exact typed-field mutation.

    Code selects the inspected intervention slot only. Neither the learned
    predictor nor the separate typed reference dispatches outcomes by card ID.
    """
    require(panel in IR_PANELS and len(documents)==len(codes),'unknown IR panel/document alignment');out=copy.deepcopy(documents);changes=[]
    def change(node,key,new,path):
        old=node[key];node[key]=new;changes.append(dict(path=list(path+(key,)),old=old,new=new))
    def visit(node,path):
        if isinstance(node,list):
            for i,v in enumerate(node):visit(v,path+(i,))
        elif isinstance(node,dict):
            if path and path[-1]=='targetResolver':
                if panel=='selector-opponent-to-any'and node.get('owner')=='opponent':change(node,'owner','any',path)
                count=node.get('count')
                if panel=='upTo-count2-to1'and node.get('mode')=='upTo'and isinstance(count,dict)and count==dict(kind='const',value=2):change(count,'value',1,path+('count',))
            if panel=='cost-cap3-to2'and node.get('kind')=='binary'and node.get('op')=='<='and node.get('left')==dict(kind='ref',path=['card','cost'])and node.get('right')==dict(kind='const',value=3):change(node['right'],'value',2,path+('right',))
            if panel=='heal-amount3-to1'and node.get('kind')=='heal'and node.get('amount')==dict(kind='const',value=3):change(node['amount'],'value',1,path+('amount',))
            for key,value in node.items():visit(value,path+(key,))
    # Printed information, keywords, attachment conditions and all other rule
    # subtrees stay exact; this is not the old whole-ability donor permutation.
    target=MUTATION_TARGETS[panel];require(list(codes).count(target)==1,'one predeclared intervention source required')
    i=list(codes).index(target);visit(out[i]['abilities'],(i,'abilities'))
    require(changes,'frozen IR panel changed no matching public rule field')
    return out,changes


def public_probe(panel,x,c,selected,scalers):
    """List-only implementation, synthetic-testable without importing NumPy."""
    require(panel in PUBLIC_PANELS,'unknown public panel')
    xx,cc,ss=copy.deepcopy(x),copy.deepcopy(c),list(selected);changes=[]
    def raw(value,key,h):return value*scalers[key]['scale'][h]+scalers[key]['center'][h]
    def norm(value,key,h):return(value-scalers[key]['center'][h])/scalers[key]['scale'][h]
    for i in range(len(xx)):
        if panel in('source-hp-neutral','source-power-neutral'):
            h,k=(11,15)if panel=='source-hp-neutral'else(10,14)
            if math.isclose(raw(xx[i][k],'context_features',k),1.,abs_tol=1e-6):xx[i][h]=0.;changes.append([i,h])
        elif panel=='candidate-cost2-swap3':
            for j in range(1,len(cc[i])):
                row=cc[i][j];known=raw(row[27],'candidate_features',27);cost=raw(row[26],'candidate_features',26)
                if math.isclose(known,1.,abs_tol=1e-6)and any(math.isclose(cost,n,abs_tol=1e-5)for n in(2,3)):
                    new=3 if math.isclose(cost,2.,abs_tol=1e-5)else 2;row[26]=norm(new,'candidate_features',26);changes.append([i,j,26])
        elif panel=='coherent-intent-swap':
            if i==32:continue
            require(ss[i]in(3,4),'frozen physical A/B intent required');ss[i]=7-ss[i]
            for j,row in enumerate(cc[i]):
                require(math.isclose(raw(row[42],'candidate_features',42),1.,abs_tol=1e-6),'known pre-action relation required')
                row[41]=norm(float(j==ss[i]),'candidate_features',41)
            changes.append([i,ss[i]])
        else:
            for j,row in enumerate(cc[i]):row[41]=row[42]=0.;changes.append([i,j,41,42])
    return xx,cc,ss,changes


def reference_score(predictions,arrays,manifest,split):
    """List-only overlap metrics: analytical predictions never become labels."""
    result={};names=manifest['target_names'];binary=set(manifest['binary_heads'])
    for cell,indices in split['root_partitions'].items():
        per={}
        for code in sorted({str(arrays['source_cards'][i])for i in indices}):
            heads={};roots=[i for i in indices if str(arrays['source_cards'][i])==code]
            for h,name in enumerate(names):
                native=overlap=correct=0;errors=[];root_errors=[]
                for i in roots:
                    current_errors=[]
                    for j,role in enumerate(manifest['candidate_order']):
                        known=bool(arrays['target_mask'][i][j][h]);native+=int(known)
                        ref=predictions[i]['observations'].get(role)
                        if not known or ref is None or not ref['mask'][h]:continue
                        overlap+=1;p=float(ref['values'][h]);y=float(arrays['targets'][i][j][h]);e=abs(p-y);errors.append(e);current_errors.append(e)
                        sign=lambda v:1 if v>.25 else-1 if v<-.25 else 0
                        correct+=int((p>=.5)==(y>=.5))if name in binary else int(sign(p)==sign(y))
                    if current_errors:root_errors.append(sum(current_errors)/len(current_errors))
                heads[name]=dict(native_known=native,coobserved=overlap,uncovered_native=native-overlap,coordinate_mae=sum(errors)/len(errors)if errors else None,
                    root_balanced_mae=sum(root_errors)/len(root_errors)if root_errors else None,max_abs_error=max(errors)if errors else None,
                    classification_accuracy=correct/overlap if overlap and name in binary else None,zero_sign_accuracy=correct/overlap if overlap and name not in binary else None)
            per[code]=heads
        result[cell]=per
    return dict(cells=result,label_origin='analytical-public-IR-not-native',source_heads='Unknown by direct-effect reference scope',semantic_validated=False)


def intent_pair_stats(branch,native,mask,codes,roles):
    """Eligibility invariance only; repeated A/B intentions are nested pairs."""
    result={}
    for i in range(0,32,2):
        require(codes[i]==codes[i+1],'same-card main pair required')
        for j,role in enumerate(roles):
            if not(mask[i][j][0]and mask[i+1][j][0]):continue
            require(native[i][j][0]==native[i+1][j][0],'native eligibility changes with declared intent')
            a,b=float(branch[i][j][0]),float(branch[i+1][j][0]);key=str(codes[i])+':'+role
            record=result.setdefault(key,dict(card=str(codes[i]),role=role,absolute_pair_differences=[],classification_flips=0,pairs=0))
            record['absolute_pair_differences'].append(abs(a-b));record['classification_flips']+=int((a>=.5)!=(b>=.5));record['pairs']+=1
    for record in result.values():
        values=record['absolute_pair_differences'];record.update(mean_abs_intent_difference=sum(values)/len(values),max_abs_intent_difference=max(values),classification_flip_rate=record['classification_flips']/record['pairs'])
    return dict(groups=list(result.values()),scope='Main32 roots only; two scenarios/card, repeated intended choices, no auxiliary32 or independence claim.')


def prepare(sealed_path,fit_dir,out):
    """Metadata/pins only. Coordinator must allocate preparation explicitly."""
    sealed=read(sealed_path);manifest=read(sealed['manifest']);fit_dir=Path(fit_dir).resolve()
    require(sealed['codes']==['LAW_045','ASH_071','LOF_077','JTL_078','LAW_133','JTL_140','ASH_081','IBH_104'],'frozen exposed eight-card bank required')
    paths=[Path(__file__),HERE/'test_ability_diagnostic.py',HERE/'ability_typed_reference.py',HERE/'test_ability_typed_reference.py',HERE/'sealed_budget.py',HERE/'semantic_discrimination_fit_v2.py',HERE/'semantic_discrimination_bank.py',HERE/'public_input_binding_model_v1.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',Path(sealed_path),Path(sealed['dataset']),Path(sealed['manifest']),fit_dir/'contract.json',fit_dir/'result.json',Path(manifest['native_receipt']['path'])]
    seeds={}
    for seed in SEEDS:
        seeds[str(seed)]=dict(checkpoint=str(fit_dir/f's{seed}-learned-full-checkpoint.npz'),correct=str(fit_dir/f's{seed}-learned-full-step200-predictions.npz'),swapped=str(fit_dir/f's{seed}-learned-full-step200-ability-swapped-predictions.npz'))
        paths.extend(map(Path,seeds[str(seed)].values()))
    require(not Path(out).exists(),'preserve prior diagnostic plan')
    result=dict(schema=SCHEMA,status='frozen-awaiting-root-GO',config=CONFIG,description=describe(),sealed_plan=str(Path(sealed_path).resolve()),fit_dir=str(fit_dir),seeds=seeds,pins=[pin(p)for p in dict.fromkeys(paths)],semantic_validated=False)
    write_new(out,result);return result


def _execute(plan_path,out,run):
    """One root-supervised attempt; guard precedes NumPy/Torch and bank creation."""
    for k in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    E=importlib.import_module('effect_identifiability_fit') # stdlib-only guard owner
    started=time.monotonic();counts=dict(neural_forwards=0,optimizer_updates=0,backwards=0,native_applies=0,numerical_fits=0,paid_jobs=0)
    out=Path(out);require(not out.exists(),'one attempt only; preserve all prior outputs');out.mkdir(parents=True)
    progress=out/'forward-journal.jsonl';status='failed';error=None;result=None;guard=None
    try:
        with E.Guard(min(CONFIG['seconds'],run.remaining_seconds()))as guard:
            frozen=read(plan_path);require(frozen['schema']==SCHEMA and frozen['config']==CONFIG and frozen['status']=='frozen-awaiting-root-GO','exact frozen diagnostic plan required')
            for p in frozen['pins']:require(run.owner.frozen.get(p['path'])==p and pin(p['path'])==p,'diagnostic source/input pin differs or is absent from budget spec: '+p['path'])
            import numpy as np
            import torch
            M=importlib.import_module('public_input_binding_model_v1');B=importlib.import_module('semantic_discrimination_bank');F=importlib.import_module('semantic_discrimination_fit_v2');R=importlib.import_module('ability_typed_reference')
            torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
            load=lambda p:F.npz(np,p)
            sealed=read(frozen['sealed_plan']);E.verify_pins(sealed['pins']);arrays=load(sealed['dataset']);manifest=read(sealed['manifest']);F.validate_data(arrays,manifest,sealed)
            require(list(manifest['target_names'])==list(R.HEADS),'reference/head order differs')
            x,c=M.project_arrays(arrays,manifest,scalers=sealed['scalers']);selected=arrays['selected_candidate_indices'];q=torch.as_tensor([sealed['codes'].index(str(code))for code in arrays['source_cards']]);fullbanks=B.banks_from_metadata(sealed,False)
            mutated={};mutation_audit={}
            for panel in IR_PANELS:
                docs,changes=mutate_documents(sealed['documents'],panel,sealed['codes']);mutated[panel]=B._encode(docs,sealed['codes'],sealed['train_codes'],sealed['vocabularies'],sealed['numeric_scale'],False);mutation_audit[panel]=changes
            probe_cache={p:public_probe(p,x.tolist(),c.tolist(),selected.tolist(),sealed['scalers'])for p in PUBLIC_PANELS}
            sx,sc,si,_=probe_cache['coherent-intent-swap'];twins=[i^1 if i<32 else 32 for i in range(33)]
            require(all(np.array_equal(np.asarray(sx[i],np.float32),x[t])and np.array_equal(np.asarray(sc[i],np.float32),c[t])and si[i]==int(selected[t])and arrays['source_cards'][i]==arrays['source_cards'][t]for i,t in enumerate(twins)),'coherent intent probe lacks exact same-public-state factual twins')
            raw=read(manifest['native_receipt']['path']);cases=sorted(raw['cases'],key=lambda r:r['world_id']);rows=manifest['public_catalog_rows']
            require(len(cases)==33 and[case['world_id']for case in cases]==list(range(33)),'reference native-before alignment differs')
            reference=[R.reference_case(manifest['cards'][case['card']]['raw_card'],case,rows)for case in cases]
            ref_mutations={}
            for panel in IR_PANELS:
                target=MUTATION_TARGETS[panel];case_indices=[i for i,case in enumerate(cases)if case['card']==target];require(len(case_indices)==4,'four exposed intervention roots required')
                raw_doc=dict(abilities=copy.deepcopy(manifest['cards'][target]['raw_card']['abilities']));changed,_=mutate_documents([raw_doc],panel,[target]);raw_card=copy.deepcopy(manifest['cards'][target]['raw_card']);raw_card['abilities']=changed[0]['abilities']
                ref_mutations[panel]={str(i):R.reference_case(raw_card,cases[i],rows)for i in case_indices}
            refscore=reference_score(reference,{k:v.tolist()for k,v in arrays.items()},manifest,sealed['split'])
            reference_values=np.zeros_like(arrays['targets']);reference_masks=np.zeros_like(arrays['target_mask'])
            for i,pred in enumerate(reference):
                for j,role in enumerate(manifest['candidate_order']):
                    observation=pred['observations'].get(role)
                    if observation is not None:reference_values[i,j]=observation['values'];reference_masks[i,j]=observation['mask']
            reference_arrays=dict(arrays,target_mask=arrays['target_mask']*reference_masks)
            reference_primary=F.primary_scores(reference_values,reference_arrays,manifest,sealed)
            write_new(out/'typed-reference.json',dict(schema='jepa-ability-reference-output/1',predictions=reference,baseline_metrics=refscore,mutated_analytical_expectations=ref_mutations,
                reference_calls=49,native_receipt=manifest['native_receipt'],label_origin='analytical-public-IR-not-native',semantic_validated=False))
            results={};replays={};weights={};tensorpins={k:F.sha_array(arrays[k])for k in('source_targets','source_mask','targets','target_mask')}
            def response(pred,factual):
                report={}
                for key,names in(('source',manifest['source_head_names']),('branch',manifest['target_names'])):
                    per={}
                    for code in sealed['codes']:
                        ix=np.flatnonzero(arrays['source_cards']==code);heads={}
                        for h,name in enumerate(names):
                            delta=pred[key][ix,...,h]-factual[key][ix,...,h]
                            # Per-anchor reports include unobserved outcomes only
                            # as model response, never as native error/accuracy.
                            heads[name]=dict(mean_abs_response=float(abs(delta).mean()),max_abs_response=float(abs(delta).max()),mean_signed_response=float(delta.mean()),by_anchor=None if key=='source'else{r:dict(mean=float(delta[:,j].mean()),max_abs=float(abs(delta[:,j]).max()))for j,r in enumerate(manifest['candidate_order'])})
                        per[code]=heads
                    report[key]=per
                return report
            for seed in SEEDS:
                inputs=frozen['seeds'][str(seed)];saved={p:load(inputs[p])for p in('correct','swapped')};state=load(inputs['checkpoint']);model=M.make_model(torch,sealed['vocabularies'],len(sealed['codes']),len(sealed['train_codes']));M.configure_arm(model,'rich-typed')
                expected=model.state_dict();require(set(state)==set(expected)and all(state[k].shape==tuple(expected[k].shape)and state[k].dtype==expected[k].detach().numpy().dtype and np.isfinite(state[k]).all()for k in state),'exact finite named checkpoint required')
                model.load_state_dict({k:torch.as_tensor(v)for k,v in state.items()},strict=True);model.eval();before=F.state_hash({k:v.detach().numpy()for k,v in model.state_dict().items()});seedresults={};predictions={}
                require(before==F.state_hash(state),'checkpoint load changed named tensors')
                for panel in PANELS:
                    xx,cc,ss=x,c,selected;bank=fullbanks['swapped_full'if panel=='ability-swap-replay'else'full']
                    if panel in IR_PANELS:bank=mutated[panel]
                    if panel in PUBLIC_PANELS:
                        px,pc,ps,_=probe_cache[panel];xx,cc,ss=np.asarray(px,np.float32),np.asarray(pc,np.float32),np.asarray(ps,np.int64)
                    counts['neural_forwards']+=1;require(counts['neural_forwards']<=33,'fixed diagnostic forward ceiling exceeded')
                    token=run.intent('neural_forwards');journal(progress,dict(event='forward-intent',global_forward=counts['neural_forwards'],seed=seed,panel=panel,rows=33,budget_token=token))
                    with torch.inference_mode():sp,bp,vectors=model(torch.as_tensor(xx),torch.as_tensor(cc),q,{k:torch.as_tensor(v)for k,v in bank.items()},'rich-typed',torch.as_tensor(ss));source,branch=E.prior().decode(torch,sp,bp,sealed['scalers'])
                    run.complete(token);vectors=vectors.detach().numpy().copy()
                    require(all(np.isfinite(v).all()for v in(source,branch,vectors)),'nonfinite diagnostic prediction');pred=dict(source=source,branch=branch);predictions[panel]=pred
                    journal(progress,dict(event='forward-complete',global_forward=counts['neural_forwards'],seed=seed,panel=panel))
                    np.savez_compressed(out/f's{seed}-{panel}-predictions.npz',**pred,card_vectors=vectors)
                    if panel in PANELS[:2]:
                        old=saved['correct'if panel=='factual-replay'else'swapped'];gap=max(float(abs(pred[k]-old[k]).max())for k in('source','branch'));require(gap<=CONFIG['replay_atol'],'saved replay mismatch: '+panel);replays[f'{seed}:{panel}']=dict(max_abs_error=gap,tolerance=CONFIG['replay_atol'],bit_exact=all(np.array_equal(pred[k],old[k])for k in('source','branch')))
                    seedresults[panel]=dict(response=response(pred,predictions['factual-replay']),native_evaluation=F.evaluation(source,branch,arrays,manifest,sealed)if panel in PANELS[:2]+('intent-neutral',)else None,
                        score_scope='Saved native masks only for factual/swap/Rneutral context; synthetic responses are not new native outcomes.')
                factual=predictions['factual-replay'];neutral=predictions['intent-neutral'];hybrid=dict(source=factual['source'].copy(),branch=factual['branch'].copy());hybrid['branch'][...,0]=neutral['branch'][...,0]
                require(np.array_equal(hybrid['source'],factual['source'])and np.array_equal(hybrid['branch'][...,1:],factual['branch'][...,1:]),'eligibility-only splice altered endpoint predictions')
                np.savez_compressed(out/f's{seed}-eligibility-only-neutral-predictions.npz',**hybrid)
                seedresults['eligibility-only-neutral']=dict(response=response(hybrid,factual),native_evaluation=F.evaluation(hybrid['source'],hybrid['branch'],arrays,manifest,sealed),exact_endpoint_invariance=True)
                seedresults['eligibility_intent_invariance']={name:intent_pair_stats(pred['branch'].tolist(),arrays['targets'].tolist(),arrays['target_mask'].tolist(),arrays['source_cards'].tolist(),manifest['candidate_order'])for name,pred in(('original',factual),('all-head-neutral',neutral),('eligibility-only-neutral',hybrid))}
                examples=[];edit_expectations=[]
                for i,code in enumerate(arrays['source_cards'].astype(str)):
                    for j,role in enumerate(manifest['candidate_order']):
                        for h,name in enumerate(manifest['target_names']):
                            nk=bool(arrays['target_mask'][i,j,h]);rk=bool(reference_masks[i,j,h]);y=float(arrays['targets'][i,j,h])if nk else None;rv=float(reference_values[i,j,h])if rk else None;lv=float(factual['branch'][i,j,h])
                            examples.append(dict(root=i,card=code,role=role,head=name,primary_anchor=role in('anchor_a','anchor_b'),native_known=nk,native_value=y,
                                analytical_known=rk,analytical_value=rv,learned_value=lv,learned_native_abs_error=abs(lv-y)if nk else None,analytical_native_abs_error=abs(rv-y)if nk and rk else None))
                for panel,refs in ref_mutations.items():
                    for key,edited in refs.items():
                        i=int(key)
                        for j,role in enumerate(manifest['candidate_order']):
                            original=reference[i]['observations'].get(role);changed=edited['observations'].get(role)
                            for h,name in enumerate(manifest['target_names']):
                                known=bool(original and changed and original['mask'][h]and changed['mask'][h]);expected_delta=float(changed['values'][h]-original['values'][h])if known else None
                                actual_delta=float(predictions[panel]['branch'][i,j,h]-factual['branch'][i,j,h])
                                edit_expectations.append(dict(panel=panel,root=i,card=str(arrays['source_cards'][i]),role=role,head=name,expected_analytical_known=known,
                                    expected_analytical_delta=expected_delta,learned_delta=actual_delta,response_abs_error=abs(actual_delta-expected_delta)if known else None,label_scope='Synthetic typed-reference response, not a native counterfactual label.'))
                write_new(out/f's{seed}-reference-comparison.json',dict(factual_examples=examples,edited_response_expectations=edit_expectations,analytical_primary_native_metrics=reference_primary,
                    learned_primary_native_metrics=seedresults['factual-replay']['native_evaluation']['primary'],semantic_validated=False))
                seedresults['typed_reference_comparison']=dict(path=str((out/f's{seed}-reference-comparison.json').resolve()),factual_examples=len(examples),edited_response_examples=len(edit_expectations),analytical_primary_native_metrics=reference_primary,
                    learned_primary_native_metrics=seedresults['factual-replay']['native_evaluation']['primary'],semantic_validated=False)
                twin_gaps={k:float(abs(predictions['coherent-intent-swap'][k]-factual[k][twins]).max())for k in('source','branch')};require(max(twin_gaps.values())<=CONFIG['replay_atol'],'intent-swap twin prediction mismatch')
                after=F.state_hash({k:v.detach().numpy()for k,v in model.state_dict().items()});require(before==after,'frozen checkpoint weights changed');weights[str(seed)]=dict(before=before,after=after,unchanged=True);seedresults['coherent_twin_parity']=twin_gaps;results[str(seed)]=seedresults
            require(counts['neural_forwards']==33,'all33 fixed diagnostic forwards required');require(tensorpins=={k:F.sha_array(arrays[k])for k in tensorpins},'native labels/masks mutated')
            for p in frozen['pins']:require(pin(p['path'])==p,'input/source bytes changed during diagnostic')
            result=dict(schema=SCHEMA,status='completed',config=CONFIG,counts=counts,replays=replays,weights=weights,results=results,typed_reference=refscore,mutation_audit=mutation_audit,public_probe_coordinates={p:probe_cache[p][3]for p in PUBLIC_PANELS},true_label_hashes=tensorpins,semantic_validated=False,
                interpretation='Consumed/discovery-exposed cohort only. Synthetic one-coordinate/IR responses are not native counterfactual labels. Rneutral fixed-weight splice is an architectural diagnostic, not a trained correction or fresh transfer result.')
            write_new(out/'result.json',F.json_native(result,np));status='completed'
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
    receipt=dict(schema=SCHEMA,status=status,error=error,active_seconds=time.monotonic()-started,counts=counts,guard=guard.receipt()if guard else None,source=pin(__file__),plan=pin(plan_path),semantic_validated=False,
        accounting='Parent allocation/ledger is authoritative. Failure retains full reserved exposure; journal is a known prefix, not successful completion. No automatic retry.')
    write_new(out/'receipt.json',receipt)
    return receipt


def execute(spec_path,plan_path,out):
    """Canonical budget lease; reservations precede strict input/science checks."""
    A=importlib.import_module('sealed_budget');owner=A.Budget(spec_path)
    argv=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
    with owner.lease()as run:
        started=time.monotonic();receipt=None;error=None
        try:
            # Route from already sealed metadata; never hash/open the plan
            # argument before the durable stage reservation exists.
            expected_plan=owner.frozen.get(str(Path(plan_path).resolve()))
            run.begin('diagnose',argv=argv,guard=owner.spec['guard'],inputs=[]if expected_plan is None else[expected_plan])
            require(expected_plan is not None and pin(plan_path)==expected_plan,'diagnostic plan must match a frozen budget input')
            descriptor=owner.spec['stages']['diagnose'];reserve=descriptor['reservation'];expected=descriptor['expected']
            require(reserve['seconds']==15. and reserve['neural_forwards']==33 and all(reserve[k]==0 for k in reserve if k not in('seconds','neural_forwards'))and expected['neural_forwards']==33,'exact zero-training33-forward allocation required')
            require(descriptor['outputs']==[str(Path(out).resolve())]and owner.spec['guard']==dict(cpu_workers=1,rss_bytes=1073741824),'exact diagnostic output/guard required')
            receipt=_execute(plan_path,out,run)
        except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
        status='completed'if receipt and receipt['status']=='completed'and error is None else'failed'
        if run.state['pending']is None:raise RuntimeError('budget begin did not reserve diagnostic: '+str(error))
        proofs=[pin(p)for p in sorted(Path(out).rglob('*'))if p.is_file()]if Path(out).exists()else[]
        state=run.finish(status,proofs=proofs,cleanup_verified=True,execution_ended=True,active_seconds=time.monotonic()-started)
        require(status=='completed'and'diagnose'in state['completed'],'diagnostic failed; canonical ledger retains full reservation: '+str(error or(receipt or{}).get('error')))
        return dict(receipt=receipt,authoritative_accounting=state)


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--describe',action='store_true');mode.add_argument('--prepare',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--sealed-plan',type=Path);parser.add_argument('--fit-dir',type=Path);parser.add_argument('--plan',type=Path);parser.add_argument('--out',type=Path);parser.add_argument('--spec',type=Path);a=parser.parse_args()
    if a.describe:print(json.dumps(describe(),indent=2));return
    if a.prepare:
        require(all((a.sealed_plan,a.fit_dir,a.plan)),'prepare needs sealed-plan,fit-dir,plan');prepare(a.sealed_plan,a.fit_dir,a.plan);print(json.dumps(pin(a.plan)));return
    require(a.spec and a.plan and a.out,'execute needs spec/plan/out');print(json.dumps(execute(a.spec,a.plan,a.out)))


if __name__=='__main__':main()
