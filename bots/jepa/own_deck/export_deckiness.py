"""Export frozen authored-vs-constructed scores and unannotated review pairs.

No fit, game, native engine call, paid job, hidden state, or quality label is
created. The two saved 200-update heads retain their exact train normalization.
Two single-batch encoder forwards cover sources and both reference populations.
"""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from collections import Counter
import copy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote

import numpy as np

HERE = Path(__file__).resolve().parent
JEPA = HERE.parent
REPO = JEPA.parents[1]
ROOT = REPO.parent
sys.path.insert(0, str(HERE))
import real_deck_data as R
import restoration_data as F
import restoration_probe as P
import run_local_experiments as G
from run_events import RunEvents

SEED = 1729
METRIC_DISPLAY_NAME = "Deck coherence (exploratory authored-vs-corrupted classifier)"
LIMITATIONS = [
    "Exploratory authored-versus-constructed classifier output, not calibrated deck coherence, synergy, legality, win probability or strength.",
    "Saved heads were weak on three held-out families: full accuracy 0.4167 and printed-only accuracy 0.5. No aggregate restoration gain was established.",
    "The frozen encoder uses printed metadata and hashed identity; it has no learned effect-program or transition objective in this score space.",
    "Existing matched references include training and validation fixtures. These illustrative scores are not a new held-out evaluation or independent observations.",
    "Unrestricted references are generated without admission rejection or cost/type/arena/aspect matching; passing the pinned validator by chance does not change their population.",
    "Admission is only the saved conservative Premier declaration policy for the reviewed source-bank card universe and explicitly empty sideboards; no current rules recheck or gameplay certification.",
    "Review pairs reuse a different original-composition-trained embedding space. Its cosine is unvalidated for behavioral or strategic similarity; review annotations are absent.",
    "No dynamic remaining draw pile or hidden draw order is inferred or scored.",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def pinned(path, expected=None):
    value = sha(path)
    if expected is not None and value != expected:
        raise ValueError(f"protected artifact changed: {path}")
    return dict(path=str(Path(path).resolve()), sha256=value)


def fixture_url(name):
    # Importer preserves source .txt stems; personal event/decklist links were
    # intentionally removed. Link only the credited pinned repository fixture.
    return ("https://github.com/TCG-Engine/TCGEngine/blob/" + R.UPSTREAM_DECK_COMMIT
            + "/SWUSim/Tests/BotFixtures/ash-meta-2026-09/" + quote(name, safe="") + ".txt")


def deck_record(deck, aliases):
    raw = Counter()
    for entry in deck["deck"]:
        code = P.O.normalized_code(entry["id"])
        if code not in aliases or type(entry["count"]) is not int or entry["count"] <= 0:
            raise ValueError("ambiguous or invalid declared card")
        raw[code] += entry["count"]
    canonical, printings = Counter(), {}
    for code, count in sorted(raw.items()):
        canonical[aliases[code]] += count
        printings.setdefault(aliases[code], []).append(code)
    return dict(leader=deck["leader"], base=deck["base"], sideboard=[],
                raw_declared_cards=[dict(id=k, count=v) for k, v in sorted(raw.items())],
                canonical_card_counts=dict(sorted(canonical.items())),
                printed_ids_by_canonical=dict(sorted(printings.items())),
                total_count=sum(canonical.values()), composition_fingerprint=R.fingerprint(canonical))


def prepare():
    summary_path = HERE / "restoration-results.json"
    summary = read(summary_path)
    result_pin = pinned(summary["result_path"], summary["result_sha256"])
    result = read(result_pin["path"])
    if result["status"] != "completed" or result["updates_completed"] != 400 or not result["frozen_checkpoints_unchanged"]:
        raise ValueError("expected the completed saved two-head probe")
    base = pinned(JEPA / "models/tx-t10.safetensors", summary["dataset"]["base_checkpoint_sha256"])
    init = pinned(JEPA / "wasm/generated-own-deck/deck-init.safetensors", summary["dataset"]["engineering_initialization_sha256"])
    heads = {arm: pinned(value["checkpoint"]["path"], value["checkpoint"]["sha256"])
             for arm, value in summary["arms"].items()}
    if set(heads) != set(P.ARMS) or any(result["arms"][arm]["updates"] != 200 for arm in heads):
        raise ValueError("expected exactly the original fixed-final 200-update heads")
    for relative, expected in summary["dataset"]["source_sha256"].items():
        if relative in ("own_deck/restoration_probe.py", "own_deck_model.py", "own_deck.py", "tx_model.py"):
            pinned(JEPA / relative, expected)
    dataset = pinned(summary["dataset"]["npz_path"], summary["dataset"]["npz_sha256"])
    manifest_pin = pinned(summary["dataset"]["manifest_path"], summary["dataset"]["manifest_sha256"])
    manifest = read(manifest_pin["path"])
    for source in manifest["sources"]:
        pinned(source["path"], source["sha256"])
    source_pin = next(s for s in manifest["sources"] if Path(s["path"]).name == "ash-meta-2026-09.json")
    catalog_pin = next(s for s in manifest["sources"] if s["path"].endswith("/compiler/generated/cards.json"))
    bank_pin = next(s for s in manifest["sources"] if Path(s["path"]).name == "real-decks.manifest.json")
    policy_pin = next(s for s in manifest["sources"] if Path(s["path"]).name == "admission-policy.json")
    decks, catalog, bank, policy = map(lambda s: read(s["path"]), (source_pin, catalog_pin, bank_pin, policy_pin))
    cards, _ = R.printed_catalog(catalog)
    aliases, _ = R.catalog_index(cards)
    printings = F.raw_printings(catalog)
    declaration_by_source = {d["source_index"]: d for d in bank["declarations"]}
    train_sources = set(manifest["inherited_split"]["source_train_indices"])
    fit_fingerprints = {}
    for record in manifest["fit_records"]:
        fit_fingerprints.setdefault((record["source_idx"], record["fingerprint"]), []).append(record["variant_id"])
    fit_sources = {r["source_idx"] for r in manifest["fit_records"]}
    rows, declarations = [], []

    def append(deck, identity, kind, source_index, generator=None, fixture=None):
        source = decks[source_index]
        split = "train" if source_index in train_sources else "validation"
        info = deck_record(deck, aliases)
        record = dict(id=identity, name=(source.get("metadata") or {}).get("name", identity), kind=kind,
                      source_index=source_index, source_deck_id=f"deck-source-{source_index:02}",
                      source_urls=[fixture_url(source["metadata"]["name"])],
                      source_url_scope="Pinned upstream .txt fixture from the documented importer filename contract; personal event links were removed.",
                      family_id=declaration_by_source[source_index]["family_id"], inherited_source_split=split,
                      probe_training_relation="train lineage" if source_index in train_sources and source_index in fit_sources else
                          "held-out lineage" if source_index in fit_sources else "excluded from saved probe fit/validation",
                      admission=F.eligibility(deck, printings, policy), **info)
        record["seen_fit_variant_ids"] = fit_fingerprints.get((source_index, info["composition_fingerprint"]), [])
        if generator is not None:
            record["generator"] = generator
        if fixture is not None:
            record["saved_fixture"] = fixture
        rows.append(record)
        declarations.append(deck)

    for i, original in enumerate(decks):
        append(F.changed_deck(original, [], []), f"deck-source-{i:02}", "source-authored", i)
    candidates = [r for r in manifest["fit_records"] if r["kind"] == "matched-constructed-record"]
    # Sample fixture identities without replacement, before looking at scores.
    candidates.sort(key=lambda r: r["variant_id"])
    rng = np.random.default_rng(SEED)
    selected = sorted(rng.choice(len(candidates), 12, replace=False).tolist())
    for j, index in enumerate(selected):
        candidate = candidates[index]
        source_index = candidate["source_idx"]
        deck = copy.deepcopy(decks[source_index])
        deck.update(deck=candidate["main_multiset"], sideboard=[])
        append(deck, f"matched-reference-{j:02}", "pinned-policy-valid-matched-reference", source_index,
               generator=dict(seed=SEED, algorithm="NumPy PCG64 choice, without replacement, sorted saved negative variant IDs",
                              candidate_count=len(candidates), selected_candidate_index=index),
               fixture={k: candidate[k] for k in ("variant_id", "group_id", "kind", "partition", "fingerprint")})
        if not rows[-1]["admission"]["admitted"] or rows[-1]["composition_fingerprint"] != candidate["fingerprint"]:
            raise ValueError("saved matched reference failed exact admission/fingerprint reproduction")
    # Deliberately unfiltered: draws are uniform independent copies from the
    # reviewed source bank, preserving only anchor leader/base and main size.
    pool = sorted({entry["id"] for d in decks for entry in d["deck"]})
    random_rng = np.random.default_rng(SEED + 1)
    for j, matched in enumerate(rows[27:39]):
        source_index = matched["source_index"]
        anchor = decks[source_index]
        count = sum(entry["count"] for entry in anchor["deck"])
        choices = random_rng.choice(pool, count, replace=True).tolist()
        deck = F.changed_deck(anchor, [], [])
        deck["deck"] = [dict(id=k, count=v) for k, v in sorted(Counter(choices).items())]
        append(deck, f"unrestricted-reference-{j:02}", "unrestricted-random-reference", source_index,
               generator=dict(seed=SEED + 1, algorithm="NumPy PCG64 sequential uniform independent copy draws with replacement; no rejection",
                              sample_index=j, pool_printed_ids=pool, pool_count=len(pool), draws=count,
                              constraints="Anchor leader/base and main size only; no metadata matching, canonical copy cap or admission filter"))
    features = np.stack([P.O.as_array(P.O.encode_hello({"deck": d, "cards": cards}))[0] for d in declarations])
    if features.shape != (51, 2, 207) or not np.all(features[:, 0, 3] == 1):
        raise ValueError("expected 51 complete own-deck declarations")
    if not np.array_equal(features[:, 1], P.O.neutral_features(len(rows))[:, 1]):
        raise ValueError("remaining composition must be explicitly unknown")
    provenance = dict(training_commit=summary["commit"], training_result=result_pin, summary=pinned(summary_path),
                      base=base, engineering_initialization=init, heads=heads, dataset=dataset, manifest=manifest_pin,
                      policy=policy_pin, source_decks=source_pin, catalog=catalog_pin, inherited_bank=bank_pin,
                      score_normalization="For each head: mask explicit size4,5,6,49; normalize each identity factor mass; printed-only additionally masks identity50:207; encode zero public context; use saved train_mean/train_scale; sigmoid(zscore @ weight + bias)",
                      balanced_training_prior="0.5 authored / 0.5 constructed; not quality calibration", split=manifest["inherited_split"],
                      saved_validation={arm: summary["arms"][arm]["validation"]["final"] for arm in P.ARMS})
    protected = {item["path"]: item["sha256"] for item in (base, init, *heads.values(), result_pin, dataset, manifest_pin, policy_pin)}
    return rows, features, provenance, protected, result


def _worker(messages, acknowledged, features, provenance, started):
    writer = G.WorkerEvents(messages)
    calls = 0
    def check():
        writer.report_rss()
        if time.monotonic() - started > 20 or G.peak_rss_mib() > 2048:
            raise RuntimeError("frozen export resource cap")
    try:
        check()
        weights, metadata = P.D.load_extended(provenance["base"]["path"], provenance["engineering_initialization"]["path"])
        model = P.D.NumpyOwnDeckTx(weights, metadata)
        scored = {}
        for arm in P.ARMS:
            check()
            contexts = P.context_without_size(features, printed_only=arm == P.ARMS[1])
            n = len(contexts)
            z = model.encode(np.zeros((n, 73), np.float32), np.zeros((n, 24), np.int64),
                             np.zeros((n, 24, 21), np.float32), np.zeros((n, 24), np.float32), own_deck=contexts)
            calls += 1
            with np.load(provenance["heads"][arm]["path"], allow_pickle=False) as head:
                values = {k: head[k].copy() for k in head.files}
            if set(values) != {"weight", "bias", "train_mean", "train_scale"} or any(not np.isfinite(v).all() for v in values.values()):
                raise ValueError("invalid saved logistic head")
            if values["weight"].shape != (96,) or values["train_scale"].shape != (96,) or not np.all(values["train_scale"] >= 1e-6):
                raise ValueError("invalid saved training normalization")
            x = (z.astype(np.float64) - values["train_mean"]) / values["train_scale"]
            scores = P.sigmoid(x @ values["weight"] + values["bias"])
            if scores.shape != (n,) or not np.isfinite(scores).all():
                raise ValueError("nonfinite frozen scores")
            scored[arm] = scores.tolist()
            writer.emit("status", "frozen_scoring", 0, status="running", metrics=dict(model_forward_calls=calls, scored_rows=n), arm=arm)
            check()
        messages.put(("result", dict(scores=scored, model_forward_calls=calls, rows_per_forward=len(features),
                                    elapsed_seconds=time.monotonic() - started, optimizer_updates=0, native_calls=0, paid_jobs=0)))
        if not acknowledged.wait(timeout=3):
            raise RuntimeError("supervisor did not acknowledge export")
    except BaseException as exc:
        messages.put(("failure", dict(reason=str(exc), type=type(exc).__name__, step=0, model_forward_calls=calls)))
        acknowledged.wait(timeout=3)


def review_pairs(rows):
    embeddings_path = ROOT / "experiments/embedding-export/deck-embeddings.json"
    embedding_manifest_path = embeddings_path.with_name("deck-embeddings.manifest.json")
    manifest = read(embedding_manifest_path)
    pin = pinned(embeddings_path, manifest["artifact"]["sha256"])
    bank = read(embeddings_path)
    if len(bank["rows"]) != 27 or bank["dimension"] != 96:
        raise ValueError("expected the actual saved 27-deck composition latent bank")
    entities = {r["id"]: r for r in rows if r["kind"] == "source-authored"}
    embeddings = {r["id"]: r for r in bank["rows"]}
    if set(entities) != set(embeddings):
        raise ValueError("review entity IDs differ from embedding bank")
    pairs = []
    for i, a in enumerate(sorted(entities)):
        for b in sorted(entities)[i + 1:]:
            ca, cb = entities[a]["canonical_card_counts"], entities[b]["canonical_card_counts"]
            if ca != embeddings[a]["canonical_card_counts"] or cb != embeddings[b]["canonical_card_counts"]:
                raise ValueError("embedding/source canonical count mismatch")
            x, y = (np.asarray(embeddings[k]["vector"], np.float64) for k in (a, b))
            nx, ny = np.linalg.norm(x), np.linalg.norm(y)
            if min(nx, ny) <= 1e-12:
                raise ValueError("zero-norm candidate cosine is undefined")
            shared = sum(min(ca.get(k, 0), cb.get(k, 0)) for k in set(ca) | set(cb))
            union = sum(max(ca.get(k, 0), cb.get(k, 0)) for k in set(ca) | set(cb))
            cosine = float(np.clip(x @ y / (nx * ny), -1., 1.))
            pairs.append(dict(id=a + "--" + b, a=a, b=b, cosine_similarity=cosine, cosine_distance=1. - cosine,
                              euclidean_raw=float(np.linalg.norm(x-y)), euclidean_unit=float(np.linalg.norm(x/nx-y/ny)),
                              shared_copies=shared, weighted_jaccard=shared/union,
                              overlap_smaller=shared/min(sum(ca.values()), sum(cb.values())), selection_methods=[], annotations=[]))
    for identity in sorted(entities):
        candidates = [p for p in pairs if identity in (p["a"], p["b"])]
        nearest = min(candidates, key=lambda p: (-p["cosine_similarity"], p["id"]))
        nearest["selection_methods"].append("nearest-cosine-for:" + identity)
        low = [p for p in candidates if p["overlap_smaller"] <= .25]
        if low:
            best = min(low, key=lambda p: (-p["cosine_similarity"], p["shared_copies"], p["id"]))
            best["selection_methods"].append("nearest-cosine-with-overlap-smaller-at-most-0.25-for:" + identity)
    return dict(schema="jepa-deck-review-candidates/1", semantic_validated=False, annotations_created=False,
                embedding_artifact=pin, embedding_manifest=pinned(embedding_manifest_path), space_id=bank["space_id"],
                metric="Cosine from raw vectors divided by their L2 norms, no whitening; count overlap is canonical main copies only.",
                selection="For each source, nearest cosine and nearest cosine subject to overlap_smaller<=0.25; deduplicated unordered pairs. No score or human-result selection.",
                pair_count=len(pairs), selected_pair_count=sum(bool(p["selection_methods"]) for p in pairs),
                entities=[entities[k] for k in sorted(entities)], pairs=pairs,
                limitations=["The selected pairs are mechanically selected candidates, not annotations or verified similar strategies.",
                             "The score probe and the composition embedding bank have different supplements/objectives; scores do not explain these distances.",
                             "No independent reviewer assessment, game evidence or unseen-card similarity validation is included."])


def reproduction(rows, raw_result):
    errors = {}
    for arm in P.ARMS:
        own = []
        for group in raw_result["arms"][arm]["curves"]["groups"].values():
            points = group["points"]
            endpoint = max((p for p in points if p["kind"] == "true-restoration"), key=lambda p: p["restored_copies"])
            source = next(r for r in rows if r["id"] == f"deck-source-{group['source_idx']:02}")
            own.append(abs(source["scores"][arm] - endpoint["score"]))
        errors[arm] = dict(saved_endpoint_comparisons=len(own), max_absolute_error=max(own))
        if max(own) > 1e-6:
            raise ValueError("export did not reproduce saved held-out endpoint scores")
    return errors


def run(out):
    started = time.monotonic()
    out = Path(out).resolve()
    if (out / "index.json").exists():
        raise ValueError("refuse to overwrite an existing export; no automatic second forward")
    out.mkdir(parents=True, exist_ok=True)
    rows, features, provenance, protected, raw_result = prepare()
    config = dict(seed=SEED, source_rows=27, matched_reference_rows=12, unrestricted_reference_rows=12,
                  max_forward_calls=3, planned_forward_calls=2, max_seconds=20, cpu_threads=1, max_rss_mib=2048,
                  optimizer_updates=0, native_calls=0, paid_jobs=0, resampling_or_score_selection=False)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    source = pinned(__file__)
    write(out / "preflight.json", dict(schema="jepa-deckiness-preflight/1", commit=commit, source=source, config=config,
                                      provenance=provenance, limitations=LIMITATIONS, protected_before=protected))
    writer = RunEvents(out / "run-events.jsonl", "deckiness-export-s1729", commit, config, provenance, LIMITATIONS)
    writer.emit("status", "frozen_scoring", 0, status="running")
    try:
        measured = G.supervise_worker(_worker, (features, provenance, started), writer, 20., started, 20., 2048.)
        for i, row in enumerate(rows):
            row["scores"] = {arm: measured["scores"][arm][i] for arm in P.ARMS}
        checks = reproduction(rows, raw_result)
        if measured["model_forward_calls"] != 2:
            raise ValueError("unexpected forward count")
        after = {p: sha(p) for p in protected}
        if after != protected:
            raise ValueError("protected frozen artifact changed")
        scores = dict(schema="jepa-deckiness-scores/1", created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      score_name="Exploratory authored-vs-constructed score", calibrated=False, quality_or_strength_validated=False,
                      metric_display_name=METRIC_DISPLAY_NAME,
                      rows=rows, provenance=provenance, population_counts=dict(source_authored=27, matched_reference=12, unrestricted_random=12),
                      normalization=provenance["score_normalization"], limitations=LIMITATIONS)
        write(out / "deckiness-scores.json", scores)
        pairs = review_pairs(rows)
        write(out / "review-candidates.json", pairs)
        selected = dict(pairs)
        selected["pairs"] = [p for p in pairs["pairs"] if p["selection_methods"]]
        selected["pair_count"] = len(selected["pairs"])
        write(out / "review-pairs.json", selected)
        receipt = dict(schema="jepa-deckiness-export-receipt/1", status="completed", commit=commit, source=source, config=config,
                       metric_display_name=METRIC_DISPLAY_NAME,
                       provenance=provenance, protected_before=protected, protected_after=after, protected_unchanged=True,
                       **{k: v for k, v in measured.items() if k != "scores"},
                       completed_elapsed_seconds=time.monotonic()-started, saved_score_reproduction=checks,
                       admission_counts={kind: dict(total=sum(r["kind"] == kind for r in rows),
                                                   admitted=sum(r["kind"] == kind and r["admission"]["admitted"] for r in rows))
                                         for kind in sorted(set(r["kind"] for r in rows))},
                       artifacts={name: pinned(out / name) for name in ("deckiness-scores.json", "review-candidates.json", "review-pairs.json")},
                       limitations=LIMITATIONS)
        write(out / "receipt.json", receipt)
        write(out / "index.json", dict(schema="jepa-deckiness-export-index/1", status="available", score_name=scores["score_name"],
                                       metric_display_name=METRIC_DISPLAY_NAME,
                                       scores=receipt["artifacts"]["deckiness-scores.json"], candidates=receipt["artifacts"]["review-candidates.json"],
                                       review_pairs=receipt["artifacts"]["review-pairs.json"], receipt=pinned(out / "receipt.json"),
                                       population_counts=scores["population_counts"], head_ids=list(P.ARMS), semantic_validated=False,
                                       quality_or_strength_validated=False, limitations=LIMITATIONS))
        writer.emit("artifact", "completed", 0, status="completed", metrics=dict(model_forward_calls=2, scored_rows=len(rows),
                    matched_reference_rows=12, unrestricted_reference_rows=12, optimizer_updates=0, paid_spend_usd=0),
                    artifacts=dict(index=str(out / "index.json"), receipt=str(out / "receipt.json")))
        return receipt
    except BaseException as exc:
        write(out / "error.json", dict(status="failed", error=str(exc), guard=getattr(exc, "guard", None),
                                       protected_before=protected, protected_after={p: sha(p) for p in protected}))
        writer.emit("error", "aborted", 0, status="failed", reason=str(exc))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "experiments/deckiness-export")
    args = parser.parse_args()
    receipt = run(args.out)
    print(json.dumps({k: receipt[k] for k in ("status", "model_forward_calls", "rows_per_forward", "completed_elapsed_seconds", "guard", "artifacts")}, indent=2))
