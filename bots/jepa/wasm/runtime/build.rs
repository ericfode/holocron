use std::{env, path::PathBuf, process::Command};
fn main() {
    let here = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let target = env::var("TARGET").unwrap();
    let script = here.join("../build_kernels.py");
    let generated = if env::var_os("CARGO_FEATURE_OWN_DECK").is_some() {
        "generated-own-deck"
    } else {
        "generated"
    };
    assert!(
        Command::new("python3")
            .arg(&script)
            .arg("--out")
            .arg(&out)
            .arg("--target")
            .arg(&target)
            .arg("--generated")
            .arg(here.join("..").join(generated))
            .status()
            .unwrap()
            .success(),
        "kernel compilation failed"
    );
    for name in ["jepa_context", "jepa_predict4"] {
        println!(
            "cargo:rustc-link-arg={}",
            out.join(format!("{name}.o")).display()
        );
        println!(
            "cargo:rerun-if-changed={}",
            here.join(format!("../{generated}/{name}.c")).display()
        );
    }
    if target == "wasm32-unknown-unknown" {
        let root = String::from_utf8(
            Command::new("rustc")
                .args(["--print", "sysroot"])
                .output()
                .unwrap()
                .stdout,
        )
        .unwrap();
        println!(
            "cargo:rustc-link-arg={}/lib/rustlib/wasm32-wasip2/lib/self-contained/libc.a",
            root.trim()
        );
        println!("cargo:rustc-link-arg=--export=_start");
        println!("cargo:rustc-link-arg=--initial-memory=16777216");
        println!("cargo:rustc-link-arg=--max-memory=268435456");
    }
    println!("cargo:rerun-if-changed={}", script.display());
}
