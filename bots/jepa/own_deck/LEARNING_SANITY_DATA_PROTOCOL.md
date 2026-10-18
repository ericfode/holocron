# Learning sanity: saved-data audit and fixed linear controls

Preparation only. `learning_sanity_data.py` performs no neural/native work. Its
actual saved-data audit and closed-form fits require the coordinator's frozen
plan and separately bounded, one-thread, at-most-10-second analysis stage. It
does not revise the prior held-family negative result or select representations.

Inputs are the exact existing 48-root native dataset (`2254eef7…`), manifest,
sealed prior plan (`6eadc7c3…`), saved prior result (`90cac45d…`) and independent
wire audit (`5410975a…`). All input/source pins are checked before and after.
The split remains 21 TRAIN, 15 family-held, seven state-held and five joint.
Unknown coordinates remain masked; no new native observations are inferred.

The audit reports every source/target head's known support, native values,
population variance and signs by split and TRAIN card. Effective loss weights
are exposed per observed coordinate: original head coefficient times original
TRAIN sign-class weight, divided by that head's observed TRAIN-root count and
the root's observed candidate count. The sign selects the assigned target's
class from the original table. Source heads have candidate count one. Sparse
neural objectives omit five terms and cannot be compared by raw loss alone.
The saved wire audit, selected-role plan and masks are rechecked. This is not a
second engine-conformance test.

Two ridge controls fit correct labels and the neural owner's one fixed joint
five-delta packet derangement. Only the 14 fully co-observed TRAIN anchors move
their complete five-vectors. Recipient roots, selected candidates, source labels,
other target heads and every observation mask remain fixed. No independent
shuffle, headwise permutation, held-label fit or hyperparameter search is used.

Predictors are public global18 + candidate-own34 + seven TRAIN-ID indicators.
The source head uses the predeclared intended candidate; each branch head uses
only its own candidate, with no intended-candidate index. Held IDs have all-zero
raw and transformed ID indicators. The first 52 predictor columns use TRAIN-only
mean/std (zero-variance scale one); the seven ID columns remain unscaled.
Source transforms use the 21 intended rows; branch transforms use all 21×8
public candidate rows, regardless of label knownness. Both are saved explicitly.

Each of all 16 heads solves **SUM** base-weighted squared residual plus
`lambda=1` times squared slopes. Ridge base weight is the original TRAIN sign
class weight divided by the observed candidate count in that root. It omits
the neural head coefficient and observed-root denominator, so its total mass
is approximately the observed TRAIN-root count, not the neural head's mass.
Both absolute weights and each head's sum are reported. The intercept is
unpenalized. Regression targets
use the original neural output center/scale; binary targets remain 0/1. This
matches masks and relative sign/root weights, but differs in absolute objective
mass and uses least squares instead of neural Huber/BCE. It has less rule
information than the typed model. It is an easier
finite-sample learning diagnostic, not a matched-capacity semantic competitor.
No 1-nearest-neighbor self-retrieval control is used.

Outputs retain design ranks, singular/condition diagnostics, slopes, intercepts,
weighted residuals and all predictions. Binary scores are clipped to [0,1] for
reported metrics; raw and clipped residuals are distinct. TRAIN is scored against
both TRUE and ASSIGNED labels. Typed-input TRAIN collision audits use the prior
actual consumed-input signatures, exclude masks/labels from input keys, and
never select the permutation by its result. All held cells use only true labels.
These held labels were examined in the previous experiment; current held
readouts are descriptive. Each head
reports native/normalized MAE, RMSE, max error, and sign/zero classification using
fixed native thresholds of ±0.25 for numeric sign/zero and 0.5 for binary
classification. TRAIN-mean and literal-zero constants are included
without fitting. All targets and negative results remain visible; no metric
selects a model, lambda, stopping point or data split.

The neural owner's separate protocol fixes three arms ×300 full-21 updates
(900 total) and six initial/final evaluations (906 total neural forwards).
This module performs zero optimizer updates and zero neural/native calls.
