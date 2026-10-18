"""Byte-only portable packaging. No model, engine, array, or network imports.

Preview: --campaign independent-controls|transition-replication
Copy completed evidence: add --write (transition also requires --completed-transition).
Verify a package: --verify PATH. Existing packages are never overwritten.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXPERIMENTS = REPO.parent / "experiments"
ARMS = ("correct-ir", "id-only", "wrong-ir", "context-only")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def files_under(root):
    return sorted(p for p in root.rglob("*") if p.is_file())


def verified_pin_sources(value, found=None):
    found = {} if found is None else found
    if isinstance(value, dict):
        if "path" in value and "sha256" in value and str(value["path"]).endswith(".py"):
            path = Path(value["path"])
            if path.is_relative_to(REPO) and digest(path.read_bytes()) == value["sha256"]:
                found[path] = value["sha256"]
            elif path.is_relative_to(REPO):
                raise ValueError("Executed Python source no longer matches its pin: " + str(path))
        for item in value.values():
            verified_pin_sources(item, found)
    elif isinstance(value, list):
        for item in value:
            verified_pin_sources(item, found)
    return found


def ledger_summary(path):
    active = 0.0
    applies = updates = 0
    pending = None
    stages = []
    for row in (json.loads(line) for line in path.read_bytes().splitlines()):
        if row["event"] == "stage-start":
            if pending is not None:
                raise ValueError("Unfinished campaign stage")
            pending = row
        elif row["event"] == "stage-finish":
            if pending is None or row["stage_id"] != pending["stage_id"]:
                raise ValueError("Campaign stage mismatch")
            active += row["active_seconds"]
            applies += row["engine_apply_attempts"]
            updates += row["completed_or_reserved_updates"]
            stages.append(dict(stage=pending["stage"], status=row["status"]))
            pending = None
        else:
            raise ValueError("Unexpected campaign accounting event")
    if pending is not None or updates != 4800 or applies > 2048 or active > 240:
        raise ValueError("Campaign is incomplete or outside the frozen allocation")
    successful = [x["stage"] for x in stages if x["status"] == "completed"]
    if successful.count("collect") != 1 or successful.count("fit") != 2 or successful.count("evaluate") != 3:
        raise ValueError("Expected collection, two fits, and three evaluations")
    return dict(active_seconds=active, engine_applies=applies, charged_updates=updates, stages=stages)


def collection(campaign):
    root = EXPERIMENTS / campaign
    sources = [(p, str(p.relative_to(root))) for p in files_under(root)]
    references = []
    if campaign == "independent-controls":
        for name in ("embedding-run", "metrics-run"):
            if read(root / name / "receipt.json")["status"] != "completed":
                raise ValueError("Retrieval stage not complete: " + name)
        pins = {}
        for name in ("embedding-run/plan.json", "metrics-run/plan.json"):
            verified_pin_sources(read(root / name), pins)
        for name in ("independent_retrieval_controls.py", "independent_retrieval_module_controls.py", "export_independent_retrieval.py"):
            pins[HERE / name] = digest((HERE / name).read_bytes())
        sources.extend((p, "sources/" + str(p.relative_to(REPO))) for p in sorted(pins))
        versioned = EXPERIMENTS / "embedding-export/independent-controls-v1"
        if versioned.exists() and (versioned / "receipt.json").exists():
            if read(versioned / "receipt.json")["status"] != "completed":
                raise ValueError("Dashboard export is still changing")
            sources.extend((p, "dashboard-export/" + str(p.relative_to(versioned))) for p in files_under(versioned))
        summary = dict(source_commit="f94457da573ad67e8dd92bf50c9d372bd34045a5",
                       assays_separate=True, v1_failed_support_preserved=True)
    else:
        summary = ledger_summary(root / "campaign-ledger.jsonl")
        summary["source_commit"] = "ae64647143916fb2bba1bc014585fed659f3f76a"
        for name in ("fit-original-s29", "fit-original-s43", "eval-fresh-s17", "eval-fresh-s29", "eval-fresh-s43"):
            if read(root / name / "result.json")["status"] != "completed":
                raise ValueError("Replication output not final: " + name)
        collector = HERE / "transition_replication_collector"
        collector_manifest = read(collector / "source-manifest.json")
        for entry in collector_manifest["project_files"]:
            path = collector / entry["path"]
            if digest(path.read_bytes()) != entry["sha256"]:
                raise ValueError("Executed collector source changed: " + str(path))
            sources.append((path, "sources/collector/" + entry["path"]))
        sources.append((collector / "source-manifest.json", "sources/collector/source-manifest.json"))
        for name in ("transition_replication_plan.py", "transition_replication_fit.py", "test_transition_replication_fit.py",
                     "grounded_contrast_data.py", "grounded_contrast_model.py", "typed_ir_alignment.py"):
            sources.append((HERE / name, "sources/" + name))
        for name in ("LICENSE.Kessel", "LICENSE.forceteki", "LICENSE.TCGEngine"):
            p = HERE / "grounded-contrast-evidence/licenses" / name
            sources.append((p, "licenses/" + name))
        prior = HERE / "grounded-contrast-evidence"
        prior_index = read(prior / "index.json")
        needed = {"grounded-contrast.npz", "grounded-contrast.manifest.json.gz", "fit-1/result.json", "fit-1/contract.json"}
        needed.update("fit-1/" + arm + suffix for arm in ARMS for suffix in (".npz", "-contract.json"))
        for entry in prior_index["files"]:
            if entry["path"] in needed:
                reference = dict(entry)
                reference["path"] = "../grounded-contrast-evidence/" + entry["path"]
                references.append(reference)
        if len(references) != len(needed):
            raise ValueError("Missing prior seed17 or original training reference")
    paths = [rel for _, rel in sources]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate portable destination")
    for path, rel in sources:
        if path.is_symlink() or not path.is_file() or path.suffix == ".safetensors":
            raise ValueError("Disallowed evidence source: " + str(path))
        if "compiler/generated" in str(path) or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError("Source or destination outside the evidence scope")
    return sources, references, summary


def payload_entry(source, relative, data):
    compressed = len(data) >= 1_000_000 and Path(relative).suffix in (".json", ".jsonl")
    if compressed:
        buf = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=buf, mtime=0) as stream:
            stream.write(data)
        stored = buf.getvalue()
        relative += ".gz"
    else:
        stored = data
    entry = dict(path=relative, source_path=str(source) if source is not None else None,
                 source_kind="byte-copy" if source is not None else "authored-package-guide",
                 source_sha256=digest(data), source_bytes=len(data), uncompressed_sha256=digest(data),
                 uncompressed_bytes=len(data), stored_sha256=digest(stored), stored_bytes=len(stored),
                 encoding="gzip;mtime=0;filename=empty" if compressed else "identity")
    return entry, stored


def verify(directory):
    directory = Path(directory)
    index = read(directory / "index.json")
    expected = {entry["path"] for entry in index["files"]} | {"index.json"}
    if expected != {str(p.relative_to(directory)) for p in files_under(directory)}:
        raise ValueError("Portable file set differs from its index")
    for entry in index["files"] + index.get("prior_portable_references", []):
        stored = (directory / entry["path"]).read_bytes()
        if len(stored) != entry["stored_bytes"] or digest(stored) != entry["stored_sha256"]:
            raise ValueError("Stored payload mismatch: " + entry["path"])
        raw = gzip.decompress(stored) if entry["encoding"].startswith("gzip") else stored
        if len(raw) != entry["uncompressed_bytes"] or digest(raw) != entry["uncompressed_sha256"]:
            raise ValueError("Uncompressed payload mismatch: " + entry["path"])
        if digest(raw) != entry["source_sha256"]:
            raise ValueError("Source-byte identity mismatch: " + entry["path"])
    return dict(index_sha256=digest((directory / "index.json").read_bytes()),
                files_including_index=len(expected), stored_bytes_including_index=sum(p.stat().st_size for p in files_under(directory)),
                **index["totals"])


def package(campaign, write=False):
    sources, references, summary = collection(campaign)
    out = HERE / (campaign + "-evidence")
    if not write:
        return dict(status="preview-only", out=str(out), source_files=len(sources), summary=summary)
    if out.exists():
        raise ValueError("Refusing to overwrite existing evidence: " + str(out))
    snapshots = [(source, rel, source.read_bytes()) for source, rel in sources]
    entries = []
    out.mkdir()
    guide = ("# Portable " + campaign + " evidence\n\n"
             "index.json resolves exact original source paths, sizes, and source/uncompressed/stored SHA-256 digests. "
             "Large JSON uses deterministic gzip (empty filename, mtime0). Absolute paths in raw artifacts are historical provenance.\n\n"
             + ("The unsupported authored-deck v1 assay remains separate from module-v2 synthetic fixtures. "
                "Neither was relabeled from embedding outcomes. The actual saved vector/metric outputs and all preparation receipts remain unchanged. "
                "These are structural-proxy assays, not native behavior, strategic synergy, or playing strength.\n\n"
                if campaign == "independent-controls" else
                "The obsolete unexecuted12000-update proposal remains separate from the final4800-update plan. "
                "All collection, two original fits, three fresh reuse evaluations, exact training-equivalence proofs, source snapshots, predictions and journal records are preserved. "
                "Prior seed17 checkpoints and original data resolve by full hash through prior_portable_references into the committed grounded-contrast-evidence sibling. "
                "Candidate branches are correlated within168 native fixture roots; no policy, deck-synergy, or strength claim follows.\n\n")
             + "Protected original safetensor weights, full catalogues, donor annotations, global feed and unified export index are excluded. "
             "Existing license notices are retained. Packaging ran no neural forward, optimizer update, native apply, or paid job. "
             "Verify using package_research_cycle_evidence.py --verify PATH; this requires only Python's standard library.\n")
    for source, rel, data in snapshots + [(None, "README.md", guide.encode())]:
        entry, stored = payload_entry(source, rel, data)
        target = out / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(stored)
        entries.append(entry)
    for source, _, data in snapshots:
        if source.read_bytes() != data:
            raise ValueError("Source changed during packaging: " + str(source))
    index = dict(schema="jepa-research-cycle-portable-evidence/1", campaign=campaign, summary=summary,
                 packager_sha256=digest(Path(__file__).read_bytes()), original_sources_modified=False,
                 model_or_engine_execution_during_packaging=False, prior_portable_references=references,
                 totals=dict(payloads=len(entries), uncompressed_bytes=sum(e["uncompressed_bytes"] for e in entries),
                             stored_bytes=sum(e["stored_bytes"] for e in entries), gzip_files=sum(e["encoding"].startswith("gzip") for e in entries)),
                 files=entries)
    (out / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    return dict(status="packaged-and-verified", out=str(out), **verify(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=("independent-controls", "transition-replication"))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--completed-transition", action="store_true")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
    else:
        if args.campaign is None:
            parser.error("--campaign or --verify required")
        if args.write and args.campaign == "transition-replication" and not args.completed_transition:
            parser.error("transition packaging requires root completion GO and --completed-transition")
        result = package(args.campaign, args.write)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
