"""Byte-only preparation of a linked, once-only diagnostic allocation."""
import argparse
import copy
import json
from pathlib import Path

import sealed_budget as S

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[3] / 'experiments'
OLD = EXPERIMENTS / 'semantic-discrimination-repair-v1'
VERIFY = EXPERIMENTS / 'semantic-discrimination-verification-v1'
ROOT = EXPERIMENTS / 'ability-diagnostic-v1'


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    import os
    data = S.encoded(value) + b'\n'
    with Path(path).open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    return S.pin(path)


def closed_journal(path):
    rows = [json.loads(v) for v in Path(path).read_text().splitlines() if v.strip()]
    S.require(rows, 'closed journal required')
    return dict(pin=S.pin(path), records=len(rows), final_chain=rows[-1]['record_sha256'],
        genesis_previous=rows[0]['previous_sha256'], closed_event=rows[-1]['event'])


def parent_manifest():
    old = read(OLD / 'campaign-spec.json')
    parent = copy.deepcopy(read(old['prior_manifest']['path']))
    closure = read(VERIFY / 'experiment-closure.json')
    S.require(closure['status'] == 'closed-verified-negative'
        and closure['cumulative']['charged_native_applies'] == 275
        and closure['cumulative']['charged_seconds'] == 215.3528530828189,
        'exact closed parent carry required')
    parent['carry'] = {k: closure['cumulative'][k] for k in
        ('charged_native_applies', 'charged_seconds', 'observed_native_applies')}
    parent['closed_journals'] += [closed_journal(OLD / 'campaign-ledger.jsonl'),
        closed_journal(VERIFY / 'campaign-ledger.jsonl')]
    parent['pins'] += read(VERIFY / 'campaign-spec.json')['pins']
    parent['pins'] += [S.pin(p) for p in VERIFY.rglob('*') if p.is_file()]
    parent['protected_roots'] += [str(OLD), str(VERIFY)]
    unique = {}
    for p in parent['pins']:
        S.verify_pin(p)
        S.require(p['path'] not in unique or unique[p['path']] == p, 'conflicting parent pin')
        unique[p['path']] = p
    parent['pins'] = [unique[k] for k in sorted(unique)]
    parent['financial'] = closure['financial']
    parent['scope'] = 'No prior reservation, failed charge, knownness, protected workspace or closed journal reset.'
    return parent


def prepare():
    """No numerical import, model construction, ledger initialization or engine."""
    import ability_diagnostic as D
    import subprocess
    S.require(not ROOT.exists(), 'one canonical NEW root; preserve every attempt')
    ROOT.mkdir()
    parent = write_new(ROOT / 'parent-manifest.json', parent_manifest())
    plan = ROOT / 'diagnostic-plan.json'
    D.prepare(OLD / 'prep-1/sealed-fit-plan.json', OLD / 'fit-1', plan)
    old = read(OLD / 'campaign-spec.json')
    py = old['stage_descriptors']['fit']['argv'][0]
    out = ROOT / 'diagnosis-1'
    argv = [py, str(HERE / 'ability_diagnostic.py'), '--execute', '--spec',
        str(ROOT / 'campaign-spec.json'), '--plan', str(plan), '--out', str(out)]
    counters = dict(native_applies=0, neural_forwards=33, optimizer_updates=0,
        numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
    pins = read(plan)['pins'] + [S.pin(plan), S.pin(py)]
    pins += [S.pin(HERE / name) for name in ('ability_diagnostic.py',
        'ability_typed_reference.py', 'test_ability_diagnostic.py',
        'test_ability_typed_reference.py', 'test_sealed_budget.py')]
    pins += [S.pin(HERE / 'ABILITY_DIAGNOSTIC_PROTOCOL.md'), S.pin(__file__)]
    unique = {p['path']: p for p in pins}
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO',
        source=S.pin(S.__file__), primitives=S.pin(S._PATH), parent_manifest=parent,
        ledger_path=str(ROOT / 'campaign-ledger.jsonl'),
        caps=dict(seconds=15., **counters), guard=dict(cpu_workers=1, rss_bytes=1024**3),
        stage_order=['diagnose'], stages=dict(diagnose=dict(argv=argv, outputs=[str(out)],
            reservation=dict(seconds=15., **counters), expected=counters,
            external_counters=[])), pins=[unique[k] for k in sorted(unique)],
        environment=old['environment'], source_freeze_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        scope='33 fixed-weight discovery forwards only; zero training/native/paid work. All old charges retained.')
    write_new(ROOT / 'campaign-spec.json', spec)
    # Validation has no side effects and cannot start scientific work.
    S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'initialize', 'status'])
    a = p.parse_args()
    if a.action == 'prepare': value = prepare()
    elif a.action == 'initialize': value = S.Budget(ROOT / 'campaign-spec.json').initialize(root_go=True)
    else: value = S.Budget(ROOT / 'campaign-spec.json').inspect()
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
