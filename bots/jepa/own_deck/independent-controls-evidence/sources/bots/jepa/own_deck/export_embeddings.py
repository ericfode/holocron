"""Inventory saved representations; explicit label-free deck export after root GO.

The default command creates pending browser metadata without a model forward.
--export-decks performs one NumPy encoder call for a batch of 27 rows,
using the original-composition readout supplement, with no optimizer or engine.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent
DEFAULT_OUT = ROOT / "experiments/embedding-export"
INDEX_SCHEMA = "jepa-embedding-browser-index/1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def peak_rss_mib():
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024


def specification():
    summary = read(HERE / "local-fit-summary.json")
    run = next(r for r in summary["runs"] if r["arm"] == "original")
    result_path = Path(run["result_path"])
    if sha(result_path) != run["result_sha256"]:
        raise ValueError("original-composition raw fit receipt changed")
    result = read(result_path)
    if result["updates"] != 100 or result["arm"] != "original" or not result["frozenBaseTensorsUnchanged"]:
        raise ValueError("expected original 100-update composition supplement")
    supplement = next(p for p in run["checkpoints"] if Path(p["path"]).name == "final-deck.safetensors")
    if sha(supplement["path"]) != supplement["sha256"]:
        raise ValueError("trained original supplement changed")
    base = HERE.parent / "models/tx-t10.safetensors"
    if sha(base) != result["immutableBefore"][str(base)]:
        raise ValueError("frozen base changed")
    dataset = ROOT / "experiments/data/real-decks.npz"
    manifest_path = dataset.with_name("real-decks.manifest.json")
    manifest = read(manifest_path)
    if sha(dataset) != summary["dataset_sha256"] or sha(manifest_path) != summary["manifest_sha256"] or sha(dataset) != manifest["artifact"]["sha256"]:
        raise ValueError("source-backed deck dataset or family split changed")
    source = next(s for s in manifest["sources"] if Path(s["path"]).name == "ash-meta-2026-09.json")
    if sha(source["path"]) != source["sha256"]:
        raise ValueError("declared card lists changed")
    return dict(base=dict(path=str(base), sha256=sha(base)), supplement=supplement,
                training_commit=summary["training_commit"], training_run_id=run["run_id"], updates=100,
                dataset=dict(path=str(dataset), sha256=sha(dataset)), dataset_manifest=dict(path=str(manifest_path), sha256=sha(manifest_path)),
                source_decks=source, manifest=manifest)


def pending_index(out, spec):
    out = Path(out)
    return dict(schema=INDEX_SCHEMA, updated_at_utc=timestamp(), status="pending-actual-neural-vectors",
                spaces=dict(deck=dict(id="original-deck-composition-z96", entity_type="deck", status="pending_forward",
                                      entity_count=27, dimension=96, vector_kind="actual neural encoder latent; not yet exported",
                                      semantic_validated=False, relative_file="deck-embeddings.json", vectors_path=str(out / "deck-embeddings.json"),
                                      manifest_path=str(out / "deck-embeddings.manifest.json"), checkpoint=dict(base=spec["base"], supplement=spec["supplement"]),
                                      limitation="Supplement trained for declared composition readouts; no behavioral similarity, synergy or strength validation."),
                            card=dict(id="supported-typed-card-program", entity_type="card", status="pending_fit_and_forward",
                                      entity_count=None, dimension=None, vector_kind="actual learned typed-program latent; unavailable",
                                      semantic_validated=False, relative_file="card-embeddings.json", vectors_path=str(out / "card-embeddings.json"),
                                      manifest_path=str(out / "card-embeddings.manifest.json"),
                                      limitation="No hashed-ID lookup, raw counts, random vector or untrained feature vector is substituted for learned effect embeddings.")),
                metrics=dict(cosine_distance="1 - dot(unit_vector_a,unit_vector_b); unavailable for zero-norm vectors",
                             euclidean_raw="sqrt(sum((vector_a-vector_b)^2)); sensitive to latent scale",
                             euclidean_unit="sqrt(sum((unit_vector_a-unit_vector_b)^2)); monotonic with cosine distance",
                             normalization="Raw vectors and explicit L2-unit vectors must be labelled separately; no fitted whitening or semantic calibration.",
                             shared_copies="sum_c min(query canonical main count[c], candidate canonical main count[c]); excludes leaders/bases/sideboards",
                             weighted_jaccard="shared_copies / sum_c max(query canonical main count[c],candidate canonical main count[c]); both-empty convention1",
                             overlap_query="shared_copies / query main total; undefined for empty query",
                             overlap_candidate="shared_copies / candidate main total; undefined for empty candidate",
                             overlap_smaller="shared_copies / min(query main total,candidate main total); undefined if either empty",
                             count_overlap_scope="Canonical/reprint-collapsed declared MAIN counts only; composition similarity, not learned or behavioral semantics."),
                optimizer_updates=0, native_engine_calls=0, paid_jobs=0)


def inventory(out):
    spec = specification()
    sources = []
    for path in sorted((ROOT / "experiments").rglob("*.npz")):
        if "/target/" in str(path) or "/embedding-export/" in str(path):
            continue
        with np.load(path, allow_pickle=False) as values:
            arrays = {k: dict(shape=list(values[k].shape), dtype=str(values[k].dtype)) for k in values.files}
        kind = "raw input/label bank"
        if path.parent.name.startswith("restoration-"):
            kind = "logistic head parameters and training normalization statistics; no per-deck latent bank"
        sources.append(dict(path=str(path), sha256=sha(path), kind=kind, arrays=arrays))
    evidence = dict(schema="jepa-embedding-inventory/1", checked_at_utc=timestamp(), actual_saved_deck_latent_banks_found=0,
                    historical_representation_probe="representation-probe.json contains aggregate readout/variance metrics only, not per-example latents",
                    actual_saved_card_semantic_banks_found=0, source_arrays=sources,
                    requirements=dict(deck="One new label-free batch forward using pinned base + original 100-step supplement is required.",
                                      card="Final structured model weights alone do not save encoded program vectors; a separately authorized program-bank extraction is required."),
                    forward_calls_performed=0, optimizer_updates=0, native_calls=0)
    write(Path(out) / "inventory.json", evidence)
    write(Path(out) / "index.json", pending_index(out, spec))
    write(Path(out) / "inventory.manifest.json", dict(schema="jepa-embedding-inventory-manifest/1", inventory_sha256=sha(Path(out) / "inventory.json"),
                                                        index_sha256=sha(Path(out) / "index.json"), script=dict(path=str(Path(__file__)), sha256=sha(__file__)),
                                                        source_checkpoint=dict(base=spec["base"], supplement=spec["supplement"]), vectors_exported=False))
    return spec


def export_decks(out):
    """Explicit root-authorized label-free export; no fitting or evaluation labels."""
    spec = specification()
    out = Path(out)
    protected = {p["path"]: p["sha256"] for p in (spec["base"], spec["supplement"])}
    with np.load(spec["dataset"]["path"], allow_pickle=False) as data:
        contexts = data["deck_features"].copy()
        names, fingerprints, families = data["deck_names"].tolist(), data["fingerprints"].tolist(), data["family_ids"].tolist()
        train, val = set(data["train_idx"].tolist()), set(data["val_idx"].tolist())
    if contexts.shape != (27, 2, 207) or not np.all(contexts[:, 0, 3] == 1) or not np.all(contexts[:, 1, 3] == 0):
        raise ValueError("expected fully known original and explicitly unknown remaining rows")
    sys.path.insert(0, str(HERE.parent))
    import own_deck_model as D
    started = time.monotonic()
    weights, metadata = D.load_extended(spec["base"]["path"], spec["supplement"]["path"])
    model = D.NumpyOwnDeckTx(weights, metadata)
    # Same synthetic declaration-only observation used for the saved composition fit.
    vectors = model.encode(np.zeros((27, 73), np.float32), np.zeros((27, 24), np.int64),
                           np.zeros((27, 24, 21), np.float32), np.zeros((27, 24), np.float32), own_deck=contexts)
    vectors = np.asarray(vectors, np.float32)
    if vectors.shape != (27, 96) or not np.isfinite(vectors).all():
        raise ValueError("nonfinite or wrong-shaped actual encoder export")
    if any(sha(p) != value for p, value in protected.items()):
        raise ValueError("protected checkpoint changed during export")
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    units = np.divide(vectors, norms[:, None], out=np.zeros_like(vectors), where=norms[:, None] > 1e-12)
    source = read(spec["source_decks"]["path"])
    import real_deck_data as R
    catalog_pin = next(p for p in spec["manifest"]["sources"] if p["path"].endswith("/compiler/generated/cards.json"))
    if sha(catalog_pin["path"]) != catalog_pin["sha256"]:
        raise ValueError("canonical/reprint catalog changed")
    printed, _ = R.printed_catalog(read(catalog_pin["path"]))
    aliases, _ = R.catalog_index(printed)
    rows = []
    declarations = spec["manifest"]["declarations"]
    for i, declaration in enumerate(declarations):
        source_index = declaration["source_index"]
        deck = source[source_index]
        counts = {}
        canonical, printings = {}, {}
        for entry in deck["deck"]:
            counts[entry["id"]] = counts.get(entry["id"], 0) + entry["count"]
            canonical_id = aliases[R.O.normalized_code(entry["id"])]
            canonical[canonical_id] = canonical.get(canonical_id, 0) + entry["count"]
            printings.setdefault(canonical_id, set()).add(entry["id"])
        if R.fingerprint(canonical) != fingerprints[i]:
            raise ValueError("canonical counts differ from pinned dataset fingerprint")
        rows.append(dict(id=f"deck-source-{source_index:02}", name=names[i], source_index=source_index, composition_fingerprint=fingerprints[i],
                         family_id=families[i], split="train" if i in train else "validation", leader=deck["leader"], base=deck["base"],
                         cards=[dict(id=code, count=count) for code, count in sorted(canonical.items())], canonical_card_counts=dict(sorted(canonical.items())),
                         raw_declared_cards=[dict(id=code, count=count) for code, count in sorted(counts.items())],
                         printed_ids_by_canonical={k: sorted(v) for k, v in sorted(printings.items())}, total_count=sum(canonical.values()),
                         original_known=True, remaining_known=False, vector=vectors[i].tolist(), unit_vector=units[i].tolist(),
                         l2_norm=float(norms[i]), cosine_available=bool(norms[i] > 1e-12)))
    data = dict(schema="jepa-deck-embedding-export/1", space_id="original-deck-composition-z96", entity_type="deck", dimension=96,
                semantic_validated=False, vector_origin="Actual NumPy encoder z from frozen baseline + saved original-composition-trained supplement",
                observation="Synthetic zero73state,24maskedzero live-card slots; unchanged original2x207features; no action query or gameplay observation",
                card_ids_are="Declared main-list IDs and counts are UI/provenance only; actual encoding uses the pinned canonical/reprint contract.", rows=rows)
    write(out / "deck-embeddings.json", data)
    manifest = dict(schema="jepa-deck-embedding-manifest/1", created_at_utc=timestamp(), semantic_validated=False,
                    artifact=dict(path=str(out / "deck-embeddings.json"), sha256=sha(out / "deck-embeddings.json")),
                    base=spec["base"], supplement=spec["supplement"], training_commit=spec["training_commit"], training_run_id=spec["training_run_id"],
                    supplement_optimizer_updates_before_export=100, optimizer_updates_during_export=0, native_calls=0, paid_jobs=0,
                    encoder_schema="swu-jepa-tx-own-deck/1; own-deck-input/v1 2x207; z96", encoder_sources=[dict(path=str(p), sha256=sha(p)) for p in
                        (HERE.parent / "own_deck_model.py", HERE.parent / "own_deck.py", HERE.parent / "tx_model.py", Path(__file__))],
                    input_dataset=spec["dataset"], input_manifest=spec["dataset_manifest"], source_decks=spec["source_decks"],
                    canonical_identity=dict(source="real_deck_data.printed_catalog/catalog_index + own_deck alias contract, identical to source dataset", catalog=catalog_pin,
                                            source_sha256=sha(HERE / "real_deck_data.py"), fingerprint_checked_for_every_row=True, preserved_raw_printings=True),
                    split=dict(train_rows=22, validation_rows=5, train_families=7, validation_families=4, rule=spec["manifest"]["split"]["rule"], no_resplit=True),
                    model_forward_calls=1, model_forward_rows=27, elapsed_seconds=time.monotonic() - started,
                    process_peak_rss_mib=peak_rss_mib(), rss_scope="Own single export process rusage peak; no child processes or tree-RSS trace.",
                    normalization=dict(raw="unaltered encoder output", unit="raw / L2norm when norm>1e-12; zero-norm cosine unavailable", fitted=False),
                    limitations=["Composition-readout training does not establish behavioral or strategic similarity, synergy, deck quality or playing strength.",
                                 "The base is frozen; only the original-deck supplement and a separate readout head were trained on declaration statistics. The readout head is not used here.",
                                 "This is a fixed synthetic declaration foil; distances can change under a different public observation.",
                                 "Five held-out decks share card identities with training decks; no unseen-card or current-format legality claim.",
                                 "Current remaining composition and hidden draw order are not represented by this export."])
    write(out / "deck-embeddings.manifest.json", manifest)
    index_path = out / "index.json"
    index = read(index_path) if index_path.exists() else pending_index(out, spec)
    index["updated_at_utc"], index["status"] = timestamp(), "deck-available-card-pending"
    index["metrics"] = pending_index(out, spec)["metrics"]
    index["spaces"]["deck"].update(status="available", vector_kind="actual neural encoder z", artifact_sha256=sha(out / "deck-embeddings.json"),
                                   manifest_sha256=sha(out / "deck-embeddings.manifest.json"))
    write(index_path, index)
    return manifest


def export_cards(out, run_path):
    """One actual program-bank encode from the completed correct-IR checkpoint."""
    out, run_path = Path(out), Path(run_path)
    started = time.monotonic()
    result_path = run_path / "result.json"
    result = read(result_path)
    if result.get("status") != "completed" or result.get("updates_completed") != 600:
        raise ValueError("the bounded three-arm structured fit has not completed")
    arm = next(r for r in result["arms"] if r["arm"] == "correct-ir")
    if arm["updates"] != 200 or sha(arm["checkpoint"]) != arm["checkpoint_sha256"]:
        raise ValueError("correct-IR checkpoint changed")
    contract_path = Path(arm["reference"]["contract"])
    if sha(contract_path) != arm["reference"]["contract_sha256"]:
        raise ValueError("structured checkpoint contract changed")
    contract = read(contract_path)
    if sha(HERE / "train_structured_transition.py") != contract["provenance"]["model_source_sha256"] or sha(HERE / "typed_ir_alignment.py") != contract["provenance"]["adapter_source_sha256"]:
        raise ValueError("structured encoder source differs from the trained checkpoint contract")
    data_manifest_path = ROOT / "experiments/supported-transition/supported-transitions.manifest.json"
    data_manifest = read(data_manifest_path)
    if sha(data_manifest_path) != contract["provenance"]["dataset_manifest_sha256"]:
        raise ValueError("structured data provenance changed")
    sys.path.insert(0, str(HERE))
    import train_structured_transition as S
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    codes, banks, _ = S.make_banks(data_manifest["programs"])
    if codes != ["ASH_011", "IBH_053"]:
        raise ValueError("only the two trained reviewed programs may be exported")
    model = S.make_model(torch, len(data_manifest["context_feature_names"]))
    with np.load(arm["checkpoint"], allow_pickle=False) as pack:
        weights = {name: torch.as_tensor(pack[name].copy()) for name in pack.files}
    model.load_state_dict(weights, strict=True)
    model.eval()
    with torch.no_grad():
        encoded = model.encode_program_bank(S.torch_bank(torch, banks["correct-ir"]))
        vectors = encoded[:len(codes)].numpy().copy()
    if vectors.shape != (2, 16) or not np.isfinite(vectors).all():
        raise ValueError("nonfinite or wrong-shaped learned program vectors")
    if sha(arm["checkpoint"]) != arm["checkpoint_sha256"]:
        raise ValueError("structured checkpoint changed during export")
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    units = np.divide(vectors, norms[:, None], out=np.zeros_like(vectors), where=norms[:, None] > 1e-12)
    catalog_path = next(p["path"] for p in data_manifest["sources"] if p["path"].endswith("/cards.json"))
    catalog = read(catalog_path)
    rows = []
    for i, code in enumerate(codes):
        card = next(r for r in catalog["cards"] if r["setCode"] == code)
        program = data_manifest["programs"][code]
        rows.append(dict(id=code, name=card["card"]["title"], subtitle=card["card"].get("subtitle"), canonical_card_id=program["canonical_card_id"],
                         declared_program_copies=1, count_scope="One selected source capability, not a deck count", ability_path=program["ability_path"],
                         split="both-train-and-validation-contexts", seen_in_training=True, seen_in_validation=True, held_out_identity=False,
                         training_context_families=[0, 1, 2, 3, 4], validation_context_families=[5, 6, 7],
                         sourceHash=program["sourceHash"], sourcePath=program["sourcePath"], vector=vectors[i].tolist(), unit_vector=units[i].tolist(),
                         l2_norm=float(norms[i]), cosine_available=bool(norms[i] > 1e-12)))
    artifact = out / "card-embeddings.json"
    write(artifact, dict(schema="jepa-card-program-embedding-export/1", space_id="supported-typed-card-program-z16", entity_type="card", dimension=16,
                         semantic_validated=False, vector_origin="Actual encode_program_bank output from saved correct-IR native-transition-trained weights",
                         context_conditioning="Program encoder output before context_projection/head; context-family supervision occurred during training, but no current context is encoded into these vectors.",
                         rows=rows))
    manifest = dict(schema="jepa-card-program-embedding-manifest/1", created_at_utc=timestamp(), semantic_validated=False,
                    artifact=dict(path=str(artifact), sha256=sha(artifact)), checkpoint=dict(path=arm["checkpoint"], sha256=arm["checkpoint_sha256"]),
                    raw_fit_result=dict(path=str(result_path), sha256=sha(result_path)), encoder_contract=dict(path=str(contract_path), sha256=sha(contract_path)),
                    dataset_manifest=dict(path=str(data_manifest_path), sha256=sha(data_manifest_path)), encoder_schema=S.SCHEMA, vocab_sha256=contract["vocab_sha256"],
                    program_order=codes, source_revision=contract["provenance"]["source_revision"],
                    encoder_sources=[dict(path=str(p), sha256=sha(p)) for p in (HERE / "train_structured_transition.py", HERE / "typed_ir_alignment.py", Path(__file__))],
                    checkpoint_updates_before_export=200, optimizer_updates_during_export=0, model_forward_calls=1, model_forward_programs=2,
                    operation="TypedTransition.encode_program_bank once; no forward_transition, native action, held-out metric or ranking evaluation.",
                    elapsed_seconds=time.monotonic() - started, process_peak_rss_mib=peak_rss_mib(), native_calls=0, paid_jobs=0,
                    normalization=dict(raw="unaltered16d learned program output", unit="raw/L2norm when norm>1e-12; zero-norm cosine unavailable", fitted=False),
                    limitations=["Only two trained card IDs; both occur in training and validation contexts, with no held-out identity evidence.",
                                 "Correct IR did not establish an advantage over the matched controls; vector proximity has no validated behavioral or neighbor-quality interpretation.",
                                 "One pair cannot support a useful nearest-neighbor quality or metric-generalization claim.",
                                 "Selected undeployed leader abilities only, not full-card, multi-effect sequence, deck synergy or production model representations.",
                                 "These16d program vectors form a separate space from96d deck latents and must never be compared directly."])
    write(out / "card-embeddings.manifest.json", manifest)
    index = read(out / "index.json")
    index["updated_at_utc"] = timestamp()
    index["status"] = "available" if index["spaces"]["deck"]["status"] == "available" else "card-available-deck-pending"
    index["spaces"]["card"].update(id="supported-typed-card-program-z16", status="available", entity_count=2, dimension=16,
                                   vector_kind="actual learned typed-program encoder output", artifact_sha256=sha(artifact),
                                   manifest_sha256=sha(out / "card-embeddings.manifest.json"), checkpoint=manifest["checkpoint"],
                                   limitation="Two identities seen during native-transition training; no validated neighbor-quality, unseen-ID or strength claim.")
    write(out / "index.json", index)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--export-decks", action="store_true", help="One actual label-free batch forward; requires root GO after priority fit.")
    parser.add_argument("--export-cards", action="store_true", help="One actual learned program-bank encode; requires root GO after priority fit.")
    parser.add_argument("--structured-run", type=Path, default=ROOT / "experiments/supported-transition/fit-2")
    args = parser.parse_args()
    if not args.export_decks and not args.export_cards:
        inventory(args.out_dir)
        print(json.dumps(dict(status="pending-inventory-only", index=str(args.out_dir / "index.json"), sha256=sha(args.out_dir / "index.json"), model_forward_calls=0)))
        return
    started = time.monotonic()
    exports = []
    if args.export_decks:
        exports.append(export_decks(args.out_dir))
    if args.export_cards:
        exports.append(export_cards(args.out_dir, args.structured_run))
    receipt = dict(schema="jepa-dashboard-embedding-export-run/1", status="completed", created_at_utc=timestamp(),
                   scope="Authorized label-free dashboard extraction after completed priority fit; distinct from training, held-out validation and prior ABI forwards.",
                   model_forward_calls=len(exports), deck_rows=27 if args.export_decks else 0, card_programs=2 if args.export_cards else 0,
                   optimizer_updates=0, native_calls=0, paid_jobs=0, elapsed_seconds=time.monotonic() - started, process_peak_rss_mib=peak_rss_mib(),
                   exports=[m["artifact"] for m in exports], index_sha256=sha(args.out_dir / "index.json"), script_sha256=sha(__file__))
    write(args.out_dir / "export-run.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
