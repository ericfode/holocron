"""Guarded fresh-state native-data adapter; no fitting or neural operations.

Reuse frozen per-case native label derivation, never the predecessor's hardcoded
33-root converter or any TRAIN-statistic fitting function. Old transforms and
programs remain exact. Actual conversion requires a sealed-spec root GO.
"""
import os
for _key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import argparse
import copy
import hashlib
import importlib
from importlib import util
import json
from pathlib import Path
import sys
import ability_correction as C

HERE=Path(__file__).resolve().parent
FROZEN_DATA_SHA='b78efb37eba223fa7e93989f6e06fabac6dd21c7b9251c70f43917d6e542ae18'
CONFIG=dict(rows=8,neural_forwards=0,optimizer_updates=0,native_applies=0,numerical_fits=0,seconds=3.,cpu_workers=1,rss_bytes=1073741824,semantic_validated=False,
    policy='Exact frozen per-case native labels; original TRAIN-only transforms. Prompt-only futures remain unknown. Full-row and actual head-local input novelty reported separately.')


def native_guard():
    path=HERE/'ability_correction_native_collector/supervise.py';spec=util.spec_from_file_location('ability_correction_saved_native_proof',path);module=util.module_from_spec(spec);spec.loader.exec_module(module);return module


def frozen_data():
    D=importlib.import_module('semantic_discrimination_data')
    C.require(Path(D.__file__).resolve()==HERE/'semantic_discrimination_data.py'and C.pin(D.__file__)['sha256']==FROZEN_DATA_SHA,'frozen per-case label implementation changed')
    return D


def journal_proof(path,raw):
    """Exact new header and paired actions; no predecessor schema substitution."""
    records=[json.loads(line)for line in Path(path).read_text().splitlines()if line.strip()];C.require(records,'native journal missing')
    header=records[0];C.require(header.get('schema')=='jepa-ability-correction-apply-journal/1'and header.get('maxApplyCalls')==32,'new8/32 native journal header differs')
    C.require(all(header.get(a)==raw[b]for a,b in(('planSha256','collectionPlanSha256'),('sourceRevision','sourceRevision'),('selectedWholeCards','selectedWholeCards'))),'journal provenance differs')
    before=[r for r in records[1:]if r.get('phase')=='beforeApply'];after=[r for r in records[1:]if r.get('phase')=='afterApply'];ends=[r for r in records[1:]if r.get('phase')=='contextComplete']
    C.require(all(r.get('phase')in('beforeApply','afterApply','contextComplete')for r in records[1:]),'unreviewed native event/error')
    C.require([r['applyCall']for r in before]==list(range(1,raw['applyCalls']+1))and[r['applyCall']for r in after]==list(range(1,raw['applyCalls']+1)),'native calls not fully paired')
    C.require([(r['phase'],r['applyCall'])for r in records[1:]if r['phase']!='contextComplete']==[(phase,i)for i in range(1,raw['applyCalls']+1)for phase in('beforeApply','afterApply')],'native chronological before/after pairs differ')
    C.require([r['case']['world_id']for r in ends]==list(range(8))and[r['case']for r in ends]==raw['cases'],'all8 exact native root completions required')
    return dict(native_apply_calls=len(before),completed_roots=8,schema=header['schema'],chronological_pairs=True)


def novelty(x,c,oldx,oldc,oldcodes,old_semantic_signature,selected,old_selected):
    """Compare actual public features; a new full panel need not refresh a head."""
    import numpy as np
    M=importlib.import_module('public_input_binding_model_v1');oldrows=[int(i)for i,v in enumerate(oldcodes)if str(v)=='IBH_104'];C.require(oldrows,'original IBH observations required')
    fresh_signatures=[old_semantic_signature]*len(x);prior_signatures=[old_semantic_signature]*len(oldx);output={}
    for name,fc,oc in(('original',c,oldc),('R_neutral',c.copy(),oldc.copy())):
        if name=='R_neutral':fc[...,41:43]=0;oc[...,41:43]=0
        new=M.consumed_input_hashes(x,fc,fresh_signatures,selected);old=M.consumed_input_hashes(oldx,oc,prior_signatures,old_selected);old_sources={old[i]['source']for i in oldrows};old_candidates={value for i in oldrows for value in old[i]['candidate']}
        records=[]
        for i,row in enumerate(new):
            full=[j for j in oldrows if np.array_equal(x[i],oldx[j])and np.array_equal(fc[i],oc[j])]
            records.append(dict(root=i,full_panel_equal_old_rows=full,source_consumed_input_seen=row['source']in old_sources,candidate_consumed_input_seen=[v in old_candidates for v in row['candidate']]))
        output[name]=dict(rows=records,full_panel_new_roots=sum(not r['full_panel_equal_old_rows']for r in records),source_new_roots=sum(not r['source_consumed_input_seen']for r in records),scope='Fixed same IBH program. Candidate hash uses only actual x32+ownc43+semantic signature; no siblings, intent labels or masks conceal a repeat.')
    output.update(old_IBH_rows=oldrows,fresh_state_worlds=4,scope='Eight intent rows nested in four fresh states, not eight independent programs or families.')
    return output


def convert(raw,plan,native_manifest,journal,old,old_native,old_arrays,old_manifest):
    import numpy as np
    D=frozen_data();M=D.M
    C.require(plan['schema']=='jepa-ability-correction-plan/1'and raw['schema']=='jepa-ability-correction-native/1'and raw['collectionPlan']==plan and raw['sourceRevision']==plan['source_revision'],'exact new8 source/plan/schema required')
    C.require(raw['candidateOrder']==list(D.ROLES)==plan['candidate_order']and raw['selectedWholeCards']==plan['selected_whole_cards'],'frozen role/card ABI differs')
    C.require(raw['collectionComplete']is True and type(raw['applyCalls'])is int and 0<raw['applyCalls']<=32,'complete bounded native collection required')
    proof=journal_proof(journal,raw);proof['full_native_proof']=native_guard().verify_native(raw,native_manifest,journal)
    rows=plan['selected_whole_rows'];source=next(r for r in plan['cards']if r['code']=='IBH_104');previous=next(r for r in old_native['cards']if r['code']=='IBH_104')
    C.require(source['raw_card']==previous['raw_card']and D.P.digest(source['raw_card'])==source['raw_row_sha256'],'exact exposed whole source row required')
    document,_=D.E.canonical_document(source['raw_card']);C.require(document==old['documents'][7],'source IR/printed model document changed')
    assembled=D.G.assembled_catalog(D.G.PINNED_KESSEL/'compiler/generated');C.require(raw['selectedCatalogueSha256']==D.G.native_catalog_hash(assembled,plan['selected_whole_cards']),'actual selected native catalogue differs')
    original={r['setCode']:r for r in assembled['cards']}
    for code,row in rows.items():C.require(D.P.digest(row)==plan['selected_row_hashes'][code]and all(original[code].get(k)==v for k,v in row.items()),'complete native source/helper row differs')
    cases=raw['cases'];worlds=plan['worlds'];C.require(len(cases)==len(worlds)==8 and [c['world_id']for c in cases]==[w['id']for w in worlds]==list(range(8)),'exact ordered8 worlds required')
    labels=[];xs=[];cs=[];records=[];blockers=[]
    for case,world in zip(cases,worlds):
        # derive_labels itself calls the frozen validate_setup and validates
        # every capture/action/commit before assigning observed labels/masks.
        label=D.derive_labels(case,world,plan,rows);labels.append(label);blockers.extend(f"world-{world['id']}:{b}"for b in label['fit_blockers']);before=case['before'];xs.append(D.V.legacy_context(before,rows));cs.append([D.V.legacy_candidate(before['projections'][role],case['refs']['source'],rows)for role in D.ROLES]);records.append(D.public_before_record(case))
    arrays=dict(context_features=np.asarray(xs,np.float32),candidate_features=np.asarray(cs,np.float32),source_targets=np.asarray([r['source']for r in labels],np.float32),source_mask=np.asarray([r['source_mask']for r in labels],np.float32),targets=np.asarray([r['targets']for r in labels],np.float32),target_mask=np.asarray([r['target_mask']for r in labels],np.float32),chosen_only_target_mask=np.asarray([r['chosen_only_target_mask']for r in labels],np.float32),selected_candidate_indices=np.asarray([r['selected']for r in labels],np.int64),source_cards=np.asarray([c['card']for c in cases]),state_families=np.asarray([c['state_family']for c in cases],np.int64),world_ids=np.arange(8,dtype=np.int64))
    manifest=dict(schema='jepa-ability-correction-data/1',plan=plan,candidate_order=list(D.ROLES),source_head_names=list(D.SOURCE_HEADS),source_binary_heads=list(D.SOURCE_BINARY),target_names=list(D.TARGET_HEADS),binary_heads=list(D.TARGET_BINARY),context_feature_names=list(D.B.A.CONTEXT_FEATURES),candidate_feature_names=list(D.B.A.CANDIDATE_FEATURES),public_before_records=records,public_catalog_rows=copy.deepcopy(rows),public_binding_contract=dict(schema=M.SCHEMA,task='actual-intent-endpoints',aspect_vocabulary=list(M.ASPECTS),metadata_mode='printed-static-fixture-only'),intent_pairs=copy.deepcopy(plan['intent_pairs']),errors=sum(c['engineError']is not None for c in cases),pending=sum(r['terminal']not in('settled-committed','settled-cancelled','unoffered-prompt-only')for r in labels),prompt_only_unknown_futures=sum(r['terminal']=='unoffered-prompt-only'for r in labels),native_status=[dict(committed=r['committed'],paid=r['paid'],terminal=r['terminal'])for r in labels],fit_blockers=blockers,native_apply_calls=raw['applyCalls'],journal_proof=proof,source_program_previously_exposed=True,source_program_transfer_claim=False,semantic_validated=False)
    x,c=M.project_arrays(arrays,manifest,'C1R1',old['scalers']);anchors=C.validate(arrays,manifest,old,x,c);oldx,oldc=M.project_arrays(old_arrays,old_manifest,'C1R1',old['scalers'])
    manifest['input_novelty']=novelty(x,c,oldx,oldc,old_arrays['source_cards'],old['semantic_signatures']['full'][7],arrays['selected_candidate_indices'],old_arrays['selected_candidate_indices'])
    C.require(manifest['input_novelty']['original']['full_panel_new_roots']==8,'fresh full normalized panels repeat old IBH rows; no correction execution')
    arrays.update(projected_context_features=x,projected_candidate_features=c);mask=np.zeros_like(arrays['target_mask']);mask[:,anchors,0]=arrays['target_mask'][:,anchors,0];arrays['primary_target_mask']=mask
    manifest.update(old_transforms=copy.deepcopy(old['scalers']),transform_policy='Exact original TRAIN transforms; no new scaler/support/class-weight fitting',label_policy='Only actual native observations. Prompt-only/cancelled futures and departed physical counters remain unknown.',frozen_data_source=C.pin(D.__file__))
    return arrays,manifest


def worker(args):
    import numpy as np
    E=importlib.import_module('effect_identifiability_fit');old=C.read(args.old_plan);E.verify_pins(old['pins']);C.require(old['status']=='sealed-awaiting-root-GO','original sealed plan required')
    old_native_pin=old['native_plan'];C.require(C.pin(old_native_pin['path'])==old_native_pin,'original native plan pin changed')
    native_manifest=C.read(args.native_manifest);C.require(native_manifest['collection_plan']==C.pin(args.native_plan),'native manifest must bind exact declared newplan path/bytes')
    arrays,manifest=convert(C.read(args.native_receipt),C.read(args.native_plan),native_manifest,args.journal,old,C.read(old_native_pin['path']),C.load_npz(np,old['dataset']),C.read(old['manifest']))
    data=args.out/'dataset.npz';mp=args.out/'dataset.manifest.json';np.savez_compressed(data,**arrays);manifest.update(dataset=C.pin(data),old_plan=C.pin(args.old_plan),native_plan=C.pin(args.native_plan),native_manifest=C.pin(args.native_manifest),native_receipt=C.pin(args.native_receipt),journal=C.pin(args.journal),source=C.pin(__file__));C.write_new(mp,manifest,np)
    return dict(dataset=C.pin(data),manifest=C.pin(mp),rows=8,neural_forwards=0,optimizer_updates=0,native_applies=0,numerical_fits=0,semantic_validated=False)


def execute(args):
    A=importlib.import_module('sealed_budget');budget=A.Budget(args.spec)
    with budget.lease()as run:
        paths=[args.old_plan,args.native_plan,args.native_manifest,args.native_receipt,args.journal];allowed=dict(budget.frozen,**run.state['proofs']);inputs=[allowed[str(p.resolve())]for p in paths if str(p.resolve())in allowed];status='failed';error=None;guard=None;created=False;result=None;receipt=args.out.parent/(args.out.name+'-stage-receipt.json')
        try:
            run.begin(args.stage,argv=[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]],guard=budget.spec['guard'],inputs=inputs)
            C.require(len(inputs)==len(paths),'all prep inputs must be frozen/completed proofs');C.require(budget.spec['stages'][args.stage]['outputs']==[str(args.out.resolve()),str(receipt.resolve())],'exact prep directory/receipt outputs required');C.require(budget.spec['guard']==dict(cpu_workers=1,rss_bytes=1073741824),'fixed audited1CPU/1GiB guard required');C.require(budget.spec['stages'][args.stage]['reservation']['seconds']==3.,'exactprep3 reservation required')
            E=importlib.import_module('effect_identifiability_fit');remaining=run.remaining_seconds();C.require(0<remaining<=3.,'prep3 wall reservation required');guard=E.Guard(remaining);args.out.mkdir(parents=True,exist_ok=False);created=True
            with guard:result=C.native(worker(args),sys.modules.get('numpy'))
            status='completed'
        except BaseException as exc:
            if run.state['pending']is None:raise
            error=dict(type=type(exc).__name__,message=str(exc))
        artifacts=[C.pin(p)for p in sorted(args.out.rglob('*'))if p.is_file()]if created else[];value=dict(status=status,error=error,result=result,source=C.pin(__file__),artifact_pins=artifacts,guard=guard.receipt()if guard else None,semantic_validated=False,authority='Shared ledger includes receipt/proof time and controls authoritative final status; failed reservation retained.')
        rp=None
        try:C.write_new(receipt,value);rp=C.pin(receipt)
        except BaseException as exc:status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        finished=run.finish(status,proofs=artifacts+([rp]if rp else[]),cleanup_verified=True,execution_ended=True);C.require(status=='completed'and args.stage in finished['completed'],'bounded data preparation failed; ledger authoritative: '+str(error));return value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--stage',default='prep')
    for name in('old-plan','native-plan','native-manifest','native-receipt','journal','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(execute(args),indent=2,allow_nan=False))


if __name__=='__main__':main()
