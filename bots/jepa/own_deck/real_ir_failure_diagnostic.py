"""Saved-output discovery only. Import/diagnose are stdlib; worker receives guarded NumPy.

No model, converter, reference interpreter, engine, fit or forward is called.
The ROOT owner writes the returned JSON under its durable ten-second stage.
"""
import hashlib
import json
import math
from pathlib import Path

SEEDS = (17, 29, 43)
ARMS = ('new-full', 'old-late-fusion', 'new-printed-only')


def require(ok, message):
    if not ok: raise ValueError(message)


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value), 'finite saved number required')
    return float(value)


def mean(values): return sum(values)/len(values) if values else None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def summary(rows, prediction='prediction'):
    known = [r for r in rows if r.get(prediction) is not None]
    nonzero = [r for r in known if r['truth'] != 0.]
    healthy = [r for r in known if r['healthy_heal']]
    return dict(coordinates=len(known), roots=len({r['root'] for r in known}),
        programs=len({r['source_card'] for r in known}),
        mae=mean([abs(r[prediction]-r['truth']) for r in known]),
        nonzero_sign_accuracy=mean([float(r[prediction]*r['truth'] > 0.) for r in nonzero]),
        healthy_count=len(healthy), healthy_max_abs=max((abs(r[prediction]) for r in healthy), default=None))


def tables(rows):
    result = {}
    for field in ('family', 'role', 'healthy_heal', 'amount', 'damage', 'hp',
                  'train_op_amount_seen', 'train_op_targetkind_seen', 'train_joint_seen'):
        groups = {}
        for row in rows: groups.setdefault(str(row[field]), []).append(row)
        result[field] = {k: summary(v) for k, v in sorted(groups.items())}
    return result


def diagnose(plan, manifest, fit_result, *, saved_predictions=None, saved_labels=None, feature_inputs=None):
    """Pure JSON/list arithmetic; no I/O. Optional predictions are FINAL saved values.

    saved_labels is {targets, primary_target_mask}, copied from the frozen dataset.
    Unobserved labels never enter means. Without it, all-role p is descriptive only.
    """
    meta = manifest['root_metadata']; public = manifest['public_before_records']
    programs = manifest['canonical_programs']; split = manifest['split']
    train = set(split['train']); held = set(split['held'])
    require(not train & held and train | held == set(range(len(meta))), 'complete disjoint saved split required')
    require(len(plan['worlds']) == len(meta) == len(public), 'saved root inventories differ')
    reference = fit_result['baseline_evaluations']['deterministic-reference']
    train_rows = reference['train']['endpoints']

    def enrich(row):
        i, q = row['root'], row['candidate']; m, p = meta[i], public[i][q]
        require(p['is_intended'] is True and p['known']['damage'] is True and p['known']['hp'] is True,
                'only known actual intended endpoints may be diagnosed')
        program = programs[m['program_index']]; selector = program['selector']
        op, amount = m['operator'], finite(m['amount'])
        require(op == program['effect']['operator'] and amount == finite(program['effect']['amount']['value']),
                'public program metadata differs from saved source')
        if saved_labels is not None:
            y, mask=saved_labels['targets'][i][q],saved_labels['primary_target_mask'][i][q]
            require(mask == [1.,1.] and y[0] == 1. and finite(y[1]) == finite(row['truth']),
                    'diagnosed endpoint must be native-known, committed/eligible and match saved truth')
        value = dict(root=i, candidate=q, source_card=m['source_card'], operator=op, amount=amount,
            selector=selector, family=op+'|'+json.dumps(selector, sort_keys=True, separators=(',', ':')),
            targetkind='base' if p['is_base'] else 'leader-unit' if p['is_leader'] else 'unit',
            role=p['owner']+'|'+p['zone'], zone=p['zone'], owner=p['owner'], domain=row['domain'],
            damage=finite(p['damage']), hp=finite(p['hp']), healthy_heal=op == 'heal' and p['damage'] == 0,
            truth=finite(row['truth']), prediction=finite(row['prediction']),
            source_printed_profile_sha256=digest(manifest['source_printed_profiles'][m['program_index']]))
        if feature_inputs is not None:
            index=feature_inputs['program_indices'][i]; c=feature_inputs['candidate_features'][i][q]
            require(index == m['program_index'] and c[12] == p['damage'] and c[14] == p['hp'] and
                    c[13] == c[15] == c[16] == 1., 'actual saved endpoint inputs differ from public metadata')
            signature=[feature_inputs['program_features'][index][10:13],c[12:14]+c[15:16],
                       feature_inputs['source_printed_features'][index],c[16]]
            value['new_endpoint_input_except_hp_sha256']=digest(signature)
        return value

    observed_train = [enrich(r) for r in train_rows]
    require(all(r['root'] in train for r in observed_train), 'TRAIN support may not read HELD outcomes')
    op_amount = {(r['operator'], r['amount']) for r in observed_train}
    op_kind = {(r['operator'], r['targetkind']) for r in observed_train}
    joint = {(r['operator'], r['amount'], r['damage'], r['hp']) for r in observed_train}
    all_rows = []; panels = {}; probability_rows = []; paired = []
    sources = [(f's{s}:{a}', fit_result['results'][f's{s}:{a}']['evaluations']['300']) for s in SEEDS for a in ARMS]
    sources += list(fit_result['baseline_evaluations'].items())
    for name, evaluation in sources:
        panel = {}
        for partition in ('train', 'held'):
            rows = []
            for original in evaluation[partition]['endpoints']:
                row = enrich(original); i, q = row['root'], row['candidate']
                require(i in (train if partition == 'train' else held), 'endpoint partition differs')
                row.update(method=name, partition=partition,
                    train_op_amount_seen=(row['operator'], row['amount']) in op_amount,
                    train_op_targetkind_seen=(row['operator'], row['targetkind']) in op_kind,
                    train_joint_seen=(row['operator'], row['amount'], row['damage'], row['hp']) in joint,
                    eligibility_probability=None, conditional_raw=None, oracle_eligibility_prediction=None)
                if saved_predictions is not None and name in saved_predictions:
                    p, delta = map(finite, saved_predictions[name][i][q])
                    require(0. <= p <= 1. and abs(delta-row['prediction']) <= 1e-6, 'saved JSON/NPZ prediction mismatch')
                    row['eligibility_probability'] = p
                    if p > 0.:
                        raw = delta/p; require(math.isfinite(raw), 'conditional division overflow')
                        row.update(conditional_raw=raw, oracle_eligibility_prediction=raw,
                            gate_sign_preserved=(raw == 0. and delta == 0.) or raw*delta > 0.,
                            division_near_zero=p < 1e-6)
                        require(row['gate_sign_preserved'], 'positive sigmoid cannot change the signed effect')
                    else: row['conditional_unavailable_reason'] = 'p=0; no imputation'
                rows.append(row); all_rows.append(row)
            panel[partition] = dict(routed=summary(rows), oracle_eligibility=summary(rows, 'oracle_eligibility_prediction'),
                undefined_conditional=sum(r['conditional_raw'] is None for r in rows), slices=tables(rows),
                saved_eligibility=evaluation[partition]['eligibility'])
            for a in rows:
                for b in rows:
                    if a['zone'] != 'space' or b['zone'] != 'base': continue
                    keys = ('source_card', 'operator', 'amount', 'damage', 'source_printed_profile_sha256')
                    if all(a[k] == b[k] for k in keys) and a['hp'] != b['hp']:
                        same = (a.get('new_endpoint_input_except_hp_sha256') == b.get('new_endpoint_input_except_hp_sha256')) if feature_inputs is not None else None
                        require(same is not False, 'matched pair changes another NEW endpoint input')
                        paired.append(dict(method=name, partition=partition, space_root=a['root'], base_root=b['root'],
                            source_card=a['source_card'], operator=a['operator'], amount=a['amount'], damage=a['damage'],
                            space_hp=a['hp'], base_hp=b['hp'], space_prediction=a['prediction'], base_prediction=b['prediction'],
                            space_conditional_raw=a['conditional_raw'], base_conditional_raw=b['conditional_raw'],
                            space_truth=a['truth'], base_truth=b['truth'], saved_endpoint_inputs_except_hp_equal=same))
        panels[name] = panel
        if saved_predictions is not None and name in saved_predictions:
            for i, candidates in enumerate(public):
                for q, candidate in enumerate(candidates):
                    p = finite(saved_predictions[name][i][q][0]); require(0 <= p <= 1, 'saved probability outside[0,1]')
                    known = saved_labels is not None and bool(saved_labels['primary_target_mask'][i][q][0])
                    truth = finite(saved_labels['targets'][i][q][0]) if known else None
                    require(truth in (None,0.,1.), 'known native eligibility must be binary')
                    probability_rows.append(dict(method=name, root=i, candidate=q, role=candidate['owner']+'|'+candidate['zone'],
                        partition='train' if i in train else 'held', intended=candidate['is_intended'], probability=p,
                        native_known=known, native_truth=truth, error=abs(p-truth) if known else None))
    failures = {}
    for seed in SEEDS:
        d = fit_result['decisions']['per_seed'][str(seed)]
        metrics = fit_result['results'][f's{seed}:new-full']['evaluations']['300']['held']
        failures[str(seed)] = dict(saved_decision=d, failed_flags=[k for k,v in d.items() if v is False and k != 'eligibility_discrimination_qualified'],
            mae_violations={k:v for k,v in metrics['endpoint_mae'].items() if v is None or v > .25},
            thresholds=dict(endpoint_mae_max=.25, nonzero_sign_min=.95, healthy_heal_max_abs=.1,
                            positive_recall_descriptive_min=.95, old_pooled_mae_allowance=.05), saved_metrics=metrics)
    probability_groups={}
    for r in probability_rows:
        key=r['method']+'|'+r['partition']+'|'+r['role'];probability_groups.setdefault(key,[]).append(r)
    eligibility_slices={k:dict(coordinates=len(v),native_known=sum(r['native_known'] for r in v),
        mean_probability=mean([r['probability'] for r in v]),
        native_known_mae=mean([r['error'] for r in v if r['native_known']]),
        positive_count=sum(r['native_truth']==1. for r in v),negative_count=sum(r['native_truth']==0. for r in v))
        for k,v in probability_groups.items()}
    return dict(schema='jepa-real-ir-failure-diagnostic/1', discovery_only=True, semantic_validated=False,
        counts=dict(neural_forwards=0, backwards=0, optimizer_updates=0, native_applies=0, numerical_fits=0, paid_jobs=0),
        support=dict(train_roots=len(train), held_roots=len(held), train_known_endpoints=len(observed_train),
            op_amount=[list(x) for x in sorted(op_amount)], op_targetkind=[list(x) for x in sorted(op_kind)],
            joint=[list(x) for x in sorted(joint)], scope='Exact tuples from co-known TRAIN endpoints only; never held fitted statistics.'),
        panels=panels, endpoint_rows=all_rows, eligibility_rows=probability_rows,
        eligibility_role_slices=eligibility_slices,space_base_pairs=paired,
        gate_failures=failures, saved_global_decisions=fit_result['decisions'],
        limitations=['All seven cards and both held cards are now exposed discovery examples; no new generalization qualification.',
            'Coordinates, seeds and repeated matched pairs are not independent samples.',
            'delta/p is an unfitted oracle-eligibility rerouting of saved outputs, not a new neural prediction. Positive p cannot repair a wrong sign.',
            'For NEW only, matched same-source space/base endpoint branches differ only in target HP: damage/knownness, operator/amount, source S10 and intended equality are fixed. Eligibility pathways and public roles differ.',
            'These pairs reveal an HP-binding opportunity; no source-printed S10 intervention or causal retraining claim was performed.',
            'OLD uses a different late-fusion graph and additional endpoint-visible fields; its pair is descriptive, not an isolated HP intervention.'])


def worker(np, root):
    """ROOT calls ONLY after durable begin inside its active time/RSS guard."""
    root = Path(root)
    paths = dict(plan=root/'metadata-1/native-plan.json', manifest=root/'prep-1/manifest.json', result=root/'fit-1/result.json')
    values = {k:json.loads(p.read_text()) for k,p in paths.items()}; predictions = {}
    for seed in SEEDS:
        for arm in ARMS:
            name=f's{seed}:{arm}'; path=root/'fit-1'/f's{seed}-{arm}-step300-predictions.npz'; paths[name]=path
            with np.load(path, allow_pickle=False) as handle:
                require(handle['predictions'].shape == (56,6,2), 'exact final saved prediction ABI required')
                predictions[name]=handle['predictions'].tolist()
    path=root/'prep-1/dataset.npz'; paths['labels']=path
    with np.load(path, allow_pickle=False) as handle:
        require(all(handle[k].shape == (56,6,2) for k in ('targets','primary_target_mask')),
                'exact frozen native label/mask ABI required')
        labels={k:handle[k].tolist() for k in ('targets','primary_target_mask')}
        features={k:handle[k].tolist() for k in ('program_features','program_indices','candidate_features','source_printed_features')}
    result=diagnose(values['plan'],values['manifest'],values['result'],saved_predictions=predictions,
                    saved_labels=labels,feature_inputs=features)
    def pin(path):
        raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    result['input_pins']={k:pin(p) for k,p in paths.items()};result['source']=pin(Path(__file__))
    return result
