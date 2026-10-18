#!/usr/bin/env python3
"""Bounded own-deck engineering parity; no games, training, or strength claims."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

from check_runtime import JsonProcess, best, check_tensors, numeric_errors, require, runtime_source_pins


HERE = Path(__file__).resolve().parent


def tensor(encoded):
    return {"t": "tensor", "encoded": encoded, "role": "raw", "horizon": "s"}


def check_boundaries(command, reference, timeout):
    neutral = next(copy.deepcopy(v["encoded"]) for v in reference["vectors"]
                   if v["encoded"].get("own_deck", {}).get("variant") == "neutral")
    absent = copy.deepcopy(neutral)
    absent.pop("own_deck")
    with JsonProcess(command, {}, timeout) as session:
        explicit = session.exchange(tensor(neutral))
        implicit = session.exchange(tensor(absent))
        numeric_errors([implicit["value"]], [explicit["value"]], 0, "implicit neutral context")
        numeric_errors(implicit["logits"], explicit["logits"], 0, "implicit neutral logits")
        require(implicit["kernelStats"]["contextCalls"] == 1,
                "absent and explicit neutral must share the same actual tensor cache key")
        # Change the first and last row's last feature independently: both rows
        # must participate in the cache key even when visible cards are unchanged.
        for row, index in enumerate((206, 413), 1):
            changed = copy.deepcopy(neutral)
            changed["own_deck"]["features"][index] += 1 / 60
            reply = session.exchange(tensor(changed))
            require(reply["kernelStats"]["contextCalls"] == row + 1,
                    "own-deck row change reused stale context")
    checks = []
    for label, edit, expected in (
        ("shape", lambda e: e["own_deck"]["features"].pop(), "own-deck context version or shape mismatch"),
        ("version", lambda e: e["own_deck"].update(version=999), "own-deck context version or shape mismatch"),
        ("nonfinite", lambda e: e["own_deck"]["features"].__setitem__(2, 1e100), "nonfinite own-deck context"),
    ):
        malformed = copy.deepcopy(neutral)
        edit(malformed)
        proc = subprocess.run(command, input=json.dumps(tensor(malformed)) + "\n",
                              capture_output=True, text=True, timeout=timeout)
        require(proc.returncode != 0 and expected in proc.stderr,
                f"malformed own-deck {label} was not rejected before kernel execution: {proc.stderr[-1000:]}")
        checks.append(label)
    return {"implicitNeutralMatchesExplicit": True, "bothDeckRowsInvalidateCache": True,
            "malformedContextsRejected": checks}


def check_protocol(command_for, reference, protocol_reference, timeout):
    """Use ordinary hello/decide, never diagnostic injection or a simulator."""
    own_hello = reference["ownDeckHello"]
    expected = {v["name"]: v for v in reference["vectors"]}
    cases = []
    for variant in ("neutral", "original", "original-plus-remaining"):
        config = {"ownDeck": variant, "score": "plan", "mix": 0,
                  "windowHorizon": "s", "followHorizon": "s", "resource": "c-clock",
                  "plan": {"gate": 1e9}}
        with JsonProcess(command_for(config), config, timeout) as session:
            for vector in protocol_reference["vectors"]:
                if not vector["msg"]["prompt"].get("actionWindow"):
                    continue
                hello = copy.deepcopy(vector["hello"])
                hello["deck"] = copy.deepcopy(own_hello["deck"])
                hello["cards"].extend(copy.deepcopy(own_hello["cards"]))
                require(session.exchange(hello) == vector["ready"], "own-deck ordinary hello differs")
                message = copy.deepcopy(vector["msg"])
                message["sim"] = False
                name = variant + "/" + vector["name"]
                target = expected[name]
                if variant != "neutral":
                    require(target["encoded"]["own_deck"]["features"][3] == 1,
                            "ordinary protocol check must use a known original deck")
                pick = best(target["networks"]["windowModel"]["predictions"]["s"]["logits"])
                reply = session.exchange(message)
                require(reply == {"t": "act", "i": pick}, f"{name}: ordinary own-deck choice {reply} != {pick}")
                stats = session.exchange({"t": "stats"})["controller"]
                require(stats["planned"] == 0 and stats["gated"] == 1,
                        f"{name}: ordinary protocol check unexpectedly planned: {stats}")
                require(session.exchange({"t": "over"}) == {"t": "ok"}, "ordinary own-deck over differs")
                cases.append({"name": name, "pick": pick})
    return {"cases": len(cases), "allChoicesMatchNumpy": True,
            "resourcePolicy": "c-clock", "simulatorMessages": 0, "reports": cases}


def check_backend(name, command_for, artifact, reference, protocol_reference, args):
    started = time.monotonic()
    command = command_for({})
    with JsonProcess(command, {}, args.timeout) as session:
        tensors = check_tensors(session, reference, args.tolerance)
    boundaries = check_boundaries(command, reference, args.timeout)
    protocol = check_protocol(command_for, reference, protocol_reference, args.timeout)
    return {"backend": name, "artifact": str(artifact.resolve()),
            "artifactSha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "artifactBytes": artifact.stat().st_size, "tensors": tensors, "boundaries": boundaries,
            "protocol": protocol,
            "elapsedSeconds": round(time.monotonic() - started, 3)}


def check_legacy(name, command, reference, timeout):
    encoded = reference["vectors"][0]["encoded"]
    proc = subprocess.run(command, input=json.dumps(tensor(encoded)) + "\n",
                          capture_output=True, text=True, timeout=timeout)
    require(proc.returncode != 0 and "requires the opt-in own-deck runtime feature" in proc.stderr,
            f"legacy {name} silently ignored supplied deck context: {proc.stderr[-1000:]}")
    return {"backend": name, "suppliedDeckContextRejected": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--wasm", type=Path)
    parser.add_argument("--baseline-native", type=Path, help="optional legacy diagnostic binary; must fail closed on own-deck input")
    parser.add_argument("--baseline-wasm", type=Path)
    parser.add_argument("--wasm-runner", default="wasmtime run")
    parser.add_argument("--reference", type=Path, default=HERE / "fixtures/own-deck-runtime-reference.json")
    parser.add_argument("--protocol-reference", type=Path, default=HERE / "fixtures/runtime-reference.json")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    require(args.native or args.wasm, "provide --native and/or --wasm")
    reference = json.loads(args.reference.read_text())
    protocol_reference = json.loads(args.protocol_reference.read_text())
    sources = runtime_source_pins("generated-own-deck")
    report = {"schema": "swu-jepa-own-deck-runtime-parity/1", "purpose": "engineering fixture only",
              "reference": str(args.reference.resolve()),
              "referenceSha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              "protocolReferenceSha256": hashlib.sha256(args.protocol_reference.read_bytes()).hexdigest(),
              "provenance": reference["provenance"], "absoluteTolerance": args.tolerance,
              "sourcePins": sources, "backends": [], "legacyBoundaries": []}
    if args.native:
        artifact = args.native.resolve()
        report["backends"].append(check_backend("native", lambda _: [str(artifact)], artifact, reference, protocol_reference, args))
    if args.wasm:
        artifact = args.wasm.resolve()
        prefix = shlex.split(args.wasm_runner)
        def command_for(config):
            return prefix + ["--env", "JEPA_CONFIG=" + json.dumps(config, separators=(",", ":")), str(artifact)]
        report["backends"].append(check_backend("wasm-wasi", command_for, artifact, reference, protocol_reference, args))
    if args.baseline_native:
        report["legacyBoundaries"].append(check_legacy("native", [str(args.baseline_native.resolve())], reference, args.timeout))
    if args.baseline_wasm:
        command = shlex.split(args.wasm_runner) + [str(args.baseline_wasm.resolve())]
        report["legacyBoundaries"].append(check_legacy("wasm-wasi", command, reference, args.timeout))
    require(runtime_source_pins("generated-own-deck") == sources, "runtime sources changed during verification")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "purpose": report["purpose"], "backends": [
        {"name": b["backend"], "tensorCases": b["tensors"]["cases"],
         "maximumContextValueError": b["tensors"]["maximumContextValueError"],
         "maximumLogitError": b["tensors"]["maximumLogitError"],
         "boundaries": b["boundaries"], "ordinaryProtocolCases": b["protocol"]["cases"],
         "elapsedSeconds": b["elapsedSeconds"]}
        for b in report["backends"]], "legacyBoundaries": report["legacyBoundaries"],
        "report": str(args.report) if args.report else None}))


if __name__ == "__main__":
    main()
