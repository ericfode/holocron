"""Pure contract tests. Synthetic receipts here are not native evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import actual_corpus_native_plan as A
import grounded_contrast_data as G


class ActualCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        gen=G.PINNED_KESSEL/"compiler/generated"
        cls.catalog=G.assembled_catalog(gen);cls.rows={r["setCode"]:r for r in cls.catalog["cards"]}
        plain=json.loads((gen/"cards.json").read_text());runtime=json.loads((gen/"runtime-admission.json").read_text())
        decks=json.loads((A.HERE.parents[2]/"decks/ash-meta-2026-09.json").read_text())
        cls.plan=A.build_plan(plain,runtime,decks)

    def cap(self,code,context):
        codes=[code,A.HELPERS["ground"],A.HELPERS["cheap"],A.HELPERS["expensive"],A.HELPERS["nonunique"],A.HELPERS["unique"],A.HELPERS["base"],A.HELPERS["base"]]
        zones=["hand","ground","space","space","upgrade","upgrade","base","base"]
        refs={slot:f"c{i}" for i,slot in enumerate(A.CANDIDATES)};proj={}
        def ref(i,c):return dict(id=f"c{i}",setCode=c,name="fixture")
        for i,(slot,c,z) in enumerate(zip(A.CANDIDATES,codes,zones)):
            meta=self.rows[c]["card"];is_upgrade="upgrade" in meta["types"];power=meta.get("power");hp=meta.get("hp")
            physical_unit="unit" in meta["types"];damageable=physical_unit or "base" in meta["types"]
            known=dict(identity=True,owner=True,damage=damageable,exhausted=physical_unit,hp=hp is not None and damageable,power=power is not None and physical_unit,shield_count=physical_unit,xp_count=physical_unit)
            proj[slot]=dict(id=refs[slot],code=c,zone=z,owner="p2" if i in (2,3,5,7) else "p1",present=True,in_arena=z in ("ground","space"),attackable=z in ("ground","space","base"),is_unit="unit" in meta["types"],is_base="base" in meta["types"],damage=0,exhausted=context["exhausted"] if i in(1,2,3) else False,power=power if known["power"] else 0,hp=hp if known["hp"] else 0,shield_count=0,xp_count=0,known=known)
        p1=dict(base=ref(6,codes[6]),leader=ref(20,A.HELPERS["leader"]),hand=[ref(0,code)],deck=[],ground=[ref(1,codes[1])],space=[],discard=[],resources=[dict(id=f"c{30+i}",setCode=A.HELPERS["resource"],exhausted=i>=context["ready_resources"]) for i in range(8)])
        p2=dict(base=ref(7,codes[7]),leader=ref(21,A.HELPERS["leader"]),hand=[],deck=[],ground=[ref(22,A.HELPERS["host"])],space=[ref(2,codes[2]),ref(3,codes[3])],discard=[],resources=[])
        if context["other_space"] is not None:p1["space"].append(ref(23,A.HELPERS[context["other_space"]]))
        witness=dict(decision="Window",ability_program=0,death_depth=0,death_pending=0,death_window=0,pending_programs=0,pending_triggers=0,after_attack_triggers=0,after_attack_programs=0,event_group_active=False,support_pending=False)
        return dict(decision="Window",actor="p1",sourceInstance=None,abilityProgramPlusOne=0,settlement=witness,terminal=False,settled=True,
                    state=dict(players=dict(p1=p1,p2=p2)),projections=proj,offeredActions=[],other_friendly_space_count=len(p1["space"]),other_friendly_fighter_count=int(context["other_space"]=="other_fighter"),own_aspect_sources=dict(base=A.HELPERS["base"],leader=A.HELPERS["leader"])),refs

    def receipt(self):
        cases=[]
        for context in self.plan["contexts"]:
            for card in self.plan["cards"]:
                code=card["code"];before,refs=self.cap(code,context);witnesses=[]
                for slot,host in (("nonunique_upgrade",refs["friendly_ground"]),("unique_upgrade","c22")):
                    q=copy.deepcopy(before);q.update(decision="UpgradeTarget",sourceInstance=refs[slot],settled=False);q["settlement"]["decision"]="UpgradeTarget"
                    offer=dict(kind="card",card=host,label="fixture");q["offeredActions"]=[offer]
                    witnesses.append(dict(upgrade=refs[slot],host=host,publicTargetQuery=q,offeredHost=offer))
                cases.append(dict(card=code,state_family=context["id"],identity_partition=card["partition"],state_partition=context["partition"],refs=refs,chosen_ref=A.selected_ref(code,context),before=before,publicSnapshotRoundtripExact=True,attachmentTargetWitnesses=witnesses,playAction=None,steps=[],targetPrompt=None,targetAction=None,final=None,engineError=None,completion="play-unavailable",applyCalls=0))
        return dict(schema="jepa-actual-corpus-native/1",sourceRevision=G.REVISION,collectionPlan=self.plan,candidateOrder=list(A.CANDIDATES),selectedWholeCards=self.plan["selected_whole_cards"],selectedCatalogueSha256=G.native_catalog_hash(self.catalog,self.plan["selected_whole_cards"]),cases=cases,applyCalls=0)

    def test_actual_source_counts_complete_scope_and_split(self):
        p=self.plan
        self.assertEqual((len(p["cards"]),p["expected_cases"],p["coverage"]["declared_source_copies"]),(8,32,65))
        self.assertEqual(set(p["split"]["heldout_codes"]),{"LOF_155","JTL_217"})
        self.assertEqual((len(A.CONTEXT_FEATURES),len(A.CANDIDATE_FEATURES),len(A.SOURCE_HEADS),len(A.TARGET_HEADS)),(18,34,9,7))
        self.assertEqual(self.rows[p["helpers"]["ground"]]["card"]["traits"],["force","jedi","wookiee"])
        for c in p["cards"]:self.assertEqual(c["raw_card"]["abilities"],self.rows[c["code"]]["abilities"])
        self.assertEqual(p["collector_max_engine_applies"],256)
        self.assertEqual(p["campaign_max_seconds"],90)
        self.assertIn("shielded",next(c for c in p["cards"] if c["code"]=="ASH_048")["raw_card"]["card"]["keywords"])

    def test_base_event_upgrade_unknown_stats_are_finite(self):
        b,refs=self.cap("LOF_077",A.contexts()[0])
        for slot in ("source","unique_upgrade","own_base"):
            v=np.asarray(A.candidate_vector(b["projections"][slot],refs["source"],self.rows),np.float32)
            self.assertTrue(np.isfinite(v).all());self.assertEqual(v.shape,(34,))
        base=A.candidate_vector(b["projections"]["own_base"],refs["source"],self.rows)
        self.assertEqual(base[26:28],[0,0])
        event=A.candidate_vector(b["projections"]["source"],refs["source"],self.rows)
        self.assertEqual((event[16],event[18]),(0,0))
        upgrade=A.candidate_vector(b["projections"]["unique_upgrade"],refs["source"],self.rows)
        self.assertEqual((upgrade[16],upgrade[18]),(0,0))

    def test_dense_unknowns_and_public_intent_not_native_labels(self):
        r=self.receipt();a,m=A.convert_receipt(r,self.plan,self.catalog)
        self.assertEqual(a["context_features"].shape,(32,18));self.assertEqual(a["candidate_features"].shape,(32,8,34))
        self.assertEqual(a["source_targets"].shape,(32,9));self.assertEqual(a["targets"].shape,(32,8,7))
        self.assertEqual([len(a[k+"_idx"]) for k in ("train","program_held","state_held","joint")],[18,6,6,2])
        self.assertEqual(int(a["target_mask"].sum()),0);self.assertEqual(int(a["source_mask"].sum()),32)
        self.assertFalse(m["every_source_has_funded_successful_play"])
        for i,c in enumerate(m["records"]):self.assertEqual(a["selected_candidate_indices"][i],A.CANDIDATES.index(A.selected_ref(c["card"],self.plan["contexts"][c["state_family"]])))

    def test_fail_closed_source_intent_settlement_private_and_attachment(self):
        for mutation in ("intent","private","attachment","settlement","quota"):
            r=self.receipt();c=r["cases"][0]
            if mutation=="intent":c["chosen_ref"]="unique_upgrade"
            elif mutation=="private":c["before"]["state"]["players"]["p2"]["hand"]=[dict(id="private")]
            elif mutation=="attachment":c["attachmentTargetWitnesses"][0]["offeredHost"]["card"]="wrong"
            elif mutation=="settlement":c["before"]["settled"]=False
            else:c["applyCalls"]=9
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):A.convert_receipt(r,self.plan,self.catalog)

    def test_declined_unit_trigger_retains_paid_entry_and_unknown_target_future(self):
        r=self.receipt();c=next(c for c in r["cases"] if c["card"]=="LOF_155" and c["state_family"]==2)
        play=dict(kind="card",card=c["refs"]["source"],label="play");c["before"]["offeredActions"]=[play];c["playAction"]=play
        prompt=copy.deepcopy(c["before"]);prompt.update(decision="AbilityTarget",sourceInstance=c["refs"]["source"],abilityProgramPlusOne=1,settled=False)
        prompt["settlement"].update(decision="AbilityTarget",ability_program=1)
        prompt["projections"]["source"].update(zone="ground",in_arena=True,attackable=True,exhausted=True)
        card=prompt["state"]["players"]["p1"]["hand"].pop();prompt["state"]["players"]["p1"]["ground"].append(card)
        for resource in prompt["state"]["players"]["p1"]["resources"][:2]:resource["exhausted"]=True
        decline=dict(kind="button",arg="passAbility",label="Pass");prompt["offeredActions"]=[decline]
        final=copy.deepcopy(prompt);final.update(decision="Window",abilityProgramPlusOne=0,settled=True);final["settlement"].update(decision="Window",ability_program=0);final["offeredActions"]=[]
        c.update(targetPrompt=prompt,steps=[dict(stage="play-own-hand",before=c["before"],action=play,after=prompt),dict(stage="decline-unoffered-target",before=prompt,action=decline,after=final)],final=final,completion="settled",applyCalls=2)
        r["applyCalls"]=2;a,m=A.convert_receipt(r,self.plan,self.catalog);i=next(i for i,v in enumerate(m["records"]) if v["card"]=="LOF_155" and v["state_family"]==2)
        self.assertEqual((a["source_targets"][i,1],a["source_targets"][i,2],a["source_targets"][i,3]),(1,2,1))
        self.assertEqual(int(a["target_mask"][i,:,0].sum()),8);self.assertEqual(int(a["target_mask"][i,:,1:].sum()),0)


if __name__=="__main__":unittest.main()
