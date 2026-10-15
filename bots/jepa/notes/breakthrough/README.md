# Where the JEPA bot is weakest (2026-10-15)

Eric asked: quantify where the model is weakest, how it differs from a typical JEPA, and how to improve it. All tests
are the standard 702 games against c-clock on the 27 real decks (`bot-test.js`, the same deals for every bot), paired
on the same games: a bootstrap over seeds plus a sign test on the games only one bot won. The bot under test is
jepa-tx-gate (tx-t10 + tx-t10-e, planner at gate 0.04, resource-v1), 51.2% against c-clock.

## 1. Kinds of decision (`swaps.txt`)

`bots/jepa/advisor.py` plays jepa_bot.py but lets c-clock answer one kind of prompt. A control run through the same
proxy with nothing swapped played every game the same as the plain bot.

| c-clock answers | decisions | win rate | paired change |
|---|---|---|---|
| nothing (control) | 0 | 51.2% | +0.0 |
| mulligan | 676 | 51.5% | +0.3 [-2.8, +3.4], p=0.93 |
| **resource** | 9,766 | **54.9%** | **+3.7 [+0.9, +6.5], p=0.019** |
| other (targets, triggers, options, distribute) | 17,289 | 47.6% | -3.5 [-6.8, -0.1], p=0.048 |
| window (the move) | 18,307 | 29.5% | -21.6 [-25.6, -17.8] |

Resource choices are a clean weakness. The other and window swaps mostly measure broken coherence: c-clock picks a
move expecting its own follow-up, then the JEPA answers the follow-up its own way (and the reverse for the planner's
planned follow-ups). A move and its follow-ups must come from one plan.

**Fix** (`resource-rule.txt`): `--resource c-clock` ports c-clock's rule (bots/c/bot.c choose_resource and keep_value,
default flags) into resource_policy.py. It agrees with c-clock on 20,199 of 20,199 of its resource decisions in
recorded games (resource-v1, a model fitted to copy c-clock and rust-search: 80.8%). With it the hybrid wins **55.1%**
(+3.7 [+0.9, +6.5], the same games as the swap run). The bot without the simulator gains nothing (-0.9 [-3.2, +1.6]).

## 2. Its own positions against the training positions (`onpolicy-yardstick.txt`, `onpolicy-breakdown.txt`)

The model was trained on branch points from rush-vs-rush games. `replay_branches.js` makes the same data at the
positions of recorded games: here 4,676 action windows of tx-s10a-c in its games against c-clock (pivots-rec-1, every
4th game), every legal move played to where it settles and judged by linear-deck-g4.

| tx-t10-e, settled horizon | top-1 (chance) | regret | blunders | random move's regret | moves per point |
|---|---|---|---|---|---|
| rush-vs-rush test (held-out games) | 0.813 (0.401) | 0.58 pts | 3.5% | 3.56 pts | 4.4 |
| its own positions vs c-clock | 0.678 (0.308) | 1.03 pts | 6.1% | 4.01 pts | 5.5 |

On the training kind of position the model loses 16% of what a random move loses; on the positions it really meets,
26%. Typical world-model agents (Dreamer, MuZero, EfficientZero) keep retraining the model on the agent's own games;
this JEPA never saw its own positions. Where the regret goes on its own positions: choosing which card to play from
hand holds 44% of the lost value (top-1 0.556), attacks and abilities 30% (0.762), pass 14%; positions where the
best and worst move are 10+ points apart are 28% of positions and 60% of the lost value; rounds 3-4 hold 44%.

## 3. Decks (`deck-par.txt`, `decks-and-shares-g04.txt`)

Par per game = c-clock's result with the same decks and seats, from 10 c-clock mirrors on fresh deals (6,807 games).
How the bot handles the deck it holds differs from c-clock's more than noise allows (chi-square 44 on 26 df for the
hybrid, 82 for the no-simulator bot); the opponent's deck does not (31-38 on 26). Both bots do worst, against their own
mean, with Obi-Wan vergence-temple, Ezra yellow and Mando colossus, and best with Maul blue-force, Talzin red-force and
Dedra colossus.

## Next

- On-policy retrain: `replay_branches.js` data at every action window of the bot's recorded games (fresh deals), mixed
  into tx-t10's recipe (`tx_train_torch.py --pack-b-weights`), with and without the decision loss (`--w-decide`: the
  evaluator-copy head on each move's imagined settled board should order the moves as the judge orders the real ones).
- The history track (claude/jepa-history, merged here): deck lists, unseen cards and the game so far as model inputs.
