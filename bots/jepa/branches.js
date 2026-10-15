'use strict';
// node bots/jepa/branches.js --games 400 --seed 700000 --workers 4 --out data/branch/rush-random [--bots rush,random] [--p 0.35]
//     [--decks decks/ash-meta-2026-09.json] [--macros face,trade,hold --macro-moves 4] [--max-branch 0]
//
// Training data for the JEPA predictor with MANY moves per position. Recorded games show one move per position, so
// the predictor never sees two moves from the same place and learns roughly the average future (the oracle test in
// README.md). Here native bots play a game, and at a sampled action window (the only place the engine rolls back
// exactly) every legal move is played on the same game, then both seats play on with fresh copies of their bots until
// the mover's next decision and its 4th next decision (with more than one legal action, as collect.js records them),
// and the game is rolled back. The main line then goes on with the bot's own move.
//
//
// --macros (the tiered data): at the same points, up to --macro-moves moves (the main-line move and others at random)
// are each played once per macro action (macros.js: a style for the rest of the round). The mover plays that style
// until this round's action phase ends (`rd`, the board when the regroup phase starts), then plays on as its own bot
// with the opponent until the next round's action phase ends (`rd2`): what the round's plan led to, and what it led to
// a round later. --max-branch 0 skips the per-move futures above and records only these.
//
// --extra-rollouts R [--gap-min 0.1] [--judge linear-deck-g4] (more data at pivotal points): after the per-move futures,
// the judge (a lab/eval evaluator) scores each move's settled board; where the best and worst move are at least
// --gap-min apart in judged win chance, every move is played R more times with fresh randomness, and each pass is
// written as one more branch record of the same position ({"rollout": r}). Records carry the judged "gap".
// branch_prep.py --base-only leaves the extra passes out (the same games without them, as a control).
//
// Output: <out>/shard-<first>.jsonl.gz, one gzip member per game:
//   {"t":"game","seed","bots":[p1,p2]}
//   {"t":"b","seed","you","prompt","state","actions","main":i,"br":[{"i","h1":decide|null,"h4":decide|null,"st":{state}|null,"over":winner|null,"err"?}],
//    "mac"?:[{"i","c":macro,"rd":{state}|null,"rd2":{state}|null,"over":winner|null,"steps","err"?}]}
//   {"t":"end","seed","winner","outcome","round","steps"}
// A `decide` body is what a stdio bot would get ({you, prompt, state, actions}), so bots/jepa/features.py encodes it.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { fork } = require('child_process');

function arg(name, dflt) {
    const i = process.argv.indexOf(`--${name}`);
    return i > 0 ? process.argv[i + 1] : dflt;
}

const { view, promptView, actionView, actionKey } = require('../../engine/view');

function decideBody(eg, pid, actions) {
    return { you: eg.seatOf(pid), prompt: promptView(eg, pid), state: view(eg, eg.seatOf(pid)), actions: actions.map((a, i) => actionView(eg, a, i, pid)) };
}

/** The seat to act and its legal actions, or null when nobody can act. */
function toAct(eg) {
    for (const pid of eg.ids) {
        const actions = eg.legalActions(pid);
        if (actions.length) {
            return { pid, actions };
        }
    }
    return null;
}

/**
 * After the root move: play on with fresh bots until `pid`'s next and 4th next decision with a choice.
 * Returns {h1, h4, st, over}; a game that ends first leaves the later targets null and sets `over` to the winner.
 * `st` is the board (from pid's seat) where the move has settled, as the planner in jepa_bot.py judges moves: the first
 * point after it where anyone is in an action window or the action phase is over.
 */
function playOn(eg, pid, makeBots, rng, maxSteps) {
    const bots = makeBots();
    const out = { h1: null, h4: null, st: null, over: null };
    let mine = 0;
    for (let s = 0; s < maxSteps; s++) {
        if (eg.over) {
            out.over = eg.winner;
            return out;
        }
        const who = toAct(eg);
        if (!who) {
            throw new Error('nobody can act');
        }
        if (!out.st && (eg.phase !== 'action' || eg.isActionWindow(who.pid))) {
            out.st = { state: view(eg, eg.seatOf(pid)) };
        }
        if (who.pid === pid && who.actions.length > 1) {
            mine++;
            if (mine === 1) {
                out.h1 = decideBody(eg, pid, who.actions);
            } else if (mine === 4) {
                out.h4 = decideBody(eg, pid, who.actions);
                return out;
            }
        }
        const bot = bots[eg.ids.indexOf(who.pid)];
        const a = who.actions.length === 1 ? who.actions[0] : bot.choose({ game: eg, pid: who.pid, actions: who.actions, rng });
        eg.apply(who.pid, a, rng);
    }
    return out;
}

/**
 * After the root move: the mover plays `mover` (a macro bot) until this round's action phase is over, then a fresh
 * bot of its own (`after()`); the opponent plays `opp` throughout. Returns {rd, rd2, over, steps}: the boards (from
 * pid's seat) where this round's and the next round's action phases have ended, and the winner if the game ends first.
 */
function roundOn(eg, pid, mover, after, opp, rng, maxSteps) {
    const out = { rd: null, rd2: null, over: null, steps: 0 };
    let stage = 0; // 0: this round's action phase, 1: regroup, 2: the next round's action phase
    let bot = mover;
    for (let s = 0; s < maxSteps; s++) {
        out.steps = s;
        if (eg.over) {
            out.over = eg.winner;
            return out;
        }
        const who = toAct(eg);
        if (!who) {
            throw new Error('nobody can act');
        }
        const action = eg.phase === 'action';
        if (stage === 0 && !action) {
            out.rd = { state: view(eg, eg.seatOf(pid)) };
            stage = 1;
            bot = after();
        } else if (stage === 1 && action) {
            stage = 2;
        } else if (stage === 2 && !action) {
            out.rd2 = { state: view(eg, eg.seatOf(pid)) };
            return out;
        }
        const b = who.pid === pid ? bot : opp;
        const a = who.actions.length === 1 ? who.actions[0] : b.choose({ game: eg, pid: who.pid, actions: who.actions, rng });
        eg.apply(who.pid, a, rng);
    }
    throw new Error(`no round end in ${maxSteps} steps`);
}

async function worker(first, count, file, botNames, p, maxBranch, decksFile, macros, macroMoves, extraRollouts = 0, gapMin = 0.1, judgeName = 'linear-deck-g4') {
    const { Env, seededRng } = require('../../engine/env');
    const { makeBot } = require('../players');
    const { createMacroBot } = require('./macros');
    const env = new Env();
    // the judge of --extra-rollouts: the fitted evaluator on each move's settled board, as eval_helper.js scores states
    const judge = extraRollouts > 0 ? require('../../lab/eval/evaluators').loadEvaluator(judgeName) : null;
    const HIDDEN = { id: 'hidden', n: 'hidden card', s: null };
    const withHands = (state) => {
        const players = {};
        for (const [s, pl] of Object.entries(state.players)) {
            players[s] = pl.hand ? pl : { ...pl, hand: Array.from({ length: pl.handCount ?? 0 }, () => HIDDEN) };
        }
        return { ...state, players };
    };
    /** Best minus worst judged win chance over the moves' settled boards (ended games by their result); null if fewer than 2. */
    const judgedGap = (br, seat, decks) => {
        const flat = { p1: decks.p1.deck.flatMap((c) => Array(c.count).fill(c.id)), p2: decks.p2.deck.flatMap((c) => Array(c.count).fill(c.id)) };
        const v = [];
        for (const rec of br) {
            if (rec.over !== null && rec.over !== undefined) {
                v.push(rec.over === seat ? 1 : rec.over === 'draw' ? 0.5 : 0);
            } else if (rec.st?.state) {
                const lg = judge.logit(judge.frame(withHands(rec.st.state), seat, { view: 'subjective', decks: flat, toAct: null }));
                v.push(1 / (1 + Math.exp(-lg)));
            }
        }
        return v.length > 1 ? Math.max(...v) - Math.min(...v) : null;
    };
    // --decks FILE: real deck lists; seed s plays deck pair s mod P, seats swapped on odd passes (as the real-deck test deals)
    const { loadDecks, deckPairs } = require('../../engine/decklists');
    const real = decksFile ? loadDecks(decksFile, env).decks : null;
    const pairs = real ? deckPairs(real.length) : null;
    fs.writeFileSync(file, '');
    let lines = [];
    const write = (o) => lines.push(JSON.stringify(o));
    for (let seed = first; seed < first + count; seed++) {
        const rng = seededRng(`branch:${seed}`);
        const names = seed % 2 === 0 ? botNames : [...botNames].reverse();
        let decks;
        if (real) {
            const [i, j] = pairs[seed % pairs.length];
            const swap = Math.floor(seed / pairs.length) % 2 !== 0;
            decks = swap ? { p1: real[j], p2: real[i] } : { p1: real[i], p2: real[j] };
        } else {
            decks = { p1: env.randomDeck(rng), p2: env.randomDeck(rng) };
        }
        const eg = env.newGame({ seed: String(seed), deck1: decks.p1, deck2: decks.p2, undo: true });
        const bots = names.map((n) => makeBot(n, []));
        const makeBots = () => names.map((n) => makeBot(n, []));
        write({ t: 'game', seed, bots: names, ...(real ? { decks: [decks.p1.metadata.name, decks.p2.metadata.name] } : {}) });
        let steps = 0;
        let outcome = 'won';
        let points = 0;
        try {
            await eg.start();
            while (!eg.over && steps < 6000) {
                const who = toAct(eg);
                if (!who) {
                    outcome = 'STUCK';
                    break;
                }
                const { pid, actions } = who;
                const bot = bots[eg.ids.indexOf(pid)];
                let a = actions.length === 1 ? actions[0] : bot.choose({ game: eg, pid, actions, rng });
                if (actions.length > 1 && eg.isActionWindow(pid) && rng() < p) {
                    const root = decideBody(eg, pid, actions);
                    // search bots (heuristic) return a refetched copy after their own rollback, so match by actionKey as collect.js does
                    const main = actions.findIndex((x) => x === a || actionKey(eg, x) === actionKey(eg, a));
                    const mark = eg.mark(pid);
                    // up to maxBranch moves, always including the main-line move
                    let idx = maxBranch > 0 ? actions.map((_, i) => i) : [];
                    if (idx.length > maxBranch) {
                        idx = idx.filter((i) => i !== main).sort(() => rng() - 0.5).slice(0, maxBranch - 1).concat([main]).sort((x, y) => x - y);
                    }
                    const branchOnce = (tag) => {
                        const out = [];
                        for (const i of idx) {
                            const rec = { i };
                            try {
                                eg.game.setRandomSeed(`${seed}:${steps}:${i}${tag}`);
                                const live = eg.refetch(pid, actions[i]);
                                if (!live) {
                                    throw new Error('move vanished after rollback');
                                }
                                eg.apply(pid, live, rng);
                                Object.assign(rec, playOn(eg, pid, makeBots, rng, 400));
                            } catch (e) {
                                rec.err = String(e?.message ?? e).split('\n')[0].slice(0, 120);
                            }
                            eg.restore(pid, mark);
                            out.push(rec);
                        }
                        return out;
                    };
                    const br = branchOnce('');
                    // --extra-rollouts R: where the moves' settled boards are far apart under the judge (a pivotal point),
                    // play every move R more times with fresh engine and bot randomness; each pass is written as one more
                    // branch record of the same position ("rollout": r), so the training data holds more of these points
                    let gap = null;
                    let extra = [];
                    if (extraRollouts > 0 && judge && br.length > 1) {
                        gap = judgedGap(br, eg.seatOf(pid), decks);
                        if (gap !== null && gap >= gapMin) {
                            extra = Array.from({ length: extraRollouts }, (_, r) => branchOnce(`:x${r + 1}`));
                        }
                    }
                    let mac;
                    if (macros.length) {
                        mac = [];
                        const me = eg.ids.indexOf(pid);
                        const mi = actions.map((_, i) => i).filter((i) => i !== main).sort(() => rng() - 0.5).slice(0, macroMoves - 1).concat([main]).sort((x, y) => x - y);
                        for (const i of mi) {
                            for (const c of macros) {
                                const rec = { i, c };
                                try {
                                    // one engine seed per move for all its macros: the styles are compared on the same draws
                                    eg.game.setRandomSeed(`${seed}:${steps}:${i}:m`);
                                    const live = eg.refetch(pid, actions[i]);
                                    if (!live) {
                                        throw new Error('move vanished after rollback');
                                    }
                                    eg.apply(pid, live, rng);
                                    Object.assign(rec, roundOn(eg, pid, createMacroBot(c), () => makeBot(names[me], []), makeBot(names[1 - me], []), rng, 3000));
                                } catch (e) {
                                    rec.err = String(e?.message ?? e).split('\n')[0].slice(0, 120);
                                }
                                eg.restore(pid, mark);
                                mac.push(rec);
                            }
                        }
                    }
                    write({ t: 'b', seed, ...root, main, br, ...(mac ? { mac } : {}), ...(gap !== null ? { gap: Math.round(gap * 1e4) / 1e4 } : {}) });
                    extra.forEach((x, r) => write({ t: 'b', seed, ...root, main, br: x, rollout: r + 1, gap: Math.round(gap * 1e4) / 1e4 }));
                    points += 1 + extra.length;
                    a = eg.refetch(pid, actions[main]);
                    if (!a) {
                        throw new Error('main-line move vanished after rollback');
                    }
                }
                eg.apply(pid, a, rng);
                steps++;
            }
            if (!eg.over && outcome === 'won') {
                outcome = 'STEP_CAP';
            }
        } catch (e) {
            outcome = 'ERROR';
            write({ t: 'error', seed, error: String(e?.message ?? e).split('\n')[0].slice(0, 200) });
        }
        write({ t: 'end', seed, winner: outcome === 'won' ? eg.winner : null, outcome, round: eg.round, steps, points });
        fs.appendFileSync(file, zlib.gzipSync(`${lines.join('\n')}\n`));
        lines = [];
        process.send?.({ done: 1, points, outcome });
    }
}

async function main() {
    const games = Number(arg('games', 100));
    const seed = Number(arg('seed', 700000));
    const workers = Number(arg('workers', 1));
    const out = path.resolve(arg('out', 'data/branch/rush-random'));
    const botNames = arg('bots', 'rush,random').split(',');
    const p = Number(arg('p', 0.35));
    const maxBranch = Number(arg('max-branch', 12));
    const macros = arg('macros', '') ? arg('macros').split(',') : [];
    const macroMoves = Number(arg('macro-moves', 4));
    const extraRollouts = Number(arg('extra-rollouts', 0));
    const gapMin = Number(arg('gap-min', 0.1));
    const judgeName = arg('judge', 'linear-deck-g4');
    fs.mkdirSync(out, { recursive: true });
    if (process.argv.includes('--worker')) {
        await worker(Number(arg('first')), Number(arg('count')), arg('file'), botNames, p, maxBranch, arg('decks', null), macros, macroMoves,
            extraRollouts, gapMin, judgeName);
        process.exit(0);
    }
    // shards from an earlier run with other seeds or worker counts would be mixed into this one by branch_train.py
    for (const f of fs.readdirSync(out)) {
        if (/^shard-\d+\.jsonl\.gz$/.test(f)) {
            fs.unlinkSync(path.join(out, f));
        }
    }
    const per = Math.ceil(games / workers);
    const t0 = Date.now();
    let done = 0;
    let points = 0;
    const outcomes = {};
    const procs = [];
    for (let k = 0; k < workers; k++) {
        const first = seed + k * per;
        const count = Math.min(per, seed + games - first);
        if (count <= 0) {
            break;
        }
        const file = path.join(out, `shard-${first}.jsonl.gz`);
        const args = ['--worker', '--first', String(first), '--count', String(count), '--file', file, '--bots', botNames.join(','), '--p', String(p), '--max-branch', String(maxBranch), '--macros', macros.join(','), '--macro-moves', String(macroMoves),
            '--extra-rollouts', String(extraRollouts), '--gap-min', String(gapMin), '--judge', judgeName, ...(arg('decks', null) ? ['--decks', path.resolve(arg('decks'))] : [])];
        const proc = fork(__filename, args, { stdio: ['ignore', 'inherit', 'inherit', 'ipc'] });
        proc.on('message', (m) => {
            done += m.done;
            points += m.points;
            outcomes[m.outcome] = (outcomes[m.outcome] ?? 0) + 1;
            const s = (Date.now() - t0) / 1000;
            console.log(`${done}/${games} games, ${points} branch points, ${(s / done).toFixed(1)} s/game, ${JSON.stringify(outcomes)}`);
        });
        procs.push(new Promise((res, rej) => proc.on('exit', (code) => (code === 0 ? res() : rej(new Error(`worker for seeds ${first}.. exited with code ${code}`))))));
    }
    await Promise.all(procs);
    console.log(`wrote ${out} in ${((Date.now() - t0) / 1000).toFixed(0)}s: ${points} branch points ${JSON.stringify(outcomes)}`);
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
