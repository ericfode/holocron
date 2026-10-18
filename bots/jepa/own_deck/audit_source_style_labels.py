"""Inventory existing source style labels; prepare a comparison plan without metrics.

Standard library only. Never imports an encoder, fits a model, computes a vector
distance, or modifies the imported decks or existing experimental artifacts.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent
IMPORT_COMMIT = "6253b1af1890df67d383141759c739834f7cba38"
UPSTREAM_COMMIT = "a2df9722314b1233d16747f7e56186071106799c"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def main():
    deck_path = REPO / "decks/ash-meta-2026-09.json"
    human_path = deck_path.with_name("ash-meta-2026-09.human.json")
    dataset_path = ROOT / "experiments/data/real-decks.npz"
    manifest_path = dataset_path.with_name("real-decks.manifest.json")
    export_path = ROOT / "experiments/embedding-export/deck-embeddings.json"
    export_manifest_path = export_path.with_name("deck-embeddings.manifest.json")
    transform = ROOT / "experiments/embedding-geometry/run-1/train-transform.npz"
    decks, human, manifest = read(deck_path), read(human_path), read(manifest_path)
    exported, export_manifest = read(export_path), read(export_manifest_path)
    assert len(decks) == len(manifest["declarations"]) == len(exported["rows"]) == 27
    assert manifest["artifact"]["sha256"] == sha(dataset_path)
    assert export_manifest["artifact"]["sha256"] == sha(export_path)
    train, val = manifest["split"]["train_idx"], manifest["split"]["val_idx"]
    assert len(train) == 22 and len(val) == 5 and not set(train) & set(val)
    assert sorted(train + val) == list(range(27))
    original = subprocess.check_output(["git", "show", f"{IMPORT_COMMIT}:bot/decks/ash-meta-2026-09.json"], cwd=REPO)
    assert hashlib.sha256(original).hexdigest() == sha(deck_path)
    with zipfile.ZipFile(dataset_path) as bank:
        array_names = sorted(Path(name).stem for name in bank.namelist())
    assert "style" not in array_names and "styles" not in array_names
    classes = sorted({deck["metadata"]["style"] for deck in decks})
    rows = []
    for dataset_index, declaration in enumerate(manifest["declarations"]):
        source_index = declaration["source_index"]
        deck, export_row = decks[source_index], exported["rows"][dataset_index]
        metadata = deck["metadata"]
        assert set(metadata) == {"name", "style"} and isinstance(metadata["style"], str)
        assert metadata["name"] == declaration["name"] == export_row["name"]
        assert source_index == export_row["source_index"]
        assert declaration["family_id"] == export_row["family_id"]
        split = "train" if dataset_index in train else "validation"
        assert export_row["split"] == split
        rows.append(dict(source_index=source_index, dataset_index=dataset_index, id=export_row["id"],
                         name=metadata["name"], source_style=metadata["style"],
                         style_labels=[metadata["style"]], ambiguity=None,
                         family_id=declaration["family_id"], split=split,
                         leader=deck["leader"], base=deck["base"],
                         companion_archetype=human["archetypes"][metadata["name"]],
                         documented_fixture_url=f"https://github.com/TCG-Engine/TCGEngine/blob/{UPSTREAM_COMMIT}/SWUSim/Tests/BotFixtures/ash-meta-2026-09/{metadata['name']}.txt"))
    assert set(human["archetypes"]) == {r["name"] for r in rows}
    support = {}
    for split in ("all", "train", "validation"):
        selected = [r for r in rows if split == "all" or r["split"] == split]
        support[split] = dict(rows=len(selected), families=len({r["family_id"] for r in selected}),
                             styles={label: dict(rows=sum(r["source_style"] == label for r in selected),
                                                 families=len({r["family_id"] for r in selected if r["source_style"] == label})) for label in classes})
    paths = [deck_path, human_path, REPO / "decks/README.md", REPO / "decks/LICENSE.TCGEngine",
             REPO / "decks/import-swusim.js", REPO / "engine/decklists.js", manifest_path, dataset_path,
             HERE / "real_deck_data.py", HERE.parent / "own_deck.py", HERE / "run_local_experiments.py",
             HERE.parent / "own_deck_model.py", HERE / "export_embeddings.py", Path(__file__)]
    audit = dict(schema="jepa-source-style-audit/1", status="metadata-only-audit-complete",
                 source_pins=[pin(p) for p in paths], source_rows=27, style_coverage=27, classes=classes,
                 source_metadata_fields=["name", "style"], multi_label_rows=0, explicitly_ambiguous_rows=0,
                 provenance=dict(imported_fixture_version=UPSTREAM_COMMIT,
                     fixture_folder="SWUSim/Tests/BotFixtures/ash-meta-2026-09",
                     local_first_import_commit=IMPORT_COMMIT, local_first_import_path="bot/decks/ash-meta-2026-09.json",
                     byte_identical_to_first_local_import=True,
                     retained_comment_rule=r"^#\s*Style:\s*([a-z-]+)\s*$ (case-insensitive); capture lowercased",
                     evidence=["engine/decklists.js:204-240", "decks/import-swusim.js:24-35", "decks/README.md:7-20"],
                     original_fixture_text_locally_available=False, original_comment_casing=None,
                     original_annotation_author=None,
                     local_search_scope="Named fixture .txt files under 2026-10-17 task directories, /Users/ericfode/src and /tmp; upstream commit object absent from this repository",
                     interpretation="Explicit labels in the imported fixture data, attributed by README/importer to SWUSim Style comments. Upstream original comments and authorship were not independently verified locally.",
                     weak_labels=True, behavioral_ground_truth=False, public_database_strategic_style_field_claim=False,
                     contradiction_resolution="A public API archetype defined by leader/base and absent strategic-style field is compatible with separate SWUSim fixture annotations. Imported metadata.style is not evidence that SWUMetaStats or SWU Stats has a structured strategic-style database field. Name/title tokens are not substitute labels."),
                 companion=dict(path=str(human_path), source=human["source"], exact_name_join_rows=27,
                     fields=["fieldDecks", "gameWinPct", "key", "label"],
                     origin="decks/import-swusim.js:34-35 copies these upstream real_matchups.json fields",
                     interpretation="Explicit source archetype keys/labels describe leader/base/color groupings, not newly inferred strategic classes. Human rates pool lists of the leader/base; not exact-list strength labels."),
                 family_origin=dict(authored_label=False, rule=manifest["split"]["rule"], evidence="real_deck_data.py:115-142,221-225"),
                 support=support, inherited_split=manifest["split"],
                 pipeline=dict(style_in_numeric_inputs=False, name_in_numeric_inputs=False,
                     style_in_readout_targets=False, name_in_readout_targets=False,
                     numeric_input_shape=[27, 2, 207], dataset_arrays=array_names,
                     actual_target_names=manifest["target_names"],
                     own_input_fields="hello.deck.deck[].id/count and hello.cards printed metadata; source metadata/name/style and own leader/base are not read by own_deck.py encoding",
                     printed_fields=manifest["printed_metadata_adapter"]["fields"],
                     name_use="real_deck_data.py:85 reads name only for record identification; NPZ deck_names is provenance and is not passed to the encoder",
                     source_style_use="Not retained in real_deck_data.py output declarations or NPZ; newly joined here by exact source index/name",
                     train_path="run_local_experiments.py:135-175 validates/returns deck_features and numeric targets; :254-265 passes numeric deck features and a fixed zero observation to the encoder, then a 13-column auxiliary readout",
                     export_path="export_embeddings.py:140-154 passes deck_features plus a fixed zero observation; names/families copied as output provenance only",
                     scope="Verified saved original-composition supplement and old 27-deck export pipeline; not a claim about every historical repository model"),
                 limitations=["Held-out five rows/four families cover only three styles; both control styles have zero held truth support.",
                     "Train softaggro has three rows but only one source family.",
                     "Sources02 and03 share a held family but have different styles; family is not a style class.",
                     "The same old vectors and some held examples were already inspected in prior geometry/reviews; new label question is exploratory, not pristine preregistered validation.",
                     "Single source fixture label per deck; no invented confidence, multi-label alternatives or gameplay truth."],
                 rows=rows, execution=dict(neural_forwards=0, nearest_neighbor_searches=0, metric_matrices=0,
                                          fits=0, optimizer_updates=0, native_calls=0, network_calls=0))
    audit_path = HERE / "source-style-labels.audit.json"
    write(audit_path, audit)
    group_specs = [("printed_mean_stats_per10", 8, 11), ("type_and_arena_fractions", 11, 16),
                   ("printed_cost_curve", 16, 25), ("keyword_fractions", 25, 35), ("aspect_fractions", 35, 41)]
    plan_inputs = [audit_path, deck_path, human_path, manifest_path, dataset_path, export_path, export_manifest_path,
                   transform, ROOT / "experiments/embedding-geometry/run-1/receipt.json", HERE / "embedding_geometry_audit.py"]
    plan = dict(schema="jepa-source-style-comparison-plan/1", status="frozen-plan-awaiting-root-execution-GO",
                execution_performed=False, source=pin(__file__), inputs=[pin(p) for p in plan_inputs],
                protected_checkpoints=[export_manifest[k] for k in ("base", "supplement")],
                source_audit=pin(audit_path), labels=dict(classes=classes, source_field="metadata.style",
                    rule="Exact categorical label equality, no assumed ordinal distance, no manual relabeling or title-derived labels",
                    multi_or_ambiguous="Preserve source lists/ambiguity if a later separately versioned source explicitly supplies them; do not fabricate here. Current pinned data has one label per row.",
                    numeric_encoder_inputs=False, numeric_features=False, role="Evaluation truth labels and, for optional frozen linear readout only, TRAIN22 supervised targets"),
                split=dict(train_indices=train, validation_indices=val, inherited=True, resplit=False,
                    train_families=7, validation_families=4, supported_validation_classes=[c for c in classes if support["validation"]["styles"][c]["rows"]],
                    unsupported_validation_classes=[c for c in classes if not support["validation"]["styles"][c]["rows"]]),
                methods=["raw_cosine", "train_centered_cosine", "train_shrunk_whitened_cosine", "count_weighted_jaccard", "printed_metadata_profile", "train_majority"],
                transforms=dict(dtype="float64", zero_norm_epsilon=1e-12, fitted_on="inherited TRAIN22 only",
                    use_saved_transform=str(transform), transform_sha256=sha(transform),
                    mean="TRAIN22 raw z96 arithmetic mean",
                    white="Saved alpha0.1 shrinkage: C_reg=0.9*C+0.1*trace(C)/96*I, C unbiased TRAIN22 covariance; (z-mean)@C_reg^(-1/2)",
                    hyperparameter_search=False, no_new_neural_forward=True),
                independent_baselines=dict(
                    canonical_counts="Declared MAIN canonical counts; weighted Jaccard=sum min / sum max; no leader/base/sideboard. Use all actual canonical identities for distances, not source names/style.",
                    printed_profile=dict(groups=[dict(name=n, start=a, stop=b) for n,a,b in group_specs],
                        distance="Equal mean of five within-group mean absolute differences, similarity=-distance. Original known metadata row only; excludes status, ID hashes, hashed traits and source labels."),
                    train_majority="Most frequent TRAIN22 style; ties lexicographic class order. No held prevalence used."),
                nearest_neighbors=dict(primary="Five inherited validation queries against TRAIN22, k=1 and3 fixed; no self/family leakage across inherited split",
                    secondary="Optional all27 leave-one-self-out and train22 leave-one-family-out results, explicitly descriptive; no parameter selection or primary pooling",
                    label_agreement="For each query/k, fraction of selected neighbor labels equal to query source style; report every query and aggregate by row, held family and supported class",
                    ties="Sort by descending score then ascending source_index for stable displayed neighbors/prediction. Also report whole equal-score tie sets using absolute tolerance1e-12 and fractional boundary-tie agreement; never silently resolve a tie as evidence.",
                    prediction="Top1 deterministic neighbor source style; top3 class vote with equal weights, ties lexicographic frozen classes; expose tied votes",
                    nulls="Zero-norm/unavailable scores are null with explicit excluded denominators, not zero similarities"),
                optional_ridge=dict(enabled_in_frozen_plan=True, algorithm="Closed-form multi-output ridge regression on one-hot TRAIN22 labels; alpha=1.0 fixed, intercept unpenalized, no optimizer",
                    features=["raw z96", "train-centered z96", "saved train-shrunk-whitened z96", "TRAIN22 canonical main-count vocabulary/60 plus one unseen-card-copy-count/60 channel", "33 printed-profile coordinates across the fixed five groups"],
                    normalization="Each coordinate standardized with TRAIN22 mean and population standard deviation only; zero TRAIN variance mapped to0 for all rows, explicitly counted. No normalization fit on validation.",
                    solver="float64: center standardized X and one-hot Y using TRAIN22; W=X_train.T @ solve(X_train@X_train.T + I22, Y_train-Y_train_mean). Predict X@W + Y_train_mean; argmax frozen class order. Objective sum squared errors + 1.0*||W||².",
                    counts_vocabulary="Sorted TRAIN22 canonical IDs only. Validation-only IDs enter an explicit unseen-copy channel; no label/name-derived features.",
                    interpretation="Raw and centered z96 become equivalent under train standardization up to numerical error; not independent supporting results. Linear scores are not calibrated class probabilities.",
                    no_hyperparameter_search=True, early_stopping=False),
                reporting=dict(primary_accuracy="Correct held predictions /5; predictions may be any of all five classes, not restricted to three held classes",
                    confusion="Full frozen five-class 5x5 count matrix, all supports printed; truth rows with zero support have count0 but recall/F1/accuracy fields null, never scored as0",
                    macro="Macro recall/F1 over the THREE supported held classes only; all-five-class macro=null/unsupported. Also print row and four-family macro accuracy; no independence claim.",
                    per_query="Source index, family, source style, prediction, neighbors/scores/ties, support and error; preserve uncertainty and prior-review exposure flags",
                    no_inference="No p values, significance, confidence intervals, strategy/strength/behavioral-truth claim, majority-vote reviewer truth, or selection of best transform after results"),
                prior_exposure=dict(old_vectors_previously_inspected=True, inherited_validation_is_pristine=False,
                    reviewed_held_sources=[2,3], new_ir_assay_unreviewed_background_sources=[10,14,25],
                    note="This is a new weak-label question on an already inspected frozen representation. It is separate from score-blind synthetic IR controls and does not make their AST proxy semantic truth."),
                support=support, limits=dict(total_preparation_plus_execution_wall_seconds=20, cpu_seconds=20,
                    sampled_rss_bytes=512*1024*1024, compute_threads=1, neural_forwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0),
                execution_rule="Root must approve this exact plan before any metrics/closed-form fitting. Freeze runner source and guard/report all attempts; check source/transform/checkpoint hashes before and after. Do not modify old vectors, transforms, checkpoints, imported decks or existing control files.")
    plan_path = HERE / "source-style-labels.plan.json"
    write(plan_path, plan)
    short_families = {f: "F" + str(i+1).zfill(2) for i,f in enumerate(sorted({r["family_id"] for r in rows}))}
    lines = ["# Source style labels", "", "All 27 imported decks explicitly contain one `metadata.style` label. These are weak fixture labels; they are not established behavioral or strategic ground truth.", "",
             "The importer preserves `# Style: <word>` fixture comments and lowercases the captured text (`engine/decklists.js:204–240`, `decks/import-swusim.js:25`). The README attributes fixtures to TCGEngine / SWUSim `SWUSim/Tests/BotFixtures/ash-meta-2026-09` at `"+UPSTREAM_COMMIT+"`. Current deck JSON is byte-identical to the first local import `"+IMPORT_COMMIT+"` (2026-10-11), historical `bot/decks/ash-meta-2026-09.json`.", "",
             "Original upstream fixture text was not found locally and its upstream commit object is absent here. Original comment casing and annotation author are unknown. The parser/README provide the import contract; they do not independently prove who authored the original annotation. No web lookup was performed for this audit.", "",
             "There is no contradiction with a public API defining archetype as leader/base and exposing no strategic-style field: these labels are separate fixture annotations. Do not describe them as structured SWUMetaStats/SWU Stats strategic tags. Titles and leader/base/color names are excluded as substitute labels.", "",
             "The companion human JSON has 27 exact-name-joined `archetypes` entries, each with `fieldDecks`, `gameWinPct`, `key`, `label`, copied by `import-swusim.js:34–35`. Their labels/keys describe source leader/base/color groupings. Human win rates pool lists of the leader/base, not this exact deck. Local family IDs are derived from shared leader, base, fingerprint or ≥80% copy overlap; they are not source-authored style classes.", "",
             "## Coverage and inherited split", "", "| Style | All rows | Train rows / families | Held rows / families |", "|---|---:|---:|---:|"]
    for c in classes:
        lines.append(f"| {c} | {support['all']['styles'][c]['rows']} | {support['train']['styles'][c]['rows']} / {support['train']['styles'][c]['families']} | {support['validation']['styles'][c]['rows']} / {support['validation']['styles'][c]['families']} |")
    lines += ["", "The inherited split has 22 training rows/seven families and five held rows/four families. Training covers five styles; held truth covers only three. Hardcontrol and softcontrol held metrics must be null. Sources02/03 share a held family but have different styles. The three training softaggro examples belong to one family.", "",
              "The saved model encoding reads own main-card IDs/counts and printed card metadata into `[27,2,207]`. It does not read deck metadata, source names/styles or own leader/base. `real_deck_data.py:85` retains name only as provenance. The 13 auxiliary targets are total count, mean/low cost, nine cost bins and initial one-card unit probability (`real_deck_data.py:27–28,84–112`). `run_local_experiments.py:135–175,254–265` passes only numeric features/targets with a fixed zero observation. `export_embeddings.py:140–154` passes the same numeric features; names/families are output provenance. This conclusion applies to the saved original-composition supplement/export pipeline, not every historical model.", "",
              "## Fixed comparison plan; execution pending", "",
              "`source-style-labels.plan.json` freezes primary held5→train22 top1/top3 agreement for raw, train-centered and saved alpha0.1 whitened cosine, canonical-count Jaccard and five-group printed profile, plus training-majority. It also fixes an optional closed-form alpha1 ridge readout for the same representations/baselines; train-only standardization, no neural forward, optimizer or parameter search. Full five-class confusion and support are required; primary class macro covers only three supported held classes. Plan execution requires root GO under one 20-second/512MiB/single-thread guard including preparation.", "",
              "These vectors and some examples have already been inspected in prior geometry/reviews. This new weak-label comparison is exploratory. It does not validate gameplay strength or the separate synthetic IR structural proxy.", "",
              "## Exact per-source mapping", "", "Family aliases below are display-only; complete exact family IDs are in the audit JSON and alias table.", "", "| Index | Source filename stem | Explicit style | Split | Family |", "|---:|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['source_index']:02} | {row['name']} | {row['source_style']} | {row['split']} | {short_families[row['family_id']]} |")
    lines += ["", "| Alias | Exact local family ID |", "|---|---|"]
    lines += [f"| {alias} | `{family}` |" for family,alias in short_families.items()]
    lines += ["", "## Pins and audit checks", "", f"- Deck JSON: `{sha(deck_path)}`.", f"- Companion human JSON: `{sha(human_path)}`.", f"- Dataset manifest: `{sha(manifest_path)}`.", f"- Exact audit JSON: `{sha(audit_path)}`.", f"- Frozen comparison plan: `{sha(plan_path)}`.", "", "The audit checks all 27 source-index/name/family/split joins, current versus first-import bytes, existing dataset/export hashes and label absence from NPZ field names. Full source hashes and public fixture reference URLs are in the audit JSON. No fitting, metric matrices, nearest-neighbor search, neural forward, native calls or network access were performed.", ""]
    (HERE / "SOURCE_STYLE_LABELS.md").write_text("\n".join(lines))
    print(json.dumps(dict(audit=pin(audit_path), plan=pin(plan_path), report=pin(HERE / "SOURCE_STYLE_LABELS.md"), support=support), indent=2))


if __name__ == "__main__":
    main()
