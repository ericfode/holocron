"""Pure saved native observations -> matched binding-transfer arrays.

No engine, Torch, forward, optimizer, ledger mutation or paid action is invoked.
Actual conversion is a separately guarded coordinator stage. Unit tests are synthetic.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import actual_corpus_native_plan as A
import effect_identifiability_fit as E
import grounded_contrast_data as G
import public_input_binding_model_v1 as M
import public_input_binding_supplemental_verify as V

HERE=Path(__file__).resolve().parent
DEFAULT=HERE.parents[3]/'experiments/binding-transfer-v1/binding-transfer.npz'
MODES={'chosen-target','attachment-parent','passive-aura'}
DELTAS=('damage','exhausted','shield_count','power','hp')
SOURCE_HEADS=A.SOURCE_HEADS
TARGET_HEADS=A.TARGET_HEADS
SOURCE_BINARY=A.SOURCE_BINARY
TARGET_BINARY=A.TARGET_BINARY
ROLES=('source','own_helper','opponent_helper','anchor_a','anchor_b','auxiliary','own_base','opponent_base')


def require(ok,message):
    if not ok:raise ValueError(message)


def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pin(path):
    p=Path(path).resolve();return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)


def validate_capture(capture,refs,rows):
    result=V.validate_capture(capture,refs)
    require(tuple(sorted(refs))==tuple(sorted(ROLES)),'fixed eight role bank required')
    active=[i for i in refs.values()if i is not None]
    require(len(active)==len(set(active)),'different roles must keep distinct physical instances')
    for p in capture['projections'].values():
        if p is None or not p['present']:continue
        require(p['code']in rows,'public row missing')
        card=rows[p['code']]['card']
        for name in('aspects','traits','types','keywords'):
            require(p['printed_'+name]==card[name]and p['known']['printed_'+name]is True,'static printed public metadata mismatch')
    return result


def public_before_record(case):
    """Allowlist only fields actually used by the public C/R projector.

    Raw fixture/journal snapshots retain original evidence externally. Private
    piles, resource identities, after/parent, menus and continuation fields never
    enter this learner record. IDs only resolve public equality and completeness.
    """
    b=case['before'];projections={}
    for role,p in b['projections'].items():
        if p is None:projections[role]=None;continue
        projections[role]={k:copy.deepcopy(p[k])for k in('id','code','owner','zone','is_unit','is_base','present','printed_aspects')}
        projections[role]['known']={k:copy.deepcopy(p['known'][k])for k in('identity','owner','printed_aspects')}
    before=dict(projections=projections,state=dict(players={seat:{zone:[dict(id=u['id'])for u in b['state']['players'][seat][zone]]for zone in('ground','space')}for seat in('p1','p2')}))
    return dict(before=before,refs=copy.deepcopy(case['refs']),declared_intent=copy.deepcopy(case['declared_intent']),observation_refs=copy.deepcopy(case['observation_refs']))


def validate_journal(journal,receipt):
    if isinstance(journal,(str,Path)):journal=[json.loads(l)for l in Path(journal).read_text().splitlines()if l.strip()]
    require(journal and journal[0]['schema']=='jepa-binding-transfer-apply-journal/1','durable native journal required')
    require(journal[0]['planSha256']==receipt['collectionPlanSha256']and journal[0]['sourceRevision']==receipt['sourceRevision']and journal[0]['selectedWholeCards']==receipt['selectedWholeCards'],'journal native provenance differs')
    intents={};ends={};complete={}
    for row in journal[1:]:
        event=row['phase']
        if event=='beforeApply':
            n=row['applyCall'];require(n==len(intents)+1,'native journal sequence differs');intents[n]=row
        elif event in('afterApply','applyError'):
            n=row['applyCall'];require(n in intents and n not in ends and all(row[k]==intents[n][k]for k in('context','branch')),'native outcome/intent differs');ends[n]=row
        elif event=='contextComplete':
            require(row['context']not in complete,'duplicate completed native root');complete[row['context']]=row['case']
        else:raise ValueError('unreviewed native journal event')
    require(set(intents)==set(ends)and len(intents)==receipt['applyCalls'],'native durable count differs')
    require(len(complete)==len(receipt['cases']),'root boundary count differs')
    for case in receipt['cases']:
        key=f"world-{case['world_id']}-{case['card']}";require(complete.get(key)==case,'completed raw root differs')
        calls=[n for n,row in intents.items()if row['context']==key];error=case['engineError']is not None
        require(len(calls)==case['applyCalls']==len(case['steps'])+int(error),'per-root apply count differs')
        for n,step in zip(calls,case['steps']):
            a,z=intents[n],ends[n]
            require(a['before']==step['before']and a['offeredAction']==step['action']and a['branch']==step['stage']and z['phase']=='afterApply'and z['after']==step['after'],'native action chain differs')
        if error:
            a,z=intents[calls[-1]],ends[calls[-1]];last=case['steps'][-1]['after']if case['steps']else case['before']
            require(z['phase']=='applyError'and a['before']==last and a['offeredAction']in last['offeredActions'],'native error lacks durable attempted action')
    return dict(apply_calls=len(intents),completed_roots=len(complete),errors=sum(v['phase']=='applyError'for v in ends.values()))


def validate_setup(case,world,plan,rows):
    before,refs=case['before'],case['refs'];require(validate_capture(before,refs,rows)and before['decision']=='Window'and case['publicSnapshotRoundtripExact']is True,'root must be clean/settled/roundtrip exact')
    require(case['card']==world['source_code']and case['partition']==world['partition']and case['state_family']==world['state_family']and case['template_id']==world['template_id']and case['cohort']==world['cohort'],'frozen root/split/template differs')
    intent=case['declared_intent'];require(set(intent)=={'ref','id','requires_target'}and type(intent['requires_target'])is bool,'explicit pre-action intent ABI')
    require(intent['ref']==world['intent_ref']and intent['id']==refs[intent['ref']]and intent['requires_target']==world['requires_target']and case['observation_mode']==world['observation_mode']and case['observation_refs']==world['observation_refs'],'predeclared roles differ')
    require(case['observation_mode']in MODES and intent['requires_target']==(case['observation_mode']!='passive-aura'),'passive aura cannot invent a target')
    source=before['projections']['source'];require((source['code'],source['owner'],source['zone'])==(case['card'],'p1','hand'),'exact own known-hand source required')
    require(V.ready(before)==world['ready_resources']and len(before['state']['players']['p1']['resources'])==12,'funding differs')
    objects=V.physical(before);witnesses=case['fixtureAttachmentWitnesses'];links={(i,o['parent']):o for i,o in objects.items()if o['zone']=='upgrade'}
    require(len(witnesses)==(2 if world['cohort']=='own-aspect-condition'else 0),'fixture attachment witness count differs')
    require(len(links)==len(witnesses),'unwitnessed initial attachment')
    for w in witnesses:
        q=w['publicTargetQuery'];validate_capture(q,refs,rows)
        require(q['decision']=='UpgradeTarget'and q['sourceInstance']==w['upgrade']and w['offeredHost']in V.actions_for(q,w['host'])and (w['upgrade'],w['host'])in links and links[w['upgrade'],w['host']]['card']['setCode']==w['code'],'actual lawful fixture attachment differs')
    pa,pb=(before['projections'][r]for r in('anchor_a','anchor_b'))
    if world['cohort']=='own-aspect-condition':
        require(before['projections']['own_helper']['code']==world['own_helper']and before['projections']['opponent_helper']['code']==world['opponent_helper'],'public condition-helper grid differs')
        require(world['victim_damage']==(2 if world['partition']=='train'else 3)and world['partition']in('train','state_held'),'LAW TRAINdamage2/STATEdamage3 contract differs')
        require((pa['code'],pa['owner'],pa['hp'],pa['damage'])==(plan['helpers']['victim'],'p2',10,world['victim_damage']),'new HP10/planned-damage LAW world required')
        require({w['code']for w in witnesses}==set(plan['helpers']['victim_upgrades'])and all(w['host']==pa['id']for w in witnesses),'two physical LAW upgrades differ')
    else:
        require(pa['damage']==pb['damage']==world['anchor_damage'],'anchor damage world differs')
        if world['cohort']=='simultaneous-damage':require(pa['code']==pb['code']==plan['helpers']['damage_space']and pa['owner']==pb['owner']=='p2'and pa['zone']==pb['zone']=='space','actual enemy-space anchors differ')
        elif world['cohort']=='friendly-space-aura':require(pa['code']==pb['code']==plan['helpers']['aura_space']and pa['zone']==pb['zone']=='space'and before['projections'][world['own_anchor']]['owner']=='p1'and {pa['owner'],pb['owner']}=={'p1','p2'},'owner-indexed passive aura anchors differ')
        elif world['cohort']=='attachment-parent-binding':require(pa['code']==pb['code']==plan['helpers']['host']and pa['owner']==pb['owner']=='p1'and pa['zone']==pb['zone']=='ground','identical own attachment hosts differ')
        else:raise ValueError('unexpected cohort')
    return before


def derive_labels(case,world,plan,rows):
    b=validate_setup(case,world,plan,rows);refs=case['refs'];j=plan['candidate_order'].index(case['declared_intent']['ref'])
    sy=np.zeros(9,np.float32);sm=np.zeros(9,np.float32);ty=np.zeros((8,7),np.float32);tm=np.zeros((8,7),np.float32);chosen=np.zeros((8,7),np.float32)
    offers=V.actions_for(b,refs['source']);sy[0],sm[0]=bool(offers),1
    play=case['playAction'];require((play is None)==(not offers)and(play is None or play in offers),'source play binding differs')
    last=b;commits=[];captures=[b]
    for index,step in enumerate(case['steps']):
        require(step['before']==last and step['action']in last['offeredActions'],'discontinuous/unoffered native step')
        validate_capture(step['after'],refs,rows);captures.append(step['after'])
        stage=step['stage']
        if index==0:require(stage=='play-own-hand'and step['action']==play,'first action is not actual own-source play')
        elif stage in('chosen-target','attach-intended-host'):
            expected='UpgradeTarget'if stage=='attach-intended-host'else'AbilityTarget'
            require(case['observation_mode']==('attachment-parent'if stage=='attach-intended-host'else'chosen-target')and case['declared_intent']['requires_target']and last==case['targetPrompt']and last['decision']==expected and step['action']==case['targetAction']and step['action']in V.actions_for(last,case['declared_intent']['id']),'actual target/parent commitment differs');commits.append(step)
        elif stage=='decline-unoffered-target':require(not V.actions_for(last,case['declared_intent']['id'])and(step['action'].get('arg')in('cancel','passAbility')or step['action'].get('label')=='Cancel'),'decline substituted an available target')
        elif stage=='accept-optional-trigger':require(last['decision']=='AbilityOptional'and step['action'].get('arg')=='trigger','optional trigger differs')
        elif stage=='use-no-effect-anyway':require(last['decision']=='AbilityNoEffect'and step['action'].get('arg')==0,'no-effect menu differs')
        elif stage=='sole-trigger-order':require(last['decision']=='TriggerOrder'and len(last['offeredActions'])==1,'trigger order ambiguous')
        else:raise ValueError('unreviewed action stage')
        last=step['after']
    require(case['lastObserved']==last and len(commits)<=1,'last observed endpoint differs')
    prompt=case['targetPrompt']
    if prompt is not None:
        validate_capture(prompt,refs,rows);require(prompt in captures and prompt['decision']in('AbilityTarget','UpgradeTarget')and case['declared_intent']['requires_target'],'unreached or passive fictional prompt')
        for k,role in enumerate(plan['candidate_order']):
            if refs[role]is not None:ty[k,0],tm[k,0]=bool(V.actions_for(prompt,refs[role])),1
    final=case['final'];paid=False;observed=False
    if final is not None:
        require(final==last and case['engineError']is None and case['completion']=='settled'and validate_capture(final,refs,rows),'future must be actual settled last endpoint')
        a,z=b['projections']['source'],final['projections']['source'];objects=V.physical(final);physical=objects.get(refs['source'])
        if physical is not None and physical['zone']=='upgrade':require(physical['parent']==case['final_source_parent'],'final physical parent witness differs')
        committed=bool(z['present']and(z['in_arena']or z['zone']=='discard'or z['zone']=='upgrade'and physical is not None))
        cost=V.ready(b)-V.ready(final);require(cost>=0,'unreviewed resource gain')
        sy[1:]=[committed,cost,z['in_arena'],z['zone']=='discard',z['zone']=='hand',z['damage']-a['damage'],z['shield_count']-a['shield_count'],z['exhausted']];sm[1:6]=1
        for h,field in((6,'damage'),(7,'shield_count'),(8,'exhausted')):sm[h]=bool(z['in_arena']and a['known'][field]and z['known'][field])
        paid=bool(committed and cost>0)
        observed=paid and(bool(commits)if case['declared_intent']['requires_target']else True)
        if case['observation_mode']=='attachment-parent'and observed:require(physical is not None and physical['zone']=='upgrade'and physical['parent']==case['declared_intent']['id']and z['code']==case['card'],'successful paid attachment lacks actual intended parent')
        if case['observation_mode']=='passive-aura':require(not commits and prompt is None and case['targetAction']is None,'aura acquired fictional target')
        if observed:
            for role in case['observation_refs']:
                k=plan['candidate_order'].index(role);a,z=b['projections'][role],final['projections'][role]
                require(a is not None and z is not None and a['id']==z['id'],'stable public observation anchor required')
                removed=not z['present']or z['zone']in('discard','absent');ty[k,1],tm[k,1]=removed,1
                same=not removed and a['present']and z['present']and a['in_arena']and z['in_arena']and a['zone']==z['zone']
                for h,field in enumerate(DELTAS,2):
                    if same and a['known'][field]and z['known'][field]:ty[k,h],tm[k,h]=float(z[field])-float(a[field]),1
            if commits:chosen[j]=tm[j]
    if case['declared_intent']['requires_target']and case['targetAction']is not None:require(prompt is not None and case['targetAction']in V.actions_for(prompt,case['declared_intent']['id']),'attempted target not actually offered')
    require(case['intendedTargetCommitted']==(case['targetAction']is not None),'attempt bookkeeping differs; successful steps remain the future proof')
    if not offers:require(not case['steps']and final is None and case['engineError']is None,'unavailable play has future observations')
    # Preserve unobserved numeric values under mask0 without letting source-entry
    # lifecycle facts become target effects or hypothetical unchosen effects.
    blocked=[]
    if case['engineError']is not None:blocked.append('native-engine-error')
    if final is None and play is not None and case['engineError']is None:blocked.append('pending-native-outcome')
    if not offers:blocked.append('planned-play-unavailable')
    if not observed:blocked.append('planned-paid-committed-observation-unavailable')
    elif any(not tm[plan['candidate_order'].index(role),1:].all()for role in case['observation_refs']):blocked.append('planned-numeric-anchor-observation-unknown')
    # This planned cohort excludes deaths/attacks/keyword-trigger paths. Native
    # counter support remains explicit even when a numerical field is unknown.
    original={i:o for i,o in V.physical(b).items()if o['zone']in('ground','space')}
    for c in captures:
        current=V.physical(c)
        for identity,o in original.items():
            if identity not in current or current[identity]['zone']!=o['zone']or current[identity]['card']['hp']-current[identity]['card']['damage']<=0:blocked.append('unreviewed-public-unit-death-or-zone-movement')
        for role in('own_helper','opponent_helper'):
            a,z=b['projections'][role],c['projections'][role]
            if a is not None:require(all(a[f]==z[f]for f in('damage','hp','power','exhausted','shield_count','xp_count')),'dormant helper changed/attacked')
    return dict(source=sy,source_mask=sm,targets=ty,target_mask=tm,chosen_only_target_mask=chosen,selected=j,fit_blockers=blocked,paid=paid,observed=observed)


def support(arrays,manifest,indices):
    result={}
    for names,key,mk in((SOURCE_HEADS,'source_targets','source_mask'),(TARGET_HEADS,'targets','target_mask')):
        for h,name in enumerate(names):
            y=arrays[key][indices,...,h];m=arrays[mk][indices,...,h]>0;v=y[m]
            roots=lambda which:int(np.count_nonzero(which if which.ndim==1 else which.any(-1)))
            result[name]=dict(known=int(m.sum()),observed_roots=roots(m),positive=int(((y>0)&m).sum()),negative=int(((y<0)&m).sum()),zero=int(((y==0)&m).sum()),positive_roots=roots((y>0)&m),negative_roots=roots((y<0)&m),zero_roots=roots((y==0)&m),values=np.unique(v).astype(float).tolist())
    return result


def support_gate(arrays,manifest,train):
    report={}
    for mechanic,names in dict(damage=('target_damage_delta',),stats=('target_power_delta','target_hp_delta')).items():
        heads={}
        for name in names:
            h=TARGET_HEADS.index(name);by_template={}
            for template in sorted({manifest['template_ids'][i]for i in train}):
                ix=[i for i in train if manifest['template_ids'][i]==template];v=arrays['targets'][ix,:,h][arrays['target_mask'][ix,:,h]>0]
                by_template[template]=dict(known=len(v),zero=int((v==0).sum()),positive=int((v>0).sum()),negative=int((v<0).sum()))
            eligible=[t for t,v in by_template.items()if v['zero']and v['positive']]
            heads[name]=dict(by_template=by_template,independent_positive_and_zero_templates=eligible,passed=len(eligible)>=2 and sum(v['zero']for v in by_template.values())>=2 and sum(v['positive']for v in by_template.values())>=2)
        report[mechanic]=dict(heads=heads,passed=all(v['passed']for v in heads.values()))
    return dict(mechanics=report,passed=all(v['passed']for v in report.values()),sign_scope='Positive stat changes and observed zeros only; negative-stat and keyword qualification unsupported. ASH228 exhaustion is one-template auxiliary.')


def quantity_support(plan,arrays=None):
    """Audit frozen public literals separately from independently measured labels.

    This is an admission check, never a source of native target values. No
    quantity, cohort, mask or split is adjusted after seeing native outcomes.
    """
    expected=dict(training_positive_power=[1,2],training_positive_hp=[1,3],held_positive_power=[2],held_positive_hp=[2,3])
    require(all(plan['numeric_support_prelabel'].get(k)==v for k,v in expected.items()),'frozen positive quantity declaration differs')
    source={}
    for entry in plan['cards']:
        row=entry['raw_card'];card=row['card'];amounts=None;origin=None
        if 'upgrade'in card['types']:
            amounts={name:card['upgrade'+name.capitalize()]for name in('power','hp')};origin='printed physical-parent upgrade bonuses'
        else:
            effects=[a['effect']for abilities in row['abilities'].values()for a in abilities if a.get('trigger')=='constant'and a.get('effect',{}).get('kind')=='modifyStats']
            if effects:
                require(len(effects)==1 and all(effects[0][n].get('kind')=='const'for n in('power','hp')),'unreviewed nonliteral/multiple stat source')
                amounts={n:effects[0][n]['value']for n in('power','hp')};origin='constant typed modifyStats literals'
        if amounts is not None:
            require(all(type(v)in(int,float)and np.isfinite(v)and v>0 for v in amounts.values()),'positive finite source stat literals required')
            source[entry['code']]=dict(amounts=amounts,origin=origin,raw_row_sha256=G.digest(row))
    groups={name:sorted({source[w['source_code']]['amounts'][stat]for w in plan['worlds']if w['source_code']in source and (w['partition']=='train'if name.startswith('training_')else w['partition']in('family_held','joint'))})for name,stat in((name,'power'if name.endswith('power')else'hp')for name in expected)}
    require(groups==expected,'source-literal TRAIN/held quantity sets differ')
    in_range={stat:all(min(groups['training_positive_'+stat])<=v<=max(groups['training_positive_'+stat])for v in groups['held_positive_'+stat])for stat in('power','hp')}
    require(all(in_range.values()),'held positive stat literal outside TRAIN range')
    result=dict(expected=expected,source_literals=source,source_positive_sets=groups,held_within_TRAIN_range=in_range,native_observed=None,passed=True,
        scope='Public source-literal and native-support admission only; HP2 is interpolation within TRAIN1/3, HP3/P2 are TRAIN-seen. Labels remain native-measured; no adaptation or semantic qualification.')
    if arrays is None:return result
    parts=plan['split']['root_partitions'];indices=dict(training=parts['train'],held=[*parts['family_held'],*parts['joint']]);actual={};per_root=[];mismatches=[]
    for group,ix in indices.items():
        for stat,h in(('power',5),('hp',6)):
            values=arrays['targets'][ix,:,h][arrays['target_mask'][ix,:,h]>0];actual[group+'_positive_'+stat]=sorted({float(v)for v in values if v>0})
    for w in plan['worlds']:
        if w['source_code']not in source:continue
        for role in w['observation_refs']:
            j=plan['candidate_order'].index(role);affected=role==(w['own_anchor']if w['observation_mode']=='passive-aura'else w['intent_ref'])
            for stat,h in(('power',5),('hp',6)):
                known=bool(arrays['target_mask'][w['id'],j,h]);value=float(arrays['targets'][w['id'],j,h])if known else None
                wanted=float(source[w['source_code']]['amounts'][stat])if affected else 0.
                record=dict(world=w['id'],code=w['source_code'],partition=w['partition'],role=role,stat=stat,source_expected=wanted,native_known=known,native_actual=value,passed=known and value==wanted)
                per_root.append(record)
                if not record['passed']:mismatches.append(record)
    result.update(native_observed=dict(positive_sets=actual,per_anchor=per_root,mismatches=mismatches),passed=actual==expected and not mismatches)
    return result


def input_conflicts(arrays,manifest,plan):
    docs=[E.canonical_document(c['raw_card'])[0]for c in plan['cards']];codes=[c['code']for c in plan['cards']];symbols=E.symbols_for(docs)
    bank,_=E.make_bank(docs,codes,plan['train_codes'],symbols,False);signatures=dict(zip(codes,E.tensor_signatures(bank)))
    rawx,rawc=M.project_arrays(arrays,manifest);expanded=dict(arrays,context_features=rawx,candidate_features=rawc)
    train=np.asarray(plan['split']['root_partitions']['train'],np.int64);scalers=E.common_scalers(expanded,manifest,train);report={}
    visible=[signatures[str(c)]for c in arrays['source_cards']]
    for arm in M.ARMS:
        x,c=M.project_arrays(arrays,manifest,arm,scalers=scalers);keys=M.consumed_input_hashes(x,c,visible,arrays['selected_candidate_indices']);seen={};conflicts=[]
        for kind,key,mk,names in(('source','source_targets','source_mask',SOURCE_HEADS),('candidate','targets','target_mask',TARGET_HEADS)):
            for i in range(len(x)):
                values=arrays[key][i:i+1]if kind=='source'else arrays[key][i];known=arrays[mk][i:i+1]if kind=='source'else arrays[mk][i]
                for j in range(len(values)):
                    signature=keys[i]['source']if kind=='source'else keys[i]['candidate'][j]
                    for h,name in enumerate(names):
                        if not known[j,h]:continue
                        signature_key=(kind,signature,name);value=float(values[j,h]);old=seen.get(signature_key)
                        if old is not None and old[0]!=value:conflicts.append(dict(kind=kind,head=name,input_sha256=signature,old_root=old[1],root=i,old_candidate=old[2],candidate=None if kind=='source'else j,old_value=old[0],value=value))
                        else:seen[signature_key]=(value,i,None if kind=='source'else j)
        report[arm]=dict(conflict_count=len(conflicts),conflicts=conflicts,consumed_signatures=keys,expected_may_conflict=arm!='C1R1')
    return report,scalers,rawx,rawc,dict(program_tensor_signatures=signatures,public_held_syntax_allocated=True)


def alias_registry(rows):
    """Provenance-only repair of frozen 7e0af843's required-setCodes lookup.

    The constructor-support TOKEN_SHIELD row supplies setId, not setCodes.
    Preserve that raw value and explicit missingness; never derive an alias
    from it. This helper does not supply labels, features, masks or admission.
    """
    result={}
    for code,row in rows.items():
        card=row['card'];present='setCodes'in card
        result[code]=dict(canonical_id=str(card['id']),
            set_codes=copy.deepcopy(card['setCodes'])if present else None,
            set_codes_present=present,set_codes_known=present and isinstance(card['setCodes'],list),
            raw_set_id=copy.deepcopy(card.get('setId')),raw_set_id_present='setId'in card,
            scope='Provenance only; IDs never numerical features or conflict keys.')
    return result


def convert_receipt(receipt,plan,assembled,journal):
    quantity_support(plan)  # Frozen source-only eligibility before raw labels.
    require(receipt['schema']=='jepa-binding-transfer-native/1'and receipt['sourceRevision']==plan['source_revision']and receipt['collectionPlan']==plan,'native schema/source/full plan differs')
    require(tuple(plan['candidate_order'])==ROLES and receipt['candidateOrder']==list(ROLES)and receipt['selectedWholeCards']==plan['selected_whole_cards'],'candidate/whole-card ABI differs')
    require(receipt['selectedCatalogueSha256']==G.native_catalog_hash(assembled,plan['selected_whole_cards']),'assembled selected catalogue differs')
    rows=plan['selected_whole_rows'];original={r['setCode']:r for r in assembled['cards']}
    for code,row in rows.items():require(G.digest(row)==plan['selected_row_hashes'][code]and all(original[code].get(k)==v for k,v in row.items()),'full original source/helper row changed')
    require(type(receipt['applyCalls'])is int and 0<=receipt['applyCalls']<=plan['collector_max_engine_applies'],'native apply cap differs')
    journal_proof=validate_journal(journal,receipt);cases=sorted(receipt['cases'],key=lambda c:c['world_id']);worlds=plan['worlds']
    require(len(cases)==len(worlds)==26 and [c['world_id']for c in cases]==list(range(26))and [w['id']for w in worlds]==list(range(26)),'all frozen26 roots required exactly once')
    require(receipt.get('collectionComplete')is True,'native collection incomplete')
    require(len(plan['cards'])==7 and len(plan['train_codes'])==5 and len(plan['heldout_codes'])==2,'final seven-source/fiveTRAIN/twoheld cohort required')
    cards={c['code']:c for c in plan['cards']};legacyx=[];legacyc=[];labels=[];records=[];blockers=[]
    for case,world in zip(cases,worlds):
        require(case['applyCalls']<=(1 if world['observation_mode']=='passive-aura'else 2),'per-root native cap differs; aura is hard1')
        result=derive_labels(case,world,plan,rows);labels.append(result);blockers.extend(f"world-{world['id']}:{v}"for v in result['fit_blockers'])
        b=case['before'];legacyx.append(V.legacy_context(b,rows));legacyc.append([V.legacy_candidate(b['projections'][role],case['refs']['source'],rows)if b['projections'][role]is not None else np.zeros(34,np.float32)for role in ROLES]);records.append(public_before_record(case))
    arrays=dict(context_features=np.asarray(legacyx,np.float32),candidate_features=np.asarray(legacyc,np.float32),source_targets=np.asarray([r['source']for r in labels],np.float32),source_mask=np.asarray([r['source_mask']for r in labels],np.float32),targets=np.asarray([r['targets']for r in labels],np.float32),target_mask=np.asarray([r['target_mask']for r in labels],np.float32),chosen_only_target_mask=np.asarray([r['chosen_only_target_mask']for r in labels],np.float32),selected_candidate_indices=np.asarray([r['selected']for r in labels],np.int64),source_cards=np.asarray([c['card']for c in cases]),state_families=np.asarray([c['state_family']for c in cases],np.int64),world_ids=np.arange(26,dtype=np.int64),partition=np.asarray([c['partition']for c in cases]),observation_modes=np.asarray([c['observation_mode']for c in cases]))
    partitions=plan['split']['root_partitions'];require({k:len(v)for k,v in partitions.items()}==dict(train=12,state_held=6,family_held=4,joint=4),'fixed split sizes differ')
    require(sorted(i for v in partitions.values()for i in v)==list(range(26)),'root partitions do not cover exactly once')
    for name,ix in partitions.items():require(all(cases[i]['partition']==name for i in ix),'split aliases/root indices differ');arrays[name+'_idx']=np.asarray(ix,np.int64)
    family_ids=[c['template_id']for c in cases]
    aliases=alias_registry(rows)
    manifest=dict(schema='jepa-binding-transfer-data/1',status='native-data-converted',plan=plan,cards=cards,codes=plan['codes'],split=plan['split'],candidate_order=list(ROLES),context_feature_names=list(A.CONTEXT_FEATURES),candidate_feature_names=list(A.CANDIDATE_FEATURES),source_head_names=list(SOURCE_HEADS),source_binary_heads=list(SOURCE_BINARY),target_names=list(TARGET_HEADS),binary_heads=list(TARGET_BINARY),family_ids=family_ids,template_ids=family_ids,public_before_records=records,public_catalog_rows=copy.deepcopy(rows),public_binding_contract=dict(schema=M.SCHEMA,task='actual-intent-endpoints',aspect_vocabulary=list(M.ASPECTS),metadata_mode='printed-static-fixture-only'),alias_registry=aliases,native_apply_calls=receipt['applyCalls'],journal_proof=journal_proof,errors=sum(c['engineError']is not None for c in cases),pending=sum(c['playAction']is not None and c['final']is None and c['engineError']is None for c in cases),fit_blockers=blockers,source_revision=plan['source_revision'],semantic_validated=False)
    conflicts,scalers,rawx,rawc,bank=input_conflicts(arrays,manifest,plan);arrays['projected_context_features']=rawx;arrays['projected_candidate_features']=rawc
    manifest.update(input_conflicts=conflicts,common_input_scalers=scalers,semantic_bank=bank,projected_context_feature_names=[*A.CONTEXT_FEATURES,*M.CONTEXT_EXTENSION],projected_candidate_feature_names=[*A.CANDIDATE_FEATURES,*M.CANDIDATE_CONTENT,*M.CANDIDATE_RELATION])
    if conflicts['C1R1']['conflict_count']:blockers.append('C1R1-coobserved-input-label-conflict')
    for i,case in enumerate(cases):
        if case['observation_mode']=='passive-aura':require(not rawc[i,:,41:].any(),'passive aura R must be N/A in every candidate')
    groups={**{name:np.asarray(ix,np.int64)for name,ix in partitions.items()},**{code:np.flatnonzero(arrays['source_cards']==code)for code in cards}}
    manifest['head_support']={name:support(arrays,manifest,ix)for name,ix in groups.items()};manifest['template_support_gate']=support_gate(arrays,manifest,partitions['train'])
    if not manifest['template_support_gate']['passed']:blockers.append('two-positive-TRAIN-templates-and-zero-support-not-met')
    manifest['quantity_support_gate']=quantity_support(plan,arrays)
    if not manifest['quantity_support_gate']['passed']:blockers.append('predeclared-source-and-native-positive-quantity-support-differs')
    stat=arrays['targets'][...,5:7][arrays['target_mask'][...,5:7]>0]
    if np.any(stat<0):blockers.append('unexpected-negative-stat-in-positive-only-cohort')
    if receipt['applyCalls']!=plan['expected_engine_applies']:blockers.append('planned-native-apply-count-not-met')
    manifest.update(fit_admitted=not blockers,public_before_scope='Allowlisted source/public-arena identity/owner/aspect/type/presence and raw arena public IDs only; no private zones, resource identities, offered actions, after-state or parent links.',chosen_only_scope='Same actual-action predictions, successful intended-target observations only. Passive aura has no chosen target and zero chosen-only target masks; this is not old conditional checkpoint replay.',actual_endpoint_scope='Two actual predeclared public surviving endpoint anchors after paid settled play; missing/dead/declined/pending futures unknown, never counterfactual zero fill.',stat_qualification='Positive parent/aura stat changes and observed zeros only; held HP2 interpolates TRAIN1/3, while HP3/P2 are TRAIN-seen. Unscored keyword/negative-state limits remain.',novelty=dict(previous12_source_benchmark='Consumed; never fresh validation.',previous16_LAW_Cable_diagnostic='Consumed; LAW HP10/damage2-3 fresh states differ from previous HP7/damage0/1.',held_programs='New complete variants in familiar parent-stat family, not new-family generalization.'),scope='Pure native-receipt conversion and TRAIN-only audit transforms. No engine/model/optimizer/ridge invocation.')
    for key,value in arrays.items():
        if value.dtype.kind=='f':require(value.dtype==np.float32 and np.isfinite(value).all(),'finite float32 numeric arrays required')
    return arrays,manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-receipt',type=Path,required=True);p.add_argument('--journal',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,default=DEFAULT);a=p.parse_args();mp=a.out.with_suffix('.manifest.json')
    require(not a.out.exists()and not mp.exists(),'preserve previous dataset and manifest')
    plan,receipt=read(a.plan),read(a.native_receipt);require(receipt['collectionPlanSha256']==sha(a.plan),'exact native plan bytes differ')
    for item in plan['source_pins']:require(sha(item['path'])==item['sha256'],'protected source/catalogue differs')
    arrays,manifest=convert_receipt(receipt,plan,G.assembled_catalog(G.PINNED_KESSEL/'compiler/generated'),a.journal)
    a.out.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(a.out,**arrays)
    files=[Path(__file__),HERE/'test_binding_transfer_data.py',HERE/'public_input_binding_model_v1.py',HERE/'public_input_binding_supplemental_verify.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',HERE/'actual_corpus_native_plan.py',HERE/'grounded_contrast_data.py',HERE/'binding_transfer_native_plan.py',HERE/'binding_transfer_native_collector/src/main.rs',a.plan,a.native_receipt,a.journal]
    manifest.update(artifact=pin(a.out),native_receipt=pin(a.native_receipt),journal=pin(a.journal),source_pins=[pin(f)for f in files]);mp.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(path=str(a.out),sha256=sha(a.out),manifest=pin(mp),fit_admitted=manifest['fit_admitted'],native_applies=0,neural_forwards=0,numerical_fits=0)))


if __name__=='__main__':main()
