# Controlled remove-and-restore probe

This is a small authored-versus-constructed **coherence proxy**, separate from
strength, legality and action/world-model training. Fit two 96-dimensional
logistic heads on frozen representations: full hashed identity plus printed
features, and an otherwise matched identity-masked printed-feature control.
The frozen model is the baseline plus checked-in engineering initialization,
independent of the later 300-update composition fits. Titles, source identity,
URLs, authors, leaderboard information and lineage fields are not model inputs.

The allocation is one seed (17), 200 full-batch updates per head, **400 total**,
fixed learning rate/L2, one NumPy CPU worker, 60 seconds total, and a conservative
2 GiB sampled process-tree stop threshold. Baseline and final provenance
classification diagnostics consume four validation calls; no hyperparameter,
checkpoint or seed search is allowed. All fit rows come from inherited training
families. The final heads score held-out restoration fixtures once. This is a
new bounded head-only allocation, not another run of the earlier 300 updates.
No paid compute is justified for these small matrices.

## Controls and interpretation

The primary curve always has the original full main-deck size. Selected cards
are replaced with alternative cards, and true originals are restored one copy
at a time. Every primary step is compared with the full-size all-alternative
anchor. Alternatives match printed cost, type, arena and aspects, pass the
[pinned declaration admission](RESTORATION_ADMISSION.md), and respect canonical
copy limits. Other stats, keywords and effects can differ; the test does not
isolate strategic synergy from every card property.

For the anchor, the horizontal coordinate is the true arm's nominal restoration
step; **zero actual originals are restored in the anchor**. Repeating it gives
no independent observations. Individual-card and IR-grounded trait-target
packages are reported separately. The fixture preserves the effect/selector
evidence behind each package, without assuming that restoring it is beneficial.
No loss term or postprocessing forces increasing scores. Report decreases and
matched-control deltas, aggregate within group/source/family before averaging,
and retain coverage gaps.

Incomplete original decks form a separate size-changing diagnostic path, never
a fit label or part of the primary aggregate. Explicit size fields are masked
and identity-factor mass is normalized. These incomplete declarations are
out of distribution for this classifier. They are **not** remaining draw piles
during a game: a depleted pile must not become a bad-state target. Current
remaining composition is still explicitly unknown.

The authored/constructed label records provenance, not objective quality:
constructed alternatives may be good and authored lists may be poor. A head
can learn construction artifacts. Source families, exact main-list identity
and near-clones remain in their original partitions; no reshuffle compensates
for missing alternatives or excluded decks. Exact and hashed card overlap is
reported, and an identity-masked control does not establish unseen-card
generalization or remove every indirect identity cue from printed metadata.

## Source and admission coverage

The existing credited 27-list bank and pinned Kessel catalog supply all cards;
there is no new scrape or tournament-result label. The conservative current
declaration policy admits 26 sources. Source index 3 is excluded as an entire
origin lineage because its old base printing's eligibility remains unverified.
Exact alternative coverage further limits the held-out fixtures. The prepared
bank has 48 training / eight validation provenance rows, seven/three families,
and 27 restoration points from three held-out sources across four groups,
including one IR-grounded package. The manifest records all exclusions and
unsupported package matches. This is a tiny diagnostic holdout, not a population
estimate. No gameplay or historical-event legality is certified.

## Live artifacts

Use the same [`jepa-run-event/v1`](run-events.schema.json) append-only feed.
Optimizer updates, head losses, final per-point restoration scores, actual
versus nominal restored counts, control kind and family aggregates are measured
events. Incomplete diagnostics are marked separately. Source commit, dataset,
policy, checkpoint and split hashes are pinned before execution; result and
checkpoint hashes accompany completion. A heartbeat reports liveness only.

Dataset and fixture lineage live outside the repository under
`/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/restoration`.
The independent dashboard worker consumes that feed and the linked artifacts.

## Measured pilot

The single execution at `bef4e82fe7ceb7100eac8b2572275fc0dd64b0b9`
completed **400 head updates**, four fixed provenance-validation measurements,
and 54 final curve points (27 per arm). All points and eight aggregate records
were appended to the feed. The worker exited cleanly; the conservative tree
RSS bound was 105.94 MiB and total measured run wall time was 0.113 seconds.
The frozen model/checkpoint files stayed unchanged. No retry, extra fit,
deployment or paid job followed these measurements.

| Held-out diagnostic | Full frozen latent | Identity-masked printed latent |
| --- | ---: | ---: |
| Final family-macro provenance log loss | 0.69679 | 0.69940 |
| Final family-macro provenance accuracy | 0.4167 | 0.5000 |
| Full-restoration minus matched-anchor score, family macro | -0.00236 | -0.00117 |
| IR-package endpoint change | +0.00408 | -0.00219 |
| IR-package adjacent changes | -0.00134, +0.00541 | -0.00121, -0.00098 |

There is **no aggregate restoration gain** in this pilot. All three individual
card endpoints decreased in each arm, and the package has a nonmonotonic full
latent curve. The classifier is weak on three held-out families; these results
do not establish lack of synergy, intrinsic deck quality or an encoder defect.
They can reflect weak labels, construction artifacts, limited representation,
insufficient training signal or a small holdout. No test or loss enforces a
positive slope. Scaling this particular probe onto a GPU is not justified.
The next useful evidence is action-conditioned transition grounding with typed
cost/target/effect controls, rather than a larger provenance classifier.

[The compact result](restoration-results.json) pins the raw result and
checkpoint hashes. [The raw result](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/runs/restoration-bef4e82-s17/result.json)
contains every curve point, admission/source lineage and guard receipt.
