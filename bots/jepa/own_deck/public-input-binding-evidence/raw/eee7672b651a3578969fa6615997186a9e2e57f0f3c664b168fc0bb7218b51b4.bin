"""Once-only native build/collection guard; default is pure source preflight."""
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
MAX_BYTES=1024**3
INTERVAL=.05
ACCOUNTING_SOURCE=HERE.parent/"public_input_binding_recovery_accounting.py"
ACCOUNTING_SHA256="ac3cca80088352a94873ce9b67ae0d746897f509d47a82e05bfc2cde81cbabe7"
STAGES={"native-build":(30.,0),"native-collect":(60.,80)}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

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

def pin(path):
    p=Path(path).resolve();return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def load_accounting():
    if sha(ACCOUNTING_SOURCE)!=ACCOUNTING_SHA256:raise ValueError("shared accounting source pin changed")
    spec=importlib.util.spec_from_file_location("binding_native_accounting",ACCOUNTING_SOURCE)
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);return a


def preflight():
    manifest=json.loads((HERE/"source-manifest.json").read_text())
    for item in manifest["pinned_execution_inputs"]:
        if pin(item["path"])!=item:raise ValueError("pinned input changed: "+item["path"])
    for item in manifest["project_files"]:
        p=HERE/item["path"]
        if sha(p)!=item["sha256"]or p.stat().st_size!=item["bytes"]:raise ValueError("collector source changed: "+item["path"])
    if manifest["accounting"]["sha256"]!=ACCOUNTING_SHA256:raise ValueError("accounting manifest differs")
    return manifest


def trace_exposure(path,launched):
    """Keep known-prefix call count separate from charged failed reservation."""
    p=Path(path)
    if not p.exists():return dict(known_calls=0,verified=not launched,reason=None if not launched else "collector launched without readable journal")
    count=0
    try:
        rows=p.read_text().splitlines()
        if not rows:raise ValueError("empty native journal")
        header=json.loads(rows[0])
        if header.get("schema")!="jepa-public-input-binding-apply-journal/1":raise ValueError("native journal schema differs")
        for line in rows[1:]:
            row=json.loads(line)
            if row.get("phase")=="beforeApply":
                if row.get("applyCall")!=count+1:raise ValueError("nonsequential durable native intent")
                count+=1
        return dict(known_calls=count,verified=True,reason=None)
    except Exception as error:
        return dict(known_calls=count,verified=False,reason=str(error))


def verify_no_physical_shields(raw):
    """The added definition is constructor support, never an experimental token."""
    captures=0;projections=0
    def scan_state(value):
        if isinstance(value,dict):
            if value.get("setCode")=="TOKEN_SHIELD"or value.get("code")=="TOKEN_SHIELD":
                raise ValueError("physical Shield instance in recovery capture")
            for child in value.values():scan_state(child)
        elif isinstance(value,list):
            for child in value:scan_state(child)
    def walk(value):
        nonlocal captures,projections
        if isinstance(value,dict):
            if "state"in value and"projections"in value:
                captures+=1
                if not isinstance(value["projections"],dict):raise ValueError("recovery projections missing")
                scan_state(value["state"])
                for p in value["projections"].values():
                    if p is None:continue
                    if not isinstance(p,dict)or type(p.get("shield_count"))is not int or p["shield_count"]!=0:
                        raise ValueError("nonzero or unknown Shield count in recovery capture")
                    projections+=1;scan_state(p)
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    # Do not scan catalogue metadata: the exact support definition belongs there.
    walk(raw.get("cases"))
    if not captures or not projections:raise ValueError("recovery physical-token proof has no captures")
    return dict(physical_shield_instances=0,captures_checked=captures,projections_checked=projections,
                scope="All raw case captures, including fixture query, before, steps, target prompt, final and last observed; native state nested attachments and projection counts.")


def build_binary_proof(records,binary):
    for row in reversed(records):
        if row["event"]=="attempt-finish":
            for proof in row["data"].get("proofs",[]):
                if proof.get("role")=="built-collector-binary":
                    expected={k:proof[k]for k in("path","sha256","bytes")}
                    if pin(binary)!=expected:raise ValueError("built collector binary changed before collection")
                    return expected
    raise ValueError("successful build binary proof required before collection")


def cleanup_owned(proc,pgid,members,receipt):
    """Any uncertain kill/wait/group inventory preserves the pending lease."""
    verified=True;errors=receipt.setdefault("cleanup_errors",[])
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    except BaseException as error:
        verified=False;errors.append(dict(operation="kill-owned-group",error=type(error).__name__+": "+str(error)))
    try:proc.wait(timeout=2)
    except BaseException as error:
        verified=False;errors.append(dict(operation="wait-owned-leader",error=type(error).__name__+": "+str(error)))
    try:
        remaining=members(pgid)
        if remaining:
            verified=False;errors.append(dict(operation="inventory-owned-group",remaining_pids=remaining))
    except BaseException as error:
        verified=False;errors.append(dict(operation="inventory-owned-group",error=type(error).__name__+": "+str(error)))
    return verified


def close_accounted_attempt(a,stream,records,receipt,elapsed,exposure,proofs,cleanup_verified):
    if not cleanup_verified:
        receipt["pending_attempt_preserved"]=True
        return
    state=a.finish(stream,records,receipt["status"],elapsed,native_applies=exposure["known_calls"],proofs=proofs,native_journal_verified=exposure["verified"])
    receipt.update(charged_native_applies=state["charged_native_applies"],charged_seconds=state["charged_seconds"],ledger_last_record_sha256=state["last_record_sha256"])


def preview(args,a,manifest):
    if args.stage not in STAGES:raise ValueError("only native-build/native-collect stages exist")
    if Path(args.ledger).resolve()!=a.LEDGER.resolve():raise ValueError("one canonical shared campaign ledger required")
    if args.target_dir.resolve()!=Path(manifest["cargo_target_dir"]).resolve():raise ValueError("use pinned writable warm Cargo target cache")
    if args.out.resolve()!=Path(manifest["stage_output_dirs"][args.stage]).resolve():raise ValueError("fixed non-overwriting stage output required")
    binary=args.target_dir/"debug/public-input-binding-recovery-collector"
    command=(["cargo","build","--offline","--locked","--manifest-path",str(HERE/"Cargo.toml"),"--bin","public-input-binding-recovery-collector","-j","1"]if args.stage=="native-build"else[str(binary),str(args.out/"native-receipt.json")])
    return dict(stage=args.stage,phase="native",command=command,source_manifest=pin(HERE/"source-manifest.json"),accounting=pin(ACCOUNTING_SOURCE),
        max_active_seconds=STAGES[args.stage][0],reserved_native_applies=STAGES[args.stage][1],max_sampled_bytes=MAX_BYTES,sample_interval_seconds=INTERVAL,
        optimizer_updates=0,neural_forwards=0,numerical_fits=0,paid_jobs=0,campaign_ledger=str(a.LEDGER),
        build_profile=dict(opt_level=0,debug=0,incremental=False,codegen_override=None,rustflags=[],cargo_build_workers=1,os_single_core_affinity=False),
        no_retries=True,binary=str(binary),ledger_initialized=a.LEDGER.is_file())


def run(args):
    if args.stage not in STAGES:raise ValueError("native build/collect only; no fit/evaluate/reset mode")
    a=load_accounting()
    if not args.execute:
        manifest=preflight();build_environment(args.target_dir);result=preview(args,a,manifest);a.verify_parents();print(json.dumps(result,indent=2));return result
    with a.lease(args.ledger)as(stream,records,current):
        started=time.monotonic();manifest=preflight();env=build_environment(args.target_dir);summary=preview(args,a,manifest)
        if args.out.exists():raise FileExistsError("preserve prior stage directory; no retry")
        args.out.mkdir(parents=True)
        a.start(stream,records,args.stage,summary)
        limit=summary["max_active_seconds"];receipt={**summary,"status":"started","phases":[],"observed_per_pid_peak_bytes":{},"sample_count":0,"exited_owned_pid_skips":[]}
        rp=args.out/"supervisor-receipt.json";proc=None;pgid=None;launched=False;cleanup_verified=True;proofs=[]
        def update():
            receipt["active_seconds"]=time.monotonic()-started;rp.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        try:
            update();rss,members=process_readers();rss(os.getpid())
            if args.stage=="native-collect":receipt["built_binary"]=build_binary_proof(records,Path(summary["binary"]))
            env["PUBLIC_INPUT_BINDING_COLLECTION_PLAN"]=str(HERE/"collection-plan.json")
            env["PUBLIC_INPUT_BINDING_NATIVE_TRACE"]=str(args.out/"native-transitions.jsonl")
            with(args.out/"stdout.log").open("x")as stdout,(args.out/"stderr.log").open("x")as stderr:
                proc=subprocess.Popen(summary["command"],cwd=HERE,env=env,stdout=stdout,stderr=stderr,start_new_session=True);pgid=proc.pid
                launched=args.stage=="native-collect";receipt["owned_pgid"]=pgid;update()
                while True:
                    readings=read_owned_rss(receipt,members(pgid),rss,os.getpid(),time.monotonic()-started)
                    peak=memory_sample(receipt,readings,os.getpid(),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);receipt["sample_count"]+=1
                    if peak>MAX_BYTES:raise RuntimeError("1GiB sampled concurrent live owned-process RSS threshold")
                    if time.monotonic()-started>=limit:raise RuntimeError("fixed stage active-wall limit exceeded")
                    code=proc.poll()
                    if code is not None:
                        receipt["exit_code"]=code
                        if members(pgid):raise RuntimeError("owned descendants remained after leader exit")
                        proc=None
                        if code:raise RuntimeError("owned stage exited "+str(code))
                        break
                    time.sleep(min(INTERVAL,max(.001,limit-(time.monotonic()-started))))
            if args.stage=="native-build":
                proofs.append(dict(role="built-collector-binary",**pin(summary["binary"])))
            else:
                raw=json.loads((args.out/"native-receipt.json").read_text());exposure=trace_exposure(args.out/"native-transitions.jsonl",True)
                if not exposure["verified"]or exposure["known_calls"]!=raw["applyCalls"]or raw["applyCalls"]>80 or len(raw["cases"])!=16 or raw.get("collectionComplete")is not True:
                    raise ValueError("native receipt/journal/complete16-root count differs")
                if any(c["completion"]!="settled"or c["engineError"]is not None or c.get("intendedTargetCommitted")is not True for c in raw["cases"]):
                    raise ValueError("unsettled/error/uncommitted native root blocks qualification")
                receipt["constructor_support_only"]=verify_no_physical_shields(raw)
                proofs.extend([dict(role="native-receipt",**pin(args.out/"native-receipt.json")),dict(role="durable-apply-journal",**pin(args.out/"native-transitions.jsonl"))])
            receipt["status"]="completed"
        except BaseException as error:
            receipt.update(status="failed",error=type(error).__name__+": "+str(error))
            if proc is not None:
                cleanup_verified=cleanup_owned(proc,pgid,members,receipt)
        finally:
            parent=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;child=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            bound=final_memory_bound(receipt.get("observed_peak_live_sum_bytes",0),parent,child)
            receipt.update(supervisor_maxrss_bytes=parent,max_single_child_rusage_peak_bytes=child,observed_conservative_peak_sum_bytes=bound,
                cleanup_verified=cleanup_verified,memory_limitation="50ms live owned-RSS samples; max with parent rusage peak plus maximum single child peak, not an OS process-tree reservation")
            if bound>MAX_BYTES:receipt.update(status="failed",error="final supervisor+single-child rusage RSS threshold exceeded")
            elapsed=time.monotonic()-started
            if elapsed>limit:receipt.update(status="failed",error="fixed stage active-wall limit exceeded including cleanup")
            exposure=trace_exposure(args.out/"native-transitions.jsonl",launched)if args.stage=="native-collect"else dict(known_calls=0,verified=True,reason=None)
            if not exposure["verified"]:receipt.update(status="failed",native_journal_error=exposure["reason"])
            receipt.update(known_native_apply_lower_bound=exposure["known_calls"],observed_native_applies=exposure["known_calls"]if exposure["verified"]else None,native_journal_verified=exposure["verified"],proofs=proofs)
            close_accounted_attempt(a,stream,records,receipt,elapsed,exposure,proofs,cleanup_verified)
            update()
        print(json.dumps({k:receipt.get(k)for k in("stage","status","active_seconds","observed_native_applies","charged_native_applies","error")}));return receipt


def main():
    a=load_accounting();p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",choices=tuple(STAGES),required=True);p.add_argument("--ledger",type=Path,default=a.LEDGER)
    p.add_argument("--out",type=Path,required=True);p.add_argument("--target-dir",type=Path,default=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target"));p.add_argument("--execute",action="store_true")
    args=p.parse_args();result=run(args)
    if args.execute and result["status"]!="completed":sys.exit(1)


if __name__=="__main__":main()
