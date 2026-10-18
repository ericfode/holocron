"""Synthetic accounting and call-proof checks; no numerical/runtime imports."""
import ast
import copy
from pathlib import Path
import unittest
import compositional_typed_campaign as C


class Campaign(unittest.TestCase):
    def fixture(self):
        cases = [{'world_id': i} for i in range(128)]
        raw = dict(collectionComplete=True, cases=cases, applyCalls=2)
        records = [dict(schema='jepa-compositional-typed-apply-journal/1')]
        for i in (1, 2):
            records += [dict(phase='beforeApply', applyCall=i), dict(phase='afterApply', applyCall=i)]
        records += [dict(phase='contextComplete', case=c) for c in cases]
        return raw, records

    def test_paired_native_counts(self):
        raw, rows = self.fixture()
        self.assertEqual(C.native_proof(raw, rows)['actual_native_applies'], 2)

    def test_missing_after_and_error_rejected(self):
        raw, rows = self.fixture()
        for bad in (rows[:2] + rows[3:], rows + [dict(phase='applyError', applyCall=3)]):
            with self.assertRaises(ValueError): C.native_proof(raw, bad)

    def test_incomplete_or_changed_case_rejected(self):
        raw, rows = self.fixture(); bad = copy.deepcopy(raw); bad['cases'][0]['world_id'] = 999
        with self.assertRaises(ValueError): C.native_proof(bad, rows)
        raw['collectionComplete'] = False
        with self.assertRaises(ValueError): C.native_proof(raw, rows)

    def test_frozen_allocation(self):
        self.assertEqual(sum(C.SECONDS.values()), 185)
        self.assertEqual(C.ZERO['paid_spend_usd'], 0)
        self.assertEqual(C.ZERO['paid_jobs'], 0)
        self.assertIn('backwards', C.ZERO)

    def test_no_scientific_imports_at_module_scope(self):
        tree = ast.parse(Path(C.__file__).read_text())
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = [a.name for n in imports for a in n.names]
        self.assertFalse(any(n.split('.')[0] in ('numpy', 'torch', 'kessel') for n in names))


if __name__ == '__main__': unittest.main()
