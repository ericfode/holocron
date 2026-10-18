"""Reviewed native proof functions copied with eight-root/32-apply schemas.

No process, engine or accounting side effects. The source test reconstructs the
exact predecessor-function delta; the supervisor pins both implementations.
"""
import json
from pathlib import Path

def settled_capture(capture):
    if type(capture.get("terminal"))is not bool:return False
    if capture["terminal"]:return capture.get("settled")is True
    witness=capture.get("settlement",{})
    integer_fields=("ability_program","death_depth","death_pending","death_window","pending_programs",
                    "pending_triggers","after_attack_triggers","after_attack_programs")
    return (capture.get("settled")is True and witness.get("decision")=="Window"
        and all(type(witness.get(k))is int and witness[k]==0 for k in integer_fields)
        and witness.get("event_group_active")is False and witness.get("support_pending")is False)

def trace_exposure(path,launched):
    """Keep known-prefix call count separate from charged failed reservation."""
    p=Path(path)
    if not p.exists():return dict(known_calls=0,verified=not launched,reason=None if not launched else "collector launched without readable journal")
    count=0
    try:
        rows=p.read_text().splitlines()
        if not rows:raise ValueError("empty native journal")
        header=json.loads(rows[0])
        if header.get("schema")!="jepa-ability-correction-apply-journal/1"or header.get("maxApplyCalls")!=32:raise ValueError("native journal header differs")
        for line in rows[1:]:
            row=json.loads(line)
            if row.get("phase")=="beforeApply":
                if row.get("applyCall")!=count+1:raise ValueError("nonsequential durable native intent")
                count+=1
        return dict(known_calls=count,verified=True,reason=None)
    except Exception as error:
        return dict(known_calls=count,verified=False,reason=str(error))

def verify_success_journal(path,raw):
    rows=[json.loads(line)for line in Path(path).read_text().splitlines()]
    if not rows or rows[0].get("planSha256")!=raw["collectionPlanSha256"]:raise ValueError("journal full plan pin differs")
    before=[r["applyCall"]for r in rows if r.get("phase")=="beforeApply"]
    after=[r["applyCall"]for r in rows if r.get("phase")=="afterApply"]
    contexts=[r["case"]["world_id"]for r in rows if r.get("phase")=="contextComplete"]
    if before!=list(range(1,raw["applyCalls"]+1))or after!=before or contexts!=list(range(8))or any(r.get("phase")=="applyError"for r in rows):
        raise ValueError("completed journal must contain every successful apply and all8 roots")
    return dict(before_apply_intents=len(before),successful_after_apply=len(after),completed_contexts=len(contexts))

def verify_complete_cases(raw,manifest,journal_path):
    """Full actual applied chain, per-world caps and settled endpoints precede admission."""
    frozen=json.loads(Path(manifest["collection_plan"]["path"]).read_text())
    worlds=frozen["worlds"];cases=raw.get("cases")
    if raw.get("schema")!="jepa-ability-correction-native/1"or raw.get("collectionComplete")is not True:
        raise ValueError("native completed collection schema required")
    if len(worlds)!=8 or not isinstance(cases,list)or len(cases)!=8:
        raise ValueError("exact full8 native roots required")
    if type(raw.get("applyCalls"))is not int or not 0<raw["applyCalls"]<=32:
        raise ValueError("native global32 apply bound required")
    validation=raw.get("fixtureValidation")
    if not isinstance(validation,list)or len(validation)!=8:raise ValueError("all8 pre-apply fixture proofs required")
    for world,case,witness in zip(worlds,cases,validation):
        if witness.get("world_id")!=world["id"]or witness.get("card")!=world["source_code"]or witness.get("before")!=case.get("before"):
            raise ValueError("fixture proof differs from actual initial world")
        if witness.get("publicSnapshotRoundtripExact")is not True or witness.get("legalActionsRoundtripExact")is not True or witness.get("applyCalls")!=0 or witness.get("actionsApplied")!=0:
            raise ValueError("fixture roundtrip proof failed or applied actions")
    rows=[json.loads(line)for line in Path(journal_path).read_text().splitlines()]
    complete=[r["case"]for r in rows if r.get("phase")=="contextComplete"]
    if complete!=cases:raise ValueError("journal/raw native case values differ")
    before=[r for r in rows if r.get("phase")=="beforeApply"]
    after=[r for r in rows if r.get("phase")=="afterApply"]
    step_index=0
    for expected_id,(world,case)in enumerate(zip(worlds,cases)):
        if type(case.get("world_id"))is not int or case["world_id"]!=expected_id or world["id"]!=expected_id:
            raise ValueError("full8 native world IDs differ")
        for key,plan_key in(("card","source_code"),("cohort","cohort"),("partition","partition"),
                            ("template_id","template_id"),("state_family","state_family"),("observation_mode","observation_mode"),("selection_mode","selection_mode"),("scenario","scenario")):
            if json.dumps(case.get(key),sort_keys=True)!=json.dumps(world[plan_key],sort_keys=True):raise ValueError("native case/frozen world binding differs: "+key)
        if case.get("observation_refs")!=world["observation_refs"]or case.get("declared_intent",{}).get("ref")!=world["intent_ref"]:
            raise ValueError("native observation/intent roles differ")
        if type(case["declared_intent"].get("requires_target"))is not bool or case["declared_intent"]["requires_target"]!=world["requires_target"]:
            raise ValueError("native required target contract differs")
        if case["declared_intent"].get("id")!=case.get("refs",{}).get(world["intent_ref"]):
            raise ValueError("native intended physical role differs")
        steps=case.get("steps")
        if not isinstance(steps,list)or type(case.get("applyCalls"))is not int or not 1<=len(steps)==case["applyCalls"]<=world["max_applies"]:
            raise ValueError("native per-world applied chain/bound differs")
        observation_only=case.get("intentResolution")=="unoffered-observation-only"
        if case.get("engineError")is not None:raise ValueError("native engine error blocks admission")
        if observation_only:
            if case.get("completion")!="unoffered-observation-only"or case.get("terminalClassification")!="unoffered-prompt-only"or case.get("final")is not None:
                raise ValueError("invalid unoffered observation-only terminal")
        elif case.get("completion")!="settled"or not settled_capture(case.get("final",{})):
            raise ValueError("unsettled committed/cancelled endpoint blocks admission")
        if steps[0].get("stage")!="play-own-hand"or steps[0].get("action")!=case.get("playAction")or steps[0].get("before")!=case.get("before"):
            raise ValueError("native source play witness differs")
        if case["playAction"].get("card")!=case.get("refs",{}).get("source"):
            raise ValueError("native played source identity differs")
        endpoint=case.get("targetPrompt")if observation_only else case["final"]
        if steps[-1].get("after")!=endpoint or case.get("lastObserved")!=endpoint:
            raise ValueError("native observed endpoint differs from actual applied chain")
        resolution=case.get("intentResolution");prompt=case.get("targetPrompt")
        if not isinstance(prompt,dict)or prompt.get("decision")!="AbilityTarget":raise ValueError("actual target prompt required")
        intended=case["declared_intent"]["id"]
        offers=[a for a in prompt.get("offeredActions",[])if a.get("card")==intended]
        if len(offers)>1 or case.get("intentOffered")is not bool(offers):raise ValueError("intended membership is not native observed")
        commits=[z for z in steps if z.get("stage")=="chosen-target"]
        dones=[z for z in steps if z.get("stage")=="commit-one-selection"]
        declines=[z for z in steps if z.get("stage")=="decline-unoffered-target"]
        if resolution=="committed":
            if case.get("intendedTargetCommitted")is not True or len(commits)!=1 or declines or case.get("targetAction")not in offers or commits[0]["action"]!=case["targetAction"]:
                raise ValueError("native intended choice missing or substituted")
            if world["selection_mode"]=="exactly-one-upTo":
                witness=case.get("selectionWitness",{})
                if witness.get("abilitySelection")!=[intended]or witness.get("abilityProgramPlusOne")!=prompt.get("abilityProgramPlusOne")or witness.get("abilityPc")!=prompt.get("abilityPc"):
                    raise ValueError("upTo exactly-one native selection witness differs")
                if len(dones)!=1 or dones[0]["before"]!=witness or dones[0]["action"]!=case.get("selectionDoneAction") or dones[0]["action"].get("arg")!="done" or dones[0]["action"].get("label")!="Done":
                    raise ValueError("upTo exactly-one Done commitment missing")
            elif dones or case.get("selectionWitness")is not None or case.get("selectionDoneAction")is not None:
                raise ValueError("single target acquired fictional multiple selection")
        elif resolution=="unoffered-declined":
            if offers or commits or dones or len(declines)!=1 or case.get("intendedTargetCommitted")is not False or case.get("targetAction")is not None:
                raise ValueError("invalid intent was substituted or committed")
            action=declines[0]["action"]
            if action!=case.get("declineAction")or action.get("arg")!="cancel"or action.get("label")!="Cancel"or action.get("card")is not None:
                raise ValueError("unoffered intention requires exact actual Cancel")
        elif resolution=="unoffered-observation-only":
            if offers or commits or dones or declines or case.get("targetAction")is not None or case.get("declineAction")is not None or case.get("intendedTargetCommitted")is not False:
                raise ValueError("unoffered observation-only branch acquired an action/future")
            if any(a.get("label")=="Cancel"and a.get("arg")=="cancel"and a.get("card")is None for a in prompt.get("offeredActions",[])):
                raise ValueError("available actual Cancel must be executed")
        else:raise ValueError("no reviewed intent resolution")
        for local_index,step in enumerate(steps):
            if step.get("action")not in step.get("before",{}).get("offeredActions",[]):
                raise ValueError("native applied action was not offered")
            if local_index and steps[local_index-1]["after"]!=step["before"]:
                raise ValueError("native applied chain has a state gap")
            context=f"world-{expected_id}-{world['source_code']}"
            if step_index>=len(before)or step_index>=len(after):raise ValueError("native journal applied chain missing")
            left,right=before[step_index],after[step_index]
            if (left.get("before")!=step["before"]or left.get("offeredAction")!=step["action"]
                or right.get("after")!=step["after"]or left.get("context")!=context or right.get("context")!=context
                or left.get("branch")!=step["stage"]or right.get("branch")!=step["stage"]):
                raise ValueError("native journal action/state binding differs")
            step_index+=1
    if step_index!=raw["applyCalls"]or len(before)!=step_index or len(after)!=step_index:
        raise ValueError("native case/journal total apply count differs")
    return dict(completed_roots=8,actual_applies=step_index,all_per_world_bounds_preserved=True,
        all_intents_committed_or_native_unoffered_observed=True,all_committed_cancelled_endpoints_settled=True,unoffered_prompt_only_future_unknown=True,journal_raw_action_state_chains_exact=True)
