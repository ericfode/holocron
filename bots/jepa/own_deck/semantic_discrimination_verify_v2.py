"""Independent saved-data/output verification; never executes an engine or model.

Only stdlib modules load at import. Actual array checks are coordinator-only,
after the canonical once-only reservation and audited five-second own guard.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

import binding_transfer_verify as H

HERE = Path(__file__).resolve().parent
ORIGINAL_VERIFIER_SHA = 'e53cf89e85563a8eca7427a2d25950f23b1020091d2589ad163199b2f650aaf1'
ACCOUNTING_CORE_SHA = '15e0542a09a6c29c0ec1562cd63ab4c905a0a2d55ef61ad2e53dc7ef36fd562d'
ARMS = ('learned-full', 'frozen-full', 'printed-only', 'ID-only', 'public-only')
SEEDS = (17, 29, 43)
HELD = ('ASH_081', 'IBH_104')
HELPER_SHA = '859b1ec2af31fad806352c0672d82c810d371406dd169d1bfd3b3ef83843e903'
GUARD_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
PRINTED = ('cost', 'hp', 'power', 'unique', 'upgradePower', 'upgradeHp', 'aspects', 'traits', 'arena', 'keywords', 'types')
ENCODER = ('edge.', 'depth', 'kind.', 'value.', 'numeric.', 'leaf.', 'card_projection.')
BLOCKED = H.BLOCKED
pin, read, require = H.pin, H.read, H.require


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def npz(np, path):
    with np.load(path, allow_pickle=False) as values:
        return {key: values[key].copy() for key in values.files}


def parts(plan):
    output = plan['split']['root_partitions']
    require(set(output) == {'train', 'state_held', 'family_held', 'joint'}, 'four explicit split cells')
    require([len(output[k]) for k in ('train', 'state_held', 'family_held', 'joint')] == [13, 12, 4, 4], '33-root fixed split')
    require(sorted(i for values in output.values() for i in values) == list(range(33)), 'unique complete root assignment')
    return output


def primary(np, branch, arrays, manifest, plan):
    held = [i for cell in ('family_held', 'joint') for i in parts(plan)[cell]]
    anchors = [manifest['candidate_order'].index(r) for r in ('anchor_a', 'anchor_b')]
    output = {}
    for code, names in (('ASH_081', ('target_damage_delta',)), ('IBH_104', ('target_allowed', 'target_removed'))):
        heads = {}
        for name in names:
            h = manifest['target_names'].index(name); observations = []
            for i in held:
                if str(arrays['source_cards'][i]) != code:
                    continue
                known = [j for j in anchors if arrays['target_mask'][i, j, h] > 0]
                if known:
                    error = sum(abs(float(branch[i, j, h])-float(arrays['targets'][i, j, h])) for j in known)/len(known)
                    observations.append(dict(root=int(i), known=len(known), mae=error))
            heads[name] = dict(known_roots=len(observations), roots=observations,
                               mae=sum(v['mae'] for v in observations)/len(observations) if observations else None)
        values = [v['mae'] for v in heads.values()]
        output[code] = dict(heads=heads, mae=sum(values)/len(values) if all(v is not None for v in values) else None)
    return output


def primary_decision(correct, controls):
    """Each group/control: every seed improves, plus pooled >=10% reduction."""
    rows = []
    for group in HELD:
        for name, values in controls.items():
            c = [correct[str(s)][group]['mae'] for s in SEEDS]
            b = [values[str(s)][group]['mae'] for s in SEEDS]
            known = all(v is not None for v in c+b)
            relative = (sum(b)-sum(c))/sum(b) if known and sum(b) > 0 else None
            every = known and all(x < y for x, y in zip(c, b))
            rows.append(dict(group=group, control=name, corrected=c, baseline=b,
                strictly_better_every_seed=every, pooled_relative_reduction=relative,
                supported=every and relative is not None and sum(c)/3 <= .9*(sum(b)/3)))
    return dict(supported=all(v['supported'] for v in rows), comparisons=rows,
                rule='Every held group/seed strictly beats every listed control; >=10% pooled three-seed reduction separately per group/control. Undefined zero denominator remains null.')


def swap_decision(correct, swapped):
    output = {}
    for group in HELD:
        c = [correct[str(s)][group]['mae'] for s in SEEDS]
        w = [swapped[str(s)][group]['mae'] for s in SEEDS]
        known = all(v is not None for v in c+w)
        relative = (sum(w)-sum(c))/sum(c) if known and sum(c) > 0 else None
        every = known and all(a > b for a, b in zip(w, c))
        output[group] = dict(strictly_worse_every_seed=every, pooled_relative_worsening=relative,
                             supported=every and relative is not None and sum(w)/3 >= 1.1*(sum(c)/3))
    return dict(supported=all(v['supported'] for v in output.values()), groups=output,
                scope='Separate predeclared IR-sensitivity diagnostic, not an extra primary benefit gate.')


def paired(np, branch, arrays, manifest, plan):
    h = manifest['target_names'].index('target_allowed'); order = manifest['candidate_order']
    a, b = (order.index(role) for role in ('anchor_a', 'anchor_b'))
    output = []
    for p in plan['primary_pairs']:
        left, right = int(p['left_root']), int(p['right_root'])
        require(str(arrays['source_cards'][left]) == 'IBH_104' and str(arrays['source_cards'][right]) == 'LOF_077', 'D orientation is IBH104 minus LOF077')
        require(all(arrays['target_mask'][i, j, h] for i in (left, right) for j in (a, b)), 'D needs complete actual eligibility witnesses')
        truth = float(arrays['targets'][left, a, h]-arrays['targets'][left, b, h]-arrays['targets'][right, a, h]+arrays['targets'][right, b, h])
        prediction = float(branch[left, a, h]-branch[left, b, h]-branch[right, a, h]+branch[right, b, h])
        output.append(dict(id=p['id'], left_root=left, right_root=right, truth=truth, prediction=prediction,
                           absolute_error=abs(prediction-truth), direction_correct=prediction*truth > 0))
    require(len(output) == 4 and [r['truth'] for r in output] == [p['expected_D'] for p in plan['primary_pairs']] and sorted(set(r['truth'] for r in output)) == [-2., 2.], 'frozen native eligibility D reversal; intents nested in two scenarios')
    return dict(pairs=output, direction_accuracy=sum(r['direction_correct'] for r in output)/len(output),
                both_directions_correct=all(r['direction_correct'] for r in output),
                scope='Eligibility reversal across two public states; not execution of an unoffered action or an independent-sample count.')


def action_rank(np, branch, arrays, manifest, plan):
    """Only ASH081 world1, two actually committed actions, complete anchors."""
    order = manifest['candidate_order']; anchors = [order.index(r) for r in ('anchor_a', 'anchor_b')]
    h = manifest['target_names'].index('target_damage_delta')
    require(len(plan['primary_spec']['rank_pairs']) == 1, 'one fixed actual-action rank pair')
    spec = plan['primary_spec']['rank_pairs'][0]
    left, right = int(spec['left_root']), int(spec['right_root'])
    require(all(str(arrays['source_cards'][i]) == 'ASH_081' for i in (left, right)), 'only frozen ASH081 rank pair')
    committed = manifest['native_status']
    eligible = all(committed[i].get('committed') is True and committed[i].get('terminal') == 'settled-committed'
                   and all(arrays['target_mask'][i, j, h] for j in anchors) for i in (left, right))
    if not eligible:
        return dict(eligible=False, accuracy=None, supported=None, reason='Both actions must actually commit and all anchor damage outcomes be known.')
    utility = lambda values, i: -sum(float(values[i, j, h]) for j in anchors)
    truth = utility(arrays['targets'], left)-utility(arrays['targets'], right)
    prediction = utility(branch, left)-utility(branch, right)
    if H.sign(truth) == 0:
        return dict(eligible=False, accuracy=None, supported=None, native_contrast=truth, reason='Native utility tie; excluded, not an error or independent rank sample.')
    correct = truth*prediction > 0
    return dict(eligible=True, left_root=left, right_root=right, native_contrast=truth, predicted_contrast=prediction,
                accuracy=float(correct), supported=float(correct) >= .75, independent_native_pairs=1,
                utility='Negative sum of observed anchor A/B damage deltas; fixed assay coordinate, not strategic game value.')


def check_documents(checks, plan):
    docs = plan['documents']; printed = plan['printed_documents']; swapped = plan['swapped_documents']
    codes, train = plan['codes'], plan['train_codes']; donors = plan['donors']
    checks.check(len(codes) == len(docs) == len(printed) == len(swapped) == 8, 'eight-document-banks')
    for i, code in enumerate(codes):
        checks.check(set(docs[i]['printed']) == set(PRINTED), 'whole-printed-whitelist/'+code)
        checks.check(digest(docs[i]['printed']) == digest(printed[i]['printed']) == digest(swapped[i]['printed']), 'printed-byte-preservation/'+code)
        checks.check(set(printed[i]) == {'printed'}, 'printed-inspection-no-semantic-subtrees/'+code)
        donor = donors[code]; j = codes.index(donor)
        checks.check(donor != code and (code in train) == (donor in train), 'separate-TRAIN-held-donor-cycle/'+code)
        wanted = copy.deepcopy(docs[i]); wanted['abilities'] = copy.deepcopy(docs[j]['abilities'])
        checks.check(swapped[i] == wanted, 'only-abilities-swapped/'+code)
    checks.check(donors['ASH_081'] == 'IBH_104' and donors['IBH_104'] == 'ASH_081', 'fixed-held-ability-swap')
    checks.check([donors[c] for c in train] == train[1:]+train[:1], 'fixed-cyclic-TRAIN-ability-swap')


def typed_tokens(value, path=()):
    """Independent ordered typed traversal; no model/frontend invocation."""
    require(len(path) <= 32, 'no path truncation')
    if isinstance(value, dict):
        require(not set(value) & {'title', 'sourcePath', 'sourceHash', 'setCode', 'internalName', 'id', 'label', 'method'}, 'no identity/display token')
        result = [(path, 'node', 'object')]
        for key in sorted(value): result += typed_tokens(value[key], path+(key,))
        return result
    if isinstance(value, list):
        return [(path, 'length', len(value))] + [t for i, child in enumerate(value) for t in typed_tokens(child, path+(i,))]
    if type(value) is bool: return [(path, 'boolean', value)]
    if type(value) in (int, float):
        require(math.isfinite(value) and abs(value) <= 65535, 'finite bounded literal')
        return [(path, 'number', float(value))]
    if isinstance(value, str):
        require(len(value) <= 96, 'bounded rule atom')
        return [(path, 'enum', value)]
    require(value is None, 'typed literal required')
    return [(path, 'null', 'null')]


def check_banks(np, checks, plan, saved):
    docs = dict(full=plan['documents'], printed=plan['documents'], swapped_full=plan['swapped_documents'], swapped_printed=plan['documents'])
    vocab = plan['vocabularies']; lookup = {k: {v: i for i, v in enumerate(items)} for k, items in vocab.items()}
    numbers = [v for code, doc in zip(plan['codes'], docs['full']) if code in plan['train_codes'] for _, k, v in typed_tokens(doc) if k in ('number', 'length')]
    scale = max(1., float(np.std(numbers)))
    checks.metric(scale, plan['numeric_scale'], 'TRAIN-only-shared-rule-literal-scale')
    banks, signatures = {}, {}
    for flavor, documents in docs.items():
        bank = dict(path_ids=np.zeros((8,512,32),np.int64), path_lengths=np.zeros((8,512),np.int64), type_ids=np.zeros((8,512),np.int64), value_ids=np.zeros((8,512),np.int64), numeric=np.zeros((8,512,2),np.float32), token_mask=np.zeros((8,512),np.float32), slot_mask=np.ones(8,np.float32), identity_indices=np.asarray([plan['train_codes'].index(code)+1 if code in plan['train_codes'] else 0 for code in plan['codes']],np.int64))
        for i, doc in enumerate(documents):
            tokens = typed_tokens(doc); require(len(tokens) <= 512, 'no token truncation')
            for j, (path, kind, value) in enumerate(tokens):
                edges = [lookup['path'][('index:' if type(k) is int else 'key:')+str(k)] for k in path]
                bank['path_ids'][i,j,:len(path)] = edges; bank['path_lengths'][i,j] = len(path)
                bank['type_ids'][i,j] = lookup['type'][kind]; bank['value_ids'][i,j] = lookup['value']['NUMBER' if kind in ('number','length') else kind+':'+str(value)]
                bank['token_mask'][i,j] = 1
                if kind in ('number','length'): bank['numeric'][i,j] = (value/scale, np.sign(value)*np.log1p(abs(value)))
        if flavor in ('printed','swapped_printed'):
            for i, doc in enumerate(documents):
                keep = np.zeros(512, bool)
                for j, (path, _, _) in enumerate(typed_tokens(doc)): keep[j] = not path or path[0] == 'printed'
                for key in ('path_ids','path_lengths','type_ids','value_ids','numeric','token_mask'): bank[key][i,~keep] = 0
        for key, value in bank.items():
            checks.check(np.array_equal(saved[flavor+'_'+key], value), 'actual-bank/'+flavor+'/'+key)
            restricted = value.copy()
            for i, code in enumerate(plan['codes']):
                if code not in plan['train_codes']: restricted[i] = 0
            checks.check(np.array_equal(saved['restricted_'+flavor+'_'+key], restricted), 'no-held-TRAIN-bank/'+flavor+'/'+key)
        signatures[flavor] = []
        for i in range(8):
            h = hashlib.sha256()
            for key in sorted(bank):
                if key != 'identity_indices':
                    v = bank[key][i]; h.update(key.encode()+str(v.dtype).encode()+str(v.shape).encode()+v.tobytes())
            signatures[flavor].append(h.hexdigest())
        banks[flavor] = bank
    return signatures


def consumed_audit(np, checks, x, c, arrays, plan, signatures):
    result = {}
    for arm in ARMS:
        entries, seen, conflicts = [], {}, []
        for i, code in enumerate(arrays['source_cards'].astype(str)):
            signature = ('PUBLIC-ZERO' if arm == 'public-only' else 'ID:'+str(plan['train_codes'].index(code)+1 if code in plan['train_codes'] else 0) if arm == 'ID-only' else signatures['printed' if arm == 'printed-only' else 'full'][plan['codes'].index(code)])
            prefix = signature.encode()
            key = lambda row: hashlib.sha256(len(prefix).to_bytes(8,'little')+prefix+x[i].tobytes()+row.tobytes()).hexdigest()
            row = dict(source=key(c[i,arrays['selected_candidate_indices'][i]]), candidate=[key(v) for v in c[i]])
            entries.append(row)
            for kind, ykey, mkey, names in (('source','source_targets','source_mask', [s['name'] for s in plan['scalers']['source_targets']]), ('candidate','targets','target_mask',[s['name'] for s in plan['scalers']['targets']])):
                ys = arrays[ykey][i:i+1] if kind == 'source' else arrays[ykey][i]
                ms = arrays[mkey][i:i+1] if kind == 'source' else arrays[mkey][i]
                for j in range(len(ys)):
                    for h, name in enumerate(names):
                        if not ms[j,h]: continue
                        k = (kind,row['source'] if kind == 'source' else row['candidate'][j],name)
                        v = float(ys[j,h])
                        if k in seen and seen[k] != v: conflicts.append(dict(root=i,candidate=j,head=name))
                        else: seen[k] = v
        expected = plan['input_audits'][arm]
        checks.check(entries == expected['consumed_signatures'], 'actual-consumed-hashes/'+arm)
        checks.check(len(conflicts) == expected['conflict_count'], 'complete-known-label-conflicts/'+arm)
        if arm == 'learned-full': checks.check(not conflicts, 'full-typed-input-no-conflicting-known-labels')
        result[arm] = dict(consumed_signatures=entries, conflict_count=len(conflicts), conflicts=conflicts)
    return result


def native_labels(np, checks, raw, arrays, manifest):
    """Independently derive offered membership and actual-endpoint masks."""
    order = manifest['candidate_order']; worlds = manifest['plan']['worlds']
    cases = sorted(raw['cases'], key=lambda c: c['world_id'])
    require(raw['collectionComplete'] is True and len(cases) == 33 and [c['world_id'] for c in cases] == list(range(33)), 'all 33 typed native roots required')
    actions = lambda capture, identity: [a for a in capture['offeredActions'] if a.get('kind') == 'card' and a.get('card') == identity]
    ready = lambda capture: sum(not c['exhausted'] for c in capture['state']['players']['p1']['resources'])
    terminals = {}; calls = 0
    for i, (case, world) in enumerate(zip(cases, worlds)):
        require(case['engineError'] is None and case['applyCalls'] <= 4, 'no failed native root')
        require(case['card'] == world['source_code'] == str(arrays['source_cards'][i]) and case['partition'] == world['partition'], 'native/root/split alignment')
        before, refs = case['before'], case['refs']; intent = case['declared_intent']; q = order.index(intent['ref'])
        require(intent == dict(ref=world['intent_ref'], id=refs[world['intent_ref']], requires_target=True), 'fixed pre-action intent')
        require(manifest['public_before_records'][i] == dict(before=before, refs=refs, declared_intent=intent, observation_refs=case['observation_refs']), 'BEFORE feature record is original native capture')
        sy, sm = np.zeros(9,np.float32), np.zeros(9,np.float32)
        ty, tm = np.zeros((8,7),np.float32), np.zeros((8,7),np.float32); chosen = np.zeros((8,7),np.float32)
        sy[0], sm[0] = bool(actions(before,refs['source'])), 1
        last, selected, done, declined = before, [], [], []
        captures = [before]
        for j, step in enumerate(case['steps']):
            require(step['before'] == last and step['action'] in last['offeredActions'], 'every native applied action was actually offered')
            stage, action = step['stage'], step['action']
            if j == 0: require(stage == 'play-own-hand' and action in actions(last,refs['source']), 'own public source play')
            elif stage == 'chosen-target':
                require(last == case['targetPrompt'] and action in actions(last,intent['id']), 'chosen intended target was offered'); selected.append(step)
            elif stage == 'commit-one-selection':
                require(world['selection_mode'] == 'exactly-one-upTo' and len(selected) == 1 and last == case['selectionWitness'] and last['abilitySelection'] == [intent['id']] and action.get('arg') == 'done' and action.get('label') == 'Done', 'upTo requires exactly one selected identity and actual Done'); done.append(step)
            elif stage == 'decline-unoffered-target':
                require(last == case['targetPrompt'] and not actions(last,intent['id']) and action.get('arg') == 'cancel' and action.get('label') == 'Cancel', 'only actual offered Cancel'); declined.append(step)
            else: require(stage in ('accept-optional-trigger','use-no-effect-anyway','sole-trigger-order'), 'reviewed continuation only')
            last = step['after']; captures.append(last)
        require(case['lastObserved'] == last and len(selected) <= 1 and len(done) <= 1 and len(declined) <= 1, 'single selected action chronology')
        prompt = case['targetPrompt']; require(prompt is not None and prompt in captures and prompt['decision'] == 'AbilityTarget', 'complete reached native target prompt')
        for j, role in enumerate(order): ty[j,0], tm[j,0] = bool(actions(prompt,refs[role])), 1
        committed = bool(selected) and (world['selection_mode'] != 'exactly-one-upTo' or bool(done))
        require(case['intentOffered'] is bool(actions(prompt,intent['id'])) and case['intendedTargetCommitted'] is committed, 'native intent witnesses')
        terminal = case['terminalClassification']; terminals[terminal] = terminals.get(terminal,0)+1
        if terminal == 'unoffered-prompt-only':
            require(not committed and not declined and not actions(prompt,intent['id']) and case['final'] is None and prompt == last and case['completion'] == case['intentResolution'] == 'unoffered-observation-only' and not any(a.get('arg') == 'cancel' and a.get('label') == 'Cancel' for a in prompt['offeredActions']), 'mandatory unavailable intent remains observation-only')
        else:
            require(terminal in ('settled-committed','settled-cancelled') and case['final'] == last and last['settled'] is True and case['completion'] == 'settled' and (terminal == 'settled-committed') == committed and (terminal == 'settled-cancelled') == bool(declined), 'actual paid settled endpoint only')
            a, z = before['projections']['source'], last['projections']['source']; cost = ready(before)-ready(last)
            physical = z['present'] and z['zone'] in ('ground','space','discard','upgrade')
            sy[1:] = [physical,cost,z['in_arena'],z['zone']=='discard',z['zone']=='hand',z['damage']-a['damage'],z['shield_count']-a['shield_count'],z['exhausted']]; sm[1:6] = 1
            for h, field in ((6,'damage'),(7,'shield_count'),(8,'exhausted')): sm[h] = bool(z['in_arena'] and a['known'][field] and z['known'][field])
            if committed:
                require(physical and cost > 0, 'native effect must actually pay and commit source')
                for j, role in enumerate(order):
                    a, z = before['projections'][role], last['projections'][role]
                    require(a['id'] == z['id'] == refs[role], 'same physical observation endpoint')
                    removed = not z['present'] or z['zone'] in ('discard','absent'); ty[j,1], tm[j,1] = removed, 1
                    stable = not removed and a['present'] and z['present'] and a['zone'] == z['zone'] and ((a['in_arena'] and z['in_arena']) or (a['is_base'] and z['is_base']))
                    for h, field in enumerate(('damage','exhausted','shield_count','power','hp'),2):
                        if stable and a['known'][field] and z['known'][field]: ty[j,h], tm[j,h] = float(z[field])-float(a[field]), 1
                chosen[q] = tm[q]
        for key, value in (('source_targets',sy),('source_mask',sm),('targets',ty),('target_mask',tm),('chosen_only_target_mask',chosen)):
            checks.check(np.array_equal(arrays[key][i],value), 'independent-native-label/'+str(i)+'/'+key)
        checks.check(int(arrays['selected_candidate_indices'][i]) == q, 'declared-before-intent-index/'+str(i))
        status = manifest['native_status'][i]
        checks.check(status['committed'] == committed and status['terminal'] == terminal, 'typed-terminal/'+str(i))
        calls += case['applyCalls']
    checks.check(terminals == {k:v for k,v in manifest['terminal_counts'].items() if v}, 'all-valid-terminal-counts')
    checks.check(calls == raw['applyCalls'] == manifest['native_apply_calls'] and calls <= 128, 'native-counts-128-cap')
    return dict(roots=33, terminal_counts=terminals, native_applies=calls, known_future_scope='Only paid settled committed native endpoints; declined/prompt-only futures unknown.')


def support(np, checks, arrays, manifest, plan):
    train = parts(plan)['train']; output = {}
    for name in ('target_allowed','target_removed','target_damage_delta'):
        h = manifest['target_names'].index(name); templates = {}
        for template in sorted({manifest['template_ids'][i] for i in train}):
            ix = [i for i in train if manifest['template_ids'][i] == template]
            values = arrays['targets'][ix,1:,h][arrays['target_mask'][ix,1:,h] > 0]
            templates[template] = dict(zero=int((values==0).sum()), positive=int((values>0).sum()), negative=int((values<0).sum()))
        eligible = [k for k,v in templates.items() if v['positive'] and v['zero']]
        checks.check(len(eligible) >= 2, 'two-independent-positive-zero-TRAIN-templates/'+name)
        output[name] = dict(by_template=templates, eligible_templates=eligible)
    h = manifest['target_names'].index('target_damage_delta'); j = manifest['candidate_order'].index('own_base')
    values = sorted({float(arrays['targets'][i,j,h]) for i in train if str(arrays['source_cards'][i]) == 'LAW_133' and arrays['target_mask'][i,j,h]})
    checks.check(values == [-3.,-1.], 'one-template-native-healing-TRAIN-literals')
    expected = np.zeros_like(arrays['target_mask'])
    for i, code in enumerate(arrays['source_cards'].astype(str)):
        for name in manifest['plan']['primary_spec']['masks'].get(code,[]):
            h = manifest['target_names'].index(name)
            for role in ('anchor_a','anchor_b'):
                j = manifest['candidate_order'].index(role); expected[i,j,h] = arrays['target_mask'][i,j,h]
    checks.check(np.array_equal(arrays['primary_target_mask'],expected), 'explicit-primary-only-two-anchor-masks')
    return dict(heads=output, healing_values=values, negative_healing_templates=1)


def legacy_public(np, arrays, manifest):
    """Independent 18/34 public projection, with explicit unknown masks."""
    xs, cs = [], []; catalog = manifest['public_catalog_rows']
    for record in manifest['public_before_records']:
        require(set(record) == {'before', 'refs', 'declared_intent', 'observation_refs'}, 'strict BEFORE-only feature record')
        before, refs = record['before'], record['refs']; projections = before['projections']; source = projections['source']
        own = before['state']['players']['p1']; require(source['owner'] == 'p1' and source['zone'] == 'hand', 'own known hand source')
        for seat in ('p1', 'p2'):
            p = before['state']['players'][seat]
            require(not p['deck'] and (seat != 'p2' or not p['hand']), 'no hidden draw order or opponent private hand')
        counts = {a: 0 for a in H.ASPECTS}
        for role in ('base', 'leader'):
            item = own[role]; code = item.get('setCode') or item.get('code') or before['own_aspect_sources'][role]
            for a in catalog[code]['card']['aspects']:
                counts[a] += 1
        resources = own['resources']; require(all(type(c.get('exhausted')) is bool for c in resources), 'observed resource readiness')
        spaces = [p for p in projections.values() if p and p['owner'] == 'p1' and p['zone'] == 'space' and p['id'] != refs['source'] and p['present']]
        fighters = [p for p in projections.values() if p and p['owner'] == 'p1' and p['zone'] in ('ground', 'space') and p['id'] != refs['source'] and p['present'] and 'fighter' in catalog[p['code']]['card']['traits']]
        known = source['known']
        xs.append([sum(not c['exhausted'] for c in resources), 1., *[counts[a] for a in H.ASPECTS], len({p['id'] for p in spaces}), len({p['id'] for p in fighters}),
                   *[float(source[f]) if known[f] else 0. for f in ('power', 'hp', 'damage', 'exhausted')], *[float(known[f]) for f in ('power', 'hp', 'damage', 'exhausted')]])
        candidates = []
        for role in manifest['candidate_order']:
            p = projections[role]
            if p is None:
                candidates.append([0.]*34); continue
            require(p['id'] == refs[role], 'stable public candidate identity')
            card = catalog[p['code']]['card']; k = p['known']; fields = ('damage', 'hp', 'power', 'exhausted', 'shield_count', 'xp_count')
            require(all(type(k[f]) is bool for f in fields), 'strict physical known masks')
            val = {f: float(p[f]) if k[f] else 0. for f in fields}; rk = k['damage'] and k['hp']
            traits = card.get('traits'); tk = isinstance(traits, list) and all(isinstance(t, str) for t in traits); traits = set(traits or [])
            cost, unique = card.get('cost'), card.get('unique'); ck = type(cost) in (int, float) and math.isfinite(cost); uk = type(unique) is bool
            candidates.append([float(p['owner'] == 'p1'), float(p['owner'] == 'p2'), float(p['is_unit']), float(p['is_base']), float(p['zone'] == 'ground'), float(p['zone'] == 'space'), float(p['id'] == refs['source']), float(p['present']),
                val['damage'], val['hp'], val['hp']-val['damage'] if rk else 0., val['power'], val['exhausted'], val['shield_count'], val['xp_count'],
                float(k['damage']), float(k['hp']), float(rk), float(k['power']), float(k['exhausted']), float(k['shield_count']), float(k['xp_count']),
                *[float(t in traits) for t in ('imperial', 'creature', 'spectre')], float(tk), float(cost) if ck else 0., float(ck), float(unique) if uk else 0., float(uk),
                float('upgrade' in card['types']), float('leader' in card['types']), float('vehicle' in traits), float('fighter' in traits)])
        cs.append(candidates)
    return np.asarray(xs, np.float32), np.asarray(cs, np.float32)


def public_projection(np, arrays, manifest):
    """Independent public owner counts and intended-reference equality only."""
    rows = manifest['public_catalog_rows']
    order = manifest['candidate_order']
    xs, cs = [], []
    for record in manifest['public_before_records']:
        require(set(record) == {'before', 'refs', 'declared_intent', 'observation_refs'}, 'before-only record keys')
        before, refs = record['before'], record['refs']
        projections = before['projections']
        source = projections['source']
        require(source['known']['identity'] is True and source['known']['owner'] is True, 'public source knownness')
        own = source['owner']
        require(own in ('p1', 'p2'), 'public source owner')
        other = 'p2' if own == 'p1' else 'p1'

        def metadata(p):
            if p is None or p.get('dynamic_aspects') is True:
                return None
            if p.get('known', {}).get('printed_aspects', True) is not True:
                return None
            values = rows.get(p.get('code'), {}).get('card', {}).get('aspects')
            if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
                return None
            values = {x.strip().lower() for x in values}
            if not values <= set(H.ASPECTS):
                return None
            witness = p.get('printed_aspects')
            if witness is not None and (not isinstance(witness, list) or
                    {x.strip().lower() for x in witness} != values):
                return None
            return values

        units, complete = {}, True
        for role, p in projections.items():
            if p is None:
                continue
            require(p['id'] == refs[role] and p['known']['identity'] is True, 'public role identity')
            require(p.get('zone') not in ('hand', 'deck') or
                    (p['id'] == source['id'] and p['owner'] == own and p['zone'] == 'hand'), 'no opponent/private pile input')
            if p['known']['owner'] is not True or p['owner'] not in ('p1', 'p2'):
                complete = False
                continue
            if p['present'] and p['is_unit'] and p['zone'] in ('ground', 'space'):
                require(p['id'] not in units, 'duplicate native fixture unit role')
                units[p['id']] = p
        try:
            raw_ids = {p['id'] for seat in ('p1', 'p2') for zone in ('ground', 'space')
                       for p in before['state']['players'][seat][zone]}
            complete = complete and raw_ids == set(units)
        except (KeyError, TypeError):
            complete = False
        extension = []
        for owner in (own, other):
            values = [metadata(p) for p in units.values() if p['owner'] == owner]
            known = complete and all(v is not None for v in values)
            extension.extend(sum(a in v for v in values) if known else 0 for a in H.ASPECTS)
            extension.append(float(known))
        intent = record['declared_intent']
        target = refs.get(intent.get('ref'))
        intended_p = projections.get(intent.get('ref'))
        relation_known = (intent.get('requires_target') is True and target is not None and
                          intent.get('id') == target and intended_p is not None and
                          intended_p['id'] == target and intended_p['known']['identity'] is True)
        candidates = []
        for role in order:
            p = projections.get(role)
            values = metadata(p)
            known = p is not None and relation_known
            candidates.append([*(float(a in values) if values is not None else 0. for a in H.ASPECTS),
                               float(values is not None), float(refs[role] == target) if known else 0., float(known)])
        xs.append(extension)
        cs.append(candidates)
    x = np.concatenate((arrays['context_features'], np.asarray(xs, np.float32)), -1)
    c = np.concatenate((arrays['candidate_features'], np.asarray(cs, np.float32)), -1)
    require(x.shape == (len(arrays['source_cards']), 32) and c.shape == (len(arrays['source_cards']), 8, 43), 'final public input ABI')
    return x, c



def compare_evaluation(np, checks, pred, saved, arrays, manifest, plan, name):
    for cell, indices in parts(plan).items():
        ix = np.asarray(indices, np.int64)
        for p, y, m, specs in (('source', 'source_targets', 'source_mask', 'source_targets'), ('branch', 'targets', 'target_mask', 'targets')):
            for h, spec in enumerate(plan['scalers'][specs]):
                result = H.head_metrics(np, pred[p][..., h], arrays[y][..., h], arrays[m][..., h], ix, spec)
                expected = saved['cells'][cell]['heads'][spec['name']]
                for key, value in result.items():
                    checks.metric(value, expected[key], name+'/'+cell+'/'+spec['name']+'/'+key)
                for code in sorted({str(arrays['source_cards'][i]) for i in indices}):
                    ci = np.asarray([i for i in indices if str(arrays['source_cards'][i]) == code],np.int64)
                    card = H.head_metrics(np,pred[p][...,h],arrays[y][...,h],arrays[m][...,h],ci,spec)
                    expected_card = saved['cells'][cell]['per_card'][code][spec['name']]
                    for key, value in card.items():
                        if key not in ('rmse','max_abs_error','zero_sign_accuracy'):
                            checks.metric(value,expected_card[key],name+'/'+cell+'/'+code+'/'+spec['name']+'/'+key)
    p = primary(np, pred['branch'], arrays, manifest, plan)
    for code in HELD:
        checks.metric(p[code]['mae'], saved['primary'][code]['mae'], name+'/primary/'+code)
        for head, value in p[code]['heads'].items():
            checks.metric(value['mae'], saved['primary'][code]['heads'][head]['mae'], name+'/primary/'+code+'/'+head)
            checks.check(value['known_roots'] == saved['primary'][code]['heads'][head]['known_roots'], name+'/primary-support/'+code+'/'+head)
    d = paired(np,pred['branch'],arrays,manifest,plan); saved_d = saved['paired_contrasts']
    for row, expected in zip(d['pairs'],saved_d['pairs']):
        for key in ('id','left_root','right_root','truth','prediction','absolute_error','direction_correct'):
            checks.metric(row[key],expected[key],name+'/eligibility-D/'+row['id']+'/'+key)
    checks.metric(d['direction_accuracy'],saved_d['direction_accuracy'],name+'/D-direction-accuracy')
    rank = action_rank(np,pred['branch'],arrays,manifest,plan)
    checks.metric(rank['accuracy'],saved_d['action_outcome_rank_accuracy'],name+'/committed-action-rank')
    return p


def verify_saved(np, args, allowed, current, campaign):
    checks = H.Checks(); inputs = {}
    def checked(path):
        actual = pin(path); require(allowed.get(actual['path']) == actual, 'input lacks exact frozen/completed-stage pin: '+actual['path']); inputs[actual['path']] = actual; return actual
    for path in (args.plan, args.fit_dir/'result.json', args.baselines_dir/'result.json', args.fit_progress, args.baseline_progress): checked(path)
    plan, fit, baseline = read(args.plan), read(args.fit_dir/'result.json'), read(args.baselines_dir/'result.json')
    for expected in plan['pins']:
        checks.check(pin(expected['path']) == expected, 'sealed-source-data-pin/'+expected['path'])
    checked(plan['dataset']); checked(plan['manifest']); arrays = npz(np, plan['dataset']); manifest = read(plan['manifest'])
    checks.check(fit['status'] == baseline['status'] == 'completed', 'completed-owned-fit-and-baseline')
    checks.check(not fit['semantic_validated'] and not baseline['semantic_validated'], 'no-generic-semantic-qualification')
    parts(plan); check_documents(checks, plan)
    require(manifest['fit_admitted'] is True and not manifest['fit_blockers'] and manifest['errors'] == 0, 'native admission must precede fit')
    checked(manifest['native_receipt']['path']); checked(manifest['journal']['path'])
    checks.check(pin(manifest['native_receipt']['path']) == manifest['native_receipt'] and pin(manifest['journal']['path']) == manifest['journal'], 'exact-native-origin')
    native = native_labels(np,checks,read(manifest['native_receipt']['path']),arrays,manifest)
    train_support = support(np,checks,arrays,manifest,plan)
    require(arrays['targets'].shape == (33, 8, 7) and arrays['source_targets'].shape == (33, 9), 'fixed native ABI')
    train = set(plan['train_codes']); codes = arrays['source_cards'].astype(str)
    checks.check(len(train) == 6 and len(plan['codes']) == 8 and set(plan['codes'])-train == set(HELD), 'canonical-card-split')
    for cell, ix in parts(plan).items():
        checks.check(all((str(codes[i]) in train) == (cell in ('train', 'state_held')) for i in ix), 'identity-disjoint/'+cell)
    for key in ('source_mask', 'target_mask'):
        checks.check(np.isin(arrays[key], [0, 1]).all(), 'binary-known-mask/'+key)
    for key in ('context_features', 'candidate_features', 'targets', 'source_targets'):
        checks.check(np.isfinite(arrays[key]).all(), 'finite/'+key)
    x, c = legacy_public(np, arrays, manifest)
    checks.check(np.array_equal(x, arrays['context_features']), 'independent-public-18')
    checks.check(np.array_equal(c, arrays['candidate_features']), 'independent-public-34')
    rawx, rawc = public_projection(np, arrays, manifest)
    H.check_scalers(np, checks, arrays, plan, rawx, rawc)
    expected_x = (rawx-np.asarray(plan['scalers']['context_features']['center'], np.float32))/np.asarray(plan['scalers']['context_features']['scale'], np.float32)
    expected_c = (rawc-np.asarray(plan['scalers']['candidate_features']['center'], np.float32))/np.asarray(plan['scalers']['candidate_features']['scale'], np.float32)
    checked(args.fit_dir/'consumed-inputs.npz'); consumed = npz(np, args.fit_dir/'consumed-inputs.npz')
    checks.check(np.array_equal(consumed['context'], expected_x) and np.array_equal(consumed['candidate'], expected_c), 'actual-common-corrected-C1R1-inputs')
    for pair in plan['primary_pairs']:
        i,j = pair['left_root'],pair['right_root']
        checks.check(np.array_equal(rawx[i],rawx[j]) and np.array_equal(rawc[i,1:],rawc[j,1:]) and np.array_equal(expected_x[i],expected_x[j]) and np.array_equal(expected_c[i,1:],expected_c[j,1:]), 'D-actual-consumed-nonsource-public-equality/'+pair['id'])
    checked(args.fit_dir/'program-inputs.npz'); signatures = check_banks(np,checks,plan,npz(np,args.fit_dir/'program-inputs.npz'))
    consumed_checks = consumed_audit(np,checks,expected_x,expected_c,arrays,plan,signatures)
    checked(args.fit_dir/'training-schedule.npz'); schedule = npz(np,args.fit_dir/'training-schedule.npz')
    for key, wanted in dict(train_indices=np.asarray(parts(plan)['train']), seeds=np.asarray(SEEDS), arms=np.asarray(ARMS), selected_candidate_indices=arrays['selected_candidate_indices'], source_cards=arrays['source_cards'], donor_indices=np.asarray([plan['codes'].index(plan['donors'][c]) for c in plan['codes']])).items():
        checks.check(np.array_equal(schedule[key],wanted),'identical-TRAIN-schedule/'+key)
    checked(args.fit_dir/'contract.json'); contract = read(args.fit_dir/'contract.json')
    checks.check(contract['plan'] == pin(args.plan) and all(contract[k] == plan[k] for k in ('scalers','parameters','vocabularies','donors','bank_contract')), 'saved-fit-contract')
    for key in ('targets','target_mask','source_targets','source_mask','selected_candidate_indices'):
        checks.check(fit['true_label_hashes'][key] == baseline['original_label_hashes'][key] == H.array_hash(arrays[key]), 'unchanged-all-arms-label-mask-intent/'+key)
    correct, swapped, drows, ranks, metric_summaries = {}, {}, {}, {}, {}
    for seed in SEEDS:
        checked(args.fit_dir/f's{seed}-initial-checkpoint.npz'); initial = npz(np, args.fit_dir/f's{seed}-initial-checkpoint.npz'); master = H.named_tensor_hash(initial)
        initial_full = None
        for arm in ARMS:
            name = f's{seed}:{arm}'; record = fit['results'][name]
            checks.check(record['initial_state_sha256'] == record['master_initial_state_sha256'] == master, name+'/common-initial-all-weights')
            checked(args.fit_dir/f's{seed}-{arm}-checkpoint.npz'); weights = npz(np, args.fit_dir/f's{seed}-{arm}-checkpoint.npz')
            checks.check(set(weights) == set(initial), name+'/same-allocated-graph')
            for key in weights:
                changed = int(np.count_nonzero(weights[key] != initial[key])); delta = float(np.sqrt(np.sum((weights[key]-initial[key]).astype(np.float64)**2)))
                checks.metric(changed, record['weight_movement'][key]['changed'], name+'/movement/'+key)
                checks.metric(delta, record['weight_movement'][key]['delta_l2'], name+'/movement-l2/'+key)
                if (arm in ('frozen-full', 'ID-only', 'public-only') and key.startswith(ENCODER)) or (arm != 'ID-only' and key.startswith('identity.')):
                    checks.check(changed == 0, name+'/deliberately-frozen/'+key)
            for step in (0, 200):
                file = args.fit_dir/f's{seed}-{arm}-step{step}-predictions.npz'; checked(file); pred = npz(np, file)
                checks.check(pred['source'].shape == (33, 9) and pred['branch'].shape == (33, 8, 7) and pred['card_vectors'].shape == (8, 16), name+f'/step{step}/ABI')
                checks.check(all(np.isfinite(pred[k]).all() for k in ('source','branch','card_vectors')),name+f'/step{step}/finite')
                for key in ('source_cards', 'state_families', 'selected_candidate_indices'):
                    checks.check(np.array_equal(pred[key], arrays[key]), name+f'/step{step}/row-order/'+key)
                p = compare_evaluation(np, checks, pred, record['evaluations'][str(step)], arrays, manifest, plan, name+f'/step{step}')
                if step == 200:
                    correct.setdefault(arm, {})[str(seed)] = p; drows.setdefault(arm, {})[str(seed)] = paired(np, pred['branch'], arrays, manifest, plan)
                    ranks.setdefault(arm, {})[str(seed)] = action_rank(np, pred['branch'], arrays, manifest, plan); final = pred
                    if arm == 'frozen-full': checks.check(np.array_equal(pred['card_vectors'],frozen_initial),'frozen-full-bank-no-learning/'+str(seed))
                if step == 0:
                    if arm == 'learned-full': initial_full = pred['card_vectors']
                    if arm == 'frozen-full':
                        frozen_initial = pred['card_vectors']; checks.check(np.array_equal(frozen_initial,initial_full),'same-full-initial-bank/'+str(seed))
                if arm == 'ID-only': checks.check(np.count_nonzero(pred['card_vectors'][[plan['codes'].index(code) for code in HELD]]) == 0, name+f'/step{step}/held-UNK0')
                if arm == 'public-only': checks.check(np.count_nonzero(pred['card_vectors']) == 0, name+f'/step{step}/public-program-zero')
            file = args.fit_dir/f's{seed}-{arm}-step200-ability-swapped-predictions.npz'; checked(file); wrong = npz(np, file)
            swapped.setdefault(arm, {})[str(seed)] = compare_evaluation(np, checks, wrong, record['ability_swapped_evaluation'], arrays, manifest, plan, name+'/ability-swapped')
            if arm in ('printed-only', 'ID-only', 'public-only'):
                for key in ('source', 'branch', 'card_vectors'): checks.check(np.array_equal(final[key], wrong[key]), name+'/swap-no-effect/'+key)
    baseline_primary = {}
    for arm in ('zero', 'train_mean', 'public_ridge'):
        file = args.baselines_dir/(arm+'-predictions.npz'); checked(file); pred = npz(np, file)
        p = compare_evaluation(np, checks, pred, baseline['evaluations'][arm], arrays, manifest, plan, 'baseline/'+arm)
        baseline_primary[arm] = {str(seed): p for seed in SEEDS}
        if arm in ('zero','train_mean'):
            for key,ykey,mkey in (('source','source_targets','source_mask'),('branch','targets','target_mask')):
                values = []
                for h in range(arrays[ykey].shape[-1]):
                    iy = arrays[ykey][parts(plan)['train'],...,h]; im = arrays[mkey][parts(plan)['train'],...,h] > 0
                    values.append(float(iy[im].mean()) if im.any() and arm == 'train_mean' else 0.)
                checks.check(np.array_equal(pred[key],np.broadcast_to(np.asarray(values,np.float32),arrays[ykey].shape)), 'independent-TRAIN-constant/'+arm+'/'+key)
        if arm == 'public_ridge':
            held_rows = [i for i, code in enumerate(codes) if code not in train]
            checks.check(pred['source_design'].shape == (33, 75) and pred['branch_design'].shape == (33, 8, 75), 'public-ridge-75-columns')
            design = np.concatenate((np.repeat(expected_x[:, None, :], 8, axis=1), expected_c), axis=-1)
            checks.check(np.array_equal(pred['branch_design'], design) and np.array_equal(pred['source_design'], design[np.arange(33), arrays['selected_candidate_indices']]), 'public-ridge-only-common-public-75')
    import semantic_discrimination_repair_accounting as A
    fit_counts = campaign.progress_counts(args.fit_progress, 'fit'); baseline_counts = campaign.progress_counts(args.baseline_progress, 'baselines')
    checks.check(fit_counts['optimizer_updates'] == 3000 and fit_counts['neural_forwards'] == 3045, 'durable-3000-updates-3045-forwards')
    checks.check(baseline_counts['numerical_fits'] == baseline['head_fit_attempts'] == 16 and baseline['actual_lstsq_solver_calls'] <= 16, 'durable-16-head-fit-attempts')
    checks.check(current['cumulative']['native_ceiling'] == 336 and current['cumulative']['seconds_ceiling'] == 309.0888967496576 and current['cumulative']['observed_native_applies'] is None, 'unchanged-cumulative-carry-and-null-observed')
    checks.check(campaign.CAPS == dict(seconds=118.,native_applies=128,neural_forwards=3045,optimizer_updates=3000,numerical_fits=16,paid_jobs=0,paid_spend_usd=0.), 'exact-new-stage-caps')
    protected = campaign.prior['protected_files']
    checks.check(len(protected) == 80 and all(pin(p['path']) == p for p in protected), 'all-original-80-byte-protection')
    checks.check(all(pin(p['path']) == p for p in inputs.values()), 'all-verifier-inputs-unchanged')
    controls = {arm: values for arm, values in correct.items() if arm != 'learned-full'}; controls.update(baseline_primary)
    decision = primary_decision(correct['learned-full'],controls)
    decision.update(eligibility_D_passed=all(v['both_directions_correct'] for v in drows['learned-full'].values()))
    decision['primary_behavior_gate_passed'] = decision['supported'] and decision['eligibility_D_passed']
    sensitivity = swap_decision(correct['learned-full'],swapped['learned-full'])
    checks.check(decision['primary_behavior_gate_passed'] == baseline['gates']['primary_behavior_gate_passed'], 'independent-primary-gate')
    checks.check(sensitivity['supported'] == baseline['gates']['ability_sensitivity_gate_passed'], 'independent-separate-IR-sensitivity-gate')
    return dict(schema='jepa-semantic-discrimination-independent-verification/1', status='PASS' if not checks.mismatches else 'FAIL', check_count=checks.count, mismatches=checks.mismatches,
        primary_decision=decision, primary_scores=correct, baseline_primary_scores=baseline_primary,
        ability_swapped_primary_scores=swapped, wrong_IR_diagnostic=sensitivity, native_label_audit=native, TRAIN_support=train_support, actual_consumed_input_audits=consumed_checks,
        eligibility_D=drows, actual_committed_action_rank=ranks, counter_proofs=dict(fit=fit_counts, baselines=baseline_counts),
        input_pins=list(inputs.values()), independent_native_held_identities=2, semantic_validated=False, generic_semantic_gate='UNSUPPORTED',
        limitations=['One held healing card with one negative TRAIN template; composition test, not healing-family validation.',
                     'One held defeat-selector card; roots, heads, checks and seeds are dependent, not independent semantic samples.',
                     'Eligibility includes observed unavailable intents; no unoffered action is executed or assigned a future outcome.',
                     'Corrected C1R1 and all metadata remain fixed; ability swaps are final-evaluation diagnostics without optimization.'],
        native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_spend_usd=0)


def run(args):
    import semantic_discrimination_repair_accounting as A
    campaign = A.Campaign(args.spec)
    with campaign.lease() as (stream, rows, current):
        allowed = campaign.allowed_pins(rows)
        needed = [args.plan, args.fit_dir/'result.json', args.baselines_dir/'result.json', args.fit_progress, args.baseline_progress]
        metadata = dict(argv=[str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), *sys.argv[1:]],
                        outputs=[str(args.out.resolve()), str(args.receipt.resolve())], input_pins=[allowed[str(p.resolve())] for p in needed if str(p.resolve()) in allowed], guard=dict(cpu_workers=1, rss_bytes=1073741824))
        started = time.monotonic(); status = 'failed'; error = None; guard = None; proofs = []; active = [False]
        sys.addaudithook(lambda event, values: H.audit_event(event, values) if active[0] else None)
        try:
            campaign.start(stream, rows, 'verify', metadata)
            require(pin(H.__file__)['sha256'] == HELPER_SHA, 'frozen independent metric/public helpers')
            original = pin(HERE/'semantic_discrimination_verify.py')
            require(original['sha256'] == ORIGINAL_VERIFIER_SHA, 'original verifier stays frozen')
            require(campaign.config['source']['sha256'] == ACCOUNTING_CORE_SHA and pin(campaign.config['source']['path']) == campaign.config['source'], 'frozen accounting core stays explicit')
            require(campaign.config['provenance']['accounting_adapter'] == pin(A.__file__), 'exact versioned accounting adapter route')
            require(all(str(p.resolve()) in allowed for p in needed), 'all verifier input pins must be admitted')
            require(not args.out.exists() and not args.receipt.exists(), 'exclusive once-only verification outputs')
            require(not any(n.split('.')[0] in BLOCKED for n in sys.modules), 'no model or fit library preloaded')
            import effect_identifiability_fit as E
            require(pin(E.__file__)['sha256'] == GUARD_SHA, 'audited own-process guard source')
            chain = H.independent_chain(rows); remaining = 5.-(time.monotonic()-started); require(remaining > 0, 'preflight exhausted verification quota')
            guard = E.Guard(remaining); active[0] = True
            with guard:
                import numpy as np
                result = verify_saved(np, args, allowed, campaign.state(rows), campaign)
                result['independent_chain_at_verification_intent'] = chain
                result['versioned_repair_provenance'] = dict(original_verifier=original, accounting_adapter=pin(A.__file__), accounting_core=campaign.config['source'], parent_charged_native_applies=208, parent_charged_seconds=191.08889674965758, failed_metadata_charge_seconds=3., scientific_checks='Unchanged from original verifier; accounting imports, carried time ceiling and explicit route provenance only.')
                write_new(args.out, result); proofs.append(pin(args.out)); require(result['status'] == 'PASS', 'independent saved-output mismatches')
            status = 'completed'
        except BaseException as exc:
            pending = campaign.state(rows)['pending']
            if not pending or pending['stage'] != 'verify' or pending['owner_pid'] != os.getpid(): raise
            error = dict(type=type(exc).__name__, message=str(exc))
        finally:
            active[0] = False
        elapsed = time.monotonic()-started
        if elapsed > 5.: status = 'failed'; error = error or dict(type='BudgetExceeded', message='verification exceeded five seconds')
        receipt = dict(status=status, error=error, active_seconds=elapsed, guard=guard.receipt() if guard else None,
            authority='Append-only campaign ledger finish is authoritative; this receipt precedes final accounting checks.', source=pin(__file__), helper=pin(H.__file__), accounting_source=pin(A.__file__), accounting_core=campaign.config['source'], native_applies=0, neural_forwards=0, optimizer_updates=0, numerical_fits=0, paid_spend_usd=0, outputs=proofs, semantic_validated=False)
        if not args.receipt.exists(): write_new(args.receipt, receipt); proofs.append(pin(args.receipt))
        state = campaign.finish(stream, rows, status, elapsed, observed=A.zero_counts(), proofs=proofs, cleanup_verified=True, execution_ended=True, observed_verified=True)
        require(status == 'completed' and 'verify' in state['completed_stages'], 'failed bounded verifier retained')
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('spec', 'plan', 'fit-dir', 'fit-progress', 'baselines-dir', 'baseline-progress', 'out', 'receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    print(json.dumps(run(parser.parse_args()), allow_nan=False))


if __name__ == '__main__':
    main()
