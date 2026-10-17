'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Env, seededRng } = require('../../../engine/env');
const { fullState } = require('../../../bots/omni/rs/state');
const { stateEvidence } = require('../../../bots/omni/rs/state-evidence');
const { constructProbeFixture, buildDeck } = require('../pipeline/probe-fixture');
const prepared = process.env.SWU_STATE_EVIDENCE_PREPARED;

test('real engine witnesses global physical registration, attachments and re-entry before first export', { skip: !prepared && 'set SWU_STATE_EVIDENCE_PREPARED to a prepared native runtime' }, async () => {
    const pool = JSON.parse(fs.readFileSync(path.join(prepared, 'pool.json')));
    const scenario = { probe: { cardId: 'ASH_061', targets: [{code:'ASH_201',owner:'self',zone:'hand'},{code:'SHD_070',owner:'opponent',zone:'hand'}], sourceInPlay: false } };
    const { eg, own, enemy } = await constructProbeFixture(new Env(), pool, scenario, 917812);
    const take = (player, code, used = []) => eg.game.allCards.filter(c => c.owner === player).find(c => !used.includes(c) &&
        [c.cardData.setId, ...(c.cardData.setCodes ?? [])].some(s => s.set + '_' + String(s.number).padStart(3, '0') === code));
    // Opponent first, then a different arena, then the first controller: neither
    // per-controller concatenation nor per-arena concatenation is chronological.
    const a = take(enemy, 'ASH_061'), b = take(own, 'ASH_201'), c = take(own, 'ASH_061');
    assert.ok(a && b && c);
    a.moveTo('groundArena'); b.moveTo('spaceArena'); c.moveTo('groundArena');
    const upgrade = take(enemy, 'SHD_070');
    assert.ok(upgrade, 'test deck must include ordinary upgrade');
    upgrade.attachTo(c);
    eg.game.resolveGameState(true);
    assert.deepEqual(stateEvidence(eg).registrationOrder.cards, [a,b,c,upgrade].map(x => eg.cardId(x.uuid)));
    const d = take(own,'ASH_061',[c]), upgrade2 = take(enemy,'SHD_070',[upgrade]);
    d.moveTo('groundArena'); upgrade2.attachTo(c); eg.game.resolveGameState(true);
    upgrade.unattach(); upgrade.attachTo(c);
    assert.deepEqual(stateEvidence(eg).registrationOrder.cards, [a,b,c,d,upgrade2,upgrade].map(x => eg.cardId(x.uuid)), 'same-zone reattachment appends the earlier upgrade after interleaved sources');
    a.moveTo('hand'); eg.game.resolveGameState(true); a.moveTo('groundArena');
    eg.game.resolveGameState(true);
    const first = fullState(eg, eg.game.actionPhaseActivePlayer.id);
    assert.deepEqual(first.registrationOrder.cards, [b,c,d,upgrade2,upgrade,a].map(x => eg.cardId(x.uuid)));
    assert.deepEqual(first.phaseHistory, {version:1,entered:[],played:[],playCounts:[0,0]});
    assert.deepEqual(first.supportGrants, []);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'swu-state-evidence-'));
    try {
        const file = path.join(dir, 'positions.jsonl');
        fs.writeFileSync(file, JSON.stringify({fullState:first}) + '\n');
        const result = spawnSync(path.join(prepared, 'kessel'), ['prove',file,'--depth','0','--nodes','1','--pool',path.join(prepared,'pool.json'),'--catalogue',path.join(prepared,'catalog.json')], {encoding:'utf8'});
        assert.equal(result.status,0,result.stderr + result.stdout);
    } finally { fs.rmSync(dir,{recursive:true,force:true}); }

    const token = eg.game.generateToken(own,'battleDroid'); token.moveTo('groundArena');
    const shield = eg.game.generateToken(own,'shield'); shield.attachTo(c); eg.game.resolveGameState(true);
    const withToken = stateEvidence(eg).registrationOrder.cards;
    assert.ok(withToken.includes(eg.cardId(token.uuid)));
    assert.ok(!withToken.includes(eg.cardId(shield.uuid)));
    upgrade.unattach(); upgrade.moveTo('discard'); upgrade2.unattach(); upgrade2.moveTo('discard');
    shield.unattach(); shield.moveTo('outsideTheGame'); c.moveTo('discard'); eg.game.resolveGameState(true);
    assert.ok(!stateEvidence(eg).registrationOrder.cards.includes(eg.cardId(c.uuid)));
    assert.ok(!stateEvidence(eg).registrationOrder.cards.includes(eg.cardId(upgrade.uuid)));

    const rollback = new Env().newGame({seed:917814, deck1:buildDeck(pool,scenario.probe), deck2:buildDeck(pool,scenario.probe),undo:true});
    await rollback.start();
    const rng = seededRng('evidence-rollback'), bot = require('../../../bots/players').makeBot('random');
    for (let i=0; !rollback.ids.some(pid => rollback.isActionWindow(pid)); i++) {
        assert.ok(i<100);
        const pid = rollback.ids.find(pid => rollback.legalActions(pid).length), actions = rollback.legalActions(pid);
        rollback.apply(pid,bot.choose({game:rollback,pid,actions,rng}),rng);
    }
    const pid = rollback.ids.find(pid => rollback.isActionWindow(pid));
    const original = fullState(rollback,pid), mark = rollback.mark(pid);
    const unit = rollback.game.allCards.find(c => c.owner.id === pid && c.internalName === a.internalName);
    unit.moveTo('groundArena'); rollback.game.resolveGameState(true);
    assert.ok(stateEvidence(rollback).registrationOrder.cards.length);
    rollback.restore(pid,mark);
    assert.deepEqual(fullState(rollback,pid),original, 'native snapshot restores chronology before prompt replay');
    unit.moveTo('groundArena'); rollback.game.resolveGameState(true);
    rollback.apply(pid,rollback.legalActions(pid).find(a => a.label === 'Pass'),rng);
    const next = rollback.ids.find(id => rollback.isActionWindow(id));
    const nonempty = fullState(rollback,next), retained = rollback.mark(next);
    unit.moveTo('hand'); rollback.game.resolveGameState(true);
    rollback.restore(next,retained);
    assert.deepEqual(fullState(rollback,next),nonempty, 'nonempty native chronology survives restore');

    const leader = rollback.player(next).getAllDeckLeaders()[0];
    leader.deploy({type:'leaderUnit'}); rollback.game.resolveGameState(true);
    assert.ok(stateEvidence(rollback).registrationOrder.cards.includes(rollback.cardId(leader.uuid)));
    rollback.restore(next,retained);
    assert.deepEqual(fullState(rollback,next),nonempty,'leader deployment rolls back with native chronology');

    const branchToken = rollback.game.generateToken(rollback.player(next),'battleDroid');
    branchToken.moveTo('groundArena'); rollback.game.resolveGameState(true);
    const branchId = rollback.cardId(branchToken.uuid);
    rollback.restore(next,retained);
    assert.ok(!rollback.game.allCards.some(c => c.uuid === branchToken.uuid));
    const recreated = rollback.game.generateToken(rollback.player(next),'battleDroid');
    recreated.moveTo('groundArena'); rollback.game.resolveGameState(true);
    assert.equal(rollback.cardId(recreated.uuid),branchId,'native rollback reuses canonical allocation slot');
    assert.ok(stateEvidence(rollback).registrationOrder.cards.includes(branchId));
    rollback.restore(next,retained);
    assert.deepEqual(fullState(rollback,next),nonempty);

    // These are native watcher event-contract checks, separate from placement:
    // setup moves alone above correctly left both phase histories empty.
    eg.game.emitEvent('onUnitEntersPlay',null,{card:d});
    eg.game.emitEvent('onCardPlayed',null,{card:d,player:own});
    eg.game.emitEvent('onCardPlayed',null,{card:d,player:own});
    const phase = stateEvidence(eg).phaseHistory;
    assert.deepEqual(phase.entered,[{card:eg.cardId(d.uuid),playedBy:'p1'}]);
    assert.deepEqual(phase.played,phase.entered);
    assert.deepEqual(phase.playCounts,[2,0]);
    eg.game.emitEvent('onPhaseEnded');
    assert.deepEqual(stateEvidence(eg).phaseHistory,{version:1,entered:[],played:[],playCounts:[0,0]});
    eg.game.ongoingEffectEngine.effects.push({duration:'untilEndOfAttack',type:'modifyStats'});
    assert.throws(() => fullState(eg), /compiled program binding/);
});

test('snapshot refuses an observer attached after initialization', () => {
    assert.throws(() => stateEvidence({}), /before game initialization/);
});
