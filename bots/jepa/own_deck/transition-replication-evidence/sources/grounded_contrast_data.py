"""Existing-runtime inventory and frozen inputs for grounded semantic contrasts.

No runtime/compiler/card conversion or model execution happens here. Whole-card
native admission, selected IR coverage, source-form binding and measured labels
are separate evidence levels. Raw ordered programs remain inspectable.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

HERE = Path(__file__).resolve().parent
PINNED_KESSEL = Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source")
REVISION = "c7ee39554901278cee70f61fd8b26fb1920696b3"
CORE_CODES = ("ASH_011", "IBH_053", "IBH_016", "LOF_134", "TWI_056", "TWI_157",
              "SHD_196", "HMW_170", "SOR_094", "LOF_004", "SOR_007", "SOR_011")
TRAIN_CODES = ("SOR_011", "ASH_011", "IBH_053", "IBH_016", "LOF_134", "TWI_056", "SHD_196", "SOR_094", "LOF_004", "SOR_007")
HELDOUT_CODES = ("TWI_157", "HMW_170")
CANDIDATES = ("own_base", "opponent_base", "friendly_ground", "enemy_ground", "enemy_space", "friendly_imperial", "friendly_creature", "source")
TARGETS = ("source_use", "target_allowed", "cost_resource", "damage_delta", "source_exhausted_after", "target_exhausted_delta", "shield_delta", "xp_delta", "target_defeated", "followup_source_offered", "terminal")
CONTEXT_FEATURES = ("ready_resources", "source_exhausted")
CANDIDATE_FEATURES = ("owner_self", "owner_opponent", "is_unit", "is_base", "zone_ground", "zone_space", "same_source", "present",
                      "damage", "hp", "remaining_hp", "power", "exhausted", "shield_count", "xp_count",
                      "known_damage", "known_hp", "known_remaining_hp", "known_power", "known_exhausted", "known_shield_count", "known_xp_count",
                      "trait_imperial", "trait_creature", "trait_spectre", "known_traits")
STATE_FAMILIES = (
    dict(id=0, name="baseline", overrides={}),
    dict(id=1, name="friendly-damaged-exhausted", overrides={"friendly_ground": {"damage": 2, "exhausted": True}}),
    dict(id=2, name="space-damaged-exhausted", overrides={"enemy_space": {"damage": 1, "exhausted": True}}),
    dict(id=3, name="own-base-damaged", overrides={"own_base": {"damage": 2}}),
    dict(id=4, name="imperial-damaged-exhausted", overrides={"friendly_imperial": {"damage": 1, "exhausted": True}}),
    dict(id=5, name="enemy-base-near-terminal", overrides={"opponent_base": {"damage": 29}}),
    dict(id=6, name="source-exhausted", overrides={"source": {"exhausted": True}}),
    dict(id=7, name="no-ready-resources", overrides={"ready_resources": 0}),
    dict(id=8, name="both-ground-damaged-exhausted", overrides={"friendly_ground": {"damage": 1, "exhausted": True}, "enemy_ground": {"damage": 2, "exhausted": True}}),
    dict(id=9, name="creature-damaged-exhausted", overrides={"friendly_creature": {"damage": 1, "exhausted": True}}),
    dict(id=10, name="held-friendly-one-hp", overrides={"friendly_ground": {"damage": 3, "exhausted": True}, "ready_resources": 3}),
    dict(id=11, name="held-enemy-base-two-hp", overrides={"opponent_base": {"damage": 28}, "ready_resources": 3}),
    dict(id=12, name="held-space-damaged-no-resources", overrides={"enemy_space": {"damage": 2, "exhausted": False}, "ready_resources": 0}),
    dict(id=13, name="held-creature-more-damaged", overrides={"friendly_creature": {"damage": 2, "exhausted": True}, "ready_resources": 2}),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def normalized_program(ability):
    """Drop only root display title; keep every other field and list position."""
    program = copy.deepcopy(ability)
    program.pop("title", None)
    return program


def nodes(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key in sorted(value):
            yield from nodes(value[key], path + (key,))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from nodes(child, path + (i,))


def pointer(path):
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in path)


def dependencies(ability):
    kinds, queries, references, literals = set(), set(), set(), set()
    typed_nodes = []
    for path, node in nodes(ability):
        if not isinstance(node, dict):
            continue
        kind = node.get("kind")
        if kind is not None:
            kinds.add(kind)
            typed_nodes.append(dict(path=pointer(path), kind=kind))
        if kind == "query":
            queries.add(node.get("name"))
        if kind == "ref":
            references.add(tuple(node.get("path", [])))
        if kind == "const":
            literals.add(json.dumps(node.get("value"), sort_keys=True))
    tokens = []
    if "giveShield" in kinds:
        tokens.append("TOKEN_SHIELD")
    if "giveExperience" in kinds:
        tokens.append("TOKEN_EXPERIENCE")
    return dict(node_kinds=sorted(kinds), query_names=sorted(queries), reference_paths=[list(v) for v in sorted(references)],
                typed_node_paths=typed_nodes, literal_values=sorted(literals), required_native_tokens=tokens)


def describe_effect(effect):
    if not isinstance(effect, dict):
        return "missing"
    kind = effect.get("kind", "unknown")
    if kind in ("sequence", "simultaneous"):
        return kind + "[" + "; ".join(describe_effect(c) for c in effect.get("effects", [])) + "]"
    amount = effect.get("amount")
    if isinstance(amount, dict):
        amount = amount.get("value") if amount.get("kind") == "const" else amount.get("name", amount.get("kind"))
    return str(kind) + (" " + str(amount) if amount is not None else "") + " -> " + str(effect.get("target", "unspecified"))


def inventory(catalog, runtime):
    admitted = {r["setCode"]: r for r in runtime["runtimeAdmittedCards"]}
    records = []
    for card in catalog["cards"]:
        if card["setCode"] not in admitted:
            continue
        for side, abilities in card.get("abilities", {}).items():
            if not isinstance(abilities, list):
                raise ValueError("admitted ability side is not an ordered list")
            for index, ability in enumerate(abilities):
                if ability.get("trigger") != "action":
                    continue
                normalized = normalized_program(ability)
                printed = card.get("card") or {}
                aliases = sorted({f"{s['set']}_{s['number']:03}" for s in printed.get("setCodes", [])})
                records.append(dict(card=card["setCode"], canonical_card_id=str(printed.get("id")), aliases=aliases,
                                    title=printed.get("title"), subtitle=printed.get("subtitle"), ability_path=["abilities", side, index], source_form=side,
                                    sourceHash=card.get("sourceHash"), sourcePath=card.get("sourcePath"), dataHash=card.get("dataHash"), whole_card_row_sha256=digest(card),
                                    runtime_admission=admitted[card["setCode"]], whole_card_admitted=True,
                                    printed={k: printed.get(k) for k in ("types", "arena", "cost", "power", "hp", "aspects", "traits", "keywords")},
                                    complete_ability_counts={k: len(v) for k, v in card["abilities"].items()},
                                    raw_ability=copy.deepcopy(ability), normalized_program=normalized, program_group_id=digest(normalized),
                                    source_binding_group_id=digest(dict(source_form=side, program=normalized)),
                                    dependencies=dependencies(ability), effect_summary=describe_effect(ability.get("effect")),
                                    selected_core=card["setCode"] in CORE_CODES,
                                    binding_status="existing verified undeployed-leader fixture" if card["setCode"] in ("ASH_011", "IBH_053") else
                                                   "existing runtime primitive; new public source/menu binding needs collection verification"))
    groups = defaultdict(list)
    identities = defaultdict(list)
    for r in records:
        groups[r["program_group_id"]].append(dict(card=r["card"], ability_path=r["ability_path"]))
        identities[r["canonical_card_id"]].append(r["card"])
    selected = [r for r in records if r["selected_core"]]
    if {r["card"] for r in selected} != set(CORE_CODES) or len(selected) != len(CORE_CODES):
        raise ValueError("core list does not resolve one complete runtime-admitted activated ability per identity")
    return dict(schema="jepa-grounded-contrast-inventory/1", source_revision=REVISION, runtime_admitted_action_abilities=len(records),
                runtime_admitted_action_cards=len({r["card"] for r in records}), normalized_program_groups=len(groups),
                normalization="Object-key order canonicalized; only root ability.title excluded. Every remaining key, cost/condition/selector/effect/continuation, list index and operand role is retained.",
                duplicate_program_groups={key: values for key, values in groups.items() if len(values) > 1},
                canonical_identity_groups=dict(identities), records=records, proposed_core=selected,
                proposal=dict(status="inventory-only-not-frozen-or-executed", selected_identities=len(selected), selected_program_groups=len({r["program_group_id"] for r in selected}),
                              rule="Aliases and exact normalized programs must remain together. Held-out primitives/operators/enums/amounts require an explicit training-coverage table.",
                              native_runtime_expansion=False, card_conversion=False, model_or_native_execution=False),
                effect_root_counts=dict(Counter(r["raw_ability"].get("effect", {}).get("kind", "missing") for r in records)))


def table(report):
    lines = ["# Existing runtime-admitted activated programs", "", "Inventory only: no native actions or training executed.", "",
             "| Card | Source | Printed source | Cost | Target | Effect | Native token dependency |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in report["proposed_core"]:
        a, p = r["raw_ability"], r["printed"]
        costs = []
        for c in a.get("costs", []):
            amount = c.get("amount", {})
            costs.append(c["kind"] + (":" + str(amount.get("value", "dynamic")) if amount else ""))
        target = a.get("targetResolver") or {}
        selector = "/".join(str(target.get(k, "*")) for k in ("owner", "type", "zone", "arena"))
        if "predicate" in target:
            selector += " + exact predicate"
        stats = str(p.get("arena")) + " " + str(p.get("power")) + "/" + str(p.get("hp")) + "; " + ",".join(p.get("traits") or [])
        lines.append("| " + " | ".join([r["card"], "/".join(map(str, r["ability_path"][1:])), stats,
                                         ", ".join(costs), selector, r["effect_summary"], ", ".join(r["dependencies"]["required_native_tokens"]) or "none"]) + " |")
    lines.extend(["", f"Whole catalog: {report['runtime_admitted_action_abilities']} actions, {report['runtime_admitted_action_cards']} cards, {report['normalized_program_groups']} normalized program groups.",
                  "", "Exact costs, predicates, ordered effects, additional keys, all-side ability counts, aliases and source/data hashes are preserved in inventory.json.", ""])
    return "\n".join(lines)


def split_plan(report):
    selected = {r["card"]: r for r in report["proposed_core"]}
    def groups(codes, key):
        return {selected[c][key] for c in codes}
    for key in ("canonical_card_id", "program_group_id"):
        if groups(TRAIN_CODES, key) & groups(HELDOUT_CODES, key):
            raise ValueError("identity/program duplicates cross declared split")
    train_aliases = {a for c in TRAIN_CODES for a in selected[c]["aliases"]}
    if train_aliases & {a for c in HELDOUT_CODES for a in selected[c]["aliases"]}:
        raise ValueError("reprint aliases cross declared split")
    def atoms(program):
        global_values, positioned = set(), set()
        for path, value in nodes(program):
            if isinstance(value, (dict, list)):
                continue
            token = (type(value).__name__, json.dumps(value, sort_keys=True))
            global_values.add(token)
            positioned.add((pointer(path), *token))
        return global_values, positioned
    train_global, train_positioned = set(), set()
    for code in TRAIN_CODES:
        g, p = atoms(selected[code]["normalized_program"])
        train_global |= g
        train_positioned |= p
    coverage = {}
    for code in HELDOUT_CODES:
        row = selected[code]
        g, p = atoms(row["normalized_program"])
        coverage[code] = dict(all_global_typed_atoms_seen=not (g - train_global),
                              unseen_global_typed_atoms=[dict(value_type=t, value=json.loads(v)) for t, v in sorted(g - train_global)],
                              novel_positioned_atoms=[dict(path=path, value_type=t, value=json.loads(v)) for path, t, v in sorted(p - train_positioned)],
                              interpretation="Global primitive/value familiarity is distinct from an unseen full program or new path/value composition; no learned generalization is inferred from this table.")
    return dict(schema="jepa-grounded-contrast-program-split/1", status="program-identities-frozen-statebank-pending", train_codes=list(TRAIN_CODES), heldout_codes=list(HELDOUT_CODES),
                train_program_group_ids=sorted(groups(TRAIN_CODES, "program_group_id")), heldout_program_group_ids=sorted(groups(HELDOUT_CODES, "program_group_id")),
                identity_overlap=0, normalized_program_overlap=0, reprint_alias_overlap=0, constituent_coverage=coverage,
                programs=[dict(code=r["card"], side=r["source_form"], index=r["ability_path"][-1], source_hash=r["sourceHash"], source_path=r["sourcePath"],
                               program_group_id=r["program_group_id"], canonical_card_id=r["canonical_card_id"], aliases=r["aliases"], raw_ability=r["raw_ability"],
                               printed=r["printed"], all_side_ability_counts=r["complete_ability_counts"], dependencies=r["dependencies"],
                               partition="train" if r["card"] in TRAIN_CODES else "heldout") for r in report["proposed_core"]],
                native_runtime_expansion=False, model_updates=0, native_applies=0)


def partition(card, state_family):
    if card not in CORE_CODES or type(state_family) is not int or state_family not in range(14):
        raise ValueError("unknown frozen card or state family")
    held_program = card in HELDOUT_CODES
    held_state = state_family >= 10
    return "joint-held" if held_program and held_state else "program-held" if held_program else "state-held" if held_state else "train"


def numeric_contract():
    units = {k: "boolean" for k in CANDIDATE_FEATURES}
    for k in ("damage", "hp", "remaining_hp", "power", "shield_count", "xp_count"):
        units[k] = "native public count"
    return dict(schema="jepa-grounded-contrast-numeric/1", root_cases=168, candidates=list(CANDIDATES),
                context=dict(shape=["R", 2], columns=list(CONTEXT_FEATURES), units=["ready-resource copies", "boolean"], normalization="None; both values must be directly known in the native before projection."),
                candidate=dict(shape=["R", 8, 26], columns=list(CANDIDATE_FEATURES), units=[units[k] for k in CANDIDATE_FEATURES],
                               normalization="Natural public units and explicit known flags. Unknown numerical payload0 is masked by its known flag; no target/offer or source identity feature.",
                               printed_predicates="Only imperial/creature/spectre traits required by the frozen programs, resolved against pinned complete catalog. Target HP/power remain necessary public predicate/delta inputs; opaque identity, title, source printed cost and irrelevant metadata are excluded."),
                prediction_locality="Source head: program plus2globals only. Candidate head: program plus2globals plus its own26candidate attributes. No candidate/source-self pooling or broadcasting into other queries.",
                primary_candidates=dict(shape=["R", 8], array="primary_candidate_mask", values=[1, 1, 1, 1, 1, 1, 1, 0],
                                        scope="Helper/base slots0..6 define matched-context primary contrasts; source-self slot7 is a separate diagnostic with legitimate source-specific target properties."),
                source_self_diagnostic=dict(shape=["R", 8], array="source_diagnostic_mask", values=[0, 0, 0, 0, 0, 0, 0, 1],
                                            auxiliary_loss_weight=0.1, primary_metrics=False, pooling_or_broadcast=False),
                source_use=dict(shape=["R"], available_mask="source_use_mask[R]", loss_owner="one native source/menu query per root"),
                candidate_allowed=dict(shape=["R", 8], available_mask="candidate_allowed_mask[R,8]", loss_owner="one actual target-prompt offered membership per candidate; unknown if no actual prompt"),
                transitions=dict(shape=["R", 8, 11], columns=list(TARGETS), masks="target_mask[R,8,11]", normalization=[1.] * 11,
                                 units=["boolean", "boolean", "ready-resource copies paid", "signed damage-counter change", "boolean", "signed exhaustion change", "signed Shield-count change", "signed Experience-count change", "boolean", "boolean", "boolean"],
                                 standalone_head_columns_masked=[0, 1], loss_ownership="source_use and target_allowed branch columns always masked; standalone heads own those coordinates exactly once.",
                                 death="Target damage/exhaustion/token deltas are unknown when the selected target leaves the observable arena; target_defeated remains a separate native label."),
                split=dict(train_codes=list(TRAIN_CODES), heldout_codes=list(HELDOUT_CODES), train_state_families=list(range(10)), heldout_state_families=list(range(10, 14)),
                           expected_cell_counts={"train": 100, "program-held": 20, "state-held": 40, "joint-held": 8}, primary="joint-held",
                           rule="Both axes fixed before collection. All source/menu/cancel/commit/follow-up branches remain inside one card/state root. Familiar states in program-held and familiar IDs in state-held are intentional."),
                state_defaults=dict(physical_resources=3, ready_resources=2, source_exhausted=False, helper_damage=0, helper_exhausted=False, base_damage=0),
                state_families=list(STATE_FAMILIES), native_labels_only=True, model_or_native_execution=False)


def assembled_catalog(generated):
    """Mirror pinned catalogue_io::load_catalogue_value without native execution."""
    generated = Path(generated)
    manifest = json.loads((generated / "manifest.json").read_text())
    read = lambda key: json.loads((generated / manifest["files"][key]).read_text())
    cards, inputs, diagnostics = read("cards"), read("inputs"), read("diagnostics")
    if any(s["compilerHash"] != manifest["compilerHash"] for s in (cards, inputs, diagnostics)):
        raise ValueError("catalogue shard compiler hashes differ")
    diagnostic_map = {r["setCode"]: r["diagnostics"] for r in diagnostics["cards"]}
    return dict(schema="swu-card-ir/v1", **{k: manifest[k] for k in
                ("compilerVersion", "typescriptVersion", "sourceTreeHash", "compilerHash", "sourceSupport", "inventory")},
                inputs=inputs["inputs"], cards=[{**r, "diagnostics": diagnostic_map.get(r["setCode"], [])} for r in cards["cards"]])


def native_catalog_hash(catalog, selected):
    subset = {**catalog, "cards": [r for r in catalog["cards"] if r["setCode"] in selected]}
    # serde_json's default object maps are key-sorted, and Unicode is UTF-8.
    return hashlib.sha256(json.dumps(subset, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def ready_resources(capture):
    resources = capture["state"]["players"]["p1"]["resources"]
    if any(type(c.get("exhausted")) is not bool for c in resources):
        raise ValueError("resource readiness must be observed boolean")
    return sum(not c["exhausted"] for c in resources)


def scalar(value):
    if type(value) not in (int, float, bool) or not math.isfinite(value):
        raise ValueError("native scalar must be finite")
    return float(value)


def boolean(value):
    if type(value) is not bool:
        raise ValueError("native known/boolean flag must be explicit")
    return value


def candidate_vector(projection, source_id, card_rows):
    """One pre-action public reference only; never reads offers or later states."""
    p, known = projection, projection["known"]
    if p["owner"] not in ("p1", "p2"):
        raise ValueError("unknown native public owner")
    values = [p["owner"] == "p1", p["owner"] == "p2", boolean(p["is_unit"]), boolean(p["is_base"]),
              p["zone"] == "ground", p["zone"] == "space", p["id"] == source_id, boolean(p["present"])]
    fields = ("damage", "hp", "power", "exhausted", "shield_count", "xp_count")
    flags = {f: boolean(known[f]) for f in fields}
    numbers = {f: scalar(p[f]) if flags[f] else 0. for f in fields}
    remaining_known = flags["hp"] and flags["damage"]
    values += [numbers["damage"], numbers["hp"], numbers["hp"] - numbers["damage"] if remaining_known else 0.,
               numbers["power"], numbers["exhausted"], numbers["shield_count"], numbers["xp_count"],
               flags["damage"], flags["hp"], remaining_known, flags["power"], flags["exhausted"], flags["shield_count"], flags["xp_count"]]
    row = card_rows.get(p["code"])
    traits = row.get("card", {}).get("traits") if row is not None else None
    traits_known = isinstance(traits, list) and all(isinstance(t, str) for t in traits)
    traits = {t.lower() for t in traits} if traits_known else set()
    values += [t in traits for t in ("imperial", "creature", "spectre")] + [traits_known]
    vector = np.asarray(values, np.float32)
    if vector.shape != (26,) or not np.isfinite(vector).all():
        raise ValueError("candidate feature shape/finite contract failed")
    return vector


def action_for(capture, identity):
    return [a for a in capture["offeredActions"] if a.get("kind") == "card" and a.get("card") == identity]


def settled_capture(capture):
    """Check explicit native continuation/death queues; a prompt is not an outcome."""
    witness = capture["settlement"]
    if witness["decision"] != capture["decision"] or witness["ability_program"] != capture["abilityProgramPlusOne"]:
        raise ValueError("native settlement witness/capture differs")
    counts = ("ability_program", "death_depth", "death_pending", "death_window", "pending_programs", "pending_triggers", "after_attack_triggers", "after_attack_programs")
    if any(type(witness[k]) is not int or witness[k] < 0 for k in counts):
        raise ValueError("native settlement queue counters invalid")
    event_active, support_pending = boolean(witness["event_group_active"]), boolean(witness["support_pending"])
    value = boolean(capture["terminal"]) or (capture["decision"] == "Window" and all(witness[k] == 0 for k in counts)
            and not event_active and not support_pending)
    if boolean(capture["settled"]) != value:
        raise ValueError("native settled flag differs from explicit continuation witness")
    return value


def validate_collection_plan(plan, report):
    frozen = split_plan(report)
    if plan.get("schema") != "grounded-native-collection-plan/1" or plan.get("source_revision") != REVISION:
        raise ValueError("collection plan source/schema differs")
    if plan.get("programs") != frozen["programs"] or plan.get("train_codes") != list(TRAIN_CODES) or plan.get("heldout_codes") != list(HELDOUT_CODES):
        raise ValueError("collection exact programs/split differs")
    if plan.get("candidate_order") != list(CANDIDATES) or plan.get("expected_cases") != 168:
        raise ValueError("collection root/candidate bank differs")
    if plan.get("helpers") != dict(base="ASH_019", ground="LOF_256", space="IBH_022", imperial="IBH_055", creature="TOKEN_BEAST") or plan.get("required_native_tokens") != ["TOKEN_SHIELD", "TOKEN_EXPERIENCE"]:
        raise ValueError("collection fixed whole helper/token bank differs")
    contexts = plan.get("contexts", [])
    if len(contexts) != 14 or {c["id"] for c in contexts} != set(range(14)):
        raise ValueError("collection state family bank differs")
    for context in contexts:
        expected = STATE_FAMILIES[context["id"]]["overrides"]
        overrides = {k: v for k, v in expected.items() if k not in ("ready_resources", "source")}
        if context["overrides"] != overrides or context["ready_resources"] != expected.get("ready_resources", 2) or context["source_exhausted"] != expected.get("source", {}).get("exhausted", False):
            raise ValueError("collection world-state overrides differ")
        if context["partition"] != ("train" if context["id"] < 10 else "state-holdout"):
            raise ValueError("collection state split differs")
    if plan.get("campaign_max_engine_applies") != 2048 or plan.get("collector_max_engine_applies", 2049) > 2048:
        raise ValueError("collection apply quota differs")


def validate_query(case, query, slot, allowed):
    """Validate labels against public native witnesses, never against IR effects."""
    before, after = case["before"], query.get("after")
    identity = case["refs"][slot]
    if query.get("chosen_ref") != slot or query.get("chosen_id") != identity:
        raise ValueError("candidate query reference/order differs")
    values, masks = query["targets"], query["target_mask"]
    if set(values) != set(TARGETS) or set(masks) != set(TARGETS):
        raise ValueError("native target coordinate set differs")
    for name in TARGETS:
        boolean(masks[name])
        if masks[name]:
            scalar(values[name])
            if name in ("source_use", "target_allowed", "source_exhausted_after", "target_defeated", "followup_source_offered", "terminal") and values[name] not in (0, 1):
                raise ValueError("native boolean target outside 0/1")
    if not masks["source_use"] or values["source_use"] != case["source_use"]:
        raise ValueError("native branch source label differs from root")
    prompt = case.get("targetPrompt")
    if masks["target_allowed"] != (prompt is not None) or (prompt is not None and values["target_allowed"] != allowed):
        raise ValueError("native candidate label differs from actual target prompt")
    if query.get("targetAction") is not None and (prompt is None or query["targetAction"] not in action_for(prompt, identity)):
        raise ValueError("target commit was not an exact offered candidate tuple")
    error = query.get("engineError")
    if error is not None and (not isinstance(error, str) or not error.startswith("NATIVE_APPLY_ERROR: ") or not allowed or query.get("targetAction") is None):
        raise ValueError("native error must belong to an actual offered commit")
    if after is None:
        if any(masks[name] for name in TARGETS[2:]):
            raise ValueError("uncommitted/error outcomes must remain unknown")
        if allowed and query.get("engineError") is None:
            raise ValueError("every offered target must have a native commit witness or error")
    else:
        if not allowed or query.get("targetAction") is None or query.get("engineError") is not None:
            raise ValueError("native commit binding/error inconsistency")
        if not settled_capture(after):
            if any(masks[name] for name in TARGETS[2:]) or query.get("following") is not None or query.get("followupPass") is not None:
                raise ValueError("pending native continuation outcomes/follow-up must remain unknown")
            if not isinstance(query.get("pendingOutcome"), str):
                raise ValueError("pending native continuation needs explicit pendingOutcome")
            return [0.] * 11, [0.] * 11
        pre, post = before["projections"][slot], after["projections"][slot]
        observed = dict(cost_resource=ready_resources(before) - ready_resources(after),
                        source_exhausted_after=after["projections"]["source"]["exhausted"], terminal=after["terminal"],
                        target_defeated=pre["attackable"] and (post["zone"] == "discard" or not post["present"]))
        for name, value in observed.items():
            if not masks[name] or values[name] != value:
                raise ValueError("native label differs from committed snapshot: " + name)
        surviving = pre["attackable"] and post["zone"] in ("ground", "space", "base") and post["zone"] == pre["zone"]
        for name, field in (("damage_delta", "damage"), ("target_exhausted_delta", "exhausted"), ("shield_delta", "shield_count"), ("xp_delta", "xp_count")):
            known = surviving and pre["known"][field] and post["known"][field]
            if masks[name] != known or (known and values[name] != scalar(post[field]) - scalar(pre[field])):
                raise ValueError("native delta/observability differs: " + name)
    following = query.get("following")
    if following is None and masks["followup_source_offered"]:
        raise ValueError("unobserved follow-up must remain unknown")
    if following is not None:
        settled_capture(following)
        if after is None or query.get("followupPass") not in after["offeredActions"]:
            raise ValueError("follow-up was not an exact offered action")
        # Presence of a unit card can mean attack. The collector labels only absence.
        if masks["followup_source_offered"] and (values["followup_source_offered"] != 0 or action_for(following, case["refs"]["source"])
                or not settled_capture(following) or following["terminal"] or following["decision"] != "Window"
                or following["state"]["activePlayer"] != "p1" or following["state"]["phase"] != "action"):
            raise ValueError("follow-up absence label differs from native offers")
    return [scalar(values[n]) if masks[n] and j >= 2 else 0. for j, n in enumerate(TARGETS)], [float(masks[n] and j >= 2) for j, n in enumerate(TARGETS)]


def convert_receipt(receipt, report, plan, catalog, plan_sha256):
    validate_collection_plan(plan, report)
    if receipt.get("schema") != "jepa-grounded-native-transitions/1" or receipt.get("sourceRevision") != REVISION:
        raise ValueError("native receipt source/schema differs")
    if receipt.get("collectionPlan") != plan or receipt.get("collectionPlanSha256") != plan_sha256:
        raise ValueError("native collection plan/hash differs")
    if receipt.get("candidateOrder") != list(CANDIDATES) or receipt.get("targetNames") != list(TARGETS):
        raise ValueError("native numerical coordinate order differs")
    calls = receipt.get("applyCalls")
    if type(calls) is not int or not 0 <= calls <= plan["collector_max_engine_applies"]:
        raise ValueError("native apply accounting outside frozen allocation")
    expected_selected = set(CORE_CODES) | set(plan["helpers"].values()) | set(plan["required_native_tokens"])
    if receipt.get("selectedWholeCards") != sorted(expected_selected) or receipt.get("selectedCatalogueSha256") != native_catalog_hash(catalog, expected_selected):
        raise ValueError("native selected whole-catalogue bytes differ")
    selected = {r["card"]: r for r in report["proposed_core"]}
    provenance = receipt.get("provenance", [])
    if len(provenance) != 12:
        raise ValueError("native exact program provenance count differs")
    for code, program in selected.items():
        matches = [p for p in provenance if p.get("card") == code]
        expected = dict(card=code, sourceHash=program["sourceHash"], sourcePath=program["sourcePath"], abilityPath=program["ability_path"], actualUnmodifiedAbility=program["raw_ability"])
        if matches != [expected]:
            raise ValueError("native exact unmodified selected program differs: " + code)
    cases = sorted(receipt["cases"], key=lambda c: (c["context_family"], c["card"]))
    if len(cases) != 168 or {(c["card"], c["context_family"]) for c in cases} != {(c, s) for c in CORE_CODES for s in range(14)}:
        raise ValueError("native fixed root bank contains duplicates/missing cases")
    rows = {r["setCode"]: r for r in catalog["cards"]}
    contexts, candidates, sources, allowances, allowance_masks, targets, target_masks, records = [], [], [], [], [], [], [], []
    matched_states, error_count = {}, 0
    for case in cases:
        code, family, before = case["card"], case["context_family"], case["before"]
        for capture in (before, case.get("sourceOpened"), case.get("postActivation"), case.get("targetPrompt"), case.get("cancelled")):
            if capture is not None:
                settled_capture(capture)
        if not before["settled"] or before["decision"] != "Window":
            raise ValueError("root must be a settled public action window")
        if case.get("abilityPath") != selected[code]["ability_path"] or case.get("identity_partition") != ("train" if code in TRAIN_CODES else "heldout") or case.get("state_partition") != ("train" if family < 10 else "state-holdout"):
            raise ValueError("native root binding/split differs")
        if set(case["refs"]) != set(CANDIDATES) or len(set(case["refs"].values())) != 8:
            raise ValueError("native reference bank differs")
        projections = before["projections"]
        if projections["source"]["code"] != code or any(projections[s]["id"] != case["refs"][s] for s in CANDIDATES):
            raise ValueError("native before source/reference binding differs")
        if not boolean(projections["source"]["known"]["exhausted"]):
            raise ValueError("source exhaustion must be known before prediction")
        context = np.asarray([ready_resources(before), boolean(projections["source"]["exhausted"])], np.float32)
        frozen_state = next(s for s in plan["contexts"] if s["id"] == family)
        helper_codes = [plan["helpers"][k] for k in ("base", "base", "ground", "ground", "space", "imperial", "creature")]
        if len(before["state"]["players"]["p1"]["resources"]) != 3 or context.tolist() != [frozen_state["ready_resources"], float(frozen_state["source_exhausted"])]:
            raise ValueError("native before resource/source state differs from frozen family")
        for i, slot in enumerate(CANDIDATES):
            expected = frozen_state["overrides"].get(slot, {})
            if projections[slot]["damage"] != expected.get("damage", 0) or projections[slot]["exhausted"] != expected.get("exhausted", frozen_state["source_exhausted"] if slot == "source" else False):
                raise ValueError("native before target state differs from frozen family")
            if i < 7 and projections[slot]["code"] != helper_codes[i]:
                raise ValueError("native fixed helper definition differs")
        candidate = np.stack([candidate_vector(projections[s], case["refs"]["source"], rows) for s in CANDIDATES])
        matched = dict(globals=context.tolist(), helper_base_candidates=candidate[:7].tolist())
        state_fp = digest(matched)
        if family in matched_states and matched_states[family] != state_fp:
            raise ValueError("primary relevant public context differs across programs")
        matched_states[family] = state_fp
        if case.get("source_use_known") is not True or type(case.get("source_use")) is not bool:
            raise ValueError("native source availability must be known once per root")
        source_action, opened, menu = case.get("sourceAction"), case.get("sourceOpened"), case.get("menuAction")
        post = case.get("postActivation")
        if source_action is not None and (source_action not in action_for(before, case["refs"]["source"]) or opened is None):
            raise ValueError("native source action not an exact initial offered tuple")
        if menu is not None and (opened is None or menu not in opened["offeredActions"] or type(menu.get("arg")) is not int or menu["arg"] != 0 or menu.get("label") in ("Attack", "Cancel")):
            raise ValueError("native selected unit menu binding differs")
        if source_action is not None and (post is None or (menu is None and post != opened)):
            raise ValueError("native post-activation witness missing/different")
        if source_action is None and any(value is not None for value in (opened, menu, post)):
            raise ValueError("native activation exists without offered source action")
        leader_finished = False
        if post is not None and selected[code]["source_form"] == "leader" and settled_capture(post):
            leader = post["state"]["players"]["p1"]["leader"]
            leader_finished = leader["id"] == case["refs"]["source"] and leader["deployed"] is False
        available = menu is not None or (opened is not None and opened["decision"] in ("AbilityTarget", "AbilityNoEffect")) or leader_finished
        if available != case["source_use"]:
            raise ValueError("source-use label confuses card attack affordance with ability")
        if available and not settled_capture(post) and (post["sourceInstance"] != case["refs"]["source"] or post["abilityProgramPlusOne"] <= 0):
            raise ValueError("native unresolved selected ability source/program differs")
        prompt = case.get("targetPrompt")
        if prompt is not None and (not available or prompt["sourceInstance"] != case["refs"]["source"] or prompt["decision"] != "AbilityTarget"):
            raise ValueError("native actual target prompt binding differs")
        completion = "target-prompt" if prompt is not None else "finished-without-target" if available and settled_capture(post) else "pending-without-target" if available else "attack-only" if source_action is not None else "not-offered"
        if case.get("activationCompletion") != completion:
            raise ValueError("native activation completion witness differs")
        if case.get("cancelled") is not None and (case["cancelled"]["state"] != before["state"] or case["cancelled"]["offeredActions"] != before["offeredActions"]):
            raise ValueError("native cancellation did not restore untouched root")
        if len(case["queries"]) != 8:
            raise ValueError("all eight candidate query branches must be preserved")
        allow = [bool(action_for(prompt, case["refs"][s])) if prompt is not None else False for s in CANDIDATES]
        branch_targets, branch_masks = [], []
        errors = 0
        for slot, query, allowed in zip(CANDIDATES, case["queries"], allow):
            vector, mask = validate_query(case, query, slot, allowed)
            branch_targets.append(vector); branch_masks.append(mask)
            errors += query.get("engineError") is not None
        if case.get("engine_error_branches") != errors:
            raise ValueError("native root engine-error accounting differs")
        error_count += errors
        contexts.append(context); candidates.append(candidate); sources.append(float(available)); allowances.append(allow)
        allowance_masks.append([prompt is not None] * 8); targets.append(branch_targets); target_masks.append(branch_masks)
        records.append(dict(source_card=code, state_family=family, partition=partition(code, family),
                            program_group_id=selected[code]["program_group_id"], state_fingerprint=state_fp,
                            root_fingerprint=digest(dict(program_group=selected[code]["program_group_id"], state=state_fp)),
                            encoded_context_fingerprint=digest(dict(globals=context.tolist(), all_candidates=candidate.tolist())),
                            native_engine_error_branches=errors, raw_native_case=case))
    if len(set(matched_states.values())) != 14:
        raise ValueError("world-state families collapse to identical relevant features")
    if receipt.get("native_engine_error_branches") != error_count:
        raise ValueError("native total engine-error accounting differs")
    n = len(cases)
    arrays = dict(context_features=np.stack(contexts), candidate_features=np.stack(candidates), candidate_mask=np.ones((n, 8), np.float32),
                  primary_candidate_mask=np.tile(np.asarray([1.] * 7 + [0.], np.float32), (n, 1)),
                  source_diagnostic_mask=np.tile(np.asarray([0.] * 7 + [1.], np.float32), (n, 1)),
                  source_use=np.asarray(sources, np.float32), source_use_mask=np.ones(n, np.float32),
                  candidate_allowed=np.asarray(allowances, np.float32), candidate_allowed_mask=np.asarray(allowance_masks, np.float32),
                  targets=np.asarray(targets, np.float32), target_mask=np.asarray(target_masks, np.float32),
                  source_cards=np.asarray([c["card"] for c in cases]), state_families=np.asarray([c["context_family"] for c in cases], np.int64),
                  program_group_ids=np.asarray([r["program_group_id"] for r in records]), partition=np.asarray([r["partition"] for r in records]),
                  root_fingerprints=np.asarray([r["root_fingerprint"] for r in records]), state_fingerprints=np.asarray([r["state_fingerprint"] for r in records]),
                  encoded_context_fingerprints=np.asarray([r["encoded_context_fingerprint"] for r in records]))
    cell_arrays = {"train": "train_idx", "program-held": "program_holdout_idx", "state-held": "state_holdout_idx", "joint-held": "joint_holdout_idx"}
    expected_counts = numeric_contract()["split"]["expected_cell_counts"]
    for cell, key in cell_arrays.items():
        arrays[key] = np.flatnonzero(arrays["partition"] == cell).astype(np.int64)
        if len(arrays[key]) != expected_counts[cell]:
            raise ValueError("four-cell root split count differs")
    def support(cell, primary):
        idx = arrays[cell_arrays[cell]]
        mask = arrays["target_mask"][idx] * (arrays["primary_candidate_mask"][idx, :, None] if primary else 1)
        return {name: dict(known=int(mask[..., j].sum()), values=sorted(set(arrays["targets"][idx, :, j][mask[..., j].astype(bool)].tolist()))) for j, name in enumerate(TARGETS)}
    manifest = dict(schema="jepa-grounded-contrast-data/1", status="native-labels-collected", source_revision=REVISION,
                    numeric_contract=numeric_contract(), context_feature_names=list(CONTEXT_FEATURES), candidate_feature_names=list(CANDIDATE_FEATURES), target_names=list(TARGETS),
                    context_feature_units=numeric_contract()["context"]["units"], candidate_feature_units=numeric_contract()["candidate"]["units"], target_units=numeric_contract()["transitions"]["units"],
                    programs={r["code"]: r for r in plan["programs"]}, source_cards=sorted(CORE_CODES), source_provenance=report.get("sources", []),
                    collection_plan_sha256=plan_sha256, selected_catalogue_sha256=receipt["selectedCatalogueSha256"], selected_whole_cards=receipt["selectedWholeCards"],
                    native_apply_calls=calls, native_engine_error_branches=error_count, root_cases=n, committed_branches=int(arrays["target_mask"][..., 2].sum()),
                    split_counts=expected_counts, identity_program_split=split_plan(report),
                    source_support={cell: dict(roots=len(arrays[key]), known=int(arrays["source_use_mask"][arrays[key]].sum()), values=dict(Counter(str(int(v)) for v in arrays["source_use"][arrays[key]]))) for cell, key in cell_arrays.items()},
                    candidate_allowed_support={cell: dict(known=int(arrays["candidate_allowed_mask"][arrays[key]].sum()), allowed=int((arrays["candidate_allowed"][arrays[key]] * arrays["candidate_allowed_mask"][arrays[key]]).sum())) for cell, key in cell_arrays.items()},
                    target_support={cell: support(cell, False) for cell in cell_arrays}, primary_target_support={cell: support(cell, True) for cell in cell_arrays},
                    paired_context_audit=dict(matched_non_source_contexts=14, programs_per_state=12, source_slot_excluded_from_primary=True,
                                              source_candidate_broadcast_or_pooling_permitted=False, exact_state_axis_overlap_rule="Seen state overlap is intentional only in program-held; held states10..13 never enter training."),
                    unknown_handling="Masked payload0 is not an observed zero. Source/allowed branch columns0/1 are always masked; standalone arrays own those labels once.",
                    prediction_time="Only root before globals and the selected candidate's before public properties. No offered action, mask, outcome, opaque identity/title, global source form or unrelated source statistics are inputs. Source-self target properties are diagnostic only.",
                    limitations=["Action-semantic synthetic-state diagnostic; no authored deck, deck-synergy, policy-strength or gameplay claim.",
                                 "Exact program and identity holdouts recombine familiar typed atoms; novel positioned atoms are explicit in identity_program_split.",
                                 "Candidate source-self properties can identify the source and are diagnostic only; primary comparisons use fixed helper/base slots0..6.",
                                 "Follow-up source presence is unknown when a card affordance could mean attack. Only actual absence is labeled.",
                                 "Native engine errors are preserved, with transition outcomes unknown, and are not negative examples."], records=records)
    return arrays, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kessel-dir", type=Path, default=PINNED_KESSEL)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path)
    parser.add_argument("--collection-plan", type=Path, default=HERE / "grounded_native_collector/collection-plan.json")
    args = parser.parse_args()
    head = subprocess.check_output(["git", "--no-optional-locks", "-C", str(args.kessel_dir), "rev-parse", "HEAD"], text=True).strip()
    if head != REVISION:
        raise ValueError("pinned Kessel revision changed")
    subprocess.run(["git", "--no-optional-locks", "-C", str(args.kessel_dir), "diff", "--quiet", "HEAD", "--", "compiler/generated", "crates/kessel", "Cargo.lock", "Cargo.toml"], check=True)
    generated = args.kessel_dir / "compiler/generated"
    paths = [generated / n for n in ("cards.json", "runtime-admission.json", "manifest.json", "inputs.json", "diagnostics.json")] + [Path(__file__)]
    report = inventory(json.loads(paths[0].read_text()), json.loads(paths[1].read_text()))
    report["sources"] = [dict(path=str(p), sha256=sha(p)) for p in paths]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    artifact = args.out_dir / "inventory.json"
    artifact.write_text(json.dumps(report, indent=2) + "\n")
    (args.out_dir / "INVENTORY.md").write_text(table(report))
    (args.out_dir / "core-programs.json").write_text(json.dumps(split_plan(report), indent=2) + "\n")
    (args.out_dir / "data-contract.json").write_text(json.dumps(numeric_contract(), indent=2) + "\n")
    if args.native_receipt:
        plan = json.loads(args.collection_plan.read_text())
        arrays, manifest = convert_receipt(json.loads(args.native_receipt.read_text()), report, plan, assembled_catalog(generated), sha(args.collection_plan))
        output = args.out_dir / "grounded-contrast.npz"
        np.savez_compressed(output, **arrays)
        manifest["artifact"] = dict(path=str(output.resolve()), sha256=sha(output))
        manifest["native_receipt"] = dict(path=str(args.native_receipt.resolve()), sha256=sha(args.native_receipt))
        manifest["collection_plan"] = dict(path=str(args.collection_plan.resolve()), sha256=sha(args.collection_plan))
        (args.out_dir / "grounded-contrast.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(artifact=str(artifact), sha256=sha(artifact), admitted_actions=report["runtime_admitted_action_abilities"], admitted_cards=report["runtime_admitted_action_cards"], program_groups=report["normalized_program_groups"], proposed_core=len(report["proposed_core"]))))


if __name__ == "__main__":
    main()
