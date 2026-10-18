# Frozen program vectors → trainable bag encoder (preparation only)

**DEFERRED / SUPERSEDED.** This is an unexecuted historical proposal, retained
for review history. No54-bag data preparation, forward or fit was run. The
actual27-corpus bridge replaces it; the budgets below are historical proposals,
not active allocations. The preparation CLI now fails closed.

This conditional composition diagnostic does **not** answer the real-deck
semantic question. The 27 saved declarations contain 1,432 main-card copies and
251 canonical main-card IDs. None has a saved selected-action vector: coverage is
0/1,432 copies and 0/251 identities. The real-27 learned/untrained/ID feature arms
therefore coincide at the explicit unknown vector; that comparison is not
admitted for fitting. Runtime admission alone does not supply a learned vector.

The seven exported main-role program IDs are HMW_170, IBH_016, LOF_134, SHD_196,
SOR_094, TWI_056, TWI_157. Five were used in card pretraining; HMW_170 and TWI_157
were held out. The larger action inventory has 19 main-role IDs: ASH_123, ASH_142,
HMW_170, IBH_016, IBH_023, IBH_062, JTL_146, LOF_134, LOF_178, LOF_243, LOF_246,
SHD_087, SHD_196, SOR_094, SOR_184, TWI_056, TWI_105, TWI_157, TWI_206. These
also have zero main-list overlap. The complete 1,178-card runtime admission
list covers 635 copies/115 identities; that is a separate native-support fact.

Canonicalization uses the pinned catalog's `card.setId`, `card.setCodes` and
`setCode`, merging repeated aliases before counting. Exported numeric
`canonical_card_id` is a source identifier, never a SET_NNN join key. Ambiguous
aliases fail closed. Leaders, bases, sideboards and tokens are excluded from
main-role coverage. Missing vectors never mean vanilla or whole-card known.

## Frozen data and split

Use **54 explicitly partial, nonlegal, two-card declaration bags**, with 1–3
copies per identity and 2–6 total copies. They have no leader/base/filler,
authorship, title/style or outcome inputs. Current-deck baseline counts are
outside its previous real-declaration range; disclose this distribution shift.
This is a supported **selected-action-program** bag diagnostic, not a complete
card representation or a legal-deck study.

Five training pairs form a cycle:
IBH_016–LOF_134, LOF_134–SHD_196, SHD_196–SOR_094,
SOR_094–TWI_056, TWI_056–IBH_016. Their ordered endpoints define copy templates;
canonical sorting never swaps which endpoint receives a template count.
The held pair is HMW_170–TWI_157. These six pair/template groups are **not six
independent real-deck families**: training pairs share card identities.

Training count templates are (1,1), (1,2), (2,1), (2,2), (2,3), (3,2), (3,3).
Held templates are (1,3), (3,1). Freeze 35 training rows, 7 held-card rows,
10 held-template rows and 2 joint rows. Every derivative/permutation/copy-expanded
view stays with its root bag. No post-hoc repartitioning or template selection.

## Four matched arms

1. Saved learned selected-action vectors (16 dimensions, frozen).
2. The same IR encoder at its frozen unused initial semantic weights (16d).
3. The saved trained ID-only table (16d, frozen); held IDs retain their original
   untrained table entries, with no adaptation.
4. Current saved deck model's frozen 96d latent for each new bag, broadcast to
   that bag's same actual identity rows. This baseline had earlier composition
   training; historical compute and pretraining task are not matched.

All arms have exactly the same two identity rows, copy weights, 130-wide input,
trainable graph, initialization, batches, target mask, objective and updates.
The first 96 channels hold a zero-padded 16d program vector or full baseline96.
The next 32 contain the same printed metadata in every arm; the last two flags
mean selected-program available and printed-metadata known. Unknown program
vectors are fixed zeros. Flags do not claim whole-card semantic coverage.
Printed32 = cost/power/hp divided by10; unit/event/upgrade; ground/space;
six aspect indicators; ten keyword indicators; eight deterministic trait bins.
No card titles, source IDs, leader/base IDs, pair IDs or split labels enter.

The **card encoders/vectors stay frozen**. The **deck encoder is trained**:
φ130→32 GELU; copy-weighted mean32 and sum32/60 plus total/60, distinct/60,
selected-program coverage and printed coverage; ρ68→32 GELU; head32→13.
This is exactly **6,829 trainable parameters** in each arm. It is invariant to
row order and duplicate-row splitting while retaining multiplicity. Nonlinear
ρ permits interactions mathematically; these labels do not validate synergy.

The 13 targets are total/60, mean printed cost/10, low-cost≤2 fraction,
cost-bin0…7 and8+ fractions, and unordered one-card unit probability. They
require only the shared printed inputs and copy counts; no semantics or game
strength is needed. Train on the fixed training-varying head mask with common
MSE. Report that mask, per-head loss and all-13 MSE, including constants and
regressions. Primary macro is the mean of train-varying heads, separately for
held cards, held templates and joint. All-constant mask is an admission failure.
Scores are measured once at initialization and once after fixed step100; no
checkpoint/seed search, no selection on held outputs and no strategic claim.

## Explicit execution gates and budget

Preparation is source/data/hash inspection only. The 16-root literal native
audit and its six frozen model evaluations are **planned, not yet measured**.
Fresh whole-card admission is unsupported; a limited old held-program/context
audit cannot establish it. Root must review and freeze sources, data, feature
banks, guard and this protocol before each serial execution stage.

Separate feature preparation permits **two** batches only: one frozen unused-IR
bank encoding and one frozen current-deck NumPy batch for all54 bags (≤64 rows).
Saved learned vectors and saved ID-table rows are read without new encodings.
Cap20 active seconds/1GiB/oneCPU; zero optimizer updates. No learned card weight
may change. Record exact bank sources, tokenizer/collision audit, frozen hashes
before/after, row alignment and coverage flags.

The later readout allowance is **100 updates per arm ×4 =400 total**, seed17,
full35-row batch, same AdamW schedule and cloned initial tensors, oneCPU,
1GiB sampled stop threshold,20 active seconds across all attempts. Exactly
eight initialization/final held batches (two per arm), with no extra evaluation
or forwards to select a result. Every actual update is durably journaled; failed
attempts retain elapsed time and quota, and no retry resets its ledger.

Overall staged caps: native60s/80 calls, card qualification20s/six forwards,
feature preparation20s/two forwards, readout20s/400 updates plus eight held
forwards:120 active seconds serially, zero paid work. Each stage still requires
root GO; this document launches none of them.

## Frozen evidence locations

Kessel commit `c7ee39554901278cee70f61fd8b26fb1920696b3`; catalog SHA256
`0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`;
runtime-admission SHA256
`91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957`.
Saved program export: `experiments/embedding-export/grounded-contrast-v1/card-embeddings.json`,
SHA256 `145cdedc7ae40dc7bf0a512de3bc27deb2d3de1f3a46c8ac69b4ac7bf068ff86`.
Real split: `experiments/data/real-decks.manifest.json`, SHA256
`1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622`.
Exact source paths/hashes, real27 coverage, partial bags and prelaunch plan are
emitted together by `staged_deck_composition.py --prepare`; feature banks remain
pending until separately authorized. Existing seed17/29/43 fresh transition
evaluations are prior limited evidence, not a replacement for the new gate.
