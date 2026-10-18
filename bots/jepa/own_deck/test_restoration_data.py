"""Matched restoration construction and lineage tests; no fitting or games."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restoration_data as D


def synthetic():
    rows, decks = [], []
    for i in range(4):
        def card(number, types, **kwargs):
            value = dict(id=str(number), title=f"Synthetic {number}", subtitle="", setId=dict(set="TST", number=number),
                         setCodes=[], types=types, aspects=["command"], keywords=[], traits=["rebel"], **kwargs)
            rows.append(dict(card=value, status="supported"))
            return f"TST_{number:03}"
        leader = card(100 + i, ["leader"], cost=0)
        base = card(200 + i, ["base"], cost=0)
        units = [card(1 + i * 4 + j, ["unit"], cost=2, power=2, hp=3, arena="ground") for j in range(4)]
        decks.append(dict(metadata=dict(name=f"Synthetic source {i}"), leader=dict(id=leader), base=dict(id=base),
                          deck=[dict(id=code, count=1) for code in units]))
    catalog = dict(schema="swu-card-ir-cards/v1", cards=rows)
    cards, _ = D.R.printed_catalog(catalog)
    aliases, _ = D.R.catalog_index(cards)
    bank = dict(declarations=[dict(source_index=i, family_id=f"family-{i}", name=f"source-{i}",
                                   fingerprint=D.R.fingerprint(D.canonical_counts(deck, aliases))) for i, deck in enumerate(decks)],
                split=dict(train_idx=[0, 1], val_idx=[2, 3], rule="fixed synthetic whole-family split"))
    policy = dict(primary_construction_scope_supported=True, allowed_printed_sets=["TST"], suspended_codes=[],
                  suspended_card_ids=[], minimum_main_count=4, max_same_name_subtitle_copies=3, base_min_overrides={})
    return decks, catalog, bank, policy


class RestorationDataTests(unittest.TestCase):
    def test_admission_fails_closed_for_printing_suspension_types_and_metadata(self):
        decks, catalog, _, policy = synthetic()
        source = decks[0]
        printings = D.raw_printings(catalog)
        self.assertTrue(D.eligibility(source, printings, policy)["admitted"])
        for change in (dict(primary_construction_scope_supported=False), dict(allowed_printed_sets=["OTHER"]),
                       dict(suspended_codes=["TST_001"]), dict(suspended_card_ids=["1"])):
            self.assertFalse(D.eligibility(source, printings, {**policy, **change})["admitted"])
        for bad in (dict(id="TST_100", count=1), dict(id="TST_999", count=1), dict(id="TST_001", count=True)):
            deck = copy.deepcopy(source)
            deck["deck"][0] = bad
            self.assertFalse(D.eligibility(deck, printings, policy)["admitted"])
        deck = copy.deepcopy(source)
        deck["leader"]["count"] = True
        self.assertFalse(D.eligibility(deck, printings, policy)["admitted"])

    def test_name_subtitle_cap_across_reprints_and_sideboard_and_base_minimum(self):
        decks, catalog, _, policy = synthetic()
        printing = copy.deepcopy(catalog["cards"][2])
        printing["card"]["setId"] = dict(set="TST", number=99)
        catalog["cards"].append(printing)
        printings = D.raw_printings(catalog)
        deck = copy.deepcopy(decks[0])
        deck["deck"][0]["count"] = 3
        deck["sideboard"] = [dict(id="TST_099", count=1)]
        result = D.eligibility(deck, printings, policy)
        self.assertIn("same name and subtitle exceeds canonical copy cap", result["reasons"])
        deck["sideboard"][0]["count"] = "bad"
        self.assertFalse(D.eligibility(deck, printings, policy)["admitted"])
        minimum = {**policy, "base_min_overrides": {"TST_200": 5}}
        self.assertFalse(D.eligibility(decks[0], printings, minimum)["admitted"])
        self.assertFalse(D.eligibility(decks[0], printings, {**policy, "minimum_main_count": 5})["admitted"])

    def test_changed_deck_is_unordered_copy_aware_and_restores_exact_original(self):
        decks, catalog, _, _ = synthetic()
        source = decks[0]
        duplicate = copy.deepcopy(source)
        duplicate["deck"] = [dict(id="TST_001", count=1), dict(id="TST_001", count=1), *source["deck"][1:]]
        merged = copy.deepcopy(source)
        merged["deck"][0]["count"] = 2
        self.assertEqual(D.changed_deck(duplicate, ["TST_001"], ["TST_005"]), D.changed_deck(merged, ["TST_001"], ["TST_005"]))
        reverse = copy.deepcopy(source)
        reverse["deck"].reverse()
        self.assertEqual(D.changed_deck(reverse, [], []), D.changed_deck(source, [], []))
        self.assertEqual(D.changed_deck(source, ["TST_001", "TST_002"], ["TST_001", "TST_002"])["deck"], source["deck"])
        with self.assertRaises(ValueError):
            D.changed_deck(source, ["TST_001"] * 2, [])

    def test_fixed_size_matches_are_exact_coarse_printed_and_construction_admitted(self):
        decks, catalog, _, policy = synthetic()
        cards, _ = D.R.printed_catalog(catalog)
        aliases, metadata = D.R.catalog_index(cards)
        printings = D.raw_printings(catalog)
        match, failure = D.choose_alternatives(decks[0], ["TST_001", "TST_002"], {"TST_005", "TST_006"}, aliases, metadata, printings, policy)
        self.assertIsNone(failure)
        alternatives, controls = match
        changed = D.changed_deck(decks[0], ["TST_001", "TST_002"], alternatives)
        self.assertTrue(D.eligibility(changed, printings, policy)["admitted"])
        self.assertEqual(sum(e["count"] for e in changed["deck"]), 4)
        for code, alt in zip(["TST_001", "TST_002"], alternatives):
            self.assertEqual(D.signature(metadata[aliases[code]]), D.signature(metadata[aliases[alt]]))
        self.assertTrue(all(c["exact_traits"] for c in controls))
        match, failure = D.choose_alternatives(decks[0], ["TST_001"], {"TST_005"}, aliases, metadata, printings, policy, {0: ["rebel"]})
        self.assertIsNone(match)
        self.assertIn("no admitted", failure["reason"])

    def test_fit_provenance_balanced_heldout_intact_and_incomplete_never_labeled(self):
        decks, catalog, bank, policy = synthetic()
        data, manifest = D.construct(decks, catalog, bank, policy)
        self.assertTrue(manifest["primary_experiment_admitted"])
        self.assertEqual(len(manifest["curve_groups"]), 4)
        self.assertEqual(data["fit_labels"].tolist(), [1, 0] * 4)
        self.assertFalse(any("incomplete" in k for k in data["fit_kind"]))
        self.assertEqual(set(data["eval_source_idx"]), {2, 3})
        self.assertEqual(set(data["fit_family_ids"][data["train_idx"]]) & set(data["fit_family_ids"][data["val_idx"]]), set())
        self.assertEqual(set(data["fit_fingerprints"][data["train_idx"]]) & set(data["fit_fingerprints"][data["val_idx"]]), set())
        authored = {r["fingerprint"] for r in bank["declarations"]}
        for r in manifest["fit_records"]:
            self.assertEqual(r["fingerprint"] in authored, r["label"] == 1)
        np.testing.assert_array_equal(data["fit_features"][:, 1, 3], 0)
        for gid in manifest["curve_groups"]:
            rows = [r for r in manifest["eval_records"] if r["group_id"] == gid]
            if not rows:
                continue
            true = [r for r in rows if r["kind"] == "true-restoration"]
            anchor = [r for r in rows if r["kind"] == "matched-alternative"]
            incomplete = [r for r in rows if r["kind"] == "incomplete-diagnostic"]
            self.assertEqual({r["total_count"] for r in true + anchor}, {4})
            self.assertEqual(len({r["fingerprint"] for r in anchor}), 1)
            self.assertEqual({r["actual_original_copies_restored"] for r in anchor}, {0})
            self.assertEqual([r["actual_original_copies_restored"] for r in true], [0, 1])
            self.assertEqual([r["total_count"] for r in incomplete], [3, 4])
            self.assertTrue(all(not r["rule_eligibility"]["admitted"] for r in incomplete))

    def test_ineligible_source_excluded_without_repartition(self):
        decks, catalog, bank, policy = synthetic()
        policy["suspended_codes"] = ["TST_102"]
        data, manifest = D.construct(decks, catalog, bank, policy)
        self.assertEqual([r["source_idx"] for r in manifest["excluded_source_lineages"]], [2])
        self.assertNotIn(2, data["fit_source_idx"])
        self.assertNotIn(2, data["eval_source_idx"])
        self.assertFalse(manifest["primary_experiment_admitted"])
        self.assertEqual(manifest["inherited_split"]["source_val_indices"], [2, 3])
        self.assertFalse(manifest["inherited_split"]["repartitioned"])

    def test_canonical_negative_equal_authored_is_skipped(self):
        decks, catalog, bank, policy = synthetic()
        # Make source 1 exactly a one-copy alternative to source 0. There are no
        # other train candidates, so neither authored bag becomes a negative.
        decks[1]["deck"] = copy.deepcopy(decks[0]["deck"])
        decks[1]["deck"][0]["id"] = "TST_005"
        cards, _ = D.R.printed_catalog(catalog)
        aliases, _ = D.R.catalog_index(cards)
        bank["declarations"][1]["fingerprint"] = D.R.fingerprint(D.canonical_counts(decks[1], aliases))
        data, manifest = D.construct(decks, catalog, bank, policy)
        self.assertTrue(any("equals an authored" in str(g["reason"]) for g in manifest["coverage_gaps"]))
        authored = {r["fingerprint"] for r in bank["declarations"]}
        self.assertTrue(all(r["fingerprint"] not in authored for r in manifest["fit_records"] if r["label"] == 0))

    def test_construct_permutation_and_ir_pointer_preserve_order(self):
        decks, catalog, bank, policy = synthetic()
        first, manifest = D.construct(decks, catalog, bank, policy)
        permuted = copy.deepcopy(decks)
        for d in permuted:
            d["deck"].reverse()
        second, other = D.construct(permuted, catalog, bank, policy)
        for key in first:
            np.testing.assert_array_equal(first[key], second[key], err_msg=key)
        self.assertEqual(manifest["curve_groups"], other["curve_groups"])
        operations = dict(abilities=dict(card=[dict(effect=[dict(kind="resource"), dict(kind="damage")])]))
        self.assertEqual(D.pointer(operations, "/abilities/card/0/effect"), [dict(kind="resource"), dict(kind="damage")])

    def test_real_artifact_admission_matching_package_witness_and_coverage(self):
        directory = D.R.REPO.parent / "experiments/restoration"
        path = directory / "restoration-data.manifest.json"
        if not path.is_file():
            self.skipTest("source-backed restoration fixtures not yet prepared")
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["artifact"]["sha256"], D.R.sha256(directory / "restoration-data.npz"))
        self.assertTrue(manifest["primary_experiment_admitted"])
        self.assertEqual([r["source_idx"] for r in manifest["excluded_source_lineages"]], [3])
        self.assertEqual(manifest["inherited_split"]["source_val_indices"], [2, 3, 10, 14, 25])
        self.assertTrue(all(g["source_admission"]["admitted"] for g in manifest["curve_groups"].values()))
        self.assertTrue(all(c["exact_cost_type_arena_aspects"] for g in manifest["curve_groups"].values() for c in g["controls"]))
        packages = [g for g in manifest["curve_groups"].values() if g["kind"] == "rule-grounded-package"]
        self.assertTrue(any(g["partition"] == "val" for g in packages))
        catalog_path = next(Path(s["path"]) for s in manifest["sources"] if s["path"].endswith("compiler/generated/cards.json"))
        printings = D.raw_printings(json.loads(catalog_path.read_text()))
        for group in packages:
            witness = group["rule_witness"]
            raw = printings[witness["payoff"]]
            self.assertEqual(witness["ir_status"], "supported")
            for field, node in (("predicate", "predicate_node"), ("owner", "ownership_node"), ("effect", "effect_node")):
                self.assertEqual(D.pointer(raw, witness[field]), witness[node])
            self.assertEqual(witness["source_hash"], raw["sourceHash"])
            self.assertTrue(witness["shared_traits"])
            self.assertTrue(group["controls"][0]["intentionally_absent_traits"])
        with np.load(directory / "restoration-data.npz", allow_pickle=False) as data:
            self.assertEqual(data["fit_features"].shape, (56, 2, 207))
            self.assertEqual(data["eval_features"].shape, (27, 2, 207))
            self.assertEqual(set(data["eval_source_idx"]), {2, 14, 25})
            self.assertTrue(set(data["eval_family_ids"]) <= set(data["fit_family_ids"][data["val_idx"]]))
            for prefix in ("fit", "eval"):
                self.assertTrue(np.isfinite(data[prefix + "_features"]).all())
                np.testing.assert_array_equal(data[prefix + "_features"][:, 1, 3], 0)
            for gid, group in manifest["curve_groups"].items():
                # Exact size, curve, coarse type/arena and aspect controls are
                # actual input invariants, not merely manifest assertions.
                fit_rows = np.flatnonzero(data["fit_group_ids"] == gid)
                feature_columns = [4, 8, *range(11, 25), *range(35, 41)]
                expected = data["fit_features"][fit_rows[0], 0, feature_columns]
                for i in fit_rows:
                    np.testing.assert_array_equal(data["fit_features"][i, 0, feature_columns], expected)
                for i in np.flatnonzero(data["eval_group_ids"] == gid):
                    if data["eval_kind"][i] != "incomplete-diagnostic":
                        np.testing.assert_array_equal(data["eval_features"][i, 0, feature_columns], expected)
                        self.assertEqual(data["eval_total_count"][i], group["original_count"])


if __name__ == "__main__":
    unittest.main()
