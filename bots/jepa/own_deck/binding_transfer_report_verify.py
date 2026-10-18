"""Saved-output report verifier with explicit failed-fit provenance.

Exact predecessor: binding_transfer_repair_verify.py SHA-256
cb0661bd71feeedfbacf8656d18bf9cd8013de87219e2b633d8546af90fbd675.
Scientific checks remain unchanged from 859b/2ada/cb066. Only accounting,
budgets, recovered-result input routing and failed-origin provenance change.
The source fit remains FAILED at its full charge with unknown observed neural
counters. Its immutable saved artifacts and durable prefix are evidence only;
this worker never authorizes another model or native call.

Import is stdlib-only. NumPy loads after durable reservation and the five-second
own-process guard. No fit, conversion, initialization or model import occurs.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

HERE = Path(__file__).resolve().parent
SEEDS = (17, 29, 43)
MAIN = ('C0R0', 'C1R0', 'C0R1', 'C1R1')
ARMS = (*MAIN, 'ID-only', 'untrained-typed')
ASPECTS = ('vigilance', 'command', 'aggression', 'cunning', 'heroism', 'villainy')
ENCODER = ('edge.', 'depth', 'kind.', 'value.', 'numeric.', 'leaf.', 'card_projection.')
BLOCKED = {'torch', 'tinygrad', 'tensorflow', 'jax', 'jaxlib', 'keras', 'transformers',
           'cupy', 'sklearn', 'statsmodels', 'scipy'}
GUARD_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
ORIGINAL_VERIFIER_SHA = '859b1ec2af31fad806352c0672d82c810d371406dd169d1bfd3b3ef83843e903'
ACCOUNTING_MODULE = 'binding_transfer_report_accounting'
PREDECESSOR_VERIFIER_SHA = 'cb0661bd71feeedfbacf8656d18bf9cd8013de87219e2b633d8546af90fbd675'
PRIOR_LINKED_VERIFIER_SHA = '2adaed75d90abdc019e13685db84cf475ffdfa505e670f7bfd9e6c8cd219571f'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pin(path):
    p = Path(path).resolve()
    raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def read(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def array_hash(value):
    return hashlib.sha256(str(value.dtype).encode() + str(value.shape).encode() + value.tobytes()).hexdigest()


def close(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 2e-6 + 1e-6*abs(b)
    return a == b


class Checks:
    def __init__(self):
        self.count = 0
        self.mismatches = []

    def check(self, ok, name, actual=None, expected=None):
        self.count += 1
        if not ok:
            self.mismatches.append(dict(check=name, actual=actual, expected=expected))

    def metric(self, actual, expected, name):
        self.check(close(actual, expected), name, actual, expected)


def sign(value):
    return 1 if value > .25 else -1 if value < -.25 else 0


def improvement(repaired, baseline):
    relative = (baseline-repaired)/baseline if baseline is not None and baseline > 0 else None
    return dict(repaired_mae=repaired, baseline_mae=baseline,
                absolute_error_reduction=baseline-repaired if baseline is not None else None,
                relative_error_reduction=relative,
                ten_percent_improvement=relative >= .10 if relative is not None else None,
                zero_baseline_policy='Relative reduction and threshold are null when baseline<=0; absolute errors remain.')


def public_projection(np, arrays, manifest):
    """Independent public owner counts and intended-reference equality only."""
    rows = manifest['public_catalog_rows']
    order = manifest['candidate_order']
    xs, cs = [], []
    for record in manifest['public_before_records']:
        require(set(record) == {'before', 'refs', 'declared_intent', 'observation_refs'}, 'before-only record keys')
        before, refs = record['before'], record['refs']
        projections = before['projections']
        source = projections['source']
        require(source['known']['identity'] is True and source['known']['owner'] is True, 'public source knownness')
        own = source['owner']
        require(own in ('p1', 'p2'), 'public source owner')
        other = 'p2' if own == 'p1' else 'p1'

        def metadata(p):
            if p is None or p.get('dynamic_aspects') is True:
                return None
            if p.get('known', {}).get('printed_aspects', True) is not True:
                return None
            values = rows.get(p.get('code'), {}).get('card', {}).get('aspects')
            if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
                return None
            values = {x.strip().lower() for x in values}
            if not values <= set(ASPECTS):
                return None
            witness = p.get('printed_aspects')
            if witness is not None and (not isinstance(witness, list) or
                    {x.strip().lower() for x in witness} != values):
                return None
            return values

        units, complete = {}, True
        for role, p in projections.items():
            if p is None:
                continue
            require(p['id'] == refs[role] and p['known']['identity'] is True, 'public role identity')
            require(p.get('zone') not in ('hand', 'deck') or
                    (p['id'] == source['id'] and p['owner'] == own and p['zone'] == 'hand'), 'no opponent/private pile input')
            if p['known']['owner'] is not True or p['owner'] not in ('p1', 'p2'):
                complete = False
                continue
            if p['present'] and p['is_unit'] and p['zone'] in ('ground', 'space'):
                require(p['id'] not in units, 'duplicate native fixture unit role')
                units[p['id']] = p
        try:
            raw_ids = {p['id'] for seat in ('p1', 'p2') for zone in ('ground', 'space')
                       for p in before['state']['players'][seat][zone]}
            complete = complete and raw_ids == set(units)
        except (KeyError, TypeError):
            complete = False
        extension = []
        for owner in (own, other):
            values = [metadata(p) for p in units.values() if p['owner'] == owner]
            known = complete and all(v is not None for v in values)
            extension.extend(sum(a in v for v in values) if known else 0 for a in ASPECTS)
            extension.append(float(known))
        intent = record['declared_intent']
        target = refs.get(intent.get('ref'))
        intended_p = projections.get(intent.get('ref'))
        relation_known = (intent.get('requires_target') is True and target is not None and
                          intent.get('id') == target and intended_p is not None and
                          intended_p['id'] == target and intended_p['known']['identity'] is True)
        candidates = []
        for role in order:
            p = projections.get(role)
            values = metadata(p)
            known = p is not None and relation_known
            candidates.append([*(float(a in values) if values is not None else 0. for a in ASPECTS),
                               float(values is not None), float(refs[role] == target) if known else 0., float(known)])
        xs.append(extension)
        cs.append(candidates)
    x = np.concatenate((arrays['context_features'], np.asarray(xs, np.float32)), -1)
    c = np.concatenate((arrays['candidate_features'], np.asarray(cs, np.float32)), -1)
    require(x.shape == (26, 32) and c.shape == (26, 8, 43), 'final public input ABI')
    return x, c


def normalized_inputs(np, rawx, rawc, scalers, arm):
    x = (rawx-np.asarray(scalers['context_features']['center'], np.float32))/np.asarray(scalers['context_features']['scale'], np.float32)
    c = (rawc-np.asarray(scalers['candidate_features']['center'], np.float32))/np.asarray(scalers['candidate_features']['scale'], np.float32)
    if arm[1] == '0':
        x[:, 18:] = 0
        c[:, :, 34:41] = 0
    if arm[3] == '0':
        c[:, :, 41:] = 0
    return x, c


def head_metrics(np, prediction, labels, masks, indices, spec):
    y, p, m = labels[indices], prediction[indices], masks[indices] > 0
    width = int(np.prod(y.shape[1:])) if y.ndim > 1 else 1
    y, p, m = (v.reshape(len(indices), width) for v in (y, p, m))
    sizes = m.sum(1)
    valid = sizes > 0
    error = ((abs(p-y)*m).sum(1)/np.maximum(sizes, 1))[valid]
    residual = (((p-y)*m).sum(1)/np.maximum(sizes, 1))[valid]
    coordinate = (p-y)[m]
    observed = y[m]
    positive, negative = (y == 1) & m, (y == 0) & m
    sensitivity = float(((p >= .5) & positive).sum()/positive.sum()) if spec['binary'] and positive.any() else None
    specificity = float(((p < .5) & negative).sum()/negative.sum()) if spec['binary'] and negative.any() else None
    accuracy = ((((p >= .5) == y)*m).sum(1)/np.maximum(sizes, 1))[valid]
    native_sign = np.where(p > .25, 1, np.where(p < -.25, -1, 0))
    true_sign = np.where(y > .25, 1, np.where(y < -.25, -1, 0))
    mae = float(error.mean()) if len(error) else None
    return dict(observed_roots=int(valid.sum()), known_coordinates=int(m.sum()), mae=mae,
                train_scaled_mae=mae/spec['scale'] if mae is not None else None,
                signed_residual=float(residual.mean()) if len(residual) else None,
                native_values=np.unique(observed).tolist(), zero=int((observed == 0).sum()),
                positive=int((observed > 0).sum()), negative=int((observed < 0).sum()),
                binary_accuracy=float(accuracy.mean()) if len(accuracy) and spec['binary'] else None,
                sensitivity=sensitivity, specificity=specificity,
                balanced_accuracy=(sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,
                rmse=float(np.sqrt(np.mean(coordinate*coordinate))) if len(coordinate) else None,
                max_abs_error=float(abs(coordinate).max()) if len(coordinate) else None,
                zero_sign_accuracy=float((native_sign[m] == true_sign[m]).mean()) if len(coordinate) and not spec['binary'] else None)


def chosen_mask(np, arrays, manifest):
    mask = np.zeros_like(arrays['target_mask'])
    for i, record in enumerate(manifest['public_before_records']):
        if record['declared_intent']['requires_target'] is True:
            j = int(arrays['selected_candidate_indices'][i])
            mask[i, j] = arrays['target_mask'][i, j]
    return mask


def narrow(np, branch, arrays, manifest, partitions):
    codes = arrays['source_cards'].astype(str)
    selected = arrays['selected_candidate_indices']
    damage = manifest['target_names'].index('target_damage_delta')
    crows = [int(i) for i in partitions['state_held'] if codes[i] == 'LAW_045']
    cvalues = [(float(arrays['targets'][i, selected[i], damage]), float(branch[i, selected[i], damage]))
               for i in crows if arrays['target_mask'][i, selected[i], damage]]
    result = dict(C=dict(roots=crows, known_coordinates=len(cvalues),
                        mae=sum(abs(p-y) for y, p in cvalues)/len(cvalues) if cvalues else None,
                        zero_sign_accuracy=sum(sign(p) == sign(y) for y, p in cvalues)/len(cvalues) if cvalues else None))
    if len(cvalues) == 2:
        truth, predicted = cvalues[1][0]-cvalues[0][0], cvalues[1][1]-cvalues[0][1]
        result['C'].update(paired_native_contrast=truth, paired_prediction=predicted,
                           contrast_mae=abs(truth-predicted), direction_accuracy=float(sign(truth) == sign(predicted)))
    rresult = {}
    for code in ('LOF_053', 'LOF_261'):
        errors, signs, pair_errors, pair_signs = [], [], [], []
        for i in [int(v) for k in ('family_held', 'joint') for v in partitions[k] if codes[v] == code]:
            q = int(selected[i])
            for name in ('target_power_delta', 'target_hp_delta'):
                h = manifest['target_names'].index(name)
                known = np.flatnonzero(arrays['target_mask'][i, :, h])
                for j in known:
                    y, p = float(arrays['targets'][i, j, h]), float(branch[i, j, h])
                    errors.append(abs(p-y)); signs.append(sign(p) == sign(y))
                    if j != q and arrays['target_mask'][i, q, h]:
                        truth = float(arrays['targets'][i, q, h]-arrays['targets'][i, j, h])
                        predicted = float(branch[i, q, h]-branch[i, j, h])
                        pair_errors.append(abs(predicted-truth)); pair_signs.append(sign(predicted) == sign(truth))
        mean = lambda v: float(sum(v)/len(v)) if v else None
        rresult[code] = dict(known_coordinates=len(errors), mae=mean(errors), zero_sign_accuracy=mean(signs),
                             measured_pairs=len(pair_errors), contrast_mae=mean(pair_errors), direction_accuracy=mean(pair_signs))
    result['R'] = rresult
    result['R_equal_variant_mae'] = sum(v['mae'] for v in rresult.values())/2 if all(v['mae'] is not None for v in rresult.values()) else None
    return result


def compare_heads(np, checks, predictions, saved, arrays, manifest, plan, name):
    output = {}
    chosen = chosen_mask(np, arrays, manifest)
    for cell, raw_indices in plan['split']['root_partitions'].items():
        indices = np.asarray(raw_indices, np.int64)
        output[cell] = {}
        for panel in ('actual_endpoints', 'chosen_only_subset'):
            heads = {}
            for pkey, ykey, mkey in (('source', 'source_targets', 'source_mask'), ('branch', 'targets', 'target_mask')):
                mask = chosen if mkey == 'target_mask' and panel == 'chosen_only_subset' else arrays[mkey]
                for h, spec in enumerate(plan['scalers'][ykey]):
                    metric = head_metrics(np, predictions[pkey][..., h], arrays[ykey][..., h], mask[..., h], indices, spec)
                    expected = saved['cells'][cell][panel]['heads'][spec['name']]
                    for key, value in metric.items():
                        checks.metric(value, expected.get(key), f'{name}/{cell}/{panel}/{spec["name"]}/{key}')
                    checks.check(expected['training_support'] == spec, f'{name}/{cell}/{panel}/{spec["name"]}/TRAIN-support')
                    heads[spec['name']] = metric
            output[cell][panel] = heads
    return output


def check_scalers(np, checks, arrays, plan, rawx, rawc):
    train = np.asarray(plan['split']['root_partitions']['train'], np.int64)
    for key, values in (('context_features', rawx), ('candidate_features', rawc)):
        v = values[train]; axes = tuple(range(v.ndim-1))
        for field, expected in (('center', v.mean(axes)), ('scale', np.maximum(1, v.std(axes)))):
            checks.check(np.array_equal(np.asarray(plan['scalers'][key][field], np.float32), expected), 'TRAIN-only/'+key+'/'+field)
    specs = []
    for key, mkey in (('source_targets', 'source_mask'), ('targets', 'target_mask')):
        for h, saved in enumerate(plan['scalers'][key]):
            y = arrays[key][train, ..., h]; m = arrays[mkey][train, ..., h] > 0; v = y[m]
            values = np.unique(v).tolist(); binary = saved['binary']
            counts = {str(s): int((np.sign(v) == s).sum()) for s in (-1, 0, 1)}
            classes = sum(n > 0 for n in counts.values())
            expected = dict(known=len(v), varying=len(values) > 1, values=values,
                            center=0. if binary or not len(v) else float(v.mean()),
                            scale=1. if binary or not len(v) else max(1., float(v.std())),
                            zero=int((v == 0).sum()), nonzero=int((v != 0).sum()),
                            negative=int((v < 0).sum()), positive=int((v > 0).sum()),
                            class_weights={s: len(v)/(classes*n) if n else 0. for s, n in counts.items()})
            for field, value in expected.items():
                checks.metric(value, saved[field], 'TRAIN-only/'+saved['name']+'/'+field)
            specs.append(saved)
    varying = sum(s['varying'] for s in specs); constant = sum(s['known'] > 0 and not s['varying'] for s in specs)
    for spec in specs:
        coefficient = 1./varying if spec['varying'] else .1/constant if spec['known'] and constant else 0.
        checks.metric(coefficient, spec['loss_coefficient'], 'TRAIN-only/'+spec['name']+'/loss-coefficient')


def conflicts(np, x, c, arrays, plan):
    seen, bad = {}, []
    signatures = dict(zip(plan['codes'], plan['semantic_tensor_sha256']))
    for i, code in enumerate(arrays['source_cards'].astype(str)):
        prefix = signatures[code].encode()
        def key(candidate):
            return hashlib.sha256(len(prefix).to_bytes(8, 'little')+prefix+x[i].tobytes()+candidate.tobytes()).hexdigest()
        for kind, labels, masks, keys in (
                ('source', arrays['source_targets'][i:i+1], arrays['source_mask'][i:i+1], [key(c[i, arrays['selected_candidate_indices'][i]])]),
                ('branch', arrays['targets'][i], arrays['target_mask'][i], [key(v) for v in c[i]])):
            for j, signature in enumerate(keys):
                for h in range(labels.shape[-1]):
                    if masks[j, h]:
                        identity = (kind, signature, h); value = float(labels[j, h])
                        if identity in seen and seen[identity] != value:
                            bad.append(dict(kind=kind, root=i, candidate=j, head=h))
                        else:
                            seen[identity] = value
    return bad


def npz(np, path):
    with np.load(path, allow_pickle=False) as values:
        return {k: values[k].copy() for k in values.files}


def named_tensor_hash(values):
    payload = {name: array_hash(values[name]) for name in sorted(values)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def independent_chain(rows):
    previous = '0'*64
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != 'record_sha256'}
        actual = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        require(row['sequence'] == i and row['previous_sha256'] == previous and row['record_sha256'] == actual, 'independent ledger hash-chain check')
        previous = actual
    return previous


def support_audit(np, checks, arrays, manifest, plan):
    train = plan['split']['root_partitions']['train']; output = {}
    for name in ('target_damage_delta', 'target_power_delta', 'target_hp_delta'):
        h = manifest['target_names'].index(name); by_template = {}
        for template in sorted({manifest['template_ids'][i] for i in train}):
            ids = [i for i in train if manifest['template_ids'][i] == template]
            values = arrays['targets'][ids, :, h][arrays['target_mask'][ids, :, h] > 0]
            by_template[template] = dict(positive=int((values > 0).sum()), zero=int((values == 0).sum()), negative=int((values < 0).sum()))
        eligible = [t for t, v in by_template.items() if v['positive'] and v['zero']]
        checks.check(len(eligible) >= 2, 'two-positive-and-zero-TRAIN-templates/'+name)
        output[name] = dict(by_template=by_template, independent_supported_templates=eligible)
    held = [i for part in ('family_held', 'joint') for i in plan['split']['root_partitions'][part]]
    for name, expected_train, expected_held in (('target_power_delta', [1., 2.], [2.]), ('target_hp_delta', [1., 3.], [2., 3.])):
        h = manifest['target_names'].index(name); values = []
        for ids in (train, held):
            y = arrays['targets'][ids, :, h]; mask = arrays['target_mask'][ids, :, h] > 0
            values.append(sorted(set(float(v) for v in y[mask] if v > 0)))
        checks.check(values == [expected_train, expected_held], 'upfront-quantity-support/'+name, values, [expected_train, expected_held])
    return output


def audit_event(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in BLOCKED:
        raise RuntimeError('model/fit import forbidden in saved-output verification')
    if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn')) or event in ('os.system', 'os.fork', 'os.forkpty', 'os.killpg'):
        raise RuntimeError('network/process execution forbidden')
    if event == 'os.kill' and args != (os.getpid(), signal.SIGALRM):
        raise RuntimeError('only own wall-guard signal allowed')


def recovered_fit_origin(args, fit, allowed, current):
    """Exact immutable failed origin; never reinterpret failure as success."""
    expected = {}
    for key, path in (('failed_fit_ledger', args.failed_fit_ledger),
                      ('failed_fit_receipt', args.failed_fit_receipt),
                      ('fit_progress', args.fit_progress)):
        actual = pin(path)
        require(allowed.get(actual['path']) == actual, 'failed-origin artifact must be an exact frozen pin: '+key)
        expected[key] = actual
    links = [v for v in current['config']['closed_parent_journals']
             if v['pin'] == expected['failed_fit_ledger']]
    require(len(links) == 1, 'failed-fit ledger must be an explicit closed parent')
    rows = [json.loads(line) for line in Path(args.failed_fit_ledger).read_text().splitlines() if line.strip()]
    require(independent_chain(rows) == links[0]['final_record_sha256'], 'failed-parent final chain differs')
    terminal = rows[-1]['data']
    require(rows[-1]['event'] == 'stage-finish' and terminal['stage'] == 'fit'
            and terminal['status'] == 'failed' and terminal['charged']['seconds'] >= 60.,
            'original fit must remain failed at its full reservation')
    require(terminal['observed']['neural_forwards'] is None and terminal['observed']['optimizer_updates'] is None,
            'failed fit observations must stay unknown')
    require(expected['failed_fit_receipt'] in terminal['proofs'], 'full failed receipt pin missing from terminal proofs')
    receipt = read(args.failed_fit_receipt)
    require(receipt['status'] == 'failed' and receipt['error']['type'] == 'TypeError'
            and 'int64' in receipt['error']['message'], 'exact serialization failure provenance required')
    require(receipt['observed']['neural_forwards'] is None and receipt['observed']['optimizer_updates'] is None,
            'failed receipt observations must stay unknown')
    require(fit.get('status') == 'recovered-from-saved-artifacts' and fit.get('original_fit_status') == 'failed',
            'recovered report must retain the failed fit disposition')
    provenance = fit['recovery_provenance']
    require(all(provenance.get(key) == value for key, value in expected.items()), 'recovered report failed-origin pins differ')
    require(all(v.get('last_step_preclip_gradients', 'missing') is None for v in fit['results'].values()),
            'unsaved final gradients must remain explicitly unavailable')
    return dict(original_fit_status='failed', observed_neural_forwards=None, observed_optimizer_updates=None,
                full_failed_charge_seconds=terminal['charged']['seconds'], failed_fit_receipt=expected['failed_fit_receipt'],
                failed_fit_ledger=expected['failed_fit_ledger'], fit_progress=expected['fit_progress'],
                final_failed_parent_chain=rows[-1]['record_sha256'], last_step_gradients='unavailable-not-saved',
                label_hash_scope='Recovery-time checksums against the sealed dataset; not a recovered pre-failure report.',
                saved_journal_scope='Historical completed durable prefix, not a successful fit disposition or new neural exposure.')


def verify_saved(np, args, allowed, current):
    checks = Checks(); inputs = {}
    def checked(path):
        p = pin(path)
        require(allowed.get(p['path']) == p, 'verification input is not an exact frozen/completed-stage pin: '+p['path'])
        inputs[p['path']] = p
        return p
    for p in (args.plan, args.recovered_result, args.baselines_dir/'result.json', args.fit_progress, args.baseline_progress):
        checked(p)
    plan, fit, base = read(args.plan), read(args.recovered_result), read(args.baselines_dir/'result.json')
    failed_origin = recovered_fit_origin(args, fit, allowed, current)
    for p in plan['pins']:
        require(pin(p['path']) == p, 'changed sealed learner source/data pin')
    checked(plan['dataset']); checked(plan['manifest'])
    arrays = npz(np, plan['dataset']); manifest = read(plan['manifest'])
    partitions = plan['split']['root_partitions']
    checks.check({k: len(v) for k, v in partitions.items()} == dict(train=12, state_held=6, family_held=4, joint=4), '26-root-partitions')
    checks.check(sorted(i for v in partitions.values() for i in v) == list(range(26)), 'unique-complete-root-partitions')
    checks.check(len(plan['codes']) == 7 and len(plan['train_codes']) == 5, 'seven-source-five-TRAIN')
    checks.check(fit['semantic_validated'] is False and base['semantic_validated'] is False, 'no-semantic-qualification')
    for key, saved in fit['true_label_hashes'].items():
        checks.check(array_hash(arrays[key]) == saved, 'immutable-labels/'+key)
    rawx, rawc = public_projection(np, arrays, manifest)
    check_scalers(np, checks, arrays, plan, rawx, rawc)
    support = support_audit(np, checks, arrays, manifest, plan)
    checks.check(np.array_equal(chosen_mask(np, arrays, manifest), arrays['chosen_only_target_mask']), 'genuine-chosen-only-mask-and-passive-N/A')
    checked(args.fit_dir/'program-inputs.npz'); programs = npz(np, args.fit_dir/'program-inputs.npz')
    full_bank = {k[5:]: v for k, v in programs.items() if k.startswith('full_')}
    restricted_bank = {k[11:]: v for k, v in programs.items() if k.startswith('restricted_')}
    checks.check(set(full_bank) == set(restricted_bank) and bool(full_bank), 'full-restricted-program-bank-schema')
    signatures = []
    for i, code in enumerate(plan['codes']):
        h = hashlib.sha256()
        for key in sorted(full_bank):
            if key != 'identity_indices':
                value = full_bank[key][i]
                h.update(key.encode()+str(value.dtype).encode()+str(value.shape).encode()+value.tobytes())
            checks.check(np.array_equal(restricted_bank[key][i], full_bank[key][i]) if code in plan['train_codes'] else
                         not np.count_nonzero(restricted_bank[key][i]), 'restricted-program-bank/'+code+'/'+key)
        signatures.append(h.hexdigest())
    checks.check(signatures == plan['semantic_tensor_sha256'], 'actual-source-bank-semantic-input-hashes')
    expected_ids = [plan['train_codes'].index(c)+1 if c in plan['train_codes'] else 0 for c in plan['codes']]
    checks.check(full_bank['identity_indices'].tolist() == expected_ids, 'TRAIN-ID-table-and-held-UNK')
    checked(args.fit_dir/'consumed-inputs.npz'); actual_inputs = npz(np, args.fit_dir/'consumed-inputs.npz')
    for arm in MAIN:
        x, c = normalized_inputs(np, rawx, rawc, plan['scalers'], arm)
        checks.check(np.array_equal(actual_inputs['x_'+arm], x), 'actual-consumed/'+arm+'/x')
        checks.check(np.array_equal(actual_inputs['c_'+arm], c), 'actual-consumed/'+arm+'/c')
    fullx, fullc = normalized_inputs(np, rawx, rawc, plan['scalers'], 'C1R1')
    checks.check(not conflicts(np, fullx, fullc, arrays, plan), 'C1R1-no-coobserved-label-conflicts')
    checked(args.fit_dir/'training-schedule.npz'); schedule = npz(np, args.fit_dir/'training-schedule.npz')
    checks.check(np.array_equal(schedule['train_indices'], partitions['train']), 'common-TRAIN-order')
    checks.check(schedule['seeds'].tolist() == list(SEEDS) and schedule['arms'].tolist() == list(ARMS), 'fixed-seed-arm-schedule')
    for key in ('source_cards', 'selected_candidate_indices'):
        checks.check(np.array_equal(schedule[key], arrays[key]), 'common-training-schedule/'+key)
    metrics, panels, initial_vectors = {}, {}, {}
    held = [i for i, code in enumerate(plan['codes']) if code not in plan['train_codes']]
    for seed in SEEDS:
        checked(args.fit_dir/f's{seed}-initial-checkpoint.npz')
        initial = npz(np, args.fit_dir/f's{seed}-initial-checkpoint.npz')
        master_hash = named_tensor_hash(initial)
        for arm in ARMS:
            identity = f's{seed}:{arm}'; saved = fit['results'][identity]; metrics[identity] = {}; panels[identity] = {}
            checks.check(saved['initial_state_sha256'] == master_hash, identity+'/all-weights-identical-initialization')
            checks.check(saved['master_initial_state_sha256'] == master_hash, identity+'/master-initialization-proof')
            checked(args.fit_dir/f's{seed}-{arm}-checkpoint.npz')
            weights = npz(np, args.fit_dir/f's{seed}-{arm}-checkpoint.npz')
            checks.check(set(weights) == set(initial), identity+'/same-allocated-graph')
            for name, value in weights.items():
                changed = int(np.count_nonzero(value != initial[name])); saved_movement = saved['weight_movement'][name]
                checks.metric(changed, saved_movement['changed'], identity+'/movement/'+name)
                delta = float(np.sqrt(np.sum((value-initial[name]).astype(np.float64)**2)))
                checks.metric(delta, saved_movement['delta_l2'], identity+'/movement-l2/'+name)
                if arm in ('ID-only', 'untrained-typed') and name.startswith(ENCODER):
                    checks.check(changed == 0, identity+'/frozen-encoder/'+name)
                if arm != 'ID-only' and name.startswith('identity.'):
                    checks.check(changed == 0, identity+'/unused-identity-frozen')
            for step in (0, 300):
                path = args.fit_dir/f's{seed}-{arm}-step{step}-predictions.npz'; checked(path); pred = npz(np, path)
                checks.check(pred['source'].shape == (26, 9) and pred['branch'].shape == (26, 8, 7) and pred['card_vectors'].shape == (7, 16), identity+f'/step{step}/prediction-ABI')
                checks.check(all(np.isfinite(pred[k]).all() for k in ('source', 'branch', 'card_vectors')), identity+f'/step{step}/finite')
                for key in ('source_cards', 'state_families', 'selected_candidate_indices'):
                    checks.check(np.array_equal(pred[key], arrays[key]), identity+f'/step{step}/row-order/'+key)
                metrics[identity][str(step)] = compare_heads(np, checks, pred, saved['evaluations'][str(step)], arrays, manifest, plan, identity+f'/step{step}')
                panel = narrow(np, pred['branch'], arrays, manifest, partitions); panels[identity][str(step)] = panel
                recorded = saved['evaluations'][str(step)]['narrow_estimands']
                checks.metric(panel['C']['mae'], recorded['C_LAW045_new_states_chosen_damage']['mae'], identity+f'/step{step}/C')
                for code, values in panel['R'].items():
                    for key in ('mae', 'contrast_mae', 'direction_accuracy'):
                        checks.metric(values[key], recorded['R_fresh_positive_parent_stat_variants_actual_endpoints'][code][key], identity+f'/step{step}/R/'+code+'/'+key)
                if step == 0:
                    initial_vectors[(seed, arm)] = pred['card_vectors']
                    if arm in MAIN:
                        checks.check(np.array_equal(pred['card_vectors'], initial_vectors[(seed, 'C0R0')]), identity+'/identical-initial-source-bank')
                if arm == 'untrained-typed' and step == 300:
                    checks.check(np.array_equal(pred['card_vectors'], initial_vectors[(seed, arm)]), identity+'/frozen-source-bank')
                if arm == 'ID-only':
                    checks.check(np.count_nonzero(pred['card_vectors'][held]) == 0, identity+f'/step{step}/held-ID-UNK0')
    baseline_metrics = {}
    for name in ('zero', 'train_mean', *MAIN):
        path = args.baselines_dir/(name+'-predictions.npz'); checked(path); pred = npz(np, path)
        baseline_metrics[name] = compare_heads(np, checks, pred, base['evaluations'][name], arrays, manifest, plan, 'baseline/'+name)
        if name in MAIN:
            checks.check(np.count_nonzero(pred['source_design'][[i for i, c in enumerate(arrays['source_cards']) if str(c) not in plan['train_codes']], -5:]) == 0, 'ridge/'+name+'/held-ID-zero')
    import binding_transfer_report_accounting as A
    fcounts = A.progress_counts(args.fit_progress, 'fit'); bcounts = A.progress_counts(args.baseline_progress, 'baselines')
    checks.check(fcounts == dict(optimizer_updates=5400, neural_forwards=5436, training_forwards=5400, evaluation_forwards=36), 'durable-fit-counts')
    checks.check(bcounts['numerical_fits'] == base['head_fit_attempts'] == 64 and base['actual_lstsq_solver_calls'] <= 64, 'durable-fixed-fit-counts')
    checks.check(current['cumulative']['charged_native_applies'] <= 208 and current['cumulative']['charged_seconds'] <= 197.01759783166926 and current['cumulative']['observed_native_applies'] is None, 'carried-global-local-bound')
    checks.check(current['config']['caps']['seconds'] == 13. and current['config']['caps']['native_applies'] == 0 and
                 current['config']['parent']['charged_native_applies'] == 208 and current['config']['parent']['charged_seconds'] == 184.01759783166926 and
                 current['config']['parent']['historical_modal_ceiling_usd'] == 100. and current['config']['parent']['historical_modal_minimum_reserve_usd'] == 25. and
                 current['config']['parent']['paid_spend_usd'] == 0., 'unchanged-cumulative-cap-failed-charge-dollar-carry')
    protection = read(A.PRESERVATION['path']); checks.check(pin(A.PRESERVATION['path']) == A.PRESERVATION, 'original-preservation-snapshot-pin')
    original_pins = {p['path']: {k: p[k] for k in ('path', 'sha256', 'bytes')}
                     for p in protection['protected_files']+protection['additional_protected_artifacts']}
    checks.check(len(original_pins) == 80, 'original-protected-unique-file-count')
    for path, expected in original_pins.items():
        checks.check(pin(path) == expected, 'original-protected-bytes/'+path)
    contrast = {}
    for seed in SEEDS:
        repaired = panels[f's{seed}:C1R1']['300']
        contrast[str(seed)] = dict(C=improvement(repaired['C']['mae'], panels[f's{seed}:C0R1']['300']['C']['mae']),
                                   R=improvement(repaired['R_equal_variant_mae'], panels[f's{seed}:C1R0']['300']['R_equal_variant_mae']))
    return dict(schema='jepa-binding-transfer-independent-verification/1', status='PASS' if not checks.mismatches else 'FAIL',
                check_count=checks.count, mismatches=checks.mismatches, partitions={k: len(v) for k, v in partitions.items()},
                per_seed_contrasts=contrast, narrow_estimands=panels, training_support=support, recomputed_head_metrics=metrics,
                recomputed_baseline_head_metrics=baseline_metrics, counter_proofs=dict(fit=fcounts, baselines=bcounts),
                input_pins=list(inputs.values()), recovered_failed_fit_origin=failed_origin,
                saved_fit_journal_scope='Historical durable prefix only; original failed fit observations remain unknown and no new neural work is allocated.',
                semantic_validated=False, generic_semantic_gate='UNSUPPORTED',
                limitations=['C is seen-program fresh-state performance; R is two variants of one broad positive-stat family.',
                             'Chosen-only metrics rescore actual-endpoint-trained predictions, not a historical objective fit.',
                             'HP/power coordinates, repeated roots and program variants are dependent observations.',
                             'Auxiliary exhaustion has one positive TRAIN template; all auxiliary metrics are descriptive.',
                             'Saved predictions and frozen source/initialization proofs are checked; no optimizer trajectory replay.'],
                native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_spend_usd=0)


def run(args):
    import binding_transfer_report_accounting as A
    with A.lease() as (stream, rows, current):
        allowed = {p['path']: p for p in current['config']['pins']}
        for row in rows:
            if row['event'] == 'stage-finish' and row['data']['status'] == 'completed':
                for p in row['data']['proofs']:
                    allowed[p['path']] = p
        required = [args.plan, args.recovered_result, args.baselines_dir/'result.json', args.fit_progress, args.baseline_progress, args.failed_fit_ledger, args.failed_fit_receipt]
        metadata = dict(argv=[str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]],
                        outputs=[str(args.out.resolve()), str(args.receipt.resolve())],
                        input_pins=[allowed[str(p.resolve())] for p in required if str(p.resolve()) in allowed],
                        guard=dict(cpu_workers=1, rss_bytes=1073741824))
        started = time.monotonic(); guard = None; active = [False]; status = 'failed'; error = None; proofs = []
        def audit(event, values):
            if active[0]:
                audit_event(event, values)
        sys.addaudithook(audit)
        try:
            A.start(stream, rows, 'verify', metadata)
            require(pin(HERE/'binding_transfer_verify.py')['sha256'] == ORIGINAL_VERIFIER_SHA, 'exact frozen scientific ancestor verifier')
            require(pin(HERE/'binding_transfer_next_verify.py')['sha256'] == PRIOR_LINKED_VERIFIER_SHA, 'exact frozen linked verifier')
            require(pin(HERE/'binding_transfer_repair_verify.py')['sha256'] == PREDECESSOR_VERIFIER_SHA, 'exact frozen report predecessor verifier')
            require(pin(A.__file__) == current['config']['source'], 'explicit new accounting source route')
            require(all(str(p.resolve()) in allowed for p in required), 'all seven verifier inputs must be exact frozen or completed-stage pins')
            import effect_identifiability_fit as E
            require(pin(E.__file__)['sha256'] == GUARD_SHA, 'exact audited own-process guard')
            parent_chain = independent_chain(rows)
            require(not args.out.exists() and not args.receipt.exists(), 'exclusive verification outputs; no retry')
            require(not any(name.split('.')[0] in BLOCKED for name in sys.modules), 'no preloaded model/fit library')
            remaining = 5.-(time.monotonic()-started)
            require(remaining > 0, 'verification preflight exhausted stage quota')
            guard = E.Guard(remaining); active[0] = True
            with guard:
                import numpy as np
                result = verify_saved(np, args, allowed, A.state(rows))
                result['independent_campaign_chain_at_verification_intent'] = parent_chain
                result['versioned_verifier_provenance'] = dict(
                    predecessor=pin(HERE/'binding_transfer_repair_verify.py'),
                    prior_linked=pin(HERE/'binding_transfer_next_verify.py'),
                    scientific_ancestor=pin(HERE/'binding_transfer_verify.py'), accounting_module=ACCOUNTING_MODULE,
                    accounting_source=pin(A.__file__), verifier_source=pin(__file__),
                    change_scope='Accounting/budgets, explicit recovered-result route and failed-fit provenance only; scientific checks unchanged.')
                write_new(args.out, result); proofs = [pin(args.out)]
                require(result['status'] == 'PASS', 'saved-output verification mismatches')
            status = 'completed'
        except BaseException as exc:
            pending = A.state(rows)['pending']
            if pending is None or pending['stage'] != 'verify' or pending['owner_pid'] != os.getpid():
                raise
            error = dict(type=type(exc).__name__, message=str(exc))
        finally:
            active[0] = False
        elapsed = time.monotonic()-started
        if elapsed > 5:
            status = 'failed'; error = error or dict(type='BudgetExceeded', message='verification exceeded5seconds')
        receipt = dict(status=status, error=error, active_seconds=elapsed, guard=guard.receipt() if guard else None,
                       native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_spend_usd=0,
                       source=pin(__file__), predecessor_verifier_sha256=PREDECESSOR_VERIFIER_SHA,
                       scientific_ancestor_sha256=ORIGINAL_VERIFIER_SHA,
                       accounting_module=ACCOUNTING_MODULE, outputs=proofs, semantic_validated=False)
        if not args.receipt.exists():
            write_new(args.receipt, receipt); proofs.append(pin(args.receipt))
        finished = A.finish(stream, rows, status, elapsed, observed=A.zero_counts(), proofs=proofs,
                            cleanup_verified=True, execution_ended=True)
        require(status == 'completed' and 'verify' in finished['completed_stages'], 'failed bounded verification retained')
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'fit-dir', 'fit-progress', 'baselines-dir', 'baseline-progress', 'out', 'receipt', 'recovered-result', 'failed-fit-ledger', 'failed-fit-receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), allow_nan=False))


if __name__ == '__main__':
    main()
