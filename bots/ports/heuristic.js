'use strict';

/**
 * The heuristic bot (bots/players/heuristic.js, profile balanced, depth 1) as a protocol v2 program: one-ply lookahead
 * through the referee's simulations instead of engine rollback.
 *
 * At each action window it tries every legal action (at most MAX_CANDIDATES) on a simulation, answers the prompts that
 * follow with the rule-based choice until someone's next action window, and scores the board. For the first follow-up
 * prompt of its own (an attack target, a card to pick) it also tries each option (at most MAX_BRANCH). It plays the
 * best line and answers the rest of it from the plan. Prompts outside the action window get the rule-based choice.
 *
 * What changed from the in-process bot: playouts run on the referee's copy of the game, where the cards you cannot see
 * are dealt again (one deal per decision, so every action is scored on the same cards); scores read only what the
 * protocol shows, with printed costs and aspects from cards.json. Without simulations (an arena that offers none) it
 * plays rush's rules at action windows. A time guard stops trying actions when the decision or the game runs long.
 *
 *   node bots/ports/heuristic.js [name]          (the arena bundles it with Javy: bots/ports/README.md)
 */

const C = require('./common');
const { windowChoice } = require('./rush');

const MAX_CANDIDATES = 40;
const MAX_BRANCH = 8;
const PLAYOUT_STEPS = 60;
// time guard: the arena allows 60 s of thinking per game and 10 s per decision; aim well under both
const GAME_MS = 40000;
const WINDOW_MS = 3000;
const MIN_WINDOW_MS = 100;
const SPARE_MS = 1500;

function create(name = 'heuristic-port', { now = () => Date.now() } = {}) {
    let you = 'p1';
    let rng = C.rngOf(0);
    let aspects = { p1: [], p2: [] };
    let plan = [];
    let seen = new Map();
    let used = 0; // ms spent deciding this game
    const stats = { windows: 0, playouts: 0, failed: 0, noops: 0, loopPasses: 0, cut: 0 };

    /** Play `seq` (my action, then my planned follow-ups) on a simulation up to the next action window, and score it. */
    async function playout(sim, seq, guard) {
        stats.playouts++;
        let r = await sim({ t: 'sim', op: 'begin', deal: 0 });
        let branch = null;
        let score = -Infinity;
        let fp = null;
        try {
            if (r.error) {
                throw new Error(r.error);
            }
            r = await sim({ t: 'sim', op: 'act', i: seq[0].i });
            const forced = seq.slice(1);
            for (let k = 0; k < PLAYOUT_STEPS && !r.error && !r.over && !r.prompt.actionWindow; k++) {
                let choice;
                if (r.actor === you && forced.length) {
                    choice = r.actions.find((a) => C.same(a, forced[0]));
                    forced.shift();
                    if (!choice) {
                        throw new Error('forced option vanished');
                    }
                } else {
                    if (k === 0 && r.actor === you && seq.length === 1) {
                        branch = r.actions.map(({ kind, label, cardUuid, arg }) => ({ kind, label, cardUuid, arg }));
                    }
                    choice = C.defaultChoose({ prompt: r.prompt, state: r.state, actions: r.actions, seat: r.actor, aspects: aspects[r.actor] });
                }
                r = await sim({ t: 'sim', op: 'act', i: choice.i });
            }
            if (r.error) {
                throw new Error(r.error);
            }
            score = r.over ? C.evaluate(null, you, r.over) : C.evaluate(r.state, you);
            fp = r.over ? `over:${r.over.winner}` : C.fingerprint(r.state, r.actor, r.prompt.actionWindow);
        } catch {
            stats.failed++;
        }
        guard.left = r.ms ?? guard.left;
        await sim({ t: 'sim', op: 'end' }); // never fails, and does nothing when the simulation already closed
        return { score, branch, fp };
    }

    async function searchWindow(msg, sim, start) {
        const base = C.fingerprint(msg.state, you, true);
        const pass = msg.actions.find(C.isPass);
        // loop guard: the same position keeps coming back to this window, so stop trying things and pass
        const n = (seen.get(base) ?? 0) + 1;
        seen.set(base, n);
        if (n > 2 && pass) {
            stats.loopPasses++;
            return pass;
        }
        const budget = Math.min(WINDOW_MS, (GAME_MS - used) / 10);
        if (!msg.sim || budget < MIN_WINDOW_MS) {
            // no simulations here, or the game's thinking time is nearly spent: rush's rules cost nothing
            stats.cut += msg.sim ? 1 : 0;
            return windowChoice(msg) ?? pass ?? msg.actions[0];
        }
        let cands = msg.actions;
        if (cands.length > MAX_CANDIDATES) {
            const keep = cands.filter((a) => a.kind === 'button');
            const rest = cands.filter((a) => a.kind !== 'button').sort(() => rng() - 0.5);
            cands = [...keep, ...rest].slice(0, MAX_CANDIDATES);
        }
        const guard = { left: msg.ms ?? null };
        const late = () => now() - start > budget || (guard.left !== null && guard.left < SPARE_MS);
        let best = null;
        const consider = (seq, r) => {
            if (r.fp === base) {
                stats.noops++;
                return;
            }
            if (best === null || r.score > best.score) {
                best = { seq, score: r.score };
            }
        };
        for (const a of cands) {
            if (late()) {
                stats.cut++;
                break;
            }
            const r = await playout(sim, [a], guard);
            consider([a], r);
            if (r.branch && r.branch.length > 1) {
                const alts = r.branch.length > MAX_BRANCH ? r.branch.slice().sort(() => rng() - 0.5).slice(0, MAX_BRANCH) : r.branch;
                for (const o of alts) {
                    if (late()) {
                        break;
                    }
                    consider([a, o], await playout(sim, [a, o], guard));
                }
            }
        }
        if (best === null || best.score === -Infinity) {
            // nothing changed the game: pass if we can, otherwise take whatever is offered
            return pass ?? msg.actions[0];
        }
        plan = best.seq.slice(1);
        return best.seq[0];
    }

    function takePlanned(actions) {
        if (!plan.length) {
            return null;
        }
        const live = actions.find((a) => C.same(a, plan[0]));
        plan = live ? plan.slice(1) : [];
        return live ?? null;
    }

    return {
        name,
        stats,
        hello(msg) {
            you = msg.you;
            rng = C.rngOf(msg.seed ?? 0);
            const opp = C.other(you);
            aspects = { [you]: C.deckAspects(msg.deck), [opp]: C.deckAspects(msg.opponent) };
            plan = [];
            seen = new Map();
            used = 0;
            return { t: 'ready', v: 2, name, sim: true };
        },
        async decide(msg, sim) {
            const start = now();
            let a;
            if (msg.prompt.actionWindow) {
                plan = [];
                stats.windows++;
                a = await searchWindow(msg, sim, start);
            } else {
                a = takePlanned(msg.actions) ?? C.defaultChoose({ prompt: msg.prompt, state: msg.state, actions: msg.actions, seat: you, aspects: aspects[you] });
            }
            used += now() - start;
            return { t: 'act', i: a.i };
        }
    };
}

module.exports = { create };
if (require.main === module) {
    require('./stdio').serve(create(process.argv[2]));
}
