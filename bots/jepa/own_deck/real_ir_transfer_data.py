"""Public real-IR transfer data and a deterministic typed physics comparator.

Import is standard-library only and does no I/O. prepare_data receives NumPy
from its guarded caller; it never fits, constructs a model, or runs an engine.
Menus/transitions supply labels. The reference is an independent admission
comparison, never a label or learned-feature source.
"""
import copy
import hashlib
import json
import math

import real_ir_adapter as A
import real_ir_reservation_v3 as R

SCHEMA = 'jepa-real-ir-transfer-data/1'
ROLES = ('p1_ground', 'p2_ground', 'p1_space', 'p2_space', 'own_base', 'opponent_base')
TRAIN = ('IBH_013', 'IBH_066', 'IBH_061', 'TWI_174', 'IBH_059')
HELD = ('JTL_075', 'TWI_170')
PROGRAM_FIELDS = ('owner_allowed_self', 'owner_allowed_opponent', 'target_unit_allowed',
    'target_leader_unit_allowed', 'target_base_allowed', 'zone_ground_allowed',
    'zone_space_allowed', 'zone_base_allowed', 'cost_cap_present', 'cost_cap',
    'op_damage', 'op_heal', 'amount')
CANDIDATE_FIELDS = ('owner_self', 'owner_opponent', 'is_unit', 'is_base', 'is_leader',
    'zone_ground', 'zone_space', 'zone_base', 'attackable', 'printed_cost',
    'cost_known', 'cost_applicable', 'damage', 'damage_known', 'hp', 'hp_known', 'is_intended')
PRINTED_FIELDS = ('cost', 'cost_known', 'hp', 'hp_known', 'power', 'power_known',
                  'unique', 'is_event', 'is_unit', 'is_base')
TARGET_NAMES = ('target_allowed', 'target_damage_delta')
TERMINALS = ('settled-committed', 'settled-cancelled', 'unoffered-prompt-only')


def require(ok, message):
    if not ok: raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value):
    require(type(value) in (int, float), 'explicit numeric value required')
    try: require(math.isfinite(value), 'finite numeric value required')
    except OverflowError as error: raise ValueError('finite numeric value required') from error
    return float(value)


def encode_program(program):
    """P13: typed allowed sets; no predicate joined to a candidate's truth."""
    require(program.get('schema') == 'jepa-real-ir-program/1' and program.get('form') == 'chosen-constant' and
            program.get('side') == 'card' and program.get('trigger') == 'event' and program.get('costs') == [] and
            all(program.get(k) is False for k in ('optional', 'requires_confirmation', 'coordinate', 'attacker_must_survive')),
            'initial transfer task requires the complete simple event form')
    selector, effect = program['selector'], program['effect']
    require(selector.get('optional') is False and selector.get('mode') in (None, 'single') and selector.get('count') is None,
            'extra selection behavior unsupported by this task')
    owner = selector['owner']; kind = selector['target_kind']; zone = selector['zone']['value']
    require(owner in ('any', 'self', 'opponent') and kind in ('any', 'unit', 'nonLeaderUnit', 'base') and
            zone in (None, 'anyAttackable', 'arena', 'base'), 'unreviewed owner/type/zone')
    owners = {'any': [1., 1.], 'self': [1., 0.], 'opponent': [0., 1.]}[owner]
    kinds = {'any': [1., 1., 1.], 'unit': [1., 1., 0.],
             'nonLeaderUnit': [1., 0., 0.], 'base': [0., 0., 1.]}[kind]
    zones = [1., 1., 1.] if zone in (None, 'anyAttackable') else [1., 1., 0.] if zone == 'arena' else [0., 0., 1.]
    arena = selector['arena']
    require(type(arena['present']) is bool, 'explicit arena presence required')
    if arena['present']:
        require(arena['values'] in (['ground'], ['space']), 'reviewed singleton arena constraint required')
        zones = [zones[0] * float('ground' in arena['values']), zones[1] * float('space' in arena['values']), 0.]
    else: require(arena['values'] is None, 'absent arena must remain unrestricted, never ground')
    cap = selector['cost_cap']; require(type(cap['present']) is bool, 'explicit cost-cap presence required')
    if cap['present']:
        value = number(cap['value']); require(value >= 0, 'nonnegative raw cost cap required')
    else:
        require(cap['value'] is None, 'absent cost cap must remain unbounded'); value = 0.
    require(effect['operator'] in ('damage', 'heal') and effect['destination'] == 'chosen' and
            effect['amount']['kind'] == 'const', 'one complete chosen literal damage/heal effect required')
    amount = number(effect['amount']['value']); require(amount > 0, 'positive actual literal amount required')
    return owners + kinds + zones + [float(cap['present']), value,
        float(effect['operator'] == 'damage'), float(effect['operator'] == 'heal'), amount]


def encode_printed(adapted):
    """S10 is a narrow numeric/type control, not all printed metadata."""
    p = adapted['printed_profile']; result = []
    for name in ('cost', 'hp', 'power'):
        require(type(p[name]['known']) is bool, 'explicit printed numeric knownness required')
        if p[name]['known']: value = number(p[name]['value'])
        else: require(p[name]['value'] is None, 'unknown printed numeric must retain null'); value = 0.
        result.extend([value, float(p[name]['known'])])
    require(p['unique']['known'] is True and type(p['unique']['value']) is bool and p['types']['known'] is True,
            'complete printed Boolean/type metadata required')
    return result + [float(p['unique']['value']), *[float(t in p['types']['value']) for t in ('event', 'unit', 'base')]]


def encode_candidate(projection, intended_id, acting_owner, public_row):
    """C17: raw public physics and applicability flags; physical IDs only bind equality."""
    p = projection; require(acting_owner in ('p1', 'p2'), 'known actual source owner required')
    require(p.get('present') is True and p.get('attackable') is True and p.get('zone') in ('ground', 'space', 'base') and
            all(p.get('known', {}).get(k) is True for k in ('identity', 'owner', 'damage', 'hp')),
            'complete known present public attackable candidate required')
    require(type(p.get('is_unit')) is bool and type(p.get('is_base')) is bool and
            p['is_unit'] != p['is_base'] and p['owner'] in ('p1', 'p2') and isinstance(p.get('id'), str) and p['id'] and
            isinstance(intended_id, str), 'explicit physical kind/owner/identity required')
    types = public_row['card']['types']; require(isinstance(types, list), 'public definition types required')
    leader = 'leader' in types
    require((p['is_base'] and 'base' in types and p['zone'] == 'base') or
            (p['is_unit'] and ('unit' in types or leader) and p['zone'] in ('ground', 'space') and p.get('in_arena') is True),
            'public type and physical zone disagree')
    hp, damage = number(p['hp']), number(p['damage']); require(hp > 0 and 0 <= damage < hp, 'living candidate physics required')
    applicable = p['is_unit']; known = p.get('known', {}).get('printed_cost') is True
    if applicable:
        require(known, 'unit printed cost unknown'); cost = number(p['printed_cost']); require(cost >= 0, 'nonnegative printed cost required')
        require(cost == number(public_row['card']['cost']), 'native unit printed cost differs from the intact public row')
    else:
        require(not known and p.get('printed_cost') is None, 'base cost must be null/not applicable, never fabricated zero')
        cost = 0.
    return [float(p['owner'] == acting_owner), float(p['owner'] != acting_owner),
        float(p['is_unit']), float(p['is_base']), float(leader),
        float(p['zone'] == 'ground'), float(p['zone'] == 'space'), float(p['zone'] == 'base'), 1.,
        cost, float(known), float(applicable), damage, 1., hp, 1., float(p['id'] == intended_id)]


def reference(program, candidates):
    """Literal selector/physics interpreter, independent of learned projections."""
    encode_program(program)  # Fail closed on unsupported semantics, not a numerical fit.
    selector, effect = program['selector'], program['effect']; result = []
    for p in candidates:
        unit = p['is_unit']; base = p['is_base']; zone = p['zone']; own = p['owner_self']
        allowed = selector['owner'] == 'any' or (selector['owner'] == 'self' and own) or (selector['owner'] == 'opponent' and not own)
        kind = selector['target_kind']
        allowed = allowed and (kind == 'any' or kind == 'base' and base or kind == 'unit' and unit or
            kind == 'nonLeaderUnit' and unit and not p['is_leader'])
        z = selector['zone']['value']
        allowed = allowed and (z in (None, 'anyAttackable') and p['attackable'] or
            z == 'arena' and unit and zone in ('ground', 'space') or z == 'base' and base)
        if selector['arena']['present']: allowed = allowed and zone in selector['arena']['values']
        if selector['cost_cap']['present']:
            # Undefined base-cost predicates are outside this initial reviewed task.
            require(not allowed or p['cost_known'] and p['cost_applicable'], 'cost predicate on an undefined base cost requires native semantic review')
            allowed = allowed and p['printed_cost'] <= selector['cost_cap']['value']
        delta = 0.
        if allowed and p['is_intended']:
            amount = number(effect['amount']['value'])
            delta = amount if effect['operator'] == 'damage' else -min(amount, number(p['damage']))
        result.append([float(allowed), delta])
    return result


def public_scene(case, roles, catalogue):
    before, refs, intent = case['before'], case['refs'], case['declared_intent']
    source = before['projections']['source']; owner = source['owner']
    require(owner == 'p1' and source.get('known', {}).get('owner') is True and
            intent.get('requires_target') is True and intent['ref'] in roles and intent['id'] == refs[intent['ref']],
            'known pre-action actor/intended reference required')
    require(len({refs[role] for role in roles}) == len(roles), 'physical candidate identities must be distinct')
    features, records, rename_hashes = [], [], []
    for role in roles:
        p = before['projections'][role]; require(p['id'] == refs[role] and p['code'] in catalogue, 'candidate public identity/catalogue mismatch')
        row = catalogue[p['code']]; f = encode_candidate(p, intent['id'], owner, row); features.append(f)
        records.append(dict(owner=p['owner'], owner_self=p['owner'] == owner, zone=p['zone'], is_unit=p['is_unit'],
            is_base=p['is_base'], is_leader=bool(f[4]), attackable=p['attackable'], printed_cost=p['printed_cost'],
            cost_known=bool(f[10]), cost_applicable=bool(f[11]), damage=p['damage'], hp=p['hp'],
            is_intended=bool(f[16]), known={k: p['known'][k] for k in ('identity', 'owner', 'damage', 'hp', 'printed_cost')}))
        renamed = dict(p); renamed['id'] = 'opaque-' + role; renamed['code'] = 'opaque-source-code'
        renamed_row = copy.deepcopy(row); renamed_row['card']['id'] = 'opaque'; renamed_row['card']['title'] = 'opaque'
        renamed_intent = renamed['id'] if p['id'] == intent['id'] else 'opaque-other'
        same = encode_candidate(renamed, renamed_intent, owner, renamed_row)
        require(f == same, 'candidate semantic input depends on code/physical spelling')
        rename_hashes.append(digest(same))
    require(sum(f[16] for f in features) == 1., 'exactly one declared intended candidate required')
    return features, records, dict(original_sha256=digest(features), renamed_sha256=digest(features),
        per_candidate_renamed_sha256=rename_hashes, invariant=True,
        scope='Only BEFORE physics/type/owner and intended equality are consumed; code/title/ID spelling ignored')


def fixture_proof(case, world, roles, catalogue):
    before, refs = case['before'], case['refs']; players = before['state']['players']
    require(before['decision'] == 'Window' and before.get('settled') is True and
            all(players[p]['deck'] == [] for p in ('p1', 'p2')) and players['p2']['hand'] == players['p2']['resources'] == [] and
            len(players['p1']['resources']) == 12 and
            [v['id'] for v in players['p1']['hand']] == [refs['source']], 'private piles or initial native window differ')
    source = before['projections']['source']
    require(source['id'] == refs['source'] and source['code'] == case['card'] and source['zone'] == 'hand', 'declared own-hand event source required')
    arena_ids = [v['id'] for p in ('p1', 'p2') for z in ('ground', 'space') for v in players[p][z]]
    require(len(arena_ids) == len(set(arena_ids)) == 4 and set(arena_ids) == {refs[r] for r in roles[:4]}, 'unrepresented public arena unit')
    for role in roles[:4]:
        p, spec = before['projections'][role], world['arena_cards'][role]; row = catalogue[p['code']]
        adapted = A.adapt_row(row)
        require(adapted['full_card_supported'] is True and adapted['canonical_program']['form'] == 'plain-profile' and
                p['code'] == spec['code'] and p['owner'] == spec['owner'] and p['zone'] == spec['arena'] and
                number(p['damage']) == number(spec['damage']) and number(p['hp']) == number(row['card']['hp']) and
                number(p['power']) == number(row['card']['power']) and p.get('exhausted') is False and
                p.get('shield_count') == p.get('xp_count') == 0, 'actual plain natural unit fixture differs')
        require(number(p['damage']) + 4 < number(p['hp']), 'all literal-damage4 intended unit outcomes must survive')
    for role, player, damage_key in (('own_base', 'p1', 'own_base_damage'), ('opponent_base', 'p2', 'opponent_base_damage')):
        p = before['projections'][role]
        adapted = A.adapt_row(catalogue[p['code']])
        require(adapted['full_card_supported'] is True and adapted['canonical_program']['form'] == 'plain-profile',
                'actual base helper must be a complete plain supported profile')
        require(players[player]['base']['id'] == refs[role] == p['id'] and p['owner'] == player and
                p['is_base'] is True and p['zone'] == 'base' and number(p['damage']) == number(world[damage_key]) and
                number(p['hp']) == number(catalogue[p['code']]['card']['hp']) and number(p['damage']) + 4 < number(p['hp']),
                'actual natural base fixture differs')


def derive_labels(case, roles):
    """Eligibility from a reached menu; only observed committed intended deltas."""
    require(case.get('engineError') is None and case.get('publicSnapshotRoundtripExact') is True and
            case.get('steps'), 'complete error-free native root required')
    before, refs, intent = case['before'], case['refs'], case['declared_intent']; selected = roles.index(intent['ref'])
    last, captures, selected_steps, cancelled = before, [before], [], []
    for i, step in enumerate(case['steps']):
        require(step['before'] == last and step['action'] in last['offeredActions'], 'native action discontinuity or unoffered action')
        if i == 0:
            require(step['stage'] == 'play-own-hand' and step['action'] == case['playAction'] and step['action'].get('card') == refs['source'],
                    'actual offered own-hand source play required')
        elif step['stage'] == 'chosen-target':
            require(last == case['targetPrompt'] and step['action'] == case['targetAction'] and step['action'].get('card') == intent['id'],
                    'substituted or undeclared native target')
            selected_steps.append(step)
        elif step['stage'] == 'decline-unoffered-target':
            require(step['action'] == case['declineAction'] and step['action'].get('arg') == 'cancel' and step['action'].get('label') == 'Cancel',
                    'decline must be an actual offered Cancel')
            cancelled.append(step)
        else: raise ValueError('unreviewed native continuation')
        last = step['after']; captures.append(last)
    prompt = case['targetPrompt']
    require(prompt in captures and prompt['decision'] == 'AbilityTarget' and last == case['lastObserved'] and
            len(selected_steps) <= 1 and len(cancelled) <= 1 and len(case['steps']) == case['applyCalls'] <= 3,
            'native prompt/last boundary/count differs')
    target = [[float(any(a.get('card') == refs[r] for a in prompt['offeredActions'])), 0.] for r in roles]
    mask = [[1., 0.] for _ in roles]
    offered = bool(target[selected][0]); committed = bool(selected_steps)
    require(type(case['intentOffered']) is bool and case['intentOffered'] == offered and
            type(case['intendedTargetCommitted']) is bool and case['intendedTargetCommitted'] == committed,
            'actual membership/commit flag differs')
    terminal = case['terminalClassification']; require(terminal in TERMINALS, 'typed completed native terminal required')
    if terminal == 'unoffered-prompt-only':
        require(not offered and not committed and not cancelled and case['final'] is None and last == prompt and
                case['completion'] == case['intentResolution'] == 'unoffered-observation-only' and
                not any(a.get('arg') == 'cancel' and a.get('label') == 'Cancel' for a in prompt['offeredActions']),
                'prompt-only cannot manufacture future or Cancel observations')
    else:
        final = case['final']
        require(final == last and final.get('settled') is True and case['completion'] == 'settled' and
                ((terminal == 'settled-committed') == committed) and ((terminal == 'settled-cancelled') == bool(cancelled)) and
                case['intentResolution'] == ('committed' if committed else 'unoffered-declined'), 'native endpoint not settled/classified')
        if committed:
            require(offered and not cancelled and final['projections']['source']['zone'] == 'discard',
                    'committed effect requires actual settled paid event entry')
            for j, role in enumerate(roles):
                a, z = before['projections'][role], final['projections'][role]
                require(a['id'] == z['id'] == refs[role], 'target physical identity changed')
                stable = (z.get('present') is True and z.get('attackable') is True and z.get('zone') == a['zone'] and
                    all(z.get('known', {}).get(k) is True for k in ('damage', 'hp')) and number(z['hp']) == number(a['hp']) and
                    number(z['damage']) < number(z['hp']))
                if j == selected:
                    if stable: target[j][1] = number(z['damage']) - number(a['damage']); mask[j][1] = 1.
                else:
                    require(stable and number(z['damage']) == number(a['damage']), 'unexpected unselected physical effect/death')
    return dict(targets=target, target_mask=mask, selected=selected, committed=committed, terminal=terminal)


def journal_proof(records, receipt):
    require(records and records[0].get('schema') == 'jepa-real-ir-transfer-apply-journal/1' and
            records[0].get('planSha256') == receipt['collectionPlanSha256'] and
            records[0].get('sourceRevision') == receipt['sourceRevision'] and
            records[0].get('maxApplyCalls') == 168 and records[0].get('expectedCases') == 56,
            'exact native journal provenance required')
    cursor, calls = 1, 0
    for case in receipt['cases']:
        require(0 < len(case['steps']) == case['applyCalls'] <= 3, 'structural per-root bound differs')
        for step in case['steps']:
            calls += 1; a, z = records[cursor:cursor + 2]; cursor += 2
            require(a['phase'] == 'beforeApply' and z['phase'] == 'afterApply' and
                a['applyCall'] == z['applyCall'] == calls and a['context'] == z['context'] == 'world-' + str(case['world_id']) + '-' + case['card'] and
                a['branch'] == z['branch'] == step['stage'] and a['before'] == step['before'] and
                a['offeredAction'] == step['action'] and z['after'] == step['after'], 'native trace/case action boundary differs')
        require(records[cursor]['phase'] == 'contextComplete' and records[cursor]['case'] == case, 'native context completion differs'); cursor += 1
    require(cursor == len(records) and calls == receipt['applyCalls'] <= 168, 'missing/extra/unpaired native application')
    return dict(native_applies=calls, roots=len(receipt['cases']), paired=True, label_origin='native offered actions and actual settled committed intended counters')


def support(targets, masks, indices):
    return {name: dict(known=sum(int(masks[i][j][h]) for i in indices for j in range(6)),
        positive=sum(int(bool(masks[i][j][h]) and targets[i][j][h] > 0) for i in indices for j in range(6)),
        negative=sum(int(bool(masks[i][j][h]) and targets[i][j][h] < 0) for i in indices for j in range(6)),
        zero=sum(int(bool(masks[i][j][h]) and targets[i][j][h] == 0) for i in indices for j in range(6))) for h, name in enumerate(TARGET_NAMES)}


def input_conflicts(programs, features, targets, masks, printed=None):
    """Known labels keyed by head-visible descriptors; masks never hide collisions.

    Typed eligibility excludes intended equality, operator/amount and target
    damage/HP. The numeric printed control deliberately loses rule information;
    its conflicts are descriptive, not a reason to alter the cohort.
    """
    seen = {}; conflicts = []
    for i, scene in enumerate(features):
        source = programs[i // 8] if printed is None else printed[i // 8]
        for j, candidate in enumerate(scene):
            for h, head in enumerate(TARGET_NAMES):
                if not masks[i][j][h]: continue
                source_input = source[:10] if h == 0 and printed is None else source
                candidate_input = candidate[:12] if h == 0 else candidate
                key = (head, digest([source_input, candidate_input])); y = targets[i][j][h]
                if key in seen and seen[key]['value'] != y:
                    conflicts.append(dict(head=head, first_root=seen[key]['root'], root=i, candidate=j,
                        first_value=seen[key]['value'], value=y, input_sha256=key[1]))
                else: seen.setdefault(key, dict(root=i, value=y))
    return dict(count=len(conflicts), conflicts=conflicts,
        scope='Head-local public/descriptor input only; no masks, source IDs, split or future provenance in hash')


def prepare_data(np, plan, receipt, journal_rows):
    """Guarded saved-only preparation; no transforms fitted and no model/engine calls."""
    require(plan['schema'] == 'jepa-real-ir-transfer-plan/1' and receipt['schema'] == 'jepa-real-ir-transfer-native/1' and
            plan.get('synthetic') is False and receipt.get('synthetic') is False and receipt['collectionComplete'] is True and
            receipt['collectionPlan'] == plan and receipt['programs'] == plan['programs'] and receipt['candidateOrder'] == plan['candidate_order'] and
            receipt['sourceRevision'] == plan['source_revision'], 'whole exact real/native plan required')
    programs, worlds, cases, roles = plan['programs'], plan['worlds'], receipt['cases'], plan['candidate_order']
    require(tuple(roles) == ROLES and len(programs) == 7 and len(worlds) == len(cases) == 56 and
            [p['code'] for p in programs] == [*TRAIN, *HELD], 'fixed7×8×6 real-card ABI required')
    require(set(plan['selected_whole_rows']) == set(plan['selected_whole_cards']), 'complete selected raw catalogue closure required')
    require(receipt.get('realCatalogueRowsUnchanged') is True, 'native raw source-row preservation proof required')
    catalogue = plan['selected_whole_rows']; canonical, program_vectors, printed_vectors = [], [], []
    for i, p in enumerate(programs):
        row = p['raw_card']; adapted = A.adapt_row(row)
        require(p['index'] == i and p['code'] == row['setCode'] and row == catalogue[p['code']] and
                adapted['full_card_supported'] is True and p['canonical_program'] == adapted['canonical_program'] and
                p['partition'] == ('train' if p['code'] in TRAIN else 'held'), 'full actual source/program/split admission differs')
        program = adapted['canonical_program']; canonical.append(program)
        program_vectors.append(encode_program(program)); printed_vectors.append(encode_printed(adapted))
    train_groups = {R.mechanism_family_key(canonical[i]) for i in range(5)}
    held_groups = {R.mechanism_family_key(canonical[i]) for i in range(5, 7)}
    require(len(train_groups) == 3 and len(held_groups) == 2 and not train_groups & held_groups,
            'numeric-abstracted full mechanism families overlap or counts differ')
    native_proof = journal_proof(journal_rows, receipt)
    require(len(receipt['fixtureValidation']) == 56, 'all56 direct pre-apply validation records required')
    features, targets, masks, selected, metadata, public_records, audits, baseline = ([] for _ in range(8))
    for i, (case, world) in enumerate(zip(cases, worlds)):
        q = i // 8; p = programs[q]
        require(world['id'] == case['world_id'] == i and world['program_index'] == case['program_index'] == q and
                world['root_variant'] == case['root_variant'] == i % 8 and case['card'] == world['source_code'] == p['code'] and
                case['partition'] == world['partition'] == p['partition'] and world['intent_ref'] == case['declared_intent']['ref'],
                'native world/card/intended partition mismatch')
        validation = receipt['fixtureValidation'][i]
        require(validation['world_id'] == i and validation['card'] == p['code'] and validation['before'] == case['before'] and
                validation['publicSnapshotRoundtripExact'] is True and validation['legalActionsRoundtripExact'] is True and
                validation['allProgramsAdmitted'] is True and validation['applyCalls'] == validation['actionsApplied'] == 0,
                'direct before-first-apply fixture validation witness differs')
        fixture_proof(case, world, roles, catalogue)
        f, records, audit = public_scene(case, roles, catalogue); derived = derive_labels(case, roles)
        reference_prediction = reference(canonical[q], records); j = derived['selected']; candidate = records[j]
        features.append(f); targets.append(derived['targets']); masks.append(derived['target_mask']); selected.append(j)
        public_records.append(records); audits.append(audit); baseline.append(reference_prediction)
        metadata.append(dict(root=i, world_id=i, root_variant=i % 8, program_index=q, source_card=p['code'], partition=p['partition'],
            operator=canonical[q]['effect']['operator'], amount=canonical[q]['effect']['amount']['value'], intent_role=roles[j],
            intent_domain='unit' if candidate['is_unit'] else 'base', intended_owner='self' if candidate['owner_self'] else 'opponent',
            intended_arena=candidate['zone'], healthy_intent=candidate['damage'] == 0,
            terminal=derived['terminal'], committed=derived['committed']))
    train = [i for i, m in enumerate(metadata) if m['partition'] == 'train']; held = [i for i in range(56) if i not in train]
    require(len(train) == 40 and len(held) == 16, '40/16 whole-card split required')
    # Same physical public boards/intents for every source; no source-cost/context shortcut.
    require(all(features[i] == features[i % 8] for i in range(56)), 'source programs received different consumed public contexts')
    mismatches, blockers = [], []
    for i in range(56):
        for j in range(6):
            for h, head in enumerate(TARGET_NAMES):
                if masks[i][j][h] and abs(targets[i][j][h] - baseline[i][j][h]) > 1e-6:
                    mismatches.append(dict(root=i, candidate=j, head=head, native=targets[i][j][h], reference=baseline[i][j][h]))
        if metadata[i]['committed'] and not masks[i][selected[i]][1]: blockers.append('missing-committed-intended-counter-' + str(i))
    if mismatches: blockers.append('native-reference-mismatch')
    expected_committed = sum(int(baseline[i][selected[i]][0]) for i in range(56))
    if sum(int(m['committed']) for m in metadata) != expected_committed: blockers.append('predeclared-eligible-intended-outcome-missing')
    counts = {key: support(targets, masks, ix) for key, ix in (('train', train), ('held', held))}
    conflicts = input_conflicts(program_vectors, features, targets, masks)
    printed_conflicts = input_conflicts(program_vectors, features, targets, masks, printed=printed_vectors)
    if conflicts['count']: blockers.append('typed-head-input-known-label-conflict')
    if counts['train'][TARGET_NAMES[0]]['positive'] == 0 or counts['train'][TARGET_NAMES[0]]['zero'] == 0:
        blockers.append('TRAIN-eligibility-class-support')
    for name in ('train', 'held'):
        if any(counts[name][TARGET_NAMES[1]][sign] == 0 for sign in ('positive', 'negative', 'zero')):
            blockers.append(name + '-signed-endpoint-support')
    slices = {'held_' + op + '_' + domain: [m['root'] for m in metadata if m['partition'] == 'held' and
              m['operator'] == op and m['intent_domain'] == domain] for op in ('damage', 'heal') for domain in ('unit', 'base')}
    slices.update({'held_healthy_heal_' + domain: [m['root'] for m in metadata if m['partition'] == 'held' and
                   m['operator'] == 'heal' and m['intent_domain'] == domain and m['healthy_intent']] for domain in ('unit', 'base')})
    for key, indices in slices.items():
        if not indices or any(not masks[i][selected[i]][1] for i in indices): blockers.append('missing-evaluation-support-' + key)
    held_positive_only = counts['held'][TARGET_NAMES[0]]['zero'] == 0 and counts['held'][TARGET_NAMES[0]]['positive'] > 0
    if not held_positive_only: blockers.append('held-all-positive-eligibility-contract-differed')
    arrays = dict(program_features=np.asarray(program_vectors, np.float32), source_printed_features=np.asarray(printed_vectors, np.float32),
        candidate_features=np.asarray(features, np.float32), program_indices=np.asarray([i // 8 for i in range(56)], np.int64),
        selected_candidate_indices=np.asarray(selected, np.int64), targets=np.asarray(targets, np.float32), target_mask=np.asarray(masks, np.float32),
        primary_target_mask=np.asarray(masks, np.float32), train_idx=np.asarray(train, np.int64), held_idx=np.asarray(held, np.int64),
        baseline_predictions=np.asarray(baseline, np.float32), baseline_mask=np.asarray(masks, np.float32),
        all_ones_eligibility=np.ones((56, 6), np.float32), world_ids=np.arange(56, dtype=np.int64),
        source_cards=np.asarray([m['source_card'] for m in metadata]), program_ids=np.asarray([p['code'] for p in programs]))
    manifest = dict(schema=SCHEMA, candidate_order=list(roles), program_feature_names=list(PROGRAM_FIELDS),
        candidate_feature_names=list(CANDIDATE_FIELDS), source_printed_feature_names=list(PRINTED_FIELDS), target_names=list(TARGET_NAMES),
        normalization='Raw native units; no fitted scales or statistics in data preparation.', programs=copy.deepcopy(programs),
        canonical_programs=canonical, source_printed_profiles=[A.adapt_row(p['raw_card'])['printed_profile'] for p in programs],
        exact_program_keys=[R.exact_program_key(p) for p in canonical], mechanism_family_keys=[R.mechanism_family_key(p) for p in canonical],
        mechanism_groups=dict(train=sorted(train_groups), held=sorted(held_groups)), split=dict(train=train, held=held),
        root_metadata=metadata, evaluation_slices=slices, public_before_records=public_records,
        physical_identity_refs=[copy.deepcopy(c['refs']) for c in cases], identity_renaming_audits=audits,
        public_context_matched_across_programs=True, public_context_sha256=[digest(f) for f in features],
        native_apply_calls=receipt['applyCalls'], journal_proof=native_proof, support=counts,
        per_program_support={p['code']: support(targets, masks, list(range(i * 8, i * 8 + 8))) for i, p in enumerate(programs)},
        reference=dict(known_coordinates=sum(int(v) for root in masks for candidate in root for v in candidate),
            known_eligibility=sum(int(c[0]) for root in masks for c in root), known_intended_deltas=sum(int(c[1]) for root in masks for c in root),
            mismatch_count=len(mismatches), mismatches=mismatches, theoretical_expected_commits=expected_committed, numerical_fits=0),
        input_conflicts=conflicts, numeric_printed_control_input_conflicts=printed_conflicts,
        held_eligibility=dict(positive_only=held_positive_only, balanced_accuracy=None, specificity=None,
            all_ones_control='Perfect on held eligibility; no general held-eligibility claim.' if held_positive_only else 'Native held eligibility differs from the predeclared all-positive cohort; fit blocked.'),
        feature_policy='BEFORE-only public candidate fields and typed program descriptors. No IDs/codes/display/style/family/split or menu/after truth enters numeric inputs.',
        label_policy='Native menu membership; only committed intended settled surviving damage-counter differences. Unknown cancelled/unoffered futures remain mask0.',
        scope='Seven actual complete simple event programs. Two held operator-specific templates nested in one new union-target form; not new primitives or general card semantics.',
        fit_admitted=not blockers, fit_blockers=blockers, semantic_validated=False, actual_deck_corpus_coverage_claim=False)
    return arrays, manifest
