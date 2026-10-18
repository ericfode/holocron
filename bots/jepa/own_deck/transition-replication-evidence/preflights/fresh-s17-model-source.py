"""Grounded contrast preparation and bounded saved-pilot diagnostics.

No optimizer is invoked by --diagnose-prior. New fits require the coordinating
root's separate GO. Old pilot source, datasets and checkpoints are read-only.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_key] = "1"

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
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

CONTRAST_SCHEMA = "jepa-grounded-contrast/1"
CONTRAST_ARMS = ("correct-ir", "id-only", "wrong-ir", "context-only")
MAX_PROGRAMS, MAX_TOKENS, MAX_PATH, MAX_CANDIDATES, HIDDEN = 16, 256, 24, 8, 16
TARGET_NAMES = ("source_use", "target_allowed", "cost_resource", "damage_delta", "source_exhausted_after",
                "target_exhausted_delta", "shield_delta", "xp_delta", "target_defeated", "followup_source_offered", "terminal")
BINARY_HEADS = (0, 1, 4, 8, 9, 10)
PROPOSED_ALLOCATION = dict(seed=17, arms=list(CONTRAST_ARMS), max_updates_per_arm=600, max_updates=2400,
                           max_native_applies=2048, max_collection_roots=168, max_collection_fit_seconds=180,
                           max_parameters=32768, cpu_workers=1, sampled_rss_stop_bytes=2147483648,
                           final_validation_batches=8, postfit_usage_batches=2, abi_embedding_batches=4,
                           constant_head_auxiliary_weight=.1, paid_jobs=0, paid_spend_usd=0)
FIT_CONFIG = dict(PROPOSED_ALLOCATION, batch_size=16, learning_rate=.003, weight_decay=.0001,
                  optimizer="AdamW", gradient_clip_l2=1., batch_seed=18, wrong_train_seed=19,
                  wrong_eval_seed=20, self_query_auxiliary_weight=.1,
                  binary_class_weight_bounds=[.25, 5.], continuous_scale_floor=1.,
                  primary_min_observed_roots=2, auxiliary_min_observed_roots=1,
                  primary_rule="at least two distinct training labels and two observed training roots",
                  source_self_policy="slot7 auxiliary0.1; primary candidate slots0..6; no candidate pooling",
                  wrong_eval_rule="heldout identities swap each other; seen identities draw from training programs excluding equivalent group",
                  train_input_scaling="training roots and primary candidates only; known numeric columns centered/std floor1; booleans unchanged",
                  heldout_cells=["program-held", "state-held", "joint-held"], primary_cell="joint-held")
CANDIDATE_NUMERIC_KNOWN = {8: 15, 9: 16, 10: 17, 11: 18, 13: 20, 14: 21}


def structural_tokens(raw):
    """Typed categorical IR structure; no execution, text encoder or card identity.

    The caller must supply a reviewed, whole-card-native-admitted program. The
    full structural data is retained except the ability's display title. This
    reader represents portable IR; it does not expand rules-engine admission.
    """
    if not isinstance(raw, dict) or raw.get("trigger") != "action" or not isinstance(raw.get("effect"), dict):
        raise ValueError("reviewed action ability required")
    output = []
    forbidden = {"sourcePath", "sourceHash", "setCode", "internalName", "label", "method"}
    def add(path, kind, value):
        if len(path) > MAX_PATH or len(output) >= MAX_TOKENS:
            raise ValueError("typed structure exceeds pilot cap; no truncation")
        output.append((tuple(path), kind, value))
    def visit(value, path):
        if isinstance(value, dict):
            if forbidden & set(value):
                raise ValueError("provenance/display binding fields are not semantic inputs")
            add(path, "node", "object")
            for key in sorted(value):
                if not path and key == "title":
                    continue
                visit(value[key], path + (key,))
        elif isinstance(value, list):
            add(path, "node", "ordered-list")
            add(path, "length", len(value))
            for index, child in enumerate(value):
                visit(child, path + (index,))
        elif type(value) is bool:
            add(path, "boolean", value)
        elif type(value) in (int, float):
            if abs(value) > 65535 or not np.isfinite(value):
                raise ValueError("nonfinite/out-of-bound numeric literal")
            add(path, "number", float(value))
        elif isinstance(value, str):
            # Symbols are categorical atoms, not words processed as text.
            import re
            if len(value) > 96 or re.fullmatch(r"[A-Z0-9]+_[0-9]{3,}", value):
                raise ValueError("unreviewed free text or card-code literal")
            add(path, "enum", value)
        elif value is None:
            add(path, "null", "null")
        else:
            raise ValueError("untyped IR value")
    visit(raw, ())
    return tuple(output)


def freeze_symbols(programs):
    """Schema atoms may be reviewed before fitting; no labels/IDs enter vocab."""
    tokens = [token for program in programs for token in structural_tokens(program)]
    edge = lambda key: ("index:" if type(key) is int else "key:") + str(key)
    paths = ("PAD", "UNKNOWN", *sorted({edge(k) for path, _, _ in tokens for k in path}))
    types = ("PAD", "UNKNOWN", "node", "length", "boolean", "number", "enum", "null")
    values = ("PAD", "UNKNOWN", "NUMBER", *sorted({kind + ":" + str(value) for _, kind, value in tokens if kind not in ("number", "length")}))
    return dict(path=list(paths), type=list(types), value=list(values))


def encode_program_bank(records, symbols, train_codes, numeric_scale=1.):
    """Fixed tensors; ID indices are consumed ONLY by the explicit ID control."""
    if not 0 < numeric_scale or not np.isfinite(numeric_scale) or len(records) > MAX_PROGRAMS:
        raise ValueError("invalid numeric scale/program cap")
    codes = [record["code"] for record in records]
    if len(set(codes)) != len(codes) or len(set(train_codes)) != len(train_codes):
        raise ValueError("duplicate program identities")
    paths = {value: i for i, value in enumerate(symbols["path"])}
    types = {value: i for i, value in enumerate(symbols["type"])}
    values = {value: i for i, value in enumerate(symbols["value"])}
    bank = dict(path_ids=np.zeros((MAX_PROGRAMS, MAX_TOKENS, MAX_PATH), np.int64),
                path_lengths=np.zeros((MAX_PROGRAMS, MAX_TOKENS), np.int64),
                type_ids=np.zeros((MAX_PROGRAMS, MAX_TOKENS), np.int64),
                value_ids=np.zeros((MAX_PROGRAMS, MAX_TOKENS), np.int64),
                numeric=np.zeros((MAX_PROGRAMS, MAX_TOKENS, 2), np.float32),
                token_mask=np.zeros((MAX_PROGRAMS, MAX_TOKENS), np.float32),
                slot_mask=np.zeros(MAX_PROGRAMS, np.float32), status=np.zeros((MAX_PROGRAMS, 5), np.float32),
                identity_indices=np.zeros(MAX_PROGRAMS, np.int64))
    for slot, record in enumerate(records):
        bank["slot_mask"][slot] = 1
        bank["status"][slot, 0] = 1
        code = record["code"]
        bank["identity_indices"][slot] = train_codes.index(code) + 1 if code in train_codes else 0
        for position, (path, kind, value) in enumerate(structural_tokens(record["raw_ability"])):
            edges = [("index:" if type(k) is int else "key:") + str(k) for k in path]
            if any(edge not in paths for edge in edges):
                raise ValueError("unreviewed path symbol")
            key = "NUMBER" if kind in ("number", "length") else kind + ":" + str(value)
            if key not in values:
                raise ValueError("unreviewed value symbol")
            bank["path_ids"][slot, position, :len(path)] = [paths[edge] for edge in edges]
            bank["path_lengths"][slot, position] = len(path)
            bank["type_ids"][slot, position] = types[kind]
            bank["value_ids"][slot, position] = values[key]
            bank["token_mask"][slot, position] = 1
            if kind in ("number", "length"):
                bank["numeric"][slot, position] = (value / numeric_scale, np.sign(value) * np.log1p(abs(value)))
    return codes, bank


def fit_input_scaling(context, candidates, train_indices, primary_mask):
    """Known numerical public inputs only, fitted without held-out distributions."""
    centers, scales = np.zeros(2), np.ones(2)
    centers[0] = np.asarray(context)[train_indices, 0].mean()
    scales[0] = max(1., float(np.asarray(context)[train_indices, 0].std()))
    candidate_center, candidate_scale = np.zeros(26), np.ones(26)
    for column, known in CANDIDATE_NUMERIC_KNOWN.items():
        values = candidates[train_indices, :, column]
        mask = (primary_mask[train_indices] > 0) & (candidates[train_indices, :, known] > 0)
        if mask.any():
            candidate_center[column] = float(values[mask].mean())
            candidate_scale[column] = max(1., float(values[mask].std()))
    return dict(context_center=centers.tolist(), context_scale=scales.tolist(),
                candidate_center=candidate_center.tolist(), candidate_scale=candidate_scale.tolist(),
                numeric_known_columns={str(k): v for k, v in CANDIDATE_NUMERIC_KNOWN.items()},
                fit_rows=np.asarray(train_indices).tolist(), fit_candidates="primary slots0..6 only")


def apply_input_scaling(context, candidates, scaling):
    x = ((np.asarray(context, np.float32) - np.asarray(scaling["context_center"], np.float32)) /
         np.asarray(scaling["context_scale"], np.float32))
    c = np.asarray(candidates, np.float32).copy()
    for column, known in CANDIDATE_NUMERIC_KNOWN.items():
        c[..., column] = ((c[..., column] - scaling["candidate_center"][column]) /
                          scaling["candidate_scale"][column]) * c[..., known]
    if not np.isfinite(x).all() or not np.isfinite(c).all():
        raise ValueError("nonfinite scaled inputs")
    return x, c


def fit_head_scaling(source, source_mask, allowed, allowed_mask, targets, masks, train_indices, primary_mask=None):
    """All fit decisions use training labels only; no constant head dominates."""
    result = dict(primary=[], auxiliary=[], scale=[], center=[], class_weights=[], support=[], observed_roots=[], variation=[])
    for head in range(len(TARGET_NAMES)):
        values, known = (source, source_mask) if head == 0 else ((allowed, allowed_mask) if head == 1 else (targets[..., head], masks[..., head]))
        known = np.asarray(known).copy()
        if head != 0 and primary_mask is not None:
            known *= primary_mask
        train_known = known[train_indices].astype(bool)
        observed_roots = int(np.sum(train_known.any(-1))) if train_known.ndim > 1 else int(train_known.sum())
        observed = np.asarray(values)[train_indices][train_known].astype(np.float64)
        if not np.isfinite(observed).all():
            raise ValueError("nonfinite known training label")
        unique = np.unique(observed)
        result["support"].append(int(len(observed)))
        result["observed_roots"].append(observed_roots)
        result["variation"].append(unique.tolist())
        if len(unique) > 1 and observed_roots >= FIT_CONFIG["primary_min_observed_roots"]:
            result["primary"].append(head)
        elif len(unique) >= 1:
            result["auxiliary"].append(head)
        binary = head in BINARY_HEADS
        if binary and not np.isin(observed, [0, 1]).all():
            raise ValueError("nonbinary observed classifier label")
        result["center"].append(0. if binary or not len(observed) else float(observed.mean()))
        result["scale"].append(1. if binary or not len(observed) else max(1., float(observed.std())))
        if binary and len(unique) == 2:
            counts = [int(np.sum(observed == value)) for value in (0, 1)]
            result["class_weights"].append([float(np.clip(len(observed) / (2 * count), .25, 5.)) for count in counts])
        else:
            result["class_weights"].append([1., 1.])
    return result


def fit_numeric_scale(records, train_codes):
    values = [value for record in records if record["code"] in train_codes
              for _, kind, value in structural_tokens(record["raw_ability"]) if kind in ("number", "length")]
    return max(1., float(np.std(values))) if values else 1.


def draw_wrong_programs(correct, train_program_indices, group_ids, rng):
    """Seeded per-example draws, never a fixed invertible ID permutation."""
    choices = np.asarray(train_program_indices, np.int64)
    result = []
    for index in np.asarray(correct, np.int64).flat:
        eligible = [candidate for candidate in choices if group_ids[candidate] != group_ids[index]]
        if not eligible:
            raise ValueError("wrong-IR control requires a distinct training program group")
        result.append(int(rng.choice(eligible)))
    return np.asarray(result, np.int64).reshape(np.asarray(correct).shape)


def training_program_bank(bank, train_program_indices):
    result = {name: value.copy() for name, value in bank.items()}
    keep = np.zeros(MAX_PROGRAMS, bool)
    keep[np.asarray(train_program_indices, np.int64)] = True
    for value in result.values():
        value[~keep] = 0
    return result


def balanced_head_loss(torch, source_logits, branch_logits, labels, scaling):
    """Mean within root, then across roots, then across varying native heads."""
    losses, self_losses = {}, []
    for head in range(len(TARGET_NAMES)):
        if head == 0:
            prediction, target, known = source_logits, labels["source_use"], labels["source_use_mask"]
        elif head == 1:
            prediction, target, known = branch_logits[..., head], labels["candidate_allowed"], labels["candidate_allowed_mask"]
        else:
            prediction, target, known = branch_logits[..., head], labels["targets"][..., head], labels["target_mask"][..., head]
        known = known.to(prediction.dtype)
        self_known = known * (1 - labels["primary_candidate_mask"]) if head != 0 else None
        if head != 0:
            known = known * labels["primary_candidate_mask"]
        if head in BINARY_HEADS:
            element = torch.nn.functional.binary_cross_entropy_with_logits(prediction, target, reduction="none")
            negative, positive = scaling["class_weights"][head]
            element = element * (negative * (1 - target) + positive * target)
        else:
            normalized = (target - scaling["center"][head]) / scaling["scale"][head]
            element = torch.nn.functional.smooth_l1_loss(prediction, normalized, reduction="none")
        if prediction.ndim > 1:
            support = known.sum(-1)
            values = (element * known).sum(-1) / torch.clamp(support, min=1)
            valid_roots = support > 0
        else:
            values, valid_roots = element, known > 0
        if bool(valid_roots.any()):
            losses[head] = values[valid_roots].mean()
        if self_known is not None and bool((self_known.sum(-1) > 0).any()):
            support = self_known.sum(-1)
            value = (element * self_known).sum(-1) / torch.clamp(support, min=1)
            self_losses.append(value[support > 0].mean())
    primary = [losses[head] for head in scaling["primary"] if head in losses]
    auxiliary = [losses[head] for head in scaling["auxiliary"] if head in losses]
    zero = source_logits.sum() * 0
    total = torch.stack(primary).mean() if primary else zero
    if auxiliary:
        total = total + .1 * torch.stack(auxiliary).mean()
    if self_losses:
        total = total + .1 * torch.stack(self_losses).mean()
    return total, losses


def make_contrast_model(torch, symbols, context_width=2, candidate_width=26):
    """No recurrent padding work or one-copy deck branch in this action model."""
    nn = torch.nn
    class GroundedContrast(nn.Module):
        def __init__(self):
            super().__init__()
            self.edge_embedding = nn.Embedding(len(symbols["path"]), HIDDEN, padding_idx=0)
            self.depth_gate = nn.Parameter(torch.randn(MAX_PATH, HIDDEN) / np.sqrt(HIDDEN))
            self.type_embedding = nn.Embedding(len(symbols["type"]), HIDDEN, padding_idx=0)
            self.value_embedding = nn.Embedding(len(symbols["value"]), HIDDEN, padding_idx=0)
            self.numeric_projection = nn.Linear(2, HIDDEN)
            self.leaf = nn.Sequential(nn.Linear(2 * HIDDEN, 32), nn.Tanh(), nn.Linear(32, HIDDEN), nn.Tanh())
            self.program_projection = nn.Sequential(nn.Linear(HIDDEN + 5, HIDDEN), nn.LayerNorm(HIDDEN))
            self.identity_embedding = nn.Embedding(MAX_PROGRAMS + 1, HIDDEN, padding_idx=0)
            self.unavailable = nn.Parameter(torch.zeros(HIDDEN))
            self.context_projection = nn.Sequential(nn.Linear(context_width, HIDDEN), nn.Tanh(), nn.LayerNorm(HIDDEN))
            self.candidate_projection = nn.Sequential(nn.Linear(candidate_width, HIDDEN), nn.Tanh(), nn.LayerNorm(HIDDEN))
            self.source_head = nn.Sequential(nn.Linear(3 * HIDDEN, 32), nn.Tanh(), nn.Linear(32, 1))
            self.branch_head = nn.Sequential(nn.Linear(5 * HIDDEN, 32), nn.Tanh(), nn.Linear(32, len(TARGET_NAMES)))

        def encode_program_bank(self, bank):
            coordinates = torch.nonzero(bank["token_mask"] * bank["slot_mask"].unsqueeze(-1), as_tuple=False)
            program_index, token_index = coordinates[:, 0], coordinates[:, 1]
            ids = bank["path_ids"][program_index, token_index]
            # Depth×key PRODUCT retains which key occurs at each depth.
            edges = self.edge_embedding(ids) * self.depth_gate
            positions = torch.arange(MAX_PATH, device=ids.device)
            path_mask = positions < bank["path_lengths"][program_index, token_index].unsqueeze(-1)
            path = (edges * path_mask.unsqueeze(-1)).sum(-2)
            value = self.type_embedding(bank["type_ids"][program_index, token_index]) + self.value_embedding(bank["value_ids"][program_index, token_index]) + self.numeric_projection(bank["numeric"][program_index, token_index])
            leaves = self.leaf(torch.cat((path, value), -1))
            pooled = torch.zeros((MAX_PROGRAMS, HIDDEN), dtype=leaves.dtype, device=leaves.device).index_add(0, program_index, leaves)
            count = torch.clamp(bank["token_mask"].sum(1, keepdim=True), min=1)
            mean = pooled / count
            program = self.program_projection(torch.cat((mean, bank["status"]), -1))
            return program * bank["slot_mask"].unsqueeze(-1)

        def forward(self, context, candidates, program_indices, bank, arm="correct-ir", zero_program=False, return_program_bank=False):
            semantic = self.encode_program_bank(bank)
            identity = self.identity_embedding(bank["identity_indices"])
            if arm in ("correct-ir", "wrong-ir"):
                program = semantic[program_indices]
            elif arm == "id-only":
                program = identity[program_indices]
                program = torch.nn.functional.layer_norm(program, (HIDDEN,))
            elif arm == "context-only":
                program = self.unavailable.expand(len(context), -1)
            else:
                raise ValueError("unreviewed contrast arm")
            if zero_program:
                program = torch.zeros_like(program)
            state = self.context_projection(context)
            candidate = self.candidate_projection(candidates)
            source = self.source_head(torch.cat((program, state, program * state), -1)).squeeze(-1)
            p = program[:, None, :].expand_as(candidate)
            s = state[:, None, :].expand_as(candidate)
            branch = self.branch_head(torch.cat((p, s, candidate, p * s, p * candidate), -1))
            return (source, branch, semantic) if return_program_bank else (source, branch)

    model = GroundedContrast()
    if sum(parameter.numel() for parameter in model.parameters()) > 32768:
        raise ValueError("grounded contrast exceeds32K parameter cap")
    return model


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


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


CELL_ARRAYS = {"train": "train_idx", "program-held": "program_holdout_idx", "state-held": "state_holdout_idx", "joint-held": "joint_holdout_idx"}


def load_contrast_data(npz_path, manifest_path):
    """Enforce both holdout axes and matched public helper inputs independently."""
    import grounded_contrast_data as D
    manifest = json.loads(Path(manifest_path).read_text())
    if G.sha(npz_path) != manifest["artifact"]["sha256"]:
        raise ValueError("dataset hash differs from manifest")
    with np.load(npz_path, allow_pickle=False) as pack:
        arrays = {name: value.copy() for name, value in pack.items()}
    shapes = dict(context_features=(168, 2), candidate_features=(168, 8, 26), candidate_mask=(168, 8),
                  primary_candidate_mask=(168, 8), source_use=(168,), source_use_mask=(168,),
                  candidate_allowed=(168, 8), candidate_allowed_mask=(168, 8), targets=(168, 8, 11), target_mask=(168, 8, 11))
    for name, shape in shapes.items():
        value = np.asarray(arrays[name])
        if value.shape != shape or value.dtype != np.float32 or not np.isfinite(value).all():
            raise ValueError("invalid dense tensor " + name)
        if name.endswith("mask") and not np.isin(value, [0, 1]).all():
            raise ValueError("invalid mask " + name)
    if not np.array_equal(arrays["primary_candidate_mask"], np.tile([1.] * 7 + [0.], (168, 1))):
        raise ValueError("primary candidates must exclude source-self slot7")
    if np.any(arrays["target_mask"][..., :2]):
        raise ValueError("standalone labels cannot be duplicated into transition loss")
    if tuple(manifest["target_names"]) != TARGET_NAMES or tuple(manifest["context_feature_names"]) != D.CONTEXT_FEATURES or tuple(manifest["candidate_feature_names"]) != D.CANDIDATE_FEATURES:
        raise ValueError("ordered input/output columns differ")
    codes = sorted(manifest["programs"])
    if set(codes) != set(D.CORE_CODES):
        raise ValueError("reviewed twelve-program bank required")
    records = [dict(manifest["programs"][code], code=code) for code in codes]
    # Neither opaque IDs nor source metadata are passed into semantic tokenization.
    for record in records:
        if digest(D.normalized_program(record["raw_ability"])) != record["program_group_id"]:
            raise ValueError("normalized program group digest differs")
        structural_tokens(record["raw_ability"])
    source = arrays["source_cards"].astype(str)
    state = arrays["state_families"]
    if source.shape != (168,) or state.shape != (168,) or len(set(zip(source, state.tolist()))) != 168:
        raise ValueError("duplicate or malformed native root")
    query = np.asarray([codes.index(code) for code in source], np.int64)
    train_codes = list(D.TRAIN_CODES)
    train_programs = np.asarray([codes.index(code) for code in train_codes], np.int64)
    held_programs = np.asarray([codes.index(code) for code in D.HELDOUT_CODES], np.int64)
    expected_counts = {"train": 100, "program-held": 20, "state-held": 40, "joint-held": 8}
    for cell, key in CELL_ARRAYS.items():
        expected = [i for i, (code, family) in enumerate(zip(source, state)) if
                    (code in D.TRAIN_CODES) == (cell in ("train", "state-held")) and
                    (family < 10) == (cell in ("train", "program-held"))]
        if arrays[key].dtype != np.int64 or arrays[key].tolist() != expected or len(expected) != expected_counts[cell]:
            raise ValueError("four-cell split differs from fixed axes")
    for family in range(14):
        rows = np.flatnonzero(state == family)
        if len(rows) != 12:
            raise ValueError("each state requires all twelve programs")
        if any(not np.array_equal(arrays["context_features"][i], arrays["context_features"][rows[0]]) or
               not np.array_equal(arrays["candidate_features"][i, :7], arrays["candidate_features"][rows[0], :7]) for i in rows):
            raise ValueError("primary public inputs differ across paired programs")
    for head in BINARY_HEADS:
        values, mask = ((arrays["source_use"], arrays["source_use_mask"]) if head == 0 else
                        (arrays["candidate_allowed"], arrays["candidate_allowed_mask"]) if head == 1 else
                        (arrays["targets"][..., head], arrays["target_mask"][..., head]))
        if not np.isin(values[mask.astype(bool)], [0, 1]).all():
            raise ValueError("known binary labels must be0/1")
    symbols = freeze_symbols([r["raw_ability"] for r in records])
    numeric_scale = fit_numeric_scale(records, train_codes)
    _, bank = encode_program_bank(records, symbols, train_codes, numeric_scale)
    train = arrays["train_idx"]
    input_scaling = fit_input_scaling(arrays["context_features"], arrays["candidate_features"], train, arrays["primary_candidate_mask"])
    context, candidates = apply_input_scaling(arrays["context_features"], arrays["candidate_features"], input_scaling)
    head_scaling = fit_head_scaling(arrays["source_use"], arrays["source_use_mask"], arrays["candidate_allowed"], arrays["candidate_allowed_mask"], arrays["targets"], arrays["target_mask"], train, arrays["primary_candidate_mask"])
    groups = [r["program_group_id"] for r in records]
    rng = np.random.default_rng(FIT_CONFIG["wrong_eval_seed"])
    wrong_eval = np.zeros(168, np.int64)
    for i, index in enumerate(query):
        pool = train_programs if index in train_programs else held_programs
        wrong_eval[i] = draw_wrong_programs([index], pool, groups, rng)[0]
    return dict(arrays=arrays, manifest=manifest, manifest_sha256=G.sha(manifest_path), dataset_sha256=G.sha(npz_path),
                records=records, codes=codes, train_codes=train_codes, query=query, train_programs=train_programs,
                held_programs=held_programs, symbols=symbols, numeric_scale=numeric_scale, bank=bank,
                context=context, candidates=candidates, input_scaling=input_scaling, head_scaling=head_scaling,
                wrong_eval=wrong_eval, group_ids=groups)


def predictions(torch, output, scaling):
    source, branch = output
    result = branch.detach().clone()
    for head in range(len(TARGET_NAMES)):
        if head in BINARY_HEADS:
            result[..., head] = torch.sigmoid(result[..., head])
        else:
            result[..., head] = result[..., head] * scaling["scale"][head] + scaling["center"][head]
    return torch.sigmoid(source.detach()).numpy(), result.numpy()


def metric_cells(source_prediction, branch_prediction, data):
    """Native-coordinate MAE with root/candidate dependence retained explicitly."""
    a, scales = data["arrays"], data["head_scaling"]
    result = {}
    for cell, key in CELL_ARRAYS.items():
        if cell == "train":
            continue
        rows = a[key]
        segments = {}
        for segment, selection in (("primary", a["primary_candidate_mask"]), ("source-self-auxiliary", 1 - a["primary_candidate_mask"])):
            heads = {}
            for head, name in enumerate(TARGET_NAMES):
                if head == 0:
                    if segment != "primary":
                        continue
                    predicted, target, known = source_prediction[rows], a["source_use"][rows], a["source_use_mask"][rows]
                else:
                    predicted = branch_prediction[rows, :, head]
                    target = a["candidate_allowed"][rows] if head == 1 else a["targets"][rows, :, head]
                    known = (a["candidate_allowed_mask"][rows] if head == 1 else a["target_mask"][rows, :, head]) * selection[rows]
                error = abs(predicted - target)
                if error.ndim > 1:
                    support = known.sum(-1)
                    valid = support > 0
                    errors = (error * known).sum(-1) / np.maximum(support, 1)
                else:
                    valid = known > 0
                    errors = error
                if valid.any():
                    root_rows = rows[valid]
                    observed = target[known.astype(bool)]
                    groups = len(set(a["program_group_ids"][root_rows].tolist()))
                    families = len(set(a["state_families"][root_rows].tolist()))
                    positive_roots = int(np.sum(((target == 1) & known.astype(bool)).any(-1))) if known.ndim > 1 else int(np.sum((target == 1) & known.astype(bool)))
                    negative_roots = int(np.sum(((target == 0) & known.astype(bool)).any(-1))) if known.ndim > 1 else int(np.sum((target == 0) & known.astype(bool)))
                    adequate = groups >= 2 and families >= 4 and (positive_roots >= 4 and negative_roots >= 4 if head in BINARY_HEADS else len(np.unique(observed)) >= 2)
                    record = dict(mae=float(errors[valid].mean()), known_coordinates=int(known.sum()), observed_roots=int(valid.sum()),
                                  observed_values=np.unique(target[known.astype(bool)]).tolist(),
                                  observed_program_groups=groups, observed_state_families=families,
                                  positive_roots=positive_roots if head in BINARY_HEADS else None,
                                  negative_roots=negative_roots if head in BINARY_HEADS else None,
                                  diagnostic_only_low_support=not adequate,
                                  evidence_rule="at least2 evaluated program groups x4states, plus4positive+4negative distinct binary roots or varying continuous labels; diagnostic flag only",
                                  training_role="primary-varying" if head in scales["primary"] else "constant-or-low-support-auxiliary" if head in scales["auxiliary"] else "unobserved-in-training")
                    if head in BINARY_HEADS:
                        correct = ((predicted >= .5) == (target >= .5)).astype(float)
                        record["accuracy"] = float(((correct * known).sum(-1) / np.maximum(known.sum(-1), 1))[valid].mean()) if known.ndim > 1 else float(correct[valid].mean())
                    heads[name] = record
            primary = [record["mae"] / scales["scale"][TARGET_NAMES.index(name)] for name, record in heads.items() if TARGET_NAMES.index(name) in scales["primary"]]
            segments[segment] = dict(root_cases=len(rows), heads=heads, macro_train_scaled_mae=float(np.mean(primary)) if primary else None)
        result[cell] = segments
    return result


def no_fit_baselines(data):
    a, train = data["arrays"], data["arrays"]["train_idx"]
    n = len(a["source_use"])
    source = np.full(n, float((a["source_use"][train] * a["source_use_mask"][train]).sum() / max(a["source_use_mask"][train].sum(), 1)), np.float32)
    branch = np.zeros((n, 8, 11), np.float32)
    for head in range(1, 11):
        values = a["candidate_allowed"] if head == 1 else a["targets"][..., head]
        mask = (a["candidate_allowed_mask"] if head == 1 else a["target_mask"][..., head]) * a["primary_candidate_mask"]
        prior = float((values[train] * mask[train]).sum() / max(mask[train].sum(), 1))
        branch[..., head] = prior
    prior = metric_cells(source, branch, data)
    branch.fill(0)
    branch[..., 4] = a["context_features"][:, 1, None]
    return dict(train_prior=prior, naive_zero_delta_copy_source_exhausted=metric_cells(np.zeros(n, np.float32), branch, data))


def numerical_contract(data):
    return dict(schema=CONTRAST_SCHEMA, purpose="standalone existing-runtime action-semantic contrast; no production tensor ABI",
                config=FIT_CONFIG, bank={name: dict(shape=list(value.shape), dtype=str(value.dtype)) for name, value in data["bank"].items()},
                tensors=dict(context=dict(shape=["B", 2], dtype="float32", columns=data["manifest"]["context_feature_names"], units=data["manifest"]["context_feature_units"]),
                             candidates=dict(shape=["B", 8, 26], dtype="float32", columns=data["manifest"]["candidate_feature_names"], units=data["manifest"]["candidate_feature_units"]),
                             query=dict(shape=["B"], dtype="int64", inclusive_bounds=[0, MAX_PROGRAMS - 1]),
                             source_logits=dict(shape=["B"], dtype="float32"), branch_logits=dict(shape=["B", 8, 11], dtype="float32", columns=list(TARGET_NAMES), units=data["manifest"]["target_units"], unused_columns=[0])),
                vocabularies=data["symbols"], vocabulary_sha256=digest(data["symbols"]), status_columns=["known", "unknown", "neutral", "unsupported", "ambiguous"],
                padding="PAD0, UNKNOWN1 reserved. Padded slots allzero. Known unseen symbol rejects; overflow rejects without truncation. Unknown statuses have no semantic tokens.",
                caps=dict(programs=MAX_PROGRAMS, typed_tokens=MAX_TOKENS, path_depth=MAX_PATH, candidates=8,
                          training_batch=16, max_reference_batch=16, max_evaluation_batch=68, parameters=32768),
                input_scaling=data["input_scaling"], head_scaling=data["head_scaling"], literal_scaling=dict(first="physical_value/train_numeric_std_floor1", second="signed log1p(abs(value))", scale=data["numeric_scale"], absolute_bound=65535),
                pooling="active-token mean then status projection+LayerNorm; depth*key product then nonlinear path/value joint leaf before pooling; no deck/bag branch",
                identity="ID control only, training IDs1..10; all heldout IDs fixedzero UNK0. No IDs/titles/source paths in semantic tokens.",
                locality="source head IR+2globals only; each candidate head IR+2globals+own26 only. No source-self broadcasting or candidate-bank pooling.",
                outputs="Binary heads are logits; continuous heads predict train-centered/std-floor1 native labels, inverse-scaled for reports. Unknown labels masked. Standalone source once/root, candidates meanwithinroot, macroheads.",
                orientation="Linear.weight[out,in], embedding[vocab,16], depth_gate[24,16]; reference make_contrast_model.encode_program_bank/forward; named state_dict saved as NPZ",
                invariance="object keys sorted; effect/list/operand order and literal-position binding retained. Action pilot has no deck aggregation; production ownDeck remains2x207.",
                source_pins=dict(model_sha256=G.sha(__file__), dataset_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"], source_revision=data["manifest"]["source_revision"], programs={r["code"]: {k: r.get(k) for k in ("source_hash", "source_path", "program_group_id", "side", "index")} for r in data["records"]}))


def _progress(path, completed, arm, step):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(dict(updates_completed=completed, arm=arm, arm_step=step, monotonic=time.monotonic())) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def torch_bank(torch, bank):
    return {key: torch.as_tensor(value) for key, value in bank.items()}


def golden_bank(bank):
    result = {key: value.copy() for key, value in bank.items()}
    for status_index, slot in enumerate(range(MAX_PROGRAMS - 4, MAX_PROGRAMS), 1):
        for value in result.values():
            value[slot] = 0
        result["slot_mask"][slot] = 1
        result["status"][slot, status_index] = 1
    return result


def fit_contrast(args):
    """Single worker, supervised externally by the shared native/fit ledger."""
    if not Path(__file__).is_absolute() or not Path(sys.executable).is_absolute():
        raise ValueError("absolute interpreter/main entrypoint required")
    data = load_contrast_data(args.dataset, args.manifest)
    contract = numerical_contract(data)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    preview = dict(config=FIT_CONFIG, contract=contract, commit=commit, entrypoint=str(Path(__file__).resolve()),
                   interpreter=sys.executable, dataset=str(args.dataset.resolve()), manifest=str(args.manifest.resolve()),
                   ledger=str(args.ledger.resolve()), ledger_sha256_at_start=G.sha(args.ledger) if args.ledger.exists() else None,
                   progress=str(args.progress.resolve()), baselines=no_fit_baselines(data))
    if args.validate_only:
        print(json.dumps(preview, indent=2, allow_nan=False))
        return preview
    if not args.ledger.exists() or args.progress.exists() or args.out.exists():
        raise ValueError("guard ledger required, fresh output and progress paths required")
    ledger_rows = [json.loads(line) for line in args.ledger.read_text().splitlines() if line.strip()]
    if not ledger_rows or ledger_rows[-1].get("event") != "stage-start" or ledger_rows[-1].get("stage") != "fit":
        raise ValueError("must run inside coordinating shared-budget supervisor fit stage")
    args.out.mkdir(parents=True, exist_ok=False)
    G.write_json(args.out / "contract.json", contract)
    G.write_json(args.out / "manifest.json", preview)
    schedule = np.random.default_rng(18).choice(data["arrays"]["train_idx"], (600, 16), replace=True)
    np.save(args.out / "batch-schedule.npy", schedule)
    wrong_schedule = np.stack([draw_wrong_programs(data["query"][rows], data["train_programs"], data["group_ids"], np.random.default_rng(19 + step)) for step, rows in enumerate(schedule)])
    np.save(args.out / "wrong-program-schedule.npy", wrong_schedule)
    writer = RunEvents(args.events, run_id=args.run_id, commit=commit, config=FIT_CONFIG,
                       dataset=dict(npz_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"], shared_ledger=str(args.ledger), model_source_sha256=G.sha(__file__)),
                       limitations=["Twelve existing-runtime programs, two held-out IDs and four held-out states; small native-fixture contrast, no policy or deck-strength claim.", "Source-self query is a separately reported0.1 auxiliary; primary paired rows0..6 have identical public inputs across programs."], parent_run_id=args.campaign_id)
    started, completed = time.monotonic(), 0
    counts = dict(optimizer_updates=0, heldout_validation_batches=0, usage_batches=0, abi_embedding_batches=0)
    stop = threading.Event()
    heartbeat = threading.Thread(target=lambda: _event_heartbeat(stop, writer), daemon=True)
    heartbeat.start()
    writer.emit("status", "preparing", 0, status="running")
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        x, c = torch.as_tensor(data["context"]), torch.as_tensor(data["candidates"])
        q = torch.as_tensor(data["query"])
        all_bank = torch_bank(torch, data["bank"])
        train_bank = torch_bank(torch, training_program_bank(data["bank"], data["train_programs"]))
        label_names = ("source_use", "source_use_mask", "candidate_allowed", "candidate_allowed_mask", "targets", "target_mask", "primary_candidate_mask")
        labels = {name: torch.as_tensor(data["arrays"][name]) for name in label_names}
        eval_rows = np.concatenate([data["arrays"][key] for cell, key in CELL_ARRAYS.items() if cell != "train"])
        results, initial_hash = [], None
        for arm in CONTRAST_ARMS:
            torch.manual_seed(17)
            model = make_contrast_model(torch, data["symbols"])
            state = {name: value.detach().numpy().copy() for name, value in model.state_dict().items()}
            state_hash = hashlib.sha256(b"".join(name.encode() + value.tobytes() for name, value in sorted(state.items()))).hexdigest()
            if initial_hash is not None and state_hash != initial_hash:
                raise AssertionError("matched arms must share initialization")
            initial_hash = state_hash
            optimizer = torch.optim.AdamW(model.parameters(), lr=.003, weight_decay=.0001)
            active_parameters, gradient_snapshots = set(), []
            def evaluate():
                counts["heldout_validation_batches"] += 1
                query = torch.as_tensor(data["wrong_eval"][eval_rows]) if arm == "wrong-ir" else q[eval_rows]
                with torch.no_grad():
                    source, branch = predictions(torch, model(x[eval_rows], c[eval_rows], query, all_bank, arm), data["head_scaling"])
                full_source = np.zeros(168, np.float32)
                full_branch = np.zeros((168, 8, 11), np.float32)
                full_source[eval_rows], full_branch[eval_rows] = source, branch
                return metric_cells(full_source, full_branch, data), full_source, full_branch
            initial_metrics, _, _ = evaluate()
            writer.emit("metric", arm, completed, status="running", arm=arm, arm_step=0, metrics=_flat_scores(initial_metrics))
            for step, rows in enumerate(schedule, 1):
                optimizer.zero_grad(set_to_none=True)
                query = torch.as_tensor(wrong_schedule[step - 1]) if arm == "wrong-ir" else q[rows]
                output = model(x[rows], c[rows], query, train_bank, arm)
                loss, _ = balanced_head_loss(torch, *output, {name: value[rows] for name, value in labels.items()}, data["head_scaling"])
                if not torch.isfinite(loss):
                    raise FloatingPointError("nonfinite balanced loss")
                loss.backward()
                if step in (1, 600):
                    gradient_snapshots.append(dict(arm_step=step, module_preclip_gradients=gradient_summary(model)))
                active_parameters.update(name for name, parameter in model.named_parameters() if parameter.grad is not None and bool((parameter.grad != 0).any()))
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                if not torch.isfinite(norm):
                    raise FloatingPointError("nonfinite gradient")
                optimizer.step()
                completed += 1
                counts["optimizer_updates"] = completed
                _progress(args.progress, completed, arm, step)
                if step % 100 == 0:
                    writer.emit("metric", arm, completed, status="running", arm=arm, arm_step=step,
                                metrics=dict(train_loss=float(loss.detach()), grad_norm=float(norm), updates_completed=completed))
            final_metrics, source_pred, branch_pred = evaluate()
            writer.emit("metric", arm, completed, status="running", arm=arm, arm_step=600, metrics=_flat_scores(final_metrics))
            checkpoint = args.out / (arm + ".npz")
            np.savez(checkpoint, **{name: value.detach().numpy() for name, value in model.state_dict().items()})
            np.savez_compressed(args.out / (arm + "-predictions.npz"), source_predictions=source_pred[eval_rows], branch_predictions=branch_pred[eval_rows],
                                source_targets=data["arrays"]["source_use"][eval_rows], source_mask=data["arrays"]["source_use_mask"][eval_rows],
                                candidate_targets=data["arrays"]["candidate_allowed"][eval_rows], candidate_mask=data["arrays"]["candidate_allowed_mask"][eval_rows],
                                targets=data["arrays"]["targets"][eval_rows], target_mask=data["arrays"]["target_mask"][eval_rows],
                                primary_candidate_mask=data["arrays"]["primary_candidate_mask"][eval_rows], root_indices=eval_rows,
                                program_groups=data["arrays"]["program_group_ids"][eval_rows], state_families=data["arrays"]["state_families"][eval_rows], partition=data["arrays"]["partition"][eval_rows])
            bank = golden_bank(data["bank"])
            counts["abi_embedding_batches"] += 1
            with torch.no_grad():
                golden_source, golden_branch, program_vectors = model(x[:1].expand(MAX_PROGRAMS, -1), c[:1].expand(MAX_PROGRAMS, -1, -1), torch.arange(MAX_PROGRAMS), torch_bank(torch, bank), arm, return_program_bank=True)
            if not torch.isfinite(golden_source).all() or not torch.isfinite(golden_branch).all():
                raise FloatingPointError("nonfinite status golden")
            golden_path = args.out / (arm + "-golden.npz")
            np.savez_compressed(golden_path, **{"bank_" + key: value for key, value in bank.items()}, context=data["context"][:1].repeat(MAX_PROGRAMS, 0), candidates=data["candidates"][:1].repeat(MAX_PROGRAMS, 0), query=np.arange(MAX_PROGRAMS, dtype=np.int64), source_logits=golden_source.numpy(), branch_logits=golden_branch.numpy(), semantic_program_vectors=program_vectors.numpy(), known_program_codes=np.asarray(data["codes"]))
            arm_contract = dict(contract, arm=arm, checkpoint_sha256=G.sha(checkpoint), golden_sha256=G.sha(golden_path), named_weights={name: dict(shape=list(value.shape), dtype=str(value.dtype)) for name, value in model.state_dict().items()}, reference_forward="grounded_contrast_model.make_contrast_model().forward")
            G.write_json(args.out / (arm + "-contract.json"), arm_contract)
            result = dict(arm=arm, updates=600, parameters=sum(p.numel() for p in model.parameters()), initialization_sha256=initial_hash,
                          tensors_with_observed_nonzero_gradient=sorted(active_parameters), allocated_coordinates_in_those_tensors=sum(p.numel() for name, p in model.named_parameters() if name in active_parameters),
                          gradient_count_interpretation="Allocated coordinates in tensors with any nonzero gradient, not a count of nonzero gradient coordinates. Snapshots report actual coordinate coverage.", gradient_snapshots=gradient_snapshots,
                          initial=initial_metrics, final=final_metrics, checkpoint_sha256=G.sha(checkpoint), contract_sha256=G.sha(args.out / (arm + "-contract.json")), golden_sha256=G.sha(golden_path))
            if arm == "correct-ir":
                result["usage_interventions"] = {}
                for name, zero in (("zero-program", True), ("partition-local-swapped-program", False)):
                    counts["usage_batches"] += 1
                    query = q[eval_rows] if zero else torch.as_tensor(data["wrong_eval"][eval_rows])
                    with torch.no_grad():
                        sp, bp = predictions(torch, model(x[eval_rows], c[eval_rows], query, all_bank, arm, zero_program=zero), data["head_scaling"])
                    sfull, bfull = source_pred.copy(), branch_pred.copy()
                    sfull[eval_rows], bfull[eval_rows] = sp, bp
                    result["usage_interventions"][name] = dict(metrics=metric_cells(sfull, bfull, data), source_probability_delta_rms=rms(sp - source_pred[eval_rows]), primary_prediction_delta_rms=rms(bp[:, :7] - branch_pred[eval_rows, :7]), labels="same independently collected native targets; intervention is postfit diagnostic, not model selection")
            results.append(result)
        if counts != dict(optimizer_updates=2400, heldout_validation_batches=8, usage_batches=2, abi_embedding_batches=4):
            raise AssertionError("fixed allocation counters differ")
        result = dict(status="completed", counts=counts, updates_completed=completed, arms=results, baselines=preview["baselines"],
                      config=FIT_CONFIG, dataset_sha256=data["dataset_sha256"], manifest_sha256=data["manifest_sha256"], contract_sha256=G.sha(args.out / "contract.json"),
                      source_sha256=G.sha(__file__), commit=commit, runtime=G.runtime_metadata(torch), fit_seconds=time.monotonic() - started,
                      heldout_labels_used_in_training=False, fixed_wrong_id_permutation=False, initializations_identical=True)
        G.write_json(args.out / "result.json", result)
        writer.emit("artifact", "completed", completed, status="completed", artifacts=dict(result=str(args.out / "result.json")))
        return result
    except BaseException as exc:
        G.write_json(args.out / "error.json", dict(error=str(exc), updates_completed=completed, counts=counts))
        writer.emit("status", "failed", completed, status="failed", error=str(exc))
        raise
    finally:
        stop.set()
        heartbeat.join(timeout=2.)


def _flat_scores(metrics):
    return {cell.replace("-", "_") + "_primary_macro_scaled_mae": value["primary"]["macro_train_scaled_mae"] for cell, value in metrics.items() if value["primary"]["macro_train_scaled_mae"] is not None}


def _event_heartbeat(stop, writer):
    while not stop.wait(1.):
        writer.heartbeat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose-prior", type=Path)
    parser.add_argument("--fit", action="store_true")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--campaign-id")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    if args.fit:
        if args.diagnose_prior is not None or any(getattr(args, field) is None for field in ("dataset", "manifest", "ledger", "progress", "run_id")):
            parser.error("--fit needs dataset, manifest, ledger, progress and run-id, and excludes diagnose-prior")
        fit_contrast(args)
    elif args.diagnose_prior is not None:
        diagnose_prior(args.diagnose_prior, args.out, args.events)
    else:
        parser.error("select --fit or --diagnose-prior")


if __name__ == "__main__":
    main()
