"""Explicit once-only v2 recovery; v1 failure/reservations remain immutable, without credit."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2].parent
CAMPAIGN = TASK / 'experiments/public-input-binding-v2'
LEDGER = CAMPAIGN / 'campaign-ledger.jsonl'
SCHEMA = 'jepa-public-input-binding-recovery-accounting/1'
CAPS = dict(native_seconds=90., native_build_seconds=30., native_collect_seconds=60.,
            analysis_seconds=30., total_seconds=120., native_roots=16,
            max_applies_per_root=5, native_applies=80, rss_bytes=1073741824, cpu_workers=1,
            neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0,
            paid_spend_usd=0., modal_cumulative_cap_usd=100, modal_minimum_reserve_usd=25)
PARENT_PINS = [
    dict(path=str(TASK/'experiments/learning-sanity-v1/campaign-ledger.jsonl'),
         sha256='86a3970efc4cba8f34bc01dad6fcbd45761cd1d9f619a6bbfc0ac3c2c182aa19', bytes=10069),
    dict(path=str(TASK/'experiments/learning-sanity-v1/analysis-ledger.jsonl'),
         sha256='8821c9ef54ad2e3749ff5f7d598e633a9453669fb14cdc973359e613af36dd62', bytes=31405),
    dict(path=str(HERE/'learning-sanity-evidence/index.json'),
         sha256='75627c2a2527af05859dada8767188fdb9e97622665922f93dbf412d889d7686', bytes=63832)]
PARENT_CHAINS = ['f8acbc596c98df8e70e1fe333deb73375d65a6a1c36827c0e5d757b914f38fbc',
                 'c185302f16f9135ab42a559ca4e4be2e7b58c19d4ebc5f8c0812d3a3200a7eea']
PRIOR_EXPOSURE = dict(scope='Linked PR36+PR37 only; not all historical research', optimizer_updates=1900,
                      neural_forwards=1917, native_applies=87, closed_form_head_fits=32,
                      paid_spend_usd=0.)
ANALYSIS_STAGES = {'analysis-controls':15., 'analysis-verification':15.}
V1_LEDGER = TASK/'experiments/public-input-binding-v1/campaign-ledger.jsonl'
V1_FINAL_CHAIN = '4be4736ee8c9bb8f0105bec597ca863d01626071b3de97991e8fd9feb3fcc953'
PARENT_PINS += [
    dict(path=str(V1_LEDGER), sha256='1b0c327d468d2553454b09e95eeb58287b42c75790510e2ec957968ba9929b3b', bytes=25221),
    dict(path=str(V1_LEDGER.parent/'campaign-config.json'), sha256='1d8f12230684db02f09ee252b3f592dc594b4dcea3b62c33792fbfc37d090f76', bytes=22912),
    dict(path=str(V1_LEDGER.parent/'startup-failure-audit.json'), sha256='16c5165af286b453e202d327224a722368588f6aae5a3f752e6fed7f623e1451', bytes=4133)]
PARENT_CHAINS += [V1_FINAL_CHAIN]
CUMULATIVE_CAPS = dict(scope='Public-input-binding v1+v2 only; historical PR36+37 separate',
    charged_native_applies=160, native_seconds=180., analysis_seconds=30., total_seconds=210.,
    neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_spend_usd=0.)



def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def pin(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def nonnegative(value, integer=False):
    if integer:
        if type(value) is not int or value < 0: raise ValueError('nonnegative integer required')
    elif type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite nonnegative time required')
    return value


def verify_pins(pins):
    seen = set()
    for expected in pins:
        if set(expected) != {'path', 'sha256', 'bytes'} or not Path(expected['path']).is_absolute():
            raise ValueError('exact absolute path/SHA256/bytes pin required')
        if expected['path'] in seen or pin(expected['path']) != expected:
            raise ValueError('duplicate or changed input pin: ' + expected['path'])
        seen.add(expected['path'])


def chain(records):
    previous = '0' * 64
    for i, record in enumerate(records):
        body = {k:v for k,v in record.items() if k != 'record_sha256'}
        if record.get('sequence') != i or record.get('previous_sha256') != previous or digest(body) != record.get('record_sha256'):
            raise ValueError('damaged hash chain; never reset')
        previous = record['record_sha256']
    return previous


def read_rows(stream):
    stream.seek(0)
    return [json.loads(line) for line in stream if line.strip()]


def verify_parents():
    verify_pins(PARENT_PINS)
    journals = []
    for expected, last in zip(PARENT_PINS[:2], PARENT_CHAINS):
        records = [json.loads(line) for line in Path(expected['path']).read_text().splitlines()]
        if chain(records) != last: raise ValueError('prior final chain differs')
        journals.append(records)
    old_pin = journals[0][0]['data']['parent_ledger']; verify_pins([old_pin])
    old = [json.loads(line) for line in Path(old_pin['path']).read_text().splitlines()]
    if chain(old) != journals[0][0]['data']['parent_final_record']:
        raise ValueError('PR36 transitive final chain differs')
    pr36 = sum(nonnegative(r['data']['active_seconds']) for r in old if r['event'] == 'attempt-finish')
    pr37 = sum(nonnegative(r['data']['active_seconds']) for rows in journals for r in rows if r['event'] in ('attempt-finish', 'finish'))
    sealed = json.loads(Path(PARENT_PINS[2]['path']).read_text())['compute']
    if pr36 != sealed['parent_PR36_subtotal']['charged_active_seconds'] or pr37 != sealed['new_increment']['active_seconds']:
        raise ValueError('derived charged-time subtotal differs from sealed parent evidence')
    return dict(pr36=pr36, pr37=pr37, linked_two_cycle_total=pr36 + pr37)


def recovery_parent():
    """Supplemental forensic0 never rewrites v1's observed-unknown or charged80."""
    verify_pins(PARENT_PINS[3:])
    records = [json.loads(line) for line in V1_LEDGER.read_text().splitlines()]
    if chain(records) != V1_FINAL_CHAIN or [r['event'] for r in records] != ['initialized','attempt-intent','attempt-finish','attempt-intent','attempt-finish']:
        raise ValueError('exact ended v1 history required')
    old_config = json.loads(Path(PARENT_PINS[4]['path']).read_text())
    if records[0]['data']['config'] != old_config or records[0]['data']['config_file'] != PARENT_PINS[4]:
        raise ValueError('v1 frozen configuration differs')
    verify_pins(old_config['pins'])
    build, failed = records[2]['data'], records[4]['data']
    if records[1]['data']['stage'] != 'native-build' or records[3]['data']['stage'] != 'native-collect' or build['status'] != 'completed' or failed['status'] != 'failed':
        raise ValueError('only the reviewed constructor failure permits this explicit recovery')
    if build['observed_native_applies'] or failed['observed_native_applies'] or failed['native_exposure_verified'] is not False:
        raise ValueError('v1 observed-unknown accounting must remain unchanged')
    audit = json.loads(Path(PARENT_PINS[5]['path']).read_text()); verify_pins(audit['evidence'])
    if audit['status'] != 'static-pre-apply-failure-proven' or audit['supplemental_forensic_conclusion']['engine_apply_calls'] != 0:
        raise ValueError('pinned independent pre-apply proof required')
    return dict(status='failed-v1-preserved-without-credit', ledger=PARENT_PINS[3], config=PARENT_PINS[4],
        failure_audit=PARENT_PINS[5], final_record=V1_FINAL_CHAIN, charged_native_applies=80,
        observed_native_applies=None, known_native_apply_lower_bound=0,
        charged_native_seconds=nonnegative(build['active_seconds']) + max(60., nonnegative(failed['active_seconds'])),
        observed_native_seconds=build['active_seconds'] + failed['active_seconds'],
        analysis_charged_seconds=0., supplemental_static_engine_apply_calls=0,
        supplemental_proof_scope='Source control flow only; not journal observation, no reservation credit')


def validate_config(config):
    if config.get('schema') != 'jepa-public-input-binding-recovery-config/1' or config.get('limits') != CAPS:
        raise ValueError('exact new-cycle schema and ceilings required')
    if config.get('config_sha256') != digest({k:v for k,v in config.items() if k != 'config_sha256'}):
        raise ValueError('frozen config digest differs')
    if config.get('parent_pins') != PARENT_PINS or config.get('parent_final_chains') != PARENT_CHAINS or config.get('prior_exposure') != PRIOR_EXPOSURE:
        raise ValueError('both prior journals, sealed evidence and prior exposure must be linked')
    prior_time = config.get('prior_charged_seconds', {})
    if set(prior_time) != {'pr36', 'pr37', 'linked_two_cycle_total'} or any(nonnegative(v) != v for v in prior_time.values()) or prior_time['linked_two_cycle_total'] != prior_time['pr36'] + prior_time['pr37']:
        raise ValueError('exact derived scoped prior charged-time subtotal required')
    if config.get('recovery_cumulative_limits') != CUMULATIVE_CAPS:
        raise ValueError('explicit v1+v2 cumulative allocation required; no reset')
    carried = config.get('recovery_parent', {})
    if carried.get('charged_native_applies') != 80 or carried.get('observed_native_applies', 1) is not None or carried.get('analysis_charged_seconds') != 0:
        raise ValueError('retain failed v1 reservation and unconsumed shared analysis allocation')
    stages = config.get('analysis_stages')
    if stages != ANALYSIS_STAGES:
        raise ValueError('freeze exactly two once-only15-second analysis stages')
    if any(not nonnegative(v) or v > CAPS['analysis_seconds'] for v in stages.values()) or sum(stages.values()) > CAPS['analysis_seconds']:
        raise ValueError('analysis allocation exceeds30 cumulative seconds')
    if not isinstance(config.get('pins'), list) or not config['pins']:
        raise ValueError('source/plan/command/input pins required')
    commands = config.get('analysis_commands', {})
    if set(commands) != set(ANALYSIS_STAGES): raise ValueError('freeze both complete analysis commands')
    for command in commands.values():
        if set(command) != {'argv', 'outputs'} or not command['argv'] or not command['outputs']:
            raise ValueError('exact structured argv and output selection required')
        if any(not isinstance(x,str) for x in command['argv']) or not Path(command['argv'][0]).is_absolute():
            raise ValueError('absolute script argv required')
        if any(not isinstance(x,str) or not Path(x).is_absolute() for x in command['outputs']):
            raise ValueError('absolute predetermined analysis outputs required')


def state(records):
    chain(records)
    result = dict(initialized=False, config=None, pending=None, seen_stages=[], completed_stages=[], attempts=0, failures=0,
                  charged_seconds=0., observed_seconds=0., phase_charged_seconds=dict(native=0., analysis=0.),
                  charged_native_applies=0, observed_native_applies=0, native_exposure_verified=True,
                  known_native_apply_lower_bound=0, neural_forwards=0, optimizer_updates=0,
                  numerical_fits=0, paid_jobs=0, paid_spend_usd=0., ceiling_violated=False,
                  parent_pins=PARENT_PINS, parent_final_chains=PARENT_CHAINS, prior_exposure=PRIOR_EXPOSURE)
    for i, row in enumerate(records):
        event, data = row['event'], row['data']
        if i == 0:
            if event != 'initialized' or data['ledger_path'] != str(LEDGER.resolve()):
                raise ValueError('one fixed canonical new ledger required')
            validate_config(data['config']); result.update(initialized=True, config=data['config'],
                prior_charged_seconds=data['config']['prior_charged_seconds'])
        elif event == 'attempt-intent':
            stage = data['stage']; native = stage in ('native-build', 'native-collect')
            if result['pending'] or stage in result['seen_stages'] or result['ceiling_violated']:
                raise ValueError('pending/repeated stage or prior violation blocks launch')
            if not native and stage not in result['config']['analysis_stages']:
                raise ValueError('stage not in frozen allocation')
            if stage == 'native-collect' and 'native-build' not in result['completed_stages']:
                raise ValueError('collection requires successfully completed build')
            seconds = (30. if stage == 'native-build' else 60.) if native else result['config']['analysis_stages'][stage]
            phase = 'native' if native else 'analysis'
            if result['phase_charged_seconds'][phase] + seconds > CAPS[phase + '_seconds'] or result['charged_seconds'] + seconds > CAPS['total_seconds']:
                raise ValueError('full stage reservation no longer fits cumulative allowance')
            expected = dict(phase='native' if native else 'analysis', seconds=seconds,
                            native_applies=80 if stage == 'native-collect' else 0, neural_forwards=0, optimizer_updates=0,
                            numerical_fits=0, paid_jobs=0)
            if data['reservation'] != expected or data['attempt'] != result['attempts'] + 1:
                raise ValueError('exact fixed allocation/attempt sequence required')
            result['attempts'] += 1; result['seen_stages'].append(stage); result['pending'] = data
        elif event == 'attempt-finish':
            pending = result['pending']
            if pending is None or data['attempt'] != pending['attempt'] or data['status'] not in ('completed', 'failed'):
                raise ValueError('finish must close matching started attempt')
            elapsed = nonnegative(data['active_seconds']); calls = nonnegative(data['observed_native_applies'], True)
            reserve = pending['reservation']; failed = data['status'] == 'failed'
            verified = data['native_exposure_verified']
            if type(verified) is not bool or (not failed and not verified):
                raise ValueError('completed stage requires verified native exposure/no-launch proof')
            if any(data[k] != 0 for k in ('neural_forwards', 'optimizer_updates', 'numerical_fits', 'paid_jobs', 'paid_spend_usd')):
                raise ValueError('neural/optimizer/fits/paid work unauthorized')
            if not failed and (elapsed > reserve['seconds'] or calls > reserve['native_applies']):
                raise ValueError('completed stage violates allocation; retain as failed')
            if pending['stage'] != 'native-collect' and (calls or not verified):
                raise ValueError('build/analysis requires proven zero native calls')
            charged_time = max(elapsed, reserve['seconds']) if failed else elapsed
            charged_calls = max(calls, reserve['native_applies']) if failed else calls
            result['charged_seconds'] += charged_time; result['observed_seconds'] += elapsed
            result['phase_charged_seconds'][reserve['phase']] += charged_time
            result['charged_native_applies'] += charged_calls; result['known_native_apply_lower_bound'] += calls
            result['native_exposure_verified'] &= verified
            result['observed_native_applies'] = result['known_native_apply_lower_bound'] if result['native_exposure_verified'] else None
            if not failed: result['completed_stages'].append(pending['stage'])
            result['failures'] += failed; result['pending'] = None
            result['ceiling_violated'] = (elapsed > reserve['seconds'] or calls > reserve['native_applies'] or
                result['charged_seconds'] > 120 or result['charged_native_applies'] > 80 or
                result['phase_charged_seconds']['native'] > 90 or result['phase_charged_seconds']['analysis'] > 30)
        else: raise ValueError('no reset, retry, credit or amendment event supported')
    if result['initialized']:
        carried = result['config']['recovery_parent']
        cumulative = dict(charged_native_applies=carried['charged_native_applies'] + result['charged_native_applies'],
            observed_native_applies=None, observed_v2_native_applies=result['observed_native_applies'],
            supplemental_static_v1_engine_applies=0, native_charged_seconds=carried['charged_native_seconds'] + result['phase_charged_seconds']['native'],
            analysis_charged_seconds=carried['analysis_charged_seconds'] + result['phase_charged_seconds']['analysis'])
        cumulative['total_charged_seconds'] = cumulative['native_charged_seconds'] + cumulative['analysis_charged_seconds']
        result['recovery_cumulative'] = cumulative
        result['ceiling_violated'] |= (cumulative['charged_native_applies'] > 160 or cumulative['native_charged_seconds'] > 180 or cumulative['analysis_charged_seconds'] > 30 or cumulative['total_charged_seconds'] > 210)
    result['last_record_sha256'] = records[-1]['record_sha256'] if records else '0' * 64
    return result


def append(stream, records, event, data):
    body = dict(sequence=len(records), previous_sha256=chain(records), event=event, data=data)
    row = dict(body, record_sha256=digest(body)); current = state([*records, row])
    stream.seek(0, os.SEEK_END); stream.write(encoded(row).decode() + '\n'); stream.flush(); os.fsync(stream.fileno())
    records.append(row); return current


def canonical(path):
    if Path(path).is_symlink() or Path(path).resolve() != LEDGER.resolve():
        raise ValueError('only the canonical linked campaign journal is valid')
    return LEDGER.resolve()


def initialize(config_path, ledger=LEDGER):
    ledger = canonical(ledger); config = json.loads(Path(config_path).read_text()); validate_config(config)
    if verify_parents() != config['prior_charged_seconds']: raise ValueError('prior charged-time source differs')
    if recovery_parent() != config['recovery_parent']: raise ValueError('exact failed-v1 parent state differs')
    verify_pins(config['pins'])
    if str(Path(__file__).resolve()) not in {p['path'] for p in config['pins']}:
        raise ValueError('accounting source must be frozen')
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open('x+') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return append(stream, [], 'initialized', dict(ledger_path=str(ledger), config=config, config_file=pin(config_path)))


@contextmanager
def lease(ledger=LEDGER):
    with canonical(ledger).open('r+') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = read_rows(stream); current = state(records)
        if not current['initialized'] or current['pending']: raise ValueError('initialized, finished journal required')
        yield stream, records, current


def start(stream, records, stage, metadata):
    current = state(records)
    if verify_parents() != current['config']['prior_charged_seconds']: raise ValueError('prior charged-time source differs')
    if recovery_parent() != current['config']['recovery_parent']: raise ValueError('exact failed-v1 parent state differs')
    verify_pins(current['config']['pins'])
    native = stage in ('native-build', 'native-collect')
    seconds = (30. if stage == 'native-build' else 60.) if native else current['config']['analysis_stages'][stage]
    return append(stream, records, 'attempt-intent', dict(attempt=current['attempts'] + 1, stage=stage,
        reservation=dict(phase='native' if native else 'analysis', seconds=seconds, native_applies=80 if stage == 'native-collect' else 0,
                         neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_jobs=0), metadata=metadata))


def finish(stream, records, status, active_seconds, native_applies=0, proofs=None, native_journal_verified=True):
    pending = state(records)['pending']
    if pending is None: raise ValueError('no pending stage')
    return append(stream, records, 'attempt-finish', dict(attempt=pending['attempt'], status=status,
        active_seconds=active_seconds, observed_native_applies=native_applies,
        native_exposure_verified=native_journal_verified, neural_forwards=0,
        optimizer_updates=0, numerical_fits=0, paid_jobs=0, paid_spend_usd=0., proofs=proofs or []))
