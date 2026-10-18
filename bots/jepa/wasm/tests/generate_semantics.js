'use strict';
// Synthetic helper-only fixtures: no models, games, network, or training are run.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const source = process.env.JEPA_REFERENCE_JS || path.resolve(__dirname, '../../js/jepa.js');
const reference = process.env.JEPA_REFERENCE_JSON || path.join(__dirname, 'fixtures/runtime-reference.json');
const J = require(source);
const helperSource = process.env.JEPA_REFERENCE_HELPERS || path.join(__dirname, 'reference-fixtures.js');
const { scriptedSimulator } = require(helperSource);
const ref = JSON.parse(fs.readFileSync(reference));
const copy = (x) => JSON.parse(JSON.stringify(x));
const bits = (xs) => Array.from(new Uint32Array(xs.buffer, xs.byteOffset, xs.length));
const snapshot = (e) => ({ state: bits(e.state), actions: { rows: bits(e.actions.rows), ids: Array.from(e.actions.ids), n: e.actions.n }, tokens: { feats: bits(e.tokens.feats), ids: Array.from(e.tokens.ids), n: e.tokens.n } });
const tables = J.cardTables(ref.cards);
const cases = ref.vectors.map((v) => ({ name: v.name, msg_json: JSON.stringify(v.msg), expected: snapshot(J.encode(v.msg, tables.db)) }));
const base = copy(ref.vectors.find((v) => v.name === 'window-p1').msg);
function add(name, msg, cards = ref.cards, msgJson = JSON.stringify(msg)) {
    cases.push({ name, msg_json: msgJson, ...(cards === ref.cards ? {} : { cards }), expected: snapshot(J.encode(JSON.parse(msgJson), J.cardTables(cards).db)) });
}
{
    const msg = copy(base);
    msg.prompt = { type: 'number', title: 'A MULLIGAN overrides number', selected: ['one'], selectCardMode: 'multiple' };
    const args = [-0, 1e-7, 1e-6, 1e20, 1e21, '1_000', '1_2_3', 'nan', 'inf', '-Infinity', '+.5', '1e+4', true, null];
    msg.actions = args.map((arg, i) => ({ i, kind: 'option', label: `number ${i}`, arg }));
    msg.actions[0].arg = '__NEGATIVE_ZERO__';
    add('number-formatting-and-nonfinite', msg, ref.cards, JSON.stringify(msg).replace('"__NEGATIVE_ZERO__"', '-0'));
}
{
    const msg = copy(base);
    msg.state.players.p1.base.hp = true;
    msg.state.players.p1.base.d = '7';
    msg.state.players.p1.res.ready = false;
    msg.state.players.p1.handCount = '3';
    msg.state.players.p1.ground[0].p = '4';
    msg.state.players.p1.ground[0].h = 1;
    msg.state.players.p1.ground[0].d = 5;
    add('numeric-booleans-strings-and-hp-clamping', msg);
}
{
    const msg = copy(base);
    const duplicate = copy(msg.state.players.p2.ground[0]);
    duplicate.id = msg.state.players.p1.ground[0].id;
    duplicate.p = 13;
    msg.state.players.p2.ground.push(duplicate);
    msg.actions = [{ i: 17, kind: 'perCardButton', label: 'YES please', arg: true, cardUuid: duplicate.id }, { i: 18, kind: 'mystery', label: 'Ω — 😀', arg: {} }];
    add('duplicate-board-id-last-wins-and-unknown-action', msg);
}
{
    const cards = copy(ref.cards);
    cards.push({ title: 'Subtype', types: ['Special UNIT'], keywords: ['AMBUSH'], cost: 3, power: 5, hp: 6, setCodes: [{ set: 'TST', number: 10 }], setId: { set: 'ALT', number: 10 } });
    cards.push({ title: 'Upgrade zero fallback', types: ['upgrade'], cost: 1, power: 0, hp: 99, upgradePower: 2, upgradeHp: 3, setCodes: [{ set: 'TST', number: 11 }] });
    cards.push({ title: 'Upgrade nonzero keeps HP', types: ['upgrade'], cost: 1, power: 4, hp: 9, upgradePower: 2, upgradeHp: 3, setCodes: [{ set: 'TST', number: 12 }] });
    const msg = copy(base);
    msg.state.players.p1.hand = ['TST_010', 'ALT_010', 'TST_011', 'TST_012', 'MISSING_001'].map((s, i) => ({ id: `extra-${i}`, s, n: 'Extra' }));
    msg.actions = msg.state.players.p1.hand.map((card, i) => ({ i, kind: 'card', label: card.n, card: { ...card, ctl: 'p1', zone: 'unknown-zone' } }));
    add('card-alias-substring-types-and-upgrade-fallback', msg, cards);
}
add('missing-fields', { actions: [{ i: 0, kind: 'button', label: 'Done' }, { i: 1, kind: 'option', arg: '2.5' }] });

const resource = copy(ref.vectors.find((v) => v.name === 'resource-p1').msg);
const resourceCases = [];
function resourceCase(name, edit, cards = ref.cards) {
    const msg = copy(resource);
    edit(msg);
    resourceCases.push({ name, msg, ...(cards === ref.cards ? {} : { cards }), expected: new J.ResourcePolicy('c-clock', J.cardTables(cards).meta).choose(msg) });
}
for (const [total, handCount] of [[5, 1], [6, 1], [6, 2], [8, 3], [9, 3], [14, 3]]) {
    resourceCase(`regroup-resources-${total}-hand-${handCount}`, (m) => { m.state.phase = 'regroup'; m.state.players.p1.res.total = total; m.state.players.p1.handCount = handCount; });
}
resourceCase('setup-still-resources-at-20', (m) => { m.state.players.p1.res.total = 20; });
resourceCase('selected-limit-uses-last-title-number', (m) => { m.prompt.title = 'Round 12: select up to 2'; m.prompt.selected = ['a', 'b']; });
resourceCase('last-button-is-done-and-no-card-options', (m) => { m.actions = [{ i: 5, kind: 'button', label: 'Skip' }, { i: 12, kind: 'button', label: 'Done' }]; });
resourceCase('first-tie-and-action-identifiers', (m) => { m.actions = [{ i: 17, kind: 'card', card: { s: 'UNKNOWN_001', zone: 'hand', ctl: 'p1' } }, { i: 19, kind: 'card', card: { s: 'UNKNOWN_002', zone: 'hand', ctl: 'p1' } }, { i: 20, kind: 'button', label: 'Done' }]; });
resourceCase('other-prompt-defers', (m) => { m.prompt.type = 'actionWindow'; });
resourceCase('no-cards-no-button-defers', (m) => { m.actions = []; });
const duplicateAspects = copy(ref.cards);
duplicateAspects[0].aspects = ['aggression'];
duplicateAspects[2].aspects = ['aggression'];
resourceCase('two-aspect-copies-pay-two-requirements', (m) => { m.state.phase = 'regroup'; m.state.players.p1.res.total = 9; m.state.players.p1.handCount = 2; }, duplicateAspects);
const singleAspect = copy(duplicateAspects);
singleAspect[2].aspects = [];
resourceCase('one-aspect-copy-does-not-pay-two-requirements', (m) => { m.state.phase = 'regroup'; m.state.players.p1.res.total = 9; m.state.players.p1.handCount = 2; }, singleAspect);

const hashes = ['', 'card:TST_007', 'option:-0', 'option:1e+21', 'Ω — 😀', 'é', 'e\u0301', 'a\0b'].map((input) => ({ input, expected: J.hashId(input) }));
const rng = [0, 1, 424242, 4294967296, 9007199254740991].map((seed) => {
    const r = new J.PyRandom(seed);
    const bounds = [1, 2, 3, 4, 7, 8, 16, 257, 65537, 2147483649];
    const draws = Array.from({ length: seed === 424242 ? 710 : 30 }, (_, i) => { const n = bounds[i % bounds.length]; return { n, expected: r.below(n) }; });
    return { seed, draws };
});
const fixture = { schema: 'swu-jepa-controller-semantics/1', provenance: { sourceSha256: crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'), referenceSchema: ref.schema }, cards: ref.cards, features: cases, resource: resourceCases, hashes, rng };
fs.writeFileSync(path.join(__dirname, 'fixtures/semantics.json'), `${JSON.stringify(fixture)}\n`);
console.log(`${cases.length} feature cases, ${resourceCases.length} resource cases, ${hashes.length} hashes, ${rng.reduce((n, x) => n + x.draws.length, 0)} RNG draws`);

// Exercise the reference controller with a deterministic model double. The trained checkpoints are never loaded.
function modelLogits(e, flat) {
    if (flat) return new Array(e.actions.n).fill(1);
    const follow = e.actions.rows[1] === 1;
    return Array.from({ length: e.actions.n }, (_, i) => follow ? [2, 1, 10][i] ?? i : i);
}
function mockBot(settings, flat) {
    const bot = Object.create(J.JepaBot.prototype);
    Object.assign(bot, { name: 'jepa-tx-gate', db: tables.db, mix: 0, score: 'plan', followHorizon: 's', windowHorizon: 's', resource: new J.ResourcePolicy('c-clock', tables.meta), cfg: { roots: 3, follow: 2, follow2: 2, depth: 2, lines: 12, secs: 1e9, floor: 0, gate: 0.04, ...settings.plan } });
    bot.think = (msg) => ({ score: modelLogits(J.encode(msg, tables.db), flat).map((v) => 1 / (1 + Math.exp(-v))) });
    bot.planNet = { context: () => ({ z: [2] }), value: () => [2] };
    bot.newGame(424242);
    return bot;
}
async function plans() {
    const planCases = [];
    for (const you of ['p1', 'p2']) {
        for (const mode of ['gated', 'planned-follow', 'renamed-card-follow', 'dropped-follow', 'low-time', 'pass-outside-roots', 'begin-mismatch', 'simulation-act-error', 'no-op-vs-draw', 'repeated-observation']) {
            const msg = copy(ref.vectors.find((v) => v.name === `window-${you}`).msg);
            msg.actions = msg.actions.slice(0, mode === 'no-op-vs-draw' ? 2 : 3);
            msg.sim = mode !== 'repeated-observation';
            const config = { plan: { roots: mode === 'pass-outside-roots' ? 1 : 3, follow: 2, follow2: 2, depth: 2, lines: 12, secs: 1e9, floor: mode === 'low-time' ? 2500 : 0, gate: 0.04 } };
            const hello = copy(ref.vectors.find((v) => v.name === `window-${you}`).hello);
            const bot = mockBot(config, mode === 'gated');
            const ready = bot.hello(hello);
            const sim = scriptedSimulator(msg, { remainingMs: mode === 'low-time' ? 1000 : null });
            const transcript = [];
            const request = async (req) => {
                let reply;
                if (mode === 'no-op-vs-draw') {
                    reply = req.op === 'begin' || (req.op === 'act' && req.i === 0)
                        ? { t: 'simulated', op: req.op, actor: you, prompt: copy(msg.prompt), state: copy(msg.state), actions: copy(msg.actions) }
                        : req.op === 'act' ? { t: 'simulated', op: 'act', over: { winner: 'draw' } } : { t: 'simulated', op: 'end' };
                } else reply = await sim.handle(req);
                if (mode === 'begin-mismatch' && req.op === 'begin') reply = { ...reply, actions: [] };
                if (mode === 'simulation-act-error' && req.op === 'act') reply = { t: 'simulated', op: 'act', error: 'synthetic fault' };
                transcript.push({ request: copy(req), reply: copy(reply) });
                return reply;
            };
            const inputs = [msg];
            const replies = [await bot.decide(msg, request)];
            if (mode.endsWith('follow')) {
                const next = copy(sim.follow);
                next.sim = false;
                if (mode === 'renamed-card-follow') for (const a of next.actions) if (a.card) a.card.id = `new-${a.card.id}`;
                if (mode === 'dropped-follow') next.actions[0].label = 'Changed target';
                inputs.push(next);
                replies.push(await bot.decide(next, request));
            }
            if (mode === 'repeated-observation') for (let i = 0; i < 6; i++) { inputs.push(copy(msg)); replies.push(await bot.decide(msg, request)); }
            planCases.push({ name: `${mode}-${you}`, config, hello, ready, flat: mode === 'gated', inputs, replies, transcript, stats: copy(bot.stats), fail: bot.fail });
        }
    }
    fs.writeFileSync(path.join(__dirname, 'fixtures/planning.json'), `${JSON.stringify({ schema: 'swu-jepa-controller-planning/1', cards: ref.cards, cases: planCases })}\n`);
    console.log(`${planCases.length} deterministic-model controller cases`);
}
plans().catch((error) => { console.error(error); process.exitCode = 1; });
