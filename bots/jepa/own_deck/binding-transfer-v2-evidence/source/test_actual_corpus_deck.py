"""Pure data/pooling/guard contracts; no model forwards, engines or optimizers."""
import copy
import importlib.util
import math
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("actual_corpus_deck",HERE/"actual_corpus_deck.py")
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)


def bank_fixture():
    cards=[]
    for i,code in enumerate(D.C.PROPOSED_IDS):
        observed=dict(declared_roots=4,availability_roots=4,committed_roots=3,settled_paid_roots=2,
                      known_source_coordinates=12,known_target_coordinates=3,
                      completions={"settled":2,"cancelled":1,"unaffordable":1},native_fixture_observed=True)
        cards.append(dict(code=code,vector=[i/10]*16,runtime_admitted=True,training_card=code not in D.C.HELD_PROPOSED_IDS,
                          native_fixture_observed=True,observed_counts=observed,semantic_validated=False))
    return dict(schema="whole-card-frozen-vectors/1",arm="correct-typed",dimensions=16,cards=cards)


def data_fixture():
    known=D.C.PROPOSED_IDS[0]
    cards={known:dict(printed=[.2,.1,.3,1.]+[0.]*28,printed_known=True),
           "ZZZ_001":dict(printed=[.3,.2,.4,1.]+[0.]*28,printed_known=True)}
    rows=[dict(source_index=i,family_id="f"+str(i//2),split="train"if i<22 else"val",fingerprint=str(i),
               counts={known:3,"ZZZ_001":2},total_count=5,targets=[i/27]*13,baseline96=[i/100]*96)for i in range(27)]
    return dict(cards=cards,rows=rows,train_idx=list(range(22)),held_idx=list(range(22,27)),train_varying_mask=[True]*13)


class DeckContractTests(unittest.TestCase):
    def test_130_rows_keep_common_metadata_and_flags(self):
        data=data_fixture();bank=D.parse_bank(bank_fixture());row=data["rows"][0]
        learned,n=D.feature_rows(row,data["cards"],bank)
        baseline,m=D.feature_rows(row,data["cards"],bank,True)
        self.assertEqual(n,m);self.assertEqual(sum(n),5)
        self.assertTrue(all(len(x)==130 for x in learned+baseline))
        self.assertEqual([x[96:]for x in learned],[x[96:]for x in baseline])
        self.assertEqual(learned[1][:96],[0.]*96)
        self.assertEqual(learned[1][-2:],[0.,1.])

    def test_all_unknown_arms_equal_on_nonempty_declarations(self):
        data=data_fixture();row=data["rows"][0]
        unavailable={"OUT_001":dict(vector=[1.]*16)}
        other={"OUT_001":dict(vector=[-2.]*16)}
        self.assertEqual(D.feature_rows(row,data["cards"],unavailable),D.feature_rows(row,data["cards"],other))
        # Thus the same deterministic phi/rho/head state sees byte-equal inputs;
        # fitting those arms would not test a learned-card semantic difference.
        self.assertEqual(sum(D.feature_rows(row,data["cards"],other)[1]),5)

    def test_pool_permutation_and_copy_sensitivity(self):
        features=[[0.]*128+[1.,1.],[0.]*128+[0.,1.]]
        hidden=[[.1]*32,[.3]*32]
        a=D.pool_reference(hidden,[3,2],features)
        b=D.pool_reference(hidden[::-1],[2,3],features[::-1])
        self.assertEqual(a,b);self.assertEqual(len(a),68)
        self.assertNotEqual(a,D.pool_reference(hidden,[4,2],features))
        self.assertEqual(a[-4],5/60)

    def test_fixed_82_evaluation_rows_and_duplicate_canonicalization(self):
        data=data_fixture();bank=D.parse_bank(bank_fixture())
        x,n=D.evaluation_rows(data,bank)
        self.assertEqual(len(x),82);self.assertEqual(len(n),82)
        self.assertEqual(x[54:81],x[:27]);self.assertEqual(n[54:81],n[:27])
        self.assertEqual(x[27],x[0][::-1]);self.assertEqual(n[27],n[0][::-1])
        self.assertEqual(sum(n[-1]),sum(n[0])+1)
        self.assertEqual([r["counts"]for r in data["rows"]],[data_fixture()["rows"][i]["counts"]for i in range(27)])

    def test_printed_features_ignore_identity_ir_and_titles(self):
        card=dict(cost=2,power=1,hp=4,types=["unit"],arena="space",aspects=["heroism"],traits=["vehicle","fighter"],keywords=[])
        a,known=D.printed32(card);self.assertTrue(known);self.assertEqual(len(a),32)
        self.assertEqual((a,known),D.printed32({**card,"id":"private-source","title":"unused","text":"unused","abilities":[{"kind":"damage"}]}))
        self.assertEqual(D.printed32({**card,"power":float("nan")}),([0.]*32,False))
        event={**card,"types":["event"],"power":None,"hp":None}
        self.assertTrue(D.printed32(event)[1])
        upgrade={**card,"types":["upgrade"],"power":3,"hp":2}
        self.assertEqual(D.printed32(upgrade)[0][1:3],[.3,.2])
        self.assertEqual(D.printed32({**upgrade,"upgradePower":4,"upgradeHp":1})[0][1:3],[.4,.1])

    def test_composition_targets_use_all_copies_not_known_bank_denominator(self):
        records={"AAA_001":dict(card=dict(cost=1,types=["unit"])),"BBB_001":dict(card=dict(cost=4,types=["event"]))}
        y=D.composition_targets({"AAA_001":1,"BBB_001":3},records)
        self.assertEqual(len(y),13);self.assertEqual(y[0],4/60);self.assertEqual(y[1],3.25/10)
        self.assertEqual(y[2],.25);self.assertEqual(y[-1],.25)

    def test_native_flag_requires_actual_settled_paid_support(self):
        value=bank_fixture();value["cards"][0]["observed_counts"]["settled_paid_roots"]=0
        with self.assertRaises(ValueError):D.parse_bank(value)
        value["cards"][0]["native_fixture_observed"]=False
        value["cards"][0]["observed_counts"]["native_fixture_observed"]=False
        self.assertFalse(D.parse_bank(value)[D.C.PROPOSED_IDS[0]]["native_fixture_observed"])

    def test_bank_rejects_nonfinite_missing_duplicate_and_false_training_claim(self):
        for mutation in ("nan","missing","duplicate","held"):
            value=bank_fixture()
            if mutation=="nan":value["cards"][0]["vector"][0]=float("nan")
            if mutation=="missing":value["cards"].pop()
            if mutation=="duplicate":value["cards"].append(copy.deepcopy(value["cards"][0]))
            if mutation=="held":next(row for row in value["cards"]if row["code"]in D.C.HELD_PROPOSED_IDS)["training_card"]=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):D.parse_bank(value)

    def test_family_first_metrics_do_not_count_siblings_independent(self):
        data=data_fixture();pred=[r["targets"][:]for r in data["rows"]]
        pred[22]=[v+2 for v in pred[22]];pred[23]=[v+2 for v in pred[23]]
        result=D.metrics(pred,data,[22,23,24])
        self.assertAlmostEqual(result["varying_macro_mse"],8/3)
        self.assertAlmostEqual(result["family_first_varying_macro_mse"],2.)
        self.assertEqual(result["families"],2)

    def test_shared_ledger_native_card_aliases_and_charge(self):
        rows=[dict(event="stage-start",phase="native",stage_id="n"),dict(event="stage-finish",phase="native",stage_id="n",elapsed_seconds=2.,optimizer_updates=0,native_applies=12,neural_forwards=0),
              dict(event="stage-start",phase="card",stage_id="c"),dict(event="stage-finish",phase="card",stage_id="c",elapsed_seconds=3.,optimizer_updates=7,charged_optimizer_updates=800,native_applies=0,neural_forwards=8)]
        totals,phases=D.ledger_totals(rows)
        self.assertEqual(totals,dict(elapsed_seconds=5.,optimizer_updates=800,native_applies=12,neural_forwards=8))
        self.assertEqual(phases["card"]["optimizer_updates"],800)

    def test_pending_mismatched_credit_and_nonfinite_ledger_rejected(self):
        for rows in ([dict(event="stage-start",phase="native",stage_id="n")],
                     [dict(event="credit",phase="deck")],
                     [dict(event="stage-start",phase="native",stage_id="n"),dict(event="stage-finish",phase="native",stage_id="x")],
                     [dict(event="stage-start",phase="native",stage_id="n"),dict(event="stage-finish",phase="native",stage_id="n",elapsed_seconds=float("nan"))]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):D.ledger_totals(rows)


if __name__=="__main__":unittest.main()
