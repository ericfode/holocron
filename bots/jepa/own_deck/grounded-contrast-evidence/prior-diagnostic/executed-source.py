"""Grounded contrast preparation and bounded saved-pilot diagnostics.

No optimizer is invoked by --diagnose-prior. New fits require the coordinating
root's separate GO. Old pilot source, datasets and checkpoints are read-only.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_local_experiments as G
from run_events import RunEvents

DIAGNOSTIC_SCHEMA = "jepa-prior-pilot-diagnostic/1"
DIAGNOSTIC_MAX_BATCHES = 12
DIAGNOSTIC_MAX_SECONDS = 20.


def rms(value):
    value = np.asarray(value, np.float64)
    return float(np.sqrt(np.mean(value ** 2))) if value.size else 0.


def gradient_summary(model):
    groups = {}
    for name, parameter in model.named_parameters():
        group = name.split(".")[0]
        record = groups.setdefault(group, dict(parameters=0, gradient_coordinates=0, nonzero_coordinates=0, squared_norm=0.))
        record["parameters"] += parameter.numel()
        if parameter.grad is not None:
            gradient = parameter.grad.detach().numpy().astype(np.float64)
            record["gradient_coordinates"] += gradient.size
            record["nonzero_coordinates"] += int(np.count_nonzero(abs(gradient) > 1e-12))
            record["squared_norm"] += float(np.sum(gradient ** 2))
    for record in groups.values():
        record["l2"] = float(np.sqrt(record.pop("squared_norm")))
        record["rms"] = record["l2"] / np.sqrt(max(record["gradient_coordinates"], 1))
        record["nonzero_fraction"] = record["nonzero_coordinates"] / max(record["parameters"], 1)
    return groups


def _diagnostic_worker(messages, acknowledged, base, outdir):
    writer = G.WorkerEvents(messages)
    started = time.monotonic()
    counts = dict(batches=0, forwards=0, backwards=0, optimizer_updates=0)
    report = dict(schema=DIAGNOSTIC_SCHEMA, status="started", counters=counts, batches=[],
                  interpretation="Posthoc saved-model gradient and label-free intervention diagnostic, not a validation search or training run.")
    stop = threading.Event()
    def heartbeat():
        while not stop.wait(1.):
            writer.report_rss()
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        import torch
        import train_structured_transition as S
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        data = S.load_dataset(base / "supported-transitions.npz", base / "supported-transitions.manifest.json")
        checkpoint = base / "fit-2/correct-ir.npz"
        protected_before = G.sha(checkpoint)
        model = S.make_model(torch, data["context"].shape[1])
        with np.load(checkpoint, allow_pickle=False) as weights:
            model.load_state_dict({name: torch.as_tensor(weights[name].copy()) for name in weights.files}, strict=True)
        model.eval()
        initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
        bank = S.torch_bank(torch, data["banks"]["correct-ir"])
        query = torch.as_tensor(data["query"])
        copies = torch.as_tensor(data["counts"])
        captures = {}
        intervention = {"zero_program": False}

        def head_hook(module, arguments):
            fusion = arguments[0]
            if intervention["zero_program"]:
                fusion = torch.cat((torch.zeros_like(fusion[:, :32]), fusion[:, 32:]), -1)
            captures["fusion"] = fusion
            if fusion.requires_grad:
                fusion.retain_grad()
            return (fusion,)
        handle = model.head[0].register_forward_pre_hook(head_hook)

        def begin(name, backward):
            if counts["batches"] >= DIAGNOSTIC_MAX_BATCHES or time.monotonic() - started >= DIAGNOSTIC_MAX_SECONDS:
                raise RuntimeError("diagnostic operation/time allocation exhausted")
            counts["batches"] += 1
            counts["forwards"] += 1
            if backward:
                counts["backwards"] += 1
            row = dict(batch=counts["batches"], name=name, backward=backward)
            report["batches"].append(row)
            G.write_json(outdir / "partial.json", report)
            return row

        train = data["train"]
        for name, head in (("training-objective", None), ("source-use-head", 0), ("damage-head", 3)):
            row = begin(name, True)
            model.zero_grad(set_to_none=True)
            context = torch.tensor(data["context"][train], requires_grad=True)
            target = torch.as_tensor(data["targets"][train])
            mask = torch.as_tensor(data["mask"][train]).clone()
            if head is not None:
                selected = torch.zeros_like(mask)
                selected[:, head] = mask[:, head]
                mask = selected
            logits = model(context, query[train], copies[train], bank)
            loss = S.loss_fn(torch, logits, target, mask)
            loss.backward()
            fusion = captures["fusion"]
            row.update(loss=float(loss.detach()), observed_coordinates=int(mask.sum()),
                       module_gradients_preclip=gradient_summary(model),
                       fusion_activation_rms={label: rms(fusion.detach().numpy()[:, start:start + 16]) for label, start in (("query", 0), ("bag", 16), ("context", 32))},
                       fusion_gradient_rms={label: rms(fusion.grad.numpy()[:, start:start + 16]) for label, start in (("query", 0), ("bag", 16), ("context", 32))},
                       input_gradient_rms_physical_units={column: rms(context.grad.numpy()[:, j]) / (30. if column.endswith("_per30") else 1.) for j, column in enumerate(data["manifest"]["context_feature_names"])})
            writer.emit("metric", name, counts["batches"], metrics=dict(loss=row["loss"], batches=counts["batches"], backwards=counts["backwards"], optimizer_updates=0))

        all_context = torch.as_tensor(data["context"])
        def forward(name, context=all_context, selected_bank=bank, zero=False):
            row = begin(name, False)
            intervention["zero_program"] = zero
            with torch.no_grad():
                logits = model(context, query, copies, selected_bank)
            intervention["zero_program"] = False
            if not torch.isfinite(logits).all():
                raise FloatingPointError("nonfinite diagnostic output")
            return row, logits.numpy().copy(), captures["fusion"].numpy().copy()

        baseline_row, baseline, fusion = forward("saved-correct-baseline")
        baseline_row.update(query_rms=rms(fusion[:, :16]), bag_rms=rms(fusion[:, 16:32]), context_rms=rms(fusion[:, 32:]),
                            max_abs_bag_minus_query_over60=float(abs(fusion[:, 16:32] - fusion[:, :16] / 60).max()),
                            query_between_rows_rms=rms(fusion[:, :16] - fusion[:, :16].mean(0)),
                            context_between_rows_rms=rms(fusion[:, 32:] - fusion[:, 32:].mean(0)))
        sensitivity = []
        def compare(row, output):
            delta = output - baseline
            row.update(logit_delta_rms=rms(delta), logit_delta_max=float(abs(delta).max()),
                       per_head_logit_delta_rms={name: rms(delta[:, j]) for j, name in enumerate(S.TARGETS)},
                       labels_used=False)
            sensitivity.append(row.copy())
        row, output, _ = forward("zero-query-and-bag-at-fusion", zero=True)
        compare(row, output)
        permutation = data["wrong_permutation"]
        swapped = {name: value[permutation] for name, value in bank.items()}
        row, output, _ = forward("swap-two-known-programs-same-context", selected_bank=swapped)
        compare(row, output)
        columns = data["manifest"]["context_feature_names"]
        exhausted = data["context"].copy()
        exhausted[:, columns.index("source_exhausted")] = 1 - exhausted[:, columns.index("source_exhausted")]
        row, output, _ = forward("flip-source-exhausted-public-input", context=torch.as_tensor(exhausted))
        compare(row, output)
        hp = data["context"].copy()
        unit = hp[:, columns.index("chosen_unit")] == 1
        remaining_index = columns.index("chosen_remaining_hp_per30")
        new_remaining = np.where(hp[unit, remaining_index] * 30 > 1.5, 1., 2.)
        hp[unit, remaining_index] = new_remaining / 30
        hp[unit, columns.index("chosen_damage_per30")] = hp[unit, columns.index("chosen_hp_per30")] - new_remaining / 30
        row, output, _ = forward("unit-remaining-hp1-versus2-public-input", context=torch.as_tensor(hp))
        row["changed_rows"] = int(unit.sum())
        compare(row, output)
        amount = {name: value.clone() for name, value in bank.items()}
        edited = 0
        for slot, code in enumerate(data["codes"]):
            semantic, _ = S.program_tokens(data["manifest"]["programs"][code])
            for position, token in enumerate(semantic):
                if token.path == ("effect", "amount", "value"):
                    amount["scalars"][slot, position] = torch.tensor([.2, np.log(3.) / 10], dtype=torch.float32)
                    edited += 1
        row, output, _ = forward("known-amount1-to2-no-native-mutant-label", selected_bank=amount)
        row["edited_program_literals"] = edited
        compare(row, output)
        handle.remove()
        unchanged = all(torch.equal(initial[name], value) for name, value in model.state_dict().items())
        if not unchanged or protected_before != G.sha(checkpoint):
            raise AssertionError("saved diagnostic changed weights")
        report.update(status="completed", counters=counts, elapsed_seconds=time.monotonic() - started,
                      weights_unchanged=unchanged, protected_checkpoint_sha256_before=protected_before,
                      protected_checkpoint_sha256_after=G.sha(checkpoint), sensitivities=sensitivity,
                      source_sha256=G.sha(__file__), prior_source_sha256=G.sha(HERE / "train_structured_transition.py"),
                      dataset_sha256=G.sha(base / "supported-transitions.npz"),
                      effect_of_scaling="Old token sum/64, synthetic one-copy bag=query/60 exactly, and HP inputs/30. Physical-input gradients divide normalized-coordinate gradients by30 for HP/damage columns.",
                      limits=dict(max_batches=12, max_seconds=20, cpu_threads=1, max_rss_mib=2048, optimizer_updates=0, native_calls=0),
                      caveats=["Instantaneous post-training gradients do not reconstruct training history or prove which program semantics were learned.", "Zero/swap/quantity interventions are unlabelled synthetic feature edits, not native counterfactual transition labels.", "Parameter gradient size depends on scale/dimension; RMS/nonzero coverage and input sensitivity accompany L2 norms."])
        G.write_json(outdir / "worker-result.json", report)
        messages.put(("result", G.json_primitives(report)))
        acknowledged.wait(timeout=3.)
    except BaseException as exc:
        report.update(status="failed", error=str(exc), counters=counts, elapsed_seconds=time.monotonic() - started)
        G.write_json(outdir / "worker-error.json", report)
        messages.put(("failure", dict(reason=str(exc), type=type(exc).__name__, step=counts["batches"])))
        acknowledged.wait(timeout=3.)
    finally:
        stop.set()
        thread.join(timeout=2.)


def diagnose_prior(base, outdir, events):
    outdir.mkdir(parents=True, exist_ok=False)
    writer = RunEvents(events, run_id="prior-pilot-gradient-diagnostic-20261018", commit="bd454609299544a37ec636e32d241d70fd492339",
                       config=dict(max_batches=12, max_seconds=20, cpu_threads=1, optimizer_updates=0, native_calls=0),
                       dataset=dict(base=str(base), checkpoint_sha256=G.sha(base / "fit-2/correct-ir.npz")),
                       limitations=["Posthoc diagnostic; no optimizer, checkpoint selection or held-out search."])
    started = time.monotonic()
    try:
        report = G.supervise_worker(_diagnostic_worker, (base, outdir), writer, 20., started, 20., 2048.)
        G.write_json(outdir / "receipt.json", report)
        writer.emit("artifact", "completed", report["counters"]["batches"], status="completed", artifacts=dict(receipt=str(outdir / "receipt.json")))
        return report
    except BaseException as exc:
        G.write_json(outdir / "guard-error.json", dict(error=str(exc), guard=getattr(exc, "guard", None)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose-prior", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    if args.diagnose_prior is None:
        parser.error("only explicit bounded saved-prior diagnostic is implemented here")
    diagnose_prior(args.diagnose_prior, args.out, args.events)


if __name__ == "__main__":
    main()
