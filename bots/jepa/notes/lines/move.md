# Lines for the move choice at action windows (2026-10-16)

Eric's pick after the line test: use lines to choose the move at an action window for the bot without the simulator.
The bar: lr-line (`--line-model` at follow-ups), 43.8% on the 702 test deals, 45.7% on the fixed-key fresh deals.
At a window the bot knows only the root move; its follow-up options appear after the move is played.

## Offline (`line_move.py`, the held-out 622 games / 9,271 windows of line_train.py's split)

Root moves the planner judged, each worth its best judged line (tx-t10's value head on the real settled boards).
Ranked by:

| scorer | top-1 | real value lost | vs baseline |
|---|---|---|---|
| baseline: tx-t10's settle prediction zb (the bot today) | 0.620 [0.610, 0.630] | 1.72 pts | |
| root model (`line_root.py`) | 0.700 [0.690, 0.710] | 0.96 pts | +0.080 top-1 |
| line model on the root move alone | 0.360 [0.349, 0.371] | 4.78 pts | -0.260 |
| line model, best of the root alone and the root then one card read off the board (units, bases, leaders) | 0.517 [0.505, 0.528] | 2.78 pts | -0.103 |
| the same, units in play only | 0.392 [0.380, 0.404] | 4.20 pts | -0.228 |

Synthesized follow-ups do not work: the line model only learned lines whose follow-ups were real, and the best of
many made-up lines (or a root move with its follow-ups missing) misleads it. Not played.

## Play (702 test deals, without the simulator)

| bot | won | paired vs lr-line |
|---|---|---|
| lr-line | 43.8% | |
| lr-line + the root model at every window (lr-both, earlier) | 38.8% | -5.0 (vs tx-t10-fs-rc +4.7) |
| lr-line + the root model only where the imagined spread is 0.04+, where it was trained (`--root-at above --plan gate=0.04`) | 44.2% | +0.6 [-2.8, +4.1] (75 vs 71 discordant) |

Neither beats lr-line, so no fresh-deal run. The root model's offline gain (+0.08 top-1 against the planner's judged
best lines) does not reach play, as with the policy head and the judge refits before it.

Command (offline): `python3 bots/jepa/line_move.py --lines data/lines/pl1.npz --line-model bots/jepa/notes/lines/l1-resid.npz
--root-model bots/jepa/notes/lines/root1.npz --model bots/jepa/models/tx-t10.safetensors --out runs/lines/move1.json data/plog/pl1`
