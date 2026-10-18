"""Portable seven-source plan/fixture tests: no native engine or subprocess."""
import copy
import json
import unittest
import binding_transfer_native_plan as P


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.here=P.HERE/"binding_transfer_native_collector"
        cls.fixture=json.loads((cls.here/"fixtures/whole-rows.json").read_text())
        cls.plan=P.build_plan(cls.fixture,cls.fixture)

    def test_complete_rows_and_support_status_are_preserved(self):
        rows={r["setCode"]:r for r in self.fixture["cards"]}
        self.assertEqual(len(self.plan["selected_whole_cards"]),17)
        for code,row in self.plan["selected_whole_rows"].items():self.assertEqual(row,rows[code])
        self.assertEqual(self.plan["selected_whole_rows"]["TOKEN_SHIELD"]["status"],"unsupported")
        self.assertNotIn("TOKEN_SHIELD",self.plan["codes"])

    def test_fixed_twenty_six_roots_and_four_cells(self):
        ws=self.plan["worlds"];parts=self.plan["split"]["root_partitions"]
        self.assertEqual([w["id"]for w in ws],list(range(26)))
        self.assertEqual({c:sum(w["source_code"]==c for w in ws)for c in P.CODES},{c:6 if c=="LAW_045"else 2 if c in("ASH_228","LOF_215")else 4 for c in P.CODES})
        self.assertEqual({k:len(v)for k,v in parts.items()},dict(train=12,family_held=4,state_held=6,joint=4))
        self.assertEqual(sorted(sum(parts.values(),[])),list(range(26)))
        self.assertEqual(self.plan["collector_max_engine_applies"],48);self.assertEqual(self.plan["max_applies_per_case"],2)
        self.assertEqual(sum(w["max_applies"]for w in ws),48)

    def test_law_train_full_factorial_then_hold_new_damage(self):
        train=[w for w in self.plan["worlds"][:6]if w["partition"]=="train"]
        held=[w for w in self.plan["worlds"][:6]if w["partition"]=="state_held"]
        self.assertEqual({(w["own_helper"],w["opponent_helper"])for w in train},{(a,b)for a in("ASH_056","SEC_094")for b in("ASH_056","SEC_094")})
        self.assertEqual({w["own_helper"]for w in held},{"ASH_056","SEC_094"})
        self.assertEqual({w["opponent_helper"]for w in held},{"ASH_056"})
        self.assertEqual({w["victim_damage"]for w in train},{2});self.assertEqual({w["victim_damage"]for w in held},{3})
        self.assertEqual(self.plan["survival_witness"]["LAW_hp"],10)
        self.assertEqual(self.plan["survival_witness"]["LAW_minimum_remaining_hp"],2)

    def test_intended_endpoint_factor_is_crossed_with_damage(self):
        for code in("ASH_071","ASH_228","LOF_215","LOF_053","LOF_261"):
            group=[w for w in self.plan["worlds"]if w["source_code"]==code]
            damages=(0,)if code in("ASH_228","LOF_215")else(0,1)
            self.assertEqual({(w["intent_ref"],w["anchor_damage"])for w in group},{(r,d)for r in("anchor_a","anchor_b")for d in damages})
            self.assertTrue(all(w["requires_target"]and w["observation_refs"]==["anchor_a","anchor_b"]for w in group))

    def test_aura_anchors_are_observations_not_target_choices(self):
        group=[w for w in self.plan["worlds"]if w["source_code"]=="JTL_085"]
        self.assertEqual({w["own_anchor"]for w in group},{"anchor_a","anchor_b"})
        self.assertTrue(all(w["observation_mode"]=="passive-aura"and not w["requires_target"]and w["intent_ref"]=="source"for w in group))
        self.assertTrue(all(w["max_applies"]==1 for w in group))
        aura=self.plan["selected_whole_rows"]["JTL_085"]
        self.assertEqual(aura["card"]["keywords"],[])
        self.assertEqual([a["trigger"]for a in aura["abilities"]["card"]],["constant"])

    def test_independent_numeric_templates_and_explicit_limits(self):
        gate=self.plan["template_gate"]
        self.assertEqual(len(set(gate["expected_positive_damage_templates"])),2)
        self.assertEqual(len(set(gate["expected_positive_stat_templates"])),2)
        self.assertEqual(P.TEMPLATES["ASH_228"],P.TEMPLATES["LOF_053"])
        self.assertFalse(gate["negative_sign_qualification"]);self.assertFalse(gate["keywords_qualified"])
        self.assertTrue(gate["support_requires_native"]);self.assertIn("UNSUPPORTED",gate["aspect_numeric_new_program_gate"])
        self.assertEqual(self.plan["numeric_support_prelabel"]["training_positive_hp"],[1,3])

    def test_changed_survival_host_or_extra_prompt_rejects(self):
        for code,mutate in(("ASH_066",lambda r:r["card"].update(upgradeHp=0)),("SEC_028",lambda r:r["card"].update(traits=["sith"])),("ASH_228",lambda r:r["abilities"]["card"][0].update(optional=True)),("TOKEN_SHIELD",lambda r:r.update(status="supported"))):
            bad=copy.deepcopy(self.fixture);row=next(r for r in bad["cards"]if r["setCode"]==code);mutate(row)
            with self.assertRaises(ValueError):P.build_plan(bad,bad)

    def test_collector_preserves_durable_budget_and_full_native_definitions(self):
        source=(self.here/"src/main.rs").read_text()
        self.assertIn("const MAX_APPLY:usize=48;",source);self.assertIn('if b.calls-start>=world["max_applies"]',source)
        self.assertEqual(source.count('.env("GIT_OPTIONAL_LOCKS","0")'),2)
        self.assertLess(source.index('"phase":"beforeApply"'),source.index("let result=e.apply(s,a)"))
        self.assertIn("fixtureAttachmentWitnesses",source);self.assertIn('"requires_target":world["requires_target"]',source)
        self.assertNotIn('["hypothesis"]',source)
        self.assertIn('name = "binding-transfer-native-collector"',(self.here/"Cargo.toml").read_text())


if __name__=="__main__":unittest.main()
