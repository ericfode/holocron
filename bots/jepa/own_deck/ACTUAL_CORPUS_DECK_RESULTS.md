# Actual27 frozen-card deck readout: measured results

The learned typed card bank did **not** beat the ID-only or saved current-deck baseline on the predeclared composition readout. Final held MSE was 0.0107333 for correct-typed, 0.0105058 for ID-only and 0.00821346 for current-deck. This run supports the aggregation/readout wiring and measured invariance checks; it provides **no semantic deck-quality, synergy, action-quality or strength qualification**. The preceding card pilot also failed its qualification comparison; this composition result does not override it.

The actual 27 declarations retain all 1,432 main-card copies / 251 identities, with the inherited 22-training / 5-held split and four held families. The new eight-card bank supplies entries for 65 copies (4.539%); 1,367 copies remain semantically unknown, with printed metadata and explicit unknown flags retained. Six card-training identities account for 59 copies; the two held card identities account for six. ID-only held entries are fixed UNKNOWN zeros. Runtime admission 115 IDs / 635 copies is a separate loader gate, whose report does not assess game conformance.

All arms used the same 6,829-parameter trainable deckφ/ρ/head, cloned initialization, printed inputs, copy weights, full 22-row batch, seed 17 and 100 updates. Card banks stayed frozen. The current-deck arm used saved 96d latents with previous composition training; that historical task/compute is unmatched. Targets are 13 printed composition quantities, all varying on training 22; all 13 MSE equals the varying-head macro here. Shared printed fields already contain the information needed for these targets.

Lower MSE is better. The constant uses only the training 22 target mean and zero NN/updates. “Zero-bank held” contains source indices 3 and 25 (two families); the other three held declarations contain at least one bank identity. Eight total declarations have zero bank coverage(six training/two held).

| Arm | Initial held MSE | Final held MSE | Family-first final | Zero-bank held final | Bank-present held final |
|---|---:|---:|---:|---:|---:|
| Training-mean constant | — | 0.015023424 | 0.015828998 | 0.025100295 | — |
| correct-typed | 0.22102814 | 0.010733313 | 0.011610738 | 0.018935276 | 0.0052653367 |
| untrained-typed | 0.22105348 | 0.01111784 | 0.011723398 | 0.019787525 | 0.0053380494 |
| id-only | 0.22116815 | 0.010505755 | 0.011316404 | 0.018870321 | 0.0049293771 |
| current-deck | 0.22726327 | 0.0082134573 | 0.009145582 | 0.013905309 | 0.0044188896 |

Correct-typed is slightly better than untrained-typed overall, but worse than ID-only and current-deck. It also regresses against the constant on cost-bin 0, 2, 4 and 5. A single seed/five held declarations cannot establish a reliable semantic gain; no checkpoint, arm or hyperparameter was selected from these results. All per-head losses are retained below, including regressions.

| Held target MSE (normalized target units) | Train mean | Correct typed | Untrained typed | ID-only | Current deck |
|---|---:|---:|---:|---:|---:|
| total_count_per_60 | 0.003859045 | 0.001548817 | 0.0009535936 | 0.001413295 | 0.001510616 |
| mean_cost_per_10 | 0.01502003 | 0.005408663 | 0.007085103 | 0.006178169 | 0.002014573 |
| low_cost_le_2_fraction | 0.05325405 | 0.04139752 | 0.04195728 | 0.0432043 | 0.01563418 |
| cost_0_fraction | 2.530552e-06 | 8.154267e-05 | 2.659829e-05 | 5.836108e-05 | 0.0002026524 |
| cost_1_fraction | 0.02907808 | 0.02384463 | 0.02417109 | 0.02297451 | 0.01845795 |
| cost_2_fraction | 0.01064391 | 0.01272941 | 0.01637682 | 0.01256291 | 0.008888642 |
| cost_3_fraction | 0.0236378 | 0.01944962 | 0.0187493 | 0.01849057 | 0.02189335 |
| cost_4_fraction | 0.003053501 | 0.003432744 | 0.004072185 | 0.003700658 | 0.002640971 |
| cost_5_fraction | 0.004533524 | 0.004679392 | 0.005735093 | 0.005003092 | 0.006451025 |
| cost_6_fraction | 0.003723483 | 0.001712612 | 0.001037872 | 0.001253533 | 0.0002833372 |
| cost_7_fraction | 0.004289822 | 0.003091615 | 0.00343852 | 0.003118944 | 0.003240599 |
| cost_8_plus_fraction | 0.008130341 | 0.001430265 | 0.001898345 | 0.001499585 | 0.0009589487 |
| initial_draw_unit_probability | 0.03607838 | 0.02072623 | 0.01903011 | 0.01711688 | 0.0245981 |

The durable journal contains exactly updates 1…400, 100 per arm. Reported model calls are 400 training plus eight initialization/final batches; each evaluation batch contains 82 rows (27 original, 27 reversed, 27 duplicate-split declarations merged by canonical identity, one extra-copy probe). Final 27×32 vectors were retained from those same calls, with zero export forwards. Across all eight recorded checks, the largest prediction/latent permutation difference was 4.76837158203125e−7, below the predeclared 1e−5; duplicate-canonicalization differences were exactly 0. These are recorded forward witnesses checked against frozen source and accounting, not a fresh replay of the unretained 82-row outputs.

Final extra-copy latent distances were 0.05539185 (correct), 0.07646271 (untrained), 0.05277535 (ID) and 0.03519863 (current). Distances were measured, not forced positive. The current-deck 96d cache stayed fixed, so its extra-copy check concerns the new count-aware pooling/readout. Distinct-card count is preserved by merging duplicate declarations before the graph.

Independent byte/hash/arithmetic verification passed: all four 27×32 vector sets, exact canonical counts and unknown masses, checkpoint parameter counts/finite arrays, shared initial state, recomputed 13-head/family/zero-coverage losses and 30 frozen input paths. Every recorded before hash equals its after hash and the current file hash. No NN/native/update was run for this review. Deck elapsed time was 2.172536665922962 s; sampled owned-process peak sum 353.171875 MiB, below 1 GiB. Sampled RSS is a stop threshold, not an instantaneous memory reservation.

Source commit: `8fb922bf56869c72f828ee8312a449f3891ed406`; runner SHA256 `904ff7197c8fcad2700b6bd7eb00f141af689c9a911a25bf57142ef97cb63086`. Frozen protocol: [ACTUAL_CORPUS_DECK_PROTOCOL.md](ACTUAL_CORPUS_DECK_PROTOCOL.md).

- [Sealed plan](../../../../experiments/actual-corpus/deck-sealed-v1.json): `346b7cb0344cdae5a7d3319d09585ba526cf0cf8505c101d39f7d8de17670e77`.
- [Saved result](../../../../experiments/actual-corpus/deck-fit-1/result.json): `c2ba170720cc00c830f314219cc79fd67fc464e193eba46afe2a3b65e2359c91`.
- [Durable update journal](../../../../experiments/actual-corpus/deck-progress-1.jsonl): `234c6af0346ef966472919be0e9f36d09482a90610f730d63c7d15dd19d24669`.
- [Independent verification](../../../../experiments/actual-corpus/deck-fit-1-independent-verification.json): `5770050f06721f543577621616f86bb925409b42b84b1c8ef55e4eaa813ff352`. Exact review script is preserved in `experiments/actual-corpus/independent-review-sources/verify_actual_corpus_deck.py`.
