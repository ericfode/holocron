'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
// Exercise the actual routing helper with injected I/O boundaries. Loading this
// module must not read a registry, engine, source file or build artifact.
const moduleUnderTest = {exports: {}};
new Function('require', 'module', 'exports', '__dirname', fs.readFileSync(path.join(__dirname, '../reference/generate.js'), 'utf8'))(name => {
    if (name === '../kessel') return {holocron: '', kessel: name => name === 'cards/inventory' ? {sha256} : {root: ''}};
    return require(name);
}, moduleUnderTest, moduleUnderTest.exports, path.join(__dirname, '../reference'));
const {selectGenerationEntries} = moduleUnderTest.exports;
const probe = {id: 'auto/TST_001/test', kind: 'probe', source: {module: '../pipeline/probe-fixture.js', scenario: 'test'}};
const named = {id: 'named/test', kind: 'behavior', source: {module: './scenarios/named.js', scenario: 'test'}};
function boundaries(bytes = 'source') {
    const index = {sources: {'./scenarios/named.js': sha256('source')}, cases: [named]}, calls = [];
    return {index, calls, dependencies: {
        registry: () => {calls.push('registry'); return index;},
        readSource: file => {calls.push(file); return bytes;},
        selectCases: (options, actual) => {assert.equal(actual, index); calls.push('selectCases'); return [named];},
    }};
}
test('explicit canonical automatic probes do not read an unrelated broken registry', () => {
    const entries = [probe], forbidden = () => {throw new Error('Unused registry dependency accessed');};
    const selected = selectGenerationEntries({entries}, {registry: forbidden, readSource: forbidden, selectCases: forbidden});
    assert.equal(selected.entries, entries);
    assert.equal(selected.index, null);
});
test('explicit named and diagnostic entries keep the complete strict index validation', () => {
    for (const kind of ['behavior', 'diagnostic', 'play']) {
        const b = boundaries(), entries = [{...named, kind}];
        const selected = selectGenerationEntries({entries}, b.dependencies);
        assert.equal(selected.entries, entries);
        assert.equal(selected.index, b.index); // diagnostic source provenance retains this exact validated index
        assert.deepEqual(b.calls, ['registry', './scenarios/named.js']);
        assert.throws(() => selectGenerationEntries({entries}, boundaries('changed').dependencies), /Stale reference index/);
    }
});
test('mixed explicit entries validate indexed sources before returning any entries', () => {
    const entries = [probe, named], b = boundaries();
    assert.equal(selectGenerationEntries({entries}, b.dependencies).index, b.index);
    assert.deepEqual(b.calls, ['registry', './scenarios/named.js']);
    const missing = boundaries(); missing.dependencies.readSource = () => {throw new Error('missing historical source');};
    assert.throws(() => selectGenerationEntries({entries}, missing.dependencies), /missing historical source/);
});
test('unexpected automatic fixture modules cannot bypass registry validation', () => {
    for (const module of ['./scenarios/other.js', '../pipeline/../pipeline/probe-fixture.js', '/tmp/arbitrary.js', undefined]) {
        const bad = {...probe, source: {module}};
        for (const entries of [[bad], [probe, bad], [bad, named]]) {
            assert.throws(() => selectGenerationEntries({entries}, boundaries().dependencies), /canonical probe fixture/);
        }
    }
    const disguised = {...probe, kind: 'diagnostic'};
    assert.throws(() => selectGenerationEntries({entries: [disguised]}, boundaries('changed').dependencies), /Stale reference index/);
});
test('default selectors require the registry and every indexed source before selection', () => {
    for (const options of [{case: 'named/test'}, {card: 'TST_001'}, {behavior: 'test'}]) {
        const b = boundaries(), selected = selectGenerationEntries(options, b.dependencies);
        assert.equal(selected.index, b.index);
        assert.deepEqual(b.calls, ['registry', './scenarios/named.js', 'selectCases']);
        assert.throws(() => selectGenerationEntries(options, boundaries('changed').dependencies), /Stale reference index/);
    }
});

test('named generation still validates unrelated historical sources, without weakening old receipts', () => {
    const b = boundaries();
    b.index.sources['./scenarios/unselected.js'] = sha256('other');
    assert.throws(() => selectGenerationEntries({entries: [named]}, b.dependencies), /Stale reference index/);
    assert.deepEqual(b.calls, ['registry', './scenarios/named.js', './scenarios/unselected.js']);
});
