"""No actual model/weight loading or neural forward in these tests."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import independent_retrieval_embeddings as E


class FakeArithmeticPipeline:
    """Only zeros/copies; validates observing hooks without a neural model."""
    def __init__(self, module, duplicate=False):
        self.w = {"lnf.g": object(), "lnf.b": object()}
        self.module, self.duplicate = module, duplicate

    def _initial_context(self, state, ids, features, mask, own_deck):
        n = len(state)
        x = np.zeros((n, 27, 64), np.float32)
        x[:, -2:, :50] = own_deck[..., :50]
        return x, np.ones((n, 27), np.float32)

    def forward(self, state, ids, features, mask, own_deck):
        x, _ = self._initial_context(state, ids, features, mask, own_deck)
        self.module._ln(x, self.w["lnf.g"], self.w["lnf.b"])
        return np.zeros((len(state), 96), np.float32)

    def encode(self, *args, **kwargs):
        output = self.forward(*args, **kwargs)
        if self.duplicate:
            self.forward(*args, **kwargs)
        return output


class CaptureContractTests(unittest.TestCase):
    def test_capture_observes_one_forward_and_restores_functions(self):
        module = SimpleNamespace(_ln=lambda x, gain, bias: x)
        original_ln = module._ln
        fake = FakeArithmeticPipeline(module)
        features = np.ones((3, 2, 207), np.float32)
        counts = dict(neural_forward_attempts=0, initial_context_calls=0, final_context_capture_calls=0)
        output = E.capture_once(np, fake, module, features, counts)
        self.assertEqual(counts, dict(neural_forward_attempts=1, initial_context_calls=1, final_context_capture_calls=1))
        self.assertIs(module._ln, original_ln)
        np.testing.assert_array_equal(output["initial_deck_tokens64"], output["final_deck_tokens64"])
        self.assertEqual(output["full_z96"].shape, (3, 96))

    def test_second_fake_call_is_stopped_and_hooks_restored(self):
        module = SimpleNamespace(_ln=lambda x, gain, bias: x)
        original_ln = module._ln
        fake = FakeArithmeticPipeline(module, duplicate=True)
        counts = dict(neural_forward_attempts=0, initial_context_calls=0, final_context_capture_calls=0)
        with self.assertRaises(RuntimeError):
            E.capture_once(np, fake, module, np.zeros((3, 2, 207), np.float32), counts)
        self.assertEqual(counts["neural_forward_attempts"], 1)
        self.assertIs(module._ln, original_ln)

    def test_row_hash_tracks_declaration_but_not_batch_size(self):
        first = np.zeros((2, 207), np.float32)
        second = first.copy(); second[0, 4] = 1
        self.assertEqual(E.input_row_hash(np, first), E.input_row_hash(np, first.copy()))
        self.assertNotEqual(E.input_row_hash(np, first), E.input_row_hash(np, second))

    def test_unit_normalization_zero_and_two_role_shape(self):
        values = np.ones((3, 2, 64), np.float32)
        values[0, 1] = 0
        normalized = E.unit(np, values)
        np.testing.assert_allclose(np.linalg.norm(normalized[1:], axis=-1), 1)
        self.assertFalse(normalized[0, 1].any())
        self.assertEqual(normalized.shape, (3, 2, 64))

    def test_ordered_bank_adds_training_rows_without_control_identity_filter(self):
        original = np.zeros((27, 2, 207), np.float32)
        original[:, 0, 4] = np.arange(27)
        controls = dict(train=list(range(22)), original_features=original, original_source_indices=list(range(27)),
                        features=original[[10, 14, 25]], ids=np.asarray(["anchor10", "anchor14", "anchor25"]),
                        source_indices=np.asarray([10, 14, 25], np.int64), anchor_indices=[0, 1, 2])
        bank = E.ordered_forward_bank(np, controls)
        self.assertEqual(bank["features"].shape, (25, 2, 207))
        np.testing.assert_array_equal(bank["features"][:22], original[:22])
        np.testing.assert_array_equal(bank["control_indices"], [22, 23, 24])
        self.assertEqual(len(bank["reference_indices"]), 25)

    def test_original_branch_transform_never_uses_controls(self):
        values = np.random.default_rng(17).normal(size=(28, 64))
        train = np.arange(22)
        first = E.train_branch_transform(np, values, train)
        values[22:] = 1e10
        second = E.train_branch_transform(np, values, train)
        for key in first:
            np.testing.assert_array_equal(first[key], second[key])
        np.testing.assert_allclose(first["train_mean"], values[:22].mean(0))
        regularized = .9 * first["training_covariance"] + .1 * np.trace(first["training_covariance"]) / 64 * np.eye(64)
        np.testing.assert_allclose(first["whitening"] @ regularized @ first["whitening"], np.eye(64), atol=1e-12)

    def test_control_preparation_allowance_cannot_reset(self):
        self.assertEqual(E.preparation_elapsed(dict(status="prepared", elapsed_seconds=2.5)), 2.5)
        self.assertEqual(E.preparation_elapsed(dict(status="prepared", elapsed_seconds=1, aggregate_preparation_attempt_seconds=3.5)), 3.5)
        for receipt in (dict(status="failed", elapsed_seconds=1), dict(status="prepared", elapsed_seconds=20),
                        dict(status="prepared", elapsed_seconds=True), dict(status="prepared", elapsed_seconds=float("nan"))):
            with self.assertRaises(ValueError):
                E.preparation_elapsed(receipt)


if __name__ == "__main__":
    unittest.main()
