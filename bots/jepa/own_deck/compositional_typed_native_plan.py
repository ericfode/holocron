"""Pure metadata for a synthetic elementary-IR comparison; never runs an engine.

Synthetic rows are laboratory inputs to existing native grammar. They are not
compiler-verified real cards, actual-corpus coverage, or fresh card identities.
"""
import copy
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KESSEL = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
REVISION = 'c7ee39554901278cee70f61fd8b26fb1920696b3'
SCHEMA = 'jepa-compositional-typed-plan/1'
BIT_NAMES = ('owner', 'arena', 'cap', 'amount', 'op')
BIT_VALUES = (('any', 'opponent'), ('ground', 'space'), (2, 3), (1, 3), ('damage', 'heal'))
SUPPORT_CODES = ('ASH_019', 'IBH_053', 'LOF_256', 'TOKEN_SHIELD')
ROLES = tuple(f'{owner}_{arena}_{cost}' for owner in ('p1', 'p2') for arena in ('ground', 'space') for cost in ('c2a', 'c2b', 'c3', 'c4'))
ALL_ROLES = ('source', *ROLES, 'own_base', 'opponent_base')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    p = Path(path).resolve(); raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def require(value, message):
    if not value:
        raise ValueError(message)


def elementary_ability(factors):
    return dict(trigger='event', title='Elementary effect', costs=[],
        targetResolver=dict(owner=factors['owner'], type='unit', zone='arena', arena=factors['arena'],
            predicate=dict(kind='binary', op='<=', left=dict(kind='ref', path=['card', 'cost']),
                right=dict(kind='const', value=factors['cap']))),
        effect=dict(kind=factors['op'], target='chosen', amount=dict(kind='const', value=factors['amount'])))


def synthetic_row(template, code, index, *, arena=None, cost=1):
    row = copy.deepcopy(template)
    unit = arena is not None
    row.update(setCode=code, id=f'synthetic-{index}', internalName='synthetic-anchor' if unit else 'synthetic-event',
        baseClass='NonLeaderUnitCard' if unit else 'EventCard', className='SyntheticElementaryAnchor' if unit else 'SyntheticElementaryEvent',
        status='supported', sourcePath=None, sourceHash=None, dataHash=None,
        keywordValues={}, abilities=dict(card=[], unit=[], leader=[]), attachCondition=None,
        requiredCapabilities=['cardType:unit'] if unit else [])
    card = row['card']
    card.update(id=f'synthetic-{index}', internalName=row['internalName'], title='Elementary anchor' if unit else 'Elementary event',
        subtitle='', text='', cost=cost, hp=10 if unit else None, power=0 if unit else None,
        types=['unit'] if unit else ['event'], aspects=[], traits=[], keywords=[], unique=False,
        setId=dict(set='SYNTH', number=index + 1), setCodes=[dict(set='SYNTH', number=index + 1)],
        deployBox=None, epicAction='', rules=None, upgradePower=None, upgradeHp=None, pilotText=None)
    if unit:
        card['arena'] = arena
    else:
        card.pop('arena', None)
    return row


def board():
    result = {}
    for role in ROLES:
        owner, arena, cost_name = role.split('_')
        cost = int(cost_name[1])
        result[role] = dict(code=f'SYNTH_ANCHOR_{arena.upper()}_{cost}', owner=owner, arena=arena,
            cost=cost, printed_cost=cost, hp=10, power=0, damage=3 if cost_name in ('c2a', 'c4') else 1, exhausted=False)
    return result


def program_worlds(program):
    f = program['factors']; arena = f['arena']; opposite = 'space' if arena == 'ground' else 'ground'
    intents = (f"{'p1' if f['owner'] == 'any' else 'p2'}_{arena}_c2a",
        f"p2_{arena}_{'c3' if f['cap'] == 3 else 'c2b'}", f'p2_{arena}_c2a', f'p2_{opposite}_c2a')
    result = []
    for variant, intent in enumerate(intents):
        cards = board()
        if variant == 2:
            cards[intent]['damage'] = 0
        result.append(dict(id=program['index'] * 4 + variant, source_code=program['code'], program_index=program['index'],
            root_variant=variant, state_family=variant, partition=program['partition'], intent_ref=intent,
            observation_refs=list(ROLES), max_applies=4, ready_resources=4, own_base_damage=0, opponent_base_damage=0,
            arena_cards=cards, variant_name=('eligible-three-damage', 'eligible-clipped-heal', 'healthy-eligible', 'invalid-opposite-arena')[variant],
            eligibility_hypothesis=variant != 3, hypothesis_is_not_native_label=True))
    return result


def build_plan(catalog):
    require(catalog['schema'] == 'swu-card-ir/v1' or (catalog['schema'] == 'swu-card-ir-cards/v1' and catalog.get('irSchema') == 'swu-card-ir/v1'), 'unchanged native catalogue or generated cards-shard schema required')
    rows = {r['setCode']: r for r in catalog['cards']}
    require(set(SUPPORT_CODES) | {'JTL_180', 'LOF_256'} <= set(rows), 'complete metadata/support templates required')
    require(rows['TOKEN_SHIELD']['status'] == 'unsupported', 'reviewed constructor token retains unsupported status')
    programs = []
    for index, bits in enumerate(itertools.product((0, 1), repeat=5)):
        factors = {name: values[bit] for name, values, bit in zip(BIT_NAMES, BIT_VALUES, bits)}
        code = f'SYNTH_PROGRAM_{index:02d}'
        row = synthetic_row(rows['JTL_180'], code, index)
        row['abilities']['card'] = [elementary_ability(factors)]
        row['requiredCapabilities'] = ['cardType:event', 'trigger:event', 'targetType:unit', 'targetZone:arena',
            'ir:binary', 'binary:<=', 'ir:ref', 'ir:const', 'ir:' + factors['op']]
        programs.append(dict(index=index, code=code, bits=list(bits), factors=factors,
            fields8=[float(factors['owner'] == 'any'), float(factors['owner'] == 'opponent'),
                float(factors['arena'] == 'ground'), float(factors['arena'] == 'space'), factors['cap'],
                float(factors['op'] == 'damage'), float(factors['op'] == 'heal'), factors['amount']],
            partition='train' if sum(bits) % 2 == 0 else 'held', raw_card=row,
            program_hash=digest(row['abilities']), synthetic=True))
    anchors = []
    for index, (arena, cost) in enumerate(itertools.product(('ground', 'space'), (2, 3, 4)), start=32):
        anchors.append(synthetic_row(rows['LOF_256'], f'SYNTH_ANCHOR_{arena.upper()}_{cost}', index, arena=arena, cost=cost))
    selected = {code: copy.deepcopy(rows[code]) for code in SUPPORT_CODES}
    selected.update({p['code']: copy.deepcopy(p['raw_card']) for p in programs})
    selected.update({r['setCode']: r for r in anchors})
    provenance = {code: dict(laboratory_definition=True, real_card_claim=False, compiler_conversion_run=False,
        metadata_template='LOF_256' if code.startswith('SYNTH_ANCHOR_') else 'JTL_180',
        native_admission_before_execution_required=True,
        status_meaning='supported is a native input gate, not a generated compiler certification')
        for code in selected if code.startswith('SYNTH_')}
    worlds = [world for program in programs for world in program_worlds(program)]
    require(len(worlds) == 128 and [w['id'] for w in worlds] == list(range(128)), 'exact complete program-root bank required')
    for program in programs:
        for world in program_worlds(program):
            eligible = [r for r, card in world['arena_cards'].items() if card['arena'] == program['factors']['arena']
                and card['printed_cost'] <= program['factors']['cap'] and (program['factors']['owner'] == 'any' or card['owner'] == 'p2')]
            require(len(eligible) >= 2, 'two eligible slots even at opponent cap2 required')
            require(any(world['arena_cards'][r]['damage'] > 0 for r in eligible), 'healthy heal intent must retain another damaged eligible unit')
            require((world['intent_ref'] in eligible) == world['eligibility_hypothesis'], 'predeclared design crossing differs')
    return dict(schema=SCHEMA, status='prepared-no-execution', source_revision=REVISION,
        synthetic=True, actual_card_coverage_claim=False, compiler_conversion_run=False, engine_source_edits=False,
        programs=programs, program_bit_order=list(BIT_NAMES), program_bit_values=[list(v) for v in BIT_VALUES],
        worlds=worlds, candidate_order=list(ROLES), capture_roles=list(ALL_ROLES), expected_programs=32, expected_cases=128,
        helpers=dict(base='ASH_019', leader='IBH_053', resource='LOF_256'),
        synthetic_definition_provenance=provenance,
        selected_whole_cards=sorted(selected), selected_whole_rows=selected,
        selected_row_hashes={code: digest(row) for code, row in selected.items()},
        split=dict(rule='parity of five bit indices; even TRAIN, odd HELD; all four roots of a full program remain together',
            train_program_indices=[p['index'] for p in programs if p['partition'] == 'train'],
            held_program_indices=[p['index'] for p in programs if p['partition'] == 'held'],
            train_roots=[w['id'] for w in worlds if w['partition'] == 'train'], held_roots=[w['id'] for w in worlds if w['partition'] == 'held'],
            claim='Synthetic held combinations, not unseen mechanic/family/card transfer; every proper subset combination occurs in both partitions.'),
        collector_max_engine_applies=512, max_applies_per_case=4, collector_max_seconds=30,
        expected_apply_count=256, expected_count_is_not_observed=True,
        action_policy='Play own event then exact declared unit if offered; otherwise actual Cancel if available or prompt-only observation. No replacement, no Done, no optional effect choice.',
        metadata_policy='All source printed semantic metadata is identical; source codes, IDs, titles/text and catalogue indices are absent from semantic inputs. Anchors have synthetic HP10/power0 with fixed printed cost/arena.',
        privacy='Empty draw piles and opposing hand/resources; own hand contains only its declared synthetic source. All sixteen public arena units are represented.',
        healthy_healing_policy='At least one OTHER eligible damaged cost2 twin remains, so a healthy intended target can be observed at an actual opened target menu.',
        numerical_policy='Committed settled actual endpoints only. Healthy heal yields observed zero; invalid/cancelled future outcomes remain unknown; no expected label substitutes for native output.',
        root_go_required=True, native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, semantic_validated=False)


def prepare_plan():
    """Metadata stage only: read pinned bytes and return a value, with no writes."""
    generated = KESSEL / 'compiler/generated'
    plan = build_plan(json.loads((generated / 'cards.json').read_text()))
    crate = HERE / 'compositional_typed_native_collector'
    plan['source_pins'] = [pin(p) for p in (Path(__file__), HERE / 'test_compositional_typed_native_plan.py',
        HERE / 'COMPOSITIONAL_TYPED_PROTOCOL.md', *(crate / n for n in ('Cargo.toml', 'Cargo.lock', 'src/main.rs', 'README.md', 'fixtures/source-templates.json')),
        *(generated / n for n in ('cards.json', 'runtime-admission.json', 'manifest.json', 'inputs.json', 'diagnostics.json')))]
    return plan
