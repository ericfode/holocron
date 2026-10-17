"""Prepare a tiny CPython-WASI bundle; never downloads or runs its runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    destination = args.output.resolve()
    if not destination.is_relative_to(here):
        parser.error("output must remain inside host-evidence")
    destination.mkdir(parents=True, exist_ok=False)
    entry = destination / "bot.py"
    shutil.copyfile(here / "protocol_fixture.py", entry)
    manifest = {
        "schema": "swu-arena-bot/1",
        "name": "v2_interpreter_probe",
        "lang": "python",
        "protocol": 2,
        "kind": "wasm",
        "platform": "wasm32-wasip1",
        "runtime": "python-3.14-wasi",
        "run": {"cmd": "python3", "args": ["bot.py"], "env": {}},
        "entry_sha256": hashlib.sha256(entry.read_bytes()).hexdigest(),
        "resources": {"memory_mb": 1024, "start_ms": 30000, "decide_ms": 10000},
        "network": "none",
        "deterministic": True,
        "build": {"description": "Bounded v2 interpreter overhead probe, not JEPA inference"},
    }
    (destination / "arena.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(destination)


if __name__ == "__main__":
    main()
