# Typed intent/application: narrow reconstruction succeeds; application gates fail

The preregistered factorized candidate fails development and terminal acceptance at
all three seeds. Keep it as research evidence; no production or deck qualification.

The TRAIN-only diagnosis (`6d5c296e6eecbbdd6d7806d76756fbccb60ddd1b`) found
consistent raw target/output units and correct frozen weights. Baseline TRAIN raw
MAE .6222/.8753/.6563 and near-collapsed damage3/4 responses rule out a purely
held-extrapolation account. Four nominal-literal/native differences are explained
by legitimate healing caps; clipped reference has zero mismatches. This supports
testing intent/application separation, not a claim about why optimization failed.

The single correction exposes identity2 and raw amount1 from the existing effect8,
then lifts predicted intent3→8 into the learned application head. HP, damage,
knownness and S10 remain available. HP is retained for survival/application; this
counter-healing cap uses current damage. Existing eligibility still excludes HP.
Both auxiliary arms allocate1517 parameters versus current1458; the matched control
has identical initialization/objective but keeps the latent route and an unused lift.
S10 remains an alternate application shortcut. There is no exact clipping/sign oracle.

Scientific source freeze: `6ef78f992cbb6cc1bd218c5bbb67a8f6fa7a945f`. All2700 updates
used only original TRAIN40 and finished before terminal native collection. Current
final weights reproduce PR45 exactly at all seeds. All24 evaluation forwards were
deferred until terminal data admission. No tuning or additional seeds followed.

Development:56 new boards on seven exposed events,29 nonreplay endpoint observations
and6 replays after excluding tuples from both prior grids. These are endpoints,
not29 distinct tuples or new cards. One lethal counter stays unknown, with physical
removal audited separately. Terminal: SOR132 only, eight boards/four known deltas;
16 positive/32 negative helper eligibility labels. Its damage3 is already familiar.
The unit S10/space-selector/whenPlayed changes are confounded; entering source is
captured and eligible but excluded from the scored six-helper panel.

Raw is saved delta/p at native-allowed committed endpoints; routed includes predicted
eligibility. All numbers below are raw damage-unit MAE.

| Seed | Arm | Dev raw | Dev routed | Terminal raw | Terminal routed |
|---|---|---:|---:|---:|---:|
| 17 | current | 0.9913 | 0.8033 | 0.5451 | 0.5098 |
| 17 | matched-aux-latent | 1.1210 | 0.8819 | 0.3403 | 0.3204 |
| 17 | factorized-intent | 1.1546 | 0.8567 | 0.3911 | 0.3587 |
| 17 | frozen-hp-projected | 0.7500 | 0.7056 | 0.3387 | 0.3194 |
| 17 | frozen-printed | 3.2926 | 1.8576 | 3.9057 | 3.8255 |
| 29 | current | 1.5112 | 0.8031 | 0.4052 | 0.4001 |
| 29 | matched-aux-latent | 1.2123 | 0.8139 | 0.6606 | 0.6636 |
| 29 | factorized-intent | 0.9360 | 0.9921 | 0.3069 | 0.3052 |
| 29 | frozen-hp-projected | 0.7136 | 0.6743 | 0.3319 | 0.3064 |
| 29 | frozen-printed | 3.2237 | 1.7867 | 3.6628 | 3.6292 |
| 43 | current | 1.0006 | 0.7622 | 0.7063 | 0.6932 |
| 43 | matched-aux-latent | 1.1189 | 0.8186 | 0.4284 | 0.3874 |
| 43 | factorized-intent | 0.9877 | 0.9917 | 0.6119 | 0.6029 |
| 43 | frozen-hp-projected | 0.7790 | 0.6540 | 0.6636 | 0.6500 |
| 43 | frozen-printed | 3.2806 | 1.7949 | 4.1220 | 4.1105 |
| — | Deterministic reference | 0 | 0 | 0 | 0 |
| — | All-ones eligibility / zero effect | 2.2759 | 2.2759 | 3 | 3 |

Every factorized pooled/unit/base/damage/heal MAE, both raw and routed, exceeds .25.
Development sign and healthy-heal gates fail all seeds. Routed improvement versus
the matched auxiliary control is2.866%/−21.896%/−21.151%, below20% throughout.
TRAIN nonregression fails17 and passes29/43. Every full development gate fails.

Identity reconstruction is1.0 at all seeds, but nominal amount remains underfit:

| Seed | TRAIN5 amount MAE | Exposed7 amount MAE | Terminal1 amount MAE | Dev raw sign | Dev healthy raw max |
|---|---:|---:|---:|---:|---:|
| 17 | 0.7438 | 0.6525 | 0.0155 | 0.8462 | 0.9840 |
| 29 | 0.4111 | 0.3885 | 0.0172 | 0.8846 | 0.4709 |
| 43 | 0.4882 | 0.4667 | 0.0360 | 0.9231 | 0.5683 |

Terminal identity/amount syntax gates pass, but known endpoint MAE fails .25 in
all seeds. Helper recall1.0 hides specificity.5 and balanced accuracy.75 (<.95);
all learned comparators have that same BA. Exact reference BA1; all-ones BA.5.
All terminal gates fail. The frozen HP-projected comparator is better on this
development panel than the factorized candidate, but also fails absolute accuracy.

The matched comparison does not support this bottleneck as an accepted correction.
It exposes remaining nominal-amount underfitting and state/selector application
failures; correct type labels alone do not establish useful semantics. Full cached
joint slices by amount/operator/domain/owner/arena/health/damage/HP/cap/prior-seen
status and source are in score-1/result.json. Boards/seeds are nested observations.
The reused old helper carries a stale all-positive-HELD scope string; terminal
counts above are mixed-class and the numeric BA/specificity are defined.

ASH259/LOF259 and HMW158 remain untouched:three sources/two conservative groups.
Old reservation64d114c8… is unchanged; a separately frozen amendment releases only
SOR132 after fitting. All selected source cards cover zero actual27 copies.

Actual new native evidence:371 development plus52 terminal coordinate comparisons,
112+16=128 calls; removal audit separate. Serialization coverage stays152/1178
runtime rows and47/1432 deck copies. These quantities are not interchangeable.

V1 saved verification stopped on heterogeneous historical journals (KeyError/schema),
after all scientific stages had completed. Its full10-second failed charge remains.
The reader repair uses the already-frozen accounting chain helper and a
separate20-second, zero-call saved-verification allocation. No model/data/loss,
predictions, native outcomes, failed seed or original root is changed.

Verification recovery PASSED:24 prediction files/18 checkpoints, all source/data
pins, native masks, exact current reproductions, shared auxiliary initial states,
metrics/gates and the checkpoint-before-terminal boundary checked. Native-data
reconstruction reuses frozen D; saved metric/gate arithmetic is independent. No
saved-weight forward parity is established.
Recovery source e739fb8…; saved-only allocation charged1.9094321669545025s, zero
scientific calls. Original failure remains closed-failed and its10s is not credited.
Final carry1,159 charged native/348.9213339596754s/observed historical native null.
Financial ceiling$100/reserve$25 persist; new paid
work$0. Original workspaces, opponents, conversion and production remain unchanged.
