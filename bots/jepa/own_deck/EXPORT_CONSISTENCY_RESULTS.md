# Research publication consistency

The current publication is an immutable index/handoff pair, selected through one atomically replaced pointer. The historical `grounded-contrast-handoff.json` remains historical; its hash checks were not weakened and it was not relabeled as current. No dashboard repository was changed.

## Current checkpoint

Workspace-relative paths below are rooted at `/Users/ericfode/Documents/Codex/2026-10-17/task-7`.

| Artifact | Path | SHA-256 |
|---|---|---|
| Stable pointer | `experiments/publication-current.json` | `6deeca07ad4e5e4cbc23189c54b21e2064723f25952e5f22761e1e92ecd7adb5` |
| Immutable manifest | `experiments/publication-checkpoints/6c0c150998f6-fa99f01a41f1-9df4d86d29a9/manifest.json` | `daf15bdfa1b942fe085bd65a562eb3c152e900ac94afe3740bdf632501b60e30` |
| Immutable index | same directory, `research-index.json` | `fa99f01a41f1dfb8cb26952bcbf7c9a609ca8a29d33b21672d98c3f11144f496` |
| Immutable handoff | same directory, `handoff.json` | `2c9a5855a9d5d2bb455290c0a4c5a13bd870a649f0c791e25a0f93d36ef99040` |

The helper verifies every pinned byte/hash, checked head `6c0c150998f6c9436e45bd61f5d3a171343d29d1`, merge `b60daf88c18250a36ae06825c4037010dd3816ff`, identical checked/merged tree `4247a184a253dc4e27f785db047f3b72563d371c`, and successful CI run `39088042211`. It publishes the immutable directory before replacing the sole pointer. The core pair still references local evidence; use the portable closure for hosting.

## Portable closure

`experiments/sites-publication/6c0c150998f6-fa99f01a41f1-9df4d86d29a9-v1/manifest.json`, SHA `4e11ad9d332f491f5c2dd47aa7bcaf774aab3cc1a785091aa17b16ddf2b9bcf8`, resolves 33 scientific entries and six vector spaces using relative URLs with exact hashes and byte counts. It contains 978 checksum-listed payloads; an independent root verification checked 289 JSON data URLs. Host paths and historical/source attestations are explicit non-fetchable provenance. Compressed raw receipts remain exact downloadable evidence.

The sibling deterministic ZIP is 45,978,716 bytes, SHA `6bb2f4d3285ebab4f4e814dae68616fe9659308a459c9b144a21fcd01dd93282`. All six vector exports retain their original numerical values. The preservation receipt verifies 338 raw-evidence references byte-for-byte across the five evidence indexes; duplicates may reference the same stored file. Earlier failed packaging attempts remain recorded rather than being hidden.

Receipts: `experiments/sites-publication-delivery.json` (SHA `12fa0781a1b0201617afb0cb3b7f0e552c78c873cbc40cdd8ed0fc1c41607470`), and `experiments/sites-publication-preservation-verification.json` (SHA `9253099666ee3f7f9c6340b4ef2662bdac4eb37041545055cb8300574ac5772b`).

Validation: 12 focused filesystem tests passed. The root separately reran them and `publication_portable.verify_bundle`. Packaging used no neural forward, native action, optimizer update, paid job, or deployment. It introduces no new scientific result or semantic-validation claim.
