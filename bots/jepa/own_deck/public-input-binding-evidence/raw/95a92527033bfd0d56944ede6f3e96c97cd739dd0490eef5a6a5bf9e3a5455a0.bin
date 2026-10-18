"""Synthetic public fixtures only; no native/model/optimizer execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import public_input_binding as B

class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=B.HERE/'public_input_binding_collector/fixtures/whole-rows.json';cls.rows={r['setCode']:r for r in json.loads(path.read_text())['cards']}
        cls.rows['BASE']={'card':dict(aspects=['vigilance'],traits=[],types=['base'],keywords=[],cost=0,unique=False,arena=None)}
        cls.rows['LEADER']={'card':dict(aspects=['aggression','heroism'],traits=[],types=['leader'],keywords=[],cost=0,unique=True,arena=None)}
    def projection(self,code,identity,owner,zone,damage=0,hp=None,power=None):
        c=self.rows[code]['card'];unit='unit'in c['types'];base='base'in c['types'];physical=unit and zone in('ground','space');p=dict(code=code,id=identity,owner=owner,zone=zone,present=True,is_unit=unit,is_base=base,in_arena=physical,attackable=physical,damage=damage,hp=hp if hp is not None else c.get('hp')or 0,power=power if power is not None else c.get('power')or 0,exhausted=False,shield_count=0,xp_count=0,known=dict(identity=True,owner=True,damage=physical or base,hp=physical or base,power=physical,exhausted=physical,shield_count=physical,xp_count=physical))
        return p
    def fixture(self,source='LAW_045',own='ASH_056',opponent='ASH_056',intent='host_a',damage=0):
        projections={r:None for r in B.ROLES};projections['source']=self.projection(source,'source','p1','hand');projections['own_base']=self.projection('BASE','base1','p1','base',hp=30);projections['opponent_base']=self.projection('BASE','base2','p2','base',hp=30)
        if source=='LAW_045':
            projections['own_helper']=self.projection(own,'own','p1','ground');projections['opponent_helper']=self.projection(opponent,'enemy','p2','ground');projections['victim']=self.projection('SEC_028','victim','p2','ground',damage=damage,hp=7,power=5);intent='victim';observations=['victim']
        else:
            projections['host_a']=self.projection('SEC_028','a','p1','ground',damage=damage);projections['host_b']=self.projection('SEC_028','b','p1','ground',damage=damage);observations=['host_a','host_b']
        refs={r:p['id']if p else None for r,p in projections.items()};players={seat:dict(ground=[],space=[],base={'setCode':'BASE'},leader={'setCode':'LEADER'},resources=[{'exhausted':False}for _ in range(12)],hand=[],deck=[])for seat in('p1','p2')}
        for p in projections.values():
            if p and p['is_unit']and p['zone']in('ground','space'):players[p['owner']][p['zone']].append(dict(id=p['id'],setCode=p['code']))
        return dict(card=source,world_id=0,refs=refs,declared_intent=dict(ref=intent,id=refs[intent]),observation_refs=observations,before=dict(projections=projections,state=dict(players=players)))
    def predict(self,case,control='bound',row=None):return B.predict_case(row or self.rows[case['card']],case,self.rows,control)
    def test_realistic_bases_and_hand_upgrade_unknown_stats_do_not_block(self):
        for card in('LAW_045','LOF_215'):
            result=self.predict(self.fixture(card));self.assertEqual(result['status'],'known',result['unknown_reasons'])
    def test_legacy_owner_collision_and_new_separation(self):
        a=self.fixture();b=self.fixture(own='SEC_094');pa=B.project_case(self.rows['LAW_045'],a,self.rows);pb=B.project_case(self.rows['LAW_045'],b,self.rows)
        self.assertEqual(pa['legacy_context18'],pb['legacy_context18']);self.assertEqual(pa['anchors']['victim']['legacy_branch_hash'],pb['anchors']['victim']['legacy_branch_hash']);self.assertEqual(pa['anchors']['victim']['legacy_source_hash'],pb['anchors']['victim']['legacy_source_hash']);self.assertNotEqual(pa['anchors']['victim']['repaired_hash'],pb['anchors']['victim']['repaired_hash'])
        self.assertEqual(self.predict(a)['observations']['victim']['values'][2],3);self.assertEqual(self.predict(b)['observations']['victim']['values'][2],5)
    def test_wrong_owner_and_unbound_share_information_but_differ_binding(self):
        case=self.fixture(own='ASH_056',opponent='SEC_094');bound=self.predict(case);wrong=self.predict(case,'wrong-owner');unbound=self.predict(case,'same-info-unbound')
        self.assertEqual(bound['projector'],wrong['projector']);self.assertEqual(bound['projector'],unbound['projector']);self.assertEqual(bound['observations']['victim']['values'][2],3);self.assertEqual(wrong['observations']['victim']['values'][2],5);self.assertEqual(unbound['observations']['victim']['values'][2],5)
    def test_host_binding_separates_actual_endpoint_from_old_conditional_branch(self):
        a=self.fixture('LOF_215',intent='host_a');b=self.fixture('LOF_215',intent='host_b');pa=B.project_case(self.rows['LOF_215'],a,self.rows);pb=B.project_case(self.rows['LOF_215'],b,self.rows)
        self.assertEqual(pa['anchors']['host_a']['legacy_branch_hash'],pb['anchors']['host_a']['legacy_branch_hash']);self.assertEqual(pa['anchors']['host_a']['legacy_source_hash'],pb['anchors']['host_a']['legacy_source_hash']);self.assertNotEqual(pa['anchors']['host_a']['repaired_hash'],pb['anchors']['host_a']['repaired_hash'])
        ar=self.predict(a)['observations'];br=self.predict(b)['observations'];self.assertEqual(ar['host_a']['values'][5:],[1,3]);self.assertEqual(ar['host_b']['values'][5:],[0,0]);self.assertEqual(br['host_a']['values'][5:],[0,0]);self.assertEqual(br['host_b']['values'][5:],[1,3]);self.assertEqual(ar['host_a']['keywords_added'],{'saboteur':1})
        unbound=self.predict(a,'same-info-unbound')['observations'];self.assertEqual(unbound['host_a']['values'][5:],unbound['host_b']['values'][5:])
    def test_legacy_omission_is_unknown_not_false_or_physical_zero(self):
        r=self.predict(self.fixture(),'legacy-omission');self.assertEqual(r['status'],'unknown');self.assertFalse(any(r['observations']['victim']['mask']))
    def test_owner_null_and_incomplete_public_arena_are_unknown(self):
        c=self.fixture();c['before']['projections']['own_helper']['owner']=None;self.assertEqual(self.predict(c)['status'],'unknown')
        c=self.fixture();c['before']['state']['players']['p1']['ground'].append({'id':'omitted','setCode':'SEC_028'});self.assertEqual(self.predict(c)['status'],'unknown')
    def test_alpha_and_layout_invariance(self):
        a=self.fixture('LOF_215');b=copy.deepcopy(a);mapping={p['id']:'renamed-'+p['id']for p in b['before']['projections'].values()if p}
        for p in b['before']['projections'].values():
            if p:p['id']=mapping[p['id']]
        b['refs']={k:mapping[v]if v else None for k,v in b['refs'].items()};b['declared_intent']['id']=mapping[b['declared_intent']['id']]
        for player in b['before']['state']['players'].values():
            for zone in('ground','space'):
                for u in player[zone]:u['id']=mapping[u['id']]
                player[zone].reverse()
        for ref in('host_a','host_b'):
            self.assertEqual(self.predict(a)['observations'][ref],self.predict(b)['observations'][ref]);self.assertEqual(self.predict(a)['projector']['anchors'][ref]['repaired_hash'],self.predict(b)['projector']['anchors'][ref]['repaired_hash'])
    def test_future_parents_offers_private_piles_are_never_inputs(self):
        a=self.fixture('LOF_215');b=copy.deepcopy(a);b['final']={'parent':'wrong','damage':999};b['targetAction']={'card':'wrong'};b['targetPrompt']={'offeredActions':['wrong']};b['before']['offeredActions']=['fiction'];b['before']['state']['players']['p2']['hand']=['PRIVATE'];b['before']['state']['players']['p1']['deck']=['ORDER']
        self.assertEqual(self.predict(a),self.predict(b))
    def test_source_card_ids_and_display_do_not_dispatch(self):
        c=self.fixture();row=copy.deepcopy(self.rows['LAW_045']);row['setCode']='OTHER';row['card']['id']='OTHER';row['card']['title']='OTHER';self.assertEqual(self.predict(c),self.predict(c,row=row))
        row['abilities']['card'][0]['effect']['amount']={'kind':'const','value':2};self.assertEqual(self.predict(c,row=row)['observations']['victim']['values'][2],2)
    def test_unsupported_and_lethal_are_stop_unknown(self):
        c=self.fixture();row=copy.deepcopy(self.rows['LAW_045']);row['abilities']['card'][0]['effect']['kind']='draw';self.assertEqual(self.predict(c,row=row)['status'],'unknown')
        c['before']['projections']['victim']['damage']=6;self.assertEqual(self.predict(c)['status'],'unknown')
    def test_no_torch_import(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import public_input_binding;assert 'torch' not in sys.modules"
        subprocess.run([sys.executable,'-B','-c',code,str(B.HERE)],check=True,capture_output=True,text=True)
if __name__=='__main__':unittest.main()
