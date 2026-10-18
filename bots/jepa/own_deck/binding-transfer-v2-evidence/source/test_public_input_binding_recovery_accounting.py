import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import public_input_binding_recovery_accounting as A


TIME=dict(pr36=1.,pr37=2.,linked_two_cycle_total=3.)

CARRY=dict(status='failed-v1-preserved-without-credit',charged_native_applies=80,observed_native_applies=None,
           known_native_apply_lower_bound=0,charged_native_seconds=60.5,analysis_charged_seconds=0.,supplemental_static_engine_apply_calls=0)

class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.parent_patch=patch.object(A,'recovery_parent',return_value=CARRY);self.parent_patch.start()
    def tearDown(self):self.parent_patch.stop()
    def config(self, root):
        source = root/'input.txt'; source.write_text('pure fixture\n')
        x = dict(schema='jepa-public-input-binding-recovery-config/1', limits=copy.deepcopy(A.CAPS),
                 parent_pins=copy.deepcopy(A.PARENT_PINS), parent_final_chains=A.PARENT_CHAINS[:],
                 prior_exposure=A.PRIOR_EXPOSURE.copy(), prior_charged_seconds=TIME.copy(), recovery_parent=CARRY.copy(), recovery_cumulative_limits=A.CUMULATIVE_CAPS.copy(), analysis_stages=A.ANALYSIS_STAGES.copy(),
                 analysis_commands={stage:dict(argv=[str(Path(A.__file__).resolve())],outputs=[str(root/stage)])for stage in A.ANALYSIS_STAGES},
                 pins=[A.pin(Path(A.__file__)), A.pin(source)])
        x['config_sha256'] = A.digest(x); path = root/'config.json'; path.write_text(json.dumps(x))
        return path

    def test_success_build_collect_analysis_preserve_observed_counters(self):
        with tempfile.TemporaryDirectory() as name, patch.object(A, 'verify_parents',return_value=TIME):
            root=Path(name).resolve(); ledger=root/'ledger.jsonl'
            with patch.object(A, 'LEDGER', ledger):
                A.initialize(self.config(root), ledger)
                with A.lease(ledger) as (stream, rows, _):
                    A.start(stream,rows,'native-build',{}); A.finish(stream,rows,'completed',.2)
                    A.start(stream,rows,'native-collect',{}); s=A.finish(stream,rows,'completed',.4,17)
                    self.assertEqual(s['observed_native_applies'],17); self.assertEqual(s['charged_native_applies'],17)
                    self.assertEqual(s['recovery_cumulative']['charged_native_applies'],97)
                    self.assertIsNone(s['recovery_cumulative']['observed_native_applies'])
                    self.assertEqual(s['recovery_cumulative']['observed_v2_native_applies'],17)
                    A.start(stream,rows,'analysis-controls',{}); s=A.finish(stream,rows,'completed',.1)
                    self.assertAlmostEqual(s['charged_seconds'],.7); self.assertEqual(s['numerical_fits'],0)
                    with self.assertRaises(ValueError): A.start(stream,rows,'native-collect',{})

    def test_failed_build_charges_own_time_zero_engine_and_prevents_collect_or_retry(self):
        with tempfile.TemporaryDirectory() as name, patch.object(A, 'verify_parents',return_value=TIME):
            root=Path(name).resolve(); ledger=root/'ledger.jsonl'
            with patch.object(A,'LEDGER',ledger):
                A.initialize(self.config(root),ledger)
                with A.lease(ledger) as (stream,rows,_):
                    A.start(stream,rows,'native-build',{});s=A.finish(stream,rows,'failed',.5)
                    self.assertEqual(s['charged_seconds'],30);self.assertEqual(s['observed_native_applies'],0)
                    for stage in ['native-build','native-collect']:
                        with self.assertRaises(ValueError):A.start(stream,rows,stage,{})

    def test_failed_collection_reservation_distinct_from_actual_or_unknown(self):
        for verified in [True,False]:
            with self.subTest(verified=verified),tempfile.TemporaryDirectory()as name,patch.object(A,'verify_parents',return_value=TIME):
                root=Path(name).resolve();ledger=root/'ledger.jsonl'
                with patch.object(A,'LEDGER',ledger):
                    A.initialize(self.config(root),ledger)
                    with A.lease(ledger)as(stream,rows,_):
                        A.start(stream,rows,'native-build',{});A.finish(stream,rows,'completed',.1)
                        A.start(stream,rows,'native-collect',{});s=A.finish(stream,rows,'failed',.2,3,native_journal_verified=verified)
                        self.assertEqual(s['charged_native_applies'],80);self.assertEqual(s['known_native_apply_lower_bound'],3)
                        self.assertEqual(s['observed_native_applies'],3 if verified else None)
                        self.assertAlmostEqual(s['charged_seconds'],60.1)

    def test_pending_path_copy_hash_tamper_and_reset_blocked(self):
        with tempfile.TemporaryDirectory()as name,patch.object(A,'verify_parents',return_value=TIME):
            root=Path(name).resolve();ledger=root/'ledger.jsonl'
            with patch.object(A,'LEDGER',ledger):
                config=self.config(root);A.initialize(config,ledger)
                with self.assertRaises(FileExistsError):A.initialize(config,ledger)
                with A.lease(ledger)as(stream,rows,_):A.start(stream,rows,'native-build',{})
                with self.assertRaises(ValueError):
                    with A.lease(ledger):pass
                copied=root/'copy.jsonl';copied.write_bytes(ledger.read_bytes())
                with self.assertRaises(ValueError):
                    with A.lease(copied):pass
                records=[json.loads(x)for x in ledger.read_text().splitlines()];records[-1]['data']['attempt']=0
                with self.assertRaises(ValueError):A.state(records)

    def test_limits_or_parent_exposure_cannot_change(self):
        with tempfile.TemporaryDirectory()as name:
            config=json.loads(self.config(Path(name)).read_text())
            for change in ['neural','parent','seconds']:
                x=copy.deepcopy(config)
                if change=='neural':x['limits']['neural_forwards']=1
                elif change=='parent':x['prior_exposure']['optimizer_updates']=0
                else:x['analysis_stages']['analysis-controls']=31
                x['config_sha256']=A.digest({k:v for k,v in x.items()if k!='config_sha256'})
                with self.assertRaises(ValueError):A.validate_config(x)

    def test_failed_analysis_charges_full_stage_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory()as name,patch.object(A,'verify_parents',return_value=TIME):
            root=Path(name).resolve();ledger=root/'ledger.jsonl'
            with patch.object(A,'LEDGER',ledger):
                A.initialize(self.config(root),ledger)
                with A.lease(ledger)as(stream,rows,_):
                    A.start(stream,rows,'analysis-controls',{});s=A.finish(stream,rows,'failed',.2)
                    self.assertEqual(s['charged_seconds'],15);self.assertEqual(s['observed_seconds'],.2)
                    with self.assertRaises(ValueError):A.start(stream,rows,'analysis-controls',{})
                    with self.assertRaises(ValueError):A.append(stream,rows,'credit',{})

    def test_overrun_is_recorded_failed_and_blocks_all_later_work(self):
        with tempfile.TemporaryDirectory()as name,patch.object(A,'verify_parents',return_value=TIME):
            root=Path(name).resolve();ledger=root/'ledger.jsonl'
            with patch.object(A,'LEDGER',ledger):
                A.initialize(self.config(root),ledger)
                with A.lease(ledger)as(stream,rows,_):
                    A.start(stream,rows,'analysis-controls',{});s=A.finish(stream,rows,'failed',15.1)
                    self.assertTrue(s['ceiling_violated'])
                    with self.assertRaises(ValueError):A.start(stream,rows,'analysis-verification',{})


if __name__=='__main__':unittest.main()
