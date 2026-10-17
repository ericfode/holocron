"""Bounded, matched local auxiliary representation fits; launch only when authorized.

Three arms, one seed, at most 100 AdamW updates each. Trains only the new deck
projection/roles and a linear auxiliary head. Frozen baseline weights and all
engine/action/world-transition objectives are outside this runner.
"""
import os
for _thread_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_thread_var] = "1"

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import multiprocessing
from pathlib import Path
import platform
import queue
import resource
import subprocess
import sys
import threading
import time

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT))
import model as M
import own_deck as O
import own_deck_model as D
from run_events import RunEvents

ARMS=("neutral","original","wrong-own")
LIMITATIONS=(
    "Auxiliary original-deck representation fit on existing local declared lists, not a policy or playing-strength experiment.",
    "No action-conditioned transition loss, environment rollouts, opponent execution, remaining-deck ledger, or effect-program semantics.",
    "Draw label is initial unit fraction n_unit/N at declaration, never the actual next hidden card or live remaining-pile probability.",
    "Empty constant board/hand is a synthetic declaration context, not a reconstructed game state.",
    "One seed and a small family-disjoint holdout are diagnostic; no selection of a new competitive checkpoint is authorized.",
)
MAX_STEPS=100
MAX_BATCH=16
MAX_ARM_SECONDS=120.
MAX_CAMPAIGN_SECONDS=300.
MAX_RSS_MIB=2048.


class GuardStopped(RuntimeError):
    def __init__(self,reason,evidence):
        super().__init__(reason)
        self.guard=evidence


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")


def peak_rss_mib():
    size=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return size/(1024**2) if sys.platform=="darwin" else size/1024


def owned_rss_mib(pid):
    """Read one explicitly owned PID only; never enumerate process tables."""
    if sys.platform!="darwin":
        raise OSError("this guarded pilot requires the verified macOS libproc RSS reader")
    library=ctypes.CDLL("/usr/lib/libproc.dylib",use_errno=True)
    info=library.proc_pidinfo
    info.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
    info.restype=ctypes.c_int
    # macOS SDK sys/proc_info.h: proc_taskinfo is96bytes, resident_size at8.
    buffer=ctypes.create_string_buffer(96)
    got=info(pid,4,0,buffer,96)
    if got!=96:
        raise OSError(ctypes.get_errno(),f"owned PID{pid} RSS unreadable (proc_pidinfo returned{got})")
    return ctypes.c_uint64.from_buffer(buffer,8).value/(1024**2)


@dataclass(frozen=True)
class Config:
    seed:int=17
    steps:int=100
    batch:int=16
    learning_rate:float=0.001
    weight_decay:float=0.0001
    max_arm_seconds:float=120.
    max_campaign_seconds:float=300.
    max_rss_mib:float=2048.

    def validate(self):
        if self.seed!=17: raise ValueError("this allocation admits seed17 only")
        if not 1<=self.steps<=MAX_STEPS: raise ValueError("updates must be in1..100")
        if not 1<=self.batch<=MAX_BATCH: raise ValueError("batch must be in1..16")
        if not 0<self.max_arm_seconds<=MAX_ARM_SECONDS: raise ValueError("per-arm time exceeds allocation")
        if not 0<self.max_campaign_seconds<=MAX_CAMPAIGN_SECONDS: raise ValueError("campaign time exceeds allocation")
        if not 0<self.max_rss_mib<=MAX_RSS_MIB: raise ValueError("RSS ceiling exceeds allocation")
        if self.learning_rate!=0.001 or self.weight_decay!=0.0001:
            raise ValueError("optimizer settings are fixed for matched first-seed allocation")
        return self

    def as_dict(self):
        return {**self.__dict__,"arms":list(ARMS),"optimizer":"AdamW","auxiliary_head":"linear96xK + bias",
                "trainable":"din.w,din.b,drole,aux.w,aux.b only","loss":"mean normalized-target squared error",
                "gradient_clip_norm":1.,"cpu_threads":1,"heartbeat_seconds":1.,"metric_every_updates":5,
                "context":"constant zero state73 and24 masked empty live-card slots plus2 deck rows",
                "checkpoint_selection":"fixed final step only; no early best-validation selection",
                "memory_guard":"known parent/worker/resource-tracker PIDs sampled with macOS libproc every<=0.1s; conservative per-PID peak sum plus reported rusage peaks; fail closed on unreadable PIDs"}


def validate_dataset(data,manifest):
    required=("deck_features","targets","train_idx","val_idx","fingerprints","family_ids","wrong_idx")
    if any(k not in data for k in required): raise ValueError("dataset missing required arrays")
    rows=np.asarray(data["deck_features"],np.float32)
    labels=np.asarray(data["targets"],np.float32)
    n=len(rows)
    if not 2<=n<=160 or rows.shape!=(n,2,207) or labels.ndim!=2 or len(labels)!=n or not 1<=labels.shape[1]<=32:
        raise ValueError("dataset shape or example cap invalid")
    if not np.isfinite(rows).all() or not np.isfinite(labels).all(): raise ValueError("nonfinite dataset")
    if not np.all(rows[:,0,3]==1) or not np.all(rows[:,0,2]==1): raise ValueError("original declarations must be complete and enabled")
    expected_rem=O.neutral_features(n)[:,1]
    if not np.array_equal(rows[:,1],expected_rem): raise ValueError("remaining deck must stay disabled and unknown")
    train=np.asarray(data["train_idx"],np.int64); val=np.asarray(data["val_idx"],np.int64)
    if train.ndim!=1 or val.ndim!=1 or len(train)<2 or len(val)<2:
        raise ValueError("each split needs at least2 examples")
    if set(train)&set(val) or set(np.r_[train,val])!=set(range(n)) or len(train)+len(val)!=n:
        raise ValueError("indices must form a complete disjoint partition")
    fingerprints=np.asarray(data["fingerprints"]).astype(str)
    families=np.asarray(data["family_ids"]).astype(str)
    wrong=np.asarray(data["wrong_idx"],np.int64)
    if fingerprints.shape!=(n,) or families.shape!=(n,) or wrong.shape!=(n,): raise ValueError("bad provenance array shapes")
    if set(fingerprints[train])&set(fingerprints[val]): raise ValueError("composition leakage across split")
    if set(families[train])&set(families[val]): raise ValueError("family leakage across split")
    for partition in (train,val):
        if set(wrong[partition])!=set(partition): raise ValueError("wrong decks must permute within each partition")
    if np.any(fingerprints==fingerprints[wrong]): raise ValueError("wrong control repeats correct composition")
    if np.any(families==families[wrong]): raise ValueError("wrong control must use another own family")
    # Metadata count/curve fields must actually differ, while status/coverage stays matched.
    if not np.all(np.any(abs(rows[:,0,8:25]-rows[wrong,0,8:25])>1e-7,axis=1)):
        raise ValueError("wrong control lacks a changed curve")
    if not np.array_equal(rows[:,0,[2,3,5,7]],rows[wrong][:,0,[2,3,5,7]]): raise ValueError("wrong control status/coverage differs")
    names=manifest.get("target_names")
    groups=manifest.get("target_groups")
    if not isinstance(names,list) or len(names)!=labels.shape[1] or len(set(names))!=len(names):
        raise ValueError("manifest target_names mismatch")
    if not isinstance(groups,dict) or set(groups)!={"count","curve","draw"}:
        raise ValueError("manifest must declare count/curve/draw target groups")
    if any(not v or any(type(i)is not int or not 0<=i<labels.shape[1] for i in v) for v in groups.values()):
        raise ValueError("invalid target groups")
    return dict(deck_features=rows,targets=labels,train_idx=train,val_idx=val,
                fingerprints=fingerprints,family_ids=families,wrong_idx=wrong,target_names=names,target_groups=groups)


def load_dataset(npz_path,manifest_path):
    manifest=json.loads(Path(manifest_path).read_text())
    expected=manifest.get("artifact",{}).get("sha256")
    if not isinstance(expected,str) or sha(npz_path)!=expected:
        raise ValueError("NPZ content does not match the manifest artifact SHA256")
    with np.load(npz_path,allow_pickle=False) as pack: data=validate_dataset(dict(pack),manifest)
    return data,manifest


def arm_features(data,arm):
    if arm=="original": return data["deck_features"].copy()
    if arm=="neutral": return O.neutral_features(len(data["targets"]))
    if arm=="wrong-own": return data["deck_features"][data["wrong_idx"]].copy()
    raise ValueError("unsupported arm")


def batch_sequence(data,config):
    rng=np.random.default_rng(config.seed+1)
    # One shared immutable index schedule, including repeats within the training partition only.
    return rng.choice(data["train_idx"],(config.steps,config.batch),replace=True)


def evaluation_metrics(pred,target,data):
    pred=np.asarray(pred,np.float64); target=np.asarray(target,np.float64)
    err=pred-target
    result={"val_loss":float(np.mean(err**2))}
    for group,indices in data["target_groups"].items():
        result[f"val_{group}_mae"]=float(np.mean(abs(err[:,indices])))
    if data["target_names"][data["target_groups"]["count"][0]]=="total_count_per_60":
        result["val_count_mae_copies"]=result["val_count_mae"]*60.
    for i,name in enumerate(data["target_names"]): result[f"val_{name}_mae"]=float(np.mean(abs(err[:,i])))
    if not all(np.isfinite(v) for v in result.values()): raise FloatingPointError("nonfinite evaluation metrics")
    return result


class Guard:
    def __init__(self,writer,config,campaign_started):
        self.writer,self.config,self.campaign_started=writer,config,campaign_started
        self.started=time.monotonic(); self.stop=threading.Event(); self.violation=None; self.thread=None

    def check(self):
        if hasattr(self.writer,"report_rss"): self.writer.report_rss()
        if time.monotonic()-self.started>self.config.max_arm_seconds: self.violation="per-arm wall-time cap"
        if time.monotonic()-self.campaign_started>self.config.max_campaign_seconds: self.violation="campaign wall-time cap"
        if peak_rss_mib()>self.config.max_rss_mib: self.violation="process peak-RSS cap"
        if self.violation: raise RuntimeError(self.violation)

    def _heartbeats(self):
        while not self.stop.wait(1.):
            try:
                self.check(); self.writer.heartbeat()
            except Exception as exc:
                self.violation=str(exc)
                break

    def __enter__(self):
        self.thread=threading.Thread(target=self._heartbeats,name="own-deck-heartbeat",daemon=True)
        self.thread.start(); return self

    def __exit__(self,*args):
        self.stop.set()
        if self.thread: self.thread.join(timeout=2.)


def train_arm(data,config,arm,schedule,writer,outdir,base_path,supplement_path,campaign_started):
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    weights,meta=D.load_extended(base_path,supplement_path)
    extras=set(D.supplemental_shapes())
    w={name:torch.tensor(value,dtype=torch.float32,requires_grad=name in extras) for name,value in weights.items()}
    rng=np.random.default_rng(config.seed+1000)
    k=data["targets"].shape[1]
    aux_w=torch.tensor(rng.normal(0,.02,(M.D,k)).astype(np.float32),requires_grad=True)
    aux_b=torch.zeros(k,dtype=torch.float32,requires_grad=True)
    parameters=[w[name] for name in D.supplemental_shapes()]+[aux_w,aux_b]
    optimizer=torch.optim.AdamW(parameters,lr=config.learning_rate,weight_decay=config.weight_decay)
    deck=torch.as_tensor(arm_features(data,arm))
    labels=torch.as_tensor(data["targets"])
    val=data["val_idx"]

    def predict(indices):
        b=len(indices)
        state=torch.zeros(b,73); ids=torch.zeros(b,24,dtype=torch.long)
        feats=torch.zeros(b,24,21); mask=torch.zeros(b,24)
        z,_=D.run_torch(w,meta,state,ids,feats,mask,own_deck=deck[indices])
        return z@aux_w+aux_b

    def evaluate():
        with torch.no_grad(): p=predict(val).numpy()
        return evaluation_metrics(p,data["targets"][val],data)

    checkpoints=[]; trace=[]
    with Guard(writer,config,campaign_started) as guard:
        guard.check()
        metrics=evaluate(); metrics.update(elapsed_seconds=0.,peak_rss_mib=peak_rss_mib())
        writer.emit("metric","baseline",0,metrics=metrics,status="running")
        trace.append(dict(step=0,**metrics))
        for step,indices in enumerate(schedule,1):
            writer.phase="training"
            guard.check()
            optimizer.zero_grad(set_to_none=True)
            pred=predict(indices)
            loss=((pred-labels[indices])**2).mean()
            if not torch.isfinite(loss): raise FloatingPointError("nonfinite train loss")
            loss.backward()
            grad_norm=torch.nn.utils.clip_grad_norm_(parameters,1.)
            if not torch.isfinite(grad_norm): raise FloatingPointError("nonfinite gradients")
            optimizer.step()
            writer.step=step
            guard.check()
            if step%5==0 or step==config.steps:
                metrics=evaluate()
                metrics.update(train_loss=float(loss.detach()),grad_norm=float(grad_norm),
                               elapsed_seconds=time.monotonic()-guard.started,peak_rss_mib=peak_rss_mib(),learning_rate=config.learning_rate)
                writer.emit("metric","training",step,metrics=metrics,status="running")
                trace.append(dict(step=step,**metrics))
        for name,value in weights.items():
            if name not in extras:
                if w[name].grad is not None or not np.array_equal(w[name].detach().numpy(),value):
                    raise AssertionError("frozen base tensor changed: "+name)
        final_extra={name:w[name].detach().numpy() for name in D.supplemental_shapes()}
        M.save_safetensors(outdir/"final-deck.safetensors",final_extra,{"format":D.FORMAT,"seed":config.seed,"arm":arm,"updates":config.steps,"purpose":"auxiliary-representation-only"})
        M.save_safetensors(outdir/"aux-head.safetensors",{"aux.w":aux_w.detach().numpy(),"aux.b":aux_b.detach().numpy()},
                           {"format":"own-deck-aux-head/1","target_names":json.dumps(data["target_names"]),"updates":config.steps})
        # Verify the deployment-format supplement loads; never copy it into generated/.
        D.load_extended(base_path,outdir/"final-deck.safetensors")
        for name in ("final-deck.safetensors","aux-head.safetensors"):
            checkpoints.append({"path":str(outdir/name),"sha256":sha(outdir/name)})
    return dict(status="completed",arm=arm,updates=config.steps,trace=trace,checkpoints=checkpoints,
                frozenBaseTensorsUnchanged=True,optimizerParameterNames=[*D.supplemental_shapes(),"aux.w","aux.b"],
                runtime=dict(python=platform.python_version(),numpy=np.__version__,torch=torch.__version__,device="cpu"))


class WorkerEvents:
    """Send observations to the single parent feed writer; no cross-process IDs."""
    def __init__(self,messages):
        self.messages=messages; self.phase="preparing"; self.step=0

    def emit(self,kind,phase,step,**kwargs):
        self.phase,self.step=phase,int(step)
        self.messages.put(("event",dict(kind=kind,phase=phase,step=step,**kwargs)))

    def heartbeat(self):
        self.report_rss()

    def report_rss(self):
        self.messages.put(("rss",dict(worker_peak_rss_mib=peak_rss_mib(),phase=self.phase,step=self.step)))


def _worker_entry(messages,acknowledged,data,config,arm,schedule,outdir,base,supplement,started):
    writer=WorkerEvents(messages)
    stop=threading.Event()
    # Covers imports/optimizer initialization before train_arm's inner guard exists.
    def report():
        while not stop.wait(1.): writer.report_rss()
    thread=threading.Thread(target=report,daemon=True)
    thread.start()
    try:
        writer.report_rss()
        result=train_arm(data,config,arm,schedule,writer,outdir,base,supplement,started)
        writer.report_rss(); messages.put(("result",result))
        if not acknowledged.wait(timeout=3.): raise RuntimeError("parent did not acknowledge terminal result")
    except BaseException as exc:
        messages.put(("failure",dict(reason=str(exc),type=type(exc).__name__,step=writer.step)))
        acknowledged.wait(timeout=3.)
    finally:
        stop.set(); thread.join(timeout=2.)


def _guard_test_worker(messages,acknowledged,mode):
    messages.put(("rss",dict(worker_peak_rss_mib=peak_rss_mib(),phase="guard-test",step=0)))
    if mode=="memory":
        # Actual owned-child allocation; its measured peak drives the parent stop.
        data=bytearray(64*1024*1024)
        data[-1]=1
        messages.put(("rss",dict(worker_peak_rss_mib=peak_rss_mib(),phase="guard-test",step=1)))
    if mode in ("complete","bad-exit","hang-after-result"):
        messages.put(("result",{"status":"test-result"}))
        acknowledged.wait(timeout=3.)
        if mode=="complete": return
        if mode=="bad-exit": raise SystemExit(3)
    time.sleep(10.)


def supervise_worker(target,args,writer,arm_seconds,campaign_started,campaign_seconds,rss_mib):
    """Watch only the created child; no ps, process scans, or unrelated signals."""
    ctx=multiprocessing.get_context("spawn")
    if time.monotonic()-campaign_started>campaign_seconds:
        raise RuntimeError("parent-enforced campaign wall-time cap before worker launch")
    messages=ctx.Queue()
    acknowledged=ctx.Event()
    process=ctx.Process(target=target,args=(messages,acknowledged,*args))
    process.start()
    started=time.monotonic(); heartbeat=started; worker_peak=0.; tree_peak=peak_rss_mib()
    from multiprocessing import resource_tracker
    tracker_pid=resource_tracker._resource_tracker._pid
    owned_pids={"supervisor":os.getpid(),"worker":process.pid,"resource_tracker":tracker_pid}
    per_pid_peaks={name:0. for name in owned_pids}

    def sample_owned_tree():
        nonlocal tree_peak
        if tracker_pid is None: raise OSError("resource-tracker owned PID missing")
        for name,pid in owned_pids.items():
            per_pid_peaks[name]=max(per_pid_peaks[name],owned_rss_mib(pid))
        per_pid_peaks["supervisor"]=max(per_pid_peaks["supervisor"],peak_rss_mib())
        per_pid_peaks["worker"]=max(per_pid_peaks["worker"],worker_peak)
        tree_peak=max(tree_peak,sum(per_pid_peaks.values()))
    result=None; reason=None
    try:
        while True:
            now=time.monotonic()
            if now-started>arm_seconds: reason="parent-enforced per-arm wall-time cap"; break
            if now-campaign_started>campaign_seconds: reason="parent-enforced campaign wall-time cap"; break
            # A normally exited worker may already have its final result queued.
            # Drain that queue before attempting to read a no-longer-live PID.
            if process.is_alive():
                try: sample_owned_tree()
                except OSError as exc: reason="owned-PID RSS guard failed closed: "+str(exc); break
            if tree_peak>rss_mib: reason="parent-enforced sampled process-tree peak-RSS cap"; break
            try: kind,payload=messages.get(timeout=.1)
            except queue.Empty:
                if not process.is_alive():
                    reason=f"worker exited without completion (exitcode={process.exitcode})"; break
                kind,payload=None,None
            if kind=="rss":
                worker_peak=max(worker_peak,float(payload["worker_peak_rss_mib"]))
                per_pid_peaks["worker"]=max(per_pid_peaks["worker"],worker_peak)
                tree_peak=max(tree_peak,sum(per_pid_peaks.values()))
                writer.phase,writer.step=payload["phase"],int(payload["step"])
            elif kind=="event":
                metrics=payload.get("metrics")
                if metrics is not None: metrics["tree_peak_rss_mib"]=tree_peak
                writer.emit(**payload)
            elif kind=="result":
                result=payload; acknowledged.set(); break
            elif kind=="failure":
                reason=payload["type"]+": "+payload["reason"]; acknowledged.set(); break
            if tree_peak>rss_mib: reason="parent-enforced sampled process-tree peak-RSS cap"; break
            if now-heartbeat>=1.:
                writer.heartbeat(); heartbeat=now
    finally:
        if result is None and process.is_alive(): process.terminate()
        grace=min(2.,max(.01,arm_seconds-(time.monotonic()-started)),max(.01,campaign_seconds-(time.monotonic()-campaign_started)))
        process.join(timeout=grace)
        if process.is_alive():
            process.kill(); process.join(timeout=2.)
            result=None; reason="worker exceeded shutdown grace and required kill"
        elif result is not None and process.exitcode!=0:
            result=None; reason=f"worker reported result but exited nonzero ({process.exitcode})"
        messages.close(); messages.join_thread()
    evidence=dict(owned_worker_pid=process.pid,worker_peak_rss_mib=worker_peak,supervisor_peak_rss_mib=peak_rss_mib(),
                  observed_tree_peak_rss_mib=tree_peak,elapsed_seconds=time.monotonic()-started,exitcode=process.exitcode,
                  owned_pids=owned_pids,per_pid_peak_rss_mib=per_pid_peaks,
                  sample_interval_seconds=.1,status="completed" if result is not None else "stopped",stop_reason=reason,
                  limitations="RSS stop guard samples known parent/worker/resource-tracker PIDs via libproc; conservative per-PID peak sum merges rusage peaks. It is not an instantaneous OS memory limit. Worker creates no descendant workers.")
    if result is None:
        writer.emit("error","stopped",writer.step,status="stopped",reason=reason,metrics={"tree_peak_rss_mib":tree_peak,"elapsed_seconds":evidence["elapsed_seconds"]},guard=evidence)
        raise GuardStopped(reason,evidence)
    result["guard"]=evidence
    return result


def self_test_guards(events_path):
    """Harmless own-child timeout and real 64MiB allocation RSS stop tests."""
    results=[]
    for mode in ("timeout","memory"):
        writer=RunEvents(events_path,run_id="guard-self-test-"+mode,commit="0"*40,config={"mode":mode},dataset={"status":"guard-test"},limitations=["Own spawned children only; no model training."])
        try:
            # Spawned NumPy worker baseline is ~35MiB; 64MiB allocation exceeds this margin.
            cap=peak_rss_mib()+80. if mode=="memory" else MAX_RSS_MIB
            supervise_worker(_guard_test_worker,(mode,),writer,.8 if mode=="timeout" else 5.,time.monotonic(),8.,cap)
            raise AssertionError("guard did not stop its test child")
        except RuntimeError as exc:
            expected="wall-time" if mode=="timeout" else "peak-RSS"
            if expected not in str(exc): raise
            records=[json.loads(line) for line in writer.path.read_text().splitlines()]
            evidence=next(row["guard"] for row in reversed(records) if row.get("run_id")==writer.run_id and "guard" in row)
            results.append(dict(mode=mode,status="PASS",reason=str(exc),guard=evidence))
    return results


def run(args):
    config=Config(steps=args.steps,batch=args.batch).validate()
    data,manifest=load_dataset(args.dataset,args.manifest)
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip()
    base=ROOT/"models/tx-t10.safetensors"; evaluator=ROOT/"models/tx-t10-e.safetensors"
    supplement=ROOT/"wasm/generated-own-deck/deck-init.safetensors"
    protected={str(p):sha(p) for p in (base,evaluator,supplement)}
    schedule=batch_sequence(data,config)
    provenance={"status":"ready","npz_path":str(args.dataset.resolve()),"npz_sha256":sha(args.dataset),
                "manifest_path":str(args.manifest.resolve()),"manifest_sha256":sha(args.manifest),
                "train_examples":len(data["train_idx"]),"val_examples":len(data["val_idx"]),
                "split_rule":manifest.get("split_rule",manifest.get("split",{})),
                "train_fingerprints":data["fingerprints"][data["train_idx"]].tolist(),
                "val_fingerprints":data["fingerprints"][data["val_idx"]].tolist(),
                "train_family_ids":data["family_ids"][data["train_idx"]].tolist(),"val_family_ids":data["family_ids"][data["val_idx"]].tolist(),
                "wrong_idx":data["wrong_idx"].tolist(),"batch_schedule_sha256":hashlib.sha256(schedule.tobytes()).hexdigest(),
                "wrong_control_total_count_mismatches":int(np.sum(data["deck_features"][:,0,4]!=data["deck_features"][data["wrong_idx"],0,4])),
                "wrong_control_total_count_note":"Tiny pilot permits different total counts; this differs from the future same-count matched comparison proposal.",
                "target_names":data["target_names"],"target_groups":data["target_groups"],"base_checkpoint_sha256":sha(base),
                "supplemental_initialization_sha256":sha(supplement),"source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HERE/"run_events.py",ROOT/"own_deck.py",ROOT/"own_deck_model.py",ROOT/"tx_model.py")}}
    preview=dict(commit=commit,config=config.as_dict(),dataset=provenance,limitations=list(LIMITATIONS),protected=protected,
                 target_train_standard_deviation=data["targets"][data["train_idx"]].std(0).tolist())
    if args.validate_only:
        print(json.dumps(preview,indent=2)); return preview
    preview["runtime"]=dict(python=platform.python_version(),numpy=np.__version__,device="cpu",torch="imported only inside owned worker")
    started=time.monotonic(); results=[]
    prior=np.broadcast_to(data["targets"][data["train_idx"]].mean(0),(len(data["val_idx"]),len(data["target_names"])))
    prior_metrics=evaluation_metrics(prior,data["targets"][data["val_idx"]],data)
    for arm in ARMS:
        run_id=f"{args.run_prefix}-{arm}-s17"
        outdir=args.runs/run_id
        outdir.mkdir(parents=True,exist_ok=False)
        writer=RunEvents(args.events,run_id=run_id,commit=commit,config={**config.as_dict(),"arm":arm},dataset=provenance,limitations=LIMITATIONS,parent_run_id=args.campaign_id)
        write_json(outdir/"manifest.json",{**preview,"run_id":run_id,"arm":arm,"prior_metrics":prior_metrics})
        np.save(outdir/"batch-schedule.npy",schedule)
        writer.emit("status","preparing",0,status="running",artifacts={"manifest":str(outdir/"manifest.json")})
        try:
            result=supervise_worker(_worker_entry,(data,config,arm,schedule,outdir,base,supplement,started),writer,
                                    config.max_arm_seconds,started,config.max_campaign_seconds,config.max_rss_mib)
            if protected!={path:sha(path) for path in protected}: raise AssertionError("protected checkpoint file changed")
            result.update(immutableBefore=protected,immutableAfter={path:sha(path) for path in protected},priorMetrics=prior_metrics)
            write_json(outdir/"result.json",result)
            writer.emit("artifact","completed",config.steps,status="completed",metrics=result["trace"][-1] | {"updates_completed":config.steps},
                        artifacts={"result":str(outdir/"result.json"),"checkpoints":result["checkpoints"]})
            results.append(result)
        except Exception as exc:
            writer.emit("error","aborted",writer.step,status="failed",reason=str(exc),metrics={"elapsed_seconds":time.monotonic()-started,"peak_rss_mib":peak_rss_mib()})
            write_json(outdir/"error.json",dict(error=str(exc),step=writer.step,guard=getattr(exc,"guard",None),immutableBefore=protected,immutableAfter={path:sha(path) for path in protected}))
            raise
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--events",type=Path,required=True)
    p.add_argument("--runs",type=Path)
    p.add_argument("--campaign-id")
    p.add_argument("--run-prefix")
    p.add_argument("--steps",type=int,default=100)
    p.add_argument("--batch",type=int,default=16)
    p.add_argument("--validate-only",action="store_true")
    p.add_argument("--self-test-guards",action="store_true")
    args=p.parse_args()
    if args.self_test_guards:
        print(json.dumps(self_test_guards(args.events),indent=2)); return
    if any(getattr(args,k) is None for k in ("dataset","manifest","runs","campaign_id","run_prefix")):
        p.error("dataset,manifest,runs,campaign-id,run-prefix are required except for guard self-tests")
    run(args)


if __name__=="__main__": main()
