# Small typed capability/action experiment

The prototype encodes selected Kessel ability programs as typed structure, binds
them to explicitly reviewed action fixtures, and checks costs, conditions,
targets and ordered effects. It performs no optimizer update and adds no model
architecture or text encoder. The shared features are sparse counts of typed
path tokens; they are structural wiring, not evidence of learned game meaning.

The native two-card experiment passed **eight actual Kessel transitions** and
two bindings of captured offered actions to their reviewed programs. The
restricted oracle agrees with the observed resource/damage/exhaustion
projection for both. Checks cover target predicates/domains, payment timing,
cancellation and subsequent inability to reuse the exhausted source. This is
wiring plus narrow independent execution evidence; persistent/granted behavior
and held-out-card behavioral-distance quality remain unsupported. The two
earlier setup/guard failures remain preserved.

## Source and compatibility

Kessel is pinned to `c7ee39554901278cee70f61fd8b26fb1920696b3` in
`/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source`.
`compiler/generated/cards.json` SHA256 is
`0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`.
Tests compare the four embedded selected-ability excerpts with that catalog.

| Selected `abilities.leader[0]` | Restricted adapter | Whole-card pinned runtime | Native execution here |
| --- | --- | --- | --- |
| ASH_011: exhaust; unit remaining HP ≥2; damage1 | Known | Admitted, runtime-admission.json:26 | Passed4 applies; actual action bound |
| IBH_053: pay1 and exhaust; either base; damage1 | Known | Admitted, :1546 | Passed4 applies; actual action bound |
| IBH_001: pay1 and exhaust; own unit; heal1 | Known selected ability | Rejected, :7137: unit-side `numCardsFunc` | Excluded |
| SHD_002: exhaust and pay1; own unit; damage2 then Shield1 | Known selected ability | Rejected, :10002: unit-side `systemPropertiesFactory` | Excluded |

Selected-ability support does not admit a partial card. The native project kept
both sides of each selected admitted leader. ASH_011 is an off-format semantic
fixture; this makes no current format legality or competitive-strength claim.
Exact card source paths and source hashes appear in `typed-ir-verification.json`.

The schema comes from `crates/kessel/src/ability_ir.rs`: typed `Expr` (:45),
`Target` (:554), `TargetResolver` (:736), `Cost` (:833), `Effect` (:890),
`Ability` (:1142), and `Program` (:1442). The adapter intentionally admits a much
smaller subset: action abilities; exhaust/resource literal costs; typed boolean
conditions and limited integer predicates; explicit owner/type/zone selectors;
chosen-target literal damage/heal/one Shield; ordered sequences of at most four
effects. Unknown fields, hooks, arbitrary queries, attached or granted programs,
ambiguous bindings and unsupported operations return unknown. They are not
silently dropped. Optional/confirmation syntax can be represented structurally,
but the restricted transition oracle rejects those execution paths.

## Template versus instantiated action

A capability contains typed nodes and edges for a program with a chosen-target
parameter. An instantiated action additionally binds source, controller,
chooser, payer, chosen target and recipient roles. Physical card instance IDs
are alpha-renamed out of the features. Card IDs, titles, labels, source paths
and source hashes remain provenance. Neither raw JSON text nor printed card text
is embedded. Object keys are sorted; list indices, expression left/right edges,
cost multiplicity and effect sequence positions remain explicit.

Kessel's `Action` is the offered tuple `(kind, card, arg, method, label)`
(`model.rs:903–937`). That tuple is an exact binding witness here, not a semantic
feature. A method string or label is not a universal program reference:
`generic_runtime.rs:1782` indexes **available programs** at an ability menu;
`simulator.rs:673–681` can skip a menu; leader deployment can offset menus
(:752–760). Target clicks are offered by `generic_runtime.rs:1809–1831`.
The adapter therefore requires a unique curated source/card/side/index/stage
binding. Missing or duplicate witnesses remain unknown. The four ordinary
adapter fixtures are explicitly synthetic offered-action shapes, not recordings
of engine-offered tuples. Separately, `native_binding_report` binds each actual
recorded target click after checking its offered tuple, source instance/card,
`AbilityTarget` stage and opaque positive runtime program handle. The manifest
and complete catalog each witness exactly one leader ability at `leader[0]`;
the numeric runtime program handle is not decoded into a catalog index.

## Adapter contract for downstream inspection

`encoding_record` returns schema **`jepa-typed-ir-wiring/1`**:

| Field | Contract |
| --- | --- |
| `status`, `known` | `known`/`unknown` and an explicit boolean; unknown is distinct from an empty valid program |
| `coverage_status` | `selected-ability` when known, otherwise `unknown`; never a whole-card admission flag |
| `semantic_tokens` | Variable-length records `{path:[string or integer], value_type:string, value:scalar}` |
| `role_tokens` | Same record shape; source form, controller/chooser/payer, chosen owner/type/zone, recipient and source-equals-chosen relation |
| `program` | Normalized restricted typed ability, or null when unknown |
| `provenance`, `reason` | IDs/path/hash/exact binding evidence and rejection explanation; excluded from semantic features |
| `numeric_feature_width` | null: sparse typed tokens, no fixed dense width or trained projection yet |
| `production_graph_integration` | false: no current NumPy/Torch/native/WASM graph or ABI consumes this prototype |

Program scalar token types are `node`, `length`, `boolean`, `integer`, `enum`.
Role token tags are `form`, `role`, `owner`, `type`, `zone` and
`source_equals_chosen`. Source form is `leader` in reviewed action fixtures;
controller, chooser and payer are `ownPlayer`; chosen owner is self/opponent,
type unit/base, zone arena/base; recipient is chosen. The action adapter maps
only explicit source/card/leader[0]/`abilityTarget` witnesses to that template.
Binding IDs and the offered `(kind,card,arg,method,label)` tuple do not enter
the features. Unknown operations/fields, invalid types/domains and nonunique
bindings return unknown with empty token lists; there is no fallback to ID or
text features. Object-key permutations preserve tokens. Ordered array indices,
conditions, left/right operands, target roles and copy/amount multiplicity are
preserved. This is an inspection schema, **not a production tensor ABI**; it
does not alter the width-64 transformer,96-dimensional latent or2×207 deck inputs.
Known serialization is bounded at512 semantic tokens and32 role tokens;
over-budget programs become unknown without truncation. Expression/effect
nesting is at most8, each effect sequence and cost list at most4, and integer
literals0–65535. Ordered sequence/cost indices0–3 remain path components.
Whole-card runtime admission is separate provenance, including explicit false
for the two rejected whole cards. The production `ownDeck` marker and[2,207]
shape remain unchanged.

## Checks and the small alignment objective

Tests cover 200 recursive object-key permutations, held-out identity/name/path
substitution with unchanged programs, familiar identity with altered programs,
instance renaming, and role/zone/source failures. Cost, condition, target,
effect-amount and sequence hard negatives all parse as **known** in the
restricted schema. Distinguishing them does not depend on an unknown flag.
Their mutated full cards are not claimed to be runtime-admitted.

For a future small trainable typed encoder, the concrete matching objective is
`-log(exp(sim(q(action,context), k(program))/τ) /
Σ[j with compatible roles] exp(sim(q(action,context), k(program_j))/τ))`.
The compatible-role mask checks controller/target roles; cost/condition/effect
negatives stay in the denominator when their roles are compatible. Ambiguous
bindings are excluded as unknown, never relabeled as negatives. A separate
grounding loss must predict independent observed costs, target legality, state
deltas and subsequent affordances from actual transitions. No such optimizer or
world model runs here.

The frozen diagnostic uses deterministic token-count cosine and the same
role mask. The action receives its reviewed program through the curated
binding, so positive overlap and retrieval are partly true **by construction**.
The reported InfoNCE number measures structural consistency only. It cannot
establish learned alignment, generalization to unseen mechanics, or strategic
preservation. No raw-JSON/text comparison or paid initialization is involved.

The separate restricted synthetic oracle checks nonlethal scalar damage/heal,
one Shield, payment, exhaustion and follow-up affordability. Reversing
damage-then-Shield changes its result. This is a synthetic order-sensitivity
test, not Kessel equivalence. Deaths, triggers, replacement ordering beyond that
single Shield, persistent registrations, granted abilities, hidden state and
draw order are unsupported.

## Native attempt and limits

The isolated scratch project is
`/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe`.
Its final `source-manifest.json` pins 97 Kessel input files and four project files,
SHA256 `b65dbfc98be39627794d3e72f879c923afd59290fcf8d03cd57891b1e6ae9c06`.
The predeclared plan used ASH_019 bases and LOF_256 vanilla units, with no hidden
cards. It allowed eight planned `Engine::apply` calls (maximum12): source click,
cancel branch, chosen target, and an offered pass per focal card. Legal-set
queries covered HP1/2, unit/base, exhausted source and resource0/1. Expected
cost deferral, cancellation rollback, damage1, payment and inability to reuse
were written before execution.

Build command under the supervisor was `cargo build --offline --locked
--manifest-path …/typed-ir-microprobe/Cargo.toml --bin typed-ir-microprobe -j 1`,
with `CARGO_BUILD_JOBS=1` and task-7-local `CARGO_TARGET_DIR`. The native command
was `…/target/debug/typed-ir-microprobe …/native-receipt.json`.

The first guard stopped on a compiler-child exit race after2.5872s, with zero
native applies. Its exact supervisor and source bytes are preserved in
`attempt-1-evidence/`. One authorized continuation skipped only the observed
nonleader ESRCH disappearance and retained the original cumulative clock and
2GiB sampled RSS threshold. Offline compilation passed in17.05s, then catalog
loading required the canonical native Shield row, before any applies. Exact
attempt2 inputs/logs are preserved in `attempt-2-evidence/`. A final authorized
setup correction retained the **unmodified** `TOKEN_SHIELD` row, including its
reviewed unsupported status; no Experience token was required. It reused the
offline cache and original clock. Attempt3 completed eight applies, all
predeclared assertions, and both actual-action binding/scalar-projection checks.
Cumulative guarded time was22.6044s and sampled peak concurrent supervisor/
process-group RSS was880,164,864 bytes. This is a sampled stop guard, not an
instantaneous OS memory reservation. `attempt-3/` holds guard/transition logs;
`native-receipt.json` is the successful raw receipt. No rules were weakened,
token invented, old checkout edited, game/opponent run, optimizer updated or
cloud service used. Cumulative Modal spend remains$0.

`native_microprobe/` contains byte-identical copies of all four final manifest
project files, the manifest and executed supervisor. Their hashes were checked
against the manifest and successful supervision receipt. Targets, logs and raw
receipts remain outside Git in the scratch project. Its `Cargo.toml` captures a
local pinned-source path for reproduction, not a portable dependency resolver;
the copied README/manifest preserve their prelaunch wording as historical input
bytes. The verification JSON links the successful raw receipt and both failures
with exact hashes. No native execution is needed to read the evidence.

## Behavioral distance: independent labels still needed

A useful context-conditioned behavioral signature `b(card, context)` should
come from **engine observations**, independently of the feature vector:

1. Source-use and explicit predicate/target-admissibility masks over the same
   public reference roles and HP/resource/exhaustion boundary contexts.
2. Paid resources/exhaustion and observed target/player/zone state deltas.
3. Subsequent legal-use/target masks after the transition and, for stochastic
   admitted effects, an observable transition distribution rather than a
   sampled hidden next-card identity.

Define a distance using predeclared weighted Hamming distances for masks and
scaled L1/total-variation distances for observed deltas/distributions. Record
unavailable measurements as unknown; do not turn unknown into zero. A source
button can be present while a later target predicate has no admissible target,
so source-use and target masks must remain separate. This distance must never
be calculated from typed-token overlap or model embeddings.

On held-out **card identities**, compare that independent distance with cosine
and Euclidean embedding distance using Spearman rank correlation and nearest
behavioral-neighbor retrieval. The minimal prospective bank needs both similar
printed stats/names with different mechanics and distinct IDs with equivalent
mechanics, plus matched cost/condition/target/effect counterfactuals. A
composition holdout or renamed identical fixture is insufficient. The two
selected cards share damage1 but differ in costs and target domains; they do
not supply that bank. The observed target masks, costs and follow-up affordances
are recorded independently in `native.binding_checks`. ASH_011 admits the
opposing HP2 unit but neither base nor the HP1 unit; IBH_053 admits both bases
and neither unit. Both deal1 and exhaust; only IBH_053 spends1 resource. These
are two grounded behavioral signatures, not a calibrated global distance.
Held-out-card rank correlation and retrieval remain **null**, not success
claims. No broader case bank or fit was launched.

A static card vector supports only a global distance averaged over a fixed,
declared context distribution. It cannot change its distance when the board
changes. Context-dependent behavioral distance needs an explicit conditional
query (card, public context, role binding); that distinction must be evaluated
before proposing another architecture.

Deck composition remains a multiset with preserved copy counts, as checked by
`test_permutation_contract.py`. Its card-entry order is discarded. That
invariance does not erase ordered effect programs, conditions, targets,
continuations or legitimate future top/bottom operations. No current deck
model, graph or checkpoint was changed by this experiment.
