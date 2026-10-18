"""Publish a consistent immutable current research index/handoff pair.

The directory is installed first; one stable JSON pointer is replaced last.
This core checkpoint does not claim to freeze the index's external artifact
closure. Portable Sites packaging is a separate, explicitly pending operation.
"""
import argparse
import contextlib
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MANIFEST_SCHEMA = "jepa-publication-checkpoint/1"
POINTER_SCHEMA = "jepa-current-publication-pointer/1"
INDEX_SCHEMA = "jepa-research-handoff-index/1"
HANDOFF_SCHEMA = "jepa-independent-cycle-handoff/1"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw, parse_constant=invalid)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def pinned(path, raw):
    return dict(path=str(Path(path).resolve()), sha256=digest(raw), bytes=len(raw))


def publication_metadata(index, handoff):
    """Equality of existing attestations, not a new assertion of CI execution."""
    if index.get("schema") != INDEX_SCHEMA or handoff.get("schema") != HANDOFF_SCHEMA:
        raise ValueError("current independent-cycle schemas required; leave legacy handoff historical")
    publication = index["publication"]
    keys = ("head_commit", "tree", "ci_run_id", "ci_conclusion", "merge_commit")
    result = {}
    for key in keys:
        if publication.get(key) != handoff.get(key):
            raise ValueError("index/handoff publication metadata differs: " + key)
        result[key] = publication[key]
    if any(not re.fullmatch(r"[0-9a-f]{40}", str(result[key])) for key in ("head_commit", "tree", "merge_commit")):
        raise ValueError("invalid commit/tree identifier")
    if type(result["ci_run_id"]) is not int or result["ci_run_id"] <= 0 or result["ci_conclusion"] != "success":
        raise ValueError("completed successful checked CI metadata required")
    if publication.get("merged") is not True or publication.get("merged_tree_matches_checked_head") is not True or handoff.get("merged_tree_matches_checked_head") is not True:
        raise ValueError("merge/check tree equality attestation required")
    if handoff.get("merged_tree", result["tree"]) != result["tree"]:
        raise ValueError("handoff merged tree differs")
    result["merged_tree_matches_checked_head"] = True
    return result


def _write_exclusive(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        try:
            os.fsync(descriptor)
            return True
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
            return False
    finally:
        os.close(descriptor)


def _verify_entry(entry, checkpoint):
    if type(entry.get("bytes")) is not int or entry["bytes"] < 1 or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256"))):
        raise ValueError("path/SHA256/byte-count pin required")
    path = Path(entry["path"])
    if not path.is_absolute() or path.is_symlink() or path.parent.resolve() != checkpoint or not path.is_file():
        raise ValueError("core artifact must be a regular flat file inside immutable checkpoint")
    raw = path.read_bytes()
    if len(raw) != entry["bytes"] or digest(raw) != entry["sha256"]:
        raise ValueError("checkpoint artifact hash or byte count differs: " + str(path))
    return raw


def verify_pointer(pointer_path):
    """Read the pointer ONCE, then only its pinned immutable files."""
    pointer_raw = Path(pointer_path).read_bytes()
    pointer = read_json(pointer_raw)
    if pointer.get("schema") != POINTER_SCHEMA:
        raise ValueError("unsupported stable pointer schema")
    checkpoint = Path(pointer["checkpoint_directory"])
    if not checkpoint.is_absolute() or str(checkpoint.resolve()) != str(checkpoint) or not checkpoint.is_dir():
        raise ValueError("canonical immutable checkpoint directory required")
    manifest = read_json(_verify_entry(pointer["manifest"], checkpoint))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unsupported checkpoint manifest schema")
    for key in ("publication_id", "publication", "artifacts", "scope"):
        if manifest.get(key) != pointer.get(key):
            raise ValueError("stable pointer/checkpoint manifest differs: " + key)
    index = read_json(_verify_entry(manifest["artifacts"]["research_index"], checkpoint))
    handoff = read_json(_verify_entry(manifest["artifacts"]["handoff"], checkpoint))
    _verify_entry(manifest["original_handoff_archive"], checkpoint)
    if handoff["research_index"] != manifest["artifacts"]["research_index"]:
        raise ValueError("handoff must pin the exact immutable index path/hash/bytes")
    if publication_metadata(index, handoff) != manifest["publication"]:
        raise ValueError("immutable pair publication metadata differs from manifest")
    return dict(status="verified", publication_id=manifest["publication_id"], publication=manifest["publication"],
                checkpoint_directory=str(checkpoint), manifest=pointer["manifest"], artifacts=manifest["artifacts"], scope=manifest["scope"],
                stable_pointer=pinned(pointer_path, pointer_raw))


def publish(index_path, handoff_path, publications_dir, stable_pointer, expected_index_sha256, expected_handoff_sha256):
    index_path, handoff_path = Path(index_path).resolve(), Path(handoff_path).resolve()
    index_raw, handoff_raw = index_path.read_bytes(), handoff_path.read_bytes()
    if digest(index_raw) != expected_index_sha256 or digest(handoff_raw) != expected_handoff_sha256:
        raise ValueError("original source bytes differ from coordinating source pins")
    index, original_handoff = read_json(index_raw), read_json(handoff_raw)
    publication = publication_metadata(index, original_handoff)
    old_pin = original_handoff["research_index"]
    if Path(old_pin["path"]).resolve() != index_path or old_pin["sha256"] != digest(index_raw) or old_pin.get("bytes", len(index_raw)) != len(index_raw):
        raise ValueError("source handoff does not already match source current index")
    publications_dir, stable_pointer = Path(publications_dir).resolve(), Path(stable_pointer).resolve()
    publication_id = publication["head_commit"][:12] + "-" + digest(index_raw)[:12] + "-" + digest(handoff_raw)[:12]
    final = publications_dir / publication_id
    publications_dir.mkdir(parents=True, exist_ok=True)
    stable_pointer.parent.mkdir(parents=True, exist_ok=True)
    with (publications_dir / ".publication.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if final.exists():
            raise FileExistsError("immutable checkpoint already exists; verify/reuse it, never overwrite")
        stage = Path(tempfile.mkdtemp(prefix=".pending-", dir=publications_dir))
        index_pin = pinned(final / "research-index.json", index_raw)
        handoff = dict(original_handoff)
        handoff["research_index"] = index_pin
        handoff["publication_checkpoint"] = dict(publication_id=publication_id, immutable_core_pair=True,
                original_index=pin_source(index_path, index_raw), original_handoff=pin_source(handoff_path, handoff_raw))
        new_handoff_raw = encoded(handoff)
        artifacts = dict(research_index=index_pin, handoff=pinned(final / "handoff.json", new_handoff_raw))
        scope = dict(current_publication=True, immutable_core_pair=True, legacy_handoff_changed=False,
                     portable=False, external_artifact_closure_copied=False,
                     external_artifact_policy="Original index artifacts retain strict hash checks; full immutable/portable closure is a separate pending publication, never implied by this core snapshot.")
        manifest = dict(schema=MANIFEST_SCHEMA, publication_id=publication_id, publication=publication, artifacts=artifacts,
                        original_handoff_archive=pinned(final / "original-handoff.json", handoff_raw), scope=scope,
                        provenance=dict(original_index=pin_source(index_path, index_raw), original_handoff=pin_source(handoff_path, handoff_raw)),
                        consumer_contract="Read stable pointer once; verify manifest and both immutable files by path/SHA256/bytes before parse. Never substitute mutable current paths. This publisher compares existing metadata, and does not rerun CI.")
        manifest_raw = encoded(manifest)
        for name, raw in (("research-index.json", index_raw), ("handoff.json", new_handoff_raw), ("original-handoff.json", handoff_raw), ("manifest.json", manifest_raw)):
            _write_exclusive(stage / name, raw)
        stage_synced = _fsync_dir(stage)
        if index_path.read_bytes() != index_raw or handoff_path.read_bytes() != handoff_raw:
            raise ValueError("mutable originals changed while staging; preserve pending directory, do not publish")
        os.rename(stage, final)
        parent_synced = _fsync_dir(publications_dir)
        pointer = dict(schema=POINTER_SCHEMA, publication_id=publication_id, publication=publication, checkpoint_directory=str(final),
                       manifest=pinned(final / "manifest.json", manifest_raw), artifacts=artifacts, scope=scope)
        pointer_raw = encoded(pointer)
        # Verify a temporary pointer against final immutable paths BEFORE switch.
        descriptor, preview_name = tempfile.mkstemp(prefix=".publication-pointer-", dir=stable_pointer.parent)
        os.close(descriptor)
        preview = Path(preview_name)
        try:
            with preview.open("wb") as stream:
                stream.write(pointer_raw); stream.flush(); os.fsync(stream.fileno())
            verify_pointer(preview)
            os.replace(preview, stable_pointer)
            pointer_parent_synced = _fsync_dir(stable_pointer.parent)
        finally:
            with contextlib.suppress(FileNotFoundError):
                preview.unlink()
        result = verify_pointer(stable_pointer)
        result.update(immutable_directory_installed_before_pointer=True, stable_pointer_replacements=1,
                      original_sources_unchanged=index_path.read_bytes() == index_raw and handoff_path.read_bytes() == handoff_raw,
                      file_fsync=True, directory_fsync=dict(checkpoint=stage_synced, publication_parent=parent_synced, pointer_parent=pointer_parent_synced),
                      neural_forwards=0, optimizer_updates=0, native_calls=0)
        return result


def pin_source(path, raw):
    return dict(path=str(path), sha256=digest(raw), bytes=len(raw), role="provenance-only; never substituted for immutable fetch artifacts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--handoff", type=Path)
    parser.add_argument("--publications-dir", type=Path)
    parser.add_argument("--stable-pointer", type=Path)
    parser.add_argument("--expected-index-sha256")
    parser.add_argument("--expected-handoff-sha256")
    args = parser.parse_args()
    if args.publish:
        fields = (args.index, args.handoff, args.publications_dir, args.stable_pointer, args.expected_index_sha256, args.expected_handoff_sha256)
        if any(value is None for value in fields):
            parser.error("publish requires both source paths+SHA256 pins, publications-dir and stable-pointer")
        result = publish(*fields)
    else:
        result = verify_pointer(args.verify)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
