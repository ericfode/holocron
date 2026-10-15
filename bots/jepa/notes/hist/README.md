# Does the JEPA need the deck lists and the game so far? (hist_train.py, 2026-10-15)

Eric's questions: feed the model the whole game as moves and train it on how well it represents the situation; and
"it needs to know about all possible cards, humans do something". `hist_train.py` trains four models of the same
size on the same batches that differ only in what they read (base: tx-t10's inputs; snap: + both discard piles; pool:
+ the unseen cards of both deck lists; hist: + the seat's own earlier decisions), and reports on held-out games.

**Data** (desktop, `from_replays.js --labels` then `data.py --labels`): 6,176 games, 811,018 decisions, drift 0, 142
games skipped for no winner. Games: 1,404 tx-s10a-c vs c-clock (pivots-rec-1), 2,808 c-clock mirrors (seeds 20001,
21001, 22001, 23001, 702 each, recorded for this), 702 tx-t10-va vs c-clock (seed 4001), 702 tx-t10-g04 vs c-clock
(seed 3001), 702 tx-t10-va vs c-clock (seed 5001); all on the 27 real decks. 618 games held out by seed; the held-out
numbers use 20,000 of their rows. Targets: tx-t10's latent (`bots/jepa/models/tx-t10.safetensors`).

## h1: 8,000 steps, all heads train the latent (`h1.json`)

```
        explained_h1  explained_h4  win_logloss  win_acc  hand_logloss  hand_recall  move_logloss  move_top1  move_top5
prior                                                       9.590        0.267        3.343        0.131      0.358
count                                                       9.090        0.200
target     0.863         0.720         0.463      0.769
base       0.735         0.696         0.446      0.782     8.472        0.292        2.143        0.401      0.715
snap       0.732         0.693         0.451      0.781     8.503        0.291        2.144        0.402      0.714
pool       0.729         0.696         0.453      0.782     8.468        0.297        2.169        0.403      0.700
hist       0.735         0.699         0.452      0.787     8.472        0.298        2.142        0.403      0.711
```

## h1p: 8,000 steps, --probe-only (the latent is shaped by the JEPA losses alone; `h1p.json`)

```
        explained_h1  explained_h4  win_logloss  win_acc  hand_logloss  hand_recall  move_logloss  move_top1  move_top5
base       0.802         0.731         0.451      0.779     8.958        0.283        2.780        0.243      0.561
snap       0.805         0.731         0.450      0.781     8.985        0.282        2.783        0.245      0.557
pool       0.802         0.731         0.450      0.778     8.453        0.295        2.785        0.238      0.562
hist       0.808         0.736         0.448      0.780     8.469        0.294        2.795        0.237      0.559
```
(prior, count and target are the same rows as in h1.)

## Reading

1. **Every learned model reads the hidden situation better than the simple baselines.** With all heads training the
   latent, the opponent's hand costs 8.47 nats against 9.09 for counting cards and 9.59 for the leader prior, and the
   opponent's next move is top-1 40% against 13%.
2. **Discards, the unseen cards of the lists and the history add nothing measurable once the heads train the latent**
   (h1: within 0.04 nats on the hand, 0.006 on recall, 0.005 on win accuracy). Pool was clearly best early (hand 8.33
   at 1,000 steps against base's 8.69) and then the others caught up: the lists speed learning, but leaders and the board
   carry the same information after enough steps.
3. **With the latent shaped by the JEPA losses alone (h1p), the lists matter for the hand**: pool and hist 8.45-8.47
   against base and snap 8.96-8.99 (pool's hand head starts from counting cards; base's has no list to count from).
   The JEPA latent itself does not carry the hidden hand; the next move drops to top-1 0.24.
4. **Forecasts**: from scratch in 8,000 steps the models stay below tx-t10 one decision ahead (0.73-0.81 against
   0.863) and reach it four decisions ahead (0.73 against 0.720). Probe-only forecasts better than joint training
   (0.80 against 0.73 at h1): the hand and move heads compete with the forecasts for the latent.
5. **History** gives the best win accuracy in h1 (0.787 against 0.782) and the best forecasts in h1p (0.808 / 0.736),
   both within noise of the others at this length.

A 20,000-step run of base and hist (`--variants base,hist`) is next, since the forecasts are still below tx-t10 at h1.

Note: `hist_train.py`'s hand recall copied the whole (20,000 x 2,048) label array for every row (`y[has][i, ...]` inside
the loop); each evaluation took about 20 minutes. Fixed on main (the indexing hoisted out of the loop).
