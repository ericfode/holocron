"""Pure saved native receipt -> masked arrays. Never runs an engine or learner.

Synthetic unit-test receipts exercise this converter, not card conformance.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import actual_corpus_native_plan as A
import grounded_contrast_data as G
import native_effect_v2 as P

MODES = {"chosen-target", "upgrade-attachment", "self-entry", "passive-area-anchor"}
DELTAS = ("damage", "exhausted", "shield_count", "power", "hp")


def query(plan, code, family):
    specs = plan["query_specs"][code]
    return specs[family] if isinstance(specs, list) else specs[str(family)]


def units(capture, seat=None):
    return [(s, u) for s in ((seat,) if seat else ("p1", "p2"))
            for zone in ("ground", "space") for u in capture["state"]["players"][s][zone]]


def attachments(capture):
    return [(seat, host, upgrade) for seat, host in units(capture) for upgrade in host.get("upgrades", [])]


def validate_capture(capture, refs):
    settled = G.settled_capture(capture)
    if capture["terminal"]:
        raise ValueError("unreviewed terminal/death continuation in this nonterminal cohort")
    if set(capture["projections"]) != set(P.CANDIDATES):
        raise ValueError("candidate projection bank differs")
    if len(set(refs.values())) != 8:
        raise ValueError("candidate instance identities must be distinct")
    for slot, projection in capture["projections"].items():
        if projection["id"] != refs[slot]:
            raise ValueError("stable candidate identity differs")
        for value in projection["known"].values():
            G.boolean(value)
        for field in ("present", "in_arena", "attackable", "is_unit", "is_base", "exhausted"):
            G.boolean(projection[field])
        for field in ("damage", "hp", "power", "shield_count", "xp_count"):
            G.scalar(projection[field])
    for seat in ("p1", "p2"):
        player = capture["state"]["players"][seat]
        if player["deck"] or seat == "p2" and player["hand"]:
            raise ValueError("private opponent hand or hidden deck input")
    token_ids = []
    for _, host in units(capture):
        shields = [u for u in host.get("upgrades", []) if u.get("setCode") == "TOKEN_SHIELD"]
        for token in shields:
            if token.get("token") is not True or token.get("parent", host["id"]) != host["id"]:
                raise ValueError("Shield lacks actual physical token/parent link")
            token_ids.append(token["id"])
        for projection in capture["projections"].values():
            if projection["id"] == host["id"] and projection["known"]["shield_count"]:
                if projection["shield_count"] != len(shields):
                    raise ValueError("native Shield count differs from physical links")
    if len(token_ids) != len(set(token_ids)):
        raise ValueError("Shield token appears on multiple hosts")
    return settled


def validate_setup(case, context, plan):
    before, refs = case["before"], case["refs"]
    if not validate_capture(before, refs) or before["decision"] != "Window" or case.get("publicSnapshotRoundtripExact") is not True:
        raise ValueError("root must be settled and snapshot/load exact")
    if G.ready_resources(before) != context["ready_resources"] or len(before["state"]["players"]["p1"]["resources"]) != 12:
        raise ValueError("public resources differ from planned world")
    source = before["projections"]["source"]
    if (source["zone"], source["code"], source["owner"]) != ("hand", case["card"], "p1"):
        raise ValueError("source must be exact own hand card")
    own = before["state"]["players"]["p1"]
    if not any(c["id"] == refs["source"] and c["setCode"] == case["card"] for c in own["hand"]):
        raise ValueError("source projection lacks actual own-hand instance")
    other_units = [u for _, u in units(before, "p1") if u["id"] != refs["source"]]
    fighter_count = sum("fighter" in plan["selected_whole_rows"][u["setCode"]]["card"]["traits"] for u in other_units)
    if before["other_friendly_fighter_count"] != fighter_count or before["other_friendly_space_count"] != sum(u["id"] != refs["source"] for u in own["space"]):
        raise ValueError("public context counts differ from actual own arena membership")
    witnesses = case["attachmentTargetWitnesses"]
    if len(witnesses) != 2:
        raise ValueError("both initial ordinary attachments need legality witnesses")
    links = {(u["id"], host["id"]) for _, host, u in attachments(before)}
    for slot, witness in zip(("nonunique_upgrade", "unique_upgrade"), witnesses):
        q = witness["publicTargetQuery"]
        validate_capture(q, refs)
        if q["decision"] != "UpgradeTarget" or q["sourceInstance"] != refs[slot] or witness["upgrade"] != refs[slot] or witness["offeredHost"] not in G.action_for(q, witness["host"]) or (witness["upgrade"], witness["host"]) not in links:
            raise ValueError("actual lawful initial attachment witness differs")
    shield_links = {(u["id"], host["id"]): seat for seat, host, u in attachments(before) if u.get("setCode") == "TOKEN_SHIELD"}
    declared = case["shieldFixtureWitnesses"]
    if len(declared) != len(shield_links) or len({w["token"] for w in declared}) != len(declared):
        raise ValueError("complete physical Shield witnesses required")
    for w in declared:
        if (w["token"], w["parent"]) not in shield_links or w["code"] != "TOKEN_SHIELD" or w["owner"] != shield_links[w["token"], w["parent"]] or w["sourceHash"] != plan["selected_whole_rows"]["TOKEN_SHIELD"]["sourceHash"]:
            raise ValueError("Shield fixture identity/parent/source binding differs")
    for slot, name in (("friendly_ground", "ground"), ("space_small", "small"), ("space_large", "large")):
        p, expected = before["projections"][slot], context[name]
        if any(p[field] != expected[key] for field, key in (("damage", "damage"), ("exhausted", "exhausted"), ("shield_count", "shield"))):
            raise ValueError("world public damage/exhaustion/Shield differs")
        if name != "ground" and (p["code"] != expected["code"] or p["owner"] != expected["owner"]):
            raise ValueError("world space helper code/owner differs")


def validate_journal(journal, receipt):
    if journal is None:
        raise ValueError("durable native journal required")
    if isinstance(journal, (str, Path)):
        journal = [json.loads(line) for line in Path(journal).read_text().splitlines() if line.strip()]
    header = journal[0]
    if header["schema"] != "native-effect-v2-apply-journal/1" or header["sourceRevision"] != G.REVISION or header["selectedWholeCards"] != receipt["selectedWholeCards"] or header["planSha256"] != receipt["collectionPlanSha256"]:
        raise ValueError("journal source/plan header differs")
    intents, ends, completions = {}, {}, {}
    for row in journal[1:]:
        phase = row["phase"]
        if phase == "beforeApply":
            n = row["applyCall"]
            if n in intents or n != len(intents) + 1:
                raise ValueError("nonsequential or duplicate durable apply boundary")
            intents[n] = row
        elif phase in ("afterApply", "applyError"):
            n = row["applyCall"]
            if n not in intents or n in ends or row["context"] != intents[n]["context"] or row["branch"] != intents[n]["branch"]:
                raise ValueError("journal outcome lacks matching single intent")
            ends[n] = row
        elif phase == "contextComplete":
            key = row["context"]
            if key in completions:
                raise ValueError("duplicate root journal completion")
            completions[key] = row["case"]
        else:
            raise ValueError("unreviewed journal phase")
    if len(intents) != receipt["applyCalls"] or set(intents) != set(ends):
        raise ValueError("durable native apply accounting differs")
    for case in receipt["cases"]:
        key = f'{case["card"]}-family-{case["state_family"]}'
        if completions.get(key) != case:
            raise ValueError("journal root boundary differs from final receipt")
        calls = [n for n, r in intents.items() if r["context"] == key]
        if len(calls) != case["applyCalls"]:
            raise ValueError("per-root durable count differs")
        for n, step in zip(calls, case["steps"]):
            r, end = intents[n], ends[n]
            if r["before"] != step["before"] or r["offeredAction"] != step["action"] or r["branch"] != step["stage"] or end.get("after") != step["after"]:
                raise ValueError("raw action chain differs from durable journal")
        if case["engineError"] is not None and (not calls or ends[calls[-1]]["phase"] != "applyError"):
            raise ValueError("native error lacks durable attempted apply")
        if case["engineError"] is not None:
            failed = intents[calls[-1]]
            last = case["steps"][-1]["after"] if case["steps"] else case["before"]
            if failed["before"] != last or failed["offeredAction"] not in last["offeredActions"]:
                raise ValueError("failed native attempt lacks exact offered before-state")
    if set(completions) != {f'{c["card"]}-family-{c["state_family"]}' for c in receipt["cases"]}:
        raise ValueError("unexpected root journal boundary")


def sparse_masks(arrays, train_indices):
    source, target = arrays["source_mask"].copy(), arrays["target_mask"].copy()
    target[np.asarray(train_indices, dtype=np.int64), :, 2:7] = 0
    return source, target


def convert_receipt(receipt, plan, assembled, journal):
    if receipt.get("schema") != "jepa-native-effect-v2/1" or receipt.get("sourceRevision") != G.REVISION or receipt.get("collectionPlan") != plan:
        raise ValueError("native source/schema/full frozen plan differs")
    if receipt["candidateOrder"] != plan["candidate_order"] or tuple(plan["candidate_order"]) != P.CANDIDATES or receipt["selectedWholeCards"] != plan["selected_whole_cards"] or receipt["selectedCatalogueSha256"] != G.native_catalog_hash(assembled, plan["selected_whole_cards"]):
        raise ValueError("complete selected catalogue or candidate ABI differs")
    for key, expected in (("context_feature_names", P.CONTEXT_FEATURES), ("candidate_feature_names", P.CANDIDATE_FEATURES), ("source_head_names", P.SOURCE_HEADS), ("source_binary_heads", P.SOURCE_BINARY), ("target_names", P.TARGET_HEADS), ("binary_heads", P.TARGET_BINARY)):
        if plan.get(key) != list(expected): raise ValueError("ordered named ABI differs: " + key)
    if type(receipt["applyCalls"]) is not int or not 0 <= receipt["applyCalls"] <= plan["collector_max_engine_applies"]:
        raise ValueError("native global apply cap differs")
    validate_journal(journal, receipt)
    cards = {c["code"]: c for c in plan["cards"]}
    cases = sorted(receipt["cases"], key=lambda c: (c["state_family"], c["card"]))
    if len(cards) != 12 or len(plan["split"]["train_codes"]) != 7 or len(plan["split"]["heldout_codes"]) != 5 or len(cases) != 48 or {(c["card"], c["state_family"]) for c in cases} != {(c, f) for c in cards for f in range(4)}:
        raise ValueError("all48 predeclared 12-card/7-5 roots required")
    rows = {r["setCode"]: r for r in assembled["cards"]}
    for code, row in plan["selected_whole_rows"].items():
        if any(rows[code].get(k) != v for k, v in row.items()):
            raise ValueError("complete source/helper row differs")
    x, cx, sy, sm, ty, tm, parts, selected, roles = [], [], [], [], [], [], [], [], []
    for case in cases:
        code, family = case["card"], case["state_family"]
        context, spec = plan["contexts"][family], query(plan, code, family)
        if case["chosen_ref"] != spec["ref"] or case["observation_mode"] != spec["mode"] or spec["mode"] not in MODES or case["identity_partition"] != cards[code]["partition"] or case["state_partition"] != context["partition"]:
            raise ValueError("predeclared public query/role/split differs")
        validate_setup(case, context, plan)
        b, refs = case["before"], case["refs"]
        j, mode = plan["candidate_order"].index(spec["ref"]), spec["mode"]
        selected.append(j); roles.append(mode)
        x.append(A.context_vector(b, rows)); cx.append([A.candidate_vector(b["projections"][s], refs["source"], rows) for s in plan["candidate_order"]])
        source, source_mask = np.zeros(9, np.float32), np.zeros(9, np.float32)
        target, target_mask = np.zeros((8, 7), np.float32), np.zeros((8, 7), np.float32)
        offered = G.action_for(b, refs["source"]); play = case["playAction"]
        source[0], source_mask[0] = bool(offered), 1
        if (play is None) != (not offered) or play is not None and play not in offered:
            raise ValueError("own hand offered play binding differs")
        steps, error = case["steps"], case["engineError"]
        if type(case["applyCalls"]) is not int or case["applyCalls"] != len(steps) + int(error is not None) or not 0 <= case["applyCalls"] <= plan["max_applies_per_case"]:
            raise ValueError("per-root native apply boundary differs")
        last, commits, captures = b, [], [b]
        for k, step in enumerate(steps):
            action, stage = step["action"], step["stage"]
            if step["before"] != last or action not in last["offeredActions"]:
                raise ValueError("native action/snapshot chain differs")
            validate_capture(step["after"], refs); captures.append(step["after"])
            if k == 0:
                if stage != "play-own-hand" or action != play: raise ValueError("first native apply must be exact source play")
            elif stage in ("chosen-target", "attach-intended-host"):
                decision = "UpgradeTarget" if stage == "attach-intended-host" else "AbilityTarget"
                expected_mode = "upgrade-attachment" if stage == "attach-intended-host" else "chosen-target"
                if mode != expected_mode or last["decision"] != decision or last != case["targetPrompt"] or action != case["targetAction"] or action not in G.action_for(last, refs[spec["ref"]]): raise ValueError("actual intended target/parent commit binding differs")
                commits.append(step)
            elif stage == "decline-unoffered-target":
                if last != case["targetPrompt"] or G.action_for(last, refs[spec["ref"]]) or not (action.get("arg") in ("cancel", "passAbility") or action.get("label") == "Cancel"): raise ValueError("decline substituted an available or different target")
            elif stage == "accept-optional-trigger":
                if last["decision"] != "AbilityOptional" or action.get("arg") != "trigger": raise ValueError("optional trigger differs")
            elif stage == "use-no-effect-anyway":
                if last["decision"] != "AbilityNoEffect" or type(action.get("arg")) is not int or action["arg"] != 0: raise ValueError("no-effect menu differs")
            elif stage == "sole-trigger-order":
                if last["decision"] != "TriggerOrder" or len(last["offeredActions"]) != 1: raise ValueError("ambiguous trigger order")
            else: raise ValueError("unreviewed native stage")
            last = step["after"]
        attempted_target = case["targetAction"] is not None
        if case.get("lastObserved", last) != last or len(commits) > 1 or case.get("chosenTargetCommitted", attempted_target) != attempted_target or commits and not attempted_target:
            raise ValueError("last snapshot/selected commit witness differs")
        prompt = case["targetPrompt"]
        if prompt is not None:
            validate_capture(prompt, refs)
            if mode not in ("chosen-target", "upgrade-attachment") or prompt["decision"] not in ("AbilityTarget", "UpgradeTarget") or not any(s["after"] == prompt for s in steps): raise ValueError("target/parent prompt not actually reached")
            if attempted_target and case["targetAction"] not in G.action_for(prompt, refs[spec["ref"]]): raise ValueError("attempted target differs from actual intended offer")
            for k, slot in enumerate(plan["candidate_order"]): target[k, 0] = bool(G.action_for(prompt, refs[slot])); target_mask[k, 0] = 1
        elif case["targetAction"] is not None: raise ValueError("target action without prompt")
        final = case["final"]
        paid, committed = False, False
        if final is not None:
            if final != last or error is not None or case["completion"] != "settled" or not validate_capture(final, refs): raise ValueError("future needs exact settled native endpoint")
            a, z = b["projections"]["source"], final["projections"]["source"]
            attached = any(u["id"] == refs["source"] for _, _, u in attachments(final))
            if mode == "upgrade-attachment" and commits and z["zone"] == "upgrade" and not any(host["id"] == refs[spec["ref"]] and u["id"] == refs["source"] for _, host, u in attachments(final)):
                raise ValueError("selected upgrade lacks actual intended physical parent link")
            committed = z["zone"] != "hand" and (z["in_arena"] or z["zone"] == "discard" or z["zone"] == "upgrade" and attached)
            cost = G.ready_resources(b) - G.ready_resources(final)
            if cost < 0: raise ValueError("unreviewed resource gain")
            source[1:] = [committed, cost, z["in_arena"], z["zone"] == "discard", z["zone"] == "hand", z["damage"] - a["damage"], z["shield_count"] - a["shield_count"], z["exhausted"]]
            source_mask[1:6] = 1
            for h, field in ((6, "damage"), (7, "shield_count"), (8, "exhausted")):
                source_mask[h] = bool(z["in_arena"] and a["known"][field] and z["known"][field])
            paid = bool(committed and cost > 0)
            observed = paid and (bool(commits) if mode in ("chosen-target", "upgrade-attachment") else True)
            if mode == "upgrade-attachment" and observed and not any(host["id"] == refs[spec["ref"]] and u["id"] == refs["source"] for _, host, u in attachments(final)):
                raise ValueError("paid attachment is not physically on intended parent")
            if mode == "self-entry" and observed and (spec["ref"] != "source" or not z["in_arena"]): raise ValueError("self-entry anchor differs from actual paid entering unit")
            if mode == "passive-area-anchor" and observed and (code != "SEC_051" or commits or prompt is not None): raise ValueError("fictional target choice for area observation")
            if observed:
                a, z = b["projections"][spec["ref"]], final["projections"][spec["ref"]]
                removed = not z["present"] or z["zone"] in ("discard", "absent")
                target[j, 1], target_mask[j, 1] = removed, 1
                # Entry lifecycle facts remain source9 secondary, not an effect
                # on a continuously observed same-zone selected unit.
                same_physical = mode != "self-entry" and not removed and a["present"] and z["present"] and a["zone"] == z["zone"]
                for h, field in enumerate(DELTAS, 2):
                    if same_physical and a["known"][field] and z["known"][field]: target[j, h] = float(z[field]) - float(a[field]); target_mask[j, h] = 1
                if code == "JTL_079" and (removed or not z["known"]["hp"] or not z["known"]["damage"] or z["hp"] - z["damage"] <= 0): raise ValueError("JTL079 target survival contract violated")
        if code == "SEC_051":
            enemy_ids = {u["id"] for _, u in units(b, "p2")}
            for capture in captures:
                if {u["id"] for _, u in units(capture, "p2")} != enemy_ids or any(u["hp"] - u["damage"] <= 0 for _, u in units(capture, "p2")):
                    raise ValueError("SEC051 enemy death would expose unreviewed XP hook")
                if any(u.get("setCode") == "TOKEN_EXPERIENCE" for _, _, u in attachments(capture)) or any(p["xp_count"] != 0 for p in capture["projections"].values()): raise ValueError("SEC051 XP hook unexpectedly observed")
        if not offered and (steps or final is not None or error is not None or prompt is not None): raise ValueError("unavailable play cannot have future outcomes")
        sy.append(source); sm.append(source_mask); ty.append(target); tm.append(target_mask)
        parts.append("joint" if code in plan["split"]["heldout_codes"] and family == 3 else "program-held" if code in plan["split"]["heldout_codes"] else "state-held" if family == 3 else "train")
    arrays = dict(context_features=np.asarray(x, np.float32), candidate_features=np.asarray(cx, np.float32), candidate_mask=np.ones((48, 8), np.float32),
                  source_targets=np.asarray(sy, np.float32), source_mask=np.asarray(sm, np.float32), targets=np.asarray(ty, np.float32), target_mask=np.asarray(tm, np.float32),
                  source_cards=np.asarray([c["card"] for c in cases]), state_families=np.asarray([c["state_family"] for c in cases], np.int64), partition=np.asarray(parts),
                  selected_candidate_indices=np.asarray(selected, np.int64), observation_modes=np.asarray(roles), native_family_ids=np.asarray([cards[c["card"]].get("family", "unknown") for c in cases]))
    for part in ("train", "program-held", "state-held", "joint"): arrays[part.replace("-", "_") + "_idx"] = np.flatnonzero(arrays["partition"] == part).astype(np.int64)
    arrays["sparse_source_mask"], arrays["sparse_target_mask"] = sparse_masks(arrays, arrays["train_idx"])
    if any(not np.isfinite(v).all() for v in arrays.values() if v.dtype.kind == "f"): raise ValueError("nonfinite converted feature/label")
    support = {}
    for group, ix in {**{p: np.flatnonzero(arrays["partition"] == p) for p in set(parts)}, **{c: np.flatnonzero(arrays["source_cards"] == c) for c in cards}}.items():
        support[group] = {}
        for names, key, mk in ((P.SOURCE_HEADS, "source_targets", "source_mask"), (P.TARGET_HEADS, "targets", "target_mask")):
            for h, name in enumerate(names):
                y, mask = arrays[key][ix, ..., h], arrays[mk][ix, ..., h]; values = y[mask > 0]
                positive, negative, zero = (y > 0) & (mask > 0), (y < 0) & (mask > 0), (y == 0) & (mask > 0)
                root_count = lambda v: int(np.count_nonzero(v if v.ndim == 1 else v.any(-1)))
                support[group][name] = dict(known=int(values.size), roots=int(np.count_nonzero(mask if mask.ndim == 1 else mask.sum(-1))), values=np.unique(values).astype(float).tolist(), zero=int(zero.sum()), nonzero=int((values != 0).sum()),
                    positive=int(positive.sum()), negative=int(negative.sum()), positive_roots=root_count(positive), negative_roots=root_count(negative), zero_roots=root_count(zero))
    errors = sum(c["engineError"] is not None for c in cases)
    pending = sum(c["playAction"] is not None and c["final"] is None and c["engineError"] is None for c in cases)
    blockers = (["native-engine-errors"] if errors else []) + (["pending-native-outcomes"] if pending else [])
    manifest = dict(schema="native-effect-v2-data/1", cards=cards, programs=cards, plan=plan, records=cases, split=plan["split"],
                    candidate_order=list(P.CANDIDATES), context_feature_names=list(P.CONTEXT_FEATURES), candidate_feature_names=list(P.CANDIDATE_FEATURES), source_head_names=list(P.SOURCE_HEADS), source_binary_heads=list(P.SOURCE_BINARY), target_names=list(P.TARGET_HEADS), binary_heads=list(P.TARGET_BINARY),
                    source_revision=G.REVISION, native_apply_calls=receipt["applyCalls"], native_engine_error_roots=errors, pending_roots=pending,
                    fit_blockers=blockers, planned_settlement_precheck_passed=not blockers, settlement_gate_scope="No engine errors or pending outcomes; independently measured per-head/card support is a separate required fit gate.",
                    head_support=support, sparse_operator=dict(columns=list(P.TARGET_HEADS[2:7]), roots="TRAIN only", source_masks_unchanged=True, full_evaluation_masks_unchanged=True),
                    root_observation_roles=[dict(card=c["card"], state_family=c["state_family"], mode=c["observation_mode"], intended_ref=c["chosen_ref"], actual_target_action=c["targetAction"]) for c in cases],
                    native_family_ids_scope="Raw native plan family labels, provenance only; learner joins authoritative strict-contract groups separately.",
                    self_entry_primary_numeric_masked=True, semantic_validated=False, scope="Saved native fixture observations only; no inferred unexecuted effects, whole-card/gameplay qualification or engine-oracle claim.")
    return arrays, manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-receipt", type=Path, required=True); ap.add_argument("--journal", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True); ap.add_argument("--out", type=Path, default=P.ROOT / "native-effect-v2.npz")
    args = ap.parse_args(); mp = args.out.with_suffix(".manifest.json")
    if args.out.exists() or mp.exists(): raise FileExistsError("preserve existing dataset/manifest")
    plan, receipt = json.loads(args.plan.read_text()), json.loads(args.native_receipt.read_text())
    if receipt["collectionPlanSha256"] != G.sha(args.plan): raise ValueError("frozen plan byte hash differs")
    for pin in plan.get("source_pins", []):
        if G.sha(pin["path"]) != pin["sha256"]: raise ValueError("protected source changed")
    arrays, manifest = convert_receipt(receipt, plan, G.assembled_catalog(G.PINNED_KESSEL / "compiler/generated"), args.journal)
    args.out.parent.mkdir(parents=True, exist_ok=True); np.savez_compressed(args.out, **arrays)
    paths = [Path(__file__), HERE / "native_effect_v2.py", HERE / "native_effect_v2_collector/src/main.rs", HERE / "actual_corpus_native_plan.py", HERE / "grounded_contrast_data.py", args.plan, args.native_receipt, args.journal]
    manifest.update(artifact=dict(path=str(args.out), sha256=G.sha(args.out)), native_receipt=dict(path=str(args.native_receipt), sha256=G.sha(args.native_receipt)), journal=dict(path=str(args.journal), sha256=G.sha(args.journal)), source_pins=[dict(path=str(p), sha256=G.sha(p)) for p in paths])
    mp.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(path=str(args.out), sha256=G.sha(args.out), native_applies=0, neural_forwards=0)))


if __name__ == "__main__": main()
