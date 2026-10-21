'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const {kesselDir} = require('../kessel');
const router = require('../pipeline/probe-fixture');
const {loadPool} = require('../../../bots/omni/rs/pool');
const pool = loadPool(process.env.SWU_CANONICAL_ROUTING_POOL || path.join(kesselDir(), 'compiler/generated/runtime-pool.json'));
const leaves = ['attack-base-history-probe-fixture', 'modal-deck-movement-probe-fixture', 'resource-number-target-experience-fixture', 'generated-token-continuation-fixture'];
for (const name of leaves) test(name + ': canonical routing preserves exact raw validation', async () => {
    const leaf = require('../pipeline/' + name), before = structuredClone(leaf.RAW_CASES), raw = structuredClone(before[0]);
    const wrapped = {...structuredClone(raw), source: {module: '../pipeline/probe-fixture.js', scenario: raw.name}};
    let games = 0;
    const marker = new Error('newGame reached');
    const env = {newGame() {games++; throw marker;}};
    for (const scenario of [raw, wrapped]) {
        const count = games;
        await assert.rejects(router.fixture(env, pool, scenario, 1), error => error === marker);
        assert.equal(games, count + 1);
    }
    const count = games;
    await assert.rejects(leaf.fixture(env, pool, wrapped, 1));
    const invalidSources = [null, undefined, [], {module:'wrong',scenario:raw.name}, {module:'../pipeline/probe-fixture.js',scenario:'wrong'}, {...wrapped.source,extra:true}];
    for (const source of invalidSources) await assert.rejects(router.fixture(env,pool,{...structuredClone(raw),source},1));
    for (const wrappedInput of [false,true]) for (const nested of [false,true]) {
        const scenario = structuredClone(wrappedInput ? wrapped : raw);
        (nested ? scenario.probe : scenario).unknown = true;
        await assert.rejects(router.fixture(env,pool,scenario,1));
    }
    assert.equal(games,count,'Invalid metadata/fields reject before constructing any game');
    assert.deepEqual(leaf.RAW_CASES,before,'Complete raw case inventory remains unchanged');
    assert.deepEqual(raw,before[0]);
    assert.deepEqual(wrapped,{...before[0],source:{module:'../pipeline/probe-fixture.js',scenario:raw.name}});
});
test('legacy family retains its original scenario and source object', async () => {
    const legacy = require('../pipeline/arena-damage-probe-fixture'), original = legacy.fixture;
    const catalogue = require(kesselDir() + '/compiler/load-catalog').loadCatalog(path.join(kesselDir(),'compiler/generated'));
    const {planArenaDamageProbes} = require(kesselDir() + '/cards/pipeline/arena-damage-probes');
    const scenario = catalogue.cards.map(entry => planArenaDamageProbes(entry,{catalogue})).find(plan => plan?.cases?.some(c => c.probe?.family === 'arena-damage'))?.cases.find(c => c.probe?.family === 'arena-damage');
    assert.ok(scenario?.source,'Real legacy planner declares routing source');
    const before = structuredClone(scenario); let calls=0;
    legacy.fixture = async (_env,_pool,actual) => {calls++; assert.equal(actual,scenario); assert.equal(actual.source,scenario.source); return 'forwarded';};
    try {assert.equal(await router.fixture({},pool,scenario,1),'forwarded');} finally {legacy.fixture=original;}
    assert.equal(calls,1); assert.deepEqual(scenario,before);
});
