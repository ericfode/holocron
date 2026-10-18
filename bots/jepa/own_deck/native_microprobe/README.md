Prepared source only; compilation and execution require the coordinating root's GO.

This isolated project references the clean Kessel source commit
`c7ee39554901278cee70f61fd8b26fb1920696b3` and retains complete actual card
definitions. It exercises ASH_011 `abilities.leader[0]` (exhaust; damage 1;
unit remaining-HP >= 2) and IBH_053 `abilities.leader[0]` (resource 1 and
exhaust; damage 1 to either base) in synthetic public microstates. Setup uses
ASH_019 bases and LOF_256 vanilla 1/4 units. No hidden cards are constructed.
The selected catalogue also retains the exact unmodified canonical TOKEN_SHIELD
row required by the loader. Its compiler status remains `unsupported`; Kessel's
native-token admission contract owns its execution. No token is created in the
two fixtures. TOKEN_EXPERIENCE is not required by these abilities or the loader.

IBH_001 was requested as the heal example, but the pinned runtime rejects its
whole card because the unit side has an unsupported `numCardsFunc` selector
(`compiler/generated/runtime-admission.json:7137`). SHD_002 is also rejected
because its unit side has `systemPropertiesFactory` (`:10002`). Stripping those
sides would change actual-card admission, so neither runs here.

The source predeclares assertions for both costs, target domains, precommit
cancellation, the exact damage delta, priority and subsequent inability to reuse.
It allows a maximum of 12 `Engine::apply` calls and performs exactly 8: source
click, cancellation branch, target click, and offered opponent pass for each
fixture. Boundary checks query legal sets without applying actions. There is
no game loop or rules search. Runtime has an internal 120-second guard; the
caller must also supervise wall time externally. Compilation has not been timed
and must be budgeted separately, with one Cargo worker and an isolated target.

The saved research probe lockfile is copied byte for byte. Its package name and
three dependencies match this package, so no lock generation was performed.
`--locked --offline` must fail if that existing resolution is not compatible.

After GO, build (do not run automatically on build success):

```sh
CARGO_BUILD_JOBS=1 CARGO_TARGET_DIR=/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target cargo build --offline --locked --manifest-path /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/Cargo.toml --bin typed-ir-microprobe -j 1
```

After separate runtime GO, invoke the built binary with new receipt and partial
trace filenames (the supervising parent sets the attempt-specific paths):

```sh
TYPED_IR_TRACE=/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/attempt-3/native-transitions.jsonl /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target/debug/typed-ir-microprobe /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/attempt-3/native-receipt.json
```

Each receipt contains all exact offered `Action` tuples and the selected
source/program binding, before/target-prompt/cancelled/after/following snapshots,
source hashes and the predeclared assertion list. These are Kessel execution
witnesses for actual card abilities in synthetic states, not new forceteki
oracles or a whole-card general correctness claim. No old workspace is changed.
Budget.apply appends and flushes public before/offered-action/after-or-error rows
so an assertion failure preserves every preceding transition and attempted call.
The original second-attempt source, manifest, guard and raw logs remain in
`attempt-2-evidence/`; they are never rewritten for the corrected third attempt.
