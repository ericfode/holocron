# Restoration fixture admission

Checked **2026-10-18 00:02:39 UTC**; the rendered live suspension list was captured **2026-10-17 23:56:31 UTC**. This audit supports conservative Premier **deck-declaration construction** admission for the pinned source bank and its checked replacements. It does not certify the historical events, omitted historical sideboards, physical cards, engine execution, or strategic quality.

Machine policy: `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/restoration/admission-policy.json`, SHA256 `0e9826aa46c2932d4856c9f5087c41beb06ca60805205cb852e061b2cca18e07`.

The official [Organized Play page](https://starwarsunlimited.com/organized-play) links the [Comprehensive Event Guide dated June 26, 2026](https://cdn.starwarsunlimited.com//Comprehensive_Event_Guide_6_26_26_0110535972.pdf). Section 9.1.1, page 43, specifies one leader, one base, a main deck of at least 50 cards, a sideboard of at most 10 cards containing no leaders or bases, and at most three copies sharing a name and subtitle across main and sideboard, irrespective of printing or finish. Its listed Premier sets are **JTL, LOF, IBH, SEC, LAW, ASH**. The [Premier overview](https://starwarsunlimited.com/how-to-play?chapter=premier) supports the basic construction counts; the specific guide supplies this set policy.

The guide's statement that no cards are suspended is stale against the rendered live [Rules suspension list](https://starwarsunlimited.com/how-to-play?chapter=rules). The live list names **Cad Bane, Ashes of the Empire #11 (`ASH_011`, card id `5648009238`)** as suspended in Premier, and defines suspension as making a card illegal in the corresponding format's events. This policy applies that live suspension. The page exposed no effective date. The bank contains no `ASH_011`.

Admission requires each **raw declared printing** to belong to an allowed set and resolve uniquely in the pinned catalog; leader, base, and main/sideboard card types must be appropriate. Canonical copy counts use normalized title plus subtitle across main and the newly declared sideboard. This fixture explicitly declares an **empty sideboard**; it does not reconstruct the sources' omitted event sideboards. Replacements come only from main-deck cards already in the original 27-list bank, preserve printed cost/type/arena/aspects, leader/base, and total main size, and must pass the complete resulting declaration check. Original source family assignments and train/validation boundaries remain unchanged.

All 19 distinct source leaders, all 20 source bases, and every used main card were reviewed in the pinned metadata for explicit deck-construction restrictions. **Data Vault (`JTL_024`) increases the minimum by 10, so its admitted minimum is 60.** No other source-bank construction restriction was found. Colossus and Nabat alter setup behavior, not the minimum deck count. This finding applies to the pinned bank, not all cards. The only old declared printing is `SOR_030` in zero-based source index **3**, `ahsoka-tano_ash_yellow`; that entire origin lineage is excluded from the primary fixture. A general old-print/reprint exemption was **not verified**, so a new-set alias in `setCodes` cannot certify that raw SOR declaration. No base exemption is assumed. The target source index **2** uses **Ahsoka `ASH_009` + City in the Clouds `JTL_019`**, both admitted printings; final admission still requires the builder's full checks.

The official Rules page links [Comprehensive Rules v9.0](https://cdn.starwarsunlimited.com//SWH_Comp_Rules_v9_0_c4aa591948.pdf), but its contents were unavailable through the read-only retrieval methods used. The event guide was read through web PDF text extraction and the live suspension list through rendered browser text. Direct CDN byte retrieval was unavailable; **no official PDF/page byte hash is claimed**. The machine policy hash pins our transcription and conservative admission choices, not official website bytes. Retain these limits when describing results: “admitted under the pinned Premier declaration policy” is supported; an unrestricted claim that every historical or proposed deck is legal is not.

Pinned local evidence:

| Evidence | Pin |
| --- | --- |
| Source bank | `decks/ash-meta-2026-09.json`, 27 lists, SHA256 `eeada07803a6545182331247bc410628b0d0630d895a8bad8a9160d58f888b03` |
| Upstream source | TCG-Engine commit `a2df9722314b1233d16747f7e56186071106799c` |
| Provenance README | `decks/README.md`, SHA256 `f41f5919b2c962bc90f9bb20cc4cb95df5396fab87856678ca3af5fb2ee58f0e` |
| License | `decks/LICENSE.TCGEngine`, MIT, copyright 2025 TCG-Engine; SHA256 `da76f8adfcaf4c4e8b4b6031bbe7a833d28d9746837c7964643343f969852073` |
| Catalog repository | `/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source`, clean commit `c7ee39554901278cee70f61fd8b26fb1920696b3` |
| Catalog | `compiler/generated/cards.json`, SHA256 `0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812` |
| Catalog manifest | SHA256 `ae9f8e4ee760932302587b3dc939122a1ffaee792ddbf8f710490a7bf908068c`; compiler hash `d188828527e6459ea9c7b2673e4746960923f9d0904c190026e6d454b45a548e` |

No training, game execution, paid jobs, scraping of SWUDB/tournament APIs, deployments, or credential creation formed part of this admission audit.
