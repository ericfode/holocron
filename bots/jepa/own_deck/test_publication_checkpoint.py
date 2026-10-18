import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publication_checkpoint as P


def fixture(root):
    publication = dict(head_commit="a" * 40, tree="b" * 40, ci_run_id=1, ci_conclusion="success", merge_commit="c" * 40,
                       merged=True, merged_tree_matches_checked_head=True)
    index = dict(schema=P.INDEX_SCHEMA, publication=publication, counts=dict(optimizer_updates=4800), artifacts={})
    index_path, handoff_path = root / "index.json", root / "handoff.json"
    raw = P.encoded(index); index_path.write_bytes(raw)
    handoff = dict(schema=P.HANDOFF_SCHEMA, **{key: value for key, value in publication.items() if key != "merged"},
                   research_index=P.pinned(index_path, raw), counts=dict(optimizer_updates=4800))
    handoff_path.write_bytes(P.encoded(handoff))
    return index_path, handoff_path


class PublicationCheckpointTests(unittest.TestCase):
    def publish(self, root):
        i, h = fixture(root)
        before_i, before_h = i.read_bytes(), h.read_bytes()
        result = P.publish(i, h, root / "publications", root / "current.json", P.digest(before_i), P.digest(before_h))
        return result, before_i, before_h

    def test_consistent_pair_preserves_sources_and_archive(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            result, index_raw, handoff_raw = self.publish(root)
            final = Path(result["checkpoint_directory"])
            self.assertEqual((final / "research-index.json").read_bytes(), index_raw)
            self.assertEqual((final / "original-handoff.json").read_bytes(), handoff_raw)
            self.assertEqual((root / "handoff.json").read_bytes(), handoff_raw)
            handoff = P.read_json((final / "handoff.json").read_bytes())
            self.assertEqual(handoff["research_index"], result["artifacts"]["research_index"])
            self.assertEqual(handoff["head_commit"], "a" * 40)
            self.assertFalse(result["scope"]["portable"])
            self.assertEqual(result["stable_pointer_replacements"], 1)

    def test_metadata_mismatch_does_not_replace_pointer(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            i, h = fixture(root)
            changed = P.read_json(h.read_bytes()); changed["tree"] = "d" * 40
            h.write_bytes(P.encoded(changed))
            pointer = root / "current.json"; pointer.write_bytes(b"keep prior bytes")
            with self.assertRaises(ValueError):
                P.publish(i, h, root / "publications", pointer, P.digest(i.read_bytes()), P.digest(h.read_bytes()))
            self.assertEqual(pointer.read_bytes(), b"keep prior bytes")

    def test_directory_install_precedes_only_stable_pointer_replace(self):
        with tempfile.TemporaryDirectory() as name:
            import os
            operations = []
            rename, replace = os.rename, os.replace
            def record_rename(a, b):
                operations.append("install-directory"); return rename(a, b)
            def record_replace(a, b):
                operations.append("replace-pointer"); return replace(a, b)
            with patch.object(P.os, "rename", record_rename), patch.object(P.os, "replace", record_replace):
                self.publish(Path(name))
            self.assertEqual(operations, ["install-directory", "replace-pointer"])

    def test_corruption_and_immutable_directory_overwrite_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            result, _, _ = self.publish(root)
            i, h = root / "index.json", root / "handoff.json"
            with self.assertRaises(FileExistsError):
                P.publish(i, h, root / "publications", root / "current.json", P.digest(i.read_bytes()), P.digest(h.read_bytes()))
            Path(result["artifacts"]["research_index"]["path"]).write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                P.verify_pointer(root / "current.json")

    def test_wrong_source_hash_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            i, h = fixture(root)
            with self.assertRaises(ValueError):
                P.publish(i, h, root / "publications", root / "current.json", "0" * 64, P.digest(h.read_bytes()))
            self.assertFalse((root / "current.json").exists())


if __name__ == "__main__":
    unittest.main()
