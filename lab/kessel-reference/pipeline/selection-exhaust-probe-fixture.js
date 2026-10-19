'use strict';
const assert=require('node:assert/strict');
const {constructProbeFixture}=require('./probe-fixture');
const {fullState,canonicalAction,expandActions}=require('../../../bots/omni/rs/state');
// Source: SelectPlayerSystem constructs its resolver during effect execution,
// after exhaustSelf payment. PlayerTargetResolver offers both players even when
// the selected ExhaustResources event cannot change their zero-ready state.
function layout(ready,reverse=false){assert.ok([0,1,2].includes(ready));const rows=[true,true,true,true];for(const i of(reverse?[0,2]:[1,3]).slice(0,ready))rows[i]=false;return rows;}
function exhaustedFirst(rows){const after=[...rows],i=after.indexOf(false);if(i>=0)after[i]=true;return after;}
async function fixture(env,pool,scenario,seed){
 const p=scenario.probe;assert.equal(p.family,'selection-exhaust');
 const auraRows=p.interactionCode?[{code:p.interactionCode,owner:'self',arena:'ground',exhausted:true},{code:p.interactionCode,owner:'opponent',arena:'ground',exhausted:true}]:[];
 const construction={...scenario,probe:{...p,sourceInPlay:true,sourceArena:p.sourceArena,targets:[...auraRows,...(p.owner?[{code:p.cardId,owner:'opponent',arena:p.sourceArena,exhausted:!p.sourceReady}]:[])]}};
 const setup=await constructProbeFixture(env,pool,construction,seed),{eg,rng,bot,deck}=setup;
 const own=p.owner?setup.enemy:setup.own,enemy=p.owner?setup.own:setup.enemy,source=p.owner?setup.targets.at(-1):setup.source;
 if(p.owner)setup.source.moveTo('deckBottom');source.exhausted=!p.sourceReady;
 const players=[own,enemy],resources=player=>player.getCardsInZone('resource'),id=c=>eg.cardId(c.uuid);
 const initialLayouts=[layout(p.ownReady,p.scenario==='reverse-order'),layout(p.enemyReady,p.scenario==='reverse-order')];
 for(let j=0;j<2;j++){const rows=resources(players[j]);for(const c of rows.slice(4))c.moveTo('deckBottom');resources(players[j]).forEach((c,i)=>c.exhausted=initialLayouts[j][i]);assert.equal(resources(players[j]).length,4);}
 const chosenIndex=p.chosenPlayer==='self'?0:1;
 const combatUnits=setup.targets.filter(c=>c!==source),attacker=combatUnits.find(c=>c.controller===players[chosenIndex]),defender=combatUnits.find(c=>c.controller!==players[chosenIndex]);
 if(p.interactionCode){assert.equal(defender.getHp(),5);assert.equal(attacker.getPower(),0);attacker.exhausted=false;defender.damage=4;}
 const baseDamageBefore=players.map(player=>player.base.damage);
 eg.game.resolveGameState(true);eg.game.continue();
 const aura=setup.targets.filter(c=>c!==source),keywordState=c=>({id:id(c),raid:c.getKeywordsWithNumericValues('raid').reduce((n,k)=>n+k.value,0),overwhelm:c.hasSomeKeyword('overwhelm'),damage:c.damage,exhausted:c.exhausted});
 const snapshot=()=>({source:{id:id(source),exhausted:source.exhausted,zone:source.zoneName,controller:eg.seatOf(source.controller.id)},resources:players.map(player=>resources(player).map(c=>({id:id(c),exhausted:c.exhausted}))),aura:aura.map(keywordState)}),initial=snapshot();
 const cancelled=p.scenario==='cancel',disabled=!p.sourceReady;
 const expectedLayouts=initialLayouts.map((rows,i)=>!cancelled&&!disabled&&i===chosenIndex?exhaustedFirst(rows):[...rows]);
 const witness={coverageObligationIds:[],initial,expectedLayouts,observations:[],sourceClicked:false,abilityChosen:false,playerChosen:false,cancelled:false,events:[]};
 const records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['selection-exhaust-probe','selection-exhaust-probe'],decks:[deck,deck],scenario:scenario.name,constructionParameters:p,fixtureConstruction:'At natural first action window stage actual Bureaucrat and four existing physical resources per player in disclosed exhaustion order. Ability selection, self-exhaust payment, nested player choice or prepayment cancellation, and full terminal game are normal recorded inputs. In live-resource-keywords cases stage chosen Chewbacca ready and opposing Chewbacca with four damage, then record the actual Raid/Overwhelm attack and excess base damage.'}];
 let step=0,settled=false,focusChecked=false,combatStarted=false,combatEnded=false;
 witness.combat={declared:false,preDamage:false,defeated:false,damage:[]};
 eg.game.on('onAttackDeclared',e=>{if(combatStarted&&!settled&&e.attack.attacker===attacker){assert.ok(e.attack.getAllTargets().includes(defender));witness.combat.declared=true;}});
 eg.game.on('onAttackDamageResolved:preResolve',e=>{if(combatStarted&&!settled&&e.attack.attacker===attacker){assert.equal(attacker.getPower(),4,'Actual attack power includes live Raid4');assert.equal(keywordState(attacker).overwhelm,true);assert.deepEqual(keywordState(defender),initial.aura.find(c=>c.id===id(defender)),'Unchosen keyword state unchanged before combat');players.forEach((player,i)=>assert.deepEqual(resources(player).map(c=>c.exhausted),expectedLayouts[i],'No extra resource change before combat'));witness.combat.preDamage=true;witness.observations.push({stage:'live-raid-overwhelm-before-combat',attackPower:attacker.getPower(),snapshot:snapshot()});}});
 eg.game.on('onCardDefeated',e=>{if(combatStarted&&!settled&&e.card===defender)witness.combat.defeated=true;});
 eg.game.on('onDamageDealt',e=>{if(combatStarted&&!settled)witness.combat.damage.push({card:id(e.card),amount:e.damageDealt??0,requested:e.amount??null});});
 eg.game.on('onAttackEnd',e=>{if(combatStarted&&!settled&&e.attack.attacker===attacker)combatEnded=true;});
 eg.game.on('onExhaustResources',e=>{if(!settled&&e.context?.source===source&&!e.isCancelledOrReplaced)witness.events.push({player:eg.seatOf(e.player.id),amount:e.amount,sourceExhausted:source.exhausted});});
 function observe(stage,pid,actions){witness.observations.push({stage,actor:eg.seatOf(pid),snapshot:snapshot(),actions:actions.map(a=>canonicalAction(eg,a))});}
 function check(){
  assert.equal(source.exhausted,disabled||!cancelled,'Source exhaustSelf remains paid after nested choice; prepayment cancel preserves readiness');
  players.forEach((player,i)=>{assert.deepEqual(resources(player).map(id),initial.resources[i].map(c=>c.id),'Physical resource order unchanged');assert.deepEqual(resources(player).map(c=>c.exhausted),expectedLayouts[i],'Exactly first ready resource of chosen player exhausts; other rows unchanged');});
  assert.equal(witness.playerChosen,!disabled&&!cancelled);assert.equal(witness.cancelled,cancelled);
  if(!disabled&&!cancelled&&initialLayouts[chosenIndex].includes(false)){assert.equal(witness.events.length,1,'Positive chosen-player effect event occurs');assert.equal(witness.events[0].player,eg.seatOf(players[chosenIndex].id));assert.equal(witness.events[0].amount,1);assert.equal(witness.events[0].sourceExhausted,true);}
  else assert.equal(witness.events.length,0,'No resource event for ineffective selection, disabled source or cancelled action');
  if(p.interactionCode){for(const c of aura){const playerIndex=players.indexOf(c.controller),before=initial.aura.find(row=>row.id===id(c)),after=keywordState(c),changed=playerIndex===chosenIndex;assert.equal(before.raid,3,'Raid initially counts three exhausted resources');assert.equal(before.overwhelm,false);assert.equal(after.raid,before.raid+(changed?1:0),'Selected resource exhaustion updates live Raid only for chosen controller');assert.equal(after.overwhelm,changed,'Exhausting last ready resource grants live Overwhelm only for chosen controller');}witness.observations.push({stage:'live-resource-keywords',snapshot:snapshot()});}
  focusChecked=true;settled=!p.interactionCode;
 }
 try{while(!eg.over&&step<5000){
  const pid=eg.ids.find(pid=>eg.legalActions(pid).length);assert.ok(pid);const actions=expandActions(eg,eg.legalActions(pid)),window=eg.isActionWindow(pid),prompt=eg.player(pid).currentPrompt();let chosen;
  if(window){records.push({type:'state',step,state:fullState(eg,pid)});
   if(!settled&&!focusChecked&&(witness.playerChosen||witness.cancelled)){observe('focused-resolution',pid,actions);check();}
   if(!settled&&pid===own.id&&!witness.sourceClicked){const click=actions.find(a=>a.cardUuid===source.uuid);observe('initial-legality',pid,actions);assert.equal(!!click,!disabled,'Initial action remains available even when both players have no ready resources');if(disabled){check();observe('disabled-source-observed',pid,actions);}else {chosen=click;witness.sourceClicked=true;}}
   if(!settled&&focusChecked&&p.interactionCode){
    if(combatEnded){assert.equal(source.exhausted,true,'Source exhaustSelf remains paid through actual combat');assert.ok(witness.combat.declared&&witness.combat.preDamage&&witness.combat.defeated,'Actual focused combat declared and resolved');assert.equal(defender.zoneName,'discard');assert.equal(players[1-chosenIndex].base.damage,baseDamageBefore[1-chosenIndex]+3,'Actual Overwhelm deals three excess damage to opposing base');assert.equal(players[chosenIndex].base.damage,baseDamageBefore[chosenIndex]);assert.ok(witness.combat.damage.some(e=>e.card===id(players[1-chosenIndex].base)&&e.amount===3),'Positive actual excess damage event');witness.observations.push({stage:'live-raid-overwhelm-combat-completed',state:fullState(eg)});settled=true;}
    else if(!combatStarted&&pid===players[chosenIndex].id){chosen=actions.find(a=>a.cardUuid===attacker.uuid);assert.ok(chosen,'Chosen player Chewbacca actual attack offered');combatStarted=true;}
   }
   if(!settled)chosen??=actions.find(a=>a.arg==='pass');
  }else if(!settled&&focusChecked&&p.interactionCode){
   assert.equal(pid,players[chosenIndex].id);chosen=actions.find(a=>a.cardUuid===defender.uuid);assert.ok(chosen,'Actual damaged opposing Chewbacca selected as combat target');
  }else if(!settled&&witness.sourceClicked){
   assert.equal(pid,own.id,'Source controller makes both choices');
   if(!witness.abilityChosen&&!witness.cancelled){
    assert.equal(prompt.menuTitle,'Choose an ability:');assert.deepEqual(actions.map(a=>({label:a.label,arg:a.arg})),[{label:'Exhaust a resource',arg:0},{label:'Attack',arg:1},{label:'Cancel',arg:2}]);assert.equal(source.exhausted,false);observe('prepayment-ability-menu',pid,actions);
    chosen=actions.find(a=>a.label===(cancelled?'Cancel':'Exhaust a resource'));if(cancelled)witness.cancelled=true;else witness.abilityChosen=true;
   }else if(!witness.playerChosen){
    assert.equal(prompt.menuTitle,"Choose a player to target for ability 'Exhaust a resource'");assert.deepEqual(actions.map(a=>({label:a.label,arg:a.arg})),[{label:'You',arg:0},{label:'Opponent',arg:1}],'Exact nested menu includes ineffective player; no postpayment Cancel');assert.equal(source.exhausted,true,'Self-exhaust cost paid before nested selector');
    players.forEach((player,i)=>assert.deepEqual(resources(player).map(c=>({id:id(c),exhausted:c.exhausted})),initial.resources[i],'Player choice has not exhausted resources yet'));observe('paid-source-player-menu',pid,actions);
    chosen=actions.find(a=>a.label===(chosenIndex===0?'You':'Opponent'));witness.playerChosen=true;
   }else assert.fail('Unexpected confirmation after nested player choice');
  }
  chosen??=bot.choose({game:eg,pid,actions,rng});assert.ok(chosen);records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,selected:(eg.player(pid).promptState.selectedCards??[]).map(id),actionWindow:window},actions:actions.map(a=>canonicalAction(eg,a)),chosen:canonicalAction(eg,chosen).key,events:[]});eg.apply(pid,chosen,rng);step++;
 }
 assert.ok(settled,'Focused ability assertions executed');assert.ok(eg.over,'Recorded game finishes');records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});witness.coverageObligationIds=[...scenario.coverageObligationIds];return{records,witness};
 }finally{bot.close?.();}
}
module.exports={fixture,layout,exhaustedFirst,dependencies:['kessel:cards/pipeline/selection-exhaust-probes.js','lab/kessel-reference/pipeline/selection-exhaust-probe-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','engine/env.js','bots/omni/rs/state.js','bots/players/index.js']};
