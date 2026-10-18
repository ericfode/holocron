# Bounded supported-transition result

The completed pilot learned some held-out context mappings, with **no observed
advantage from correct IR** over the ID-only or fixed wrong-IR controls. All
three arms improved on simple baselines. This is a two-card engineering result,
not evidence of unseen-card, compositional-effect or strategic generalization.

Source commit: `c0b1527fce1f69c658f5db6c2d06800c8e9fb88b`.
Run: `supported-transition-s17-20261018-v2`. Full paths and SHA256 values for
source, data, checkpoints, contracts, golden fixtures and accounting evidence
are in [supported-transition-summary.json](supported-transition-summary.json).
The report reads saved outputs only; it performs no additional model queries.

| Arm/baseline | Final validation MAE | Actual updates |
| --- | ---: | ---: |
| Correct typed IR | 0.226566 | 200 |
| ID-only | **0.205742** | 200 |
| Fixed wrong IR | 0.209615 | 200 |
| Training-label prior | 0.349206 | 0 |
| Naive zero/copy-current | 0.611111 | 0 |

MAE averages **18 known label coordinates**, not 18 independent scenarios. The
six validation contexts contain only two known resource/damage/exhaust/terminal
labels each, three target-admissibility labels and one follow-up label. Known
damage/exhaust/follow-up targets are constant 1/1/0. Their accuracy alone is
uninformative; the training-prior baseline already predicts them perfectly.

| Varying target | Validation support | Correct IR | ID-only | Wrong IR |
| --- | ---: | ---: | ---: | ---: |
| Source use, balanced accuracy | 6 | 0.8333 | 0.8333 | 0.8333 |
| Chosen target allowed, balanced accuracy | 3 | 0.5000 | 0.5000 | 0.5000 |
| Resource payment, MAE | 2 | 0.2464 | 0.1715 | 0.2066 |
| Terminal, balanced accuracy | 2 | 0.5000 | 1.0000 | 1.0000 |

The terminal result is based on one positive and one negative per partition;
it cannot support a broad terminal-prediction claim. Target balanced accuracy
shows no improvement over chance on the three known labels. One seed and this
small holdout do not establish a meaningful ranking between the learned arms.

The native collector executed 32 `Engine::apply` calls across 16 public synthetic
contexts using complete, already admitted ASH_011 and IBH_053 cards at pinned
Kessel `c7ee39554901278cee70f61fd8b26fb1920696b3`. Ten rows from context
families 0–4 trained; six from families 5–7 validated. Both card identities appear
in both partitions. Full context families and exact numerical contexts are
disjoint. There are 41 known training coordinates, 18 known validation
coordinates and 53 masked unknown coordinates. Labels come from actual offered
actions and observed snapshots, including terminal-aware committed-state
captures. Neither the typed encoder nor the restricted synthetic oracle
generates labels. Offered masks and later states are excluded from inputs.

Each standalone arm has 6,759 allocated parameters, seed 17, identical initial
weights and batch schedule, AdamW learning rate 0.003 / weight decay 0.0001, batch 8
and 200 updates. The shared path GRU and nonlinear joint path/value map preserve
ordered operand/effect roles before token pooling. Capability counts aggregate
by a canonical weighted sum. The supplied bag has one source-program copy; it
does not train actual deck-composition or remaining-deck semantics. Structural
order/count/condition/target checks establish representational sensitivity,
not learned multieffect meaning from these two single-damage abilities.

The ID-only arm supplies one opaque identity token per program and can memorize
both identities. The fixed wrong-IR swap is an invertible code shared across
training and validation, so its head can learn a remapping. These controls are
matched engineering comparisons, not decisive semantic falsifications. The
allocated graphs and padded shapes match; effective gradient paths differ
(ID-only has zero-length paths and no effective path-GRU gradient).

There were exactly six held-out model evaluations: initial and final for each
arm. Three additional label-free reference forwards saved finite known,
unknown, neutral, unsupported and ambiguous ABI fixtures. The numerical
contract is `jepa-typed-transition-numeric/1`: eight program slots, 64 semantic
and 32 role slots, 16 path components, width 16, seven output columns, explicit
masks/statuses, ordered vocabularies with PAD/UNKNOWN, units/scales, named
weights and reference forward. The earlier inspection cap of 512 semantic
tokens is separate. Every arm pins its final checkpoint, contract and golden
input/output hashes. No production graph, actor, WASM adapter or evaluator was
changed; existing production own-deck inputs remain [2,207] and the dynamic
remaining deck remains unknown.

| Artifact | Correct IR | ID-only | Wrong IR |
| --- | --- | --- | --- |
| Checkpoint SHA256 prefix | `545ef9b878aa` | `76c15c482531` | `6fd641eee6df` |
| Contract SHA256 prefix | `b18b8a3029f4` | `3f9a7accec4d` | `eee2b77584cd` |
| Golden SHA256 prefix | `7aa31decc0da` | `8fee217e44c4` | `9807cb7b1e93` |

The dataset SHA256 is
`fd40fe92108bf89c25299dda1a975a550209283908a54f9c745e0514e9e79865`;
its manifest SHA256 is
`821a96109d6dadc44dcda510c1293a5e8eab41ba55709f5516849ecf3280893e`.
The unchanged model source SHA256 is
`0b0826951cd880e8920e496c54c9a27c7a69032e726ec52f5354cead3e56bece`.

Shared accounting retains every failed attempt. A first collector compile
failed with zero applies. The first fit command used a relative entrypoint
under the collector working directory; CPython exited 2 before opening the
trainer. No output directory, progress file or matching feed event existed.
The failed record's 600-update reservation remains intact; an independently
reviewed, append-only `missing-main-update-credit` records 600 unused updates
returned in the **same ledger**, with zero actual updates verified. Its 0.056929 s
time debit remains. The subsequent absolute-path run uses a fresh run ID and
records every actual update 1–600 durably. There was no quota/time reset or
optimizer replay.

Cumulative active build/collection/startup/fit time across all attempts was
**5.774309 seconds** against the shared 120-second ceiling. Actual usage was
32/96 engine applies and 600/600 updates; prior completed updates were 700.
Final receipt snapshots sum to 5.774725 seconds, 0.000415 seconds later than
the durable ledger debits. Both totals include all failed attempts.
The maximum conservative sampled RSS bound across all attempts was
525,893,632 bytes; the successful fit bound was 399,212,544 bytes, against
2 GiB. The fit's inner known-process bound was 343.969 MiB. These are sampled stop guards,
not instantaneous OS memory reservations. Paid jobs/spend: **0 / $0**.

Saved outputs are under
`/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/supported-transition/`:
`fit-2/result.json`, `fit-guard-2/supervisor-receipt.json`,
`campaign-ledger.jsonl`, the earlier failure receipts, and the native/data
artifacts. The numerical handoff supports later independent integration work;
this pilot makes no playing-strength, full-world-model, persistent/granted
ability or seven-loss-reproduction claim. No more training, validation,
deployment or paid compute was performed to prepare this report.
