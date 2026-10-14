'use strict';
// The generation test that Kessel's cards/test/reference-manifest.test.js kept until the generator moved here.
// It stubs the engine and the fixture, so it needs only a Kessel checkout (KESSEL_DIR, default ../kessel).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const { hasKessel, kessel } = require('../kessel');
if (!hasKessel()) { test('the generator needs a Kessel checkout', { skip: 'set KESSEL_DIR' }, () => {}); return; }
const lib = kessel('cards/reference/library');
const { sha256 } = kessel('cards/inventory');

function temporary(t) { const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'swu-manifest-')); t.after(() => fs.rmSync(dir, { recursive: true, force: true })); return dir; }
function moduleWith(file, overrides, suffix = '') {
    const filename = path.resolve(__dirname, '../reference', file), ordinary = createRequire(filename), module = { exports: {} };
    vm.runInNewContext(fs.readFileSync(filename, 'utf8') + suffix, { require: name => Object.hasOwn(overrides, name) ? overrides[name] : ordinary(name), module, exports: module.exports, __dirname: path.dirname(filename), process, Buffer, console });
    return module.exports;
}

test('generation orchestration writes a fresh gzip corpus without changing witness or provenance', async t => {
    const root = temporary(t), out = path.join(root, 'generated'), catalogue = path.join(root, 'catalog.json'), pool = path.join(root, 'pool.json');
    fs.writeFileSync(catalogue, '{"cards":[]}'); fs.writeFileSync(pool, '{}');
    const entry = { id: 'auto/TST_001/generated', kind: 'probe', focusCardIds: ['TST_001'], setupCardIds: [], source: { module: '../pipeline/probe-fixture.js', scenario: 'generated' } };
    const witness = { optional: null, states: [{ z: 1, a: 2 }] };
    const generate = moduleWith('generate.js', {
        '../../../engine/env': { Env: class {} }, '../../../bots/omni/rs/pool': { loadPool: () => ({}) },
        [path.resolve(__dirname, '../pipeline/probe-fixture.js')]: { fixture: async () => ({ witness, records: [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: { sha256: sha256('{}') }, seed: 1, scenario: 'generated' }, { type: 'decision' }, { type: 'state' }, { type: 'result' }] }) },
    }, '\nsourceIdentity = () => ({}); prepareEngine = () => ({storageTest:true});');
    await generate.generate({ out, entries: [entry], catalogue, pool, seed: 1 });
    const artifact = lib.manifestArtifact(out);
    assert.equal(path.basename(artifact.path), 'manifest.json.gz');
    assert.deepEqual(artifact.document.recordings[0].witness, witness);
    assert.equal(artifact.document.recordings[0].provenance.sourceCatalogueSha256, sha256(fs.readFileSync(catalogue)));
    assert.deepEqual(artifact.document.recordings[0].caseDefinition, entry);
});

test('case index paths resolve scenarios here and annotations in Kessel', () => {
    const index = lib.registry();
    for (const file of Object.keys(index.sources)) {
        const where = file.startsWith('./scenarios/') ? path.resolve(__dirname, '../reference', file) : path.resolve(lib.root, file);
        assert.ok(fs.existsSync(where), file);
        assert.equal(sha256(fs.readFileSync(where)), index.sources[file], `${file} changed since Kessel's cases.json was indexed; run npm run kessel:reference -- index`);
    }
    const here = fs.readdirSync(path.resolve(__dirname, '../reference/scenarios')).filter(f => f.endsWith('.js')).map(f => './scenarios/' + f);
    assert.deepEqual(here.sort(), Object.keys(index.sources).filter(f => f.startsWith('./scenarios/')).sort(), 'Every scenario module is indexed');
});
