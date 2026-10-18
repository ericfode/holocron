The saved 27-deck, 96-dimensional export has a strong common direction and low-dimensional residual variation. Near-one raw cosine is therefore insufficient evidence of semantic equivalence. Train-only centering reveals more angular spread; fixed shrinkage whitening does not establish better held-out retrieval. This audit changes no encoder, raw vector, checkpoint, native-contrast configuration, or deployment.

The frozen plan is [plan.json](embedding-geometry-evidence/plan.json), SHA-256 `af15cbc057b76faf4cd185c9495de7b77431abac63763036fbd45b0d35077518`. The source is [embedding_geometry_audit.py](embedding_geometry_audit.py), SHA-256 `a8151c194f254e7d3d7444db24051ef53a5906665286cd54143069964439d12d`, committed before execution at `bfcdb30e1b869ade776b558ee1b433c836084c9a`. Preparation used only metadata and hashes; the numerical run followed coordinator GO. Full scores, ranks, eigenvalues and denominators are in [result.json](embedding-geometry-evidence/result.json); execution evidence is [receipt.json](embedding-geometry-evidence/receipt.json). Portable copies are indexed by [index.json](embedding-geometry-evidence/index.json).

The inherited split was fixed at 22 training decks and five validation decks (`02,03,10,14,25`), in four validation families. The arithmetic mean and unbiased covariance were fitted on training vectors only. Whitening used the predeclared `0.9*C + 0.1*trace(C)/96*I`, with no parameter search or validation fitting. All three angular methods use the original raw vectors; transformed copies and fitted mean/matrix are separate artifacts. Counts use canonical main-deck multiplicities. The printed-profile baseline is the equal mean of five groupwise mean absolute distances: printed cost/power/HP means, card type/arena fractions, cost curve, keyword fractions and aspect fractions. These are actual original-row features from [own_deck.py](../own_deck.py#L129), excluding status, identity hashes and hashed traits. They are independent calculations of composition, not independent gameplay relevance labels.

| Saved geometry | Result |
| --- | ---: |
| Raw vector norm, minimum / median / maximum | 8.598553 / 9.075836 / 9.612085 |
| Training mean norm | 8.858958 |
| Training energy accounted for by common mean | 97.0543% |
| Largest uncentered second-moment eigenvalue fraction | 97.1343% |
| Uncentered entropy / participation effective rank | 1.1816 / 1.0595 |
| Centered entropy / participation effective rank | 3.6402 / 2.6789 |
| Centered top-one / top-three variance fraction | 55.0799% / 91.6446% |
| Centered numerical covariance rank | 21 of at most 21, from 22 training rows |
| Raw / centered / whitened median pair cosine | 0.977393 / −0.032776 / −0.060789 |
| Raw pair Euclidean distance, minimum / median / maximum | 0.247778 / 1.983532 / 4.583783 |

This is strong anisotropy rather than identical-vector collapse: vectors and residuals differ, with 21 numerical covariance directions. Most residual variance nevertheless occupies roughly three to four effective directions. Centering preserves every Euclidean distance (maximum numerical discrepancy `4.44e-16`); wider cosine spread alone is a change of origin, not evidence of new information. Whitening condition number is 476.89, with inverse-standard-deviation gains 0.8982–19.6140. Estimating 96 directions from 22 examples remains underdetermined despite regularization. Only 0.5102% of held-out centered energy lies outside the training covariance span; that is a geometry observation, not evidence of semantic generalization.

The composition comparison below uses **five validation queries against the 22 training candidates**. Higher top-one weighted Jaccard and lower printed-profile distance are better only as these composition proxies. Family macro averages give the four validation families equal weight. A baseline evaluated on the quantity it optimizes is an oracle for that proxy, not an independent semantic winner.

| Method | Query-mean top-one Jaccard | Family-macro Jaccard | Query-mean profile distance | Family-macro profile distance |
| --- | ---: | ---: | ---: | ---: |
| Raw cosine | 0.175072 | 0.165990 | 0.085029 | 0.090049 |
| Train-centered cosine | 0.180597 | 0.172897 | 0.082066 | 0.086345 |
| Train-shrunk-whitened cosine | 0.175072 | 0.165990 | 0.085029 | 0.090049 |
| Count-weighted Jaccard | 0.209603 | 0.191792 | 0.077216 | 0.083493 |
| Printed-profile baseline | 0.197849 | 0.177100 | 0.075409 | 0.081235 |

Centering changes two top-one neighbors (`10:16→17`, `25:24→08`), with small proxy gains; three stay unchanged. Whitening selects exactly the same five top-one neighbors as raw cosine. Descriptive Spearman correlations on the 110 dependent validation–training pairs are raw/centered/whitened `0.4958/0.4752/0.3560` against count overlap, and `0.5759/0.5944/0.4116` against the printed profile. These pairs share five queries and 22 candidates; they are not 110 independent test observations. There is no consistent improvement across controls and no semantic-improvement claim.

The separately predeclared structural control uses all other 26 decks as gallery. The only validation same-family/same-leader positive is `02↔03`: one unordered pair and two dependent query directions, with three other validation queries lacking positives. The inherited split leaves **no** positive family/leader/base controls in the training-only gallery. Exact-main and same-base validation positives are absent, so those metrics are unsupported, not zero.

| Method | Positive ranks for queries 02 / 03 | Recall@1 | Recall@3 | MRR |
| --- | --- | ---: | ---: | ---: |
| Raw cosine | 2 / 3 | 0/2 | 2/2 | 0.4167 |
| Train-centered cosine | 2 / 3 | 0/2 | 2/2 | 0.4167 |
| Train-shrunk-whitened cosine | 2 / 1 | 1/2 | 2/2 | 0.7500 |
| Count-weighted Jaccard | 4 / 5 | 0/2 | 0/2 | 0.2250 |
| Printed-profile baseline | 14 / 7 | 0/2 | 0/2 | 0.1071 |

The whitening improvement on one direction of one structural pair is too little support to select a retrieval method or infer gameplay similarity. No exact-identity holdout control can be estimated from these five decks. Their card identities overlap training, so this is not unseen-card evaluation.

The requested third review and matching Markdown were read together with the two earlier reviews. Their pairs were selected using existing metrics and card/effect inspection. The third review contains eight training/training pairs and one validation/training pair, with no validation/validation pair. Repeated reviewers and overlapping pairs are posthoc qualitative context, never fresh holdout truth or majority-voted labels. For example, the third review's two misleading pairs `06/16` and `06/20` move from raw global ranks `6/14` to centered `63/148` and whitened `26/183`; the plausible `06/07` pair also moves `23→89/10`. The disputed validation/training pair `03/21` moves `11→4/8`, while the earlier and third reviews disagree between plausible and uncertain. These are descriptive rank changes, not scored annotation accuracy. Raw near-one cosine should be presented alongside count/profile evidence and this anisotropy diagnosis.

The first and only matrix execution used NumPy alone: **0.078760208 seconds wall, 0.067914 seconds CPU, 53,690,368 bytes high-water RSS, one compute thread**. The 20-second wall/CPU and 512-MiB sampled-RSS bounds passed; RSS sampling is not an instantaneous OS memory reservation. There were zero neural forwards, native calls, optimizer updates or paid jobs. Protected input hashes were checked before and after, including raw export `7917ee4d76e86ac1fd3f3d63e546adc07d15da05bb866e14eaccd632b81e5301`, base checkpoint `50b8f9a2c3782c5cf5b23e80b2a65d2a0292523ec9a9213287b86143f99b6d34`, and original-composition supplement `498f2c9a796ec75879796eb6d43c812f72a7a06b10d0774c74aed328b1315cbc`. All were unchanged. External originals remain at `/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/embedding-geometry/`; raw annotations are not republished here. The separate native-contrast fit has no bearing on validation of these earlier 27 deck vectors.
