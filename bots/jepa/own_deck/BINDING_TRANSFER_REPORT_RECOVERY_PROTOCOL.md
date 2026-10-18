# Saved-output report recovery

The frozen learner completed all 5,400 optimizer updates and 5,436 neural
forwards, saving every initial/final prediction and checkpoint for six arms
and three seeds. It then failed to serialize a NumPy integer in the final
result report. Its canonical stage remains failed, charged the full 60 seconds,
with observed neural counters unknown. The durable journal and saved outputs
remain independent evidence of the completed execution prefix. No ledger,
receipt, checkpoint or prediction is rewritten, and no training is repeated.

The remaining authorized Phase B allowance is 13.9957191250287 seconds after
the failed five-second prep, successful 1.0042808749713004-second prep and
failed 60-second fit. This linked continuation allocates 13 seconds: saved
report recovery 3, fixed baselines 5, and independent verification 5. It permits
zero native applications, zero neural forwards, zero optimizer updates and
64 fixed numerical head-fit attempts. It carries 208 charged applications and
184.01759783166926 charged seconds; its cumulative time ceiling is
197.01759783166926 seconds. All failed charges and historical unknowns remain.

Recovery checks the exact failed-stage artifact inventory and durable journal,
then applies the frozen evaluation and contrast functions to the saved arrays.
It reconstructs tensor hashes and weight movement from saved initial/final
checkpoints. It never loads a model or performs a forward, backward, optimizer
step, new initialization or replay. Unrecoverable last-step gradient summaries are
reported as unavailable; they are never fabricated. Recomputed label hashes
are explicitly recovery-time checksums, not claimed as a lost original report.

The report writer converts NumPy scalar values to their equivalent JSON scalar
values. The baseline route uses the same serialization adapter so the same
reporting bug cannot consume that stage. No metric, feature, prediction, label,
mask, split, scale, solver, loss or decision criterion changes. The original
failed stage is the source of recovered predictions, not a successful run.

Independent verification retains all scientific checks, additionally checking
the failed origin, full durable prefix, immutable saved inputs and recovery
provenance. Both predeclared primary decisions and the stronger typed-transfer
criterion in `BINDING_TRANSFER_V2_PROTOCOL.md` remain unchanged. General
semantic validation remains false, and mixed or negative findings remain.

The $100 financial ceiling, $25 reserve and saved spend ledger are unchanged;
new paid allocation and spend remain $0. No games, deployments, native calls,
engine or card changes, hidden draw order or opponent private identities are
introduced. Original research workspaces remain read-only.
