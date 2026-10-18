# Capability semantics and dynamic deck state: proposed next increment

The implemented increment is original-deck input plumbing. Its shared card
embeddings, printed metadata and keyword aggregates do **not** encode an effect
program, and its remaining-deck row is always unknown. It does not yet satisfy
the requirement that remaining deck be dynamic world state updated by actions.
No semantic encoder, remaining ledger or new world-model fit is implemented here.

## Grounded source and limits

Read-only inspection used Kessel commit
`c7ee39554901278cee70f61fd8b26fb1920696b3` in the saved pilot checkout. Its
`swu-card-ir/v1` schema supplies a stronger source than a bag of card names:

- `crates/kessel/src/ability_ir.rs:833` defines costs; `:890` defines typed
  effects with quantities and targets; `:1000` distinguishes sequence,
  simultaneous and conditional effects. `:1142` retains trigger, optionality,
  costs, target resolvers, conditions, `then` and `ifYouDo` continuations.
- `crates/kessel/src/selector_contract.rs` preserves target owner/type/zone and
  predicates. Source, chooser, payer, recipient and attachment host are different
  roles; they must not collapse into one generic target vector.
- `crates/kessel/src/ability_ir.rs:1442` retains executable-program timing and
  instructions; `:1472` has reviewed gained-host ability templates. A granted
  ability needs its host/source relation and future trigger, not merely a
  "grant" flag.
- `compiler/deck-play-ir.js:39` retains search scope/count, selected/remaining
  bindings, completion order and shuffle behavior. The compiler README at
  `:735` explicitly says complete deck-search cards remain runtime-rejected
  pending a randomness/execution contract. Converted IR is not runtime support.
- `crates/kessel/src/model.rs:903` exposes offered actions as kind, physical
  card, argument, method and label. It does not provide a universal stable
  action-to-ability-program reference. Mapping a label to an IR node needs a
  reviewed adapter; ambiguity must remain unknown.

The schema has explicit size/nesting bounds and compiler-only construction
programs. Unsupported or partial cards cannot become a supposedly complete
capability embedding by dropping unknown operations. Pin catalog/source hashes
and both conversion and runtime-admission status. The current printed-metadata
`known` flag is not a certificate of full rules coverage.

Concrete catalog examples at that commit are `LAW_083` (conditional draw followed
by a separate conditional top-deck resource), `ASH_103` (defeat a selected
friendly Imperial unit, then resource only through `ifYouDo`), and `LOF_051`
(attach to a Force host, granting that host an optional On Attack heal of
another unit). Their catalog records illustrate why operation/keyword counts
alone cannot describe a card. Catalog shard SHA-256:
`0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`;
compiler hash:
`d188828527e6459ea9c7b2673e4746960923f9d0904c190026e6d454b45a548e`.

## Small coherent extension

Deck-list order is not a semantic input. Canonicalize card identities and sum
copy counts before encoding; preserve multiplicity. The current implementation
does this structurally, using sorted canonical counts in Python and an ordered
map in Rust, then count-weighted invariant pooling. It has no positional
embedding for entries in the deck list. Original/remaining role embeddings
identify information roles, not arbitrary card positions.

Any later per-card interactions must also obey the set contract: shared card
encoders and permutation-equivariant attention, followed by sum/count pooling
or invariant role-query attention. A learned deck-list position must not be
introduced. Grouped-count attention would need explicit multiplicity weights
to agree with expanded copies; treating a grouped entry as one copy would
violate the contract. Repeated permutations and grouped/expanded-copy checks
apply to features, latent queries and downstream scores, within declared
numeric tolerances.

This invariance applies to unordered composition. Ordered children inside an
effect program, sequential continuations and timing remain ordered. A future
belief state must preserve legitimately observed top/bottom constraints in a
separate explicit structure, rather than infer order from an original list or
discard known constraints during bag pooling. Current remaining rows do not
implement that belief structure; hidden draw order is never an input.

Share a typed card-capability encoder across deck, visible state and candidate
actions. Encode operation kinds, ordered child edges, conditions, numeric
expressions, target predicates, timing, costs, continuations and granted-host
relations. Preserve lexical bindings and source/target roles. An unordered
effect-count bag would erase the semantics Eric identified. Card identity can
remain a separate residual for uniqueness, title references and unresolved
card-specific rules; it must not be the only semantic input.

Keep the existing state/deck/action projections and small transformer. Replace
or augment the pooled identity contribution with capability embeddings; keep
the two dedicated context roles and independent live-card capacity. This is a
proposed input/transition extension, not a reason to replace the entire model.

Original deck is fixed provenance and a set of potential capabilities. A card
in it might become drawable/playable later; that does not mean its abilities are
currently legal. Candidate actions bind the engine's actual offered instance,
ability/continuation, targets and arguments against contextual state. The
engine remains the authority for legal actions and payment/selection timing.

Remaining deck is an **action-updated belief over world state**, jointly related
to hand, board, resources, discard, captured/removed cards and ownership. Its
encoder reads known counts plus unknown mass/status, using the same capability
semantics. A supported observation ledger updates these zones after draws,
searches, discards, returns, creations and transfers. A control change is not
the creation of an owned copy. Unknown or unsupported movement invalidates the
affected belief rather than consulting simulator-private order. Clone the
ledger with each hypothetical branch and restore it with the root.

The action-conditioned predictor must predict the changed world representation,
including dynamic deck belief. The target encoder must read the corresponding
updated, actor-visible future observation/belief. Feeding original composition
unchanged into both sides is useful context but is not depletion learning.

## Targets and uncertainty

Known deterministic movements can use count-conservation and zone-delta targets
alongside future latent prediction. Compare against copying the current state
and against shuffled actions; include paired cases sharing original deck and
visible board/hand while differing in observed depletion. Weight/evaluate the
changing fields separately so a large static original-deck component cannot
make a copy shortcut appear successful.

For an unresolved draw, predict a distribution over observable outcomes or
condition a transition on a sampled outcome from the same information set.
When counts are known, the one-card marginal is `P(card j) = remaining[j]/N`;
multiple draws require sampling without replacement. After the actor observes
the draw, the target may encode that observed card and the updated counts.
The predictor must not be given its actual hidden position/order in advance.
Evaluate proper scores/calibration or conditional transitions, not whether a
deterministic point prediction guessed the unknown next card.

Distributional/conditional latent prediction and expected downstream value need
a separate bounded design: value of a mean latent need not equal expected
value across futures. A deterministic frozen-judge loss alone is insufficient.
Mask genuinely unknown labels; retain known zone counts and information status.
Kessel's draw handler (`generic_runtime.rs:2350`) also distinguishes an event
resolving from cards moved: an empty-deck draw can resolve with fatigue. Thus
`ifYouDo` cannot be reduced to `drawn > 0`.

## Smallest useful semantic test, before expansion

Start with a tiny prospectively fixed set of admitted deterministic effects and
one known-count stochastic draw boundary, not full games or broad training:

1. Hold out complete card identities while using familiar typed effect
   compositions. Predict one-step and short multi-step zone/stat changes and
   target feasibility from the same board/hand and offered action bindings.
   A second, separately reported stratum can compose familiar Draw/Discard
   primitives in an unseen sequence. Compare Draw-then-Discard with the reverse
   from empty/nonempty hands; do not conflate identity holdout with composition
   holdout. Use only cases admitted by the chosen executor or explicitly label
   a restricted synthetic oracle; arbitrary compositions are not automatically
   supported by Kessel.
2. Keep familiar identities/printed stats fixed while changing exactly one IR
   effect quantity, resource cost, target predicate, continuation condition or
   sequence edge. This synthetic definition mutation must change the semantic
   input and corresponding expected consequence; an ID-only path is a control.
   Changed definitions are fixture interventions, never altered rated cards.
3. Include matched no-context, wrong-own-deck and wrong-IR controls with the same
   architecture, parameter budget, candidate banks and compute. A wrong deck
   for decision-quality tests should remain consistent with known visible
   copies; avoid trivial impossible-hand detection.
4. Hold out by card definition/program and deck composition as applicable,
   retaining the same control intervention across paired seeds/seats. Measure
   input/latent informativeness, action-conditioned transition quality and
   equal-budget held-out decision quality separately.

The present bounded probes measure original composition, curve and initial
declaration probabilities only; their train/test sets share printed identities.
They do not establish held-out-card or effect-composition generalization.
The paired remaining-deck fixture deliberately exposes the current unknown-row
limitation. A null downstream control result may reflect weak fixture
sensitivity or an unused representation; it is not alone an encoder-failure
diagnosis. Variance/rank/collapse checks are smoke tests, not success criteria.

[I-JEPA](https://arxiv.org/abs/2301.08243) motivates predictive semantic
representations and informative context/targets;
[V-JEPA 2](https://arxiv.org/abs/2506.09985) motivates evaluating action-conditioned
latent prediction and planning separately from representation pretraining.
Neither paper validates this card-specific schema, belief update, or proposed
architecture. Those remain hypotheses requiring the controlled tests above.

## Later auxiliary coherence and separate strength targets

After the dynamic capability contract is admitted, a small frozen probe can
compare held-out real SWUDB deck lists with legal, leader/aspect/curve-matched
constructed negatives and graded card swaps. Split near-duplicate families and
archetypes together before fitting; remove titles, authors, URLs, source labels,
rank/popularity fields and other dataset provenance from encoder inputs.
Report how separability changes with swaps, without assuming every swap makes
a deck worse. Real versus random is a noisy coherence proxy: a random deck can
be strong and a real deck weak. It is neither a hard legality rule nor a
playing-strength label.

The separate source audit must establish what any SWUDB ranking measures before
it is used. Popularity must not become a win-rate target. Strength requires
actual performance labels and matchup/metagame, format, date and policy context,
with deck/archetype-grouped holdouts and uncertainty. Keep coherence and strength
heads/evaluations distinct so source classification cannot masquerade as win
prediction. No SWUDB collection, scraping, rank ingestion or training is part of
this increment or its current fit allocation.
