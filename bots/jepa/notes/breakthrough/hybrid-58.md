# From 51.2% to 58.7%: the hybrid's three fixes, and what failed (2026-10-15)

All results: the standard 702 games against c-clock on the 27 real decks (`bot-test.js`, the same deals for every
bot), paired on the same games (bootstrap over seeds, sign test on the games only one bot won). Desktop WSL runs, 14
workers. Model files: `bots/jepa/models/tx-t10.safetensors` and `tx-t10-e.safetensors` (the runs used copies under
`runs/` with the same sha256: 50b8f9a2... and bee3f601...).

## The bots

Common arguments (the no-simulator part of every bot below):
`--model bots/jepa/models/tx-t10.safetensors --window-model bots/jepa/models/tx-t10-e.safetensors --window-horizon s --mix 0`

| bot | what changes | extra arguments |
|---|---|---|
| tx-t10-g04 (jepa-tx-gate this morning) | the planner at windows whose imagined moves spread 0.04+ | `--resource bots/jepa/models/resource-v1.json --score plan --plan-model bots/jepa/models/tx-t10-e.safetensors --plan gate=0.04` |
| tx-t10-g04-rc | c-clock's resource rule | `--resource c-clock --score plan --plan-model bots/jepa/models/tx-t10-e.safetensors --plan gate=0.04` |
| tx-t10-g04-rc-fs | the action phase's other prompts by the settled board | `--resource c-clock --follow-horizon s --score plan --plan-model bots/jepa/models/tx-t10-e.safetensors --plan gate=0.04` |
| **tx-t10-g04-rc-fs-pv** | **the planner judges with tx-t10's own value head** | `--resource c-clock --follow-horizon s --score plan --plan-model bots/jepa/models/tx-t10.safetensors --plan gate=0.04` |

The 58.7% bot in one line:

```
python3 bots/jepa/jepa_bot.py --model bots/jepa/models/tx-t10.safetensors --window-model bots/jepa/models/tx-t10-e.safetensors --window-horizon s --mix 0 --resource c-clock --follow-horizon s --score plan --plan-model bots/jepa/models/tx-t10.safetensors --plan gate=0.04 --name jepa-tx-gate
```

Code: `--resource c-clock` (resource_policy.py, c7b70df), `--follow-horizon s` (jepa_bot.py, 1fd40d0), both on
holocron claude/jepa-breakthrough. The planner needs the simulator (protocol v2 `sim`); without it the bot plays as
the no-simulator rows below.

## Results with the simulator

| bot | won | vs tx-t10-g04 (51.2%) | vs tx-t10-g04-rc (55.1%) | windows planned | ms per decision (mean / max) |
|---|---|---|---|---|---|
| tx-t10-g04 | 51.2% [47.4, 54.9] | | | 59% | 75.5 / 3,510 |
| tx-t10-g04-rc | 55.1% [51.4, 58.8] | +3.7 [+0.9, +6.5], p=0.019 | | 59.6% | 121.6 / 5,171 |
| tx-t10-g04-rc-fs | 56.3% [52.5, 59.9] | +5.1 [+1.9, +8.2], p=0.003 | +1.3 [-1.3, +3.9], p=0.39 | 62.5% | 102.7 / 4,782 |
| **tx-t10-g04-rc-fs-pv** | **58.7% [55.0, 62.3]** | **+7.7 [+4.2, +11.1], p<0.001** | **+3.7 [+0.3, +7.1], p=0.050** | 64.4% | 103.9 / 4,048 |

tx-t10-g04-rc-fs-pv against tx-t10-g04-rc-fs: +2.3 [-0.9, +5.7], p=0.20. No bot lost a game on time (the limit is 10 s
per decision; the planner stops at 5 s).

## Results without the simulator (what Karabast can run)

| bot | won | paired vs tx-t10-va |
|---|---|---|
| tx-t10-va (`--resource bots/jepa/models/resource-v1.json`) | 31.1% | |
| tx-t10-va-rc (`--resource c-clock`) | 30.3% | -0.9 [-3.3, +1.6] |
| **tx-t10-fs** (`--resource bots/jepa/models/resource-v1.json --follow-horizon s`) | **34.5%** | **+3.3 [+0.3, +6.4], p=0.027** |
| tx-t10-fs-rc (`--resource c-clock --follow-horizon s`) | 34.4% | +3.2 [+0.1, +6.4], p=0.049 (the same as tx-t10-fs: +0.0 [-2.5, +2.5]) |

Decision time without the simulator: 4.0 ms mean, under 0.2 s max.

## What failed: training on its own positions with a decision loss (tx-o1d)

tx-o1d = tx-t10's recipe plus 18,018 on-policy branch points (`replay_branches.js` at every action window of
tx-t10-va's own games against c-clock, fresh deals; 25.5% of the branch draws) plus `--w-decide 1` (the
evaluator-copy head on each move's imagined settled board ordered like linear-deck-g4 orders the real ones).

- The judge yardstick improved: on tx-s10a-c's own windows (other games) top-1 0.678 -> 0.750, regret 1.03 -> 0.77
  pts, blunders 6.1% -> 4.8%; the rush test held (0.807 vs 0.813).
- Play fell: no simulator 20.0% (-11.1 [-14.6, -7.6] vs tx-t10-va); hybrid at gate 0.04 with c-clock resources 47.3%
  (-7.7 [-11.5, -3.8] vs tx-t10-g04-rc, 42.9% of windows planned).
- Split, no simulator: tx-t10 raw + tx-o1d-e at windows 26.2% (-5.1 [-8.4, -1.7]); tx-o1d raw + tx-t10-e at windows
  22.9% (-8.2). Both halves got worse.
- Own-move regret (both bots on the same 351 fresh deals, half of each bot's own windows branched and judged): the
  moves tx-t10-va played lose 1.51 pts per window, tx-o1d-va's 1.09 pts, yet tx-o1d-va wins 23% to tx-t10-va's 32%.
- With `--follow-horizon s`, tx-o1d falls to 7.4% (-23.4): its settled-board forecasts away from the window choice
  are broken. The decision loss taught the predictor to order the window's moves the judge's way, not to forecast.

Lesson: the judge's (linear-deck-g4's) score of the settled board is not what wins. Fitting it harder hurt; judging
the planner's real boards with a head trained on who won helped (+2.3 over the evaluator copy, +3.7 over
tx-t10-g04-rc). The next step is that head refit on games against c-clock (`fit_value.py`: held-out BCE 0.457 ->
0.437 on pack-h).

## Later runs (same day)

On the test deals, paired against the 58.7% bot (tx-t10-g04-rc-fs-pv) unless noted:

| change | won | paired |
|---|---|---|
| judge = tx-t10's head refit on 811k decisions vs c-clock (`fit_value.py`, held-out BCE 0.457 -> 0.437) | 58.1% | -0.4 [-4.1, +3.3] |
| gate 0 (plan every window) | 53.7% | -5.1 [-8.1, -2.2] |
| gate 0.06 (50% of windows planned) | 56.0% | -2.6 [-5.0, -0.1] |
| gate 0.08 (37%) | 55.1% | -3.6 [-6.7, -0.6] |
| `--plan reply=1` (judge after the opponent's next action, played like rush) | 52.7% | -6.0 [-9.4, -2.6] |
| judge = mean of tx-t10 and tx-t10-e (`--plan-model a,b`), gate 0.04 | 60.0% | +1.0 [-1.6, +3.8] |
| the same at gate 0 | 56.4% | -2.6 [-6.0, +0.7] |
| tx-o1 (tx-t10's recipe + 18k on-policy points, no decision loss) as the hybrid | 59.7% | +0.7 [-3.1, +4.5] |
| tx-o1 without the simulator (`-fs-rc`), vs tx-t10-fs-rc | 30.6% | -4.1 [-7.8, -0.3] |

The outcome-trained head judges big decisions better than the evaluator copy and small ones worse (gate 0 hurts it,
less so the mean of both). On-policy branch data has not helped play in any form.

**Confirmation on fresh deals** (702 games each, ladder seed 40001, no key: the same deck pairings and seats, each run
its own shuffles):

| bot | won | vs the morning bot |
|---|---|---|
| tx-t10-g04 (the morning bot) | 52.9% (366-326) | |
| tx-t10-g04-rc | 58.3% (403-288) | +5.6 [+1.0, +10.0], p=0.020 |
| **tx-t10-g04-rc-fs-pv** | **63.8% (441-250)** | **+11.4 [+6.6, +16.2], p<0.001** (+5.9 [+1.2, +10.5] vs -rc) |
| tx-t10-g04-rc-fs-pe (mean judge) | 60.9% (424-272) | +8.0 [+3.4, +12.7] (-3.2 [-7.6, +1.2] vs -pv) |

Over both deal sets the value-judged bot and the mean-judged bot are equal within noise; the value-judged one (one
model, already the 58.7% bot) stays the pick.

**More on-policy data (tx-o2)**: tx-t10's recipe + all six on-policy parts (87,821 points from the bots' own games
against c-clock, 25% of the branch draws), no decision loss. Yardstick flat (own-positions top-1 0.671, regret 0.97
pts; rush 0.810). Play: without the simulator 28.7%, -5.7 [-9.3, -1.9] vs tx-t10-fs-rc; as the value-judged hybrid
56.7%, -2.1 [-6.0, +1.9]. With tx-o1 (18k points: -4.1 and +0.7), more on-policy branch data makes the
no-simulator bot worse and leaves the hybrid alone. Closed for this model.

**Planner breadth**: roots 32 and follow 10 (16 and 6 by default) changed 4 of 688 games: 59.0%, +0.3 [-0.3, +0.9].
Planned windows use 13.6 lines and 0.40 s on average, far under the caps (150 lines, 5 s); breadth is not a lever.

## Planner data, a settled-board judge and a policy head (coordinator's steps 1-3)

**Data**: the 58.7% bot with `--plan-log` against c-clock on new deals (ladder seed 50001, no key): 6,318 games in 59
minutes, won 60.5% (3,769-2,462). `plan_data.py`: 6,231 decided games, 92,094 planned windows, 91,469 judged boards.

**Judge** (`fit_value.py` on the picked move's best judged board, label = game won; tx-t10-sb): held-out BCE 0.494 ->
0.4745, accuracy 0.746 -> 0.760. As `--plan-model`: 60.5%, +1.6 [-1.5, +4.7] vs the 58.7% bot (p=0.38).

**Policy head** (`policy_train.py`, frozen tx-t10-e, per candidate [z, zs, zs-z, v] -> 128 -> 1, softmax over up to 24
candidates; pol-1): held-out agreement with the planner 0.556 (imagined best) -> 0.642; the planner's own value lost by
the pick 2.19 -> 1.45 pts. In play:

| bot | won | paired |
|---|---|---|
| no simulator, the policy at every window (`--policy-at all`) | 28.8% | -5.5 [-8.7, -2.5] vs tx-t10-fs-rc |
| no simulator, the policy only where the imagined spread is 0.04+ (`--policy-at above`) | 34.0% | -0.3 [-3.1, +2.5] |
| hybrid, the policy at the windows below the gate (`--policy-at gated`) | 50.9% | -8.2 [-11.0, -5.4] vs the 58.7% bot |

Copying the planner's pick better offline does not win games: outside the windows it was trained on it hurts, inside
them it is neutral. The planner's value is the move together with its planned follow-ups; a move-only policy gets none
of the follow-ups.

**More planner data and the judge again**: a second batch of 12,636 games (seed 60001, no key; the bot won 60.6%)
brings the data to 18,673 decided games, 275,318 planned windows and 273,457 judged boards. The judge refit on all of it
(tx-t10-sb2): held-out BCE 0.4748 -> 0.4301, accuracy 0.768 -> 0.798. As `--plan-model` on the test deals: 60.7%, +2.2
[-1.0, +5.4] vs the 58.7% bot (p=0.23). On the fresh deals with one fixed key for both bots (ladder seed 40001,
`--key 23c49785...` = sha256 of "jepa fresh deals 40001": the same shuffles, paired game by game): the 58.7% bot 61.7%
(424-264), sb2 62.5% (430-257), +0.9 [-2.5, +4.2] (p=0.67). Not confirmed; the planner keeps tx-t10's own head. A
better win predictor on the planner's settled boards (+3 accuracy points) moves play by about a point at most.
