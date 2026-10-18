"""Source-only replication contract tests; no model/native/optimizer calls."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grounded_contrast_data as G
import transition_replication_plan as R


class TransitionReplicationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generated = G.PINNED_KESSEL / "compiler/generated"
        cls.catalog = json.loads((generated / "cards.json").read_text())
        cls.runtime = json.loads((generated / "runtime-admission.json").read_text())
        cls.original_manifest = json.loads((R.ORIGINAL / "grounded-contrast.manifest.json").read_text())
        cls.original_contract = json.loads((R.ORIGINAL / "fit-1/contract.json").read_text())
        with np.load(R.ORIGINAL / "grounded-contrast.npz", allow_pickle=False) as data:
            cls.original_arrays = {k: v.copy() for k, v in data.items()}

    def plan(self, catalog=None, manifest=None):
        return R.make_plan(catalog or self.catalog, self.runtime, manifest or self.original_manifest, self.original_contract)

    def test_whole_fresh_programs_and_original_training_identity(self):
        p = self.plan()
        self.assertEqual(p["heldout_codes"], ["SHD_004", "TWI_206"])
        self.assertEqual(p["train_codes"], list(G.TRAIN_CODES))
        self.assertEqual(len(p["programs"]), 12)
        self.assertEqual(p["prior_unexecuted_action_inventory"], 29)
        self.assertEqual(p["fresh_id_program_alias_overlap_with_prior"], 0)
        for record in p["programs"]:
            if record["code"] in G.TRAIN_CODES:
                self.assertEqual(record, self.original_manifest["programs"][record["code"]])
            else:
                raw = next(c for c in self.catalog["cards"] if c["setCode"] == record["code"])
                self.assertEqual(record["raw_ability"], raw["abilities"][record["side"]][0])
                self.assertEqual(record["source_hash"], raw["sourceHash"])
                self.assertEqual(record["all_side_ability_counts"][record["side"]], 1)

    def test_fixed_vocabulary_and_numeric_literal_disclosure(self):
        p = self.plan()
        self.assertEqual(p["architecture"]["parameters"], 9020)
        self.assertEqual(p["architecture"]["vocabularies"], dict(path=26, type=8, value=43))
        self.assertEqual(p["vocabulary_coverage"]["SHD_004"]["tokens"], 50)
        self.assertEqual(p["vocabulary_coverage"]["TWI_206"]["tokens"], 47)
        self.assertTrue(all(not any(v["missing"].values()) for v in p["vocabulary_coverage"].values()))
        self.assertTrue(any("threshold4 from threshold3" in s for s in p["limitations"]))
        records = copy.deepcopy(p["programs"])
        records[-1]["raw_ability"]["unreviewedNewField"] = True
        with self.assertRaisesRegex(ValueError, "fixed architecture vocabulary"):
            R.vocabulary_coverage(records, self.original_contract)

    def test_state_recipe_only_one_change_and_four_held_effect_contexts(self):
        p = self.plan()
        self.assertEqual([c["id"] for c in p["contexts"]], list(range(14)))
        old = self.original_manifest["numeric_contract"]["state_families"]
        new = p["numeric_contract"]["state_families"]
        for i, (a, b) in enumerate(zip(old, new)):
            if i == 12:
                self.assertEqual(a["overrides"]["ready_resources"], 0)
                self.assertEqual(b["overrides"]["ready_resources"], 2)
                self.assertEqual({k: v for k, v in a["overrides"].items() if k != "ready_resources"},
                                 {k: v for k, v in b["overrides"].items() if k != "ready_resources"})
            else:
                self.assertEqual(a, b)
        self.assertTrue(all(c["ready_resources"] >= 2 and not c["source_exhausted"] for c in p["contexts"][10:]))
        self.assertTrue(p["contexts"][6]["source_exhausted"])
        self.assertEqual(p["contexts"][7]["ready_resources"], 0)

    def test_private_contract_does_not_mutate_original(self):
        codes, states, held = copy.deepcopy(G.CORE_CODES), copy.deepcopy(G.STATE_FAMILIES), copy.deepcopy(G.HELDOUT_CODES)
        module = R.configured_contract()
        self.plan()
        self.assertIsNot(module, G)
        self.assertEqual((G.CORE_CODES, G.STATE_FAMILIES, G.HELDOUT_CODES), (codes, states, held))
        self.assertEqual(G.STATE_FAMILIES[12]["overrides"]["ready_resources"], 0)

    def test_training_program_mutation_and_fresh_identity_alias_collision_rejected(self):
        for kind in ("training", "identity", "alias", "previously_executed"):
            catalog, manifest = copy.deepcopy(self.catalog), copy.deepcopy(self.original_manifest)
            row = next(c for c in catalog["cards"] if c["setCode"] == ("SOR_011" if kind == "training" else "SHD_004"))
            if kind == "training":
                row["abilities"]["leader"][0]["effect"]["effects"][0]["amount"]["value"] += 1
            elif kind == "identity":
                row["card"]["id"] = next(c for c in catalog["cards"] if c["setCode"] == "ASH_011")["card"]["id"]
            elif kind == "alias":
                row["card"]["setCodes"] += [{"set": "ASH", "number": 11}]
            else:
                manifest["programs"]["SHD_004"] = copy.deepcopy(manifest["programs"]["ASH_011"])
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.plan(catalog=catalog, manifest=manifest)

    def test_run_matrix_caps_and_primary_same_candidate_metric(self):
        p = self.plan()
        runs = p["replication_design"]["run_matrix"]
        self.assertEqual([(r["dataset"], r["seed"]) for r in runs], [("original", 29), ("original", 43), ("fresh", 17), ("fresh", 29), ("fresh", 43)])
        self.assertEqual(sum(r["updates"] for r in runs), 4800)
        self.assertTrue(all(r["updates_per_arm"] == (600 if r["action"] == "fit" else 0) and len(r["arms"]) == 4 for r in runs))
        self.assertEqual([r["action"] for r in runs], ["fit", "fit", "evaluate-only", "evaluate-only", "evaluate-only"])
        self.assertEqual(p["replication_design"]["fresh_evaluation_forwards"], 12)
        self.assertEqual(p["primary_paired_metric"]["heads"], ["cost_resource", "xp_delta", "target_exhausted_delta"])
        self.assertIn("both independent commits settle", p["primary_paired_metric"]["eligibility"])
        self.assertEqual(p["primary_paired_metric"]["orientation"], "SHD_004 minus TWI_206")
        self.assertEqual((p["native_applies"], p["optimizer_updates"], p["model_forwards"]), (0, 0, 0))
        self.assertTrue(p["proposed_campaign_limits"]["requires_root_go"])

    def test_original_native_schema_is_not_accepted_as_new_evidence(self):
        with self.assertRaisesRegex(ValueError, "new replication receipt schema"):
            R.convert_receipt(dict(schema="jepa-grounded-native-transitions/1"), {}, {}, {}, "0" * 64)

    def fresh_training_fixture(self):
        """Only the training-equality gate is exercised; not a native dataset."""
        arrays = {k: v.copy() for k, v in self.original_arrays.items()}
        manifest = copy.deepcopy(self.original_manifest)
        manifest["programs"] = {p["code"]: p for p in self.plan()["programs"]}
        return arrays, manifest

    def proof(self, arrays, manifest=None, contract=None):
        return R.training_equivalence(self.original_arrays, arrays, self.original_manifest,
                                      manifest or self.original_manifest, contract or self.original_contract)

    def test_exact_training_equivalence_aligns_rows_and_program_bank_by_code(self):
        arrays, manifest = self.fresh_training_fixture()
        first = self.proof(arrays, manifest)
        self.assertEqual(first["training_roots"], 100)
        self.assertTrue(first["all8candidate_inputs_labels_masks"])
        self.assertEqual(set(first["tensor_sha256"]), set(R.TRAIN_TENSORS))
        self.assertEqual((first["native_applies"], first["model_forwards"], first["optimizer_updates"]), (0, 0, 0))
        # Full-dataset positions and held-program slots differ without changing training content.
        for name, value in list(arrays.items()):
            if value.ndim and value.shape[0] == 168:
                arrays[name] = value[::-1].copy()
            elif name.endswith("_idx"):
                arrays[name] = (167 - value).astype(np.int64)
        second = self.proof(arrays, manifest)
        self.assertEqual(first["canonical_training_sha256"], second["canonical_training_sha256"])
        self.assertNotEqual(first["fresh_row_indices"], second["fresh_row_indices"])

    def test_equivalence_checks_all8_candidates_unknown_payloads_and_masks(self):
        for name in R.TRAIN_TENSORS:
            arrays, manifest = self.fresh_training_fixture()
            row = int(arrays["train_idx"][0])
            value = arrays[name]
            coordinate = (row,) + tuple(7 if i == 1 and value.shape[i] == 8 else 0 for i in range(1, value.ndim))
            value[coordinate] += 1
            with self.subTest(tensor=name), self.assertRaisesRegex(ValueError, "bit-exact training tensor"):
                self.proof(arrays, manifest)

    def test_equivalence_rejects_program_dtype_root_and_saved_scaling_changes(self):
        for kind in ("program", "dtype", "root", "scaling"):
            arrays, manifest = self.fresh_training_fixture()
            contract = copy.deepcopy(self.original_contract)
            if kind == "program": manifest["programs"][R.TRAIN_CODES[0]]["raw_ability"]["extraField"] = True
            elif kind == "dtype": arrays["targets"] = arrays["targets"].astype(np.float64)
            elif kind == "root": arrays["train_idx"][0] = arrays["train_idx"][1]
            else: contract["head_scaling"]["scale"][2] += 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.proof(arrays, manifest, contract)

    def test_fresh_held_only_content_does_not_change_training_proof(self):
        arrays, manifest = self.fresh_training_fixture()
        before = self.proof(arrays, manifest)
        held = int(arrays["joint_holdout_idx"][0])
        arrays["candidate_features"][held, 0, 8] += 1
        arrays["targets"][held, 0, 3] += 1
        after = self.proof(arrays, manifest)
        self.assertEqual(before["canonical_training_sha256"], after["canonical_training_sha256"])


if __name__ == "__main__":
    unittest.main()
