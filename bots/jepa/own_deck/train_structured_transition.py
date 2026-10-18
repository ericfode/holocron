"""Bounded typed-program transition pilot. Fit only after coordinating root GO.

Two verified card identities support a context holdout, not unseen-card or
playing-strength claims. The fixed wrong-program swap is invertible; both it
and ID-only can memorize the two identities. No production model is modified.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import typed_ir_alignment as T
import run_local_experiments as G
from run_events import RunEvents

SCHEMA = "jepa-typed-transition-numeric/1"
ARMS = ("correct-ir", "id-only", "wrong-ir")
PROGRAMS, SEMANTIC, ROLES, PATH, WIDTH = 8, 64, 32, 16, 16
TOKENS = SEMANTIC + ROLES
STATUSES = ("known", "unknown", "neutral", "unsupported", "ambiguous")
TARGETS = ("source_use", "target_allowed", "cost_resource", "damage_delta", "source_exhausted_after", "followup_source_offered", "terminal")
BINARY = (0, 1, 4, 5, 6)
ALLOCATION = dict(max_updates=600, max_validation_forwards=6, golden_diagnostic_forwards=3,
                  shared_collection_fit_seconds=120, engine_apply_ceiling=96, collector_apply_ceiling=64,
                  sampled_rss_stop_bytes=2147483648, cpu_workers=1, prior_completed_updates=700,
                  paid_jobs=0, paid_spend_usd=0)
KEYS = "trigger optional requiresConfirmation costs kind amount value condition targetResolver owner type zone arena predicate effect effects target left right op receiver args name path source controller chooser payer chosen recipient bindings form role source_equals_chosen".split()
ENUMS = "action exhaustSelf resources damage heal giveShield sequence chosen self opponent any unit base arena anyAttackable ground space const ref query binary isUnit && >= <= === !== card source remainingHp exhausted leader ownPlayer".split()
PATH_VOCAB = ("PAD", "UNKNOWN", *sorted("key:" + k for k in set(KEYS)), *["index:" + str(i) for i in range(32)])
VALUE_VOCAB = ("PAD", "UNKNOWN", *sorted({"node:object", "node:ordered-list", "boolean:false", "boolean:true", "number", *["enum:" + k for k in ENUMS]}), *["opaque:" + str(i) for i in range(PROGRAMS)])
TYPE_VOCAB = ("PAD", "UNKNOWN", "node", "length", "boolean", "integer", "enum", "form", "role", "owner", "type", "zone", "source_equals_chosen", "opaque")
LIMITATIONS = (
    "Two supported identities; shared context-family holdout only, no held-out-card/effect-composition generalization claim.",
    "ID-only and fixed wrong-IR are memorization/invertible-code engineering controls on this two-ID bank.",
    "Native labels and masks are independent of typed features. Unexecuted transitions stay masked, never synthetic zeros.",
    "Program bag is a synthetic source-capability multiset, not an original/remaining deck or a dynamic ledger.",
    "Ordered compositional capacity is tested structurally; these native abilities do not train multieffect sequence semantics.",
    "Small standalone CPU model only; no actor, production graph, export, WASM, deployment or paid compute.",
)


@dataclass(frozen=True)
class Config:
    seed: int = 17
    steps: int = 200
    batch: int = 8
    learning_rate: float = .003

    def validate(self):
        if self.seed != 17 or not 1 <= self.steps <= 200 or not 1 <= self.batch <= 16:
            raise ValueError("seed17, at most200 updates/arm and batch16 are authorized")
        if self.learning_rate != .003:
            raise ValueError("fixed matched AdamW learning rate .003")
        return self


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def program_tokens(record):
    raw = record["raw_ability"]
    program = T.ability(raw)
    if program != record["program"]:
        raise ValueError("canonical program differs from reviewed raw ability")
    path = record["ability_path"]
    if path != ["abilities", "leader", 0]:
        raise ValueError("this pilot admits only the two verified leader[0] bindings")
    semantic = T.typed_tokens(program)
    roles = (T.Token(("source",), "form", "leader"), *[T.Token((role,), "role", "ownPlayer") for role in ("controller", "chooser", "payer")])
    if len(semantic) > SEMANTIC or len(roles) > ROLES:
        raise ValueError("pilot token overflow; no truncation")
    return semantic, roles


def empty_bank():
    return dict(path_ids=np.zeros((PROGRAMS, TOKENS, PATH), np.int64),
                path_lengths=np.zeros((PROGRAMS, TOKENS), np.int64),
                type_ids=np.zeros((PROGRAMS, TOKENS), np.int64),
                value_ids=np.zeros((PROGRAMS, TOKENS), np.int64),
                scalars=np.zeros((PROGRAMS, TOKENS, 2), np.float32),
                token_mask=np.zeros((PROGRAMS, TOKENS), np.float32),
                status=np.zeros((PROGRAMS, len(STATUSES)), np.float32),
                slot_mask=np.zeros(PROGRAMS, np.float32))


def fill_program(bank, slot, semantic=(), roles=(), status="known"):
    if not 0 <= slot < PROGRAMS or status not in STATUSES:
        raise ValueError("invalid program slot/status")
    if len(semantic) > SEMANTIC or len(roles) > ROLES:
        raise ValueError("token overflow; no truncation")
    if status != "known" and (semantic or roles):
        raise ValueError("unknown/neutral/unsupported/ambiguous cannot smuggle semantic tokens")
    paths = {v: i for i, v in enumerate(PATH_VOCAB)}
    values = {v: i for i, v in enumerate(VALUE_VOCAB)}
    types = {v: i for i, v in enumerate(TYPE_VOCAB)}
    bank["status"][slot, STATUSES.index(status)] = 1
    bank["slot_mask"][slot] = 1
    positioned = [*enumerate(semantic), *[(SEMANTIC + i, t) for i, t in enumerate(roles)]]
    for pos, token in positioned:
        if len(token.path) > PATH:
            raise ValueError("path overflow; no truncation")
        edge_ids = [paths.get(("index:" if type(k) is int else "key:") + str(k), 1) for k in token.path]
        if 1 in edge_ids or token.value_type not in types:
            raise ValueError("unreviewed path/type; reject instead of known UNKNOWN token")
        if token.value_type == "opaque":
            value_key = "opaque:" + str(token.value)
        elif type(token.value) is bool:
            value_key = "boolean:" + str(token.value).lower()
        elif type(token.value) is int:
            if not 0 <= token.value <= 65535:
                raise ValueError("integer outside0..65535")
            value_key = "number"
            bank["scalars"][slot, pos] = (token.value / 10., math.log1p(token.value) / 10.)
        else:
            value_key = ("node:" if token.value_type == "node" else "enum:") + token.value
        if value_key not in values:
            raise ValueError("unreviewed enum; reject instead of silently dropping meaning")
        bank["path_ids"][slot, pos, :len(edge_ids)] = edge_ids
        bank["path_lengths"][slot, pos] = len(edge_ids)
        bank["type_ids"][slot, pos] = types[token.value_type]
        bank["value_ids"][slot, pos] = values[value_key]
        bank["token_mask"][slot, pos] = 1


def make_banks(records):
    codes = sorted(records)
    if not 2 <= len(codes) <= PROGRAMS:
        raise ValueError("program count must be2..8")
    correct, identity = empty_bank(), empty_bank()
    for i, code in enumerate(codes):
        semantic, roles = program_tokens(records[code])
        fill_program(correct, i, semantic, roles)
        fill_program(identity, i, (T.Token((), "opaque", i),))
    permutation = np.arange(PROGRAMS)
    permutation[:len(codes)] = np.roll(np.arange(len(codes)), -1)
    wrong = {name: value[permutation].copy() for name, value in correct.items()}
    return codes, {"correct-ir": correct, "id-only": identity, "wrong-ir": wrong}, permutation


def load_dataset(npz_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    if G.sha(npz_path) != manifest["artifact"]["sha256"]:
        raise ValueError("NPZ SHA256 does not match manifest")
    with np.load(npz_path, allow_pickle=False) as pack:
        data = dict(pack)
    x = np.asarray(data["context_features"], np.float32)
    y = np.asarray(data["targets"], np.float32)
    mask = np.asarray(data["target_mask"], np.float32)
    n = len(x)
    names = tuple(manifest["target_names"])
    if names != TARGETS or not 4 <= n <= 160 or x.ndim != 2 or not 1 <= x.shape[1] <= 64 or y.shape != (n, 7) or mask.shape != y.shape:
        raise ValueError("dataset shape/target contract invalid")
    if not all(np.isfinite(a).all() for a in (x, y, mask)) or not np.isin(mask, [0, 1]).all():
        raise ValueError("nonfinite values or invalid availability mask")
    if not np.isin(y[:, BINARY][mask[:, BINARY] == 1], [0, 1]).all():
        raise ValueError("binary native labels must be0/1")
    if not np.all(mask[:, 0] == 1):
        raise ValueError("source-use is always an observed native legal-set query")
    train = np.asarray(data["train_idx"], np.int64)
    val = np.asarray(data["val_idx"], np.int64)
    if train.ndim != 1 or val.ndim != 1 or min(len(train), len(val)) < 2 or set(train) & set(val) or sorted(np.r_[train, val]) != list(range(n)):
        raise ValueError("split must be a complete disjoint partition")
    groups = np.asarray(data["context_groups"]).astype(str)
    fingerprints = np.asarray(data.get("fingerprints", data.get("row_fingerprints"))).astype(str)
    if groups.shape != (n,) or fingerprints.shape != (n,) or set(groups[train]) & set(groups[val]) or set(fingerprints[train]) & set(fingerprints[val]):
        raise ValueError("context/fingerprint leakage or missing provenance")
    numeric_contexts = [hashlib.sha256(row.tobytes()).hexdigest() for row in x]
    if {numeric_contexts[i] for i in train} & {numeric_contexts[i] for i in val}:
        raise ValueError("identical encoded public context crosses split")
    codes, banks, permutation = make_banks(manifest["programs"])
    source = np.asarray(data["source_cards"]).astype(str)
    if source.shape != (n,) or any(code not in codes for code in source):
        raise ValueError("unknown source program")
    query = np.array([codes.index(code) for code in source], np.int64)
    # Exact source program records are restricted to the two existing bindings.
    reviewed = {c["setCode"]: c for c in T.REVIEWED_CARDS if T.RUNTIME_ADMISSION[c["setCode"]]["admitted"]}
    for code in codes:
        record = manifest["programs"][code]
        if code not in reviewed or record["raw_ability"] != reviewed[code]["abilities"]["leader"][0] or record["sourceHash"] != reviewed[code]["sourceHash"]:
            raise ValueError("program outside currently verified binding/source subset")
    counts = np.zeros((n, PROGRAMS), np.float32)
    supplied = np.asarray(data.get("deck_counts", np.eye(len(codes), dtype=np.float32)[query]), np.float32)
    if supplied.shape != (n, len(codes)) or not np.isfinite(supplied).all() or np.any(supplied < 0) or np.any(supplied > 60):
        raise ValueError("invalid synthetic capability-bag counts")
    counts[:, :len(codes)] = supplied
    columns = manifest["context_feature_names"]
    if len(columns) != x.shape[1] or len(set(columns)) != len(columns):
        raise ValueError("context column contract mismatch")
    return dict(context=x, targets=y, mask=mask, train=train, val=val, groups=groups,
                fingerprints=fingerprints, codes=codes, banks=banks, wrong_permutation=permutation,
                query=query, counts=counts, manifest=manifest, manifest_sha256=G.sha(manifest_path), dataset_sha256=G.sha(npz_path))


def make_model(torch, context_width):
    """Shared trainable path composition and nonlinear path/value interaction."""
    nn = torch.nn

    class TypedTransition(nn.Module):
        def __init__(self):
            super().__init__()
            self.path_embedding = nn.Embedding(len(PATH_VOCAB), WIDTH, padding_idx=0)
            self.path_gru = nn.GRU(WIDTH, WIDTH, batch_first=True)
            self.type_embedding = nn.Embedding(len(TYPE_VOCAB), WIDTH, padding_idx=0)
            self.value_embedding = nn.Embedding(len(VALUE_VOCAB), WIDTH, padding_idx=0)
            self.scalar = nn.Linear(2, WIDTH)
            self.leaf = nn.Sequential(nn.Linear(2 * WIDTH, WIDTH), nn.Tanh(), nn.Linear(WIDTH, WIDTH), nn.Tanh())
            self.status_projection = nn.Linear(len(STATUSES), WIDTH, bias=False)
            self.context_projection = nn.Sequential(nn.Linear(context_width, WIDTH), nn.Tanh())
            self.head = nn.Sequential(nn.Linear(3 * WIDTH, 32), nn.Tanh(), nn.Linear(32, len(TARGETS)))

        def encode_program_bank(self, bank):
            # Encode each supplied program once, not once per context row.
            active = torch.nonzero(bank["slot_mask"], as_tuple=False).flatten()
            count = len(active)
            ids = bank["path_ids"][active].reshape(count * TOKENS, PATH)
            hidden, _ = self.path_gru(self.path_embedding(ids))
            lengths = bank["path_lengths"][active].reshape(-1)
            rows = torch.arange(len(lengths), device=ids.device)
            path = hidden[rows, torch.clamp(lengths - 1, min=0)] * (lengths > 0).unsqueeze(-1)
            path = path.reshape(count, TOKENS, WIDTH)
            value = self.type_embedding(bank["type_ids"][active]) + self.value_embedding(bank["value_ids"][active]) + self.scalar(bank["scalars"][active])
            # Nonlinear joint map BEFORE pooling preserves value-to-path assignment.
            leaf = self.leaf(torch.cat((path, value), -1))
            pooled = (leaf * bank["token_mask"][active].unsqueeze(-1)).sum(1) / 64.
            encoded = pooled + self.status_projection(bank["status"][active])
            return torch.zeros((PROGRAMS, WIDTH), dtype=encoded.dtype, device=encoded.device).index_copy(0, active, encoded)

        def forward_transition(self, context, query, counts, bank):
            programs = self.encode_program_bank(bank)
            queried = programs[query]
            # Count-weighted canonical-program sum is invariant to entry order.
            bag = (counts / 60.) @ programs
            context = self.context_projection(context)
            return self.head(torch.cat((queried, bag, context), -1))

        forward = forward_transition

    model = TypedTransition()
    if sum(p.numel() for p in model.parameters()) > 32768:
        raise ValueError("parameter cap exceeded")
    return model


def torch_bank(torch, bank):
    return {name: torch.as_tensor(value) for name, value in bank.items()}


def predictions(torch, logits):
    result = logits.clone()
    result[:, BINARY] = torch.sigmoid(logits[:, BINARY])
    return result


def loss_fn(torch, logits, target, mask):
    errors = (logits - target) ** 2
    errors[:, BINARY] = torch.nn.functional.binary_cross_entropy_with_logits(logits[:, BINARY], target[:, BINARY], reduction="none")
    return (errors * mask).sum() / torch.clamp(mask.sum(), min=1)


def metrics(pred, target, mask):
    pred, target, mask = (np.asarray(v, np.float64) for v in (pred, target, mask))
    result = {"observed_labels": int(mask.sum()), "masked_mae": float((abs(pred - target) * mask).sum() / max(mask.sum(), 1))}
    for i, name in enumerate(TARGETS):
        observed = mask[:, i] == 1
        result[name + "_n"] = int(observed.sum())
        if observed.any():
            result[name + "_mae"] = float(abs(pred[observed, i] - target[observed, i]).mean())
            if i in BINARY:
                result[name + "_accuracy"] = float(((pred[observed, i] >= .5) == target[observed, i]).mean())
                if len(np.unique(target[observed, i])) == 2:
                    result[name + "_balanced_accuracy"] = float(np.mean([((pred[observed, i] >= .5)[target[observed, i] == c] == c).mean() for c in (0, 1)]))
    return result


def append_progress(path, total, arm, step):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(dict(updates_completed=total, arm=arm, arm_step=step)) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_golden(torch, model, data, arm, outdir, checkpoint):
    """Exactly one label-free five-case reference ABI forward per final arm."""
    bank = {name: value.copy() for name, value in data["banks"][arm].items()}
    for slot, status in zip((2, 3, 4, 5), STATUSES[1:]):
        fill_program(bank, slot, status=status)
    query = np.array([0, 2, 3, 4, 5], np.int64)
    context = np.zeros((5, data["context"].shape[1]), np.float32)
    counts = np.zeros((5, PROGRAMS), np.float32)
    counts[np.arange(5), query] = 1
    with torch.no_grad():
        logits = model(torch.as_tensor(context), torch.as_tensor(query), torch.as_tensor(counts), torch_bank(torch, bank)).numpy()
    if not np.isfinite(logits).all():
        raise FloatingPointError("nonfinite golden output")
    golden = Path(outdir) / (arm + "-golden.npz")
    np.savez(golden, context=context, query=query, counts=counts, logits=logits,
             **{"bank." + name: value for name, value in bank.items()})
    abi = contract(data)
    abi.update(checkpoint=dict(path=str(checkpoint), sha256=G.sha(checkpoint)),
               weight_shapes={name: dict(shape=list(value.shape), dtype=str(value.numpy().dtype)) for name, value in model.state_dict().items()},
               golden=dict(path=str(golden), sha256=G.sha(golden), cases=list(STATUSES), targets=None,
                           reference_forward="make_model(torch,F).forward_transition(context,query,counts,bank)",
                           interpretation="Finite ABI fixtures only; zero synthetic contexts, no native labels or semantic-quality metric."))
    abi_path = Path(outdir) / (arm + "-contract.json")
    G.write_json(abi_path, abi)
    return dict(contract=str(abi_path), contract_sha256=G.sha(abi_path), golden=str(golden), golden_sha256=G.sha(golden))


def _worker(messages, acknowledged, data, config, schedule, outdir, progress_path):
    writer = G.WorkerEvents(messages)
    stop = threading.Event()
    thread = threading.Thread(target=lambda: _rss_loop(stop, writer), daemon=True)
    thread.start()
    completed = 0
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        context = torch.as_tensor(data["context"])
        query = torch.as_tensor(data["query"])
        counts = torch.as_tensor(data["counts"])
        target = torch.as_tensor(data["targets"])
        mask = torch.as_tensor(data["mask"])
        results = []
        train, val = data["train"], data["val"]
        denominator = data["mask"][train].sum(0)
        prior = (data["targets"][train] * data["mask"][train]).sum(0) / np.maximum(denominator, 1)
        prior_metrics = metrics(np.broadcast_to(prior, data["targets"][val].shape), data["targets"][val], data["mask"][val])
        no_delta = np.zeros(data["targets"][val].shape, np.float32)
        source_column = data["manifest"]["context_feature_names"].index("source_exhausted")
        no_delta[:, 4] = data["context"][val, source_column]
        no_delta_metrics = metrics(no_delta, data["targets"][val], data["mask"][val])
        init_hash = None
        for arm in ARMS:
            torch.manual_seed(config.seed)
            model = make_model(torch, context.shape[1])
            state = {name: value.detach().numpy().copy() for name, value in model.state_dict().items()}
            current_hash = hashlib.sha256(b"".join(name.encode() + value.tobytes() for name, value in sorted(state.items()))).hexdigest()
            if init_hash is not None and current_hash != init_hash:
                raise AssertionError("arms did not share identical initialization")
            init_hash = current_hash
            bank = torch_bank(torch, data["banks"][arm])
            optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=.0001)

            def evaluate():
                with torch.no_grad():
                    pred = predictions(torch, model(context[val], query[val], counts[val], bank)).numpy()
                return metrics(pred, data["targets"][val], data["mask"][val])

            trace = [dict(step=0, **evaluate())]
            writer.emit("metric", arm, completed, metrics=trace[-1], status="running", arm=arm, arm_step=0)
            for step, indices in enumerate(schedule, 1):
                optimizer.zero_grad(set_to_none=True)
                loss = loss_fn(torch, model(context[indices], query[indices], counts[indices], bank), target[indices], mask[indices])
                if not torch.isfinite(loss):
                    raise FloatingPointError("nonfinite loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
                if not torch.isfinite(norm):
                    raise FloatingPointError("nonfinite gradient")
                optimizer.step()
                completed += 1
                # Durable quota evidence after EVERY actual update.
                append_progress(progress_path, completed, arm, step)
                writer.step = completed
                if step % 40 == 0 or step == config.steps:
                    # Six held-out evaluations TOTAL: initial+final for each arm.
                    validation = evaluate() if step == config.steps else {}
                    observation = dict(step=step, **validation, train_loss=float(loss.detach()), grad_norm=float(norm), updates_completed=completed)
                    trace.append(observation)
                    writer.emit("metric", arm, completed, metrics=observation, status="running", arm=arm, arm_step=step)
            checkpoint = Path(outdir) / (arm + ".npz")
            np.savez(checkpoint, **{name: value.detach().numpy() for name, value in model.state_dict().items()})
            reference = write_golden(torch, model, data, arm, outdir, checkpoint)
            results.append(dict(arm=arm, updates=config.steps, parameter_count=sum(p.numel() for p in model.parameters()), initialization_sha256=init_hash,
                                trace=trace, checkpoint=str(checkpoint), checkpoint_sha256=G.sha(checkpoint), reference=reference))
        result = dict(status="completed", updates_completed=completed, held_out_evaluation_calls=6, arms=results, prior_metrics=prior_metrics,
                      no_delta_metrics=no_delta_metrics, golden_diagnostic_forwards=3,
                      no_delta_interpretation="Explicitly naive no-fit zero availability/followup/cost/damage/terminal; copies public preaction source_exhausted. No legal-rule inference or offered-mask input.",
                      label_support=data["manifest"].get("target_known_support"), target_variation=data["manifest"].get("target_variation"),
                      runtime=G.runtime_metadata(torch), limitations=list(LIMITATIONS), initializations_identical=True)
        writer.report_rss()
        messages.put(("result", G.json_primitives(result)))
        acknowledged.wait(timeout=3.)
    except BaseException as exc:
        messages.put(("failure", dict(reason=str(exc), type=type(exc).__name__, step=completed)))
        acknowledged.wait(timeout=3.)
    finally:
        stop.set()
        thread.join(timeout=2.)


def _rss_loop(stop, writer):
    while not stop.wait(1.):
        writer.report_rss()


def contract(data):
    bank = data["banks"]["correct-ir"]
    return dict(schema=SCHEMA, purpose="two-card context-holdout transition pilot; not production ABI",
                tensors={name: dict(shape=list(v.shape), dtype=str(v.dtype)) for name, v in bank.items()},
                query=dict(shape=["B"], dtype="int64", bounds=[0, PROGRAMS - 1]),
                context=dict(shape=["B", data["context"].shape[1]], dtype="float32", columns=data["manifest"]["context_feature_names"], units=data["manifest"]["context_feature_units"]),
                counts=dict(shape=["B", PROGRAMS], dtype="float32", unit="synthetic source-capability copies0..60; sum weighted by1/60"),
                outputs=dict(shape=["B", len(TARGETS)], dtype="float32", columns=list(TARGETS), units=data["manifest"].get("target_units", ["boolean", "boolean", "ready-resource copies", "damage counters", "boolean", "boolean", "boolean"]), normalization=data["manifest"].get("target_normalization", [1.] * 7), binary_logit_columns=list(BINARY), continuous_columns=[2, 3], availability="target_mask float32[B,7]; unknown labels masked, never filled as observed zero"),
                vocabularies=dict(path=list(PATH_VOCAB), type=list(TYPE_VOCAB), value=list(VALUE_VOCAB), status=list(STATUSES)),
                vocab_sha256=digest(dict(path=PATH_VOCAB, type=TYPE_VOCAB, value=VALUE_VOCAB, status=STATUSES)),
                padding="PAD0, UNKNOWN1 reserved. Padded IDs/scalars/masks/status zero; known unreviewed symbols reject. No truncation.",
                caps=dict(programs=PROGRAMS, semantic_tokens=SEMANTIC, role_tokens=ROLES, path_components=PATH, batch=16, parameters=32768),
                scales=dict(integer_features=["v/10", "log1p(v)/10"], integer_bounds=[0, 65535], token_sum_divisor=64, bag_count_divisor=60),
                orientation="nn.Linear.weight is[out,in]; embeddings[vocab,16]; PyTorch GRU r,z,n gates and documented state_dict names; exact reference is make_model.encode_program_bank/forward_transition",
                invariance="object keys sorted; list/operand/sequence indices retained; nonlinear joint path/value before sum; canonical count-weighted program bag order invariant",
                binding="Only exact source/card/leader[0]/target-stage witnesses from upstream native collector. Supplied labels/method strings are never universal binding or semantic features.",
                coverage="Selected-program known status separate from whole-card runtime admission and printed metadata; only two whole-card admitted/bound leaders in this pilot.",
                ownership="Standalone experiment, no baseline tensors loaded/changed; no evaluator/actor sharing or production export yet. No dynamic remaining deck or branch ledger.",
                provenance=dict(source_revision=T.PINNED_KESSEL_COMMIT, dataset_manifest_sha256=data.get("manifest_sha256"), dataset_sha256=data.get("dataset_sha256"), adapter_source_sha256=G.sha(HERE / "typed_ir_alignment.py"), model_source_sha256=G.sha(__file__), program_sources={code: {key: data["manifest"]["programs"][code][key] for key in ("sourceHash", "sourcePath", "ability_path")} for code in data["codes"]}),
                limitations=list(LIMITATIONS))


def run(args):
    config = Config(steps=args.steps, batch=args.batch).validate()
    data = load_dataset(args.dataset, args.manifest)
    if not math.isfinite(args.spent_seconds) or not 0 <= args.spent_seconds < 120:
        raise ValueError("invalid prior collection time; shared cap120seconds")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    provenance = dict(dataset_sha256=G.sha(args.dataset), manifest_sha256=G.sha(args.manifest),
                      source_sha256=G.sha(__file__), adapter_sha256=G.sha(HERE / "typed_ir_alignment.py"),
                      train_rows=data["train"].tolist(), val_rows=data["val"].tolist(), context_groups=data["groups"].tolist(),
                      source_cards=data["codes"], prior_collection_seconds=args.spent_seconds,
                      shared_ledger_path=str(args.ledger), shared_ledger_sha256_at_start=G.sha(args.ledger) if args.ledger.exists() else None,
                      source_allocation_manifest=str(args.manifest.resolve()))
    run_config = config.__dict__ | ALLOCATION | {"arms": list(ARMS)}
    preview = dict(config=run_config, contract=contract(data), commit=commit, dataset=provenance)
    if args.validate_only:
        print(json.dumps(preview, indent=2))
        return preview
    args.out.mkdir(parents=True, exist_ok=False)
    G.write_json(args.out / "contract.json", contract(data))
    G.write_json(args.out / "manifest.json", preview)
    schedule = np.random.default_rng(18).choice(data["train"], (config.steps, config.batch), replace=True)
    np.save(args.out / "batch-schedule.npy", schedule)
    progress = args.progress or (args.out / "completed-updates.jsonl")
    if progress.exists():
        raise ValueError("refusing to reuse an optimizer-progress file")
    writer = RunEvents(args.events, run_id=args.run_id, commit=commit, config=run_config, dataset=provenance, limitations=LIMITATIONS, parent_run_id=args.campaign_id)
    writer.emit("status", "preparing", 0, status="running")
    started = time.monotonic() - args.spent_seconds
    try:
        result = G.supervise_worker(_worker, (data, config, schedule, args.out, progress), writer, 120 - args.spent_seconds, started, 120., 2048.)
        result["contract_sha256"] = G.sha(args.out / "contract.json")
        G.write_json(args.out / "result.json", result)
        writer.emit("artifact", "completed", result["updates_completed"], status="completed", artifacts={"result": str(args.out / "result.json")})
        return result
    except BaseException as exc:
        G.write_json(args.out / "error.json", dict(error=str(exc), guard=getattr(exc, "guard", None), progress=str(progress)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--campaign-id")
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--spent-seconds", type=float, default=0.)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--validate-only", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
