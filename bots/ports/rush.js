'use strict';

/**
 * The rush bot (bots/players/rush.js) as a protocol v2 program: fast rules, no lookahead, no simulations.
 *
 * In its action window: play the most expensive card it can from hand, otherwise attack with a unit, otherwise use the
 * leader, otherwise pass. Attack prompts go face first (the enemy base whenever it is selectable). Everything else is
 * the heuristic bot's rule-based choice. A position that keeps coming back to the same window is a loop (a card click
 * that gets cancelled), and the bot passes.
 *
 *   node bots/ports/rush.js [name]          (the arena bundles it with Javy: bots/ports/README.md)
 */

const C = require('./common');

const ARENAS = new Set(['groundArena', 'spaceArena']);

/** Order of preference among card clicks in `you`'s action window (higher first). */
function windowPriority(a, you, state) {
    const c = a.card;
    if (!c || c.ctl !== you) {
        return -1;
    }
    if (c.zone === 'hand') {
        return 300 + C.costOf(c.s);
    }
    const unit = ARENAS.has(c.zone) ? C.findUnit(state, c.id)?.u : null;
    if (unit) {
        return 200 + unit.p;
    }
    if (state.players[you].leader?.id === c.id) {
        return 100;
    }
    return 0;
}

/** The best card click of an action window by windowPriority, or null when there is none worth making. */
function windowChoice(msg) {
    let best = null;
    let bestP = 0;
    for (const a of msg.actions) {
        const p = windowPriority(a, msg.you, msg.state);
        if (p > bestP) {
            best = a;
            bestP = p;
        }
    }
    return best;
}

function attackChoice(actions, you, state) {
    const cards = actions.filter((a) => a.kind === 'card' && a.card);
    const opp = C.other(you);
    const base = cards.find((a) => a.card.ctl === opp && a.card.id === state.players[opp].base.id);
    if (base) {
        return base;
    }
    // no base (e.g. sentinel): hit the enemy unit with the least health left
    const enemies = cards.map((a) => ({ a, u: a.card.ctl === opp ? C.findUnit(state, a.card.id)?.u : null })).filter((x) => x.u);
    if (!enemies.length) {
        return null;
    }
    return enemies.reduce((best, x) => (x.u.h - x.u.d < best.u.h - best.u.d ? x : best)).a;
}

function create(name = 'rush-port') {
    let you = 'p1';
    let aspects = [];
    let seen = new Map();
    const stats = { windows: 0, loopPasses: 0 };
    return {
        name,
        stats,
        hello(msg) {
            you = msg.you;
            aspects = C.deckAspects(msg.deck);
            seen = new Map();
            return { t: 'ready', v: 2, name };
        },
        decide(msg) {
            const { prompt, state, actions } = msg;
            let a = null;
            if (prompt.actionWindow) {
                stats.windows++;
                const me = state.players[you];
                const pass = actions.find(C.isPass);
                // same window, same visible counts as before: something we tried got cancelled, so stop retrying
                const ready = C.units(me).filter((u) => !u.x).length;
                const key = [state.round, me.handCount, me.res.ready, state.players[C.other(you)].base.d, ready].join('|');
                const n = (seen.get(key) ?? 0) + 1;
                seen.set(key, n);
                if (n > 2 && pass) {
                    stats.loopPasses++;
                    a = pass;
                } else {
                    a = windowChoice(msg) ?? pass ?? actions[0];
                }
            } else {
                if (/attack/i.test(`${prompt.title ?? ''} ${prompt.promptTitle ?? ''}`)) {
                    a = attackChoice(actions, you, state);
                }
                a ??= C.defaultChoose({ prompt, state, actions, seat: you, aspects });
            }
            return { t: 'act', i: a.i };
        }
    };
}

module.exports = { create, windowPriority, windowChoice, attackChoice };
if (require.main === module) {
    require('./stdio').serve(create(process.argv[2]));
}
