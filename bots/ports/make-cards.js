'use strict';
// Writes cards.json: what the ports need to know about a card that the protocol does not send, by set code
// (<SET>_<NNN>, as `s` in protocol messages): [printed cost, 1 if a unit, aspects as digits of ASPECTS].
// Run after the card data changes:  node bots/ports/make-cards.js [forceteki/test/json/Card]

const fs = require('fs');
const path = require('path');
const { ASPECTS } = require('./common');

const dir = process.argv[2] ?? path.join(__dirname, '..', '..', 'forceteki', 'test', 'json', 'Card');
const code = ({ set, number }) => `${set}_${String(number).padStart(3, '0')}`;
const out = {};
const alias = {};
for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json')).sort()) {
    const c = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    if (!c.setId || c.setId.number == null) {
        continue;
    }
    const aspects = (c.aspects ?? []).map((a) => {
        const k = ASPECTS.indexOf(a);
        if (k < 0) {
            throw new Error(`${f}: unknown aspect ${a}`);
        }
        return k;
    }).join('');
    const row = [c.cost ?? 0, (c.types ?? []).includes('unit') ? 1 : 0, aspects];
    // the engine names a card by its first printing (setId); other printings only fill gaps
    out[code(c.setId)] = row;
    for (const s of c.setCodes ?? []) {
        alias[code(s)] ??= row;
    }
}
for (const [k, row] of Object.entries(alias)) {
    out[k] ??= row;
}
const sorted = Object.fromEntries(Object.keys(out).sort().map((k) => [k, out[k]]));
fs.writeFileSync(path.join(__dirname, 'cards.json'), `${JSON.stringify(sorted)}\n`);
console.log(`${Object.keys(sorted).length} set codes -> bots/ports/cards.json`);
