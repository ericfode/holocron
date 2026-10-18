"""Own-deck actor plumbing only: synthetic observations and fake inference, no games."""
import copy
import unittest
from unittest.mock import patch

import numpy as np

import features as F
import jepa_bot as J
import own_deck as O


class FakeNet:
    horizons = (1, 4, "s")

    def __init__(self):
        self.calls = []

    def encode(self, state, ids, feats, mask):
        self.calls.append(((state, ids, feats, mask), None))
        return np.zeros((len(state), 96), np.float32)

    def action(self, actions, aids):
        return np.zeros((len(actions), 1), np.float32)

    def predict(self, z, action, horizon):
        return np.zeros((len(action), 96), np.float32)

    def value(self, z):
        return np.zeros(z.shape[:-1], np.float32)


class OwnNet(FakeNet):
    supports_own_deck = True

    def encode(self, state, ids, feats, mask, *, own_deck):
        self.calls.append(((state, ids, feats, mask), own_deck.copy()))
        return np.zeros((len(state), 96), np.float32)


def hello(seat="p1"):
    return {"you": seat, "deck": {"deck": [{"id": "SOR_042", "count": 3}]},
            "cards": [{"setId": {"set": "SOR", "number": 42}, "setCodes": [],
                       "cost": 2, "power": 3, "hp": 4, "types": ["unit"],
                       "keywords": [], "aspects": ["command"], "traits": ["Rebel"]}]}


def message(seat="p1"):
    return {"you": seat, "prompt": {"type": "actionWindow", "actionWindow": True},
            "state": {"phase": "action", "round": 1, "players": {}},
            "actions": [{"i": 0, "kind": "button", "label": "A"},
                        {"i": 1, "kind": "button", "label": "B"}]}


def player(net=None, **kwargs):
    net = net or OwnNet()
    with patch.object(J.X, "load", return_value=(net, {})):
        return J.JepaPlayer("synthetic", {}, **kwargs), net


class OwnDeckPlayerTests(unittest.TestCase):
    def assert_own(self, net, source=None, variant="original", batch=1):
        expected = O.as_array(O.encode_hello(source or hello(), variant), batch)
        np.testing.assert_array_equal(net.calls[-1][1], expected)

    def assert_unknown(self, net, variant="original", batch=1):
        expected = O.as_array(O.encode_hello({}, variant), batch)
        np.testing.assert_array_equal(net.calls[-1][1], expected)
        self.assertEqual(float(net.calls[-1][1][0, 0, 3]), 0.)
        self.assertTrue(np.all(net.calls[-1][1][..., 50:] == 0))

    def test_live_original_comes_from_own_hello_only(self):
        p, net = player()
        h = hello()
        h.update(opponent={"deck": [{"id": "SOR_999", "count": 50}]}, drawOrder=["SOR_999"])
        p.new_game(0, h)
        p.think(message())
        self.assert_own(net)
        h["deck"]["deck"][0]["count"] = 49
        p.think(message())
        self.assert_own(net)  # Aggregate features do not retain mutable hello objects.

    def test_new_game_clears_context_and_missing_list_is_explicitly_unknown(self):
        p, net = player()
        p.new_game(0, hello())
        p.new_game(1)
        self.assertIsNone(p.own_deck_seat)
        p.think(message())
        self.assert_unknown(net)
        p.new_game(2, {"you": "p1", "cards": hello()["cards"]})
        p.think(message())
        self.assert_unknown(net)

    def test_opponent_perspective_reply_never_receives_root_own_bag(self):
        p, net = player(plan={"reply_by": 1})
        p.new_game(0, hello())
        msg = message()
        r = {"actor": "p2", "prompt": msg["prompt"], "state": msg["state"]}
        p.reply_pick(r, "p1", msg["actions"])
        self.assert_unknown(net)
        p.plan_cfg["reply_by"] = 2
        p.reply_pick(r, "p1", msg["actions"])
        self.assert_own(net)

    def test_missing_actor_role_never_receives_root_own_bag(self):
        p, net = player()
        p.new_game(0, hello())
        msg = message()
        del msg["you"]
        p.think(msg)
        self.assert_unknown(net)
        h = hello()
        del h["you"]
        p.new_game(1, h)
        p.think(message())
        self.assert_unknown(net)

    def test_neutral_and_unsupported_remaining_variants_are_explicit(self):
        p, net = player(own_deck="neutral")
        p.new_game(0, hello())
        p.think(message())
        np.testing.assert_array_equal(net.calls[-1][1], O.neutral_features(1))
        p, net = player(own_deck="original-plus-remaining")
        p.new_game(0, hello())
        p.think(message())
        self.assert_own(net, variant="original-plus-remaining")
        self.assertEqual(tuple(net.calls[-1][1][0, 1, 1:4]), (1., 1., 0.))

    def test_legacy_network_keeps_identical_four_positional_arguments(self):
        p, net = player(FakeNet())
        p.new_game(0, hello())
        msg = message()
        p.think(msg)
        e = F.encode(msg, {})
        expected = (e["state"][None], e["tok_ids"][None].astype(np.int64), e["tok_feats"][None], e["tok_mask"][None])
        self.assertIsNone(p.own_deck_context)
        self.assertIsNone(net.calls[-1][1])
        for actual, expected in zip(net.calls[-1][0], expected):
            np.testing.assert_array_equal(actual, expected)

    def test_judged_boards_use_root_context_even_when_opponent_acts(self):
        p, net = player()
        p.new_game(0, hello())
        msg = message()
        rs = [{"actor": "p2", "state": msg["state"]}, {"actor": "p1", "state": msg["state"],
               "prompt": msg["prompt"], "actions": msg["actions"]}]
        values = p.judge_boards(rs, msg)
        self.assertEqual(values.shape, (2,))
        self.assert_own(net, batch=2)

    def test_sim_v_batch_uses_root_context(self):
        p, net = player()
        p.new_game(0, hello())
        msg = message()
        leaf = {"actor": "p2", "state": msg["state"], "prompt": msg["prompt"], "actions": msg["actions"]}
        with patch.object(p, "real_next", return_value=leaf):
            values = p.sim_scores(msg, lambda request: {}, ["sim-v"])
        self.assertEqual(values["sim-v"].shape, (2,))
        self.assert_own(net, batch=2)

    def test_plan_leaf_batch_uses_root_context(self):
        p, net = player(plan={"roots": 1, "lines": 1, "secs": 1})
        p.new_game(0, hello())
        msg = message()
        leaf = {"actor": "p2", "state": copy.deepcopy(msg["state"]), "prompt": msg["prompt"], "actions": msg["actions"]}
        leaf["state"]["round"] = 2
        p._last_pre, p._last_line = None, []
        with patch.object(p, "plan_line", return_value=([0], [], leaf)):
            result = p.plan_moves(msg, lambda request: {}, np.asarray([0.8, 0.2]))
        self.assertIsNotNone(result)
        self.assert_own(net)

    def test_extended_window_and_judge_work_with_legacy_main_net(self):
        legacy, window, judge = FakeNet(), OwnNet(), OwnNet()
        with patch.object(J.X, "load", side_effect=[(legacy, {}), (judge, {}), (window, {})]):
            p = J.JepaPlayer("legacy", {}, plan_model="judge", window_model="window")
        p.new_game(0, hello())
        p.think(message())
        self.assert_own(window)
        p.judge_boards([{"actor": "p2", "state": message()["state"]}], message())
        self.assert_own(judge)


if __name__ == "__main__":
    unittest.main()
