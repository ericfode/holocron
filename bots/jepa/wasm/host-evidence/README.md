# Final Arena host evidence

Target: Arena `3afa1f8bbf3bc45a08359f15b96291d55c641fa6`.
The task-local Arena checkout's HEAD is older, but the host, checker, transport,
guard and intake files listed in `final-host-blobs.json` were fetched at the target
revision and have identical Git blobs locally. No production service was read or
changed. This folder does not contain a deployable JEPA controller.

## Actual limits

- The normal command is `python3 -I bot/compiled/run.py bundle`, with the bot's
  frozen version as cwd (`bot/arena/registry.js:27,39,65`). There is no `--fuel`,
  `--wall-s` or explicit memory override. Fuel and epochs default to disabled.
- `resources.memory_mb` is used: a positive integer, else 512 MiB, capped at 1024
  MiB. One linear memory, eight tables, four instances and 1,000,000 table elements
  are allowed (`run.py:192–196`). `resources.start_ms` / `decide_ms` are not read.
- Admission sends `hello.v:1, versions:[2]`, requires explicit `ready.v:2` and
  verifies the trusted checker's `negotiatedProtocol:2` result. It allows 30 s for
  startup/hello, with an outer 35 s kill (`bot/arena/api.js:178–217`).
- Games charge the standalone program's aggregate wall time for hello and
  decisions, including simulations. `ms` is the remaining game bank, not a fixed
  10 s allowance (`bot/players/guard.js:94–150,220–235`). The round chooses capMs;
  defaults in source do not prove today's live setting. Rated watchdogs are
  `hangMs=2*capMs+30000`, `gameMs=4*capMs+600000`, 6000 steps
  (`bot/game-pool.js:38–48`).
- Optional `--fuel N` refills after every non-sim stdout line; `t:sim` lines do not
  refill. It therefore covers the complete decide exchange, including all guest
  work between simulated replies. The host classifies stdout lines but does not
  validate protocol correctness at the refill hook (`run.py:214–232`). Fuel is
  approximately WASM instruction work, not elapsed time or FLOPs.
- Host `startup_ms` stops before guest `_start`; externally measured hello latency
  includes guest imports and weight loading (`run.py:281–288`).
- Kernel proof fuel around 116.7 million was measured on CLI Wasmtime 44.0.1,
  fixed four-action monolithic inference, with startup/binding. It is neither an
  Arena cap nor pinned Wasmtime 49 evidence nor complete decision cost.

## Bounded v2 protocol harness

`exercise_host.py` executes the unchanged final host using a supplied reviewed
bundle. It verifies host Git blobs before running, then exchanges v2-only hello,
one synthetic decide, sequential sim begin/act/end responses and over→ok, twice
in the same process. Simulation responses are canned synthetic board positions
from `tinygrad-probe/reference.json`; there is no rules engine or real game.
It rejects invalid final indices, caps sim count/line bytes/wall time, supplies
decreasing `ms`, kills the child at its external deadline, and writes a full
transcript, stderr, external hello/decide timings and host stats.

```sh
python3 exercise_host.py \
  --arena ../../../../../jepa-wasm \
  --bundle /absolute/path/to/reviewed-bundle \
  --reference ../../../../../tinygrad-probe/reference.json \
  --python /absolute/path/to/python-with-wasmtime49 \
  --out actual-controller-smoke
```

Use `--sim-error-at 2` to test simulation-error handling. Use `--fuel` and
`--start-fuel` only for diagnostic runs, clearly separate from Arena's actual
invocation. The script defaults to 2 sessions, 128 total sim requests, 30 s first
reply, 10 s subsequent line timeout and 60 s total. It is stricter than production
transport about line size and never attempts network access or submission.

## Minimal CPython WASI baseline

`protocol_fixture.py` uses only json/sys. It explicitly negotiates v2, performs
four sim requests per decide (begin, two acts, end), returns act 0, and acknowledges
over. It has no model, features or planner. `prepare_probe.py probe-bundle` creates
the source bundle to measure interpreter+JSON+transport overhead when the pinned
runtime is available. No NumPy, tinygrad or runtime machine-code generation is
required by this baseline.

Arena's `python-3.14-wasi` is pinned CPython 3.14.7, standard library only, with
read-only lib mounted at `/usr/local/lib`, plus the bundle at `/bot`. It does not
provide NumPy or a host hook to call the separately exported kernel. A real
Python controller needs a compatible generated-C integration (such as a built-in
extension in a rebuilt CPython WASI) or a different reviewed route. That integration
and its total memory/startup/decision cost have not been demonstrated here.

The parent task provisioned pinned Wasmtime 49.0.0 in
`task-4/runtime-venv/bin/python`; this interpreter passes `-I` import and runs the
native controller. The official CPython WASI release-asset download remains
blocked, so no Python-interpreter overhead number is available. The ignored
`blocked-host-run/` folder is an earlier failed attempt using system Python before
the pinned interpreter existed; it is superseded by the successful final native
checks below.

## Executed native controller results

The parent task built `holocron-wasm/build/arena/jepa_tx_gate_wasm` from published
source commit `6485d31df4bb15242e02f281b8ddd4176aedd931`, with source SHA-256
`570ec9d86e6a4e86bae273ff458902a0294575e37c3a9815df95746c4fe89cd5`.
Its frozen entry is 2,534,886 bytes, SHA-256
`6356747ac4ca162c61d4c6c8cfd3b2620edb033c498274e9e5162e5dd3a0f2e3`.
The final checker accepted it, and independently hashing the canonical tar agrees
with checker ID
`80ed5c894dec3763971bdbeefbbf10a69064736ae6e65b9b85e287037671691c`.
Tar size is 2,549,760 bytes; reproducible gzip is 1,963,050 bytes. Imports are only
WASI preview1 clock, environment, stdin/stdout and exit functions. The native
manifest honestly declares `deterministic:false` because the planner has a clock
deadline. Validation details and the exact tar are in `final-bundle-check/`.

All three final runs below assert the exact final Arena host blobs, use pinned
Wasmtime 49.0.0, and hash the complete canonical bundle before and after execution.
All six hashes match the checker ID above. Each runs two synthetic sessions in
one guest process; these are not full games or real-engine simulations.

| Result directory | Mode | Sim requests | Final replies | Exit | Linear memory |
|---|---|---:|---:|---:|---:|
| `final-host-normal/` | actual Arena invocation, no fuel flag | 50 (16 begin, 32 act, 2 end) | 6 | 0 | 16 MiB |
| `final-host-error/` | inject simulation error at request 2 | 46 (15 begin, 29 act, 2 end) | 6 | 0 | 16 MiB |
| `final-host-fuel/` | diagnostic fuel 1 billion per final reply | 50 | 6 | 0 | 16 MiB |

There was no stderr in these runs. Every session explicitly negotiated
`ready.v:2,sim:true`, returned a legal real-action index and acknowledged `over`.
The error run continued after its injected failure, cleaned up and completed the
second session as well. Normal-run externally measured first hello was 95.56 ms,
second hello 0.131 ms, and decides 8.02/6.93 ms. Cold module compilation was
32.5 ms. These are tiny synthetic decisions on this Mac; they do not establish
full-game time-bank fitness or process RSS.

The fuel diagnostic consumed 390,194,848 units across six final reply intervals;
maximum was 197,039,573 for one complete exchange. Sim output did not refill fuel.
This enables fuel only for measurement; Arena's actual command still has no fuel
flag. Source-level admission rules and transport are verified, but the hosted
admission function was not invoked and no submission or rated game ran.

Earlier `native-*` folders retain preliminary build measurements. Only the
`final-*` folders and `final-host-summary.json` describe the frozen bundle above.
Raw run folders, compiled caches and tar files are ignored; the parent task
curates compact public validation evidence separately.

## Bundle and digest check

The tiny source probe passes the final checker's manifest validation:

```
v2_interpreter_probe sha256:cfafe7d577c10ae9c613b5c7d12c6526e60604623555c9d5044eae1d21660e58
tar 10240 B, gzip 1000 B
```

That acceptance proves file/manifest consistency, not runtime availability.
`bundle.py` checks integer protocol 2, kind/platform, entry existence,
optional entry digest and no network. Runtime availability and WASM module
validation happen in `run.py` later. `entry_sha256` hashes entry bytes;
the submission identifier hashes the complete canonical tar, including the
manifest and support files (`bundle.py:48–125`).

`check_native_bundle.py` strictly checks the finished native manifest and entry
hash, runs the unchanged final Arena checker, reproduces the canonical tar hash,
validates and compiles the module with pinned Wasmtime 49 without invoking it,
checks WASI-only imports plus `_start`/memory exports, and confirms the source
folder did not change during validation. It writes the tar and JSON evidence
inside this folder only. Example, from this folder:

```sh
../../../../../runtime-venv/bin/python -I check_native_bundle.py \
  --arena ../../../../../jepa-wasm \
  --bundle ../../../../build/arena/jepa_tx_gate_wasm \
  --out fresh-final-bundle-check
```

For the actual native controller, use protocol 2, kind `wasm`, platform
`wasm32-wasip1`, runtime `wasi-p1`, `run.cmd:./bot.wasm`, empty args/env, accurate
entry SHA-256, requested memory and network none. Keep build/checkpoint/exporter
provenance with the source and package. Check the finished folder with:

```sh
python3 -I /path/to/final-arena/bot/compiled/bundle.py /path/to/bundle
python3 -I /path/to/final-arena/bot/compiled/bundle.py tar /path/to/bundle > bundle.tar
shasum -a 256 bundle.tar
```

The printed bundle ID and tar SHA-256 must agree. The actual start check and
bounded exchange then use exactly that digest's contents; do not rebuild or
change manifests between validation and measurement. Direct uploaded source
files have a 16,000,000-byte total API limit; canonical tar transfer separately
allows 64 MiB of files and 2000 entries. Report both size routes explicitly.
