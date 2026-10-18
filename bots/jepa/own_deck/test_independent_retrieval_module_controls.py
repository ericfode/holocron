"""Pure exact-profile contract checks, without catalogue generation or models."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_retrieval_module_controls as M


def row(power=2, hp=4, keywords=None):
    return dict(card=dict(cost=2, types=["unit"], arena="ground", aspects=["vigilance", "heroism"],
                          power=power, hp=hp, keywords=keywords or []))


class ModuleControlTests(unittest.TestCase):
    def test_signature_requires_stats_but_keyword_difference_is_separate(self):
        a, b = row(), row(keywords=["sentinel"])
        self.assertEqual(M.strict_signature(a), M.strict_signature(b))
        b["card"]["aspects"].reverse()
        self.assertEqual(M.strict_signature(a), M.strict_signature(b))
        self.assertNotEqual(M.strict_signature(a), M.strict_signature(row(hp=5)))
        self.assertNotEqual(M.strict_signature(a), M.strict_signature(row(power=3)))

    def test_entire_profile_matches_for_both_doses_and_detects_nuisance(self):
        cards = {"A": row(), "B": row(keywords=["shielded"]), "C": row(hp=5)}
        anchor = dict(deck=[dict(id="A", count=3)])
        for dose in (1, 2):
            variant = dict(deck=[dict(id="A", count=3-dose), dict(id="B", count=dose)])
            self.assertEqual(M.profile(anchor, cards), M.profile(variant, cards))
        variant = dict(deck=[dict(id="A", count=2), dict(id="C", count=1)])
        self.assertNotEqual(M.profile(anchor, cards), M.profile(variant, cards))

    def test_scope_is_synthetic_and_has_no_execution_allocation(self):
        plan = M.plan()
        self.assertEqual(plan["maximum_new_rows"], 21)
        self.assertEqual(plan["source_indices"], [10, 14, 25])
        self.assertEqual(plan["model_forward_calls"], 0)
        self.assertEqual(plan["native_calls"], 0)
        self.assertIn("not a relaxed v1", plan["interpretation"])


if __name__ == "__main__":
    unittest.main()
