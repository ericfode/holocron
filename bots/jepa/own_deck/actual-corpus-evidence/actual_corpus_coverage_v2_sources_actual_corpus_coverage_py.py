"""Data-only, alias-aware coverage of the complete saved27 main declarations.

No model, engine, numerical framework, training or private observation is used.
Runtime admission is an atomic loader gate whose own report says game
conformance is not assessed. All unknown cards/copies remain in each main list.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[3] / "experiments"
GENERATED = EXPERIMENTS.parent.parent / "task-5/kessel-pilot-source/compiler/generated"
SCHEMA = "jepa-actual-corpus-coverage/1"
PROPOSED_IDS = ("ASH_048", "JTL_095", "SEC_163", "LOF_155", "LOF_077", "JTL_078", "JTL_158", "JTL_217")
HELD_PROPOSED_IDS = ("LOF_155", "JTL_217")
EXPECTED = dict(catalog="0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812",
                admission="91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957",
                saved_vectors="145cdedc7ae40dc7bf0a512de3bc27deb2d3de1f3a46c8ac69b4ac7bf068ff86",
                split="1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(value):
    if isinstance(value, dict):
        number, set_name = value.get("number"), value.get("set")
        if type(number) is not int or number < 0 or number > 2**64-1 or not isinstance(set_name, str):
            return None
        value = f"{set_name}_{number}"
    if not isinstance(value, str) or not value.isascii():
        return None
    match = re.fullmatch(r"([A-Z0-9]+)_([0-9]+)", value.strip().upper())
    return f"{match[1]}_{(match[2].lstrip('0') or '0').zfill(3)}" if match else None


def index_catalog(catalog):
    if catalog.get("schema") != "swu-card-ir-cards/v1":
        raise ValueError("unknown catalog schema")
    aliases, rows = defaultdict(set), {}
    for row in catalog["cards"]:
        card = row.get("card") or {}
        canonical = normalize(card.get("setId")) or normalize(row.get("setCode"))
        if canonical is None:
            continue
        for value in [canonical, row.get("setCode"), *card.get("setCodes", [])]:
            if code := normalize(value):
                aliases[code].add(canonical)
        if canonical in rows and rows[canonical] != row:
            raise ValueError("conflicting canonical catalog record " + canonical)
        rows[canonical] = row
    ambiguous = {code: sorted(codes) for code,codes in aliases.items() if len(codes) != 1}
    return {code:next(iter(codes)) for code,codes in aliases.items() if len(codes) == 1}, rows, ambiguous


def canonical_counts(entries, aliases):
    if isinstance(entries, dict):
        entries = [dict(id=code,count=count) for code,count in entries.items()]
    if not isinstance(entries, list):
        raise ValueError("unordered count map/list required")
    counts = Counter()
    for row in entries:
        if not isinstance(row,dict) or type(row.get("count")) is not int or not 0 <= row["count"] <= 2**53-1:
            raise ValueError("invalid exact copy count")
        code = normalize(row.get("id"))
        if code not in aliases:
            raise ValueError("unknown or ambiguous printed alias: " + str(code))
        counts[aliases[code]] += row["count"]
        if counts[aliases[code]] > 2**53-1:
            raise ValueError("merged count overflow")
    return dict(sorted((code,count) for code,count in counts.items() if count))


def effect_kinds(value):
    """Inventory actual serialized typed kinds, without interpreting outcomes."""
    kinds = Counter()
    def visit(node):
        if isinstance(node,dict):
            if isinstance(node.get("kind"),str):
                kinds[node["kind"]] += 1
            for child in node.values():
                visit(child)
        elif isinstance(node,list):
            for child in node:
                visit(child)
    visit(value)
    return dict(sorted(kinds.items()))


def flags(code, admitted, saved, proposed):
    return dict(runtime_admitted=code in admitted,
                saved_selected_action_vector_available=code in saved,
                proposed_native_fixture_selected=code in proposed,
                whole_card_typed_model_serialized=False,
                native_fixture_verified=False,
                learned_whole_card_vector_available=False,
                whole_card_trained=False,
                unknown_runtime=code not in admitted,
                unknown_saved_selected_action_vector=code not in saved,
                unknown_whole_card_typed_model=True,
                unknown_native_fixture=True,
                unknown_learned_whole_card_vector=True)


def build(catalog, admission, decks, saved_vectors, split):
    aliases, records, ambiguous = index_catalog(catalog)
    admitted = {aliases[row["setCode"]]:row for row in admission["runtimeAdmittedCards"] if row["setCode"] in aliases}
    saved = {aliases[row["id"]] for row in saved_vectors["rows"] if row["ability_path"][1] == "card"}
    proposed = {aliases[code] for code in PROPOSED_IDS}
    train_ids = set(split["split"]["train_idx"])
    val_ids = set(split["split"]["val_idx"])
    counts, deck_frequency, deck_rows = Counter(), Counter(), []
    for deck in sorted(decks["rows"], key=lambda x:x["source_index"]):
        own = canonical_counts(deck["canonical_card_counts"],aliases)
        index = deck["source_index"]
        expected_partition = "train" if index in train_ids else "val" if index in val_ids else None
        if expected_partition is None or deck["split"] not in (expected_partition,"validation" if expected_partition=="val" else "train"):
            raise ValueError("saved declaration and inherited22/5 split disagree")
        total = sum(own.values())
        if total != deck["total_count"] or not total:
            raise ValueError("main count mismatch/empty main declaration")
        entries = []
        for code,n in own.items():
            card = records[code]["card"]
            if any(t in card.get("types",[]) for t in ("leader","base","token")):
                raise ValueError("non-main form entered main declaration")
            entries.append(dict(canonical_id=code,source_id=str(records[code].get("id",card.get("id"))),copies=n,
                                runtime_implementation=admitted.get(code,{}).get("implementation"),
                                **flags(code,admitted,saved,proposed)))
        coverage = {}
        for label,key in (("runtime_admitted","runtime_admitted"),("saved_selected_action_vectors","saved_selected_action_vector_available"),
                          ("proposed_native_fixture","proposed_native_fixture_selected"),("typed_model_serialized","whole_card_typed_model_serialized"),
                          ("native_fixture_verified","native_fixture_verified"),("learned_whole_card_vectors","learned_whole_card_vector_available"),
                          ("whole_card_trained","whole_card_trained")):
            present = [entry for entry in entries if entry[key]]
            copies = sum(entry["copies"] for entry in present)
            coverage[label] = dict(copies=copies,unique_ids=len(present),copy_fraction=copies/total,
                                   unique_fraction=len(present)/len(entries),unknown_copies=total-copies)
        deck_rows.append(dict(source_index=index,composition_fingerprint=deck["composition_fingerprint"],family_id=deck["family_id"],
                              split=expected_partition,total_main_copies=total,main_unique_ids=len(entries),
                              leader=deck["leader"],base=deck["base"],coverage=coverage,main_cards=entries))
        counts.update(own);deck_frequency.update(own.keys())
    inventory, implementations, types, triggers = [], Counter(), Counter(), Counter()
    no_ir = no_ir_keywords = empty_ir_keywords = 0
    for code in sorted(set(counts)&set(admitted)):
        row, card = records[code], records[code]["card"]
        abilities = row.get("abilities",{})
        flat = [ability for side in abilities.values() for ability in side]
        implementations[admitted[code]["implementation"]] += 1
        types.update(card.get("types",[]))
        triggers.update(ability.get("trigger","<missing>") for ability in flat)
        if not flat:
            no_ir += 1
            if card.get("keywords"):
                no_ir_keywords += 1
            else:
                empty_ir_keywords += 1
        inventory.append(dict(canonical_id=code,source_id=str(row.get("id",card.get("id"))),
                              aliases=sorted(alias for alias,target in aliases.items() if target==code),
                              main_copies=counts[code],declaration_count=deck_frequency[code],
                              source_path=row.get("sourcePath"),source_sha256=row.get("sourceHash"),data_sha256=row.get("dataHash"),
                              whole_catalog_row_sha256=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
                              whole_catalog_row=row,
                              runtime_admission=admitted[code],printed_metadata=card,abilities=abilities,
                              keyword_values=row.get("keywordValues",{}),required_capabilities=row.get("requiredCapabilities",[]),
                              ability_registration_count=len(flat),ability_triggers=dict(sorted(Counter(a.get("trigger","<missing>") for a in flat).items())),
                              typed_node_kinds=effect_kinds(abilities),no_declared_ir_abilities=not flat,
                              no_declared_ir_abilities_or_keywords=not flat and not card.get("keywords"),
                              vanilla_semantics_verified=False,**flags(code,admitted,saved,proposed)))
    present_native = set(counts)&set(admitted)
    def totals(domain):
        ids = set(counts)&set(domain)
        copies = sum(counts[code] for code in ids)
        return dict(unique_ids=len(ids),copies=copies,copy_fraction=copies/sum(counts.values()),
                    ids=sorted(ids),unknown_copies=sum(counts.values())-copies)
    summary = dict(declarations=len(deck_rows),train_declarations=len(train_ids),held_declarations=len(val_ids),
                   main_copies=sum(counts.values()),main_unique_ids=len(counts),runtime_admitted=totals(admitted),
                   saved_selected_action_vectors=totals(saved),proposed_native_fixture=totals(proposed),
                   whole_card_typed_model_serialized=totals(set()),native_fixture_verified=totals(set()),
                   learned_whole_card_vectors=totals(set()),whole_card_trained=totals(set()),
                   runtime_implementation_unique=dict(sorted(implementations.items())),
                   runtime_implementation_copies={kind:sum(counts[code] for code in present_native if admitted[code]["implementation"]==kind) for kind in sorted(implementations)},
                   runtime_types_unique=dict(sorted(types.items())),ability_registrations=sum(triggers.values()),
                   ability_trigger_counts=dict(sorted(triggers.items())),zero_ir_cards=no_ir,
                   zero_ir_with_keywords=no_ir_keywords,zero_ir_and_keywords_empty=empty_ir_keywords,
                   proposed_card_records=[dict(canonical_id=code,main_copies=counts[code],declaration_count=deck_frequency[code],
                                               proposed_fit_partition="held-card" if code in HELD_PROPOSED_IDS else "train-card") for code in sorted(proposed)])
    return dict(schema=SCHEMA,status="data-only-pre-native-pre-model",summary=summary,
                runtime_game_conformance=admission.get("gameConformance"),ambiguous_aliases=ambiguous,
                canonical_join="catalog card.setId / card.setCodes / setCode, never numeric exported source ID",
                main_identity_inventory=[dict(canonical_id=code,source_id=str(records[code].get("id",records[code]["card"].get("id"))),copies=counts[code],declaration_count=deck_frequency[code],**flags(code,admitted,saved,proposed)) for code in sorted(counts)],
                decks=deck_rows,runtime_admitted_card_inventory=inventory,
                unknown_policy="Every original main-card copy retained. Masks distinguish runtime admission, serialized model input, planned/verified native fixtures and learned vectors. No missing vector is relabeled vanilla or silently dropped.",
                whole_row_policy="Every admitted inventory entry preserves the complete pinned catalog row, including top-level attachCondition/stateWatchers or other executable fields; the convenience abilities/printed fields are not a complete semantic frontend by themselves.",
                claims="Runtime admission is not assessed game conformance, native fixture verification, whole-card semantic validation, learned vector coverage or strategic quality. Proposed8-card coverage is a plan, not executed evidence.")


def prepare(out):
    paths = dict(catalog=GENERATED/"cards.json",admission=GENERATED/"runtime-admission.json",
                 decks=EXPERIMENTS/"embedding-export/deck-embeddings.json",
                 saved_vectors=EXPERIMENTS/"embedding-export/grounded-contrast-v1/card-embeddings.json",
                 split=EXPERIMENTS/"data/real-decks.manifest.json")
    for key,digest in EXPECTED.items():
        if sha(paths[key]) != digest:
            raise ValueError("pinned input mismatch " + key)
    values = {key:json.loads(path.read_text()) for key,path in paths.items()}
    result = build(**values)
    result["sources"] = {key:dict(path=str(path.resolve()),sha256=sha(path),bytes=path.stat().st_size) for key,path in paths.items()}
    result["source_code"] = dict(path=str(Path(__file__).resolve()),sha256=sha(__file__))
    expected = (result["summary"]["declarations"],result["summary"]["main_copies"],result["summary"]["main_unique_ids"],result["summary"]["runtime_admitted"]["copies"],result["summary"]["runtime_admitted"]["unique_ids"])
    if expected != (27,1432,251,635,115):
        raise ValueError("coverage changed; review before proceeding: " + str(expected))
    out = Path(out);out.mkdir(parents=True,exist_ok=False)
    target = out/"actual-corpus-coverage.json"
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    receipt = dict(schema=SCHEMA+"/receipt",path=str(target),sha256=sha(target),bytes=target.stat().st_size,
                   source_sha256=sha(__file__),native_calls=0,model_forwards=0,optimizer_updates=0)
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path,help="NEW data-only artifact directory")
    print(json.dumps(prepare(parser.parse_args().out),indent=2))


if __name__ == "__main__":
    main()
