# Actual27 main-deck coverage (data only)

The inherited22-training/5-held declaration split contains1,432 main-card copies
and251 canonical main-card IDs. Every copy is retained, including all unknowns.
This is a declaration audit, with zero native calls, model forwards or updates.

| Evidence layer | Unique main IDs | Main copies |
|---|---:|---:|
| Runtime-admitted loader rows |115|635 (44.34%)|
| Saved12 selected-action vectors |0|0|
| Proposed8-card native/model subset |8|65 (4.539%)|
| Native-fixture verified (at snapshot) |0|0|
| Whole-card typed model serialized (at snapshot) |0|0|
| Learned whole-card vectors/trained (at snapshot) |0|0|

The admission file explicitly says `gameConformance: not assessed by this
report`. Its115 cards comprise91 `sourceIr` rows/495 copies and24 `dataOnly`
rows/140 copies:92 units,15 events and8 upgrades. Their97 registered abilities
are24 `whenPlayed`,19 `onAttack`,14 `whenDefeated`,21 `constant`,15 `event`,
two `onDefense`,one `whenAttackEnds`,one `eventHooks`, and zero activated
`action` registrations. The previous action-program pilot misses this corpus.

Twenty-five admitted cards have no registered IR abilities. Sixteen have
intrinsic keywords; nine have neither registered IR abilities nor keywords.
These counts do not prove vanilla semantics: executable top-level attachment
conditions, piloting, stat modifiers and other fields can still matter.

The proposed eight are ASH_04819copies/8decks, JTL_0959/3, SEC_16313/6,
LOF_1553/1, LOF_0779/3, JTL_0786/3, JTL_1583/1, JTL_2173/1. LOF_155 and
JTL_217 are proposed held-card identities. This proposed subset is separate
from actual verified or learned coverage. Eight of27 decks have zero proposed
card coverage (six training/two held); no deck is dropped for that reason.

Canonicalization joins `card.setId`, `card.setCodes`, and `setCode` through the
exact pinned catalog. Numeric source IDs are recorded separately. Duplicate
printings merge before counting; ambiguous aliases and malformed counts fail
closed. Leader/base declarations are preserved separately and excluded from
main totals. No draw order, opponent observations or private data is involved.

`actual_corpus_coverage.py` emits per-deck canonical/source IDs, copy counts,
layer-specific coverage fractions and unknown masks, plus a deterministic
inventory of all115 admitted main cards. **Coverage-v2 preserves each entire
catalog row**, including top-level `attachCondition`, `stateWatchers`, piloting
or future fields, with its canonical row hash. Convenience printed/ability
fields alone must not be treated as a whole-card semantic frontend.

The immutable external artifacts are:

- `experiments/actual-corpus/coverage-v1/actual-corpus-coverage.json`, SHA256
  `3e8d996dc342bab07ea325872a89c627221938bda85f8442cba4a6699b2397f4`.
  This original selected-field inventory remains unchanged; its exact source
  snapshot is retained in `coverage-v1/sources/actual_corpus_coverage.py`.
- `experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json`, SHA256
  `dd3ec9dc77f1f888d070f7e8ed0ab20290c347c75c75f6fe01f5504ce43f0480`.
  Complete catalog rows; source SHA256
  `c93ffc307824010f00eff4ea046ef053d648c386d0e2a5a7a32917809377c4f5`.

Both artifacts contain exact input paths, byte lengths and SHA256 pins. The
catalog SHA is `0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`;
runtime admission SHA is
`91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957`, from
Kessel commit `c7ee39554901278cee70f61fd8b26fb1920696b3`.
The focused nine stdlib tests cover aliases, exact counts, unknown preservation,
source-ID joins, inherited split, main-form exclusion and complete-row hashes.
