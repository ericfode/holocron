"""Existing-runtime inventory and grouping tests; no native/model execution."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grounded_contrast_data as G


class GroundedContrastInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generated = G.PINNED_KESSEL / "compiler/generated"
        cls.catalog = json.loads((generated / "cards.json").read_text())
        cls.runtime = json.loads((generated / "runtime-admission.json").read_text())
        cls.report = G.inventory(cls.catalog, cls.runtime)

    def test_existing_whole_card_runtime_counts_and_exact_core(self):
        report = self.report
        self.assertEqual((report["runtime_admitted_action_abilities"], report["runtime_admitted_action_cards"], report["normalized_program_groups"]), (41, 40, 41))
        self.assertEqual(report["duplicate_program_groups"], {})
        self.assertEqual({r["card"] for r in report["proposed_core"]}, set(G.CORE_CODES))
        self.assertEqual(len(report["proposed_core"]), 12)
        for record in report["proposed_core"]:
            raw = next(r for r in self.catalog["cards"] if r["setCode"] == record["card"])
            side, index = record["ability_path"][1:]
            self.assertEqual(record["raw_ability"], raw["abilities"][side][index])
            self.assertEqual(record["whole_card_row_sha256"], G.digest(raw))
            self.assertEqual(record["sourceHash"], raw["sourceHash"])
            self.assertTrue(record["whole_card_admitted"])
            self.assertEqual(record["complete_ability_counts"], {k: len(v) for k, v in raw["abilities"].items()})

    def test_title_and_object_key_order_do_not_change_exact_program_group(self):
        raw = self.report["proposed_core"][0]["raw_ability"]
        changed = json.loads(json.dumps(raw, sort_keys=True))
        changed["title"] = "Unrelated display title"
        self.assertEqual(G.digest(G.normalized_program(raw)), G.digest(G.normalized_program(changed)))
        original = copy.deepcopy(raw)
        self.assertNotIn("title", G.normalized_program(original))
        self.assertIn("title", original)

    def test_semantic_order_quantity_roles_and_unknown_fields_are_retained(self):
        record = next(r for r in self.report["proposed_core"] if r["card"] == "SOR_011")
        original = record["raw_ability"]
        for kind in ("sequence", "quantity", "owner", "unknown"):
            changed = copy.deepcopy(original)
            if kind == "sequence": changed["effect"]["effects"].reverse()
            elif kind == "quantity": changed["effect"]["effects"][0]["amount"]["value"] += 1
            elif kind == "owner": changed["targetResolver"]["owner"] = "opponent"
            else: changed["unreviewedContinuation"] = {"kind": "unknown", "target": "source"}
            with self.subTest(kind=kind):
                self.assertNotEqual(G.digest(G.normalized_program(changed)), record["program_group_id"])
        paths = record["dependencies"]["typed_node_paths"]
        self.assertIn(dict(path="/effect/effects/0", kind="damage"), paths)
        self.assertIn(dict(path="/effect/effects/1", kind="ready"), paths)

    def test_runtime_rejection_does_not_become_partial_card_admission(self):
        catalog = copy.deepcopy(self.catalog)
        unadmitted = copy.deepcopy(next(r for r in catalog["cards"] if r["setCode"] == "ASH_011"))
        unadmitted["setCode"] = "TST_UNADMITTED"
        catalog["cards"].append(unadmitted)
        report = G.inventory(catalog, self.runtime)
        self.assertEqual(report["runtime_admitted_action_abilities"], 41)
        self.assertNotIn("TST_UNADMITTED", {r["card"] for r in report["records"]})

    def test_exact_duplicate_program_groups_ignore_names_but_not_fields(self):
        catalog, runtime = copy.deepcopy(self.catalog), copy.deepcopy(self.runtime)
        row = copy.deepcopy(next(r for r in catalog["cards"] if r["setCode"] == "ASH_011"))
        row["setCode"] = "TST_DUPLICATE"
        row["abilities"]["leader"][0]["title"] = "New title, same exact mechanics"
        row["abilities"]["unit"] = []
        catalog["cards"].append(row)
        runtime["runtimeAdmittedCards"].append(dict(setCode="TST_DUPLICATE", implementation="synthetic test declaration"))
        report = G.inventory(catalog, runtime)
        self.assertEqual(report["runtime_admitted_action_abilities"], 42)
        self.assertEqual(report["normalized_program_groups"], 41)
        duplicate = next(iter(report["duplicate_program_groups"].values()))
        self.assertEqual({p["card"] for p in duplicate}, {"ASH_011", "TST_DUPLICATE"})

    def test_program_identity_alias_and_global_atom_split_checks(self):
        plan = G.split_plan(self.report)
        self.assertEqual((len(plan["train_codes"]), len(plan["heldout_codes"])), (10, 2))
        self.assertEqual(plan["identity_overlap"], 0)
        self.assertEqual(plan["normalized_program_overlap"], 0)
        self.assertEqual(plan["reprint_alias_overlap"], 0)
        for code, coverage in plan["constituent_coverage"].items():
            self.assertTrue(coverage["all_global_typed_atoms_seen"], code)
            self.assertEqual(coverage["unseen_global_typed_atoms"], [])
            self.assertTrue(coverage["novel_positioned_atoms"])
        for kind in ("canonical_card_id", "program_group_id", "aliases"):
            changed = copy.deepcopy(self.report)
            train = next(r for r in changed["proposed_core"] if r["card"] == G.TRAIN_CODES[0])
            held = next(r for r in changed["proposed_core"] if r["card"] == G.HELDOUT_CODES[0])
            held[kind] = train[kind]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                G.split_plan(changed)


class GroundedContrastReceiptTests(unittest.TestCase):
    """Synthetic receipt witnesses test conversion, never stand in for native data."""
    @classmethod
    def setUpClass(cls):
        generated = G.PINNED_KESSEL / "compiler/generated"
        cls.catalog = G.assembled_catalog(generated)
        raw = json.loads((generated / "cards.json").read_text())
        cls.report = G.inventory(raw, json.loads((generated / "runtime-admission.json").read_text()))
        cls.plan_path = G.HERE / "grounded_native_collector/collection-plan.json"
        cls.plan = json.loads(cls.plan_path.read_text())
        cls.rows = {r["setCode"]: r for r in cls.catalog["cards"]}

    def receipt(self):
        plan, records = self.plan, []
        programs = {p["code"]: p for p in plan["programs"]}
        for state in plan["contexts"]:
            for code in G.CORE_CODES:
                program = programs[code]
                refs = {slot: "c" + str(i) for i, slot in enumerate(G.CANDIDATES)}
                helpers = plan["helpers"]
                codes = [helpers["base"], helpers["base"], helpers["ground"], helpers["ground"], helpers["space"], helpers["imperial"], helpers["creature"], code]
                projections = {}
                for i, (slot, card_code) in enumerate(zip(G.CANDIDATES, codes)):
                    card = self.rows[card_code]["card"]
                    zone = "base" if i < 2 else "space" if i == 4 else "leader" if i == 7 and program["side"] == "leader" else "ground"
                    projections[slot] = dict(id=refs[slot], code=card_code, owner="p2" if i in (1, 3, 4) else "p1", zone=zone,
                        present=True, in_arena=zone in ("ground", "space"), attackable=zone in ("ground", "space", "base"),
                        is_unit=zone in ("ground", "space"), is_base=zone == "base", damage=0, exhausted=False,
                        hp=card.get("hp") or 0, power=card.get("power") or 0, shield_count=0, xp_count=0,
                        known=dict(damage=True, exhausted=True, hp=card.get("hp") is not None, power=card.get("power") is not None, shield_count=True, xp_count=True))
                projections["source"]["exhausted"] = state["source_exhausted"]
                for slot, fields in state["overrides"].items():
                    projections[slot].update(fields)
                before = dict(state=dict(players=dict(p1=dict(resources=[dict(exhausted=i >= state["ready_resources"]) for i in range(3)]))),
                              projections=projections, offeredActions=[], decision="ActionWindow", terminal=False, sourceInstance=None)
                queries = [dict(chosen_ref=s, chosen_id=refs[s], targetAction=None, after=None, following=None, followupPass=None, engineError=None,
                                targets={n: 0 for n in G.TARGETS}, target_mask={n: n == "source_use" for n in G.TARGETS}) for s in G.CANDIDATES]
                records.append(dict(card=code, abilityPath=["abilities", program["side"], program["index"]], context_family=state["id"], context_group="family-" + str(state["id"]),
                                    identity_partition=program["partition"], state_partition=state["partition"], refs=refs, before=before, sourceAction=None, sourceOpened=None,
                                    menuAction=None, targetPrompt=None, cancelAction=None, cancelled=None, queries=queries, source_use=False, source_use_known=True, engine_error_branches=0))
        selected = sorted(set(G.CORE_CODES) | set(plan["helpers"].values()) | set(plan["required_native_tokens"]))
        return dict(schema="jepa-grounded-native-transitions/1", sourceRevision=G.REVISION, collectionPlan=copy.deepcopy(plan), collectionPlanSha256=G.sha(self.plan_path),
                    candidateOrder=list(G.CANDIDATES), targetNames=list(G.TARGETS), applyCalls=0, selectedWholeCards=selected, selectedCatalogueSha256=G.native_catalog_hash(self.catalog, selected),
                    provenance=[dict(card=p["code"], sourceHash=p["source_hash"], sourcePath=p["source_path"], abilityPath=["abilities", p["side"], p["index"]], actualUnmodifiedAbility=p["raw_ability"]) for p in plan["programs"]],
                    cases=records, native_engine_error_branches=0)

    def convert(self, receipt):
        return G.convert_receipt(receipt, self.report, self.plan, self.catalog, G.sha(self.plan_path))

    def committed(self):
        receipt = self.receipt()
        case = next(c for c in receipt["cases"] if c["card"] == "ASH_011" and c["context_family"] == 0)
        source = dict(kind="card", card=case["refs"]["source"], label="source")
        action = dict(kind="card", card=case["refs"]["enemy_ground"], label="target")
        case["before"]["offeredActions"] = [source]
        prompt = copy.deepcopy(case["before"])
        prompt.update(decision="AbilityTarget", sourceInstance=case["refs"]["source"], offeredActions=[action])
        case.update(sourceAction=source, sourceOpened=copy.deepcopy(prompt), targetPrompt=prompt, source_use=True)
        for query in case["queries"]:
            query["targets"]["source_use"] = 1
            query["target_mask"]["target_allowed"] = True
        query = case["queries"][G.CANDIDATES.index("enemy_ground")]
        after = copy.deepcopy(case["before"])
        after["projections"]["source"]["exhausted"] = True
        # A snapshot witness, deliberately not computed by inspecting the IR.
        after["projections"]["enemy_ground"]["damage"] = 1
        after["offeredActions"] = []
        query.update(targetAction=action, after=after)
        known = dict(target_allowed=1, cost_resource=0, damage_delta=1, source_exhausted_after=1,
                     target_exhausted_delta=0, shield_delta=0, xp_delta=0, target_defeated=0, terminal=0)
        for name, value in known.items():
            query["targets"][name] = value
            query["target_mask"][name] = True
        return receipt, case, query

    def test_dense_root_split_and_mask_ownership(self):
        arrays, manifest = self.convert(self.receipt())
        self.assertEqual(arrays["context_features"].shape, (168, 2))
        self.assertEqual(arrays["candidate_features"].shape, (168, 8, 26))
        self.assertEqual(arrays["targets"].shape, (168, 8, 11))
        self.assertEqual([len(arrays[k]) for k in ("train_idx", "program_holdout_idx", "state_holdout_idx", "joint_holdout_idx")], [100, 20, 40, 8])
        self.assertEqual(arrays["source_use_mask"].sum(), 168)
        self.assertEqual(arrays["target_mask"][..., :2].sum(), 0)
        self.assertEqual(arrays["candidate_allowed_mask"].sum(), 0)
        self.assertTrue((arrays["primary_candidate_mask"][:, 7] == 0).all())
        self.assertEqual(len(set(arrays["state_fingerprints"])), 14)
        self.assertEqual(manifest["native_engine_error_branches"], 0)

    def test_native_outcomes_and_actual_prompt_masks(self):
        receipt, _, _ = self.committed()
        arrays, manifest = self.convert(receipt)
        self.assertEqual(arrays["source_use"].sum(), 1)
        self.assertEqual(arrays["candidate_allowed_mask"].sum(), 8)
        self.assertEqual(arrays["candidate_allowed"].sum(), 1)
        self.assertEqual(manifest["committed_branches"], 1)
        self.assertEqual(arrays["target_mask"][..., 9].sum(), 0)  # no follow-up observed
        self.assertEqual(arrays["target_mask"][..., :2].sum(), 0)

    def test_labels_errors_and_whole_source_provenance_fail_closed(self):
        for kind in ("label", "prompt", "source", "path", "catalog", "missing", "mask", "alias_split"):
            receipt, case, query = self.committed()
            if kind == "label": query["targets"]["damage_delta"] = 7
            elif kind == "prompt": case["targetPrompt"]["offeredActions"] = []
            elif kind == "source": receipt["provenance"][0]["actualUnmodifiedAbility"] = {}
            elif kind == "path": case["abilityPath"] = ["abilities", "unit", 0]
            elif kind == "catalog": receipt["selectedCatalogueSha256"] = "0" * 64
            elif kind == "missing": receipt["cases"].pop()
            elif kind == "mask": case["queries"][0]["target_mask"]["terminal"] = True
            else: receipt["collectionPlan"]["heldout_codes"] = list(G.TRAIN_CODES[:2])
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.convert(receipt)

    def test_error_branch_is_unknown_not_a_negative_outcome(self):
        receipt, case, query = self.committed()
        query["after"] = None
        query["engineError"] = "NATIVE_APPLY_ERROR: synthetic test witness"
        for name in G.TARGETS[2:]: query["target_mask"][name] = False
        case["engine_error_branches"] = receipt["native_engine_error_branches"] = 1
        arrays, manifest = self.convert(receipt)
        self.assertEqual(manifest["native_engine_error_branches"], 1)
        self.assertEqual(arrays["candidate_allowed"].sum(), 1)
        self.assertEqual(arrays["target_mask"].sum(), 0)

    def test_primary_context_matching_and_local_candidate_no_outcome_input(self):
        receipt = self.receipt()
        case = receipt["cases"][0]
        before = case["before"]["projections"]["friendly_ground"]
        vector = G.candidate_vector(before, case["refs"]["source"], self.rows)
        altered = copy.deepcopy(before)
        altered.update(hp=float("nan"), power=float("nan"))
        altered["known"].update(hp=False, power=False)
        unknown = G.candidate_vector(altered, case["refs"]["source"], self.rows)
        self.assertTrue(np.isfinite(unknown).all())
        self.assertEqual(unknown[9], 0)
        self.assertEqual(unknown[16], 0)
        self.assertEqual(unknown[17], 0)
        self.assertEqual(vector.shape, (26,))
        case["before"]["projections"]["friendly_ground"]["power"] += 1
        with self.assertRaisesRegex(ValueError, "context differs across programs"):
            self.convert(receipt)

    def test_dead_target_deltas_unknown_defeat_observed(self):
        receipt, _, query = self.committed()
        after = query["after"]["projections"]["enemy_ground"]
        after.update(zone="discard", in_arena=False, attackable=False)
        query["targets"]["target_defeated"] = 1
        for name in ("damage_delta", "target_exhausted_delta", "shield_delta", "xp_delta"):
            query["target_mask"][name] = False
        arrays, _ = self.convert(receipt)
        self.assertEqual(arrays["target_mask"][..., 3].sum(), 0)
        self.assertEqual(arrays["targets"][..., 8].sum(), 1)


if __name__ == "__main__":
    unittest.main()
