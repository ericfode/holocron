"""Frozen zero-update literal/path audit and bounded conditional native evaluation.

Preparation is pure token/tensor/saved-artifact inspection. Model calls require a
separately sealed native manifest and the coordinator's GO; no optimizer exists.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent / "experiments"
PRIOR = ROOT / "grounded-contrast"
FRESH = ROOT / "transition-replication"
DEFAULT = ROOT / "literal-binding"
SEEDS = (17, 29, 43)
ARMS = ("correct-ir", "context-only")
MODEL_SHA = "473bc2324cf62c0437effd631e8fec3cc5930d2aeee0d00255da3bd08747eaf2"
RUNNER_SHA = "f4277ab29be9fdd26d6920e04d35eee4acbe6bd781c36968475b37a306af9a6e"
HEADS = ("source_use", "target_allowed", "cost_resource", "damage_delta", "source_exhausted_after", "target_exhausted_delta", "shield_delta", "xp_delta", "target_defeated", "followup_source_offered", "terminal")
COUNTS = dict(model_forwards=6, backwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def definitions():
    if sha(HERE / "grounded_contrast_model.py") != MODEL_SHA or sha(HERE / "transition_replication_fit.py") != RUNNER_SHA:
        raise ValueError("frozen model/loader source changed")
    sys.path.insert(0, str(HERE))
    import transition_replication_fit as R
    return R, R.model_definitions()


def references(seed=17):
    R, M = definitions()
    data = R.load_data(FRESH / "transition-replication.npz", FRESH / "transition-replication.manifest.json", PRIOR / "fit-1/contract.json", seed)
    result = PRIOR / "fit-1/result.json" if seed == 17 else FRESH / f"fit-original-s{seed}/result.json"
    return data, R.saved_checkpoints(result, seed), result


def role(path, kind):
    if kind == "length":
        return "structural-list-length"
    return {"costs": "activation-cost", "effect": "effect-payload", "targetResolver": "target-selector", "condition": "source-condition"}.get(path[0] if path else "", "other")


def tensor_binding_trace(data):
    """Decode the actual production tensors; no encoder/model evaluation."""
    import numpy as np
    _, M = definitions()
    bank, symbols, scale = data["bank"], data["symbols"], data["numeric_scale"]
    rows, signatures = [], {}
    for slot, record in enumerate(data["records"]):
        literals = []
        for index, (path, kind, value) in enumerate(M.structural_tokens(record["raw_ability"])):
            depth = int(bank["path_lengths"][slot,index])
            atoms = [symbols["path"][int(i)] for i in bank["path_ids"][slot,index,:depth]]
            decoded = tuple(int(atom[6:]) if atom.startswith("index:") else atom[4:] for atom in atoms)
            if decoded != path or symbols["type"][int(bank["type_ids"][slot,index])] != kind:
                raise ValueError("path/type alignment lost")
            if kind in ("number", "length"):
                encoded = bank["numeric"][slot,index].astype(float)
                expected = [value/scale, np.sign(value)*np.log1p(abs(value))]
                if not np.allclose(encoded, expected, rtol=1e-6, atol=1e-6):
                    raise ValueError("numeric literal/channel alignment differs")
                literals.append(dict(path=list(path), kind=kind, role=role(path,kind), physical_value=value, encoded=encoded.tolist(), recovered_first_channel=float(encoded[0]*scale)))
        digest = hashlib.sha256()
        for key in sorted(bank):
            if key != "identity_indices":
                value = bank[key][slot]
                digest.update(key.encode()+str(value.dtype).encode()+str(value.shape).encode()+value.tobytes())
        signature = digest.hexdigest()
        group = record["program_group_id"]
        if signature in signatures and signatures[signature][1] != group:
            raise ValueError("distinct normalized programs collide in semantic input tensors")
        signatures[signature] = (record["code"],group)
        rows.append(dict(code=record["code"], program_group_id=group, semantic_tensor_sha256=signature, numeric_literals=literals))
    return dict(programs=rows, distinct_input_signatures=len(signatures), collisions=[], numeric_scale=scale,
                scale_scope="training-program numbers AND list lengths; frozen shared std-floor1, plus unscaled signedlog1p channel",
                limits="No collision here proves neither injective learned embeddings nor learned role/quantity use.")


def vocabulary_coverage(symbols):
    _, M = definitions()
    inventory = read(ROOT / "grounded-contrast/inventory.json")
    rows = []
    for record in inventory["records"]:
        try:
            tokens = M.structural_tokens(record["raw_ability"])
            paths = {("index:" if type(key) is int else "key:")+str(key) for path,_,_ in tokens for key in path}
            values = {"NUMBER" if kind in ("number","length") else kind+":"+str(value) for _,kind,value in tokens}
            missing_path, missing_value = sorted(paths-set(symbols["path"])), sorted(values-set(symbols["value"]))
            rows.append(dict(code=record["card"], ability_path=record["ability_path"], total_card_abilities=sum(record["complete_ability_counts"].values()),
                             representable=not missing_path and not missing_value, missing_path=missing_path, missing_value=missing_value, parser_error=None))
        except ValueError as error:
            rows.append(dict(code=record["card"],representable=False,parser_error=str(error)))
    return dict(action_programs=len(rows), representable=sum(row["representable"] for row in rows), records=rows,
                scope="Only selected action-program syntax. Whole-card stats, other abilities/triggers, leader/unit roles and missing source-public features are separate admission gates.",
                fresh_unseen_whole_card_gate="unsupported: only unused ASH_123 and SHD_087 fit vocab; both need absent source power, SHD_087 has multiple abilities")


def input_signature(program_group, context, candidate=None):
    """Exact model-visible triple; board/root provenance is not an input."""
    import numpy as np
    digest = hashlib.sha256(program_group.encode()+np.asarray(context,np.float32).tobytes())
    if candidate is not None:
        digest.update(np.asarray(candidate,np.float32).tobytes())
    return digest.hexdigest()


def old_input_signatures():
    import numpy as np
    R, _ = definitions()
    source, candidate = set(), set()
    for directory, stem in ((PRIOR,"grounded-contrast"),(FRESH,"transition-replication")):
        data = R.load_data(directory/(stem+".npz"),directory/(stem+".manifest.json"),PRIOR/"fit-1/contract.json",17)
        for i,group in enumerate(data["arrays"]["program_group_ids"].astype(str)):
            source.add(input_signature(group,data["context"][i]))
            for j in range(8):
                candidate.add(input_signature(group,data["context"][i],data["candidates"][i,j]))
    return source,candidate


def prepare(plan_path, native_plan):
    import numpy as np
    data, _, _ = references()
    if plan_path.exists():
        raise FileExistsError("preserve existing plan")
    replay = [int(np.flatnonzero((data["arrays"]["source_cards"]==code)&(data["arrays"]["state_families"]==10))[0]) for code in ("SHD_004","TWI_206")]
    paths = [Path(__file__),HERE/"grounded_contrast_model.py",HERE/"transition_replication_fit.py",HERE/"composition_gradient_diagnostic.py",HERE/"grounded_contrast_data.py",HERE/"literal_binding_native_plan.py",
             PRIOR/"fit-1/contract.json",ROOT/"grounded-contrast/inventory.json",PRIOR/"grounded-contrast.npz",PRIOR/"grounded-contrast.manifest.json",
             FRESH/"transition-replication.npz",FRESH/"transition-replication.manifest.json",native_plan]
    for seed in SEEDS:
        _, refs, result = references(seed)
        paths.append(result)
        for arm in ARMS:
            paths.extend([Path(refs[arm]["checkpoint"]),Path(refs[arm]["contract"]),FRESH/f"eval-fresh-s{seed}"/(arm+"-predictions.npz")])
    train=data["arrays"]["candidate_features"][data["arrays"]["train_idx"],:7]
    support={name:dict(values=np.unique(train[...,j]).tolist(),varying=bool(np.ptp(train[...,j]))) for j,name in enumerate(data["manifest"]["candidate_feature_names"])}
    plan = dict(schema="jepa-literal-binding-audit/1",status="prepared-before-native-labels-and-NN",source_sha256=sha(__file__),
                inputs=[dict(path=str(path),sha256=sha(path)) for path in paths],replay_root_indices=replay,
                native_root_count=16,model_rows_per_call=18,candidate_slots_per_row=8,seeds=list(SEEDS),arms=list(ARMS),expected_counts=COUNTS,
                runtime=dict(active_NN_seconds=20,threads=1,sampled_rss_bytes=1073741824),replay_max_absolute_tolerance=1e-5,
                binding_trace=tensor_binding_trace(data),vocabulary_coverage=vocabulary_coverage(data["symbols"]),
                frozen_head_order=list(HEADS),head_scaling=data["head_scaling"],input_scaling=data["input_scaling"],numeric_scale=data["numeric_scale"],
                primary_heads=["cost_resource","xp_delta","target_exhausted_delta"],all_negative_heads_retained=True,
                training_primary_candidate_support=support,source_features=list(data["manifest"]["context_feature_names"]),
                input_limits="Source printed power is absent for a non-self candidate. XP1 native attachment changes HP/power together; constant-training coordinates are numerical OOD, not independently learned effects.",
                qualification="Previously inspected held-program conditional diagnostic; no fresh unseen-card/whole-card/effect-family admission.",
                novelty="Exact program-group + scaled2globals + own26candidate versus ALL original168 and fresh168; source novelty separately. No worldfingerprint independence claim.",
                loss_or_fit="None. Same9020weights/vocabulary/scalers; no categorical remap, no optimizer, no gradients, no synthetic IR model variants.")
    plan_path.parent.mkdir(parents=True,exist_ok=True)
    write(plan_path,plan)
    return plan


def load_native(dataset, manifest_path, reference):
    import numpy as np
    R, M = definitions()
    manifest = read(manifest_path)
    if sha(dataset)!=manifest["artifact"]["sha256"]:
        raise ValueError("native dataset hash differs")
    with np.load(dataset,allow_pickle=False) as pack:
        arrays={key:value.copy() for key,value in pack.items()}
    shapes=dict(context_features=(16,2),candidate_features=(16,8,26),source_use=(16,),source_use_mask=(16,),candidate_allowed=(16,8),candidate_allowed_mask=(16,8),targets=(16,8,11),target_mask=(16,8,11),primary_candidate_mask=(16,8))
    for key,shape in shapes.items():
        if arrays[key].shape!=shape or arrays[key].dtype!=np.float32 or not np.isfinite(arrays[key]).all():
            raise ValueError("native shape/dtype/finite mismatch "+key)
        if key.endswith("mask") and not np.isin(arrays[key],[0,1]).all():
            raise ValueError("invalid native mask")
    if tuple(manifest["target_names"])!=HEADS or manifest["context_feature_names"]!=reference["manifest"]["context_feature_names"] or manifest["candidate_feature_names"]!=reference["manifest"]["candidate_feature_names"] or not np.array_equal(arrays["primary_candidate_mask"],np.tile([1.]*7+[0.],(16,1))) or arrays["target_mask"][...,:2].any():
        raise ValueError("native head/primary/label ownership mismatch")
    if set(arrays["source_cards"].astype(str))!={"SHD_004","TWI_206"}:
        raise ValueError("conditional program pair differs")
    for code,record in manifest["programs"].items():
        old=reference["records"][reference["codes"].index(code)]
        if R.normalized_program(record["raw_ability"])!=R.normalized_program(old["raw_ability"]):
            raise ValueError("native program differs from fixed bank")
    if arrays["source_cards"].shape!=(16,) or arrays["state_families"].shape!=(16,) or arrays["state_families"].dtype!=np.int64 or not np.array_equal(arrays["eval_idx"],np.arange(16,dtype=np.int64)) or {(str(code),int(state)) for code,state in zip(arrays["source_cards"],arrays["state_families"])}!={(code,state) for code in ("SHD_004","TWI_206") for state in range(8)}:
        raise ValueError("fixed16 native program/context roots required")
    import grounded_contrast_data as G
    settled=np.zeros((16,8),bool)
    if len(manifest["records"])!=16:raise ValueError("native witness root count differs")
    for i,record in enumerate(manifest["records"]):
        if record["card"]!=str(arrays["source_cards"][i]) or record["context_family"]!=int(arrays["state_families"][i]) or len(record["queries"])!=8:
            raise ValueError("raw native witness order differs")
        for j,query in enumerate(record["queries"]):
            if query["chosen_ref"]!=R.CANDIDATE_ROLES[j]:raise ValueError("native candidate order differs")
            after=query["after"]
            settled[i,j]=query["targetAction"] is not None and not query.get("engineError") and after is not None and G.settled_capture(after)
    for head in M.BINARY_HEADS:
        values,mask=(arrays["source_use"],arrays["source_use_mask"]) if head==0 else (arrays["candidate_allowed"],arrays["candidate_allowed_mask"]) if head==1 else (arrays["targets"][...,head],arrays["target_mask"][...,head])
        if not np.isin(values[mask.astype(bool)],[0,1]).all():raise ValueError("nonbinary known native label")
    if np.any(arrays["target_mask"][:,[0,1,3,4,5,6,7],2:]):raise ValueError("uncommitted outcome labels must remain unknown")
    if np.any(arrays["target_mask"][...,2:].any(-1)&~settled):
        raise ValueError("future labels without settled branch")
    context,candidates=M.apply_input_scaling(arrays["context_features"],arrays["candidate_features"],reference["input_scaling"])
    old_source,old_candidate=old_input_signatures()
    source_new,query_new=[],[]
    for i,code in enumerate(arrays["source_cards"].astype(str)):
        group=reference["group_ids"][reference["codes"].index(code)]
        source_new.append(input_signature(group,context[i])not in old_source)
        query_new.append([input_signature(group,context[i],candidates[i,j])not in old_candidate for j in range(8)])
    return dict(arrays=arrays,manifest=manifest,context=context,candidates=candidates,settled=settled,source_new=np.asarray(source_new,bool),candidate_new=np.asarray(query_new,bool))


def seal(prepared_path, plan_path, dataset, manifest_path):
    plan=read(prepared_path)
    if plan_path.exists():
        raise FileExistsError("preserve sealed plan")
    for item in plan["inputs"]:
        if sha(item["path"])!=item["sha256"]:
            raise ValueError("prepared source/input changed")
    reference,_,_=references()
    native=load_native(dataset,manifest_path,reference)
    native_plan=next(item for item in plan["inputs"]if Path(item["path"]).name=="native-plan-v2.json")
    if native["manifest"]["plan"]!=read(native_plan["path"]):raise ValueError("native labels differ from frozen native plan")
    plan.update(status="sealed-native-labels-awaiting-root-GO",prepared_plan_sha256=sha(prepared_path),native_dataset=str(dataset),native_manifest=str(manifest_path),
                native_source_new=native["source_new"].tolist(),native_candidate_new=native["candidate_new"].tolist())
    plan["inputs"] += [dict(path=str(path),sha256=sha(path)) for path in (dataset,manifest_path)]
    write(plan_path,plan)
    return plan


def metrics(source,branch,native,reference):
    import numpy as np
    a=native["arrays"];result={}
    for segment,selection in (("primary",a["primary_candidate_mask"]),("source-self",1-a["primary_candidate_mask"])):
        heads={}
        for head,name in enumerate(HEADS):
            if head==0 and segment!="primary":
                continue
            target=a["source_use"] if head==0 else a["candidate_allowed"] if head==1 else a["targets"][...,head]
            pred=source if head==0 else branch[...,head]
            known=a["source_use_mask"].copy() if head==0 else (a["candidate_allowed_mask"] if head==1 else a["target_mask"][...,head])*selection
            scopes={}
            for scope in ("all","new-local-input","repeated-local-input"):
                use=known.copy()
                novelty=native["source_new"] if head==0 else native["candidate_new"]
                if scope!="all":use*=novelty if scope=="new-local-input" else ~novelty
                support=use if head==0 else use.sum(-1);valid=support>0
                error=abs(pred-target) if head==0 else (abs(pred-target)*use).sum(-1)/np.maximum(support,1)
                residual=pred-target if head==0 else ((pred-target)*use).sum(-1)/np.maximum(support,1)
                accuracy=((pred>=.5)==target).astype(float)
                accuracy=accuracy if head==0 else (accuracy*use).sum(-1)/np.maximum(support,1)
                scopes[scope]=dict(observed_roots=int(valid.sum()),known_coordinates=int(use.sum()),mae=float(error[valid].mean())if valid.any()else None,
                                   signed_mean_residual=float(residual[valid].mean())if valid.any()else None,
                                   binary_accuracy_at_point5=float(accuracy[valid].mean())if valid.any()and head in (0,1,4,8,9,10)else None,
                                   native_values=np.unique(target[use.astype(bool)]).tolist(),known_zero_coordinates=int(((target==0)&use.astype(bool)).sum()),known_nonzero_coordinates=int(((target!=0)&use.astype(bool)).sum()))
            heads[name]=scopes
        result[segment]=heads
    pairs=[]
    for state in sorted(set(a["state_families"].tolist())):
        rows=[int(i)for i in np.flatnonzero(a["state_families"]==state)];by={str(a["source_cards"][i]):i for i in rows}
        if set(by)!={"SHD_004","TWI_206"}:raise ValueError("matched2program context required")
        left,right=by["SHD_004"],by["TWI_206"]
        if not np.array_equal(native["context"][left],native["context"][right])or not np.array_equal(native["candidates"][left,:7],native["candidates"][right,:7]):raise ValueError("paired primary inputs differ")
        for head in (2,7,5):
            j=2
            if all(a["target_mask"][[left,right],j,head])and all(a["candidate_allowed_mask"][[left,right],j])and all(a["candidate_allowed"][[left,right],j])and all(native["settled"][[left,right],j]):
                truth=float(a["targets"][left,j,head]-a["targets"][right,j,head]);pred=float(branch[left,j,head]-branch[right,j,head]);pairs.append(dict(state_family=int(state),head=HEADS[head],native_delta=truth,predicted_delta=pred,error=abs(pred-truth),train_scaled_error=abs(pred-truth)/reference["head_scaling"]["scale"][head],local_inputs_new=[bool(native["candidate_new"][left,j]),bool(native["candidate_new"][right,j])]))
    summary={name:dict(pairs=sum(p["head"]==name for p in pairs),mae=float(np.mean([p["error"]for p in pairs if p["head"]==name]))if any(p["head"]==name for p in pairs)else None,train_scaled_mae=float(np.mean([p["train_scaled_error"]for p in pairs if p["head"]==name]))if any(p["head"]==name for p in pairs)else None)for name in (HEADS[2],HEADS[7],HEADS[5])}
    macro=float(np.mean([row["train_scaled_mae"]for row in summary.values()]))if all(row["pairs"]for row in summary.values())else None
    return dict(heads=result,mutually_legal_settled_pairs=pairs,fixed_three_head_pair_summary=summary,fixed_three_head_train_scaled_macro=macro,limitations="Dependent synthetic public contexts; no new-card/effect-family generalization, no XPamount2 labels; XPchangesHP/power together.")


def execute(plan_path,out):
    plan=read(plan_path)
    if plan["status"]!="sealed-native-labels-awaiting-root-GO":raise ValueError("sealed native plan required")
    out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(HERE))
    from composition_gradient_diagnostic import Guard
    counts={key:0 for key in COUNTS}
    guard=Guard()
    try:
        with guard:
            if sha(__file__)!=plan["source_sha256"] or plan["expected_counts"]!=COUNTS or plan["arms"]!=list(ARMS) or plan["seeds"]!=list(SEEDS):raise ValueError("frozen source/counter matrix differs")
            for item in plan["inputs"]:
                if sha(item["path"])!=item["sha256"]:raise ValueError("sealed input changed")
            import numpy as np
            import torch
            torch.set_num_threads(1);torch.set_num_interop_threads(1)
            _,M=definitions();reference,_,_=references();native=load_native(Path(plan["native_dataset"]),Path(plan["native_manifest"]),reference)
            replay=np.asarray(plan["replay_root_indices"],np.int64)
            x=torch.as_tensor(np.concatenate([reference["context"][replay],native["context"]]));c=torch.as_tensor(np.concatenate([reference["candidates"][replay],native["candidates"]]))
            q=torch.as_tensor(np.concatenate([reference["query"][replay],np.asarray([reference["codes"].index(str(code))for code in native["arrays"]["source_cards"]],np.int64)]))
            if len(x)!=18:raise ValueError("fixed18modelrows required")
            bank=M.torch_bank(torch,reference["bank"]);results=[]
            for seed in SEEDS:
                _,checkpoints,_=references(seed)
                for arm in ARMS:
                    model=M.make_contrast_model(torch,reference["symbols"]);weights=checkpoints[arm]["arrays"]
                    model.load_state_dict({name:torch.as_tensor(value)for name,value in weights.items()},strict=True);model.eval()
                    if sum(p.numel()for p in model.parameters())!=9020:raise ValueError("frozen parameter count differs")
                    counts["model_forwards"]+=1
                    if counts["model_forwards"]>6:raise RuntimeError("sixforwards exhausted")
                    with torch.inference_mode():source,branch=M.predictions(torch,model(x,c,q,bank,arm),reference["head_scaling"])
                    if not np.isfinite(source).all()or not np.isfinite(branch).all():raise ValueError("nonfinite frozen predictions")
                    with np.load(FRESH/f"eval-fresh-s{seed}"/(arm+"-predictions.npz"),allow_pickle=False)as saved:
                        positions=[saved["root_indices"].tolist().index(int(i))for i in replay]
                        discrepancy=max(float(abs(source[:2]-saved["source_predictions"][positions]).max()),float(abs(branch[:2]-saved["branch_predictions"][positions]).max()))
                    if not np.isfinite(discrepancy)or discrepancy>plan["replay_max_absolute_tolerance"]:raise ValueError("saved same-backend replay parity failed")
                    if any(not np.array_equal(value.detach().numpy(),weights[name])for name,value in model.state_dict().items()):raise ValueError("checkpoint state changed")
                    np.savez_compressed(out/f"{arm}-s{seed}-predictions.npz",source=source,branch=branch,replay_indices=replay)
                    results.append(dict(seed=seed,arm=arm,replay_max_absolute_error=discrepancy,metrics=metrics(source[2:],branch[2:],native,reference),checkpoint_sha256=checkpoints[arm]["checkpoint_sha256"]))
            if counts!=COUNTS:raise ValueError("fixedcounter mismatch")
            for item in plan["inputs"]:
                if sha(item["path"])!=item["sha256"]:raise ValueError("protected input/checkpoint changed")
            if guard.rss()>1073741824:raise RuntimeError("1GiB memory limit reached")
            result=dict(schema=plan["schema"],status="completed",source_sha256=sha(__file__),plan_sha256=sha(plan_path),counts=counts,results=results,
                        input_scope=dict(source_new=native["source_new"].tolist(),candidate_new=native["candidate_new"].tolist()),all_parameters_and_inputs_unchanged=True,checkpoint_writes=0,guard=guard.receipt())
            write(out/"result.json",result)
        receipt=dict(status="completed",source_sha256=sha(__file__),plan_sha256=sha(plan_path),result_sha256=sha(out/"result.json"),counts=counts,guard=guard.receipt())
        write(out/"receipt.json",receipt);print(json.dumps(receipt,indent=2))
    except BaseException as error:
        receipt=dict(status="failed-preserved-no-automatic-retry",error_type=type(error).__name__,error=str(error),source_sha256=sha(__file__),plan_sha256=sha(plan_path),counts=counts,counter_rule="A started interrupted forward is charged; no automatic budget reset or retry.",guard=guard.receipt())
        write(out/"receipt.json",receipt)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
    for key in ("prepare","seal","execute"):mode.add_argument("--"+key,action="store_true")
    parser.add_argument("--plan",type=Path,default=DEFAULT/"audit-plan.json");parser.add_argument("--prepared",type=Path,default=DEFAULT/"audit-prepared.json")
    parser.add_argument("--native-plan",type=Path,default=DEFAULT/"native-plan-v2.json");parser.add_argument("--dataset",type=Path,default=DEFAULT/"literal-binding.npz");parser.add_argument("--manifest",type=Path,default=DEFAULT/"literal-binding.manifest.json");parser.add_argument("--out",type=Path,default=DEFAULT/"audit-run-1")
    args=parser.parse_args()
    if args.prepare:prepare(args.prepared,args.native_plan);print(json.dumps(dict(prepared=str(args.prepared),sha256=sha(args.prepared))))
    elif args.seal:seal(args.prepared,args.plan,args.dataset,args.manifest);print(json.dumps(dict(plan=str(args.plan),sha256=sha(args.plan))))
    else:execute(args.plan,args.out)


if __name__=="__main__":main()
