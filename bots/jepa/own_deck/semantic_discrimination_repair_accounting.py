"""Explicit repair adapter for the unchanged, frozen Campaign core.

Only the linked parent carry and adapter provenance change. The specification's
source pin remains the original core; the adapter has its own mandatory pin.
No globals, module aliases or __file__ values are replaced. Import is stdlib-only.
"""
import copy
import importlib.util
import json
from pathlib import Path

CORE_SOURCE = dict(path=str(Path(__file__).resolve().with_name("semantic_discrimination_accounting.py")),
    sha256="15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d", bytes=32142)


def _load_core():
    import hashlib
    raw = Path(CORE_SOURCE["path"]).read_bytes()
    if len(raw) != CORE_SOURCE["bytes"] or hashlib.sha256(raw).hexdigest() != CORE_SOURCE["sha256"]:
        raise ValueError("frozen original Campaign core changed")
    spec = importlib.util.spec_from_file_location("semantic_discrimination_frozen_core", CORE_SOURCE["path"])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE = _load_core()
require, pin, verify_pin = CORE.require, CORE.pin, CORE.verify_pin
encoded, digest, counts, zero_counts = CORE.encoded, CORE.digest, CORE.counts, CORE.zero_counts
read_rows, chain = CORE.read_rows, CORE.chain
SCHEMA, SPEC_SCHEMA, COUNTERS = CORE.SCHEMA, CORE.SPEC_SCHEMA, CORE.COUNTERS
GUARD, STAGE_SECONDS, DEFAULT_CAPS = copy.deepcopy(CORE.GUARD), copy.deepcopy(CORE.STAGE_SECONDS), copy.deepcopy(CORE.DEFAULT_CAPS)


def make_spec(*args, **kwargs):
    spec = CORE.make_spec(*args, **kwargs)
    spec["provenance"].update(accounting_core=copy.deepcopy(CORE_SOURCE), accounting_adapter=pin(__file__),
        repair_scope="New allocation after closed failed metadata; all old three seconds retained, no native/NN reservation reused or credited.")
    pins = {p["path"]: p for p in spec["pins"]}
    for expected in (CORE_SOURCE, pin(__file__)):
        require(expected["path"] not in pins or pins[expected["path"]] == expected, "conflicting core/adapter source pin")
        pins[expected["path"]] = expected
    spec["pins"] = list(pins.values())
    return spec


class Campaign(CORE.Campaign):
    def validate_spec(self):
        super().validate_spec()
        provenance = self.config.get("provenance", {})
        require(provenance.get("accounting_core") == CORE_SOURCE
                and provenance.get("accounting_adapter") == pin(__file__), "explicit frozen core and repair adapter routes required")
        pinned = {p["path"]: p for p in self.config["pins"]}
        require(pinned.get(CORE_SOURCE["path"]) == CORE_SOURCE and pinned.get(str(Path(__file__).resolve())) == pin(__file__),
                "core and adapter must both be immutable specification inputs")

    def validate_prior(self):
        p = self.prior
        require(p.get("schema") == "jepa-campaign-prior-manifest/1", "pinned prior manifest schema required")
        carry = p.get("carry", {})
        require(carry.get("charged_native_applies", carry.get("native_applies")) == 208
                and carry.get("charged_seconds", carry.get("active_seconds")) == 191.08889674965758
                and carry.get("observed_native_applies") is None, "closed failed metadata charge and all unknown observations must carry forward")
        for name in ("pins", "protected_files", "closed_journals", "protected_roots", "original_workspaces"):
            require(isinstance(p.get(name), list), "explicit prior " + name + " required")
        for expected in p["pins"] + p["protected_files"]:
            CORE.validate_pin(expected)
        failed = p.get("repair_parent", {})
        require(failed.get("charged_seconds") == 3. and failed.get("charged_native_applies") == 0
                and failed.get("charged_neural_forwards") == 0 and failed.get("charged_optimizer_updates") == 0
                and failed.get("final_chain") == "5edada95312903f7fadd809e311d42cf5cc1eeb080adc6d94e262cbbb0381f88",
                "exact closed first-attempt metadata failure must remain linked")
