"""Portable accounting-boundary/resource checks; no native subprocess launches."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch,Mock

SPEC=importlib.util.spec_from_file_location("public_binding_guard",Path(__file__).with_name("supervise.py"))
G=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(G)


class GuardTests(unittest.TestCase):
    def test_constructor_support_is_allowed_but_all_physical_captures_are_zero(self):
        capture=dict(state=dict(players=dict(p1=dict(ground=[dict(setCode="SEC_028",upgrades=[])]))),
                     projections=dict(host_a=dict(code="SEC_028",shield_count=0),host_b=None))
        raw=dict(collectionPlan=dict(selected_whole_rows=dict(TOKEN_SHIELD=dict(setCode="TOKEN_SHIELD"))),
                 cases=[dict(before=capture,steps=[dict(before=capture,after=capture)],final=capture)])
        proof=G.verify_no_physical_shields(raw)
        self.assertEqual(proof["physical_shield_instances"],0);self.assertEqual(proof["captures_checked"],4)
        for field in("before","final"):
            bad=copy.deepcopy(raw);bad["cases"][0][field]["state"]["players"]["p1"]["ground"][0]["upgrades"].append(dict(setCode="TOKEN_SHIELD",token=True))
            with self.assertRaisesRegex(ValueError,"physical Shield"):G.verify_no_physical_shields(bad)
        bad=copy.deepcopy(raw);bad["cases"][0]["steps"][0]["after"]["projections"]["host_a"]["shield_count"]=1
        with self.assertRaisesRegex(ValueError,"Shield count"):G.verify_no_physical_shields(bad)

    def test_missing_or_unknown_physical_token_proof_rejects(self):
        with self.assertRaisesRegex(ValueError,"no captures"):G.verify_no_physical_shields(dict(cases=[]))
        for value in(None,False,"0"):
            bad=dict(cases=[dict(before=dict(state={},projections=dict(source=dict(shield_count=value))))])
            with self.assertRaisesRegex(ValueError,"Shield count"):G.verify_no_physical_shields(bad)

    def test_exact_two_native_allocations_and_no_fit_entry(self):
        self.assertEqual(G.STAGES,{"native-build":(30.,0),"native-collect":(60.,80)})
        self.assertEqual(G.MAX_BYTES,1024**3)
        for stage in("fit","evaluate","collect","reset"):
            with self.assertRaisesRegex(ValueError,"native build/collect"):
                G.run(types.SimpleNamespace(stage=stage))

    def test_failed_engine_intent_is_an_actual_call(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"trace.jsonl"
            rows=[dict(schema="jepa-public-input-binding-apply-journal/1"),dict(phase="beforeApply",applyCall=1),dict(phase="applyError",applyCall=1)]
            p.write_text("\n".join(json.dumps(v)for v in rows)+"\n")
            self.assertEqual(G.trace_exposure(p,True),dict(known_calls=1,verified=True,reason=None))

    def test_unknown_observed_exposure_does_not_invent_eighty_calls(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"trace.jsonl"
            self.assertEqual(G.trace_exposure(p,False),dict(known_calls=0,verified=True,reason=None))
            self.assertFalse(G.trace_exposure(p,True)["verified"])
            p.write_text('{"schema":"jepa-public-input-binding-apply-journal/1"}\n{"phase":"beforeApply","applyCall":1}\nBROKEN\n')
            r=G.trace_exposure(p,True);self.assertEqual(r["known_calls"],1);self.assertFalse(r["verified"])

    def test_nonsequential_intents_are_not_verified(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"trace.jsonl";p.write_text('{"schema":"jepa-public-input-binding-apply-journal/1"}\n{"phase":"beforeApply","applyCall":2}\n')
            r=G.trace_exposure(p,True);self.assertEqual(r["known_calls"],0);self.assertFalse(r["verified"])

    def test_concurrent_memory_not_historical_pid_peak_sum(self):
        m=1024**2;r=dict(observed_per_pid_peak_bytes={})
        self.assertEqual(G.memory_sample(r,{1:100*m,2:600*m},1,100*m),700*m)
        self.assertEqual(G.memory_sample(r,{1:100*m,3:600*m},1,100*m),700*m)
        self.assertGreater(sum(r["observed_per_pid_peak_bytes"].values()),G.MAX_BYTES)
        self.assertGreater(G.memory_sample(r,{1:100*m,2:600*m,3:600*m},1,100*m),G.MAX_BYTES)
        self.assertEqual(G.final_memory_bound(700*m,100*m,700*m),800*m)

    def test_vanished_owned_pid_skip_has_explicit_receipt(self):
        def rss(pid):
            if pid==2:raise OSError(3,"vanished owned PID")
            if pid==3:raise OSError(1,"permission")
            return 100
        r={};self.assertEqual(G.read_owned_rss(r,[2,4],rss,1,.5),{1:100,4:100})
        self.assertEqual(r["exited_owned_pid_skips"][0]["elapsed_seconds"],.5)
        with self.assertRaises(PermissionError):G.read_owned_rss({},[3],rss,1,.6)

    def test_cached_profile_and_one_build_worker_no_semantic_changes(self):
        with patch.dict(G.os.environ,{},clear=True):env=G.build_environment(Path("/tmp/test-binding-cache"))
        self.assertEqual(env["CARGO_BUILD_JOBS"],"1");self.assertEqual(env["CARGO_PROFILE_DEV_DEBUG"],"0")
        self.assertEqual(env["CARGO_PROFILE_DEV_INCREMENTAL"],"false")
        self.assertNotIn("RUSTFLAGS",env);self.assertNotIn("CARGO_PROFILE_DEV_CODEGEN_UNITS",env)
        with patch.dict(G.os.environ,{"RUSTFLAGS":"-C panic=abort"},clear=True),self.assertRaises(ValueError):G.build_environment(Path("/tmp/test-binding-cache"))

    def test_collect_requires_exact_previously_built_binary_bytes(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td)/"collector";p.write_bytes(b"fixture-binary-not-executed")
            proof=dict(role="built-collector-binary",**G.pin(p));records=[dict(event="attempt-finish",data=dict(proofs=[proof]))]
            self.assertEqual(G.build_binary_proof(records,p),G.pin(p))
            p.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"binary changed"):G.build_binary_proof(records,p)
            with self.assertRaisesRegex(ValueError,"proof required"):G.build_binary_proof([],p)

    def test_kill_eperm_keeps_pending_and_never_closes_ledger(self):
        proc=types.SimpleNamespace(pid=123,wait=Mock());members=Mock(return_value=[]);receipt=dict(status="failed")
        with patch.object(G.os,"killpg",side_effect=PermissionError(1,"mock EPERM"))as kill:
            verified=G.cleanup_owned(proc,123,members,receipt)
        self.assertFalse(verified);kill.assert_called_once();proc.wait.assert_called_once_with(timeout=2);members.assert_called_once_with(123)
        self.assertIn("PermissionError",receipt["cleanup_errors"][0]["error"])
        accounting=types.SimpleNamespace(finish=Mock())
        G.close_accounted_attempt(accounting,None,[],receipt,1.,dict(known_calls=0,verified=True),[],verified)
        accounting.finish.assert_not_called();self.assertTrue(receipt["pending_attempt_preserved"])


if __name__=="__main__":unittest.main()
