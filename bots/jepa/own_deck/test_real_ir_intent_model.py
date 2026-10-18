"""Primitive contract tests only: no arrays, Torch or model construction."""
import ast
import math
import unittest
from pathlib import Path

import real_ir_intent_model as M


class IntentContractTests(unittest.TestCase):
    def test_fixed_parameter_budget_and_existing_keys(self):
        counts = {a: sum(math.prod(s) for s in M.parameter_shapes(a).values())
                  for a in M.ARMS}
        self.assertEqual(counts, {'current': 1458, 'matched-aux-latent': 1517,
                                  'factorized-intent': 1517})
        self.assertEqual(M.parameter_shapes('matched-aux-latent'),
                         M.parameter_shapes('factorized-intent'))
        for key, value in M.parameter_shapes('current').items():
            self.assertEqual(M.parameter_shapes('factorized-intent')[key], value)

    def test_contract_keeps_nominal_amount_separate_from_application(self):
        c = M.contract()
        self.assertTrue(c['implementation_ready'])
        self.assertEqual(c['intent']['identity_classes'], ['damage', 'heal'])
        self.assertEqual(c['outputs']['intent_amount_native'], ['R'])
        self.assertEqual(c['supervision']['native'], {'eligibility': .5, 'endpoint': .5})
        self.assertEqual(c['supervision']['auxiliary'],
                         {'identity_cross_entropy': .25, 'literal_raw_smooth_l1': .25})
        self.assertIn('never clipped native delta', c['supervision']['labels'])
        self.assertFalse(c['semantic_validated'])
        self.assertFalse(c['production_promotion'])

    def test_invalid_arm_cannot_touch_a_framework(self):
        class ForbiddenFramework:
            def __getattr__(self, name):
                raise AssertionError('framework access before ROOT GO')
        with self.assertRaises(ValueError):
            M.make_model(ForbiddenFramework(), 'new-unknown-arm')

    def test_no_numerical_imports_or_old_source_mutation(self):
        tree = ast.parse(Path(M.__file__).read_text())
        roots = [node.names[0].name.split('.')[0] for node in ast.walk(tree)
                 if isinstance(node, ast.Import)]
        self.assertNotIn('torch', roots)
        self.assertNotIn('numpy', roots)
        self.assertEqual(M.base_pin()['sha256'], M.BASE_SHA256)

    def test_current_is_direct_original_without_a_wrapper(self):
        tree = ast.parse(Path(M.__file__).read_text())
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'make_model')
        assignment = next(n for n in factory.body if isinstance(n, ast.Assign) and
                          any(isinstance(t, ast.Name) and t.id == 'model' for t in n.targets))
        self.assertEqual(ast.unparse(assignment.value), "M.make_model(torch, 'new-full')")
        current = next(n for n in factory.body if isinstance(n, ast.If))
        self.assertEqual(ast.unparse(current.test), "arm == 'current'")
        self.assertEqual(ast.unparse(current.body[0]), 'return model')

    def test_card_only_readouts_and_factorized_route_have_no_state_bypass(self):
        tree = ast.parse(Path(M.__file__).read_text())
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'make_model')
        forward = next(n for n in factory.body if isinstance(n, ast.FunctionDef) and n.name == 'forward')
        assignments = {n.targets[0].id: ast.unparse(n.value) for n in forward.body
                       if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
        self.assertEqual(assignments['effect'], 'self.effect(p[:, 10:13])')
        self.assertEqual(assignments['identity_logits'], 'self.intent_identity(effect)')
        self.assertEqual(assignments['amount_native'], 'self.intent_amount(effect).squeeze(-1)')
        route = next(n for n in forward.body if isinstance(n, ast.If))
        self.assertEqual(ast.unparse(route.test), "arm == 'factorized-intent'")
        self.assertEqual(ast.unparse(route.body[-1]), 'application_effect = self.intent_lift(decoded)')
        self.assertEqual(ast.unparse(route.orelse[0]), 'application_effect = effect')
        self.assertIn('torch.softmax(identity_logits, dim=-1)', ast.unparse(route.body[0]))
        self.assertIn('amount_native[:, None] / LITERAL_SCALE', ast.unparse(route.body[0]))
        self.assertEqual(assignments['state'], 'self.state(c[..., 12:16])')
        self.assertEqual(assignments['raw'], 'self.endpoint(torch.cat((effect_rows, state, s), -1)).squeeze(-1)')
        self.assertNotIn('clamp', ast.unparse(forward))
        self.assertNotIn('argmax', ast.unparse(forward))


if __name__ == '__main__':
    unittest.main()
