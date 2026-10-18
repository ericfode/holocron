"""New128-call actual-corpus semantic-discrimination allocation; default is read-only source preflight."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import uuid
HERE=Path(__file__).resolve().parent
CRATE=HERE
MAX_BYTES=1024**3
INTERVAL=.05
ACCOUNTING_SOURCE=HERE.parent/"semantic_discrimination_accounting.py"
ACCOUNTING_SHA256="15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d"
SPEC_PATH=HERE.parents[4]/"experiments/semantic-discrimination-v1/campaign-spec.json"
MANIFEST_PATH=SPEC_PATH.parent/"metadata-1/native-source-manifest.json"
CARGO_EXECUTABLE="/Users/ericfode/.cargo/bin/cargo"
TARGET_DIR=HERE.parents[4]/"experiments/typed-ir-microprobe/target"
ENGINE_SOURCE=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source")
STAGES={"build":(10.,0),"native":(45.,128)}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def count_applies(path):
    """Count durable before-apply intent records, including failed engine calls."""
    if not Path(path).exists():
        return 0
    calls = []
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        if row.get('phase') == 'beforeApply':
            calls.append(row['applyCall'])
    if calls != list(range(1, len(calls) + 1)):
        raise RuntimeError('nonsequential durable apply journal')
    return len(calls)

def memory_sample(receipt, readings, supervisor_pid, supervisor_peak):
    """Peak of concurrent live RSS sums; past PID peaks are metadata only."""
    if supervisor_pid not in readings or any(type(v) is not int or v < 0 for v in readings.values()):
        raise RuntimeError('live owned RSS reading unavailable/invalid')
    for pid, value in readings.items():
        key = str(pid)
        receipt['observed_per_pid_peak_bytes'][key] = max(value, receipt['observed_per_pid_peak_bytes'].get(key, 0))
    key = str(supervisor_pid)
    receipt['observed_per_pid_peak_bytes'][key] = max(supervisor_peak, receipt['observed_per_pid_peak_bytes'].get(key, 0))
    live_sum = sum(readings.values())
    receipt['observed_live_sum_bytes'] = live_sum
    peak = max(live_sum, receipt.get('observed_peak_live_sum_bytes', 0))
    receipt['observed_peak_live_sum_bytes'] = peak
    receipt['observed_conservative_peak_sum_bytes'] = peak
    return peak

def final_memory_bound(peak_live_sum, supervisor_peak, max_single_child_peak):
    """Rusage supplements sampling; never sum sequential historical child peaks."""
    return max(peak_live_sum, supervisor_peak + max_single_child_peak)

def read_owned_rss(receipt,pids,rss,supervisor_pid,elapsed_seconds):
    """Only confirmed vanished owned PIDs may be skipped, with receipt evidence."""
    readings={supervisor_pid:rss(supervisor_pid)}
    for pid in pids:
        try:
            readings[pid]=rss(pid)
        except OSError as exc:
            if exc.errno!=3:raise
            receipt.setdefault('exited_owned_pid_skips',[]).append(dict(pid=pid,errno=exc.errno,
                error=str(exc),elapsed_seconds=elapsed_seconds))
    return readings

def process_readers():
    if sys.platform != 'darwin':
        raise RuntimeError('verified macOS owned-group RSS guard required')
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listpids.restype = ctypes.c_int
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int

    def rss(pid):
        buf = ctypes.create_string_buffer(96)
        got = lib.proc_pidinfo(pid, 4, 0, buf, 96)
        if got != 96:
            raise OSError(ctypes.get_errno(), f'owned PID {pid} RSS unavailable ({got})')
        return ctypes.c_uint64.from_buffer(buf, 8).value

    def members(pgid):
        buf = (ctypes.c_int * 4096)()
        count = lib.proc_listpids(2, pgid, buf, ctypes.sizeof(buf))
        if count < 0 or count % 4 or count >= ctypes.sizeof(buf):
            raise RuntimeError('owned group inventory unavailable/truncated')
        return sorted((pid for pid in buf[:count // 4] if pid > 0))
    return (rss, members)

def build_environment(target_dir):
    """Restore the prior cached dev profile; one Cargo/jobserver build worker."""
    env=os.environ.copy()
    allowed={
        'RUSTFLAGS': ('',), 'CARGO_ENCODED_RUSTFLAGS': ('',),
        'CARGO_PROFILE_DEV_CODEGEN_UNITS': ('',),
        'CARGO_PROFILE_DEV_DEBUG': ('', '0'),
        'CARGO_PROFILE_DEV_INCREMENTAL': ('', 'false', '0'),
        'CARGO_INCREMENTAL': ('', '0', 'false'),
        'CARGO_PROFILE_DEV_OPT_LEVEL': ('', '0'),
        'CARGO_PROFILE_DEV_DEBUG_ASSERTIONS': ('', 'true'),
        'CARGO_PROFILE_DEV_OVERFLOW_CHECKS': ('', 'true'),
        'CARGO_PROFILE_DEV_PANIC': ('', 'unwind'),
        'SWU_RULES_CATALOGUE': ('',),
        'RUSTC': ('',), 'RUSTC_WRAPPER': ('',), 'RUSTC_WORKSPACE_WRAPPER': ('',),
        'CARGO_BUILD_RUSTC': ('',), 'CARGO_BUILD_RUSTC_WRAPPER': ('',), 'CARGO_BUILD_RUSTFLAGS': ('',),
    }
    for key,values in allowed.items():
        if key in env and env[key] not in values:
            raise ValueError('unfrozen compiler profile override: '+key)
    # Absence restores the saved nonincremental default and rustflags[] fingerprint.
    # The cached rlib contains16 codegen objects;256 would be an inaccurate claim.
    # No unrelated nonempty flag is removed: the whitelist above rejects it.
    for key in ('CARGO_PROFILE_DEV_CODEGEN_UNITS','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','SWU_RULES_CATALOGUE'):
        env.pop(key,None)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
        env[key]='1'
    env.update(CARGO_BUILD_JOBS='1', CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_DEV_INCREMENTAL='false',
               CARGO_TARGET_DIR=str(target_dir),CARGO_NET_OFFLINE='true')
    return env

def pin(path):
    p=Path(path).resolve();return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def child_descriptors(campaign_root):
    root=Path(campaign_root).resolve();binary=TARGET_DIR/"debug/semantic-discrimination-native-collector"
    return dict(build=dict(argv=[CARGO_EXECUTABLE,"build","--offline","--locked","--manifest-path",str(CRATE/"Cargo.toml"),"--bin","semantic-discrimination-native-collector","-j","1"],outputs=[str(root/"native-build-1"),str(binary)]),
        native=dict(argv=[str(binary),str(root/"native-attempt-1/native-receipt.json")],outputs=[str(root/"native-attempt-1")]))


def write_source_manifest(plan_path,out_path,campaign_root,source_freeze_commit):
    """Metadata worker only: byte pins and exclusive JSON; no subprocess/engine."""
    root=Path(campaign_root).resolve();plan_path=Path(plan_path).resolve(strict=True);out=Path(out_path).resolve()
    if out.exists():raise FileExistsError("new external native source manifest required")
    if out!=root/"metadata-1/native-source-manifest.json"or plan_path!=root/"native-plan.json":
        raise ValueError("generated native plan/manifest belong to exact declared metadata stage outputs")
    if not isinstance(source_freeze_commit,str)or len(source_freeze_commit)!=40 or any(c not in"0123456789abcdef"for c in source_freeze_commit):
        raise ValueError("coordinator-attested40hex source commit required")
    plan=json.loads(plan_path.read_text());worlds=plan["worlds"]
    if len(worlds)!=33 or [w["id"]for w in worlds]!=list(range(33))or any(type(w["max_applies"])is not int or not 1<=w["max_applies"]<=4 for w in worlds):
        raise ValueError("frozen33-root per-root4 global128 contract differs")
    if sha(ACCOUNTING_SOURCE)!=ACCOUNTING_SHA256:raise ValueError("shared accounting source differs")
    projects=[CRATE/name for name in("Cargo.toml","Cargo.lock","src/main.rs","supervise.py","test_guard.py","README.md")]+[ACCOUNTING_SOURCE]
    engine_files=[ENGINE_SOURCE/"Cargo.toml",ENGINE_SOURCE/"Cargo.lock"]
    engine_files+=[p for p in(ENGINE_SOURCE/"crates/kessel").rglob("*")if p.is_file()and"target"not in p.parts]
    engine_files+=[p for p in(ENGINE_SOURCE/"compiler/generated").rglob("*.json")if p.is_file()]
    pins={str(Path(p).resolve()):pin(p)for p in engine_files+[plan_path,Path(CARGO_EXECUTABLE)]}
    target=TARGET_DIR/"debug"
    preserved=[pin(target/name)for name in("binding-transfer-native-collector","binding-transfer-fixture-validator")]
    expected={"binding-transfer-native-collector":"f7bdbbef31a08aaeb4c3fb28be04bcece3a82782849fbc829b98ba59922dbaeb","binding-transfer-fixture-validator":"b87a950a132f0e88b1edf7a9f7d83257306f68cc2d15184f11271df3691060ad"}
    if any(v["sha256"]!=expected[Path(v["path"]).name]for v in preserved):raise ValueError("original protected binaries differ")
    descriptors=child_descriptors(root)
    manifest=dict(schema="jepa-semantic-discrimination-native-source/1",status="metadata-generated-awaiting-root-stage-GO",source_commit=source_freeze_commit,
        engine_source_revision="c7ee39554901278cee70f61fd8b26fb1920696b3",collection_plan=pin(plan_path),project_files=[pin(p)for p in projects],
        pinned_execution_inputs=[pins[p]for p in sorted(pins)],accounting=pin(ACCOUNTING_SOURCE),campaign_ledger=str(root/"campaign-ledger.jsonl"),
        cargo_executable=CARGO_EXECUTABLE,cargo_target_dir=str(TARGET_DIR),stage_output_dirs={k:v["outputs"][0]for k,v in descriptors.items()},
        expected_cases=33,collector_max_engine_applies=128,max_applies_per_root=4,native_build_seconds=10,native_collect_seconds=45,
        new_binary="semantic-discrimination-native-collector",preserved_binaries=preserved,physical_shield_instances_required=0,
        complete_rows_preserved=True,support_only_shield=True,up_to_cardinality_scope="Exactly one intended target followed by actual Done; no multi-target-cardinality claim.",
        reviewed_terminal_classes=["settled-committed","settled-cancelled","unoffered-prompt-only"],
        unknown_scope="Unselected targets are actual observed endpoints only after a successful committed action; unoffered-prompt-only branches have no future labels.",
        compiler_profile=dict(opt_level=0,debug=0,incremental=False,codegen_override=None,rustflags=[],cargo_workers=1,offline=True,locked=True,os_cpu_affinity=False),
        sampled_rss_stop_bytes=MAX_BYTES,cpu_workers=1,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,
        root_go_required=True,no_retries=True,full_fixture_validation_before_first_apply=True,metadata_only_writer=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x")as f:json.dump(manifest,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
    return dict(manifest=pin(out),plan=pin(plan_path),child_descriptors=descriptors,science_performed=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0))


def load_accounting(spec_path):
    if sha(ACCOUNTING_SOURCE)!=ACCOUNTING_SHA256:raise ValueError("shared accounting source pin changed")
    spec=importlib.util.spec_from_file_location("semantic_discrimination_native_accounting",ACCOUNTING_SOURCE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.Campaign(spec_path)


def preflight(manifest_path):
    manifest=json.loads(Path(manifest_path).read_text())
    for item in manifest["pinned_execution_inputs"]:
        if pin(item["path"])!=item:raise ValueError("pinned input changed: "+item["path"])
    for item in manifest["project_files"]:
        p=Path(item["path"])
        if not p.is_absolute():p=HERE/p
        if sha(p)!=item["sha256"]or p.stat().st_size!=item["bytes"]:raise ValueError("collector source changed: "+item["path"])
    if manifest["accounting"]["sha256"]!=ACCOUNTING_SHA256:raise ValueError("accounting manifest differs")
    verify_preserved_binaries(manifest)
    return manifest


def trace_exposure(path,launched):
    """Keep known-prefix call count separate from charged failed reservation."""
    p=Path(path)
    if not p.exists():return dict(known_calls=0,verified=not launched,reason=None if not launched else "collector launched without readable journal")
    count=0
    try:
        rows=p.read_text().splitlines()
        if not rows:raise ValueError("empty native journal")
        header=json.loads(rows[0])
        if header.get("schema")!="jepa-semantic-discrimination-apply-journal/1"or header.get("maxApplyCalls")!=128:raise ValueError("native journal header differs")
        for line in rows[1:]:
            row=json.loads(line)
            if row.get("phase")=="beforeApply":
                if row.get("applyCall")!=count+1:raise ValueError("nonsequential durable native intent")
                count+=1
        return dict(known_calls=count,verified=True,reason=None)
    except Exception as error:
        return dict(known_calls=count,verified=False,reason=str(error))


def verify_no_physical_shields(raw):
    """The added definition is constructor support, never an experimental token."""
    captures=0;projections=0
    def scan_state(value):
        if isinstance(value,dict):
            if value.get("setCode")=="TOKEN_SHIELD"or value.get("code")=="TOKEN_SHIELD":
                raise ValueError("physical Shield instance in authored fixture capture")
            for child in value.values():scan_state(child)
        elif isinstance(value,list):
            for child in value:scan_state(child)
    def walk(value):
        nonlocal captures,projections
        if isinstance(value,dict):
            if "state"in value and"projections"in value:
                captures+=1
                if not isinstance(value["projections"],dict):raise ValueError("authored fixture projections missing")
                scan_state(value["state"])
                for p in value["projections"].values():
                    if p is None:continue
                    if not isinstance(p,dict)or type(p.get("shield_count"))is not int or p["shield_count"]!=0:
                        raise ValueError("nonzero or unknown Shield count in authored fixture capture")
                    projections+=1;scan_state(p)
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    # Do not scan catalogue metadata: the exact support definition belongs there.
    walk(raw.get("cases"))
    if not captures or not projections:raise ValueError("authored physical-token proof has no captures")
    return dict(physical_shield_instances=0,captures_checked=captures,projections_checked=projections,
                scope="All raw case captures, including fixture query, before, steps, target prompt, final and last observed; native state nested attachments and projection counts.")


def verify_fixture_privacy(raw):
    captures=0
    def walk(value):
        nonlocal captures
        if isinstance(value,dict):
            if isinstance(value.get("state"),dict)and isinstance(value.get("projections"),dict):
                captures+=1;players=value["state"].get("players",{})
                if set(players)!={"p1","p2"}:raise ValueError("two public fixture seats required")
                if any(players[k].get("deck")!=[] for k in("p1","p2"))or players["p2"].get("hand")!=[]or players["p2"].get("resources")!=[]:
                    raise ValueError("hidden/opponent-private fixture piles must remain empty")
                source=value["projections"].get("source",{}).get("id")
                if len(players["p1"].get("hand",[]))>1 or any(c.get("id")!=source for c in players["p1"].get("hand",[])):
                    raise ValueError("only declared source may occupy own focus hand")
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    walk(raw.get("fixtureValidation"));walk(raw.get("cases"))
    if not captures:raise ValueError("nonvacuous public capture privacy proof required")
    return dict(captures_checked=captures,hidden_draw_cards=0,opponent_hand_cards=0,opponent_resources=0,
        public_discards="Actual observed defeat endpoints are public; no private identities supplied.")


def verify_frozen_plan(raw,manifest,path=None):
    path=Path(manifest["collection_plan"]["path"])if path is None else Path(path)
    expected=manifest["collection_plan"];actual=pin(path)
    if actual["sha256"]!=expected["sha256"]or actual["bytes"]!=expected["bytes"]:
        raise ValueError("loaded frozen collection plan byte pin differs")
    frozen=json.loads(path.read_text())
    if raw.get("collectionPlanSha256")!=expected["sha256"]or raw.get("collectionPlan")!=frozen:
        raise ValueError("native full collection plan differs from frozen input")
    if json.dumps(raw["collectionPlan"],sort_keys=True,allow_nan=False)!=json.dumps(frozen,sort_keys=True,allow_nan=False):
        raise ValueError("native full collection plan value types differ")
    return dict(full_plan_matches_frozen=True,collection_plan_sha256=expected["sha256"])


def verify_success_journal(path,raw):
    rows=[json.loads(line)for line in Path(path).read_text().splitlines()]
    if not rows or rows[0].get("planSha256")!=raw["collectionPlanSha256"]:raise ValueError("journal full plan pin differs")
    before=[r["applyCall"]for r in rows if r.get("phase")=="beforeApply"]
    after=[r["applyCall"]for r in rows if r.get("phase")=="afterApply"]
    contexts=[r["case"]["world_id"]for r in rows if r.get("phase")=="contextComplete"]
    if before!=list(range(1,raw["applyCalls"]+1))or after!=before or contexts!=list(range(33))or any(r.get("phase")=="applyError"for r in rows):
        raise ValueError("completed journal must contain every successful apply and all33 roots")
    return dict(before_apply_intents=len(before),successful_after_apply=len(after),completed_contexts=len(contexts))


def verify_preserved_binaries(manifest):
    expected=manifest["preserved_binaries"]
    names={Path(p["path"]).name for p in expected}
    if len(expected)!=2 or names!={"binding-transfer-native-collector","binding-transfer-fixture-validator"}:
        raise ValueError("both prior collector and fixture-validator binary pins required")
    for item in expected:
        if pin(item["path"])!=item:raise ValueError("prior binary changed: "+item["path"])
    return dict(prior_binaries_unchanged=True,pins=expected)


def settled_capture(capture):
    if type(capture.get("terminal"))is not bool:return False
    if capture["terminal"]:return capture.get("settled")is True
    witness=capture.get("settlement",{})
    integer_fields=("ability_program","death_depth","death_pending","death_window","pending_programs",
                    "pending_triggers","after_attack_triggers","after_attack_programs")
    return (capture.get("settled")is True and witness.get("decision")=="Window"
        and all(type(witness.get(k))is int and witness[k]==0 for k in integer_fields)
        and witness.get("event_group_active")is False and witness.get("support_pending")is False)


def verify_complete_cases(raw,manifest,journal_path):
    """Full actual applied chain, per-world caps and settled endpoints precede admission."""
    frozen=json.loads(Path(manifest["collection_plan"]["path"]).read_text())
    worlds=frozen["worlds"];cases=raw.get("cases")
    if raw.get("schema")!="jepa-semantic-discrimination-native/1"or raw.get("collectionComplete")is not True:
        raise ValueError("native completed collection schema required")
    if len(worlds)!=33 or not isinstance(cases,list)or len(cases)!=33:
        raise ValueError("exact full33 native roots required")
    if type(raw.get("applyCalls"))is not int or not 0<raw["applyCalls"]<=128:
        raise ValueError("native global128 apply bound required")
    validation=raw.get("fixtureValidation")
    if not isinstance(validation,list)or len(validation)!=33:raise ValueError("all33 pre-apply fixture proofs required")
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
            raise ValueError("full33 native world IDs differ")
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
    return dict(completed_roots=33,actual_applies=step_index,all_per_world_bounds_preserved=True,
        all_intents_committed_or_native_unoffered_observed=True,all_committed_cancelled_endpoints_settled=True,unoffered_prompt_only_future_unknown=True,journal_raw_action_state_chains_exact=True)


def build_binary_proof(records,binary,verify=True):
    for row in reversed(records):
        if row["event"]=="stage-finish"and row["data"]["stage"]=="build"and row["data"]["status"]=="completed":
            for proof in row["data"].get("proofs",[]):
                if proof.get("path")==str(binary.resolve()):
                    if verify and pin(binary)!=proof:raise ValueError("built collector binary changed before native collection")
                    return proof
    raise ValueError("successful build binary proof required before collection")


def cleanup_owned(proc,pgid,members,receipt):
    """Any uncertain kill/wait/group inventory preserves the pending lease."""
    verified=True;errors=receipt.setdefault("cleanup_errors",[])
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    except BaseException as error:
        verified=False;errors.append(dict(operation="kill-owned-group",error=type(error).__name__+": "+str(error)))
    try:proc.wait(timeout=2)
    except BaseException as error:
        verified=False;errors.append(dict(operation="wait-owned-leader",error=type(error).__name__+": "+str(error)))
    try:
        remaining=members(pgid)
        if remaining:
            verified=False;errors.append(dict(operation="inventory-owned-group",remaining_pids=remaining))
    except BaseException as error:
        verified=False;errors.append(dict(operation="inventory-owned-group",error=type(error).__name__+": "+str(error)))
    return verified


def close_accounted_attempt(a,stream,records,receipt,elapsed,exposure,proofs,cleanup_verified,counter_proof=None):
    if not cleanup_verified:
        receipt["pending_attempt_preserved"]=True
        current=a.note_pending_failure(stream,records,"owned cleanup not verified",proofs)
        receipt.update(pending_reservation=current["pending"]["reservation"],
            conservative_including_pending=current["conservative_including_pending"],cumulative=current["cumulative"])
        return
    if receipt["status"]!="completed":counter_proof=None
    observed=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
    observed["native_applies"]=exposure["known_calls"]if exposure["verified"]else None
    current=a.finish(stream,records,receipt["status"],elapsed,observed,proofs,
        cleanup_verified=True,execution_ended=True,observed_verified=exposure["verified"],counter_proof=counter_proof)
    if receipt["status"]=="completed"and receipt["stage"]not in current["completed_stages"]:
        receipt.update(status="failed",error="authoritative accounting did not complete this stage")
    receipt.update(charged_native_applies=current["charged"]["native_applies"],charged_seconds=current["charged"]["seconds"],ledger_last_record_sha256=current["last_record_sha256"])


def enforce_launch_deadline(started,limit):
    if time.monotonic()-started>=limit:raise RuntimeError("fixed stage active-wall limit reached before process launch")


def preview(args,a,manifest):
    if args.stage not in STAGES:raise ValueError("only build/native stages exist")
    if args.ledger is not None and Path(args.ledger).resolve()!=a.LEDGER.resolve():raise ValueError("one canonical shared campaign ledger required")
    if args.target_dir.resolve()!=Path(manifest["cargo_target_dir"]).resolve():raise ValueError("use pinned writable warm Cargo target cache")
    if args.out.resolve()!=Path(manifest["stage_output_dirs"][args.stage]).resolve():raise ValueError("fixed non-overwriting stage output required")
    binary=args.target_dir/"debug/semantic-discrimination-native-collector"
    command=([manifest["cargo_executable"],"build","--offline","--locked","--manifest-path",str(CRATE/"Cargo.toml"),"--bin","semantic-discrimination-native-collector","-j","1"]if args.stage=="build"else[str(binary),str(args.out/"native-receipt.json")])
    return dict(stage=args.stage,argv=command,outputs=[str(args.out),str(binary)]if args.stage=="build"else[str(args.out)],
        source_manifest=pin(args.manifest),accounting=pin(ACCOUNTING_SOURCE),
        max_active_seconds=STAGES[args.stage][0],reserved_native_applies=STAGES[args.stage][1],max_sampled_bytes=MAX_BYTES,sample_interval_seconds=INTERVAL,
        optimizer_updates=0,neural_forwards=0,numerical_fits=0,paid_jobs=0,campaign_ledger=str(a.LEDGER),
        build_profile=dict(opt_level=0,debug=0,incremental=False,codegen_override=None,rustflags=[],cargo_build_workers=1,os_single_core_affinity=False),
        no_retries=True,binary=str(binary),ledger_initialized=a.LEDGER.is_file())


def run(args):
    if args.stage not in STAGES:raise ValueError("native build/collection only; no fit/evaluate/reset mode")
    invocation_started=time.monotonic();a=load_accounting(args.spec)
    if not args.execute:
        manifest=preflight(args.manifest);build_environment(args.target_dir);result=preview(args,a,manifest);print(json.dumps(result,indent=2));return result
    if args.ledger is not None and args.ledger.resolve()!=a.LEDGER:raise ValueError("one canonical shared campaign ledger required")
    with a.lease()as(stream,records,current):
        started=invocation_started;limit=STAGES[args.stage][0];descriptor=current["config"]["stage_descriptors"][args.stage]
        receipt=dict(stage=args.stage,status="started",argv=descriptor["argv"],outputs=descriptor["outputs"],observed_per_pid_peak_bytes={},sample_count=0,exited_owned_pid_skips=[])
        rp=args.out/"supervisor-receipt.json";proc=None;pgid=None;launched=False;cleanup_verified=True;proofs=[];new_output=False;summary={};child_intended=False;child_started=False;child_recorded=False;child_ended=False;known_spawn_failure=False
        def update():
            receipt["active_seconds"]=time.monotonic()-started
            if new_output:rp.write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        try:
            input_pins=list(current["config"]["pins"])
            expected_manifest=a.allowed_pins(records).get(str(args.manifest.resolve()))
            if expected_manifest is None:raise ValueError("completed metadata stage must pin external native manifest")
            input_pins.append(expected_manifest)
            if args.stage=="native":
                binary=args.target_dir/"debug/semantic-discrimination-native-collector"
                input_pins.append(build_binary_proof(records,binary,verify=False))
            # Reservation is durable before strict input/profile checks or launch.
            a.start(stream,records,args.stage,dict(argv=descriptor["argv"],outputs=descriptor["outputs"],guard=a.GUARD,input_pins=input_pins))
            manifest=preflight(args.manifest);env=build_environment(args.target_dir);summary=preview(args,a,manifest)
            if dict(argv=summary["argv"],outputs=summary["outputs"])!=descriptor:raise ValueError("native command differs from canonical frozen descriptor")
            if args.out.exists():raise FileExistsError("preserve prior stage directory; no retry")
            args.out.mkdir(parents=True);new_output=True;receipt.update(summary);update()
            rss,members=process_readers();rss(os.getpid())
            env["SEMANTIC_DISCRIMINATION_PLAN"]=manifest["collection_plan"]["path"]
            env["SEMANTIC_DISCRIMINATION_NATIVE_TRACE"]=str(args.out/"native-transitions.jsonl")
            with(args.out/"stdout.log").open("x")as stdout,(args.out/"stderr.log").open("x")as stderr:
                enforce_launch_deadline(started,limit)
                a.child_intent(stream,records,summary["argv"]);child_intended=True
                launch_identity="guard-launch-token="+uuid.uuid4().hex+";monotonic="+repr(time.monotonic())
                launched=args.stage=="native"
                try:
                    proc=subprocess.Popen(summary["argv"],cwd=CRATE,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
                except OSError as spawn_error:
                    known_spawn_failure=True;launched=False
                    receipt["spawn_failure_before_pid"]={"type":type(spawn_error).__name__,"error":str(spawn_error),"argv":summary["argv"],"scope":"Popen OSError: failed exec child reaped/no owned PID returned"}
                    raise
                except BaseException:
                    cleanup_verified=False
                    raise
                pgid=proc.pid;child_started=True;receipt["owned_pgid"]=pgid
                receipt["owned_launch_identity"]=launch_identity+";pid="+str(proc.pid)+";pgid="+str(pgid)
                a.child_started(stream,records,proc.pid,pgid,receipt["owned_launch_identity"]);child_recorded=True;update()
                while True:
                    readings=read_owned_rss(receipt,members(pgid),rss,os.getpid(),time.monotonic()-started)
                    peak=memory_sample(receipt,readings,os.getpid(),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);receipt["sample_count"]+=1
                    if peak>MAX_BYTES:raise RuntimeError("1GiB sampled concurrent live owned-process RSS threshold")
                    if time.monotonic()-started>=limit:raise RuntimeError("fixed stage active-wall limit exceeded")
                    code=proc.poll()
                    if code is not None:
                        receipt["exit_code"]=code
                        if members(pgid):raise RuntimeError("owned descendants remained after leader exit")
                        proc=None
                        if code:raise RuntimeError("owned stage exited "+str(code))
                        break
                    time.sleep(min(INTERVAL,max(.001,limit-(time.monotonic()-started))))
            if args.stage=="build":proofs.append(pin(summary["binary"]))
            else:
                raw=json.loads((args.out/"native-receipt.json").read_text())
                receipt["frozen_plan_postcondition"]=verify_frozen_plan(raw,manifest)
                exposure=trace_exposure(args.out/"native-transitions.jsonl",True)
                if not exposure["verified"]or exposure["known_calls"]!=raw["applyCalls"]or raw["applyCalls"]>128 or len(raw["cases"])!=33 or raw.get("collectionComplete")is not True:
                    raise ValueError("native receipt/journal/complete33-root count differs")
                if any(c["engineError"]is not None or c.get("intentResolution")not in("committed","unoffered-declined","unoffered-observation-only")for c in raw["cases"]):
                    raise ValueError("unsettled/error/uncommitted native root blocks qualification")
                receipt["successful_journal"]=verify_success_journal(args.out/"native-transitions.jsonl",raw)
                receipt["complete_native_chains"]=verify_complete_cases(raw,manifest,args.out/"native-transitions.jsonl")
                receipt["constructor_support_only"]=verify_no_physical_shields(raw)
                receipt["public_fixture_privacy"]=verify_fixture_privacy(raw)
                proofs.extend([pin(args.out/"native-receipt.json"),pin(args.out/"native-transitions.jsonl")])
            receipt["preserved_binaries"]=verify_preserved_binaries(manifest)
            receipt["status"]="completed"
        except BaseException as error:
            receipt.update(status="failed",error=type(error).__name__+": "+str(error))
            if proc is not None:cleanup_verified=cleanup_owned(proc,pgid,members,receipt)
        finally:
            parent=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;child=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            bound=final_memory_bound(receipt.get("observed_peak_live_sum_bytes",0),parent,child)
            receipt.update(supervisor_maxrss_bytes=parent,max_single_child_rusage_peak_bytes=child,observed_conservative_peak_sum_bytes=bound,
                cleanup_verified=cleanup_verified,memory_limitation="50ms live owned-RSS samples; max with parent rusage peak plus maximum single child peak, not an OS process-tree reservation")
            if bound>MAX_BYTES:receipt.update(status="failed",error="final supervisor+single-child rusage RSS threshold exceeded")
            elapsed=time.monotonic()-started
            if elapsed>limit:receipt.update(status="failed",error="fixed stage active-wall limit exceeded including cleanup")
            exposure=trace_exposure(args.out/"native-transitions.jsonl",launched)if args.stage=="native"and new_output else dict(known_calls=0,verified=True,reason=None)
            if not exposure["verified"]:receipt.update(status="failed",native_journal_error=exposure["reason"])
            receipt.update(known_native_apply_lower_bound=exposure["known_calls"],observed_native_applies=exposure["known_calls"]if exposure["verified"]else None,native_journal_verified=exposure["verified"])
            for name in("stdout.log","stderr.log"):
                if new_output and(args.out/name).exists():proofs.append(pin(args.out/name))
            journal=args.out/"native-transitions.jsonl"
            if new_output and journal.exists()and not any(p["path"]==str(journal.resolve())for p in proofs):proofs.append(pin(journal))
            receipt["proofs"]=proofs;update()
            if child_intended and cleanup_verified:
                if child_started and not child_recorded:
                    cleanup_verified=False;receipt.setdefault("cleanup_errors",[]).append(dict(operation="durable-child-start",error="PID ownership record was not durably acknowledged"))
                if not child_started and not known_spawn_failure:
                    cleanup_verified=False;receipt.setdefault("cleanup_errors",[]).append(dict(operation="spawn-ownership",error="child intent exists without verified spawn failure or PID"))
                if known_spawn_failure:
                    spawn_proof=args.out/"spawn-failure-proof.json"
                    with spawn_proof.open("x")as f:json.dump(receipt["spawn_failure_before_pid"],f,sort_keys=True,indent=2);f.write("\n")
                    proofs.append(pin(spawn_proof))
                try:
                    if not cleanup_verified:raise RuntimeError("unknown spawn ownership")
                    a.child_ended(stream,records,proofs,cleanup_verified=True,execution_ended=True);child_ended=True
                except BaseException as error:
                    cleanup_verified=False;receipt.setdefault("cleanup_errors",[]).append(dict(operation="durable-child-ended",error=type(error).__name__+": "+str(error)))
            receipt["cleanup_verified"]=cleanup_verified
            pending=a.state(records)["pending"]
            if pending is not None:
                counter_proof=pin(args.out/"native-transitions.jsonl")if receipt["status"]=="completed"and args.stage=="native"and exposure["verified"]and(args.out/"native-transitions.jsonl").exists()else None
                close_accounted_attempt(a,stream,records,receipt,elapsed,exposure,proofs,cleanup_verified,counter_proof)
            update()
        print(json.dumps({k:receipt.get(k)for k in("stage","status","active_seconds","observed_native_applies","charged_native_applies","error")}));return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",choices=tuple(STAGES),required=True);p.add_argument("--manifest",type=Path,default=MANIFEST_PATH);p.add_argument("--spec",type=Path,default=SPEC_PATH);p.add_argument("--ledger",type=Path)
    p.add_argument("--out",type=Path,required=True);p.add_argument("--target-dir",type=Path,default=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/typed-ir-microprobe/target"));p.add_argument("--execute",action="store_true")
    args=p.parse_args();result=run(args)
    if args.execute and result["status"]!="completed":sys.exit(1)


if __name__=="__main__":main()
