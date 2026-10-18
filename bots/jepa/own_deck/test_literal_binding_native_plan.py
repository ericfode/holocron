"""Preparation and fail-closed receipt tests; no native or neural execution."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import literal_binding_native_plan as L


class LiteralBindingPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gen=L.G.PINNED_KESSEL/"compiler/generated"
        cls.catalog=L.G.assembled_catalog(gen)
        cls.plan=L.build_plan(json.loads((gen/"cards.json").read_text()),json.loads((gen/"runtime-admission.json").read_text()),
            json.loads((L.ROOT/"grounded-contrast/core-programs.json").read_text()),json.loads((L.ROOT/"transition-replication/core-programs.json").read_text()))
        cls.old=json.loads((L.ROOT/"transition-replication/attempt-1/native-receipt.json").read_text())

    def test_sixteen_roots_threshold4_costs_and_xp_ready_factorial(self):
        p=self.plan
        self.assertEqual((p["expected_cases"],len(p["contexts"]),len(p["programs"])),(16,8,2))
        self.assertEqual({(c["chosen_xp"],c["overrides"][L.CHOSEN]["exhausted"]) for c in p["contexts"][:4]}, {(0,False),(0,True),(1,False),(1,True)})
        self.assertEqual([p["contexts"][i]["chosen_code"] for i in (4,5)],["LOF_084","SEC_167"])
        self.assertEqual([p["contexts"][i]["ready_resources"] for i in (0,6,7)],[2,0,1])
        self.assertEqual((p["collector_max_engine_applies"],p["campaign_max_seconds"],p["max_rss_bytes"],p["optimizer_updates"]),(80,60,1073741824,0))
        self.assertEqual(p["independent_new_card_gate"]["status"],"UNSUPPORTED_NO_TWO_ADMITTED_PROGRAM_INPUT_PAIRS")

    def test_power4_and5_features_differ_only_in_power(self):
        rows={r["setCode"]:r for r in self.catalog["cards"]}
        def projection(code):
            c=rows[code]["card"]
            return dict(id="target",code=code,owner="p1",is_unit=True,is_base=False,zone="ground",present=True,damage=0,hp=c["hp"],power=c["power"],exhausted=False,shield_count=0,xp_count=0,
                        known={k:True for k in ("damage","hp","power","exhausted","shield_count","xp_count")})
        a=L.G.candidate_vector(projection("LOF_084"),"source",rows);b=L.G.candidate_vector(projection("SEC_167"),"source",rows)
        self.assertEqual(np.flatnonzero(a!=b).tolist(),[11])
        self.assertEqual((a[11],b[11]),(4,5))

    def test_program_scope_does_not_turn_leaders_into_main_or_all_abilities(self):
        p=self.plan["published12_vector_scope"]
        self.assertEqual((p["vectors"],p["leader_vectors"],p["main_unit_vectors"],p["total_declared_abilities"]),(12,5,7,17))
        self.assertFalse(p["whole_card_semantics"])
        self.assertFalse(p["whole_deck_card_coverage"])
        self.assertEqual(sum(r["additional_unencoded_abilities"] for r in p["rows"]),5)

    def synthetic_receipt(self):
        """Synthetic contract data is never published as native evidence."""
        p=self.plan;rows={r["setCode"]:r for r in self.catalog["cards"]};cases=[]
        for context in p["contexts"]:
            for program in p["programs"]:
                case=copy.deepcopy(next(c for c in self.old["cases"] if c["card"]==program["code"] and c["context_family"]==0))
                case.update(context_family=context["id"],source_use=False,source_use_known=True,sourceAction=None,sourceOpened=None,postActivation=None,menuAction=None,targetPrompt=None,cancelAction=None,cancelled=None,publicSnapshotRoundtripExact=True)
                case["before"]["offeredActions"]=[]
                for i,resource in enumerate(case["before"]["state"]["players"]["p1"]["resources"]):resource["exhausted"]=i>=context["ready_resources"]
                q=case["before"]["projections"][L.CHOSEN];c=rows[context["chosen_code"]]["card"]
                q.update(code=context["chosen_code"],power=c["power"]+context["chosen_xp"],hp=c["hp"]+context["chosen_xp"],xp_count=context["chosen_xp"],exhausted=context["overrides"].get(L.CHOSEN,{}).get("exhausted",False))
                case["queries"]=[dict(chosen_ref=slot,chosen_id=case["refs"][slot],targetAction=None,after=None,followupPass=None,following=None,engineError=None,
                                      targets={n:0 for n in L.G.TARGETS},target_mask={n:n=="source_use" for n in L.G.TARGETS}) for slot in L.G.CANDIDATES]
                cases.append(case)
        return dict(schema=L.SCHEMA,sourceRevision=L.G.REVISION,collectionPlan=p,selectedWholeCards=p["selected_whole_cards"],selectedCatalogueSha256=L.G.native_catalog_hash(self.catalog,p["selected_whole_cards"]),applyCalls=0,
                    provenance=[dict(card=r["code"],sourceHash=r["source_hash"],sourcePath=r["source_path"],abilityPath=["abilities",r["side"],r["index"]],actualUnmodifiedAbility=r["raw_ability"]) for r in p["programs"]],cases=cases)

    def test_dense_conversion_preserves_unknown_unchosen_transitions(self):
        arrays,manifest=L.convert_receipt(self.synthetic_receipt(),self.plan,self.catalog)
        self.assertEqual(arrays["candidate_features"].shape,(16,8,26))
        self.assertEqual(arrays["context_features"].shape,(16,2))
        self.assertEqual(arrays["source_use_mask"].sum(),16)
        self.assertEqual(arrays["candidate_allowed_mask"].sum(),0)
        self.assertEqual(arrays["target_mask"].sum(),0)
        self.assertEqual(len(manifest["programs"]),2)

    def test_settlement_source_fixture_provenance_and_unchosen_labels_fail_closed(self):
        for kind in ("unsettled","source","fixture","xp","provenance","unchosen","missing"):
            r=self.synthetic_receipt();c=r["cases"][0]
            if kind=="unsettled":c["before"]["settled"]=False;c["before"]["settlement"]["pending_programs"]=1
            elif kind=="source":c["source_use"]=True
            elif kind=="fixture":c["before"]["projections"][L.CHOSEN]["power"]+=1
            elif kind=="xp":c["before"]["projections"][L.CHOSEN]["xp_count"]+=1
            elif kind=="provenance":r["provenance"][0]["actualUnmodifiedAbility"]={}
            elif kind=="unchosen":c["queries"][0]["target_mask"]["cost_resource"]=True
            else:r["cases"].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):L.convert_receipt(r,self.plan,self.catalog)

    def test_freshness_uses_local_inputs_not_other_candidate_changes(self):
        a,_=L.convert_receipt(self.synthetic_receipt(),self.plan,self.catalog)
        programs={r["code"]:r for r in self.plan["programs"]};manifest=dict(programs=programs)
        prior={k:v.copy() for k,v in a.items()};info=L.input_novelty(a,programs,[(prior,manifest)])
        self.assertEqual((info["source_roots_new"],info["selected_candidate_new"]),(0,0))
        a["candidate_features"][0,4,11]+=1
        info=L.input_novelty(a,programs,[(prior,manifest)])
        self.assertEqual((info["source_roots_new"],info["selected_candidate_new"]),(0,0))
        self.assertFalse(a["candidate_input_is_prior_replay"][0,4])
        self.assertTrue(a["candidate_input_is_prior_replay"][0,2])
        a["context_features"][0,0]+=1
        info=L.input_novelty(a,programs,[(prior,manifest)])
        self.assertEqual((info["source_roots_new"],info["selected_candidate_new"]),(1,1))


if __name__=="__main__":unittest.main()
