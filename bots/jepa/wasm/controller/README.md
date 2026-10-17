# JEPA controller

This crate ports the current table `jepa-tx-gate` policy from `bots/jepa/js/jepa.js`. It contains no matrix kernels,
checkpoint parsing, training, game engine, or platform-specific stdio loop. A host supplies numerical inference and
the protocol simulation exchange through two traits:

```rust,ignore
trait Model {
    fn predict_values(&mut self, role: ModelRole, e: &Encoded, horizon: &str)
        -> Result<Vec<f64>, String>; // one raw value logit per candidate action
    fn context_value(&mut self, role: ModelRole, e: &Encoded)
        -> Result<f64, String>;      // raw value logit of the observed position
}
trait Simulator {
    fn request(&mut self, request: serde_json::Value) -> Result<serde_json::Value, String>;
}
```

`ModelRole::Raw` means the original outcome-trained checkpoint; `Evaluator` means its evaluator-head copy.
`Encoded` retains the JS shapes: state `[73]`, action rows `[n * 62]` plus `[n]` hashed IDs, and up to 32 card tokens
with `[n * 21]` features plus IDs. The inference backend truncates/pads tokens to its checkpoint's 24 slots and is
responsible for tensor layout, context caching, and action batching. Features are calculated in float64 then cast
to float32, like JS's `Float32Array`; policy scores stay float64.

Create `JepaBot::new(Config::default())`. Send each game's `hello` to `hello(&msg)`, which rebuilds card tables from
`hello.cards` and resets RNG, search plan, counters, and loop guard. `decide(&msg, &mut model, &mut sim)` returns
`{"t":"act","i":...}`; the simulator callback exchanges each `sim` request for its `simulated` reply synchronously.
`over()` returns `{"t":"ok"}`. Nothing reads card files or hidden real hands.

Defaults preserve the table: settled horizon for windows/action follow-ups, evaluator head for imagined choices,
raw head for simulated leaves, c-clock resourcing, gate 0.04, 16 roots, follow-up widths 6/3, depth 2, 150 lines,
5 seconds, and a 2,500 ms simulator-time margin. Search compares candidates on deal 0 and uses the existing rush
rule for opponent follow-ups. Final choices retain the JS loop guard and follow-up signature matching. The crate
supports the JS `imagined` mode and horizon mixing for comparison; other resource policies are rejected.

The host must keep one outstanding protocol request, flush newline JSON, and include simulation time in the
decision budget. `decide.ms` itself is not a compute watchdog: the controller follows the existing policy, checking
the simulator's remaining `ms` and the planner's monotonic clock. The WASM host/referee enforces the final deadline.

The current build route uses the installed `wasm32-unknown-unknown` Rust target and explicit WASI preview 1 imports;
it does not use the standard `wasm32-wasip1` target or its standard-library I/O. The controller imports only
`wasi_snapshot_preview1.clock_time_get` for its monotonic planner clock on wasm32. A nonzero WASI errno or a
backwards clock returns an error through `decide`, rather than calling an unsupported standard-library time
function. Native builds retain `std::time::Instant`. The outer runtime supplies the WASI stdin/stdout imports and
links the generated numerical objects and math library. A full WASI SDK remains optional for that route.

Run the independent native parity checks without downloading dependencies:

```sh
cargo test --offline --manifest-path bots/jepa/wasm/controller/Cargo.toml
```

The integration test source and JS-generated golden fixtures live in `../tests/`. They exercise exact input bits,
hashes, c-clock choices, Python-compatible random draws, and scripted v2 planning. Numerical model/kernel parity is
the inference backend's separate check.
