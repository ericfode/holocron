# Real-IR adapter and transfer evidence

Read [adapter coverage](REAL_IR_ADAPTER_RESULTS.md) and
[transfer results](REAL_IR_TRANSFER_RESULTS.md). Whole-row serialization covers
152/1,178 pinned runtime definitions and 47/1,432 actual27 main-card copies.
The seven-event native/reference gate passed; every learned usability gate failed.
No general card/deck representation or production change is qualified.

The [packet manifest](real-ir-transfer-evidence/manifest.json) is SHA256
`1e34895e3011c955c2d539587b8b71baef7fd99ca227e0a7b5d2fd4582f508a4`:
124 files, 36,503,522 raw bytes and 3,743,930 stored bytes. It preserves the
unstarted coverage V1, failed V2 with its full ten-second charge, completed V3,
and completed transfer V1, plus frozen sources, tests, reports and review receipts.
Gzip members have fixed timestamp zero; NPZ files are opaque bytes to packaging.
Limits are 64 MiB/file, 256 MiB total, 1,000 files and 4 MiB manifest.

Verify without opening original provenance paths or running models/arrays/engine:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bots/jepa/own_deck/real_ir_transfer_package.py \
  --verify --out bots/jepa/own_deck/real-ir-transfer-evidence \
  --expected-manifest-sha 1e34895e3011c955c2d539587b8b71baef7fd99ca227e0a7b5d2fd4582f508a4
```

This verifies byte integrity, inventory and closed accounting, not learned-weight
forward parity or an independent second semantic implementation. Prior history
is an explicit dependency on the adjacent
[earlier manifest](compositional-actual-admission-evidence/manifest.json), SHA256
`0131a7169b9b4b789077b3f7348c3f968d9557cad2f75d3ece200a65269892f1`;
it is never recursively fetched or copied. The compiled collector is excluded
with its exact byte pin retained. Rebuilding requires the pinned Kessel source
and toolchain recorded in the campaign, which are not vendored here.

Coverage source freeze is `c44be0871cad71e5026e75e7a5f2fcac4f5b5733`;
transfer source freeze is `b663fe8b282b43f35f41d147f27472bd604b2c96`.
Packet assembly source is `1dbed03eec98b4b35750bb8654ec26566b3b3476`.
All earlier source commits remain in ancestry. Packaging performed zero scientific
calls. Independent byte/lineage review and local validation receipts are included;
the latter truthfully records missing local JavaScript dependencies. Repository CI
performs its normal setup and validates the final PR head separately.
