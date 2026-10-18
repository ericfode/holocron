"""Saved native semantic observations to arrays; no engine/model invocation.

Only native offered actions and actual paid/settled endpoints supply labels.
Pending/unoffered/declined futures and counters after departure stay unknown.
"""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import binding_transfer_data_v2 as B
import semantic_discrimination_plan as P

E,G,M,V=B.E,B.G,B.M,B.V
SOURCE_HEADS=B.SOURCE_HEADS
TARGET_HEADS=B.TARGET_HEADS
SOURCE_BINARY=B.SOURCE_BINARY
TARGET_BINARY=B.TARGET_BINARY
ROLES=P.ROLES
DELTAS=B.DELTAS
require=P.require
pin=P.pin
read=B.read


def validate_capture(capture,refs,rows):return B.validate_capture(capture,refs,rows)
def public_before_record(case):return B.public_before_record(case)


def validate_setup(case,world,plan,rows):
    b=case['before'];refs=case['refs']
    require(validate_capture(b,refs,rows)and b['decision']=='Window'and case['publicSnapshotRoundtripExact']is True,'clean public initial snapshot required')
    for key in('card','cohort','partition','state_family','template_id','scenario','selection_mode','observation_mode'):
        require(case[key]==world['source_code'if key=='card'else key],'frozen root field differs: '+key)
    intent=case['declared_intent'];require(intent==dict(ref=world['intent_ref'],id=refs[world['intent_ref']],requires_target=True),'declared pre-action intent differs')
    require(case['observation_refs']==list(ROLES)==world['observation_refs']and not case['fixtureAttachmentWitnesses'],'all eight roles and no initial attachments required')
    source=b['projections']['source'];require((source['code'],source['owner'],source['zone'])==(case['card'],'p1','hand'),'own fresh source required')
    require(V.ready(b)==world['ready_resources']==12 and len(b['state']['players']['p1']['resources'])==12,'fixed public funding differs')
    require(b['projections']['own_base']['damage']==world['own_base_damage']and b['projections']['opponent_base']['damage']==world['opponent_base_damage'],'base damage grid differs')
    for role,spec in world['arena_cards'].items():
        p=b['projections'][role];require(p['code']==spec['code']and p['owner']==spec['owner']and p['damage']==spec['damage']and p['exhausted']is spec['exhausted']and p['in_arena']and p['hp']>p['damage'],'actual public arena fixture differs: '+role)
    visible={p['id']for p in b['projections'].values()if p is not None and p['in_arena']}
    arena={u['id']for seat in('p1','p2')for zone in('ground','space')for u in b['state']['players'][seat][zone]}
    require(visible==arena and len(arena)==5,'every initial arena instance must be represented once')
    return b


def journal_proof(journal,receipt):
    if isinstance(journal,(str,Path)):journal=[json.loads(s)for s in Path(journal).read_text().splitlines()if s.strip()]
    require(journal and journal[0]['schema']=='jepa-semantic-discrimination-apply-journal/1','native durable journal header required')
    require(all(journal[0][a]==receipt[b]for a,b in(('planSha256','collectionPlanSha256'),('sourceRevision','sourceRevision'),('selectedWholeCards','selectedWholeCards'))),'native journal provenance differs')
    starts={};ends={};complete={}
    for row in journal[1:]:
        phase=row['phase']
        if phase=='beforeApply':
            n=row['applyCall'];require(n==len(starts)+1,'native application sequence differs');starts[n]=row
        elif phase in('afterApply','applyError'):
            n=row['applyCall'];require(n in starts and n not in ends and all(row[k]==starts[n][k]for k in('context','branch')),'application boundary differs');ends[n]=row
        elif phase=='contextComplete':require(row['context']not in complete,'duplicate native root');complete[row['context']]=row['case']
        else:raise ValueError('unreviewed native journal event')
    require(set(starts)==set(ends)and len(starts)==receipt['applyCalls']and len(complete)==len(receipt['cases']),'incomplete native journal')
    for case in receipt['cases']:
        context=f"world-{case['world_id']}-{case['card']}";require(complete.get(context)==case,'native root boundary differs')
        calls=[n for n,a in starts.items()if a['context']==context];require(len(calls)==case['applyCalls']==len(case['steps'])+int(case['engineError']is not None),'native root count differs')
        for n,step in zip(calls,case['steps']):
            a,z=starts[n],ends[n];require(a['before']==step['before']and a['offeredAction']==step['action']and a['branch']==step['stage']and z['phase']=='afterApply'and z['after']==step['after'],'native step evidence differs')
    return dict(apply_calls=len(starts),completed_roots=len(complete),errors=sum(z['phase']=='applyError'for z in ends.values()))


def derive_labels(case,world,plan,rows):
    b=validate_setup(case,world,plan,rows);refs=case['refs'];intent=case['declared_intent'];q=ROLES.index(intent['ref'])
    sy=np.zeros(9,np.float32);sm=np.zeros(9,np.float32);ty=np.zeros((8,7),np.float32);tm=np.zeros_like(ty);chosen=np.zeros_like(ty)
    offers=V.actions_for(b,refs['source']);sy[0],sm[0]=bool(offers),1
    require((case['playAction']is None)==(not offers)and(case['playAction']is None or case['playAction']in offers),'source offeredness/action mismatch')
    last=b;captures=[b];selected=[];done=[];declined=[]
    for i,step in enumerate(case['steps']):
        require(step['before']==last and step['action']in last['offeredActions'],'unoffered/discontinuous native step')
        validate_capture(step['after'],refs,rows);stage=step['stage'];action=step['action']
        if i==0:require(stage=='play-own-hand'and action==case['playAction'],'initial action is not source play')
        elif stage=='chosen-target':
            require(last==case['targetPrompt']and last['decision']=='AbilityTarget'and action==case['targetAction']and action in V.actions_for(last,intent['id']),'chosen target lacks actual offered commitment');selected.append(step)
        elif stage=='commit-one-selection':
            require(world['selection_mode']=='exactly-one-upTo'and len(selected)==1 and last==case['selectionWitness']and action==case['selectionDoneAction']and action.get('arg')=='done'and action.get('label')=='Done'and last['abilitySelection']==[intent['id']],'exactly-one selection/Done proof differs')
            require(last['abilityProgramPlusOne']==case['targetPrompt']['abilityProgramPlusOne']and last['abilityPc']==case['targetPrompt']['abilityPc'],'selection continues different native program');done.append(step)
        elif stage=='decline-unoffered-target':
            require(last==case['targetPrompt']and not V.actions_for(last,intent['id'])and action==case['declineAction']and action.get('arg')=='cancel'and action.get('label')=='Cancel','native Cancel proof differs');declined.append(step)
        elif stage=='accept-optional-trigger':require(last['decision']=='AbilityOptional'and action.get('arg')=='trigger','optional acceptance differs')
        elif stage=='use-no-effect-anyway':require(last['decision']=='AbilityNoEffect'and action.get('arg')==0,'native no-effect acceptance differs')
        elif stage=='sole-trigger-order':require(last['decision']=='TriggerOrder'and len(last['offeredActions'])==1,'ambiguous trigger order')
        else:raise ValueError('unreviewed native stage')
        last=step['after'];captures.append(last)
    require(case['lastObserved']==last and len(selected)<=1 and len(done)<=1 and len(declined)<=1,'native last/selection counts differ')
    prompt=case['targetPrompt']
    if prompt is not None:
        require(prompt in captures and prompt['decision']=='AbilityTarget','target membership must come from reached native prompt')
        validate_capture(prompt,refs,rows)
        for j,role in enumerate(ROLES):ty[j,0],tm[j,0]=bool(V.actions_for(prompt,refs[role])),1
        require(case['intentOffered']is bool(V.actions_for(prompt,intent['id'])),'intent offered witness differs')
    else:require(case['intentOffered']is None,'no-prompt offeredness must stay unknown')
    committed=bool(selected)and(world['selection_mode']!='exactly-one-upTo'or bool(done))
    require(case['intendedTargetCommitted']is committed,'committed selection witness differs')
    terminal=case['terminalClassification'];final=case['final'];block=[];paid=False
    if terminal=='unoffered-prompt-only':
        require(prompt==last and final is None and case['engineError']is None and case['completion']==case['intentResolution']=='unoffered-observation-only'and not V.actions_for(prompt,intent['id'])and not any(a.get('arg')=='cancel'and a.get('label')=='Cancel'for a in prompt['offeredActions'])and not selected and not declined,'observation-only terminal lacks absent-Cancel proof')
    elif terminal in('settled-committed','settled-cancelled'):
        require(final==last and case['completion']=='settled'and case['engineError']is None and validate_capture(final,refs,rows),'actual settled endpoint required')
        require((terminal=='settled-committed')==committed and(terminal=='settled-cancelled')==bool(declined),'terminal commitment classification differs')
        require(case['intentResolution']==('committed'if committed else'unoffered-declined'),'terminal intent resolution differs')
        a,z=b['projections']['source'],final['projections']['source'];cost=V.ready(b)-V.ready(final);require(cost>=0,'unreviewed resource gain')
        physical_commit=z['present']and z['zone']in('ground','space','discard','upgrade')
        sy[1:]=[physical_commit,cost,z['in_arena'],z['zone']=='discard',z['zone']=='hand',z['damage']-a['damage'],z['shield_count']-a['shield_count'],z['exhausted']];sm[1:6]=1
        for h,f in((6,'damage'),(7,'shield_count'),(8,'exhausted')):sm[h]=bool(z['in_arena']and a['known'][f]and z['known'][f])
        paid=bool(physical_commit and cost>0)
        if committed:
            require(paid,'committed effect has no actual paid source')
            for j,role in enumerate(ROLES):
                a,z=b['projections'][role],final['projections'][role];require(a['id']==z['id'],'physical observation identity changed')
                removed=not z['present']or z['zone']in('discard','absent');ty[j,1],tm[j,1]=removed,1
                same=not removed and a['present']and z['present']and a['zone']==z['zone']and((a['in_arena']and z['in_arena'])or(a['is_base']and z['is_base']))
                for h,f in enumerate(DELTAS,2):
                    if same and a['known'][f]and z['known'][f]:ty[j,h],tm[j,h]=float(z[f])-float(a[f]),1
            chosen[q]=tm[q]
    else:block.append('unreviewed-native-terminal')
    if case['engineError']is not None:block.append('native-engine-error')
    if not offers:block.append('planned-source-play-unavailable')
    if prompt is None:block.append('planned-native-target-prompt-unavailable')
    # No action was applied to an illegal intended target. Cancellation and
    # observation-only roots never acquire hypothetical after/effect labels.
    return dict(source=sy,source_mask=sm,targets=ty,target_mask=tm,chosen_only_target_mask=chosen,selected=q,
        fit_blockers=block,committed=committed,paid=paid,terminal=terminal)


def primary_mask(arrays,manifest):
    mask=np.zeros_like(arrays['target_mask'])
    for i,code in enumerate(arrays['source_cards'].astype(str)):
        for name in manifest['plan']['primary_spec']['masks'].get(code,[]):
            h=TARGET_HEADS.index(name)
            for role in('anchor_a','anchor_b'):
                j=ROLES.index(role);mask[i,j,h]=arrays['target_mask'][i,j,h]
    return mask


def admission(arrays,manifest,rawx,rawc):
    plan=manifest['plan'];reports=[];passed=True
    scaledx,scaledc=M.project_arrays(arrays,manifest,scalers=manifest['common_input_scalers'])
    for p in plan['primary_pairs']:
        i,k=p['left_root'],p['right_root'];a,b=ROLES.index(p['anchor_a']),ROLES.index(p['anchor_b']);h=TARGET_HEADS.index(p['head'])
        same=np.array_equal(rawx[i],rawx[k])and np.array_equal(rawc[i,1:],rawc[k,1:])
        scaled_same=np.array_equal(scaledx[i],scaledx[k])and np.array_equal(scaledc[i,1:],scaledc[k,1:]);known=bool(arrays['target_mask'][[i,k]][:,[a,b],h].all())
        d=float((arrays['targets'][i,a,h]-arrays['targets'][i,b,h])-(arrays['targets'][k,a,h]-arrays['targets'][k,b,h]))if known else None
        ok=same and scaled_same and known and d==p['expected_D'];passed&=ok
        reports.append(dict(id=p['id'],left_root=i,right_root=k,public_X32_and_non_source_C43_identical=same,common_TRAIN_scaled_inputs_identical=scaled_same,coobserved=known,native_D=d,expected_D=p['expected_D'],passed=ok))
    train=plan['split']['root_partitions']['train'];byhead={}
    for head in('target_allowed','target_damage_delta','target_removed'):
        h=TARGET_HEADS.index(head);bytemplate={}
        for template in sorted({manifest['template_ids'][i]for i in train}):
            ix=[i for i in train if manifest['template_ids'][i]==template];y=arrays['targets'][ix,1:,h];m=arrays['target_mask'][ix,1:,h]>0;y=y[m]
            bytemplate[template]=dict(known=len(y),zero=int((y==0).sum()),positive=int((y>0).sum()),negative=int((y<0).sum()))
        eligible=[t for t,v in bytemplate.items()if v['zero']and v['positive']]
        byhead[head]=dict(by_template=bytemplate,positive_and_zero_templates=eligible,passed=len(eligible)>=2)
    healing=[]
    for i in train:
        if arrays['source_cards'][i]!='LAW_133':continue
        h=TARGET_HEADS.index('target_damage_delta');j=ROLES.index('own_base');known=bool(arrays['target_mask'][i,j,h]);value=float(arrays['targets'][i,j,h])if known else None
        healing.append(dict(root=int(i),known=known,native_delta=value))
    heal_values=sorted({p['native_delta']for p in healing if p['known']});healok=heal_values==[-3.,-1.]
    rank=[]
    for p in plan['primary_spec']['rank_pairs']:
        ix=[p['left_root'],p['right_root']];js=[ROLES.index(r)for r in p['anchors']];h=TARGET_HEADS.index(p['head']);known=bool(arrays['target_mask'][ix][:,js,h].all())
        committed=all(manifest['native_status'][i]['committed']for i in ix);values=[float(p['utility_sign']*arrays['targets'][i,js,h].sum())for i in ix]if known and committed else None
        rank.append(dict(id=p['id'],supported=values is not None and values[0]!=values[1],native_utilities=values,scope='One nested magnitude pair; not strategic value or independent semantic qualification.'))
    return dict(primary_eligibility_pairs=reports,TRAIN_heads=byhead,healing_train_observations=healing,healing_values=heal_values,
        rank_pairs=rank,passed=bool(passed and all(v['passed']for v in byhead.values())and healok),semantic_validated=False,
        healing_scope='LAW133 main/capped auxiliary are one positive healing template, not independent templates.')


def convert_receipt(receipt,plan,assembled,journal):
    require(receipt['schema']=='jepa-semantic-discrimination-native/1'and receipt['collectionPlan']==plan and receipt['sourceRevision']==plan['source_revision'],'native schema/plan/source differs')
    require(receipt['candidateOrder']==list(ROLES)and receipt['selectedWholeCards']==plan['selected_whole_cards']and receipt['selectedCatalogueSha256']==G.native_catalog_hash(assembled,plan['selected_whole_cards']),'selected native catalogue differs')
    rows=plan['selected_whole_rows'];original={r['setCode']:r for r in assembled['cards']}
    for code,row in rows.items():require(P.digest(row)==plan['selected_row_hashes'][code]and all(original[code].get(k)==v for k,v in row.items()),'complete source/helper row changed')
    require(receipt['collectionComplete']is True and type(receipt['applyCalls'])is int and 0<=receipt['applyCalls']<=128,'collection incomplete or native quota differs')
    proof=journal_proof(journal,receipt);cases=sorted(receipt['cases'],key=lambda c:c['world_id']);worlds=plan['worlds']
    require(len(cases)==len(worlds)==33 and [c['world_id']for c in cases]==[w['id']for w in worlds]==list(range(33)),'exact frozen33 roots required')
    labels=[];x=[];c=[];records=[];block=[]
    for case,world in zip(cases,worlds):
        require(case['applyCalls']<=world['max_applies']<=4,'root application cap differs')
        result=derive_labels(case,world,plan,rows);labels.append(result);block.extend(f"world-{world['id']}:{s}"for s in result['fit_blockers'])
        b=case['before'];x.append(V.legacy_context(b,rows));c.append([V.legacy_candidate(b['projections'][role],case['refs']['source'],rows)for role in ROLES]);records.append(public_before_record(case))
    arrays=dict(context_features=np.asarray(x,np.float32),candidate_features=np.asarray(c,np.float32),source_targets=np.asarray([r['source']for r in labels],np.float32),source_mask=np.asarray([r['source_mask']for r in labels],np.float32),
        targets=np.asarray([r['targets']for r in labels],np.float32),target_mask=np.asarray([r['target_mask']for r in labels],np.float32),chosen_only_target_mask=np.asarray([r['chosen_only_target_mask']for r in labels],np.float32),
        selected_candidate_indices=np.asarray([r['selected']for r in labels],np.int64),source_cards=np.asarray([case['card']for case in cases]),state_families=np.asarray([case['state_family']for case in cases],np.int64),world_ids=np.arange(33,dtype=np.int64),partition=np.asarray([case['partition']for case in cases]))
    parts=plan['split']['root_partitions'];require({k:len(v)for k,v in parts.items()}==dict(train=13,state_held=12,family_held=4,joint=4)and sorted(i for v in parts.values()for i in v)==list(range(33)),'root split differs')
    for name,ix in parts.items():require(all(cases[i]['partition']==name for i in ix),'partition/world mismatch');arrays[name+'_idx']=np.asarray(ix,np.int64)
    templates=[case['template_id']for case in cases]
    manifest=dict(schema='jepa-semantic-discrimination-data/1',plan=plan,cards={c['code']:c for c in plan['cards']},codes=plan['codes'],split=plan['split'],family_ids=templates,template_ids=templates,
        candidate_order=list(ROLES),source_head_names=list(SOURCE_HEADS),source_binary_heads=list(SOURCE_BINARY),target_names=list(TARGET_HEADS),binary_heads=list(TARGET_BINARY),context_feature_names=list(B.A.CONTEXT_FEATURES),candidate_feature_names=list(B.A.CANDIDATE_FEATURES),
        public_before_records=records,public_catalog_rows=copy.deepcopy(rows),public_binding_contract=dict(schema=M.SCHEMA,task='actual-intent-endpoints',aspect_vocabulary=list(M.ASPECTS),metadata_mode='printed-static-fixture-only'),
        alias_registry=B.alias_registry(rows),native_apply_calls=receipt['applyCalls'],journal_proof=proof,native_status=[dict(committed=r['committed'],paid=r['paid'],terminal=r['terminal'])for r in labels],
        terminal_counts={s:sum(r['terminal']==s for r in labels)for s in plan['raw_abi']['terminal_classes']},errors=sum(c['engineError']is not None for c in cases),fit_blockers=block,semantic_validated=False,
        output_scope='Actual native prompt membership; paid settled committed effects only; cancelled/unoffered/pending futures unknown and dead/departed numeric counters masked.',
        public_input_scope='BEFORE allowlist only; no offered actions, after states, final parents, hidden piles or source IDs as numeric features.')
    conflicts,scalers,rawx,rawc,bank=B.input_conflicts(arrays,manifest,plan)
    arrays['projected_context_features']=rawx;arrays['projected_candidate_features']=rawc;arrays['primary_target_mask']=primary_mask(arrays,manifest)
    manifest.update(input_conflicts=conflicts,common_input_scalers=scalers,semantic_bank=bank,head_support={name:B.support(arrays,manifest,np.asarray(ix,np.int64))for name,ix in parts.items()})
    manifest['native_admission']=admission(arrays,manifest,rawx,rawc)
    if conflicts['C1R1']['conflict_count']:block.append('corrected-consumed-input-label-conflict')
    if not manifest['native_admission']['passed']:block.append('frozen-native-support-or-primary-pair-admission-failed')
    manifest['fit_admitted']=not block
    for key,value in arrays.items():
        if value.dtype.kind=='f':require(value.dtype==np.float32 and np.isfinite(value).all(),'finite float32 arrays required')
    return arrays,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('native-receipt','journal','plan','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();mp=a.out.with_suffix('.manifest.json');require(not a.out.exists()and not mp.exists(),'preserve previous outputs')
    plan,receipt=read(a.plan),read(a.native_receipt);require(receipt['collectionPlanSha256']==pin(a.plan)['sha256'],'exact plan bytes differ')
    for p in plan['source_pins']:require(pin(p['path'])==p,'frozen metadata source changed')
    arrays,manifest=convert_receipt(receipt,plan,G.assembled_catalog(G.PINNED_KESSEL/'compiler/generated'),a.journal)
    a.out.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(a.out,**arrays)
    manifest.update(artifact=pin(a.out),native_receipt=pin(a.native_receipt),journal=pin(a.journal),source_pins=[pin(p)for p in(Path(__file__),Path(B.__file__),Path(P.__file__),a.plan,a.native_receipt,a.journal)])
    with mp.open('x')as f:json.dump(manifest,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(dataset=pin(a.out),manifest=pin(mp),fit_admitted=manifest['fit_admitted'],native_applies=0,neural_forwards=0,numerical_fits=0)))


if __name__=='__main__':main()
