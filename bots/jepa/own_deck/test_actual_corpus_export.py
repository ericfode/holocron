import copy
import gzip
from pathlib import Path
import tempfile
import unittest

import actual_corpus_export as E


CODES = ("ASH_048", "JTL_095", "SEC_163", "LOF_077", "JTL_078", "JTL_158", "LOF_155", "JTL_217")


def fixture(root):
    """Protocol fixtures only; never scientific/production vector artifacts."""
    decks, saved = [], []
    for i in range(27):
        known = 3 if i < 21 else 2 if i == 21 else 0
        total = 50 if i < 26 else 132
        counts = {"TST_999": total - known}
        if known:
            counts[CODES[i % 8]] = known
        metadata = dict(source_index=i, family_id="family-" + str(i), split="train" if i < 22 else "held",
                        composition_fingerprint=str(i).zfill(64))
        decks.append(dict(metadata, total_main_copies=total, leader={"id": "TST_001", "count": 1},
                          base={"id": "TST_002", "count": 1}, main_cards=[dict(canonical_id=k, copies=v) for k, v in counts.items()]))
        saved.append(dict(metadata, canonical_card_counts=counts, total_count=total, vector=[float(i + 1)] + [0.] * 31,
                          coverage_layers={"learned": known / total}))
    coverage = dict(schema="jepa-actual-corpus-coverage/1", status="data-only-pre-native-pre-model",
                    summary={"proposed_native_fixture": {"ids": list(CODES), "copies": 65}}, decks=decks)
    card = dict(schema="whole-card-frozen-vectors/1", arm="correct-typed", dimensions=16,
                cards=[dict(code=code, vector=[float(i + 1)] + [0.] * 15, runtime_admitted=True,
                            native_fixture_observed=True, training_card=i < 6, semantic_validated=False) for i, code in enumerate(CODES)])
    deck = dict(schema="actual-corpus-deck-frozen-vectors/1", arm="correct-typed", dimension=32,
                semantic_validated=False, rows=saved)
    values = dict(coverage=coverage, card_vectors=card, deck_vectors=deck,
                  coverage_verification={"status": "verified", "artifact": {"sha256": E.digest(E.encoded(coverage))}},
                  native_result={"schema": "jepa-actual-corpus-native/1", "selectedWholeCards": list(CODES),
                                 "collectionPlan": {"cards": [{"code": code} for code in CODES], "selected_whole_cards": list(CODES)},
                                 "cases": [{"card": code} for code in CODES for _ in range(4)]},
                  card_result={"status": "completed", "all_arms": {"wrong": {"head": {"signed_residual": -2, "support": 0, "mae": None}}}},
                  deck_result={"status": "completed", "per_deck": {"unknown": [True, False]}, "negative_result": -1})
    artifacts = {}
    for role, value in values.items():
        path = root / (role + ".json"); path.write_bytes(E.encoded(value)); artifacts[role] = E.pin(path)
    spec = dict(version=E.VERSION, source_commit="a" * 40, artifacts=artifacts)
    return spec, coverage, card, deck


class ActualCorpusExportTests(unittest.TestCase):
    def test_masks_and_raw_vectors_preserve_partial_coverage(self):
        with tempfile.TemporaryDirectory() as name:
            _, coverage, cards, decks = fixture(Path(name))
            card, deck = E.browser_payloads(coverage, cards, decks)
            self.assertEqual([r["vector"] for r in card["rows"]], [r["vector"] for r in sorted(cards["cards"], key=lambda x: x["code"])])
            self.assertEqual(deck["coverage"], dict(main_copies=1432, known_copies=65, unknown_copies=1367))
            self.assertEqual(sum(r["known_copy_count"] for r in deck["rows"]), 65)
            self.assertFalse(deck["rows"][-1]["whole_deck_semantics_known"])
            self.assertTrue(all(deck["rows"][-1]["unknown_card_mask"]))
            for row in deck["rows"]:
                self.assertEqual(row["unknown_card_mask"], [not x for x in row["known_card_mask"]])
                self.assertFalse(row["semantic_validated"])
                self.assertFalse(row["remaining_known"])

    def test_full_negative_heads_and_source_bytes_survive_package(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); spec, _, _, _ = fixture(root)
            sentinel = root / "current-index.json"; sentinel.write_bytes(b"unchanged")
            before = {k: Path(v["path"]).read_bytes() for k, v in spec["artifacts"].items()}
            plan = E.prepare(spec)
            receipt = E.package(plan, root / "evidence", root / "vectors", gzip_threshold=1)
            index = E.read((root / "evidence/index.json").read_bytes())
            for entry in index["files"]:
                if entry["source_kind"] != "byte-copy":
                    continue
                raw = (root / "evidence" / entry["path"]).read_bytes()
                decoded = gzip.decompress(raw) if entry["encoding"].startswith("gzip") else raw
                self.assertEqual(decoded, before[entry["role"]])
            fragment = E.read((root / "vectors/index-fragment.json").read_bytes())
            self.assertEqual(fragment["status"], "review-only-not-merged")
            self.assertEqual(sentinel.read_bytes(), b"unchanged")
            self.assertEqual(receipt["neural_forwards"], 0)
            self.assertFalse(receipt["current_indexes_modified"])
            self.assertFalse(receipt["semantic_validated"])
            for k, record in spec["artifacts"].items():
                self.assertEqual(Path(record["path"]).read_bytes(), before[k])

    def test_preexisting_outputs_and_changed_pins_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); spec, _, _, _ = fixture(root); plan = E.prepare(spec)
            existing = root / "evidence"; existing.mkdir()
            with self.assertRaises(FileExistsError):
                E.package(plan, existing, root / "vectors")
            Path(spec["artifacts"]["card_vectors"]["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                E.package(plan, root / "new-evidence", root / "vectors")

    def test_counts_families_and_no_fake_card_rows(self):
        with tempfile.TemporaryDirectory() as name:
            _, coverage, cards, decks = fixture(Path(name))
            for changed in ("counts", "family", "extra_card"):
                c, d = copy.deepcopy(cards), copy.deepcopy(decks)
                if changed == "counts": d["rows"][0]["canonical_card_counts"]["TST_999"] += 1
                if changed == "family": d["rows"][0]["family_id"] = "other"
                if changed == "extra_card": c["cards"].append(dict(c["cards"][0], code="TST_888"))
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    E.browser_payloads(coverage, c, d)

    def test_invalid_vectors_and_semantic_status_are_rejected(self):
        for value in ([True] + [0.] * 15, [float("nan")] + [0.] * 15, [0.], [float("inf")] + [0.] * 15):
            with self.subTest(value=value), self.assertRaises(ValueError):
                E.vector({"vector": value}, 16)
        with tempfile.TemporaryDirectory() as name:
            _, coverage, cards, decks = fixture(Path(name))
            cards["cards"][0]["semantic_validated"] = True
            with self.assertRaises(ValueError): E.browser_payloads(coverage, cards, decks)

    def test_deterministic_gzip_and_no_source_selection(self):
        raw = E.encoded({"all_heads": {"unknown": None, "negative": -7, "failed": False}})
        self.assertEqual(E.deterministic_gzip(raw), E.deterministic_gzip(raw))
        self.assertEqual(gzip.decompress(E.deterministic_gzip(raw)), raw)

    def test_native_helpers_allowed_but_source_ids_and_full_plan_must_match(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); spec, _, _, _ = fixture(root)
            native_path = Path(spec["artifacts"]["native_result"]["path"])
            native = E.read(native_path.read_bytes())
            native["selectedWholeCards"].extend(["TST_001", "TOKEN_SHIELD"])
            native["collectionPlan"]["selected_whole_cards"] = list(native["selectedWholeCards"])
            native_path.write_bytes(E.encoded(native)); spec["artifacts"]["native_result"] = E.pin(native_path)
            self.assertEqual(E.prepare(spec)["status"], "frozen-export-inputs-verified")
            for changed in ("source", "case", "helper"):
                bad = copy.deepcopy(native)
                if changed == "source": bad["collectionPlan"]["cards"][0]["code"] = "TST_001"
                if changed == "case": bad["cases"][0]["card"] = "TST_001"
                if changed == "helper": bad["selectedWholeCards"].append("TOKEN_EXPERIENCE")
                native_path.write_bytes(E.encoded(bad)); spec["artifacts"]["native_result"] = E.pin(native_path)
                with self.subTest(changed=changed), self.assertRaises(ValueError): E.prepare(spec)

    def test_verified_status_never_bypasses_coverage_hash_binding(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); spec, _, _, _ = fixture(root)
            path = Path(spec["artifacts"]["coverage_verification"]["path"])
            value = E.read(path.read_bytes()); value["artifact"]["sha256"] = "0" * 64
            path.write_bytes(E.encoded(value)); spec["artifacts"]["coverage_verification"] = E.pin(path)
            with self.assertRaisesRegex(ValueError, "exact coverage artifact"):
                E.prepare(spec)


if __name__ == "__main__":
    unittest.main()
