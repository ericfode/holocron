# Import-scoping repair and fresh allocation

The first allocation's metadata stage failed before `prepare_plan()` because
`import importlib.util` inside `metadata_worker` made the earlier `importlib`
reference local and unbound. Source freeze was
`b94dd4cfb9b63a3199805526398b925d3fdedc65`. Its failed stage remains failed:
three seconds charged, zero native/neural/update/numerical-fit calls, no prepared
corpus or output artifacts, and no pending worker. The empty attempt directory,
receipt, specification, source bytes and append-only journal remain unchanged.

The failed journal is SHA256
`8657e782e0523b8a694ea50b95c61ed3a0f4d9bf9e4ac24f1414cc50ed98a864`,
72,201 bytes, final chain
`5edada95312903f7fadd809e311d42cf5cc1eeb080adc6d94e262cbbb0381f88`.
It observed 0.21101508394349366 seconds; that does not credit its three-second
failed reservation. The previous scientific conclusions are unchanged.

This version fixes the local import through `from importlib import util` and
uses new learner, verifier and supervisor entrypoints. A small explicit
accounting subclass reuses the unchanged budget/state implementation and
validates the new pinned parent carry. Both the base accounting source and
adapter are pinned; no global paths, module identities or old journals are
patched. A synthetic metadata-worker flow test covers the missed import path.

The new canonical root is task-7/experiments/semantic-discrimination-repair-v1.
Carry forward **208 charged native applications and 191.08889674965758 charged
seconds**, with historical observed applications still unknown. A fresh
allocation permits metadata3/build10/native45/prep5/fit45/baselines5/verify5
seconds: 118 seconds total, 128 native attempts, 3,000 optimizer updates,
3,045 forwards and 16 fixed ridge head-fit attempts. The new cumulative
ceilings are **336 applications and 309.0888967496576 seconds**. Unstarted
stages in the failed campaign were never charged or executed; no allowance is
credited or reused through its closed ledger. Every new failed stage retains
its full reservation; no automatic retry is allowed.

The [original scientific protocol](SEMANTIC_DISCRIMINATION_PROTOCOL.md) is
unchanged: eight actual-corpus programs, 33 roots, the same split, input tensors,
five arms, initializations, seeds, steps, native labels, masks, donor map,
baselines, primary contrasts and diagnostic thresholds. No labels were seen
before this repair. New source routing is frozen before preparation or native
execution. No added epochs, samples, seeds, cohort substitution or tuning.

The financial ceiling and reserve remain $100 and $25; no paid compute job is
allocated. Original workspaces, old source bytes, protected evidence and the
global dashboard pointer remain unchanged. No opponent games, engine/card
changes, production deployment or semantic-validation claim follow.
