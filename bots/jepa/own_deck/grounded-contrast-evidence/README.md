# Portable grounded-contrast evidence

This directory preserves the completed twelve-program native-fixture contrast.
`index.json` resolves each portable file to its historical source path and records
the source, uncompressed, and stored SHA-256 digests. Large JSON artifacts use
deterministic gzip (`mtime=0`, empty filename); decompression reproduces the exact
original bytes. Absolute paths inside receipts remain historical provenance.

The package includes both collection attempts, their logs and one shared campaign
ledger, the native receipt and complete apply journal, the dense dataset and full
lineage manifest, frozen inventory and collection contract, admission audit,
previews and commands, all four final checkpoints with contracts/goldens/predictions
and schedules, every actual optimizer-step record, and the three grounded run IDs'
event stream. The small earlier no-update diagnostic is preserved separately.
The package now has 65 indexed payloads plus `index.json` (three gzip files); byte
totals are recorded in `index.json`. `embeddings/` contains twelve actual saved
16-dimensional selected-program vectors, their manifest/schema/export receipt,
and the previous embedding index. They were copied from the saved correct-IR
ABI golden output with zero extra forward passes. They are static program
vectors before board-context fusion; `semantic_validated` remains false.

The fit command's `prepared-not-launched` field is an unchanged preflight snapshot;
the completed guard receipt, progress journal and result record actual execution.

Collection used 932 native applies over 168 roots and 1,344 candidate queries;
413 target branches settled. Training completed 2,400 updates (600 per arm).
The ledger retains the initial zero-call build failure and all elapsed charges:
39.715139750042 active seconds. Guard receipts sum to 39.715672084014 seconds;
the original small timing difference remains preserved. The standalone research
checkpoints are not production actor weights or a deployed WASM supplement.

Collection source: `aa2526b84c5705dcbf12a7d043df29d57d41c2f2`.
Initial failed build source: `79f3aa68ab33faa8fd24d930559447650139df21`.
Fit source: `fb8853c8a52d0ceed4d7c4221fbef008ccd2e747`.
Kessel source: `c7ee39554901278cee70f61fd8b26fb1920696b3`.
`frozen-source/` preserves the exact plan and execution-input hash manifest;
the original protected checkpoints and full catalogue are excluded.

Read `ACTUAL_NATIVE_SUPPORT.md` for observed support and limitations and
`fit-1/result.json` for matched-control results. Only two program identities and
four world-state families are held out; candidate branches within a root are
correlated. Constant or unobserved heads do not establish nontrivial semantics.
No policy, deck strength, strategic synergy, or semantic-neighbor claim follows
from packaging these artifacts. Masked, unavailable and no-target paths remain
in the raw native evidence.

Kessel is Eric Fode's MIT-licensed rules simulator; retained Forceteki/Ringteki
notices credit Stuart Walsh and Addison Mayberry. TCG-Engine's existing deck-data
notice is retained for continuity with the earlier pilot. Exact license texts
are in `licenses/`. STAR WARS: Unlimited card names and rules are used as research
fixtures; this package does not distribute card artwork or claim those rights.

Verification needs only Python's standard library: for each index entry, hash
the stored bytes; gzip-decompress when `encoding` starts with `gzip`; compare
the resulting size and hash to `uncompressed_bytes` and `uncompressed_sha256`.
For an identity byte-copy, all three recorded digests must match. The index
itself is excluded from its own file list to avoid a circular self-hash.
