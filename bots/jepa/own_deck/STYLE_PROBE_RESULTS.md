# Source style probe results

The frozen representation shows limited agreement with the imported fixture style labels on five held decks. Nearest-neighbor predictions match one or two of five labels depending on the fixed method. Fixed alpha1 ridge matches two of five for raw/centered vectors and three of five for whitened vectors. These are exploratory weak-label results, not evidence of behavioral similarity, strategy quality or strength; no method is selected for deployment.

## Support and provenance

The inherited split remains TRAIN22/seven families and held5/four families. Training has all five styles; held truth has hyperaggro2 (sources03/10), softaggro2 (02/14) and midrange1 (25). Sources02/03 share one family. Hardcontrol and softcontrol have zero held truth support: their per-class metrics and the all-five-class macro are null. The three training softaggro rows share one family. All five held predictions are available for every reported method.

All 27 `metadata.style` values are explicit in the imported JSON. The importer documents preserving lowercased SWUSim fixture `# Style:` comments. JSON is byte-identical to first local import `6253b1af1890df67d383141759c739834f7cba38`; the README attributes fixtures to upstream `a2df9722314b1233d16747f7e56186071106799c`. Original upstream comment text/casing and annotation authorship were not independently verified locally. These are separate fixture annotations, not evidence of a structured strategic-style field in SWU Stats/SWUMetaStats. Source names/titles and styles were absent from the saved model's numeric inputs and 13 composition targets. Full evidence and all27 mappings are in [SOURCE_STYLE_LABELS.md](SOURCE_STYLE_LABELS.md) and [source-style-labels.audit.json](source-style-labels.audit.json).

This is a new label question on previously inspected vectors; sources02/03 also appeared in earlier reviews. The result is not pristine validation. It is separate from the synthetic IR module assay and does not establish that assay's structural proxy as semantic truth.

## Nearest neighbors

Queries are the same five held decks; candidates are TRAIN22. Top3 prediction is the most common neighbor label, with frozen lexicographic class order for vote ties. “Agreement” is the mean fraction of three neighbors whose labels match the query, distinct from classification accuracy. Family macro weights each of four held families equally. Percentages below are descriptive.

| Fixed distance | Top1 correct /5 | Top1 family macro | Top3 correct /5 | Top3 family macro | Top3 label agreement |
|---|---:|---:|---:|---:|---:|
| Raw cosine | 2 | 50% | 2 | 50% | 33.33% |
| TRAIN22-centered cosine | 1 | 25% | 2 | 50% | 40% |
| Saved TRAIN22 alpha0.1 whitened cosine | 2 | 50% | 2 | 50% | 33.33% |
| Canonical main-count weighted Jaccard | 1 | 25% | 1 | 25% | 20% |
| Five-group printed profile | 2 | 50% | 1 | 25% | 20% |

| Fixed distance | Top1 supported-class macro recall / F1 | Top3 supported-class macro recall / F1 |
|---|---:|---:|
| Raw cosine | 50% / 38.89% | 50% / 33.33% |
| TRAIN22-centered cosine | 16.67% / 13.33% | 50% / 46.67% |
| Saved TRAIN22 alpha0.1 whitened cosine | 50% / 38.89% | 50% / 38.89% |
| Canonical main-count weighted Jaccard | 16.67% / 13.33% | 16.67% / 13.33% |
| Five-group printed profile | 50% / 35.56% | 16.67% / 13.33% |

Top3 vote ties occur for raw/source10 (midrange, softaggro, softcontrol), centered/source02 (hyperaggro, midrange, softaggro), whitened/source02 (midrange, softaggro, softcontrol), counts/source25 (hyperaggro, midrange, softaggro), and profile/source25 (hyperaggro, midrange, softcontrol). No top1 vote ties or score-boundary ties within the fixed absolute tolerance1e-12 occur; fractional boundary-tie agreement equals the displayed deterministic agreement. Vote ties remain visible in the result rather than becoming evidence for the chosen label.

The TRAIN22 majority label is softcontrol: 0/5 correct and 0% family macro. Its failure also reflects that softcontrol is absent from held truth; it does not establish a universal chance baseline.

## Fixed linear readouts

Five independent closed-form ridge readouts use the fixed alpha1, unpenalized intercept and TRAIN22 one-hot labels. Each representation is standardized using TRAIN22 coordinate means/population standard deviations only; zero-variance coordinates map to0. Counts use a TRAIN22-only canonical-ID vocabulary plus an unseen-copy channel. The printed baseline has 33 coordinates from the same five fixed groups used above.

| Fixed alpha1 readout | Dimensions / zero-variance columns | Correct /5 | Family macro | Supported-class macro recall / F1 |
|---|---:|---:|---:|---:|
| Raw z96 | 96 /0 | 2 | 50% | 50% /33.33% |
| TRAIN22-centered z96 | 96 /0 | 2 | 50% | 50% /33.33% |
| Saved TRAIN22 alpha0.1 whitened z96 | 96 /0 | 3 | 75% | 66.67% /66.67% |
| Canonical counts | 220 /1 | 1 | 25% | 16.67% /16.67% |
| Printed profile | 33 /2 | 1 | 25% | 16.67% /13.33% |

Raw and centered ridge predictions are identical, as expected from train standardization; they are redundant evidence. The whitened readout matches sources10/14/25 and misses02/03. Count/profile readouts match source14 only. The count unseen-copy channel has zero training variance and cannot learn an effect under this normalization. No ridge class-score argmax ties occur within1e-12. Linear scores are not calibrated probabilities.

No hyperparameter search, optimizer updates, best-validation checkpoint/transform selection, secondary leave-one-out analysis, neural forward, native execution or paid job occurred. The five-class confusion matrices, exact class scores, per-query neighbors/ties and row/family/class aggregates are retained in the result JSON. There are no inferential tests or five-style generalization claims.

## Exact artifacts and bounded receipt

Source execution commit: `32dc59a50bd76633dad4460f109a3fe04b10c87b`. Root executed the frozen runner once. The receipt reports 0.047800333s execution, 0.011512834s preparation, 0.059313167s aggregate, 0.041352s execution CPU, 39,632,896 bytes peak RSS (39.63MB;37.80MiB), one compute thread. The run completed before the first50ms periodic sample; RSS evidence is process high-water rusage, not an instantaneous memory reservation. Protected source/checkpoint/input hashes stayed unchanged.

- External result: `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/source-style-labels/run-1/result.json`; SHA256 `d37eb9d7779c32118f8851b2ecebb82d3607f1842d9602679fc8edb6eb21bbb2`.
- Receipt: same directory, `receipt.json`; SHA256 `a3c79411997889235b512272713fb06196fb8fdd4b5dad250010a69d8c9ff40c`.
- Frozen execution plan: `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/source-style-labels/plan.json`; SHA256 `e334807541bf85da388c962f45108ba67b654d37cb90906fb9b292a52bbae7fd`.
- Runner [source_style_probe.py](source_style_probe.py); SHA256 `ed324ce1f61b93825a9afb9ba6194c67f0263dd954c81ccd2d0f20cc674e1807`. Four pure tests passed before execution.
- Immutable proposal [source-style-labels.plan.json](source-style-labels.plan.json); SHA256 `4dd73f0dbcad4c18200078b127d14463d7d4d4088dc4ab044c86ae16f121a59c`.
- Audit [source-style-labels.audit.json](source-style-labels.audit.json); SHA256 `5fe066d1827bfca2b616946ed4404647236e185a690ba0012207d3eacc9e7b50`.

This report only reads the saved result/receipt and formats their values; it does not rerun metrics or fitting.
