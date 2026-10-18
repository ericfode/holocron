"""Exact unchanged candidate admission; pure stdlib, no model construction."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def row_digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def audit(catalogue_path, runtime_path, exposure_plan_path, exposure_receipt_path):
    import compositional_typed_model as candidate
    catalogue = json.loads(Path(catalogue_path).read_text())
    runtime = json.loads(Path(runtime_path).read_text())
    cards = catalogue['cards']
    admitted = {r['setCode'] for r in runtime['runtimeAdmittedCards']}
    assert len(admitted) == runtime['runtimeAdmittedCount']
    assert len(cards) == runtime['knownCards']
    codes = [r['setCode'] for r in cards]
    assert len(codes) == len(set(codes)) and admitted <= set(codes)
    rows = []
    for row in cards:
        fields = None
        error_type = error_message = None
        try:
            fields = candidate.encode_program(row)
        except (ValueError, KeyError, TypeError) as error:
            error_type, error_message = type(error).__name__, str(error)
        rows.append(dict(set_code=row['setCode'], full_row_sha256=row_digest(row),
                         runtime_admitted=row['setCode'] in admitted,
                         accepted=fields is not None, error_type=error_type,
                         error_message=error_message, fields_or_null=fields))
    def rejects(subset):
        return dict(sorted(Counter(r['error_type'] + ': ' + r['error_message']
                                   for r in subset if not r['accepted']).items()))
    runtime_rows = [r for r in rows if r['runtime_admitted']]
    counts = dict(catalogue_total=len(rows), runtime_admitted=len(runtime_rows),
                  parser_accepted=sum(r['accepted'] for r in rows),
                  runtime_parser_accepted=sum(r['accepted'] for r in runtime_rows),
                  rejections_all=rejects(rows), rejections_runtime=rejects(runtime_rows))
    # Preserve even an unexpected success before the bounded stage fails closed.
    boundary_passed = counts['parser_accepted'] == 0
    return dict(schema='jepa-compositional-actual-admission/1',
        inputs=dict(catalogue=pin(catalogue_path), runtime=pin(runtime_path),
                    candidate_source=pin(candidate.__file__)),
        exposure_plan_path=pin(exposure_plan_path),
        exposure_receipt_path=pin(exposure_receipt_path), rows=rows, counts=counts,
        supported_semantic_tuples=32, unexposed_supported_semantic_families=0,
        fresh_eligible_actual_cards=0 if boundary_passed else None,
        boundary_passed=boundary_passed,
        decision='blocked-exact-input-contract' if boundary_passed else 'unexpected-admission-requires-full-card-review',
        runtime_game_conformance=runtime['gameConformance'],
        compiler_converted=runtime['irConvertedCount'],
        compiler_breakdown=dict(sourceAst=runtime['sourceAstConvertedCount'],
                                dataOnly=runtime['dataOnlyConvertedCount']),
        runtime_breakdown=runtime['runtimeAdmittedBreakdown'],
        scope='Whole unchanged rows submitted; parser examines abilities only. Zero parser admission implies zero whole-card admission. No prediction transfer was evaluated.',
        candidate_state_boundary='Live public unit, cost2/3/4, HP10; separate unmet actual-state review even if an ability were accepted.',
        first_failure_categories_only=True, training_calls=0, native_calls=0,
        neural_calls=0, production_changed=False)
