'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { Env } = require('../../../engine/env');
const { fixture } = require('../pipeline/distributed-damage-probe-fixture');
test('raw distributed-damage plans execute without enriching pool or probes', { skip: !process.env.DISTRIBUTED_DAMAGE_POOL || !process.env.DISTRIBUTED_DAMAGE_PLANS }, async () => {
    const poolBytes = fs.readFileSync(process.env.DISTRIBUTED_DAMAGE_POOL), plansBytes = fs.readFileSync(process.env.DISTRIBUTED_DAMAGE_PLANS);
    const pool = JSON.parse(poolBytes), plans = JSON.parse(plansBytes), beforePool = JSON.stringify(pool), beforePlans = JSON.stringify(plans), env = new Env();
    assert.ok(pool.cards.every(c => !Object.hasOwn(c, 'keywordValues')), 'Raw prepared metadata only');
    const cases = plans.cases ?? (Array.isArray(plans) ? plans : Object.values(plans)).flatMap(p => p.cases), receipts = [];
    assert.ok(cases.length > 0);
    for (const [i, scenario] of cases.entries()) {
        try {
            const result = await fixture(env, pool, scenario, 11900 + i);
            assert.ok(result.records.at(-1).winner);
            receipts.push({ id: scenario.id, winner: result.records.at(-1).winner });
            if (process.env.DISTRIBUTED_DAMAGE_RECORDINGS) { fs.mkdirSync(process.env.DISTRIBUTED_DAMAGE_RECORDINGS, {recursive:true}); fs.writeFileSync(path.join(process.env.DISTRIBUTED_DAMAGE_RECORDINGS, i+'.json'), JSON.stringify(result)); }
        } catch (error) {
            if (process.env.DISTRIBUTED_DAMAGE_RECORDINGS) { fs.mkdirSync(process.env.DISTRIBUTED_DAMAGE_RECORDINGS, {recursive:true}); fs.writeFileSync(path.join(process.env.DISTRIBUTED_DAMAGE_RECORDINGS, i+'-failed.json'), JSON.stringify({ error: error.message, stack: error.stack, diagnostic: error.diagnostic })); }
            throw error;
        }
    }
    assert.equal(JSON.stringify(pool), beforePool); assert.equal(JSON.stringify(plans), beforePlans);
    if (process.env.DISTRIBUTED_DAMAGE_RECORDINGS) fs.writeFileSync(path.join(process.env.DISTRIBUTED_DAMAGE_RECORDINGS, 'receipt.json'), JSON.stringify({ poolSha256: require('crypto').createHash('sha256').update(poolBytes).digest('hex'), plansSha256: require('crypto').createHash('sha256').update(plansBytes).digest('hex'), receipts }, null, 2));
});
