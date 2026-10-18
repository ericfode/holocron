# Saved-pilot diagnostic

The saved correct-IR checkpoint has a connected semantic path and responds to
program swaps. Its literal-quantity sensitivity is extremely small. This is
consistent with a pilot that learned some program/identity distinctions from
two familiar cards while never seeing a varying damage amount; it does not
establish learned rule meaning or prove that the semantic path is dead.

This posthoc diagnostic used9 batches:9 forwards and3 backwards, **zero
optimizer updates and native calls**. The guarded worker completed in1.3805s
with a268.69MiB conservative sampled RSS bound (limits20s/2GiB, CPU1). Saved
checkpoint bytes and loaded parameter values are unchanged. No thresholds,
hyperparameters or checkpoint were selected using these measurements. Exact
counter, gradient, source snapshot and checkpoint hashes are in
[PRIOR_PILOT_DIAGNOSTIC.json](PRIOR_PILOT_DIAGNOSTIC.json); the executed source
was preserved before adding the next model implementation.

| Saved-model measurement | Observed value |
| --- | ---: |
| Program/query activation RMS | 0.66978 |
| Projected context activation RMS (all16 rows) | 0.47307 |
| Synthetic one-copy bag activation RMS | 0.011163 |
| Maximum error from `bag = query / 60` | 9.31e-10 |
| Full-objective path-GRU gradient RMS, before clipping | 1.03e-4 |
| Full-objective context-projection gradient RMS | 7.03e-3 |
| Path-GRU gradient coordinates nonzero | 100% |

Gradient RMS and L2 norm depend on parameterization, dimension and loss scale;
their relative sizes alone do not diagnose semantic quality. The JSON reports
per-module RMS/L2/nonzero coverage, separate source-use and damage-head
gradients, gradients at queried/bag/context fusion coordinates, and input
gradients converted back to physical HP/damage units. These are instantaneous
post-training gradients, not a reconstruction of optimization history.

| Matched saved-model intervention | Overall logit delta RMS |
| --- | ---: |
| Zero queried-program and bag vectors at fusion | 1.96327 |
| Swap the two known programs, same public context | 0.80345 |
| Flip public source-exhausted input | 2.13402 |
| Change unit remaining HP1↔2 with consistent HP/damage | 0.03205 |
| Change known damage literal1→2 in both programs | **0.000154** |

For the quantity intervention, the damage head's logit/output delta RMS is
4.42e-5. These are label-free feature interventions; no native mutant
transition was collected or scored against copied factual labels. They measure
local sensitivity, not correctness or unseen-program generalization. The
exhaustion flip is a unit boolean change; the HP intervention changes only unit
rows, so the overall RMS values are not equal-sized causal comparisons.

The earlier negative result has several concrete limits. Eighteen known
validation coordinates came from six contexts and two identities shared with
training. ID-only could memorize both, and a persistent wrong-IR swap was an
invertible code. Damage/exhaust/follow-up were constant1/1/0. The old loss
averaged available coordinates, weighting its heads by support10/7/5/5/5/4/5;
constant heads contributed14/41 known training coordinates. Naively giving all
seven heads equal weight would increase the constant-head share to3/7.

The old token sum divided by64 irrespective of active length and then added an
unscaled known-status projection. That creates a scaling confound, although
this diagnostic did not separately ablate status and cannot claim that status
dominated. The bag was exactly a redundant query/60, not deck information.
HP/30 made a one-HP boundary only1/30 at the context input. The ID-only root
token has zero-length paths, giving no effective path-GRU gradient despite
equal allocated parameters; AdamW weight drift alone would not prove path use.

The proposed action contrast removes the redundant bag, uses active-token
means and normalized program/context representations, and preserves depth/key
assignment through an explicit interaction before the nonlinear path/value
map. Native HP/resources/counts use physical units followed by train-only
scales. Per-head availability, class support and variation remain explicit;
constant heads are auxiliary, not evidence of semantics. The new model is a
small typed structural learner, with no text encoder or rules-engine changes.

The frozen prospective split crosses10 training and2 held-out program
identities with10 training and4 held-out state families, retaining all branch
descendants together. Separate cells measure new programs, new contexts and
their intersection. Correct IR, ID-only (one held-out UNK), per-example
train-partition wrong IR and context-only use matched capacity/schedule.
Known primitive combinations and exact program/reprint groups are audited
separately. Native collection and any new optimizer fit still require root GO;
this diagnostic does not authorize or report that next fit.
