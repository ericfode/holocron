'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const file=path.join(__dirname,'../pipeline/selection-exhaust-probe-fixture.js'),isolated={exports:{}};
new Function('require','module','exports',fs.readFileSync(file,'utf8'))(name=>{if(name==='node:assert/strict')return assert;if(name==='./probe-fixture'||name==='../../../bots/omni/rs/state')return {};throw Error(name);},isolated,isolated.exports);
const {layout,exhaustedFirst}=isolated.exports;
test('physical layouts distinguish exhaustion from physical resource order',()=>{
 assert.deepEqual(layout(2),[true,false,true,false]);assert.deepEqual(layout(1),[true,false,true,true]);assert.deepEqual(layout(0),[true,true,true,true]);assert.deepEqual(layout(2,true),[false,true,false,true]);assert.deepEqual(exhaustedFirst(layout(2)),[true,true,true,false]);assert.deepEqual(exhaustedFirst(layout(2,true)),[true,true,false,true]);assert.deepEqual(exhaustedFirst(layout(0)),layout(0));assert.throws(()=>layout(3));
});
test('expectations preserve caller layout and already exhausted rows',()=>{const before=[true,false,true,false];exhaustedFirst(before);assert.deepEqual(before,[true,false,true,false]);});
test('pinned source and helpers establish paid nested player choice before comparisons',()=>{
 const engine=path.join(__dirname,'../../../forceteki/server/game'),read=p=>fs.readFileSync(path.join(engine,p),'utf8');
 const card=read('cards/06_SEC/units/RegulationsBureaucrat.ts'),select=read('gameSystems/SelectPlayerSystem.ts'),resolver=read('core/ability/abilityTargets/PlayerTargetResolver.ts'),ability=read('core/gameSteps/AbilityResolver.ts');
 assert.match(card,/cost: AbilityHelper.costs.exhaustSelf\(\)/);assert.match(card,/immediateEffects.selectPlayer/);assert.match(card,/exhaustResources\(\{ amount: 1 \}\)/);
 assert.match(select,/queueGenerateEventGameSteps/);assert.match(select,/new PlayerTargetResolver/);assert.match(select,/targetResolver.resolve\(context, targetResults\)/);
 assert.match(resolver,/const players = \[player, player.opponent\]/);assert.match(resolver,/if \(targetResults.canCancel\)/);
 assert.ok(ability.indexOf("this.payCosts(), 'payCosts'")<ability.indexOf("this.executeHandler(), 'executeHandler'"));
});
test('interaction donor source binds Raid count and last-ready Overwhelm boundary',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../../forceteki/server/game/cards/09_HMW/units/ChewbaccaResourcefulWookiee.ts'),'utf8');
 assert.match(source,/amount: context.player.exhaustedResourceCount/);assert.match(source,/context.player.readyResourceCount === 0/);assert.match(source,/gainKeyword\(KeywordName.Overwhelm\)/);
});
