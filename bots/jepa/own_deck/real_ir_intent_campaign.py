"""Sealed typed-intent comparison; terminal native outcomes follow all fitting.

Import and contract helpers are metadata-only. ROOT alone prepares, initializes
and executes the fixed allocation after source freeze. Prior ledgers stay closed.
"""
import argparse
import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
ROOT = D.EXPERIMENTS / 'real-ir-intent-v1'
PRIOR = D.EXPERIMENTS / 'real-ir-intent-diagnostic-v1'
OLD = D.EXPERIMENTS / 'real-ir-transfer-v1'
HP = D.EXPERIMENTS / 'real-ir-hp-projection-v1'
CRATE = HERE / 'real_ir_intent_native_collector'
ENGINE = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
RESERVATION = D.EXPERIMENTS / 'real-ir-hp-fresh-reservation.json'
RESERVATION_SHA = '64d114c84a454546e16c906815980f167d35c4f6d9a0884402a0105e76cc1bb8'
CARRY = dict(charged_native_applies=1031, charged_seconds=313.4962767929537,
             observed_native_applies=None)
ZERO = dict(native_applies=0, neural_forwards=0, backwards=0,
            optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
SECONDS = dict(build=20., **{'dev-native': 30.}, prep=10., fit=90.,
               **{'terminal-native': 15., 'terminal-prep': 10.}, score=20., verify=10.)
CAPS = dict(seconds=205., **dict(ZERO, native_applies=240, neural_forwards=2724,
                               backwards=2700, optimizer_updates=2700))
PRESERVED = ['ASH_259', 'HMW_158', 'LOF_259']


def read(path): return json.loads(Path(path).read_text())


def descriptors(python, root, script):
    """Pure fixed allocation: no scoring or terminal outcomes before all fits."""
    root, script = Path(root), Path(script)
    stages = {}
    for name, seconds in SECONDS.items():
        counts = dict(ZERO)
        if name in ('dev-native', 'terminal-native'):
            counts['native_applies'] = 200 if name == 'dev-native' else 40
        if name == 'fit': counts.update(neural_forwards=2700, backwards=2700, optimizer_updates=2700)
        if name == 'score': counts['neural_forwards'] = 24
        native = name in ('dev-native', 'terminal-native')
        stages[name] = dict(argv=[str(python), str(script), 'run', '--stage', name,
            '--spec', str(root / 'campaign-spec.json')],
            outputs=[str(root / (name + '-1')), str(root / (name + '-1-stage-receipt.json'))],
            reservation=dict(seconds=seconds, **counts),
            expected=dict(counts, **({'native_applies': None} if native else {})),
            external_counters=['native_applies'] if native else [])
    return stages


def amendment(reservation, reservation_pin, declaration):
    """Release one source without changing the original four-source reservation."""
    S.require(reservation_pin['sha256'] == RESERVATION_SHA and
        reservation['status'] == 'reserved-no-new-outcomes' and
        reservation['reserved_codes'] == ['ASH_259', 'HMW_158', 'LOF_259', 'SOR_132'],
        'exact unchanged four-source reservation required')
    S.require(declaration['released_terminal_source'] == 'SOR_132' and
        sorted(declaration['remaining_reserved_codes']) == PRESERVED and
        declaration['native_outcome_order'] == ['development', 'all-fitted-checkpoints-sealed', 'terminal'],
        'only SOR_132 may be released after all fits')
    value = copy.deepcopy(declaration)
    value.update(status='terminal-release-preregistered', original_reservation=copy.deepcopy(reservation_pin),
        remaining_reserved_codes=list(PRESERVED), remaining_conservative_groups=[['ASH_259', 'LOF_259'], ['HMW_158']],
        fresh_scope='SOR_132 source outcomes only; its public IR was previously inspected. Three sources/two conservative groups remain reserved.',
        semantic_validated=False)
    return value


def validate_panels(panels):
    S.require(set(panels) == {'development', 'terminal', 'preregistration'}, 'two complete panels and preregistration required')
    for name, roots, cap, seconds in (('development', 56, 200, 30), ('terminal', 8, 40, 15)):
        p = panels[name]; selected = set(p['selected_whole_cards'])
        S.require(p['panel_role'] == name and p['expected_cases'] == len(p['worlds']) == roots and
            p['collector_max_engine_applies'] == cap and p['collector_max_seconds'] == seconds and
            p['terminal_outcomes_after_all_checkpoints'] == (name == 'terminal') and
            not selected.intersection(PRESERVED) and ('SOR_132' in selected) == (name == 'terminal'),
            'frozen native role/quantity/reservation contract differs')


def admit_data(manifest, terminal=False):
    """Fail closed on declared quantities before any fit or terminal scoring."""
    def reference_ok(ref, terminal=False):
        expected = dict(known_coordinates=52 if terminal else 371,
            known_eligibility=48 if terminal else 336, known_intended_deltas=4 if terminal else 35,
            mismatch_count=0, removed_count=0 if terminal else 1, removal_mismatch_count=0)
        return all(ref.get(k) == v for k, v in expected.items()) and ref.get('mismatches', []) == []
    S.require(manifest['schema'] == 'jepa-real-ir-intent-data/1' and
        manifest['fit_admitted'] is True and not manifest['fit_blockers'] and
        reference_ok(manifest['reference']) and
        manifest['support'] == dict(development_known_endpoints=35, primary=29, replay=6, removed=1),
        'development native/reference/support gate blocks fitting: ' + str(manifest['fit_blockers']))
    if terminal:
        S.require(manifest['terminal_admitted'] is True and not manifest['terminal_blockers'] and
            reference_ok(manifest['terminal_reference'], terminal=True),
            'terminal native/reference gate blocks scoring: ' + str(manifest['terminal_blockers']))


def prepare():
    import real_ir_intent_plan as P
    S.require(not ROOT.exists(), 'new canonical allocation only; never reopen history')
    prior = S.Budget(PRIOR / 'campaign-spec.json'); state = prior.inspect(); closure = read(PRIOR / 'experiment-closure.json')
    S.require(state['completed'] == ['diagnose'] and not state['failures'] and state['pending'] is None and
        state['cumulative'] == closure['cumulative'] == CARRY and closure['status'] == 'closed-saved-diagnostic' and
        all(state['charged'][k] == 0 for k in ZERO), 'exact closed zero-science intent diagnosis required')
    reservation_pin = S.pin(RESERVATION); reservation = read(RESERVATION)
    panels = P.build(read(OLD / 'metadata-1/native-plan.json'), reservation); validate_panels(panels)
    released = amendment(reservation, reservation_pin, panels['preregistration'])
    ROOT.mkdir(); metadata = ROOT / 'metadata-1'; metadata.mkdir()
    plan_pins = {name: D.write_new(metadata / (name + '-plan.json'), panels[name]) for name in ('development', 'terminal')}
    release_pin = D.write_new(metadata / 'preregistration.json', released)
    parent = copy.deepcopy(prior.parent); parent['carry'] = state['cumulative']; pins = {p['path']: p for p in parent['pins']}
    for p in list(prior.frozen.values()) + [S.pin(p) for p in PRIOR.rglob('*') if p.is_file()]:
        S.verify_pin(p); S.require(p['path'] not in pins or pins[p['path']] == p, 'immutable parent conflict'); pins[p['path']] = p
    parent['pins'] = [pins[k] for k in sorted(pins)]; parent['protected_roots'].append(str(PRIOR))
    parent['closed_journals'].append(D.closed_journal(prior.ledger)); pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    scientific = read(HP / 'campaign-spec.json'); python = scientific['stages']['fit']['argv'][0]
    stages = descriptors(python, ROOT, Path(__file__).resolve())
    names = ('real_ir_intent_campaign.py', 'test_real_ir_intent_campaign.py', 'real_ir_intent_plan.py',
        'test_real_ir_intent_plan.py', 'real_ir_intent_data.py', 'test_real_ir_intent_data.py',
        'real_ir_intent_model.py', 'test_real_ir_intent_model.py', 'real_ir_intent_fit.py',
        'test_real_ir_intent_fit.py', 'real_ir_intent_verify.py', 'test_real_ir_intent_verify.py',
        'REAL_IR_INTENT_PROTOCOL.md', 'effect_identifiability_fit.py',
        'semantic_discrimination_native_collector/supervise_v2.py')
    files = [HERE / n for n in names] + [Path(python), Path('/Users/ericfode/.cargo/bin/cargo'), RESERVATION,
        metadata / 'development-plan.json', metadata / 'terminal-plan.json', metadata / 'preregistration.json',
        ENGINE / 'Cargo.toml', ENGINE / 'Cargo.lock']
    files += [p for p in CRATE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'target' not in p.parts]
    freeze = subprocess.check_output(['git', '--no-optional-locks', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip()
    S.require(len(freeze) == 40 and all(c in '0123456789abcdef' for c in freeze), 'full source-freeze commit required')
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=S.pin(S.__file__), primitives=S.pin(S._PATH),
        parent_manifest=pm, ledger_path=str(ROOT / 'campaign-ledger.jsonl'), caps=dict(CAPS),
        guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=list(stages), stages=stages,
        pins=[S.pin(p) for p in sorted(set(files))], environment=scientific['environment'], financial=prior.spec['financial'],
        protocol=S.pin(HERE / 'REAL_IR_INTENT_PROTOCOL.md'), source_freeze_commit=freeze,
        prior_root=str(OLD), hp_prior_root=str(HP), diagnostic_root=str(PRIOR), prelabel_reservation=reservation_pin,
        reservation_amendment=release_pin, native_plans=plan_pins,
        scope='Original TRAIN40 only. Seven exposed event sources are developmental. SOR_132 outcomes after every fitted checkpoint; other three reserved sources unused. Typed intent/application slot, no whole-card or deck qualification.')
    D.write_new(ROOT / 'campaign-spec.json', spec); S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def native_worker():
    loader = importlib.util.spec_from_file_location('real_ir_intent_owned_process', CRATE / 'supervise.py')
    module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module); return module


def stage(args):
    budget = S.Budget(args.spec); args.root = ROOT; args.out = ROOT / (args.stage + '-1')
    args.plan = ROOT / 'metadata-1' / ('terminal-plan.json' if args.stage == 'terminal-native' else 'development-plan.json')
    receipt_path = ROOT / (args.stage + '-1-stage-receipt.json')
    with budget.lease() as run:
        status = 'failed'; guard = None; receipt = dict(stage=args.stage, cleanup_verified=True)
        try:
            descriptor = budget.spec['stages'][args.stage]
            run.begin(args.stage, argv=descriptor['argv'], guard=budget.spec['guard'], inputs=list(run.state['proofs'].values()))
            S.require([str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]] == descriptor['argv'] and
                args.spec.resolve() == ROOT / 'campaign-spec.json', 'exact sealed runtime command required')
            S.require(all(os.environ.get(k) == v for k, v in budget.spec['environment'].items()), 'exact sealed environment required')
            receipt['source'] = S.pin(__file__); args.out.mkdir(); E = importlib.import_module('effect_identifiability_fit')
            with E.Guard(run.remaining_seconds()) as guard:
                if args.stage in ('build', 'dev-native', 'terminal-native'): native_worker().worker(args, run, receipt)
                elif args.stage in ('prep', 'terminal-prep'):
                    import numpy as np
                    C = importlib.import_module('real_ir_intent_data')
                    arrays, manifest = C.prepare_development(np, OLD, HP, ROOT) if args.stage == 'prep' else C.prepare_terminal(np, ROOT)
                    np.savez_compressed(args.out / 'dataset.npz', **arrays); D.write_new(args.out / 'manifest.json', manifest)
                    admit_data(manifest, terminal=args.stage == 'terminal-prep')
                    receipt['reference'] = manifest['reference']; receipt['support'] = manifest['support']
                    if args.stage == 'terminal-prep': receipt['terminal_reference'] = manifest['terminal_reference']
                elif args.stage in ('fit', 'score'):
                    args.prior = OLD; args.hp_prior = HP
                    panel = 'prep-1' if args.stage == 'fit' else 'terminal-prep-1'
                    args.dataset = ROOT / panel / 'dataset.npz'; args.manifest = ROOT / panel / 'manifest.json'
                    admit_data(read(args.manifest), terminal=args.stage == 'score')
                    F = importlib.import_module('real_ir_intent_fit')
                    receipt['result'] = (F.fit_worker if args.stage == 'fit' else F.score_worker)(args, run)
                elif args.stage == 'verify':
                    import numpy as np
                    receipt['verification'] = importlib.import_module('real_ir_intent_verify').verify(np, ROOT, args.out)
                else: raise ValueError('unallocated stage')
            status = 'completed'
        except BaseException as error:
            if run.state['pending'] is None: raise
            receipt['error'] = dict(type=type(error).__name__, message=str(error))
        receipt.update(status=status, guard=guard.receipt() if guard else None); rp = None
        try: rp = D.write_new(receipt_path, receipt)
        except BaseException as error:
            status = 'failed'; receipt['receipt_write_error'] = dict(type=type(error).__name__, message=str(error))
        if receipt.get('cleanup_verified') is not True:
            run.pending_failure('owned cleanup/execution unresolved: ' + str(receipt.get('error')))
            raise RuntimeError('retain pending full reservation; no retry')
        proofs = [S.pin(p) for p in sorted(args.out.rglob('*')) if p.is_file()] + ([rp] if rp else [])
        state = run.finish(status, proofs=proofs, cleanup_verified=True, execution_ended=True)
        S.require(status == 'completed' and args.stage in state['completed'], 'allocation failed; full reservation retained: ' + str(receipt.get('error')))
        return dict(stage=args.stage, receipt=rp, charged=state['charged'], cumulative=state['cumulative'])


def close():
    b = S.Budget(ROOT / 'campaign-spec.json'); state = b.inspect()
    S.require(state['completed'] == list(SECONDS) and not state['failures'] and state['pending'] is None, 'all eight verified stages required')
    verified = read(ROOT / 'verify-1/verification-result.json'); score = read(ROOT / 'score-1/result.json')
    manifest = read(ROOT / 'terminal-prep-1/manifest.json'); admit_data(manifest, terminal=True)
    S.require(verified['verified'] is True, 'independent saved-output verification required')
    value = dict(schema='jepa-real-ir-intent-closure/1', status='closed-verified-typed-intent', source_freeze_commit=b.spec['source_freeze_commit'],
        prelabel_reservation=b.spec['prelabel_reservation'], reservation_amendment=b.spec['reservation_amendment'], native_plans=b.spec['native_plans'],
        development_native=S.pin(ROOT / 'dev-native-1/receipt.json'), terminal_native=S.pin(ROOT / 'terminal-native-1/receipt.json'),
        data_manifest=S.pin(ROOT / 'terminal-prep-1/manifest.json'), fit_result=S.pin(ROOT / 'fit-1/result.json'),
        score_result=S.pin(ROOT / 'score-1/result.json'), verification=S.pin(ROOT / 'verify-1/verification-result.json'),
        decisions=score['decisions'], reference=manifest['reference'], terminal_reference=manifest['terminal_reference'],
        journal=S.pin(b.ledger), final_chain=state['last_sha256'], new_charged=state['charged'], new_observed=state['observed'],
        cumulative=state['cumulative'], financial=b.spec['financial'], remaining_reserved_codes=list(PRESERVED),
        production_changed=False, opponent_execution=False, card_conversion_run=False, generic_card_embedding_qualified=False, semantic_validated=False)
    return D.write_new(ROOT / 'experiment-closure.json', value)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['prepare', 'initialize', 'run', 'status', 'close'])
    p.add_argument('--stage', choices=list(SECONDS)); p.add_argument('--spec', type=Path, default=ROOT / 'campaign-spec.json'); args = p.parse_args()
    if args.action == 'run':
        b = S.Budget(args.spec); argv = b.spec['stages'][args.stage]['argv']; env = dict(os.environ, **b.spec['environment'])
        if str(Path(sys.executable).resolve()) != argv[0] or any(os.environ.get(k) != v for k, v in b.spec['environment'].items()): os.execve(argv[0], argv, env)
    value = prepare() if args.action == 'prepare' else S.Budget(args.spec).initialize(root_go=True) if args.action == 'initialize' else stage(args) if args.action == 'run' else close() if args.action == 'close' else S.Budget(args.spec).inspect()
    print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == '__main__': main()
