'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { Env } = require('../../../engine/env');
const { fixture } = require('../pipeline/ambush-context-probe-fixture');
test('raw Ambush-context plans use actual paid plays, exact combat context, and complete games', { skip: !process.env.AMBUSH_CONTEXT_POOL || !process.env.AMBUSH_CONTEXT_PLANS }, async () => {
    const poolBytes = fs.readFileSync(process.env.AMBUSH_CONTEXT_POOL), planBytes = fs.readFileSync(process.env.AMBUSH_CONTEXT_PLANS);
    const pool = require('../../../bots/omni/rs/pool').loadPool(process.env.AMBUSH_CONTEXT_POOL), plans = JSON.parse(planBytes), cases = plans.cases ?? (Array.isArray(plans) ? plans : Object.values(plans)).flatMap(p => p.cases);
    const poolBefore = JSON.stringify(pool), plansBefore = JSON.stringify(plans), env = new Env(), receipts = [];
    assert.ok(cases.length > 0); assert.ok(pool.cards.every(c => !Object.hasOwn(c, 'keywordValues')), 'Unenriched raw card metadata only');
    for (const [i, scenario] of cases.entries()) {
        try {
            const result = await fixture(env, pool, scenario, 28700 + i);
            assert.ok(result.records.at(-1).winner);
            for (const state of result.records.filter(r => r.type === 'state').map(r => r.state)) {
                for (const player of Object.values(state.players)) for (const unit of [...player.ground, ...player.space]) if (unit.name === 'heroic-purrgil') {
                    assert.equal(unit.phaseStats, undefined, 'Persistent Ambush condition never exported as phase delta');
                    assert.equal(unit.power, 3, 'Stable snapshots are outside source Ambush context');
                }
            }
            const pending = result.witness.observations.find(o => o.stage === 'pending-real-defender-death');
            if (scenario.probe.scenario.startsWith('defender-death')) { assert.ok(pending); assert.equal(pending.sourcePower, 5); assert.equal(pending.attacking, true); assert.equal(pending.isAmbush, true); assert.equal(pending.state, undefined, 'No fabricated pending import snapshot'); }
            if(scenario.probe.assertDefenderNoBonus){const combat=result.witness.events.find(e=>e.name==='combat-context'&&e.ambush);assert.ok(combat);assert.equal(combat.power,5);assert.equal(combat.defenderPower,3);assert.equal(combat.defenderAttacking,false);assert.equal(combat.defenderAmbushContext,true);}
            receipts.push({ id: scenario.id, winner: result.records.at(-1).winner });
            if (process.env.AMBUSH_CONTEXT_RECORDINGS) { fs.mkdirSync(process.env.AMBUSH_CONTEXT_RECORDINGS, { recursive: true }); fs.writeFileSync(path.join(process.env.AMBUSH_CONTEXT_RECORDINGS, i + '.json'), JSON.stringify(result)); }
        } catch (error) {
            if (process.env.AMBUSH_CONTEXT_RECORDINGS) { fs.mkdirSync(process.env.AMBUSH_CONTEXT_RECORDINGS, { recursive: true }); fs.writeFileSync(path.join(process.env.AMBUSH_CONTEXT_RECORDINGS, i + '-failed.json'), JSON.stringify({ error: error.message, stack: error.stack, diagnostic: error.diagnostic })); }
            throw error;
        }
    }
    assert.equal(JSON.stringify(pool), poolBefore); assert.equal(JSON.stringify(plans), plansBefore);
    if (process.env.AMBUSH_CONTEXT_RECORDINGS) fs.writeFileSync(path.join(process.env.AMBUSH_CONTEXT_RECORDINGS, 'receipt.json'), JSON.stringify({ poolSha256: require('crypto').createHash('sha256').update(poolBytes).digest('hex'), plansSha256: require('crypto').createHash('sha256').update(planBytes).digest('hex'), receipts }, null, 2));
});

test('invalid negative-wound Legacy construction is rejected before starting the engine', async () => {
    await assert.rejects(fixture(null, null, { probe: { family: 'ambush-context', targets: [{ damage: -2 }] } }, 0), /Physical construction never uses negative damage/);
});
