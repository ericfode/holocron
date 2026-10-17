# Bounded local representation experiment

The later instruction to start visible experiments authorizes a smaller local
pilot than [the prospective gameplay fit](COMPUTE_PROPOSAL.md). This pilot uses
three matched arms, one seed, and at most 100 updates per arm (300 total).
It trains the 4,416 supplemental context parameters and an auxiliary linear
readout while freezing the competitive base. Its targets describe the original
declared deck: counts, printed curve and initial unit probability. It does not
train action transitions, remaining-deck belief, effect programs or playing
strength. No gameplay data, downloaded opponents or paid compute is required.

Existing credited deck lists are grouped by shared leader, shared base,
canonical composition and near-clone overlap before a deterministic holdout.
The input is an original-deck declaration with a fixed empty live state, not
a reconstructed game. Source popularity is not a strength label. Targets that
are constant in this small bank must be identified in the report.

Every arm has the same expanded model, initialization, targets, optimizer,
batches and update ceiling. The neutral arm receives role labels without deck
content; the wrong-deck arm receives another original composition from the
same partition. Such swaps are corrupted-input controls, not legal game states.
Final-step checkpoints are used; validation is diagnostic, not a selection
search. Small grouped holdouts and a single seed cannot establish generalization
or useful action quality.

## Dashboard reader contract

The shared append-only feed is outside the repository:

```text
/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/run-events.jsonl
/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/SCHEMA.json
```

The schema is [`jepa-run-event/v1`](run-events.schema.json). Each complete line
repeats its run ID, source commit, config and hash, dataset/split provenance,
timestamps, phase, step and limitations. `metrics` values are finite numbers.
Campaign and arm run IDs are separate; `parent_run_id` links children. Events
are real status/measurement reports. A heartbeat is liveness, not an update.
Readers should ignore malformed lines and an incomplete final line, de-duplicate
by `event_id`, and use the latest timestamp to detect stale workers. Sequence
numbers are increasing per run ID. A restarted writer resumes that sequence.
There must be only one active writer for a given run ID; different run IDs can
append concurrently under a file lock. Checkpoint/manifest paths and hashes are
artifact events. Dataset preparation is labeled `preparing`; only optimizer
updates are labeled training steps. Failures and exhausted limits remain in
the journal. No reset or rewrite erases a consumed allocation.

The initial campaign is `campaign-original-20261017T234539Z`. Its first event
pins the implementation commit `eb86fe0c75867aa2dc8fae1cf4b341d488b8e87d`;
each fit must pin the later runner commit that actually executes. Fit output
and its manifest belong under the same external `experiments/` directory.
The dashboard is implemented by a separate worker and is not part of this
checkout's UI work.

## Limits and cloud access

One CPU worker, one Torch compute thread, batch at most 16, 120 seconds per
arm, 300 seconds total fit time, 2 GiB process-tree RSS, and 300 total optimizer
updates are ceilings, not promises of completion. A supervisor must first pass
harmless guard checks and record observed usage and termination reasons. A retry
does not replenish any budget. The run manifest must include exact dataset,
split, source, initialization and runtime hashes before launch.

Modal CLI 1.4.3 and the active `ericfode` workspace were verified with a harmless
read-only profile lookup. No credential values were displayed. Eric subsequently
authorized **US$100 cumulative for this entire batch**, not per run. The parent
owns the budget; this coordinator is the only worker allowed to allocate paid
jobs, and child workers may not independently spend it. Start with local learning
and metrics verification. Keep US$25 unallocated as a conservative margin until
current GPU/CPU/memory/storage/startup/egress charges are accounted for. Reserve
each proposed job's worst-case cost against the remaining ceiling before launch,
including earlier attempts and failed runs; never replenish the cap on retry.
Record committed, estimated and confirmed spend distinctly in the event feed.
No persistent volume, scheduled app or idle GPU is needed for this local pilot.
Paid work still requires a useful experiment, a current price estimate, fixed
runtime/concurrency and automatic shutdown. A spending cap alone is not a reason
to use a GPU for an experiment that runs efficiently on local CPU.
