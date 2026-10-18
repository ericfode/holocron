"""Build the table JEPA as a self-contained WASI preview-1 bot; never submit it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARENA_REVISION = '3afa1f8bbf3bc45a08359f15b96291d55c641fa6'
EXPECTED = {
    'tx-t10.safetensors': '50b8f9a2c3782c5cf5b23e80b2a65d2a0292523ec9a9213287b86143f99b6d34',
    'tx-t10-e.safetensors': 'bee3f60123317a850e49f4037fd380b5d2007aebb43f0f9ced761eed89dbf9f1',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / 'build/arena/jepa_tx_gate_wasm')
    ap.add_argument('--diagnostics', action='store_true', help='test-only tensor/stats messages; not an admission artifact')
    args = ap.parse_args()
    for name, digest in EXPECTED.items():
        if sha(HERE.parent / 'models' / name) != digest:
            raise ValueError('checkpoint bytes differ from preserved table baseline: ' + name)
    command = ['cargo', 'build', '--offline', '--release', '--target', 'wasm32-unknown-unknown',
               '--manifest-path', str(HERE / 'runtime/Cargo.toml')]
    if args.diagnostics:
        command += ['--features', 'diagnostics']
    # All mutable compiler/cache outputs remain inside this checkout.
    cargo_home = Path(os.environ.get('CARGO_HOME', str(Path.home() / '.cargo'))).resolve()
    flags = ' '.join([os.environ.get('RUSTFLAGS', ''), '-C strip=symbols',
                      '--remap-path-prefix=%s=.' % ROOT,
                      '--remap-path-prefix=%s=/cargo' % cargo_home]).strip()
    env = dict(os.environ, CARGO_TARGET_DIR=str(HERE / 'runtime/target'), RUSTFLAGS=flags)
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    binary = HERE / 'runtime/target/wasm32-unknown-unknown/release/jepa-wasi.wasm'
    subprocess.run(['wasm-tools', 'validate', str(binary)], check=True)
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        if set(p.name for p in out.iterdir()) - {'bot.wasm', 'arena.json'}:
            raise ValueError('refusing to replace a directory containing unrelated files')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(binary, out / 'bot.wasm')
    inputs = sorted(p for folder in ('controller', 'runtime', 'generated') for p in (HERE / folder).rglob('*')
                    if p.is_file() and 'target' not in p.relative_to(HERE).parts)
    inputs += [HERE / 'build.py', HERE / 'build_kernels.py']
    source_files = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    source_digest = hashlib.sha256(json.dumps(source_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {
        'schema': 'swu-arena-bot/1', 'name': 'jepa_tx_gate_wasm', 'lang': 'rust', 'protocol': 2,
        'kind': 'wasm', 'platform': 'wasm32-wasip1', 'runtime': 'wasi-p1',
        'run': {'cmd': './bot.wasm', 'args': [], 'env': {}},
        'entry_sha256': sha(binary), 'resources': {'memory_mb': 256},
        'network': 'none', 'deterministic': False,
        'build': {'source': 'https://github.com/ericfode/holocron', 'commit': commit,
                  'path': 'bots/jepa/wasm', 'recipe': 'python3 bots/jepa/wasm/build.py',
                  'builder': 'self', 'toolchain': subprocess.check_output(['rustc', '--version'], text=True).strip(),
                  'rustflags': flags.replace(str(ROOT), '<repo>').replace(str(cargo_home), '<cargo>'),
                  'kernel_toolchain': 'Apple Clang IR, Rust LLVM llc; explicit WASI p1 imports',
                  'source_sha256': source_digest, 'source_files': source_files,
                  'checkpoint_sha256': EXPECTED, 'arena_compatibility_revision': ARENA_REVISION,
                  'diagnostics': args.diagnostics},
    }
    (out / 'arena.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'bundle': str(out), 'entry_sha256': manifest['entry_sha256'],
                      'bytes': binary.stat().st_size, 'source_sha256': source_digest}))


if __name__ == '__main__':
    main()
