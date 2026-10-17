# Recovered research and own-deck encoding audit

The saved research is recoverable at
`c39e1534664d6c055c844722f7251ee6cdf6c3ac` on
`codex/jepa-continuation-research`. Its six saved commits, exact report paths,
checkpoint hashes and the verified 274-file recovery archive are recorded in
[PROVENANCE.md](PROVENANCE.md). The complete broken-chat transcript was not
found locally; repository recovery does not establish chat-service recovery.
The original task4/task5 workspaces and running processes were left untouched.

## What the frozen actor already sees

The comparison source is WASM parity commit
`f9cbbd427689081d5f12829b1fe7edd76ca51fab`. The competitive snapshot was
`jepa_tx_gate_wasm-v1`, initially 3 wins / 7 losses without forfeits.

| Existing feature | Source under `bots/jepa/` | Limit |
| --- | --- | --- |
| Both sides' numeric deck sizes, discard counts, hand counts, resources and board aggregates | `features.py:98–122` | Sizes do not identify remaining cards |
| Own hand's summed/minimum cost, card types, playability and power | `features.py:138–164` | A hand-cost signal, not original or remaining deck curve |
| Hashed identities and printed/dynamic features for own hand, public boards, leaders and bases | `features.py:269–298` | Produces 32 slots; frozen runtime uses 24 (`wasm/runtime/src/backend.rs:22`, `tx_model.py:122`) |
| Offered action kind, card/target information, cost, stats, types, arena and ten keywords | `features.py:183–246` | Contextual action information, not a complete card-effect program |
| Separate legacy `disc`, `pool`, `poolk` auxiliary arrays during data preparation | `data.py:107–133,170–182` | Not read as base encoder inputs by `tx_train_torch.py:134–135`; unseen-pool construction is not a validated own observation ledger |

`features.encode` (`features.py:302–308`) exports state, actions and live-card
tokens. It does not export the actor's original main-deck multiset, remaining
identity counts, whole-deck curve or explicit synergy/capability representation.
Shared hashed identity weights can learn card associations from encountered
cards; that is not evidence that the actor knows its full deck or arbitrary
rules text. The model is not blind to all deck-related signals: hand/board
identities and numeric remaining size were already present.

The seven loss exports passed all 45 recorded checksums. They are omniscient
replays, not exact seat-redacted protocol observations, and remain consumed
diagnostics. No hidden order or opponent private identity was admitted as an
own-deck feature. Their recorded charges (1.45–8.99 seconds) are below the
45-second bank but do not expose per-decision or simulator effort.

## Small extension and matched evidence

The isolated implementation adds two dedicated context rows outside the 24
live-card slots. Shared card embeddings feed a count-weighted original bag;
printed curve/type/keyword/aspect/trait summaries and explicit known/unknown
status feed a 66→64 role projection. This adds 4,416 parameters. Existing state
and action attention can read those tokens, including simulated-leaf scoring.
The remaining row is deliberately unknown. The frozen competitive bundle is
unchanged; these experiments do not replace it.

[VALIDATION.md](VALIDATION.md) records encoder, actor, gradient, native/WASM and
legacy-regression checks. [PROBES.md](PROBES.md) separates input/latent
decodability from useful action quality. [LIVE_EXPERIMENTS.md](LIVE_EXPERIMENTS.md)
defines the later authorized small local auxiliary fit and dashboard artifacts.

For subsequent action learning, compare matched neutral, correct original and
wrong-own inputs with identical model shapes, initialization, batch/order,
labels, update counts and realized search budgets. Use grouped composition and
game holdouts and multiple paired seeds. Add remaining context only after its
observation ledger and updated future-target path pass branch/reset/conservation
tests. Count/curve readouts alone do not establish action-conditioned world
prediction or strength; hold out paired decision-quality consequences separately.

[CAPABILITY_WORLD_MODEL.md](CAPABILITY_WORLD_MODEL.md) grounds the next semantic
increment in Kessel's typed effects, costs, predicates, ordering, conditions and
granted abilities. It proposes shared semantics with role-specific modules and
action-updated deck belief, including calibrated stochastic draw targets.
No such semantic encoder or dynamic ledger is claimed to be implemented.
