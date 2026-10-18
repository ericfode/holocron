"""Exclusive byte-only packet for diagnosis, failed intent verification and its saved-only sidecar.

Default preparation writes nothing and requires all three canonical roots closed.
NPZ is opaque. The prior packet is a pinned dependency, never recursively read.
"""
import argparse
import gzip
import json
import os
from pathlib import Path

import compositional_typed_package as P

HERE = Path(__file__).resolve().parent
NAMES = ('real-ir-intent-diagnostic-v1', 'real-ir-intent-v1', 'real-ir-intent-saved-v1')
SCHEMA = 'jepa-real-ir-intent-saved-evidence/1'
LIMITS = dict(P.LIMITS)
PRIOR_SHA = 'dc4d89a220722120b3aae51801fdf9521fa971e175f5c1985a81f10544b6b3c0'
DIAGNOSTIC_SHA = 'd531e1fe35fb556f81562e10b8802da79f586f1f282379654867b8880cb60624'
RESERVATION_SHA = '64d114c84a454546e16c906815980f167d35c4f6d9a0884402a0105e76cc1bb8'
RESERVED = ['ASH_259', 'HMW_158', 'LOF_259', 'SOR_132']
REMAINING = ['ASH_259', 'HMW_158', 'LOF_259']
STAGES = ('build', 'dev-native', 'prep', 'fit', 'terminal-native', 'terminal-prep', 'score', 'verify')
BINARY = 'build-1/real-ir-intent-native-collector'
ORIGINAL_HELPER_SHA = 'a44505a4825de66e1577262ded70f069a41236a403a621a1a11a9ef58d7dc084'
ORIGINAL_TEST_SHA = '9709cb454759e48d37dc3dff84bc654f094c28c3d73a3012ce15da591ee5e1d2'
EXTENSIONS = {'.json', '.jsonl', '.log', '.txt', '.md', '.npz', '.py', '.rs', '.toml', '.lock'}
TEXT = EXTENSIONS - {'.npz'}


def load(path): return json.loads(P.read_limited(Path(path), P.MAX_FILE))
def pin(path):
    path = Path(path).resolve(strict=True); value = P.transfer(path, 'identity')
    return dict(path=str(path), sha256=value['raw_sha256'], bytes=value['raw_bytes'])


def exact_pin(value):
    P.require(type(value) is dict and set(value) == {'path', 'sha256', 'bytes'} and
        Path(value['path']).is_absolute() and P.sha(value['sha256']) and
        type(value['bytes']) is int and value['bytes'] >= 0, 'exact absolute byte pin required')


def history(root, read_bytes=None):
    """Replay only the sealed accounting records, including full failed charges."""
    root = Path(root)
    raw = lambda name: P.read_limited(root / name, P.MAX_FILE) if read_bytes is None else read_bytes(name)
    doc = lambda name: json.loads(raw(name))
    localpin = lambda name: dict(path=str(root / name), sha256=P.digest(raw(name)), bytes=len(raw(name)))
    spec, parent, closure = (doc(n) for n in ('campaign-spec.json', 'parent-manifest.json', 'experiment-closure.json'))
    source = spec['source_freeze_commit']
    P.require(type(source) is str and len(source) == 40 and all(c in '0123456789abcdef' for c in source), 'full source freeze required')
    P.require(spec['schema'] == 'jepa-sealed-budget-spec/1' and spec['ledger_path'] == str(root / 'campaign-ledger.jsonl') and
        spec['parent_manifest'] == localpin('parent-manifest.json'), 'canonical spec/parent route differs')
    P.require(spec['stage_order'] == (['diagnose'] if root.name == NAMES[0] else list(STAGES) if root.name == NAMES[1] else ['verify']), 'fixed stage/terminal outcome order required')
    carry = parent['carry']; P.require(carry['observed_native_applies'] is None, 'historical unknown observed count must remain unknown')
    rows = [json.loads(v) for v in raw('campaign-ledger.jsonl').splitlines() if v.strip()]
    keys = set(spec['caps']) - {'seconds'}; charged = {k: 0 for k in spec['caps']}; observed = {k: 0 for k in keys}
    previous = '0' * 64; finished = []; statuses = []; pending = None; proofs = []
    for sequence, row in enumerate(rows):
        body = {k: v for k, v in row.items() if k != 'record_sha256'}; d = row['data']; event = row['event']
        P.require(row['schema'] == 'jepa-sealed-budget-journal/1' and row['sequence'] == sequence and
            row['previous_sha256'] == previous and P.digest(P.canonical(body)) == row['record_sha256'], 'closed journal hashchain differs')
        previous = row['record_sha256']
        if event == 'initialized':
            P.require(sequence == 0 and d == dict(spec=localpin('campaign-spec.json')), 'once-only exact spec initialization required')
        elif event == 'begin':
            P.require(sequence > 0 and pending is None and 'failed' not in statuses and len(finished) < len(spec['stage_order']) and
                d['stage'] == spec['stage_order'][len(finished)] and d['argv'] == spec['stages'][d['stage']]['argv'] and
                d['guard'] == spec['guard'], 'once-only stage command/order differs')
            pending = dict(stage=d['stage'], open={}, intents={k: 0 for k in keys}, done={k: 0 for k in keys})
        elif event == 'intent':
            P.require(pending is not None and d['token'] == sequence and d['token'] not in pending['open'] and
                d['counter'] in keys and P.number(d['amount']) and d['amount'] > 0, 'invalid durable intent')
            k = d['counter']; pending['intents'][k] += d['amount']
            P.require(pending['intents'][k] <= spec['stages'][pending['stage']]['reservation'][k], 'intent exceeds reservation')
            pending['open'][d['token']] = (k, d['amount'])
        elif event == 'complete':
            P.require(pending is not None and d['token'] in pending['open'], 'unpaired counter completion')
            k, n = pending['open'].pop(d['token']); external = k in spec['stages'][pending['stage']]['external_counters']
            P.require((external and P.number(d['actual']) and d['actual'] <= n and len({p['path'] for p in d['proofs']}) >= 2) or
                (not external and d['actual'] is None and not d['proofs']), 'ordinary/external completion differs')
            pending['done'][k] += d['actual'] if external else n; proofs += d['proofs']
        elif event == 'finish':
            P.require(pending is not None and d['status'] in ('completed', 'failed') and d['cleanup_verified'] is True and
                d['execution_ended'] is True and P.number(d['seconds']), 'unresolved execution cannot be packaged')
            stage = spec['stages'][pending['stage']]; failed = d['status'] == 'failed'
            P.require(failed or (not pending['open'] and d['seconds'] <= stage['reservation']['seconds'] and
                all(v is None or pending['done'][k] == v for k, v in stage['expected'].items())), 'completed panel/ceiling differs')
            charge = {k: max(stage['reservation'][k], pending['intents'][k]) if failed else pending['done'][k] for k in keys}
            charge['seconds'] = max(stage['reservation']['seconds'], d['seconds']) if failed else d['seconds']
            P.require(d['charged'] == charge and d['durable_intents'] == pending['intents'] and
                d['durable_completed'] == pending['done'], 'failed charge or observed prefix rewritten')
            for k, v in charge.items(): charged[k] += v
            for k in keys: observed[k] = None if failed and stage['reservation'][k] else None if observed[k] is None else observed[k] + pending['done'][k]
            pending_done = dict(pending['done']); pending_intents = dict(pending['intents'])
            finished.append(pending['stage']); statuses.append(d['status']); proofs += d['proofs']; pending = None
        else:
            raise ValueError('pending failure/unreviewed accounting event')
    P.require(rows and rows[0]['event'] == 'initialized' and rows[-1]['event'] == 'finish' and pending is None, 'closed ended ledger required')
    failed = 'failed' in statuses
    if root.name == NAMES[1]:
        failed_receipt = doc('verify-1-stage-receipt.json')
        P.require(failed and finished == list(STAGES) and statuses == ['completed'] * 7 + ['failed'] and
            closure['schema'] == 'jepa-real-ir-intent-failed-closure/1' and
            closure['status'] == 'closed-failed-saved-verification' and closure['completed_stages'] == list(STAGES[:-1]) and
            closure['failed_stage'] == 'verify' and closure['failed_stage_receipt'] == localpin('verify-1-stage-receipt.json') and
            closure['failed_stage_receipt'] in proofs and closure['decisions_independently_verified'] is False and
            closure['original_ledger_reopened'] is False and closure['failed_charge_credited'] is False and
            failed_receipt['stage'] == 'verify' and failed_receipt['status'] == 'failed' and
            failed_receipt['cleanup_verified'] is True and
            failed_receipt['error'] == dict(type='KeyError', message="'schema'") and
            stage['reservation']['seconds'] == 10. and charge['seconds'] == 10. and
            all(v == 0 for k, v in charge.items() if k != 'seconds') and
            all(v == 0 for v in pending_done.values()) and
            all(v == 0 for v in pending_intents.values()) and
            all(v == 0 for k, v in stage['reservation'].items() if k != 'seconds'),
            'original must retain exactly seven completed stages and the failed zero-call schema verifier/full10s charge')
    else:
        expected = 'closed-saved-diagnostic' if root.name == NAMES[0] else 'closed-verified-saved-intent'
        P.require(not failed and finished == spec['stage_order'] and statuses == ['completed'] * len(finished) and
            closure['status'] == expected, 'all declared diagnostic/saved-only stages must be completed')
    if root.name == NAMES[2]:
        P.require(closure['schema'] == 'jepa-real-ir-intent-saved-closure/1' and
            closure['original_ledger_reopened'] is False and closure['failed_charge_credited'] is False and
            spec['caps']['seconds'] == spec['stages']['verify']['reservation']['seconds'] == 20. and
            all(v == 0 for k, v in spec['caps'].items() if k != 'seconds') and
            all(v == 0 for k, v in spec['stages']['verify']['reservation'].items() if k != 'seconds') and
            all(v == 0 for v in spec['stages']['verify']['expected'].values()) and
            not spec['stages']['verify']['external_counters'] and
            all(v == 0 for k, v in charged.items() if k != 'seconds') and
            all(v == 0 for v in observed.values()), 'saved sidecar must be a single20s zero-science allocation')
    cumulative = dict(charged_native_applies=carry['charged_native_applies'] + charged['native_applies'],
        charged_seconds=carry['charged_seconds'] + charged['seconds'], observed_native_applies=None)
    P.require(closure['source_freeze_commit'] == source and closure['journal'] == localpin('campaign-ledger.jsonl') and
        closure['final_chain'] == previous and closure['new_charged'] == charged and closure['cumulative'] == cumulative and
        closure['production_changed'] is False and charged['paid_jobs'] == charged['paid_spend_usd'] == 0, 'closure/source/carry mismatch')
    if 'new_observed' in closure: P.require(closure['new_observed'] == observed, 'official observed knownness differs')
    if root.name == NAMES[0]:
        P.require(localpin('experiment-closure.json')['sha256'] == DIAGNOSTIC_SHA and
            all(v == 0 for k, v in charged.items() if k != 'seconds'), 'exact zero-call closed diagnostic required')
    return dict(disposition='failed' if failed else 'completed', closure_status=closure['status'], source_freeze_commit=source,
        closure=localpin('experiment-closure.json'), ledger=localpin('campaign-ledger.jsonl'), records=len(rows), stages=finished,
        statuses=statuses, final_chain=previous, carry=carry, cumulative=cumulative, charged=charged, observed=observed), spec, proofs


def allowed(path, root, spec):
    metadata = {root / n for n in ('campaign-spec.json', 'parent-manifest.json', 'campaign-ledger.jsonl', 'experiment-closure.json')}
    if root.name == NAMES[1]:
        metadata.update(root / ('metadata-1/' + n) for n in ('development-plan.json', 'terminal-plan.json', 'preregistration.json'))
    outputs = [Path(p) for stage in spec['stages'].values() for p in stage['outputs']]
    P.require(all(p.is_absolute() and p.is_relative_to(root) and '..' not in p.parts for p in outputs), 'canonical in-root outputs required')
    return path in metadata or any(path == p or path.is_relative_to(p) for p in outputs)


def new_source(path):
    return path.is_relative_to(HERE) and path.relative_to(HERE).parts[0].startswith(
        ('real_ir_intent', 'test_real_ir_intent', 'REAL_IR_INTENT'))


def release_proof(root, spec, reservation, reservation_pin, read_bytes=None):
    """Prelabel metadata and stage order, never a claim of learned transfer."""
    raw = lambda name: P.read_limited(root / name, P.MAX_FILE) if read_bytes is None else read_bytes(name)
    pins = {p['path']: p for p in spec['pins']}; metadata = {}
    for name in ('development-plan.json', 'terminal-plan.json', 'preregistration.json'):
        relative = 'metadata-1/' + name; value = raw(relative)
        p = dict(path=str(root / relative), sha256=P.digest(value), bytes=len(value))
        P.require(pins.get(p['path']) == p, 'release/panel metadata must be frozen before stages')
        metadata[name] = (json.loads(value), p)
    amendment, amendment_pin = metadata['preregistration.json']
    P.require(spec['reservation_amendment'] == amendment_pin and spec['prelabel_reservation'] == reservation_pin and
        amendment['schema'] == 'jepa-real-ir-intent-reservation-amendment/1' and
        amendment['status'] == 'terminal-release-preregistered' and amendment['original_reservation'] == reservation_pin and
        amendment['old_reservation_sha256'] == P.digest(P.canonical(reservation)) and
        amendment['released_terminal_source'] == 'SOR_132' and amendment['remaining_reserved_codes'] == REMAINING and
        amendment['remaining_conservative_groups'] == [['ASH_259', 'LOF_259'], ['HMW_158']] and
        amendment['native_outcome_order'] == ['development', 'all-fitted-checkpoints-sealed', 'terminal'],
        'only SOR_132 terminal release is permitted; original reservation/groups unchanged')
    for name, panel in (('development', 'development-plan.json'), ('terminal', 'terminal-plan.json')):
        plan, p = metadata[panel]; selected = set(plan['selected_whole_cards'])
        P.require(spec['native_plans'][name] == p and not selected.intersection(REMAINING) and
            ('SOR_132' in selected) == (name == 'terminal') and plan['panel_role'] == name and
            plan['terminal_outcomes_after_all_checkpoints'] == (name == 'terminal'), 'unreleased source selected or panel role changed')
        if name == 'terminal': P.require([v['code'] for v in plan['programs']] == ['SOR_132'], 'terminal source must be SOR_132 only')
    return dict(amendment=amendment_pin, released_terminal_source='SOR_132', remaining_reserved_codes=REMAINING,
        remaining_conservative_groups=[['ASH_259', 'LOF_259'], ['HMW_158']],
        order=list(STAGES), scope='Frozen metadata plus completed stage ordering; scientific checkpoint and prediction correctness are separately verified.')


def recovery_proof(experiments, histories, specs, readers=None):
    """Link separate immutable dispositions without laundering the original failure."""
    roots = [Path(experiments) / name for name in NAMES]
    def raw(index, relative):
        return P.read_limited(roots[index] / relative, P.MAX_FILE) if readers is None else readers[index](relative)
    def doc(index, relative): return json.loads(raw(index, relative))
    def localpin(index, relative):
        value = raw(index, relative)
        return dict(path=str(roots[index] / relative), sha256=P.digest(value), bytes=len(value))
    for left, right in zip(NAMES, NAMES[1:]):
        P.require(histories[left]['cumulative'] == histories[right]['carry'], 'linked parent charge reset')
    side = specs[2]; closure = doc(2, 'experiment-closure.json'); original = localpin(1, 'experiment-closure.json')
    P.require(side['original_root'] == str(roots[1]) and side['failed_closure'] == original and
        closure['original_failed_closure'] == original and
        side['original_source_freeze_commit'] == closure['original_source_freeze_commit'] == histories[NAMES[1]]['source_freeze_commit'],
        'saved sidecar must bind exact failed original/source')
    parent = doc(2, 'parent-manifest.json'); frozen = {p['path']: p for p in parent['pins']}
    for name in ('campaign-spec.json', 'campaign-ledger.jsonl', 'experiment-closure.json'):
        value = localpin(1, name)
        P.require(frozen.get(value['path']) == value, 'sidecar parent must preserve original failed metadata bytes')
    verification_pin = localpin(2, 'verify-1/verification-result.json')
    P.require(closure['verification'] == verification_pin, 'saved verification closure pin differs')
    result = doc(2, 'verify-1/verification-result.json')
    P.require(result['verified'] is True and result['mismatches'] == 0 and result['semantic_validated'] is False and
        result['lineage']['original_failure_preserved'] is True and result['lineage']['scientific_arithmetic_unchanged'] is True and
        set(result['calls']) == {'native_applies', 'neural_forwards', 'backwards', 'optimizer_updates', 'numerical_fits', 'paid_jobs'} and
        all(type(v) in (int, float) and not isinstance(v, bool) and v == 0 for v in result['calls'].values()),
        'official saved verification must pass with zero new scientific calls')
    return dict(original_failed_closure=original, preserved_failed_stage='verify', preserved_failed_charge_seconds=10.,
        saved_verification=verification_pin, original_disposition='failed', saved_disposition='completed',
        failed_charge_credited=False, scope='Byte/provenance and closed-accounting replay only; saved semantic calculations are not rerun.')


def inventory(experiments, report):
    experiments = Path(experiments).resolve(strict=True); entries = []; excluded = []; histories = {}; specs = []; proofs = []; sources = {}
    def add(path, url, category, expected=None):
        if expected is not None: P.require(pin(path) == expected, 'frozen source bytes differ')
        encoding = 'gzip' if path.suffix in TEXT else 'identity'
        entries.append(dict(url=P.safe_name(url + ('.gz' if encoding == 'gzip' else '')), category=category,
            provenance=dict(original_path=str(path)), **P.transfer(path, encoding))); P.check_entries(entries)
    for name in NAMES:
        root = experiments / name; P.require(root.is_dir() and not root.is_symlink(), 'exact closed campaign root required')
        h, spec, pr = history(root); histories[name] = h; specs.append(spec); proofs += pr
        for path in sorted(root.rglob('*')):
            P.require(not path.is_symlink(), 'campaign symlink forbidden')
            if not path.is_file(): continue
            P.require(allowed(path, root, spec), 'unreviewed campaign path outside metadata/declared outputs')
            relative = path.relative_to(root).as_posix()
            if name == NAMES[1] and relative == BINARY:
                excluded.append(dict(campaign=name, relative_path=relative, reason='compiled binary excluded; byte pin retained',
                    provenance=dict(original_path=str(path)), **P.transfer(path, 'identity'))); continue
            P.require(path.suffix in EXTENSIONS and not set(path.relative_to(root).parts) & {'target', '__pycache__', '.git', '.venv'}, 'unexpected campaign payload')
            add(path, 'payload/campaigns/' + name + '/' + relative, 'campaign')
        for value in spec['pins']:
            path = Path(value['path'])
            if new_source(path):
                exact_pin(value); P.require(value['path'] not in sources or sources[value['path']] == value, 'conflicting frozen source versions')
                sources[value['path']] = value
    recovery = recovery_proof(experiments, histories, specs)
    for value in sources.values(): add(Path(value['path']), 'payload/sources/' + Path(value['path']).relative_to(HERE).as_posix(), 'frozen-source', value)
    for name in (Path(__file__).name, 'test_real_ir_intent_saved_package.py', 'compositional_typed_package.py'):
        path = HERE / name
        if str(path) not in sources: add(path, 'payload/sources/' + name, 'packaging-source')
    for name, digest in (('real_ir_intent_package.py', ORIGINAL_HELPER_SHA), ('test_real_ir_intent_package.py', ORIGINAL_TEST_SHA)):
        path = HERE / name; value = pin(path)
        P.require(value['sha256'] == digest, 'original package helper/test bytes must remain unchanged')
        if str(path) not in sources: add(path, 'payload/sources/' + name, 'historical-packaging-source', value)
    report = Path(report).resolve(strict=True)
    P.require(report == HERE / 'REAL_IR_INTENT_RESULTS.md', 'one brief new results report required')
    if str(report) not in sources: add(report, 'payload/reports/' + report.name, 'final-report')
    reservation = experiments / 'real-ir-hp-fresh-reservation.json'; rp = pin(reservation)
    P.require(rp['sha256'] == RESERVATION_SHA and specs[1]['prelabel_reservation'] == rp, 'exact frozen fresh-family reservation required')
    reserved = load(reservation)
    P.require(reserved['status'] == 'reserved-no-new-outcomes' and reserved['reserved_codes'] == RESERVED, 'reserved sources must remain explicit')
    release = release_proof(experiments / NAMES[1], specs[1], reserved, rp)
    add(reservation, 'payload/reservation/' + reservation.name, 'prelabel-reservation', rp)
    dependency = HERE / 'real-ir-hp-projection-evidence/manifest.json'; dp = pin(dependency)
    P.require(dp['sha256'] == PRIOR_SHA, 'exact opaque prior packet required')
    by_path = {e['provenance']['original_path']: e for e in entries + excluded}
    for value in proofs:
        exact_pin(value)
        if any(Path(value['path']).is_relative_to(experiments / name) for name in NAMES):
            e = by_path.get(value['path']); P.require(e is not None and e['raw_sha256'] == value['sha256'] and e['raw_bytes'] == value['bytes'], 'in-root proof absent/changed')
    return dict(schema=SCHEMA, root_order=list(NAMES), limits=LIMITS, files=entries, excluded=excluded, histories=histories,
        source_freeze_commits={n: h['source_freeze_commit'] for n, h in histories.items()}, frozen_source_pins=list(sources.values()),
        reservation=rp, release=release, recovery=recovery, dependency=dict(relative_manifest='../real-ir-hp-projection-evidence/manifest.json', pin=dp,
            scope='Explicit prior publication dependency; opaque, never recursively fetched or copied.'),
        scientific_calls=0, semantic_validated=False,
        scope='Exact byte preservation of closed diagnosis, failed original verification and separate successful zero-call saved sidecar; no model/native/array execution or publication mutation.')


def documents(plan):
    index = P.encode(dict(schema=SCHEMA, manifest='manifest.json', histories=plan['histories'], dependency=plan['dependency'], semantic_validated=False))
    P.require(len(index) <= P.MAX_MANIFEST, 'index metadata limit')
    manifest = dict(plan, files=plan['files'] + [dict(url='index.json', encoding='identity', sha256=P.digest(index), bytes=len(index),
        raw_sha256=P.digest(index), raw_bytes=len(index), category='index')])
    raw = P.encode(manifest); P.require(len(raw) <= P.MAX_MANIFEST, '4MiB manifest limit'); P.check_entries(manifest['files'], len(raw))
    return index, raw


def prepare(experiments, out, report):
    out = Path(out); P.require(not out.is_symlink(), 'destination symlink forbidden'); out = out.resolve()
    prior = HERE / 'real-ir-hp-projection-evidence'
    P.require(not out.exists() and all(not out.is_relative_to(Path(experiments).resolve() / n) and
        not (Path(experiments).resolve() / n).is_relative_to(out) for n in NAMES) and
        not out.is_relative_to(prior) and not prior.is_relative_to(out), 'exclusive destination outside evidence roots/prior packet required')
    plan = inventory(experiments, report); documents(plan); return plan


def build(experiments, out, report):
    plan = prepare(experiments, out, report); index, manifest = documents(plan); out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    for e in plan['files']:
        path = out / e['url']; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            actual = P.transfer(Path(e['provenance']['original_path']), e['encoding'], stream); stream.flush(); os.fsync(stream.fileno())
        P.require(all(actual[k] == e[k] for k in actual), 'source changed during byte copy')
    P.require(inventory(experiments, report) == plan, 'source inventory changed while copying')
    for name, raw in (('index.json', index), ('manifest.json', manifest)):
        with (out / name).open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return verify(out)


def verify(out, expected_manifest_sha=None):
    out = Path(out); P.require(not out.is_symlink() and not (out / 'manifest.json').is_symlink(), 'packet symlink forbidden'); out = out.resolve(strict=True)
    raw = P.read_limited(out / 'manifest.json', P.MAX_MANIFEST)
    if expected_manifest_sha is not None: P.require(P.digest(raw) == expected_manifest_sha, 'manifest pin differs')
    m = json.loads(raw); P.require(m['schema'] == SCHEMA and m['limits'] == LIMITS and m['scientific_calls'] == 0 and
        m['semantic_validated'] is False and m['dependency']['pin']['sha256'] == PRIOR_SHA and
        m['dependency']['relative_manifest'] == '../real-ir-hp-projection-evidence/manifest.json' and m['reservation']['sha256'] == RESERVATION_SHA,
        'packet identity/scope differs'); P.check_entries(m['files'], len(raw)); expected = {'manifest.json'}; by_original = {}
    for e in m['files']:
        name = P.safe_name(e['url']); P.require(name not in expected, 'duplicate packet URL'); expected.add(name); path = out / name
        P.require(path.resolve().is_relative_to(out) and not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(out)), 'packet path escape/symlink')
        P.verify_payload(path, e)
        if 'provenance' in e:
            original = e['provenance']['original_path']; P.require(original not in by_original, 'duplicate original source'); by_original[original] = e
    actual = set()
    for path in out.rglob('*'):
        P.require(not path.is_symlink(), 'packet symlink forbidden')
        if path.is_file(): actual.add(path.relative_to(out).as_posix())
    P.require(actual == expected and set(m['histories']) == set(NAMES) and m['root_order'] == list(NAMES), 'packet membership/root inventory differs')
    reservation_entry = by_original.get(m['reservation']['path'])
    P.require(reservation_entry is not None, 'original reservation payload absent')
    def decode(entry):
        path = out / entry['url']
        with (gzip.open(path, 'rb') if entry['encoding'] == 'gzip' else path.open('rb')) as stream: value = stream.read(entry['raw_bytes'] + 1)
        P.require(len(value) == entry['raw_bytes'], 'bounded metadata payload differs'); return value
    reservation = json.loads(decode(reservation_entry))
    readers = []; specs = []
    for name in NAMES:
        h = m['histories'][name]; root = Path(h['closure']['path']).parent
        def read_bytes(relative, root=root):
            e = by_original[str(root / relative)]; path = out / e['url']
            with (gzip.open(path, 'rb') if e['encoding'] == 'gzip' else path.open('rb')) as stream: data = stream.read(e['raw_bytes'] + 1)
            P.require(len(data) == e['raw_bytes'], 'bounded accounting payload differs'); return data
        readers.append(read_bytes)
        rebuilt, spec, proofs = history(root, read_bytes); specs.append(spec)
        P.require(rebuilt == h and m['source_freeze_commits'][name] == h['source_freeze_commit'], 'offline accounting/source differs')
        if name == NAMES[1]: P.require(release_proof(root, spec, reservation, m['reservation'], read_bytes) == m['release'], 'offline release policy differs')
        for original, e in by_original.items():
            path = Path(original)
            if path.is_relative_to(root): P.require(allowed(path, root, spec), 'offline undeclared campaign file')
        for value in proofs:
            if Path(value['path']).is_relative_to(root):
                e = by_original.get(value['path'])
                if e is None: e = next((x for x in m['excluded'] if x['provenance']['original_path'] == value['path']), None)
                P.require(e is not None and e['raw_sha256'] == value['sha256'] and e['raw_bytes'] == value['bytes'], 'offline in-root proof differs')
    experiments = Path(m['histories'][NAMES[0]]['closure']['path']).parent.parent
    P.require(recovery_proof(experiments, m['histories'], specs, readers) == m['recovery'], 'offline recovery link differs')
    for name, digest in (('real_ir_intent_package.py', ORIGINAL_HELPER_SHA), ('test_real_ir_intent_package.py', ORIGINAL_TEST_SHA)):
        matched = [e for e in m['files'] if e['url'] == 'payload/sources/' + name + '.gz']
        P.require(len(matched) == 1 and matched[0]['raw_sha256'] == digest, 'original packaging bytes absent/changed')
    for value in m['frozen_source_pins'] + [m['reservation']]:
        e = by_original.get(value['path']); P.require(e is not None and e['raw_sha256'] == value['sha256'] and e['raw_bytes'] == value['bytes'], 'frozen source/reservation payload absent')
    return dict(status='verified-bytes-only', manifest_sha256=P.digest(raw), files=len(actual), raw_bytes=sum(e['raw_bytes'] for e in m['files']) + len(raw),
        stored_bytes=sum(e['bytes'] for e in m['files']) + len(raw), source_freeze_commits=m['source_freeze_commits'],
        dispositions={n: h['disposition'] for n, h in m['histories'].items()}, scientific_calls=0, semantic_validated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--build', action='store_true'); modes.add_argument('--verify', action='store_true')
    parser.add_argument('--experiments', type=Path); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path); parser.add_argument('--expected-manifest-sha'); args = parser.parse_args()
    if args.verify: result = verify(args.out, args.expected_manifest_sha)
    else:
        P.require(args.experiments is not None and args.report is not None, 'experiments and final report required')
        result = (build if args.build else prepare)(args.experiments, args.out, args.report)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__': main()
