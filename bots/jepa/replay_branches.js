'use strict';
// node bots/jepa/replay_branches.js --out data/branch/op-0 --workers 20 [--who tx-t10-g04] [--p 0.35] [--max-branch 12]
//     [--max N] [--every K --part J] <run dir>...
//
// On-policy branch data. branches.js plays its own games (rush against rush) and, at sampled action windows, plays
// every legal move on the same game; the bot is then tested in other positions, the ones it meets against c-clock.
// Here the main line is a recorded game instead (a run folder with games/, from ladder.js or bot-test.js --record), so
// the branch points are positions a bot really reached. At a sampled action window of a seat whose bot is in --who
// (all seats when it is not given), the game is copied (engine/protocol.js Shadow, as rank_data.js does), every legal
// move (up to --max-branch, the recorded move always in) is played on the copy, both seats play on as rush (branches.js
// playOn) to the mover's next and 4th next decision and the settled board, and the copy is rolled back. The real game
// then goes on with the recorded move. Output is branches.js's format (branch_prep.py, pack_data.py and judge_prep.py
// read it unchanged); the game line also names the recording ("src") and the bots that played it.
// --every K --part J keeps the games whose index in the sorted file list is J mod K (a held-out split by game).
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { fork } = require('child_process');

function arg(name, dflt) {
    const i = process.argv.indexOf(`--${name}`);
    return i > 0 ? process.argv[i + 1] : dflt;
}

/** Game files under each argument: a run folder (its games/), a games folder, or one file. */
function gameFiles(inputs, max) {
    const files = [];
    for (const p of inputs) {
        const dir = fs.existsSync(path.join(p, 'games')) ? path.join(p, 'games') : p;
        const found = fs.statSync(dir).isDirectory()
            ? fs.readdirSync(dir).filter((f) => /\.jsonl(\.gz)?$/.test(f)).sort().map((f) => path.join(dir, f))
            : [dir];
        files.push(...(max ? found.slice(0, max) : found));
    }
    return files;
}

function readGame(file) {
    let text = fs.readFileSync(file);
    if (file.endsWith('.gz')) {
        text = zlib.gunzipSync(text);
    }
    const out = { header: null, steps: [], end: null };
    for (const l of text.toString('utf8').split('\n')) {
        if (!l.trim()) {
            continue;
        }
        const o = JSON.parse(l);
        if (o.t === 'header') {
            out.header = o;
        } else if (o.t === 'step' && o.n > 0) {
            out.steps.push(o);
        } else if (o.t === 'end') {
            out.end = o;
        }
    }
    return out;
}

const srcOf = (f) => path.basename(path.dirname(path.dirname(f))) + '/' + path.basename(f).replace(/\.jsonl(\.gz)?$/, '');

async function worker(files, file, cfg) {
    const { Env, seededRng } = require('../../engine/env');
    const { gameStreams } = require('../../engine/rng');
    const { actionKey } = require('../../engine/view');
    const { Shadow } = require('../../engine/protocol');
    const { makeBot } = require('../players');
    const { playOn, decideBody } = require('./branches');
    const env = new Env();
    fs.writeFileSync(file, '');
    const makeBots = () => cfg.playOn.map((n) => makeBot(n, []));
    for (const f of files) {
        let g;
        try {
            g = readGame(f);
        } catch {
            process.send?.({ done: 1, points: 0, outcome: 'unreadable' });
            continue;
        }
        const { header, steps, end } = g;
        if (!header?.decks?.p1 || !header?.decks?.p2 || !end) {
            process.send?.({ done: 1, points: 0, outcome: 'no decks' });
            continue;
        }
        const bots = header.players.map((p) => p.bot);
        const seats = ['p1', 'p2'].filter((s, k) => !cfg.who || cfg.who.includes(String(bots[k]).split('#')[0]));
        const src = srcOf(f);
        const rng = seededRng(`replay-branch:${src}`);
        const setup = { seed: gameStreams(header.seed, end.key ?? null).engine, deck1: header.decks.p1, deck2: header.decks.p2 };
        const lines = [JSON.stringify({ t: 'game', seed: header.seed, bots, src, decks: [header.decks.p1?.metadata?.name ?? header.decks.p1, header.decks.p2?.metadata?.name ?? header.decks.p2] })];
        let points = 0;
        let outcome = 'won';
        try {
            const real = env.newGame(setup);
            const shadow = new Shadow(env, setup);
            await real.start();
            for (let k = 0; k < steps.length; k++) {
                const s = steps[k];
                const pid = real.pidOf(s.pid);
                const actions = real.legalActions(pid);
                const a = actions[s.action.i];
                if (actions.length !== s.legal || a?.label !== s.action.label) {
                    outcome = 'drift';
                    break;
                }
                if (actions.length > 1 && seats.includes(s.pid) && real.isActionWindow(pid) && rng() < cfg.p) {
                    const eg = await shadow.sync(real, pid);
                    if (eg) {
                        const rootActions = eg.legalActions(pid);
                        const root = decideBody(eg, pid, rootActions);
                        const main = s.action.i;
                        let idx = rootActions.map((_, i) => i);
                        if (idx.length > cfg.maxBranch) {
                            idx = idx.filter((i) => i !== main).sort(() => rng() - 0.5).slice(0, cfg.maxBranch - 1).concat([main]).sort((x, y) => x - y);
                        }
                        const mark = eg.mark(pid);
                        const br = [];
                        let broken = false;
                        for (const i of idx) {
                            const rec = { i };
                            try {
                                const live = eg.refetch(pid, rootActions[i]);
                                if (!live) {
                                    throw new Error('move vanished after rollback');
                                }
                                eg.apply(pid, live, rng);
                                Object.assign(rec, playOn(eg, pid, makeBots, rng, 400));
                            } catch (e) {
                                rec.err = String(e?.message ?? e).split('\n')[0].slice(0, 120);
                            }
                            try {
                                eg.restore(pid, mark);
                            } catch {
                                broken = true; // the copy is built again at the next sync
                            }
                            br.push(rec);
                            if (broken) {
                                break;
                            }
                        }
                        // the copy plays on from the rolled-back position, which can differ from a game never rolled
                        // back (known engine bug 6), so it is rebuilt from the real moves before the next branch point
                        shadow.drop();
                        lines.push(JSON.stringify({ t: 'b', seed: header.seed, src, step: k, ...root, main, br }));
                        points++;
                    }
                }
                shadow.record({ pid, i: s.action.i, legal: actions.length, key: actionKey(real, a), split: s.action.split });
                real.apply(pid, s.action.split ? { ...a, split: s.action.split.map((e) => ({ id: real.uuidOf(e.id), amount: e.amount })) } : a);
            }
        } catch (e) {
            outcome = 'ERROR';
            lines.push(JSON.stringify({ t: 'error', seed: header.seed, error: String(e?.message ?? e).split('\n')[0].slice(0, 200) }));
        }
        lines.push(JSON.stringify({ t: 'end', seed: header.seed, winner: end.winner, outcome, round: end.round, steps: steps.length, points }));
        if (points) {
            fs.appendFileSync(file, zlib.gzipSync(`${lines.join('\n')}\n`));
        }
        process.send?.({ done: 1, points, outcome });
    }
}

async function main() {
    const cfg = {
        who: arg('who', '') ? arg('who').split(',') : null,
        p: Number(arg('p', 0.35)),
        maxBranch: Number(arg('max-branch', 12)),
        playOn: arg('play-on', 'rush,rush').split(','),
    };
    if (process.argv.includes('--worker')) {
        const files = await new Promise((resolve) => process.once('message', (m) => resolve(m.files)));
        await worker(files, arg('file'), JSON.parse(arg('cfg')));
        process.exit(0);
    }
    const out = path.resolve(arg('out', 'data/branch/op-0'));
    const workers = Number(arg('workers', 4));
    const every = Number(arg('every', 1));
    const part = Number(arg('part', 0));
    const inputs = process.argv.slice(2).filter((x, i, all) => !x.startsWith('--') && !(all[i - 1] ?? '').startsWith('--'));
    const files = gameFiles(inputs, Number(arg('max', 0))).filter((_, i) => i % every === part);
    fs.mkdirSync(out, { recursive: true });
    for (const f of fs.readdirSync(out)) {
        if (/^shard-\d+\.jsonl\.gz$/.test(f)) {
            fs.unlinkSync(path.join(out, f));
        }
    }
    const t0 = Date.now();
    let done = 0;
    let points = 0;
    const outcomes = {};
    const procs = [];
    for (let k = 0; k < workers; k++) {
        const mine = files.filter((_, i) => i % workers === k);
        if (!mine.length) {
            break;
        }
        const p = fork(__filename, ['--worker', '--file', path.join(out, `shard-${k}.jsonl.gz`), '--cfg', JSON.stringify(cfg)], { stdio: ['ignore', 'inherit', 'inherit', 'ipc'] });
        p.send({ files: mine });
        p.on('message', (m) => {
            done += m.done;
            points += m.points;
            outcomes[m.outcome] = (outcomes[m.outcome] ?? 0) + 1;
            if (done % 25 === 0 || done === files.length) {
                const s = (Date.now() - t0) / 1000;
                console.log(`${done}/${files.length} games, ${points} branch points, ${(s / done).toFixed(1)} s/game, ${JSON.stringify(outcomes)}`);
            }
        });
        procs.push(new Promise((res, rej) => p.on('exit', (code) => (code === 0 ? res() : rej(new Error(`worker ${k} exited with code ${code}`))))));
    }
    await Promise.all(procs);
    console.log(`wrote ${out} in ${((Date.now() - t0) / 1000).toFixed(0)}s from ${files.length} games: ${points} branch points ${JSON.stringify(outcomes)}`);
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
