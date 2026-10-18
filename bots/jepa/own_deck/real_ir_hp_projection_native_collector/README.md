# Versioned public-state projection collector

This is a source copy of the closed PR45 real-event collector. The only Rust
behavioral difference validates ground/space/base damage1/2/4 instead of3/5/5;
healthy own-ground/own-base exceptions remain0. The binary and crate entrypoint
have a unique new name. The supervisor changes only `BINARY`; `HERE` resolves to
this new directory. A pure source-diff test proves those narrow differences.

All original Kessel1178 definitions, schemas, helpers, natural HP8/10/30,
56 roots,168-call ceiling,3-call root ceiling, source preservation, private-pile
restrictions, full pre-apply fixture validation and durable journal remain
unchanged. No old file, source pin, checkpoint, ledger or outcome is changed.

All seven programs are previously exposed DEVELOPMENTAL sources. This plan
changes public-state composition only; the four fresh whenPlayed sources
ASH_259/LOF_259/SOR_132/HMW_158 remain unselected. Importing the producer or
supervisor executes no engine, build, model, fit or actual plan construction.

The parent must separately freeze and authorize a new bounded allocation before
building or running this binary. No actual native outcome is implied by the
synthetic metadata and primitive journal tests.
