# Actual-corpus semantic-discrimination native collector

This new executable copies the reviewed public-only collector machinery from
`binding_transfer_native_collector/src/main.rs` at SHA-256
`6355cde9d6ec5bfb51feab133b3d7fbf352b2edb392bba74187d91c7ff00d61c`.
It leaves that source, the historical journals and both protected binaries intact.
The new binary is `semantic-discrimination-native-collector`.

The frozen plan declares 33 independent authored fixtures: 32 main roots from
eight complete actual-corpus cards plus one LAW133 training support root. Each
starts with an own known source in hand, empty draw piles and opponent hand and
resources, public arena objects, and public bases. Metadata may include the exact
native Shield definition for constructor support; there are no physical Shields.
No card, engine, compiler or runtime coverage is changed.

Inside the 45-second native stage, every fixture is constructed and checked by
snapshot/load and legal-action equality **before the first apply**. These checks
apply no actions. They share the native stage's active-wall and memory budget;
there is no separately authorized fixture run. The collection then starts each
root from its unchanged fixture. All Engine::apply calls pass one budget entry:
fsynced beforeApply intent, native offered-action check, a global 128-call cap,
per-root plan cap no greater than four, and afterApply/applyError evidence.

A valid intended target is selected exactly once. The reviewed `upTo` programs
then require the native selection to contain that one intended physical card,
the same source program and PC, and the actual offered Done action. No second
card is selected. An unoffered intent uses an actual Cancel if available. Some
mandatory triggered prompts have no Cancel: those roots stop at the actual
prompt as `unoffered-observation-only`, with known false membership and **all
future labels unknown**. This is an explicit observation terminal, not a settled
action or engine error. Committed and cancelled action roots must settle fully.
A second target prompt, unknown continuation, native error, or quota exhaustion
stops the collection and blocks admission; no target or fixture is substituted.

Both the intended and other predeclared endpoints are observed. After departure,
identity/zone proof is retained and physical numeric known flags are false.
Removal-aware conversion owns the corresponding masks; this collector creates
no IR-derived labels or fabricated unselected outcomes. Runtime counters and
post-action parent links are proof fields, not learned before-input features.

`supervise.py` is a new guard with explicit `--spec` and `--manifest` inputs. It
uses the shared config-bound accounting Campaign, a nonblocking serial lease,
durable child intent/start/end, and once-only build/native descriptors. Build is
10 seconds and native is 45 seconds, including preflight and cleanup. The guard
samples concurrent owned-process RSS plus its own RSS at 50 ms, with a 1 GiB stop;
it supplements samples with parent plus maximum single-child rusage. This is a
sampled threshold, not an OS memory reservation. Cargo is offline and locked,
with one Cargo/jobserver worker, debug 0, incremental false, and no codegen or
rustflags override. This does not claim OS single-core affinity.

The metadata worker calls `write_source_manifest` only within its three-second
stage. It writes an exclusive external `metadata-1/native-source-manifest.json`,
pinning the generated `native-plan.json`, reviewed source, exact original engine
files, compiler catalogue, and protected binaries. Build and native must consume
those completed metadata proof pins. Source freeze therefore precedes all
metadata, build and native execution. No generated manifest is written into the
tracked collector directory.

Portable stdlib tests use synthetic JSON and mocks; they do not build or launch
an engine, construct real snapshots, load arrays, train, or spend money. Every
actual build and collection remains coordinator-only after source/configuration
freeze and explicit GO.
