"""Synthetic-only provenance repair and frozen scientific-source parity."""
import ast
import copy
import hashlib
from pathlib import Path
import unittest

import numpy as np
import binding_transfer_data as OLD
import binding_transfer_data_v2 as NEW
from test_binding_transfer_data import fixture


class Tests(unittest.TestCase):
    def test_missing_aliases_stay_unknown_and_raw_set_id_is_not_promoted(self):
        rows={'TOKEN_SHIELD':dict(card=dict(id='token-id',setId=dict(set='SOR')))};before=copy.deepcopy(rows)
        result=NEW.alias_registry(rows)['TOKEN_SHIELD']
        self.assertIsNone(result['set_codes']);self.assertIs(result['set_codes_present'],False);self.assertIs(result['set_codes_known'],False)
        self.assertEqual(result['raw_set_id'],dict(set='SOR'));self.assertTrue(result['raw_set_id_present'])
        self.assertEqual(rows,before);self.assertNotIn('setCodes',rows['TOKEN_SHIELD']['card'])
        result['raw_set_id']['set']='changed-output-only';self.assertEqual(rows,before)

    def test_known_aliases_preserved_exactly_and_copied(self):
        aliases=[dict(set='A',number=17),dict(set='B',number=23)]
        rows={'A_017':dict(card=dict(id=17,setCodes=aliases,setId=dict(set='A',number=17)))}
        result=NEW.alias_registry(rows)['A_017']
        self.assertEqual(result['canonical_id'],'17');self.assertEqual(result['set_codes'],aliases)
        self.assertTrue(result['set_codes_present']and result['set_codes_known'])
        result['set_codes'][0]['number']=99;self.assertEqual(aliases[0]['number'],17)

    def test_present_null_or_empty_aliases_are_not_invented(self):
        rows={'null':dict(card=dict(id=1,setCodes=None)),'empty':dict(card=dict(id=2,setCodes=[]))}
        result=NEW.alias_registry(rows)
        self.assertIsNone(result['null']['set_codes']);self.assertTrue(result['null']['set_codes_present']);self.assertFalse(result['null']['set_codes_known'])
        self.assertEqual(result['empty']['set_codes'],[]);self.assertTrue(result['empty']['set_codes_known'])
        self.assertIsNone(result['empty']['raw_set_id']);self.assertFalse(result['empty']['raw_set_id_present'])

    def test_frozen_original_bytes_and_only_provenance_assignment_differs(self):
        original=Path(OLD.__file__).read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),'7e0af843d21500f78307c95c6ad7f56f1d731d69c5a901725e81e0421ab5afb6')
        old,new=ast.parse(original),ast.parse(Path(NEW.__file__).read_text())
        helper=[n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='alias_registry'];self.assertEqual(len(helper),1)
        new.body.remove(helper[0]);oldconvert=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='convert_receipt');newconvert=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='convert_receipt')
        locate=lambda f:next(i for i,n in enumerate(f.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='aliases'for t in n.targets))
        oi,ni=locate(oldconvert),locate(newconvert);self.assertEqual(oi,ni)
        expected=ast.parse('aliases=alias_registry(rows)').body[0]
        self.assertEqual(ast.dump(newconvert.body[ni]),ast.dump(expected))
        newconvert.body[ni]=copy.deepcopy(oldconvert.body[oi])
        self.assertEqual(ast.dump(old),ast.dump(new),'scientific source or any other statement changed')

    def test_synthetic_features_labels_masks_and_unknowns_bit_exact(self):
        for mode in('attachment','aura','unknown-counter','pending'):
            with self.subTest(mode=mode):
                case,world,plan,rows=fixture(mode=='aura')
                if mode=='unknown-counter':case['final']['projections']['anchor_a']['known']['hp']=False
                if mode=='pending':
                    case['steps']=case['steps'][:1];case.update(final=None,lastObserved=case['targetPrompt'],targetAction=None,intendedTargetCommitted=False,completion='unreviewed-continuation',applyCalls=1)
                old=OLD.derive_labels(case,world,plan,rows);new=NEW.derive_labels(case,world,plan,rows)
                for key in old:
                    if isinstance(old[key],np.ndarray):
                        self.assertEqual(old[key].dtype,new[key].dtype);self.assertEqual(old[key].shape,new[key].shape);self.assertEqual(old[key].tobytes(),new[key].tobytes())
                    else:self.assertEqual(old[key],new[key])
                before=OLD.public_before_record(case);self.assertEqual(before,NEW.public_before_record(case))
                x,c=OLD.M.project_record(before,list(OLD.ROLES),rows);xx,cc=NEW.M.project_record(NEW.public_before_record(case),list(NEW.ROLES),rows)
                np.testing.assert_array_equal(np.asarray(x,np.float32),np.asarray(xx,np.float32));np.testing.assert_array_equal(np.asarray(c,np.float32),np.asarray(cc,np.float32))


if __name__=='__main__':unittest.main()
