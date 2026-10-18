"""TRAIN-only saved magnitude diagnosis; no model, converter, engine or fit.

diagnose consumes artificial/prefiltered JSON lists. ROOT calls worker(np,
prior_root,hp_root) only inside its durable ten-second guard. Container byte
hashes cover immutable files; every numerical selection is original TRAIN0..39.
"""
import hashlib
import json
import math
from pathlib import Path

SEEDS=(17,29,43)
ARMS=('baseline','effect-hp-invariant')


def require(ok,message):
    if not ok:raise ValueError(message)


def number(value):
    require(type(value)in(int,float)and math.isfinite(value),'finite saved number required')
    return float(value)


def mean(values):return sum(values)/len(values)if values else None


def summary(rows,field):
    points=[r for r in rows if r[field]is not None];nz=[r for r in points if r['truth']!=0.]
    return dict(endpoints=len(points),roots=len({r['root']for r in points}),programs=len({r['program_index']for r in points}),
        truth_mean=mean([r['truth']for r in points]),prediction_mean=mean([r[field]for r in points]),
        signed_residual_mean=mean([r[field]-r['truth']for r in points]),
        magnitude_residual_mean=mean([abs(r[field])-abs(r['truth'])for r in points]),
        mae=mean([abs(r[field]-r['truth'])for r in points]),
        nonzero_sign_accuracy=mean([float(r[field]*r['truth']>0.)for r in nz]))


def diagnose(a,metadata,programs,printed_profiles,predictions,weights,scales):
    """Pure stdlib arithmetic over TRAIN lists only; never fit conditional means."""
    n=len(metadata);require(0<n<=40 and len(a['targets'])==n,'only original TRAIN rows may enter diagnosis')
    require(all(m['root']==i and m['partition']=='train'for i,m in enumerate(metadata)),'strict TRAIN metadata only')
    require(len(programs)==len(a['program_features'])==len(a['source_printed_features'])==len(printed_profiles),
        'TRAIN program banks only, with matching provenance')
    require(scales['program'][12]==3. and scales['candidate'][12]==4. and scales['candidate'][14]==10.,'frozen physics scales differ')
    indices=a['program_indices'];require(set(indices)==set(range(len(programs))),'every bank entry must be present in TRAIN')
    reference_mismatches=[];records=[];binary_counts=[0,0];strata={};root_known=[]
    for i,m in enumerate(metadata):
        k=indices[i];p=a['program_features'][k];program=programs[k];op=m['operator'];amount=number(m['amount'])
        require(op==program['effect']['operator']and amount==number(program['effect']['amount']['value'])==p[12]and
            p[10:12]==([1.,0.]if op=='damage'else[0.,1.]),'semantic literal/operator input differs from public source')
        known=sum(bool(mask[0])for mask in a['target_mask'][i]);root_known.append(known)
        for q,(truth,mask,ref,c) in enumerate(zip(a['targets'][i],a['target_mask'][i],a['baseline_predictions'][i],a['candidate_features'][i])):
            for head in range(2):
                if mask[head]and number(truth[head])!=number(ref[head]):reference_mismatches.append([i,q,head])
            if mask[0]:
                require(truth[0]in(0.,1.),'known native eligibility must be binary');binary_counts[int(truth[0])]+=1
            if not mask[1]:continue
            require(truth[0]==1. and c[16]==1. and c[13]==c[15]==1.,'only native-known committed intended endpoints')
            damage,hp=number(c[12]),number(c[14]);native=number(truth[1]);signed=amount if op=='damage'else-amount
            clipped=amount if op=='damage'else-min(amount,damage)
            selector=program['selector'];cap=selector['cost_cap'];kind='base'if c[3]else'leader-unit'if c[4]else'unit'
            key=op+'|'+m['intent_domain'];strata[key]=strata.get(key,0)+1
            records.append(dict(root=i,candidate=q,program_index=k,source_card=m['source_card'],operator=op,
                amount=amount,targetkind=kind,domain=m['intent_domain'],owner='self'if c[0]else'opponent',
                arena='ground'if c[5]else'space'if c[6]else'base',damage=damage,hp=hp,
                neural_amount_input=amount/3.,neural_damage_input=damage/4.,neural_hp_input=hp/10.,
                healthy_heal=op=='heal'and damage==0.,cap=cap['value']if cap['present']else'absent',
                family=op+'|'+json.dumps(selector,sort_keys=True,separators=(',',':')),truth=native,
                signed_literal=signed,clipped_literal=clipped,native_minus_signed_literal=native-signed,
                native_minus_clipped_literal=native-clipped,public_candidate=list(c),program_selector_fields=p[:10],
                printed_features=a['source_printed_features'][k]))
    require(binary_counts==weights['class_statistics']['class_counts']and strata==weights['stratum_statistics']['counts'],
        'observed TRAIN support differs from frozen statistics')
    total=sum(binary_counts);endpoints=len(records)
    weight_checks=dict(binary_weights_equal=all(abs(w-total/(2*v))<1e-12 for w,v in zip(weights['class_statistics']['weights'],binary_counts)),
        stratum_weights_equal=all(abs(weights['stratum_statistics']['weights'][k]-endpoints/(len(strata)*v))<1e-12 for k,v in strata.items()))
    panels={};all_rows=[];contrasts=[]
    for method,prediction in predictions.items():
        require(len(prediction)==n,'prediction list must be TRAIN-sliced before diagnosis')
        rows=[]
        for original in records:
            row=dict(original);i,q=row['root'],row['candidate'];prob,delta=map(number,prediction[i][q])
            require(0<=prob<=1,'saved eligibility probability outside[0,1]')
            raw=delta/prob if prob>0 else None
            require(raw is None or math.isfinite(raw),'conditional division overflow')
            row.update(method=method,eligibility_probability=prob,routed=delta,raw=raw,
                conditional_undefined=prob==0.,near_zero_probability=0<prob<1e-6,
                endpoint_loss_coordinate_weight=.5*weights['stratum_statistics']['weights'][row['operator']+'|'+row['domain']]/endpoints)
            rows.append(row);all_rows.append(row)
        for row in rows:
            row['operator_amount']=row['operator']+'|'+str(row['amount'])
            row['operator_amount_target_health']='|'.join(str(row[k])for k in('operator','amount','targetkind','healthy_heal'))
        groups={}
        for field in('operator','amount','targetkind','domain','owner','arena','healthy_heal','cap','damage','hp','family','source_card',
                     'operator_amount','operator_amount_target_health'):
            bucket={}
            for row in rows:bucket.setdefault(str(row[field]),[]).append(row)
            groups[field]={k:dict(raw=summary(v,'raw'),routed=summary(v,'routed'))for k,v in sorted(bucket.items())}
        panels[method]=dict(raw=summary(rows,'raw'),routed=summary(rows,'routed'),slices=groups,
            undefined_conditional=sum(r['conditional_undefined']for r in rows))
        for x in rows:
            for y in rows:
                if x['root']>=y['root']or x['operator']!=y['operator']or x['amount']==y['amount']:continue
                if x['public_candidate']!=y['public_candidate']:continue
                contrasts.append(dict(method=method,roots=[x['root'],y['root']],operator=x['operator'],
                    amounts=[x['amount'],y['amount']],native_difference=y['truth']-x['truth'],
                    routed_difference=y['routed']-x['routed'],raw_difference=y['raw']-x['raw']if x['raw']is not None and y['raw']is not None else None,
                    selector_fields_equal=x['program_selector_fields']==y['program_selector_fields'],
                    source_printed_equal=x['printed_features']==y['printed_features'],
                    scope='Identical full public candidate state; different source programs/printed profiles or selectors may still confound amount.'))
    support={}
    for op in sorted({r['operator']for r in records}):
        subset=[r for r in records if r['operator']==op]
        support[op]={field:sorted({r[field]for r in subset})for field in('amount','truth','damage','hp','targetkind')}
        support[op]['operator_amount_program_counts']={str(v):len({r['program_index']for r in subset if r['amount']==v})for v in support[op]['amount']}
    return dict(schema='jepa-real-ir-intent-diagnostic/1',training_only=True,semantic_validated=False,
        counts=dict(neural_forwards=0,backwards=0,optimizer_updates=0,native_applies=0,numerical_fits=0,paid_jobs=0),
        support=dict(roots=n,programs=len(programs),known_eligibility=sum(binary_counts),known_endpoints=endpoints,
            binary_counts=binary_counts,strata=strata,operator_ranges=support),
        scaling_algebra=dict(program_amount_scale=3.,candidate_damage_scale=4.,candidate_hp_scale=10.,
            target_units='Raw physical after-minus-before damage; no target normalization or inverse scaling.',
            output='routed_delta=raw_conditional_output*sigmoid(eligibility)*intended_equality',
            loss='0.5 TRAIN-balanced root-mean BCE +0.5 stratum-weighted raw SmoothL1(beta=1), denominator=knownTRAINendpoints',
            weights=weights,frozen_weight_arithmetic=weight_checks,binary_known_per_root=root_known,
            signed_literal_mismatches=sum(r['native_minus_signed_literal']!=0. for r in records),
            clipped_literal_mismatches=sum(r['native_minus_clipped_literal']!=0. for r in records),
            reference_known_mismatches=reference_mismatches),
        panels=panels,endpoint_rows=all_rows,same_state_amount_contrasts=contrasts,
        limitations=['Original TRAIN only; no held/fresh outcome or support statistic is read into calculations.',
            'Conditional means/residuals are descriptive arithmetic, not a fit or causal diagnosis.',
            'Magnitude differences between semantic amount and native healing can be clipping, not normalization.',
            'Source S10 and selector differences remain potential confounds in cross-source amount contrasts.',
            'delta/p reconstructs a float32 ratio, not a retained raw preactivation; zero p is undefined.',
            'Positive eligibility cannot reverse a conditional sign. Residuals inside TRAIN are not evidence of held extrapolation.',
            'Roots/candidates/seeds are nested observations, not independent new cards or trials.'])


def worker(np,prior_root,hp_root):
    """Call only inside ROOT's active guard; return JSON without writes or ledger I/O."""
    prior_root,hp_root=Path(prior_root),Path(hp_root)
    paths=dict(dataset=prior_root/'prep-1/dataset.npz',manifest=prior_root/'prep-1/manifest.json',
        weights=prior_root/'fit-1/loss-weights.json',contract=prior_root/'fit-1/contract.json')
    manifest=json.loads(paths['manifest'].read_text());metadata=manifest['root_metadata'][:40]
    with np.load(paths['dataset'],allow_pickle=False)as h:
        require(h['train_idx'].tolist()==list(range(40)),'only exact originalTRAIN40 order permitted')
        a={k:h[k][:40].tolist()for k in('targets','target_mask','baseline_predictions','candidate_features','program_indices')}
        bank_indices=sorted(set(a['program_indices']));require(bank_indices==list(range(5)),'only original5TRAIN programs')
        for k in('program_features','source_printed_features'):a[k]=h[k][bank_indices].tolist()
    predictions={}
    for seed in SEEDS:
        for arm in ARMS:
            key=f's{seed}:{arm}';path=hp_root/'fit-1'/f's{seed}-{arm}-step300-predictions.npz';paths[key]=path
            with np.load(path,allow_pickle=False)as h:
                require(h['predictions'].shape==(112,6,2),'exact immutable saved final container required')
                predictions[key]=h['predictions'][:40].tolist()
    weights=json.loads(paths['weights'].read_text());contract=json.loads(paths['contract'].read_text())
    result=diagnose(a,metadata,manifest['canonical_programs'][:5],manifest['source_printed_profiles'][:5],
        predictions,weights,contract['model']['scales'])
    for name in('real_ir_transfer_model.py','real_ir_transfer_fit.py','real_ir_hp_projection_model.py','real_ir_hp_projection_fit.py'):
        paths[name]=Path(__file__).with_name(name)
    def pin(path):
        raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    result['input_pins']={k:pin(p)for k,p in paths.items()};result['source']=pin(Path(__file__))
    result['selection_proof']=dict(original_rows=list(range(40)),program_indices=bank_indices,
        predictions_sliced_before_tolist=True,held_metrics_loaded=False,
        scope='Compressed containers and parsed provenance JSON include other rows; no held/fresh array value enters array-to-list conversion, arithmetic, grouping, or decisions.')
    return result
