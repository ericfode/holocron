#!/usr/bin/env python3
"""
Build arena bundles of Holocron's bots: one folder per bot in build/arena/<name>/, ready to submit to the arena (its
intake checks and enters a bundle as it is: swu_bot bot/arena/intake.js, kind "wasm").

    python3 bots/bundles.py                       # every bot in BOTS
    python3 bots/bundles.py c_clock rust_search   # just these
    python3 bots/bundles.py --list
    python3 bots/bundles.py --arena ../swu_bot    # and check each bundle with the arena's bot/compiled/bundle.py

A WebAssembly bot (C, Rust) becomes bot.wasm (WASI preview 1) plus arena.json (schema swu-arena-bot/1). py_clock is
not compiled: its folder holds only the bot's modules (entry swu_clock.py, no tests), for the arena's Python intake,
which packs it with the arena's own CPython for WASI. No bundle mounts card data: every bot reads its cards from hello.

Needs: rustc with the wasm32-wasip1 target (rustup target add wasm32-wasip1) and the Python package ziglang 0.17.0
(python3 -m pip install ziglang==0.17.0) for zig cc.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "arena")
SCHEMA = "swu-arena-bot/1"
ZIG = "0.17.0"

# name (as the arena names a bot: [a-z][a-z0-9_]*) -> how to build it. c-clock answers ready with protocol v1.
BOTS = {
    "c_clock": {"lang": "c", "protocol": 1},
    "rust_greedy2": {"lang": "rust", "args": ["greedy2"]},
    "rust_search": {"lang": "rust", "args": ["search"]},
    "py_clock": {"lang": "python", "dir": "bots/python", "entry": "swu_clock.py"},
}
SOURCE = {"rust": "bots/rust", "c": "bots/c"}


def log(msg):
    print("[bundles] %s" % msg, flush=True)


def run(cmd, **kw):
    log(" ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(path, recipe, toolchain):
    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--", path, "bots/bundles.py"):
        commit += "+dirty"
    return {
        "source": "https://github.com/ericfode/holocron", "commit": commit, "path": path, "recipe": recipe,
        "toolchain": toolchain, "builder": "self", "source_date_epoch": int(git("log", "-1", "--format=%ct") or 0) or None,
    }


def build_rust(cache):
    if "rust" in cache:
        return cache["rust"]
    target = os.path.join(OUT, ".cargo")
    cargo_home = os.environ.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
    # strip symbols, and drop this machine's paths from panic messages so the wasm is the same on any machine
    flags = "-C strip=symbols --remap-path-prefix=%s=. --remap-path-prefix=%s=/cargo" % (ROOT, cargo_home)
    env = dict(os.environ, CARGO_TARGET_DIR=target, RUSTFLAGS=flags)
    run(["cargo", "build", "--release", "--target", "wasm32-wasip1", "--manifest-path", os.path.join(ROOT, SOURCE["rust"], "Cargo.toml")], env=env)
    rustc = subprocess.run(["rustc", "--version"], capture_output=True, text=True).stdout.strip()
    cache["rust"] = (os.path.join(target, "wasm32-wasip1", "release", "swu-bot-rs.wasm"),
                     "RUSTFLAGS='%s' cargo build --release --target wasm32-wasip1" % flags.replace(ROOT, "<repo>").replace(cargo_home, "<cargo>"), rustc)
    return cache["rust"]


def build_c(work):
    version = subprocess.run([sys.executable, "-m", "ziglang", "version"], capture_output=True, text=True).stdout.strip()
    if version != ZIG:
        sys.exit("needs zig %s from the Python package ziglang (found %r): python3 -m pip install ziglang==%s" % (ZIG, version, ZIG))
    out = os.path.join(work, "c_clock.wasm")
    cmd = [sys.executable, "-m", "ziglang", "cc", "--target=wasm32-wasi", "-O2", "-std=gnu11", "-s", "-o", out, "bot.c", "cards.c", "json.c", "-lm"]
    run(cmd, cwd=os.path.join(ROOT, SOURCE["c"]))
    return out, "zig cc --target=wasm32-wasi -O2 -std=gnu11 -s -o bot.wasm bot.c cards.c json.c -lm", "zig %s (pip ziglang)" % ZIG


def manifest(name, spec, entry_path, args, prov):
    return {
        "schema": SCHEMA, "name": name, "lang": spec["lang"], "protocol": spec.get("protocol", 2),
        "kind": "wasm", "platform": "wasm32-wasip1", "runtime": "wasi-p1", "run": {"cmd": "./bot.wasm", "args": args, "env": {}},
        "entry_sha256": sha256_file(entry_path),
        "resources": {"memory_mb": 512, "start_ms": 30000, "decide_ms": 10000},
        "network": "none", "deterministic": True, "build": prov,
    }


def build_one(name, cache):
    spec = BOTS[name]
    folder = os.path.join(OUT, name)
    work = os.path.join(OUT, ".work")
    os.makedirs(work, exist_ok=True)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    if spec["lang"] == "python":
        # the source folder the arena's Python intake takes: the bot's modules only
        src = os.path.join(ROOT, spec["dir"])
        for f in sorted(os.listdir(src)):
            if f.endswith(".py") and not f.startswith("test_"):
                shutil.copyfile(os.path.join(src, f), os.path.join(folder, f))
        if not os.path.isfile(os.path.join(folder, spec["entry"])):
            sys.exit("%s: no %s in %s" % (name, spec["entry"], spec["dir"]))
    else:
        if spec["lang"] == "rust":
            wasm, recipe, tool = build_rust(cache)
        else:
            wasm, recipe, tool = build_c(work)
        entry = os.path.join(folder, "bot.wasm")
        shutil.copyfile(wasm, entry)
        m = manifest(name, spec, entry, spec.get("args", []), provenance(SOURCE[spec["lang"]], recipe, tool))
        with open(os.path.join(folder, "arena.json"), "w") as f:
            json.dump(m, f, indent=2)
            f.write("\n")
    for dirpath, _, filenames in os.walk(folder):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            os.chmod(p, (os.stat(p).st_mode & ~0o7777) | 0o644)
    files = sorted(os.listdir(folder))
    log("%-13s %s (%d B)" % (name, ", ".join(files), sum(os.path.getsize(os.path.join(folder, f)) for f in files)))
    return folder


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("bots", nargs="*", help="names from BOTS (default: all)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--arena", help="a swu_bot checkout: check each bundle with its bot/compiled/bundle.py")
    o = ap.parse_args()
    if o.list:
        for name, spec in BOTS.items():
            print("%-13s %s" % (name, spec["lang"]))
        return
    unknown = [b for b in o.bots if b not in BOTS]
    if unknown:
        sys.exit("unknown bot(s): %s (see --list)" % ", ".join(unknown))
    cache = {}
    built = {name: build_one(name, cache) for name in o.bots or list(BOTS)}
    if o.arena:
        checker = os.path.join(o.arena, "bot", "compiled", "bundle.py")
        for name, folder in built.items():
            if BOTS[name]["lang"] != "python":  # a Python source folder has no arena.json until the intake packs it
                run([sys.executable, "-I", checker, folder])


if __name__ == "__main__":
    main()
