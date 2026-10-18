"""Primitive metadata tests only: no Torch/model/numerical construction."""
import copy
import itertools
import json
import unittest

import compositional_typed_model as M


def program(owner='any',arena='ground',cap=2,amount=1,op='damage'):
    return dict(trigger='event',costs=[],targetResolver=dict(owner=owner,type='unit',zone='arena',arena=arena,
        predicate=dict(kind='binary',op='<=',left=dict(kind='ref',path=['card','cost']),right=dict(kind='const',value=cap))),
        effect=dict(kind=op,target='chosen',amount=dict(kind='const',value=amount)))


def candidate():
    return dict(id='instance-a',code='not-a-feature',owner='p2',zone='space',present=True,is_unit=True,
        printed_cost=3,damage=1,hp=10,known={k:True for k in('identity','owner','printed_cost','damage','hp')})


class MetadataTest(unittest.TestCase):
    def test_complete_primitive_factorial_has_unique_fields_and_balanced_atoms(self):
        groups={0:[],1:[]}
        for owner,arena,cap,amount,op in itertools.product(('any','opponent'),('ground','space'),(2,3),(1,3),('damage','heal')):
            raw=program(owner,arena,cap,amount,op);bits=M.extract_program_bits(raw)
            fields=M.encode_program(raw);groups[sum(bits)%2].append((bits,fields))
            self.assertEqual(fields,[float(owner=='any'),float(owner=='opponent'),float(arena=='ground'),
                float(arena=='space'),float(cap),float(op=='damage'),float(op=='heal'),float(amount)])
        self.assertEqual([len(groups[k])for k in(0,1)],[16,16])
        self.assertEqual(len({tuple(fields)for group in groups.values()for _,fields in group}),32)
        for group in groups.values():
            for index in range(5):self.assertEqual({bits[index]for bits,_ in group},{0,1})

    def test_only_ir_content_not_code_title_or_object_key_order(self):
        raw=program();expected=M.encode_program(raw)
        raw['title']='arbitrary display';raw=dict(reversed(list(raw.items())))
        wrapped=dict(setCode='SYN_999',sourceHash='not-a-feature',card=dict(title='anything'),
            abilities=dict(card=[raw],leader=[],unit=[]))
        self.assertEqual(M.encode_program(wrapped),expected)
        wrapped['setCode']='different';wrapped['sourceHash']='changed'
        self.assertEqual(M.encode_program(wrapped),expected)

    def test_owner_arena_cost_amount_operator_remain_separate(self):
        base=M.encode_program(program())
        for changed,indices in [(program(owner='opponent'),{0,1}),(program(arena='space'),{2,3}),
                                (program(cap=3),{4}),(program(amount=3),{7}),(program(op='heal'),{5,6})]:
            fields=M.encode_program(changed)
            self.assertEqual({i for i,(a,b)in enumerate(zip(base,fields))if a!=b},indices)

    def test_unreviewed_programs_and_nonliteral_amounts_reject(self):
        for mutation in ('owner','op','extra','cost','formula','count'):
            raw=program()
            if mutation=='owner':raw['targetResolver']['owner']='self'
            elif mutation=='op':raw['effect']['kind']='defeat'
            elif mutation=='extra':raw['ifYouDo']={'effect':raw['effect']}
            elif mutation=='cost':raw['costs']=[{'kind':'exhaust'}]
            elif mutation=='formula':raw['effect']['amount']={'kind':'ref','path':['card','damage']}
            else:raw['targetResolver']['mode']='upTo';raw['targetResolver']['count']={'kind':'const','value':2}
            with self.assertRaises(ValueError):M.encode_program(raw)
        raw=program(cap=True)
        with self.assertRaises(ValueError):M.encode_program(raw)

    def test_public_candidate_role_binding_and_identity_renaming(self):
        raw=candidate();fields=M.encode_candidate(raw,'instance-a')
        self.assertEqual(fields,[0.,1.,0.,1.,3.,1.,10.,1.])
        other=M.encode_candidate(raw,'instance-b')
        self.assertEqual(other[:-1],fields[:-1]);self.assertEqual(other[-1],0.)
        raw['id']='renamed';raw['code']='another-code'
        self.assertEqual(M.encode_candidate(raw,'renamed'),fields)
        self.assertEqual(M.encode_candidate(raw,'renamed',acting_owner='p2')[:2],[1.,0.])

    def test_unknown_or_private_candidate_never_zero_filled(self):
        for field in('identity','owner','printed_cost','damage','hp'):
            raw=candidate();raw['known'][field]=False
            with self.assertRaises(ValueError):M.encode_candidate(raw,'instance-a')
        for field,value in [('zone','hand'),('present',False),('hp',11),('damage',float('nan')),('printed_cost',5)]:
            raw=candidate();raw[field]=value
            with self.assertRaises(ValueError):M.encode_candidate(raw,'instance-a')

    def test_fixed_parameter_contract_identity_gate_and_no_selector_truth_inputs(self):
        metadata=M.parameter_metadata(16)
        self.assertEqual(metadata['allocated'],1258);self.assertEqual(metadata['trainable'],1258)
        self.assertEqual(metadata['identity_parameters'],136)
        spec=M.contract();self.assertEqual(spec['fields']['columns'],list(M.FIELD_NAMES))
        self.assertEqual(spec['candidates']['columns'],list(M.CANDIDATE_NAMES))
        self.assertEqual(spec['candidates']['scales'],[1.,1.,1.,1.,4.,4.,10.,1.])
        self.assertFalse(any(k in M.FIELD_NAMES+M.CANDIDATE_NAMES for k in('allowed','target_allowed','outcome','card_id')))
        self.assertFalse(spec['semantic_validated']);json.dumps(spec,allow_nan=False)

    def test_source_fingerprint_is_stdlib_metadata(self):
        fingerprint=M.source_fingerprint()
        self.assertEqual(len(fingerprint['sha256']),64);self.assertEqual(len(fingerprint['contract_ast_sha256']),64)
        self.assertGreater(fingerprint['bytes'],1000)


if __name__=='__main__':unittest.main()
