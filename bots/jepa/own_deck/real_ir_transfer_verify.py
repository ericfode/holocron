"""Independent saved-output verification for the frozen real-event comparison.

Import is standard-library only. ROOT calls verify(np, root, out) inside its
durable verify reservation and active guard. No model module, training helper,
optimizer, fitted transform, numerical solver, or engine is called. Checkpoint
bytes are audited; this is not a forward-parity proof for saved weights.
"""
import hashlib
import json
import math
import os
from pathlib import Path

SEEDS = (17, 29, 43)
ARMS = ('new-full', 'old-late-fusion', 'new-printed-only')
COUNTS = dict(neural_forwards=2718, backwards=2700, optimizer_updates=2700, numerical_fits=2)
PROGRAM_FIELDS = ('owner_allowed_self', 'owner_allowed_opponent', 'target_unit_allowed',
    'target_leader_unit_allowed', 'target_base_allowed', 'zone_ground_allowed',
    'zone_space_allowed', 'zone_base_allowed', 'cost_cap_present', 'cost_cap',
    'op_damage', 'op_heal', 'amount')
CANDIDATE_FIELDS = ('owner_self', 'owner_opponent', 'is_unit', 'is_base', 'is_leader',
    'zone_ground', 'zone_space', 'zone_base', 'attackable', 'printed_cost',
    'cost_known', 'cost_applicable', 'damage', 'damage_known', 'hp', 'hp_known', 'is_intended')
PRINTED_FIELDS = ('cost', 'cost_known', 'hp', 'hp_known', 'power', 'power_known',
                  'unique', 'is_event', 'is_unit', 'is_base')


def require(ok, message):
    if not ok: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value): return hashlib.sha256(canonical(value)).hexdigest()


def pin(path):
    p = Path(path).resolve(strict=True); raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def load(path): return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def close(actual, expected, path='value', tolerance=1e-6):
    """Compare a saved claim with an independently computed primitive tree."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), 'object keys differ: ' + path)
        for key in expected: close(actual[key], expected[key], path + '.' + key, tolerance)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), 'list length differs: ' + path)
        for i, item in enumerate(expected): close(actual[i], item, path + '[' + str(i) + ']', tolerance)
    elif type(expected) in (int, float):
        require(type(actual) in (int, float) and math.isfinite(actual) and math.isfinite(expected)
                and abs(actual - expected) <= tolerance * max(1., abs(expected)), 'numeric claim differs: ' + path)
    else: require(type(actual) is type(expected) and actual == expected, 'primitive claim differs: ' + path)


def mean(values): return sum(values) / len(values) if values else None


def scores(predictions, labels, masks, metadata, indices):
    """Root-balanced endpoints; positive-only eligibility never has a BA."""
    effects, yes, no, root_error = [], [], [], []
    for i in indices:
        errors = []
        for j in range(len(labels[i])):
            prediction, truth, known = predictions[i][j], labels[i][j], masks[i][j]
            require(all(type(v) in (int, float) and math.isfinite(v) for v in prediction), 'nonfinite saved prediction')
            if known[0]:
                require(truth[0] in (0., 1.) and 0. <= prediction[0] <= 1., 'invalid probability/native membership')
                if truth[0] == 1.: yes.append(float(prediction[0] >= .5))
                else: no.append(float(prediction[0] < .5))
                errors.append(abs(prediction[0] - truth[0]))
            if known[1]:
                m = metadata[i]
                healthy = m['operator'] == 'heal' and m['healthy_intent'] is True
                require(not healthy or truth[1] == 0., 'healthy heal must be an observed native zero')
                effects.append(dict(root=int(i), candidate=j, truth=float(truth[1]), prediction=float(prediction[1]),
                    error=abs(float(prediction[1]) - float(truth[1])), operator=m['operator'],
                    domain=m['intent_domain'], healthy=healthy))
        if errors: root_error.append(mean(errors))
    groups = dict(pooled=effects)
    for domain in ('unit', 'base'): groups[domain] = [v for v in effects if v['domain'] == domain]
    for operator in ('damage', 'heal'): groups[operator] = [v for v in effects if v['operator'] == operator]
    healthy = [v for v in effects if v['healthy']]
    signed = [v for v in effects if v['truth'] != 0.]
    recall, specificity = mean(yes), mean(no)
    return dict(endpoint_mae={k: mean([v['error'] for v in group]) for k, group in groups.items()},
        endpoint_support={k: len(group) for k, group in groups.items()},
        nonzero_sign_accuracy=mean([float(v['truth'] * v['prediction'] > 0.) for v in signed]),
        nonzero_support=len(signed), healthy_count=len(healthy),
        healthy_mean_abs=mean([abs(v['prediction']) for v in healthy]),
        healthy_max_abs=max([abs(v['prediction']) for v in healthy], default=None),
        eligibility=dict(positive_recall=recall, specificity=specificity, rootbalanced_mae=mean(root_error),
            balanced_accuracy=(recall + specificity) / 2 if recall is not None and specificity is not None else None,
            positive_count=len(yes), negative_count=len(no), all_ones_positive_recall=1. if yes else None,
            scope='All-positive HELD eligibility has undefined specificity/BA; recall alone cannot establish discrimination.'),
        endpoints=effects)


def gates(evaluations):
    by_seed, full, control = {}, [], []
    for seed in SEEDS:
        current = evaluations[f's{seed}:new-full']['300']['held']
        comparator = evaluations[f's{seed}:old-late-fusion']['300']['held']
        printed = evaluations[f's{seed}:new-printed-only']['300']['held']
        values = current['endpoint_mae']
        absolute = all(v is not None and v <= .25 for v in values.values())
        sign = current['nonzero_sign_accuracy'] is not None and current['nonzero_sign_accuracy'] >= .95
        zero = current['healthy_count'] > 0 and current['healthy_max_abs'] <= .1
        recall = current['eligibility']['positive_recall'] is not None and current['eligibility']['positive_recall'] >= .95
        previous = comparator['endpoint_mae']['pooled']
        nonregression = values['pooled'] is not None and previous is not None and values['pooled'] <= previous + .05
        by_seed[str(seed)] = dict(endpoint_slices_passed=absolute, nonzero_sign_passed=sign,
            healthy_max_abs_passed=zero, positive_recall_descriptive_passed=recall,
            usable_endpoint_gate_passed=absolute and sign and zero and recall,
            old_endpoint_nonregression=nonregression, eligibility_discrimination_qualified=False)
        full.append(values['pooled']); control.append(printed['endpoint_mae']['pooled'])
    a = mean(full) if all(v is not None for v in full) else None
    b = mean(control) if all(v is not None for v in control) else None
    improvement = 1. - a / b if a is not None and b is not None and b > 0. else None
    return dict(per_seed=by_seed, pooled_three_seed_new_mae=a, pooled_three_seed_printed_mae=b,
        relative_improvement_vs_printed=improvement,
        usability_passed=all(v['usable_endpoint_gate_passed'] for v in by_seed.values()),
        architecture_diagnostic_passed=improvement is not None and improvement >= .2 and
            all(v['old_endpoint_nonregression'] for v in by_seed.values()),
        deterministic_reference='Native/reference exactness is an admission prerequisite; learned performance cannot beat the perfect reference.',
        semantic_validated=False, scope='Two exposed-at-evaluation held cards and one selector form; no broad semantic or statistical qualification.')


def weight_statistics(labels, masks, train, metadata):
    """Verify saved TRAIN count-derived weights; do not fit any new parameter."""
    binary, strata = [0, 0], {}
    for i in train:
        require(sum(bool(m[1]) for m in masks[i]) <= 1, 'more than one supervised endpoint')
        for y, m in zip(labels[i], masks[i]):
            if m[0]:
                require(y[0] in (0., 1.), 'binary native eligibility required'); binary[int(y[0])] += 1
            if m[1]:
                key = metadata[i]['operator'] + '|' + metadata[i]['intent_domain']
                strata[key] = strata.get(key, 0) + 1
    require(all(binary) and set(strata) == {'damage|unit', 'damage|base', 'heal|unit'}, 'TRAIN-only class/stratum support differs')
    n = sum(binary); total = sum(strata.values())
    return dict(class_statistics=dict(class_counts=binary, weights=[n / (2 * v) for v in binary],
            scope='TRAIN-only inverse class frequency; per-root known-coordinate mean then root mean.'),
        stratum_statistics=dict(counts=strata, weights={k: total / (3 * v) for k, v in strata.items()},
            absent_train_strata=['heal|base'], known_endpoints=total,
            scope='TRAIN-only equal mass over three observed operator×domain strata, raw physical SmoothL1; held heal|base contributes no fitted weight.'))


def expected_shapes(arm):
    require(arm in ARMS, 'fixed three-arm comparison required')
    if arm == 'old-late-fusion':
        return {'paths.weight': (23, 16), 'values.weight': (16, 1), 'values.bias': (16,),
            'candidate.0.weight': (16, 17), 'candidate.0.bias': (16,),
            'readout.0.weight': (16, 48), 'readout.0.bias': (16,),
            'readout.2.weight': (2, 16), 'readout.2.bias': (2,)}
    values = {}
    for name, width in (('owner', 4), ('kind', 6), ('zone', 7), ('cap', 5), ('printed', 10), ('effect', 3), ('state', 4)):
        values[name + '.0.weight'] = (8, width); values[name + '.0.bias'] = (8,)
    for name, width in (('selector', 40), ('endpoint', 24)):
        values.update({name + '.0.weight': (16, width), name + '.0.bias': (16,),
                       name + '.2.weight': (1, 16), name + '.2.bias': (1,)})
    return values


def state_hash(values):
    parts = {k: hashlib.sha256(str(v.dtype).encode() + str(v.shape).encode() + v.tobytes(order='C')).hexdigest()
             for k, v in sorted(values.items())}
    return sha(parts)


def npz(np, path):
    with np.load(path, allow_pickle=False) as handle: return {k: handle[k] for k in handle.files}


def array_equal(np, actual, expected, name):
    require(actual.shape == expected.shape and actual.dtype == expected.dtype and np.array_equal(actual, expected), 'saved array differs: ' + name)


def counter_panel(events, *, updates=2700, evaluations=18):
    """The frozen ledger order is 2 statistics, updates, then all evaluations."""
    expected = ['numerical_fits'] * 2
    expected.extend(k for _ in range(updates) for k in ('neural_forwards', 'backwards', 'optimizer_updates'))
    expected.extend(['neural_forwards'] * evaluations)
    require(len(events) == len(expected) * 2, 'extra/missing fit counter event')
    for i, name in enumerate(expected):
        intent, done = events[2 * i:2 * i + 2]
        require(intent['event'] == 'intent' and done['event'] == 'complete' and
                intent['data']['counter'] == name and type(intent['data']['amount']) is int and intent['data']['amount'] == 1 and
                intent['data']['token'] == intent['sequence'] == done['data']['token'] and
                done['data']['actual'] is None and done['data']['proofs'] == [],
                'fit call completion/order/deferred-HELD barrier differs')
    return dict(training_forwards=updates, evaluation_forwards=evaluations,
        optimizer_updates=updates, backwards=updates, numerical_fits=2,
        all_evaluation_after_last_update=True,
        scope='Durable call order plus frozen worker call-flow; saved-weight forward parity is not tested.')


def source_pins(spec, parent):
    frozen = {}
    for p in parent['pins'] + parent['protected_files'] + spec['pins'] + [spec['source'], spec['primitives']]:
        require(set(p) == {'path', 'sha256', 'bytes'} and (p['path'] not in frozen or frozen[p['path']] == p),
                'conflicting or malformed inherited source pin')
        frozen[p['path']] = p
    return frozen


def fit_inventory():
    names = {'result.json', 'contract.json', 'consumed-inputs.npz', 'training-schedule.npz', 'loss-weights.json', 'fit-progress.jsonl',
        'deterministic-reference-predictions.npz', 'all-ones-eligibility-zero-effect-predictions.npz'}
    for seed in SEEDS:
        for arm in ARMS:
            names.update(f's{seed}-{arm}-{suffix}.npz' for suffix in
                ('initial-checkpoint', 'checkpoint', 'step0-predictions', 'step300-predictions'))
    return names


def budget_audit(root):
    spec_path = root / 'campaign-spec.json'; spec = load(spec_path)
    ledger = rows(root / 'campaign-ledger.jsonl'); previous = '0' * 64
    require(spec['schema'] == 'jepa-sealed-budget-spec/1' and spec['guard']['cpu_workers'] == 1 and
            0 < spec['guard']['rss_bytes'] <= 1024 ** 3 and spec['caps']['paid_jobs'] == spec['caps']['paid_spend_usd'] == 0,
            'sealed single-worker/local resource contract differs')
    pending, complete, fit_events, fit_finish, observed = None, [], [], None, {}
    for index, record in enumerate(ledger):
        body = {k: v for k, v in record.items() if k != 'record_sha256'}
        require(record['schema'] == 'jepa-sealed-budget-journal/1' and record['sequence'] == index and
                record['previous_sha256'] == previous and record['record_sha256'] == sha(body), 'ledger chain changed')
        previous = record['record_sha256']; event, data = record['event'], record['data']
        if index == 0:
            require(event == 'initialized' and data == dict(spec=pin(spec_path)), 'ledger exact spec link differs'); continue
        if event == 'begin':
            require(pending is None and data['stage'] == spec['stage_order'][len(complete)] and
                    data['argv'] == spec['stages'][data['stage']]['argv'] and data['guard'] == spec['guard'], 'stage order/command differs')
            pending = data['stage']
        elif event == 'finish':
            require(pending is not None and data['status'] == 'completed' and data['cleanup_verified'] is True and
                    data['execution_ended'] is True and not data.get('integrity_error'), 'prior stage failed or cleanup uncertain')
            reserve = spec['stages'][pending]['reservation']; expected = spec['stages'][pending]['expected']
            require(data['seconds'] <= reserve['seconds'] and all(data['charged'][k] <= reserve[k] for k in reserve), 'stage ceiling breached')
            require(all(v is None or data['durable_completed'][k] == v for k, v in expected.items()), 'sealed expected counter differs')
            if pending == 'fit': fit_finish = data
            observed[pending] = data['durable_completed']; complete.append(pending); pending = None
        else:
            require(event in ('intent', 'complete') and pending is not None, 'unreviewed accounting event or unresolved failure')
            if pending == 'fit': fit_events.append(record)
    require(spec['stage_order'][-1] == pending == 'verify' and complete == spec['stage_order'][:-1] and
            {'native', 'prep', 'fit'} <= set(complete) and fit_finish is not None, 'verification requires completed native/prep/fit and its own pending stage')
    proof = counter_panel(fit_events)
    for key, value in COUNTS.items():
        require(fit_finish['durable_intents'][key] == fit_finish['durable_completed'][key] == fit_finish['charged'][key] == value,
                'fit exact durable counters differ: ' + key)
    for key in ('native_applies', 'paid_jobs', 'paid_spend_usd'):
        require(fit_finish['durable_completed'][key] == fit_finish['charged'][key] == 0, 'fit performed an unallocated call')
    # The outer ledger already verifies the full protected closure. Independently
    # bind every scientific implementation used by this saved-output verifier.
    parent = load(spec['parent_manifest']['path'])
    require(pin(spec['parent_manifest']['path']) == spec['parent_manifest'], 'inherited protected closure byte pin differs')
    frozen = source_pins(spec, parent)
    own = Path(__file__).resolve().parent
    for name in ('real_ir_adapter.py', 'real_ir_reservation_v3.py', 'real_ir_transfer_data.py',
                 'real_ir_transfer_model.py', 'real_ir_transfer_fit.py', Path(__file__).name):
        p = pin(own / name); require(frozen.get(p['path']) == p, 'scientific source not frozen: ' + name)
    require(observed['native']['native_applies'] <= 168, 'native application ceiling exceeded')
    return dict(fit=proof, native_applies=observed['native']['native_applies'], complete_stages=complete,
        pending='verify', source_pins_verified=True, official_new_verification_calls=0,
        parent_manifest=spec['parent_manifest'], original_failures_preserved_by_parent=True)


def audit_progress(log, result):
    expected = [(seed, arm, update) for seed in SEEDS for arm in ARMS for update in range(1, 301)]
    require(len(log) == len(expected), '2700 durable fit loss rows required')
    losses = {f's{seed}:{arm}': [] for seed in SEEDS for arm in ARMS}
    for row, (seed, arm, update) in zip(log, expected):
        require((row['seed'], row['arm'], row['update']) == (seed, arm, update), 'TRAIN full-batch arm/update order differs')
        require(all(type(row[k]) in (int, float) and math.isfinite(row[k]) for k in
            ('loss', 'eligibility_loss', 'endpoint_loss', 'preclip_gradient_l2')) and row['preclip_gradient_l2'] >= 0., 'nonfinite loss/gradient journal')
        close(row['loss'], .5 * (row['eligibility_loss'] + row['endpoint_loss']), 'combined TRAIN loss')
        losses[f's{seed}:{arm}'].append(row['loss'])
    for key, values in losses.items(): close(result['results'][key]['losses'], values, key + '.losses')
    return dict(rows=len(log), train_order='seed, arm, full40TRAIN, update1..300', finite=True)


def verify(np, root, out):
    """Saved-only guarded worker; no imports of any learned-model module."""
    import real_ir_transfer_data as D
    root, out = Path(root).resolve(), Path(out).resolve()
    require(out.is_dir() and not any(out.iterdir()), 'existing empty exclusive verification directory required')
    accounting = budget_audit(root)
    plan_path = root / 'metadata-1/native-plan.json'
    receipt_path = root / 'native-1/receipt.json'; trace_path = root / 'native-1/transitions.jsonl'
    plan, receipt, trace = load(plan_path), load(receipt_path), rows(trace_path)
    require(receipt['collectionPlanSha256'] == pin(plan_path)['sha256'], 'native plan byte pin differs')
    rebuilt, manifest = D.prepare_data(np, plan, receipt, trace)
    require(manifest['fit_admitted'] is True and not manifest['fit_blockers'] and
            manifest['reference']['known_eligibility'] == 336 and manifest['reference']['known_intended_deltas'] == 39 and
            manifest['reference']['known_coordinates'] == 375 and manifest['reference']['mismatch_count'] == 0 and
            manifest['journal_proof']['native_applies'] == accounting['native_applies'], 'native/reference/support gate differs')
    require(tuple(manifest['program_feature_names']) == PROGRAM_FIELDS and tuple(manifest['candidate_feature_names']) == CANDIDATE_FIELDS and
            tuple(manifest['source_printed_feature_names']) == PRINTED_FIELDS, 'P13/C17/S10 numerical field order differs')
    saved = npz(np, root / 'prep-1/dataset.npz'); require(set(saved) == set(rebuilt), 'dataset array inventory differs')
    for key in rebuilt: array_equal(np, saved[key], rebuilt[key], 'dataset.' + key)
    prepared_manifest = load(root / 'prep-1/manifest.json')
    extra = set(prepared_manifest) - set(manifest)
    require(extra <= {'input_pins'}, 'unreviewed prepared manifest enrichment')
    close({k: prepared_manifest[k] for k in manifest}, manifest, 'prepared manifest', tolerance=0.)
    fit = root / 'fit-1'
    require({p.name for p in fit.iterdir()} == fit_inventory() and
            all(p.is_file() and not p.is_symlink() for p in fit.iterdir()), 'saved fit44-file inventory differs')
    result = load(fit / 'result.json'); contract = load(fit / 'contract.json')
    require(result['schema'] == 'jepa-real-ir-transfer-fit/1' and result['semantic_validated'] is False and
            result['counts'] == COUNTS and result['native_applies'] == result['paid_jobs'] == 0, 'fit status/counter/scope claim differs')
    config = dict(seeds=list(SEEDS), arms=list(ARMS), updates_per_arm=300, training_forwards=2700,
        evaluation_forwards=18, neural_forwards=2718, backwards=2700, optimizer_updates=2700, numerical_fits=2,
        learning_rate=.003, weight_decay=.0001, clip_l2=1., eligibility_loss_coefficient=.5,
        endpoint_loss_coefficient=.5, endpoint_huber_beta=1., fixed_physics=True, hyperparameter_search=False)
    close(result['config'], config, 'fit config', tolerance=0.); close(contract['config'], config, 'saved contract', tolerance=0.)
    require(Path(contract['source_dataset']).resolve() == root / 'prep-1/dataset.npz' and
            Path(contract['source_manifest']).resolve() == root / 'prep-1/manifest.json', 'fit used adjacent/unbound input files')
    model = contract['model']
    require(model['schema'] == 'jepa-real-ir-transfer-model/1' and model['arms'] == list(ARMS) and
            model['program_fields'] == list(PROGRAM_FIELDS) and model['candidate_fields'] == list(CANDIDATE_FIELDS) and
            model['source_printed_fields'] == list(PRINTED_FIELDS) and model['semantic_validated'] is False, 'saved model field/scope contract differs')
    close(model['scales'], dict(program=[1.] * 9 + [4., 1., 1., 3.], candidate=[1.] * 9 + [4., 1., 1., 4., 1., 10., 1., 1.],
        printed=[4., 1., 10., 1., 10., 1., 1., 1., 1., 1.]), 'fixed public scales', tolerance=0.)
    inputs = npz(np, fit / 'consumed-inputs.npz')
    input_keys = {'program_features', 'source_printed_features', 'candidate_features', 'program_indices', 'train_idx', 'held_idx'}
    require(set(inputs) == input_keys, 'actual consumed input inventory differs')
    for key in input_keys: array_equal(np, inputs[key], saved[key], 'consumed.' + key)
    schedule = npz(np, fit / 'training-schedule.npz')
    require(set(schedule) == {'train_indices', 'seeds', 'arms', 'updates'}, 'training schedule inventory differs')
    array_equal(np, schedule['train_indices'], saved['train_idx'], 'TRAIN schedule')
    require(schedule['seeds'].tolist() == list(SEEDS) and schedule['arms'].tolist() == list(ARMS) and
            schedule['updates'].tolist() == list(range(1, 301)), 'seeds/arms/update schedule differs')
    labels, masks, metadata = saved['targets'].tolist(), saved['primary_target_mask'].tolist(), manifest['root_metadata']
    partitions = dict(train=saved['train_idx'].tolist(), held=saved['held_idx'].tolist())
    close(load(fit / 'loss-weights.json'), weight_statistics(labels, masks, partitions['train'], metadata), 'saved TRAIN-only statistics')
    progress = audit_progress(rows(fit / 'fit-progress.jsonl'), result)
    expected_result_keys = {f's{seed}:{arm}' for seed in SEEDS for arm in ARMS}
    require(set(result['results']) == expected_result_keys, 'missing/extra arm or seed')
    evaluations, states, inventory = {}, {}, []
    for seed in SEEDS:
        for arm in ARMS:
            key = f's{seed}:{arm}'; item = result['results'][key]; state_pair = []
            shapes = expected_shapes(arm)
            close(model['parameters'][arm], dict(allocated=sum(math.prod(v) for v in shapes.values()),
                shapes={k: list(v) for k, v in shapes.items()}), 'allocated graph.' + arm, tolerance=0.)
            for suffix, claim in (('initial-checkpoint', 'initial_state_sha256'), ('checkpoint', 'final_state_sha256')):
                path = fit / f's{seed}-{arm}-{suffix}.npz'; state = npz(np, path)
                require(set(state) == set(shapes), 'named checkpoint inventory differs')
                for name, shape in shapes.items():
                    require(state[name].shape == shape and state[name].dtype == np.float32 and np.isfinite(state[name]).all(), 'checkpoint shape/float32/finite differs')
                actual_hash = state_hash(state); require(item[claim] == actual_hash, 'named checkpoint hash differs')
                state_pair.append(actual_hash); inventory.append(pin(path))
            states[key] = dict(initial=state_pair[0], final=state_pair[1], named_tensors=len(shapes))
            require(item['master_initial_state_sha256'] == (None if arm == 'old-late-fusion' else state_pair[0]), 'shared initial-state provenance differs')
            evaluations[key] = {}
            require(set(item['evaluations']) == {'0', '300'}, 'unexpected checkpoint selection/evaluation')
            for step in (0, 300):
                path = fit / f's{seed}-{arm}-step{step}-predictions.npz'; prediction = npz(np, path)
                require(set(prediction) == {'predictions', 'eligibility_logits', 'program_indices'}, 'prediction array inventory differs')
                p, logits = prediction['predictions'], prediction['eligibility_logits']
                require(p.shape == (56, 6, 2) and logits.shape == (56, 6) and p.dtype == logits.dtype == np.float32 and
                        np.isfinite(p).all() and np.isfinite(logits).all() and ((p[..., 0] >= 0) & (p[..., 0] <= 1)).all(), 'invalid raw saved prediction')
                array_equal(np, prediction['program_indices'], saved['program_indices'], 'prediction program alignment')
                exponential = np.exp(-np.abs(logits.astype(np.float64)))
                probability = np.where(logits >= 0, 1. / (1. + exponential), exponential / (1. + exponential))
                require(np.allclose(probability, p[..., 0], rtol=1e-6, atol=1e-7), 'saved probability/logit mismatch')
                require((p[..., 1][saved['candidate_features'][..., 16] == 0] == 0).all(), 'non-intended endpoint escaped the fixed graph gate')
                evaluation = {name: scores(p.tolist(), labels, masks, metadata, indices) for name, indices in partitions.items()}
                close(item['evaluations'][str(step)], evaluation, key + '.' + str(step))
                require(evaluation['held']['eligibility']['negative_count'] == 0 and
                        evaluation['held']['eligibility']['balanced_accuracy'] is None and
                        evaluation['held']['eligibility']['specificity'] is None, 'held positive-only eligibility overclaim')
                evaluations[key][str(step)] = evaluation; inventory.append(pin(path))
        require(states[f's{seed}:new-full']['initial'] == states[f's{seed}:new-printed-only']['initial'], 'NEW full/printed initial weights differ')
    final_gates = gates(evaluations); close(result['decisions'], final_gates, 'independent gate decisions')
    baseline_metrics = {}
    for name in ('deterministic-reference', 'all-ones-eligibility-zero-effect'):
        prediction = npz(np, fit / (name + '-predictions.npz'))
        require(set(prediction) == {'predictions', 'program_indices'}, 'baseline inventory differs')
        array_equal(np, prediction['program_indices'], saved['program_indices'], 'baseline alignment')
        if name == 'deterministic-reference': expected = saved['baseline_predictions']
        else:
            expected = np.zeros((56, 6, 2), np.float32); expected[..., 0] = 1.
        array_equal(np, prediction['predictions'], expected, 'saved baseline.' + name)
        baseline_metrics[name] = {part: scores(expected.tolist(), labels, masks, metadata, indices) for part, indices in partitions.items()}
    close(result['baseline_evaluations'], baseline_metrics, 'independent baseline scores')
    close(result['held_samples'], dict(cards=2, roots=16, eligibility_all_positive=True), 'held scope', tolerance=0.)
    report = dict(schema='jepa-real-ir-transfer-verification/1', verified=True, mismatches=0,
        native_reference=dict(known_coordinates=375, eligibility=336, committed_intended_deltas=39,
            actual_native_applies=receipt['applyCalls'], exact=True, no_label_replacement=True),
        source_pins_verified=True, dataset_arrays_verified=len(saved), prepared_manifest_verified=True,
        independently_scored_prediction_files=18, checkpoints_verified=18, common_new_initials_verified=3,
        checkpoints=states, actual_consumed_arrays_verified=len(inputs), training_statistics_verified=True,
        deferred_evaluation=accounting['fit'], fit_progress=progress, accounting=accounting,
        decisions=final_gates, evaluations=evaluations, baseline_evaluations=baseline_metrics,
        input_pins=[pin(p) for p in (plan_path, receipt_path, trace_path, root / 'prep-1/dataset.npz',
            root / 'prep-1/manifest.json', fit / 'result.json', fit / 'contract.json')], saved_artifact_pins=inventory,
        calls=dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0),
        semantic_validated=False,
        scope='Native data are rebuilt with the frozen converter; metrics, TRAIN count weights, byte contracts and counters are checked independently. No model-forward parity or broad semantic/deck qualification.')
    raw = (json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with (out / 'verification-result.json').open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    return report
