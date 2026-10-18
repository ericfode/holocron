import copy
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
sys.path.insert(0, '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck')
from embedding_geometry_audit import Guard
out=Path(__file__).resolve().parent
prior=json.loads((out/'feasibility-receipt.json').read_text())['aggregate_preparation_attempt_seconds']
def pin(p):
    p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
guard=Guard(out)
receipt=dict(status='failed',phase='fixed-module-generation',prior_preparation_seconds=prior,command=pin(__file__),neural_forwards=0,model_forward_calls=0,neighbor_metrics=0,native_calls=0,optimizer_updates=0,paid_spend_usd=0)
try:
    with guard:
        signal.setitimer(signal.ITIMER_REAL,20-prior)
        resource.setrlimit(resource.RLIMIT_CPU,(18,19))
        import independent_retrieval_module_controls as module
        manifest=module.generate(out)
        raw_manifest=out/'combined-controls.manifest.json'
        (out/'combined-controls.generated-raw.manifest.json').write_bytes(raw_manifest.read_bytes())
        # Schema normalization only: selected modules, all counts, arrays and
        # IR labels stay untouched. Preserve the raw module source output.
        for row in manifest['rows']:
            row['cohort']=row['assay'];row['lineage']['assay']=row['assay']
            if row['assay']=='v2-synthetic':
                m=row['lineage']['module']
                row['module_id']='module-'+module.C.R.fingerprint({m['a']:1,m['near']:1,m['far']:1})[:16]
            else:
                row['module_id']=None
            row['lineage']['module_id']=row['module_id']
        manifest['metadata_normalization']=dict(command=pin(__file__),raw_generated_manifest=pin(out/'combined-controls.generated-raw.manifest.json'),fields=['cohort','assay','module_id'],candidate_or_label_changes=False)
        original={r['source_index']:r for r in manifest['rows'] if r['kind']=='anchor'}
        for row in manifest['rows']:
            baseline=original[row['source_index']]
            if row['leader']!=baseline['leader'] or row['base']!=baseline['base'] or sum(row['canonical_card_counts'].values())!=sum(baseline['canonical_card_counts'].values()):
                raise ValueError('background leader/base/size changed')
        raw_manifest.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
        receipt.update(status='prepared',artifact=pin(out/'combined-controls.npz'),manifest=pin(raw_manifest),source=pin(module.__file__),counts=manifest['counts'],v1=manifest['v1'],v2=manifest['v2'])
    measured=guard.receipt();receipt.update(guard=measured,elapsed_seconds=measured['elapsed_seconds'],aggregate_preparation_attempt_seconds=prior+measured['elapsed_seconds'])
    if receipt['aggregate_preparation_attempt_seconds']>20 or measured['peak_rss_bytes']>512*1024*1024:
        raise RuntimeError('aggregate preparation allowance exceeded')
except BaseException as exc:
    measured=guard.receipt();receipt.update(status='failed',error=str(exc),guard=measured,elapsed_seconds=measured['elapsed_seconds'],aggregate_preparation_attempt_seconds=prior+measured['elapsed_seconds'])
    (out/'control-preparation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise
(out/'control-preparation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','elapsed_seconds','aggregate_preparation_attempt_seconds','counts','v2','guard','artifact','manifest')},indent=2))
