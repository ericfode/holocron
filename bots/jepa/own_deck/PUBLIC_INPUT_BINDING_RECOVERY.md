# Explicit recovery allocation

The first collection failed at simulator initialization because the reduced
catalogue lacked the mandatory native Shield definition. Its ledger and source
commit `30e49a50d9495b17a428a2793046381d1ab02d81` remain immutable. The failed
collection retains its full 80-application and 60-second reservation charge;
the recorded observed count remains unknown.

The separate startup-failure audit pins the error, executable and sources. The
unique error is returned from Engine construction before the collector creates
its journal, fixtures or application budget. This establishes zero applications
by control-flow evidence, rather than by an application journal. It gives no
ledger credit. No native labels or post-action states were exposed.

One distinct recovery allocation adds only the exact existing `TOKEN_SHIELD`
definition needed by the native constructor. Preserve its reviewed native-token
status; do not relabel it as an ordinarily admitted source card. Instantiate
zero Shield tokens. Every earlier source/helper row, all 16 worlds, intents,
observation anchors, hypotheses and expected pairs stay identical. The frozen
predictor `f40a77bd9fb0e08f692624fe4841d4a4352bd87436d84a1ac51725ef5a5afde5`
and verifier `6d0f1bef8ffa8ee250b1a6b3ced4ce1ddd4f5b47ed58b7e44c72f3367c0123d4`
stay unchanged. This corrects experiment setup without changing the scientific
contrasts or adding card coverage.

Use a separate ledger, configuration, native guard and uniquely named executable
so the failed run's executable remains available at its original hash. Link the
failed ledger's file hash and final chain, its frozen configuration and failure
audit, and the older research ledgers. A pending attempt blocks further work.

The new once-only allocation is 30 seconds for build and 60 for collection,
with at most 80 applications. Across v1 and this recovery, the ceilings are 160
charged native applications and 180 native seconds. The analysis allocation is
one shared 30 seconds (two 15-second stages); none was used in v1. The combined
ceiling is 210 charged seconds. Keep the older two-cycle exposure subtotal
separate and linked; these ceilings do not erase its counts or time. Dollar
limits stay at $100 with $25 reserved and $0 Modal spending.

One engine/analysis worker, one Cargo job, numerical thread limits of one and
the sampled 1 GiB RSS threshold retain their disclosed limitations. No OS CPU
affinity or process-tree memory reservation is asserted. No neural forwards,
updates, fits, paid jobs, opponent games or deployment are added. If this
recovery fails, preserve its failure and stop; do not broaden the catalogue or
silently allocate another attempt.
