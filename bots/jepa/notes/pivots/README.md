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
