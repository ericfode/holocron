'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const text=fs.readFileSync(path.join(__dirname,'../pipeline/exhaust-resources-probe-fixture.js'),'utf8');
const isolated={exports:{}};
new Function('require','module','exports',text)((name)=>{
    if(name==='node:assert/strict')return assert;
    if(name==='./probe-fixture')return {};
    if(name==='../../../bots/omni/rs/state')return {};
    throw Error(name);
},isolated,isolated.exports);
const {expectedLayout}=isolated.exports;
test('source-derived physical order exhausts first ready row without moving identities',()=>{
    assert.deepEqual(expectedLayout([true,false,true,false],false),[true,true,true,false]);
    assert.deepEqual(expectedLayout([true,false,true,true],false),[true,true,true,true]);
    assert.deepEqual(expectedLayout([true,true,true,true],false),[true,true,true,true]);
});
test('decline preserves every row and expectation construction is immutable',()=>{
    const before=[true,false,true,false];assert.deepEqual(expectedLayout(before,true),before);
    assert.deepEqual(before,[true,false,true,false]);
});
test('pinned sources establish defaults, LKI target and physical order before oracle comparisons',()=>{
    const engine=path.join(__dirname,'../../../forceteki/server/game');
    const scout=fs.readFileSync(path.join(engine,'cards/08_ASH/units/MandalorianScout.ts'),'utf8');
    const ziro=fs.readFileSync(path.join(engine,'cards/03_TWI/units/ZiroTheHuttColorfulSchemer.ts'),'utf8');
    const player=fs.readFileSync(path.join(engine,'core/Player.ts'),'utf8');
    const target=fs.readFileSync(path.join(engine,'core/gameSystem/PlayerTargetSystem.ts'),'utf8');
    assert.match(scout,/addWhenDefeatedAbility/);assert.match(scout,/target: context.player, amount: 1/);
    assert.match(ziro,/controller: RelativePlayer.Opponent/);assert.match(ziro,/exhaustResources\(\{ amount: 1 \}\)/);
    assert.match(target,/\[context.player.opponent\]/);
    assert.match(player,/resources.slice\(0, count\).forEach\(\(resource\) => resource.exhaust\(\)\)/);
});
test('pinned selector separates legal selection from effect feasibility',()=>{
    const engine=path.join(__dirname,'../../../forceteki/server/game');
    const resolver=fs.readFileSync(path.join(engine,'core/ability/abilityTargets/CardTargetResolver.ts'),'utf8');
    const exhaust=fs.readFileSync(path.join(engine,'gameSystems/ExhaustSystem.ts'),'utf8');
    assert.match(resolver,/this.properties.mustChangeGameState/);
    assert.match(resolver,/GameStateChangeRequired.MustFullyOrPartiallyResolve/);
    assert.match(resolver,/if \(!effectiveTargetFound\)/);
    assert.match(exhaust,/mustChangeGameState !== GameStateChangeRequired.None/);
});
