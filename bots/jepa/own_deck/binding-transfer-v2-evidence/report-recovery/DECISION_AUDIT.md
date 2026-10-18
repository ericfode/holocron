# Independent saved-JSON decision review

Official saved-output verification passed 93,471 checks with zero mismatches. Both predeclared narrow benefits are supported: C reduces seed-mean MAE from 1.000000 to 0.420372 (57.96%); R from 1.293299 to 0.524695 (59.43%). Every corresponding seed improves.

The stronger typed-transfer criterion fails. The learned typed model beats all six zero/mean/ridge designs for each R variant in every seed, but ID-only has lower LOF_053 error in all three seeds. The frozen random card encoder with a trained readout also beats it on both variants at seed29. ID-only beats the corrected model on the C panel in all three seeds. Routing direction is correct throughout the corrected R panel, but the ID and frozen-encoder controls also achieve this; it is not unique evidence of learned program semantics.

| Seed | C baseline | C corrected | R baseline | R corrected |
|---|---:|---:|---:|---:|
| 17 | 1.000000 | 0.390420 | 1.305627 | 0.522206 |
| 29 | 1.000000 | 0.129694 | 1.256007 | 0.483920 |
| 43 | 1.000000 | 0.741002 | 1.318262 | 0.567958 |

The saved corrected-model family-first, TRAIN-scaled primary-error mean across seeds is train 0.002523, state_held 0.245217, family_held 0.234453, joint 0.653377. The joint damage head also remains inaccurate on native zero outcomes: corrected mean MAE 1.059372 versus zero-baseline MAE 0. These are descriptive, separate from the narrow R stat panel.

Phase B charged 70.07557979295962s of 80s, retaining failed prep5s and failed fit60s. The new report/baseline/verification stages charged 4.071298917988315s with zero new native calls, neural forwards or updates; 64 head-fit attempts used 64 solver calls. Cumulative binding accounting remains 208 charged applications / 188.08889674965758s, with historical observed applications unknown. The original fit remains failed with observed neural counters unknown; the durable 5,400-update/5,436-forward prefix and saved outputs are separate evidence. Unsaved gradients remain unavailable. New paid spending is $0.

C covers one seen damage program on fresh states; R covers two positive-stat variants within one broad family. Repeated contexts, correlated heads and three seeds are not independent family trials. Generic semantics remain unsupported/false. This does not establish capacity, playing strength, complete-card semantics or the cause of the earlier conditional-task failure.

This review used JSON and simple arithmetic only: no model/NumPy imports, prediction evaluation, numerical fit or new metric run. [decision-audit.json](decision-audit.json) contains every control comparison, saved-metric summaries, exact source SHA-256/byte pins and ledger arithmetic. [decision_audit_json_only.py](decision_audit_json_only.py) is the review source.
