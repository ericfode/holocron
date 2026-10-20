'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {Env}=require('../../../engine/env');
const {fixture}=require('../pipeline/cross-arena-probe-fixture');
const pool=require('../../../bots/omni/rs/pool.json');
const env=new Env();
const codes=['ASH_037','SOR_072','ASH_034'];
for(const code of codes){const raw=env.cardDataGetter.cardIds.map(id=>env.cardDataGetter.getCardSync(id)).find(c=>c.setId.set+'_'+String(c.setId.number).padStart(3,'0')===code);assert.ok(raw);pool.cards.push({...raw,setCode:code,keywordValues:code==='ASH_037'?{support:1}:code==='ASH_034'?{saboteur:1}:{},reason:'Engine-only fixture definition; native admission is separate.'});}
pool.provenance={scope:'strict baseline supplemented with engine-only Red Leader'};
const ground=pool.cards.find(c=>c.arena==='ground'&&!c.text&&!c.unique),space=pool.cards.find(c=>c.arena==='space'&&!c.text&&!c.unique),leader=pool.cards.find(c=>c.types.includes('leader'));
for(const sourceSeat of [1,2])for(const arena of ['ground','space'])for(const decline of [false,true])test(`paid Support ${sourceSeat} ${arena} decline=${decline}`,async()=>{
 const recipient=arena==='ground'?ground:space,defender=arena==='ground'?space:ground;
 const result=await fixture(env,pool,{name:`cross-${sourceSeat}-${arena}-${decline}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:recipient.setCode,defenders:[{code:defender.setCode}],expectedDefenderIndices:[0],expectedBase:true,decline,donors:{leader:leader.setCode}}},7100+sourceSeat);
 assert.equal(result.records.at(-1).type,'result');assert.ok(result.records.at(-1).winner);
});
for(const sourceSeat of [1,2])test(`printed base attack ${sourceSeat}`,async()=>{
const result=await fixture(env,pool,{name:`printed-base-${sourceSeat}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'printed',sourceArena:'space',recipientCode:ground.setCode,defenders:[{code:ground.setCode},{code:space.setCode}],expectedDefenderIndices:[0,1],expectedBase:true,baseTarget:true,donors:{leader:leader.setCode}}},7200+sourceSeat);assert.ok(result.records.at(-1).winner);
});
for(const sourceSeat of [1,2])test(`Support Saboteur bypasses both arena Sentinels ${sourceSeat}`,async()=>{
const saboteur=pool.cards.find(c=>c.arena==='ground'&&c.keywordValues?.saboteur),gs=pool.cards.find(c=>c.arena==='ground'&&c.keywordValues?.sentinel),ss=pool.cards.find(c=>c.arena==='space'&&c.keywordValues?.sentinel);assert.ok(saboteur&&gs&&ss);
const result=await fixture(env,pool,{name:`support-saboteur-${sourceSeat}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:saboteur.setCode,defenders:[{code:gs.setCode},{code:ss.setCode}],expectedDefenderIndices:[0,1],expectedBase:true,defenderIndex:1,donors:{leader:leader.setCode}}},7300+sourceSeat);assert.ok(result.records.at(-1).winner);
});

for(const sourceSeat of [1,2])for(const arena of ['ground','space'])test(`Entrenched only-cross pregrant excludes recipient ${sourceSeat} ${arena}`,async()=>{
 const recipient=arena==='ground'?ground:space,defender=arena==='ground'?space:ground;
 const result=await fixture(env,pool,{name:`entrenched-${sourceSeat}-${arena}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:recipient.setCode,recipientAttachments:[{code:'SOR_072'}],defenders:[{code:defender.setCode}],expectedDefenderIndices:[0],expectedBase:false,noEligibleSupport:true,donors:{leader:leader.setCode}}},7400+sourceSeat);
 assert.ok(result.witness.observations.some(o=>o.stage==='no-eligible-support-before-grant'));assert.ok(result.records.at(-1).winner);
});
for(const sourceSeat of [1,2])test(`admitted Wicket only-cross pregrant excludes recipient ${sourceSeat}`,async()=>{
const result=await fixture(env,pool,{name:`wicket-${sourceSeat}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:'ASH_034',defenders:[{code:space.setCode}],expectedDefenderIndices:[0],expectedBase:false,noEligibleSupport:true,donors:{leader:leader.setCode}}},7600+sourceSeat);assert.ok(result.witness.observations.some(o=>o.stage==='no-eligible-support-before-grant'));assert.ok(result.records.at(-1).winner);
});

for(const sourceSeat of [1,2])for(const arena of ['ground','space'])for(const multipleCancellations of [false,true])test(`residual Support actual cross attack seat${sourceSeat} ${arena} multiple=${multipleCancellations}`,async()=>{
const recipient=arena==='ground'?ground:space,defender=arena==='ground'?space:ground;
const result=await fixture(env,pool,{name:`residual-${sourceSeat}-${arena}-${multipleCancellations}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:recipient.setCode,defenders:[{code:defender.setCode}],expectedDefenderIndices:[0],expectedBase:true,cancelDefender:true,multipleCancellations,resourceCount:30,donors:{leader:leader.setCode}}},7700+sourceSeat);
assert.ok(result.records.at(-1).winner);assert.ok(result.witness.observations.some(o=>o.stage==='retained-cross-attack-cleanup'));if(multipleCancellations)assert.ok(result.witness.observations.some(o=>o.stage==='two-cancelled-grants-after-unique-departure'));
require('fs').writeFileSync(`/private/tmp/cross-v4-residual-${sourceSeat}-${arena}-${multipleCancellations}.json`,JSON.stringify(result));
});

for(const sourceSeat of [1,2])test(`cancelled Support survives natural fatigue terminal seat${sourceSeat}`,async()=>{
try {const result=await fixture(env,pool,{name:`fatigue-${sourceSeat}`,coverageObligationIds:[],probe:{family:'cross-arena',cardId:'ASH_037',sourceSeat,mode:'support',sourceArena:'space',recipientCode:ground.setCode,defenders:[{code:space.setCode}],expectedDefenderIndices:[0],expectedBase:true,cancelDefender:true,terminalFatigue:true,donors:{leader:leader.setCode}}},7800+sourceSeat);assert.ok(result.records.at(-1).winner);assert.ok(result.witness.observations.some(o=>o.stage==='natural-fatigue-terminal-retained-grant'));require('fs').writeFileSync(`/private/tmp/cross-v5-terminal-${sourceSeat}.json`,JSON.stringify(result));}
catch(e){require('fs').writeFileSync(`/private/tmp/cross-v5-terminal-failed-${sourceSeat}.json`,JSON.stringify({error:e.message,diagnostic:e.diagnostic}));throw e;}
});

// Prepared native pools intentionally contain raw printed metadata, with no
// legacy keywordValues enrichment. Exercise raw planner objects at that boundary.
test('all raw cross-arena plans execute against the exact prepared metadata pool', {skip: !process.env.CROSS_ARENA_PREPARED_POOL || !process.env.CROSS_ARENA_PLANS}, async()=>{
const fs=require('node:fs'),crypto=require('node:crypto'),prepared=JSON.parse(fs.readFileSync(process.env.CROSS_ARENA_PREPARED_POOL)),plans=JSON.parse(fs.readFileSync(process.env.CROSS_ARENA_PLANS));
assert.equal(plans.cases.length,46);assert.ok(prepared.cards.every(c=>!Object.hasOwn(c,'keywordValues')),'Exact plain prepared pool has no synthetic enrichment');
const poolBefore=JSON.stringify(prepared),plansBefore=JSON.stringify(plans),results=[];
for(const [i,scenario] of plans.cases.entries()){
assert.equal(scenario.probe.recipientCode,undefined,'Use unnormalized planner probe');
const result=await fixture(env,prepared,scenario,8900+i);assert.ok(result.records.at(-1).winner);results.push({case:scenario.id,winner:result.records.at(-1).winner});
if(process.env.CROSS_ARENA_RECORDINGS_DIR){fs.mkdirSync(process.env.CROSS_ARENA_RECORDINGS_DIR,{recursive:true});fs.writeFileSync(require('node:path').join(process.env.CROSS_ARENA_RECORDINGS_DIR,`${i}.json`),JSON.stringify(result));}
}
assert.equal(JSON.stringify(prepared),poolBefore,'Fixture must not enrich or mutate prepared pool');assert.equal(JSON.stringify(plans),plansBefore,'Fixture must not normalize input objects in place');
if(process.env.CROSS_ARENA_RECORDINGS_DIR)fs.writeFileSync(require('node:path').join(process.env.CROSS_ARENA_RECORDINGS_DIR,'receipt.json'),JSON.stringify({poolSha256:crypto.createHash('sha256').update(fs.readFileSync(process.env.CROSS_ARENA_PREPARED_POOL)).digest('hex'),plansSha256:crypto.createHash('sha256').update(fs.readFileSync(process.env.CROSS_ARENA_PLANS)).digest('hex'),results},null,2));
});
