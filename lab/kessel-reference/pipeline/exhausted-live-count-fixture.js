'use strict';
const assert=require('node:assert/strict');
const {constructProbeFixture}=require('./probe-fixture');
const {terminalCompletion}=require('./terminal-completion');
const {fullState,canonicalAction,expandActions}=require('../../../bots/omni/rs/state');
const scenarios=['paid-play7','count0-ready','count1-self','count2-ground','count2-space','mixed-arenas','enemy-negative','resource-negative','friendly-ground-target','enemy-ground-target','source-self-lethal','paid-sentinel-override','saboteur-no-override','saboteur-sentinel-override','paid-support-ready','depart-reentry','live-ready','live-exhaust','token-count','deployed-leader-count','undeployed-leader-negative'];
function validateProbe(p){
 assert.ok(p&&typeof p==='object'&&!Array.isArray(p),'Missing exhausted-live-count probe');
 assert.deepEqual(Object.keys(p).sort(),['family','sourceArena','cardId','owner','scenario','resourceCount','leaderCode','enemyLeaderCode','baseCode','enemyBaseCode'].sort(),'Unsupported exhausted-live-count construction fields');
 assert.equal(p.family,'exhaustedLiveCount');assert.equal(p.cardId,'ASH_035');assert.equal(p.sourceArena,'ground');
 assert.ok(scenarios.includes(p.scenario));assert.ok([0,1].includes(p.owner));assert.equal(p.resourceCount,24);
 for(const key of ['leaderCode','enemyLeaderCode'])assert.equal(p[key],'SOR_014');
 for(const key of ['baseCode','enemyBaseCode'])assert.equal(p[key],'SOR_023');
 return p;
}
async function fixture(env,pool,scenario,seed){
 const p=validateProbe(scenario.probe);const reversed=p.owner===1,owner=reversed?'opponent':'self',opponent=reversed?'self':'opponent',specs=[],roles={};
 const add=(name,code,extra={})=>{roles[name]=specs.length;specs.push({code,owner,arena:'ground',exhausted:false,...extra});};
 const paid=['paid-play7','resource-negative'].includes(p.scenario);
 if(!paid||reversed)add('train','ASH_035',paid?{zone:'hand'}:{});
 add('friendlyTarget','ASH_131');add('enemyTarget','ASH_131',{owner:opponent,exhausted:true});add('enemyAttacker',p.scenario.startsWith('saboteur-')?'ASH_173':'SOR_095',{owner:opponent});
 const withGround=['count2-ground','mixed-arenas','friendly-ground-target','enemy-ground-target','source-self-lethal','paid-sentinel-override','saboteur-no-override','saboteur-sentinel-override','depart-reentry','live-ready','live-exhaust'].includes(p.scenario),withSpace=['count2-space','mixed-arenas','source-self-lethal'].includes(p.scenario);
 if(withGround)add('ground','ASH_061',{exhausted:true});if(withSpace)add('space','JTL_069',{arena:'space',exhausted:true});
 if(p.scenario==='enemy-negative'){add('enemyGround','ASH_061',{owner:opponent,exhausted:true});add('enemySpace','JTL_069',{owner:opponent,arena:'space',exhausted:true});}
 if(p.scenario==='source-self-lethal')add('third','ASH_190',{exhausted:true});
 if(p.scenario.includes('sentinel-override'))add('sentinel','SEC_071',{zone:'hand'});
 if(p.scenario==='paid-support-ready'){add('support','ASH_033',{zone:'hand'});add('supportDefender','SOR_095',{owner:opponent,exhausted:true});}
 if(p.scenario==='depart-reentry'){add('bounceOther','TWI_226',{zone:'hand'});add('bounceTrain','TWI_226',{zone:'hand'});}
 if(['live-ready','live-exhaust'].includes(p.scenario))add('ready','LAW_043',{zone:'hand'});
 if(p.scenario==='token-count')add('droids','TWI_237',{zone:'hand'});
 const setup=await constructProbeFixture(env,pool,{...scenario,probe:{...p,sourceInPlay:false,initiative:owner,targets:specs}},seed);
 const {eg,rng,bot,targets}=setup,own=reversed?setup.enemy:setup.own,enemy=reversed?setup.own:setup.enemy,train=paid&&!reversed?setup.source:targets[roles.train],card=n=>targets[roles[n]],id=c=>eg.cardId(c.uuid),count=()=>own.getArenaUnits({condition:c=>c.exhausted}).length;
 const live=()=>({count:count(),ids:own.getArenaUnits({condition:c=>c.exhausted}).map(id),source:{id:id(train),zone:train.zoneName,exhausted:train.isInPlay()?train.exhausted:null,damage:train.isInPlay()?train.damage:null,sentinel:train.isInPlay()?train.hasSomeKeyword('sentinel'):false},ground:own.getArenaUnits({arena:'groundArena'}).map(id),space:own.getArenaUnits({arena:'spaceArena'}).map(id),enemyExhausted:enemy.getArenaUnits({condition:c=>c.exhausted}).map(id),exhaustedResources:own.resources.filter(c=>c.exhausted).length});
 const tasks=[];if(paid)tasks.push({kind:'play',card:train,expect:'paid-train'},{kind:'phase'});
 if(p.scenario==='count0-ready')tasks.push({kind:'enemy-attack',card:card('enemyAttacker'),target:train,expect:'initial-ready-target'});
 if(p.scenario==='token-count')tasks.push({kind:'play',card:card('droids'),expect:'token-created'});
 const leader=own.getAllDeckLeaders()[0];if(p.scenario==='deployed-leader-count')tasks.push({kind:'leader',card:leader,expect:'leader-deployed'},{kind:'attack',card:leader,target:enemy.base,expect:'leader-exhausted'});
 if(p.scenario==='undeployed-leader-negative')tasks.push({kind:'leader',card:leader,expect:'leader-action'});
 if(p.scenario==='paid-support-ready')tasks.push({kind:'play',card:card('support'),attacker:train,target:card('supportDefender'),damageTarget:card('friendlyTarget'),expect:'support-attack'});else tasks.push({kind:'attack',card:train,target:enemy.base,damageTarget:p.scenario==='source-self-lethal'?train:p.scenario==='friendly-ground-target'?card('friendlyTarget'):card('enemyTarget'),expect:'train-attack'});
 if(p.scenario.includes('sentinel-override'))tasks.push({kind:'play',card:card('sentinel'),target:train,expect:'sentinel-attached'});
 if(p.scenario==='depart-reentry')tasks.push({kind:'play',card:card('bounceOther'),target:card('ground'),expect:'friend-left'},{kind:'play',card:card('ground'),expect:'friend-reentered'},{kind:'play',card:card('bounceTrain'),target:train,expect:'train-left'},{kind:'play',card:train,expect:'train-reentered'});
 if(['live-ready','live-exhaust'].includes(p.scenario))tasks.push({kind:'play',card:card('ready'),target:card('ground'),expect:'friend-readied'});
 if(p.scenario==='live-exhaust')tasks.push({kind:'attack',card:card('ground'),target:enemy.base,expect:'friend-exhausted'});
 if(p.scenario!=='source-self-lethal'&&p.scenario!=='count0-ready')tasks.push({kind:'enemy-attack',card:card('enemyAttacker'),target:own.base,expect:'restriction-menu'});
 const witness={scope:'source-only actual engine, zero native/admission credit',construction:{paidTrain:paid,resourceCount:p.resourceCount,owner:p.owner,scenario:p.scenario},events:[],menus:[],windows:[],initial:live(),identities:{train:id(train),targets:targets.map(c=>({id:id(c),code:c.cardData.internalName,zone:c.zoneName}))}},records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['exhaustedLiveCount','exhaustedLiveCount'],decks:setup.decks,scenario:scenario.name,constructionParameters:p,fixtureConstruction:'Disclosed source/donor hand/arena/resource setup using real card objects. Paid train scenarios pay7 normally. Other source setups stage ready Train. Every subsequent scripted action is actual legal input; all mandatory effects and final games are completed.'}];
 let at=0,step=0,settled=false;
 const event=(name,e)=>{if(settled||e.isCancelledOrReplaced)return;witness.events.push({name,card:eg.game.allCards.includes(e.card)?id(e.card):null,source:eg.game.allCards.includes(e.context?.source)?id(e.context.source):null,amount:e.amount??null,damageDealt:e.damageDealt??null,type:e.type??null,player:e.player?eg.seatOf(e.player.id):null,live:live(),activeAttack:eg.game.currentAttack?{attacker:id(eg.game.currentAttack.attacker),targets:eg.game.currentAttack.getAllTargets().map(id)}:null});};
 for(const name of ['onCardPlayed','onCardDefeated','onCardLeavesPlay','onDamageDealt','onCardReadied','onCardExhausted','onUnitEntersPlay','onUpgradeAttached','onAttackEnd'])eg.game.on(name,e=>event(name,e));
 eg.game.on('onCardPlayed',e=>{if(settled)return;const t=tasks[at];if(e.card===t?.card){t.done=true;t.paid=t.beforeResources-own.resources.filter(c=>!c.exhausted).length;assert.equal(t.paid,e.card.cost+2*own.getPenaltyAspects(e.card.aspects).length,'Actual ordinary payment including all aspect penalties');}});
 eg.game.on('onAttackDeclared',e=>{if(settled)return;const t=tasks[at];if(e.attack.attacker===(t?.attacker??t?.card)){assert.deepEqual(e.attack.getAllTargets(),[t.target]);t.declared=true;if(e.attack.attacker===train){t.declaration=live();assert.ok(train.exhausted,'Train is exhausted before OnAttack');assert.equal(train.getFriendlyExhaustedUnitCount({player:own}),count(),'Pinned helper reads live CURRENT controller arena units');}}});
 function check(t){
  const after=live();if(t.expect==='paid-train'){assert.equal(t.paid,7);assert.equal(after.count,1);assert.equal(train.exhausted,true);assert.equal(after.exhaustedResources>=7,true);}
  if(t.expect==='train-attack'||t.expect==='support-attack'){
   assert.ok(t.declared);const expectedCount=({ 'count2-ground':2,'count2-space':2,'mixed-arenas':3,'friendly-ground-target':2,'enemy-ground-target':2,'source-self-lethal':4,'paid-sentinel-override':2,'saboteur-no-override':2,'saboteur-sentinel-override':2,'paid-support-ready':2,'depart-reentry':2,'live-ready':2,'live-exhaust':2,'token-count':3,'deployed-leader-count':2 })[p.scenario]??1;assert.equal(t.declaration.count,expectedCount,'Independent declared construction count includes source only after attack exhaustion');assert.ok(t.damagePrompt,'Actual mandatory target prompt observed');assert.equal(t.promptDamage,t.declaration.count*2,'Prompt independently reads live query after exhaustion');const damages=witness.events.filter(e=>e.name==='onDamageDealt'&&e.source===id(train)&&e.card===id(t.damageTarget)&&e.type!=='combat');assert.equal(damages.at(-1)?.amount,t.promptDamage,'Factory event.amount captures query independently of applied damage');assert.equal(eg.game.currentAttack,null,'Attack cleanup completes');
   if(p.scenario==='source-self-lethal'){assert.equal(t.promptDamage,8);assert.equal(train.zoneName,'discard');assert.equal(enemy.base.damage,t.beforeBase,'Invalidated attacker deals no combat damage');assert.equal(damages.at(-1).damageDealt,7,'Applied damage is clamped independently of captured amount8');}
   if(t.expect==='support-attack'){assert.equal(t.paid,9);assert.equal(t.promptDamage,4);assert.equal(card('supportDefender').zoneName,'discard');assert.equal(train.exhausted,false,'Copied real Thrawn attack-end trigger readies recipient');assert.equal(after.count,1,'Readied train immediately leaves live exhausted query');assert.equal(card('friendlyTarget').damage,4);}
  }
  if(t.expect==='sentinel-attached'){assert.equal(t.paid,5);assert.ok(train.upgrades.includes(t.card));assert.ok(train.hasSomeKeyword('sentinel'));assert.equal(count(),2);}
  if(t.expect==='friend-left'){assert.equal(card('ground').zoneName,'hand');assert.equal(count(),1);}
  if(t.expect==='friend-reentered'){assert.equal(card('ground').zoneName,'groundArena');assert.equal(card('ground').exhausted,true);assert.equal(count(),2);}
  if(t.expect==='train-left'){assert.equal(train.zoneName,'hand');assert.equal(count(),1);}
  if(t.expect==='train-reentered'){assert.equal(t.paid,7);assert.equal(train.damage,0);assert.equal(train.exhausted,true);assert.equal(count(),2);}
  if(t.expect==='friend-readied'){assert.equal(t.paid,9);assert.equal(count(),1);assert.equal(card('ground').exhausted,false);assert.ok(card('ground').upgrades.some(c=>c.cardData.internalName==='shield'));}
  if(t.expect==='friend-exhausted'){assert.equal(count(),2);assert.equal(card('ground').exhausted,true);}
  if(t.expect==='token-created'){assert.equal(t.paid,4);assert.equal(count(),2);assert.equal(own.getArenaUnits().filter(c=>c.cardData.internalName==='battle-droid'&&c.exhausted).length,2);}
  if(t.expect==='leader-deployed'){assert.equal(leader.zoneName,'groundArena');assert.equal(leader.exhausted,false);assert.equal(count(),0);}
  if(t.expect==='leader-exhausted'){assert.equal(leader.exhausted,true);assert.equal(count(),1);}
  if(t.expect==='leader-action'){assert.equal(leader.zoneName,'base');assert.equal(leader.exhausted,true);assert.equal(count(),0);}
  witness.windows.push({stage:t.expect,paid:t.paid??null,before:t.before,after,promptDamage:t.promptDamage??null,state:fullState(eg)});
 }
 const completion=terminalCompletion(eg,5000);try{while(true){const pid=completion.nextActor(step);if(!pid)break;const actions=expandActions(eg,eg.legalActions(pid)),window=eg.isActionWindow(pid),prompt=eg.player(pid).currentPrompt();let t=tasks[at],chosen;
  if(window&&!settled&&t.kind==='phase'){t.round??=eg.round;if(eg.round>t.round){at++;t=tasks[at];assert.equal(count(),0,'Natural regroup readies source and units');}}
  if(window&&!settled&&(t.done||t.declared||t.kind==='leader'&&(t.expect==='leader-deployed'?leader.zoneName==='groundArena':leader.exhausted))){check(t);at++;t=tasks[at];if(!t)settled=true;}
  if(window){records.push({type:'state',step,actor:eg.seatOf(pid),state:fullState(eg,pid)});if(!settled){const actor=t.kind==='enemy-attack'?enemy:own;if(t.kind!=='phase'&&pid===actor.id){chosen=actions.find(a=>a.cardUuid===t.card.uuid);if(chosen){t.before=live();t.beforeResources=own.resources.filter(c=>!c.exhausted).length;t.beforeBase=enemy.base.damage;}}chosen??=actions.find(a=>a.arg==='pass');}}
  if(!window&&!settled){witness.menus.push({stage:t.expect??t.kind,title:prompt.menuTitle,promptTitle:prompt.promptTitle??null,actor:eg.seatOf(pid),actions:actions.map(a=>canonicalAction(eg,a)),live:live()});
   if(t.kind==='leader'){chosen=actions.find(a=>new RegExp(t.expect==='leader-deployed'?'Deploy':'Deal 1 damage','i').test(a.label??''));}
   if(/Choose a ground unit to deal (\d+) damage to/.test(prompt.menuTitle??'')){const n=Number(prompt.menuTitle.match(/deal (\d+) damage/)[1]);t.damagePrompt=true;t.promptDamage=n;assert.equal(n,count()*2);assert.equal(train.getAttackDamage({player:own}),n);const expected=[...own.getArenaUnits({arena:'groundArena'}),...enemy.getArenaUnits({arena:'groundArena'})].map(id);assert.deepEqual(actions.filter(a=>a.kind==='card').map(a=>eg.cardId(a.cardUuid)),expected,'Exact ground target domain includes both owners and excludes bases/space');chosen=actions.find(a=>a.cardUuid===t.damageTarget.uuid);}
   if(prompt.menuTitle==='Choose a target for attack'&&t.kind==='enemy-attack'){
    const saboteur=t.card.hasSomeKeyword('saboteur'),ground=own.getArenaUnits({arena:'groundArena'}),sentinels=ground.filter(c=>c.hasSomeKeyword('sentinel'));let expected=ground.filter(c=>c!==train||count()<2||c.hasSomeKeyword('sentinel'));if(!saboteur&&sentinels.length)expected=expected.filter(c=>c.hasSomeKeyword('sentinel'));else expected.push(own.base);assert.deepEqual(actions.filter(a=>a.kind==='card').map(a=>eg.cardId(a.cardUuid)),expected.map(id),'Exact live restriction/Sentinel/Saboteur target menu');witness.windows.push({stage:'enemy-target-menu',live:live(),expected:expected.map(id),actions:actions.map(a=>canonicalAction(eg,a))});
    if(p.scenario==='count0-ready'){assert.equal(count(),0);assert.ok(expected.includes(train));}if(p.scenario.startsWith('saboteur-'))assert.ok(saboteur);if(p.scenario==='saboteur-no-override')assert.ok(!expected.includes(train),'Saboteur does not bypass BeAttacked restriction');if(p.scenario.includes('sentinel-override')){assert.ok(expected.includes(train));t.target=train;}if(!expected.includes(t.target))t.target=expected[0];
   }
   if(t.attacker)chosen??=actions.find(a=>a.cardUuid===t.attacker.uuid);
   if(t.target)chosen??=actions.find(a=>a.cardUuid===t.target.uuid);
   chosen??=actions.find(a=>a.label==='Pass');chosen??=actions.find(a=>a.arg==='done');chosen??=actions.length===1?actions[0]:undefined;
  }
  if(settled&&!window&&/^Attack with another unit\./.test(prompt.menuTitle??''))chosen=actions.find(a=>a.arg==='passAbility');
  chosen??=bot.choose({game:eg,pid,actions,rng});assert.ok(chosen);records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,actionWindow:window},actions:actions.map(a=>canonicalAction(eg,a)),chosen:canonicalAction(eg,chosen).key,events:[]});eg.apply(pid,chosen,rng);step++;
 }assert.ok(settled,'All intended tasks complete');assert.ok(eg.over);witness.terminalCompletion=completion.assertComplete();records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});witness.coverageObligationIds=[...(scenario.coverageObligationIds??[])];return {records,witness};
 }catch(e){e.diagnostic={records,witness,task:{kind:tasks[at]?.kind,expect:tasks[at]?.expect}};throw e;}finally{bot.close?.();}
}
module.exports={fixture,scenarios,validateProbe,dependencies:['lab/kessel-reference/pipeline/exhausted-live-count-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','lab/kessel-reference/pipeline/terminal-completion.js','engine/env.js','bots/omni/rs/state.js']};
