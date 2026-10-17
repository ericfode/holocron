"""Bounded own-deck correctness tests; no games, training run or downloads."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import model as M
import own_deck as O
import own_deck_model as D
import tx_model as X

ROOT = Path(__file__).resolve().parent
WASM = ROOT / "wasm"


def inputs(e):
    t = min(e["tokens"]["n"], 24)
    n = e["actions"]["n"]
    return (np.asarray(e["state"],np.float32).reshape(1,73),
            np.asarray(e["tokens"]["ids"][:t]+[0]*(24-t),np.int64).reshape(1,24),
            np.asarray(e["tokens"]["feats"][:t*21]+[0.]*(21*(24-t)),np.float32).reshape(1,24,21),
            np.asarray([1.]*t+[0.]*(24-t),np.float32).reshape(1,24),
            np.asarray(e["actions"]["rows"],np.float32).reshape(1,n,62),
            np.asarray(e["actions"]["ids"],np.int64).reshape(1,n))


class OwnDeckContractTests(unittest.TestCase):
    def test_rust_contract_bit_for_bit(self):
        corpus=json.loads((WASM/"controller/fixtures/own-deck-contract.json").read_text())
        for case in corpus["cases"]:
            with self.subTest(case=case["name"]):
                got=O.encode_hello(case["hello"],case["variant"])
                self.assertEqual(got["version"],case["expected"]["version"])
                self.assertEqual(got["variant"],case["expected"]["variant"])
                np.testing.assert_array_equal(np.asarray(got["features"],np.float32).view(np.uint32),case["expected_bits"])

    def test_input_rejects_bad_contract_and_nonfinite(self):
        for bad in ({"version":True,"variant":"original","features":[0.]*414},
                    {"version":1,"variant":"original","features":[0.]*413},
                    {"version":1,"variant":"original","features":[float("nan")]*414}):
            with self.subTest(bad=bad["version"]):
                with self.assertRaises(ValueError): O.as_array(bad)

    def test_no_distinct_card_capacity_limit(self):
        deck={"deck":[{"id":f"SOR_{n:03}","count":2} for n in range(120)]}
        context=O.as_array(O.encode_hello({"deck":deck,"cards":[]}))[0,0]
        self.assertEqual(float(context[4]),4.)
        self.assertEqual(float(context[5]),4.)
        self.assertEqual(float(context[6]),2.)
        for start,end in ((50,114),(114,146),(146,207)):
            self.assertAlmostEqual(float(context[start:end].sum()),4.,places=6)

    def test_factor_pool_matches_shared_embedding(self):
        w,_=M.load_safetensors(ROOT/"models/tx-t10.safetensors")
        hello={"deck":{"deck":[{"id":"SOR_042","count":3},{"id":"SOR_043","count":2}]},"cards":[]}
        deck=O.as_array(O.encode_hello(hello))
        expected=(3*M.embed(w,np.asarray(O.F.hash_id("card:SOR_042")))+2*M.embed(w,np.asarray(O.F.hash_id("card:SOR_043"))))/60
        np.testing.assert_allclose(D.pooled_identity(w,deck)[0,0],expected,atol=1e-8,rtol=2e-6)


class OwnDeckModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.weights,cls.meta=M.load_safetensors(ROOT/"models/tx-t10.safetensors")
        cls.ext={**cls.weights,**D.supplement()}
        cls.ref=json.loads((WASM/"tests/fixtures/runtime-reference.json").read_text())
        cls.deckref=json.loads((WASM/"tests/fixtures/own-deck-runtime-reference.json").read_text())

    def test_legacy_fixture_numbers_unchanged(self):
        net=X.NumpyTx(self.weights,self.meta)
        for case in self.ref["vectors"]:
            with self.subTest(case=case["name"]):
                z,pred=net.forward(*inputs(case["encoded"]))
                expect=case["networks"]["model"]
                self.assertLess(abs(float(net.value(z)[0])-expect["context"]["valueLogit"]),1e-5)
                for hi,h in enumerate(net.horizons):
                    np.testing.assert_allclose(net.value(pred[0,:,hi]),expect["predictions"][str(h)]["logits"],atol=1e-5,rtol=0)

    def test_cached_action_path_retains_deck(self):
        net=D.NumpyOwnDeckTx(self.ext,self.meta)
        case=self.deckref["vectors"][7]
        state,ids,feats,mask,act,aid=inputs(case["encoded"])
        deck=case["encoded"]["own_deck"]
        z,pred=net.forward(state,ids,feats,mask,act,aid,own_deck=deck)
        np.testing.assert_allclose(net.encode(state,ids,feats,mask,own_deck=deck),z,atol=1e-7,rtol=0)
        packed=net.action(act[0],aid[0])
        for hi,h in enumerate(net.horizons):
            np.testing.assert_allclose(net.predict(z,packed,h),pred[0,:,hi],atol=2e-6,rtol=0)

    def test_all_24_live_slots_survive_deck_context(self):
        net=D.NumpyOwnDeckTx(self.ext,self.meta)
        source=self.ref["vectors"][-1]
        args=list(inputs(source["encoded"]))
        x,kval=net._initial_context(*args[:4],O.neutral_features())
        self.assertEqual(x.shape,(1,27,64))
        self.assertEqual(float(kval.sum()),27.)
        z,_=net.forward(*args)
        args[2]=args[2].copy()
        args[2][0,23,0]+=1.0
        changed,_=net.forward(*args)
        self.assertGreater(float(np.max(abs(z-changed))),1e-7)

    def test_deck_reaches_state_actions_value_and_roundtrip(self):
        net=D.NumpyOwnDeckTx(self.ext,self.meta)
        case=self.deckref["vectors"][7]
        args=inputs(case["encoded"])
        z,pred=net.forward(*args,own_deck=case["encoded"]["own_deck"])
        zn,pn=net.forward(*args,own_deck=O.neutral_features())
        self.assertGreater(float(np.max(abs(z-zn))),1e-5)
        self.assertGreater(float(np.max(abs(pred-pn))),1e-5)
        self.assertGreater(float(np.max(abs(net.value(pred)-net.value(pn)))),1e-6)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"own-deck.safetensors"
            M.save_safetensors(path,self.ext,{**self.meta,"format":D.FORMAT})
            loaded,_=X.load(path)
            zl,pl=loaded.forward(*args,own_deck=case["encoded"]["own_deck"])
            np.testing.assert_array_equal(zl,z)
            np.testing.assert_array_equal(pl,pred)

    def test_torch_matches_numpy_and_updates_only_extra_tensors(self):
        try: import torch
        except ImportError: self.skipTest("PyTorch unavailable; no download/install performed")
        torch.set_num_threads(1)
        case=self.deckref["vectors"][7]
        args=inputs(case["encoded"])
        deck=O.as_array(case["encoded"]["own_deck"])
        net=D.NumpyOwnDeckTx(self.ext,self.meta)
        z,pred=net.forward(*args,own_deck=deck)
        w={k:torch.tensor(v,requires_grad=k in D.supplemental_shapes()) for k,v in self.ext.items()}
        ta=[torch.as_tensor(a) for a in args]
        tz,tp=D.run_torch(w,self.meta,*ta,own_deck=torch.as_tensor(deck))
        np.testing.assert_allclose(tz.detach().numpy(),z,atol=3e-6,rtol=0)
        np.testing.assert_allclose(tp.detach().numpy(),pred,atol=4e-6,rtol=0)
        np.testing.assert_allclose(D.value_torch(w,tp).detach().numpy(),net.value(pred),atol=3e-6,rtol=0)
        # One synthetic diagnostic gradient, no game examples or broad optimizer run.
        loss=(tz**2).mean()+(tp**2).mean()
        loss.backward()
        before={k:v.copy() for k,v in self.ext.items()}
        for k in D.supplemental_shapes():
            self.assertTrue(torch.isfinite(w[k].grad).all())
            self.assertGreater(float(w[k].grad.abs().sum()),0.)
        opt=torch.optim.SGD([w[k] for k in D.supplemental_shapes()],lr=1e-4)
        opt.step()
        for k in self.weights:
            np.testing.assert_array_equal(w[k].detach().numpy(),before[k])
        trained={k:v.detach().numpy() for k,v in w.items()}
        self.assertGreater(max(float(abs(trained[k]-before[k]).max()) for k in D.supplemental_shapes()),0.)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"one-step.safetensors"
            M.save_safetensors(path,trained,{**self.meta,"format":D.FORMAT})
            loaded,_=X.load(path)
            az,ap=loaded.forward(*args,own_deck=deck)
            bz,bp=D.run_torch(w,self.meta,*ta,own_deck=torch.as_tensor(deck))
            np.testing.assert_allclose(az,bz.detach().numpy(),atol=4e-6,rtol=0)
            np.testing.assert_allclose(ap,bp.detach().numpy(),atol=5e-6,rtol=0)
            extra=Path(td)/"supplement.safetensors"
            M.save_safetensors(extra,{k:trained[k] for k in D.supplemental_shapes()},{"format":D.FORMAT})
            ew,em=D.load_extended(ROOT/"models/tx-t10.safetensors",extra)
            ez,ep=D.NumpyOwnDeckTx(ew,em).forward(*args,own_deck=deck)
            np.testing.assert_array_equal(ez,az)
            np.testing.assert_array_equal(ep,ap)


if __name__=="__main__": unittest.main()
