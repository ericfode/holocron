"""Byte-only once-only allocation for independent saved-output verification."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
PRIOR = D.EXPERIMENTS / 'ability-correction-v1'
ROOT = D.EXPERIMENTS / 'ability-correction-verification-v1'


def prepare():
    S.require(not ROOT.exists(), 'preserve every prior verification attempt')
    b = S.Budget(PRIOR / 'campaign-spec.json'); state = b.inspect()
    closure = D.read(PRIOR / 'experiment-closure.json')
    S.require(state['completed'] == b.spec['stage_order'] and not state['failures']
        and state['pending'] is None and closure['cumulative'] == state['cumulative'],
        'closed correction campaign required')
    for p in state['proofs'].values(): S.verify_pin(p)
    ROOT.mkdir()
    parent = copy.deepcopy(b.parent); parent['carry'] = state['cumulative']
    parent['pins'] += list(b.frozen.values())
    parent['pins'] += [S.pin(p) for p in PRIOR.rglob('*') if p.is_file()]
    parent['pins'] = list({p['path']: p for p in parent['pins']}.values())
    parent['closed_journals'].append(D.closed_journal(b.ledger))
    parent['protected_roots'].append(str(PRIOR))
    pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    py = b.spec['stages']['correction']['argv'][0]
    counts = dict(native_applies=0, neural_forwards=0, optimizer_updates=0,
        numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
    out = ROOT / 'verify-1'
    argv = [py, str(HERE / 'ability_correction_verify.py'), '--spec',
        str(ROOT / 'campaign-spec.json'), '--out', str(out)]
    files = [Path(__file__), HERE / 'ability_correction_verify.py',
        HERE / 'test_ability_correction_verify.py', HERE / 'ability_diagnostic_campaign.py', Path(py)]
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO', source=S.pin(S.__file__),
        primitives=S.pin(S._PATH), parent_manifest=pm, ledger_path=str(ROOT / 'campaign-ledger.jsonl'),
        caps=dict(seconds=3., **counts), guard=dict(cpu_workers=1, rss_bytes=1024**3),
        stage_order=['verify'], stages=dict(verify=dict(argv=argv,
            outputs=[str(out), str(ROOT / 'verify-1-stage-receipt.json')],
            reservation=dict(seconds=3., **counts), expected=counts, external_counters=[])),
        pins=[S.pin(p) for p in files], environment=b.spec['environment'],
        source_freeze_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        scope='Independent native-journal/array/metric checks on saved artifacts only; no inference, engine application, fitting or update.')
    D.write_new(ROOT / 'campaign-spec.json', spec)
    S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'initialize', 'status'])
    a = p.parse_args()
    if a.action == 'prepare': result = prepare()
    elif a.action == 'initialize': result = S.Budget(ROOT / 'campaign-spec.json').initialize(root_go=True)
    else: result = S.Budget(ROOT / 'campaign-spec.json').inspect()
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
