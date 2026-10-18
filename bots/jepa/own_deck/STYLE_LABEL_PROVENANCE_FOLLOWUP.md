# Style label provenance follow-up

All27 imported `metadata.style` values are now verified against the original `# Style:` comments at upstream commit `a2df9722314b1233d16747f7e56186071106799c`. Every value matches exactly, including lowercase wording: softcontrol7, midrange7, softaggro5, hyperaggro4, hardcontrol4. The [27-row evidence](style-label-provenance-followup.fixtures.json) records each deck stem, exact comment, line number and pinned public URL; it retains no other fixture comments.

The upstream documentation describes owner-labelled fixtures and says Style chooses the heuristic profile/later RL base profile. These are documented fixture annotations, rather than strategic-style fields established in a public deck database. Filenames are not a style inference rule. [Pinned upstream README](https://raw.githubusercontent.com/TCG-Engine/TCGEngine/a2df9722314b1233d16747f7e56186071106799c/SWUSim/Tests/BotFixtures/ash-meta-2026-09/README.md), lines1–15,22–27,34–48.

The distinction from automated inference is explicit. `BotArchetypes.php` prioritizes hand labels and supplies a separate composition fallback for unlabelled decks. `BotDeckStyle.php` documents fitting shape weights/cuts **to owner-labelled decks**, including later owner relabels of Boba Lake Country and Ezra Yellow. Its runtime first transfers a registry label when card overlap reaches75%, otherwise uses shape inference. Those paths do not show that a composition heuristic generated the27 fixture annotations. [BotArchetypes.php](https://raw.githubusercontent.com/TCG-Engine/TCGEngine/a2df9722314b1233d16747f7e56186071106799c/SWUSim/Custom/BotArchetypes.php), lines180–202; [BotDeckStyle.php](https://raw.githubusercontent.com/TCG-Engine/TCGEngine/a2df9722314b1233d16747f7e56186071106799c/SWUSim/Custom/BotDeckStyle.php), lines186–211,322–369.

The sweep script consumes the fixture comment directly when choosing a heuristic profile. This establishes the direction of the observed import/consumer path: explicit header → profile selection; our importer retains that same header value. [sweep_fixtures.sh](https://raw.githubusercontent.com/TCG-Engine/TCGEngine/a2df9722314b1233d16747f7e56186071106799c/SWUSim/DevTools/rl/sweep_fixtures.sh), lines85–86,98.

Some upstream README summaries disagree with its current fixture headers:

| Deck stem | README summary | Verified header/import |
|---|---|---|
| ahsoka-tano_ash_yellow | softaggro | hyperaggro |
| boba-fett_jtl_lake-country | softaggro | hyperaggro |
| darth-maul_lof_blue-force | midrange | softcontrol |
| lando-calrissian_law_blue | softcontrol | hardcontrol |
| ezra-bridger_ash_yellow | introductory prose: hyper aggro | softaggro |

These documentation discrepancies do not require relabelling our data: all27 actual headers agree with the imported JSON. The per-file links are in the fixture evidence; the header, rather than the summary table/prose, is the directly verified field.

The [official commit page](https://github.com/TCG-Engine/TCGEngine/commit/a2df9722314b1233d16747f7e56186071106799c) was accessible. GitHub blame/history API paths were inaccessible through the tools, and the specification path linked by the README returned404 at this commit. Therefore exact per-label edit authorship/history remains unresolved. The public code describes owner judgements, but it does not establish annotator identity/qualifications, a blinded annotation protocol, confidence or agreement. Whether every Style token was manually typed or mapped from an owner-provided archetype term is also unresolved. Retrieval status and source locations are preserved in [source evidence](style-label-provenance-followup.sources.json).

These remain **weak labels**, not behavioral, synergy or strength truth. The completed style probe measures agreement with this particular annotation set. This follow-up resolves the earlier inability to inspect original headers; it preserves the old audit/proposal/probe bytes as historical evidence and performs no new model, metric, native or training computation. Only new follow-up files were written. No player names, event placements or decklist links were retained.
