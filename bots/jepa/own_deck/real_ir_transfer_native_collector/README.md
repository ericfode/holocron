# Real IR transfer native collector

New source-only collector for seven complete real event rows from the pinned
Kessel snapshot at `c7ee39554901278cee70f61fd8b26fb1920696b3`. It changes no
Kessel source, compiler output, original card row, or previous collector.

The coordinator supplies schema `jepa-real-ir-transfer-plan/1`, `synthetic:false`,
seven programs and 56 worlds (eight intents each), with maximum 168 native calls
and at most three per root. Expected ordinary play/target-or-Cancel is 112 calls;
the maximum is a ceiling, not an observation. No build or call is authorized by
importing this source.

The six candidate roles are `p1_ground,p2_ground,p1_space,p2_space,own_base,opponent_base`.
`source` is captured separately. Every original selected row is compared against
the assembled pinned catalogue; the source shard may omit only the diagnostics
merged by `catalogue_io`. `TOKEN_SHIELD` is required by the native constructor
even though these fixtures contain no physical Shield. Missing aliases remain
missing. Helpers must be plain nonunique units at their natural printed HP,
power and arena. Both owners have the same ground/space definitions. Worlds use
HMW_093 ground (8 HP), LOF_119 space (10 HP); public damage is 3/5 respectively,
with a healthy intended ground/base variant. No private opponent hand, resource
identity, deck identity, or draw order is admitted.

All 56 fixtures undergo construction, whole-row admission, snapshot/load and
legal-action roundtrips before the first application. Native target membership
comes from the actual target prompt. Only an offered intended action or an
actually offered Cancel is applied. Unoffered prompts without Cancel remain
explicit prompt-only observations with no inferred future. Settled endpoints
include continuation/death/event/support witnesses; departed numeric counters
remain unknown to the downstream converter. Base cost is `null`/unknown.

The binary takes `PLAN NEW_RECEIPT NEW_JOURNAL`. Receipt JSON streams compactly
to the exclusive file; stdout contains only a short counter summary. Every
before/after/context-complete journal entry is flushed and fsynced.

`supervise.worker(args, run, receipt)` is called only after the coordinator's
durable sealed stage begins and creates an empty output directory. Required args
are `stage` (`build` or `native`), `root`, `plan`, and `out`. It inherits the frozen
process-group/RSS cleanup helpers, Cargo offline/locked/jobs=1, a unique copied
campaign binary, and the coordinator's remaining wall budget. It initializes no
ledger and performs no retry. The coordinator owns begin/finish and source pins.

Primitive tests use only synthetic dictionary journals and command strings.
They instantiate no engine or model and parse no actual receipt.
