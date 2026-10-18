"""Source-only IBH104 fresh-state diagnostic; no collection or model calls.

The source program was exposed in the preceding assay. These eight roots test
new public states and intent invariance, never new-program generalization.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3] / 'experiments/ability-correction-v1'
KESSEL = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
REVISION = 'c7ee39554901278cee70f61fd8b26fb1920696b3'
SCHEMA = 'jepa-ability-correction-plan/1'
SOURCE_CODE = 'IBH_104'
ROLES = ('source', 'own_helper', 'opponent_helper', 'anchor_a', 'anchor_b', 'auxiliary', 'own_base', 'opponent_base')
HELPERS = dict(base='ASH_019', leader='IBH_053', resource='LOF_256', own_false='ASH_056', own_true='SEC_094',
    cheap_ground='SEC_028', expensive_ground='LOF_112', cheap_space='TWI_253', expensive_space='TWI_111',
    cost4_ground='ASH_061', auxiliary='TWI_253')
PRIOR_COLLECTOR_SHA = 'f5a54313c9d33fa2f2e1755d63d60cf2a22bf53d71b752c9f174b2f551df948e'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def require(value, message):
    if not value:
        raise ValueError(message)


def scenario_cards(scenario):
    unit = lambda code, owner: dict(code=code, owner=owner, damage=0, exhausted=False)
    anchors = (
        (unit('SEC_028', 'p2'), unit('LOF_112', 'p1')),
        (unit('TWI_253', 'p2'), unit('TWI_111', 'p2')),
        (unit('SEC_028', 'p1'), unit('TWI_111', 'p1')),
        (unit('ASH_061', 'p2'), unit('LOF_112', 'p2')),
    )
    require(type(scenario) is int and 0 <= scenario < 4, 'four predeclared public worlds only')
    a, b = anchors[scenario]
    return dict(own_helper=unit('ASH_056', 'p1'), opponent_helper=unit('SEC_094', 'p2'),
        anchor_a=a, anchor_b=b, auxiliary=unit('TWI_253', 'p2'))


def worlds():
    result = []
    for scenario in range(4):
        for intent in ('anchor_a', 'anchor_b'):
            result.append(dict(id=len(result), source_code=SOURCE_CODE, scenario=scenario, state_family=scenario,
                intent_ref=intent, requires_target=True, observation_refs=list(ROLES),
                observation_mode='actual-action-endpoints', partition='state_diagnostic',
                template_id='exposed-enemy-cost-bounded-multi-target-defeat', cohort='exposed-program-fresh-state',
                max_applies=4, ready_resources=12, own_base_damage=0, opponent_base_damage=0,
                arena_cards=scenario_cards(scenario), selection_mode='exactly-one-upTo',
                auxiliary_cap_root=False, primary_pair_excluded=False))
    return result


def build_plan(catalog, admission, prior_plan=None):
    rows = {r['setCode']: r for r in catalog['cards']}
    admitted = {r['setCode']: r for r in admission['runtimeAdmittedCards']}
    selected = sorted({SOURCE_CODE, 'TOKEN_SHIELD', *HELPERS.values()})
    require(set(selected) <= set(rows), 'every complete source/helper/support row required')
    require(set(selected) - {'TOKEN_SHIELD'} <= set(admitted), 'whole normal source/helper runtime admission required')
    require(rows['TOKEN_SHIELD']['status'] == 'unsupported', 'constructor Shield support is not normal-card admission')
    source = rows[SOURCE_CODE]
    require(source['sourceHash'] == '618f250ddd8f0059656e893070f76457591b1635f648041c675447c3fed664dd', 'previously exposed source implementation changed')
    require(admitted[SOURCE_CODE]['implementation'] == 'sourceIr', 'complete existing source IR required')
    abilities = source['abilities']
    require(not abilities['leader'] and not abilities['unit'] and len(abilities['card']) == 1, 'one complete event program required')
    ability = abilities['card'][0]
    require(ability['trigger'] == 'event' and ability['effect'] == dict(kind='defeat', target='chosen'), 'source effect differs')
    require(ability['targetResolver']['mode'] == 'upTo' and ability['targetResolver']['owner'] == 'opponent', 'source target protocol differs')
    if prior_plan is not None:
        require(prior_plan['selected_whole_rows'][SOURCE_CODE] == source, 'source row differs from prior exposed program')
    for code in ('SEC_028', 'LOF_112', 'TWI_253', 'TWI_111', 'ASH_061', 'LOF_256'):
        row = rows[code]
        require(not any(row['abilities'].values()) and not row['keywordValues'] and not row['card']['keywords'], 'plain complete anchor/resource row required: ' + code)
        require(row['card']['unique'] is False, 'plain nonunique anchor/resource required')
    for code, cost, arena in (('SEC_028', 2, 'ground'), ('LOF_112', 3, 'ground'), ('TWI_253', 2, 'space'), ('TWI_111', 3, 'space'), ('ASH_061', 4, 'ground')):
        card = rows[code]['card']
        require(card['cost'] == cost and card['arena'] == arena and card['hp'] >= 4, 'intact cost/arena/HP anchor profile differs')
    ws = worlds()
    expected = []
    for scenario in range(4):
        w = ws[2 * scenario]
        allowed = {role: spec['owner'] == 'p2' and rows[spec['code']]['card']['cost'] <= 3
            for role, spec in w['arena_cards'].items()}
        expected.append(dict(id='world-' + str(scenario), scenario=scenario,
            left_root=2 * scenario, right_root=2 * scenario + 1, root_ids=[2 * scenario, 2 * scenario + 1],
            logical_anchors=['anchor_a', 'anchor_b'], intended_refs=['anchor_a', 'anchor_b'],
            anchor_membership_hypothesis=[allowed['anchor_a'], allowed['anchor_b']],
            identical_pre_action_world_except_declared_intent=True, native_outcomes_required=True,
            eligibility_invariant_to_intent=True, actual_endpoint_effects_intent_dependent=True))
    require([p['anchor_membership_hypothesis'] for p in expected] == [[True, False], [True, True], [False, False], [False, True]], 'frozen owner/arena/cost crossings differ')
    return dict(schema=SCHEMA, status='source-prepared-no-execution', source_revision=REVISION,
        codes=[SOURCE_CODE], source_program_exposure='previously exposed in PR41; discovery/state diagnostic only',
        source_program_transfer_claim=False, native_input_novelty='Must compare full consumed C1R1 inputs against all preceding source rows before claiming fresh-state evidence.',
        cards=[dict(code=SOURCE_CODE, raw_card=copy.deepcopy(source), raw_row_sha256=digest(source),
            canonical_card_id=str(source['card']['id']), aliases=copy.deepcopy(source['card']['setCodes']),
            template_id=ws[0]['template_id'], family_id=ws[0]['template_id'])],
        worlds=ws, helpers=copy.deepcopy(HELPERS), candidate_order=list(ROLES),
        selected_whole_cards=selected, selected_whole_rows={c: copy.deepcopy(rows[c]) for c in selected},
        selected_row_hashes={c: digest(rows[c]) for c in selected},
        selected_row_pins={c: dict(sha256=digest(rows[c]), bytes=len(encoded(rows[c]))) for c in selected},
        intent_pairs=expected, expected_cases=8, main_cases=8, max_applies_per_case=4,
        collector_max_engine_applies=32, collector_max_seconds=15, native_build_max_seconds=10,
        structural_apply_bound=dict(roots=8, maximum_per_root=4, total=32,
            expected_if_direct_upTo_target_prompt=20, estimate_is_not_observed_count=True),
        unknown_policy='No replacement target; actual Cancel if offered, otherwise prompt-only membership observations. All future labels unknown for prompt-only roots.',
        privacy='Empty draw piles/opposing hand/resources; own hand contains only declared source; all five public arena instances represented.',
        public_input_task='actual-intent-endpoints', primary_heads=['target_allowed'],
        secondary_heads=['target_removed'], removal_numeric_unknown=True,
        eligibility_input_contract='Candidate eligibility is a property of source program and public candidate/state, independent of the actor predeclared intended target. Endpoint consequences retain intent relation.',
        prior_collector_sha256=PRIOR_COLLECTOR_SHA, neural_forwards=0, optimizer_updates=0,
        numerical_fits=0, paid_jobs=0, semantic_validated=False, root_go_required=True)


def prepare_plan():
    """Coordinator metadata stage only; caller owns all actual output writes."""
    generated = KESSEL / 'compiler/generated'
    prior = HERE.parents[3] / 'experiments/semantic-discrimination-repair-v1/native-plan.json'
    plan = build_plan(json.loads((generated / 'cards.json').read_text()),
        json.loads((generated / 'runtime-admission.json').read_text()), json.loads(prior.read_text()))
    paths = [Path(__file__), HERE / 'test_ability_correction_native_plan.py', prior,
        HERE / 'semantic_discrimination_native_collector/src/main.rs',
        *(generated / n for n in ('cards.json', 'runtime-admission.json', 'manifest.json', 'inputs.json', 'diagnostics.json'))]
    plan['source_pins'] = [pin(path) for path in paths]
    require(pin(paths[3])['sha256'] == PRIOR_COLLECTOR_SHA, 'prior collector bytes changed')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'native-plan.json')
    args = parser.parse_args()
    require(not args.out.exists(), 'exclusive new metadata output required')
    plan = prepare_plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(plan, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(plan=pin(args.out), roots=8, native_applies=0, neural_forwards=0)))


if __name__ == '__main__':
    main()
