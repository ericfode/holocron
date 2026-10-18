"""Stdlib preparation contracts only; no numerical or neural imports."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).with_name("composition_gradient_diagnostic.py")
SPEC = importlib.util.spec_from_file_location("composition_gradient_contract", PATH)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class GradientPlanTests(unittest.TestCase):
    def test_frozen_train_only_allocation_and_protected_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = C.prepare(Path(directory)/"plan.json", Path(directory)/"result")
            self.assertEqual(plan["batch_rows"], 22)
            self.assertEqual(len(plan["targets"]), 13)
            self.assertEqual(plan["expected_counts"],dict(production_forwards=1,backwards=1,optimizer_updates=0,native_calls=0,paid_jobs=0,checkpoint_writes=0))
            self.assertEqual(plan["limits"]["sampled_rss_bytes"],1073741824)
            self.assertEqual(plan["source_sha256"],C.sha(PATH))
            self.assertTrue(all(C.sha(row["path"])==row["sha256"] for row in plan["inputs"]))

    def test_frozen_plan_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory)/"plan.json"
            C.prepare(plan,Path(directory)/"result")
            with self.assertRaises(FileExistsError):
                C.prepare(plan,Path(directory)/"result")


if __name__ == "__main__":
    unittest.main()
