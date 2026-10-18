# HP projection evidence

The [compact result](REAL_IR_HP_PROJECTION_RESULTS.md) retains every failed seed.
HP projection fixes the observed sign error but fails every primary accuracy gate.
It does not qualify a whole-card or deck embedding.

[Packet manifest](real-ir-hp-projection-evidence/manifest.json):
`dc4d89a220722120b3aae51801fdf9521fa971e175f5c1985a81f10544b6b3c0`.
91 files; 20,163,151 raw bytes / 1,618,376 stored bytes. Fixed bounds are
64 MiB/file, 256 MiB total, 1,000 files and 4 MiB manifest; gzip timestamp is zero.
The compiled collector is excluded with its byte pin retained. NPZs stay opaque.

Verify without loading arrays or running models:

    PYTHONDONTWRITEBYTECODE=1 python3 bots/jepa/own_deck/real_ir_hp_projection_package.py --verify --out bots/jepa/own_deck/real-ir-hp-projection-evidence --expected-manifest-sha dc4d89a220722120b3aae51801fdf9521fa971e175f5c1985a81f10544b6b3c0

Offline verification checks bytes, inventory and closed accounting, rather than
checkpoint forward parity. The explicit opaque dependency is
the [PR45 manifest](real-ir-transfer-evidence/manifest.json), SHA `1e34895e…`.
Diagnosis froze `cb269b0fdeaca42c305d4c2897401deff6fc9971`; the matched experiment
froze `38532e7a1dafbeb55c7b738778a34e295a80e48c`. Four fresh `whenPlayed` sources
remain reserved. Adapter coverage remains 152 runtime rows / 47 corpus copies;
each native collection's 375 comparisons / 112 calls is a separate denominator.
