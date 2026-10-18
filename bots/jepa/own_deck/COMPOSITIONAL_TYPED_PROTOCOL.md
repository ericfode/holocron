# Elementary typed-binding comparison

This is a falsification test before deck composition. The preceding negative
transfer, wrong-ability gain and failed fixed-weight eligibility correction remain
unchanged. No playing-strength, actual-card coverage or production claim follows
from this assay.

Freeze one architecture per family and one objective, with no capacity, learning
rate, epoch or seed sweep. Compare the existing 16-coordinate typed-path pooling
and late-fusion graph against a small compositional graph that binds selector
owner, target arena and cost cap to the corresponding public candidate fields.
The latter binds effect operator and amount to damage/HP and intended-target
equality. Eligibility excludes intended equality, effect operator and amount.
The old comparator also excludes intended equality from eligibility. The new
graph's explicit endpoint gating is part of its architectural hypothesis; this
does not isolate pooling from all other architectural changes.

Both families train from scratch, using identical native observations, TRAIN
rows, loss coefficients, optimizer, updates and seed pairing. This tests the
existing architecture on the elementary objective, not the old checkpoint on
an incompatible vocabulary. Each family has matched identity-on and identity-off
arms with identical allocated tensors and initialization. TRAIN identities have
separate optional embeddings; every held identity is UNK. The no-ID arms gate
this channel to zero. Source printed metadata is identical across programs,
display text and identity are absent from semantic inputs, and candidate card
identity is never a semantic feature. Rename invariance is checked on actual
consumed semantic fields.
Identity removal is a matched training-arm ablation; with every held identity
UNK0, it is not deletion of a known held identity from a single fitted checkpoint.

Programs form the full 2^5 factorial: owner any/opponent, arena ground/space,
cost cap 2/3, amount 1/3, and damage/heal. The parity of the five bit indices
assigns 16 complete programs to TRAIN and 16 to HELD. Every atomic value and
every proper subset combination occurs in both partitions; all four roots of
a program stay together. HELD labels cannot select epochs or modify weights.
These are deliberately synthetic complete event definitions admitted by the
unchanged pinned Kessel runtime, not variants represented as real cards.

Each of 128 roots has sixteen visible plain units: owner × arena × cost 2/3/4,
plus a second cost-2 unit for each owner/arena pair. Synthetic anchors have fixed
HP 10 and power 0. Two distinct eligible targets, a healthy eligible target
with another damaged eligible unit, and an invalid opposite-arena intention
are planned per program. The healthy target does not suppress heal offeredness.
Only actual native menus supply eligibility; only observed settled actions
supply endpoint deltas. Invalid future outcomes stay unknown unless observed.
No replacement targets, private piles, hidden draw order, opponents or games
are admitted. Validate every fixture round trip and every program's admission
before the first apply. Native calls have durable paired before/after records.

The deterministic typed reference computes owner/arena/cap matching and signed
damage or clipped healing directly from the BEFORE fields. It supplies neither
training labels nor learned inputs. Require complete exact agreement on all
native-known coordinates before neural fitting; preserve mismatches as failure.

Use seeds 17/29/43, 300 full-TRAIN updates per arm, AdamW learning rate .003,
weight decay .0001 and gradient norm clip 1. The common objective is half
TRAIN-class-balanced eligibility BCE over all candidates and half SmoothL1 on
the native committed intended candidate's raw damage delta. Root/stratum
weights are frozen from TRAIN only; zero, sign, operator and amount support
are reported. Fixed physical feature scales do not use held statistics.
Save initial/final predictions and all checkpoints, inputs, masks and weights.

Primary learning success requires, in every seed and the identity-off arm:

- Eligibility balanced accuracy at least .95 in every held owner, arena, cap,
  amount and operator slice.
- Intended damage MAE at most .25 and three-way sign accuracy at least .95 in
  every held operator/amount slice. Healthy-zero recall must reach .95 in both
  heal/amount slices; the damage slices have no native zero endpoints and their
  zero recall is explicitly not applicable. Missing expected support fails.
- No-ID balanced accuracy drop at most .02 and damage MAE increase at most .05
  relative to the corresponding new ID-on arm in every slice, plus exact
  semantic rename invariance. Old-model identity gaps remain descriptive.

Reference agreement is an admission condition, not learned success. A strict
new-architecture advantage requires at least 10% lower pooled held composite
error `((1 - balanced_accuracy) + damage_MAE / 3) / 2` than the old no-ID graph
in each seed, without worse eligibility accuracy or damage MAE (1e-6 tolerance).
A zero old denominator gives no relative claim. If both pass the absolute gates,
prefer the simpler adequate design and do not claim a strict win against zero.
If neither passes, stop deck composition: this elementary objective and model
combination has failed. A shared objective prevents attributing a relative
architecture difference to different losses; absolute failure alone cannot
separate architecture from objective without another authorized test.
Predicted damage in [-.25,.25] has zero sign; native sign uses exact zero.

Allocation: one compute worker, sampled RSS at most 1 GiB, zero paid jobs/spend,
at most 512 new native applications, exactly 3,624 neural forwards (3,600 train
and 24 initial/final evaluation), 3,600 backward/optimizer calls, and exactly two
TRAIN preprocessing fits (typed numeric scale and shared loss-weight statistics).
The deterministic reference has zero fits. Stage ceilings are metadata
5 s, build 15 s, native 30 s, data preparation 5 s, fitting 120 s and saved-only
verification 10 s (185 s total). Source/input pins and full reservations precede
execution. No failed stage is retried or credited back. Final measured charges
link to the preceding 295 applications / 222.92651104100514 seconds; historical
aggregate observed calls remain unknown. The cumulative $100 ceiling and saved
$25 reserve persist. No new paid work is allocated; this is not a billing claim.
