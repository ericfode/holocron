'use strict';
// The protocol ports of heuristic and rush (bots/ports/): their choices on hand-made protocol messages, the heuristic's
// lookahead against a fake simulator, and one real game between them (needs forceteki/build and its card data).
const test = require('node:test');
const assert = require('node:assert');
const C = require('../ports/common');
const heuristicPort = require('../ports/heuristic');
const rushPort = require('../ports/rush');

const unit = (id, p, h, extra = {}) => ({ id, n: id, s: null, p, h, d: 0, ...extra });
function player({ base = 'b', baseHp = 30, baseDamage = 0, ground = [], space = [], hand = 3, res = 3, leader = null } = {}) {
    return { base: { id: base, n: 'Base', s: null, hp: baseHp, d: baseDamage }, leader, res: { ready: res, total: res }, handCount: hand, deck: 40,
        discard: [], ground, space, hand: [] };
}
const state = (p1, p2, extra = {}) => ({ round: 1, phase: 'action', initiative: null, players: { p1, p2 }, ...extra });
const windowPrompt = { type: 'actionWindow', signature: 'actionWindow|-', title: 'Choose an action', promptTitle: null, selected: [], actionWindow: true };
const hello = (you, seed = 1) => ({ t: 'hello', you, seed, ms: 30000, deck: { leader: { id: 'SOR_010' }, base: { id: 'SOR_023' } }, opponent: { leader: { id: 'SOR_010' }, base: { id: 'SOR_023' } } });

test('cards.json gives printed cost, unit and aspects by set code', () => {
    assert.deepStrictEqual([C.costOf('SOR_095'), C.isUnitCard('SOR_095')], [2, true]); // Battlefield Marine
    assert.deepStrictEqual([C.costOf('SOR_042'), C.isUnitCard('SOR_042')], [4, false]); // Search Your Feelings, an event
    assert.deepStrictEqual(C.aspectsOf('SOR_010'), ['aggression', 'villainy']); // Darth Vader, Dark Lord of the Sith
    assert.strictEqual(C.costOf(null), 0); // tokens have no set code
});

test('evaluate: the in-process weights, from either seat, and finished games', () => {
    const s = state(player({ ground: [unit('c1', 3, 4)] }), player({ baseDamage: 6 }), { initiative: 'p1' });
    const v = C.evaluate(s, 'p1');
    assert.ok(v > 0);
    assert.strictEqual(C.evaluate(s, 'p2'), -v);
    // a unit's value: power 1.3, health left 0.9, a Shield token 2.2, Sentinel 1, exhausted x0.85
    assert.strictEqual(C.unitValue(unit('c1', 2, 3)), 2 * 1.3 + 3 * 0.9);
    assert.strictEqual(C.unitValue(unit('c1', 2, 3, { u: [{ id: 'c9', n: 'Shield', s: null, t: 1 }], sn: 1, x: 1 })), (2 * 1.3 + 3 * 0.9 + 2.2 + 1) * 0.85);
    assert.strictEqual(C.evaluate(s, 'p1', { winner: 'p1' }), 10000);
    assert.strictEqual(C.evaluate(s, 'p1', { winner: 'p2' }), -10000);
    assert.strictEqual(C.evaluate(s, 'p1', { winner: 'draw' }), 0);
    // base danger: below 12 HP each point lost costs more
    const low = C.evaluate(state(player(), player({ baseDamage: 25 })), 'p1') - C.evaluate(state(player(), player({ baseDamage: 24 })), 'p1');
    const high = C.evaluate(state(player(), player({ baseDamage: 2 })), 'p1') - C.evaluate(state(player(), player({ baseDamage: 1 })), 'p1');
    assert.ok(low > high && high > 0);
});

test('defaultChoose: keep, take the initiative, attack the weakest enemy, stop at Done', () => {
    const s = state(player({ ground: [unit('c1', 3, 4)] }), player({ base: 'b2', ground: [unit('c2', 1, 1), unit('c3', 5, 5)] }));
    const pick = (prompt, actions, seat = 'p1') => C.defaultChoose({ prompt: { selected: [], ...prompt }, state: s, actions, seat, aspects: [] });
    const b = (i, label) => ({ i, kind: 'button', label });
    const card = (i, id, zone, ctl) => ({ i, kind: 'card', label: id, cardUuid: id, card: { id, n: id, s: null, zone, ctl } });
    assert.strictEqual(pick({ title: 'Mulligan?' }, [b(0, 'Mulligan'), b(1, 'Keep')]).i, 1);
    assert.strictEqual(pick({ title: 'Who takes the initiative?' }, [b(0, 'Opponent'), b(1, 'Yourself')]).i, 1);
    // an attack target: the enemy base scores 8, an enemy unit its value minus half its health plus 10, mine -100
    const target = pick({ title: 'Choose a target for attack' }, [card(0, 'c1', 'groundArena', 'p1'), card(1, 'c2', 'groundArena', 'p2'), card(2, 'c3', 'groundArena', 'p2'), card(3, 'b2', 'base', 'p2')]);
    assert.strictEqual(target.i, 2);
    assert.strictEqual(pick({ title: 'Select 1 card' }, [card(0, 'c2', 'groundArena', 'p2'), b(1, 'Done')], 'p1').i, 0);
    assert.strictEqual(pick({ title: 'Select 1 card', selected: ['c2'] }, [card(0, 'c3', 'groundArena', 'p2'), b(1, 'Done')]).i, 1);
    assert.strictEqual(pick({ title: 'Pick a number' }, [{ i: 0, kind: 'option', label: '#1' }, { i: 1, kind: 'option', label: '#3' }]).i, 1);
    assert.strictEqual(pick({ title: 'Trigger?' }, [b(0, 'Pass'), b(1, 'Trigger')]).i, 1);
});

test('rush port: the most expensive card from hand, then attacks, then the leader; face first; loops pass', () => {
    const bot = rushPort.create();
    bot.hello(hello('p1'));
    const s = state(player({ ground: [unit('c1', 4, 4)], leader: { id: 'c50', n: 'Leader', s: 'SOR_010', dep: 0, x: 0 } }), player({ base: 'b2', ground: [unit('c2', 1, 1)] }));
    const card = (i, id, zone, ctl, s0 = null) => ({ i, kind: 'card', label: id, cardUuid: id, card: { id, n: id, s: s0, zone, ctl } });
    const actions = [{ i: 0, kind: 'button', label: 'Pass' }, card(1, 'c50', 'base', 'p1', 'SOR_010'), card(2, 'c1', 'groundArena', 'p1'), card(3, 'c7', 'hand', 'p1', 'SOR_095'), card(4, 'c8', 'hand', 'p1', 'SOR_042')];
    const act = (msg) => bot.decide({ t: 'decide', you: 'p1', prompt: windowPrompt, state: s, actions, ...msg }).i;
    assert.strictEqual(act({}), 4); // Search Your Feelings costs 4, Battlefield Marine 2
    assert.strictEqual(act({ actions: actions.slice(0, 4) }), 3);
    assert.strictEqual(act({ actions: actions.slice(0, 3), state: { ...s, round: 2 } }), 2);
    assert.strictEqual(act({ actions: actions.slice(0, 2), state: { ...s, round: 3 } }), 1);
    // the same window a third time: something got cancelled, so pass
    assert.strictEqual(act({ actions: actions.slice(0, 2), state: { ...s, round: 3 } }), 1);
    assert.strictEqual(act({ actions: actions.slice(0, 2), state: { ...s, round: 3 } }), 0);
    const attack = { type: null, title: 'Choose a target for attack', promptTitle: null, selected: [], actionWindow: false };
    assert.strictEqual(bot.decide({ t: 'decide', you: 'p1', prompt: attack, state: s, actions: [card(0, 'c2', 'groundArena', 'p2'), card(1, 'b2', 'base', 'p2')] }).i, 1);
    assert.strictEqual(bot.decide({ t: 'decide', you: 'p1', prompt: attack, state: s, actions: [card(0, 'c1', 'groundArena', 'p1'), card(1, 'c2', 'groundArena', 'p2')] }).i, 1);
});

/**
 * A fake simulator over a tiny game: from the real position, action `i` of `results` leads to a follow-up prompt of
 * mine (when `follow` lists options) or straight to the opponent's action window, with the enemy base damaged by
 * `dmg[i]` (or by the option's damage). Records every request.
 */
function fakeSim(base, { dmg, follow = {} }) {
    const log = [];
    let at = null;
    const position = (s, actor, prompt, actions) => ({ t: 'simulated', ms: 9000, actor, prompt, state: s, actions });
    const hit = (s, d) => ({ ...s, players: { ...s.players, p2: { ...s.players.p2, base: { ...s.players.p2.base, d: s.players.p2.base.d + d } } } });
    const oppWindow = (s) => position(s, 'p2', { ...windowPrompt }, [{ i: 0, kind: 'button', label: 'Pass' }]);
    const sim = async (req) => {
        log.push(req);
        if (req.op === 'begin') {
            at = { first: null };
            return position(base, 'p1', windowPrompt, []);
        }
        if (req.op === 'end') {
            return { t: 'simulated', op: 'end', ms: 9000 };
        }
        if (at.first === null) {
            at.first = req.i;
            const opts = follow[req.i];
            if (opts) {
                return position(base, 'p1', { type: null, title: 'Choose a target', promptTitle: null, selected: [], actionWindow: false },
                    opts.map((d, k) => ({ i: k, kind: 'card', label: `t${k}`, cardUuid: `t${k}`, card: { id: `t${k}`, n: 't', s: null, zone: 'groundArena', ctl: 'p2' } })));
            }
            return oppWindow(hit(base, dmg[req.i]));
        }
        return oppWindow(hit(base, follow[at.first][req.i]));
    };
    return { sim, log };
}

test('heuristic port: tries each action and each first follow-up on a simulation, plays the best, then its plan', async () => {
    const bot = heuristicPort.create('h', { now: () => 0 });
    assert.deepStrictEqual(bot.hello(hello('p1')), { t: 'ready', v: 2, name: 'h', sim: true });
    const s = state(player(), player({ base: 'b2' }));
    const actions = [{ i: 0, kind: 'button', label: 'Pass' }, { i: 1, kind: 'card', label: 'a', cardUuid: 'c1', card: { id: 'c1', zone: 'hand', ctl: 'p1' } },
        { i: 2, kind: 'card', label: 'b', cardUuid: 'c2', card: { id: 'c2', zone: 'groundArena', ctl: 'p1' } }];
    // action 1 deals 2; action 2 asks for a target, and its second option deals 5
    const { sim, log } = fakeSim(s, { dmg: [0, 2, 0], follow: { 2: [1, 5, 0] } });
    const r = await bot.decide({ t: 'decide', you: 'p1', sim: true, ms: 10000, prompt: windowPrompt, state: s, actions }, sim);
    assert.strictEqual(r.i, 2);
    assert.ok(log.filter((q) => q.op === 'begin').every((q) => q.deal === 0), 'every playout on the same deal');
    assert.strictEqual(log.filter((q) => q.op === 'begin').length, 3 + 3);
    // the target prompt that follows in the real game: the planned option, found by its card, not its index
    const follow = { type: null, title: 'Choose a target', promptTitle: null, selected: [], actionWindow: false };
    const targets = [{ i: 0, kind: 'card', label: 't2', cardUuid: 't2', card: { id: 't2' } }, { i: 1, kind: 'card', label: 't1', cardUuid: 't1', card: { id: 't1' } }];
    assert.strictEqual((await bot.decide({ t: 'decide', you: 'p1', sim: false, ms: 10000, prompt: follow, state: s, actions: targets })).i, 1);
});

test('heuristic port: without simulations it plays rush rules, and it guards its time', async () => {
    const s = state(player(), player({ base: 'b2' }));
    const actions = [{ i: 0, kind: 'button', label: 'Pass' }, { i: 1, kind: 'card', label: 'a', cardUuid: 'c1', card: { id: 'c1', s: 'SOR_095', zone: 'hand', ctl: 'p1' } }];
    const noSim = heuristicPort.create('h');
    noSim.hello(hello('p1'));
    assert.strictEqual((await noSim.decide({ t: 'decide', you: 'p1', sim: false, ms: 10000, prompt: windowPrompt, state: s, actions }, null)).i, 1);
    // a clock that jumps 5 s per call: the first playout uses up the window, so the rest are cut
    let t = 0;
    const slow = heuristicPort.create('h', { now: () => (t += 5000) });
    slow.hello(hello('p1'));
    const { sim, log } = fakeSim(s, { dmg: [0, 2] });
    await slow.decide({ t: 'decide', you: 'p1', sim: true, ms: 10000, prompt: windowPrompt, state: s, actions }, sim);
    assert.ok(log.filter((q) => q.op === 'begin').length <= 1);
    assert.ok(slow.stats.cut >= 1);
});

test('heuristic and rush ports play a real game to the end through the protocol', { timeout: 300000 }, async (t) => {
    let env;
    try {
        const { Env } = require('../../engine/env');
        env = new Env();
    } catch (e) {
        t.skip(`no engine or card data: ${e.message.split('\n')[0]}`);
        return;
    }
    const { playGame } = require('../../engine/match');
    const h = heuristicPort.create('heuristic-port');
    const r = rushPort.create('rush-port');
    const res = await playGame(env, { seed: 3, bots: [h, r], maxSteps: 6000, limits: { decide: null } });
    assert.strictEqual(res.outcome, 'won', JSON.stringify({ outcome: res.outcome, error: res.error, by: res.by }));
    assert.ok(h.stats.windows > 0 && h.stats.playouts > h.stats.windows, JSON.stringify(h.stats));
    assert.ok(r.stats.windows > 0);
});
