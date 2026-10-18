# Deck representation diagnosis

The saved deck vectors are strongly anisotropic, with useful composition signal and limited evidence of mechanical similarity. The 97.05% common-mean energy does **not** establish identical-vector collapse, a disconnected deck path, or a need for a larger encoder. The source/matrix audit used saved arrays only. A separate coordinator-approved current-gradient diagnostic subsequently used exactly one forward and one backward, with zero optimizer updates, native calls, checkpoint writes or paid jobs.

The original 27-vector audit reports centered numerical rank 21 of the maximum 21, entropy effective rank 3.6402, and nonzero pair distances 0.2478–4.5838. See [saved geometry](embedding-geometry-evidence/result.json#L206) and [interpretation](EMBEDDING_GEOMETRY_AUDIT.md#L9). Effective rank describes concentration of variance, not the number of meaningful strategic distinctions.

## Where concentration occurs

The later saved one-forward bank captured the original-deck token before attention, after final layer normalization, and full z96 in the **same computation** ([capture source](independent_retrieval_embeddings.py#L247)). Float64 matrix calculations on its 22 training-reference rows give:

| Saved tensor | Dimensions | Mean energy fraction | Centered entropy / participation effective rank | Centered top3 variance | Numerical rank |
|---|---:|---:|---:|---:|---:|
| Initial original-deck token |64|94.6378%|5.4987 /3.8565|75.3517%|21|
| Final original-deck token |64|96.4057%|2.9194 /1.9321|91.7072%|21|
| Full public-context latent |96|97.0543%|3.6402 /2.6789|91.6446%|21|

Numerical rank uses centered singular values above 1e-5 of the largest. These are current saved representations at different layers, **not** before/after training. They show that the full readout is not the sole source of concentration. They cannot establish whether training increased anisotropy: no matched 27-deck pretraining latent bank was saved.

The input contains count-aware printed summaries and three pooled identity factors ([own_deck.py129–149](../own_deck.py#L129)). Identity becomes 16 shared embedding coordinates; metadata 50 plus identity 16 project to 64, with bias and role embeddings ([own_deck_model.py39–57](../own_deck_model.py#L39)). Both original and unknown-remaining tokens are visible. The final z96 combines the state token, mean active context and numeric public state through a frozen affine/ReLU readout ([lines88–112](../own_deck_model.py#L88)). On the export's zero public state and masked live cards, the status/role/unknown row and frozen readout can supply common components. This is a plausible mechanism, not an identified causal decomposition. Layer normalization does not impose zero mean across examples or make raw cosine task aligned.

## What training actually rewards

The measured 100-step arm updates only `din.w`, `din.b`, `drole` and a separate biased linear 96×13 readout. The base transformer, identity tables andz projection are frozen. Its loss is mean squared error on 13 declared count/curve/unit-fraction statistics; there is no cosine, pairwise, variance, covariance or action-transition term ([runner242–284](run_local_experiments.py#L242), [freeze check295–308](run_local_experiments.py#L295)).

Targets are constructed directly from original composition ([real_deck_data.py96–105](real_deck_data.py#L96)). Their centered 22×13 training matrix has numerical rank 11 at relative singular threshold 1e-6; the last two singular values are about 2.01e-8 and1.19e-8. Cost-bin fractions sum to 1 and the low-cost fraction is a sum of bins. Thus the task need not retain 96 independent distinctions. Same-curve/unit/count decks can have different effects without a corresponding target difference. Exact ability IR is absent from the printed input parser ([own_deck.py49–73](../own_deck.py#L49)); the decoder cannot invent missing rule information reliably from this loss.

For `prediction=zW+b`, replacing `z` by `z+c` and `b` by `b-cW` preserves predictions and MSE. This is an invariance of the supervised readout, not a claim that arbitrary translations are available under the frozen encoder or leave AdamW unchanged. It explains why small readout error does not define an origin or justify raw cosine as semantic distance. Inflating variance alone would not supply missing effect supervision.

There is measured useful signal: correct-original validation MSE 0.00827 versus neutral 0.01718 and wrong-own 0.01691; curve MAE 0.06082 versus 0.09950/0.09809. Count error is worse, so improvement is not universal ([LOCAL_RESULTS.md10–25](LOCAL_RESULTS.md#L10)). The saved aggregate gradient norms combine projection and readout parameters; they do not identify per-module gradients. The independent [saved-gradient audit](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/embedding-geometry/composition-saved-gradient-audit.json), SHA-256 `027973c04487623b4dd760bdfd18ae2117717a155576bfcf758b7fe847c24327`, finds original-arm metadata/pooled-identity weight endpoint changes L2=0.62377/0.58939 and zero-initial `din.b` becoming 64/64 nonzero. The projection received training signal; these are not gradient magnitudes or proof every channel is useful. Neutral weights also move through decay. The three real 100-step fit traces do not save per-module/input/activation gradients. A separate earlier [synthetic wiring receipt](training-verification.json#L8) records one SGD test update and finite nonzero gradients for all three supplemental tensors ([checks](training-verification.json#L18)); it proves differentiable wiring, not current real-deck gradient coverage. Restoration trained logistic heads on a frozen engineering initialization, so its weak results are not additional encoder-training evidence ([restoration_probe.py353–379](restoration_probe.py#L353)).

## Measured current gradient diagnostic

The separately frozen diagnostic executed at commit `32dc59a` on the actual saved 100-step original supplement and readout, all 22 training rows, and unchanged 13-target MSE ([source133–161](composition_gradient_diagnostic.py#L133)). It made exactly **one production forward, one backward, zero optimizer updates**. The current loss was 0.00229665. All 60 frozen base parameter gradients were absent as intended; all parameters and protected files remained unchanged ([checks162–169](composition_gradient_diagnostic.py#L162)).

| Current gradient block | Coordinates above 1e-12 / total | RMS |
|---|---:|---:|
| Metadata projection weights |2944/3200|4.5440e-4|
| Pooled-identity projection weights |1024/1024|5.1400e-5|
| Projection bias |64/64|2.0202e-3|
| Original role / unknown-remaining role |64/64 each|1.0150e-3 /1.6017e-3|
| Readout weights / bias |1248/1248;13/13|1.6438e-3 /1.8206e-3|
| Original metadata input |1100/1100|4.4922e-5|
| Original hashed-identity input |3454/3454|5.7476e-5|
| Disabled remaining input |4554/4554|6.9472e-5|
| Full z96 |2112/2112|2.5395e-5|

This rules out an entirely disconnected metadata/identity projection for the current batch. It does **not** prove meaningful use of every coordinate. Only 41/50 original metadata columns and 152/157 identity columns vary across these 22 decks. Remaining has 0/207 varying columns, enabled=0 and known=0; its nonzero derivatives concern a constant unknown token, not represented remaining-pile information. Input derivatives perturb continuous coordinates independently, including constant/zero coordinates that are not lawful card substitutions. Block gradient RMS depends on scales, dimensions and parameterization; it is not an importance ranking. These observations characterize the **current checkpoint and batch**, not historical training coverage or semantic correctness. No objective or architecture changed.

The [actual result](/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/composition-gradient/run-1/result.json) has SHA-256 `db31fa0ba2f8f914ee8cb34991813936938eb9917235435e5ad5bc5b626a45db`; its plan/source hashes are `9c07cafdc97cee524fc6883b69bb065fe582fae36953a3b0cf0bdf280229ba81` / `00dadcc76c473e7bd4b2e2c56e4620c1024eb759fca86a209a9e408f0401b204`. The completion receipt records 0.918928 seconds wall, 0.863370 CPU, 226,836,480 bytes sampled high-water RSS, 16 samples and one compute thread. It passed the frozen 20-second / 1-GiB bounds; sampled RSS is not an instantaneous OS reservation.

## Controls and next decision

The independently prepared strict synthetic mechanics controls have **2 near wins/3 source roots** at each replacement dose for both full z96 and the original64 branch. Centering/whitening does not change that winner pattern. Raw fullz family-macro gaps are 4.48e-6 and2.01e-5. Count overlap ties; the typed-IR proxy oracle orders all 3, by its own definition. These are weak structural-proxy signals on three dependent roots, not zero discrimination or native semantics. Authored-list strict controls have no admitted comparisons; their two exploratory cases are stat-confounded. See external `independent-controls/metrics-run/result.json`, `summaries.v2-synthetic.strict-power-hp` and `declared_support`.

**No larger architecture or variance-only objective retest is justified now.** First retain the fresh controls and native replication results, with input collisions, per-head support and the independent gradient audit. Exact collisions at the207-coordinate boundary are missing-input evidence; an objective-only retest cannot recover a distinction absent from its inputs. If genuinely new controls show no useful mechanical signal despite learnable inputs and functioning gradients, the smallest retest is a fixed two-arm, one-seed supplemental experiment: existing declaration loss versus the same loss plus a predeclared native same-context program-contrast auxiliary on covered train-family examples. Keep base, initialization, capacity, update count and schedules matched; use the same dedicated deck projection in both arms, preserve unknown capabilities, and evaluate untouched program/family controls once. No validation-selected margin or variance coefficient; no declaration that increased rank alone is success. A branch-readout change is warranted only if the saved branch succeeds where fullz fails; current 2/3 results do not show that separation.

## Reproduction and pins

All calculations below read saved arrays only, using `/Users/ericfode/src/crown-jepa/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1`:

```python
import numpy as np
root = "/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/"
with np.load(root + "independent-controls/embedding-run/vectors.npz", allow_pickle=False) as a:
    rows = a["train_reference_indices"]
    for name in ("initial_deck_tokens64", "final_deck_tokens64", "full_z96"):
        x = a[name][rows].astype(np.float64)
        if x.ndim == 3: x = x[:, 0]  # original role only
        mean = x.mean(0)
        s = np.linalg.svd(x - mean, compute_uv=False)
        p = s*s / (s@s)
        print(name, len(x)*(mean@mean)/(x*x).sum(),
              np.exp(-(p[p>0]*np.log(p[p>0])).sum()), 1/(p@p),
              p[:3].sum(), (s>s.max()*1e-5).sum())
with np.load(root + "data/real-decks.npz", allow_pickle=False) as a:
    y = a["targets"][a["train_idx"]].astype(np.float64)
    s = np.linalg.svd(y-y.mean(0), compute_uv=False)
    print(s, (s>s.max()*1e-6).sum())
```

Elapsed time, process RSS and BLAS thread count were not instrumented for this tiny read-only matrix recomputation; tool latency is not a compute receipt. Matrix-audit counts: 0 neural forwards, 0 native applies, 0 optimizer updates, 0 paid jobs. The separate measured diagnostic above accounts for its one forward/one backward and measured guard receipt.

| Input/source | SHA-256 |
|---|---|
| Saved token/full vector bank |`a1651cb48443b5a8bfe39ebaa5d773d3f06b9d07776092762315fdc2b70b0463`|
| Independent retrieval metrics |`7d9f1bad2dad073ec6038996895825f6426a60588edd503971e04e981a6c157f`|
| Real-deck feature/target bank |`3a255abaf8d4fc3e5ca28aba8a3b910d341532614ce7ba5c52d7e5b250126091`|
| own_deck_model.py |`c9bb484f1923942b3c78b770dec361a08745f9a000aef82d5c809d0e9c2dbd16`|
| run_local_experiments.py |`b3826c443bd4a2f8aab2c29bc9d90f74282b3f05baa620e01376a999674d4354`|
| Saved token capture source |`e7061a0cc591f1db297aec8397afb45b88630eea9aa32103dfbe0ab0b5db0a59`|

The bank uses frozen base checkpoint `50b8f9a2c3782c5cf5b23e80b2a65d2a0292523ec9a9213287b86143f99b6d34` and original-composition supplement `498f2c9a796ec75879796eb6d43c812f72a7a06b10d0774c74aed328b1315cbc`; source/export provenance remains in the saved embedding-run plan/result and earlier geometry receipt. No protected source, dataset, raw vector or checkpoint was changed.
