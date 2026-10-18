import argparse
from pathlib import Path
import subprocess
import sys
import unittest
import ast
import importlib
import types
from types import SimpleNamespace
from unittest.mock import patch

import binding_transfer_repair as W


class RoutingTests(unittest.TestCase):
    def fake_accounting(self):return SimpleNamespace(start=lambda *_args:'reserved',LEDGER=W.ROOT/'campaign-ledger.jsonl',__file__=__file__)

    def test_import_has_no_neural_or_numerical_import(self):
        subprocess.run([sys.executable,'-B','-c','import sys; import binding_transfer_repair; assert "torch" not in sys.modules and "numpy" not in sys.modules'],cwd=Path(W.__file__).parent,check=True,capture_output=True)

    def test_science_sources_remain_exact(self):
        pins=W.verify_science();self.assertEqual(len(pins),9)
        self.assertEqual(pins[0]['sha256'],W.SCIENCE['binding_transfer_fit.py'])

    def test_shared_module_route_and_original_bindings_restored(self):
        F,P,B=W.modules();original=(F.accounting,F.stage_metadata,P.A);A=self.fake_accounting();old_start=A.start
        with W.routed(A)as(bound,f,p,b):
            self.assertIs(bound,A);self.assertIs(f,F);self.assertIs(b.F,F);self.assertIs(p.A,A);self.assertIs(f.accounting(),A)
        self.assertEqual((F.accounting,F.stage_metadata,P.A),original);self.assertIs(A.start,old_start)

    def test_audit_runs_only_after_durable_reservation(self):
        events=[];A=self.fake_accounting();A.start=lambda *_args:events.append('reserved')
        with patch.object(W,'routing_audit',side_effect=lambda *_args:events.append('audited')):
            with W.routed(A):
                self.assertEqual(events,[]);A.start(None,[], 'fit',dict(argv=W.actual_argv()))
        self.assertEqual(events,['reserved','audited'])

    def test_audit_failure_retains_started_reservation_for_worker_closure(self):
        events=[];A=self.fake_accounting();A.start=lambda *_args:events.append('reserved')
        with patch.object(W,'routing_audit',side_effect=ValueError('changed science')):
            with W.routed(A):
                with self.assertRaisesRegex(ValueError,'changed science'):A.start(None,[],'fit',dict(argv=W.actual_argv()))
        self.assertEqual(events,['reserved'])

    def test_unexpected_cached_worker_route_rejects_after_reservation(self):
        events=[];A=self.fake_accounting();A.start=lambda *_args:events.append('reserved');F,_,_=W.modules()
        with patch.object(F,'accounting',return_value='unexpected'),patch.object(W,'routing_audit'):
            with W.routed(A):
                with self.assertRaisesRegex(ValueError,'already-loaded'):A.start(None,[],'fit',dict(argv=W.actual_argv()))
        self.assertEqual(events,['reserved'])

    def test_actual_wrapper_argv_is_metadata_entrypoint(self):
        A=self.fake_accounting();root=W.ROOT
        with patch.object(sys,'argv',[str(W.HERE/'binding_transfer_repair.py'),'fit','--plan','p']):
            with W.routed(A)as(_,F,_,_):
                meta,_,_=F.stage_metadata(dict(config=dict(pins=[])),[],root/'p',root/'fit-1',root/'progress',W.HERE/'binding_transfer_fit.py')
        self.assertEqual(meta['argv'][1],str(Path(W.__file__).resolve()));self.assertEqual(meta['argv'][2:6],['fit','--plan','p'])

    def test_prep_explicitly_uses_new_ledger_and_wrapper_argv(self):
        A=self.fake_accounting();F,P,B=W.modules();args=argparse.Namespace(command='prep',native_receipt=Path('/r'),journal=Path('/j'),native_plan=Path('/p'),prepared=Path('/m'),out=Path('/o'))
        with patch.object(W,'load_accounting',return_value=A),patch.object(P,'run',return_value='no execution')as worker:
            self.assertEqual(W.dispatch(args),'no execution')
        self.assertEqual(worker.call_args.kwargs['ledger'],A.LEDGER);self.assertEqual(worker.call_args.kwargs['argv'],W.actual_argv())

    def test_converter_alias_restores_previous_import_without_importing_numpy(self):
        module=types.ModuleType(W.DATA_MODULE);module.__file__=str(W.HERE/(W.DATA_MODULE+'.py'))
        sentinel=object();before=sys.modules.get('binding_transfer_data',sentinel)
        with W.converter_alias(module):self.assertIs(importlib.import_module('binding_transfer_data'),module)
        self.assertIs(sys.modules.get('binding_transfer_data',sentinel),before)

    def test_manifest_hook_changes_provenance_only_and_restores(self):
        A=self.fake_accounting();F,P,B=W.modules();saved=[];old_save=P.save_json
        value=dict(schema='jepa-binding-transfer-data/1',source_pins=[],targets='unchanged-payload',fit_admitted=True)
        with patch.object(P,'save_json',side_effect=lambda path,value:saved.append(value)):
            with W.routed(A):P.save_json(Path('/unused'),value)
        self.assertEqual(saved[0]['targets'],value['targets']);self.assertEqual(saved[0]['fit_admitted'],value['fit_admitted'])
        self.assertEqual(value['source_pins'],[]);self.assertEqual(len(saved[0]['source_pins']),4);self.assertIn('repair_provenance',saved[0]);self.assertIs(P.save_json,old_save)

    def test_baseline_copy_changes_only_five_wall_fields(self):
        original=(W.HERE/'binding_transfer_baselines.py').read_text();expected=original
        replacements={'seconds=10.':'seconds=5.','Guard(10.)':'Guard(5.)','remaining=10.-':'remaining=5.-','elapsed>10:':'elapsed>5:','exceeded10seconds':'exceeded5seconds'}
        for old,new in replacements.items():self.assertEqual(expected.count(old),1);expected=expected.replace(old,new)
        self.assertEqual((W.HERE/'binding_transfer_repair_baselines.py').read_text(),expected)
        ast.parse(expected)


if __name__=='__main__':unittest.main()
