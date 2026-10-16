'use strict';

/**
 * Holocron's own (not part of the arena's player): hello's card data where a seat does not know both deck lists, so
 * it sends every card instead of the game's (game-cards.js gameCards, which stays as the arena has it).
 *
 *   allCards(getter)    // every card the getter knows: bots/jev/look.js when a list is missing
 *   folderCards(dir)    // every card file in <dir>/Card, without the engine: the Karabast seat (karabast/seat.js)
 *
 * Both are sorted by internalName, as gameCards is, so a lookup by title that takes the first match finds the same
 * card in either.
 */
const fs = require('fs');
const path = require('path');

const byInternalName = (a, b) => (a.internalName < b.internalName ? -1 : a.internalName > b.internalName ? 1 : 0);

/** Every card the getter knows, sorted by internalName. */
function allCards(getter) {
    return getter.cardIds.map((id) => getter.getCardSync(id)).sort(byInternalName);
}

const folders = new Map();

/**
 * Every card file in <dir>/Card, sorted by internalName, read once per folder and without the engine. A file that is
 * not card JSON is skipped; no Card folder gives an empty list.
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

module.exports = { allCards, folderCards };
