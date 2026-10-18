"""Pure contract tests. Neural smoke forwards have their own bounded receipt."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grounded_contrast_model as M


def program(amount=1):
    return {"title": "display only", "trigger": "action", "costs": [{"kind": "resources", "amount": {"kind": "const", "value": 1}}],
            "targetResolver": {"kind": "query", "owner": "opponent", "type": "unit"},
            "effect": {"kind": "sequence", "effects": [{"kind": "damage", "amount": {"kind": "const", "value": amount}, "target": "chosen"}, {"kind": "ready", "target": "chosen"}]}}


class StructuralContractTests(unittest.TestCase):
    def test_object_keys_and_identity_invariant(self):
        p = program()
        shuffled = {key: value for key, value in reversed(list(p.items()))}
        shuffled["title"] = "different title and ID"
        self.assertEqual(M.structural_tokens(p), M.structural_tokens(shuffled))
        symbols = M.freeze_symbols([p])
        _, bank = M.encode_program_bank([dict(code="AAA_001", raw_ability=p), dict(code="ZZZ_999", raw_ability=shuffled)], symbols, ["AAA_001"])
        for key in bank:
            if key != "identity_indices":
                np.testing.assert_array_equal(bank[key][0], bank[key][1])
        np.testing.assert_array_equal(bank["identity_indices"][:2], [1, 0])

    def test_sequence_operand_quantity_preserved(self):
        p, reverse, changed = program(), program(), program(2)
        reverse["effect"]["effects"].reverse()
        self.assertNotEqual(M.structural_tokens(p), M.structural_tokens(reverse))
        self.assertNotEqual(M.structural_tokens(p), M.structural_tokens(changed))
        operand = program()
        operand["targetResolver"]["owner"] = "self"
        self.assertNotEqual(M.structural_tokens(p), M.structural_tokens(operand))

    def test_caps_nonfinite_and_identity_fields_reject(self):
        for altered in (dict(program(), sourcePath="private"), dict(program(), effect={"kind": "damage", "amount": float("nan")}), dict(program(), effect={"kind": "damage", "amount": 10 ** 400}), dict(program(), effect={"kind": "ref", "path": ["x"] * 300})):
            with self.assertRaises(ValueError):
                M.structural_tokens(altered)
        with self.assertRaises(ValueError):
            M.encode_program_bank([dict(code="A", raw_ability=program())] * 17, M.freeze_symbols([program()]), [])

    def test_wrong_control_has_no_fixed_inverse_or_heldout_content(self):
        correct = np.zeros(100, np.int64)
        draws = M.draw_wrong_programs(correct, [0, 1, 2, 3], ["a", "a", "b", "c"], np.random.default_rng(19))
        self.assertEqual(set(draws), {2, 3})
        np.testing.assert_array_equal(draws, M.draw_wrong_programs(correct, [0, 1, 2, 3], ["a", "a", "b", "c"], np.random.default_rng(19)))
        with self.assertRaises(ValueError):
            M.draw_wrong_programs([0], [0, 1], ["a", "a"], np.random.default_rng(1))

    def test_training_bank_heldout_zero(self):
        _, bank = M.encode_program_bank([dict(code="A", raw_ability=program()), dict(code="B", raw_ability=program(2))], M.freeze_symbols([program(), program(2)]), ["A"])
        restricted = M.training_program_bank(bank, [0])
        self.assertTrue(all(not np.any(value[1:]) for value in restricted.values()))
        self.assertTrue(bank["slot_mask"][1])

    def test_input_scaling_train_only_known_and_flags(self):
        x = np.array([[0, 0], [2, 1], [999, 0]], np.float32)
        c = np.zeros((3, 8, 26), np.float32)
        c[..., 9] = 30
        c[..., 16] = 1
        c[2, :, 9] = 1000
        c[:, 7, 9] = 9000
        primary = np.tile([1] * 7 + [0], (3, 1))
        scaling = M.fit_input_scaling(x, c, [0, 1], primary)
        self.assertEqual(scaling["context_center"], [1., 0.])
        self.assertEqual(scaling["candidate_center"][9], 30.)
        sx, sc = M.apply_input_scaling(x, c, scaling)
        np.testing.assert_array_equal(sx[:, 1], x[:, 1])
        np.testing.assert_array_equal(sc[..., 16], c[..., 16])
        c[..., 16] = 0
        _, unknown = M.apply_input_scaling(x, c, scaling)
        self.assertFalse(unknown[..., 9].any())

    def test_head_scales_primary_self_exclusion_capped_weights(self):
        n = 20
        source = np.zeros(n, np.float32); source[-1] = 1
        allowed = np.zeros((n, 8), np.float32); allowed[:, 7] = 100
        target = np.zeros((n, 8, 11), np.float32)
        target[..., 3] = 2; target[-1, :7, 3] = 4
        mask = np.ones_like(target); mask[..., :2] = 0
        primary = np.tile([1] * 7 + [0], (n, 1))
        scale = M.fit_head_scaling(source, np.ones(n), allowed, np.ones_like(allowed), target, mask, np.arange(n), primary)
        self.assertIn(0, scale["primary"])
        self.assertIn(3, scale["primary"])
        self.assertIn(1, scale["auxiliary"])
        self.assertEqual(scale["class_weights"][0][1], 5.)
        self.assertEqual(scale["variation"][1], [0.])
        self.assertEqual(scale["center"][3], 2.1)

    def test_golden_statuses_have_no_smuggled_program(self):
        _, bank = M.encode_program_bank([dict(code="A", raw_ability=program())], M.freeze_symbols([program()]), ["A"])
        golden = M.golden_bank(bank)
        np.testing.assert_array_equal(golden["status"][[0, 12, 13, 14, 15]], np.eye(5))
        self.assertFalse(golden["token_mask"][12:].any())
        self.assertFalse(golden["identity_indices"][12:].any())

    def test_progress_exact_budget_key_and_fixed_allocation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.jsonl"
            M._progress(path, 7, "correct-ir", 7)
            event = json.loads(path.read_text())
            self.assertEqual(event["updates_completed"], 7)
            self.assertNotIn("completed_updates", event)
        self.assertEqual(M.FIT_CONFIG["max_updates"], 4 * 600)
        self.assertEqual(M.FIT_CONFIG["final_validation_batches"], 8)
        self.assertEqual(M.FIT_CONFIG["source_self_policy"], "slot7 auxiliary0.1; primary candidate slots0..6; no candidate pooling")


if __name__ == "__main__":
    unittest.main()
