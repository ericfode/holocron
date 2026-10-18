"""Explicit campaign routing around unchanged binding-transfer science.

No automatic execution. Prelabel is public/source metadata only. Actual stages
reserve the NEW campaign before the strict routing audit; frozen workers own
their original guards, data admission, objectives, counters and output writes.
"""
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/'experiments'/'binding-transfer-v2'
ACCOUNTING='binding_transfer_next_accounting'
ACCOUNTING_SHA256='ba6a9938210db820b16306afa36561bcd4a4abffa7dac1d9a388623f5bec6215'
PLAN_SHA256='0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f'
SCIENCE={
    'binding_transfer_fit.py':'85e77bdef0fefb18d23040a40f6be8121e82a724feba47124b76b622c8cde7ce',
    'binding_transfer_prep.py':'62ef18971fb80119036db68596144ac5cb62f55aca55976dac75704120d110ff',
    'binding_transfer_baselines.py':'750043948139436b32bfc082e17c8015e9ba84c87103b257c89cca586c15116b',
    'public_input_binding_model_v1.py':'4d53c2fb0b707c8b0982795413eabb9f198bfdd5794be27fb8dde0a42e1e929b',
    'binding_transfer_data.py':'7e0af843d21500f78307c95c6ad7f56f1d731d69c5a901725e81e0421ab5afb6',
    'effect_identifiability_fit.py':'90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765',
    'binding_transfer_accounting.py':'51ad01b175d5367e27b5e0f8eebb91d2a417f73069cfdd865269cff714f012cd',
}


def pin(path):
    p=Path(path).resolve();raw=p.read_bytes()
    return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def require(value,message):
    if not value:raise ValueError(message)
def actual_argv():return[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
def verify_science():
    pins=[]
    for name,expected in SCIENCE.items():
        value=pin(HERE/name);require(value['sha256']==expected,'frozen scientific source changed: '+name);pins.append(value)
    return pins
def load_accounting():return importlib.import_module(ACCOUNTING)
def modules():
    # These modules have stdlib-only top-level imports. No model/NumPy call.
    return tuple(importlib.import_module(name)for name in('binding_transfer_fit','binding_transfer_prep','binding_transfer_baselines'))


def routing_audit(A,F,P,B,argv=None):
    science=verify_science();accounting=pin(A.__file__)
    require(accounting['sha256']==ACCOUNTING_SHA256,'new accounting source changed or is not frozen')
    require(Path(A.LEDGER).resolve()==ROOT/'campaign-ledger.jsonl','routing must use canonical NEW ledger')
    require(Path(F.__file__).resolve()==HERE/'binding_transfer_fit.py'and Path(P.__file__).resolve()==HERE/'binding_transfer_prep.py'and Path(B.__file__).resolve()==HERE/'binding_transfer_baselines.py','wrong loaded worker module')
    require(B.F is F and F.accounting()is A and P.A is A,'shared worker objects are not explicitly routed to new accounting')
    if argv is not None:require(argv==actual_argv(),'actual wrapper argv differs from reserved command')
    return dict(schema='jepa-binding-transfer-v2-routing/1',wrapper=pin(__file__),accounting=accounting,science=science,
        ledger_path=str(A.LEDGER),bindings=['F.accounting -> NEW A','P.A -> NEW A','P.run ledger -> NEW A.LEDGER','F.stage_metadata entrypoint -> this wrapper'],
        unchanged='Documents, world plan, graph, inputs, splits, labels, admission gates, loss, scalers, schedules, optimizer, guards and budgets remain frozen.',
        exposure=dict(optimizer_updates=5400,neural_forwards=5436,training_forwards=5400,evaluation_forwards=36,numerical_fits=64,export_forwards=0,paid_jobs=0),semantic_validated=False)


@contextmanager
def routed(A=None,prelabel=False):
    """Scoped routing only. Strict byte/route checks run AFTER durable start."""
    A=load_accounting()if A is None else A;F,P,B=modules()
    old_accounting,old_metadata,old_prep,old_start=F.accounting,F.stage_metadata,P.A,A.start
    original_routes=bool(getattr(old_accounting,'__module__',None)=='binding_transfer_fit'and getattr(old_accounting,'__name__',None)=='accounting'
        and getattr(old_metadata,'__module__',None)=='binding_transfer_fit'and getattr(old_metadata,'__name__',None)=='stage_metadata'
        and getattr(old_prep,'__name__',None)=='binding_transfer_accounting'and B.F is F)
    if prelabel:require(original_routes,'already-loaded worker has an unexpected accounting/metadata route')
    def metadata(current,rows,plan,out,progress,_frozen_entrypoint):
        return old_metadata(current,rows,plan,out,progress,Path(__file__))
    def start(stream,rows,stage,meta):
        value=old_start(stream,rows,stage,meta)
        require(original_routes,'already-loaded worker has an unexpected accounting/metadata route')
        routing_audit(A,F,P,B,meta['argv'])
        return value
    F.accounting=lambda:A;F.stage_metadata=metadata;P.A=A;A.start=start
    try:yield A,F,P,B
    finally:F.accounting=old_accounting;F.stage_metadata=old_metadata;P.A=old_prep;A.start=old_start


def prelabel(native_plan,out):
    require(out.resolve()==ROOT/'learner-prepared-v1.json','one new-campaign prelabel output required')
    sidecar=ROOT/'prelabel-routing-v1.json'
    require(not out.exists()and not sidecar.exists(),'prelabel outputs are exclusive; preserve prior preparation')
    require(pin(native_plan)['sha256']==PLAN_SHA256,'exact unchanged26-world scientific plan required')
    native=json.loads(native_plan.read_text())
    for expected in native['source_pins']:require(pin(expected['path'])==expected,'scientific plan embedded source pin changed')
    with routed(prelabel=True)as(A,F,P,B):
        audit=routing_audit(A,F,P,B);value=F.prepare(native_plan,out)
        audit.update(prepared=pin(out),native_plan=pin(native_plan),worlds=len(native['worlds']),cards=len(native['cards']),
            route_phase='Public/source metadata only; no ledger initialization, native application, numerical fit or neural execution.')
        F.write(sidecar,audit)
        return dict(prepared=pin(out),routing=pin(sidecar),parameters=value['parameters'],no_science_execution=True)


def dispatch(args):
    if args.command=='prelabel':return prelabel(args.native_plan,args.out)
    with routed()as(A,F,P,B):
        if args.command=='prep':return P.run(args.native_receipt,args.journal,args.native_plan,args.prepared,args.out,ledger=A.LEDGER,argv=actual_argv())
        if args.command=='fit':return F.execute(args.plan,args.out,args.progress)
        if args.command=='baselines':return B.run(args.plan,args.out,args.progress)
    raise ValueError('unallocated wrapper stage')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prelabel');a.add_argument('--native-plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('prep')
    for name in('native-receipt','journal','native-plan','prepared','out'):a.add_argument('--'+name,type=Path,required=True)
    for command in('fit','baselines'):
        a=sub.add_parser(command)
        for name in('plan','out','progress'):a.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(dispatch(p.parse_args()),indent=2,allow_nan=False))

if __name__=='__main__':main()
