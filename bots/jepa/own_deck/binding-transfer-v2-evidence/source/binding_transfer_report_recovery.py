"""Zero-neural reconstruction of a failed final JSON report from saved arrays.

No fit retry, model construction, forward, optimizer or native action exists in
the recovery command. The separate baseline command reuses the frozen5s worker
with only a scoped JSON-scalar writer and new accounting route.
"""
import os
for _key in('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]/'experiments'/'binding-transfer-report-recovery-v1'
ACCOUNTING_SHA='b212f83d72e6e2eb2feb248d14dce4fbf2a4c8b3e468a2a22c9810cf051e3acb'
FROZEN={'binding_transfer_fit.py':'85e77bdef0fefb18d23040a40f6be8121e82a724feba47124b76b622c8cde7ce',
    'effect_identifiability_fit.py':'90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765',
    'binding_transfer_repair_baselines.py':'13f2ed30060ab8618bcb87a874c9a41123284eac00cec1bfb7ae345d3e379e4e'}
ARMS=('C0R0','C1R0','C0R1','C1R1','ID-only','untrained-typed');SEEDS=(17,29,43)
BLOCKED=('torch','tensorflow','jax','keras','pytorch_lightning')


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def read(path):return json.loads(Path(path).read_text())
def require(value,message):
    if not value:raise ValueError(message)
def accounting():return importlib.import_module('binding_transfer_report_accounting')
def argv():return[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
def verify_sources(A):
    require(pin(A.__file__)['sha256']==ACCOUNTING_SHA and Path(A.LEDGER).resolve()==ROOT/'campaign-ledger.jsonl','exact new zero-neural accounting route required')
    for name,expected in FROZEN.items():require(pin(HERE/name)['sha256']==expected,'frozen scientific source changed: '+name)


def native_json(value,np=None):
    """Convert NumPy scalar leaves only; arrays/unknown objects remain errors."""
    if np is not None and isinstance(value,np.generic):return native_json(value.item(),np)
    if isinstance(value,dict):return{native_json(k,np):native_json(v,np)for k,v in value.items()}
    if isinstance(value,(list,tuple)):return[native_json(v,np)for v in value]
    if value is None or type(value)in(bool,int,float,str):return value
    raise TypeError('unsupported JSON object; no array/string fallback: '+type(value).__name__)


def write_new(path,value,np=None):
    with Path(path).open('x')as stream:
        json.dump(native_json(value,np),stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def inventory_paths(args):
    paths=[args.plan,args.progress,args.failed_ledger,args.failed_receipt]
    names=['contract.json','consumed-inputs.npz','program-inputs.npz','training-schedule.npz']
    for seed in SEEDS:
        names.append(f's{seed}-initial-checkpoint.npz')
        for arm in ARMS:
            names.append(f's{seed}-{arm}-checkpoint.npz')
            for step in(0,300):names.append(f's{seed}-{arm}-step{step}-predictions.npz')
    return paths+[args.fit_dir/name for name in names]


def audit_event(event,values):
    if event=='import'and str(values[0]).split('.')[0]in BLOCKED:raise RuntimeError('neural import forbidden in saved-report recovery')
    if event in('subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.exec')or event.startswith('socket.'):raise RuntimeError('process/network forbidden in saved-report recovery')


def npz(np,path):
    with np.load(path,allow_pickle=False)as values:return{k:values[k].copy()for k in values.files}


def recover_saved(np,A,args,allowed,out):
    F=importlib.import_module('binding_transfer_fit')
    require(F.ARMS==ARMS and F.SEEDS==SEEDS,'frozen arm/seed matrix changed')
    required=inventory_paths(args)
    for path in required:
        expected=allowed.get(str(path.resolve()));require(expected is not None,'saved input lacks exact frozen pin: '+str(path));A.verify_pin(expected)
    expected_names={p.name for p in required if p.parent.resolve()==args.fit_dir.resolve()}
    actual_names={p.name for p in args.fit_dir.iterdir()if p.is_file()}
    require(actual_names in(expected_names,expected_names|{'receipt.json'}),'saved failed-fit inventory differs; no partial/missing result replacement')
    plan=read(args.plan);F.E.verify_pins(plan['pins']);contract=read(args.fit_dir/'contract.json')
    require(contract['plan']==pin(args.plan)and contract['config']==F.CONFIG,'saved scientific contract differs')
    for path in(Path(plan['dataset']),Path(plan['manifest'])):
        require(str(path.resolve())in allowed,'sealed dataset/manifest must be frozen recovery inputs');A.verify_pin(allowed[str(path.resolve())])
    arrays=npz(np,plan['dataset']);manifest=read(plan['manifest']);F.validate_data(arrays,manifest,plan)
    prefix=A.progress_counts(args.progress,'fit');require(prefix==dict(optimizer_updates=5400,neural_forwards=5436,training_forwards=5400,evaluation_forwards=36),'full durable completed optimizer/forward prefix required')
    failed=read(args.failed_receipt);ledger=[json.loads(line)for line in args.failed_ledger.read_text().splitlines()];last=ledger[-1]
    require(failed['status']=='failed'and failed['error']['type']=='TypeError','original failed serialization receipt required')
    require(last['event']=='stage-finish'and last['data']['stage']=='fit'and last['data']['status']=='failed'and last['data']['observed']['neural_forwards']is None and last['data']['observed']['optimizer_updates']is None,'closed failed ledger and null original observations must remain intact')
    results={}
    for seed in SEEDS:
        initial=npz(np,args.fit_dir/f's{seed}-initial-checkpoint.npz');master=F.named_state_sha256(initial)
        for arm in ARMS:
            evaluations={}
            for step in(0,300):
                predictions=npz(np,args.fit_dir/f's{seed}-{arm}-step{step}-predictions.npz')
                require(predictions['source'].shape==(26,9)and predictions['branch'].shape==(26,8,7)and predictions['card_vectors'].shape==(7,16),'saved prediction shapes differ')
                for key in('source_cards','state_families','selected_candidate_indices'):require(np.array_equal(predictions[key],arrays[key]),'saved prediction row order differs')
                require(all(np.isfinite(predictions[k]).all()for k in('source','branch','card_vectors')),'nonfinite saved predictions')
                evaluations[str(step)]=dict(cells=F.evaluate(predictions['source'],predictions['branch'],arrays,manifest,plan),narrow_estimands=F.narrow_estimands(predictions['source'],predictions['branch'],arrays,manifest,plan))
            checkpoint=args.fit_dir/f's{seed}-{arm}-checkpoint.npz';weights=npz(np,checkpoint)
            require(set(weights)==set(initial)and all(v.shape==initial[n].shape and v.dtype==initial[n].dtype and np.isfinite(v).all()for n,v in weights.items()),'saved named checkpoint differs')
            movement={n:dict(delta_l2=float(np.linalg.norm((v-initial[n]).astype(np.float64))),changed=int(np.count_nonzero(v!=initial[n])),elements=v.size)for n,v in weights.items()}
            results[f's{seed}:{arm}']=dict(evaluations=evaluations,checkpoint=pin(checkpoint),initial_state_sha256=master,master_initial_state_sha256=master,
                initial_hash_basis='Recomputed saved per-seed master; frozen original worker asserts strict per-arm loaded equality before each first forward. Per-arm transient hashes were not durably saved.',
                last_step_preclip_gradients=None,last_step_preclip_gradients_unrecoverable='Ephemeral final gradient summaries were lost before original result JSON could be serialized; no backward/replay permitted.',weight_movement=movement)
    provenance=dict(failed_fit_ledger=pin(args.failed_ledger),failed_fit_receipt=pin(args.failed_receipt),fit_progress=pin(args.progress))
    inventory=dict(schema='jepa-saved-fit-report-inventory/1',pins=[allowed[str(p.resolve())]for p in required],artifact_count=len(required)-4,verified=True)
    write_new(out/'source-inventory.json',inventory,np)
    result=dict(status='recovered-from-saved-artifacts',original_fit_status='failed',config=F.CONFIG,
        counts=dict(prefix,backwards=5400,export_forwards=0),counts_scope='Historical durable saved forward intents/completed optimizer updates; backward count follows the unchanged completed-step code path. These are not new campaign observations and do not replace original null observed counters.',
        results=results,factorial_contrasts=F.factorial_contrasts(results),true_label_hashes={k:F.sha_array(arrays[k])for k in('targets','target_mask','source_targets','source_mask','selected_candidate_indices')},
        true_label_hashes_scope='Recomputed from byte-pinned sealed arrays; original transient hash dictionary was not durably saved.',
        all_inputs_unchanged=True,all_inputs_unchanged_scope='Original source pins, sealed data and complete saved artifact inventory verified now; no original failed artifact is written.',
        semantic_validated=False,task=F.CONFIG['task'],recovery_provenance=provenance,source_inventory=pin(out/'source-inventory.json'),
        recovery_calls=A.zero_counts(),chosen_subset_scope='Same actual applied actions restricted to chosen anchors; not historical conditional-objective replication.',
        prior_baselines_scope='Fresh matched C0R0/ID/untrained saved runs. Prior wrong/shuffle/checkpoint results remain historical descriptive evidence; no extra old-checkpoint forwards.')
    write_new(out/'result.json',result,np)
    for path in required:A.verify_pin(allowed[str(path.resolve())])
    return dict(result=pin(out/'result.json'),inventory=pin(out/'source-inventory.json'),historical_saved_prefix=prefix,new_calls=A.zero_counts())


def run_recover(args):
    A=accounting()
    with A.lease()as(stream,rows,current):
        allowed={p['path']:p for p in current['config']['pins']};required=inventory_paths(args);receipt_path=args.out.parent/(args.out.name+'-stage-receipt.json')
        meta=dict(argv=argv(),outputs=[str(args.out.resolve()),str(receipt_path.resolve())],input_pins=[allowed[str(p.resolve())]for p in required if str(p.resolve())in allowed],guard=dict(A.GUARD))
        started=time.monotonic();guard=None;status='failed';error=None;created=False;outputs=None;active=[False]
        def audit(event,values):
            if active[0]:audit_event(event,values)
        sys.addaudithook(audit)
        try:
            A.start(stream,rows,'recover',meta);verify_sources(A)
            require(not args.out.exists()and not receipt_path.exists(),'exclusive recovery outputs; no retry/reset')
            require(not any(name.split('.')[0]in BLOCKED for name in sys.modules),'no preloaded neural library permitted')
            E=importlib.import_module('effect_identifiability_fit');remaining=3.-(time.monotonic()-started);require(remaining>0,'recovery startup exhausted3seconds')
            guard=E.Guard(remaining);args.out.mkdir(parents=True);created=True;active[0]=True
            with guard:
                import numpy as np
                outputs=recover_saved(np,A,args,allowed,args.out)
            status='completed'
        except BaseException as exc:
            pending=A.state(rows)['pending']
            if pending is None or pending['stage']!='recover'or pending['owner_pid']!=os.getpid():raise
            error=dict(type=type(exc).__name__,message=str(exc))
        finally:active[0]=False
        elapsed=time.monotonic()-started
        if elapsed>3:status='failed';error=error or dict(type='BudgetExceeded',message='saved report recovery exceeded3seconds')
        receipt=dict(status=status,error=error,active_seconds=elapsed,guard=guard.receipt()if guard else None,outputs=outputs,observed=A.zero_counts(),source=pin(__file__),semantic_validated=False,accounting_authority='New canonical ledger controls final status including receipt/proof write time; original failed fit remains failed.')
        proofs=[]
        if created:proofs.extend(pin(p)for p in sorted(args.out.rglob('*'))if p.is_file())
        try:write_new(receipt_path,receipt);proofs.append(pin(receipt_path))
        except BaseException as exc:status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        finished=A.finish(stream,rows,status,elapsed,observed=A.zero_counts(),proofs=proofs,cleanup_verified=True,execution_ended=True)
        require(status=='completed'and'recover'in finished['completed_stages'],'failed bounded recovery retained; authoritative ledger controls status: '+str(error))
        return receipt


@contextmanager
def baseline_route(A):
    F=importlib.import_module('binding_transfer_fit');B=importlib.import_module('binding_transfer_repair_baselines')
    original=(F.accounting,F.stage_metadata,F.write,A.start);old_accounting,old_metadata,old_write,old_start=original
    def metadata(current,rows,plan,out,progress,_entry):return old_metadata(current,rows,plan,out,progress,Path(__file__))
    def start(stream,rows,stage,value):
        result=old_start(stream,rows,stage,value);verify_sources(A);require(B.F is F and F.accounting()is A and value['argv']==argv(),'explicit baseline accounting/wrapper route differs');return result
    def scalar_write(path,value):return old_write(path,native_json(value,sys.modules.get('numpy')))
    F.accounting=lambda:A;F.stage_metadata=metadata;F.write=scalar_write;A.start=start
    try:yield B
    finally:F.accounting=old_accounting;F.stage_metadata=old_metadata;F.write=old_write;A.start=old_start


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('recover')
    for name in('plan','fit-dir','progress','failed-ledger','failed-receipt','out'):a.add_argument('--'+name,type=Path,required=True)
    a=sub.add_parser('baselines')
    for name in('plan','out','progress'):a.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.command=='recover':value=run_recover(args)
    else:
        with baseline_route(accounting())as B:value=B.run(args.plan,args.out,args.progress)
    print(json.dumps(native_json(value,sys.modules.get('numpy')),allow_nan=False))

if __name__=='__main__':main()
