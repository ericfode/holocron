"""Saved-only sidecar recovery after the original verifier schema failure.

Import and primitive tests use only the standard library. ROOT supplies NumPy
inside the existing verify reservation; no model is imported or constructed,
and no saved-weight forward, optimizer, fitting, or native action is called.
"""
import math
import os
from pathlib import Path

import real_ir_transfer_verify as V
import semantic_discrimination_accounting as P

SCHEMA = 'jepa-real-ir-intent-verification/2'
V1_SHA256 = 'e2ec1662a70effc42ea694f6e14390233630e2556019222c336e22bc0e49ec02'
PRIMITIVES_SHA256 = '15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d'
SEEDS = (17, 29, 43)
ARMS = ('current', 'matched-aux-latent', 'factorized-intent')
COMPARATORS = ('frozen-hp-projected', 'frozen-printed')
FIT_COUNTS = dict(neural_forwards=2700, backwards=2700, optimizer_updates=2700, numerical_fits=0)
SCORE_COUNTS = dict(neural_forwards=24, backwards=0, optimizer_updates=0, numerical_fits=0)
MODEL_SHA256 = '8e16dbb14fd460ce4fa2cbfa6e47f17324042620da3db8d8c6cc4d196b98d41b'
PANELS = ('train', 'old_dev', 'exposed', 'development_all', 'development_primary', 'development_replay', 'terminal')
CONFIG = dict(seeds=list(SEEDS), arms=list(ARMS), updates_per_arm=300, training_forwards=2700,
    evaluation_forwards=24, neural_forwards=2724, backwards=2700, optimizer_updates=2700, numerical_fits=0,
    learning_rate=.003, weight_decay=.0001, clip_l2=1., eligibility_loss_coefficient=.5,
    endpoint_loss_coefficient=.5, identity_loss_coefficient=.25, amount_loss_coefficient=.25,
    smooth_l1_beta=1., hyperparameter_search=False, statistics='Frozen original TRAIN weights; no new statistics fits.')


def shapes(arm):
    V.require(arm in ARMS, 'one fixed intent arm required')
    result = V.expected_shapes('new-full')
    if arm != 'current':
        result.update({'intent_identity.weight': (2, 8), 'intent_identity.bias': (2,),
            'intent_amount.weight': (1, 8), 'intent_amount.bias': (1,),
            'intent_lift.0.weight': (8, 3), 'intent_lift.0.bias': (8,)})
    return result


def counter_panel(events, *, updates=2700, evaluations=0):
    """Verify every durable call pair, including the separate scoring barrier."""
    names = [key for _ in range(updates) for key in ('neural_forwards', 'backwards', 'optimizer_updates')]
    names += ['neural_forwards'] * evaluations
    V.require(len(events) == 2 * len(names), 'extra/missing call or numerical fit')
    for i, name in enumerate(names):
        a, z = events[2 * i:2 * i + 2]
        V.require(a['event'] == 'intent' and z['event'] == 'complete' and
            a['data']['counter'] == name and type(a['data']['amount']) is int and a['data']['amount'] == 1 and
            a['sequence'] == a['data']['token'] == z['data']['token'] and
            z['data']['actual'] is None and z['data']['proofs'] == [], 'durable call order/barrier differs')
    return dict(training_forwards=updates, evaluation_forwards=evaluations,
        backwards=updates, optimizer_updates=updates, numerical_fits=0)


def raw_scores(predictions, labels, masks, metadata, indices):
    """Saved delta/p arithmetic on actual known endpoints; zero p is unknown."""
    points, undefined = [], []
    for i in indices:
        for q, (prediction, truth, known) in enumerate(zip(predictions[i], labels[i], masks[i])):
            if not known[1]:
                continue
            V.require(truth[0] == 1., 'conditional endpoint must be native allowed')
            p, delta = map(float, prediction)
            V.require(math.isfinite(p) and math.isfinite(delta) and 0. <= p <= 1., 'invalid saved probability/delta')
            if p == 0.:
                undefined.append([int(i), q])
                continue
            raw = delta / p
            V.require(math.isfinite(raw) and (raw == delta == 0. or raw * delta > 0.), 'invalid conditional division/sign')
            m = metadata[i]
            points.append(dict(root=int(i), candidate=q, truth=float(truth[1]), prediction=raw,
                routed_prediction=delta, eligibility_probability=p, error=abs(raw - float(truth[1])),
                operator=m['operator'], domain=m['intent_domain'],
                healthy=bool(m['healthy_intent']) and m['operator'] == 'heal', division_near_zero=p < 1e-6))
    groups = dict(pooled=points)
    for domain in ('unit', 'base'):
        groups[domain] = [p for p in points if p['domain'] == domain]
    for op in ('damage', 'heal'):
        groups[op] = [p for p in points if p['operator'] == op]
    nonzero = [p for p in points if p['truth'] != 0.]
    healthy = [p for p in points if p['healthy']]
    return dict(endpoint_mae={k: V.mean([p['error'] for p in group]) for k, group in groups.items()},
        endpoint_support={k: len(group) for k, group in groups.items()}, undefined=undefined,
        nonzero_sign_accuracy=V.mean([float(p['truth'] * p['prediction'] > 0.) for p in nonzero]),
        healthy_max_abs=max((abs(p['prediction']) for p in healthy), default=None), endpoints=points,
        scope='Float32 saved delta/p oracle-eligibility arithmetic, not a new neural prediction or retained preactivation; p=0 remains undefined.')


def typed_scores(identity, amount, program_indices, programs, indices):
    """One public syntax label per unique program, never repeated-board support."""
    if identity is None:
        return None
    first, points = {}, []
    for i in indices:
        key = int(program_indices[i])
        row = (list(identity[i]), float(amount[i]))
        V.require(len(row[0]) == 2 and all(math.isfinite(float(x)) for x in row[0]) and math.isfinite(row[1]),
            'finite typed identity/amount required')
        if key in first:
            V.require(row == first[key][1], 'card-only typed outputs differ across public states')
        else:
            first[key] = (i, row)
    for key in sorted(first):
        i, (logits, literal) = first[key]
        p = programs[key]
        V.require(p[10:12] in ([1., 0.], [0., 1.]) and p[12] > 0., 'typed syntax label outside fixed damage/heal grammar')
        truth = 0 if p[10] else 1
        prediction = 0 if logits[0] >= logits[1] else 1
        members = [j for j in indices if int(program_indices[j]) == key]
        points.append(dict(program_index=key, root_representative=int(i), roots=len(members),
            identity_truth=truth, identity_prediction=prediction, identity_correct=prediction == truth,
            amount_truth=float(p[12]), amount_prediction=literal, amount_error=abs(literal - float(p[12])),
            repeated_root_max_amount_difference=0., repeated_root_max_logit_difference=0.))
    return dict(programs=len(points), identity_accuracy=V.mean([float(p['identity_correct']) for p in points]),
        amount_mae=V.mean([p['amount_error'] for p in points]), per_program=points,
        scope='Unique public syntax readouts; repeated boards are not extra semantic samples.')


def endpoint_slices(routed, raw, metadata, public, programs, replay):
    """Independently group the already computed native-known endpoint errors."""
    conditional = {(p['root'], p['candidate']): p for p in raw['endpoints']}
    points = []
    fields = ('operator', 'amount', 'domain', 'owner', 'arena', 'healthy', 'damage', 'hp', 'cap')
    for endpoint in routed['endpoints']:
        p = dict(endpoint); i, q = p['root'], p['candidate']; m, c = metadata[i], public[i][q]
        cap = programs[m['program_index']]['selector']['cost_cap']
        x = conditional.get((i, q))
        p.update(source_card=m['source_card'], amount=m['amount'], owner=c['owner'], arena=c['zone'],
            damage=c['damage'], hp=c['hp'], cap=cap['value'] if cap['present'] else 'absent',
            prior_seen=True if i < 56 else bool(replay[i][q][1]) if i < 112 else None,
            raw_prediction=x['prediction'] if x else None, raw_error=x['error'] if x else None)
        p['joint'] = '|'.join(str(p[k]) for k in fields)
        points.append(p)
    tables = {}
    for field in (*fields, 'prior_seen', 'source_card', 'joint'):
        groups = {}
        for p in points:
            groups.setdefault(str(p[field]), []).append(p)
        tables[field] = {key: dict(endpoints=len(group), roots=len({p['root'] for p in group}),
            sources=len({p['source_card'] for p in group}), routed_mae=V.mean([p['error'] for p in group]),
            raw_mae=V.mean([p['raw_error'] for p in group if p['raw_error'] is not None])) for key, group in groups.items()}
    return dict(rows=points, tables=tables,
        scope='Descriptive cached endpoints; seeds/boards are not independent cards. Prior-seen applies to original or development effect/state tuples; terminal is unscoped/null.')


def endpoint_gate(metrics, *, require_all_slices):
    required = ('pooled', 'unit', 'base', 'damage', 'heal') if require_all_slices else ('pooled',)
    mae = all(metrics['endpoint_mae'][key] is not None and metrics['endpoint_mae'][key] <= .25 for key in required)
    sign = metrics['nonzero_sign_accuracy'] is not None and metrics['nonzero_sign_accuracy'] >= .95
    undefined = not metrics.get('undefined', [])
    # A slice without healthy examples is explicitly unsupported, not a passed test.
    healthy = None if metrics['healthy_max_abs'] is None else metrics['healthy_max_abs'] <= .1
    return dict(endpoint_slices_passed=mae, nonzero_sign_passed=sign, conditional_defined=undefined,
        healthy_max_abs_passed=healthy, endpoint_passed=mae and sign and undefined and healthy is not False)


def typed_gate(metrics):
    return bool(metrics and metrics['programs'] > 0 and metrics['identity_accuracy'] == 1. and
        metrics['amount_mae'] is not None and metrics['amount_mae'] <= .25)


def fit_inventory():
    names = {'result.json', 'contract.json', 'input-pins.json', 'loss-weights.json',
        'consumed-train-inputs.npz', 'training-schedule.npz', 'fit-progress.jsonl'}
    for seed in SEEDS:
        for arm in ARMS:
            names.update(f's{seed}-{arm}-{suffix}.npz' for suffix in ('initial-checkpoint', 'checkpoint'))
    return names


def score_prediction_inventory():
    names = set()
    for seed in SEEDS:
        for arm in ARMS:
            names.update(f's{seed}-{arm}-step{step}-predictions.npz' for step in (0, 300))
        for arm in COMPARATORS:
            names.add(f's{seed}-{arm}-step300-predictions.npz')
    return names


def audit_progress(log, result):
    order = [(s, a, u) for s in SEEDS for a in ARMS for u in range(1, 301)]
    V.require(len(log) == len(order) == 2700, '2700 fixed TRAIN progress rows required')
    losses = {f's{s}:{a}': [] for s in SEEDS for a in ARMS}
    for row, (seed, arm, update) in zip(log, order):
        V.require((row['seed'], row['arm'], row['update']) == (seed, arm, update), 'fixed seed/arm/update order differs')
        keys = ('loss', 'eligibility_loss', 'endpoint_loss', 'preclip_gradient_l2')
        V.require(all(type(row[k]) in (int, float) and math.isfinite(row[k]) for k in keys) and
            row['preclip_gradient_l2'] >= 0., 'nonfinite TRAIN loss/gradient')
        identity, amount = row['identity_loss'], row['amount_loss']
        if arm == 'current':
            V.require(identity is amount is None, 'current must use original native-only objective')
            identity = amount = 0.
        else:
            V.require(all(type(x) in (int, float) and math.isfinite(x) for x in (identity, amount)), 'finite auxiliary loss required')
        V.close(row['loss'], .5 * row['eligibility_loss'] + .5 * row['endpoint_loss'] +
            .25 * identity + .25 * amount, 'fixed TRAIN objective')
        losses[f's{seed}:{arm}'].append(row['loss'])
    for key, values in losses.items():
        V.close(result['results'][key]['losses'], values, 'TRAIN losses.' + key)
    return dict(rows=2700, full_train_only=True, numerical_fits=0)


def decisions(results):
    """Recompute fixed decisions without using the training/scoring worker."""
    def endpoint(panel, all_slices):
        result = {}
        for name in ('raw', 'routed'):
            value = endpoint_gate(panel[name], require_all_slices=all_slices)
            result[name] = dict(mae_passed=value['endpoint_slices_passed'] and value['conditional_defined'],
                nonzero_sign_passed=value['nonzero_sign_passed'], healthy_max_passed=value['healthy_max_abs_passed'])
        return result
    per_seed = {}
    for seed in SEEDS:
        current = results[f's{seed}:current']['evaluations']['300']
        control = results[f's{seed}:matched-aux-latent']['evaluations']['300']
        factorized = results[f's{seed}:factorized-intent']['evaluations']['300']
        dev = endpoint(factorized['development_primary'], True)
        x = factorized['development_primary']['routed']['endpoint_mae']['pooled']
        y = control['development_primary']['routed']['endpoint_mae']['pooled']
        reduction = 1. - x / y if x is not None and y is not None and y > 0. else None
        train = factorized['train']['routed']['endpoint_mae']['pooled']
        original = current['train']['routed']['endpoint_mae']['pooled']
        nonregression = train is not None and original is not None and train <= original + .05
        syntax = factorized['exposed']['typed_intent']
        typed = typed_gate(syntax) and syntax['programs'] == 7
        dev_pass = all(v['mae_passed'] and v['nonzero_sign_passed'] and v['healthy_max_passed'] is not False for v in dev.values())
        development = dev_pass and reduction is not None and reduction >= .2 and nonregression and typed
        terminal = endpoint(factorized['terminal'], False)
        e = factorized['terminal']['routed']['eligibility']
        eligibility = e['balanced_accuracy'] is not None and e['balanced_accuracy'] >= .95 and e['positive_recall'] is not None and e['positive_recall'] >= .95
        syntax = factorized['terminal']['typed_intent']
        terminal_typed = typed_gate(syntax) and syntax['programs'] == 1
        terminal_pass = all(v['mae_passed'] and v['nonzero_sign_passed'] for v in terminal.values()) and eligibility and terminal_typed
        per_seed[str(seed)] = dict(development_endpoint=dev, development_routed_relative_improvement=reduction,
            development_improvement_passed=reduction is not None and reduction >= .2, train_routed_nonregression=nonregression,
            exposed_unique_program_typed_passed=typed, development_passed=development, terminal_endpoint=terminal,
            terminal_eligibility_passed=eligibility, terminal_unique_program_typed_passed=terminal_typed, terminal_passed=terminal_pass)
    return dict(per_seed=per_seed, development_passed=all(p['development_passed'] for p in per_seed.values()),
        terminal_passed=all(p['terminal_passed'] for p in per_seed.values()),
        thresholds=dict(endpoint_mae_max=.25, nonzero_sign_min=.95, healthy_heal_max=.1, routed_improvement_min=.2,
            train_routed_allowance=.05, identity_accuracy=1., amount_mae_max=.25, terminal_balanced_accuracy_min=.95, terminal_positive_recall_min=.95),
        scope='Development29 nonreplay effects and terminal one-card outcome are separate gates. Unsupported slices remain null; no whole-card/deck qualification follows.', semantic_validated=False)


def chain(records, previous='0' * 64):
    """Use the frozen proven helper for schema-less and null-genesis history."""
    V.require(bool(records), 'empty append-only journal')
    V.require(V.pin(P.__file__)['sha256'] == PRIMITIVES_SHA256, 'frozen chain primitives changed')
    return P.chain(records, records[0].get('schema'), previous)


def terminal_boundary(fit_proofs, terminal_inputs, required_paths):
    """All fit artifacts must be completed and passed into terminal collection."""
    fitted = {p['path']: p for p in fit_proofs}
    consumed = {p['path']: p for p in terminal_inputs}
    V.require(set(required_paths) <= set(fitted) and all(consumed.get(p) == fitted[p] for p in required_paths),
        'all18 checkpoints and fit outputs must be byte sealed before terminal native begins')
    return True


def failed_verify(finish, descriptor, receipt, calls):
    """Admit only the known ended zero-call V1 schema failure, never forgive it."""
    reserve = descriptor['reservation']
    V.require(reserve['seconds'] == 10. and all(v == 0 for k, v in reserve.items() if k != 'seconds') and
        not calls and finish['status'] == 'failed' and finish['cleanup_verified'] is True and
        finish['execution_ended'] is True and not finish.get('integrity_error') and
        math.isfinite(finish['seconds']) and 0 <= finish['seconds'] <= 10. and
        finish['charged'] == reserve and
        all(v == 0 for v in finish['durable_intents'].values()) and
        all(v == 0 for v in finish['durable_completed'].values()), 'original failed verify/full10 charge or zero-call evidence differs')
    V.require(receipt['stage'] == 'verify' and receipt['status'] == 'failed' and receipt['cleanup_verified'] is True and
        receipt['error'] == dict(type='KeyError', message="'schema'"), 'original failure is not the preserved schema KeyError')
    return dict(status='failed', charged_seconds=10., preserved=True, scientific_calls=0)


def sidecar_pin_audit(original, sidecar, accounting):
    """Bind NEW recovery code to its own sealed allocation, keeping V1 frozen."""
    spec_path = sidecar / 'campaign-spec.json'
    spec = V.load(spec_path)
    V.require(spec['schema'] == 'jepa-sealed-budget-spec/1' and spec['stage_order'] == ['verify'] and
        spec['guard'] == dict(cpu_workers=1, rss_bytes=1024 ** 3) and
        spec['caps'] == dict(seconds=20., native_applies=0, neural_forwards=0, backwards=0,
            optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.), 'one saved-only20s sidecar required')
    V.require(V.pin(spec['parent_manifest']['path']) == spec['parent_manifest'], 'sidecar parent byte pin differs')
    parent = V.load(spec['parent_manifest']['path'])
    frozen = V.source_pins(spec, parent)
    for name in ('real_ir_intent_verify_v2.py', 'test_real_ir_intent_verify_v2.py',
                 'real_ir_intent_verify.py', 'semantic_discrimination_accounting.py'):
        p = V.pin(Path(__file__).with_name(name))
        V.require(frozen.get(p['path']) == p, 'sidecar source not byte frozen: ' + name)
    V.require(V.pin(Path(__file__).with_name('real_ir_intent_verify.py'))['sha256'] == V1_SHA256,
        'failed original verifier bytes changed')
    carry = dict(charged_native_applies=accounting['cumulative_native_applies'],
        charged_seconds=313.4962767929537 + accounting['original_new_charged']['seconds'], observed_native_applies=None)
    V.require(parent['carry'] == carry, 'failed original charge or historical unknownness reset in sidecar')
    original_spec = V.pin(original / 'campaign-spec.json')
    original_ledger = V.pin(original / 'campaign-ledger.jsonl')
    V.require(frozen.get(original_spec['path']) == original_spec and frozen.get(original_ledger['path']) == original_ledger,
        'sidecar must freeze the original closed failed campaign')
    V.require(spec['original_root'] == str(original) and V.pin(spec['failed_closure']['path']) == spec['failed_closure'] and
        spec['failed_closure']['path'] == str(original / 'experiment-closure.json'), 'exact closed failed original link differs')
    closure = V.load(spec['failed_closure']['path'])
    V.require(closure['schema'] == 'jepa-real-ir-intent-failed-closure/1' and closure['status'] == 'closed-failed-saved-verification' and
        closure['journal'] == original_ledger and closure['final_chain'] == accounting['ledger_chain'] and
        closure['completed_stages'] == accounting['completed_stages'] and closure['failed_stage'] == 'verify' and
        closure['new_charged'] == accounting['original_new_charged'] and closure['cumulative'] == carry and
        closure['failed_charge_credited'] is False and closure['decisions_independently_verified'] is False,
        'original failed closure changed, charge was credited, or success was retroactively claimed')
    ledger = V.rows(sidecar / 'campaign-ledger.jsonl')
    V.require(len(ledger) == 2 and chain(ledger) == ledger[-1]['record_sha256'] and
        ledger[0]['event'] == 'initialized' and ledger[0]['data'] == dict(spec=V.pin(spec_path)) and
        ledger[1]['event'] == 'begin' and ledger[1]['data']['stage'] == 'verify' and
        ledger[1]['data']['argv'] == spec['stages']['verify']['argv'] and ledger[1]['data']['guard'] == spec['guard'],
        'sidecar must have one initialized pending zero-call verify')
    return dict(specification=V.pin(spec_path), parent=spec['parent_manifest'], original_specification=original_spec,
        original_ledger=original_ledger, pending='verify', counters=0, preserved_failure_charge_seconds=10., carry=carry)


def budget_audit(root):
    """Check the canonical chain and the byte-sealed pre-terminal fit boundary."""
    spec_path = root / 'campaign-spec.json'
    spec = V.load(spec_path)
    order = ['build', 'dev-native', 'prep', 'fit', 'terminal-native', 'terminal-prep', 'score', 'verify']
    V.require(spec['schema'] == 'jepa-sealed-budget-spec/1' and spec['stage_order'] == order and
        spec['guard'] == dict(cpu_workers=1, rss_bytes=1024 ** 3) and
        spec['caps'] == dict(seconds=205., native_applies=240, neural_forwards=2724, backwards=2700,
            optimizer_updates=2700, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.), 'fixed local allocation differs')
    V.require(V.pin(spec['parent_manifest']['path']) == spec['parent_manifest'], 'parent manifest pin changed')
    parent = V.load(spec['parent_manifest']['path'])
    V.require(parent['carry'] == dict(charged_native_applies=1031, charged_seconds=313.4962767929537,
        observed_native_applies=None), 'historical failed allocation carry/unknownness changed')
    frozen = V.source_pins(spec, parent)
    for p in frozen.values():
        V.require(V.pin(p['path']) == p, 'raw or stored source/input byte pin differs: ' + p['path'])
    for journal in parent['closed_journals']:
        V.require(V.pin(journal['pin']['path']) == journal['pin'], 'closed historical journal changed')
        old = V.rows(journal['pin']['path'])
        V.require(len(old) == journal['records'] and chain(old, journal['genesis_previous']) == journal['final_chain'] and
            old[-1]['event'] == journal['closed_event'], 'historical final-chain closure differs')
    own = Path(__file__).resolve().parent
    sources = ('real_ir_transfer_verify.py', 'real_ir_transfer_data.py', 'real_ir_transfer_model.py',
        'real_ir_transfer_fit.py', 'real_ir_hp_projection_data.py', 'real_ir_hp_projection_model.py',
        'real_ir_hp_projection_fit.py', 'real_ir_intent_plan.py', 'real_ir_intent_data.py',
        'real_ir_intent_model.py', 'real_ir_intent_fit.py', 'real_ir_intent_campaign.py', 'real_ir_intent_verify.py',
        'REAL_IR_INTENT_PROTOCOL.md')
    for name in sources:
        p = V.pin(own / name)
        V.require(frozen.get(p['path']) == p, 'scientific source not frozen: ' + name)
    V.require(V.pin(own / 'real_ir_intent_model.py')['sha256'] == MODEL_SHA256, 'peer-reviewed intent model pin differs')
    ledger = V.rows(root / 'campaign-ledger.jsonl')
    final_chain = chain(ledger)
    V.require(ledger[0]['event'] == 'initialized' and ledger[0]['data'] == dict(spec=V.pin(spec_path)), 'canonical initialized spec link differs')
    pending, completed, ended, finishes, calls, proofs, begin_inputs = None, [], [], {}, {}, {}, {}
    totals = {k: 0 for k in spec['caps']}
    for row in ledger[1:]:
        event, data = row['event'], row['data']
        if event == 'begin':
            V.require(pending is None and len(ended) < len(order) and data['stage'] == order[len(ended)] and
                data['argv'] == spec['stages'][data['stage']]['argv'] and data['guard'] == spec['guard'], 'stage command/order differs')
            pending = data['stage']; calls[pending] = []; begin_inputs[pending] = data['inputs']
            allowed = dict(frozen, **proofs)
            for p in data['inputs']:
                V.require(allowed.get(p['path']) == p and V.pin(p['path']) == p, 'stage input is not a frozen/completed proof')
        elif event == 'finish':
            V.require(pending is not None, 'finish without original stage')
            descriptor = spec['stages'][pending]
            if pending == 'verify':
                failed_verify(data, descriptor, V.load(root / 'verify-1-stage-receipt.json'), calls[pending])
            else:
                V.require(data['status'] == 'completed' and data['cleanup_verified'] is True and
                    data['execution_ended'] is True and not data.get('integrity_error'), 'prior scientific stage failed/uncertain')
                V.require(math.isfinite(data['seconds']) and 0 <= data['seconds'] <= descriptor['reservation']['seconds'] and
                    all(data['charged'][k] <= v for k, v in descriptor['reservation'].items()) and
                    all(v is None or data['durable_completed'][k] == v for k, v in descriptor['expected'].items()), 'stage reservation/counters differ')
                V.require(data['charged']['seconds'] == data['seconds'] and
                    all(data['charged'][k] == data['durable_completed'][k] for k in data['durable_completed']), 'ended stage charge rewrite')
            for p in data['proofs']:
                V.require(V.pin(p['path']) == p and (p['path'] not in proofs or proofs[p['path']] == p), 'completed output byte pin differs')
                proofs[p['path']] = p
            for key in totals:
                totals[key] += data['charged'][key]
            finishes[pending] = data; ended.append(pending)
            if data['status'] == 'completed':
                completed.append(pending)
            pending = None
        else:
            V.require(pending is not None and event in ('intent', 'complete'), 'unreviewed journal event')
            calls[pending].append(row)
    V.require(completed == order[:-1] and ended == order and pending is None and not calls['verify'],
        'original must end with exactly seven complete stages and the single failed zero-call verify')
    fit_calls = counter_panel(calls['fit'])
    score_calls = counter_panel(calls['score'], updates=0, evaluations=24)
    for stage, expected in (('fit', FIT_COUNTS), ('score', SCORE_COUNTS)):
        for key, value in dict(expected, native_applies=0, paid_jobs=0, paid_spend_usd=0.).items():
            V.require(finishes[stage]['durable_intents'][key] == finishes[stage]['durable_completed'][key] ==
                finishes[stage]['charged'][key] == value, 'exact fixed fit/score counts differ')
    for stage in ('build', 'prep', 'terminal-prep'):
        V.require(not calls[stage], 'unallocated computation in build/prep')
    for stage, cap in (('dev-native', 200), ('terminal-native', 40)):
        pair = calls[stage]
        V.require(len(pair) == 2, 'one bounded external native reservation per panel required')
        a, z = pair
        raw = V.load(root / (stage + '-1') / 'receipt.json')
        V.require(a['event'] == 'intent' and z['event'] == 'complete' and a['data']['counter'] == 'native_applies' and
            a['data']['amount'] == cap and a['sequence'] == a['data']['token'] == z['data']['token'] and
            type(z['data']['actual']) is int and 0 <= z['data']['actual'] <= cap and
            z['data']['actual'] == raw['applyCalls'] == finishes[stage]['durable_completed']['native_applies'] and
            len({p['path'] for p in z['data']['proofs']}) >= 2, 'native observed count/pair differs')
        for p in z['data']['proofs']:
            V.require(V.pin(p['path']) == p, 'native direct trace proof pin differs')
    fit_paths = {str((root / 'fit-1' / name).resolve()) for name in fit_inventory()}
    terminal_boundary(finishes['fit']['proofs'], begin_inputs['terminal-native'], fit_paths)
    V.require(all(totals[k] <= spec['caps'][k] for k in totals), 'aggregate allocation cap exceeded')
    return dict(completed_stages=completed, ended_stages=ended, pending=None, ledger_chain=final_chain,
        original_failed_verification=dict(status='failed', charged_seconds=finishes['verify']['charged']['seconds'],
            actual_seconds=finishes['verify']['seconds'], calls=finishes['verify']['durable_completed'],
            receipt=V.pin(root / 'verify-1-stage-receipt.json'), preserved=True),
        fit=fit_calls, score=score_calls, all_fit_outputs_sealed_before_terminal=True,
        source_pins_verified=True, frozen_pin_count=len(frozen), historical_journals_verified=len(parent['closed_journals']),
        original_new_charged=totals, cumulative_native_applies=1031 + totals['native_applies'],
        observed_historical_native_applies=None, carry=parent['carry'])


def regular_inventory(directory, expected):
    V.require(directory.is_dir() and {p.name for p in directory.iterdir()} == expected and
        all(p.is_file() and not p.is_symlink() for p in directory.iterdir()), 'saved output inventory/regular-file constraint differs: ' + directory.name)


def check_input_pins(path, required):
    pins = V.load(path)
    V.require(isinstance(pins, list) and len({p['path'] for p in pins}) == len(pins), 'duplicate or malformed input pins')
    lookup = {p['path']: p for p in pins}
    for p in pins:
        V.require(V.pin(p['path']) == p, 'consumed source/input byte pin differs')
    for path in required:
        p = V.pin(path)
        V.require(lookup.get(p['path']) == p, 'required consumed input is not byte pinned: ' + p['path'])


def check_state(np, state, arm):
    expected = shapes(arm)
    V.require(set(state) == set(expected) and all(state[k].shape == shape and state[k].dtype == np.float32 and
        np.isfinite(state[k]).all() for k, shape in expected.items()), 'named finite float32 checkpoint shape differs')


def verify(np, root, out):
    """ROOT invokes once inside the sealed guard; saved arithmetic only."""
    import real_ir_intent_data as D
    root, out = Path(root).resolve(), Path(out).resolve()
    V.require(out.is_dir() and not any(out.iterdir()), 'existing empty verification output required')
    accounting = budget_audit(root)
    recovery = sidecar_pin_audit(root, out.parent, accounting)
    spec = V.load(root / 'campaign-spec.json')
    prior, hp = Path(spec['prior_root']), Path(spec['hp_prior_root'])
    rebuilt_dev, dev_manifest = D.prepare_development(np, prior, hp, root)
    saved_dev = V.npz(np, root / 'prep-1/dataset.npz')
    V.require(set(saved_dev) == set(rebuilt_dev), 'development dataset array keys differ')
    for key in saved_dev:
        V.array_equal(np, saved_dev[key], rebuilt_dev[key], 'development.' + key)
    V.close(V.load(root / 'prep-1/manifest.json'), dev_manifest, 'development manifest', tolerance=0.)
    rebuilt, manifest = D.prepare_terminal(np, root)
    saved = V.npz(np, root / 'terminal-prep-1/dataset.npz')
    V.require(set(saved) == set(rebuilt), 'final dataset array keys differ')
    for key in saved:
        V.array_equal(np, saved[key], rebuilt[key], 'terminal.' + key)
    V.close(V.load(root / 'terminal-prep-1/manifest.json'), manifest, 'terminal manifest', tolerance=0.)
    V.require(manifest['fit_admitted'] is True and not manifest['fit_blockers'] and
        manifest['terminal_admitted'] is True and not manifest['terminal_blockers'] and
        manifest['support'] == dict(development_known_endpoints=35, primary=29, replay=6, removed=1), 'fixed native/reference support/admission differs')
    for name, expected in (('reference', (371, 336, 35, 1)), ('terminal_reference', (52, 48, 4, 0))):
        ref = manifest[name]
        V.require(tuple(ref[k] for k in ('known_coordinates', 'known_eligibility', 'known_intended_deltas', 'removed_count')) == expected and
            ref['mismatch_count'] == ref['removal_mismatch_count'] == 0 and ref['mismatches'] == [], 'native/reference or removal mismatch')
    for key in ('candidate_features', 'targets', 'target_mask', 'baseline_predictions'):
        V.require(saved[key].shape == ((120, 6, 17) if key == 'candidate_features' else (120, 6, 2)) and
            saved[key].dtype == np.float32 and np.isfinite(saved[key]).all(), 'final120 tensor ABI differs')
    V.require(saved['program_features'].shape == (8, 13) and saved['source_printed_features'].shape == (8, 10) and
        saved['program_indices'].shape == (120,) and saved['program_indices'].dtype == np.int64, 'P13/S10/bank lookup ABI differs')
    partitions = dict(train_idx=list(range(40)), old_dev_idx=list(range(40, 56)), old_all_idx=list(range(56)),
        development_all_idx=list(range(56, 112)), terminal_idx=list(range(112, 120)))
    for key, expected in partitions.items():
        V.require(saved[key].dtype == np.int64 and saved[key].tolist() == expected, 'fixed saved partition differs: ' + key)
    masks = {key: saved[key] for key in ('target_mask', 'primary_target_mask', 'replay_target_mask', 'terminal_target_mask')}
    for key, mask in masks.items():
        V.require(mask.shape == (120, 6, 2) and mask.dtype == np.float32 and np.isin(mask, [0., 1.]).all() and
            (mask <= masks['target_mask']).all(), 'native knownness mask differs: ' + key)
    primary, replay, terminal = (masks[k] for k in ('primary_target_mask', 'replay_target_mask', 'terminal_target_mask'))
    V.require(primary[..., 0].sum() == replay[..., 0].sum() == 0 and primary[..., 1].sum() == 29 and replay[..., 1].sum() == 6 and
        not (primary * replay).any() and not primary[:56].any() and not primary[112:].any() and
        not replay[:56].any() and not replay[112:].any() and not terminal[:112].any() and
        terminal[..., 0].sum() == 48 and terminal[..., 1].sum() == 4, 'primary/replay/terminal unknown-future separation differs')
    fit, score = root / 'fit-1', root / 'score-1'
    regular_inventory(fit, fit_inventory())
    score_names = score_prediction_inventory() | {'result.json', 'input-pins.json', 'consumed-inputs.npz',
        'deterministic-reference-predictions.npz', 'all-ones-eligibility-zero-effect-predictions.npz'}
    regular_inventory(score, score_names)
    fitted, contract, scored = V.load(fit / 'result.json'), V.load(fit / 'contract.json'), V.load(score / 'result.json')
    for result, schema, counts in ((fitted, 'jepa-real-ir-intent-fit/1', FIT_COUNTS), (scored, 'jepa-real-ir-intent-score/1', SCORE_COUNTS)):
        V.require(result['schema'] == schema and result['counts'] == counts and result['native_applies'] == result['paid_jobs'] == 0 and
            result['semantic_validated'] is False, 'fit/score scope and exact calls differ')
        V.close(result['config'], CONFIG, 'fixed configuration', tolerance=0.)
    V.close(contract['config'], CONFIG, 'contract configuration', tolerance=0.)
    V.require(fitted['fit_sealed_before_terminal'] is True and scored['fit_result'] == V.pin(fit / 'result.json') and
        contract['admission_manifest'] == V.pin(root / 'prep-1/manifest.json'), 'fit/score/development closure differs')
    model = contract['model']
    V.require(model['schema'] == 'jepa-real-ir-intent-model/1' and model['arms'] == list(ARMS) and
        model['base_source'] == V.pin(Path(__file__).with_name('real_ir_transfer_model.py')) and
        model['semantic_validated'] is model['production_promotion'] is False, 'typed model/base source contract differs')
    expected_parameters = {a: dict(allocated=sum(math.prod(s) for s in shapes(a).values()),
        shapes={k: list(s) for k, s in shapes(a).items()}) for a in ARMS}
    V.close(model['parameters'], expected_parameters, 'independent parameter budget', tolerance=0.)
    V.close(model['inputs'], dict(program_fields=list(V.PROGRAM_FIELDS), candidate_fields=list(V.CANDIDATE_FIELDS),
        source_printed_fields=list(V.PRINTED_FIELDS)), 'unchanged public input ABI', tolerance=0.)
    check_input_pins(fit / 'input-pins.json', [root / 'prep-1/manifest.json', prior / 'prep-1/dataset.npz',
        prior / 'prep-1/manifest.json', prior / 'fit-1/loss-weights.json', Path(__file__).with_name('real_ir_intent_fit.py'),
        Path(__file__).with_name('real_ir_intent_model.py')])
    check_input_pins(score / 'input-pins.json', [root / 'terminal-prep-1/dataset.npz', root / 'terminal-prep-1/manifest.json',
        fit / 'result.json', fit / 'contract.json', fit / 'consumed-train-inputs.npz'])
    score_consumed = V.npz(np, score / 'consumed-inputs.npz')
    wanted = {'program_features', 'source_printed_features', 'candidate_features', 'program_indices', *partitions}
    V.require(set(score_consumed) == wanted, 'score consumed input inventory differs')
    for key in score_consumed:
        V.array_equal(np, score_consumed[key], saved[key], 'score exact public inputs.' + key)
    weights = V.load(prior / 'fit-1/loss-weights.json')
    V.close(V.load(fit / 'loss-weights.json'), weights, 'frozen original TRAIN weights', tolerance=0.)
    V.close(manifest['old_loss_weights'], weights, 'manifest frozen TRAIN weights', tolerance=0.)
    consumed = V.npz(np, fit / 'consumed-train-inputs.npz')
    old = V.npz(np, prior / 'prep-1/dataset.npz')
    V.require(set(consumed) == {'candidate_features', 'targets', 'target_mask', 'program_indices', 'program_features', 'source_printed_features'}, 'TRAIN-only input inventory differs')
    for key in consumed:
        n = 5 if key in ('program_features', 'source_printed_features') else 40
        V.array_equal(np, consumed[key], old[key][:n], 'original-only TRAIN.' + key)
        V.array_equal(np, consumed[key], saved[key][:n], 'final preserved TRAIN.' + key)
    schedule = V.npz(np, fit / 'training-schedule.npz')
    V.require(set(schedule) == {'train_indices', 'seeds', 'arms', 'updates'} and schedule['train_indices'].tolist() == list(range(40)) and
        schedule['seeds'].tolist() == list(SEEDS) and schedule['arms'].tolist() == list(ARMS) and
        schedule['updates'].tolist() == list(range(1, 301)), 'original full40 TRAIN schedule differs')
    V.require(set(fitted['results']) == {f's{s}:{a}' for s in SEEDS for a in ARMS}, 'fit arm/seed inventory differs')
    progress = audit_progress(V.rows(fit / 'fit-progress.jsonl'), fitted)
    hashes = {}
    for seed in SEEDS:
        original = V.npz(np, prior / f'fit-1/s{seed}-new-full-initial-checkpoint.npz')
        old_final = V.npz(np, prior / f'fit-1/s{seed}-new-full-checkpoint.npz')
        shared_aux = None
        for arm in ARMS:
            key = f's{seed}:{arm}'; item = fitted['results'][key]
            V.require(item['old_initial_state_sha256'] == V.state_hash(original) and item['evaluations'] == {}, 'no fit evaluation or changed original initializer allowed')
            initial = V.npz(np, fit / f's{seed}-{arm}-initial-checkpoint.npz')
            final = V.npz(np, fit / f's{seed}-{arm}-checkpoint.npz')
            for suffix, state, field in (('initial-checkpoint', initial, 'initial_state_sha256'), ('checkpoint', final, 'final_state_sha256')):
                check_state(np, state, arm); digest = V.state_hash(state)
                V.require(item[field] == digest, 'named checkpoint hash differs')
                hashes[key + ':' + suffix] = digest
            for name in original:
                V.array_equal(np, initial[name], original[name], 'entire original initializer')
            if arm == 'current':
                V.require(item['current_exact_reproduction'] is True and item['aux_initial_state_sha256'] is None, 'current reproduction claim differs')
                for name in old_final:
                    V.array_equal(np, final[name], old_final[name], 'exact current final reproduction')
            else:
                V.require(item['aux_initial_state_sha256'] == V.state_hash(initial), 'full auxiliary initial hash differs')
                if shared_aux is None:
                    shared_aux = initial
                else:
                    for name in initial:
                        V.array_equal(np, initial[name], shared_aux[name], 'common entire1517 auxiliary initialization')
                if arm == 'matched-aux-latent':
                    for name in ('intent_lift.0.weight', 'intent_lift.0.bias'):
                        V.array_equal(np, initial[name], final[name], 'unused matched-control lift remains unchanged')
    labels, known, metadata = saved['targets'].tolist(), saved['target_mask'].tolist(), manifest['root_metadata']
    panels = dict(train=(partitions['train_idx'], known), old_dev=(partitions['old_dev_idx'], known), exposed=(partitions['old_all_idx'], known),
        development_all=(partitions['development_all_idx'], known), development_primary=(partitions['development_all_idx'], primary.tolist()),
        development_replay=(partitions['development_all_idx'], replay.tolist()), terminal=(partitions['terminal_idx'], terminal.tolist()))
    def evaluate(prediction, extra):
        p = prediction.tolist()
        identity = extra['intent_identity_logits'].tolist() if extra else None
        amount = extra['intent_amount_native'].tolist() if extra else None
        result = {}
        for name, (ids, mask) in panels.items():
            routed = V.scores(p, labels, mask, metadata, ids)
            raw = raw_scores(p, labels, mask, metadata, ids)
            result[name] = dict(routed=routed, raw=raw,
                typed_intent=typed_scores(identity, amount, saved['program_indices'].tolist(), saved['program_features'].tolist(), ids),
                slices=endpoint_slices(routed, raw, metadata, manifest['public_before_records'], manifest['canonical_programs'], replay.tolist()))
        return result
    V.require(set(scored['results']) == {f's{s}:{a}' for s in SEEDS for a in (*ARMS, *COMPARATORS)}, 'score fixed methods/seeds differ')
    evaluations, initial_aux = {}, {}
    for seed in SEEDS:
        for arm in (*ARMS, *COMPARATORS):
            key = f's{seed}:{arm}'; item = scored['results'][key]; evaluations[key] = dict(evaluations={})
            steps = (0, 300) if arm in ARMS else (300,)
            V.require(set(item['evaluations']) == {str(s) for s in steps}, 'only fixed initial/final readouts allowed')
            if arm in COMPARATORS:
                path = hp / f'fit-1/s{seed}-effect-hp-invariant-checkpoint.npz' if arm == 'frozen-hp-projected' else prior / f'fit-1/s{seed}-new-printed-only-checkpoint.npz'
                V.require(item['frozen_checkpoint'] == V.pin(path), 'frozen comparator checkpoint differs')
            for step in steps:
                data = V.npz(np, score / f's{seed}-{arm}-step{step}-predictions.npz')
                extra_names = {'intent_identity_logits', 'intent_amount_native', 'card_effect', 'application_effect'} if arm in ARMS[1:] else set()
                V.require(set(data) == {'predictions', 'eligibility_logits', 'program_indices'} | extra_names and
                    data['predictions'].shape == (120, 6, 2) and data['eligibility_logits'].shape == (120, 6), 'prediction file ABI differs')
                V.array_equal(np, data['program_indices'], saved['program_indices'], 'prediction source lookup alignment')
                V.require(all(data[k].dtype == np.float32 and np.isfinite(data[k]).all() for k in data if k != 'program_indices'), 'finite float32 saved predictions required')
                logits = data['eligibility_logits'].astype(np.float64)
                exp = np.exp(-np.abs(logits)); probability = np.where(logits >= 0., 1. / (1. + exp), exp / (1. + exp))
                V.require(np.allclose(probability, data['predictions'][..., 0], rtol=1e-6, atol=1e-7) and
                    (data['predictions'][..., 1][saved['candidate_features'][..., 16] == 0.] == 0.).all(), 'saved probability/intended gating differs')
                extra = {k: data[k] for k in extra_names}
                if extra:
                    for name, shape in (('intent_identity_logits', (120, 2)), ('intent_amount_native', (120,)), ('card_effect', (120, 8)), ('application_effect', (120, 8))):
                        V.require(extra[name].shape == shape, 'typed card output shape differs')
                    if arm == 'matched-aux-latent':
                        V.array_equal(np, extra['application_effect'], extra['card_effect'], 'matched latent effect route')
                    if step == 0:
                        if arm == 'matched-aux-latent':
                            initial_aux[seed] = extra
                        else:
                            for name in ('intent_identity_logits', 'intent_amount_native', 'card_effect'):
                                V.array_equal(np, extra[name], initial_aux[seed][name], 'shared auxiliary initial card readouts')
                value = evaluate(data['predictions'], extra)
                V.close(item['evaluations'][str(step)], value, 'independent.' + key + '.' + str(step))
                evaluations[key]['evaluations'][str(step)] = value
    decision = decisions(evaluations)
    V.close(scored['decisions'], decision, 'independent preregistered gates')
    baselines = {}
    for name in ('deterministic-reference', 'all-ones-eligibility-zero-effect'):
        data = V.npz(np, score / (name + '-predictions.npz'))
        V.require(set(data) == {'predictions', 'program_indices'}, 'baseline prediction key inventory differs')
        V.array_equal(np, data['program_indices'], saved['program_indices'], 'baseline source lookup')
        expected = saved['baseline_predictions'] if name == 'deterministic-reference' else np.zeros((120, 6, 2), np.float32)
        if name != 'deterministic-reference':
            expected[..., 0] = 1.
        V.array_equal(np, data['predictions'], expected, 'exact deterministic baseline')
        baselines[name] = evaluate(expected, {})
    V.close(scored['baseline_evaluations'], baselines, 'independent deterministic baseline readouts')
    report = dict(schema=SCHEMA, verified=True, mismatches=0, dataset_arrays_verified=len(saved),
        development_reference=manifest['reference'], terminal_reference=manifest['terminal_reference'], support=manifest['support'],
        prediction_files_verified=24, checkpoints_verified=18, exact_current_reproductions=3, shared_entire_auxiliary_initials=3,
        checkpoint_hashes=hashes, progress=progress, accounting=accounting, recovery=recovery, decisions=decision,
        evaluations=evaluations, baseline_evaluations=baselines,
        calls=dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0),
        input_pins=[V.pin(p) for p in (root / 'terminal-prep-1/dataset.npz', root / 'terminal-prep-1/manifest.json', fit / 'result.json', score / 'result.json')],
        lineage=dict(original_verifier=V.pin(Path(__file__).with_name('real_ir_intent_verify.py')),
            original_failure_preserved=True, scientific_arithmetic_unchanged=True),
        scope='Saved-only sidecar for a closed failed verifier. Scientific arithmetic is unchanged from frozen V1; only historical journal compatibility and closed-failure lifecycle differ. No model construction, saved-weight forward parity, complete-card or deck qualification.',
        semantic_validated=False)
    with (out / 'verification-result.json').open('xb') as stream:
        stream.write(V.canonical(report) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    return report
