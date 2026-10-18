"""Synthetic saved-data contract tests; no engine or model calls."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_effect_v2_data as D


class NativeEffectDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = D.G.assembled_catalog(D.G.PINNED_KESSEL / "compiler/generated")
        cls.rows = {r["setCode"]: r for r in cls.catalog["cards"]}
        selected = sorted(set(D.P.CODES) | set(D.P.HELPERS.values()) | {"TOKEN_SHIELD", "TOKEN_EXPERIENCE"})
        cls.plan = dict(cards=[dict(code=c, partition="train" if c in D.P.TRAIN else "heldout", family=D.P.FAMILIES[c], raw_card=cls.rows[c]) for c in D.P.CODES],
                        contexts=D.P.contexts(), helpers=D.P.HELPERS, selected_whole_cards=selected,
                        selected_whole_rows={c:cls.rows[c] for c in selected}, candidate_order=list(D.P.CANDIDATES),
                        query_specs={c:[D.P.query_spec(c,f) for f in range(4)] for c in D.P.CODES},
                        collector_max_engine_applies=240,max_applies_per_case=5,
                        context_feature_names=list(D.P.CONTEXT_FEATURES),candidate_feature_names=list(D.P.CANDIDATE_FEATURES),source_head_names=list(D.P.SOURCE_HEADS),source_binary_heads=list(D.P.SOURCE_BINARY),target_names=list(D.P.TARGET_HEADS),binary_heads=list(D.P.TARGET_BINARY),
                        split=dict(train_codes=list(D.P.TRAIN),heldout_codes=list(D.P.HELD)))

    def cap(self, code, world):
        refs = {s:f"c{i}" for i,s in enumerate(D.P.CANDIDATES)}
        cs = [code,D.P.HELPERS["ground"],world["small"]["code"],world["large"]["code"],D.P.HELPERS["nonunique"],D.P.HELPERS["unique"],D.P.HELPERS["base"],D.P.HELPERS["base"]]
        zones = ["hand","ground","space","space","upgrade","upgrade","base","base"]
        owners = ["p1","p1",world["small"]["owner"],world["large"]["owner"],"p1","p2","p1","p2"]
        projections = {}
        for i,slot in enumerate(D.P.CANDIDATES):
            m=self.rows[cs[i]]["card"];unit="unit" in m["types"];base="base" in m["types"]
            known=dict(identity=True,owner=True,damage=unit or base,hp=(unit or base) and m.get("hp") is not None,power=unit and m.get("power") is not None,exhausted=unit,shield_count=unit,xp_count=unit)
            projections[slot]=dict(id=refs[slot],code=cs[i],zone=zones[i],owner=owners[i],present=True,in_arena=zones[i] in ("ground","space"),attackable=zones[i] in ("ground","space","base"),is_unit=unit,is_base=base,
                                   damage=0,hp=m.get("hp",0) if known["hp"] else 0,power=m.get("power",0) if known["power"] else 0,exhausted=False,shield_count=0,xp_count=0,known=known)
        def wire(i):
            p=projections[D.P.CANDIDATES[i]]
            return dict(id=p["id"],setCode=p["code"],damage=p["damage"],hp=p["hp"],power=p["power"],exhausted=p["exhausted"],upgrades=[])
        players={s:dict(base=wire(6 if s=="p1" else 7),leader=dict(id=s+"leader",setCode=D.P.HELPERS["leader"]),hand=[wire(0)] if s=="p1" else [],deck=[],ground=[],space=[],discard=[],resources=[]) for s in ("p1","p2")}
        players["p1"]["ground"].append(wire(1))
        for i in (2,3):players[owners[i]]["space"].append(wire(i))
        host=dict(id="enemy-host",setCode=D.P.HELPERS["host"],damage=0,hp=self.rows[D.P.HELPERS["host"]]["card"]["hp"],power=2,exhausted=False,upgrades=[])
        players["p2"]["ground"].append(host)
        for slot,host in (("nonunique_upgrade",players["p1"]["ground"][0]),("unique_upgrade",host)):
            p=projections[slot];meta=self.rows[p["code"]]["card"]
            host["upgrades"].append(dict(id=p["id"],setCode=p["code"],token=False,owner=p["owner"],controller=p["owner"]))
            host["hp"]+=meta.get("upgradeHp",0) or 0;host["power"]+=meta.get("upgradePower",0) or 0
            if slot=="nonunique_upgrade":projections["friendly_ground"].update(hp=host["hp"],power=host["power"])
        shields=[]
        for slot,name in (("friendly_ground","ground"),("space_small","small"),("space_large","large")):
            p=projections[slot];p.update(damage=world[name]["damage"],exhausted=world[name]["exhausted"],shield_count=world[name]["shield"])
            unit=next(u for _,u in [(s,u)for s in players for z in ("ground","space")for u in players[s][z]]if u["id"]==p["id"])
            unit.update(damage=p["damage"],exhausted=p["exhausted"])
            if p["shield_count"]:
                token="shield-"+slot;unit["upgrades"].append(dict(id=token,setCode="TOKEN_SHIELD",token=True))
                shields.append(dict(token=token,code="TOKEN_SHIELD",owner=p["owner"],parent=p["id"],sourceHash=self.rows["TOKEN_SHIELD"]["sourceHash"]))
        players["p1"]["resources"]=[dict(id=f"res{i}",setCode=D.P.HELPERS["resource"],exhausted=False)for i in range(12)]
        settlement=dict(decision="Window",ability_program=0,death_depth=0,death_pending=0,death_window=0,pending_programs=0,pending_triggers=0,after_attack_triggers=0,after_attack_programs=0,event_group_active=False,support_pending=False)
        ownspace=players["p1"]["space"]
        cap=dict(decision="Window",actor="p1",sourceInstance=None,abilityProgramPlusOne=0,settlement=settlement,terminal=False,settled=True,state=dict(players=players),projections=projections,offeredActions=[],
                 other_friendly_space_count=len(ownspace),other_friendly_fighter_count=sum("fighter" in self.rows[u["setCode"]]["card"]["traits"] for u in players["p1"]["ground"]+ownspace),own_aspect_sources=dict(base=D.P.HELPERS["base"],leader=D.P.HELPERS["leader"]))
        return cap,refs,shields

    def receipt(self):
        cases=[]
        for world in self.plan["contexts"]:
            for card in self.plan["cards"]:
                code=card["code"];b,refs,shields=self.cap(code,world);witnesses=[]
                for slot,host in (("nonunique_upgrade",refs["friendly_ground"]),("unique_upgrade","enemy-host")):
                    q=copy.deepcopy(b);q.update(decision="UpgradeTarget",sourceInstance=refs[slot],settled=False);q["settlement"]["decision"]="UpgradeTarget"
                    action=dict(kind="card",card=host,label="attach");q["offeredActions"]=[action]
                    witnesses.append(dict(upgrade=refs[slot],host=host,publicTargetQuery=q,offeredHost=action))
                spec=D.query(self.plan,code,world["id"])
                cases.append(dict(card=code,state_family=world["id"],identity_partition=card["partition"],state_partition=world["partition"],refs=refs,chosen_ref=spec["ref"],observation_mode=spec["mode"],before=b,publicSnapshotRoundtripExact=True,attachmentTargetWitnesses=witnesses,shieldFixtureWitnesses=shields,playAction=None,steps=[],targetPrompt=None,targetAction=None,final=None,engineError=None,completion="play-unavailable",applyCalls=0))
        return dict(schema="jepa-native-effect-v2/1",sourceRevision=D.G.REVISION,collectionPlan=self.plan,collectionPlanSha256="fixture-plan-sha",candidateOrder=list(D.P.CANDIDATES),selectedWholeCards=self.plan["selected_whole_cards"],selectedCatalogueSha256=D.G.native_catalog_hash(self.catalog,self.plan["selected_whole_cards"]),cases=cases,applyCalls=0)

    def journal(self,r):
        result=[dict(schema="native-effect-v2-apply-journal/1",sourceRevision=D.G.REVISION,selectedWholeCards=r["selectedWholeCards"],planSha256=r["collectionPlanSha256"])]
        n=0
        for c in r["cases"]:
            context=f'{c["card"]}-family-{c["state_family"]}'
            for step in c["steps"]:
                n+=1;result.extend([dict(phase="beforeApply",applyCall=n,context=context,branch=step["stage"],before=step["before"],offeredAction=step["action"]),dict(phase="afterApply",applyCall=n,context=context,branch=step["stage"],after=step["after"])])
            if c["engineError"] is not None:
                n+=1;last=c["steps"][-1]["after"] if c["steps"] else c["before"]
                action=c["targetAction"] if c["targetAction"] is not None else c["playAction"]
                stage="chosen-target" if c["targetAction"] is not None else "play-own-hand"
                result.extend([dict(phase="beforeApply",applyCall=n,context=context,branch=stage,before=last,offeredAction=action),dict(phase="applyError",applyCall=n,context=context,branch=stage,error=c["engineError"])])
            result.append(dict(phase="contextComplete",context=context,case=c))
        r["applyCalls"]=n
        return result

    def convert(self,r):return D.convert_receipt(r,self.plan,self.catalog,self.journal(r))

    def play(self,r,code,family=0,decline=False,pending=False,dead=False):
        c=next(c for c in r["cases"]if c["card"]==code and c["state_family"]==family)
        b=c["before"];refs=c["refs"];mode=c["observation_mode"];slot=c["chosen_ref"]
        action=dict(kind="card",card=refs["source"],label="play");b["offeredActions"]=[action];c["playAction"]=action
        entered=copy.deepcopy(b);source=entered["projections"]["source"];wire=entered["state"]["players"]["p1"]["hand"].pop()
        if mode!="upgrade-attachment":
            source.update(zone="ground",in_arena=True,attackable=True,exhausted=True)
            wire.update(exhausted=True);entered["state"]["players"]["p1"]["ground"].append(wire)
            for card in entered["state"]["players"]["p1"]["resources"][:2]:card["exhausted"]=True
        if mode in ("chosen-target","upgrade-attachment"):
            prompt=entered;decision="UpgradeTarget"if mode=="upgrade-attachment"else"AbilityTarget"
            prompt.update(decision=decision,settled=False,abilityProgramPlusOne=1,sourceInstance=refs["source"]);prompt["settlement"].update(decision=decision,ability_program=1)
            target=dict(kind="card",card=refs[slot],label="target");cancel=dict(kind="button",arg="passAbility",label="Pass")
            prompt["offeredActions"]=[cancel]if decline else[target]
            c["targetPrompt"]=prompt;c["steps"]=[dict(stage="play-own-hand",before=b,action=action,after=prompt)]
            if pending:
                c.update(lastObserved=prompt,completion="pending",applyCalls=1);return c
            final=copy.deepcopy(prompt);final.update(decision="Window",settled=True,abilityProgramPlusOne=0);final["settlement"].update(decision="Window",ability_program=0);final["offeredActions"]=[]
            if decline:stage,chosen="decline-unoffered-target",cancel
            else:
                stage="attach-intended-host"if mode=="upgrade-attachment"else"chosen-target";chosen=target;c["targetAction"]=chosen
                host=next(u for _,u in D.units(final)if u["id"]==refs[slot]);p=final["projections"][slot]
                if mode=="upgrade-attachment":
                    final["state"]["players"]["p1"]["resources"][0]["exhausted"]=True
                    final["projections"]["source"].update(zone="upgrade",in_arena=False)
                    host["upgrades"].append(dict(id=refs["source"],setCode=code,token=False,owner="p1",controller="p1"))
                    host["hp"]+=2;host["power"]+=3;p["hp"]+=2;p["power"]+=3
                elif dead:
                    final["state"]["players"][p["owner"]][p["zone"]].remove(host);final["state"]["players"][p["owner"]]["discard"].append(host)
                    p.update(zone="discard",in_arena=False)
                else:p["damage"]+=1;host["damage"]+=1
            c["steps"].append(dict(stage=stage,before=prompt,action=chosen,after=final))
        else:
            final=entered
            if mode=="self-entry":
                unit=next(u for _,u in D.units(final)if u["id"]==refs["source"])
                unit["upgrades"].append(dict(id="entry-shield",setCode="TOKEN_SHIELD",token=True));source["shield_count"]=1
            else:
                for _,u in D.units(final,"p2"):
                    u["hp"]-=3;u["power"]-=3
                    for p in final["projections"].values():
                        if p["id"]==u["id"]:p["hp"]-=3;p["power"]-=3
            c["steps"]=[dict(stage="play-own-hand",before=b,action=action,after=final)]
        c.update(final=final,lastObserved=final,completion="settled",applyCalls=len(c["steps"]),chosenTargetCommitted=not decline and mode in("chosen-target","upgrade-attachment"))
        return c

    def index(self,m,code,family=0):return next(i for i,c in enumerate(m["records"])if c["card"]==code and c["state_family"]==family)

    def test_fixed_shapes_unknown_unavailable_and_sparse_split(self):
        a,m=self.convert(self.receipt())
        self.assertEqual(a["context_features"].shape,(48,18));self.assertEqual(a["candidate_features"].shape,(48,8,34))
        self.assertEqual([len(a[k+"_idx"])for k in("train","program_held","state_held","joint")],[21,15,7,5])
        self.assertEqual(a["source_mask"].sum(),48);self.assertEqual(a["target_mask"].sum(),0)
        np.testing.assert_array_equal(a["sparse_source_mask"],a["source_mask"])

    def test_all_four_observation_modes_require_real_binding(self):
        r=self.receipt()
        for code in ("SEC_142","LOF_151","ASH_048","SEC_051"):self.play(r,code)
        a,m=self.convert(r)
        chosen=self.index(m,"SEC_142");attach=self.index(m,"LOF_151");entry=self.index(m,"ASH_048");area=self.index(m,"SEC_051")
        self.assertEqual(a["targets"][chosen,1,2],1)
        np.testing.assert_array_equal(a["targets"][attach,1,5:7],[3,2]);self.assertEqual(a["source_targets"][attach,1],1)
        self.assertEqual(a["source_targets"][entry,7],1);self.assertEqual(a["target_mask"][entry,:,2:].sum(),0)
        np.testing.assert_array_equal(a["targets"][area,2,5:7],[-3,-3]);self.assertEqual(a["target_mask"][area,:,0].sum(),0)
        self.assertEqual(m["head_support"]["SEC_051"]["target_hp_delta"]["negative"],1)
        self.assertEqual(m["head_support"]["train"]["target_hp_delta"]["negative_roots"],1)
        self.assertEqual(a["sparse_target_mask"][a["train_idx"],:,2:7].sum(),0)
        np.testing.assert_array_equal(a["sparse_target_mask"][:,:,0:2],a["target_mask"][:,:,0:2])
        np.testing.assert_array_equal(a["sparse_target_mask"][a["joint_idx"]],a["target_mask"][a["joint_idx"]])

    def test_declined_and_pending_target_futures_unknown(self):
        for pending in (False,True):
            r=self.receipt();self.play(r,"SEC_142",decline=not pending,pending=pending)
            a,m=self.convert(r);i=self.index(m,"SEC_142")
            self.assertEqual(a["target_mask"][i,:,1:].sum(),0)
            self.assertEqual(a["target_mask"][i,:,0].sum(),8)
            if pending:
                self.assertEqual(a["source_mask"][i,1:].sum(),0)
                self.assertEqual(m["fit_blockers"],["pending-native-outcomes"])

    def test_native_errors_are_preserved_unknown_and_block_planned_fit(self):
        for failed_target in (False,True):
            r=self.receipt();c=next(c for c in r["cases"]if c["card"]=="SEC_142" and c["state_family"]==0)
            if failed_target:
                c=self.play(r,"SEC_142",pending=True);c["targetAction"]=c["targetPrompt"]["offeredActions"][0];c["chosenTargetCommitted"]=True
            else:
                action=dict(kind="card",card=c["refs"]["source"],label="play");c["before"]["offeredActions"]=[action];c["playAction"]=action
            c.update(engineError="NATIVE_APPLY_ERROR: synthetic",completion="native-error",applyCalls=len(c["steps"])+1)
            a,m=self.convert(r);i=self.index(m,"SEC_142")
            self.assertEqual(a["source_mask"][i,1:].sum(),0);self.assertEqual(a["target_mask"][i,:,1:].sum(),0)
            self.assertEqual(m["native_engine_error_roots"],1);self.assertFalse(m["planned_settlement_precheck_passed"])
            self.assertEqual(m["fit_blockers"],["native-engine-errors"])

    def test_dead_target_numeric_unknown_and_jtl079_survival_enforced(self):
        r=self.receipt();self.play(r,"SEC_142",dead=True);a,m=self.convert(r);i=self.index(m,"SEC_142")
        self.assertEqual(a["targets"][i,1,1],1);self.assertEqual(a["target_mask"][i,:,2:].sum(),0)
        r=self.receipt();self.play(r,"JTL_079",dead=True)
        with self.assertRaisesRegex(ValueError,"survival"):self.convert(r)

    def test_private_inputs_physical_shields_and_source_intent_rejected(self):
        for fault in ("privacy","shield","intent","binding"):
            r=self.receipt();c=next(c for c in r["cases"]if c["state_family"]==1)
            if fault=="privacy":c["before"]["state"]["players"]["p2"]["hand"]=[dict(id="private")]
            elif fault=="shield":c["before"]["state"]["players"]["p1"]["ground"][0]["upgrades"]=[u for u in c["before"]["state"]["players"]["p1"]["ground"][0]["upgrades"]if u["setCode"]!="TOKEN_SHIELD"]
            elif fault=="intent":c["chosen_ref"]="opponent_base"
            else:
                c=self.play(r,"LOF_151");c["final"]["state"]["players"]["p1"]["ground"][0]["upgrades"]=[u for u in c["final"]["state"]["players"]["p1"]["ground"][0]["upgrades"]if u["id"]!=c["refs"]["source"]]
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.convert(r)

    def test_sec051_no_enemy_death_or_experience_hook(self):
        for fault in ("death","xp"):
            r=self.receipt();c=self.play(r,"SEC_051");f=c["final"]
            if fault=="death":f["state"]["players"]["p2"]["space"].pop()
            else:f["state"]["players"]["p1"]["ground"][0]["upgrades"].append(dict(id="xp",setCode="TOKEN_EXPERIENCE",token=True))
            with self.subTest(fault=fault),self.assertRaisesRegex(ValueError,"SEC051"):self.convert(r)

    def test_journal_boundaries_and_actual_mode_binding_fail_closed(self):
        r=self.receipt();self.play(r,"SEC_142");j=self.journal(r)
        broken=copy.deepcopy(j);next(x for x in broken if x.get("phase")=="beforeApply")["applyCall"]=2
        with self.assertRaisesRegex(ValueError,"durable"):D.convert_receipt(r,self.plan,self.catalog,broken)
        with self.assertRaisesRegex(ValueError,"journal required"):D.convert_receipt(r,self.plan,self.catalog,None)
        r=self.receipt();c=self.play(r,"SEC_142");c["steps"][1]["stage"]="attach-intended-host"
        with self.assertRaisesRegex(ValueError,"binding"):self.convert(r)


if __name__ == "__main__":unittest.main()
