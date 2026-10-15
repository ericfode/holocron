'use strict';
/**
 * Macro actions for the tiered JEPA data (branches.js --macros): styles a player can follow for the rest of a round. Each one is a small rule-based bot that stands for a whole set of moves, so a model can be asked "if I play
 * this card now and then play the round like this, where does the board end up?".
 *
 *   face     rush.js as it is: play the most expensive card, attack with ready units, enemy base first
 *   trade    the same moves, but attacks go at enemy units first (the one with the least health left), the base only
 *            when no unit can be picked
 *   wide     as face, but the cheapest card in hand first: more, smaller cards instead of the biggest one
 *   hold     no more cards this round: claim the initiative when it is free, else pass
 *
 * Prompts outside the action window (targets, resource choices, triggers) go to rush.js's rules, so the styles differ
 * only in what they do with the round. The data uses face, trade and hold: on 4 smoke-test games wide gave the same
 * round as face for most moves and was the best style for 2 of 205 moves.
 */
const { createRushBot, windowPriority } = require('../players/rush');
const { arenaUnits } = require('../players/heuristic');

const MACROS = ['face', 'trade', 'wide', 'hold'];

const isPass = (a) => a.kind === 'button' && /^pass$/i.test(a.label);
const isClaim = (a) => a.kind === 'button' && /initiative/i.test(a.label);

function unitFirst(acts, pl) {
    const cards = acts.filter((a) => a.kind === 'card' && a.card);
    const enemies = cards.filter((a) => a.card.controller !== pl && a.card.isUnit?.());
    if (enemies.length) {
        return enemies.reduce((best, a) => ((a.card.remainingHp ?? 99) < (best.card.remainingHp ?? 99) ? a : best));
    }
    return cards.find((a) => a.card.isBase?.() && a.card.controller !== pl) ?? null;
}

/** A bot that plays `style` in its action windows; see the list above. */
function createMacroBot(style) {
    if (!MACROS.includes(style)) {
        throw new Error(`unknown macro ${style} (${MACROS.join(', ')})`);
    }
    const rush = createRushBot(`macro-${style}`);
    if (style === 'face') {
        return rush;
    }
    const seen = new Map();
    return {
        name: `macro-${style}`,
        choose(ctx) {
            const { game: eg, pid, actions } = ctx;
            const pl = eg.player(pid);
            if (eg.isActionWindow(pid)) {
                const pass = actions.find(isPass);
                if (style === 'hold') {
                    return actions.find(isClaim) ?? pass ?? actions[0];
                }
                // the same loop guard as rush.js: a window that keeps coming back with nothing changed means a pick got cancelled
                const key = [eg.round, pl.hand.length, pl.readyResourceCount, pl.opponent.base.damage, arenaUnits(pl).filter((u) => !u.exhausted).length].join('|');
                const n = (seen.get(key) ?? 0) + 1;
                seen.set(key, n);
                if (n > 2 && pass) {
                    return pass;
                }
                let best = null;
                let bestP = 0;
                for (const a of actions) {
                    let p = windowPriority(a, pl);
                    if (style === 'wide' && p >= 300) {
                        p = 300 + Math.max(0, 50 - (a.card.cost ?? 0)); // a card from hand: cheapest first
                    }
                    if (p > bestP) {
                        best = a;
                        bestP = p;
                    }
                }
                return best ?? pass ?? actions[0];
            }
            if (style === 'trade') {
                const prompt = pl.currentPrompt();
                if (/attack/i.test(`${prompt.menuTitle ?? ''} ${prompt.promptTitle ?? ''}`)) {
                    const a = unitFirst(actions, pl);
                    if (a) {
                        return a;
                    }
                }
            }
            return rush.choose(ctx);
        }
    };
}

module.exports = { MACROS, createMacroBot };
