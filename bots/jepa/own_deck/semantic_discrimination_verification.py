"""One linked five-second saved-artifact verification; no experimental retry.

The failed verifier and all earlier charges remain immutable. Preparation is
byte-only; run requires a separately initialized once-only journal and root GO.
"""
import argparse
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3] / "experiments/semantic-discrimination-verification-v1"
OLD = ROOT.with_name("semantic-discrimination-repair-v1")
CORE_PATH = HERE / "semantic_discrimination_accounting.py"
CORE_SHA = "15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d"
GUARD_PATH = HERE / "effect_identifiability_fit.py"
GUARD_SHA = "90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765"
OLD_LEDGER_SHA = "38aec9744526ed6483aa870df59ddf4fac0c04bc71d419f0810f44e1c671f83c"
OLD_FINAL = "31f0c00536f47077d17f7b2865aa503892513ffd9f5165aff951279a71491755"
SCHEMA = "jepa-saved-verification-accounting/1"
SPEC_SCHEMA = "jepa-saved-verification-spec/1"
PARENT = dict(charged_native_applies=275, charged_seconds=214.23341095773503,
              observed_native_applies=None, failed_verifier_charged_seconds=5.)
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def verify_pin(expected):
    require(set(expected) == {"path", "sha256", "bytes"} and pin(expected["path"]) == expected, "changed immutable input: " + expected.get("path", "?"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def zero_counts():
    return {k: 0. if k == "paid_spend_usd" else 0 for k in COUNTERS}


def write_new(path, value):
    raw = encoded(value) + b"\n"  # Complete serialization before exclusive create.
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def native_json(value, np):
    if isinstance(value, np.generic):
        return native_json(value.item(), np)
    if isinstance(value, dict):
        return {native_json(k, np): native_json(v, np) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native_json(v, np) for v in value]
    require(value is None or type(value) in (str, int, float, bool), "unsupported JSON leaf; arrays/string fallback forbidden")
    return value


def preserve_verification_result(path, result):
    """A scientific mismatch is evidence too; preserve it before failing."""
    proof = write_new(path, result)
    require(result.get("status", "").startswith("PASS"), "independent verifier did not pass")
    return proof


def old_context():
    require(pin(CORE_PATH)["sha256"] == CORE_SHA, "frozen core changed")
    accounting = load(HERE / "semantic_discrimination_repair_accounting.py", "saved_old_accounting")
    c = accounting.Campaign(OLD / "campaign-spec.json")
    expected = pin(OLD / "campaign-ledger.jsonl")
    require(expected["sha256"] == OLD_LEDGER_SHA and expected["bytes"] == 220276, "exact closed failed-verifier parent required")
    with Path(expected["path"]).open() as stream:
        rows = accounting.read_rows(stream)
    state = c.state(rows)
    require(state["last_record_sha256"] == OLD_FINAL and state["pending"] is None and not state["violated"]
            and state["completed_stages"] == ["metadata", "build", "native", "prep", "fit", "baselines"], "parent must stay closed with verifier failed")
    require(rows[-1]["data"]["stage"] == "verify" and rows[-1]["data"]["status"] == "failed"
            and rows[-1]["data"]["charged"]["seconds"] == 5., "old failed five-second charge required")
    require(state["cumulative"]["charged_native_applies"] == PARENT["charged_native_applies"]
            and state["cumulative"]["charged_seconds"] == PARENT["charged_seconds"], "parent carry changed")
    return c, rows, state


def prepare_spec(helper_path):
    """Byte-only preparation, no NumPy, helper execution or ledger creation."""
    c, rows, state = old_context()
    allowed = c.allowed_pins(rows)
    values = list(allowed.values()) + c.prior["protected_files"]
    values += [pin(p) for p in OLD.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    values += [pin(p) for p in (Path(__file__), helper_path, CORE_PATH, GUARD_PATH,
        HERE / "semantic_discrimination_repair_accounting.py", HERE / "semantic_discrimination_verify.py",
        HERE / "semantic_discrimination_verify_v2.py", HERE / "binding_transfer_verify.py",
        HERE / "test_semantic_discrimination_verification.py")]
    unique = {}
    for expected in values:
        require(expected["path"] not in unique or unique[expected["path"]] == expected, "conflicting immutable input pins")
        verify_pin(expected)
        unique[expected["path"]] = expected
    require(pin(GUARD_PATH)["sha256"] == GUARD_SHA, "frozen sampled guard changed")
    spec_path = ROOT / "campaign-spec.json"
    py = c.config["stage_descriptors"]["verify"]["argv"][0]
    return dict(schema=SPEC_SCHEMA, status="sealed-awaiting-root-GO", source=pin(__file__), helper=pin(helper_path),
        guard=pin(GUARD_PATH), parent=copy.deepcopy(PARENT), parent_ledger=pin(OLD / "campaign-ledger.jsonl"), parent_final_chain=OLD_FINAL,
        ledger_path=str(ROOT / "campaign-ledger.jsonl"), caps=dict(seconds=5., **zero_counts(), cpu_workers=1, rss_bytes=1024 ** 3),
        argv=[py, str(Path(__file__).resolve()), "run", "--spec", str(spec_path)],
        outputs=[str(ROOT / "verify-result.json"), str(ROOT / "verification-receipt.json")],
        environment=copy.deepcopy(c.config["environment"]), pins=[unique[k] for k in sorted(unique)],
        scope="New saved-data verification only. Old FAILED verification and all preceding charges remain; no reset, native/model/optimizer/fit or paid work.")


class Journal:
    def __init__(self, spec_path):
        self.path = Path(spec_path).resolve(strict=True)
        self.spec_pin = pin(self.path)
        self.spec = json.loads(self.path.read_text())
        s = self.spec
        require(s.get("schema") == SPEC_SCHEMA and s.get("status") == "sealed-awaiting-root-GO"
                and s.get("source") == pin(__file__) and s.get("parent") == PARENT, "exact frozen verification specification required")
        require(s.get("caps") == dict(seconds=5., **zero_counts(), cpu_workers=1, rss_bytes=1024 ** 3), "five seconds and zero scientific exposure only")
        require(self.path == ROOT / "campaign-spec.json" and s["ledger_path"] == str(ROOT / "campaign-ledger.jsonl"), "one new canonical specification/ledger")
        require(s["outputs"] == [str(ROOT / "verify-result.json"), str(ROOT / "verification-receipt.json")], "new exclusive outputs only")
        self.ledger = Path(s["ledger_path"])

    def verify_inputs(self):
        require(pin(self.path) == self.spec_pin, "frozen spec changed")
        for expected in self.spec["pins"] + [self.spec["source"], self.spec["helper"], self.spec["guard"], self.spec["parent_ledger"]]:
            verify_pin(expected)

    def state(self, rows):
        previous, pending, ended = "0" * 64, None, None
        for i, row in enumerate(rows):
            body = {k: v for k, v in row.items() if k != "record_sha256"}
            require(row.get("schema") == SCHEMA and row.get("sequence") == i and row.get("previous_sha256") == previous
                    and hashlib.sha256(encoded(body)).hexdigest() == row.get("record_sha256"), "damaged immutable verification journal")
            event, d = row["event"], row["data"]
            if i == 0:
                require(event == "initialized" and d == dict(spec=self.spec_pin, parent=PARENT, reservation_seconds=5.), "exact linked initialization required")
            elif event == "verify-start":
                require(i == 1 and pending is None and ended is None and d["reservation_seconds"] == 5.
                        and d["argv"] == self.spec["argv"], "once-only exact verification intent")
                pending = d
            elif event == "verify-finish":
                require(pending is not None and "unresolved" not in pending and ended is None and d["cleanup_verified"] is True
                        and d["status"] in ("completed", "failed") and d["new_exposure"] == zero_counts(), "known-ended zero-science verification only")
                require(type(d["active_seconds"]) in (int, float) and math.isfinite(d["active_seconds"])
                        and d["active_seconds"] >= 0, "finite nonnegative measured wall time required")
                expected = max(d["active_seconds"], 5.) if d["status"] == "failed" else d["active_seconds"]
                require(d["charged_seconds"] == expected and (d["status"] == "failed" or expected <= 5.), "full failed reservation/actual wall charge required")
                pending, ended = None, d
            elif event == "pending-failure":
                require(pending is not None and ended is None, "unresolved verification required")
                pending = dict(pending, unresolved=True, error=d)
            else:
                raise ValueError("no retry/reset/credit/other stage")
            previous = row["record_sha256"]
        charge = ended["charged_seconds"] if ended else 5. if pending else 0.
        return dict(pending=pending, ended=ended, charged_seconds=charge, last_record_sha256=previous,
            cumulative=dict(charged_native_applies=275, charged_seconds=PARENT["charged_seconds"] + charge,
                            observed_native_applies=None, native_ceiling=275, seconds_ceiling=PARENT["charged_seconds"] + 5.))

    def append(self, stream, rows, event, data):
        previous = self.state(rows)["last_record_sha256"]
        body = dict(schema=SCHEMA, sequence=len(rows), previous_sha256=previous, event=event, data=data)
        row = dict(body, record_sha256=hashlib.sha256(encoded(body)).hexdigest())
        state = self.state([*rows, row])
        stream.seek(0, os.SEEK_END); stream.write(encoded(row).decode() + "\n"); stream.flush(); os.fsync(stream.fileno()); rows.append(row)
        return state

    def initialize(self, *, root_go=False):
        require(root_go is True, "explicit root freeze/GO required")
        self.verify_inputs()
        require(not self.ledger.is_symlink() and not self.ledger.exists(), "never reset or reopen a prior journal")
        with self.ledger.open("x+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self.append(stream, [], "initialized", dict(spec=self.spec_pin, parent=PARENT, reservation_seconds=5.))

    @contextmanager
    def lease(self):
        require(not self.ledger.is_symlink() and self.ledger.resolve() == self.ledger, "canonical non-symlink ledger required")
        with self.ledger.open("r+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = [json.loads(line) for line in stream if line.strip()]
            state = self.state(rows)
            require(rows and state["pending"] is None and state["ended"] is None, "once-only unstarted initialized verification required")
            yield stream, rows


@contextmanager
def science_fence(np):
    """No process/network/neural import or numerical fitting; restore fit APIs."""
    active = [True]
    violations = []
    def audit(event, args):
        blocked = event.startswith(("subprocess.", "socket.")) or event in ("os.system", "os.fork", "os.posix_spawn", "os.exec")
        blocked |= event == "import" and args and str(args[0]).split(".")[0] in ("torch", "tensorflow", "jax")
        if active[0] and blocked:
            violations.append(event)
            raise RuntimeError("zero-science verification fence: " + event)
    sys.addaudithook(audit)
    originals = {name: getattr(np.linalg, name) for name in ("lstsq", "solve", "pinv")}
    def forbidden(*_, **__):
        violations.append("numerical-fit")
        raise RuntimeError("no numerical fits in saved verification")
    try:
        for name in originals:
            setattr(np.linalg, name, forbidden)
        yield violations
    finally:
        for name, original in originals.items():
            setattr(np.linalg, name, original)
        active[0] = False


def run(spec_path):
    journal = Journal(spec_path)
    with journal.lease() as (stream, rows):
        actual = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]]
        journal.append(stream, rows, "verify-start", dict(reservation_seconds=5., argv=journal.spec["argv"],
            started_monotonic_seconds=time.monotonic(), owner_pid=os.getpid()))
        started = journal.state(rows)["pending"]["started_monotonic_seconds"]
        status, error, result, guard, cleanup = "failed", None, None, None, True
        try:
            require(actual == journal.spec["argv"], "actual argv differs from frozen entrypoint")
            journal.verify_inputs()
            require(not any(Path(p).exists() for p in journal.spec["outputs"]), "exclusive fresh verification outputs required")
            require(pin(GUARD_PATH)["sha256"] == GUARD_SHA, "unchanged sampled guard required")
            E = load(GUARD_PATH, "saved_verification_resource_guard")
            remaining = 5. - (time.monotonic() - started)
            require(remaining > 0, "startup exhausted five-second allocation")
            guard = E.Guard(remaining)
            with guard:
                import numpy as np
                with science_fence(np) as violations:
                    helper = load(journal.spec["helper"]["path"], "saved_independent_verification_helper")
                    old, old_rows, current = old_context()
                    args = argparse.Namespace(plan=OLD / "prep-1/sealed-fit-plan.json", fit_dir=OLD / "fit-1",
                        fit_progress=OLD / "fit-progress.jsonl", baselines_dir=OLD / "baselines-1", baseline_progress=OLD / "baseline-progress.jsonl")
                    result = native_json(helper.verify_saved(np, args, old.allowed_pins(old_rows), current, old), np)
                    require(not violations, "zero-science fence violation")
                    preserve_verification_result(journal.spec["outputs"][0], result)
            cleanup = not hasattr(guard, "thread") or not guard.thread.is_alive()
            status = "completed"
        except BaseException as exc:
            error = dict(type=type(exc).__name__, message=str(exc))
            cleanup = guard is None or not hasattr(guard, "thread") or not guard.thread.is_alive()
        try:
            journal.verify_inputs()
        except BaseException as exc:
            status, error = "failed", dict(type=type(exc).__name__, message=str(exc), post_input_check_failed=True)
        elapsed = time.monotonic() - started
        if elapsed > 5.:
            status, error = "failed", error or dict(type="BudgetExceeded", message="five seconds including postchecks")
        proof = [pin(journal.spec["outputs"][0])] if Path(journal.spec["outputs"][0]).is_file() else []
        receipt = dict(status=status, error=error, active_seconds=elapsed, cleanup_verified=cleanup,
            new_exposure=zero_counts(), source=pin(__file__), helper=journal.spec["helper"], parent_ledger=journal.spec["parent_ledger"],
            original_failed_verifier_preserved=True, scientific_execution=False, guard=guard.receipt() if guard else None, proofs=proof)
        try:
            receipt_pin = write_new(journal.spec["outputs"][1], receipt)
        except BaseException as exc:
            status, error, receipt_pin = "failed", dict(type=type(exc).__name__, message=str(exc), receipt_write_failed=True), None
        elapsed = time.monotonic() - started
        if not cleanup:
            state = journal.append(stream, rows, "pending-failure", dict(error=error, receipt=receipt_pin, scope="cleanup unknown; full five seconds retained, no retry"))
        else:
            if elapsed > 5.:
                status = "failed"
            state = journal.append(stream, rows, "verify-finish", dict(status=status, active_seconds=elapsed,
                charged_seconds=max(elapsed, 5.) if status == "failed" else elapsed, new_exposure=zero_counts(),
                cleanup_verified=True, proofs=proof + ([receipt_pin] if receipt_pin else []), error=error, original_failed_verifier_preserved=True))
        print(json.dumps(dict(status=status, state=state), allow_nan=False))
        require(status == "completed" and cleanup, "bounded verification failed; all charges retained")
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare"); p.add_argument("--helper", type=Path, required=True)
    p = commands.add_parser("initialize"); p.add_argument("--spec", type=Path, default=ROOT / "campaign-spec.json"); p.add_argument("--root-go", action="store_true")
    p = commands.add_parser("run"); p.add_argument("--spec", type=Path, default=ROOT / "campaign-spec.json")
    args = parser.parse_args()
    if args.command == "prepare":
        value = prepare_spec(args.helper); ROOT.mkdir(parents=True, exist_ok=True)
        print(json.dumps(dict(spec=write_new(ROOT / "campaign-spec.json", value), ledger_initialized=False, scientific_execution=False)))
    elif args.command == "initialize":
        print(json.dumps(Journal(args.spec).initialize(root_go=args.root_go), allow_nan=False))
    else:
        run(args.spec)


if __name__ == "__main__":
    main()
