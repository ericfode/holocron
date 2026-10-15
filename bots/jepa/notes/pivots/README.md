# Pivotal moments (desktop, 2026-10-15)

Eric's hypothesis: a few moments decide most games; training on them should help.

- Evidence (`pivotal-evidence.txt`, scratch script on the desktop): on test-b with the fixed judge, tx-s10a-e loses
  nothing at 80% of branch points; the worst 5% hold 65% of all regret. Points with an action gap over 10 pts are 22%
  of points and hold 56% of regret. In the bot's own games (on-policy logs) the worst 10% of windows hold 57-63%.
- Own windows: 1,404 recorded tx-s10a-c games vs c-clock -> rank_data.js --teachers tx-s10a-c --p 0.5 -> 18,216
  windows (`pivots-record.txt`, `pivots-rank.txt`, `pivots-prep.txt`).
- Head refits (fit_veval.py --gap-weight / several rank sets; `tx-s10a-e*-fit.txt`, `-ys.txt`, `pivots-heads.txt`):
  no change in the fixed judge or in games. Variant (c) vs tx-s10a-c (28.4%): eg 26.6% (-1.9 [-4.5, +0.7]),
  eo 29.8% (+1.3 [-1.2, +3.9]), eog 28.4% (+0.0).
- Gap-weighted predictor (tx_train_torch.py --gap-weight 1, gaps from `pack_gaps.py` = tx-s10a-e on the real settled
  boards, `pack-gaps.txt`; run `tx-s10p*.txt`): -e hs 0.812 / regret 0.58 / blunders 3.5%. Games: (a) 29.7%,
  (c) 22.8%; best vs best (tx-s10p-a vs tx-s10a-c) +1.2 [-2.2, +4.6].
- Reading: the head already copies the evaluator on real settled boards (0.2 pt regret); the loss is in the imagined
  settle latent. Reweighting toward pivotal points trades average accuracy for pivotal accuracy and nets about zero.

## Hybrid: plan only the pivotal windows (2e7a7e1, desktop 2026-10-15)

tx-t10 (models/tx-t10*.safetensors) with --window-model tx-t10-e --window-horizon s --mix 0 --resource resource-v1
--score plan --plan-model tx-t10-e --plan gate=G; 702 games vs c-clock, 10 workers, paired with tx-t10 (a) 31.1%
(`hybrid.txt`, `hybrid-games.txt`). Gate calibration on 40 games: 0.03 plans 60%, 0.06 37%, 0.10 16.5% of windows.
- gate=0.10: 22.3% of 17,349 windows planned; 42.8% [39.1, 46.5]; +11.6 pts [+8.4, +14.9] vs (a); 0 timeouts,
  decide mean 47 ms, max 4.0 s.
- gate=0 (every window): 51.4% [47.7, 55.1] (BT Elo +10 vs c-clock); +20.2 [+16.2, +24.1] vs (a), +8.4 vs gate=0.10;
  0 timeouts, mean 113 ms, max 5.1 s.
Planning the pivotal fifth of the windows recovers more than half of what planning every window gives.

## More data at pivotal points (idea 2, desktop 2026-10-15)

branches.js --extra-rollouts 3 --gap-min 0.10 (judge linear-deck-g4 on the settled boards): 3 parts of 3,000 real-deck
rush games (seeds 800000 + 3000*i, `xr-data.txt`); 26% of points passed the gap and got 3 more passes, so each part
holds about 110k records (x-*) or 61.7k without the extra passes (branch_prep --base-only, xb-*, the control).
Both trained on the tx-t10 recipe (10 b-packs + 3 new, tiers t-0..2, 30k steps; `xr-chain.txt`, `tx-x13*.txt`):
- tx-x13 (extra rollouts): -e hs 0.811 / regret 0.59 / blunders 3.6%; held-out settled 0.743. Games as (a): 20.2%;
  -11.0 pts [-14.7, -7.3] vs tx-t10-va (31.1%).
- tx-x13b (same games, base only): -e hs 0.802 / 0.60 / 3.5%; settled 0.745. Games: 28.1%; -3.2 [-6.4, +0.0].
- tx-x13 vs tx-x13b: -8.0 [-11.8, -4.2] (`xr-games.txt`). A rerun of tx-t10-va on the current bot code gave 31.1% again.
Reading: as with the gap-weighted sampling (tx-s10p), giving the predictor more of the pivotal points hurts play; more
uniform data did not help either. The pivotal moments pay off at play time (the hybrid planner above), not in training.

## Gate grid and an evaluator-scored planner (desktop 2026-10-15, `gate-grid.txt`)

tx-t10 + tx-t10-e as in the hybrid section, the same 702 deals vs c-clock, 10 workers, paired with tx-t10 (a) 31.1%:
| gate | windows planned | win% | vs (a) | decide mean / max |
|---|---|---|---|---|
| none | 0% | 31.1 [27.7, 34.6] | | 5 ms / 0.3 s |
| 0.10 | 22.3% | 42.8 [39.1, 46.5] | +11.6 [+8.5, +14.8] | 47 ms / 4.0 s |
| 0.08 | 33.7% | 47.1 [43.4, 50.8] | +15.7 [+12.2, +19.3] | 49 ms / 3.5 s |
| 0.06 | 46.3% | 48.5 [44.8, 52.3] | +17.1 [+13.3, +21.1] | 61 ms / 3.3 s |
| 0.04 | 59.3% | 51.2 [47.4, 54.9] | +19.8 [+15.9, +23.7] | 74 ms / 3.5 s |
| 0 | 100% | 51.4 [47.7, 55.1] | +20.2 [+16.2, +24.2] | 113 ms / 5.1 s |
| 0, --plan-scorer eval | 100% | 50.0 [46.3, 53.7] | +18.9 [+14.9, +22.8] | 89 ms / 2.9 s |
No timeouts in any run. Planning the 60% of windows with the widest imagined spread gives all of the gain. The value
head as the planner's scorer costs nothing against linear-deck-g4 (-1.3 [-4.4, +1.9], eval minus value head).
