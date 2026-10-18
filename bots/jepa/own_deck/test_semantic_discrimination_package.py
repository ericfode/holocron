"""Only temporary synthetic byte files; no actual campaign copying."""
import gzip
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import semantic_discrimination_package as P


class PackageTests(unittest.TestCase):
    def test_deterministic_portable_bytes_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);sources=[]
            for name in P.ROOT_NAMES:
                path=root/name;path.mkdir();sources.append(path)
                (path/'failed-journal.jsonl').write_bytes(b'{"event":"start"}\n{"event":"failed"}\n')
                (path/'weights.npz').write_bytes(b'PK\0synthetic-opaque-npz-only')
            (sources[0]/'old-archive.tar.gz').write_bytes(b'not-to-copy')
            (sources[0]/'native-collector').write_bytes(b'\x7fELF\0native-binary')
            (sources[0]/'target').mkdir();(sources[0]/'target'/'cache').write_bytes(b'cache')
            (sources[0]/'link').symlink_to(sources[1]/'failed-journal.jsonl')
            first=root/'first';second=root/'second';commits=['a'*40,'b'*40]
            P.package(sources,first,commits);P.package(sources,second,commits)
            left={p.relative_to(first):p.read_bytes()for p in first.rglob('*')if p.is_file()};right={p.relative_to(second):p.read_bytes()for p in second.rglob('*')if p.is_file()};self.assertEqual(left,right)
            manifest=json.loads((first/'manifest.json').read_text());self.assertEqual(6,manifest['files']);self.assertEqual(4,len(manifest['excluded']))
            record=next(r for r in manifest['records']if r['relative_path']=='failed-journal.jsonl');self.assertEqual(b'{"event":"start"}\n{"event":"failed"}\n',gzip.decompress((first/record['stored']['path']).read_bytes()))
            for source in sources:shutil.rmtree(source)
            self.assertTrue(P.verify(first)['verified'])
            payload=first/record['stored']['path'];payload.write_bytes(payload.read_bytes()+b'corrupt')
            with self.assertRaisesRegex(ValueError,'stored pin mismatch'):P.verify(first)
            with self.assertRaises(FileExistsError):second.mkdir(exist_ok=False)


if __name__=='__main__':unittest.main()
