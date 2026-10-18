# Use the identity-free compositional encoder for the next research stage

The 1,258-parameter compositional design passes every predeclared elementary
semantic gate in all three seeds. The existing 10,016-parameter path-pooled
late-fusion graph fails every seed's full gate under the same objective and
training budget. Use the small identity-free design as the next research
architecture. The common two-head objective is learnable in this assay; this
does not justify replacing it, nor validate the earlier joint objective.
No additional experiment, deck composition, opponent execution or production
promotion followed this result.

| Seed | Existing no-ID eligibility BA | Existing damage MAE | Compositional no-ID BA | Compositional damage MAE | New full gate |
|---|---:|---:|---:|---:|---|
| 17 | 96.36% | 0.513415 | 100% | 0.087480 | pass |
| 29 | 96.94% | 0.499843 | 100% | 0.085771 | pass |
| 43 | 96.43% | 0.333933 | 100% | 0.068010 | pass |

The deterministic typed reference has no fitted parameters and matches every
one of the 3,584 native-known coordinates exactly: 2,048 eligibility and 1,536
effect observations. These include all sixteen offered, committed healthy-heal
zeros. It is a transparent reference for this grammar, not learned success or
a substitute label source.

The frozen [protocol](COMPOSITIONAL_TYPED_PROTOCOL.md) requires eligibility BA
at least .95 in every held owner, arena, cap, amount and operator slice, intended
damage MAE at most .25 and sign accuracy at least .95 in every operator/amount
slice, and healthy-zero recall at least .95 in both healing slices. New no-ID
eligibility, effect sign and healthy-zero recall are all 100%. Its worst
operator/amount MAE is .211252/.129867/.221594 for seeds 17/29/43, so the pooled
averages do not hide a failing slice. The existing graph's worst eligibility
slices are .942045/.942308/.937500 and worst effect MAEs are
1.109897/.826231/.410580. All three frozen relative-composite improvement and
endpoint nonregression gates also pass for the new design.

Identity removal improves transfer. Existing ID-on held damage MAE is
1.429–1.624 despite TRAIN MAE .019–.037; new ID-on held MAE is .701–.770 versus
.068–.087 without identity. The new no-ID arm passes every .02 BA/.05 MAE
identity-gap tolerance. These are matched training-arm ablations with identical
allocated graphs and initialization within each family; held identities are
UNK0. They are not same-checkpoint deletion of known held IDs. Candidate codes,
display text and program identities are absent from semantic fields, and all
128 public-input renaming/poison checks pass without extra neural calls.

The new encoder learns separate 8-coordinate bindings for selector owner versus
candidate owner, selector arena versus candidate arena, and cap versus printed
cost. A 16-coordinate selector head predicts eligibility without intent,
operator, amount or damage/HP. Separate operator/amount and damage/HP bindings
predict signed effect, routed through predicted eligibility and declared-target
equality. No analytical selector truth or effect prediction enters the learned
inputs. The old comparator retains the typed-path mean pool and late-fusion
modules, also excludes intent from eligibility, and uses the same two supervised
heads. The comparison tests an architecture bundle, including endpoint routing;
it does not isolate pooling alone. Similar old TRAIN and HELD no-ID errors also
mean this is an elementary trainability/approximation failure under the fixed
recipe, rather than pure held-combination failure.

The dataset is the complete 2^5 product of owner any/opponent, target arena
ground/space, cost cap 2/3, amount 1/3, and damage/heal. All source printed
profiles are identical. Each program has four roots and sixteen visible plain
units spanning both owners, both arenas and costs 2/3/4, with cheap twins.
Parity holds out sixteen full programs and all their roots; every atom and
every proper-subset combination occurs in TRAIN. Held eligibility uses 1,024
candidate coordinates and primary damage uses 48 actually committed intended
endpoints, nested within sixteen programs. Unknown invalid-intent futures never
become zeros. Three seeds, four arms and exactly 300 full-TRAIN updates per arm
use shared TRAIN class/stratum weights and the same half-BCE/half-SmoothL1
objective. All held metrics were computed after all updates finished.

This establishes a narrow elementary prerequisite, not real-card transfer,
numeric extrapolation, nested/multiple-effect composition, deck synergy or
playing strength. The shared objective and successful small model support
replacing the current research architecture within that scope. Preserve the
deterministic reference as an exact control for supported primitives. Earlier
negative transfers, wrong-ability gains and the failed fixed-weight correction
remain evidence; this experiment does not erase them.

The original native stage failed its 30-second limit during final pretty-JSON
serialization. The receipt is truncated. Its full 512-application reservation
remains charged, even though the append-only journal independently proves 256
successful applications and 128 complete cases. A separate
[saved-only recovery](COMPOSITIONAL_TYPED_SAVED_RECOVERY.md) reused those exact
cases with **zero additional engine calls**. Individual fixture-validation
captures were lost; frozen source/binary control flow proves validation preceded
journal creation, and that inference is explicitly separate from directly saved
actions/outcomes. The original failed ledger remains closed and unchanged.

The two linked attempts charge 43.689336666837335 seconds, within the original
185-second envelope. Total new work is 256 observed native applications (512
charged), 3,624 forwards, 3,600 backward/optimizer calls, two TRAIN preprocessing
fits, and zero paid jobs/spend. Final carry is 807 charged applications /
266.6158477078425 charged seconds; historical aggregate observed calls stay
unknown. The saved $100 ceiling/$25 reserve persist, without an account-wide
billing assertion. Production and the task5 workspace remain unchanged.

Scientific source freeze: `2d037a41d01b948e32f9f9bbd27c00e9439c564c`.
Saved-recovery source freeze: `90ea15b77aa03f80c05e7fe2c257e8e021a1005f`.

Local evidence roots are `experiments/compositional-typed-v1/` (closed failure)
and `experiments/compositional-typed-saved-v1/` (closed verified comparison) in
task7. The latter includes every initial/final per-example prediction, named
checkpoint, actual consumed input, native mask and TRAIN weight. Independent
saved-only verification reran no engine, model, fit or optimizer call.

- Fit result: `4061e9482b9280911c255e805134c2854b9a1c22a99a672e6471bb51f14fe8ef`.
- Verification: `3612d22d80cfe431ff4ff20e640b9ef9a187cb9033f0ee83b0c29c028460a335`.
- Closure: `fc71c60d567d95bd2ea0a1bdba42092bb8b26471fd9d0aeaa72a85d271bd1cd4`.
- Final ledger chain: `f633df4469954dbbb1f68ed52895c68615367639325a10595511f2aded3afe51`.

The [portable packet](compositional-typed-evidence/manifest.json) retains both
accounting histories, the opaque failed receipt and all saved comparison
artifacts. Its 80 files contain 101,145,830 decoded bytes / 4,039,427 stored
bytes. Manifest SHA256:
`70536441fce9f4cd1a3b59dd1781548a0a023adf96996d7f43e260298e9065a6`.
Bounded offline byte verification and both accounting-chain replays pass.
The 91 focused source/packet tests and 19 sealed-budget regression tests pass;
these software checks add no engine applications or learned examples.

```sh
python3 bots/jepa/own_deck/compositional_typed_saved_package.py --verify \
  --out bots/jepa/own_deck/compositional-typed-evidence \
  --expected-manifest-sha 70536441fce9f4cd1a3b59dd1781548a0a023adf96996d7f43e260298e9065a6
```
