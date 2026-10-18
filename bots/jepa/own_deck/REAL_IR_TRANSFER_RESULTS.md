# Real-IR transfer: verified execution, failed learned usability

The role-bound learner reduced three-seed held endpoint MAE from **2.2052** for its matched numeric printed control to **1.2494** (**43.34%**), but **every seed failed the preregistered usability gate**. The architecture diagnostic also failed: seed 29 regressed against the late-fusion comparator beyond the allowed .05 MAE. These results do not qualify a general card embedding or a replacement architecture. The deterministic selector/physics reference remained exact.

Source freeze: `b663fe8b282b43f35f41d147f27472bd604b2c96`. The [protocol](REAL_IR_TRANSFER_PROTOCOL.md) and prelabel reservation fixed five TRAIN cards (IBH013, IBH066, IBH061, TWI174, IBH059) and two HELD cards (JTL075/SOR074 and TWI170/SHD178). Numeric-abstracted complete templates were reserved whole, including aliases: three TRAIN templates and two operator-specific HELD templates nested in **one new unit-or-base selector form**. This tests composition of previously developed primitives, not a new primitive. The seven event sources account for **zero actual27 main-deck copies**.

All seven complete real card definitions were unchanged. Each saw the same eight declared-intent states over six natural public candidates: ground HP8/damage3, space HP10/damage5, one per owner, and two bases at damage5, with healthy ground/base variants. This gives 40 TRAIN and 16 HELD roots. Native outcomes supplied 336 eligibility coordinates and 39 committed intended deltas (23 TRAIN, 16 HELD), all **375 exactly matching the reference**. Canceled/unoffered future effects stayed unknown. All 56 fixture-validation captures and offered action chains were retained; 112 native applies completed.

NEW full and its printed control share all 1,458 parameters and complete initial weights; the control gates only the 13 semantic descriptors to zero. S10 is a narrow numeric printed-stat/type vector, not all printed metadata. OLD uses the same P13/C17/S10 inputs but a different 1,506-parameter path-pooled graph and eligibility factorization, so its comparison is an architecture bundle. All nine runs used the same objective and 300 full-TRAIN updates. Every initial/final evaluation was deferred until all 2,700 updates finished.

Final HELD metrics below are copied from the saved step-300 JSON. MAE is in native damage-counter units; lower is better. Each row has 16 intended endpoints (10 unit, 6 base; 8 damage, 8 heal), 14 nonzero endpoints and two healthy-heal zeros. Recall uses all 96 held eligibility coordinates. All 96 are positive, so **specificity and balanced accuracy are undefined for every arm**; the all-ones eligibility rule is perfect.

| Seed | Arm | Pooled MAE | Unit | Base | Damage | Heal | Positive recall | Nonzero sign | Healthy max abs |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 17 | new-full | 1.2273 | 0.7843 | 1.9658 | 1.1759 | 1.2788 | 0.5000 | 0.8571 | 0.0958 |
| 17 | old-late-fusion | 1.5115 | 1.2193 | 1.9986 | 0.0954 | 2.9277 | 0.6146 | 0.8571 | 1.9849 |
| 17 | new-printed-only | 2.2264 | 2.3622 | 2.0000 | 2.3310 | 2.1217 | 0.5000 | 0.5000 | 1.8023 |
| 29 | new-full | 1.2707 | 0.8603 | 1.9547 | 1.1104 | 1.4310 | 0.6667 | 0.8571 | 0.1835 |
| 29 | old-late-fusion | 0.9185 | 0.4477 | 1.7032 | 0.3874 | 1.4495 | 0.6458 | 0.8571 | 1.2776 |
| 29 | new-printed-only | 2.1946 | 2.3113 | 2.0000 | 2.6004 | 1.7888 | 0.0000 | 0.5000 | 1.0503 |
| 43 | new-full | 1.2502 | 0.9018 | 1.8309 | 1.0886 | 1.4119 | 0.3333 | 0.8571 | 0.1414 |
| 43 | old-late-fusion | 1.6191 | 1.5193 | 1.7855 | 0.8156 | 2.4226 | 0.6146 | 0.7857 | 2.4729 |
| 43 | new-printed-only | 2.1948 | 2.3116 | 2.0000 | 2.6909 | 1.6986 | 0.0000 | 0.5000 | 0.8032 |

The exact reference has held pooled MAE 0, nonzero sign accuracy 1, healthy maximum 0 and positive recall 1. The all-ones-eligibility/zero-effect control has pooled MAE 2.1250 and positive recall 1. These controls are saved and independently scored; they require no neural forward or fitted baseline.

The per-seed NEW gate requires MAE ≤.25 in every listed endpoint slice, nonzero sign ≥.95, healthy-heal maximum ≤.1, and descriptive positive recall ≥.95. The separate architecture diagnostic requires ≥20% pooled three-seed MAE improvement over S10 and per-seed MAE ≤OLD+.05. The relative S10 condition passed; the full architecture diagnostic did not.

| Seed | Endpoint slices | Nonzero sign | Healthy max | Positive recall | OLD nonregression | Usable | Eligibility discrimination qualified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | FAIL | FAIL | PASS | FAIL | PASS | FAIL | No |
| 29 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | No |
| 43 | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | No |

Both aggregate flags are false: `usability_passed=False`, `architecture_diagnostic_passed=False`; `semantic_validated=False`. One visible limitation in the saved endpoint records is that all three NEW seeds predict small **positive** deltas for the two damaged HELD healing bases whose truth is −3. This is a descriptive observation, not a causal diagnosis or permission to retune on these exposed held cards. All seeds and controls remain reported.

The saved-output verifier passed with zero mismatches. It rebuilt native labels, features and reference values using the same frozen data converter, then independently recomputed scores, gates and TRAIN count-derived weights. It checked all 16 prepared arrays, six consumed-input arrays, 18 prediction files, 18 named checkpoints, the three matched NEW initial states, finite loss rows and the durable evaluation barrier. It did **not** reconstruct neural modules or test saved-weight forward parity. This is verified evidence and scoring, not an independent second native converter or a general semantic validation.

This closed allocation used **112 native applies, 2,718 forwards, 2,700 backwards/optimizer updates and two TRAIN-only weight-statistics fits**, in **16.129547375952825 charged seconds**. No paid jobs or recorded spend, new card conversion, opponent execution or production change occurred. Linked cumulative charges are **919 native applies / 296.03341929172166 seconds**; historical aggregate observed native applies remain **unknown (`null`)**. Earlier failures and their charges are preserved. The saved $100 ceiling/$25 reserve is unchanged and is not an account-wide billing claim.

Main evidence pins are SHA-256 over the exact closed files. Paths below are under `experiments/real-ir-transfer-v1/`, except the reservation.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `experiment-closure.json` | 4038 | `04bd16a7c32fcc3fa99fb5f10a840ba33e0031676c3febb548e6f9049d043167` |
| `metadata-1/native-plan.json` | 71310 | `0c9e7ae51b34f2c25ed64cfa1aebd0f0b171809efb8604b1a52734313415d1e0` |
| `native-1/receipt.json` | 4177284 | `f4d8aa2bc7665b06b149c5b73c88e00c03440435ae6796d550e0ca43218a9519` |
| `native-1/transitions.jsonl` | 5914096 | `d8f701795c2a538030ddedd5c384e788892fc656ea5aed367d77b04bdb52290a` |
| `prep-1/manifest.json` | 205860 | `4583e0b607c02da810ac0280b848ee563203ac6a34a99ea991e6458667375170` |
| `fit-1/result.json` | 376049 | `673a42ad980e2775dcc2341018a8205f867d1fa4d6a411c4bedac9749a5de5ef` |
| `verify-1/verification-result.json` | 156895 | `48121121336a27a7dc54e8488d3610abcfbfe670dafab8eff94d3bcd47dfbed7` |
| `campaign-ledger.jsonl` | 4888483 | `6d04e181f152ad084f15f7768c7f6425c3cea09c59c30c561277542e6a36f6ec` |
| `../real-ir-coverage-v3/coverage-1/holdout-reservation.json` | 280206 | `d46bb580b0b1884d6988875eb20038bd405f91f2995821e8c717da2aa05f8486` |

This report reads only closed JSON evidence. No arrays, new predictions, numerical fitting, training or engine execution were performed to write it.
