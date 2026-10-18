import gzip
from pathlib import Path
import tempfile
import unittest

import publication_checkpoint as P
import publication_portable as B


class PortablePublicationTests(unittest.TestCase):
    def spaces(self):
        keys = ["deck", "card"] + ["independent_controls_" + str(i) for i in range(6)] + ["actual_corpus_card", "actual_corpus_deck"]
        return {key: dict(id="space-" + key, vectors_url=key + ".json", artifact_sha256="a" * 64,
                          vectors_url_bytes=10, dimension=32 if key == "actual_corpus_deck" else 16,
                          entity_count=27, semantic_validated=False) for key in keys}

    def closure(self, root):
        stage = root / "bundle"; stage.mkdir()
        return B.Closure(stage)

    def test_relative_payload_closure_preserves_numbers_masks_and_card_base(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); closure = self.closure(root)
            child = root / "result.json"
            value = dict(per_head={"damage": {"mae": -0.125, "support": 0, "known": False}},
                         base={"id": "SOR_030", "count": 1}, semantic_validated=False)
            child.write_bytes(P.encoded(value))
            parent = root / "index.json"
            parent.write_bytes(P.encoded(dict(result=P.pinned(child, child.read_bytes()),
                                               source_path="/Users/example/private-source.py")))
            pin = closure.copy(P.pinned(parent, parent.read_bytes()), root / "source.json", "index.json")
            index = closure.values[pin["url"]]
            copied = B.resolve_url(closure.stage, closure.stage / "index.json", index["result"]["url"])
            self.assertEqual(P.read_json(copied.read_bytes()), value)
            self.assertEqual(index["provenance_only"]["source_path"], "/Users/example/private-source.py")
            self.assertEqual(closure.verify_sources_unchanged(), 2)
            child.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "source changed"):
                closure.verify_sources_unchanged()

    def test_stored_gzip_evidence_keeps_exact_bytes_without_embedded_fetches(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); closure = self.closure(root)
            evidence = root / "receipt.json.gz"
            raw = gzip.compress(P.encoded(dict(delta=-3, path="/Users/example/not-a-fetch")), mtime=0)
            evidence.write_bytes(raw)
            original = dict(path=evidence.name, stored_sha256=P.digest(raw), stored_bytes=len(raw), encoding="gzip")
            entry = closure.sanitize(original, root / "index.json", "index.json")
            copied = B.resolve_url(closure.stage, closure.stage / "index.json", entry["url"])
            self.assertEqual(copied.read_bytes(), raw)
            self.assertEqual(entry["payload_role"], "raw-download-no-embedded-fetches")
            self.assertEqual(entry["provenance"]["original_record"], original)

    def test_plain_report_cannot_fetch_host_paths_and_original_is_archived(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); closure = self.closure(root)
            report = root / "report.md"; raw = b"MAE=-0.1; [source](/Users/example/data.json)\n"
            report.write_bytes(raw)
            entry = closure.copy(P.pinned(report, raw), root / "index.json")
            value = P.read_json((closure.stage / entry["url"]).read_bytes())
            self.assertIn("MAE=-0.1", value["text"])
            self.assertNotIn("/Users/", value["text"])
            self.assertEqual((closure.stage / entry["provenance"]["raw_archive"]["url"]).read_bytes(), raw)

    def test_required_data_hash_mismatch_is_not_downgraded(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); closure = self.closure(root)
            source = root / "results.json"; source.write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "pin mismatch"):
                closure.sanitize(dict(path=str(source), sha256="0" * 64), root / "index.json", "index.json")

    def test_historical_file_attestation_is_provenance_but_before_state_is_data(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); closure = self.closure(root)
            old = dict(path="/Users/example/changed.json", sha256="0" * 64)
            result = closure.sanitize(dict(before=old, state={"before": {"damage": 3}}), root / "receipt.json", "receipt.json")
            self.assertEqual(result["provenance_only"]["before"], old)
            self.assertEqual(result["state"]["before"], {"damage": 3})

    def test_urls_reject_traversal_schemes_and_query(self):
        for value in ("../data.json", "/data.json", "file:data.json", "https://example/data", "a\\b", "a/%2e%2e/b", "a?x", "a#x", "//example/a", "a//b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                B.safe_url(value)
        self.assertEqual(B.safe_url("assets/data.json"), "assets/data.json")

    def test_zip_is_deterministic(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); data = root / "bundle"; data.mkdir()
            (data / "a.json").write_bytes(b"{\"negative\":-1}\n")
            for filename in ("first.zip", "second.zip"):
                B.deterministic_zip(data, root / filename)
            self.assertEqual((root / "first.zip").read_bytes(), (root / "second.zip").read_bytes())

    def test_original_default_remains_exactly33_artifacts_and_six_assay_spaces(self):
        spaces = self.spaces()
        result = B.select_vector_spaces(dict.fromkeys(range(33)), {"spaces": spaces})
        self.assertEqual([row["id"] for row in result], ["space-independent_controls_" + str(i) for i in range(6)])
        with self.assertRaises(ValueError):
            B.select_vector_spaces(dict.fromkeys(range(38)), {"spaces": spaces})

    def test_explicit38_artifacts_and_all10_exact_ids_preserve_legacy_and_dimensions(self):
        spaces = self.spaces(); expected = [row["id"] for row in spaces.values()]
        result = B.select_vector_spaces(dict.fromkeys(range(38)), {"spaces": spaces}, expected_artifact_count=38,
                                        expected_space_count=10, all_registered_spaces=True, expected_space_ids=expected)
        self.assertEqual([row["id"] for row in result], expected)
        self.assertEqual(result[-1]["dimension"], 32)
        self.assertTrue(all(row["semantic_validated"] is False for row in result))
        for missing_ids in (None, expected[:-1], expected[:-1] + [expected[0]]):
            with self.subTest(ids=missing_ids), self.assertRaises(ValueError):
                B.select_vector_spaces(dict.fromkeys(range(38)), {"spaces": spaces}, expected_artifact_count=38,
                                       expected_space_count=10, all_registered_spaces=True, expected_space_ids=missing_ids)
        with self.assertRaises(ValueError):
            B.select_vector_spaces(dict.fromkeys(range(38)), {"spaces": spaces}, expected_artifact_count=38,
                                   expected_space_count=9, all_registered_spaces=True, expected_space_ids=expected)


if __name__ == "__main__":
    unittest.main()
