"""Config-bound, append-only accounting; constructing Campaign never starts work.

Stdlib only. A frozen specification owns paths, budgets and exact entrypoints;
historical evidence is a separately pinned JSON manifest, never Python globals.
No credits, reset, retry, cleanup inference or scientific execution is provided.
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

SCHEMA = "jepa-config-bound-campaign-accounting/1"
SPEC_SCHEMA = "jepa-config-bound-campaign-spec/1"
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")
GUARD = dict(cpu_workers=1, rss_bytes=1024 ** 3)
STAGE_SECONDS = dict(metadata=3., build=10., native=45., prep=5., fit=45., baselines=5., verify=5.)
DEFAULT_CAPS = dict(seconds=118., native_applies=128, neural_forwards=3045,
                    optimizer_updates=3000, numerical_fits=16, paid_jobs=0, paid_spend_usd=0.)


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


def validate_pin(value):
    require(isinstance(value, dict) and set(value) == {"path", "sha256", "bytes"}, "exact path/SHA256/bytes pin required")
    require(Path(value["path"]).is_absolute() and len(value["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in value["sha256"]), "absolute lowercase SHA256 pin required")
    number(value["bytes"], integral=True)


def verify_pin(expected):
    validate_pin(expected)
    require(pin(expected["path"]) == expected, "changed pinned bytes: " + expected["path"])


def number(value, integral=False):
    require(type(value) in ((int,) if integral else (int, float)) and math.isfinite(value) and value >= 0,
            "finite nonnegative " + ("integer" if integral else "number") + " required")
    return value


def zero_counts():
    return {key: 0. if key == "paid_spend_usd" else 0 for key in COUNTERS}


def counts(value, unknown=False):
    require(isinstance(value, dict) and set(value) == set(COUNTERS), "all exposure counter keys required")
    for key, amount in value.items():
        if unknown and amount is None:
            continue
        number(amount, integral=key != "paid_spend_usd")
    return value


def read_rows(stream):
    stream.seek(0)
    return [json.loads(line) for line in stream if line.strip()]


def chain(rows, schema=SCHEMA, genesis="0" * 64):
    previous = genesis
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        require(row.get("schema") == schema and row.get("sequence") == i and row.get("previous_sha256") == previous
                and row.get("record_sha256") == digest(body), "damaged hash chain; never reset")
        previous = row["record_sha256"]
    return previous


def validate_descriptor(value):
    require(isinstance(value, dict) and set(value) == {"argv", "outputs"}, "fixed argv/output descriptor required")
    require(isinstance(value["argv"], list) and value["argv"] and all(type(s) is str and s for s in value["argv"])
            and Path(value["argv"][0]).is_absolute(), "absolute exact argv required")
    require(isinstance(value["outputs"], list) and value["outputs"]
            and len(set(value["outputs"])) == len(value["outputs"])
            and all(type(p) is str and Path(p).is_absolute() for p in value["outputs"]), "unique absolute declared outputs required")


def make_spec(campaign_root, prior_manifest, stage_descriptors, pins, *, sealed=False,
              environment=None, provenance=None):
    """Return metadata only; no files, ledger, process or allowance is created."""
    root = Path(campaign_root).resolve()
    allocations = {stage: dict(seconds=seconds, **zero_counts()) for stage, seconds in STAGE_SECONDS.items()}
    allocations["native"]["native_applies"] = 128
    allocations["fit"].update(neural_forwards=3045, optimizer_updates=3000)
    allocations["baselines"]["numerical_fits"] = 16
    return dict(schema=SPEC_SCHEMA, status="sealed-awaiting-root-GO" if sealed else "draft-awaiting-freeze",
        campaign_root=str(root), ledger_path=str(root / "campaign-ledger.jsonl"), source=pin(__file__),
        prior_manifest=copy.deepcopy(prior_manifest), stage_order=list(STAGE_SECONDS), allocations=allocations,
        caps=copy.deepcopy(DEFAULT_CAPS), guard=copy.deepcopy(GUARD), stage_descriptors=copy.deepcopy(stage_descriptors),
        pins=copy.deepcopy(pins), environment=copy.deepcopy(environment or {}), provenance=copy.deepcopy(provenance or {}),
        counter_contracts=dict(native=dict(schema="jepa-semantic-discrimination-apply-journal/1", maxApplyCalls=128,
            expected_roots=33, max_applies_per_root=4), fit=dict(optimizer_updates=3000, neural_forwards=3045,
            training_forwards=3000, evaluation_forwards=45), baselines=dict(numerical_fits=16)),
        owned_child_stages=["build", "native"],
        scope="Fresh independent allocation, linked historical charges retained; no reset, credit, paid job or retry")


class Campaign:
    def __init__(self, spec_path):
        self.spec_path = Path(spec_path).resolve(strict=True)
        self.spec_pin = pin(self.spec_path)
        self.config = json.loads(self.spec_path.read_text())
        self.spec = self.config
        self.validate_spec()
        self.LEDGER = Path(self.config["ledger_path"])
        self.CAPS = self.config["caps"]
        self.STAGES = self.config["allocations"]
        self.GUARD = self.config["guard"]
        verify_pin(self.config["prior_manifest"])
        self.prior = json.loads(Path(self.config["prior_manifest"]["path"]).read_text())
        self.validate_prior()
        self.PARENT = self.prior["carry"]
        self._config_digest = digest(self.config)

    def validate_spec(self):
        c = self.config
        require(c.get("schema") == SPEC_SCHEMA and c.get("status") == "sealed-awaiting-root-GO", "sealed specification required")
        require(c.get("source") == pin(__file__), "exact accounting source required")
        root = Path(c["campaign_root"])
        require(root.is_absolute() and root.resolve() == root and c["ledger_path"] == str(root / "campaign-ledger.jsonl")
                and self.spec_path.parent == root, "spec and canonical ledger must share campaign root")
        require(c.get("stage_order") == list(STAGE_SECONDS) and set(c.get("allocations", {})) == set(STAGE_SECONDS)
                and set(c.get("stage_descriptors", {})) == set(STAGE_SECONDS), "exact seven ordered stages required")
        require(c.get("caps") == DEFAULT_CAPS and c.get("guard") == GUARD, "root-frozen allocation and guard required")
        for stage, reservation in c["allocations"].items():
            require(set(reservation) == {"seconds", *COUNTERS} and reservation["seconds"] == STAGE_SECONDS[stage], "exact stage wall reservation required")
            counts({k: reservation[k] for k in COUNTERS})
            validate_descriptor(c["stage_descriptors"][stage])
        require(all(sum(c["allocations"][s][k] for s in c["stage_order"]) == c["caps"][k]
                    for k in c["caps"]), "stage reservations must sum to the new allocation")
        require(c["allocations"]["native"]["native_applies"] == 128 and c["allocations"]["fit"]["optimizer_updates"] == 3000
                and c["allocations"]["fit"]["neural_forwards"] == 3045 and c["allocations"]["baselines"]["numerical_fits"] == 16,
                "exposure must remain in its allocated stage")
        require(c.get("owned_child_stages") == ["build", "native"], "owned child lifecycle required for native/build")
        require(c.get("counter_contracts") == make_spec(root, c["prior_manifest"], {}, []) ["counter_contracts"], "fixed durable counter contracts required")
        require(isinstance(c.get("pins"), list), "explicit source/input pins required")
        seen = {}
        for p in c["pins"] + [c["prior_manifest"], c["source"]]:
            validate_pin(p)
            require(p["path"] not in seen or seen[p["path"]] == p, "conflicting source pins")
            seen[p["path"]] = p
        require(isinstance(c.get("environment"), dict), "frozen environment metadata required")

    @classmethod
    def validate_document(cls, document, spec_path):
        """Validate prospective frozen metadata without writing or initializing."""
        view = cls.__new__(cls)
        view.config = document
        view.spec_path = Path(spec_path).resolve()
        view.validate_spec()
        return copy.deepcopy(document)

    def validate_prior(self):
        p = self.prior
        require(p.get("schema") == "jepa-campaign-prior-manifest/1", "pinned prior manifest schema required")
        carry = p.get("carry", {})
        require(carry.get("charged_native_applies", carry.get("native_applies")) == 208
                and carry.get("charged_seconds", carry.get("active_seconds")) == 188.08889674965758
                and carry.get("observed_native_applies") is None, "closed carry must retain all charges and unknown observations")
        for name in ("pins", "protected_files", "closed_journals", "protected_roots", "original_workspaces"):
            require(isinstance(p.get(name), list), "explicit prior " + name + " required")
        for expected in p["pins"] + p["protected_files"]:
            validate_pin(expected)

    def _canonical(self):
        require(not self.LEDGER.is_symlink() and self.LEDGER.resolve() == self.LEDGER, "one canonical non-symlink ledger required")
        return self.LEDGER

    def verify_links(self):
        """Byte-only checks. Never imports protected/native/model code."""
        require(pin(self.spec_path) == self.spec_pin, "spec changed after construction")
        require(digest(self.config) == self._config_digest, "in-memory frozen specification changed")
        verify_pin(self.config["prior_manifest"])
        seen = {}
        for p in self.config["pins"] + [self.config["source"]] + self.prior["pins"] + self.prior["protected_files"]:
            require(p["path"] not in seen or seen[p["path"]] == p, "conflicting prior/source pins")
            if p["path"] not in seen:
                verify_pin(p)
            seen[p["path"]] = p
        for journal in self.prior["closed_journals"]:
            expected = journal["pin"]
            verify_pin(expected)
            rows = [json.loads(line) for line in Path(expected["path"]).read_text().splitlines() if line.strip()]
            require(len(rows) == journal["records"] and rows, "prior journal count changed")
            final = chain(rows, rows[0].get("schema"), journal.get("genesis_previous", rows[0]["previous_sha256"]))
            require(final == journal["final_chain"] and rows[-1]["event"] == journal["closed_event"], "closed prior chain changed")

    def verify_output_protection(self, outputs, *, accounting_files=False):
        protected = [Path(p["path"]) for p in self.prior["protected_files"] + self.prior["pins"]]
        roots = [Path(p) for p in self.prior["protected_roots"]]
        roots += [Path(p["path"]) for p in self.prior["original_workspaces"]]
        for output in outputs:
            p = Path(output)
            require(p.resolve() == p and not p.is_symlink(), "canonical output required")
            require(not any(p == old or old.is_relative_to(p) for old in protected), "output covers protected bytes")
            require(not any(p == old or p.is_relative_to(old) or old.is_relative_to(p) for old in roots), "output enters/covers immutable prior root")
            require(accounting_files or (p != self.LEDGER and p != self.spec_path), "stage may not overwrite canonical accounting")

    def allowed_pins(self, rows):
        allowed = {p["path"]: p for p in self.config["pins"] + self.prior["pins"] + [self.config["source"], self.config["prior_manifest"], self.spec_pin]}
        for row in rows:
            if row["event"] == "stage-finish" and row["data"]["status"] == "completed":
                for p in row["data"]["proofs"] + ([row["data"]["counter_proof"]] if row["data"].get("counter_proof") else []):
                    allowed[p["path"]] = p
        return allowed

    def metadata(self, stage, input_pins=()):
        return dict(**copy.deepcopy(self.config["stage_descriptors"][stage]), input_pins=list(input_pins), guard=copy.deepcopy(self.GUARD))

    def inspect(self, *, verify=True):
        """Nonmutating byte/chain inspection. Does not initialize or execute stages."""
        if verify:
            self.verify_links()
        ledger_exists = self._canonical().exists()
        current = None
        if ledger_exists:
            with self.LEDGER.open() as stream:
                current = self.state(read_rows(stream))
        return dict(schema="jepa-campaign-inspection/1", status="metadata-only-no-execution",
            spec=self.spec_pin, source=self.config["source"], prior_manifest=self.config["prior_manifest"],
            ledger_initialized=ledger_exists, checked_pins=verify, state=current,
            caps=copy.deepcopy(self.CAPS), parent=copy.deepcopy(self.PARENT))

    def state(self, rows):
        chain(rows)
        r = dict(config=None, spec=None, pending=None, seen_stages=[], completed_stages=[], failures=0,
                 charged=dict(seconds=0., **zero_counts()), observed=dict(seconds=0., **zero_counts()),
                 durable_prefix=zero_counts(), violated=False)
        for i, row in enumerate(rows):
            event, d = row["event"], row["data"]
            if i == 0:
                require(event == "initialized" and d["spec"] == self.config and d["spec_file"] == self.spec_pin, "exact frozen initial specification required")
                r["config"] = r["spec"] = d["spec"]
            elif event == "stage-start":
                stage = d["stage"]
                require(r["pending"] is None and not r["violated"] and stage in self.STAGES and stage not in r["seen_stages"], "pending/breach/once-only stage rule")
                require(r["completed_stages"] == self.config["stage_order"][:self.config["stage_order"].index(stage)], "prior ordered stages must complete")
                require(d["reservation"] == self.STAGES[stage], "exact stage reservation required")
                require({k: d["metadata"][k] for k in ("argv", "outputs")} == self.config["stage_descriptors"][stage]
                        and d["metadata"].get("guard") == self.GUARD and isinstance(d["metadata"].get("input_pins"), list), "exact stage descriptor/guard required")
                number(d["started_monotonic_seconds"])
                require(all(r["charged"][k] + d["reservation"][k] <= self.CAPS[k] for k in self.CAPS), "full reservation exceeds allocation")
                r["pending"] = dict(d, child=None)
                r["seen_stages"].append(stage)
            elif event in ("child-intent", "child-started", "child-ended"):
                pending = r["pending"]
                require(pending is not None and d["stage"] == pending["stage"]
                        and pending["stage"] in self.config["owned_child_stages"], "owned child requires matching native/build stage")
                if event == "child-intent":
                    require(pending["child"] is None and d["argv"] == pending["metadata"]["argv"], "one exact owned child required")
                    pending["child"] = dict(intent=d, started=None, ended=None)
                elif event == "child-started":
                    require(pending["child"] is not None and pending["child"]["started"] is None, "durable intent must precede owned child")
                    require(type(d["pid"]) is int and d["pid"] > 0 and type(d["pgid"]) is int and d["pgid"] > 0
                            and type(d["start_identity"]) is str and d["start_identity"], "PID/PGID/start identity required")
                    pending["child"]["started"] = d
                else:
                    require(pending["child"] is not None and pending["child"]["ended"] is None
                            and d["cleanup_verified"] is True and d["execution_ended"] is True
                            and d["proofs"], "positive owned cleanup evidence required")
                    pending["child"]["ended"] = d
            elif event == "pending-failure":
                require(r["pending"] is not None and d["stage"] == r["pending"]["stage"], "matching pending failure required")
                r["pending"]["unresolved_failure"] = d
            elif event == "stage-finish":
                pending = r["pending"]
                require(pending is not None and d["stage"] == pending["stage"] and "unresolved_failure" not in pending, "known pending stage required")
                require(d["status"] in ("completed", "failed") and d["cleanup_verified"] is True and d["execution_ended"] is True, "known ended execution/cleanup required")
                require(pending["child"] is None or pending["child"]["ended"] is not None, "owned child cleanup unresolved")
                failed = d["status"] == "failed"
                require(failed or pending["stage"] not in self.config["owned_child_stages"] or pending["child"] is not None, "native/build success requires owned child evidence")
                observed = counts(d["observed"], unknown=True)
                counts(d["durable_prefix"])
                number(d["active_seconds"])
                require(type(d["observed_verified"]) is bool and (failed or (d["observed_verified"] and all(v is not None for v in observed.values()))), "completed exact counters required")
                require(not failed or d["counter_proof"] is None, "failed counter proof must not parse an incomplete journal")
                if not failed and pending["stage"] in self.config["counter_contracts"]:
                    require(d["counter_proof"] is not None and isinstance(d["counter_measurements"], dict), "durable success counter proof required")
                    contract = self.config["counter_contracts"][pending["stage"]]
                    for key, value in d["counter_measurements"].items():
                        if key in COUNTERS:
                            require(observed[key] == value, "measured/observed counters differ")
                    if pending["stage"] != "native":
                        require(d["counter_measurements"] == contract, "fixed successful quota required")
                expected = dict(seconds=max(d["active_seconds"], pending["reservation"]["seconds"]) if failed else d["active_seconds"])
                for key in COUNTERS:
                    expected[key] = max(observed[key] or 0, pending["reservation"][key]) if failed else observed[key]
                    r["durable_prefix"][key] += d.get("durable_prefix", {}).get(key, observed[key] or 0)
                    if r["observed"][key] is not None:
                        if d["observed_verified"] and observed[key] is not None:
                            r["observed"][key] += observed[key]
                        elif pending["reservation"][key]:
                            r["observed"][key] = None
                require(d["charged"] == expected, "full failed reservation/actual charge changed")
                require(all(d["durable_prefix"][k] <= expected[k] for k in COUNTERS), "durable prefix exceeds charged evidence")
                for key, value in expected.items():
                    r["charged"][key] += value
                    r["violated"] |= value > pending["reservation"][key] or r["charged"][key] > self.CAPS[key]
                r["observed"]["seconds"] += d["active_seconds"]
                if not failed:
                    require(not r["violated"], "completed stage breached allocation")
                    r["completed_stages"].append(pending["stage"])
                r["failures"] += int(failed)
                r["pending"] = None
            else:
                raise ValueError("unsupported event; no credits/resets/retries")
        conservative = copy.deepcopy(r["charged"])
        if r["pending"]:
            for key, value in r["pending"]["reservation"].items():
                conservative[key] += value
        r["conservative_including_pending"] = conservative
        r["pending_reserved_exposure"] = copy.deepcopy(r["pending"]["reservation"]) if r["pending"] else None
        prior_native = self.PARENT.get("charged_native_applies", self.PARENT.get("native_applies"))
        prior_seconds = self.PARENT.get("charged_seconds", self.PARENT.get("active_seconds"))
        r["cumulative"] = dict(charged_native_applies=prior_native + conservative["native_applies"],
            charged_seconds=prior_seconds + conservative["seconds"], observed_native_applies=None,
            observed_new_native_applies=r["observed"]["native_applies"],
            native_ceiling=prior_native + self.CAPS["native_applies"], seconds_ceiling=prior_seconds + self.CAPS["seconds"])
        r["last_record_sha256"] = rows[-1]["record_sha256"] if rows else "0" * 64
        return r

    def _append(self, stream, rows, event, data):
        body = dict(schema=SCHEMA, sequence=len(rows), previous_sha256=chain(rows), event=event, data=data)
        row = dict(body, record_sha256=digest(body))
        current = self.state([*rows, row])
        stream.seek(0, os.SEEK_END)
        stream.write(encoded(row).decode() + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        rows.append(row)
        return current

    def initialize(self, *, root_go=False):
        require(root_go is True, "explicit root freeze/GO required; constructor never initializes")
        self.verify_links()
        target = self._canonical()
        self.verify_output_protection([str(target), str(self.spec_path)], accounting_files=True)
        require(not target.exists(), "no reset/overwrite of existing journal")
        with target.open("x+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self._append(stream, [], "initialized", dict(spec=self.config, spec_file=self.spec_pin))

    @contextmanager
    def lease(self):
        with self._canonical().open("r+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            rows = read_rows(stream)
            current = self.state(rows)
            require(current["config"] is not None and current["pending"] is None and not current["violated"], "ended unbreached initialized ledger required")
            yield stream, rows, current

    def start(self, stream, rows, stage, metadata):
        # Reservation precedes checks/imports/launch; every post-start failure is accounted.
        current = self._append(stream, rows, "stage-start", dict(stage=stage, reservation=copy.deepcopy(self.STAGES[stage]),
            metadata=copy.deepcopy(metadata), started_monotonic_seconds=time.monotonic(), owner_pid=os.getpid()))
        self.verify_links()
        self.verify_output_protection(metadata["outputs"])
        require(not any(Path(p).exists() for p in metadata["outputs"]), "exclusive NEW stage outputs required; no overwrite/retry")
        allowed = self.allowed_pins(rows)
        argv = metadata["argv"]
        entrypoints = [argv[0]] + ([argv[1]] if "python" in Path(argv[0]).name.lower() and len(argv) > 1 else [])
        require("python" not in Path(argv[0]).name.lower() or len(entrypoints) == 2, "absolute Python script entrypoint required")
        for path in entrypoints:
            require(Path(path).is_absolute() and Path(path).is_file(), "existing absolute entrypoint required")
            require(allowed.get(str(Path(path).resolve())) == pin(path), "entrypoint must be frozen or completed-stage binary")
        for expected in metadata["input_pins"]:
            require(allowed.get(expected["path"]) == expected, "input must be frozen or completed-stage output")
            verify_pin(expected)
        return current

    def child_intent(self, stream, rows, argv):
        return self._append(stream, rows, "child-intent", dict(stage=self.state(rows)["pending"]["stage"], argv=list(argv)))

    def child_started(self, stream, rows, pid, pgid, start_identity):
        return self._append(stream, rows, "child-started", dict(stage=self.state(rows)["pending"]["stage"], pid=pid, pgid=pgid, start_identity=start_identity))

    def child_ended(self, stream, rows, proofs, *, cleanup_verified=False, execution_ended=False):
        for expected in proofs:
            verify_pin(expected)
        return self._append(stream, rows, "child-ended", dict(stage=self.state(rows)["pending"]["stage"], proofs=list(proofs),
            cleanup_verified=cleanup_verified, execution_ended=execution_ended))

    def progress_counts(self, path, kind):
        records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        if kind == "fit":
            intents = [r for r in records if r.get("event") == "optimizer-intent"]
            updates = [r for r in records if r.get("event") == "optimizer-update"]
            forwards = [r for r in records if r.get("event") == "forward-intent"]
            require([(r["event"], r["global_update"]) for r in records if r.get("event") in ("optimizer-intent", "optimizer-update")]
                    == [(event, i) for i in range(1, len(updates) + 1) for event in ("optimizer-intent", "optimizer-update")], "paired contiguous optimizer intent/update required")
            require(all(all(a.get(k) == b.get(k) and k in a for k in ("seed", "arm", "arm_update")) for a, b in zip(intents, updates)), "optimizer model identity changed")
            require([r["global_forward"] for r in forwards] == list(range(1, len(forwards) + 1))
                    and all(r["kind"] in ("train", "evaluate") for r in forwards), "contiguous allocated forwards required")
            return dict(optimizer_updates=len(updates), neural_forwards=len(forwards), training_forwards=sum(r["kind"] == "train" for r in forwards), evaluation_forwards=sum(r["kind"] == "evaluate" for r in forwards))
        if kind == "native":
            contract = self.config["counter_contracts"][kind]
            require(records and records[0].get("schema") == contract["schema"] and records[0].get("maxApplyCalls") == contract["maxApplyCalls"], "frozen native journal header required")
            before = [r for r in records if r.get("phase") == "beforeApply"]
            after = [r for r in records if r.get("phase") in ("afterApply", "applyError")]
            require([r["applyCall"] for r in before] == list(range(1, len(before) + 1)) and len(before) <= contract["maxApplyCalls"], "contiguous bounded native attempts required")
            require([r["applyCall"] for r in after] == [r["applyCall"] for r in before]
                    and all(r.get("phase") == "afterApply" for r in after), "successful native requires completed successful applies")
            require([(r["phase"], r["applyCall"]) for r in records if r.get("phase") in ("beforeApply", "afterApply", "applyError")]
                    == [(phase, i) for i in range(1, len(before) + 1) for phase in ("beforeApply", "afterApply")],
                    "before/after applies must be chronologically paired")
            require(all(a.get("context") == b.get("context") for a, b in zip(before, after)), "native before/after context differs")
            contexts = {}
            for r in before:
                contexts[r["context"]] = contexts.get(r["context"], 0) + 1
            complete = [r["context"] for r in records if r.get("phase") == "contextComplete"]
            require(len(set(complete)) == len(complete) == contract["expected_roots"] and set(contexts).issubset(complete)
                    and all(n <= contract["max_applies_per_root"] for n in contexts.values()), "all predeclared roots must complete within per-root quota")
            return dict(native_applies=len(before))
        if kind == "baselines":
            calls = [r["global_fit"] for r in records if r.get("event") == "numerical-fit-intent"]
            require(calls == list(range(1, len(calls) + 1)), "contiguous numerical fit attempts required")
            return dict(numerical_fits=len(calls))
        raise ValueError("unallocated counter kind")

    def finish(self, stream, rows, status, active_seconds, observed, proofs, *, cleanup_verified=False,
               execution_ended=False, observed_verified=None, counter_proof=None, durable_prefix=None):
        current = self.state(rows)
        pending = current["pending"]
        require(pending is not None and cleanup_verified is True and execution_ended is True, "known ended execution/cleanup required; otherwise leave pending")
        counts(observed, unknown=True)
        number(active_seconds)
        require(status in ("completed", "failed") and (status != "failed" or counter_proof is None), "failed incomplete proof must remain opaque; full reservation applies")
        allowed = self.allowed_pins(rows)
        def check_proof(expected):
            validate_pin(expected)
            p = Path(expected["path"])
            require(allowed.get(expected["path"]) == expected or any(p == Path(o) or p.is_relative_to(Path(o)) for o in pending["metadata"]["outputs"]), "proof must be declared output/frozen input")
            verify_pin(expected)
        for expected in proofs:
            check_proof(expected)
        measured = None
        if status == "completed" and pending["stage"] in self.config["counter_contracts"]:
            require(counter_proof is not None, "success requires durable counter proof")
            check_proof(counter_proof)
            measured = self.progress_counts(counter_proof["path"], pending["stage"])
        verified = status == "completed" if observed_verified is None else observed_verified
        # Preserve before/after source/protection checks even on a known failed attempt.
        # A post-work mismatch is recorded as a failed finish rather than erasing work.
        integrity_error = None
        try:
            self.verify_links()
            for expected in pending["metadata"]["input_pins"]:
                verify_pin(expected)
        except (OSError, ValueError) as error:
            status, counter_proof, measured, integrity_error = "failed", None, None, str(error)
        elapsed = max(active_seconds, time.monotonic() - pending["started_monotonic_seconds"])
        if elapsed > pending["reservation"]["seconds"]:
            status, counter_proof, measured = "failed", None, None
        charged = dict(seconds=max(elapsed, pending["reservation"]["seconds"]) if status == "failed" else elapsed)
        charged.update({k: max(observed[k] or 0, pending["reservation"][k]) if status == "failed" else observed[k] for k in COUNTERS})
        if durable_prefix is not None:
            counts(durable_prefix)
        return self._append(stream, rows, "stage-finish", dict(stage=pending["stage"], status=status,
            active_seconds=elapsed, observed=copy.deepcopy(observed), observed_verified=verified, charged=charged,
            proofs=copy.deepcopy(proofs), counter_proof=copy.deepcopy(counter_proof), counter_measurements=measured,
            durable_prefix=copy.deepcopy(durable_prefix or {k: observed[k] or 0 for k in COUNTERS}),
            integrity_error=integrity_error, cleanup_verified=True, execution_ended=True))

    def note_pending_failure(self, stream, rows, error, proofs=()):
        for expected in proofs:
            verify_pin(expected)
        return self._append(stream, rows, "pending-failure", dict(stage=self.state(rows)["pending"]["stage"],
            error=str(error), proofs=list(proofs), disposition="execution/cleanup unknown; reservation retained; no ordinary finish or retry"))
