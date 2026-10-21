'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const files=['lab/kessel-reference/pipeline/round-limit-probe-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','lab/kessel-reference/pipeline/terminal-completion.js','engine/env.js','engine/rng.js','engine/view.js','bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/unit-entry-state.js','bots/omni/rs/support-state.js','bots/omni/rs/round-limit-state.js','bots/omni/rs/pool.js','bots/players/index.js','bots/players/random.js'];
test('round dispatch preserves Blade and collective and inventories exporter dependencies',async()=>{
 const central=require('../pipeline/probe-fixture'),round=require('../pipeline/round-limit-probe-fixture');
 for(const f of files)assert.ok(round.dependencies.includes(f),f);
 for(const f of ['lab/kessel-reference/pipeline/round-limit-probe-fixture.js','bots/omni/rs/round-limit-state.js','kessel:cards/pipeline/round-limit-probes.js','lab/kessel-reference/pipeline/blade-base-damage-probe-fixture.js','lab/kessel-reference/pipeline/collective-trigger-probe-fixture.js'])assert.ok(central.dependencies.includes(f),f);
 const source=fs.readFileSync(path.join(root,'lab/kessel-reference/pipeline/probe-fixture.js'),'utf8');
 for(const family of ['round-limit','blade-base-damage','collective-trigger'])assert.ok(source.includes("family === '"+family+"'"),family);
 await assert.rejects(central.fixture({newGame(){throw Error('unexpected engine access');}},null,{probe:{family:'round-limit',cardId:'UNREVIEWED'}},1));
});
test('strict source inventory loads with explicit external Kessel and no sibling fallback',()=>{
 assert.ok(process.env.KESSEL_DIR,'Set explicit KESSEL_DIR for the integration inventory gate');
 assert.equal(fs.existsSync(path.resolve(root,'../kessel')),false,'isolated H has no sibling Kessel');
 const script=`const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');const root=${JSON.stringify(root)}; const {Env}=require(root+'/engine/env'); new Env(); const fixture=require(root+'/lab/kessel-reference/pipeline/round-limit-probe-fixture'); for(const p of Object.keys(require.cache).filter(p=>p.startsWith(root+'/')&&!p.includes('/node_modules/')&&!p.includes('/forceteki/'))){assert.ok(fixture.dependencies.includes(p.slice(root.length+1)),'missing loaded source '+p);} const identity=require(root+'/lab/kessel-reference/reference/generate').sourceIdentity();for(const f of fixture.dependencies){const p=f.startsWith('kessel:')?require('node:path').join(process.env.KESSEL_DIR,f.slice(7)):require('node:path').join(root,f);assert.equal(identity.sources[f],crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),f);} console.log(JSON.stringify({sourceCount:Object.keys(identity.sources).length,engineSourceSha256:identity.engineSourceSha256,engineBuildSha256:identity.engineBuildSha256,sources:identity.sources}));`;
 const output=execFileSync(process.execPath,['-e',script],{cwd:require('node:os').tmpdir(),env:{...process.env,KESSEL_DIR:path.resolve(process.env.KESSEL_DIR)},encoding:'utf8'});
 const receipt=JSON.parse(output);assert.ok(receipt.sourceCount>=20);assert.equal(receipt.sources['bots/omni/rs/round-limit-state.js'],crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'bots/omni/rs/round-limit-state.js'))).digest('hex'));
 if(process.env.ROUND_INTEGRATION_INVENTORY_RECEIPT)fs.writeFileSync(process.env.ROUND_INTEGRATION_INVENTORY_RECEIPT,JSON.stringify(receipt,null,2)+'\n');
});
test('standalone exporter and fixture modules load without Kessel environment or sibling',()=>{
 const env={...process.env};delete env.KESSEL_DIR;
 execFileSync(process.execPath,['-e',`const assert=require('node:assert/strict'),fs=require('node:fs');const root=${JSON.stringify(root)};assert.equal(fs.existsSync(require('node:path').resolve(root,'../kessel')),false);assert.equal(process.env.KESSEL_DIR,undefined);new (require(root+'/engine/env').Env)();assert.equal(typeof require(root+'/bots/omni/rs/round-limit-state').roundLimitState,'function');assert.equal(typeof require(root+'/lab/kessel-reference/pipeline/probe-fixture').fixture,'function');assert.equal(typeof require(root+'/lab/kessel-reference/pipeline/round-limit-probe-fixture').fixture,'function');`],{cwd:require('node:os').tmpdir(),env,stdio:'pipe'});
});
