"""New sealed-budget build/native bridge; source preparation only by default.

The old supervisor supplies byte-pinned process/RSS/cleanup helpers. The new
native proof functions retain its checks with explicit eight-root/32-call schema.
No historical ledger or source is changed, initialized or credited here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
OWN = HERE.parent
ROOT = HERE.parents[4] / 'experiments/ability-correction-v1'
TARGET = HERE.parents[4] / 'experiments/typed-ir-microprobe/target'
PRIOR = OWN / 'semantic_discrimination_native_collector/supervise_v2.py'
PRIOR_SHA = 'f8937de03baa97d63c668b92c462bdcb7341fee331f2e38d4e3e3974ec8b0948'
CORE = OWN / 'sealed_budget.py'
CORE_SHA = 'a49c6dcf821fc48f3104d8d2bd54e00f2a451a9f0e987c4a844afcad303e6352'
ENGINE = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source')
CARGO = Path('/Users/ericfode/.cargo/bin/cargo')
BINARY = 'ability-correction-native-collector'
LIMITS = dict(build=10., native=15.)
MAX_BYTES = 1024 ** 3
INTERVAL = .05


def pin(path):
    p = Path(path).resolve(); raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def load(path, name, expected=None):
    if expected is not None and pin(path)['sha256'] != expected:
        raise ValueError('reviewed helper source changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = load(PRIOR, 'ability_native_process_helpers', PRIOR_SHA)
P = load(HERE / 'native_proof.py', 'ability_native_proof')


def descriptors(root, python):
    root = Path(root).resolve(); python = str(Path(python).absolute())
    common = ['--spec', str(root / 'campaign-spec.json'), '--manifest', str(root / 'metadata-1/native-source-manifest.json')]
    return {stage: dict(argv=[python, str(HERE / 'supervise.py'), '--stage', stage, *common, '--out', str(root / ('build-1' if stage == 'build' else 'native-attempt-1')), '--execute'],
        outputs=[str(root / ('build-1' if stage == 'build' else 'native-attempt-1'))]) for stage in LIMITS}


def child_command(stage, root):
    root = Path(root).resolve()
    if stage == 'build':
        return [str(CARGO), 'build', '--offline', '--locked', '--manifest-path', str(HERE / 'Cargo.toml'), '--bin', BINARY, '-j', '1']
    return [str(root / 'build-1' / BINARY), str(root / 'native-attempt-1/native-receipt.json')]


def write_source_manifest(plan_path, out_path, campaign_root, source_freeze_commit):
    """Metadata-stage byte pins only; never builds, snapshots or applies."""
    root = Path(campaign_root).resolve(); plan_path = Path(plan_path).resolve(strict=True); out = Path(out_path).resolve()
    if plan_path != root / 'native-plan.json' or out != root / 'metadata-1/native-source-manifest.json' or out.exists():
        raise ValueError('exclusive declared metadata outputs required')
    if len(source_freeze_commit) != 40 or any(c not in '0123456789abcdef' for c in source_freeze_commit):
        raise ValueError('coordinator source-freeze commit required')
    if pin(CORE)['sha256'] != CORE_SHA:
        raise ValueError('frozen sealed-budget source changed')
    plan = json.loads(plan_path.read_text())
    if plan['schema'] != 'jepa-ability-correction-plan/1' or len(plan['worlds']) != 8 or [w['id'] for w in plan['worlds']] != list(range(8)) or plan['collector_max_engine_applies'] != 32:
        raise ValueError('exact eight-root/32-call frozen plan required')
    if any(w['source_code'] != 'IBH_104' or w['max_applies'] != 4 or w['selection_mode'] != 'exactly-one-upTo' for w in plan['worlds']):
        raise ValueError('source/selection/per-world cap changed')
    projects = [HERE / name for name in ('Cargo.toml', 'Cargo.lock', 'src/main.rs', 'supervise.py', 'native_proof.py', 'test_guard.py', 'README.md', 'fixtures/whole-rows.json')]
    projects += [OWN / name for name in ('ability_correction_native_plan.py', 'test_ability_correction_native_plan.py', 'sealed_budget.py')]
    projects += [PRIOR, OWN / 'semantic_discrimination_accounting.py']
    engine = [ENGINE / 'Cargo.toml', ENGINE / 'Cargo.lock']
    engine += [p for p in (ENGINE / 'crates/kessel').rglob('*') if p.is_file() and 'target' not in p.parts]
    engine += list((ENGINE / 'compiler/generated').rglob('*.json'))
    preserved = [pin(TARGET / 'debug' / name) for name in ('binding-transfer-native-collector', 'binding-transfer-fixture-validator', 'semantic-discrimination-native-collector')]
    G.verify_preserved_binaries(dict(preserved_binaries=preserved[:2]))
    manifest = dict(schema='jepa-ability-correction-native-source/1', source_commit=source_freeze_commit,
        collection_plan=pin(plan_path), project_files=[pin(p) for p in projects],
        pinned_execution_inputs=[pin(p) for p in sorted(set(engine + [plan_path, CARGO]))],
        accounting=pin(CORE), inherited_process_helpers=pin(PRIOR),
        cargo_target_dir=str(TARGET), cargo_executable=str(CARGO), preserved_binaries=preserved,
        expected_cases=8, collector_max_engine_applies=32, max_applies_per_root=4,
        build_seconds=10, native_seconds=15, sampled_rss_bytes=MAX_BYTES,
        physical_shields=0, source_program_previously_exposed=True, source_program_transfer_claim=False,
        mutable_cache_scope='Existing Cargo warm target is build cache only; unique new binary is copied into the declared build output and that immutable copy is executed.',
        no_retries=True, root_go_required=True, native_applies=0, neural_forwards=0, optimizer_updates=0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    return dict(manifest=pin(out), plan=pin(plan_path))


def preflight(path):
    manifest = json.loads(Path(path).read_text())
    if pin(CORE)['sha256'] != CORE_SHA or manifest['schema'] != 'jepa-ability-correction-native-source/1' or manifest['accounting'] != pin(CORE) or manifest['inherited_process_helpers'] != pin(PRIOR):
        raise ValueError('frozen source/accounting manifest changed')
    for item in manifest['project_files'] + manifest['pinned_execution_inputs'] + manifest['preserved_binaries']:
        if pin(item['path']) != item:
            raise ValueError('pinned source/input/history changed: ' + item['path'])
    return manifest


def verify_native(raw, manifest, journal):
    summary = dict(frozen_plan=G.verify_frozen_plan(raw, manifest), journal=P.verify_success_journal(journal, raw),
        actual_chains=P.verify_complete_cases(raw, manifest, journal), no_physical_shields=G.verify_no_physical_shields(raw),
        public_privacy=G.verify_fixture_privacy(raw))
    exposure = P.trace_exposure(journal, True)
    if not exposure['verified'] or exposure['known_calls'] != raw['applyCalls'] or not 0 < exposure['known_calls'] <= 32:
        raise ValueError('durable native counter differs from complete receipt')
    summary.update(actual_native_applies=exposure['known_calls'], schema='jepa-ability-correction-native-verification/1',
        complete_roots=8, all_future_knowledge_from_native_snapshots=True, no_new_program_transfer_claim=True)
    return summary


def cleanup_and_close(run, receipt, proofs, cleanup_verified):
    """Unknown cleanup keeps the reservation pending; never closes as success."""
    if not cleanup_verified:
        result = run.pending_failure(receipt.get('error', 'owned cleanup not proven'))
        receipt.update(status='pending-failure', accounting=result, status_source='sealed-budget-ledger')
        return result
    result = run.finish(receipt['status'], proofs=proofs, cleanup_verified=True, execution_ended=True)
    receipt['accounting'] = result
    receipt['status'] = 'completed' if receipt['stage'] in result['completed'] and not result['failures'] else 'failed'
    receipt['status_source'] = 'sealed-budget-ledger'
    receipt['ledger_final_sha256'] = result.get('last_sha256')
    return result


def validate_stage_contract(descriptor, guard, stage):
    reserve = descriptor['reservation']
    if reserve['seconds'] != LIMITS[stage] or guard['rss_bytes'] != MAX_BYTES or guard['cpu_workers'] != 1:
        raise ValueError('frozen native stage guard differs')
    for key, value in reserve.items():
        if key not in ('seconds', 'native_applies') and value != 0:
            raise ValueError('native supervisor cannot reserve neural/optimizer/fit/paid work')
    if stage == 'native':
        if reserve['native_applies'] != 32 or descriptor['external_counters'] != ['native_applies'] or descriptor['expected']['native_applies'] is not None:
            raise ValueError('native stage requires explicit external capped32/observed-unknown contract')
    elif reserve['native_applies'] != 0 or descriptor['external_counters'] or descriptor['expected']['native_applies'] != 0:
        raise ValueError('build stage cannot reserve native calls')
    if any(value != 0 for key, value in descriptor['expected'].items() if key != 'native_applies'):
        raise ValueError('native supervisor expects zero neural/optimizer/fit/paid work')


def provisional_receipt(out, receipt, proofs):
    """Metered, immutable execution evidence; final status belongs to the ledger."""
    path = Path(out) / 'supervisor-receipt.json'
    snapshot = dict(receipt, status='provisional-awaiting-accounting', execution_status=receipt['status'],
        status_source='sealed-budget-ledger-after-this-proof', final_accounting_status=None)
    with path.open('x') as stream:
        json.dump(snapshot, stream, indent=2, allow_nan=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    item = pin(path); proofs.append(item)
    receipt['provisional_receipt'] = item
    return item


def run(args):
    root = args.spec.resolve().parent
    if not args.execute:
        if args.out.resolve() != root / ('build-1' if args.stage == 'build' else 'native-attempt-1') or args.manifest.resolve() != root / 'metadata-1/native-source-manifest.json':
            raise ValueError('fixed NEW output/metadata paths required')
        return dict(stage=args.stage, child_argv=child_command(args.stage, root), outputs=[str(args.out.resolve())],
            native_reservation=32 if args.stage == 'native' else 0, max_seconds=LIMITS[args.stage],
            execute=False, ledger_initialized=False, scope='preview only; no manifest generation, build, engine, ledger or model call')
    A = load(CORE, 'ability_native_sealed_budget', CORE_SHA)
    budget = A.Budget(args.spec)
    with budget.lease() as session:
        descriptor = budget.spec['stages'][args.stage]
        expected = descriptor['argv']
        allowed = dict(budget.frozen, **session.state['proofs'])
        needed = [root / 'metadata-1/native-source-manifest.json', root / 'native-plan.json']
        if args.stage == 'native':
            needed.append(root / 'build-1' / BINARY)
        # Derive only sealed metadata before begin. Missing inputs and all actual
        # invocation/guard/pin checks fail inside the durable reservation.
        inputs = [allowed[str(path)] for path in needed if str(path) in allowed]
        proc = None; pgid = None; members = None; launched = False; cleanup_verified = True; created = False; proofs = []
        receipt = dict(schema='jepa-ability-correction-native-supervisor/1', stage=args.stage, status='started',
            observed_per_pid_peak_bytes={}, sample_count=0, exited_owned_pid_skips=[],
            actual_wrapper_argv=[str(Path(sys.executable).absolute()), str(Path(__file__).resolve()), *sys.argv[1:]])
        try:
            session.begin(args.stage, argv=expected, guard=budget.spec['guard'], inputs=inputs)
            if Path(expected[0]).resolve() != Path(sys.executable).resolve() or Path(expected[1]).resolve() != Path(__file__).resolve() or expected[2:] != sys.argv[1:]:
                raise ValueError('actual wrapper invocation differs from frozen stage descriptor')
            validate_stage_contract(descriptor, budget.spec['guard'], args.stage)
            if args.out.resolve() != root / ('build-1' if args.stage == 'build' else 'native-attempt-1') or args.manifest.resolve() != root / 'metadata-1/native-source-manifest.json':
                raise ValueError('fixed NEW output/metadata paths required')
            if any(str(path) not in allowed for path in needed):
                raise ValueError('completed metadata/build must pin plan/manifest/unique campaign binary')
            manifest = preflight(args.manifest)
            env = G.build_environment(TARGET)
            if args.out.exists():
                raise FileExistsError('preserve prior attempt; no retry')
            args.out.mkdir(parents=True); created = True
            rss, members = G.process_readers(); rss(os.getpid())
            command = child_command(args.stage, root)
            receipt.update(child_argv=command, wrapper_argv=expected, owned_launch_identity='token=' + uuid.uuid4().hex)
            env['ABILITY_CORRECTION_PLAN'] = manifest['collection_plan']['path']
            env['ABILITY_CORRECTION_NATIVE_TRACE'] = str(args.out / 'native-transitions.jsonl')
            if session.remaining_seconds() <= 0:
                raise TimeoutError('native stage exhausted before child launch')
            token = session.intent('native_applies', 32) if args.stage == 'native' else None
            with (args.out / 'stdout.log').open('x') as stdout, (args.out / 'stderr.log').open('x') as stderr:
                try:
                    proc = subprocess.Popen(command, cwd=HERE, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
                except OSError:
                    raise
                except BaseException:
                    cleanup_verified = False
                    raise
                launched = args.stage == 'native'; pgid = proc.pid
                receipt['owned_pgid'] = pgid
                while True:
                    readings = G.read_owned_rss(receipt, members(pgid), rss, os.getpid(), LIMITS[args.stage] - session.remaining_seconds())
                    peak = G.memory_sample(receipt, readings, os.getpid(), resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    receipt['sample_count'] += 1
                    if peak > MAX_BYTES or session.remaining_seconds() <= 0:
                        raise RuntimeError('owned RSS or stage wall threshold')
                    code = proc.poll()
                    if code is not None:
                        receipt['exit_code'] = code
                        if members(pgid):
                            raise RuntimeError('owned descendants remain after leader exit')
                        proc = None
                        if code:
                            raise RuntimeError('owned child failed: ' + str(code))
                        break
                    time.sleep(min(INTERVAL, max(.001, session.remaining_seconds())))
            if args.stage == 'build':
                target = TARGET / 'debug' / BINARY
                destination = args.out / BINARY
                with target.open('rb') as source, destination.open('xb') as output:
                    shutil.copyfileobj(source, output)
                    output.flush(); os.fsync(output.fileno())
                destination.chmod(target.stat().st_mode & 0o777)
                if pin(target)['sha256'] != pin(destination)['sha256']:
                    raise ValueError('campaign binary byte copy differs')
                proofs.append(pin(destination))
            else:
                raw = json.loads((args.out / 'native-receipt.json').read_text())
                summary = verify_native(raw, manifest, args.out / 'native-transitions.jsonl')
                verification = args.out / 'native-verification.json'
                with verification.open('x') as stream:
                    json.dump(summary, stream, sort_keys=True, indent=2); stream.write('\n')
                    stream.flush(); os.fsync(stream.fileno())
                proofs.extend([pin(args.out / 'native-receipt.json'), pin(args.out / 'native-transitions.jsonl'), pin(verification)])
                session.complete(token, actual=summary['actual_native_applies'], proofs=[pin(args.out / 'native-transitions.jsonl'), pin(verification)])
                receipt['observed_native_applies'] = summary['actual_native_applies']
            preflight(args.manifest)
            receipt['status'] = 'completed'
        except BaseException as error:
            receipt.update(status='failed', error=type(error).__name__ + ': ' + str(error))
            if proc is not None:
                cleanup_verified = G.cleanup_owned(proc, pgid, members, receipt)
        finally:
            parent = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            child = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            bound = G.final_memory_bound(receipt.get('observed_peak_live_sum_bytes', 0), parent, child)
            receipt.update(supervisor_maxrss_bytes=parent, max_single_child_rusage_peak_bytes=child,
                observed_conservative_peak_sum_bytes=bound, cleanup_verified=cleanup_verified,
                memory_scope='50ms live owned RSS samples plus parent and max-single-child rusage; no hard OS process-tree reservation or core-affinity claim')
            if bound > MAX_BYTES:
                receipt.update(status='failed', error='final supervisor plus single child RSS threshold')
            if created:
                for name in ('stdout.log', 'stderr.log', 'native-transitions.jsonl'):
                    path = args.out / name
                    if path.exists() and not any(p['path'] == str(path.resolve()) for p in proofs):
                        proofs.append(pin(path))
                if args.stage == 'native':
                    receipt['durable_prefix'] = P.trace_exposure(args.out / 'native-transitions.jsonl', launched)
            if session.state['pending'] is not None:
                if created:
                    try:
                        provisional_receipt(args.out, receipt, proofs)
                    except BaseException as error:
                        receipt.update(status='failed', error='provisional receipt: ' + type(error).__name__ + ': ' + str(error))
                cleanup_and_close(session, receipt, proofs, cleanup_verified)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=tuple(LIMITS), required=True)
    parser.add_argument('--spec', type=Path, default=ROOT / 'campaign-spec.json')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'metadata-1/native-source-manifest.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(); receipt = run(args)
    print(json.dumps({k: receipt.get(k) for k in ('stage', 'status', 'status_source', 'ledger_final_sha256', 'provisional_receipt', 'execute', 'child_argv', 'observed_native_applies', 'error')}, indent=2))
    if args.execute and receipt['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
