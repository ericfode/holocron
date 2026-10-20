'use strict';
const { terminalCompletion } = require('./terminal-completion');
const assert=require('node:assert/strict');
const {constructProbeFixture}=require('./probe-fixture');
const {fullState,canonicalAction,expandActions}=require('../../../bots/omni/rs/state');
function observe(c,eg){return {id:eg.cardId(c.uuid),zone:c.zoneName,damage:c.isUnit?.()&&c.isInPlay()?c.damage:null};}
function construction(p){
 const d=p.donors,targets=[],add=(code,owner,extra={})=>{const i=targets.length;targets.push({code,owner,arena:code===d.ground?'ground':'space',exhausted:true,...extra});return i;},r={};
 const space=(owner,extra)=>add(d.space,owner,extra),ground=owner=>add(d.ground,owner);
 if(p.scenario==='mixed-global-order'){space('self');space('opponent');ground('opponent');space('opponent');space('self');ground('self');}
 if(p.scenario==='space-defender-removed')r.defender=space('opponent');
 if(p.scenario==='attachments'){
  const attachments=[{code:d.shield,token:'shield'},{code:d.experience,token:'experience'},{code:d.ordinaryUpgrade}];space('opponent',{attachments});space('self',{attachments});add(d.ground,'self',{arena:'ground',attachments});
 }
 if(['sentinel-domain','saboteur-bypass'].includes(p.scenario)){r.prelude=add(p.scenario==='saboteur-bypass'?d.spaceSaboteur:d.space,'opponent',{exhausted:false});space('opponent');space('self');}
 if(p.scenario==='death-trigger-order'){add(d.deathDraw,'self');add(d.deathBase,'opponent');add(d.deathDraw,'opponent');add(d.deathBase,'self');}
 if(p.scenario==='terminal-base'){add(d.deathBase,'opponent');add(d.deathDraw,'self');add(d.deathBase,'self');}
 if(p.scenario==='own-copy-included')add(p.cardId,'self');
 if(p.scenario==='enemy-copy-included')r.defender=add(p.cardId,'opponent');
 if(['on-defense-capture','on-defense-terminal'].includes(p.scenario))r.defender=add(d.defense,'opponent');
 if(p.scenario==='phantom-diagnostic'){add(d.phantom,'self');add(d.phantom,'opponent');space('self');space('opponent');ground('opponent');}
 return {targets,roles:r};
}
async function fixture(env,pool,scenario,seed){
 const p=scenario.probe;assert.equal(p.family,'arena-defeat-attack');const reverse=p.sourceSeat===2,{targets:specs,roles}=construction(p),relative=o=>reverse?o==='self'?'opponent':'self':o;
 const staged=specs.map(t=>({...t,owner:relative(t.owner),attachments:t.attachments?.map(a=>({...a,owner:relative(t.owner)}))}));
 let handCopy;if(reverse){handCopy=staged.length;staged.push({code:p.cardId,owner:'opponent',zone:'hand'});}
 const setup=await constructProbeFixture(env,pool,{...scenario,probe:{...p,sourceArena:'space',sourceInPlay:false,leaderCode:p.donors.leader,initiative:relative('self'),resourceCount:30,targets:staged}},seed);
 const {eg,rng,bot,targets}=setup,own=reverse?setup.enemy:setup.own,enemy=reverse?setup.own:setup.enemy,source=reverse?targets[handCopy]:setup.source,id=c=>eg.cardId(c.uuid),cards=targets.slice(0,specs.length);
 if(['terminal-base','on-defense-terminal'].includes(p.scenario)){const victim=p.scenario==='terminal-base'?own:enemy;victim.base.damage=victim.base.cardData.hp-1;eg.game.resolveGameState(true);eg.game.continue();}
 const tasks=[{stage:'play',card:source,player:own}];
 if(roles.prelude!=null)tasks.push({stage:'prelude',card:cards[roles.prelude],player:enemy,target:p.scenario==='sentinel-domain'?source:own.base});
 tasks.push({stage:'phase'});if(p.scenario==='source-only')tasks.push({stage:'cancel',card:source,player:own});
 tasks.push({stage:'attack',card:source,player:own,target:roles.defender==null?enemy.base:cards[roles.defender]});
 const witness={coverageObligationIds:[],events:[],menus:[],observations:[],initial:{source:observe(source,eg),targets:cards.map(c=>observe(c,eg))}},records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['arena-defeat-attack','arena-defeat-attack'],decks:setup.decks,scenario:scenario.name,constructionParameters:p,fixtureConstruction:'At first natural action window disclose real target cards, attachment identities and optional base29 boundary. Focus source is paid normally, readied through natural regroup, then attacks through actual legal inputs. All subsequent effects and terminal continuation use the pinned engine.'}];
 let at=0,step=0,settled=false,attackDeclared=false,attackEnded=false,sourcePlayed=false,payment=null,baseline=null;const task=()=>tasks[at];
 const snapshot=stage=>{const state=fullState(eg);witness.observations.push({stage,state,source:observe(source,eg),targets:cards.map(c=>observe(c,eg)),activeAttack:eg.game.currentAttack?{attacker:id(eg.game.currentAttack.attacker),targets:eg.game.currentAttack.getAllTargets().map(id)}:null});return state;};
 eg.game.on('onCardPlayed',e=>{if(e.card===source&&!e.isCancelledOrReplaced){sourcePlayed=true;assert.ok(payment);const paid=payment.ready-own.resources.filter(c=>!c.exhausted).length;assert.equal(paid,source.cost+2*own.getPenaltyAspects(source.aspects).length);witness.events.push({name:'paid-source',amount:paid,source:id(source)});}});
 for(const name of ['onCardDefeated','onCardLeavesPlay','onDamageDealt','onCardsDrawn'])eg.game.on(name,e=>{if(!attackDeclared||settled||e.isCancelledOrReplaced)return;witness.events.push({name,card:e.card?id(e.card):null,source:eg.game.allCards.includes(e.context?.source)?id(e.context.source):null,amount:e.damageDealt??e.amount??null,damageType:e.type??null,player:e.player?eg.seatOf(e.player.id):null,activeAttacker:eg.game.currentAttack?id(eg.game.currentAttack.attacker):null,winner:eg.over?eg.winner:null});});
 eg.game.on('onAttackDeclared',e=>{if(settled)return;if(e.attack.attacker===source){assert.equal(task().stage,'attack');assert.deepEqual(e.attack.getAllTargets(),[task().target],'Actual declared target is the scripted physical target');attackDeclared=true;witness.events.push({name:'focus-attack-declared',attacker:id(source),target:id(task().target)});}});
 eg.game.on('onAttackEnd',e=>{if(settled)return;if(attackDeclared&&e.attack.attacker===source){attackEnded=true;witness.events.push({name:'focus-attack-end',attacker:id(source)});}});
 function beginFocus(){
  const queried=eg.game.getArenaUnits({otherThan:source,arena:'spaceArena'}),attachments=queried.flatMap(c=>c.upgrades.map(id));
  assert.deepEqual(queried,cards.filter(c=>c.zoneName==='spaceArena'),'Declared global staging order is the source live query order');baseline={queried:queried.map(id),attachments,ground:cards.filter(c=>c.zoneName==='groundArena').map(c=>({card:c,...observe(c,eg),upgrades:c.upgrades.map(id)})),base:[own.base.damage,enemy.base.damage],hand:[own.hand.length,enemy.hand.length]};
  witness.observations.push({stage:'before-attack',queried:baseline.queried,attachments,source:id(source),arenaOrder:eg.game.getArenaUnits({arena:'spaceArena'}).map(id)});
 }
 function checkFocus(){
  assert.ok(attackDeclared,'Real focus attack declared');const defeated=witness.events.filter(e=>e.name==='onCardDefeated').map(e=>e.card),expected=baseline.queried.filter(cid=>{const c=eg.game.allCards.find(c=>id(c)===cid);return !(p.scenario==='phantom-diagnostic'&&c.controller===enemy&&c.cardData.internalName==='lurking-tie-phantom');});
  assert.deepEqual(defeated.filter(cid=>baseline.queried.includes(cid)),expected,'Explicit defeat resolves in global arena entry order with applicable enemy immunity');
  assert.deepEqual(defeated.filter(cid=>baseline.attachments.includes(cid)),baseline.attachments.toReversed(),'Attachment contingents reverse complete insertion order before parent defeats');
  if(baseline.attachments.length)assert.ok(Math.max(...baseline.attachments.map(cid=>defeated.indexOf(cid)))<Math.min(...expected.map(cid=>defeated.indexOf(cid))),'All attachment contingents precede all parents');
  assert.equal(source.zoneName,'spaceArena','Only physical source is excluded');for(const g of baseline.ground){assert.deepEqual(observe(g.card,eg),{id:g.id,zone:g.zone,damage:g.damage},'Ground exclusion');assert.deepEqual(g.card.upgrades.map(id),g.upgrades,'Ground attachments excluded from space defeat');}
  if(roles.defender!=null){assert.equal(cards[roles.defender].zoneName,'discard');assert.equal(witness.events.filter(e=>e.name==='onDamageDealt'&&e.damageType==='combat').length,0,'Removed defender produces no combat damage');}
  assert.ok(attackEnded,'Attack ends even with a removed defender or latched terminal winner');assert.equal(eg.game.currentAttack,null,'Cleanup removes active attack, including terminal continuation');
  if(p.scenario==='death-trigger-order'){assert.equal(own.hand.length,baseline.hand[0]+1);assert.equal(enemy.hand.length,baseline.hand[1]+1);assert.equal(own.base.damage,baseline.base[0]+2);assert.equal(enemy.base.damage,baseline.base[1]+2+source.getPower());}
  if(p.scenario==='on-defense-capture')assert.equal(enemy.base.damage,baseline.base[1]+1,'Captured mandatory OnDefense resolves after defender is defeated');
  if(p.scenario==='on-defense-terminal')assert.equal(enemy.base.damage,enemy.base.cardData.hp,'Captured dead defender causes actual terminal base1');
  if(p.scenario==='terminal-base'){assert.ok(eg.over,'Mandatory death damage creates a true terminal result');assert.equal(own.base.damage,own.base.cardData.hp);assert.equal(own.hand.length,baseline.hand[0]+1,'Captured optional death draw resolves even after winner latch');assert.ok(witness.events.some(e=>e.name==='onCardsDrawn'&&e.winner),'Actual death continuation runs after terminal winner is latched');assert.equal(enemy.base.damage,baseline.base[1]+2+source.getPower(),'Captured own death damage and combat finish after terminal latch');}
  snapshot('after-focused-attack');
 }
 const completion=terminalCompletion(eg,5000);try{while(true){
  const pid=completion.nextActor(step);if(!pid)break;const actions=expandActions(eg,eg.legalActions(pid)),window=eg.isActionWindow(pid),prompt=eg.player(pid).currentPrompt();let chosen;if(eg.over)witness.observations.push({stage:'post-winner-public-choice',actor:eg.seatOf(pid),title:prompt.menuTitle,actions:actions.map(a=>canonicalAction(eg,a)),winner:eg.winner});
  if(window&&!settled){let t=task();if(t.stage==='play'&&sourcePlayed||t.stage==='phase'&&t.round!=null&&eg.round>t.round||t.stage==='prelude'&&t.declared||t.stage==='cancel'&&t.cancelled||t.stage==='attack'&&attackDeclared){if(t.stage==='cancel'){assert.equal(attackDeclared,false);assert.equal(source.exhausted,false);assert.equal(own.resources.filter(c=>!c.exhausted).length,t.readyResources,'Cancellation pays no resource cost');assert.deepEqual(actions.map(a=>canonicalAction(eg,a)),t.beforeActions,'Cancellation restores exact canonical action window');assert.ok(cards.every(c=>['groundArena','spaceArena'].includes(c.zoneName)));snapshot('cancelled-before-declaration');}if(t.stage==='attack'){checkFocus();settled=true;}else at++;}}
  const t=task();if(window){records.push({type:'state',step,actor:eg.seatOf(pid),state:fullState(eg,pid)});if(!settled){if(t.stage==='phase'){t.round??=eg.round;}else if(pid===t.player.id){chosen=actions.find(a=>a.cardUuid===t.card.uuid);if(chosen&&t.stage==='play')payment={ready:own.resources.filter(c=>!c.exhausted).length};if(chosen&&t.stage==='cancel'){t.beforeActions=actions.map(a=>canonicalAction(eg,a));t.readyResources=own.resources.filter(c=>!c.exhausted).length;}if(chosen&&t.stage==='attack')beginFocus();}chosen??=actions.find(a=>a.arg==='pass');}}
  if(!window&&!settled){witness.menus.push({stage:t.stage,actor:eg.seatOf(pid),title:prompt.menuTitle,actions:actions.map(a=>canonicalAction(eg,a))});
   if(t.stage==='cancel'){chosen=actions.find(a=>a.arg==='cancel');if(chosen)t.cancelled=true;}
   if(prompt.menuTitle==='Choose a target for attack'){if(['attack','cancel'].includes(t.stage)){const enemies=eg.game.getArenaUnits({arena:'spaceArena'}).filter(c=>c.controller===enemy),sentinels=enemies.filter(c=>c.hasSomeKeyword('sentinel')),expected=sentinels.length?sentinels:[...enemies,enemy.base];assert.deepEqual(actions.filter(a=>a.kind==='card').map(a=>eg.cardId(a.cardUuid)),expected.map(id),'Exact normal space-attack defender domain and Sentinel precedence');witness.observations.push({stage:'focus-target-menu',expected:expected.map(id),actions:actions.map(a=>canonicalAction(eg,a))});}
    if(t.stage==='prelude'){const legal=actions.filter(a=>a.kind==='card').map(a=>a.cardUuid);if(p.scenario==='sentinel-domain')assert.deepEqual(legal,[source.uuid],'Live intrinsic Sentinel forces opponent to choose Summa');else{assert.ok(legal.includes(own.base.uuid),'Actual Saboteur can bypass Summa Sentinel');assert.ok(legal.includes(source.uuid));}t.declared=true;}
    chosen??=actions.find(a=>a.cardUuid===t.target?.uuid);
   }
   if(/Both players have triggered/.test(prompt.menuTitle??'')){assert.deepEqual(actions.map(a=>a.label),['You','Opponent']);assert.deepEqual(actions.map(a=>canonicalAction(eg,a).arg),[0,1],'Exact declaration/death owner choice arguments');chosen=actions.find(a=>a.label===(p.scenario==='terminal-base'?'Opponent':'You'));}
   if(attackDeclared&&actions.some(a=>a.kind==='card')){
    const bases=actions.filter(a=>a.kind==='card').map(a=>a.cardUuid);if(bases.includes(own.base.uuid)&&bases.includes(enemy.base.uuid))chosen=actions.find(a=>a.cardUuid===eg.player(pid).opponent.base.uuid);
   }
   chosen??=actions.find(a=>a.arg==='all'&&/^Resolve all/.test(a.label??''));chosen??=actions.find(a=>/Defeat all other space units/.test(a.label??''));chosen??=actions.find(a=>['Trigger','Resolve','Yes'].includes(a.label));chosen??=actions.find(a=>a.arg==='done');chosen??=actions.length===1?actions[0]:undefined;
  }
  chosen??=bot.choose({game:eg,pid,actions,rng});assert.ok(chosen);records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,selected:(eg.player(pid).promptState.selectedCards??[]).map(id),actionWindow:window},actions:actions.map(a=>canonicalAction(eg,a)),chosen:canonicalAction(eg,chosen).key,events:[]});eg.apply(pid,chosen,rng);step++;
 }
 if(!settled&&attackDeclared){checkFocus();settled=true;}assert.ok(sourcePlayed&&settled);assert.ok(eg.over,'All actual recorded games complete');witness.terminalCompletion=completion.assertComplete();records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});witness.coverageObligationIds=[...(scenario.coverageObligationIds??[])];return {records,witness};
 }catch(e){let state;try{state=fullState(eg);}catch(x){state={exportError:x.message};}e.diagnostic={records,witness,state,task:task()?.stage};throw e;}finally{bot.close?.();}
}
module.exports={fixture,dependencies:['lab/kessel-reference/pipeline/terminal-completion.js','lab/kessel-reference/pipeline/arena-defeat-attack-probe-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','engine/env.js','bots/omni/rs/state.js']};
