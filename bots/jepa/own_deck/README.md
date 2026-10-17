# Own-deck context

This isolated increment makes the actor's original deck available to the JEPA
transformer through two dedicated context tokens. It adds encoding, model and
export contracts; it does not provide trained deck-aware weights or evidence
of improved play. The existing competitive bundle and checkpoint bytes remain
the frozen reference. Recovered research provenance is in [PROVENANCE.md](PROVENANCE.md).

## Information contract

The original bag is the unordered multiset in the actor's `hello.deck.deck`.
It contains the main draw-deck cards, with copy counts. Separate leader, base
and sideboard fields are ignored. A main-list entry whose printed type is
leader, base or token is unsupported metadata and makes the original row
unknown; it is not accepted as a complete main-deck description. Printed
metadata comes from `hello.cards`.

The second token is reserved for the current unordered draw-pile multiset.
**This first increment always marks remaining composition unknown.** It does
not derive a count ledger by subtracting the current board or hand. A zero
content row with `known=0` is not a known empty draw pile. Numeric draw-pile size
already exists in the live state encoding.

This stage does **not** yet meet the full dynamic-world-state requirement.
Remaining composition/belief must evolve with actions and the hand, board and
other zones, and appear updated in future-state JEPA targets. Original
composition is fixed provenance, not a substitute for that evolving state.
The transition, conservation and stochastic-target requirements are specified
in [DESIGN_VERIFICATION.md](DESIGN_VERIFICATION.md#required-dynamic-transition-contract).

Only the actor's original deck is encoded. Opponent setup/private zones,
canonical simulator state, sampled-deal provenance and draw order are not
inputs. The supplied main-deck entry order has no meaning; permuting entries or
splitting one count into equivalent duplicate entries must not change the rows.
Identity uses the existing hashed card-ID convention, so it is not a
collision-free vocabulary or an encoding of arbitrary ability text.

Malformed counts or missing metadata must remain visible through the status
features. They must not silently produce a supposedly complete, known deck.

## Small model extension

Both rows sit outside the existing 24 live-card slots. They attend with the
state and live-card context in the existing two-layer, width-64 transformer.
Move prediction sees the same expanded context. The shared latent feeds the
value head, and the same context contract must be supplied when the planner
judges a live simulated leaf. This is not an auxiliary diagnostic head.

Each input row has 207 numbers:

| Range | Content |
| --- | --- |
| 0–24 | Original/remaining role, enabled/known status, total/unknown/distinct counts, coverage, printed-stat means, card/arena fractions and nine curve buckets |
| 25–34 | Ten printed keyword aggregates |
| 35–40 | Six aspect aggregates |
| 41–48 | Eight hashed trait bins |
| 49 | Malformed-input aggregate |
| 50–206 | Copy-count histograms over the existing 64/32/61 identity tables |

Count and identity totals use the same 60-card normalization. The 157 identity
bins aggregate through the existing shared 16-dimensional embedding tables;
concatenating that result with the 50 metadata numbers gives 66 inputs to the
new width-64 projection. Two learned role embeddings distinguish original and
remaining. The projection and role parameters are new and untrained.
Metadata fractions and means use all accepted copy counts as their denominator;
unknown metadata contributes zero to those numerators and is separately
reported by unknown count and coverage. A valid explicit empty original list
has `known=1` and `coverage=1`; a missing list has `known=0`.

The neutral control retains the same expanded architecture and two active
token slots, with role labels and no deck content. It controls for the changed
attention/pooling structure and extra parameters. Existing checkpoints use the
legacy path unless the new contract is explicitly enabled; an untrained
extension must not replace the competitive reference.

[DESIGN_VERIFICATION.md](DESIGN_VERIFICATION.md) maps the shared 16-dimensional
card embeddings, role-specific `din`/`sin`/`ain` projections and masked attention
to exact sources. State and deck tokens attend within the context; each action
attends to context plus itself, without action-to-context backflow. Input
availability, downstream use and real playing strength require different
evidence. A null wrong-deck probe on a weak fixture does not by itself diagnose
an encoder failure.

## Boundary checks

The focused checks for this increment should establish these contracts:

1. Canonical bag invariance under entry permutation and equivalent count splits;
   copy-count changes affect the original row.
2. Opponent/private-state changes and unused draw-order fields cannot change
   either row. Remaining status stays explicitly unknown.
3. Invalid counts, unknown cards and absent deck/metadata have explicit status;
   known empty and unknown are distinguishable.
4. Deck tokens do not displace live-card tokens, including observations with
   more than 24 visible cards.
5. The new tokens can affect state, predicted action latents and their value
   outputs when enabled, while the neutral arm with the same weights receives
   no deck-specific content.
6. Python reference and generated inference agree on the same original,
   unknown-remaining and neutral fixtures. Export receipts identify source,
   parameter and fixture hashes; parity is not a playing-strength result.
7. Legacy checkpoint/model behavior and original checkpoint bytes remain fixed.

These checks use synthetic metadata and deterministic numerical fixtures. A
bounded synthetic forward/backward/optimizer-update check may verify gradients
and export round-tripping; its receipt must label that synthetic update and
count it separately. This is no real-data fit, gameplay or strength result.
No downloaded opponent or rules-engine game is needed for these checks.

## Optional trajectory preparation

The existing preparer accepts an opt-in own-deck context. For already available
seat-redacted `swu-traj/1` decision trajectories and pinned printed metadata:

```sh
python3 bots/jepa/data.py --workers 1 \
  --card-data /path/to/pinned-card-json-directory \
  --own-deck original --own-deck-cards /path/to/pinned-hello-cards.json \
  --out /tmp/own-deck-rows.npz /path/to/seat-redacted-trajectories.jsonl.gz
python3 bots/jepa/pack_data.py --replays /tmp/own-deck-rows.npz \
  --tmax 24 --out-dir /tmp/own-deck-pack
```

These are example commands, not an executed data allocation. `--own-deck-cards`
is a JSON array in the `hello.cards` format. The preparer reads each actor's
original list from the game header, caches it per game/seat, and stores
`own_deck[N,2,207]`. This array and `gid`/`seat`/`seq` grouping metadata survive
packing independently of live-card `--tmax`. Labels, opponent hands and legacy
unseen-card arrays are never passed to the own-deck encoder. Omitting
`--own-deck` retains legacy preparation with no new field. The reserved
`original-plus-remaining` option still writes an unknown remaining row and is
not a valid depletion experiment.

The consumed rated-loss exports have omniscient replay boards, rather than exact
seat-redacted protocol decisions with own resource identities. They were not
silently converted into model inputs. No automatic engine reconstruction or
legacy `from_replays.js` game replay was performed. Admitting those exports as
training trajectories would require a separate reconstruction/redaction audit.

The old `tx_train_torch.py` CLI is the legacy training route; it does not consume
this new field. `own_deck_model.run_torch` is an import-safe differentiable
forward callable accepting `own_deck` with shape `[B,2,207]`; its returned
state/action latents and `value_torch` support a separately reviewed objective.
Passing the packed field into that callable must be explicit. No broader
trainer or real-data fit was launched here.

## Matched experiment design

The next proposed representation comparison has three arms with identical
architecture and feature definition: no-context neutral, correct original,
and a fixed wrong-own-deck control. Wrong deck assignment stays within each
split and changes no live state, action, label, role or remaining-unknown
status. It is a proposed control recipe, not a new CLI variant. A fourth
original+remaining arm is deferred until a remaining-card ledger passes its
observation/simulation-branch contracts and future target context is wired.
Curve-only and metadata-removal arms can follow if the original comparison is
useful. Changing metadata and depletion together would not isolate either gain.

Use at least three paired initialization seeds, identical shared tensors,
per-tensor initialization rules, row/batch order, update counts, objective,
optimizer and model-selection rule. Freeze c-clock resourcing. Initially keep
search routing/candidate sets fixed, or predeclare and report the effect of
changed score gating on actual search effort. Group holdouts by game and actual
canonical deck-composition fingerprint; include held-out deck swaps that share leader/base to test whether
the model uses composition. The seven previously inspected rated losses are
diagnostics, never an untouched validation/test set.

Frozen deck-blind target latents or leaf-judge scores alone cannot establish
deck-sensitive action quality. The common objective needs action-return or
pairwise-gap evidence whose consequences can depend on the deck. An outcome
observed only for the chosen action is not a counterfactual pairwise label.
JEPA losses and detached deck probes must remain the same across arms; probe
accuracy demonstrates accessible information, not useful decisions.
The NumPy/Torch interfaces can accept separate context for a future target
call, but no new deck-aware EMA objective or target-training CLI is wired.
Original composition stays static from the original header; remaining stays
unknown until the ledger exists. Never recompute original composition from a
future private simulator state.
Draw/search uncertainty also requires a declared conditional-future target
semantics: a belief summary or stochastic/distribution-aware latent objective,
not a claim that a deterministic predictor knows the future drawn card.

The [compute proposal](COMPUTE_PROPOSAL.md) gives the concrete unlaunched fit and
paired-game ceilings. No real-data allocation is spent by this increment.
Before a training or game pilot, pin the exact data/holdout manifests, seeds,
step/transition budgets, wall and memory limits, one-worker supervision,
checkpoint selection and stop conditions. Later paired games must share deck,
seed, seat, opponent bytes and per-game thinking banks, and report incomplete
or unsupported runs. No larger run is launched by this implementation.

## Future remaining-card ledger

A future ledger must track stable observed card instances and current draw-pile
membership, not current controller or only cards presently on the actor's
board. Own hand, resources, discard, upgrades, captured cards and known removed
cards all matter. Generated tokens and leader/base copies must not deplete the
original main-deck bag. Transfers, returns, searches and shuffles require
explicit supported handling; when own observations cannot establish the bag,
use unknown status rather than guessed subtraction. Reconcile known counts
against the numeric deck size.

Every speculative simulation branch needs its own ledger clone. Restoring a
root restores its ledger; simulated draws never update the live-game ledger.
The policy may consume only the actor-visible observation at that branch,
never hidden draw order or opponent private information.
