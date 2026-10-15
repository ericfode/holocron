# JEPA bot: planning in a learned latent space (tinygrad)

A bot whose moves come from a **Joint Embedding Predictive Architecture** (LeCun, "A Path Towards Autonomous
Machine Intelligence", 2022; I-JEPA / V-JEPA). It learns an embedding of the board and a predictor of *future
embeddings* given an action, then picks moves by imagining futures in that embedding space. It never
reconstructs a board, which is the difference from a generative world model (and from the "world head" of the
Rust and tinygrad learned bots, which predict board numbers directly).

Not to be confused with the Jev bot (`bots/jev/`), which asks TypeSafe's Jev model.

## The model

```
observation ─ state (73) + card tokens (≤32) ─> encoder E ─> z (96)            Ē = EMA copy of E (target encoder)
legal action ─ action (62) + card id ────────> action enc ─> a (64)
[z, a, h]  ─> predictor P ─> ẑ_h = z + P(z, a, h)    trained so ẑ_h ≈ Ē(observation h of my decisions later), h ∈ {1, 4}
z          ─> value V ─> logit "I win from here"
```

- **Encoding is shared** with the Rust learned bot: `features.py` is a line-by-line port of
  `bots/rust-learned/src/features.rs` (state 73, action 62, FNV-1a card/label id in 2048 buckets); on 5,939 real
  decisions the two give the same numbers (max difference 2e-7, f32 rounding) and the same ids. On top of it
  the JEPA reads card tokens: hand, both boards, leaders and bases, each with its id and live stats.
  Card ids are embedded as the sum of three small tables indexed by different functions of the bucket,
  because a 2048-row gather is a one-hot mask in tinygrad.
- **Training data is shared** too: the "swu-traj/1" games written by `lab/learn/collect.js`
  (`/mnt/project-files/learn/README.md`). The targets are the same seat's next recorded decision (+1) and
  fourth next (+4) in the same game, so the latent future includes the opponent's replies.
- **Losses** (`train.py`), in two stages:
  1. JEPA prediction `‖ẑ_h − sg(Ē(x_{t+h}))‖²` plus VICReg variance and covariance terms on z so it cannot
     collapse. With `--w-value 0` (the default) the encoder learns from this self-supervised loss only.
  2. The value head, either `--value-mode frozen` (V alone on frozen z, ẑ_1, ẑ_4) or `--value-mode predictor`
     (V, predictor and action encoder fine-tuned together on `V(ẑ)` against the outcome while the JEPA loss
     keeps the predictor on target, as in EfficientZero), early-stopped on held-out games.

  Why two stages: v1 trained the value head through the encoder, and it memorised outcomes (a deck's leader
  and base nearly name a training game); its held-out value loss was best at step 500 and then rose.
- **Planning** (`jepa_bot.py`): for each legal move, `score = (1 − mix)·σV(ẑ_1) + mix·σV(ẑ_4)`; best score wins
  (`--temp` samples instead). A loop guard stops it repeating a pick when the same observation keeps coming back.
- **Probes**: after training, ridge regression from z to readable numbers (base HP, hand, board power, ...).
  They only explain the latent on the dashboard ("what it imagines"); they play no part in choosing moves.

Training is tinygrad (CPU). Play is numpy only (`check_parity.py` checks the two forward passes agree to 1e-6),
so the bot starts fast and needs no tinygrad.

## Commands (from the repo root)

```bash
python3 -m pip install tinygrad numpy           # training only; play needs numpy
node lab/learn/collect.js --games 2000 --seed 200000 --workers 4 --out data/traj/rr --bots random-a,random-b
node lab/learn/collect.js --games 1200 --seed 210000 --workers 4 --out data/traj/rush-random --bots rush,random-a
node lab/learn/collect.js --games 800 --seed 220000 --workers 4 --out data/traj/rush-rush --bots rush,rush#2
python3 bots/jepa/data.py --out data/jepa/mix-v1.npz data/traj/rr data/traj/rush-random data/traj/rush-rush
python3 bots/jepa/train.py --data data/jepa/mix-v1.npz --out bots/jepa/models/jepa-v1
python3 bots/jepa/check_parity.py --model bots/jepa/models/jepa-v1.safetensors --data data/jepa/mix-v1.npz
node lab/learn/eval.js --bots jepa,random-a --games 100 --workers 4
python3 bots/jepa/panel.py --thoughts /tmp/jepa-thoughts.json      # dashboard panel (needs /mnt/project-files)
```

Registered bots (`bots/external-bots.json`, `lang: python`): `jepa` (v1, mix 0.5), `jepa-h1` (v1, mix 0, next
decision only) and `jepa-pure` (v2p, the pure-JEPA encoder). `SWU_JEPA_THOUGHTS=<file>` makes the bot write its
latest decision for the panel. Card data is read from `$SWU_CARD_DATA` (default `forceteki/test/json`).

**Use the ladder, not `eval.js`, to measure strength against rule bots.** `lab/learn/eval.js` and `collect.js`
build each bot once per worker and reuse it across games. Rush keeps a loop-guard map of positions it has seen,
so in later games it thinks it is looping and passes early. Head-to-head numbers against rush from `eval.js` are
too kind to the other bot (jepa looked 41-18 there and is 2-8 on the ladder). `lab/runners/ladder.js` builds fresh bots
for every game.

## Results

Ladder `jepa-ladder-1` (`/mnt/project-files/results/jepa-ladder-1`): 6 bots, 10 games per pair, seeds from both
seats, 150 games, 1 engine error.

| Bot | BT Elo | Record | ms / decision |
|---|---|---|---|
| rust-greedy2 | 2081 | 49-1 | 3.2 |
| rush | 1661 | 35-15 | 0.15 |
| jepa-h1 | 1491 | 26-24 | 9.3 |
| jepa | 1422 | 22-28 | 10.3 |
| jepa-pure | 1276 | 13-36 | 12.5 |
| random | 1069 | 4-45 | 0.01 |

jepa beats random 9-1, loses to rush 2-8 and to rust-greedy2 0-10. jepa-h1 beat jepa 7-3; jepa beat jepa-pure 8-2.

Model versions (`models/*.train.json` hold the training logs; safetensors for v1, v2 and v2p):

| Model | Recipe | Held-out value acc. | vs rush (eval.js) | vs rust-greedy2 (eval.js) |
|---|---|---|---|---|
| v1 (`jepa`, `jepa-h1`) | V trained with the encoder, step-500 checkpoint | 0.702 | 41-18 | 2-57 |
| v2 | encoder on JEPA loss only, V on frozen latents | 0.719 | 10-29 | 1-37 |
| v2p (`jepa-pure`) | v2, then predictor + action encoder + V tuned on V(ẑ) | – | 29-30 | – |
| v3 | as v2, plus 1500 rust-greedy2 games | 0.738 | 11-49 | 0-60 |
| v3p | v3, then predictor + V tuned | – | 12-47 | 2-58 |
| v1p | v1, then predictor + V tuned (encoder frozen) | – | 6-53 | – |

The eval.js columns are against the handicapped rush (see above): compare rows with each other only.

**Lesson: better at predicting the winner is not better at choosing moves.** The only label is who won. Every
later version learned "who is ahead" better (up to 74% on unseen games) and played worse. Choosing a move needs
the difference between moves from one position, and the outcome label says almost nothing about that, least of
all in lopsided games (adding rust-greedy2 games made it worse). The latent is fine: linear probes read the board
back with R² 0.95 to 0.99. The weak part is the score on imagined futures, and the test below traces that to the predictor.

## Which part is weak (oracle test)

Swap one part for a perfect stand-in and see what changes. Protocol v2 lets a bot play moves on a private copy of
the game (`sim`), so `jepa_bot.py --score` can replace the predictor's imagined future with the real one:

- `--score sim-v` (`jepa-sim-v`): play each move on the copy, then score the real next position with the same
  encoder and value head. A perfect predictor.
- `--score sim-eval` (`jepa-sim-eval`): the same real position, scored by the position-evaluation thread's
  `linear-deck-g4` (`lab/eval`) through `eval_helper.js`. A perfect predictor and a better judge.
- `--log <file>` with any score mode writes all three score lists for every action window, and
  `oracle_report.py` compares them.

Inside a simulation the opponent plays like rush (the training data's main opponent; a stand-in that always
passed made Pass look best). `--judge round` (default) plays both seats rush-style to the end of the round's action
phase and scores my first decision after it; `--judge window` scores my next action window, which favours Pass and
Claim Initiative because they get judged after the next draw. Moves that change nothing (a cancelled click) score 0.
Simulations are only allowed at action windows, so the other 63% of decisions (targets, cards, resources) still
use the imagined score, and a 2.5 s guard falls back to it when time runs short.

```bash
python3 bots/jepa/oracle_report.py jepa-h1.jsonl --json report.json
```

Results on jepa-h1's own action windows (about 2,600 per run; ladders `jepa-oracle-1-window` and
`jepa-oracle-2` in `/mnt/project-files/results`):

| Comparison | run 1 (window): agree / chance, ρ | run 2 (round): agree / chance, ρ |
|---|---|---|
| imagined vs real, same value head | 16% / 25%, −0.44 | 48% / 38%, 0.46 |
| imagined vs real, evaluator | 15% / 25%, −0.50 | 31% / 36%, −0.18 |
| value head vs evaluator, both real | 63% / 25%, 0.97 | 59% / 36%, 0.77 |
| score spread over a position's moves, imagined / real | 3.3 / 16.9 pts | 3.0 / 4.2 pts |

*Agree* = both rank the same move first; ρ = Spearman over one position's moves, median over positions.

**The predictor is the weak part.** The encoder holds the board and the value head ranks real futures like the
fitted evaluator. The imagined futures barely differ between moves, and their ranking is near or below chance. The
likely cause is the data: each game shows one move per position, so the predictor learns roughly the average
future. A better predictor should raise imagined-vs-real agreement toward the value-head-vs-evaluator level.

Play does not separate the parts yet: the test bots were +83 / +161 Elo over jepa-h1 in run 1 and −110 / −160 in
run 2, inside the ±100 noise of 10 games per pair, because most of their decisions still come from imagination.
Next: train the predictor on simulated branches (every legal move from sampled positions) and re-run the
comparison.

## Training the predictor on branches (v1b)

Eric's pick after the oracle test. `branches.js` plays rush and random games and, at a third of the action windows
(the only place the engine rolls back exactly), plays every legal move on the same game with rollback, then both
seats play on until the mover's next and 4th next decision. `branch_train.py` fine-tunes the predictor and the
action encoder on those futures, with the encoder and value head frozen: the plain error plus the error after
subtracting each position's mean over its moves (the part that tells moves apart), mixed with recorded games.

```bash
node bots/jepa/branches.js --games 1000 --workers 4 --seed 700000 --bots rush,random --out data/branch/rush-random
node bots/jepa/branches.js --games 800 --workers 4 --seed 710000 --bots rush,rush --out data/branch/rush-rush
python3 bots/jepa/branch_train.py --model bots/jepa/models/jepa-v1.safetensors --branches data/branch/rush-random \
    data/branch/rush-rush --data data/jepa/mix-v1.npz --cache data/jepa/branches-v1.npz --out bots/jepa/models/jepa-v1b
```

1,800 games gave 30,417 branch points (about 5 moves each) in 40 minutes; 1% of games ended early on engine errors
after a rollback (known engine bug 6 in the repo CLAUDE.md, plus bug 7). v1b and the numbers below predate
`--w-terminal`: moves that end the game before their target (2% before the next decision, 8% before the 4th) were
left out of training and of the held-out comparison; both now use the result. On 2,983 held-out branch points the
imagined ranking of moves got much closer to the real one:

| Score of a move vs the real future | v1 | v1b |
|---|---|---|
| next decision: median ρ, top-1 agree (chance 31%) | 0.43, 43% | 0.69, 61% |
| 4 decisions on: median ρ, top-1 agree (chance 30%) | 0.40, 38% | 0.50, 43% |

On the bots' own action windows in a ladder (`results/jepa-branch-2`, judged after the round as in the oracle
test), v1b's ranking also agrees with `linear-deck-g4` on the real future (ρ 0.40, top-1 53% vs chance 48%) where
v1's did not (ρ −0.16, 34% vs 38%).

**It plays worse.** `jepa-branch-2` (10 games per pair): jepa-h1 1542 (29-31), jepa-b (v1b, mix 0.5) 1431,
jepa-h1b (v1b, mix 0) 1378 (19-41); jepa-h1 beat jepa-h1b 9-1. v1b also changed the prompts branches cannot cover
(same pick as v1 in 24% of resource prompts, 70% of target prompts, 48% of action windows), so `jepa-h1w` uses v1b
in action windows only (`--window-model`). `jepa-branch-3` (20 games per pair): jepa-h1 1414, jepa-h1b 1299,
jepa-h1w 1278; jepa-h1 beat jepa-h1w 13-7 and jepa-h1b 14-6. So the window choices themselves got worse.

**Lesson: a predictor that tracks the real next position better does not make this planner stronger.** The
yardstick from the oracle test (imagined-vs-real agreement) rose and play fell. This fits the oracle runs, where the
perfect predictor (`jepa-sim-v`) was not clearly stronger either. What limits the bot is the planning itself: one
move scored by V a short way ahead, while 63% of decisions are follow-up and resource prompts it plans no further.
jepa-h1 (v1) stays the JEPA entry.

## Planning whole moves (jepa-plan)

`--score plan` (registered as `jepa-plan`: model v1, mix 0) plans each action window on the referee's copy of the game
(protocol v2 simulations). Every candidate move (the 16 best by the imagined score, plus Pass) is played together with
its follow-up choices: at each of my follow-up prompts (targets, cards, options) the best 6 options by the imagined
score each get a line of their own, 3 at the second level, the greedy choice below that. The opponent's prompts inside
my move are played like rush. A line stops where the move has settled: anyone's next action window, the end of the
action phase, or the end of the game. The value head scores that real position (an opponent-to-act position is read as
my action window, the same way for every move); a move's score is its best line. The chosen line's follow-up choices
are replayed at the real follow-up prompts while the prompt matches; resource prompts and anything else use the
imagined score.

```bash
node lab/runners/ladder.js --bots jepa-plan,jepa-h1,rush,rust-greedy2,h@linear-deck-g4 --games 20 --workers 4 --seed 860000 --id jepa-plan-1
```

Result (`results/jepa-plan-1`, 20 games per pair, random decks, seats alternate):

| Bot | W-L | BT Elo | vs jepa-plan |
|---|---|---|---|
| rust-greedy2 | 63-17 | 1723 | 17-3 |
| h@linear-deck-g4 | 60-20 | 1693 | 16-4 |
| rush | 37-43 | 1483 | 9-11 |
| **jepa-plan** | 33-47 | 1446 | |
| jepa-h1 | 7-73 | 1155 | 5-15 |

Planning whole moves lifts the bot by about 290 Elo: it beats jepa-h1 15-5 and rush 11-9, where jepa-h1 went 0-20
against rush in the same run (3-17 and 2-8 in the branch runs). It planned all 2,014 of its action windows, 9.6 lines
and 0.32 s each (no window ran out of time); 1,308 follow-up prompts were answered from the plan, 29 plans were dropped
because the real prompt differed, and 2,288 resource prompts plus about 200 other prompts used the imagined score.

So the planning scope was the main limit. h@linear-deck-g4 plans the same way (each move with its first follow-up
choices, judged where the move settles, `bots/players/heuristic.js`) and answers the other prompts with hand-written
rules; it also runs inside the engine, so its lookahead sees the real hidden cards. The remaining gap (about 250 Elo)
therefore sits in the scorer (value head against the fitted linear-deck evaluator) and the unplanned prompts, mostly
resources, which simulations cannot reach (sims are allowed only in action windows). A run of the same planner scored
by the linear-deck evaluator would measure the scorer's share. jepa-plan was then the JEPA entry (now jepa-plan-r, below).

## Learning from recorded games (jepa-plan-r)

The real-deck gauntlets left thousands of recorded games between strong bots. `from_replays.js` turns them into
training rows: each game is played again on the engine from its header (decks, seed, key), and at every recorded
decision with more than one legal action the acting seat's view, prompt and legal actions are written as
`collect.js` writes them for live games, with the recorded choice. A game that drifts from its recording is dropped
(none did).

```bash
R=/mnt/project-files/human-meta/realdeck; L=/mnt/project-files/results
node bots/jepa/from_replays.js --out data/traj/replays --workers 4 $R/ash-gauntlet-cclock-1 $R/ash-gauntlet-cclock-2 \
  $R/ash-gauntlet-ismcts-1 $R/ash-heuristic-1 $R/ash-h4-1 $R/ash-learned-vh-1 $R/ash-rust-search-1 $R/ash-ismcts-1 \
  $L/atlas-map-1 $L/eval-ladder-6 $L/eval-ladder-7 $L/eval-ladder-8
python3 bots/jepa/data.py --out data/jepa/replays.npz data/traj/replays
python3 bots/jepa/resource_policy.py fit --out bots/jepa/models/resource-v1.json data/traj/replays
```

Data: 7,840 games (1,003,147 decisions, 687 distinct deals) from 12 runs, mostly the real-deck gauntlets of c-clock,
heuristic, h4, learned-vh, rust-search and ismcts.

**Better value heads did not play better.** On held-out games of the new data:

| Model | Recipe | Brier | Accuracy |
|---|---|---|---|
| v1 | as before (3,480 random-deck games) | 0.203 | – |
| v1r | v1, value head refit on the new data (`--init`, `--steps 0`) | 0.171 | 0.733 |
| v4 | trained from scratch on the new data (8,000 + 6,000 steps) | 0.146 | 0.786 |

Played as the planner's scorer, none of them moved: jepa-plan 12.1%, with v1r 13.7%, and with the fitted
linear-deck-g4 evaluator as scorer 16.4% (all against c-clock, below).

**The leak was resourcing.** The planner only plans action windows; the resource prompts used the imagined score,
which often skipped resourcing. In sample games jepa-plan had 4.3 resources at round 5, c-clock 6.0.
`resource_policy.py` copies the resource choices of c-clock and rust-search in the recorded games: a conditional
logit over the offered hand cards (cost bands, card type, off-aspect, second copy, space, and a weight per card seen
at least 30 times) and a logistic model for "resource nothing" in the regroup phase. On held-out games it picks the
teacher's card 66% of the time (features only 64%, a hand rule 64%, chance 22%) and the stop choice 97.5%.
`--resource <model.json>` uses it at every resource prompt; `--resource rule` uses the hand rule (heuristic.js's
keep score, resource every time) as an ablation.

Fresh deals against c-clock (27 real decks from `decks/ash-meta-2026-09.json`, seats alternate, one secret key
for every run, so each bot plays the same deals; these deals are outside the gauntlets the models learned from):

| Bot | Wins | Paired with jepa-plan-r (same deals) |
|---|---|---|
| **jepa-plan-r** (v1 + resource-v1) | 266/694 = 38.3% ± 3.6 | |
| jepa-plan-rr (v1 + hand rule) | 247/693 = 35.6% ± 3.6 | r alone won 71, rr alone 53 |
| jepa-plan-r4 (v4 + resource-v1) | 149/458 = 32.5% ± 4.3 (stopped) | r alone won 68, r4 alone 50 |
| jepa-plan-eval (scorer linear-deck-g4) | 28/171 = 16.4% ± 5.5 (stopped) | |
| jepa-plan-v1r (v1r) | 39/284 = 13.7% ± 4.0 (stopped) | |
| jepa-plan (v1) | 32/264 = 12.1% ± 3.9 (stopped) | r alone won 82, jepa-plan alone 6 |

Standard bot test (`npm run realdeck:test -- --bot jepa-plan-r`, 702 games vs c-clock):
35.2% [31.7, 38.8], Elo −106; between lisp (37.7%) and h@linear-deck-g4 (33.2%). Its deals overlap the
gauntlets the resource model learned from, so the fresh-deal number above is the cleaner one.

In 60 recorded games against c-clock (`--record`, 30 per bot), jepa-plan had 3.4 resources when round 3's action
phase started and 4.3 at round 5, where c-clock had 4.0 and 6.0; jepa-plan-r had 4.0 and 6.0.

Random decks (`results/jepa-plan-r-1`, 20 games per pair, seats alternate):

```bash
node lab/runners/ladder.js --bots jepa-plan-r,jepa-plan,rush,rust-greedy2,h@linear-deck-g4 --games 20 --workers 4 --seed 870000 --id jepa-plan-r-1
```

| Bot | W-L | BT Elo | jepa-plan-r vs it |
|---|---|---|---|
| h@linear-deck-g4 | 55-25 | 1613 | 7-13 |
| rust-greedy2 | 48-32 | 1559 | 11-9 |
| **jepa-plan-r** | 44-36 | 1529 | |
| rush | 27-53 | 1403 | 13-7 |
| jepa-plan | 26-54 | 1395 | 13-7 |

So the resource picker learned on real decks carries over to random decks (about +130 Elo over jepa-plan).

So resourcing at all is most of the gain (12% to 36%), and learned picks add about 3 points over the hand rule.
The new value head trained on strong-bot games (v4) plays worse than v1 with the same resource model, although it
predicts the winner better. jepa-plan-r is the JEPA entry.

## Scoring the plans with the fitted evaluator (jepa-plan-reval)

`jepa-plan-reval` is jepa-plan-r with linear-deck-g4 (`lab/eval/`) scoring the planner's settled positions in place of
the value head. On the same fresh deals as above it wins 337/691 = 48.8% ± 3.7 against c-clock (on the 690 games both
played, jepa-plan-reval alone won 120 and jepa-plan-r alone 49). Standard bot test: 47.2% [43.5, 50.9], Elo −20,
level with rust-search (48.8%) and the c-clock family (49 to 52%).

Without the resource picker the same scorer gave 16.4% (jepa-plan-eval), so the two limits were stacked: first
resourcing, then the scorer. With resourcing fixed, the value head costs about 10 points against c-clock. The JEPA
parts left in jepa-plan-reval are the candidate order (the 16 best moves by the imagined score), the follow-up
branching, and the prompts the planner does not reach. jepa-plan-r stays the entry whose positions the JEPA judges
itself; jepa-plan-reval is the strongest bot built on it.

## Teaching the value head to rank moves (jepa-v1k, jepa-v1d)

The planner keeps the move whose settled position V scores highest, so V has to order the positions one window's
moves reach. `rank_data.js` replays recorded games of c-clock and rust-search (the teachers) and, at 15% of their
action windows, plays up to 16 candidate moves on the referee's copy the way the planner does: each move, up to 4 of
its first follow-up options, then random choices until it settles. The teacher's line is the real game up to the same
point. `rank_train.py` fits V on frozen v1 latents with a softmax per window that puts the teacher's position first,
plus an outcome term (`--target rank`), or trains V to copy linear-deck-g4's score at every position
(`--target eval`).

    node bots/jepa/rank_data.js --out data/rank/v1 --workers 4 --p 0.15 <run dirs>   # --skip DIR carries on a stopped run
    python3 bots/jepa/rank_train.py prep --data data/rank/v1 --out data/jepa/rank-v1-ev.npz --eval linear-deck-g4 --eval-all
    python3 bots/jepa/rank_train.py fit --data data/jepa/rank-v1-ev.npz --out bots/jepa/models/jepa-v1k --epochs 30
    python3 bots/jepa/rank_train.py fit --data data/jepa/rank-v1-ev.npz --target eval --hidden 256 --epochs 60 --out bots/jepa/models/jepa-v1d

Data: 2,776 games (the run stopped at a time limit after 35% of the 7,916 recorded games), 14,392 windows, 155k
settled positions; 10% of games held out (1,414 windows). Play: 702 fresh-deal games against c-clock, as above.

| Scorer of the planned positions | Picks the teacher's move | Same move as linear-deck-g4 | Wins vs c-clock |
|---|---|---|---|
| v1 value head (jepa-plan-r) | 40.1% | 56.5% | 266/694 = 38.3% |
| ranking head v1k, plans only (jepa-plan-rkp) | 63.6% | 59.0% | 263/689 = 38.2% |
| ranking head v1k everywhere (jepa-plan-rk) | 63.6% | | 248/690 = 35.9% |
| evaluator copy v1d, plans only (jepa-plan-rd) | 45.8% | 76.8% | 262/690 = 38.0% |
| linear-deck-g4 (jepa-plan-reval) | 50.1% | 100% | 337/691 = 48.8% |

The first two columns are held-out windows. `--plan-model` scores only the planner's positions with the second model
and leaves every other prompt to v1; jepa-plan-rk uses v1k for those prompts too and loses a little.

- The ranking head learned what it was taught: it picks the teacher's move 64% of the time against 40% for v1 and 50%
  for linear-deck-g4. That is no artifact of the teacher's line being the real game: with the teacher's move played on
  by random choices like the other lines (`prep --teacher-line alt`), v1k still picks it 62.5%.
- Play did not change. jepa-plan-rkp and jepa-plan-r won the same games to within one (89 against 88 games only one of
  them won). Agreement with strong bots on held-out windows does not predict strength; the branch fine-tune (v1b)
  showed the same.
- The copy of the evaluator does not play like it either. In 60 logged games (a scratch copy of the bot that scores
  each planned window with all three), it picks linear-deck-g4's move in 74% of real windows (v1: 59%), so the planner's
  own positions are not out of distribution, and it still plays at 38.0%. The 10 points sit in the 1 window in 4 where
  even a close copy disagrees.
- The latent is the limit for scoring. A head on the encoder's 73 raw state features alone (`fit --input state`, an
  offline check that jepa_bot.py cannot load) copies the evaluator better than any head on z (85.8% same move) and
  ranks better (68.6% teacher moves); z next to the raw features adds nothing. v1's 96 numbers drop details the
  scorer needs, and no training target for the head brings them back.
- v1k's level drifts (Brier 0.264 on the teacher's positions, base rate 0.222) because ended games and no-op moves sit
  in the softmax with fixed scores. `--live-only --w-outcome 1` keeps V a win estimate (Brier 0.158, better than v1's
  0.175) at 61.9% teacher moves. The planner only compares, so the drift does not affect play.

jepa-plan-reval stays the strongest JEPA bot. A better JEPA scorer needs an encoder that keeps those details, for
example one trained with the ranking or copy loss flowing into it; a new target for the head on v1's latent is
unlikely to help.

## Transformer JEPA: moves as tokens, no simulator (jepa-tx)

The planners above need a simulator to see where a move goes. This bot does not: the game only lists the legal moves,
the model imagines where each one leads, and the best imagined future wins. The engine is used for legality alone.

```
[state] [≤24 card tokens] [move tokens: one per legal move and horizon]  ─> 2 transformer layers (tx_model.py)
  context tokens see each other; a move token sees the context and itself, so it attends to the cards it touches
z    = readout(state token, mean of card tokens, raw state)
ẑ_h  = z + P([z, move token_h])          h ∈ {1, 4, s}: next decision, 4th next, and the board once the move has settled
```

- **Settle horizon** (`--settle`): about 45% of "next decision" targets are halfway through a move (choose a target,
  pay a cost), so ẑ_1 judges half-moves. The third move token learns the board where the move has settled
  (`branches.js` records it as `st`): the position the simulating planner judges.
- **Data**: `branches.js --decks` plays rush against rush on the 27 real decks; at sampled action windows it plays
  every legal move (up to 12) on the same game and records each one's futures at h1, h4 and settled. Training on every
  legal move is what made the predictor rank moves (53% -> 67% like the real futures); the pooled twin did as well
  on 55k points, so the data did it there. On 618k points only the transformer kept improving (below).
- **Losses** (`tx_train_torch.py`): the JEPA prediction and VICReg terms of train.py on 7,840 recorded games, plus on
  branch points the error of every move's imagined future, the error after removing each point's mean (what tells the
  moves apart) and its size. The held-out line reports `moves_explained_h1/h4/settled` = 1 - (move-separating error /
  how much the real futures differ): higher is better. `--pack-e --w-eval 1` adds a head that copies linear-deck-g4 on
  settled positions, with its gradient reaching the encoder.
- **Evaluator head** (`fit_veval.py`, models ending in `-e`): a value head refit to copy linear-deck-g4's score of
  settled positions (the rank data), on the frozen encoder. The bot uses it at action windows only
  (`--window-model <m>-e.safetensors --window-horizon s`): the raw model answers every other prompt.
- **Fixed judge** (`judge_prep.py`, `yardstick.py --judge`): each model's own value head judging its own imagined
  futures makes models incomparable, so every model is graded by linear-deck-g4's score of the real futures on one test
  set (3,000 games, seeds 740000-742999, none trained on). top-1 = picks the move whose real future the judge rates
  best; regret = judged win chance lost by playing the imagined best; blunders = regret above 5 points.
- **Scoring in chunks**: attention over ~2,000 legal moves at once timed out the 10 s decision limit in 6-15% of games;
  `NumpyTx.predict` scores 256 moves at a time (no timeouts since).

Commands (from the repo root; the big run used Eric's desktop, RTX 4090, 20 workers):

    node bots/jepa/branches.js --games 3000 --workers 20 --seed <750000 + 3000*i> --bots rush,rush --decks decks/ash-meta-2026-09.json --out data/branch/st-<i>
    python3 bots/jepa/branch_prep.py --procs 8 --out data/jepa/st-<i>.npz data/branch/st-<i>
    python3 bots/jepa/pack_data.py --branches data/jepa/st-<i>.npz --out-dir packs --name b-<i>        # ~50 MB per part
    python3 bots/jepa/pack_data.py --replays data/jepa/replays.npz --rank data/jepa/rank-v1-ev.npz --tok data/jepa/rank-v1-tok.npz --out-dir data
    python3 bots/jepa/branch_prep.py --out data/jepa/test.npz data/branch/test     # test set: branches.js --seed 740000, same flags
    python3 bots/jepa/pack_data.py --branches data/jepa/test.npz --out-dir data/jepa --name test-b
    python3 bots/jepa/judge_prep.py --branches data/jepa/test.npz --out data/jepa/test-judge.npz data/branch/test
    python3 bots/jepa/tx_train_torch.py --arch tx --settle --pack-r data/pack-r.npz --pack-b packs/b-0.npz ... packs/b-9.npz \
        --pack-e data/pack-e.npz --w-eval 1 --steps 30000 --test-pack data/jepa/test-b.npz --test-judge data/jepa/test-judge.npz --out runs/tx-s10a
    python3 bots/jepa/fit_veval.py --model runs/tx-s10a.safetensors --out runs/tx-s10a-e.safetensors --rank data/jepa/rank-v1-ev.npz --tok data/jepa/rank-v1-tok.npz
    python3 bots/jepa/yardstick.py runs/tx-s10a-e.safetensors data/jepa/test-b.npz --judge data/jepa/test-judge.npz
    python3 bots/jepa/monitor.py --data-logs "data/branch/st-*.log" --run-logs "runs/*.txt" --parts 10 --games 3000   # progress page on :8765

Registered bots: `jepa-tx` (tx-s10a, mix 0, tx-s10a-e at action windows on the settled board, resource-v1) and
`jepa-h1r` (v1, mix 0, resource-v1: the baseline below).

### Results

Play: 702 games against c-clock on the 27 real decks, all bots on the same deals, resource-v1 for every bot. Paired =
win-rate difference against jepa-h1r on the same games, 95% bootstrap interval over seeds. Fixed judge: the `-e` model's
settled horizon (hs) on the test set (chance 0.401). Data: 10 parts of 3,000 games, 618,019 branch points.

| Bot | Model | Fixed judge hs: top-1 / regret / blunders | Wins vs c-clock | Paired vs jepa-h1r |
|---|---|---|---|---|
| **jepa-tx** (tx-s10a-c) | tx, 10 parts, copy loss; -e at windows only, mix 0 | 0.803 / 0.60 pts / 3.5% | **28.4%** [25.2, 31.9] | **+13.8** [+10.3, +17.5] |
| tx-s10a-d | same, mix 1 | | 27.5% | +12.9 |
| tx-s10-a | tx, 10 parts; -e everywhere, mix 1 | 0.799 / 0.64 / 3.8% | 26.4% | +11.7 |
| tx-s3-a | tx, 3 parts; -e everywhere, mix 1 | 0.761 / 0.76 / 4.7% | 20.1% | +5.6 |
| tx-s10a-b | tx, 10 parts, raw head on the settled board | 0.667 / 1.17 / 6.9% | 11.9% | -2.6 |
| jepa-h1r | v1 (pooled, recorded games), mix 0 | | 14.6% [12.1, 17.4] | reference |
| pool-10-d | pooled twin, 10 parts (no settle token) | | 5.5% | -9.0 |

Training on the RTX 4090: tx-s10 29 min, tx-s10a 37 min, pool-10 19 min (30,000 steps each). Held-out
moves_explained h1 / h4 / settled: tx-s10 0.858 / 0.548 / 0.757, tx-s10a 0.845 / 0.506 / 0.784. The full table of 41
game tests and the logs behind this section are in `notes/round2/`.

- **The first no-simulator JEPA bot clearly above v1.** jepa-tx won 128 games jepa-h1r lost and lost 33 it won.
  The simulating planners are still stronger (jepa-plan-r 38.3%, jepa-plan-reval 48.8%).
- **More branch data helps the transformer**: the same recipe on 3 parts against 10 parts, +6.2 points
  [+2.6, +9.9]. It hurts the pooled twin: its losses and value head improved, but it ranks moves worse on the fixed
  judge (h4_vs_settled 0.614 -> 0.555; tx-s10 0.680) and plays at about 5%. The transformer is the one to keep.
- **The settled board decides it.** The raw value head on the settled board plays no better than v1 (11.6-14.5%); the
  evaluator head on the same imagined board adds 12-16 points. The fixed judge's hs score tracks the win rate across
  tx-s3, tx-s10 and tx-s10a.
- **The copy loss shapes the encoder**: fit_veval's same_as_eval 0.786 -> 0.838 and every window number on the fixed
  judge improves. In play it is +2.3 points over tx-s10-a [-1.2, +5.8], within noise, and with it the evaluator head
  belongs at action windows only (-e everywhere: 23.0%).
- The evaluator head on the NEXT decision is a disaster (v1-e mix 0: 0.1%): it rates half-moves as if settled.

**On-policy check** (`notes/round2/onpolicy.txt`): 60 logged games each against c-clock, and at every one of the
bot's own action windows the referee's copy plays each legal move to the end of the round for linear-deck-g4 to judge.
jepa-tx picks the judge's best move at 50% of its windows (chance 41%), v1 at 37% (chance 35%). Mean regret is the
same for all three bots tested (3.5-3.9 points, blunders 21-23%), far above the 0.6 points on the test set. Likely
cause: this judge scores one rush-style playout per move to the end of the round, so it is noisy, and the best of
several noisy scores sits above the truth; regret then measures the judge's noise as much as the bot. jepa-tx's misses are rarer but no
smaller. Prompts outside action windows (about 45% of decisions: targets, options, triggers) have no simulations and
are not judged.

## Round tiers and macro actions

Eric's question (2026-10-15): the bot plans one move ahead; would it play better with a few coarser horizons, where a
macro action stands for a set of moves and bounds the card choices over several turns? Hierarchical JEPA work says
yes when the high-level choice is a small fixed set (H-JEPA arXiv 2610.06805, HWM arXiv 2604.03208, Hi-LeWM arXiv
2607.12547: a hierarchy helps only with a constrained high-level search). So this adds three tiers and three macros:

```
tier 1  s     the board once this move has settled                                  (the jepa-tx horizon)
tier 2  r     the board when this round's action phase ends, if I play the move and then the round in style m
tier 3  r2    the board when the next round's action phase ends (after tier 2, both seats play as rush)
macros  face  rush: biggest card first, attack the base       trade  the same, attack enemy units first
        hold  no more cards this round: claim the initiative when free, else pass
```

- **Data** (`branches.js --macros face,trade,hold --macro-moves 4 --max-branch 0`, `macros.js`): at sampled action
  windows, 4 moves (the main line and 3 at random) are each played 3 times, once per macro, to the end of this round
  and of the next (`rd`, `rd2`). The macros of one move share the engine seed, so they differ by the style alone.
  `tier_prep.py` encodes the boards; with `--eval` it also judges them (a test set for `yardstick.py --tiers`).
  On 4 smoke-test games, a fourth style (wide: cheapest card first) gave the same round as face for most moves and
  was best for 2 of 205, so it is left out. With face, trade and hold, the macro moved the judged round result by more
  than 1 point for 40% of moves (the rest are mostly late in the round, where little is left to play).
- **Model** (`tx_model.py`, `tx_train_torch.py --tier-pack`): one learned row per (tier, macro) added to the move
  token, so each move gets 3 + 6 tokens that all attend to the cards. Trained with the branch losses, the (move,
  macro) lines of a point standing in for the moves. Held-out lines: `moves_explained_r/r2` and
  `macros_explained_r/r2` (the macros of one move told apart). `NumpyTx.forward` now computes move tokens beside the
  context (same numbers, 6x faster on a 2,000-option prompt) and `predict` runs only the group of horizons it needs.
- **Bot** (`jepa_bot.py --tiers s=1,r=1,r2=1 [--commit-macro]`): at action windows a move is worth the weighted mean
  of its settled score and its best macro's round scores; `--commit-macro` keeps the round's first macro for the rest
  of that round, so later moves serve the same plan.
- **Yardstick** (`yardstick.py <model> --tiers <tier test>`): per tier, the (move, macro) lines against the judged real
  round ends, how often the imagined best macro is the real best, and the move picked by the tier against the move
  the settled horizon picks, each judged by its best real line.

Commands (Eric's desktop): data `node bots/jepa/branches.js --games 2000 --workers 20 --seed <790000 + 2000*i> --bots
rush,rush --decks decks/ash-meta-2026-09.json --p 0.25 --max-branch 0 --macros face,trade,hold --out data/branch/tier-<i>`,
then `python3 bots/jepa/tier_prep.py --procs 8 --out data/jepa/tier-<i>.npz data/branch/tier-<i>` and
`python3 bots/jepa/pack_data.py --branches data/jepa/tier-<i>.npz --out-dir packs --name t-<i>`; test set seeds 745000+
with `tier_prep.py --eval linear-deck-g4`; training adds `--tier-pack packs/t-0.npz ... --tier-test data/jepa/tier-test.npz`
to the jepa-tx command above.

Results (desktop run, `notes/tiers/`; 3 parts, 88,545 tier points; test set 500 games at seed 745000): tx-t10 = the
tx-s10a recipe plus the tiers. The macros are learned: the imagined best macro is the judged best 77% of the time at
the round end (chance 44%). Played vs c-clock on the usual 702 deals, paired against jepa-tx (28.4%):

| tx-t10 variant | Wins vs c-clock | Paired vs jepa-tx |
|---|---|---|
| (a) jepa-tx's settings, no tiers at play | **31.1%** [27.7, 34.6] | +2.6 [-0.9, +6.2] |
| (b) `--tiers s=1,r=1` | 30.6% | +2.1 [-1.8, +5.9] |
| (c) `--tiers s=1,r=1,r2=1` | 28.6% | -0.1 [-3.7, +3.4] |
| (d) (c) + `--commit-macro` | 29.0% | +0.3 [-3.3, +3.8] |
| (e) `--tiers r=1,r2=1` (no settled score) | 24.6% | -4.1 [-7.7, -0.4] |

Training on the tiers made the best no-simulator model (held-out h1 / h4 / settled 0.878 / 0.591 / 0.793 against
tx-s10a's 0.845 / 0.506 / 0.784), though +2.6 points in play is within noise. Scoring moves with the tiers does not
help: picking the move by its best round plan is no better on the yardstick than picking it by the settled board, and
in play the round tiers cost points. The tiers work as a training signal, not as a move scorer.

## Pivotal moments and the hybrid bots (jepa-tx-gate, jepa-tx-plan)

Eric's other question the same day: a few moments decide most games; can the bot learn them? `notes/pivots/` has
the runs. The losses are concentrated: on the test set the worst 5% of positions hold 65% of the judged win chance
the bot loses, and the positions where the moves' judged outcomes differ by more than 10 points (22% of positions)
hold 56%. Training harder on those positions did not help: refitting the window head with gap weights
(`fit_veval.py --gap-weight`) or drawing high-gap branch points more often (`tx_train_torch.py --gap-weight`) stayed
within noise of jepa-tx. The head already copies the evaluator on real boards (0.2 points of regret); the misses come
from the imagined settled board.

Looking harder at those positions does help. `--score plan --plan gate=G` simulates only at action windows where the
imagined scores of the moves spread at least G and plays the imagined best move everywhere else. Model tx-t10, window
and planner head tx-t10-e, 702 games vs c-clock, paired against tx-t10 (a) 31.1%:

| Bot | Windows simulated | Wins vs c-clock | Paired vs tx-t10 (a) | Decide time mean / max |
|---|---|---|---|---|
| **jepa-tx-plan** (gate 0) | 100% | **51.4%** [47.7, 55.1] | +20.2 [+16.2, +24.1] | 113 ms / 5.1 s |
| **jepa-tx-gate** (gate 0.1) | 22% | 42.8% [39.1, 46.5] | +11.6 [+8.4, +14.9] | 47 ms / 4.0 s |

Simulating the pivotal fifth of the windows recovers more than half of what simulating every window gives.
jepa-tx-plan is the first JEPA bot above 50% against c-clock on these deals (jepa-plan-reval's 48.8% was on other
deals). Both need the referee's simulations (protocol v2); jepa-tx stays the bot that plays with no simulator.
