'use strict';
/**
 * Portable, engine-free reference vectors for another JEPA backend.
 *
 *   node bots/jepa/wasm/tests/reference-fixtures.js > /tmp/jepa-reference.json
 *   node bots/jepa/wasm/tests/reference-fixtures.js --caches --compact
 *
 * No games, installs, training, or files written. Cards and positions below are synthetic. By default the reference
 * uses the table's vendored JS and two checkpoints; --jepa FILE / --models DIR make it transferable to holocron.
 * Importing this file performs no inference. generateReference() returns JSON data, including every input and the
 * scripted simulation request/reply transcript. Numeric tensors retain JS precision; compare floating outputs with
 * a tolerance (for example 1e-6), while comparing encoded float32 features, protocol replies and choices exactly.
 * Gate cases use the production .04 threshold. Identically encoded copies of a hand card exercise the below-gate
 * tie; different root actions exercise above-gate planning with the pinned checkpoints. A new model can require
 * adjusting the above-gate input if its scores become too close; the assertions make that change visible.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('node:assert/strict');

const SCHEMA = 'swu-jepa-parity/1';
const clone = (v) => JSON.parse(JSON.stringify(v));
const sigmoid = (v) => 1 / (1 + Math.exp(-v));
const other = (you) => you === 'p1' ? 'p2' : 'p1';
const sha256 = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

function card(number, title, fields) {
    return { title, subtitle: null, cost: 0, power: 0, hp: 0, types: [], aspects: [], keywords: [],
        setCodes: [{ set: 'TST', number }], ...fields };
}

function syntheticCards() {
    return [
        card(1, 'Test Leader Alpha', { types: ['leader'], aspects: ['command', 'heroism'] }),
        card(2, 'Test Leader Beta', { types: ['leader'], aspects: ['aggression', 'villainy'] }),
        card(3, 'Test Base Alpha', { types: ['base'], aspects: ['vigilance'], hp: 30 }),
        card(4, 'Test Base Beta', { types: ['base'], aspects: ['cunning'], hp: 30 }),
        card(5, 'Test Runner', { types: ['unit'], cost: 2, power: 3, hp: 2, aspects: ['command'], keywords: ['raid', 'ambush'] }),
        card(6, 'Test Sentinel', { types: ['unit'], cost: 4, power: 2, hp: 6, aspects: ['vigilance'], keywords: ['sentinel', 'restore', 'grit', 'bounty'] }),
        card(7, 'Test Frigate', { types: ['unit'], arena: 'space', cost: 8, power: 7, hp: 9, aspects: ['aggression', 'aggression'], keywords: ['overwhelm', 'saboteur', 'shielded', 'smuggle'] }),
        card(8, 'Test Event', { types: ['event'], cost: 3, aspects: ['cunning'] }),
        card(9, 'Test Upgrade', { types: ['upgrade'], cost: 1, upgradePower: 2, upgradeHp: 1, aspects: ['heroism'] })
    ];
}

const ref = (id, number, name) => ({ id, s: `TST_${String(number).padStart(3, '0')}`, n: name });
function side(seat) {
    const a = seat === 'p1';
    const hand = [ref(`${seat}-h1`, 5, 'Test Runner'), ref(`${seat}-h2`, 7, 'Test Frigate'), ref(`${seat}-h3`, 8, 'Test Event')];
    return {
        name: seat, base: { ...ref(`${seat}-b`, a ? 3 : 4, `Test Base ${a ? 'Alpha' : 'Beta'}`), hp: 30, d: a ? 7 : 12 },
        leader: { ...ref(`${seat}-l`, a ? 1 : 2, `Test Leader ${a ? 'Alpha' : 'Beta'}`), dep: a ? 0 : 1, x: 0 },
        res: { ready: a ? 4 : 2, total: 5 }, handCount: hand.length, hand, deck: 31,
        discard: [ref(`${seat}-d1`, 8, 'Test Event')],
        ground: [{ ...ref(`${seat}-g1`, 6, 'Test Sentinel'), p: 4, h: 7, d: 2, x: a ? 0 : 1, sn: 1,
            u: [{ id: `${seat}-shield`, n: 'Shield', s: null, t: 1 }, { ...ref(`${seat}-up`, 9, 'Test Upgrade'), t: 0 }] }],
        space: [{ ...ref(`${seat}-s1`, 7, 'Test Frigate'), p: 7, h: 9, d: 1, x: 0 }]
    };
}

function position(you = 'p1') {
    const players = { p1: side('p1'), p2: side('p2') };
    delete players[other(you)].hand; // protocol state is always from the bot's seat
    return { round: 4, phase: 'action', initiative: 'p2', players };
}

const button = (i, label) => ({ i, kind: 'button', label, arg: label.toLowerCase() });
const pickCard = (i, c, zone, ctl, label = c.n) => ({ i, kind: 'card', label, card: { ...clone(c), zone, ctl } });
const windowPrompt = () => ({ type: 'actionWindow', actionWindow: true, title: 'Choose an action', selected: [], selectCardMode: null });
function windowDecision(you = 'p1') {
    const state = position(you);
    const me = state.players[you];
    return { t: 'decide', seq: 1, you, ms: 10000, sim: false, prompt: windowPrompt(), state, revealed: [], actions: [
        button(0, 'Pass'), pickCard(1, me.hand[0], 'hand', you),
        pickCard(2, me.ground[0], 'groundArena', you), pickCard(3, me.leader, 'leader', you)
    ] };
}

function followDecision(you = 'p1') {
    const msg = windowDecision(you);
    const them = msg.state.players[other(you)];
    msg.seq = 2;
    msg.prompt = { type: 'selectCard', actionWindow: false, title: 'Choose an attack target', selected: [], selectCardMode: 'single' };
    msg.actions = [pickCard(0, them.base, 'base', other(you)), pickCard(1, them.ground[0], 'groundArena', other(you)), button(2, 'Cancel')];
    return msg;
}

function decisions() {
    const resource = windowDecision('p1');
    resource.state.phase = 'setup';
    resource.prompt = { type: 'resource', title: 'Choose up to 2 cards to resource', actionWindow: false, selected: [], selectCardMode: 'multiple' };
    resource.actions = [...resource.state.players.p1.hand.map((c, i) => pickCard(i, c, 'hand', 'p1')), button(3, 'Done')];
    const stop = clone(resource);
    stop.you = 'p2';
    stop.state = position('p2');
    stop.state.phase = 'regroup';
    stop.state.players.p2.res = { ready: 14, total: 14 };
    stop.actions = [...stop.state.players.p2.hand.map((c, i) => pickCard(i, c, 'hand', 'p2')), button(3, 'Done')];
    const assorted = followDecision('p2');
    assorted.prompt = { type: 'number', actionWindow: false, title: 'Choose a number — Δ', selected: ['p2-g1'], selectCardMode: 'multiple' };
    assorted.actions = [
        { i: 0, kind: 'option', label: '−1.5', arg: -1.5 }, { i: 1, kind: 'option', label: '2.5', arg: '2.5' },
        { i: 2, kind: 'displayCard', label: 'Shown card', arg: 'p1-d1' },
        { i: 3, kind: 'perCardButton', label: 'Yes', arg: 'yes', cardUuid: 'p2-g1' },
        { i: 4, kind: 'distribute', label: 'Distribute damage', distribute: { type: 'damage', amount: 3, targets: [{ id: 'p1-g1', cap: 5 }, { id: 'p1-b', cap: null }] } },
        { i: 5, kind: 'card', label: 'hidden card', card: { id: 'hidden', n: 'hidden card', s: null, zone: 'hand', ctl: 'p1' } }
    ];
    const upgrade = ref('p2-h4', 9, 'Test Upgrade');
    assorted.state.players.p2.hand.push(upgrade);
    assorted.state.players.p2.handCount += 1;
    assorted.actions.push(pickCard(6, upgrade, 'hand', 'p2'));
    const crowded = windowDecision('p1');
    for (const seat of ['p1', 'p2']) {
        const unit = crowded.state.players[seat].ground[0];
        crowded.state.players[seat].ground = Array.from({ length: 14 }, (_, i) => ({ ...clone(unit), id: `${seat}-crowded-${i}`, x: i % 2 }));
    }
    return [
        { name: 'window-p1', msg: windowDecision('p1') }, { name: 'window-p2', msg: windowDecision('p2') },
        { name: 'followup-p1', msg: followDecision('p1') }, { name: 'resource-p1', msg: resource },
        { name: 'resource-stop-p2', msg: stop }, { name: 'action-kinds-p2', msg: assorted },
        { name: 'crowded-token-truncation', msg: crowded }
    ];
}

/** A bounded toy tree, not a game simulator. Root 1 + target 1 wins; root 2 tests the opponent rush response. */
function scriptedSimulator(msg, { remainingMs = null } = {}) {
    const input = clone(msg);
    const follow = followDecision(msg.you);
    follow.state = clone(msg.state);
    const opponent = clone(follow);
    const me = opponent.state.players[msg.you];
    opponent.actions = [pickCard(0, me.base, 'base', msg.you), pickCard(1, me.ground[0], 'groundArena', msg.you)];
    const transcript = [];
    let stage = null;
    const at = (req, actor, scene) => ({ t: 'simulated', op: req.op, ms: remainingMs, actor, prompt: clone(scene.prompt), state: clone(scene.state), actions: clone(scene.actions) });
    const terminal = (req, winner) => ({ t: 'simulated', op: req.op, ms: remainingMs, over: { winner } });
    async function handle(req) {
        assert.equal(req.t, 'sim');
        let reply;
        if (req.op === 'end') {
            stage = null;
            reply = { t: 'simulated', op: 'end', ms: remainingMs };
        } else if (req.op === 'begin') {
            assert.equal(req.deal, 0, 'the current planner compares every line on deal 0');
            stage = 'root';
            reply = at(req, msg.you, input);
        } else {
            assert.equal(req.op, 'act');
            assert.ok(Number.isInteger(req.i));
            if (stage === 'root') {
                assert.ok(req.i >= 0 && req.i < 3);
                if (req.i === 0) {
                    const waiting = clone(input);
                    waiting.state.players[msg.you].res.ready = 0;
                    reply = at(req, other(msg.you), waiting);
                    stage = 'settled';
                } else {
                    stage = req.i === 1 ? 'follow' : 'opponent';
                    reply = at(req, stage === 'follow' ? msg.you : other(msg.you), stage === 'follow' ? follow : opponent);
                }
            } else if (stage === 'follow') {
                assert.ok(req.i === 0 || req.i === 1, 'planner excludes Cancel while follow-ups remain');
                reply = terminal(req, req.i === 1 ? msg.you : other(msg.you));
                stage = 'settled';
            } else if (stage === 'opponent') {
                assert.equal(req.i, 0, 'rush response attacks our base');
                reply = terminal(req, other(msg.you));
                stage = 'settled';
            } else {
                throw new Error(`unexpected simulation action in ${stage}`);
            }
        }
        transcript.push({ request: clone(req), reply: clone(reply) });
        return reply;
    }
    return { handle, transcript, follow };
}

function plain(v) {
    if (ArrayBuffer.isView(v)) return Array.from(v);
    if (Array.isArray(v)) return v.map(plain);
    if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, plain(x)]));
    return v;
}

function loadReference({ modulePath = path.resolve(__dirname, '../../js/jepa.js'), modelDir = path.resolve(__dirname, '../../models') } = {}) {
    const J = require(path.resolve(modulePath));
    const models = {};
    const provenance = { implementationSha256: sha256(fs.readFileSync(modulePath)), checkpoints: {} };
    for (const [name, file] of [['model', 'tx-t10.safetensors'], ['windowModel', 'tx-t10-e.safetensors']]) {
        const bytes = fs.readFileSync(path.join(modelDir, file));
        models[name] = J.loadModel(bytes);
        provenance.checkpoints[name] = { file, sha256: sha256(bytes), metadata: clone(models[name].meta) };
    }
    return { J, models, provenance };
}

function tensorSnapshot(J, models, msg, cards, { includeCaches = false } = {}) {
    const encoded = J.encode(msg, cards.db);
    const networks = {};
    for (const [name, data] of Object.entries(models)) {
        const net = new J.TxModel(data);
        const ctx = net.context(encoded);
        const predictions = {};
        for (const h of net.horizons) {
            const latent = net.predict(ctx, encoded, h);
            const logits = net.value(latent, encoded.actions.n);
            predictions[String(h)] = { latent: plain(latent), logits: plain(logits), scores: Array.from(logits, sigmoid) };
        }
        networks[name] = { context: { z: plain(ctx.z), c: ctx.c, valueLogit: net.value(ctx.z, 1)[0],
            ...(includeCaches ? { layers: plain(ctx.layers) } : {}) }, predictions };
    }
    return { encoded: plain(encoded), networks };
}

async function generateReference(options = {}) {
    const { J, models, provenance } = loadReference(options);
    const cards = syntheticCards();
    const tables = J.cardTables(cards);
    const settings = { score: 'plan', mix: 0, windowHorizon: 's', followHorizon: 's', resource: 'c-clock', plan: { gate: 0.04 } };
    const makeBot = (plan = {}) => new J.JepaBot({ ...models, planModel: models.model, cards: tables, ...settings, plan: { ...settings.plan, ...plan } });
    const hello = (you) => ({ t: 'hello', protocol: 'swu-bot-stdio', v: 1, versions: [2], you, seed: 424242, ms: 30000, cards: clone(cards) });
    const vectors = [];
    for (const fixture of decisions()) {
        const bot = makeBot();
        const greeting = hello(fixture.msg.you);
        const ready = bot.hello(greeting);
        const imagined = bot.think(fixture.msg).score;
        const reply = await bot.decide(fixture.msg, async () => { throw new Error('sim=false fixture requested a simulation'); });
        assert.equal(ready.v, 2);
        assert.equal(ready.sim, true);
        vectors.push({ ...fixture, hello: greeting, ready, ...tensorSnapshot(J, models, fixture.msg, tables, options), imagined, reply, stats: clone(bot.stats), over: bot.over({ t: 'over' }) });
    }
    const behaviors = [];
    for (const you of ['p1', 'p2']) {
        for (const [name, remainingMs, floor] of [['below-gate', null, 0], ['above-gate', null, 0], ['low-time-fallback', 1000, 2500]]) {
            const msg = windowDecision(you);
            msg.actions = msg.actions.slice(0, 3);
            msg.sim = true;
            if (name === 'below-gate') {
                const me = msg.state.players[you];
                const copy = { ...clone(me.hand[0]), id: `${you}-runner-copy` };
                me.hand.push(copy);
                me.handCount += 1;
                msg.actions = [pickCard(0, me.hand[0], 'hand', you), pickCard(1, copy, 'hand', you)];
            }
            const plan = { gate: 0.04, roots: 3, follow: 2, follow2: 2, depth: 2, lines: 12, secs: 1e9, floor };
            const bot = makeBot(plan);
            const greeting = hello(you);
            const ready = bot.hello(greeting);
            const imagined = bot.think(msg).score;
            const sim = scriptedSimulator(msg, { remainingMs });
            const reply = await bot.decide(msg, sim.handle);
            let followup = null;
            if (name === 'above-gate') {
                assert.equal(reply.i, 1);
                assert.ok(bot.stats.planned === 1 && bot.plan.length > 0);
                const next = clone(sim.follow);
                next.sim = false;
                const response = await bot.decide(next, sim.handle);
                assert.equal(response.i, 1);
                assert.equal(bot.stats.followed, 1);
                followup = { msg: next, reply: response };
            } else if (name === 'below-gate') {
                assert.equal(sim.transcript.length, 0);
                assert.equal(bot.stats.gated, 1);
            } else {
                assert.deepEqual(sim.transcript.map((x) => x.request.op), ['begin', 'end']);
                assert.equal(bot.fail, 'time');
            }
            behaviors.push({ name: `${name}-${you}`, settings: { ...settings, plan }, hello: greeting, ready, msg, imagined,
                spread: Math.max(...imagined) - Math.min(...imagined), transcript: sim.transcript, reply, followup, stats: clone(bot.stats), fail: bot.fail });
        }
    }
    return { schema: SCHEMA, provenance, cards, settings, vectors, behaviors };
}

module.exports = { SCHEMA, syntheticCards, decisions, scriptedSimulator, tensorSnapshot, loadReference, generateReference };

if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {};
    let compact = false;
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--compact') compact = true;
        else if (args[i] === '--caches') options.includeCaches = true;
        else if ((args[i] === '--jepa' || args[i] === '--models') && args[i + 1]) options[args[i++] === '--jepa' ? 'modulePath' : 'modelDir'] = path.resolve(args[i]);
        else throw new Error(`unknown or incomplete argument: ${args[i]}`);
    }
    generateReference(options).then((data) => process.stdout.write(`${JSON.stringify(data, null, compact ? 0 : 2)}\n`)).catch((e) => {
        console.error(e.stack || e);
        process.exitCode = 1;
    });
}
