# Transition replication: independent saved-result review

2026-10-18 UTC. **The original aggregate advantage repeats across seeds; transfer to the fresh overlapping-target pair is modest and inconsistent by head.** Correct IR improves the new predeclared paired contrast score in all three seeds, but its absolute nine-head joint error is worse than context-only in two. This supports retaining the structural channel for diagnosis, not admitting a general effect interpreter or scaling/deploying the model.

This review reads saved results and performs only JSON arithmetic. No model/native call, fit or matrix evaluation is added. Full raw per-seed/arm/head MAEs, accuracies, support, baselines, checkpoint/source pins and descriptive seed statistics are retained in `experiments/transition-replication/independent-result-summary.json` (SHA256 `d63e13206b726ed2df73c428e50e2ea6dabdda355eba78337e6a2498a3b912e4`). Original source results remain unchanged, including the earlier negative pilot and [single-seed review](GROUNDED_CONTRAST_RESULTS.md).

## Original fixture: fixed-data replication

Only seeds 29/43 were newly fitted. Historical seed 17 was already inspected and is a reference, not a fresh blinded replicate. Each seed uses four matched 9,020-parameter arms, identical per-seed initialization and minibatches, 600 updates/arm, unchanged graph/loss/vocabulary, training-only scales and final-step selection. Lower is better. Each cell below is **program-held / joint-held primary nine-head macro MAE**; state-held and all per-head records are retained in the JSON.

| Seed | Correct IR | ID-only | Wrong IR | Context-only |
| --- | ---: | ---: | ---: | ---: |
| 17, historical | 0.247283 / 0.249382 | 0.532475 / 0.511233 | 0.308460 / 0.332910 | 0.304246 / 0.325079 |
| 29 | 0.256120 / 0.294996 | 0.447907 / 0.465975 | 0.292801 / 0.322446 | 0.295203 / 0.334393 |
| 43 | 0.263923 / 0.286430 | 0.546055 / 0.505015 | 0.295226 / 0.333325 | 0.293111 / 0.332940 |
| Mean, descriptive | **0.255775 / 0.276936** | 0.508812 / 0.494074 | 0.298829 / 0.329560 | 0.297520 / 0.330804 |

Correct IR beats all three arms in both cells at every seed. The context-only margin varies: joint reduction is 0.075697, 0.039397 and 0.046510. Seeds measure optimization variability on the same tiny fixture; they do not add independent held programs or worlds. Original joint outcomes still come from five prompt roots across three states, and the two held programs have disjoint committed base/unit target domains.

The aggregate does not erase head failures. The table gives **correct-IR minus context-only native-unit joint MAE**: positive means worse. All target scales equal 1 here; auxiliary constant heads remain outside this nine-head macro.

| Original joint head | Seed 17 | Seed 29 | Seed 43 |
| --- | ---: | ---: | ---: |
| Source-use | −0.124965 | −0.126061 | −0.122878 |
| Target-allowed | −0.340272 | −0.170207 | −0.392862 |
| Resource cost | +0.001028 | −0.189893 | −0.106054 |
| Signed damage | −0.445197 | −0.024096 | −0.120655 |
| Target exhaustion | **+0.042303** | −0.020461 | **+0.199441** |
| Shield | **+0.087999** | **+0.090151** | **+0.070420** |
| Experience | **+0.137318** | **+0.125268** | **+0.120062** |
| Defeat | −0.050006 | −0.078222 | −0.071386 |
| Terminal | **+0.010519** | **+0.038945** | **+0.005321** |

Shield/Experience/defeat are zero in these held programs; terminal has only one positive root. Their low errors or differences cannot validate nontrivial generalization of those effects. Source-use has only one negative joint root. Admissibility remains the clearest original matched signal; damage gains vary substantially by seed.

## Fresh pair: the same trained models, overlapping native outcomes

Fresh holdouts are `SHD_004` (resource 1, Experience 1 on a low-power unit) and `TWI_206` (resource 2, exhaust under its power predicate). All ten training programs and families 0–9 were independently proven exactly equivalent after fresh native collection: all 100 canonical roots, all eight candidate inputs including source-self auxiliary, labels, masks, scales, program tensors and identity-index order. Saved weights were reused, avoiding three identical refits. No fresh-label gradient or normalization fitting occurred; each seed adds only four final batched evaluations. Loaded weights and the global optimizer journal remain unchanged.

The predeclared new primary compares **SHD004 minus TWI206** predicted/native deltas on the same candidate and held state, requiring actual offers, independent untouched-prompt commits, settlement and known masks for both. There are eight pairs (friendly/enemy ground candidates × four states), two programs and four world families. Those are dependent branches, not eight independent games. Cost contrast is always −1, Experience always +1, and exhaustion contrast is −1 in seven pairs and 0 in one.

| Fresh paired three-head macro MAE ↓ | Seed 17 | Seed 29 | Seed 43 | Mean |
| --- | ---: | ---: | ---: | ---: |
| Correct IR | **0.874925** | **0.928125** | **0.916146** | **0.906398** |
| ID-only | 0.958333 | 0.958333 | 0.958333 | 0.958333 |
| Wrong IR | 0.958616 | 0.958323 | 0.958060 | 0.958333 |
| Context-only | 0.958333 | 0.958333 | 0.958333 | 0.958333 |

ID-only and context-only receive identical public inputs and the same unavailable/unknown program channel for both held actions, so they predict zero pair differences by construction. Their primary score is a useful zero-contrast baseline, not evidence that they learned these effects. Correct IR improves this aggregate in all seeds, but retains large errors:

| Paired head: correct-IR MAE ↓ | Seed 17 | Seed 29 | Seed 43 | Zero-contrast baseline |
| --- | ---: | ---: | ---: | ---: |
| Resource cost | **1.028853** | **1.023715** | 0.860501 | 1.000000 |
| Experience | 0.884324 | **1.071437** | **1.010673** | 1.000000 |
| Target exhaustion | 0.711597 | 0.689223 | **0.877263** | 0.875000 |

Bold errors exceed that baseline. Mean predicted cost contrasts are `+0.0289 / +0.0237 / −0.1395`, versus native −1; mean Experience contrasts are `+0.1157 / −0.0714 / −0.0107`, versus native +1. Two seeds have the wrong average sign for each quantity. This is limited program sensitivity, not reliable cost/quantity binding. Exact power-4 versus power-3 discrimination is untested by the helper powers 1/3/5.

The old absolute nine-head joint macro measures a different question and must remain visible:

| Fresh absolute nine-head joint MAE ↓ | Seed 17 | Seed 29 | Seed 43 | Mean |
| --- | ---: | ---: | ---: | ---: |
| Correct IR | 0.384170 | **0.433732** | **0.478270** | **0.432057** |
| ID-only | 0.410291 | 0.370551 | 0.404486 | 0.395109 |
| Wrong IR | 0.439548 | 0.415750 | 0.370302 | 0.408533 |
| Context-only | 0.432595 | 0.415978 | 0.365736 | 0.404770 |

Correct IR is worse than context-only at seeds 29/43. Absolute Experience, Shield and terminal errors are worse in all three seeds; absolute cost is worse in 29/43, exhaustion in 43, and zero-damage prediction in 43. Target-allowed probability MAE is slightly better each seed, yet threshold accuracy is worse: `0.625/0.625/0.554` versus context `0.750/0.643/0.714`. Paired differences can cancel a shared offset while absolute predictions remain poor; neither metric supersedes the other.

Fresh joint support is eight source observations, 56 target-membership coordinates and 24 settled primary outcomes. Source-use is **8 positive / 0 negative**; source-exhausted-after is always 1, damage/Shield/defeat/terminal always 0, and known follow-up offers always 0. Those are diagnostics, not balanced semantic tests. The changed held family 12 has two ready resources, so this is also a declared context-recipe change from the original assay. It is a separate transfer test, not a new training-world sample.

## Accounting, pins and decision

All six stages completed: fresh native collection, two fits and three zero-update evaluations. The append-only ledger totals **980 native applies, 4,800 new updates and 61.851617085 active seconds**, within 2,048/4,800/240. There were 452 settled target commits, zero native errors, sixteen initial/final original-validation batches plus twelve fresh final batches = **28 evaluations**, zero new use/ABI batches and US$0 recorded new spend. The optimizer journal is exact 1–4,800 and byte-identical across fresh evaluations. Historical updates/attempts remain separately preserved, not reset or counted as new.

All-stage conservative sampled RSS is **639,909,888 bytes**; fit-only peak is 431,374,336 bytes, below 2 GiB, one compute worker/thread. Supervisor receipts sum to 61.852484875 seconds, a preserved 0.000868-second difference from ledger boundaries. Sampling is not an instantaneous kernel memory limit. Independent accounting/hash review also passed named checkpoints/contracts, predictions/evaluation evidence, source pins, journal and sequential completed run events. Thirteen pure runner tests passed before execution.

Native collection executed at `f94457da573ad67e8dd92bf50c9d372bd34045a5`; the two fits and three evaluations executed at `ae64647143916fb2bba1bc014585fed659f3f76a`. Runner SHA is `f4277ab29be9fdd26d6920e04d35eee4acbe6bd781c36968475b37a306af9a6e`; unchanged model source SHA `473bc2324cf62c0437effd631e8fec3cc5930d2aeee0d00255da3bd08747eaf2`. Fresh dataset SHA `fe67ed242fed1be794c498bc062bdb5031b9136aa0ac5f277cb6001964b632cc`; manifest `8ff5b35d4189e6c45994807366a9665e935779896b9a91d409ef97b55577bf64`; independent equivalence proof `a7b399b24e329f5f1c55e5e2f7d10a0092f0b4245586d17efe39ce3a29043289`. Kessel remains `c7ee39554901278cee70f61fd8b26fb1920696b3`. The summary JSON records all six source-result hashes and every loaded checkpoint hash.

The supported decision is to retain the seed-replicated original signal while treating broad transfer as unresolved and per-head failures as substantive. The cheapest next question is why the existing cost/Experience/exhaust paths often predict near-zero or wrong-sign contrasts; inspect literal/role binding and head gradients before another architecture change or fit. Neither this auxiliary task nor the retrieval proxy establishes deck coherence, dynamic remaining-deck prediction, semantic-neighbor quality or playing strength. No production graph/checkpoint or deployment changes follow.
