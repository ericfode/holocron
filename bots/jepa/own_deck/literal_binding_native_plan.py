"""Small existing-runtime literal/effect qualification bank; preparation only.

Programs and full definitions are immutable. Native offers and settled snapshots
are the only labels; edited-IR neural sensitivities are a separate, unlabelled
diagnostic. No model or native execution is performed by the default command.
"""
import argparse
import copy
import json
import hashlib
from pathlib import Path
import sys
import subprocess

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grounded_contrast_data as G

ROOT = Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments")
CODES = ("SHD_004", "TWI_206")
SCHEMA = "jepa-literal-binding-native/1"
CHOSEN = "friendly_ground"


def contexts():
    rows = []
    for xp in (0, 1):
        for exhausted in (False, True):
            rows.append(dict(id=len(rows), name=f"xp{xp}-exhausted{int(exhausted)}", partition="frozen-native-eval", chosen_code="LOF_256", chosen_xp=xp,
                             ready_resources=2, source_exhausted=False, overrides={CHOSEN: dict(exhausted=exhausted)}))
    for code, power in (("LOF_084", 4), ("SEC_167", 5)):
        rows.append(dict(id=len(rows), name=f"printed-power-{power}", partition="frozen-native-eval", chosen_code=code, chosen_xp=0,
                         ready_resources=2, source_exhausted=False, overrides={}))
    for ready in (0, 1):
        rows.append(dict(id=len(rows), name=f"resources-{ready}", partition="frozen-native-eval", chosen_code="LOF_256", chosen_xp=0,
                         ready_resources=ready, source_exhausted=False, overrides={}))
    return rows


def program_scope(records):
    rows = []
    for r in records:
        total = sum(r["all_side_ability_counts"].values())
        leader = r["side"] == "leader"
        rows.append(dict(code=r["code"], canonical_card_id=r["canonical_card_id"], aliases=r["aliases"],
                         actual_card_role="leader" if leader else "main-unit", selected_ability_path=["abilities", r["side"], r["index"]],
                         all_side_ability_counts=r["all_side_ability_counts"], encoded_abilities=1, additional_unencoded_abilities=total-1,
                         scope="Undeployed leader activated action only; deployed side excluded" if leader else "Selected ordinary-unit activated action only"))
    return dict(rows=rows, vectors=len(rows), leader_vectors=sum(r["actual_card_role"] == "leader" for r in rows),
                main_unit_vectors=sum(r["actual_card_role"] == "main-unit" for r in rows),
                selected_programs=len(rows), total_declared_abilities=sum(sum(r["all_side_ability_counts"].values()) for r in rows),
                whole_card_semantics=False, whole_deck_card_coverage=False,
                aggregation_rule="Leader programs require a separate leader role, never main-list copy counts. Missing event/upgrade/trigger/continuous/deployed-side capabilities remain unknown; no whole-card semantic label.")


def build_plan(catalog, runtime, original_core, fresh_core):
    report = G.inventory(catalog, runtime)
    available = {r["card"]: r for r in report["records"]}
    programs = [copy.deepcopy(next(r for r in fresh_core["programs"] if r["code"] == code)) for code in CODES]
    for r in programs:
        actual = available[r["code"]]
        if r["raw_ability"] != actual["raw_ability"] or r["source_hash"] != actual["sourceHash"] or r["all_side_ability_counts"][r["side"]] != 1:
            raise ValueError("exact complete existing-runtime program/source differs")
    rows = {r["setCode"]: r for r in catalog["cards"]}
    admitted = {r["setCode"] for r in runtime["runtimeAdmittedCards"]}
    helpers = dict(base="ASH_019", ground="LOF_256", space="IBH_022", imperial="IBH_055", creature="TOKEN_BEAST")
    required = set(helpers.values()) | {"LOF_084", "SEC_167"}
    for code in required:
        if code not in admitted:
            raise ValueError("whole helper not already runtime admitted: " + code)
    for code, power in (("LOF_084", 4), ("SEC_167", 5)):
        r, card = rows[code], rows[code]["card"]
        if card["types"] != ["unit"] or card["arena"] != "ground" or card["power"] != power or card["hp"] != 4 or card["keywords"] or any(r["abilities"].values()) or set(card["traits"]) & {"imperial", "creature", "spectre"}:
            raise ValueError("vanilla power4/5 matched helper contract differs")
    selected = sorted(required | set(CODES) | {"TOKEN_EXPERIENCE", "TOKEN_SHIELD", "IBH_053"})
    return dict(schema="literal-binding-native-collection-plan/1", plan_version=2, status="frozen-preparation-no-execution", source_revision=G.REVISION,
                programs=programs, candidate_order=list(G.CANDIDATES), target_names=list(G.TARGETS), chosen_ref=CHOSEN,
                helpers=helpers, contexts=contexts(), expected_cases=16, commits_per_root=1,
                selected_whole_cards=selected, required_native_tokens=["TOKEN_SHIELD", "TOKEN_EXPERIENCE"],
                helper_printed={code: rows[code]["card"] for code in sorted(required)},
                helper_row_sha256={code: G.digest(rows[code]) for code in sorted(required)},
                collector_max_engine_applies=80, campaign_max_engine_applies=80, campaign_max_seconds=60,
                coordinator_outer_apply_ceiling=256, campaign_all_phase_active_seconds=100,
                future_phase_caps=dict(frozen_neural_eval_seconds=20, staged_deck_updates=400, staged_deck_seconds=20,
                                       execution="Separate root authorization/source freeze required; this collector permits only native collection and0updates."),
                max_rss_bytes=1073741824, cpu_threads=1, optimizer_updates=0, paid_jobs=0,
                target_labels="Actual native target prompt membership and independently committed settled snapshots only; no oracle labels from IR or expected thresholds.",
                commit_scope="Only friendly_ground may be committed; every other candidate has observed membership but unobserved transition masks0, even when offered. Every commit starts at untouched prompt.",
                native_setup="Whole admitted definitions only. Existing Experience token fixture sets both token/upgrade links, preserving owner and parent; public snapshot-load roundtrip must be exact. XP changes actual power/HP; no printed-stat override.",
                metrics=dict(resource_boundaries="source availability at ready-resource0/1/2, cost copies on actual commits", effect_routing="same-target XP0/1 x ready/exhausted; cost_resource/xp_delta/target_exhausted_delta", threshold="native TWI206 target membership at current power4 and5; power4 distinguishes<=4 from<=3", availability_and_outcomes_separate=True),
                numeric_contract=dict(context_feature_names=list(G.CONTEXT_FEATURES), candidate_feature_names=list(G.CANDIDATE_FEATURES), target_names=list(G.TARGETS), primary_candidate_slots=list(range(7)), source_candidate_diagnostic_only=True,
                                      fixed_scaling="Saved original checkpoint vocabulary/input/head/literal scalers only; never fit controls or change weights.", replay="Reserve at least2 saved fresh-root replay rows per seed before scoring new controls; correct-ir plus context-only batches at seeds17/29/43:6forwards of18rows total, separate20-second/1-GiB guard, no training."),
                published12_vector_scope=program_scope(original_core["programs"]),
                independent_new_card_gate=dict(status="UNSUPPORTED_NO_TWO_ADMITTED_PROGRAM_INPUT_PAIRS", inventory_actions=41,
                    fixed_parser_vocab_compatible=16, previously_reviewed_identities=14,
                    unused_compatible=[dict(code="ASH_123",reason="Single action requires getPower(source), absent from model globals/other-candidate input; general behavior unsupported"),
                                       dict(code="SHD_087",reason="Two card abilities plus missing getPower(source) input")],
                    action="No coverage/ABI expansion, no replacement cards;16 SHD004/TWI206 roots are conditional literal/effect diagnostics, not two independently new identities."),
                input_freshness_rule="Before scoring, compare normalizedIR+2globals source inputs and normalizedIR+2globals+own26candidate inputs against both prior168 banks. Exact repeats are replay/calibration; report new-only separately. Other helper changes do not create candidate-local independence.",
                qualification_scope="Selected activated-program behavior, not whole-card or whole-deck semantics. SHD004 is an undeployed leader action; TWI206 is an ordinary main-unit action.",
                limitations=["XP grant amount is always1 in these existing programs: routing/attachment behavior, not XP-quantity extrapolation.",
                    "Native XP fixtures legitimately change power and HP together; do not describe independent XP-coordinate intervention.",
                    "Power4/5 vanilla helpers differ in opaque printed identity/aspects/traits outside relevant numeric features; these fields never enter neural inputs. Program pairs use the identical context/candidate.",
                    "No exact SHD threshold2vs3 test, no ordered multi-effect or whole-card semantics claim.",
                    "Unsupported/error/unsettled outcomes remain unknown. No replacement scenario selected after outcomes; preserve all16 roots and failures.",
                    "No engine, card conversion, runtime coverage or existing collector/data/model source is modified."])


def source_available(case, program):
    before, opened, post, menu = case["before"],case.get("sourceOpened"),case.get("postActivation"),case.get("menuAction")
    action=case.get("sourceAction")
    if case.get("source_use_known") is not True or type(case.get("source_use")) is not bool:
        raise ValueError("native source label must be explicit and observed")
    if action is None:
        if any(x is not None for x in (opened,post,menu,case.get("targetPrompt"))) or case["source_use"] or G.action_for(before,case["refs"]["source"]):
            raise ValueError("activation exists without exact native source offer")
        return False
    if action not in G.action_for(before,case["refs"]["source"]) or opened is None or post is None:
        raise ValueError("source activation lacks exact offered tuple/witness")
    G.settled_capture(opened);settled=G.settled_capture(post)
    if menu is not None and (menu not in opened["offeredActions"] or type(menu.get("arg")) is not int or menu["arg"]!=0 or menu.get("label") in ("Attack","Cancel")):
        raise ValueError("selected sole activated ability menu differs")
    if menu is None and post!=opened:raise ValueError("direct activation poststate differs")
    leader_finished=False
    if program["side"]=="leader" and settled:
        leader=post["state"]["players"]["p1"]["leader"]
        leader_finished=leader["id"]==case["refs"]["source"] and leader["deployed"] is False
    available=menu is not None or opened["decision"] in ("AbilityTarget","AbilityNoEffect") or leader_finished
    if available!=case["source_use"]:raise ValueError("source-use confuses attack with selected program")
    if available and not settled and (post["sourceInstance"]!=case["refs"]["source"] or post["abilityProgramPlusOne"]<=0):raise ValueError("unresolved source/program binding differs")
    prompt=case.get("targetPrompt")
    if prompt is not None:
        if prompt!=post or prompt["decision"]!="AbilityTarget":raise ValueError("actual target prompt differs")
        G.settled_capture(prompt)
    return available


def input_novelty(arrays, programs, prior_banks):
    """Exact candidate-local input audit; never inspects outcomes or model scores."""
    def key(program, context, candidate=None):
        parts=[G.digest(G.normalized_program(program)).encode(),np.ascontiguousarray(context,dtype=np.float32).tobytes()]
        if candidate is not None:parts.append(np.ascontiguousarray(candidate,dtype=np.float32).tobytes())
        return hashlib.sha256(b"\0".join(parts)).hexdigest()
    source_keys,candidate_keys=set(),set()
    for data,manifest in prior_banks:
        for i,code in enumerate(data["source_cards"]):
            raw=manifest["programs"][str(code)]["raw_ability"]
            source_keys.add(key(raw,data["context_features"][i]))
            for j in range(8):candidate_keys.add(key(raw,data["context_features"][i],data["candidate_features"][i,j]))
    source_replay=[];candidate_replay=[]
    for i,code in enumerate(arrays["source_cards"]):
        raw=programs[str(code)]["raw_ability"]
        source_replay.append(key(raw,arrays["context_features"][i]) in source_keys)
        candidate_replay.append([key(raw,arrays["context_features"][i],arrays["candidate_features"][i,j]) in candidate_keys for j in range(8)])
    arrays["source_input_is_prior_replay"]=np.asarray(source_replay,np.bool_)
    arrays["candidate_input_is_prior_replay"]=np.asarray(candidate_replay,np.bool_)
    return dict(source_roots_new=int((~arrays["source_input_is_prior_replay"]).sum()),source_roots_replay=int(arrays["source_input_is_prior_replay"].sum()),
                selected_candidate_new=int((~arrays["candidate_input_is_prior_replay"][:,2]).sum()),selected_candidate_replay=int(arrays["candidate_input_is_prior_replay"][:,2].sum()),
                exact_rule="Fixed normalized IR, float32 globals and same candidate26 bytes; status based on input only, never outcome/score.")


def convert_receipt(receipt, plan, catalog):
    if receipt.get("schema") != SCHEMA or receipt.get("sourceRevision") != G.REVISION or receipt.get("collectionPlan") != plan:
        raise ValueError("literal native source/schema/plan differs")
    if receipt.get("selectedWholeCards") != plan["selected_whole_cards"] or receipt.get("selectedCatalogueSha256") != G.native_catalog_hash(catalog, plan["selected_whole_cards"]):
        raise ValueError("selected whole catalogue differs")
    if type(receipt.get("applyCalls")) is not int or not 0 <= receipt["applyCalls"] <= 80:
        raise ValueError("literal native apply budget differs")
    cases = sorted(receipt["cases"], key=lambda c: (c["context_family"], c["card"]))
    if len(cases) != 16 or {(c["card"], c["context_family"]) for c in cases} != {(code, f) for code in CODES for f in range(8)}:
        raise ValueError("all16 fixed roots required")
    rows = {r["setCode"]: r for r in catalog["cards"]}
    programs={p["code"]:p for p in plan["programs"]}
    provenance=receipt.get("provenance",[])
    if len(provenance)!=2:raise ValueError("exact two program witnesses required")
    for code,p in programs.items():
        expected=dict(card=code,sourceHash=p["source_hash"],sourcePath=p["source_path"],abilityPath=["abilities",p["side"],p["index"]],actualUnmodifiedAbility=p["raw_ability"])
        if [r for r in provenance if r.get("card")==code]!=[expected]:raise ValueError("exact complete source program provenance differs")
    x, cf, su, allow, am, ys, ms = [], [], [], [], [], [], []
    for case in cases:
        before, prompt = case["before"], case.get("targetPrompt")
        if not G.settled_capture(before) or before["decision"]!="Window" or case.get("publicSnapshotRoundtripExact") is not True:
            raise ValueError("root must be settled and public-roundtrip exact")
        code=case["card"];context=plan["contexts"][case["context_family"]];chosen=before["projections"][CHOSEN]
        if case["abilityPath"]!=["abilities",programs[code]["side"],programs[code]["index"]] or before["projections"]["source"]["code"]!=code:
            raise ValueError("selected source/path differs")
        c=rows[context["chosen_code"]]["card"]
        if chosen["code"]!=context["chosen_code"] or chosen["owner"]!="p1" or chosen["zone"]!="ground" or not chosen["present"] or not chosen["is_unit"] or chosen["damage"]!=0 or chosen["shield_count"]!=0 or chosen["xp_count"]!=context["chosen_xp"] or chosen["power"]!=c["power"]+context["chosen_xp"] or chosen["hp"]!=c["hp"]+context["chosen_xp"] or chosen["exhausted"]!=context["overrides"].get(CHOSEN,{}).get("exhausted",False):
            raise ValueError("native chosen public fixture differs from declared context")
        if G.ready_resources(before)!=context["ready_resources"] or len(before["state"]["players"]["p1"]["resources"])!=3 or before["projections"]["source"]["exhausted"]:
            raise ValueError("native resource/source public fixture differs")
        x.append([G.ready_resources(before), before["projections"]["source"]["exhausted"]])
        cf.append([G.candidate_vector(before["projections"][slot], case["refs"]["source"], rows) for slot in G.CANDIDATES])
        su.append(float(source_available(case,programs[code])))
        a = [bool(G.action_for(prompt, case["refs"][slot])) if prompt is not None else False for slot in G.CANDIDATES]
        allow.append(a); am.append([prompt is not None]*8)
        y, mask = np.zeros((8,11),np.float32), np.zeros((8,11),np.float32)
        if len(case["queries"]) != 8: raise ValueError("all candidate membership witnesses required")
        for j, query in enumerate(case["queries"]):
            if set(query["targets"])!=set(G.TARGETS) or set(query["target_mask"])!=set(G.TARGETS) or any(type(v) is not bool for v in query["target_mask"].values()):
                raise ValueError("explicit complete native label coordinate masks required")
            if query["chosen_ref"] != G.CANDIDATES[j] or query["chosen_id"] != case["refs"][G.CANDIDATES[j]]:
                raise ValueError("candidate references/order differ")
            if query["target_mask"]["source_use"] is not True or query["targets"]["source_use"]!=case["source_use"]:
                raise ValueError("branch source label differs from once-per-root witness")
            if G.CANDIDATES[j] == CHOSEN:
                y[j], mask[j] = G.validate_query(case,query,CHOSEN,a[j])
            elif query["after"] is not None or query["targetAction"] is not None or query.get("engineError") is not None or any(query["target_mask"][n] for n in G.TARGETS[2:]):
                raise ValueError("unchosen transition must stay unobserved")
            if query["target_mask"]["target_allowed"] != (prompt is not None) or (prompt is not None and query["targets"]["target_allowed"] != a[j]):
                raise ValueError("membership differs from native offers")
        ys.append(y); ms.append(mask)
    arrays=dict(context_features=np.asarray(x,np.float32), candidate_features=np.asarray(cf,np.float32), candidate_mask=np.ones((16,8),np.float32),
                primary_candidate_mask=np.tile([1,1,1,1,1,1,1,0],(16,1)).astype(np.float32),source_diagnostic_mask=np.tile([0,0,0,0,0,0,0,1],(16,1)).astype(np.float32),
                source_use=np.asarray(su,np.float32),source_use_mask=np.ones(16,np.float32),candidate_allowed=np.asarray(allow,np.float32),candidate_allowed_mask=np.asarray(am,np.float32),
                targets=np.asarray(ys,np.float32),target_mask=np.asarray(ms,np.float32),source_cards=np.asarray([c["card"] for c in cases]),state_families=np.asarray([c["context_family"] for c in cases],np.int64),eval_idx=np.arange(16,dtype=np.int64))
    for f in range(8):
        a,b=np.flatnonzero(arrays["state_families"]==f)
        if not np.array_equal(arrays["context_features"][a],arrays["context_features"][b]) or not np.array_equal(arrays["candidate_features"][a,:7],arrays["candidate_features"][b,:7]):
            raise ValueError("same-context primary program inputs differ")
    manifest=dict(schema="jepa-literal-binding-data/1",programs={r["code"]:r for r in plan["programs"]},plan=plan,records=cases,
                  context_feature_names=list(G.CONTEXT_FEATURES),candidate_feature_names=list(G.CANDIDATE_FEATURES),target_names=list(G.TARGETS),
                  source_revision=G.REVISION,native_apply_calls=receipt["applyCalls"],selected_catalogue_sha256=receipt["selectedCatalogueSha256"],
                  semantic_scope="Selected program controls only; no training or whole-card/deck semantic qualification.")
    return arrays,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir",type=Path,default=ROOT/"literal-binding")
    parser.add_argument("--native-receipt",type=Path)
    parser.add_argument("--plan-file",type=Path)
    args=parser.parse_args()
    gen=G.PINNED_KESSEL/"compiler/generated"
    revision=subprocess.check_output(["git","--no-optional-locks","-C",str(G.PINNED_KESSEL),"rev-parse","HEAD"],text=True).strip()
    if revision!=G.REVISION:raise ValueError("pinned native revision differs")
    subprocess.run(["git","--no-optional-locks","-C",str(G.PINNED_KESSEL),"diff","--quiet","HEAD","--","compiler/generated","crates/kessel","Cargo.toml","Cargo.lock"],check=True)
    catalog=json.loads((gen/"cards.json").read_text());runtime=json.loads((gen/"runtime-admission.json").read_text())
    args.out_dir.mkdir(parents=True,exist_ok=True)
    path=args.plan_file or args.out_dir/"native-plan.json"
    if args.native_receipt:
        plan=json.loads(path.read_text())
        if any(G.sha(p["path"])!=p["sha256"] for p in plan["source_pins"]):raise ValueError("frozen plan source pins differ")
        receipt=json.loads(args.native_receipt.read_text());arrays,manifest=convert_receipt(receipt,plan,G.assembled_catalog(gen));out=args.out_dir/"literal-binding.npz"
        if receipt["collectionPlanSha256"]!=G.sha(path):raise ValueError("native collection plan byte hash differs")
        prior=[]
        for stem in (ROOT/"grounded-contrast/grounded-contrast",ROOT/"transition-replication/transition-replication"):
            with np.load(stem.with_suffix(".npz"),allow_pickle=False) as bank:prior.append(({k:v.copy() for k,v in bank.items()},json.loads(stem.with_suffix(".manifest.json").read_text())))
        manifest["input_novelty"]=input_novelty(arrays,manifest["programs"],prior)
        if out.exists() or (args.out_dir/"literal-binding.manifest.json").exists():raise ValueError("conversion outputs already exist; preserve measured artifacts")
        np.savez_compressed(out,**arrays)
        manifest.update(artifact=dict(path=str(out),sha256=G.sha(out)),native_receipt=dict(path=str(args.native_receipt),sha256=G.sha(args.native_receipt)))
        (args.out_dir/"literal-binding.manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    else:
        plan=build_plan(catalog,runtime,json.loads((ROOT/"grounded-contrast/core-programs.json").read_text()),json.loads((ROOT/"transition-replication/core-programs.json").read_text()))
        plan["source_pins"]=[dict(path=str(p),sha256=G.sha(p)) for p in (Path(__file__),HERE/"grounded_contrast_data.py",gen/"cards.json",gen/"runtime-admission.json",gen/"manifest.json")]
        data=json.dumps(plan,indent=2)+"\n"
        if path.exists() and path.read_text()!=data:raise ValueError("frozen plan already exists; preserve bytes and use an explicit new version")
        if not path.exists():path.write_text(data)
    print(json.dumps(dict(plan=str(path),sha256=G.sha(path),native_calls=0,neural_forwards=0)))


if __name__=="__main__":main()
