"""Prepare the fixed seven-source learned-input assay; no engine/model execution."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/"experiments/binding-transfer-v1"
KESSEL=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source")
REVISION="c7ee39554901278cee70f61fd8b26fb1920696b3"
CODES=("LAW_045","ASH_071","JTL_085","ASH_228","LOF_215","LOF_053","LOF_261")
TRAIN=CODES[:5]
HELD=CODES[5:]
ROLES=("source","own_helper","opponent_helper","anchor_a","anchor_b","auxiliary","own_base","opponent_base")
HELPERS=dict(base="ASH_019",leader="IBH_053",resource="LOF_256",huyang="ASH_056",mina="SEC_094",
             host="SEC_028",victim="SEC_028",victim_upgrades=["ASH_066","LOF_215"],
             damage_space="LAW_175",aura_space="JTL_095",unused_anchor="LOF_256")
TEMPLATES=dict(LAW_045="conditional-chosen-damage",ASH_071="simultaneous-self-and-chosen-damage",
               JTL_085="other-friendly-space-stat-aura",ASH_228="physical-parent-stat-bonus",
               LOF_215="physical-parent-stat-bonus",LOF_053="physical-parent-stat-bonus",LOF_261="physical-parent-stat-bonus")

def encoded(v):return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v):return hashlib.sha256(encoded(v)).hexdigest()
def pin(path):
    p=Path(path).resolve();b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))


def worlds():
    out=[]
    def add(code,cohort,mode,intent,partition,**kwargs):
        out.append(dict(id=len(out),source_code=code,cohort=cohort,observation_mode=mode,intent_ref=intent,
            requires_target=mode!="passive-aura",observation_refs=["anchor_a","anchor_b"],partition=partition,
            ready_resources=12,state_family=sum(w["source_code"]==code for w in out),template_id=TEMPLATES[code],
            max_applies=1 if mode=="passive-aura"else 2,**kwargs))
    for own,opponent in itertools.product(("ASH_056","SEC_094"),repeat=2):
        add("LAW_045","own-aspect-condition","chosen-target","anchor_a","train",
            own_helper=own,opponent_helper=opponent,victim_damage=2,
            hypothesis=dict(chosen_damage=5 if own=="SEC_094"else 3,other_anchor_damage=0))
    for own in("ASH_056","SEC_094"):
        add("LAW_045","own-aspect-condition","chosen-target","anchor_a","state_held",
            own_helper=own,opponent_helper="ASH_056",victim_damage=3,
            hypothesis=dict(chosen_damage=5 if own=="SEC_094"else 3,other_anchor_damage=0))
    for intended,damage in itertools.product(("anchor_a","anchor_b"),(0,1)):
        add("ASH_071","simultaneous-damage","chosen-target",intended,"train"if damage==0 else"state_held",
            anchor_damage=damage,hypothesis=dict(source_damage=1,chosen_damage=1,other_anchor_damage=0))
    for own_anchor,damage in itertools.product(("anchor_a","anchor_b"),(0,1)):
        add("JTL_085","friendly-space-aura","passive-aura","source","train"if damage==0 else"state_held",
            own_anchor=own_anchor,anchor_damage=damage,hypothesis=dict(own_power=1,own_hp=1,opponent_power=0,opponent_hp=0))
    for code in ("ASH_228","LOF_215","LOF_053","LOF_261"):
        for intended,damage in itertools.product(("anchor_a","anchor_b"),(0,)if code in TRAIN else(0,1)):
            part=("train"if damage==0 else"state_held")if code in TRAIN else("family_held"if damage==0 else"joint")
            add(code,"attachment-parent-binding","attachment-parent",intended,part,anchor_damage=damage,
                hypothesis=dict(untouched_anchor_power=0,untouched_anchor_hp=0))
    return out


def build_plan(catalog,runtime):
    rows={r["setCode"]:r for r in catalog["cards"]};admitted={r["setCode"]for r in runtime["runtimeAdmittedCards"]}
    helpers={v for v in HELPERS.values()if isinstance(v,str)}|set(HELPERS["victim_upgrades"])
    selected=sorted(set(CODES)|helpers|{"TOKEN_SHIELD"})
    if not(set(selected)-{"TOKEN_SHIELD"})<=admitted:raise ValueError("complete normal source/helper lacks existing admission")
    token=rows["TOKEN_SHIELD"]
    if digest(token)!="677c6916b4cce150b411c83708dcc1af953204fde4191e3a3039891a91a758be"or token["status"]!="unsupported"or token["card"]["types"]!=["token","upgrade"]:raise ValueError("original native Shield support changed")
    for code in CODES:
        if any(rows[code].get(k)for k in("historyHelpers","privatePrograms","stateWatchers","deploymentOverride","classMethods")):
            raise ValueError("unreviewed complete source semantics: "+code)
    host=rows["SEC_028"]
    if host["card"]["unique"]or"vehicle"in host["card"]["traits"]or"force"not in host["card"]["traits"]or any(host["abilities"].values())or host["keywordValues"]:
        raise ValueError("hosts must be identical plain nonunique Force non-Vehicles")
    for code in("LAW_175","JTL_095"):
        r=rows[code]
        if r["card"]["unique"]or r["card"].get("arena")!="space"or any(r["abilities"].values())or r["keywordValues"]:
            raise ValueError("space endpoints must be plain nonunique native units")
    if rows["LAW_175"]["card"]["hp"]-1-1<=0:raise ValueError("ASH071 endpoint must survive")
    if set(rows["LAW_045"]["card"]["aspects"])&{"command","cunning"}:raise ValueError("entering LAW source changes aspect condition")
    if set(host["card"]["aspects"])&{"command","cunning"}:raise ValueError("victim contaminates opponent control")
    hp=host["card"]["hp"]+sum(rows[c]["card"]["upgradeHp"]for c in HELPERS["victim_upgrades"])
    if hp!=10 or hp-3-5<=0:raise ValueError("fixed LAW victim survival differs")
    a=rows["ASH_228"]["abilities"]["card"]
    if len(a)!=1 or a[0].get("optional",False)or a[0].get("targetResolver")or a[0]["effect"]!={"kind":"exhaust","target":{"kind":"ref","path":["source","parentCard"]}}:
        raise ValueError("ASH228 must retain mandatory direct parent exhaust without another prompt")
    ws=worlds();partitions={p:[w["id"]for w in ws if w["partition"]==p]for p in("train","family_held","state_held","joint")}
    pairs=[]
    for opposite,damage in(("ASH_056",2),("SEC_094",2),("ASH_056",3)):
        pairs.append(dict(kind="LAW-own-aspect-flip",worlds=[w["id"]for w in ws[:6]if w["opponent_helper"]==opposite and w["victim_damage"]==damage]))
    for own in("ASH_056","SEC_094"):
        pairs.append(dict(kind="LAW-opponent-null",worlds=[w["id"]for w in ws[:4]if w["own_helper"]==own]))
    for code in("ASH_071","ASH_228","LOF_215","LOF_053","LOF_261"):
        for damage in((0,)if code in("ASH_228","LOF_215")else(0,1)):
            pairs.append(dict(kind="actual-intent-swap",source=code,worlds=[w["id"]for w in ws if w["source_code"]==code and w["anchor_damage"]==damage],observe_both=True))
    return dict(schema="jepa-binding-transfer-plan/1",status="prepared-no-execution",source_revision=REVISION,codes=list(CODES),train_codes=list(TRAIN),heldout_codes=list(HELD),
        cards=[dict(code=c,raw_card=copy.deepcopy(rows[c]),raw_row_sha256=digest(rows[c]),template_id=TEMPLATES[c])for c in CODES],worlds=ws,helpers=copy.deepcopy(HELPERS),
        candidate_order=list(ROLES),selected_whole_cards=selected,selected_whole_rows={c:copy.deepcopy(rows[c])for c in selected},
        selected_row_hashes={c:digest(rows[c])for c in selected},selected_row_pins={c:dict(sha256=digest(rows[c]),bytes=len(encoded(rows[c])))for c in selected},
        split=dict(root_partitions=partitions,train_codes=list(TRAIN),heldout_codes=list(HELD),
            family_held_meaning="New whole-program variants within the familiar positive physical-parent-stat family; NOT unseen numeric-stat-family transfer.",
            source_grouping="All aliases/reprints of one full normalized program stay together. LAW full own/opponent aspect factorial TRAIN at victimdamage2; both own truths STATE-held at damage3. Fresh state transfer remains distinct from unsupported fresh aspect-numeric program transfer."),
        expected_cases=26,max_applies_per_case=2,collector_max_engine_applies=48,expected_engine_applies=48,
        structural_apply_bound=dict(passive_aura_roots=4,passive_aura_per_root=1,other_roots=22,other_per_root=2,total=48),native_build_max_seconds=15,collector_max_seconds=30,
        max_rss_bytes=1024**3,cpu_workers=1,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,
        declared_pairs=pairs,survival_witness=dict(LAW_hp=hp,LAW_initial_damage=[2,3],LAW_maximum_damage=5,LAW_minimum_remaining_hp=hp-8,ASH071_enemy_hp=rows["LAW_175"]["card"]["hp"],ASH071_initial_damage=1,ASH071_damage=1),
        template_gate=dict(expected_positive_damage_templates=[TEMPLATES[c]for c in("LAW_045","ASH_071")],expected_positive_stat_templates=[TEMPLATES[c]for c in("JTL_085","ASH_228")],
            support_requires_native=True,observed_zero_required=True,negative_sign_qualification=False,aspect_numeric_new_program_gate="UNSUPPORTED: LAW045 is the only aspect-dependent numeric-damage template among actual115; report fresh STATE transfer separately.",
            keywords_qualified=False,old_conditional_task_separate=True),
        numeric_support_prelabel=dict(training_positive_power=[1,2],training_positive_hp=[1,3],held_positive_power=[2],held_positive_hp=[2,3],
            interpretation="Expected native quantities only. Held HP2 interpolates the TRAIN1/3 range; HP3 and P2 appear in TRAIN. Actual observed support is a mandatory postcollection gate, not an oracle label."),
        constructor_support=dict(codes=["TOKEN_SHIELD"],not_normal_source_admission=True,expected_physical_shield_instances=0),
        raw_abi=dict(schema="jepa-binding-transfer-native/1",journal_schema="jepa-binding-transfer-apply-journal/1",modes=["chosen-target","attachment-parent","passive-aura"],
            capture="Full native state and current public projections with known flags and complete printed metadata; BEFORE only is model input.",
            declaration="refs,declared_intent{ref,id,requires_target},observation_refs; aura uses source play-intent and has no external intended-target bit.",
            physical_proof="fixtureAttachmentWitnesses list; actual targetAction and final source parent are label proof only.",
            task="Observe both predeclared public endpoints under ONE actual action. Old conditional-on-query labels remain valid and are a separate secondary panel."),
        privacy="Only own known source hand and public arena/resources/base/leader. Both decks and opponent hand empty; no attacks, draws, private order or future links in inputs.",
        novelty="LAW victimHP10/damage2 differs from seen16 HP7/damage0/1. Prior programs/states are diagnostics, never fresh qualification. Native inputs must be audited against saved old banks without outcome-based replacement.",
        hypothesis_is_not_label=True,no_retry_after_collection_start=True,root_go_required=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--out-dir",type=Path,default=ROOT);a=p.parse_args()
    gen=KESSEL/"compiler/generated";result=build_plan(json.loads((gen/"cards.json").read_text()),json.loads((gen/"runtime-admission.json").read_text()))
    result["source_pins"]=[pin(q)for q in(Path(__file__),*[gen/n for n in("cards.json","runtime-admission.json","manifest.json","inputs.json","diagnostics.json")])]
    result["prelaunch_history"]=[pin(ROOT/n/"snapshot.json")for n in("prelaunch-24-root-v1","prelaunch-26-root-6-source-v2")]
    a.out_dir.mkdir(parents=True,exist_ok=True);out=a.out_dir/"native-plan-v3.json";raw=json.dumps(result,indent=2)+"\n"
    if out.exists()and out.read_text()!=raw:raise FileExistsError("preserve prior plan; use versioned output")
    if not out.exists():out.write_text(raw)
    print(json.dumps(dict(plan=pin(out),roots=26,max_applies=48,native_applies=0,neural_forwards=0)))


if __name__=="__main__":main()
