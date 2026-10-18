"""Once-only deterministic analyses under shared accounting. Preview by default."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import time

import public_input_binding_accounting as A

GUARD = A.HERE/'effect_identifiability_fit.py'
GUARD_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
BLOCKED = {'torch','tinygrad','tensorflow','jax','jaxlib','keras','transformers','cupy','sklearn','statsmodels'}


def audit_event(event,args):
    if event=='import' and str(args[0]).split('.')[0] in BLOCKED:raise RuntimeError('neural/fit library import forbidden')
    if event.startswith(('socket.','subprocess.','os.exec','os.spawn','os.posix_spawn'))or event in('os.system','os.fork','os.forkpty','os.killpg'):
        raise RuntimeError('network/process execution forbidden')
    if event=='os.kill'and args!=(os.getpid(),signal.SIGALRM):raise RuntimeError('only own guard SIGALRM allowed')


def descriptor(path, current):
    path=Path(path).resolve(); value=json.loads(path.read_text()); stage=value['stage']
    if stage not in A.ANALYSIS_STAGES: raise ValueError('only frozen deterministic analysis stages allowed')
    argv=value['argv']
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str)for x in argv) or not Path(argv[0]).is_absolute() or Path(argv[0]).suffix!='.py':
        raise ValueError('structured absolute Python-script argv required')
    if dict(argv=argv,outputs=value['outputs'])!=current['config']['analysis_commands'][stage]:
        raise ValueError('analysis input/output selection differs from pre-native frozen command')
    A.verify_pins(value['pins']); frozen={p['path']:p for p in current['config']['pins']}
    for required in (Path(argv[0]),Path(__file__),GUARD):
        if frozen.get(str(required.resolve()))!=A.pin(required): raise ValueError('analysis script/runner/guard must be frozen before native work')
    if A.pin(GUARD)['sha256']!=GUARD_SHA: raise ValueError('own-process guard changed')
    if not value['outputs']: raise ValueError('new outputs must be explicit')
    for output in value['outputs']:
        p=Path(output)
        if not p.is_absolute() or not p.resolve().is_relative_to(A.CAMPAIGN.resolve()) or p.exists():
            raise ValueError('outputs must be new campaign-local paths')
    if 'native-collect' not in current['completed_stages']: raise ValueError('native collection must complete first')
    if stage in current['seen_stages']:raise ValueError('analysis stage already attempted; no retry')
    if stage=='analysis-verification' and 'analysis-controls' not in current['completed_stages']:
        raise ValueError('independent verification follows completed controls')
    return value


def run(path,execute=False):
    path=Path(path).resolve()
    with A.lease() as (stream,records,current):
        value=descriptor(path,current); stage=value['stage']; seconds=A.ANALYSIS_STAGES[stage]
        preview=dict(status='preview-only',descriptor=A.pin(path),stage=stage,seconds=seconds,argv=value['argv'],outputs=value['outputs'])
        if not execute:return preview
        target=A.CAMPAIGN/(stage+'-receipt.json')
        if target.exists():raise FileExistsError('stage receipt exists; never replace')
        A.start(stream,records,stage,dict(descriptor=A.pin(path),argv=value['argv'],input_pins=value['pins']))
        started=time.monotonic(); active=[False]; error=None; status='failed'; guard=None; outputs=[]
        def audit(event,args):
            if not active[0]:return
            audit_event(event,args)
        oldargv=sys.argv[:];sys.dont_write_bytecode=True
        for key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
        try:
            if any(name.split('.')[0]in BLOCKED for name in sys.modules):raise RuntimeError('neural/fit library already loaded')
            sys.addaudithook(audit);active[0]=True
            spec=importlib.util.spec_from_file_location('frozen_public_input_guard',GUARD);E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
            guard=E.Guard(max(.001,seconds-(time.monotonic()-started)))
            with guard:
                sys.argv=value['argv'][:]
                try:runpy.run_path(value['argv'][0],run_name='__main__')
                except SystemExit as exited:
                    if exited.code not in(None,0):raise
                A.verify_pins(value['pins']); A.verify_pins(current['config']['pins']); A.verify_parents()
                for name in value['outputs']:
                    p=Path(name)
                    if not p.exists():raise ValueError('declared output missing')
                    outputs.extend(A.pin(q)for q in sorted(p.rglob('*'))if q.is_file())if p.is_dir()else outputs.append(A.pin(p))
            status='completed'
        except BaseException as caught:error=dict(type=type(caught).__name__,message=str(caught))
        finally:active[0]=False;sys.argv=oldargv
        elapsed=time.monotonic()-started
        if elapsed>seconds:status='failed';error=error or dict(type='WallLimit',message='stage allocation exceeded')
        receipt=dict(status=status,error=error,stage=stage,active_seconds=elapsed,outputs=outputs,
            guard=guard.receipt()if guard else None,descriptor=A.pin(path),neural_forwards=0,native_applies=0,
            optimizer_updates=0,numerical_fits=0,paid_jobs=0,paid_spend_usd=0.)
        with target.open('x')as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        receipt['accounting']=A.finish(stream,records,status,elapsed,proofs=[A.pin(target)])
        return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--descriptor',required=True);p.add_argument('--execute',action='store_true')
    a=p.parse_args();result=run(a.descriptor,a.execute);print(json.dumps(result,allow_nan=False));return 0 if result['status']in('preview-only','completed')else 1


if __name__=='__main__':sys.exit(main())
