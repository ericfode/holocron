"""Eight actual-deck cards: reviewed whole-card frontend and bounded native fit.

Preparation and sealing use only public JSON/NumPy. Torch is imported exclusively
inside the sampled execution guard. Existing action models remain immutable.
"""
import os
for _name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_name]="1"
import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import threading
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
ROOT=REPO.parent/"experiments"
DEFAULT=ROOT/"whole-card"
CATALOG=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source/compiler/generated/cards.json")
RUNTIME=CATALOG.with_name("runtime-admission.json")
CODES=("ASH_048","JTL_095","SEC_163","LOF_077","JTL_078","JTL_158","LOF_155","JTL_217")
TRAIN=CODES[:6]
HELD=CODES[6:]
ARMS=("correct-typed","id-only","untrained-typed","wrong-typed")
MAX_TOKENS,MAX_PATH,HIDDEN=512,32,16
PRINTED=("cost","hp","power","unique","upgradePower","upgradeHp","aspects","traits","arena","keywords","types")
EXTRA=("stateWatchers","privatePrograms","historyHelpers","inheritedSource","deploymentOverride","setupValidationOverrides","classMethods","privateClassConstants")
ROW_FIELDS={"setCode","sourcePath","sourceHash","abilities","id","internalName","status","card","dataHash","keywordValues","requiredCapabilities","baseClass","className","attachCondition",*EXTRA}
PRINTED_FIELDS={*PRINTED,"title","subtitle","text","deployBox","epicAction","rules","id","setId","setCodes","internalName","pilotText","backSideTitle","backSideTraits","backSideSubtitle","backSideAspects"}
CONFIG=dict(seed=17,arms=list(ARMS),updates_per_arm=200,total_updates=800,batch_size=18,learning_rate=.003,weight_decay=.0001,
            optimizer="AdamW",clip_l2=1.,training_forwards=800,backwards=800,evaluation_forwards=8,export_forwards=0,
            loss="root-mean BCE/smoothL1, macro over training-varying heads; constant observed heads auxiliary0.1",seconds=60,threads=1,rss_bytes=1073741824,paid_jobs=0)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def card_document(row):
    """All pilot runtime semantic fields; identity/display/provenance stay outside.

    Empty programs are NOT vanilla: keywordValues and attachment conditions are
    explicit. Unsupported additional machine semantics reject, never disappear.
    This reviewed main-card contract does not accept leader/deployed roles.
    """
    card=row["card"]
    if set(row)-ROW_FIELDS or set(card)-PRINTED_FIELDS:raise ValueError("unreviewed catalog semantic field")
    if not set(card["types"])<= {"unit","event","upgrade"} or not card["types"]:
        raise ValueError("main-card unit/event/upgrade role required")
    for key in EXTRA:
        if row.get(key):raise ValueError("unreviewed whole-card semantic field "+key)
    for key in("pilotText","backSideTitle","backSideTraits","backSideSubtitle","backSideAspects","deployBox","epicAction"):
        if card.get(key):raise ValueError("unsupported pilot/leader/backside semantics "+key)
    abilities=copy.deepcopy(row["abilities"])
    if set(abilities)!={"leader","unit","card"} or any(not isinstance(v,list)for v in abilities.values()):raise ValueError("all ordered ability sides required")
    if abilities["leader"] or abilities["unit"]:raise ValueError("leader/deployed unit roles require separate contract")
    for ability in abilities["card"]:
        if not isinstance(ability,dict)or not isinstance(ability.get("trigger"),str):raise ValueError("typed trigger required")
        ability.pop("title",None)
    return dict(role="main",printed={key:copy.deepcopy(card.get(key))for key in PRINTED},keywordValues=copy.deepcopy(row["keywordValues"]),
                attachCondition=copy.deepcopy(row.get("attachCondition")),abilities=abilities)


def tokens(document):
    """Categorical typed paths preserve every key, ordered index and literal."""
    import math
    output=[]
    def visit(value,path):
        if len(path)>MAX_PATH or len(output)>=MAX_TOKENS:raise ValueError("whole-card cap exceeded; no truncation")
        def add(kind,value):output.append((path,kind,value))
        if isinstance(value,dict):
            if set(value)&{"title","sourcePath","sourceHash","setCode","internalName","id","label","method"}:raise ValueError("unreviewed identity/display/binding field")
            add("node","object")
            for key in sorted(value):visit(value[key],path+(key,))
        elif isinstance(value,list):
            add("length",len(value))
            for i,item in enumerate(value):visit(item,path+(i,))
        elif type(value)is bool:add("boolean",value)
        elif type(value)in(int,float):
            if not math.isfinite(value)or abs(value)>65535:raise ValueError("invalid numeric literal")
            add("number",float(value))
        elif isinstance(value,str):
            # Genuine rule literal strings/references remain categorical atoms;
            # identity/provenance cannot enter through whitelisted printed data.
            if len(value)>96:raise ValueError("unreviewed long string atom")
            add("enum",value)
        elif value is None:add("null","null")
        else:raise ValueError("untyped value")
    visit(document,())
    if len(output)>MAX_TOKENS:raise ValueError("whole-card token cap exceeded")
    return tuple(output)


def symbols_for(documents):
    all_tokens=[t for document in documents for t in tokens(document)]
    return dict(path=["PAD",*sorted({("index:"if type(k)is int else"key:")+str(k)for path,_,_ in all_tokens for k in path})],
                type=["PAD","node","length","number","boolean","enum","null"],
                value=["PAD","NUMBER",*sorted({kind+":"+str(value)for _,kind,value in all_tokens if kind not in("number","length")})])


def make_bank(documents,symbols,training=True):
    import numpy as np
    lookup={key:{v:i for i,v in enumerate(values)}for key,values in symbols.items()}
    numbers=[value for code,doc in zip(CODES,documents)if code in TRAIN for _,kind,value in tokens(doc)if kind in("number","length")]
    scale=max(1.,float(np.std(numbers)))
    bank=dict(path_ids=np.zeros((8,MAX_TOKENS,MAX_PATH),np.int64),path_lengths=np.zeros((8,MAX_TOKENS),np.int64),
              type_ids=np.zeros((8,MAX_TOKENS),np.int64),value_ids=np.zeros((8,MAX_TOKENS),np.int64),numeric=np.zeros((8,MAX_TOKENS,2),np.float32),
              token_mask=np.zeros((8,MAX_TOKENS),np.float32),slot_mask=np.ones(8,np.float32),identity_indices=np.asarray([i+1 if i<6 else 0 for i in range(8)],np.int64))
    for slot,doc in enumerate(documents):
        for i,(path,kind,value)in enumerate(tokens(doc)):
            try:
                edges=[lookup["path"][("index:"if type(k)is int else"key:")+str(k)]for k in path]
                bank["type_ids"][slot,i]=lookup["type"][kind]
                bank["value_ids"][slot,i]=lookup["value"]["NUMBER"if kind in("number","length")else kind+":"+str(value)]
            except KeyError as error:raise ValueError("unreviewed categorical symbol; no UNKNOWN remap")from error
            bank["path_ids"][slot,i,:len(path)]=edges;bank["path_lengths"][slot,i]=len(path);bank["token_mask"][slot,i]=1
            if kind in("number","length"):bank["numeric"][slot,i]=(value/scale,np.sign(value)*np.log1p(abs(value)))
    if training:
        for value in bank.values():value[6:]=0
    return bank,scale


def bank_signatures(bank):
    """Identity-free exact tensor collision evidence, not embedding injectivity."""
    result=[]
    for slot in range(8):
        h=hashlib.sha256()
        for key in sorted(bank):
            if key=="identity_indices":continue
            value=bank[key][slot];h.update(key.encode()+str(value.dtype).encode()+str(value.shape).encode()+value.tobytes())
        result.append(h.hexdigest())
    return result


def prepare(path,native_plan):
    if path.exists():raise FileExistsError("preserve prepared plan")
    rows={r["setCode"]:r for r in read(CATALOG)["cards"]};admitted={r["setCode"]for r in read(RUNTIME)["runtimeAdmittedCards"]}
    if not set(CODES)<=admitted:raise ValueError("pilot whole-card native admission differs")
    docs=[card_document(rows[code])for code in CODES];symbols=symbols_for(docs)
    bank,numeric_scale=make_bank(docs,symbols,False)
    signatures=[digest(doc)for doc in docs]
    if len(set(signatures))!=8:raise ValueError("whole-card semantic duplicate requires grouped split")
    tensor_signatures=bank_signatures(bank)
    if len(set(tensor_signatures))!=8:raise ValueError("distinct documents collide in semantic tensors")
    native=read(native_plan)
    if tuple(c["code"]for c in native["cards"])!=CODES or tuple(native["split"]["train_codes"])!=TRAIN or tuple(native["split"]["heldout_codes"])!=HELD:raise ValueError("native card split differs")
    if any(card_document(c["raw_card"])!=docs[i]for i,c in enumerate(native["cards"])):raise ValueError("native complete card document differs")
    abi={key:native[key]for key in("candidate_order","context_feature_names","candidate_feature_names","source_head_names","source_binary_heads","target_names","binary_heads")}
    sys.path.insert(0,str(HERE));import actual_corpus_native_plan as N
    intent={code+":"+str(context["id"]):native["candidate_order"].index(N.selected_ref(code,context))for code in CODES for context in native["contexts"]}
    allocated=9312+16*(len(symbols["path"])+len(symbols["value"]));encoder=2560+16*(len(symbols["path"])+len(symbols["value"]))
    parameters=dict(allocated=allocated,trainable={"correct-typed":allocated-112,"wrong-typed":allocated-112,"id-only":allocated-encoder,"untrained-typed":allocated-encoder-112})
    plan=dict(schema="whole-card-native-pilot/1",status="prepared-no-execution",source_sha256=sha(__file__),config=CONFIG,codes=list(CODES),train_codes=list(TRAIN),held_codes=list(HELD),abi=abi,parameters=parameters,
              documents=docs,document_sha256=signatures,semantic_tensor_sha256=tensor_signatures,vocabularies=symbols,numeric_scale=numeric_scale,native_plan=str(native_plan),selected_public_intent=intent,
              pins=[dict(path=str(p),sha256=sha(p))for p in(Path(__file__),CATALOG,RUNTIME,native_plan,HERE/"actual_corpus_native_plan.py",HERE/"grounded_contrast_data.py")],
              scopes=dict(runtime_admitted_actual_corpus=115,runtime_admitted_copies=635,fixture_planned=8,training_cards=6,held_cards=2,actual_copies_in_pilot=65,total_corpus_copies=1432,
                          whole_card_frontend=True,whole_card_behavior_verified=False,all115_encoded=False),
              split=dict(train_states=[0,1,2],held_states=[3],expected_cells=dict(train=18,card_held=6,state_held=6,joint=2),
                         held_cases={"LOF_155":"seen-defeat/upgrade family; unseen nonunique restriction","JTL_217":"single wholly held exhaust-primitive OOD card; no family-population claim"}),
              controls="Allocated graph/init/schedule equal; ID table trained6/heldUNK0; untrained typed encoder frozen; wrong typed independently permuted to another training semantic group each update.",
              intent_contract="All9 source predictions condition on the predeclared intended candidate public features. Availability is generally a source-only fact; this shared head must learn invariance. No offeredness/after labels enter inputs.",
              vocabulary_scope="Reviewed categorical schema from all8 public definitions before labels; held-only rows allocated but receive no held-token training gradient because every held bank field is zero in training. This is not a train-only vocabulary.",
              qualification="Eight actual cards/65copies; full runtime machine semantics represented for these8, only sampled native consequences qualify. Printed reconstruction does not establish semantic quality.")
    path.parent.mkdir(parents=True,exist_ok=True);write(path,plan);return plan


def make_model(torch,symbols,context_width,candidate_width,source_width=9,branch_width=7):
    nn=torch.nn
    class WholeCard(nn.Module):
        def __init__(self):
            super().__init__()
            self.edge=nn.Embedding(len(symbols["path"]),16,padding_idx=0);self.depth=nn.Parameter(torch.randn(MAX_PATH,16)/4)
            self.kind=nn.Embedding(len(symbols["type"]),16,padding_idx=0);self.value=nn.Embedding(len(symbols["value"]),16,padding_idx=0);self.numeric=nn.Linear(2,16)
            self.leaf=nn.Sequential(nn.Linear(32,32),nn.Tanh(),nn.Linear(32,16),nn.Tanh());self.card_projection=nn.Sequential(nn.Linear(16,16),nn.LayerNorm(16))
            self.identity=nn.Embedding(7,16,padding_idx=0)
            self.context=nn.Sequential(nn.Linear(context_width,16),nn.Tanh(),nn.LayerNorm(16));self.candidate=nn.Sequential(nn.Linear(candidate_width,16),nn.Tanh(),nn.LayerNorm(16))
            self.source_head=nn.Sequential(nn.Linear(80,32),nn.Tanh(),nn.Linear(32,source_width));self.branch_head=nn.Sequential(nn.Linear(80,32),nn.Tanh(),nn.Linear(32,branch_width))
        def card_bank(self,bank):
            slot,pos=torch.nonzero(bank["token_mask"]*bank["slot_mask"][:,None],as_tuple=True)
            ids=bank["path_ids"][slot,pos];depthmask=torch.arange(MAX_PATH,device=ids.device)<bank["path_lengths"][slot,pos,None]
            path=(self.edge(ids)*self.depth*depthmask[...,None]).sum(1)
            value=self.kind(bank["type_ids"][slot,pos])+self.value(bank["value_ids"][slot,pos])+self.numeric(bank["numeric"][slot,pos])
            leaves=self.leaf(torch.cat((path,value),-1));pool=torch.zeros((8,16),device=leaves.device,dtype=leaves.dtype).index_add(0,slot,leaves)
            mean=pool/bank["token_mask"].sum(1,keepdim=True).clamp(min=1)
            return self.card_projection(mean)*bank["slot_mask"][:,None]
        def forward(self,x,c,q,bank,arm,selected_candidate_indices):
            semantic=self.card_bank(bank)
            vectors=torch.nn.functional.layer_norm(self.identity(bank["identity_indices"]),(16,))if arm=="id-only"else semantic
            p=vectors[q];s=self.context(x);candidate=self.candidate(c)
            intended=candidate[torch.arange(len(c),device=c.device),selected_candidate_indices]
            source=self.source_head(torch.cat((p,s,intended,p*s,p*intended),-1));pp=p[:,None,:].expand_as(candidate);ss=s[:,None,:].expand_as(candidate)
            branch=self.branch_head(torch.cat((pp,ss,candidate,pp*ss,pp*candidate),-1))
            return source,branch,vectors
    return WholeCard()


ENCODER_PREFIXES=("edge.","depth","kind.","value.","numeric.","leaf.","card_projection.")
def configure_arm(model,arm):
    if arm not in ARMS:raise ValueError("unreviewed arm")
    for name,p in model.named_parameters():
        encoder=any(name.startswith(prefix)for prefix in ENCODER_PREFIXES)
        p.requires_grad=(not encoder if arm in("untrained-typed","id-only")else True)and(not name.startswith("identity.")or arm=="id-only")


def validate_data(arrays,manifest):
    import numpy as np
    shapes=dict(context_features=(32,18),candidate_features=(32,8,34),source_targets=(32,9),source_mask=(32,9),targets=(32,8,7),target_mask=(32,8,7))
    for key,shape in shapes.items():
        a=arrays[key]
        if a.shape!=shape or a.dtype!=np.float32 or not np.isfinite(a).all():raise ValueError("native numeric ABI differs: "+key)
        if key.endswith("mask")and not np.isin(a,[0,1]).all():raise ValueError("unknown/mask must be explicit0/1")
    if len(manifest["context_feature_names"])!=18 or len(manifest["candidate_feature_names"])!=34 or len(manifest["source_head_names"])!=9 or len(manifest["target_names"])!=7:raise ValueError("named ABI differs")
    if arrays["source_cards"].shape!=(32,)or arrays["state_families"].shape!=(32,)or {(str(c),int(s))for c,s in zip(arrays["source_cards"],arrays["state_families"])}!={(c,s)for c in CODES for s in range(4)}:raise ValueError("fixed32 roots required")
    intent=arrays["selected_candidate_indices"]
    if intent.shape!=(32,)or intent.dtype!=np.int64 or ((intent<0)|(intent>=8)).any():raise ValueError("public before-play selected candidate indices required")
    for target,mask,names,binary in ((arrays["source_targets"],arrays["source_mask"],manifest["source_head_names"],manifest["source_binary_heads"]),(arrays["targets"],arrays["target_mask"],manifest["target_names"],manifest["binary_heads"])):
        for name in binary:
            j=names.index(name)
            if not np.isin(target[...,j][mask[...,j]>0],[0,1]).all():raise ValueError("nonbinary known native label")


def partition(arrays):
    import numpy as np
    train=np.isin(arrays["source_cards"],TRAIN);seen=arrays["state_families"]<3
    return dict(train=np.flatnonzero(train&seen),card_held=np.flatnonzero(~train&seen),state_held=np.flatnonzero(train&~seen),joint=np.flatnonzero(~train&~seen))


def scalers(arrays,manifest):
    import numpy as np
    idx=partition(arrays)["train"];result={}
    for key in("context_features","candidate_features"):
        value=arrays[key][idx];axes=tuple(range(value.ndim-1))
        # Center/scale every named public coordinate, including boolean flags;
        # this invertible train-only transform never imputes hidden information.
        result[key]=dict(center=value.mean(axes).tolist(),scale=np.maximum(1,value.std(axes)).tolist())
    for key,mask_key,names_key,binary_key in(("source_targets","source_mask","source_head_names","source_binary_heads"),("targets","target_mask","target_names","binary_heads")):
        rows=[]
        for j,name in enumerate(manifest[names_key]):
            v=arrays[key][idx,...,j];mask=arrays[mask_key][idx,...,j]>0;known=v[mask];binary=name in manifest[binary_key]
            rows.append(dict(name=name,binary=binary,center=0. if binary or not len(known)else float(known.mean()),scale=1. if binary or not len(known)else max(1.,float(known.std())),
                             known=int(mask.sum()),varying=bool(len(np.unique(known))>1),training_values=np.unique(known).tolist()))
        result[key]=rows
    if not any(r["varying"]for key in("source_targets","targets")for r in result[key]):raise ValueError("no train-varying native objective")
    return result


def native_support(arrays,manifest):
    """Endpoint support from actual paid/settled witnesses, never root presence."""
    import numpy as np
    sys.path.insert(0,str(HERE))
    import grounded_contrast_data as G
    records=manifest["records"]
    if len(records)!=32:raise ValueError("all32 raw native witnesses required")
    result={code:dict(declared_roots=4,availability_roots=0,committed_roots=0,settled_paid_roots=0,known_source_coordinates=0,known_target_coordinates=0,completions={})for code in CODES}
    committed=manifest["source_head_names"].index("play_committed");cost=manifest["source_head_names"].index("cost_resource");available=manifest["source_head_names"].index("play_available")
    for i,record in enumerate(records):
        record=record.get("raw_native_case",record)
        code=str(arrays["source_cards"][i]);state=int(arrays["state_families"][i])
        if record["card"]!=code or record["state_family"]!=state:raise ValueError("native witness/root order mismatch")
        counts=result[code];counts["availability_roots"]+=int(arrays["source_mask"][i,available]>0)
        paid=bool(arrays["source_mask"][i,committed]and arrays["source_targets"][i,committed]==1 and arrays["source_mask"][i,cost]and arrays["source_targets"][i,cost]>0)
        counts["committed_roots"]+=int(paid)
        final=record.get("final")
        settled=bool(final is not None and G.settled_capture(final))
        if paid and (not record.get("steps")or record.get("playAction")not in record["before"]["offeredActions"]):raise ValueError("paid entry lacks actual offered play/step witness")
        counts["settled_paid_roots"]+=int(paid and settled and not record.get("engineError"))
        counts["known_source_coordinates"]+=int(arrays["source_mask"][i].sum());counts["known_target_coordinates"]+=int(arrays["target_mask"][i].sum())
        completion=record["completion"];counts["completions"][completion]=counts["completions"].get(completion,0)+1
    for counts in result.values():counts["native_fixture_observed"]=counts["settled_paid_roots"]>0
    return result


def seal(prepared,path,dataset,manifest_path):
    import numpy as np
    if path.exists():raise FileExistsError("preserve sealed plan")
    plan=read(prepared)
    for pin in plan["pins"]:
        if sha(pin["path"])!=pin["sha256"]:raise ValueError("prepared source/native plan changed")
    manifest=read(manifest_path)
    if sha(dataset)!=manifest["artifact"]["sha256"]:raise ValueError("native artifact hash mismatch")
    with np.load(dataset,allow_pickle=False)as pack:arrays={k:pack[k].copy()for k in pack.files}
    validate_data(arrays,manifest);cells=partition(arrays)
    for key,expected in plan["abi"].items():
        if manifest[key]!=expected:raise ValueError("ordered native ABI differs: "+key)
    if arrays["selected_candidate_indices"].tolist()!=[plan["selected_public_intent"][str(code)+":"+str(int(state))]for code,state in zip(arrays["source_cards"],arrays["state_families"])]:raise ValueError("selected index differs from frozen public intent")
    if {k:len(v)for k,v in cells.items()}!=plan["split"]["expected_cells"]:raise ValueError("split matrix differs")
    plan.update(status="sealed-awaiting-root-GO",prepared_sha256=sha(prepared),dataset=str(dataset),manifest=str(manifest_path),scalers=scalers(arrays,manifest))
    plan["native_support"]=native_support(arrays,manifest)
    plan["pins"] += [dict(path=str(p),sha256=sha(p))for p in(dataset,manifest_path)]
    write(path,plan);return plan


def loss(torch,source,branch,labels,scaling):
    varying=[];constant=[]
    for prediction,key,maskkey in((source,"source_targets","source_mask"),(branch,"targets","target_mask")):
        for j,spec in enumerate(scaling[key]):
            target=labels[key][...,j];mask=labels[maskkey][...,j]
            if not spec["known"]or not bool(mask.any()):continue
            element=torch.nn.functional.binary_cross_entropy_with_logits(prediction[...,j],target,reduction="none")if spec["binary"]else torch.nn.functional.smooth_l1_loss(prediction[...,j],(target-spec["center"])/spec["scale"],reduction="none")
            if mask.ndim>1:
                support=mask.sum(-1);values=(element*mask).sum(-1)/support.clamp(min=1);values=values[support>0]
            else:values=element[mask>0]
            (varying if spec["varying"]else constant).append(values.mean())
    zero=source.sum()*0
    return (torch.stack(varying).mean()if varying else zero)+(.1*torch.stack(constant).mean()if constant else zero)


def decode(torch,source,branch,scaling):
    import numpy as np
    result=[]
    for value,key in((source,"source_targets"),(branch,"targets")):
        output=value.detach().numpy().copy()
        for j,spec in enumerate(scaling[key]):output[...,j]=torch.sigmoid(value[...,j]).detach().numpy()if spec["binary"]else output[...,j]*spec["scale"]+spec["center"]
        if not np.isfinite(output).all():raise ValueError("nonfinite decoded predictions")
        result.append(output)
    return result


def metrics(source,branch,arrays,manifest,scaling):
    import numpy as np
    cells=partition(arrays)
    cells.update({code:np.flatnonzero(arrays["source_cards"]==code)for code in HELD})
    result={}
    for cell,idx in cells.items():
        heads={}
        for prediction,key,maskkey in((source,"source_targets","source_mask"),(branch,"targets","target_mask")):
            for j,spec in enumerate(scaling[key]):
                target=arrays[key][idx,...,j];mask=arrays[maskkey][idx,...,j];pred=prediction[idx,...,j]
                support=mask if mask.ndim==1 else mask.sum(-1);valid=support>0
                def rootmean(v):return v if mask.ndim==1 else (v*mask).sum(-1)/np.maximum(support,1)
                observed=target[mask>0];error=rootmean(abs(pred-target));bias=rootmean(pred-target);accuracy=rootmean(((pred>=.5)==target).astype(float))
                positives=(target==1)&(mask>0);negatives=(target==0)&(mask>0);npositive=int(positives.sum());nnegative=int(negatives.sum())
                sensitivity=float(((pred>=.5)&positives).sum()/npositive)if spec["binary"]and npositive else None
                specificity=float(((pred<.5)&negatives).sum()/nnegative)if spec["binary"]and nnegative else None
                heads[spec["name"]]=dict(observed_roots=int(valid.sum()),known_coordinates=int(mask.sum()),mae=float(error[valid].mean())if valid.any()else None,
                    signed_residual=float(bias[valid].mean())if valid.any()else None,binary_accuracy=float(accuracy[valid].mean())if valid.any()and spec["binary"]else None,
                    native_values=np.unique(observed).tolist(),zero_coordinates=int((observed==0).sum()),nonzero_coordinates=int((observed!=0).sum()),train_varying=spec["varying"],train_scale=spec["scale"],
                    positive_known_coordinates=npositive if spec["binary"]else None,negative_known_coordinates=nnegative if spec["binary"]else None,
                    sensitivity=sensitivity,specificity=specificity,balanced_accuracy=(sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,
                    class_metric_scope="Known coordinates; root-mean MAE and overall accuracy reported separately")
        primary=[h["mae"]/h["train_scale"]for h in heads.values()if h["mae"]is not None and h["train_varying"]]
        result[cell]=dict(roots=len(idx),heads=heads,train_varying_macro=float(np.mean(primary))if primary else None)
    return result


def constant_baselines(arrays,manifest,scaling):
    """Zero neural work: literal zero heads and TRAIN18 known-coordinate means."""
    import numpy as np
    train=partition(arrays)["train"];means=[];counts=[]
    for key,maskkey in(("source_targets","source_mask"),("targets","target_mask")):
        values=[];support=[]
        for j in range(arrays[key].shape[-1]):
            known=arrays[key][train,...,j][arrays[maskkey][train,...,j]>0];values.append(float(known.mean())if len(known)else 0.);support.append(int(len(known)))
        means.append(np.broadcast_to(np.asarray(values,np.float32),arrays[key].shape).copy());counts.append(support)
    zero=[np.zeros_like(arrays[key])for key in("source_targets","targets")]
    return dict(zero_heads=dict(interpretation="Literal all-zero decoded heads, not a full no-change physical state",metrics=metrics(*zero,arrays,manifest,scaling)),
                train_constant=dict(interpretation="Training-known coordinate mean/positive rate only; fallback0 for entirely unknown heads",source_values=means[0][0].tolist(),target_values=means[1][0,0].tolist(),source_training_support=counts[0],target_training_support=counts[1],metrics=metrics(*means,arrays,manifest,scaling)))


class Guard:
    def __enter__(self):
        self.start=time.monotonic();self.cpu=resource.getrusage(resource.RUSAGE_SELF);self.stop=threading.Event();self.samples=0
        def halt(sig,frame):raise RuntimeError("card60second/1GiB limit")
        for sig in(signal.SIGALRM,signal.SIGXCPU,signal.SIGUSR1):signal.signal(sig,halt)
        signal.setitimer(signal.ITIMER_REAL,60);resource.setrlimit(resource.RLIMIT_CPU,(59,60))
        def monitor():
            while not self.stop.wait(.05):
                self.samples+=1
                if self.rss()>1073741824:os.kill(os.getpid(),signal.SIGUSR1);break
        self.thread=threading.Thread(target=monitor,daemon=True);self.thread.start();return self
    def rss(self):return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=="darwin"else 1024))
    def receipt(self):
        c=resource.getrusage(resource.RUSAGE_SELF)
        return dict(wall_seconds=time.monotonic()-self.start,cpu_seconds=c.ru_utime+c.ru_stime-self.cpu.ru_utime-self.cpu.ru_stime,peak_rss_bytes=self.rss(),samples=self.samples,threads=1)
    def __exit__(self,*args):signal.setitimer(signal.ITIMER_REAL,0);self.stop.set();self.thread.join(timeout=.2)


def append(path,event):
    with path.open("a")as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(event,allow_nan=False)+"\n");f.flush();os.fsync(f.fileno());fcntl.flock(f,fcntl.LOCK_UN)


def reserve(ledger,plan_path,out):
    """Read all campaign attempts while locked, then reserve this fixed phase."""
    with ledger.open("a+")as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);records=[json.loads(line)for line in f if line.strip()]
        if any(row.get("phase")=="card"for row in records):raise ValueError("card reservation already exists; no implicit retry/reset")
        started={r["stage_id"]for r in records if r.get("event")=="stage-start"}
        finished={r["stage_id"]for r in records if r.get("event")=="stage-finish"}
        if started!=finished:raise ValueError("pending/malformed campaign stage must be reconciled")
        terminal=[r for r in records if r.get("event")=="stage-finish"]
        elapsed=sum(float(r["elapsed_seconds"])for r in terminal)
        if elapsed+60>240:raise ValueError("campaign total240s reservation unavailable")
        event=dict(event="stage-start",phase="card",stage="fit",stage_id="card-"+out.name,reserved_applies=0,reserved_updates=800,reserved_neural_forwards=808,
                   elapsed_seconds=0,optimizer_updates=0,native_applies=0,neural_forwards=0,source_sha256=sha(__file__),plan_sha256=sha(plan_path))
        f.seek(0,2);f.write(json.dumps(event)+"\n");f.flush();os.fsync(f.fileno());fcntl.flock(f,fcntl.LOCK_UN)
    return event["stage_id"]


def execute(plan_path,out,ledger,progress):
    """One campaign attempt only; failed reservations cannot be silently reset."""
    plan=read(plan_path)
    if plan["status"]!="sealed-awaiting-root-GO"or plan["source_sha256"]!=sha(__file__)or plan["config"]!=CONFIG:raise ValueError("frozen sealed source/config required")
    if progress.exists():raise ValueError("existing durable card progress requires coordinator review; no retry/reset")
    out.mkdir(parents=True,exist_ok=False);ledger.parent.mkdir(parents=True,exist_ok=True)
    lease=Path(str(ledger)+".worker.lock").open("a")
    try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lease.close();raise ValueError("another campaign CPU worker holds the lease")
    counts=dict(training_forwards=0,backwards=0,optimizer_updates=0,evaluation_forwards=0,export_forwards=0,native_calls=0,paid_jobs=0)
    try:stage_id=reserve(ledger,plan_path,out)
    except BaseException:fcntl.flock(lease,fcntl.LOCK_UN);lease.close();raise
    guard=Guard()
    try:
        with guard:
            for pin in plan["pins"]:
                if sha(pin["path"])!=pin["sha256"]:raise ValueError("protected source/data changed")
            import numpy as np
            import torch
            torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(17)
            with np.load(plan["dataset"],allow_pickle=False)as pack:arrays={k:pack[k].copy()for k in pack.files}
            manifest=read(plan["manifest"]);validate_data(arrays,manifest)
            full,_=make_bank(plan["documents"],plan["vocabularies"],False);restricted,_=make_bank(plan["documents"],plan["vocabularies"],True)
            full={k:torch.as_tensor(v)for k,v in full.items()};restricted={k:torch.as_tensor(v)for k,v in restricted.items()}
            sc=plan["scalers"]
            x=torch.as_tensor((arrays["context_features"]-np.asarray(sc["context_features"]["center"],np.float32))/np.asarray(sc["context_features"]["scale"],np.float32))
            c=torch.as_tensor((arrays["candidate_features"]-np.asarray(sc["candidate_features"]["center"],np.float32))/np.asarray(sc["candidate_features"]["scale"],np.float32))
            q=torch.as_tensor([CODES.index(str(code))for code in arrays["source_cards"]]);selected=torch.as_tensor(arrays["selected_candidate_indices"]);labels={k:torch.as_tensor(arrays[k])for k in("source_targets","source_mask","targets","target_mask")}
            train=partition(arrays)["train"];rng=np.random.default_rng(18);schedule=np.asarray([rng.choice(train,len(train),replace=True)for _ in range(200)],np.int64)
            wrong_rng=np.random.default_rng(19);wrong=np.asarray([[wrong_rng.choice([i for i in range(6)if i!=int(q[row])])for row in batch]for batch in schedule],np.int64)
            wrong_eval=q.numpy().copy()
            for i,v in enumerate(wrong_eval):wrong_eval[i]=(v+1)%6 if v<6 else 13-v
            np.savez_compressed(out/"schedules.npz",batches=schedule,wrong_train=wrong,wrong_eval=wrong_eval)
            base=make_model(torch,plan["vocabularies"],18,34);initial={n:p.detach().clone()for n,p in base.state_dict().items()};results=[];vectors={}
            for arm in ARMS:
                model=make_model(torch,plan["vocabularies"],18,34);model.load_state_dict(initial,strict=True);configure_arm(model,arm)
                if sum(p.numel()for p in model.parameters())!=plan["parameters"]["allocated"]or sum(p.numel()for p in model.parameters()if p.requires_grad)!=plan["parameters"]["trainable"][arm]:raise ValueError("frozen allocated/trainable parameter counts differ")
                optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=.003,weight_decay=.0001)
                evaluations={};initial_vectors=None
                for step in range(201):
                    if step in(0,200):
                        model.eval();counts["evaluation_forwards"]+=1
                        with torch.inference_mode():sp,bp,bank_vectors=model(x,c,torch.as_tensor(wrong_eval)if arm=="wrong-typed"else q,full,arm,selected);sp,bp=decode(torch,sp,bp,sc)
                        evaluations[str(step)]=metrics(sp,bp,arrays,manifest,sc)
                        np.savez_compressed(out/f"{arm}-step{step}-predictions.npz",source=sp,branch=bp,source_targets=arrays["source_targets"],source_mask=arrays["source_mask"],targets=arrays["targets"],target_mask=arrays["target_mask"],source_cards=arrays["source_cards"],state_families=arrays["state_families"])
                        if step==0:initial_vectors=bank_vectors.detach().numpy().copy()
                        if step==200:vectors[arm]=bank_vectors.detach().numpy().copy()
                    if step==200:break
                    model.train();rows=schedule[step];optimizer.zero_grad(set_to_none=True);counts["training_forwards"]+=1
                    sp,bp,_=model(x[rows],c[rows],torch.as_tensor(wrong[step])if arm=="wrong-typed"else q[rows],restricted,arm,selected[rows])
                    objective=loss(torch,sp,bp,{k:v[rows]for k,v in labels.items()},sc)
                    if not bool(torch.isfinite(objective)):raise ValueError("nonfinite objective")
                    counts["backwards"]+=1;objective.backward();grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                    if not bool(torch.isfinite(grad)):raise ValueError("nonfinite gradient")
                    optimizer.step();counts["optimizer_updates"]+=1
                    append(progress,dict(global_update=counts["optimizer_updates"],arm=arm,arm_update=step+1,loss=float(objective.detach()),preclip_gradient_norm=float(grad)))
                weights={name:value.detach().numpy()for name,value in model.state_dict().items()};np.savez_compressed(out/f"{arm}-checkpoint.npz",**weights)
                if arm in("untrained-typed","id-only")and any(not np.array_equal(value,initial[name].numpy())for name,value in weights.items()if any(name.startswith(prefix)for prefix in ENCODER_PREFIXES)):raise ValueError("frozen typed encoder changed")
                if arm=="untrained-typed"and not np.array_equal(initial_vectors,vectors[arm]):raise ValueError("unused semantic vectors changed")
                if arm=="id-only"and np.any(vectors[arm][6:]):raise ValueError("held identity vector is not UNKNOWN zero")
                results.append(dict(arm=arm,allocated_parameters=sum(p.numel()for p in model.parameters()),trainable_parameters=sum(p.numel()for p in model.parameters()if p.requires_grad),evaluations=evaluations,checkpoint_sha256=sha(out/f"{arm}-checkpoint.npz"),frozen_typed_encoder=arm in("id-only","untrained-typed")))
            if counts!={"training_forwards":800,"backwards":800,"optimizer_updates":800,"evaluation_forwards":8,"export_forwards":0,"native_calls":0,"paid_jobs":0}:raise ValueError("fixed counters differ")
            for pin in plan["pins"]:
                if sha(pin["path"])!=pin["sha256"]:raise ValueError("protected source/checkpoint changed")
            if guard.rss()>1073741824:raise RuntimeError("1GiB memory limit")
            np.savez_compressed(out/"card-vectors.npz",codes=np.asarray(CODES),**vectors)
            for arm,v in vectors.items():
                if not np.isfinite(v).all():raise ValueError("nonfinite final card vectors")
                write(out/f"{arm}-vectors.json",dict(schema="whole-card-frozen-vectors/1",arm=arm,dimensions=16,cards=[dict(code=code,vector=v[i].tolist(),runtime_admitted=True,native_fixture_observed=plan["native_support"][code]["native_fixture_observed"],observed_counts=plan["native_support"][code],training_card=code in TRAIN,semantic_validated=False)for i,code in enumerate(CODES)],limitations="Eight-card frontend and sampled native behavior; not all115admitted/whole-card semantic conformance."))
            write(out/"contract.json",dict(plan_sha256=sha(plan_path),source_sha256=sha(__file__),config=CONFIG,codes=list(CODES),scalers=sc,vocabularies=plan["vocabularies"],documents_sha256=plan["document_sha256"],numeric_scale=plan["numeric_scale"]))
            write(out/"result.json",dict(status="completed",source_sha256=sha(__file__),plan_sha256=sha(plan_path),counts=counts,results=results,zero_neural_baselines=constant_baselines(arrays,manifest,sc),native_support=plan["native_support"],all_protected_inputs_unchanged=True,semantic_validated=False,guard=guard.receipt()))
        receipt=dict(status="completed",counts=counts,result_sha256=sha(out/"result.json"),progress_sha256=sha(progress),guard=guard.receipt())
        append(ledger,dict(event="stage-finish",phase="card",stage="fit",stage_id=stage_id,elapsed_seconds=receipt["guard"]["wall_seconds"],active_seconds=receipt["guard"]["wall_seconds"],optimizer_updates=800,native_applies=0,neural_forwards=808,engine_apply_attempts=0,completed_or_reserved_updates=800,charged_optimizer_updates=800,**receipt));write(out/"receipt.json",receipt)
    except BaseException as error:
        receipt=dict(status="failed-preserved",error_type=type(error).__name__,error=str(error),counts=counts,charged_updates=800,guard=guard.receipt())
        append(ledger,dict(event="stage-finish",phase="card",stage="fit",stage_id=stage_id,elapsed_seconds=receipt["guard"]["wall_seconds"],active_seconds=receipt["guard"]["wall_seconds"],optimizer_updates=counts["optimizer_updates"],native_applies=0,neural_forwards=counts["training_forwards"]+counts["evaluation_forwards"],engine_apply_attempts=0,completed_or_reserved_updates=800,charged_optimizer_updates=800,**receipt));write(out/"receipt.json",receipt);raise
    finally:
        fcntl.flock(lease,fcntl.LOCK_UN);lease.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    for name in("prepare","seal","execute"):mode.add_argument("--"+name,action="store_true")
    p.add_argument("--prepared",type=Path,default=DEFAULT/"card-prepared.json");p.add_argument("--plan",type=Path,default=DEFAULT/"card-plan.json")
    p.add_argument("--native-plan",type=Path,default=ROOT/"actual-corpus/native-plan.json");p.add_argument("--dataset",type=Path,default=ROOT/"actual-corpus/actual-corpus.npz");p.add_argument("--manifest",type=Path,default=ROOT/"actual-corpus/actual-corpus.manifest.json")
    p.add_argument("--out",type=Path,default=DEFAULT/"fit-1");p.add_argument("--ledger",type=Path,default=ROOT/"actual-corpus/campaign-ledger.jsonl");p.add_argument("--progress",type=Path,default=DEFAULT/"card-progress.jsonl")
    a=p.parse_args()
    if a.prepare:prepare(a.prepared,a.native_plan);print(json.dumps(dict(path=str(a.prepared),sha256=sha(a.prepared))))
    elif a.seal:seal(a.prepared,a.plan,a.dataset,a.manifest);print(json.dumps(dict(path=str(a.plan),sha256=sha(a.plan))))
    else:execute(a.plan,a.out,a.ledger,a.progress)
if __name__=="__main__":main()
