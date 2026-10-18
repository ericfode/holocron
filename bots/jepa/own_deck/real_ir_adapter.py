"""Explicit, ID-free semantic adapter for a small reviewed real-IR grammar.

The raw whole row is retained. Adapter support is a serialization claim, never
native conformance, prediction accuracy, or compatibility with the old f8 model.
Import and adaptation use only the standard library.
"""
import copy
import hashlib
import json
import math

SCHEMA='jepa-real-ir-adapter/1'
PROGRAM_SCHEMA='jepa-real-ir-program/1'
CATALOGUE_SHA='0219449c7fbd14cd974f6d496bf05a585807aa1204eac86aefe231e79f87a812'
RUNTIME_SHA='91553fdcd7862ebe473bfbbddaf4f17fdf37c2fc7fad7319bf2686d82122a957'
ENGINE_REVISION='c7ee39554901278cee70f61fd8b26fb1920696b3'
TOP={'setCode','sourcePath','sourceHash','abilities','className','baseClass','stateWatchers','id','internalName',
    'status','card','dataHash','keywordValues','requiredCapabilities','attachCondition'}
PRINTED={'title','subtitle','cost','hp','power','text','deployBox','epicAction','unique','rules','upgradePower',
    'upgradeHp','id','aspects','traits','arena','keywords','types','setId','setCodes','internalName'}
ABILITY={'trigger','title','contextTitle','costs','optional','requiresConfirmation','coordinate','attackerMustSurvive',
    'targetResolver','condition','effect','then','ifYouDo','hooks','gainedHost','attachedContext','targetResolvers'}
RESOLVER={'promptTitle','promptTitleParts','owner','type','arena','zone','optional','predicate','mode','count'}
CAPABILITIES={'cardType:'+v for v in('unit','event','base')}|{'trigger:'+v for v in('event','whenPlayed')}|{
    'targetType:'+v for v in('any','unit','nonLeaderUnit','base')}|{'targetZone:'+v for v in('arena','anyAttackable','base')}|{
    'ir:const','ir:damage','ir:heal','ir:binary','ir:ref','binary:<=','ref:card.cost','targetMode:single'}


def canonical_bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def row_digest(row):return hashlib.sha256(canonical_bytes(row)).hexdigest()
def _number(value):
    try:return type(value)in(int,float)and math.isfinite(value)
    except OverflowError:return False


def contract():
    return dict(schema=SCHEMA,program_schema=PROGRAM_SCHEMA,profile='Raw printed values with present/known flags; null is never numeric zero.',
        grammar='Keywordless unit/base plain profiles, or one card-side event/whenPlayed chosen constant damage/heal ability; no extra executable rules.',
        selector_defaults=dict(owner='any',type='any',arena=None,zone=None,predicate=None,mode=None,count=None,optional=False),
        ability_defaults=dict(costs=[],optional=False,requiresConfirmation=False,coordinate=False,attackerMustSurvive=False),
        owner_binding='self/opponent relative to the source actual owner, not an absolute seat',
        target_domains='Native portable type and zone remain separate. anyAttackable includes units/bases as type allows; arena excludes bases; base is retained distinctly; absent zone/arena has no corresponding filter.',
        cost_cap='Separate present flag and raw nonnegative integer literal. Absence is unbounded, not cap3/4.',
        arena='Absent/null restriction has values=null; explicit ground/space becomes a singleton set. No ground default.',
        healing='Target prompt uses require_change=false: healthy healing targets can be offered. No outcomes or allowed masks are computed here.',
        support='Only full_card_supported rows qualify for whole-row coverage. program_adapter_supported alone does not cover keywords or other rules.',
        exact_program_key='family_key is a backward-compatible alias for the exact structural program hash, retaining amount/cap/trigger. It is not a numeric-abstracted or held-out mechanism family.',
        not_v1_compatible=True,native_conformance_verified=False,semantic_validated=False,
        reference_pins=dict(catalogue_sha256=CATALOGUE_SHA,runtime_admission_sha256=RUNTIME_SHA,engine_revision=ENGINE_REVISION),
        source_locations=['crates/kessel/src/selector_contract.rs:655-707','crates/kessel/src/ability_ir.rs:1142-1199',
            'crates/kessel/src/generic_runtime.rs:1439-1490','crates/kessel/src/generic_runtime.rs:1827-1829'])


def adapt_row(row):
    """Return a complete row record; unsupported executable fields fail closed."""
    raw=copy.deepcopy(row);issues=[]
    def mark(path,reason,scope='whole-card'):
        item=dict(path=path,reason=reason,scope=scope)
        if item not in issues:issues.append(item)
    def keys(value,allowed,path,scope='program'):
        if not isinstance(value,dict):mark(path,'object required',scope);return False
        for key in sorted(set(value)-allowed):mark(path+'.'+key,'unreviewed field',scope)
        return True
    def strict_bool(value,key,path,default=False):
        result=value.get(key,default)
        if type(result)is not bool:mark(path+'.'+key,'strict boolean required','program');return None
        return result
    def display(value,path):
        if type(value)is not str:mark(path,'literal display string required','program')
    def constant(node,path,amount=False):
        if not keys(node,{'kind','value'},path):return None
        value=node.get('value')
        if node.get('kind')!='const' or type(value)is not int or value<0 or(amount and value not in(1,2,3,4,5)):
            mark(path,'literal amount1..5 required'if amount else'nonnegative integer literal required','program');return None
        return value
    def predicate(node,path):
        if node is None:return dict(present=False,value=None)
        if not keys(node,{'kind','op','left','right'},path):return None
        if node.get('kind')!='binary'or node.get('op')!='<='or node.get('left')!=dict(kind='ref',path=['card','cost']):
            mark(path,'only literal printed card.cost <= cap is reviewed','program');return None
        cap=constant(node.get('right'),path+'.right')
        return dict(present=True,value=cap)if cap is not None else None
    def selector(node,path):
        start=len(issues)
        if not keys(node,RESOLVER,path):return None
        owner=node.get('owner','any');kind=node.get('type','any');zone=node.get('zone');arena=node.get('arena')
        if owner not in('any','self','opponent'):mark(path+'.owner','unreviewed owner','program')
        if kind not in('any','unit','nonLeaderUnit','base'):mark(path+'.type','unreviewed target kind','program')
        if zone not in(None,'arena','anyAttackable','base'):mark(path+'.zone','unreviewed zone','program')
        if arena not in(None,'ground','space'):mark(path+'.arena','unreviewed arena restriction','program')
        if(kind=='base'and(zone=='arena'or arena is not None))or(kind in('unit','nonLeaderUnit')and zone=='base')or(zone=='base'and arena is not None):
            mark(path,'target kind/zone/arena constraints have no reviewed legal overlap','program')
        optional=strict_bool(node,'optional',path)
        if node.get('mode')not in(None,'single'):mark(path+'.mode','multiple/other target mode unsupported','program')
        if node.get('count')is not None:mark(path+'.count','explicit target count unsupported','program')
        if node.get('promptTitle')is not None:mark(path+'.promptTitle','named prompt title requires a separately reviewed named descriptor','program')
        if node.get('promptTitleParts',[])!=[]:mark(path+'.promptTitleParts','dynamic display expression unsupported','program')
        cap=predicate(node.get('predicate'),path+'.predicate')
        if len(issues)!=start:return None
        return dict(owner=owner,target_kind=kind,zone=dict(present='zone'in node,value=zone),
            arena=dict(present=arena is not None,values=None if arena is None else[arena]),cost_cap=cap,
            optional=optional,mode=node.get('mode'),count=None)
    def ability(node,path,types):
        start=len(issues)
        if not keys(node,ABILITY,path):return None
        trigger=node.get('trigger')
        if trigger not in('event','whenPlayed'):mark(path+'.trigger','unreviewed trigger','program')
        if(trigger=='event'and types!=['event'])or(trigger=='whenPlayed'and types!=['unit']):
            mark(path+'.trigger','trigger/source printed-type mismatch','program')
        if 'title'not in node:mark(path+'.title','required native title missing','program')
        else:display(node['title'],path+'.title')
        if node.get('contextTitle',[])!=[]:mark(path+'.contextTitle','dynamic display expression unsupported','program')
        if node.get('costs',[])!=[]:mark(path+'.costs','extra ability costs unsupported','program')
        flags={key:strict_bool(node,key,path)for key in('optional','requiresConfirmation','coordinate','attackerMustSurvive')}
        for key in('requiresConfirmation','coordinate','attackerMustSurvive'):
            if flags[key]is True:mark(path+'.'+key,'additional execution behavior unsupported','program')
        for key in('condition','then','ifYouDo','gainedHost','attachedContext'):
            if node.get(key)is not None:mark(path+'.'+key,'additional condition/effect/context unsupported','program')
        for key in('hooks','targetResolvers'):
            if node.get(key,[])!=[]:mark(path+'.'+key,'additional hook/resolver unsupported','program')
        target=selector(node.get('targetResolver'),path+'.targetResolver')
        effect=node.get('effect');op=None;amount=None
        if keys(effect,{'kind','target','amount'},path+'.effect'):
            op=effect.get('kind')
            if op not in('damage','heal'):mark(path+'.effect.kind','only damage/heal supported','program')
            if effect.get('target')!='chosen':mark(path+'.effect.target','only declared chosen target supported','program')
            amount=constant(effect.get('amount'),path+'.effect.amount',True)
        if len(issues)!=start:return None
        return dict(schema=PROGRAM_SCHEMA,form='chosen-constant',side='card',trigger=trigger,
            costs=[],optional=flags['optional'],requires_confirmation=False,coordinate=False,attacker_must_survive=False,
            selector=target,effect=dict(operator=op,destination='chosen',amount=dict(kind='const',value=amount)))

    if not keys(row,TOP,'$','whole-card'):
        return dict(schema=SCHEMA,contract=SCHEMA,raw_row=raw,whole_row_sha256=row_digest(raw),profile_serialized=False,
            program_adapter_supported=False,full_card_supported=False,fully_supported=False,unsupported_reasons=issues,canonical_program=None,family_key=None,exact_program_key=None)
    printed=row.get('card');profile_start=len(issues);profile={}
    if keys(printed,PRINTED,'$.card','profile'):
        for name in('cost','hp','power','upgradePower','upgradeHp'):
            value=printed.get(name);known=_number(value)
            if value is not None and not known:mark('$.card.'+name,'finite numeric or null printed field required','profile')
            profile[name]=dict(present=name in printed,known=known,value=value)
        for name in('types','aspects','traits'):
            value=printed.get(name);known=isinstance(value,list)and all(type(v)is str for v in value)
            if not known:mark('$.card.'+name,'complete printed string list required','profile')
            profile[name]=dict(present=name in printed,known=known,value=copy.deepcopy(value))
        arena=printed.get('arena');known=arena in('ground','space')
        if arena is not None and not known:mark('$.card.arena','unreviewed printed arena','profile')
        profile['arena']=dict(present='arena'in printed,known=known,value=arena)
        value=printed.get('unique');profile['unique']=dict(present='unique'in printed,known=type(value)is bool,value=value)
        if type(value)is not bool:mark('$.card.unique','complete strict printed boolean required','profile')
    profile_ok=not any(v['scope']=='profile'for v in issues[profile_start:])and isinstance(printed,dict)
    printed=printed if isinstance(printed,dict)else{};types=printed.get('types');sides=row.get('abilities');program=None
    if not isinstance(row.get('setCode'),str)or not row['setCode']:mark('$.setCode','source code required')
    if row.get('status')!='supported':mark('$.status','source compiler status is not supported')
    capabilities=row.get('requiredCapabilities')
    if not isinstance(capabilities,list)or not all(type(v)is str for v in capabilities):mark('$.requiredCapabilities','complete capability string list required')
    else:
        for i,capability in enumerate(capabilities):
            if capability not in CAPABILITIES:mark('$.requiredCapabilities['+str(i)+']','unreviewed required capability: '+capability)
    if types not in(['unit'],['event'],['base']):mark('$.card.types','only ordinary unit/event/base profile reviewed')
    source_class=row.get('baseClass')
    if source_class is not None and(source_class not in('NonLeaderUnitCard','EventCard','BaseCard')or
        types!=[{'NonLeaderUnitCard':'unit','EventCard':'event','BaseCard':'base'}.get(source_class)]):
        mark('$.baseClass','source base class/printed type mismatch or unreviewed class')
    if printed.get('keywords')!=[]:mark('$.card.keywords','printed keywords not represented')
    if row.get('keywordValues')!={}:mark('$.keywordValues','keyword behavior not represented')
    for name in('deployBox','epicAction','rules'):
        if printed.get(name)not in(None,''):mark('$.card.'+name,'additional printed rule/deploy behavior unsupported')
    for name in('upgradePower','upgradeHp'):
        if printed.get(name)is not None:mark('$.card.'+name,'upgrade modifiers outside ordinary profile support')
    if row.get('attachCondition')is not None:mark('$.attachCondition','attachment condition unsupported')
    if row.get('stateWatchers',[])not in(None,[]):mark('$.stateWatchers','state watchers unsupported')
    card_side=sides.get('card',[])if isinstance(sides,dict)else[]
    for trigger,expected in(('event','EventCard'),('whenPlayed','NonLeaderUnitCard')):
        if isinstance(card_side,list)and any(isinstance(a,dict)and a.get('trigger')==trigger for a in card_side)and row.get('baseClass')!=expected:
            mark('$.baseClass','reviewed executable source base class required')
    program_start=len(issues)
    if keys(sides,{'card','unit','leader'},'$.abilities'):
        all_abilities=[]
        for side in('card','unit','leader'):
            values=sides.get(side,[])
            if not isinstance(values,list):mark('$.abilities.'+side,'ability list required','program');continue
            if values and side!='card':mark('$.abilities.'+side,'non-card side execution unsupported','program')
            for i,node in enumerate(values):all_abilities.append((side,ability(node,'$.abilities.'+side+'['+str(i)+']',types)))
        if not all_abilities:
            if types not in(['unit'],['base']):mark('$.abilities','empty-program full profile is unit/base only; events require one event program','program')
            if printed.get('text')not in(None,''):mark('$.card.text','empty IR cannot explain nonempty printed rule text')
            program=dict(schema=PROGRAM_SCHEMA,form='plain-profile',side=None,trigger=None,abilities=[])
        elif len(all_abilities)==1 and all_abilities[0][0]=='card':program=all_abilities[0][1]
        else:mark('$.abilities','multiple complete abilities unsupported','program')
    program_ok=program is not None and not any(v['scope']=='program'for v in issues[program_start:])
    full=profile_ok and program_ok and not issues
    # Default-presence spelling and source identity do not create new families.
    def semantic(value):
        if isinstance(value,dict):return{k:semantic(v)for k,v in value.items()if k!='present'}
        if isinstance(value,list):return[semantic(v)for v in value]
        return value
    family=row_digest(semantic(program))if program_ok else None
    return dict(schema=SCHEMA,contract=SCHEMA,raw_row=raw,whole_row_sha256=row_digest(raw),
        codes=dict(primary=row.get('setCode'),id=row.get('id'),set_id=copy.deepcopy(printed.get('setId')),set_codes=copy.deepcopy(printed.get('setCodes'))),
        provenance={k:copy.deepcopy(row.get(k))for k in('sourcePath','sourceHash','dataHash','status')},
        printed_profile=profile,profile_serialized=profile_ok,ability_sides=copy.deepcopy(sides),canonical_program=program if program_ok else None,
        program_adapter_supported=program_ok,full_card_supported=full,fully_supported=full,family_key=family,
        exact_program_key=family,unsupported_reasons=issues,native_conformance_verified=False,semantic_validated=False)
