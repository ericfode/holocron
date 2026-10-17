"""Declaration-label and family-split checks; no games or fitting."""
from collections import Counter
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import real_deck_data as R


def catalog():
    unit = dict(setId=dict(set="TST", number=1), setCodes=[], cost=2, power=3, hp=4,
                types=["unit"], aspects=["command"], keywords=[], traits=["rebel"], arena="ground")
    event = dict(setId=dict(set="TST", number=2), setCodes=[], cost=6, power=None, hp=None,
                 upgradePower=None, upgradeHp=None, types=["event"], aspects=[], keywords=[], traits=[])
    leader = dict(setId=dict(set="TST", number=101), setCodes=[], cost=0, types=["leader"], aspects=[], keywords=[], traits=[])
    base = dict(setId=dict(set="TST", number=102), setCodes=[], cost=None, types=["base"], aspects=[], keywords=[], traits=[])
    return dict(schema="swu-card-ir-cards/v1", cards=[dict(card=c, abilities={"ignored": "never a target"}) for c in (unit, event, leader, base)])


def deck():
    return dict(metadata=dict(name="synthetic-label-check"), leader=dict(id="TST_101"), base=dict(id="TST_102"),
                deck=[dict(id="TST_001", count=3), dict(id="TST_002", count=2)])


class RealDeckDataTests(unittest.TestCase):
    def test_only_printed_fields_enter_and_nonunit_nulls_have_documented_defaults(self):
        original = catalog()
        cards, normalized = R.printed_catalog(original)
        changed = copy.deepcopy(original)
        changed["cards"][0]["abilities"] = dict(effect=dict(amount=999, private="ignored"))
        changed["cards"][0]["runtimeAdmission"] = ["not input"]
        other, normalized_other = R.printed_catalog(changed)
        self.assertEqual(cards, other)
        self.assertEqual((normalized, normalized_other), (4, 4))
        self.assertNotIn("power", cards[1])
        self.assertNotIn("hp", cards[1])
        self.assertTrue(all(set(card) <= set(R.PRINTED_FIELDS) for card in cards))

    def test_auxiliary_labels_match_declared_counts_costs_and_initial_unit_probability(self):
        cards, _ = R.printed_catalog(catalog())
        aliases, metadata = R.catalog_index(cards)
        row, reason = R.encode_declaration(deck(), cards, aliases, metadata, 0)
        self.assertIsNone(reason)
        expected = np.zeros(13, np.float32)
        expected[:3] = [5 / 60, 3.6 / 10, 3 / 5]
        expected[3 + 2], expected[3 + 6], expected[12] = 3 / 5, 2 / 5, 3 / 5
        np.testing.assert_allclose(row["targets"], expected, atol=1e-7, rtol=0)
        self.assertEqual(row["metadata_known_fraction"], 1.)
        self.assertEqual(row["features"][1, 3], 0.)

    def test_missing_printed_cost_excludes_the_declaration_explicitly(self):
        source = catalog()
        source["cards"][0]["card"]["cost"] = None
        cards, _ = R.printed_catalog(source)
        aliases, metadata = R.catalog_index(cards)
        row, reason = R.encode_declaration(deck(), cards, aliases, metadata, 0)
        self.assertIsNone(row)
        self.assertIn("incomplete", reason["reason"])
        self.assertAlmostEqual(reason["known_metadata_fraction"], 2 / 5)
        self.assertAlmostEqual(reason["unknown_metadata_copies"], 3.)

    def test_leader_base_exact_copy_and_nearclone_edges_form_whole_components(self):
        def row(counts, leader, base):
            counts = Counter(counts)
            return dict(counts=counts, total_count=sum(counts.values()), fingerprint=R.fingerprint(counts), leader=leader, base=base)
        rows = [row(dict(a=3, b=2), "L1", "B1"), row(dict(d=3, e=2), "L1", "B2"),
                row(dict(f=3, g=2), "L3", "B2"), row(dict(a=3, b=1, c=1), "L4", "B4"),
                row(dict(z=5), "L5", "B5"), row(dict(a=3, b=2), "L6", "B6")]
        groups, edges = R.family_components(rows)
        self.assertEqual(sorted(map(len, groups.values())), [1, 5])
        reasons = {reason for edge in edges for reason in edge["reasons"]}
        self.assertEqual(reasons, {"leader", "base", "fingerprint", "nearclone-copy-overlap"})

    def test_split_and_wrong_own_controls_are_deterministic_and_partition_local(self):
        records = []
        for i in range(8):
            targets = np.zeros(13, np.float32)
            targets[1], targets[3 + i] = i / 10, 1
            records.append(dict(fingerprint=R.fingerprint({str(i): 50}), targets=targets))
        groups = {f"F{i}": [i] for i in range(8)}
        train, val = R.grouped_split(groups, 8, validation_target=2)
        repeated = R.grouped_split(dict(reversed(list(groups.items()))), 8, validation_target=2)
        for a, b in zip((train, val), repeated):
            np.testing.assert_array_equal(a, b)
        wrong, modes = R.wrong_own_indices(records, np.asarray(list(groups)), (train, val))
        self.assertEqual(modes, ["different-family-fingerprint-and-curve"] * 2)
        for partition in (train, val):
            self.assertEqual(set(wrong[partition]), set(partition))
            self.assertTrue(np.all(wrong[partition] != partition))
        with self.assertRaises(ValueError):
            R.grouped_split({"one": [0], "two": [1]}, 2)

    def test_prepared_real_artifact_has_full_coverage_and_zero_split_overlap(self):
        directory = R.REPO.parent / "experiments/data"
        if not (directory / "real-decks.npz").is_file():
            self.skipTest("local source-backed artifact has not been prepared")
        manifest = json.loads((directory / "real-decks.manifest.json").read_text())
        self.assertEqual(manifest["artifact"]["sha256"], R.sha256(directory / "real-decks.npz"))
        self.assertEqual(manifest["included_deck_count"], 27)
        self.assertEqual(manifest["excluded"], [])
        self.assertEqual(manifest["provenance"]["kessel_commit"], R.KESSEL_COMMIT)
        self.assertEqual(manifest["target_groups"], dict(count=[0], curve=list(range(1, 12)), draw=[12]))
        for source in manifest["sources"]:
            self.assertEqual(source["sha256"], R.sha256(source["path"]))
        with np.load(directory / "real-decks.npz", allow_pickle=False) as data:
            self.assertEqual(data["deck_features"].shape, (27, 2, 207))
            self.assertEqual(data["targets"].shape, (27, 13))
            train, val, wrong = data["train_idx"], data["val_idx"], data["wrong_idx"]
            self.assertEqual((len(train), len(val)), (22, 5))
            self.assertEqual(set(data["fingerprints"][train]) & set(data["fingerprints"][val]), set())
            self.assertEqual(set(data["family_ids"][train]) & set(data["family_ids"][val]), set())
            np.testing.assert_array_equal(data["deck_features"][:, 0, 3], np.ones(27))
            np.testing.assert_array_equal(data["deck_features"][:, 1, 3], np.zeros(27))
            np.testing.assert_allclose(data["targets"][:, 0], data["deck_features"][:, 0, 4], atol=1e-7)
            np.testing.assert_allclose(data["targets"][:, 1], data["deck_features"][:, 0, 8], atol=1e-7)
            np.testing.assert_allclose(data["targets"][:, 3:12].sum(1), np.ones(27), atol=1e-6)
            np.testing.assert_allclose(data["targets"][:, 12], data["deck_features"][:, 0, 11], atol=1e-7)
            for partition in (train, val):
                self.assertEqual(set(wrong[partition]), set(partition))
                self.assertTrue(np.all(data["fingerprints"][partition] != data["fingerprints"][wrong[partition]]))
                self.assertTrue(np.all(data["family_ids"][partition] != data["family_ids"][wrong[partition]]))
                self.assertTrue(all(not np.array_equal(data["targets"][i, 1:12], data["targets"][wrong[i], 1:12]) for i in partition))


if __name__ == "__main__":
    unittest.main()
