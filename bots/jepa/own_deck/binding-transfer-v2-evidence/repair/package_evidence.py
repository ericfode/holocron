"""Explicit, bounded byte-only research packet. Preview is default; root alone builds.

No subprocess, framework, NumPy, engine, model, fit, remote client or publisher is
imported. The spec is a flat allowlist, not a recursive config/source-pin crawl.
Source paths are provenance; consumers verify relative packet files by hashes.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

HERE=Path(__file__).resolve().parent
TASK=HERE.parents[1]
REPO=TASK/'holocron-deck-context'
V2=HERE.parent/'binding-transfer-v2'
RECOVERY=HERE.parent/'binding-transfer-report-recovery-v1'
DESTINATION=REPO/'bots/jepa/own_deck/binding-transfer-v2-evidence'
SCHEMA='jepa-binding-transfer-repair-evidence/1'
SPEC_SCHEMA='jepa-binding-transfer-repair-evidence-spec/1'
MAX_STORED=25*1024**2
MAX_RAW=128*1024**2
MAX_SINGLE_RAW=32*1024**2
SEEDS=(17,29,43)
ARMS=('C0R0','C1R0','C0R1','C1R1','ID-only','untrained-typed')
FIT_NAMES={f's{s}-{a}-step{k}-predictions.npz'for s in SEEDS for a in ARMS for k in(0,300)}
FIT_NAMES|={f's{s}-{a}-checkpoint.npz'for s in SEEDS for a in ARMS}
FIT_NAMES|={f's{s}-initial-checkpoint.npz'for s in SEEDS}
FIT_NAMES|={'program-inputs.npz','consumed-inputs.npz','training-schedule.npz','contract.json','receipt.json'}
BASELINE_NAMES={name+'-predictions.npz'for name in(*ARMS[:4],'zero','train_mean')}|{'result.json','receipt.json'}
REQUIRED_ROLES={'original-config','original-ledger','failed-prep-receipt','native-receipt','native-journal','native-plan',
    'repair-config','repair-ledger','routing','prepared','source-plan','source-freeze','dataset','dataset-manifest','sealed-plan',
    'prep-receipt','fit','fit-progress','fit-receipt','baselines','baseline-progress','baseline-receipt',
    'verification','verification-receipt','report','spend-document','final-pins',
    'recovery-config','recovery-ledger','recovery-assembly-receipt','recovery-source-inventory','recovered-result','restoration-receipt'}
ALLOWED_ROLES=REQUIRED_ROLES|{'source','metadata','original-log','preparation','recovery-routing'}
FIXED_NATIVE={
    'native-receipt':('native-attempt-1/native-receipt.json','3b7c030a6ab8b737bceef44ed7951fd97d133a425c6633c26f7ff6c70e6139f6'),
    'native-journal':('native-attempt-1/native-transitions.jsonl','8819c0eea42c932db83a4540ce5bd4e38c0af0a6d01922d709b782ed9c3b0986'),
    'native-plan':('native-plan.json','0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f'),
    'original-config':('campaign-config.json','6c1bde1ea5274547279f510200438a5b0d18c73e8275b1cfe00b45b453f2f3f5'),
    'original-ledger':('campaign-ledger.jsonl','37d623f5f7a9675e49e8ebd74892244c3b9341e9391a387ae7383fe5449467c5'),
    'failed-prep-receipt':('prep-1-stage-receipt.json','54c1e00aba765c624590249a2e843c892f72c0945a974f844a9ea57616866e23'),
}
V2_ALLOWED={'campaign-config.json','campaign-ledger.jsonl','native-plan.json','native-source-manifest.json',
    'native-preparation-receipt.json','learner-prepared-v1.json','prelabel-routing-v1.json','prep-1-stage-receipt.json',
    'prep-1/receipt.json','native-attempt-1/native-receipt.json','native-attempt-1/native-transitions.jsonl',
    'native-attempt-1/supervisor-receipt.json','native-attempt-1/stdout.log','native-attempt-1/stderr.log',
    'native-build-1/supervisor-receipt.json','native-build-1/stdout.log','native-build-1/stderr.log'}
ZERO_EXPOSURE=dict(native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0)


def require(value,message):
    if not value:raise ValueError(message)


def encoded(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_text(),parse_constant=lambda x:(_ for _ in()).throw(ValueError('nonfinite JSON '+x)))
def pin(path):
    p=Path(path).resolve(strict=True);raw=p.read_bytes()
    return dict(path=str(p),sha256=digest(raw),bytes=len(raw))


def relative(value):
    require(isinstance(value,str)and value and not any(c in value for c in('\\',':','%','?','#')),'unsafe relative packet path')
    p=PurePosixPath(value)
    require(not p.is_absolute()and all(x not in('', '.', '..')for x in value.split('/')),'packet path must be canonical and relative')
    return value


def deterministic_gzip(raw):
    out=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=9)as f:f.write(raw)
    return out.getvalue()


def allowed_source(path,repair=HERE,native=V2,repo=REPO,recovery=RECOVERY):
    require(not Path(path).is_symlink(),'symlink evidence source rejected')
    p=Path(path).resolve(strict=True)
    repair,native,repo,recovery=map(lambda x:Path(x).resolve(),(repair,native,repo,recovery))
    require(p.is_file()and p.suffix.lower()in('.json','.jsonl','.npz','.log','.md','.py','.patch','.toml','.lock'),
            'only explicit bounded metadata/array/source files are allowed; no binary/runtime/archive payloads')
    if p.is_relative_to(native):
        require(p.relative_to(native).as_posix()in V2_ALLOWED,'original native campaign path is not allowlisted')
    elif p.is_relative_to(repair)or p.is_relative_to(recovery):
        require('target'not in p.parts and'node_modules'not in p.parts,'runtime dependency tree excluded')
    elif p.is_relative_to(repo/'bots/jepa/own_deck'):
        require('binding-transfer-v2-evidence'not in p.parts and'raw'not in p.parts,'recursive evidence/archive source rejected')
        require(p.suffix.lower()in('.md','.py','.patch','.toml','.lock'),'repository sources/reports only; no old evidence closure')
    else:raise ValueError('source outside explicit repair/native/repository documentation roots')
    require(p.stat().st_size<=MAX_SINGLE_RAW,'individual raw artifact exceeds32MiB')
    return p


def verify_chain(path):
    rows=[json.loads(s)for s in Path(path).read_text().splitlines()if s.strip()]
    require(bool(rows),'nonempty canonical ledger required');previous='0'*64;pending=None
    for n,row in enumerate(rows):
        body={k:v for k,v in row.items()if k!='record_sha256'}
        raw=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        require(row.get('sequence')==n and row.get('previous_sha256')==previous and row.get('record_sha256')==digest(raw),'ledger chain mismatch')
        previous=row['record_sha256']
        if row['event']in('stage-start','attempt-start'):
            require(pending is None,'overlapping ledger stages');pending=row['data'].get('stage',row['data'].get('phase'))
        if row['event']in('stage-finish','attempt-finish'):
            require(pending==row['data'].get('stage',row['data'].get('phase')),'ledger finish binding mismatch');pending=None
    require(pending is None,'publication cannot package a pending scientific stage')
    return dict(records=len(rows),final_record_sha256=previous,rows=rows)


def privacy_values(raw,lines):
    """Inspect actual authored fixtures; internal proof fields are not actor inputs."""
    require(raw.get('collectionComplete')is True and len(raw['cases'])==26 and raw['applyCalls']==48,'complete48-apply/26-root native record required')
    complete=[r['case']for r in lines if r.get('phase')=='contextComplete']
    require(complete==raw['cases'],'raw/journal roots differ')
    phases={name:sum(r.get('phase')==name for r in lines)for name in('beforeApply','afterApply','contextComplete','applyError')}
    require(phases==dict(beforeApply=48,afterApply=48,contextComplete=26,applyError=0),'native journal phase counts differ')
    captures=[];codes=set();own_hand=set();resource_codes=set()
    def walk(x):
        if isinstance(x,dict):
            if isinstance(x.get('state'),dict)and isinstance(x.get('projections'),dict):captures.append(x)
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(raw['cases'])
    require(bool(captures),'native public captures missing')
    admitted=set(raw['collectionPlan']['selected_whole_cards'])
    source_codes={c['card']for c in raw['cases']}
    def physical(x):
        if isinstance(x,dict):
            if'setCode'in x:
                require(x['setCode']in admitted and x['setCode']!='TOKEN_SHIELD','unreviewed physical identity/Shield in fixture')
                codes.add(x['setCode'])
            for v in x.values():physical(v)
        elif isinstance(x,list):
            for v in x:physical(v)
    for cap in captures:
        players=cap['state']['players']
        require(set(players)=={'p1','p2'},'two authored players required')
        for seat in('p1','p2'):
            player=players[seat]
            require(player['deck']==[] and player['discard']==[],'draw/discard piles must remain empty in this exact cohort')
            if seat=='p2':require(player['hand']==[] and player['resources']==[],'opponent private fixture zones must remain empty')
            else:
                require(len(player['hand'])<=1,'only declared own focus hand is allowed')
                for c in player['hand']:
                    require(c['setCode']in source_codes,'unexpected own hand identity');own_hand.add(c['setCode'])
                for c in player['resources']:
                    require(c['setCode']=='LOF_256','unexpected own resource identity');resource_codes.add(c['setCode'])
        physical(cap['state'])
    return dict(status='authored-public-fixtures-only',raw_case_captures=len(captures),opponent_hand_cards=0,
        opponent_resource_cards=0,draw_pile_cards=0,discard_cards=0,physical_shields=0,
        own_focus_source_codes=sorted(own_hand),own_resource_codes=sorted(resource_codes),physical_codes=sorted(codes),
        no_hidden_draw_order=True,internal_runtime_counters='Proof-only diagnostic metadata; excluded from learned before-input tensors.',
        source_paths='Local paths are provenance, never secret credentials or consumer fetch targets.')


def privacy_summary(native,journal):
    return privacy_values(read(native),[json.loads(s)for s in Path(journal).read_text().splitlines()if s.strip()])


def npz_inventory(raw):
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        names=z.namelist();require(bool(names)and len(names)==len(set(names)),'NPZ members must be nonempty/unique')
        total=0
        for entry in z.infolist():
            require('/'not in entry.filename and'\\'not in entry.filename and entry.filename.endswith('.npy'),'NPZ may contain only flat NPY members')
            total+=entry.file_size;require(total<=MAX_SINGLE_RAW,'NPZ uncompressed members exceed32MiB')
        return dict(members=names,uncompressed_member_bytes=total,scope='ZIP metadata only; no array/framework load or numerical calculation.')


def fit_inventory(entries):
    found=[Path(v['source']).name for v in entries if v['role']=='fit']
    require(len(found)==len(set(found))and set(found)==FIT_NAMES,'entire original failed fit directory required:36predictions/18checkpoints/3initial plus inputs/contract/failedreceipt; recovered result is separate')
    return dict(prediction_files=36,trained_checkpoint_files=18,initial_checkpoint_files=3,fit_files=len(found))


def baseline_inventory(entries):
    names=[Path(v['source']).name for v in entries if v['role']=='baselines']
    require(len(names)==len(set(names))and set(names)==BASELINE_NAMES,'all six fixed baseline predictions plus result/receipt are required')
    return dict(prediction_files=6,baseline_files=len(names))


def collect(spec_path):
    spec=read(spec_path)
    require(spec.get('schema')==SPEC_SCHEMA and spec.get('status')=='closed-science-root-reviewed-for-packaging','explicit final root-reviewed packaging spec required')
    require(re.fullmatch('[0-9a-f]{40}',spec.get('source_freeze_commit','')),'root-attested40hex source freeze required')
    entries=spec.get('files');require(isinstance(entries,list)and entries,'flat nonempty explicit file allowlist required')
    require(REQUIRED_ROLES<={r.get('role')for r in entries},'required scientific/failure/accounting/report evidence role missing')
    destinations=set();sources=set();total=0;loaded=[];by_role={}
    for entry in entries:
        require(entry['role']in ALLOWED_ROLES,'unknown evidence role')
        source=allowed_source(entry['source']);destination=relative(entry['destination'])
        require(destination not in('manifest.json','README.md')and destination not in destinations,'reserved/duplicate packet destination')
        require(str(source)not in sources,'duplicate source should have one explicit packet record')
        destinations.add(destination);sources.add(str(source));expected=dict(path=str(source),sha256=entry['sha256'],bytes=entry['bytes'])
        require(pin(source)==expected,'allowlisted source pin changed')
        raw=source.read_bytes();total+=len(raw);require(total<=MAX_RAW,'raw packet exceeds128MiB')
        encoding=entry.get('encoding','gzip'if source.suffix in('.json','.jsonl')else'identity')
        require(encoding in('identity','gzip'),'only identity/deterministicgzip supported')
        require((destination.endswith('.gz'))==(encoding=='gzip'),'gzip destination suffix must disclose stored encoding')
        stored=deterministic_gzip(raw)if encoding=='gzip'else raw
        row=dict(role=entry['role'],path=destination,encoding=encoding,sha256=digest(stored),bytes=len(stored),
            content_sha256=digest(raw),content_bytes=len(raw),source=expected)
        if source.suffix=='.npz':row['npz_inventory']=npz_inventory(raw)
        loaded.append((row,stored));by_role.setdefault(entry['role'],[]).append(source)
    for role,(name,sha)in FIXED_NATIVE.items():
        require(len(by_role[role])==1 and by_role[role][0]==(V2/name).resolve()and pin(by_role[role][0])['sha256']==sha,'original native/failure evidence cannot be substituted: '+role)
    fit_counts=fit_inventory(entries)
    baseline_counts=baseline_inventory(entries)
    original=verify_chain(by_role['original-ledger'][0]);repair=verify_chain(by_role['repair-ledger'][0]);recovery=verify_chain(by_role['recovery-ledger'][0])
    finishes=[r['data']for r in original['rows']if r['event']=='stage-finish']
    require([(r['stage'],r['status'])for r in finishes]==[('build','completed'),('native','completed'),('prep','failed')],'original failedprep must remain preserved')
    require(finishes[-1]['charged']['seconds']==5 and finishes[-1]['charged']['native_applies']==0,'failedprep full5seconds charge must remain retained')
    require(read(by_role['verification'][0]).get('status')=='PASS','independent successful saved-output verifier required')
    require(read(by_role['verification-receipt'][0]).get('status')=='completed','completed verifier accounting receipt required')
    repair_finishes=[r['data']for r in repair['rows']if r['event']=='stage-finish']
    require([(r['stage'],r['status'])for r in repair_finishes]==[('prep','completed'),('fit','failed')],'original prep/fit dispositions must remain unchanged')
    failed_fit=repair_finishes[-1]
    require(failed_fit['charged']['seconds']==60 and failed_fit['charged']['optimizer_updates']==5400
        and failed_fit['charged']['neural_forwards']==5436,'original failedfit full reservation must remain charged')
    require(failed_fit['observed']['neural_forwards']is None and failed_fit['observed']['optimizer_updates']is None,
        'original official unknown fit counters must remain null')
    failed_receipt=read(by_role['fit-receipt'][0])
    require(failed_receipt.get('status')=='failed'and failed_receipt.get('error',{}).get('type')=='TypeError'
        and failed_receipt.get('durable_prefix')==dict(optimizer_updates=5400,training_forwards=5400,evaluation_forwards=36,export_forwards=0),
        'preserve failed JSON writer and complete durable prefix separately from official observed counters')
    require(failed_receipt['observed']['neural_forwards']is None and failed_receipt['observed']['optimizer_updates']is None,
        'original failed receipt unknown counters must remain null')
    recovered=read(by_role['recovered-result'][0])
    require(recovered.get('status')=='recovered-from-saved-artifacts'and recovered.get('original_fit_status')=='failed',
        'recovered report must disclose its separate saved-artifact origin and original failure')
    for key,role in(('failed_fit_ledger','repair-ledger'),('failed_fit_receipt','fit-receipt'),('fit_progress','fit-progress')):
        require(recovered.get('recovery_provenance',{}).get(key)==pin(by_role[role][0]),'recovered report original provenance differs: '+key)
    require(recovered.get('source_inventory')==pin(by_role['recovery-source-inventory'][0]),'recovered complete source inventory pin differs')
    require(any(r['event']=='stage-finish'and r['data'].get('stage')=='verify'and r['data'].get('status')=='completed'for r in recovery['rows']),
        'separate recovery ledger must close successful supplemental verification')
    require(read(by_role['restoration-receipt'][0]).get('status')=='completed','completed zero-forward restoration receipt required')
    for row in recovery['rows']:
        if row['event']=='stage-finish':
            observed=row['data']['observed']
            require(all(observed[k]==0 for k in('native_applies','neural_forwards','optimizer_updates','paid_jobs','paid_spend_usd')),
                'report recovery must have known zero native/neural/update/paid exposure; numerical baselines remain separate')
    privacy=privacy_summary(by_role['native-receipt'][0],by_role['native-journal'][0])
    stored_total=sum(len(v)for _,v in loaded);require(stored_total<=MAX_STORED,'compressed packet exceeds25MiB')
    return spec,loaded,dict(source_freeze_commit_root_attested=spec['source_freeze_commit'],fit_inventory=fit_counts,baseline_inventory=baseline_counts,
        original_ledger_final_record_sha256=original['final_record_sha256'],repair_ledger_final_record_sha256=repair['final_record_sha256'],
        recovery_ledger_final_record_sha256=recovery['final_record_sha256'],
        original_fit_status='failed-retained-no-credit',fit_durable_prefix=failed_receipt['durable_prefix'],
        original_official_observed_fit_counters=failed_fit['observed'],recovered_result=pin(by_role['recovered-result'][0]),
        privacy=privacy,raw_bytes=total,stored_payload_bytes=stored_total,files=len(loaded),spend_document=[pin(p)for p in by_role['spend-document']],
        scope='Bounded scientific evidence only; runtime dependencies, native binaries and preceding212MB archive/oldportableZIP closure are excluded.',
        semantic_validated=False,science_performed_by_packager=ZERO_EXPOSURE,remote_publication_performed=False)


def preview(spec_path):
    _,loaded,summary=collect(spec_path)
    return dict(status='preview-no-copies',destination=str(DESTINATION),summary=summary,
        source_files=[row for row,_ in loaded],spec=pin(spec_path))


def build(spec_path):
    spec,loaded,summary=collect(spec_path);out=DESTINATION
    require(not out.exists(),'new immutable packet directory required')
    out.mkdir(parents=True,exist_ok=False)
    for record,stored in loaded:
        p=out/record['path'];p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb')as f:f.write(stored)
    text=('# Binding-transfer v2 bounded evidence\n\nThis packet retains the successful26-root/48-application native collection, the failed five-second preparation, the failed post-fit JSON writer, and separately linked zero-neural report restoration/baselines/supplemental verification. The original fit remains failed with its full reservation and official unknown counters; the complete5400/5436 durable prefix and saved outputs are separate evidence. No failure is credited or rewritten. Packaging reruns no science, adds no embedding space, publishes no remote asset and makes no general card/deck semantic claim.\n\nVerify manifest.json stored hashes before opening a file. Gzip payloads use deterministic mtime0; content_sha256/content_bytes pin the exact decoded source bytes. Original paths and source-freeze metadata are provenance only. Full local runtime/nativebinary and prior archive closures are excluded.\n')
    (out/'README.md').write_text(text)
    authored=pin(out/'README.md');authored.pop('path');authored['path']='README.md'
    manifest=dict(schema=SCHEMA,status='closed-bounded-experiment-evidence',files=[r for r,_ in loaded],authored_files=[authored],
        summary=summary,packaging_spec=pin(spec_path),packager=pin(__file__),semantic_validated=False)
    with(out/'manifest.json').open('x')as f:json.dump(manifest,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
    for record,_ in loaded:require(pin(record['source']['path'])==record['source'],'source changed during packaging')
    return verify(out,check_originals=True)


def verify(out,expected_manifest_sha256=None,check_originals=False):
    out=Path(out).resolve(strict=True);manifest=read(out/'manifest.json')
    if expected_manifest_sha256 is not None:require(pin(out/'manifest.json')['sha256']==expected_manifest_sha256,'external manifest pin differs')
    require(manifest.get('schema')==SCHEMA and manifest.get('semantic_validated')is False,'packet schema/unqualified scope differs')
    expected={'manifest.json'};total=(out/'manifest.json').stat().st_size;native_payloads={}
    for record in manifest['files']+manifest['authored_files']:
        name=relative(record['path']);require(name not in expected,'duplicate packet path');expected.add(name);p=out/name
        require(not p.is_symlink()and p.resolve().is_relative_to(out),'packet symlink/escape rejected')
        require(type(record['bytes'])is int and 0<=record['bytes']<=MAX_STORED and p.stat().st_size==record['bytes'],'stored packet size bound differs')
        raw=p.read_bytes();total+=len(raw)
        require(digest(raw)==record['sha256']and len(raw)==record['bytes'],'stored packet hash/bytes differ')
        if'content_sha256'in record:
            require(record['encoding']in('gzip','identity'),'unknown packet encoding')
            require(type(record['content_bytes'])is int and 0<=record['content_bytes']<=MAX_SINGLE_RAW,'decoded packet size bound differs')
            if record['encoding']=='gzip':
                with gzip.GzipFile(fileobj=io.BytesIO(raw),mode='rb')as stream:content=stream.read(MAX_SINGLE_RAW+1)
            else:content=raw
            require(digest(content)==record['content_sha256']and len(content)==record['content_bytes'],'decoded source bytes differ')
            if record['role']in FIXED_NATIVE:
                require(record['content_sha256']==FIXED_NATIVE[record['role']][1],'original native/failure bytes substituted in packet')
            if record['role']in('native-receipt','native-journal'):native_payloads[record['role']]=content
            if check_originals:require(pin(record['source']['path'])==record['source'],'original source changed')
    require(all(not p.is_symlink()for p in out.rglob('*')),'packet symlinks rejected')
    require({p.relative_to(out).as_posix()for p in out.rglob('*')if p.is_file()}==expected,'missing/unmanifested packet files')
    require(total<=MAX_STORED,'stored packet exceeds25MiB')
    roles={r['role']for r in manifest['files']};require(REQUIRED_ROLES<=roles,'required evidence roles missing')
    fit_inventory([dict(source=r['source']['path'],role=r['role'])for r in manifest['files']])
    baseline_inventory([dict(source=r['source']['path'],role=r['role'])for r in manifest['files']])
    privacy=privacy_values(json.loads(native_payloads['native-receipt']),[json.loads(s)for s in native_payloads['native-journal'].decode().splitlines()if s.strip()])
    require(privacy==manifest['summary']['privacy'],'copied native privacy summary differs from actual payloads')
    return dict(status='verified',manifest=pin(out/'manifest.json'),files=len(expected),stored_bytes=total,
        originals_checked=check_originals,semantic_validated=False,remote_publication_performed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--build',action='store_true');mode.add_argument('--verify',type=Path);mode.add_argument('--describe',action='store_true')
    parser.add_argument('--spec',type=Path);parser.add_argument('--expected-manifest-sha256');parser.add_argument('--check-originals',action='store_true')
    args=parser.parse_args()
    if args.describe:
        result=dict(schema=SPEC_SCHEMA,status='closed-science-root-reviewed-for-packaging',source_freeze_commit='<root-verified40hex>',
            required_roles=sorted(REQUIRED_ROLES),fit_names=sorted(FIT_NAMES),baseline_names=sorted(BASELINE_NAMES),fixed_original_native=FIXED_NATIVE,
            files=[dict(role='<requiredrole>',source='<absolute allowlisted source>',destination='<canonicalrelative>',sha256='<sha256>',bytes=0,encoding='gzip')],
            destination=str(DESTINATION),max_stored_bytes=MAX_STORED,no_copy_performed=True)
    elif args.verify:result=verify(args.verify,args.expected_manifest_sha256,args.check_originals)
    else:
        require(args.spec is not None,'explicit final reviewed --spec required')
        result=build(args.spec)if args.build else preview(args.spec)
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))


if __name__=='__main__':main()
