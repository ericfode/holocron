"""Once-only, zero-engine/zero-neural actual-card admission allocation."""
import argparse
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
ROOT = D.EXPERIMENTS / 'compositional-actual-admission-v1'
PRIOR = D.EXPERIMENTS / 'compositional-typed-saved-v1'
CATALOGUE = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/generated/cards.json')
RUNTIME = CATALOGUE.with_name('runtime-admission.json')
PLAN = PRIOR / 'metadata-1/native-plan.json'
NATIVE_RECEIPT = PRIOR / 'native-1/receipt.json'
ZERO = dict(native_applies=0, neural_forwards=0, backwards=0,
            optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
FILES = ['compositional_actual_admission.py', 'compositional_actual_admission_verify.py',
         'compositional_actual_admission_campaign.py', 'COMPOSITIONAL_ACTUAL_ADMISSION_PROTOCOL.md']


def read(path):
    return json.loads(Path(path).read_text())


def prepare():
    S.require(not ROOT.exists(), 'new campaign only; never reset history')
    prior = S.Budget(PRIOR / 'campaign-spec.json')
    state = prior.inspect()
    closure = read(PRIOR / 'experiment-closure.json')
    S.require(state['completed'] == prior.spec['stage_order'] and not state['failures']
              and state['pending'] is None and state['cumulative'] == closure['cumulative'],
              'closed exact prior required')
    S.require(state['cumulative'] == dict(charged_native_applies=807,
        charged_seconds=266.6158477078425, observed_native_applies=None), 'no charge reset')
    publication = D.EXPERIMENTS / 'compositional-typed-publication-complete.json'
    published = read(publication)
    S.require(published['state'] == 'MERGED' and published['merge_commit'] ==
              'ae6b95d4a0d0282e4ce02ce8ca918b4ef14d96c5', 'publish before transfer')
    ROOT.mkdir()
    parent = copy.deepcopy(prior.parent)
    parent['carry'] = state['cumulative']
    pins = {p['path']: p for p in parent['pins']}
    for p in list(prior.frozen.values()) + [S.pin(p) for p in PRIOR.rglob('*') if p.is_file()]:
        S.verify_pin(p)
        S.require(p['path'] not in pins or pins[p['path']] == p, 'immutable pin conflict')
        pins[p['path']] = p
    parent['pins'] = [pins[k] for k in sorted(pins)]
    parent['protected_roots'].append(str(PRIOR))
    parent['closed_journals'].append(D.closed_journal(prior.ledger))
    pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    py = str(Path(sys.executable).resolve())
    stages = {}
    for name in ('audit', 'verify'):
        stages[name] = dict(argv=[py, str(Path(__file__).resolve()), 'run', '--stage', name,
            '--spec', str(ROOT / 'campaign-spec.json')],
            outputs=[str(ROOT / (name+'-1')), str(ROOT / (name+'-1-stage-receipt.json'))],
            reservation=dict(seconds=10., **ZERO), expected=dict(ZERO), external_counters=[])
    inputs = [HERE / n for n in FILES] + [HERE / 'compositional_typed_model.py',
        HERE / 'effect_identifiability_fit.py', CATALOGUE, RUNTIME, PLAN, NATIVE_RECEIPT, publication, Path(py)]
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=S.pin(S.__file__),
        primitives=S.pin(S._PATH), parent_manifest=pm, ledger_path=str(ROOT / 'campaign-ledger.jsonl'),
        caps=dict(seconds=20., **ZERO), guard=dict(cpu_workers=1, rss_bytes=1024**3),
        stage_order=list(stages), stages=stages, pins=[S.pin(p) for p in inputs],
        environment=prior.spec['environment'], financial=prior.spec['financial'],
        source_freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=HERE, text=True).strip(),
        scope='Exact unchanged full-row parser coverage, independently reproduced. No engine, model, array, fit, opponent or production operation is allocated.')
    D.write_new(ROOT / 'campaign-spec.json', spec)
    S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def stage(args):
    budget = S.Budget(args.spec)
    out = ROOT / (args.stage+'-1')
    receipt_path = ROOT / (args.stage+'-1-stage-receipt.json')
    with budget.lease() as run:
        status = 'failed'
        guard = None
        receipt = dict(stage=args.stage, cleanup_verified=True)
        try:
            descriptor = budget.spec['stages'][args.stage]
            actual = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]]
            run.begin(args.stage, argv=descriptor['argv'], guard=budget.spec['guard'],
                      inputs=list(run.state['proofs'].values()))
            receipt['source'] = S.pin(__file__)
            S.require(actual == descriptor['argv'] and args.spec.resolve() == ROOT / 'campaign-spec.json',
                      'canonical exact sealed command required')
            out.mkdir()
            E = importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds()) as guard:
                if args.stage == 'audit':
                    A = importlib.import_module('compositional_actual_admission')
                    value = A.audit(CATALOGUE, RUNTIME, PLAN, NATIVE_RECEIPT)
                    receipt['report'] = D.write_new(out / 'admission-report.json', value)
                    receipt['counts'] = value['counts']
                    S.require(value['boundary_passed'], 'unexpected acceptance persisted; stop for full-card review')
                elif args.stage == 'verify':
                    V = importlib.import_module('compositional_actual_admission_verify')
                    value = V.verify(CATALOGUE, RUNTIME, ROOT / 'audit-1/admission-report.json')
                    receipt['verification'] = D.write_new(out / 'verification-result.json', value)
                else:
                    raise ValueError('unallocated stage')
            status = 'completed'
        except BaseException as error:
            if run.state['pending'] is None:
                raise
            receipt['error'] = dict(type=type(error).__name__, message=str(error))
        receipt.update(status=status, guard=guard.receipt() if guard else None)
        rp = None
        try:
            rp = D.write_new(receipt_path, receipt)
        except BaseException as error:
            status = 'failed'
            receipt['receipt_write_error'] = dict(type=type(error).__name__, message=str(error))
        proofs = [S.pin(p) for p in sorted(out.rglob('*')) if p.is_file()] + ([rp] if rp else [])
        state = run.finish(status, proofs=proofs, cleanup_verified=True, execution_ended=True)
        S.require(status == 'completed' and args.stage in state['completed'],
                  'failed boundary stage; full reservation retained: '+str(receipt.get('error')))
        return dict(stage=args.stage, receipt=rp, cumulative=state['cumulative'])


def close():
    budget = S.Budget(ROOT / 'campaign-spec.json')
    state = budget.inspect()
    S.require(state['completed'] == budget.spec['stage_order'] and not state['failures']
              and state['pending'] is None, 'closed verified stages required')
    report = read(ROOT / 'audit-1/admission-report.json')
    verified = read(ROOT / 'verify-1/verification-result.json')
    S.require(report['counts']['parser_accepted'] == 0 and verified['verified'] is True,
              'independent full-row rejection verification required')
    value = dict(schema='jepa-compositional-actual-admission-closure/1',
        status='closed-verified-transfer-blocked', decision=report['decision'],
        source_freeze_commit=budget.spec['source_freeze_commit'], counts=report['counts'],
        report=S.pin(ROOT / 'audit-1/admission-report.json'),
        verification=S.pin(ROOT / 'verify-1/verification-result.json'),
        journal=S.pin(budget.ledger), final_chain=state['last_sha256'],
        new_charged=state['charged'], new_observed=state['observed'], cumulative=state['cumulative'],
        financial=budget.spec['financial'], production_changed=False, opponent_execution=False,
        measured_prediction_transfer=False, fresh_supported_semantic_families=0)
    return D.write_new(ROOT / 'experiment-closure.json', value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare','initialize','run','status','close'])
    parser.add_argument('--stage', choices=['audit','verify'])
    parser.add_argument('--spec', type=Path, default=ROOT / 'campaign-spec.json')
    args = parser.parse_args()
    value = prepare() if args.action == 'prepare' else S.Budget(args.spec).initialize(root_go=True) if args.action == 'initialize' else stage(args) if args.action == 'run' else close() if args.action == 'close' else S.Budget(args.spec).inspect()
    print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
