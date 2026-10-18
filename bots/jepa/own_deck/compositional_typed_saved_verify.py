"""Narrow saved-journal recovery adapter around the unchanged independent verifier.

No engine/model execution and no synthetic validation captures. The original
native stage remains failed and fully charged. Only its complete fsynced case
journal supplies observations. Original label/reference/metric/gate helpers are
imported unchanged; the orchestration differences are locked by a transform test.
The root owns the sealed saved-only stage and NumPy import.
"""
from pathlib import Path
import copy
import json
import math

import compositional_typed_verify as V
from compositional_typed_verify import (SCHEMA, SEEDS, ARMS, COUNTS, FEATURES, require,
    digest, pin, read, rows, write_new, close, parity, parse_program, native_journal,
    native_case, reference, consumed_conflicts, public_features, load_npz, bank_audit,
    loss_statistics, array_hash, progress_audit, named_hash, evaluations, source_contrasts,
    gate, comparative)

ORIGINAL_VERIFIER_SHA256 = '0bfbf1b1a397b311b27741e8966c655722f9d3d7775e8baf59e957e7b75d405c'
COLLECTOR_SOURCE_SHA256 = '488780ca5726f7d0a9fbdd25b76b2a32490d01df3441f0492511198671d66b27'
FIXTURE_SCOPE = 'source-control-flow-attestation-only; no persisted per-fixture validation records'


def checked_chain(ledger):
    previous = '0' * 64
    for i, row in enumerate(ledger):
        body = {k: v for k, v in row.items() if k != 'record_sha256'}
        require(row['schema'] == 'jepa-sealed-budget-journal/1' and row['sequence'] == i and
                row['previous_sha256'] == previous and row['record_sha256'] == digest(body),
                'original failed journal chain changed')
        previous = row['record_sha256']
    require(ledger and ledger[0]['event'] == 'initialized', 'original initialized journal required')
    return previous


def recovery_audit(root, raw, plan_path, trace_path, spec):
    require(pin(V.__file__)['sha256'] == ORIGINAL_VERIFIER_SHA256, 'unchanged original independent verifier required')
    require('fixtureValidation' not in raw and isinstance(raw.get('recovery_provenance'), dict),
            'recovery cannot fabricate missing per-fixture validation records')
    p = raw['recovery_provenance']
    keys = ('source_journal', 'source_plan', 'failed_ledger', 'failed_stage_receipt',
            'built_binary', 'collector_source', 'source_campaign_spec')
    frozen = {v['path']: v for v in spec['pins']}
    parent = read(spec['parent_manifest']['path'])
    for field in keys:
        proof = p[field]
        require(pin(proof['path']) == proof, 'recovered source provenance changed: ' + field)
        require(proof in parent['pins'] or frozen.get(proof['path']) == proof,
                'recovery source not in the frozen parent/input closure: ' + field)
    require(p['fixture_validation_scope'] == FIXTURE_SCOPE and p['per_fixture_validation_records_persisted'] is False and
            p['source_observed_native_applies'] == 256 and p['source_charged_native_applies'] == 512 and
            p['new_native_applies'] == 0 and p['no_credit'] is True, 'recovery observation/charge distinction changed')
    require(pin(plan_path)['sha256'] == p['source_plan']['sha256'] and
            pin(plan_path)['bytes'] == p['source_plan']['bytes'] and
            pin(trace_path)['sha256'] == p['source_journal']['sha256'] and
            pin(trace_path)['bytes'] == p['source_journal']['bytes'], 'plan/trace copy is not byte exact')
    source_spec = read(p['source_campaign_spec']['path'])
    require(pin(source_spec['parent_manifest']['path']) == source_spec['parent_manifest'], 'original parent manifest bytes changed')
    old_parent = read(source_spec['parent_manifest']['path'])
    ledger = rows(p['failed_ledger']['path']); final_chain = checked_chain(ledger)
    require(ledger[0]['data']['spec'] == p['source_campaign_spec'], 'original failed source spec not bound to its journal')
    finishes = [r['data'] for r in ledger if r['event'] == 'finish']
    require([r['data']['stage'] for r in ledger if r['event'] == 'begin'] == ['metadata', 'build', 'native'] and
            len(finishes) == 3 and ledger[-1]['event'] == 'finish' and
            [r['status'] for r in finishes] == ['completed', 'completed', 'failed'],
            'original native failure/reset/retry status differs')
    failed = finishes[-1]
    require(failed['charged']['native_applies'] == 512 and failed['charged']['seconds'] >= 30. and
            failed['durable_intents']['native_applies'] == 512 and failed['durable_completed']['native_applies'] == 0 and
            failed['cleanup_verified'] is True and failed['execution_ended'] is True,
            'original conservative failed native reservation must stay fully charged')
    require(p['built_binary'] in finishes[1]['proofs'], 'built binary not witnessed by original completed build')
    require(p['source_journal'] in failed['proofs'] and p['failed_stage_receipt'] in failed['proofs'],
            'original failed finish must bind its exact source trace and stage receipt')
    failure_receipt = read(p['failed_stage_receipt']['path'])
    require(failure_receipt['stage'] == 'native' and failure_receipt['status'] == 'failed' and
            failure_receipt['cleanup_verified'] is True and
            failure_receipt['child_argv'][0] == p['built_binary']['path'] and
            failure_receipt['child_argv'][1] == p['source_plan']['path'] and
            failure_receipt['child_argv'][3] == p['source_journal']['path'], 'failed stage/binary route provenance differs')
    carry = parent['carry']; prior = old_parent['carry']
    require(carry['charged_native_applies'] == prior['charged_native_applies'] + sum(v['charged']['native_applies'] for v in finishes) and
            math.isclose(carry['charged_seconds'], prior['charged_seconds'] + sum(v['charged']['seconds'] for v in finishes), abs_tol=1e-9) and
            carry['observed_native_applies'] is None, 'new parent credited/reset historical exposure or unknown observations')
    source = Path(p['collector_source']['path']).read_text()
    require(p['collector_source']['sha256'] == COLLECTOR_SOURCE_SHA256 and
            p['collector_source'] in source_spec['pins'], 'reviewed native source/binary build closure differs')
    begin = source.index('fn run(plan_path:')
    validation = source.index('let validation=validate_fixtures(&engine,&plan)?;', begin)
    journal = source.index('let mut journal=fs::OpenOptions::new().write(true).create_new(true).open(journal_path)', begin)
    application = source.index('let mut budget=Budget{started,calls:0', begin)
    require(begin < validation < journal < application and
            'for (i,w)in worlds.iter().enumerate()' in source and
            'snapshot!=e.snapshot(&loaded)||e.legal_actions(&s)!=e.legal_actions(&loaded)' in source,
            'reviewed all-fixture validation no longer precedes journal/application creation')
    return dict(source_observed_native_applies=256, source_charged_native_applies=512,
        new_native_applies=0, no_credit=True, failed_source_final_chain=final_chain,
        fixture_validation_scope=FIXTURE_SCOPE, per_fixture_validation_records_persisted=False,
        control_flow=dict(collector_source=p['collector_source'], built_binary=p['built_binary'],
            all_fixture_validation_call_offset=validation, journal_creation_offset=journal,
            first_budget_creation_offset=application),
        source_pins={key: p[key] for key in keys},
        limitation='Header existence plus reviewed unchanged built-source control flow attests validation returned. Individual validation snapshots were not durably retained and are not reconstructed.')


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
    require(pending == 'verify' and list(stages) == ['recover', 'prep', 'fit'] and fit_finish,
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
                native_applies=sum(stage['durable_completed']['native_applies'] for stage in stages.values()), last_chain=previous)


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
        recovery = recovery_audit(root, raw, plan_path, trace_path, spec)
        for i, (case, world) in enumerate(zip(raw['cases'], plan['worlds'])):
            require(case['world_id'] == world['id'] == i and case['program_index'] == world['program_index'] == i // 4 and
                    case['root_variant'] == world['root_variant'] == i % 4 and case['card'] == world['source_code'] == programs[i // 4]['code'] and
                    case['partition'] == world['partition'] == programs[i // 4]['partition'] and case['declared_intent']['ref'] == world['intent_ref'],
                    'native root/program/split alignment differs')
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
        require(budget['native_applies'] == 0 and native['native_applies'] == recovery['source_observed_native_applies'] == 256,
                'recovery must not charge new calls or invent/credit original native calls')
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
        report.update(status='passed', native=native, recovery=recovery, original_verifier=pin(V.__file__), reference=dict(known_eligibility=2048, known_effects=1536,
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
