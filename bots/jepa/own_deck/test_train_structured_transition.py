"""Forward/contract tests only; these tests perform no optimizer updates."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import train_structured_transition as S

try:
    import torch
except ImportError:
    torch = None


def records():
    return {c["setCode"]: dict(program=S.T.ability(c["abilities"]["leader"][0]),
              raw_ability=copy.deepcopy(c["abilities"]["leader"][0]), ability_path=c["abilityPath"],
              sourceHash=c["sourceHash"], sourcePath=c["sourcePath"])
            for c in S.T.REVIEWED_CARDS if S.T.RUNTIME_ADMISSION[c["setCode"]]["admitted"]}


def permute(value, rng):
    if isinstance(value, dict):
        keys = list(value); rng.shuffle(keys)
        return {k: permute(value[k], rng) for k in keys}
    if isinstance(value, list):
        return [permute(v, rng) for v in value]
    return value


class ContractTests(unittest.TestCase):
    def test_caps_and_progress_protocol(self):
        self.assertEqual(S.Config().validate().steps * len(S.ARMS), 600)
        for bad in (S.Config(seed=18), S.Config(steps=201), S.Config(batch=17)):
            with self.assertRaises(ValueError): bad.validate()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.jsonl"
            S.append_progress(path, 17, "correct-ir", 17)
            self.assertEqual(json.loads(path.read_text())["updates_completed"], 17)

    def test_same_shapes_and_id_only_no_ast_shape(self):
        codes, banks, permutation = S.make_banks(records())
        for name in banks["correct-ir"]:
            self.assertEqual(banks["correct-ir"][name].shape, banks["id-only"][name].shape)
            np.testing.assert_array_equal(banks["wrong-ir"][name], banks["correct-ir"][name][permutation])
        np.testing.assert_array_equal(banks["id-only"]["token_mask"][:len(codes)].sum(1), [1, 1])
        np.testing.assert_array_equal(banks["id-only"]["path_lengths"], 0)

    def test_object_key_order_and_identity_metadata_invariance(self):
        original = records()
        bank = S.make_banks(original)[1]["correct-ir"]
        rng = random.Random(17)
        for _ in range(20):
            changed = permute(original, rng)
            for record in changed.values():
                record["sourcePath"] = "different-provenance"
                record["sourceHash"] = "different-provenance"
                record["raw_ability"]["title"] = "different-name"
            actual = S.make_banks(changed)[1]["correct-ir"]
            for name in bank: np.testing.assert_array_equal(bank[name], actual[name])

    def test_unknown_statuses_are_explicit_not_known_empty(self):
        bank = S.empty_bank()
        for i, status in enumerate(S.STATUSES[1:]): S.fill_program(bank, i, status=status)
        np.testing.assert_array_equal(bank["token_mask"], 0)
        self.assertEqual(len(np.unique(bank["status"][:4], axis=0)), 4)
        with self.assertRaises(ValueError): S.fill_program(bank, 0, [S.T.Token((), "enum", "damage")], status="unsupported")
        with self.assertRaises(ValueError): S.fill_program(bank, 0, [S.T.Token(("unreviewed",), "enum", "damage")])
        with self.assertRaises(ValueError): S.fill_program(bank, 0, [S.T.Token((), "integer", 65536)])

    def test_dataset_binding_split_and_masks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.npz"; manifest = Path(tmp) / "manifest.json"
            np.savez(path, context_features=np.array([[0, 0], [0, 0], [1, 0], [1, 0]], np.float32), targets=np.zeros((4, 7), np.float32),
                     target_mask=np.ones((4, 7), np.float32), train_idx=[0, 1], val_idx=[2, 3],
                     context_groups=["a", "a", "b", "b"], fingerprints=["a0", "a1", "b0", "b1"],
                     source_cards=["ASH_011", "IBH_053", "ASH_011", "IBH_053"])
            meta = dict(artifact=dict(sha256=S.G.sha(path)), target_names=list(S.TARGETS), programs=records(),
                        context_feature_names=["ready_resources", "source_exhausted"], context_feature_units=["count", "boolean"])
            manifest.write_text(json.dumps(meta))
            data = S.load_dataset(path, manifest)
            self.assertEqual(data["counts"].shape, (4, S.PROGRAMS))
            contract = S.contract(data)
            self.assertEqual(contract["context"]["units"], ["count", "boolean"])
            meta["artifact"]["sha256"] = "bad"; manifest.write_text(json.dumps(meta))
            with self.assertRaises(ValueError): S.load_dataset(path, manifest)


@unittest.skipIf(torch is None, "cached Torch unavailable")
class ForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def model(self):
        torch.manual_seed(17)
        return S.make_model(torch, 2)

    def test_parameter_cap_same_initialization_and_finite_statuses(self):
        model = self.model(); other = self.model()
        self.assertLessEqual(sum(p.numel() for p in model.parameters()), 32768)
        for a, b in zip(model.parameters(), other.parameters()): self.assertTrue(torch.equal(a, b))
        bank = S.make_banks(records())[1]["correct-ir"]
        for i, status in zip((2, 3, 4, 5), S.STATUSES[1:]): S.fill_program(bank, i, status=status)
        with torch.no_grad():
            pred = model(torch.zeros(5, 2), torch.tensor([0, 2, 3, 4, 5]), torch.zeros(5, 8), S.torch_bank(torch, bank))
        self.assertTrue(torch.isfinite(pred).all())

    def test_order_quantity_cost_target_interact_before_pooling(self):
        card = next(c for c in S.T.REVIEWED_CARDS if c["setCode"] == "SHD_002")
        variants = [card, *S.T.hard_negatives(card).values()]
        bank = S.empty_bank()
        for i, variant in enumerate(variants):
            encoded = S.T.capability(variant, variant["abilityPath"])
            self.assertTrue(encoded.known)
            S.fill_program(bank, i, encoded.semantic_tokens, encoded.role_tokens)
        with torch.no_grad():
            encoded = self.model().encode_program_bank(S.torch_bank(torch, bank)).numpy()
        for i in range(1, len(variants)):
            self.assertGreater(np.max(abs(encoded[0] - encoded[i])), 1e-8)

    def test_deck_entry_permutation_count_split_invariance_and_multiplicity(self):
        bank = S.torch_bank(torch, S.make_banks(records())[1]["correct-ir"])
        grouped = np.zeros((1, 8), np.float32); grouped[0, :2] = [2, 3]
        expanded = np.zeros_like(grouped)
        for index in [1, 0, 1, 0, 1]: expanded[0, index] += 1
        model = self.model()
        with torch.no_grad():
            a = model(torch.zeros(1, 2), torch.zeros(1, dtype=torch.long), torch.tensor(grouped), bank)
            b = model(torch.zeros(1, 2), torch.zeros(1, dtype=torch.long), torch.tensor(expanded), bank)
            changed = model(torch.zeros(1, 2), torch.zeros(1, dtype=torch.long), torch.tensor(grouped * 2), bank)
        self.assertTrue(torch.equal(a, b))
        self.assertFalse(torch.equal(a, changed))

    def test_unavailable_labels_do_not_change_loss(self):
        logits = torch.zeros(2, 7); target = torch.zeros(2, 7); mask = torch.ones(2, 7)
        mask[:, 2] = 0
        before = S.loss_fn(torch, logits, target, mask)
        target[:, 2] = 100
        self.assertEqual(float(before), float(S.loss_fn(torch, logits, target, mask)))


if __name__ == "__main__": unittest.main()
