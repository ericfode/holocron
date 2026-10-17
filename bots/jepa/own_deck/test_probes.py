"""Correctness of the bounded probe design, not a playing-strength test."""
import unittest

import numpy as np

import probe_representation as P


class RepresentationProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts,cls.train,cls.test=P.make_dataset()
        cls.report=P.run()

    def test_group_holdout_is_unique_bounded_and_deterministic(self):
        other,train,test=P.make_dataset()
        np.testing.assert_array_equal(other,self.counts)
        np.testing.assert_array_equal(train,self.train)
        np.testing.assert_array_equal(test,self.test)
        self.assertEqual((len(other),len(train),len(test)),(128,96,32))
        fingerprints=[P.fingerprint(c) for c in self.counts]
        self.assertEqual(len(set(fingerprints)),128)
        self.assertFalse(set(fingerprints[i] for i in train)&set(fingerprints[i] for i in test))

    def test_wrong_decks_are_partition_local_matched_permutation(self):
        wrong=P.wrong_deck_permutation(self.counts,self.train,self.test)
        y=P.targets(self.counts)
        for partition in (self.train,self.test):
            self.assertEqual(set(wrong[partition]),set(partition))
        self.assertTrue(np.all(y[:,0]!=y[wrong,0]))
        self.assertTrue(np.all(y[:,1]!=y[wrong,1]))
        self.assertTrue(np.all(~np.isclose(y[:,3],y[wrong,3])))
        np.testing.assert_array_equal(wrong,P.wrong_deck_permutation(self.counts,self.train,self.test))

    def test_raw_features_expose_declared_targets_with_neutral_prior_control(self):
        # Threshold applies only to the deliberately explicit raw input contract.
        # Untrained latents have no success threshold or strength requirement.
        for name in P.TARGETS:
            prior=self.report["priorBaseline"][name]["mae"]
            original=self.report["arms"]["raw_original"]["maeR2"][name]["mae"]
            neutral=self.report["arms"]["raw_neutral"]["maeR2"][name]["mae"]
            self.assertLess(original,prior/100)
            self.assertAlmostEqual(neutral,prior,places=10)
        self.assertEqual(self.report["ridge"]["actorUpdates"],0)
        self.assertEqual(self.report["ridge"]["encoderUpdates"],0)
        self.assertEqual(self.report["immutableBefore"],self.report["immutableAfter"])
        for name,arm in self.report["arms"].items():
            for metric in (arm["maeR2"],arm["permutedTrainingLabels"]):
                for row in metric.values():
                    self.assertTrue(np.isfinite(row["mae"]))
                    self.assertTrue(row["r2"] is None or np.isfinite(row["r2"]))
        for diagnostic in self.report["frozenLatentVarianceDiagnostics"].values():
            self.assertTrue(np.isfinite(diagnostic["varianceEntropyEffectiveRank"]))
            self.assertTrue(all(np.isfinite(v) for v in diagnostic["perDimensionStd"].values()))
            self.assertTrue(all(np.isfinite(v) for v in diagnostic["pairwiseEuclidean"].values()))

    def test_probability_label_is_initial_declaration_only(self):
        y=P.targets(self.counts)
        np.testing.assert_allclose(y[:,4],self.counts[:,0]/self.counts.sum(1),atol=0,rtol=0)
        context=P.contexts(self.counts)
        self.assertTrue(np.all(context[:,0,3]==1))
        self.assertTrue(np.all(context[:,1,3]==0))
        self.assertTrue(np.all(context[:,1,4:]==0))
        self.assertTrue(any("No live remaining-deck probability" in s for s in self.report["limitations"]))


if __name__=="__main__": unittest.main()
