# Round tiers and macro actions: desktop run (2026-10-15)

Code: holocron df83954 (claude/project-thread-cm1u93), run from claude/jepa-pivots (df83954 merged, f2e4148) on Windows
for training and in WSL (bots/jepa copied from that checkout) for data and games. c-clock: the WSL binary built on
2026-10-14 from holocron 66f0732 (bots/c before #9), the same opponent as every earlier test, so all games pair.

Data (`tier-data.txt`, `tier-gen-*.log`, `tier-prep-*.log`): rush vs rush on the 27 real decks, --p 0.25 --max-branch 0
--macros face,trade,hold, 20 workers. Parts of 2,000 games took 3,442 / 3,486 / 3,457 s (1.7 s/game wall, about 34 s
per game per worker, while the CPU also ran other jobs), so the run stopped at 3 parts (seeds 790000, 792000,
794000): 29,733 + 29,505 + 29,307 tier points. Test set: 500 games at seed 745000, 7,108 points, judged by
linear-deck-g4 (815 s).

tx-t10 (`tx-t10.txt`): the tx-s10a recipe (10 branch packs, --settle, --pack-e --w-eval 1) plus --tier-pack t-0..t-2,
30k steps, 41 min at 13 it/s. Held-out: moves_explained h1 0.878, h4 0.591, settled 0.793, r 0.752, r2 0.394;
macros_explained r 0.731, r2 0.356. Value head BCE 0.4459. Raw hs (fixed judge): 0.669 / regret 1.09 / blunders 5.6%.

tx-t10-e (plain fit_veval, `tx-t10-fit.txt`, same_as_eval 0.845): fixed-judge hs 0.813 / 0.58 / 3.5% (`tx-t10-e-ys.txt`).
Tier yardstick (`tx-t10-e-tiers.txt`): r: lines top-1 0.780 (chance 0.557), macro top-1 0.772 (chance 0.440), move pick
by tier 0.849 / regret 1.05 / blunders 4.9% vs by the settled horizon 0.853 / 1.09 / 5.4%; r2: lines 0.742, macro 0.684,
by tier 0.844 / 1.50 / 7.1% vs settled 0.827 / 1.62 / 8.2%.

Games (`tier-games.txt`): 702 vs c-clock, same deals as every earlier test; --model tx-t10 --window-model tx-t10-e
--window-horizon s --mix 0 --resource resource-v1, plus:
| variant | win% | vs tx-s10a-c (28.4%) | vs (a) |
|---|---|---|---|
| (a) no tiers | 31.1 [27.7, 34.6] | +2.6 [-0.9, +6.2] | |
| (b) --tiers s=1,r=1 | 30.6 [27.3, 34.2] | +2.1 [-1.8, +5.9] | -0.6 [-3.2, +2.0] |
| (c) --tiers s=1,r=1,r2=1 | 28.6 [25.3, 32.0] | -0.1 [-3.7, +3.4] | -2.6 [-5.2, +0.0] |
| (d) as (c) + --commit-macro | 29.0 [25.7, 32.5] | +0.3 [-3.3, +3.8] | -2.2 [-4.8, +0.4] |
| (e) --tiers r=1,r2=1 | 24.6 [21.5, 27.9] | -4.1 [-7.7, -0.4] | -6.8 [-9.8, -3.8] |
Decide time: mean 5 ms, p95 about 10 ms, max 344 ms; no timeouts.

Reading: the tiers are learned (macro top-1 0.77 at the round end) and training on them may help the base model a little
((a) +2.6, not significant; h1/h4 predictions improved). Using them to score moves does not help in play, and dropping
the settled score hurts.
