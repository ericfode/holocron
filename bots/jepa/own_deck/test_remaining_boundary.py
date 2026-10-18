"""Synthetic remaining-deck boundary, not a production ledger or game-strength test.

The fixture oracle consumes only declared own lists and unordered batches of
already observed own cards. It checks a small, explicit zone-movement history;
it never constructs a draw order or reads an opponent's private cards. These
histories use lawful draw/resource/play/defeat primitives and conserved card
counts, but are not rules-engine games or validated implementations of TST cards.
"""
from collections import Counter
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np

JEPA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(JEPA))
import features as F
import model as M
import own_deck as O
import own_deck_model as D

TARGET_A, TARGET_B = "TST_001", "TST_002"


def composition_fingerprint(counts):
    pairs = sorted((code, int(count)) for code, count in counts.items() if count)
    return hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()


def declared_counts(fixture):
    return Counter({entry["id"]: entry["count"] for entry in fixture["hello"]["deck"]["deck"]})


def printed_cards():
    cards = []
    for n in range(1, 18):
        cards.append(dict(setId=dict(set="TST", number=n), setCodes=[],
                          cost=1 if n in (1, 2) else 8 if n == 17 else min(n, 8),
                          power=1 if n in (1, 2) else 2, hp=1 if n in (1, 2) else 3,
                          types=["unit"], aspects=["command"], arena="ground",
                          keywords=["ambush"] if n in (1, 2) else [],
                          traits=["rebel" if n == 1 else "imperial" if n == 2 else "trooper"]))
    # Shared played unit and common resource must be affordable in the fixture's first round.
    cards[4]["cost"] = 1
    for n, type_ in ((800, "leader"), (801, "base"), (802, "leader"), (803, "base")):
        cards.append(dict(setId=dict(set="TST", number=n), setCodes=[], cost=0,
                          power=0, hp=30 if type_ == "base" else 0, types=[type_],
                          aspects=["command"], arena="ground", keywords=[], traits=[]))
    cards.append(dict(setId=dict(set="TST", number=900), setCodes=[], cost=1,
                      power=1, hp=3, types=["unit"], aspects=[], arena="ground",
                      keywords=[], traits=[]))
    return cards


def fixture_db(cards):
    """Printed synthetic metadata only; no engine, files or hidden card instances."""
    db = {}
    for card in cards:
        info = F.CardInfo()
        for key in F.CardInfo.__slots__:
            setattr(info, key, 0)
        for key in ("cost", "power", "hp"):
            setattr(info, key, card[key])
        for key in ("unit", "event", "upgrade", "leader", "base", "token"):
            setattr(info, key, key in card["types"])
        info.space = card.get("arena") == "space"
        info.keywords = sum(1 << bit for bit, key in enumerate(F.KEYWORDS) if key in card["keywords"])
        db[O.normalized_code(card["setId"])] = info
    return db


def _reference(instance, code):
    return {"id": instance, "s": code, "n": code}


def make_fixture(depleted=TARGET_A):
    own = [{"id": f"TST_{n:03}", "count": 2 if n == 17 else 3} for n in range(1, 18)]
    refs = {"resource-one": _reference("own-seen-a", depleted),
            "discard-one": _reference("own-seen-b", depleted),
            "hand-one": _reference("own-hand-c", "TST_003"),
            "hand-two": _reference("own-hand-d", "TST_004"),
            "board-one": _reference("own-board-e", "TST_005"),
            "resource-common": _reference("own-seen-f", "TST_006"),
            "resource-two": _reference("own-seen-g", depleted),
            "hand-three": _reference("own-hand-h", "TST_007")}
    move = lambda key, source, destination: dict(kind="move", id=refs[key]["id"], source=source, destination=destination)
    history = [
        dict(kind="observed-own-draw", cards=[copy.deepcopy(refs[k]) for k in ("resource-one", "discard-one", "hand-one", "hand-two", "board-one", "resource-common")]),
        move("resource-one", "hand", "resource"), move("resource-common", "hand", "resource"),
        move("board-one", "hand", "ground"), move("discard-one", "hand", "ground"),
        move("discard-one", "ground", "discard"),
        dict(kind="observed-own-draw", cards=[copy.deepcopy(refs[k]) for k in ("resource-two", "hand-three")]),
        move("resource-two", "hand", "resource"),
    ]
    board = {**refs["board-one"], "p": 2, "h": 3, "d": 0, "x": 0}
    me = dict(base={"id": "own-base", "s": "TST_801", "hp": 30, "d": 0},
              leader={"id": "own-leader", "s": "TST_800", "dep": 0, "x": 0},
              hand=[refs[k] for k in ("hand-one", "hand-two", "hand-three")], handCount=3,
              resources=[refs[k] for k in ("resource-one", "resource-common", "resource-two")],
              res={"ready": 3, "total": 3}, discard=[refs["discard-one"]], deck=42, ground=[board], space=[])
    # Open board only. The 1/3 enemy survives the fixture's 1/1 Ambush unit with one damage.
    them = dict(base={"id": "public-other-base", "s": "TST_803", "hp": 30, "d": 0},
                leader={"id": "public-other-leader", "s": "TST_802", "dep": 0, "x": 0},
                handCount=3, res={"ready": 3, "total": 3}, discard=[], deck=42,
                ground=[dict(id="public-other-unit", s="TST_900", p=1, h=3, d=1, x=0)], space=[])
    message = dict(you="p1", prompt={"type": "actionWindow", "actionWindow": True},
                   state={"phase": "action", "round": 2, "initiative": "p1", "players": {"p1": me, "p2": them}},
                   actions=[dict(i=0, kind="button", label="Pass", arg="pass"),
                            dict(i=1, kind="card", label="Play shared hand card", card={**refs["hand-one"], "zone": "hand", "ctl": "p1"}),
                            dict(i=2, kind="card", label="Attack with shared unit", card={**board, "zone": "groundArena", "ctl": "p1"})])
    return {"name": "depleted-" + depleted, "hello": {"you": "p1", "deck": {"deck": own}, "cards": printed_cards()},
            "history": history, "message": message}


def build_pairs():
    """Two depletion histories, plus an independently declared sibling own list."""
    first, second = make_fixture(TARGET_A), make_fixture(TARGET_B)
    sibling = copy.deepcopy(first)
    sibling["name"] = "sibling-own-list-less-TST002-more-TST017"
    sibling["hello"]["deck"]["deck"][1]["count"] = 2
    sibling["hello"]["deck"]["deck"][-1]["count"] = 3
    return first, second, sibling


def oracle_remaining(fixture):
    """Fixture-only conservation oracle, deliberately outside every policy path.

    Supports only the explicitly listed own transitions below. No order within
    any observed draw batch is retained, and unsupported histories raise.
    """
    remaining, instances = declared_counts(fixture), {}
    allowed = {("hand", "resource"), ("hand", "ground"), ("ground", "discard")}
    for event in fixture["history"]:
        if event["kind"] == "observed-own-draw":
            for card in event["cards"]:
                ident, code = card["id"], card["s"]
                if ident in instances or remaining[code] <= 0:
                    raise ValueError("duplicate own instance or impossible own draw")
                remaining[code] -= 1
                instances[ident] = (code, "hand")
        elif event["kind"] == "move":
            current = instances.get(event["id"])
            if current is None or current[1] != event["source"] or (event["source"], event["destination"]) not in allowed:
                raise ValueError("unsupported or inconsistent own zone movement")
            instances[event["id"]] = (current[0], event["destination"])
        else:
            raise ValueError("unsupported fixture event")
    me = fixture["message"]["state"]["players"]["p1"]
    visible = {}
    for key, zone in (("hand", "hand"), ("resources", "resource"), ("ground", "ground"), ("discard", "discard")):
        for card in me[key]:
            if card["id"] in visible:
                raise ValueError("own instance appears in multiple zones")
            visible[card["id"]] = (card["s"], zone)
    if instances != visible or sum(remaining.values()) != me["deck"]:
        raise ValueError("history and current own observation do not reconcile")
    return +remaining


def contract_inputs(fixture, variant="original-plus-remaining"):
    """Actual encoder inputs only: fixture oracle and histories are excluded."""
    encoded = F.encode(fixture["message"], fixture_db(fixture["hello"]["cards"]))
    deck = O.as_array(O.encode_hello(fixture["hello"], variant))
    return encoded, deck


def model_forward(net, encoded, deck):
    z, predicted = net.forward(encoded["state"][None], encoded["tok_ids"][None].astype(np.int64),
                               encoded["tok_feats"][None], encoded["tok_mask"][None],
                               encoded["actions"][None], encoded["aids"][None].astype(np.int64), own_deck=deck)
    return z, predicted, net.value(predicted)


def boundary_report():
    first, second, sibling = build_pairs()
    records = []
    for fixture in (first, second, sibling):
        original, remaining = declared_counts(fixture), oracle_remaining(fixture)
        encoded, deck = contract_inputs(fixture)
        records.append(dict(name=fixture["name"], original_fingerprint=composition_fingerprint(original),
                            remaining_fingerprint=composition_fingerprint(remaining), original_count=sum(original.values()),
                            remaining_count=sum(remaining.values()), remaining_target_A=remaining[TARGET_A],
                            remaining_target_B=remaining[TARGET_B], probability_next_target_A=float(Fraction(remaining[TARGET_A], sum(remaining.values()))),
                            original_known=bool(deck[0, 0, 3]), remaining_known=bool(deck[0, 1, 3]),
                            encoded_sha256=hashlib.sha256(b"".join(encoded[k].tobytes() for k in sorted(encoded))).hexdigest(),
                            context_sha256=hashlib.sha256(deck.tobytes()).hexdigest()))
    weights, meta = M.load_safetensors(JEPA / "models/tx-t10.safetensors")
    net = D.NumpyOwnDeckTx({**weights, **D.supplement()}, {**meta, "format": D.FORMAT})
    outputs = [model_forward(net, *contract_inputs(fixture)) for fixture in (first, second)]
    return dict(schema="jepa-remaining-boundary/1", evidence="synthetic input and numerical representation boundary only",
                remaining_supported=False, oracle_is_policy_input=False, hidden_draw_order_constructed=False,
                gameplay_strength_claim=False, records=records,
                depletion_pair_max_abs_delta={key: float(np.max(np.abs(a - b))) for key, a, b in zip(("z", "predicted_latents", "value_logits"), *outputs)},
                limitation="The current original-only context cannot distinguish these different remaining multisets; remaining stays explicitly unknown.")


class RemainingBoundaryTests(unittest.TestCase):
    def test_history_oracle_conserves_original_and_changes_draw_probabilities(self):
        first, second, _ = build_pairs()
        self.assertEqual(declared_counts(first), declared_counts(second))
        self.assertEqual(sum(declared_counts(first).values()), 50)
        self.assertTrue(all(0 < n <= 3 for n in declared_counts(first).values()))
        a, b = oracle_remaining(first), oracle_remaining(second)
        self.assertEqual((sum(a.values()), sum(b.values())), (42, 42))
        self.assertEqual((a[TARGET_A], b[TARGET_A], a[TARGET_B], b[TARGET_B]), (0, 3, 3, 0))
        self.assertEqual((Fraction(a[TARGET_A], 42), Fraction(b[TARGET_A], 42)), (0, Fraction(1, 14)))
        self.assertNotEqual(composition_fingerprint(a), composition_fingerprint(b))

    def test_different_resource_discard_identities_are_currently_input_indistinguishable(self):
        first, second, _ = build_pairs()
        me = lambda f: f["message"]["state"]["players"]["p1"]
        self.assertNotEqual(me(first)["resources"], me(second)["resources"])
        self.assertNotEqual(me(first)["discard"], me(second)["discard"])
        for key in ("hand", "ground", "space", "handCount", "res", "deck"):
            self.assertEqual(me(first)[key], me(second)[key])
        a, b = contract_inputs(first), contract_inputs(second)
        for key in a[0]:
            np.testing.assert_array_equal(a[0][key], b[0][key], err_msg=key)
        np.testing.assert_array_equal(a[1], b[1])
        self.assertEqual(tuple(a[1][0, 1, 1:4]), (1., 1., 0.))
        self.assertTrue(np.all(a[1][0, 1, 4:] == 0))

    def test_actual_frozen_scaffold_outputs_match_for_the_indistinguishable_pair(self):
        report = boundary_report()
        self.assertEqual(report["depletion_pair_max_abs_delta"], dict(z=0., predicted_latents=0., value_logits=0.))
        self.assertFalse(report["remaining_supported"])
        self.assertFalse(report["oracle_is_policy_input"])

    def test_same_observation_different_original_counts_changes_original_context(self):
        first, _, sibling = build_pairs()
        self.assertEqual(first["message"], sibling["message"])
        self.assertNotEqual(declared_counts(first), declared_counts(sibling))
        self.assertEqual(sum(declared_counts(sibling).values()), 50)
        self.assertTrue(all(n <= 3 for n in declared_counts(sibling).values()))
        self.assertNotEqual(oracle_remaining(first), oracle_remaining(sibling))
        a, b = contract_inputs(first), contract_inputs(sibling)
        for key in a[0]:
            np.testing.assert_array_equal(a[0][key], b[0][key])
        self.assertFalse(np.array_equal(a[1], b[1]))
        np.testing.assert_array_equal(a[1][:, 1], b[1][:, 1])

    def test_permutation_and_wrong_own_control_use_only_declared_owned_lists(self):
        first, _, sibling = build_pairs()
        self.assertNotIn("opponent", first["hello"])
        self.assertNotIn("opponent", sibling["hello"])
        shuffled = copy.deepcopy(first)
        shuffled["hello"]["deck"]["deck"].reverse()
        shuffled["hello"]["cards"].reverse()
        np.testing.assert_array_equal(contract_inputs(first)[1], contract_inputs(shuffled)[1])
        wrong_own = copy.deepcopy(first)
        wrong_own["hello"]["deck"] = copy.deepcopy(sibling["hello"]["deck"])
        np.testing.assert_array_equal(contract_inputs(wrong_own)[1], contract_inputs(sibling)[1])
        self.assertFalse(np.array_equal(contract_inputs(first)[1], contract_inputs(wrong_own)[1]))

    def test_fixture_oracle_rejects_inconsistent_or_unsupported_own_histories(self):
        first, _, _ = build_pairs()
        for mutation in ("duplicate", "impossible-count", "unsupported", "wrong-current-zone"):
            bad = copy.deepcopy(first)
            if mutation == "duplicate":
                bad["history"][0]["cards"].append(copy.deepcopy(bad["history"][0]["cards"][0]))
            elif mutation == "impossible-count":
                bad["hello"]["deck"]["deck"][0]["count"] = 2
            elif mutation == "unsupported":
                bad["history"][1]["destination"] = "unknown-private-zone"
            else:
                bad["message"]["state"]["players"]["p1"]["resources"][0]["s"] = TARGET_B
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                oracle_remaining(bad)

    def test_rule_effect_quantities_costs_and_targets_are_an_explicit_semantic_gap(self):
        first, _, _ = build_pairs()
        a, b = copy.deepcopy(first), copy.deepcopy(first)
        a["hello"]["cards"][0]["abilities"] = [dict(cost={"exhaust": True}, effect={"type": "damage", "amount": 1, "target": "enemy-unit"})]
        b["hello"]["cards"][0]["abilities"] = [dict(cost={"resources": 2}, effect={"type": "damage", "amount": 3, "target": "enemy-base"})]
        _, da = contract_inputs(a)
        _, db = contract_inputs(b)
        np.testing.assert_array_equal(da, db)
        self.assertEqual(float(da[0, 0, 3]), 1.)  # Known printed metadata is not rules-effect coverage.


if __name__ == "__main__":
    unittest.main()
