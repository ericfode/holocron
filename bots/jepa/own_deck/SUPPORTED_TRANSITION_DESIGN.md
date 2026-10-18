# Supported transition pilot: independent design check

Read-only design review, **2026-10-18 UTC**. No collection, training, compilation, games, or paid actions were launched by this reviewer. Repository instructions: `AGENTS.md` and `CLAUDE.md`. This review owns only this document.

The available verified subset is enough for a bounded **held-out-context engineering pilot**: actual whole-card Kessel abilities `ASH_011` and `IBH_053`, with unmodified `ASH_019`, `LOF_256`, and the exact canonical Shield dependency. No eight-card admission minimum applies. The older `next-transition-experiment.json` eight-card/six-train/two-held-out gate is superseded by the current supported-subset instruction. **Held-out card IDs: none.** `IBH_001` and `SHD_002` have parsable selected abilities but fail whole-card runtime admission; they remain excluded. ASH_011 is a semantic microfixture, not a current Premier-eligible deck claim.

## Targets and split

The collector defines **16 public contexts**, eight per focal card, with at most **64 native applies** under the root's absolute 96-apply ceiling. Train families **0–4** cover baseline, zero ready resources, exhausted source, invalid chosen target, and a friendly target with own base at 29 damage. Validation families **5–7** cover enemy base at 29 damage, zero resources combined with an invalid chosen target, and exhausted source combined with a friendly board. The friendly/enemy base cases provide a native terminal-positive case on each side. The split applies **across both cards**. Every branch and stage derived from the same starting context belongs to the same family: source click, cancel, target commit, and optional offered opponent pass are never split independently. Exact repeated public scalar contexts after canonical instance renaming are rejected across the split, even across cards. Retain the split in a hashed manifest; do not repartition after seeing outcomes.

Primary targets must be projections of actual `Engine::legal_actions`, `Engine::apply`, and settled before/after public snapshots: separate source-use and candidate-target masks, paid resource/exhaustion costs, visible damage/zone changes, terminal status, and subsequent offered affordances. Prediction time must be explicit. Raw current resources, HP, ownership, exhaustion, and chosen roles are admissible inputs; the actual offered mask being predicted, paid cost, future snapshot, and terminal result cannot be supplied as input. Missing/dead targets and unavailable follow-up measurements need explicit known/missing masks rather than a zero invented as fact. Keep terminal cases; do not select only nonterminal successful transitions. Record rejected applies and stop causes; do not generate their outcome targets with `synthetic_transition` or token arithmetic.

The new `supported_native_collector/src/main.rs` was inspected: its guarded `Budget::apply` journals before/after/error evidence around the real engine call; `run_case` reads masks from actual offers, branches cancellation and commitment from the untouched prompt, measures costs/counters/terminal status from the settled native result, and queries follow-up after an offered pass. The cancellation branch checks snapshot and legal-action restoration. `supported_transition_data.py` builds 19 fixed coordinates exclusively from `before.state`, checks source/program provenance and observed native target projections, groups both cards by the declared family, and rejects identical encoded contexts across partitions. Its seven output columns predict one chosen-reference admissibility scalar; the complete candidate-target masks remain raw evidence, not model inputs or additional learned outputs. The earlier independent evidence follows the same separation in `native_microprobe/src/main.rs:99` and `typed_ir_alignment.py:503`–`:529`. A target is not independently grounded merely because a feature-derived oracle agrees with itself.

## Matched representation comparison

The proposed small width-16 encoder uses shared typed-key/ordered-index path encoding, typed leaf embeddings and scalar projection, a nonlinear node MLP **before** invariant count-weighted pooling, and a context projection/prediction head. The model owner selected an independent numerical pilot cap of eight program slots, 64 semantic plus 32 role slots per program, and 16 path components, rejecting overflow without truncation. These are not inferred from the adapter's separate 512-semantic/32-role inspection limits. All three arms must share those padded input shapes, graph, trainable parameter count (at most 32,768 each), seed 17 initialization, normalized targets, batches, update ceiling, optimizer, and final-step selection:

| Arm | Capability input | Context and native targets |
| --- | --- | --- |
| Correct IR | Reviewed typed program, with no source identity | Identical across arms |
| ID-only | Reserved opaque identity tokens; fixed neutral padding without AST length/path leakage | Identical across arms |
| Wrong IR | Predeclared wrong capability mapping, applied consistently to both program and pooled paths | Real bound roles and context unchanged |

Parameter receipts should include total and effective trainable counts and every tensor shape. Opaque ID controls belong only in their named arm. Source card code, title, source path/hash, fixture/family index, runtime program number, physical instance ID, and offered label remain provenance, never primary numeric features. A binding witness can resolve a program without becoming a feature. The current adapter does this in `typed_ir_alignment.py:265`–`:275` and `:290`–`:294`; its source-identity substitution and instance-renaming tests are at `test_typed_ir_alignment.py:36` and `:78`.

Object-key permutation must produce exactly the same model input and initialized prediction; preserve list indices, expression left/right roles, cost multiplicity, literal quantities, and effect sequence positions. The adapter sorts only object edges (`typed_ir_alignment.py:245`–`:262`), and tests distinguish sequence reversal (`test_typed_ir_alignment.py:57`). The trainable encoder needs its own corresponding assertions. In particular, summing independent path and value embeddings, or linearly projecting their concatenation before summing, can erase which value occupied which sequence position. Path and value must interact nonlinearly at each node before pooling. A learned difference under reversal is an encoding sensitivity check; the currently rejected Qi'ra whole card supplies no new native order-semantic label.

Native transition/affordance loss is primary. The inspected pilot trains this loss directly, without a program/action alignment auxiliary. Injecting the same curated program into both action and capability representations would make positive alignment partly true by construction; its loss/retrieval alone could not establish learned semantics. Report a no-fit copy-current/zero-delta baseline on exactly the same known future target coordinates, alongside the training-prior baseline. Per-column known support and target variation matter: settled damage and exhaustion remain nearly trivial, and follow-up reuse is always absent in successful exhausted-source cases. Aggregate error alone can hide these constants.

## Interpretation and bounds

With both focal IDs present during fitting, a fixed two-card wrong-IR swap is an invertible identity code. The model can learn the remapping. Equal correct/wrong performance does not refute reusable semantics, and success against ID-only on three held-out context families does not establish held-out-card generalization. There is only one global card pair, so card-distance rank correlation and held-out-ID neighbor retrieval are **unsupported**, not zero. Familiar-ID altered-program parser tests are structural diagnostics; without independently executed altered-card outcomes they are not behavioral training truth. No new coverage work is required for this pilot.

The root's shared ceilings are **96 applies including failures, 600 total optimizer updates** (at most 200 per arm), **120 active seconds across collection plus fit and all retries**, **2 GiB sampled concurrent process-tree RSS**, one worker and one compute thread. Consume the collector's elapsed/applies receipt in the trainer's remaining allocation; retries preserve attempts and subtract prior consumption. Count imports, validation, and auxiliary work inside the guarded active run. Final evaluation is fixed, with no hyperparameter/checkpoint search and at most six held-out model forwards total (initial/final per arm). Three additional label-free ABI golden forwards are declared separately and remain inside the same guarded time/memory allowance. Sampled RSS is a stop guard, not an instantaneous operating-system reservation; state this limitation in the receipt. Stop with partial evidence at a limit rather than extend silently.

Local CPU comes first. Cumulative external budget remains **US$100**, shared across the entire experiment batch with root as sole spending coordinator; current recorded batch spend is **US$0**. This review authorizes no paid job. It changes neither the production JEPA graph nor the native/WASM own-deck ABI. These two scalar abilities also do not exercise dynamic deck depletion, draw distributions, persistent granted abilities, or strategic strength; those conclusions remain outside this pilot.

## Source receipt and readiness

Reviewed base is Holocron commit `456f914fc2f8fc1f254b6baa8fec53f0e97a2b45`, pinned Kessel `c7ee39554901278cee70f61fd8b26fb1920696b3`, catalog SHA256 `0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812`. Reviewed adapter SHA256 `25a05e39e8e432e2003127747d2c311fe32d225528ac60db9afa05aee5b856c9`; adapter tests `18f47f6a6a50cca1fc308a51b3228cc61f6985fc8d88946db25ab0bc4dc92619`. These are source-review pins, not execution receipts.

Final source review includes `supported_native_collector/src/main.rs`, its durable campaign supervisor, `supported_transition_data.py`, and `train_structured_transition.py`. The model's nonlinear joint path/value map, fixed tensor shapes, five explicit status classes, source-free typed primary inputs, and matched graph/initialization/batches are present. Query indices only gather shared encoded programs; they do not enter a learned identity embedding in the primary arm. Both converter and trainer reject identical encoded public contexts across the split. Review caught an optimizer-progress key mismatch and 18 validation forwards instead of six; the saved source now uses one durable, fsynced `updates_completed` record per actual step and initial/final validation per arm. The supervisor requires the exact completed-step journal for successful debit and charges the entire update reservation for an interrupted/missing/incomplete journal.

The versioned numerical contract records all input tensor shapes/dtypes, ordered vocabularies and hash, PAD/UNKNOWN IDs, bounds, status/token masks, scalar units/scales, ordered context and target columns, target availability, source/dataset provenance, reference forward and weight orientation. Completion writes each arm's named weight shapes, checkpoint hash and five-status finite numerical goldens. Input count pooling remains a one-source synthetic capability bag, not a dynamic deck. The frozen source and saved focused preflight are suitable for the bounded context-only fit under parent coordination; this reviewer launched no fit and claims no learned result. The saved receipt reports **9/9 forward/contract tests passed**, zero optimizer updates, and successful validation of the actual 16-row data including recomputed float32 context-overlap rejection. Those receipts were inspected, not rerun here.

Collected evidence at Holocron commit `843b7a2d7d2d369b2b5301678403cdf18979ae1e` was read without rerunning it: attempt 1 preserves a compile failure with zero applies; attempt 2 records **32 applies**, **16 cases**, **10 train / 6 validation**. The campaign ledger debits **2.0025895409 guarded seconds** across both attempts, leaving the original allowance reduced rather than reset. Native labels vary in both partitions for source-use, chosen-target legality, resource cost and terminal status. Observed damage is always 1, exhaustion always 1, and follow-up reuse always 0. Known-label support is deliberately small:

| Target | Train | Validation |
| --- | ---: | ---: |
| Source use | 10 | 6 |
| Chosen target allowed | 7 | 3 |
| Resource cost | 5 | 2 |
| Damage delta | 5 | 2 |
| Source exhausted after | 5 | 2 |
| Follow-up source offered | 4 | 1 |
| Terminal | 5 | 2 |

Evidence and reviewed source pins:

| Item | SHA256 |
| --- | --- |
| External `supported-transition/supported-transitions.npz` | `fd40fe92108bf89c25299dda1a975a550209283908a54f9c745e0514e9e79865` |
| External `supported-transition/supported-transitions.manifest.json` | `821a96109d6dadc44dcda510c1293a5e8eab41ba55709f5516849ecf3280893e` |
| External `supported-transition/attempt-2/native-receipt.json` | `b208f5f6083bc4c19d4e15ed2d8e820e8e144fd14f633deea1d29d24cfc8061c` |
| `supported_native_collector/source-manifest.json` | `ada4704708f233866b8ce1a79fe919a33a798cd0fd21c0b9e552d76d4f210871` |
| `supported_native_collector/src/main.rs` | `be006279e51bb1ed45aa7ca84f67149da14ffd01605add28cb778878892ba346` |
| `supported_native_collector/supervise.py` | `99baae6ea11d0421332df16802c729dd2c6134103518317dfc7e504aabb1359e` |
| `supported_transition_data.py` | `7e7fccc2c058a7b4a888c6cc61dedb548044bb43e5354647f4a05475091553ac` |
| `train_structured_transition.py` | `0b0826951cd880e8920e496c54c9a27c7a69032e726ec52f5354cead3e56bece` |
| `test_train_structured_transition.py` | `340473c6c43e2e8d3e2fad6267c1fabf56fd8422ce649aee9c424cdfc9b90e85` |
| External `supported-transition/structured-preflight.json` | `9405173ebe97ded820f357bdc1106c3016ff3f40797ad298c6b34210c6415aea` |
| External `supported-transition/structured-contract-preflight.json` | `03bad3b85435afbd8efec68f9eab4890081604136cdb43f03f106c4640167f06` |

External paths above are beneath `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/`. The selected native catalog hash is `d2074dd51beaf0bef7a7d9d138ade22611bcbcdd84a6d79aa0b25b6493f9b7ad`; the frozen numerical vocabulary hash is `72bb6e274c117b8abadc38ef31430ea3ee27168376a48a6f31bb92e4947057d5`. The numerical contract requested by the read-only task-4 handoff (`/Users/ericfode/Documents/Codex/2026-10-17/task-4/representation-integration/README.md`) is recorded for this standalone pilot; no production integration readiness or parity is inferred.
