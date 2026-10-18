"""Collect-only owned-process guard; no fit/evaluate/credit entry points.

Pure default preflight. Native build plus every collection attempt share90active
seconds,256Engine applies,1GiB sampledRSS and zero optimizer updates.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
MAX_SECONDS=90.
MAX_APPLIES=256
MAX_UPDATES=0
MAX_BYTES=1024**3
INTERVAL=.05

ACCOUNTING_PATH=HERE.parents[4]/"experiments/effect-identifiability-v2/accounting.py"
ACCOUNTING_SHA256="a72d3ccc9bb381ba626032481d1bbb980236e302a6d532b0960e11445df8e0f9"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def accounting():
    if sha(ACCOUNTING_PATH)!=ACCOUNTING_SHA256:
        raise RuntimeError("shared accounting source changed")
    spec=importlib.util.spec_from_file_location("effect_native_shared_accounting",ACCOUNTING_PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class CampaignLedger:
    """Hash-chained shared lease, held before preflight until final cleanup."""
    def __init__(self,path):
        self.path=Path(path).resolve()
        self.accounting=accounting()

    def __enter__(self):
        self._lease=self.accounting.lease(self.path)
        self.stream,self.rows,self.current=self._lease.__enter__()
        self.entered=time.monotonic()
        self.totals=dict(active_seconds=self.current["phase_seconds"]["native"],
                         engine_apply_attempts=self.current["native_applies"],updates=self.current["optimizer_updates"])
        return self

    def start(self,stage,reserved_applies,reserved_updates,metadata):
        if stage!="collect" or reserved_updates:
            raise ValueError("native collect-only reservation required")
        self.remaining_seconds=min(MAX_SECONDS-self.current["phase_seconds"]["native"],
                                   self.accounting.CAPS["active_seconds"]-self.current["active_seconds"])
        self.started=self.entered
        self.attempt=self.current["attempts"]+1
        reservation=dict(phase="native",active_seconds=self.remaining_seconds,native_applies=reserved_applies,
                         optimizer_updates=0,training_forwards=0,evaluation_forwards=0,export_forwards=0)
        self.current=self.accounting.append(self.stream,self.rows,self.path,"attempt-start",
                                           dict(attempt=self.attempt,reservation=reservation,metadata=metadata))

    def finish(self,applies,updates,status,journal_verified):
        if updates:raise ValueError("native stage cannot update a model")
        self.current=self.accounting.append(self.stream,self.rows,self.path,"attempt-finish",
            dict(attempt=self.attempt,status=status,active_seconds=time.monotonic()-self.started,native_applies=applies,
                 native_journal_verified=journal_verified,observed_optimizer_updates=0,
                 training_forwards=0,evaluation_forwards=0,export_forwards=0))

    def __exit__(self,*exc):
        return self._lease.__exit__(*exc)


def count_applies(path):
    """Count durable before-apply intent records, including failed engine calls."""
    if not Path(path).exists():
        return 0
    calls = []
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        if row.get('phase') == 'beforeApply':
            calls.append(row['applyCall'])
    if calls != list(range(1, len(calls) + 1)):
        raise RuntimeError('nonsequential durable apply journal')
    return len(calls)


def journal_debit(path,collector_started,reservation):
    """Absence is zero-native proof only when the collector never launched."""
    try:
        if Path(path).exists():return count_applies(path),True
        return (reservation,False) if collector_started else (0,True)
    except Exception:
        return reservation,False


def memory_sample(receipt, readings, supervisor_pid, supervisor_peak):
    """Peak of concurrent live RSS sums; past PID peaks are metadata only."""
    if supervisor_pid not in readings or any(type(v) is not int or v < 0 for v in readings.values()):
        raise RuntimeError('live owned RSS reading unavailable/invalid')
    for pid, value in readings.items():
        key = str(pid)
        receipt['observed_per_pid_peak_bytes'][key] = max(value, receipt['observed_per_pid_peak_bytes'].get(key, 0))
    key = str(supervisor_pid)
    receipt['observed_per_pid_peak_bytes'][key] = max(supervisor_peak, receipt['observed_per_pid_peak_bytes'].get(key, 0))
    live_sum = sum(readings.values())
    receipt['observed_live_sum_bytes'] = live_sum
    peak = max(live_sum, receipt.get('observed_peak_live_sum_bytes', 0))
    receipt['observed_peak_live_sum_bytes'] = peak
    receipt['observed_conservative_peak_sum_bytes'] = peak
    return peak


def final_memory_bound(peak_live_sum, supervisor_peak, max_single_child_peak):
    """Rusage supplements sampling; never sum sequential historical child peaks."""
    return max(peak_live_sum, supervisor_peak + max_single_child_peak)


def read_owned_rss(receipt,pids,rss,supervisor_pid,elapsed_seconds):
    """Only confirmed vanished owned PIDs may be skipped, with receipt evidence."""
    readings={supervisor_pid:rss(supervisor_pid)}
    for pid in pids:
        try:
            readings[pid]=rss(pid)
        except OSError as exc:
            if exc.errno!=3:raise
            receipt.setdefault('exited_owned_pid_skips',[]).append(dict(pid=pid,errno=exc.errno,
                error=str(exc),elapsed_seconds=elapsed_seconds))
    return readings


def preflight():
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    for item in manifest['pinned_execution_inputs']:
        if sha(item['path']) != item['sha256']:
            raise RuntimeError('pinned source mismatch: ' + item['path'])
    for item in manifest['project_files']:
        if sha(HERE / item['path']) != item['sha256']:
            raise RuntimeError('collector source mismatch: ' + item['path'])
    return manifest

def process_readers():
    if sys.platform != 'darwin':
        raise RuntimeError('verified macOS owned-group RSS guard required')
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listpids.restype = ctypes.c_int
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int

    def rss(pid):
        buf = ctypes.create_string_buffer(96)
        got = lib.proc_pidinfo(pid, 4, 0, buf, 96)
        if got != 96:
            raise OSError(ctypes.get_errno(), f'owned PID {pid} RSS unavailable ({got})')
        return ctypes.c_uint64.from_buffer(buf, 8).value

    def members(pgid):
        buf = (ctypes.c_int * 4096)()
        count = lib.proc_listpids(2, pgid, buf, ctypes.sizeof(buf))
        if count < 0 or count % 4 or count >= ctypes.sizeof(buf):
            raise RuntimeError('owned group inventory unavailable/truncated')
        return sorted((pid for pid in buf[:count // 4] if pid > 0))
    return (rss, members)


def build_environment(target_dir):
    """Restore the prior cached dev profile; one Cargo/jobserver build worker."""
    env=os.environ.copy()
    allowed={
        'RUSTFLAGS': ('',), 'CARGO_ENCODED_RUSTFLAGS': ('',),
        'CARGO_PROFILE_DEV_CODEGEN_UNITS': ('',),
        'CARGO_PROFILE_DEV_DEBUG': ('', '0'),
        'CARGO_PROFILE_DEV_INCREMENTAL': ('', 'false', '0'),
        'CARGO_INCREMENTAL': ('', '0', 'false'),
        'CARGO_PROFILE_DEV_OPT_LEVEL': ('', '0'),
        'CARGO_PROFILE_DEV_DEBUG_ASSERTIONS': ('', 'true'),
        'CARGO_PROFILE_DEV_OVERFLOW_CHECKS': ('', 'true'),
        'CARGO_PROFILE_DEV_PANIC': ('', 'unwind'),
    }
    for key,values in allowed.items():
        if key in env and env[key] not in values:
            raise ValueError('unfrozen compiler profile override: '+key)
    # Absence restores the saved nonincremental default and rustflags[] fingerprint.
    # The cached rlib contains16 codegen objects;256 would be an inaccurate claim.
    # No unrelated nonempty flag is removed: the whitelist above rejects it.
    for key in ('CARGO_PROFILE_DEV_CODEGEN_UNITS','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS'):
        env.pop(key,None)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        env[key]='1'
    env.update(CARGO_BUILD_JOBS='1', CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_DEV_INCREMENTAL='false',
               CARGO_TARGET_DIR=str(target_dir),CARGO_NET_OFFLINE='true')
    return env


def _run_leased(args,ledger):
    if args.stage != 'collect':
        raise ValueError('this guard authorizes collection only')
    manifest = preflight()
    if args.ledger.resolve() != Path(manifest['campaign_ledger']).resolve():
        raise ValueError('this allocation uses one fixed campaign ledger; quota paths cannot reset')
    if args.target_dir.resolve() != Path(manifest['cargo_target_dir']).resolve():
        raise ValueError('use the pinned writable task7 Cargo target cache')
    commands = []
    env = build_environment(args.target_dir)
    commands = [('build', ['cargo', 'build', '--offline', '--locked', '--manifest-path', str(HERE / 'Cargo.toml'), '--bin', 'native-effect-v2-collector', '-j', '1']), ('collect', [str(args.target_dir / 'debug/native-effect-v2-collector'), str(args.out / 'native-receipt.json')])]
    env['NATIVE_EFFECT_V2_NATIVE_TRACE'] = str(args.out / 'native-transitions.jsonl')
    env['NATIVE_EFFECT_V2_COLLECTION_PLAN'] = str(HERE / 'collection-plan.json')
    reserve_applies, reserve_updates = (manifest['collector_max_engine_applies'], 0)
    preview = dict(phase='native', stage=args.stage, commands=commands, source_manifest_sha256=sha(HERE / 'source-manifest.json'), campaign_ledger=str(args.ledger), max_active_seconds=MAX_SECONDS, max_engine_apply_attempts=MAX_APPLIES, max_updates=MAX_UPDATES, reserved_engine_applies=reserve_applies, reserved_updates=reserve_updates, max_sampled_bytes=MAX_BYTES, sample_interval_seconds=INTERVAL, scope='one fresh owned process group at a time, supervisor plus owned members only; no unrelated process signals')
    preview['build_profile']=dict(opt_level=0,debug=0,incremental=False,codegen_units='prior cached default (unset;16 archived codegen objects)',rustflags=[],cargo_build_workers=1,os_single_core_affinity=False,semantic_features_changed=False)
    preview['prior_campaign_debits'] = ledger.totals
    preview['shared_accounting_sha256']=ACCOUNTING_SHA256
    preview['shared_campaign_state']=ledger.current
    preview['remaining_active_seconds'] = max(0.0, MAX_SECONDS-preview['prior_campaign_debits']['active_seconds'])
    if not args.execute:
        print(json.dumps(preview, indent=2))
        return preview
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = {**preview, 'status': 'started', 'phases': [], 'observed_per_pid_peak_bytes': {}, 'sample_count': 0}
    receipt_path = args.out / 'supervisor-receipt.json'
    proc = None
    ledger.start(args.stage, reserve_applies, reserve_updates, preview)

    def update():
        receipt['attempt_active_seconds'] = time.monotonic() - ledger.started
        receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')

    def sample(pgid):
        own = members(pgid)
        readings=read_owned_rss(receipt,own,rss,os.getpid(),time.monotonic()-ledger.started)
        parent_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        conservative = memory_sample(receipt, readings, os.getpid(), parent_peak)
        receipt['sample_count'] += 1
        if conservative > MAX_BYTES:
            raise RuntimeError('1GiB sampled concurrent live owned-process RSS sum threshold')
        if time.monotonic() - ledger.started >= ledger.remaining_seconds:
            raise RuntimeError('90-second cumulative active wall quota exhausted')
    try:
        update()
        rss, members = process_readers()
        rss(os.getpid())
        for name, command in commands:
            if time.monotonic() - ledger.started >= ledger.remaining_seconds:
                raise RuntimeError('no campaign wall quota remains')
            phase = dict(name=name, command=command)
            receipt['phases'].append(phase)
            update()
            with (args.out / (name + '.stdout.log')).open('x') as out, (args.out / (name + '.stderr.log')).open('x') as err:
                proc = subprocess.Popen(command, cwd=HERE, env=env, stdout=out, stderr=err, start_new_session=True)
                phase['owned_pgid'] = proc.pid
                while True:
                    sample(proc.pid)
                    code = proc.poll()
                    if code is not None:
                        phase['exit_code'] = code
                        if members(proc.pid):
                            raise RuntimeError('owned descendants remained after group leader exit')
                        if code:
                            raise RuntimeError(f'{name} exited {code}')
                        proc = None
                        break
                    time.sleep(min(INTERVAL, max(0.001, ledger.remaining_seconds - (time.monotonic() - ledger.started))))
            update()
        native = json.loads((args.out / 'native-receipt.json').read_text())
        calls = count_applies(args.out / 'native-transitions.jsonl')
        if native['applyCalls'] != calls or calls > reserve_applies or len(native['cases']) != manifest['expected_cases']:
            raise RuntimeError('native journal/receipt quota mismatch')
        receipt.update(engine_apply_attempts=calls, native_receipt_sha256=sha(args.out / 'native-receipt.json'))
        receipt['status'] = 'completed'
    except BaseException as exc:
        receipt.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=2)
    finally:
        parent_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        child_peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        receipt.update(supervisor_maxrss_bytes=parent_peak, children_maxrss_bytes=child_peak)
        final_bound = final_memory_bound(receipt.get('observed_peak_live_sum_bytes', 0), parent_peak, child_peak)
        receipt['observed_conservative_peak_sum_bytes'] = final_bound
        receipt['memory_accounting'] = 'max(sampled concurrent live owned RSS sum including supervisor, supervisor rusage peak + max single child rusage peak); historical per-PID peaks are metadata only'
        if final_bound > MAX_BYTES:
            receipt.update(status='failed', error='final owned supervisor/child rusage RSS threshold exceeded')
        journal=args.out / 'native-transitions.jsonl'
        collector_started=any(p['name']=='collect' for p in receipt['phases'])
        applies,journal_verified=journal_debit(journal,collector_started,reserve_applies)
        if not journal_verified:
            receipt['apply_accounting'] = 'malformed interrupted journal; entire reservation charged'
        updates = 0
        if time.monotonic()-ledger.started>ledger.remaining_seconds:
            receipt.update(status='failed',error='cumulative native/shared active wall quota exceeded')
        ledger.finish(applies, updates, receipt['status'],journal_verified)
        receipt.update(elapsed_seconds=time.monotonic()-ledger.started, native_applies=applies, optimizer_updates=updates, neural_forwards=0, engine_apply_attempts=applies, completed_or_reserved_updates=updates, prior_campaign_debits=ledger.totals, guard_limitation='Live owned-process RSS is sampled; rusage adds supervisor plus maximum single-child peak, not an instantaneous process-tree OS reservation. Historical per-PID peaks are metadata only. Unfinished ledger stages forbid resets.')
        update()
    print(json.dumps({k: receipt[k] for k in ('status', 'attempt_active_seconds', 'engine_apply_attempts', 'completed_or_reserved_updates')}))
    return receipt
def run(args):
    if args.stage!="collect":raise ValueError("this guard authorizes collection only")
    # No preflight/import/build or child launch can overlap another campaign phase.
    with CampaignLedger(args.ledger) as ledger:
        return _run_leased(args,ledger)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=("collect",),default="collect")
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--target-dir",type=Path,default=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target"))
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    receipt=run(args)
    if args.execute and receipt["status"]!="completed":sys.exit(1)
if __name__=="__main__":main()
