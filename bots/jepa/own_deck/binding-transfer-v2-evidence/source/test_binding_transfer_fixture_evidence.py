"""Portable saved-byte checks only: no engine, model, fitting or subprocess call."""
import hashlib
import json
from pathlib import Path
import unittest

import binding_transfer_fixture_guard as G


ROOT = Path(__file__).resolve().parent / "binding-transfer-fixture-evidence"
GUARD_SHA = "ab7f7d0473550d39371145dd025c5c53a4f5cfa12731e45be359bf13dfb5d3a7"
OLD_LEDGER_SHA = "ffb01088cc7c456b84e1c23a38720e5cfe060869e878236ec065d409fb37a4f2"
PLAN_SHA = "0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f"
VALIDATION_SHA = "8942b37d64ec098ebccd0981884ea2938b775649dc933c3095af57921442d1bf"


def read(relative):
    return json.loads((ROOT / relative).read_bytes())


def rows(relative):
    return [json.loads(line) for line in (ROOT / relative).read_bytes().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chain(records, first_previous):
    """Independent of the saved guard/accounting state evaluators."""
    previous = first_previous
    for number, row in enumerate(records):
        if row["sequence"] != number or row["previous_sha256"] != previous:
            raise AssertionError("ledger sequence or previous digest differs")
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        previous = hashlib.sha256(raw).hexdigest()
        if previous != row["record_sha256"]:
            raise AssertionError("ledger body digest differs")
    return previous


class FixtureEvidenceTests(unittest.TestCase):
    def test_all_local_copy_hashes_and_exact_package_membership(self):
        manifest = read("manifest.json")
        self.assertEqual(manifest["schema"], "jepa-binding-transfer-fixture-evidence/1")
        self.assertEqual(manifest["status"], "fixture-construction-validated-only")
        self.assertIs(manifest["semantic_validated"], False)
        self.assertEqual(len(manifest["files"]), 18)
        expected = {"manifest.json"}
        for record in manifest["files"] + manifest["authored_files"]:
            relative = Path(record["path"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            self.assertNotIn(relative.as_posix(), expected)
            path = ROOT / relative
            self.assertFalse(path.is_symlink())
            self.assertEqual(sha(path), record["sha256"], relative.as_posix())
            self.assertEqual(path.stat().st_size, record["bytes"], relative.as_posix())
            expected.add(relative.as_posix())
            if "original_path" in record:
                self.assertTrue(Path(record["original_path"]).is_absolute())
        actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)
        self.assertLess(sum((ROOT / p).stat().st_size for p in actual), 2 * 1024 ** 2)

    def test_pinned_guard_accepts_complete_local_frozen_twenty_six_worlds(self):
        self.assertEqual(sha(Path(G.__file__)), GUARD_SHA)
        self.assertEqual(read("manifest.json")["guard_source"]["sha256"], GUARD_SHA)
        self.assertEqual(sha(ROOT / "collection-plan.json"), PLAN_SHA)
        self.assertEqual(sha(ROOT / "debug/validate-1/validation.json"), VALIDATION_SHA)
        raw = read("debug/validate-1/validation.json")
        proof = G.validate_receipt(raw, ROOT / "collection-plan.json")
        self.assertEqual(proof["cases"], 26)
        self.assertEqual(proof["unique_world_ids"], list(range(26)))
        self.assertIs(raw["noHiddenCardsOrDrawOrder"], True)
        self.assertEqual(sum(len(c["fixtureAttachmentWitnesses"]) for c in raw["cases"]), 12)
        for case in raw["cases"]:
            self.assertTrue({"steps", "final", "targetAction"}.isdisjoint(case))
            self.assertEqual(case["applyCalls"], 0)
            self.assertEqual(case["actionsApplied"], 0)
            self.assertIs(case["publicSnapshotRoundtripExact"], True)
            self.assertIs(case["legalActionsRoundtripExact"], True)

    def test_new_ledger_is_fully_closed_zero_call_and_retains_prior_carry(self):
        ledger = rows("debug/campaign-ledger.jsonl")
        final = chain(ledger, None)
        self.assertEqual(final, "6321739736b349771bace38bdd607545c05c59fe4dd18f4d0978b62c1f365f30")
        self.assertEqual([(r["event"], r["data"].get("stage")) for r in ledger], [
            ("initialized", None), ("stage-start", "build"), ("stage-finish", "build"),
            ("stage-start", "validate"), ("stage-finish", "validate")])
        config = read("debug/config.json")
        unsigned = dict(config)
        digest = unsigned.pop("config_sha256")
        encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), digest)
        self.assertEqual(config["parent"]["charged_native_applies"], 160)
        self.assertEqual(config["parent"]["charged_seconds"], 110.10179149871692)
        self.assertIsNone(config["parent"]["observed_native_applies"])
        self.assertEqual(ledger[0]["data"]["parent"], config["parent"])
        self.assertEqual(ledger[0]["data"]["config"]["sha256"], sha(ROOT / "debug/config.json"))
        for index, stage, limit in ((1, "build", 15), (3, "validate", 10)):
            start, finish = ledger[index]["data"], ledger[index + 1]["data"]
            self.assertEqual(start["reserved_seconds"], limit)
            self.assertTrue(all(value == 0 for value in start["reserved_calls"].values()))
            self.assertEqual(finish["status"], "completed")
            self.assertIs(finish["cleanup_verified"], True)
            self.assertIs(finish["observed_verified"], True)
            self.assertTrue(all(value == 0 for value in finish["observed_calls"].values()))
            self.assertGreater(finish["charged_seconds"], 0)
            self.assertLessEqual(finish["charged_seconds"], limit)
            receipt = read("debug/" + stage + "-1-stage-receipt.json")
            self.assertIs(receipt["preliminary"], True)
            self.assertLessEqual(receipt["charged_seconds"], finish["charged_seconds"])
            self.assertEqual(receipt["observed_calls"], finish["observed_calls"])
        charged = sum(ledger[i]["data"]["charged_seconds"] for i in (2, 4))
        self.assertEqual(charged, 1.6639899580040947)
        self.assertEqual(read("manifest.json")["accounting"]["debug_charged_seconds"], charged)
        self.assertEqual(read("manifest.json")["accounting"]["cumulative_charged_seconds"], 111.76578145672102)
        self.assertEqual(config["stages"]["validate"]["argv"][1], "--validate-fixtures-only")
        self.assertEqual(Path(config["binary"]).name, "binding-transfer-fixture-validator")

    def test_original_failed_charge_and_header_only_zero_observation_are_preserved(self):
        self.assertEqual(sha(ROOT / "prior-failure/campaign-ledger.jsonl"), OLD_LEDGER_SHA)
        ledger = rows("prior-failure/campaign-ledger.jsonl")
        self.assertEqual(len(ledger), 5)
        chain(ledger, "0" * 64)
        failed = ledger[-1]["data"]
        self.assertEqual((failed["stage"], failed["status"]), ("native", "failed"))
        self.assertEqual(failed["charged"]["native_applies"], 48)
        self.assertEqual(failed["charged"]["seconds"], 30)
        self.assertIs(failed["observed_verified"], True)
        self.assertEqual(failed["observed"]["native_applies"], 0)
        self.assertTrue(all(value == 0 for value in failed["observed"].values()))
        journal = rows("prior-failure/native-attempt-1/native-transitions.jsonl")
        self.assertEqual(len(journal), 1)
        self.assertEqual(journal[0]["schema"], "jepa-binding-transfer-apply-journal/1")
        self.assertEqual(journal[0]["maxApplyCalls"], 48)
        self.assertEqual((ROOT / "prior-failure/native-attempt-1/stderr.log").read_text().strip(),
                         "collector: registrationOrder conflicts with physical attachment chronology")
        accounting = read("manifest.json")["accounting"]
        self.assertEqual(accounting["prior_failed_native_reservation_retained"], 48)
        self.assertEqual(accounting["cumulative_charged_native_applies"], 160)
        self.assertIsNone(accounting["historical_observed_native_applies"])

    def test_local_proof_pins_match_copies_without_following_external_paths(self):
        manifest = read("manifest.json")
        local = {r["original_path"]: r for r in manifest["files"]}
        ledger = rows("debug/campaign-ledger.jsonl")
        for index in (2, 4):
            for proof in ledger[index]["data"]["proofs"]:
                if proof["path"] in local:
                    record = local[proof["path"]]
                    self.assertEqual((proof["sha256"], proof["bytes"]),
                                     (record["sha256"], record["bytes"]))
                else:
                    self.assertEqual(Path(proof["path"]).name, "binding-transfer-fixture-validator")
        source = read("debug/validation-source-manifest.json")
        self.assertEqual(source["closed_failed_ledger"]["sha256"], OLD_LEDGER_SHA)
        self.assertEqual(source["collection_plan"]["sha256"], PLAN_SHA)
        self.assertEqual(manifest["external_evidence"]["failed_archive_manifest"]["sha256"],
                         "5cd1e0bac1f7f04965e464e945e368777711a1704638d9e650f24af5105426ae")
        self.assertIn("binaries", manifest["external_evidence"]["excluded"])


if __name__ == "__main__":
    unittest.main()
