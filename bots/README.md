# bots/ — every bot, and how they plug in

Every bot here plays through the copied game player in `engine/`, which runs the real rules engine (`forceteki/`) with
no server, sockets, lobby or login. Commands run from the repo root; other paths below are relative to this folder,
except those that start with `engine/`, `lab/`, `decks/` or `karabast/` (from the repo root).

Run from the **repo root** (the engine submodule `forceteki/` needs `npm ci --ignore-scripts`, `npm run get-cards` and
`npm run build` done first):

    node engine/random-run.js [numGames] [startSeed] [maxSteps]
    node engine/debug-seed.js <seed>        # replay one seed and dump the context if it errors

## Folders

| Folder | Bots |
| --- | --- |
| `players/` | the in-process bots (random, rush, heuristic and its profiles, ISMCTS, omniscient) and the name registry `players/index.js` |
| `examples/` | example protocol clients in JS and Python (`node-random`, `node-search`, `py-random`) |
| `starters/` | the starter bots the arena hands to new builders |
| `c/`, `python/`, `rust/`, `lisp/`, `clojure/`, `haskell/`, `bend/`, `wasm/` | bots in other languages over the stdio protocol (`c-clock`, `py-clock`, `rust-*`, `lisp`, `clj-forecast`, `haskell`, `bend*`, `wasm`) |
| `jev/` | `jev`, `jev-look`: moves picked by TypeSafe's Jev model |
| `learned/`, `rust-learned/`, `jepa/` | learned bots: a tiny world model in JS, the Burn model in Rust, the JEPA planner |
| `omni/`, `rust-omni/` | the omniscient reference bot and endgame prover, and rust-search on Kessel's simulator (they see hidden cards: never in competitive ladders) |
| `test/` | the bot tests (`npm test`) |

Most folders have their own README. `external-bots.json` names every bot program, so the name works in `--bots`.

## The game player (`engine/`)
- `engine/env.js` — `Env` (card data, random deck builder) and `EnvGame` (`start()`, `legalActions(pid)`, `apply(pid, action)`).
  Actions are plain objects: `button`, `card`, `option`, `displayCard`, `perCardButton`, `distribute`.
- `engine/random-run.js` — random-vs-random games; prints per-game outcome, games/sec and the prompt shapes it saw.
- `engine/debug-seed.js` — replays one seed deterministically and prints the last actions and prompt state on failure.
- Games are reproducible: engine RNG is seeded via `game.setRandomSeed`, bot choices via `seededRng`.
- Engine input rules learned the hard way: the distribute-damage prompt's `Done` button is *not* a menu click
  (it is sent via `statefulPromptResults`); in "cards with buttons" prompts only the per-card buttons are legal;
  indirect damage on a unit may not exceed its remaining HP.
- Undo/snapshots are disabled by default (`newGame({ undo: true })` enables `UndoMode.Free` for search experiments).
- `engine/match.js` — `playGame(env, {seed, bots, record, snapshot, key, limits})` plays one game; `engine/view.js` — the
  board snapshots replays record (`engine/recorder.js` is an alias). The arena's `bot/tournament.js` and `bot/gate.js`
  (determinism gate) are not copied here; `lab/runners/ladder.js` plays local round robins.

## The bot protocol
Every bot is a client of the bot protocol (`spec/protocol.md` in the arena repo): JSON messages, over stdio for a program in any language or as plain objects in process.
- `engine/stdio.js` — `StdioClient` runs a bot program; `serve(client)` runs an in-process client as a program. No engine dependency. `players/external.js` still exports it as `ExternalBot`.
- `engine/protocol.js` — the referee: hello/decide/over, time limits, blame (a bot that breaks a game loses it), simulations (`sim` requests) on a separate copy of the engine with hidden cards dealt again.
- `engine/rng.js` — seeded and keyed random streams; `engine/view.js` — what a seat sees (board, prompt, actions).
- `ports/` — `heuristic-port` and `rush-port`: the heuristic (balanced, depth 1) and rush bots as protocol v2 programs, the heuristic looking ahead through simulations. They are how the two enter the arena as submitted entries; see `ports/README.md`.
- `examples/random_bot.py`, `examples/random-bot.js`, `examples/search-bot.js` — reference clients (the last one searches with simulations). Register programs by name in `external-bots.json` (or `$SWU_EXTERNAL_BOTS`); the registry in `players/index.js` picks them up, so the name works in `--bots` for `lab/runners/ladder.js`. Entries name their files from the repo root (`bots/c/swu-c`, `bots/python/swu_clock.py`).

## Bots in other languages
- `wasm/` — a bot written by hand in WebAssembly text (`bot.wat`) behind a thin stdio shim (`host.js`), registered as `wasm`. See `wasm/README.md`.
- `python/` — `py-clock`, a Python bot (race-clock evaluation, beam search over attack sequences, card data from the engine JSON); see `python/README.md`.
- `c/` — `c-clock`, a bot in C on that protocol (`make -C bots/c` first), and `c-clock2` (`--v2`: Pilot deploys, no duplicate uniques). See `c/README.md`.
- The full interface and replay format are written up in the arena repo's `spec/`.
- `jev/jev_bot.py` — `jev`: each move is picked by TypeSafe's Jev model (a Choice over the legal actions). See `jev/README.md`.
- `rust/` — Rust bot (`swu-bot-rs`, policies `random`, `greedy`, `greedy2` and `search`) speaking the stdio protocol (v1, or v2 with simulations when offered); registered as `rust-<policy>` in `external-bots.json`. `greedy2` reads card stats from `forceteki/test/json`. Build with `cargo build --release` at the repo root (Cargo workspace, binaries in `target/release/`), test with `cargo test --workspace`, then `node bots/rust/check.js [gamesPerSeat] [startSeed] [cardJsonDir]` plays both against `random-a` on the real engine. Why a subprocess rather than WASM or a native addon: see `rust/README.md`.
- `rust-omni/` — `rust-omni`: rust-search with its playouts in the native rules simulator (Kessel's `omni-rs`), in-process and about 15 times faster per decision. It searches only games whose decks come from the simulator's card pool (`node bots/rust-omni/pool-decks.js` makes such decks for `ladder.js --decks`); other games it plays as rust-search. See `rust-omni/README.md`.
- `clojure/` — `clj-forecast` (Clojure): plays each legal action on its own immutable board model and lets the opponent answer in a 3-ply alpha-beta search; card stats from `forceteki/test/json`. Needs Java only (`clojure/run.sh` fetches Clojure from Maven Central). `bots/clojure/run.sh test` runs its tests. See `clojure/README.md`.
- `lab/tools/synth-cards.js [outDir]` — writes a stand-in card-data folder (real card classes, invented stats, default `replays/.synth-cards`) for machines that cannot download card data. Pass the folder to `new Env(dir)` or as `cardJsonDir` above. Results on it are plumbing checks, not SWU balance numbers.

## Bots and the ladder
- Registry: `players/index.js` (`makeBot(name)`), used by `lab/runners/ladder.js` (and the arena's `tournament.js`).
  - `random*` — uniform random. `rush` — rule-based, no lookahead: plays its most expensive card, attacks face, then passes.
  - `heuristic`, `aggro`, `tempo`, `control` — the same one-ply rollback search (`players/heuristic.js`) with different
    evaluation profiles (`players/profiles.js`); `heuristic` is the original weights with the base-danger sign fixed, `legacy` is the original evaluation bit-for-bit (inverted danger term included). Add `-dN` for depth N.
  - `ismcts[-bB][-hH][-nN]` — known-decklist Information Set MCTS (`players/ismcts.js`, `players/belief.js`). Both
    decklists are known; each iteration samples one world (my deck order; which unseen opponent cards are in hand,
    resources or deck), searches my turn with UCB in one shared tree, lets the opponent reply from its sampled hand and
    scores the result with the heuristic evaluation. `B` = belief sharpness: the weight of a card in the opponent's
    hand is `exp(-B * evidence)`, where evidence grows each time the opponent could afford the card but spent a window
    without paying for anything (0 = uniform over the decklist). `H` = exchanges before scoring, `N` = iterations
    per legal action. `ismcts-peek` searches the real hidden cards: an unfair control that measures what hidden
    information is worth. `ISMCTS_THOUGHTS=<dir>` makes the bots write their latest search there;
    `node lab/runners/ismcts-panel.js --runs <ladder dir> --thoughts <dir> --watch 10` turns that into the dashboard panel.
    `node lab/runners/determinize-check.js` checks that world sampling keeps zone sizes and that rollback restores exactly.
  - `name#tag` enters the same bot twice (`aggro#1,aggro#2`) as a sanity check.
- `node lab/runners/ladder.js --bots rush,aggro,tempo,control,heuristic,random --games 10 [--workers 3] [--seed 1] [--record] [--key K|none]`
  runs a round robin on worker threads. Each seed is played once from each seat (random decks follow the seat, so deck luck cancels).
  Decks come from a random run key, as in the arena's `tournament.js`; it is saved in `ladder.json` (`config.key`) when the run is done.
  Pass it as `--key` to give a second run the same games, or use `--key none` to deal from the seed alone.
  After every game it rewrites `<out>/<id>/index.json` (same tournament index as the arena's `tournament.js`, so the viewer and the
  research dashboard read it unchanged) and `<out>/<id>/ladder.json` (schema `swu-ladder/1`: per-bot W/L/D, win rate with
  95% CI, sequential Elo, Bradley-Terry Elo, pair matrix, Elo history). Writes are atomic. `--record` also saves `games/<id>.jsonl`
  replays (~1 MB each). `--out` defaults to `/mnt/project-files/results` when it exists, else `results/`.
- `--vs a,b,c` turns the ladder into a gauntlet: each `--bots` entry plays each `--vs` entry on the same seeds (not each
  other), which is what a parameter sweep needs: `node lab/runners/ladder.js --bots ismcts-b0,ismcts-b1,ismcts-b4 --vs rush,heuristic --games 8`.
- `--decks <file>` plays fixed deck lists instead of random decks (`engine/decklists.js`; real tournament decks in `decks/`, see
  `decks/README.md`). Seed `--seed + s` plays deck pair `s mod P` (P = n(n-1)/2), so the deal depends on the seed minus
  `--seed`, not on the seed alone. The pairs come in round-robin rounds, so a run cut after whole rounds has given every
  deck the same number of games (when n is odd, a deck that sat out a round has one seed less: 2 games less per bot
  pair). Each bot keeps its deck when the seats swap; both games of a seed use the same engine seed, but the seats get
  the same shuffles only when both decks have the same size. In one pass over the pairs each bot holds each deck about half the time, and the next pass
  gives each bot the other deck of every pair. Give each bot pair whole passes (`--games` a multiple of 2P, e.g. 702 or
  7020 for 27 decks), otherwise some pairs play more than others (the ladder warns). Index entries then carry
  `decks: {p1, p2}`. A mirror (`--bots c-clock#a,c-clock#b`) cancels the bots out, so it rates the decks:
  `lab/analysis/realdeck/compare.js` compares that with human results.
- `npm test` — unit tests for ratings, the report and bot logic on mock boards (needs `forceteki/build`, not card data);
  the tests sit next to what they test: `test/` here, `engine/test/`, `lab/test/`, `karabast/test/`.

## Arena
- The hosted arena (submissions, the arena window, the WebAssembly bundles and rated rounds) lives in the arena repo
  (`ericfode/swu_bot`, `bot/arena/` and `bot/compiled/` there); Holocron sends it bots and reads results back.
