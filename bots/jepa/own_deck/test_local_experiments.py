"""Bounded runner admission/control/owned-child watchdog tests; no training."""
import copy
import json
import pickle
from pathlib import Path
import tempfile
import time
import threading
import types
import unittest
from unittest import mock

import numpy as np

import run_local_experiments as R


def forbidden_unpickle():
    raise AssertionError("a backend-specific pickle reducer escaped the worker")


class BackendVersion(str):
    def __reduce__(self):
        return forbidden_unpickle,()


def fixture():
    rows=R.O.neutral_features(6)
    rows[:,0,2:4]=1
    rows[:,0,4]=np.arange(6)/60+.8
    rows[:,0,7]=1
    rows[:,0,8]=np.arange(6)/20
    rows[:,0,16]=np.arange(6)/10
    names=["total_count_per_60","mean_cost_per_10","initial_draw_unit_probability"]
    data=dict(deck_features=rows,targets=np.arange(18,dtype=np.float32).reshape(6,3)/20,
              train_idx=np.asarray([0,1,2,3]),val_idx=np.asarray([4,5]),
              fingerprints=np.asarray(["fp"+str(i) for i in range(6)]),
              family_ids=np.asarray(["family"+str(i) for i in range(6)]),
              wrong_idx=np.asarray([1,2,3,0,5,4]))
    manifest=dict(target_names=names,target_groups={"count":[0],"curve":[1],"draw":[2]})
    return data,manifest


class LocalRunnerTests(unittest.TestCase):
    def test_runtime_versions_and_worker_results_are_plain_json_values(self):
        runtime=R.runtime_metadata(types.SimpleNamespace(__version__=BackendVersion("test-version")))
        self.assertIs(type(runtime["torch"]),str)
        # Exercise the terminal worker transport with its training function mocked.
        messages=R.queue.Queue(); acknowledged=threading.Event(); acknowledged.set()
        fake=dict(status="completed",runtime={"torch":BackendVersion("test-version")})
        with mock.patch.object(R,"train_arm",return_value=fake):
            R._worker_entry(messages,acknowledged,None,None,None,None,None,None,None,None)
        results=[]
        while not messages.empty():
            kind,payload=messages.get()
            if kind=="result": results.append(payload)
        self.assertEqual(len(results),1)
        self.assertIs(type(results[0]["runtime"]["torch"]),str)
        self.assertEqual(pickle.loads(pickle.dumps(results[0])),fake)

    def test_final_parent_peak_is_included_in_conservative_tree_bound(self):
        peaks,total=R.finalized_memory_bound({"supervisor":41.515625,"worker":279.703125,"resource_tracker":18.09375},339.3125,203.25)
        self.assertEqual(peaks["supervisor"],203.25)
        self.assertEqual(total,501.046875)
        self.assertGreaterEqual(total,sum(peaks.values()))

    def test_allocation_caps(self):
        self.assertEqual(R.Config().validate().steps,100)
        for kwargs in ({"steps":101},{"batch":17},{"seed":18},{"max_arm_seconds":121},
                       {"max_campaign_seconds":301},{"max_rss_mib":2049},{"learning_rate":.01}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError): R.Config(**kwargs).validate()

    def test_complete_admission_and_arm_shapes(self):
        data,manifest=fixture(); data=R.validate_dataset(data,manifest)
        np.testing.assert_array_equal(R.arm_features(data,"original"),data["deck_features"])
        np.testing.assert_array_equal(R.arm_features(data,"wrong-own"),data["deck_features"][data["wrong_idx"]])
        np.testing.assert_array_equal(R.arm_features(data,"neutral"),R.O.neutral_features(6))
        self.assertEqual(R.arm_features(data,"neutral").shape,(6,2,207))

    def test_admission_rejects_cross_split_leakage(self):
        for field in ("fingerprints","family_ids"):
            data,manifest=fixture(); data[field][4]=data[field][0]
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,"leakage"): R.validate_dataset(data,manifest)

    def test_admission_rejects_bad_wrong_control_and_unknown_original(self):
        for mutation in ("cross-partition","same-identity","same-curve","remaining-known","original-unknown"):
            data,manifest=fixture()
            if mutation=="cross-partition": data["wrong_idx"]=np.asarray([5,2,3,0,1,4])
            elif mutation=="same-identity": data["wrong_idx"]=np.arange(6)
            elif mutation=="same-curve": data["deck_features"][:,0,8:25]=0
            elif mutation=="remaining-known": data["deck_features"][:,1,3]=1
            elif mutation=="original-unknown": data["deck_features"][:,0,3]=0
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): R.validate_dataset(data,manifest)

    def test_batch_sequence_is_paired_and_training_only(self):
        data,manifest=fixture(); data=R.validate_dataset(data,manifest)
        schedule=R.batch_sequence(data,R.Config())
        np.testing.assert_array_equal(schedule,R.batch_sequence(data,R.Config()))
        self.assertEqual(schedule.shape,(100,16))
        self.assertTrue(set(schedule.flat)<=set(data["train_idx"]))

    def test_metrics_are_observed_values_with_copy_units(self):
        data,manifest=fixture(); data=R.validate_dataset(data,manifest)
        target=data["targets"][data["val_idx"]]
        metrics=R.evaluation_metrics(target+.1,target,data)
        self.assertAlmostEqual(metrics["val_loss"],.01,places=6)
        self.assertAlmostEqual(metrics["val_count_mae_copies"],6.,places=5)
        self.assertAlmostEqual(metrics["val_draw_mae"],.1,places=6)
        with self.assertRaises(FloatingPointError): R.evaluation_metrics(target*np.nan,target,data)

    def test_validate_only_needs_no_torch_and_writes_no_event_or_run(self):
        data,manifest=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); pack=tmp/"data.npz"; meta=tmp/"manifest.json"
            np.savez(pack,**data); manifest["artifact"]={"sha256":R.sha(pack)}; meta.write_text(json.dumps(manifest))
            args=types.SimpleNamespace(dataset=pack,manifest=meta,events=tmp/"events.jsonl",runs=tmp/"runs",
                 campaign_id="test",run_prefix="test",steps=100,batch=16,validate_only=True)
            with mock.patch.dict("sys.modules",{"torch":None}),mock.patch("builtins.print"):
                preview=R.run(args)
            self.assertEqual(preview["dataset"]["train_examples"],4)
            self.assertFalse(args.events.exists()); self.assertFalse(args.runs.exists())

    def test_npz_manifest_binding_rejects_changed_bytes(self):
        data,manifest=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); pack=tmp/"data.npz"; meta=tmp/"manifest.json"
            np.savez(pack,**data); manifest["artifact"]={"sha256":"0"*64}; meta.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"SHA256"): R.load_dataset(pack,meta)

    def test_owned_child_guards_stop_timeout_and_real_allocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=R.self_test_guards(Path(tmp)/"guards.jsonl")
        self.assertEqual([v["status"] for v in result],["PASS","PASS"])
        self.assertTrue(all(v["guard"]["status"]=="stopped" for v in result))
        self.assertTrue(all(v["guard"]["exitcode"] is not None for v in result))

    def test_completion_requires_clean_worker_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("complete","bad-exit"):
                writer=R.RunEvents(Path(tmp)/"events.jsonl",run_id=mode,commit="0"*40,config={},dataset={},limitations=[])
                if mode=="complete":
                    result=R.supervise_worker(R._guard_test_worker,(mode,),writer,3.,time.monotonic(),5.,2048.)
                    self.assertEqual(result["guard"]["exitcode"],0)
                else:
                    with self.assertRaisesRegex(R.GuardStopped,"nonzero"):
                        R.supervise_worker(R._guard_test_worker,(mode,),writer,3.,time.monotonic(),5.,2048.)


if __name__=="__main__": unittest.main()
