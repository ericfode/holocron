"""Once-only supplemental checker; ended recovery accounting remains immutable."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import time

import public_input_binding_recovery_accounting as A

PARENT = dict(path=str(A.LEDGER), sha256='7e23b61f5defc3f07199b87693dcfc36a4a80e3ca8f795a473e8c0d8bf7ede05', bytes=42610)
PARENT_CHAIN = '3b52469f736894260f3cdb6494231d278526924cd6ba78e18e0277d97f15d0e1'
ACCOUNTING_SHA = 'ac3cca80088352a94873ce9b67ae0d746897f509d47a82e05bfc2cde81cbabe7'
GUARD = A.HERE/'effect_identifiability_fit.py'
GUARD_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
VERIFIER = A.HERE/'public_input_binding_supplemental_verify.py'
VERIFIER_SHA = 'a9a723c02abb20aa790b40e8e36f7c12cfbc7b32a456bb8ce54dd85487e3c016'
OUTPUT = A.CAMPAIGN/'independent-verification-supplemental.json'
JOURNAL = A.CAMPAIGN/'supplemental-verification-ledger.jsonl'
SCHEMA = 'jepa-public-input-binding-supplemental-analysis/1'
SECONDS = 12.
BLOCKED = {'torch','tinygrad','tensorflow','jax','jaxlib','keras','transformers','cupy','sklearn','statsmodels'}


def audit_event(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in BLOCKED:
        raise RuntimeError('neural/fit library import forbidden')
    if event.startswith(('socket.','subprocess.','os.exec','os.spawn','os.posix_spawn')) or event in ('os.system','os.fork','os.forkpty','os.killpg'):
        raise RuntimeError('network/process execution forbidden')
    if event == 'os.kill' and args != (os.getpid(),signal.SIGALRM):
        raise RuntimeError('only own guard SIGALRM allowed')


def parent_state(records, current):
    A.verify_pins([PARENT])
    if A.pin(A.__file__)['sha256'] != ACCOUNTING_SHA or A.chain(records) != PARENT_CHAIN:
        raise ValueError('exact immutable recovery parent/accounting required')
    if current['pending'] or current['completed_stages'] != ['native-build','native-collect','analysis-controls'] or current['seen_stages'] != ['native-build','native-collect','analysis-controls','analysis-verification']:
        raise ValueError('ended recovery with original failed checker required')
    if records[-1]['event'] != 'attempt-finish' or records[-1]['data']['status'] != 'failed':
        raise ValueError('original checker failure must remain preserved')
    A.verify_parents(); A.recovery_parent(); A.verify_pins(current['config']['pins'])
    charged = current['phase_charged_seconds']['analysis']
    if charged + SECONDS > 30.:
        raise ValueError('supplement must fit the original shared analysis allowance')
    return charged


def descriptor(path, current):
    value = json.loads(Path(path).read_text())
    expected = json.loads(json.dumps(current['config']['analysis_commands']['analysis-verification']))
    expected['argv'][0] = str(VERIFIER)
    if expected['argv'][-2] != '--out': raise ValueError('frozen verification command layout changed')
    expected['argv'][-1] = str(OUTPUT); expected['outputs'] = [str(OUTPUT)]
    if value.get('schema') != SCHEMA or value.get('seconds') != SECONDS or {k:value.get(k) for k in ('argv','outputs')} != expected:
        raise ValueError('only the new zone-aware checker/output may differ from the frozen command')
    A.verify_pins(value['pins'])
    pins = {p['path']:p for p in value['pins']}
    required = [Path(__file__), Path(A.__file__), GUARD, VERIFIER, Path(PARENT['path'])]
    required += [Path(expected['argv'][i+1]) for i,x in enumerate(expected['argv'][:-1]) if x in ('--plan','--receipt','--journal','--predictions','--predictor-source')]
    if any(pins.get(str(p.resolve())) != A.pin(p) for p in required):
        raise ValueError('pin all sources, ended ledger, native inputs and saved predictions before launch')
    if A.pin(GUARD)['sha256'] != GUARD_SHA or A.pin(VERIFIER)['sha256'] != VERIFIER_SHA or pins[str(A.LEDGER)] != PARENT:
        raise ValueError('immutable guard/new checker/ended recovery pin differs')
    if OUTPUT.exists() or JOURNAL.exists(): raise FileExistsError('supplement already attempted; never retry or replace')
    return value


def append(stream, records, event, data):
    body = dict(schema=SCHEMA,sequence=len(records),previous_sha256=A.chain(records),event=event,data=data)
    row = dict(body,record_sha256=A.digest(body))
    stream.write(A.encoded(row).decode()+'\n'); stream.flush(); os.fsync(stream.fileno()); records.append(row)
    return row


def finish(stream, records, status, elapsed, **details):
    if len(records) != 1 or records[0]['event'] != 'intent' or status not in ('completed','failed'):
        raise ValueError('exactly one pending supplemental intent required')
    A.nonnegative(elapsed)
    if elapsed > SECONDS: status = 'failed'
    return append(stream,records,'finish',dict(status=status,observed_seconds=elapsed,
        charged_seconds=max(SECONDS,elapsed) if status=='failed' else elapsed,
        neural_forwards=0,native_applies=0,optimizer_updates=0,numerical_fits=0,paid_spend_usd=0.,**details))


def run(path, execute=False):
    path = Path(path).resolve()
    with A.lease() as (_,parent_records,current):
        charged = parent_state(parent_records,current); value = descriptor(path,current)
        preview = dict(status='preview-only',descriptor=A.pin(path),parent=PARENT,parent_final_chain=PARENT_CHAIN,
            shared_analysis_charged_before=charged,reserved_seconds=SECONDS,
            shared_analysis_max_after=charged+SECONDS,argv=value['argv'],outputs=value['outputs'])
        if not execute: return preview
        with JOURNAL.open('x+') as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB); records=[]
            append(stream,records,'intent',dict(**preview,source=A.pin(__file__),input_pins=value['pins'],
                prior_v1=A.recovery_parent(),historical_parent_pins=A.PARENT_PINS,
                historical_parent_chains=A.PARENT_CHAINS,prior_exposure=A.PRIOR_EXPOSURE))
            started=time.monotonic(); active=[False]; guard=None; error=None; status='failed'; outputs=[]
            def audit(event,args):
                if active[0]: audit_event(event,args)
            oldargv=sys.argv[:];sys.dont_write_bytecode=True
            for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
            try:
                if any(x.split('.')[0] in BLOCKED for x in sys.modules): raise RuntimeError('neural/fit library already loaded')
                sys.addaudithook(audit);active[0]=True
                spec=importlib.util.spec_from_file_location('frozen_supplemental_guard',GUARD)
                E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
                guard=E.Guard(max(.001,SECONDS-(time.monotonic()-started)))
                with guard:
                    sys.argv=value['argv'][:]
                    try: runpy.run_path(str(VERIFIER),run_name='__main__')
                    except SystemExit as exited:
                        if exited.code not in (None,0): raise
                    A.verify_pins(value['pins']);parent_state(parent_records,current)
                    if not OUTPUT.is_file(): raise ValueError('declared supplemental result missing')
                    outputs=[A.pin(OUTPUT)]
                status='completed'
            except BaseException as caught: error=dict(type=type(caught).__name__,message=str(caught))
            finally: active[0]=False;sys.argv=oldargv
            elapsed=time.monotonic()-started
            return finish(stream,records,status,elapsed,error=error,guard=guard.receipt() if guard else None,
                outputs=outputs,shared_analysis_charged_before=charged,
                shared_analysis_charged_after=charged+(max(SECONDS,elapsed) if status=='failed' or elapsed>SECONDS else elapsed))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--descriptor',required=True);p.add_argument('--execute',action='store_true')
    a=p.parse_args();result=run(a.descriptor,a.execute);print(json.dumps(result,allow_nan=False))
    return 0 if result.get('status',result.get('data',{}).get('status')) in ('preview-only','completed') else 1


if __name__=='__main__':sys.exit(main())
