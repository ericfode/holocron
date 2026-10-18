Each compilation, collection, and fit is coordinated by root. Saved attempt
receipts are the record of executed stages.

This collector reuses the two previously executed complete leader definitions
ASH_011 and IBH_053 at Kessel source
`c7ee39554901278cee70f61fd8b26fb1920696b3`. The whole ASH_019 base,
LOF_256 unit, and exact reviewed native TOKEN_SHIELD row are also retained.
No engine, compiler, card definition, coverage, or action binding is changed.

Sixteen synthetic public contexts (eight families shared across both cards)
produce native offered-action masks and actual resource, exhaustion, damage,
follow-up affordance, and terminal targets. Unperformed transitions have false
target masks. Every branch starts from its original state or untouched target
prompt. Cancellation and commitment are independent branches. Every actual
`Engine::apply` has a flushed and fsynced before/after journal; failed calls
still spend apply quota. No hidden cards, draw order, opponent, or full game is
constructed. These are supported Kessel transition labels, not Forceteki oracles.

The frozen families are:

| Family | Split | Public variation |
| --- | --- | --- |
| 0 | train | Ready source/resource; enemy units with 2/1 remaining HP |
| 1 | train | Same physical resource exhausted |
| 2 | train | Source exhausted |
| 3 | train | Chosen enemy unit has 1 remaining HP; other unit has 2 |
| 4 | train | Friendly unit target; own base damage29, chosen for IBH_053 |
| 5 | validation | Enemy base damage29, chosen for IBH_053 |
| 6 | validation | Exhausted resource plus invalid chosen unit boundary |
| 7 | validation | Exhausted source plus friendly-unit board variation |

Family4's friendly unit has damage0; family7's has damage1 and own base
damage2. Other default enemy units have damage2/3. Both leaders are undeployed
and controlled by P1, with exactly one physical resource. ASH_011 chooses the
first unit. IBH_053 chooses the enemy base except families3/6 (first unit) and
families4/7 (own base). All derivatives of each family remain on one split
across both card identities. There is no held-out-card generalization claim.

The shared supervisor ledger is append-only under an exclusive stage lock.
Collection/build and fit, including failures and retries, share120 active seconds,
96 engine applies,600 optimizer updates, one active owned process group, and a
2GiB sampled RSS stop threshold. This collector reserves at most64 applies;
actual attempted calls are counted from durable before-apply records. An
unfinished prior stage fails closed. Failed or unaccountable fit stages debit
their entire update reservation. Sampling is not an instantaneous OS memory
reservation. Compilation reuses the existing external target cache and counts
toward the same120 seconds. Offline locked Cargo uses one build worker.

Read-only preflight (omit `--execute` until root GO after source commit):

```sh
python3 bots/jepa/own_deck/supported_native_collector/supervise.py --stage collect --ledger /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/supported-transition/campaign-ledger.jsonl --out /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/supported-transition/attempt-1
```

The exact execution command is that command plus `--execute`. The fit must use
the same supervisor with `--stage fit --progress DEDICATED_PROGRESS.jsonl
--max-updates 600 --command ...`. Progress rows carry nondecreasing integral
`updates_completed`; no other campaign's feed may be used for quota accounting.
Fit code must itself enforce its fixed update allocation. The parent owns its
source review and GO. No retry may switch ledger paths to restore quota.

The supervisor now checks that a direct Python main-script path exists before
creating a stage or reserving updates. Paths are resolved against the collector
working directory; use an absolute trainer path for fit commands.

A separate, explicit missing-main credit can correct a conservative update
reservation only when the latest finished failed fit never opened its Python
main file. Verification requires the exact receipt/stderr hashes, one fit phase
with exit2, the exact solitary CPython missing-file diagnostic, the derived main
path still absent, empty stdout, absent declared progress/output, and no events
for that run ID. Runtime errors, interrupted optimization, any progress/output,
altered evidence, later stages, and duplicate credits reject. The append-only
`missing-main-update-credit` event subtracts exactly the original reservation
from net update debit. It retains the raw failed stage and charge, all elapsed
time, engine applies, and hashes proving the exception. It cannot increase the
600-update allocation or credit any time. The next fit uses new paths and run ID.

Read-only proof verification for the recorded startup failure:

```sh
python3 bots/jepa/own_deck/supported_native_collector/supervise.py --ledger /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/supported-transition/campaign-ledger.jsonl --credit-missing-main /Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/supported-transition/fit-guard-1/supervisor-receipt.json --receipt-sha256 bf6a91e1709ead9a07afbb48889a9be31c1d3f44b9a8c60464413223e3c82d56 --stderr-sha256 8d807e88ac5751019b8f3829ba925ec419176f9ae8a7077980b6ce8b7c8aa65c
```

Only the coordinating root appends the checked credit by adding
`--execute-credit` after source review/commit. This command launches no worker.
