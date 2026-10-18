"""Synthetic IR tests only: no actual fixture generation, model or engine."""
import copy
import unittest

import ability_typed_reference as R


def const(value): return dict(kind='const', value=value)


def card(owner='p2', cost=2, damage=0, hp=6, zone='ground', base=False, traits=None):
    return dict(id='', code='synthetic', owner=owner, present=True, zone=zone,
        is_unit=not base, is_base=base, damage=damage, hp=hp, power=2,
        exhausted=False, shield_count=0, xp_count=0, printed_cost=cost,
        printed_traits=list(traits or []), printed_aspects=[], printed_types=['base' if base else 'unit'],
        known={k: True for k in ('identity', 'owner', 'damage', 'hp', 'power', 'exhausted',
            'shield_count', 'xp_count', 'printed_cost', 'printed_traits', 'printed_aspects', 'printed_types')})


def fixture(effect=None, resolver=None, optional=False):
    projections = dict(source=card(owner='p1', zone='hand'), a=card(), b=card(owner='p1', cost=3),
        own_base=card(owner='p1', damage=1, hp=30, zone='base', base=True),
        opponent_base=card(damage=0, hp=30, zone='base', base=True))
    for role, p in projections.items(): p['id'] = role
    before = dict(projections=projections, state=dict(players={seat:dict(ground=[dict(id=r) for r,p in projections.items()
        if p['owner']==seat and p['zone']=='ground'], space=[]) for seat in ('p1','p2')}))
    case = dict(before=before, refs={r:r for r in projections}, observation_refs=list(projections),
        declared_intent=dict(ref='a', id='a', requires_target=True))
    ability = dict(trigger='event', costs=[], effect=effect or dict(kind='defeat', target='chosen'),
        targetResolver=resolver or dict(owner='any', type='unit', zone='anyAttackable'))
    if optional: ability['optional'] = True
    raw = dict(card=dict(types=['event'], arena=None), abilities=dict(card=[ability], unit=[], leader=[]))
    return raw, case


class ReferenceTest(unittest.TestCase):
    def test_eligibility_ignores_intention_but_outcomes_use_it(self):
        raw, case = fixture()
        first = R.reference_case(raw, case)
        case['declared_intent'] = dict(ref='b', id='b', requires_target=True)
        second = R.reference_case(raw, case)
        for role in ('a', 'b'):
            self.assertEqual(first['observations'][role]['values'][0], 1)
            self.assertEqual(second['observations'][role]['values'][0], 1)
        self.assertEqual(first['observations']['a']['values'][1], 1)
        self.assertEqual(second['observations']['a']['values'][1], 0)
        self.assertEqual(second['observations']['b']['values'][1], 1)
        self.assertEqual(first['source']['mask'], [0]*9)

    def test_owner_and_literal_threshold_are_separate(self):
        predicate = dict(kind='binary', op='<=', left=dict(kind='ref', path=['card','cost']), right=const(2))
        raw, case = fixture(resolver=dict(owner='opponent', type='nonLeaderUnit', zone='anyAttackable', predicate=predicate))
        out = R.reference_case(raw, case)
        self.assertEqual([out['observations'][r]['values'][0] for r in ('a','b')], [1,0])
        raw['abilities']['card'][0]['targetResolver']['owner'] = 'any'
        predicate['right'] = const(3)
        self.assertEqual(R.reference_case(raw,case)['observations']['b']['values'][0],1)

    def test_heal_require_change_and_cap(self):
        raw, case = fixture(effect=dict(kind='heal', target='chosen', amount=const(3)), optional=True)
        case['before']['projections']['a']['damage'] = 1
        out = R.reference_case(raw,case)
        self.assertEqual(out['observations']['a']['values'][2], -1)
        self.assertEqual(out['observations']['b']['values'][0], 0)
        self.assertEqual(out['observations']['a']['mask'][2], 1)

    def test_shield_blocks_one_damage_event(self):
        raw, case = fixture(effect=dict(kind='damage', target='chosen', amount=const(3)))
        case['before']['projections']['a']['shield_count'] = 2
        out = R.reference_case(raw,case)['observations']['a']
        self.assertEqual(out['values'][2:5], [0,0,-1])

    def test_removed_numeric_fields_unknown(self):
        raw, case = fixture(effect=dict(kind='damage', target='chosen', amount=const(6)))
        out = R.reference_case(raw,case)['observations']['a']
        self.assertEqual(out['values'][1],1)
        self.assertEqual(out['mask'][2:],[0]*5)

    def test_if_you_do_own_base_heal_only_after_committed_defeat(self):
        raw, case = fixture(optional=True)
        raw['abilities']['card'][0]['ifYouDo'] = dict(costs=[],effect=dict(kind='heal',target='ownBase',amount=const(3)))
        out = R.reference_case(raw,case)
        self.assertEqual(out['observations']['own_base']['values'][2],-1)
        raw['abilities']['card'][0]['targetResolver']['owner']='self'
        out = R.reference_case(raw,case)
        self.assertEqual(out['observations']['own_base']['values'][2],0)
        self.assertEqual(out['observations']['a']['values'][1],0)

    def test_simultaneous_nested_selection(self):
        raw, case = fixture()
        ability = raw['abilities']['card'][0]; ability.pop('targetResolver'); ability['trigger']='whenPlayed'
        raw['card'] = dict(types=['unit'],arena='ground')
        case['before']['projections']['a']['zone']='space'
        case['before']['state']['players']['p2'] = dict(ground=[],space=[dict(id='a')])
        ability['effect'] = dict(kind='simultaneous',effects=[dict(kind='damage',target='self',amount=const(1)),
            dict(kind='select',targetResolver=dict(owner='opponent',type='unit',zone='arena',arena='space'),
                 effect=dict(kind='damage',target='chosen',amount=const(1)))])
        out=R.reference_case(raw,case)
        self.assertEqual(out['observations']['a']['values'][2],1)
        self.assertEqual(out['observations']['b']['values'][0],0)
        self.assertEqual(out['observations']['source']['mask'],[0]*7)

    def test_conditional_amount_uses_complete_own_public_arena(self):
        condition=dict(kind='query',name='hasSomeArenaUnit',receiver=dict(kind='ref',path=['player']),args=[
            dict(kind='query',name='hasSomeAspect',receiver=dict(kind='ref',path=['card']),args=[const('command')])])
        raw, case = fixture(effect=dict(kind='damage',target='chosen',amount={
            'kind':'conditional','condition':condition,'then':const(5),'else':const(3)}))
        case['before']['projections']['b']['printed_aspects']=['command']
        self.assertEqual(R.reference_case(raw,case)['observations']['a']['values'][2],5)
        case['before']['state']['players']['p1']['ground'].append(dict(id='unprojected'))
        self.assertEqual(R.reference_case(raw,case)['status'],'unknown')

    def test_mandatory_illegal_intent_does_not_invent_cancel(self):
        raw, case=fixture(resolver=dict(owner='self',type='unit',zone='anyAttackable'))
        out=R.reference_case(raw,case)
        self.assertEqual(out['status'],'partial')
        self.assertEqual(out['observations']['b']['mask'],[1,0,0,0,0,0,0])

    def test_unknown_constructor_rejected_even_on_optional_illegal_intent(self):
        raw, case=fixture(effect=dict(kind='draw',target='ownPlayer'),resolver=dict(owner='self',type='unit'),optional=True)
        out=R.reference_case(raw,case)
        self.assertEqual(out['status'],'unknown')
        self.assertTrue(all(not any(v['mask']) for v in out['observations'].values()))

    def test_unknown_metadata_not_false(self):
        raw, case=fixture(resolver=dict(owner='any',type='nonLeaderUnit'))
        case['before']['projections']['a']['known']['printed_types']=False
        self.assertEqual(R.reference_case(raw,case)['status'],'unknown')

    def test_no_identity_dispatch_or_future_reads(self):
        raw, case=fixture()
        before=copy.deepcopy(case)
        expected=R.reference_case(raw,case)
        raw['setCode']='another-name'; raw['abilities']['card'][0]['title']='Different display'
        case['final']=object();case['after']=object();case['targetPrompt']=object();case['offeredActions']=object()
        self.assertEqual(R.reference_case(raw,case),expected)
        self.assertEqual(case['before'],before['before'])


if __name__=='__main__': unittest.main()
