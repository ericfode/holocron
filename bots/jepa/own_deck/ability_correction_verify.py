"""Independent saved-output checks only; execution requires a new sealed3s stage.

No engine, model, fit, training, export or correction scorer is executed. Native
membership is rederived by exact action.card equality at the observed prompt.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
EXP=HERE.parents[3]/'experiments'
ROOT=EXP/'ability-correction-v1';DIAG=EXP/'ability-diagnostic-v1';OLD=EXP/'semantic-discrimination-repair-v1'
SEEDS=(17,29,43);VIEWS=('original','neutral_all_heads','corrected');TOL=1e-6
ROLES=('source','own_helper','opponent_helper','anchor_a','anchor_b','auxiliary','own_base','opponent_base')


def require(ok,message):
    if not ok:raise ValueError(message)
def pin(path):
    p=Path(path).resolve();raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write_new(path,value):
    raw=encoded(value)+b'\n'
    with Path(path).open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
def read(path):return json.loads(Path(path).read_text())
def npz(np,path):
    with np.load(path,allow_pickle=False)as p:return{k:p[k].copy()for k in p.files}
def state_hash(values):
    hashes={k:hashlib.sha256(str(v.dtype).encode()+str(v.shape).encode()+v.tobytes()).hexdigest()for k,v in values.items()}
    return hashlib.sha256(encoded(hashes)).hexdigest()
def paths():
    files=[ROOT/'native-attempt-1/native-receipt.json',ROOT/'native-attempt-1/native-transitions.jsonl',ROOT/'prep-1/dataset.npz',ROOT/'prep-1/dataset.manifest.json',ROOT/'correction-1/result.json',ROOT/'campaign-ledger.jsonl',ROOT/'experiment-closure.json',DIAG/'campaign-ledger.jsonl',DIAG/'experiment-closure.json']
    return files+[OLD/f'fit-1/s{s}-learned-full-checkpoint.npz'for s in SEEDS]+[ROOT/f'correction-1/s{s}-{v}-predictions.npz'for s in SEEDS for v in VIEWS]


def metric(pred,truth,mask,roles,pairs):
    rows=[];positive=negative=tp=tn=0
    for i in range(len(pred)):
        known=[j for j in roles if mask[i][j]]
        if known:rows.append(sum(abs(pred[i][j]-truth[i][j])for j in known)/len(known))
        for j in known:
            require(truth[i][j]in(0,1),'known eligibility must be binary')
            if truth[i][j]==1:positive+=1;tp+=pred[i][j]>=.5
            else:negative+=1;tn+=pred[i][j]<.5
    sensitivity=tp/positive if positive else None;specificity=tn/negative if negative else None;deltas=[];flips=[];pair_rows=[]
    for pair in pairs:
        a,b=pair['left_root'],pair['right_root'];known=[j for j in roles if mask[a][j]and mask[b][j]];ds=[abs(pred[a][j]-pred[b][j])for j in known]
        if ds:deltas.append(sum(ds)/len(ds));flips.append(sum((pred[a][j]>=.5)!=(pred[b][j]>=.5)for j in known)/len(known))
        pair_rows.append(dict(known=len(ds),max_abs_difference=max(ds)if ds else None))
    eligibility=dict(known=positive+negative,known_roots=len(rows),positive=positive,negative=negative,mae=sum(rows)/len(rows)if rows else None,balanced_accuracy=(sensitivity+specificity)/2 if positive and negative else None,sensitivity=sensitivity,specificity=specificity)
    invariance=dict(mean_abs_difference=sum(deltas)/len(deltas)if deltas else None,max_abs_difference=max((r['max_abs_difference']for r in pair_rows if r['known']),default=None),mean_threshold_flip_fraction=sum(flips)/len(flips)if flips else None,passed=len(deltas)==4 and all(r['max_abs_difference']<=TOL for r in pair_rows if r['known']))
    return eligibility,invariance


def journal_check(raw,records,check):
    check(records[0]['schema']=='jepa-ability-correction-apply-journal/1'and records[0]['maxApplyCalls']==32,'native header')
    check(raw['schema']=='jepa-ability-correction-native/1'and raw['collectionComplete']is True and records[0]['planSha256']==raw['collectionPlanSha256'],'completed native source/plan')
    before=[r for r in records[1:]if r.get('phase')=='beforeApply'];after=[r for r in records[1:]if r.get('phase')=='afterApply'];ends=[r['case']for r in records[1:]if r.get('phase')=='contextComplete']
    check(raw['applyCalls']==20 and [r['applyCall']for r in before]==[r['applyCall']for r in after]==list(range(1,21)),'20 paired native calls')
    check(ends==raw['cases']and len(ends)==8,'eight exact context completions')
    check([r.get('phase')for r in records[1:]if r.get('phase')!='contextComplete']==['beforeApply','afterApply']*20,'native chronology without errors')
    steps=[s for case in raw['cases']for s in case['steps']]
    check(len(steps)==20,'20 captured native steps')
    for a,b,s in zip(before,after,steps):check(a['before']==s['before']and a['offeredAction']==s['action']and b['after']==s['after'],'native action/state binding')


def closed_counts(rows,check):
    previous='0'*64;counts=dict(neural_forwards=0,native_applies=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
    for i,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'}
        check(row['schema']=='jepa-sealed-budget-journal/1'and row['sequence']==i and row['previous_sha256']==previous and hashlib.sha256(encoded(body)).hexdigest()==row['record_sha256'],'closed chain')
        previous=row['record_sha256']
        if row['event']=='finish':
            check(row['data']['status']=='completed','closed successful stage')
            for k in counts:counts[k]+=row['data']['charged'][k]
    check(rows[-1]['event']=='finish','closed terminal record');return counts


def verify(np,allowed):
    checks=0;failures=[]
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not bool(ok):failures.append(label)
    def equal(actual,expected,label):
        if isinstance(expected,(float,int))and not isinstance(expected,bool):check(actual is not None and abs(float(actual)-expected)<=1e-7,label)
        else:check(actual==expected,label)
    for p in paths():require(allowed.get(str(p.resolve()))==pin(p),'missing/changed frozen verifier input: '+str(p))
    raw=read(paths()[0]);records=[json.loads(v)for v in paths()[1].read_text().splitlines()];journal_check(raw,records,check)
    arrays=npz(np,paths()[2]);manifest=read(paths()[3]);saved=read(paths()[4]);closure=read(paths()[6]);h=manifest['target_names'].index('target_allowed')
    check(tuple(manifest['candidate_order'])==ROLES and len(raw['cases'])==8,'fixed8 roles/roots')
    check(arrays['targets'].shape==arrays['target_mask'].shape==(8,8,7),'target ABI')
    check(arrays['source_cards'].astype(str).tolist()==['IBH_104']*8,'exact exposed source identities')
    pairs=manifest['intent_pairs'];check([(p['left_root'],p['right_root'])for p in pairs]==[(0,1),(2,3),(4,5),(6,7)],'four fixed pairs')
    truth=arrays['targets'][...,h].tolist();mask=arrays['target_mask'][...,h].tolist();scopes=dict(anchors=[3,4],all_known=list(range(8)),non_source=list(range(1,8)),anchor_a=[3],anchor_b=[4])
    for i,case in enumerate(raw['cases']):
        offered=case['targetPrompt']['offeredActions'];check(case['targetPrompt']['decision']=='AbilityTarget','actual native target prompt')
        check(case['declared_intent']['id']==case['refs'][ROLES[int(arrays['selected_candidate_indices'][i])]],'native/dataset intended identity')
        for j,role in enumerate(ROLES):check(mask[i][j]==1 and truth[i][j]==float(any(a.get('card')==case['refs'][role]for a in offered)),'native membership '+str((i,role)))
    output={};primary=[]
    for seed in SEEDS:
        old=npz(np,OLD/f'fit-1/s{seed}-learned-full-checkpoint.npz');weight_hash=state_hash(old);record=saved['results'][str(seed)]
        check(all(np.isfinite(v).all()for v in old.values()),'finite saved weights');check(weight_hash==record['state_sha256_before']==record['state_sha256_after'],'exact frozen checkpoint hash')
        check(record['checkpoint']==pin(OLD/f'fit-1/s{seed}-learned-full-checkpoint.npz'),'exact checkpoint pin')
        views={v:npz(np,ROOT/f'correction-1/s{seed}-{v}-predictions.npz')for v in VIEWS};metrics={}
        for v,p in views.items():
            check(p['source'].shape==(8,9)and p['branch'].shape==(8,8,7),'saved prediction ABI');check(all(np.isfinite(p[k]).all()for k in('source','branch','card_vectors')),'finite saved predictions')
            metrics[v]={}
            for scope,roles in scopes.items():
                e,inv=metric(p['branch'][...,h].tolist(),truth,mask,roles,pairs);metrics[v][scope]=dict(eligibility=e,invariance=inv)
                if scope not in('anchor_a','anchor_b'):
                    for k,value in e.items():equal(record['views'][v]['eligibility'][scope][k],value,'saved eligibility '+str((seed,v,scope,k)))
                    for k,value in inv.items():equal(record['views'][v]['intent_invariance'][scope][k],value,'saved invariance '+str((seed,v,scope,k)))
        o,n,c=(views[v]for v in VIEWS);controls=[np.array_equal(c['source'],o['source']),np.array_equal(c['branch'][...,1:],o['branch'][...,1:]),np.array_equal(c['branch'][...,h],n['branch'][...,h])]
        check(h==0 and all(controls),'15 endpoint heads bit-identical and eligibility equals N');check(np.array_equal(o['card_vectors'],n['card_vectors'])and np.array_equal(o['card_vectors'],c['card_vectors']),'frozen saved card vectors')
        orig=metrics['original']['anchors']['eligibility'];corr=metrics['corrected']['anchors'];supported=orig['balanced_accuracy']is not None and corr['eligibility']['balanced_accuracy']is not None
        gates=dict(intent_invariant=corr['invariance']['passed'],mae_noninferior=corr['eligibility']['mae']<=orig['mae']+TOL,balanced_accuracy_supported=supported,balanced_accuracy_noninferior=supported and corr['eligibility']['balanced_accuracy']>=orig['balanced_accuracy']-TOL)
        gates['passed']=all(controls)and all(gates.values())
        for k,value in gates.items():equal(record['primary'][k],value,'saved gate '+str((seed,k)))
        primary.append(gates['passed']);output[str(seed)]=dict(metrics=metrics,primary=gates,checkpoint_sha256=weight_hash)
    total={k:0 for k in ('neural_forwards','native_applies','optimizer_updates','numerical_fits','paid_jobs','paid_spend_usd')}
    for root in(DIAG,ROOT):
        rows=[json.loads(v)for v in(root/'campaign-ledger.jsonl').read_text().splitlines()];counts=closed_counts(rows,check);closed=read(root/'experiment-closure.json');check(closed['journal']==pin(root/'campaign-ledger.jsonl')and closed['final_chain']==rows[-1]['record_sha256'],'closure journal pin')
        for k,value in counts.items():total[k]+=value;check(value==closed['new_charged'][k],'closure counts')
    check(total==dict(neural_forwards=39,native_applies=20,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.),'combined completed39NN/20native/zero learning')
    check(all(primary)==saved['all_seed_primary_passed']==closure['primary_gate_passed'],'aggregate negative/positive gate preserved')
    return dict(schema='jepa-ability-correction-independent-verification/1',status='PASS'if not failures else'FAIL',checks=checks,mismatches=failures,seed_results=output,closed_campaign_totals=total,semantic_validated=False,scope='Saved output/data bookkeeping only; no new calls, fit, transfer or semantic qualification.')


def execute(args):
    A=importlib.import_module('sealed_budget');budget=A.Budget(args.spec)
    with budget.lease()as run:
        status='failed';error=None;guard=None;created=False;receipt=args.out.parent/(args.out.name+'-stage-receipt.json');allowed=dict(budget.frozen,**run.state['proofs'])
        try:
            run.begin('verify',argv=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]],guard=budget.spec['guard'],inputs=[allowed[str(p.resolve())]for p in paths()if str(p.resolve())in allowed])
            d=budget.spec['stages']['verify'];require(d['reservation']['seconds']==3 and all(v==0 for k,v in d['reservation'].items()if k!='seconds')and d['outputs']==[str(args.out.resolve()),str(receipt.resolve())],'exact3s zero-science output contract')
            require(budget.spec['guard']==dict(cpu_workers=1,rss_bytes=1073741824),'audited fixed Guard contract');E=importlib.import_module('effect_identifiability_fit');guard=E.Guard(run.remaining_seconds());args.out.mkdir(parents=True,exist_ok=False);created=True
            with guard:
                import numpy as np
                result=verify(np,allowed);write_new(args.out/'result.json',result);require(result['status']=='PASS','saved evidence mismatches; full FAIL result preserved')
            status='completed'
        except BaseException as exc:
            if run.state['pending']is None:raise
            error=dict(type=type(exc).__name__,message=str(exc))
            if created and not(args.out/'result.json').exists():write_new(args.out/'result.json',dict(status='FAIL',error=error,semantic_validated=False,scope='Saved verifier stopped; no rerun or scientific calls.'))
        proofs=[pin(p)for p in sorted(args.out.rglob('*'))if p.is_file()]if created else[]
        value=dict(status=status,error=error,guard=guard.receipt()if guard else None,source=pin(__file__),proofs=proofs,science_counters=0,semantic_validated=False,authority='Shared ledger controls final status; scientific gate may remain negative when verification passes.')
        try:write_new(receipt,value);proofs.append(pin(receipt))
        except BaseException as exc:status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        finished=run.finish(status,proofs=proofs,cleanup_verified=True,execution_ended=True);require(status=='completed'and'verify'in finished['completed'],'verification failed; no retry or prior charge changes');return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();print(json.dumps(execute(args),indent=2))
if __name__=='__main__':main()
