"""Linked source-frozen state-only correction test; preparation is byte-only."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
ROOT = D.EXPERIMENTS / 'ability-correction-v1'
DIAG = D.ROOT
CRATE = HERE / 'ability_correction_native_collector'
COUNTERS = dict(native_applies=0, neural_forwards=0, optimizer_updates=0,
    numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)


def load_guard():
    spec = importlib.util.spec_from_file_location('correction_guard_preparation', CRATE / 'supervise.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def prepare():
    S.require(not ROOT.exists(), 'exclusive new root; preserve every prior attempt')
    closure = D.read(DIAG / 'experiment-closure.json')
    b = S.Budget(DIAG / 'campaign-spec.json'); state = b.inspect()
    S.require(state['completed'] == ['diagnose'] and not state['failures']
        and state['pending'] is None and closure['cumulative'] == state['cumulative'],
        'closed diagnosis must precede correction allocation')
    for p in state['proofs'].values(): S.verify_pin(p)
    ROOT.mkdir()
    parent = copy.deepcopy(b.parent)
    parent['carry'] = closure['cumulative']
    parent['pins'] += [S.pin(p) for p in DIAG.rglob('*') if p.is_file()]
    parent['pins'] += [S.pin(p['path']) for p in state['proofs'].values()]
    parent['closed_journals'].append(D.closed_journal(b.ledger))
    parent['protected_roots'].append(str(DIAG))
    parent['pins'] = list({p['path']: p for p in parent['pins']}.values())
    pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    old = D.read(D.OLD / 'campaign-spec.json'); py = old['stage_descriptors']['fit']['argv'][0]
    guard = load_guard(); native = guard.descriptors(ROOT, py)
    command = [py, str(Path(__file__).resolve()), 'metadata', '--spec', str(ROOT / 'campaign-spec.json')]
    stages = dict(metadata=dict(argv=command, outputs=[str(ROOT / 'native-plan.json'), str(ROOT / 'metadata-1')],
        reservation=dict(seconds=3., **COUNTERS), expected=dict(COUNTERS), external_counters=[]))
    for name in ('build', 'native'):
        counts = dict(COUNTERS)
        if name == 'native': counts['native_applies'] = 32
        stages[name] = dict(**native[name], reservation=dict(seconds=10. if name == 'build' else 15., **counts),
            expected=dict(counts, **({'native_applies': None} if name == 'native' else {})),
            external_counters=['native_applies'] if name == 'native' else [])
    common = ['--spec', str(ROOT / 'campaign-spec.json'), '--old-plan', str(D.OLD / 'prep-1/sealed-fit-plan.json')]
    prep = ROOT / 'prep-1'; out = ROOT / 'correction-1'
    stages['prep'] = dict(argv=[py, str(HERE / 'ability_correction_prepare.py'), *common,
        '--native-plan', str(ROOT / 'native-plan.json'), '--native-manifest', str(ROOT / 'metadata-1/native-source-manifest.json'),
        '--native-receipt', str(ROOT / 'native-attempt-1/native-receipt.json'), '--journal', str(ROOT / 'native-attempt-1/native-transitions.jsonl'), '--out', str(prep)],
        outputs=[str(prep), str(ROOT / 'prep-1-stage-receipt.json')],
        reservation=dict(seconds=3., **COUNTERS), expected=dict(COUNTERS), external_counters=[])
    counts = dict(COUNTERS, neural_forwards=6)
    stages['correction'] = dict(argv=[py, str(HERE / 'ability_correction.py'), *common,
        '--fit-dir', str(D.OLD / 'fit-1'), '--dataset', str(prep / 'dataset.npz'),
        '--manifest', str(prep / 'dataset.manifest.json'), '--out', str(out)],
        outputs=[str(out), str(ROOT / 'correction-1-stage-receipt.json')],
        reservation=dict(seconds=10., **counts), expected=counts, external_counters=[])
    paths = [Path(__file__), HERE / 'ability_correction.py', HERE / 'ability_correction_prepare.py',
        HERE / 'ability_correction_native_plan.py', HERE / 'test_ability_correction.py',
        HERE / 'test_ability_correction_prepare.py', HERE / 'test_ability_correction_native_plan.py',
        HERE / 'ABILITY_DIAGNOSTIC_PROTOCOL.md', HERE / 'ability_diagnostic_campaign.py', Path(py)]
    paths += [p for p in CRATE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    # Every engine input is immutable before metadata/compilation; the metadata
    # writer additionally declares exact selected rows and preserved binaries.
    engine = guard.ENGINE
    paths += [engine / 'Cargo.toml', engine / 'Cargo.lock', guard.CARGO]
    paths += [p for p in (engine / 'crates/kessel').rglob('*') if p.is_file() and 'target' not in p.parts]
    paths += list((engine / 'compiler/generated').rglob('*.json'))
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=S.pin(S.__file__),
        primitives=S.pin(S._PATH), parent_manifest=pm, ledger_path=str(ROOT / 'campaign-ledger.jsonl'),
        caps=dict(seconds=41., **dict(COUNTERS, native_applies=32, neural_forwards=6)),
        guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=list(stages), stages=stages,
        pins=[S.pin(p) for p in sorted(set(paths))], environment=old['environment'],
        source_freeze_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        correction_selection=dict(diagnosis_result=closure['result'],
            decision='Exclude intended relation from eligibility only; retain it for actual endpoints.',
            evidence='Fixed-weight discovery makes intent dependence zero and preserves all other heads; neutralizing every head damages removal. One discovery seed has a small eligibility MAE regression, so fresh accuracy remains an explicit gate.',
            heldout_scope='Four new public states of an exposed program; no fresh program or semantic family claim.',
            no_training=True, added_parameters=0,
            reference_limit='The analytical helper misclassifies sixteen healthy-heal offers. All fresh labels must come from measured native observations, never its predictions.'),
        scope='Four fresh public-state pairs of exposed IBH_104; no updates, new symbols, opponent execution or production change.')
    D.write_new(ROOT / 'campaign-spec.json', spec); S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def metadata(spec_path):
    budget = S.Budget(spec_path)
    with budget.lease() as run:
        status = 'failed'; error = None; made = []
        try:
            argv = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]]
            run.begin('metadata', argv=argv, guard=budget.spec['guard'])
            import effect_identifiability_fit as E
            with E.Guard(run.remaining_seconds()):
                import ability_correction_native_plan as P
                plan = P.prepare_plan()
                made.append(D.write_new(ROOT / 'native-plan.json', plan))
                root = ROOT / 'metadata-1'; root.mkdir()
                g = load_guard(); g.write_source_manifest(ROOT / 'native-plan.json', root / 'native-source-manifest.json', ROOT, budget.spec['source_freeze_commit'])
                made.append(S.pin(root / 'native-source-manifest.json'))
            status = 'completed'
        except BaseException as exc:
            if run.state['pending'] is None: raise
            error = dict(type=type(exc).__name__, message=str(exc))
        state = run.finish(status, proofs=made, cleanup_verified=True, execution_ended=True)
        S.require('metadata' in state['completed'], 'metadata failed; full reservation retained: ' + str(error))
        return dict(status=status, proofs=made, cumulative=state['cumulative'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'initialize', 'status', 'metadata'])
    p.add_argument('--spec', type=Path, default=ROOT / 'campaign-spec.json')
    a = p.parse_args()
    if a.action == 'prepare': result = prepare()
    elif a.action == 'initialize': result = S.Budget(a.spec).initialize(root_go=True)
    elif a.action == 'metadata': result = metadata(a.spec)
    else: result = S.Budget(a.spec).inspect()
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
