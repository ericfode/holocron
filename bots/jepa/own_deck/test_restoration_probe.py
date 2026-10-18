"""Boundary and objective-math checks only; no optimizer updates or model fits."""
import argparse
import json
from pathlib import Path
import queue
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restoration_probe as P
import own_deck as O


def fixture():
    fit = O.neutral_features(8)
    fit[:, 0, 2:4] = 1
    fit[:, 0, 4] = 50/60
    fit[:, 0, 6] = 20/60
    fit[:, 0, 7] = 1
    fit[:, 0, 41] = .3
    for a, b in ((50, 114), (114, 146), (146, 207)):
        fit[:, 0, a] = 40/60
        fit[:, 0, a+1] = 10/60
    return dict(fit_features=fit, fit_labels=np.array([1,0,1,0,1,0,1,0]),
                fit_source_idx=np.repeat(np.arange(4), 2), fit_family_ids=np.repeat(["A","B","C","D"],2),
                fit_partition=np.array(["train"]*4+["val"]*4), fit_variant_ids=np.array([f"fit{i}" for i in range(8)]),
                fit_fingerprints=np.array([f"fingerprint{i}" for i in range(8)]), train_idx=np.arange(4), val_idx=np.arange(4,8),
                eval_features=fit[np.repeat(4,7)], eval_source_idx=np.repeat(2,7), eval_family_ids=np.repeat("C",7),
                eval_partition=np.repeat("val",7), eval_variant_ids=np.array([f"eval{i}" for i in range(7)]),
                eval_group_ids=np.repeat("individual-C",7), eval_kind=np.array(["true-restoration"]*3+["matched-alternative"]*3+["incomplete-diagnostic"]),
                eval_restored_copies=np.array([0,1,2,0,1,2,0]), eval_removed_copies=np.repeat(2,7),
                eval_total_count=np.array([50]*6+[48]))


class RestorationContracts(unittest.TestCase):
    def test_admits_fixed_count_fit_and_unlabelled_restoration(self):
        data = P.validate_dataset(fixture(), {})
        self.assertEqual(data["train_idx"].tolist(), [0,1,2,3])
        self.assertNotIn("eval_labels", data)

    def test_family_and_source_leakage_rejected(self):
        for field, index, value in (("fit_family_ids",4,"A"),("eval_source_idx",0,0),("eval_family_ids",0,"A")):
            data=fixture(); data[field][index]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                P.validate_dataset(data,{})

    def test_incomplete_decks_cannot_be_negative_fit_examples(self):
        data=fixture(); data["fit_features"][1,0,4]=49/60
        with self.assertRaises(ValueError): P.validate_dataset(data,{})
        data=fixture(); data["eval_total_count"][1]=49
        with self.assertRaises(ValueError): P.validate_dataset(data,{})

    def test_remaining_is_unknown_and_never_read_as_private_state(self):
        data=fixture(); data["fit_features"][0,1,3]=1
        with self.assertRaises(ValueError): P.validate_dataset(data,{})

    def test_size_and_identity_mass_removed_without_mutating_inputs(self):
        rows=fixture()["fit_features"]
        original=rows.copy()
        output=P.context_without_size(rows)
        np.testing.assert_array_equal(rows,original)
        np.testing.assert_array_equal(output[:,0,[4,5,6,49]],0)
        for a,b in ((50,114),(114,146),(146,207)):
            np.testing.assert_allclose(output[:,0,a:b].sum(1),1)
        printed=P.context_without_size(rows,True)
        np.testing.assert_array_equal(printed[:,:,50:],0)
        np.testing.assert_array_equal(printed[:,0,41],rows[:,0,41])

    def test_curves_retain_empirical_decreases_and_keep_incomplete_separate(self):
        data=P.validate_dataset(fixture(),{})
        scores=np.array([.8,.2,.7,.3,.4,.5,.6])
        report=P.curve_report(scores,data,{})
        group=report["groups"]["individual-C"]
        np.testing.assert_allclose(group["adjacent_score_deltas"],[-.6,.5])
        self.assertEqual(group["decreases"],1)
        self.assertEqual(group["nondecreasing_adjacent_fraction"],.5)
        aggregate=report["family_first_same_count_aggregate"]
        self.assertEqual((aggregate["n_families"],aggregate["n_sources"],aggregate["n_restoration_groups"],aggregate["n_packages"],aggregate["n_dependent_points"]),(1,1,1,0,3))
        self.assertAlmostEqual(aggregate["mean_same_count_delta"],(.5-.2+.2)/3)
        self.assertTrue([p for p in group["points"] if p["kind"]=="incomplete-diagnostic"][0]["out_of_distribution"])
        anchors=[p for p in group["points"] if p["kind"]=="matched-alternative"]
        self.assertEqual([p["paired_restoration_step"] for p in anchors],[0,1,2])
        self.assertEqual([p["actual_original_copies_restored"] for p in anchors],[0,0,0])
        self.assertTrue(all(p["constant_anchor"] for p in anchors))

    def test_coarse_metadata_controls_and_exact_source_family_mapping(self):
        for field, index, value in (("fit_features",(1,0,16),.2),("eval_features",(1,0,35),.2),("eval_family_ids",0,"D")):
            data=fixture(); data[field][index]=value
            with self.subTest(field=field), self.assertRaises(ValueError): P.validate_dataset(data,{})

    def test_curve_feed_preserves_scores_flags_support_and_finite_json(self):
        data=P.validate_dataset(fixture(),{})
        curves=P.curve_report(np.array([.8,.2,.7,.3,.4,.5,.6]),data,{})
        writer=mock.Mock()
        P.emit_curve_events(writer,curves,"frozen-latent",200)
        with tempfile.TemporaryDirectory() as tmp:
            journal=P.RunEvents(Path(tmp)/"events.jsonl","curve-contract","a"*40,{}, {}, [])
            for call in writer.emit.call_args_list:
                journal.emit(*call.args,**call.kwargs)
            events=[json.loads(line,parse_constant=lambda value: self.fail("nonfinite JSON: "+value)) for line in journal.path.read_text().splitlines()]
        self.assertTrue(all(event["step"]==200 for event in events))
        points=[event for event in events if event["phase"]=="restoration_curve"]
        self.assertEqual(len(points),7)
        true=[event for event in points if event["curve_kind"]=="true-restoration"]
        self.assertEqual([event["metrics"]["score"] for event in true],[.8,.2,.7])
        self.assertEqual([event["metrics"]["true_arm_restoration_step"] for event in true],[0,1,2])
        self.assertTrue(all(event["metrics"]["is_primary"]==1 for event in true))
        anchors=[event for event in points if event["curve_kind"]=="matched-alternative"]
        self.assertEqual([event["metrics"]["actual_original_copies_restored"] for event in anchors],[0,0,0])
        incomplete=[event for event in points if event["curve_kind"]=="incomplete-diagnostic"]
        self.assertEqual([(event["metrics"]["is_primary"],event["metrics"]["deck_size"]) for event in incomplete],[(0,48)])
        aggregates=[event for event in events if event["phase"]=="restoration_curve_aggregate"]
        aggregate=next(event for event in aggregates if event["aggregation"]=="all-steps")
        self.assertEqual(aggregate["metrics"]["n_families"],1)
        self.assertEqual(aggregate["metrics"]["n_sources"],1)
        self.assertEqual(aggregate["metrics"]["n_dependent_points"],3)
        self.assertEqual(len(aggregates),4)
        self.assertTrue(all(isinstance(event[field],str) for event in points for field in ("arm","curve_group","family_id","source_idx","curve_kind")))

    def test_logistic_derivative_matches_finite_difference_without_updates(self):
        rng=np.random.default_rng(17)
        x=rng.normal(size=(6,96)); y=np.array([1.,0,1,0,0,0])
        w=rng.normal(0,.01,96); before=w.copy(); b=.2
        loss,gradient,db=P.logistic_terms(x,y,w,b,.001)
        eps=1e-5; plus=w.copy(); minus=w.copy(); plus[3]+=eps; minus[3]-=eps
        observed=(P.logistic_terms(x,y,plus,b,.001)[0]-P.logistic_terms(x,y,minus,b,.001)[0])/(2*eps)
        self.assertAlmostEqual(gradient[3],observed,places=8)
        observed_b=(P.logistic_terms(x,y,w,b+eps,.001)[0]-P.logistic_terms(x,y,w,b-eps,.001)[0])/(2*eps)
        self.assertAlmostEqual(db,observed_b,places=8)
        np.testing.assert_array_equal(w,before)
        self.assertTrue(np.isfinite(loss))

    def test_allocation_rejects_search_or_extra_steps(self):
        for config in (P.Config(seed=18),P.Config(steps=201),P.Config(learning_rate=.1),P.Config(max_seconds=61)):
            with self.subTest(config=config), self.assertRaises(ValueError): config.validate()

    def test_worker_terminal_result_uses_acknowledgement_and_plain_json(self):
        messages=queue.Queue()
        acknowledged=mock.Mock()
        acknowledged.wait.return_value=True
        with mock.patch.object(P,"train_probe",return_value={"updates_completed":400,"value":np.float64(.5)}):
            P._restoration_worker(messages,acknowledged,None,None,None,None,None,None,None,None)
        emitted=[]
        while not messages.empty(): emitted.append(messages.get_nowait())
        self.assertEqual([p for kind,p in emitted if kind=="result"],[{"updates_completed":400,"value":.5}])
        self.assertFalse(any(kind=="failure" for kind,_ in emitted))
        acknowledged.wait.assert_called_once_with(timeout=3.)

    def test_execute_requires_explicit_admission_or_historical_launch(self):
        data=P.validate_dataset(fixture(),{})
        args=argparse.Namespace(steps=200,execute=True,historical_diagnostic=False)
        with mock.patch.object(P,"prepare",return_value=(data,{},None,None,{})), mock.patch.object(P.subprocess,"check_output",return_value="a"*40), mock.patch.object(P.G,"supervise_worker") as guard:
            with self.assertRaisesRegex(ValueError,"admission"):
                P.run(args)
        guard.assert_not_called()

    def test_parent_routes_both_arms_through_one_guard_and_only_then_completes(self):
        data=P.validate_dataset(fixture(),{})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/"base"; init=root/"init"
            base.write_bytes(b"frozen-base"); init.write_bytes(b"frozen-init")
            args=argparse.Namespace(steps=200,execute=True,historical_diagnostic=False,out=root/"out",
                                    events=root/"events.jsonl",run_id="guard-contract",parent_run_id=None)
            manifest={"primary_experiment_admitted":True}
            with mock.patch.object(P,"prepare",return_value=(data,manifest,base,init,{})), mock.patch.object(P.subprocess,"check_output",return_value="a"*40), mock.patch.object(P.G,"supervise_worker",return_value={"updates_completed":400,"guard":{"status":"completed"}}) as guard:
                result=P.run(args)
            call=guard.call_args.args
            self.assertIs(call[0],P._restoration_worker)
            self.assertEqual((call[3],call[5],call[6]),(60.,60.,2048.))
            self.assertEqual(result["updates_completed"],400)
            events=[json.loads(line) for line in args.events.read_text().splitlines()]
            self.assertEqual([e["phase"] for e in events],["encoding","completed"])
            self.assertEqual(json.loads((args.out/"result.json").read_text())["guard"]["status"],"completed")

    def test_guard_failure_writes_receipt_without_completed_artifact(self):
        data=P.validate_dataset(fixture(),{})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/"base"; init=root/"init"
            base.write_bytes(b"frozen-base"); init.write_bytes(b"frozen-init")
            args=argparse.Namespace(steps=200,execute=True,historical_diagnostic=False,out=root/"out",
                                    events=root/"events.jsonl",run_id="guard-failure",parent_run_id=None)
            failure=P.G.GuardStopped("test stop",{"status":"stopped"})
            with mock.patch.object(P,"prepare",return_value=(data,{"primary_experiment_admitted":True},base,init,{})), mock.patch.object(P.subprocess,"check_output",return_value="a"*40), mock.patch.object(P.G,"supervise_worker",side_effect=failure):
                with self.assertRaises(P.G.GuardStopped): P.run(args)
            events=[json.loads(line) for line in args.events.read_text().splitlines()]
            self.assertFalse(any(e["phase"]=="completed" for e in events))
            self.assertFalse((args.out/"result.json").exists())
            receipt=json.loads((args.out/"error.json").read_text())
            self.assertEqual(receipt["guard"]["status"],"stopped")
            self.assertEqual(receipt["immutable_before"],receipt["immutable_after"])


if __name__=="__main__": unittest.main()
