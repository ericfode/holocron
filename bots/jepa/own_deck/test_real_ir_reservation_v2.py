"""Public synthetic metadata only; no real audit, arrays, model or native run."""
import ast
import copy
from pathlib import Path
import types
import unittest

import real_ir_reservation_v2 as R


def program(op='heal',kind='unit',zone='anyAttackable',amount=2,trigger='event',cap=None,arena=None):
    return dict(schema='toy-program',form='chosen-constant',side='card',trigger=trigger,costs=[],optional=False,requires_confirmation=False,coordinate=False,attacker_must_survive=False,
        selector=dict(owner='any',target_kind=kind,zone=dict(present=True,value=zone),arena=dict(present=arena is not None,values=arena),cost_cap=dict(present=cap is not None,value=cap),optional=False,mode=None,count=None),effect=dict(operator=op,destination='chosen',amount=dict(kind='const',value=amount)))


def row(code,identity,p,aliases=None):
    q=p['selector'];selector=dict(owner=q['owner'],type=q['target_kind'],zone=q['zone']['value'])
    if q['arena']['values']is not None:selector['arena']=q['arena']['values'][0]
    if q['cost_cap']['value']is not None:selector['predicate']=dict(kind='binary',op='<=',left=dict(kind='ref',path=['card','cost']),right=dict(kind='const',value=q['cost_cap']['value']))
    return dict(setCode=code,id=identity,card=dict(setCodes=aliases or[dict(set=code[:3],number=int(code[4:]))]),sourceHash='toy-source',sourcePath='toy.ts',
        abilities=dict(leader=[],unit=[],card=[dict(trigger=p['trigger'],title='Display only',costs=[],optional=p['optional'],targetResolver=selector,effect=dict(kind=p['effect']['operator'],target='chosen',amount=copy.deepcopy(p['effect']['amount'])))]),toy_canonical=copy.deepcopy(p))


class ReservationTests(unittest.TestCase):
    def fixture(self):
        definitions=[('IBH_013','1',program(amount=5)),('IBH_066','2',program(amount=2)),('IBH_061','3',program(op='damage',amount=3)),('TWI_174','4',program(op='damage',amount=4)),('IBH_059','5',program(op='damage',kind='any',zone='base')),('JTL_075','6',program(kind='any',amount=3)),('TWI_170','7',program(op='damage',kind='any'))]
        rows=[row(*d)for d in definitions];rows[4]['card']['setCodes'].append(dict(set='IBH',number=71))
        def adapt(r):
            p=r.get('toy_canonical');return dict(canonical_program=p,program_adapter_supported=p is not None,full_card_supported=p is not None,family_key=R.exact_program_key(p)if p else None)
        adapter=types.SimpleNamespace(adapt_row=adapt)
        coverage=dict(decks=[dict(source_index=0,family_id='toy-family',split='train',total_main_copies=3,main_cards=[dict(canonical_id='IBH_013',source_id='1',copies=1),dict(canonical_id='OLD_001',source_id='not-covered',copies=2)])])
        return rows,{r['setCode']for r in rows},coverage,adapter

    def test_numeric_abstraction_and_exact_key_are_separate(self):
        a=program(amount=2);b=program(amount=5)
        self.assertEqual(R.mechanism_family_key(a),R.mechanism_family_key(b));self.assertNotEqual(R.exact_program_key(a),R.exact_program_key(b))
        self.assertEqual(R.mechanism_family_key(program(cap=2)),R.mechanism_family_key(program(cap=4)))
        self.assertNotEqual(R.mechanism_family_key(program(cap=2)),R.mechanism_family_key(program(cap=None)))

    def test_mechanism_preserves_operators_selectors_trigger_control(self):
        a=program();original=R.mechanism_family_key(a)
        for b in(program(op='damage'),program(kind='any'),program(zone='base'),program(trigger='whenPlayed'),program(arena=['space'])):
            self.assertNotEqual(original,R.mechanism_family_key(b))
        b=copy.deepcopy(a);b['optional']=True;self.assertNotEqual(original,R.mechanism_family_key(b))
        b=copy.deepcopy(a);b['selector']['owner']='opponent';self.assertNotEqual(original,R.mechanism_family_key(b))
        b=copy.deepcopy(a);b['effect']['destination']='self';self.assertNotEqual(original,R.mechanism_family_key(b))

    def test_raw_keys_keep_unknown_fields_order_and_binding(self):
        a=dict(trigger='event',title='A',effect=dict(kind='sequence',effects=[dict(kind='damage',amount=dict(kind='const',value=1)),dict(kind='heal',amount=dict(kind='const',value=3))]))
        b=copy.deepcopy(a);b['title']='B';b['effect']['effects'][0]['amount']['value']=9
        self.assertEqual(R.numeric_raw_program_key(a),R.numeric_raw_program_key(b))
        b['effect']['effects'].reverse();self.assertNotEqual(R.numeric_raw_program_key(a),R.numeric_raw_program_key(b))
        b=copy.deepcopy(a);b['unknownMechanic']={'source':['parentCard']};self.assertNotEqual(R.numeric_raw_program_key(a),R.numeric_raw_program_key(b))

    def test_alias_identity_and_ambiguous_alias_fail_closed(self):
        rows,_,_,_=self.fixture();index,ids=R.alias_index(rows)
        self.assertEqual(index['IBH_071'],'IBH_059');self.assertEqual(ids['5']['aliases'],['IBH_059','IBH_071'])
        extra=row('OLD_001','8',program(),[dict(set='IBH',number=71)])
        with self.assertRaises(ValueError):R.alias_index(rows+[extra])

    def test_token_without_printing_aliases_retains_primary_identity(self):
        rows,_,_,_=self.fixture();token=dict(setCode='TOKEN_SHIELD',id='token-id',card=dict(setId=dict(set='SOR')))
        index,ids=R.alias_index(rows+[token]);self.assertEqual(index['TOKEN_SHIELD'],'TOKEN_SHIELD')
        self.assertEqual(ids['token-id']['aliases'],['TOKEN_SHIELD']);self.assertNotIn('SOR_000',index)
        for value in(None,{},'SOR_001',[dict(set='SOR',number=True)],[dict(set='SOR',number=-1)],[dict(set='SOR',number=1000)],[dict(set='bad-set',number=1)]):
            bad=copy.deepcopy(token);bad['card']['setCodes']=value
            with self.assertRaises(ValueError):R.alias_index(rows+[bad])
        for value in(None,'',False):
            bad=copy.deepcopy(token);bad['id']=value
            with self.assertRaises(ValueError):R.alias_index(rows+[bad])
        bad=copy.deepcopy(token);del bad['id']
        with self.assertRaises(ValueError):R.alias_index(rows+[bad])
        bad=copy.deepcopy(token);bad['id']=rows[0]['id']
        with self.assertRaises(ValueError):R.alias_index(rows+[bad])

    def test_alphanumeric_printing_set_preserves_ts26_alias(self):
        rows,_,_,_=self.fixture();extra=row('TS26_034','ts26-id',program(),[dict(set='TS26',number=34),dict(set='SOR',number=34)])
        index,ids=R.alias_index(rows+[extra]);self.assertEqual(index['TS26_034'],'TS26_034');self.assertEqual(index['SOR_034'],'TS26_034')
        self.assertEqual(ids['ts26-id']['aliases'],['SOR_034','TS26_034'])
        for value in('', 'ts26', 'TS-26', 'TS_26', 'TS26/', 'ＴＳ26', 'TS26\n'):
            bad=copy.deepcopy(extra);bad['card']['setCodes'][0]['set']=value
            with self.assertRaises(ValueError):R.alias_index(rows+[bad])

    def test_partition_whole_groups_and_no_copy_drops(self):
        rows,admitted,cov,adapter=self.fixture();out=R.assemble(rows,admitted,[],cov,adapter)
        self.assertEqual(len(out['mechanism_groups']['train']),3);self.assertEqual(len(out['mechanism_groups']['held']),2)
        self.assertEqual(out['deck_coverage'][0]['proposed_known_copies'],1);self.assertEqual(out['deck_coverage'][0]['proposed_unknown_copies'],2)
        self.assertEqual(sum(c['copies']for c in out['deck_coverage'][0]['main_cards']),3)
        self.assertFalse(out['semantic_validated']);self.assertEqual(out['native_calls'],0)

    def test_prior_alias_source_or_helper_disqualifies_candidate(self):
        rows,admitted,cov,adapter=self.fixture()
        for plan in(dict(codes=['IBH_071']),dict(helpers={'resource':'IBH_071'})):
            with self.assertRaises(ValueError):R.assemble(rows,admitted,[('toy-prior',plan)],cov,adapter)

    def test_held_full_family_overlap_even_other_literal_is_rejected(self):
        rows,admitted,cov,adapter=self.fixture();prior=row('OLD_001','8',program(kind='any',amount=1))
        with self.assertRaises(ValueError):R.assemble(rows+[prior],admitted,[('toy-prior',dict(codes=['OLD_001']))],cov,adapter)
        prior['toy_canonical']=None
        with self.assertRaises(ValueError):R.assemble(rows+[prior],admitted,[('toy-prior',dict(codes=['OLD_001']))],cov,adapter)

    def test_selector_exposure_disclosed_without_false_complete_overlap(self):
        rows,admitted,cov,adapter=self.fixture();p=program(kind='any',amount=3,trigger='whenPlayed');p['optional']=True;prior=row('OLD_001','8',p)
        out=R.assemble(rows+[prior],admitted,[('toy-prior',dict(codes=['OLD_001']))],cov,adapter);held=next(r for r in out['candidates']if r['code']=='JTL_075')
        self.assertTrue(held['prior_selector_operator_overlaps']);self.assertFalse(held['prior_adapter_full_program_overlaps'])

    def test_all32_restricted_synthetic_programs_are_scanned(self):
        rows,admitted,cov,adapter=self.fixture();synthetic={}
        for i in range(32):
            p=program(op='damage'if i%2 else'heal',amount=1 if i%4 else 3,zone='arena',arena=['space'if i%2 else'ground'],cap=2 if i%4 else 3)
            r=row('SYN_001','toy-'+str(i),p);r['setCode']='SYN_TYPED_'+str(i);synthetic[r['setCode']]=r
        out=R.assemble(rows,admitted,[('synthetic-plan',dict(selected_whole_rows=synthetic,selected_whole_cards=['TOKEN_SHIELD']))],cov,adapter)
        self.assertEqual(len(out['prior_synthetic_codes']),32);self.assertEqual(len(out['prior_program_records']),32);self.assertEqual(out['token_helpers'][0]['code'],'TOKEN_SHIELD')

    def test_source_only_fixed_snapshot_and_no_execution_surface(self):
        tree=ast.parse(Path(R.__file__).read_text());names=[a.name for n in ast.walk(tree)if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(names)&{'numpy','torch','subprocess'});self.assertEqual(len(R.source_paths()),33)
        text=Path(R.__file__).read_text();self.assertNotIn('write_text(',text);self.assertNotIn('write_bytes(',text);self.assertNotIn('np.load',text)
        self.assertEqual(R.CATALOGUE_SHA,'0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812')


if __name__=='__main__':unittest.main()
