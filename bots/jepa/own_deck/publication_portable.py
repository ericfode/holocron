"""Portable, hash-checked scientific-data closure; no models or deployment.

Fetchable data records use explicit relative ``url``+SHA256+bytes. Host paths,
code/checkpoint provenance, historical indexes and the live feed are metadata
only. Original data bytes are archived separately for inspection.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

import publication_checkpoint as P

SCHEMA = "jepa-portable-research-publication/1"
PROVENANCE_KEYS = {
    "provenance", "source_pins", "source_provenance", "encoder_sources", "sources", "source_sha256", "source_hashes", "verified_files",
    "protected", "protected_before", "protected_after", "immutableBefore", "immutableAfter",
    "previous_index", "previous_index_snapshot", "previous_publication", "space_history", "publication_checkpoint",
    "supplement", "checkpoint", "checkpoints", "model_source", "export_source", "export_sources",
    "live_run_events", "raw_fit_source", "sourcePath", "source_path", "source_paths", "cwd", "working_directory",
    "project_files", "stable_index",
}
SOURCE_EXTENSIONS = {".py", ".rs", ".js", ".ts", ".toml", ".lock", ".safetensors", ".c", ".h"}
LOCAL = re.compile(r"/(?:Users|home|private|tmp|var)/[^\s)\]\"'<>`]+")


def hash_file(path):
    return P.digest(Path(path).read_bytes())


def safe_url(url):
    if not isinstance(url, str) or not url or "\\" in url:
        raise ValueError("invalid portable URL")
    decoded = unquote(url)
    parts = urlsplit(decoded)
    if parts.scheme or parts.netloc or parts.query or parts.fragment or decoded.startswith("/") or any(x in ("", ".", "..") for x in decoded.split("/")):
        raise ValueError("portable URL must stay relative and traversal-free: " + url)
    return decoded


def resolve_url(bundle, from_file, url):
    relative = safe_url(url)
    target = (Path(from_file).parent / relative).resolve()
    if not target.is_relative_to(Path(bundle).resolve()) or not target.is_file():
        raise ValueError("portable URL missing/outside bundle: " + url)
    return target


class Closure:
    def __init__(self, stage, max_bytes=512 * 1024 * 1024, max_files=4000):
        self.stage = Path(stage)
        (self.stage / "assets").mkdir()
        (self.stage / "provenance/raw").mkdir(parents=True)
        self.cache, self.active, self.values, self.records = {}, set(), {}, {}
        self.input_pins = {}
        self.max_bytes, self.max_files, self.total_bytes = max_bytes, max_files, 0

    def store(self, relative, raw):
        relative = safe_url(relative)
        if len(self.records) >= self.max_files or self.total_bytes + len(raw) > self.max_bytes:
            raise ValueError("portable closure exceeds fixed file/byte cap")
        path = self.stage / relative
        P._write_exclusive(path, raw)
        record = dict(url=relative, sha256=P.digest(raw), bytes=len(raw))
        self.records[relative] = record
        self.total_bytes += len(raw)
        return record

    def original_path(self, path, origin):
        path = Path(path)
        return path.resolve() if path.is_absolute() else (Path(origin).parent / path).resolve()

    def data_pin(self, record, origin):
        path = self.original_path(record["path"], origin)
        raw = path.read_bytes()
        if P.digest(raw) != record["sha256"] or ("bytes" in record and len(raw) != record["bytes"]):
            raise ValueError("required data pin mismatch: " + str(path) + "; origin=" + str(origin) + "; expected=" + record["sha256"] + "; actual=" + P.digest(raw))
        self.input_pins[str(path)] = dict(sha256=record["sha256"], bytes=len(raw))
        return path, raw

    def copy(self, record, origin, root_name=None):
        source, raw = self.data_pin(record, origin)
        key = (str(source), record["sha256"])
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            raise ValueError("cyclic fetchable data dependency: " + str(source))
        self.active.add(key)
        slug = re.sub(r"[^A-Za-z0-9_.-]", "_", source.name)[-100:]
        tag = hashlib.sha256(str(source).encode()).hexdigest()[:10] + "-" + record["sha256"][:12]
        raw_url = "provenance/raw/" + tag + "-" + slug
        raw_record = self.store(raw_url, raw)
        # Large compressed raw receipts/manifests are downloadable evidence,
        # never recursively interpreted as browser fetch instructions.
        is_json = source.name.endswith(".json")
        is_text = source.suffix in (".md", ".txt")
        name = root_name or ("assets/" + tag + "-" + slug + (".json" if is_text else ""))
        if is_json:
            value = P.read_json(raw)
            value = self.sanitize(value, source, name)
            result = self.store(name, P.encoded(value))
            self.values[name] = value
        elif is_text:
            # Render as plain text, not Markdown/HTML with host-path links.
            text = raw.decode("utf-8")
            value = dict(schema="jepa-portable-plain-report/1", text=LOCAL.sub("[local provenance path]", text),
                         rendering="plain-text; original Markdown is archived as provenance")
            result = self.store(name, P.encoded(value))
            self.values[name] = value
        else:
            result = self.store(name, raw)
        result = dict(result, provenance=dict(original_path=str(source), original_sha256=record["sha256"],
                                              original_bytes=len(raw), raw_archive=raw_record,
                                              role="original bytes/host path are provenance only, never a fetch-path fallback"))
        self.cache[key] = result
        self.active.remove(key)
        return result

    def reference(self, record, origin, parent_name):
        copied = self.copy(record, origin)
        relative = os.path.relpath(copied["url"], Path(parent_name).parent).replace(os.sep, "/")
        # All nested data files live together; root files point into assets.
        safe_url(relative)
        return dict(url=relative, sha256=copied["sha256"], bytes=copied["bytes"], provenance=copied["provenance"])

    def sanitize(self, value, origin, parent_name):
        if isinstance(value, list):
            return [self.sanitize(x, origin, parent_name) for x in value]
        if isinstance(value, str):
            if LOCAL.search(value) or value.startswith("file:"):
                return dict(provenance_only=dict(original_value=value), display="Local provenance path; not a fetch URL")
            return value
        if not isinstance(value, dict):
            return value
        # Published evidence packages pin the stored (possibly gzip) payload.
        if isinstance(value.get("path"), str) and re.fullmatch(r"[0-9a-f]{64}", str(value.get("stored_sha256"))):
            pin = dict(path=value["path"], sha256=value["stored_sha256"], bytes=value["stored_bytes"])
            result = self.reference(pin, origin, parent_name)
            result["provenance"]["original_record"] = value
            result["payload_role"] = "raw-download-no-embedded-fetches" if value["path"].endswith(".gz") else "scientific-evidence"
            return result
        if isinstance(value.get("path"), str) and re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256"))):
            path = self.original_path(value["path"], origin)
            if path.suffix in SOURCE_EXTENSIONS or "source_commit" in value or ("repository" in value and "commit" in value):
                return dict(provenance_only=dict(value), fetchable=False)
            result = self.reference(value, origin, parent_name)
            for key, child in value.items():
                if key not in ("path", "sha256", "bytes", "source", "provenance"):
                    result[key] = self.sanitize(child, origin, parent_name)
            return result
        result, provenance = {}, {}
        used = set()
        # Browser index records carry paired path/hash fields instead of pins.
        for path_key, sha_key, url_key in (("vectors_path", "artifact_sha256", "vectors_url"), ("manifest_path", "manifest_sha256", "manifest_url")):
            if path_key in value and sha_key in value:
                target = self.reference(dict(path=value[path_key], sha256=value[sha_key]), origin, parent_name)
                result[url_key] = target["url"]
                result[sha_key] = target["sha256"]
                result[url_key + "_bytes"] = target["bytes"]
                provenance[path_key] = target["provenance"]
                used.update((path_key, sha_key, "relative_file"))
        for key, child in value.items():
            if key in used:
                continue
            historical_pin = (key in ("before", "previous", "legacy_index", "legacy_index_before") and isinstance(child, dict)
                              and "path" in child and "sha256" in child)
            if key in PROVENANCE_KEYS or historical_pin or (key in ("source", "base") and isinstance(child, dict) and "path" in child) or (key == "path" and isinstance(child, str)):
                provenance[key] = child
            else:
                result[key] = self.sanitize(child, origin, parent_name)
        if provenance:
            result.setdefault("provenance_only", {}).update(provenance)
        return result

    def verify_sources_unchanged(self):
        for path, pin in self.input_pins.items():
            raw = Path(path).read_bytes()
            if len(raw) != pin["bytes"] or P.digest(raw) != pin["sha256"]:
                raise ValueError("source changed during portable copy: " + path)
        return len(self.input_pins)


def verify_bundle(bundle):
    bundle = Path(bundle)
    manifest = P.read_json((bundle / "manifest.json").read_bytes())
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported portable manifest")
    checked = set()
    def verify_json(value, origin, provenance=False):
        if isinstance(value, list):
            for child in value:
                verify_json(child, origin, provenance)
        elif isinstance(value, dict):
            if provenance:
                return
            if isinstance(value.get("url"), str):
                target = resolve_url(bundle, origin, value["url"])
                raw = target.read_bytes()
                if P.digest(raw) != value.get("sha256") or len(raw) != value.get("bytes"):
                    raise ValueError("portable data hash/bytes mismatch")
                if target.suffix == ".json" and target not in checked:
                    checked.add(target); verify_json(P.read_json(raw), target)
            for key, child in value.items():
                if key == "provenance_only" or key == "provenance":
                    continue
                if key in ("vectors_url", "manifest_url"):
                    target = resolve_url(bundle, origin, child)
                    digest_key = "artifact_sha256" if key == "vectors_url" else "manifest_sha256"
                    raw = target.read_bytes()
                    if P.digest(raw) != value[digest_key] or len(raw) != value[key + "_bytes"]:
                        raise ValueError("portable paired data hash mismatch")
                    if target not in checked:
                        checked.add(target); verify_json(P.read_json(raw), target)
                elif key != "url":
                    verify_json(child, origin)
        elif isinstance(value, str) and (LOCAL.search(value) or value.startswith("file:")):
            raise ValueError("host path escaped provenance into UI data")
    verify_json(manifest, bundle / "manifest.json")
    index_path = resolve_url(bundle, bundle / "manifest.json", manifest["artifacts"]["research_index"]["url"])
    handoff_path = resolve_url(bundle, bundle / "manifest.json", manifest["artifacts"]["handoff"]["url"])
    index, handoff = (P.read_json(path.read_bytes()) for path in (index_path, handoff_path))
    if P.publication_metadata(index, handoff) != manifest["publication"]:
        raise ValueError("portable pair publication metadata mismatch")
    target = resolve_url(bundle, handoff_path, handoff["research_index"]["url"])
    if target != index_path:
        raise ValueError("portable handoff does not resolve to exact portable index")
    checksums = P.read_json((bundle / "checksums.json").read_bytes())
    for entry in checksums["files"]:
        target = resolve_url(bundle, bundle / "checksums.json", entry["url"])
        raw = target.read_bytes()
        if len(raw) != entry["bytes"] or P.digest(raw) != entry["sha256"]:
            raise ValueError("bundle checksum mismatch: " + entry["url"])
    return dict(status="verified", data_urls_checked=len(checked), files=len(checksums["files"]), publication=manifest["publication"])


def deterministic_zip(bundle, destination):
    bundle, destination = Path(bundle), Path(destination)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
            name = path.relative_to(bundle).as_posix()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def select_vector_spaces(scientific, embedding_value, *, expected_artifact_count=33, expected_space_count=6,
                         all_registered_spaces=False, expected_space_ids=None):
    """Freeze a selection explicitly; legacy callers retain the six-space assay."""
    if any(type(n) is not int or n < 1 for n in (expected_artifact_count, expected_space_count)):
        raise ValueError("positive explicit artifact/space counts required")
    if len(scientific) != expected_artifact_count:
        raise ValueError("scientific artifact count differs from frozen expectation")
    if type(all_registered_spaces) is not bool:
        raise ValueError("all_registered_spaces must be explicit boolean")
    if all_registered_spaces and expected_space_ids is None:
        raise ValueError("all registered spaces require frozen exact space IDs")
    selected = [space for key, space in embedding_value["spaces"].items()
                if all_registered_spaces or key.startswith("independent_controls_")]
    ids = [space["id"] for space in selected]
    if len(selected) != expected_space_count or len(ids) != len(set(ids)):
        raise ValueError("vector space count/unique IDs differ from frozen expectation")
    if expected_space_ids is not None:
        expected = list(expected_space_ids)
        if len(expected) != len(set(expected)) or set(expected) != set(ids):
            raise ValueError("exact vector space IDs differ from frozen expectation")
    result = []
    for space in selected:
        if space.get("semantic_validated") is not False:
            raise ValueError("unvalidated-space status must remain explicit")
        result.append(dict(id=space["id"], url="assets/" + Path(space["vectors_url"]).name,
                           sha256=space["artifact_sha256"], bytes=space["vectors_url_bytes"],
                           dimension=space["dimension"], rows=space["entity_count"], semantic_validated=False))
    return result


def build(pointer_path, out, *, expected_artifact_count=33, expected_space_count=6,
          all_registered_spaces=False, expected_space_ids=None):
    pointer_path, out = Path(pointer_path).resolve(), Path(out).resolve()
    verified = P.verify_pointer(pointer_path)
    if out.exists() or out.with_suffix(".zip").exists():
        raise FileExistsError("portable immutable output already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".sites-pending-", dir=out.parent))
    closure = Closure(stage)
    index_pin, handoff_pin = (verified["artifacts"][key] for key in ("research_index", "handoff"))
    index = closure.copy(index_pin, pointer_path, "research-index.json")
    handoff = closure.copy(handoff_pin, pointer_path, "handoff.json")
    sanitized_index = closure.values[index["url"]]
    scientific = sanitized_index["artifacts"]
    embedding_entry = scientific.get("embedding_index")
    if not embedding_entry:
        raise ValueError("embedding index artifact required")
    embedding_value = closure.values["assets/" + Path(embedding_entry["url"]).name]
    vector_spaces = select_vector_spaces(scientific, embedding_value, expected_artifact_count=expected_artifact_count,
                                        expected_space_count=expected_space_count, all_registered_spaces=all_registered_spaces,
                                        expected_space_ids=expected_space_ids)
    payload = dict(schema="jepa-portable-research-ui/1", publication=verified["publication"], counts=sanitized_index["counts"],
                   limits=sanitized_index.get("current_limits", []), scientific_artifacts=scientific, vector_spaces=vector_spaces,
                   semantic_validated=False, data_policy="All data URLs are relative hash/byte-pinned bundle files. Provenance paths are never fetch URLs. No scientific results or support flags were recomputed.")
    if "space_groups" in embedding_value:
        payload["space_groups"] = embedding_value["space_groups"]
    payload_pin = closure.store("ui-payload.json", P.encoded(payload))
    manifest = dict(schema=SCHEMA, publication_id=verified["publication_id"], publication=verified["publication"],
                    artifacts=dict(research_index={k: index[k] for k in ("url", "sha256", "bytes")},
                                   handoff={k: handoff[k] for k in ("url", "sha256", "bytes")}, ui_payload=payload_pin),
                    scientific_artifact_count=expected_artifact_count, vector_spaces=vector_spaces, fetchable_closure_complete=True,
                    provenance=dict(core_stable_pointer=P.pinned(pointer_path, pointer_path.read_bytes()), original_scope=verified["scope"]),
                    provenance_policy="Raw original bytes are under provenance/raw; host/source/code/checkpoint/history/live-feed paths are non-fetch metadata. Required scientific data pins never silently downgrade on mismatch.",
                    semantic_validated=False, neural_forwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0)
    if "space_groups" in embedding_value:
        manifest["space_groups"] = embedding_value["space_groups"]
    closure.store("manifest.json", P.encoded(manifest))
    checksums = dict(schema="jepa-portable-checksums/1", files=[closure.records[key] for key in sorted(closure.records)],
                     self_hash="Excluded to avoid a hash cycle; external export receipt pins this file and deterministic ZIP.")
    P._write_exclusive(stage / "checksums.json", P.encoded(checksums))
    validation = verify_bundle(stage)
    validation["original_source_pins_rechecked"] = closure.verify_sources_unchanged()
    P._fsync_dir(stage)
    os.rename(stage, out)
    archive = out.with_suffix(".zip")
    deterministic_zip(out, archive)
    validation.update(bundle=str(out), manifest=P.pinned(out / "manifest.json", (out / "manifest.json").read_bytes()),
                      checksums=P.pinned(out / "checksums.json", (out / "checksums.json").read_bytes()), zip=P.pinned(archive, archive.read_bytes()),
                      neural_forwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pointer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-artifact-count", type=int, default=33)
    parser.add_argument("--expected-space-count", type=int, default=6)
    parser.add_argument("--all-registered-spaces", action="store_true")
    parser.add_argument("--expected-space-id", action="append", dest="expected_space_ids")
    args = parser.parse_args()
    print(json.dumps(build(args.pointer, args.out, expected_artifact_count=args.expected_artifact_count,
                           expected_space_count=args.expected_space_count, all_registered_spaces=args.all_registered_spaces,
                           expected_space_ids=args.expected_space_ids), indent=2))


if __name__ == "__main__":
    main()
