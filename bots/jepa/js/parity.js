#!/usr/bin/env node
'use strict';
/**
 * Checks the JavaScript JEPA bot (jepa.js) against jepa_bot.py, on jepa-tx-gate's settings.
 *
 *   node bots/jepa/js/parity.js features [--games 2] [--seed 1]   every decision of real-deck games: features, imagined
 *                                                                 scores and resource choices of both, compared
 *   node bots/jepa/js/parity.js games [--games 2] [--seed 1]      the planner too: both bots answer every decision of
 *                                                                 real games (the Python bot's move is played) and the
 *                                                                 picks are compared; the planner gets no time limit,
 *                                                                 so both explore the same lines (--py FILE: another
 *                                                                 Python bot to compare, default bots/jepa/jepa_bot.py)
 *
 * Needs the built engine, Python 3 with numpy, and card data (SWU_CARD_DATA, default forceteki/test/json). Prints a
 * JSON summary; exits 1 when the two disagree beyond float rounding.
 */

const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const { Env } = require('../../../engine/env');
const { playGame } = require('../../../engine/match');
const { loadDecks } = require('../../../engine/decklists');
const { StdioClient } = require('../../../engine/stdio');
const { makeBot: make, readCards } = require('./main');
const { cardTables } = require('./jepa');

let cards = null;
const makeBot = (a) => make(a, (cards ??= cardTables(readCards())));

const ROOT = path.join(__dirname, '..', '..', '..');
const MODELS = path.join(ROOT, 'bots', 'jepa', 'models');
// jepa-tx-gate (bots/external-bots.json)
const GATE = { model: path.join(MODELS, 'tx-t10.safetensors'), windowModel: path.join(MODELS, 'tx-t10-e.safetensors'), windowHorizon: 's',
    followHorizon: 's', mix: 0, resource: 'c-clock', score: 'plan', planModel: path.join(MODELS, 'tx-t10.safetensors'), plan: { gate: 0.04 }, name: 'jepa-tx-gate' };
const pyArgs = (a, extra = []) => ['--model', a.model, '--window-model', a.windowModel, '--window-horizon', a.windowHorizon, '--follow-horizon', a.followHorizon,
    '--mix', String(a.mix), '--resource', a.resource, ...extra];

function options(argv) {
    const o = { mode: argv[0], games: 2, seed: 1, decks: path.join(ROOT, 'decks', 'ash-meta-2026-09.json') };
    for (let k = 1; k < argv.length; k += 2) {
        o[argv[k].replace(/^--/, '')] = argv[k + 1];
    }
    o.games = Number(o.games);
    o.seed = Number(o.seed);
    return o;
}

/** Python helper (parity.py) answering one message at a time. */
function pyHelper(a) {
    const child = spawn('python3', [path.join(__dirname, 'parity.py'), ...pyArgs(a)], { cwd: ROOT, stdio: ['pipe', 'pipe', 'inherit'] });
    const lines = readline.createInterface({ input: child.stdout })[Symbol.asyncIterator]();
    return {
        async ask(msg) {
            child.stdin.write(`${JSON.stringify(msg)}\n`);
            const { value, done } = await lines.next();
            if (done) {
                throw new Error('parity.py exited');
            }
            return JSON.parse(value);
        },
        close: () => child.stdin.end()
    };
}

const maxDiff = (a, b) => {
    if (a.length !== b.length) {
        return Infinity;
    }
    let m = 0;
    for (let k = 0; k < a.length; k++) {
        m = Math.max(m, Math.abs(a[k] - b[k]));
    }
    return m;
};

async function features(o, env, decks) {
    const { encode } = require('./jepa');
    const py = pyHelper(GATE);
    const sum = { decisions: 0, state: 0, rows: 0, tokens: 0, score: 0, ids: 0, resource: 0, best: 0, worst: null };
    for (let g = 0; g < o.games; g++) {
        const seed = o.seed + g;
        const msgs = [];
        // two JS bots in imagined mode play the game quickly; every message they see is checked afterwards
        const seat = (name) => {
            const bot = makeBot({ ...GATE, score: 'imagined', name });
            return { name, hello: (m) => bot.hello(m), over: (m) => bot.over(m), decide: (m, sim) => (msgs.push(m), bot.decide(m, sim)) };
        };
        const pair = [decks[(2 * g) % decks.length], decks[(2 * g + 1) % decks.length]];
        const res = await playGame(env, { seed, bots: [seat('a'), seat('b')], decks: { p1: pair[0], p2: pair[1] } });
        const bot = makeBot(GATE);
        for (const m of msgs) {
            if ((m.actions || []).length <= 1) {
                continue;
            }
            const p = await py.ask(m);
            const e = encode(m, bot.db);
            const js = bot.think(m).score;
            const res2 = bot.resource.choose(m);
            sum.decisions++;
            sum.state = Math.max(sum.state, maxDiff(e.state, p.state));
            sum.rows = Math.max(sum.rows, maxDiff(e.actions.rows, p.rows));
            sum.tokens = Math.max(sum.tokens, maxDiff(e.tokens.feats, p.tok_feats));
            sum.ids += maxDiff(e.actions.ids, p.aids) > 0 || maxDiff(e.tokens.ids, p.tok_ids) > 0 ? 1 : 0;
            const d = maxDiff(js, p.score);
            if (d > sum.score) {
                sum.score = d;
                sum.worst = { seed, seq: m.seq, prompt: m.prompt?.type, n: js.length };
            }
            sum.resource += (res2 ?? null) !== (p.resource ?? null) ? 1 : 0;
            // the best move: the same, or one the Python bot scores within rounding of its own best
            const bj = js.indexOf(Math.max(...js));
            sum.best += Math.max(...p.score) - p.score[bj] > 1e-5 ? 1 : 0;
        }
        console.error(`game ${seed}: ${res.outcome} ${res.winner} after ${res.steps} steps, ${msgs.length} decisions`);
    }
    py.close();
    return { ...sum, ok: sum.state < 1e-6 && sum.rows < 1e-6 && sum.tokens < 1e-6 && sum.ids === 0 && sum.score < 1e-4 && sum.resource === 0 && sum.best === 0 };
}

async function games(o, env, decks) {
    const plan = { gate: 0.04, secs: 1e6, floor: 0 };
    const sum = { decisions: 0, same: 0, tied: 0, differs: 0, differ: [], games: [] };
    for (let g = 0; g < o.games; g++) {
        const seed = o.seed + g;
        // each seat: the Python bot plays, the JS bot answers the same decision with the same simulations, and its pick is compared
        const twin = (name) => {
            const py = new StdioClient(name, { cmd: 'python3', args: [o.py ?? path.join('bots', 'jepa', 'jepa_bot.py'), ...pyArgs(GATE, ['--score', 'plan', '--plan-model', GATE.planModel,
                '--plan', `gate=0.04,secs=${plan.secs},floor=0`, '--name', name])], cwd: ROOT, stderr: 'ignore' });
            const js = makeBot({ ...GATE, plan, name });
            return {
                name, py,
                async hello(m) {
                    js.hello(m);
                    return py.hello(m);
                },
                async decide(m, sim) {
                    const a = await py.decide(m, sim);
                    const b = await js.decide(m, sim);
                    if ((m.actions || []).length > 1) {
                        sum.decisions++;
                        const score = js.last?.score;
                        if (a.i === b.i) {
                            sum.same++;
                        } else if (score && Math.abs(score[a.i] - score[b.i]) < 1e-6) {
                            // equal scores (two copies of one card, two moves that settle the same way): numpy's sort picks
                            // one of them, in an order that depends on the computer's sort instructions
                            sum.tied++;
                        } else if (++sum.differs <= 20) {
                            sum.differ.push({ seed, seat: m.you, seq: m.seq, prompt: m.prompt?.type, py: m.actions[a.i].label, js: m.actions[b.i].label,
                                ...(score ? { scores: [score[a.i], score[b.i]] } : {}) });
                        }
                        // the JS bot follows the move played, so both keep the same plan and loop guard
                        if (a.i !== b.i) {
                            js.adopt(a.i);
                        }
                    }
                    return a;
                },
                over: (m) => py.over(m)
            };
        };
        const bots = [twin('a'), twin('b')];
        const pair = [decks[(2 * g) % decks.length], decks[(2 * g + 1) % decks.length]];
        const t0 = Date.now();
        const res = await playGame(env, { seed, bots, decks: { p1: pair[0], p2: pair[1] }, limits: { decide: 600000 } });
        await Promise.all(bots.map((b) => b.py.close()));
        sum.games.push({ seed, outcome: res.outcome, winner: res.winner, steps: res.steps, error: res.error ?? null, secs: Math.round((Date.now() - t0) / 1000) });
        console.error(`game ${seed}: ${res.outcome} ${res.winner} after ${res.steps} steps (${sum.same}/${sum.decisions} same so far)`);
    }
    return { ...sum, ok: sum.differs === 0 && sum.games.every((x) => x.outcome !== 'ERROR') };
}

async function main() {
    const o = options(process.argv.slice(2));
    if (!['features', 'games'].includes(o.mode)) {
        throw new Error('usage: parity.js features|games [--games N] [--seed S] [--decks FILE]');
    }
    const env = new Env();
    const { decks } = loadDecks(o.decks, env);
    const out = await (o.mode === 'features' ? features : games)(o, env, decks);
    console.log(JSON.stringify(out));
    process.exitCode = out.ok ? 0 : 1;
}

main().catch((e) => {
    console.error(e.stack || e);
    process.exit(2);
});
