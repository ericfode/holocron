"""Actual 27-list cards, complete definitions, bounded native play consequences.

Preparation/conversion only; never build an engine, run a network or fit weights.
The runtime admission report is not a game-conformance certificate. Native
fixtures qualify only the observed play/entry/selected-trigger paths.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grounded_contrast_data as G

ROOT = HERE.parents[3] / "experiments" / "actual-corpus"
SOURCE_CODES = ("ASH_048", "JTL_095", "SEC_163", "LOF_077", "JTL_078", "JTL_158", "LOF_155", "JTL_217")
HELD_CODES = ("LOF_155", "JTL_217")
CANDIDATES = ("source", "friendly_ground", "enemy_vehicle_cheap", "enemy_vehicle_expensive",
              "nonunique_upgrade", "unique_upgrade", "own_base", "opponent_base")
ASPECTS = ("vigilance", "command", "aggression", "cunning", "heroism", "villainy")
CONTEXT_FEATURES = ("ready_resources", "source_in_hand", *["own_aspect_" + a for a in ASPECTS],
                    "other_friendly_space_count", "other_friendly_fighter_count", "source_power", "source_hp",
                    "source_damage", "source_exhausted", "known_source_power", "known_source_hp", "known_source_damage", "known_source_exhausted")
CANDIDATE_FEATURES = (*G.CANDIDATE_FEATURES, "printed_cost", "known_printed_cost", "unique", "known_unique",
                      "is_upgrade", "is_leader", "trait_vehicle", "trait_fighter")
SOURCE_HEADS = ("play_available", "play_committed", "cost_resource", "source_in_arena", "source_in_discard",
                "source_in_hand_after", "source_damage_delta", "source_shield_delta", "source_exhausted_after")
SOURCE_BINARY = ("play_available", "play_committed", "source_in_arena", "source_in_discard", "source_in_hand_after", "source_exhausted_after")
TARGET_HEADS = ("target_allowed", "target_removed", "target_damage_delta", "target_exhausted_delta", "target_shield_delta", "target_power_delta", "target_hp_delta")
TARGET_BINARY = ("target_allowed", "target_removed")
HELPERS = dict(base="ASH_019", leader="IBH_053", ground="LOF_093", host="LOF_093", cheap="TWI_253", expensive="TWI_111",
               nonunique="LOF_151", unique="ASH_066", other_fighter="TWI_253", other_nonfighter="SHD_060", resource="LOF_256")


def contexts():
    return [dict(id=0, name="funded-no-other-space", partition="train", ready_resources=8, other_space=None, exhausted=False,
                 upgrade_choice="nonunique_upgrade", unit_choice="enemy_vehicle_cheap"),
            dict(id=1, name="unfunded-no-other-space", partition="train", ready_resources=0, other_space=None, exhausted=False,
                 upgrade_choice="nonunique_upgrade", unit_choice="enemy_vehicle_cheap"),
            dict(id=2, name="funded-other-fighter-expensive-unique", partition="train", ready_resources=8, other_space="other_fighter", exhausted=True,
                 upgrade_choice="unique_upgrade", unit_choice="enemy_vehicle_expensive"),
            dict(id=3, name="held-funded-other-nonfighter-ready", partition="heldout", ready_resources=8, other_space="other_nonfighter", exhausted=False,
                 upgrade_choice="nonunique_upgrade", unit_choice="enemy_vehicle_cheap")]


def selected_ref(code, context):
    if code in ("SEC_163", "LOF_155"):
        return context["upgrade_choice"]
    if code == "JTL_217":
        return "friendly_ground"
    if code in ("LOF_077", "JTL_078"):
        return context["unit_choice"]
    return "source"


def build_plan(catalog, runtime, decks):
    by = {r["setCode"]: r for r in catalog["cards"]}
    admitted = {r["setCode"] for r in runtime["runtimeAdmittedCards"]}
    counts, deck_ids = Counter(), defaultdict(set)
    for i, deck in enumerate(decks):
        for entry in deck["deck"]:
            counts[entry["id"]] += entry["count"]
            deck_ids[entry["id"]].add(i)
    selected = sorted(set(SOURCE_CODES) | set(HELPERS.values()) | {"TOKEN_SHIELD", "TOKEN_EXPERIENCE"})
    if any(code not in admitted for code in selected):
        raise ValueError("complete source/helper/token lacks existing runtime admission")
    for name in ("ground", "host"):
        host=by[HELPERS[name]]["card"]
        if "jedi" not in host["traits"] or "vehicle" in host["traits"] or host["types"]!=["unit"]:
            raise ValueError("Knight's Saber requires a non-Vehicle Jedi host")
    cards = []
    for code in SOURCE_CODES:
        r = by[code]
        if counts[code] <= 0 or set(r["card"]["types"]) - {"unit", "event"}:
            raise ValueError("source is not a declared main unit/event")
        abilities = [(side, i, a) for side, group in r["abilities"].items() for i, a in enumerate(group)]
        if any(side != "card" or a["trigger"] not in ("whenPlayed", "event") for side, i, a in abilities):
            raise ValueError("whole source needs an unreviewed trigger path")
        if any(r.get(k) for k in ("historyHelpers", "privatePrograms", "stateWatchers", "deploymentOverride", "classMethods")):
            raise ValueError("extra complete-card semantic fields require review")
        cards.append(dict(code=code, partition="heldout" if code in HELD_CODES else "train", raw_card=copy.deepcopy(r),
                          raw_row_sha256=G.digest(r), source_path=r.get("sourcePath"), source_hash=r.get("sourceHash"),
                          canonical_card_id=r["card"]["id"], aliases=r["card"]["setCodes"],
                          declared_copies=counts[code], source_deck_indices=sorted(deck_ids[code]),
                          ability_paths=[["abilities", side, i] for side, i, a in abilities],
                          normalized_program_group=G.digest(dict(card={k:v for k,v in r["card"].items() if k not in ("id","title","subtitle","setId","setCodes","internalName","text","rules")},
                                                               keywordValues=r.get("keywordValues",{}), abilities={side:[G.normalized_program(a) for a in group] for side,group in r["abilities"].items()}))))
    groups = defaultdict(set)
    for card in cards:
        groups[card["normalized_program_group"]].add(card["partition"])
    if any(len(v) > 1 for v in groups.values()):
        raise ValueError("complete normalized definition group crosses card split")
    return dict(schema="actual-corpus-native-plan/1", status="prepared-no-execution", source_revision=G.REVISION,
                cards=cards, contexts=contexts(), helpers=HELPERS, selected_whole_cards=selected,
                selected_whole_rows={code: by[code] for code in selected}, selected_row_hashes={code:G.digest(by[code]) for code in selected},
                candidate_order=list(CANDIDATES), context_feature_names=list(CONTEXT_FEATURES), candidate_feature_names=list(CANDIDATE_FEATURES),
                source_head_names=list(SOURCE_HEADS),source_binary_heads=list(SOURCE_BINARY),target_names=list(TARGET_HEADS),binary_heads=list(TARGET_BINARY),
                source_head_units={n:("boolean" if n in SOURCE_BINARY else "resource copies" if n=="cost_resource" else "signed count") for n in SOURCE_HEADS},
                target_units={n:("boolean" if n in TARGET_BINARY else "signed native stat/count") for n in TARGET_HEADS},
                expected_cases=32,candidates_per_case=8,max_applies_per_case=8,collector_max_engine_applies=256,campaign_max_seconds=90,
                max_rss_bytes=1024**3,cpu_threads=1,optimizer_updates=0,paid_jobs=0,
                split=dict(train_codes=[c for c in SOURCE_CODES if c not in HELD_CODES],heldout_codes=list(HELD_CODES),train_state_families=[0,1,2],heldout_state_families=[3],
                           cells=dict(train=18,program_held=6,state_held=6,joint=2)),
                coverage=dict(source_cards=8,declared_source_copies=sum(counts[c] for c in SOURCE_CODES),source_deck_indices=sorted(set().union(*(deck_ids[c] for c in SOURCE_CODES))),
                              all_main_ids=251,all_main_copies=1432,runtime_admitted_main_ids=115,runtime_admitted_main_copies=635,
                              qualification="Only observed paths of selected8 cards, not all115 admitted or all251 main IDs."),
                admission_scope="runtime-admission gameConformance is explicitly not assessed by this report; native collection is a separate observed fixture check.",
                action_protocol="Own hand -> actual offered play -> native entry/event -> sole complete trigger choices -> predeclared target if offered, otherwise actual Cancel if offered -> settled snapshot; at most8 actual applies/root. Never substitute another target. Unrecognized/unsettled/error path preserved with outcome masks0.",
                catalogue_scope="Pin full generated catalogue/admission/shards and preserve complete selected rows plus exact helper/token definitions. Explicit subcatalog selection is recorded and checked by the unchanged runtime; no claim that full-pool admission implies all-state conformance.",
                privacy="Own known hand and public arena/resources/base/leader/aspects only. No opponent hand, deck contents, hidden order, draws or opponent execution.",
                feature_scope="Public before-play source stats/known masks, own aspects, OTHER friendly space/Fighter counts, and each candidate's public stats/printed cost/unique/type/Vehicle/Fighter. Full source metadata+all ordered abilities+keywordValues supplied separately; no raw opaque IDs in primary features.",
                action_intent="selected_candidate_indices is a declared BEFORE-play candidate intent, not an observed offer. It is irrelevant to source availability but may enter a shared source head; post-play source heads require its candidate features because cancellation/commit changes cost and entry. Target membership remains a label only.",
                limitations=["Held LOF155 is a native fixture card holdout but occurs in inherited deck-training lists; JTL217 is inherited held-only.",
                             "Exhaust is wholly held in JTL217: one-card effect-family OOD diagnostic, not repeated held-effect proof.",
                             "Held selector unique is an explicit new predicate-path stress; do not claim every held primitive/path is seen.",
                             "Only two joint roots; no gameplay, strategic or broad semantic qualification.",
                             "ASH048 Shielded is observed on entry; Sentinel metadata preserved, attack-target behavior not tested here.",
                             "JTL158 executable effect is conditional SELF DAMAGE1, despite its display title. JTL217 excludes entering source from other-space count.",
                             "Printed-cost2/3 helpers are actual distinct cards TWI253/TWI111: both Vehicle/Fighter/space/HP4, power1vs3. No printed-cost override or one-field causal claim.",
                             "Full card frontend is complete definition coverage; measured behavior remains limited to play, entry and selected trigger in four synthetic public states."])


def candidate_vector(p, source, rows):
    code=p.get("code");card=rows[code]["card"] if code in rows else None
    cost=card.get("cost") if card else None;cost_known=type(cost) in (int,float) and np.isfinite(cost)
    unique=card.get("unique") if card else None;unique_known=type(unique) is bool
    return [*G.candidate_vector(p,source,rows),float(cost) if cost_known else 0,float(cost_known),float(unique) if unique_known else 0,float(unique_known),
            float(card is not None and "upgrade" in card["types"]),float(card is not None and "leader" in card["types"]),
            float(card is not None and "vehicle" in card["traits"]),float(card is not None and "fighter" in card["traits"])]


def context_vector(before, rows):
    p=before["projections"]["source"];player=before["state"]["players"]["p1"]
    counts=Counter()
    for role in ("base","leader"):
        card=player[role];code=card.get("setCode") or card.get("code")
        if code is None:
            code=before["own_aspect_sources"][role]
        counts.update(rows[code]["card"]["aspects"])
    return [G.ready_resources(before),float(p["zone"]=="hand"),*[counts[a] for a in ASPECTS],before["other_friendly_space_count"],before["other_friendly_fighter_count"],
            *[float(p[f]) for f in ("power","hp","damage","exhausted")],*[float(p["known"][f]) for f in ("power","hp","damage","exhausted")]]


def _validate_capture(capture, refs):
    settled=G.settled_capture(capture)
    if set(capture["projections"])!=set(CANDIDATES):raise ValueError("public candidate bank differs")
    for slot in CANDIDATES:
        if capture["projections"][slot]["id"]!=refs[slot]:raise ValueError("public projection identity differs")
    for seat in ("p1","p2"):
        # These fixtures have no draw primitive and create no deck/hidden cards.
        if capture["state"]["players"][seat]["deck"] or seat=="p2" and capture["state"]["players"][seat]["hand"]:
            raise ValueError("fixture unexpectedly contains hidden opponent/deck input")
    return settled


def convert_receipt(receipt, plan, assembled):
    """Derive masked labels only from actual public actions and native snapshots."""
    if receipt.get("schema")!="jepa-actual-corpus-native/1" or receipt.get("sourceRevision")!=G.REVISION or receipt.get("collectionPlan")!=plan:
        raise ValueError("native receipt source/schema/whole plan differs")
    if receipt.get("candidateOrder")!=list(CANDIDATES) or receipt.get("selectedWholeCards")!=plan["selected_whole_cards"] or receipt.get("selectedCatalogueSha256")!=G.native_catalog_hash(assembled,plan["selected_whole_cards"]):
        raise ValueError("whole native selected catalogue differs")
    if type(receipt.get("applyCalls")) is not int or not 0<=receipt["applyCalls"]<=256:raise ValueError("native quota differs")
    cases=sorted(receipt["cases"],key=lambda c:(c["state_family"],c["card"]))
    if len(cases)!=32 or {(c["card"],c["state_family"]) for c in cases}!={(c,f) for c in SOURCE_CODES for f in range(4)}:
        raise ValueError("all32 predeclared roots required")
    rows={r["setCode"]:r for r in assembled["cards"]};cards={r["code"]:r for r in plan["cards"]}
    x=[];cx=[];sy=[];sm=[];ty=[];tm=[];parts=[];chosen_indices=[];applies=0;errors=0;pending=0
    for case in cases:
        code=case["card"];context=plan["contexts"][case["state_family"]];before=case["before"];refs=case["refs"]
        if not _validate_capture(before,refs) or before["decision"]!="Window" or case.get("publicSnapshotRoundtripExact") is not True:
            raise ValueError("before-play root is not settled/roundtrip exact")
        if case["chosen_ref"]!=selected_ref(code,context) or case["identity_partition"]!=cards[code]["partition"] or case["state_partition"]!=context["partition"]:
            raise ValueError("root binding/prechosen target/split differs")
        chosen_indices.append(CANDIDATES.index(case["chosen_ref"]))
        if before["projections"]["source"]["zone"]!="hand" or before["projections"]["source"]["code"]!=code or before["projections"]["source"]["owner"]!="p1":
            raise ValueError("source is not the exact own declared hand card")
        if G.ready_resources(before)!=context["ready_resources"] or len(before["state"]["players"]["p1"]["resources"])!=8:
            raise ValueError("resource fixture differs")
        # Native public UpgradeTarget queries independently certify lawful fixture
        # attachments; cancellation of a trigger is never treated as play undo.
        witnesses=case.get("attachmentTargetWitnesses",[])
        if len(witnesses)!=2:raise ValueError("both attachment legality witnesses required")
        for slot,w in zip(("nonunique_upgrade","unique_upgrade"),witnesses):
            q=w["publicTargetQuery"];_validate_capture(q,refs)
            if q["decision"]!="UpgradeTarget" or q["sourceInstance"]!=refs[slot] or w["upgrade"]!=refs[slot] or w["offeredHost"] not in G.action_for(q,w["host"]):
                raise ValueError("lawful native attachment target witness differs")
        actual_space=before["state"]["players"]["p1"]["space"]
        fighter=sum("fighter" in rows[r["setCode"]]["card"]["traits"] for r in actual_space)
        ground=before["state"]["players"]["p1"]["ground"]
        fighter+=sum("fighter" in rows[r["setCode"]]["card"]["traits"] for r in ground)
        expected_other=0 if context["other_space"] is None else 1
        if before["other_friendly_space_count"]!=len(actual_space) or len(actual_space)!=expected_other or before["other_friendly_fighter_count"]!=fighter:
            raise ValueError("OTHER friendly unit query facts differ")
        if actual_space and actual_space[0]["setCode"]!=HELPERS[context["other_space"]]:raise ValueError("other-space complete helper differs")
        for slot in ("friendly_ground","enemy_vehicle_cheap","enemy_vehicle_expensive"):
            if before["projections"][slot]["exhausted"]!=context["exhausted"]:raise ValueError("candidate readiness fixture differs")
        x.append(context_vector(before,rows));cx.append([candidate_vector(before["projections"][slot],refs["source"],rows) for slot in CANDIDATES])
        source=np.zeros(9,np.float32);source_mask=np.zeros(9,np.float32);target=np.zeros((8,7),np.float32);target_mask=np.zeros((8,7),np.float32)
        offered=G.action_for(before,refs["source"]);available=bool(offered)
        source[0]=available;source_mask[0]=1
        play=case.get("playAction");steps=case["steps"];error=case.get("engineError");errors+=error is not None
        if (play is None)!= (not available) or play is not None and play not in offered:raise ValueError("actual own-hand play offer differs")
        if type(case["applyCalls"]) is not int or not 0<=case["applyCalls"]<=8 or case["applyCalls"]!=len(steps)+int(error is not None):raise ValueError("per-root durable apply accounting differs")
        applies+=case["applyCalls"];last=before;chosen_steps=[]
        for k,step in enumerate(steps):
            a=step["action"]
            if step["before"]!=last or a not in last["offeredActions"]:raise ValueError("native action/snapshot chain differs")
            _validate_capture(step["after"],refs)
            stage=step["stage"]
            if k==0:
                if stage!="play-own-hand" or a!=play:raise ValueError("first action must play exact own hand source")
            elif stage=="chosen-target":
                if last!=case.get("targetPrompt") or a!=case.get("targetAction") or a not in G.action_for(last,refs[case["chosen_ref"]]):raise ValueError("actual chosen target binding differs")
                chosen_steps.append(step)
            elif stage=="decline-unoffered-target":
                if last!=case.get("targetPrompt") or G.action_for(last,refs[case["chosen_ref"]]) or not (a.get("arg") in ("cancel","passAbility") or a.get("label")=="Cancel"):raise ValueError("decline cannot replace an available target")
            elif stage=="accept-optional-trigger":
                if last["decision"]!="AbilityOptional" or a.get("arg")!="trigger":raise ValueError("optional trigger choice differs")
            elif stage=="use-no-effect-anyway":
                if last["decision"]!="AbilityNoEffect" or type(a.get("arg")) is not int or a["arg"]!=0:raise ValueError("no-effect choice differs")
            elif stage=="sole-trigger-order":
                if last["decision"]!="TriggerOrder" or len(last["offeredActions"])!=1:raise ValueError("ambiguous trigger order unsupported")
            else:raise ValueError("unreviewed native protocol stage")
            last=step["after"]
        prompt=case.get("targetPrompt")
        if prompt is not None:
            _validate_capture(prompt,refs)
            if prompt["decision"]!="AbilityTarget" or not any(s["after"]==prompt for s in steps):raise ValueError("target prompt not actually reached")
            for j,slot in enumerate(CANDIDATES):target[j,0]=bool(G.action_for(prompt,refs[slot]));target_mask[j,0]=1
        if len(chosen_steps)>1:raise ValueError("only one predeclared candidate commit allowed")
        final=case.get("final")
        if final is not None:
            if error is not None or final!=last or not _validate_capture(final,refs) or case["completion"]!="settled":raise ValueError("final outcomes need exact settled native witness")
            a=before["projections"]["source"];z=final["projections"]["source"]
            source[1:]=[float(z["zone"]!="hand" and (z["in_arena"] or z["zone"]=="discard")),G.ready_resources(before)-G.ready_resources(final),float(z["in_arena"]),float(z["zone"]=="discard"),float(z["zone"]=="hand"),z["damage"]-a["damage"],z["shield_count"]-a["shield_count"],float(z["exhausted"])]
            source_mask[1:6]=1
            for h,field in ((6,"damage"),(7,"shield_count"),(8,"exhausted")):
                source_mask[h]=float(a["known"][field] and z["known"][field])
            if chosen_steps:
                j=CANDIDATES.index(case["chosen_ref"]);a=before["projections"][case["chosen_ref"]];z=final["projections"][case["chosen_ref"]]
                target[j,1]=float(not z["present"] or z["zone"] in ("discard","absent"));target_mask[j,1]=1
                if a["present"] and z["present"] and a["zone"]==z["zone"]:
                    for h,field in enumerate(("damage","exhausted","shield_count","power","hp"),2):
                        if a["known"][field] and z["known"][field]:target[j,h]=float(z[field])-float(a[field]);target_mask[j,h]=1
        elif available and error is None:pending+=1
        if not available and (steps or final is not None or prompt is not None or error is not None):raise ValueError("unavailable own play cannot have transitions")
        sy.append(source);sm.append(source_mask);ty.append(target);tm.append(target_mask)
        parts.append("joint" if code in HELD_CODES and context["id"]==3 else "program-held" if code in HELD_CODES else "state-held" if context["id"]==3 else "train")
    if applies!=receipt["applyCalls"]:raise ValueError("native total apply count differs from roots")
    arrays=dict(context_features=np.asarray(x,np.float32),candidate_features=np.asarray(cx,np.float32),candidate_mask=np.ones((32,8),np.float32),
                source_targets=np.asarray(sy,np.float32),source_mask=np.asarray(sm,np.float32),targets=np.asarray(ty,np.float32),target_mask=np.asarray(tm,np.float32),
                source_cards=np.asarray([r["card"] for r in cases]),state_families=np.asarray([r["state_family"] for r in cases],np.int64),partition=np.asarray(parts),selected_candidate_indices=np.asarray(chosen_indices,np.int64))
    for part in ("train","program-held","state-held","joint"):arrays[part.replace("-","_")+"_idx"]=np.flatnonzero(arrays["partition"]==part).astype(np.int64)
    if any(not np.isfinite(v).all() for v in arrays.values() if v.dtype.kind=="f"):raise ValueError("nonfinite native dataset")
    for f in range(4):
        ids=np.flatnonzero(arrays["state_families"]==f);anchor=ids[0]
        for i in ids[1:]:
            if not np.array_equal(arrays["context_features"][anchor,:10],arrays["context_features"][i,:10]) or not np.array_equal(arrays["candidate_features"][anchor,1:],arrays["candidate_features"][i,1:]):raise ValueError("fixed public relevant context differs across source identities")
    signatures={part:{hashlib.sha256(arrays["context_features"][i,:10].tobytes()+arrays["candidate_features"][i,1:].tobytes()).hexdigest() for i in np.flatnonzero(arrays["partition"]==part)} for part in ("train","state-held")}
    if signatures["train"]&signatures["state-held"]:raise ValueError("held public state has exact encoded training replay")
    support={}
    for part in ("train","program-held","state-held","joint"):
        ix=np.flatnonzero(arrays["partition"]==part);support[part]={}
        for names,y,m in ((SOURCE_HEADS,arrays["source_targets"][ix],arrays["source_mask"][ix]),(TARGET_HEADS,arrays["targets"][ix],arrays["target_mask"][ix])):
            for h,n in enumerate(names):
                vals=y[...,h][m[...,h]>0];support[part][n]=dict(known=int(vals.size),values=np.unique(vals).astype(float).tolist())
    witnesses={}
    for code in SOURCE_CODES:
        ix=np.flatnonzero(arrays["source_cards"]==code)
        funded=ix[arrays["context_features"][ix,0]>0]
        played=[int(i) for i in funded if arrays["source_mask"][i,1] and arrays["source_targets"][i,1]==1]
        witnesses[code]=dict(funded_offered_roots=[int(i) for i in funded if arrays["source_targets"][i,0]],
                             funded_successful_play_roots=played,settled_roots=[int(i) for i in ix if cases[i].get("final") is not None],
                             selected_target_commit_roots=[int(i) for i in ix if any(s["stage"]=="chosen-target" for s in cases[i]["steps"])],
                             declined_target_roots=[int(i) for i in ix if any(s["stage"]=="decline-unoffered-target" for s in cases[i]["steps"])],
                             native_error_roots=[int(i) for i in ix if cases[i].get("engineError") is not None],
                             shield_entry_observed=bool(any(arrays["source_mask"][i,7] and arrays["source_targets"][i,7]>0 for i in ix)),
                             sentinel_attack_behavior_tested=False)
    manifest=dict(schema="jepa-actual-corpus-native-data/1",cards=cards,programs=cards,plan=plan,records=cases,candidate_order=list(CANDIDATES),
                  context_feature_names=list(CONTEXT_FEATURES),candidate_feature_names=list(CANDIDATE_FEATURES),source_head_names=list(SOURCE_HEADS),source_binary_heads=list(SOURCE_BINARY),target_names=list(TARGET_HEADS),binary_heads=list(TARGET_BINARY),
                  source_revision=G.REVISION,native_apply_calls=applies,native_engine_error_roots=errors,pending_roots=pending,head_support=support,
                  split=plan["split"],state_context_exact_training_overlap=0,endpoint_witnesses=witnesses,
                  every_source_has_funded_successful_play=all(w["funded_successful_play_roots"] for w in witnesses.values()),
                  play_committed_definition="At a settled native endpoint source has left own hand and is in an arena or discard; accepted Window click alone is not this label. Unit-trigger decline retains play, event cancellation may retain hand.",
                  semantic_validated=False,scope="8 actual-list complete definitions;32 synthetic public play states. No all-state/whole-corpus/gameplay qualification.")
    return arrays,manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out-dir",type=Path,default=ROOT);ap.add_argument("--native-receipt",type=Path);ap.add_argument("--plan-file",type=Path);args=ap.parse_args()
    gen=G.PINNED_KESSEL/"compiler/generated";repo=HERE.parents[2]
    catalog=json.loads((gen/"cards.json").read_text());runtime=json.loads((gen/"runtime-admission.json").read_text())
    if args.native_receipt:
        path=args.plan_file or args.out_dir/"native-plan.json";plan=json.loads(path.read_text())
        if any(G.sha(p["path"])!=p["sha256"] for p in plan["source_pins"]):raise ValueError("frozen source pin differs")
        receipt=json.loads(args.native_receipt.read_text())
        if receipt["collectionPlanSha256"]!=G.sha(path):raise ValueError("native plan byte pin differs")
        arrays,manifest=convert_receipt(receipt,plan,G.assembled_catalog(gen));out=args.out_dir/"actual-corpus.npz";mp=out.with_suffix(".manifest.json")
        if out.exists() or mp.exists():raise ValueError("preserve existing native dataset")
        np.savez_compressed(out,**arrays);manifest.update(artifact=dict(path=str(out),sha256=G.sha(out)),native_receipt=dict(path=str(args.native_receipt),sha256=G.sha(args.native_receipt)))
        mp.write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(dict(path=str(out),sha256=G.sha(out),native_applies=0,neural_forwards=0)));return
    bank=repo/"decks/ash-meta-2026-09.json";plan=build_plan(catalog,runtime,json.loads(bank.read_text()))
    paths=[Path(__file__),HERE/"grounded_contrast_data.py",bank,ROOT/"coverage-v2/actual-corpus-coverage.json",*[gen/n for n in ("cards.json","runtime-admission.json","manifest.json","inputs.json","diagnostics.json")]]
    plan["source_pins"]=[dict(path=str(p),sha256=G.sha(p)) for p in paths]
    args.out_dir.mkdir(parents=True,exist_ok=True);out=args.plan_file or args.out_dir/"native-plan.json";data=json.dumps(plan,indent=2)+"\n"
    if out.exists() and out.read_text()!=data:raise ValueError("preserve frozen proposal; select a new versioned output directory")
    if not out.exists():out.write_text(data)
    print(json.dumps(dict(path=str(out),sha256=G.sha(out),source_cards=8,cases=32,neural_forwards=0,native_applies=0,coverage=plan["coverage"])))


if __name__=="__main__":main()
