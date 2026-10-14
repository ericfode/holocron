'use strict';
// Holocron-only checks of the Kessel reference generator's engine side: every fixture and scenario module loads
// from its place here, the dependency inventory names files that exist, and both CLIs parse their options.
// Needs the built engine (forceteki/build) but no Kessel checkout, so it runs in npm test.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { holocron } = require('../kessel');

const pipeline = path.resolve(__dirname, '../pipeline'), scenarios = path.resolve(__dirname, '../reference/scenarios');

test('every probe fixture loads and exports fixture()', () => {
    const files = fs.readdirSync(pipeline).filter((f) => f.endsWith('-fixture.js'));
    assert.ok(files.length >= 27);
    for (const file of files) assert.equal(typeof require(path.join(pipeline, file)).fixture, 'function', file);
});

test('every reference scenario loads with fixture() and its named scenarios', () => {
    for (const file of fs.readdirSync(scenarios).filter((f) => f.endsWith('.js'))) {
        const suite = require(path.join(scenarios, file));
        assert.equal(typeof suite.fixture, 'function', file);
        if (file === 'card-play.js') assert.equal(typeof suite.create, 'function');
        else assert.ok(Array.isArray(suite.scenarios) && suite.scenarios.length, file);
    }
});

test('the fixture dependency inventory names files in this repository or in Kessel', () => {
    const named = new Set(fs.readdirSync(pipeline).filter((f) => f.endsWith('-fixture.js')).flatMap((f) => require(path.join(pipeline, f)).dependencies ?? []));
    assert.ok(named.size > 0);
    for (const file of named) {
        if (file.startsWith('kessel:')) assert.match(file, /^kessel:cards\/pipeline\/[a-z-]+\.js$/);
        else assert.ok(fs.existsSync(path.join(holocron, file)), file);
    }
});

test('pipeline CLI keeps builds mandatory and parses multiple selected cards', () => {
    const { options } = require('../pipeline/cli');
    assert.deepEqual(options(['--cards', 'TWI_124,TWI_170', '--card', 'JTL_052']).cards, ['TWI_124', 'TWI_170', 'JTL_052']);
    assert.throws(() => options(['--no-build']), /Unknown/);
    assert.throws(() => options(['--out']), /Missing/);
});

test('reference CLI parses selections and flags', () => {
    const { options } = require('../reference/cli');
    assert.deepEqual(options(['--card', 'TWI_124', '--play', '--out', '/tmp/x']), { card: 'TWI_124', play: true, out: '/tmp/x' });
    assert.throws(() => options(['--case']), /needs a value/);
    assert.throws(() => options(['--nope']), /Unknown/);
});
