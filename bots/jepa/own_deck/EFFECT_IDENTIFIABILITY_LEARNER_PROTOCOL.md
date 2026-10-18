# Fixed-width effect identifiability: preparation, not a launch

This protocol implements [the frozen hypothesis](EFFECT_IDENTIFIABILITY_HYPOTHESIS.md).
The primary intervention is training observation coverage. It does not enlarge
the 16d encoder/leaf/head widths or the 512-token/32-path representation. New
reviewed vocabulary tables, ID-table size and bank cardinality are frozen once
for this cohort; their parameter counts are disclosed and identical across all
new arms. Old source, checkpoints, evidence and negative results remain intact.

The fixed cohort has seven training cards (ASH_048, LOF_151, SEC_142, JTL_144,
JTL_217, ASH_171, SEC_051) and five held cards (JTL_102, LAW_131, JTL_079,
LAW_127, ASH_228), each in three training and one held public state: 21 training,
15 family-held, 7 state-held and 5 joint roots. The targeted-debuff variants
LAW_131/JTL_079 form one held family; attached-exhaust LAW_127/ASH_228 another;
space-count damage JTL_102 is the third. No alias, exact program duplicate or
member of a held template family may cross training. Primitive damage,
exhaustion, stat modification and numeric signs must have actual training
support; otherwise the affected head/case is explicitly unsupported/OOD.

Native labels are actual settled before/after observations of one predeclared
public anchor per root. Modes distinguish chosen-target, upgrade-attachment,
self-entry and passive-area-anchor. Future labels never cover every offered
candidate by assumption. Area/attached paths need no fictitious target action.
Actual offered membership remains a separate native label. Full source
definitions remain serialized; SEC_051's event hook is preserved but native
fixtures avoid deaths and do not qualify that hook's behavior.

The frontend makes two reviewed cleanups: recursive UI title/contextTitle/
promptTitle annotations, and SEC_051-style callback argument bindings. Only
`dataPath`/`root=[event]` bindings with the reviewed invocation/read timing and
callback identifier syntax are canonicalized to lexical ability/hook scope and
first-occurrence slot. Repeated references remain equal, distinct binders/scopes
remain distinct, and raw source positions cannot identify the card. Unknown
binding shapes or genuine semantic fields reject. Old-eight documents and
semantic tensors must remain bit-identical for saved-model use.

Five new arms share cloned initialization, data, 200 updates, batch size18,
AdamW .003/weight decay .0001, clipping1, seed17 and precomputed batches:
rich typed; sparse typed; rich ID-only; rich unused typed encoder; rich shuffled
typed. ID and frozen-encoder trainable counts differ and are disclosed. Wrong
typed inputs freshly exclude the actual/equivalent training card each update.

Only sparse TRAIN masks change: the five candidate stat-delta heads are masked
out, recreating PR35's missing training supervision. Source, membership and
removal masks remain identical. Missing observations never become zero labels.
All evaluation arms use the same full rich native masks. Input/literal/head
transforms, head eligibility, signed-class weights and explicit loss coefficients
are computed once from rich TRAIN and shared, including sparse; this is fixed
control information. The loss denominator stays fixed even when a sparse head
has no observations. Constant/unobserved heads cannot silently become primary.

Primary behavior is family-first native target-effect error, not source
cost/location, membership, neighbors or composition. The groups are damage,
exhaustion, Shield and joint power/HP statistics (the latter count as one
correlated mechanic). At least two observed zero and two nonzero TRAIN
coordinates are needed per head; all signed/per-card support counts are reported.
This is a minimal identifiability threshold, not a large-sample guarantee.
Family applicability is fixed from reviewed mechanics before labels: count
damage uses damage/Shield; targeted debuffs use joint statistics; attached
exhaust uses exhaustion/joint statistics. Every held family remains reported,
including zero-change negatives and unsupported directions.

The held gate requires rich typed to reduce this fixed family-first error by
at least 10% versus the strongest eligible sparse/ID/unused/wrong/train-mean/literal-zero
control, including both train-mean and literal-zero heads. At least two held families and three held program groups must have
support. There is no per-family winner selection. The fixed contrast panel is
JTL_102 state0↔1 and2↔3; each attached-exhaust card state0↔1 and2↔3; and
LAW_131↔JTL_079 within each of the four states. These are public scenario/program
contrasts, not automatically isolated one-feature causal interventions. Native
unknowns remain unknown; pairs are not selected by their observed sign.
Require at least four measured pairs across two families, family-first contrast
direction accuracy ≥.75 and ≥10% lower train-scaled contrast error than the
strongest eligible control. Sign uses a predeclared ±.25-native-unit deadband;
zero contrasts require |predicted contrast|≤.25. Joint statistics receive one
group weight. Every pair and family error is retained even if the gate fails.

Exact model-visible input hashes are checked against co-observed native labels
before fitting. Source hashes include public intended-candidate features;
candidate hashes do not invent access to intent. ID-only hashes use actual
table indices, including common held UNK0; wrong-evaluation hashes use the
wrong card actually supplied. Expected control ambiguity is counted and never
hidden behind unconsumed true-document IDs. Declared intent, anchor role and
masks are recorded alongside hashes. Conflicts in the correct/sparse typed
contract block fitting until explicitly repaired before execution.

Saved PR35 evaluation is separate and descriptive: only the two compatible
current TRAIN identities (ASH_048/JTL_217), original old-eight bank/documents,
old schema/checkpoint and old numeric transforms. There is no model resize or
unknown remapping. A single fixed batch includes compatibility replay anchors;
it makes no claim about the new held families and is not a fitted control.

Proposed fixed fit cap is five×200=1,000 updates, 1,000 training forwards/
backwards, ten initialization/final full-data evaluation batches and one saved
diagnostic batch: 1,011 forwards, zero separate export forwards, one CPU,
60 active seconds/1 GiB sampled RSS, zero paid work. Native cap remains90s /
256 applies (48 roots, local bound5/root=240); shared campaign cap180s.
Every attempt uses the frozen hash-chained ledger and one serial lease;
failures retain elapsed time and conservative reserved exposure. This document
does not authorize any native action, forward, fit or reset.

Rich success would support supervision sufficiency for this model and cohort.
Rich failure would show that this data expansion did not rescue transfer;
capacity, optimization, representation and cohort limits would remain possible.
A same-capacity comparison cannot establish capacity as the cause. Neither
outcome authorizes a larger model, joint fine-tune or held-result tuning.

Sealing also enforces the support thresholds before a fit is admissible: all
four planned mechanics must satisfy the two-zero/two-nonzero training rule;
at least two held families and three observed held program groups, and four
fixed known contrast pairs in two families, must exist. A support failure is
preserved as a collection/identifiability failure and stops before neural work.
This admission uses training labels and held observation masks, never held
prediction errors. All five arms start from the saved full initial checkpoint.
Per-tensor last-step gradients are labeled post-clipping; the journal records
pre-clipping total norm. The guard's macOS RSS API was corrected and smoke-tested
before execution; this preparation correction is not an experimental attempt.
