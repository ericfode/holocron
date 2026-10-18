"""Public native observations for the synthetic compositional assay.

Importing this module uses only the standard library and performs no I/O.
``prepare_data(np, plan, receipt, journal_rows)`` is an explicit preparation
helper: its caller owns the sealed budget, input pins and exclusive outputs.
The analytical primitive is a comparator, never the source of native labels.
"""
import copy
import hashlib
import itertools
import json
import math

SCHEMA = 'jepa-compositional-typed-data/1'
FEATURES = ('owner_self', 'owner_opponent', 'arena_ground', 'arena_space',
            'printed_cost', 'damage', 'hp', 'is_intended')
HEADS = ('target_allowed', 'target_damage_delta')
BIT_NAMES = ('owner_opponent', 'arena_space', 'cap_three', 'amount_three', 'op_heal')
TYPED_FIELDS = ('owner_any', 'owner_opponent', 'arena_ground', 'arena_space',
                'cost_cap', 'op_damage', 'op_heal', 'amount')
KNOWN = ('identity', 'owner', 'printed_cost', 'damage', 'hp')
TERMINALS = ('settled-committed', 'settled-cancelled', 'unoffered-prompt-only')
PHYSICS_SCALES = dict(printed_cost=4., damage=4., hp=10., amount=3.)


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def number(value):
    require(type(value) in (int, float), 'explicit numeric public field required')
    try:
        require(math.isfinite(value), 'finite public numeric field required')
    except OverflowError as error:
        raise ValueError('finite public numeric field required') from error
    return float(value)


def candidate(projection, intended_id, own):
    """Return an identity-free eight-field input, rejecting unknowns."""
    p = projection
    require(isinstance(p, dict) and own in ('p1', 'p2'), 'public candidate/acting owner required')
    require(all(p.get('known', {}).get(k) is True for k in KNOWN), 'unknown candidate input')
    require(p.get('present') is True and p.get('is_unit') is True and p.get('in_arena') is True,
            'present public arena unit required')
    require(p.get('zone') in ('ground', 'space') and p.get('owner') in ('p1', 'p2'),
            'explicit public arena/owner required')
    require(isinstance(p.get('id'), str) and p['id'] and isinstance(intended_id, str),
            'public physical identity required for equality only')
    cost, damage, hp = (number(p[k]) for k in ('printed_cost', 'damage', 'hp'))
    require(cost in (2., 3., 4.) and hp == 10. and 0 <= damage < hp,
            'fixed cost2/3/4 and HP10 living candidate required')
    return [float(p['owner'] == own), float(p['owner'] != own),
            float(p['zone'] == 'ground'), float(p['zone'] == 'space'),
            cost, damage, hp, float(p['id'] == intended_id)]


def public_inputs(case, roles):
    """Whitelist only BEFORE physical fields; menus/futures are never inspected."""
    require(len(roles) == len(set(roles)) == 16, 'sixteen distinct candidate roles required')
    refs, intent, projections = case['refs'], case['declared_intent'], case['before']['projections']
    source = projections['source']
    require(source.get('known', {}).get('owner') is True and source.get('owner') in ('p1', 'p2'),
            'known public acting owner required')
    own = source['owner']
    require(intent.get('requires_target') is True and intent.get('ref') in roles and
            intent.get('id') == refs[intent['ref']], 'explicit pre-action intended equality required')
    require(len({refs[r] for r in roles}) == 16, 'candidate identities must be distinct')
    records, features = [], []
    for role in roles:
        p = projections[role]
        require(p.get('id') == refs[role], 'candidate reference/projection mismatch')
        row = candidate(p, intent['id'], own)
        records.append(dict(owner=p['owner'], arena=p['zone'], printed_cost=row[4],
                            damage=row[5], hp=row[6], is_intended=bool(row[7]),
                            known={k: True for k in KNOWN}))
        features.append(row)
    require(sum(row[7] for row in features) == 1., 'exactly one intended candidate required')
    return features, dict(acting_owner=own, candidates=records,
                          input_scope='BEFORE owner/arena/cost/damage/HP and intended equality only')


def identity_audit(case, roles):
    """Opaque physical/code renaming cannot change any consumed public field."""
    original, _ = public_inputs(case, roles)
    altered = copy.deepcopy(case)
    mapping = {value: 'opaque-' + str(i) for i, value in enumerate(case['refs'].values())}
    altered['refs'] = {key: mapping[value] for key, value in case['refs'].items()}
    altered['declared_intent']['id'] = mapping[case['declared_intent']['id']]
    for role, p in altered['before']['projections'].items():
        if p is not None:
            if p.get('id') in mapping:
                p['id'] = mapping[p['id']]
            if 'code' in p:
                p['code'] = 'opaque-public-code-' + role
    # Deliberately inconsistent poisoned future/menu content must be irrelevant.
    altered['targetPrompt'] = {'offeredActions': [{'card': 'poison'}]}
    altered['final'] = {'private_future': 'poison'}
    altered['before']['offeredActions'] = [{'card': 'poison'}]
    altered['before']['state'] = {'private': 'poison'}
    renamed, _ = public_inputs(altered, roles)
    return dict(original_sha256=digest(original), renamed_sha256=digest(renamed),
                physical_id_and_code_renaming_invariant=original == renamed,
                menu_future_private_poison_invariant=original == renamed)


def factors_from_bits(bits):
    require(isinstance(bits, list) and len(bits) == 5 and all(type(b) is int and b in (0, 1) for b in bits),
            'five exact binary grammar coordinates required')
    return dict(owner='opponent' if bits[0] else 'any', arena='space' if bits[1] else 'ground',
                cap=3 if bits[2] else 2, amount=3 if bits[3] else 1,
                op='heal' if bits[4] else 'damage')


def partition(bits):
    factors_from_bits(bits)
    return 'held' if sum(bits) % 2 else 'train'


def program_fields(program):
    """Independently parse the exact public grammar, never a name/code lookup."""
    factors = factors_from_bits(program['bits'])
    require(digest(program.get('factors')) == digest(factors) and program.get('synthetic') is True,
            'synthetic factors must equal the actual five-bit declaration')
    ability = dict(trigger='event', title='Elementary effect', costs=[],
        targetResolver=dict(owner=factors['owner'], type='unit', zone='arena', arena=factors['arena'],
            predicate=dict(kind='binary', op='<=', left=dict(kind='ref', path=['card', 'cost']),
                           right=dict(kind='const', value=factors['cap']))),
        effect=dict(kind=factors['op'], target='chosen', amount=dict(kind='const', value=factors['amount'])))
    require(digest(program['raw_card'].get('abilities')) == digest(dict(card=[ability], unit=[], leader=[])),
            'whole public ability must equal the declared strict grammar')
    return [float(factors['owner'] == 'any'), float(factors['owner'] == 'opponent'),
            float(factors['arena'] == 'ground'), float(factors['arena'] == 'space'),
            float(factors['cap']), float(factors['op'] == 'damage'),
            float(factors['op'] == 'heal'), float(factors['amount'])]


def fixture_proof(case, world, roles):
    """The full BEFORE scene is public and exactly matches the declared lattice."""
    before, refs = case['before'], case['refs']
    source = before['projections']['source']
    require(source.get('id') == refs['source'] and source.get('code') == case['card'] and
            source.get('owner') == 'p1' and source.get('zone') == 'hand' and
            source.get('known', {}).get('identity') is True, 'own declared fresh-hand source required')
    require(set(world['arena_cards']) == set(roles), 'all sixteen physical units must be declared')
    public, _ = public_inputs(case, roles)
    lattice = {}
    for role, row in zip(roles, public):
        p, spec = before['projections'][role], world['arena_cards'][role]
        require(p.get('code') == spec['code'] and p.get('owner') == spec['owner'] and
                p.get('zone') == spec['arena'] and number(p['damage']) == number(spec['damage']) and
                row[6] == 10. and number(p['power']) == 0. and row[4] == number(spec['printed_cost']) and
                ('cost' not in spec or number(spec['cost']) == number(spec['printed_cost'])),
                'actual public fixture differs')
        key = (p['owner'], p['zone'], row[4]); lattice[key] = lattice.get(key, 0) + 1
    expected = {(owner, arena, float(cost)): (2 if cost == 2 else 1)
                for owner, arena, cost in itertools.product(('p1', 'p2'), ('ground', 'space'), (2, 3, 4))}
    require(lattice == expected, 'complete owner/arena/cost lattice with four cost2 twins required')
    players = before['state']['players']
    require(all(players[p]['deck'] == [] for p in ('p1', 'p2')) and
            players['p2']['hand'] == [] and players['p2']['resources'] == [], 'hidden fixture piles must stay empty')
    require([x['id'] for x in players['p1']['hand']] == [refs['source']], 'own hand must contain only public declared source')
    arena = [x['id'] for p in ('p1', 'p2') for zone in ('ground', 'space') for x in players[p][zone]]
    require(len(arena) == len(set(arena)) == 16 and set(arena) == {refs[r] for r in roles},
            'every actual public arena instance must be represented exactly once')
    return dict(public_candidates=16, complete_lattice=True, empty_private_piles=True)


def primitive(factors, features, selected):
    """Generic typed comparator; healthy healing is clipped, never excluded."""
    require(set(factors) == {'owner', 'arena', 'cap', 'amount', 'op'}, 'exact primitive factors required')
    require(factors['owner'] in ('any', 'opponent') and factors['arena'] in ('ground', 'space') and
            factors['cap'] in (2, 3) and factors['amount'] in (1, 3) and
            factors['op'] in ('damage', 'heal'), 'unsupported primitive')
    require(type(selected) is int and 0 <= selected < len(features), 'explicit intended index required')
    predictions = []
    for j, row in enumerate(features):
        require(len(row) == 8 and all(math.isfinite(number(v)) for v in row), 'eight finite public inputs required')
        allowed = ((factors['owner'] == 'any' or row[1] == 1.) and
                   row[2 if factors['arena'] == 'ground' else 3] == 1. and row[4] <= factors['cap'])
        delta = 0.
        if allowed and j == selected:
            delta = float(factors['amount']) if factors['op'] == 'damage' else -min(float(factors['amount']), row[5])
        predictions.append([float(allowed), delta])
    return predictions


def offered(capture, physical_id):
    require(capture.get('decision') == 'AbilityTarget' and isinstance(capture.get('offeredActions'), list),
            'reached native target prompt required')
    return [action for action in capture['offeredActions'] if action.get('card') == physical_id]


def derive_labels(case, roles):
    """Only reached native menus and settled committed endpoints become labels."""
    require(case.get('engineError') is None and case.get('publicSnapshotRoundtripExact') is True,
            'error-free roundtripped native fixture required')
    before, refs, intent = case['before'], case['refs'], case['declared_intent']
    require(before.get('decision') == 'Window' and case.get('steps'), 'actual native source play from public Window required')
    features, record = public_inputs(case, roles)
    selected = roles.index(intent['ref'])
    last, captures, choices, done, cancelled = before, [before], [], [], []
    for i, step in enumerate(case['steps']):
        require(step['before'] == last and step['action'] in last['offeredActions'],
                'native step is discontinuous or action unoffered')
        stage, action = step['stage'], step['action']
        if i == 0:
            require(stage == 'play-own-hand' and action == case['playAction'] and
                    action.get('card') == refs['source'], 'actual source play required')
        elif stage == 'chosen-target':
            require(last == case['targetPrompt'] and action == case['targetAction'] and
                    action in offered(last, intent['id']), 'actual offered intended target required')
            choices.append(step)
        elif stage == 'commit-one-selection':
            require(len(choices) == 1 and action.get('arg') == 'done' and action.get('label') == 'Done' and
                    last.get('abilitySelection') == [intent['id']], 'exactly-one native Done witness required')
            done.append(step)
        elif stage == 'decline-unoffered-target':
            require(last == case['targetPrompt'] and not offered(last, intent['id']) and
                    action == case['declineAction'] and action.get('arg') == 'cancel' and
                    action.get('label') == 'Cancel', 'actual offered native Cancel required')
            cancelled.append(step)
        elif stage == 'accept-optional-trigger':
            require(last['decision'] == 'AbilityOptional' and action.get('arg') == 'trigger', 'optional trigger differs')
        elif stage == 'use-no-effect-anyway':
            require(last['decision'] == 'AbilityNoEffect' and action.get('arg') == 0, 'no-effect acceptance differs')
        elif stage == 'sole-trigger-order':
            require(last['decision'] == 'TriggerOrder' and len(last['offeredActions']) == 1, 'ambiguous trigger order')
        else:
            raise ValueError('unreviewed native step stage')
        last = step['after']; captures.append(last)
    require(case.get('lastObserved') == last and len(choices) <= 1 and len(done) <= 1 and len(cancelled) <= 1,
            'native last/selection witness differs')
    prompt = case.get('targetPrompt')
    require(prompt in captures and prompt.get('decision') == 'AbilityTarget', 'native reached target prompt required')
    targets = [[float(bool(offered(prompt, refs[role]))), 0.] for role in roles]
    masks = [[1., 0.] for role in roles]
    require(type(case.get('intentOffered')) is bool and case['intentOffered'] == bool(targets[selected][0]),
            'native intended membership differs')
    terminal = case.get('terminalClassification')
    require(terminal in TERMINALS, 'explicit typed native terminal required')
    committed = bool(choices) and (not done or len(done) == 1)
    require(case.get('intendedTargetCommitted') is committed, 'native commitment flag differs')
    if terminal == 'unoffered-prompt-only':
        require(case.get('final') is None and last == prompt and not targets[selected][0] and not choices and not cancelled and
                case.get('completion') == case.get('intentResolution') == 'unoffered-observation-only' and
                not any(a.get('arg') == 'cancel' and a.get('label') == 'Cancel' for a in prompt['offeredActions']),
                'prompt-only terminal must not invent Cancel or future labels')
    else:
        final = case.get('final')
        require(final == last and final.get('settled') is True and case.get('completion') == 'settled',
                'actual settled endpoint required')
        require((terminal == 'settled-committed') == committed and
                (terminal == 'settled-cancelled') == bool(cancelled), 'native terminal/commit mismatch')
        require(case.get('intentResolution') == ('committed' if committed else 'unoffered-declined'),
                'native resolution differs')
        if committed:
            require(targets[selected][0] == 1., 'unoffered intent cannot have effects')
            for j, role in enumerate(roles):
                a, z = before['projections'][role], final['projections'][role]
                require(z.get('id') == a['id'] == refs[role], 'endpoint physical identity changed')
                stable = (z.get('present') is True and z.get('in_arena') is True and z.get('zone') == a['zone'] and
                          z.get('known', {}).get('damage') is True and z.get('known', {}).get('hp') is True)
                if stable and number(z['damage']) < number(z['hp']):
                    targets[j][1] = number(z['damage']) - number(a['damage']); masks[j][1] = 1.
    return dict(features=features, public_before=record, targets=targets, target_mask=masks,
                selected=selected, terminal=terminal, committed=committed,
                identity_audit=identity_audit(case, roles))


def split_report(programs):
    bits = [p['bits'] for p in programs]
    require(len(bits) == 32 and {tuple(b) for b in bits} == set(itertools.product((0, 1), repeat=5)),
            'complete unique five-bit program product required')
    report = {}
    for name in ('train', 'held'):
        selected = [b for b in bits if partition(b) == name]
        single = {BIT_NAMES[i]: [sum(b[i] == value for b in selected) for value in (0, 1)] for i in range(5)}
        pair = {BIT_NAMES[i] + '__' + BIT_NAMES[j]:
                [sum((b[i], b[j]) == level for b in selected) for level in itertools.product((0, 1), repeat=2)]
                for i in range(5) for j in range(i + 1, 5)}
        require(len(selected) == 16 and all(v == [8, 8] for v in single.values()) and
                all(v == [4, 4, 4, 4] for v in pair.values()), 'parity atom/pair balance differs')
        report[name] = dict(programs=16, roots=64, atom_counts=single, pair_counts=pair)
    return report


def class_support(labels, masks, rows):
    """Descriptive coordinate counts, never independent-sample counts."""
    return {head: dict(known=sum(int(masks[i][j][h]) for i in rows for j in range(16)),
        zero=sum(int(bool(masks[i][j][h]) and labels[i][j][h] == 0.) for i in rows for j in range(16)),
        positive=sum(int(bool(masks[i][j][h]) and labels[i][j][h] > 0.) for i in rows for j in range(16)),
        negative=sum(int(bool(masks[i][j][h]) and labels[i][j][h] < 0.) for i in rows for j in range(16)))
        for h, head in enumerate(HEADS)}


def journal_proof(rows, receipt):
    """Validate chronological physical action boundaries without running native code."""
    require(isinstance(rows, list) and rows, 'native durable journal required')
    header = rows[0]
    require(header.get('schema') == 'jepa-compositional-typed-apply-journal/1' and
            header.get('planSha256') == receipt.get('collectionPlanSha256') and
            header.get('sourceRevision') == receipt.get('sourceRevision'), 'native journal provenance differs')
    starts, ends, completed, open_call = [], [], [], None
    for row in rows[1:]:
        phase = row.get('phase')
        if phase == 'beforeApply':
            require(open_call is None and row['applyCall'] == len(starts) + 1, 'unpaired/nonchronological native apply')
            starts.append(row); open_call = row
        elif phase == 'afterApply':
            require(open_call is not None and all(row[k] == open_call[k] for k in ('applyCall', 'context', 'branch')),
                    'native afterApply boundary differs')
            ends.append(row); open_call = None
        elif phase == 'contextComplete':
            require(open_call is None, 'root completed during pending application')
            completed.append(row['case'])
        else:
            raise ValueError('native journal error/unreviewed event')
    require(open_call is None and len(starts) == len(ends) == receipt['applyCalls'] and
            completed == receipt['cases'], 'native actions or root completions incomplete')
    offset = 0
    for case in receipt['cases']:
        steps = case['steps']; require(len(steps) == case['applyCalls'], 'root native count differs')
        for step, a, z in zip(steps, starts[offset:offset + len(steps)], ends[offset:offset + len(steps)]):
            require(step['before'] == a['before'] and step['action'] == a['offeredAction'] and
                    a['context'] == 'world-' + str(case['world_id']) + '-' + case['card'] and
                    step['stage'] == a['branch'] and step['after'] == z['after'], 'native journal step differs')
        offset += len(steps)
    return dict(native_applies=len(starts), roots=len(completed), chronological_pairs=True)


def prepare_data(np, plan, receipt, journal_rows):
    """Allocated preparation only. No I/O, model invocation, fitting or hidden input."""
    roles, programs, worlds = plan['candidate_order'], plan['programs'], plan['worlds']
    require(len(roles) == 16 and len(programs) == 32 and len(worlds) == 128, 'frozen32x4x16 assay required')
    require(plan.get('schema') == 'jepa-compositional-typed-plan/1' and
            receipt.get('schema') == 'jepa-compositional-typed-native/1', 'exact compositional plan/native schema required')
    balance = split_report(programs)
    typed = [program_fields(p) for p in programs]
    printed_keys = ('cost', 'hp', 'power', 'types', 'aspects', 'traits', 'keywords', 'unique',
                    'arena', 'upgradePower', 'upgradeHp')
    printed_profiles = [{k: p['raw_card']['card'].get(k) for k in printed_keys} for p in programs]
    require(len({digest(p) for p in printed_profiles}) == 1 and
            all(p['index'] == i and p['partition'] == partition(p['bits']) and
                p['program_hash'] == digest(p['raw_card']['abilities']) for i, p in enumerate(programs)),
            'source printed profiles must be constant and program metadata must match syntax')
    require(receipt.get('collectionPlan') == plan and receipt.get('collectionComplete') is True and
            receipt.get('candidateOrder') == roles and receipt.get('programs') == programs and
            receipt.get('sourceRevision') == plan['source_revision'],
            'complete exact native plan/source/role receipt required')
    require(type(receipt.get('applyCalls')) is int and 0 < receipt['applyCalls'] <= plan['collector_max_engine_applies'],
            'native calls must remain within the frozen plan cap')
    cases = receipt['cases']; require(len(cases) == 128, 'all128 actual roots required')
    proof = journal_proof(journal_rows, receipt)
    features, labels, masks, selected, indices, identities, records, statuses, baselines, audits, mismatches = ([] for _ in range(11))
    for i, (case, world) in enumerate(zip(cases, worlds)):
        require(case['world_id'] == world['id'] == i and case['card'] == world['source_code'] and
                case['program_index'] == world['program_index'] and case['root_variant'] == world['root_variant'],
                'native root identity/order differs')
        p = programs[world['program_index']]; factors = factors_from_bits(p['bits'])
        require(p['code'] == world['source_code'] and p['factors'] == factors and p.get('synthetic') is True and
                world['partition'] == partition(p['bits']) and case['partition'] == world['partition'] and
                world['root_variant'] == i % 4 and world['program_index'] == i // 4,
                'program bits/factors/split differs')
        require(case['declared_intent']['ref'] == world['intent_ref'], 'native intended role differs')
        fixture_proof(case, world, roles)
        derived = derive_labels(case, roles); prediction = primitive(factors, derived['features'], derived['selected'])
        for j, role in enumerate(roles):
            for h, head in enumerate(HEADS):
                if derived['target_mask'][j][h] and prediction[j][h] != derived['targets'][j][h]:
                    mismatches.append(dict(root=i, program_index=world['program_index'], role=role, head=head,
                        native=derived['targets'][j][h], primitive=prediction[j][h],
                        healthy_healing=factors['op'] == 'heal' and derived['features'][j][5] == 0.))
        features.append(derived['features']); labels.append(derived['targets']); masks.append(derived['target_mask'])
        selected.append(derived['selected']); indices.append(world['program_index']); identities.append(case['card'])
        records.append(derived['public_before']); baselines.append(prediction); audits.append(derived['identity_audit'])
        statuses.append(dict(root=i, terminal=derived['terminal'], committed=derived['committed'],
                             root_variant=world['root_variant'], program_index=world['program_index']))
    require(all(sum(x == j for x in indices) == 4 for j in range(32)), 'exactly four roots per complete program required')
    train = [i for i, j in enumerate(indices) if partition(programs[j]['bits']) == 'train']
    held = [i for i, j in enumerate(indices) if partition(programs[j]['bits']) == 'held']
    primary = copy.deepcopy(masks)
    for i in range(128):
        for j in range(16):
            if j != selected[i]:
                primary[i][j][1] = 0.
    counts = {name: class_support(labels, masks, ix) for name, ix in (('train', train), ('held', held))}
    primary_counts = {name: class_support(labels, primary, ix) for name, ix in (('train', train), ('held', held))}
    strata = {}
    for name, ix in (('train', train), ('held', held)):
        strata[name] = {}
        for axis, bit_name in enumerate(BIT_NAMES):
            for value in (0, 1):
                rows = [i for i in ix if programs[indices[i]]['bits'][axis] == value]
                strata[name][bit_name + '=' + str(value)] = dict(roots=rows,
                    program_indices=sorted({indices[i] for i in rows}),
                    primary_classes=class_support(labels, primary, rows))
        for op, amount in itertools.product(('damage', 'heal'), (1, 3)):
            rows = [i for i in ix if programs[indices[i]]['factors']['op'] == op and
                    programs[indices[i]]['factors']['amount'] == amount]
            strata[name][op + '-amount=' + str(amount)] = dict(roots=rows,
                program_indices=sorted({indices[i] for i in rows}), primary_classes=class_support(labels, primary, rows))
    blockers = []
    if mismatches:
        blockers.append('actual-native-primitive-comparator-mismatch')
    for i, status in enumerate(statuses):
        expected_commit = status['root_variant'] != 3
        if status['committed'] != expected_commit or (expected_commit and masks[i][selected[i]][1] != 1.):
            blockers.append('root-' + str(i) + '-predeclared-commit-or-intended-endpoint-missing')
        if any(row[0] != 1. or row[1] != float(status['committed']) for row in masks[i]):
            blockers.append('root-' + str(i) + '-native-observation-mask-coverage-incomplete')
    for name in ('train', 'held'):
        if not all(counts[name][HEADS[0]][k] > 0 for k in ('zero', 'positive')) or not all(
                counts[name][HEADS[1]][k] > 0 for k in ('zero', 'positive', 'negative')):
            blockers.append(name + '-native-class-support-incomplete')
    coverage = {head: dict(known=sum(int(masks[i][j][h]) for i in range(128) for j in range(16)),
        compared=sum(int(masks[i][j][h]) for i in range(128) for j in range(16)),
        mismatches=sum(m['head'] == head for m in mismatches)) for h, head in enumerate(HEADS)}
    for head, expected in zip(HEADS, (128 * 16, 96 * 16)):
        coverage[head]['predeclared_known_coordinates'] = expected
        if coverage[head]['known'] != expected:
            blockers.append(head + '-predeclared-native-coverage-incomplete')
    healthy = []
    for i, j in enumerate(indices):
        if programs[j]['factors']['op'] != 'heal' or statuses[i]['root_variant'] != 2:
            continue
        q = selected[i]
        healthy.append(dict(root=i, program_index=j, role=roles[q], before_damage=features[i][q][5],
            native_allowed=labels[i][q][0], eligibility_known=bool(masks[i][q][0]),
            native_delta=labels[i][q][1] if masks[i][q][1] else None, delta_known=bool(masks[i][q][1]),
            primitive_delta=baselines[i][q][1], retained=True))
    healthy_complete = len(healthy) == 16 and all(h['before_damage'] == 0. and h['eligibility_known'] and
        h['native_allowed'] == 1. and h['delta_known'] and h['native_delta'] == 0. for h in healthy)
    if not healthy_complete:
        blockers.append('healthy-healing-native-known-zero-support-incomplete')
    seen, conflicts = {}, []
    for i, j in enumerate(indices):
        for q in range(16):
            key = digest([typed[j], features[i][q]])
            for h in range(2):
                if not masks[i][q][h]:
                    continue
                slot = (key, h); prior = seen.get(slot)
                if prior is not None and prior['value'] != labels[i][q][h]:
                    conflicts.append(dict(first=prior['root'], second=i, candidate=q, head=HEADS[h], input_sha256=key))
                else:
                    seen[slot] = dict(root=i, value=labels[i][q][h])
    if conflicts:
        blockers.append('complete-typed-public-input-known-label-conflict')
    arrays = dict(candidate_features=np.asarray(features, dtype=np.float32), targets=np.asarray(labels, dtype=np.float32),
        target_mask=np.asarray(masks, dtype=np.float32), selected_candidate_indices=np.asarray(selected, dtype=np.int64),
        program_indices=np.asarray(indices, dtype=np.int64), program_bits=np.asarray([p['bits'] for p in programs], dtype=np.int64),
        typed_features=np.asarray(typed, dtype=np.float32),
        world_ids=np.arange(128, dtype=np.int64), source_cards=np.asarray(identities),
        program_ids=np.asarray([p['code'] for p in programs]), train_idx=np.asarray(train, dtype=np.int64), held_idx=np.asarray(held, dtype=np.int64),
        baseline_predictions=np.asarray(baselines, dtype=np.float32))
    arrays['primary_target_mask'] = np.asarray(primary, dtype=np.float32)
    manifest = dict(schema=SCHEMA, synthetic_programs=True, real_card_semantic_claim=False, semantic_validated=False,
        candidate_order=copy.deepcopy(roles), candidate_feature_names=list(FEATURES), target_names=list(HEADS),
        program_bit_names=list(BIT_NAMES), typed_field_names=list(TYPED_FIELDS),
        physics_scales=dict(PHYSICS_SCALES), normalization='Fixed physics constants; no TRAIN or HELD transform fitting',
        programs=copy.deepcopy(programs), plan=copy.deepcopy(plan), split=dict(train=train, held=held, program_balance=balance),
        printed_metadata_audit=dict(fields=list(printed_keys), identical_profiles=True, sha256=digest(printed_profiles[0])),
        public_before_records=records, physical_identity_refs=[copy.deepcopy(c['refs']) for c in cases],
        identity_renaming_audits=audits, native_status=statuses, native_apply_calls=receipt['applyCalls'], journal_proof=proof,
        terminal_counts={t: sum(s['terminal'] == t for s in statuses) for t in TERMINALS},
        class_counts=counts, primary_class_counts=primary_counts, stratum_support=strata,
        analytical_primitive=dict(scope='Comparator only; never training labels or mask source. No healthy-heal exclusions.',
            mismatch_count=len(mismatches), mismatches=mismatches, coverage=coverage,
            healthy_heal_mismatches=sum(m['healthy_healing'] for m in mismatches),
            healthy_healing_observations=healthy, healthy_healing_complete=healthy_complete,
            exact_complete_native_reference_pass=not blockers),
        input_conflicts=dict(count=len(conflicts), conflicts=conflicts,
            scope='Actual per-candidate typed8 plus public8 inputs; both labels must be known to conflict.'),
        fit_admitted=not blockers, fit_blockers=blockers,
        witnesses=[dict(native_targets=labels[i], native_masks=masks[i], primitive_predictions=baselines[i],
                        input_sha256=digest(features[i]), **statuses[i]) for i in range(128)],
        independent_samples=dict(programs=32, train_programs=16, held_programs=16, roots=128,
            limitation='Four repeated synthetic worlds per program; coordinates/checks are not independent samples.'),
        label_policy='Reached native action membership; effect deltas only after actual offered committed settled actions. Cancel/prompt-only futures unknown.',
        input_policy='Strict BEFORE public owner/arena/cost/damage/HP/intended equality. Physical/code IDs only separate provenance, never numeric inputs.')
    require(all(a['physical_id_and_code_renaming_invariant'] for a in audits), 'identity-removal audit failed')
    return arrays, manifest
