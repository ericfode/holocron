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
