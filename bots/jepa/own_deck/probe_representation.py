"""Bounded synthetic ridge probes of raw own-deck inputs and frozen latents.

No actor/encoder training, optimizer, engine, opponent, hidden state, download or
kernel regeneration. These synthetic bags are not a legal-deck strength test.
"""
import os
for _thread_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_thread_var] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import own_deck as O
import own_deck_model as D

N_EXAMPLES=128
N_TRAIN=96
N_TEST=32
SEED=1907
ALPHA=0.001
CODES=tuple(f"SYN_{i:03}" for i in range(1,7))
COSTS=np.asarray([0.,1.,2.,4.,6.,8.])
TARGETS=("total_copies","specific_card_copies","cost_le_2_fraction","mean_cost","initial_specific_card_draw_probability")


def fingerprint(counts):
    text=json.dumps([(code,int(n)) for code,n in zip(CODES,counts) if n],separators=(",",":"))
    return hashlib.sha256(text.encode()).hexdigest()


def printed_catalog():
    return [{"setId":{"set":"SYN","number":i+1},"setCodes":[],"types":["unit" if i%2==0 else "event"],
             "cost":float(cost),"power":float(i+1),"hp":float(i+2),"arena":"space" if i==4 else "ground",
             "keywords":["raid"] if i==2 else [],"aspects":[O.ASPECTS[i]],"traits":[f"Synthetic {i}"]}
            for i,cost in enumerate(COSTS)]


def targets(counts):
    counts=np.asarray(counts,np.float64)
    total=counts.sum(-1)
    return np.stack([total,counts[...,0],counts[...,:3].sum(-1)/total,(counts*COSTS).sum(-1)/total,counts[...,0]/total],-1)


def make_dataset(seed=SEED):
    rng=np.random.default_rng(seed)
    bags=[]; seen=set()
    while len(bags)<N_EXAMPLES:
        counts=rng.integers(0,7,len(CODES))
        tag=fingerprint(counts)
        if counts.sum() and tag not in seen:
            seen.add(tag); bags.append(counts)
    counts=np.asarray(bags,np.int64)
    # Split complete composition groups. Every example is a unique bag.
    order=np.random.default_rng(seed+1).permutation(N_EXAMPLES)
    return counts,order[:N_TRAIN],order[N_TRAIN:]


def wrong_deck_permutation(counts,train,test,seed=SEED):
    """Within-partition bijection: every assigned own bag differs in count/curve."""
    y=targets(counts)
    out=np.arange(len(counts))
    rng=np.random.default_rng(seed+2)
    for partition in (train,test):
        options={int(i):[int(j) for j in rng.permutation(partition)
                        if i!=j and y[i,0]!=y[j,0] and y[i,1]!=y[j,1] and not np.isclose(y[i,3],y[j,3])]
                 for i in partition}
        assigned={}
        def augment(i,visited):
            for j in options[i]:
                if j in visited: continue
                visited.add(j)
                if j not in assigned or augment(assigned[j],visited):
                    assigned[j]=i
                    return True
            return False
        for i in partition:
            if not augment(int(i),set()):
                raise ValueError("no valid matched wrong-deck permutation for this seed")
        for j,i in assigned.items(): out[i]=j
    return out


def contexts(counts):
    cards=printed_catalog()
    rows=[]
    for bag in counts:
        hello={"cards":cards,"deck":{"deck":[{"id":code,"count":int(n)} for code,n in zip(CODES,bag) if n]}}
        row=O.as_array(O.encode_hello(hello))[0]
        if row[0,3]!=1: raise AssertionError("synthetic declaration must be fully known")
        rows.append(row)
    return np.asarray(rows,np.float32)


def fixed_inputs():
    fixture=json.loads((ROOT/"wasm/tests/fixtures/runtime-reference.json").read_text())
    source=next(v for v in fixture["vectors"] if v["name"]=="window-p1")
    e=source["encoded"]; used=min(e["tokens"]["n"],24)
    return (np.asarray(e["state"],np.float32).reshape(1,73),
            np.asarray(e["tokens"]["ids"][:used]+[0]*(24-used),np.int64).reshape(1,24),
            np.asarray(e["tokens"]["feats"][:used*21]+[0.]*(21*(24-used)),np.float32).reshape(1,24,21),
            np.asarray([1.]*used+[0.]*(24-used),np.float32).reshape(1,24))


def encode_latents(net,inputs,deck):
    n=len(deck)
    args=[np.repeat(v,n,axis=0) for v in inputs]
    return net.forward(*args,own_deck=deck)[0].astype(np.float64)


def ridge_predict(x,y,train,test,label_permutation=None,alpha=ALPHA):
    """Train-only standardization and ridge fit; intercept is not penalized."""
    x=np.asarray(x,np.float64); y=np.asarray(y,np.float64)
    mu=x[train].mean(0); std=x[train].std(0)
    std=np.where(std>1e-12,std,1.)
    a=(x[train]-mu)/std; b=(x[test]-mu)/std
    labels=y[train] if label_permutation is None else y[label_permutation]
    prior=labels.mean(0); centered=labels-prior
    # Dual solve bounds each regression at 96x96 even for the raw207 arm.
    weights=a.T @ np.linalg.solve(a@a.T+alpha*np.eye(len(train)),centered)
    return b@weights+prior


def metrics(pred,truth):
    pred=np.asarray(pred,np.float64); truth=np.asarray(truth,np.float64)
    err=pred-truth
    sst=((truth-truth.mean(0))**2).sum(0)
    return {target:{"mae":float(np.mean(abs(err[:,i]))),"r2":float(1-(err[:,i]**2).sum()/sst[i]) if sst[i]>0 else None}
            for i,target in enumerate(TARGETS)}


def variance_diagnostics(x):
    """Scale/collapse smoke diagnostics only; no semantic success criterion."""
    x=np.asarray(x,np.float64)
    # Exact repeated rows remain exact zero despite rounding a large mean.
    centered=x-x[0]
    centered=centered-centered.mean(0)
    std=np.sqrt((centered**2).mean(0))
    singular=np.linalg.svd(centered,compute_uv=False)
    power=singular**2
    total=power.sum()
    probabilities=power[power>0]/total if total>0 else np.asarray([])
    effective=float(np.exp(-(probabilities*np.log(probabilities)).sum())) if len(probabilities) else 0.
    i,j=np.triu_indices(len(x),1)
    distances=np.sqrt(((x[i]-x[j])**2).sum(1))
    return {"perDimensionStd":{"min":float(std.min()),"median":float(np.median(std)),"mean":float(std.mean()),"max":float(std.max()),"dimensionsAtOrBelow1e-12":int((std<=1e-12).sum())},
            "centeredRankAtRelative1e-6":int((singular>singular.max()*1e-6).sum()) if singular.max()>0 else 0,
            "varianceEntropyEffectiveRank":effective,
            "pairwiseEuclidean":{"pairs":len(distances),"min":float(distances.min()),"median":float(np.median(distances)),"mean":float(distances.mean()),"p95":float(np.quantile(distances,.95)),"max":float(distances.max())},
            "interpretation":"Scale/collapse smoke diagnostics; no threshold establishes strategic preservation or semantic understanding."}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(seed=SEED):
    started=time.monotonic()
    model=ROOT/"models/tx-t10.safetensors"
    supplement=ROOT/"wasm/generated-own-deck/deck-init.safetensors"
    protected=[model,ROOT/"models/tx-t10-e.safetensors",supplement]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    counts,train,test=make_dataset(seed)
    wrong=wrong_deck_permutation(counts,train,test,seed)
    deck=contexts(counts); neutral=O.neutral_features(N_EXAMPLES)
    w,meta=D.load_extended(model,supplement)
    net=D.NumpyOwnDeckTx(w,meta)
    inputs=fixed_inputs()
    latent=encode_latents(net,inputs,deck)
    # Same model and full batch size for every context arm.
    neutral_latent=encode_latents(net,inputs,neutral)
    wrong_latent=encode_latents(net,inputs,deck[wrong])
    arms={"raw_original":deck[:,0],"raw_neutral":neutral[:,0],"raw_wrong_deck":deck[wrong,0],
          "latent_original":latent,"latent_neutral":neutral_latent,"latent_wrong_deck":wrong_latent}
    y=targets(counts)
    permutation=np.random.default_rng(seed+3).permutation(train)
    reports={}
    for name,x in arms.items():
        pred=ridge_predict(x,y,train,test)
        null=ridge_predict(x,y,train,test,label_permutation=permutation)
        reports[name]={"inputDimensions":x.shape[1],"maeR2":metrics(pred,y[test]),
                       "permutedTrainingLabels":metrics(null,y[test])}
    prior=np.repeat(y[train].mean(0)[None],len(test),axis=0)
    fingerprints=[fingerprint(c) for c in counts]
    after={str(p.relative_to(ROOT)):sha(p) for p in protected}
    if before!=after: raise AssertionError("probe mutated a protected checkpoint")
    return {"schema":"own-deck-representation-probe/1","seed":seed,"examples":N_EXAMPLES,"trainExamples":len(train),"testExamples":len(test),
        "fixedObservation":"runtime-reference/window-p1; identical board, hand, state, token mask for every bag",
        "specificCard":CODES[0],"cardIds":list(CODES),"cardCosts":COSTS.tolist(),"targets":list(TARGETS),
        "ridge":{"alpha":ALPHA,"standardization":"train-only mean/std; constant columns left at unit scale","selection":"fixed in advance; no tuning on holdout","solver":"float64 dual96x96","actorUpdates":0,"encoderUpdates":0},
        "priorBaseline":metrics(prior,y[test]),"arms":reports,
        "frozenLatentVarianceDiagnostics":{"original":variance_diagnostics(latent),"neutral":variance_diagnostics(neutral_latent),"wrongDeck":variance_diagnostics(wrong_latent)},
        "provenance":{"compositionFingerprint":"SHA256 of sorted nonzero (printed ID,copy count) pairs","counts":counts.tolist(),"compositionFingerprints":fingerprints,
            "trainIndices":train.tolist(),"testIndices":test.tolist(),"overlappingCompositionFingerprints":0,
            "wrongDeckIndexForExample":wrong.tolist(),"wrongDeckControl":"within-partition bijection; different total copies, specific-card copies, mean cost; never opponent information",
            "permutedTrainingLabelIndices":permutation.tolist(),"seedOffsets":{"bagGeneration":0,"split":1,"wrongDeckPermutation":2,"trainingLabelPermutation":3},
            "sourceSha256":{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),Path(__file__).with_name("test_probes.py"),ROOT/"own_deck.py",ROOT/"own_deck_model.py",ROOT/"tx_model.py"]},
            "fixtureSha256":sha(ROOT/"wasm/tests/fixtures/runtime-reference.json"),"catalog":printed_catalog(),"python":platform.python_version(),"numpy":np.__version__},
        "immutableBefore":before,"immutableAfter":after,"elapsedSeconds":round(time.monotonic()-started,4),"cpuThreads":1,
        "limitations":["Raw-input decodability and frozen initialized-latent diagnostic only; no actor learning or playing-strength claim.",
            "Composition-disjoint split uses the same six card identities in train and test; it does not test unseen identities or effect-program semantics.",
            "Current representation has hashed identities and printed metadata/keyword/trait summaries, not structured card-effect programs.",
            "Initial draw-probability target is n_c/N at declaration, before any draw, with complete known original bag. No live remaining-deck probability is supported without an observation ledger.",
            "Wrong-deck and permuted-label controls may retain incidental statistical relationships; their measured MAE/R2 are reported without a forced null threshold.",
            "Small synthetic bags vary copy counts and are not asserted to satisfy game deck-building legality.",
            "The fixed existing board is an encoding foil, not a reconstructed game consistent with every synthetic original bag.",
            "The target card has a unique cost bin in this six-card catalog, making its initial fraction explicitly available; this is a deliberate contract test, not a semantics task."]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path(__file__).with_name("representation-probe.json"))
    args=p.parse_args()
    report=run()
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"examples":report["examples"],"train":report["trainExamples"],"test":report["testExamples"],"elapsedSeconds":report["elapsedSeconds"],
        "mae":{arm:{target:round(m["mae"],6) for target,m in data["maeR2"].items()} for arm,data in report["arms"].items()}},indent=2))


if __name__=="__main__": main()
