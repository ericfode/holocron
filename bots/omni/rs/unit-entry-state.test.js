'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {unitEntryProjection}=require('./unit-entry-state');
function setup(stats,zone='discard'){
 const card={internalName:'fixture-unit',zoneName:zone,owner:{id:'p1'},controller:{id:'p2'},isUnit:()=>true,isToken:()=>false,getOngoingEffects:()=>[{type:'modifyStats',duration:'untilEndOfPhase'}]};
 const eg={game:{allCards:[card]},seatOf:id=>id};
 const ref=()=>({id:'c2',setCode:'ASH_041',name:'fixture-unit'});
 return {card,eg,ref,read:()=>stats};
}
test('markerless inactive-entry descriptor remains exact and does not mutate stats',()=>{
 const stats=Object.freeze({phaseStats:Object.freeze({power:2,hp:0})}),x=setup(stats);
 assert.deepEqual(unitEntryProjection(x.eg,x.read,null,x.ref),{unitEntryStateVersion:1,inactiveUnitEntryStats:[{card:{id:'c2',setCode:'ASH_041',name:'fixture-unit',owner:'p1',controller:'p2'},power:2,hp:0}]});
 assert.deepEqual(stats,{phaseStats:{power:2,hp:0}});
});
test('markerless and forged companions preserve all original keyword/loss/stat guards',()=>{
 for(const stats of [{phaseStats:{power:1,hp:0},phaseKeywords:{sentinel:1}},{phaseStats:{power:1,hp:0},phaseKeywords:{}},{phaseStats:{power:1,hp:0},phaseLostKeywords:['sentinel']},{phaseStats:{power:0,hp:0}},{phaseStats:{power:65536,hp:0}},{phaseStats:{power:1,hp:1}}]){
  const before=structuredClone(stats),x=setup(stats);
  assert.throws(()=>unitEntryProjection(x.eg,x.read,null,x.ref),/Unsupported inactive/);
  assert.throws(()=>unitEntryProjection(x.eg,x.read,null,x.ref,{inactivePhaseKeywordStateVersion:1,inactiveAllocatedCards:[]}),/Unsupported inactive/);
  assert.deepEqual(stats,before);
 }
 const x=setup({phaseStats:{power:1,hp:0}},'hand');assert.throws(()=>unitEntryProjection(x.eg,x.read,null,x.ref),/target zone/);
});
test('fresh actual source7 and Outcast-Snoke captures compose without stripping facts',{skip:!process.env.UNIT_ENTRY_CAPTURE_DRIVER},async()=>{
 const {runCapture}=require(process.env.UNIT_ENTRY_CAPTURE_DRIVER),path=require('node:path');
 assert.ok(process.env.UNIT_ENTRY_CAPTURE_OUT);assert.ok(process.env.UNIT_ENTRY_SOURCE_POOL);assert.ok(process.env.UNIT_ENTRY_SOURCE_CASES);assert.ok(process.env.UNIT_ENTRY_OLD_HELPER);
 const result=await runCapture({holocronRoot:path.resolve(__dirname,'../../..'),outDir:process.env.UNIT_ENTRY_CAPTURE_OUT,poolPath:process.env.UNIT_ENTRY_SOURCE_POOL,rawCasesPath:process.env.UNIT_ENTRY_SOURCE_CASES,oldUnitEntryPath:process.env.UNIT_ENTRY_OLD_HELPER});
 assert.equal(result.results.length,4);assert.ok(result.results.every(r=>r.winner&&r.captures>0));
 const composition=result.results.filter(r=>r.name.startsWith('outcast'));assert.equal(composition.length,2);assert.ok(composition.every(r=>r.paid===5&&r.entryProof&&r.rawStatsPreserved));
});
