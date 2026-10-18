# Frozen implementation and host evidence

Source commit: `6485d31df4bb15242e02f281b8ddd4176aedd931`, based on Holocron `f00df42`.
The final evidence commit adds tests/reports/docs without changing runtime source inputs.
Arena compatibility target: `3afa1f8bbf3bc45a08359f15b96291d55c641fa6`; exact host/checker blobs are recorded.

| Object | SHA-256 | Bytes |
|---|---|---:|
| `bot.wasm` | `6356747ac4ca162c61d4c6c8cfd3b2620edb033c498274e9e5162e5dd3a0f2e3` | 2,534,886 |
| Canonical Arena tar / bundle ID | `80ed5c894dec3763971bdbeefbbf10a69064736ae6e65b9b85e287037671691c` | 2,549,760 |
| Gzip of canonical tar | `89001a8c4245cd4110824af348d2396d5758758bfe8dcc4465a937262d604bb4` | 1,963,050 |

`build/arena/jepa_tx_gate_wasm.tar.gz` is the local transferable bundle. The canonical tar hash, rather than the gzip
hash, is Arena's bundle identifier. `bundle.json` includes the complete manifest, entry digest, source-file hashes,
unchanged checkpoint hashes, Wasmtime49 import/export checks and final checker output. All recorded before/after
digests agree. The two checkpoint files already tracked in the repository are unmodified.

- `runtime-parity.json`: actual-weight diagnostic native and CLI Wasmtime44 runs, 126 tensor combinations each,
  seven normal decisions and six exact scripted planner transcripts. Max value-logit error 1.35e-6 and action-logit
  error 3.12e-6 at absolute tolerance 1e-5; best indices match. This artifact enables test-only diagnostics.
- `production-parity.json`: final production entry hash above, seven ordinary decisions, six exact JS simulator
  transcripts and five strict-protocol rejection cases. Diagnostics are disabled in this module.
- `handshake.json`: actual hello/ready/decide/sim/simulated/act/over/ok messages selected from the isolated final-host
  exchange, including synthetic card and observation context; full transcript digest retained.
- `host-normal.json`, `host-simulator-error.json`, `host-diagnostic-fuel.json`, `host-summary.json`: unchanged final
  Arena host plus pinned Wasmtime49, two synthetic sessions per run, normal/error recovery/optional diagnostic fuel.
  All exit0, no stderr, 16 MiB linear memory. Normal first hello 95.56 ms; decisions 8.02/6.93 ms on this Mac.

Normal host invocation enables no fuel or epoch limit. The separate 1-billion-fuel diagnostic run consumed
390,194,848 total, maximum 197,039,573 for a whole exchange. Sim requests never replenish that budget. These figures
are neither a configured production cap nor a worst-case search bound. Resident process memory was not measured.
The source's default game bank is 60 seconds; today's live Arena setting was not queried.

Paths in curated reports use `$TASK_ROOT` for this task's workspace. Full raw transcripts, host caches, generated
temporary objects and tar files remain outside Git. The tests use synthetic observations and canned simulator
responses; they do not establish full-game strength, live deadlines or hosted eligibility. No training, engine games,
admission, submission or production change ran. The CPython-WASI overhead comparison remains unmeasured because
that separate guest runtime was unavailable; normal pip installation supplies the host Wasmtime49 dependency.
