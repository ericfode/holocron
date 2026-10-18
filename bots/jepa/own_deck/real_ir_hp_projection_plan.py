"""Pure metadata projection of the exposed PR45 seven-event public state grid.

No file I/O, imports of scientific libraries, engine calls or outcome generation.
The old plan and complete card rows are preserved; only public damage changes.
The original collector rejects this grid, so a new versioned collector is required.
"""
import copy
import hashlib
import json

ROLES = ('p1_ground', 'p2_ground', 'p1_space', 'p2_space', 'own_base', 'opponent_base')
CODES = ('IBH_013', 'IBH_066', 'IBH_061', 'TWI_174', 'IBH_059', 'JTL_075', 'TWI_170')
PRESERVED_NOT_SELECTED = ('ASH_259', 'LOF_259', 'SOR_132', 'HMW_158')
HELPERS = dict(base='ASH_019', leader='IBH_053', resource='LOF_256', ground='HMW_093', space='LOF_119')
CATALOGUE_SHA = '0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812'
RUNTIME_SHA = '91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957'
REVISION = 'c7ee39554901278cee70f61fd8b26fb1920696b3'
NEW_COLLECTOR = 'real_ir_hp_projection_native_collector'
NEW_BINARY = 'real-ir-hp-projection-native-collector'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_old(plan):
    require(plan.get('schema') == 'jepa-real-ir-transfer-plan/1' and plan.get('synthetic') is False,
            'unchanged real-event plan schema required')
    require(plan.get('source_revision') == REVISION and plan.get('catalogue_sha256') == CATALOGUE_SHA and
            plan.get('runtime_sha256') == RUNTIME_SHA and plan.get('runtime_admitted_snapshot') == 1178,
            'unchanged pinned1178 engine/catalogue/admission required')
    require(tuple(plan.get('candidate_order', [])) == ROLES and plan.get('helpers') == HELPERS and
            plan.get('collector_max_engine_applies') == 168 and plan.get('expected_apply_count') == 112 and
            plan.get('collector_max_seconds') == 30 and plan.get('expected_count_is_not_observed') is True,
            'fixed roles/helpers/call ceilings required')
    programs, worlds = plan.get('programs', []), plan.get('worlds', [])
    require(len(programs) == 7 and tuple(p.get('code') for p in programs) == CODES and len(worlds) == 56,
            'unchanged ordered seven programs and56 worlds required')
    rows = plan['selected_whole_rows']
    require(set(rows) == set(plan['selected_whole_cards']) and not set(PRESERVED_NOT_SELECTED) & set(rows),
            'complete original selected closure; reserved whenPlayed sources must remain unselected')
    for key, hp, arena in (('ground', 8, 'ground'), ('space', 10, 'space'), ('base', 30, None)):
        card = rows[HELPERS[key]]['card']
        require(card['hp'] == hp and card['unique'] is False and card['keywords'] == [] and
                (arena is None or card['arena'] == arena), 'original natural HP/kind helper profile differs')
    for i, program in enumerate(programs):
        require(program.get('index') == i and program.get('raw_card') == rows[program['code']] and
                program.get('partition') == ('train' if i < 5 else 'held'), 'original whole-program identity/order/split differs')
    for i, world in enumerate(worlds):
        variant = i % 8; program = programs[i // 8]
        require(world.get('id') == i and world.get('program_index') == i // 8 and world.get('root_variant') == variant and
                world.get('source_code') == program['code'] and world.get('partition') == program['partition'] and
                world.get('max_applies') == 3 and world.get('requires_target') is True and world.get('ready_resources') == 12,
                'original world/source/structural bound differs')
        intent = ROLES[variant if variant < 6 else 0 if variant == 6 else 4]
        require(world.get('intent_ref') == intent and set(world['arena_cards']) == set(ROLES[:4]),
                'original eight-intent/four-unit design differs')
        for role in ROLES[:4]:
            owner, arena = role.split('_'); spec = world['arena_cards'][role]
            expected = 0 if variant == 6 and role == 'p1_ground' else 3 if arena == 'ground' else 5
            require(spec['code'] == HELPERS[arena] and spec['owner'] == owner and spec['arena'] == arena and
                    spec['damage'] == expected and spec['exhausted'] is False,
                    'original public3/5 damage fixture differs')
        require(world['own_base_damage'] == (0 if variant == 7 else 5) and world['opponent_base_damage'] == 5,
                'original public5-damage base fixture differs')


def build(old_plan):
    """Return metadata only. All seven source programs are DEVELOPMENTAL."""
    validate_old(old_plan)
    plan = copy.deepcopy(old_plan)
    for world in plan['worlds']:
        variant = world['root_variant']
        for role, spec in world['arena_cards'].items():
            spec['damage'] = 0 if variant == 6 and role == 'p1_ground' else 1 if spec['arena'] == 'ground' else 2
        world['own_base_damage'] = 0 if variant == 7 else 4
        world['opponent_base_damage'] = 4
    plan['fit_source_policy'] = ('All seven programs are previously exposed DEVELOPMENTAL sources. Historical train/held tags are '
        'retained for compatible analysis only. Any new claim concerns this preregistered public-state composition, not fresh programs.')
    plan['state_projection'] = dict(schema='jepa-real-ir-public-state-projection/1', parent_plan_sha256=digest(old_plan),
        old_initial_damage=dict(ground=3, space=5, base=5), new_initial_damage=dict(ground=1, space=2, base=4),
        unchanged_natural_hp=dict(ground=8, space=10, base=30),
        healthy_exceptions=[dict(variant=6, role='p1_ground', damage=0), dict(variant=7, role='own_base', damage=0)],
        unchanged=dict(programs=True, whole_rows=True, aliases=True, source_pins=True, program_order=True,
            candidate_order=True, helpers=True, resources=True, intents=True, quotas=True, engine=True),
        original_fit_source_policy=old_plan.get('fit_source_policy'),
        numerical_fits=0, native_applies=0, model_calls=0, outcomes_observed=False)
    plan['freshness_scope'] = dict(schema='jepa-real-ir-state-freshness/1',
        source_program_status={code: 'DEVELOPMENTAL-previously-exposed' for code in CODES},
        fresh_source_programs=False, fresh_primitives=False, fresh_mechanism_families=False,
        new_state_composition_only=True, fresh_whenPlayed_sources_preserved_not_selected=list(PRESERVED_NOT_SELECTED),
        historical_partition_labels='Retained without reclassifying the previously observed programs as fresh holdouts.',
        independent_native_state_outcomes='Unobserved until a separately authorized bounded native collection.')
    plan['native_collector_requirement'] = dict(new_collector_required=True, directory=NEW_COLLECTOR, binary=NEW_BINARY,
        unchanged_old_collector_compatible=False,
        reason='The frozen PR45 collector explicitly validates3/5/5 damage. Its versioned copy validates1/2/4; all other behavior is unchanged.',
        schema_unchanged=True, runtime_admitted_snapshot=1178, engine_source_changed=False)
    for key in ('programs', 'selected_whole_rows', 'selected_whole_cards', 'candidate_order', 'helpers'):
        require(plan[key] == old_plan[key], 'projection changed protected semantic/source content: ' + key)
    return plan
