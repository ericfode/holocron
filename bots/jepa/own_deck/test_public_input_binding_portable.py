import gzip
import json
from pathlib import Path
import tempfile
import unittest

import publication_checkpoint as P
from public_input_binding_portable import HistoricalClosure,SCHEMA,PACKAGE_BYTES,PACKAGE_FILES,file_pin


class HistoricalReferenceTests(unittest.TestCase):
    def prepare(self,root):
        original=root/'live.json';original.write_text('{"version":2}\n')
        archive=root/'archived.bin';raw=b'{"version":1}\n';archive.write_bytes(raw)
        declared=dict(path=str(original),sha256=P.digest(raw),bytes=len(raw))
        mapping=root/'mapping.json';mapping.write_bytes(P.encoded(dict(schema=SCHEMA,entries=[dict(declared=declared,archive=file_pin(archive),encoding='identity')],authority_pins=[])))
        return original,archive,declared,mapping

    def test_exact_historical_bytes_preserve_logical_origin_and_later_host(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);original,archive,declared,mapping=self.prepare(root);before=original.read_bytes()
            stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
            record=closure.copy(declared,root/'origin.json');self.assertEqual(closure.values[record['url']]['version'],1)
            self.assertEqual(original.read_bytes(),before);self.assertEqual(len(closure.historical_reads),1)
            self.assertGreater(closure.verify_sources_unchanged(),0)

    def test_unknown_path_hash_or_byte_count_never_gets_a_fallback(self):
        for field,value in(('sha256','0'*64),('bytes',999),('path','other.json')):
            with self.subTest(field=field),tempfile.TemporaryDirectory()as name:
                root=Path(name);_,_,declared,mapping=self.prepare(root);stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
                bad=dict(declared);bad[field]=str(root/value)if field=='path'else value
                with self.assertRaises((ValueError,FileNotFoundError)):closure.copy(bad,root/'origin.json')

    def test_archive_tampering_and_wrong_decoded_pin_fail_closed(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,archive,declared,mapping=self.prepare(root);stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
            archive.write_text('tampered')
            with self.assertRaisesRegex(ValueError,'archived payload'):closure.copy(declared,root/'origin.json')
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,archive,declared,mapping=self.prepare(root);archive.write_bytes(b'{"version":9}\n')
            value=json.loads(mapping.read_bytes());value['entries'][0]['archive']=file_pin(archive);mapping.write_bytes(P.encoded(value))
            stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
            with self.assertRaisesRegex(ValueError,'decoded payload'):closure.copy(declared,root/'origin.json')

    def test_missing_bytes_and_duplicate_declared_keys_are_rejected(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,_,_,mapping=self.prepare(root);value=json.loads(mapping.read_bytes());value['entries']*=2
            mapping.write_bytes(P.encoded(value));stage=root/'portable';stage.mkdir()
            with self.assertRaisesRegex(ValueError,'duplicate'):HistoricalClosure(stage,mapping)
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,_,_,mapping=self.prepare(root);value=json.loads(mapping.read_bytes());value['entries'][0]['declared'].pop('bytes')
            mapping.write_bytes(P.encoded(value));stage=root/'portable';stage.mkdir()
            with self.assertRaisesRegex(ValueError,'byte count'):HistoricalClosure(stage,mapping)

    def test_gzip_resolution_and_mapping_authority_tamper_checks(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,archive,declared,mapping=self.prepare(root);archive.write_bytes(gzip.compress(archive.read_bytes(),mtime=0))
            authority=root/'authority.json';authority.write_text('{}\n')
            value=json.loads(mapping.read_bytes());value['entries'][0].update(archive=file_pin(archive),encoding='gzip');value['authority_pins']=[file_pin(authority)]
            mapping.write_bytes(P.encoded(value));stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
            record=closure.copy(declared,root/'origin.json');self.assertEqual(closure.values[record['url']]['version'],1)
            mapping.write_bytes(mapping.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'mapping changed'):closure.verify_sources_unchanged()
            mapping.write_bytes(P.encoded(value));authority.write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'archive changed'):closure.verify_sources_unchanged()

    def test_fixed_publication_only_cap_and_checksummed_provenance_copies(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);_,_,_,mapping=self.prepare(root);stage=root/'portable';stage.mkdir();closure=HistoricalClosure(stage,mapping)
            self.assertEqual(closure.max_bytes,PACKAGE_BYTES);self.assertEqual(closure.max_files,PACKAGE_FILES)
            with self.assertRaisesRegex(ValueError,'fixed publication'):HistoricalClosure(root/'other',mapping,max_bytes=2*PACKAGE_BYTES)
            record=closure.store('manifest.json',P.encoded(dict(schema='synthetic')))
            value=json.loads((stage/record['url']).read_bytes());proof=value['provenance']
            self.assertEqual(proof['local_artifact_copy_bound']['final_measured_payload_bytes'],closure.total_bytes)
            for key in('mapping_raw_download','wrapper_raw_download'):
                pin=proof['historical_reference_resolution'][key];self.assertIn(pin['url'],closure.records)
                self.assertEqual(P.digest((stage/pin['url']).read_bytes()),pin['sha256'])


if __name__=='__main__':unittest.main()
