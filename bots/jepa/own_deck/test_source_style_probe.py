import unittest
import source_style_probe as P


class StyleProbePureTests(unittest.TestCase):
    def test_unsupported_truth_is_null_and_full_confusion_retained(self):
        r=P.classification(["a","a","b"],["a","c","b"],["F1","F1","F2"],["a","b","c"])
        self.assertEqual(r["confusion_counts"],[[1,0,1],[0,1,0],[0,0,0]])
        self.assertIsNone(r["per_class"]["c"]["recall"])
        self.assertIsNone(r["per_class"]["c"]["f1"])
        self.assertEqual(r["supported_class_macro_recall"],.75)
        self.assertEqual(r["family_macro_accuracy"],.75)

    def test_fixed_index_ties_exposed_with_fractional_agreement(self):
        r=P.neighborhood([.8,.8,.4],[10,2,8],["a","b","a"],["x","y","z"],["a","b"],"a",1)
        self.assertEqual(r["prediction"],"b")
        self.assertEqual(r["cutoff_tie_ids"],["y","x"])
        self.assertEqual(r["fractional_boundary_tie_agreement"],.5)

    def test_top3_vote_tie_is_fixed_class_order(self):
        r=P.neighborhood([.9,.8,.7],[0,1,2],["b","c","a"],["x","y","z"],["a","b","c"],"a",3)
        self.assertEqual(r["prediction"],"a")
        self.assertEqual(r["vote_ties"],["a","b","c"])
        self.assertEqual(r["agreement"],1/3)

    def test_nonfinite_scores_stay_unavailable(self):
        r=P.neighborhood([float("nan"),.3],[0,1],["a","b"],["x","y"],["a","b"],"a",3)
        self.assertIsNone(r["prediction"])
        self.assertIsNone(r["agreement"])


if __name__=="__main__": unittest.main()
