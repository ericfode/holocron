"""Bounded actual27 readout preparation; execution requires a sealed bank plan.

The CLI defaults to no execution. Frozen whole-card vector banks and the saved
current-deck96 export are data; only the common deck phi/rho/head is trainable.
Thirteen printed-composition targets establish neither semantics nor strength.
"""
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import argparse
from collections import Counter
import copy
import fcntl
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import actual_corpus_coverage as C
ROOT = C.EXPERIMENTS
SCHEMA = "actual-corpus-deck-readout/1"
ARMS = ("correct-typed","untrained-typed","id-only","current-deck")
CARD_ARMS = ARMS[:3]
ASPECTS = ("vigilance","command","aggression","cunning","heroism","villainy")
KEYWORDS = ("ambush","bounty","grit","overwhelm","raid","restore","saboteur","sentinel","shielded","sweep")
TARGETS = ("total_count_per_60","mean_cost_per_10","low_cost_le_2_fraction",*(f"cost_{i}_fraction" for i in range(8)),"cost_8_plus_fraction","initial_draw_unit_probability")
CONFIG = dict(seed=17,arms=list(ARMS),updates_per_arm=100,total_updates=400,batch_size=22,
              optimizer="AdamW",learning_rate=.003,betas=[.9,.999],epsilon=1e-8,weight_decay=0.,
              training_forwards=400,evaluation_forwards=8,export_forwards=0,seconds=60,threads=1,
              evaluation_rows=82,invariance_tolerance=1e-5,
              rss_bytes=1024**3,input_dim=130,trainable_parameters_per_arm=6829,
              loss="mean MSE over training-only varying13 composition heads; all13/perhead results retained")
LIMITS = ["Printed composition wiring only; semantic deck quality, interactions, synergy and game strength unsupported.",
          "Only8card vectors/65of1432copies; all1367unknown copies retained. Runtime admission is not conformance.",
          "Current-deck baseline had earlier composition training; historical pretraining compute unmatched.",
          "Card encoder weights frozen. All four new deck graphs/data/initialization/updates are matched."]


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def pin(path):
    path=Path(path).resolve();return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
def check(item):
    if sha(item["path"])!=item["sha256"] or Path(item["path"]).stat().st_size!=item["bytes"]:raise ValueError("frozen input changed: "+item["path"])
def append(path,row):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n");stream.flush();os.fsync(stream.fileno())


def trait_bin(text):
    value=2166136261
    for byte in text.encode():value=((value^byte)*16777619)&0xffffffff
    return value%8


def printed32(card):
    lists={}
    for key in ("types","aspects","traits","keywords"):
        value=card.get(key)
        if not isinstance(value,list) or any(not isinstance(x,str) or not x.strip() for x in value):return [0.]*32,False
        lists[key]=sorted(set(x.strip().lower() for x in value))
    types=lists["types"]
    if not types or any(x in types for x in ("leader","base","token")):return [0.]*32,False
    power=card.get("power") if "unit" in types else card.get("upgradePower",card.get("power",0)) if "upgrade" in types else 0
    hp=card.get("hp") if "unit" in types else card.get("upgradeHp",card.get("hp",0)) if "upgrade" in types else 0
    numbers=[card.get("cost"),0 if power is None and "unit" not in types else power,0 if hp is None and "unit" not in types else hp]
    if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e6 for v in numbers) or numbers[0]<0:return [0.]*32,False
    output=[v/10 for v in numbers]+[float(t in types) for t in ("unit","event","upgrade")]
    output += [float(card.get("arena")==arena) for arena in ("ground","space")]
    output += [float(t in lists["aspects"]) for t in ASPECTS]
    output += [float(any(k==t or k.startswith(t+" ") for k in lists["keywords"])) for t in KEYWORDS]
    bins=[0.]*8
    for trait in lists["traits"]:bins[trait_bin(trait)]+=1.
    return output+bins,True


def composition_targets(counts,records):
    total=sum(counts.values());cost=low=unit=0.;curve=[0.]*9
    if total<=0:raise ValueError("nonempty main list required")
    for code,n in counts.items():
        card=records[code]["card"]
        value=card.get("cost")
        if type(value) not in (int,float) or not math.isfinite(value) or value<0 or value!=int(value):raise ValueError("printed-cost target unknown")
        cost+=n*value;low+=n*(value<=2);unit+=n*("unit" in card["types"]);curve[min(int(value),8)]+=n
    return [total/60,cost/total/10,low/total,*(v/total for v in curve),unit/total]


def prepare(out,coverage):
    out=Path(out)
    if out.exists():raise FileExistsError("preserve existing preparation")
    coverage=Path(coverage);audit=read(coverage)
    if audit.get("schema")!=C.SCHEMA or audit["summary"]["main_copies"]!=1432 or audit["summary"]["main_unique_ids"]!=251:raise ValueError("wrong actual corpus")
    for item in audit["sources"].values():check(item)
    catalog=read(audit["sources"]["catalog"]["path"]);aliases,records,ambiguous=C.index_catalog(catalog)
    split=read(audit["sources"]["split"]["path"])
    current=read(audit["sources"]["decks"]["path"])
    current_rows={row["source_index"]:row for row in current["rows"]}
    cards={};rows=[]
    for deck in audit["decks"]:
        counts={entry["canonical_id"]:entry["copies"] for entry in deck["main_cards"]}
        for code in counts:
            features,known=printed32(records[code]["card"])
            cards[code]=dict(printed=features,printed_known=known)
        baseline=current_rows[deck["source_index"]]
        if C.canonical_counts(baseline["canonical_card_counts"],aliases)!=counts or len(baseline["vector"])!=96:raise ValueError("baseline alignment changed")
        if any(type(x) not in(int,float) or not math.isfinite(x) for x in baseline["vector"]):raise ValueError("nonfinite baseline")
        rows.append(dict(source_index=deck["source_index"],family_id=deck["family_id"],split=deck["split"],
                         fingerprint=deck["composition_fingerprint"],counts=counts,total_count=deck["total_main_copies"],
                         targets=composition_targets(counts,records),baseline96=baseline["vector"],coverage=deck["coverage"]))
    rows.sort(key=lambda row:row["source_index"])
    if [r["source_index"] for r in rows]!=list(range(27)):raise ValueError("all27source rows required")
    train=split["split"]["train_idx"];held=split["split"]["val_idx"]
    if set(r["family_id"] for r in rows if r["source_index"] in train)&set(r["family_id"] for r in rows if r["source_index"] in held):raise ValueError("family leakage")
    varying=[max(rows[j]["targets"][i] for j in train)>min(rows[j]["targets"][i] for j in train) for i in range(13)]
    if not any(varying):raise ValueError("empty training-varying mask")
    data=dict(schema=SCHEMA+"/data",cards=cards,rows=rows,train_idx=train,held_idx=held,target_names=TARGETS,train_varying_mask=varying,
              unknown_policy="All251 identities and1432copies retained; semantic8bank coverage distinct from complete printed information.")
    mean=[sum(rows[j]["targets"][i]for j in train)/len(train)for i in range(13)]
    data["constant_train_mean_baseline"]=dict(values=mean,held=metrics([mean for _ in rows],data,held),neural_forwards=0,optimizer_updates=0)
    out.mkdir(parents=True)
    write(out/"data.json",data)
    plan=dict(schema=SCHEMA,status="prepared-banks-pending",config=CONFIG,limitations=LIMITS,
              dataset=pin(out/"data.json"),coverage=pin(coverage),inherited_sources=audit["sources"],
              source_files=[pin(Path(__file__)),pin(HERE/"actual_corpus_coverage.py"),pin(HERE/"test_actual_corpus_coverage.py"),pin(HERE/"test_actual_corpus_deck.py"),pin(HERE/"run_events.py"),pin(HERE/"run_local_experiments.py"),pin(HERE/"ACTUAL_CORPUS_DECK_PROTOCOL.md")],
              expected_bank_codes=sorted(C.PROPOSED_IDS),expected_training_card_codes=sorted(set(C.PROPOSED_IDS)-set(C.HELD_PROPOSED_IDS)),
              banks_pending=True,card_weights_frozen=True,deck_encoder_trainable=True,
              campaign_ledger=str(ROOT/"actual-corpus/campaign-ledger.jsonl"),max_campaign_seconds=240,
              root_go_required=True,neural_forwards_preparation=0,native_calls_preparation=0)
    write(out/"plan.json",plan)
    return dict(path=str(out/"plan.json"),sha256=sha(out/"plan.json"),model_forwards=0,optimizer_updates=0,native_calls=0)


def parse_bank(value):
    if not isinstance(value,dict) or not isinstance(value.get("cards"),list):raise ValueError("whole-card bank cards list required")
    cards={}
    for row in value["cards"]:
        code=C.normalize(row.get("code"));vector=row.get("vector")
        if code in cards or code not in C.PROPOSED_IDS or not isinstance(vector,list) or len(vector)!=16 or any(type(x) not in(int,float) or not math.isfinite(x) for x in vector):raise ValueError("invalid/duplicate whole-card vector row")
        if row.get("semantic_validated") is not False:raise ValueError("no whole-card semantic validation claim admitted")
        if row.get("training_card") != (code not in C.HELD_PROPOSED_IDS):raise ValueError("held-card training flag changed")
        if row.get("runtime_admitted") is not True:raise ValueError("eight bank cards must be runtime admitted")
        observed=row.get("observed_counts")
        numeric=("declared_roots","availability_roots","committed_roots","settled_paid_roots","known_source_coordinates","known_target_coordinates")
        if not isinstance(observed,dict)or any(type(observed.get(key))is not int or observed[key]<0 for key in numeric):raise ValueError("per-card native observed_counts required")
        if observed["declared_roots"]!=4 or not 0<=observed["settled_paid_roots"]<=observed["committed_roots"]<=4:raise ValueError("invalid native settled/committed support")
        if not isinstance(observed.get("completions"),dict)or any(type(n)is not int or n<0 for n in observed["completions"].values())or sum(observed["completions"].values())!=4:raise ValueError("allfour native completion witnesses required")
        supported=observed["settled_paid_roots"]>0
        if type(row.get("native_fixture_observed"))is not bool or row["native_fixture_observed"]!=supported or observed.get("native_fixture_observed")is not supported:raise ValueError("native observed flag lacks matching settled paid support")
        cards[code]=copy.deepcopy(row)
    if set(cards)!=set(C.PROPOSED_IDS):raise ValueError("exact frozen eight-card bank required")
    return cards


def seal(plan_path,bank_directory,out):
    import numpy as np
    plan=read(plan_path)
    if plan.get("schema")!=SCHEMA or plan.get("status")!="prepared-banks-pending":raise ValueError("unsealed preparation required")
    for item in [plan["dataset"],plan["coverage"],*plan["source_files"],*plan["inherited_sources"].values()]:check(item)
    directory=Path(bank_directory)
    banks={arm:pin(directory/(arm+"-vectors.json")) for arm in CARD_ARMS}
    exported={arm:read(item["path"])for arm,item in banks.items()}
    parsed={arm:parse_bank(value)for arm,value in exported.items()}
    result=read(directory/"result.json");contract=read(directory/"contract.json")
    if result.get("status")!="completed"or result.get("semantic_validated")is not False or result.get("all_protected_inputs_unchanged")is not True:raise ValueError("completed frozen card fit required")
    if result.get("counts",{}).get("optimizer_updates")!=800 or result["counts"].get("evaluation_forwards")!=8 or result["counts"].get("export_forwards")!=0:raise ValueError("card stage fixed counters differ")
    if result.get("source_sha256")!=contract.get("source_sha256")or result.get("plan_sha256")!=contract.get("plan_sha256"):raise ValueError("card result/contract provenance mismatch")
    card_plan=directory.parent/"card-plan.json"
    if sha(card_plan)!=contract["plan_sha256"]:raise ValueError("card sealed plan hash differs")
    card_plan_value=read(card_plan)
    for item in card_plan_value["pins"]:
        if sha(item["path"])!=item["sha256"]:raise ValueError("card source/native input changed")
    checkpoints={row["arm"]:row["checkpoint_sha256"]for row in result["results"]}
    code_order=list(contract["codes"])
    with np.load(directory/"card-vectors.npz",allow_pickle=False)as pack:
        if pack["codes"].tolist()!=code_order or set(code_order)!=set(C.PROPOSED_IDS):raise ValueError("final card-vector pack IDs differ")
        for arm in CARD_ARMS:
            if exported[arm].get("schema")!="whole-card-frozen-vectors/1"or exported[arm].get("arm")!=arm or exported[arm].get("dimensions")!=16:raise ValueError("wrong/stale card bank arm/schema")
            vector=np.asarray([parsed[arm][code]["vector"]for code in code_order],np.float32)
            if pack[arm].shape!=(8,16)or not np.array_equal(pack[arm],vector):raise ValueError("JSON bank differs from saved final vectors")
            if sha(directory/(arm+"-checkpoint.npz"))!=checkpoints[arm]:raise ValueError("saved final card checkpoint differs")
            if any(parsed[arm][code]["observed_counts"]!=result["native_support"][code]for code in C.PROPOSED_IDS):raise ValueError("bank native flags differ from measured card support")
    for code in C.PROPOSED_IDS:
        flags=[{k:parsed[arm][code][k]for k in ("code","runtime_admitted","training_card","native_fixture_observed","observed_counts","semantic_validated")}for arm in CARD_ARMS]
        if any(row!=flags[0] for row in flags[1:]):raise ValueError("arm coverage/provenance flags differ; graph input domain must match")
    plan.update(status="sealed-not-executed",banks_pending=False,banks=banks,card_stage_result=pin(directory/"result.json"),
                card_stage_contract=pin(directory/"contract.json"),card_stage_plan=pin(card_plan),card_stage_vectors=pin(directory/"card-vectors.npz"),
                card_stage_checkpoints=[pin(directory/(arm+"-checkpoint.npz"))for arm in CARD_ARMS],preparation_plan=pin(plan_path))
    if Path(out).exists():raise FileExistsError("sealed plan immutable")
    write(out,plan)
    return dict(path=str(out),sha256=sha(out),model_forwards=0,optimizer_updates=0)


def feature_rows(row,cards,bank,baseline=False):
    features=[];weights=[]
    for code,n in sorted(row["counts"].items()):
        supported=code in bank
        semantic=list(row["baseline96"]) if baseline else list(bank[code]["vector"])+[0.]*80 if supported else [0.]*96
        features.append(semantic+cards[code]["printed"]+[float(supported),float(cards[code]["printed_known"])])
        weights.append(n)
    return features,weights


def pool_reference(hidden,copies,features):
    """Pure pooling contract; input hidden rows are arbitrary, not model calls."""
    if not copies or len(hidden)!=len(copies) or len(features)!=len(copies) or any(type(n)is not int or n<=0 for n in copies):raise ValueError("aligned nonempty copies required")
    total=sum(copies);sums=[math.fsum(row[i]*n for row,n in zip(hidden,copies)) for i in range(32)]
    return [x/total for x in sums]+[x/60 for x in sums]+[total/60,len(copies)/60,*(math.fsum(row[i]*n for row,n in zip(features,copies))/total for i in (128,129))]


def evaluation_rows(data,bank,baseline=False):
    """Fixed82 rows in each existing eval call; no extra model invocation.

    Duplicate-split declarations merge by canonical ID before graph entry, as
    real declarations do. Reversal tests the graph's actual row-order behavior.
    The last row increases the lexically first canonical card in source0 by1.
    """
    original=[feature_rows(row,data["cards"],bank,baseline)for row in data["rows"]]
    reversed_rows=[(x[::-1],n[::-1])for x,n in original]
    duplicate_rows=[]
    for row in data["rows"]:
        entries=[]
        for code,n in row["counts"].items():
            entries.append(dict(id=code,count=1))
            if n>1:entries.append(dict(id=code,count=n-1))
        canonical=C.canonical_counts(entries,{code:code for code in row["counts"]})
        duplicate_rows.append(feature_rows({**row,"counts":canonical},data["cards"],bank,baseline))
    perturbed=copy.deepcopy(data["rows"][0]);code=min(perturbed["counts"]);perturbed["counts"][code]+=1
    values=original+reversed_rows+duplicate_rows+[feature_rows(perturbed,data["cards"],bank,baseline)]
    width=max(len(n)for _,n in values)
    return [x+[[0.]*130]*(width-len(x))for x,n in values],[n+[0]*(width-len(n))for x,n in values]


def model_factory(torch):
    class Deck(torch.nn.Module):
        def __init__(self):
            super().__init__();self.phi=torch.nn.Linear(130,32);self.rho=torch.nn.Linear(68,32);self.head=torch.nn.Linear(32,13)
        def forward(self,x,copies):
            if x.ndim!=3 or x.shape[-1]!=130 or copies.shape!=x.shape[:2]:raise ValueError("batch×identity×130 required")
            total=copies.sum(1,keepdim=True)
            if bool((total<=0).any()):raise ValueError("empty bag")
            hidden=torch.nn.functional.gelu(self.phi(x));summed=(hidden*copies[:,:,None]).sum(1)
            coverage=(x[:,:,128:130]*copies[:,:,None]).sum(1)/total
            pooled=torch.cat((summed/total,summed/60,total/60,(copies>0).sum(1,keepdim=True).to(x.dtype)/60,coverage),1)
            z=torch.nn.functional.gelu(self.rho(pooled));return self.head(z),z
    model=Deck()
    if sum(p.numel()for p in model.parameters())!=6829:raise ValueError("graph mismatch")
    return model


def metrics(predictions,data,indices):
    per=[sum((predictions[j][i]-data["rows"][j]["targets"][i])**2 for j in indices)/len(indices) for i in range(13)]
    varying=data["train_varying_mask"]
    families=sorted({data["rows"][j]["family_id"] for j in indices})
    family_macro=[]
    for family in families:
        members=[j for j in indices if data["rows"][j]["family_id"]==family]
        family_macro.append(sum(sum((predictions[j][i]-data["rows"][j]["targets"][i])**2 for i in range(13) if varying[i])/sum(varying) for j in members)/len(members))
    return dict(all13_mse=sum(per)/13,varying_macro_mse=sum(loss for loss,keep in zip(per,varying) if keep)/sum(varying),per_head_mse=per,
                family_first_varying_macro_mse=sum(family_macro)/len(family_macro),families=len(families),declarations=len(indices),family_ids=families)


def ledger_totals(rows):
    pending=None;totals=dict(elapsed_seconds=0.,optimizer_updates=0,native_applies=0,neural_forwards=0);phases={}
    for row in rows:
        event=row.get("event");phase=row.get("phase")
        if event=="stage-start":
            if pending is not None:raise ValueError("unfinished/concurrent shared stage")
            pending=(phase,row.get("stage_id"))
        elif event=="stage-finish":
            if pending!=(phase,row.get("stage_id")):raise ValueError("shared stage mismatch")
            pending=None;p=phases.setdefault(phase,{key:0 for key in totals})
            values=dict(elapsed_seconds=row.get("elapsed_seconds",row.get("active_seconds")),
                        optimizer_updates=row.get("charged_optimizer_updates",row.get("optimizer_updates",row.get("completed_or_reserved_updates",0))),
                        native_applies=row.get("native_applies",row.get("engine_apply_attempts",0)),neural_forwards=row.get("neural_forwards",0))
            for key,value in values.items():
                if type(value) not in(int,float) or not math.isfinite(value) or value<0 or (key!="elapsed_seconds" and type(value)is not int):raise ValueError("invalid shared debit")
                totals[key]+=value;p[key]+=value
        else:raise ValueError("unsupported ledger record; never reset/credit")
    if pending is not None:raise ValueError("unfinished shared stage; coordinator review required")
    return totals,phases


def worker(messages,acknowledged,plan_path,out,progress):
    import run_local_experiments as G
    writer=G.WorkerEvents(messages);stop=threading.Event()
    def heartbeat():
        while not stop.wait(.5):writer.report_rss()
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        import numpy as np
        import torch
        torch.set_num_threads(1);torch.manual_seed(17)
        plan=read(plan_path);data=read(plan["dataset"]["path"])
        banks={arm:parse_bank(read(item["path"])) for arm,item in plan["banks"].items()}
        targets=torch.tensor([row["targets"] for row in data["rows"]],dtype=torch.float32)
        train=torch.tensor(data["train_idx"]);mask=torch.tensor(data["train_varying_mask"],dtype=torch.bool)
        template=model_factory(torch);initial=copy.deepcopy(template.state_dict());init_hash=digest({k:v.tolist()for k,v in initial.items()})
        np.savez(Path(out)/"shared-initial.npz",**{k:v.numpy()for k,v in initial.items()})
        results={};completed=forwards=0
        for arm in ARMS:
            model=model_factory(torch);model.load_state_dict(initial)
            bank=banks[arm] if arm in banks else banks["correct-typed"]
            array,copy_rows=evaluation_rows(data,bank,arm=="current-deck")
            x=torch.tensor(array,dtype=torch.float32);copies=torch.tensor(copy_rows,dtype=torch.float32)
            optimizer=torch.optim.AdamW(model.parameters(),lr=.003,betas=(.9,.999),eps=1e-8,weight_decay=0.)
            def evaluate():
                nonlocal forwards
                with torch.no_grad():prediction,latent=model(x,copies)
                forwards+=1
                gaps={}
                for label,offset in (("permutation",27),("duplicate_split",54)):
                    gaps[label+"_prediction_max_abs"]=float((prediction[:27]-prediction[offset:offset+27]).abs().max())
                    gaps[label+"_latent_max_abs"]=float((latent[:27]-latent[offset:offset+27]).abs().max())
                if max(gaps.values())>1e-5:raise ValueError("actual82-row permutation/count-canonicalization witness failed")
                gaps["copy_perturbed_latent_l2"]=float(torch.linalg.vector_norm(latent[-1]-latent[0]))
                gaps["copy_perturbed_prediction_l2"]=float(torch.linalg.vector_norm(prediction[-1]-prediction[0]))
                return prediction[:27].tolist(),latent[:27].tolist(),gaps
            pred,_,initial_invariance=evaluate();baseline=metrics(pred,data,data["held_idx"])
            writer.emit("metric","deck_initial",completed,arm=arm,metrics={k:v for k,v in baseline.items()if type(v)in(int,float)})
            losses=[]
            for step in range(1,101):
                optimizer.zero_grad(set_to_none=True);prediction,_=model(x[train],copies[train]);forwards+=1
                loss=((prediction[:,mask]-targets[train][:,mask])**2).mean()
                if not bool(torch.isfinite(loss)):raise ValueError("nonfinite fit loss")
                loss.backward();optimizer.step();completed+=1
                append(progress,dict(updates_completed=completed,arm=arm,arm_step=step,neural_forwards=forwards))
                if step%20==0:
                    losses.append(dict(step=step,loss=float(loss.detach())))
                    writer.emit("metric","deck_fit",completed,arm=arm,metrics=dict(training_loss=float(loss.detach()),arm_step=step,neural_forwards=forwards))
            final,latent,final_invariance=evaluate();held=metrics(final,data,data["held_idx"])
            np.savez(Path(out)/(arm+".npz"),**{k:v.detach().numpy()for k,v in model.state_dict().items()})
            checkpoint=pin(Path(out)/(arm+".npz"))
            vector_rows=[]
            for row,vector in zip(data["rows"],latent):
                total=row["total_count"];known=sum(n for code,n in row["counts"].items()if code in bank)
                coverage=copy.deepcopy(row["coverage"])
                for label,predicate in (("whole_card_vector_available",lambda c:True),("native_fixture_observed",lambda c:bank[c].get("native_fixture_observed")is True),("whole_card_training_id",lambda c:bank[c].get("training_card")is True)):
                    mass=sum(n for c,n in row["counts"].items()if c in bank and predicate(c));coverage[label]=dict(copies=mass,copy_fraction=mass/total,unknown_copies=total-mass)
                vector_rows.append(dict(id=f"deck-source-{row['source_index']:02d}",source_index=row["source_index"],family_id=row["family_id"],split=row["split"],
                                        fingerprint=row["fingerprint"],canonical_card_counts=row["counts"],total_count=total,coverage_layers=coverage,vector=vector))
            write(Path(out)/(arm+"-vectors.json"),dict(schema="actual-corpus-deck-frozen-vectors/1",dimension=32,arm=arm,semantic_validated=False,rows=vector_rows,checkpoint=checkpoint,
                                                     source_banks=plan["banks"],saved_baseline=plan["inherited_sources"]["decks"],limitations=LIMITS))
            write(Path(out)/(arm+"-predictions.json"),dict(predictions=final,targets=[row["targets"]for row in data["rows"]],held_indices=data["held_idx"],target_names=TARGETS))
            zero=[j for j in data["held_idx"]if not any(c in bank for c in data["rows"][j]["counts"])]
            results[arm]=dict(initial_held=baseline,final_held=held,zero_bank_covered_held=metrics(final,data,zero)if zero else None,
                              updates=100,training_losses=losses,checkpoint=checkpoint,shared_initial_sha256=init_hash,
                              initial_invariance=initial_invariance,final_invariance=final_invariance)
            results[arm]["final_minus_train_mean"]={key:held[key]-data["constant_train_mean_baseline"]["held"][key]for key in ("all13_mse","varying_macro_mse","family_first_varying_macro_mse")}
            writer.emit("metric","deck_final",completed,arm=arm,metrics={**{k:v for k,v in held.items()if type(v)in(int,float)},**final_invariance})
        result=dict(schema=SCHEMA,status="completed",optimizer_updates=completed,neural_forwards=forwards,native_applies=0,arms=results,
                    initial_state_sha256=init_hash,train_varying_mask=data["train_varying_mask"],target_names=TARGETS,
                    frozen_bank_hashes={arm:sha(item["path"])for arm,item in plan["banks"].items()},limitations=LIMITS)
        result["constant_train_mean_baseline"]=data["constant_train_mean_baseline"]
        if completed!=400 or forwards!=408:raise ValueError("exact400updates/408forwards contract violated")
        write(Path(out)/"result.json",result);writer.report_rss();messages.put(("result",G.json_primitives(result)))
        if not acknowledged.wait(3):raise RuntimeError("terminal guard acknowledgement missing")
    except BaseException as exc:
        messages.put(("failure",dict(type=type(exc).__name__,reason=str(exc),step=writer.step)));acknowledged.wait(3)
    finally:stop.set();thread.join(timeout=1.)


def execute(plan_path,out,ledger,progress,events,run_id,commit):
    plan=read(plan_path)
    if plan.get("status")!="sealed-not-executed" or plan.get("schema")!=SCHEMA:raise ValueError("sealed plan required")
    frozen=[plan["dataset"],plan["coverage"],plan["card_stage_result"],plan["card_stage_contract"],plan["card_stage_plan"],plan["card_stage_vectors"],*plan["card_stage_checkpoints"],*plan["banks"].values(),*plan["source_files"],*plan["inherited_sources"].values()]
    for item in frozen:check(item)
    if Path(ledger).resolve()!=Path(plan["campaign_ledger"]).resolve():raise ValueError("one fixed shared ledger only")
    if Path(out).exists()or Path(progress).exists():raise ValueError("new output/progress paths required")
    Path(ledger).parent.mkdir(parents=True,exist_ok=True)
    with Path(str(ledger)+".worker.lock").open("a") as lease:
        fcntl.flock(lease.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        rows=[json.loads(line)for line in Path(ledger).read_text().splitlines()if line.strip()]if Path(ledger).exists()else[]
        totals,phases=ledger_totals(rows)
        if any(row.get("phase")=="deck"for row in rows):raise ValueError("existing deck attempt requires coordinator review; no implicitretry")
        remaining=min(60.,240.-totals["elapsed_seconds"])
        if remaining<=0:raise ValueError("shared campaign time exhausted")
        Path(out).mkdir(parents=True);stage_id="deck-"+Path(out).name
        from run_events import RunEvents
        import run_local_experiments as G
        writer=RunEvents(events,run_id,commit,CONFIG,dict(plan=pin(plan_path),data=plan["dataset"]),LIMITS)
        started=time.monotonic();before={item["path"]:sha(item["path"])for item in frozen}
        append(ledger,dict(event="stage-start",phase="deck",stage_id=stage_id,reserved_updates=400,reserved_neural_forwards=408,reserved_applies=0,
                           elapsed_seconds=0,optimizer_updates=0,native_applies=0,neural_forwards=0,source_sha256=sha(__file__),plan_sha256=sha(plan_path)))
        status="failed";actual=forwards=0;result=None
        try:
            writer.emit("status","deck_start",0,status="started")
            result=G.supervise_worker(worker,(str(plan_path),str(out),str(progress)),writer,remaining,started,remaining,1024)
            actual=result["optimizer_updates"];forwards=result["neural_forwards"]
            if any(sha(path)!=digest for path,digest in before.items()):raise ValueError("frozen feature bank changed")
            journal=[json.loads(line)for line in Path(progress).read_text().splitlines()if line.strip()]
            if [row["updates_completed"]for row in journal]!=list(range(1,401)):raise ValueError("completed worker requires durable1..400journal")
            status="completed";write(Path(out)/"guard.json",result["guard"])
        finally:
            if Path(progress).exists():
                entries=[json.loads(line)for line in Path(progress).read_text().splitlines()if line.strip()]
                seq=[row["updates_completed"]for row in entries]
                if seq!=list(range(1,len(seq)+1)):status="failed"
                actual=len(seq);forwards=max([row.get("neural_forwards",0)for row in entries]or[0])if status!="completed"else forwards
            receipt=dict(phase="deck",status=status,elapsed_seconds=time.monotonic()-started,optimizer_updates=actual,native_applies=0,
                         neural_forwards=forwards,charged_optimizer_updates=400,charged_neural_forwards=408,plan=pin(plan_path),progress=pin(progress)if Path(progress).exists()else None,
                         frozen_before=before,frozen_after={path:sha(path)for path in before})
            append(ledger,dict(event="stage-finish",stage_id=stage_id,active_seconds=receipt["elapsed_seconds"],engine_apply_attempts=0,completed_or_reserved_updates=400,**receipt))
            write(Path(out)/"receipt.json",receipt)
            writer.emit("status","deck_finished",actual,status=status,metrics=dict(elapsed_seconds=receipt["elapsed_seconds"],optimizer_updates=actual,neural_forwards=forwards))
        if status!="completed":raise RuntimeError("deck stage failed; preserve charged reservation")
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true");mode.add_argument("--seal",action="store_true");mode.add_argument("--execute",action="store_true")
    parser.add_argument("--out",type=Path,required=True);parser.add_argument("--plan",type=Path)
    parser.add_argument("--coverage",type=Path,default=ROOT/"actual-corpus/coverage-v2/actual-corpus-coverage.json")
    parser.add_argument("--banks",type=Path,default=ROOT/"whole-card/fit-1")
    parser.add_argument("--ledger",type=Path,default=ROOT/"actual-corpus/campaign-ledger.jsonl")
    parser.add_argument("--progress",type=Path,default=ROOT/"actual-corpus/deck-progress.jsonl")
    parser.add_argument("--events",type=Path,default=ROOT/"run-events.jsonl");parser.add_argument("--run-id");parser.add_argument("--commit")
    args=parser.parse_args()
    if args.prepare:result=prepare(args.out,args.coverage)
    elif args.seal:result=seal(args.plan,args.banks,args.out)
    else:
        if not args.run_id or not args.commit or len(args.commit)!=40:parser.error("execute needs explicit run-id and40-character source commit")
        result=execute(args.plan,args.out,args.ledger,args.progress,args.events,args.run_id,args.commit)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":main()
