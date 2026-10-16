# py-clock

A Star Wars Unlimited bot in Python 3 (standard library only). It plays through the stdio protocol
(`spec/stdio-protocol.md`), so the engine stays in Node and this process only sees the JSON `decide` messages.

    node lab/runners/ladder.js --bots py-clock,rush --games 10
    python3 -m unittest discover -s bots/python      # tests on mock boards, no engine needed
    python3 bots/bundles.py py_clock                 # build/arena/py_clock: the files for the arena's Python intake

Registered in `bots/external-bots.json` as `py-clock` (`"lang": "python"`). Card costs, keywords and text come with
each game's `hello`: `cards` holds the engine's card JSON for both decks and the tokens, and the bot builds its card
table from it (`CardDb.from_cards`). It reads no files. With no cards in hello it still plays from the board numbers
alone. `SWU_PY_TRACE=<file>` appends every prompt and the choice made (one JSON line each).

For the arena, `bots/bundles.py` copies the bot's modules (not the tests) into `build/arena/py_clock`; submit that
folder as a Python bot with entry `swu_clock.py`. The arena runs it on CPython for WASI, a 32-bit build, so `hash()`
and set order differ from 64-bit Python and a few games can go another way.

## Strategy: the clock

- **Values.** A unit is worth the base damage it will deal before it dies (`power x 2.2 rounds x weight`) plus a
  little for its body (remaining HP, shields, Sentinel). One point of base damage is worth more the closer that base
  is to 0. Both sides use the same numbers, so a trade is simply "value I remove minus value I lose".
- **The race.** Each side's clock is the number of rounds its units need to kill the other base. The side that wins
  the race weights base damage up (be the beatdown); the side that loses it weights enemy units up (control).
- **Attack planner.** The engine cannot be rolled back over stdio, so the bot simulates combat itself on a copy of
  the board (power and Raid, damage back, shields, Overwhelm, Sentinel, Saboteur, Restore) and runs a beam search
  over whole attack sequences. That finds plays a one-attack-at-a-time bot misses: two units killing one big unit,
  or killing a Sentinel first so the rest can hit the base. Lethal is checked first.
- **Cards.** A knapsack picks the set of hand cards that uses the most resources for the most value. Removal is only
  played when it hits something worth it, upgrades go before attacks, then the most expensive card.
- **Action window order:** lethal, deploy the leader, attacks that kill a ready enemy unit, cards, the rest of the
  attack plan, leader ability, then claim initiative (better than passing when nothing is left).
- **Other prompts** are read from their title ("Deal 3 damage to a unit", "Give a Shield token", "Attach ...") with
  the source card's text as fallback, and scored with the same unit values. Damage splits kill the most valuable
  units first and send the rest to the enemy base.
- **Loop guards.** Choosing the same action again in an identical state and prompt means it did nothing, so it is
  skipped. A window action that ended in Cancel is not retried that round.

## Files

| File | What |
| --- | --- |
| `swu_clock.py` | Entry point: the JSON Lines loop. A crash in a rule plays action 0 instead of losing the game. |
| `cards.py` | The card table from hello's `cards`, and the aspect penalty. |
| `board.py` | Board model from the `decide` message, unit values and the clock. |
| `planner.py` | Combat simulation and the beam search over attack sequences. |
| `effects.py` | Reads effects and pick counts from prompt and card text. |
| `policy.py` | One handler per prompt shape. |
| `test_policy.py` | Unit tests on mock boards, and one run of `swu_clock.py` with cards only in hello. |

## Engine bug found while testing

`Resonate` (HMW 098) crashes forceteki `2be4fcd` when played while a leader is still undeployed: its heal-target
check reads `damage` of a leader in the base zone (`Contract assertion failure ... in zone 'base'`). Repro:
`py-clock` vs `rush`, seed 115, `py-clock` as p1. The bot does not play Resonate.
