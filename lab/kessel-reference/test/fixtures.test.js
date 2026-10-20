'use strict';
// Engine-side tests of the probe fixtures, split out of Kessel's planner tests (cards/test/*-probes.test.js) when
// the fixtures moved here. They plan with Kessel's planners and catalogue and then play the experiments in the
// pinned forceteki engine. Needs KESSEL_DIR (default ../kessel) and forceteki/build; run by hand (README.md).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { hasKessel, kessel, kesselPath } = require('../kessel');
if (!hasKessel()) { test('probe fixtures need a Kessel checkout', { skip: 'set KESSEL_DIR' }, () => {}); return; }

const catalogue = kessel('compiler/load-catalog').loadCatalog();
const runtimePool = kesselPath('compiler/generated/runtime-pool.json');
const copy = (value) => JSON.parse(JSON.stringify(value));
const find = (id) => catalogue.cards.find((c) => c.setCode === id);
const engineBuilt = fs.existsSync(path.resolve(__dirname, '../../../forceteki/build/server/game/core/Game.js'));
let env;
const engine = () => (env ??= new (require('../../../engine/env').Env)());
const loadPool = (file = runtimePool) => require('../../../bots/omni/rs/pool').loadPool(file);
const withCards = (pool, ids) => {
    for (const id of new Set(ids)) if (!pool.cards.some((c) => c.setCode === id)) pool.cards.push({ ...find(id).card, setCode: id });
    return pool;
};
const actorsAgree = (records) => {
    for (let i = 0; i < records.length; i++)
        if (records[i].type === 'state') {
            assert.equal(records[i + 1].type, 'decision');
            assert.equal(records[i].state.actor, records[i + 1].actor, 'State actor must match next decision actor');
        }
};

// From cards/test/probes.test.js
const { planCardProbes } = kessel('cards/pipeline/probes');
const plan = (id) => planCardProbes(find(id), { catalogue });

test('automatic fixtures execute real oracle experiments including expiry, lethal damage, invalid zone and live refresh', { skip: !engineBuilt }, async () => {
    const { fixture } = require('../pipeline/probe-fixture');
    const pool = loadPool();
    const scenarios = [
        plan('TWI_124').cases.find((c) => c.probe.waitForExpiry),
        plan('TWI_170').cases.find((c) => c.name.endsWith('-lethal')),
        plan('TWI_170').cases.find((c) => c.probe.negativeOnly),
        plan('JTL_052').cases.find((c) => c.probe.mutateSource),
    ];
    for (const [i, scenario] of scenarios.entries()) {
        const { records, witness } = await fixture(engine(), pool, scenario, 84000 + i);
        assert.equal(records.at(-1).type, 'result');
        actorsAgree(records);
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
    }
});

test('arena-list oracle constructions witness membership, expiry, empty sets and lethal batches', { skip: !engineBuilt }, async () => {
    const { fixture } = require('../pipeline/probe-fixture');
    const ids = ['TWI_126', 'TWI_075', 'TS26_048'], pool = withCards(loadPool(), ids);
    let seed = 85000;
    for (const id of ids) for (const scenario of plan(id).cases) {
        const { witness } = await fixture(engine(), pool, scenario, seed++);
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
        if (scenario.name.endsWith('simultaneous-lethal'))
            assert.ok(witness.observations.find((o) => o.stage === 'after-resolution').targets.every((t) => t.zone === 'discard'));
    }
});

test('defeat arena-list construction witnesses owners, global order, death triggers, attachments and tokens', { skip: !engineBuilt }, async () => {
    const { fixture } = require('../pipeline/probe-fixture');
    const ids = ['SOR_043', 'SEC_078', 'JTL_080'], scenarios = ids.flatMap((id) => plan(id).cases);
    const pool = withCards(loadPool(), [...ids, ...scenarios.flatMap((c) => c.setupCardIds)]);
    let seed = 86000;
    for (const scenario of scenarios) {
        const { witness } = await fixture(engine(), pool, scenario, seed++);
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
    }
    for (const id of ids) {
        const p = plan(id);
        assert.ok(p.cases.some((c) => c.probe.expectDraws));
        assert.ok(p.cases.some((c) => c.name.endsWith('attachments-reversed')));
        assert.ok(p.cases.some((c) => c.name.endsWith('token-lifecycle')));
    }
});

// From cards/test/cost-probes.test.js
test('actual engine cost-query experiments execute state changes, exact exclusions, cancellation, real deaths and attachments', { skip: !engineBuilt }, async () => {
    const { planCostProbes } = kessel('cards/pipeline/cost-probes'), { fixture } = require('../pipeline/cost-probe-fixture');
    const ids = ['HMW_154', 'HMW_249', 'SEC_154', 'TS26_079'];
    const pool = loadPool(process.env.SWU_COST_PROBE_POOL ?? runtimePool);
    let total = 0;
    for (const id of ids) for (const scenario of planCostProbes(find(id), { catalogue }).cases) {
        const { records, witness } = await fixture(engine(), pool, scenario, 970000 + total++);
        assert.equal(records.at(-1).type, 'result');
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
        assert.ok(witness.observations.some((o) => o.stage === 'after-resolution'));
        if (scenario.probe.shape === 'attach' && (scenario.probe.decline || scenario.probe.negativeOnly))
            assert.equal(witness.played, false, 'Later random play cannot rewrite a negative activation receipt');
        for (let i = 0; i < records.length; i++) if (records[i].type === 'state') assert.equal(records[i].state.actor, records[i + 1].actor);
    }
});

// From cards/test/on-defense-probes.test.js
test('actual defense attacks retain full actors/actions/states/results and finite source assertions', { skip: !engineBuilt }, async () => {
    const { planOnDefenseProbes } = kessel('cards/pipeline/on-defense-probes'), { fixture } = require('../pipeline/on-defense-probe-fixture');
    const ids = ['LOF_047', 'SHD_035', 'SOR_196', 'TS26_024', 'TWI_049', 'TWI_083'];
    const scenarios = ids.flatMap((id) => planOnDefenseProbes(find(id), { catalogue }).cases);
    const pool = withCards(loadPool(), scenarios.flatMap((c) => [...c.focusCardIds, ...c.setupCardIds]));
    let seed = 89000;
    for (const scenario of scenarios) {
        const { records, witness } = await fixture(engine(), pool, scenario, seed++);
        assert.ok(witness.declared);
        assert.equal(records.at(-1).type, 'result');
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
        actorsAgree(records);
    }
});

// From cards/test/upgrade-return-probes.test.js
test('actual pinned engine plays each source and witnesses upgrade return lifecycle boundaries', { skip: !engineBuilt }, async () => {
    const { planUpgradeReturnProbes } = kessel('cards/pipeline/upgrade-return-probes'), { fixture } = require('../pipeline/upgrade-return-probe-fixture');
    const ids = ['HMW_222', 'SHD_044', 'SHD_209', 'HMW_236', 'SEC_200'];
    const scenarios = ids.flatMap((id) => planUpgradeReturnProbes(find(id), { catalogue }).cases);
    const pool = withCards(loadPool(), scenarios.flatMap((c) => [...c.focusCardIds, ...c.setupCardIds]));
    let seed = 87000;
    for (const scenario of scenarios) {
        const { records, witness } = await fixture(engine(), pool, scenario, seed++);
        assert.equal(records.at(-1).type, 'result');
        assert.deepEqual(witness.coverageObligationIds, scenario.coverageObligationIds);
        assert.ok(witness.played);
    }
});

// From cards/test/arena-token-probes.test.js
const tokenExamples = ['ASH_064', 'SEC_119', 'SEC_252', 'SOR_037'].map(find);
test('source-derived entry title chooses renamed structural bulk correctly', () => {
    const { classifyArenaToken } = kessel('cards/pipeline/arena-token-probes'), { entryChoice } = require('../pipeline/arena-token-probe-fixture');
    const original = copy(tokenExamples[0]); original.abilities.card[0].title = 'Protect the qualifying units';
    const shape = classifyArenaToken(original); assert.ok(shape);
    const actions = [{ kind: 'button', label: 'Shielded' }, { kind: 'button', label: 'Protect the qualifying units' }];
    assert.equal(entryChoice(actions, { ...shape, entryOrder: 'bulk' }), actions[1]);
    assert.equal(entryChoice(actions, { ...shape, entryOrder: 'shielded' }), actions[0]);
});
test('all current arena-token plans roundtrip immutable library definitions and dependency closure', () => {
    const { planArenaTokenProbes } = kessel('cards/pipeline/arena-token-probes'), library = kessel('cards/reference/library'), core = require('../pipeline/probe-fixture');
    const all = tokenExamples.flatMap((e) => planArenaTokenProbes(e, { catalogue: catalogue.cards }).cases);
    assert.equal(all.length, 68);
    for (const scenario of all) assert.deepEqual(library.definition(scenario.id, library.registry(), scenario), scenario);
    for (const dependency of ['kessel:cards/pipeline/arena-token-probes.js', 'lab/kessel-reference/pipeline/arena-token-probe-fixture.js', 'bots/omni/rs/make-pool.js'])
        assert.ok(core.dependencies.includes(dependency), dependency);
});

// From cards/test/base-zone-probes.test.js
test('base-zone definitions roundtrip and central dependency closure includes both helpers', () => {
    const { planBaseZoneProbes } = kessel('cards/pipeline/base-zone-probes'), library = kessel('cards/reference/library'), core = require('../pipeline/probe-fixture');
    for (const e of ['TWI_019', 'TWI_028', 'HMW_007'].map(find))
        for (const scenario of planBaseZoneProbes(e, { catalogue }).cases) assert.deepEqual(library.definition(scenario.id, library.registry(), scenario), scenario);
    for (const dependency of ['kessel:cards/pipeline/base-zone-probes.js', 'lab/kessel-reference/pipeline/base-zone-probe-fixture.js', 'bots/omni/rs/make-pool.js'])
        assert.ok(core.dependencies.includes(dependency));
});
test('optional enemy leader is passed only at genuine deck2 construction boundary', async () => {
    const { planBaseZoneProbes } = kessel('cards/pipeline/base-zone-probes'), core = require('../pipeline/probe-fixture');
    const examples = ['TWI_019', 'TWI_028', 'HMW_007'].map(find), scenario = planBaseZoneProbes(examples[0], { catalogue }).cases[0];
    const probe = { cardId: scenario.probe.fillerCode, leaderCode: scenario.probe.ordinaryLeaderCode, baseCode: scenario.probe.ordinaryBaseCode, targets: [] };
    const pool = { cards: catalogue.cards.map((e) => ({ setCode: e.setCode, ...e.card })) };
    async function capture(p) {
        let seen;
        await assert.rejects(core.constructProbeFixture({ newGame(opts) { seen = opts; throw new Error('capture-deck-boundary'); } }, pool, { probe: p }, 77), /capture-deck-boundary/);
        return seen;
    }
    const standard = await capture(probe); assert.deepEqual(standard.deck2, standard.deck1);
    const distinct = await capture({ ...probe, enemyLeaderCode: examples[2].setCode });
    assert.deepEqual(distinct.deck1, standard.deck1); assert.equal(distinct.deck2.leader.id, examples[2].setCode);
    assert.deepEqual({ ...distinct.deck2, leader: distinct.deck1.leader }, distinct.deck1);
});

// From cards/test/keyword-inventory-probes.test.js
test('renamed structural Force donors retain identity-based gain/use assertions', () => {
    const p = kessel('cards/pipeline/keyword-inventory-probes'), { assertGainUseCheckpoint } = require('../pipeline/keyword-inventory-probe-fixture');
    const gain = structuredClone(find('LOF_193')), use = structuredClone(find('LOF_195'));
    gain.internalName = gain.card.internalName = 'alternate-gain'; gain.card.title = 'Alternate Gain';
    use.internalName = use.card.internalName = 'alternate-use'; use.card.title = 'Alternate Use';
    assert.ok(p.roleDonor(gain, 'gain-force')); assert.ok(p.roleDonor(use, 'use-ready'));
    const firstGain = { internalName: gain.internalName }, secondGain = { internalName: gain.internalName }, used = { internalName: use.internalName, exhausted: false };
    const extras = [{}, firstGain, used, secondGain];
    const host = { cardData: { hp: 4 }, keywords: [{ name: 'sentinel' }, { name: 'restore' }], getHp: () => 7 };
    for (const card of [firstGain, secondGain]) {
        assert.equal(assertGainUseCheckpoint(host, card, extras, { held: true }), 'gain');
        assert.throws(() => assertGainUseCheckpoint(host, card, extras, { held: false }));
    }
    host.keywords = [{ name: 'restore' }]; host.getHp = () => 5;
    assert.equal(assertGainUseCheckpoint(host, used, extras, { held: false }), 'use');
    assert.throws(() => assertGainUseCheckpoint(host, used, extras, { held: true }));
    used.exhausted = true;
    assert.throws(() => assertGainUseCheckpoint(host, used, extras, { held: false }));
});
