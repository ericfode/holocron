"""Independent public-input/native endpoint audit; stdlib + NumPy, never runs engine/NN.

Preparation and synthetic tests are harmless. Actual receipt verification is an
explicit coordinator action. Same-card legacy hashes describe architecture input
sufficiency, not an unsupported old-checkpoint inference or embedding lookup.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

ASPECTS = ('vigilance','command','aggression','cunning','heroism','villainy')
NUMERIC = ('damage','hp','power','exhausted','shield_count','xp_count')
DELTA_HEADS = ('target_damage_delta','target_exhausted_delta','target_shield_delta','target_power_delta','target_hp_delta')
DELTA_FIELDS = ('damage','exhausted','shield_count','power','hp')
PRINTED = ('cost','hp','power','unique','upgradePower','upgradeHp','aspects','traits','arena','keywords','types')
DISPLAY = {'title','contextTitle','promptTitle'}


def require(ok, message):
    if not ok: raise ValueError(message)


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def pin(path):
    p=Path(path).resolve();return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def typed_tokens(value, path=()):
    """Exact dictionary-key invariance, semantic list order and numeric types."""
    if isinstance(value,dict):
        out=[(path,'node','object')]
        for k in sorted(value):out.extend(typed_tokens(value[k],path+(k,)))
        return out
    if isinstance(value,list):
        out=[(path,'length',len(value))]
        for i,v in enumerate(value):out.extend(typed_tokens(v,path+(i,)))
        return out
    if type(value)is bool:return [(path,'boolean',value)]
    if type(value)in(int,float):
        require(np.isfinite(value),'nonfinite rule literal');return [(path,'number',float(value))]
    if value is None:return [(path,'null','null')]
    require(isinstance(value,str),'untyped rule literal');return [(path,'enum',value)]


def semantic_document(row):
    """Independent original whole-card semantic selection + scoped alpha cleanup."""
    def clean(v,scope,mapping):
        if isinstance(v,list):return [clean(x,scope,mapping)for x in v]
        if not isinstance(v,dict):return v
        result={}
        for k in sorted(v):
            if k in DISPLAY:continue
            x=v[k]
            if k=='hooks':result[k]=[clean(h,scope+('hook',i),{})for i,h in enumerate(x)]
            elif k=='argumentBinding':
                require(v.get('kind')=='dataPath' and v.get('root')==['event'] and set(x)=={'id','bindAt','readAt'},'unreviewed callback binding')
                require(x['bindAt']=='callbackInvocation' and x['readAt']=='expressionEvaluation','binding timing differs')
                mapping.setdefault(x['id'],len(mapping));result[k]=dict(binding_scope=list(scope),binding_slot=mapping[x['id']],bindAt=x['bindAt'],readAt=x['readAt'])
            else:result[k]=clean(x,scope,mapping)
        return result
    abilities={side:[clean(a,('ability',side,i),{})for i,a in enumerate(items)]for side,items in row['abilities'].items()}
    return dict(role='main',printed={k:copy.deepcopy(row['card'].get(k))for k in PRINTED},keywordValues=copy.deepcopy(row['keywordValues']),attachCondition=copy.deepcopy(row.get('attachCondition')),abilities=abilities)


def source_program_hash(row):return digest(typed_tokens(semantic_document(row)))


def physical(capture):
    """Read all own/public objects, including attached upgrades, by identity."""
    found={}
    def add(card,seat,zone,parent=None):
        if card is None:return
        require(isinstance(card,dict)and isinstance(card.get('id'),str),'physical identity missing')
        identity=card['id'];require(identity not in found,'duplicate physical identity')
        found[identity]=dict(card=card,seat=seat,zone=zone,parent=parent)
        for u in card.get('upgrades',[]):add(u,seat,'upgrade',identity)
    for seat,p in capture['state']['players'].items():
        require(seat in ('p1','p2'),'unreviewed player')
        require(not p['deck'] and (seat!='p2'or not p['hand']),'hidden pile/hand exposure')
        for zone in ('ground','space','hand','discard','resources'):
            for c in p.get(zone,[]):add(c,seat,zone)
        for zone in ('base','leader'):
            c=p.get(zone)
            if isinstance(c,dict):add(c,seat,zone)
    return found


def validate_capture(capture,refs):
    objects=physical(capture)
    s=capture['settlement'];require(s['decision']==capture['decision'] and s['ability_program']==capture['abilityProgramPlusOne'],'settlement projection mismatch')
    keys=('ability_program','death_depth','death_pending','death_window','pending_programs','pending_triggers','after_attack_triggers','after_attack_programs')
    require(all(type(s[k])is int and s[k]>=0 for k in keys),'invalid continuation counters')
    settled=bool(capture['terminal'])or(capture['decision']=='Window'and all(s[k]==0 for k in keys)and not s['event_group_active']and not s['support_pending'])
    require(type(capture['settled'])is bool and capture['settled']==settled,'incorrect settled witness')
    require(capture['terminal']is False,'unreviewed terminal endpoint')
    require(set(capture['projections'])==set(refs),'projection bank/refs differ')
    shield_ids=set()
    for slot,identity in refs.items():
        p=capture['projections'][slot]
        if identity is None:require(p is None,'inactive projection must be null');continue
        require(p is not None and p['id']==identity,'projection identity differs')
        actual=objects.get(identity)
        require(p['present']==(actual is not None),'projection presence differs')
        if actual is None:continue
        card=actual['card'];require((p['owner'],p['zone'],p['code'])==(actual['seat'],actual['zone'],card['setCode']),'projection owner/zone/code differs')
        if p['known']['damage']:require(p['damage']==card['damage'],'physical damage mismatch')
        if p['known']['exhausted']:require(p['exhausted']==card['exhausted'],'physical exhaustion mismatch')
        for f in ('hp','power'):
            if p['known'][f] and f in card:require(p[f]==card[f],'physical '+f+' mismatch')
        shields=[u for u in card.get('upgrades',[])if u['setCode']=='TOKEN_SHIELD']
        for u in shields:
            require(u.get('token')is True and u.get('parent',identity)==identity and u['id']not in shield_ids,'physical Shield link differs');shield_ids.add(u['id'])
        if p['known']['shield_count']:require(p['shield_count']==len(shields),'physical Shield count differs')
    return settled


def ready(capture):return sum(not c['exhausted']for c in capture['state']['players']['p1']['resources'])
def actions_for(capture,identity):return [a for a in capture['offeredActions']if a.get('kind')=='card'and a.get('card')==identity]


def legacy_context(before,rows):
    own=before['state']['players']['p1'];source=before['projections']['source'];objects=physical(before)
    aspects={a:0 for a in ASPECTS}
    for role in ('base','leader'):
        code=own[role].get('setCode')or before['own_aspect_sources'][role]
        for a in rows[code]['card']['aspects']:aspects[a]+=1
    other=[o for identity,o in objects.items()if o['seat']=='p1'and o['zone']in('ground','space')and identity!=source['id']]
    space=sum(o['zone']=='space'for o in other);fighters=sum('fighter'in rows[o['card']['setCode']]['card']['traits']for o in other)
    return np.asarray([ready(before),source['zone']=='hand',*[aspects[a]for a in ASPECTS],space,fighters,*[source[k]for k in('power','hp','damage','exhausted')],*[source['known'][k]for k in('power','hp','damage','exhausted')]],np.float32)


def legacy_candidate(p,source,rows):
    require(p is not None and p['owner']in('p1','p2'),'active known public candidate needed')
    k=p['known'];v={f:float(p[f])if k[f]else 0. for f in NUMERIC};remaining=bool(k['hp']and k['damage'])
    card=rows[p['code']]['card'];traits=set(card['traits']);cost=card.get('cost');costknown=type(cost)in(int,float)and np.isfinite(cost);unique=card.get('unique');uniqueknown=type(unique)is bool
    return np.asarray([p['owner']=='p1',p['owner']=='p2',p['is_unit'],p['is_base'],p['zone']=='ground',p['zone']=='space',p['id']==source,p['present'],v['damage'],v['hp'],v['hp']-v['damage']if remaining else 0.,v['power'],v['exhausted'],v['shield_count'],v['xp_count'],k['damage'],k['hp'],remaining,k['power'],k['exhausted'],k['shield_count'],k['xp_count'],*[t in traits for t in('imperial','creature','spectre')],True,cost if costknown else 0.,costknown,unique if uniqueknown else 0.,uniqueknown,'upgrade'in card['types'],'leader'in card['types'],'vehicle'in traits,'fighter'in traits],np.float32)


def legacy_hash(program,context,candidate):
    require(context.shape==(18,)and candidate.shape==(34,),'legacy architecture dimensions')
    return hashlib.sha256(program.encode()+context.astype(np.float32).tobytes()+candidate.astype(np.float32).tobytes()).hexdigest()


def observed_deltas(before,after,ref):
    """Native after evidence only; same physical surviving public object required."""
    a,z=before['projections'][ref],after['projections'][ref]
    require(a is not None and z is not None and a['id']==z['id'],'fixed observation identity')
    known=bool(z['present']and z['zone']==a['zone']and z['in_arena']and a['in_arena'])
    return {name:dict(known=known and bool(a['known'][field]and z['known'][field]),value=float(z[field])-float(a[field])if known and a['known'][field]and z['known'][field]else None)for name,field in zip(DELTA_HEADS,DELTA_FIELDS)}


def collision_records(records):
    groups={};pairs=[]
    for r in records:
        if not r['known']:continue
        key=(r['kind'],r['input_sha256'],r['head']);previous=groups.setdefault(key,[])
        for old in previous:
            if old['value']!=r['value']:pairs.append(dict(kind=r['kind'],head=r['head'],left=old['case'],right=r['case'],left_ref=old['ref'],right_ref=r['ref'],input_sha256=r['input_sha256'],left_value=old['value'],right_value=r['value']))
        previous.append(r)
    return pairs


def corrected_public_features(before,rows,intended,anchor):
    """An independent identity-free complete-public-fixture fingerprint.

    A diagnostic feature witness, not a production encoder or interpreter. All
    membership, ownership, printed mechanics, current numeric state and intent
    relations come exclusively from this pre-action snapshot/public catalogue.
    """
    objects=physical(before);source=before['projections']['source']['id'];projections={p['id']:p for p in before['projections'].values()if p is not None}
    def describe(identity):
        o=objects[identity];card=rows[o['card']['setCode']]['card'];p=projections.get(identity)
        public=dict(owner=o['seat'],zone=o['zone'],printed={k:copy.deepcopy(card.get(k))for k in PRINTED},source=identity==source,intended=identity==intended,anchor=identity==anchor)
        public['numeric']={f:dict(known=bool(p['known'][f]),value=p[f]if p['known'][f]else None)for f in NUMERIC}if p is not None else {f:o['card'].get(f)for f in('damage','hp','power','exhausted')}
        return public
    members=[]
    for identity,o in objects.items():
        # Deck/opponent hand are already rejected. Own hand is legitimate; omit
        # resource identities while preserving public ready/total counts below.
        if o['zone']=='resources':continue
        item=describe(identity)
        if o['parent']is not None:item['parent_relation']=describe(o['parent'])
        members.append(item)
    members.sort(key=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')))
    return dict(ready_resources=ready(before),total_resources=len(before['state']['players']['p1']['resources']),members=members)


def validate_journal(journal,raw):
    require(journal and journal[0]['planSha256']==raw['collectionPlanSha256'],'journal plan pin')
    intents={};ends={};complete={}
    for row in journal[1:]:
        phase=row['phase']
        if phase=='beforeApply':
            n=row['applyCall'];require(n==len(intents)+1,'nonsequential apply journal');intents[n]=row
        elif phase in('afterApply','applyError'):
            n=row['applyCall'];require(n in intents and n not in ends and row['context']==intents[n]['context']and row['branch']==intents[n]['branch'],'unmatched native boundary');ends[n]=row
        elif phase=='contextComplete':
            require(row['context']not in complete,'duplicate completed root');complete[row['context']]=row['case']
        else:raise ValueError('unreviewed journal phase')
    require(len(intents)==raw['applyCalls']and set(intents)==set(ends),'native accounting mismatch')
    for case in raw['cases']:
        matches=[k for k,v in complete.items()if v==case];require(len(matches)==1,'case/final journal boundary mismatch');key=matches[0]
        calls=[n for n,v in intents.items()if v['context']==key]
        require(len(calls)==case['applyCalls']==len(case['steps']),'root apply tally/errors differ')
        for n,step in zip(calls,case['steps']):
            a,z=intents[n],ends[n]
            require(a['before']==step['before']and a['offeredAction']==step['action']and a['branch']==step['stage']and z['phase']=='afterApply'and z['after']==step['after'],'journal/raw action mismatch')
    require(len(complete)==len(raw['cases']),'extra native roots')
    return dict(apply_calls=len(intents),completed_roots=len(complete),apply_errors=sum(r['phase']=='applyError'for r in ends.values()))


def validate_case(case,rows):
    before=case['before'];refs=case['refs'];require(validate_capture(before,refs)and before['decision']=='Window','unclean root')
    require(case['publicSnapshotRoundtripExact']is True and case['engineError']is None and case['completion']=='settled','native error/inexact/pending outcome')
    source=before['projections']['source'];require(source['code']==case['card']and source['zone']=='hand'and source['owner']=='p1','source is not own known hand instance')
    require(case['playAction']in actions_for(before,source['id']),'source play not offered')
    last=before
    for i,step in enumerate(case['steps']):
        require(step['before']==last and step['action']in last['offeredActions'],'unoffered/discontinuous native chain')
        validate_capture(step['after'],refs)
        if i==0:require(step['action']==case['playAction'],'first step not source play')
        last=step['after']
    final=case['final'];require(final is not None and final==last and case.get('lastObserved',last)==last and validate_capture(final,refs),'future is not last settled native endpoint')
    require(ready(before)>ready(final),'not an actual paid action')
    z=final['projections']['source'];require(z['zone']!='hand','source not committed')
    intent=case['declared_intent'];require(intent['ref']in refs and refs[intent['ref']]==intent['id'],'public predeclared intent identity mismatch')
    prompt=case['targetPrompt'];action=case['targetAction']
    require(prompt is not None and any(s['after']==prompt for s in case['steps'])and action in actions_for(prompt,intent['id']),'target/attachment not offered')
    require(any(s['before']==prompt and s['action']==action for s in case['steps']),'intended action not actually committed')
    require(case['intendedTargetCommitted']is True,'missing attempted target bookkeeping')
    if case['card']=='LOF_215':
        objects=physical(final);actual=objects.get(source['id'])
        require(actual is not None and actual['zone']=='upgrade'and actual['parent']==intent['id']and case['final_source_parent']==intent['id'],'after-only physical intended parent binding differs')
    else:require(case['final_source_parent']is None,'unexpected source parent')
    return before,final


def check_predictor_source(path,function_names):
    """Narrow static guard; full source review is still required."""
    tree=ast.parse(Path(path).read_text());selected=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))and node.name in function_names:
            literals=[v.value for v in ast.walk(node)if isinstance(v,ast.Constant)and isinstance(v.value,str)]
            require(not any(__import__('re').search(r'\b(?:LAW|LOF|ASH|SEC|JTL|SOR|TWI|SHD|IBH|HMW)_\d{3}\b',v)for v in literals),'card-ID dispatch literal inside predictor')
            require(not(set(literals)&{'final','lastObserved','targetPrompt','targetAction','steps','engineError','final_source_parent','intendedTargetCommitted','playAction','offeredActions'}),'native future/action-oracle field inside predictor')
            selected.append(node.name)
    require(set(selected)==set(function_names),'reviewed predictor functions missing')
    return dict(source=pin(path),functions=sorted(selected),scope='No literal printed-code dispatch in selected function ASTs; source review covers indirect dispatch/dependencies.')


def validate_world(case,world,rows):
    require(case['card']==world['source_code'],'source/world differs')
    before=case['before'];objects=physical(before);active={r:p for r,p in before['projections'].items()if p is not None}
    own_arena=[o for o in objects.values()if o['seat']=='p1'and o['zone']in('ground','space')]
    require(ready(before)==world['ready_resources'],'funding differs')
    require(case['declared_intent']['ref']==world['intent_ref']and case['observation_refs']==world['observation_refs'],'predeclared action/observation roles differ')
    if world['cohort']=='own-aspect-condition':
        require(len(own_arena)==1 and active['own_helper']['code']==world['own_helper']and active['own_helper']['owner']=='p1','own query scope contaminated')
        require(active['opponent_helper']['code']==world['opponent_helper']and active['opponent_helper']['owner']=='p2','wrong-owner factorial differs')
        victim=active['victim'];require(victim['code']=='SEC_028'and victim['owner']=='p2'and victim['hp']==7 and victim['power']==5 and victim['damage']==world['victim_damage'],'physical surviving victim differs')
        require(not(set(rows[victim['code']]['card']['aspects'])&{'command','cunning'}),'victim contaminates owner condition')
        witness=case['fixtureAttachmentWitness'];require(witness is not None,'missing fixture attachment witness')
        public_query=witness['publicTargetQuery'];validate_capture(public_query,case['refs'])
        require(public_query['decision']=='UpgradeTarget'and witness['host']==victim['id']and witness['offeredHost']in actions_for(public_query,victim['id']),'victim upgrade legality witness differs')
        item=objects[victim['id']];upgrades=item['card'].get('upgrades',[])
        require(len(upgrades)==1 and upgrades[0]['setCode']=='ASH_066'and objects[upgrades[0]['id']]['parent']==victim['id']and upgrades[0]['id']==witness['upgrade'],'HP7 victim lacks physical+3/+3 upgrade')
        for name in('own_helper','opponent_helper'):
            p=active[name];require(p['hp']==4 and p['power']==2 and p['damage']==0,'helper printed/current profile differs')
    elif world['cohort']=='attachment-parent-binding':
        require(len(own_arena)==2 and case['fixtureAttachmentWitness']is None,'binding world must have only two own hosts/no initial attachment')
        for name in('host_a','host_b'):
            p=active[name];require((p['code'],p['owner'],p['hp'],p['power'],p['damage'])==('SEC_028','p1',4,2,world['host_damage']),'identical hosts differ')
        require(active['host_a']['id']!=active['host_b']['id'],'binding aliases collapse actual instances')
    else:raise ValueError('unexpected cohort')
    # Every public physical unit must survive, so dormant defeat/draw hooks never
    # fire. A successful damage call is not a settled-survival witness by itself.
    original_units={identity:o for identity,o in objects.items()if o['zone']in('ground','space')}
    for capture in [before,*[s['after']for s in case['steps']]]:
        current=physical(capture)
        for identity,old in original_units.items():
            require(identity in current and current[identity]['zone']==old['zone'],'unreviewed helper/target death or zone movement')
            p=next((p for p in capture['projections'].values()if p is not None and p['id']==identity),None)
            require(p is not None and p['known']['hp']and p['known']['damage']and p['hp']-p['damage']>0,'unobserved or dead physical unit')
        for ref in('own_helper','opponent_helper'):
            p=before['projections'].get(ref)
            if p is not None:
                z=capture['projections'][ref]
                require(all(z[f]==p[f]for f in NUMERIC),'dormant helper attacked/changed')


def validate_catalog(plan):
    require(plan['schema']=='public-input-binding-plan/1'and len(plan['worlds'])==16 and plan['expected_cases']==16,'frozen16-root plan')
    for item in plan['source_pins']:require(sha(item['path'])==item['sha256'],'original protected catalogue/source changed')
    rows=plan['selected_whole_rows']
    require(set(rows)==set(plan['selected_whole_cards']),'full selected row bank differs')
    for code,row in rows.items():require(digest(row)==plan['selected_row_hashes'][code],'selected full row mutated')
    catalog_pin=next(p for p in plan['source_pins']if Path(p['path']).name=='cards.json')
    catalog=read(catalog_pin['path']);original={r['setCode']:r for r in catalog['cards']}
    require(all(original[c]==row for c,row in rows.items()),'catalogue row mutation')
    source_codes={c['code']for c in plan['cards']};require(source_codes=={'LAW_045','LOF_215'},'unreviewed source programs')
    for c in plan['cards']:require(c['raw_card']==rows[c['code']]and digest(c['raw_card'])==c['raw_row_sha256'],'source full card differs')
    require(rows['SEC_028']['card']['hp']==4 and rows['ASH_066']['card']['upgradeHp']==3,'pinned physical victim calculation differs')
    require(not(set(rows['LAW_045']['card']['aspects'])&{'command','cunning'}),'source supplies its own condition')
    for code in('ASH_056','SEC_094'):
        c=rows[code]['card'];require(c['cost']==2 and c['hp']==4 and c['power']==2 and c['unique']is True,'matched helper profile differs')
    require('command'not in rows['ASH_056']['card']['aspects']and 'cunning'not in rows['ASH_056']['card']['aspects']and 'command'in rows['SEC_094']['card']['aspects'],'condition source metadata differs')
    generated=Path(catalog_pin['path']).parent;manifest=read(generated/'manifest.json')
    shards={key:read(generated/manifest['files'][key])for key in('cards','inputs','diagnostics')}
    require(all(shard['compilerHash']==manifest['compilerHash']for shard in shards.values()),'catalogue compiler shard hashes differ')
    diagnostics={r['setCode']:r['diagnostics']for r in shards['diagnostics']['cards']}
    assembled=dict(schema='swu-card-ir/v1',**{k:manifest[k]for k in('compilerVersion','typescriptVersion','sourceTreeHash','compilerHash','sourceSupport','inventory')},inputs=shards['inputs']['inputs'],cards=[{**r,'diagnostics':diagnostics.get(r['setCode'],[])}for r in shards['cards']['cards']])
    subset={**assembled,'cards':[r for r in assembled['cards']if r['setCode']in rows]}
    subset_hash=hashlib.sha256(json.dumps(subset,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return rows,subset_hash


def label_records(case,world,rows):
    before,after=validate_case(case,rows);validate_world(case,world,rows)
    context=legacy_context(before,rows);program=source_program_hash(rows[case['card']]);intent=case['declared_intent']['id']
    intended=legacy_candidate(before['projections'][case['declared_intent']['ref']],before['projections']['source']['id'],rows)
    records=[];anchors={}
    a,z=before['projections']['source'],after['projections']['source'];source_values=dict(play_available=True,play_committed=z['zone']!='hand',cost_resource=ready(before)-ready(after),source_in_arena=z['in_arena'],source_in_discard=z['zone']=='discard',source_in_hand_after=z['zone']=='hand')
    for name,field in(('source_damage_delta','damage'),('source_shield_delta','shield_count'),('source_exhausted_after','exhausted')):
        known=z['in_arena']and a['known'][field]and z['known'][field]
        source_values[name]=dict(known=bool(known),value=float(z[field])-(float(a[field])if name.endswith('_delta')else 0.)if known else None)
    for head,value in source_values.items():
        known,value=(value['known'],value['value'])if isinstance(value,dict)else(True,float(value))
        records.append(dict(case=world['id'],ref='intended',kind='source-head-intended-only',head=head,input_sha256=legacy_hash(program,context,intended),known=known,value=value))
    for ref in case['observation_refs']:
        p=before['projections'][ref];candidate=legacy_candidate(p,before['projections']['source']['id'],rows);labels=observed_deltas(before,after,ref)
        require(all(v['known']for v in labels.values()),'designated numeric native endpoints unknown; qualification blocked')
        repaired=corrected_public_features(before,rows,intent,p['id'])
        anchor=dict(legacy34=candidate.tolist(),legacy_branch_hash=legacy_hash(program,context,candidate),legacy_source_hash=legacy_hash(program,context,intended),corrected_public_hash=digest(dict(program=program,features=repaired)),native=labels)
        anchors[ref]=anchor
        for head,value in labels.items():records.append(dict(case=world['id'],ref=ref,kind='expanded-branch'if world['cohort']=='attachment-parent-binding'else'conditional-chosen-branch',head=head,input_sha256=anchor['legacy_branch_hash'],**value))
    return dict(world_id=world['id'],card=case['card'],program_hash=program,legacy_context18=context.tolist(),intended_legacy34=intended.tolist(),source_native=source_values,anchors=anchors),records


def compare_predictions(predictions,case,record,rows):
    require(set(predictions)=={'bound','legacy-omission','same-info-unbound','wrong-owner'},'all predeclared controls required')
    heads=('target_allowed','target_removed',*DELTA_HEADS);output={}
    for control,prediction in predictions.items():
        require(prediction['control']==control and set(prediction['observations'])==set(case['observation_refs']),'prediction control/observation pairing differs')
        projector=prediction['projector'];require(projector is not None,'before projector unavailable')
        require(digest(projector['program'])==digest(semantic_document(rows[case['card']])),'canonical original program differs')
        require(np.array_equal(np.asarray(projector['legacy_context18'],np.float32),np.asarray(record['legacy_context18'],np.float32)),'independent18 feature mismatch')
        require(set(projector['anchors'])==set(record['anchors']),'projector anchors differ')
        result={h:dict(known=0,unknown=0,absolute_errors=[],signed_truth=[],signed_prediction=[])for h in heads}
        for ref,anchor in record['anchors'].items():
            projected=projector['anchors'][ref]
            require(np.array_equal(np.asarray(projected['legacy34'],np.float32),np.asarray(anchor['legacy34'],np.float32)),'independent34 feature mismatch')
            # Match the owner's JSON-hash encoding independently as well as our
            # byte-exact original float32 contract hash. Both encode same values.
            expected_branch=digest(dict(program=projector['program'],globals=record['legacy_context18'],candidate=anchor['legacy34']))
            expected_source=digest(dict(program=projector['program'],globals=record['legacy_context18'],intended_candidate=record['intended_legacy34']))
            require(projected['legacy_branch_hash']==expected_branch and projected['legacy_source_hash']==expected_source,'legacy JSON input hash mismatch')
            feature=projected['features'];p=case['before']['projections'][ref];intent=case['declared_intent']['id']
            require(feature['relations']['candidate_is_intended_host_or_target']==(p['id']==intent)and feature['relations']['candidate_is_source']==(p['id']==case['refs']['source']),'pre-action relation witness differs')
            require(feature['anchor_traits']==sorted(rows[p['code']]['card']['traits'])and feature['anchor_aspects']==sorted(rows[p['code']]['card']['aspects']),'public before anchor metadata differs')
            require(projected['repaired_hash']==digest(dict(program=projector['program'],features=feature)),'repaired mechanical hash differs')
            counts={seat:{aspect:sum(aspect in rows[u['setCode']]['card']['aspects']for zone in('ground','space')for u in case['before']['state']['players'][seat][zone])for aspect in ASPECTS}for seat in('p1','p2')}
            require(feature['own_arena_aspect_counts']==counts['p1']and feature['opponent_arena_aspect_counts']==counts['p2'],'owner-scoped public count mismatch')
            observation=prediction['observations'][ref];values=observation['values'];mask=observation['mask']
            require(len(values)==len(mask)==7 and all(type(m)is int and m in(0,1)for m in mask)and np.isfinite(values).all(),'prediction ABI/finite/mask')
            require(mask[0]==0,'offered membership must not be predicted from native oracle')
            for h,head in enumerate(heads):
                native=dict(known=False,value=None)if h==0 else dict(known=True,value=0.)if h==1 else anchor['native'][head]
                if not native['known']:continue
                if not mask[h]:result[head]['unknown']+=1;continue
                r=result[head];r['known']+=1;r['absolute_errors'].append(abs(float(values[h])-native['value']));r['signed_truth'].append(native['value']);r['signed_prediction'].append(float(values[h]))
        if control=='bound':require(prediction['status']=='known'and all(result[h]['unknown']==0 and not any(result[h]['absolute_errors'])for h in heads[1:]),'bound exact native endpoint gate failed')
        if control=='legacy-omission':require(prediction['status']=='unknown'and all(not any(o['mask'])for o in prediction['observations'].values()),'legacy omitted facts must stay unknown')
        output[control]=result
    return output



def verify_control_transformations(case,rows,predictions):
    """Predeclared falsification controls checked from BEFORE facts, not labels."""
    before=case['before'];units={seat:[u for zone in('ground','space')for u in before['state']['players'][seat][zone]]for seat in('p1','p2')}
    conditions={seat:any(set(rows[u['setCode']]['card']['aspects'])&{'command','cunning'}for u in members)for seat,members in units.items()}
    source=rows[case['card']]['card'];intent=case['declared_intent']['ref']
    for control in('bound','wrong-owner','same-info-unbound'):
        p=predictions[control];require(p['status']=='known','falsification control must have full known coverage')
        for ref,o in p['observations'].items():
            require(o['mask']==[0,1,1,1,1,1,1],'control numeric mask changed or became unknown')
            expected=[0.]*7
            if case['cohort']=='own-aspect-condition':
                condition=conditions['p1']if control=='bound'else conditions['p2']if control=='wrong-owner'else any(conditions.values())
                expected[2]=5. if condition else 3.
            elif case['cohort']=='attachment-parent-binding':
                if control=='same-info-unbound'or ref==intent:expected[5],expected[6]=source['upgradePower'],source['upgradeHp']
            else:raise ValueError('unreviewed control cohort')
            require(o['values']==expected,'control does not implement frozen public owner/intent transformation')
    return dict(known_controls=['bound','same-info-unbound','wrong-owner'],legacy_omission_unknown=True,condition_scope=conditions,source='Pre-action public memberships/aspects and printed upgrade literals; not native outcomes.')

def paired_results(plan,records,predictions):
    byid={r['world_id']:r for r in records};result=[]
    for pair in plan['declared_pairs']:
        left,right=(byid[i]for i in pair['worlds']);rows=[]
        for ref in set(left['anchors'])&set(right['anchors']):
            a,z=left['anchors'][ref],right['anchors'][ref]
            for head in DELTA_HEADS:
                x,y=a['native'][head],z['native'][head]
                if not(x['known']and y['known']):continue
                delta=y['value']-x['value'];collision=a['legacy_branch_hash']==z['legacy_branch_hash']
                if pair['kind']=='own-public-aspect-flip'and head=='target_damage_delta':require(abs(delta)==2 and collision,'designated own-query collision absent')
                if pair['kind']=='intended-parent-swap'and head in('target_power_delta','target_hp_delta'):require(abs(delta)==(1 if head=='target_power_delta'else 3)and collision,'designated parent-binding collision absent')
                if pair['kind']=='wrong-owner-null-control':require(delta==0,'opponent helper unexpectedly changed native endpoint')
                if pair['kind']=='physical-layout-alpha-control':require(delta==0 and a['corrected_public_hash']==z['corrected_public_hash'],'layout/identity renaming changed mechanical native/witness input')
                rows.append(dict(ref=ref,head=head,left_native=x['value'],right_native=y['value'],native_delta=delta,legacy_equal_input=collision,balanced_pair_absolute_error_floor=abs(delta)/2 if collision else None))
        for control in('bound','same-info-unbound','wrong-owner'):
            a=predictions[left['world_id']][control]['observations'];z=predictions[right['world_id']][control]['observations']
            if pair['kind']in('physical-layout-alpha-control','wrong-owner-null-control')and control=='bound':
                require(a==z,'bound prediction violates owner/order null control')
        result.append(dict(kind=pair['kind'],worlds=pair['worlds'],comparisons=rows))
    return result


def verify(plan_path,raw_path,journal_path,prediction_path,predictor_source,output):
    require(not output.exists(),'preserve independent verification output')
    plan,raw,analysis=read(plan_path),read(raw_path),read(prediction_path);rows,subset_hash=validate_catalog(plan)
    require(raw['schema']=='jepa-public-input-binding-native/1'and raw['collectionPlan']==plan and raw['collectionPlanSha256']==sha(plan_path),'native full plan/schema pin')
    require(raw['sourceRevision']==plan['source_revision']and raw['candidateOrder']==plan['candidate_order']and raw['selectedWholeCards']==plan['selected_whole_cards']and raw['selectedCatalogueSha256']==subset_hash,'native source/complete catalogue differs')
    require(type(raw['applyCalls'])is int and 0<raw['applyCalls']<=plan['collector_max_engine_applies'],'apply cap')
    require(analysis['schema']=='public-input-binding-predictions/1'and analysis['source_sha256']==sha(predictor_source)and analysis['receipt_sha256']==sha(raw_path),'prediction provenance differs')
    require(analysis['semantic_validated']is False and analysis['neural_forwards']==analysis['native_applies']==analysis['optimizer_updates']==0,'invalid experiment scope')
    protected=[plan_path,raw_path,journal_path,prediction_path,predictor_source]
    journal=validate_journal([json.loads(l)for l in journal_path.read_text().splitlines()if l.strip()],raw)
    cases={c['world_id']:c for c in raw['cases']};pred={c['world_id']:c['predictions']for c in analysis['cases']}
    require(len(raw['cases'])==len(cases)==len(analysis['cases'])==len(pred)==16 and set(cases)==set(pred)==set(range(16)),'all fixed fresh roots exactly once')
    records=[];labels=[];control_rows={};future_parent=[];control_transformations=[]
    for world in plan['worlds']:
        case=cases[world['id']];require(case['cohort']==world['cohort']and case['applyCalls']<=plan['max_applies_per_case'],'world/case/cap mismatch')
        record,local_labels=label_records(case,world,rows);records.append(record);labels.extend(local_labels)
        control_rows[world['id']]=compare_predictions(pred[world['id']],case,record,rows)
        control_transformations.append(dict(world_id=world['id'],**verify_control_transformations(case,rows,pred[world['id']])))
        future_parent.append(dict(world_id=world['id'],declared_intent=case['declared_intent'],after_parent=case['final_source_parent'],source_parent_is_input=False))
    controls={}
    for control in('bound','legacy-omission','same-info-unbound','wrong-owner'):
        controls[control]={}
        for cohort in('own-aspect-condition','attachment-parent-binding'):
            controls[control][cohort]={}
            for head in('target_removed',*DELTA_HEADS):
                group=[control_rows[w['id']][control][head]for w in plan['worlds']if w['cohort']==cohort];errors=[v for row in group for v in row['absolute_errors']];truth=[v for row in group for v in row['signed_truth']];prediction=[v for row in group for v in row['signed_prediction']]
                controls[control][cohort][head]=dict(known=sum(r['known']for r in group),unknown=sum(r['unknown']for r in group),mae=float(np.mean(errors))if errors else None,max_error=max(errors)if errors else None,exact=sum(e==0 for e in errors),positive_truth=sum(v>0 for v in truth),negative_truth=sum(v<0 for v in truth),zero_truth=sum(v==0 for v in truth),signed_accuracy=float(np.mean(np.sign(prediction)==np.sign(truth)))if errors else None)
    require(controls['wrong-owner']['own-aspect-condition']['target_damage_delta']['known']==8 and controls['wrong-owner']['own-aspect-condition']['target_damage_delta']['exact']==4,'wrong-owner must disagree on4of8 fresh damage endpoints')
    require(controls['same-info-unbound']['own-aspect-condition']['target_damage_delta']['exact']==6,'union-owner must disagree on2of8 fresh damage endpoints')
    for head in('target_power_delta','target_hp_delta'):
        require(controls['same-info-unbound']['attachment-parent-binding'][head]['known']==16 and controls['same-info-unbound']['attachment-parent-binding'][head]['exact']==8,'unbound parent must disagree on8of16 fresh anchors')
        require(controls['wrong-owner']['attachment-parent-binding'][head]['exact']==16,'wrong-owner control must preserve correct attachment binding')
    source_audit=check_predictor_source(predictor_source,('scene_before','project_case','predict_case','expr','targets','effect'))
    report=dict(schema='public-input-binding-independent-verification/1',status='PASS',source=pin(__file__),inputs=[pin(p)for p in protected],catalogue_unmodified=True,native_journal=journal,records=records,head_input_records=labels,legacy_collisions=collision_records(labels),causal_pairs=paired_results(plan,records,pred),controls=controls,control_transformations=control_transformations,after_only_parent_proof=future_parent,predictor_source_audit=source_audit,
        mechanic_primary=dict(damage=dict(cohort='own-aspect-condition',coordinates=8),power=dict(cohort='attachment-parent-binding',coordinates=16),hp=dict(cohort='attachment-parent-binding',coordinates=16)),
        counts=dict(roots=len(records),observation_anchors=sum(len(r['anchors'])for r in records),bound_numeric_coordinates=sum(v['known']for r in records for a in r['anchors'].values()for v in a['native'].values()),bound_removed_coordinates=sum(len(r['anchors'])for r in records)),fresh_native=True,preinspected_IR=True,neural_forwards=0,native_applies=0,numerical_fits=0,semantic_validated=False,
        limitations=['No source is used as TRAIN; fresh native outcomes follow prior inspection of both source programs, not blind universal interpretation.','Legacy collision is same-card original18/34 architecture/input-contract sufficiency, not old checkpoint inference or a new embedding-row lookup.','Attachment branch is an expanded actual-action transition observing selected and unselected hosts; old chosen-only masks are not retroactively wrong.','Source-head intended-only input/label records are separate from branch/observation-anchor records.','Balanced-pair absolute-error floors are |observed label difference|/2 for identical input; no fitted estimator or generalization of fixed-fallback errors.','Only numeric surviving endpoints qualified; keyword grant/attack/defeat/hidden/draw behavior is not validated.','Native order control swaps host creation/registration order and IDs with logical roles preserved; the distinct pure synthetic alpha test renames every fixture reference.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x')as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('plan','receipt','journal','predictions','predictor-source','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=verify(a.plan,a.receipt,a.journal,a.predictions,a.predictor_source,a.out)
    print(json.dumps(dict(path=str(a.out),sha256=sha(a.out),status=result['status'])))


if __name__=='__main__':main()
