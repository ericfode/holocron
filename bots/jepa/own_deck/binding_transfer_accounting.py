"""New linked binding-transfer accounting. Preparation does not initialize a ledger.

Stdlib only. Historical journals are read-only parents. Every actual stage uses
one canonical nonblocking lease from before input checks/imports through cleanup.
An unresolved cleanup leaves the durable start pending and blocks later stages.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2].parent
CAMPAIGN = TASK / "experiments/binding-transfer-v1"
LEDGER = CAMPAIGN / "campaign-ledger.jsonl"
SCHEMA = "jepa-binding-transfer-accounting/1"
CONFIG_SCHEMA = "jepa-binding-transfer-config/1"
PRESERVATION = dict(path=str(TASK / "experiments/next-cycle-preservation-v1/protected-before.json"),
    sha256="9c9106f7184a8135db34a02125f6f702a2cb0303f71de99156697928787444bf", bytes=27822)
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")
STAGES = {
    "build": dict(seconds=15., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "native": dict(seconds=30., native_applies=48, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "prep": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "fit": dict(seconds=60., native_applies=0, neural_forwards=5436, optimizer_updates=5400, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "baselines": dict(seconds=10., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=64, paid_jobs=0, paid_spend_usd=0.),
    "verify": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
}
CAPS = dict(seconds=125., native_applies=48, neural_forwards=5436, optimizer_updates=5400,
            numerical_fits=64, paid_jobs=0, paid_spend_usd=0., cpu_workers=1, rss_bytes=1024 ** 3)
PARENT = dict(scope="Public-input-binding v1+v2+supplement only; PR36/37 exposure separately linked",
    charged_native_applies=112, charged_seconds=79.26753083174117, observed_native_applies=None,
    verified_v2_native_applies=32, v1_static_forensic_engine_applies=0,
    pr36_pr37_optimizer_updates=1900, pr36_pr37_neural_forwards=1917,
    pr36_pr37_native_applies=87, pr36_pr37_closed_form_head_fits=32,
    paid_spend_usd=0., cumulative_native_ceiling=160, cumulative_seconds_ceiling=210.,
    historical_modal_ceiling_usd=100., historical_modal_minimum_reserve_usd=25.)
GUARD = dict(cpu_workers=1, rss_bytes=1024 ** 3)


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def verify_pin(expected):
    require(set(expected) == {"path", "sha256", "bytes"} and Path(expected["path"]).is_absolute(),
            "absolute path/SHA256/bytes source pin required")
    require(pin(expected["path"]) == expected, "changed pinned input: " + expected["path"])


def number(value, integral=False):
    require(type(value) in ((int,) if integral else (int, float)) and math.isfinite(value) and value >= 0,
            "finite nonnegative " + ("integer" if integral else "number") + " required")
    return value


def counts(value, unknown=False):
    require(set(value) == set(COUNTERS), "all exposure counter keys required")
    for key, amount in value.items():
        if unknown and amount is None:
            continue
        number(amount, key != "paid_spend_usd")
    return value


def zero_counts():
    return {key: 0. if key == "paid_spend_usd" else 0 for key in COUNTERS}


def guard_environment(target_dir):
    """Description only; caller installs it before any numerical import/build."""
    return dict(CARGO_BUILD_JOBS="1", CARGO_PROFILE_DEV_DEBUG="0", CARGO_PROFILE_DEV_INCREMENTAL="false",
        CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(Path(target_dir).resolve()),
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1", NUMEXPR_NUM_THREADS="1")


def validate_descriptor(value):
    require(isinstance(value, dict) and set(value) == {"argv", "outputs"}, "fixed argv/output descriptor required")
    require(isinstance(value["argv"], list) and value["argv"] and all(isinstance(s, str) and s for s in value["argv"]),
            "nonempty exact argv required")
    require(Path(value["argv"][0]).is_absolute(), "absolute main entrypoint required")
    require(isinstance(value["outputs"], list) and len(set(value["outputs"])) == len(value["outputs"])
            and all(isinstance(p, str) and Path(p).is_absolute() for p in value["outputs"]), "unique absolute declared output paths required")


def validate_config(config):
    require(config.get("schema") == CONFIG_SCHEMA and config.get("status") == "sealed-awaiting-root-GO", "sealed new configuration required")
    require(config.get("ledger_path") == str(LEDGER.resolve()) and config.get("source") == pin(__file__), "fixed canonical ledger and exact accounting source required")
    require(config.get("stages") == STAGES and config.get("caps") == CAPS and config.get("parent") == PARENT,
            "exact frozen allocations and carried accounting required")
    require(config.get("preservation") == PRESERVATION and config.get("guard") == GUARD, "exact protection and guard contract required")
    require(set(config.get("stage_descriptors", {})) == set(STAGES), "all six frozen stage descriptors required")
    for descriptor in config["stage_descriptors"].values():
        validate_descriptor(descriptor)
    require(isinstance(config.get("pins"), list), "explicit frozen source/input pins required")
    require(len({p["path"] for p in config["pins"]}) == len(config["pins"]), "duplicate frozen input paths")
    require(config.get("fit_success_counts") == dict(optimizer_updates=5400, neural_forwards=5436,
            training_forwards=5400, evaluation_forwards=36), "fixed complete fit quota required")


def verify_links(config):
    """Byte-only checks, never imports/executes protected/model/native sources."""
    verify_pin(PRESERVATION)
    before = json.loads(Path(PRESERVATION["path"]).read_text())
    protected = before["protected_files"] + before["additional_protected_artifacts"]
    seen = {}
    for value in protected:
        expected = {key: value[key] for key in ("path", "sha256", "bytes")}
        require(expected["path"] not in seen or seen[expected["path"]] == expected, "conflicting protected byte pins")
        if expected["path"] not in seen:
            verify_pin(expected)
        seen[expected["path"]] = expected
    prior = before["closed_current_study_accounting"]
    require(prior["charged_native_applies"] == PARENT["charged_native_applies"]
            and prior["total_charged_seconds"] == PARENT["charged_seconds"]
            and prior["observed_native_applies"] is None and prior["observed_v2_native_applies"] == 32,
            "carried failed reservations/unknown observation changed")
    for expected in config["pins"]:
        verify_pin(expected)


def make_config(stage_descriptors, pins, sealed=False):
    """Return data only. No configuration file, journal or allowance is created."""
    config = dict(schema=CONFIG_SCHEMA, status="sealed-awaiting-root-GO" if sealed else "draft-awaiting-freeze",
        ledger_path=str(LEDGER.resolve()), source=pin(__file__), preservation=copy.deepcopy(PRESERVATION),
        stages=copy.deepcopy(STAGES), caps=copy.deepcopy(CAPS), parent=copy.deepcopy(PARENT), guard=copy.deepcopy(GUARD),
        stage_descriptors=copy.deepcopy(stage_descriptors), pins=copy.deepcopy(pins),
        fit_success_counts=dict(optimizer_updates=5400, neural_forwards=5436, training_forwards=5400, evaluation_forwards=36),
        scope="New linked cycle only; prior journals remain immutable; no credits/resets")
    if sealed:
        validate_config(config)
    return config


def chain(rows):
    previous = "0" * 64
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        require(row.get("schema") == SCHEMA and row.get("sequence") == i and row.get("previous_sha256") == previous
                and row.get("record_sha256") == digest(body), "damaged canonical journal hash chain; never reset")
        previous = row["record_sha256"]
    return previous


def read_rows(stream):
    stream.seek(0)
    return [json.loads(line) for line in stream if line.strip()]


def state(rows):
    chain(rows)
    result = dict(config=None, pending=None, seen_stages=[], completed_stages=[], failures=0,
        charged=dict(seconds=0., **zero_counts()), observed=dict(seconds=0., **zero_counts()),
        durable_prefix=zero_counts(), violated=False)
    for i, row in enumerate(rows):
        event, data = row["event"], row["data"]
        if i == 0:
            require(event == "initialized", "single initial configuration record required")
            validate_config(data["config"])
            result["config"] = data["config"]
        elif event == "stage-start":
            stage = data["stage"]
            require(result["pending"] is None and not result["violated"], "pending/violated stage blocks start")
            require(stage in STAGES and stage not in result["seen_stages"] and data["reservation"] == STAGES[stage], "once-only exact stage reservation required")
            previous = list(STAGES)[:list(STAGES).index(stage)]
            require(result["completed_stages"] == previous, "all prior stages must have completed successfully")
            require(data["metadata"]["argv"] == result["config"]["stage_descriptors"][stage]["argv"]
                    and data["metadata"]["outputs"] == result["config"]["stage_descriptors"][stage]["outputs"], "stage differs from frozen command/output descriptor")
            require(data["metadata"].get("guard") == GUARD and isinstance(data["metadata"].get("input_pins"), list),
                    "exact single-worker/RSS guard and input pins required")
            number(data["started_monotonic_seconds"])
            for key, amount in data["reservation"].items():
                require(result["charged"][key] + amount <= CAPS[key], "full stage reservation exceeds new allowance")
            result["pending"] = data
            result["seen_stages"].append(stage)
        elif event == "pending-failure":
            require(result["pending"] is not None and data["stage"] == result["pending"]["stage"], "failure note requires matching pending stage")
            result["pending"] = dict(result["pending"], unresolved_failure=data)
        elif event == "stage-finish":
            pending = result["pending"]
            require(pending is not None and data["stage"] == pending["stage"], "finish requires matching pending stage")
            require(data["status"] in ("completed", "failed") and data["cleanup_verified"] is True
                    and data["execution_ended"] is True, "known ended execution and owned cleanup required; otherwise leave pending")
            require("unresolved_failure" not in pending, "uncertain cleanup note cannot be cleared by ordinary finish")
            observed = counts(data["observed"], unknown=True)
            number(data["active_seconds"])
            require(type(data["observed_verified"]) is bool, "explicit observation knownness required")
            failed = data["status"] == "failed"
            require(failed or (data["observed_verified"] and all(observed[k] is not None for k in COUNTERS)), "successful completion requires exact counters")
            if not failed and pending["stage"] in ("native", "fit", "baselines"):
                measured = data.get("counter_measurements")
                require(isinstance(measured, dict) and data.get("counter_proof") is not None,
                        "completed exposure stage requires recorded durable counter proof")
                require(all(observed[k] == measured[k] for k in COUNTERS if k in measured), "saved measured/observed count differs")
                if pending["stage"] == "fit":
                    require(measured == result["config"]["fit_success_counts"], "complete fixed fit counts required")
            expected_charge = dict(seconds=max(data["active_seconds"], pending["reservation"]["seconds"]) if failed else data["active_seconds"])
            for key in COUNTERS:
                amount = observed[key]
                expected_charge[key] = max(amount or 0, pending["reservation"][key]) if failed else amount
                result["durable_prefix"][key] += amount or 0
                if result["observed"][key] is not None:
                    result["observed"][key] = (result["observed"][key] + amount if data["observed_verified"] and amount is not None
                        else None if pending["reservation"][key] else result["observed"][key])
            require(data["charged"] == expected_charge, "failed full-reservation/actual charge changed")
            for key, amount in expected_charge.items():
                result["charged"][key] += amount
                result["violated"] |= result["charged"][key] > CAPS[key] or amount > pending["reservation"][key]
            result["observed"]["seconds"] += data["active_seconds"]
            if not failed:
                require(all(data["charged"][k] <= pending["reservation"][k] for k in expected_charge), "completed stage must fit exact allocation")
                result["completed_stages"].append(pending["stage"])
            result["failures"] += int(failed)
            result["pending"] = None
        else:
            raise ValueError("unsupported journal event; no credit, reset, retry or generic recovery event")
    conservative = copy.deepcopy(result["charged"])
    if result["pending"]:
        for key, amount in result["pending"]["reservation"].items():
            conservative[key] += amount
    result["conservative_including_pending"] = conservative
    result["cumulative"] = dict(charged_native_applies=PARENT["charged_native_applies"] + conservative["native_applies"],
        charged_seconds=PARENT["charged_seconds"] + conservative["seconds"], observed_native_applies=None,
        observed_new_native_applies=result["observed"]["native_applies"],
        prior_verified_v2_native_applies=32, prior_v1_static_forensic_engine_applies=0)
    result["violated"] |= result["cumulative"]["charged_native_applies"] > PARENT["cumulative_native_ceiling"] or result["cumulative"]["charged_seconds"] > PARENT["cumulative_seconds_ceiling"]
    result["last_record_sha256"] = rows[-1]["record_sha256"] if rows else "0" * 64
    return result


def append(stream, rows, event, data):
    body = dict(schema=SCHEMA, sequence=len(rows), previous_sha256=chain(rows), event=event, data=data)
    row = dict(body, record_sha256=digest(body))
    current = state([*rows, row])
    stream.seek(0, os.SEEK_END)
    stream.write(encoded(row).decode() + "\n")
    stream.flush()
    os.fsync(stream.fileno())
    rows.append(row)
    return current


def canonical(path):
    path = Path(path)
    require(not path.is_symlink() and path.resolve() == LEDGER.resolve(), "one canonical NEW ledger required")
    return path.resolve()


def initialize(config_path, ledger=LEDGER, *, root_go=False):
    require(root_go is True, "explicit root freeze/GO required; preparation never initializes")
    target = canonical(ledger)
    config = json.loads(Path(config_path).read_text())
    validate_config(config)
    verify_links(config)
    require(not target.exists(), "existing journal is immutable; no overwrite/reset")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return append(stream, [], "initialized", dict(config=config, config_file=pin(config_path)))


@contextmanager
def lease(ledger=LEDGER):
    with canonical(ledger).open("r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        rows = read_rows(stream)
        current = state(rows)
        require(current["config"] is not None and current["pending"] is None and not current["violated"], "ended initialized journal without breach required")
        yield stream, rows, current


def preflight_entrypoint(argv):
    require(Path(argv[0]).is_absolute() and Path(argv[0]).is_file(), "absolute existing stage main entrypoint required")
    if "python" in Path(argv[0]).name.lower():
        require(len(argv) > 1 and Path(argv[1]).is_absolute() and Path(argv[1]).is_file(), "absolute existing Python main script required before launch")


def verify_output_protection(outputs):
    before = json.loads(Path(PRESERVATION["path"]).read_text())
    protected = [Path(p["path"]).resolve() for p in before["protected_files"] + before["additional_protected_artifacts"]]
    workspaces = [Path(p["path"]).resolve() for p in before.get("original_workspaces", [])]
    for output in outputs:
        path = Path(output).resolve()
        require(not any(path == existing or existing.is_relative_to(path) for existing in protected),
                "output would cover an immutable protected artifact")
        require(not any(path.is_relative_to(workspace) for workspace in workspaces),
                "output inside an original protected workspace forbidden")


def start(stream, rows, stage, metadata):
    current = state(rows)
    require(metadata.get("guard") == GUARD and isinstance(metadata.get("input_pins"), list), "one-worker/1GiB guard and explicit input pins required")
    descriptor = dict(argv=metadata.get("argv"), outputs=metadata.get("outputs"))
    validate_descriptor(descriptor)
    # Durable reservation is deliberately before entrypoint/input/protection
    # checks, so failed preflight never disappears from accounting.
    current = append(stream, rows, "stage-start", dict(stage=stage, reservation=copy.deepcopy(STAGES[stage]),
        metadata=copy.deepcopy(metadata), started_monotonic_seconds=time.monotonic(), owner_pid=os.getpid()))
    preflight_entrypoint(metadata["argv"])
    verify_links(current["config"])
    verify_output_protection(metadata["outputs"])
    allowed = {p["path"]: p for p in current["config"]["pins"]}
    for row in rows:
        if row["event"] == "stage-finish" and row["data"]["status"] == "completed":
            for expected in row["data"]["proofs"]:
                allowed[expected["path"]] = expected
            if row["data"].get("counter_proof"):
                expected = row["data"]["counter_proof"]
                allowed[expected["path"]] = expected
    for expected in metadata["input_pins"]:
        require(allowed.get(expected["path"]) == expected, "input pin must be frozen or a pinned completed-stage output")
        verify_pin(expected)
    entrypoints = [metadata["argv"][0]]
    if "python" in Path(entrypoints[0]).name.lower():
        entrypoints.append(metadata["argv"][1])
    for entrypoint in entrypoints:
        expected = pin(entrypoint)
        require(allowed.get(expected["path"]) == expected, "main entrypoint must be frozen or a completed-stage binary")
    return current


def progress_counts(path, kind):
    """Read existing durable intent/update records; never infer missing calls."""
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if kind == "fit":
        intents = [r for r in records if r.get("event") == "optimizer-intent"]
        updates = [r for r in records if r.get("event") == "optimizer-update"]
        forwards = [r for r in records if r.get("event") == "forward-intent"]
        require([r["global_update"] for r in intents] == list(range(1, len(intents) + 1)), "nonsequential optimizer intent journal")
        require([r["global_update"] for r in updates] == list(range(1, len(updates) + 1)), "nonsequential optimizer journal")
        paired = [(r["event"], r["global_update"]) for r in records if r.get("event") in ("optimizer-intent", "optimizer-update")]
        require(paired == [(event, i) for i in range(1, len(updates) + 1) for event in ("optimizer-intent", "optimizer-update")],
                "completed fit requires paired before-intent/after-update records")
        require(all(all(before.get(key) == after.get(key) and key in before for key in ("seed", "arm", "arm_update"))
                    for before, after in zip(intents, updates)), "optimizer intent/update model identity differs")
        require([r["global_forward"] for r in forwards] == list(range(1, len(forwards) + 1)), "nonsequential forward journal")
        require(all(r["kind"] in ("train", "evaluate") for r in forwards), "unallocated forward kind")
        return dict(optimizer_updates=len(updates), neural_forwards=len(forwards),
            training_forwards=sum(r["kind"] == "train" for r in forwards),
            evaluation_forwards=sum(r["kind"] == "evaluate" for r in forwards))
    if kind == "native":
        require(records and records[0].get("schema") == "jepa-binding-transfer-apply-journal/1"
                and records[0].get("maxApplyCalls") == 48, "exact native journal header required")
        calls = [r["applyCall"] for r in records if r.get("phase") == "beforeApply"]
        require(calls == list(range(1, len(calls) + 1)), "nonsequential before-apply journal")
        return dict(native_applies=len(calls))
    if kind == "baselines":
        calls = [r["global_fit"] for r in records if r.get("event") == "numerical-fit-intent"]
        require(calls == list(range(1, len(calls) + 1)), "nonsequential numerical-fit intent journal")
        return dict(numerical_fits=len(calls))
    raise ValueError("unrecognized progress counter kind")


def finish(stream, rows, status, active_seconds, observed, proofs, *, cleanup_verified=False,
           execution_ended=False, observed_verified=None, counter_proof=None):
    current = state(rows)
    pending = current["pending"]
    require(pending is not None and cleanup_verified is True and execution_ended is True,
            "known ended execution/cleanup required; otherwise leave pending")
    counts(observed, unknown=True)
    number(active_seconds)
    verified = status == "completed" if observed_verified is None else observed_verified
    existing = {p["path"]: p for p in current["config"]["pins"] + pending["metadata"]["input_pins"]}
    def allowed_proof(expected):
        if existing.get(expected["path"]) == expected:
            return
        path = Path(expected["path"])
        require(any(path == Path(output) or path.is_relative_to(Path(output))
                    for output in pending["metadata"]["outputs"]), "proof must be a declared stage output or an existing input")
    for expected in proofs:
        allowed_proof(expected)
        verify_pin(expected)
    measured = None
    if counter_proof is not None:
        allowed_proof(counter_proof)
        verify_pin(counter_proof)
        measured = progress_counts(counter_proof["path"], pending["stage"])
        for key in COUNTERS:
            if key in measured:
                require(observed[key] == measured[key], "observed count differs from durable progress")
        if status == "completed" and pending["stage"] == "fit":
            require(measured == current["config"]["fit_success_counts"], "complete fixed fit quota required")
    elif status == "completed" and pending["stage"] in ("native", "fit", "baselines"):
        raise ValueError("completed exposure stage requires durable counter proof")
    if status == "completed":
        verify_links(current["config"])
    elapsed = max(active_seconds, time.monotonic() - pending["started_monotonic_seconds"])
    if elapsed > pending["reservation"]["seconds"]:
        status = "failed"
    charged = dict(seconds=max(elapsed, pending["reservation"]["seconds"]) if status == "failed" else elapsed)
    charged.update({key: max(observed[key] or 0, pending["reservation"][key]) if status == "failed" else observed[key] for key in COUNTERS})
    return append(stream, rows, "stage-finish", dict(stage=pending["stage"], status=status,
        active_seconds=elapsed, observed=copy.deepcopy(observed), observed_verified=verified,
        charged=charged, proofs=copy.deepcopy(proofs), counter_proof=copy.deepcopy(counter_proof),
        counter_measurements=measured,
        cleanup_verified=True, execution_ended=True))


def note_pending_failure(stream, rows, error, proofs=()):
    current = state(rows)
    require(current["pending"] is not None, "pending stage required")
    for expected in proofs:
        verify_pin(expected)
    return append(stream, rows, "pending-failure", dict(stage=current["pending"]["stage"],
        error=str(error), proofs=list(proofs), disposition="cleanup/execution unknown; full reservation retained; no ordinary finish/retry"))
