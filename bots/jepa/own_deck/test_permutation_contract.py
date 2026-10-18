"""Original deck declarations are unordered multisets with preserved counts.

This invariance applies to main-list serialization, duplicate grouping and
printed reprint aliases. It does not erase meaningful future effect-instruction
order or observed top/bottom positions, which need separate typed inputs.

No optimizer, training, games, opponents, graph builds or paid work run here.
"""
import os
for _thread_var in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","VECLIB_MAXIMUM_THREADS","MKL_NUM_THREADS"):
    os.environ[_thread_var]="1"

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import model as M
import own_deck as O
import own_deck_model as D

SEED=61423
PERMUTATIONS_PER_FORM=64
COUNTS=(3,2,3,1,3,2)
RUST_ENCODER=ROOT/"wasm/controller/target/debug/examples/own_deck_encode"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog():
    cards=[]
    for i,cost in enumerate((0,1,2,4,6,8)):
        cards.append(dict(setId={"set":"PER","number":i+1},
            setCodes=[{"set":"PER","number":i+1},{"set":"ALT","number":101+i},{"set":"RPT","number":201+i}],
            cost=cost,power=i+1,hp=i+3,types=["unit" if i%2==0 else "event"],
            arena="space" if i==4 else "ground",aspects=[O.ASPECTS[i]],
            keywords=["raid","ambush"] if i==2 else [],traits=["Permutation fixture",f"Group {i}"]))
    return cards


def base_hello():
    return dict(deck={"deck":[{"id":f"PER_{i+1:03}","count":n} for i,n in enumerate(COUNTS)]},cards=catalog())


def alias(i,rng):
    text=(f"PER_{i+1:03}",f"ALT_{101+i:03}",f"RPT_{201+i:03}")[int(rng.integers(3))]
    return " "+text.lower()+" " if rng.integers(2) else text


def equivalent_cases():
    rng=np.random.default_rng(SEED)
    cases=[]
    orders=set()
    for form in ("grouped","expanded","split-reprints","expanded-reprints"):
        for repetition in range(PERMUTATIONS_PER_FORM):
            entries=[]
            if form=="grouped":
                order=tuple(rng.permutation(len(COUNTS)).tolist())
                while order in orders: order=tuple(rng.permutation(len(COUNTS)).tolist())
                orders.add(order)
                entries=[{"id":f"PER_{i+1:03}","count":COUNTS[i]} for i in order]
            elif form=="expanded":
                entries=[{"id":f"PER_{i+1:03}","count":1} for i,n in enumerate(COUNTS) for _ in range(n)]
                rng.shuffle(entries)
            elif form=="split-reprints":
                for i,count in enumerate(COUNTS):
                    remaining=count
                    while remaining:
                        take=int(rng.integers(1,remaining+1))
                        entries.append({"id":alias(i,rng),"count":take})
                        remaining-=take
                rng.shuffle(entries)
            else:
                entries=[{"id":alias(i,rng),"count":1} for i,n in enumerate(COUNTS) for _ in range(n)]
                rng.shuffle(entries)
            hello=base_hello(); hello["deck"]["deck"]=entries
            rng.shuffle(hello["cards"])
            for card in hello["cards"]:
                rng.shuffle(card["setCodes"])
            cases.append(dict(name=f"{form}/{repetition:02}",variant="original",hello=hello))
    return cases


def changed_cases():
    extra=base_hello(); extra["deck"]["deck"][0]["count"]+=1
    transfer=base_hello()
    transfer["deck"]["deck"][0]["count"]-=1
    transfer["deck"]["deck"][1]["count"]+=1
    return [dict(name="extra-copy",variant="original",hello=extra),
            dict(name="same-total-copy-transfer",variant="original",hello=transfer)]


def feature(case):
    return O.as_array(O.encode_hello(case["hello"],case.get("variant","original")))[0]


def bits(value):
    return np.asarray(value,np.float32).reshape(-1).view(np.uint32)


def fixed_inputs():
    fixture=json.loads((ROOT/"wasm/tests/fixtures/runtime-reference.json").read_text())
    e=next(v["encoded"] for v in fixture["vectors"] if v["name"]=="window-p1")
    t=min(e["tokens"]["n"],24); k=e["actions"]["n"]
    return (np.asarray(e["state"],np.float32).reshape(1,73),
            np.asarray(e["tokens"]["ids"][:t]+[0]*(24-t),np.int64).reshape(1,24),
            np.asarray(e["tokens"]["feats"][:21*t]+[0.]*(21*(24-t)),np.float32).reshape(1,24,21),
            np.asarray([1.]*t+[0.]*(24-t),np.float32).reshape(1,24),
            np.asarray(e["actions"]["rows"],np.float32).reshape(1,k,62),
            np.asarray(e["actions"]["ids"],np.int64).reshape(1,k))


def model_outputs(net,deck):
    z,pred=net.forward(*fixed_inputs(),own_deck=deck)
    return dict(z=z,action_latents=pred,context_value=net.value(z),action_values=net.value(pred))


def rust_batch(cases):
    payload=json.dumps({"cases":cases},separators=(",",":"))
    process=subprocess.run([str(RUST_ENCODER)],input=payload,text=True,capture_output=True,timeout=10,check=True)
    return json.loads(process.stdout)["cases"]


class PermutationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=equivalent_cases()
        cls.reference=feature(dict(hello=base_hello()))
        cls.features=[feature(case) for case in cls.cases]

    def test_256_reorderings_groupings_and_alias_forms_have_identical_feature_bits(self):
        self.assertEqual(len(self.cases),256)
        for form in ("grouped","expanded","split-reprints","expanded-reprints"):
            serialized={json.dumps(c["hello"]["deck"]["deck"],sort_keys=True) for c in self.cases if c["name"].startswith(form+"/")}
            self.assertGreaterEqual(len(serialized),50)
        for case,encoded in zip(self.cases,self.features):
            with self.subTest(case=case["name"]):
                np.testing.assert_array_equal(bits(encoded),bits(self.reference))
        self.assertEqual(float(self.reference[0,3]),1.)

    def test_copy_multiplicity_is_not_reduced_to_a_set(self):
        extra,transfer=[feature(case) for case in changed_cases()]
        self.assertFalse(np.array_equal(extra,self.reference))
        self.assertFalse(np.array_equal(transfer,self.reference))
        self.assertNotEqual(float(extra[0,4]),float(self.reference[0,4]))
        self.assertEqual(float(transfer[0,4]),float(self.reference[0,4]))
        for start,end in ((50,114),(114,146),(146,207)):
            self.assertAlmostEqual(float(extra[0,start:end].sum()-self.reference[0,start:end].sum()),1/60,places=6)
            self.assertFalse(np.array_equal(transfer[0,start:end],self.reference[0,start:end]))

    def test_pooled_identity_and_two_role_tokens_have_no_deck_entry_positions(self):
        weights,meta=D.load_extended(ROOT/"models/tx-t10.safetensors",ROOT/"wasm/generated-own-deck/deck-init.safetensors")
        net=D.NumpyOwnDeckTx(weights,meta)
        initial,kval=net._initial_context(*fixed_inputs()[:4],self.reference)
        pooled=D.pooled_identity(weights,self.reference)
        self.assertEqual(initial.shape,(1,27,64))
        self.assertEqual(kval.shape,(1,27))
        for encoded in self.features:
            np.testing.assert_array_equal(D.pooled_identity(weights,encoded),pooled)
            actual,mask=net._initial_context(*fixed_inputs()[:4],encoded)
            np.testing.assert_array_equal(actual,initial)
            np.testing.assert_array_equal(mask,kval)
        # Original/remaining role slots are fixed; their distinction is not list ordering.
        self.assertFalse(np.array_equal(initial[:,-2],initial[:,-1]))

    def test_frozen_model_latents_all_action_horizons_and_values_are_invariant(self):
        for checkpoint in ("tx-t10.safetensors","tx-t10-e.safetensors"):
            weights,meta=D.load_extended(ROOT/"models"/checkpoint,ROOT/"wasm/generated-own-deck/deck-init.safetensors")
            net=D.NumpyOwnDeckTx(weights,meta)
            expected=model_outputs(net,self.reference)
            for case,encoded in zip(self.cases,self.features):
                with self.subTest(checkpoint=checkpoint,case=case["name"]):
                    for name,actual in model_outputs(net,encoded).items():
                        np.testing.assert_array_equal(actual,expected[name])
            # Same-total changed copies are a different multiset, with a changed model context.
            changed=model_outputs(net,feature(changed_cases()[1]))
            self.assertGreater(float(np.max(abs(changed["z"]-expected["z"]))),1e-7)

    @unittest.skipUnless(RUST_ENCODER.exists(),"build the pure native encoder example for cross-language checks")
    def test_existing_rust_encoder_matches_all_permutations_and_count_changes(self):
        golden=json.loads((ROOT/"wasm/controller/fixtures/own-deck-contract.json").read_text())["cases"]
        cases=[dict(name="reference",variant="original",hello=base_hello()),*self.cases,*changed_cases(),
               *[dict(name="golden/"+case["name"],variant=case["variant"],hello=case["hello"]) for case in golden]]
        encoded=rust_batch(cases)
        self.assertEqual(len(encoded),281)
        for case in encoded:
            with self.subTest(case=case["name"]):
                np.testing.assert_array_equal(case["expected_bits"],bits(feature(case)))


def verification_report():
    cases=equivalent_cases(); reference=feature(dict(hello=base_hello()))
    max_errors={name:0. for name in ("features","pooled_identity","role_tokens","z","action_latents","context_value","action_values")}
    sensitivity={}; input_args=fixed_inputs()
    protected=[ROOT/"models/tx-t10.safetensors",ROOT/"models/tx-t10-e.safetensors",ROOT/"wasm/generated-own-deck/deck-init.safetensors"]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    for checkpoint in ("tx-t10.safetensors","tx-t10-e.safetensors"):
        weights,meta=D.load_extended(ROOT/"models"/checkpoint,protected[-1]); net=D.NumpyOwnDeckTx(weights,meta)
        expected=model_outputs(net,reference)
        initial,_=net._initial_context(*input_args[:4],reference)
        pooled=D.pooled_identity(weights,reference)
        for case in cases:
            encoded=feature(case)
            max_errors["features"]=max(max_errors["features"],float(np.max(abs(encoded-reference))))
            max_errors["pooled_identity"]=max(max_errors["pooled_identity"],float(np.max(abs(D.pooled_identity(weights,encoded)-pooled))))
            actual,_=net._initial_context(*input_args[:4],encoded)
            max_errors["role_tokens"]=max(max_errors["role_tokens"],float(np.max(abs(actual-initial))))
            for name,value in model_outputs(net,encoded).items():
                max_errors[name]=max(max_errors[name],float(np.max(abs(value-expected[name]))))
        sensitivity[checkpoint]={case["name"]:{name:float(np.max(abs(value-expected[name]))) for name,value in model_outputs(net,feature(case)).items()} for case in changed_cases()}
    golden=json.loads((ROOT/"wasm/controller/fixtures/own-deck-contract.json").read_text())["cases"]
    rust_cases=[dict(name="reference",variant="original",hello=base_hello()),*cases,*changed_cases(),
                *[dict(name="golden/"+c["name"],variant=c["variant"],hello=c["hello"]) for c in golden]]
    rust=rust_batch(rust_cases)
    mismatches=sum(int(np.sum(np.asarray(c["expected_bits"],np.uint32)!=bits(feature(c)))) for c in rust)
    sources=[Path(__file__).resolve(),ROOT/"own_deck.py",ROOT/"own_deck_model.py",ROOT/"tx_model.py",ROOT/"wasm/controller/src/own_deck.rs",ROOT/"wasm/controller/examples/own_deck_encode.rs"]
    return dict(schema="jepa-own-deck-permutation-verification/1",status="PASS" if not any(max_errors.values()) and mismatches==0 else "FAIL",
        seed=SEED,forms=["grouped","expanded","split-reprints","expanded-reprints"],permutations_per_form=64,equivalent_forms_tested=256,
        model_checkpoint_roles=2,horizons_per_action=9,actions=4,feature_bit_identity=True,model_output_bit_identity=not any(max_errors.values()),
        maximum_absolute_errors=max_errors,required_output_tolerance=1e-6,multiplicity_sensitivity=sensitivity,
        rust=dict(path=str(RUST_ENCODER),sha256=sha(RUST_ENCODER),cases=len(rust),float_coordinates=len(rust)*414,bit_mismatches=mismatches,
                  limitation="Existing pure encoder executable used read-only; no build or graph export. Its hash is recorded separately from current source hashes."),
        structural_chain=["Printed aliases normalize to canonical IDs and integer copy counts aggregate before features.",
            "Python iterates sorted canonical counts; Rust uses BTreeMap entries. Neither assigns per-card deck-list positions.",
            "Fixed count histograms produce a copy-weighted sum through shared embedding tables.",
            "din projects metadata plus pooled identity into two fixed original/remaining role tokens, independent of24 live-card capacity.",
            "The transformer sees those two role tokens, never a sequence of cards in declared deck-list order."],
        scope=["Unordered original composition is invariant to list serialization, duplicate grouping and reprint alias choice; multiplicity remains meaningful.",
               "Future effect AST instruction order and legitimately observed top/bottom positions are ordered semantics and must not be erased by this invariant.",
               "No effect-program semantics, unknown draw order, opponent-private information, optimization, gameplay or paid computation is introduced."],
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},fixture_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"wasm/tests/fixtures/runtime-reference.json",ROOT/"wasm/controller/fixtures/own-deck-contract.json"]},
        generated_case_sha256=hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        immutable_before=before,immutable_after={str(p.relative_to(ROOT)):sha(p) for p in protected})


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report",type=Path)
    args=parser.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PermutationContractTests))
    if args.write_report:
        report=verification_report(); report["tests_run"]=result.testsRun; report["skips"]=result.skipped
        if not result.wasSuccessful() or result.skipped: report["status"]="FAIL"
        args.write_report.write_text(json.dumps(report,indent=2)+"\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
