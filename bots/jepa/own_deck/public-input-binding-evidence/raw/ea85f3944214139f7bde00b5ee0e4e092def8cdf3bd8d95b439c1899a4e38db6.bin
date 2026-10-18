"""Portable recovery invariants: no native constructors, subprocesses or models."""
import copy
import hashlib
import json
import unittest

import public_input_binding_recovery_plan as P


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.here=P.HERE/"public_input_binding_recovery_collector"
        cls.v1=json.loads((cls.here/"fixtures/native-plan-v1.json").read_text())
        cls.catalog=json.loads((cls.here/"fixtures/native-token-support.json").read_text())
        cls.v2=P.build_plan(cls.v1,cls.catalog)

    def test_original_science_and_all_nine_rows_are_unchanged(self):
        P.assert_recovery_invariants(self.v1,self.v2)
        self.assertEqual(self.v1["worlds"],self.v2["worlds"])
        self.assertEqual(self.v1["cards"],self.v2["cards"])
        self.assertEqual(self.v1["declared_pairs"],self.v2["declared_pairs"])
        self.assertEqual(hashlib.sha256((self.here/"fixtures/native-plan-v1.json").read_bytes()).hexdigest(),P.V1_PLAN_SHA256)

    def test_only_exact_unsupported_constructor_token_is_added(self):
        self.assertEqual(set(self.v2["selected_whole_cards"])-set(self.v1["selected_whole_cards"]),{"TOKEN_SHIELD"})
        self.assertEqual(len(self.v2["selected_whole_cards"]),10)
        row=self.v2["selected_whole_rows"]["TOKEN_SHIELD"]
        self.assertEqual(row["status"],"unsupported");self.assertEqual(row["card"]["types"],["token","upgrade"])
        self.assertEqual(P.digest(row),P.TOKEN_ROW_SHA256)
        self.assertFalse(self.v2["recovery"]["support_is_experimental_card"])

    def test_world_or_source_hypothesis_drift_rejects(self):
        for key in("worlds","cards","declared_pairs"):
            bad=copy.deepcopy(self.v2);bad[key]=[]
            with self.assertRaisesRegex(ValueError,"scientific value"):
                P.assert_recovery_invariants(self.v1,bad)
        bad=copy.deepcopy(self.v2);bad["selected_whole_rows"]["LAW_045"]["card"]["power"]=99
        with self.assertRaisesRegex(ValueError,"whole row"):
            P.assert_recovery_invariants(self.v1,bad)

    def test_token_normalization_or_extra_support_rejects(self):
        with self.assertRaisesRegex(ValueError,"constructor support row absent"):
            P.build_plan(self.v1,dict(cards=[]))
        bad=copy.deepcopy(self.catalog);bad["cards"][0]["status"]="supported"
        with self.assertRaisesRegex(ValueError,"support row changed"):
            P.build_plan(self.v1,bad)
        bad=copy.deepcopy(self.v2);bad["selected_whole_cards"].append("TOKEN_EXPERIENCE")
        with self.assertRaisesRegex(ValueError,"only mandatory"):
            P.assert_recovery_invariants(self.v1,bad)

    def test_new_rust_is_exact_original_and_binary_name_is_distinct(self):
        source=(self.here/"src/main.rs").read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),"f80e5fa4cce45de0eedbe0b8b66587578fa96494f3d56d899acc16ad846b518c")
        cargo=(self.here/"Cargo.toml").read_text()
        self.assertIn('name = "public-input-binding-recovery-collector"',cargo)
        self.assertNotIn('name = "public-input-binding-collector"',cargo)
        self.assertEqual((self.here/"Cargo.lock").read_bytes(),(P.HERE/"public_input_binding_collector/Cargo.lock").read_bytes())

    def test_support_never_becomes_a_physical_fixture_card(self):
        source=(self.here/"src/main.rs").read_text()
        fixture=source.split("fn fixture",1)[1].split("fn offered",1)[0]
        self.assertNotIn("TOKEN_SHIELD",fixture);self.assertNotIn("shield_fixture",source)
        self.assertEqual(self.v2["recovery"]["expected_physical_shield_instances"],0)
        for code,row in self.v1["selected_whole_rows"].items():
            self.assertNotIn("shielded",row["keywordValues"],code)


if __name__=="__main__":unittest.main()
