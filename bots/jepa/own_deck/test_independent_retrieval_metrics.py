"""Pure arithmetic/lineage checks; no NumPy, learned vectors or NN execution."""
import unittest
import independent_retrieval_metrics as M


class RetrievalMetricsTests(unittest.TestCase):
    def test_fixed_tie_and_rank(self):
        self.assertEqual(M.order_result(1., 1.+5e-11)["result"], "tie")
        self.assertEqual(M.order_result(1., .9)["near_rank"], 1.)
        self.assertEqual(M.order_result(.9, 1.)["near_rank"], 2.)
        self.assertEqual(M.order_result(1., 1.)["near_rank"], 1.5)

    def test_unknown_not_negative(self):
        self.assertEqual(M.order_result(None, .5)["result"], "unknown")
        self.assertIsNone(M.order_result(None, .5)["half_credit"])

    def test_family_macro_does_not_count_more_slots_as_more_families(self):
        records = [dict(source_index=14, source_card="a", **M.order_result(1., 0.)),
                   dict(source_index=14, source_card="b", **M.order_result(1., 0.)),
                   dict(source_index=25, source_card="c", **M.order_result(0., 1.))]
        result = M.aggregate(records)
        self.assertEqual(result["family_macro_half_credit"], .5)
        self.assertAlmostEqual(result["slot_macro_half_credit"], 2/3)
        self.assertEqual(result["source_families"], 2)

    def test_absent_strict_support_stays_unknown(self):
        result = M.aggregate([])
        self.assertEqual(result["known_comparisons"], 0)
        self.assertIsNone(result["family_macro_half_credit"])

    def test_pair_matching_rejects_count_confound(self):
        rows = [dict(id=str(i), kind="anchor", source_index=i) for i in (10,14,25)]
        for kind, count, distance in (("ir-near", 1, .1), ("ir-far", 2, .5)):
            rows.append(dict(kind=kind, source_index=14,
                             lineage=dict(source_card="a", copies=1, stratum="strict-power-hp"),
                             count_baseline=dict(shared=count), mechanical_labels=dict(ir_only=dict(distance=distance))))
        with self.assertRaisesRegex(ValueError, "overlap differs"):
            M.comparison_groups(rows)

    def test_synthetic_anchor_is_not_original_source_anchor(self):
        rows = [dict(id=str(i), kind="anchor", source_index=i) for i in (10,14,25)]
        rows.append(dict(id="synthetic10", kind="module-anchor", source_index=10))
        for kind, distance in (("ir-near", .1), ("ir-far", .5)):
            rows.append(dict(id=kind, assay="v2-synthetic", anchor_id="synthetic10", module_id="module1",
                             kind=kind, source_index=10,
                             lineage=dict(source_card="a", copies=1, stratum="strict-power-hp"),
                             count_baseline=dict(shared=49), mechanical_labels=dict(ir_only=dict(distance=distance))))
        result = M.comparison_groups(rows)
        self.assertEqual(result[0]["anchor"], 3)
        self.assertEqual(result[0]["assay"], "v2-synthetic")


if __name__ == "__main__":
    unittest.main()
