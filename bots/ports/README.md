# Protocol ports of heuristic and rush

`heuristic.js` and `rush.js` are the in-process bots of `bots/players/` (heuristic with the balanced profile and
depth 1, and rush) rewritten as protocol v2 programs, so the arena can play them as submitted entries. The in-process
bots read the engine directly; these read only the protocol's messages (`state`, `prompt`, `actions`), so they run
anywhere a bot program runs, including the arena's WebAssembly sandbox.

| File | What it is |
|---|---|
| `heuristic.js` | One-ply lookahead through the referee's simulations (`sim: true`): every legal action, and every option of its first follow-up prompt, is played on a simulation up to the next action window and scored. Prompts outside the action window get the rule-based choice. |
| `rush.js` | Rules only: the most expensive card from hand, then attacks, then the leader, then pass; attacks go face first. |
| `common.js` | The in-process bots' evaluation (same weights) and rule-based choices, over protocol messages. |
| `cards.json` | Printed cost, unit or not, and aspects by set code: what the protocol does not send. Made by `make-cards.js` from `forceteki/test/json/Card`; run it again when the card data changes. |
| `stdio.js` | `serve()` for Node. The arena's intake swaps it for its own. |

## How close are they to the in-process bots?

- `rush.js` plays the same games as `rush`: 19 of 20 games against `heuristic` and `c-clock` on the same seeds had the
  same moves and result (the 20th was against `heuristic`, whose own rollback search can differ between runs).
- `heuristic.js` uses the same evaluation and rules, but its playouts run on the referee's copy of the game, where the
  cards you cannot see are dealt again (one deal per decision, so all actions are scored on the same cards). The
  in-process bot played on the real hidden cards with a reseeded random stream. Without simulations (an arena that
  offers none) it plays rush's rules at action windows.
- `heuristic.js` guards its time: it aims at 40 s of thinking per game and at most 3 s per action window, and stops
  trying actions when a decision runs long. Under the cap it plays the same moves for the same messages.
- As WebAssembly bundles under the arena's limits (60 s of thinking per game, 2 games at once), 10 games each against
  `rush` and `c-clock`: `heuristic.js` thought 10.6 s per game on average, 21.3 s at most, and 2.5 s at most for one
  decision; `rush.js` about 0.1 s per game. No time forfeits.

## Run them

```bash
node bots/ports/heuristic.js [name]     # a bot program on stdin/stdout (spec/protocol.md in the arena)
node bots/ports/rush.js [name]
node lab/runners/ladder.js --bots heuristic-port,heuristic --vs rush,c-clock --games 10 --key none
node --test bots/test/ports.test.js
```

`heuristic-port` and `rush-port` are in `bots/external-bots.json`.

## In the arena

They enter the arena as JavaScript submissions (kind `js`): the files of this folder except `make-cards.js` and this
README, with `heuristic.js` or `rush.js` as the entry. The intake bundles them with Javy into one `bot.wasm` that
runs under wasmtime (about 1.4 MB each). They have no Node built-ins and require nothing outside this folder, which is
what the intake allows.

The heuristic port needs the arena to offer simulations. An arena whose bots bring their own simulator would play it
as rush at every action window.
