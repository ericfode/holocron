# Training sanity passes; held-family transfer still fails

The pipeline can fit both the correct deterministic training labels and an
arbitrary fixed shuffle of them. No basic optimizer, target-alignment or
normalization failure was found. The observed failure is generalization under
thin and shifted semantic coverage; this test cannot assign that failure to
encoder capacity. A broad capacity sweep is not justified.

The neural execution source is **`187860ce7dfd76aae5e574d5b73f7371542ea918`**
(`learning_sanity.py`, SHA256 `f96830caf577b7e41a1243e8701c2af7a59f4dbd5c09da13d957f0b88f008fc8`).
The fixed data/ridge analysis source is
**`d5939b2285a8cb7d8a59d57a61d3345e278a0512`**
(`learning_sanity_data.py`, SHA256 `477bbf31a63f2e321e3b0f85b24606d66659974c3342d7a991d6a234af75cbb4`).
The previous [negative result](EFFECT_IDENTIFIABILITY_RESULTS.md) remains intact.

## Fixed diagnostic and fitting result

The [neural protocol](LEARNING_SANITY_PROTOCOL.md) froze three identical typed
models, the saved 11,856-parameter initialization, original TRAIN-only transforms
and full auxiliary loss. Each received 300 full-batch updates on the same 21
TRAIN roots, with no width, learning-rate or stopping search. Fourteen anchors
have all five effect deltas observed. Held labels never entered training.

Only those joint five-value effect packets were shuffled; recipient inputs,
anchors, masks, source outputs, membership and removal remained fixed. The fixed
derangement changed 13/14 packets and 32/70 coordinates; duplicates were reported.
Fresh shuffles used a saved, outcome-independent schedule of 300 derangements.
Initial and final all-48 forwards also captured predictions and vectors.

The correct arm passed the predeclared gate for **every** effect head: final
TRAIN-scale MAE <= .05, at least 95% reduction from initialization, and >= .95
native zero/sign accuracy using a +/- .25 deadband. Actual normalized MAEs were
.00440, .00535, .00815, .00624 and .00954; zero/sign accuracy was 100% for all five.
Native MAEs were .00662, .00535, .00815, .00807 and .01150.

Fixed-shuffle assigned-label normalized MAEs were also small:
.00224, .00257, .00472, .00608 and .00589. Against TRUE labels they were instead
1.13980, .28798, .28656, 1.10937 and 1.07074. This demonstrates that updates follow
the supplied labels; memorization alone does not establish semantics. Fresh
shuffle TRUE-label errors stayed high. Its auxiliary labels remained correct,
so it is not a pure information-free control.

## Per-target train/held comparison and fitted baseline

Values below are normalized MAE over the observed coordinates, with TRAIN /
family-held row means. These are per-head errors, distinct from the previous
family-first mechanic aggregate. All 16 heads, native/normalized MAE, RMSE, max
error, signs, rare classes, and all four split cells are retained in the evidence.

| Target delta | Correct neural TRAIN / held | Fitted ridge TRAIN / held | Zero TRAIN / held |
| --- | ---: | ---: | ---: |
| Damage | .004 / .545 | .495 / .753 | .569 / .177 |
| Exhaustion | .005 / .554 | .039 / .403 | .143 / .267 |
| Shield | .008 / .280 | .228 / .231 | .143 / .067 |
| Power | .006 / 1.823 | .228 / 2.384 | .552 / 1.546 |
| HP | .010 / 1.748 | .297 / 2.565 | .533 / 1.493 |

Zero beats the correct neural arm on **every** held effect head. Correct neural
family-first error remains 1.599818 versus zero 1.414729. A shuffled/null arm's
lower held error is not selected as a semantic winner. These held data were
already consumed in PR36; all new held readouts are descriptive.

The [linear-control protocol](LEARNING_SANITY_DATA_PROTOCOL.md) fixed weighted
ridge at lambda=1, with an unpenalized intercept and TRAIN-only predictor
standardization. It uses 18 public global fields, 34 local-candidate fields and
seven TRAIN identity indicators; held identities are zero. Source heads use the
intended candidate; branch heads use only their own candidate. This baseline has
less rule information than the typed model and no conditional interactions.

All 16 heads were fitted for correct and fixed-shuffled labels: 32 closed-form
fits, no hyperparameter selection. Relative sign/root weights match the neural
loss, but absolute mass and objective deliberately differ. Ridge omits the neural
head coefficient and observed-root denominator: primary weight sum 14 versus
neural sum 1/12. Ridge minimizes squared residuals, while the neural loss uses
Huber/BCE. Binary scores alone are clipped to [0,1] for evaluation.

The primary weighted design has rank 10/60. Ridge does not memorize all outcomes,
but it solves the declared regularized problem: independent maximum relative
normal-equation residual is **5.16e-16**. Its errors are not evidence of a failed
linear solver or an unfinished fit.

## Alignment, variance, weighting and coverage

Independent saved-wire inspection found no mismatch across 48 roots, 87 recorded
actions, 135 before/after captures, all 12 source documents, 48 context rows and
384 candidate rows. Features use the before state; targets use actual settled
endpoints. Legal offered actions, selected queries, physical attachments and
passive observation anchors were checked separately. No new engine call was made.
Correct and fixed-shuffle TRAIN typed-input conflicts are both zero. Unknown
future coordinates stay masked; each primary head has 14 known and 154 unknown
TRAIN coordinates.

Targets are not constant: TRAIN variances are damage 2.265306, exhaustion/Shield
.122449 each, power 1.673469 and HP 1.454082. Scaling and inverse scaling were
independently checked. Original effective weights include head coefficient,
sign-class weight, observed-root count and per-root candidate-mask count.
Rare exhaustion-positive/Shield-negative roots have sign weight 3.5; the sole
negative-stat root has weight 4.6667 and contributes one third of its head's
weighted mass. Those are explicit choices, not extra independent examples.

Coverage is still weak: nonzero exhaustion comes from one TRAIN card/two states;
negative stat changes from one TRAIN area-effect anchor (power clamps from 1 to
0, HP changes by -3). Held targeted debuffs have -2/-5 outcomes and different
templates. Parent-card references and space-count query atoms were not trained
in equivalent roles. Five held identities represent only three template
families. Availability is constant-positive. Matched held debuff pairs have
identical public numeric candidate inputs but different programs/outcomes,
making the held-UNK identity control inherently ambiguous.

## Decision, next experiment and preservation

Basic learning sanity **passes**. The optimizer can memorize even deliberately
wrong assignments, so a larger model or longer fitting is not the next step.
The remaining question is semantic input sufficiency and transfer across
operators, references and signed magnitudes, with very limited independent
training support. No semantic or playing-strength qualification is made.

Next, freeze a small **public-input sufficiency and binding test** before another
learned representation experiment: audit each supported predicate/query/reference
against the exact consumed fields, then construct paired public states changing
only the referenced count/host or a signed literal. Require multiple independent
TRAIN templates per tested mechanic, balanced zero/nonzero signs, and supported
operators in TRAIN; reserve fresh grouped program/state holdouts. A missing
observable or same-input/different-outcome pair should stop training and identify
the contract gap. Only then compare the same-width pooled and explicit-binding
representations, with fixed label-shuffle, ridge, mean and zero controls. No
capacity sweep or new representation fit was run in this diagnostic.

New exposure is exactly **900 updates/backwards, 906 forwards, 32 linear head
fits, zero native actions and $0 paid work**. Neural time was 3.906379s; data
analysis .222913s; independent verification .218154s: 4.347445s total. The neural
guard sampled 362,577,920 bytes peak RSS. Prior ledgers remain closed and unchanged;
this is an explicit increment, not a reset. All new stages completed without a
failure or retry. Eleven neural, eight data, six verifier and four runner pure
checks passed; independent verification found no audited mismatch.

The tested remaining-card ledger remains out of live inference until complete
instance/event provenance is established. All 38 protected hashes, original
task4/task5 workspace states, the PR36 evidence index and prior ledger remain
unchanged. See the complete immutable
[learning-sanity evidence index](learning-sanity-evidence/index.json) for source
pins, schedules, raw predictions, checkpoints, ridge designs/coefficients,
all per-target metrics, audits and negative held results.
