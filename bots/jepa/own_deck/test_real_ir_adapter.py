"""Selected real-row and synthetic metadata tests; no full audit or execution."""
import ast
import copy
import json
from pathlib import Path
import unittest

import real_ir_adapter as A

FIXTURES=json.loads(Path(__file__).with_name('real_ir_adapter_fixtures.json').read_text())
ROWS={v['code']:v['row']for v in FIXTURES['fixtures']}


class AdapterTests(unittest.TestCase):
    def row(self,code='IBH_061'):return copy.deepcopy(ROWS[code])

    def test_selected_whole_rows_and_frozen_origin_pins(self):
        self.assertEqual(FIXTURES['source_pins']['catalogue']['sha256'],A.CATALOGUE_SHA)
        self.assertEqual(FIXTURES['source_pins']['runtime_admission']['sha256'],A.RUNTIME_SHA)
        self.assertEqual(FIXTURES['source_pins']['engine_revision'],A.ENGINE_REVISION)
        for fixture in FIXTURES['fixtures']:
            with self.subTest(code=fixture['code']):
                self.assertTrue(fixture['runtime_admitted']);self.assertEqual(A.row_digest(fixture['row']),fixture['row_sha256'])
                record=A.adapt_row(fixture['row']);self.assertEqual(record['full_card_supported'],fixture['expected_full_card_supported'])
                self.assertEqual(record['raw_row'],fixture['row']);self.assertEqual(record['whole_row_sha256'],fixture['row_sha256'])
                if fixture['expected_full_card_supported']:
                    self.assertEqual(record['unsupported_reasons'],[]);self.assertTrue(record['profile_serialized'])
                    program=record['canonical_program'];self.assertEqual(program['trigger'],None if fixture['expected_form']=='plain-profile'else fixture['expected_form'])
                else:self.assertTrue(record['unsupported_reasons'])

    def test_native_defaults_no_arena_or_cap_sentinel(self):
        row=self.row();resolver=row['abilities']['card'][0]['targetResolver'];resolver.clear()
        record=A.adapt_row(row);self.assertTrue(record['full_card_supported']);selector=record['canonical_program']['selector']
        self.assertEqual(selector['owner'],'any');self.assertEqual(selector['target_kind'],'any')
        self.assertEqual(selector['zone'],dict(present=False,value=None));self.assertEqual(selector['arena'],dict(present=False,values=None))
        self.assertEqual(selector['cost_cap'],dict(present=False,value=None));self.assertFalse(selector['optional'])
        self.assertIsNone(selector['mode']);self.assertIsNone(selector['count'])
        for code,zone,kind in(('IBH_059','base','any'),('IBH_061','anyAttackable','unit')):
            selector=A.adapt_row(self.row(code))['canonical_program']['selector']
            self.assertEqual(selector['zone']['value'],zone);self.assertEqual(selector['target_kind'],kind)
        selector=A.adapt_row(self.row('ASH_259'))['canonical_program']['selector']
        self.assertEqual(selector['zone']['value'],'arena');self.assertEqual(selector['arena'],dict(present=True,values=['ground']))

    def test_raw_cost_cap_owner_and_amount_fields(self):
        row=self.row();resolver=row['abilities']['card'][0]['targetResolver']
        resolver.update(owner='self',type='nonLeaderUnit',zone='arena',arena='space',predicate=dict(kind='binary',op='<=',left=dict(kind='ref',path=['card','cost']),right=dict(kind='const',value=0)))
        record=A.adapt_row(row);self.assertTrue(record['full_card_supported']);s=record['canonical_program']['selector']
        self.assertEqual(s['cost_cap'],dict(present=True,value=0));self.assertEqual(s['owner'],'self');self.assertEqual(s['target_kind'],'nonLeaderUnit')
        self.assertEqual(s['arena']['values'],['space'])
        for amount in(1,2,3,4,5):
            row['abilities']['card'][0]['effect']['amount']['value']=amount
            self.assertEqual(A.adapt_row(row)['canonical_program']['effect']['amount']['value'],amount)

    def test_printed_nulls_and_data_only_plain_profiles(self):
        event=A.adapt_row(self.row());p=event['printed_profile']
        self.assertEqual(p['hp'],dict(present=True,known=False,value=None));self.assertFalse(p['power']['known'])
        self.assertEqual(p['arena'],dict(present=False,known=False,value=None))
        plain=A.adapt_row(self.row('ASH_201'));self.assertTrue(plain['full_card_supported'])
        self.assertNotIn('baseClass',plain['raw_row']);self.assertIsNone(plain['provenance']['sourceHash'])
        self.assertTrue(plain['printed_profile']['hp']['known']);self.assertEqual(plain['canonical_program']['form'],'plain-profile')

    def test_when_played_is_explicit_and_other_triggers_reject(self):
        for code in('ASH_081','ASH_259','HMW_158'):
            result=A.adapt_row(self.row(code));self.assertTrue(result['full_card_supported'])
            self.assertEqual(result['canonical_program']['trigger'],'whenPlayed')
        row=self.row('ASH_081');row['abilities']['card'][0]['trigger']='onAttack'
        result=A.adapt_row(row);self.assertFalse(result['program_adapter_supported'])
        self.assertTrue(any(v['path']=='$.abilities.card[0].trigger'for v in result['unsupported_reasons']))

    def test_every_extra_execution_field_fails_whole_support(self):
        changes=[(lambda r:r.update(privatePrograms=[]),'$.privatePrograms'),
            (lambda r:r['abilities']['card'][0].update(unreviewedRule=True),'$.abilities.card[0].unreviewedRule'),
            (lambda r:r['card'].update(newRule=None),'$.card.newRule'),
            (lambda r:r['abilities']['card'][0].update(condition=dict(kind='const',value=True)),'$.abilities.card[0].condition'),
            (lambda r:r['abilities']['card'][0].update(costs=[dict(kind='exhaustSelf')]),'$.abilities.card[0].costs'),
            (lambda r:r['abilities']['card'][0]['effect'].update(sideEffect=dict(kind='draw')),'$.abilities.card[0].effect.sideEffect')]
        for mutate,path in changes:
            row=self.row();mutate(row);result=A.adapt_row(row)
            self.assertFalse(result['full_card_supported']);self.assertTrue(any(v['path']==path for v in result['unsupported_reasons']))
            self.assertEqual(result['raw_row'],row)

    def test_keywords_attachment_and_multiple_sides_are_never_plain_support(self):
        row=self.row('ASH_201');row['card']['keywords']=['sentinel'];row['keywordValues']={'sentinel':1}
        result=A.adapt_row(row);self.assertTrue(result['program_adapter_supported']);self.assertFalse(result['full_card_supported'])
        self.assertTrue(any(v['path']=='$.card.keywords'for v in result['unsupported_reasons']))
        attach=A.adapt_row(self.row('LOF_151'));self.assertFalse(attach['full_card_supported'])
        self.assertTrue(any(v['path']=='$.attachCondition'for v in attach['unsupported_reasons']))
        multiple=A.adapt_row(self.row('ASH_011'));self.assertFalse(multiple['program_adapter_supported'])
        self.assertEqual(multiple['ability_sides'],ROWS['ASH_011']['abilities']);self.assertIsNone(multiple['canonical_program'])

    def test_strict_null_boolean_cardinality_and_nonliteral_amount(self):
        for modify in(lambda a:a.update(optional=None),lambda a:a['targetResolver'].update(optional=0),
            lambda a:a['targetResolver'].update(mode='upTo',count=dict(kind='const',value=1)),
            lambda a:a['effect'].update(amount=dict(kind='binary',op='+',left=dict(kind='const',value=1),right=dict(kind='const',value=2)))):
            row=self.row();modify(row['abilities']['card'][0]);result=A.adapt_row(row)
            self.assertFalse(result['program_adapter_supported']);self.assertTrue(result['unsupported_reasons'])
        row=self.row();row['abilities']['card']=None
        self.assertFalse(A.adapt_row(row)['full_card_supported'])

    def test_identity_display_changes_do_not_create_program_families(self):
        row=self.row('IBH_059');original=copy.deepcopy(row);first=A.adapt_row(row)
        row.update(setCode='SYN_001',id='synthetic-id',sourcePath='display-only',sourceHash=None)
        row['card'].update(title='New title',cost=9);row['abilities']['card'][0]['title']='Different display title'
        second=A.adapt_row(row);self.assertEqual(first['family_key'],second['family_key'])
        self.assertEqual(first['family_key'],first['exact_program_key'])
        self.assertNotEqual(first['whole_row_sha256'],second['whole_row_sha256']);self.assertEqual(ROWS['IBH_059'],original)
        row['abilities']['card'][0]['effect']['amount']['value']=3
        self.assertNotEqual(first['family_key'],A.adapt_row(row)['family_key'])

    def test_unknown_required_capability_is_not_silently_ignored(self):
        row=self.row();row['requiredCapabilities'].append('ir:future-unrepresented-rule')
        result=A.adapt_row(row);self.assertTrue(result['program_adapter_supported']);self.assertFalse(result['full_card_supported'])
        self.assertEqual(result['raw_row'],row)
        self.assertTrue(any(v['path'].startswith('$.requiredCapabilities[')and'future-unrepresented-rule'in v['reason']for v in result['unsupported_reasons']))

    def test_native_empty_event_and_impossible_selector_shapes_reject(self):
        row=self.row();row['abilities']['card']=[];row['card']['text']=''
        self.assertFalse(A.adapt_row(row)['program_adapter_supported'])
        for constraints in(dict(type='base',zone='arena'),dict(type='base',arena='ground'),
            dict(type='unit',zone='base'),dict(type='any',zone='base',arena='space'),dict(promptTitle='Named prompt')):
            row=self.row();row['abilities']['card'][0]['targetResolver'].update(constraints)
            result=A.adapt_row(row);self.assertFalse(result['full_card_supported']);self.assertFalse(result['program_adapter_supported'])
        for base_class in('EventCard','BaseCard','LeaderUnitCard','UnreviewedSourceClass'):
            row=self.row('ASH_201');row['baseClass']=base_class;result=A.adapt_row(row)
            self.assertFalse(result['full_card_supported']);self.assertTrue(any(v['path']=='$.baseClass'for v in result['unsupported_reasons']))

    def test_import_and_contract_are_standard_library_only(self):
        tree=ast.parse(Path(A.__file__).read_text());names=[a.name for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(names)&{'numpy','torch','subprocess','compositional_typed_model'})
        self.assertTrue(A.contract()['not_v1_compatible']);self.assertFalse(A.contract()['semantic_validated'])


if __name__=='__main__':unittest.main()
