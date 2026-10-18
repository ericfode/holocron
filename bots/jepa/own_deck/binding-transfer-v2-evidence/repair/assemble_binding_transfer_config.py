"""Metadata-only assembler for a NEW zero-native repair allocation.

Consumes the immutable successful native48 receipt/journal and prior prepared
program bank. Root alone runs --write after source freeze. No initialization,
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
OLD = CAMPAIGN.parent / "binding-transfer-v2"
LEDGER = CAMPAIGN / "campaign-ledger.jsonl"
VENV = Path("/Users/ericfode/src/crown-jepa/.venv")
PYTHON = (VENV / "bin/python").resolve()
SITE = VENV / "lib/python3.11/site-packages"
CACHED_ARCHIVES = tuple(Path("/Users/ericfode/.cache/uv/archive-v0") / name for name in (
    "rehTsShR29rpWi8Dqz5BL", "ntYsJgeLWxSB0rhe6n9sh", "5i8dYw1S9c5zrvrF0rCIy",
    "C7W22kpzl1cAe-Hdx0N-2", "F1isPlsf9ooQ4EGhGPl5V", "PVyRmcnszTpMFeVdyuyJs",
    "fDmWyEr9slZLLcHdlujql", "khxszcG0X4WuYCMH_DEdE", "7h7hIgcQT6GjZZGqqRrhM"))
ENV_REFERENCE = TASK / "experiments/effect-identifiability-v2/seal-preflight-command-v2.json"
ACCOUNTING_SHA = "761b62596c76ed3f61dfee1f348fdd54a41a8e92d756eade8ecb90b3f9aa96bb"
SCHEMA = "jepa-binding-transfer-repair-configuration-assembly/1"
STAGE_ORDER = ("prep", "fit", "baselines", "verify")


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
    path = OWN / "binding_transfer_repair_accounting.py"
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


def stage_descriptors(prepared):
    paths = dict(native_receipt=OLD / "native-attempt-1/native-receipt.json",
        journal=OLD / "native-attempt-1/native-transitions.jsonl", native_plan=OLD / "native-plan.json",
        prepared=Path(prepared).resolve(), prep=CAMPAIGN / "prep-1",
        sealed=CAMPAIGN / "prep-1/sealed-fit-plan.json", fit=CAMPAIGN / "fit-1",
        fit_progress=CAMPAIGN / "fit-progress.jsonl", baselines=CAMPAIGN / "baselines-1",
        baseline_progress=CAMPAIGN / "baseline-progress.jsonl", verify=CAMPAIGN / "verify-result.json",
        verification_receipt=CAMPAIGN / "verification-receipt.json")
    worker = str(OWN / "binding_transfer_repair.py")
    descriptors = dict(prep=dict(argv=[str(PYTHON), worker, "prep",
        "--native-receipt", str(paths["native_receipt"]), "--journal", str(paths["journal"]),
        "--native-plan", str(paths["native_plan"]), "--prepared", str(paths["prepared"]),
        "--out", str(paths["prep"])], outputs=[str(paths["prep"]), str(CAMPAIGN / "prep-1-stage-receipt.json")]))
    for stage, output, progress in (("fit", "fit", "fit_progress"), ("baselines", "baselines", "baseline_progress")):
        descriptors[stage] = dict(argv=[str(PYTHON), worker, stage, "--plan", str(paths["sealed"]),
            "--out", str(paths[output]), "--progress", str(paths[progress])],
            outputs=[str(paths[output]), str(paths[progress]), str(CAMPAIGN / (paths[output].name + "-stage-receipt.json"))])
    descriptors["verify"] = dict(argv=[str(PYTHON), str(OWN / "binding_transfer_repair_verify.py"),
        "--plan", str(paths["sealed"]), "--fit-dir", str(paths["fit"]), "--fit-progress", str(paths["fit_progress"]),
        "--baselines-dir", str(paths["baselines"]), "--baseline-progress", str(paths["baseline_progress"]),
        "--out", str(paths["verify"]), "--receipt", str(paths["verification_receipt"])],
        outputs=[str(paths["verify"]), str(paths["verification_receipt"])])
    return descriptors, {key: str(value) for key, value in paths.items()}


def assemble(prepared, routing_path, output, write=False):
    prepared, routing_path, output = (Path(path).resolve() for path in (prepared, routing_path, output))
    require(output.parent == CAMPAIGN and not output.exists(), "new repair configuration output required")
    require(prepared == OLD / "learner-prepared-v1.json", "reuse the exact old prepared program metadata")
    require(routing_path == CAMPAIGN / "repair-routing-v1.json", "one new repair route metadata path required")
    require(not LEDGER.exists(), "canonical repair ledger already exists; never reset/reconfigure")
    receipt_path = output.with_name(output.stem + "-assembly-receipt.json")
    require(not receipt_path.exists(), "preserve existing assembly receipt")
    A = accounting()
    public_plan, routing = read(prepared), read(routing_path)
    require(public_plan["status"] == "prepared-no-neural-execution"
            and len(public_plan["codes"]) == 7 and len(public_plan["train_codes"]) == 5,
            "reuse exact seven-source/fiveTRAIN public prepared bank")
    require(public_plan["source_sha256"] == pin(OWN / "binding_transfer_fit.py")["sha256"], "frozen learner changed")
    descriptors, stage_paths = stage_descriptors(prepared)
    plan = Path(stage_paths["native_plan"])
    allowed_plan_paths = {plan, OWN / "binding_transfer_native_collector/collection-plan.json"}
    require(Path(public_plan["native_plan"]).resolve() in allowed_plan_paths, "unexpected original prelabel plan path")
    for path in allowed_plan_paths:
        value = pin(path)
        require(value["sha256"] == "0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f"
                and value["bytes"] == 107878, "unchanged scientific plan bytes required")
    require(read(plan) == read(public_plan["native_plan"]), "original prelabel and reused native plan bodies differ")
    require(routing["schema"] == "jepa-binding-transfer-repair-routing/1"
            and routing["prepared"] == pin(prepared) and routing["native_plan"] == pin(plan)
            and routing["accounting"] == pin(OWN / "binding_transfer_repair_accounting.py")
            and routing["wrapper"] == pin(OWN / "binding_transfer_repair.py")
            and routing["ledger_path"] == str(LEDGER), "new repair route/source differs")
    for expected in routing["science"]:
        verify_pin(expected)
    for descriptor in descriptors.values():
        A.validate_descriptor(descriptor)
        require(all(not Path(path).exists() for path in descriptor["outputs"]), "preserve all existing stage outputs")
    entrypoints = [OWN / (name + ".py") for name in (
        "binding_transfer_repair_accounting", "binding_transfer_repair", "binding_transfer_repair_baselines",
        "binding_transfer_repair_verify", "binding_transfer_data_v2", "binding_transfer_data",
        "binding_transfer_fit", "binding_transfer_prep", "binding_transfer_baselines",
        "public_input_binding_model_v1", "effect_identifiability_fit", "whole_card_encoder", "learning_sanity_data")]
    static = source_closure(entrypoints)
    static.extend(pin(path) for path in sorted(OWN.glob("test_binding_transfer*.py")))
    for path in (Path(__file__), CAMPAIGN / "test_assemble_binding_transfer_config.py",
        OWN / "BINDING_TRANSFER_REPAIR_PROTOCOL.md", OWN / "BINDING_TRANSFER_V2_PROTOCOL.md",
        OWN / "BINDING_TRANSFER_V2_ROUTING.md", OWN / "BINDING_TRANSFER_LEARNER_PROTOCOL.md",
        OWN / "BINDING_TRANSFER_PREREGISTRATION.md", OWN / "test_public_input_binding_model_v1.py",
        prepared, routing_path, OLD / "prelabel-routing-v1.json", OLD / "assemble_binding_transfer_config.py",
        OLD / "campaign-config.json", OLD / "campaign-ledger.jsonl", plan,
        Path(public_plan["native_plan"]), Path(stage_paths["native_receipt"]), Path(stage_paths["journal"])):
        static.append(pin(path))
    static.extend(verify_pin(value) for value in public_plan["pins"])
    protection = read(A.PRESERVATION["path"])
    static.append(verify_pin(A.PRESERVATION))
    for value in protection["protected_files"] + protection["additional_protected_artifacts"]:
        static.append(verify_pin(value))
    environment, installed = environment_pins()
    source_pins = unique_pins([*static, *environment])
    config = A.make_config(descriptors, source_pins, sealed=True)
    require(tuple(config["stages"]) == STAGE_ORDER and config["caps"]["native_applies"] == 0
            and config["caps"]["seconds"] == 75., "repair must have four zero-native stages and75seconds")
    config.update(stage_input_paths=stage_paths,
        runtime_environment=dict(PYTHONPATH=os.pathsep.join(str(p) for p in (OWN, *CACHED_ARCHIVES, SITE)),
            PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1", NUMEXPR_NUM_THREADS="1"),
        provenance=dict(assembler=pin(__file__), inherited_assembler=pin(OLD / "assemble_binding_transfer_config.py"),
            reused_prepared=pin(prepared), new_repair_route=pin(routing_path),
            actual_original_prelabel_plan=pin(public_plan["native_plan"]), reused_native_plan=pin(plan),
            successful_native_receipt=pin(stage_paths["native_receipt"]), successful_native_journal=pin(stage_paths["journal"]),
            failed_preparation_charge_retained=True, native_collection_reused=True, program_bank_recomputed=False,
            python=dict(requested_venv=str(VENV), resolved_executable=pin(PYTHON),
                installed_dependency_manifests=installed, scope="Cached manifests and module entries pinned; not a complete installed-wheel byte audit"),
            execution_scope="Configuration-only repair metadata; no ledger initialization, build, native application, conversion, neural call or fit"))
    A.validate_config(config)
    for expected in source_pins:
        verify_pin(expected)
    require(not LEDGER.exists(), "repair ledger unexpectedly appeared")
    if write:
        A.verify_links(config)
        exclusive_json(output, config)
        result = dict(schema=SCHEMA, status="sealed-configuration-written-no-ledger-or-execution",
            config=pin(output), source=pin(__file__), immutable_pin_count=len(config["pins"]),
            stages=list(config["stage_descriptors"]), canonical_ledger=str(LEDGER),
            ledger_initialized=False, native_applies=0, neural_forwards=0, optimizer_updates=0,
            numerical_fits=0, paid_jobs=0, science_executed=False)
        exclusive_json(receipt_path, result)
    else:
        result = dict(schema=SCHEMA, status="preview-only-no-writes", source=pin(__file__),
            expected_output=str(output), immutable_pin_count=len(config["pins"]), stage_descriptors=descriptors,
            stage_input_paths=stage_paths, runtime_environment=config["runtime_environment"],
            ledger_initialized=False, science_executed=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=OLD / "learner-prepared-v1.json")
    parser.add_argument("--routing", type=Path, default=CAMPAIGN / "repair-routing-v1.json")
    parser.add_argument("--out", type=Path, default=CAMPAIGN / "campaign-config.json")
    parser.add_argument("--write", action="store_true", help="Root only: exclusively write metadata; never initializes a ledger or starts a stage")
    args = parser.parse_args()
    print(json.dumps(assemble(args.prepared, args.routing, args.out, args.write), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
