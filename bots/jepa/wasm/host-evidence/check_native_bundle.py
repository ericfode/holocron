"""Strict local native-WASI bundle evidence; validates/compiles but never invokes _start."""
import argparse
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import sys

import wasmtime

ARENA_REVISION = "3afa1f8bbf3bc45a08359f15b96291d55c641fa6"
CHECKER_BLOB = "b065fc53391b37a6c6d4cf0fadff603dc4fa9ed1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlinks are forbidden: " + str(path))
        if path.is_file():
            result[str(path.relative_to(folder))] = {"bytes": path.stat().st_size,
                                                     "sha256": sha(path.read_bytes())}
        elif not path.is_dir():
            raise ValueError("only ordinary files/directories allowed: " + str(path))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arena", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    destination = args.out.resolve()
    if not destination.is_relative_to(here):
        parser.error("output must remain inside host-evidence")
    if version("wasmtime") != "49.0.0":
        parser.error("use Arena's pinned wasmtime==49.0.0 interpreter")
    checker = args.arena.resolve() / "bot/compiled/bundle.py"
    data = checker.read_bytes()
    checker_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if checker_blob != CHECKER_BLOB:
        raise ValueError("checker differs from final Arena revision")
    folder = args.bundle.resolve()
    before = snapshot(folder)
    if sum(row["bytes"] for row in before.values()) > 64 << 20 or len(before) > 2000:
        raise ValueError("bundle exceeds Arena's transfer bounds")
    manifest = json.loads((folder / "arena.json").read_text())
    if not (manifest.get("schema") == "swu-arena-bot/1" and
            type(manifest.get("protocol")) is int and manifest["protocol"] == 2 and
            manifest.get("kind") == "wasm" and manifest.get("platform") == "wasm32-wasip1" and
            manifest.get("runtime") == "wasi-p1" and manifest.get("network") == "none"):
        raise ValueError("manifest must explicitly declare native WASI preview1, protocol2, no network")
    if manifest.get("run", {}).get("cmd") != "./bot.wasm":
        raise ValueError("this native-WASI check expects ./bot.wasm")
    entry = folder / "bot.wasm"
    module_bytes = entry.read_bytes()
    expected = manifest.get("entry_sha256")
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected) or sha(module_bytes) != expected:
        raise ValueError("entry_sha256 is required and must match actual bot.wasm bytes")
    checker_command = [sys.executable, "-I", str(checker), str(folder)]
    checked = subprocess.run(checker_command, capture_output=True, text=True, timeout=15, check=True)
    archive = subprocess.check_output([sys.executable, "-I", str(checker), "tar", str(folder)], timeout=15)
    digest = sha(archive)
    if ("sha256:" + digest) not in checked.stdout:
        raise ValueError("checker ID differs from canonical tar SHA-256")
    if len(archive) > 68 << 20 or sum(row["bytes"] for row in before.values()) > 64 << 20 or len(before) > 2000:
        raise ValueError("bundle exceeds Arena's transfer bounds")
    engine = wasmtime.Engine()
    module = wasmtime.Module(engine, module_bytes)
    def type_description(item):
        if isinstance(item, wasmtime.FuncType):
            return {"kind": "function", "params": [str(t) for t in item.params],
                    "results": [str(t) for t in item.results]}
        return {"kind": type(item).__name__}
    imports = [{"module": item.module, "name": item.name, "type": type_description(item.type)} for item in module.imports]
    if any(item["module"] != "wasi_snapshot_preview1" for item in imports):
        raise ValueError("module requires imports unavailable from the normal Arena host")
    export_types = {item.name: item.type for item in module.exports}
    exports = {name: type_description(item) for name, item in export_types.items()}
    start = export_types.get("_start")
    if not (isinstance(start, wasmtime.FuncType) and not start.params and not start.results and
            isinstance(export_types.get("memory"), wasmtime.MemoryType)):
        raise ValueError("Arena native entry requires _start and memory exports")
    if snapshot(folder) != before:
        raise ValueError("bundle changed during validation; rerun on finished contents")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "bundle.tar").write_bytes(archive)
    report = {"ok": True, "arena_revision": ARENA_REVISION, "checker_git_blob": checker_blob,
              "checker_command": checker_command, "checker_stdout": checked.stdout.strip(),
              "bundle": str(folder), "bundle_sha256": digest, "entry_sha256": sha(module_bytes),
              "entry_bytes": len(module_bytes), "canonical_tar_bytes": len(archive),
              "canonical_gzip_bytes": len(gzip.compress(archive, compresslevel=9, mtime=0)),
              "files": before, "manifest": manifest, "wasmtime_version": version("wasmtime"),
              "imports": imports, "exports": exports,
              "scope": "Manifest, digest, pinned Wasmtime compilation only; _start not invoked"}
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
