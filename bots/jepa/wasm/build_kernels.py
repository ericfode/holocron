"""Compile the unchanged tinygrad C kernels using already installed toolchains.

Native builds use Clang. The bounded WASM build retargets unoptimized Clang IR
using Rust's installed LLVM tools. This route retains i64 setter indices and
wasm32 data pointers; it is explicitly distinct from a WASI SDK build.
"""
import argparse
from pathlib import Path
import re
import subprocess


def run(*command):
    subprocess.run(list(map(str, command)), check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--target', required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent
    wasm = a.target == 'wasm32-unknown-unknown'
    if a.target.startswith('wasm') and not wasm:
        p.error('this verified recipe supports wasm32-unknown-unknown with explicit WASI imports')
    if wasm:
        sysroot = Path(subprocess.check_output(['rustc', '--print', 'sysroot'], text=True).strip())
        host = next(x.split(': ', 1)[1] for x in subprocess.check_output(['rustc', '-vV'], text=True).splitlines() if x.startswith('host:'))
        llc = sysroot / 'lib/rustlib' / host / 'bin/llc'
    for name in ('jepa_context', 'jepa_predict4'):
        src = root / 'generated' / (name + '.c')
        obj = a.out / (name + '.o')
        if not wasm:
            run('clang', '-O2', '-ffp-contract=off', '-fno-common', '-c', src, '-o', obj)
            continue
        ir = a.out / (name + '.native.ll')
        portable = a.out / (name + '.wasm.ll')
        run('clang', '-S', '-emit-llvm', '-O0', '-fno-common', '-ffp-contract=off', src, '-o', ir)
        text = re.sub(r' "(?:target-cpu|target-features|tune-cpu)"="[^"]*"', '', ir.read_text())
        text = text.replace(' noinline', '').replace(' optnone', '')
        text = '\n'.join(x for x in text.splitlines() if not x.startswith(('target datalayout =', 'target triple ='))) + '\n'
        portable.write_text(text)
        run(llc, '-mtriple=wasm32-unknown-unknown', '-mcpu=generic', '-mattr=+simd128', '-filetype=obj', portable, '-o', obj)


if __name__ == '__main__':
    main()
