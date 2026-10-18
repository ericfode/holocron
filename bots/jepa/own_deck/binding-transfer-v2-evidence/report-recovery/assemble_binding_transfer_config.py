"""Metadata-only assembler for zero-neural saved-report recovery.

Consumes immutable saved predictions/checkpoints and the sealed data plan. Root alone runs --write after source freeze. No initialization,
lease, native/build process, numerical import, model, or fit is invoked here.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent
TASK = CAMPAIGN.parents[1]
OWN = TASK / "holocron-deck-context/bots/jepa/own_deck"
OLD = CAMPAIGN.parent / "binding-transfer-repair-v1"
LEDGER = CAMPAIGN / "campaign-ledger.jsonl"
VENV = Path("/Users/ericfode/src/crown-jepa/.venv")
PYTHON = (VENV / "bin/python").resolve()
SITE = VENV / "lib/python3.11/site-packages"
CACHED_ARCHIVES = tuple(Path("/Users/ericfode/.cache/uv/archive-v0") / name for name in (
    "rehTsShR29rpWi8Dqz5BL", "ntYsJgeLWxSB0rhe6n9sh", "5i8dYw1S9c5zrvrF0rCIy",
    "C7W22kpzl1cAe-Hdx0N-2", "F1isPlsf9ooQ4EGhGPl5V", "PVyRmcnszTpMFeVdyuyJs",
    "fDmWyEr9slZLLcHdlujql", "khxszcG0X4WuYCMH_DEdE", "7h7hIgcQT6GjZZGqqRrhM"))
ENV_REFERENCE = TASK / "experiments/effect-identifiability-v2/seal-preflight-command-v2.json"
ACCOUNTING_SHA = "b212f83d72e6e2eb2feb248d14dce4fbf2a4c8b3e468a2a22c9810cf051e3acb"
SCHEMA = "jepa-binding-transfer-report-configuration-assembly/1"
STAGE_ORDER = ("recover", "baselines", "verify")



def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def verify_pin(expected):
    expected = {key: expected[key] for key in ("path", "sha256", "bytes")}
    require(Path(expected["path"]).is_absolute(), "absolute pinned path required")
    require(pin(expected["path"]) == expected, "changed expected source: " + expected["path"])
    return expected


def read(path):
    return json.loads(Path(path).read_text())


def exclusive_json(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def accounting():
    """The only loaded campaign module is the pinned, stdlib-only accounting API."""
    path = OWN / "binding_transfer_report_accounting.py"
    require(pin(path)["sha256"] == ACCOUNTING_SHA, "reviewed accounting source changed")
    spec = importlib.util.spec_from_file_location("binding_transfer_config_accounting", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique_pins(values):
    result = {}
    for value in values:
        value = verify_pin(value)
        require(value["path"] not in result or result[value["path"]] == value, "conflicting pin")
        result[value["path"]] = value
    return [result[key] for key in sorted(result)]


def source_closure(entrypoints):
    """Read local Python imports as AST, including literal dynamic imports.

    Imported third-party libraries are NOT loaded. Their installed distribution
    manifests are separately pinned. Relative/computed imports that do not name
    a local own_deck module stay explicit in the reviewed entrypoint sources.
    """
    pending = [Path(path).resolve(strict=True) for path in entrypoints]
    found = set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == "import_module" and node.args
                  and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                names.add(node.args[0].value.split(".")[0])
        for name in names:
            local = OWN / (name + ".py")
            if local.is_file():
                pending.append(local.resolve())
    return [pin(path) for path in sorted(found)]


def environment_pins():
    """Pin installed manifests/entrypoints; do not claim complete wheel-file hashing."""
    require(SITE.is_dir(), "existing cached Python environment required; no installation")
    values = [pin(PYTHON), pin(VENV / "pyvenv.cfg")]
    distributions = {}
    roots = [(SITE, "numpy")]
    for root in CACHED_ARCHIVES:
        require(root.is_dir(), "prior cached dependency archive missing; no installation")
        matches = sorted(root.glob("*.dist-info"))
        require(len(matches) == 1, "one installed distribution per pinned archive required")
        roots.append((root, matches[0].name.split("-")[0]))
    for root, name in roots:
        matches = sorted(root.glob(name + "-*.dist-info"))
        require(len(matches) == 1, "one existing dependency distribution required: " + name)
        record = dict(distribution=str(matches[0]), root=str(root), files=[])
        for basename in ("METADATA", "RECORD", "WHEEL"):
            path = matches[0] / basename
            require(path.is_file(), "installed dependency manifest missing")
            value = pin(path)
            record["files"].append(value)
            values.append(value)
        # Some distributions are single modules or use a lower-case package.
        entries = [root / name / "__init__.py", root / (name + ".py")]
        for entry in entries:
            if not entry.is_file():
                continue
            value = pin(entry)
            values.append(value)
            record["files"].append(value)
        distributions[name] = record
    values.append(pin(ENV_REFERENCE))
    return values, distributions


def stage_descriptors(plan):
    paths = dict(plan=Path(plan).resolve(), old_fit=OLD / "fit-1", old_progress=OLD / "fit-progress.jsonl",
        old_ledger=OLD / "campaign-ledger.jsonl", old_failed_receipt=OLD / "fit-1-stage-receipt.json",
        recover=CAMPAIGN / "recover-1", recovered_result=CAMPAIGN / "recover-1/result.json",
        baselines=CAMPAIGN / "baselines-1", baseline_progress=CAMPAIGN / "baseline-progress.jsonl",
        verify=CAMPAIGN / "verify-result.json", verification_receipt=CAMPAIGN / "verification-receipt.json")
    worker = str(OWN / "binding_transfer_report_recovery.py")
    descriptors = dict(recover=dict(argv=[str(PYTHON), worker, "recover", "--plan", str(paths["plan"]),
        "--fit-dir", str(paths["old_fit"]), "--progress", str(paths["old_progress"]),
        "--failed-ledger", str(paths["old_ledger"]), "--failed-receipt", str(paths["old_failed_receipt"]),
        "--out", str(paths["recover"])],
        outputs=[str(paths["recover"]), str(CAMPAIGN / "recover-1-stage-receipt.json")]))
    descriptors["baselines"] = dict(argv=[str(PYTHON), worker, "baselines", "--plan", str(paths["plan"]),
        "--out", str(paths["baselines"]), "--progress", str(paths["baseline_progress"])],
        outputs=[str(paths["baselines"]), str(paths["baseline_progress"]), str(CAMPAIGN / "baselines-1-stage-receipt.json")])
    descriptors["verify"] = dict(argv=[str(PYTHON), str(OWN / "binding_transfer_report_verify.py"),
        "--plan", str(paths["plan"]), "--fit-dir", str(paths["old_fit"]), "--fit-progress", str(paths["old_progress"]),
        "--baselines-dir", str(paths["baselines"]), "--baseline-progress", str(paths["baseline_progress"]),
        "--out", str(paths["verify"]), "--receipt", str(paths["verification_receipt"]),
        "--recovered-result", str(paths["recovered_result"]), "--failed-fit-ledger", str(paths["old_ledger"]),
        "--failed-fit-receipt", str(paths["old_failed_receipt"])],
        outputs=[str(paths["verify"]), str(paths["verification_receipt"])])
    return descriptors, {key: str(value) for key, value in paths.items()}


def assemble(plan_path, output, write=False):
    plan_path, output = (Path(path).resolve() for path in (plan_path, output))
    require(plan_path == OLD / "prep-1/sealed-fit-plan.json", "reuse the exact immutable sealed plan")
    require(output.parent == CAMPAIGN and not output.exists(), "new saved-report configuration output required")
    require(not LEDGER.exists(), "canonical report ledger already exists; never reset/reconfigure")
    receipt_path = output.with_name(output.stem + "-assembly-receipt.json")
    require(not receipt_path.exists(), "preserve previous assembly receipt")
    A = accounting()
    plan = read(plan_path)
    require(plan["status"] == "sealed-awaiting-root-GO" and len(plan["codes"]) == 7
            and len(plan["train_codes"]) == 5, "unchanged sealed seven-source/fiveTRAIN plan required")
    require(plan["source_sha256"] == pin(OWN / "binding_transfer_fit.py")["sha256"], "frozen learner changed")
    require(plan["config"]["optimizer_updates"] == 5400 and plan["config"]["neural_forwards"] == 5436,
            "saved-fit scientific contract changed")
    descriptors, stage_paths = stage_descriptors(plan_path)
    parent_rows = [json.loads(line) for line in (OLD / "campaign-ledger.jsonl").read_text().splitlines()]
    require(parent_rows[-1]["record_sha256"] == "594157318901334828cfb11009afd6151c7c767f549e2c9fc9513e10e2fae0fe",
            "immutable failed-fit ledger final record differs")
    terminal = parent_rows[-1]["data"]
    require(parent_rows[-1]["event"] == "stage-finish" and terminal["stage"] == "fit"
            and terminal["status"] == "failed" and terminal["charged"]["seconds"] == 60.
            and terminal["charged"]["neural_forwards"] == 5436 and terminal["charged"]["optimizer_updates"] == 5400
            and terminal["observed"]["neural_forwards"] is None and terminal["observed"]["optimizer_updates"] is None,
            "failed fit observations/charges must stay unchanged")
    for descriptor in descriptors.values():
        A.validate_descriptor(descriptor)
        require(all(not Path(path).exists() for path in descriptor["outputs"]), "preserve all existing outputs")
    entrypoints = [OWN / (name + ".py") for name in (
        "binding_transfer_report_accounting", "binding_transfer_report_recovery", "binding_transfer_report_verify",
        "binding_transfer_repair_baselines", "binding_transfer_fit", "binding_transfer_baselines",
        "public_input_binding_model_v1", "effect_identifiability_fit", "whole_card_encoder", "learning_sanity_data")]
    static = source_closure(entrypoints)
    static.extend(pin(path) for path in sorted(OWN.glob("test_binding_transfer*.py")))
    for path in (Path(__file__), CAMPAIGN / "test_assemble_binding_transfer_config.py",
        OWN / "BINDING_TRANSFER_REPORT_RECOVERY_PROTOCOL.md", OWN / "BINDING_TRANSFER_REPAIR_PROTOCOL.md",
        OWN / "BINDING_TRANSFER_V2_PROTOCOL.md", OWN / "BINDING_TRANSFER_LEARNER_PROTOCOL.md",
        OWN / "BINDING_TRANSFER_PREREGISTRATION.md", OWN / "test_public_input_binding_model_v1.py",
        plan_path, OLD / "assemble_binding_transfer_config.py", OLD / "campaign-config.json",
        OLD / "campaign-ledger.jsonl", OLD / "fit-1-stage-receipt.json", OLD / "fit-progress.jsonl",
        Path(plan["dataset"]), Path(plan["manifest"])):
        static.append(pin(path))
    # No NPZ loading or inference: preserve every saved old-fit file byte-for-byte.
    static.extend(pin(path) for path in sorted((OLD / "fit-1").rglob("*")) if path.is_file())
    static.extend(verify_pin(value) for value in plan["pins"])
    protection = read(A.PRESERVATION["path"])
    static.append(verify_pin(A.PRESERVATION))
    for value in protection["protected_files"] + protection["additional_protected_artifacts"]:
        static.append(verify_pin(value))
    environment, installed = environment_pins()
    source_pins = unique_pins([*static, *environment])
    config = A.make_config(descriptors, source_pins, sealed=True)
    require(tuple(config["stages"]) == STAGE_ORDER and config["caps"]["seconds"] == 13.
            and all(config["caps"][key] == 0 for key in ("native_applies", "neural_forwards", "optimizer_updates")),
            "saved-report stage must have zero native, neural and update allowances")
    config.update(stage_input_paths=stage_paths,
        runtime_environment=dict(PYTHONPATH=os.pathsep.join(str(p) for p in (OWN, *CACHED_ARCHIVES, SITE)),
            PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1", NUMEXPR_NUM_THREADS="1"),
        provenance=dict(assembler=pin(__file__), inherited_assembler=pin(OLD / "assemble_binding_transfer_config.py"),
            immutable_failed_fit_ledger=pin(OLD / "campaign-ledger.jsonl"),
            immutable_failed_fit_receipt=pin(OLD / "fit-1-stage-receipt.json"),
            immutable_failed_fit_progress=pin(OLD / "fit-progress.jsonl"),
            saved_plan=pin(plan_path), saved_predictions_only=True, failed_fit_charge_unchanged=True,
            no_new_neural_or_optimizer_execution=True,
            python=dict(requested_venv=str(VENV), resolved_executable=pin(PYTHON),
                installed_dependency_manifests=installed, scope="Cached manifests and module entries pinned; not a complete installed-wheel byte audit"),
            execution_scope="Configuration metadata only; no ledger initialization, report recovery, numerical fit, model or native execution"))
    A.validate_config(config)
    for expected in source_pins:
        verify_pin(expected)
    require(not LEDGER.exists(), "report ledger unexpectedly appeared")
    if write:
        A.verify_links(config)
        exclusive_json(output, config)
        result = dict(schema=SCHEMA, status="sealed-configuration-written-no-ledger-or-execution",
            config=pin(output), source=pin(__file__), immutable_pin_count=len(config["pins"]),
            stages=list(config["stage_descriptors"]), canonical_ledger=str(LEDGER), ledger_initialized=False,
            native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0,
            paid_jobs=0, scientific_execution=False)
        exclusive_json(receipt_path, result)
    else:
        result = dict(schema=SCHEMA, status="preview-only-no-writes", source=pin(__file__),
            expected_output=str(output), immutable_pin_count=len(config["pins"]),
            stage_descriptors=descriptors, stage_input_paths=stage_paths,
            runtime_environment=config["runtime_environment"], ledger_initialized=False, scientific_execution=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=OLD / "prep-1/sealed-fit-plan.json")
    parser.add_argument("--out", type=Path, default=CAMPAIGN / "campaign-config.json")
    parser.add_argument("--write", action="store_true", help="Root only: exclusively write metadata; no ledger initialization or saved-output analysis")
    args = parser.parse_args()
    print(json.dumps(assemble(args.plan, args.out, args.write), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
