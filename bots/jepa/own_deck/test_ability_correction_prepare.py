"""Pure source/journal and optional synthetic-feature checks only."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import ability_correction_prepare as P


class SourceTests(unittest.TestCase):
    def test_no_model_fitting_or_predecessor_cohort_converter(self):
        tree=ast.parse(Path(P.__file__).read_text());top=[a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names];self.assertFalse(set(top)&{'numpy','torch'})
        calls=[ast.unparse(n.func)for n in ast.walk(tree)if isinstance(n,ast.Call)]
        for forbidden in('D.convert_receipt','D.B.input_conflicts','E.common_scalers','M.make_model','D.E.make_model'):self.assertNotIn(forbidden,calls)
        self.assertIn('D.derive_labels',calls);self.assertIn('D.V.legacy_context',calls);self.assertIn('D.V.legacy_candidate',calls);self.assertIn('D.public_before_record',calls)
        self.assertEqual((0,0,0,0,3.),tuple(P.CONFIG[k]for k in('neural_forwards','optimizer_updates','native_applies','numerical_fits','seconds')))

    def test_frozen_label_source_unchanged(self):
        path=Path(P.__file__).with_name('semantic_discrimination_data.py');self.assertEqual(P.FROZEN_DATA_SHA,P.C.pin(path)['sha256'])

    def test_reservation_and_remaining_guard_precede_arrays(self):
        tree=ast.parse(Path(P.__file__).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='execute');text=ast.unparse(fn)
        self.assertLess(text.index('run.begin('),text.index('len(inputs)'))
        self.assertLess(text.index('run.begin('),text.index("import_module('effect_identifiability_fit')"))
        self.assertIn('run.remaining_seconds()',text);self.assertIn('with guard:',text);self.assertIn("args.stage in finished['completed']",text)

    def test_new_schema_and_chronological_native_journal(self):
        raw=dict(applyCalls=2,collectionPlanSha256='a'*64,sourceRevision='fixed',selectedWholeCards=['IBH_104'],cases=[dict(world_id=i)for i in range(8)])
        header=dict(schema='jepa-ability-correction-apply-journal/1',maxApplyCalls=32,planSha256=raw['collectionPlanSha256'],sourceRevision='fixed',selectedWholeCards=['IBH_104'])
        rows=[header]+[dict(phase=p,applyCall=i)for i in(1,2)for p in('beforeApply','afterApply')]+[dict(phase='contextComplete',case=c)for c in raw['cases']]
        with tempfile.TemporaryDirectory()as temp:
            path=Path(temp)/'journal.jsonl';path.write_text(''.join(json.dumps(r)+'\n'for r in rows));self.assertEqual(2,P.journal_proof(path,raw)['native_apply_calls'])
            changed=[rows[0],rows[1],rows[3],rows[2],rows[4],*rows[5:]];path.write_text(''.join(json.dumps(r)+'\n'for r in changed))
            with self.assertRaisesRegex(ValueError,'chronological'):P.journal_proof(path,raw)
            rows[0]['schema']='jepa-semantic-discrimination-apply-journal/1';path.write_text(''.join(json.dumps(r)+'\n'for r in rows))
            with self.assertRaisesRegex(ValueError,'header'):P.journal_proof(path,raw)


@unittest.skipUnless(importlib.util.find_spec('numpy'),'optional synthetic NumPy feature checks')
class NoveltyTests(unittest.TestCase):
    def test_full_panel_novelty_does_not_hide_actual_candidate_replay(self):
        import numpy as np
        x=np.zeros((8,32),np.float32);c=np.zeros((8,8,43),np.float32);oldx=np.zeros((4,32),np.float32);oldc=np.zeros((4,8,43),np.float32);selected=np.asarray([3,4]*4,np.int64);oldselected=np.asarray([3,4]*2,np.int64)
        # Only an unrelated sibling/source candidate changes in root0. The
        # head for anchorA still consumes exactly the preceding public input.
        c[0,0,0]=1.;x[1:,0]=np.arange(1,8);before=c.copy()
        report=P.novelty(x,c,oldx,oldc,['IBH_104']*4,'fixed-semantic-bank',selected,oldselected)
        self.assertEqual(8,report['original']['full_panel_new_roots']);self.assertTrue(report['original']['rows'][0]['candidate_consumed_input_seen'][3]);self.assertTrue(report['original']['rows'][0]['source_consumed_input_seen']);np.testing.assert_array_equal(before,c)
        self.assertEqual(4,report['fresh_state_worlds']);self.assertIn('R_neutral',report)


if __name__=='__main__':unittest.main()
