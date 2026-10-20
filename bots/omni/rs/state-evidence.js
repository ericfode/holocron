'use strict';

const { supportProjection, supportGrants } = require('./support-state');
const observations = new WeakMap();
const arena = zone => zone === 'groundArena' || zone === 'spaceArena';
const ordinaryUpgrade = card => card.isUpgrade?.() && !card.isToken?.();
const registered = card => card.isUnit?.() || (ordinaryUpgrade(card) && card.isAttached?.());

/** Install before initialiseAsync: onCardMoved fires after zone initialization (Card.postMoveSteps).
 * resolveGameState processes moved-card registrations in that recorded order. It also covers fixture
 * moveTo/attachTo, which deliberately bypass play events. Arena-to-arena moves
 * retain registration order; leaving play and entering again appends anew.
 * This ledger observes engine events; card allocation order is never evidence.
 */
function observeStateEvidence(eg, watchers) {
    if (eg.started) throw new Error('State evidence must start before initialization');
    if (observations.has(eg)) throw new Error('State evidence observer already installed');
    // GameStateManager serializes the whole plain game.state object with v8.
    // Keep only primitive identities there, so every native snapshot/rollback
    // restores chronology together with engine state (manual, phase and quick).
    const key = 'holocronRegistrationEvidenceV1';
    if (eg.game.state[key]) throw new Error('Registration history already exists');
    eg.game.state[key] = { cards: [], processedUnits: [] };
    const ledger = () => {
        const value = eg.game.state[key];
        if (!value || !Array.isArray(value.cards) || !Array.isArray(value.processedUnits)) throw new Error('Registration history missing from native state');
        return value;
    };
    const evidence = { wrapped: new WeakSet(), entered: watchers.cardsEnteredPlayThisPhase(), played: watchers.cardsPlayedThisPhase() };
    for (const field of ['cards', 'processedUnits']) Object.defineProperty(evidence, field, {
        get: () => {
            const cards = new Map(eg.game.allCards.map(c => [c.uuid, c]));
            return ledger()[field].map(uuid => {
                const card = cards.get(uuid);
                if (!card) throw new Error('Recorded registration identity is absent from native state');
                return card;
            });
        },
        set: cards => { ledger()[field] = cards.map(c => c.uuid); }
    });
    observations.set(eg, evidence);
    eg.game.on('onCardMoved', event => {
        const { card, originalZone, newZone } = event;
        // Leaders already show their front-side type when leaving the arena.
        // Remove by witnessed departure, before asking the current card type.
        if (arena(originalZone) && !arena(newZone)) {
            evidence.cards = evidence.cards.filter(c => c !== card);
            evidence.processedUnits = evidence.processedUnits.filter(c => c !== card);
        }
        if (!card.isUnit?.()) return;
        if (!arena(originalZone) && arena(newZone)) {
            if (evidence.cards.includes(card)) throw new Error('Duplicate physical registration entry');
            evidence.cards = [...evidence.cards, card];
        }
    });
    const wrapCard = card => {
        if (typeof card.resolveAbilitiesForNewZone !== 'function' || evidence.wrapped.has(card)) return;
        evidence.wrapped.add(card);
        const resolve = card.resolveAbilitiesForNewZone;
        card.resolveAbilitiesForNewZone = function (...args) {
            const result = resolve.apply(this, args);
            if (this.isUnit?.() && arena(this.zoneName) && !evidence.processedUnits.includes(this)) evidence.processedUnits = [...evidence.processedUnits, this];
            return result;
        };
        if (!ordinaryUpgrade(card)) return;
        const attach = card.attachTo, detach = card.unattach;
        card.attachTo = function (...args) {
            const result = attach.apply(this, args);
            evidence.cards = evidence.cards.filter(c => c !== this);
            if (arena(this.zoneName) && this.isAttached()) evidence.cards = [...evidence.cards, this];
            return result;
        };
        card.unattach = function (...args) {
            const result = detach.apply(this, args);
            evidence.cards = evidence.cards.filter(c => c !== this);
            return result;
        };
    };
    // Game initialization creates all physical deck cards. Instrument completed
    // attachment calls before returning to any caller that can place a fixture.
    evidence.instrument = () => eg.game.allCards.forEach(wrapCard);
    const generateToken = eg.game.generateToken;
    eg.game.generateToken = function (...args) {
        const card = generateToken.apply(this, args);
        wrapCard(card);
        return card;
    };
}
function instrumentStateEvidence(eg) {
    const evidence = observations.get(eg);
    if (!evidence) throw new Error('Missing initialization evidence');
    evidence.instrument();
}

function stateEvidence(eg, support = supportProjection(eg)) {
    const evidence = observations.get(eg);
    if (!evidence) throw new Error('State evidence observer must be installed before game initialization');
    const live = eg.game.allCards.filter(c => arena(c.zoneName) && registered(c));
    if (live.length !== evidence.cards.length || live.some(c => !evidence.cards.includes(c))) {
        throw new Error('Registration observer did not witness every live physical card: ' + JSON.stringify({live:live.map(c=>[eg.cardId(c.uuid),c.internalName,c.zoneName]),observed:evidence.cards.map(c=>[eg.cardId(c.uuid),c.internalName,c.zoneName])}));
    }
    const units = evidence.cards.filter(c => c.isUnit?.());
    if (units.length !== evidence.processedUnits.length || units.some((c, i) => c !== evidence.processedUnits[i])) throw new Error('Physical entry chronology differs from completed native registration sequence');
    for (const zone of ['groundArena', 'spaceArena']) {
        const projected = evidence.cards.filter(c => c.isUnit?.() && c.zoneName === zone);
        const actual = eg.game.getArenaUnits({ arena: zone });
        if (projected.length !== actual.length || projected.some((c, i) => c !== actual[i])) throw new Error('Registration chronology conflicts with engine arena order');
    }
    for (const host of live.filter(c => c.isUnit?.())) {
        const projected = evidence.cards.filter(c => ordinaryUpgrade(c) && c.parentCard === host);
        const actual = (host.upgrades ?? []).filter(ordinaryUpgrade);
        if (projected.length !== actual.length || projected.some((c, i) => c !== actual[i]) ||
            actual.some(c => evidence.cards.indexOf(c) < evidence.cards.indexOf(host))) throw new Error('Registration chronology conflicts with completed physical attachments');
    }
    const id = card => {
        if (!card || !eg.game.state.allCards.includes(card.uuid)) throw new Error('Evidence needs allocated physical card identity');
        return eg.cardId(card.uuid);
    };
    const seat = player => {
        if (!eg.ids.includes(player?.id)) throw new Error('Evidence needs an engine player identity');
        return eg.seatOf(player.id);
    };
    const entries = raw => {
        const unique = new Map(raw.map(({ card, playedBy }) => {
            const entry = { card: id(card), playedBy: seat(playedBy) };
            return [entry.playedBy + '/' + entry.card, entry];
        }));
        return [...unique.values()].sort((a, b) => a.playedBy.localeCompare(b.playedBy) || Number(a.card.slice(1)) - Number(b.card.slice(1)));
    };
    const played = evidence.played.getCurrentValue();
    const playCounts = eg.ids.map(pid => played.filter(entry => entry.playedBy.id === pid).length);
    if (playCounts.some(n => n > 65535)) throw new Error('Phase play count exceeds simulator bounds');
    return { supportStateVersion: 1, supportGrants: supportGrants(eg, support), registrationOrder: { version: 1, cards: evidence.cards.map(id) },
        phaseHistory: { version: 1, entered: entries(evidence.entered.getCurrentValue()), played: entries(played), playCounts } };
}
module.exports = { observeStateEvidence, instrumentStateEvidence, stateEvidence };
