"""Frozen, train-only static geometry audit. Never imports a neural model.

--prepare writes only a plan and source/input digests, without NumPy or metrics.
--execute requires that exact plan. Root coordinates the separate bounded run.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = REPO.parent
TASKS = ROOT.parent
EXPORT = ROOT / "experiments/embedding-export"
DATA = ROOT / "experiments/data"
OUT = ROOT / "experiments/embedding-geometry"
SCHEMA = "jepa-static-embedding-geometry/1"
METHODS = ("raw_cosine", "train_centered_cosine", "train_shrunk_whitened_cosine", "count_weighted_jaccard", "printed_metadata_profile")
GROUPS = (("printed_mean_stats_per10", 8, 11), ("type_and_arena_fractions", 11, 16),
          ("printed_cost_curve", 16, 25), ("keyword_fractions", 25, 35), ("aspect_fractions", 35, 41))


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def make_plan(path):
    export = read(EXPORT / "deck-embeddings.json")
    manifest = read(DATA / "real-decks.manifest.json")
    em = read(EXPORT / "deck-embeddings.manifest.json")
    rows = export["rows"]
    train, val = manifest["split"]["train_idx"], manifest["split"]["val_idx"]
    if len(rows) != 27 or export["dimension"] != 96 or len(train) != 22 or len(val) != 5:
        raise ValueError("expected immutable 27x96 export and inherited 22/5 split")
    if [i for i, row in enumerate(rows) if row["split"] == "validation"] != val:
        raise ValueError("export and inherited manifest split disagree")
    controls = {}
    for name, key in (("family", "family_id"), ("leader", "leader"), ("base", "base"), ("main_identity", "composition_fingerprint")):
        get = lambda i: rows[i][key]["id"] if key in ("leader", "base") else rows[i][key]
        controls[name] = [[rows[a]["id"], rows[b]["id"]] for a in val for b in val if a < b and get(a) == get(b)]
    sources = [EXPORT / "deck-embeddings.json", EXPORT / "deck-embeddings.manifest.json",
               DATA / "real-decks.npz", DATA / "real-decks.manifest.json",
               TASKS / "task-17/jepa-deck-neighbor-annotations.json", TASKS / "task-17/jepa-deck-neighbor-annotations.md",
               TASKS / "task-16/jepa-effects-review.json", TASKS / "task-16/jepa-effects-review.md",
               TASKS / "task-15/review_pairs.json", TASKS / "task-15/review_pairs.md"]
    protected = [dict(path=str(Path(em[k]["path"])), sha256=em[k]["sha256"]) for k in ("base", "supplement")]
    plan = dict(schema=SCHEMA, status="frozen-before-new-geometry-metrics", created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                source=dict(path=str(Path(__file__)), sha256=sha(__file__)), inputs=[dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size) for p in sources],
                protected=protected, train_indices=train, validation_indices=val, validation_ids=[rows[i]["id"] for i in val],
                controls=controls, methods=list(METHODS), dtype="float64", zero_norm_epsilon=1e-12,
                transformations=dict(mean="arithmetic mean of training22 raw vectors ONLY",
                    covariance="unbiased training covariance, denominator21, float64 symmetric eigendecomposition",
                    whitening="fixed alpha0.1: C_reg=0.9*C+0.1*trace(C)/96*I; W=C_reg^(-1/2); apply (z-train_mean)@W then cosine",
                    shrinkage_alpha=0.1, eigen_rank_relative_tolerance=1e-10, hyperparameter_search=False,
                    validation_used_for_fitting=False, raw_vectors_modified=False),
                independent_baselines=dict(count_weighted_jaccard="sum min(copies)/sum max(copies), canonical declared MAIN only; no leader/base/sideboard",
                    printed_metadata_profile=dict(source="known original-row input metadata, not learned latents; excludes status, identity hashes and hashed traits",
                        groups=[dict(name=n, start=a, stop=b, within_group="mean absolute coordinate difference") for n,a,b in GROUPS],
                        distance="equal mean of the five group distances; similarity=-distance; no fitted scaling"),
                    interpretation="Independent computations from actual declared counts/printed metadata, not independent semantic relevance labels"),
                metrics=dict(geometry="raw norms, alignment/energy in train mean, training uncentered and centered spectra, entropy/participation effective rank, residual norms/pair distances, whitening condition and held-out out-of-train-span energy",
                    composition_retrieval="five validation queries against22 training candidates; fixed top1/top3 and count/profile proxy scores, query and held-out-family macro averages",
                    structural_control="validation queries against all other26 decks; family/leader/base/exact-main positives fixed here; only queries with positives have recall/MRR, print all denominators",
                    annotations="all selected pairs get descriptive score/rank changes only; no annotation accuracy, majority voting, p values, significance or semantic-improvement claim",
                    pair_correlations="descriptive tie-aware Spearman against count/profile baselines on train-training and validation-training pairs; dependent pairs are not independent samples"),
                annotation_limits="Metric-aware posthoc selection, mostly training pairs; five validation decks/four families are already seen composition holdouts, not new card-identity or gameplay truth",
                limits=dict(active_wall_seconds=20, cpu_seconds=20, sampled_rss_bytes=512*1024*1024, sample_interval_seconds=.05, compute_threads=1,
                            neural_forwards=0, optimizer_updates=0, native_calls=0, paid_jobs=0),
                no_touch="Do not alter raw vectors, checkpoints, prior negative evidence, current native-contrast model/config, or other owners' sources")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("refusing to replace an existing frozen plan")
    write(path, plan)
    return plan


class BudgetStop(RuntimeError):
    pass


class Guard:
    def __init__(self, out):
        self.out, self.started = out, time.monotonic()
        self.cpu_before = resource.getrusage(resource.RUSAGE_SELF)
        self.stopped, self.peak, self.samples = threading.Event(), 0, 0

    def rss(self):
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)

    def __enter__(self):
        def stop(signum, frame):
            raise BudgetStop("static geometry wall/CPU/RSS allowance reached")
        for sig in (signal.SIGALRM, signal.SIGXCPU, signal.SIGUSR1):
            signal.signal(sig, stop)
        signal.setitimer(signal.ITIMER_REAL, 20)
        resource.setrlimit(resource.RLIMIT_CPU, (19, 20))
        def monitor():
            while not self.stopped.wait(.05):
                self.peak = max(self.peak, self.rss())
                self.samples += 1
                if self.peak > 512 * 1024 * 1024:
                    os.kill(os.getpid(), signal.SIGUSR1)
                    break
        self.thread = threading.Thread(target=monitor, daemon=True)
        self.thread.start()
        return self

    def receipt(self):
        current = resource.getrusage(resource.RUSAGE_SELF)
        return dict(elapsed_seconds=time.monotonic()-self.started,
                    cpu_seconds=(current.ru_utime+current.ru_stime)-(self.cpu_before.ru_utime+self.cpu_before.ru_stime),
                    peak_rss_bytes=max(self.peak,self.rss()), samples=self.samples, worker_pid=os.getpid(), compute_threads=1,
                    limitation="One owned process; RSS is sampled high-water rusage, not an instantaneous OS memory reservation. NumPy import is inside the guard.")

    def __exit__(self, *args):
        signal.setitimer(signal.ITIMER_REAL, 0)
        self.stopped.set()
        self.thread.join(timeout=.2)


def analyze(plan, plan_path, out):
    import numpy as np
    export = read(EXPORT / "deck-embeddings.json")
    records = export["rows"]
    ids = [r["id"] for r in records]
    train, val = np.asarray(plan["train_indices"]), np.asarray(plan["validation_indices"])
    z = np.asarray([r["vector"] for r in records], np.float64)
    if z.shape != (27,96) or not np.isfinite(z).all():
        raise ValueError("raw vectors changed shape or contain nonfinite entries")
    with np.load(DATA / "real-decks.npz", allow_pickle=False) as bank:
        features = np.asarray(bank["deck_features"], np.float64)
        if bank["train_idx"].tolist() != train.tolist() or bank["val_idx"].tolist() != val.tolist():
            raise ValueError("input NPZ split differs from frozen plan")
    if features.shape != (27,2,207) or not np.all(features[:,0,3] == 1):
        raise ValueError("expected all-known original printed metadata")
    eps = plan["zero_norm_epsilon"]
    def norms(a):
        return np.linalg.norm(a, axis=1)
    def stats(a):
        a = np.asarray(a, np.float64)
        return dict(n=int(a.size), minimum=float(a.min()), median=float(np.median(a)), mean=float(a.mean()), maximum=float(a.max()), std=float(a.std())) if a.size else dict(n=0)
    def cosine(a):
        n = norms(a)
        u = np.divide(a, n[:,None], out=np.zeros_like(a), where=n[:,None]>eps)
        score = np.clip(u@u.T,-1,1)
        score[(n<=eps)[:,None] | (n<=eps)[None,:]] = np.nan
        return score
    def spectrum(a, centered):
        values = np.linalg.eigvalsh(a.T@a/(len(a)-1 if centered else len(a)))[::-1]
        if values[0] > 0 and values[-1] < -values[0]*1e-10:
            raise ValueError("unexpected covariance negative eigenvalue")
        values = np.maximum(values,0)
        total = values.sum()
        p = values[values>0]/total if total>0 else np.array([])
        return dict(eigenvalues=values.tolist(), numerical_rank=int((values>values[0]*1e-10).sum()) if values[0]>0 else 0,
                    entropy_effective_rank=float(np.exp(-(p*np.log(p)).sum())) if len(p) else 0.,
                    participation_effective_rank=float(total**2/(values@values)) if total>0 else 0.,
                    top_variance_fractions={str(k):float(values[:k].sum()/total) if total>0 else None for k in (1,3,5,10)},
                    rank_limit=min(a.shape) - (1 if centered else 0))
    mu = z[train].mean(0)
    centered = z-mu
    cov = centered[train].T@centered[train]/(len(train)-1)
    eigen, vectors = np.linalg.eigh(cov)
    eigen = np.maximum(eigen,0)
    tau, alpha = float(eigen.sum()/96), plan["transformations"]["shrinkage_alpha"]
    ridge = (1-alpha)*eigen+alpha*tau
    whitened, whitening = None, dict(available=False, reason="zero training covariance")
    if tau>eps:
        w = (vectors/np.sqrt(ridge)[None,:])@vectors.T
        whitened = centered@w
        whitening = dict(available=True, alpha=alpha, tau=tau, condition_number=float(ridge.max()/ridge.min()),
                         largest_gain=float(1/np.sqrt(ridge.min())), smallest_gain=float(1/np.sqrt(ridge.max())),
                         training_rank=int((eigen>eigen.max()*1e-10).sum()))
        np.savez(out/"train-transform.npz", train_mean=mu, whitening=w, training_covariance=cov, regularized_eigenvalues=ridge)
    pair_indices = np.triu_indices(27,1)
    euclidean = np.sqrt(np.maximum(((z[:,None,:]-z[None,:,:])**2).sum(2),0))
    centered_euclidean = np.sqrt(np.maximum(((centered[:,None,:]-centered[None,:,:])**2).sum(2),0))
    if not np.allclose(euclidean,centered_euclidean,atol=1e-12,rtol=1e-12):
        raise AssertionError("centering must preserve raw Euclidean distances")
    count_codes = sorted({c for row in records for c in row["canonical_card_counts"]})
    counts = np.asarray([[r["canonical_card_counts"].get(c,0) for c in count_codes] for r in records],np.float64)
    numerator = np.minimum(counts[:,None,:],counts[None,:,:]).sum(2)
    denominator = np.maximum(counts[:,None,:],counts[None,:,:]).sum(2)
    jaccard = np.divide(numerator,denominator,out=np.ones_like(numerator),where=denominator>0)
    metadata_distance = sum(np.abs(features[:,None,0,a:b]-features[None,:,0,a:b]).mean(2) for _,a,b in GROUPS)/len(GROUPS)
    scores = dict(raw_cosine=cosine(z), train_centered_cosine=cosine(centered), count_weighted_jaccard=jaccard,
                  printed_metadata_profile=-metadata_distance)
    if whitened is not None:
        scores["train_shrunk_whitened_cosine"] = cosine(whitened)
    def ordered(score, query, gallery):
        return sorted((int(i) for i in gallery if i != query and np.isfinite(score[query,i])), key=lambda i:(-float(score[query,i]),ids[i]))
    def aggregate_proxy(items):
        if not items:
            return dict(eligible_queries=0)
        families = sorted({r["family_id"] for r in items})
        keys = ("top1_weighted_jaccard", "top1_metadata_distance", "best_available_jaccard_minus_top1")
        return dict(eligible_queries=len(items), query_means={k:sum(r[k] for r in items)/len(items) for k in keys},
                    family_count=len(families), family_macro={k:sum(sum(r[k] for r in items if r["family_id"]==f)/sum(r["family_id"]==f for r in items) for f in families)/len(families) for k in keys})
    retrieval, controls = {}, {}
    for method,score in scores.items():
        query_rows=[]
        for query in val:
            order=ordered(score,query,train)
            if not order:
                continue
            first=order[0]
            query_rows.append(dict(query=ids[query], family_id=records[query]["family_id"], top1_weighted_jaccard=float(jaccard[query,first]),
                top1_metadata_distance=float(metadata_distance[query,first]), best_available_jaccard_minus_top1=float(jaccard[query,train].max()-jaccard[query,first]),
                neighbors=[dict(id=ids[i],score=float(score[query,i]),weighted_jaccard=float(jaccard[query,i]),metadata_distance=float(metadata_distance[query,i])) for i in order[:3]]))
        retrieval[method]=dict(gallery="training22 only", queries=query_rows, aggregate=aggregate_proxy(query_rows),
            meaning="Count/profile composition proxies only. A baseline optimizing its own proxy is not independently validated semantics.")
        control_methods={}
        for name,pairs in plan["controls"].items():
            relevant={i:set() for i in val}
            for a,b in pairs:
                ia,ib=ids.index(a),ids.index(b)
                relevant[ia].add(ib);relevant[ib].add(ia)
            detail=[]
            for query in val:
                if not relevant[query]:
                    continue
                order=ordered(score,query,range(27))
                rank=min((order.index(i)+1 for i in relevant[query] if i in order),default=None)
                detail.append(dict(query=ids[query],relevant_ids=[ids[i] for i in sorted(relevant[query])],best_positive_rank=rank,
                                   top3=[ids[i] for i in order[:3]]))
            control_methods[name]=dict(positive_unordered_pairs=len(pairs),eligible_queries=len(detail),all_validation_queries=5,detail=detail,
                recall_at1=sum(d["best_positive_rank"]==1 for d in detail)/len(detail) if detail else None,
                recall_at3=sum(d["best_positive_rank"] is not None and d["best_positive_rank"]<=3 for d in detail)/len(detail) if detail else None,
                mean_reciprocal_rank=sum(1/d["best_positive_rank"] if d["best_positive_rank"] else 0 for d in detail)/len(detail) if detail else None,
                caveat="Structural group control, not semantic truth; reciprocal directions of one pair are dependent. Training-only gallery has no positive family/leader/base controls by inherited split.")
        controls[method]=control_methods
    def rankdata(a):
        order=np.argsort(a,kind="stable");rank=np.zeros(len(a));i=0
        while i<len(a):
            j=i+1
            while j<len(a) and a[order[j]]==a[order[i]]:
                j+=1
            rank[order[i:j]]=(i+j-1)/2+1;i=j
        return rank
    def spearman(a,b):
        good=np.isfinite(a)&np.isfinite(b);a,b=rankdata(a[good]),rankdata(b[good])
        if not len(a):
            return dict(pairs=0,rho=None,interpretation="No finite pairs")
        aa,bb=a-a.mean(),b-b.mean()
        norm=np.linalg.norm(aa)*np.linalg.norm(bb)
        return dict(pairs=int(len(a)),rho=float(aa@bb/norm) if norm>eps else None,interpretation="Descriptive dependent-pair statistic; no p value or independent-sample claim")
    correlations={}
    for method,score in scores.items():
        if method in ("count_weighted_jaccard","printed_metadata_profile"):
            continue
        correlations[method]={}
        for split,ij in (("train_train",np.triu_indices(len(train),1)),("validation_train",None)):
            a,b=(train[ij[0]],train[ij[1]]) if ij is not None else (np.repeat(val,len(train)),np.tile(train,len(val)))
            correlations[method][split]=dict(counts=spearman(score[a,b],jaccard[a,b]),metadata=spearman(score[a,b],-metadata_distance[a,b]))
    # Review pairs were selected using existing metrics. Preserve each judgment as prose only.
    reviews=[]
    for task,filename in ((17,"jepa-deck-neighbor-annotations.json"),(16,"jepa-effects-review.json"),(15,"review_pairs.json")):
        original=read(TASKS/f"task-{task}"/filename);pair_rows=[]
        for pair in original["pairs"]:
            left,right=(pair["left"],pair["right"]) if task==17 else (pair["deck_a"],pair["deck_b"])
            identify=lambda r:r.get("source_deck_id",r.get("entity_id",r.get("id")))
            a,b=ids.index(identify(left)),ids.index(identify(right));judgment=pair["judgment"]
            if isinstance(judgment,dict):
                judgment=judgment.get("label",judgment.get("judgment",str(judgment)[:160]))
            ranks={}
            for method,score in scores.items():
                all_pairs=sorted(((i,j) for i in range(27) for j in range(i+1,27) if np.isfinite(score[i,j])),key=lambda ij:(-float(score[ij]),ids[ij[0]],ids[ij[1]]))
                key=(min(a,b),max(a,b))
                ranks[method]=dict(score=float(score[a,b]) if np.isfinite(score[a,b]) else None,global_pair_rank=all_pairs.index(key)+1 if key in all_pairs else None)
            pair_rows.append(dict(left=ids[a],right=ids[b],split=f"{records[a]['split']}/{records[b]['split']}",judgment=judgment,ranks=ranks))
        reviews.append(dict(source_task=task,pair_count=len(pair_rows),pairs=pair_rows,
                            use="Posthoc metric-selected qualitative context only; no accuracy, majority label or new holdout relevance truth"))
    train_span=vectors[:,eigen>eigen.max()*1e-10] if eigen.max()>0 else np.zeros((96,0))
    val_res=centered[val]
    residual=val_res-val_res@train_span@train_span.T
    directions=norms(z)*np.linalg.norm(mu)
    mean_cos=np.divide(z@mu,directions,out=np.zeros(27),where=directions>eps)
    geometry=dict(norms=stats(norms(z)),per_row=[dict(id=ids[i],split=records[i]["split"],raw_norm=float(norms(z)[i]),centered_norm=float(norms(centered)[i]),cosine_to_train_mean=float(mean_cos[i])) for i in range(27)],
        train_mean_norm=float(np.linalg.norm(mu)),train_common_mean_energy_fraction=float(len(train)*(mu@mu)/(z[train]**2).sum()),
        train_centered_energy_fraction=float((centered[train]**2).sum()/(z[train]**2).sum()),
        train_uncentered_second_moment=spectrum(z[train],False),train_centered_covariance=spectrum(centered[train],True),
        raw_pair_euclidean=stats(euclidean[pair_indices]),centered_pair_euclidean=stats(centered_euclidean[pair_indices]),
        centered_distance_identity_max_error=float(np.max(abs(euclidean-centered_euclidean))),
        whitening=whitening,heldout_out_of_train_span_energy_fraction=float((residual**2).sum()/(val_res**2).sum()) if (val_res**2).sum()>eps else None,
        pair_similarity={method:stats(score[pair_indices][np.isfinite(score[pair_indices])]) for method,score in scores.items()})
    return dict(schema=SCHEMA,status="completed",numpy=np.__version__,plan_sha256=sha(plan_path),geometry=geometry,
                heldout_composition_proxy_retrieval=retrieval,heldout_structural_controls=controls,correlations=correlations,posthoc_reviews=reviews,
                numerical_artifacts=dict(train_transform_sha256=sha(out/"train-transform.npz") if (out/"train-transform.npz").exists() else None),
                limitations=["Five validation decks in four inherited families; their card identities overlap training decks.",
                    "Only one held-out same-family/leader pair supports two dependent retrieval queries; no exact-main/base positive pairs.",
                    "Centering/whitening can change a common cone without establishing improved semantics or playing strength.",
                    "Whitening96 dimensions from22 training examples is underdetermined; fixed shrinkage stabilizes inversion but does not validate new directions.",
                    "Metadata/count baselines share input information with the encoder and are composition proxies, not independent gameplay labels.",
                    "Metric-selected annotation pairs and repeated reviewers are not independent heldout truth; no majority voting or inferential tests."])


def execute(plan_path,out):
    out.mkdir(parents=True,exist_ok=False)
    guard=Guard(out)
    try:
        with guard:
            plan=read(plan_path)
            if plan["source"]["sha256"]!=sha(__file__):
                raise ValueError("source differs from frozen plan")
            before={item["path"]:item["sha256"] for item in plan["inputs"]+plan["protected"]}
            for path,digest in before.items():
                if sha(path)!=digest:
                    raise ValueError("protected input changed: "+path)
            result=analyze(plan,plan_path,out)
            if any(sha(path)!=digest for path,digest in before.items()):
                raise ValueError("protected vectors/checkpoints/reviews changed during audit")
            result["guard"]=guard.receipt()
            if result["guard"]["peak_rss_bytes"]>512*1024*1024:
                raise BudgetStop("512 MiB RSS allowance exceeded")
            result["protected_inputs_unchanged"]=True
            result["counts"]=dict(neural_forwards=0,optimizer_updates=0,native_calls=0,paid_jobs=0)
            write(out/"result.json",result)
        receipt=dict(schema=SCHEMA,status="completed",source_sha256=sha(__file__),plan_sha256=sha(plan_path),result_sha256=sha(out/"result.json"),guard=guard.receipt(),
                     neural_forwards=0,optimizer_updates=0,native_calls=0,paid_jobs=0)
        write(out/"receipt.json",receipt)
        print(json.dumps(receipt,indent=2))
    except BaseException as error:
        write(out/"error.json",dict(status="failed",error=repr(error),guard=guard.receipt(),source_sha256=sha(__file__),plan_sha256=sha(plan_path)))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true")
    mode.add_argument("--execute",action="store_true")
    parser.add_argument("--plan",type=Path,default=OUT/"plan.json")
    parser.add_argument("--out",type=Path,default=OUT/"run-1")
    args=parser.parse_args()
    if args.prepare:
        plan=make_plan(args.plan)
        print(json.dumps(dict(plan=str(args.plan),plan_sha256=sha(args.plan),source_sha256=plan["source"]["sha256"],train=22,validation=5,controls=plan["controls"]),indent=2))
    else:
        execute(args.plan,args.out)


if __name__=="__main__":
    main()
