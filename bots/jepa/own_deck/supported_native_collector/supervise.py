"""One owned worker and a durable shared collection/fit quota. Default: preflight.

No stage runs without --execute. Compilation counts toward the same cumulative
120-second active allowance as collection and fit, including failed attempts.
An unfinished previous ledger stage fails closed rather than resetting quota.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
MAX_SECONDS=120.
MAX_APPLIES=96
MAX_UPDATES=600
MAX_BYTES=2*1024**3
INTERVAL=.05


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def append(file,row):
    file.write(json.dumps(row,allow_nan=False,sort_keys=True)+"\n")
    file.flush(); os.fsync(file.fileno())


def ledger_totals(rows):
    pending=None; seconds=0.; applies=updates=0
    for row in rows:
        if row.get("event")=="stage-start":
            if pending is not None: raise RuntimeError("unfinished prior campaign stage; quota cannot reset")
            pending=row["stage_id"]
        elif row.get("event")=="stage-finish":
            if pending!=row["stage_id"]: raise RuntimeError("campaign ledger stage mismatch")
            pending=None
            elapsed=row["active_seconds"]; calls=row["engine_apply_attempts"]; count=row["completed_or_reserved_updates"]
            if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:
                raise RuntimeError("invalid campaign time debit")
            if type(calls) is not int or type(count) is not int or min(calls,count)<0:
                raise RuntimeError("invalid campaign apply/update debit")
            seconds+=elapsed; applies+=calls; updates+=count
        else: raise RuntimeError("unknown campaign ledger event")
    if pending is not None: raise RuntimeError("unfinished prior campaign stage; preserve evidence, no retry/reset")
    if seconds<0 or applies<0 or updates<0: raise RuntimeError("negative campaign debit")
    return dict(active_seconds=seconds,engine_apply_attempts=applies,updates=updates)


class CampaignLedger:
    """Exclusive stage lease; all attempts and both phases share this file."""
    def __init__(self,path):
        self.path=Path(path)
        self.file=None

    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.file=self.path.open("a+")
        fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.file.seek(0)
        try: self.totals=ledger_totals([json.loads(line) for line in self.file if line.strip()])
        except BaseException:
            self.file.close(); raise
        self.file.seek(0,os.SEEK_END)
        return self

    def start(self,stage,reserved_applies,reserved_updates,metadata):
        if reserved_applies+self.totals["engine_apply_attempts"]>MAX_APPLIES or reserved_updates+self.totals["updates"]>MAX_UPDATES:
            raise RuntimeError("campaign apply/update quota exhausted before launch")
        self.remaining_seconds=MAX_SECONDS-self.totals["active_seconds"]
        if self.remaining_seconds<=0: raise RuntimeError("campaign active wall quota exhausted before launch")
        self.stage_id=f"{stage}-{time.time_ns()}"
        self.started=time.monotonic()
        append(self.file,dict(event="stage-start",stage_id=self.stage_id,stage=stage,
            prior=self.totals,reserved_applies=reserved_applies,reserved_updates=reserved_updates,
            remaining_seconds=self.remaining_seconds,metadata=metadata))

    def finish(self,applies,updates,status):
        append(self.file,dict(event="stage-finish",stage_id=self.stage_id,status=status,
            active_seconds=time.monotonic()-self.started,engine_apply_attempts=applies,
            completed_or_reserved_updates=updates))

    def __exit__(self,*exc):
        self.file.close()


def count_applies(path):
    """Count durable before-apply intent records, including failed engine calls."""
    if not Path(path).exists(): return 0
    calls=[]
    for line in Path(path).read_text().splitlines():
        row=json.loads(line)
        if row.get("phase")=="beforeApply": calls.append(row["applyCall"])
    if calls!=list(range(1,len(calls)+1)): raise RuntimeError("nonsequential durable apply journal")
    return len(calls)


def count_updates(path):
    if not Path(path).exists(): return None
    updates=[]
    for line in Path(path).read_text().splitlines():
        row=json.loads(line)
        value=row.get("updates_completed",row.get("metrics",{}).get("updates_completed"))
        if value is not None:
            if type(value) is not int or value<0: raise RuntimeError("invalid update progress record")
            updates.append(value)
    if updates!=list(range(1,len(updates)+1)): raise RuntimeError("update journal is not one durable record per completed update")
    return max(updates,default=0)


def update_debit(path,reservation,status):
    try: actual=count_updates(path)
    except Exception: actual=None
    if status=="completed" and actual==reservation:
        return actual,status,"exact completed-step journal"
    if status=="completed": status="failed"
    return reservation,status,"interrupted, missing, or incomplete step journal; entire reservation charged"


def preflight():
    manifest=json.loads((HERE/"source-manifest.json").read_text())
    for item in manifest["pinned_execution_inputs"]:
        if sha(item["path"])!=item["sha256"]: raise RuntimeError("pinned source mismatch: "+item["path"])
    for item in manifest["project_files"]:
        if sha(HERE/item["path"])!=item["sha256"]: raise RuntimeError("collector source mismatch: "+item["path"])
    return manifest


def process_readers():
    if sys.platform!="darwin": raise RuntimeError("verified macOS owned-group RSS guard required")
    lib=ctypes.CDLL("/usr/lib/libproc.dylib",use_errno=True)
    lib.proc_listpids.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int]
    lib.proc_listpids.restype=ctypes.c_int
    lib.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
    lib.proc_pidinfo.restype=ctypes.c_int
    def rss(pid):
        buf=ctypes.create_string_buffer(96)
        got=lib.proc_pidinfo(pid,4,0,buf,96)
        if got!=96: raise OSError(ctypes.get_errno(),f"owned PID {pid} RSS unavailable ({got})")
        return ctypes.c_uint64.from_buffer(buf,8).value
    def members(pgid):
        buf=(ctypes.c_int*4096)()
        count=lib.proc_listpids(2,pgid,buf,ctypes.sizeof(buf))
        if count<0 or count%4 or count>=ctypes.sizeof(buf): raise RuntimeError("owned group inventory unavailable/truncated")
        return sorted(pid for pid in buf[:count//4] if pid>0)
    return rss,members


def run(args):
    manifest=preflight()
    commands=[]
    env=os.environ.copy()
    for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS"): env[key]="1"
    env.update(CARGO_BUILD_JOBS="1",CARGO_TARGET_DIR=str(args.target_dir),CARGO_NET_OFFLINE="true")
    if args.stage=="collect":
        commands=[("build",["cargo","build","--offline","--locked","--manifest-path",str(HERE/"Cargo.toml"),"--bin","supported-native-collector","-j","1"]),
                  ("collect",[str(args.target_dir/"debug/supported-native-collector"),str(args.out/"native-receipt.json")])]
        env["SUPPORTED_NATIVE_TRACE"]=str(args.out/"native-transitions.jsonl")
        reserve_applies,reserve_updates=64,0
    else:
        if not args.command or args.progress is None: raise ValueError("fit requires --progress and --command")
        commands=[("fit",args.command)]
        reserve_applies,reserve_updates=0,args.max_updates
        if not 1<=reserve_updates<=MAX_UPDATES: raise ValueError("fit update reservation invalid")
    preview=dict(stage=args.stage,commands=commands,source_manifest_sha256=sha(HERE/"source-manifest.json"),
        campaign_ledger=str(args.ledger),max_active_seconds=MAX_SECONDS,max_engine_apply_attempts=MAX_APPLIES,
        max_updates=MAX_UPDATES,reserved_engine_applies=reserve_applies,reserved_updates=reserve_updates,
        max_sampled_bytes=MAX_BYTES,sample_interval_seconds=INTERVAL,
        scope="one fresh owned process group at a time, supervisor plus owned members only; no unrelated process signals")
    preview["prior_campaign_debits"]=ledger_totals([json.loads(line) for line in args.ledger.read_text().splitlines() if line.strip()]) if args.ledger.exists() else dict(active_seconds=0.,engine_apply_attempts=0,updates=0)
    if not args.execute:
        print(json.dumps(preview,indent=2)); return preview
    rss,members=process_readers()
    rss(os.getpid())
    args.out.mkdir(parents=True,exist_ok=False)
    receipt={**preview,"status":"started","phases":[],"observed_per_pid_peak_bytes":{},"sample_count":0}
    receipt_path=args.out/"supervisor-receipt.json"
    proc=None
    with CampaignLedger(args.ledger) as ledger:
        ledger.start(args.stage,reserve_applies,reserve_updates,preview)
        def update():
            receipt["attempt_active_seconds"]=time.monotonic()-ledger.started
            receipt_path.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        def sample(pgid):
            own=members(pgid)
            readings={os.getpid():rss(os.getpid())}
            for pid in own:
                try: readings[pid]=rss(pid)
                except OSError as exc:
                    if exc.errno==3: continue  # A known owned child exited between samples.
                    raise
            for pid,value in readings.items():
                key=str(pid); receipt["observed_per_pid_peak_bytes"][key]=max(value,receipt["observed_per_pid_peak_bytes"].get(key,0))
            parent_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            key=str(os.getpid()); receipt["observed_per_pid_peak_bytes"][key]=max(parent_peak,receipt["observed_per_pid_peak_bytes"].get(key,0))
            conservative=sum(receipt["observed_per_pid_peak_bytes"].values())
            receipt["observed_conservative_peak_sum_bytes"]=conservative
            receipt["sample_count"]+=1
            if conservative>MAX_BYTES: raise RuntimeError("2GiB sampled owned-process peak sum threshold")
            if time.monotonic()-ledger.started>=ledger.remaining_seconds: raise RuntimeError("120-second cumulative active wall quota exhausted")
        try:
            update()
            for name,command in commands:
                if time.monotonic()-ledger.started>=ledger.remaining_seconds: raise RuntimeError("no campaign wall quota remains")
                phase=dict(name=name,command=command); receipt["phases"].append(phase); update()
                with (args.out/(name+".stdout.log")).open("x") as out,(args.out/(name+".stderr.log")).open("x") as err:
                    proc=subprocess.Popen(command,cwd=HERE,env=env,stdout=out,stderr=err,start_new_session=True)
                    phase["owned_pgid"]=proc.pid
                    while True:
                        sample(proc.pid)
                        if args.stage=="fit" and count_updates(args.progress) is not None and count_updates(args.progress)>reserve_updates:
                            raise RuntimeError("fit progress exceeded reserved update quota")
                        code=proc.poll()
                        if code is not None:
                            phase["exit_code"]=code
                            if members(proc.pid): raise RuntimeError("owned descendants remained after group leader exit")
                            if code: raise RuntimeError(f"{name} exited {code}")
                            proc=None; break
                        time.sleep(min(INTERVAL,max(.001,ledger.remaining_seconds-(time.monotonic()-ledger.started))))
                update()
            if args.stage=="collect":
                native=json.loads((args.out/"native-receipt.json").read_text())
                calls=count_applies(args.out/"native-transitions.jsonl")
                if native["applyCalls"]!=calls or calls>64 or len(native["cases"])!=16: raise RuntimeError("native journal/receipt quota mismatch")
                receipt.update(engine_apply_attempts=calls,native_receipt_sha256=sha(args.out/"native-receipt.json"))
            receipt["status"]="completed"
        except BaseException as exc:
            receipt.update(status="failed",error=f"{type(exc).__name__}: {exc}")
            if proc is not None:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait(timeout=2)
        finally:
            parent_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            child_peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            receipt.update(supervisor_maxrss_bytes=parent_peak,children_maxrss_bytes=child_peak)
            final_bound=max(receipt.get("observed_conservative_peak_sum_bytes",0),parent_peak+child_peak)
            receipt["observed_conservative_peak_sum_bytes"]=final_bound
            if final_bound>MAX_BYTES:
                receipt.update(status="failed",error="final owned supervisor/child rusage RSS threshold exceeded")
            try: applies=count_applies(args.out/"native-transitions.jsonl") if args.stage=="collect" else 0
            except Exception: applies=reserve_applies; receipt["apply_accounting"]="malformed interrupted journal; entire reservation charged"
            updates=0
            if args.stage=="fit":
                updates,status,accounting=update_debit(args.progress,reserve_updates,receipt["status"])
                receipt.update(status=status,update_accounting=accounting)
                if status!="completed" and "error" not in receipt: receipt["error"]="fit did not produce the exact fixed-allocation progress journal"
            ledger.finish(applies,updates,receipt["status"])
            receipt.update(engine_apply_attempts=applies,completed_or_reserved_updates=updates,
                prior_campaign_debits=ledger.totals,
                guard_limitation="Sampled known-owned process-group RSS and rusage peaks; not an instantaneous OS memory reservation. Failed update stages conservatively debit reservation. Unfinished ledger stages forbid resets.")
            update()
    print(json.dumps({k:receipt[k] for k in ("status","attempt_active_seconds","engine_apply_attempts","completed_or_reserved_updates")}))
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",choices=("collect","fit"),required=True)
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--target-dir",type=Path,default=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target"))
    parser.add_argument("--progress",type=Path)
    parser.add_argument("--max-updates",type=int,default=600)
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--command",nargs=argparse.REMAINDER)
    args=parser.parse_args()
    receipt=run(args)
    if args.execute and receipt["status"]!="completed": sys.exit(1)


if __name__=="__main__": main()
