"""Synthetic lifecycle tests only: no actual campaign, data conversion or fit."""
import ast
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import binding_transfer_prep as P


class FakeGuard:
    active=False
    def __init__(self,seconds):self.seconds=seconds
    def __enter__(self):type(self).active=True;return self
    def __exit__(self,*args):type(self).active=False
    def receipt(self):return dict(seconds=self.seconds)


class Tests(unittest.TestCase):
    def test_metadata_uses_frozen_and_completed_proofs_without_reading_inputs(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();out=root/'prep-1';a,b=root/'a',root/'b'
            pa=dict(path=str(a),sha256='a'*64,bytes=123);pb=dict(path=str(b),sha256='b'*64,bytes=456)
            current=dict(config=dict(pins=[pa]));rows=[dict(event='stage-finish',data=dict(status='completed',proofs=[pb]))]
            value,expected,receipt=P.metadata(current,rows,[a,b],out,['python','script'])
            self.assertEqual(expected,[pa,pb]);self.assertEqual(value['input_pins'],expected)
            self.assertEqual(value['outputs'],[str(out),str(out.parent/'prep-1-stage-receipt.json')]);self.assertFalse(a.exists())

    def lifecycle(self,root,start_error=None,prepare_error=None):
        paths=[root/name for name in('raw','journal','plan','prepared')]
        for p in paths:p.write_text('synthetic')
        current=dict(config=dict(pins=[P.A.pin(p)for p in paths]));rows=[];out=root/'prep-1';events=[];finish_calls=[]
        @contextmanager
        def lease(_):yield None,rows,current
        def start(stream,r,stage,metadata):
            events.append('start');rows.append(dict(event='started'))
            if start_error:raise start_error
        def prepare(*args):
            self.assertTrue(FakeGuard.active);events.append('guarded-conversion')
            if prepare_error:raise prepare_error
            (out/'dataset.npz').write_text('synthetic-array-output')
            (out/'dataset.manifest.json').write_text('synthetic-manifest')
            (out/'sealed-fit-plan.json').write_text('synthetic-seal')
            return dict(fit_admitted=True)
        def finish(*args,**kwargs):
            finish_calls.append((args,kwargs));events.append('finish')
            return dict(completed_stages=['prep']if args[2]=='completed'else[],last_record_sha256='f'*64,charged=dict(seconds=5 if args[2]=='failed'else args[3]),observed=args[4])
        pending=dict(pending=dict(stage='prep',owner_pid=os.getpid()))
        stack=[mock.patch.object(P.A,'lease',lease),mock.patch.object(P.A,'start',start),mock.patch.object(P.A,'state',return_value=pending),mock.patch.object(P.A,'finish',finish),mock.patch.object(P.A,'verify_links'),mock.patch.object(P.A,'verify_output_protection'),mock.patch.object(P.E,'Guard',FakeGuard),mock.patch.object(P,'prepare_outputs',prepare)]
        return paths,out,events,finish_calls,stack

    def exercise(self,root,**kwargs):
        from contextlib import ExitStack
        paths,out,events,finished,patches=self.lifecycle(root,**kwargs)
        with ExitStack()as stack:
            for patch in patches:stack.enter_context(patch)
            if kwargs:
                with self.assertRaisesRegex(RuntimeError,'failed prep retained'):P.run(*paths,out,root/'ledger',argv=['python','script'])
                result=None
            else:result=P.run(*paths,out,root/'ledger',argv=['python','script'])
        return out,events,finished,result

    def test_success_has_guard_and_zero_counters_and_all_output_proofs(self):
        with tempfile.TemporaryDirectory()as tmp:
            out,events,finished,result=self.exercise(Path(tmp))
            self.assertEqual(events,['start','guarded-conversion','finish']);self.assertEqual(result['status'],'completed')
            args,kw=finished[0];self.assertEqual(args[4],P.A.zero_counts());self.assertTrue(kw['cleanup_verified']and kw['execution_ended'])
            self.assertEqual({Path(p['path']).name for p in args[5]},{'prep-1-stage-receipt.json','dataset.npz','dataset.manifest.json','sealed-fit-plan.json','receipt.json'})
            self.assertFalse(FakeGuard.active)

    def test_durable_start_failure_finishes_failed_without_import_or_conversion(self):
        with tempfile.TemporaryDirectory()as tmp:
            out,events,finished,_=self.exercise(Path(tmp),start_error=ValueError('changed frozen pin'))
            self.assertEqual(events,['start','finish']);self.assertFalse(out.exists())
            self.assertEqual(finished[0][0][2],'failed');self.assertEqual(finished[0][0][4],P.A.zero_counts())
            self.assertTrue((out.parent/'prep-1-stage-receipt.json').exists())

    def test_guarded_unknown_or_private_data_rejection_preserves_failure(self):
        for message in('unknown physical counter','hidden private pile'):
            with self.subTest(message=message),tempfile.TemporaryDirectory()as tmp:
                out,events,finished,_=self.exercise(Path(tmp),prepare_error=ValueError(message))
                self.assertEqual(events,['start','guarded-conversion','finish']);self.assertEqual(finished[0][0][2],'failed')
                receipt=P.json.loads((out/'receipt.json').read_text());self.assertEqual(receipt['error']['message'],message)
                self.assertFalse(FakeGuard.active)

    def test_no_top_level_numerical_import_or_execution(self):
        tree=ast.parse(Path(P.__file__).read_text());names=[]
        for node in tree.body:
            if isinstance(node,ast.Import):names.extend(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):names.append(node.module)
        self.assertFalse(set(names)&{'numpy','torch','binding_transfer_data','binding_transfer_fit'})
        self.assertEqual(P.SECONDS,5.)

    def test_unadmitted_converter_output_cannot_reach_learner_seal(self):
        import numpy as np
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);seal=mock.Mock()
            D=SimpleNamespace(read=lambda p:dict(source_pins=[])if p.name=='plan'else dict(collectionPlanSha256='s'),sha=lambda _: 's',quantity_support=mock.Mock(),
                convert_receipt=lambda *a:({},dict(fit_admitted=False,quantity_support_gate=dict(passed=False),fit_blockers=['unknown-native-counter'])),G=SimpleNamespace(assembled_catalog=lambda _: {},PINNED_KESSEL=root))
            with mock.patch.object(P.importlib,'import_module',side_effect=[D,SimpleNamespace(seal=seal)]),mock.patch.object(P.A,'pin',side_effect=lambda p:dict(path=str(p),sha256='s',bytes=1)),mock.patch.object(np,'savez_compressed'):
                with self.assertRaisesRegex(ValueError,'did not admit'):P.prepare_outputs(root/'raw',root/'journal',root/'plan',root/'prepared',root)
            seal.assert_not_called();self.assertTrue((root/'dataset.manifest.json').exists())


if __name__=='__main__':unittest.main()
