"use strict";
const test = require('node:test');
const assert = require('node:assert/strict');
const state = require('./state');
const { supportProjection, supportGrants } = require('./support-state');
const { Env, seededRng } = require('../../../engine/env');
const probe = {"family": "cross-arena", "cardId": "ASH_037", "sourceSeat": 2, "mode": "support", "sourceArena": "space", "recipientCode": "ASH_261", "defenders": [{"code": "TWI_253"}], "expectedDefenderIndices": [0], "expectedBase": true, "cancelDefender": true, "donors": {"leader": "SOR_014"}};

test('actual cancelled Support snapshots bind captured registrations and reject mutants', async () => {
    const env = new Env(), pool = structuredClone(require('./pool.json'));
    const all = env.cardDataGetter.cardIds.map(id => env.cardDataGetter.getCardSync(id));
    for (const code of [probe.cardId, probe.recipientCode, ...probe.defenders.map(d => d.code)]) {
        if (pool.cards.some(c => c.setCode === code)) continue;
        const c = all.find(c => c.setId.set + '_' + String(c.setId.number).padStart(3, '0') === code);
        pool.cards.push({ ...c, setCode: code, keywordValues: Object.fromEntries(c.keywords.map(k => [k, 1])) });
    }
    const original = state.fullState, stop = new Error('captured actual residual window');
    let checked = 0; const capturedGames = new Set();
    state.fullState = function (eg, ...args) {
        if (capturedGames.has(eg)) throw stop;
        if (!eg.game.ongoingEffectEngine.effects.some(e => e.duration === 'untilEndOfAttack')) return original(eg, ...args);
        const registry = eg.game.ongoingEffectEngine.effects;
        const copy = registry.find(e => e.type === 'gainNonKeywordAbilitiesFromUnit' && e.duration === 'untilEndOfAttack');
        const keyword = registry.find(e => e.type === 'gainKeyword' && e.duration === 'untilEndOfAttack');
        const target = copy.source, donor = copy.getValue(target), wrapper = copy.impl.valueWrapper;
        const receipt = supportProjection(eg), rows = supportGrants(eg, receipt);
        assert.deepEqual(rows, [{kind:'sourcePrograms',target:eg.cardId(target.uuid),donor:eg.cardId(donor.uuid),sourcePrograms:{setCode:'ASH_037',side:'card'},keywords:Array(9).fill(0),presence:0}]);
        assert.deepEqual(original(eg, ...args).supportGrants, rows);
        assert.throws(() => state.phaseStats(target, {consumed:new Set([keyword])}), /Unsupported stat effect duration/);
        assert.throws(() => supportGrants({...eg}, receipt), /foreign projection receipt/);
        const mutate = (object, key, value) => {
            const old = object[key]; object[key] = value;
            try { assert.throws(() => supportProjection(eg), /Unsupported Support projection/); }
            finally { object[key] = old; }
        };
        mutate(copy.ongoingEffect, 'ability', {...copy.ongoingEffect.ability});
        mutate(copy.ongoingEffect, 'condition', () => true);
        delete copy.ongoingEffect.condition;
        mutate(donor.cardData, 'hp', donor.cardData.hp + 1);
        const donorConstants = donor.getConstantAbilities;
        donor.getConstantAbilities = () => { throw new Error('live donor reread'); };
        try { assert.deepEqual(supportGrants(eg, supportProjection(eg)), rows); } finally { donor.getConstantAbilities = donorConstants; }
        const keywordValue = keyword.getValue;
        keyword.getValue = () => [{keyword:'raid',amount:0},{keyword:'sentinel'}];
        try { const row = supportGrants(eg, supportProjection(eg))[0]; assert.equal(row.presence,65); assert.deepEqual(row.keywords,[1,0,0,0,0,0,0,0,0]); } finally { keyword.getValue = keywordValue; }
        mutate(target, 'controller', donor.controller.opponent);
        mutate(keyword, 'getValue', () => [{keyword:'raid',amount:-1}]);
        mutate(keyword, 'getValue', () => [{keyword:'raid',amount:65535},{keyword:'raid',amount:1}]);
        mutate(keyword, 'getValue', () => [{keyword:'support'}]);
        mutate(keyword, 'getValue', () => [{keyword:'sentinel',condition:true}]);
        const map = wrapper._constantAbilityUuidsByTargetCard, ids = map.get(target.uuid);
        map.set(target.uuid, [...ids, ...ids]);
        assert.throws(() => supportProjection(eg), /closed captured registration/); map.set(target.uuid, ids);
        const constant = target.getConstantAbilities().find(a => a.uuid === ids[0]);
        mutate(constant.properties, 'gainAbilitySource', target);
        mutate(constant.properties, 'condition', () => true); delete constant.properties.condition;
        mutate(constant.registeredEffects[0], 'getValue', () => false);
        mutate(constant.registeredEffects[0], 'targetsSourceOnly', false);
        const old = wrapper._triggeredAbilityUuidsByTargetCard.get(target.uuid);
        wrapper._triggeredAbilityUuidsByTargetCard.set(target.uuid, ['extra']);
        assert.throws(() => supportProjection(eg), /closed captured registration/);
        wrapper._triggeredAbilityUuidsByTargetCard.set(target.uuid, old);
        // A recognized captured empty list is evidence. A missing companion is not.
        const index = registry.indexOf(keyword); registry.splice(index, 1);
        assert.throws(() => supportProjection(eg), /pairing/); registry.splice(index, 0, keyword);
        assert.deepEqual(supportGrants(eg, supportProjection(eg)), rows);
        checked++; capturedGames.add(eg); throw stop;
    };
    const fixturePath = require.resolve('../../../lab/kessel-reference/pipeline/cross-arena-probe-fixture');
    delete require.cache[fixturePath];
    const { fixture } = require(fixturePath);
    try {
        for (const sourceSeat of [1,2]) {
            await assert.rejects(fixture(env,pool,{name:'support-reference',id:'support-reference',probe:{...probe,sourceSeat},coverageObligationIds:[]},7500+sourceSeat), error => error === stop);
        }
    } finally { state.fullState = original; delete require.cache[fixturePath]; }
    assert.equal(checked, 2);
    for (const eg of capturedGames) {
        const rng = seededRng('support-terminal-proof'), before = original(eg).supportGrants;
        const target = eg.game.allCards.find(c => eg.cardId(c.uuid) === before[0].target);
        const pid = target.controller.id;
        const attack = eg.legalActions(pid).find(a => a.kind === 'card' && a.cardUuid === target.uuid);
        // Return priority through legal passes if the opponent owns the window.
        if (!attack) {
            const other = eg.ids.find(id => eg.isActionWindow(id));
            eg.apply(other, eg.legalActions(other).find(a => a.arg === 'pass'), rng);
        }
        eg.apply(pid, eg.legalActions(pid).find(a => a.kind === 'card' && a.cardUuid === target.uuid), rng);
        assert.equal(eg.over, false);
        assert.equal(eg.ids.some(id => eg.isActionWindow(id)), false);
        assert.throws(() => original(eg), /grant outside action window/);
        const cancel = eg.legalActions(pid).find(a => a.arg === 'cancel');
        assert.ok(cancel, 'actual pending normal attack is cancellable: '+JSON.stringify(eg.legalActions(pid).map(a=>({kind:a.kind,label:a.label,arg:a.arg})))); eg.apply(pid, cancel, rng);
        assert.deepEqual(original(eg).supportGrants, before);
        // Explicit terminal fixture preparation. Only subsequent legal inputs
        // resolve fatigue; standard natural-deck cases live in the fixture lane.
        const victim = target.controller.opponent;
        victim.base.damage = 29;
        for (const card of [...victim.drawDeck]) card.moveTo('discard');
        eg.game.resolveGameState(true);
        for (let i = 0; i < 100 && !eg.over; i++) {
            const actor = eg.ids.find(id => eg.legalActions(id).length);
            const actions = eg.legalActions(actor);
            const action = actions.find(a => a.arg === 'pass') ?? actions.find(a => a.arg === 'claimInitiative') ?? actions.find(a => a.arg === 'passAbility') ?? actions.find(a => a.arg === 'done') ?? actions.find(a => a.label === 'Choose nothing') ?? actions[0];
            eg.apply(actor, action, rng);
        }
        assert.equal(eg.over, true); assert.equal(eg.phase, 'regroup');
        assert.equal(eg.ids.some(id => eg.isActionWindow(id)), false);
        assert.deepEqual(original(eg).supportGrants, before);
    }
});
