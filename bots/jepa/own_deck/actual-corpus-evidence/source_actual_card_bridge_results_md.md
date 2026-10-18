# Actual-card → frozen-card → deck experiment

The bridge now uses real cards from the 27 saved declarations, but the learned card encoder **failed its held-card transfer test**. The fixed deck comparison does not rescue that result: ID-only and the saved current-deck baseline have lower composition error. No semantic-quality, synergy, action-quality or playing-strength improvement is established. No joint fine-tuning or competitive deployment followed.

## What changed

The competitive actor already sees own-hand/public-board identities and stats, offered-action features, and numeric deck size. It lacks the original deck multiset, remaining identity counts and whole-deck mechanical context. The earlier isolated extension adds original/unknown-remaining tokens using count-pooled shared hashed identity factors and printed summaries; those factors were not separately qualified native-effect card embeddings. See [recovered baseline audit](AUDIT.md) and [representation diagnosis](DECK_REPRESENTATION_DIAGNOSIS.md). The production bundle remains unchanged.

The new staged prototype first learns a 16d static card vector from reviewed printed metadata, intrinsic keywords and the complete typed abilities/conditions/costs/targets/literals of eight actual cards. Public state and the intended public target condition native prediction heads. It then freezes the card vectors and trains a count-aware DeepSets deck encoder: per-card φ130→32, copy-weighted mean and sum plus count/coverage scalars, ρ68→32, and a 13-head composition readout. Nonlinear pooling can represent interactions; these targets do not establish learned synergy.

| Coverage layer | Actual main identities | Copies / 1,432 |
|---|---:|---:|
| Runtime-admitted loader definitions |115 /251|635 (44.34%)|
| Old twelve selected-action vectors |0|0|
| New full-input/native-fixture card bank |8|65 (4.539%)|
| Card pretraining identities |6|59|
| Card-held identities |2|6|

Runtime admission explicitly does not assess game conformance. All 251 identities, 1,432 copies and per-deck unknown masks are retained. The other 1,367 copies have no new semantic vector. Eight decks, including two held decks, have zero bank coverage. Runtime admission varies from 20% to 66.15% by deck. Complete source rows and exact per-deck coverage are in [coverage audit](ACTUAL_CORPUS_COVERAGE.md); the immutable full-row artifact is `experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json`, SHA `dd3ec9dc77f1f888d070f7e8ed0ab20290c347c75c75f6fe01f5504ce43f0480`.

## Native and card evidence

Unmodified Kessel `c7ee39554901278cee70f61fd8b26fb1920696b3` supplied 32 public fixtures, eight cards × four states, using 38 actual applies: 24 offered own-hand plays, 12 chosen targets and two native declines. There were 24 settled roots, eight unavailable plays, 23 paid/settled plays and no engine errors or pending outcomes. Every card had at least two paid/settled witnesses. An independent snapshot-to-array review found no label/mask mismatch or private-information input. See [native endpoint audit](ACTUAL_CORPUS_ADMISSION_AUDIT.md).

Six cards × three states train (18 roots); LOF_155/JTL_217 × seen states are card-held (6), seen cards × state3 are state-held (6), and the joint cell has two roots. LOF_155 is within the seen upgrade-defeat family but has a new restriction. JTL_217 is a single held exhaust-primitive stress case. Five target-delta heads have **zero** training observations; target removal is training-constant one. Their held errors cannot establish learned effect binding. Shielded entry is observed; Sentinel attack behavior and upgrade-host downstream losses are not qualified.

All four card arms share initialization, data schedule, allocated graph and 200 updates, seed17. Allocated parameters are 11,168; actually trainable counts differ because the unused encoder/ID branches are frozen. Every negative head and both zero-neural baselines remain saved. Lower values below are root-mean MAE normalized by training scales, averaged over training-varying observed heads; this is not game performance.

| Card arm | Train | Card-held | State-held | Joint |
|---|---:|---:|---:|---:|
| Learned typed |.011659|.330944|.044255|.317687|
| Trained ID-only |.009914|.161349|.037215|.160734|
| Untrained typed encoder |.071709|.141036|.100711|.161999|
| Wrong typed input |.075826|.108723|.100544|.112144|
| Training-only constant prior |.377295|.306308|.349520|.297435|

The typed encoder did receive optimization: 4,368/4,416 encoder coordinates changed relative to the frozen initial encoder; its eight vectors changed. Held target-membership balanced accuracy improved to .7778 versus ID-only .5556, a narrow positive signal. It nevertheless generalized worse on the overall held-card outcomes. One trained cost prediction was negative for a native cost of five. The wrong-input arm is an incompatible whole-card control, not a pure effect-only ablation. See [complete card qualification results](ACTUAL_CARD_QUALIFICATION_RESULTS.md).

## Frozen vectors in the actual declarations

All four new deck models have 6,829 trainable parameters, identical initialization/full training batches and 100 updates. The inherited split remains 22 train / five held declarations in four held families. All card banks stay frozen; held native outcomes are absent from deck labels. The saved current-deck baseline had earlier composition training, so historical pretraining compute is not matched.

| Frozen feature bank | Held 13-head MSE | Held family-first MSE |
|---|---:|---:|
| Learned typed card vectors |.0107333|.0116107|
| Untrained typed card vectors |.0111178|.0117234|
| Trained ID-only card vectors |.0105058|.0113164|
| Saved current-deck latent |.00821346|.00914558|
| Training-only target mean |.0150234|.0158290|

These labels reconstruct printed count/curve/type statistics already present in common inputs. Slight improvement over the untrained bank does not qualify semantics, especially given the card-stage failure and low coverage. Fixed initialization/final batches also checked all 27 declarations, reversed rows, canonical duplicate splitting and a one-copy perturbation: maximum permutation gap 4.77e-7, duplicate gap zero, and multiplicity changes the saved latent. There were no extra export forwards. See [deck results and per-head regressions](ACTUAL_CORPUS_DECK_RESULTS.md).

## Accounting, sources and decision

Executed source head: `8fb922bf56869c72f828ee8312a449f3891ed406`. Card source was frozen at `00eae396791e785edfa82ff1a013706961815151`; deck source at `2fda449`. Native collector/guard repairs are preserved in intervening commits and four failed attempts. They corrected memory accounting, restored prior compiler partitioning, used the public trait catalog API and registered ordinary fixture attachments. They did not change engine/card coverage, the frozen card/state selection, label definitions or model settings. All failures remain charged in the same append-only ledger.

Total recorded active time is 19.252928208 seconds, including failed builds, with 38 native applies, 1,200 updates and 1,216 neural batch forwards. Separate export forwards, paid jobs and Modal spend are zero; the cumulative $100 Modal cap remains unused. The successful stages passed their guards. A genuine earlier build memory excess remains visible rather than being presented as a passing run. Original task4/task5 workspaces, protected checkpoints and the competitive WASM are unchanged.

The next scientific requirement is broader **identifiable native consequence coverage among admitted actual cards**, with positive/negative examples and repeated held card/effect families. It is not a larger encoder, variance-only fix or joint fine-tune selected from these held results. The saved research remains recoverable at `c39e1534664d6c055c844722f7251ee6cdf6c3ac`; this does not establish recovery of the broken chat interface. Publication consistency and the portable prior evidence are documented in [export results](EXPORT_CONSISTENCY_RESULTS.md).
