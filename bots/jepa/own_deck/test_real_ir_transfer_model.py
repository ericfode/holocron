"""Pure contracts/AST only: never construct a model or import Torch/NumPy."""
import ast
from pathlib import Path
import unittest
import real_ir_transfer_model as M


class ModelContractTest(unittest.TestCase):
    def test_exact_common_dimensions_and_fixed_scales(self):
        c=M.contract()
        self.assertEqual((len(c['program_fields']),len(c['candidate_fields']),len(c['source_printed_fields'])),(13,17,10))
        self.assertEqual(len(M.P_SCALE),13);self.assertEqual(len(M.C_SCALE),17);self.assertEqual(len(M.S_SCALE),10)
        self.assertEqual(M.CANDIDATE_FIELDS[16],'is_intended')
        self.assertEqual(M.C_SCALE[9],4.);self.assertEqual(M.C_SCALE[12],4.);self.assertEqual(M.C_SCALE[14],10.)

    def test_printed_control_allocates_same_named_shapes(self):
        self.assertEqual(M.parameter_shapes('new-full'),M.parameter_shapes('new-printed-only'))
        self.assertLess(M.contract()['parameters']['new-full']['allocated'],5000)
        self.assertNotEqual(M.parameter_shapes('new-full'),M.parameter_shapes('old-late-fusion'))
        self.assertIn('different graph',M.contract()['comparator'])

    def test_no_identity_or_text_feature_or_learned_identity_table(self):
        fields=M.PROGRAM_FIELDS+M.CANDIDATE_FIELDS+M.PRINTED_FIELDS
        self.assertFalse(any(any(word in f for word in ('code','title','text','identity')) for f in fields))
        self.assertFalse(any('identity' in n for a in M.ARMS for n in M.parameter_shapes(a)))
        self.assertEqual(M.parameter_shapes('old-late-fusion')['paths.weight'],(23,16))

    def test_safe_import_and_explicit_constructor_only(self):
        tree=ast.parse(Path(M.__file__).read_text())
        top_imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual([a.name for n in top_imports for a in n.names],['math'])
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='make_model' for n in tree.body))
        with self.assertRaises(ValueError):M.parameter_shapes('unapproved-arm')


if __name__=='__main__':unittest.main()
