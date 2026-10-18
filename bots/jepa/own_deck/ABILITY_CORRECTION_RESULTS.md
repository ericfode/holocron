# Frozen-weight eligibility correction

The parameter-free correction restored intent invariance but **failed the
predeclared accuracy gate**. Seed29 worsened both anchor eligibility MAE and
balanced accuracy; seed43 worsened MAE. Do not promote the patch. Production
remains unchanged and `semantic_validated=false`.

The test used eight new native roots: four public states of the already exposed
IBH_104 program, each with intended anchor A/B. Native collection completed
**20 successful applications, eight roots, zero errors**: four paid committed
outcomes and four settled cancellations. Cancelled target futures remain
unknown. These are four state families, not eight independent programs or a
new-program transfer test.

The three saved learned checkpoints, full eight-card bank and original TRAIN
transforms stayed frozen. Each seed ran two forwards: **O**, original corrected
C1R1 input; **N**, the same input with normalized candidate relation columns
41:43 zeroed for every head. **C** is a derived output that takes only
`target_allowed` from N and retains the other outputs from O. Total exposure was
**six forwards, zero updates, zero numerical fits, zero export forwards**.

The primary panel has 16 known anchor eligibility coordinates, eight positive
and eight negative, nested within eight roots. MAE is root-balanced; balanced
accuracy averages sensitivity and specificity. Each seed had to preserve both
metrics within 1e-6 while restoring intent invariance.

| Seed | O anchor MAE | C anchor MAE | O balanced accuracy | C balanced accuracy | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| 17 | 0.519756 | 0.499995 | 0.4375 | 0.5000 | Pass |
| 29 | 0.458424 | 0.461825 | 0.5625 | 0.5000 | **Fail** |
| 43 | 0.498372 | 0.505696 | 0.5000 | 0.5000 | **Fail** |

Maximum same-state intent-pair eligibility differences fell from
0.632367 / 0.379824 / 0.383636 to **exactly zero** for seeds17/29/43.
N and C have identical eligibility. C's nine source outputs and six other
branch heads are **bit-identical to O**, including all endpoint consequences.
The all-head neutral control N also changed source and endpoint predictions;
its removal MAE increased in every seed. Saved JSON retains all 16-head metrics
for O/N/C and the secondary all-known/non-source eligibility panels. Those
secondary panels do not replace the anchor gate.

Both original and R-neutral inputs passed novelty checks against preceding
IBH_104 rows: all eight full panels, all eight source-consumed inputs and all
64 candidate-consumed inputs were new. The checks use actual head-local inputs,
not unrelated sibling candidates. Checkpoint state hashes match before/after
inference in all three seeds. This was an inference-only intervention on weights
trained with R; it did not test retraining with head-specific routing. Enforced
invariance alone did not establish useful accuracy or learned rule semantics.

Source freeze: `48215e6717b1cc4f6f271786ae2e70b7a191a5da`.
The [worker](ability_correction.py) and
[native-data adapter](ability_correction_prepare.py) preserve the old source,
native label/mask derivation and model. This note was prepared using saved JSON
only, with no new model, array, native or fitting execution.

Evidence origins are under `experiments/ability-correction-v1/` in the task7
workspace. Exact byte pins:

| Artifact | SHA256 |
| --- | --- |
| `correction-1/result.json` | `d63547a83eb5502c0147a4e3e80f477fca1c9b15daf51aca20691178b40de2f9` |
| `prep-1/dataset.npz` | `c48b74c35f056b66f245b5088e54b733d93e7925ca8b2a19dafc8ff89ded34d7` |
| `prep-1/dataset.manifest.json` | `d1e58a76df8271da3982fe86617dde9caef82b380c181fbf9db1de66d555d644` |
| `native-plan.json` | `ad0e643a051e3d05442da2d01f05997b459992986ab2c2156406eada87bb50ee` |
| `native-attempt-1/native-receipt.json` | `9c587b4b4a98ddb6821397225a3bdd921ff5d378a1b4e84acbccb2e9bfa4ee95` |
| `native-attempt-1/native-transitions.jsonl` | `5013a5871ae89a1b8ac3bb4d3593e486c74c8adf0fb3f56982d7ca29ccb413d9` |
| `campaign-spec.json` | `204ae6e2ac8eaa3441a5d9a43d4acae443e892608a7ca4c7b4bd337e973a8222` |

At correction completion, before the separate independent verification stage,
the linked carry was **295 charged applications / 222.5877107490087 charged
seconds**; historical aggregate observed applications remain unknown. The new
campaign recorded 20 observed applications, six forwards and zero paid jobs or
spend. The ledger snapshot had 25 records, file SHA256
`e50367ee36e949996e413b29eab5fb646df84c90754d98256f591fc86e004c49`
and final chain
`94fb60a4922dc16c3a6970b9949acca6d86f5941e63eb5df2c8f376a6e96c27f`.
Independent verification has a separate three-second allocation and is not
claimed complete by this snapshot. All earlier failures and negative reports
remain preserved.
