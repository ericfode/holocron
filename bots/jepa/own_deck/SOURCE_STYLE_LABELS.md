# Source style labels

All 27 imported decks explicitly contain one `metadata.style` label. These are weak fixture labels; they are not established behavioral or strategic ground truth.

The importer preserves `# Style: <word>` fixture comments and lowercases the captured text (`engine/decklists.js:204–240`, `decks/import-swusim.js:25`). The README attributes fixtures to TCGEngine / SWUSim `SWUSim/Tests/BotFixtures/ash-meta-2026-09` at `a2df9722314b1233d16747f7e56186071106799c`. Current deck JSON is byte-identical to the first local import `6253b1af1890df67d383141759c739834f7cba38` (2026-10-11), historical `bot/decks/ash-meta-2026-09.json`.

Original upstream fixture text was not found locally and its upstream commit object is absent here. Original comment casing and annotation author are unknown. The parser/README provide the import contract; they do not independently prove who authored the original annotation. No web lookup was performed for this audit.

There is no contradiction with a public API defining archetype as leader/base and exposing no strategic-style field: these labels are separate fixture annotations. Do not describe them as structured SWUMetaStats/SWU Stats strategic tags. Titles and leader/base/color names are excluded as substitute labels.

The companion human JSON has 27 exact-name-joined `archetypes` entries, each with `fieldDecks`, `gameWinPct`, `key`, `label`, copied by `import-swusim.js:34–35`. Their labels/keys describe source leader/base/color groupings. Human win rates pool lists of the leader/base, not this exact deck. Local family IDs are derived from shared leader, base, fingerprint or ≥80% copy overlap; they are not source-authored style classes.

## Coverage and inherited split

| Style | All rows | Train rows / families | Held rows / families |
|---|---:|---:|---:|
| hardcontrol | 4 | 4 / 2 | 0 / 0 |
| hyperaggro | 4 | 2 / 2 | 2 / 2 |
| midrange | 7 | 6 / 5 | 1 / 1 |
| softaggro | 5 | 3 / 1 | 2 / 2 |
| softcontrol | 7 | 7 / 4 | 0 / 0 |

The inherited split has 22 training rows/seven families and five held rows/four families. Training covers five styles; held truth covers only three. Hardcontrol and softcontrol held metrics must be null. Sources02/03 share a held family but have different styles. The three training softaggro examples belong to one family.

The saved model encoding reads own main-card IDs/counts and printed card metadata into `[27,2,207]`. It does not read deck metadata, source names/styles or own leader/base. `real_deck_data.py:85` retains name only as provenance. The 13 auxiliary targets are total count, mean/low cost, nine cost bins and initial one-card unit probability (`real_deck_data.py:27–28,84–112`). `run_local_experiments.py:135–175,254–265` passes only numeric features/targets with a fixed zero observation. `export_embeddings.py:140–154` passes the same numeric features; names/families are output provenance. This conclusion applies to the saved original-composition supplement/export pipeline, not every historical model.

## Fixed comparison plan; execution pending

`source-style-labels.plan.json` freezes primary held5→train22 top1/top3 agreement for raw, train-centered and saved alpha0.1 whitened cosine, canonical-count Jaccard and five-group printed profile, plus training-majority. It also fixes an optional closed-form alpha1 ridge readout for the same representations/baselines; train-only standardization, no neural forward, optimizer or parameter search. Full five-class confusion and support are required; primary class macro covers only three supported held classes. Plan execution requires root GO under one 20-second/512MiB/single-thread guard including preparation.

These vectors and some examples have already been inspected in prior geometry/reviews. This new weak-label comparison is exploratory. It does not validate gameplay strength or the separate synthetic IR structural proxy.

## Exact per-source mapping

Family aliases below are display-only; complete exact family IDs are in the audit JSON and alias table.

| Index | Source filename stem | Explicit style | Split | Family |
|---:|---|---|---|---|
| 00 | admiral-piett_jtl_blue | softcontrol | train | F09 |
| 01 | admiral-piett_jtl_red-splash | midrange | train | F09 |
| 02 | ahsoka-tano_ash_blue | softaggro | validation | F08 |
| 03 | ahsoka-tano_ash_yellow | hyperaggro | validation | F08 |
| 04 | aurra-sing_law_data-vault | softcontrol | train | F01 |
| 05 | aurra-sing_law_red | hardcontrol | train | F01 |
| 06 | boba-fett_jtl_blue | midrange | train | F10 |
| 07 | boba-fett_jtl_lake-country | hyperaggro | train | F10 |
| 08 | chewbacca_law_alliance-outpost | hyperaggro | train | F06 |
| 09 | darth-maul_lof_blue-force | softcontrol | train | F05 |
| 10 | darth-vader_jtl_yellow | hyperaggro | validation | F04 |
| 11 | dedra-meero_sec_colossus | hardcontrol | train | F01 |
| 12 | director-krennic_law_blue-splash | softcontrol | train | F10 |
| 13 | director-krennic_law_blue | softcontrol | train | F10 |
| 14 | ezra-bridger_ash_yellow | softaggro | validation | F03 |
| 15 | grand-admiral-thrawn_jtl_data-vault | softcontrol | train | F01 |
| 16 | grand-admiral-thrawn_jtl_yellow | softcontrol | train | F01 |
| 17 | greef-karga_ash_data-vault | softaggro | train | F01 |
| 18 | greef-karga_ash_red | softaggro | train | F01 |
| 19 | lando-calrissian_law_blue | hardcontrol | train | F10 |
| 20 | luke-skywalker_ash_data-vault | midrange | train | F01 |
| 21 | luke-skywalker_jtl_data-vault | softaggro | train | F01 |
| 22 | mother-talzin_lof_red-force | midrange | train | F11 |
| 23 | mother-talzin_lof_yellow-force | midrange | train | F11 |
| 24 | obi--wan-kenobi_lof_vergence-temple | midrange | train | F07 |
| 25 | the-armorer_ash_nabat-village | midrange | validation | F02 |
| 26 | the-mandalorian_ash_colossus | hardcontrol | train | F01 |

| Alias | Exact local family ID |
|---|---|
| F01 | `family-095df501aeed046dfc5575f88df134f078932209f8e76e697c52eefb7e3c7247` |
| F02 | `family-17b52e9fb2c042793aa6a25f5b55cc3fb9738e8c5b297e6076e0046d2783071a` |
| F03 | `family-20c7c9147cf318c51488b208519dc709897314ba35f208473f27caebb0182ac6` |
| F04 | `family-26943b376d35cf4d5455560534efddcb471c4f70d9ff4333b273af16899452d4` |
| F05 | `family-79f2f8f622f1e979d55699bdc2d7ca21f3d911fcc304b1fbb234dae39a07d792` |
| F06 | `family-910adb0c4fc425184f94f1217ce99529eb1fb9a2bb8dae23c5e99b689b382425` |
| F07 | `family-aed567b86372d62069dd6459790f1ce6db1b6c6c6bc5999b7d77122294f6ad47` |
| F08 | `family-c8a9ccb9e8fc0217801f2904d489d57e3200e13afce97d2e16bd92cf7e609b8d` |
| F09 | `family-d39d23810c835d165d9fda7709ab2a2a379675a33b32ae6f5af9e315e2d2ba6c` |
| F10 | `family-e4bd3db8e1f2aa7c5b5a31e6718246e3b184685d50df32818caf64280ceebe7b` |
| F11 | `family-ee8b387dd13d5289313eef2cbe4c3265926d2a2bb5545eaac0e5026c4b36a087` |

## Pins and audit checks

- Deck JSON: `eeada07803a6545182331247bc410628b0d0630d895a8bad8a9160d58f888b03`.
- Companion human JSON: `7495da627d8ba43cc09fd97eefbd0bff12738cef590ff229ca85040394fdaeb2`.
- Dataset manifest: `1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622`.
- Exact audit JSON: `5fe066d1827bfca2b616946ed4404647236e185a690ba0012207d3eacc9e7b50`.
- Frozen comparison plan: `4dd73f0dbcad4c18200078b127d14463d7d4d4088dc4ab044c86ae16f121a59c`.

The audit checks all 27 source-index/name/family/split joins, current versus first-import bytes, existing dataset/export hashes and label absence from NPZ field names. Full source hashes and public fixture reference URLs are in the audit JSON. No fitting, metric matrices, nearest-neighbor search, neural forward, native calls or network access were performed.
