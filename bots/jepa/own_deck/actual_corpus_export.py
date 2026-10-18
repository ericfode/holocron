"""Package frozen actual-corpus results and saved vectors; no model imports.

Protocol: prepare a spec only AFTER experiment source/results are frozen. Its
``artifacts`` map must pin coverage, coverage_verification, native_result,
card_result, deck_result, card_vectors and deck_vectors. Add ALL contracts,
checkpoints, predictions, controls, per-head results and receipts as further
roles. This module copies entire input files, including failures/unknown masks;
it never selects successful heads or executes a model. The current research or
embedding index is never opened for writing. An index fragment is review-only.
"""
import argparse
import copy
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

VERSION = "actual-corpus-v1"
PLAN_SCHEMA = "jepa-actual-corpus-export-plan/1"
EVIDENCE_SCHEMA = "jepa-actual-corpus-evidence/1"
REQUIRED = {"coverage", "coverage_verification", "native_result", "card_result", "deck_result", "card_vectors", "deck_vectors"}
EXPECTED = dict(cards=8, decks=27, total_main_copies=1432, supported_main_copies=65)
ZERO_COMPUTE = dict(neural_forwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw, parse_constant=invalid)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), sha256=digest(raw), bytes=len(raw))


def checked(record):
    if not isinstance(record, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256"))):
        raise ValueError("frozen SHA256 pin required")
    if type(record.get("bytes")) is not int or record["bytes"] < 1:
        raise ValueError("positive exact byte-count pin required")
    raw = Path(record["path"]).read_bytes()
    if digest(raw) != record["sha256"] or len(raw) != record["bytes"]:
        raise ValueError("frozen artifact changed: " + record["path"])
    return raw


def exclusive(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def deterministic_gzip(raw):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0, compresslevel=9) as archive:
        archive.write(raw)
    result = stream.getvalue()
    if gzip.decompress(result) != raw:
        raise ValueError("gzip roundtrip differs")
    return result


def vector(row, dimension):
    value = row.get("vector")
    if not isinstance(value, list) or len(value) != dimension or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError("finite saved vector with exact dimension required")
    norm = math.hypot(*value)
    if not math.isfinite(norm):
        raise ValueError("saved vector norm is not finite")
    unit = [x / norm for x in value] if norm else [0.] * dimension
    if "unit_vector" in row:
        supplied = row["unit_vector"]
        if not isinstance(supplied, list) or len(supplied) != dimension or any(type(x) not in (int, float) or not math.isfinite(x) for x in supplied):
            raise ValueError("invalid saved unit vector")
        if any(abs(a - b) > 1e-6 for a, b in zip(unit, supplied)):
            raise ValueError("saved unit vector disagrees with its raw vector")
        unit = supplied
    return dict(vector=copy.deepcopy(value), unit_vector=unit, l2_norm=norm, cosine_available=bool(norm))


def counts_for(deck):
    rows = deck["main_cards"]
    counts = {}
    for row in rows:
        code, copies = row["canonical_id"], row["copies"]
        if code in counts or type(copies) is not int or copies <= 0:
            raise ValueError("unique canonical main-card IDs and positive counts required")
        counts[code] = copies
    if sum(counts.values()) != deck["total_main_copies"]:
        raise ValueError("declared main-copy total differs")
    return counts


def browser_payloads(coverage, card_saved, deck_saved, version=VERSION):
    """Data-only adaptation; unsupported cards receive masks, never fake vectors."""
    proposed = coverage["summary"]["proposed_native_fixture"]
    codes = set(proposed["ids"])
    if len(codes) != EXPECTED["cards"] or proposed["copies"] != EXPECTED["supported_main_copies"]:
        raise ValueError("frozen eight-card/65-copy proposal differs")
    if card_saved.get("arm") != "correct-typed" or card_saved.get("dimensions", card_saved.get("dimension")) != 16:
        raise ValueError("saved correct-typed card16 bank required")
    saved_cards = card_saved.get("cards", card_saved.get("rows", []))
    by_code = {row.get("code", row.get("id")): row for row in saved_cards}
    if len(saved_cards) != len(by_code) or set(by_code) != codes:
        raise ValueError("saved card bank must be exactly the eight actual selected IDs")
    card_rows = []
    for code in sorted(codes):
        source = by_code[code]
        if source.get("semantic_validated") is not False or source.get("runtime_admitted") is not True or source.get("native_fixture_observed") is not True or type(source.get("training_card")) is not bool:
            raise ValueError("explicit native/training/semantic status required per card")
        row = copy.deepcopy(source)
        row.update(id=code, code=code, **vector(source, 16), whole_card_semantics_validated=False,
                   selected_native_fixture_observed=True, unknown_rest_of_corpus=True)
        card_rows.append(row)
    decks = coverage["decks"]
    source_decks = {row["source_index"]: row for row in decks}
    if len(source_decks) != EXPECTED["decks"] or set(source_decks) != set(range(27)):
        raise ValueError("exact original27 actual-deck declarations required")
    if deck_saved.get("arm") != "correct-typed" or deck_saved.get("dimension", deck_saved.get("dimensions")) != 32 or deck_saved.get("semantic_validated") is not False:
        raise ValueError("saved correct-typed deck32 bank required")
    saved_decks = deck_saved.get("rows", [])
    by_source = {row["source_index"]: row for row in saved_decks}
    if len(saved_decks) != len(by_source) or set(by_source) != set(source_decks):
        raise ValueError("saved deck bank must have every actual declaration exactly once")
    deck_rows, totals = [], dict(main_copies=0, known_copies=0, unknown_copies=0)
    for source_index, declaration in sorted(source_decks.items()):
        saved = by_source[source_index]
        counts = counts_for(declaration)
        if saved.get("canonical_card_counts") != counts or saved.get("total_count") != sum(counts.values()):
            raise ValueError("saved deck canonical counts differ from frozen declaration")
        if saved.get("family_id") != declaration["family_id"] or saved.get("split") != declaration["split"]:
            raise ValueError("original family/split changed")
        fingerprint = saved.get("composition_fingerprint", saved.get("fingerprint"))
        if fingerprint != declaration["composition_fingerprint"]:
            raise ValueError("saved composition fingerprint changed")
        order = sorted(counts)
        known = [code in codes for code in order]
        known_copies = sum(counts[code] for code in order if code in codes)
        unknown_copies = sum(counts.values()) - known_copies
        row = copy.deepcopy(saved)
        row.update(id="actual-deck-source-" + str(source_index).zfill(2), **vector(saved, 32),
                   canonical_card_counts=counts, leader=copy.deepcopy(declaration["leader"]), base=copy.deepcopy(declaration["base"]),
                   original_deck_known=True, remaining_known=False, whole_deck_semantics_known=False,
                   semantic_validated=False, card_order=order, known_card_mask=known, unknown_card_mask=[not x for x in known],
                   card_copy_counts=[counts[code] for code in order], known_copy_count=known_copies,
                   unknown_copy_count=unknown_copies, supported_copy_fraction=known_copies / sum(counts.values()),
                   unknown_policy="Missing whole-card vectors are unknown; no vanilla/fake vector is imputed. Saved deck latent includes its declared unknown handling.")
        deck_rows.append(row)
        totals["main_copies"] += sum(counts.values()); totals["known_copies"] += known_copies; totals["unknown_copies"] += unknown_copies
    if totals != dict(main_copies=1432, known_copies=65, unknown_copies=1367):
        raise ValueError("actual corpus copy coverage differs")
    common = dict(version=version, semantic_validated=False,
                  vector_origin="Only previously saved final-evaluation vectors; zero export forwards. Unit vectors use explicit deterministic L2 normalization only.",
                  compatible_distance_scope="Within this exact space_id only. Card16 and deck32 are different models/spaces; no cross-space comparison.",
                  limitations=["Eight main-card IDs cover65 of1432 declared copies; the other1367 copies are explicitly unknown.",
                               "Native observations sample chosen contexts; neither complete card semantics nor game conformance is certified.",
                               "The27 historical declarations and22/5 family split are unchanged; no deck quality, synergy, current legality or playing-strength claim."])
    card = dict(common, schema="jepa-card-embedding-export/1", space_id=version + "-whole-card-z16", entity_type="card", dimension=16, rows=card_rows)
    deck = dict(common, schema="jepa-deck-embedding-export/1", space_id=version + "-partial-corpus-deck-z32", entity_type="deck", dimension=32, rows=deck_rows,
                coverage=totals, coverage_source_status=coverage["status"])
    return card, deck


def prepare(spec):
    """Validate frozen pins, full vectors and coverage without writing outputs."""
    if spec.get("version", VERSION) != VERSION or not re.fullmatch(r"[0-9a-f]{40}", str(spec.get("source_commit"))):
        raise ValueError("version and frozen experiment source commit required")
    artifacts = spec["artifacts"]
    if not REQUIRED <= set(artifacts) or any(not re.fullmatch(r"[a-z][a-z0-9_-]*", role) for role in artifacts):
        raise ValueError("required artifact roles missing or unsafe")
    raw = {role: checked(record) for role, record in artifacts.items()}
    for role in ("card_result", "deck_result"):
        if read(raw[role]).get("status") not in ("completed", "verified", "success"):
            raise ValueError("completed/verified " + role + " required")
    coverage = read(raw["coverage"])
    verification = read(raw["coverage_verification"])
    if verification.get("artifact", {}).get("sha256") != artifacts["coverage"]["sha256"]:
        raise ValueError("coverage verification must pin this exact coverage artifact")
    if verification.get("status") not in ("completed", "verified", "success"):
        required_checks = ("all_27_deck_denominators_preserved", "all_251_identity_counts_preserved", "all_source_pins_match")
        if not all(verification.get(key) is True for key in required_checks):
            raise ValueError("verified original coverage denominators/source pins required")
    native = read(raw["native_result"])
    expected_ids = set(coverage["summary"]["proposed_native_fixture"]["ids"])
    collection_plan = native.get("collectionPlan", {})
    source_rows = collection_plan.get("cards", [])
    source_ids = [row.get("code") for row in source_rows]
    cases = native.get("cases", [])
    case_ids = {row.get("card", row.get("code")) for row in cases}
    selected = native.get("selectedWholeCards", [])
    planned_selected = collection_plan.get("selected_whole_cards", [])
    if (native.get("schema") != "jepa-actual-corpus-native/1" or len(source_ids) != 8 or set(source_ids) != expected_ids
            or len(cases) != 32 or case_ids != expected_ids or len(selected) != len(set(selected))
            or len(planned_selected) != len(set(planned_selected)) or set(selected) != set(planned_selected)
            or not expected_ids <= set(selected)):
        raise ValueError("frozen actual eight-card/32-context native receipt required")
    browser_payloads(coverage, read(raw["card_vectors"]), read(raw["deck_vectors"]))
    return dict(schema=PLAN_SCHEMA, status="frozen-export-inputs-verified", version=VERSION,
                source_commit=spec["source_commit"], artifacts=copy.deepcopy(artifacts), expected=copy.deepcopy(EXPECTED),
                source_code=pin(__file__), policy="Copy ALL supplied raw artifacts and full head/negative/unknown results. Never mutate existing indexes or publications.",
                counters=copy.deepcopy(ZERO_COMPUTE))


def package(plan, evidence_dir, vectors_dir, gzip_threshold=65536):
    """Install two new immutable directories; emit an unmerged index fragment."""
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "frozen-export-inputs-verified" or plan.get("expected") != EXPECTED:
        raise ValueError("validated frozen export plan required")
    checked(plan["source_code"])
    raw = {role: checked(record) for role, record in plan["artifacts"].items()}
    card, deck = browser_payloads(read(raw["coverage"]), read(raw["card_vectors"]), read(raw["deck_vectors"]))
    evidence_dir, vectors_dir = Path(evidence_dir).resolve(), Path(vectors_dir).resolve()
    if evidence_dir == vectors_dir or evidence_dir.is_relative_to(vectors_dir) or vectors_dir.is_relative_to(evidence_dir):
        raise ValueError("separate sibling/disjoint immutable outputs required")
    if evidence_dir.exists() or vectors_dir.exists():
        raise FileExistsError("preserve prior versioned outputs; never overwrite")
    for directory in (evidence_dir.parent, vectors_dir.parent):
        directory.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".actual-evidence-pending-", dir=evidence_dir.parent))
    browser_stage = Path(tempfile.mkdtemp(prefix=".actual-vectors-pending-", dir=vectors_dir.parent))
    files = []
    for role, value in sorted(raw.items()):
        original = Path(plan["artifacts"][role]["path"])
        compressed = len(value) >= gzip_threshold and original.suffix in (".json", ".jsonl")
        stored = deterministic_gzip(value) if compressed else value
        relative = role + original.suffix + (".gz" if compressed else "")
        exclusive(stage / relative, stored)
        files.append(dict(path=relative, role=role, source_kind="byte-copy", source_path=str(original),
                          source_sha256=digest(value), source_bytes=len(value), uncompressed_sha256=digest(value),
                          uncompressed_bytes=len(value), stored_sha256=digest(stored), stored_bytes=len(stored),
                          encoding="gzip;mtime=0;filename=empty" if compressed else "identity"))
    browser_pins, fragment = {}, {}
    for entity, value in (("card", card), ("deck", deck)):
        relative = entity + "-embeddings.json"; data = encoded(value)
        exclusive(browser_stage / relative, data)
        exclusive(stage / relative, data)
        browser_pins[entity] = dict(path=relative, sha256=digest(data), bytes=len(data), dimension=value["dimension"], rows=len(value["rows"]))
        files.append(dict(path=relative, role="browser_" + entity, source_kind="saved-vector-serialization", source_path=plan["artifacts"][entity + "_vectors"]["path"],
                          source_sha256=plan["artifacts"][entity + "_vectors"]["sha256"], source_bytes=len(raw[entity + "_vectors"]),
                          uncompressed_sha256=digest(data), uncompressed_bytes=len(data), stored_sha256=digest(data), stored_bytes=len(data), encoding="identity"))
        fragment["actual_corpus_" + entity] = dict(id=value["space_id"], entity_type=entity, version=VERSION, status="available", dimension=value["dimension"],
                       entity_count=len(value["rows"]), semantic_validated=False, relative_file=relative,
                       vectors_path=str(vectors_dir / relative), artifact_sha256=digest(data), manifest_path=str(vectors_dir / "manifest.json"),
                       limitation="Partial8-ID/65-copy native-grounded corpus;1367 of1432 copies unknown. No semantic-neighbor, deck-quality or strength validation.")
    evidence = dict(schema=EVIDENCE_SCHEMA, version=VERSION, status="packaged-raw-artifacts-preserved", source_commit=plan["source_commit"],
                    files=files, original_sources_modified=False, semantic_validated=False, sampled_corpus=dict(ids=8, known_copies=65, unknown_copies=1367, total_copies=1432),
                    source_plan=plan, counters=ZERO_COMPUTE, selection="Every supplied raw artifact is preserved in full; no per-head filtering or recomputation.")
    exclusive(stage / "index.json", encoded(evidence))
    browser_manifest = dict(schema="jepa-actual-corpus-browser-export/1", version=VERSION, source_commit=plan["source_commit"], semantic_validated=False,
                            artifacts=browser_pins, evidence_index=dict(path=str(evidence_dir / "index.json"), sha256=digest(encoded(evidence)), bytes=len(encoded(evidence))),
                            coverage=dict(total_main_copies=1432, known_main_copies=65, unknown_main_copies=1367), source_plan=plan, counters=ZERO_COMPUTE)
    manifest_raw = encoded(browser_manifest); exclusive(browser_stage / "manifest.json", manifest_raw)
    for value in fragment.values():
        value["manifest_sha256"] = digest(manifest_raw)
    exclusive(browser_stage / "index-fragment.json", encoded(dict(schema="jepa-embedding-index-fragment/1", status="review-only-not-merged", spaces=fragment, counters=ZERO_COMPUTE)))
    for role, record in plan["artifacts"].items():
        checked(record)
    checked(plan["source_code"])
    os.rename(stage, evidence_dir); os.rename(browser_stage, vectors_dir)
    return dict(schema="jepa-actual-corpus-export-receipt/1", status="completed", evidence_index=pin(evidence_dir / "index.json"),
                browser_manifest=pin(vectors_dir / "manifest.json"), index_fragment=pin(vectors_dir / "index-fragment.json"),
                raw_artifact_count=len(raw), vector_spaces=2, current_indexes_modified=False, original_sources_modified=False,
                semantic_validated=False, **ZERO_COMPUTE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Only after coordinator freezes the actual results/source")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--vectors-dir", type=Path)
    args = parser.parse_args()
    if args.execute:
        if args.evidence_dir is None or args.vectors_dir is None:
            parser.error("--execute requires both immutable output directories")
        print(json.dumps(package(read(args.plan.read_bytes()), args.evidence_dir, args.vectors_dir), indent=2))
    else:
        if args.spec is None:
            parser.error("preparation requires --spec")
        plan = prepare(read(args.spec.read_bytes()))
        exclusive(args.plan, encoded(plan))
        print(json.dumps(dict(status=plan["status"], plan=pin(args.plan), **ZERO_COMPUTE), indent=2))


if __name__ == "__main__":
    main()
