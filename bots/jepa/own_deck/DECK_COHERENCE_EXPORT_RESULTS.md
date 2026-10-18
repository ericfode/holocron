# Deck coherence exports and bounded counterfactual search

These are actual outputs of the saved **authored-versus-constructed classifier**.
The display name is “Deck coherence (exploratory authored-vs-corrupted classifier)”.
They are not calibrated coherence, synergy, legality, win probability or strength.
The earlier negative restoration result is unchanged: held-out family accuracy
was 0.4167 for the full head and 0.5 for the identity-masked head, with no aggregate
restoration gain. Neither head was fitted or changed for either export.

## Frozen source/reference export

`/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/deckiness-export/index.json`
retains the original 51-row score file and adds versioned pointers. Its current
SHA256 is `c13c720296d7cc69fe9c34b87d2673d221eee9e86d96968250786cf7ad6992c7`.

The 27 source declarations, 12 reproducibly sampled existing matched fixtures,
and 12 unfiltered random-copy reference declarations were scored by both saved
heads. The pinned declaration policy admits 26/27, 12/12 and 11/12 respectively.
The random population remains unrestricted even when its declaration passes.
Counts, raw printings, source fixture URLs, generator seeds, inherited splits,
fit exposure and admission reasons are attached to every row. Personal source
event links removed by the importer were not recovered.

This export used two batch forwards, 1.094 seconds through artifact creation,
177.31 MiB conservative sampled tree RSS, zero updates/native calls and $0.
All four saved restoration endpoints reproduced exactly for both heads. Baseline,
engineering initialization, logistic heads and original datasets stayed unchanged.
The full head checkpoint is
`d1a5e408db1288f731afa5c73fdf3289d8fbd4dc5605c73f6ad84055daf63ced`;
the identity-masked head is
`f5c96f00b5c468aabd5c5474feaf6417c1919d8ba5a20e30085e7e622c15ed85`.
Both retain the exact saved training mean/scale, size masking, identity-factor
normalization and frozen engineering-initialization encoder from the 200-update
probe. The composition-trained nearest-neighbor space is a different supplement.

The original score file remains byte-identical, SHA256
`98d1ae013c75f889b6f95180348f344eb4a1ca90737901313602d9b80799d3a6`.
The original 351 candidate pairs, 32 selected pairs and empty annotation arrays
are also unchanged.

## Scorer-adversarial exploratory counterfactuals

Versioned directory:
`/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/deckiness-export/adversarial-v1/`.
The pre-scoring input manifest fixes source choice, all candidate counts, seeds,
generators and constraints before either forward. Four search sources (8, 23, 6,
22) were chosen by replacement capacity without scores. Four disjoint inherited
validation sources (2, 10, 14, 25) form the reserved generator family. Source
families remain disjoint; card identities can still overlap.

The run scored **144 modified declarations plus eight original anchors**:
128 distinct modified compositions across the source identities. Three nested
paths per source/family supply levels 1, 4, 8 and `max_replaceable`. Search uses
uniform substitutions and trait-preferred substitutions. The reserved family
uses a different balanced allocation procedure and was never ranked, selected,
included in minimum summaries or used for tuning. Its 48 rows remain in fixed
generation order for later independent validation.

Every declaration preserves leader, base, main size, exact cost/type/arena/aspect
copy counts, canonical name/subtitle copy cap and the pinned policy. Alternatives
are source-bank cards with names absent from the original main list. Within each
exact metadata signature, the maximum is the smaller of available source copies
and three times the number of novel alternative identities. The disjoint bucket
sum is the feasible maximum **within that declared pool**, not a global search
over every legal deck. Actual replacements range from one to 28 copies. Source
10 has only six feasible replacements, so its nominal eight-copy level is capped
at six and duplicates its maximum level; repeated compositions are dependent.

Measured execution: two frozen batch forwards, **7.7446 cumulative seconds**
including the prior 3.7732-second pure preparation check, 220.48 MiB conservative
sampled tree RSS, one CPU thread, zero updates/native calls, $0. The fixed caps
were 20 seconds and 2 GiB. All protected checkpoints, datasets, original score
exports and exporter stayed unchanged. Eight anchor scores match the prior
export exactly. Display/instruction-only metadata amendments preserve executed
source bytes and performed no additional forward.

Full-head selection is the minimum of three SEARCH candidates for each
source/family/level. These 32 adaptive minima are not an evaluation sample.
The table averages their change from the corresponding source over four source
decks. The identity-masked head was never selected; it shares the original
provenance training objective and is not independent quality truth.

| Search family | Level | Mean full-score change | Mean masked-score change, unselected |
| --- | --- | ---: | ---: |
| Uniform | 1 | -0.001977 | -0.001793 |
| Uniform | 4 | -0.004693 | -0.004387 |
| Uniform | 8 | -0.007566 | -0.004392 |
| Uniform | Maximum feasible | -0.008531 | -0.004007 |
| Trait-preferred | 1 | -0.003832 | -0.003126 |
| Trait-preferred | 4 | -0.007135 | -0.008278 |
| Trait-preferred | 8 | -0.007868 | -0.006637 |
| Trait-preferred | Maximum feasible | -0.005211 | -0.003879 |

At maximum replacements, only **two of four sources** decreased in each search
family. More replaced cards did not reliably lower the score. The lowest sampled
full score was source 22 with 25 replacements: 0.50143028 → 0.46528216,
change **-0.03614812**. Its unselected masked-head change was -0.02196596.
This is an adaptive scorer counterexample, not an incoherence oracle. All means
are descriptive, source/seed dependent, and based on correlated nested paths;
no confidence interval, significance, population or strength claim is made.

Independent structural diagnostics retain actual trait/keyword copy counts,
catalog compiler-status coverage and evidence from the three explicitly reviewed
IR trait-target patterns. Interactions outside those patterns remain unknown.
The lowest-scoring example has zero such witnesses both as source and modified
deck, so those witnesses cannot explain or validate its score change. Compiler
“supported” status is explicitly distinct from native runtime admission. No
missing interaction, beneficial synergy or gameplay effect is invented.

## Independent review and blind review packets

`adversarial-v1/reviews-v2/` archives all three completed review JSON files and
the third review's Markdown report byte-for-byte; the earlier two-review
`reviews-v1/` version remains unchanged. `joined-annotations.json` joins
**21 separate reviewer judgments over ten
pairs**, preserving explanations, scopes and uncertainty without a consensus
label. The reviewers read full card definitions and visible metrics, so these
are metric-aware expert hypotheses, not blinded annotations or engine targets.

All three call Boba blue versus Thrawn yellow (`06--16`) misleading at cosine
0.9982122359812206 with five shared copies out of a 96-copy union. The effect
review calls the same-leader Boba control (`06--07`) plausible at the lower
cosine 0.9950520916707273 with 28 shared copies out of a 72-copy union. The
reasoning concerns differing trigger conditions, effect engines, arenas and
plans. Low count overlap alone does not prove a semantic mismatch. These reviews
do not establish strength or justify directly fitting their labels. Disagreement
is retained: for Ahsoka versus Talzin (`03--21`), the strategy reviewer says
plausible and the controls reviewer says uncertain. No majority truth is created.

The annotation index exposes model limitations explicitly: compressed cosine
values near one; 351 dependent pair comparisons and selected extrema; indirect
leader/base correlations with composition and split rules; fixed synthetic zero
context; and shared card identities across the inherited family split. These
are interpretation limits, not measured explanations of any particular vector.

The separate `blind_annotation_packets.json` contains 176 opaque-ID pairs: the
original 32 pairs and all 144 counterfactual pairs. It exposes only full counts,
leader/base and public references, with no scores, distances, overlap numbers,
generator, selection or authored/corrupted labels. Every annotation array is
empty. `annotation_analysis_join.json` contains the separate provenance/metric
join and must not be sent to blinded reviewers. Importing the completed reviews
did not modify those packets or fabricate counterfactual annotations.

## Exact artifact pins

| Artifact, relative to the export directory | SHA256 |
| --- | --- |
| `adversarial-v1/index.json` | `018b54e48d80c04bb10abab36f12215561402cb63fd60ed9f060e61ce17eeb7a` |
| `adversarial-v1/counterfactuals.json` | `2e35574a5ac4f19bb43c450ac0fea02f0b54676eeb6691bbe654297402793cfe` |
| `adversarial-v1/receipt.json` | `f02b40e7e9827e471acc9a9550c02cd0637efdeb73d05db4cd82cacce5b2c3ca` |
| `adversarial-v1/blind_annotation_packets.json` | `64f67bacd3e98cf2fb72c86a99111971564a3999e5870dc63414d58fa5e598de` |
| `adversarial-v1/annotation_analysis_join.json` | `a11544bf2cfd4fe86d2319e9f884d9835862590d2f2d0687f47ce08959ae6570` |
| `adversarial-v1/search-summary.json` | `3d131619bfb6de0b9ccca4265ba1cde70147fec97b5671be442921db5a4c83ad` |
| `adversarial-v1/legacy-index.before.json` | `3f2c6bd1e563199318cf422e25fe81d79b25bf364541686c21565d4abe15e023` |
| `adversarial-v1/reviews-v1/strategy-review.original.json` | `65d7dc21f35dc3008f7f44ec1cde5659ea775930d6d944cbafb2022d2a84bbd2` |
| `adversarial-v1/reviews-v1/effects-review.original.json` | `4d5d8d5cba2e2434923c9143b74fc8ce8422998c6d4f510fd1d73dc2b7b1d0dc` |
| `adversarial-v1/reviews-v1/index.json` | `f17a2ac60dc64eb4f66db10ba9ea5364f39f0bcc41c90c24adc24c2ee7af0954` |
| `adversarial-v1/reviews-v1/joined-annotations.json` | `abc2beaf63782065d241d1587dd2cdfd1b1e4132cf8153706f1fa15bc4886142` |
| `adversarial-v1/reviews-v2/controls-review.original.json` | `a7bab78165b9ee2e7567b05e6a23002afb05eb36532bdd6a2bb725d0fe0e5ff6` |
| `adversarial-v1/reviews-v2/controls-review.original.md` | `b675813be609f66cb2d0892851492514feaecddf855370f89c5ae3dd24d49a27` |
| `adversarial-v1/reviews-v2/index.json` | `f7e912329663d85a2210a99b57a4ca4bed5957f0bcd39317f2a112650da84828` |
| `adversarial-v1/reviews-v2/joined-annotations.json` | `4ebb903b8777fc3a8f6950ae22fef88aa28c451df6126895a405af729cdb8123` |

Exporter source `export_adversarial_decks.py`: SHA256
`230cbfc93fbef2b9b40e431087b66c513a840583aceacd60e8ecc250562ed8de`.
The original exporter remains SHA256
`df9d6e750730ac1ae99025e0ddc35db1e52ea161341767bbdfdceb960918dbaa`.
The executed code snapshots and metadata amendments are preserved externally.
No source research workspace, competitive checkpoint or live bot was changed.
