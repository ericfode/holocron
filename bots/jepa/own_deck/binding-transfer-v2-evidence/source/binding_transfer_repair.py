"""Explicit metadata-repair routing around unchanged binding-transfer science.

No automatic execution. Routing metadata reuses the original preparation after
native exposure, without reconstructing it. Actual stages
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
ROOT=HERE.parents[3]/'experiments'/'binding-transfer-repair-v1'
ACCOUNTING='binding_transfer_repair_accounting'
ACCOUNTING_SHA256='761b62596c76ed3f61dfee1f348fdd54a41a8e92d756eade8ecb90b3f9aa96bb'
DATA_MODULE='binding_transfer_data_v2'
DATA_SHA256='b98316c7b1210fdd1f5db4e993f5d8738e25db46334f454b588f7c68324135bc'
BASELINE_SHA256='13f2ed30060ab8618bcb87a874c9a41123284eac00cec1bfb7ae345d3e379e4e'
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
    for name,expected in ((DATA_MODULE+'.py',DATA_SHA256),('binding_transfer_repair_baselines.py',BASELINE_SHA256)):
        value=pin(HERE/name);require(value['sha256']==expected,'repair source changed: '+name);pins.append(value)
    return pins
def load_accounting():return importlib.import_module(ACCOUNTING)
def modules():
    # These modules have stdlib-only top-level imports. No model/NumPy call.
    return tuple(importlib.import_module(name)for name in('binding_transfer_fit','binding_transfer_prep','binding_transfer_repair_baselines'))


def routing_audit(A,F,P,B,argv=None):
    science=verify_science();accounting=pin(A.__file__)
    require(accounting['sha256']==ACCOUNTING_SHA256,'new accounting source changed or is not frozen')
    require(Path(A.LEDGER).resolve()==ROOT/'campaign-ledger.jsonl','routing must use canonical NEW ledger')
    require(Path(F.__file__).resolve()==HERE/'binding_transfer_fit.py'and Path(P.__file__).resolve()==HERE/'binding_transfer_prep.py'and Path(B.__file__).resolve()==HERE/'binding_transfer_repair_baselines.py','wrong loaded worker module')
    require(B.F is F and F.accounting()is A and P.A is A,'shared worker objects are not explicitly routed to new accounting')
    if argv is not None:require(argv==actual_argv(),'actual wrapper argv differs from reserved command')
    return dict(schema='jepa-binding-transfer-repair-routing/1',wrapper=pin(__file__),accounting=accounting,science=science,
        ledger_path=str(A.LEDGER),bindings=['F.accounting -> NEW A','P.A -> NEW A','P.run ledger -> NEW A.LEDGER','F.stage_metadata entrypoint -> this wrapper','P.prepare_outputs scoped binding_transfer_data import -> metadata-only v2 converter','P.save_json manifest -> explicit repair provenance'],
        unchanged='Documents, world plan, graph, inputs, splits, labels, admission gates, loss, scalers, schedules and optimizer remain frozen. Baseline wall guard changes10to5seconds only.',
        exposure=dict(optimizer_updates=5400,neural_forwards=5436,training_forwards=5400,evaluation_forwards=36,numerical_fits=64,export_forwards=0,paid_jobs=0),semantic_validated=False)


@contextmanager
def converter_alias(module=None):
    module=importlib.import_module(DATA_MODULE)if module is None else module
    require(pin(module.__file__)['sha256']==DATA_SHA256,'metadata-only converter source changed')
    sentinel=object();previous=sys.modules.get('binding_transfer_data',sentinel)
    sys.modules['binding_transfer_data']=module
    try:
        require(importlib.import_module('binding_transfer_data')is module,'explicit converter import identity differs')
        yield module
    finally:
        if previous is sentinel:sys.modules.pop('binding_transfer_data',None)
        else:sys.modules['binding_transfer_data']=previous


@contextmanager
def routed(A=None,prelabel=False):
    """Scoped routing only. Strict byte/route checks run AFTER durable start."""
    A=load_accounting()if A is None else A;F,P,B=modules()
    old_accounting,old_metadata,old_prep,old_start=F.accounting,F.stage_metadata,P.A,A.start
    old_outputs,old_save=P.prepare_outputs,P.save_json
    original_routes=bool(getattr(old_accounting,'__module__',None)=='binding_transfer_fit'and getattr(old_accounting,'__name__',None)=='accounting'
        and getattr(old_metadata,'__module__',None)=='binding_transfer_fit'and getattr(old_metadata,'__name__',None)=='stage_metadata'
        and getattr(old_prep,'__name__',None)=='binding_transfer_accounting'and B.F is F
        and getattr(old_outputs,'__module__',None)=='binding_transfer_prep'and getattr(old_outputs,'__name__',None)=='prepare_outputs'
        and getattr(old_save,'__module__',None)=='binding_transfer_prep'and getattr(old_save,'__name__',None)=='save_json')
    if prelabel:require(original_routes,'already-loaded worker has an unexpected accounting/metadata route')
    def metadata(current,rows,plan,out,progress,_frozen_entrypoint):
        return old_metadata(current,rows,plan,out,progress,Path(__file__))
    def start(stream,rows,stage,meta):
        value=old_start(stream,rows,stage,meta)
        require(original_routes,'already-loaded worker has an unexpected accounting/metadata route')
        routing_audit(A,F,P,B,meta['argv'])
        return value
    def outputs(*args,**kwargs):
        # Called by frozen P.run ONLY from inside its5-second own-process guard.
        with converter_alias():return old_outputs(*args,**kwargs)
    def save(path,value):
        if value.get('schema')=='jepa-binding-transfer-data/1':
            value=dict(value);extras=[pin(__file__),pin(A.__file__),pin(HERE/(DATA_MODULE+'.py')),pin(HERE/'binding_transfer_repair_baselines.py')]
            existing={p['path']:p for p in value['source_pins']}
            for expected in extras:existing[expected['path']]=expected
            value['source_pins']=list(existing.values());value['repair_provenance']=dict(schema='jepa-binding-transfer-metadata-repair/1',sources=extras,old_converter=pin(HERE/'binding_transfer_data.py'),scope='Alias-registry provenance only: missing setCodes stays unknown; no feature/label/mask/gate change. Successful v2 native evidence reused, no new Engine.apply.')
        return old_save(path,value)
    F.accounting=lambda:A;F.stage_metadata=metadata;P.A=A;A.start=start;P.prepare_outputs=outputs;P.save_json=save
    try:yield A,F,P,B
    finally:F.accounting=old_accounting;F.stage_metadata=old_metadata;P.A=old_prep;A.start=old_start;P.prepare_outputs=old_outputs;P.save_json=old_save


def route_metadata(native_plan,prepared,out):
    require(out.resolve()==ROOT/'repair-routing-v1.json','one new repair metadata output required')
    require(not out.exists(),'repair metadata output is exclusive')
    require(pin(native_plan)['sha256']==PLAN_SHA256,'exact unchanged26-world scientific plan required')
    native=json.loads(native_plan.read_text())
    for expected in native['source_pins']:require(pin(expected['path'])==expected,'scientific plan embedded source pin changed')
    with routed(prelabel=True)as(A,F,P,B):
        audit=routing_audit(A,F,P,B);value=F.read(prepared);F.E.verify_pins(value['pins'])
        require(value['source_sha256']==SCIENCE['binding_transfer_fit.py']and value['config']==F.CONFIG,'original prepared science/config differs')
        audit.update(prepared=pin(prepared),native_plan=pin(native_plan),worlds=len(native['worlds']),cards=len(native['cards']),
            route_phase='Metadata repair prepared after successful native exposure and failed provenance conversion. Original public program preparation reused byte-exact; no retokenization, new collection, tuning or model call.')
        out.parent.mkdir(parents=True,exist_ok=True);F.write(out,audit)
        return dict(routing=pin(out),reused_prepared=pin(prepared),parameters=value['parameters'],no_science_execution=True)


def dispatch(args):
    if args.command=='route':return route_metadata(args.native_plan,args.prepared,args.out)
    with routed()as(A,F,P,B):
        if args.command=='prep':return P.run(args.native_receipt,args.journal,args.native_plan,args.prepared,args.out,ledger=A.LEDGER,argv=actual_argv())
        if args.command=='fit':return F.execute(args.plan,args.out,args.progress)
        if args.command=='baselines':return B.run(args.plan,args.out,args.progress)
    raise ValueError('unallocated wrapper stage')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('route');a.add_argument('--native-plan',type=Path,required=True);a.add_argument('--prepared',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('prep')
    for name in('native-receipt','journal','native-plan','prepared','out'):a.add_argument('--'+name,type=Path,required=True)
    for command in('fit','baselines'):
        a=sub.add_parser(command)
        for name in('plan','out','progress'):a.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(dispatch(p.parse_args()),indent=2,allow_nan=False))

if __name__=='__main__':main()
