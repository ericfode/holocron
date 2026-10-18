"""Pure native plan/source contracts; no engine, model or compiler execution."""
import copy
import json
from pathlib import Path
import unittest

import native_effect_v2 as P


class NativePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gen=P.G.PINNED_KESSEL/"compiler/generated"
        cls.catalog=json.loads((gen/"cards.json").read_text())
        cls.runtime=json.loads((gen/"runtime-admission.json").read_text())
        cls.coverage=json.loads((P.HERE.parents[3]/"experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json").read_text())
        cls.plan=P.build_plan(cls.catalog,cls.runtime,cls.coverage)
        cls.rows={r["setCode"]:r for r in cls.catalog["cards"]}
        cls.rust=(P.HERE/"native_effect_v2_collector/src/main.rs").read_text()

    def test_actual_whole_rows_and_template_family_holdouts(self):
        plan=self.plan
        self.assertEqual(len(plan["cards"]),12)
        self.assertEqual(sum(c["main_copies"] for c in plan["cards"]),58)
        for code,row in plan["selected_whole_rows"].items():
            self.assertEqual(row,self.rows[code])
        self.assertFalse({P.FAMILIES[c] for c in P.TRAIN}&{P.FAMILIES[c] for c in P.HELD})
        self.assertEqual(P.FAMILIES["LAW_131"],P.FAMILIES["JTL_079"])
        self.assertEqual(P.FAMILIES["LAW_127"],P.FAMILIES["ASH_228"])
        self.assertEqual(plan["split"]["cells"],dict(train=21,program_held=15,state_held=7,joint=5))
        self.assertEqual(plan["expected_cases"]*plan["max_applies_per_case"],240)
        self.assertLessEqual(240,plan["campaign_max_engine_applies"])

    def test_all_enemy_area_anchors_and_minus5_host_survive(self):
        for witness in self.plan["survival_witnesses"]:
            self.assertTrue(all(h>0 for h in witness["after_area_minus3"]))
            self.assertGreater(witness["after_targeted_minus5_remaining"],0)
        self.assertEqual(self.plan["survival_witnesses"][1]["friendly_ground_hp"],7)
        self.assertEqual(self.plan["survival_witnesses"][1]["after_targeted_minus5_remaining"],1)
        # Prevent a helper/cost refactor from silently activating SEC051's XP hook.
        changed=copy.deepcopy(self.catalog)
        next(r for r in changed["cards"] if r["setCode"]=="TWI_111")["card"]["hp"]=3
        with self.assertRaisesRegex(ValueError,"death hook"):
            P.build_plan(changed,self.runtime,self.coverage)

    def test_jtl217_predeclared_two_ready_positive_opportunities(self):
        worlds=self.plan["contexts"]
        q1=P.query_spec("JTL_217",1);q2=P.query_spec("JTL_217",2)
        self.assertEqual(q1["ref"],"space_small")
        self.assertFalse(worlds[1]["small"]["exhausted"])
        self.assertEqual(worlds[1]["small"]["owner"],"p1")
        self.assertEqual(q2["ref"],"friendly_ground")
        self.assertFalse(worlds[2]["ground"]["exhausted"])
        self.assertTrue(worlds[3]["ground"]["exhausted"])
        # Public held-world count combination differs from train world1.
        self.assertEqual(worlds[3]["small"]["code"],"SHD_060")
        self.assertNotIn("fighter",self.rows["SHD_060"]["card"]["traits"])

    def test_area_observation_attachment_and_decline_are_distinct(self):
        for world in range(4):
            self.assertEqual(P.query_spec("SEC_051",world)["mode"],"passive-area-anchor")
            self.assertEqual(P.query_spec("LOF_151",world)["mode"],"upgrade-attachment")
        self.assertEqual(P.query_spec("ASH_171",1)["ref"],"unique_upgrade")
        self.assertEqual(P.query_spec("ASH_171",0)["ref"],"nonunique_upgrade")
        self.assertEqual(len(self.plan["predeclared_behavior_pairs"]),10)

    def test_unreviewed_hidden_or_trait_mutating_program_rejects(self):
        for kind in ("draw","gainTrait"):
            changed=copy.deepcopy(self.catalog)
            abilities=next(r for r in changed["cards"] if r["setCode"]=="SEC_142")["abilities"]
            next(iter(abilities.values())).append({"effect":{"kind":kind}})
            with self.assertRaisesRegex(ValueError,"missing public-state"):
                P.build_plan(changed,self.runtime,self.coverage)

    def test_physical_attachment_and_shield_constructor_contract(self):
        rust=self.rust
        attach=rust.split("fn attach_fixture",1)[1].split("fn shield_fixture",1)[0]
        shield=rust.split("fn shield_fixture",1)[1].split("fn fixture",1)[0]
        self.assertEqual(attach.count("registration_order.push(id)"),1)
        self.assertNotIn("registration_order",shield)
        for link in (".parent=host",".next_token=old_tokens",".next_upgrade=old_upgrades",".shield=id",".upgrades=id"):
            self.assertIn(link,shield)
        self.assertIn("native public upgrade-target query rejects fixture host",rust)
        self.assertIn("public fixture snapshot/load mismatch",rust)
        self.assertIn("MAX_APPLY:usize=240",rust)
        self.assertIn('let mode=query["mode"]',rust)
        self.assertNotIn("expected_damage",rust)


if __name__=="__main__":unittest.main()
