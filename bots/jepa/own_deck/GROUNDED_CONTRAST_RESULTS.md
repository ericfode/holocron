# Grounded contrast: independent result review

Reviewed 2026-10-18 UTC from saved source, native receipts, dense data, contracts, predictions and fit results. This review launches no model/native execution or paid work. The result supports a **narrow benefit from the correct typed program channel**, strongest for target admissibility, in one seed and twelve existing-runtime programs. It does not establish a general effect interpreter, semantic distance, deck coherence, dynamic deck prediction or playing strength. The earlier negative two-card result remains preserved.

## Matched result

The fit used ten program groups × ten state families; evaluation contains two unfamiliar program groups (`TWI_157`, `HMW_170`), four unfamiliar state families, and their crossed cells. The 100/20/40/8 root split and all branches were frozen before collection. Primary globals and candidate slots 0–6 match exactly across programs within each state. Source-self slot 7 is a separately reported 0.1 auxiliary and is not broadcast to primary predictions. Native offers and settled transitions supply labels; they are not reconstructed from IR.

All four arms have 9,020 allocated parameters, identical initialization, 600 updates, the same 16-root minibatches, optimizer and final-step selection. Correct IR has no card IDs/titles/source paths; unseen IDs in the ID arm share one unknown token. Wrong IR changes per training example/step, preventing the old fixed invertible identity code; evaluation uses the frozen partition-local wrong mapping. Training inputs/scales use fit roots only. Eight evaluation batches cover initial/final readouts across four arms; there is no checkpoint search.

The reported macro averages nine heads selected using training variation: source-use, target-allowed, resource cost, signed damage, target exhaustion, Shield, Experience, defeat and terminal. It averages candidates within roots, roots within heads, then heads. All saved target scales equal 1 here, so it is an equal-weight mixture of these native-unit MAEs. Low-support flags do **not** remove a head from this macro. Constant source-exhaustion and follow-up heads are auxiliary.

| Final primary macro MAE ↓ | Program-held, 20 roots | State-held, 40 roots | Joint-held, 8 roots |
| --- | ---: | ---: | ---: |
| Correct IR | **0.247283** | **0.061480** | **0.249382** |
| ID-only | 0.532475 | 0.065927 | 0.511233 |
| Wrong IR | 0.308460 | 0.285253 | 0.332910 |
| Context-only | 0.304246 | 0.281489 | 0.325079 |
| Training-prior baseline | 0.360674 | 0.314613 | 0.366213 |
| Zero-delta/copy-source baseline | 0.428266 | 0.345350 | 0.434683 |

Correct IR beats context-only by 0.056963 on program-held and 0.075697 on joint-held macro MAE. The state-held ID result is nearly as good as correct IR: familiar identities already support this small state interpolation. The held-program improvement is the more relevant transfer observation. This is one frozen seed, without a confidence interval or repeated-seed estimate.

## Where the signal lies

| Native-unit head MAE ↓ | Program-held: correct / context / wrong | Joint-held: correct / context / wrong |
| --- | --- | --- |
| Source-use | 0.00108 / 0.05117 / 0.05143 | 0.00189 / 0.12685 / 0.12727 |
| Target-allowed | **0.15871 / 0.53913 / 0.53584** | **0.20082 / 0.54109 / 0.53436** |
| Resource cost | 0.53112 / 0.67367 / 0.63511 | 0.62645 / 0.62542 / 0.58646 |
| Signed damage change | 0.75663 / 1.02503 / 1.00598 | 0.62626 / 1.07146 / 1.10019 |
| Target exhaustion change | 0.25709 / 0.19771 / 0.28610 | 0.22266 / 0.18036 / 0.26339 |
| Shield change | 0.20545 / 0.05227 / 0.06615 | 0.19511 / 0.10711 / 0.12099 |
| Experience change | 0.28971 / 0.13592 / 0.12933 | 0.27320 / 0.13588 / 0.13865 |

Target-allowed is the clearest matched native contrast: both held programs face the same public candidate vectors, but one selects bases and the other units. Correct-IR root-averaged threshold accuracy is 89.01% versus context-only 38.46% on program-held and 82.86% versus 40.00% on joint-held. These are ordinary accuracy, not balanced accuracy. Source-use is also accurate, but its negatives are sparse: 17/3 positive/negative program-held roots and 7/1 joint-held.

Damage prediction improves against both non-identity controls; resource cost is effectively tied with context-only in the joint cell and worse than wrong IR there. Readying/exhaustion is worse than context-only in both held-program cells. Shield and Experience errors are worse as well, with only zero targets in the held programs. Thus the result cannot be summarized as successful transfer of all costs/effects/quantities. Defeat is also zero throughout held-program evaluation. Terminal has only one positive root and is correctly classified by several controls, so its small error is not independent evidence of a learned terminal rule.

## Support and interpretation limits

Collection preserved 168 source observations, 932 actual native applies, 413 settled target commits, zero native errors and zero pending commits. Seven actual offered abilities completed without a target prompt; their candidate memberships remain unknown. The joint cell has eight source roots but only **five target-prompt roots across three state families**, 35 known primary candidate memberships (16 true, 19 false), and sixteen primary committed outcomes. Candidate branches are correlated observations from each root, not sixteen independent worlds. All joint heads are marked low support by the frozen four-state evidence rule.

Joint cost takes values 0/2, signed damage 0/2, and target exhaustion −1/0. Shield/Experience/defeat are always zero; source-exhaustion is always one. There is one positive terminal branch in one `TWI_157` root. `HMW_170` has no target prompt in two held worlds; the zero-resource `TWI_157` world has no activated ability. Masking preserves those limitations rather than inventing negative future labels.

The two held programs have disjoint committed base/unit target domains. Their target-membership contrasts are cleanly matched, but they do not provide a same-candidate, both-legal held-program-only contrast for committed damage versus readying. Context predicts part of their effect domain. The full bank has paired committed contrasts involving familiar programs, which does not remove this held-program limitation. Both held ASTs reuse global typed atoms but introduce new positions/combinations; frozen vocabulary exposure to their label-free definitions is not an unseen-vocabulary test. Exact normalized program groups are disjoint, but that is not a proof of semantic-equivalence exclusion. Two programs and one seed remain insufficient for population claims or a reliable semantic-neighbor ranking.

Actual native Ready behavior also corrects an early static simplification: if nothing selectable can change, the ability can finish without a prompt; when one target can change, the observed prompt can include already-ready units. Treating “target must be exhausted” as a per-candidate label rule would have been wrong. The native labels, not that proposed parser rule, were used.

## Gradients and same-weights use checks

The correct arm's existing training backwards recorded nonzero program-path gradients at steps 1 and 600. Preclip RMS at those steps was 0.00462 → 0.00540 for program projection, 0.000380 → 0.00592 for numeric projection, and 0.00121 → 0.00322 for the joint leaf MLP. Context projection was 0.00402 → 0.000714; candidate projection 0.00660 → 0.00273. Numeric and leaf gradients cover all their coordinates; program projection covers 83.3%, while inactive/padded paths appropriately remain unused. Identity embeddings have no gradient in the correct arm. These scale-dependent snapshots show a connected, used semantic path; they do not establish that every literal or predicate is interpreted correctly. “Allocated coordinates in tensors with a nonzero gradient” in the result is not the count of actual nonzero coordinates; snapshot coverage gives the latter.

Two saved inference-only interventions on the fitted correct model used the same collected native targets, without model selection:

| Correct model channel | Program-held macro ↓ | State-held macro ↓ | Joint-held macro ↓ |
| --- | ---: | ---: | ---: |
| Correct program | 0.247283 | 0.061480 | 0.249382 |
| Zero program | 0.408992 | 0.341195 | 0.420786 |
| Partition-local swapped program | 0.534616 | 0.451385 | 0.532677 |

Zero/swap interventions change source probabilities by RMS 0.262/0.399, and primary branch predictions by RMS 0.438/0.573. Their aggregate degradation, especially target membership, supports useful program use. It is not uniformly semantic: swapping actually improves damage MAE (joint 0.409 versus correct 0.626), and zeroing improves program-held readying error. These are feature interventions scored against original native labels, not native execution of mutant cards. No causal quantity/predicate counterfactual claim follows.

## Attempts, resource accounting and reproducibility

The shared append-only campaign ledger retains the failed initial compile, the successful collection retry, and the fit. Total durable debit is **932 applies, 2,400 updates and 39.715139750042 guarded active seconds** against ceilings 2,048/2,400/180. Summed supervisor receipt time is 39.715672084014 seconds; the preserved 0.000532334-second difference is negligible accounting-boundary overhead, not a reset. The first failed attempt used zero native calls/updates. Fit execution records 600 updates per arm, eight initial/final evaluation batches, two use interventions and four combined golden/program-vector batches, exactly the frozen allocation. The durable optimizer journal is the update source of truth.

All-attempt conservative sampled process-tree RSS is **595,574,784 bytes** (about 568 MiB); fit-only RSS is **413,237,248 bytes**. These are different scopes. Sampling is not a hard kernel memory limit; the guard's saved sampling limitation remains applicable. One compute worker/thread was configured. The recorded new paid-job count/spend is **0 / US$0**; this is the experiment's recorded spend, not an account balance claim. The cumulative US$100 batch cap and US$25 reserve remain parent-coordinated in [MODAL_BUDGET.md](MODAL_BUDGET.md).

Native source commit: `aa2526b84c5705dcbf12a7d043df29d57d41c2f2`; failed-build commit: `79f3aa68ab33faa8fd24d930559447650139df21`. Fit source commit recorded in result: **`fb8853c8a52d0ceed4d7c4221fbef008ccd2e747`**. Kessel: `c7ee39554901278cee70f61fd8b26fb1920696b3`. The parent registry records nine pure model-contract tests and actual-dataset validation passing before fitting, with zero model forwards before launch; this reviewer verified final source hashes and saved receipts rather than rerunning those checks. The independent native-data audit records 18,429 passing raw/dense, mask, source, catalog and journal assertions. See [the portable evidence](grounded-contrast-evidence/README.md), [actual native support](grounded-contrast-evidence/ACTUAL_NATIVE_SUPPORT.md), [fit result](grounded-contrast-evidence/fit-1/result.json), [numerical contract](grounded-contrast-evidence/fit-1/contract.json) and [fit guard](grounded-contrast-evidence/fit-guard-1/supervisor-receipt.json).

| Artifact | SHA256 |
| --- | --- |
| Model source | `473bc2324cf62c0437effd631e8fec3cc5930d2aeee0d00255da3bd08747eaf2` |
| Model tests | `cfe8e263c8774412af9905e18b95381e062320848c8dba25a044e72f82524923` |
| Dense dataset | `83a0ec4125e3d97b54ebd910925558bed0c18b779b706417991a650da1dfed52` |
| Dataset manifest | `c0206e0638a995b8237574cb11a697c35a0711d9a9f5dd9741314431bd4aea20` |
| Fit result | `733ce9aeecc373d5e17a4363b99970f2076e65ed753a9e5c338d4dad9fc0d68e` |
| Numerical contract | `29ba5cd39c3262bee8b2cd93719efdd96545d3e66d4f410084ca6a4048d660ce` |
| Fit guard receipt | `56a57f126e588a833839c6aa2b9d72b387e978ffbbfa85afd593c4606a6c07b4` |
| Correct-IR checkpoint | `4372f17d411f84fea05ce03b871aec30bf0dabb61aa17061b1eeb89af13dbf06` |
| ID-only checkpoint | `a67d847f415b8bad2d1938546f438269f9a849d5f3fc76ba72a269363c6da9dc` |
| Wrong-IR checkpoint | `d0852bbe660e7b7b18f045d17d26c6b282b21cfc0c3fa2e31fc2daba71f42609` |
| Context-only checkpoint | `4f75e14da23d39aebe142ebbc734174d480f43b76e76da2c3496204532a123ef` |

All checkpoint hashes above were recomputed from saved bytes. The package also retains named tensors, per-arm contracts, five-status goldens, row predictions and fixed batch/wrong-program schedules. These are standalone research fixtures; no production checkpoint, deck graph or deployed policy is changed by this result.
