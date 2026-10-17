#!/usr/bin/env python3
"""Actual-checkpoint JSONL parity against the vendored JS, without engine games or third-party Python packages."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import shlex
import subprocess
import tempfile
import time


HERE = Path(__file__).resolve().parent
HORIZONS = ("1", "4", "s", "r:face", "r:trade", "r:hold", "r2:face", "r2:trade", "r2:hold")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class JsonProcess:
    """One bounded JSON-lines session; stderr cannot fill a pipe and stall the runtime."""
    def __init__(self, command, config, timeout):
        env = dict(os.environ)
        env["JEPA_CONFIG"] = json.dumps(config, separators=(",", ":"))
        self.stderr = tempfile.TemporaryFile()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, env=env, bufsize=0)
        self.timeout = timeout
        self.buffer = bytearray()

    def __enter__(self):
        return self

    def diagnostics(self):
        self.stderr.seek(0)
        return self.stderr.read()[-4000:].decode("utf-8", errors="replace")

    def send(self, value):
        payload = json.dumps(value, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        try:
            self.process.stdin.write(payload)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise AssertionError(f"runtime stopped while writing: {self.diagnostics()}") from error

    def receive(self):
        deadline = time.monotonic() + self.timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            require(remaining > 0, f"runtime reply exceeded {self.timeout}s: {self.diagnostics()}")
            ready, _, _ = select.select([self.process.stdout], [], [], min(remaining, 0.2))
            if not ready:
                require(self.process.poll() is None, f"runtime exited {self.process.returncode}: {self.diagnostics()}")
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            require(chunk, f"runtime stdout ended: {self.diagnostics()}")
            self.buffer.extend(chunk)
        line, _, rest = self.buffer.partition(b"\n")
        self.buffer = bytearray(rest)
        try:
            return json.loads(line)
        except (ValueError, UnicodeError) as error:
            raise AssertionError(f"invalid runtime JSON: {line[:300]!r}") from error

    def exchange(self, value):
        self.send(value)
        return self.receive()

    def __exit__(self, exc_type, exc, traceback):
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=0.5)
        stderr = self.diagnostics()
        self.stderr.close()
        if exc_type is None:
            require(self.process.returncode == 0, f"runtime exited {self.process.returncode}: {stderr}")


def numeric_errors(actual, expected, tolerance, label):
    require(len(actual) == len(expected), f"{label}: length {len(actual)} != {len(expected)}")
    errors = []
    for index, (got, want) in enumerate(zip(actual, expected)):
        require(isinstance(got, (int, float)) and math.isfinite(got), f"{label}[{index}]: nonfinite/non-numeric result {got!r}")
        error = abs(got - want)
        require(error <= tolerance, f"{label}[{index}]: {got} != {want}, error {error} > {tolerance}")
        errors.append(error)
    return max(errors, default=0.0)


def best(values):
    return max(range(len(values)), key=values.__getitem__) if values else None


def check_tensors(session, reference, tolerance):
    maximum_value = maximum_logits = 0.0
    checks = 0
    expected_predict_calls = 0
    stats = None
    for vector in reference["vectors"]:
        for network_name, role in (("model", "raw"), ("windowModel", "evaluator")):
            network = vector["networks"][network_name]
            require(set(network["predictions"]) == set(HORIZONS), f"{vector['name']}: missing horizon")
            for horizon in HORIZONS:
                reply = session.exchange({"t": "tensor", "encoded": vector["encoded"], "role": role, "horizon": horizon})
                require(reply.get("t") == "tensor", f"unexpected tensor response: {reply}")
                label = f"{vector['name']} / {role} / {horizon}"
                value_error = numeric_errors([reply["value"]], [network["context"]["valueLogit"]], tolerance, label + " context")
                expected = network["predictions"][horizon]["logits"]
                logit_error = numeric_errors(reply["logits"], expected, tolerance, label + " logits")
                require(best(reply["logits"]) == best(expected), f"{label}: best-action index differs")
                maximum_value = max(maximum_value, value_error)
                maximum_logits = max(maximum_logits, logit_error)
                expected_predict_calls += math.ceil(vector["encoded"]["actions"]["n"] / 4)
                checks += 1
                stats = reply["kernelStats"]
    require(checks == len(reference["vectors"]) * 2 * 9, "tensor coverage incomplete")
    require(stats["contextCalls"] == len(reference["vectors"]) * 2, f"context cache did not reuse the model's encoding: {stats}")
    require(stats["predictCalls"] == expected_predict_calls, f"candidate batching changed: {stats}")
    require(stats["cacheHits"] >= checks, f"expected context cache hits: {stats}")
    return {"cases": checks, "distinctContexts": len(reference["vectors"]) * 2,
            "maximumContextValueError": maximum_value, "maximumLogitError": maximum_logits,
            "allBestActionIndicesMatch": True, "kernelStats": stats}


def decide_with_transcript(session, message, transcript, cursor, label):
    session.send(message)
    for _ in range(len(transcript) - cursor + 1):
        reply = session.receive()
        if reply.get("t") != "sim":
            return reply, cursor
        require(cursor < len(transcript), f"{label}: unexpected extra sim request {reply}")
        expected = transcript[cursor]
        require(reply == expected["request"], f"{label}: sim request {cursor} {reply} != {expected['request']}")
        session.send(expected["reply"])
        cursor += 1
    raise AssertionError(f"{label}: exceeded bounded simulation transcript")


def check_vectors(session, reference):
    names = []
    for vector in reference["vectors"]:
        require(session.exchange(vector["hello"]) == vector["ready"], f"{vector['name']}: hello differs")
        reply, consumed = decide_with_transcript(session, vector["msg"], [], 0, vector["name"])
        require(reply == vector["reply"] and consumed == 0, f"{vector['name']}: act differs: {reply}")
        require(session.exchange({"t": "over"}) == vector["over"], f"{vector['name']}: over differs")
        names.append(vector["name"])
    return {"cases": len(names), "allRepliesMatch": True, "names": names}


def check_behavior(command_for, reference, timeout):
    reports = []
    for case in reference["behaviors"]:
        config = case["settings"]
        command = command_for(config)
        with JsonProcess(command, config, timeout) as session:
            require(session.exchange(case["hello"]) == case["ready"], f"{case['name']}: hello differs")
            reply, consumed = decide_with_transcript(session, case["msg"], case["transcript"], 0, case["name"])
            require(reply == case["reply"], f"{case['name']}: action {reply} != {case['reply']}")
            follow = case.get("followup")
            if follow:
                reply, consumed = decide_with_transcript(session, follow["msg"], case["transcript"], consumed, case["name"] + " follow")
                require(reply == follow["reply"], f"{case['name']}: follow-up action differs: {reply}")
            require(consumed == len(case["transcript"]), f"{case['name']}: unconsumed simulator messages")
            stats = session.exchange({"t": "stats"})
            require(stats.get("t") == "stats", f"{case['name']}: diagnostics unavailable: {stats}")
            require(stats["controller"] == case["stats"], f"{case['name']}: controller statistics differ: {stats['controller']} != {case['stats']}")
            require(session.exchange({"t": "over"}) == {"t": "ok"}, f"{case['name']}: over differs")
            reports.append({"name": case["name"], "gate": config["plan"]["gate"], "simulatorMessages": consumed,
                            "rootPick": case["reply"]["i"], "followPick": follow["reply"]["i"] if follow else None,
                            "controllerStats": stats["controller"], "kernelStats": {k: v for k, v in stats.items() if k not in ("t", "controller")}})
    return {"cases": len(reports), "allRepliesAndTranscriptsMatch": True, "reports": reports}


def check_backend(name, command_for, reference, args, artifact):
    started = time.monotonic()
    config = reference["settings"]
    with JsonProcess(command_for(config), config, args.timeout) as session:
        tensors = check_tensors(session, reference, args.tolerance)
        vectors = check_vectors(session, reference)
    behavior = check_behavior(command_for, reference, args.timeout)
    return {"backend": name, "artifact": str(artifact.resolve()), "artifactSha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "artifactBytes": artifact.stat().st_size, "tensors": tensors, "vectors": vectors,
            "behavior": behavior, "elapsedSeconds": round(time.monotonic() - started, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, help="diagnostic native runtime binary")
    parser.add_argument("--wasm", type=Path, help="diagnostic WASI runtime module")
    parser.add_argument("--wasm-runner", default="wasmtime run", help="Wasmtime command prefix; parsed without a shell")
    parser.add_argument("--reference", type=Path, default=HERE / "fixtures/runtime-reference.json")
    parser.add_argument("--timeout", type=float, default=20.0, help="seconds allowed for each runtime reply")
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    require(args.native or args.wasm, "provide --native and/or --wasm")
    reference = json.loads(args.reference.read_text())
    report = {"schema": "swu-jepa-runtime-parity/1", "reference": str(args.reference.resolve()),
              "referenceSha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              "provenance": reference["provenance"], "absoluteTolerance": args.tolerance, "backends": []}
    if args.native:
        native = args.native.resolve()
        report["backends"].append(check_backend("native", lambda _: [str(native)], reference, args, native))
    if args.wasm:
        wasm = args.wasm.resolve()
        prefix = shlex.split(args.wasm_runner)
        def command(config):
            return prefix + ["--env", "JEPA_CONFIG=" + json.dumps(config, separators=(",", ":")), str(wasm)]
        report["backends"].append(check_backend("wasm-wasi", command, reference, args, wasm))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "backends": [{"name": b["backend"], "tensorCases": b["tensors"]["cases"],
          "maximumContextValueError": b["tensors"]["maximumContextValueError"], "maximumLogitError": b["tensors"]["maximumLogitError"],
          "vectorReplies": b["vectors"]["cases"], "scriptedCases": b["behavior"]["cases"], "elapsedSeconds": b["elapsedSeconds"]} for b in report["backends"]],
          "report": str(args.report) if args.report else None}))


if __name__ == "__main__":
    main()
