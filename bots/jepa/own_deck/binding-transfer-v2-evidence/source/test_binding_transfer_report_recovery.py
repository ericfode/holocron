import argparse
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import binding_transfer_report_recovery as R


class Scalar:
    def __init__(self,value):self.value=value
    def item(self):return self.value


class SavedReportTests(unittest.TestCase):
    def test_import_does_not_import_neural_or_numerical_library(self):
        subprocess.run([sys.executable,'-B','-c','import sys; import binding_transfer_report_recovery; assert "torch" not in sys.modules and "numpy" not in sys.modules'],cwd=Path(R.__file__).parent,check=True,capture_output=True)

    def test_recursive_scalar_conversion_preserves_types_and_values(self):
        fake=SimpleNamespace(generic=Scalar)
        value={'roots':[Scalar(3),Scalar(7)],'nested':{Scalar(2):(Scalar(True),Scalar(.125),None)},'literal':'same'}
        result=R.native_json(value,fake)
        self.assertEqual(result,{'roots':[3,7],'nested':{2:[True,.125,None]},'literal':'same'})
        self.assertIs(type(result['roots'][0]),int);self.assertIs(type(result['nested'][2][0]),bool);self.assertIs(type(result['nested'][2][1]),float)
        json.dumps(result,allow_nan=False)
        with self.assertRaises(TypeError):R.native_json(object(),fake)

    def test_saved_inventory_exact61_artifacts_no_result_substitution(self):
        args=argparse.Namespace(plan=Path('/plan'),fit_dir=Path('/fit'),progress=Path('/progress'),failed_ledger=Path('/ledger'),failed_receipt=Path('/receipt'))
        paths=R.inventory_paths(args);self.assertEqual(len(paths),65);self.assertEqual(len(set(paths)),65)
        self.assertEqual(sum('-predictions.npz'in p.name for p in paths),36);self.assertEqual(sum('-checkpoint.npz'in p.name and 'initial'not in p.name for p in paths),18)
        self.assertEqual(sum('initial-checkpoint.npz'in p.name for p in paths),3);self.assertNotIn(Path('/fit/result.json'),paths)

    def test_recovery_blocks_model_process_and_network(self):
        for event,args in(('import',('torch.nn',)),('subprocess.Popen',()),('os.fork',()),('socket.__new__',()),('socket.connect',())):
            with self.subTest(event=event),self.assertRaises(RuntimeError):R.audit_event(event,args)
        R.audit_event('import',('numpy',));R.audit_event('open',('/saved','r'))

    def test_recovery_ast_has_no_model_or_optimizer_calls(self):
        tree=ast.parse(Path(R.__file__).read_text());forbidden={'make_model','run_torch','forward','backward','execute','step','convert_receipt','fit_head','lstsq'}
        calls=[node.func.attr for node in ast.walk(tree)if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)]
        self.assertFalse(forbidden.intersection(calls))

    def test_baseline_route_only_normalizes_writer_and_restores(self):
        F=__import__('binding_transfer_fit');B=__import__('binding_transfer_repair_baselines');old=(F.accounting,F.stage_metadata,F.write)
        A=SimpleNamespace(start=lambda *_args:'reserved',LEDGER=R.ROOT/'campaign-ledger.jsonl');start=A.start;captured=[]
        with patch.object(F,'write',side_effect=lambda path,value:captured.append(value)):
            original=F.write
            with R.baseline_route(A)as bound:
                self.assertIs(bound,B);self.assertIs(F.accounting(),A);F.write(Path('/unused'),dict(roots=[3],metric=.5));self.assertIs(B.F,F)
            self.assertIs(F.write,original)
        self.assertEqual(captured,[dict(roots=[3],metric=.5)]);self.assertEqual((F.accounting,F.stage_metadata,F.write),old);self.assertIs(A.start,start)

    def test_baseline_audit_after_reservation(self):
        events=[];A=SimpleNamespace(start=lambda *_args:events.append('reserved'),LEDGER=R.ROOT/'campaign-ledger.jsonl')
        with patch.object(R,'verify_sources',side_effect=lambda *_args:events.append('audited')):
            with R.baseline_route(A):A.start(None,[],'baselines',dict(argv=R.argv()))
        self.assertEqual(events,['reserved','audited'])

    @unittest.skipUnless(importlib.util.find_spec('numpy'),'optional local NumPy synthetic regression')
    def test_real_numpy_nested_roots_from_frozen_evaluate(self):
        import numpy as np
        import binding_transfer_fit as F
        source_names=['s'+str(i)for i in range(9)];target_names=['target_allowed','target_removed','target_damage_delta','target_exhausted_delta','target_shield_delta','target_power_delta','target_hp_delta']
        arrays=dict(source_targets=np.zeros((4,9),np.float32),source_mask=np.ones((4,9),np.float32),targets=np.zeros((4,8,7),np.float32),target_mask=np.ones((4,8,7),np.float32),source_cards=np.asarray(['card']*4),selected_candidate_indices=np.zeros(4,np.int64))
        manifest=dict(family_ids=['family']*4,public_before_records=[dict(declared_intent=dict(requires_target=True))for _ in range(4)])
        specs=lambda names:[dict(name=n,binary=False,scale=1.)for n in names]
        plan=dict(split=dict(root_partitions=dict(train=[0],family_held=[1],state_held=[2],joint=[3])),scalers=dict(source_targets=specs(source_names),targets=specs(target_names)),primary_mechanics=['damage','stats'])
        metrics=F.evaluate(arrays['source_targets'],arrays['targets'],arrays,manifest,plan)
        root=metrics['train']['actual_endpoints']['families']['family']['roots'][0];self.assertIsInstance(root,np.int64)
        with self.assertRaises(TypeError):json.dumps(metrics)
        normalized=R.native_json(metrics,np);encoded=json.dumps(normalized,allow_nan=False)
        self.assertEqual(json.loads(encoded)['train']['actual_endpoints']['families']['family']['roots'],[0])
        self.assertEqual(normalized['train']['actual_endpoints']['heads']['target_damage_delta']['mae'],0.)
        with self.assertRaises(TypeError):R.native_json(np.zeros(2),np)


if __name__=='__main__':unittest.main()
