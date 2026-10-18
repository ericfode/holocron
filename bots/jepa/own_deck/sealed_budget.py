"""Reusable sealed-spec bookkeeping; no scientific import, process or allocation.

Workers install their frozen resource guard using run.remaining_seconds(). Every
budgeted call must have a durable intent before execution and completion after
return. This ledger is accounting, not an OS sandbox or process supervisor.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

_PATH = Path(__file__).resolve().with_name("semantic_discrimination_accounting.py")
_SHA = "15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d"
if hashlib.sha256(_PATH.read_bytes()).hexdigest() != _SHA:
    raise ValueError("frozen bookkeeping primitives changed")
_loader = importlib.util.spec_from_file_location("sealed_budget_frozen_primitives", _PATH)
_P = importlib.util.module_from_spec(_loader)
exec(compile(_PATH.read_bytes(), str(_PATH), "exec"), _P.__dict__)
pin, verify_pin, encoded, digest, require = _P.pin, _P.verify_pin, _P.encoded, _P.digest, _P.require
SCHEMA, SPEC_SCHEMA = "jepa-sealed-budget-journal/1", "jepa-sealed-budget-spec/1"
STANDARD = {"native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd"}


def _number(value, key):
    require(type(value) in ((int, float) if key in ("seconds", "paid_spend_usd") else (int,))
            and math.isfinite(value) and value >= 0, "finite nonnegative budget unit: " + key)


class Budget:
    def __init__(self, spec_path):
        self.path = Path(spec_path).resolve(strict=True)
        self.spec_pin, self.spec = pin(self.path), json.loads(self.path.read_text())
        s = self.spec
        require(s.get("schema") == SPEC_SCHEMA and s.get("status") == "sealed-awaiting-root-GO"
                and s.get("source") == pin(__file__) and s.get("primitives") == pin(_PATH), "exact sealed implementation pins required")
        self.root, self.ledger = self.path.parent, Path(s["ledger_path"])
        require(self.ledger == self.root / "campaign-ledger.jsonl" and not self.ledger.is_symlink(), "one canonical NEW ledger required")
        self.keys = set(s["caps"])
        require({"seconds", *STANDARD} <= self.keys and s["caps"]["seconds"] > 0, "explicit time/exposure caps required")
        for k, v in s["caps"].items(): _number(v, k)
        require(s["caps"]["paid_jobs"] == s["caps"]["paid_spend_usd"] == 0, "no paid allocation supported")
        require(s["guard"]["cpu_workers"] == 1 and type(s["guard"]["rss_bytes"]) is int
                and 0 < s["guard"]["rss_bytes"] <= 1024**3, "single worker and at most1GiB sampled RSS")
        order = s["stage_order"]
        require(order and len(order) == len(set(order)) and set(order) == set(s["stages"]), "unique frozen stage order required")
        for name in order:
            d = s["stages"][name]
            _P.validate_descriptor({k: d[k] for k in ("argv", "outputs")})
            require(set(d["reservation"]) == self.keys and set(d["expected"]) == self.keys - {"seconds"}, "all stage units/expected knownness explicit")
            for k, v in d["reservation"].items(): _number(v, k)
            require(d["reservation"]["seconds"] > 0, "positive stage wall reservation required")
            for k, v in d["expected"].items():
                if v is not None: _number(v, k); require(v <= d["reservation"][k], "expected count exceeds reservation")
            external = d["external_counters"]
            require(isinstance(external, list) and len(external) == len(set(external)) and set(external) <= {"native_applies"}
                    and all(d["expected"][k] is None for k in external), "explicit external native counters require cap-only expected knownness")
        require(all(sum(s["stages"][n]["reservation"][k] for n in order) <= s["caps"][k] for k in self.keys), "stage reservations exceed cap")
        verify_pin(s["parent_manifest"])
        self.parent = json.loads(Path(s["parent_manifest"]["path"]).read_text())
        for key in ("pins", "protected_files", "protected_roots", "closed_journals"): require(isinstance(self.parent.get(key), list), "explicit parent protection: " + key)
        carry = self.parent["carry"]
        _number(carry["charged_native_applies"], "native_applies"); _number(carry["charged_seconds"], "seconds")
        require("observed_native_applies" in carry, "historical observation knownness required")
        if carry["observed_native_applies"] is not None: _number(carry["observed_native_applies"], "native_applies")
        self.frozen = {}
        for p in s["pins"] + self.parent["pins"] + self.parent["protected_files"] + [s["source"], s["primitives"], s["parent_manifest"], self.spec_pin]:
            _P.validate_pin(p)
            require(p["path"] not in self.frozen or self.frozen[p["path"]] == p, "conflicting immutable pins")
            self.frozen[p["path"]] = p

    def verify(self):
        require(pin(self.path) == self.spec_pin and digest(self.spec) == digest(json.loads(self.path.read_text())), "sealed spec changed")
        for p in self.frozen.values(): verify_pin(p)
        for j in self.parent["closed_journals"]:
            verify_pin(j["pin"])
            rows = [json.loads(v) for v in Path(j["pin"]["path"]).read_text().splitlines() if v.strip()]
            require(rows and len(rows) == j["records"] and _P.chain(rows, rows[0].get("schema"), j["genesis_previous"]) == j["final_chain"]
                    and rows[-1]["event"] == j["closed_event"], "closed history changed; no reset")

    def protect(self, outputs, *, accounting=False):
        roots = [Path(v) for v in self.parent["protected_roots"]]
        for output in outputs:
            p = Path(output)
            require(p.resolve() == p and p.is_relative_to(self.root) and p != self.path
                    and (accounting or p != self.ledger), "canonical outputs inside NEW campaign only")
            require(not any(p == old or p.is_relative_to(old) or old.is_relative_to(p) for old in roots), "output intersects protected history/workspace")
            require(not any(p == Path(old) or Path(old).is_relative_to(p) for old in self.frozen), "output covers immutable bytes")

    def _empty(self):
        return dict(pending=None, completed=[], failures=0, violated=False, charged={k: 0 for k in self.keys},
                    observed={k: 0 for k in self.keys - {"seconds"}}, proofs={}, last_sha256="0"*64, sequence=0)

    def _apply(self, state, event, d, sequence):
        p = state["pending"]
        if event == "initialized":
            require(sequence == 0 and d == {"spec": self.spec_pin}, "exact once-only initialization")
            return lambda: None
        require(sequence > 0, "initialized journal required")
        if event == "begin":
            stage = d["stage"]
            _number(d["started"], "seconds")
            require(p is None and not state["failures"] and not state["violated"] and len(state["completed"]) < len(self.spec["stage_order"])
                    and stage == self.spec["stage_order"][len(state["completed"])]
                    and d["argv"] == self.spec["stages"][stage]["argv"] and d["guard"] == self.spec["guard"], "once-only ordered exact command/guard")
            require(all(state["charged"][k] + self.spec["stages"][stage]["reservation"][k] <= self.spec["caps"][k] for k in self.keys), "full reservation exceeds allowance")
            return lambda: state.update(pending=dict(d, open={}, evidence=[], intents={k: 0 for k in self.keys - {"seconds"}}, done={k: 0 for k in self.keys - {"seconds"}}))
        require(p is not None and "unresolved" not in p, "known pending stage required")
        reserve = self.spec["stages"][p["stage"]]["reservation"]
        if event == "intent":
            k, n = d["counter"], d["amount"]
            require(k in p["intents"] and d["token"] == sequence, "allocated counter and unique token")
            _number(n, k); require(n > 0 and p["intents"][k] + n <= reserve[k], "counter reservation exceeded before call")
            def intent(): p["intents"][k] += n; p["open"][d["token"]] = (k, n)
            return intent
        if event == "complete":
            require(d["token"] in p["open"], "completion needs uncompleted durable intent")
            k, n = p["open"][d["token"]]
            external = k in self.spec["stages"][p["stage"]]["external_counters"]
            if external:
                _number(d["actual"], k)
                require(d["actual"] <= n and len({v["path"] for v in d["proofs"]}) >= 2, "external completion needs bounded actual count plus trace/verification pins")
                for proof in d["proofs"]: _P.validate_pin(proof)
            else: require(d["actual"] is None and not d["proofs"], "ordinary completion cannot reduce an intent or import external counts")
            def complete():
                p["open"].pop(d["token"]); p["done"][k] += d["actual"] if external else n; p["evidence"].extend(d["proofs"])
            return complete
        if event == "pending-failure": return lambda: p.update(unresolved=copy.deepcopy(d))
        require(event == "finish" and d["status"] in ("completed", "failed") and d["cleanup_verified"] is True and d["execution_ended"] is True, "known ended cleanup or leave pending")
        _number(d["seconds"], "seconds")
        failed = d["status"] == "failed"
        expected = self.spec["stages"][p["stage"]]["expected"]
        require(failed or (not p["open"] and all(v is None or p["done"][k] == v for k, v in expected.items())), "complete fixed call panel required")
        charge = {k: max(reserve[k], p["intents"][k]) if failed else p["done"][k] for k in p["done"]}
        charge["seconds"] = max(reserve["seconds"], d["seconds"]) if failed else d["seconds"]
        require(failed or charge["seconds"] <= reserve["seconds"], "wall overrun must fail")
        require(d["charged"] == charge and d["durable_intents"] == p["intents"] and d["durable_completed"] == p["done"], "no counter/charge rewrite")
        def finish():
            for k, v in charge.items(): state["charged"][k] += v; state["violated"] |= state["charged"][k] > self.spec["caps"][k]
            for k in p["done"]:
                state["observed"][k] = None if failed and reserve[k] else None if state["observed"][k] is None else state["observed"][k] + p["done"][k]
            if not failed:
                state["completed"].append(p["stage"])
                state["proofs"].update({v["path"]: v for v in d["proofs"]})
            state["failures"] += int(failed); state["pending"] = None
        return finish

    def _read(self, stream):
        stream.seek(0); state = self._empty()
        for line in stream:
            if not line.strip(): continue
            row = json.loads(line); body = {k: v for k, v in row.items() if k != "record_sha256"}
            require(row["schema"] == SCHEMA and row["sequence"] == state["sequence"] and row["previous_sha256"] == state["last_sha256"]
                    and digest(body) == row["record_sha256"], "damaged append-only journal")
            self._apply(state, row["event"], row["data"], state["sequence"])()
            state["sequence"] += 1; state["last_sha256"] = row["record_sha256"]
        return state

    def snapshot(self, state):
        out = copy.deepcopy(state); conservative = dict(state["charged"])
        if state["pending"]:
            for k, v in self.spec["stages"][state["pending"]["stage"]]["reservation"].items(): conservative[k] += v
        c = self.parent["carry"]
        out.update(conservative_including_pending=conservative, cumulative=dict(charged_native_applies=c["charged_native_applies"] + conservative["native_applies"],
            charged_seconds=c["charged_seconds"] + conservative["seconds"], observed_native_applies=None if c["observed_native_applies"] is None or state["observed"]["native_applies"] is None else c["observed_native_applies"] + state["observed"]["native_applies"]))
        return out

    def initialize(self, *, root_go=False):
        require(root_go is True, "explicit root freeze/GO required"); self.verify(); self.protect([str(self.ledger)], accounting=True)
        require(not self.ledger.exists() and not self.ledger.is_symlink(), "never reset/reopen existing journal")
        with self.ledger.open("x+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return Session(self, stream, self._empty())._append("initialized", {"spec": self.spec_pin})

    @contextmanager
    def lease(self):
        require(not self.ledger.is_symlink() and self.ledger.resolve() == self.ledger, "canonical ledger only")
        with self.ledger.open("r+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); state = self._read(stream)
            require(state["sequence"] and state["pending"] is None and not state["failures"] and not state["violated"], "closed unbreached history required; no ordinary retry")
            yield Session(self, stream, state)

    def inspect(self, *, verify=True):
        if verify: self.verify()
        if not self.ledger.exists(): return dict(ledger_initialized=False, carry=copy.deepcopy(self.parent["carry"]))
        with self.ledger.open() as stream: return self.snapshot(self._read(stream))


class Session:
    def __init__(self, owner, stream, state): self.owner, self.stream, self.state = owner, stream, state

    def _append(self, event, data):
        s = self.state; apply = self.owner._apply(s, event, data, s["sequence"])
        body = dict(schema=SCHEMA, sequence=s["sequence"], previous_sha256=s["last_sha256"], event=event, data=data)
        row = dict(body, record_sha256=digest(body)); raw = encoded(row).decode() + "\n"
        self.stream.seek(0, os.SEEK_END); self.stream.write(raw); self.stream.flush(); os.fsync(self.stream.fileno())
        apply(); s["sequence"] += 1; s["last_sha256"] = row["record_sha256"]
        return self.owner.snapshot(s)

    def begin(self, stage, *, argv, guard, inputs=()):
        result = self._append("begin", dict(stage=stage, argv=list(argv), guard=copy.deepcopy(guard), inputs=list(inputs), started=time.monotonic()))
        self.owner.verify(); d = self.owner.spec["stages"][stage]; self.owner.protect(d["outputs"])
        require(not any(Path(p).exists() for p in d["outputs"]), "exclusive NEW outputs required")
        allowed = dict(self.owner.frozen, **self.state["proofs"])
        for p in inputs: require(allowed.get(p["path"]) == p, "input must be frozen or completed-stage proof"); verify_pin(p)
        entrypoints = [argv[0]] + ([argv[1]] if "python" in Path(argv[0]).name.lower() and len(argv) > 1 else [])
        for path in entrypoints: require(allowed.get(str(Path(path).resolve())) == pin(path), "entrypoint must be pinned")
        return result

    def remaining_seconds(self):
        p = self.state["pending"]; require(p is not None, "pending stage required")
        return self.owner.spec["stages"][p["stage"]]["reservation"]["seconds"] - (time.monotonic() - p["started"])

    def intent(self, counter, amount=1):
        require(self.remaining_seconds() > 0, "wall exhausted before call")
        token = self.state["sequence"]; self._append("intent", dict(token=token, counter=counter, amount=amount)); return token

    def complete(self, token, *, actual=None, proofs=()):
        for p in proofs: self._proof(p)
        return self._append("complete", dict(token=token, actual=actual, proofs=list(proofs)))

    def _proof(self, expected):
        pending = self.state["pending"]; require(pending is not None, "pending stage required")
        path = Path(expected["path"]); allowed = dict(self.owner.frozen, **self.state["proofs"])
        require(allowed.get(expected["path"]) == expected or any(path == Path(o) or path.is_relative_to(Path(o))
                for o in self.owner.spec["stages"][pending["stage"]]["outputs"]), "proof outside declared outputs/inputs")
        verify_pin(expected)

    def pending_failure(self, error): return self._append("pending-failure", dict(error=str(error), scope="cleanup/execution unknown; reservation retained"))

    def finish(self, status, *, proofs=(), cleanup_verified=False, execution_ended=False, active_seconds=0.):
        require(cleanup_verified is True and execution_ended is True, "positive cleanup/end evidence required; otherwise pending_failure")
        p = self.state["pending"]; require(p is not None, "pending stage required"); _number(active_seconds, "seconds")
        reserve = self.owner.spec["stages"][p["stage"]]["reservation"]; integrity_error = None; verified = []
        try:
            self.owner.verify()
            for expected in p["inputs"]: verify_pin(expected)
            for expected in list(p["evidence"]) + list(proofs): self._proof(expected); verified.append(expected)
        except (OSError, ValueError) as error: status, integrity_error = "failed", str(error)
        elapsed = max(active_seconds, time.monotonic() - p["started"])
        if elapsed > reserve["seconds"]: status = "failed"
        charge = {k: max(reserve[k], p["intents"][k]) if status == "failed" else p["done"][k] for k in p["done"]}
        charge["seconds"] = max(reserve["seconds"], elapsed) if status == "failed" else elapsed
        return self._append("finish", dict(status=status, seconds=elapsed, charged=charge, durable_intents=dict(p["intents"]),
            durable_completed=dict(p["done"]), proofs=verified, cleanup_verified=True, execution_ended=True, integrity_error=integrity_error))
