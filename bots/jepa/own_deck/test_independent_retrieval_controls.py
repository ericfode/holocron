"""Synthetic contract checks; no source-bank generation, encoder or native calls."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_retrieval_controls as C


def card(effect=None):
    return dict(setCode="JTL_100", status="supported", card=dict(types=["unit"], power=2, hp=3,
                traits=["imperial"], keywords=[], unique=False),
                abilities={"card": [dict(trigger="action", title="Display text", costs=[dict(kind="exhaustSelf")],
                    targetResolver=dict(owner="opponent", type="unit", zone="arena"),
                    effect=effect or dict(kind="damage", target="chosen", amount=dict(kind="const", value=1)))]})


def known(row):
    return C.descriptor(row, {row["setCode"]: dict(implementation="sourceIr")})


class IRControlTests(unittest.TestCase):
    def test_display_and_object_order_are_invariant_but_effect_order_is_not(self):
        a = card(dict(kind="sequence", effects=[dict(kind="damage", target="chosen", amount=dict(kind="const", value=1)),
                                               dict(kind="heal", target="chosen", amount=dict(kind="const", value=2))]))
        b = json.loads(json.dumps(a, sort_keys=True))
        b["abilities"]["card"][0]["title"] = "Different display title"
        self.assertEqual(C.ir_distance(known(a), known(b))["distance"], 0.)
        b["abilities"]["card"][0]["effect"]["effects"].reverse()
        result = C.ir_distance(known(a), known(b))
        self.assertGreater(result["parts"]["effects"], 0.)
        self.assertEqual(result["parts"]["costs"], 0.)

    def test_amount_magnitude_cost_target_and_condition_are_retained(self):
        a = card()
        b, c = copy.deepcopy(a), copy.deepcopy(a)
        b["abilities"]["card"][0]["effect"]["amount"]["value"] = 2
        c["abilities"]["card"][0]["effect"]["amount"]["value"] = 9
        self.assertLess(C.ir_distance(known(a), known(b))["distance"], C.ir_distance(known(a), known(c))["distance"])
        b = copy.deepcopy(a)
        b["abilities"]["card"][0]["costs"].append(dict(kind="resources", amount=dict(kind="const", value=1)))
        b["abilities"]["card"][0]["targetResolver"]["owner"] = "self"
        b["abilities"]["card"][0]["condition"] = dict(kind="const", value=True)
        parts = C.ir_distance(known(a), known(b))["parts"]
        self.assertGreater(parts["costs"], 0.)
        self.assertGreater(parts["conditions_targets"], 0.)

    def test_unknown_or_native_adapter_is_not_an_empty_effect(self):
        a = card()
        missing = C.descriptor(a, {})
        self.assertFalse(missing["known"])
        self.assertIsNone(C.ir_distance(known(a), missing)["distance"])
        adapter = C.descriptor(a, {"JTL_100": dict(implementation="nativeAdapters")})
        self.assertFalse(adapter["known"])
        b = copy.deepcopy(a); del b["abilities"]
        self.assertFalse(known(b)["known"])
        b = copy.deepcopy(a); b["abilities"] = {}
        self.assertTrue(known(b)["known"])
        self.assertGreater(C.ir_distance(known(a), known(b))["distance"], 0.)

    def test_printed_mechanics_cannot_change_selection_proxy(self):
        a, b = card(), card()
        b["card"].update(traits=["jedi"], keywords=["sentinel"], power=9, hp=12)
        self.assertEqual(C.ir_distance(known(a), known(b))["distance"], 0.)
        separate = C.printed_distance(C.printed_descriptor(a), C.printed_descriptor(b))
        self.assertGreater(separate["distance"], 0.)
        self.assertFalse(separate["used_for_near_far_selection"])

    def test_copy_distance_is_tied_for_distinct_novel_identity_substitutions(self):
        source = {"A": 3, "B": 47}
        near, far = {"A": 1, "B": 47, "C": 2}, {"A": 1, "B": 47, "D": 2}
        self.assertEqual(C.count_baseline(source, near), C.count_baseline(source, far))
        self.assertEqual(C.count_baseline(source, near)["shared_copies"], 48)
        self.assertEqual(C.count_baseline(source, near)["union_copies"], 52)
        self.assertEqual(C.count_baseline(source, source)["weighted_jaccard"], 1.)

    def test_entire_reviewed_family_is_excluded(self):
        rows = [dict(source_index=i, family_id=f"f-{i}") for i in range(26)]
        rows[2]["family_id"] = rows[3]["family_id"]
        excluded = C.family_exclusion(rows, {"deck-source-03"})
        self.assertIn(2, excluded["all_source_indices_in_excluded_families"])
        self.assertIn(3, excluded["all_source_indices_in_excluded_families"])
        rows[10]["family_id"] = rows[3]["family_id"]
        with self.assertRaisesRegex(ValueError, "reviewed family"):
            C.family_exclusion(rows, {"deck-source-03"})

    def test_nonfinite_ir_fails_closed_and_plan_has_no_model_budget(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            list(C.atoms(dict(amount=float("nan"))))
        plan = C.fixed_plan()
        self.assertEqual(plan["maximum_modified"], 24)
        self.assertEqual(plan["maximum_rows"], 36)
        self.assertEqual(plan["source_indices"], [10, 14, 25])
        self.assertEqual(plan["model_forward_calls"], 0)
        self.assertEqual(plan["native_calls"], 0)


if __name__ == "__main__":
    unittest.main()
