"""Saved-only HP-projection checks; ROOT owns the guard and canonical ledger.

Rebuilds data with the frozen converters. Scores, gates, checkpoint hashes and
counter order are verified without importing a model or training worker. No
saved-weight forward parity is claimed except exact baseline checkpoint bytes.
"""
import math
import os
from pathlib import Path

import real_ir_transfer_verify as V

SEEDS = (17, 29, 43)
ARMS = ('baseline', 'effect-hp-invariant')
COUNTS = dict(neural_forwards=1815, backwards=1800, optimizer_updates=1800, numerical_fits=0)
PANELS = ('train', 'old_dev', 'fresh_all', 'fresh_primary', 'fresh_replay')


def raw_scores(predictions, labels, masks, metadata, indices):
    points, undefined = [], []
    for i in indices:
        for q, (prediction, truth, known) in enumerate(zip(predictions[i], labels[i], masks[i])):
            if not known[1]: continue
            p, delta = map(float, prediction)
            V.require(math.isfinite(p) and math.isfinite(delta) and 0. <= p <= 1., 'invalid saved probability/delta')
            if p == 0.:
                undefined.append([int(i), q]); continue
            raw = delta / p
            V.require(math.isfinite(raw) and (raw == delta == 0. or raw * delta > 0.), 'invalid conditional division/sign')
            m = metadata[i]
            points.append(dict(root=int(i), candidate=q, truth=float(truth[1]), prediction=raw,
                routed_prediction=delta, eligibility_probability=p, error=abs(raw - float(truth[1])),
                operator=m['operator'], domain=m['intent_domain'],
                healthy=bool(m['healthy_intent']) and m['operator'] == 'heal', division_near_zero=p < 1e-6))
    groups = dict(pooled=points)
    for domain in ('unit', 'base'): groups[domain] = [p for p in points if p['domain'] == domain]
    for op in ('damage', 'heal'): groups[op] = [p for p in points if p['operator'] == op]
    nonzero = [p for p in points if p['truth'] != 0.]; healthy = [p for p in points if p['healthy']]
    return dict(endpoint_mae={k: V.mean([p['error'] for p in group]) for k, group in groups.items()},
        endpoint_support={k: len(group) for k, group in groups.items()}, undefined=undefined,
        nonzero_sign_accuracy=V.mean([float(p['truth'] * p['prediction'] > 0.) for p in nonzero]),
        healthy_max_abs=max((abs(p['prediction']) for p in healthy), default=None), endpoints=points,
        scope='Float32 saved delta/p oracle-eligibility arithmetic, not a new neural prediction or retained preactivation; p=0 remains undefined.')


def usability(m):
    mae = all(v is not None and v <= .25 for v in m['endpoint_mae'].values())
    sign = m['nonzero_sign_accuracy'] is not None and m['nonzero_sign_accuracy'] >= .95
    zero = m['healthy_count'] > 0 and m['healthy_max_abs'] <= .1
    recall = m['eligibility']['positive_recall'] is not None and m['eligibility']['positive_recall'] >= .95
    return dict(endpoint_slices_passed=mae, nonzero_sign_passed=sign, healthy_max_abs_passed=zero,
        positive_recall_descriptive_passed=recall, usable_endpoint_gate_passed=mae and sign and zero and recall,
        eligibility_discrimination_qualified=False)


def gates(evaluations):
    result = {}
    for seed in SEEDS:
        old = evaluations[f's{seed}:baseline']['300']; new = evaluations[f's{seed}:effect-hp-invariant']['300']
        a, b = new['fresh_primary']['raw'], old['fresh_primary']['raw']
        absolute = all(v is not None and v <= .25 for v in a['endpoint_mae'].values()) and not a['undefined']
        sign = a['nonzero_sign_accuracy'] is not None and a['nonzero_sign_accuracy'] >= .95
        x, y = a['endpoint_mae']['pooled'], b['endpoint_mae']['pooled']
        relative = 1. - x / y if x is not None and y is not None and y > 0. else None
        train, baseline = new['train']['routed']['endpoint_mae']['pooled'], old['train']['routed']['endpoint_mae']['pooled']
        nonregression = train is not None and baseline is not None and train <= baseline + .05
        gain = relative is not None and relative >= .2
        result[str(seed)] = dict(raw_endpoint_slices_passed=absolute, raw_nonzero_sign_passed=sign,
            relative_raw_mae_improvement=relative, raw_improvement_passed=gain, train_routed_nonregression=nonregression,
            primary_passed=absolute and sign and gain and nonregression,
            old_dev_original_usability={arm: usability(evaluations[f's{seed}:{arm}']['300']['old_dev']['routed']) for arm in ARMS})
    return dict(per_seed=result, primary_passed=all(v['primary_passed'] for v in result.values()),
        thresholds=dict(raw_mae_max=.25, raw_nonzero_sign_min=.95, raw_relative_improvement_min=.2, train_routed_mae_allowance=.05),
        scope='Fresh nonreplay30 known endpoints are primary; replay9 and exposed olddev16 are separate. Oracle-eligibility raw gate and original fully routed usability are different decisions.',
        semantic_validated=False)


def counter_panel(events, updates=1800, evaluations=15):
    expected = [name for _ in range(updates) for name in ('neural_forwards', 'backwards', 'optimizer_updates')]
    expected += ['neural_forwards'] * evaluations
    V.require(len(events) == 2 * len(expected), 'extra/missing call, or a forbidden statistics refit')
    for i, name in enumerate(expected):
        a, z = events[2 * i:2 * i + 2]
        V.require(a['event'] == 'intent' and z['event'] == 'complete' and a['data']['counter'] == name and
            type(a['data']['amount']) is int and a['data']['amount'] == 1 and
            a['sequence'] == a['data']['token'] == z['data']['token'] and z['data']['actual'] is None and z['data']['proofs'] == [],
            'fit counter pair/deferred-evaluation barrier differs')
    return dict(training_forwards=updates, evaluation_forwards=evaluations, backwards=updates,
        optimizer_updates=updates, numerical_fits=0, all_evaluation_after_last_update=True)


def budget_audit(root):
    spec_path = root / 'campaign-spec.json'; spec = V.load(spec_path); ledger = V.rows(root / 'campaign-ledger.jsonl')
    previous, pending, done, calls, finish = '0' * 64, None, [], [], None
    V.require(spec['schema'] == 'jepa-sealed-budget-spec/1' and spec['guard']['cpu_workers'] == 1 and
        0 < spec['guard']['rss_bytes'] <= 1024 ** 3 and spec['caps']['numerical_fits'] ==
        spec['caps']['paid_jobs'] == spec['caps']['paid_spend_usd'] == 0, 'bounded no-refit/local contract differs')
    for i, row in enumerate(ledger):
        body = {k: v for k, v in row.items() if k != 'record_sha256'}
        V.require(row['schema'] == 'jepa-sealed-budget-journal/1' and row['sequence'] == i and
            row['previous_sha256'] == previous and row['record_sha256'] == V.sha(body), 'ledger chain differs')
        previous = row['record_sha256']; event, data = row['event'], row['data']
        if i == 0:
            V.require(event == 'initialized' and data == dict(spec=V.pin(spec_path)), 'exact new spec link differs'); continue
        if event == 'begin':
            V.require(pending is None and data['stage'] == spec['stage_order'][len(done)] and
                data['argv'] == spec['stages'][data['stage']]['argv'] and data['guard'] == spec['guard'], 'stage route differs')
            pending = data['stage']
        elif event == 'finish':
            V.require(pending and data['status'] == 'completed' and data['cleanup_verified'] is True and
                data['execution_ended'] is True and not data.get('integrity_error'), 'failed/uncertain current stage')
            descriptor = spec['stages'][pending]
            V.require(data['seconds'] <= descriptor['reservation']['seconds'] and
                all(data['charged'][k] <= value for k, value in descriptor['reservation'].items()) and
                all(value is None or data['durable_completed'][k] == value for k, value in descriptor['expected'].items()), 'stage budget/counters differ')
            if pending == 'fit': finish = data
            done.append(pending); pending = None
        else:
            V.require(pending and event in ('intent', 'complete'), 'unreviewed accounting event')
            if pending == 'fit': calls.append(row)
    V.require(pending == spec['stage_order'][-1] == 'verify' and done == spec['stage_order'][:-1] and
        {'native', 'prep', 'fit'} <= set(done) and finish is not None, 'all preceding current stages must complete')
    proof = counter_panel(calls)
    for key, value in dict(COUNTS, native_applies=0, paid_jobs=0, paid_spend_usd=0).items():
        V.require(finish['durable_intents'][key] == finish['durable_completed'][key] == finish['charged'][key] == value,
            'exact fixed fit count differs: ' + key)
    V.require(V.pin(spec['parent_manifest']['path']) == spec['parent_manifest'], 'parent closure pin differs')
    frozen = V.source_pins(spec, V.load(spec['parent_manifest']['path'])); own = Path(__file__).resolve().parent
    for name in ('real_ir_transfer_data.py', 'real_ir_transfer_verify.py', 'real_ir_transfer_model.py',
        'real_ir_hp_projection_data.py', 'real_ir_hp_projection_model.py', 'real_ir_hp_projection_fit.py', Path(__file__).name):
        p = V.pin(own / name); V.require(frozen.get(p['path']) == p, 'scientific source not frozen: ' + name)
    return dict(fit=proof, completed_stages=done, pending='verify', source_pins_verified=True)


def output_inventory():
    names = {'result.json', 'contract.json', 'input-pins.json', 'loss-weights.json', 'consumed-inputs.npz',
        'training-schedule.npz', 'fit-progress.jsonl', 'deterministic-reference-predictions.npz', 'all-ones-eligibility-zero-effect-predictions.npz'}
    for seed in SEEDS:
        for arm in ARMS:
            names.update(f's{seed}-{arm}-{suffix}.npz' for suffix in ('initial-checkpoint', 'checkpoint', 'step0-predictions', 'step300-predictions'))
        names.add(f's{seed}-old-printed-only-step300-predictions.npz')
    return names


def verify(np, root, out):
    import real_ir_hp_projection_data as H
    root, out = Path(root).resolve(), Path(out).resolve()
    V.require(out.is_dir() and not any(out.iterdir()), 'existing empty verification output directory required')
    accounting = budget_audit(root); spec = V.load(root / 'campaign-spec.json')
    prior = Path(spec['prior_root']); prepared, manifest = H.prepare(np, prior, root)
    V.require(manifest['fit_admitted'] and manifest['support'] == dict(fresh_known_endpoints=39, primary=30, replay=9) and
        manifest['reference']['known_coordinates'] == 375 and manifest['reference']['mismatch_count'] == 0, 'native/replay admission differs')
    saved = V.npz(np, root / 'prep-1/dataset.npz'); V.require(set(saved) == set(prepared), 'combined array inventory differs')
    for key in saved: V.array_equal(np, saved[key], prepared[key], 'prepared.' + key)
    V.close(V.load(root / 'prep-1/manifest.json'), manifest, 'combined manifest', tolerance=0.)
    fit = root / 'fit-1'; V.require({p.name for p in fit.iterdir()} == output_inventory(), 'fit36-file inventory differs')
    V.require(all(p.is_file() and not p.is_symlink() for p in fit.iterdir()), 'fit artifact must be regular files')
    result, contract = V.load(fit / 'result.json'), V.load(fit / 'contract.json')
    V.require(result['schema'] == 'jepa-real-ir-hp-projection-fit/1' and result['counts'] == COUNTS and
        result['native_applies'] == result['paid_jobs'] == 0 and result['semantic_validated'] is False, 'fit scope/counts differ')
    config = dict(seeds=list(SEEDS), arms=list(ARMS), updates_per_arm=300, training_forwards=1800, evaluation_forwards=15,
        neural_forwards=1815, backwards=1800, optimizer_updates=1800, numerical_fits=0, learning_rate=.003, weight_decay=.0001,
        clip_l2=1., eligibility_loss_coefficient=.5, endpoint_loss_coefficient=.5, endpoint_huber_beta=1., hyperparameter_search=False,
        statistics='Exact frozen PR45 TRAIN loss-weights.json; zero new statistics fits.')
    V.close(result['config'], config, 'fixed fit config', tolerance=0.); V.close(contract['config'], config, 'contract config', tolerance=0.)
    model = contract['model']; shapes = V.expected_shapes('new-full')
    V.require(model['schema'] == 'jepa-real-ir-hp-projection-model/1' and model['arms'] == list(ARMS) and
        model['base_source'] == V.pin(Path(__file__).with_name('real_ir_transfer_model.py')) and model['base_arm'] == 'new-full' and
        model['added_parameters'] == 0 and model['projection']['zero_columns'] == [2] and
        model['projection']['originating_candidate_column'] == 14 and model['projection']['original_input_mutated'] is False,
        'only the endpoint HP input projection is declared')
    V.close(model['parameters'], dict(allocated=1458, shapes={k: list(v) for k, v in shapes.items()}), 'unchanged graph', tolerance=0.)
    for p in V.load(fit / 'input-pins.json'): V.require(V.pin(p['path']) == p, 'fit input pin changed')
    V.close(V.load(fit / 'loss-weights.json'), manifest['old_loss_weights'], 'reused original TRAIN statistics', tolerance=0.)
    consumed = V.npz(np, fit / 'consumed-inputs.npz')
    wanted = {'program_features', 'source_printed_features', 'candidate_features', 'program_indices', 'train_idx', 'old_dev_idx', 'old_all_idx', 'fresh_all_idx'}
    V.require(set(consumed) == wanted, 'consumed input inventory differs')
    for key in wanted: V.array_equal(np, consumed[key], saved[key], 'consumed.' + key)
    schedule = V.npz(np, fit / 'training-schedule.npz')
    V.require(set(schedule) == {'train_indices', 'seeds', 'arms', 'updates'} and schedule['train_indices'].tolist() == list(range(40)) and
        schedule['seeds'].tolist() == list(SEEDS) and schedule['arms'].tolist() == list(ARMS) and schedule['updates'].tolist() == list(range(1, 301)), 'only original40 TRAIN schedule allowed')
    log = V.rows(fit / 'fit-progress.jsonl'); order = [(s, a, u) for s in SEEDS for a in ARMS for u in range(1, 301)]
    V.require(len(log) == len(order) == 1800, '1800 loss rows required')
    losses = {f's{s}:{a}': [] for s in SEEDS for a in ARMS}
    for row, (seed, arm, update) in zip(log, order):
        V.require((row['seed'], row['arm'], row['update']) == (seed, arm, update) and
            all(type(row[k]) in (int, float) and math.isfinite(row[k]) for k in ('loss', 'eligibility_loss', 'endpoint_loss', 'preclip_gradient_l2')) and row['preclip_gradient_l2'] >= 0., 'TRAIN order/loss/gradient differs')
        V.close(row['loss'], .5 * (row['eligibility_loss'] + row['endpoint_loss']), 'fixed objective')
        losses[f's{seed}:{arm}'].append(row['loss'])
    labels, masks, metadata = saved['targets'].tolist(), saved['target_mask'].tolist(), manifest['root_metadata']
    panels = dict(train=(saved['train_idx'].tolist(), masks), old_dev=(saved['old_dev_idx'].tolist(), masks), fresh_all=(saved['fresh_all_idx'].tolist(), masks),
        fresh_primary=(saved['fresh_all_idx'].tolist(), saved['primary_target_mask'].tolist()), fresh_replay=(saved['fresh_all_idx'].tolist(), saved['replay_target_mask'].tolist()))
    def score(p):
        return {name: dict(routed=V.scores(p, labels, mask, metadata, ids), raw=raw_scores(p, labels, mask, metadata, ids))
            for name, (ids, mask) in panels.items()}
    evaluations, hashes = {}, {}
    V.require(set(result['results']) == {f's{s}:{a}' for s in SEEDS for a in (*ARMS, 'old-printed-only')}, 'fixed methods/seeds required')
    for seed in SEEDS:
        original = V.npz(np, prior / f'fit-1/s{seed}-new-full-initial-checkpoint.npz'); original_hash = V.state_hash(original)
        for arm in ARMS:
            key = f's{seed}:{arm}'; item = result['results'][key]; V.close(item['losses'], losses[key], 'saved loss history')
            V.require(item['old_initial_state_sha256'] == original_hash, 'original common initializer differs')
            for suffix, field in (('initial-checkpoint', 'initial_state_sha256'), ('checkpoint', 'final_state_sha256')):
                state = V.npz(np, fit / f's{seed}-{arm}-{suffix}.npz')
                V.require(set(state) == set(shapes) and all(state[k].shape == shape and state[k].dtype == np.float32 and np.isfinite(state[k]).all()
                    for k, shape in shapes.items()), 'unchanged named float32 checkpoint shape differs')
                digest = V.state_hash(state); V.require(digest == item[field], 'checkpoint hash claim differs'); hashes[key + ':' + suffix] = digest
                if suffix == 'initial-checkpoint':
                    for k in shapes: V.array_equal(np, state[k], original[k], 'complete common original initializer')
                elif arm == 'baseline':
                    oldfinal = V.npz(np, prior / f'fit-1/s{seed}-new-full-checkpoint.npz')
                    for k in shapes: V.array_equal(np, state[k], oldfinal[k], 'exact original baseline final reproduction')
                    V.require(item['old_final_checkpoint_exact'] is True, 'baseline reproduction claim absent')
            V.require(set(item['evaluations']) == {'0', '300'}, 'only fixed initial/final readout allowed')
        printed = result['results'][f's{seed}:old-printed-only']
        V.require(printed['frozen_checkpoint'] == V.pin(prior / f'fit-1/s{seed}-new-printed-only-checkpoint.npz') and
            set(printed['evaluations']) == {'300'}, 'printed control must reuse its one frozen checkpoint')
        for arm in (*ARMS, 'old-printed-only'):
            key = f's{seed}:{arm}'; evaluations[key] = {}
            for step in ((300,) if arm == 'old-printed-only' else (0, 300)):
                a = V.npz(np, fit / f's{seed}-{arm}-step{step}-predictions.npz')
                V.require(set(a) == {'predictions', 'eligibility_logits', 'program_indices'} and a['predictions'].shape == (112, 6, 2) and
                    a['eligibility_logits'].shape == (112, 6) and a['predictions'].dtype == a['eligibility_logits'].dtype == np.float32 and
                    np.isfinite(a['predictions']).all() and np.isfinite(a['eligibility_logits']).all(), 'saved prediction ABI/finite differs')
                V.array_equal(np, a['program_indices'], saved['program_indices'], 'prediction source alignment')
                exponential = np.exp(-np.abs(a['eligibility_logits'].astype(np.float64)))
                probability = np.where(a['eligibility_logits'] >= 0, 1 / (1 + exponential), exponential / (1 + exponential))
                V.require(np.allclose(probability, a['predictions'][..., 0], rtol=1e-6, atol=1e-7) and
                    (a['predictions'][..., 1][saved['candidate_features'][..., 16] == 0] == 0).all(), 'logit/probability/intended gate differs')
                evaluated = score(a['predictions'].tolist())
                V.close(result['results'][key]['evaluations'][str(step)], evaluated, 'independent.' + key + '.' + str(step))
                evaluations[key][str(step)] = evaluated
    decisions = gates(evaluations); V.close(result['decisions'], decisions, 'independent fixed gate')
    baselines = {}
    for name in ('deterministic-reference', 'all-ones-eligibility-zero-effect'):
        a = V.npz(np, fit / (name + '-predictions.npz'))
        V.require(set(a) == {'predictions', 'program_indices'}, 'baseline saved inventory differs')
        V.array_equal(np, a['program_indices'], saved['program_indices'], 'baseline source alignment')
        expected = saved['baseline_predictions'] if name == 'deterministic-reference' else np.zeros((112, 6, 2), np.float32)
        if name != 'deterministic-reference': expected[..., 0] = 1.
        V.array_equal(np, a['predictions'], expected, 'exact saved baseline')
        baselines[name] = score(expected.tolist())
    V.close(result['baseline_evaluations'], baselines, 'independent baseline readouts')
    report = dict(schema='jepa-real-ir-hp-projection-verification/1', verified=True, mismatches=0,
        dataset_arrays_verified=len(saved), native_reference=manifest['reference'], support=manifest['support'],
        prediction_files_verified=15, checkpoints_verified=12, exact_baseline_reproductions=3, original_common_initials=6,
        checkpoint_hashes=hashes, accounting=accounting, decisions=decisions, evaluations=evaluations, baseline_evaluations=baselines,
        calls=dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0),
        input_pins=[V.pin(p) for p in (root / 'prep-1/dataset.npz', root / 'prep-1/manifest.json', fit / 'result.json', fit / 'contract.json')],
        scope='Frozen converters rebuild native data; saved metrics/counters/checkpoint identity are checked without model construction or forward parity. Same exposed cards, fresh states only.',
        semantic_validated=False)
    raw = V.canonical(report) + b'\n'
    with (out / 'verification-result.json').open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    return report
