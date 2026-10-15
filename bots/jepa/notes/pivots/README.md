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
