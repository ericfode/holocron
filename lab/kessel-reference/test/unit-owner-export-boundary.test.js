'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { Env } = require('../../../engine/env');
const { fullState } = require('../../../bots/omni/rs/state');
const { stateEvidence } = require('../../../bots/omni/rs/state-evidence');
const { constructProbeFixture } = require('../pipeline/probe-fixture');
const { kesselPath, kessel } = require('../kessel');
const env = new Env();
const pool = JSON.parse(fs.readFileSync(kesselPath('compiler/generated/runtime-pool.json')));
// Exporter-only attachment control regression: use the exact printed definition,
// without claiming this supplemented pool is a prepared runtime-admission proof.
const catalogue = kessel('compiler/load-catalog').loadCatalog();
for (const code of ['SHD_070']) if (!pool.cards.some(c => c.setCode === code)) {
    const entry = catalogue.cards.find(c => c.setCode === code);
    assert.ok(entry); pool.cards.push({ ...entry.card, setCode: code });
}
const scenario = { probe: { cardId: 'ASH_061', sourceArena: 'ground', sourceInPlay: false,
    targets: [{ code: 'ASH_061', owner: 'self', arena: 'ground' }, { code: 'ASH_061', owner: 'opponent', arena: 'ground' }, { code: 'SHD_070', owner: 'self', zone: 'hand' }, { code: 'SHD_070', owner: 'opponent', zone: 'hand' }] } };
const boundary = /Unsupported foreign-controlled unit physical ownership before export/;
for (const seat of [1, 2]) test(`real foreign-owned unit refuses lossy export in controller seat ${seat}`, async () => {
    const { eg, own, enemy, targets, bot } = await constructProbeFixture(env, pool, scenario, 77100 + seat);
    try {
        const controller = seat === 1 ? own : enemy;
        const source = targets[seat === 1 ? 1 : 0];
        const owner = source.owner;
        assert.doesNotThrow(() => fullState(eg));
        assert.equal(source.takeControl(controller), true);
        eg.game.resolveGameState(true); eg.game.continue();
        assert.notEqual(source.owner, source.controller);
        assert.equal(source.owner, owner); assert.equal(source.controller, controller);
        assert.throws(() => stateEvidence(eg), boundary);
        assert.throws(() => fullState(eg), boundary, 'No owner-less state object escapes');
        source.takeControl(owner); eg.game.resolveGameState(true); eg.game.continue();
        assert.doesNotThrow(() => fullState(eg), 'Ordinary ownership remains exportable');
    } finally { bot.close?.(); }
});
for (const seat of [1, 2]) test(`ordinary mixed-owner attachment stays exportable on host seat ${seat}`, async () => {
    const { eg, own, enemy, targets, bot } = await constructProbeFixture(env, pool, scenario, 77200 + seat);
    try {
        const host = targets[seat === 1 ? 0 : 1], upgrade = targets[seat === 1 ? 3 : 2];
        // Stage the opposing player's physical upgrade on this host while
        // retaining its ownership/controller; this is not a unit control transfer.
        upgrade.attachTo(host); eg.game.resolveGameState(true); eg.game.continue();
        const upgradePlayer = seat === 1 ? enemy : own;
        assert.equal(upgrade.owner, upgradePlayer); assert.equal(upgrade.controller, upgradePlayer);
        assert.notEqual(upgrade.controller, host.controller);
        assert.equal(host.owner, host.controller);
        const state = fullState(eg), row = state.players['p' + seat].ground.find(c => c.id === eg.cardId(host.uuid));
        assert.ok(row);
        const attachment = row.upgrades.find(u => u.id === eg.cardId(upgrade.uuid));
        assert.ok(attachment); assert.equal(attachment.name, upgrade.internalName);
        assert.equal(attachment.token, false);
        assert.equal(attachment.owner, 'p' + (3 - seat));
        assert.equal(attachment.controller, 'p' + (3 - seat));
        assert.equal(own, eg.player(eg.ids[0]));
    } finally { bot.close?.(); }
});
test('actual Credit transfer keeps owner and controller equal and does not reject unit export', async () => {
    const { eg, own, enemy, bot } = await constructProbeFixture(env, pool, scenario, 77300);
    try {
        const credit = eg.game.generateToken(own, 'credit');
        credit.moveTo('base'); eg.game.resolveGameState(true); eg.game.continue();
        const { TakeControlOfCreditTokenSystem } = require('../../../forceteki/build/server/game/gameSystems/TakeControlOfCreditTokenSystem');
        new TakeControlOfCreditTokenSystem({ newController: enemy }).eventHandler({ player: own, newController: enemy, amount: 1 });
        assert.equal(credit.owner, enemy); assert.equal(credit.controller, enemy);
        assert.ok(enemy.baseZone.credits.includes(credit)); assert.ok(!own.baseZone.credits.includes(credit));
        assert.doesNotThrow(() => fullState(eg));
    } finally { bot.close?.(); }
});

for (const seat of [1, 2]) test(`foreign-controlled native token unit also refuses owner loss in seat ${seat}`, async () => {
    const { eg, own, enemy, bot } = await constructProbeFixture(env, pool, scenario, 77400 + seat);
    try {
        const owner = seat === 1 ? enemy : own, controller = seat === 1 ? own : enemy;
        const token = eg.game.generateToken(owner, 'battleDroid');
        token.moveTo('groundArena'); eg.game.resolveGameState(true); eg.game.continue();
        assert.doesNotThrow(() => fullState(eg));
        token.takeControl(controller); eg.game.resolveGameState(true); eg.game.continue();
        assert.equal(token.owner, owner); assert.equal(token.controller, controller);
        assert.throws(() => fullState(eg), boundary);
    } finally { bot.close?.(); }
});
