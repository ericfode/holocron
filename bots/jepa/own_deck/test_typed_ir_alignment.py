"""Typed-IR structural wiring and explicitly synthetic primitive checks."""
import copy
import json
from pathlib import Path
import random
import unittest

import typed_ir_alignment as T


def permute_keys(value,rng):
    if isinstance(value,dict):
        keys=list(value); rng.shuffle(keys)
        return {k:permute_keys(value[k],rng) for k in keys}
    if isinstance(value,list): return [permute_keys(v,rng) for v in value]
    return value


class TypedIRTests(unittest.TestCase):
    def test_four_actual_selected_abilities_encode_without_whole_card_claim(self):
        for card in T.REVIEWED_CARDS:
            encoded=T.capability(card,card["abilityPath"])
            self.assertTrue(encoded.known,encoded.reason)
            self.assertIn("selected ability only",encoded.provenance["coverage"])
            self.assertTrue(encoded.semantic_tokens)

    def test_fifty_object_key_permutations_are_invariant(self):
        rng=random.Random(9401)
        for card in T.REVIEWED_CARDS:
            original=T.capability(card,card["abilityPath"])
            for _ in range(50):
                actual=T.capability(permute_keys(card,rng),card["abilityPath"])
                self.assertTrue(actual.known)
                self.assertEqual(actual.semantic_tokens,original.semantic_tokens)

    def test_identity_title_source_path_do_not_supply_semantic_features(self):
        for card in T.REVIEWED_CARDS:
            old=T.capability(card,card["abilityPath"])
            changed=copy.deepcopy(card)
            changed.update(setCode="UNSEEN_999",sourcePath="unseen/private/title/location",sourceHash="different")
            changed["abilities"]["leader"][0]["title"]="Entirely different printed name"
            new=T.capability(changed,changed["abilityPath"])
            self.assertEqual(old.semantic_tokens,new.semantic_tokens)
            self.assertNotEqual(old.provenance,new.provenance)
            self.assertFalse(any("UNSEEN"in str(token)or"private"in str(token)for token in new.semantic_tokens))

    def test_same_identity_changed_cost_condition_target_effect_are_known_hard_negatives(self):
        for card in T.REVIEWED_CARDS:
            original=T.capability(card,card["abilityPath"])
            for kind,changed in T.hard_negatives(card).items():
                with self.subTest(card=card["setCode"],negative=kind):
                    self.assertEqual(changed["setCode"],card["setCode"])
                    encoded=T.capability(changed,changed["abilityPath"])
                    self.assertTrue(encoded.known,encoded.reason)
                    self.assertNotEqual(encoded.semantic_tokens,original.semantic_tokens)

    def test_effect_sequence_order_is_semantic_and_changes_restricted_oracle(self):
        card=next(c for c in T.REVIEWED_CARDS if c["setCode"]=="SHD_002")
        forward=T.capability(card,card["abilityPath"])
        reverse=T.capability(T.hard_negatives(card)["sequence"],card["abilityPath"])
        state=T.fixture(card,0)[1]["state"]
        left=T.synthetic_transition(forward,state); right=T.synthetic_transition(reverse,state)
        self.assertNotEqual(forward.semantic_tokens,reverse.semantic_tokens)
        self.assertEqual((left["chosen"]["damage"],left["chosen"]["shield"]),(5,1))
        self.assertEqual((right["chosen"]["damage"],right["chosen"]["shield"]),(3,0))

    def test_explicit_binding_known_and_label_only_or_ambiguous_unknown(self):
        for i,card in enumerate(T.REVIEWED_CARDS):
            offered,context,binding=T.fixture(card,i)
            action=T.instantiate_action(offered,context,[binding])
            self.assertTrue(action.known,action.reason)
            self.assertEqual(action.semantic_tokens,T.capability(card,card["abilityPath"]).semantic_tokens)
            self.assertFalse(T.instantiate_action(offered,context,[]).known)
            self.assertFalse(T.instantiate_action(offered,context,[binding,binding]).known)
            mutated=copy.deepcopy(offered); mutated["method"]="guessed-ability-name"
            self.assertFalse(T.instantiate_action(mutated,context,[binding]).known)

    def test_physical_instance_alpha_renaming_preserves_action_features(self):
        offered,context,binding=T.fixture(T.REVIEWED_CARDS[0],0)
        original=T.instantiate_action(offered,context,[binding])
        renamed=copy.deepcopy(context); renamed.update(source_instance="c300",chosen_instance="c400")
        new_offered=copy.deepcopy(offered); new_offered["card"]="c400"
        new_binding=T.CuratedBinding("c300",binding.source_card,binding.ability_path,binding.stage,new_offered,binding.card)
        actual=T.instantiate_action(new_offered,renamed,[new_binding])
        self.assertTrue(actual.known)
        self.assertEqual(original.semantic_tokens,actual.semantic_tokens)
        self.assertEqual(original.role_tokens,actual.role_tokens)

    def test_wrong_source_form_card_and_target_domain_fail_closed(self):
        offered,context,binding=T.fixture(T.REVIEWED_CARDS[0],0)
        for key,value in (("source_form","unit"),("source_card","wrong")):
            bad=copy.deepcopy(context); bad[key]=value
            self.assertFalse(T.instantiate_action(offered,bad,[binding]).known)
        for zone in ("hand","deck","discard"):
            bad=copy.deepcopy(context); bad["state"]["chosen"]["zone"]=zone
            self.assertFalse(T.instantiate_action(offered,bad,[binding]).known)
        changed=copy.deepcopy(binding.card); changed["setCode"]="WRONG_001"
        bad_binding=T.CuratedBinding(binding.source_instance,binding.source_card,binding.ability_path,binding.stage,offered,changed)
        self.assertFalse(T.instantiate_action(offered,context,[bad_binding]).known)

    def test_unknown_operations_partial_fields_and_object_equality_are_not_erased(self):
        card=copy.deepcopy(T.REVIEWED_CARDS[0]); a=card["abilities"]["leader"][0]
        a["effect"]["kind"]="unreviewedGrantProgram"
        self.assertFalse(T.capability(card,card["abilityPath"]).known)
        card=copy.deepcopy(T.REVIEWED_CARDS[0]);card["abilities"]["leader"][0]["attachedContext"]="host"
        self.assertFalse(T.capability(card,card["abilityPath"]).known)
        with self.assertRaises(T.UnknownIR):
            T.expression({"kind":"binary","op":"===","left":{"kind":"ref","path":["source"]},"right":{"kind":"ref","path":["card"]}})
        with self.assertRaises(T.UnknownIR):
            T.expression({"kind":"binary","op":"&&","left":{"kind":"const","value":1},"right":{"kind":"const","value":True}})
        for remove in (True,False):
            card=copy.deepcopy(T.REVIEWED_CARDS[0]);a=card["abilities"]["leader"][0]
            if remove: del a["targetResolver"]
            else: a["targetResolver"]=None
            self.assertFalse(T.capability(card,card["abilityPath"]).known)

    def test_committed_primitive_oracle_cost_condition_target_and_followup_boundaries(self):
        for card in T.REVIEWED_CARDS:
            encoded=T.capability(card,card["abilityPath"]); state=T.fixture(card,0)[1]["state"]
            self.assertTrue(T.synthetic_affordance(encoded,state))
            after=T.synthetic_transition(encoded,state)
            self.assertTrue(after["source"]["exhausted"])
            self.assertFalse(T.synthetic_affordance(encoded,after))
            if any(c["kind"]=="resources"for c in encoded.program["costs"]):
                blocked=copy.deepcopy(state);blocked["ready_resources"]=0
                self.assertFalse(T.synthetic_affordance(encoded,blocked))
            if card["setCode"]=="ASH_011":
                blocked=copy.deepcopy(state);blocked["chosen"].update(hp=4,damage=3)
                self.assertFalse(T.synthetic_affordance(encoded,blocked))
            if card["setCode"]=="IBH_001":
                blocked=copy.deepcopy(state);blocked["chosen"]["owner"]="opponent"
                self.assertFalse(T.synthetic_affordance(encoded,blocked))

    def test_frozen_alignment_is_wiring_and_masks_incompatible_roles(self):
        card=T.REVIEWED_CARDS[1]; offered,context,binding=T.fixture(card,0)
        action=T.instantiate_action(offered,context,[binding])
        candidates=[T.capability(card,card["abilityPath"]),*[T.capability(c,c["abilityPath"])for c in T.hard_negatives(card).values()]]
        diagnostic=T.frozen_alignment(action,candidates,context["state"])
        self.assertTrue(diagnostic["positive_unique_best"])
        self.assertIn("no learned alignment",diagnostic["interpretation"])
        invalid=copy.deepcopy(context["state"]);invalid["chosen"]["owner"]="opponent"
        with self.assertRaises(T.UnknownIR): T.frozen_alignment(action,candidates,invalid)

    def test_selected_excerpts_match_pinned_catalog_without_partial_card_admission(self):
        path=T.PINNED_SOURCE/"compiler/generated/cards.json"
        if not path.exists(): self.skipTest("pinned local Kessel checkout unavailable")
        raw=json.loads(path.read_text())
        entries=raw if isinstance(raw,list)else raw["cards"]
        by_code={card["setCode"]:card for card in entries}
        for card in T.REVIEWED_CARDS:
            actual=by_code[card["setCode"]]
            self.assertEqual(actual["abilities"]["leader"][0],card["abilities"]["leader"][0])
            self.assertEqual(actual["sourceHash"],card["sourceHash"])
            self.assertEqual(actual["sourcePath"],card["sourcePath"])
        self.assertFalse(T.RUNTIME_ADMISSION["IBH_001"]["admitted"])
        self.assertFalse(T.RUNTIME_ADMISSION["SHD_002"]["admitted"])

    def test_structural_report_does_not_claim_training_or_learned_alignment(self):
        report=T.structural_report()
        self.assertEqual(report["optimizer_steps"],0)
        self.assertIsNone(report["learned_semantic_quality"])
        self.assertEqual(len(report["cards"]),4)
        for case in report["cards"]:
            self.assertTrue(case["hard_negatives_all_known"])
            self.assertIn("not Kessel execution",case["synthetic_oracle"]["scope"])

    def test_native_binding_rejects_unreviewed_receipt(self):
        with self.assertRaises(T.UnknownIR): T.native_binding_report({})

    def test_versioned_inspection_contract_has_no_production_tensor_width(self):
        known=T.encoding_record(T.capability(T.REVIEWED_CARDS[0],T.REVIEWED_CARDS[0]["abilityPath"]))
        unknown=T.encoding_record(T.Encoding(False,reason="ambiguous binding"))
        self.assertEqual(known["schema"],"jepa-typed-ir-wiring/1")
        self.assertEqual(known["status"],"known")
        self.assertEqual(known["coverage_status"],"selected-ability")
        self.assertIsNone(known["numeric_feature_width"])
        self.assertFalse(known["production_graph_integration"])
        self.assertEqual(unknown["semantic_tokens"],[])
        self.assertEqual(unknown["role_tokens"],[])
        self.assertEqual(unknown["status"],"unknown")
        json.dumps([known,unknown],allow_nan=False)

    def test_semantic_token_budget_rejects_without_truncation(self):
        card=copy.deepcopy(T.REVIEWED_CARDS[0])
        effect=card["abilities"]["leader"][0]["effect"]
        for _ in range(4): effect=dict(kind="sequence",effects=[copy.deepcopy(effect)for _ in range(4)])
        card["abilities"]["leader"][0]["effect"]=effect
        encoded=T.capability(card,card["abilityPath"])
        self.assertFalse(encoded.known)
        self.assertEqual(encoded.semantic_tokens,())
        self.assertIn("token budget",encoded.reason)

    def test_recorded_actual_native_binding_if_receipt_available(self):
        path=T.HERE/"typed-ir-verification.json"
        if not path.exists(): self.skipTest("verification receipt not generated")
        report=json.loads(path.read_text())
        receipt_path=report.get("native",{}).get("receipt_path")
        if receipt_path is None or not Path(receipt_path).exists(): self.skipTest("local raw native receipt unavailable")
        receipt=json.loads(Path(receipt_path).read_text())
        actual=T.native_binding_report(receipt)
        self.assertEqual(len(actual["rows"]),2)
        for case in actual["rows"]:
            self.assertTrue(case["binding_known"])
            self.assertTrue(case["restricted_oracle_matches_observed_scalar_projection"])
            self.assertEqual(case["observed"]["target_damage_delta"],1)
            self.assertTrue(case["observed"]["source_exhausted"])
            self.assertFalse(case["observed"]["followup_source_offered"])


if __name__=="__main__": unittest.main()
