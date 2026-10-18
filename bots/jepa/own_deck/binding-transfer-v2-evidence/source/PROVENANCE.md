# Own-deck implementation and recovered research provenance

This branch starts from the existing WASM parity work at
`f9cbbd427689081d5f12829b1fe7edd76ca51fab` on `codex/jepa-wasm-parity`.
Its isolated workspace is
`/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context`.
The original task4/task5 workspaces were inspected read-only. No recovered
research commit is cherry-picked into this stacked change.

## Recoverable research

The reported broken chat is `01a14bb1-57ca-77b9-9c5a-8b25e27be01f`.
Its complete transcript was not found by filename or content search in local
`~/.codex/sessions` and `~/.codex/memories`. This does not establish whether the
service retains that chat. The saved repository work is available at:

```text
/Users/ericfode/Documents/Codex/2026-10-17/task-5/holocron
branch: codex/jepa-continuation-research
base:   f00df42e67dbb63c686c7cadb3d1af0be09b4e06
head:   c39e1534664d6c055c844722f7251ee6cdf6c3ac
```

The tracked tree and index were clean during the recovery audit. These six
commits preserve the research, including model/optimizer checkpoints and run
receipts. Report paths below are relative to that original workspace; committed
versions can also be read with `git show <commit>:<path>`.

A separate recovery archive preserves the committed research directory plus
the four untracked report snapshots:

```text
/Users/ericfode/Documents/Codex/2026-10-17/task-7/recovered-research-c39e153
manifest: MANIFEST.json
manifest SHA-256: c36ebc44fc6858871c96a7db67d9153906228bc8861f59b3a0e736af599fd47e
274 files; 36,706,364 bytes (excluding the manifest)
```

An independent read-only pass checked all 274 archived file lengths and hashes
against that manifest without errors. The archive stays outside this repository
and the stacked PR. It preserves bytes, not a claim that historical runs were
rerun or every old scientific conclusion remains current.

| Commit | Saved work | Main report |
| --- | --- | --- |
| `a441528f48444ca82194aa06eb4f21d41b6095ab` | Paired continuation harness and Rust terminal pilot | `bots/jepa/research/kessel-pilot.md` |
| `e929c89f2edd9772be625379d55b61d9f549de4d` | Native bridge and paired target collection | `bots/jepa/research/bridge-report.md` |
| `8e050c4924655bd69d6387f62003e1dde15dd003` | Continuation policy audit and stratified diagnostic | `bots/jepa/research/stratified-report.md` |
| `f898461879fe668d86906b069807eb34712e49d1` | Terminal/objective/optimizer prerequisites and validation reservation | `bots/jepa/research/prerequisites-report.md` |
| `00886e4324f8f3b057adec25a0d93be8d7a142eb` | Bounded pilot and missing recruitment explanation | `bots/jepa/research/next-pilot-report.md` |
| `c39e1534664d6c055c844722f7251ee6cdf6c3ac` | Real-data integration, saved checkpoints, native wiring and hybrid binding | `bots/jepa/research/integration-report.md` |

At recovered HEAD, the six report SHA-256 values in table order are:

```text
4f763b34647f10c0c89a161e9ffa4606b5cfddd4325ccc37c9668f1b76a2f702
015c194609c1279fe8df90156e434d9c15db63b002a5fa91bf6cce1ebe660102
3d8e03b737a945d8339285cb6022627dcc637940f918edff32535b719663ed98
1894c3d5f4bf137f480a833c392f34bad0692fcb1c4ffa56225daa243cfbbaf4
5ff6c03808904c1e7ae120689f8fcae379b39a09c21d73df9167ef53847557d3
0b9a4008272ed6ed221a75c77496ff18afe7f11cbb4a871bca8ddc17dec07065
```

Additional recovered HEAD references:

| Path under original workspace | SHA-256 |
| --- | --- |
| `bots/jepa/research/README.md` | `b0b5b718c6bb1baf6d2c2a2b9afca0726f210f2b0549e28c712c5243d56dba24` |
| `bots/jepa/research/continuation-manifest.json` | `5a72389709bdfc29e89b4b5dfcb2ee5a53f903f7963713efc2867f745245d8a3` |
| `bots/jepa/research/hybrid-kessel-probe-report.md` | `5a91bc890a0a51398b816889e0644ee173cd5f7879fa7b0a91d5dd47f57c6daa` |

Four newer files were untracked. Their independent snapshots must remain outside
this PR; they are not covered by the commit IDs above:

| Path under original workspace | Bytes | SHA-256 |
| --- | ---: | --- |
| `bots/jepa/research/opponent-eval-environment.md` | 12050 | `271f53ac958ed40ba025cbe0ec35ec473649e756ca29ee962bc1890c9af9b98f` |
| `bots/jepa/research/opponent-eval-environment.json` | 17106 | `cffa3e118cd9c643fe1af0ba058a2d7d7842437745116f2cf8e7711e7fb1a455` |
| `bots/jepa/research/rated-loss-inventory.md` | 5798 | `b349bc95cd01ffa95680f1ef6eaec147823d9c36f687e4a923c291cdeb70ebed` |
| `bots/jepa/research/rated-loss-inventory.json` | 12339 | `84872652ce9f51e1af4438d43f61b03b3dd268cfed73acfe3a2b5f212b9af0c6` |

## Evidence boundaries carried forward

- Stratified targets differ on 20/96 enriched pairs and 0/32 natural pairs;
  those differences reduce to five distinct root cases. The best retained root
  is unchanged. See `stratified-report.md:3`.
- The next pilot contributes 64 validation rows and zero new training rows.
  See `next-pilot-report.md:3`.
- Sixty-four real-data updates and twelve native wiring games completed, but
  A/B strength is inconclusive; every selected head is worse than frozen `zb`
  on the common validation objective. See `integration-report.md:3,27`.
- The fit's outer supervisor failed with `PermissionError`. Saved worker
  completion is independently audited; outer deadline and tree-RSS enforcement
  remain unverified. See `integration-report.md:63`.
- The unchanged competitive hybrid completed one Kessel-only operational game,
  with 104 actual and 390 simulated actions. That inspected fixture supplies no
  untouched strength holdout. See `hybrid-kessel-probe-report.md:3`.
- The untracked loss inventory predates the seven-loss export at
  `/Users/ericfode/Documents/Codex/2026-10-17/task-2/jepa-loss-export-20261017`.
  Its earlier missing-replay finding is historical. These seven seen losses
  remain diagnostics, not validation or test holdouts.

No old training result establishes the benefit of own-deck context. The legacy
deck-edit research in chat `01a12ebd-eaf3-7570-a0d2-fde1efdfc203` is a different
task and was not substituted for this recovered continuation research.

## Owner checkpoint and restart handoff

After the Mac restart on 2026-10-18, the parent relayed the old research owner's
checkpoint: HEAD remains `c39e1534664d6c055c844722f7251ee6cdf6c3ac`, tracked
files are clean, the same four untracked reports are preserved, and its work
has stopped with no surviving task-owned experiment processes. It confirms
64 continuation updates, 12 Kessel integration games, 175 historical tests,
worse held-out fit loss than the frozen baseline, and the historical supervisor
failure. These are owner-reported historical counts, not reruns here.

The independent task7 audit checked the saved commit/report/archive pins and
the newer seven-loss export; the old owner had not inspected that export.
There is no remaining overlap blocker. Current task7 fit receipts and the
append-only feed show all 300 composition and 400 frozen-probe head updates
completed before the restart. They were checked from saved artifacts and were
not restarted. No paid job or deployment had been launched by this batch.

The old owner subsequently resumed a separate file-only loss audit and saved
commit `0c6b5cc5a88cd6d8ea47ec885cb495dcb690dee5` in task5. Its
`bots/jepa/research/resumed-research-report.md` records 934 decisions across
seven losses, without bank exhaustion, and a public sequence where readying an
enemy Cinta enables its immediate lethal reply. A saving alternative is not
established. The pinned strict bridge cannot reproduce those full games.
That authorized later task5 commit explains why its HEAD now differs from the
earlier preserved snapshot; task7 did not edit that workspace. The original
four untracked reports and frozen checkpoints remain preserved. This newer
audit adds no training or games and does not overlap the task7 experiments.
