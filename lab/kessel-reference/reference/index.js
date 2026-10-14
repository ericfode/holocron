'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { kessel } = require('../kessel');
const { sha256 } = kessel('cards/inventory');
// Kessel keeps the case index (cases.json, annotations.json, ../behaviors.json); the scenario modules live here.
// `index` rewrites cases.json and behaviors.json in the Kessel checkout (KESSEL_DIR); commit them there.
const { root, read } = kessel('cards/reference/library');
function collectCodes(value) {
    const ids = new Set();
    function visit(v) {
        if (typeof v === 'string' && /^(?:[A-Z][A-Z0-9]{2,3}_\d{3}|TOKEN_[A-Z0-9_]+)$/.test(v)) ids.add(v);
        else if (Array.isArray(v)) v.forEach(visit);
        else if (v && typeof v === 'object') Object.values(v).forEach(visit);
    }
    visit(value); return [...ids].sort();
}
function build() {
    const annotations = read(path.join(root, 'annotations.json'));
    const cases = [], sources = {};
    for (const file of fs.readdirSync(path.join(__dirname, 'scenarios')).filter(f => f.endsWith('.js')).sort()) {
        const module = './scenarios/' + file, suite = file.slice(0, -3);
        sources[module] = sha256(fs.readFileSync(path.join(__dirname, module)));
        if (suite === 'card-play') continue;
        const library = require(path.join(__dirname, module));
        assert.equal(typeof library.fixture, 'function', module + ' needs fixture(env, pool, scenario, seed)');
        for (const scenario of library.scenarios) {
            const id = suite + '/' + scenario.name, setup = JSON.parse(JSON.stringify(scenario)); delete setup.failureOut;
            const focusCardIds = [...new Set([...(scenario.actualScriptedCardIds ?? annotations[id]?.focusCardIds ?? []), ...(scenario.actualTriggeredCardIds ?? [])])].sort();
            cases.push({ id, behaviorIds: [...new Set([suite, ...(scenario.family ? [scenario.family] : [])])],
                kind: scenario.diagnosticOnly || scenario.name.startsWith('SYNTHETIC') ? 'diagnostic' : 'behavior',
                source: { module, scenario: scenario.name }, focusCardIds, setupCardIds: collectCodes(setup), setup,
                assertionStages: [...(library.assertRecording ? ['assertRecording'] : []), ...Object.entries(scenario).filter(([name, value]) => typeof value === 'function' && /assert|observe|before|choose/i.test(name)).map(([name]) => name)] });
        }
    }
    assert.equal(new Set(cases.map(c => c.id)).size, cases.length, 'Duplicate case ID');
    sources['./annotations.json'] = sha256(fs.readFileSync(path.join(root, 'annotations.json')));
    cases.sort((a, b) => a.id.localeCompare(b.id));
    fs.writeFileSync(path.join(root, 'cases.json'), JSON.stringify({ schema: 'swu-reference-cases/v1', sources, cases }, null, 2) + '\n');
    const behaviorIds = [...new Set(['card-play', ...cases.flatMap(c => c.behaviorIds)])].sort();
    fs.writeFileSync(path.join(root, '../behaviors.json'), JSON.stringify({ schema: 'swu-card-behaviors/v1',
        note: 'Reference-test families and semantic subfamilies. Compiler requiredCapabilities are indexed separately from the emitted IR.',
        behaviors: behaviorIds.map(id => ({ id, label: id.replace(/-/g, ' '), kind: id === 'card-play' ? 'play' : 'behavior',
            scope: id === 'card-play' ? 'onCardPlayed event only' : 'The setup and assertions in linked named cases define the scope.' })) }, null, 2) + '\n');
    return { cases: cases.length, behaviors: behaviorIds.length };
}
module.exports = { build, collectCodes };
