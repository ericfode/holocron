# Holocron

Bots and research for the SWU Arena: every bot, the position evaluators and learning code, deck building, the game
analysis and Strategy Atlas model, the Lean theory, and the bot that plays people on karabast.net.

Holocron uses the arena as its playground. The arena (`ericfode/swu_bot`, private) plays every rated game: Holocron
sends it bots and evaluators, and reads ratings, games and analytics back through the arena's export API. Holocron
never sends the arena game results. Kessel (`ericfode/kessel`), the Rust rules simulator, is its own repo; look-ahead
bots bring it as their simulator.

The files came from `swu_bot` with their history (`git log --follow` works across the move). Their paths are the same
as they were there for now; a later change sorts them into `bots/`, `lab/` and `karabast/`.

## Setup

Node 22, Python 3, and a Rust toolchain for the Rust bots.

```bash
git clone --recursive https://github.com/ericfode/holocron && cd holocron
cd forceteki && npm ci --ignore-scripts && npm run get-cards && npm run build && cd ..
npm ci
npm test                      # bot logic on mock boards, evaluators, deck building, the Karabast seat, the importer
node bot/random-run.js 3 1    # the engine works: seeds 1-3 give 594/342/486 steps, p2 wins each
```

`forceteki/` is a submodule of `ericfode/forceteki` at the commit the arena pins (`2ebed8ca2`). Never change files
inside it; workarounds for engine bugs go in `bot/`.

## Layout

| Path | What it is |
| --- | --- |
| `bot/players/`, `bot/examples/` | the in-process bots (random, rush, heuristic and its profiles, ISMCTS, omniscient) and the example protocol clients; `players/index.js` is the name registry |
| `bot/c`, `rust`, `python`, `lisp`, `clojure`, `haskell`, `bend`, `wasm`, `jev`, `jepa`, `learned`, `rust-learned`, `rust-omni`, `omni` | bots in other languages and the research bots, each with its README |
| `bot/arena/starters/` | the starter bots the arena hands to new builders |
| `bot/eval/`, `bot/learn/`, `bot/info/` | position evaluators (win predictors), self-play learning, the knowledge dial |
| `bot/deckbuild/` | deck building and drafting (deck JEPA) |
| `bot/karabast/`, `importer/` | the bot that plays people on karabast.net, and the importer that turns captures of human games into replays |
| `bot/ladder.js`, `ladder-worker.js`, `ladder-report.js`, `sweep.js`, ... | local round robins and gauntlets, parameter sweeps, measurement scripts |
| `bot/env.js`, `view.js`, `protocol.js`, `match.js`, `game-pool.js`, `stdio.js`, `rng.js`, `recorder.js`, `decklists.js`, `cardpool.js`, `ratings.js`, `decks/` | the arena's game player, copied from `swu_bot` at `7455601` so games can be played here; replaced by the arena's published player when it has one |
| `analysis/` | game analysis, the real-deck bot test (`npm run realdeck:test -- --bot <bot>`), SWU Stats |
| `meta/`, `dashboard/` | the Strategy Atlas model and page builder, the research dashboard |
| `theory/` | Lean proofs about the game and the measurements that check them |
| `models/` | trained model files the bots load |
| `tools/search-profile/`, `tools/omni-search-bench.js` | search profiling and benchmarks |

## Daily commands

```bash
npm run ladder -- --bots rush,heuristic,random --games 10   # local round robin -> results JSON (bot/README.md)
npm run realdeck:test -- --bot <bot>                          # 702 games vs c-clock on 27 real decks (analysis/realdeck/README.md)
npm test && npm run test:py && npm run analysis:test          # what CI runs, plus cargo and the C bot build
cargo build --release                                         # Rust bots, binaries in target/release/
make -C bot/c                                                 # c-clock
```

`bot/external-bots.json` names every bot program, so the name works in `--bots`.

## Not here yet

- `rust-omni` and the `omni` bot's Rust simulations need Kessel; they build again once Holocron takes Kessel as a
  dependency.
- Building a bot into a submission bundle uses the arena's bundle tool (`bot/compiled/` in `swu_bot`) until the
  arena publishes it.
