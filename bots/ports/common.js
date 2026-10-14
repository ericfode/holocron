'use strict';

/**
 * What the protocol ports of heuristic and rush share: the in-process bots' evaluation and rule-based choices
 * (bots/players/heuristic.js), rewritten over the protocol's messages (spec/protocol.md in the arena: `state` from
 * your seat, `prompt`, `actions`) instead of engine objects. Same weights, same rules; what the protocol does not send
 * (a card's printed cost, whether it is a unit, its aspects) comes from cards.json by set code (make-cards.js).
 *
 * No Node built-ins and no files outside this folder: the arena's JavaScript intake bundles these files with Javy.
 */

const ASPECTS = ['vigilance', 'command', 'aggression', 'cunning', 'heroism', 'villainy'];

let table = null;
/** [cost, unit, aspects] for a set code, or null (tokens, hidden cards, unknown codes). */
function info(s) {
    table ??= require('./cards.json');
    return (s && table[s]) || null;
}
const costOf = (s) => info(s)?.[0] ?? 0;
const isUnitCard = (s) => info(s)?.[1] === 1;
const aspectsOf = (s) => [...(info(s)?.[2] ?? '')].map((d) => ASPECTS[Number(d)]);

/** The aspects a deck list's leader and base give (the engine's getDeckAspects). */
function deckAspects(deck) {
    return [...new Set([deck?.leader?.id, deck?.base?.id].flatMap((s) => aspectsOf(s)))];
}

const HARM = /defeat|damage|attack|exhaust|capture|return|discard|take control|destroy|deal|disable/i;
const HELP = /heal|shield|give|ready|attach|experience|restore|buff|\+\d/i;
const W = { power: 1.3, hp: 0.9, cost: 0.25, shield: 2.2, upgrade: 0.6, sentinel: 1.0, exhaustedMult: 0.85, hand: 1.8, resource: 1.4, initiative: 2.5, baseHp: 0.9 };
const SIDE = { myBase: 1.5, oppBase: 1.5, myUnits: 1, oppUnits: 1, baseDangerHp: 12, dangerScale: 6 };

const other = (seat) => (seat === 'p1' ? 'p2' : 'p1');
const isPass = (a) => a.kind === 'button' && /^pass$/i.test(a.label);
const units = (pl) => [...(pl?.ground ?? []), ...(pl?.space ?? [])];

/** The unit with card id `id` and its seat, or null. */
function findUnit(state, id) {
    for (const seat of ['p1', 'p2']) {
        const u = units(state.players[seat]).find((x) => x.id === id);
        if (u) {
            return { u, seat };
        }
    }
    return null;
}

function unitValue(u) {
    let v = u.p * W.power + Math.max(0, u.h - u.d) * W.hp + costOf(u.s) * W.cost;
    for (const up of u.u ?? []) {
        v += up.t && /^shield$/i.test(up.n) ? W.shield : W.upgrade;
    }
    if (u.sn) {
        v += W.sentinel;
    }
    return u.x ? v * W.exhaustedMult : v;
}

function baseTerm(base) {
    const hp = Math.max(0, base.hp - base.d);
    const danger = hp <= SIDE.baseDangerHp ? ((SIDE.baseDangerHp - hp) ** 2) / SIDE.dangerScale : 0;
    return hp * W.baseHp - danger;
}

function sideValue(state, seat, mine) {
    const p = state.players[seat];
    let v = baseTerm(p.base) * (mine ? SIDE.myBase : SIDE.oppBase);
    const um = mine ? SIDE.myUnits : SIDE.oppUnits;
    for (const u of units(p)) {
        v += unitValue(u) * um;
    }
    v += p.handCount * W.hand + p.res.total * W.resource;
    if (state.initiative === seat) {
        v += W.initiative;
    }
    return v;
}

/** Score of `state` for seat `you` (higher is better); `over` is a finished game's {winner}. */
function evaluate(state, you, over = null) {
    if (over) {
        return over.winner === you ? 10000 : over.winner === other(you) ? -10000 : 0;
    }
    return sideValue(state, you, true) - sideValue(state, other(you), false);
}

/**
 * The visible position, to tell when a line of play changed nothing. Includes who must act and whether it is an action
 * window, so passing (which hands the window to the opponent) is never a no-op.
 */
function fingerprint(state, actor, actionWindow) {
    const parts = [state.round, state.phase, state.initiative, actor, actionWindow ? 'W' : '-'];
    for (const seat of ['p1', 'p2']) {
        const p = state.players[seat];
        parts.push(p.base.d, p.res.ready, p.res.total, p.handCount, p.deck, p.discard?.length ?? 0, p.passed ?? 0, p.out ?? 0);
        for (const u of units(p)) {
            parts.push(u.id, u.d, u.x ? 1 : 0, u.p, u.h, (u.u ?? []).length);
        }
        parts.push(p.leader ? `${p.leader.x ? 1 : 0}${p.leader.dep ? 1 : 0}${p.leader.epic ? 1 : 0}` : '-');
    }
    return parts.join('|');
}

// ---------- rule-based choices (everything outside the action window, and playout continuations) ----------

function keepScore(card, aspects) {
    const off = aspectsOf(card.s).filter((a) => !aspects.includes(a)).length;
    const cost = costOf(card.s);
    return -off * 3 + (isUnitCard(card.s) ? 1.5 : 0) + (cost <= 3 ? 1 : 0) - cost * 0.3;
}

/** How much `seat` wants to pick `card` ({ id, s, zone, ctl }) for a prompt titled `title`. */
function targetScore(card, seat, title, state, aspects) {
    const mine = card.ctl === seat;
    if (card.zone === 'hand' || card.zone === 'discard') {
        return /discard/i.test(title) ? -keepScore(card, aspects) : keepScore(card, aspects);
    }
    const attack = /attack/i.test(title);
    const harm = HARM.test(title);
    const help = HELP.test(title) && !harm;
    const unit = /arena/i.test(card.zone ?? '') ? findUnit(state, card.id)?.u : null;
    const val = unit ? unitValue(unit) : 0;
    if (card.ctl && state.players[card.ctl]?.base.id === card.id) {
        return mine ? -100 : (attack || harm ? 8 : -5);
    }
    if (attack) {
        return mine ? -100 : val - (unit ? unit.h - unit.d : 0) * 0.5 + 10;
    }
    if (harm) {
        return mine ? -50 : val;
    }
    if (help) {
        return mine ? val : -50;
    }
    return mine ? val : -1;
}

function parseMax(title, fallback = 1) {
    const between = /between (\d+) and (\d+)/i.exec(title);
    if (between) {
        return Number(between[2]);
    }
    const n = /(?:select|choose)\s+(?:up to\s+)?(\d+)/i.exec(title);
    return n ? Number(n[1]) : fallback;
}

function buttonScore(label) {
    if (/trigger|yes|use|play|keep/i.test(label)) {
        return 5;
    }
    if (/done|confirm|continue|resolve all|^ok/i.test(label)) {
        return 3;
    }
    if (/pass|^no\b|decline|skip|choose nothing|cancel/i.test(label)) {
        return -3;
    }
    return 0;
}

const maxBy = (list, f) => list.reduce((best, x) => (best === null || f(x) > f(best) ? x : best), null);

/**
 * The rule-based choice of `seat` among `actions` at `prompt`, with `state` seen from any seat (only public facts of
 * the other seat are read). `aspects`: the deck aspects of `seat`. Returns an action.
 */
function defaultChoose({ prompt, state, actions, seat, aspects }) {
    const title = `${prompt.title ?? ''} ${prompt.promptTitle ?? ''}`;
    const buttons = actions.filter((a) => a.kind === 'button');
    const cards = actions.filter((a) => a.kind === 'card');
    if (/initiative/i.test(title)) {
        const b = buttons.find((x) => /yourself/i.test(x.label));
        if (b) {
            return b;
        }
    }
    if (/mulligan/i.test(title)) {
        const b = buttons.find((x) => /keep/i.test(x.label));
        if (b) {
            return b;
        }
    }
    const done = buttons.find((x) => /^(done|confirm|submit|ok)/i.test(x.label));
    if (cards.length) {
        if (done && (prompt.selected?.length ?? 0) >= parseMax(title, 1)) {
            return done;
        }
        return /resource/i.test(title)
            ? maxBy(cards, (a) => -keepScore(a.card, aspects))
            : maxBy(cards, (a) => targetScore(a.card, seat, title, state, aspects));
    }
    // multi-select display prompts keep offering unselected cards after the limit is reached (clicking them does nothing),
    // so stop at the limit and press Done instead of clicking forever
    if (actions.some((a) => a.kind === 'displayCard')) {
        const picked = (prompt.cards ?? []).filter((c) => c.st === 'selected').length;
        if (done && picked >= parseMax(title, 1)) {
            return done;
        }
    }
    const options = actions.filter((a) => a.kind === 'option');
    if (options.length) {
        return /^#\d+$/.test(options[0].label) ? maxBy(options, (a) => Number(a.label.slice(1))) : options[0];
    }
    const nonButtons = actions.filter((a) => a.kind !== 'button');
    if (nonButtons.length) {
        return nonButtons[0];
    }
    return maxBy(buttons, (a) => buttonScore(a.label)) ?? actions[0];
}

/** The same choice in another list of actions (indexes change between positions). */
const same = (a, b) => a.kind === b.kind && a.label === b.label && a.cardUuid === b.cardUuid && a.arg === b.arg;

/** A deterministic random stream from an integer seed (mulberry32). */
function rngOf(seed) {
    let s = seed >>> 0;
    return () => {
        s = (s + 0x6d2b79f5) >>> 0;
        let t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

module.exports = {
    ASPECTS, W, SIDE, info, costOf, isUnitCard, aspectsOf, deckAspects, other, isPass, units, findUnit, unitValue, evaluate,
    fingerprint, keepScore, targetScore, parseMax, buttonScore, defaultChoose, same, rngOf, maxBy
};
