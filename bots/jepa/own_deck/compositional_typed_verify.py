"""Independent saved-only verification of the synthetic compositional assay.

Only the caller-supplied NumPy module reads saved arrays. No learner, model,
converter, engine, optimizer or scoring implementation is imported or invoked.
The caller owns the sealed verification stage, lease, resource guard and outputs.
"""
import copy
import hashlib
import itertools
import json
import math
import os
from pathlib import Path

SCHEMA = 'jepa-compositional-typed-verification/1'
SEEDS = (17, 29, 43)
ARMS = ('old-no-id', 'old-with-id', 'new-no-id', 'new-with-id')
AXES = ('owner_opponent', 'arena_space', 'cap_is_3', 'amount_is_3', 'op_heal')
FEATURES = ('owner_self', 'owner_opponent', 'arena_ground', 'arena_space',
            'printed_cost', 'damage', 'hp', 'is_intended')
PRINTED = ('cost', 'hp', 'power', 'unique', 'upgradePower', 'upgradeHp',
           'aspects', 'traits', 'arena', 'keywords', 'types')
COUNTS = dict(neural_forwards=3624, training_forwards=3600,
              evaluation_forwards=24, backwards=3600,
              optimizer_updates=3600, numerical_fits=2)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_new(path, value):
    raw = json.dumps(value, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def close(actual, expected, label='value', tolerance=1e-8):
    """Strict recursive shape/type/knownness comparison, with numeric tolerance."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), label + ': object keys differ')
        for key in expected:
            close(actual[key], expected[key], label + '.' + str(key), tolerance)
    elif isinstance(expected, (list, tuple)):
        require(isinstance(actual, (list, tuple)) and len(actual) == len(expected), label + ': list shape differs')
        for i, value in enumerate(expected):
            close(actual[i], value, label + '[' + str(i) + ']', tolerance)
    elif expected is None or type(expected) is bool or isinstance(expected, str):
        require(type(actual) is type(expected) and actual == expected, label + ': categorical/unknown value differs')
    else:
        require(type(actual) in (int, float) and math.isfinite(actual) and
                math.isclose(actual, expected, abs_tol=tolerance, rel_tol=tolerance), label + ': numeric value differs')


def scalar(value):
    require(type(value) in (int, float) and math.isfinite(value), 'finite explicit numeric input required')
    return float(value)


def parse_program(program):
    """Rebuild the complete allowed IR from bits, rather than trust factor labels."""
    bits = program['bits']
    require(len(bits) == 5 and all(type(b) is int and b in (0, 1) for b in bits), 'five binary coordinates required')
    owner, arena, cap, amount, op = ('opponent' if bits[0] else 'any',
        'space' if bits[1] else 'ground', 3 if bits[2] else 2,
        3 if bits[3] else 1, 'heal' if bits[4] else 'damage')
    factors = dict(owner=owner, arena=arena, cap=cap, amount=amount, op=op)
    ability = dict(trigger='event', title='Elementary effect', costs=[],
        targetResolver=dict(owner=owner, type='unit', zone='arena', arena=arena,
            predicate=dict(kind='binary', op='<=', left=dict(kind='ref', path=['card', 'cost']),
                           right=dict(kind='const', value=cap))),
        effect=dict(kind=op, target='chosen', amount=dict(kind='const', value=amount)))
    abilities = dict(card=[ability], unit=[], leader=[])
    require(program['factors'] == factors and program['raw_card']['abilities'] == abilities and
            program['synthetic'] is True and program['program_hash'] == digest(abilities),
            'program factors/hash are not the complete literal typed program')
    return [float(owner == 'any'), float(owner == 'opponent'), float(arena == 'ground'),
            float(arena == 'space'), float(cap), float(op == 'damage'), float(op == 'heal'), float(amount)]


def parity(programs):
    bits = [p['bits'] for p in programs]
    require(len(programs) == 32 and {tuple(b) for b in bits} == set(itertools.product((0, 1), repeat=5)),
            'complete unique five-factor product required')
    for i, p in enumerate(programs):
        require(p['index'] == i and p['partition'] == ('held' if sum(bits[i]) % 2 else 'train'),
                'complete-program parity split differs')
    for size in range(1, 5):
        for axes in itertools.combinations(range(5), size):
            for odd in (0, 1):
                observed = {tuple(b[a] for a in axes) for b in bits if sum(b) % 2 == odd}
                require(observed == set(itertools.product((0, 1), repeat=size)), 'TRAIN/HELD proper-subset support missing')
    require(len({p['code'] for p in programs}) == len({p['program_hash'] for p in programs}) == 32,
            'alias/duplicate program crosses the split')
    printed = [{key: p['raw_card']['card'].get(key) for key in PRINTED} for p in programs]
    require(all(p == printed[0] for p in printed), 'printed source metadata reveals program factors')
    return bits


def public_features(case, roles):
    """The only consumed scene fields; neither future/menu nor source ID is read."""
    projections, refs, intent = case['before']['projections'], case['refs'], case['declared_intent']
    source = projections['source']; own = source['owner']
    require(own == 'p1' and source['known']['owner'] is True and
            intent.get('requires_target') is True and intent['ref'] in roles and
            refs[intent['ref']] == intent['id'], 'explicit BEFORE actor/intended equality required')
    require(len({refs[r] for r in roles}) == len(roles), 'candidate identities must be distinct')
    result, records = [], []
    for role in roles:
        p = projections[role]
        require(p['id'] == refs[role] and p['present'] is True and p['is_unit'] is True and
                p['in_arena'] is True and p['owner'] in ('p1', 'p2') and p['zone'] in ('ground', 'space') and
                all(p['known'].get(k) is True for k in ('identity', 'owner', 'printed_cost', 'damage', 'hp')),
                'known physical arena candidate required')
        cost, damage, hp = (scalar(p[key]) for key in ('printed_cost', 'damage', 'hp'))
        require(cost in (2., 3., 4.) and hp == 10. and 0 <= damage < hp, 'fixed live-unit lattice required')
        row = [float(p['owner'] == own), float(p['owner'] != own), float(p['zone'] == 'ground'),
               float(p['zone'] == 'space'), cost, damage, hp, float(p['id'] == intent['id'])]
        result.append(row)
        records.append(dict(owner=p['owner'], arena=p['zone'], printed_cost=cost, damage=damage,
            hp=hp, is_intended=bool(row[7]), known={k: True for k in ('identity', 'owner', 'printed_cost', 'damage', 'hp')}))
    require(sum(row[7] for row in result) == 1., 'one intended public candidate required')
    return result, dict(acting_owner=own, candidates=records,
                       input_scope='BEFORE owner/arena/cost/damage/HP and intended equality only')


def reference(fields, features):
    """Deterministic public typed comparator; takes no native labels or code."""
    output = []
    for row in features:
        eligible = (bool(fields[0]) or bool(row[1])) and bool(row[2 if fields[2] else 3]) and row[4] <= fields[4]
        effect = fields[7] if fields[5] else -min(fields[7], row[5])
        output.append([float(eligible), effect if eligible and row[7] else 0.])
    return output


def native_case(case, world, roles):
    """Derive membership from the reached menu, and effects from actual endpoints."""
    require(case.get('engineError') is None and case['publicSnapshotRoundtripExact'] is True,
            'native fixture did not roundtrip without error')
    features, record = public_features(case, roles)
    refs, before, intent = case['refs'], case['before'], case['declared_intent']
    selected = roles.index(intent['ref'])
    require(before['decision'] == 'Window' and before['projections']['source']['zone'] == 'hand' and
            before['projections']['source']['id'] == refs['source'] and
            before['projections']['source']['code'] == case['card'], 'actual own-hand event source required')
    players = before['state']['players']
    require(all(players[p]['deck'] == [] for p in ('p1', 'p2')) and
            players['p2']['hand'] == players['p2']['resources'] == [] and
            [v['id'] for v in players['p1']['hand']] == [refs['source']], 'private pile or undeclared hand information')
    actual_ids = [v['id'] for p in ('p1', 'p2') for arena in ('ground', 'space') for v in players[p][arena]]
    require(len(actual_ids) == len(set(actual_ids)) == 16 and set(actual_ids) == {refs[r] for r in roles},
            'unrepresented physical public unit')
    lattice = {}
    for role, row in zip(roles, features):
        p, spec = before['projections'][role], world['arena_cards'][role]
        require(p['code'] == spec['code'] and p['owner'] == spec['owner'] and p['zone'] == spec['arena'] and
                row[4] == spec['printed_cost'] and row[5] == spec['damage'] and scalar(p['power']) == 0.,
                'BEFORE physics differs from declared synthetic scene')
        key = (p['owner'], p['zone'], row[4]); lattice[key] = lattice.get(key, 0) + 1
    require(lattice == {(owner, arena, float(cost)): 2 if cost == 2 else 1
            for owner, arena, cost in itertools.product(('p1', 'p2'), ('ground', 'space'), (2, 3, 4))},
            'complete balanced synthetic unit lattice required')
    captures, last, chosen, cancelled, committed_selection = [before], before, 0, 0, 0
    for i, step in enumerate(case['steps']):
        require(step['before'] == last and step['action'] in last['offeredActions'], 'discontinuous/unoffered native action')
        stage, action = step['stage'], step['action']
        if i == 0:
            require(stage == 'play-own-hand' and action == case['playAction'] and action.get('card') == refs['source'],
                    'first native action is not the declared source play')
        elif stage == 'chosen-target':
            require(last == case['targetPrompt'] and action == case['targetAction'] and action.get('card') == intent['id'],
                    'substituted/undeclared native target')
            chosen += 1
        elif stage == 'commit-one-selection':
            require(chosen == 1 and action.get('arg') == 'done' and action.get('label') == 'Done',
                    'unexpected selection commit')
            committed_selection += 1
        elif stage == 'decline-unoffered-target':
            require(action.get('arg') == 'cancel' and action.get('label') == 'Cancel' and action == case['declineAction'],
                    'invented decline action')
            cancelled += 1
        else:
            raise ValueError('unreviewed native action stage')
        last = step['after']; captures.append(last)
    prompt = case['targetPrompt']
    require(prompt in captures and prompt['decision'] == 'AbilityTarget' and last == case['lastObserved'] and
            len(case['steps']) == case['applyCalls'] <= 4 and chosen <= 1 and cancelled <= 1 and committed_selection <= 1,
            'native prompt/terminal/application count differs')
    target = [[float(any(a.get('card') == refs[r] for a in prompt['offeredActions'])), 0.] for r in roles]
    mask = [[1., 0.] for _ in roles]
    require(type(case['intentOffered']) is bool and case['intentOffered'] == bool(target[selected][0]) and
            type(case['intendedTargetCommitted']) is bool and case['intendedTargetCommitted'] == bool(chosen),
            'native membership/commit flags differ')
    terminal = case['terminalClassification']
    if terminal == 'unoffered-prompt-only':
        require(last == prompt and case['final'] is None and not chosen and not cancelled and not target[selected][0] and
                case['completion'] == case['intentResolution'] == 'unoffered-observation-only' and
                not any(a.get('arg') == 'cancel' and a.get('label') == 'Cancel' for a in prompt['offeredActions']),
                'prompt-only future or Cancel fabricated')
    else:
        require(terminal in ('settled-committed', 'settled-cancelled') and case['final'] == last and
                last['settled'] is True and case['completion'] == 'settled' and
                ((terminal == 'settled-committed') == bool(chosen)) and
                ((terminal == 'settled-cancelled') == bool(cancelled)) and
                case['intentResolution'] == ('committed' if chosen else 'unoffered-declined'),
                'unsettled or unclassified native endpoint')
        if chosen:
            require(target[selected][0] == 1., 'committed target was unoffered')
            for j, role in enumerate(roles):
                a, z = before['projections'][role], last['projections'][role]
                require(a['id'] == z['id'] == refs[role], 'physical endpoint changed identity')
                if (z.get('present') is True and z.get('in_arena') is True and z.get('zone') == a['zone'] and
                    z.get('known', {}).get('damage') is True and z.get('known', {}).get('hp') is True and
                    scalar(z['damage']) < scalar(z['hp'])):
                    target[j][1] = scalar(z['damage']) - scalar(a['damage']); mask[j][1] = 1.
    require(bool(chosen) == (world['root_variant'] != 3), 'predeclared eligible/invalid root did not complete as planned')
    # Independently rename only equality-bearing public IDs; poison unconsumed fields.
    renamed = dict(refs={k: 'opaque-' + str(i) for i, k in enumerate(refs)},
                   declared_intent=dict(intent), before=dict(projections={k: dict(v) if v is not None else None
                       for k, v in before['projections'].items()}))
    renamed['declared_intent']['id'] = renamed['refs'][intent['ref']]
    for role, p in renamed['before']['projections'].items():
        if p is not None:
            p['id'] = renamed['refs'][role]; p['code'] = 'opaque-code'
    renamed['final'] = {'poison': True}; renamed['targetPrompt'] = {'poison': True}
    renamed['before']['state'] = {'hidden': 'poison'}
    renamed_features, _ = public_features(renamed, roles)
    require(features == renamed_features, 'actual consumed public fields are identity/future dependent')
    return dict(features=features, record=record, targets=target, mask=mask, selected=selected,
                rename_sha256=digest(features), terminal=terminal)


def native_journal(records, raw):
    require(records and records[0]['schema'] == 'jepa-compositional-typed-apply-journal/1' and
            records[0]['planSha256'] == raw['collectionPlanSha256'] and
            records[0]['sourceRevision'] == raw['sourceRevision'], 'native trace header provenance differs')
    n, offset = 0, 1
    for case in raw['cases']:
        for step in case['steps']:
            n += 1; a, z = records[offset:offset + 2]; offset += 2
            require(a['phase'] == 'beforeApply' and z['phase'] == 'afterApply' and
                    a['applyCall'] == z['applyCall'] == n and a['context'] == z['context'] ==
                    'world-' + str(case['world_id']) + '-' + case['card'] and
                    a['branch'] == z['branch'] == step['stage'] and a['before'] == step['before'] and
                    a['offeredAction'] == step['action'] and z['after'] == step['after'],
                    'native trace does not exactly witness every physical action')
        require(records[offset]['phase'] == 'contextComplete' and records[offset]['case'] == case,
                'native root completion record differs'); offset += 1
    require(offset == len(records) and n == raw['applyCalls'] <= 512, 'extra/missing native call or event')
    return dict(native_applies=n, roots=len(raw['cases']), paired_actions=True)


def score(prediction, targets, masks, selected, indices):
    positive = negative = tp = tn = 0; errors = []; correct = 0
    classes = {name: [0, 0] for name in ('positive', 'negative', 'zero')}
    for i in indices:
        for j, target in enumerate(targets[i]):
            if masks[i][j][0]:
                y, p = target[0], prediction['eligibility'][i][j]
                require(y in (0, 1) and math.isfinite(float(p)) and 0 <= p <= 1, 'binary truth/finite probability required')
                positive += int(y == 1); negative += int(y == 0)
                tp += int(y == 1 and p >= .5); tn += int(y == 0 and p < .5)
        j = int(selected[i])
        if masks[i][j][1]:
            y, p = float(targets[i][j][1]), float(prediction['damage'][i][j])
            require(math.isfinite(p), 'finite native-unit prediction required')
            truth = 1 if y > 0 else -1 if y < 0 else 0
            predicted = 1 if p > .25 else -1 if p < -.25 else 0
            ok = int(truth == predicted); correct += ok; errors.append(abs(y - p))
            name = 'positive' if truth > 0 else 'negative' if truth < 0 else 'zero'
            classes[name][0] += 1; classes[name][1] += ok
    return dict(roots=len(indices), eligibility=dict(positive=positive, negative=negative,
        true_positive=tp, true_negative=tn, balanced_accuracy=(tp / positive + tn / negative) / 2 if positive and negative else None),
        damage=dict(known=len(errors), mae=sum(errors) / len(errors) if errors else None,
            max_abs_error=max(errors) if errors else None, sign_accuracy=correct / len(errors) if errors else None,
            classes={key: dict(count=value[0], recall=value[1] / value[0] if value[0] else None) for key, value in classes.items()}))


def evaluations(prediction, targets, masks, selected, q, bits, train, held):
    evaluate = lambda ix: score(prediction, targets, masks, selected, ix)
    return dict(train=evaluate(train), held=evaluate(held),
        held_axes={f'{name}={value}': evaluate([i for i in held if bits[int(q[i])][axis] == value])
                   for axis, name in enumerate(AXES) for value in (0, 1)},
        held_op_amount={f'op_heal={op},amount_is_3={amount}': evaluate([i for i in held
            if bits[int(q[i])][4] == op and bits[int(q[i])][3] == amount]) for op in (0, 1) for amount in (0, 1)})


def gate(noid, withid, new):
    checks = []
    for key, metric in noid['held_axes'].items():
        value, other = metric['eligibility']['balanced_accuracy'], withid['held_axes'][key]['eligibility']['balanced_accuracy']
        checks.append(dict(panel=key, head='eligibility', value=value, ID_on=other,
            absolute=value is not None and value >= .95,
            identity_drop=value is not None and other is not None and other - value <= .02 + 1e-12))
    for key, metric in noid['held_op_amount'].items():
        d, other = metric['damage'], withid['held_op_amount'][key]['damage']; zero = d['classes']['zero']['recall']
        heal = key.startswith('op_heal=1,')
        zero_ok = zero is not None and zero >= .95 if heal else d['classes']['zero']['count'] == 0
        checks.append(dict(panel=key, head='damage', mae=d['mae'], sign_accuracy=d['sign_accuracy'], zero_recall=zero,
            zero_scope='Required healthy-zero recall' if heal else 'Predeclared N/A: damage op has no native-zero intended outcomes',
            absolute=d['mae'] is not None and d['mae'] <= .25 and d['sign_accuracy'] is not None and d['sign_accuracy'] >= .95 and zero_ok,
            identity_drop=d['mae'] is not None and other['mae'] is not None and d['mae'] - other['mae'] <= .05 + 1e-12))
    absolute, identity = all(c['absolute'] for c in checks), all(c['identity_drop'] for c in checks)
    return dict(passed=absolute and (identity or not new), absolute_passed=absolute,
                identity_passed=identity, identity_required=new, checks=checks)


def comparative(old, new):
    ob, nb = old['eligibility']['balanced_accuracy'], new['eligibility']['balanced_accuracy']
    od, nd = old['damage']['mae'], new['damage']['mae']
    complete = all(v is not None for v in (ob, nb, od, nd))
    oe = ((1 - ob) + od / 3) / 2 if complete else None
    ne = ((1 - nb) + nd / 3) / 2 if complete else None
    return dict(old_balanced_accuracy=ob, new_balanced_accuracy=nb, old_damage_mae=od, new_damage_mae=nd,
        old_composite_error=oe, new_composite_error=ne, relative_supported=complete and oe > 0,
        passed=complete and oe > 0 and ne <= .9 * oe and nb >= ob - 1e-6 and nd <= od + 1e-6)


def loss_statistics(targets, masks, selected, q, fields, train):
    counts = [0, 0]; strata = {}; known = []; weights = [0.] * len(targets)
    for i in train:
        for j in range(len(targets[i])):
            if masks[i][j][0]: counts[int(targets[i][j][0])] += 1
        j = int(selected[i])
        if masks[i][j][1]:
            y = float(targets[i][j][1]); f = fields[int(q[i])]
            key = ('heal' if f[6] else 'damage', int(f[7]), 'zero' if y == 0 else 'nonzero')
            strata.setdefault(key, []).append(i); known.append(dict(root=i, value=y, stratum=list(key)))
    require(all(counts) and known, 'TRAIN objective lacks native balanced support')
    for ix in strata.values():
        for i in ix: weights[i] = len(known) / (len(strata) * len(ix))
    return dict(eligibility_class_counts=counts, eligibility_class_weights=[sum(counts) / (2 * n) for n in counts],
        damage_weights=weights, damage_observations=known,
        strata=[dict(key=list(k), roots=v, count=len(v), weight=weights[v[0]]) for k, v in sorted(strata.items())], train_roots=train)


def array_hash(array):
    return hashlib.sha256(str(array.dtype).encode() + str(array.shape).encode() + array.tobytes()).hexdigest()


def named_hash(values):
    return digest({key: array_hash(values[key]) for key in sorted(values)})


def load_npz(np, path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def tokenise(value, path=()):
    require(len(path) <= 32, 'semantic path cap exceeded')
    if isinstance(value, dict):
        yield path, 'node', 'object'
        for key in sorted(value): yield from tokenise(value[key], path + (key,))
    elif isinstance(value, list):
        yield path, 'length', len(value)
        for i, child in enumerate(value): yield from tokenise(child, path + (i,))
    elif type(value) is bool: yield path, 'boolean', value
    elif type(value) in (int, float): yield path, 'number', float(value)
    elif isinstance(value, str): yield path, 'enum', value
    elif value is None: yield path, 'null', 'null'
    else: raise ValueError('non-typed semantic value')


def bank_audit(np, programs, contract, consumed):
    documents = []
    for p in programs:
        row = p['raw_card']; ability = copy.deepcopy(row['abilities']['card'][0]); ability.pop('title')
        documents.append(dict(role='main', printed={k: copy.deepcopy(row['card'].get(k)) for k in PRINTED},
            keywordValues=copy.deepcopy(row['keywordValues']), attachCondition=copy.deepcopy(row.get('attachCondition')),
            abilities=dict(card=[ability], unit=[], leader=[])))
    close(contract['documents'], documents, 'canonical semantic documents')
    all_tokens = [list(tokenise(doc)) for doc in documents]
    require(all(len(tokens) <= 512 for tokens in all_tokens), 'semantic token cap exceeded')
    symbols = dict(path=['PAD', *sorted({('index:' if type(k) is int else 'key:') + str(k)
        for tokens in all_tokens for path, _, _ in tokens for k in path})],
        type=['PAD', 'node', 'length', 'number', 'boolean', 'enum', 'null'],
        value=['PAD', 'NUMBER', *sorted({kind + ':' + str(value) for tokens in all_tokens
            for _, kind, value in tokens if kind not in ('number', 'length')})])
    close(contract['symbols'], symbols, 'complete public vocabulary')
    train_tokens = [tokens for p, tokens in zip(programs, all_tokens) if p['partition'] == 'train']
    require({(path, kind, value) for tokens in all_tokens for path, kind, value in tokens if kind not in ('number', 'length')}
            == {(path, kind, value) for tokens in train_tokens for path, kind, value in tokens if kind not in ('number', 'length')},
            'HELD-only categorical atoms or paths admitted')
    numbers = [value for tokens in train_tokens for _, kind, value in tokens if kind in ('number', 'length')]
    scale = max(1., float(np.std(numbers)))
    close(contract['numeric_scale'], scale, 'common TRAIN-only literal scale')
    lookup = {k: {v: i for i, v in enumerate(values)} for k, values in symbols.items()}
    train_programs = [i for i, p in enumerate(programs) if p['partition'] == 'train']
    identity = np.asarray([train_programs.index(i) + 1 if i in train_programs else 0 for i in range(32)], np.int64)
    shape = dict(path_ids=(32, 512, 32), path_lengths=(32, 512), type_ids=(32, 512), value_ids=(32, 512),
                 numeric=(32, 512, 2), token_mask=(32, 512), slot_mask=(32,), identity_indices=(32,))
    bank = {k: np.zeros(v, np.float32 if k in ('numeric', 'token_mask', 'slot_mask') else np.int64) for k, v in shape.items()}
    bank['slot_mask'][:] = 1; bank['identity_indices'][:] = identity
    for slot, tokens in enumerate(all_tokens):
        for j, (path, kind, value) in enumerate(tokens):
            ids = [lookup['path'][('index:' if type(k) is int else 'key:') + str(k)] for k in path]
            bank['path_ids'][slot, j, :len(ids)] = ids; bank['path_lengths'][slot, j] = len(ids)
            bank['type_ids'][slot, j] = lookup['type'][kind]
            bank['value_ids'][slot, j] = lookup['value']['NUMBER' if kind in ('number', 'length') else kind + ':' + str(value)]
            bank['token_mask'][slot, j] = 1
            if kind in ('number', 'length'):
                bank['numeric'][slot, j] = (value / scale, np.sign(value) * np.log1p(abs(value)))
    held = [i for i in range(32) if i not in train_programs]
    for key, value in bank.items():
        require(np.array_equal(consumed['old_' + key], value), 'actual old semantic tensor differs: ' + key)
        restricted = value.copy(); restricted[held] = 0
        require(np.array_equal(consumed['old_train_' + key], restricted), 'HELD semantic slot exposed during TRAIN: ' + key)
    require(np.array_equal(consumed['identity_indices'], identity) and contract['identity_indices'] == identity.tolist(), 'identity table or HELDUNK differs')
    require(contract['semantic_rename_sha256'] == [digest(doc) for doc in documents] and
            contract['semantic_rename_invariance'] is True, 'semantic source rename proof differs')
    return dict(vocabulary_all_seen_in_TRAIN=True, numeric_scale=scale, held_slots_masked=True,
                metadata_identity_excluded=True, original_and_renamed_semantic_hashes=[digest(d) for d in documents])


def progress_audit(progress):
    forwards, updates, backwards = [], [], []
    current_forward = current_update = None
    per_arm = {}
    for entry in progress:
        event = entry['event']; key = (entry['seed'], entry['arm'])
        require(key[0] in SEEDS and key[1] in ARMS, 'unfrozen seed/arm in actual fit journal')
        stat = per_arm.setdefault(key, dict(train=0, evaluate=0, steps=[]))
        if event == 'forward-intent':
            require(current_forward is None and entry['global_forward'] == len(forwards) + 1, 'unpaired forward intent')
            current_forward = entry; forwards.append(entry)
            require(entry['kind'] in ('train', 'evaluate'), 'unknown forward kind')
            stat[entry['kind']] += 1
        elif event == 'forward-complete':
            require(current_forward is not None and all(entry[k] == current_forward[k] for k in ('global_forward', 'seed', 'arm', 'step')), 'forward return differs')
            current_forward = None
        elif event == 'backward-intent':
            require(entry['global_backward'] == len(backwards) + 1, 'backward sequence differs'); backwards.append(entry)
        elif event == 'optimizer-intent':
            require(current_update is None and entry['global_update'] == len(updates) + 1, 'unpaired update intent')
            current_update = entry
        elif event == 'optimizer-complete':
            require(current_update is not None and all(entry[k] == current_update[k] for k in ('global_update', 'seed', 'arm', 'step')),
                    'optimizer return differs')
            require(all(math.isfinite(entry[k]) for k in ('loss', 'eligibility_loss', 'damage_loss', 'preclip_gradient_norm')),
                    'nonfinite saved loss/gradient')
            updates.append(entry); stat['steps'].append(entry['step']); current_update = None
        else: raise ValueError('unreviewed fit progress event')
    require(current_forward is current_update is None and len(forwards) == 3624 and len(updates) == len(backwards) == 3600,
            'exact completed neural/update/backward panel differs')
    trained = [r for r in forwards if r['kind'] == 'train']
    for forward, backward, update in zip(trained, backwards, updates):
        require(all(forward[k] == backward[k] == update[k] for k in ('seed', 'arm', 'step')),
                'forward/backward/update input pairing differs')
    for seed in SEEDS:
        for arm in ARMS:
            stat = per_arm[(seed, arm)]
            require(stat == dict(train=300, evaluate=2, steps=list(range(1, 301))), 'arm schedule differs')
            require([r['step'] for r in forwards if r['seed'] == seed and r['arm'] == arm and r['kind'] == 'evaluate'] == [0, 300],
                    'unfrozen evaluation/held stopping schedule')
    return dict(neural_forwards=3624, training_forwards=3600, evaluation_forwards=24, backwards=3600, optimizer_updates=3600)


def budget_audit(ledger, spec, progress):
    previous = '0' * 64; pending = None; stages = {}; tokens = {}; fit_tokens = {}; fit_finish = None
    for i, row in enumerate(ledger):
        body = {k: v for k, v in row.items() if k != 'record_sha256'}
        require(row['sequence'] == i and row['previous_sha256'] == previous and
                row['record_sha256'] == digest(body) and row['schema'] == 'jepa-sealed-budget-journal/1', 'campaign chain corrupt')
        previous = row['record_sha256']; event, d = row['event'], row['data']
        if event == 'initialized': require(i == 0, 'ledger reset')
        elif event == 'begin':
            require(pending is None and d['stage'] not in stages and d['argv'] == spec['stages'][d['stage']]['argv'] and
                    d['guard'] == spec['guard'], 'repeated/unfrozen stage')
            pending = d['stage']; tokens = {}
        elif event == 'intent':
            require(pending is not None and d['token'] == i and d['token'] not in tokens, 'missing durable call intent')
            tokens[d['token']] = d
            if pending == 'fit': fit_tokens[d['token']] = dict(d, completed=False)
        elif event == 'complete':
            require(d['token'] in tokens, 'unintended/duplicate counter completion'); tokens.pop(d['token'])
            if pending == 'fit': fit_tokens[d['token']]['completed'] = True
        elif event == 'finish':
            require(pending and not tokens and d['status'] == 'completed' and d['cleanup_verified'] is True and d['execution_ended'] is True,
                    'failed/unfinished current campaign scientific stage')
            stages[pending] = d
            if pending == 'fit': fit_finish = d
            pending = None
        else: raise ValueError('unreviewed/unresolved campaign event')
    require(pending == 'verify' and list(stages) == ['metadata', 'build', 'native', 'prep', 'fit'] and fit_finish,
            'verification requires finished fit and its own still-open saved-only stage')
    expected = dict(native_applies=0, neural_forwards=3624, backwards=3600, optimizer_updates=3600,
                    numerical_fits=2, paid_jobs=0, paid_spend_usd=0.)
    close(fit_finish['durable_completed'], expected, 'authoritative completed fit counters')
    close(fit_finish['durable_intents'], expected, 'authoritative fit intent counters')
    require(all(v['completed'] and v['amount'] == 1 for v in fit_tokens.values()), 'fit call not completely witnessed')
    actual = {key: sum(v['amount'] for v in fit_tokens.values() if v['counter'] == key) for key in expected}
    close(actual, expected, 'independently counted fit intents/completions')
    progress_tokens = [entry['budget_token'] for entry in progress if entry['event'].endswith('-intent')]
    require(len(progress_tokens) == len(set(progress_tokens)) == 10824 and
            set(progress_tokens) == {token for token, value in fit_tokens.items() if value['counter'] != 'numerical_fits'},
            'progress does not account for every actual neural/backward/update call exactly once')
    for entry in progress:
        if entry['event'].endswith('-intent'):
            token = fit_tokens.get(entry['budget_token']); counter = {'forward-intent': 'neural_forwards', 'backward-intent': 'backwards', 'optimizer-intent': 'optimizer_updates'}[entry['event']]
            require(token and token['counter'] == counter, 'fit progress not linked to durable budget intent')
    return dict(fit_completed=True, verify_currently_pending=True, official_counts=expected,
                native_applies=stages['native']['durable_completed']['native_applies'], last_chain=previous)


def source_contrasts(prediction, bits, selected):
    """Saved-prediction factor contrasts only; no additional counterfactual calls."""
    index = {tuple(b): i for i, b in enumerate(bits)}; report = {}
    for axis, name in enumerate(AXES):
        eligibility, intended = [], []
        for q, b in enumerate(bits):
            if b[axis]: continue
            other = list(b); other[axis] = 1; z = index[tuple(other)]
            for variant in range(4):
                a, c = q * 4 + variant, z * 4 + variant
                eligibility.extend(float(y - x) for x, y in zip(prediction['eligibility'][a], prediction['eligibility'][c]))
                intended.append(float(prediction['damage'][c][int(selected[c])] - prediction['damage'][a][int(selected[a])]))
        report[name] = dict(mean_eligibility_contrast=sum(eligibility) / len(eligibility),
            mean_intended_damage_contrast=sum(intended) / len(intended), nested_pairs=len(intended),
            scope='Observed saved paired factor programs, not additional forwards or independent samples')
    return report


def consumed_conflicts(fields, features, targets, masks):
    """Keys contain only each family's actually consumed no-ID head fields.

    NEW eligibility omits effect, intent and damage/HP. OLD eligibility has the
    whole semantic document (uniquely represented by fields in this grammar)
    and the seven non-intent public fields. Masks never split a collision.
    """
    seen = {}; count = {'old': 0, 'new': 0}
    for i, scene in enumerate(features):
        field = fields[i // 4]
        for j, candidate in enumerate(scene):
            for head in (0, 1):
                if not masks[i][j][head]: continue
                for family in ('old', 'new'):
                    if head == 0:
                        visible = (field[:5], candidate[:5]) if family == 'new' else (field, candidate[:7])
                    else:
                        visible = (field, candidate)
                    key = (family, head, digest(visible)); y = targets[i][j][head]
                    if key in seen and seen[key] != y: count[family] += 1
                    else: seen[key] = y
    require(not any(count.values()), 'co-known label conflict in actually consumed head inputs')
    return count


def verify(np, root, out):
    """Run only inside the caller's sealed saved-only verification allocation."""
    root, out = Path(root).resolve(), Path(out).resolve()
    require(out.is_dir() and not list(out.iterdir()) and out.is_relative_to(root), 'exclusive root-owned verification directory required')
    report = dict(schema=SCHEMA, status='failed', semantic_validated=False,
                  verifier_source=pin(__file__), neural_forwards=0, backwards=0, optimizer_updates=0, numerical_fits=0, native_applies=0)
    try:
        plan_path, raw_path, trace_path = root / 'metadata-1/native-plan.json', root / 'native-1/receipt.json', root / 'native-1/transitions.jsonl'
        plan, raw = read(plan_path), read(raw_path); manifest = read(root / 'prep-1/manifest.json')
        arrays = load_npz(np, root / 'prep-1/dataset.npz'); fit = root / 'fit-1'
        result, contract = read(fit / 'result.json'), read(fit / 'contract.json')
        spec = read(root / 'campaign-spec.json'); programs, roles = plan['programs'], plan['candidate_order']
        require(plan['schema'] == 'jepa-compositional-typed-plan/1' and raw['schema'] == 'jepa-compositional-typed-native/1' and
                raw['collectionComplete'] is True and raw['collectionPlan'] == plan and raw['programs'] == programs and
                raw['candidateOrder'] == roles and raw['sourceRevision'] == plan['source_revision'] and
                raw['collectionPlanSha256'] == pin(plan_path)['sha256'], 'native plan/source bytes differ')
        require(len(roles) == 16 and len(set(roles)) == 16 and len(plan['worlds']) == len(raw['cases']) == 128, 'fixed native dimensions differ')
        bits = parity(programs); fields = [parse_program(p) for p in programs]
        train = [i for i in range(128) if sum(bits[i // 4]) % 2 == 0]; held = [i for i in range(128) if i not in train]
        native = native_journal(rows(trace_path), raw); derived = []
        require(len(raw['fixtureValidation']) == 128, 'every fixture must be validated before the first apply')
        for i, (case, world) in enumerate(zip(raw['cases'], plan['worlds'])):
            require(case['world_id'] == world['id'] == i and case['program_index'] == world['program_index'] == i // 4 and
                    case['root_variant'] == world['root_variant'] == i % 4 and case['card'] == world['source_code'] == programs[i // 4]['code'] and
                    case['partition'] == world['partition'] == programs[i // 4]['partition'] and case['declared_intent']['ref'] == world['intent_ref'],
                    'native root/program/split alignment differs')
            fixture = raw['fixtureValidation'][i]
            require(fixture['world_id'] == i and fixture['card'] == case['card'] and
                    fixture['publicSnapshotRoundtripExact'] is True and fixture['legalActionsRoundtripExact'] is True and
                    fixture['allProgramsAdmitted'] is True and fixture['applyCalls'] == fixture['actionsApplied'] == 0 and
                    fixture['before'] == case['before'], 'pre-apply admission/fixture roundtrip witness differs')
            derived.append(native_case(case, world, roles))
        expected = dict(candidate_features=[d['features'] for d in derived], targets=[d['targets'] for d in derived],
            target_mask=[d['mask'] for d in derived], selected_candidate_indices=[d['selected'] for d in derived],
            program_indices=[i // 4 for i in range(128)], program_bits=bits, typed_features=fields,
            world_ids=list(range(128)), source_cards=[p['code'] for p in programs for _ in range(4)],
            program_ids=[p['code'] for p in programs], train_idx=train, held_idx=held,
            baseline_predictions=[reference(fields[i // 4], d['features']) for i, d in enumerate(derived)])
        primary = copy.deepcopy(expected['target_mask'])
        for i in range(128):
            for j in range(16):
                if j != expected['selected_candidate_indices'][i]: primary[i][j][1] = 0.
        expected['primary_target_mask'] = primary
        input_conflicts = consumed_conflicts(fields, expected['candidate_features'], expected['targets'], expected['target_mask'])
        require(set(arrays) == set(expected), 'dataset ABI extra/missing fields')
        for key, value in expected.items():
            actual = arrays[key]; require(np.array_equal(actual, np.asarray(value, dtype=actual.dtype)), 'native reconstructed array mismatch: ' + key)
            if actual.dtype.kind in 'fi': require(np.isfinite(actual).all(), 'nonfinite saved input/label')
            require(actual.dtype == (np.int64 if key in ('selected_candidate_indices', 'program_indices', 'program_bits', 'world_ids', 'train_idx', 'held_idx')
                else actual.dtype if key in ('source_cards', 'program_ids') else np.float32), 'native array dtype differs: ' + key)
        ref = arrays['baseline_predictions']; mask = arrays['target_mask'] > 0
        require(int(mask[..., 0].sum()) == 2048 and int(mask[..., 1].sum()) == 1536 and
                np.all(np.abs(ref[mask] - arrays['targets'][mask]) <= 1e-6), 'reference/native agreement or complete coverage failed')
        healthy = [i for i in range(128) if bits[i // 4][4] and i % 4 == 2]
        require(len(healthy) == 16 and all(primary[i][derived[i]['selected']][1] == 1. and expected['targets'][i][derived[i]['selected']][1] == 0. for i in healthy),
                'healthy eligible native zero outcomes missing')
        require(manifest['fit_admitted'] is True and manifest['fit_blockers'] == [] and manifest['semantic_validated'] is False and
                manifest['programs'] == programs and manifest['plan'] == plan and
                manifest['candidate_feature_names'] == list(FEATURES) and manifest['target_names'] == ['target_allowed', 'target_damage_delta'] and
                manifest['public_before_records'] == [d['record'] for d in derived] and
                manifest['physics_scales'] == dict(printed_cost=4., damage=4., hp=10., amount=3.) and
                manifest['split']['train'] == train and manifest['split']['held'] == held, 'manifest input/support/split claim differs')
        for i, audit in enumerate(manifest['identity_renaming_audits']):
            require(audit['original_sha256'] == audit['renamed_sha256'] == derived[i]['rename_sha256'] and
                    audit['physical_id_and_code_renaming_invariant'] is True and audit['menu_future_private_poison_invariant'] is True,
                    'physical/code identity renaming proof differs')
        consumed, schedule = load_npz(np, fit / 'consumed-inputs.npz'), load_npz(np, fit / 'training-schedule.npz')
        for key in ('candidate_features', 'program_indices', 'program_bits', 'selected_candidate_indices', 'targets', 'target_mask', 'primary_target_mask'):
            require(np.array_equal(consumed[key], arrays[key]), 'actually consumed input differs: ' + key)
        require(np.array_equal(consumed['program_fields'], arrays['typed_features']), 'actual typed field extraction differs')
        schedule_expected = dict(train_indices=train, held_indices=held, seeds=list(SEEDS), arms=list(ARMS),
                                 program_indices=expected['program_indices'], selected_candidate_indices=expected['selected_candidate_indices'])
        require(set(schedule) == set(schedule_expected), 'training schedule extra/missing keys')
        for key, value in schedule_expected.items(): require(np.array_equal(schedule[key], np.asarray(value, dtype=schedule[key].dtype)), 'training schedule differs: ' + key)
        bank = bank_audit(np, programs, contract, consumed)
        statistics = loss_statistics(expected['targets'], primary, expected['selected_candidate_indices'], expected['program_indices'], fields, train)
        saved_weights = read(fit / 'loss-weights.json')
        for key, value in statistics.items(): close(saved_weights[key], value, 'TRAIN-only objective statistics.' + key)
        require(result['status'] == 'completed' and result['semantic_validated'] is False and result['semantic_rename_invariance'] is True, 'misstated fit status or semantic qualification')
        close(result['counts'], COUNTS, 'exact reported exposure')
        close(contract['config'], result['config'], 'saved objective/config equality')
        for name, value in dict(seeds=list(SEEDS), arms=list(ARMS), updates_per_arm=300,
                learning_rate=.003, weight_decay=.0001, clip_l2=1., optimizer='AdamW',
                eligibility_loss=.5, damage_loss=.5, candidate_scales=[1., 1., 1., 1., 4., 4., 10., 1.],
                cpu_workers=1, rss_bytes=1073741824, **COUNTS).items():
            close(result['config'][name], value, 'frozen experimental control.' + name)
        for key in ('targets', 'target_mask'): require(result['label_hashes'][key] == array_hash(arrays[key]), 'true label mutation hash')
        require(result['public_input_sha256'] == array_hash(arrays['candidate_features']), 'public input mutation hash')
        frozen = {p['path']: p for p in spec['pins']}
        source_pins = [*contract['source_pins'], *contract['input_pins']]
        for p in source_pins:
            require(pin(p['path']) == p, 'fit source/input pin changed')
            if p in contract['source_pins']: require(frozen.get(p['path']) == p, 'fit source absent from frozen closure')
        close(contract['program_fields'], fields, 'contract literal fields'); close(contract['program_bits'], bits, 'contract program bits')
        require(contract['program_codes'] == expected['program_ids'], 'contract source bank order differs')
        progress = rows(fit / 'fit-progress.jsonl'); counter_check = progress_audit(progress)
        budget = budget_audit(rows(root / 'campaign-ledger.jsonl'), spec, progress)
        require(budget['native_applies'] == native['native_applies'], 'official native count disagrees with physical trace')
        all_scores, all_gates, advantages, contrasts, movement = {}, {}, [], {}, {}
        for seed in SEEDS:
            for family in ('old', 'new'):
                initial = load_npz(np, fit / f's{seed}-{family}-initial-checkpoint.npz'); initial_hash = named_hash(initial)
                require(all(np.isfinite(a).all() for a in initial.values()) and result['initial_state_hashes'][f'{seed}:{family}'] == initial_hash,
                        'initial named-weight hash/nonfinite state')
                for arm in (family + '-no-id', family + '-with-id'):
                    key = f'{seed}:{arm}'; metadata = result['arm_metadata'][key]
                    require(metadata['initial_state_sha256'] == initial_hash and metadata['identity_enabled'] == arm.endswith('with-id'),
                            'paired arm initialization/source load assertion differs')
                    final_path = fit / f's{seed}-{arm}-checkpoint.npz'; final = load_npz(np, final_path)
                    require(set(final) == set(initial) and all(final[k].shape == initial[k].shape and final[k].dtype == initial[k].dtype and np.isfinite(final[k]).all() for k in final),
                            'final checkpoint named shapes/dtypes/nonfinite state differ')
                    require(result['checkpoints'][key] == dict(pin=pin(final_path), state_sha256=named_hash(final)) and
                            metadata['allocated_parameters'] == metadata['trainable_parameters'] == sum(v.size for v in final.values()),
                            'final checkpoint pin/state/parameter count differs')
                    if family == 'new':
                        require({k: list(v.shape) for k, v in final.items()} == contract['new_model']['parameters']['named_weight_shapes'] and
                                sum(v.size for v in final.values()) == contract['new_model']['parameters']['allocated'] <= 5000,
                                'small compositional model shape/capacity contract differs')
                    identity_key = 'base.identity.weight' if family == 'old' else 'identity.weight'
                    require(not np.any(initial[identity_key][0]) and not np.any(final[identity_key][0]), 'UNK0 acquired identity information')
                    movement[key] = dict(l2=float(math.sqrt(sum(float(np.square(final[k].astype(np.float64) - initial[k]).sum()) for k in final))),
                        changed_coordinates=sum(int(np.count_nonzero(final[k] != initial[k])) for k in final),
                        initial_hash_scope='Saved shared-family master plus per-arm post-load hash assertion; no extra initial forward.')
                    all_scores[key] = {}
                    for step in (0, 300):
                        pred = load_npz(np, fit / f's{seed}-{arm}-step{step}-predictions.npz')
                        require(set(pred) == {'eligibility', 'damage', 'program_indices', 'selected_candidate_indices'} and
                                pred['eligibility'].shape == pred['damage'].shape == (128, 16) and
                                pred['eligibility'].dtype == pred['damage'].dtype == np.float32 and
                                all(np.isfinite(pred[k]).all() for k in ('eligibility', 'damage')) and
                                np.array_equal(pred['program_indices'], arrays['program_indices']) and
                                np.array_equal(pred['selected_candidate_indices'], arrays['selected_candidate_indices']), 'saved prediction ABI/alignment differs')
                        scores = evaluations(pred, expected['targets'], primary, expected['selected_candidate_indices'], expected['program_indices'], bits, train, held)
                        close(result['results'][key][str(step)], scores, 'saved per-example metric.' + key + '.' + str(step))
                        all_scores[key][str(step)] = scores
                        if step == 300: contrasts[key] = source_contrasts(pred, bits, expected['selected_candidate_indices'])
            for family in ('old', 'new'):
                key = f'{seed}:{family}'; computed = gate(all_scores[key + '-no-id']['300'], all_scores[key + '-with-id']['300'], family == 'new')
                for name, value in computed.items(): close(result['gates'][key][name], value, 'absolute/identity gate.' + key + '.' + name)
                all_gates[key] = computed
            advantage = comparative(all_scores[f'{seed}:old-no-id']['300']['held'], all_scores[f'{seed}:new-no-id']['300']['held'])
            reported = next(a for a in result['advantage'] if a['seed'] == seed)
            for name, value in advantage.items(): close(reported[name], value, 'comparative gate.' + str(seed) + '.' + name)
            advantages.append(dict(seed=seed, **advantage))
        passing = {family: all(all_gates[f'{seed}:{family}']['passed'] for seed in SEEDS) for family in ('old', 'new')}
        relative = all(a['passed'] for a in advantages)
        decision = 'retain-old-research-only' if passing['old'] else 'support-new-research-architecture-only' if passing['new'] and relative else 'stop-composition-comparison-insufficient'
        require(result['passing_families'] == passing and result['decision'] == decision and
                result['strict_new_advantage'] == (relative and passing['new'] and not passing['old']), 'final decision overclaims saved gates')
        report.update(status='passed', native=native, reference=dict(known_eligibility=2048, known_effects=1536,
            healthy_heal_zero_endpoints=16, complete=True, native_max_abs_error=0., fits=0),
            parity=dict(train_programs=16, held_programs=16, train_roots=64, held_roots=64, proper_subset_support=True),
            bank=bank, counters=counter_check, budget=budget, results=all_scores, gates=all_gates,
            consumed_input_conflicts=input_conflicts,
            advantage=advantages, passing_families=passing, decision=decision, weight_movement=movement,
            source_factor_contrasts=contrasts,
            limitations=['Synthetic full-combination holdout, not actual-card or playing-strength qualification.',
                'Architecture comparison includes hard endpoint eligibility/intended routing as well as typed binding.',
                'Rename checks verify consumed serialization equality, not an additional neural execution.',
                'Four worlds per program and target coordinates are nested observations, not independent samples.'],
            input_pins=[pin(p) for p in (plan_path, raw_path, trace_path, root / 'prep-1/dataset.npz', root / 'prep-1/manifest.json', fit / 'result.json', fit / 'contract.json', fit / 'fit-progress.jsonl')])
    except BaseException as error:
        report['error'] = dict(type=type(error).__name__, message=str(error))
        write_new(out / 'verification-result.json', report)
        raise
    write_new(out / 'verification-result.json', report)
    return dict(status='passed', result=pin(out / 'verification-result.json'), decision=report['decision'],
                native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0, numerical_fits=0, semantic_validated=False)
