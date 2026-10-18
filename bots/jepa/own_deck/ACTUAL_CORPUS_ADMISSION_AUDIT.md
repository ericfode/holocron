# Actual-corpus admission and play-fixture audit

2026-10-18 UTC. Independent read of the original 27 declarations, pinned catalogue/report, compiler and Rust loader. No native/NN execution, build, training, engine edit or paid work. The previous action-only literal fixture is held. Kessel remains `c7ee39554901278cee70f61fd8b26fb1920696b3`.

## What the admission count means

The alias-aware join independently reproduces **115 canonical main-card identities / 635 copies** among **251 identities / 1,432 copies** in the actual 27 lists. Of those admitted identities, 91 are `sourceIr` (495 copies), 24 `dataOnly` (140 copies); 92 are units, 15 events and eight upgrades. No native adapter is itself a main card. Printed aliases must resolve through `setCodes`/`setId`; for example declared `JTL_136` resolves to catalogue `LAW_175`, identity `8746311599`. Do not join a numeric source ID directly to a printed code or count reprints twice.

The generated report is produced by the actual Rust catalogue loader, rather than by matching a primitive name. [Catalogue loading](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/ability_ir.rs:2819>) rejects compiler-unsupported entries, validates complete source/registration envelopes and compiles **every** leader/unit/card-side ability into temporary storage. It installs the card only after all succeed ([atomic installation](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/ability_ir.rs:3093>)); a retained inspectable partial IR does not become a playable partial card. The [engine loader](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/generic_runtime.rs:395>) then applies runtime card-type, keyword, token, trigger and dependency gates, rejecting whole definitions. The [report command](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/main.rs:121>) labels its evidence **`gameConformance: "not assessed by this report"`**. Admission is therefore a whole-definition executable-envelope claim for this pinned engine, not proof of all card/state interactions or fresh engine-oracle agreement.

Subset loading still requires the exact dependency closure. Missing reviewed token definitions can remove dependent cards ([dependency rejection](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/generic_runtime.rs:634>)); this loader also requires a native Shield definition at construction. Retain full immutable rows, verify every requested selected card actually enters the loaded engine, and preserve explicit rejection reasons. Never strip an inconvenient ability or mark unsupported rows supported. Whole-card admission, reachable fixture construction and observed outcome coverage remain separate facts.

`dataOnly` does not mean effectless. The [compiler fallback](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/build.js:144>) admits plain bases, fully parsed keyword-only units and plain stat-only upgrades. Its [keyword parser](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/keywords.js:7>) checks the whole printed text. Runtime intrinsic keywords come from `keywordValues`, while metadata keyword names can also mention grants. Of the 115 actual identities, 25 have no declared IR abilities, but 16 still have intrinsic keywords. Even the nine with neither are not all vanilla: `LOF_151` (`6885149318`) has zero abilities but an attachment predicate **Jedi AND non-Vehicle**, plus printed upgrade bonuses **+3/+2**.

The admitted actual corpus has **97 ability registrations**, and **zero `action` registrations**:

| Trigger | Registrations |
| --- | ---: |
| whenPlayed | 24 |
| constant | 21 |
| onAttack | 19 |
| event | 15 |
| whenDefeated | 14 |
| onDefense | 2 |
| whenAttackEnds | 1 |
| eventHooks | 1 |

Thus the saved action-program vectors cover **zero actual main-list identities/copies**. They cannot be relabeled as these cards' whole semantics. A new whole-card frontend must include public printed/type/aspect/unique/arena/upgrade metadata, intrinsic keyword values, all ordered side/trigger registrations and continuations, and root `attachCondition`/`piloting` contracts where present. Dictionary keys may canonicalize; effect/list/operand order and literal roles must remain intact. Missing fields, unavailable capabilities and event HP/power nulls need explicit known masks, not fabricated semantic zeros.

## Small actual-card play subset

The proposed eight cards occur in the real corpus and account for **65 copies**, not all 635 admitted copies. Held IDs are `LOF_155` and `JTL_217`; final source/context protocol is still separate from this inventory.

| Card / numeric identity | Copies / lists | Complete emitted behavior relevant to a play fixture |
| --- | ---: | --- |
| ASH_048 / 3962920521 | 19 / 8 | Empty abilities; intrinsic **Shielded + Sentinel**; actual entry must create Shield, and Sentinel needs a separate target-legality observation if claimed. |
| JTL_095 / 7653629848 | 9 / 3 | Plain space Fighter, cost 2, power 3, HP 2; valid effectless entry control. |
| SEC_163 / 6387581059 | 13 / 6 | Optional When Played: defeat any upgrade. |
| LOF_155 / 1093502388 | 3 / 1 | Optional When Played: defeat a **non-unique** upgrade. |
| LOF_077 / 4218264341 | 9 / 3 | Event: defeat a nonleader unit whose **printed cost ≤2**. |
| JTL_078 / 5093056978 | 6 / 3 | Event: defeat a nonleader **Vehicle** unit. |
| JTL_158 / 4159101997 | 3 / 1 | When Played: **self damage 1** if no **other friendly Fighter**. Its display title says “Defeat this unit”; that title is not the executable effect or a label. |
| JTL_217 / 1303370295 | 3 / 1 | Optional When Played: exhaust a unit if another friendly space unit exists; the entering source is excluded. |

The exact typed sources are the pinned `cards.json` rows; their `sourcePath`/`sourceHash` are retained in the coverage artifact. Relevant TypeScript paths are `game/cards/06_SEC/units/OuterRimConstable.ts`, `game/cards/05_LOF/units/DRK-1ProbeDroid.ts`, `game/cards/05_LOF/events/CrushingBlow.ts`, and `game/cards/04_JTL/{events/DirectHit,units/CrackshotVWing,units/DeathSpaceSkirmisher}.ts`. Original TypeScript files were not present in the inspected task-5/src-Kessel paths; this review does not claim a new original-source/oracle conformance check.

The subset can distinguish useful native endpoints without changing coverage: unique versus non-unique attached upgrades (`ASH_114` and `ASH_228` are actual admitted examples); Vehicle/non-Vehicle and printed-cost-2/3 unit targets; and absent/friendly/opposing/other-space or Fighter context. Declare which endpoints the four frozen state families actually support. A helper's mere presence does not qualify its own full behavior. If a predicate lacks a discriminating candidate, report that predicate as untested rather than infer success from a legal common target.

## Native-play and information boundaries

Use the ordinary offered **hand-card play**. [Availability](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/simulator.rs:430>) checks resource readiness plus event/upgrade feasibility; [effective play cost](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/simulator.rs:369>) includes aspect penalties, not merely printed cost. Public leader/base aspects and resources must be available to a model predicting cost; labels are measured resource changes.

**Do not inherit the old activated-action cancellation invariant.** [Ordinary units](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/simulator.rs:682>) pay, leave hand and enter an arena before their When Played window; declining an optional defeat still leaves the paid unit in play. Events begin their program through a different targeting/payment path. Clone the untouched **preplay** state for every branch and retain intermediate payment/entry/optional/target witnesses. A cancellation/decline is a native branch, not an undo operation unless the actual snapshot proves it. [Entry processing](</Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/crates/kessel/src/simulator.rs:966>) handles entry/deaths before dispatching queued Shielded/When Played registrations, so direct arena placement cannot witness play effects.

Source zone/hand-count/cost/entry/public-stat outcomes can be known after an actual settled no-target or declined-trigger unit play. Target-specific effects require the actual offered target action and settled public snapshots. Pending continuations, trigger/death windows and discarded targets' unavailable counters retain unknown masks; record defeat/zone separately. No final-state claim may rely on a latched winner alone while mandatory continuations remain. The selected eight do not themselves require draw/search; avoid introducing hidden-order outcomes merely to broaden this pilot.

Condition source **after-play** outcomes on the public intended target as well as the card/context: an event can return to hand unpaid when that target is rejected and the native selection is cancelled. The frozen intent is an index into the preplay public candidate bank, never the resulting legal offer, selected-after-state or target mask. Root approved the shared 80-input source-head fusion `(program, globals, intended candidate, program×globals, program×candidate)` across all four arms; global source-play availability remains a distinct reported head, with its extra candidate input disclosed. Exact declared-index validation is required before fitting.

Model inputs need an explicit observation whitelist: own known hand/source, public board/candidate printed cost/unique/traits/stats/attachments, resources/aspects and current public context. Do not feed complete native snapshots, legal opponent-hand plays, opponent private cards or either hidden draw order. Public offered target membership and native after-state deltas are **labels**, never pre-action features. Play from hand updates hand/in-play zones; it does not deplete the draw pile. Original declaration provenance stays fixed, and a remaining-pile belief must not silently subtract a card twice.

## Coverage and qualification gates

Keep every one of the 1,432 actual declared copies in downstream deck records. Distinguish corpus occurrence, runtime admission, complete frontend serialization, native focus/endpoint observation, learned-vector availability and held-card validation. Current native-qualified and learned whole-card flags remain false. Native observations on eight focus cards cannot qualify all 115; admitting inputs for the rest is a distinct unvalidated extrapolation. A masked partial deck vector must retain unrepresented-copy counts/coverage, rather than averaging only the convenient supported cards and calling it the whole deck.

Use the same whole frontend, shapes, heads, initialization and compute for learned, untrained-semantic and ID controls. Hold `LOF_155`/`JTL_217` out by canonical identity and all aliases; keep each preplay root and its optional/target branches together, and hold context families globally where promised. Report new/constant categorical atoms, numeric ranges and exact local-input replays. The first held card shares defeat-upgrade behavior with `SEC_163` but adds uniqueness binding; the second combines an exhaust effect with an other-space condition. These two IDs and a few synthetic worlds can diagnose a bridge, not validate the card population. Preserve per-head negative results and simple metadata/context priors; count/curve-only downstream labels cannot establish a benefit from effect semantics or synergy.

## Pinned evidence and review status

- Initial coverage artifact: `experiments/actual-corpus/coverage-v1/actual-corpus-coverage.json`, SHA256 `3e8d996dc342bab07ea325872a89c627221938bda85f8442cba4a6699b2397f4`. The independent raw-declaration join agrees. It preserves unknown flags but omits root attachment/piloting fields; retain this original evidence.
- Complete-row revision: `experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json`, SHA256 `dd3ec9dc77f1f888d070f7e8ed0ab20290c347c75c75f6fe01f5504ce43f0480`. Independently checked all 115 `whole_catalog_row` objects equal their pinned catalogue rows and all 115 canonical row hashes match. This repairs the attachment/piloting serialization source without changing admission or claiming measured capabilities. Owner reports nine data-only tests passing; this reviewer did not run them.
- Catalogue `compiler/generated/cards.json`: `0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`; saved runtime admission: `91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957`.
- Saved declaration export: `7917ee4d76e86ac1fd3f3d63e546adc07d15da05bb866e14eaccd632b81e5301`; actual raw list: `decks/ash-meta-2026-09.json`. Original 22/5 family split remains pinned by `real-decks.manifest.json` `1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622`.

**Admission audit complete.** Whole emitted definitions are admitted atomically; actual whole-card consequences and new frontend completeness remain to be qualified. New play collector/plan/converter source review is pending. No experiment is launched by this document.
