"""Saved-only preparation for the fixed HP-projection comparison.

ROOT supplies guarded NumPy and writes returned arrays/manifest. The only TRAIN
rows and fitted weight statistics are the original study's 40 TRAIN rows.
Fresh source partitions are provenance, never a new training split.
"""
import copy
import hashlib
import json
from pathlib import Path

import real_ir_transfer_data as D

SCHEMA = 'jepa-real-ir-hp-projection-data/1'


def require(ok, message):
    if not ok: raise ValueError(message)


def values(a): return a.tolist() if hasattr(a, 'tolist') else copy.deepcopy(a)


def load(path): return json.loads(Path(path).read_text())


def pin(path):
    p = Path(path).resolve(strict=True); raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def combine(np, old, old_manifest, fresh, fresh_manifest):
    """Join two already-derived native datasets; no fitted transform or relabeling."""
    a, b = ({k: values(v) for k, v in data.items()} for data in (old, fresh))
    require(len(a['targets']) == len(b['targets']) == 56 and a['train_idx'] == list(range(40)) and
            a['held_idx'] == list(range(40, 56)), 'exact original56/40TRAIN/16olddev ABI required')
    for key in ('program_features', 'source_printed_features', 'program_ids'):
        require(a[key] == b[key], 'original source bank changed: ' + key)
    require(a['program_indices'] == b['program_indices'] and a['selected_candidate_indices'] == b['selected_candidate_indices'] and
            a['source_cards'] == b['source_cards'], 'source/intent order changed')
    require(old_manifest['canonical_programs'] == fresh_manifest['canonical_programs'] and
            old_manifest['mechanism_family_keys'] == fresh_manifest['mechanism_family_keys'] and
            old_manifest['candidate_order'] == fresh_manifest['candidate_order'], 'canonical program/family/role changed')
    for i in range(56):
        for q in range(6):
            x, y = a['candidate_features'][i][q], b['candidate_features'][i][q]
            require(len(x) == len(y) == 17 and x[:12] + x[13:] == y[:12] + y[13:] and
                    y[14] == (8. if q < 2 else 10. if q < 4 else 30.), 'fresh public input changed beyond declared damage')
            damage = 1. if q < 2 else 2. if q < 4 else 4.
            if i % 8 == 6 and q == 0 or i % 8 == 7 and q == 4: damage = 0.
            require(y[12] == damage, 'fresh board must use ground1/space2/base4 and exact healthy variants')
    metadata = []
    for offset, manifest in ((0, old_manifest), (56, fresh_manifest)):
        require(len(manifest['root_metadata']) == 56, 'root metadata inventory differs')
        for i, original in enumerate(manifest['root_metadata']):
            m = copy.deepcopy(original)
            require(m['root'] == i and m['program_index'] == a['program_indices'][i], 'source-root alignment differs')
            m.update(root=i + offset, world_id=i + offset, native_world_id=original['world_id'],
                native_source_partition=original['partition'], source_campaign='old' if offset == 0 else 'fresh',
                partition='fresh' if offset else 'train' if i < 40 else 'old_dev')
            metadata.append(m)
    def packet(data, m, i, q):
        c = data['candidate_features'][i][q]
        return (m['operator'], m['amount'], c[12], c[14])
    # Every PR45 observed endpoint, including the exposed HELD cards, excludes
    # its exact effect/state tuple from the new primary endpoint panel.
    prior = {packet(a, old_manifest['root_metadata'][i], i, q)
        for i in range(56) for q in range(6) if a['target_mask'][i][q][1]}
    primary = [[[0., 0.] for _ in range(6)] for _ in range(112)]
    replay = copy.deepcopy(primary); primary_roots, replay_roots, audit = [], [], []
    for i in range(56):
        for q in range(6):
            if not b['target_mask'][i][q][1]: continue
            require(q == b['selected_candidate_indices'][i] and b['target_mask'][i][q] == [1., 1.],
                    'only actual committed eligible intended endpoints may be scored')
            key = packet(b, fresh_manifest['root_metadata'][i], i, q); seen = key in prior
            (replay if seen else primary)[i + 56][q][1] = 1.
            (replay_roots if seen else primary_roots).append(i + 56)
            audit.append(dict(root=i + 56, candidate=q, tuple=list(key), seen_any_PR45_endpoint=seen,
                              source='all39 PR45 native endpoints, including exposed held outcomes'))
    blockers = []
    for name, m in (('old', old_manifest), ('fresh', fresh_manifest)):
        ref = m['reference']
        if (not m['fit_admitted'] or m['fit_blockers'] or ref['known_coordinates'] != 375 or ref['known_eligibility'] != 336 or
                ref['known_intended_deltas'] != 39 or ref['mismatch_count'] != 0):
            blockers.append(name + '-native-reference-admission')
    if (len(primary_roots), len(replay_roots)) != (30, 9): blockers.append('fresh30primary9replay-support')
    arrays = {k: np.asarray(a[k] + b[k], np.float32) for k in
        ('candidate_features', 'targets', 'target_mask', 'baseline_predictions', 'baseline_mask', 'all_ones_eligibility')}
    for key in ('program_features', 'source_printed_features'): arrays[key] = np.asarray(a[key], np.float32)
    for key in ('program_indices', 'selected_candidate_indices'): arrays[key] = np.asarray(a[key] + b[key], np.int64)
    for key in ('source_cards',): arrays[key] = np.asarray(a[key] + b[key])
    arrays.update(program_ids=np.asarray(a['program_ids']), world_ids=np.arange(112, dtype=np.int64),
        native_world_ids=np.asarray(a['world_ids'] + b['world_ids'], np.int64),
        train_idx=np.arange(40, dtype=np.int64), old_dev_idx=np.asarray(list(range(40, 56)), np.int64),
        old_all_idx=np.arange(56, dtype=np.int64), fresh_all_idx=np.asarray(list(range(56, 112)), np.int64),
        primary_target_mask=np.asarray(primary, np.float32), replay_target_mask=np.asarray(replay, np.float32))
    manifest = dict(schema=SCHEMA, fit_admitted=not blockers, fit_blockers=blockers, root_metadata=metadata,
        split=dict(train=list(range(40)), old_dev=list(range(40, 56)), old_all=list(range(56)), fresh_all=list(range(56, 112))),
        fresh_primary_roots=primary_roots, replay_roots=replay_roots, fresh_tuple_audit=audit,
        support=dict(fresh_known_endpoints=len(primary_roots) + len(replay_roots), primary=len(primary_roots), replay=len(replay_roots)),
        reference=copy.deepcopy(fresh_manifest['reference']), old_reference=copy.deepcopy(old_manifest['reference']),
        canonical_programs=copy.deepcopy(old_manifest['canonical_programs']), candidate_order=old_manifest['candidate_order'],
        program_feature_names=old_manifest['program_feature_names'], candidate_feature_names=old_manifest['candidate_feature_names'],
        source_printed_feature_names=old_manifest['source_printed_feature_names'], target_names=old_manifest['target_names'],
        programs=copy.deepcopy(old_manifest['programs']), public_before_records=copy.deepcopy(old_manifest['public_before_records'] + fresh_manifest['public_before_records']),
        normalization='Original fixed public-unit scales only; no new statistics fitted.', training_rows='Only original0..39; never fresh source partitions.',
        primary_policy='Fresh known intended endpoints whose exact(operator,amount,damage,HP) tuple was absent from ALL39 PR45 native endpoints; eligibility is outside primary masks.',
        scope='Fresh states only, same seven exposed cards and helpers. No fresh program/family/eligibility claim; four whenPlayed sources remain reserved.',
        semantic_validated=False)
    return arrays, manifest


def prepare(np, oldroot, newroot):
    """Call only inside ROOT's active saved-prep reservation/guard; no output I/O."""
    oldroot, newroot = Path(oldroot), Path(newroot)
    with np.load(oldroot / 'prep-1/dataset.npz', allow_pickle=False) as data: old = {k: data[k] for k in data.files}
    old_manifest = load(oldroot / 'prep-1/manifest.json')
    plan_path, receipt_path, trace_path = (newroot / p for p in ('metadata-1/native-plan.json', 'native-1/receipt.json', 'native-1/transitions.jsonl'))
    plan, receipt = load(plan_path), load(receipt_path)
    require(receipt['collectionPlanSha256'] == pin(plan_path)['sha256'], 'fresh native plan byte pin differs')
    oldplan = load(oldroot / 'metadata-1/native-plan.json')
    require(plan['programs'] == oldplan['programs'] and plan['helpers'] == oldplan['helpers'] and
            plan['selected_whole_rows'] == oldplan['selected_whole_rows'], 'same complete source rows/canonical programs/helpers required')
    trace = [json.loads(v) for v in trace_path.read_text().splitlines() if v.strip()]
    fresh, fresh_manifest = D.prepare_data(np, plan, receipt, trace)
    arrays, manifest = combine(np, old, old_manifest, fresh, fresh_manifest)
    stats = oldroot / 'fit-1/loss-weights.json'; manifest['old_loss_weights'] = load(stats); manifest['old_loss_weights_pin'] = pin(stats)
    manifest['input_pins'] = [pin(p) for p in (oldroot / 'prep-1/dataset.npz', oldroot / 'prep-1/manifest.json',
        oldroot / 'metadata-1/native-plan.json', plan_path, receipt_path, trace_path, stats)]
    manifest['fresh_native'] = dict(journal_proof=fresh_manifest['journal_proof'], native_apply_calls=fresh_manifest['native_apply_calls'])
    return arrays, manifest
