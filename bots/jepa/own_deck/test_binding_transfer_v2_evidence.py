"""Portable, byte-only checks of the published experiment packet."""
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import unittest


PACKET = Path(__file__).resolve().parent / 'binding-transfer-v2-evidence'
MANIFEST_SHA = 'c59bfa15c89ecedd695785c032a4e865364f12f40dc4af44e1363742a3ebe871'


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('transfer_packet_checker', PACKET / 'repair/package_evidence.py')
        cls.checker = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(cls.checker)
        finally:
            sys.dont_write_bytecode = previous
        cls.manifest = json.loads((PACKET / 'manifest.json').read_text())

    def payload(self, role):
        records = [r for r in self.manifest['files'] if r['role'] == role]
        self.assertEqual(len(records), 1)
        record = records[0]
        raw = (PACKET / record['path']).read_bytes()
        return gzip.decompress(raw) if record['encoding'] == 'gzip' else raw

    def test_portable_offline_hash_inventory_and_privacy_verification(self):
        result = self.checker.verify(PACKET, MANIFEST_SHA, check_originals=False)
        self.assertEqual(result['status'], 'verified')
        self.assertFalse(result['originals_checked'])
        self.assertEqual(result['files'], 202)
        self.assertLess(result['stored_bytes'], 25 * 1024**2)

    def test_failed_origin_remains_failed_and_recovery_is_separate(self):
        rows = [json.loads(line) for line in self.payload('repair-ledger').decode().splitlines()]
        fit = rows[-1]['data']
        self.assertEqual((fit['stage'], fit['status']), ('fit', 'failed'))
        self.assertEqual(fit['charged']['seconds'], 60)
        self.assertIsNone(fit['observed']['optimizer_updates'])
        self.assertIsNone(fit['observed']['neural_forwards'])
        summary = self.manifest['summary']
        self.assertEqual(summary['fit_inventory']['prediction_files'], 36)
        self.assertEqual(summary['fit_durable_prefix']['optimizer_updates'], 5400)
        self.assertEqual(summary['fit_durable_prefix']['evaluation_forwards'], 36)
        self.assertFalse(summary['semantic_validated'])
        self.assertTrue(all(v == 0 for v in summary['science_performed_by_packager'].values()))

    def test_verified_closure_retains_budget_and_negative_control_decision(self):
        closure = json.loads(self.payload('final-pins'))
        self.assertEqual(closure['verification'], dict(status='PASS', checks=93471, mismatches=0))
        self.assertEqual(closure['native']['new_successful_applications'], 48)
        self.assertEqual(closure['native']['cumulative_charged_applications'], 208)
        self.assertIsNone(closure['native']['historical_observed_applications'])
        self.assertLessEqual(closure['budget']['phaseB_charged_seconds'], 80)
        self.assertTrue(closure['budget']['all_failed_charges_retained'])
        self.assertEqual(closure['budget']['new_paid_spend_usd'], 0)
        self.assertTrue(closure['decisions']['public_aspect_content_narrow_benefit'])
        self.assertTrue(closure['decisions']['intended_relation_narrow_benefit'])
        self.assertFalse(closure['decisions']['typed_program_transfer_beyond_all_controls'])
        self.assertFalse(closure['decisions']['semantic_validated'])


if __name__ == '__main__':
    unittest.main()
