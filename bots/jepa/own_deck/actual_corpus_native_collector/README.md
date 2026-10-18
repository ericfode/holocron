# Actual-corpus native play bridge

Preparation only. Root must freeze/review source and explicitly authorize execution. This new executable uses the unchanged pinned Kessel public API. No engine, compiler, card, existing collector, checkpoint or coverage migration is edited.

The eight main-list sources are ASH_048, JTL_095, SEC_163, LOF_077, JTL_078, JTL_158, LOF_155 and JTL_217: 65 declared copies from the actual 27-list bank. Complete compiler rows, all ordered abilities, intrinsic keyword values, top-level conditions and exact dependency/token definitions remain intact. Runtime admission is distinct from game conformance; the admission report explicitly does not assess the latter.

Every source starts in the actor's own hand. The native protocol follows an actually offered play through payment, entry, optional trigger, predeclared target and settlement. Only that target may be committed; an unavailable intended target may use a native decline/cancel, never a substituted target. Unit-trigger decline retains the already played unit; event cancellation can leave the event in hand. Source cost/zone outcomes come from actual final snapshots, and selected-target futures stay unknown unless that target was committed and the native outcome settled. Errors, unsupported continuations and unavailable plays are retained.

Four fixed public state families per source produce 32 roots. Six source identities × three states train (18 roots); LOF_155/JTL_217 × seen states are program held (6); seen identities × state 3 are state held (6); the joint cell has only two roots. LOF_155 exists in inherited deck training lists; JTL_217 is inherited held-only. Exhaust is wholly held in one card, an explicit OOD stress rather than replicated unseen-effect evidence. No strategic/gameplay claim follows.

The candidate bank has eight fixed roles. Public source/candidate stats have type-specific known masks: events and upgrades do not acquire fictional unit HP/damage/exhaustion. Printed cost and unique are known only when numeric/boolean. Actual printed-cost-2/3 helpers TWI_253/TWI_111 share Vehicle/Fighter/space/HP4 but differ in power; no printed field is overridden. LOF_151 and ASH_066 attach to separate vanilla non-Vehicle Jedi Gungi hosts. Each attachment has an independent native public UpgradeTarget offered-host witness plus exact snapshot/load roundtrip.

JTL_158 is conditional **self damage 1**, regardless of its display title. JTL_217 checks another friendly space unit, excluding itself. The before-play features carry the public other-space/Fighter counts. ASH_048's native Shielded entry is observed; its Sentinel keyword is retained, while later attack-target behavior remains untested.

The collect-only supervisor uses the existing writable task-7 cache at `experiments/typed-ir-microprobe/target`. It runs offline/locked Cargo, one build worker and one codegen unit. Build plus every failed/completed collection attempt share 90 active seconds, 256 durable Engine::apply attempts, a sampled 1-GiB owned-process RSS threshold and zero model forwards/optimizer updates. Each root has an additional eight-apply cap. Memory accounting uses the maximum sampled sum of **currently live** owned processes plus the supervisor. Final rusage supplements it with supervisor peak plus maximum single-child peak. Historical per-PID peaks remain metadata and are never added across sequential compilers. RSS is sampled, not an instantaneous OS process-tree reservation. No unrelated process is inspected or signalled.

Guard version 1 stopped build attempt 1 before collection because it added historical peaks of sequential compilers. That failed receipt and ledger debit remain intact: 1.720206 active seconds and zero applies. Version 2 fixes accounting without raising the 1-GiB limit; a manually approved retry has at most 88.279794 seconds and 256 applies remaining. The old source manifest remains in `source-manifest-v1.json` and the source commit. Native Rust, card definitions, numerical contract and collection plan are unchanged.

The append-only shared allocation ledger is `experiments/actual-corpus/campaign-ledger.jsonl`. Stage start reserves quota; stage finish records phase `native`, elapsed seconds, native applies, neural forwards and optimizer updates, including failure debits. Interrupted/unfinished ledger state forbids resetting quota. Later card/deck stages require their separately frozen guards and root GO; this collector cannot launch them.

The default command is harmless source/hash/quota preflight:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/ericfode/src/crown-jepa/.venv/bin/python \
  bots/jepa/own_deck/actual_corpus_native_collector/supervise.py \
  --ledger /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/actual-corpus/campaign-ledger.jsonl \
  --out /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/actual-corpus/native-attempt-1
```

Do not append `--execute` before root GO. No unguarded Cargo/native commands are part of preparation. Conversion afterward uses `actual_corpus_native_plan.py --native-receipt ... --plan-file ...` and makes arrays only, with no model/native calls. Its per-card endpoint table must show actual successful funded plays for all eight before training admission; merely completing 32 records does not verify the cards.

Dense ABI: globals `[32,18]`, candidates `[32,8,34]`, source targets/masks `[32,9]`, branch targets/masks `[32,8,7]`, public `selected_candidate_indices[32]`. Target intent is fixed before play; observed offeredness and after states never enter features. Source post-play heads need intended target features because cancel/commit can change costs and entry. Arrays retain exact source/state partitions and support counts; no unknown label is converted to a negative.
