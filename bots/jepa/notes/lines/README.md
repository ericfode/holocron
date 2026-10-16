# Line-level JEPA test (2026-10-15/16)

Eric asked whether a JEPA could train on action trajectories ("a meta JEPA"). The day's lesson was that a move and
its follow-ups must be chosen as one unit (category swaps, `--follow-horizon s`, the policy head), so the test asks:
does a predictor conditioned on a whole line (the root move plus its follow-up choices, as the planner plays it) rank
lines closer to their real results than today's one-click model, and does that help the bot without the simulator?

## Data

The 58.7% bot (`jepa_bot.py --model tx-t10 --window-model tx-t10-e --window-horizon s --mix 0 --resource c-clock
--follow-horizon s --score plan --plan-model tx-t10 --plan gate=0.04`) with `--plan-log`, which now also writes each
judged line's action tokens: at each of my choices in the line (the root move first), the chosen option's 62-number
action row and id, encoded where the choice was made. Against c-clock, ladder seed 50001, `--key none`, 6,318 games in
58 minutes (won 60.5%). The earlier seed 50001/60001 logs kept lines only as option indices, so they could not be used.

`line_data.py`: 6,231 decided games, 92,089 planned windows, 1,197,528 judged lines with a real settled board (76% with
follow-up choices). Per window: tx-t10's latent z, and for each root move tx-t10's settle prediction zb (what the bot
without the simulator scores today). Per line: its tokens (at most 4), the latent of the real settled board z_real.

## Offline test (`line_train.py`, `line_root.py`)

tx-t10's encoder (and so the targets) frozen. Line model: action tokens (row + id embedding + position) -> 2-layer
transformer (64 wide) -> masked mean; "line" variant ẑ = z + MLP([z, line]); "resid" variant ẑ = zb + MLP([z, zb, line]).
Loss: error to z_real plus 4x the error after removing each window's mean. 8,000 steps, batches of 256 windows. Held
out: 622 games (9,271 windows). Lines are ranked within their window by tx-t10's value head on ẑ, against the same head
on z_real (the planner's ranking); 95% intervals by game.

| ranking | baseline zb (root move only) | line | resid |
|---|---|---|---|
| lines: top-1 | 0.421 [0.411, 0.432] | 0.686 | **0.701** [0.691, 0.710] |
| lines: Spearman | 0.504 | 0.845 | 0.848 |
| lines: value lost by the predicted top line | 4.14 pts | 0.74 | 0.67 |
| root moves (each worth its best line): top-1 | 0.619 [0.608, 0.629] | 0.779 | **0.782** [0.773, 0.791] |
| root moves: value lost | 1.72 pts | 0.46 | 0.42 |
| latent error (MSE to z_real) | 0.0247 (no change 0.0356) | 0.0052 | 0.0051 |

resid vs baseline: lines top-1 +0.279 [+0.268, +0.291]; root moves top-1 +0.163 [+0.152, +0.175], value lost -1.29
[-1.41, -1.19] pts.

- **Leak check**: the follow-up tokens' rows were read after the root move was played in the simulation. With
  follow-ups reduced to their identity (`--ids-only`): root moves top-1 0.738-0.746 (+0.12), value lost 0.64-0.66 pts.
  Most of the gain stays.
- On the 524 held-out windows without any follow-ups: top-1 +0.05 [+0.01, +0.09].
- Chaining one-step predictions through the follow-ups was not run: the one-click predictor reads board tokens, not
  latents.
- **Root model** (`line_root.py`, for action windows, where the bot without the simulator knows only the root move):
  (z, zb, root token) -> the real settled latent of that root's best line. Root moves top-1 0.700 vs 0.619 (+0.081
  [+0.071, +0.091]), value lost 0.96 vs 1.72 pts.

## Play without the simulator (702 test deals vs c-clock, paired against tx-t10-fs-rc)

`line_models.py` (numpy port, equal to torch within 3e-7). `jepa_bot.py --root-model` scores the moves at action
windows with the root model; `--line-model` scores the options at the follow-up prompts of the move just played with
the resid line model (the line so far plus each option, encoded at the prompt as in the data).

| bot | won | paired vs tx-t10-fs-rc |
|---|---|---|
| tx-t10-fs-rc (today's best without the simulator) | 34.4% | |
| lr-root (root model at windows) | 28.6% | -5.4 [-8.9, -2.0] |
| **lr-line (line model at follow-ups)** | **43.8%** | **+9.6 [+6.6, +12.7]**, p<0.001 (93 vs 27 discordant) |
| lr-both | 38.8% | +4.7 [+0.7, +8.8] |

**Fresh deals** (ladder seed 40001, one fixed key for both bots, so the same shuffles): tx-t10-fs-rc 35.5% (243-443),
lr-line 45.7% (314-373): **+10.2 [+6.9, +13.5]**, p<0.001 (105 vs 35 discordant).

The line model at follow-ups is the biggest single gain for the bot without the simulator so far (31.1% -> 34.4% with
`--follow-horizon s`, -> 43.8% with the line model). The root model ranks root moves better offline but plays worse:
the offline root ranking assumes the planner's best follow-ups, and the windows' choice remains the hard part without
the simulator.

## Commands (desktop; WSL for the games)

```
# data (the 58.7% bot with --plan-log; bot registered locally as gate-logl)
node lab/runners/ladder.js --decks decks/ash-meta-2026-09.json --bots gate-logl --vs c-clock --games 6318 --seed 50001 --key none --id pl1 --out ~/plog/runs --workers 14
python3 bots/jepa/line_data.py --model bots/jepa/models/tx-t10.safetensors --out data/lines/pl1.npz data/plog/pl1
python3 bots/jepa/line_train.py --data data/lines/pl1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/l1
python3 bots/jepa/line_train.py --data data/lines/pl1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/l1ids --ids-only
python3 bots/jepa/line_root.py --data data/lines/pl1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/root1
# play (line_train.py writes <out>-resid.npz next to the .pt, line_root.py <out>.npz; both .npz files are in this folder)
python3 bots/jepa/jepa_bot.py --model bots/jepa/models/tx-t10.safetensors --window-model bots/jepa/models/tx-t10-e.safetensors \
  --window-horizon s --mix 0 --resource c-clock --follow-horizon s --line-model bots/jepa/notes/lines/l1-resid.npz
```

Files: `l1.json` / `l1ids.json` / `root1.json` (all metrics), `l1-resid.npz` (line model), `root1.npz` (root model),
`play-runs.txt` (game logs and paired results). No bot is registered or shipped.

## Inside the hybrid (claude/jepa-lines-hybrid)

The 58.7% bot plus `--line-model bots/jepa/notes/lines/l1-resid.npz`: the line model scores the follow-up prompts the
planner does not plan (planned follow-ups now also join the line, so later prompts see the whole line). 702 test deals:
59.0% vs 58.7%, +0.3 [-2.0, +2.6] (30 vs 28 discordant games, p=0.90). Under the +2 bar, so no fresh-deal run. The
planner already makes most of the follow-ups that matter; the line model's gain is for the bot without the simulator.
