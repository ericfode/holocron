"""Temporary byte fixtures only: no scientific imports or actual packaging."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import ability_diagnostic_package as P


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.roots = {name:self.base/name for name in P.NAMES}
        for root in self.roots.values():
            root.mkdir();(root/'experiment-closure.json').write_bytes(b'{ "status": "closed", "negative": true }\n')
            (root/'campaign-ledger.jsonl').write_bytes(b'{"stage":"start"}\n{"stage":"failed","observed":null}\n')
        self.prior = self.base/'old-manifest.json';self.prior.write_bytes(b'{"old":"immutable"}\n')
        self.prior_sha = P.digest(self.prior.read_bytes())
        self.out = self.base/'packet'

    def arguments(self):
        return dict(roots=self.roots,prior_manifest=self.prior,prior_sha=self.prior_sha)

    def test_prepare_is_readonly_and_requires_all_three_campaigns(self):
        plan = P.prepare(self.out,**self.arguments())
        self.assertFalse(self.out.exists());self.assertEqual(len(plan['files']),6)
        (self.roots[P.NAMES[2]]/'campaign-ledger.jsonl').unlink()
        (self.roots[P.NAMES[2]]/'experiment-closure.json').unlink()
        self.roots[P.NAMES[2]].rmdir()
        with self.assertRaisesRegex(ValueError,'absent'):P.prepare(self.out,**self.arguments())

    def test_raw_roundtrip_jsonl_and_opaque_npz(self):
        root=self.roots[P.NAMES[0]];blob=b'not-a-numerical-import\x00\x01'
        (root/'arrays.npz').write_bytes(blob);(root/'stderr.log').write_bytes(b'original failure\n')
        result=P.build(self.out,**self.arguments());self.assertEqual(result['status'],'verified-bytes-only')
        manifest=json.loads((self.out/'manifest.json').read_bytes())
        for entry in manifest['files']:
            if entry['path']=='index.json':continue
            stored=(self.out/entry['path']).read_bytes()
            raw=gzip.decompress(stored)if entry['encoding']=='gzip'else stored
            self.assertEqual(raw,Path(entry['provenance']['original_path']).read_bytes())
        self.assertEqual((self.out/'raw'/P.NAMES[0]/'arrays.npz').read_bytes(),blob)
        self.assertTrue((self.out/'raw'/P.NAMES[0]/'campaign-ledger.jsonl.gz').exists())

    def test_deterministic_bytes_and_offline_verification(self):
        first=P.build(self.out,**self.arguments());second_path=self.base/'packet2'
        second=P.build(second_path,**self.arguments())
        self.assertEqual(first['manifest_sha256'],second['manifest_sha256'])
        for root in self.roots.values():
            for path in root.iterdir():path.unlink()
            root.rmdir()
        self.prior.unlink()
        self.assertEqual(P.verify(self.out,first['manifest_sha256']),first)

    def test_old_pin_and_existing_destination_preserved(self):
        old=self.prior.read_bytes();P.build(self.out,**self.arguments())
        before=(self.out/'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):P.build(self.out,**self.arguments())
        self.assertEqual((self.out/'manifest.json').read_bytes(),before);self.assertEqual(self.prior.read_bytes(),old)
        with self.assertRaisesRegex(ValueError,'historical'):P.prepare(self.base/'other',self.roots,self.prior,'0'*64)

    def test_binary_cache_and_lock_exclusions_retain_build_logs(self):
        root=self.roots[P.NAMES[1]];(root/'build-1').mkdir()
        (root/'build-1'/P.BINARY).write_bytes(b'executable-not-copied')
        (root/'build-1'/'stdout.log').write_text('warm cache disclosed\n')
        (root/'target').mkdir();(root/'target'/'binary').write_bytes(b'cache')
        (root/'campaign-ledger.jsonl.lock').write_bytes(b'volatile')
        (root/'Cargo.lock').write_bytes(b'preserved source lockfile\n')
        plan=P.prepare(self.out,**self.arguments());self.assertEqual(len(plan['excluded']),1)
        self.assertEqual(plan['excluded'][0]['sha256'],P.digest(b'executable-not-copied'))
        self.assertTrue(any(e['path'].endswith('stdout.log')for e in plan['files']))
        self.assertTrue(any(e['path'].endswith('Cargo.lock')for e in plan['files']))
        P.build(self.out,**self.arguments());self.assertFalse((self.out/'raw'/P.NAMES[1]/'build-1'/P.BINARY).exists())

    def test_unknown_files_and_symlinks_fail_closed(self):
        root=self.roots[P.NAMES[0]];(root/'unreviewed.bin').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'unreviewed'):P.prepare(self.out,**self.arguments())
        (root/'unreviewed.bin').unlink();(root/'alias.json').symlink_to(self.prior)
        with self.assertRaisesRegex(ValueError,'symlink'):P.prepare(self.out,**self.arguments())

    def test_corruption_extra_membership_and_expected_manifest_pin(self):
        receipt=P.build(self.out,**self.arguments())
        with self.assertRaisesRegex(ValueError,'manifest pin'):P.verify(self.out,'0'*64)
        (self.out/'extra.log').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'membership'):P.verify(self.out,receipt['manifest_sha256'])
        (self.out/'extra.log').unlink()
        payload=self.out/'raw'/P.NAMES[0]/'campaign-ledger.jsonl.gz'
        corrupted=bytearray(payload.read_bytes());corrupted[0]^=1;payload.write_bytes(corrupted)
        with self.assertRaisesRegex(ValueError,'stored pin'):P.verify(self.out,receipt['manifest_sha256'])

    def test_payload_traversal_rejected(self):
        P.build(self.out,**self.arguments());path=self.out/'manifest.json';m=json.loads(path.read_bytes())
        m['files'][0]['path']='../outside.json';path.write_bytes(P.encode(m))
        with self.assertRaisesRegex(ValueError,'unsafe'):P.verify(self.out)

    def test_oversize_declarations_rejected_before_payload_read(self):
        P.build(self.out,**self.arguments());path=self.out/'manifest.json';original=json.loads(path.read_bytes())
        for field in ('raw_bytes','bytes'):
            changed=json.loads(json.dumps(original));changed['files'][0][field]=P.MAX_SINGLE+1
            path.write_bytes(P.encode(changed))
            with self.assertRaisesRegex(ValueError,'single-payload'):P.verify(self.out)
        changed=json.loads(json.dumps(original));changed['files']=[dict(changed['files'][0],path='raw/'+str(i),raw_bytes=P.MAX_SINGLE)for i in range(3)]
        path.write_bytes(P.encode(changed))
        with self.assertRaisesRegex(ValueError,'aggregate raw'):P.verify(self.out)
        changed=json.loads(json.dumps(original));changed['files']*=P.MAX_FILES
        path.write_bytes(P.encode(changed))
        with self.assertRaisesRegex(ValueError,'file-count'):P.verify(self.out)

    def test_bomb_and_truncated_gzip_rejected_with_bounded_read(self):
        P.build(self.out,**self.arguments());path=self.out/'manifest.json';original=json.loads(path.read_bytes())
        for payload,declared,message in [(gzip.compress(b'x'*8192,mtime=0),4,'decoded size'),
                                         (gzip.compress(b'abcd',mtime=0)[:-8],4,'bounded gzip')]:
            changed=json.loads(json.dumps(original));entry=changed['files'][0]
            (self.out/entry['path']).write_bytes(payload)
            entry.update(bytes=len(payload),sha256=P.digest(payload),raw_bytes=declared)
            path.write_bytes(P.encode(changed))
            with self.assertRaisesRegex(ValueError,message):P.verify(self.out)

    def test_prepare_checks_file_size_before_read(self):
        path=self.roots[P.NAMES[0]]/'oversize.npz'
        with path.open('wb')as stream:stream.truncate(P.MAX_SINGLE+1)
        with self.assertRaisesRegex(ValueError,'size limit'):P.prepare(self.out,**self.arguments())


if __name__=='__main__':unittest.main()
