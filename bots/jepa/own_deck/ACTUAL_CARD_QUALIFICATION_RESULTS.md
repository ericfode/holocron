# Actual-card qualification: negative held result

The learned whole-card encoder fitted the training fixtures but **did not
qualify as a transferable semantic card representation**. Its held-card and
joint errors exceed ID-only, unused typed and shuffled typed controls, and the
training-only constant prior. This remains a single-seed, eight-card diagnostic;
no tuning, extra evaluation or retraining follows from these results.

The fixed native dataset contains eight actual-list cards, 32 public roots and
38 applies: 24 settled endpoints, eight unavailable plays, 23 paid/settled plays,
and no native errors or pending outcomes. Every card has at least two paid,
settled witnesses. The split is 18 training / 6 card-held / 6 state-held /
2 joint roots. LOF_155 is the held nonunique restriction within the seen
defeat/upgrade family. JTL_217 is one wholly held exhaust-primitive card, not
a sample supporting effect-family generalization. These eight cards cover
65/1,432 main copies (4.54%); the other 107 runtime-admitted identities have
not acquired measured card representations here. Sentinel attacks, upgrades
as source cards, attack/death/constant/multiple-ability behavior and gameplay
remain unqualified.

The table is mean train-scaled MAE over the nine training-varying heads, with
equal head weight. Lower is better. Unknown/constant training heads are retained
in the per-head results, but cannot silently enter this primary macro.

| Final arm / baseline | Train18 | Card-held6 | State-held6 | Joint2 |
| --- | ---: | ---: | ---: | ---: |
| Learned correct typed | .01166 | .33094 | .04426 | .31769 |
| ID-only, held UNK0 | .00991 | .16135 | .03722 | .16073 |
| Unused typed encoder + trained head | .07171 | .14104 | .10071 | .16200 |
| Shuffled typed | .07583 | .10872 | .10054 | .11214 |
| Train-only constant mean/rate | .37729 | .30631 | .34952 | .29743 |
| Literal zero heads | .54201 | .53468 | .61724 | .57866 |

All sixteen heads are preserved below. Support is known **coordinates**, not
independent observations. MAE is in native units/probability, without scaling.
The card-held cell comprises only two identities and three states; endpoint
heads have four supported roots, membership three roots/24 coordinates.

| Head | Train known | Card-held known | Correct MAE | ID MAE | Constant MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| play_available | 18 | 6 | .01211 | .00501 | .44444 |
| play_committed | 12 | 4 | .29471 | .01057 | .08333 |
| cost_resource | 12 | 4 | 2.84376 | 1.25811 | 1.50000 |
| source_in_arena | 12 | 4 | .17168 | .01269 | .33333 |
| source_in_discard | 12 | 4 | .01029 | .01347 | .25000 |
| source_in_hand_after | 12 | 4 | .27820 | .00974 | .08333 |
| source_damage_delta | 8 | 4 | .26859 | .20889 | .12500 |
| source_shield_delta | 8 | 4 | .19961 | .18056 | .25000 |
| source_exhausted_after | 8 | 4 | .03620 | .00870 | .00000 |
| target_allowed | 48 | 24 | .20326 | .32986 | .37500 |
| target_removed | 5 | 2 | .40053 | .26131 | .50000 |
| target_damage_delta | 0 | 1 | .29131 | .38383 | .00000 |
| target_exhausted_delta | 0 | 1 | .61391 | .05711 | .00000 |
| target_shield_delta | 0 | 1 | .19194 | .25746 | .00000 |
| target_power_delta | 0 | 1 | .24493 | .27897 | .00000 |
| target_hp_delta | 0 | 1 | .08727 | .28200 | .00000 |

There is a narrow positive membership signal: correct typed improves held-card
target membership balanced accuracy to .77778 versus ID .55556 and the
constant/zero .5; sensitivity is .66667 and specificity .88889 (6 positive,
18 negative coordinates). Joint balanced accuracy is .65455 versus ID .46364,
with sensitivity .4 and specificity .90909 (5 positive, 11 negative). Ordinary
accuracy alone would hide the all-negative classifier: it already scores .75
on card-held membership. The membership gain does not offset the native
outcome regressions or qualify the representation.

Resource error is strongly signed: card-held mean residual is −2.84376.
For JTL_217, funded state0 predicts cost −.15174 against native cost5; state2
predicts commitment .10935 against native1 and hand retention .85414 against
native0. Across all four states, its primary macro is .56188 versus ID .27875
and the constant prior .34218. LOF_155 is also worse than ID (.09767 versus
.05355), although better than its constant prior (.27121). These per-card
numbers include their state-held root and are not extra independent tests.

Five candidate-delta heads have **zero known training labels**, so neither
their zeros nor JTL_217's single joint exhaust +1 are trained binding tests.
Their output rows can move through decay/shared features without supervised
mechanic learning. Training target_removed has only five positives and no
negatives; JTL_217's observed non-removals expose this limitation (correct
mean removal probability .81490). source_exhausted_after is likewise trained
only on eight positives. Correct source damage/Shield predictions on held
zero-change endpoints are retained as negative cases, not discarded.

Saved weights show that the encoder itself moved. Relative to the saved
unused typed encoder, 4,368/4,416 typed-encoder coordinates change, with total
ΔL2 4.71338; the residual against a decay-only reference is 4.71352. Numeric
projection ΔL2 is .22581, nonlinear leaves 2.16301 and card projection 1.31931.
All eight vector rows differ by L2 3.02388–5.68809, including held LOF_155
3.80786 and JTL_217 4.51231. Thus this is not head-only fitting. Parameter
movement and vector separation do not establish useful semantics. A complete
initial checkpoint was not stored: the unused typed encoder is the frozen
cloned initialization reference; the ID-only frozen encoder matches it exactly,
and correct/unused initialization predictions are byte-identical.

Accounting and artifact checks pass. There are exactly 800 durable updates
(global1…800; 200 per arm), 800 training forwards/backwards, eight initialization/
final evaluation forwards, zero export forwards/native calls/paid jobs in the
card worker. Its receipt records 3.304105417 seconds and 325,943,296 peak RSS
bytes, within 60 seconds/1 GiB/one CPU. Every graph allocates 11,168 parameters;
trainable counts are 11,056 correct/shuffled, 6,752 ID and 6,640 unused typed.
All four checkpoint hashes/counts/finite arrays pass. All eight saved prediction
metric blocks and both baselines recompute exactly; vector JSON float32 bytes
equal the saved 8×16 NPZ banks; held ID vectors remain zero. Source/data pins,
train-only schedules, fresh wrong-card exclusion and protected inputs pass.
This audit executed no model, backward, optimizer or native action.

Sources: implementation `whole_card_encoder.py:47,109,175,236,255,301,327,408`,
frozen source commit `00eae396791e785edfa82ff1a013706961815151`, SHA256
`b310315d153b3cdfe3439c4f242d9b07e07a1c2ce16c46ede4cf9084a8e0d8a2`.
External `experiments/whole-card/fit-1/result.json` SHA256
`593314724ee98d1b2e81cd2910dd7485b17d32ea36665b61e4d86e5af3e20cff`;
contract `7beab74914110c5f380e188976f263afd6d843ebf07468d27e3d7152034f0141`;
progress `a736fe299b9cbf01d02b41064d3799a409ac297f7402ea48feab786b720c43df`.
Independent `experiments/whole-card/card-qualification-audit.json` SHA256
`f378dd7ad0849978da5f52203a0b2266da671d1926eff8df4dc7af38edf565a3`
contains full checkpoint/prediction pins, weight-group and vector-row changes.
Native NPZ `e3f8cc1227f59fa61bbbea230780afec61ebb3f5c9bba2fb3a7be906533187aa`;
sealed plan `88da6979813a3a655d6dba1779da476c8447bc9b584e42f3ba81c12d72d55e4b`.
