"""Single production preparation attempt; no model or neighbor execution."""
import hashlib
import json
from pathlib import Path
import sys

SOURCE_DIR = Path('/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE_DIR))
from embedding_geometry_audit import Guard


def pin(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


receipt = dict(status='failed', production_attempts=1, neural_forwards=0, model_forward_calls=0,
               neighbor_metrics=0, native_calls=0, optimizer_updates=0, paid_spend_usd=0,
               command=pin(__file__), source=pin(SOURCE_DIR / 'independent_retrieval_controls.py'),
               guard_source=pin(SOURCE_DIR / 'embedding_geometry_audit.py'))
guard = Guard(OUT)
try:
    with guard:
        import independent_retrieval_controls as controls
        if receipt['source']['sha256'] != '069e8b2714aeff7fa071022f496a3526d45f14139f841a91705e3129c5b3b8f3':
            raise ValueError('source differs from reviewed preparation command')
        manifest = controls.prepare(OUT)
        receipt.update(status='prepared', manifest=pin(OUT / 'deck-controls.manifest.json'),
                       artifact=pin(OUT / 'deck-controls.npz'), support=manifest['support'],
                       minimum_family_support_satisfied=manifest['minimum_family_support_satisfied'],
                       minimum_strict_primary_support_satisfied=manifest['minimum_strict_primary_support_satisfied'],
                       protected_before=manifest['protected_before'], protected_after=manifest['protected_after'])
    measured = guard.receipt()
    if measured['elapsed_seconds'] > 20 or measured['cpu_seconds'] > 20 or measured['peak_rss_bytes'] > 512*1024*1024:
        raise RuntimeError('preparation cap exceeded')
    receipt.update(guard=measured, elapsed_seconds=measured['elapsed_seconds'],
                   aggregate_preparation_attempt_seconds=measured['elapsed_seconds'])
except BaseException as exc:
    measured = guard.receipt()
    receipt.update(status='failed', error=str(exc), guard=measured, elapsed_seconds=measured['elapsed_seconds'],
                   aggregate_preparation_attempt_seconds=measured['elapsed_seconds'])
    (OUT / 'control-preparation-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    raise
(OUT / 'control-preparation-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','elapsed_seconds','support','minimum_family_support_satisfied','minimum_strict_primary_support_satisfied','guard')},indent=2))
