# Reproduce the tinygrad JEPA kernels

The checked-in `../generated/*.c` files are generated from the existing
`tx-t10.safetensors` checkpoint. No optimizer, training loop, retraining, objective
change, or checkpoint rewrite is part of this recipe. The evaluator checkpoint
uses the same graph with its existing replacement value head.

The numerical source is `export_cached.py`, with shared layer/input helpers in
`export_jepa.py`. It exports a board encoder returning per-layer context keys and
values, then a four-candidate predictor at one selected horizon. The original
structural attention mask makes candidate tokens independent, so this split
reuses context without changing which tokens attend to each other.

## Pinned dependency

Provide an existing tinygrad checkout at commit
**`87378331e816d8c9ed71328569efa08f6bcb50fc`**:

<https://github.com/tinygrad/tinygrad/tree/87378331e816d8c9ed71328569efa08f6bcb50fc>

This recipe does not fetch or install tinygrad. The local proof used Python
3.14.3, `DEV=CPU:CLANGJIT`, `CPU_COUNT=1`, and the existing Clang compiler. Do not
substitute the Metal/CUDA renderer: these are generic C exports for native/WASM
compilation, independent of a later training device.

`TINYGRAD-LICENSE` preserves tinygrad's MIT license. The full framework source is
not duplicated here.

## Re-export

From `bots/jepa/wasm`, with `TINYGRAD_CHECKOUT` set to that provided checkout:

```sh
PYTHONPATH="$TINYGRAD_CHECKOUT" DEV=CPU:CLANGJIT CPU_COUNT=1 python3 export/export_cached.py --export-only --out generated
```

`--export-only` supplies synthetic input buffers with 11 visible tokens and four
candidate slots. Inputs are runtime buffers, not specialized constants. The
values do not influence Python control flow; only the fixed context and batch
shapes define the compiled graph. This path does not need a reference fixture.

Default paths are resolved relative to the script:

- `--models`: `bots/jepa/models`
- `--out`: `bots/jepa/wasm/generated`
- `--reference`: `bots/jepa/wasm/tests/fixtures/runtime-reference.json`

All three can be overridden. Re-exporting writes C, binding JSON, the ABI header,
and small export metadata/browser-wrapper files under `--out`. The browser JS
wrapper is diagnostic output only; the Rust runtime calls prefixed C functions
directly. Neither Emscripten nor a Python/tinygrad runtime is needed by the bot.

To use an independent reference observation for capture and compare numeric
outputs on this Mac:

```sh
PYTHONPATH="$TINYGRAD_CHECKOUT" DEV=CPU:CLANGJIT CPU_COUNT=1 python3 export/export_cached.py --export --build-native --native-check --out /tmp/jepa-reexport
```

The compact runtime fixture retains logits and may omit latent arrays. Checks
compare all available arrays and both checkpoint roles over all nine horizons;
omitted latent arrays are not claimed as checked. `--tinygrad-check` optionally
compares the Python graph instead. `--build-native` uses local Clang to build
Mac `.dylib` files. Keep temporary artifacts outside the source tree when only
checking reproduction.

## Export boundary adaptations

The pinned exporter has a buffer-name key mismatch and deduplicates repeated
kernel calls while traversing a memory-planned sequence. This recipe corrects
those orchestration details without editing generated arithmetic:

1. Match weights with the exact `(base, offset, size, dtype)` buffer key.
2. Preserve the captured LINEAR call order, including repeated calls after
   scratch has changed; reject unsupported non-kernel schedule entries.
3. Realize output tensors together so exported cache views do not cause encoder
   recomputation.
4. Require single-threaded kernels and bind every saved weight/constant.
5. Mechanically prefix external function and buffer names so both objects link.
6. Spell intermediate 64-bit integers `long long`; WASM C's `long` is 32-bit.

The runtime ABI is documented in `../generated/jepa_cached.h`. The local
host-LLVM-to-wasm32 build retains an i64 setter index and wasm32 pointers; the
Rust backend declares that exact ABI. A fresh WASI SDK C build has a different
`size_t` width and must update the setter declaration accordingly.

## Reproduction evidence

`generated-baseline.json` records the unchanged checked-in C/header/binding
hashes. `reproduction-check.json` records the temporary seed-input re-export.
Both binding manifests reproduced exactly. Kernel definitions, names, and call
order reproduced exactly. **Only global scratch declaration order differed**,
because the upstream C exporter iterates a Python set. Sorting those declaration
lines made both C sources identical. Therefore source hashes can vary with
Python hash randomization while the emitted computation is unchanged. Do not
interpret that as a weight or arithmetic change.

## Build from existing generated C

Normal runtime builds compile checked-in C and do not import tinygrad:

```sh
cargo build --offline --manifest-path runtime/Cargo.toml
cargo build --offline --manifest-path runtime/Cargo.toml --target wasm32-unknown-unknown
```

`../build_kernels.py` uses already-installed Clang and Rust LLVM tools. Its WASM
route retargets unoptimized LLVM IR before optimization; it does not install a
toolchain or require this export directory. The integration's runtime reference
and behavior checks remain the gate after any re-export.

## Opt-in own-deck graph

`export_own_deck.py` exports the separately selected graph under
`generated-own-deck/`. It preserves all 24 live-card inputs and adds two
independent role/status-bearing context tokens. The 207 inputs per deck row
contain 50 metadata coordinates and 157 factorized identity counts. Multiplying
those three count histograms by the existing embedding tables exactly produces
a copy-weighted sum of the shared 16-dimensional card embedding, without a
fixed distinct-card-list limit. The new `din.w`, `din.b`, and `drole` tensors
are stored separately in `deck-init.safetensors` (4,416 float parameters).

This artifact is deterministic untrained engineering scaffolding. It is not a
strength-tested replacement for either baseline checkpoint. The default runtime
continues to select `generated/`; enable the runtime's `own-deck` feature only
for the matched experimental variants.

With the same pinned tinygrad checkout and NumPy available:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$TINYGRAD_CHECKOUT" DEV=CPU:CLANGJIT CPU_COUNT=1 python3 export/export_own_deck.py --export --build-native
```

The script writes the separate supplemental weights only if absent, allowing a
trained **supplemental-only** checkpoint to be placed there before re-export.
The baseline model files are read-only inputs. With no `--export`, it regenerates
only the compact bounded NumPy reference and validates the supplemental file.
That reference covers all seven existing observation fixtures, both checkpoint
roles, all nine horizons, and all three variant statuses. It records context
value and prediction logits; latent and gradient parity are checked directly by
`bots/jepa/test_own_deck.py` using NumPy and PyTorch.

Run the focused correctness checks from the repository root using an existing
Python environment with NumPy and PyTorch:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bots/jepa -p test_own_deck.py -v
```

PyTorch is imported lazily and that one test skips if unavailable; a passing
training-path claim requires that test to run. The test performs one synthetic
SGD update of supplemental tensors only, checks finite nonzero gradients,
checks base-weight immutability, and round-trips both the full opt-in checkpoint
and supplemental-only deployment format. It never writes the baseline files.
The reusable `own_deck_model.run_torch` callable has no training CLI side effects.

The recorded local training check used an existing Python 3.11 environment plus
read-only cached PyTorch 2.8.0 dependencies. This exact session command installs
nothing and leaves those caches unchanged (`PYTHONDONTWRITEBYTECODE=1`):

```sh
DECK_TEST_CACHE=/Users/ericfode/.cache/uv/archive-v0
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$DECK_TEST_CACHE/rehTsShR29rpWi8Dqz5BL:$DECK_TEST_CACHE/ntYsJgeLWxSB0rhe6n9sh:$DECK_TEST_CACHE/5i8dYw1S9c5zrvrF0rCIy:$DECK_TEST_CACHE/C7W22kpzl1cAe-Hdx0N-2:$DECK_TEST_CACHE/F1isPlsf9ooQ4EGhGPl5V:$DECK_TEST_CACHE/PVyRmcnszTpMFeVdyuyJs:$DECK_TEST_CACHE/fDmWyEr9slZLLcHdlujql:$DECK_TEST_CACHE/khxszcG0X4WuYCMH_DEdE:$DECK_TEST_CACHE/7h7hIgcQT6GjZZGqqRrhM" \
/Users/ericfode/src/crown-jepa/.venv/bin/python bots/jepa/own_deck/verify_training.py
```

`own_deck/training-verification.json` records the test result, exact source and
fixture hashes, and before/after hashes proving both baseline checkpoint files
and the checked-in supplemental initialization stayed unchanged. The synthetic
updated weights exist only in a temporary directory and are removed by the test.
