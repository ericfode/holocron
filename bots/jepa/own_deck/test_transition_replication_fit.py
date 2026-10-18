"""Data/accounting contracts only: no Torch imports or neural/native execution."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transition_replication_fit as R

ROOT = R.HERE.parents[3] / "experiments/grounded-contrast"


class ReplicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = R.load_data(ROOT / "grounded-contrast.npz", ROOT / "grounded-contrast.manifest.json", ROOT / "fit-1/contract.json", 29)

    def test_actual_original_data_and_no_neural_import(self):
        self.assertEqual(len(self.data["arrays"]["train_idx"]), 100)
        self.assertEqual(len(self.data["arrays"]["joint_holdout_idx"]), 8)
        R.validate_cohort(self.data, "original", 29)
        # Other pure suites may already import the old data module legitimately.
        # Verify this runner's imports in its own fresh process instead.
        code = """import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import transition_replication_fit as R
root=Path(sys.argv[2])
R.load_data(root/'grounded-contrast.npz',root/'grounded-contrast.manifest.json',root/'fit-1/contract.json',29)
print(json.dumps({'torch_imported':'torch' in sys.modules,'old_data_imported':'grounded_contrast_data' in sys.modules}))
"""
        completed = subprocess.run([sys.executable, "-c", code, str(R.HERE), str(ROOT)], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(completed.stdout), dict(torch_imported=False, old_data_imported=False))
        with self.assertRaises(ValueError):
            R.validate_cohort(self.data, "original", 17)
        with self.assertRaises(ValueError):
            R.validate_cohort(self.data, "fresh", 29)

    def test_axes_are_manifest_membership_not_numeric_threshold(self):
        manifest = copy.deepcopy({"numeric_contract": {"split": self.data["manifest"]["numeric_contract"]["split"]}, "programs": self.data["manifest"]["programs"]})
        manifest["numeric_contract"]["split"]["train_state_families"] = list(range(30, 40))
        manifest["numeric_contract"]["split"]["heldout_state_families"] = [4, 8, 10, 99]
        split = R.validate_axes(manifest)
        self.assertEqual(split["heldout_state_families"], [4, 8, 10, 99])
        split["heldout_state_families"][0] = 30
        with self.assertRaises(ValueError):
            R.validate_axes(manifest)

    def test_same_seed_schedules_and_fresh_wrong_draws(self):
        schedule, wrong = R.schedules(self.data, 29)
        schedule2, wrong2 = R.schedules(self.data, 29)
        np.testing.assert_array_equal(schedule, schedule2)
        np.testing.assert_array_equal(wrong, wrong2)
        self.assertEqual(schedule.shape, (600, 16))
        self.assertTrue(np.isin(schedule, self.data["arrays"]["train_idx"]).all())
        self.assertTrue(np.isin(wrong, self.data["train_programs"]).all())
        groups = np.asarray(self.data["group_ids"])
        self.assertTrue(np.all(groups[wrong] != groups[self.data["query"][schedule]]))
        self.assertGreater(len(set(wrong[self.data["query"][schedule] == self.data["train_programs"][0]].tolist())), 1)
        self.assertNotEqual(R.array_digest(schedule), R.array_digest(R.schedules(self.data, 43)[0]))

    def test_held_bank_and_identity_zero_without_changing_full_bank(self):
        M = R.model_definitions()
        bank = self.data["bank"]
        restricted = M.training_program_bank(bank, self.data["train_programs"])
        self.assertTrue(all(not value[self.data["held_programs"]].any() for value in restricted.values()))
        self.assertTrue(bank["token_mask"][self.data["held_programs"]].any())
        self.assertFalse(bank["identity_indices"][self.data["held_programs"]].any())

    def test_fixed_vocabulary_rejects_unseen_categorical_symbol(self):
        M = R.model_definitions()
        record = copy.deepcopy(self.data["records"][0])
        record["raw_ability"]["effect"]["kind"] = "unreviewed-effect"
        with self.assertRaisesRegex(ValueError, "unreviewed value"):
            M.encode_program_bank([record], self.data["symbols"], [record["code"]])

    def test_scaling_excludes_all_heldout_labels_and_contexts(self):
        M = R.model_definitions()
        a = self.data["arrays"]
        x, c = a["context_features"].copy(), a["candidate_features"].copy()
        held = np.concatenate([a[k] for cell, k in M.CELL_ARRAYS.items() if cell != "train"])
        x[held, 0] = 1e6
        c[held, :, 9] = 1e6
        self.assertEqual(M.fit_input_scaling(x, c, a["train_idx"], a["primary_candidate_mask"]), self.data["input_scaling"])
        targets = a["targets"].copy()
        targets[held, :, 3] = 1e6
        scale = M.fit_head_scaling(a["source_use"], a["source_use_mask"], a["candidate_allowed"], a["candidate_allowed_mask"], targets, a["target_mask"], a["train_idx"], a["primary_candidate_mask"])
        self.assertEqual(scale, self.data["head_scaling"])

    def test_native_contrasts_filter_legal_settled_and_known(self):
        data = dict(self.data)
        a = {k: v.copy() for k, v in self.data["arrays"].items()}
        data["arrays"] = a
        source = a["source_use"].copy()
        branch = a["targets"].copy()
        branch[:, :, 1] = a["candidate_allowed"]
        before = R.paired_native_errors(source, branch, data)
        for cell in before.values():
            self.assertTrue(all(pair["absolute_contrast_error"] == 0 for pair in cell["pairs"]))
        data["settled_commits"] = np.zeros_like(self.data["settled_commits"])
        after = R.paired_native_errors(source, branch, data)
        self.assertTrue(any(pair["kind"] == "settled-both-legal-transition" for cell in before.values() for pair in cell["pairs"]))
        self.assertFalse(any(pair["kind"] == "settled-both-legal-transition" for cell in after.values() for pair in cell["pairs"]))
        self.assertTrue(any(pair["kind"] == "native-target-membership" for cell in after.values() for pair in cell["pairs"]))

    def test_primary_keeps_native_invariants_and_fixed_three_heads(self):
        pairs = []
        for head, delta, error in [("cost_resource", 1., 2.), ("xp_delta", 1., 4.), ("target_exhausted_delta", 0., 6.)]:
            pairs.append(dict(head=head, left_code="TWI_206", right_code="SHD_004", left_root=1, right_root=2, state_family=12,
                              candidate=2, native_delta=delta, predicted_delta=delta + error, absolute_contrast_error=error,
                              train_scaled_error=error, native_varies=delta != 0))
        primary = R.fresh_primary({"joint-held": {"pairs": pairs}})
        self.assertEqual(primary["macro_train_scaled_mae"], 4.)
        self.assertEqual(primary["heads"]["target_exhausted_delta"]["pairs"], 1)
        self.assertEqual(primary["heads"]["cost_resource"]["detail"][0]["native_delta"], -1.)
        partial = R.fresh_primary({"joint-held": {"pairs": pairs[:2]}})
        self.assertIsNone(partial["macro_train_scaled_mae"])

    def test_global_progress_is_durable_exact_and_preserves_seed_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.jsonl"
            args = argparse.Namespace(seed=29, cohort="original", run_id="original29")
            self.assertEqual(R.progress_baseline(path), 0)
            R.progress(path, 1, 1, "correct-ir", 1, args)
            R.progress(path, 2, 2, "correct-ir", 2, args)
            self.assertEqual(R.progress_baseline(path), 2)
            row = json.loads(path.read_text().splitlines()[0])
            self.assertEqual((row["seed"], row["cohort"], row["seed_updates_completed"]), (29, "original", 1))
            R.progress(path, 4, 4, "correct-ir", 4, args)
            with self.assertRaises(ValueError):
                R.progress_baseline(path)

    def test_exact_two_fit_three_evaluate_allocation_and_no_extra_forwards(self):
        self.assertEqual(list(R.UPDATE_OFFSETS.values()), [0, 2400])
        self.assertEqual(len(R.UPDATE_OFFSETS) * R.EXPECTED_COUNTS["optimizer_updates"], 4800)
        self.assertEqual(2 * R.EXPECTED_COUNTS["heldout_validation_batches"] + 3 * R.EVALUATION_COUNTS["heldout_validation_batches"], 28)
        self.assertEqual(R.EVALUATION_COUNTS["optimizer_updates"], 0)
        self.assertEqual(R.EVALUATION_COUNTS["training_forward_batches"], 0)
        self.assertEqual(R.EXPECTED_COUNTS["usage_batches"], 0)
        self.assertEqual(R.EXPECTED_COUNTS["abi_embedding_batches"], 0)

    def test_training_equivalence_includes_labels_self_inputs_scaling_and_bank(self):
        proof = R.training_equivalence(self.data, self.data)
        self.assertEqual(proof["roots"], 100)
        fresh = dict(self.data)
        fresh["arrays"] = {name: value.copy() for name, value in self.data["arrays"].items()}
        held = int(fresh["arrays"]["joint_holdout_idx"][0])
        fresh["arrays"]["targets"][held, 0, 3] = 999
        self.assertEqual(R.training_equivalence(self.data, fresh), proof)
        train = int(fresh["arrays"]["train_idx"][0])
        fresh["arrays"]["candidate_features"][train, 7, 9] += 1
        with self.assertRaisesRegex(ValueError, "training tensor differs"):
            R.training_equivalence(self.data, fresh)
        fresh = dict(self.data, head_scaling=copy.deepcopy(self.data["head_scaling"]))
        fresh["head_scaling"]["scale"][3] += 1
        with self.assertRaisesRegex(ValueError, "scalers"):
            R.training_equivalence(self.data, fresh)
        fresh = dict(self.data, bank={name: value.copy() for name, value in self.data["bank"].items()})
        index = int(self.data["train_programs"][0])
        fresh["bank"]["numeric"][index, 0, 0] += 1
        with self.assertRaisesRegex(ValueError, "semantic/identity bank"):
            R.training_equivalence(self.data, fresh)

    def test_historical_named_checkpoint_provenance_without_model(self):
        before = set(sys.modules)
        references = R.saved_checkpoints(ROOT / "fit-1/result.json", 17)
        self.assertEqual(list(references), list(R.ARMS))
        self.assertTrue(all(sum(value.size for value in row["arrays"].values()) == 9020 for row in references.values()))
        self.assertFalse(any(name == "torch" or name.startswith("torch.") for name in set(sys.modules) - before))

    def test_preflight_and_guard_baseline_agree_without_neural_execution(self):
        before = set(sys.modules)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            args = argparse.Namespace(dataset=(ROOT / "grounded-contrast.npz").resolve(), manifest=(ROOT / "grounded-contrast.manifest.json").resolve(),
                vocabulary_contract=(ROOT / "fit-1/contract.json").resolve(), plan=base / "plan.json", out=base / "fit29", progress=base / "progress.jsonl",
                ledger=base / "ledger.jsonl", events=base / "events.jsonl", seed=29, cohort="original", update_offset=0,
                run_id="test-original29", campaign_id="test-campaign", reference_dataset=None, reference_manifest=None, reference_result=None)
            plan = R.make_preflight(args)
            self.assertEqual(plan["config"]["cumulative_campaign_updates"], 4800)
            self.assertEqual(plan["config"]["self_query_auxiliary_weight"], .1)
            metadata = dict(max_updates=4800, max_active_seconds=240, max_sampled_bytes=2147483648, max_engine_apply_attempts=2048,
                            campaign_ledger=str(args.ledger), initial_progress_updates=0, commands=[["fit", plan["worker_command"]]])
            stage = dict(event="stage-start", stage="fit", reserved_updates=2400, prior=dict(updates=0), metadata=metadata)
            args.ledger.write_text(json.dumps(stage) + "\n")
            self.assertEqual(R.verify_plan(args), plan)
            stage["prior"]["updates"] = 1
            args.ledger.write_text(json.dumps(stage) + "\n")
            with self.assertRaisesRegex(ValueError, "baseline"):
                R.verify_plan(args)
            stage["prior"]["updates"] = 0
            args.ledger.write_text(json.dumps(stage) + "\n")
            plan["sources"][0]["sha256"] = "0" * 64
            R.write(args.plan, plan)
            with self.assertRaisesRegex(ValueError, "frozen source/input"):
                R.verify_plan(args)
            self.assertFalse(any(name == "torch" or name.startswith("torch.") for name in set(sys.modules) - before))


if __name__ == "__main__":
    unittest.main()
