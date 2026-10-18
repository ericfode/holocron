# Recover the completed native journal without another engine call

The source-frozen assay at `2d037a4` reached all 128 case-completion records and
256 paired native applications. Its 30-second native stage was terminated while
writing the final pretty JSON receipt. That receipt is truncated. The native
stage is failed, with its entire 512-application reservation charged; it is
never reopened, retried, declared successful or credited back. The sampled
owned-tree peak was about 501 MiB, below the 1 GiB limit. This was an output
finalization timeout, not a learned-model result. No training had started.

A separate, source-frozen saved-data recovery allocation may use only the
immutable plan, built-binary/source pins, failed-stage receipt and append-only
native journal. Recover each case exactly from its durable `contextComplete`
record, and independently require all 256 before/action/after boundaries and all
128 ordered roots. Preserve the partial receipt as failed evidence; never repair
or overwrite it. Recovered metadata explicitly identifies its derivation.

The individual fixture-validation snapshots did not reach durable storage.
Do not invent them. The unchanged collector's reviewed control flow completes
all 128 snapshot/load and legal-action checks, and admits all definitions,
before creating the journal header or applying an action. The built binary and
source pins support that control-flow inference. It is reported as inference,
separately from directly journaled native actions and outcomes. Any absent,
inconsistent or unpaired native outcome blocks recovery.

The recovered plan, examples, split, reference admission, model source, training
schedule, loss and all falsification gates remain exactly the original assay.
The versioned verifier reuses the frozen independent native-label, input,
reference, prediction, metric and gate helpers. Its only orchestration changes
admit the explicit source/control-flow fixture proof and the new saved-only
ledger. No scientific result selected those changes; no neural call has yet run.

The new ledger reserves recovery 10 s, preparation 5 s, fitting 120 s and
verification 10 s: 145 s, one worker, sampled RSS at most 1 GiB, zero native
applications and zero paid jobs/spend. It retains the original 3,624 forwards,
3,600 backward/optimizer calls and two TRAIN preprocessing fits. The preceding
failed attempt charged 31.28667466691695 s, so the combined maximum is
176.28667466691695 s, within the original 185-second allocation. The combined
native charge remains 512, with no further native reservation. Earlier carry is
807 charged applications / 254.2131857079221 seconds; historical aggregate
observed calls stay unknown. The saved $100 ceiling and $25 reserve persist.

If this saved-only recovery fails admission or verification, stop without
another engine invocation or result-driven architecture/objective revision.
All earlier failed charges and evidence remain linked and unchanged.
