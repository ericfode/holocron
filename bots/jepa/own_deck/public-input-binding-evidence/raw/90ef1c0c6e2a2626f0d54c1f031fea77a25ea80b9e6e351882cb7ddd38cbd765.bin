"""Fixed-width native effect-identifiability experiment; preparation is pure.

Rich and sparse typed arms differ only in training observation masks. New
categorical table/cardinality counts are frozen publicly before labels. The
16d encoder, typed paths, numeric channels and prediction widths stay fixed.
"""
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key]="1"
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ROOT=REPO.parent/"experiments"
DEFAULT=ROOT/"effect-identifiability-v2"
PR35_SHA="b310315d153b3cdfe3439c4f242d9b07e07a1c2ce16c46ede4cf9084a8e0d8a2"
ARMS=("rich-typed","sparse-typed","rich-id-only","rich-untrained-typed","rich-wrong-typed")
DISPLAY_KEYS={"title","contextTitle","promptTitle"}
TARGET_EFFECTS=("target_damage_delta","target_exhausted_delta","target_shield_delta","target_power_delta","target_hp_delta")
MECHANICS={"damage":("target_damage_delta",),"exhaustion":("target_exhausted_delta",),"shield":("target_shield_delta",),"stats":("target_power_delta","target_hp_delta")}
CONFIG=dict(seed=17,arms=list(ARMS),updates_per_arm=200,batch_size=18,optimizer_updates=1000,training_forwards=1000,
            evaluation_forwards=11,export_forwards=0,backwards=1000,learning_rate=.003,weight_decay=.0001,clip_l2=1.,
            width=16,max_tokens=512,max_path=32,fit_seconds=60,threads=1,rss_bytes=1073741824,paid_jobs=0,
            primary_relative_error_reduction=.10,contrast_direction_accuracy=.75)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def prior():
    if sha(HERE/"whole_card_encoder.py")!=PR35_SHA:raise ValueError("immutable PR35 frontend/model source differs")
    sys.path.insert(0,str(HERE));import whole_card_encoder as W
    return W


def canonical_document(row):
    """Reviewed display cleanup and lexical callback alpha-normalization.

    Display expressions are UI annotations, not rule effects. Only the reviewed
    event dataPath argumentBinding shape is rewritten. Scoped equality and
    invocation/read timing remain explicit; no generic identity key is admitted.
    """
    W=prior();row=copy.deepcopy(row);audit={"display_paths":[],"callback_occurrences":[]}
    def clean(value,path,scope,mapping):
        if isinstance(value,list):
            return [clean(child,path+(i,),scope,mapping)for i,child in enumerate(value)]
        if not isinstance(value,dict):
            if isinstance(value,str)and value.startswith("callback:"):raise ValueError("unreviewed callback reference outside argumentBinding")
            return value
        if value.get("kind")=="const"and isinstance(value.get("value"),(dict,list)):raise ValueError("structured rule literals require explicit review; never strip their fields")
        out={}
        for key in sorted(value):
            child=value[key]
            if key in DISPLAY_KEYS:
                audit["display_paths"].append(list(path+(key,)));continue
            if key=="hooks":
                if not isinstance(child,list):raise ValueError("ordered hook invocation scopes required")
                out[key]=[clean(hook,path+(key,i),scope+("hook",i),{})for i,hook in enumerate(child)];continue
            if key=="argumentBinding":
                if value.get("kind")!="dataPath"or value.get("root")!=["event"] or not isinstance(child,dict)or set(child)!={"id","bindAt","readAt"}or child["bindAt"]!="callbackInvocation"or child["readAt"]!="expressionEvaluation"or not isinstance(child["id"],str)or not re.fullmatch(r"callback:\d+:\d+",child["id"]):
                    raise ValueError("unreviewed callback binding semantics")
                if child["id"]not in mapping:mapping[child["id"]]=len(mapping)
                out[key]=dict(binding_scope=list(scope),binding_slot=mapping[child["id"]],bindAt=child["bindAt"],readAt=child["readAt"])
                audit["callback_occurrences"].append(dict(path=list(path+(key,)),scope=list(scope),slot=mapping[child["id"]]));continue
            out[key]=clean(child,path+(key,),scope,mapping)
        return out
    for side,abilities in row["abilities"].items():
        row["abilities"][side]=[clean(ability,("abilities",side,i),("ability",side,i),{})for i,ability in enumerate(abilities)]
    document=W.card_document(row);W.tokens(document)
    return document,audit


def frontend_fingerprint():
    tree=ast.parse(Path(__file__).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="canonical_document")
    return dict(schema="effect-card-cleanup/1",canonical_function_ast_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),prior_source_sha256=PR35_SHA,display_keys=sorted(DISPLAY_KEYS))


def symbols_for(documents):return prior().symbols_for(documents)


def make_bank(documents,codes,train_codes,symbols,training=False):
    import numpy as np
    W=prior();n=len(codes)
    if len(set(codes))!=n or len(documents)!=n or not set(train_codes)<=set(codes):raise ValueError("unique frozen card bank required")
    lookup={k:{v:i for i,v in enumerate(values)}for k,values in symbols.items()}
    numbers=[value for code,doc in zip(codes,documents)if code in train_codes for _,kind,value in W.tokens(doc)if kind in("number","length")]
    scale=max(1.,float(np.std(numbers)))if numbers else 1.
    bank=dict(path_ids=np.zeros((n,512,32),np.int64),path_lengths=np.zeros((n,512),np.int64),type_ids=np.zeros((n,512),np.int64),value_ids=np.zeros((n,512),np.int64),numeric=np.zeros((n,512,2),np.float32),token_mask=np.zeros((n,512),np.float32),slot_mask=np.ones(n,np.float32),identity_indices=np.asarray([train_codes.index(code)+1 if code in train_codes else 0 for code in codes],np.int64))
    for slot,doc in enumerate(documents):
        for pos,(path,kind,value)in enumerate(W.tokens(doc)):
            try:
                ids=[lookup["path"][("index:"if type(k)is int else"key:")+str(k)]for k in path]
                bank["type_ids"][slot,pos]=lookup["type"][kind];bank["value_ids"][slot,pos]=lookup["value"]["NUMBER"if kind in("number","length")else kind+":"+str(value)]
            except KeyError as error:raise ValueError("unreviewed symbol; no remap")from error
            bank["path_ids"][slot,pos,:len(ids)]=ids;bank["path_lengths"][slot,pos]=len(ids);bank["token_mask"][slot,pos]=1
            if kind in("number","length"):bank["numeric"][slot,pos]=(value/scale,np.sign(value)*np.log1p(abs(value)))
        if training and codes[slot]not in train_codes:
            for value in bank.values():value[slot]=0
    return bank,scale


def tensor_signatures(bank):
    output=[]
    for slot in range(len(bank["slot_mask"])):
        h=hashlib.sha256()
        for key in sorted(bank):
            if key=="identity_indices":continue
            v=bank[key][slot];h.update(key.encode()+str(v.dtype).encode()+str(v.shape).encode()+v.tobytes())
        output.append(h.hexdigest())
    return output


def training_masks(arrays,train_indices,target_names,arm):
    """Sparse mask repeats PR35's absent five stat-delta supervision exactly."""
    import numpy as np
    source=arrays["source_mask"].copy();target=arrays["target_mask"].copy()
    if arm not in ARMS:raise ValueError("unreviewed mask arm")
    if arm=="sparse-typed":
        for name in TARGET_EFFECTS:target[np.asarray(train_indices),:,target_names.index(name)]=0
    return dict(source_mask=source,target_mask=target)


def exact_input_conflicts(arrays,manifest,documents,codes,context,candidates,representation="typed",train_codes=None,query_codes=None):
    """Actual source/branch visible inputs → co-observed native label conflicts.

    Source keys include public intent; per-candidate keys cannot borrow it.
    A separate provenance key records intent and masks without hiding a conflict.
    Unknown labels never create conflicts; their masks remain audited.
    """
    import numpy as np
    bank,_=make_bank(documents,codes,list(train_codes)if train_codes is not None else list(codes),symbols_for(documents),False)
    groups=dict(zip(codes,tensor_signatures(bank)));seen={};conflicts=[];records=[]
    if representation=="id-only":
        if train_codes is None:raise ValueError("ID-visible contract requires frozen training table")
        groups={code:"identity:"+str(train_codes.index(code)+1 if code in train_codes else 0)for code in codes}
    elif representation not in("typed","wrong-eval"):raise ValueError("unreviewed input representation")
    def key(code,x,c):return hashlib.sha256(groups[code].encode()+np.asarray(x,np.float32).tobytes()+np.asarray(c,np.float32).tobytes()).hexdigest()
    for i,code in enumerate(arrays["source_cards"].astype(str)):
        visible_code=code if query_codes is None else str(query_codes[i])
        chosen=int(arrays["selected_candidate_indices"][i]);source=key(visible_code,context[i],candidates[i,chosen])
        for category,names,targets,masks in(("source",manifest["source_head_names"],arrays["source_targets"][i:i+1],arrays["source_mask"][i:i+1]),("candidate",manifest["target_names"],arrays["targets"][i],arrays["target_mask"][i])):
            for j in range(len(targets)):
                signature=source if category=="source"else key(visible_code,context[i],candidates[i,j])
                records.append(dict(root=i,candidate=None if category=="source"else j,kind=category,input_sha256=signature,intended_candidate=chosen,mask=masks[j].tolist()))
                for h,name in enumerate(names):
                    if masks[j,h]<=0:continue
                    identity=(category,signature,name);value=float(targets[j,h]);old=seen.get(identity)
                    if old is not None and old[0]!=value:conflicts.append(dict(kind=category,head=name,input_sha256=signature,old_root=old[1],root=i,old_value=old[0],value=value))
                    else:seen[identity]=(value,i)
    return dict(representation=representation,conflicts=conflicts,conflict_count=len(conflicts),input_records=records,rule="Actual arm-visible semantic tensor/ID table contract; held IDs shareUNK0. Source includes intended candidate; branch onlyitsowncandidate. Masks/intent recorded separately; missing labels never become0.")


def partition(arrays,split):
    import numpy as np
    train=np.isin(arrays["source_cards"],split["train_codes"]);state=np.isin(arrays["state_families"],split["train_state_families"])
    return dict(train=np.flatnonzero(train&state),family_held=np.flatnonzero(~train&state),state_held=np.flatnonzero(train&~state),joint=np.flatnonzero(~train&~state))


def common_scalers(arrays,manifest,train):
    import numpy as np
    result={}
    for key in("context_features","candidate_features"):
        a=arrays[key][train];axes=tuple(range(a.ndim-1));result[key]=dict(center=a.mean(axes).tolist(),scale=np.maximum(1,a.std(axes)).tolist())
    for key,mkey,nkey,bkey in(("source_targets","source_mask","source_head_names","source_binary_heads"),("targets","target_mask","target_names","binary_heads")):
        result[key]=[]
        for h,name in enumerate(manifest[nkey]):
            y=arrays[key][train,...,h];m=arrays[mkey][train,...,h]>0;v=y[m];binary=name in manifest[bkey]
            zero=int((v==0).sum());nonzero=int((v!=0).sum());negative=int((v<0).sum());positive=int((v>0).sum())
            counts={str(sign):int((np.sign(v)==sign).sum())for sign in(-1,0,1)};classes=sum(n>0 for n in counts.values())
            weights={sign:(len(v)/(classes*n)if n else 0.)for sign,n in counts.items()}
            result[key].append(dict(name=name,binary=binary,known=len(v),varying=len(np.unique(v))>1,center=0. if binary or not len(v)else float(v.mean()),scale=1. if binary or not len(v)else max(1.,float(v.std())),values=np.unique(v).tolist(),zero=zero,nonzero=nonzero,negative=negative,positive=positive,class_weights=weights))
    primary=sum(r["varying"]for k in("source_targets","targets")for r in result[k]);constant=sum(r["known"]>0 and not r["varying"]for k in("source_targets","targets")for r in result[k])
    for key in("source_targets","targets"):
        for r in result[key]:r["loss_coefficient"]=(1./primary if r["varying"]else .1/constant if r["known"]and constant else 0.)
    result["control_information"]="All arms share rich-TRAIN support, head set, coefficients and numeric transforms. Sparse training only changes observation masks. No held statistics. Missing heads contribute0 to the fixed denominator."
    return result


def behavioral_support(arrays,manifest,scalers,split):
    """Eligibility uses TRAIN only; lack of support remains an explicit result."""
    train=partition(arrays,split)["train"];groups={};eligible=[]
    for mechanic,names in MECHANICS.items():
        specs=[scalers["targets"][manifest["target_names"].index(n)]for n in names]
        ok=all(s["zero"]>=2 and s["nonzero"]>=2 and s["known"]>=4 for s in specs)
        groups[mechanic]=dict(heads=list(names),eligible=ok,minimum="at least2 observedzero and2 nonzero training coordinates; per-card/sign support reported, repeated contexts are not independent families",training_support=specs)
        if ok:eligible.append(mechanic)
    return dict(mechanics=groups,eligible_mechanics=eligible,minimum_held_families=2,minimum_held_program_groups=3,
                gate="Before semantics: ≥10% family-first target-effect MAE reduction versus each eligible rich ID/untrained/wrong/train-prior control AND sparse typed, plus≥.75 direction accuracy on predeclared native contrast pairs; report all held families and negative heads. Support failure is unsupported, not success.")


FAMILY_MECHANICS={"pointed-unit-friendly-space-count-damage":("damage","shield"),"pointed-unit-event-stat-debuff":("stats",),"attached-host-exhaust":("exhaustion","stats")}


def make_model(torch,symbols,n_cards,n_train):
    """PR35 widths/modules; only public symbol/identity table cardinality varies."""
    nn=torch.nn
    class Effects(nn.Module):
        def __init__(self):
            super().__init__()
            self.edge=nn.Embedding(len(symbols["path"]),16,padding_idx=0);self.depth=nn.Parameter(torch.randn(32,16)/4)
            self.kind=nn.Embedding(len(symbols["type"]),16,padding_idx=0);self.value=nn.Embedding(len(symbols["value"]),16,padding_idx=0);self.numeric=nn.Linear(2,16)
            self.leaf=nn.Sequential(nn.Linear(32,32),nn.Tanh(),nn.Linear(32,16),nn.Tanh());self.card_projection=nn.Sequential(nn.Linear(16,16),nn.LayerNorm(16))
            self.identity=nn.Embedding(n_train+1,16,padding_idx=0);self.context=nn.Sequential(nn.Linear(18,16),nn.Tanh(),nn.LayerNorm(16));self.candidate=nn.Sequential(nn.Linear(34,16),nn.Tanh(),nn.LayerNorm(16))
            self.source_head=nn.Sequential(nn.Linear(80,32),nn.Tanh(),nn.Linear(32,9));self.branch_head=nn.Sequential(nn.Linear(80,32),nn.Tanh(),nn.Linear(32,7))
        def card_bank(self,bank):
            slot,pos=torch.nonzero(bank["token_mask"]*bank["slot_mask"][:,None],as_tuple=True);ids=bank["path_ids"][slot,pos]
            mask=torch.arange(32,device=ids.device)<bank["path_lengths"][slot,pos,None]
            path=(self.edge(ids)*self.depth*mask[...,None]).sum(1)
            value=self.kind(bank["type_ids"][slot,pos])+self.value(bank["value_ids"][slot,pos])+self.numeric(bank["numeric"][slot,pos])
            leaves=self.leaf(torch.cat((path,value),-1));pool=torch.zeros((n_cards,16),dtype=leaves.dtype,device=leaves.device).index_add(0,slot,leaves)
            return self.card_projection(pool/bank["token_mask"].sum(1,keepdim=True).clamp(min=1))*bank["slot_mask"][:,None]
        def forward(self,x,c,q,bank,arm,selected):
            semantic=self.card_bank(bank)
            vectors=torch.nn.functional.layer_norm(self.identity(bank["identity_indices"]),(16,))if arm=="rich-id-only"else semantic
            p=vectors[q];s=self.context(x);candidate=self.candidate(c);t=candidate[torch.arange(len(c),device=c.device),selected]
            source=self.source_head(torch.cat((p,s,t,p*s,p*t),-1));pp=p[:,None,:].expand_as(candidate);ss=s[:,None,:].expand_as(candidate)
            return source,self.branch_head(torch.cat((pp,ss,candidate,pp*ss,pp*candidate),-1)),vectors
    return Effects()


def configure_arm(model,arm):
    prefixes=prior().ENCODER_PREFIXES
    for name,p in model.named_parameters():
        encoder=any(name.startswith(prefix)for prefix in prefixes)
        p.requires_grad=(not encoder if arm in("rich-untrained-typed","rich-id-only")else True)and(not name.startswith("identity.")or arm=="rich-id-only")


def fixed_loss(torch,source,branch,labels,scalers):
    """Fixed rich-TRAIN denominator/classes; absent sparse terms contribute0."""
    total=source.sum()*0
    for prediction,key,mkey in((source,"source_targets","source_mask"),(branch,"targets","target_mask")):
        for h,spec in enumerate(scalers[key]):
            target=labels[key][...,h];mask=labels[mkey][...,h]
            if not spec["loss_coefficient"]or not bool(mask.any()):continue
            element=torch.nn.functional.binary_cross_entropy_with_logits(prediction[...,h],target,reduction="none")if spec["binary"]else torch.nn.functional.smooth_l1_loss(prediction[...,h],(target-spec["center"])/spec["scale"],reduction="none")
            weights=spec["class_weights"];weight=torch.where(target<0,weights["-1"],torch.where(target>0,weights["1"],weights["0"]))
            if mask.ndim>1:
                support=mask.sum(-1);values=(element*weight*mask).sum(-1)/support.clamp(min=1);values=values[support>0]
            else:values=(element*weight)[mask>0]
            total=total+spec["loss_coefficient"]*values.mean()
    return total


def scale_inputs(arrays,scalers):
    import numpy as np
    return tuple((arrays[key]-np.asarray(scalers[key]["center"],np.float32))/np.asarray(scalers[key]["scale"],np.float32)for key in("context_features","candidate_features"))


def head_metrics(source,branch,arrays,manifest,scalers,indices):
    import numpy as np
    result={}
    for prediction,key,mkey in((source,"source_targets","source_mask"),(branch,"targets","target_mask")):
        for h,spec in enumerate(scalers[key]):
            target=arrays[key][indices,...,h];mask=arrays[mkey][indices,...,h];pred=prediction[indices,...,h]
            support=mask if mask.ndim==1 else mask.sum(-1);valid=support>0
            def mean(v):return v if mask.ndim==1 else(v*mask).sum(-1)/np.maximum(support,1)
            error=mean(abs(pred-target));bias=mean(pred-target);observed=target[mask>0];positive=(target==1)&(mask>0);negative=(target==0)&(mask>0)
            tp=int(((pred>=.5)&positive).sum());tn=int(((pred<.5)&negative).sum());npositive=int(positive.sum());nnegative=int(negative.sum())
            sensitivity=tp/npositive if spec["binary"]and npositive else None;specificity=tn/nnegative if spec["binary"]and nnegative else None
            result[spec["name"]]=dict(observed_roots=int(valid.sum()),known_coordinates=int(mask.sum()),mae=float(error[valid].mean())if valid.any()else None,train_scaled_mae=float(error[valid].mean()/spec["scale"])if valid.any()else None,
                signed_residual=float(bias[valid].mean())if valid.any()else None,native_values=np.unique(observed).tolist(),zero=int((observed==0).sum()),positive=int((observed>0).sum()),negative=int((observed<0).sum()),
                binary_accuracy=float(mean(((pred>=.5)==target).astype(float))[valid].mean())if valid.any()and spec["binary"]else None,sensitivity=sensitivity,specificity=specificity,balanced_accuracy=(sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,training_support=spec)
    return result


def family_metrics(branch,arrays,manifest,scalers,support,indices):
    import numpy as np
    family_by_code={c:record["family"]for c,record in manifest["cards"].items()};output={}
    for family,mechanics in FAMILY_MECHANICS.items():
        rows=[int(i)for i in indices if family_by_code[str(arrays["source_cards"][i])]==family];groups={}
        for mechanic in mechanics:
            values=[];heads={}
            for name in MECHANICS[mechanic]:
                h=manifest["target_names"].index(name);m=arrays["target_mask"][rows,:,h];target=arrays["targets"][rows,:,h];pred=branch[rows,:,h]
                count=m.sum(-1);valid=count>0;errors=(abs(pred-target)*m).sum(-1)/np.maximum(count,1);metric=float(errors[valid].mean()/scalers["targets"][h]["scale"])if valid.any()else None
                heads[name]=dict(known_coordinates=int(m.sum()),observed_roots=int(valid.sum()),train_scaled_mae=metric,zero=int(((target==0)&(m>0)).sum()),nonzero=int(((target!=0)&(m>0)).sum()),eligible=support["mechanics"][mechanic]["eligible"])
                if metric is not None and support["mechanics"][mechanic]["eligible"]:values.append(metric)
            groups[mechanic]=dict(heads=heads,mae=float(np.mean(values))if len(values)==len(MECHANICS[mechanic])else None)
        means=[v["mae"]for v in groups.values()if v["mae"]is not None]
        observed_rows=[i for i in rows if any(support["mechanics"][m]["eligible"]and any(arrays["target_mask"][i,:,manifest["target_names"].index(n)].any()for n in MECHANICS[m])for m in mechanics)]
        output[family]=dict(roots=rows,declared_program_groups=sorted({manifest["cards"][str(arrays["source_cards"][i])]["normalized_program_group"]for i in rows}),program_groups=sorted({manifest["cards"][str(arrays["source_cards"][i])]["normalized_program_group"]for i in observed_rows}),mechanics=groups,mae=float(np.mean(means))if means else None)
    eligible=[v["mae"]for v in output.values()if v["mae"]is not None]
    return dict(families=output,family_first_mae=float(np.mean(eligible))if eligible else None,known_families=len(eligible),known_program_groups=len(set(g for v in output.values()if v["mae"]is not None for g in v["program_groups"])))


def contrast_metrics(branch,arrays,manifest,scalers,support=None):
    import numpy as np
    index={(str(c),int(s)):i for i,(c,s)in enumerate(zip(arrays["source_cards"],arrays["state_families"]))};pairs=[]
    for pair in manifest["plan"]["predeclared_behavior_pairs"]:
        left=index[(pair["left"]["card"],pair["left"]["state"])];right=index[(pair["right"]["card"],pair["right"]["state"])];a=int(arrays["selected_candidate_indices"][left]);b=int(arrays["selected_candidate_indices"][right]);heads=[]
        for name in pair["heads"]:
            h=manifest["target_names"].index(name);known=bool(arrays["target_mask"][left,a,h]and arrays["target_mask"][right,b,h])
            eligible=support is None or all(support["mechanics"][m]["eligible"]for m,names in MECHANICS.items()if name in names)
            if not known:heads.append(dict(head=name,known=False,eligible=eligible));continue
            truth=float(arrays["targets"][left,a,h]-arrays["targets"][right,b,h]);pred=float(branch[left,a,h]-branch[right,b,h])
            direction=int(abs(pred)<=.25)if abs(truth)<=.25 else int(pred>.25)if truth>.25 else int(pred<-.25)
            heads.append(dict(head=name,known=True,eligible=eligible,native_contrast=truth,predicted_contrast=pred,train_scaled_error=abs(pred-truth)/scalers["targets"][h]["scale"],direction_correct=direction))
        values=[v for v in heads if v["known"]and v["eligible"]];complete=len(values)==len(heads)
        pairs.append(dict(id=pair["id"],family=pair["family"],left_root=left,right_root=right,heads=heads,known=complete,mae=float(np.mean([v["train_scaled_error"]for v in values]))if complete else None,direction_accuracy=float(np.mean([v["direction_correct"]for v in values]))if complete else None))
    families={}
    for family in sorted({p["family"]for p in pairs}):
        known=[p for p in pairs if p["family"]==family and p["known"]];families[family]=dict(known_pairs=len(known),mae=float(np.mean([p["mae"]for p in known]))if known else None,direction_accuracy=float(np.mean([p["direction_accuracy"]for p in known]))if known else None)
    known=[f for f in families.values()if f["known_pairs"]]
    return dict(pairs=pairs,families=families,known_pairs=sum(f["known_pairs"]for f in known),known_families=len(known),family_first_mae=float(np.mean([f["mae"]for f in known]))if known else None,family_first_direction_accuracy=float(np.mean([f["direction_accuracy"]for f in known]))if known else None)


def evaluate_metrics(source,branch,arrays,manifest,plan):
    cells=partition(arrays,plan["split"])
    return dict(cells={name:dict(roots=len(indices),heads=head_metrics(source,branch,arrays,manifest,plan["scalers"],indices),per_card={code:head_metrics(source,branch,arrays,manifest,plan["scalers"],[i for i in indices if str(arrays["source_cards"][i])==code])for code in sorted({str(arrays["source_cards"][i])for i in indices})},behavior=family_metrics(branch,arrays,manifest,plan["scalers"],plan["behavioral_support"],indices))for name,indices in cells.items()},contrasts=contrast_metrics(branch,arrays,manifest,plan["scalers"],plan["behavioral_support"]))


def constant_baselines(arrays,manifest,plan):
    import numpy as np
    train=partition(arrays,plan["split"])["train"];values=[]
    for key,mkey in(("source_targets","source_mask"),("targets","target_mask")):
        means=[]
        for h in range(arrays[key].shape[-1]):
            known=arrays[key][train,...,h][arrays[mkey][train,...,h]>0];means.append(float(known.mean())if len(known)else 0.)
        values.append(np.broadcast_to(np.asarray(means,np.float32),arrays[key].shape).copy())
    return dict(train_constant=evaluate_metrics(*values,arrays,manifest,plan),zero_heads=evaluate_metrics(np.zeros_like(arrays["source_targets"]),np.zeros_like(arrays["targets"]),arrays,manifest,plan))


def behavioral_gate(evaluations,baselines):
    rich=evaluations["rich-typed"];controls={k:v for k,v in evaluations.items()if k!="rich-typed"};controls.update({k:baselines[k]for k in("train_constant","zero_heads")})
    primary=rich["cells"]["family_held"]["behavior"];eligible={k:v["cells"]["family_held"]["behavior"]["family_first_mae"]for k,v in controls.items()if v["cells"]["family_held"]["behavior"]["family_first_mae"]is not None}
    best=min(eligible.values())if len(eligible)==6 else None;error=primary["family_first_mae"]
    contrast=rich["contrasts"];comp={k:v["contrasts"]["family_first_mae"]for k,v in controls.items()if v["contrasts"]["family_first_mae"]is not None};cbest=min(comp.values())if len(comp)==6 else None
    support=primary["known_families"]>=2 and primary["known_program_groups"]>=3 and contrast["known_pairs"]>=4 and contrast["known_families"]>=2
    error_pass=best is not None and error is not None and best>0 and error<=.9*best
    contrast_pass=cbest is not None and cbest>0 and contrast["family_first_mae"]<=.9*cbest and contrast["family_first_direction_accuracy"]>=.75
    return dict(passed=bool(support and error_pass and contrast_pass),support_pass=support,primary_error_pass=error_pass,contrast_pass=contrast_pass,rich_primary_error=error,strongest_control_error=best,all_control_errors=eligible,rich_contrasts=contrast,strongest_control_contrast_error=cbest,all_control_contrast_errors=comp,interpretation="Selected-anchor held-template predictive gate only; no whole-card/all-state/playing-strength qualification. Failure does not identify capacity as the cause.")

ABI_KEYS=("candidate_order","context_feature_names","candidate_feature_names","source_head_names","source_binary_heads","target_names","binary_heads")
CONTRACT=ROOT/"actual-corpus/effect-cohort-audit-v1/strict12-contract-v3.json"
ACCOUNTING_SHA="a72d3ccc9bb381ba626032481d1bbb980236e302a6d532b0960e11445df8e0f9"


def pin(path):
    p=Path(path).resolve();return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def verify_pins(pins):
    for p in pins:
        path=Path(p["path"])
        if path.resolve()!=path or sha(path)!=p["sha256"]or("bytes"in p and path.stat().st_size!=p["bytes"]):raise ValueError("protected input differs: "+str(path))


def parameter_counts(symbols,n_train):
    encoder=2560+16*(len(symbols["path"])+len(symbols["value"]));identity=16*(n_train+1)
    allocated=9200+identity+16*(len(symbols["path"])+len(symbols["value"]))
    if len(symbols["type"])!=7:raise ValueError("fixed seven-type graph required")
    return dict(allocated=allocated,encoder=encoder,identity=identity,trainable={a:allocated-(encoder if a in("rich-id-only","rich-untrained-typed")else 0)-(0 if a=="rich-id-only"else identity)for a in ARMS},explanation="PR35 graph widths unchanged; public categorical/ID tables vary. Frozen/unused blocks remain allocated but are excluded from optimizer.")


def prepare(path,native_plan,contract_path=CONTRACT):
    if path.exists():raise FileExistsError("preserve existing preparation")
    native=read(native_plan);contract=read(contract_path);bycode={r["code"]:r for r in contract["cards"]};codes=[r["code"]for r in native["cards"]];train=native["split"]["train_codes"]
    if len(codes)!=12 or len(train)!=7 or len(set(codes))!=12 or set(codes)!=set(bycode):raise ValueError("frozen strict12 cohort required")
    docs=[];audits=[]
    for card in native["cards"]:
        doc,audit=canonical_document(card["raw_card"]);code=card["code"]
        if doc!=bycode[code]["normalized_document"]or digest(doc)!=bycode[code]["normalized_program_group"]:raise ValueError("canonical cohort contract differs: "+code)
        if (code in train)!=(bycode[code]["partition"]=="train"):raise ValueError("contract partition differs")
        docs.append(doc);audits.append(audit)
    for group in("normalized_program_group","exact_machine_program_group"):
        seen={}
        for code in codes:
            key=bycode[code][group];part=code in train
            if key in seen and seen[key]!=part:raise ValueError("program duplicate crosses partition")
            seen[key]=part
    symbols=symbols_for(docs);bank,numeric_scale=make_bank(docs,codes,train,symbols,False);signatures=tensor_signatures(bank)
    if len(set(signatures))!=12:raise ValueError("semantic input collision")
    train_docs=[d for c,d in zip(codes,docs)if c in train];train_symbols=symbols_for(train_docs)
    public_untrained_atoms={k:[v for v in symbols[k]if v not in train_symbols[k]]for k in symbols}
    old=ROOT/"whole-card";oldfit=old/"fit-1"
    files=[Path(__file__),HERE/"test_effect_identifiability_fit.py",HERE/"EFFECT_IDENTIFIABILITY_LEARNER_PROTOCOL.md",HERE/"EFFECT_IDENTIFIABILITY_HYPOTHESIS.md",HERE/"whole_card_encoder.py",native_plan,contract_path,DEFAULT/"accounting.py",DEFAULT/"freeze_campaign.py",old/"card-plan.json",oldfit/"contract.json",oldfit/"result.json",oldfit/"correct-typed-checkpoint.npz",oldfit/"correct-typed-step200-predictions.npz",ROOT/"actual-corpus/actual-corpus.npz",ROOT/"actual-corpus/actual-corpus.manifest.json"]
    for item in native.get("source_pins",[]):files.append(Path(item["path"]))
    pins=[pin(p)for p in sorted(set(Path(p).resolve()for p in files))]
    plan=dict(schema="native-effect-identifiability/2",status="prepared-no-execution",source_sha256=sha(__file__),config=CONFIG,codes=codes,train_codes=train,held_codes=native["split"]["heldout_codes"],split=native["split"],abi={k:native[k]for k in ABI_KEYS},documents=docs,document_sha256=[digest(d)for d in docs],frontend=frontend_fingerprint(),frontend_audits=audits,vocabularies=symbols,public_held_only_atoms=public_untrained_atoms,numeric_scale=numeric_scale,parameters=parameter_counts(symbols,len(train)),semantic_tensor_sha256=signatures,cohort_contract=str(contract_path.resolve()),native_plan=str(native_plan.resolve()),pins=pins,baseline_scope="One frozen PR35 diagnostic: exact old bank/transforms/head; only new TRAIN ASH048/JTL217 plus old replay anchors. No new held identity is supported.",semantic_validated=False)
    path.parent.mkdir(parents=True,exist_ok=True);write(path,plan);return plan


def joined_manifest(manifest,plan):
    m=copy.deepcopy(manifest);contract=read(plan["cohort_contract"]);cards={r["code"]:r for r in contract["cards"]}
    for code in plan["codes"]:
        if canonical_document(m["cards"][code]["raw_card"])[0]!=cards[code]["normalized_document"]:raise ValueError("saved native whole-card input differs")
        m["cards"][code]["normalized_program_group"]=cards[code]["normalized_program_group"]
    return m


def validate_data(arrays,manifest,plan):
    import numpy as np
    for key,shape in dict(context_features=(48,18),candidate_features=(48,8,34),source_targets=(48,9),source_mask=(48,9),targets=(48,8,7),target_mask=(48,8,7)).items():
        a=arrays[key]
        if a.shape!=shape or a.dtype!=np.float32 or not np.isfinite(a).all():raise ValueError("finite float32 ABI required: "+key)
        if key.endswith("mask")and not np.isin(a,[0,1]).all():raise ValueError("binary observation masks required")
    for key in ABI_KEYS:
        if manifest[key]!=plan["abi"][key]:raise ValueError("ordered public ABI differs: "+key)
    if arrays["source_cards"].shape!=(48,)or arrays["state_families"].shape!=(48,)or arrays["state_families"].dtype!=np.int64:raise ValueError("fixed root keys required")
    roots=[(str(c),int(s))for c,s in zip(arrays["source_cards"],arrays["state_families"])]
    if len(set(roots))!=48 or set(roots)!={(c,s)for c in plan["codes"]for s in range(4)}:raise ValueError("one exact root per card/world required")
    selected=arrays["selected_candidate_indices"]
    if selected.dtype!=np.int64 or selected.shape!=(48,)or ((selected<0)|(selected>=8)).any():raise ValueError("preplay selected public anchors required")
    native=read(plan["native_plan"])
    for i,(code,state)in enumerate(roots):
        specs=native["query_specs"][code];q=specs[state]if isinstance(specs,list)else specs[str(state)]
        if int(selected[i])!=native["candidate_order"].index(q["ref"]):raise ValueError("selected input differs from frozen preplay anchor")
        numeric=arrays["target_mask"][i,:,2:]
        if np.any(numeric[np.arange(8)!=selected[i]]):raise ValueError("unchosen future labels are ambiguous under this branch graph")
        if q["mode"]=="self-entry"and numeric.any():raise ValueError("self-entry lifecycle cannot duplicate primary effects")
    for y,m,names,binary in((arrays["source_targets"],arrays["source_mask"],manifest["source_head_names"],manifest["source_binary_heads"]),(arrays["targets"],arrays["target_mask"],manifest["target_names"],manifest["binary_heads"])):
        for name in binary:
            h=names.index(name)
            if not np.isin(y[...,h][m[...,h]>0],[0,1]).all():raise ValueError("known binary label differs")
    cells=partition(arrays,plan["split"])
    if {k:len(v)for k,v in cells.items()}!=dict(train=21,family_held=15,state_held=7,joint=5):raise ValueError("split cells differ")
    sparse=training_masks(arrays,cells["train"],manifest["target_names"],"sparse-typed")
    for key,value in sparse.items():
        if "sparse_"+key in arrays and not np.array_equal(arrays["sparse_"+key],value):raise ValueError("converter sparse masks differ from five-head-only intervention")
    return cells


def support_by_card(arrays,manifest,cells):
    import numpy as np
    result={}
    for part,indices in cells.items():
        result[part]={}
        for code in sorted(set(arrays["source_cards"][indices].astype(str))):
            rows=[i for i in indices if str(arrays["source_cards"][i])==code];heads={}
            for h,name in enumerate(manifest["target_names"]):
                y=arrays["targets"][rows,:,h];m=arrays["target_mask"][rows,:,h]>0;v=y[m]
                heads[name]=dict(known=int(m.sum()),observed_roots=int(m.any(-1).sum()),zero=int((v==0).sum()),positive=int((v>0).sum()),negative=int((v<0).sum()),values=np.unique(v).tolist())
            result[part][code]=heads
    return result


def support_admission(arrays,manifest,plan):
    """Pre-fit gate: training support and held observation masks, no predictions."""
    import numpy as np
    support=plan["behavioral_support"];cells=partition(arrays,plan["split"])
    f=family_metrics(np.zeros_like(arrays["targets"]),arrays,manifest,plan["scalers"],support,cells["family_held"])
    p=contrast_metrics(np.zeros_like(arrays["targets"]),arrays,manifest,plan["scalers"],support)
    checks=dict(all_four_mechanics_train_identifiable=all(v["eligible"]for v in support["mechanics"].values()),held_families_at_least_two=f["known_families"]>=2,held_program_groups_at_least_three=f["known_program_groups"]>=3,contrast_pairs_at_least_four=p["known_pairs"]>=4,contrast_families_at_least_two=p["known_families"]>=2)
    return dict(passed=all(checks.values()),checks=checks,training_support=support,held_known_families=f["known_families"],held_known_program_groups=f["known_program_groups"],contrast_known_pairs=p["known_pairs"],contrast_known_families=p["known_families"],rule="Support/masks only; no prediction-based selection or extra roots. Failure stops before any neural import/fit.")


def seal(prepared,path,dataset,manifest_path):
    import numpy as np
    if path.exists():raise FileExistsError("preserve sealed plan")
    plan=read(prepared);verify_pins(plan["pins"])
    if plan["source_sha256"]!=sha(__file__)or plan["config"]!=CONFIG:raise ValueError("prepared source/config differs")
    raw=read(manifest_path)
    if raw["artifact"]["sha256"]!=sha(dataset):raise ValueError("native dataset hash differs")
    manifest=joined_manifest(raw,plan)
    if manifest.get("fit_blockers")or manifest.get("planned_settlement_precheck_passed")is not True:raise ValueError("native errors/pending/unverified settlement blocks fitting")
    if manifest["plan"]!=read(plan["native_plan"]):raise ValueError("native manifest plan differs")
    with np.load(dataset,allow_pickle=False)as pack:arrays={k:pack[k].copy()for k in pack.files}
    cells=validate_data(arrays,manifest,plan);scalers=common_scalers(arrays,manifest,cells["train"]);x,c=scale_inputs(arrays,scalers)
    typed=exact_input_conflicts(arrays,manifest,plan["documents"],plan["codes"],x,c,train_codes=plan["train_codes"])
    if typed["conflict_count"]:raise ValueError("actual typed-input co-known label conflict: "+json.dumps(typed["conflicts"]))
    ids=exact_input_conflicts(arrays,manifest,plan["documents"],plan["codes"],x,c,"id-only",plan["train_codes"])
    wrong=wrong_evaluation_indices(plan)
    wrong_audit=exact_input_conflicts(arrays,manifest,plan["documents"],plan["codes"],x,c,"wrong-eval",plan["train_codes"],[plan["codes"][wrong[plan["codes"].index(str(code))]]for code in arrays["source_cards"]])
    plan.update(status="sealed-awaiting-root-GO",prepared_sha256=sha(prepared),dataset=str(dataset.resolve()),manifest=str(manifest_path.resolve()),scalers=scalers,behavioral_support=behavioral_support(arrays,manifest,scalers,plan["split"]),per_card_head_support=support_by_card(arrays,manifest,cells),input_audits=dict(typed=typed,id_only=ids,wrong_evaluation=wrong_audit),semantic_validated=False)
    plan["support_admission"]=support_admission(arrays,manifest,plan)
    if not plan["support_admission"]["passed"]:
        report=path.with_suffix(".admission-failure.json")
        if report.exists():raise FileExistsError("preserve prior admission failure")
        write(report,dict(status="collection-identifiability-failure-no-fit",prepared=pin(prepared),dataset=pin(dataset),manifest=pin(manifest_path),support_admission=plan["support_admission"],per_card_head_support=plan["per_card_head_support"]))
        raise ValueError("pre-fit native support failed; preserved "+str(report))
    plan["pins"] += [pin(dataset),pin(manifest_path)];write(path,plan);return plan


def wrong_evaluation_indices(plan):
    output=list(range(len(plan["codes"])))
    for group in(plan["train_codes"],plan["held_codes"]):
        for i,code in enumerate(group):output[plan["codes"].index(code)]=plan["codes"].index(group[(i+1)%len(group)])
    return output


def accounting():
    import importlib.util
    path=DEFAULT/"accounting.py"
    if sha(path)!=ACCOUNTING_SHA:raise ValueError("accounting implementation changed")
    spec=importlib.util.spec_from_file_location("effect_frozen_accounting",path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def preflight(plan_path,ledger):
    plan=read(plan_path);verify_pins(plan["pins"])
    if plan["source_sha256"]!=sha(__file__)or plan["config"]!=CONFIG:raise ValueError("source/config mismatch")
    A=accounting()
    with Path(ledger).open()as f:state=A.state(A.read_rows(f),ledger)
    return dict(status="read-only-preflight",source_sha256=sha(__file__),plan_sha256=sha(plan_path),plan_status=plan["status"],ledger_frozen=state["frozen"],pending=state["pending"],counts=CONFIG,parameters=plan["parameters"],no_execution=True)


def append_journal(path,event):
    with path.open("a")as f:f.write(json.dumps(event,sort_keys=True,allow_nan=False)+"\n");f.flush();os.fsync(f.fileno())


def journal_counts(path):
    rows=[json.loads(line)for line in path.read_text().splitlines()]if path.exists()else[]
    updates=[r for r in rows if r["event"]=="optimizer-update"];forwards=[r for r in rows if r["event"]=="forward-intent"]
    if [r["global_update"]for r in updates]!=list(range(1,len(updates)+1))or [r["global_forward"]for r in forwards]!=list(range(1,len(forwards)+1)):raise ValueError("durable journal sequence changed")
    return dict(optimizer_updates=len(updates),training_forwards=sum(r["kind"]=="train"for r in forwards),evaluation_forwards=sum(r["kind"]=="evaluate"for r in forwards),export_forwards=0)


class Guard:
    """Sample live own-process RSS; wall timer starts before numerical imports."""
    def __init__(self,seconds):
        import math
        if not math.isfinite(seconds)or seconds<=0:raise ValueError("positive finite active-wall guard required")
        self.seconds=seconds;self.peak=0;self.error=None;self.started=None
    def rss(self):
        import ctypes
        if sys.platform=="darwin":
            lib=ctypes.CDLL("/usr/lib/libproc.dylib",use_errno=True);buf=ctypes.create_string_buffer(96)
            lib.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int];lib.proc_pidinfo.restype=ctypes.c_int
            if lib.proc_pidinfo(os.getpid(),4,0,buf,96)!=96:raise RuntimeError("live RSS query failed")
            return int.from_bytes(buf.raw[8:16],sys.byteorder)
        return int(Path("/proc/self/statm").read_text().split()[1])*os.sysconf("SC_PAGE_SIZE")
    def __enter__(self):
        import signal,time,threading
        self.started=time.monotonic();self.stop=threading.Event();self.signal=signal;self.previous=signal.getsignal(signal.SIGALRM)
        def alarm(*_):raise RuntimeError(self.error or "active card wall limit")
        def sample():
            while not self.stop.wait(.01):
                try:
                    self.peak=max(self.peak,self.rss())
                    if self.peak>CONFIG["rss_bytes"]:self.error="1GiB sampled live RSS limit";os.kill(os.getpid(),signal.SIGALRM);return
                except BaseException as error:self.error=str(error);os.kill(os.getpid(),signal.SIGALRM);return
        self.peak=self.rss()
        if self.peak>CONFIG["rss_bytes"]:raise RuntimeError("initial live RSS exceeds1GiB")
        self.thread=threading.Thread(target=sample,daemon=True)
        try:
            signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,self.seconds);self.thread.start();return self
        except BaseException:
            signal.setitimer(signal.ITIMER_REAL,0);self.stop.set()
            if self.thread.is_alive():self.thread.join(.1)
            signal.signal(signal.SIGALRM,self.previous);raise
    def __exit__(self,*_):
        self.signal.setitimer(self.signal.ITIMER_REAL,0);self.stop.set();self.thread.join(.1);self.signal.signal(self.signal.SIGALRM,self.previous)
        self.peak=max(self.peak,self.rss())
        if self.peak>CONFIG["rss_bytes"]:self.error="1GiB sampled live RSS limit"
        if self.error:raise RuntimeError(self.error)
    def receipt(self):
        import time
        return dict(active_seconds=time.monotonic()-self.started if self.started else 0.,peak_live_rss_bytes=self.peak,rss_sampler="proc_pidinfo live resident/10ms"if sys.platform=="darwin"else"proc statm/10ms",cpu_threads=1,wall_limit=self.seconds,rss_limit=CONFIG["rss_bytes"],paid_jobs=0)


def saved_pr35_diagnostic(torch,np,arrays,manifest,forward):
    """Exactly one old-model batch, no adaptation; replay and new TRAIN overlap."""
    W=prior();old=read(ROOT/"whole-card/card-plan.json");contract=read(ROOT/"whole-card/fit-1/contract.json")
    with np.load(ROOT/"actual-corpus/actual-corpus.npz",allow_pickle=False)as p:oldarrays={k:p[k]for k in p.files}
    with np.load(ROOT/"whole-card/fit-1/correct-typed-step200-predictions.npz",allow_pickle=False)as p:oldpred={k:p[k]for k in p.files}
    anchors=[next(i for i,(code,state)in enumerate(zip(oldarrays["source_cards"],oldarrays["state_families"]))if str(code)==c and int(state)==s)for c,s in(("ASH_048",0),("JTL_217",3))]
    overlap=[i for i,c in enumerate(arrays["source_cards"].astype(str))if c in("ASH_048","JTL_217")]
    for key in("context_feature_names","candidate_feature_names","source_head_names","target_names"):
        if manifest[key]!=read(ROOT/"actual-corpus/actual-corpus.manifest.json")[key]:raise ValueError("old overlap schema incompatible")
    merged={k:np.concatenate([oldarrays[k][anchors],arrays[k][overlap]])for k in("context_features","candidate_features","source_cards","selected_candidate_indices")}
    bank,_=W.make_bank(old["documents"],old["vocabularies"],False);bank={k:torch.as_tensor(v)for k,v in bank.items()};model=W.make_model(torch,old["vocabularies"],18,34)
    with np.load(ROOT/"whole-card/fit-1/correct-typed-checkpoint.npz",allow_pickle=False)as p:
        state=model.state_dict()
        if set(p.files)!=set(state):raise ValueError("old checkpoint names differ")
        model.load_state_dict({k:torch.as_tensor(p[k].copy())for k in p.files},strict=True)
    sc=contract["scalers"];x,c=scale_inputs(merged,sc);q=torch.as_tensor([W.CODES.index(str(code))for code in merged["source_cards"]]);model.eval();forward("evaluate","saved-pr35",0)
    with torch.inference_mode():sp,bp,_=model(torch.as_tensor(x),torch.as_tensor(c),q,bank,"correct-typed",torch.as_tensor(merged["selected_candidate_indices"]));source,branch=W.decode(torch,sp,bp,sc)
    discrepancies=[float(abs(source[:2]-oldpred["source"][anchors]).max()),float(abs(branch[:2]-oldpred["branch"][anchors]).max())]
    if not all(np.isfinite(discrepancies))or max(discrepancies)>1e-5:raise ValueError("saved PR35 same-backend replay parity failed")
    return dict(scope="Descriptive two new TRAIN identities only; no new HELD support, no refit",old_source_sha256=PR35_SHA,replay_old_rows=anchors,replay_max_abs_error=max(discrepancies),new_rows=overlap,source_predictions=source[2:].tolist(),branch_predictions=branch[2:].tolist())


def execute(plan_path,out,ledger,progress):
    plan=read(plan_path);verify_pins(plan["pins"])
    if plan["status"]!="sealed-awaiting-root-GO"or plan["source_sha256"]!=sha(__file__)or plan["config"]!=CONFIG:raise ValueError("sealed exact source/config required")
    if out.exists()or progress.exists():raise FileExistsError("preserve prior attempt; no reset/retry")
    A=accounting();counts=dict(optimizer_updates=0,training_forwards=0,evaluation_forwards=0,export_forwards=0,backwards=0);guard=None
    with A.lease(ledger)as(stream,rows,current):
        if not current["frozen"]or current["config"]["arms"]!=list(ARMS):raise ValueError("root-frozen matched config required")
        frozen=current["config"];verify_pins(frozen["pins"])
        if not any(p["path"]==str(Path(__file__).resolve())and p["sha256"]==sha(__file__)for p in frozen["pins"]):raise ValueError("learner source missing from campaign pins")
        for key in("optimizer_updates","training_forwards","evaluation_forwards","export_forwards"):
            if frozen[key]!=CONFIG[key]:raise ValueError("campaign allocation mismatch")
        seconds=min(60-current["phase_seconds"]["card"],180-current["active_seconds"])
        attempt=current["attempts"]+1;reservation=dict(phase="card",active_seconds=seconds,native_applies=0,optimizer_updates=1000,training_forwards=1000,evaluation_forwards=11,export_forwards=0)
        out.mkdir(parents=True);progress.parent.mkdir(parents=True,exist_ok=True)
        A.append(stream,rows,ledger,"attempt-start",dict(attempt=attempt,reservation=reservation,metadata=dict(source=pin(__file__),plan=pin(plan_path),pins=plan["pins"],progress_path=str(progress.resolve()),out=str(out.resolve()),config_sha256=frozen["config_sha256"])))
        import time
        begun=time.monotonic();status="failed";error=None
        def forward(kind,arm,step):
            key="training_forwards"if kind=="train"else"evaluation_forwards";counts[key]+=1
            if counts[key]>CONFIG[key]:raise RuntimeError("fixed forward ceiling exceeded")
            append_journal(progress,dict(event="forward-intent",global_forward=counts["training_forwards"]+counts["evaluation_forwards"],kind=kind,arm=arm,step=step))
        try:
            guard=Guard(seconds)
            with guard:
                import numpy as np
                import torch
                torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
                with np.load(plan["dataset"],allow_pickle=False)as p:arrays={k:p[k].copy()for k in p.files}
                manifest=joined_manifest(read(plan["manifest"]),plan);cells=validate_data(arrays,manifest,plan);sc=plan["scalers"]
                full,_=make_bank(plan["documents"],plan["codes"],plan["train_codes"],plan["vocabularies"],False);restricted,_=make_bank(plan["documents"],plan["codes"],plan["train_codes"],plan["vocabularies"],True)
                full={k:torch.as_tensor(v)for k,v in full.items()};restricted={k:torch.as_tensor(v)for k,v in restricted.items()};x,c=map(torch.as_tensor,scale_inputs(arrays,sc));q=torch.as_tensor([plan["codes"].index(str(code))for code in arrays["source_cards"]]);selected=torch.as_tensor(arrays["selected_candidate_indices"])
                rng=np.random.default_rng(18);schedule=np.asarray([rng.choice(cells["train"],18,replace=True)for _ in range(200)],np.int64);wrong_rng=np.random.default_rng(19)
                wrong=np.asarray([[wrong_rng.choice([plan["codes"].index(code)for code in plan["train_codes"]if digest(plan["documents"][plan["codes"].index(code)])!=digest(plan["documents"][int(q[row])])])for row in batch]for batch in schedule],np.int64)
                wrong_eval=np.asarray(wrong_evaluation_indices(plan),np.int64)[q.numpy()];np.savez_compressed(out/"schedules.npz",batches=schedule,wrong_train=wrong,wrong_eval=wrong_eval)
                base=make_model(torch,plan["vocabularies"],len(plan["codes"]),len(plan["train_codes"]));initial={n:p.detach().clone()for n,p in base.state_dict().items()};results={};vectors={};final_metrics={}
                np.savez_compressed(out/"initial-checkpoint.npz",**{n:v.numpy()for n,v in initial.items()})
                for arm in ARMS:
                    model=make_model(torch,plan["vocabularies"],len(plan["codes"]),len(plan["train_codes"]));model.load_state_dict(initial,strict=True);configure_arm(model,arm)
                    if sum(p.numel()for p in model.parameters())!=plan["parameters"]["allocated"]or sum(p.numel()for p in model.parameters()if p.requires_grad)!=plan["parameters"]["trainable"][arm]:raise ValueError("allocated/trainable count mismatch")
                    optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=.003,weight_decay=.0001);masks=training_masks(arrays,cells["train"],manifest["target_names"],arm);labels={k:torch.as_tensor(masks[k]if k in masks else arrays[k])for k in("source_targets","source_mask","targets","target_mask")};evaluations={};gradients={}
                    for step in range(201):
                        if step in(0,200):
                            model.eval();forward("evaluate",arm,step)
                            with torch.inference_mode():sp,bp,v=model(x,c,torch.as_tensor(wrong_eval)if arm=="rich-wrong-typed"else q,full,arm,selected);source,branch=prior().decode(torch,sp,bp,sc)
                            evaluations[str(step)]=evaluate_metrics(source,branch,arrays,manifest,plan)
                            np.savez_compressed(out/f"{arm}-step{step}-predictions.npz",source=source,branch=branch,source_cards=arrays["source_cards"],state_families=arrays["state_families"],selected_candidate_indices=arrays["selected_candidate_indices"])
                            if step==200:vectors[arm]=v.detach().numpy().copy();final_metrics[arm]=evaluations[str(step)]
                        if step==200:break
                        model.train();batch=schedule[step];optimizer.zero_grad(set_to_none=True);forward("train",arm,step+1)
                        sp,bp,_=model(x[batch],c[batch],torch.as_tensor(wrong[step])if arm=="rich-wrong-typed"else q[batch],restricted,arm,selected[batch]);objective=fixed_loss(torch,sp,bp,{k:v[batch]for k,v in labels.items()},sc)
                        if not bool(torch.isfinite(objective)):raise ValueError("nonfinite objective")
                        objective.backward();counts["backwards"]+=1;norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                        if not bool(torch.isfinite(norm)):raise ValueError("nonfinite gradient")
                        if step==199:gradients={n:dict(rms=float(p.grad.square().mean().sqrt()),nonzero=int(torch.count_nonzero(p.grad)),elements=p.numel())for n,p in model.named_parameters()if p.grad is not None}
                        optimizer.step();counts["optimizer_updates"]+=1;append_journal(progress,dict(event="optimizer-update",global_update=counts["optimizer_updates"],arm=arm,arm_update=step+1,loss=float(objective.detach()),preclip_gradient_norm=float(norm)))
                    weights={n:p.detach().numpy().copy()for n,p in model.state_dict().items()};np.savez_compressed(out/f"{arm}-checkpoint.npz",**weights)
                    if arm in("rich-id-only","rich-untrained-typed")and any(not np.array_equal(weights[n],initial[n].numpy())for n in weights if any(n.startswith(p)for p in prior().ENCODER_PREFIXES)):raise ValueError("frozen encoder changed")
                    if arm=="rich-id-only"and np.any(vectors[arm][[plan["codes"].index(code)for code in plan["held_codes"]]]):raise ValueError("held ID UNK vector changed")
                    results[arm]=dict(evaluations=evaluations,checkpoint=pin(out/f"{arm}-checkpoint.npz"),last_step_postclip_gradients=gradients,parameters=plan["parameters"]["trainable"][arm])
                saved=saved_pr35_diagnostic(torch,np,arrays,manifest,forward);baselines=constant_baselines(arrays,manifest,plan);gate=behavioral_gate(final_metrics,baselines)
                np.savez_compressed(out/"card-vectors.npz",codes=np.asarray(plan["codes"]),**vectors)
                if any(not np.isfinite(v).all()for v in vectors.values()):raise ValueError("nonfinite captured vectors")
                verify_pins(plan["pins"]);verify_pins(frozen["pins"])
                durable=journal_counts(progress)
                if durable!={k:CONFIG[k]for k in durable}or counts["backwards"]!=1000:raise ValueError("fixed durable counters differ")
                write(out/"contract.json",dict(plan=pin(plan_path),source=pin(__file__),config=CONFIG,scalers=sc,vocabularies=plan["vocabularies"],documents_sha256=plan["document_sha256"],numeric_scale=plan["numeric_scale"],parameters=plan["parameters"]))
                write(out/"result.json",dict(status="completed",counts=counts,results=results,zero_neural_baselines=baselines,behavioral_gate=gate,held_behavior_gate_passed=gate["passed"],saved_PR35_diagnostic=saved,all_protected_inputs_unchanged=True,semantic_validated=False,qualification_scope="Only frozen selected-anchor held-template gate; no full-card semantics/deck synergy/play strength",plan=pin(plan_path),source=pin(__file__)))
            status="completed"
        except BaseException as caught:error=dict(type=type(caught).__name__,message=str(caught))
        elapsed=time.monotonic()-begun
        if elapsed>seconds:status="failed";error=dict(type="BudgetExceeded",message="total owned worker time exceeds reservation")
        try:durable=journal_counts(progress)
        except BaseException as caught:durable={k:counts[k]for k in("optimizer_updates","training_forwards","evaluation_forwards","export_forwards")};status="failed";error=dict(type=type(caught).__name__,message=str(caught),journal_unverified=True)
        receipt=dict(status=status,error=error,active_seconds=elapsed,counts=counts,durable_counts=durable,charged_optimizer_updates=1000,charged_training_forwards=1000,charged_evaluation_forwards=11,guard=guard.receipt()if guard else None,progress_sha256=sha(progress)if progress.exists()else None,result_sha256=sha(out/"result.json")if(out/"result.json").exists()else None,native_applies=0,paid_spend_usd=0.)
        write(out/"receipt.json",receipt)
        A.append(stream,rows,ledger,"attempt-finish",dict(attempt=attempt,status=status,active_seconds=elapsed,native_applies=0,native_journal_verified=True,observed_optimizer_updates=durable["optimizer_updates"],training_forwards=durable["training_forwards"],evaluation_forwards=durable["evaluation_forwards"],export_forwards=0,receipt=pin(out/"receipt.json")))
        if status!="completed":raise RuntimeError("failed attempt preserved: "+str(error))
        return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group(required=True)
    for name in("prepare","seal","preflight","execute"):m.add_argument("--"+name,action="store_true")
    p.add_argument("--prepared",type=Path,default=DEFAULT/"learner-prepared.json");p.add_argument("--plan",type=Path,default=DEFAULT/"learner-plan.json");p.add_argument("--native-plan",type=Path,default=ROOT/"native-effect-v2/native-plan.json");p.add_argument("--cohort-contract",type=Path,default=CONTRACT)
    p.add_argument("--dataset",type=Path,default=ROOT/"native-effect-v2/native-effect-v2.npz");p.add_argument("--manifest",type=Path,default=ROOT/"native-effect-v2/native-effect-v2.manifest.json");p.add_argument("--ledger",type=Path,default=DEFAULT/"campaign-ledger.jsonl");p.add_argument("--progress",type=Path,default=DEFAULT/"fit-progress.jsonl");p.add_argument("--out",type=Path,default=DEFAULT/"fit-1")
    a=p.parse_args()
    if a.prepare:prepare(a.prepared,a.native_plan,a.cohort_contract);print(json.dumps(pin(a.prepared)))
    elif a.seal:seal(a.prepared,a.plan,a.dataset,a.manifest);print(json.dumps(pin(a.plan)))
    elif a.preflight:print(json.dumps(preflight(a.plan,a.ledger),allow_nan=False))
    else:print(json.dumps(execute(a.plan,a.out,a.ledger,a.progress),allow_nan=False))
if __name__=="__main__":main()
