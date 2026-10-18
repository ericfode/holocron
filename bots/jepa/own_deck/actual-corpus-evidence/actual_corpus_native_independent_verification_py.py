"""Independent saved-data audit. No converter/model import or native execution.

Run with an existing NumPy interpreter; writes one NEW JSON receipt beside this
script. It reads saved arrays/snapshots and performs deterministic arithmetic.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] / "holocron-deck-context"
COLLECTOR = REPO / "bots/jepa/own_deck/actual_corpus_native_collector"
OUT = HERE / "native-independent-verification.json"
NATIVE_COMMIT = "8fb922bf56869c72f828ee8312a449f3891ed406"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    path = Path(path)
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def ready(capture):
    return sum(not card["exhausted"] for card in capture["state"]["players"]["p1"]["resources"])


def settled(capture):
    s = capture["settlement"]
    queues = ("ability_program", "death_depth", "death_pending", "death_window", "pending_programs",
              "pending_triggers", "after_attack_triggers", "after_attack_programs")
    return bool(capture["terminal"] or (s["decision"] == "Window" and all(s[k] == 0 for k in queues)
                and not s["event_group_active"] and not s["support_pending"]))


def walk_kinds(value):
    if isinstance(value, dict):
        if isinstance(value.get("kind"), str):
            yield value["kind"]
        for child in value.values():
            yield from walk_kinds(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_kinds(child)


def main():
    if OUT.exists():
        raise FileExistsError("preserve existing independent receipt")
    raw_path = HERE / "native-attempt-5/native-receipt.json"
    dataset_path = HERE / "actual-corpus.npz"
    manifest_path = HERE / "actual-corpus.manifest.json"
    plan_path = HERE / "native-plan.json"
    source_manifest_path = COLLECTOR / "source-manifest.json"
    ledger_path = HERE / "campaign-ledger.jsonl"
    raw, manifest, plan = read(raw_path), read(manifest_path), read(plan_path)
    source_manifest = read(source_manifest_path)
    with np.load(dataset_path, allow_pickle=False) as pack:
        arrays = {k: pack[k].copy() for k in pack.files}
    checks, mismatches = Counter(), []

    def check(category, condition, **details):
        checks[category] += 1
        if not condition:
            mismatches.append(dict(category=category, **details))

    check("artifact", sha(dataset_path) == manifest["artifact"]["sha256"])
    check("artifact", sha(raw_path) == manifest["native_receipt"]["sha256"])
    check("plan", raw["collectionPlan"] == plan == manifest["plan"])
    check("plan", raw["collectionPlanSha256"] == sha(plan_path))
    check("source", raw["sourceRevision"] == "c7ee39554901278cee70f61fd8b26fb1920696b3")
    for key in ("project_files", "pinned_execution_inputs"):
        for item in source_manifest[key]:
            p = Path(item["path"])
            p = p if p.is_absolute() else COLLECTOR / p
            check("source_pins", sha(p) == item["sha256"] and p.stat().st_size == item["bytes"], path=str(p))
    raw_by = {(r["card"], r["state_family"]): r for r in raw["cases"]}
    check("roots", len(raw_by) == len(raw["cases"]) == 32)
    check("roots", {(str(c), int(s)) for c, s in zip(arrays["source_cards"], arrays["state_families"])} == set(raw_by))
    check("roots", manifest["records"] == sorted(raw["cases"], key=lambda r: (r["state_family"], r["card"])))
    for key, value in arrays.items():
        if value.dtype.kind == "f":
            check("array_finite", bool(np.isfinite(value).all()), array=key)
        if key.endswith("mask"):
            check("mask_domain", bool(np.isin(value, [0, 1]).all()), array=key)
    captures, root_rows, aliases = [], [], 0
    for i, (code, family) in enumerate(zip(arrays["source_cards"], arrays["state_families"])):
        code, family = str(code), int(family)
        case = raw_by[code, family]
        before, final, refs = case["before"], case.get("final"), case["refs"]
        source, sm = arrays["source_targets"][i], arrays["source_mask"][i]
        target, tm = arrays["targets"][i], arrays["target_mask"][i]
        detail = dict(code=code, state_family=family)
        captures.append(before)
        for witness in case["attachmentTargetWitnesses"]:
            q = witness["publicTargetQuery"]
            captures.append(q)
            check("attachment", q["decision"] == "UpgradeTarget" and q["sourceInstance"] == witness["upgrade"]
                  and witness["offeredHost"] in q["offeredActions"] and witness["offeredHost"]["card"] == witness["host"], **detail)
        last = before
        for step in case["steps"]:
            captures.extend((step["before"], step["after"]))
            check("action_chain", step["before"] == last and step["action"] in last["offeredActions"], **detail)
            last = step["after"]
        if "lastObserved" in case:
            aliases += 1
            check("last_observed_alias", case["lastObserved"] == last, **detail)
        chosen = manifest["candidate_order"].index(case["chosen_ref"])
        check("intent", int(arrays["selected_candidate_indices"][i]) == chosen, **detail)
        available = any(a.get("kind") == "card" and a.get("card") == refs["source"] for a in before["offeredActions"])
        check("source_labels", source[0] == available and sm[0] == 1 and available == (case.get("playAction") is not None), **detail)
        if final:
            captures.append(final)
            check("settled_endpoint", final == last and settled(final) and case["engineError"] is None, **detail)
            a, z = before["projections"]["source"], final["projections"]["source"]
            expected = [float(z["zone"] != "hand" and (z["in_arena"] or z["zone"] == "discard")),
                        ready(before) - ready(final), float(z["in_arena"]), float(z["zone"] == "discard"),
                        float(z["zone"] == "hand"), z["damage"] - a["damage"], z["shield_count"] - a["shield_count"], float(z["exhausted"])]
            mask = [1] * 5 + [int(a["known"][k] and z["known"][k]) for k in ("damage", "shield_count", "exhausted")]
            check("source_labels", np.array_equal(source[1:], expected), **detail)
            check("source_masks", np.array_equal(sm[1:], mask), **detail)
        else:
            check("unknown_source_future", not bool(np.any(sm[1:])), **detail)
        prompt = case.get("targetPrompt")
        if prompt:
            captures.append(prompt)
            check("target_prompt_witness", prompt["decision"] == "AbilityTarget" and any(s["after"] == prompt for s in case["steps"]), **detail)
            offered = [a["card"] for a in prompt["offeredActions"] if a.get("kind") == "card"]
            for k, slot in enumerate(manifest["candidate_order"]):
                check("target_offer_labels", target[k, 0] == float(refs[slot] in offered) and tm[k, 0] == 1, slot=slot, **detail)
        else:
            check("unknown_target_offer", not bool(np.any(tm[:, 0])), **detail)
        commits = [s for s in case["steps"] if s["stage"] == "chosen-target"]
        check("chosen_commit_count", len(commits) <= 1, **detail)
        if commits:
            check("chosen_commit_binding", commits[0]["before"] == prompt and commits[0]["action"]["card"] == refs[case["chosen_ref"]]
                  and commits[0]["action"] == case["targetAction"], **detail)
        if final and commits:
            a, z = before["projections"][case["chosen_ref"]], final["projections"][case["chosen_ref"]]
            removed = float(not z["present"] or z["zone"] in ("discard", "absent"))
            check("target_removal_label", tm[chosen, 1] == 1 and target[chosen, 1] == removed, **detail)
            for k, field in enumerate(("damage", "exhausted", "shield_count", "power", "hp"), 2):
                known = a["present"] and z["present"] and a["zone"] == z["zone"] and a["known"][field] and z["known"][field]
                check("target_delta_masks", tm[chosen, k] == int(known), field=field, **detail)
                if known:
                    check("target_delta_labels", target[chosen, k] == float(z[field]) - float(a[field]), field=field, **detail)
        else:
            check("unknown_target_future", not bool(np.any(tm[:, 1:])), **detail)
        check("unselected_target_future", all(not np.any(tm[k, 1:]) for k in range(8) if k != chosen), **detail)
        root_rows.append(dict(**detail, completion=case["completion"], source_values=source.tolist(), source_mask=sm.tolist(),
                              chosen_ref=case["chosen_ref"], selected_target_values=target[chosen].tolist(), selected_target_mask=tm[chosen].tolist(),
                              stages=[s["stage"] for s in case["steps"]]))
    for c in captures:
        check("privacy", all(not c["state"]["players"][seat]["deck"] for seat in ("p1", "p2")) and not c["state"]["players"]["p2"]["hand"])
        check("settlement_witness", c["settled"] == settled(c))
        units = c["state"]["players"]["p1"]["ground"] + c["state"]["players"]["p1"]["space"]
        other = [u for u in units if u["id"] != c["projections"]["source"]["id"]]
        fighters = sum("fighter" in plan["selected_whole_rows"][u["setCode"]]["card"]["traits"] for u in other)
        check("printed_trait_scope", c["other_friendly_fighter_count"] == fighters)
        check("printed_trait_scope", c["other_friendly_space_count"] == sum(u["id"] != c["projections"]["source"]["id"] for u in c["state"]["players"]["p1"]["space"]))
    mutations = sorted({kind for row in plan["selected_whole_rows"].values() for kind in walk_kinds(row) if "trait" in kind.lower()})
    check("printed_trait_scope", not mutations)
    support = {}
    for part in ("train", "program-held", "state-held", "joint"):
        ix = np.flatnonzero(arrays["partition"] == part)
        support[part] = {}
        for names, key, mask_key in ((manifest["source_head_names"], "source_targets", "source_mask"), (manifest["target_names"], "targets", "target_mask")):
            for j, name in enumerate(names):
                y, mask = arrays[key][ix, ..., j], arrays[mask_key][ix, ..., j]
                values = y[mask > 0]
                entry = dict(known=int(values.size), values=np.unique(values).tolist(), positive=int((values == 1).sum()), negative=int((values == 0).sum()))
                support[part][name] = entry
                saved = manifest["head_support"][part][name]
                check("head_support", entry["known"] == saved["known"] and entry["values"] == saved["values"], partition=part, head=name)
    journal_path = HERE / "native-attempt-5/native-transitions.jsonl"
    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    actions = [r for r in journal if r.get("phase") == "beforeApply"]
    check("durable_journal", [r["applyCall"] for r in actions] == list(range(1, 39)))
    check("durable_journal", len(actions) == raw["applyCalls"] == sum(r["applyCalls"] for r in raw["cases"]))
    tally = dict(Counter(r["branch"] for r in actions))
    check("durable_journal", tally == {"play-own-hand": 24, "chosen-target": 12, "decline-unoffered-target": 2})
    ledger_lines = ledger_path.read_bytes().splitlines(keepends=True)
    native_prefix = b"".join(ledger_lines[:10])
    native_events = [json.loads(line) for line in ledger_lines[:10]]
    native_finishes = [r for r in native_events if r["event"] == "stage-finish"]
    check("native_ledger", len(native_finishes) == 5 and all(r["phase"] == "native" for r in native_events))
    for start, finish in zip(native_events[::2], native_events[1::2]):
        check("native_ledger", start["event"] == "stage-start" and finish["event"] == "stage-finish" and start["stage_id"] == finish["stage_id"])
    attempts = []
    for i, finished in enumerate(native_finishes, 1):
        path = HERE / f"native-attempt-{i}/supervisor-receipt.json"
        r = read(path)
        check("native_ledger", r["status"] == finished["status"] and r["engine_apply_attempts"] == finished["engine_apply_attempts"])
        check("native_ledger", finished["completed_or_reserved_updates"] == finished["neural_forwards"] == 0)
        if i == 5:
            check("source", r["source_manifest_sha256"] == sha(source_manifest_path))
        else:
            preserved = source_manifest["preserved_failed_attempts"][i - 1]
            check("preserved_failure", preserved["receipt"]["sha256"] == sha(path) and preserved["ledger_active_seconds"] == finished["active_seconds"])
        attempts.append(dict(attempt=i, receipt=pin(path), status=r["status"], canonical_active_seconds=finished["active_seconds"],
                             receipt_elapsed_seconds=r["elapsed_seconds"], native_applies=finished["engine_apply_attempts"],
                             recorded_memory_bound_bytes=r["observed_conservative_peak_sum_bytes"]))
    check("native_ledger", [r["status"] for r in attempts] == ["failed"] * 4 + ["completed"])
    check("native_ledger", sum(r["native_applies"] for r in attempts) == 38)
    per_card = {}
    for code in [r["code"] for r in plan["cards"]]:
        ix = np.flatnonzero(arrays["source_cards"] == code)
        paid = [int(i) for i in ix if arrays["source_mask"][i, 1] and arrays["source_targets"][i, 1] == 1 and arrays["source_targets"][i, 2] > 0]
        per_card[code] = dict(roots=len(ix), paid_settled_plays=len(paid), paid_root_indices=paid)
        check("per_card_observation", len(paid) >= 2, code=code)
    paths = [raw_path, dataset_path, manifest_path, plan_path, source_manifest_path, COLLECTOR / "src/main.rs", COLLECTOR / "supervise.py", journal_path]
    report = dict(schema="actual-corpus-independent-native-verification/1", created_utc=datetime.now(timezone.utc).isoformat(),
                  status="passed" if not mismatches else "failed", source_commit=NATIVE_COMMIT, script=pin(__file__), inputs=[pin(p) for p in paths],
                  method="Independent raw snapshot/offer arithmetic; no converter/model import, no native calls or neural forwards.",
                  check_counts=dict(checks), mismatch_count=len(mismatches), mismatches=mismatches,
                  capture_occurrences_checked=len(captures), last_observed_aliases_verified=aliases,
                  total_snapshot_occurrences_covered=len(captures) + aliases, terminal_capture_occurrences=sum(c["terminal"] for c in captures),
                  root_completion_counts=dict(Counter(r["completion"] for r in raw["cases"])), root_count=len(raw_by),
                  native_error_roots=sum(r["engineError"] is not None for r in raw["cases"]), pending_roots=manifest["pending_roots"],
                  native_apply_count=len(actions), native_action_tally=tally, per_card=per_card, root_checks=root_rows, head_support=support,
                  printed_trait_scope=dict(selected_complete_rows=len(plan["selected_whole_rows"]), trait_mutating_kinds_found=mutations,
                      lookup="Actual current arena definition code -> pinned public full-row card.traits; source excluded.",
                      limitation="Valid for these unchanged-trait fixtures; printed traits are not assumed current for arbitrary trait-changing games."),
                  support_limits=dict(train_zero_known_heads=[n for n, v in support["train"].items() if v["known"] == 0],
                      train_constant_heads=[n for n, v in support["train"].items() if v["known"] > 0 and len(v["values"]) == 1],
                      positive_exhaust_delta="One joint-held coordinate; this output has no supervised training labels.",
                      qualification="Eight actual cards/65 declared copies and selected play paths, not all115 admitted IDs, all card abilities, gameplay strength or semantic validation."),
                  attempts=attempts, failed_attempt_count=4, native_ledger_prefix=dict(sha256=hashlib.sha256(native_prefix).hexdigest(), bytes=len(native_prefix),
                      canonical_active_seconds=sum(r["canonical_active_seconds"] for r in attempts), native_applies=38, optimizer_updates=0, neural_forwards=0),
                  resource_limit_caveat="The genuine attempt2 over-limit sample remains preserved; successful-attempt RSS is not an all-attempt cap pass.",
                  audit_execution=dict(native_calls=0, neural_forwards=0, optimizer_updates=0, paid_jobs=0))
    with OUT.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps(dict(path=str(OUT), sha256=sha(OUT), status=report["status"], mismatch_count=len(mismatches), captures=len(captures))))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
