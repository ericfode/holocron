"""Once-only five-second saved-native preparation under the campaign lease.

No native applications, neural forwards, optimizers or numerical fits. NumPy and
the pure converter are imported only after a durable reservation and wall guard.
The canonical ledger, including a failed full reservation, controls completion.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import time

import binding_transfer_accounting as A
import effect_identifiability_fit as E

HERE=Path(__file__).resolve().parent
SECONDS=5.
SCHEMA='jepa-binding-transfer-preparation/1'


def metadata(current,rows,inputs,out,argv):
    """Resolve expectations from frozen metadata without opening stage inputs."""
    allowed={p['path']:p for p in current['config']['pins']}
    for row in rows:
        if row['event']=='stage-finish'and row['data']['status']=='completed':
            for expected in row['data']['proofs']:allowed[expected['path']]=expected
            if row['data'].get('counter_proof'):
                expected=row['data']['counter_proof'];allowed[expected['path']]=expected
    expected=[allowed.get(str(Path(path).resolve()))for path in inputs]
    receipt=out.parent/(out.name+'-stage-receipt.json')
    value=dict(argv=argv,outputs=[str(out.resolve()),str(receipt.resolve())],input_pins=[p for p in expected if p is not None],guard=dict(A.GUARD))
    return value,expected,receipt


def save_json(path,value):
    with path.open('x')as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def prepare_outputs(native_receipt,journal,native_plan,prepared,out):
    """Pure conversion and sealing; called only inside the owned guard."""
    import numpy as np
    D=importlib.import_module('binding_transfer_data')
    F=importlib.import_module('binding_transfer_fit')
    plan=D.read(native_plan);receipt=D.read(native_receipt)
    A.require(receipt['collectionPlanSha256']==D.sha(native_plan),'exact native plan bytes differ')
    for item in plan['source_pins']:A.verify_pin(item)
    # This source-only gate precedes reading/measuring any native labels.
    D.quantity_support(plan)
    arrays,manifest=D.convert_receipt(receipt,plan,D.G.assembled_catalog(D.G.PINNED_KESSEL/'compiler/generated'),journal)
    dataset=out/'dataset.npz';manifest_path=out/'dataset.manifest.json';sealed=out/'sealed-fit-plan.json'
    np.savez_compressed(dataset,**arrays)
    sources=[Path(__file__),HERE/'test_binding_transfer_prep.py',HERE/'binding_transfer_data.py',HERE/'test_binding_transfer_data.py',HERE/'public_input_binding_model_v1.py',HERE/'public_input_binding_supplemental_verify.py',HERE/'effect_identifiability_fit.py',HERE/'whole_card_encoder.py',HERE/'actual_corpus_native_plan.py',HERE/'grounded_contrast_data.py',HERE/'binding_transfer_native_plan.py',HERE/'binding_transfer_native_collector/src/main.rs',native_plan,native_receipt,journal,prepared]
    manifest.update(artifact=A.pin(dataset),native_receipt=A.pin(native_receipt),journal=A.pin(journal),source_pins=[A.pin(p)for p in sources])
    save_json(manifest_path,manifest)
    A.require(manifest['fit_admitted']and manifest['quantity_support_gate']['passed'],'native conversion did not admit this frozen fit')
    sealed_value=F.seal(prepared,dataset,manifest_path,sealed)
    A.require(sealed_value['status']=='sealed-awaiting-root-GO'and sealed_value['support']['passed']and sealed_value['quantity_support']['passed']and sealed_value['input_audits']['C1R1']['conflict_count']==0,'sealed support/quantity/conflict admission differs')
    # Byte-check both original sources and newly sealed inputs after all writes.
    for item in manifest['source_pins']:A.verify_pin(item)
    E.verify_pins(sealed_value['pins'])
    return dict(dataset=A.pin(dataset),manifest=A.pin(manifest_path),sealed_fit_plan=A.pin(sealed),fit_admitted=True,
        native_recorded_applies=manifest['native_apply_calls'],quantity_support=manifest['quantity_support_gate'],semantic_validated=False)


def run(native_receipt,journal,native_plan,prepared,out,ledger=A.LEDGER,argv=None):
    native_receipt,journal,native_plan,prepared,out=map(Path,(native_receipt,journal,native_plan,prepared,out))
    argv=argv or[str(Path(sys.executable).resolve()),str(Path(__file__).resolve()),*sys.argv[1:]]
    with A.lease(ledger)as(stream,rows,current):
        meta,expected,stage_receipt=metadata(current,rows,[native_receipt,journal,native_plan,prepared],out,argv)
        started=time.monotonic();guard=E.Guard(SECONDS);status='failed';error=None;created=False;outputs=None
        try:
            # start appends/fsyncs before entrypoint, input and protection checks.
            A.start(stream,rows,'prep',meta)
            A.require(all(p is not None for p in expected),'all prep inputs must be frozen or pinned completed-stage outputs')
            A.require(not out.exists()and not stage_receipt.exists(),'preserve all previous outputs; no retry/reset')
            out.mkdir(parents=True);created=True
            remaining=SECONDS-(time.monotonic()-started)
            A.require(remaining>0,'prep startup exhausted its five-second allocation')
            guard=E.Guard(remaining)
            with guard:
                outputs=prepare_outputs(native_receipt,journal,native_plan,prepared,out)
            for item in meta['input_pins']:A.verify_pin(item)
            A.verify_links(current['config'])
            status='completed'
        except BaseException as exc:
            pending=A.state(rows)['pending']
            if pending is None or pending['stage']!='prep'or pending['owner_pid']!=os.getpid():raise
            error=dict(type=type(exc).__name__,message=str(exc))
        elapsed=time.monotonic()-started
        if elapsed>SECONDS:status='failed';error=error or dict(type='BudgetExceeded',message='prep exceeded five seconds')
        observed=A.zero_counts()
        receipt=dict(schema=SCHEMA,status=status,error=error,active_seconds=elapsed,observed=observed,guard=guard.receipt(),outputs=outputs,
            input_pins=meta['input_pins'],source=A.pin(__file__),semantic_validated=False,
            accounting_authority='Canonical campaign ledger controls status; a failed stage retains its full five-second reservation. No retries or credits.')
        receipt_pin=None
        try:
            A.verify_output_protection([str(stage_receipt.resolve())])
            stage_receipt.parent.mkdir(parents=True,exist_ok=True);save_json(stage_receipt,receipt);receipt_pin=A.pin(stage_receipt)
            if created:save_json(out/'receipt.json',receipt)
        except BaseException as exc:
            status='failed';error=dict(type=type(exc).__name__,message=str(exc),receipt_write_failed=True)
        proofs=([receipt_pin]if receipt_pin else[])
        if created:
            proofs.extend(A.pin(p)for p in sorted(out.rglob('*'))if p.is_file())
        # No child process is started by this stage. Guard exit joins its sampler.
        finished=A.finish(stream,rows,status,elapsed,observed,proofs,cleanup_verified=True,execution_ended=True)
        if status!='completed'or 'prep'not in finished['completed_stages']:
            raise RuntimeError('failed prep retained; authoritative ledger controls completion: '+str(error))
        return dict(receipt=receipt_pin,status='completed',accounting_last_record_sha256=finished['last_record_sha256'],charged=finished['charged'],observed=finished['observed'],outputs=outputs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('native-receipt','journal','native-plan','prepared','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--ledger',type=Path,default=A.LEDGER)
    a=parser.parse_args();print(json.dumps(run(a.native_receipt,a.journal,a.native_plan,a.prepared,a.out,a.ledger),allow_nan=False))


if __name__=='__main__':main()
