"""Pure prelabel plans for factorized intent/application and one terminal card.

The seven prior event programs are developmental. Only SOR_132 is released from
the existing metadata reservation; the ground nearclones and HMW_158 stay unused.
No file I/O, numeric library, native application, model or outcome is involved.
"""
import copy
import hashlib
import json

EVENTS = ('IBH_013', 'IBH_066', 'IBH_061', 'TWI_174', 'IBH_059', 'JTL_075', 'TWI_170')
TERMINAL = 'SOR_132'
PRESERVED = ('ASH_259', 'LOF_259', 'HMW_158')
ROLES = ('p1_ground', 'p2_ground', 'p1_space', 'p2_space', 'own_base', 'opponent_base')
HELPERS = dict(base='ASH_019', leader='IBH_053', resource='LOF_256', ground='HMW_093', space='LOF_119')
LEVELS = (0, 1, 4, 6)
SCHEMA = 'jepa-real-ir-intent-plan/1'
REVISION = 'c7ee39554901278cee70f61fd8b26fb1920696b3'
CATALOGUE_SHA = '0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812'
RUNTIME_SHA = '91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def worlds(programs):
    result = []
    for q, p in enumerate(programs):
        for v in range(8):
            level = LEVELS[v % 4]; owner = 'p1' if v % 4 in (0, 2) else 'p2'
            other = 'p2' if owner == 'p1' else 'p1'
            intent = owner + '_space' if v < 4 else 'own_base' if owner == 'p1' else 'opponent_base'
            board = {}
            for role in ROLES[:4]:
                role_owner, arena = role.split('_')
                board[role] = dict(code=HELPERS[arena], owner=role_owner, arena=arena,
                    damage=1 if level == 0 and role == other + '_space' else level, exhausted=False)
            result.append(dict(id=q * 8 + v, source_code=p['code'], program_index=q, root_variant=v,
                partition=p['partition'], legacy_partition=p.get('legacy_partition'),
                damage_level=level, intended_domain='space-unit' if v < 4 else 'base',
                intent_ref=intent, requires_target=True, max_applies=3, ready_resources=12,
                arena_cards=board,
                own_base_damage=1 if level == 0 and other == 'p1' else level,
                opponent_base_damage=1 if level == 0 and other == 'p2' else level))
    return result


def build(old_plan, reservation):
    """Return immutable metadata panels; terminal outcomes must follow all fitting."""
    require(old_plan.get('schema') == 'jepa-real-ir-transfer-plan/1' and old_plan.get('synthetic') is False and
            old_plan.get('source_revision') == REVISION and old_plan.get('catalogue_sha256') == CATALOGUE_SHA and
            old_plan.get('runtime_sha256') == RUNTIME_SHA and old_plan.get('runtime_admitted_snapshot') == 1178,
            'complete unchanged pinned1178 original real-event plan required')
    require(tuple(p['code'] for p in old_plan['programs']) == EVENTS and old_plan['helpers'] == HELPERS and
            tuple(old_plan['candidate_order']) == ROLES, 'original event/helper order differs')
    require(reservation.get('status') == 'reserved-no-new-outcomes' and
            set(reservation.get('reserved_codes', [])) == {TERMINAL, *PRESERVED}, 'unconsumed four-source reservation required')
    reserved = {r['code']: r for r in reservation['cards']}
    require(set(reserved) == {TERMINAL, *PRESERVED}, 'complete existing reservation records required')
    terminal = reserved[TERMINAL]; row = terminal['raw_row']; ability = row['abilities']['card']
    require(digest(row) == terminal['whole_row_sha256'], 'reserved terminal whole-row digest differs')
    require(row['setCode'] == TERMINAL and row['id'] == '9002021213' and row['card']['types'] == ['unit'] and
            row['card']['hp'] == 2 and row['card']['arena'] == 'space' and row['card']['keywords'] == [] and
            len(ability) == 1 and ability[0].get('trigger') == 'whenPlayed' and ability[0].get('optional') is True and
            ability[0].get('targetResolver') == dict(owner='any', type='unit', zone='arena', arena='space') and
            ability[0].get('effect') == dict(kind='damage', target='chosen', amount=dict(kind='const', value=3)),
            'reserved complete optional space-unit damage3 whenPlayed source differs')
    require(not set(PRESERVED) & set(old_plan['selected_whole_cards']) and TERMINAL not in old_plan['selected_whole_rows'],
            'reserved sources already selected by parent event plan')
    dev = []
    for i, p in enumerate(old_plan['programs']):
        require(p['index'] == i and p['raw_card'] == old_plan['selected_whole_rows'][p['code']], 'whole event row differs')
        v = copy.deepcopy(p); v['legacy_partition'] = p['partition']; v['partition'] = 'developmental-state'; dev.append(v)
    held = dict(index=0, code=TERMINAL, partition='terminal-card', legacy_partition=None,
        raw_card=copy.deepcopy(row), canonical_program=copy.deepcopy(terminal['canonical_program']),
        aliases=copy.deepcopy(terminal['aliases']), exact_program_key=terminal['exact_program_key'],
        mechanism_family_key=terminal['numeric_abstracted_family_key'], full_row_sha256=terminal['whole_row_sha256'], synthetic=False)
    shared = dict(schema=SCHEMA, synthetic=False, source_revision=REVISION, catalogue_sha256=CATALOGUE_SHA,
        runtime_sha256=RUNTIME_SHA, runtime_admitted_snapshot=1178, candidate_order=list(ROLES), helpers=copy.deepcopy(HELPERS),
        ready_resources=12, expected_count_is_not_observed=True, new_collector_required='real_ir_intent_native_collector',
        parent_plan_sha256=digest(old_plan), reservation_sha256=digest(reservation),
        preregistered_grid=dict(levels=list(LEVELS), domains=['space-unit', 'base'], owner_order=['p1', 'p2', 'p1', 'p2'],
            natural_hp=dict(ground=8, space=10, base=30),
            healthy_zero_exception='At level0 only the opposite-owner SPACE helper and opposite base have damage1; all sources share this exact board.',
            ground_scope='Ground candidates supply native eligibility negatives for SOR_132; there are no ground intended-action outcomes.',
            lethal_scope='TWI_174 space6 damage4 may defeat the selected unit: physical removal known, departed damage counter unknown, never zero-filled.'),
        input_policy='BEFORE public physics and full source program only; full actual native menus retained as proof, never numeric features.',
        hidden_policy=old_plan.get('hidden_policy'), production_changed=False, card_conversion_run=False,
        fresh_source_scope='Only SOR_132 terminal native outcomes are newly released. Its metadata/IR and primitives were already inspected.',
        remaining_reserved_codes=list(PRESERVED), remaining_nearclone_group=['ASH_259', 'LOF_259'],
        source_form_shift='SOR_132 is an optional whenPlayed unit (printedHP2/power3) after event-only training; entering source itself is an extra eligible space unit, captured but never intended.',
        optional_policy='Exact offered intended action; otherwise actual Cancel for events, actual Pass/passAbility for optional whenPlayed. No replacement target or root undo.')
    panels = {}
    for name, programs, cap, seconds in (('development', dev, 200, 30), ('terminal', [held], 40, 15)):
        plan = copy.deepcopy(shared); plan['panel_role'] = name; plan['programs'] = programs; plan['worlds'] = worlds(programs)
        selected = {p['code'] for p in programs} | set(HELPERS.values()) | {'TOKEN_SHIELD'}
        source_rows = dict(old_plan['selected_whole_rows']); source_rows[TERMINAL] = row
        plan['selected_whole_cards'] = sorted(selected)
        plan['selected_whole_rows'] = {code: copy.deepcopy(source_rows[code]) for code in sorted(selected)}
        plan.update(collector_max_engine_applies=cap, collector_max_seconds=seconds,
            expected_apply_count=2 * len(plan['worlds']), expected_cases=len(plan['worlds']), expected_programs=len(programs),
            terminal_outcomes_after_all_checkpoints=name == 'terminal',
            fit_source_policy='Original saved PR45 TRAIN40 only; new development/terminal native labels are not training additions.')
        require(not set(PRESERVED) & selected and (TERMINAL in selected) == (name == 'terminal'), 'unreleased source selected in a role')
        panels[name] = plan
    panels['preregistration'] = dict(schema='jepa-real-ir-intent-reservation-amendment/1', old_reservation_sha256=digest(reservation),
        released_terminal_source=TERMINAL, remaining_reserved_codes=list(PRESERVED),
        grouped_untouched_sources=['ASH_259', 'LOF_259'], original_programs_developmental=list(EVENTS),
        native_outcome_order=['development', 'all-fitted-checkpoints-sealed', 'terminal'],
        expected_native_calls=128, native_call_ceiling=240, numerical_fits=0, model_calls=0, native_applies=0,
        semantic_validated=False)
    return panels
