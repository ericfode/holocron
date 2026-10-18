"""Versioned linked recovery accounting; preparation never initializes a ledger.

Stdlib only. Historical journals are read-only parents. Every actual stage uses
one canonical nonblocking lease from before input checks/imports through cleanup.
An unresolved cleanup leaves the durable start pending and blocks later stages.
Copied from the frozen 51ad accounting core; only versioned routes, carried
totals and explicit closed-parent/preservation checks differ. Old files stay put.
"""
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time


HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2].parent
CAMPAIGN = TASK / "experiments/binding-transfer-v2"
LEDGER = CAMPAIGN / "campaign-ledger.jsonl"
SCHEMA = "jepa-binding-transfer-next-accounting/1"
CONFIG_SCHEMA = "jepa-binding-transfer-next-config/1"
PRESERVATION = dict(path=str(TASK / "experiments/next-cycle-preservation-v1/protected-before.json"),
    sha256="9c9106f7184a8135db34a02125f6f702a2cb0303f71de99156697928787444bf", bytes=27822)
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")
STAGES = {
    "build": dict(seconds=15., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "native": dict(seconds=30., native_applies=48, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "prep": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "fit": dict(seconds=60., native_applies=0, neural_forwards=5436, optimizer_updates=5400, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "baselines": dict(seconds=10., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=64, paid_jobs=0, paid_spend_usd=0.),
    "verify": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
}
CAPS = dict(seconds=125., native_applies=48, neural_forwards=5436, optimizer_updates=5400,
            numerical_fits=64, paid_jobs=0, paid_spend_usd=0., cpu_workers=1, rss_bytes=1024 ** 3)
PARENT = dict(scope="Binding v1+v2+supplement, failed binding-transfer-v1 and zero-call fixture debugging; PR36/37 separately linked",
    charged_native_applies=160, charged_seconds=111.76578145672102, observed_native_applies=None,
    verified_v2_native_applies=32, v1_static_forensic_engine_applies=0,
    pr36_pr37_optimizer_updates=1900, pr36_pr37_neural_forwards=1917,
    pr36_pr37_native_applies=87, pr36_pr37_closed_form_head_fits=32,
    paid_spend_usd=0., cumulative_native_ceiling=208, cumulative_seconds_ceiling=236.76578145672102,
    historical_modal_ceiling_usd=100., historical_modal_minimum_reserve_usd=25.)
GUARD = dict(cpu_workers=1, rss_bytes=1024 ** 3)

# Frozen inherited bytes and closed journals; original source-path declarations
# inside historical manifests are provenance, never rechecked as current code.
INHERITED_CORE = {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck/binding_transfer_accounting.py',
 'sha256': '51ad01b175d5367e27b5e0f8eebb91d2a417f73069cfdd865269cff714f012cd',
 'bytes': 25321}
CLOSED_PARENT_JOURNALS = [{'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/effect-identifiability-v2/campaign-ledger.jsonl',
          'sha256': 'e69410d8caa5c5219f46107a6238e4c811125c65cead3db15d970b9a25133259',
          'bytes': 245814},
  'records': 14,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': 'a4ebccf072b203af8242004155be55dd0f8b34ba4ec68532aa12d172986a1cf0',
  'final_event': 'attempt-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/learning-sanity-v1/campaign-ledger.jsonl',
          'sha256': '86a3970efc4cba8f34bc01dad6fcbd45761cd1d9f619a6bbfc0ac3c2c182aa19',
          'bytes': 10069},
  'records': 3,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': 'f8acbc596c98df8e70e1fe333deb73375d65a6a1c36827c0e5d757b914f38fbc',
  'final_event': 'attempt-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/learning-sanity-v1/analysis-ledger.jsonl',
          'sha256': '8821c9ef54ad2e3749ff5f7d598e633a9453669fb14cdc973359e613af36dd62',
          'bytes': 31405},
  'records': 4,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': 'c185302f16f9135ab42a559ca4e4be2e7b58c19d4ebc5f8c0812d3a3200a7eea',
  'final_event': 'finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v1/campaign-ledger.jsonl',
          'sha256': '1b0c327d468d2553454b09e95eeb58287b42c75790510e2ec957968ba9929b3b',
          'bytes': 25221},
  'records': 5,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': '4be4736ee8c9bb8f0105bec597ca863d01626071b3de97991e8fd9feb3fcc953',
  'final_event': 'attempt-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v2/campaign-ledger.jsonl',
          'sha256': '7e23b61f5defc3f07199b87693dcfc36a4a80e3ca8f795a473e8c0d8bf7ede05',
          'bytes': 42610},
  'records': 9,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': '3b52469f736894260f3cdb6494231d278526924cd6ba78e18e0277d97f15d0e1',
  'final_event': 'attempt-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v2/supplemental-verification-ledger.jsonl',
          'sha256': 'a5701e1b3ac3342de0f72299481cdedf9c22c9334d19d606fb58148330a424f1',
          'bytes': 8883},
  'records': 2,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': 'f42dd06ac438739ead55d1cae05faa7d477b7bbd51e9b00c7be12fc073365b45',
  'final_event': 'finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v1/campaign-ledger.jsonl',
          'sha256': 'ffb01088cc7c456b84e1c23a38720e5cfe060869e878236ec065d409fb37a4f2',
          'bytes': 217862},
  'records': 5,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': '87c79ce95df5fe332f8c9f634427e4e3b7dcb083c52acbee5258616cbeb05d0f',
  'final_event': 'stage-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-fixture-validation-v1/campaign-ledger.jsonl',
          'sha256': 'f68f7220a09812d80fc2dd64dba34737e3926f4caab8c3b3b909388cbad511d3',
          'bytes': 79866},
  'records': 5,
  'first_previous_sha256': None,
  'final_record_sha256': '6321739736b349771bace38bdd607545c05c59fe4dd18f4d0978b62c1f365f30',
  'final_event': 'stage-finish'}]
PARENT_ARTIFACT_PINS = [{'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/preservation.json',
  'sha256': '3abd68737a7714fc9efcde4fdc90a78e7f6808386bc1b863a0d7db0231dd0384',
  'bytes': 9037},
 {'bytes': 17135056,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target/debug/binding-transfer-native-collector',
  'sha256': 'f7bdbbef31a08aaeb4c3fb28be04bcece3a82782849fbc829b98ba59922dbaeb'},
 {'bytes': 17204960,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target/debug/binding-transfer-fixture-validator',
  'sha256': 'b87a950a132f0e88b1edf7a9f7d83257306f68cc2d15184f11271df3691060ad'},
 {'bytes': 630,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/Cargo.toml',
  'sha256': 'e83ef1ce6ac4cce5b9b0e519c748f81fb12683bff95ad7e17f8ea69d702a6aba'},
 {'bytes': 9567,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/Cargo.lock',
  'sha256': '1e807c215b0bbd7932bfc8bff6b3e465ec00db7d96df1a5f09541c8e48952b6a'},
 {'bytes': 30162,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/src/main.rs',
  'sha256': '6355cde9d6ec5bfb51feab133b3d7fbf352b2edb392bba74187d91c7ff00d61c'},
 {'bytes': 161,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/src/fixture_validator.rs',
  'sha256': '411dec510934d0973d3fd9a9f23ec373d5786724eb3aae395927a256c2e9222b'},
 {'bytes': 107878,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/collection-plan.json',
  'sha256': '0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f'},
 {'bytes': 4465,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/native-collector/test_fixture_validation.py',
  'sha256': 'dfd61f748b7877886dab538f25d4282b5056f926055e9c888f72c25f273ed926'},
 {'bytes': 45330,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/config.json',
  'sha256': '5886e15ab9fe09082357351b297e333093e4eeee0224892f2a06dcab7b494192'},
 {'bytes': 79866,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/campaign-ledger.jsonl',
  'sha256': 'f68f7220a09812d80fc2dd64dba34737e3926f4caab8c3b3b909388cbad511d3'},
 {'bytes': 41724,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/validation-source-manifest.json',
  'sha256': '5fd4783d9d8e595bdd974343dfedb960a9f5e871bffc789271b7d6881f75391d'},
 {'bytes': 44093,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/build-1-stage-receipt.json',
  'sha256': 'd27f2019683599c92c569e530889a7828b6a198791dd9811d377cb67abfd32c8'},
 {'bytes': 45447,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/validate-1-stage-receipt.json',
  'sha256': '163278787fbb94264105617114784b2f8a119eb40e9f38a9ff6cf6c9189f4d39'},
 {'bytes': 828113,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/validate-1/validation.json',
  'sha256': '8942b37d64ec098ebccd0981884ea2938b775649dc933c3095af57921442d1bf'},
 {'bytes': 63082,
  'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source/fixture-validation/closure-audit.json',
  'sha256': '6f9974fee431558068faaf65ebb756d0050a0e07d6d62b5e5fcb500181559b67'},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v1/campaign-config.json',
  'sha256': 'af9c88e239fbb62be22b4b78145b1160411dc7d9e0225edc09c226b4a727ca7c',
  'bytes': 102809},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v1/postmortem-closure-audit.json',
  'sha256': '74b120d3af7e612e3fb92ecc85e1c83cb056d56b66425c8e2265318530eb219f',
  'bytes': 60572},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/publication-sources/binding-transfer-v1-failed-archive/manifest.json',
  'sha256': '5cd1e0bac1f7f04965e464e945e368777711a1704638d9e650f24af5105426ae',
  'bytes': 150503},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/publication-sources/binding-transfer-v1-failed-archive/evidence-index.json',
  'sha256': 'ac672676f76305294afd44940707ea5b08ad69b921b8e51f06e0e1f061ff749a',
  'bytes': 205624}]
IMMUTABLE_PARENT_ROOTS = ['/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-fixture-validation-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/effect-identifiability-v2',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/learning-sanity-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v2',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/publication-sources/binding-transfer-v1-failed-archive']


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def verify_pin(expected):
    require(set(expected) == {"path", "sha256", "bytes"} and Path(expected["path"]).is_absolute(),
            "absolute path/SHA256/bytes source pin required")
    require(pin(expected["path"]) == expected, "changed pinned input: " + expected["path"])


def number(value, integral=False):
    require(type(value) in ((int,) if integral else (int, float)) and math.isfinite(value) and value >= 0,
            "finite nonnegative " + ("integer" if integral else "number") + " required")
    return value


def counts(value, unknown=False):
    require(set(value) == set(COUNTERS), "all exposure counter keys required")
    for key, amount in value.items():
        if unknown and amount is None:
            continue
        number(amount, key != "paid_spend_usd")
    return value


def zero_counts():
    return {key: 0. if key == "paid_spend_usd" else 0 for key in COUNTERS}


def guard_environment(target_dir):
    """Description only; caller installs it before any numerical import/build."""
    return dict(CARGO_BUILD_JOBS="1", CARGO_PROFILE_DEV_DEBUG="0", CARGO_PROFILE_DEV_INCREMENTAL="false",
        CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(Path(target_dir).resolve()),
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
        VECLIB_MAXIMUM_THREADS="1", NUMEXPR_NUM_THREADS="1")


def validate_descriptor(value):
    require(isinstance(value, dict) and set(value) == {"argv", "outputs"}, "fixed argv/output descriptor required")
    require(isinstance(value["argv"], list) and value["argv"] and all(isinstance(s, str) and s for s in value["argv"]),
            "nonempty exact argv required")
    require(Path(value["argv"][0]).is_absolute(), "absolute main entrypoint required")
    require(isinstance(value["outputs"], list) and len(set(value["outputs"])) == len(value["outputs"])
            and all(isinstance(p, str) and Path(p).is_absolute() for p in value["outputs"]), "unique absolute declared output paths required")


def validate_config(config):
    require(config.get("schema") == CONFIG_SCHEMA and config.get("status") == "sealed-awaiting-root-GO", "sealed new configuration required")
    require(config.get("ledger_path") == str(LEDGER.resolve()) and config.get("source") == pin(__file__), "fixed canonical ledger and exact accounting source required")
    require(config.get("stages") == STAGES and config.get("caps") == CAPS and config.get("parent") == PARENT,
            "exact frozen allocations and carried accounting required")
    require(config.get("preservation") == PRESERVATION and config.get("guard") == GUARD, "exact protection and guard contract required")
    require(set(config.get("stage_descriptors", {})) == set(STAGES), "all six frozen stage descriptors required")
    for descriptor in config["stage_descriptors"].values():
        validate_descriptor(descriptor)
    require(isinstance(config.get("pins"), list), "explicit frozen source/input pins required")
    require(len({p["path"] for p in config["pins"]}) == len(config["pins"]), "duplicate frozen input paths")
    require(config.get("fit_success_counts") == dict(optimizer_updates=5400, neural_forwards=5436,
            training_forwards=5400, evaluation_forwards=36), "fixed complete fit quota required")
    require(config.get("inherited_core") == INHERITED_CORE
            and config.get("closed_parent_journals") == CLOSED_PARENT_JOURNALS
            and config.get("parent_artifact_pins") == PARENT_ARTIFACT_PINS,
            "exact immutable inherited core and eight closed-parent links required")


def verify_closed_parent(link):
    """Verify saved hashes/chains without importing any older accounting code."""
    verify_pin(link["pin"])
    rows = [json.loads(line) for line in Path(link["pin"]["path"]).read_text().splitlines()]
    require(len(rows) == link["records"], "closed parent record count changed")
    previous = link["first_previous_sha256"]
    for i, row in enumerate(rows):
        body = {key: value for key, value in row.items() if key != "record_sha256"}
        require(row["sequence"] == i and row["previous_sha256"] == previous
                and row["record_sha256"] == digest(body), "closed parent hash chain changed")
        previous = row["record_sha256"]
    require(previous == link["final_record_sha256"] and rows[-1]["event"] == link["final_event"],
            "closed parent final record changed")


def verify_failed_archive():
    """Check immutable stored files offline; never follow old original paths."""
    root = TASK / "experiments/publication-sources/binding-transfer-v1-failed-archive"
    manifest = json.loads((root / "manifest.json").read_text())
    for value in manifest["files"]:
        relative = Path(value["url"])
        require(not relative.is_absolute() and ".." not in relative.parts, "archive path traversal")
        path = (root / relative).resolve()
        require(path.is_relative_to(root.resolve()), "archive path outside immutable root")
        verify_pin(dict(path=str(path), sha256=value["sha256"], bytes=value["bytes"]))


def verify_links(config):
    """Byte-only checks, never imports/executes protected/model/native sources."""
    verify_pin(PRESERVATION)
    before = json.loads(Path(PRESERVATION["path"]).read_text())
    protected = before["protected_files"] + before["additional_protected_artifacts"]
    seen = {}
    for value in protected:
        expected = {key: value[key] for key in ("path", "sha256", "bytes")}
        require(expected["path"] not in seen or seen[expected["path"]] == expected, "conflicting protected byte pins")
        if expected["path"] not in seen:
            verify_pin(expected)
        seen[expected["path"]] = expected
    prior = before["closed_current_study_accounting"]
    # The original80-file snapshot predates the failed v1 and zero-call debug.
    # Validate its original112/79.267 values independently of the new160+D carry.
    require(prior["charged_native_applies"] == 112
            and prior["total_charged_seconds"] == 79.26753083174117
            and prior["observed_native_applies"] is None and prior["observed_v2_native_applies"] == 32,
            "carried failed reservations/unknown observation changed")
    verify_pin(INHERITED_CORE)
    for link in CLOSED_PARENT_JOURNALS:
        verify_closed_parent(link)
    for expected in PARENT_ARTIFACT_PINS:
        verify_pin(expected)
    verify_failed_archive()
    for expected in config["pins"]:
        verify_pin(expected)


def make_config(stage_descriptors, pins, sealed=False):
    """Return data only. No configuration file, journal or allowance is created."""
    merged = {}
    inherited = [INHERITED_CORE, *(link["pin"] for link in CLOSED_PARENT_JOURNALS), *PARENT_ARTIFACT_PINS]
    for expected in [*pins, *inherited]:
        require(expected["path"] not in merged or merged[expected["path"]] == expected, "conflicting inherited/frozen input pin")
        merged[expected["path"]] = copy.deepcopy(expected)
    config = dict(schema=CONFIG_SCHEMA, status="sealed-awaiting-root-GO" if sealed else "draft-awaiting-freeze",
        ledger_path=str(LEDGER.resolve()), source=pin(__file__), preservation=copy.deepcopy(PRESERVATION),
        stages=copy.deepcopy(STAGES), caps=copy.deepcopy(CAPS), parent=copy.deepcopy(PARENT), guard=copy.deepcopy(GUARD),
        stage_descriptors=copy.deepcopy(stage_descriptors), pins=[merged[key] for key in sorted(merged)],
        inherited_core=copy.deepcopy(INHERITED_CORE), closed_parent_journals=copy.deepcopy(CLOSED_PARENT_JOURNALS),
        parent_artifact_pins=copy.deepcopy(PARENT_ARTIFACT_PINS),
        fit_success_counts=dict(optimizer_updates=5400, neural_forwards=5436, training_forwards=5400, evaluation_forwards=36),
        scope="New linked cycle only; prior journals remain immutable; no credits/resets")
    if sealed:
        validate_config(config)
    return config


def chain(rows):
    previous = "0" * 64
    for i, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        require(row.get("schema") == SCHEMA and row.get("sequence") == i and row.get("previous_sha256") == previous
                and row.get("record_sha256") == digest(body), "damaged canonical journal hash chain; never reset")
        previous = row["record_sha256"]
    return previous


def read_rows(stream):
    stream.seek(0)
    return [json.loads(line) for line in stream if line.strip()]


def state(rows):
    chain(rows)
    result = dict(config=None, pending=None, seen_stages=[], completed_stages=[], failures=0,
        charged=dict(seconds=0., **zero_counts()), observed=dict(seconds=0., **zero_counts()),
        durable_prefix=zero_counts(), violated=False)
    for i, row in enumerate(rows):
        event, data = row["event"], row["data"]
        if i == 0:
            require(event == "initialized", "single initial configuration record required")
            validate_config(data["config"])
            result["config"] = data["config"]
        elif event == "stage-start":
            stage = data["stage"]
            require(result["pending"] is None and not result["violated"], "pending/violated stage blocks start")
            require(stage in STAGES and stage not in result["seen_stages"] and data["reservation"] == STAGES[stage], "once-only exact stage reservation required")
            previous = list(STAGES)[:list(STAGES).index(stage)]
            require(result["completed_stages"] == previous, "all prior stages must have completed successfully")
            require(data["metadata"]["argv"] == result["config"]["stage_descriptors"][stage]["argv"]
                    and data["metadata"]["outputs"] == result["config"]["stage_descriptors"][stage]["outputs"], "stage differs from frozen command/output descriptor")
            require(data["metadata"].get("guard") == GUARD and isinstance(data["metadata"].get("input_pins"), list),
                    "exact single-worker/RSS guard and input pins required")
            number(data["started_monotonic_seconds"])
            for key, amount in data["reservation"].items():
                require(result["charged"][key] + amount <= CAPS[key], "full stage reservation exceeds new allowance")
            result["pending"] = data
            result["seen_stages"].append(stage)
        elif event == "pending-failure":
            require(result["pending"] is not None and data["stage"] == result["pending"]["stage"], "failure note requires matching pending stage")
            result["pending"] = dict(result["pending"], unresolved_failure=data)
        elif event == "stage-finish":
            pending = result["pending"]
            require(pending is not None and data["stage"] == pending["stage"], "finish requires matching pending stage")
            require(data["status"] in ("completed", "failed") and data["cleanup_verified"] is True
                    and data["execution_ended"] is True, "known ended execution and owned cleanup required; otherwise leave pending")
            require("unresolved_failure" not in pending, "uncertain cleanup note cannot be cleared by ordinary finish")
            observed = counts(data["observed"], unknown=True)
            number(data["active_seconds"])
            require(type(data["observed_verified"]) is bool, "explicit observation knownness required")
            failed = data["status"] == "failed"
            require(failed or (data["observed_verified"] and all(observed[k] is not None for k in COUNTERS)), "successful completion requires exact counters")
            if not failed and pending["stage"] in ("native", "fit", "baselines"):
                measured = data.get("counter_measurements")
                require(isinstance(measured, dict) and data.get("counter_proof") is not None,
                        "completed exposure stage requires recorded durable counter proof")
                require(all(observed[k] == measured[k] for k in COUNTERS if k in measured), "saved measured/observed count differs")
                if pending["stage"] == "fit":
                    require(measured == result["config"]["fit_success_counts"], "complete fixed fit counts required")
            expected_charge = dict(seconds=max(data["active_seconds"], pending["reservation"]["seconds"]) if failed else data["active_seconds"])
            for key in COUNTERS:
                amount = observed[key]
                expected_charge[key] = max(amount or 0, pending["reservation"][key]) if failed else amount
                result["durable_prefix"][key] += amount or 0
                if result["observed"][key] is not None:
                    result["observed"][key] = (result["observed"][key] + amount if data["observed_verified"] and amount is not None
                        else None if pending["reservation"][key] else result["observed"][key])
            require(data["charged"] == expected_charge, "failed full-reservation/actual charge changed")
            for key, amount in expected_charge.items():
                result["charged"][key] += amount
                result["violated"] |= result["charged"][key] > CAPS[key] or amount > pending["reservation"][key]
            result["observed"]["seconds"] += data["active_seconds"]
            if not failed:
                require(all(data["charged"][k] <= pending["reservation"][k] for k in expected_charge), "completed stage must fit exact allocation")
                result["completed_stages"].append(pending["stage"])
            result["failures"] += int(failed)
            result["pending"] = None
        else:
            raise ValueError("unsupported journal event; no credit, reset, retry or generic recovery event")
    conservative = copy.deepcopy(result["charged"])
    if result["pending"]:
        for key, amount in result["pending"]["reservation"].items():
            conservative[key] += amount
    result["conservative_including_pending"] = conservative
    result["cumulative"] = dict(charged_native_applies=PARENT["charged_native_applies"] + conservative["native_applies"],
        charged_seconds=PARENT["charged_seconds"] + conservative["seconds"], observed_native_applies=None,
        observed_new_native_applies=result["observed"]["native_applies"],
        prior_verified_v2_native_applies=32, prior_v1_static_forensic_engine_applies=0)
    result["violated"] |= result["cumulative"]["charged_native_applies"] > PARENT["cumulative_native_ceiling"] or result["cumulative"]["charged_seconds"] > PARENT["cumulative_seconds_ceiling"]
    result["last_record_sha256"] = rows[-1]["record_sha256"] if rows else "0" * 64
    return result


def append(stream, rows, event, data):
    body = dict(schema=SCHEMA, sequence=len(rows), previous_sha256=chain(rows), event=event, data=data)
    row = dict(body, record_sha256=digest(body))
    current = state([*rows, row])
    stream.seek(0, os.SEEK_END)
    stream.write(encoded(row).decode() + "\n")
    stream.flush()
    os.fsync(stream.fileno())
    rows.append(row)
    return current


def canonical(path):
    path = Path(path)
    require(not path.is_symlink() and path.resolve() == LEDGER.resolve(), "one canonical NEW ledger required")
    return path.resolve()


def initialize(config_path, ledger=LEDGER, *, root_go=False):
    require(root_go is True, "explicit root freeze/GO required; preparation never initializes")
    target = canonical(ledger)
    config = json.loads(Path(config_path).read_text())
    validate_config(config)
    verify_links(config)
    require(not target.exists(), "existing journal is immutable; no overwrite/reset")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return append(stream, [], "initialized", dict(config=config, config_file=pin(config_path)))


@contextmanager
def lease(ledger=LEDGER):
    with canonical(ledger).open("r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        rows = read_rows(stream)
        current = state(rows)
        require(current["config"] is not None and current["pending"] is None and not current["violated"], "ended initialized journal without breach required")
        yield stream, rows, current


def preflight_entrypoint(argv):
    require(Path(argv[0]).is_absolute() and Path(argv[0]).is_file(), "absolute existing stage main entrypoint required")
    if "python" in Path(argv[0]).name.lower():
        require(len(argv) > 1 and Path(argv[1]).is_absolute() and Path(argv[1]).is_file(), "absolute existing Python main script required before launch")


def verify_output_protection(outputs):
    before = json.loads(Path(PRESERVATION["path"]).read_text())
    protected = [Path(p["path"]).resolve() for p in before["protected_files"] + before["additional_protected_artifacts"]]
    workspaces = [Path(p["path"]).resolve() for p in before.get("original_workspaces", [])]
    for output in outputs:
        path = Path(output).resolve()
        require(not any(path == existing or existing.is_relative_to(path) for existing in protected),
                "output would cover an immutable protected artifact")
        require(not any(path.is_relative_to(workspace) for workspace in workspaces),
                "output inside an original protected workspace forbidden")
        require(not any(path == Path(root) or path.is_relative_to(Path(root))
                        or Path(root).is_relative_to(path) for root in IMMUTABLE_PARENT_ROOTS),
                "output would cover or enter a closed parent/archive/preserved-source directory")


def start(stream, rows, stage, metadata):
    current = state(rows)
    require(metadata.get("guard") == GUARD and isinstance(metadata.get("input_pins"), list), "one-worker/1GiB guard and explicit input pins required")
    descriptor = dict(argv=metadata.get("argv"), outputs=metadata.get("outputs"))
    validate_descriptor(descriptor)
    # Durable reservation is deliberately before entrypoint/input/protection
    # checks, so failed preflight never disappears from accounting.
    current = append(stream, rows, "stage-start", dict(stage=stage, reservation=copy.deepcopy(STAGES[stage]),
        metadata=copy.deepcopy(metadata), started_monotonic_seconds=time.monotonic(), owner_pid=os.getpid()))
    preflight_entrypoint(metadata["argv"])
    verify_links(current["config"])
    verify_output_protection(metadata["outputs"])
    allowed = {p["path"]: p for p in current["config"]["pins"]}
    for row in rows:
        if row["event"] == "stage-finish" and row["data"]["status"] == "completed":
            for expected in row["data"]["proofs"]:
                allowed[expected["path"]] = expected
            if row["data"].get("counter_proof"):
                expected = row["data"]["counter_proof"]
                allowed[expected["path"]] = expected
    for expected in metadata["input_pins"]:
        require(allowed.get(expected["path"]) == expected, "input pin must be frozen or a pinned completed-stage output")
        verify_pin(expected)
    entrypoints = [metadata["argv"][0]]
    if "python" in Path(entrypoints[0]).name.lower():
        entrypoints.append(metadata["argv"][1])
    for entrypoint in entrypoints:
        expected = pin(entrypoint)
        require(allowed.get(expected["path"]) == expected, "main entrypoint must be frozen or a completed-stage binary")
    return current


def progress_counts(path, kind):
    """Read existing durable intent/update records; never infer missing calls."""
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if kind == "fit":
        intents = [r for r in records if r.get("event") == "optimizer-intent"]
        updates = [r for r in records if r.get("event") == "optimizer-update"]
        forwards = [r for r in records if r.get("event") == "forward-intent"]
        require([r["global_update"] for r in intents] == list(range(1, len(intents) + 1)), "nonsequential optimizer intent journal")
        require([r["global_update"] for r in updates] == list(range(1, len(updates) + 1)), "nonsequential optimizer journal")
        paired = [(r["event"], r["global_update"]) for r in records if r.get("event") in ("optimizer-intent", "optimizer-update")]
        require(paired == [(event, i) for i in range(1, len(updates) + 1) for event in ("optimizer-intent", "optimizer-update")],
                "completed fit requires paired before-intent/after-update records")
        require(all(all(before.get(key) == after.get(key) and key in before for key in ("seed", "arm", "arm_update"))
                    for before, after in zip(intents, updates)), "optimizer intent/update model identity differs")
        require([r["global_forward"] for r in forwards] == list(range(1, len(forwards) + 1)), "nonsequential forward journal")
        require(all(r["kind"] in ("train", "evaluate") for r in forwards), "unallocated forward kind")
        return dict(optimizer_updates=len(updates), neural_forwards=len(forwards),
            training_forwards=sum(r["kind"] == "train" for r in forwards),
            evaluation_forwards=sum(r["kind"] == "evaluate" for r in forwards))
    if kind == "native":
        require(records and records[0].get("schema") == "jepa-binding-transfer-apply-journal/1"
                and records[0].get("maxApplyCalls") == 48, "exact native journal header required")
        calls = [r["applyCall"] for r in records if r.get("phase") == "beforeApply"]
        require(calls == list(range(1, len(calls) + 1)), "nonsequential before-apply journal")
        return dict(native_applies=len(calls))
    if kind == "baselines":
        calls = [r["global_fit"] for r in records if r.get("event") == "numerical-fit-intent"]
        require(calls == list(range(1, len(calls) + 1)), "nonsequential numerical-fit intent journal")
        return dict(numerical_fits=len(calls))
    raise ValueError("unrecognized progress counter kind")


def finish(stream, rows, status, active_seconds, observed, proofs, *, cleanup_verified=False,
           execution_ended=False, observed_verified=None, counter_proof=None):
    current = state(rows)
    pending = current["pending"]
    require(pending is not None and cleanup_verified is True and execution_ended is True,
            "known ended execution/cleanup required; otherwise leave pending")
    counts(observed, unknown=True)
    number(active_seconds)
    verified = status == "completed" if observed_verified is None else observed_verified
    existing = {p["path"]: p for p in current["config"]["pins"] + pending["metadata"]["input_pins"]}
    def allowed_proof(expected):
        if existing.get(expected["path"]) == expected:
            return
        path = Path(expected["path"])
        require(any(path == Path(output) or path.is_relative_to(Path(output))
                    for output in pending["metadata"]["outputs"]), "proof must be a declared stage output or an existing input")
    for expected in proofs:
        allowed_proof(expected)
        verify_pin(expected)
    measured = None
    if counter_proof is not None:
        allowed_proof(counter_proof)
        verify_pin(counter_proof)
        measured = progress_counts(counter_proof["path"], pending["stage"])
        for key in COUNTERS:
            if key in measured:
                require(observed[key] == measured[key], "observed count differs from durable progress")
        if status == "completed" and pending["stage"] == "fit":
            require(measured == current["config"]["fit_success_counts"], "complete fixed fit quota required")
    elif status == "completed" and pending["stage"] in ("native", "fit", "baselines"):
        raise ValueError("completed exposure stage requires durable counter proof")
    if status == "completed":
        verify_links(current["config"])
    elapsed = max(active_seconds, time.monotonic() - pending["started_monotonic_seconds"])
    if elapsed > pending["reservation"]["seconds"]:
        status = "failed"
    charged = dict(seconds=max(elapsed, pending["reservation"]["seconds"]) if status == "failed" else elapsed)
    charged.update({key: max(observed[key] or 0, pending["reservation"][key]) if status == "failed" else observed[key] for key in COUNTERS})
    return append(stream, rows, "stage-finish", dict(stage=pending["stage"], status=status,
        active_seconds=elapsed, observed=copy.deepcopy(observed), observed_verified=verified,
        charged=charged, proofs=copy.deepcopy(proofs), counter_proof=copy.deepcopy(counter_proof),
        counter_measurements=measured,
        cleanup_verified=True, execution_ended=True))


def note_pending_failure(stream, rows, error, proofs=()):
    current = state(rows)
    require(current["pending"] is not None, "pending stage required")
    for expected in proofs:
        verify_pin(expected)
    return append(stream, rows, "pending-failure", dict(stage=current["pending"]["stage"],
        error=str(error), proofs=list(proofs), disposition="cleanup/execution unknown; full reservation retained; no ordinary finish/retry"))
