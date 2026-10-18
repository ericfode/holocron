"""Temporary synthetic evidence files only; no experiment or science execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location("binding_export",Path(__file__).with_name("public_input_binding_export.py"))
X=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(X)


class PortableBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.raw=self.root/"observations.json";self.raw.write_bytes(X.encoded(dict(public_state=[1,2,3],unknown_mask=[0,1],negative_result=True)))
        self.source=self.root/"source.py";self.source.write_bytes(b"# inert synthetic source; no execution\n")
        self.config=self.root/"config.json"
        declared=X.file_pin(self.source);declared["path"]="source.py"
        self.config.write_bytes(X.encoded(dict(schema="synthetic-test/1",pins=[declared],nested=dict(duplicate=copy.deepcopy(declared)),uninterpreted_path="not-a-source-pin")))
        self.entries=[X.artifact(role,role,self.raw)for role in sorted(X.REQUIRED)]

    def tearDown(self): self.temporary.cleanup()

    def test_deterministic_dedup_gzip_and_all_direct_pins_preserved(self):
        before={p:X.file_pin(p)for p in(self.raw,self.source,self.config)}
        a,b=self.root/"bundle-a",self.root/"bundle-b"
        X.build(self.config,a,self.entries,gzip_threshold=1)
        X.build(self.config,b,list(reversed(self.entries)),gzip_threshold=1)
        self.assertEqual((a/"index.json").read_bytes(),(b/"index.json").read_bytes())
        self.assertEqual((a/"manifest.json").read_bytes(),(b/"manifest.json").read_bytes())
        index=X.read_json(a/"index.json");manifest=X.read_json(a/"manifest.json")
        required=[e for e in index["artifacts"]if e["role"]in X.REQUIRED and e["id"]!="campaign-config"]
        self.assertEqual(len({e["url"]for e in required}),1)
        self.assertEqual(required[0]["encoding"],"gzip")
        stored=(a/required[0]["url"]).read_bytes();self.assertEqual(stored[4:8],bytes(4))
        self.assertEqual(len(manifest["direct_config_source_pins"]),2)
        self.assertEqual(X.direct_config_pins(X.read_json(self.config)),[{"pointer":v["pointer"],"declared_pin":v["declared_pin"]}for v in manifest["direct_config_source_pins"]])
        self.assertTrue(X.verify_bundle(a,expected_index_sha256=X.file_pin(a/"index.json")["sha256"],expected_manifest_sha256=X.file_pin(a/"manifest.json")["sha256"])["verified"])
        for p,pin in before.items():self.assertEqual(X.file_pin(p),pin)

    def test_portable_verify_does_not_fetch_original_paths(self):
        out=self.root/"bundle";X.build(self.config,out,self.entries)
        self.raw.unlink();self.source.unlink();self.config.unlink()
        self.assertTrue(X.verify_bundle(out)["verified"])
        with self.assertRaises(FileNotFoundError):X.verify_bundle(out,check_originals=True)

    def test_exclusive_bundle_and_extra_file_rejection(self):
        out=self.root/"bundle";X.build(self.config,out,self.entries)
        initial=(out/"index.json").read_bytes()
        with self.assertRaisesRegex(ValueError,"already exists"):X.build(self.config,out,self.entries)
        self.assertEqual((out/"index.json").read_bytes(),initial)
        (out/"extra.txt").write_text("unmanifested")
        with self.assertRaisesRegex(ValueError,"unmanifested"):X.verify_bundle(out)

    def test_changed_source_pin_rejected_before_output_creation(self):
        self.source.write_text("changed\n");out=self.root/"bundle"
        with self.assertRaisesRegex(ValueError,"source pin changed"):X.build(self.config,out,self.entries)
        self.assertFalse(out.exists())

    def test_stored_and_decoded_tampering_detected(self):
        out=self.root/"bundle";X.build(self.config,out,self.entries,gzip_threshold=1)
        index=X.read_json(out/"index.json");target=out/index["artifacts"][0]["url"]
        target.write_bytes(target.read_bytes()+b"tamper")
        with self.assertRaisesRegex(ValueError,"stored artifact pin"):X.verify_bundle(out)
        out2=self.root/"bundle2";X.build(self.config,out2,self.entries,gzip_threshold=1)
        index=X.read_json(out2/"index.json");manifest=X.read_json(out2/"manifest.json")
        index["artifacts"][0]["raw_sha256"]="0"*64;manifest["artifacts"]=index["artifacts"]
        raw=X.encoded(index);(out2/"index.json").write_bytes(raw)
        for item in manifest["files"]:
            if item["url"]=="index.json":item.update(sha256=X.digest(raw),bytes=len(raw))
        (out2/"manifest.json").write_bytes(X.encoded(manifest))
        with self.assertRaisesRegex(ValueError,"decoded raw pin"):X.verify_bundle(out2)

    def test_traversal_absolute_url_and_symlink_rejected(self):
        directory=self.root/"empty";directory.mkdir()
        for url in("../outside","/absolute","raw/../source","https://example.test/x","raw/%2e%2e/x","raw\\escape","raw//x"):
            with self.assertRaises(ValueError):X.safe_path(directory,url)
        (directory/"link").symlink_to(self.source)
        with self.assertRaisesRegex(ValueError,"symlink"):X.safe_path(directory,"link")

    def test_roles_ids_and_expected_pins_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"missing required"):X.build(self.config,self.root/"none",self.entries[:1])
        with self.assertRaisesRegex(ValueError,"duplicate artifact"):X.build(self.config,self.root/"dup",self.entries+self.entries[:1])
        with self.assertRaisesRegex(ValueError,"unsupported artifact role"):X.artifact("vectors","vectors",self.raw)
        wrong=copy.deepcopy(self.entries);wrong[0]["expected_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"artifact hash differs"):X.build(self.config,self.root/"wrong",wrong)
        with self.assertRaisesRegex(ValueError,"config byte hash"):X.build(self.config,self.root/"config-wrong",self.entries,expected_config_sha256="0"*64)

    def test_explicit_artifact_manifest_relative_paths_and_descriptor_copy(self):
        descriptor=self.root/"artifacts.json"
        descriptor.write_bytes(X.encoded(dict(artifacts=[dict(id=r,role=r,path="observations.json",sha256=X.file_pin(self.raw)["sha256"],bytes=self.raw.stat().st_size)for r in sorted(X.REQUIRED)])))
        entries=X.artifact_manifest(descriptor);out=self.root/"bundle";X.build(self.config,out,entries)
        index=X.read_json(out/"index.json")
        self.assertTrue(any(e["provenance"]["original_path"]==str(descriptor.resolve())for e in index["artifacts"]))
        self.assertTrue(all(not Path(e["url"]).is_absolute()and e["sha256"]and type(e["bytes"])is int for e in index["artifacts"]))


if __name__=="__main__":unittest.main()
