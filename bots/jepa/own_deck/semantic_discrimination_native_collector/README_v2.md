# Versioned native guard for the metadata repair allocation

`supervise_v2.py` is a new copy of the reviewed native guard. It routes explicitly
to `semantic_discrimination_repair_accounting.py` and the new canonical
`experiments/semantic-discrimination-repair-v1/campaign-spec.json`. The original
`supervise.py` remains byte-identical at SHA-256 `36e32622ff8ff715e8a9aa7ab79d221b0ee0c0ab096c1c7447726810cdcaff88`.

The Rust source remains byte-identical at SHA-256
`f5a54313c9d33fa2f2e1755d63d60cf2a22bf53d71b752c9f174b2f551df948e`.
The Cargo manifest, lockfile, scientific world builder and 33-root action protocol
are unchanged. The original metadata attempt failed before plan preparation;
its separate ledger retains the full three-second charge. This route neither
credits nor reopens that allocation.

The metadata worker from `semantic_discrimination_fit_v2.py` calls the same
`write_source_manifest(plan_path, out_path, campaign_root, source_freeze_commit)`
API. The writer records the actual versioned guard, tests, fit worker, verifier,
accounting adapter and inherited accounting core as separate pins. It never
changes module globals, `__file__`, or another module's accounting object. Its
outputs are the declared new root's `native-plan.json` and
`metadata-1/native-source-manifest.json`; the original study's paths are retained.

The new allocation retains the same once-only 10-second build and 45-second
native stages, 128-call global cap and per-root maximum of four. Fixture sanity
and snapshot/load validation stay inside the native stage before any apply.
There is no new collector binary name: the already unique
`semantic-discrimination-native-collector` was never built by the failed metadata
attempt. Both older protected collector and validator binaries are still checked
before and after each guarded stage.

Default invocation is read-only preflight after metadata outputs exist. Actual
metadata, build, native and learning remain coordinator-only after the complete
versioned sources, new allocation, exact descriptors and configuration are frozen.
No stage has been executed by the source author.
