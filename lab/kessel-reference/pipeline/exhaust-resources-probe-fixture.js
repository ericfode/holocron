'use strict';
const assert = require('node:assert/strict');
const {constructProbeFixture} = require('./probe-fixture');
const {fullState, canonicalAction, expandActions} = require('../../../bots/omni/rs/state');
// Source contract: ExhaustResourcesSystem defaults to opponent; Scout explicitly
// targets context.player. Player.exhaustResources takes the first ready physical
// resource, preserving the resource zone's order and all existing exhausted rows.
function expectedLayout(layout, decline) {
    const result = [...layout];
    const first = result.indexOf(false);
    if (!decline && first >= 0) result[first] = true;
    return result;
}
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.equal(p.family, 'exhaust-resources');
    const death = p.trigger === 'when-defeated', attack = p.trigger === 'on-attack';
    const rows = [];
    if (death) rows.push({code:p.groundCode,owner:p.owner ? 'self':'opponent',arena:'ground',exhausted:false});
    if (!death && !attack && !['no-units','entering-source'].includes(p.scenario)) {
        for (const arena of ['ground','space']) rows.push({code:p[arena+'Code'], owner:p.owner ? 'self':'opponent',arena,exhausted:p.scenario==='all-exhausted'||p.scenario==='mixed-exhausted'&&arena==='ground'});
        if (p.scenario !== 'enemy-only') rows.push({code:p.groundCode,owner:p.owner ? 'opponent':'self',arena:'ground',exhausted:false});
    }
    const sourceIndex = p.owner ? rows.length : -1;
    if (p.owner) rows.push({code:p.cardId,owner:'opponent',arena:'ground',zone:death||attack?undefined:'hand',exhausted:false});
    const constructed = {...scenario,probe:{...p,activationCode:undefined,targets:rows,sourceInPlay:death||attack,sourceArena:'ground',sourceDamage:0}};
    const s = await constructProbeFixture(env,pool,constructed,seed);
    const {eg,rng,bot,deck}=s, own=p.owner?s.enemy:s.own, enemy=p.owner?s.own:s.enemy;
    const source=p.owner?s.targets[sourceIndex]:s.source;
    if(p.owner) s.source.moveTo('deckBottom');
    const targets=s.targets.filter(c=>c!==source), attacker=death?targets[0]:source;
    if(death){source.damage=source.getHp()-1;source.exhausted=true;assert.ok(attacker.getPower()>0);}
    if(attack) source.exhausted=false;
    const recipient=death?own:enemy;
    const resources=player=>player.getCardsInZone('resource');
    const selectedResources=resources(recipient).slice(0,p.resourceLayout.length);
    for(const c of resources(recipient).slice(p.resourceLayout.length)) c.moveTo('deckBottom');
    selectedResources.forEach((c,i)=>c.exhausted=p.resourceLayout[i]);
    assert.equal(selectedResources.filter(c=>!c.exhausted).length,p.readyResources);
    eg.game.resolveGameState(true);eg.game.continue();
    const id=c=>eg.cardId(c.uuid), initialResources=resources(recipient).map(id), initialOther=resources(death?enemy:own).map(c=>({id:id(c),exhausted:c.exhausted}));
    const initialUnits=new Map(targets.map(c=>[c,{exhausted:c.exhausted,zone:c.zoneName}]));
    const resourceRows=player=>resources(player).map(c=>({id:id(c),exhausted:c.exhausted}));
    const initialOwn=resourceRows(own), initialEnemy=resourceRows(enemy);
    const expected=expectedLayout(p.resourceLayout,p.decline);
    const enemyUnits=targets.filter(c=>c.controller===enemy), desired=enemyUnits.find(c=>c.zoneName===(p.targetArena??'ground')+'Arena');
    const witness={initial:{source:id(source),resourceIds:initialResources,resourceLayout:[...p.resourceLayout],expectedResourceLayout:expected,units:targets.map(c=>({id:id(c),owner:eg.seatOf(c.controller.id),...initialUnits.get(c)}))},coverageObligationIds:[],observations:[],events:[],optionalPrompt:false,targetSelected:false,declined:false,selectedTarget:null,playResources:null};
    const records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['exhaust-resources-probe','exhaust-resources-probe'],decks:[deck,deck],scenario:scenario.name,constructionParameters:p,fixtureConstruction:'Stage real focus, quiet units and four existing physical resources in specified interleaved exhaustion order at first natural action window. Wounded Scout is defeated by actual combat; Ziro attacks normally or is normally played. Record all subsequent inputs through terminal result.'}];
    let initiated=false, targeted=false, occurred=false, settled=false, step=0;
    eg.game.on('onCardDefeated',e=>{if(!settled&&e.card===source) {occurred=true;assert.equal(source.zoneName,'discard','Scout LKI trigger occurs after physical departure');}});
    eg.game.on('onCardPlayed',e=>{if(!settled&&e.card===source&&!e.isCancelledOrReplaced){occurred=true;witness.playResources=resourceRows(own);}});
    eg.game.on('onAttackDeclared',e=>{if(!settled&&attack&&e.attack.attacker===source)occurred=true;});
    eg.game.on('onExhaustResources',e=>{if((death||attack)&&!settled&&e.context?.source===source&&!e.isCancelledOrReplaced)witness.events.push({player:eg.seatOf(e.player.id),amount:e.amount,sourceZone:source.zoneName});});
    function check(){
        assert.ok(occurred,'Actual source trigger must occur');
        if(death||attack){
            assert.deepEqual(resources(recipient).map(id),initialResources,'Resource identities retain physical order');
            assert.deepEqual(resources(recipient).map(c=>c.exhausted),expected,'Exactly first ready resource exhausts');
            assert.deepEqual(resources(death?enemy:own).map(c=>({id:id(c),exhausted:c.exhausted})),initialOther,'Other controller resources unchanged');
            assert.equal(witness.events.length,!p.decline&&p.readyResources>0?1:0);
            if(witness.events.length){assert.equal(witness.events[0].player,eg.seatOf(recipient.id));assert.equal(witness.events[0].amount,1);if(death)assert.equal(witness.events[0].sourceZone,'discard');}
            if(attack)assert.equal(witness.optionalPrompt,p.readyResources>0,'Zero-effect optional resource trigger has no prompt');
        }else{
            const feasible=enemyUnits.some(c=>!initialUnits.get(c).exhausted);
            assert.equal(witness.targetSelected,feasible&&!!desired&&!p.decline);
            for(const c of enemyUnits){assert.equal(c.exhausted,initialUnits.get(c).exhausted||feasible&&!p.decline&&c===desired,'Initial exhaustion persists; only chosen enemy can change');assert.equal(c.zoneName,initialUnits.get(c).zone);}
            assert.deepEqual(resourceRows(enemy),initialEnemy,'When Played unit exhaust never exhausts enemy resources');
            assert.deepEqual(resourceRows(own),witness.playResources,'After ordinary play payment, unit exhaustion does not change own resources');
            const aspects=[...own.getAspectsForCosts()];let payment=source.cardData.cost;for(const aspect of source.cardData.aspects){const i=aspects.indexOf(aspect);if(i<0)payment+=2;else aspects.splice(i,1);}
            assert.equal(initialOwn.filter(c=>!c.exhausted).length-witness.playResources.filter(c=>!c.exhausted).length,payment,'Normal source play pays printed and missing-aspect resource cost');
            if(p.scenario==='mixed-exhausted'){assert.equal(witness.selectedTarget,id(desired));assert.equal(initialUnits.get(desired).exhausted,true,'Actual chosen unit was already exhausted');}
            for(const c of targets.filter(c=>c.controller===own))assert.equal(c.exhausted,false,'Friendly units never exhaust');
            assert.equal(witness.optionalPrompt,feasible,'Entering source cannot make enemy-only resolver feasible');
        }
        if(p.decline)assert.ok(witness.declined,'Actual optional decline input');
        witness.observations.push({stage:'focused-effect-resolved',state:fullState(eg)});settled=true;
    }
    try{while(!eg.over&&step<5000){
        const pid=eg.ids.find(pid=>eg.legalActions(pid).length);assert.ok(pid);
        const actions=expandActions(eg,eg.legalActions(pid)),window=eg.isActionWindow(pid),prompt=eg.player(pid).currentPrompt();let chosen;
        if(window){records.push({type:'state',step,state:fullState(eg,pid)});if(occurred&&!settled)check();
            const actor=death?enemy:own;
            if(!initiated&&pid===actor.id){chosen=actions.find(a=>a.cardUuid===(death?attacker:source).uuid);assert.ok(chosen,'Actual focus activation offered');initiated=true;}
            if(!settled)chosen??=actions.find(a=>a.arg==='pass');
        }else if(initiated&&!settled){
            if((death||attack)&&!targeted){chosen=actions.find(a=>a.cardUuid===(death?source:enemy.base).uuid);if(chosen)targeted=true;}
            else if((death||attack)&&actions.some(a=>a.label==='Pass')){
                assert.equal(pid,own.id);witness.optionalPrompt=true;
                assert.deepEqual(actions.map(a=>a.label),['Trigger','Pass'],'Exact optional attack menu');
                chosen=actions.find(a=>a.label===(p.decline?'Pass':'Trigger'));assert.ok(chosen,JSON.stringify({title:prompt.menuTitle,actions:actions.map(a=>canonicalAction(eg,a))}));if(p.decline)witness.declined=true;
            }else if(!death&&!attack&&actions.some(a=>a.kind==='card')){
                assert.equal(pid,own.id);witness.optionalPrompt=true;
                assert.deepEqual(actions.filter(a=>a.kind!=='card').map(a=>({label:a.label,arg:a.arg})),[{label:'Pass',arg:'passAbility'}],'Exact direct optional unit selector Pass');
                assert.deepEqual(actions.filter(a=>a.kind==='card').map(a=>eg.cardId(a.cardUuid)).sort(),enemyUnits.map(id).sort(),'Exact enemy-only unit domain across both arenas');
                chosen=p.decline?actions.find(a=>a.arg==='passAbility'):actions.find(a=>a.cardUuid===desired?.uuid);
                assert.ok(chosen,JSON.stringify({title:prompt.menuTitle,actions:actions.map(a=>canonicalAction(eg,a))}));if(p.decline)witness.declined=true;else {witness.targetSelected=true;witness.selectedTarget=id(desired);}
            }
            chosen??=actions.find(a=>a.kind==='button'&&/trigger|resolve|yes/i.test(a.label??''));chosen??=actions.find(a=>a.arg==='done');
        }
        chosen??=bot.choose({game:eg,pid,actions,rng});assert.ok(chosen);
        records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,selected:(eg.player(pid).promptState.selectedCards??[]).map(id),actionWindow:window},actions:actions.map(a=>canonicalAction(eg,a)),chosen:canonicalAction(eg,chosen).key,events:[]});eg.apply(pid,chosen,rng);step++;
    }
    assert.ok(settled,'Focused effect assertions executed');assert.ok(eg.over,'Full recorded game finishes');records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});witness.coverageObligationIds=[...scenario.coverageObligationIds];return {records,witness};
    }finally{bot.close?.();}
}
module.exports={fixture,expectedLayout,dependencies:['kessel:cards/pipeline/exhaust-resources-probes.js','lab/kessel-reference/pipeline/exhaust-resources-probe-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','engine/env.js','bots/omni/rs/state.js','bots/players/index.js']};
