# Holocron

Bots and research for the SWU Arena: every bot, the position evaluators and learning code, deck building, the game
analysis and Strategy Atlas model, the Lean theory, and the bot that plays people on karabast.net.

Holocron uses the arena as its playground. The arena (`ericfode/swu_bot`, private) plays every rated game: Holocron
sends it bots and evaluators, and reads ratings, games and analytics back through the arena's export API. Holocron
never sends the arena game results. Kessel (`ericfode/kessel`), the Rust rules simulator, is its own repo; look-ahead
bots bring it as their simulator.

The files came from `swu_bot` with their history and were then sorted into `bots/`, `engine/`, `lab/`, `decks/` and
`karabast/` (`git log --follow` works across both moves).

## Setup

Node 22, Python 3, and a Rust toolchain for the Rust bots.

```bash
git clone --recursive https://github.com/ericfode/holocron && cd holocron
cd forceteki && npm ci --ignore-scripts && npm run get-cards && npm run build && cd ..
npm ci
npm test                         # bot logic on mock boards, evaluators, deck building, the Karabast seat, the importer
node engine/random-run.js 3 1    # the engine works: seeds 1-3 give 594/342/486 steps, p2 wins each
```

`forceteki/` is a submodule of `ericfode/forceteki` at the commit the arena pins (`2ebed8ca2`). Never change files
inside it; workarounds for engine bugs go in `engine/` or `bots/`.

## Layout

| Path | What it is |
| --- | --- |
| `bots/` | every bot, each with its README; `bots/README.md` lists them and `bots/external-bots.json` names every bot program |
| `bots/players/`, `bots/examples/` | the in-process bots (random, rush, heuristic and its profiles, ISMCTS, omniscient) and the example protocol clients; `players/index.js` is the name registry |
| `bots/c`, `rust`, `python`, `lisp`, `clojure`, `haskell`, `bend`, `wasm`, `jev`, `jepa`, `learned`, `rust-learned`, `rust-omni`, `omni` | bots in other languages and the research bots |
| `bots/starters/` | the starter bots the arena hands to new builders |
| `engine/` | the arena's game player (`env.js`, `view.js`, `protocol.js`, `match.js`, `game-cards.js`, `game-pool.js`, `stdio.js`, `rng.js`, `recorder.js`, `decklists.js`, `cardpool.js`, `ratings.js`, `random-run.js`, `debug-seed.js`), copied from `swu_bot` at `7455601` so games can be played here, with the arena's card data in hello from `swu_bot` `1d819e2` (`game-cards.js`, `match.js`, `protocol.js`); replaced by the arena's published player when it has one. Holocron's own checks of it: `protocol-test.js` (protocol conformance), `rollback-test.js`, `determinism-check.js [seed] [bot]` |
| `decks/` | real tournament deck lists (with the game player) |
| `lab/runners/` | `ladder.js`, `ladder-worker.js`, `ladder-report.js`, `sweep.js`, ...: local round robins and gauntlets, parameter sweeps, measurement scripts |
| `lab/eval/`, `lab/learn/`, `lab/info/` | position evaluators (win predictors), self-play learning, the knowledge dial |
| `lab/deckbuild/` | deck building and drafting (deck JEPA) |
| `lab/analysis/` | game analysis, the real-deck bot test (`npm run realdeck:test -- --bot <bot>`), SWU Stats |
| `lab/meta/`, `lab/dashboard/` | the Strategy Atlas model and page builder, the research dashboard's shared code |
| `lab/theory/` | Lean proofs about the game and the measurements that check them |
| `lab/models/` | trained model files the bots load |
| `lab/tools/` | card-data stand-in (`synth-cards.js`), search profiling (`search-profile/`), benchmarks (`omni-search-bench.js`), and a local copy of the arena's open-table games (`pull-open-tables.js`) |
| `lab/kessel-reference/` | the engine side of Kessel's reference corpus: named scenarios, the generator, the probe fixtures and the card pipeline runner (`npm run kessel:reference`, `npm run kessel:pipeline`; needs a Kessel checkout, [README](lab/kessel-reference/README.md)) |
| `karabast/`, `karabast/importer/` | the bot that plays people on karabast.net, and the importer that turns captures of human games into replays |

Tests sit next to what they test: `engine/test/`, `bots/test/`, `lab/test/`, `karabast/test/`, `karabast/importer/test/`
(all in `npm test`), `lab/analysis/test/` (`npm run analysis:test`), `bots/python/` (`npm run test:py`) and
`lab/kessel-reference/test/` (`load.test.js` in `npm test`; the rest need Kessel: `npm run kessel-reference:test`).

## Daily commands

```bash
npm run ladder -- --bots rush,heuristic,random --games 10   # local round robin -> results JSON (bots/README.md)
npm run realdeck:test -- --bot <bot>                          # 702 games vs c-clock on 27 real decks (lab/analysis/realdeck/README.md)
npm test && npm run test:py && npm run analysis:test          # what CI runs, plus cargo and the C bot build
cargo build --release                                         # Rust bots, binaries in target/release/
make -C bots/c && make -C bots/c test                         # c-clock and its card table tests
python3 bots/bundles.py                                       # arena bundles in build/arena/ (bots/README.md, "Arena")
SWU_TABLES_TOKEN=swu_r_... npm run open-tables                # the arena's open-table games into replays/open-tables (token: swu-arena.fly.dev/tables/logs)
```

`bots/external-bots.json` names every bot program, so the name works in `--bots`.

Every game's `hello` carries the card data for that game (`cards`: the engine's card JSON for both decks and the
tokens, `engine/game-cards.js`), in local games as in the arena. A bot reads its cards from there, never from
`forceteki/test/json`.

## Not here yet

- `rust-omni` and the `omni` bot's Rust simulations need Kessel; they build again once Holocron takes Kessel as a
  dependency.
- Bots that still read the card folder: `jev`, the JEPA bots, `clj-forecast`, `haskell`, `lisp`, `wasm`, `omni`
  (`bots/omni/lens.js`), and the learned JS bots and evaluators (`bots/learned/cards.js`, `lab/eval/cards.js`). `bend` and the `ports` bots build
  their card tables from it. The C, Rust and Python bots take their cards from `hello`.

## License and credits

The code is MIT licensed (`LICENSE`). This is an unofficial fan project. It is not made, endorsed or supported by Fantasy Flight Games, Asmodee, Disney or
Lucasfilm. Star Wars: Unlimited and its card names, card text and art belong to their owners.

- Rules engine: [forceteki](https://github.com/SWU-Karabast/forceteki), Karabast's engine (MIT), as the `forceteki/`
  submodule. Card data comes from the official card database through its `get-cards` download.
- Tournament deck lists and results in `decks/`: TCGEngine / SWU Stats (MIT, `decks/LICENSE.TCGEngine`), from public
  melee.gg Premier events. Online leader win rates in `lab/analysis/swustats/`: SWU Stats (swustats.net).
