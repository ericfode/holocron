# Bounded representation probes

These probes test availability of synthetic original-deck information. They do
not train the actor or encoder, establish playing strength, or evaluate effect
programs. All six printed card identities occur in both train and test; only
complete composition fingerprints are disjoint.

The fixed experiment uses 128 unique synthetic bags (96 train, 32 test), one
unchanging existing board/hand observation, seed 1907, and ridge alpha 0.001
selected before evaluation. Inputs are standardized using training rows only.
The same model and batch size encode original, neutral, and wrong-deck arms.
Wrong decks are a within-partition bijection of other synthetic own bags and
must differ in total count, target-card count, and mean cost. They never contain
opponent-private data. A train-mean prior and permuted-training-label probes are
reported alongside MAE and R² for every arm.

Held-out MAE from the recorded run:

| Input | Total copies | Target copies | Cost ≤2 fraction | Mean cost | Initial target fraction |
|---|---:|---:|---:|---:|---:|
| Raw original | 0.000021 | 0.000020 | 0.000001 | 0.000005 | 0.000001 |
| Frozen initialized latent, original | 0.648912 | 0.301632 | 0.012034 | 0.089497 | 0.012149 |
| Frozen initialized latent, neutral | 3.970703 | 1.398438 | 0.092024 | 0.661253 | 0.081379 |
| Frozen initialized latent, wrong deck | 6.014237 | 2.311428 | 0.167777 | 0.937055 | 0.133823 |

Raw-input results confirm the explicit count/curve contract. Initialized latent
results are diagnostic linear decodability on six familiar synthetic identities.
They support neither policy competence nor generalization to unseen card IDs or
novel compositions of effect programs. No minimum latent R² is imposed. Negative
control R² and permutation results are retained as measured, including negatives.

Variance diagnostics are recorded independently of probe accuracy: original
latent dimensions have median standard deviation 0.01355, variance-entropy
effective rank 2.268, and median pair distance 0.18672. Neutral latents have zero
variance and pair distance, as expected with an identical board and no deck
information. Wrong-deck permutation preserves the overall latent distribution.
These scale/collapse diagnostics do not establish strategic information retention.

The probability target is only `n_target/N_initial` for a complete known bag at
declaration, before any draw. The target has a unique cost bin in this deliberately
simple catalog, so its initial fraction is directly exposed. The constant board
is an encoding foil, not a game reconstructed consistently for every synthetic
bag. Nothing here predicts the next draw from the live remaining pile. Remaining
composition requires a sound observation ledger and is currently unknown.

The current deck path represents hashed identity and printed metadata, including
keyword/trait summaries. It has no structured effect-program meaning. A future
semantics test would need familiar effect compositions on held-out card identities
and familiar identities with deliberately changed effects; this run tests neither.

Reproduce from the repository root with an existing NumPy environment:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bots/jepa/own_deck/probe_representation.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bots/jepa/own_deck -p test_probes.py -v
```

The CLI caps the experiment at 128 examples and sets numerical-library thread
limits to one. The recorded run took under one second. `representation-probe.json`
contains all counts, split fingerprints, control permutations, source/fixture
hashes, complete metrics, and unchanged checkpoint hashes. No kernels regenerate.
