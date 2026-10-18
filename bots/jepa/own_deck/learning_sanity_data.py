"""Saved-data audit + fixed lambda1 weighted ridge. No neural/engine imports.

Default/--prepare only seals inputs. --run is for the coordinator's separately
authorized <=10s pure analysis stage; never invoked automatically.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key]="1"

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[3] / "experiments"
OLD = EXPERIMENTS / "effect-identifiability-v2"
DEFAULT = EXPERIMENTS / "learning-sanity-v1"
DATA_SHA = "2254eef79afaa2da7cca145522ec8d05a6b2e374c71387d4cfe09b7b0c47a122"
PRIOR_SHA = "6eadc7c3231c93b8aeebf85e1d6d44bb16b98ff80143283cc84c95071a3dd3b2"
RESULT_SHA = "90cac45d13e621751164815d65ebc99eb6b2c501b39128d244352970a092569e"
AUDIT_SHA = "5410975ad9fb59a3065655b25ee2405366af1b06ac28cdecfb6c464347ee246a"
CONFIG = dict(ridge_lambda=1., objective="SUM (original TRAIN signweight/root known coordinates)*squared normalized residual + lambda*squared slopes; no neural head coefficient/root denominator", intercept_penalized=False,
              predictor_columns=59, continuous_columns=52, train_id_columns=7, feature_scale="TRAIN population std, constant scale1; ID unscaled",
              zero_threshold_native=.25, binary_threshold=.5, ridge_label_arms=["correct", "fixed-shuffle"], search=False,
              native_applies=0, neural_forwards=0, optimizer_updates=0, cpu_threads=1, max_analysis_seconds=10)


def require(value, message):
    if not value: raise ValueError(message)


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pathof(value): return Path(value["path"] if isinstance(value, dict) else value).resolve()
def pin(path):
    path = pathof(path)
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def verify_pins(pins):
    for item in pins: require(pin(item) == item, "input/source pin changed: " + item["path"])


def write(path, value): Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def prepare(sanity_plan, out, neural_fit=None):
    require(not out.exists(), "preserve data-analysis plan")
    shared = read(sanity_plan)
    prior_path = pathof(shared.get("prior_plan", OLD / "learner-plan.json"))
    prior = read(prior_path)
    paths = dict(sanity_plan=pathof(sanity_plan), prior_plan=prior_path,
                 dataset=pathof(shared.get("dataset", prior["dataset"])), manifest=pathof(shared.get("manifest", prior["manifest"])),
                 old_result=OLD / "fit-1/result.json", wire_audit=OLD / "independent-data-verification.json")
    require(sha(paths["prior_plan"]) == PRIOR_SHA and sha(paths["dataset"]) == DATA_SHA, "frozen prior dataset/plan differs")
    require(sha(paths["old_result"]) == RESULT_SHA and sha(paths["wire_audit"]) == AUDIT_SHA, "frozen result/wire audit differs")
    require(shared["effect_columns"] == list(range(2, 7)), "five joint delta columns required")
    require(len(shared["shuffle_roots"]) == 14 and len(shared["fixed_mapping"]) == 14, "frozen 14-packet shuffle required")
    pinned = {str(Path(__file__).resolve()): pin(__file__)}
    for item in [*prior["pins"], *shared.get("pins", []), *(pin(p) for p in paths.values())]:
        p = pin(item); require(p == item, "source changed before preparation")
        old = pinned.get(p["path"]); require(old is None or old == p, "conflicting transitive pin")
        pinned[p["path"]] = p
    for path in(HERE/"LEARNING_SANITY_DATA_PROTOCOL.md",HERE/"test_learning_sanity_data.py"):
        item=pin(path);pinned[item["path"]]=item
    fit_dir=pathof(neural_fit or DEFAULT/"fit-1")
    # Only byte pins are inspected here. Freeze the now-completed neural files
    # before the analysis can perform any matrix fitting or metric readout.
    neural_pins=[pin(p)for p in sorted(fit_dir.iterdir())if p.is_file()]if fit_dir.is_dir()else[]
    require(neural_pins and (fit_dir/"result.json").is_file(),"complete neural inputs must exist before data-analysis preparation")
    for item in neural_pins:pinned[item["path"]]=item
    result = dict(schema="learning-sanity-data-plan/1", status="prepared-awaiting-root-GO", config=CONFIG,
                  inputs={k: pin(v) for k, v in paths.items()}, pins=sorted(pinned.values(), key=lambda p:p["path"]),
                  source=pin(__file__), neural_fit_dir=str(fit_dir),neural_input_pins=neural_pins,
                  neural_inputs_scope="Finished neural files byte-pinned before analysis; baseline design unchanged. No outcome-dependent fit/split/config choices.", semantic_validated=False)
    out.parent.mkdir(parents=True,exist_ok=True);write(out, result); return result


def partitions(arrays, prior):
    import numpy as np
    train = np.isin(arrays["source_cards"], prior["train_codes"])
    state = np.isin(arrays["state_families"], prior["split"]["train_state_families"])
    return dict(train=np.flatnonzero(train & state), family_held=np.flatnonzero(~train & state),
                state_held=np.flatnonzero(train & ~state), joint=np.flatnonzero(~train & ~state))


def fixed_assignment(arrays, shared, train):
    import numpy as np
    roots = np.asarray(shared["shuffle_roots"], np.int64)
    mapping = np.asarray(shared["fixed_mapping"], np.int64)
    columns = np.asarray(shared["effect_columns"], np.int64)
    require(roots.shape == mapping.shape == (14,) and np.array_equal(columns, np.arange(2, 7)), "joint packet ABI")
    require(len(set(roots.tolist())) == 14 and set(roots.tolist()) <= set(train.tolist()), "shuffle outside TRAIN")
    require(set(mapping.tolist()) == set(range(14)) and (mapping != np.arange(14)).all(), "fixed shuffle must be a derangement")
    selected = arrays["selected_candidate_indices"][roots]
    require((arrays["target_mask"][roots[:, None], selected[:, None], columns] == 1).all(), "shuffle requires fully known packets")
    eligible = [int(r) for r in train if (arrays["target_mask"][r, arrays["selected_candidate_indices"][r], columns] == 1).all()]
    require(roots.tolist() == eligible, "shuffle must include all co-known TRAIN packets in original order")
    require(all({int(r)for r in train if arrays["target_mask"][r,:,h].any()}==set(roots.tolist())for h in columns),"partially known delta roots must not be dropped")
    copied = dict(arrays); copied["targets"] = arrays["targets"].copy()
    packets = arrays["targets"][roots[:, None], selected[:, None], columns].copy()
    copied["targets"][roots[:, None], selected[:, None], columns] = packets[mapping]
    return copied


def features(arrays, prior):
    import numpy as np
    x, c = arrays["context_features"], arrays["candidate_features"]
    require(x.shape == (48, 18) and c.shape == (48, 8, 34), "public predictor ABI")
    ids = np.zeros((48, 7), np.float64)
    require(len(prior["train_codes"]) == 7, "seven TRAIN identity slots")
    for i, code in enumerate(arrays["source_cards"]):
        if str(code) in prior["train_codes"]: ids[i, prior["train_codes"].index(str(code))] = 1.
    selected = arrays["selected_candidate_indices"]
    source = np.concatenate((x, c[np.arange(48), selected], ids), axis=-1).astype(np.float64)
    branch = np.concatenate((np.broadcast_to(x[:, None, :], (48, 8, 18)), c,
                             np.broadcast_to(ids[:, None, :], (48, 8, 7))), axis=-1).astype(np.float64)
    require(np.isfinite(source).all() and np.isfinite(branch).all(), "nonfinite predictor")
    held = ~np.isin(arrays["source_cards"], prior["train_codes"])
    require(not ids[held].any(), "held identity must be allzero")
    return source, branch


def standardize(raw, train):
    import numpy as np
    fitting = raw[train].reshape(-1, raw.shape[-1])
    center = np.zeros(raw.shape[-1], np.float64); scale = np.ones_like(center)
    center[:52] = fitting[:, :52].mean(0)
    std = fitting[:, :52].std(0); scale[:52] = np.where(std > 0, np.maximum(std,1e-8), 1.)
    transformed = (raw - center) / scale
    return transformed, dict(center=center.tolist(), scale=scale.tolist(), observations=len(fitting), id_columns_unscaled=True,
                             population_std=std.tolist(), constant_columns=np.flatnonzero(std==0).tolist(), nonconstant_scale_floor=1e-8)


def head_records(arrays, prior):
    for kind, ykey, mkey, specs in (("source", "source_targets", "source_mask", prior["scalers"]["source_targets"]),
                                  ("target", "targets", "target_mask", prior["scalers"]["targets"])):
        for h, spec in enumerate(specs): yield kind, h, ykey, mkey, spec


def weights_for(target, mask, spec, train):
    """Exact full-TRAIN neural per-head/root/candidate averaging coefficients."""
    import numpy as np
    y, m = np.asarray(target, np.float64), np.asarray(mask, bool)
    counts = m.sum(-1) if m.ndim == 2 else m.astype(np.int64)
    nroots = int(np.count_nonzero(counts[train]))
    denominator = counts[:, None] if m.ndim == 2 else counts
    classes = spec["class_weights"]
    signs = np.where(y < 0, classes["-1"], np.where(y > 0, classes["1"], classes["0"]))
    if nroots == 0: return np.zeros_like(y), counts, nroots
    return np.asarray(spec["loss_coefficient"] * signs * m / (nroots * np.maximum(denominator, 1))), counts, nroots


def ridge_weights(target,mask,spec):
    import numpy as np
    y,m=np.asarray(target,np.float64),np.asarray(mask)>0
    counts=m.sum(-1) if m.ndim==2 else m.astype(int)
    denominator=counts[:,None] if m.ndim==2 else counts
    classes=spec["class_weights"]
    signs=np.where(y<0,classes["-1"],np.where(y>0,classes["1"],classes["0"]))
    return signs*m/np.maximum(denominator,1)


def support(y, mask):
    import numpy as np
    y, m = np.asarray(y), np.asarray(mask) > 0; observed = y[m]
    def root_count(which): return int(np.count_nonzero(which if which.ndim == 1 else which.any(-1)))
    return dict(known_coordinates=int(m.sum()), unknown_coordinates=int(m.size-m.sum()), observed_roots=root_count(m),
                values=np.unique(observed).astype(float).tolist(), mean=float(observed.mean()) if len(observed) else None,
                variance=float(observed.astype(np.float64).var()) if len(observed) else None,
                zero=int(((y == 0) & m).sum()), positive=int(((y > 0) & m).sum()), negative=int(((y < 0) & m).sum()),
                zero_roots=root_count((y == 0) & m), nonzero_roots=root_count((y != 0) & m),
                positive_roots=root_count((y > 0) & m), negative_roots=root_count((y < 0) & m))


def metrics(prediction, target, mask, spec, reference_train):
    import numpy as np
    p, y, m = np.asarray(prediction, np.float64), np.asarray(target, np.float64), np.asarray(mask) > 0
    if not m.any(): return dict(known_coordinates=0, observed_roots=0, mae=None, normalized_mae=None, rmse=None, normalized_rmse=None, max_error=None, normalized_max_error=None)
    count = m.sum(-1) if m.ndim == 2 else m.astype(int); valid = count > 0
    def root_mean(v): return (v*m).sum(-1)/np.maximum(count,1) if m.ndim == 2 else v
    residual = p-y; error = np.abs(residual); scale=spec["scale"]
    threshold=.5 if spec["binary"] else CONFIG["zero_threshold_native"]
    predicted_sign = np.where(p>=threshold,1,0) if spec["binary"] else np.where(p>threshold,1,np.where(p < -threshold,-1,0))
    true_sign=np.sign(y)
    signs = {str(sign): float(((predicted_sign == sign) & (true_sign == sign) & m).sum()/((true_sign == sign) & m).sum()) if ((true_sign == sign) & m).any() else None for sign in (-1,0,1)}
    # This supplied reference fixes the TRAIN loss denominator. Cell metrics
    # below additionally report unweighted root-mean errors, not fake fit loss.
    class_weights=spec["class_weights"]
    signweight=np.where(y<0,class_weights["-1"],np.where(y>0,class_weights["1"],class_weights["0"]))
    weighted=root_mean((residual/scale)**2*signweight)
    return dict(known_coordinates=int(m.sum()), observed_roots=int(valid.sum()), mae=float(root_mean(error)[valid].mean()),
                normalized_mae=float(root_mean(error)[valid].mean()/scale), rmse=float(np.sqrt(root_mean(residual**2)[valid].mean())),
                normalized_rmse=float(np.sqrt(root_mean(residual**2)[valid].mean())/scale), max_error=float(error[m].max()), normalized_max_error=float(error[m].max()/scale),
                zero_nonzero_accuracy=float(root_mean(((predicted_sign == 0) == (true_sign == 0)).astype(float))[valid].mean()),
                sign_accuracy=float(root_mean((predicted_sign == true_sign).astype(float))[valid].mean()), sign_recall=signs,
                sign_balanced_accuracy=float(np.mean([v for v in signs.values() if v is not None])), zero_threshold_native=threshold,
                weighted_normalized_squared_residual_sum=float(spec["loss_coefficient"] * weighted[valid].sum()/max(reference_train,1)),
                ridge_base_weighted_normalized_squared_residual_sum=float(weighted[valid].sum()),
                weighted_residual_denominator="original full-TRAIN observed-root count; cell numerator only")


def fit_head(x, target, mask, spec, train):
    import numpy as np
    x=np.asarray(x,np.float64); y=np.asarray(target,np.float64); m=np.asarray(mask)>0
    nnw, counts, nroots=weights_for(y,m,spec,train)
    w=ridge_weights(y,m,spec)
    trainmask=np.zeros(m.shape,bool); trainmask[train]=m[train]
    flatx=x[trainmask]; flaty=y[trainmask]; flatw=w[trainmask]
    z=flaty if spec["binary"] else (flaty-spec["center"])/spec["scale"]
    design=np.concatenate((np.ones((len(flatx),1)),flatx),axis=1)
    if not len(flatx) or not flatw.any():
        beta=np.zeros(x.shape[-1]+1); fit=dict(status="unsupported-no-positive-weight", rank=0, condition=None, observations=len(flatx),coefficients=beta.tolist())
    else:
        weighted=design*np.sqrt(flatw)[:,None]; response=z*np.sqrt(flatw)
        penalty=np.eye(design.shape[1]); penalty[0,0]=0
        augmented=np.concatenate((weighted,penalty),axis=0); augmented_y=np.concatenate((response,np.zeros(design.shape[1])))
        beta,residuals,rank,singular=np.linalg.lstsq(augmented,augmented_y,rcond=None)
        data_singular=np.linalg.svd(weighted,compute_uv=False); data_rank=int(np.linalg.matrix_rank(weighted))
        fit=dict(status="fitted-fixed-lambda", observations=len(flatx), positive_weight_observations=int((flatw>0).sum()), observed_train_roots=nroots,
                 weighted_design_rank=data_rank, columns=design.shape[1], augmented_rank=int(rank),
                 weighted_design_condition=float(data_singular[0]/data_singular[-1]) if len(data_singular) and data_singular[-1]>np.finfo(float).eps*data_singular[0] and data_rank==design.shape[1] else None,
                 weighted_design_rank_deficient=data_rank<design.shape[1], augmented_condition=float(singular[0]/singular[-1]),
                 weighted_squared_residual_sum=float(((design@beta-z)**2*flatw).sum()), penalty_squared_slopes=float((beta[1:]**2).sum()),
                 total_objective=float(((design@beta-z)**2*flatw).sum()+(beta[1:]**2).sum()), weights=flatw.tolist(),
                 train_targets_native=flaty.tolist(), train_targets_normalized=z.tolist(), coefficients=beta.tolist(), ridge_lambda=1., intercept_penalized=False)
        fit.update(ridge_weight_sum=float(flatw.sum()),original_neural_weight_sum=float(nnw[trainmask].sum()),
                   original_neural_weights=nnw[trainmask].tolist(),original_head_coefficient=spec["loss_coefficient"],
                   original_neural_observed_root_denominator=nroots,
                   weight_scope="Ridge omits neural coefficient and observed-root denominator; same relative TRAIN sign/root weights.")
    raw=x@beta[1:]+beta[0]
    native=raw if spec["binary"] else raw*spec["scale"]+spec["center"]
    scored=np.clip(native,0,1) if spec["binary"] else native
    return scored,native,fit


def score_all(predictions, arrays, prior, cells):
    result={}
    for cell,indices in cells.items():
        result[cell]={}
        for kind,h,ykey,mkey,spec in head_records(arrays,prior):
            counts=arrays[mkey][cells["train"],...,h]
            reference=int((counts.sum(-1)>0).sum()) if counts.ndim==2 else int((counts>0).sum())
            result[cell][spec["name"]]=metrics(predictions[kind][indices,...,h],arrays[ykey][indices,...,h],arrays[mkey][indices,...,h],spec,reference)
    return result


def consumed_input_conflicts(arrays,prior,train):
    """Saved actual typed-tensor/context/candidate hashes; no mask in key."""
    records=prior["input_audits"]["typed"]["input_records"]
    seen={};conflicts=[];observed=0;root_set=set(int(i)for i in train)
    source_specs=prior["scalers"]["source_targets"];target_specs=prior["scalers"]["targets"]
    for record in records:
        root=record["root"]
        if root not in root_set:continue
        source=record["kind"]=="source";j=record["candidate"]
        y=arrays["source_targets"][root]if source else arrays["targets"][root,j]
        mask=arrays["source_mask"][root]if source else arrays["target_mask"][root,j]
        specs=source_specs if source else target_specs
        for h,spec in enumerate(specs):
            if not mask[h]:continue
            observed+=1;key=(record["kind"],record["input_sha256"],spec["name"]);value=float(y[h]);old=seen.get(key)
            if old is not None and old["value"]!=value:conflicts.append(dict(kind=record["kind"],head=spec["name"],input_sha256=record["input_sha256"],first=old,second=dict(root=root,candidate=j,value=value)))
            else:seen[key]=dict(root=root,candidate=j,value=value)
    return dict(known_observations=observed,unique_input_head_pairs=len(seen),conflict_count=len(conflicts),conflicts=conflicts,
                scope="TRAIN only; prior actual consumed typed tensor/context/localcandidate signatures; source includes intended candidate. Labels/masks are not input keys.")


def legality_check(arrays, prior, shared, wire_audit, native_plan):
    import numpy as np
    require(wire_audit["status"]=="PASS-data-contract" and wire_audit["fit_gate"]=="PASS" and not wire_audit["fit_blockers"], "prior independent wire audit failed")
    require(all(wire_audit[key] for key in ("privacy_checks_passed","preserved_unknown_masks","all_original_units_survive","no_xp_hook_observed")), "wire/privacy/no-death scope changed")
    require(not wire_audit["input_conflicts"] and not wire_audit["errors"] and not wire_audit["pending"], "known prior input/settlement conflict")
    require(wire_audit["sources"]["dataset"]["sha256"]==DATA_SHA, "wire audit covers another dataset")
    cells=partitions(arrays,prior); require({k:len(v)for k,v in cells.items()}==dict(train=21,family_held=15,state_held=7,joint=5), "frozen split changed")
    require(shared["train_indices"]==cells["train"].tolist(), "neural/baseline TRAIN rows differ")
    require(shared["target_names"]==native_plan["target_names"], "joint head order differs")
    for i,(code,family)in enumerate(zip(arrays["source_cards"],arrays["state_families"])):
        specs=native_plan["query_specs"][str(code)]; q=specs[int(family)] if isinstance(specs,list) else specs[str(int(family))]
        selected=int(arrays["selected_candidate_indices"][i]);require(native_plan["candidate_order"][selected]==q["ref"],"selected before-state intent changed")
        require(not arrays["target_mask"][i,np.arange(8)!=selected,2:].any(),"unchosen target future got a fabricated label")
        require(q["mode"]!="self-entry"or not arrays["target_mask"][i,:,2:].any(),"self-entry duplicated target effects")
    for key in ("source_mask","target_mask"):
        require(np.isin(arrays[key],[0,1]).all(),"nonbinary known mask")
    return dict(status="PASS-saved-wire-audit-and-role-recheck",roots=48,native_applies_previously_observed=87,
                fresh_native_applies=0,privacy_reconstructed_now=False,scope="Pins the independent native wire audit; rechecks NPZ roles/masks/split without engine reexecution.")


def saved_neural_metrics(fit_dir,shared_pin,arrays,assigned,prior,cells,shared):
    import numpy as np
    require(fit_dir.is_dir(),"neural fit must finish before this one data-analysis stage")
    used=[p for p in sorted(fit_dir.iterdir())if p.is_file()]
    pins=[pin(p)for p in used];result=read(fit_dir/"result.json")
    require(result["status"]=="completed"and result["plan"]==shared_pin and result["semantic_validated"]is False,"saved neural result/plan mismatch")
    require(result["counts"]==dict(optimizer_updates=900,training_forwards=900,evaluation_forwards=6,export_forwards=0,backwards=900),"saved neural counts differ")
    contract=read(fit_dir/"contract.json")
    require(contract["scalers"]==prior["scalers"]and contract["plan"]==shared_pin,"saved neural transforms changed")
    with np.load(fit_dir/"shuffle-schedules.npz",allow_pickle=False)as schedules:
        for key in("train_indices","shuffle_roots","fixed_mapping","fresh_mappings"):
            require(np.array_equal(schedules[key],np.asarray(shared[key])),"saved neural shuffle schedule differs: "+key)
    output={}
    for arm in("correct","fixed-shuffle","fresh-shuffle"):
        output[arm]={}
        for step in(0,300):
            with np.load(fit_dir/f"{arm}-step{step}-predictions.npz",allow_pickle=False)as p:
                source,branch=p["source"].copy(),p["branch"].copy()
                require(source.shape==(48,9)and branch.shape==(48,8,7)and np.isfinite(source).all()and np.isfinite(branch).all(),"saved neural prediction ABI/finite")
                for key in("source_cards","state_families","selected_candidate_indices"):
                    require(np.array_equal(p[key],arrays[key]),"prediction row pairing differs")
            predictions=dict(source=source,target=branch)
            output[arm][str(step)]=dict(metrics_TRUE=score_all(predictions,arrays,prior,cells),
                metrics_ASSIGNED_TRAIN=score_all(predictions,assigned if arm=="fixed-shuffle"else arrays,prior,{"train":cells["train"]})if arm!="fresh-shuffle"else None,
                assigned_scope="Fixed joint packets"if arm=="fixed-shuffle"else"No stable assigned target across fresh-shuffle updates"if arm=="fresh-shuffle"else"Original TRUE labels")
    verify_pins(pins)
    return output,pins


def run(plan_path,out,neural_fit=None):
    import numpy as np
    plan=read(plan_path);require(plan["config"]==CONFIG and plan["source"]==pin(__file__),"frozen analysis source/config changed")
    require(not out.exists(),"preserve prior audit/baseline attempt")
    verify_pins(plan["pins"])
    shared=read(plan["inputs"]["sanity_plan"]["path"]);prior=read(plan["inputs"]["prior_plan"]["path"])
    old_result=read(plan["inputs"]["old_result"]["path"]);wire=read(plan["inputs"]["wire_audit"]["path"]);native_plan=read(prior["native_plan"])
    with np.load(plan["inputs"]["dataset"]["path"],allow_pickle=False)as packed:arrays={k:packed[k].copy()for k in packed.files}
    cells=partitions(arrays,prior); legal=legality_check(arrays,prior,shared,wire,native_plan)
    assigned=fixed_assignment(arrays,shared,cells["train"])
    conflicts={name:consumed_input_conflicts(data,prior,cells["train"])for name,data in(("correct",arrays),("fixed-shuffle",assigned))}
    for name,diagnostic in conflicts.items():
        require(diagnostic["conflict_count"]==shared["TRAIN_input_conflicts"][name]["conflict_count"],"independent assigned conflict count differs from frozen neural audit")
    raw_source,raw_target=features(arrays,prior)
    source,source_transform=standardize(raw_source,cells["train"]);target,target_transform=standardize(raw_target,cells["train"])
    transforms=dict(source=source_transform,target=target_transform)
    audit={}; effective={}; old_metrics={}
    for kind,h,ykey,mkey,spec in head_records(arrays,prior):
        y,m=arrays[ykey][...,h],arrays[mkey][...,h]
        audit[spec["name"]]=dict(training_spec=spec,cells={cell:support(y[ix],m[ix])for cell,ix in cells.items()},
            train_by_card={code:support(y[ix],m[ix])for code in prior["train_codes"]for ix in[cells["train"][arrays["source_cards"][cells["train"]]==code]]})
    # Explicit recipient records make rare-root leverage and objective weighting
    # auditable. Missing labels never enter this list as negative observations.
    for label_arm,data in (("correct",arrays),("fixed-shuffle",assigned)):
        effective[label_arm]={}
        for kind,h,ykey,mkey,spec in head_records(data,prior):
            y,m=data[ykey][...,h],data[mkey][...,h];w,counts,nroots=weights_for(y,m,spec,cells["train"]);basew=ridge_weights(y,m,spec);records=[]
            for i in cells["train"]:
                positions=np.flatnonzero(m[i]) if m.ndim==2 else ([None]if m[i]else[])
                for j in positions:
                    value=float(y[i,j]if j is not None else y[i]);sign=str(int(np.sign(value)))
                    records.append(dict(root=int(i),card=str(data["source_cards"][i]),candidate=None if j is None else int(j),native_assigned_label=value,
                        original_head_coefficient=spec["loss_coefficient"],original_sign_class_weight=spec["class_weights"][sign],
                        train_observed_root_denominator=nroots,root_candidate_mask_count=int(counts[i]),original_neural_weight=float(w[i,j]if j is not None else w[i]),
                        ridge_base_weight=float(basew[i,j]if j is not None else basew[i])))
            effective[label_arm][spec["name"]]=dict(coordinates=records,ridge_base_weight_sum=sum(r["ridge_base_weight"]for r in records),
                original_neural_weight_sum=sum(r["original_neural_weight"]for r in records))
    for arm,record in old_result["results"].items():
        old_metrics[arm]={step:{cell:record["evaluations"][step]["cells"][cell]["heads"]for cell in cells}for step in("0","200")}
    baselines={};predictions={};fits={}
    for label_arm,data in (("correct",arrays),("fixed-shuffle",assigned)):
        scored=dict(source=np.zeros((48,9)),target=np.zeros((48,8,7)));raw={k:v.copy()for k,v in scored.items()};fits[label_arm]={}
        for kind,h,ykey,mkey,spec in head_records(data,prior):
            scored[kind][...,h],raw[kind][...,h],fits[label_arm][spec["name"]]=fit_head(source if kind=="source"else target,data[ykey][...,h],data[mkey][...,h],spec,cells["train"])
        predictions[label_arm]=dict(scored=scored,raw=raw)
        baselines[label_arm]=dict(metrics_TRUE=score_all(scored,arrays,prior,cells),metrics_ASSIGNED_TRAIN=score_all(scored,data,prior,{"train":cells["train"]}),
            raw_unclipped_metrics_TRUE=score_all(raw,arrays,prior,cells),fit_details=fits[label_arm])
    constants={}
    for control in("train-mean","zero"):
        pred=dict(source=np.zeros((48,9)),target=np.zeros((48,8,7)))
        for kind,h,ykey,mkey,spec in head_records(arrays,prior):
            observed=arrays[ykey][cells["train"],...,h][arrays[mkey][cells["train"],...,h]>0]
            if control=="train-mean"and len(observed):pred[kind][...,h]=observed.mean()
        constants[control]=score_all(pred,arrays,prior,cells)
    fit_dir=pathof(neural_fit or plan["neural_fit_dir"])
    require(str(fit_dir)==plan["neural_fit_dir"],"neural input directory differs from prepared plan")
    neural,neural_pins=saved_neural_metrics(fit_dir,plan["inputs"]["sanity_plan"],arrays,assigned,prior,cells,shared)
    require(neural_pins==plan["neural_input_pins"],"neural input file set changed after preparation")
    verify_pins(plan["pins"])
    out.mkdir(parents=True)
    for arm,values in predictions.items():np.savez_compressed(out/(arm+"-predictions.npz"),**{s+"_"+k:v for s,d in values.items()for k,v in d.items()})
    design=dict(source_features=source,target_features=target,raw_source_features=raw_source,raw_target_features=raw_target,
                source_targets=arrays["source_targets"],source_mask=arrays["source_mask"],targets_TRUE=arrays["targets"],targets_ASSIGNED_FIXED=assigned["targets"],target_mask=arrays["target_mask"],
                train_indices=cells["train"],source_cards=arrays["source_cards"],state_families=arrays["state_families"],selected_candidate_indices=arrays["selected_candidate_indices"])
    for arm,data in(("correct",arrays),("fixed-shuffle",assigned)):
        for kind,ykey,mkey,scalerkey in(("source","source_targets","source_mask","source_targets"),("target","targets","target_mask","targets")):
            w=np.zeros_like(data[ykey],np.float64);nnw=w.copy()
            for h,spec in enumerate(prior["scalers"][scalerkey]):
                w[...,h]=ridge_weights(data[ykey][...,h],data[mkey][...,h],spec)
                nnw[...,h]=weights_for(data[ykey][...,h],data[mkey][...,h],spec,cells["train"])[0]
            design[arm.replace("-","_")+"_"+kind+"_ridge_weights"]=w
            design[arm.replace("-","_")+"_"+kind+"_neural_weights"]=nnw
    np.savez_compressed(out/"design.npz",**design)
    result=dict(schema="learning-sanity-data-result/1",status="completed-data-analysis",plan=pin(plan_path),source=pin(__file__),
                config=CONFIG,legal_state_target_pairing=legal,transforms=transforms,label_audit=audit,effective_sample_weights=effective,assigned_input_conflicts=conflicts,
                old_saved_head_metrics=old_metrics,neural_saved_prediction_metrics=neural,neural_input_pins=neural_pins,
                ridge=baselines,constants=constants,inputs_unchanged=True,design=pin(out/"design.npz"),
                compute=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,closed_form_head_fits=32),semantic_validated=False,
                limitations=["Fixed weighted least squares is not neural Huber/BCE and has less rule information than typed IR.",
                    "Good TRAIN fit may memorize public printed/state/card proxies and does not validate semantic transfer.",
                    "No held selection, tuning or representation change; prior held-family failure remains unchanged. Held data were already consumed in that earlier round; current held readouts are descriptive."])
    write(out/"result.json",result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare",action="store_true");g.add_argument("--run",action="store_true")
    p.add_argument("--sanity-plan",type=Path,default=DEFAULT/"sanity-plan.json");p.add_argument("--plan",type=Path,default=DEFAULT/"data-plan.json");p.add_argument("--out",type=Path,default=DEFAULT/"data-analysis-1")
    p.add_argument("--neural-fit",type=Path)
    a=p.parse_args()
    if a.prepare:prepare(a.sanity_plan,a.plan,a.neural_fit);print(json.dumps(pin(a.plan)))
    else:run(a.plan,a.out,a.neural_fit);print(json.dumps(pin(a.out/"result.json")))


if __name__=="__main__":main()
