"""Identifiable native effects from actual corpus cards; no execution by default.

Rich and sparse supervision use the same roots, features and native labels. The
only sparse training operator masks the five target-delta columns. No engine,
card coverage, learner capacity or old evidence is changed by preparation.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import actual_corpus_native_plan as A
import grounded_contrast_data as G

ROOT=HERE.parents[3]/"experiments/native-effect-v2"
COHORT_CONTRACT=HERE.parents[3]/"experiments/actual-corpus/effect-cohort-audit-v1/strict12-contract-v3.json"
TRAIN=("ASH_048","LOF_151","SEC_142","JTL_144","JTL_217","ASH_171","SEC_051")
HELD=("JTL_102","LAW_131","JTL_079","LAW_127","ASH_228")
CODES=TRAIN+HELD
CANDIDATES=("source","friendly_ground","space_small","space_large","nonunique_upgrade","unique_upgrade","own_base","opponent_base")
CONTEXT_FEATURES=A.CONTEXT_FEATURES
CANDIDATE_FEATURES=A.CANDIDATE_FEATURES
SOURCE_HEADS=A.SOURCE_HEADS
SOURCE_BINARY=A.SOURCE_BINARY
TARGET_HEADS=A.TARGET_HEADS
TARGET_BINARY=A.TARGET_BINARY
FAMILIES={"ASH_048":"shielded-entry","LOF_151":"vanilla-upgrade-stats","SEC_142":"pointed-ground-constant-damage",
          "JTL_144":"pointed-unit-remaining-hp-damage","JTL_217":"other-space-conditional-exhaust",
          "ASH_171":"owned-upgrade-defeat-then-ready-source","SEC_051":"opponent-area-stat-debuff",
          "JTL_102":"pointed-unit-friendly-space-count-damage","LAW_131":"pointed-unit-event-stat-debuff",
          "JTL_079":"pointed-unit-event-stat-debuff","LAW_127":"attached-host-exhaust","ASH_228":"attached-host-exhaust"}
HELPERS=dict(A.HELPERS,small="TWI_253",large="TWI_111",nonfighter="SHD_060")


def contexts():
    return [dict(id=0,name="no-other-space-clean-ready",partition="train",ready_resources=12,
                 small=dict(code="TWI_253",owner="p2",damage=0,exhausted=False,shield=0),
                 large=dict(code="TWI_111",owner="p2",damage=0,exhausted=False,shield=0),
                 ground=dict(damage=0,exhausted=False,shield=0)),
            dict(id=1,name="one-friendly-ready-fighter-shielded-exhausted-ground",partition="train",ready_resources=12,
                 small=dict(code="TWI_253",owner="p1",damage=2,exhausted=False,shield=1),
                 large=dict(code="TWI_111",owner="p2",damage=0,exhausted=False,shield=0),
                 ground=dict(damage=1,exhausted=True,shield=1)),
            dict(id=2,name="two-friendly-fighters-clean-ready",partition="train",ready_resources=12,
                 small=dict(code="TWI_253",owner="p1",damage=0,exhausted=False,shield=0),
                 large=dict(code="TWI_111",owner="p1",damage=2,exhausted=False,shield=0),
                 ground=dict(damage=0,exhausted=False,shield=0)),
            dict(id=3,name="held-one-friendly-nonfighter",partition="heldout",ready_resources=12,
                 small=dict(code="SHD_060",owner="p1",damage=0,exhausted=False,shield=0),
                 large=dict(code="TWI_111",owner="p2",damage=0,exhausted=False,shield=0),
                 ground=dict(damage=1,exhausted=True,shield=1))]


def query_spec(code,family):
    if code=="SEC_051":return dict(ref=("space_small","friendly_ground","space_large","space_large")[family],mode="passive-area-anchor")
    if code=="ASH_048":return dict(ref="source",mode="self-entry")
    if code in ("LOF_151","LAW_127","ASH_228"):return dict(ref="friendly_ground",mode="upgrade-attachment")
    if code=="ASH_171":return dict(ref="unique_upgrade" if family==1 else "nonunique_upgrade",mode="chosen-target")
    if code=="JTL_217":return dict(ref="space_small" if family==1 else "friendly_ground",mode="chosen-target")
    if code=="JTL_144":return dict(ref=("space_small","space_small","space_large","space_large")[family],mode="chosen-target")
    if code=="JTL_102":return dict(ref=("space_small","space_small","space_small","space_large")[family],mode="chosen-target")
    return dict(ref="friendly_ground",mode="chosen-target")


def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from _walk(child)
    elif isinstance(value,list):
        for child in value:yield from _walk(child)


def build_plan(catalog,runtime,coverage):
    rows={r["setCode"]:r for r in catalog["cards"]};admitted={r["setCode"] for r in runtime["runtimeAdmittedCards"]}
    corpus={r["canonical_id"]:r for r in coverage["runtime_admitted_card_inventory"]}
    cards=[]
    for code in CODES:
        row=rows[code]
        if code not in admitted or code not in corpus:raise ValueError("source lacks actual-corpus whole runtime admission")
        if any(n.get("kind") in ("draw","resourceCard","searchDeck","disclose","useForce","gainTrait","loseTrait") for n in _walk(row["abilities"])):
            raise ValueError("cohort needs hidden or missing public-state input")
        if any(row.get(k) for k in ("historyHelpers","privatePrograms","stateWatchers","deploymentOverride","classMethods")):
            raise ValueError("complete source has unreviewed top-level semantics")
        cards.append(dict(code=code,partition="train" if code in TRAIN else "heldout",family=FAMILIES[code],raw_card=copy.deepcopy(row),
                          raw_row_sha256=G.digest(row),canonical_card_id=row["card"]["id"],aliases=row["card"]["setCodes"],
                          source_path=row.get("sourcePath"),source_hash=row.get("sourceHash"),main_copies=corpus[code]["main_copies"],
                          complete_ability_count=sum(map(len,row["abilities"].values()))))
    selected=sorted(set(CODES)|set(HELPERS.values())|{"TOKEN_SHIELD","TOKEN_EXPERIENCE"})
    if not set(selected)<=admitted:raise ValueError("complete helper/token lacks existing runtime admission")
    # Structural family holdouts deliberately group literal variants and the
    # conditional wrapper around attached-parent exhaustion together.
    if {FAMILIES[c] for c in TRAIN}&{FAMILIES[c] for c in HELD}:raise ValueError("template family crosses split")
    worlds=contexts();survival=[]
    ground_hp=rows[HELPERS["ground"]]["card"]["hp"]+rows[HELPERS["nonunique"]]["card"]["upgradeHp"]
    enemy_host_hp=rows[HELPERS["host"]]["card"]["hp"]+rows[HELPERS["unique"]]["card"]["upgradeHp"]
    for c in worlds:
        enemy_remaining=[enemy_host_hp]
        for slot in ("small","large"):
            if c[slot]["owner"]=="p2":enemy_remaining.append(rows[c[slot]["code"]]["card"]["hp"]-c[slot]["damage"])
        if min(enemy_remaining)<=3 or ground_hp-c["ground"]["damage"]<=5:raise ValueError("planned area/targeted debuff causes an unreviewed death hook")
        survival.append(dict(state_family=c["id"],opponent_unit_remaining_hp=enemy_remaining,after_area_minus3=[h-3 for h in enemy_remaining],
                             friendly_ground_hp=ground_hp,friendly_ground_damage=c["ground"]["damage"],after_targeted_minus5_remaining=ground_hp-c["ground"]["damage"]-5))
    return dict(schema="native-effect-v2-plan/1",status="prepared-no-execution",source_revision=G.REVISION,cards=cards,contexts=worlds,helpers=HELPERS,
                selected_whole_cards=selected,selected_whole_rows={c:rows[c] for c in selected},selected_row_hashes={c:G.digest(rows[c]) for c in selected},
                candidate_order=list(CANDIDATES),context_feature_names=list(CONTEXT_FEATURES),candidate_feature_names=list(CANDIDATE_FEATURES),
                source_head_names=list(SOURCE_HEADS),source_binary_heads=list(SOURCE_BINARY),target_names=list(TARGET_HEADS),binary_heads=list(TARGET_BINARY),
                query_specs={c:[query_spec(c,f) for f in range(4)] for c in CODES},survival_witnesses=survival,
                predeclared_behavior_pairs=[
                    *[dict(id=f"count-damage-{a}-{b}",kind="within-card-public-state-contrast",family=FAMILIES["JTL_102"],left=dict(card="JTL_102",state=a),right=dict(card="JTL_102",state=b),heads=["target_damage_delta"]) for a,b in ((0,1),(2,3))],
                    *[dict(id=f"attached-exhaust-{code}-{a}-{b}",kind="within-card-public-state-contrast",family=FAMILIES[code],left=dict(card=code,state=a),right=dict(card=code,state=b),heads=["target_exhausted_delta"]) for code in ("LAW_127","ASH_228") for a,b in ((0,1),(2,3))],
                    *[dict(id=f"targeted-stats-literals-state-{f}",kind="same-public-anchor-different-source-literal",family=FAMILIES["LAW_131"],left=dict(card="LAW_131",state=f),right=dict(card="JTL_079",state=f),heads=["target_power_delta","target_hp_delta"]) for f in range(4)]],
                expected_cases=48,max_applies_per_case=5,collector_max_engine_applies=240,campaign_max_engine_applies=256,campaign_max_seconds=90,max_rss_bytes=1024**3,cpu_workers=1,
                optimizer_updates=0,neural_forwards=0,paid_jobs=0,
                split=dict(train_codes=list(TRAIN),heldout_codes=list(HELD),train_state_families=[0,1,2],heldout_state_families=[3],cells=dict(train=21,program_held=15,state_held=7,joint=5),
                           family_groups=FAMILIES,held_template_families=sorted({FAMILIES[c] for c in HELD})),
                sparse_operator="Training mask only: keep every source mask and target_allowed/target_removed mask unchanged; mask exactly target delta columns2..6. Features, label values, roots, evaluation masks, fixed-capacity learner and batches remain matched. No outcome-dependent selection.",
                query_semantics="Chosen-target futures require an actual native target commit; upgrade futures require actual parent attachment. SEC051 alone uses a predeclared public area-observation anchor after a real paid settled play, without a fictional target choice/membership label. Unavailable/unoffered/declined/error/pending pointed futures remain unknown.",
                action_intent="Every selected_candidate_indices entry is the frozen query role before play, never offered membership or an after-state label. The source future head may consume that public intent; source availability is measured independently before play.",
                attachment_scope="Whole public target legality queries, valid non-Vehicle Jedi hosts, real physical Shield token links+parent+upgrades and exact snapshot/load; engine-created Shield entry remains native.",
                safety_scope="Own known hand and public board/resources only; both draw piles and opponent hand empty; no draw/resource-top-deck primitives, engine/card/coverage migration or opponent execution.",
                observability=dict(source_play_available="All roots funded; constant-positive availability diagnostic, not primary generalization.",
                    target_damage_delta="Damage family actual positive changes and Shield-blocked observed zeros; future masks unknown when removed.",target_exhausted_delta="Actual chosen ready/exhausted units give1/0; no zero-fill for inactive/no-target branches.",
                    target_shield_delta="Actual damage onto existing native Shield gives−1 versus0 unshielded/other-family commits.",
                    target_power_hp_delta="Positive vanilla-upgrade attachment; negative area-debuff; real zero changes under other committed effects. Held targeted debuff literals and attached-exhaust bonuses are stresses.",
                    source_exhausted_after="ASH171 actual successful upgrade-defeat→ready sequence vs valid declined played-unit endpoint; other played units remain exhausted.",
                    target_removed="Actual ASH171 chosen ordinary-upgrade defeat positive vs surviving actual chosen/area anchors negative."),
                limitations=["Only48 synthetic public roots from12 actual IDs; no all115/all-state/gameplay semantic claim.",
                             "SEC051 full eventHooks→Experience remains byte-exact but unobserved: all opponent units survive the area−3 effect, verified before and after natively.",
                             "SEC142 full onAttack ability is retained but not executed; this cohort measures play/entry paths only.",
                             "Three held template families, not five independent identities: LAW131/JTL079 grouped; LAW127/ASH228 grouped.",
                             "Numeric literal−5 is beyond training−3; distinguish extrapolation from familiar primitive transfer.",
                             "Two positive JTL217 exhaust contexts come from one source template, not two independent behavioral families.",
                             "Rich native support is planned, not asserted before collection; per-head zero/nonzero support and all failures will be reported.",
                             "PR35 checkpoints are historical controls with different data/support; compare only compatible unchanged input serialization/scales, never imply matched pretraining."])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out-dir",type=Path,default=ROOT);args=ap.parse_args()
    gen=G.PINNED_KESSEL/"compiler/generated";coverage_path=HERE.parents[3]/"experiments/actual-corpus/coverage-v2/actual-corpus-coverage.json"
    plan=build_plan(json.loads((gen/"cards.json").read_text()),json.loads((gen/"runtime-admission.json").read_text()),json.loads(coverage_path.read_text()))
    plan["source_pins"]=[dict(path=str(p),sha256=G.sha(p)) for p in (Path(__file__),HERE/"actual_corpus_native_plan.py",HERE/"grounded_contrast_data.py",coverage_path,COHORT_CONTRACT,*[gen/n for n in ("cards.json","runtime-admission.json","manifest.json","inputs.json","diagnostics.json")])]
    args.out_dir.mkdir(parents=True,exist_ok=True);out=args.out_dir/"native-plan.json";data=json.dumps(plan,indent=2)+"\n"
    if out.exists() and out.read_text()!=data:raise ValueError("preserve frozen plan; choose a new versioned directory")
    if not out.exists():out.write_text(data)
    print(json.dumps(dict(plan=str(out),sha256=G.sha(out),roots=48,max_applies=240,neural_forwards=0,native_applies=0)))


if __name__=="__main__":main()
