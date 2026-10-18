"""Data-contract tests use synthetic receipt-shaped values, never engine labels."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import supported_transition_data as D


def actual_plan():
    path = D.T.PINNED_SOURCE / "compiler/generated"
    return D.make_plan(json.loads((path / "cards.json").read_text()), json.loads((path / "runtime-admission.json").read_text()))


def synthetic_case(code, family):
    """A unit-test fixture only; not saved or used as native training data."""
    spec = D.CONTEXT_FAMILIES[family]
    def card(identity, set_code, hp, damage=0, exhausted=False):
        return dict(id=identity, setCode=set_code, hp=hp, damage=damage, exhausted=exhausted, deployed=False, upgrades=[])
    players = {seat: dict(base=card(seat + "b", "ASH_019", 30, spec["own_base_damage"] if seat == "p1" else spec["opponent_base_damage"]),
                          leader=card(seat + "l", code if seat == "p1" else "IBH_053", 10, exhausted=spec["source_exhausted"] if seat == "p1" else False),
                          ground=[], space=[], resources=[]) for seat in ("p1", "p2")}
    players["p1"]["resources"] = [card("resource", "LOF_256", 4, exhausted=not spec["resource_ready"])]
    players[spec["first_owner"]]["ground"].append(card("unit1", "LOF_256", 4, spec["first_damage"], True))
    players["p2"]["ground"].append(card("unit2", "LOF_256", 4, spec["second_damage"], True))
    chosen = "unit1" if code == "ASH_011" or family in (3, 6) else "p1b" if family in (4, 7) else "p2b"
    refs = dict(source="p1l", resource="resource", chosen=chosen, own_base="p1b", opponent_base="p2b", first_unit="unit1", second_unit="unit2")
    action = lambda identity: dict(kind="card", card=identity, arg=None, method=None, label="synthetic test action")
    use = not spec["source_exhausted"] and (spec["resource_ready"] or code == "ASH_011")
    before = dict(state=dict(players=players), offeredActions=[action("p1l")] if use else [])
    case = dict(card=code, context_family=family, abilityPath=["abilities", "leader", 0], refs=refs, before=before,
                sourceAction=action("p1l") if use else None, targetPrompt=None, targetAction=None, after=None, following=None,
                targets={k: None for k in D.TARGET_NAMES}, target_mask={k: False for k in D.TARGET_NAMES})
    case["targets"]["source_use"], case["target_mask"]["source_use"] = use, True
    if not use:
        return case
    eligible = [c["id"] for p in players.values() for c in p["ground"] if c["hp"] - c["damage"] >= 2] if code == "ASH_011" else ["p1b", "p2b"]
    case["targetPrompt"] = dict(offeredActions=[action(c) for c in eligible])
    allowed = chosen in eligible
    case["targets"]["target_allowed"], case["target_mask"]["target_allowed"] = allowed, True
    if not allowed:
        return case
    after = copy.deepcopy(before)
    source = D.public_card(after["state"], "p1l")[2]
    source["exhausted"] = True
    D.public_card(after["state"], chosen)[2]["damage"] += 1
    after["state"]["players"]["p1"]["resources"][0]["exhausted"] |= code == "IBH_053"
    terminal = D.public_card(after["state"], chosen)[2]["damage"] >= D.public_card(after["state"], chosen)[2]["hp"]
    after["terminal"] = terminal
    after["offeredActions"] = []
    case.update(after=after, targetAction=action(chosen), following=None if terminal else copy.deepcopy(after))
    for k, value in dict(cost_resource=int(code == "IBH_053"), damage_delta=1, source_exhausted_after=True, terminal=terminal).items():
        case["targets"][k], case["target_mask"][k] = value, True
    if not terminal:
        case["targets"]["followup_source_offered"], case["target_mask"]["followup_source_offered"] = False, True
    return case


def synthetic_receipt(plan):
    return dict(schema=D.NATIVE_SCHEMA, sourceRevision=plan["sourceRevision"], applyCalls=40,
                selectedWholeCards=list(plan["complete_runtime_definition_codes"]), selectedCatalogueSha256="a" * 64,
                provenance=[dict(card=code, sourceHash=p["sourceHash"], sourcePath=p["sourcePath"], abilityPath=p["ability_path"], actualUnmodifiedAbility=p["raw_ability"]) for code, p in plan["programs"].items()],
                cases=[synthetic_case(code, i) for code in D.SELECTED for i in range(8)])


class SupportedTransitionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = actual_plan()

    def test_actual_coverage_distinguishes_parser_runtime_and_binding(self):
        plan = self.plan
        self.assertEqual(plan["coverage_scan"]["parser_parseable_count"], 9)
        self.assertEqual(plan["coverage_scan"]["runtime_admitted_parseable_count"], 6)
        self.assertEqual(set(plan["programs"]), {"ASH_011", "IBH_053"})
        excluded = {p["card"]: p for p in plan["excluded_selected_abilities"]}
        self.assertFalse(excluded["IBH_001"]["whole_card_runtime_admitted"])
        self.assertTrue(excluded["TWI_056"]["whole_card_runtime_admitted"])
        for p in plan["programs"].values():
            self.assertEqual(D.T.ability(p["raw_ability"]), p["program"])
            self.assertTrue(p["complete_definition_preserved"])
            self.assertIn("unit", p["all_side_ability_counts"])

    def test_fixed_split_groups_both_ids_and_has_terminal_support_both_partitions(self):
        data, manifest = D.convert_receipt(synthetic_receipt(self.plan), self.plan)
        self.assertEqual(data["context_features"].shape, (16, 19))
        self.assertEqual(data["targets"].shape, (16, 7))
        self.assertEqual((len(data["train_idx"]), len(data["val_idx"])), (10, 6))
        self.assertEqual(set(data["context_groups"][data["train_idx"]]), set(range(5)))
        self.assertEqual(set(data["context_groups"][data["val_idx"]]), {5, 6, 7})
        self.assertEqual(set(data["source_cards"][data["train_idx"]]), set(D.SELECTED))
        self.assertEqual(set(data["source_cards"][data["val_idx"]]), set(D.SELECTED))
        self.assertFalse(manifest["split"]["held_out_card_ids"])
        self.assertEqual(set(data["context_fingerprints"][data["train_idx"]]) & set(data["context_fingerprints"][data["val_idx"]]), set())
        self.assertEqual(manifest["target_variation"]["terminal"], dict(train=[0., 1.], val=[0., 1.]))
        np.testing.assert_array_equal(data["deck_counts"].sum(1), np.ones(16))

    def test_unknown_targets_stay_masked_and_unobserved_prompt_is_not_negative(self):
        data, manifest = D.convert_receipt(synthetic_receipt(self.plan), self.plan)
        row = next(i for i, r in enumerate(manifest["records"]) if r["source_card"] == "IBH_053" and r["context_family"] == 1)
        np.testing.assert_array_equal(data["target_mask"][row], [1, 0, 0, 0, 0, 0, 0])
        self.assertIn("target_allowed", manifest["records"][row]["unknown_targets"])
        self.assertIsNone(manifest["records"][row]["raw_native_case"]["targets"]["target_allowed"])

    def test_labels_offers_future_and_private_fields_cannot_change_context_input(self):
        case = synthetic_case("ASH_011", 0)
        expected = D.context_features(case)
        changed = copy.deepcopy(case)
        changed["targets"] = {k: 999 for k in D.TARGET_NAMES}
        changed["before"]["offeredActions"] = []
        changed["targetPrompt"] = dict(offeredActions=[dict(secret="not an input")])
        changed["after"] = dict(secret="not an input")
        for p in changed["before"]["state"]["players"].values():
            p["hand"] = [dict(secret="private" * 100)]
            p["deck"] = [dict(secret="hidden draw order")]
        np.testing.assert_array_equal(D.context_features(changed), expected)

    def test_case_order_and_object_key_order_do_not_change_tensor_bank(self):
        receipt = synthetic_receipt(self.plan)
        a, _ = D.convert_receipt(receipt, self.plan)
        receipt["cases"].reverse()
        receipt = json.loads(json.dumps(receipt, sort_keys=True))
        b, _ = D.convert_receipt(receipt, self.plan)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])

    def test_changed_provenance_unsupported_fields_and_invented_labels_fail_closed(self):
        for kind in ("hash", "program", "whole", "source-label", "target-label", "unknown-committed", "missing-case", "too-many-applies"):
            receipt = synthetic_receipt(self.plan)
            if kind == "hash": receipt["provenance"][0]["sourceHash"] = "0" * 64
            elif kind == "program": receipt["provenance"][0]["actualUnmodifiedAbility"] = {"unsupported": True}
            elif kind == "whole": receipt["selectedWholeCards"].remove("ASH_011")
            elif kind == "source-label": receipt["cases"][0]["targets"]["source_use"] = False
            elif kind == "target-label": receipt["cases"][0]["targets"]["target_allowed"] = False
            elif kind == "unknown-committed": receipt["cases"][2]["target_mask"]["damage_delta"] = True
            elif kind == "missing-case": receipt["cases"].pop()
            else: receipt["applyCalls"] = 97
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                D.convert_receipt(receipt, self.plan)
        changed = copy.deepcopy(self.plan["programs"]["ASH_011"]["raw_ability"])
        changed["unreviewedField"] = True
        with self.assertRaises(D.T.UnknownIR):
            D.T.ability(changed)


if __name__ == "__main__":
    unittest.main()
