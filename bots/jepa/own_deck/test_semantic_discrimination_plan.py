"""Synthetic public catalogue only; never prepares the actual scientific bank."""
import copy
import unittest
from unittest import mock
import semantic_discrimination_plan as P
from test_binding_transfer_data import row


def inputs():
    rows={}
    for i,code in enumerate(P.CODES):
        r=row(code,('event',),hp=None,power=None)
        r['abilities']['card']=[dict(trigger='whenPlayed',effect=dict(kind='damage',amount=i+1))]
        rows[code]=r
    for code in set(P.HELPERS.values())|{'TOKEN_SHIELD'}:
        rows[code]=row(code)
    for key,cost,hp,arena,traits in(('cheap_ground',2,4,'ground',()),('expensive_ground',3,6,'ground',()),('cheap_space',2,4,'space',('vehicle','fighter')),('expensive_space',3,4,'space',('vehicle','fighter'))):
        rows[P.HELPERS[key]]['card'].update(cost=cost,hp=hp,arena=arena,traits=list(traits))
    rows['TOKEN_SHIELD']['card'].pop('setCodes')
    admitted=dict(runtimeAdmittedCards=[dict(setCode=c,implementation='sourceIr')for c in rows if c!='TOKEN_SHIELD'])
    inventory=[dict(canonical_id=c,main_copies=n,declaration_count=1,whole_catalog_row=copy.deepcopy(rows[c]))for c,n in zip(P.CODES,(3,1,9,6,21,8,1,1))]
    return dict(cards=list(rows.values())),admitted,dict(runtime_admitted_card_inventory=inventory)


class Tests(unittest.TestCase):
    def test_exact_grid_and_native_budget(self):
        plan=P.build_plan(*inputs());ws=plan['worlds']
        self.assertEqual([w['id']for w in ws],list(range(33)))
        self.assertEqual({k:len(v)for k,v in plan['split']['root_partitions'].items()},dict(train=13,state_held=12,family_held=4,joint=4))
        self.assertEqual(plan['actual_source_copies'],50)
        self.assertEqual((plan['native_build_max_seconds'],plan['collector_max_seconds'],plan['collector_max_engine_applies']),(10,45,128))
        self.assertEqual(plan['structural_apply_estimate']['total_stage_bound'],107)
        for w in ws:
            self.assertEqual(w['ready_resources'],12)
            self.assertEqual(len(w['arena_cards']),5)
            self.assertEqual(w['arena_cards']['auxiliary']['owner'],'p2')
            self.assertEqual(w['arena_cards']['auxiliary']['code'],'TWI_253')
            self.assertEqual(w['arena_cards']['anchor_a']['damage'],1 if w['scenario']==0 else 4)
            self.assertEqual(w['arena_cards']['anchor_b']['damage'],1)
        self.assertEqual((ws[32]['source_code'],ws[32]['own_base_damage'],ws[32]['partition']),('LAW_133',1,'train'))
        self.assertTrue(ws[32]['auxiliary_cap_root']and ws[32]['primary_pair_excluded'])

    def test_predeclared_pairs_primary_roles_and_rank(self):
        plan=P.build_plan(*inputs())
        self.assertEqual([(p['left_root'],p['right_root'],p['expected_D'])for p in plan['primary_pairs']],[(28,8,-2),(29,9,-2),(30,10,2),(31,11,2)])
        self.assertEqual(plan['primary_spec']['anchors'],['anchor_a','anchor_b'])
        rank=plan['primary_spec']['rank_pairs'][0]
        self.assertEqual((rank['left_root'],rank['right_root'],rank['utility_sign']),(26,27,-1.))
        self.assertNotIn(32,[p[k]for p in plan['primary_pairs']for k in('left_root','right_root')])

    def test_full_rows_aliases_and_numeric_provenance_unchanged(self):
        catalog,admission,coverage=inputs();saved=copy.deepcopy(catalog)
        plan=P.build_plan(catalog,admission,coverage)
        self.assertEqual(catalog,saved)
        for c in plan['cards']:
            self.assertEqual(c['raw_card'],next(r for r in saved['cards']if r['setCode']==c['code']))
            self.assertEqual(c['aliases'],c['raw_card']['card']['setCodes'])
        self.assertNotIn('setCodes',plan['selected_whole_rows']['TOKEN_SHIELD']['card'])
        self.assertFalse(plan['semantic_validated'])

    def test_canonical_and_program_crossings_reject(self):
        catalog,a,c=inputs();catalog['cards'][6]['card']['id']=catalog['cards'][0]['card']['id'];c['runtime_admitted_card_inventory'][6]['whole_catalog_row']=copy.deepcopy(catalog['cards'][6])
        with self.assertRaisesRegex(ValueError,'canonical source'):P.build_plan(catalog,a,c)
        catalog,a,c=inputs();catalog['cards'][6]['abilities']=copy.deepcopy(catalog['cards'][0]['abilities']);c['runtime_admitted_card_inventory'][6]['whole_catalog_row']=copy.deepcopy(catalog['cards'][6])
        with self.assertRaisesRegex(ValueError,'equivalent'):P.build_plan(catalog,a,c)

    def test_native_admission_and_exact_corpus_row_required(self):
        catalog,a,c=inputs();a['runtimeAdmittedCards'][0]['implementation']='dataOnly'
        with self.assertRaisesRegex(ValueError,'complete actual-corpus'):P.build_plan(catalog,a,c)
        catalog,a,c=inputs();c['runtime_admitted_card_inventory'][0]['whole_catalog_row']['keywordValues']={'hiddenChange':1}
        with self.assertRaisesRegex(ValueError,'complete actual-corpus'):P.build_plan(catalog,a,c)

    def test_frontend_caps_fail_without_truncation(self):
        catalog,_,_=inputs();rows={r['setCode']:r for r in catalog['cards']}
        rows[P.CODES[0]]['abilities']['card'][0]['effect']['huge']=[1]*600
        with self.assertRaisesRegex(ValueError,'cap'):P.frontend_audit(rows)


if __name__=='__main__':unittest.main()
