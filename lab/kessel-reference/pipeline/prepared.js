'use strict';
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { holocron, kessel, kesselDir } = require('../kessel');
const { sha256 } = kessel('cards/inventory');
const { compileCatalog } = kessel('compiler/build');
const { implementationSnapshot } = kessel('cards/pipeline/review');
const reference = require('../reference/generate');
// Native and Wasm builds (and their cargo cache) happen in the Kessel checkout; the reference engine is Holocron's.
const repo = kesselDir();
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
function command(exe, args, env) { const r = spawnSync(exe, args, { cwd: repo, env, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }); if (r.error)
    throw r.error; assert.equal(r.status, 0, r.stderr || r.stdout); return r.stdout; }
function packageHashes(dir) { const rows = []; for (const relative of fs.readdirSync(dir, { recursive: true }).sort()) {
    const file = path.join(dir, relative), stat = fs.lstatSync(file);
    assert.ok(!stat.isSymbolicLink(), 'Prepared Wasm files cannot be symlinks');
    if (stat.isFile())
        rows.push([relative.split(path.sep).join('/'), sha256(fs.readFileSync(file))]);
} return Object.fromEntries(rows); }
// Everything a prepared run executes besides Kessel's implementation snapshot (review.js): Holocron's game player,
// fixtures, generator and bots, and Kessel's build script, Wasm adapter, compiler and corpus code ('kessel:' paths).
function executionSnapshot() {
    const roots = { '': holocron, 'kessel:': repo }, files = new Set(['package.json', 'package-lock.json', 'kessel:crates/kessel-wasm/build.js']);
    for (const file of fs.readdirSync(path.join(holocron, 'engine')).filter(f => /\.(js|mjs)$/.test(f))) files.add('engine/' + file);
    for (const file of fs.readdirSync(path.join(holocron, 'bots/omni')).filter(f => /\.(js|mjs)$/.test(f))) files.add('bots/omni/' + file);
    for (const dir of ['lab/kessel-reference', 'bots/omni/rs', 'bots/players', 'bots/examples', 'lab/eval', 'bots/learned', 'kessel:cards/reference', 'kessel:crates/kessel-wasm/js', 'kessel:compiler']) {
        const [prefix, relative] = dir.startsWith('kessel:') ? ['kessel:', dir.slice('kessel:'.length)] : ['', dir];
        for (const f of fs.readdirSync(path.join(roots[prefix], relative), { recursive: true }).filter(f => /\.(?:js|mjs|json)$/.test(f) && !f.startsWith('generated' + path.sep) && !f.startsWith('test' + path.sep) && !f.startsWith('node_modules' + path.sep) && !(relative === 'cards/reference' && f.startsWith('fixtures' + path.sep))))
            files.add(dir + '/' + f.split(path.sep).join('/'));
    }
    const file = (name) => name.startsWith('kessel:') ? path.join(repo, name.slice('kessel:'.length)) : path.join(holocron, name);
    return [...files].sort().map(name => ({ path: name, sha256: sha256(fs.readFileSync(file(name))) }));
}
function artifact(root, relative) { assert.equal(typeof relative, 'string'); const file = path.resolve(root, relative); assert.ok(file.startsWith(root + path.sep), 'Prepared artifact escaped directory'); assert.equal(fs.realpathSync(file), file, 'Prepared artifacts cannot be symlinks'); return file; }
// Selection is a projection of the freshly built native binary's admitted pool.
// Catalogue rows and caller metadata are never used to fill missing definitions.
function selectPool(admitted, cardIds) {
    assert.ok(Array.isArray(cardIds) && cardIds.length, 'poolCards must be a nonempty array');
    assert.ok(cardIds.every(id => typeof id === 'string' && id.length), 'poolCards requires card IDs');
    assert.equal(new Set(cardIds).size, cardIds.length, 'Duplicate poolCards ID');
    assert.ok(admitted?.schema === 'omni-rs-pool-v1' && Array.isArray(admitted.cards), 'Invalid admitted pool');
    const available = new Set(admitted.cards.map(c => c.setCode));
    assert.equal(available.size, admitted.cards.length, 'Duplicate admitted pool ID');
    for (const id of cardIds) assert.ok(available.has(id), 'Unknown or unadmitted poolCards ID: ' + id);
    const requested = new Set(cardIds);
    return { ...admitted, cards: admitted.cards.filter(c => requested.has(c.setCode)) };
}
function verifyPoolSelection(root, selection, actual) {
    assert.deepEqual(Object.keys(selection).sort(), ['admittedPool', 'cardIds'], 'Invalid prepared pool selection');
    assert.deepEqual(Object.keys(selection.admittedPool).sort(), ['path', 'sha256'], 'Invalid admitted pool artifact');
    const file = artifact(root, selection.admittedPool.path), bytes = fs.readFileSync(file);
    assert.equal(sha256(bytes), selection.admittedPool.sha256, 'Prepared admitted pool changed');
    assert.deepEqual(selectPool(JSON.parse(bytes), selection.cardIds), actual, 'Prepared selected pool differs from admitted projection');
}
function loadPrepared(input) {
    const resolved = path.resolve(input), file = fs.statSync(resolved).isDirectory() ? path.join(resolved, 'manifest.json') : resolved, root = fs.realpathSync(path.dirname(file)), bytes = fs.readFileSync(file), m = JSON.parse(bytes);
    assert.equal(m.schema, 'swu-card-pipeline-prepared/v1');
    assert.deepEqual(Object.keys(m.artifacts).sort(), ['admission', 'catalogue', 'native', 'pool', 'rules']);
    assert.ok(m.wasmPackage.files['kessel_wasm.js'] && m.wasmPackage.files['kessel_wasm_bg.wasm'], 'Prepared Wasm loader/binary missing');
    assert.equal(m.nodeVersion, process.version, 'Prepared Node version differs');
    const paths = {};
    for (const [key, row] of Object.entries(m.artifacts)) {
        const p = artifact(root, row.path);
        assert.equal(sha256(fs.readFileSync(p)), row.sha256, 'Prepared ' + key + ' changed');
        paths[key] = p;
    }
    if (m.poolSelection !== undefined) { assert.notEqual(m.poolSelection.admittedPool?.path, m.artifacts.pool.path, 'Admitted pool requires a separate artifact'); verifyPoolSelection(root, m.poolSelection, JSON.parse(fs.readFileSync(paths.pool))); }
    const wasmPackage = artifact(root, m.wasmPackage.path);
    assert.deepEqual(packageHashes(wasmPackage), m.wasmPackage.files, 'Prepared Wasm package changed');
    assert.deepEqual(executionSnapshot(), m.executionInputs, 'Prepared execution inputs changed');
    assert.equal(sha256(Buffer.from(JSON.stringify(JSON.parse(fs.readFileSync(paths.catalogue))))), m.catalogueSemanticSha256, 'Prepared semantic catalogue differs');
    assert.deepEqual(implementationSnapshot(), m.implementationBefore, 'Implementation changed since preparation');
    reference.verifyPreparedEngine(m.engineBuild);
    assert.deepEqual(reference.sourceIdentity(), m.sourceIdentity, 'Reference inputs changed since preparation');
    return { directory: root, cataloguePath: paths.catalogue, catalogueSha256: m.artifacts.catalogue.sha256, catalogue: JSON.parse(fs.readFileSync(paths.catalogue)), admission: JSON.parse(fs.readFileSync(paths.admission)), pool: JSON.parse(fs.readFileSync(paths.pool)), rules: JSON.parse(fs.readFileSync(paths.rules)), native: paths.native, wasmPackage, implementationBefore: m.implementationBefore, engineBuild: m.engineBuild, buildMode: m.buildMode, sourceIdentity: m.sourceIdentity, manifestSha256: sha256(bytes), manifestPath: file, ...(m.poolSelection === undefined ? {} : {poolSelection:m.poolSelection}) };
}
function acquireBuildCache({ out, cache, full = false } = {}) {
    assert.equal(typeof full, 'boolean', 'full must be a boolean checkpoint option');
    if(full)assert.ok(out,'Full checkpoint needs a fresh output directory');
    const directory = full ? path.resolve(out) : path.resolve(cache ?? path.join(repo, 'target/card-pipeline-cache'));
    fs.mkdirSync(directory, { recursive: true });
    const lock = path.join(directory, 'build.lock'), token = require('node:crypto').randomUUID();
    try { write(lock, { token, pid: process.pid, host: require('node:os').hostname() }); }
    catch(error) { if(error.code === 'EEXIST') throw new Error('Pipeline build cache is locked; never steal a stale lock automatically: '+lock); throw error; }
    const target = full ? path.join(path.resolve(out), 'build-target') : cache === undefined ? path.join(repo, 'target') : path.join(directory, 'target');
    const catalogue = full ? path.join(path.resolve(out), 'catalog.json') : path.join(directory, 'catalog.json');
    return { target, catalogue, mode: full ? 'full-checkpoint' : 'incremental', release() { assert.equal(JSON.parse(fs.readFileSync(lock)).token, token, 'Build cache lock ownership changed'); fs.unlinkSync(lock); } };
}
async function prepare({ out, cache, full = false, poolCards } = {}) {
    assert.ok(!(full && poolCards !== undefined), 'Full checkpoint preparation requires the entire admitted pool');
    if (poolCards !== undefined) { assert.ok(Array.isArray(poolCards) && poolCards.length, 'poolCards must be a nonempty array'); assert.equal(new Set(poolCards).size, poolCards.length, 'Duplicate poolCards ID'); }
    assert.ok(out, 'prepare needs --out NEW_DIRECTORY');
    out = path.resolve(out);
    assert.ok(!fs.existsSync(out), 'Use a fresh preparation directory');
    const implementationBefore = implementationSnapshot(), executionInputs = executionSnapshot(), referenceBefore = reference.sourceIdentity(), catalogue = compileCatalog();
    fs.mkdirSync(out, { recursive: true });
    const catalogFile = path.join(out, 'catalog.json');
    write(catalogFile, catalogue);
    const lease = acquireBuildCache({out,cache,full});
    try {
    const target = lease.target;
    if(lease.catalogue !== catalogFile && (!fs.existsSync(lease.catalogue) || !fs.readFileSync(lease.catalogue).equals(fs.readFileSync(catalogFile))))fs.copyFileSync(catalogFile,lease.catalogue);
    const env = { ...process.env, CARGO_TARGET_DIR: target, SWU_RULES_CATALOGUE: lease.catalogue };
    console.error('Preparing reference engine, native and Wasm once…');
    const engineBuild = reference.prepareEngine();
    command('cargo', ['build', '--locked', '--release', '-p', 'kessel'], env);
    command(process.execPath, ['crates/kessel-wasm/build.js', '--target', 'node', '--out-dir', path.join(out, 'wasm')], env);
    const native = path.join(out, process.platform === 'win32' ? 'kessel.exe' : 'kessel');
    fs.copyFileSync(path.join(target, 'release', path.basename(native)), native);
    fs.chmodSync(native, 0o755);
    const poolFile = path.join(out, 'pool.json');
    write(path.join(out, 'admission.json'), JSON.parse(command(native, ['catalogue', catalogFile, '--out-pool', poolFile], env)));
    let poolSelection;
    if (poolCards !== undefined) {
        const admittedFile = path.join(out, 'admitted-pool.json');
        const selected = selectPool(JSON.parse(fs.readFileSync(poolFile)), poolCards);
        fs.renameSync(poolFile, admittedFile);
        write(poolFile, selected);
        poolSelection = {cardIds:[...poolCards], admittedPool:{path:'admitted-pool.json', sha256:sha256(fs.readFileSync(admittedFile))}};
    }
    write(path.join(out, 'rules.json'), JSON.parse(command(native, ['rules', '--catalogue', catalogFile, '--pool', poolFile], env)));
    assert.deepEqual(implementationSnapshot(), implementationBefore, 'Implementation changed during preparation');
    reference.verifyPreparedEngine(engineBuild);
    const sourceIdentity = reference.sourceIdentity();
    for (const [key, value] of Object.entries(referenceBefore))
        if (key !== 'engineBuildSha256')
            assert.deepEqual(sourceIdentity[key], value, 'Reference input changed during preparation: ' + key);
    assert.deepEqual(executionSnapshot(), executionInputs, 'Execution input changed during preparation');
    const artifacts = {};
    for (const [key, name] of Object.entries({ catalogue: 'catalog.json', admission: 'admission.json', pool: 'pool.json', rules: 'rules.json', native: path.basename(native) }))
        artifacts[key] = { path: name, sha256: sha256(fs.readFileSync(path.join(out, name))) };
    const manifest = { schema: 'swu-card-pipeline-prepared/v1', nodeVersion: process.version, buildMode: lease.mode, implementationBefore, executionInputs, catalogueSemanticSha256: sha256(Buffer.from(JSON.stringify(catalogue))), engineBuild, sourceIdentity, artifacts, wasmPackage: { path: 'wasm/node', files: packageHashes(path.join(out, 'wasm/node')) } };
    if (poolSelection !== undefined) manifest.poolSelection = poolSelection;
    write(path.join(out, 'manifest.json'), manifest);
    const verified = loadPrepared(out);
    return { ...verified, manifest: path.join(out, 'manifest.json'), cards: catalogue.cards.length };
    } finally { lease.release(); }
}
module.exports = { prepare, loadPrepared, packageHashes, executionSnapshot, acquireBuildCache, selectPool, verifyPoolSelection };
