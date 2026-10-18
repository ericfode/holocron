# Real-IR HP projection: sign repaired, accuracy gate still failed

PR45 failed learned usability at every seed. Its three-seed held endpoint MAE was
1.2494 versus 2.2052 for the matched printed control (43.34% lower), but the
architecture diagnostic failed seed29's OLD nonregression condition. The exact
selector/physics reference remained perfect. Neither result qualifies a whole-card encoder.

These five MAE columns are copied from closed step300 JSON, in native damage units:

| Method | Pooled | Unit | Base | Damage | Heal | Matched printed pooled |
|---|---:|---:|---:|---:|---:|---:|
| NEW seed17 | 1.2273 | 0.7843 | 1.9658 | 1.1759 | 1.2788 | 2.2264 |
| NEW seed29 | 1.2707 | 0.8603 | 1.9547 | 1.1104 | 1.4310 | 2.1946 |
| NEW seed43 | 1.2502 | 0.9018 | 1.8309 | 1.0886 | 1.4119 | 2.1948 |
| Exact reference | 0 | 0 | 0 | 0 | 0 | — |
| All-ones eligibility, zero effect | 2.1250 | 2.2000 | 2.0000 | 2.0000 | 2.2500 | — |

All five NEW MAEs exceed the .25 gate at every seed. Nonzero sign must reach .95,
healthy-heal max must be ≤.1, positive recall ≥.95, and OLD MAE allowance is .05:

| Seed | Nonzero sign | Healthy max | Positive recall | OLD nonregression | Usable |
|---|---:|---:|---:|---|---|
| 17 | .8571 FAIL | .0958 PASS | .5000 FAIL | PASS | FAIL |
| 29 | .8571 FAIL | .1835 FAIL | .6667 FAIL | FAIL | FAIL |
| 43 | .8571 FAIL | .1414 FAIL | .3333 FAIL | PASS | FAIL |

All96 HELD eligibility labels are positive: specificity/BA are undefined; all-ones is perfect. Recall alone cannot qualify discrimination.

The held cases mix distinct shifts. Heal3 is an unseen TRAIN operator×amount pair
(the literal3 already occurs with damage). Damage2 is trained on bases, but not on
units. Healing bases is an unseen TRAIN operator×target-domain pair. The damage/heal
union selectors are two complete templates nested in one held unit-or-base form;
their primitives and earlier selector development were exposed. These are not two
independent new mechanics, nor a uniform test of unseen literals.

The saved diagnostic's `space_base_pairs` isolates a specific NEW conditional-head
input contrast: JTL075 roots42/44 share source, heal3, BEFORE damage5, source S10 and
every consumed endpoint input except HP10 versus HP30. Both native truths are −3.
Below, δ is the saved routed prediction, p the saved eligibility probability, and
δ/p the already-computed conditional output; no new forward was used:

| Seed | Space δ | Space p | Space δ/p | Base δ | Base p | Base δ/p |
|---|---:|---:|---:|---:|---:|---:|
| 17 | −2.666158 | .903607 | −2.950572 | +.027480 | .029063 | +.945547 |
| 29 | −2.166393 | .770008 | −2.813467 | +.093031 | .031775 | +2.927802 |
| 43 | −2.444948 | .764774 | −3.196956 | +.076027 | .117044 | +.649559 |

This is a model-specific matched-input HP dependence witness, not an executed HP
intervention or proof that HP explains every error. Eligibility paths/public roles
differ. Positive p cannot flip a wrong conditional sign. Setting eligibility to its
known true value leaves that sign wrong and worsens saved held MAE at all seeds:
17:1.2273→1.5221; 29:1.2707→2.4142; 43:1.2502→1.4943. This unfitted δ/p oracle
rerouting is algebra on saved predictions, not a corrected model or a new fit.

The only correction tested was [endpoint HP projection](real_ir_hp_projection_model.py),
with [the fixed protocol](REAL_IR_HP_PROJECTION_PROTOCOL.md): zero target HP only at
the effect-state input, retaining HP knownness, all1,458 parameters and original
TRAIN rows/weights. The probe reused the seven exposed events with damage1/2/4 and
natural HP8/10/30. This tests state cells, not fresh cards or a whole-card encoder.

Four sources remain reserved and excluded from that probe: ASH259, LOF259, SOR132,
HMW158. ASH259/LOF259 remain one ground-damage nearclone group; space and friendly
damage give three conservative groups, not four independent families. All four
have zero actual27 copies; their IR was metadata-inspected, and two were adapter
fixtures. Reservation: `experiments/real-ir-hp-fresh-reservation.json`, SHA `64d114c8…`.

Coverage:152/1178 runtime-admitted definitions and9/251 actual27 identities
(47/1432 copies) describe serialization. PR45 evidence is56 authored roots,375
known coordinate comparisons and112 applies,
not375 independent cards or native conformance for152 definitions.

Sources: [PR45 results](REAL_IR_TRANSFER_RESULTS.md), [saved diagnostic code](real_ir_failure_diagnostic.py)
and `experiments/real-ir-failure-diagnostic-v1/diagnose-1/diagnostic.json` (SHA `245218f4…`).
PR45 froze `b663fe8b…`; diagnosis froze `cb269b0f…`, added .9130808329209685s and
zero native/NN/update/fits. Before HP testing, carry was919 applies/296.9465001246426s
with historical observed native aggregate null. Prior failures and $100/$25 limits persist.

## Closed HP result

Source freeze: `38532e7a1dafbeb55c7b738778a34e295a80e48c`. All3 baseline final
checkpoints reproduce PR45 exactly. Fresh primary30 endpoints exclude all exact
(operator,amount,damage,HP) tuples in PR45's39 endpoints;9 replay endpoints are
separate. None entered fitting. Raw is saved δ/p, routed is δ; exact reference MAE0.

| Seed | Arm | Fresh primary raw MAE | Routed MAE |
|---|---|---:|---:|
| 17 | Reproduced baseline | 1.1675 | .9313 |
| 17 | HP projected | .8504 | .8347 |
| 17 | Frozen printed control | 3.1526 | 1.7222 |
| 29 | Reproduced baseline | 1.6863 | .9576 |
| 29 | HP projected | .8328 | .8112 |
| 29 | Frozen printed control | 2.9688 | 1.6800 |
| 43 | Reproduced baseline | 1.1766 | .9205 |
| 43 | HP projected | .8560 | .7882 |
| 43 | Frozen printed control | 2.9408 | 1.6885 |

All3 corrected raw sign accuracies are1.0 (≥.95 PASS), relative raw improvements
are27.159%/50.615%/27.249% (≥20% PASS), and original TRAIN routed nonregression
passes all3. Every corrected pooled/unit/base/damage/heal raw MAE exceeds .25:
**all3 primary gates FAIL**. Old exposed HELD raw signs also reach1.0, but original
fully routed usability remains false at every seed. Heal2/5 both clip at fresh
unit damage1/2; this grid cannot establish repaired literal sensitivity.

The new native375 comparisons/112 applies are separate from PR45. The study used
1,815 forwards/1,800 backwards and updates/0 new fitted statistics, charging
15.562452751328237s. Final carry:1,031 charged applies/312.50895287597086s/observed
historical native count null; $100 ceiling/$25 reserve and $0 new paid work persist.
Closure `a0374b33…`, fit `3171e079…`, verification `ede76ba5…` are closed JSON pins
under `experiments/real-ir-hp-projection-v1/`. Verification passed; qualification
and `semantic_validated` remain false. This report performs no new scientific work.
