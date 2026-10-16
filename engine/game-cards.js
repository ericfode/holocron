'use strict';

/**
 * The card data of one game, as every bot gets it in hello.cards (spec/protocol.md): the engine's card objects for
 * every card the game can show a bot. Finding card data is the referee's job, so a bot reads no card files.
 *
 *   gameCards(getter, [deck1, deck2])   // getter: the engine's card-data getter (env.cardDataGetter)
 *   cardGetter(dir?)                    // that getter on a card folder (default the referee's), without the engine
 *   allCards(getter)                    // every card the getter knows (Holocron: a seat that lacks a deck list)
 *   folderCards(dir)                    // every card file in <dir>/Card, without the engine (Holocron: the Karabast seat)
 *
 * For both lists: the leader, a second leader, the base, every deck entry and every sideboard entry, each resolved the
 * engine's way (setCodeMap, then getCardSync), so a reprint code ('JTL_020') gives the card the engine plays (setId
 * HMW_022). Then the 13 tokens. During play the engine reads card data only for these, plus card titles for "name a
 * card" dropdowns, whose labels are titles only. The objects are the getter's own, unchanged; ClientSeat.hello sends a
 * copy. One object per internalName, sorted by internalName, so both seats get the same array: a lookup by title that
 * takes the first match finds the same card for both.
 */
const fs = require('fs');
const path = require('path');

const CARD_DIR = path.join(__dirname, '..', 'forceteki', 'test', 'json');

const byInternalName = (a, b) => (a.internalName < b.internalName ? -1 : a.internalName > b.internalName ? 1 : 0);

/** The set codes a deck list names, in list order. */
const codesOf = (d) => [d.leader?.id, d.secondleader?.id, d.base?.id, ...(d.deck ?? []).map((c) => c.id), ...(d.sideboard ?? []).map((c) => c.id)].filter((id) => id !== undefined);

/** decks: the game's two deck lists, an array or { p1, p2 }. Throws on a set code the card data does not know. */
function gameCards(getter, decks) {
    const byName = new Map();
    const add = (c) => byName.has(c.internalName) || byName.set(c.internalName, c);
    for (const d of Array.isArray(decks) ? decks : Object.values(decks)) {
        for (const code of codesOf(d)) {
            const id = getter.setCodeMap.get(code);
            if (id === undefined) {
                throw new Error(`deck list ${d.metadata?.name ?? '?'}: no card ${code} in the card data`);
            }
            add(getter.getCardSync(id));
        }
    }
    Object.values(getter.tokenData).forEach(add);
    return [...byName.values()].sort(byInternalName);
}

/** The card-data getter env.js uses (forceteki's UnitTestCardDataGetter), on `dir`; it loads none of the engine's cards. */
function cardGetter(dir = CARD_DIR) {
    const { UnitTestCardDataGetter } = require(path.join(__dirname, '..', 'forceteki', 'build', 'server', 'utils', 'cardData', 'UnitTestCardDataGetter.js'));
    return new UnitTestCardDataGetter(dir);
}

/**
 * Every card the getter knows, sorted by internalName: hello's cards for a seat that does not know both deck lists
 * (Holocron's bots/jev/look.js when a list is missing).
 */
function allCards(getter) {
    return getter.cardIds.map((id) => getter.getCardSync(id)).sort(byInternalName);
}

const folders = new Map();

/**
 * Every card file in <dir>/Card, sorted by internalName, read once per folder and without the engine: hello's cards on
 * Karabast (karabast/seat.js), where the opponent's list is not known. A file that is not card JSON is skipped; no
 * Card folder gives an empty list.
 */
function folderCards(dir) {
    if (!folders.has(dir)) {
        const cards = [];
        const folder = path.join(dir, 'Card');
        for (const f of fs.existsSync(folder) ? fs.readdirSync(folder) : []) {
            try {
                const c = JSON.parse(fs.readFileSync(path.join(folder, f), 'utf8'));
                if (c && typeof c.internalName === 'string') {
                    cards.push(c);
                }
            } catch {
                // not a card file
            }
        }
        folders.set(dir, cards.sort(byInternalName));
    }
    return folders.get(dir);
}

module.exports = { gameCards, cardGetter, CARD_DIR, allCards, folderCards };
