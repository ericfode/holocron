'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {Env}=require('../../../engine/env');
const {fullState}=require('../../../bots/omni/rs/state');
const {fixture}=require('../pipeline/chosen-hand-discard-probe-fixture');
const {kessel,kesselPath}=require('../kessel');
const catalogue=kessel('compiler/load-catalog').loadCatalog(),pool=JSON.parse(fs.readFileSync(kesselPath('compiler/generated/runtime-pool.json')));
// Exact raw engine metadata is an exporter diagnostic pool, not a prepared or
// runtime-admission receipt for these currently rejected focus definitions.
for(const code of ['HMW_041','ASH_226','SOR_095','JTL_075'])if(!pool.cards.some(c=>c.setCode===code)){const e=catalogue.cards.find(c=>c.setCode===code);assert.ok(e);pool.cards.push({...e.card,setCode:code});}
const env=new Env();
for(const sourceSeat of [1,2])for(const terminalAttackCleanup of [false,true])test(`actual Keeper attack modifiers reject pending export and clean up naturally seat${sourceSeat} terminal=${terminalAttackCleanup}`,async()=>{
    const scenario={id:'export-diagnostic',name:'export-diagnostic',coverageObligationIds:[],probe:{family:'chosen-hand-discard',profile:'keeper',cardId:'HMW_041',sourceArena:'ground',sourceSeat,resourceCount:30,targets:[{code:'SOR_095',owner:'opponent',arena:'ground'}],handCodes:['HMW_041','HMW_041'],discardIndexes:[0,1],targetIndex:terminalAttackCleanup?'base':0,baseDamage:5,triggerOrder:'restore-first',terminalAttackCleanup,enemyBaseDamage:terminalAttackCleanup?10:0}};
    let sawGrant=false;
    const result=await fixture(env,pool,scenario,19600+sourceSeat+(terminalAttackCleanup?10:0),{onLiveAttack({eg,source}){
        const effects=eg.game.ongoingEffectEngine.effects.filter(e=>e.duration==='untilEndOfAttack'&&e.source===source);
        assert.equal(effects.length,2);assert.deepEqual(effects.map(e=>e.type),['modifyStats','gainKeyword']);
        assert.deepEqual(effects[0].getValue(source),{power:15,hp:0});assert.deepEqual(effects[1].getValue(source),{keyword:'overwhelm'});
        const ability=effects[0].ongoingEffect.ability;
        assert.equal(effects[1].ongoingEffect.ability,ability);
        assert.equal(ability.constructor.name,'FrameworkCardAbilityStep');
        assert.equal(source.getTriggeredAbilities().filter(root=>root.properties?.ifYouDo?.immediateEffect===ability.immediateEffect).length,1,'Real printed continuation identity');
        assert.equal(source.getPower(),20);assert.ok(source.hasSomeKeyword('overwhelm'));
        assert.throws(()=>fullState(eg),/Unsupported Support projection: grant outside action window/,'No unrepresented pending grant is mislabeled as Support or phase state');
        sawGrant=true;
    }});
    assert.ok(sawGrant);const final=result.records.at(-1).state;assert.deepEqual(final.supportGrants,[]);
    const after=result.witness.observations.find(o=>o.stage===(terminalAttackCleanup?'terminal-attack-cleanup':'attack-grant-expired'));
    assert.ok(after);assert.deepEqual(after.state.supportGrants,[]);
    const unit=after.state.players['p'+sourceSeat].ground.find(c=>c.name==='keeper-of-skara-nal#awoken');assert.ok(unit);assert.equal(unit.power,5);assert.equal(unit.phaseStats,undefined);assert.equal(unit.phaseKeywords,undefined);
});
for(const sourceSeat of [1,2])test(`actual Qi live hand stat is derived rather than exported twice seat${sourceSeat}`,async()=>{
    const result=await fixture(env,pool,{id:'qira-export',name:'qira-export',coverageObligationIds:[],probe:{family:'chosen-hand-discard',profile:'qira',cardId:'ASH_226',sourceArena:'ground',sourceSeat,resourceCount:30,targets:[{code:'SOR_095',owner:'opponent',arena:'ground'}],handCodes:['JTL_075'],discardIndexes:[0],targetIndex:0}},19700+sourceSeat);
    const state=result.witness.observations.find(o=>o.stage==='resolved-discard-and-damage').state;
    const unit=state.players['p'+sourceSeat].ground.find(c=>c.name==='qira#master-of-teras-kasi');assert.ok(unit);assert.equal(unit.power,9);assert.equal(unit.phaseStats,undefined);assert.equal(unit.phaseKeywords,undefined);
});
