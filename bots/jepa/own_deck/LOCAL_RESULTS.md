# Measured local original-deck readout results

All three arms completed 100 updates at
`eb5c6d953ee45de56947ec6877880264885447eb`: **300 updates total**, seed 17,
batch 16, one CPU worker. The shared dataset has 22 training and five validation
decks, with seven/four disjoint source families. The base tensors and all three
protected checkpoint files stayed unchanged. The new supplement and auxiliary
head were saved separately for each arm and were not exported or activated.

| Final validation metric | Neutral | Correct original | Wrong own deck | Training-mean prior |
| --- | ---: | ---: | ---: | ---: |
| Mean normalized squared error | 0.01718 | **0.00827** | 0.01691 | 0.01502 |
| Curve-coordinate MAE | 0.09950 | **0.06082** | 0.09809 | 0.09156 |
| Initial unit-fraction MAE | 0.15185 | **0.10749** | 0.15898 | 0.16079 |
| Main-deck count MAE, copies | 3.285 | 4.124 | **1.890** | 3.727 |

Correct composition improves the overall readout on this tiny grouped holdout,
but does not improve every target: its count error is worse than both trained
controls. The wrong input is a partition-local different-family permutation;
17/27 assignments differ in total count, so this pilot does not fulfill the
stricter count-matched future decision experiment. Card identities may overlap
between partitions. These are declaration statistics directly available in the
input, not synergy, hidden-draw prediction, action consequences or playing
strength. No rollout, opponent or tournament outcome label was used. The
initial-unit label is the declared unordered unit fraction, not a live draw
forecast.

There were 63 validation forwards at the fixed five-update reporting cadence;
the final step was selected in advance. No extra fit, retry, early checkpoint
selection or deployment followed the results. Total owned-worker wall time was
8.23 seconds, including imports/startup/shutdown. Modal batch spend is **$0**.
There is no useful GPU scaling claim from a fit this small or from these labels.

## Memory-accounting correction

The first result transported a `TorchVersion` string subclass, which caused
Torch to import while the parent deserialized it. Its final recorded parent
peak was omitted from the first summed tree bound. The corrected conservative
bound is **501.05 MiB**, versus the raw 339.31 MiB. The other arms remain
499.66/500.06 MiB; all are below the sampled 2,048 MiB stop threshold.

The correction is append-only in the dashboard feed. Raw results and checkpoint
bytes were preserved. Commit `15410edd42b0f2eaacfe41da3daa399c1e6a9a54`
transports primitive runtime metadata and merges terminal parent peaks; 12
runner regression tests pass. This corrects reporting, not model outputs, and
consumes zero additional optimizer updates. These are conservative independently
observed peak sums, not simultaneous RSS traces or instantaneous OS limits.

## Inspectable evidence

- [Compact summary and raw artifact hashes](local-fit-summary.json)
- [Immutable raw results and per-arm manifests](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/runs)
- [Memory correction receipt](local-runner-memory-correction.json)
- [Append-only dashboard feed](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/run-events.jsonl)
- [Data manifest and source/license pins](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/data/real-decks.manifest.json)
- [Experiment contract](LIVE_EXPERIMENTS.md) and [cloud budget](MODAL_BUDGET.md)

The separate remove/restore coherence probe is not part of these 300 updates.
It must retain the source-family holdout and distinguish equal-size alternative
controls from incomplete-original diagnostics and valid depleted game states.
