"""Saved-verification recovery only; never reopen the failed scientific ledger.

ROOT closes the original failure honestly, then freezes a separate20s zero-call
allocation. This module performs no work at import and never imports a model.
"""
import argparse
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
ORIGINAL = D.EXPERIMENTS / 'real-ir-intent-v1'
ROOT = D.EXPERIMENTS / 'real-ir-intent-saved-v1'
ORDER = ['build', 'dev-native', 'prep', 'fit', 'terminal-native', 'terminal-prep', 'score', 'verify']
ZERO = dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0,
            numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)


def read(path): return json.loads(Path(path).read_text())


def original_failure(state, last, receipt):
    """Only the known ended saved-verifier failure can seed this allocation."""
    S.require(state['completed'] == ORDER[:-1] and state['failures'] == 1 and
        state['pending'] is None and state['violated'] is False and
        last['event'] == 'finish' and last['record_sha256'] == state['last_sha256'] and
        last['data']['status'] == 'failed' and last['data']['cleanup_verified'] is True and
        last['data']['execution_ended'] is True and last['data']['integrity_error'] is None and
        last['data']['charged'] == dict(seconds=10., **ZERO) and
        last['data']['durable_intents'] == last['data']['durable_completed'] == ZERO and
        receipt['stage'] == 'verify' and receipt['status'] == 'failed' and receipt['cleanup_verified'] is True and
        receipt['error'] == dict(type='KeyError', message="'schema'"),
        'exact ended zero-call verify failure/full10s charge required; no credit or retry')


def closed_original():
    budget = S.Budget(ORIGINAL / 'campaign-spec.json'); state = budget.inspect()
    last = json.loads(budget.ledger.read_text().splitlines()[-1]); receipt = read(ORIGINAL / 'verify-1-stage-receipt.json')
    S.require(budget.spec['stage_order'] == ORDER, 'original eight-stage scientific contract required')
    original_failure(state, last, receipt)
    S.require(S.pin(ORIGINAL / 'verify-1-stage-receipt.json') in last['data']['proofs'], 'exact failed receipt must remain bound to the closed ledger')
    for p in last['data']['proofs']: S.verify_pin(p)
    return budget, state


def close_failed():
    budget, state = closed_original()
    score = read(ORIGINAL / 'score-1/result.json')
    value = dict(schema='jepa-real-ir-intent-failed-closure/1', status='closed-failed-saved-verification',
        source_freeze_commit=budget.spec['source_freeze_commit'], closure_source=S.pin(__file__),
        spec=S.pin(budget.path), journal=S.pin(budget.ledger), final_chain=state['last_sha256'],
        completed_stages=state['completed'], failed_stage='verify', failed_stage_receipt=S.pin(ORIGINAL / 'verify-1-stage-receipt.json'),
        verifier_failure=dict(type='KeyError', message="'schema'", scope='Inherited historical journal schema reader; saved scoring remains unverified here.'),
        development_native=S.pin(ORIGINAL / 'dev-native-1/receipt.json'), terminal_native=S.pin(ORIGINAL / 'terminal-native-1/receipt.json'),
        fit_result=S.pin(ORIGINAL / 'fit-1/result.json'), score_result=S.pin(ORIGINAL / 'score-1/result.json'),
        data_manifest=S.pin(ORIGINAL / 'terminal-prep-1/manifest.json'), reservation_amendment=budget.spec['reservation_amendment'],
        decisions=score['decisions'], decisions_independently_verified=False,
        new_charged=state['charged'], new_observed=state['observed'], cumulative=state['cumulative'],
        financial=budget.spec['financial'], original_ledger_reopened=False, failed_charge_credited=False,
        production_changed=False, semantic_validated=False)
    return D.write_new(ORIGINAL / 'experiment-closure.json', value)


def descriptor(python, script, root):
    root = Path(root)
    return dict(argv=[str(python), str(script), 'run', '--spec', str(root / 'campaign-spec.json')],
        outputs=[str(root / 'verify-1'), str(root / 'verify-1-stage-receipt.json')],
        reservation=dict(seconds=20., **ZERO), expected=dict(ZERO), external_counters=[])


def prepare():
    S.require(not ROOT.exists(), 'new saved-only allocation; never reopen a ledger')
    prior, state = closed_original(); closure = read(ORIGINAL / 'experiment-closure.json')
    S.require(closure['status'] == 'closed-failed-saved-verification' and
        closure['cumulative'] == state['cumulative'] and closure['final_chain'] == state['last_sha256'] and
        closure['journal'] == S.pin(prior.ledger) and closure['failed_charge_credited'] is False,
        'full failed closure must precede the linked allocation')
    parent = copy.deepcopy(prior.parent); parent['carry'] = state['cumulative']; pins = {p['path']: p for p in parent['pins']}
    for p in list(prior.frozen.values()) + [S.pin(p) for p in ORIGINAL.rglob('*') if p.is_file()]:
        S.verify_pin(p); S.require(p['path'] not in pins or pins[p['path']] == p, 'immutable failed-parent conflict'); pins[p['path']] = p
    parent['pins'] = [pins[k] for k in sorted(pins)]; parent['protected_roots'].append(str(ORIGINAL))
    parent['closed_journals'].append(D.closed_journal(prior.ledger))
    ROOT.mkdir(); pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    python = prior.spec['stages']['verify']['argv'][0]
    files = [HERE / n for n in ('real_ir_intent_recovery_campaign.py', 'test_real_ir_intent_recovery_campaign.py',
        'real_ir_intent_verify_v2.py', 'test_real_ir_intent_verify_v2.py', 'real_ir_intent_verify.py',
        'test_real_ir_intent_verify.py', 'REAL_IR_INTENT_SAVED_PROTOCOL.md', 'effect_identifiability_fit.py')]
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=S.pin(S.__file__), primitives=S.pin(S._PATH),
        parent_manifest=pm, ledger_path=str(ROOT / 'campaign-ledger.jsonl'), caps=dict(seconds=20., **ZERO),
        guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=['verify'],
        stages=dict(verify=descriptor(python, Path(__file__).resolve(), ROOT)), pins=[S.pin(p) for p in files + [Path(python)]],
        environment=prior.spec['environment'], financial=prior.spec['financial'], original_root=str(ORIGINAL),
        original_source_freeze_commit=prior.spec['source_freeze_commit'], failed_closure=S.pin(ORIGINAL / 'experiment-closure.json'),
        source_freeze_commit=subprocess.check_output(['git', '--no-optional-locks', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        protocol=S.pin(HERE / 'REAL_IR_INTENT_SAVED_PROTOCOL.md'),
        scope='Saved-only verification; exact old arrays/checkpoints/scores and all failed charges preserved. No new native, neural, backward, update, numerical-fit or paid calls.')
    D.write_new(ROOT / 'campaign-spec.json', spec); S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def stage(args):
    budget = S.Budget(args.spec); out = ROOT / 'verify-1'; receipt_path = ROOT / 'verify-1-stage-receipt.json'
    with budget.lease() as run:
        status = 'failed'; guard = None; receipt = dict(stage='verify', cleanup_verified=True)
        try:
            d = budget.spec['stages']['verify']; run.begin('verify', argv=d['argv'], guard=budget.spec['guard'], inputs=list(run.state['proofs'].values()))
            S.require([str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]] == d['argv'] and
                args.spec.resolve() == ROOT / 'campaign-spec.json', 'exact sealed saved-verification runtime required')
            S.require(all(os.environ.get(k) == v for k, v in budget.spec['environment'].items()), 'sealed scientific environment required')
            out.mkdir(); E = importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds()) as guard:
                import numpy as np
                receipt['verification'] = importlib.import_module('real_ir_intent_verify_v2').verify(np, ORIGINAL, out)
                S.require(receipt['verification']['verified'] is True, 'saved-output verification did not pass')
            status = 'completed'
        except BaseException as error:
            if run.state['pending'] is None: raise
            receipt['error'] = dict(type=type(error).__name__, message=str(error))
        receipt.update(status=status, guard=guard.receipt() if guard else None); rp = None
        try: rp = D.write_new(receipt_path, receipt)
        except BaseException as error:
            status = 'failed'; receipt['receipt_write_error'] = dict(type=type(error).__name__, message=str(error))
        state = run.finish(status, proofs=[S.pin(p) for p in sorted(out.rglob('*')) if p.is_file()] + ([rp] if rp else []),
            cleanup_verified=True, execution_ended=True)
        S.require(status == 'completed' and state['completed'] == ['verify'], 'saved verification failed; full20s reservation retained: ' + str(receipt.get('error')))
        return dict(receipt=rp, charged=state['charged'], cumulative=state['cumulative'])


def close():
    budget = S.Budget(ROOT / 'campaign-spec.json'); state = budget.inspect(); result = read(ROOT / 'verify-1/verification-result.json')
    S.require(state['completed'] == ['verify'] and not state['failures'] and state['pending'] is None and result['verified'] is True,
        'one complete saved-only verification required')
    return D.write_new(ROOT / 'experiment-closure.json', dict(schema='jepa-real-ir-intent-saved-closure/1', status='closed-verified-saved-intent',
        source_freeze_commit=budget.spec['source_freeze_commit'], original_source_freeze_commit=budget.spec['original_source_freeze_commit'],
        original_failed_closure=budget.spec['failed_closure'], verification=S.pin(ROOT / 'verify-1/verification-result.json'),
        journal=S.pin(budget.ledger), final_chain=state['last_sha256'], new_charged=state['charged'], new_observed=state['observed'],
        cumulative=state['cumulative'], financial=budget.spec['financial'], original_ledger_reopened=False,
        failed_charge_credited=False, production_changed=False, semantic_validated=False))


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['close-failed', 'prepare', 'initialize', 'run', 'status', 'close'])
    p.add_argument('--spec', type=Path, default=ROOT / 'campaign-spec.json'); args = p.parse_args()
    if args.action == 'run':
        b = S.Budget(args.spec); argv = b.spec['stages']['verify']['argv']; env = dict(os.environ, **b.spec['environment'])
        if str(Path(sys.executable).resolve()) != argv[0] or any(os.environ.get(k) != v for k, v in b.spec['environment'].items()): os.execve(argv[0], argv, env)
    value = close_failed() if args.action == 'close-failed' else prepare() if args.action == 'prepare' else S.Budget(args.spec).initialize(root_go=True) if args.action == 'initialize' else stage(args) if args.action == 'run' else close() if args.action == 'close' else S.Budget(args.spec).inspect()
    print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == '__main__': main()
