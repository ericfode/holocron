"""One-shot, own-process-group supervisor for the two-card native microprobe.

This is a sampled stop guard, not an instantaneous OS memory reservation.
It never enumerates unrelated processes or sends a signal outside a new group.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
MAX_SECONDS=120.0
MAX_BYTES=2*1024**3
INTERVAL=.05
lib=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
lib.proc_listpids.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int]
lib.proc_listpids.restype=ctypes.c_int
lib.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
lib.proc_pidinfo.restype=ctypes.c_int


def rss(pid):
    buf=ctypes.create_string_buffer(96)
    got=lib.proc_pidinfo(pid,4,0,buf,96)
    if got!=96: raise OSError(ctypes.get_errno(),f'RSS unavailable for owned PID {pid}: return {got}')
    return ctypes.c_uint64.from_buffer(buf,8).value


def members(pgid):
    buf=(ctypes.c_int*4096)()
    count=lib.proc_listpids(2,pgid,buf,ctypes.sizeof(buf))
    if count<0 or count%4 or count>=ctypes.sizeof(buf):
        raise RuntimeError(f'owned process-group inventory unavailable/truncated: {count}')
    return sorted(pid for pid in buf[:count//4]if pid>0)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight(continuing=False):
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    for item in manifest['pinned_execution_inputs']:
        if sha(item['path'])!=item['sha256']: raise RuntimeError(f'pinned input mismatch: {item["path"]}')
    for item in manifest['project_files']:
        if sha(HERE/item['path'])!=item['sha256']: raise RuntimeError(f'probe source mismatch: {item["path"]}')
    if (HERE/'native-receipt.json').exists()or((HERE/'supervisor-receipt.json').exists()and not continuing):
        raise RuntimeError('a previous receipt exists; refusing duplicate native attempt')
    rss(os.getpid())


def main():
    previous_path=Path(sys.argv[1]).resolve()if len(sys.argv)>=2 else None
    previous=json.loads(previous_path.read_text())if previous_path else None
    if previous is not None and previous['status']!='failed':
        raise RuntimeError('continuation requires an explicitly authorized failed receipt')
    if previous is not None and any(p['name']=='native'for p in previous['phases']):
        error_path=previous_path.parent/'native.stderr.log'
        if error_path.read_text().strip()!='microprobe: catalogue must include native Shield token':
            raise RuntimeError('native continuation is restricted to the known zero-apply Shield setup failure')
    spent=previous['elapsed_seconds']if previous else 0.
    if not 0<=spent<MAX_SECONDS: raise RuntimeError('original cumulative budget exhausted')
    preflight(continuing=previous is not None)
    output=HERE/sys.argv[2]if len(sys.argv)==3 else(HERE/'attempt-2'if previous else HERE)
    if previous: output.mkdir(exist_ok=False)
    # Created before launch and finalized even on blocked offline compilation.
    receipt_path=output/'supervisor-receipt.json'
    receipt_path.touch(exist_ok=False)
    attempt_started=time.monotonic()
    started=attempt_started-spent
    receipt=dict(schema='typed-ir-microprobe-supervision/1',status='started',
        source_manifest_sha256=sha(HERE/'source-manifest.json'),supervisor_sha256=sha(__file__),
        limits=dict(cumulative_build_and_run_seconds=MAX_SECONDS,sampled_rss_stop_bytes=MAX_BYTES,
                    sample_interval_seconds=INTERVAL,cargo_workers=1,max_engine_applies=12),
        guard_scope='supervisor plus all current members of each fresh owned process group',
        limitation='Sampled RSS stop guard; short spikes and between-sample short-lived children may be missed. No instantaneous OS reservation.',
        phases=[],observed_peak_concurrent_rss_bytes=previous['observed_peak_concurrent_rss_bytes']if previous else 0,
        observed_per_pid_peak_rss_bytes={},sample_count=0,disappeared_owned_children=[])
    if previous:
        receipt.update(previous_receipt=str(previous_path),previous_receipt_sha256=sha(previous_path),
            previously_spent_guarded_seconds=spent,previous_native_apply_calls=0,continuation_not_a_budget_reset=True)
    proc=None
    def update():
        receipt['elapsed_seconds']=time.monotonic()-started
        receipt['attempt_elapsed_seconds']=time.monotonic()-attempt_started
        receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    def sample(pgid):
        own=members(pgid)
        readings={os.getpid():rss(os.getpid())}
        for pid in own:
            try: readings[pid]=rss(pid)
            except OSError as exc:
                if proc is not None and pid==proc.pid and proc.poll()is not None: continue
                if proc is not None and pid!=proc.pid and exc.errno==3:
                    receipt['disappeared_owned_children'].append(dict(pid=pid,errno=3,elapsed_seconds=time.monotonic()-started))
                    continue
                raise  # Permission and every unknown RSS failure stop, even after a concurrent exit.
        for pid,value in readings.items():
            key=str(pid)
            receipt['observed_per_pid_peak_rss_bytes'][key]=max(value,receipt['observed_per_pid_peak_rss_bytes'].get(key,0))
        total=sum(readings.values())
        receipt['sample_count']+=1
        receipt['observed_peak_concurrent_rss_bytes']=max(total,receipt['observed_peak_concurrent_rss_bytes'])
        if total>MAX_BYTES: raise RuntimeError('sampled RSS stop threshold exceeded')
        if time.monotonic()-started>=MAX_SECONDS: raise RuntimeError('cumulative build+run wall ceiling exceeded')
    def phase(name,cmd,env):
        nonlocal proc
        if time.monotonic()-started>=MAX_SECONDS: raise RuntimeError('no wall budget remains')
        entry=dict(name=name,command=cmd,started_elapsed_seconds=time.monotonic()-started)
        receipt['phases'].append(entry); update()
        with (output/(name+'.stdout.log')).open('x')as out,(output/(name+'.stderr.log')).open('x')as err:
            proc=subprocess.Popen(cmd,cwd=HERE,env=env,stdout=out,stderr=err,start_new_session=True)
            entry['owned_pgid']=proc.pid
            while True:
                sample(proc.pid)
                code=proc.poll()
                if code is not None:
                    entry.update(exit_code=code,finished_elapsed_seconds=time.monotonic()-started)
                    if members(proc.pid): raise RuntimeError('owned subprocess group remained after leader exit')
                    if code!=0: raise RuntimeError(f'{name} exited {code}')
                    proc=None; update(); return
                time.sleep(min(INTERVAL,max(.001,MAX_SECONDS-(time.monotonic()-started))))
    try:
        env=os.environ.copy()
        env.update(CARGO_BUILD_JOBS='1',CARGO_TARGET_DIR=str(HERE/'target'),CARGO_NET_OFFLINE='true')
        env['TYPED_IR_TRACE']=str(output/'native-transitions.jsonl')
        phase('build',['cargo','build','--offline','--locked','--manifest-path',str(HERE/'Cargo.toml'),'--bin','typed-ir-microprobe','-j','1'],env)
        binary=HERE/'target/debug/typed-ir-microprobe'
        receipt['binary_sha256']=sha(binary)
        phase('native',[str(binary),str(HERE/'native-receipt.json')],env)
        native=json.loads((HERE/'native-receipt.json').read_text())
        if native['applyCalls']!=8 or native['applyCalls']>12: raise RuntimeError('native transition count mismatch')
        receipt.update(status='completed',native_receipt_sha256=sha(HERE/'native-receipt.json'),apply_calls=native['applyCalls'])
    except BaseException as exc:
        receipt.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        if proc is not None:
            # Signal only the fresh group created by this supervisor.
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=5)
            receipt['stopped_owned_pgid']=proc.pid
    finally:
        parent_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        key=str(os.getpid())
        receipt['observed_per_pid_peak_rss_bytes'][key]=max(parent_peak,receipt['observed_per_pid_peak_rss_bytes'].get(key,0))
        receipt['supervisor_self_maxrss_bytes']=parent_peak
        receipt['children_self_maxrss_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        receipt['observed_per_pid_peak_sum_bytes']=sum(receipt['observed_per_pid_peak_rss_bytes'].values())
        update()
    print(json.dumps({k:receipt[k]for k in('status','elapsed_seconds','observed_peak_concurrent_rss_bytes','sample_count')}))
    return 0 if receipt['status']=='completed'else 1


if __name__=='__main__': sys.exit(main())
