"""Source-only real-event build/native worker for a coordinator-sealed stage.

The coordinator owns durable begin/finish and the exclusive output directory.
Importing this module performs no reads, builds, engine calls or ledger writes.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
OWN = HERE.parent
TARGET = HERE.parents[4] / 'experiments/typed-ir-microprobe/target'
CARGO = Path('/Users/ericfode/.cargo/bin/cargo')
HELPERS = OWN / 'semantic_discrimination_native_collector/supervise_v2.py'
HELPERS_SHA = 'f8937de03baa97d63c668b92c462bdcb7341fee331f2e38d4e3e3974ec8b0948'
BINARY = 'real-ir-transfer-native-collector'
MAX_CALLS = 168
N_ROOTS = 56
MAX_BYTES = 1024 ** 3


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    p = Path(path).resolve(); raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def commands(stage, root, plan, out):
    root, plan, out = Path(root), Path(plan), Path(out)
    require(stage in ('build', 'native'), 'build or native stage only')
    if stage == 'build':
        return [str(CARGO), 'build', '--offline', '--locked', '--manifest-path',
                str(HERE / 'Cargo.toml'), '--bin', BINARY, '-j', '1']
    return [str(root / 'build-1' / BINARY), str(plan), str(out / 'receipt.json'),
            str(out / 'transitions.jsonl')]


def process_helpers():
    require(pin(HELPERS)['sha256'] == HELPERS_SHA, 'reviewed process helpers changed')
    spec = importlib.util.spec_from_file_location('real_ir_transfer_process_helpers', HELPERS)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def native_proof(raw, records):
    """Structural/counter proof only; native labels have a separate verifier."""
    require(raw.get('schema') == 'jepa-real-ir-transfer-native/1'
            and raw.get('synthetic') is False and raw.get('collectionComplete') is True,
            'complete real-event receipt required')
    cases = raw.get('cases', [])
    require(len(cases) == N_ROOTS and [c['world_id'] for c in cases] == list(range(N_ROOTS)),
            'all frozen roots in order required')
    require(records and records[0].get('schema') == 'jepa-real-ir-transfer-apply-journal/1'
            and records[0].get('expectedCases') == N_ROOTS
            and records[0].get('maxApplyCalls') == MAX_CALLS
            and records[0].get('planSha256') == raw.get('collectionPlanSha256'),
            'frozen journal header differs')
    require(all(r.get('phase') in ('beforeApply', 'afterApply', 'contextComplete')
                for r in records[1:]), 'unexpected native journal phase or engine error')
    before = [r for r in records if r.get('phase') == 'beforeApply']
    after = [r for r in records if r.get('phase') == 'afterApply']
    ends = [r for r in records if r.get('phase') == 'contextComplete']
    n = raw.get('applyCalls')
    require(type(n) is int and 0 < n <= MAX_CALLS and
            [r['applyCall'] for r in before] == list(range(1, n + 1)) and
            [r['applyCall'] for r in after] == list(range(1, n + 1)),
            'native calls are not bounded and fully paired')
    require([(r['phase'], r['applyCall']) for r in records if r.get('phase') in ('beforeApply', 'afterApply')] ==
            [(phase, i) for i in range(1, n + 1) for phase in ('beforeApply', 'afterApply')],
            'native call chronology differs')
    require([r['case'] for r in ends] == cases, 'journal/receipt root disagreement')
    cursor = 1; last_call = 0
    for case, end in zip(cases, ends):
        context = 'world-' + str(case['world_id']) + '-' + case['card']
        steps = case['steps']; count = case['applyCalls']
        require(type(count) is int and 0 < count <= 3 and count == len(steps),
                'per-root three-call bound or step count differs')
        require(case.get('engineError') is None, 'native engine error is not an admitted root')
        settled = case.get('completion') == 'settled'
        prompt_only = case.get('completion') == 'unoffered-observation-only'
        require((settled and case.get('intentResolution') in ('committed', 'unoffered-declined')
                 and case.get('final', {}).get('settled') is True)
                or (prompt_only and case.get('intentOffered') is False
                    and case.get('final') is None and case.get('targetPrompt') is not None),
                'unsettled or unsupported terminal root')
        previous = case['before']
        for step in steps:
            require(cursor + 1 < len(records), 'truncated native step chain')
            b, a = records[cursor:cursor + 2]
            require(b.get('phase') == 'beforeApply' and a.get('phase') == 'afterApply'
                    and b['context'] == context == a['context']
                    and b['branch'] == step['stage'] == a['branch']
                    and b['before'] == previous == step['before']
                    and b['offeredAction'] == step['action']
                    and step['action'] in b['before']['offeredActions']
                    and a['after'] == step['after'], 'native offered-action/state chain differs')
            previous = step['after']; last_call = a['applyCall']; cursor += 2
        require(records[cursor] == end and end['context'] == context
                and end['applyCalls'] == last_call
                and case['lastObserved'] == previous
                and (not settled or case['final'] == previous), 'root terminal chain differs')
        cursor += 1
    require(cursor == len(records) and sum(c['applyCalls'] for c in cases) == n,
            'unaccounted journal records')
    return dict(actual_native_applies=n, completed_roots=N_ROOTS, fully_paired=True,
                exact_step_chains=True, label_origin='native menus and observed transitions only')


def worker(args, run, receipt):
    """Called only after coordinator durable begin; never initializes a ledger."""
    require(args.stage in ('build', 'native'), 'unallocated worker stage')
    require(Path(args.out).is_dir() and not any(Path(args.out).iterdir()),
            'coordinator must create a new empty declared output directory')
    require(isinstance(run.state.get('pending'), dict)
            and run.state['pending'].get('stage') == args.stage,
            'durable coordinator stage reservation required before strict inputs')
    g = process_helpers(); out = Path(args.out); root = Path(args.root)
    command = commands(args.stage, root, args.plan, out)
    env = g.build_environment(TARGET)
    rss, members = g.process_readers(); proc = None; pgid = None
    receipt.update(child_argv=command, cleanup_verified=True,
                   observed_per_pid_peak_bytes={}, sample_count=0)
    try:
        token = run.intent('native_applies', MAX_CALLS) if args.stage == 'native' else None
        with (out / 'stdout.log').open('x') as stdout, (out / 'stderr.log').open('x') as stderr:
            require(run.remaining_seconds() > 0, 'stage exhausted before owned launch')
            proc = subprocess.Popen(command, cwd=HERE, env=env, stdout=stdout, stderr=stderr,
                                    start_new_session=True)
            pgid = proc.pid; receipt.update(owned_pgid=pgid, cleanup_verified=False)
            started = time.monotonic()
            while True:
                readings = g.read_owned_rss(receipt, members(pgid), rss, os.getpid(), time.monotonic() - started)
                peak = g.memory_sample(receipt, readings, os.getpid(),
                                      resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                receipt['sample_count'] += 1
                require(peak <= MAX_BYTES and run.remaining_seconds() > 0,
                        'owned child RSS or stage wall limit')
                code = proc.poll()
                if code is not None:
                    require(not members(pgid), 'owned descendants remain')
                    receipt.update(cleanup_verified=True, exit_code=code); proc = None
                    require(code == 0, 'owned child failed: ' + str(code)); break
                time.sleep(min(.05, max(.001, run.remaining_seconds())))
        if args.stage == 'build':
            original = TARGET / 'debug' / BINARY; destination = out / BINARY
            with original.open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst); dst.flush(); os.fsync(dst.fileno())
            destination.chmod(original.stat().st_mode & 0o777)
            require(pin(original)['sha256'] == pin(destination)['sha256'], 'binary copy mismatch')
            receipt['campaign_binary'] = pin(destination)
        else:
            raw = json.loads((out / 'receipt.json').read_text())
            require(raw['collectionPlan'] == json.loads(Path(args.plan).read_text()),
                    'actual native plan differs from sealed metadata')
            records = [json.loads(line) for line in (out / 'transitions.jsonl').read_text().splitlines()]
            proof = native_proof(raw, records)
            path = out / 'native-verification.json'
            with path.open('x') as stream:
                json.dump(proof, stream, sort_keys=True, allow_nan=False); stream.write('\n')
                stream.flush(); os.fsync(stream.fileno())
            run.complete(token, actual=proof['actual_native_applies'],
                         proofs=[pin(out / 'transitions.jsonl'), pin(path)])
            receipt['native_proof'] = proof
        return receipt
    except BaseException:
        if proc is not None:
            receipt['cleanup_verified'] = g.cleanup_owned(proc, pgid, members, receipt)
        raise
    finally:
        bound = g.final_memory_bound(receipt.get('observed_peak_live_sum_bytes', 0),
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        receipt['conservative_tree_peak_bytes'] = bound
        require(bound <= MAX_BYTES, 'final owned tree RSS exceeds 1 GiB')
