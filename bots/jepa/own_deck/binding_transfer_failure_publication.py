"""Failure-only archive and additive publication preparation; no scientific execution.

Preview reads bytes only. --build writes a NEW external evidence directory.
--candidate attaches independently obtained CI/merge metadata in a NEW directory.
--promote archives the old pointer bytes, then uses the existing atomic core
publisher. Nothing rebuilds the preceding portable archive or embedding index.
Archive availability on this filesystem is not remote/Sites availability.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

import public_input_binding_export as E
import publication_checkpoint as P

SCHEMA = "jepa-binding-transfer-failed-evidence/1"
MANIFEST = "jepa-binding-transfer-failed-manifest/1"
STATUS = "closed-failed-before-first-native-apply"
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")
REQUIRED_CAMPAIGN_FILES = (
    "campaign-config.json", "campaign-ledger.jsonl", "native-plan.json", "native-plan-v2.json", "native-plan-v3.json",
    "native-preparation-receipt.json", "native-preparation-receipt-v2.json", "postmortem-closure-audit.json",
    "native-build-1/supervisor-receipt.json", "native-build-1/stdout.log", "native-build-1/stderr.log",
    "native-attempt-1/supervisor-receipt.json", "native-attempt-1/stdout.log", "native-attempt-1/stderr.log",
    "native-attempt-1/native-transitions.jsonl",
)
REQUIRED_SNAPSHOTS = ("prelaunch-24-root-v1", "prelaunch-26-root-6-source-v2", "prelaunch-guard-v1")
SCIENCE = dict(native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0)
MAX_UNIQUE_RAW_BYTES = 512 * 1024 ** 2


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return E.read_json(path)


def pin(path):
    return E.file_pin(path)


def checked(expected):
    actual = pin(expected["path"])
    require(actual == {k: expected[k] for k in ("path", "sha256", "bytes")}, "changed source pin: " + expected["path"])
    return Path(actual["path"]).read_bytes()


def ledger_failure(campaign):
    """Validate this closed failure, not a planned successful result or a quota reset."""
    campaign = Path(campaign)
    rows = [json.loads(line) for line in (campaign / "campaign-ledger.jsonl").read_text().splitlines() if line.strip()]
    previous = "0" * 64
    for number, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        require(row.get("sequence") == number and row.get("previous_sha256") == previous
                and row.get("record_sha256") == hashlib.sha256(canonical).hexdigest(), "ledger hash chain differs")
        previous = row["record_sha256"]
    require([(r["event"], r.get("data", {}).get("stage")) for r in rows] == [
        ("initialized", None), ("stage-start", "build"), ("stage-finish", "build"),
        ("stage-start", "native"), ("stage-finish", "native")], "only the closed build/native failure is admitted")
    build, failure = rows[2]["data"], rows[4]["data"]
    require(build["status"] == "completed" and failure["status"] == "failed", "actual build success/native failure required")
    for result in (build, failure):
        require(result.get("cleanup_verified") is True and result.get("execution_ended") is True
                and result.get("observed_verified") is True, "closed verified cleanup/counters required")
        require(set(result["observed"]) == set(COUNTERS) and all(v == 0 for v in result["observed"].values()), "new observed scientific exposure must be zero")
    require(failure["charged"]["native_applies"] == 48 and failure["charged"]["seconds"] == 30,
            "full failed native reservation must remain charged")
    require(build["charged"]["native_applies"] == 0, "build is not an engine application")
    journal = [json.loads(line) for line in (campaign / "native-attempt-1/native-transitions.jsonl").read_text().splitlines() if line.strip()]
    require(len(journal) == 1 and journal[0].get("schema") == "jepa-binding-transfer-apply-journal/1"
            and journal[0].get("maxApplyCalls") == 48, "header-only native journal required; no completed roots or apply calls")
    require((campaign / "native-attempt-1/stderr.log").read_text().strip()
            == "collector: registrationOrder conflicts with physical attachment chronology", "actual startup failure text differs")
    for name in ("prep", "fit", "baselines", "verify"):
        require(not any(campaign.glob(name + "-*")), "unstarted scientific stage has outputs: " + name)
    config = read(campaign / "campaign-config.json")
    charged_seconds = build["charged"]["seconds"] + failure["charged"]["seconds"]
    parent = config["parent"]
    return dict(schema="jepa-binding-transfer-failure-summary/1", status=STATUS, semantic_validated=False,
        learned_results=None, dataset_available=False, completed_roots=0, planned_roots=26,
        new_observed=copy.deepcopy(SCIENCE), new_charged=dict(native_applies=48, seconds=charged_seconds),
        cumulative_charged_native_applies=parent["charged_native_applies"] + 48,
        cumulative_charged_seconds=parent["charged_seconds"] + charged_seconds,
        cumulative_observed_native_applies=parent["observed_native_applies"],
        unstarted_stages=["prep", "fit", "baselines", "verify"], final_ledger_record_sha256=previous,
        failure="registrationOrder conflicts with physical attachment chronology",
        no_retry_or_credit=True, new_embedding_spaces=0,
        historical_scope="Carried binding-study reservation totals only; unknown prior observed calls remain unknown.")


def capture(campaign, report, blocker, patch, previous_pointer):
    campaign = Path(campaign).resolve(strict=True)
    for name in REQUIRED_CAMPAIGN_FILES:
        require((campaign / name).is_file(), "missing frozen failure evidence: " + name)
    for name in REQUIRED_SNAPSHOTS:
        require((campaign / name / "snapshot.json").is_file(), "missing preserved prelaunch version: " + name)
    summary = ledger_failure(campaign)
    previous_pointer = Path(previous_pointer).resolve(strict=True)
    prior = P.verify_pointer(previous_pointer)
    old_index = read(prior["artifacts"]["research_index"]["path"])
    old_embedding = read(old_index["artifacts"]["embedding_index"]["path"])
    require(len(old_index["artifacts"]) == 54 and len(old_embedding["spaces"]) == 18,
            "exact previous54 artifacts and18 embedding spaces required")
    sources = {}

    def add(path, declared=None, role="source"):
        path = Path(path)
        require(not path.is_symlink(), "symlink evidence is forbidden")
        actual = pin(path)
        if declared is not None:
            require(actual["sha256"] == declared["sha256"] and ("bytes" not in declared or actual["bytes"] == declared["bytes"]),
                    "frozen evidence source changed: " + str(path))
        key = actual["path"]
        if key in sources:
            require(sources[key]["pin"] == actual, "source changed while collecting")
            return
        sources[key] = dict(pin=actual, role=role)

    for path in sorted(campaign.rglob("*")):
        require(not path.is_symlink(), "campaign symlink is forbidden")
        if path.is_file():
            add(path)
    roots = [campaign / "campaign-config.json", campaign / "postmortem-closure-audit.json",
             campaign / "native-build-1/supervisor-receipt.json", campaign / "native-attempt-1/supervisor-receipt.json"]
    # Exact explicit pins in these frozen roots are copied. Their JSON payloads
    # remain opaque: this does not traverse/rebuild the old54/18 portable bundle.
    for root in roots:
        for record in E.direct_config_pins(read(root)):
            expected = record["declared_pin"]
            path = Path(expected["path"])
            add(path if path.is_absolute() else root.parent / path, expected)
    for path in (report, blocker, patch, __file__, E.__file__, P.__file__, previous_pointer):
        add(path)
    here = Path(__file__).resolve().parent
    for path in (here / "test_binding_transfer_failure_publication.py", here / "TRANSFER_ATTRIBUTION_DESIGN_REVIEW.md",
                 here / "binding_transfer_native_collector/README.md"):
        add(path)
    for expected in (prior["manifest"], *prior["artifacts"].values(), old_index["artifacts"]["embedding_index"]):
        add(expected["path"], expected)
    captured = []
    for n, item in enumerate(sorted(sources.values(), key=lambda v: v["pin"]["path"])):
        p = item["pin"]
        captured.append(dict(pin=p, entry=dict(id="evidence-" + str(n).zfill(4), role=item["role"],
            path=p["path"], provenance={})))
    source_by_path = {v["pin"]["path"]: v["pin"] for v in captured}
    return dict(campaign=campaign, summary=summary, captured=captured,
        previous_pointer=pin(previous_pointer), previous_index=prior["artifacts"]["research_index"],
        previous_handoff=prior["artifacts"]["handoff"], old_index=old_index,
        old_embedding_pin=old_index["artifacts"]["embedding_index"],
        report=source_by_path[str(Path(report).resolve())], blocker=source_by_path[str(Path(blocker).resolve())],
        patch=source_by_path[str(Path(patch).resolve())])


def preview(captured, out):
    out = Path(out).resolve()
    require(not out.exists() and not out.is_relative_to(captured["campaign"]), "NEW output outside frozen campaign required")
    unique = {v["pin"]["sha256"]: v["pin"] for v in captured["captured"]}
    return dict(status="preview-only-no-writes", output=str(out), sources=len(captured["captured"]),
        unique_raw_payloads=len(unique), raw_bytes=sum(p["bytes"] for p in unique.values()),
        large_files=[p for p in unique.values() if p["bytes"] >= 100_000_000],
        summary=captured["summary"], old_artifacts=54, embedding_spaces_unchanged=18,
        scope="Local external archive only; no remote assets, old portable rebuild, pointer change or science.")


def prepare_registry(old_index, summary, additions):
    require(len(old_index["artifacts"]) == 54, "previous54 exact records required")
    result = copy.deepcopy(old_index)
    require(not (set(additions) & set(result["artifacts"])), "additive records cannot replace old artifacts")
    result["artifacts"].update(copy.deepcopy(additions))
    result["previous_publication"] = copy.deepcopy(old_index.get("publication", {}))
    result["publication"] = dict(status="pending-new-checked-head-ci-and-merge")
    result["status"] = STATUS
    result["current_report_artifact_id"] = "binding_transfer_failure_report"
    result["binding_transfer_failure"] = copy.deepcopy(summary)
    result["counts_note"] = "Existing counts retain their preceding-cycle scope. New failed-campaign observations and charges are in binding_transfer_failure."
    result["semantic_validated"] = False
    result["current_limits"] = ["No new native dataset or learned-transfer result exists.",
        "The new48-call failure reservation remains charged; cumulative160 ceiling is exhausted.",
        "Archive is local external evidence; no new vector space, remote asset or Sites deployment is implied."]
    return result


def write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    P._write_exclusive(path, raw)


def build(captured, out):
    plan = preview(captured, out)
    out = Path(plan["output"])
    require(plan["raw_bytes"] <= MAX_UNIQUE_RAW_BYTES, "unique archive inputs exceed the512MiB preparation bound")
    raw_by_hash = {}
    loaded = []
    for item in captured["captured"]:
        sha = item["pin"]["sha256"]
        if sha not in raw_by_hash:
            raw_by_hash[sha] = checked(item["pin"])
        loaded.append(dict(**item, raw=raw_by_hash[sha]))
    payloads, logical = E.store_plan(loaded, E.DEFAULT_GZIP_THRESHOLD)
    out.mkdir(parents=True, exist_ok=False)
    for url, item in payloads.items():
        write(out / url, item["stored"])
    archive = dict(schema=SCHEMA, status=STATUS, artifacts=logical, semantic_validated=False,
        results=captured["summary"], scope="Byte-preserved failure evidence only. Source paths are provenance, not fetch URLs.")
    write(out / "evidence-index.json", P.encoded(archive))
    write(out / "failure-summary.json", P.encoded(captured["summary"]))
    write(out / "previous-publication-pointer.json", checked(captured["previous_pointer"]))
    for key, name in (("report", "report.md"), ("blocker", "fixture-postmortem.md"), ("patch", "unapplied-fixture-repair.patch")):
        write(out / name, checked(captured[key]))
    additions = {"binding_transfer_failure_" + key: pin(out / name) for key, name in (
        ("report", "report.md"), ("postmortem", "fixture-postmortem.md"), ("patch", "unapplied-fixture-repair.patch"),
        ("evidence", "evidence-index.json"), ("summary", "failure-summary.json"))}
    index = prepare_registry(captured["old_index"], captured["summary"], additions)
    index.setdefault("provenance", {})["binding_transfer_failure_parent"] = dict(
        previous_index=captured["previous_index"], previous_handoff=captured["previous_handoff"],
        previous_pointer=captured["previous_pointer"], previous_pointer_archive=pin(out / "previous-publication-pointer.json"),
        preceding54_artifact_records_unchanged=True, preceding18_space_index_unchanged=True)
    write(out / "research-index.json", P.encoded(index))
    handoff = dict(schema=P.HANDOFF_SCHEMA, status=STATUS, cycle="binding-transfer-v1-failed",
        research_index=pin(out / "research-index.json"), artifacts=copy.deepcopy(index["artifacts"]),
        artifact_count=len(index["artifacts"]), embedding_index=captured["old_embedding_pin"], registered_embedding_spaces=18,
        binding_transfer_failure=captured["summary"], semantic_validated=False, learned_results=None,
        current_report_artifact_id="binding_transfer_failure_report", new_neural_forwards=0, new_optimizer_updates=0,
        new_fits=0, new_observed_native_applies=0, new_charged_native_applies=48,
        publication=dict(status="pending-new-checked-head-ci-and-merge"),
        portable_scope="NEW failure evidence closure only; preceding54 artifact records remain pinned in place. The old portable ZIP may be copied byte-exact as an explicit frozen input, never rebuilt. No remote upload.")
    write(out / "handoff.json", P.encoded(handoff))
    for item in captured["captured"]:
        checked(item["pin"])
    files = [dict(url=p.relative_to(out).as_posix(), sha256=pin(p)["sha256"], bytes=p.stat().st_size)
             for p in sorted(out.rglob("*")) if p.is_file()]
    manifest = dict(schema=MANIFEST, status=STATUS, files=files,
        original_pins=[v["pin"] for v in captured["captured"]], previous_pointer=captured["previous_pointer"],
        previous_index=captured["previous_index"], previous_handoff=captured["previous_handoff"],
        previous_embedding_index=captured["old_embedding_pin"], new_artifact_ids=sorted(additions),
        science_performed_by_packager=SCIENCE, remote_assets_uploaded=False, old_portable_archive_rebuilt=False)
    write(out / "manifest.json", P.encoded(manifest))
    return verify(out, check_originals=True)


def verify(out, check_originals=False):
    out = Path(out).resolve(strict=True)
    manifest = read(out / "manifest.json")
    require(manifest["schema"] == MANIFEST and manifest["status"] == STATUS, "failure archive manifest required")
    listed = set()
    for item in manifest["files"]:
        require(item["url"] not in listed, "duplicate archive file")
        listed.add(item["url"])
        path = E.safe_path(out, item["url"])
        require(pin(path)["sha256"] == item["sha256"] and path.stat().st_size == item["bytes"], "archive file changed")
    actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    require(actual == listed | {"manifest.json"}, "missing or unexpected archive file")
    require(all(not p.is_symlink() for p in out.rglob("*")), "archive symlink forbidden")
    archive = read(out / "evidence-index.json")
    require(archive["schema"] == SCHEMA and archive["status"] == STATUS, "failure archive schema/status differs")
    archived = {}
    decoded = {}  # Hash/size metadata only; do not retain the old ZIP/raw bank in RAM.
    for record in archive["artifacts"]:
        require(record["encoding"] in ("gzip", "identity"), "unknown archive encoding")
        if record["url"] not in decoded:
            stored = E.safe_path(out, record["url"]).read_bytes()
            raw = gzip.decompress(stored) if record["encoding"] == "gzip" else stored
            decoded[record["url"]] = (E.digest(stored), len(stored), E.digest(raw), len(raw), record["encoding"])
            del stored, raw
        stored_sha, stored_bytes, raw_sha, raw_bytes, encoding = decoded[record["url"]]
        require(stored_sha == record["sha256"] and stored_bytes == record["bytes"]
                and raw_sha == record["raw_sha256"] and raw_bytes == record["raw_bytes"]
                and encoding == record["encoding"], "archived raw bytes differ")
        archived[(record["provenance"]["original_path"], record["raw_sha256"], record["raw_bytes"])] = record
    def archived_read(expected):
        key = (expected["path"], expected["sha256"], expected["bytes"])
        require(key in archived, "original pin missing from archive closure")
        record = archived[key]
        stored = E.safe_path(out, record["url"]).read_bytes()
        return gzip.decompress(stored) if record["encoding"] == "gzip" else stored
    for expected in manifest["original_pins"]:
        require((expected["path"], expected["sha256"], expected["bytes"]) in archived, "original pin missing from archive closure")
    if check_originals:
        for expected in manifest["original_pins"]:
            checked(expected)
    index, handoff = read(out / "research-index.json"), read(out / "handoff.json")
    old = json.loads(archived_read(manifest["previous_index"]))
    for key, value in old["artifacts"].items():
        require(index["artifacts"][key] == value, "previous artifact record changed")
    require(len(old["artifacts"]) == 54 and set(index["artifacts"]) == set(old["artifacts"]) | set(manifest["new_artifact_ids"]), "additive artifact IDs differ")
    require(index["artifacts"]["embedding_index"] == manifest["previous_embedding_index"]
            and len(json.loads(archived_read(manifest["previous_embedding_index"]))["spaces"]) == 18, "old18-space index changed")
    require((out / "previous-publication-pointer.json").read_bytes() == archived_read(manifest["previous_pointer"]),
            "archived previous pointer bytes differ")
    require(handoff["research_index"] == pin(out / "research-index.json") and handoff["status"] == STATUS
            and handoff["learned_results"] is None and index["binding_transfer_failure"] == read(out / "failure-summary.json")
            and handoff["artifacts"] == index["artifacts"] and handoff["artifact_count"] == len(index["artifacts"])
            and handoff["embedding_index"] == manifest["previous_embedding_index"] and handoff["registered_embedding_spaces"] == 18
            and handoff["binding_transfer_failure"] == index["binding_transfer_failure"], "failure handoff differs")
    return dict(status="verified-closed-failure-archive", archive=str(out), index=pin(out / "research-index.json"),
        handoff=pin(out / "handoff.json"), manifest=pin(out / "manifest.json"), artifact_count=len(index["artifacts"]),
        embedding_spaces=18, remote_assets_uploaded=False, scientific_exposure=SCIENCE)


def attested_pair(out, destination, publication, attestation_pin):
    """The only permitted changes from prepared science are publication metadata."""
    index, handoff = read(out / "research-index.json"), read(out / "handoff.json")
    index["publication"] = copy.deepcopy(publication)
    handoff["publication"] = copy.deepcopy(publication)
    for key in ("head_commit", "tree", "ci_run_id", "ci_conclusion", "merge_commit", "merged_tree_matches_checked_head"):
        handoff[key] = publication.get(key)
    handoff["merged_tree"] = publication.get("tree")
    P.publication_metadata(index, handoff)
    handoff["research_index"] = P.pinned(destination / "research-index.json", P.encoded(index))
    handoff["publication_attestation"] = attestation_pin
    return index, handoff


def candidate(out, destination, attestation):
    verify(out)
    out, destination = Path(out).resolve(strict=True), Path(destination).resolve()
    require(not destination.exists() and not destination.is_relative_to(out), "NEW candidate directory outside immutable archive required")
    publication = read(attestation)
    attestation_raw = Path(attestation).read_bytes()
    attestation_pin = P.pinned(destination / "publication-attestation.json", attestation_raw)
    index, handoff = attested_pair(out, destination, publication, attestation_pin)
    destination.mkdir(parents=True, exist_ok=False)
    write(destination / "publication-attestation.json", attestation_raw)
    write(destination / "research-index.json", P.encoded(index))
    write(destination / "handoff.json", P.encoded(handoff))
    return dict(status="candidate-prepared-not-promoted", index=pin(destination / "research-index.json"),
        handoff=pin(destination / "handoff.json"), original_archive=pin(out / "manifest.json"), publication=publication)


def promote(out, candidate_dir, publications_dir, stable_pointer):
    verify(out)
    out, candidate_dir = Path(out).resolve(strict=True), Path(candidate_dir).resolve(strict=True)
    manifest = read(out / "manifest.json")
    require(pin(stable_pointer) == manifest["previous_pointer"], "stable pointer advanced since failure archive; refuse stale promotion")
    require((out / "previous-publication-pointer.json").read_bytes() == Path(stable_pointer).read_bytes(), "old pointer bytes were not archived exactly")
    index, handoff = read(candidate_dir / "research-index.json"), read(candidate_dir / "handoff.json")
    attestation = pin(candidate_dir / "publication-attestation.json")
    wanted_index, wanted_handoff = attested_pair(out, candidate_dir, json.loads(checked(attestation)), attestation)
    require(index == wanted_index and handoff == wanted_handoff, "candidate changed science/registry/handoff beyond publication attestation")
    result = P.publish(candidate_dir / "research-index.json", candidate_dir / "handoff.json", publications_dir,
        stable_pointer, pin(candidate_dir / "research-index.json")["sha256"], pin(candidate_dir / "handoff.json")["sha256"])
    result.update(study_status=STATUS, previous_pointer_archive=pin(out / "previous-publication-pointer.json"),
        old_portable_rebuilt=False, embedding_spaces_unchanged=18, remote_assets_uploaded=False,
        postclosure_mutable_pointer_exception=dict(path=str(Path(stable_pointer).resolve()),
            old=manifest["previous_pointer"], archived=pin(out / "previous-publication-pointer.json"), new=pin(stable_pointer),
            closed_ledger_final_record_sha256=read(out / "failure-summary.json")["final_ledger_record_sha256"],
            scope="Only this explicitly promoted pointer changes after study closure; frozen config, ledger and preservation snapshots remain unchanged."))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    for name in ("build", "verify", "candidate", "promote"):
        modes.add_argument("--" + name, action="store_true")
    for name in ("campaign", "report", "blocker", "patch", "previous-pointer", "out", "candidate-out", "attestation", "publications-dir", "stable-pointer"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--check-originals", action="store_true")
    args = parser.parse_args()
    require(args.out is not None, "explicit external --out required; no default tracked large archive")
    if args.verify:
        result = verify(args.out, args.check_originals)
    elif args.candidate:
        require(args.candidate_out and args.attestation, "candidate destination and independently obtained attestation required")
        result = candidate(args.out, args.candidate_out, args.attestation)
    elif args.promote:
        require(args.candidate_out and args.publications_dir and args.stable_pointer, "explicit promotion paths required")
        result = promote(args.out, args.candidate_out, args.publications_dir, args.stable_pointer)
    else:
        require(all((args.campaign, args.report, args.blocker, args.patch, args.previous_pointer)), "all failure evidence inputs required")
        captured = capture(args.campaign, args.report, args.blocker, args.patch, args.previous_pointer)
        result = build(captured, args.out) if args.build else preview(captured, args.out)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
