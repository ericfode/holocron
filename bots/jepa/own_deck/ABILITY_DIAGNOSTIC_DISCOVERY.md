# Ability diagnostic discovery draft

This is a post-result, JSON-only diagnosis. All eight cards—LAW_045, ASH_071, LOF_077, JTL_078, LAW_133, JTL_140, ASH_081 and IBH_104—and both scenario families are now exposed discovery data. ASH_081 and IBH_104 were held from training, but cannot be presented as fresh tests of a subsequent correction. No NumPy, arrays, model calls, native applications, optimization or numerical fitting were used for this report. Means and differences below are arithmetic on already saved JSON metrics/predictions.

The independent supplemental verification is PASS (212,610 checks, zero mismatches). That confirms the saved calculation/provenance checks; the learner primary benefit gate and ability-sensitivity gate both failed. Checks, coordinates, intent repetitions and seeds are not independent examples. The held semantic support is two canonical cards.

## Where the wrong-ability gain comes from

On IBH_104, swapping in ASH_081 abilities improves the anchored equal-head MAE from 0.522552 to 0.299857 across the three seeds. Eligibility contributes 81.20% of that arithmetic improvement.

| IBH anchored head | Correct abilities | ASH abilities | Scope |
|---|---:|---:|---|
| target_allowed | 0.851956 | 0.490320 | Four roots; A/B membership known even for unavailable intents |
| target_removed | 0.193149 | 0.109394 | Only two actually committed roots; unavailable-intent futures remain unknown |

In scenario 0, A is the own cost-2 ground unit and B the opponent cost-3 space unit. Native IBH eligibility is [0,1]. The correct-ability model predicts approximately [0.99,0.00] for both intents in all seeds: the opposite of IBH and the same cheap-target pattern as TRAIN LOF_077 (cost≤2). With the healing ability, B rises to about 0.995–0.999; A is also often high. In scenario 1, A is the opponent cost-3 ground unit and B the own cost-2 space unit; native eligibility is [1,0], but the swapped model mostly predicts both legal. This is consistent with a broad “any unit” proxy correcting false negatives, rather than learning IBH’s opponent/cost conjunction. It does not establish that this is the unique internal mechanism.

The removal gain is concentrated at scenario-0 intent-B root 29: mean MAE 0.205550→0.003683. Scenario-1 intent-A root 30 gets worse on average, 0.180748→0.215106; seed 29 improves there while seeds 17 and 43 worsen. No removal outcome is scored for unavailable-intent roots 28/31.

Whole-ability replacement changes trigger, resolver owner/type/predicate/count/mode and effect together. Therefore the observed change proves that the ability subtree influences this fitted function, but does not isolate correct use of an effect operator. Frozen-full also improves on IBH, 0.431251→0.335822, so useful latent perturbations are not unique to the trained encoder.

## Controls and the healing contrast

Correct-ability anchored MAEs, mean of seeds 17/29/43:

| Arm/baseline | ASH_081 damage delta | IBH_104 eligibility/removal |
|---|---:|---:|
| learned-full | 1.124210 | 0.522552 |
| frozen-full | 0.992648 | 0.431251 |
| printed-only | 1.227631 | 0.293142 |
| ID-only | 1.109079 | 0.373460 |
| public-only | 0.902492 | 0.400640 |
| zero | 0.750000 | 0.500000 |
| train_mean | 0.750000 | 0.500000 |
| public_ridge | 1.323185 | 0.404041 |

ASH’s selected scenario-0 targets are predicted to take roughly +1 damage, although the native delta is −1 healing; nonselected anchors are mostly near zero. Routing is partly learned while polarity is wrong. Its whole-ability swap changes the mean only 1.124210→1.128624, hiding seed disagreement: errors worsen for seeds 17/29 and improve for 43. Zero and the public-only arm outperform the full learned arm on this held card.

The full learned model does fit TRAIN: mean all-role TRAIN eligibility MAE is 0.00435. Thus these saved results do not indicate a basic loss/optimizer disconnection. The current public source context also retains unit printed power/HP and knownness, so the two held cards have different non-IR context (ASH unit versus IBH event); ID-UNK is not a proof that their complete inputs coincide.

## A verified intent nuisance and limited support

Native membership is measured at the initial target prompt, before target selection, and is identical across intents A/B for the same source/board. Yet the two intended-reference R channels enter the shared candidate representation for all seven branch heads (public_input_binding_model_v1.py:194; effect_identifiability_fit.py:222–227). On IBH seed 43, scenario 1, predicted eligibility of A changes 0.2679404318332672→0.8652969002723694 when only declared intent changes A→B (roots 30→31); native eligibility stays [1,0]. This is unwanted intent dependence of the eligibility head. It does not establish the cause of every transfer error.

The predeclared difference-of-differences also needs careful reading. It can obtain the correct sign from its trained LOF contribution while the held program is flat or wrong. For example, learned seed 17 predicts scenario-1 D=0.008312735706567764 against native D=2. The original gate is preserved; a later fresh test should require the held source’s own contrast and a declared magnitude/margin, not just the composite D sign.

TRAIN contains only one cost-comparator resolver, LOF_077 card.cost≤2; IBH combines a new threshold 3, opponent ownership and upTo selection. Two positive/zero templates for an overall head do not establish multiple-threshold interpretation. Negative healing in TRAIN occurs only on ownBase via LAW_133 (−3/−1); held ASH applies healing to units. That is a target-class/composition change with one healing template, not independently supported healing-family transfer. The primary anchor scenarios couple ownership and cost, with ground/space roles and damage levels also differing; the extra helper roles provide some additional variation. A stdlib-only source-profile audit of the pinned actual-corpus coverage inventory finds 115 unique full printed profiles among 115 admitted cards (the eleven whitelisted fields; aspect/trait/keyword/type arrays treated as sets), so no full-printed-profile impossibility witness exists here.

## Proposed fixed-weight probes and pending correction

Freeze all checkpoints, normalization and inputs before these discovery probes; do not tune on the two exposed cards. Use the same actual program/public inputs and all saved control arms. No probes below have been run for this report. The parent’s next panel is planned for 33 frozen-weight forwards, with additional IBH states and no training. Those are state-held discovery probes on exposed cards, not fresh whole-card tests; no compatible fresh whole card is available within the current frozen vocabulary. Actual forward counts/results will require their own receipt and report.

1. Toggle only declared intent A↔B on an otherwise identical source/board, rebuilding the two R fields consistently. Eligibility should be invariant; actual endpoint heads should reroute. The saved intent pairs already demonstrate the nuisance. A proposed correction excludes R only from the eligibility logit, retaining R for actual endpoints/source aftermath, with shared widths/weights and no added capacity. This is pending controlled probes and a fresh test, not a demonstrated fix of learned-IR benefit.
2. With public/printed input fixed, alter one IBH resolver property at a time: owner opponent→any; cost threshold 3→2; count 2→1 as a null intervention in this exactly-one+Done assay. The first two have distinct eligibility predictions; count should leave these observed one-choice endpoints unchanged. Compare against printed/ID/public controls and frozen-full. These are synthetic IR functional probes, with interpreter/proxy expectations until separately native-validated; they are not newly observed game outcomes.
3. Alter only ASH healing amount 3→1. The known damage-1 scenario is capped and should remain −1; scenario-1 intent-A should change −3→−1, while the nonselected anchor stays zero. Distinguish a correctly bound quantity response from a generic ability-subtree perturbation. Do not use a heal→damage swap on these possibly lethal fixtures as if numeric after-labels remained known.
4. For a later confirmatory assay, use fresh canonical/alias and program-group held cards plus unseen states; support owner and multiple cost thresholds and healing target classes in TRAIN. Prefer actual identical helper cards with swapped owners to isolate ownership while holding cost/stats/arena fixed. Require each held program’s own known eligibility/action contrast, all-control performance and meaningful magnitude; rank only two genuinely committed, known outcomes. Keep unknown futures unknown and retain all exposed results as discovery.

## All-head versus anchored metrics

The following are native-unit, per-head MAEs averaged over seeds, copied from the already saved all-role cell metrics. They are not a combined score across unlike units. All-role errors include easier unchanged/nonprimary roles and must not replace the anchored primary above. A dash means unsupported.

| Head | TRAIN (13 roots) | State held (12) | Program held (4) | Joint (4) |
|---|---:|---:|---:|---:|
| play_available | 0.030088 | 0.025331 | 0.030636 | 0.032263 |
| play_committed | 0.005953 | 0.178421 | 0.499942 | 0.209738 |
| cost_resource | 0.036255 | 1.300942 | 2.726902 | 1.244372 |
| source_in_arena | 0.009554 | 0.085244 | 0.010343 | 0.075733 |
| source_in_discard | 0.008425 | 0.192809 | 0.497723 | 0.219754 |
| source_in_hand_after | 0.005262 | 0.179762 | 0.499994 | 0.203564 |
| source_damage_delta | 0.003371 | 0.122682 | 0.068714 | 0.095385 |
| source_shield_delta | 0.001037 | 0.044325 | 0.008634 | 0.069700 |
| source_exhausted_after | 0.006694 | 0.007539 | 0.005120 | 0.006532 |
| target_allowed | 0.004347 | 0.056232 | 0.342741 | 0.327737 |
| target_removed | 0.005121 | 0.050686 | 0.024607 | 0.019948 |
| target_damage_delta | 0.018936 | 0.243626 | 0.264531 | 0.285547 |
| target_exhausted_delta | 0.013360 | 0.043475 | 0.021369 | 0.045044 |
| target_shield_delta | 0.014753 | 0.043981 | 0.032203 | 0.035914 |
| target_power_delta | 0.010932 | 0.039224 | 0.017222 | 0.030281 |
| target_hp_delta | 0.016040 | 0.028249 | 0.039432 | 0.033594 |

## Exact saved anchored predictions

Pairs below are [anchor A, anchor B]. Values are the original JSON float representations, without rounding. “Unknown” removal entries are omitted from the primary, not zero labels. Scenario/intent are from native-plan.worlds[root].

### IBH_104

| Root/scenario/intent | Seed | Eligibility truth | Correct prediction | Swapped prediction | Removal truth | Correct removal | Swapped removal |
|---|---:|---|---|---|---|---|---|
| 28/s0/anchor_a | 17 | [0.0, 1.0] | [0.993607759475708, 0.0058351620100438595] | [0.32789140939712524, 0.9988136291503906] | unknown | unknown | unknown |
| 28/s0/anchor_a | 29 | [0.0, 1.0] | [0.9909867644309998, 0.009814268909394741] | [0.9481918811798096, 0.9969311952590942] | unknown | unknown | unknown |
| 28/s0/anchor_a | 43 | [0.0, 1.0] | [0.9969461560249329, 0.008010944351553917] | [0.9805877804756165, 0.9982585310935974] | unknown | unknown | unknown |
| 29/s0/anchor_b | 17 | [0.0, 1.0] | [0.9988251328468323, 0.0017455759225413203] | [0.5660188794136047, 0.9954215884208679] | [0.0, 1.0] | [0.16423045098781586, 0.8677146434783936] | [0.002032544696703553, 0.9958277344703674] |
| 29/s0/anchor_b | 29 | [0.0, 1.0] | [0.9987114667892456, 0.0030320987571030855] | [0.9783832430839539, 0.9931801557540894] | [0.0, 1.0] | [0.15618930757045746, 0.5268398523330688] | [0.0036005463916808367, 0.9952424764633179] |
| 29/s0/anchor_b | 43 | [0.0, 1.0] | [0.9989855885505676, 0.001135147176682949] | [0.9953149557113647, 0.9940294027328491] | [0.0, 1.0] | [0.032023653388023376, 0.7245907783508301] | [0.004351867362856865, 0.9968178272247314] |
| 30/s1/anchor_a | 17 | [1.0, 0.0] | [0.018267903476953506, 0.046586453914642334] | [0.7739846110343933, 0.9918482303619385] | [1.0, 0.0] | [0.5671207904815674, 0.001856353715993464] | [0.03895610570907593, 0.0019047074019908905] |
| 30/s1/anchor_a | 29 | [1.0, 0.0] | [0.03996066749095917, 0.9911166429519653] | [0.9901183247566223, 0.9961270689964294] | [1.0, 0.0] | [0.3826729655265808, 0.006863960064947605] | [0.8126927614212036, 0.004070411901921034] |
| 30/s1/anchor_a | 43 | [1.0, 0.0] | [0.2679404318332672, 0.996065080165863] | [0.6513423323631287, 0.9972521662712097] | [1.0, 0.0] | [0.97672438621521, 0.0022861778270453215] | [0.8667315244674683, 0.0030415647197514772] |
| 31/s1/anchor_b | 17 | [1.0, 0.0] | [0.10246134549379349, 0.0016216601943597198] | [0.8069443702697754, 0.9985470175743103] | unknown | unknown | unknown |
| 31/s1/anchor_b | 29 | [1.0, 0.0] | [0.15667641162872314, 0.9198105931282043] | [0.9808318018913269, 0.9989123344421387] | unknown | unknown | unknown |
| 31/s1/anchor_b | 43 | [1.0, 0.0] | [0.8652969002723694, 0.9938556551933289] | [0.8297306299209595, 0.9981889128684998] | unknown | unknown | unknown |

### ASH_081

| Root/scenario/intent | Seed | Damage-delta truth | Correct prediction | Swapped prediction |
|---|---:|---|---|---|
| 24/s0/anchor_a | 17 | [-1.0, 0.0] | [1.0030431747436523, -0.02292191982269287] | [1.2327542304992676, 0.060356661677360535] |
| 24/s0/anchor_a | 29 | [-1.0, 0.0] | [1.3071939945220947, 0.06448477506637573] | [1.0942524671554565, -0.10375802218914032] |
| 24/s0/anchor_a | 43 | [-1.0, 0.0] | [1.2048649787902832, 0.07858070731163025] | [-0.1280890554189682, -0.37017425894737244] |
| 25/s0/anchor_b | 17 | [0.0, -1.0] | [0.012003101408481598, 0.9862087965011597] | [0.26274925470352173, 0.9037034511566162] |
| 25/s0/anchor_b | 29 | [0.0, -1.0] | [-0.0016598999500274658, 1.0848408937454224] | [0.38855549693107605, 1.0018397569656372] |
| 25/s0/anchor_b | 43 | [0.0, -1.0] | [-0.016981393098831177, 1.1014759540557861] | [0.3745521903038025, -0.6364611387252808] |
| 26/s1/anchor_a | 17 | [-3.0, 0.0] | [-0.5113892555236816, -0.4787202775478363] | [-0.6259416341781616, -0.6640526056289673] |
| 26/s1/anchor_a | 29 | [-3.0, 0.0] | [-0.08568724244832993, 0.1104290634393692] | [0.4996418058872223, 0.3179650604724884] |
| 26/s1/anchor_a | 43 | [-3.0, 0.0] | [-1.1600351333618164, -0.013011671602725983] | [-0.6868077516555786, -0.2103019803762436] |
| 27/s1/anchor_b | 17 | [0.0, -1.0] | [-0.7994251251220703, 0.4241735339164734] | [-1.140637755393982, 0.9172054529190063] |
| 27/s1/anchor_b | 29 | [0.0, -1.0] | [-0.2792578935623169, 0.5216225385665894] | [0.011816360056400299, 1.1970958709716797] |
| 27/s1/anchor_b | 43 | [0.0, -1.0] | [-1.1775647401809692, 0.049689844250679016] | [-0.7074921131134033, -0.29462623596191406] |

## Exact source pins

All paths are beneath `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/`. JSON field paths used: `fit.results[sSEED:ARM].evaluations[200]` and `.ability_swapped_evaluation`, each `.primary[CARD].heads[HEAD].roots`; `.cells[CELL].heads`; `.paired_contrasts`; `baselines.evaluations`; `native_plan.worlds`; `sealed_plan.documents`.

| Source | SHA256 | Bytes |
|---|---|---:|
| actual-corpus/coverage-v2/actual-corpus-coverage.json | `dd3ec9dc77f1f888d070f7e8ed0ab20290c347c75c75f6fe01f5504ce43f0480` | 1498747 |
| semantic-discrimination-repair-v1/fit-1/result.json | `a0c2cae5b15d0c43847e3aff3ad346a04a9029b90183f4c940b08cf42d20f281` | 21900403 |
| semantic-discrimination-repair-v1/baselines-1/result.json | `f2be52af8db1f3f54a4892ee93e53342ba5a4057d69ad1a788d7e1707ad05a0e` | 1387072 |
| semantic-discrimination-repair-v1/prep-1/dataset.manifest.json | `01b52828b766b7570331c034af7304ff06d345228602c01ab3237b1524f1eca7` | 587818 |
| semantic-discrimination-repair-v1/native-plan.json | `6ccb1db9e711b540d7e049469621f34ecc91edab956e96c52f2ceefbf0dd4de3` | 166997 |
| semantic-discrimination-verification-v1/verify-result.json | `73544bc3d312497747e11bc10936a54d5b6f11e9f4fffdbff758400df37c3d0a` | 180733 |
| semantic-discrimination-repair-v1/prep-1/sealed-fit-plan.json | `478cf7d627eae7a483f57a64232b4f9839ddefc77969af18d2baa64f42ee541a` | 209331 |

Original verifier failure and its full five-second charge remain preserved. The later supplemental PASS does not relabel that attempt or authorize more training. This report changes no old report, source, data, checkpoint, ledger or publication pointer.
