"""One fixed training-batch gradient inspection; never updates or writes weights."""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent / "experiments"
RUN = ROOT / "runs/original-eb5c6d9-20261017T2356Z-original-s17"
DEFAULT = ROOT / "composition-gradient"
MODEL_SHA = "c9bb484f1923942b3c78b770dec361a08745f9a000aef82d5c809d0e9c2dbd16"
COUNTS = dict(production_forwards=1, backwards=1, optimizer_updates=0, native_calls=0, paid_jobs=0, checkpoint_writes=0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def prepare(plan_path, out):
    manifest = read(RUN / "manifest.json")
    dataset = manifest["dataset"]
    train = dataset["split_rule"]["train_idx"]
    if len(train) != 22 or len(set(train)) != 22 or len(dataset["target_names"]) != 13:
        raise ValueError("fixed22training rows and13targets required")
    production = REPO / "bots/jepa/own_deck_model.py"
    if sha(production) != MODEL_SHA:
        raise ValueError("frozen production encoder source differs")
    original = subprocess.check_output(["git", "show", manifest["commit"] + ":bots/jepa/own_deck/run_local_experiments.py"], cwd=REPO)
    if hashlib.sha256(original).hexdigest() != dataset["source_sha256"]["own_deck/run_local_experiments.py"]:
        raise ValueError("saved training source pin differs")
    for snippet in ("return z@aux_w+aux_b", "loss=((pred-labels[indices])**2).mean()"):
        if snippet not in original.decode():
            raise ValueError("saved readout/loss implementation differs")
    paths = [Path(__file__), production, REPO / "bots/jepa/model.py", REPO / "bots/jepa/own_deck.py", REPO / "bots/jepa/tx_model.py", REPO / "bots/jepa/features.py",
             Path(dataset["npz_path"]), Path(dataset["manifest_path"]), RUN / "manifest.json", RUN / "result.json", RUN / "final-deck.safetensors", RUN / "aux-head.safetensors", REPO / "bots/jepa/models/tx-t10.safetensors"]
    if plan_path.exists() or out.exists():
        raise FileExistsError("fresh plan and output paths required")
    plan = dict(schema="jepa-composition-onebatch-gradient/1", status="frozen-before-execution", source_sha256=sha(__file__),
                inputs=[dict(path=str(path), sha256=sha(path)) for path in paths], out=str(out), train_indices=train, targets=dataset["target_names"],
                expected_counts=COUNTS, batch_rows=22, context="zero state73,24masked live slots; original+disabled remaining deck rows",
                loss="((z @ saved_aux_w + saved_aux_b - saved_targets[train22]) ** 2).mean()",
                label_scaling="Same13 stored normalized target coordinates as original fit; no new normalization/heldout readout.",
                original_training_commit=manifest["commit"], original_training_source_sha256=hashlib.sha256(original).hexdigest(),
                trainable_for_gradients=["din.w", "din.b", "drole", "aux.w", "aux.b"], frozen_base="requires_grad=False; gradient absence expected",
                blocks=["din metadata rows0:50", "din pooled-identity rows50:66", "din bias", "original/remaining role", "readout weight/bias", "original metadata/hash input", "disabled remaining input", "z"],
                limits=dict(active_wall_seconds=20, cpu_seconds=20, compute_threads=1, sampled_rss_bytes=1073741824, sampling_seconds=.05),
                interpretation="One local posthoc gradient of the existing auxiliary objective; not training history, semantic quality, or objective selection. No optimizer or checkpoint output.")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    write(plan_path, plan)
    return plan


class Guard:
    def __enter__(self):
        self.start = time.monotonic()
        self.cpu = resource.getrusage(resource.RUSAGE_SELF)
        self.stop = threading.Event()
        self.samples = 0
        def halt(signum, frame):
            raise RuntimeError("onebatch20second/1GiB budget reached")
        for sig in (signal.SIGALRM, signal.SIGXCPU, signal.SIGUSR1):
            signal.signal(sig, halt)
        signal.setitimer(signal.ITIMER_REAL, 20)
        resource.setrlimit(resource.RLIMIT_CPU, (19, 20))
        def monitor():
            while not self.stop.wait(.05):
                self.samples += 1
                if self.rss() > 1073741824:
                    os.kill(os.getpid(), signal.SIGUSR1)
                    break
        self.thread = threading.Thread(target=monitor, daemon=True)
        self.thread.start()
        return self

    def rss(self):
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)

    def receipt(self):
        current = resource.getrusage(resource.RUSAGE_SELF)
        return dict(wall_seconds=time.monotonic()-self.start, cpu_seconds=current.ru_utime+current.ru_stime-self.cpu.ru_utime-self.cpu.ru_stime,
                    peak_rss_bytes=self.rss(), samples=self.samples, threads=1, limitation="Sampled process high-water RSS, not instantaneous OS memory reservation; NumPy/Torch imports inside guard.")

    def __exit__(self, *args):
        signal.setitimer(signal.ITIMER_REAL, 0)
        self.stop.set()
        self.thread.join(timeout=.2)


def execute(plan_path, out):
    counts = {name: 0 for name in COUNTS}
    out.mkdir(parents=True, exist_ok=False)
    guard = Guard()
    try:
        with guard:
            plan = read(plan_path)
            if sha(__file__) != plan["source_sha256"] or str(out) != plan["out"]:
                raise ValueError("source/output differs from frozen plan")
            for item in plan["inputs"]:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("protected input changed: " + item["path"])
            import numpy as np
            import torch
            sys.path.insert(0, str(REPO / "bots/jepa"))
            import model as M
            import own_deck_model as D
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            train = np.asarray(plan["train_indices"], np.int64)
            with np.load(ROOT / "data/real-decks.npz", allow_pickle=False) as pack:
                if pack["train_idx"].tolist() != train.tolist():
                    raise ValueError("training partition differs")
                features = pack["deck_features"][train].copy()
                targets = pack["targets"][train].copy()
            weights, meta = D.load_extended(REPO / "bots/jepa/models/tx-t10.safetensors", RUN / "final-deck.safetensors")
            head, _ = M.load_safetensors(RUN / "aux-head.safetensors")
            extras = set(D.supplemental_shapes())
            w = {name: torch.tensor(value, dtype=torch.float32, requires_grad=name in extras) for name, value in weights.items()}
            aux_w, aux_b = (torch.tensor(head[name], dtype=torch.float32, requires_grad=True) for name in ("aux.w", "aux.b"))
            if features.shape != (22,2,207) or targets.shape != (22,13) or tuple(aux_w.shape) != (96,13) or tuple(aux_b.shape) != (13,):
                raise ValueError("saved minibatch/readout shape differs")
            deck = torch.tensor(features, requires_grad=True)
            labels = torch.tensor(targets)
            counts["production_forwards"] += 1
            z, _ = D.run_torch(w, meta, torch.zeros(22,73), torch.zeros(22,24,dtype=torch.long), torch.zeros(22,24,21), torch.zeros(22,24), own_deck=deck)
            z.retain_grad()
            pred = z@aux_w+aux_b
            loss = ((pred-labels)**2).mean()
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("nonfinite saved objective")
            counts["backwards"] += 1
            loss.backward()
            def summary(value):
                if value is None:
                    return dict(present=False)
                a = value.detach().numpy().astype(np.float64)
                if not np.isfinite(a).all():
                    raise FloatingPointError("nonfinite gradient")
                return dict(present=True, coordinates=int(a.size), nonzero_exact=int(np.count_nonzero(a)), nonzero_above_1e_minus12=int(np.count_nonzero(abs(a)>1e-12)),
                            l2=float(np.linalg.norm(a)), rms=float(np.sqrt(np.mean(a*a))), max_absolute=float(abs(a).max()))
            gradients = {"din_metadata": summary(w["din.w"].grad[:50]), "din_pooled_identity": summary(w["din.w"].grad[50:]), "din_bias": summary(w["din.b"].grad),
                         "role_original": summary(w["drole"].grad[0]), "role_remaining_disabled": summary(w["drole"].grad[1]), "readout_weight": summary(aux_w.grad), "readout_bias": summary(aux_b.grad),
                         "input_original_metadata": summary(deck.grad[:,0,:50]), "input_original_hashed_identity": summary(deck.grad[:,0,50:]), "input_remaining_disabled": summary(deck.grad[:,1]), "z": summary(z.grad)}
            frozen = [name for name in w if name not in extras]
            if any(w[name].grad is not None for name in frozen):
                raise AssertionError("frozen base unexpectedly received parameter gradients")
            if any(not np.array_equal(w[name].detach().numpy(), value) for name,value in weights.items()) or not np.array_equal(aux_w.detach().numpy(),head["aux.w"]) or not np.array_equal(aux_b.detach().numpy(),head["aux.b"]):
                raise AssertionError("gradient-only pass changed parameter values")
            for item in plan["inputs"]:
                if sha(item["path"]) != item["sha256"]:
                    raise AssertionError("protected file changed")
            if counts != COUNTS:
                raise AssertionError("oneforward/onebackward allocation differs")
            input_scope = {}
            for name,role,start,stop in (("original_metadata",0,0,50),("original_hashed_identity",0,50,207),("remaining_disabled",1,0,207)):
                value = features[:,role,start:stop]
                input_scope[name] = dict(columns=stop-start, columns_varying_across_train22=int(np.count_nonzero(np.ptp(value,axis=0))),
                                         columns_nonzero_in_any_row=int(np.count_nonzero(np.any(value!=0,axis=0))),
                                         enabled_status_values=np.unique(features[:,role,2]).tolist(), known_status_values=np.unique(features[:,role,3]).tolist())
            result = dict(schema=plan["schema"], status="completed", plan_sha256=sha(plan_path), source_sha256=sha(__file__), counts=counts, train_indices=plan["train_indices"],
                          loss=float(loss.detach()), gradient_blocks=gradients, input_scope=input_scope, frozen_base_tensors=len(frozen), frozen_base_parameter_gradients_absent=True,
                          all_parameters_unchanged=True, all_protected_files_unchanged=True, runtime=dict(python=sys.version.split()[0],numpy=np.__version__,torch=torch.__version__), guard=guard.receipt(),
                          caveats=["Current local gradient, not saved training-gradient history or proof of semantic quality.","Input derivatives use continuous feature coordinates, not native legal card substitutions; inactive/constant inputs and feature scales matter.","Remaining role is a disabled unknown token; its gradients are not a live remaining-pile representation."])
            if result["guard"]["peak_rss_bytes"] > 1073741824:
                raise RuntimeError("1GiB memory allowance exceeded")
            write(out / "result.json", result)
        receipt = dict(status="completed", plan_sha256=sha(plan_path), source_sha256=sha(__file__), result_sha256=sha(out / "result.json"), counts=counts, guard=guard.receipt())
        write(out / "receipt.json", receipt)
        print(json.dumps(receipt, indent=2))
    except BaseException as exc:
        write(out / "error.json", dict(error=repr(exc), counts=counts, guard=guard.receipt()))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", type=Path, default=DEFAULT / "plan.json")
    parser.add_argument("--out", type=Path, default=DEFAULT / "run-1")
    args = parser.parse_args()
    if args.prepare:
        plan = prepare(args.plan, args.out)
        print(json.dumps(dict(plan=str(args.plan),plan_sha256=sha(args.plan),source_sha256=plan["source_sha256"],expected_counts=COUNTS),indent=2))
    else:
        execute(args.plan, args.out)


if __name__ == "__main__":
    main()
