"""Bounded protocol-v2 exchange through the exact Arena host, with canned simulations.

This does not load forceteki/Kessel, play games, rate bots, or submit anything.
Use a reviewed bundle and the Arena Python interpreter containing wasmtime 49.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

REVISION = "3afa1f8bbf3bc45a08359f15b96291d55c641fa6"
BLOBS = {
    "run.py": "ba056825450d874e0f20b758c298fae4bf6a9d81",
    "bundle.py": "b065fc53391b37a6c6d4cf0fadff603dc4fa9ed1",
    "toolchain.json": "d3673d31ca03b944fa5e4349857fae9decfffd8f",
}


def blob_id(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arena", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True,
                        help="tinygrad-probe/reference.json (synthetic raw observations)")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--max-sims", type=int, default=128)
    parser.add_argument("--message-s", type=float, default=10)
    parser.add_argument("--startup-s", type=float, default=30)
    parser.add_argument("--total-s", type=float, default=60)
    parser.add_argument("--decision-ms", type=int, default=10000)
    parser.add_argument("--fuel", type=int, default=0)
    parser.add_argument("--start-fuel", type=int, default=0)
    parser.add_argument("--allow-no-sim", action="store_true")
    parser.add_argument("--sim-error-at", type=int, default=0,
                        help="return a canned error at this simulation request, exercising fallback")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    out = args.out.resolve()
    if not out.is_relative_to(here):
        parser.error("output must remain inside host-evidence")
    if not (1 <= args.games <= 4 and 1 <= args.max_sims <= 512 and
            0 < args.message_s <= 30 and 0 < args.startup_s <= 30 and 0 < args.total_s <= 120 and
            0 < args.decision_ms <= 60000 and args.fuel >= 0 and args.start_fuel >= 0):
        parser.error("requested bounds exceed this harness's limits")
    out.mkdir(parents=True, exist_ok=False)
    compiled = args.arena.resolve() / "bot" / "compiled"
    checked = {name: blob_id(compiled / name) for name in BLOBS}
    if checked != BLOBS:
        raise ValueError("host sources differ from pinned final Arena revision: " + repr(checked))
    def bundle_digest():
        archive = subprocess.check_output([args.python, "-I", str(compiled / "bundle.py"), "tar",
                                           str(args.bundle.resolve())], timeout=15)
        return hashlib.sha256(archive).hexdigest()
    before_bundle = bundle_digest()
    reference = json.loads(args.reference.read_text())
    fixtures = {case["name"]: case for case in reference["vectors"]}
    root = copy.deepcopy(fixtures["window-p1"]["msg"])
    follow = copy.deepcopy(fixtures["followup-p1"]["msg"])
    hello = copy.deepcopy(fixtures["window-p1"]["hello"])
    hello.update(t="hello", protocol="swu-bot-stdio", v=1, versions=[2], seed=1,
                 bot="host_probe", you="p1", ms=30000, cards=reference["cards"])
    hello.pop("simEngine", None)
    stats_path = out / "host-stats.jsonl"
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8",
                   "SWU_WASM_CACHE": str(out / "compiled-cache"), "WASM_HOST_STATS": str(stats_path)}
    command = [args.python, "-I", str(compiled / "run.py"), str(args.bundle.resolve())]
    if args.fuel:
        command.extend(["--fuel", str(args.fuel)])
    if args.start_fuel:
        command.extend(["--start-fuel", str(args.start_fuel)])
    # The external watchdog also covers blocked stdin/file reads, which an epoch trap alone cannot bound.
    started = time.monotonic()
    deadline = started + args.total_s
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    pending = bytearray()
    stderr = bytearray()
    transcript = []
    timings = []
    sim_count = 0
    sim_operations = {}
    active = False
    stage = 0
    failure = None

    def send(message):
        transcript.append({"direction": "referee_to_bot", "message": message})
        process.stdin.write(json.dumps(message, separators=(",", ":")).encode() + b"\n")
        process.stdin.flush()

    def receive(seconds):
        until = min(deadline, time.monotonic() + seconds)
        while True:
            index = pending.find(b"\n")
            if index >= 0:
                raw = bytes(pending[:index])
                del pending[:index + 1]
                message = json.loads(raw)
                transcript.append({"direction": "bot_to_referee", "message": message})
                return message
            remaining = until - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("bounded host exchange timed out")
            events = selector.select(remaining)
            for key, _ in events:
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    if key.data == "stdout":
                        raise EOFError("host stdout closed before reply")
                    continue
                target = pending if key.data == "stdout" else stderr
                target.extend(data)
                if len(target) > 1 << 20:
                    raise ValueError("host output exceeds 1 MiB bound")

    try:
        for game in range(args.games):
            active = False
            initial_sim_count = sim_count
            hello["seed"] = game + 1
            tick = time.monotonic()
            send(hello)
            ready = receive(args.startup_s)
            if ready.get("t") != "ready" or type(ready.get("v")) is not int or ready["v"] != 2:
                raise ValueError("explicit protocol v2 handshake required")
            if not args.allow_no_sim and ready.get("sim") is not True:
                raise ValueError("this run requires the planner's sim:true handshake")
            timings.append({"game": game, "phase": "hello", "ms": (time.monotonic() - tick) * 1000})
            message = copy.deepcopy(root)
            message.update(seq=1, sim=ready.get("sim") is True, ms=args.decision_ms)
            tick = time.monotonic()
            send(message)
            while True:
                reply = receive(args.message_s)
                if reply.get("t") == "act":
                    index = reply.get("i")
                    if type(index) is not int or not 0 <= index < len(root["actions"]):
                        raise ValueError("final act is not a legal real-observation index")
                    active = False
                    break
                if reply.get("t") != "sim" or not message["sim"]:
                    raise ValueError("unexpected message during decide")
                sim_count += 1
                if sim_count > args.max_sims:
                    raise ValueError("simulation request count exceeds bound")
                operation = reply.get("op")
                sim_operations[str(operation)] = sim_operations.get(str(operation), 0) + 1
                left = max(0, args.decision_ms - int((time.monotonic() - tick) * 1000))
                if left == 0:
                    raise TimeoutError("decision exhausted its ms budget")
                response = {"t": "simulated", "op": operation, "ms": left}
                if sim_count == args.sim_error_at:
                    response["error"] = "canned simulation failure for fallback check"
                    active = False
                elif operation == "end":
                    active = False
                elif operation == "begin":
                    active, stage = True, 0
                    response.update(actor="p1", **{key: root[key] for key in ("state", "prompt", "actions")})
                elif operation == "act" and active:
                    available = follow["actions"] if stage == 1 else root["actions"]
                    index = reply.get("i")
                    if type(index) is not int or not 0 <= index < len(available):
                        raise ValueError("simulated act is not a legal canned-position index")
                    stage += 1
                    if stage == 1:
                        response.update(actor="p1", **{key: follow[key] for key in ("state", "prompt", "actions")})
                    else:
                        response.update(actor="p2", **{key: root[key] for key in ("state", "prompt", "actions")})
                else:
                    response["error"] = "no open canned simulation or unknown operation"
                    active = False
                send(response)
            if not args.allow_no_sim and sim_count == initial_sim_count:
                raise ValueError("planner sent no sim requests for this synthetic decision")
            timings.append({"game": game, "phase": "decide", "ms": (time.monotonic() - tick) * 1000})
            send({"t": "over", "you": "p1", "winner": "p1", "outcome": "won", "round": 4})
            if receive(args.message_s).get("t") != "ok":
                raise ValueError("over must receive ok")
        process.stdin.close()
        process.wait(timeout=min(5, max(0.01, deadline - time.monotonic())))
        if process.returncode != 0:
            raise ValueError("host exited " + str(process.returncode))
    except Exception as error:
        failure = type(error).__name__ + ": " + str(error)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        # Drain finite post-exit stderr without blocking; the direct child owns the descriptors.
        stderr.extend(process.stderr.read((1 << 20) - len(stderr)))
        selector.close()
        try:
            after_bundle = bundle_digest()
            if after_bundle != before_bundle:
                failure = "bundle contents changed during the host exchange"
        except Exception as error:
            after_bundle = None
            failure = "bundle recheck failed: " + repr(error)
        (out / "stderr.txt").write_bytes(stderr)
        (out / "transcript.jsonl").write_text("".join(json.dumps(row) + "\n" for row in transcript))
        host_stats = [json.loads(line) for line in stats_path.read_text().splitlines()] if stats_path.exists() else []
        report = {"ok": failure is None, "failure": failure, "command": command,
                  "bundle_sha256": before_bundle, "bundle_after_sha256": after_bundle,
                  "bundle_unchanged": before_bundle == after_bundle,
                  "stderr_tail": stderr.decode("utf-8", "replace")[-2000:],
                  "arena_revision": REVISION, "verified_host_git_blobs": checked,
                  "fixture": "synthetic window-p1 and followup-p1; canned simulations, no rules engine",
                  "games": args.games, "simulation_requests": sim_count,
                  "simulation_operations": sim_operations, "timings": timings,
                  "host_exit": process.returncode, "elapsed_ms": (time.monotonic() - started) * 1000,
                  "host_stats": host_stats,
                  "scope": "Protocol and host integration only; no full games or gameplay-strength evidence"}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return int(failure is not None)


if __name__ == "__main__":
    raise SystemExit(main())
