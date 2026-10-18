"""Versioned zero-neural saved-report recovery accounting; preparation never initializes a ledger.

Stdlib only. Historical journals are read-only parents. Every actual stage uses
one canonical nonblocking lease from before input checks/imports through cleanup.
An unresolved cleanup leaves the durable start pending and blocks later stages.
Copied from the frozen 761b accounting core; only versioned routes, carried
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
CAMPAIGN = TASK / "experiments/binding-transfer-report-recovery-v1"
LEDGER = CAMPAIGN / "campaign-ledger.jsonl"
SCHEMA = "jepa-binding-transfer-report-accounting/1"
CONFIG_SCHEMA = "jepa-binding-transfer-report-config/1"
PRESERVATION = dict(path=str(TASK / "experiments/next-cycle-preservation-v1/protected-before.json"),
    sha256="9c9106f7184a8135db34a02125f6f702a2cb0303f71de99156697928787444bf", bytes=27822)
COUNTERS = ("native_applies", "neural_forwards", "optimizer_updates", "numerical_fits", "paid_jobs", "paid_spend_usd")
STAGES = {
    "recover": dict(seconds=3., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
    "baselines": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=64, paid_jobs=0, paid_spend_usd=0.),
    "verify": dict(seconds=5., native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0.),
}
CAPS = dict(seconds=13., native_applies=0, neural_forwards=0, optimizer_updates=0,
            numerical_fits=64, paid_jobs=0, paid_spend_usd=0., cpu_workers=1, rss_bytes=1024 ** 3)
PARENT = dict(scope="Binding v1+v2+supplement, failed binding-transfer-v1, zero-call fixture debugging binding-transfer-v2 failed prep and binding-transfer-repair-v1 failed report write after saved optimizer completion; PR36/37 separately linked",
    charged_native_applies=208, charged_seconds=184.01759783166926, observed_native_applies=None,
    verified_v2_native_applies=32, verified_binding_transfer_v2_native_applies=48,
    charged_saved_fit_optimizer_updates=5400, charged_saved_fit_neural_forwards=5436,
    failed_fit_observed_optimizer_updates=None, failed_fit_observed_neural_forwards=None,
    durable_saved_fit_optimizer_updates=5400, durable_saved_fit_neural_forwards=5436,
    v1_static_forensic_engine_applies=0,
    pr36_pr37_optimizer_updates=1900, pr36_pr37_neural_forwards=1917,
    pr36_pr37_native_applies=87, pr36_pr37_closed_form_head_fits=32,
    paid_spend_usd=0., cumulative_native_ceiling=208, cumulative_seconds_ceiling=197.01759783166926,
    historical_modal_ceiling_usd=100., historical_modal_minimum_reserve_usd=25.)
GUARD = dict(cpu_workers=1, rss_bytes=1024 ** 3)

# Frozen inherited bytes and closed journals; original source-path declarations
# inside historical manifests are provenance, never rechecked as current code.
INHERITED_CORE = {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck/binding_transfer_repair_accounting.py',
 'sha256': '761b62596c76ed3f61dfee1f348fdd54a41a8e92d756eade8ecb90b3f9aa96bb',
 'bytes': 41477}
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
  'final_event': 'stage-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/campaign-ledger.jsonl',
          'sha256': '37d623f5f7a9675e49e8ebd74892244c3b9341e9391a387ae7383fe5449467c5',
          'bytes': 258090},
  'records': 7,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': '0376fef55991b42b4ce573cba75b021d87db0a86ccec46918881a591600618c6',
  'final_event': 'stage-finish'},
 {'pin': {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/campaign-ledger.jsonl',
          'sha256': '38b24eddd4b43871091494fe4d6a442eadff3091e10cb9ed816ab3e603b1845d',
          'bytes': 98140},
  'records': 5,
  'first_previous_sha256': '0000000000000000000000000000000000000000000000000000000000000000',
  'final_record_sha256': '594157318901334828cfb11009afd6151c7c767f549e2c9fc9513e10e2fae0fe',
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
  'bytes': 205624},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck/binding_transfer_accounting.py',
  'sha256': '51ad01b175d5367e27b5e0f8eebb91d2a417f73069cfdd865269cff714f012cd',
  'bytes': 25321},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/campaign-config.json',
  'sha256': '6c1bde1ea5274547279f510200438a5b0d18c73e8275b1cfe00b45b453f2f3f5',
  'bytes': 123958},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/learner-prepared-v1.json',
  'sha256': 'b674ff7a2eab3550e2dc138cf49b72ad9b0673724553e8914dc5494a46f668d2',
  'bytes': 25770},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelabel-routing-v1.json',
  'sha256': '72b7bbc8d8bf87b78ff0957d2f92d05b453aa64e017821a24d84510737cf7292',
  'bytes': 3741},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/native-plan.json',
  'sha256': '0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f',
  'bytes': 107878},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/native-attempt-1/native-receipt.json',
  'sha256': '3b7c030a6ab8b737bceef44ed7951fd97d133a425c6633c26f7ff6c70e6139f6',
  'bytes': 3869468},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/native-attempt-1/native-transitions.jsonl',
  'sha256': '8819c0eea42c932db83a4540ce5bd4e38c0af0a6d01922d709b782ed9c3b0986',
  'bytes': 2425246},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/native-build-1/supervisor-receipt.json',
  'sha256': '220a8e41b47e1cd588b4f309c0481f6acbebd7453132bc03d06b7ecf8e6dcbc9',
  'bytes': 4685},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/native-attempt-1/supervisor-receipt.json',
  'sha256': 'db64ce7ce0a033327fb07ce15ba972a4cf9bc6104d74c8582b1073a94732aeba',
  'bytes': 5381},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prep-1-stage-receipt.json',
  'sha256': '54c1e00aba765c624590249a2e843c892f72c0945a974f844a9ea57616866e23',
  'bytes': 2085},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prep-1/receipt.json',
  'sha256': '54c1e00aba765c624590249a2e843c892f72c0945a974f844a9ea57616866e23',
  'bytes': 2085},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck/binding_transfer_next_accounting.py',
  'sha256': 'ba6a9938210db820b16306afa36561bcd4a4abffa7dac1d9a388623f5bec6215',
  'bytes': 38602},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/campaign-config.json',
  'sha256': 'c1a9e45742e1cf5d86d833fd3788943e8fc1fe96282a2e22b3d6d786fef0486e',
  'bytes': 90676},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/prep-1/sealed-fit-plan.json',
  'sha256': '563d8856e941915885b697b1d127e5899d78922fd2f57a4efd662ac8e1cf3d7d',
  'bytes': 182849},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/prep-1/dataset.npz',
  'sha256': '9df7e7a6ba49bee813acab9a689178074b785876e28829e0c827470a0b4c22d9',
  'bytes': 6207},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/prep-1/dataset.manifest.json',
  'sha256': '8ddfb62686e472b5cc29a88ca9ae124c6bf4b7487e51c6f44660d37275cb702b',
  'bytes': 500060},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/prep-1-stage-receipt.json',
  'sha256': '62555193caaa16ad913fc3edf78115ad4e86e1a376fe4478b7f8b20dcad5ccf1',
  'bytes': 25375},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1-stage-receipt.json',
  'sha256': 'c2328584730b1e8561753cc6a43e49130cef07dd764f78e130ff8e672e579513',
  'bytes': 17168},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-progress.jsonl',
  'sha256': '30bfc09de6c58acbe39931c92a10c17737c23b5ea0ba409c8b2f441fbd986f2a',
  'bytes': 2104400},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/repair-routing-v1.json',
  'sha256': 'c2a2b6fd4dc84705d5c6919ee2cdd92e59a44814cc8858a7df573ccdac1d5840',
  'bytes': 4500},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/consumed-inputs.npz',
  'sha256': 'd68a1c57fb7508c7d9057805882e7e5bf16a6fee46d40f247c84b1a0b9e81a3f',
  'bytes': 8575},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/contract.json',
  'sha256': 'ce59683f2410001f2d2c672d98fddc39cf531a95bf2afc4913feb27d40051ef5',
  'bytes': 14668},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/program-inputs.npz',
  'sha256': '8c1a4971957f9f8ec7650695fb979e86bdeea0cf1675395514628f008b514b02',
  'bytes': 12197},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/receipt.json',
  'sha256': 'c2328584730b1e8561753cc6a43e49130cef07dd764f78e130ff8e672e579513',
  'bytes': 17168},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R0-checkpoint.npz',
  'sha256': 'c37fbbacb7f6b80fa6ad8f4fd09b9970f925c86807b42b85e7a768c705a3152f',
  'bytes': 49676},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R0-step0-predictions.npz',
  'sha256': 'bb789c7f04d8ce211ddfce1aef017affa9a8d5361df24828b8d600fadcb2b59e',
  'bytes': 3554},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R0-step300-predictions.npz',
  'sha256': '4d2915d2a5e5824a94224e6472d3b2a1f5ee03b819a42166503ccf3b0efc5fb7',
  'bytes': 3597},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R1-checkpoint.npz',
  'sha256': 'a450fbb57da14661876fd726713b077f10c35afcbb0e53cd3845e037008837e6',
  'bytes': 49684},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R1-step0-predictions.npz',
  'sha256': 'cb6922a752101cf06ef42e7d13f6da106ad179ef6739285678af7e938b194ea5',
  'bytes': 3793},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C0R1-step300-predictions.npz',
  'sha256': '47632f3dcf0b9e8bcd67f3f1ff4249cfcea8cbc2580f40ee6a1b588366460b61',
  'bytes': 3851},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R0-checkpoint.npz',
  'sha256': '115879029be35b54dbaa90882fab71bb910412fa1b595044886d3925f85c9f27',
  'bytes': 49696},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R0-step0-predictions.npz',
  'sha256': '6cd5b5e9e21f21d6d11491c430bd1c7142a6228f44f4c4b64b842465de394f3d',
  'bytes': 4352},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R0-step300-predictions.npz',
  'sha256': '94a24e415c9ec60a9fb1f112a02263e4bf7ab071a37623b3017084fa7f26769a',
  'bytes': 4409},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R1-checkpoint.npz',
  'sha256': 'c8cb0ff4a0ef62a21146ce90660a6d445050cbfd1dcab283a652803f8decc7d2',
  'bytes': 49709},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R1-step0-predictions.npz',
  'sha256': '424e492b463333476e8e6c52d93674c0baee469f146dceeabe8bf947def2f73b',
  'bytes': 4582},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-C1R1-step300-predictions.npz',
  'sha256': 'dd82d18299d1847ddec7cd081462f226c392c5d241e5dd93cd23af76bda4dfa6',
  'bytes': 4642},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-ID-only-checkpoint.npz',
  'sha256': '11a7ab12b3ec88224be6b619c1ca1bc67c3f15234d28752613d0657199f44448',
  'bytes': 49547},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-ID-only-step0-predictions.npz',
  'sha256': '1efa4884b832d73b49747ddc72a69e9f9fa8c9f60dca1b53f4e35aa6b78d22df',
  'bytes': 4207},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-ID-only-step300-predictions.npz',
  'sha256': '647845f6b6cd2a00c40e442dfd702d4465f1aec07df300848320e927a5309e47',
  'bytes': 4270},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-initial-checkpoint.npz',
  'sha256': 'ab8337093a2ce28ac8e5a392c59fe662343703c3c93f24f84b061bf6637bd9fa',
  'bytes': 49027},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-untrained-typed-checkpoint.npz',
  'sha256': '603b01fc2021c2e00c8680439d9907dd504205f0091742e06ef85973ad67771f',
  'bytes': 49601},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-untrained-typed-step0-predictions.npz',
  'sha256': '424e492b463333476e8e6c52d93674c0baee469f146dceeabe8bf947def2f73b',
  'bytes': 4582},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s17-untrained-typed-step300-predictions.npz',
  'sha256': '73fad28f84dafeb45220568d2b12316dcd0d204d8dba7d129736824da086e22f',
  'bytes': 4656},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R0-checkpoint.npz',
  'sha256': '64e7a810b9162613ac93c3b53dcd01d78d7abca72565170b4dc64aff240de639',
  'bytes': 49706},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R0-step0-predictions.npz',
  'sha256': 'be3aff7ce5f501adb612e33e1eab776119a9e72e824dc2e687f4c57047bfe22b',
  'bytes': 3575},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R0-step300-predictions.npz',
  'sha256': 'b4f2dfafeb46a3f2ac7a2edf24cb91681eee84aec1cd91506016b0321f9a7a9d',
  'bytes': 3629},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R1-checkpoint.npz',
  'sha256': '4758cb081b3f2cdbcf1449e44f56c64fb502c8f92cddd3622cee104aa8f594c3',
  'bytes': 49710},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R1-step0-predictions.npz',
  'sha256': '3606193108fb8cfc09be7addac53f5eeace7fbbd40a70acb6ec1c375c8df6e66',
  'bytes': 3816},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C0R1-step300-predictions.npz',
  'sha256': '308a42b530f58dbb0777f59d8352796dbbe5ffd5f4ecd073e4232bd6ae870eb3',
  'bytes': 3861},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R0-checkpoint.npz',
  'sha256': '0b19aa1cc569c92c4eeb067c205a06541a623cfad18087046db0ed8043c28d2d',
  'bytes': 49710},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R0-step0-predictions.npz',
  'sha256': '56735e852684ee14df2ee54a9280a0b4995a2e5918ad57774480b36b3885fa8c',
  'bytes': 4344},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R0-step300-predictions.npz',
  'sha256': 'ae86936d6f1ab64e53415614ff84772ed86b9f17cf7c5ac088bc1f3d222e9b0b',
  'bytes': 4414},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R1-checkpoint.npz',
  'sha256': '825cbecddb4fb444ac4744655883debca4b893dd70833df122fb32b0b75a6e2d',
  'bytes': 49700},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R1-step0-predictions.npz',
  'sha256': 'abce34bdecdcc3b1543a719315a58e357a3e4ef97de06a1df0495638c08934d5',
  'bytes': 4580},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-C1R1-step300-predictions.npz',
  'sha256': 'd5d6df7f0fc1d6e4548935b9f4a4f3a2d483513f7f9e5b1bc877c194dd5aed85',
  'bytes': 4644},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-ID-only-checkpoint.npz',
  'sha256': 'f7f640b97d63da7a81c4391a48130a088e48a918c805369629c853e43e05a3c1',
  'bytes': 49561},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-ID-only-step0-predictions.npz',
  'sha256': 'e1bc9ba86a774968f13b9119b50dfec9c780dab1db47e7c582e5d1a067ee5595',
  'bytes': 4228},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-ID-only-step300-predictions.npz',
  'sha256': '60c66cc84a53426024bc48694bf5861c4220f24ab0b79e5aa20fff5c1c1222a6',
  'bytes': 4255},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-initial-checkpoint.npz',
  'sha256': '4f0c90629f208150fb144efbf67932e241f462ec7665bcdb0e4b19ea09599cdd',
  'bytes': 49016},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-untrained-typed-checkpoint.npz',
  'sha256': '8e72fb6dc64404c0a31a84805240a63aee26f4df7c24f3c50e71fbb643815ccc',
  'bytes': 49570},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-untrained-typed-step0-predictions.npz',
  'sha256': 'abce34bdecdcc3b1543a719315a58e357a3e4ef97de06a1df0495638c08934d5',
  'bytes': 4580},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s29-untrained-typed-step300-predictions.npz',
  'sha256': 'abf43be235b16fc78744def82f2ff6e4e81de1b1068cc90b80a3de1b6f0283f5',
  'bytes': 4633},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R0-checkpoint.npz',
  'sha256': 'b60e71316808197f52d90cfe8e8e1f149321e363b37033743981d5bb72ca91a0',
  'bytes': 49702},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R0-step0-predictions.npz',
  'sha256': '34d347f669b25485efc5ab7fa1c85594b93739d790d42815adae9c404e2b5691',
  'bytes': 3585},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R0-step300-predictions.npz',
  'sha256': 'ff51badd9ec6bbc5abbd1421bc654af51b14488e81f890fab59c534a3d06ba55',
  'bytes': 3613},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R1-checkpoint.npz',
  'sha256': '009a3103924caf9ca49cb60e689bc4f0f00f533c44d469b1c1cd05e1f3baac45',
  'bytes': 49708},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R1-step0-predictions.npz',
  'sha256': '7cee66490d224bc7e99e3569eeb2dac51dc9234b405355c78657d52db0ef8970',
  'bytes': 3812},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C0R1-step300-predictions.npz',
  'sha256': '2d9c6e6fa059f91706d27fa21a69c35c96f4d2dbfb55e4ceb37c00ed3c4dd64d',
  'bytes': 3856},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R0-checkpoint.npz',
  'sha256': '0274d7534676ff11bb16fc9393374093e47ac085ec08bf1c6ec503d28b866472',
  'bytes': 49722},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R0-step0-predictions.npz',
  'sha256': 'c57778be99799426eafe6e0e116b03d0cdcc8e3f32124287c27404e4099c52b1',
  'bytes': 4368},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R0-step300-predictions.npz',
  'sha256': 'b1df0124dba0e00aac16947c4663b88980dc24e71625ba242502ccde3c4247c3',
  'bytes': 4403},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R1-checkpoint.npz',
  'sha256': '94e1849ca4194e94b57aa2b89fa07902ed40079ed3b67a72a742296cdf035a30',
  'bytes': 49693},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R1-step0-predictions.npz',
  'sha256': 'b30bba1761c283b85affc63646ef179ae326b648876ccca194f37ba8af1f111c',
  'bytes': 4606},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-C1R1-step300-predictions.npz',
  'sha256': 'a68ec416c18ca3b7863be7449dbbaec08f929f144aef0170808a67c7d2a1fb06',
  'bytes': 4653},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-ID-only-checkpoint.npz',
  'sha256': '27aa6ae0a92789607bda306593ff6a2dd2fdc1210e75422bfc7577f9abb1c854',
  'bytes': 49585},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-ID-only-step0-predictions.npz',
  'sha256': '75260f6e24dda7ce50c6a8010bfb40e6fda9d70fd3876a20e060ec3215f867d4',
  'bytes': 4197},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-ID-only-step300-predictions.npz',
  'sha256': 'ad057af202bf02ca877aa3e34f96acda16981ab8ee742acc58dc8f093db18e62',
  'bytes': 4272},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-initial-checkpoint.npz',
  'sha256': 'ff45394e4e63e66b9882645ae17b7855dabb337abccc879485a4e7f941b622a3',
  'bytes': 49026},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-untrained-typed-checkpoint.npz',
  'sha256': 'ea5806eb4d5333fc0daaf1883c9f211348335f96debb8a3e2882dfb1027f0f5e',
  'bytes': 49550},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-untrained-typed-step0-predictions.npz',
  'sha256': 'b30bba1761c283b85affc63646ef179ae326b648876ccca194f37ba8af1f111c',
  'bytes': 4606},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/s43-untrained-typed-step300-predictions.npz',
  'sha256': '814c24c1f7baf84b186cf86418032574853733043870770d612711317158bb28',
  'bytes': 4655},
 {'path': '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1/fit-1/training-schedule.npz',
  'sha256': '8623ac4f7916993172f2d5b409059945bad0bb1e304d91e19a414c440eb03e28',
  'bytes': 1217}]
IMMUTABLE_PARENT_ROOTS = ['/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-fixture-validation-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2/prelaunch-validated-source',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/effect-identifiability-v2',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/learning-sanity-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v1',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/public-input-binding-v2',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/publication-sources/binding-transfer-v1-failed-archive',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-v2',
 '/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/binding-transfer-repair-v1']


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
    require(set(config.get("stage_descriptors", {})) == set(STAGES), "all three frozen stage descriptors required")
    for descriptor in config["stage_descriptors"].values():
        validate_descriptor(descriptor)
    require(isinstance(config.get("pins"), list), "explicit frozen source/input pins required")
    require(len({p["path"] for p in config["pins"]}) == len(config["pins"]), "duplicate frozen input paths")
    require(config.get("fit_success_counts") == dict(optimizer_updates=5400, neural_forwards=5436,
            training_forwards=5400, evaluation_forwards=36), "fixed complete fit quota required")
    require(config.get("inherited_core") == INHERITED_CORE
            and config.get("closed_parent_journals") == CLOSED_PARENT_JOURNALS
            and config.get("parent_artifact_pins") == PARENT_ARTIFACT_PINS,
            "exact immutable inherited core and ten closed-parent links required")


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
    # Validate its original112/79.267 values independently of the new208/184.017 carry.
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
        fit_counts_scope="Historical immutable saved-fit journal witness only; zero NEW neural/update allowance and no fit stage. Failed fit observations stay null.",
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
