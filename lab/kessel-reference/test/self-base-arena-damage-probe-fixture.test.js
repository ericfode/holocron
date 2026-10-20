'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const { fixture, dependencies } = require('../pipeline/self-base-arena-damage-probe-fixture');
test('self-base then arena fixture rejects another source or amount before construction', async () => {
    for (const probe of [{ family: 'self-base-arena-damage', cardId: 'SOR_001', amount: 5 }, { family: 'self-base-arena-damage', cardId: 'ASH_151', amount: 4 }]) {
        await assert.rejects(fixture(null, null, { probe }, 1), assert.AssertionError);
    }
    assert.ok(dependencies.includes('kessel:cards/pipeline/self-base-arena-damage-probes.js'));
});
test('raw paid Operation Cinder probes preserve source timing, terminal choices and exact actions', { skip: !process.env.SELF_BASE_ARENA_DAMAGE_POOL || !process.env.SELF_BASE_ARENA_DAMAGE_PLANS }, async () => {
    const poolBytes = fs.readFileSync(process.env.SELF_BASE_ARENA_DAMAGE_POOL), plansBytes = fs.readFileSync(process.env.SELF_BASE_ARENA_DAMAGE_PLANS);
    const pool = JSON.parse(poolBytes), plans = JSON.parse(plansBytes);
    const beforePool = JSON.stringify(pool), beforePlans = JSON.stringify(plans);
    assert.ok(pool.cards.every(c => !Object.hasOwn(c, 'keywordValues')), 'Raw compiled pool, no author metadata enrichment');
    const cases = plans.cases ?? (Array.isArray(plans) ? plans : Object.values(plans)).flatMap(p => p.cases);
    assert.ok(cases.length > 0);
    const { Env } = require('../../../engine/env'), env = new Env(), receipts = [];
    const output = process.env.SELF_BASE_ARENA_DAMAGE_RECORDINGS;
    if (output) fs.mkdirSync(output, { recursive: true });
    for (const [i, scenario] of cases.entries()) {
        try {
            const result = await fixture(env, pool, scenario, 15100 + i);
            assert.equal(result.records.at(-1).type, 'result'); assert.ok(result.records.at(-1).winner);
            assert.equal(result.records.at(-1).state.winner, result.records.at(-1).winner);
            assert.ok(result.witness.observations.some(x => x.stage === 'resolved-own-base-then-arena'));
            receipts.push({ id: scenario.id, sourceSeat: scenario.probe.sourceSeat, scenario: scenario.probe.scenario, winner: result.records.at(-1).winner, decisions: result.records.filter(x => x.type === 'decision').length });
            if (output) fs.writeFileSync(path.join(output, i + '.json'), JSON.stringify(result));
        } catch (error) {
            if (output) fs.writeFileSync(path.join(output, i + '-failed.json'), JSON.stringify({ error: error.message, stack: error.stack, diagnostic: error.diagnostic }));
            throw error;
        }
    }
    assert.equal(JSON.stringify(pool), beforePool); assert.equal(JSON.stringify(plans), beforePlans);
    const sha = b => crypto.createHash('sha256').update(b).digest('hex');
    if (output) fs.writeFileSync(path.join(output, 'receipt.json'), JSON.stringify({ poolSha256: sha(poolBytes), plansSha256: sha(plansBytes), receipts }, null, 2));
});
