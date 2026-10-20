'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fixture=require('../pipeline/unit-entry-probe-fixture');
const {unitEntryProjection}=require('../../../bots/omni/rs/unit-entry-state');
const {phaseStats}=require('../../../bots/omni/rs/state');
function card(id,{zone='discard',power=1,hp=0,token=false,owner='p1',controller=owner,type='unit'}={}) {
 const e={duration:'untilEndOfPhase',type:'modifyStats',getValue:()=>({power,hp})};
 return {id,uuid:id,internalName:token?'mandalorian':'outcast#mercenary-starship',zoneName:zone,owner:{id:owner},controller:{id:controller},isUnit:()=>type==='unit',isToken:()=>token,getOngoingEffects:()=>[e]};
}
const ref=(eg,c)=>({id:c.id,setCode:c.isToken()?'TOKEN_MANDALORIAN':'ASH_041',name:c.internalName});
const projection=cards=>unitEntryProjection({game:{allCards:cards},seatOf:x=>x},phaseStats,null,ref);
test('inactive grants retain physical descriptor and numeric allocation order',()=>{
 const a=card('c10',{zone:'outsideTheGame',token:true,owner:'p2',power:2}), b=card('c2',{power:2});
 assert.deepEqual(projection([a,b]),{unitEntryStateVersion:1,inactiveUnitEntryStats:[{card:ref(null,b),power:2,hp:0},{card:ref(null,a),power:2,hp:0}].map((r,i)=>({...r,card:{...r.card,owner:i?'p2':'p1',controller:i?'p2':'p1'}}))});
});
test('active arena phase stats stay in existing unit row, empty versioned inactive state remains explicit',()=>{assert.deepEqual(projection([card('c0',{zone:'spaceArena'})]),{unitEntryStateVersion:1,inactiveUnitEntryStats:[]});});
test('no fabricated dead-card history without actual attached phase effects',()=>{const c=card('c0');c.getOngoingEffects=()=>[];assert.equal(projection([c]).inactiveUnitEntryStats.length,0);});
test('inactive protocol rejects unsupported magnitude, hp, zone, type, identity and duplicate rows',()=>{
 for(const options of [{power:0},{power:-1},{power:65536},{hp:1},{zone:'hand'},{zone:'outsideTheGame'},{type:'upgrade'}])assert.throws(()=>projection([card('c0',options)]),/Unsupported|bounds/);
 assert.throws(()=>projection([card('c01')]),/identity/);assert.throws(()=>projection([card('c0'),card('c0')]),/Duplicate/);
});
test('aggregation is checked without saturation or partial output',()=>{const c=card('c1',{power:40000}),e=c.getOngoingEffects()[0];c.getOngoingEffects=()=>[e,e];assert.throws(()=>projection([c]),/bounds/);assert.deepEqual(projection([]).inactiveUnitEntryStats,[]);});
test('standard fixture selection excludes rejected-donor diagnostics',()=>{
 assert.equal(fixture.variants.length,14);assert.equal(fixture.diagnosticVariants.length,7);assert.ok(fixture.diagnosticVariants.includes('piloting-no-entry'));
 assert.ok(fixture.variants.every(v=>!fixture.donorCodes(v).some(x=>['SEC_105','JTL_121','ASH_060'].includes(x))));
 assert.deepEqual(fixture.donorCodes('multiple-entrants-next'),['SOR_014','TWI_237']);
 assert.deepEqual(fixture.donorCodes('source-departure'),['SOR_014','SOR_095','TWI_226']);
});
test('source-seat and lifecycle boundaries stay explicit, unsupported cases are not approximated',()=>{
 for(const sourceSeat of [1,2])assert.equal(fixture.definition({family:'unit-entry',cardId:'ASH_041',scenario:'self-entry',sourceSeat}).sourceSeat,sourceSeat);
 for(const scenario of ['rescue','control-change-no-entry','simultaneous-source-departure'])assert.throws(()=>fixture.definition({family:'unit-entry',cardId:'ASH_041',scenario,sourceSeat:1}),/Unsupported|bounds/);
 assert.throws(()=>fixture.definition({family:'unit-entry',cardId:'ASH_041',scenario:'self-entry',sourceSeat:0}));
});
test('central inventory can bind the transitive entry exporter',()=>{assert.ok(fixture.dependencies.includes('bots/omni/rs/unit-entry-state.js'));});

test('engine-only diagnostics require an explicit flag before constructing any engine state',async()=>{await assert.rejects(fixture.fixture(null,null,{name:'diagnostic',probe:{family:'unit-entry',cardId:'ASH_041',scenario:'piloting-no-entry',sourceSeat:1}},1),/engineOnlyDiagnostic/);});
