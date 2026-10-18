"""DEFERRED, unexecuted historical partial-bag proposal; not an active pilot.

The CLI never imports a numerical framework or executes a model. The lazy model
factory is for a separately authorized, bounded worker. Selected action-program
availability is not whole-card semantic knowledge, legality, synergy or strength.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[3] / "experiments"
KESSEL = EXPERIMENTS.parent.parent / "task-5/kessel-pilot-source/compiler/generated"
SCHEMA = "jepa-staged-program-bag-composition/1"
ARMS = ("learned-program", "untrained-ir", "id-only", "current-deck")
TRAIN_IDS = ("IBH_016", "LOF_134", "SHD_196", "SOR_094", "TWI_056")
HELD_IDS = ("HMW_170", "TWI_157")
TRAIN_PAIRS = tuple((TRAIN_IDS[i], TRAIN_IDS[(i+1) % len(TRAIN_IDS)]) for i in range(5))
HELD_PAIR = HELD_IDS
TRAIN_TEMPLATES = ((1,1), (1,2), (2,1), (2,2), (2,3), (3,2), (3,3))
HELD_TEMPLATES = ((1,3), (3,1))
ASPECTS = ("vigilance", "command", "aggression", "cunning", "heroism", "villainy")
KEYWORDS = ("ambush", "bounty", "grit", "overwhelm", "raid", "restore", "saboteur", "sentinel", "shielded", "sweep")
TARGET_NAMES = ("total_count_per_60", "mean_cost_per_10", "low_cost_le_2_fraction",
                *(f"cost_{i}_fraction" for i in range(8)), "cost_8_plus_fraction", "initial_draw_unit_probability")
INPUT_DIM, TRAINABLE_PARAMETERS = 130, 6829
PINNED = {
    "catalog": "0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812",
    "admission": "91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957",
    "vectors": "145cdedc7ae40dc7bf0a512de3bc27deb2d3de1f3a46c8ac69b4ac7bf068ff86",
    "real_manifest": "1d1f6f413dd116dfd7b6254822136e236e90c52a9026463daf32390be17c4622",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def normalized_code(value):
    if isinstance(value, dict):
        number, set_name = value.get("number"), value.get("set")
        if type(number) is not int or not 0 <= number <= 2**64-1 or not isinstance(set_name, str):
            return None
        value = f"{set_name}_{number}"
    if not isinstance(value, str) or not value.isascii():
        return None
    match = re.fullmatch(r"([A-Z0-9]+)_([0-9]+)", value.strip().upper())
    if not match:
        return None
    return f"{match[1]}_{(match[2].lstrip('0') or '0').zfill(3)}"


def catalog_index(catalog):
    aliases, records = defaultdict(set), {}
    if catalog.get("schema") != "swu-card-ir-cards/v1":
        raise ValueError("unrecognized pinned catalog")
    for row in catalog["cards"]:
        card = row.get("card") or {}
        canonical = normalized_code(card.get("setId")) or normalized_code(row.get("setCode"))
        if canonical is None:
            continue
        values = [canonical, row.get("setCode"), *card.get("setCodes", [])]
        for value in values:
            if code := normalized_code(value):
                aliases[code].add(canonical)
        # The catalog normally has one whole canonical row. Conflicts are not
        # silently resolved using whichever printing appears first.
        if canonical in records and records[canonical] != row:
            raise ValueError("duplicate canonical catalog rows: " + canonical)
        records[canonical] = row
    ambiguous = {code: sorted(names) for code, names in aliases.items() if len(names) != 1}
    return {code: next(iter(names)) for code, names in aliases.items() if len(names) == 1}, records, ambiguous


def canonical_counts(entries, aliases, max_copies=None):
    """Merge aliases/duplicates, exclude zero rows, reject malformed counts."""
    if isinstance(entries, dict):
        entries = [dict(id=code, count=count) for code, count in entries.items()]
    if not isinstance(entries, list):
        raise ValueError("declaration must be an unordered list or count map")
    counts = Counter()
    for item in entries:
        if not isinstance(item, dict) or type(item.get("count")) is not int or not 0 <= item["count"] <= 2**53-1:
            raise ValueError("count must be a nonnegative exact integer")
        code = normalized_code(item.get("id"))
        if code not in aliases:
            raise ValueError("unknown or ambiguous canonical alias")
        counts[aliases[code]] += item["count"]
        if counts[aliases[code]] > 2**53-1 or (max_copies is not None and counts[aliases[code]] > max_copies):
            raise ValueError("canonical copy count exceeds declared bound")
    return dict(sorted((code, count) for code, count in counts.items() if count))


def fnv_bin(text, bins=8):
    value = 2166136261
    for byte in text.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value % bins


def printed_features(card):
    """Fixed32 printed features only; no title/text, IR or source identifiers."""
    for key in ("types", "aspects", "traits", "keywords"):
        if not isinstance(card.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in card[key]):
            return [0.] * 32, False
    types, aspects, traits, keywords = (sorted(set(x.strip().lower() for x in card[key])) for key in ("types", "aspects", "traits", "keywords"))
    if not types or any(x in types for x in ("leader", "base", "token")):
        return [0.] * 32, False
    unit = "unit" in types
    values = [card.get("cost"), card.get("power", 0) if unit else 0, card.get("hp", 0) if unit else 0]
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 or x > 1e6 for x in values):
        return [0.] * 32, False
    features = [x / 10 for x in values] + [float(x in types) for x in ("unit", "event", "upgrade")]
    features += [float(card.get("arena") == arena) for arena in ("ground", "space")]
    features += [float(x in aspects) for x in ASPECTS]
    features += [float(any(k == x or k.startswith(x + " ") for k in keywords)) for x in KEYWORDS]
    bins = [0.] * 8
    for trait in traits:
        bins[fnv_bin(trait)] += 1.
    features += bins
    assert len(features) == 32
    return features, True


def labels(counts, records):
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("composition labels require a nonempty bag")
    costs = low = units = 0.
    curve = [0.] * 9
    for code, count in counts.items():
        card = records[code]["card"]
        _, known = printed_features(card)
        if not known:
            raise ValueError("unknown printed metadata cannot produce a target")
        cost = card["cost"]
        costs += count * cost
        low += count * (cost <= 2)
        units += count * ("unit" in card["types"])
        curve[min(int(cost), 8)] += count
    return [total / 60, costs / total / 10, low / total, *(x / total for x in curve), units / total]


def feature_rows(counts, records, bank, baseline=None, available=None):
    """Same identity/count rows, printed32 and flags across all four arms.

    `available` is the common selected-program domain, independent of arm bank.
    A missing entry in a claimed supported bank fails closed. The current-deck
    baseline is a single frozen deck latent broadcast across these same rows.
    """
    available = set(bank) if available is None else set(available)
    if baseline is not None and (len(baseline) != 96 or any(type(x) not in (int,float) or not math.isfinite(x) for x in baseline)):
        raise ValueError("baseline must be a finite frozen96-vector")
    rows, weights = [], []
    for code, count in sorted(counts.items()):
        printed, known = printed_features(records[code]["card"])
        supported = code in available
        if supported and (code not in bank or len(bank[code]) != 16):
            raise ValueError("claimed supported selected-program vector is absent")
        vector = list(bank[code]) if supported else [0.] * 16
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in vector):
            raise ValueError("nonfinite program vector")
        semantic = list(baseline) if baseline is not None else vector + [0.] * 80
        rows.append(semantic + printed + [float(supported), float(known)])
        weights.append(count)
    return rows, weights


def pool_reference(transformed, weights, rows):
    """Pure count/pooling contract; does not execute an encoder or model."""
    if len(rows) != len(weights) or len(transformed) != len(weights) or not weights:
        raise ValueError("nonempty aligned bag required")
    if any(type(n) is not int or n <= 0 for n in weights):
        raise ValueError("positive exact copy weights required")
    total = sum(weights)
    weighted = [math.fsum(row[i] * n for row, n in zip(transformed, weights)) for i in range(32)]
    return [x / total for x in weighted] + [x / 60 for x in weighted] + [total / 60, len(rows) / 60,
            math.fsum(row[128] * n for row,n in zip(rows,weights)) / total,
            math.fsum(row[129] * n for row,n in zip(rows,weights)) / total]


def make_bags(records):
    bags = []
    for pair_index, pair in enumerate((*TRAIN_PAIRS, HELD_PAIR)):
        for template in (*TRAIN_TEMPLATES, *HELD_TEMPLATES):
            held_card, held_count = pair_index == 5, template in HELD_TEMPLATES
            cell = "joint" if held_card and held_count else "held-card" if held_card else "held-template" if held_count else "train"
            counts = dict(sorted(zip(pair, template)))
            for code in counts:
                if "unit" not in records[code]["card"]["types"]:
                    raise ValueError("this pilot is main-unit selected programs only")
            bags.append(dict(id=f"pair-{pair_index}-copies-{template[0]}-{template[1]}", pair_group=pair_index,
                             ordered_pair=list(pair), template=list(template), cell=cell, counts=counts,
                             fingerprint=hashlib.sha256(canonical_json(counts).encode()).hexdigest(),
                             total_count=sum(template), targets=labels(counts, records)))
    if len({row["fingerprint"] for row in bags}) != 54:
        raise ValueError("duplicate bag fingerprints")
    return bags


def target_mask(bags):
    train = [b["targets"] for b in bags if b["cell"] == "train"]
    mask = [max(row[i] for row in train) > min(row[i] for row in train) for i in range(13)]
    if not any(mask):
        raise ValueError("no training-varying composition targets")
    return mask


def build_model(torch):
    """Lazy identical trainable DECK graph. Caller supplies frozen data tensors.

    Card banks are not Parameters, and are not part of this graph. Callers clone
    one initialized state_dict into all four arms and run only under root GO.
    """
    class BagEncoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.phi = torch.nn.Linear(130, 32)
            self.rho = torch.nn.Linear(68, 32)
            self.head = torch.nn.Linear(32, 13)

        def forward(self, rows, copies):
            if rows.ndim != 3 or rows.shape[-1] != 130 or copies.shape != rows.shape[:2]:
                raise ValueError("expected batch×identity×130 rows and copy weights")
            copies = copies.to(rows.dtype)
            total = copies.sum(1, keepdim=True)
            if bool((total <= 0).any()):
                raise ValueError("empty bag")
            hidden = torch.nn.functional.gelu(self.phi(rows))
            summed = (hidden * copies.unsqueeze(-1)).sum(1)
            distinct = (copies > 0).sum(1, keepdim=True).to(rows.dtype)
            coverage = (rows[:,:,128:130] * copies.unsqueeze(-1)).sum(1) / total
            pooled = torch.cat((summed / total, summed / 60, total / 60, distinct / 60, coverage), 1)
            return self.head(torch.nn.functional.gelu(self.rho(pooled)))

    model = BagEncoder()
    if sum(p.numel() for p in model.parameters()) != TRAINABLE_PARAMETERS:
        raise ValueError("unmatched trainable graph")
    return model


def coverage_audit(real_rows, vector_rows, inventory, admission, aliases, records):
    all_counts, per_deck = Counter(), []
    saved = {aliases[row["id"]] for row in vector_rows if row["ability_path"][1] == "card"}
    trained = {aliases[row["id"]] for row in vector_rows if row["ability_path"][1] == "card" and row["seen_in_training"]}
    main_actions = {aliases[row["card"]] for row in inventory["records"] if row["source_form"] == "card"}
    native = {aliases[row["setCode"]] for row in admission["runtimeAdmittedCards"] if row["setCode"] in aliases}
    def intersection(counts, domain):
        common = sorted(set(counts) & domain)
        return dict(copies=sum(counts[code] for code in common), unique_ids=len(common), ids=common)
    for row in sorted(real_rows, key=lambda row: row["source_index"]):
        counts = canonical_counts(row["canonical_card_counts"], aliases)
        all_counts.update(counts)
        per_deck.append(dict(source_index=row["source_index"], family_id=row["family_id"], split=row["split"],
                             total_count=sum(counts.values()), selected_program=intersection(counts, saved),
                             native_admission=intersection(counts, native)))
    classes = defaultdict(Counter)
    for code, count in all_counts.items():
        record = records[code]
        abilities = [a for group in record.get("abilities", {}).values() for a in group]
        if code not in native:
            kind = "not-native-admitted"
        elif code in main_actions:
            kind = "native-admitted-action-program"
        elif abilities or record["card"].get("keywords"):
            kind = "native-admitted-other-abilities-or-keywords"
        else:
            kind = "native-admitted-no-ir-abilities-or-keywords-vanilla-unproven"
        classes[kind].update({code: count})
    return dict(schema=SCHEMA+"/real-coverage", declarations=len(real_rows), main_copies=sum(all_counts.values()),
                main_unique_ids=len(all_counts), selected_main_program_ids=sorted(saved), trained_main_program_ids=sorted(trained),
                action_inventory_main_ids=sorted(main_actions), total_runtime_admitted_records=len(admission["runtimeAdmittedCards"]),
                selected_program=intersection(all_counts,saved), trained_program=intersection(all_counts,trained),
                action_inventory=intersection(all_counts,main_actions), native_admission=intersection(all_counts,native),
                native_classes={kind:dict(copies=sum(c.values()),unique_ids=len(c)) for kind,c in sorted(classes.items())},
                real27_semantic_comparison_admitted=bool(set(all_counts) & saved), per_deck=per_deck,
                scope="Main lists only; numeric exported source IDs never used for alias joins. Missing vectors are unknown, never vanilla; whole-card semantic coverage is not admitted.")


def prepare(out):
    raise RuntimeError("DEFERRED: synthetic54 bags superseded by the actual27 corpus bridge; no artifact or execution admitted")
    paths = dict(catalog=KESSEL/"cards.json", admission=KESSEL/"runtime-admission.json",
                 vectors=EXPERIMENTS/"embedding-export/grounded-contrast-v1/card-embeddings.json",
                 real_manifest=EXPERIMENTS/"data/real-decks.manifest.json",
                 real_vectors=EXPERIMENTS/"embedding-export/deck-embeddings.json",
                 inventory=EXPERIMENTS/"grounded-contrast/inventory.json")
    for key, digest in PINNED.items():
        if sha(paths[key]) != digest:
            raise ValueError("frozen input changed: " + key)
    inputs = {key:json.loads(path.read_text()) for key,path in paths.items()}
    aliases, records, ambiguous = catalog_index(inputs["catalog"])
    bags = make_bags(records)
    audit = coverage_audit(inputs["real_vectors"]["rows"], inputs["vectors"]["rows"], inputs["inventory"], inputs["admission"], aliases, records)
    if audit["declarations"] != 27 or audit["main_copies"] != 1432 or audit["main_unique_ids"] != 251 or audit["selected_program"]["copies"] != 0:
        raise ValueError("predeclared real-deck coverage changed; review before fitting")
    common_ids = set(TRAIN_IDS + HELD_IDS)
    vector_rows = {aliases[row["id"]]: row for row in inputs["vectors"]["rows"] if row["ability_path"][1] == "card"}
    if set(vector_rows) != common_ids or any(vector_rows[code]["seen_in_training"] != (code in TRAIN_IDS) for code in common_ids):
        raise ValueError("selected program/pretraining split changed")
    # Fixed card metadata/labels are emitted now, before any model forward.
    cards = {code:dict(printed_features=printed_features(records[code]["card"])[0],
                      selected_program_available=True, whole_card_semantics_known=False,
                      source_hash=records[code].get("sourceHash"), ability_path=vector_rows[code]["ability_path"],
                      learned_vector=list(vector_rows[code]["vector"])) for code in sorted(common_ids)}
    plan = dict(schema=SCHEMA, status="prepared-not-executed", real27_semantic_admission=False,
                conditional_scope="Partial nonlegal selected-action-program bags; printed composition only; no whole-card, synergy or strength claim.",
                sources={key:dict(path=str(path.resolve()),sha256=sha(path),bytes=path.stat().st_size) for key,path in paths.items()},
                source_code=dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)),
                protocol=dict(path=str(HERE/"STAGED_DECK_COMPOSITION_PROTOCOL.md"),sha256=sha(HERE/"STAGED_DECK_COMPOSITION_PROTOCOL.md")),
                ambiguous_catalog_aliases=ambiguous, card_order=sorted(common_ids), pair_groups=[list(p) for p in (*TRAIN_PAIRS,HELD_PAIR)],
                train_templates=TRAIN_TEMPLATES, held_templates=HELD_TEMPLATES,
                cells=dict(Counter(b["cell"] for b in bags)), target_names=TARGET_NAMES, train_varying_target_mask=target_mask(bags),
                arms=ARMS, input_dim=INPUT_DIM, trainable_parameters_per_arm=TRAINABLE_PARAMETERS,
                graph="phi130x32/GELU; copy mean32,sum32/60,4counts/coverage; rho68x32/GELU; head32x13",
                optimizer=dict(name="AdamW",lr=0.003,betas=[0.9,0.999],eps=1e-8,weight_decay=0.0),
                loss="mean MSE over train-only varying heads; all13 and per-head losses retained",
                fit=dict(seed=17,updates_per_arm=100,arms=4,total_updates=400,batch="all35train",held_forwards=8,seconds=20,rss_bytes=1024**3,cpu_threads=1),
                prep=dict(forwards=2,untrained_ir_batches=1,current_deck_batches=1,current_deck_rows=54,seconds=20,rss_bytes=1024**3,cpu_threads=1),
                bank_status=dict(learned="saved-export-read-only",untrained_ir="pending-authorized-single-bank-forward",id_only="pending-saved-table-read-only",current_deck="pending-authorized-single54row-forward"),
                gates=dict(card_native="planned-not-run",card_model="planned-not-run",fresh_whole_card="unsupported",root_go_required=True),
                frozen_card_weights=True,trainable_deck_encoder=True,no_provenance_inputs=True)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name, data in (("real27-coverage.json",audit),("partial-bags.json",dict(schema=SCHEMA,cards=cards,rows=bags)),("plan.json",plan)):
        (out/name).write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")
    return dict(output=str(out),files={p.name:sha(p) for p in sorted(out.iterdir())},executed_forwards=0,optimizer_updates=0,native_calls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", type=Path, required=True, help="NEW output directory; data/hash preparation only")
    print(json.dumps(prepare(parser.parse_args().prepare),indent=2))


if __name__ == "__main__":
    main()
