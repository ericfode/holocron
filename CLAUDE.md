# CLAUDE.md

Guidance for Claude Code (claude.ai/code) in this repository.

## What this repo is

Holocron holds the bots and the research of the SWU Arena project: every bot, evaluators, learning, deck building,
analysis, the Strategy Atlas model, Lean theory, and the Karabast player. `README.md` has the layout and the commands.

- The arena (`ericfode/swu_bot`) plays every rated game. Holocron submits bots and evaluators and reads results back
  through the arena's export API; it never sends the arena game results. Local games (ladders, the real-deck test,
  sweeps) are for research only.
- Kessel (`ericfode/kessel`) is the Rust rules simulator. A look-ahead bot brings its own simulator; only `omni*` bots
  see hidden cards, and they stay out of competitive ladders.
- The files came from `swu_bot` with their history and were then sorted into this layout (`git log --follow` works
  across both moves):
  - `bots/`: every bot (`bots/<name>/`, `bots/players/` with the name registry `players/index.js`, `bots/examples/`,
    `bots/starters/`), the bot list `bots/README.md` and `bots/external-bots.json`.
  - `engine/` and `decks/`: a copy of the arena's game player (swu_bot `7455601`, where it was `bot/env.js`,
    `bot/view.js`, ...): `env.js`, `view.js`, `protocol.js`, `match.js`, `game-pool.js`, `stdio.js`, `rng.js`,
    `recorder.js`, `decklists.js`, `cardpool.js`, `ratings.js`, `random-run.js`, `debug-seed.js`, and the deck lists.
    `game-cards.js` and the card data in hello (`cards`) in `match.js` and `protocol.js` follow swu_bot `1d819e2`
    (`game-cards.js` is the arena's file as it is; `all-cards.js` holds Holocron's lists of every card).
    Fix player bugs in the arena first, then copy the fix here. `protocol-test.js`, `rollback-test.js` and
    `determinism-check.js` are Holocron's own checks of this player (the arena dropped them).
  - `lab/`: `runners/` (ladder, sweeps, measurement scripts), `eval/`, `learn/`, `info/`, `deckbuild/`, `tools/`,
    `analysis/`, `theory/`, `meta/`, `dashboard/`, `models/`, and `kessel-reference/`: the engine side of Kessel's
    reference corpus (scenarios, generator, probe fixtures, card pipeline runner; its `README.md`).
  - `karabast/` (the Karabast player) and `karabast/importer/`.
  - Tests sit next to what they test (`engine/test/`, `bots/test/`, `lab/test/`, `karabast/test/`, ...).
- Paths into code that is not in this repo stay as the arena and Kessel name them: `bot/tournament.js`,
  `bot/compiled/`, `bot/arena/` (arena), `omni-rs`, `omni-wasm`, `card-compiler`, `bot/cards` (Kessel).
  `lab/kessel-reference/` loads Kessel's code from a checkout (`KESSEL_DIR`, default `../kessel`) by Kessel's current
  paths (`cards/`, `compiler/`, `crates/`), and its index command writes Kessel's `cases.json`.

**Do not modify anything inside `forceteki/` without asking the user first.** It is a submodule of `ericfode/forceteki`
pinned to the arena's commit (`2ebed8ca2`); move the pin only together with the arena.

## Commands

Engine setup (once; Node 22):

```bash
git submodule update --init
cd forceteki && npm ci --ignore-scripts && npm run get-cards && npm run build
```

`engine/` loads the engine from `forceteki/build/server` and card data from `forceteki/test/json` (both gitignored).
If you hit `Importing card class with repeated id!`, delete `forceteki/build/` and rebuild.

```bash
npm test                        # unit tests (needs the built engine); CI runs this, test:py, analysis:test, cargo, make
node engine/random-run.js 3 1   # engine sanity check: seeds 1-3 give 594/342/486 steps, p2 wins (deterministic)
node engine/debug-seed.js <seed>
node lab/runners/ladder.js --bots rush,random-a,c-clock --games 2   # quick ladder; c-clock needs make -C bots/c
npm run ladder -- --bots rush,heuristic,random --games 10
npm run realdeck:test -- --bot <bot>   # standard bot test: 702 games vs c-clock on 27 real decks
```

## How `engine/env.js` drives the engine

`env.js` constructs a forceteki `Game` directly (no server, sockets or lobby):

- `Env` loads card data once (the first `require` of ~2000 card modules takes ~7 s) and builds decks.
- `EnvGame`: `start()`, `legalActions(pid)`, `apply(pid, action, rng)`, `over`, `winners`, `round`,
  `promptSignature(pid)`. Actions are plain objects of kind `button`, `card`, `option`, `displayCard`, `perCardButton`,
  `distribute`.
- The player who must act is the one with at least one legal action. Game over is `game.winnerNames.length > 0`.
- The bot RNG (`seededRng`) and engine RNG (`game.setRandomSeed`) are separate; seed both.
- Undo is off by default; `newGame({ undo: true })` enables `UndoMode.Free` for rollback search.

Engine input is always followed by `game.continue()`. Easy to get wrong:

- The distribute-damage/healing `Done` button has `command: 'statefulPromptResults'`: send the split that way, never as
  a menu click. Indirect damage on a unit may not exceed its `remainingHp` (bases uncapped), and the sum must equal
  `amount` unless `canDistributeLess`.
- "Cards with buttons" prompts (`perCardButtons` present): only the per-card buttons are legal. Plain display-selection
  prompts click the card via `menuButton(pid, cardUuid, promptUuid, 'menuButton')`.
- Number prompts and dropdowns answer with `menuButton(pid, String(value), promptUuid)`. Multi-select card prompts:
  click cards, then `Done`.

## Known engine bugs

The arena's `CLAUDE.md` keeps the list (TakeCover, Sundari Palace, Mystic Monastery, rollback drift, and others).
Treat engine errors during play as findings to report to the arena, never something to patch in `forceteki/`.

## Rules that carry over from the arena project

- Karabast opponents' names stay on the Karabast machine and with Eric: never in this repo, memory or shared files.
- Only openly public data, credited; no usernames or chat from other people's games.
- No model identifiers in commits or PRs.
