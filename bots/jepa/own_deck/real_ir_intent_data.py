"""Conditional chosen-effect data; ROOT owns every guarded read and output write.

Whole source rows/trigger/optionality are preserved. P13 projects the declared
chosen effect conditional on funded source entry and choosing that effect. It
does not predict optional acceptance, source entry, or complete card behavior.
Only original PR45 roots0..39 train; new native rows are never additions.
"""
import copy
import json
from pathlib import Path

import real_ir_adapter as A
import real_ir_transfer_data as D
import real_ir_transfer_verify as V

SCHEMA = 'jepa-real-ir-intent-data/1'
EVENTS = (*D.TRAIN, *D.HELD)
TERMINAL = 'SOR_132'


def require(ok, message):
    if not ok: raise ValueError(message)


def val(a): return a.tolist() if hasattr(a, 'tolist') else copy.deepcopy(a)
def read(path): return json.loads(Path(path).read_text())


def project_program(program):
    """Known conditional projection, never a rewritten event/card definition."""
    require(program['schema'] == 'jepa-real-ir-program/1' and program['form'] == 'chosen-constant' and
        program['side'] == 'card' and program['trigger'] in ('event', 'whenPlayed') and program['costs'] == [] and
        type(program['optional']) is bool and all(program[k] is False for k in
            ('requires_confirmation', 'coordinate', 'attacker_must_survive')), 'unsupported complete chosen-effect projection')
    s, e = program['selector'], program['effect']
    require(s['optional'] is False and s['mode'] in (None, 'single') and s['count'] is None and
        e['destination'] == 'chosen' and e['operator'] in ('damage', 'heal') and e['amount']['kind'] == 'const' and
        type(e['amount']['value']) is int and e['amount']['value'] in (1, 2, 3, 4, 5), 'unreviewed selector/effect form')
    owner = {'any': [1., 1.], 'self': [1., 0.], 'opponent': [0., 1.]}[s['owner']]
    kind = {'any': [1., 1., 1.], 'unit': [1., 1., 0.], 'nonLeaderUnit': [1., 0., 0.], 'base': [0., 0., 1.]}[s['target_kind']]
    zone = {None: [1., 1., 1.], 'anyAttackable': [1., 1., 1.], 'arena': [1., 1., 0.], 'base': [0., 0., 1.]}[s['zone']['value']]
    if s['arena']['present']:
        require(s['arena']['values'] in (['ground'], ['space']), 'unreviewed arena restriction')
        zone = [zone[0] * float('ground' in s['arena']['values']), zone[1] * float('space' in s['arena']['values']), 0.]
    else: require(s['arena']['values'] is None, 'absent arena remains unrestricted')
    cap = s['cost_cap']; require(type(cap['present']) is bool, 'known cap applicability required')
    if cap['present']: require(type(cap['value']) is int and cap['value'] >= 0, 'raw nonnegative cap required')
    else: require(cap['value'] is None, 'absent cap is not a fabricated numeric bound')
    return owner + kind + zone + [float(cap['present']), float(cap['value'] or 0),
        float(e['operator'] == 'damage'), float(e['operator'] == 'heal'), float(e['amount']['value'])]


def reference(program, records):
    project_program(program); s, e = program['selector'], program['effect']; result = []
    for c in records:
        owner = s['owner'] == 'any' or s['owner'] == 'self' and c['owner_self'] or s['owner'] == 'opponent' and not c['owner_self']
        kind = s['target_kind']
        allowed = owner and (kind == 'any' or kind == 'unit' and c['is_unit'] or kind == 'base' and c['is_base'] or
            kind == 'nonLeaderUnit' and c['is_unit'] and not c['is_leader'])
        z = s['zone']['value']; allowed = allowed and (z in (None, 'anyAttackable') and c['attackable'] or
            z == 'arena' and c['is_unit'] and c['zone'] in ('ground', 'space') or z == 'base' and c['is_base'])
        if s['arena']['present']: allowed = allowed and c['zone'] in s['arena']['values']
        if s['cost_cap']['present']:
            require(not allowed or c['cost_known'] and c['cost_applicable'], 'undefined base cost predicate needs separate review')
            allowed = allowed and c['printed_cost'] <= s['cost_cap']['value']
        delta = 0.
        if allowed and c['is_intended']:
            delta = float(e['amount']['value']) if e['operator'] == 'damage' else -float(min(e['amount']['value'], c['damage']))
        result.append([float(bool(allowed)), delta])
    return result


def fixture(case, world, catalogue):
    before, refs = case['before'], case['refs']; players = before['state']['players']
    require(before['decision'] == 'Window' and before['settled'] is True and all(players[p]['deck'] == [] for p in ('p1', 'p2')) and
        players['p2']['hand'] == players['p2']['resources'] == [] and len(players['p1']['resources']) == 12 and
        [c['id'] for c in players['p1']['hand']] == [refs['source']], 'public/privacy/funded own-hand setup differs')
    source = before['projections']['source']
    require(source['id'] == refs['source'] and source['code'] == case['card'] and source['zone'] == 'hand' and source['owner'] == 'p1', 'whole own-hand source differs')
    arena_ids = [c['id'] for p in players.values() for z in ('ground', 'space') for c in p[z]]
    require(len(arena_ids) == len(set(arena_ids)) == 4 and set(arena_ids) == {refs[r] for r in D.ROLES[:4]}, 'extra initial public arena unit')
    for q, role in enumerate(D.ROLES):
        p = before['projections'][role]; row = catalogue[p['code']]; adapted = A.adapt_row(row)
        require(adapted['full_card_supported'] and adapted['canonical_program']['form'] == 'plain-profile' and
            p['hp'] == row['card']['hp'] and 0 <= p['damage'] < p['hp'], 'complete natural living plain helper required')
        if q < 4:
            spec = world['arena_cards'][role]
            require(p['code'] == spec['code'] and p['owner'] == spec['owner'] and p['zone'] == spec['arena'] and
                p['damage'] == spec['damage'] and p['power'] == row['card']['power'] and p['exhausted'] is False and
                p['shield_count'] == p['xp_count'] == 0, 'natural public arena helper differs')
        else:
            own = q == 4; owner = 'p1' if own else 'p2'
            require(p['zone'] == 'base' and p['owner'] == owner and players[owner]['base']['id'] == refs[role] and
                p['damage'] == world['own_base_damage' if own else 'opponent_base_damage'], 'natural public base differs')


def derive(case, program):
    """Actual menus/actions; departed damage counters remain unknown."""
    before, refs, intent = case['before'], case['refs'], case['declared_intent']; selected = D.ROLES.index(intent['ref'])
    require(case['engineError'] is None and case['publicSnapshotRoundtripExact'] is True and case['steps'], 'error-free actual root required')
    last, captures, chosen, declined = before, [before], [], []
    for i, step in enumerate(case['steps']):
        require(step['before'] == last and step['action'] in last['offeredActions'], 'unoffered or discontinuous native action')
        if i == 0:
            require(step['stage'] == 'play-own-hand' and step['action'] == case['playAction'] and step['action']['card'] == refs['source'], 'actual source play differs')
        elif step['stage'] == 'chosen-target':
            require(last == case['targetPrompt'] and step['action'] == case['targetAction'] and step['action']['card'] == intent['id'], 'replacement target forbidden'); chosen.append(step)
        else:
            require(step['action'] == case['declineAction'] and step['action'].get('card') is None and
                ((step['stage'] == 'decline-unoffered-target' and step['action'].get('arg') == 'cancel' and step['action'].get('label') == 'Cancel') or
                 (step['stage'] == 'decline-unoffered-optional' and program['trigger'] == 'whenPlayed' and program['optional'] is True and
                  step['action'].get('arg') == 'passAbility' and step['action'].get('label') == 'Pass')), 'decline must be the actual offered Cancel/optional Pass'); declined.append(step)
        last = step['after']; captures.append(last)
    prompt = case['targetPrompt']
    require(prompt in captures and prompt['decision'] == 'AbilityTarget' and last == case['lastObserved'] and
        len(chosen) <= 1 and len(declined) <= 1 and len(case['steps']) == case['applyCalls'] <= 3, 'prompt/settlement/call bound differs')
    targets = [[float(any(a.get('card') == refs[r] for a in prompt['offeredActions'])), 0.] for r in D.ROLES]
    masks = [[1., 0.] for _ in D.ROLES]; offered = bool(targets[selected][0]); committed = bool(chosen)
    require(case['intentOffered'] is offered and case['intendedTargetCommitted'] is committed, 'native membership/commit differs')
    removed = None
    if case['terminalClassification'] == 'unoffered-prompt-only':
        require(not offered and not committed and not declined and case['final'] is None and last == prompt and
            case['completion'] == case['intentResolution'] == 'unoffered-observation-only' and
            not any(a.get('arg') in ('cancel', 'passAbility') for a in prompt['offeredActions']), 'prompt-only cannot manufacture decline/future')
    else:
        final = case['final']
        require(final == last and final['settled'] is True and case['completion'] == 'settled' and
            case['terminalClassification'] == ('settled-committed' if committed else 'settled-declined') and
            case['intentResolution'] == ('committed' if committed else 'unoffered-declined') and
            ((committed and offered and not declined) or (not offered and not committed and bool(declined))), 'actual completed terminal differs')
        source = final['projections']['source']
        expected_zone = ('discard' if committed else 'hand') if program['trigger'] == 'event' else 'space'
        require(source['zone'] == expected_zone, 'source disposition differs from committed/cancelled event or paid whenPlayed entry')
        if program['trigger'] == 'whenPlayed':
            require(source['zone'] == 'space' and source['in_arena'] is True and source['known']['exhausted'] is True and
                source['exhausted'] is True, 'paid source remains in its actual arena exhausted after use/Pass')
        if committed:
            arena_ids = {c['id'] for p in final['state']['players'].values() for z in ('ground', 'space') for c in p[z]}
            for q, role in enumerate(D.ROLES):
                a, z = before['projections'][role], final['projections'][role]
                require(a['id'] == z['id'] == refs[role], 'physical target identity changed')
                departed = a['is_unit'] and refs[role] not in arena_ids
                if q == selected: removed = bool(departed)
                else: require(not departed, 'unexpected non-intended unit departure')
                if departed:
                    require(q == selected and z['zone'] not in ('ground', 'space') and z['attackable'] is False, 'departure wire/projection disagree')
                    continue
                require(z['zone'] == a['zone'] and z['present'] is True and all(z['known'][k] is True for k in ('damage', 'hp')) and
                    z['hp'] == a['hp'] and 0 <= z['damage'] < z['hp'], 'surviving known physical endpoint required')
                if q == selected: targets[q][1] = float(z['damage'] - a['damage']); masks[q][1] = 1.
                else: require(z['damage'] == a['damage'], 'unexpected non-intended damage change')
    return dict(targets=targets, mask=masks, selected=selected, committed=committed, removed=removed,
        extra_source_offered=any(a.get('card') == refs['source'] for a in prompt['offeredActions']))


def panel(plan, raw, journal):
    role = plan['panel_role']; require(role in ('development', 'terminal'), 'unknown native panel role')
    n = 56 if role == 'development' else 8
    require(plan['schema'] == 'jepa-real-ir-intent-plan/1' and raw['schema'] == 'jepa-real-ir-intent-native/1' and
        raw['collectionComplete'] is True and raw['collectionPlan'] == plan and raw['programs'] == plan['programs'] and
        raw['candidateOrder'] == plan['candidate_order'] == list(D.ROLES) and raw['sourceRevision'] == plan['source_revision'] and
        raw['synthetic'] is False and raw['realCatalogueRowsUnchanged'] is True, 'complete original-source native panel required')
    require(len(raw['cases']) == len(plan['worlds']) == len(raw['fixtureValidation']) == n and
        journal[0]['schema'] == 'jepa-real-ir-intent-apply-journal/1' and journal[0]['planSha256'] == raw['collectionPlanSha256'] and
        journal[0]['sourceRevision'] == raw['sourceRevision'] and journal[0]['expectedCases'] == n and
        journal[0]['maxApplyCalls'] == plan['collector_max_engine_applies'] and journal[0]['fixtureValidation'] == raw['fixtureValidation'], 'direct pre-first-apply fixture/header proof differs')
    data = dict(candidate_features=[], targets=[], target_mask=[], selected_candidate_indices=[], program_indices=[], source_cards=[], baseline_predictions=[])
    metadata, public, removals, mismatches, removal_errors = [], [], [], [], []
    cursor = 1; calls = 0
    programs = []
    for p in plan['programs']:
        adapted = A.adapt_row(p['raw_card'])
        require(adapted['full_card_supported'] and p['raw_card'] == plan['selected_whole_rows'][p['code']] and
            p['canonical_program'] == adapted['canonical_program'], 'complete supported source/canonical row differs')
        project_program(adapted['canonical_program']); programs.append(adapted)
    for i, (case, world) in enumerate(zip(raw['cases'], plan['worlds'])):
        q = i // 8; p = plan['programs'][q]; program = programs[q]['canonical_program']
        require(case['world_id'] == world['id'] == i and case['program_index'] == world['program_index'] == q and
            case['card'] == world['source_code'] == p['code'] and case['root_variant'] == world['root_variant'] == i % 8 and
            case['declared_intent']['ref'] == world['intent_ref'], 'root/card/intended alignment differs')
        v = raw['fixtureValidation'][i]
        require(v['world_id'] == i and v['card'] == p['code'] and v['before'] == case['before'] and
            all(v[k] is True for k in ('publicSnapshotRoundtripExact', 'legalActionsRoundtripExact', 'allProgramsAdmitted')) and
            v['applyCalls'] == v['actionsApplied'] == 0, 'direct complete fixture witness differs')
        fixture(case, world, plan['selected_whole_rows'])
        features, records, _ = D.public_scene(case, D.ROLES, plan['selected_whole_rows']); observed = derive(case, program)
        expected = reference(program, records); j = observed['selected']; c = records[j]
        for h in range(2):
            for k in range(6):
                if observed['mask'][k][h] and abs(observed['targets'][k][h] - expected[k][h]) > 1e-6:
                    mismatches.append(dict(root=i, candidate=k, head=h, native=observed['targets'][k][h], reference=expected[k][h]))
        if observed['committed']:
            predicted_removal = c['is_unit'] and program['effect']['operator'] == 'damage' and c['damage'] + program['effect']['amount']['value'] >= c['hp']
            if observed['removed'] != predicted_removal: removal_errors.append(i)
            removals.append(dict(root=i, candidate=j, observed_removed=observed['removed'], expected_removed=predicted_removal,
                damage_counter_known=bool(observed['mask'][j][1]), source_card=p['code']))
        for key, value in (('candidate_features', features), ('targets', observed['targets']), ('target_mask', observed['mask']),
            ('selected_candidate_indices', j), ('program_indices', q), ('source_cards', p['code']), ('baseline_predictions', expected)):
            data[key].append(value)
        public.append(records)
        metadata.append(dict(root=i, world_id=i, source_card=p['code'], program_index=q, root_variant=i % 8, partition=p['partition'],
            operator=program['effect']['operator'], amount=program['effect']['amount']['value'], intent_role=D.ROLES[j],
            intent_domain='unit' if c['is_unit'] else 'base', intended_owner='self' if c['owner_self'] else 'opponent',
            intended_arena=c['zone'], healthy_intent=c['damage'] == 0, committed=observed['committed'], removed=observed['removed'],
            terminal=case['terminalClassification'], trigger=program['trigger'], optional=program['optional'], extra_source_offered=observed['extra_source_offered']))
        for step in case['steps']:
            calls += 1; a, z = journal[cursor:cursor + 2]; cursor += 2
            require(a['phase'] == 'beforeApply' and z['phase'] == 'afterApply' and a['applyCall'] == z['applyCall'] == calls and
                a['context'] == z['context'] == 'world-' + str(i) + '-' + p['code'] and a['branch'] == z['branch'] == step['stage'] and
                a['before'] == step['before'] and a['offeredAction'] == step['action'] and z['after'] == step['after'], 'native application pair differs')
        require(journal[cursor]['phase'] == 'contextComplete' and journal[cursor]['case'] == case, 'native complete context differs'); cursor += 1
    require(cursor == len(journal) and calls == raw['applyCalls'] <= plan['collector_max_engine_applies'] and
        all(data['candidate_features'][i] == data['candidate_features'][i % 8] for i in range(n)), 'native count/public board matching differs')
    count = sum(int(k[1]) for root in data['target_mask'] for k in root); removed = sum(int(v['observed_removed']) for v in removals)
    expected_counts = (35, 1) if role == 'development' else (4, 0)
    blockers = (['native-reference-mismatch'] if mismatches else []) + (['removal-reference-mismatch'] if removal_errors else [])
    if (count, removed) != expected_counts: blockers.append('predeclared-known-endpoint/removal-support')
    ref = dict(known_coordinates=n * 6 + count, known_eligibility=n * 6, known_intended_deltas=count,
        mismatch_count=len(mismatches), mismatches=mismatches, removed_count=removed, removal_mismatch_count=len(removal_errors))
    return data, dict(root_metadata=metadata, public_before_records=public, reference=ref, removal_witnesses=removals,
        blockers=blockers, native_apply_calls=calls, canonical_programs=[p['canonical_program'] for p in programs])


def tensorize(np, data):
    integer = {'program_indices', 'selected_candidate_indices', 'world_ids', 'train_idx', 'old_dev_idx', 'old_all_idx', 'development_all_idx', 'terminal_idx'}
    strings = {'source_cards', 'program_ids'}
    return {k: np.asarray(v, np.int64 if k in integer else None if k in strings else np.float32) for k, v in data.items()}


def prepare_development(np, oldroot, hp_root, newroot):
    oldroot, hp_root, root = map(Path, (oldroot, hp_root, newroot))
    old = {k: val(v) for k, v in V.npz(np, oldroot / 'prep-1/dataset.npz').items()}; om = read(oldroot / 'prep-1/manifest.json')
    hp = {k: val(v) for k, v in V.npz(np, hp_root / 'prep-1/dataset.npz').items()}; hm = read(hp_root / 'prep-1/manifest.json')
    require(om['fit_admitted'] is True and hm['fit_admitted'] is True and not om['fit_blockers'] and not hm['fit_blockers'] and
        all(m['reference'][k] == v for m in (om, hm) for k, v in
            dict(known_coordinates=375, known_eligibility=336, known_intended_deltas=39, mismatch_count=0).items()),
        'closed original/HP native-reference admission required')
    require(len(old['targets']) == 56 and len(hp['targets']) == 112 and old['held_idx'] == list(range(40, 56)) and
        hp['train_idx'] == old['train_idx'] == list(range(40)) and all(hp[k][:56] == old[k] for k in
            ('candidate_features', 'targets', 'target_mask', 'program_indices', 'selected_candidate_indices', 'source_cards')),
        'exact original56/HP112 lineage and original TRAIN40 required')
    plan_path = root / 'metadata-1/development-plan.json'; plan = read(plan_path); terminal_plan = read(root / 'metadata-1/terminal-plan.json')
    raw = read(root / 'dev-native-1/receipt.json'); require(raw['collectionPlanSha256'] == V.pin(plan_path)['sha256'], 'native development plan byte pin differs')
    fresh, fm = panel(plan, raw, V.rows(root / 'dev-native-1/transitions.jsonl'))
    require(tuple(p['code'] for p in plan['programs']) == EVENTS and terminal_plan['programs'][0]['code'] == TERMINAL and
        old['train_idx'] == list(range(40)), 'fixed event/terminal/original training reservation differs')
    all_programs = [*plan['programs'], *terminal_plan['programs']]; projected = [project_program(p['canonical_program']) for p in all_programs]
    printed = [D.encode_printed(A.adapt_row(p['raw_card'])) for p in all_programs]
    require(projected[:7] == old['program_features'] and printed[:7] == old['source_printed_features'], 'original card representation changed')
    def packet(metadata, features, i, q): return (metadata[i]['operator'], metadata[i]['amount'], features[i][q][12], features[i][q][14])
    prior = {packet(om['root_metadata'], old['candidate_features'], i, q) for i in range(56) for q in range(6) if old['target_mask'][i][q][1]}
    prior |= {packet(hm['root_metadata'], hp['candidate_features'], i, q) for i in range(56, 112) for q in range(6) if hp['target_mask'][i][q][1]}
    primary = [[[0., 0.] for _ in range(6)] for _ in range(112)]; replay = copy.deepcopy(primary); audit = []
    for i in range(56):
        for q in range(6):
            if fresh['target_mask'][i][q][1]:
                key = packet(fm['root_metadata'], fresh['candidate_features'], i, q); seen = key in prior
                (replay if seen else primary)[56 + i][q][1] = 1.; audit.append(dict(root=56 + i, candidate=q, tuple=list(key), replay=seen))
    support = dict(development_known_endpoints=fm['reference']['known_intended_deltas'], primary=int(sum(c[1] for r in primary for c in r)),
        replay=int(sum(c[1] for r in replay for c in r)), removed=fm['reference']['removed_count'])
    blockers = list(fm['blockers'])
    if support != dict(development_known_endpoints=35, primary=29, replay=6, removed=1): blockers.append('development29primary6replay1removed-support')
    data = {k: old[k] + fresh[k] for k in ('candidate_features', 'targets', 'target_mask', 'selected_candidate_indices', 'program_indices', 'source_cards', 'baseline_predictions')}
    data.update(program_features=projected, source_printed_features=printed, program_ids=[p['code'] for p in all_programs],
        primary_target_mask=primary, replay_target_mask=replay, terminal_target_mask=copy.deepcopy(primary))
    data['terminal_target_mask'] = [[[0., 0.] for _ in range(6)] for _ in range(112)]
    data.update(world_ids=list(range(112)), train_idx=list(range(40)), old_dev_idx=list(range(40, 56)), old_all_idx=list(range(56)),
        development_all_idx=list(range(56, 112)), terminal_idx=[])
    metadata = copy.deepcopy(om['root_metadata']) + copy.deepcopy(fm['root_metadata'])
    for i, m in enumerate(metadata): m.update(root=i, native_world_id=m['world_id'], world_id=i, source_campaign='old' if i < 56 else 'development')
    weights_path = oldroot / 'fit-1/loss-weights.json'
    manifest = dict(schema=SCHEMA, fit_admitted=not blockers, fit_blockers=blockers, support=support, reference=fm['reference'],
        root_metadata=metadata, public_before_records=om['public_before_records'] + fm['public_before_records'], programs=all_programs,
        canonical_programs=[p['canonical_program'] for p in all_programs], candidate_order=list(D.ROLES),
        program_feature_names=list(D.PROGRAM_FIELDS), candidate_feature_names=list(D.CANDIDATE_FIELDS), source_printed_feature_names=list(D.PRINTED_FIELDS),
        target_names=list(D.TARGET_NAMES), prior_endpoint_tuples=[list(p) for p in sorted(prior)], tuple_audit=audit,
        removal_witnesses=fm['removal_witnesses'], old_loss_weights=read(weights_path), old_loss_weights_pin=V.pin(weights_path),
        input_pins=[V.pin(p) for p in (oldroot / 'prep-1/dataset.npz', oldroot / 'prep-1/manifest.json',
            hp_root / 'prep-1/dataset.npz', hp_root / 'prep-1/manifest.json', plan_path,
            root / 'metadata-1/terminal-plan.json', root / 'dev-native-1/receipt.json',
            root / 'dev-native-1/transitions.jsonl', weights_path)],
        conditional_projection='Full IR/trigger/optionality preserved. P13 chosen effect conditional on funded entry and choosing the optional effect; no event rewrite/full-card forecast.',
        scope='Original TRAIN40 only. Seven exposed programs developmental; SOR132 terminal source only after checkpoints. Six pre-existing helpers exclude the entering source.',
        semantic_validated=False)
    return tensorize(np, data), manifest


def prepare_terminal(np, newroot):
    root = Path(newroot); data = {k: val(v) for k, v in V.npz(np, root / 'prep-1/dataset.npz').items()}; manifest = read(root / 'prep-1/manifest.json')
    path = root / 'metadata-1/terminal-plan.json'; plan = read(path); raw = read(root / 'terminal-native-1/receipt.json')
    require(raw['collectionPlanSha256'] == V.pin(path)['sha256'], 'native terminal plan byte pin differs')
    fresh, fm = panel(plan, raw, V.rows(root / 'terminal-native-1/transitions.jsonl'))
    require(len(data['targets']) == 112 and len(manifest['programs']) == 8 and plan['programs'][0]['code'] == TERMINAL and
        plan['programs'][0]['canonical_program'] == manifest['canonical_programs'][7], 'reserved terminal source/bank differs')
    for key in ('candidate_features', 'targets', 'target_mask', 'selected_candidate_indices', 'source_cards', 'baseline_predictions'): data[key] += fresh[key]
    data['program_indices'] += [7] * 8
    for key in ('primary_target_mask', 'replay_target_mask'): data[key] += [[[0., 0.] for _ in range(6)] for _ in range(8)]
    data['terminal_target_mask'] += fresh['target_mask']; data['terminal_idx'] = list(range(112, 120)); data['world_ids'] = list(range(120))
    for i, original in enumerate(fm['root_metadata']):
        m = copy.deepcopy(original); m.update(root=112 + i, native_world_id=m['world_id'], world_id=112 + i, program_index=7, source_campaign='terminal')
        manifest['root_metadata'].append(m)
    manifest['public_before_records'] += fm['public_before_records']; manifest['terminal_reference'] = fm['reference']
    manifest['terminal_blockers'] = list(fm['blockers']); manifest['terminal_admitted'] = not fm['blockers']
    manifest['terminal_removal_witnesses'] = fm['removal_witnesses']
    manifest['terminal_input_pins'] = [V.pin(p) for p in (root / 'prep-1/dataset.npz', root / 'prep-1/manifest.json',
        path, root / 'terminal-native-1/receipt.json', root / 'terminal-native-1/transitions.jsonl')]
    return tensorize(np, data), manifest
