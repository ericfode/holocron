"""Separate once-only zero-apply fixture construction guard. No science launcher.

Preparation is data-only. Only the coordinator may initialize or execute stages.
The prior failed campaign is linked by immutable bytes, never reopened.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/'experiments'/'binding-transfer-fixture-validation-v1'
CONFIG=ROOT/'config.json'
LEDGER=ROOT/'campaign-ledger.jsonl'
OLD_LEDGER=ROOT.parent/'binding-transfer-v1'/'campaign-ledger.jsonl'
OLD_ARCHIVE=ROOT.parent/'publication-sources'/'binding-transfer-v1-failed-archive'
OLD_BINARY=ROOT.parent/'typed-ir-microprobe'/'target'/'debug'/'binding-transfer-native-collector'
HELPER=HERE/'binding_transfer_native_collector'/'supervise.py'
HELPER_SHA='3efe92e2e6e5f191fd95444655cf424b28420dc2db0b57c12e524359d035d958'
BIN='binding-transfer-fixture-validator'
STAGES={'build':15.,'validate':10.}
ZERO=dict(engine_apply_invocations=0,native_applies=0,neural_forwards=0,optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
CAPS=dict(seconds=25.,rss_bytes=1073741824,cpu_workers=1,**ZERO)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def pin(path):
    p=Path(path).resolve();data=p.read_bytes()
    return dict(path=str(p),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def verify(p):
    if pin(p['path'])!=p:raise ValueError('immutable byte pin changed: '+p['path'])
def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def canonical(path,expected):
    if Path(path).resolve()!=expected.resolve():raise ValueError('one canonical path required: '+str(expected))


def load_helper():
    if pin(HELPER)['sha256']!=HELPER_SHA:raise ValueError('reviewed process helper changed')
    spec=importlib.util.spec_from_file_location('fixture_zero_process_helpers',HELPER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def prepare(cargo,manifest,target,collection_plan,extra_pins=(),source_manifest=None):
    """Only public/source byte reads; no process, engine or numerical import."""
    manifest=manifest.resolve();target=target.resolve();collection_plan=collection_plan.resolve()
    crate=manifest.parent;binary=target/'debug'/BIN
    source_manifest=Path(source_manifest or ROOT/'validation-source-manifest.json').resolve();source=read(source_manifest)
    if source.get('schema')!='jepa-binding-transfer-fixture-validation-source/1':raise ValueError('reviewed fixture-only source manifest required')
    required=[Path(__file__),HERE/'test_binding_transfer_fixture_guard.py',HELPER,manifest,
        crate/'Cargo.lock',crate/'src'/'main.rs',crate/'src'/'fixture_validator.rs',collection_plan,
        OLD_LEDGER,OLD_ARCHIVE/'manifest.json',OLD_ARCHIVE/'evidence-index.json',OLD_BINARY,Path(cargo),source_manifest]
    for expected in source['pinned_execution_inputs']:
        verify(expected);required.append(Path(expected['path']))
    for expected in source['project_files']:
        p=crate/expected['path']
        if pin(p)['sha256']!=expected['sha256']or pin(p)['bytes']!=expected['bytes']:raise ValueError('current fixture source differs from reviewed manifest')
        required.append(p)
    pins=[pin(p)for p in sorted(set(p.resolve()for p in(*required,*extra_pins)))]
    old=read_lines(OLD_LEDGER)
    if not old or old[-1]['event']!='stage-finish'or old[-1]['data']['status']!='failed':raise ValueError('closed failed prior campaign required')
    stages={}
    for stage in STAGES:
        out=ROOT/(stage+'-1');receipt=ROOT/(stage+'-1-stage-receipt.json')
        argv=([str(cargo),'build','--offline','--locked','--manifest-path',str(manifest),'--bin',BIN,'-j','1']if stage=='build'else[str(binary),'--validate-fixtures-only',str(out/'validation.json')])
        stages[stage]=dict(argv=argv,cwd=str(crate),out=str(out),receipt=str(receipt),seconds=STAGES[stage])
    config=dict(schema='jepa-zero-apply-fixture-guard/1',root=str(ROOT),ledger_path=str(LEDGER),caps=CAPS,
        source=pin(__file__),helper=pin(HELPER),pins=pins,stages=stages,binary=str(binary),target_dir=str(target),
        collection_plan=str(collection_plan),source_manifest=pin(source_manifest),parent=dict(ledger=pin(OLD_LEDGER),last_record_sha256=old[-1]['record_sha256'],
        archive_manifest=pin(OLD_ARCHIVE/'manifest.json'),archive_index=pin(OLD_ARCHIVE/'evidence-index.json'),
        charged_native_applies=160,charged_seconds=110.10179149871692,observed_native_applies=None,scope='Prior charged failures remain immutable; historical observed native aggregate remains unknown. This is new zero-call fixture construction only.'),
        no_retries=True,science_execution_authorized=False)
    config['config_sha256']=digest(config);write_new(CONFIG,config);return config


def read_lines(path):return[json.loads(line)for line in Path(path).read_text().splitlines()]
def validate_config(config):
    if config.get('schema')!='jepa-zero-apply-fixture-guard/1'or config.get('caps')!=CAPS:raise ValueError('fixed zero-call caps/schema differ')
    canonical(config['root'],ROOT);canonical(config['ledger_path'],LEDGER)
    unsigned=dict(config);claimed=unsigned.pop('config_sha256')
    if digest(unsigned)!=claimed:raise ValueError('config digest differs')
    if config['helper']['sha256']!=HELPER_SHA:raise ValueError('process helper pin differs')
    if set(config['stages'])!=set(STAGES):raise ValueError('only build/validate stages exist')
    for name,limit in STAGES.items():
        s=config['stages'][name]
        if s['seconds']!=limit:raise ValueError('fixed stage seconds differ')
        canonical(s['out'],ROOT/(name+'-1'));canonical(s['receipt'],ROOT/(name+'-1-stage-receipt.json'))
    b=config['stages']['build']['argv'];v=config['stages']['validate']['argv']
    if len(b)!=10 or b[1:5]!=['build','--offline','--locked','--manifest-path']or b[6:]!=['--bin',BIN,'-j','1']:raise ValueError('only the unique validator Cargo build is allowed')
    if Path(v[0]).name!=BIN or v!=[config['binary'],'--validate-fixtures-only',str(ROOT/'validate-1'/'validation.json')]:raise ValueError('only forced zero-call validation CLI is allowed')
    return config


def append(stream,rows,event,data):
    row=dict(schema='jepa-zero-apply-fixture-ledger/1',sequence=len(rows),previous_sha256=rows[-1]['record_sha256']if rows else None,event=event,data=data)
    row['record_sha256']=digest(row);stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno());rows.append(row);return row
def state(rows):
    if not rows or rows[0]['event']!='initialized':raise ValueError('initialized ledger required')
    pending=None;used=[];completed=[];charged=0.
    for i,row in enumerate(rows):
        value=dict(row);claim=value.pop('record_sha256')
        if row['schema']!='jepa-zero-apply-fixture-ledger/1'or row['sequence']!=i or row['previous_sha256']!=(rows[i-1]['record_sha256']if i else None)or digest(value)!=claim:raise ValueError('ledger chain invalid')
        if i==0:continue
        data=row['data'];stage=data['stage']
        if stage not in STAGES:raise ValueError('unknown stage')
        if row['event']=='stage-start':
            if pending or stage in used or data['reserved_seconds']!=STAGES[stage]or data['reserved_calls']!=ZERO:raise ValueError('repeated/pending/changed reservation')
            if stage=='validate'and'build'not in completed:raise ValueError('successful unique build required')
            pending=data;used.append(stage)
        elif row['event']=='stage-finish':
            calls=data['observed_calls']
            if pending is None or pending['stage']!=stage or data['status']not in('completed','failed')or set(calls)!=set(ZERO)or any(v not in(0,None)for v in calls.values())or not isinstance(data['active_seconds'],(int,float))or data['active_seconds']<0:raise ValueError('invalid zero-call terminal record')
            if data['status']=='completed'and(calls!=ZERO or data.get('observed_verified')is not True):raise ValueError('completed stage needs verified zero-call witness')
            expected=data['active_seconds']if data['status']=='completed'else max(STAGES[stage],data['active_seconds'])
            if data['charged_seconds']!=expected or data['cleanup_verified']is not True:raise ValueError('invalid debit/cleanup')
            charged+=expected
            if data['status']=='completed':completed.append(stage)
            pending=None
        else:raise ValueError('unknown event')
    return dict(pending=pending,used=used,completed=completed,charged_seconds=charged)


def initialize(config_path=None):
    config_path=CONFIG if config_path is None else config_path
    canonical(config_path,CONFIG);config=validate_config(read(config_path))
    for item in config['pins']:verify(item)
    ROOT.mkdir(parents=True,exist_ok=True)
    with LEDGER.open('x')as stream:
        rows=[];append(stream,rows,'initialized',dict(config=pin(CONFIG),parent=config['parent'],caps=CAPS))
    return pin(LEDGER)


@contextmanager
def lease():
    with LEDGER.open('r+')as stream:
        fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        rows=[json.loads(line)for line in stream.read().splitlines()];current=state(rows)
        if current['pending']:raise RuntimeError('pending owned cleanup blocks all launch; no automatic recovery')
        verify(rows[0]['data']['config']);config=validate_config(read(CONFIG));stream.seek(0,2)
        yield stream,rows,current,config


def validate_receipt(raw,collection_plan):
    expected=dict(schema='jepa-binding-transfer-fixture-validation/1',validationComplete=True,
        applyCalls=0,engineApplyInvocations=0,actionsApplied=0,nativeJournalCreated=False,neuralForwards=0,optimizerUpdates=0)
    for name,value in expected.items():
        if name not in raw or type(raw[name])is not type(value)or raw[name]!=value:raise ValueError('zero-call construction witness differs: '+name)
    plan=read(collection_plan)
    if raw.get('collectionPlanSha256')!=pin(collection_plan)['sha256']or raw.get('collectionPlan')!=plan:raise ValueError('full unchanged collection plan differs')
    cases=raw.get('cases')
    if not isinstance(cases,list)or len(cases)!=26 or[type(c.get('world_id'))for c in cases]!=[int]*26 or sorted(c['world_id']for c in cases)!=list(range(26)):raise ValueError('26 unique fixture world ids required')
    cards={w['id']:w['source_code']for w in plan['worlds']}
    for case in cases:
        if case.get('card')!=cards[case['world_id']]or case.get('publicSnapshotRoundtripExact')is not True or case.get('legalActionsRoundtripExact')is not True:raise ValueError('fixture identity/public snapshot or legal query roundtrip differs')
        if type(case.get('applyCalls'))is not int or case['applyCalls']!=0 or type(case.get('actionsApplied'))is not int or case['actionsApplied']!=0:raise ValueError('per-fixture zero counters differ')
        if any(p.get('exact')is not True or p.get('linkedUpgradeOrder')!=p.get('registrationUpgradeOrder')for p in case.get('attachmentChronology',[])):raise ValueError('fixture attachment registration chronology differs')
        if any(w.get('offeredHost')is None for w in case.get('fixtureAttachmentWitnesses',[])):raise ValueError('fixture upgrade-target query witness missing')
        if any(k in case for k in('steps','final','targetAction')):raise ValueError('fixture-only receipt must not contain action outcome labels')
    return dict(**expected,cases=26,unique_world_ids=list(range(26)),collection_plan=pin(collection_plan))


def terminal_status(preliminary,elapsed,limit):
    status='completed'if preliminary=='completed'and elapsed<=limit else'failed'
    return status,elapsed if status=='completed'else max(limit,elapsed)


def run(stage):
    if stage not in STAGES:raise ValueError('no collection, fit or other execution stage exists')
    with lease()as(stream,rows,current,config):
        if stage in current['used']:raise RuntimeError('once-only stage already reserved; no retries')
        if stage=='validate'and'build'not in current['completed']:raise RuntimeError('completed unique build required')
        descriptor=config['stages'][stage];out=Path(descriptor['out']);receipt_path=Path(descriptor['receipt']);start=time.monotonic();limit=STAGES[stage]
        receipt=dict(stage=stage,status='failed',argv=descriptor['argv'],config=pin(CONFIG),observed_calls=ZERO,
            observed_per_pid_peak_bytes={},sample_count=0,cleanup_verified=True,created_output=False)
        append(stream,rows,'stage-start',dict(stage=stage,owner_pid=os.getpid(),reserved_seconds=limit,reserved_calls=ZERO,
            exact_argv=descriptor['argv'],cwd=descriptor['cwd'],outputs=[str(out),str(receipt_path)],input_pins=config['pins'],started_monotonic_seconds=start))
        proc=None;helpers=None;members=None;proofs=[];cleanup=True;launched=False;witness=False
        try:
            for item in config['pins']:verify(item)
            if out.exists()or receipt_path.exists():raise FileExistsError('exclusive attempt outputs already exist')
            if stage=='validate':
                build=[r for r in rows if r['event']=='stage-finish'and r['data']['stage']=='build'and r['data']['status']=='completed'][-1]
                expected=[p for p in build['data']['proofs']if p['path']==config['binary']]
                if len(expected)!=1:raise ValueError('unique built validator byte proof required')
                verify(expected[0]);receipt['binary']=expected[0]
            out.mkdir(parents=True);receipt['created_output']=True
            helpers=load_helper();rss,members=helpers.process_readers()
            if rss(os.getpid())>CAPS['rss_bytes']:raise RuntimeError('initial supervisor RSS exceeds1GiB')
            env=helpers.build_environment(Path(config['target_dir']));env.pop('PYTHONPATH',None);env.pop('BINDING_TRANSFER_NATIVE_TRACE',None)
            env['BINDING_TRANSFER_COLLECTION_PLAN']=config['collection_plan']
            receipt['environment_overrides']=dict(CARGO_BUILD_JOBS='1',CARGO_NET_OFFLINE='true',BINDING_TRANSFER_COLLECTION_PLAN=config['collection_plan'],BINDING_TRANSFER_NATIVE_TRACE='ABSENT',cpu_threads=1)
            if time.monotonic()-start>=limit:raise TimeoutError('stage budget exhausted before launch')
            with(out/'stdout.log').open('x')as stdout,(out/'stderr.log').open('x')as stderr:
                proc=subprocess.Popen(descriptor['argv'],cwd=descriptor['cwd'],env=env,stdout=stdout,stderr=stderr,start_new_session=True)
                launched=True
                receipt.update(owned_pid=proc.pid,owned_pgid=proc.pid)
                while True:
                    readings=helpers.read_owned_rss(receipt,members(proc.pid),rss,os.getpid(),time.monotonic()-start)
                    peak=helpers.memory_sample(receipt,readings,os.getpid(),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);receipt['sample_count']+=1
                    if peak>CAPS['rss_bytes']:raise RuntimeError('sampled concurrent owned RSS exceeds1GiB')
                    if time.monotonic()-start>=limit:raise TimeoutError('fixed stage wall time exhausted')
                    code=proc.poll()
                    if code is not None:
                        receipt['exit_code']=code
                        if members(proc.pid):raise RuntimeError('owned descendants remain after leader exit')
                        proc=None
                        if code:raise RuntimeError('owned stage exit'+str(code))
                        break
                    time.sleep(.02)
            if stage=='build':proofs.append(pin(config['binary']))
            else:receipt['construction_witness']=validate_receipt(read(out/'validation.json'),config['collection_plan']);proofs.append(pin(out/'validation.json'));witness=True
            for item in config['pins']:verify(item)
            receipt['status']='completed'
        except BaseException as error:
            receipt['error']=dict(type=type(error).__name__,message=str(error))
            if proc is not None:cleanup=helpers.cleanup_owned(proc,proc.pid,members,receipt)
        elapsed=time.monotonic()-start
        bound=max(receipt.get('observed_peak_live_sum_bytes',0),resource.getrusage(resource.RUSAGE_SELF).ru_maxrss+resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        if elapsed>limit or bound>CAPS['rss_bytes']:receipt.update(status='failed',guard_limit_exceeded=True)
        receipt.update(active_seconds=elapsed,cleanup_verified=cleanup,final_rusage_supplemented_peak_bytes=bound,
            memory_limitation='20ms live owned-group RSS samples supplemented by supervisor peak plus max single-child rusage; no OS tree memory reservation.',
            charged_seconds=elapsed if receipt['status']=='completed'else max(limit,elapsed),source=pin(__file__),input_pins=config['pins'])
        receipt['observed_verified']=bool(stage=='build'or not launched or witness)
        receipt['observed_calls']=dict(ZERO)if receipt['observed_verified']else{k:None for k in ZERO}
        receipt['zero_call_scope']='Allocation and reviewed forced validator path permit zero scientific calls. A failed launched validator without the full26-case witness has unknown measured counters; no zero-call success claim.'
        if receipt['created_output']:proofs.extend(pin(p)for p in sorted(out.rglob('*'))if p.is_file())
        receipt['proofs']=proofs;receipt['preliminary']=True;receipt['status_authority']='Append-only campaign ledger terminal row; elapsed includes receipt/proof writes and may downgrade this preliminary status.'
        # External receipt is attempted even when startup failed before mkdir.
        # Any uncertainty or receipt write failure leaves the reservation pending.
        write_new(receipt_path,receipt)
        if not cleanup:raise RuntimeError('owned cleanup uncertain; pending reservation retained')
        terminal_proofs=[*proofs,pin(receipt_path)]
        elapsed=time.monotonic()-start;status,charged=terminal_status(receipt['status'],elapsed,limit)
        final=append(stream,rows,'stage-finish',dict(stage=stage,status=status,active_seconds=elapsed,charged_seconds=charged,
            cleanup_verified=True,observed_calls=receipt['observed_calls'],observed_verified=receipt['observed_verified'],proofs=terminal_proofs,
            preliminary_receipt_status=receipt['status'],elapsed_scope='From pre-reservation start through receipt and proof writes; measured immediately before terminal append/fsync.'))
        state(rows)
        receipt.update(status=status,active_seconds=elapsed,charged_seconds=charged,preliminary=False,authoritative_terminal_sha256=final['record_sha256'])
        if status!='completed':raise RuntimeError('failed zero-call stage retained; authoritative ledger status, no retry')
        return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--cargo',type=Path,required=True);a.add_argument('--manifest-path',type=Path,required=True);a.add_argument('--target-dir',type=Path,required=True);a.add_argument('--collection-plan',type=Path,required=True);a.add_argument('--source-manifest',type=Path);a.add_argument('--pin',type=Path,action='append',default=[])
    sub.add_parser('initialize');a=sub.add_parser('run');a.add_argument('--stage',choices=tuple(STAGES),required=True)
    args=p.parse_args()
    value=prepare(args.cargo,args.manifest_path,args.target_dir,args.collection_plan,args.pin,args.source_manifest)if args.command=='prepare'else initialize()if args.command=='initialize'else run(args.stage)
    print(json.dumps(value,indent=2,allow_nan=False))

if __name__=='__main__':main()
