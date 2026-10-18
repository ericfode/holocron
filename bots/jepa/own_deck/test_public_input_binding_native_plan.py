"""Pure plan and fixture regressions; never compile or execute a native engine."""
import copy
import json
import unittest

import public_input_binding_native_plan as P


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=json.loads((P.HERE/"public_input_binding_collector/fixtures/whole-rows.json").read_text())
        cls.catalog=dict(cards=fixture["cards"]);cls.runtime=fixture["runtime_admission"]
        cls.plan=P.build_plan(cls.catalog,cls.runtime)
        cls.rust=(P.HERE/"public_input_binding_collector/src/main.rs").read_text()

    def test_exact_sixteen_factorial_worlds_and_cap(self):
        p=self.plan;w=p["worlds"]
        self.assertEqual([v["id"]for v in w],list(range(16)))
        self.assertEqual(len({(v["own_helper"],v["opponent_helper"],v["victim_damage"])for v in w[:8]}),8)
        self.assertEqual(len({(v["intent_ref"],v["host_damage"],v["layout"])for v in w[8:]}),8)
        self.assertEqual(p["expected_cases"]*p["max_applies_per_case"],80)
        self.assertEqual((p["native_build_max_seconds"],p["collector_max_seconds"],p["campaign_max_seconds"]),(30,60,90))
        self.assertEqual((p["neural_forwards"],p["optimizer_updates"],p["numerical_fits"]),(0,0,0))

    def test_complete_raw_rows_and_deep_byte_pins(self):
        rows={r["setCode"]:r for r in self.catalog["cards"]}
        self.assertEqual(len(self.plan["selected_whole_cards"]),9)
        for code,row in self.plan["selected_whole_rows"].items():
            self.assertEqual(row,rows[code]);self.assertEqual(self.plan["selected_row_pins"][code]["sha256"],P.digest(row))
            self.assertGreater(self.plan["selected_row_pins"][code]["bytes"],0)
        self.assertNotIn("LOF_093",self.plan["selected_whole_cards"])

    def test_wrong_owner_contrast_not_contaminated_by_victim(self):
        p=self.plan;rows=p["selected_whole_rows"]
        self.assertEqual(p["helpers"]["victim"],"SEC_028")
        self.assertFalse(set(rows["SEC_028"]["card"]["aspects"])&{"command","cunning"})
        self.assertFalse(set(rows["LAW_045"]["card"]["aspects"])&{"command","cunning"})
        for w in p["worlds"][:8]:self.assertEqual(w["hypothesis"]["damage_delta"],5 if w["own_helper"]=="SEC_094"else 3)
        changed=copy.deepcopy(self.catalog)
        next(r for r in changed["cards"]if r["setCode"]=="SEC_028")["card"]["aspects"]=["command"]
        with self.assertRaisesRegex(ValueError,"wrong-owner"):
            P.build_plan(changed,self.runtime)

    def test_physical_survival_and_plain_nonunique_hosts(self):
        p=self.plan;v=p["survival_witness"]
        self.assertEqual((v["total_before_hp"],v["minimum_remaining_hp"]),(7,1))
        c=p["selected_whole_rows"]["SEC_028"]
        self.assertFalse(c["card"]["unique"]);self.assertFalse(any(c["abilities"].values()));self.assertFalse(c["keywordValues"])
        self.assertNotIn("vehicle",c["card"]["traits"])

    def test_both_actual_anchors_are_predeclared_in_both_intents(self):
        for world in self.plan["worlds"][8:]:
            self.assertEqual(world["observation_refs"],["host_a","host_b"])
            other="host_b"if world["intent_ref"]=="host_a"else"host_a"
            self.assertEqual(world["hypothesis"][other+"_power_delta"],0)
        self.assertEqual(len(self.plan["declared_pairs"]),16)

    def test_ordinary_upgrade_links_and_registration_once(self):
        attach=self.rust.split("fn attach_fixture",1)[1].split("fn fixture",1)[0]
        self.assertEqual(attach.count("registration_order.push(id)"),1)
        self.assertIn("native public upgrade-target query rejects fixture host",self.rust)
        self.assertIn("public fixture snapshot/load mismatch",self.rust)
        self.assertIn('let order=if world["layout"]==0{[4,5]}else{[5,4]}',self.rust)

    def test_before_public_metadata_and_no_endpoint_parent_input(self):
        capture=self.rust.split("fn capture",1)[1].split("fn attach_fixture",1)[0]
        for key in ("printed_traits","printed_aspects","role_matches","observation_anchor_a","observation_anchor_b"):
            self.assertIn(key,capture)
        self.assertNotIn(".parent",capture)
        self.assertIn('if *id==0{projections.insert((*slot).into(),Value::Null);continue;}',capture)
        self.assertNotIn('world["hypothesis"]',self.rust)
        self.assertIn('if !complete{break;}',self.rust)
        self.assertIn('self.trace(&json!({"phase":"beforeApply"',self.rust)
        self.assertIn("self.calls+=1;let result=e.apply",self.rust)


if __name__=="__main__":unittest.main()
