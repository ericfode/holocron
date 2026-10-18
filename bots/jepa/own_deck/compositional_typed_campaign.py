"""Source-frozen, once-only elementary binding comparison.

Import and prepare are byte/metadata only. Every engine/numerical operation is
inside its separate sealed stage. Previous attempts remain protected and charged.
"""
import argparse
import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import sealed_budget as S
import ability_diagnostic_campaign as D

HERE = Path(__file__).resolve().parent
ROOT = D.EXPERIMENTS / 'compositional-typed-v1'
PRIOR = D.EXPERIMENTS / 'ability-correction-verification-v1'
CRATE = HERE / 'compositional_typed_native_collector'
ENGINE = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
TARGET = D.EXPERIMENTS / 'typed-ir-microprobe/target'
CARGO = Path('/Users/ericfode/.cargo/bin/cargo')
BINARY = 'compositional-typed-native-collector'
ZERO = dict(native_applies=0, neural_forwards=0, backwards=0, optimizer_updates=0,
            numerical_fits=0, paid_jobs=0, paid_spend_usd=0.)
SECONDS = dict(metadata=5., build=15., native=30., prep=5., fit=120., verify=10.)


def read(path):
    return json.loads(Path(path).read_text())


def prepare():
    S.require(not ROOT.exists(), 'new campaign only; no retries or history reset')
    prior = S.Budget(PRIOR / 'campaign-spec.json'); state = prior.inspect()
    closure = read(PRIOR / 'experiment-closure.json')
    S.require(state['completed'] == prior.spec['stage_order'] and not state['failures']
              and state['pending'] is None and state['cumulative'] == closure['cumulative'],
              'exact closed previous carry required')
    S.require(state['cumulative']['charged_native_applies'] == 295
              and state['cumulative']['charged_seconds'] == 222.92651104100514,
              'no historical charge reset')
    ROOT.mkdir()
    parent = copy.deepcopy(prior.parent)
    parent['carry'] = state['cumulative']
    parent['pins'] += list(prior.frozen.values()) + [S.pin(p) for p in PRIOR.rglob('*') if p.is_file()]
    parent['pins'] = list({p['path']: p for p in parent['pins']}.values())
    parent['closed_journals'].append(D.closed_journal(prior.ledger))
    parent['protected_roots'].append(str(PRIOR))
    pm = D.write_new(ROOT / 'parent-manifest.json', parent)
    py = prior.spec['stages']['verify']['argv'][0]
    stages = {}
    for name, seconds in SECONDS.items():
        counts = dict(ZERO)
        if name == 'native': counts['native_applies'] = 512
        if name == 'fit': counts.update(neural_forwards=3624, backwards=3600,
                                       optimizer_updates=3600, numerical_fits=2)
        out = ROOT / (name + '-1')
        stages[name] = dict(argv=[py, str(Path(__file__).resolve()), 'run', '--stage', name,
                                 '--spec', str(ROOT / 'campaign-spec.json')],
            outputs=[str(out), str(ROOT / (name + '-1-stage-receipt.json'))],
            reservation=dict(seconds=seconds, **counts),
            expected=dict(counts, **({'native_applies': None} if name == 'native' else {})),
            external_counters=['native_applies'] if name == 'native' else [])
    files = list(HERE.glob('compositional_typed*.py')) + list(HERE.glob('test_compositional_typed*.py'))
    files += [HERE / ('compositional_typed_' + name + '.py')
              for name in ('campaign', 'model', 'native_plan', 'data', 'fit', 'verify')]
    files += [HERE / 'COMPOSITIONAL_TYPED_PROTOCOL.md', Path(py), CARGO,
              HERE / 'effect_identifiability_fit.py', HERE / 'whole_card_encoder.py',
              HERE / 'semantic_discrimination_bank.py', HERE / 'public_input_binding_model_v1.py',
              HERE / 'semantic_discrimination_native_collector/supervise_v2.py']
    files += [p for p in CRATE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ENGINE / 'Cargo.toml', ENGINE / 'Cargo.lock']
    files += [p for p in (ENGINE / 'crates/kessel').rglob('*') if p.is_file() and 'target' not in p.parts]
    files += list((ENGINE / 'compiler/generated').rglob('*.json'))
    spec = dict(schema=S.SPEC_SCHEMA, status='sealed-awaiting-root-GO',
        source=S.pin(S.__file__), primitives=S.pin(S._PATH), parent_manifest=pm,
        ledger_path=str(ROOT / 'campaign-ledger.jsonl'),
        caps=dict(seconds=sum(SECONDS.values()), **dict(ZERO, native_applies=512,
            neural_forwards=3624, backwards=3600, optimizer_updates=3600, numerical_fits=2)),
        guard=dict(cpu_workers=1, rss_bytes=1024**3), stage_order=list(stages), stages=stages,
        pins=[S.pin(p) for p in sorted(set(files))], environment=prior.spec['environment'],
        source_freeze_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        financial=closure['financial'], protocol=S.pin(HERE / 'COMPOSITIONAL_TYPED_PROTOCOL.md'),
        scope='One fixed compositional architecture versus matched old graph; elementary synthetic native labels only. No paid work, capacity sweep, deck composition or promotion.')
    D.write_new(ROOT / 'campaign-spec.json', spec)
    S.Budget(ROOT / 'campaign-spec.json').verify()
    return S.pin(ROOT / 'campaign-spec.json')


def process_helpers():
    path = HERE / 'semantic_discrimination_native_collector/supervise_v2.py'
    spec = importlib.util.spec_from_file_location('compositional_owned_helpers', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def native_proof(raw, records):
    """Byte-only paired-call proof; scientific labels are checked independently."""
    before = [r for r in records if r.get('phase') == 'beforeApply']
    after = [r for r in records if r.get('phase') == 'afterApply']
    ends = [r['case'] for r in records if r.get('phase') == 'contextComplete']
    n = raw['applyCalls']
    S.require(records and records[0].get('schema') == 'jepa-compositional-typed-apply-journal/1'
              and all(r.get('phase') in ('beforeApply', 'afterApply', 'contextComplete')
                      for r in records[1:]), 'exact native journal schema and phases required')
    S.require(raw['collectionComplete'] is True and len(raw['cases']) == 128,
              'all frozen native roots must complete')
    S.require(0 < n <= 512 and [r['applyCall'] for r in before] == list(range(1, n + 1))
              and [r['applyCall'] for r in after] == list(range(1, n + 1)), 'bounded fully paired calls')
    S.require([(r['phase'], r['applyCall']) for r in records if r.get('phase') in
              ('beforeApply', 'afterApply', 'applyError')] ==
              [(phase, i) for i in range(1, n + 1) for phase in ('beforeApply', 'afterApply')],
              'native errors or unpaired chronology')
    S.require(ends == raw['cases'] and [c['world_id'] for c in ends] == list(range(128)),
              'case journal and native receipt differ')
    return dict(actual_native_applies=n, completed_roots=128, fully_paired=True,
                label_origin='native menus and observed transitions only')


def subprocess_stage(args, run, receipt):
    """One owned child group; only this owned group may be cleaned up."""
    g = process_helpers(); out = args.out
    if args.stage == 'build':
        command = [str(CARGO), 'build', '--offline', '--locked', '--manifest-path',
                   str(CRATE / 'Cargo.toml'), '--bin', BINARY, '-j', '1']
    else:
        command = [str(ROOT / 'build-1' / BINARY), str(ROOT / 'metadata-1/native-plan.json'),
                   str(out / 'receipt.json'), str(out / 'transitions.jsonl')]
    env = g.build_environment(TARGET)
    proc = None; pgid = None; members = None
    rss, members = g.process_readers()
    receipt.update(child_argv=command, observed_per_pid_peak_bytes={}, sample_count=0)
    try:
        token = run.intent('native_applies', 512) if args.stage == 'native' else None
        with (out / 'stdout.log').open('x') as stdout, (out / 'stderr.log').open('x') as stderr:
            S.require(run.remaining_seconds() > 0, 'stage exhausted before owned launch')
            proc = subprocess.Popen(command, cwd=CRATE, env=env, stdout=stdout, stderr=stderr,
                                    start_new_session=True)
            receipt['cleanup_verified'] = False
            pgid = proc.pid; receipt['owned_pgid'] = pgid
            while True:
                readings = g.read_owned_rss(receipt, members(pgid), rss, os.getpid(),
                                           SECONDS[args.stage] - run.remaining_seconds())
                peak = g.memory_sample(receipt, readings, os.getpid(),
                                      resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                receipt['sample_count'] += 1
                S.require(peak <= 1024**3 and run.remaining_seconds() > 0,
                          'owned child RSS or stage wall limit')
                code = proc.poll()
                if code is not None:
                    S.require(not members(pgid), 'owned descendants remain')
                    receipt['cleanup_verified'] = True
                    proc = None; receipt['exit_code'] = code
                    S.require(code == 0, 'owned child failed: ' + str(code))
                    break
                time.sleep(min(.05, max(.001, run.remaining_seconds())))
        if args.stage == 'build':
            original = TARGET / 'debug' / BINARY; destination = out / BINARY
            with original.open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst); dst.flush(); os.fsync(dst.fileno())
            destination.chmod(original.stat().st_mode & 0o777)
            S.require(S.pin(original)['sha256'] == S.pin(destination)['sha256'], 'binary copy mismatch')
        else:
            raw = read(out / 'receipt.json')
            S.require(raw['collectionPlan'] == read(ROOT / 'metadata-1/native-plan.json'),
                      'actual native plan differs from sealed metadata')
            records = [json.loads(line) for line in (out / 'transitions.jsonl').read_text().splitlines()]
            proof = native_proof(raw, records)
            T = importlib.import_module('compositional_typed_data')
            proof['exact_step_chain'] = T.journal_proof(records, raw)
            S.require(sum(c['applyCalls'] for c in raw['cases']) == proof['actual_native_applies']
                      and all(0 < c['applyCalls'] <= 4 for c in raw['cases']),
                      'native root counts or structural bounds differ')
            p = D.write_new(out / 'native-verification.json', proof)
            run.complete(token, actual=proof['actual_native_applies'],
                         proofs=[S.pin(out / 'transitions.jsonl'), p])
            receipt['native_proof'] = proof
    except BaseException:
        if proc is not None:
            receipt['cleanup_verified'] = g.cleanup_owned(proc, pgid, members, receipt)
        raise
    finally:
        bound = g.final_memory_bound(receipt.get('observed_peak_live_sum_bytes', 0),
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        receipt['conservative_tree_peak_bytes'] = bound
        if bound > 1024**3: raise RuntimeError('final owned tree RSS exceeds 1 GiB')


def stage(args):
    budget = S.Budget(args.spec); args.out = ROOT / (args.stage + '-1')
    receipt_path = ROOT / (args.stage + '-1-stage-receipt.json')
    with budget.lease() as run:
        status = 'failed'; guard = None; created = False
        receipt = dict(stage=args.stage, cleanup_verified=True, source=S.pin(__file__))
        try:
            descriptor = budget.spec['stages'][args.stage]
            actual = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]]
            inputs = list(run.state['proofs'].values())
            run.begin(args.stage, argv=descriptor['argv'], guard=budget.spec['guard'], inputs=inputs)
            S.require(actual == descriptor['argv'] and args.spec.resolve() == ROOT / 'campaign-spec.json',
                      'actual stage command or canonical spec differs')
            args.out.mkdir(); created = True
            if args.stage in ('build', 'native'):
                subprocess_stage(args, run, receipt)
            else:
                E = importlib.import_module('effect_identifiability_fit')
                with E.Guard(run.remaining_seconds()) as guard:
                    if args.stage == 'metadata':
                        P = importlib.import_module('compositional_typed_native_plan')
                        plan = P.prepare_plan()
                        D.write_new(args.out / 'native-plan.json', plan)
                    elif args.stage == 'prep':
                        import numpy as np
                        T = importlib.import_module('compositional_typed_data')
                        plan = read(ROOT / 'metadata-1/native-plan.json')
                        raw = read(ROOT / 'native-1/receipt.json')
                        records = [json.loads(line) for line in (ROOT / 'native-1/transitions.jsonl').read_text().splitlines()]
                        arrays, manifest = T.prepare_data(np, plan, raw, records)
                        np.savez_compressed(args.out / 'dataset.npz', **arrays)
                        D.write_new(args.out / 'manifest.json', manifest)
                    elif args.stage == 'fit':
                        args.plan = ROOT / 'metadata-1/native-plan.json'
                        args.dataset = ROOT / 'prep-1/dataset.npz'
                        args.manifest = ROOT / 'prep-1/manifest.json'
                        F = importlib.import_module('compositional_typed_fit')
                        receipt['result'] = F.worker(args, run)
                    elif args.stage == 'verify':
                        import numpy as np
                        V = importlib.import_module('compositional_typed_verify')
                        receipt['result'] = V.verify(np, ROOT, args.out)
                    else: raise ValueError('unallocated stage')
            status = 'completed'
        except BaseException as error:
            if run.state['pending'] is None: raise
            receipt['error'] = dict(type=type(error).__name__, message=str(error))
        receipt.update(status=status, guard=guard.receipt() if guard else None)
        artifacts = [S.pin(p) for p in sorted(args.out.rglob('*')) if p.is_file()] if created else []
        receipt_pin = None
        try:
            receipt_pin = D.write_new(receipt_path, receipt)
        except BaseException as error:
            status = 'failed'
            receipt['receipt_write_error'] = dict(type=type(error).__name__, message=str(error))
        if receipt['cleanup_verified'] is not True:
            run.pending_failure(receipt.get('error', 'owned cleanup unknown'))
            raise RuntimeError('cleanup unknown; reservation remains pending')
        state = run.finish(status, proofs=artifacts + ([receipt_pin] if receipt_pin else []),
                           cleanup_verified=True, execution_ended=True)
        S.require(args.stage in state['completed'] and status == 'completed',
                  'stage failed; full reservation retained: ' + str(receipt.get('error')))
        return dict(stage=args.stage, status='completed', receipt=receipt_pin,
                    charged=state['charged'], cumulative=state['cumulative'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'initialize', 'status', 'run'])
    p.add_argument('--stage', choices=list(SECONDS)); p.add_argument('--spec', type=Path,
                      default=ROOT / 'campaign-spec.json')
    args = p.parse_args()
    if args.action == 'prepare': result = prepare()
    elif args.action == 'initialize': result = S.Budget(args.spec).initialize(root_go=True)
    elif args.action == 'status': result = S.Budget(args.spec).inspect()
    else: result = stage(args)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__': main()
