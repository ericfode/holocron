"""Pure synthetic checks; the actual assembler/config/ledger is never run."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name("assemble_binding_transfer_config.py")
spec = importlib.util.spec_from_file_location("repair_assembler_under_test", SOURCE)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class AssemblerTests(unittest.TestCase):
    def test_four_stages_reuse_old_native_inputs_and_new_outputs(self):
        descriptors, paths = C.stage_descriptors(C.OLD / "learner-prepared-v1.json")
        self.assertEqual(tuple(descriptors), ("prep", "fit", "baselines", "verify"))
        self.assertEqual(descriptors["prep"]["argv"][2], "prep")
        self.assertNotIn("--ledger", descriptors["prep"]["argv"])
        for name in ("native_receipt", "journal", "native_plan", "prepared"):
            self.assertTrue(Path(paths[name]).is_relative_to(C.OLD))
        for stage, descriptor in descriptors.items():
            self.assertEqual(descriptor["argv"][0], str(C.PYTHON))
            self.assertTrue(all(Path(path).is_relative_to(C.CAMPAIGN) for path in descriptor["outputs"]))
            if stage != "prep":
                args = descriptor["argv"]
                self.assertEqual(args[args.index("--plan") + 1], paths["sealed"])
        self.assertEqual(descriptors["verify"]["argv"][2::2],
            ["--plan", "--fit-dir", "--fit-progress", "--baselines-dir", "--baseline-progress", "--out", "--receipt"])
        self.assertEqual(descriptors["verify"]["outputs"], [paths["verify"], paths["verification_receipt"]])

    def test_ast_closure_never_executes_local_or_numeric_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entry.py").write_text("import torch\nimport leaf\nraise RuntimeError('never run')\n")
            (root / "leaf.py").write_text("import entry\n")
            with patch.object(C, "OWN", root):
                pins = C.source_closure([root / "entry.py"])
            self.assertEqual({Path(value["path"]).name for value in pins}, {"entry.py", "leaf.py"})

    def test_exact_pins_deduplicate_and_reject_modified_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source"
            path.write_bytes(b"old")
            expected = C.pin(path)
            self.assertEqual(C.unique_pins([expected, expected]), [expected])
            path.write_bytes(b"new")
            with self.assertRaisesRegex(ValueError, "changed"):
                C.unique_pins([expected])

    def test_exclusive_metadata_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            C.exclusive_json(path, dict(value=1))
            old = path.read_bytes()
            with self.assertRaises(FileExistsError):
                C.exclusive_json(path, dict(value=2))
            self.assertEqual(old, path.read_bytes())

    def test_source_has_no_initialization_science_or_process_execution(self):
        tree = ast.parse(SOURCE.read_text())
        calls = {ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
        for name in ("A.initialize", "A.lease", "A.start", "A.finish", "subprocess.run", "os.system"):
            self.assertNotIn(name, calls)
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertFalse(imports & {"torch", "numpy", "socket", "subprocess"})
        self.assertIn("A.make_config", calls)
        self.assertNotIn("cache_snapshots", calls)


if __name__ == "__main__":
    unittest.main()
