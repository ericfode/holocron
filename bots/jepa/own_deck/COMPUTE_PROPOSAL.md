# Proposed bounded own-deck experiment

This larger action/decision comparison remains unlaunched. The subsequently
authorized 3×100-step local declaration-readout pilot is a different, smaller
experiment, documented in [LIVE_EXPERIMENTS.md](LIVE_EXPERIMENTS.md). Its
composition targets do not fulfill the consequence-supervision gates below.

**Proposal only. No real-data fit, data collection, game run or opponent
execution is allocated or launched by this implementation.** The present
remaining-card row is unknown. The next proposed controls are neutral, correct
original, and wrong own deck using the existing original-row contract. Wrong
deck assignment is a future manifest-controlled recipe, not a new CLI variant.
This document fixes a reviewable ceiling for a later
stage; any launch needs a new exact input manifest and a suitable verified
supervisor before consuming its budget.

## Admission and common inputs

Pin a prospective game/deck-cluster split using canonical composition
fingerprints, common candidate/return banks,
metadata/card hashes, code and numerical-runtime hashes, model initialization,
sampler order, loss coefficients, checkpoint selection and seed list before
labels or results are inspected. No previously consumed holdout is reused as
new validation or test data. The seven seen rated losses are diagnostic only.
No additional collection is implied by the fit ceiling below.

Targets must contain deck-sensitive consequences. Frozen deck-blind judge
scores and target latents alone are insufficient. Training only on a
chosen-action return supplies no counterfactual pairwise gap. Every arm uses
the same common objective and label bank; detached deck probes stay diagnostic.
Prediction loss alone is insufficient: a fixed bounded smoke should report
collapse/variance diagnostics and action-conditioned one-/multi-step
sensitivity, while the proposed held-out comparison measures decision quality
under equal realized budgets. Cost/effect/target/count interventions need
rule-grounded fixtures. Uncertain draws require conditional distribution or
outcome evaluation, with proper scoring/calibration where distributions are
predicted; never assume the current actor knows the actual next card.

The arms share the same expanded model and parameter shapes. The initial
comparison is no-context neutral, correct original+metadata, and wrong own deck,
with three paired seeds per arm. Freeze the wrong-deck assignment within each
partition, requiring a different fingerprint and matched status/coverage and
total-count conditions. Keep the actual state, action and target banks identical.
Prefer same-leader/base swaps; mark contradictions with observed own cards as
corrupted-input probes rather than legal counterfactual states.
Original+remaining+the same metadata is a fourth arm, admitted only after an observation-only
ledger supports that feature, passes its branch/reset/unknown contracts, and
future target context is wired. Remaining composition/belief is dynamic world
state: its draw/search/discard/return/create/transfer transitions must conserve
observed instances alongside hand, board and other zones, with explicit
unknown/uncertainty status. Declare a belief-summary or stochastic/distribution-aware
conditional future objective before treating uncertain draws as training
targets. Stage 1 does not fulfill this dynamic requirement.
Original remains the original header multiset;
it is never recomputed from a future private simulator state. The new forwards
can accept future context, but no deck-aware EMA objective or target-training
CLI is wired by this increment.
Curve-only or metadata-removal comparisons require a separate proposal.

## Fit ceiling

| Item | Proposed limit |
| --- | --- |
| Models | 3 arms × 3 paired seeds = 9; at most 12 if the ledger/target gates admit the fourth arm |
| Optimizer | AdamW; fixed shared optimizer/schedule and objective, pinned before launch |
| Batch | 64 rows, with the common candidate/window grouping preserved |
| Updates | At most 500 per model: 4,500 across the proposed three controls; 6,000 only if the fourth depletion arm is admitted |
| Worker | One CPU worker; no concurrent model fits |
| Time | 10 minutes per model and 30 minutes total fit wall time, cumulative across attempts/retries |
| Memory | 2 GiB process-tree RSS ceiling; this is not a WASM linear-memory allowance |
| Validation | At most 64 complete validation forwards total, including selection, failed attempts and retries |

Use a fixed candidate checkpoint schedule at steps 0/250/500, common validation
objective and earliest-checkpoint tie-breaking. This consumes at most 27
scheduled validation forwards for three arms or 36 for four; any other validation
activity still counts against 64. Record every actual update and validation
forward in a durable journal. A retry resumes the remaining allocation; it does
not reset the clock, update or forward budget.

A receipt-preserving guard must report the entire process tree, wall/RSS
measurements, initiating stop reason, exit/reaping status and journal/checkpoint
hashes. Test its deadline, RSS, denied-signal and supervisor-failure handling
with harmless children before a fit. The recovered research had an outer
supervisor `PermissionError`; its worker-completion audit does not certify that
old guard. If reliable process-tree RSS enforcement is unavailable, stop and
revise the tooling/allocation instead of claiming this 2 GiB limit was enforced.

Every applicable ceiling is a stop condition. Per-model maxima are not a
promise that all models can complete inside the smaller cumulative cap. Do not
add updates, seeds, retries or validation queries after a favorable result.
Report partial coverage and all spent budget before proposing a larger run.

## Separate paired-game proposal

After fit/export/runtime admission, propose at most 16 games per arm: two held-out
supported deck pairs × four seeds × both candidate seats. The proposed three-arm
comparison is 48 games; an admitted fourth arm would make 64. Use one worker,
the same in-repository trusted native opponent, identical per-game start and
candidate schedules, and a 45,000 ms aggregate thinking bank per bot/game.
Keep c-clock resourcing fixed. Pin routing/candidate sets, or explicitly
measure the search-effort changes caused by learned gating.

The entire paired-game stage has a separate 30-minute cumulative wall cap,
including failures and retries. Pin a per-game native-transition cap in its
launch manifest before execution. Interleave arms within each seed/deck/seat
pair so that a total-budget stop leaves a useful paired prefix. Keep every
incomplete/unsupported/error/timeout result; the cap does not promise completion
of all scheduled games. Analyze complete paired seed/deck clusters with both
seats together and report the small-sample uncertainty.

This proposal permits no downloaded opponent execution. A later comparison
against submitted opponents needs its separately authorized Linux environment,
exact opponent bytes/context, supported capabilities and another bounded
manifest. No production helper, deployment or submission is part of this plan.
