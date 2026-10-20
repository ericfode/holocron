'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {Env}=require('../../../engine/env'),{fixture}=require('../pipeline/arena-defeat-attack-probe-fixture');
const env=new Env(),pool=structuredClone(require('../../../bots/omni/rs/pool.json'));
const donors={leader:'SEC_005',ground:'ASH_061',space:'JTL_069',deathDraw:'JTL_063',deathBase:'LAW_189',spaceSaboteur:'ASH_141',shield:'TOKEN_SHIELD',experience:'TOKEN_EXPERIENCE',ordinaryUpgrade:'IC27_052',defense:'TS26_024',phantom:'SHD_187'};
const all=env.cardDataGetter.cardIds.map(id=>env.cardDataGetter.getCardSync(id));
for(const code of ['ASH_083',...Object.values(donors)])if(!pool.cards.some(c=>c.setCode===code)){
 const raw=all.find(c=>code==='TOKEN_EXPERIENCE'?c.internalName==='experience':code==='TOKEN_SHIELD'?c.internalName==='shield':(c.setCodes??[c.setId]).some(s=>s.set+'_'+String(s.number).padStart(3,'0')===code));assert.ok(raw,code);pool.cards.push({...raw,setCode:code});
}
const scenarios=['mixed-global-order','source-only','space-defender-removed','attachments','sentinel-domain','saboteur-bypass','death-trigger-order','terminal-base','own-copy-included','enemy-copy-included','on-defense-capture','on-defense-terminal'];
for(const sourceSeat of [1,2])for(const scenario of scenarios)test(`paid Summa seat${sourceSeat} ${scenario}`,async()=>{
 const entry={id:`auto/ASH_083/${sourceSeat}-${scenario}`,name:`summa-${sourceSeat}-${scenario}`,coverageObligationIds:[],probe:{family:'arena-defeat-attack',cardId:'ASH_083',sourceSeat,scenario,donors}};
 try{const r=await fixture(env,pool,entry,21000+sourceSeat*100+scenarios.indexOf(scenario));assert.ok(r.records.at(-1).winner);if(process.env.SUMMA_RECORDINGS_DIR){fs.mkdirSync(process.env.SUMMA_RECORDINGS_DIR,{recursive:true});fs.writeFileSync(`${process.env.SUMMA_RECORDINGS_DIR}/${sourceSeat}-${scenario}.json`,JSON.stringify(r));}}
 catch(e){fs.writeFileSync(`/private/tmp/summa-failed-${sourceSeat}-${scenario}.json`,JSON.stringify({error:e.message,stack:e.stack,diagnostic:e.diagnostic}));throw e;}
});
for(const sourceSeat of [1,2])test(`engine-only Phantom replacement diagnostic seat${sourceSeat}`,async()=>{
 const r=await fixture(env,pool,{id:`diagnostic/ASH_083/phantom-${sourceSeat}`,name:`engine-only-phantom-${sourceSeat}`,coverageObligationIds:[],probe:{family:'arena-defeat-attack',cardId:'ASH_083',sourceSeat,scenario:'phantom-diagnostic',donors}},22000+sourceSeat);assert.ok(r.records.at(-1).winner);
 if(process.env.SUMMA_RECORDINGS_DIR)fs.writeFileSync(`${process.env.SUMMA_RECORDINGS_DIR}/engine-only-phantom-${sourceSeat}.json`,JSON.stringify(r));
});
test('raw Summa plans execute against exact plain engine-only source-oracle pool',{skip:!process.env.SUMMA_PREPARED_POOL||!process.env.SUMMA_PLANS},async()=>{
const {loadPool}=require('../../../bots/omni/rs/pool'),crypto=require('node:crypto'),prepared=loadPool(process.env.SUMMA_PREPARED_POOL),plans=JSON.parse(fs.readFileSync(process.env.SUMMA_PLANS));
assert.equal(plans.cases.length,24);assert.ok(!prepared.cards.some(c=>c.setCode===donors.phantom),'Rejected Phantom stays outside native pool');assert.ok(prepared.cards.every(c=>!Object.hasOwn(c,'keywordValues')),'Prepared pool stays raw');
const before=JSON.stringify(prepared),planBefore=JSON.stringify(plans),results=[];
for(const [i,entry]of plans.cases.entries()){
 const result=await fixture(env,prepared,entry,23000+i);assert.equal(result.records[0].pool.sha256,prepared.provenance.sha256,'Normal loader binds pool before serialization');assert.ok(result.records.at(-1).winner);results.push({case:entry.id,winner:result.records.at(-1).winner});
 if(process.env.SUMMA_RECORDINGS_DIR)fs.writeFileSync(`${process.env.SUMMA_RECORDINGS_DIR}/raw-${i}.json`,JSON.stringify(result));
}
assert.equal(JSON.stringify(prepared),before);assert.equal(JSON.stringify(plans),planBefore);
if(process.env.SUMMA_RECORDINGS_DIR)fs.writeFileSync(`${process.env.SUMMA_RECORDINGS_DIR}/raw-receipt.json`,JSON.stringify({poolSha256:prepared.provenance.sha256,plansSha256:crypto.createHash('sha256').update(fs.readFileSync(process.env.SUMMA_PLANS)).digest('hex'),results},null,2));
});
