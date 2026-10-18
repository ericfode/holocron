import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
sys.path.insert(0, '/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck')
from embedding_geometry_audit import Guard
out=Path(__file__).resolve().parent
prior=json.loads((out.parent/'control-preparation-receipt.json').read_text())['elapsed_seconds']
def pin(p):
    p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
guard=Guard(out)
receipt=dict(phase='strict-module-feasibility',status='failed',prior_preparation_seconds=prior,command=pin(__file__),neural_forwards=0,neighbor_metrics=0,native_calls=0,optimizer_updates=0)
try:
    with guard:
        signal.setitimer(signal.ITIMER_REAL,20-prior)
        resource.setrlimit(resource.RLIMIT_CPU,(18,19))
        import independent_retrieval_module_controls as module
        result=module.feasibility(out)
        receipt.update(status=result['status'],counts=result['counts'],feasibility=pin(out/'feasibility.json'),source=pin(module.__file__))
    measured=guard.receipt()
    receipt.update(guard=measured,elapsed_seconds=measured['elapsed_seconds'],aggregate_preparation_attempt_seconds=prior+measured['elapsed_seconds'])
    if receipt['aggregate_preparation_attempt_seconds']>20 or measured['peak_rss_bytes']>512*1024*1024:
        raise RuntimeError('aggregate preparation allowance exceeded')
except BaseException as exc:
    measured=guard.receipt();receipt.update(status='failed',error=str(exc),guard=measured,elapsed_seconds=measured['elapsed_seconds'],aggregate_preparation_attempt_seconds=prior+measured['elapsed_seconds'])
    (out/'feasibility-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise
(out/'feasibility-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
