# Fixed saved-evidence diagnosis

Preserve PR45 and all failed seeds. Before selecting a correction, use only its
saved predictions, native labels and public input arrays. Allocate ten seconds,
one CPU worker, 1 GiB sampled RSS, zero engine/neural/backward/update/fit/paid
calls. Import NumPy only inside the durable stage guard; never construct a model.

Report every original per-seed gate with its threshold. Slice intended effects
by operator/complete template, target role/domain/owner/arena/health, amount,
current damage and natural HP. Mark exact TRAIN support for operator/amount,
operator/domain and operator/amount/damage/HP combinations. These are descriptive
rows, not independent samples or new untouched holdouts. Compare NEW, OLD and
the matched printed control, the exact deterministic reference, and the saved
zero-effect control. Retain all unknown future masks.

For committed intended effects with finite positive predicted eligibility p,
the frozen forward is delta = raw * p. Reconstruct raw = delta/p; replacing p by
native eligibility 1 is a deterministic, unfitted gate intervention. Report its
errors beside routed errors without calling it a learned improvement. Reject
zero/nonfinite p rather than impute. A positive gate cannot change an effect's
sign. Compare space versus base predictions when source/operator/amount/current
damage are identical: the endpoint branch sees only the changed target HP and
its knownness (source printed features remain fixed). This isolates that branch
input, not the effect of any future retraining or architecture.

No hypothesis search, new evaluation calls, new labels, tuning, production
change, conversion or opponent execution is allowed in this diagnostic. A later
correction needs a separate source freeze, pre-outcome holdout reservation and
bounded allocation. Keep 152/1,178 runtime-row and 47/1,432 deck-copy coverage
separate from PR45's 375 comparisons and 112 engine calls.
