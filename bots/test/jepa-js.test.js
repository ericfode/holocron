'use strict';
// The JavaScript JEPA bot (bots/jepa/js/jepa.js) against jepa_bot.py: hashed ids, Python's random numbers, the model
// files, a protocol hello, and (with the built engine, card data and numpy) every decision of a real-deck game:
// features, imagined scores and resource choices (bots/jepa/js/parity.js features).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { JepaBot, TxModel, PyRandom, loadModel, hashId, canon } = require('../jepa/js/jepa');

const ROOT = path.join(__dirname, '..', '..');
const MODELS = path.join(ROOT, 'bots', 'jepa', 'models');
const read = (name) => loadModel(fs.readFileSync(path.join(MODELS, name)));

test('hashed ids are features.hash_id (FNV-1a, 2048 buckets)', () => {
    // python3 -c "import features as F; print([F.hash_id(s) for s in ...])" in bots/jepa
    assert.deepStrictEqual(['card:SOR_042', 'button:pass', 'option:2', 'card:', 'perCardButton:play'].map(hashId), [556, 452, 1032, 671, 1162]);
});

test("PyRandom draws Python's random.Random numbers", () => {
    let r = new PyRandom(12345);
    assert.deepStrictEqual([1, 2, 3, 5, 7, 10, 16, 17, 100, 1000, 65537, 2 ** 31 + 5].map((n) => r.below(n)), [0, 0, 1, 2, 1, 4, 13, 5, 47, 127, 56745, 1121373020]);
    r = new PyRandom(0);
    assert.deepStrictEqual(Array.from({ length: 6 }, () => r.choice([0, 1, 2, 3, 4, 5, 6, 7, 8])), [6, 6, 0, 4, 8, 7]);
    r = new PyRandom(4294967295);
    assert.deepStrictEqual(Array.from({ length: 6 }, () => r.below(13)), [10, 9, 3, 3, 9, 8]);
});

test('canon is sort_keys JSON: equal values give equal text', () => {
    assert.strictEqual(canon({ b: [1, { d: null, c: 'x' }], a: true }), canon({ a: true, b: [1, { c: 'x', d: null }] }));
    assert.notStrictEqual(canon({ a: 1 }), canon({ a: 2 }));
});

test("jepa-tx-gate's models load as transformer JEPAs with a settled horizon", () => {
    for (const name of ['tx-t10.safetensors', 'tx-t10-e.safetensors']) {
        const net = new TxModel(read(name));
        assert.deepStrictEqual([net.L, net.H, net.T, net.dm], [2, 4, 24, 64]);
        assert.ok(net.horizons.includes('s'));
    }
    assert.throws(() => new TxModel(read('jepa-v1.safetensors')), /not a transformer JEPA/);
});

test('hello: protocol v2 with simulations in plan mode, v1 without', () => {
    const cards = { db: new Map(), meta: new Map() };
    const model = read('tx-t10.safetensors');
    const plan = new JepaBot({ model, cards });
    assert.deepStrictEqual(plan.hello({ t: 'hello', seed: 3, versions: [1, 2] }), { t: 'ready', v: 2, name: 'jepa-tx-gate', sim: true });
    const imagined = new JepaBot({ model, cards, score: 'imagined', name: 'j' });
    assert.deepStrictEqual(imagined.hello({ t: 'hello', seed: 3, versions: [1, 2] }), { t: 'ready', v: 1, name: 'j' });
});

test('every decision of a real-deck game matches jepa_bot.py (features, scores, resource choices)', (t) => {
    const numpy = spawnSync('python3', ['-c', 'import numpy'], { encoding: 'utf8' });
    if (numpy.status !== 0) {
        t.skip('no python3 with numpy');
        return;
    }
    if (!fs.existsSync(path.join(ROOT, 'forceteki', 'build', 'server')) || !fs.existsSync(path.join(ROOT, 'forceteki', 'test', 'json', 'Card'))) {
        t.skip('no engine or card data');
        return;
    }
    const r = spawnSync(process.execPath, [path.join(ROOT, 'bots', 'jepa', 'js', 'parity.js'), 'features', '--games', '1'], { cwd: ROOT, encoding: 'utf8', timeout: 300000 });
    const out = JSON.parse(r.stdout.trim().split('\n').pop() || '{}');
    assert.ok(out.decisions > 50, `${out.decisions} decisions checked\n${r.stderr}`);
    assert.strictEqual(out.ok, true, JSON.stringify(out));
});
