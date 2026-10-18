"""Pure temporary-file and descriptor checks; no saved-output processing."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name("assemble_binding_transfer_config.py")
spec = importlib.util.spec_from_file_location("report_assembler_under_test", SOURCE)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class AssemblerTests(unittest.TestCase):
    def test_three_stages_reuse_immutable_old_fit_and_create_only_new_outputs(self):
        descriptors, paths = C.stage_descriptors(C.OLD / "prep-1/sealed-fit-plan.json")
        self.assertEqual(tuple(descriptors), ("recover", "baselines", "verify"))
        self.assertEqual(descriptors["recover"]["argv"][2], "recover")
        self.assertEqual(descriptors["baselines"]["argv"][2], "baselines")
        for key in ("plan", "old_fit", "old_progress", "old_ledger", "old_failed_receipt"):
            self.assertTrue(Path(paths[key]).is_relative_to(C.OLD))
        for descriptor in descriptors.values():
            self.assertEqual(descriptor["argv"][0], str(C.PYTHON))
            self.assertTrue(all(Path(p).is_relative_to(C.CAMPAIGN) for p in descriptor["outputs"]))
            self.assertNotIn(paths["old_progress"], descriptor["outputs"])
        args = descriptors["recover"]["argv"]
        self.assertEqual(args[args.index("--failed-ledger") + 1], paths["old_ledger"])
        self.assertEqual(args[args.index("--failed-receipt") + 1], paths["old_failed_receipt"])
        self.assertNotIn("--inventory", args)
        self.assertEqual(descriptors["verify"]["argv"][2::2],
            ["--plan", "--fit-dir", "--fit-progress", "--baselines-dir", "--baseline-progress", "--out", "--receipt",
             "--recovered-result", "--failed-fit-ledger", "--failed-fit-receipt"])
        self.assertEqual(descriptors["verify"]["outputs"], [paths["verify"], paths["verification_receipt"]])

    def test_ast_closure_never_executes_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entry.py").write_text("import torch\nimport leaf\nraise RuntimeError('never run')\n")
            (root / "leaf.py").write_text("import entry\n")
            with patch.object(C, "OWN", root):
                values = C.source_closure([root / "entry.py"])
            self.assertEqual({Path(v["path"]).name for v in values}, {"entry.py", "leaf.py"})

    def test_pins_deduplicate_and_fail_on_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source"
            path.write_bytes(b"original")
            expected = C.pin(path)
            self.assertEqual(C.unique_pins([expected, expected]), [expected])
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                C.unique_pins([expected])

    def test_metadata_output_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            C.exclusive_json(path, dict(value=1))
            old = path.read_bytes()
            with self.assertRaises(FileExistsError):
                C.exclusive_json(path, dict(value=2))
            self.assertEqual(path.read_bytes(), old)

    def test_source_cannot_initialize_or_run_recovery_fit_native_or_nn(self):
        tree = ast.parse(SOURCE.read_text())
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for name in ("A.initialize", "A.lease", "A.start", "A.finish", "subprocess.run", "os.system", "np.load"):
            self.assertNotIn(name, calls)
        imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse(imports & {"torch", "numpy", "subprocess", "socket"})
        self.assertIn("A.make_config", calls)


if __name__ == "__main__":
    unittest.main()
