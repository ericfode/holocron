"""Before-only public rule/binding diagnostic. No Torch/forward/fit/engine calls.

Printed traits/aspects are valid only in frozen fixtures with no changing effect.
Predictions condition on the declared play/accept-optional/target-or-host intent.
The expanded attachment task observes BOTH hosts; legacy chosen-only is distinct.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import effect_identifiability_fit as E
import actual_corpus_native_plan as A
HEADS=('target_allowed','target_removed','target_damage_delta','target_exhausted_delta','target_shield_delta','target_power_delta','target_hp_delta')
CONTROLS=('bound','legacy-omission','same-info-unbound','wrong-owner')
ASPECTS=A.ASPECTS
ROLES=('source','own_helper','opponent_helper','victim','host_a','host_b','own_base','opponent_base')
class Unknown(ValueError):pass

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def finite(value):
    if type(value)not in(int,float)or not math.isfinite(value):raise Unknown('unknown/nonfinite public scalar')
    return float(value)
def current(p,field,required=False):
    if p.get('known',{}).get(field)is not True:
        if required:raise Unknown('public current stat unknown: '+field)
        return None
    value=p.get(field)
    if field=='exhausted':
        if type(value)is not bool:raise Unknown('explicit boolean exhaustion required')
        return float(value)
    return finite(value)
def row_for(projection,rows):
    if projection.get('code')not in rows:raise Unknown('printed public definition missing')
    return rows[projection['code']]
def metadata(projection,rows):
    card=row_for(projection,rows)['card'];result={}
    for key in('traits','aspects','types','keywords'):
        value=card.get(key)
        if not isinstance(value,list)or any(not isinstance(x,str)for x in value):raise Unknown('unknown printed '+key)
        result[key]=sorted(x.lower()for x in value)
        pkey='printed_'+key
        if pkey in projection and sorted(x.lower()for x in projection[pkey])!=result[key]:raise Unknown('public printed metadata witness differs')
    result.update(cost=card.get('cost'),unique=card.get('unique'),arena=card.get('arena'))
    return result

def scene_before(source_row,case,rows):
    """Only these case fields enter: before/refs/declared_intent/observation_refs."""
    before=case['before'];refs=case['refs'];projections=before['projections'];intent=case['declared_intent'];observation_refs=case['observation_refs']
    if tuple(projections)!=ROLES and set(projections)!=set(ROLES):raise Unknown('fixed named projection bank required')
    if not observation_refs or any(r not in ROLES or projections[r]is None for r in observation_refs):raise Unknown('active public observation anchors required')
    active={}
    for role,p in projections.items():
        if p is None:
            if refs.get(role)is not None:raise Unknown('inactive role must remain null')
            continue
        if p.get('id')!=refs[role]or p.get('owner')not in('p1','p2')or p.get('known',{}).get('owner')is not True or p.get('known',{}).get('identity')is not True:raise Unknown('unknown explicit owner/identity binding')
        for field in('is_unit','is_base','present'):
            if type(p.get(field))is not bool:raise Unknown('explicit public type/presence flag required')
        if p['is_unit']and p['zone']in('ground','space'):
            for field in('damage','hp','power','exhausted','shield_count','xp_count'):current(p,field,True)
        item=copy.deepcopy(p);item['printed']=metadata(p,rows)
        if p['id']in active and semantic_unit(active[p['id']])!=semantic_unit(item):raise Unknown('duplicate physical reference disagrees')
        active[p['id']]=item
    source=projections.get('source')
    if source is None or source['zone']!='hand':raise Unknown('this diagnostic requires an own-hand prospective play')
    if intent.get('ref')not in projections or projections[intent['ref']]is None or intent.get('id')!=refs[intent['ref']]:raise Unknown('pre-action intended reference missing')
    own=source['owner'];opponent='p2'if own=='p1'else'p1'
    if own!='p1':raise Unknown('legacy18 ABI here is explicit p1-own; unknown owner never defaults')
    raw_ids={u['id']for seat in('p1','p2')for zone in('ground','space')for u in before['state']['players'][seat][zone]}
    projected_ids={i for i,p in active.items()if p['is_unit']and p['zone']in('ground','space')}
    if raw_ids!=projected_ids:raise Unknown('public arena projection is incomplete')
    document,_=E.canonical_document(source_row)
    if document['role']!='main':raise Unknown('unsupported source role')
    arena=[p for p in active.values()if p['id']in projected_ids]
    return dict(before=before,document=document,source=active[source['id']],units=arena,active=active,own=own,opponent=opponent,intended=intent['id'],observations={r:refs[r]for r in observation_refs})

def semantic_unit(p):
    return dict(owner=p['owner'],zone=p['zone'],is_unit=p['is_unit'],is_base=p['is_base'],present=p['present'],**{k:current(p,k)for k in('damage','hp','power','exhausted','shield_count','xp_count')},known={k:p.get('known',{}).get(k)is True for k in('damage','hp','power','exhausted','shield_count','xp_count')},printed=p['printed'])

def project_case(source_row,case,catalog_rows):
    s=scene_before(source_row,case,catalog_rows);before=copy.deepcopy(s['before']);source=s['source'];own_units=[p for p in s['units']if p['owner']==s['own']and p['id']!=source['id']]
    before['other_friendly_space_count']=sum(p['zone']=='space'for p in own_units);before['other_friendly_fighter_count']=sum('fighter'in p['printed']['traits']for p in own_units)
    legacy_context=[float(x)for x in A.context_vector(before,catalog_rows)]
    counts={seat:{a:sum(a in p['printed']['aspects']for p in s['units']if p['owner']==seat)for a in ASPECTS}for seat in('p1','p2')}
    anchors={};intent_projection=s['active'][s['intended']];intended34=[float(x)for x in A.candidate_vector(intent_projection,source['id'],catalog_rows)]
    for role,identity in s['observations'].items():
        p=s['active'][identity];legacy=[float(x)for x in A.candidate_vector(p,source['id'],catalog_rows)]
        relations=dict(candidate_is_source=identity==source['id'],candidate_is_intended_host_or_target=identity==s['intended'])
        # IDs, named slot positions and source/candidate catalog IDs stay outside
        # numerical/mechanical hashes. Full owner/intent relations remain explicit.
        arena=[]
        for unit in s['units']:
            arena.append(dict(**semantic_unit(unit),is_source=unit['id']==source['id'],is_intended=unit['id']==s['intended'],is_observation=unit['id']==identity))
        arena=sorted(arena,key=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')))
        features=dict(legacy_context18=legacy_context,legacy_candidate34=legacy,anchor_traits=p['printed']['traits'],anchor_aspects=p['printed']['aspects'],own_arena_aspect_counts=counts[s['own']],opponent_arena_aspect_counts=counts[s['opponent']],relations=relations,public_arena=arena)
        anchors[role]=dict(legacy34=legacy,legacy_branch_hash=digest(dict(program=s['document'],globals=legacy_context,candidate=legacy)),legacy_source_hash=digest(dict(program=s['document'],globals=legacy_context,intended_candidate=intended34)),repaired_hash=digest(dict(program=s['document'],features=features)),features=features)
    return dict(schema='public-input-binding-projector/1',program=s['document'],legacy_context18=legacy_context,anchors=anchors,scope='Raw old18/34 pre-action values and full canonical source mechanics. No checkpoint forward/new vocab inference. Printed traits/aspects only where no dynamic changer exists. All control predictors receive this same complete repaired information.')

class Interpreter:
    def __init__(self,scene,control):
        self.s=scene;self.control=control;self.owner=scene['opponent']if control=='wrong-owner'else scene['own'];self.units=list(scene['units'])
        self.source=scene['source'];self.source_id=self.source['id'];self.intent=scene['intended'];self.target=self.intent
        # Entering source belongs to the prospective public action, not an
        # observed after-state. A played unit participates in its whenPlayed query.
        if 'unit'in scene['document']['printed']['types']:
            source=copy.deepcopy(self.source);source['zone']=scene['document']['printed']['arena'];self.units.append(source)
    def expr(self,e,card=None):
        if not isinstance(e,dict):raise Unknown('typed expression required')
        kind=e.get('kind')
        if kind=='const':
            if set(e)!={'kind','value'}or isinstance(e['value'],(dict,list)):raise Unknown('unreviewed structured literal')
            return e['value']
        if kind=='ref':
            path=e.get('path')
            if path==['player']:return self.owner
            if path==['opponent']:return 'p2'if self.owner=='p1'else'p1'
            identity=card if path and path[0]=='card'else self.source_id if path and path[0]=='source'else self.target if path and path[0]=='target'else None
            if identity is None:raise Unknown('unbound reference')
            if len(path)==1:return identity
            if path==['source','parentCard']:
                if 'upgrade'not in self.s['document']['printed']['types']:raise Unknown('parent binding requires proposed upgrade attachment')
                return self.intent
            p=self.s['active'].get(identity)
            if p is None:raise Unknown('reference not public')
            if len(path)==2 and path[1]in('power','hp','damage','exhausted'):return p[path[1]]
            if path==['target','remainingHp']:return p['hp']-p['damage']
            raise Unknown('unsupported reference path')
        if kind=='unary':
            if set(e)!={'kind','op','value'}:raise Unknown('unknown unary field')
            v=self.expr(e['value'],card)
            if e['op']=='!':return not bool(v)
            if e['op']=='-'and type(v)in(int,float):return -v
            raise Unknown('unsupported unary operator')
        if kind=='binary':
            if set(e)!={'kind','op','left','right'}:raise Unknown('unknown binary field')
            a=self.expr(e['left'],card);b=self.expr(e['right'],card);op=e['op']
            if op=='&&':return bool(a)and bool(b)
            if op=='||':return bool(a)or bool(b)
            if op=='+':return finite(a)+finite(b)
            if op=='-':return finite(a)-finite(b)
            if op in('===','!=='):return(a==b)if op=='==='else(a!=b)
            raise Unknown('unsupported binary operator')
        if kind=='conditional':
            if set(e)!={'kind','condition','then','else'}:raise Unknown('unknown conditional field')
            # Validate both branches even if one would be inactive.
            yes=self.expr(e['then'],card);no=self.expr(e['else'],card);return yes if self.expr(e['condition'],card)else no
        if kind=='query':
            if set(e)!={'kind','name','receiver','args'}:raise Unknown('unknown query field')
            name=e['name'];receiver=self.expr(e['receiver'],card);args=e['args']
            if name=='hasSomeArenaUnit'and len(args)==1 and receiver in('p1','p2'):
                units=self.units if self.control=='same-info-unbound'else[p for p in self.units if p['owner']==receiver]
                return any(bool(self.expr(args[0],p['id']))for p in units)
            if name in('hasSomeAspect','hasSomeTrait')and len(args)==1:
                p=next((p for p in self.units if p['id']==receiver),self.s['active'].get(receiver))
                if p is None:raise Unknown('unbound public property receiver')
                literal=self.expr(args[0],card)
                if not isinstance(literal,str):raise Unknown('literal aspect/trait required')
                return literal.lower()in p['printed']['aspects'if name=='hasSomeAspect'else'traits']
            raise Unknown('unsupported typed query')
        raise Unknown('unsupported expression kind '+str(kind))
    def resolver(self,r):
        if not isinstance(r,dict)or set(r)-{'owner','type','arena','zone','predicate'}:raise Unknown('unreviewed public selector')
        p=self.s['active'][self.intent]
        if r.get('owner')not in('any','self','opponent'):raise Unknown('unreviewed selector owner')
        owner=self.s['own']if r['owner']=='self'else self.s['opponent']
        if r['owner']!='any'and p['owner']!=owner:return False
        if r.get('type')not in('any','unit','nonLeaderUnit'):raise Unknown('unreviewed selector type')
        if r['type']in('unit','nonLeaderUnit')and not p['is_unit']:return False
        if r['type']=='nonLeaderUnit'and'leader'in p['printed']['types']:return False
        if r.get('zone')not in('arena','anyAttackable')or p['zone']not in('ground','space'):return False
        if r.get('arena')not in(None,'ground','space'):raise Unknown('unreviewed selector arena')
        if r.get('arena')and p['zone']!=r['arena']:return False
        return bool(self.expr(r['predicate'],self.intent))if'predicate'in r else True
    def targets(self,t,anchor):
        if t=='parent'and'upgrade'not in self.s['document']['printed']['types']:raise Unknown('parent target requires proposed upgrade attachment')
        if t in('chosen','parent'):return [anchor]if self.control=='same-info-unbound'else[self.intent]
        if t=='self':return[self.source_id]
        if isinstance(t,dict):
            value=self.expr(t)
            if value not in self.s['active']:raise Unknown('unbound target expression')
            return[value]
        raise Unknown('unsupported effect target')
    def effect(self,e,anchor,out,keywords):
        if not isinstance(e,dict):raise Unknown('typed effect required')
        kind=e.get('kind')
        if kind=='damage':
            if set(e)!={'kind','target','amount'}:raise Unknown('unreviewed damage semantics')
            amount=self.expr(e['amount']);amount=finite(amount)
            if amount<0:raise Unknown('negative damage unsupported')
            if anchor not in self.targets(e['target'],anchor):return
            p=self.s['active'][anchor]
            if p['shield_count']>0 and amount>0:out[4]-=1
            else:out[2]+=amount
        elif kind=='modifyStats':
            if set(e)!={'kind','target','power','hp','duration'}or e['duration']not in('phase','persistent'):raise Unknown('unreviewed stat effect')
            power=finite(self.expr(e['power']));hp=finite(self.expr(e['hp']))
            if anchor in self.targets(e['target'],anchor):out[5]+=power;out[6]+=hp
        elif kind=='gainKeyword':
            if set(e)!={'kind','target','keyword','amount','duration'}or e['duration']!='persistent'or e['keyword']!='saboteur'or self.expr(e['amount'])!=1:raise Unknown('unreviewed keyword effect')
            if anchor in self.targets(e['target'],anchor):keywords['saboteur']=1
        elif kind=='conditional':
            raise Unknown('conditional effect continuations not in this frozen expression-only condition contract')
        elif kind=='noAction':
            if set(e)!={'kind'}:raise Unknown('unknown noAction fields')
        else:raise Unknown('unsupported effect kind '+str(kind))

def predict_case(source_row,case,catalog_rows,control='bound'):
    if control not in CONTROLS:raise ValueError('unreviewed control')
    empty={ref:dict(values=[0.]*7,mask=[0]*7,keywords_added={})for ref in case.get('observation_refs',[])}
    try:
        projected=project_case(source_row,case,catalog_rows)
        if control=='legacy-omission':raise Unknown('legacy schema omits arena-aspect predicates and actual-endpoint intended-host relation; no unknown-as-false fallback')
        scene=scene_before(source_row,case,catalog_rows);document=scene['document'];machine=Interpreter(scene,control);printed=document['printed'];abilities=document['abilities']
        if 'upgrade'in printed['types']:
            host=scene['active'][scene['intended']]
            if not host['is_unit']or host['zone']not in('ground','space'):raise Unknown('proposed parent must be a public arena unit')
        if abilities['leader']or abilities['unit']:raise Unknown('unsupported alternate ability side')
        for a in abilities['card']:
            if set(a)-{'trigger','costs','effect','optional','targetResolver','condition'}or a.get('trigger')not in('whenPlayed','constant')or a.get('costs')!=[]:raise Unknown('unsupported ability/continuation/cost/trigger')
            if 'optional'in a and type(a['optional'])is not bool:raise Unknown('unreviewed optional choice')
            if a.get('targetResolver')is not None and not machine.resolver(a['targetResolver']):raise Unknown('proposed target fails public selector')
        observations={}
        for ref,anchor in scene['observations'].items():
            p=scene['active'][anchor]
            if not p['is_unit']or p['zone']not in('ground','space')or not p['present']:raise Unknown('continuous public arena unit anchor required')
            out=[0.]*7;keywords={}
            if 'upgrade'in printed['types']:
                condition=document['attachCondition']
                if condition is not None and not machine.expr(condition,scene['intended']):raise Unknown('proposed attachment host fails public predicate')
                if control=='same-info-unbound'or anchor==scene['intended']:
                    out[5]+=finite(printed['upgradePower']);out[6]+=finite(printed['upgradeHp'])
            elif printed['types']!=['unit']:raise Unknown('unsupported play type')
            for ability in abilities['card']:
                if ability.get('condition')is None or machine.expr(ability['condition']):machine.effect(ability['effect'],anchor,out,keywords)
            out[5]=max(0.,p['power']+out[5])-p['power']
            if p['hp']+out[6]-p['damage']-out[2]<=0:raise Unknown('lethal/death/hook path outside frozen nonterminal contract')
            observations[ref]=dict(values=out,mask=[0,1,1,1,1,1,1],keywords_added=keywords)
        return dict(status='known',control=control,observations=observations,unknown_reasons=[],projector=projected,scope='Conditional prospective play under fixed public intent; no availability/offeredness oracle. Seven-head order; head0 unknown. Keyword witness is separate from numeric-head qualification.')
    except (Unknown,ValueError,KeyError,TypeError)as error:
        return dict(status='unknown',control=control,observations=empty,unknown_reasons=[str(error)],projector=locals().get('projected'),scope='Unknown is mask0, never a physical zero prediction; no fallback or case reselection.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError('preserve prior prediction artifact')
    receipt=json.loads(a.receipt.read_text());catalog=json.loads(a.catalog.read_text());rows={r['setCode']:r for r in catalog['cards']}if isinstance(catalog.get('cards'),list)else catalog.get('selected_whole_rows',catalog);cases=[]
    for case in receipt['cases']:
        raw=rows[case['card']];cases.append(dict(world_id=case['world_id'],predictions={c:predict_case(raw,case,rows,c)for c in CONTROLS}))
    stopped=any(c['predictions']['bound']['status']!='known'for c in cases)
    output=dict(schema='public-input-binding-predictions/1',status='stopped-unknown'if stopped else'supported-frozen-fixture-subset',heads=list(HEADS),controls=list(CONTROLS),cases=cases,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),receipt_sha256=hashlib.sha256(a.receipt.read_bytes()).hexdigest(),catalog_sha256=hashlib.sha256(a.catalog.read_bytes()).hexdigest(),neural_forwards=0,native_applies=0,optimizer_updates=0,semantic_validated=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(path=str(a.out),sha256=hashlib.sha256(a.out.read_bytes()).hexdigest())))
    if stopped:raise SystemExit(1)
if __name__=='__main__':main()
