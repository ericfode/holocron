# Recovery, deck encoding and ability diagnosis

Saved research is recoverable at
`c39e1534664d6c055c844722f7251ee6cdf6c3ac`. Task5 subsequently saved the separate
file-only loss audit at `0c6b5cc5a88cd6d8ea47ec885cb495dcb690dee5`; its tracked
tree is clean, with four original untracked reports preserved. All six research
commit IDs and report/checkpoint locations are in [PROVENANCE.md](PROVENANCE.md).
The 274-file recovery archive (36,706,364 bytes) and all 45 loss-export checksums
were checked again without mismatches. This does not claim repair of the chat
service or recovery of its complete transcript.

The frozen competitive actor already receives numeric deck/discard/hand sizes,
visible hand/board identities and stats, hand cost summaries and action features.
It lacks the original main-deck multiset, remaining identity counts, whole-deck
curve and explicit effect/synergy programs. The exact baseline source is
`f9cbbd427689081d5f12829b1fe7edd76ca51fab`; [AUDIT.md](AUDIT.md) distinguishes
these existing signals from the missing features.

The small opt-in original-deck extension is two 64-coordinate context tokens:
a count-weighted shared identity bag plus printed curve/type/keyword/aspect/
trait summaries and knownness, projected 66→64 with role embeddings (4,416
additional parameters). Its ordinary remaining row stays unknown. A separate
provenance-ledger API exists but is not wired to ordinary observations; see
[REMAINING_LEDGER.md](REMAINING_LEDGER.md). Neither extension grants hidden draw
order or opponent private information, and neither qualifies playing strength.

For action-quality evaluation, retain matched neutral/correct-original/wrong-own
arms with identical dimensions, initial tensors, labels, update/order, search
budgets and paired seeds. Group game/deck-composition holdouts; keep the seven
already inspected losses as discovery. Admit a remaining-bag arm only after
actor-visible event provenance and branch/reset/conservation tests establish
its knowledge. Curve readouts alone cannot establish useful action choices.

The new [discovery analysis](ABILITY_DIAGNOSTIC_DISCOVERY.md) and
[33-forward probes](ABILITY_DIAGNOSTIC_RESULTS.md) explain the wrong-ability
gain: the learned model is sensitive to whole abilities, but its owner, threshold
and amount edits have tiny or misdirected effects. Public features and declared
intent can dominate eligibility. The transparent reference matches the twenty
primary anchored coordinates but wrongly rejects sixteen native healthy-heal
offers; its predictions never replace native labels.

The one tested correction excludes intent from eligibility while retaining it
for actual outcomes, using the same weights and no additional parameters.
[Fresh-state results](ABILITY_CORRECTION_RESULTS.md) show exact intent invariance
and fifteen unchanged heads, but worse eligibility error in two seeds. The
accuracy gate fails. These are four new states of an exposed program, not fresh
program transfer; the experiment does not test retraining the corrected graph.
Production and the earlier negative results remain unchanged.

Source freezes: diagnosis `66c3780e3452d62078c4e4cb19f952719ba94204`, fresh-state
test `48215e6717b1cc4f6f271786ae2e70b7a191a5da`, independent verification
`0e8fa42c04f22e09b9073bfb1767d8aa7f9ef8d3`.

Independent saved-output verification passed 600 checks with zero mismatches,
without another model, engine, fitting or optimizer call. The two experiments
used 39 forwards, 20 successful native applications, zero training updates and
zero paid jobs. All prior failed charges remain linked. Final carry is
**295 charged applications / 222.92651104100514 charged seconds**, with historical
aggregate observed native calls still unknown. The saved $100 ceiling/$25
reserve persist; this is not an account-wide billing assertion.

The verification result is
`5edc38d91be44124d99cac2d4cc710342f720d11f03346b02ab56a338c5ef8e1`;
final closure is
`44bec23f02d7c78373ddf05e1c1f7de291f8d8e3d91064e52bad42e76496bd50`.
Both live under `experiments/ability-correction-verification-v1/` in task7.
The portable evidence packet links the unchanged earlier packet and preserves
native captures, predictions, masks, checkpoints' hashes, ledgers and failures.

[Packet manifest](ability-diagnostic-evidence/manifest.json):
`71d5cf27174649ad2cfbcf308791fb2f83b47eb67a86f3dffe74018b073206eb`.
Its 87 entries contain 17,639,633 decoded bytes / 1,178,503 stored bytes. The
bounded byte verifier passed; 94 focused synthetic software tests passed.
These are engineering checks, not additional semantic examples.

```sh
python3 bots/jepa/own_deck/ability_diagnostic_package.py --verify --out bots/jepa/own_deck/ability-diagnostic-evidence
```
