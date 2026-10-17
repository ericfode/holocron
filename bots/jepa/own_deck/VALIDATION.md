# Bounded implementation verification

The original-deck context reaches action prediction and simulated-leaf value
scoring through the Python actor and the Rust/WASM controller. Both dedicated
rows have independent capacity alongside all 24 existing live-card slots.
The second row is always explicitly unknown; no remaining-card ledger or
trained deck-aware candidate is supplied by this increment. This is a draft
original-context milestone, not the completed dynamic capability world model
described in [the proposed next design](CAPABILITY_WORLD_MODEL.md).

| Check | Result |
| --- | --- |
| Integrated Python contract/model/actor/data/probe/boundary checks | 32 tests passed, no skips; PyTorch 2.8.0, CPU |
| Rust controller and existing scripted semantics | 17 tests passed |
| Cross-language encoder | 22 cases / 9,108 float32 coordinates bit-identical |
| Own-deck graph, each native and WASM backend | 378 tensor combinations and 9 ordinary hello/decide exchanges passed |
| Maximum own-deck action-logit error | 4.5299530029296875e-6, tolerance 1e-5 |
| Legacy graph regression, each backend | 126 tensor combinations, 7 decisions, 6 scripted planner cases passed |
| Maximum legacy action-logit error | 3.1174978076808912e-6, tolerance 1e-5 |
| Rust formatting and Git whitespace checks | Passed |
| Frozen original-composition probes | 128 synthetic compositions, 96/32 disjoint composition split; raw and latent probes versus neutral/wrong-deck/label controls |
| Same-board/hand remaining-deck counterexample | Expected gap: forecasts stay identical although fixture draw probabilities differ (0 versus 3/42); remaining row stays unknown |
| Same-ID altered effect-definition counterexample | Expected gap: current printed-metadata encoder ignores effect-program changes |

The integrated checks cover gradients and a synthetic supplemental-only SGD
update, full and supplemental checkpoint round-trips, base-weight immutability,
known/unknown/neutral states, canonical counts/reprints, malformed inputs,
opponent-seat isolation, reset, cached predictions, simulated-leaf propagation,
and trajectory-to-pack retention independent of `--tmax`. The bounded tensor
fixtures cover both checkpoint roles and all nine horizons. Ordinary protocol
checks use a fixed high gate, c-clock resourcing and no simulator calls.

The 4,416 new parameters and their checked-in initialization are engineering
fixtures. These results establish numerical and information-boundary wiring,
not playing strength. Synthetic optimizer checks do not consume real-data
training examples. No full games, downloaded opponents, live submissions or
deployments were run. Engine-dependent full-game checks were outside this
focused verification.

## Receipts and reproduction

- [Integrated Python receipt](integration-verification.json) pins the core
  Python implementation sources and the test/probe sources, recording 32
  passing checks.
- [Training receipt](training-verification.json) records the synthetic update,
  source/fixture hashes and unchanged baseline/supplemental files.
- [Own-deck runtime receipt](../wasm/tests/evidence/own-deck-runtime-parity.json)
  binds both artifacts, final sources and the compact numerical reference.
- [Legacy regression receipt](../wasm/tests/evidence/own-deck-baseline-regression.json)
  binds rebuilt legacy-graph artifacts and the unchanged baseline reference.
- [Exporter instructions](../wasm/export/README.md) include the exact local
  offline PyTorch invocation and generated-kernel reproduction recipe.
- [Runtime instructions](../wasm/tests/README.md) include native/WASM builds
  and the bounded parity checker commands.
- [Probe evidence](PROBES.md) distinguishes input/latent decodability from
  downstream strategic use and playing strength; variance diagnostics are only
  smoke checks. Draw-probability probes are for the known initial declaration.
- [Remaining-boundary evidence](remaining-boundary-evidence.json) records the
  current dynamic/semantic gaps without inventing a production ledger.

The rebuilt legacy-graph diagnostic executable is separate from the frozen
competitive bundle: shared controller source additions change its bytes.
Both original checkpoint files and every legacy generated kernel remain
unchanged from `f9cbbd427689081d5f12829b1fe7edd76ca51fab`.

## Next computation

The [unlaunched compute proposal](COMPUTE_PROPOSAL.md) caps a later three-control,
three-seed comparison at 500 updates per model, 4,500 total updates, batch 64,
one CPU worker, 30 minutes total fit wall time, 2 GiB process-tree RSS and 64
validation forwards. It requires new input/holdout manifests and a verified
guard before launch. The remaining-deck arm is deferred until a sound ledger
supports it. No larger fit or game allocation has been spent here.
