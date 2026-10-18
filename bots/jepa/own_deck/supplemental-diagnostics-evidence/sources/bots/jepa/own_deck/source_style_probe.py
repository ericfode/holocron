"""Bounded frozen-vector weak-style evaluation; no neural imports or optimizer.

--prepare freezes inputs/source and performs no metrics. --execute is permitted
only after root approval of the emitted execution plan. Original proposal stays
immutable; its optional secondary retrieval analyses are explicitly disabled.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import time

import embedding_geometry_audit as G

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCHEMA = "jepa-source-style-evaluation/1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def classification(truth, predictions, families, classes):
    matrix = [[0 for _ in classes] for _ in classes]
    for gold, prediction in zip(truth, predictions):
        if prediction is not None:
            matrix[classes.index(gold)][classes.index(prediction)] += 1
    per_class = {}
    for i, label in enumerate(classes):
        support = truth.count(label)
        predicted = predictions.count(label)
        tp = matrix[i][i]
        recall = tp / support if support else None
        precision = tp / predicted if predicted and support else (0. if support else None)
        f1 = 2 * precision * recall / (precision + recall) if support and precision + recall else (0. if support else None)
        per_class[label] = dict(support=support, predicted=predicted, correct=tp, precision=precision, recall=recall, f1=f1)
    supported = [v for v in per_class.values() if v["support"]]
    groups = defaultdict(list)
    for gold, pred, family in zip(truth, predictions, families):
        groups[family].append(float(gold == pred))
    correct = sum(a == b for a,b in zip(truth, predictions))
    return dict(rows=len(truth), predictions_available=sum(p is not None for p in predictions), correct=correct,
                accuracy=correct / len(truth), families=len(groups),
                family_macro_accuracy=sum(sum(v)/len(v) for v in groups.values()) / len(groups),
                classes=classes, confusion_counts=matrix, per_class=per_class,
                supported_class_macro_recall=sum(v["recall"] for v in supported)/len(supported),
                supported_class_macro_f1=sum(v["f1"] for v in supported)/len(supported),
                all_five_class_macro=None, all_five_class_macro_reason="Two held truth classes unsupported",
                unsupported_classes=[label for label,v in per_class.items() if not v["support"]])


def neighborhood(scores, candidate_indices, candidate_labels, candidate_ids, classes, gold, k):
    import math
    available = [i for i,value in enumerate(scores) if math.isfinite(float(value))]
    available.sort(key=lambda i: (-float(scores[i]), candidate_indices[i]))
    if len(available) < k:
        return dict(k=k, prediction=None, reason="Fewer than k finite candidate scores", agreement=None,
                    fractional_boundary_tie_agreement=None)
    selected = available[:k]
    cutoff = float(scores[selected[-1]])
    boundary = [i for i in available if abs(float(scores[i])-cutoff) <= 1e-12]
    strict = [i for i in available if float(scores[i]) > cutoff + 1e-12]
    fraction = (k-len(strict))/len(boundary)
    votes = Counter(candidate_labels[i] for i in selected)
    vote_ties = [label for label in classes if votes[label] == max(votes.values())]
    return dict(k=k, prediction=vote_ties[0], vote_ties=vote_ties,
                neighbors=[dict(id=candidate_ids[i], source_index=candidate_indices[i], style=candidate_labels[i], score=float(scores[i])) for i in selected],
                agreement=sum(candidate_labels[i] == gold for i in selected)/k,
                fractional_boundary_tie_agreement=(sum(candidate_labels[i] == gold for i in strict)+fraction*sum(candidate_labels[i] == gold for i in boundary))/k,
                cutoff_tie_ids=[candidate_ids[i] for i in boundary], cutoff_tie_weight=fraction)


def prepare(proposal_path, execution_path):
    started = time.monotonic()
    if execution_path.exists():
        raise FileExistsError("Refusing to replace frozen execution plan")
    proposal = read(proposal_path)
    inputs = [*proposal["inputs"], *proposal["protected_checkpoints"], proposal["source"], pin(proposal_path), pin(HERE / "embedding_geometry_audit.py")]
    for item in inputs:
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Proposal source/input pin differs: " + item["path"])
    plan = dict(schema=SCHEMA, status="prepared-awaiting-root-execution-GO", proposal=pin(proposal_path),
                source=pin(__file__), guard_source=pin(HERE / "embedding_geometry_audit.py"), inputs=inputs,
                source_git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip(),
                source_is_working_file_pinned_by_sha256=True, no_git_stage_or_commit=True,
                scope="Primary five validation queries against TRAIN22, k1/k3, five distances+majority and fixed alpha1 ridge; ALL optional27 LOO/LOFO analyses disabled",
                no_tuning=True, neural_forwards=0, optimizer_updates=0, native_calls=0,
                preparations_attempted=1, preparation_elapsed_seconds=time.monotonic()-started,
                limits=proposal["limits"])
    execution_path.parent.mkdir(parents=True, exist_ok=True)
    write(execution_path, plan)
    print(json.dumps(dict(plan=pin(execution_path), source=plan["source"], preparation_elapsed_seconds=plan["preparation_elapsed_seconds"], git_head=plan["source_git_head"]), indent=2))


def analyze(proposal):
    import numpy as np
    audit = read(proposal["source_audit"]["path"])
    rows = audit["rows"]
    classes = proposal["labels"]["classes"]
    paths = {Path(item["path"]).name: item["path"] for item in proposal["inputs"]}
    exported = read(paths["deck-embeddings.json"])["rows"]
    train = np.asarray(proposal["split"]["train_indices"], np.int64)
    val = np.asarray(proposal["split"]["validation_indices"], np.int64)
    with np.load(paths["real-decks.npz"], allow_pickle=False) as bank:
        features = bank["deck_features"].astype(np.float64)
        assert bank["train_idx"].tolist() == train.tolist() and bank["val_idx"].tolist() == val.tolist()
    z = np.asarray([r["vector"] for r in exported], np.float64)
    assert z.shape == (27,96) and np.isfinite(z).all() and features.shape == (27,2,207)
    with np.load(proposal["transforms"]["use_saved_transform"], allow_pickle=False) as transform:
        mean, whitening = transform["train_mean"].copy(), transform["whitening"].copy()
    assert np.allclose(mean, z[train].mean(0), atol=1e-12, rtol=1e-12)
    latent = {"raw_cosine":z, "train_centered_cosine":z-mean, "train_shrunk_whitened_cosine":(z-mean)@whitening}
    def cosine(values):
        norms = np.linalg.norm(values, axis=1)
        unit = np.divide(values, norms[:,None], out=np.zeros_like(values), where=norms[:,None]>1e-12)
        scores = np.clip(unit[val]@unit[train].T, -1, 1)
        scores[(norms[val]<=1e-12)[:,None] | (norms[train]<=1e-12)[None,:]] = np.nan
        return scores
    scores = {key:cosine(value) for key,value in latent.items()}
    all_codes = sorted({code for row in exported for code in row["canonical_card_counts"]})
    counts = np.asarray([[row["canonical_card_counts"].get(code,0) for code in all_codes] for row in exported],np.float64)
    numerator = np.minimum(counts[val,None,:],counts[None,train,:]).sum(2)
    denominator = np.maximum(counts[val,None,:],counts[None,train,:]).sum(2)
    scores["count_weighted_jaccard"] = np.divide(numerator, denominator, out=np.ones_like(numerator), where=denominator>0)
    groups = proposal["independent_baselines"]["printed_profile"]["groups"]
    distance = sum(np.abs(features[val,None,0,g["start"]:g["stop"]]-features[None,train,0,g["start"]:g["stop"]]).mean(2) for g in groups)/len(groups)
    scores["printed_metadata_profile"] = -distance
    truth = [rows[i]["source_style"] for i in val]
    families = [rows[i]["family_id"] for i in val]
    candidate_labels = [rows[i]["source_style"] for i in train]
    candidate_ids = [rows[i]["id"] for i in train]
    candidate_source_indices = [rows[i]["source_index"] for i in train]
    label_counts = Counter(candidate_labels)
    majority = min(classes, key=lambda c:(-label_counts[c], c))
    results = {}
    for method,matrix in scores.items():
        query_rows = []
        for q, row_index in enumerate(val):
            query_rows.append(dict(id=rows[row_index]["id"], source_index=rows[row_index]["source_index"],
                                   family_id=rows[row_index]["family_id"], source_style=truth[q],
                                   neighborhoods={str(k):neighborhood(matrix[q],candidate_source_indices,candidate_labels,candidate_ids,classes,truth[q],k) for k in (1,3)}))
        summaries = {}
        for k in (1,3):
            summaries[str(k)] = classification(truth,[r["neighborhoods"][str(k)]["prediction"] for r in query_rows],families,classes)
            for key in ("agreement", "fractional_boundary_tie_agreement"):
                values = [r["neighborhoods"][str(k)][key] for r in query_rows]
                valid = [(i,v) for i,v in enumerate(values) if v is not None]
                fam = defaultdict(list); styles = defaultdict(list)
                for i,v in valid:
                    fam[families[i]].append(v); styles[truth[i]].append(v)
                summaries[str(k)][key] = dict(rows=len(valid), mean=sum(v for _,v in valid)/len(valid) if valid else None,
                    family_macro=sum(sum(v)/len(v) for v in fam.values())/len(fam) if fam else None,
                    supported_class_macro=sum(sum(v)/len(v) for v in styles.values())/len(styles) if styles else None)
        results[method] = dict(queries=query_rows,summaries=summaries)
    majority_result = classification(truth,[majority]*len(val),families,classes)
    majority_result["predicted_style"] = majority
    # Closed-form alpha1 only, never an optimizer or validation-driven choice.
    vocab = sorted({code for i in train for code in exported[i]["canonical_card_counts"]})
    known = set(vocab)
    count_features = np.asarray([[row["canonical_card_counts"].get(c,0)/60 for c in vocab]+[sum(n for c,n in row["canonical_card_counts"].items() if c not in known)/60] for row in exported],np.float64)
    printed = np.concatenate([features[:,0,g["start"]:g["stop"]] for g in groups],axis=1)
    ridge_inputs = {**latent, "canonical_counts":count_features, "printed_metadata_profile":printed}
    y = np.eye(len(classes),dtype=np.float64)[[classes.index(c) for c in candidate_labels]]
    y_mean = y.mean(0)
    ridge = {}
    for method,x in ridge_inputs.items():
        mu,std = x[train].mean(0),x[train].std(0)
        varying = std > 0
        scaled = np.divide(x-mu,std,out=np.zeros_like(x),where=varying)
        x_train = scaled[train]
        w = x_train.T@np.linalg.solve(x_train@x_train.T+np.eye(len(train)), y-y_mean)
        predictions = scaled[val]@w+y_mean
        labels = [classes[i] for i in predictions.argmax(1)]
        ridge[method] = dict(alpha=1., input_dimension=x.shape[1], zero_train_variance_columns=int((~varying).sum()),
            summary=classification(truth,labels,families,classes), queries=[dict(id=rows[i]["id"],source_index=rows[i]["source_index"],
                family_id=rows[i]["family_id"],source_style=truth[j],prediction=labels[j],class_scores=predictions[j].tolist()) for j,i in enumerate(val)],
            scores_are_calibrated_probabilities=False)
    return dict(schema=SCHEMA,status="completed",numpy=np.__version__,classes=classes,support=audit["support"],
                inherited_train_indices=train.tolist(), inherited_validation_indices=val.tolist(),
                nearest_neighbors=results, train_majority=majority_result, fixed_alpha1_ridge=ridge,
                count_ridge_vocabulary=vocab, unseen_copy_feature_index=len(vocab),
                limits_and_interpretation=["Weak single fixture labels, not established strategic or behavioral truth.",
                    "Five held decks in four families; only three held truth styles; both control classes unsupported/null.",
                    "All old vectors and some held examples previously inspected. New label question is exploratory.",
                    "Raw/centered standardization yields redundant ridge representations; no best-transform selection.",
                    "No optimizer, hyperparameter search, new neural forward, native calls or gameplay evaluation."])


def execute(plan_path, out):
    out.mkdir(parents=True, exist_ok=False)
    guard = G.Guard(out)
    try:
        with guard:
            plan = read(plan_path)
            prep = plan["preparation_elapsed_seconds"]
            if prep >= 20 or sha(__file__) != plan["source"]["sha256"]:
                raise ValueError("Preparation allowance exhausted or runner source changed")
            signal.setitimer(signal.ITIMER_REAL,20-prep)
            pins = [*plan["inputs"],plan["source"],plan["guard_source"]]
            for item in pins:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("Frozen input differs: "+item["path"])
            result = analyze(read(plan["proposal"]["path"]))
            for item in pins:
                if sha(item["path"]) != item["sha256"]:
                    raise ValueError("Protected input changed: "+item["path"])
            result["execution_plan"] = pin(plan_path)
            result["guard"] = guard.receipt()
            result["aggregate_preparation_execution_seconds"] = prep+result["guard"]["elapsed_seconds"]
            if result["aggregate_preparation_execution_seconds"] > 20 or result["guard"]["peak_rss_bytes"] > 512*1024*1024:
                raise G.BudgetStop("Shared style allowance exceeded")
            result["protected_inputs_unchanged"] = True
            result["counts"] = dict(neural_forwards=0,optimizer_updates=0,native_calls=0,closed_form_ridge_readouts=5,
                                    query_candidate_score_matrices=5,query_rows=5,candidate_rows=22,paid_jobs=0)
            write(out/"result.json",result)
        receipt = dict(schema=SCHEMA,status="completed",source=pin(__file__),plan=pin(plan_path),result=pin(out/"result.json"),
                       guard=guard.receipt(),preparation_elapsed_seconds=prep, neural_forwards=0,optimizer_updates=0,native_calls=0,
                       closed_form_ridge_readouts=5,protected_inputs_unchanged=True)
        receipt["aggregate_preparation_execution_seconds"] = prep+receipt["guard"]["elapsed_seconds"]
        write(out/"receipt.json",receipt)
        print(json.dumps(receipt,indent=2))
    except BaseException as error:
        write(out/"error.json",dict(status="failed",error=repr(error),guard=guard.receipt(),plan=pin(plan_path),source=pin(__file__)))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare",action="store_true"); modes.add_argument("--execute",action="store_true")
    p.add_argument("--proposal",type=Path,default=HERE/"source-style-labels.plan.json")
    p.add_argument("--plan",type=Path,default=ROOT/"experiments/source-style-labels/plan.json")
    p.add_argument("--out",type=Path,default=ROOT/"experiments/source-style-labels/run-1")
    args=p.parse_args()
    if args.prepare: prepare(args.proposal,args.plan)
    else: execute(args.plan,args.out)


if __name__ == "__main__":
    main()
