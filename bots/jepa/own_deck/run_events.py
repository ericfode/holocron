"""Small append-only experiment feed for local dashboard readers."""
import datetime
import hashlib
import json
import math
import numbers
import os
from pathlib import Path
import threading

import fcntl

SCHEMA = "jepa-run-event/v1"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class RunEvents:
    """One writer per run ID; different runs may append to the same file.

    Every complete line is independently parseable. Readers may ignore a final
    incomplete line during a write; no event is rewritten or removed.
    """
    def __init__(self, path, run_id, commit, config, dataset, limitations, parent_run_id=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id, self.commit = run_id, commit
        # Snapshot provenance so later caller mutations cannot invalidate its hash.
        self.config = json.loads(json.dumps(config, allow_nan=False))
        self.dataset = json.loads(json.dumps(dataset, allow_nan=False))
        self.config_sha256 = digest_json(self.config)
        self.limitations = list(limitations)
        self.parent_run_id = parent_run_id
        self.sequence = 0
        self.phase, self.step = "preparing", 0
        self.lock = threading.RLock()
        if self.path.exists():
            with self.path.open() as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict) or event.get("run_id") != run_id:
                        continue
                    if (event.get("commit") != self.commit or
                            event.get("config_sha256") != self.config_sha256 or
                            event.get("dataset") != self.dataset):
                        raise ValueError("a resumed run must retain its source/config/dataset identity")
                    if isinstance(event.get("sequence"), int) and event["sequence"] > self.sequence:
                        self.sequence = event["sequence"]
                        self.phase, self.step = event["phase"], event["step"]

    def emit(self, kind, phase, step, metrics=None, status=None, artifacts=None, **extra):
        with self.lock:
            if kind not in {"status", "metric", "heartbeat", "artifact", "error"}:
                raise ValueError("unknown run-event kind")
            if isinstance(step, bool) or not isinstance(step, numbers.Integral) or step < 0:
                raise ValueError("step must be a nonnegative integer")
            checked_metrics = {}
            for key, value in (metrics or {}).items():
                if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
                    raise ValueError("metrics must have string keys and finite numeric values")
                checked_metrics[key] = int(value) if isinstance(value, numbers.Integral) else float(value)
            self.sequence += 1
            self.phase, self.step = phase, int(step)
            stamp = utc_now()
            event = dict(schema=SCHEMA, run_id=self.run_id, sequence=self.sequence,
                         event_id=f"{self.run_id}:{self.sequence}", timestamp=stamp,
                         heartbeat_at=stamp, commit=self.commit, config=self.config,
                         config_sha256=self.config_sha256, dataset=self.dataset,
                         phase=phase, step=self.step, kind=kind, metrics=checked_metrics,
                         limitations=self.limitations)
            if self.parent_run_id is not None:
                event["parent_run_id"] = self.parent_run_id
            if status is not None:
                event["status"] = status
            if artifacts is not None:
                event["artifacts"] = artifacts
            if set(event) & set(extra):
                raise ValueError("extra fields cannot replace run-event provenance")
            event.update(extra)
            data = (json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            with self.path.open("a+b", buffering=0) as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                try:
                    # Preserve a crashed writer's partial tail, but isolate it
                    # from the next complete JSON line without rewriting bytes.
                    stream.seek(0, os.SEEK_END)
                    if stream.tell():
                        stream.seek(-1, os.SEEK_END)
                        if stream.read(1) != b"\n":
                            stream.write(b"\n")
                    pending = memoryview(data)
                    while pending:
                        count = stream.write(pending)
                        if not count:
                            raise OSError("run-event append made no progress")
                        pending = pending[count:]
                    os.fsync(stream.fileno())
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            return json.loads(data)

    def heartbeat(self):
        with self.lock:
            return self.emit("heartbeat", self.phase, self.step)
