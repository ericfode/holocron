"""Independent byte/structure verifier for an exact-contract admission audit.

Standard library only. This program never imports the candidate parser, loads
weights/arrays, invokes an engine, or performs training/inference. A surrounding
sealed stage owns wall time, RSS and all output paths. Parser acceptance is not
whole-card coverage; any accepted row stops this zero-admission audit pending a
separate full-semantic contract review.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path

REPORT_SCHEMA = 'jepa-compositional-actual-admission/1'
VERIFY_SCHEMA = 'jepa-compositional-actual-admission-verification/1'
CANDIDATE_SOURCE_SHA256 = '15aff57f03efb0720e97d3921a0e060fb7ee901cb3c19f2abc59cebb3c3d8a42'
ROW_KEYS = {'set_code', 'full_row_sha256', 'runtime_admitted', 'accepted',
            'error_type', 'error_message', 'fields_or_null'}
REPORT_KEYS = {'schema', 'inputs', 'rows', 'counts', 'supported_semantic_tuples',
               'unexposed_supported_semantic_families', 'fresh_eligible_actual_cards', 'decision',
               'boundary_passed'}
COUNT_KEYS = {'catalogue_total', 'runtime_admitted', 'parser_accepted',
              'runtime_parser_accepted', 'rejections_all', 'rejections_runtime'}
REPORT_EXTRA_KEYS = {'exposure_plan_path', 'exposure_receipt_path', 'runtime_game_conformance', 'compiler_converted',
                    'compiler_breakdown', 'runtime_breakdown', 'scope', 'candidate_state_boundary',
                    'first_failure_categories_only', 'training_calls', 'native_calls',
                    'neural_calls', 'production_changed'}


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def read(path):
    return json.loads(Path(path).read_text())


def checked_pin(expected):
    require(isinstance(expected, dict) and set(expected) == {'path', 'sha256', 'bytes'} and
            type(expected['path']) is str and Path(expected['path']).is_absolute() and
            type(expected['bytes']) is int and expected['bytes'] >= 0 and
            type(expected['sha256']) is str and len(expected['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in expected['sha256']), 'explicit canonical byte pin required')
    require(pin(expected['path']) == expected, 'input byte pin mismatch: ' + expected['path'])
    return expected


def keys(value, allowed):
    # This independently reproduces the precise fail-first candidate contract.
    # Keep its error text so the report cannot aggregate a different predicate.
    require(isinstance(value, dict) and not set(value) - set(allowed), 'unreviewed typed field')


def independent_fields(row):
    """Reproduce the pinned parser's restricted grammar, without importing it.

    Direct indexing intentionally preserves Python KeyError spelling (including
    quotes) and ordering. This is parser admission only: the original parser
    does not consume all other executable full-row fields.
    """
    value = row
    if 'abilities' in value:
        abilities = value['abilities']
        require(set(abilities) == {'card', 'unit', 'leader'} and not abilities['unit'] and
                not abilities['leader'] and len(abilities['card']) == 1, 'one main event program required')
        value = abilities['card'][0]
    keys(value, ('trigger', 'title', 'contextTitle', 'promptTitle', 'costs', 'optional', 'targetResolver', 'effect'))
    require(value.get('trigger') == 'event' and value.get('costs', []) == [],
            'one event with no additional ability costs required')
    require('optional' not in value or type(value['optional']) is bool, 'strict optional boolean required')
    resolver = value['targetResolver']
    keys(resolver, ('owner', 'type', 'zone', 'arena', 'predicate'))
    owner, arena = resolver['owner'], resolver['arena']
    require(owner in ('any', 'opponent') and arena in ('ground', 'space') and
            resolver.get('type') == 'unit' and resolver.get('zone') == 'arena',
            'restricted owner/unit/arena selector required')
    predicate = resolver['predicate']
    keys(predicate, ('kind', 'op', 'left', 'right'))
    require(predicate.get('kind') == 'binary' and predicate.get('op') == '<=' and
            predicate.get('left') == {'kind': 'ref', 'path': ['card', 'cost']},
            'literal printed-cost <= predicate required')
    bound = predicate['right']
    keys(bound, ('kind', 'value'))
    require(bound.get('kind') == 'const' and type(bound.get('value')) is int and bound['value'] in (2, 3),
            'cap literal2/3 required')
    effect = value['effect']
    keys(effect, ('kind', 'target', 'amount'))
    operation, amount = effect['kind'], effect['amount']
    keys(amount, ('kind', 'value'))
    require(operation in ('damage', 'heal') and effect.get('target') == 'chosen' and
            amount.get('kind') == 'const' and type(amount.get('value')) is int and amount['value'] in (1, 3),
            'chosen damage/heal literal1/3 required')
    return [float(owner == 'any'), float(owner == 'opponent'), float(arena == 'ground'),
            float(arena == 'space'), float(bound['value']), float(operation == 'damage'),
            float(operation == 'heal'), float(amount['value'])]


def classify(row):
    try:
        return {'accepted': True, 'error_type': None, 'error_message': None,
                'fields_or_null': independent_fields(row)}
    except (ValueError, KeyError, TypeError) as error:
        return {'accepted': False, 'error_type': type(error).__name__,
                'error_message': str(error), 'fields_or_null': None}


def exposure_audit(proof, receipt_proof):
    """Check all32 tuples and saved actual outcome metadata, without scoring labels."""
    checked_pin(proof)
    plan = read(proof['path'])
    require(plan.get('schema') == 'jepa-compositional-typed-plan/1' and plan.get('synthetic') is True,
            'exact synthetic exposure metadata required')
    programs = plan['programs']
    require(isinstance(programs, list) and len(programs) == 32, 'all32 exposed semantic tuples required')
    tuples, bits_seen, program_hashes = set(), set(), set()
    for i, program in enumerate(programs):
        bits = program['bits']
        require(isinstance(bits, list) and len(bits) == 5 and
                all(type(b) is int and b in (0, 1) for b in bits), 'five binary exposure axes required')
        expected = [float(not bits[0]), float(bits[0]), float(not bits[1]), float(bits[1]),
                    float(3 if bits[2] else 2), float(not bits[4]), float(bits[4]), float(3 if bits[3] else 1)]
        fields = independent_fields(program['raw_card'])
        require(fields == expected and program['index'] == i and program['synthetic'] is True and
                program['partition'] == ('held' if sum(bits) % 2 else 'train') and
                program['program_hash'] == digest(program['raw_card']['abilities']),
                'exposure declaration differs from its actual complete typed program')
        tuples.add(tuple(fields)); bits_seen.add(tuple(bits)); program_hashes.add(program['program_hash'])
    require(bits_seen == set(itertools.product((0, 1), repeat=5)) and len(tuples) == len(program_hashes) == 32,
            'missing/duplicated semantic tuple inventory')
    checked_pin(receipt_proof)
    receipt = read(receipt_proof['path'])
    require(receipt.get('schema') == 'jepa-compositional-typed-native/1' and receipt.get('collectionComplete') is True and
            receipt.get('collectionPlanSha256') == proof['sha256'] and receipt.get('collectionPlan') == plan and
            receipt.get('programs') == programs, 'actual saved exposure receipt is not tied to the complete pinned plan')
    worlds, cases = plan['worlds'], receipt['cases']
    require(isinstance(worlds, list) and isinstance(cases, list) and len(worlds) == len(cases) == 128 and
            [c['world_id'] for c in cases] == list(range(128)), 'all128 ordered actual exposure cases required')
    committed_counts = [0] * 32
    cancelled = prompt_only = 0
    for i, (world, case) in enumerate(zip(worlds, cases)):
        program_index, variant = i // 4, i % 4
        require(world['id'] == i and world['program_index'] == case['program_index'] == program_index and
                world['root_variant'] == case['root_variant'] == variant and
                world['source_code'] == case['card'] == programs[program_index]['code'] and
                'engineError' in case and case['engineError'] is None,
                'actual exposed program/world/variant identity differs or errored')
        if variant in (0, 1, 2):
            require(case['intentOffered'] is True and case['intendedTargetCommitted'] is True and
                    case['intentResolution'] == 'committed' and case['completion'] == 'settled' and
                    case['terminalClassification'] == 'settled-committed' and isinstance(case['final'], dict) and
                    case['final'].get('settled') is True, 'three actual offered committed outcomes per program required')
            committed_counts[program_index] += 1
        else:
            require(case['intentOffered'] is False and case['intendedTargetCommitted'] is False,
                    'invalid-intent variant cannot count as a committed exposure')
            if case['intentResolution'] == 'unoffered-declined':
                require(case['completion'] == 'settled' and case['terminalClassification'] == 'settled-cancelled' and
                        isinstance(case['final'], dict) and case['final'].get('settled') is True,
                        'actual cancelled exposure terminal differs')
                cancelled += 1
            else:
                require(case['intentResolution'] == case['completion'] == 'unoffered-observation-only' and
                        case['terminalClassification'] == 'unoffered-prompt-only' and case['final'] is None,
                        'invalid intent must preserve the actual cancelled or prompt-only terminal')
                prompt_only += 1
    require(all(count >= 3 for count in committed_counts), 'a supported tuple lacks three saved committed exposures')
    return {'plan': proof, 'receipt': receipt_proof, 'supported_tuple_count': 32, 'inventory_verified': True,
            'all_supported_tuples_already_in_inventory': True,
            'unexposed_supported_semantic_families': 0,
            'identity_is_not_semantic_family': True,
            'actual_saved_case_count': 128, 'committed_cases_per_program': committed_counts,
            'actual_saved_committed_outcomes': sum(committed_counts),
            'actual_saved_cancelled_cases': cancelled, 'actual_saved_prompt_only_cases': prompt_only,
            'evidence_scope': 'All32 actual typed programs and full factorial independently checked against a pinned complete saved receipt, including at least three settled committed outcomes per program. Numeric labels are not scored here; original native journal conformance remains established by the linked closed verification.',
            'native_outcome_receipt_reopened_by_this_verifier': True}


def verify(catalogue_path, runtime_path, report_path):
    """Check every supplied full catalogue row and the exact declared counts."""
    catalogue_pin, runtime_pin, report_pin = pin(catalogue_path), pin(runtime_path), pin(report_path)
    catalogue, runtime, report = read(catalogue_path), read(runtime_path), read(report_path)
    require(isinstance(report, dict) and REPORT_KEYS <= set(report) <= REPORT_KEYS | REPORT_EXTRA_KEYS and
            report['schema'] == REPORT_SCHEMA, 'exact admission report schema required')
    inputs = report['inputs']
    require(isinstance(inputs, dict) and set(inputs) == {'catalogue', 'runtime', 'candidate_source'},
            'catalogue/runtime/candidate source pins required')
    for proof in inputs.values(): checked_pin(proof)
    require(inputs['catalogue'] == catalogue_pin and inputs['runtime'] == runtime_pin,
            'command input differs from report input')
    require(inputs['candidate_source']['sha256'] == CANDIDATE_SOURCE_SHA256,
            'the independently implemented pinned candidate source changed')
    require(isinstance(catalogue, dict) and isinstance(catalogue.get('cards'), list), 'full catalogue cards list required')
    require(isinstance(runtime, dict) and isinstance(runtime.get('runtimeAdmittedCards'), list), 'runtime admission list required')
    cards = catalogue['cards']; runtime_records = runtime['runtimeAdmittedCards']
    require(cards and all(isinstance(row, dict) and type(row.get('setCode')) is str and row['setCode'] for row in cards),
            'every full catalogue row must have a real source code')
    require(all(isinstance(row, dict) and type(row.get('setCode')) is str and row['setCode'] for row in runtime_records),
            'runtime setCode provenance required')
    codes = [row['setCode'] for row in cards]; runtime_codes = [row['setCode'] for row in runtime_records]
    require(len(codes) == len(set(codes)) and len(runtime_codes) == len(set(runtime_codes)),
            'duplicate source/runtime aliases cannot inflate a denominator')
    runtime_set = set(runtime_codes)
    require(runtime_set <= set(codes), 'runtime-admitted definition missing from the full catalogue')
    require(type(runtime.get('runtimeAdmittedCount')) is int and runtime['runtimeAdmittedCount'] == len(runtime_set) and
            type(runtime.get('knownCards')) is int and runtime['knownCards'] == len(cards),
            'runtime manifest denominator differs from the actual pinned row sets')
    require(isinstance(report['rows'], list) and len(report['rows']) == len(cards),
            'one proof per full catalogue row required; no sampling')
    counts = {'catalogue_total': len(cards), 'runtime_admitted': len(runtime_set), 'parser_accepted': 0,
              'runtime_parser_accepted': 0, 'rejections_all': {}, 'rejections_runtime': {}}
    hashes = []; accepted_codes = []
    for index, (card, claimed) in enumerate(zip(cards, report['rows'])):
        require(isinstance(claimed, dict) and set(claimed) == ROW_KEYS and claimed['set_code'] == card['setCode'],
                'report row ordering/keys differ at catalogue index ' + str(index))
        full_hash = digest(card); hashes.append(full_hash)
        require(claimed['full_row_sha256'] == full_hash and type(claimed['runtime_admitted']) is bool and
                claimed['runtime_admitted'] == (card['setCode'] in runtime_set),
                'full source row or independent runtime membership differs: ' + card['setCode'])
        expected = classify(card)
        require(type(claimed['accepted']) is bool and all(claimed[key] == value for key, value in expected.items()),
                'independent fail-first rejection proof differs: ' + card['setCode'])
        if expected['accepted']:
            require(isinstance(claimed['fields_or_null'], list) and len(claimed['fields_or_null']) == 8 and
                    all(type(v) is float for v in claimed['fields_or_null']), 'eight literal float fields required')
            counts['parser_accepted'] += 1; counts['runtime_parser_accepted'] += int(card['setCode'] in runtime_set)
            accepted_codes.append(card['setCode'])
        else:
            key = expected['error_type'] + ': ' + expected['error_message']
            counts['rejections_all'][key] = counts['rejections_all'].get(key, 0) + 1
            if card['setCode'] in runtime_set:
                counts['rejections_runtime'][key] = counts['rejections_runtime'].get(key, 0) + 1
    require(isinstance(report['counts'], dict) and set(report['counts']) == COUNT_KEYS and report['counts'] == counts,
            'denominator/acceptance/rejection counts do not replay from every catalogue row')
    require(all(type(report['counts'][key]) is int for key in ('catalogue_total', 'runtime_admitted',
            'parser_accepted', 'runtime_parser_accepted')), 'counts must be integers, never booleans')
    for key in ('rejections_all', 'rejections_runtime'):
        require(all(type(value) is int and value > 0 for value in report['counts'][key].values()),
                'positive integer first-rejection counts required')
    require(sum(counts['rejections_all'].values()) + counts['parser_accepted'] == len(cards) and
            sum(counts['rejections_runtime'].values()) + counts['runtime_parser_accepted'] == len(runtime_set),
            'every row must contribute to exactly one first-failure/acceptance bucket')
    require(type(report['supported_semantic_tuples']) is int and report['supported_semantic_tuples'] == 32 and
            type(report['unexposed_supported_semantic_families']) is int and report['unexposed_supported_semantic_families'] == 0 and
            type(report['fresh_eligible_actual_cards']) is int and report['fresh_eligible_actual_cards'] == 0 and
            report['decision'] == 'blocked-exact-input-contract', 'fresh-family or decision claim exceeds the audited contract')
    require(report['boundary_passed'] is True, 'unexpected acceptance must persist as a failed audit boundary, never verified success')
    expected_metadata = {
        'runtime_game_conformance': runtime['gameConformance'],
        'compiler_converted': runtime['irConvertedCount'],
        'compiler_breakdown': {'sourceAst': runtime['sourceAstConvertedCount'], 'dataOnly': runtime['dataOnlyConvertedCount']},
        'runtime_breakdown': runtime['runtimeAdmittedBreakdown'],
        'scope': 'Whole unchanged rows submitted; parser examines abilities only. Zero parser admission implies zero whole-card admission. No prediction transfer was evaluated.',
        'candidate_state_boundary': 'Live public unit, cost2/3/4, HP10; separate unmet actual-state review even if an ability were accepted.',
        'first_failure_categories_only': True, 'training_calls': 0, 'native_calls': 0,
        'neural_calls': 0, 'production_changed': False}
    for key, value in expected_metadata.items():
        if key in report:
            require(report[key] == value, 'unsupported copied runtime/scope claim: ' + key)
    for key in ('training_calls', 'native_calls', 'neural_calls'):
        if key in report: require(type(report[key]) is int, 'explicit zero call count required')
    for key in ('first_failure_categories_only', 'production_changed'):
        if key in report: require(type(report[key]) is bool, 'explicit Boolean scope flag required')
    require('exposure_plan_path' in report and 'exposure_receipt_path' in report,
            'the full pinned32-program plan and actual outcome receipt are required for the family-zero claim')
    exposure = exposure_audit(report['exposure_plan_path'], report['exposure_receipt_path'])
    require(not accepted_codes, 'accepted parser rows require a separate whole-semantic/task admission review; stop: ' + ', '.join(accepted_codes))
    return {'schema': VERIFY_SCHEMA, 'status': 'passed', 'verified': True, 'decision': 'blocked-exact-input-contract',
            'counts': counts, 'verified_full_rows': len(cards), 'ordered_full_row_hashes_sha256': digest(hashes),
            'inputs': inputs, 'report': report_pin, 'exposure': exposure,
            'coverage_scope': 'Exact restricted parser admission over full pinned source rows; no whole-card coverage or learned/native transfer claim.',
            'whole_card_coverage_claim': False, 'native_conformance_verified': False, 'learned_transfer_verified': False,
            'native_applies': 0, 'neural_forwards': 0, 'backwards': 0, 'optimizer_updates': 0, 'numerical_fits': 0,
            'paid_jobs': 0, 'paid_spend_usd': 0.}


def write_new(path, result):
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('catalogue', 'runtime', 'report', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.catalogue, args.runtime, args.report)
    except Exception as error:
        write_new(args.out, {'schema': VERIFY_SCHEMA, 'status': 'failed',
            'error': {'type': type(error).__name__, 'message': str(error)},
            'native_applies': 0, 'neural_forwards': 0, 'backwards': 0, 'optimizer_updates': 0,
            'numerical_fits': 0, 'paid_jobs': 0, 'paid_spend_usd': 0.})
        raise
    write_new(args.out, result)
    print(json.dumps({'status': result['status'], 'output': pin(args.out)}, allow_nan=False))


if __name__ == '__main__': main()
