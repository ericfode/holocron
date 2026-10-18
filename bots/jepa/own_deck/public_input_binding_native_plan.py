"""Prepare sixteen public-input/binding fixtures; never build or run an engine."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import grounded_contrast_data as G

ROOT=HERE.parents[3]/"experiments/public-input-binding-v1"
COVERAGE_CONTRACT=ROOT/"coverage-contract.json"
CODES=("LAW_045","LOF_215")
ROLES=("source","own_helper","opponent_helper","victim","host_a","host_b","own_base","opponent_base")
HELPERS=dict(base="ASH_019",leader="IBH_053",resource="LOF_256",victim="SEC_028",victim_upgrade="ASH_066",huyang="ASH_056",mina="SEC_094",host="SEC_028")


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def worlds():
    result=[]
    for own,opponent,damage in itertools.product(("ASH_056","SEC_094"),("ASH_056","SEC_094"),(0,1)):
        result.append(dict(id=len(result),cohort="own-aspect-condition",source_code="LAW_045",own_helper=own,opponent_helper=opponent,
            victim_damage=damage,ready_resources=12,intent_ref="victim",observation_refs=["victim"],layout=0,
            hypothesis=dict(damage_delta=5 if own=="SEC_094"else 3,opponent_helper_effect=0)))
    for intended,damage,layout in itertools.product(("host_a","host_b"),(0,1),(0,1)):
        result.append(dict(id=len(result),cohort="attachment-parent-binding",source_code="LOF_215",host_damage=damage,
            ready_resources=12,intent_ref=intended,observation_refs=["host_a","host_b"],layout=layout,
            hypothesis=dict(host_a_power_delta=1 if intended=="host_a"else 0,host_a_hp_delta=3 if intended=="host_a"else 0,
                            host_b_power_delta=1 if intended=="host_b"else 0,host_b_hp_delta=3 if intended=="host_b"else 0)))
    return result


def build_plan(catalog,runtime):
    rows={r["setCode"]:r for r in catalog["cards"]};admitted={r["setCode"]for r in runtime["runtimeAdmittedCards"]}
    selected=sorted(set(CODES)|set(HELPERS.values()))
    if not set(selected)<=admitted:raise ValueError("complete source/helper row lacks existing runtime admission")
    for code in CODES:
        if any(rows[code].get(k)for k in("historyHelpers","privatePrograms","stateWatchers","deploymentOverride","classMethods")):
            raise ValueError("unreviewed complete source semantics")
    # No omitted arena unit may silently make Zeb's own-aspect condition true.
    if set(rows["LAW_045"]["card"]["aspects"])&{"command","cunning"}:raise ValueError("Zeb entering source satisfies its own condition")
    for code in ("ASH_056","SEC_094"):
        card=rows[code]["card"]
        if card["arena"]!="ground"or"fighter"in card["traits"]or card["keywords"]not in([], ["restore"]):raise ValueError("helper changes an unintended global")
    key=lambda code:tuple(rows[code]["card"].get(k)for k in("cost","power","hp","unique","arena"))+tuple(t in rows[code]["card"]["traits"]for t in("imperial","creature","spectre","vehicle","fighter"))
    if key("ASH_056")!=key("SEC_094"):raise ValueError("public helper legacy34 matching changed")
    host=rows["SEC_028"]
    if host["card"]["unique"]or"vehicle"in host["card"]["traits"]or any(host["abilities"].values())or host["keywordValues"]:
        raise ValueError("binding hosts must be identical plain nonunique non-Vehicles")
    if set(rows[HELPERS["victim"]]["card"]["aspects"])&{"command","cunning"}:raise ValueError("opponent victim contaminates wrong-owner control")
    hp=rows[HELPERS["victim"]]["card"]["hp"]+rows["ASH_066"]["card"]["upgradeHp"]
    if hp-1-5<=0:raise ValueError("fixed victim must survive maximum damage")
    ws=worlds();pairs=[]
    for opponent,damage in itertools.product(("ASH_056","SEC_094"),(0,1)):
        ids=[w["id"]for w in ws if w["cohort"]=="own-aspect-condition"and w["opponent_helper"]==opponent and w["victim_damage"]==damage]
        pairs.append(dict(kind="own-public-aspect-flip",worlds=ids,expected_native_difference=2))
    for own,damage in itertools.product(("ASH_056","SEC_094"),(0,1)):
        ids=[w["id"]for w in ws if w["cohort"]=="own-aspect-condition"and w["own_helper"]==own and w["victim_damage"]==damage]
        pairs.append(dict(kind="wrong-owner-null-control",worlds=ids,expected_native_difference=0))
    for damage,layout in itertools.product((0,1),(0,1)):
        ids=[w["id"]for w in ws if w["cohort"]=="attachment-parent-binding"and w["host_damage"]==damage and w["layout"]==layout]
        pairs.append(dict(kind="intended-parent-swap",worlds=ids,observe_both_anchors=True))
    for intended,damage in itertools.product(("host_a","host_b"),(0,1)):
        ids=[w["id"]for w in ws if w["cohort"]=="attachment-parent-binding"and w["intent_ref"]==intended and w["host_damage"]==damage]
        pairs.append(dict(kind="physical-layout-alpha-control",worlds=ids,expected_native_difference=0))
    return dict(schema="public-input-binding-plan/1",status="prepared-no-execution",source_revision=G.REVISION,
        cards=[dict(code=c,raw_card=copy.deepcopy(rows[c]),raw_row_sha256=digest(rows[c]))for c in CODES],worlds=ws,helpers=HELPERS,
        candidate_order=list(ROLES),selected_whole_cards=selected,selected_whole_rows={c:copy.deepcopy(rows[c])for c in selected},selected_row_hashes={c:digest(rows[c])for c in selected},
        selected_row_pins={c:dict(sha256=digest(rows[c]),bytes=len(json.dumps(rows[c],sort_keys=True,separators=(",",":"),allow_nan=False).encode()))for c in selected},
        expected_cases=16,max_applies_per_case=5,collector_max_engine_applies=80,campaign_max_engine_applies=80,campaign_max_seconds=90,
        native_build_max_seconds=30,collector_max_seconds=60,max_rss_bytes=1024**3,cpu_workers=1,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,
        declared_pairs=pairs,survival_witness=dict(victim_printed_hp=rows[HELPERS["victim"]]["card"]["hp"],physical_upgrade_hp=3,total_before_hp=hp,maximum_initial_damage=1,maximum_hypothesized_damage=5,minimum_remaining_hp=hp-1-5),
        raw_abi=dict(schema="jepa-public-input-binding-native/1",inactive_roles="JSON null refs/projections",declaration="declared_intent={ref,id}, observation_refs ordered list; frozen before play",
            capture="Full native state wire and active public projections; printed traits/aspects/types/cost/unique/keywords+known, role_matches(source/intended/observation_anchor_a/b). Input only BEFORE capture.",
            chain="before,playAction,steps[{stage,before,action,after}],targetPrompt,targetAction,final,lastObserved,engineError,completion,applyCalls",
            endpoint_parent="final_source_parent is after-state physical proof ONLY; never predictor input",labels="No oracle labels in native receipt. Both attachment anchors actually observed from same settled transition."),
        scope="Two fresh complete actual-corpus source identities,16 authored public states. No old48 reuse as fresh evidence, no whole-card/all-state or learning-strength claim.",
        privacy="Only own known source hand and public arena/resources/bases/leaders; both decks and opponent hand empty; no helper attacks/deaths, draw/disclose or random selection.",
        fixture_semantics="LAW own arena initially contains ONLY the chosen own helper; source Zeb lacks Command/Cunning. Opponent SEC028 victim also lacks Command/Cunning, allowing the separate opponent helper flip to test wrong-owner binding. Its actual ASH066 attachment is publicly legality-queried; HP7 survives5 even with1 prior damage. LOF uses two distinct nonunique SEC028 instances; layout reverses physical creation order while retaining logical role/intent relations.",
        hypothesis_is_not_label="world.hypothesis and declared_pairs are frozen scientific expectations; after labels must be independently derived from actual settled native snapshots, retaining failures and unknowns.",
        no_retry_after_collection_start=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out-dir",type=Path,default=ROOT);args=ap.parse_args()
    gen=G.PINNED_KESSEL/"compiler/generated";plan=build_plan(json.loads((gen/"cards.json").read_text()),json.loads((gen/"runtime-admission.json").read_text()))
    plan["source_pins"]=[dict(path=str(p),sha256=G.sha(p),bytes=p.stat().st_size)for p in(Path(__file__),HERE/"grounded_contrast_data.py",COVERAGE_CONTRACT,*[gen/n for n in("cards.json","runtime-admission.json","manifest.json","inputs.json","diagnostics.json")])]
    args.out_dir.mkdir(parents=True,exist_ok=True);out=args.out_dir/"native-plan.json";data=json.dumps(plan,indent=2)+"\n"
    if out.exists()and out.read_text()!=data:raise FileExistsError("preserve existing plan; choose versioned directory")
    if not out.exists():out.write_text(data)
    print(json.dumps(dict(path=str(out),sha256=G.sha(out),roots=16,native_applies=0,neural_forwards=0)))


if __name__=="__main__":main()
