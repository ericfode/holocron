# Shared card semantics, role modules and verification limits

The proposed separation is appropriate: reuse card identity semantics, project
state/deck/action roles into a common width, let state and actions attend to the
deck, and give future JEPA targets the appropriate future information set.
The first three parts are implemented as a small opt-in extension. Updated
remaining-card context and a new deck-aware EMA training objective are not
implemented by this increment.

**The dynamic requirement is not fulfilled by stage 1.** Remaining-deck
composition, or a belief over it when uncertain, is part of the evolving world
state alongside hand, board and other zones. Actions must update that state,
and a future-state JEPA target must encode its updated deck/belief. The fixed
original bag supplies provenance and prior composition; copying it into every
position is not a replacement for dynamic remaining state.

## What the implementation shares

| Input role | Actual path | Source |
| --- | --- | --- |
| Printed card identity | Shared 16-dimensional sum of `emb_a[64]`, `emb_b[32]`, `emb_c[61]` lookup factors | [`model.py:22`](../model.py#L22), [`model.py:57`](../model.py#L57) |
| Original/remaining bag identity | Copy-count-weighted sum using those same three tables, without a main-deck token cap | [`own_deck_model.py:39`](../own_deck_model.py#L39) |
| Deck token | 50 metadata/status coordinates + 16 pooled identity coordinates; `din` projects 66 → 64, then a learned original/remaining role embedding is added | [`own_deck_model.py:16`](../own_deck_model.py#L16), [`own_deck_model.py:53`](../own_deck_model.py#L53) |
| State token | Separate `sin` projection, 73 → 64 | [`tx_model.py:43`](../tx_model.py#L43), [`tx_model.py:106`](../tx_model.py#L106) |
| Live-card token | Separate `tin` projection, 21 live-card coordinates + 16 shared identity coordinates → 64 | [`tx_model.py:45`](../tx_model.py#L45) |
| Action token | Separate `ain` projection, 62 action coordinates + 16 shared identity coordinates → 64, plus its horizon embedding | [`tx_model.py:53`](../tx_model.py#L53), [`tx_model.py:128`](../tx_model.py#L128) |

The shared table weights provide a shared representation of hashed card
identity. They do not by themselves prove learned synergy or an understanding
of arbitrary card text. The new deck projection is untrained engineering
scaffolding. Original and remaining share `din`; their role/status inputs and
learned role embeddings distinguish them. This is count-aware bag pooling plus
the transformer's nonlinear processing, not a newly trained per-card semantic
MLP. Hash collisions and the coarse trait/keyword summaries remain limits.

## Attention and downstream paths

In the existing two-layer, width-64 graph, the context consists of the state,
up to 24 live cards, and two additional deck tokens. Context tokens attend to
one another. Thus the state token can attend to both deck tokens and the deck
tokens can attend to the state/live cards. Padded live cards remain masked.

Each action/horizon token attends to the context and itself, never another
action token. Context cannot attend back to actions. The same structure is
implemented by the optimized NumPy context/action paths and the masked Torch
forward: [`tx_model.py:136`](../tx_model.py#L136),
[`tx_model.py:59`](../tx_model.py#L59), and
[`own_deck_model.py:88`](../own_deck_model.py#L88).

The state token and mean context readout produce the 96-dimensional latent;
action prediction uses that latent and the action's attended representation.
The value head consumes state or predicted latents. This gives deck information
a path into state, action prediction, scalar judgment and live simulated-leaf
judgment. It does not guarantee that training will use that path well.
See [`tx_model.py:149`](../tx_model.py#L149),
[`own_deck_model.py:109`](../own_deck_model.py#L109), and the actor's
[`encode_net`](../jepa_bot.py#L171). Opponent-perspective reply scoring receives
unknown deck context rather than the root actor's original bag.

## Future targets: available interface, missing experiment

The NumPy and Torch forwards accept an explicit own-deck context per batch.
A future target-encoder call can therefore receive context appropriate to its
future observation. This is an interface capability, not an already wired EMA
objective: [`own_deck_model.py:53`](../own_deck_model.py#L53),
[`own_deck_model.py:60`](../own_deck_model.py#L60).

The original multiset remains the original header/hello list at every time.
It must not be reconstructed from future private/canonical simulator state or
reduced when cards are drawn. The current preparer deliberately caches the
original context per game/seat: [`data.py:53`](../data.py#L53). Current actor
and prepared-data inputs leave remaining composition unknown; no new target
pipeline supplies known remaining composition.

Only a validated observation ledger can later supply an updated remaining
multiset. It needs separate state for each speculative branch, exact root
restoration, reconciliation against numeric deck size, and explicit unknown
status when reconstruction fails. No hidden draw order, opponent private
zones, future labels or sampled-bank provenance may enter the context.

A later deck-aware JEPA experiment must explicitly pass that context to the
future target encoder and include the new encoder tensors in its declared
target/EMA policy. It also needs common deck-sensitive consequence supervision;
matching a frozen deck-blind target alone can suppress useful new information.
The legacy trainer's EMA calls and update remain in
[`tx_train_torch.py:294`](../tx_train_torch.py#L294) and
[`tx_train_torch.py:434`](../tx_train_torch.py#L434); they do not consume this new
field. The import-safe new forward is not a new target-training CLI.

## Required dynamic transition contract

Represent the current information state as visible zones plus an unordered
remaining multiset when exact, or a declared belief over that multiset when
not exact. An action/observation transition updates both the zones and this
deck state together. Current numerical deck count is a consistency check,
not enough to reconstruct card identities. A known empty deck, an unknown bag
of known size, and a probabilistic bag are different states.

| Transition | Required deck/zone accounting when observations support it |
| --- | --- |
| Draw | Move one card from remaining to own hand; subtract its identity only when legitimately observed. Before the draw, preserve uncertainty about which card will move. |
| Search/reveal/select | Update using the actor's permitted reveal and selected destination; do not retain or infer unobserved order. A search can change a belief even without changing deck size. |
| Discard/mill | Move the observed instance to discard from its actual source. Discarding from hand does not itself deplete the draw pile; milling does. |
| Return/shuffle | Move supported returned instances into the unordered remaining bag; erase any order assumption. Returning a previously drawn original card increases remaining count without changing original provenance. |
| Create | Record a new instance and its origin. Tokens/leaders/bases do not deplete original main-deck copies. If a supported rule creates a non-token card in the draw pile, account for that addition separately from original copies. |
| Transfer/capture/remove | Track original owner/provenance separately from controller and current location, including nested upgrades/captured cards and known removed zones. A controller change is not a new card or an automatic return to deck. |

Conserve stable instances across all tracked locations and reconcile copy
counts with the public numeric deck size. Newly created instances require
explicit additions; known removed instances require an explicit out-of-deck
location rather than disappearing from the accounting. Canonical card-code
counts must not deduplicate distinct copies, while nested views must not
double-count the same instance. Do not derive remaining as original minus only
the actor's currently controlled board. If a source, identity, owner or
transition cannot be reconstructed from allowed observations, retain supported
knowledge and mark the rest uncertain/unknown; never silently invent an exact
bag. A concrete belief representation and supported transition set remain
design work after the engine/IR audit, not a semantic implementation here.

Each simulated branch needs an isolated state/belief transition history, with
root restoration returning both zones and deck/belief to the same root. The
real actor's ledger must not absorb a hypothetical draw. Only branch-visible
future observations may update that branch; the simulator's hidden deal/order
is not a policy feature.

## Conditional stochastic future targets

An action that draws an unseen card can produce several legitimate future
hands and remaining bags. An updated target must encode the actual future
actor information set for that sampled continuation, including its updated
deck/belief, while the current encoder sees only current information. The
training record must distinguish these two times and their masks; no future
card identity may be copied into the root input.

This conditional future can be stochastic even though original composition is
fixed. A deterministic predictor cannot be interpreted as knowing the actual
future draw. Squared error across different future latents can regress toward
an average; it does not identify a particular unseen card or establish a
correct distribution. The next design must declare whether it predicts an
information-state/belief summary, samples a stochastic future latent, or uses a
distribution-aware objective over shared sampled continuations. Evaluate that
choice under matched realized compute and calibrated uncertainty. Do not add
true draw order to make a deterministic target easier.

Consequently, enabling the deferred depletion arm requires more than filling
the second row: observation-grounded dynamic transitions, future deck/belief
encoding, a target/EMA policy containing the new context parameters, and an
objective appropriate to its conditional stochastic target must be specified
and checked together. Stage 1's forward/backward/parity checks establish none
of those dynamic guarantees.

## Three different evidence levels

| Evidence level | What can establish it | What it does not establish |
| --- | --- | --- |
| Input information | Correct own-list encoding, unknown flags, privacy/permutation checks and cross-language feature parity | That a model uses the information |
| Latent and downstream use | Controlled bag interventions, measured latent/action-logit changes, gradients, and parity through deployed inference | Better decisions or generalization |
| Real playing strength | Prospectively held-out, paired games under the same opponents, starts, seats and resource budgets | A broad strength claim from a tiny or dependent sample |

A null wrong-deck intervention is not automatically an encoder failure. The
fixture may offer only equivalent actions, terminate before future draws,
share the same encoded deck statistics, or use an insensitive/untrained value
head. Check the encoded rows, latent deltas, action-logit deltas and margins
separately. Latent changes with unchanged action ranking are a different
finding from missing information at the encoder boundary. Conversely,
nonzero numerical sensitivity alone is not useful deck reasoning.

Before any real-data comparison, propose a bounded numerical smoke that reports
latent/prediction variance, covariance or effective rank, pairwise distances
and gradient norms on a fixed diverse fixture bank. These are collapse and
wiring diagnostics, not an allocation for more optimization or evidence of
strategy. Low prediction loss alone can discard information that matters to
later action choices.

The next proposed evaluation should include action-conditioned one- and
multi-step probes; controlled effect, cost, target and copy-count changes in
rule-grounded fixtures; and decision quality on protected held-out games/deck
clusters under equal realized budgets. Distinguish a legal world change from
merely corrupting an input feature. For uncertain draws, evaluate a declared
conditional distribution with a proper scoring rule and calibration, or
evaluate conditional outcomes. The realized next card is one stochastic sample,
not a card the current state is assumed to know. No such larger evaluation is
executed by this document.

## Matched controls

The next unlaunched comparison has three controls with the same two slots,
tensor shapes, trainable-parameter policy, initialization, objective and compute:

1. **No-context neutral:** original/remaining role labels remain, deck content
   is absent. This is the expanded-architecture control, distinct from the
   frozen legacy baseline.
2. **Correct original:** the actor's actual original multiset and metadata.
3. **Wrong own deck:** the same feature contract with a prospectively assigned
   different original multiset, while state, actions, labels and remaining
   unknown status stay fixed. This is an input-control recipe, not an existing
   extra CLI variant or a demonstrated training result.

Freeze the wrong-deck assignment within each train/validation/test partition;
do not source it across a holdout boundary. Require a different canonical
composition fingerprint and retain the assignment map in the input manifest.
Match status/coverage and total-count conditions so a model cannot identify the
control from missingness alone. Prefer same-leader/base swaps and test the
effect of composition; when an intervention contradicts already observed own
cards, label it as corrupted-input sensitivity rather than a legal
counterfactual game state.

Group splits and uncertainty by actual deck composition fingerprints and
game/seed clusters, not by shuffled input entries, repeated windows or assigned
control fingerprints. Keep candidate/return banks common and protected
holdouts untouched. A fourth original+remaining arm is deferred until the
ledger and future target context are supported. The explicit larger ceilings
for these proposed controls are in [COMPUTE_PROPOSAL.md](COMPUTE_PROPOSAL.md).

## Method references and scope

[I-JEPA, *Self-Supervised Learning from Images with a Joint-Embedding Predictive
Architecture*](https://arxiv.org/abs/2301.08243) studies prediction of semantic
target-block representations from image context.
[V-JEPA 2, *Self-Supervised Video Models Enable Understanding, Prediction and
Planning*](https://arxiv.org/abs/2506.09985) studies video pretraining followed
by action-conditioned robot post-training and physical planning. These are
methodological precedents for representation prediction and, in the latter
case, action-conditioned prediction. Neither paper validates this card-game
encoding, its proposed count/belief transition semantics, or the stochastic
target/control experiments above. Those remain engineering hypotheses to test
against the actual rules and protected decision outcomes.
