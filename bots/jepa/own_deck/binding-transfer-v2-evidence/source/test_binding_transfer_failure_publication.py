"""Portable synthetic byte/metadata tests; no real scientific or publication stage."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import binding_transfer_failure_publication as F
import publication_checkpoint as P


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(P.encoded(value))
    return F.pin(path)


def publication(symbol="a"):
    return dict(head_commit=symbol * 40, tree="b" * 40, merge_commit="c" * 40,
        ci_run_id=123, ci_conclusion="success", merged=True, merged_tree_matches_checked_head=True)


class FailurePublicationTests(unittest.TestCase):
    def fixture(self, base):
        campaign = base / "campaign"
        campaign.mkdir()
        for name in F.REQUIRED_CAMPAIGN_FILES:
            path = campaign / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n" if path.suffix == ".json" else "")
        for name in F.REQUIRED_SNAPSHOTS:
            save(campaign / name / "snapshot.json", dict(kind="unexecuted-prelaunch-snapshot"))
            (campaign / name / "preserved-source.txt").write_text(name)
        source = base / "frozen-source.txt"
        source.write_text("same immutable source\n")
        config = dict(parent=dict(charged_native_applies=112, charged_seconds=79.26753083174117,
            observed_native_applies=None), pins=[F.pin(source)], repeated=dict(pin=F.pin(source)))
        save(campaign / "campaign-config.json", config)
        zero = copy.deepcopy(F.SCIENCE)
        finished = dict(status="completed", cleanup_verified=True, execution_ended=True,
            observed_verified=True, observed=zero, charged=dict(native_applies=0, seconds=.8))
        failed = copy.deepcopy(finished)
        failed.update(status="failed", charged=dict(native_applies=48, seconds=30))
        records = [("initialized", {}), ("stage-start", dict(stage="build")),
            ("stage-finish", dict(stage="build", **finished)), ("stage-start", dict(stage="native")),
            ("stage-finish", dict(stage="native", **failed))]
        previous = "0" * 64
        rows = []
        for n, (event, data) in enumerate(records):
            row = dict(sequence=n, previous_sha256=previous, event=event, data=data)
            canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            previous = hashlib.sha256(canonical).hexdigest()
            row["record_sha256"] = previous
            rows.append(row)
        (campaign / "campaign-ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (campaign / "native-attempt-1/native-transitions.jsonl").write_text(json.dumps(dict(schema="jepa-binding-transfer-apply-journal/1", maxApplyCalls=48)) + "\n")
        (campaign / "native-attempt-1/stderr.log").write_text("collector: registrationOrder conflicts with physical attachment chronology\n")
        report = base / "report.md"
        report.write_text("Failed before apply. Learned results unavailable.\n")
        blocker = base / "postmortem.md"
        blocker.write_text("Two linked upgrades disagree with registration chronology.\n")
        patch = base / "unapplied.patch"
        patch.write_text("--- original\n+++ proposed-only\n")
        embedding = save(base / "embedding.json", dict(spaces={str(n): dict(id=str(n)) for n in range(18)}))
        artifacts = {"old" + str(n): F.pin(source) for n in range(53)}
        artifacts["embedding_index"] = embedding
        pub = publication()
        index = save(base / "old-index.json", dict(schema=P.INDEX_SCHEMA, artifacts=artifacts, publication=pub, counts={}))
        handoff = save(base / "old-handoff.json", dict(schema=P.HANDOFF_SCHEMA, research_index=index,
            **{k: pub[k] for k in ("head_commit", "tree", "merge_commit", "ci_run_id", "ci_conclusion", "merged_tree_matches_checked_head")}))
        pointer = base / "current.json"
        P.publish(index["path"], handoff["path"], base / "checkpoints", pointer, index["sha256"], handoff["sha256"])
        args = campaign, report, blocker, patch, pointer
        return args

    def archive(self, base):
        args = self.fixture(base)
        capture = F.capture(*args)
        out = base / "new-archive"
        F.build(capture, out)
        return args, out

    def test_summary_distinguishes_observed_reserved_unknown_and_unrun(self):
        with tempfile.TemporaryDirectory() as name:
            args = self.fixture(Path(name))
            value = F.ledger_failure(args[0])
            self.assertEqual(value["new_observed"]["native_applies"], 0)
            self.assertEqual(value["new_charged"]["native_applies"], 48)
            self.assertEqual(value["cumulative_charged_native_applies"], 160)
            self.assertIsNone(value["cumulative_observed_native_applies"])
            self.assertIsNone(value["learned_results"])
            self.assertEqual(value["unstarted_stages"], ["prep", "fit", "baselines", "verify"])

    def test_damaged_ledger_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            args = self.fixture(Path(name))
            path = args[0] / "campaign-ledger.jsonl"
            path.write_text(path.read_text().replace('"failed"', '"completed"'))
            with self.assertRaisesRegex(ValueError, "hash chain"):
                F.ledger_failure(args[0])

    def test_nonempty_apply_journal_and_later_outputs_are_not_failure_only(self):
        with tempfile.TemporaryDirectory() as name:
            args = self.fixture(Path(name))
            journal = args[0] / "native-attempt-1/native-transitions.jsonl"
            original = journal.read_bytes()
            journal.write_bytes(original + b'{"phase":"beforeApply"}\n')
            with self.assertRaisesRegex(ValueError, "header-only"):
                F.ledger_failure(args[0])
            journal.write_bytes(original)
            (args[0] / "fit-1").mkdir()
            with self.assertRaisesRegex(ValueError, "unstarted"):
                F.ledger_failure(args[0])

    def test_preview_reads_no_raw_payload_bank_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            args = self.fixture(base)
            before = {str(p): p.read_bytes() for p in base.rglob("*") if p.is_file()}
            captured = F.capture(*args)
            self.assertTrue(all("raw" not in item for item in captured["captured"]))
            value = F.preview(captured, base / "new-output")
            self.assertEqual(value["embedding_spaces_unchanged"], 18)
            self.assertFalse((base / "new-output").exists())
            self.assertEqual(before, {str(p): p.read_bytes() for p in base.rglob("*") if p.is_file()})

    def test_complete_archive_adds_five_records_and_preserves_old54_and18(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            args, out = self.archive(base)
            result = F.verify(out, check_originals=True)
            self.assertEqual(result["artifact_count"], 59)
            self.assertEqual(result["embedding_spaces"], 18)
            self.assertFalse(result["remote_assets_uploaded"])
            archive = F.read(out / "evidence-index.json")
            originals = [r["provenance"]["original_path"] for r in archive["artifacts"]]
            self.assertEqual(len(originals), len(set(originals)))
            self.assertTrue(all(any(n in p for p in originals) for n in F.REQUIRED_SNAPSHOTS))
            self.assertEqual((out / "previous-publication-pointer.json").read_bytes(), args[-1].read_bytes())
            with self.assertRaises(ValueError):
                F.build(F.capture(*args), out)

    def test_archive_verifies_without_original_paths_but_check_originals_detects_drift(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            _, out = self.archive(base)
            (base / "frozen-source.txt").write_text("changed")
            F.verify(out)
            with self.assertRaises(ValueError):
                F.verify(out, check_originals=True)

    def test_missing_snapshot_changed_configpin_or_inside_output_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            args = self.fixture(base)
            captured = F.capture(*args)
            with self.assertRaises(ValueError):
                F.preview(captured, args[0] / "archive")
            (base / "frozen-source.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                F.capture(*args)

    def test_candidate_and_promotion_only_change_attestation_then_pointer(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            args, out = self.archive(base)
            old_pointer = args[-1].read_bytes()
            attestation = base / "ci.json"
            save(attestation, publication("d"))
            candidate = base / "candidate"
            F.candidate(out, candidate, attestation)
            self.assertEqual(args[-1].read_bytes(), old_pointer)
            self.assertEqual(F.read(candidate / "handoff.json")["publication"], publication("d"))
            result = F.promote(out, candidate, base / "checkpoints", args[-1])
            self.assertEqual(result["study_status"], F.STATUS)
            self.assertEqual((out / "previous-publication-pointer.json").read_bytes(), old_pointer)
            self.assertFalse(result["old_portable_rebuilt"])
            self.assertEqual(P.verify_pointer(args[-1])["publication"]["head_commit"], "d" * 40)
            F.verify(out)

    def test_publication_requires_successful_new_attestation(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            _, out = self.archive(base)
            bad = publication("d")
            bad["ci_conclusion"] = "pending"
            path = base / "ci.json"
            save(path, bad)
            with self.assertRaises(ValueError):
                F.candidate(out, base / "candidate", path)
            self.assertFalse((base / "candidate").exists())

    def test_tampered_candidate_handoff_or_advanced_pointer_cannot_promote(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            args, out = self.archive(base)
            attestation = base / "ci.json"
            save(attestation, publication("d"))
            target = base / "candidate"
            F.candidate(out, target, attestation)
            handoff = F.read(target / "handoff.json")
            handoff["learned_results"] = {"fake": 0}
            save(target / "handoff.json", handoff)
            with self.assertRaisesRegex(ValueError, "changed science"):
                F.promote(out, target, base / "checkpoints", args[-1])
            args[-1].write_bytes(args[-1].read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "advanced"):
                F.promote(out, target, base / "checkpoints", args[-1])

    def test_payload_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            _, out = self.archive(base)
            payload = next((out / "raw").iterdir())
            payload.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "archive file changed"):
                F.verify(out)


if __name__ == "__main__":
    unittest.main()
