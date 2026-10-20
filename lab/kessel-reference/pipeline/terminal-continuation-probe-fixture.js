'use strict';
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');

// Planner expectations are assertions, not annotations. Keep their supported
// field domain closed so a future expectation cannot silently acquire credit.
function assertExpected(expected, witness, {ownSeat, enemySeat, focusOwner}) {
    const fields = ['winner','terminalPromptOwner','promptTitle','targetIndices','optionalPass',
        'targetDamageEvents','targetFinalDamage','ownBaseFinalDamage','enemyBaseFinalDamage',
        'focusFinalZone','targetFinalZone','mandatoryHandDiscard','exactButtons','focusOwnerHandDelta'];
    assert.ok(expected && typeof expected === 'object' && !Array.isArray(expected), 'Required source expectations');
    for (const key of Object.keys(expected)) assert.ok(fields.includes(key), 'Unasserted terminal expectation: ' + key);
    const seat = relative => { assert.ok(['self','opponent'].includes(relative)); return relative === 'self' ? ownSeat : enemySeat; };
    assert.equal(witness.final.winner,seat(expected.winner),'Expected latched winner');
    const prompt = witness.observations.find(o => o.stage === 'post-winner-public-choice' && o.title === expected.promptTitle);
    assert.ok(prompt,'Expected exact post-winner prompt title: ' + expected.promptTitle);
    assert.equal(prompt.actor,seat(expected.terminalPromptOwner),'Expected terminal prompt owner');
    const pass = prompt.actions.filter(a => a.arg === 'passAbility' || a.arg === 'pass');
    assert.equal(pass.length,expected.optionalPass ? 1 : 0,'Exact optional Pass presence');
    if (expected.optionalPass) assert.equal(pass[0].label,'Pass');
    if (Object.hasOwn(expected,'targetIndices')) assert.deepEqual(prompt.actions.filter(a => a.kind === 'card').map(a => a.card),
        expected.targetIndices.map(i => witness.final.targets[i].id),'Exact physical terminal target domain');
    if (Object.hasOwn(expected,'exactButtons')) assert.deepEqual(prompt.actions.filter(a => a.kind === 'button').map(({arg,label}) => ({arg,label})),expected.exactButtons,'Exact button arguments and labels');
    const target = () => { assert.ok(expected.targetIndices?.length,'Target assertion requires explicit physical target index'); return witness.final.targets[expected.targetIndices[0]]; };
    if (Object.hasOwn(expected,'targetDamageEvents')) assert.deepEqual(witness.events.filter(e => e.event === 'onDamageDealt' && e.card === target().id).map(e => e.amount),expected.targetDamageEvents,'Exact ordered per-event damage amounts');
    if (Object.hasOwn(expected,'targetFinalDamage')) assert.equal(target().damage,expected.targetFinalDamage,'Expected target damage');
    if (Object.hasOwn(expected,'targetFinalZone')) assert.equal(target().zone,expected.targetFinalZone,'Expected target zone');
    if (Object.hasOwn(expected,'focusFinalZone')) assert.equal(witness.final.source.zone,expected.focusFinalZone,'Expected focus zone');
    if (Object.hasOwn(expected,'ownBaseFinalDamage')) assert.equal(witness.final.bases[0],expected.ownBaseFinalDamage,'Expected acting player base damage');
    if (Object.hasOwn(expected,'enemyBaseFinalDamage')) assert.equal(witness.final.bases[1],expected.enemyBaseFinalDamage,'Expected opposing base damage');
    if (Object.hasOwn(expected,'mandatoryHandDiscard')) {
        const discarded = witness.events.filter(e => e.event === 'onCardDiscarded' && e.state.winner).map(e => e.card);
        assert.equal(discarded.length,expected.mandatoryHandDiscard,'Exact committed post-winner discard count');
        for (const card of discarded) assert.ok(prompt.state.ownHand.includes(card),'Discard belongs to pre-discard acting hand');
        assert.deepEqual(witness.final.ownHand,prompt.state.ownHand.filter(card => !discarded.includes(card)),'Only accepted physical hand cards depart');
        assert.ok(discarded.includes(prompt.chosen.card),'Accepted selected card is actually discarded');
    }
    if (Object.hasOwn(expected,'focusOwnerHandDelta')) {
        seat(focusOwner); const hand = focusOwner === 'self' ? 'ownHand' : 'enemyHand';
        assert.equal(witness.final[hand].length-witness.initial[hand].length,expected.focusOwnerHandDelta,'Expected focus-owner hand change');
    }
    return Object.keys(expected);
}

function assertRegroupExpected(expected, witness, ownSeat) {
    const fields=['winner','terminalPromptOwner','promptTitle','prewinnerDeathPromptTitle','prewinnerDeathPhase',
        'ownBaseFinalDamage','enemyBaseFinalDamage','targetFinalZone','targetDamageBeforeExpiry','targetHpBeforeExpiry',
        'roundDelta','allResourcesReady','postWinnerResourceSeats','regroupDrawAmounts','phaseSequence'];
    for(const key of Object.keys(expected))assert.ok(fields.includes(key),'Unasserted regroup expectation: '+key);
    assert.equal(expected.winner,'self');assert.equal(witness.final.winner,ownSeat);
    assert.equal(expected.terminalPromptOwner,'both');
    const prompts=witness.observations.filter(o=>o.stage==='post-winner-public-choice'&&o.title===expected.promptTitle);
    assert.deepEqual(prompts.map(o=>o.actor),expected.postWinnerResourceSeats,'Both real resource prompts after winner');
    assert.ok(prompts.every(o=>o.state.phase==='regroup'&&o.chosen.arg==='done'&&o.chosen.label==='Skip Resourcing'));
    const death=witness.observations.find(o=>o.title===expected.prewinnerDeathPromptTitle&&!o.state.winner);
    assert.ok(death,'Mandatory death target before winner latch');assert.equal(death.state.phase,expected.prewinnerDeathPhase);
    assert.equal(death.chosen.card,witness.enemyBaseId,'Actual death ability chooses opposing physical base');
    assert.equal(witness.final.bases[0],expected.ownBaseFinalDamage);assert.equal(witness.final.bases[1],expected.enemyBaseFinalDamage);
    assert.equal(witness.final.targets[0].zone,expected.targetFinalZone);
    const damage=witness.events.find(e=>e.event==='onDamageDealt'&&e.card===witness.initial.targets[0].id);
    assert.ok(damage);assert.equal(damage.amount,expected.targetDamageBeforeExpiry);
    assert.equal(damage.state.targets[0].damage,expected.targetDamageBeforeExpiry);assert.equal(damage.state.targets[0].hp,expected.targetHpBeforeExpiry);
    assert.equal(witness.final.round-witness.initial.round,expected.roundDelta);
    assert.equal(witness.final.resources.flat().every(c=>!c.exhausted),expected.allResourcesReady);
    assert.deepEqual(witness.events.filter(e=>e.event==='onCardsDrawn'&&e.state.phase==='regroup').map(e=>e.amount),expected.regroupDrawAmounts);
    assert.deepEqual([witness.initial.phase,...witness.events.filter(e=>e.event==='onPhaseStarted').map(e=>e.phase)],expected.phaseSequence);
    return Object.keys(expected);
}

// Phase-end death can latch a winner before RegroupPhase's already queued draw,
// resource and ready steps. Complete that phase and its next action boundary;
// stopping when winner first appears loses real engine behavior.
async function regroupFixture(env,pool,scenario,seed) {
    const p=scenario.probe;assert.equal(p.scenario,'expiry-cavern-regroup');assert.ok([1,2].includes(p.sourceSeat));
    assert.equal(p.emptyDecks,true);assert.equal(p.initiallyExhaustResource,true);
    const preparationCode=p.preparationCode,activationCode=p.activationCode??p.cardId;
    for(const code of [preparationCode,activationCode,...p.targets.map(t=>t.code)])
        assert.ok(pool.cards.some(c=>c.setCode===code),'Regroup construction requires actual admitted definition: '+code);
    const reverse=p.sourceSeat===2,swap=owner=>owner==='self'?'opponent':'self';
    const rows=p.targets.map(t=>({...t,owner:reverse?swap(t.owner):t.owner,attachments:t.attachments?.map(a=>({...a,...(reverse&&a.owner?{owner:swap(a.owner)}:{})}))}));
    rows.push({code:activationCode,owner:reverse?'opponent':'self',zone:'hand'});
    if(reverse)rows.push({code:preparationCode,owner:'opponent',zone:'hand'});
    const setup=await constructProbeFixture(env,pool,{...scenario,probe:{...p,cardId:preparationCode,activationCode:undefined,
        sourceInPlay:false,initiative:reverse?'opponent':'self',targets:rows}},seed);
    const {eg,rng,bot,deck}=setup,own=reverse?setup.enemy:setup.own,enemy=reverse?setup.own:setup.enemy;
    const targets=setup.targets.slice(0,p.targets.length),activation=setup.targets[p.targets.length],preparation=reverse?setup.targets.at(-1):setup.source;
    own.base.damage=p.ownDamage;enemy.base.damage=p.enemyDamage;
    for(const player of [own,enemy]){for(const card of [...player.drawDeck])card.moveTo('discard');player.resources[0].exhausted=true;}
    eg.game.resolveGameState(true);eg.game.continue();const id=c=>eg.cardId(c.uuid);
    const observation=()=>({winner:eg.winner??null,phase:eg.phase,round:eg.round,bases:[own.base.damage,enemy.base.damage],
        ownHand:own.getCardsInZone('hand').map(id),enemyHand:enemy.getCardsInZone('hand').map(id),
        resources:[own,enemy].map(player=>player.resources.map(c=>({id:id(c),exhausted:c.exhausted}))),
        source:{id:id(activation),zone:activation.zoneName},targets:targets.map(c=>({id:id(c),zone:c.zoneName,hp:c.isInPlay()?c.getHp():null,damage:c.isInPlay()?c.damage:null}))});
    const witness={initial:observation(),enemyBaseId:id(enemy.base),events:[],observations:[],coverageObligationIds:[]};
    const records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['terminal-regroup-probe','terminal-regroup-probe'],
        decks:[deck,deck],scenario:scenario.name,constructionParameters:p,fixtureConstruction:'Quiet physical XP Cavern, empty decks and one exhausted resource per seat. Moment of Glory then Operation Cinder are normally paid; ordinary phase passes trigger expiry death, followed by real post-winner regroup choices and ready/round steps.'}];
    const ready=()=>own.resources.filter(c=>!c.exhausted).length;
    const cost=card=>{const aspects=[...own.getAspectsForCosts()];return card.cardData.cost+card.cardData.aspects.reduce((n,a)=>{const i=aspects.indexOf(a);if(i<0)return n+2;aspects.splice(i,1);return n;},0);};
    const payments=[];let played=0,step=0,latched=null,settled=false;
    eg.game.on('onCardPlayed',e=>{if(e.card===preparation||e.card===activation){played++;const payment=payments.find(p=>p.id===id(e.card));assert.ok(payment);payment.after=ready();assert.equal(payment.after,payment.before-payment.cost,'Actual preparation/activation payment');}});
    for(const name of ['onCardsDrawn','onDamageDealt','onCardDefeated','onRegroupPhaseReadyCards','onPhaseStarted','onPhaseEnded'])
        eg.game.on(name,e=>witness.events.push({event:name,phase:e.phase??null,card:e.card?id(e.card):null,amount:e.damageDealt??e.amount??null,state:observation()}));
    try {
        for(;step<60;step++) {
            const pid=eg.ids.find(pid=>eg.legalActions(pid).length);assert.ok(pid,'Committed phase must expose its next real prompt');
            const actions=expandActions(eg,eg.legalActions(pid)),prompt=eg.player(pid).currentPrompt();
            if(latched)assert.equal(eg.winner,latched);else if(eg.winner)latched=eg.winner;
            if(eg.winner&&eg.isActionWindow(pid)&&eg.phase==='action'&&eg.round===witness.initial.round+1){settled=true;break;}
            if(eg.isActionWindow(pid))records.push({type:'state',step,state:fullState(eg,pid)});
            let chosen;
            if(eg.isActionWindow(pid)) {
                const card=pid===own.id?(played===0?preparation:played===1?activation:null):null;
                chosen=card?actions.find(a=>a.cardUuid===card.uuid):actions.find(a=>a.arg==='pass');
                if(card)payments.push({id:id(card),before:ready(),cost:cost(card)});
            } else if(/Give a unit/.test(prompt.menuTitle??''))chosen=actions.find(a=>a.cardUuid===targets[0].uuid);
            else if(prompt.menuTitle==='Deal 2 damage to a base')chosen=actions.find(a=>a.cardUuid===enemy.base.uuid);
            else chosen=actions.find(a=>a.arg==='done')??actions.find(a=>['Resolve','Trigger'].includes(a.label));
            assert.ok(chosen,'Missing actual regroup choice: '+JSON.stringify({title:prompt.menuTitle,actions:actions.map(a=>canonicalAction(eg,a))}));
            const canonical=actions.map(a=>canonicalAction(eg,a));
            witness.observations.push({stage:eg.winner?'post-winner-public-choice':'pre-winner-choice',actor:eg.seatOf(pid),title:prompt.menuTitle,
                actions:canonical,chosen:canonicalAction(eg,chosen),state:observation()});
            records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,
                selected:(eg.player(pid).promptState.selectedCards??[]).map(id),actionWindow:eg.isActionWindow(pid)},actions:canonical,chosen:canonicalAction(eg,chosen).key,events:[]});
            eg.apply(pid,chosen,rng);
        }
        assert.ok(settled);assert.equal(played,2,'Both ordinary printed sources actually played');
        assert.equal(preparation.zoneName,'discard');assert.equal(activation.zoneName,'discard');
        assert.ok(witness.initial.resources.every(rows=>rows.some(c=>c.exhausted)),'Ready result is state-changing');
        witness.final=observation();witness.payments=payments;witness.expectedAssertions=assertRegroupExpected(scenario.expected,witness,eg.seatOf(own.id));
        witness.coverageObligationIds=[...scenario.coverageObligationIds];
        records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});return{records,witness};
    }catch(error){error.diagnostic={records,witness};throw error;}finally{bot.close?.();}
}

function assertOrdinaryRegroupExpected(expected,witness) {
    const fields=['winnerAbsolute','baseFinalDamageAbsolute','resourceCountDelta','handCountDelta','allResourcesReady','allUnitsReady',
        'allLeadersReady','roundDelta','finalActor','postWinnerResourceSeats','resourceSelectionPerSeat','phaseSequence','terminalPromptOwner','promptTitle','regroupDrawAmounts'];
    for(const key of Object.keys(expected))assert.ok(fields.includes(key),'Unasserted ordinary regroup expectation: '+key);
    assert.equal(witness.final.winner,expected.winnerAbsolute);assert.deepEqual(witness.final.players.map(p=>p.base),expected.baseFinalDamageAbsolute);
    assert.equal(witness.final.round-witness.initial.round,expected.roundDelta);assert.equal(witness.finalActor,expected.finalActor);
    assert.deepEqual(witness.final.players.map((p,i)=>p.resources.length-witness.initial.players[i].resources.length),expected.resourceCountDelta);
    assert.deepEqual(witness.final.players.map((p,i)=>p.hand.length-witness.initial.players[i].hand.length),expected.handCountDelta);
    assert.equal(witness.final.players.every(p=>p.resources.every(c=>!c.exhausted)),expected.allResourcesReady);
    assert.equal(witness.final.players.every(p=>p.units.every(c=>!c.exhausted)),expected.allUnitsReady);
    assert.equal(witness.final.players.every(p=>!p.leaderExhausted),expected.allLeadersReady);
    assert.equal(expected.terminalPromptOwner,'both');
    const prompts=witness.observations.filter(o=>o.stage==='post-winner-public-choice');
    assert.ok(prompts.every(o=>o.title===expected.promptTitle&&o.state.phase==='regroup'));
    assert.deepEqual([...new Set(prompts.map(o=>o.actor))],expected.postWinnerResourceSeats);
    for(const seat of expected.postWinnerResourceSeats){
        const picks=prompts.filter(o=>o.actor===seat&&o.chosen.kind==='card');assert.equal(picks.length,expected.resourceSelectionPerSeat);
        const confirms=prompts.filter(o=>o.actor===seat&&o.chosen.arg==='done');assert.equal(confirms.length,1);assert.equal(confirms[0].chosen.label,'Confirm Resources');
        const final=witness.final.players[seat==='p1'?0:1];for(const pick of picks){assert.ok(final.resources.some(c=>c.id===pick.chosen.card));assert.ok(!final.hand.includes(pick.chosen.card));}
    }
    assert.deepEqual([witness.initial.phase,...witness.events.filter(e=>e.event==='onPhaseStarted').map(e=>e.phase)],expected.phaseSequence);
    const draws=witness.events.filter(e=>e.event==='onCardsDrawn'),damages=witness.events.filter(e=>e.event==='onDamageDealt');
    assert.deepEqual(draws.map(e=>e.amount),expected.regroupDrawAmounts,'Both queued framework draws resolve');
    assert.deepEqual(expected.regroupDrawAmounts,[2,2]);
    assert.ok(witness.events.indexOf(draws[1])<witness.events.indexOf(damages[0]),'Both draw events precede fatigue damage');
    assert.equal(damages.length,2);assert.ok(damages.every(e=>!e.state.winner),'Batch damage resolves before the winner latch');
    assert.deepEqual(damages.at(-1).state.players.map(p=>p.base),expected.baseFinalDamageAbsolute);
    return Object.keys(expected);
}

async function ordinaryRegroupFixture(env,pool,scenario,seed) {
    const p=scenario.probe;assert.equal(p.behaviorOnly,true);assert.ok([1,2].includes(p.initiativeSeat));assert.equal(p.sourceSeat,p.initiativeSeat);assert.equal(p.activationCode,null);
    assert.equal(p.emptyDecks,true);assert.equal(p.initiallyExhaustResource,true);assert.equal(p.initiallyExhaustLeaders,true);
    for(const code of [p.cardId,p.constructionCode,...p.targets.map(t=>t.code)])assert.ok(pool.cards.some(c=>c.setCode===code),'Ordinary regroup requires admitted definition: '+code);
    const setup=await constructProbeFixture(env,pool,{...scenario,probe:{...p,cardId:p.constructionCode,activationCode:undefined,
        sourceInPlay:false,initiative:p.initiativeSeat===1?'self':'opponent'}},seed);
    const {eg,rng,bot,deck}=setup,players=[setup.own,setup.enemy],id=c=>eg.cardId(c.uuid);
    for(const [i,player]of players.entries()){player.base.damage=p.initialBaseDamageAbsolute[i];for(const card of [...player.drawDeck])card.moveTo('discard');
        player.resources[0].exhausted=true;player.getAllDeckLeaders()[0].exhausted=true;}
    eg.game.resolveGameState(true);eg.game.continue();
    const observation=()=>({winner:eg.winner??null,phase:eg.phase,round:eg.round,players:players.map(player=>({base:player.base.damage,
        hand:player.getCardsInZone('hand').map(id),resources:player.resources.map(c=>({id:id(c),exhausted:c.exhausted})),
        leaderExhausted:player.getAllDeckLeaders()[0].exhausted,units:player.getArenaUnits().map(c=>({id:id(c),exhausted:c.exhausted})),deck:player.drawDeck.length}))});
    const witness={initial:observation(),events:[],observations:[],coverageObligationIds:[]};
    const records=[{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,bots:['ordinary-regroup-probe','ordinary-regroup-probe'],
        decks:[deck,deck],scenario:scenario.name,constructionParameters:p,fixtureConstruction:'Behavior-only blank-base focus; no source is played. Quiet exhausted units/leaders/resources and empty decks are staged; ordinary passes enter simultaneous regroup draw, followed by actual interleaved resource selection/confirmation after winner.'}];
    let played=0;eg.game.on('onCardPlayed',()=>played++);
    for(const name of ['onCardsDrawn','onDamageDealt','onRegroupPhaseReadyCards','onPhaseStarted','onPhaseEnded'])
        eg.game.on(name,e=>witness.events.push({event:name,phase:e.phase??null,card:e.card?id(e.card):null,amount:e.damageDealt??e.amount??null,state:observation()}));
    let resourceStarted=false,step=0,settled=false,latched=null;const selected=new Set();
    try {
        for(;step<30;step++){
            const pending=eg.ids.filter(pid=>eg.legalActions(pid).length);assert.ok(pending.length);
            if(resourceStarted&&pending.some(pid=>eg.isActionWindow(pid))&&eg.round===witness.initial.round+1){settled=true;break;}
            const preferred=eg.ids[p.initiativeSeat-1],pid=resourceStarted&&pending.includes(preferred)?preferred:pending[0];
            const actions=expandActions(eg,eg.legalActions(pid)),prompt=eg.player(pid).currentPrompt();
            if(latched)assert.equal(eg.winner,latched);else if(eg.winner)latched=eg.winner;
            if(eg.isActionWindow(pid))records.push({type:'state',step,state:fullState(eg,pid)});
            let chosen;if(eg.isActionWindow(pid))chosen=actions.find(a=>a.arg==='pass');
            else {resourceStarted=true;if(!selected.has(pid)){chosen=actions.find(a=>a.kind==='card');selected.add(pid);}chosen??=actions.find(a=>a.arg==='done');}
            assert.ok(chosen);const canonical=actions.map(a=>canonicalAction(eg,a));
            witness.observations.push({stage:eg.winner?'post-winner-public-choice':'pre-winner-choice',actor:eg.seatOf(pid),title:prompt.menuTitle,
                actions:canonical,chosen:canonicalAction(eg,chosen),state:observation()});
            records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType??null,title:prompt.menuTitle??null,
                selected:(eg.player(pid).promptState.selectedCards??[]).map(id),actionWindow:eg.isActionWindow(pid)},actions:canonical,chosen:canonicalAction(eg,chosen).key,events:[]});
            eg.apply(pid,chosen,rng);
        }
        assert.ok(settled&&resourceStarted);assert.equal(played,0,'Behavior-only cases earn no card activation witness');
        witness.final=observation();const finalState=fullState(eg);witness.finalActor=finalState.actor;
        assert.deepEqual(witness.observations.filter(o=>o.stage==='post-winner-public-choice').map(o=>o.actor),p.initiativeSeat===1?['p1','p1','p2','p2']:['p1','p2','p2','p1'],'Actual initiative-dependent resource interleaving');
        witness.expectedAssertions=assertOrdinaryRegroupExpected(scenario.expected,witness);witness.coverageObligationIds=[...scenario.coverageObligationIds];
        records.push({type:'result',step,winner:eg.winner,state:finalState});return{records,witness};
    }catch(error){error.diagnostic={records,witness};throw error;}finally{bot.close?.();}
}

// A winner latch does not end an already committed ability. Record every public
// continuation, including an opponent's optional trigger, until the engine returns
// to an action window. Only then may the terminal result be exported.
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.equal(p.family, 'terminal-continuation');
    if(p.scenario==='ordinary-regroup-fatigue')return ordinaryRegroupFixture(env,pool,scenario,seed);
    if(p.scenario==='expiry-cavern-regroup')return regroupFixture(env,pool,scenario,seed);
    assert.ok([1, 2].includes(p.sourceSeat));
    const activationCode = p.activationCode ?? p.cardId;
    for (const code of [activationCode, p.cardId, ...p.targets.map(t => t.code)])
        assert.ok(pool.cards.some(c => c.setCode === code), 'Terminal construction requires actual admitted definition: ' + code);
    const reverse = p.sourceSeat === 2;
    const rows = p.targets.map(t => ({...t, owner: reverse ? (t.owner === 'self' ? 'opponent' : 'self') : t.owner,
        attachments: t.attachments?.map(a => ({...a, ...(reverse && a.owner ? {owner:a.owner === 'self' ? 'opponent' : 'self'} : {})}))}));
    if (reverse) rows.push({code:activationCode, owner:'opponent', ...(p.sourceInPlay ? {arena:p.sourceArena, exhausted:false} : {zone:'hand'})});
    const setup = await constructProbeFixture(env, pool, { ...scenario, probe: {
        ...p, cardId:activationCode, targets:rows, activationCode:undefined,
        sourceInPlay:!!p.sourceInPlay && !reverse,
        initiative: reverse ? 'opponent' : 'self',
    }}, seed);
    const {eg, rng, bot, deck} = setup;
    const own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const activation = reverse ? setup.targets.at(-1) : setup.source;
    const targets = setup.targets.slice(0, p.targets.length);
    const focus = p.focusTargetIndex == null ? activation : targets[p.focusTargetIndex];
    assert.ok(['self','opponent'].includes(p.focusOwner),'Declared focus physical owner');
    assert.equal(focus.owner,p.focusOwner === 'self' ? own : enemy,'Physical focus owner matches construction');
    own.base.damage = p.ownDamage ?? 0;
    enemy.base.damage = p.enemyDamage ?? 0;
    if (p.sourceInPlay) activation.exhausted = false;
    if (p.emptyDeck) for (const c of [...own.drawDeck]) c.moveTo('discard');
    eg.game.resolveGameState(true); eg.game.continue();
    const id = c => eg.cardId(c.uuid);
    const observation = () => ({winner:eg.winner ?? null, bases:[own.base.damage,enemy.base.damage],
        ownHand:own.getCardsInZone('hand').map(id), enemyHand:enemy.getCardsInZone('hand').map(id),
        source:{id:id(focus),zone:focus.zoneName}, targets:targets.map(c => ({id:id(c),zone:c.zoneName,
            damage:c.isInPlay() ? c.damage : null, hp:c.isInPlay() ? c.getHp() : null}))});
    const witness = {initial:observation(), events:[], observations:[], coverageObligationIds:[]};
    const records = [{type:'meta',schema:'omni-rs-trace-v1',pool:pool.provenance,seed,
        bots:['terminal-continuation-probe','terminal-continuation-probe'],decks:[deck,deck],scenario:scenario.name,
        constructionParameters:p,fixtureConstruction:'Explicit physical quiet targets and initial damage; unmodified activation card paid normally, or staged Hounds attacks. All post-winner public prompts complete before result.'}];
    let activated = false, played = false, latchedWinner = null, terminalChoices = 0, step = 0, settled = false;
    const ready = () => own.getCardsInZone('resource').filter(c => !c.exhausted).length;
    const aspects = [...own.getAspectsForCosts()];
    const expectedCost = activation.cardData.cost + activation.cardData.aspects.reduce((n,a) => {
        const i = aspects.indexOf(a); if (i < 0) return n + 2; aspects.splice(i,1); return n;
    }, 0);
    let beforePayment = null;
    for (const name of ['onCardPlayed','onAttackDeclared','onAttackEnd','onDamageDealt','onCardDefeated','onCardDiscarded','onCardsDrawn'])
        eg.game.on(name, e => {
            if (!activated) return;
            if (name === 'onCardPlayed' && e.card === activation && !e.isCancelledOrReplaced) played = true;
            witness.events.push({event:name,card:e.card ? id(e.card) : null,amount:e.damageDealt ?? e.amount ?? null,state:observation()});
        });
    try {
        for (; step < 100; step++) {
            const pid = eg.ids.find(pid => eg.legalActions(pid).length);
            if (!pid) { settled = true; break; }
            const actions = expandActions(eg, eg.legalActions(pid)), prompt = eg.player(pid).currentPrompt();
            if (latchedWinner) assert.equal(eg.winner, latchedWinner, 'Committed continuation preserves latched winner');
            else if (eg.winner) latchedWinner = eg.winner;
            if (activated && eg.isActionWindow(pid)) { settled = true; break; }
            if (eg.isActionWindow(pid)) records.push({type:'state',step,state:fullState(eg,pid)});
            let chosen;
            if (!activated) {
                chosen = pid === own.id ? actions.find(a => a.cardUuid === activation.uuid) : actions.find(a => a.arg === 'pass');
                if (chosen?.cardUuid === activation.uuid) { activated = true; beforePayment = ready(); }
            } else if (p.sourceInPlay && !eg.winner) chosen = actions.find(a => a.cardUuid === enemy.base.uuid);
            else if (p.scenario === 'rancor-two-hits') chosen = actions.find(a => a.cardUuid === targets[0].uuid);
            else if (p.scenario === 'raddus-death') chosen = actions.find(a => a.cardUuid === targets[1].uuid);
            else if (p.scenario === 'hounds-choose') chosen = actions.find(a => a.cardUuid === targets[0].uuid);
            else if (p.scenario === 'hounds-pass') chosen = actions.find(a => a.arg === 'passAbility');
            else if (p.scenario === 'watermonger-committed-discard' && eg.winner) chosen = actions.find(a => a.kind === 'card');
            else if (p.scenario.startsWith('shuttle-')) chosen = (/Both players have triggered abilities/.test(prompt.menuTitle ?? '') ? actions.find(a => a.label === 'You') : null) ?? actions.find(a => a.cardUuid === enemy.base.uuid) ??
                (eg.winner ? actions.find(a => a.arg === (p.scenario === 'shuttle-pass' ? 'pass' : 'trigger')) : null);
            chosen ??= actions.find(a => ['Trigger','Resolve','Resolve all','Done'].includes(a.label));
            assert.ok(chosen, 'Missing terminal continuation choice: ' + JSON.stringify({scenario:p.scenario,title:prompt.menuTitle,actions:actions.map(a => canonicalAction(eg,a))}));
            const canonical = actions.map(a => canonicalAction(eg,a));
            if (eg.winner) {
                terminalChoices++;
                witness.observations.push({stage:'post-winner-public-choice',actor:eg.seatOf(pid),title:prompt.menuTitle,
                    actions:canonical,chosen:canonicalAction(eg,chosen),state:observation()});
            }
            records.push({type:'decision',step,actor:eg.seatOf(pid),prompt:{type:prompt.promptType ?? null,title:prompt.menuTitle ?? null,
                selected:(eg.player(pid).promptState.selectedCards ?? []).map(id),actionWindow:eg.isActionWindow(pid)},
                actions:canonical,chosen:canonicalAction(eg,chosen).key,events:[]});
            eg.apply(pid, chosen, rng);
        }
        assert.ok(settled && activated && eg.winner, 'Actual terminal sequence completes');
        assert.ok(terminalChoices > 0, 'Actual public choice after winner latch');
        if (!p.sourceInPlay) { assert.ok(played,'Activation card normally played'); assert.equal(ready(),beforePayment-expectedCost,'Printed/aspect payment'); }
        witness.final = observation();
        witness.coverageObligationIds = [...scenario.coverageObligationIds];
        const relativeWinner = ['hounds-choose','hounds-pass','shuttle-trigger','shuttle-pass'].includes(p.scenario) ? own : enemy;
        assert.equal(eg.winner,eg.seatOf(relativeWinner.id));
        if (p.scenario === 'rancor-two-hits') {
            assert.equal(targets[0].damage,10); assert.equal(own.base.damage,30);
            const o=witness.observations.find(o => o.title === 'Deal 5 damage to an enemy ground unit. Then, deal 5 damage to the same unit.');
            assert.ok(o); assert.equal(o.actions.length,1); assert.equal(o.actions[0].card,id(targets[0]));
            assert.deepEqual(witness.events.filter(e => e.event === 'onDamageDealt' && e.card === id(targets[0])).map(e => e.amount),[5,5]);
        } else if (p.scenario === 'raddus-death') { assert.equal(focus.zoneName,'discard'); assert.equal(targets[1].damage,13);
            assert.deepEqual(witness.events.filter(e => e.event === 'onDamageDealt' && e.card === id(targets[1])).map(e => e.amount),[5,8]);
            const o=witness.observations.find(o => o.title === 'Deal 8 damage to an enemy unit');
            assert.ok(o); assert.equal(o.actions.length,1); assert.equal(o.actions[0].card,id(targets[1])); }
        else if (p.scenario.startsWith('hounds-')) {
            assert.equal(targets[0].zoneName,p.scenario === 'hounds-pass' ? 'groundArena' : 'discard');
            const o=witness.observations.find(o => o.title === 'Defeat a unit with less than 4 power');
            assert.ok(o); assert.equal(o.actions.length,2); assert.ok(o.actions.some(a => a.arg === 'passAbility' && a.label === 'Pass'));
        } else if (p.scenario === 'watermonger-committed-discard') {
            assert.equal(own.getCardsInZone('hand').length,witness.initial.ownHand.length-2);
            assert.ok(witness.observations.some(o => o.title === "Choose a card to discard for Mos Espa Watermonger's effect" && o.actions.every(a => a.kind === 'card')));
        } else {
            const o=witness.observations.find(o => o.title === 'You may trigger this ability'); assert.ok(o);
            assert.equal(o.actor,eg.seatOf(enemy.id)); assert.deepEqual(o.actions.map(a => a.label),['Trigger','Pass']);
            assert.equal(enemy.getCardsInZone('hand').length,witness.initial.enemyHand.length+(p.scenario === 'shuttle-trigger' ? 1 : 0));
        }
        witness.expectedAssertions = assertExpected(scenario.expected,witness,{ownSeat:eg.seatOf(own.id),enemySeat:eg.seatOf(enemy.id),focusOwner:p.focusOwner});
        // Pending selectors are decisions, never action-window import snapshots.
        // The terminal export happens only after all committed choices complete.
        records.push({type:'result',step,winner:eg.winner,state:fullState(eg)});
        return {records,witness};
    } catch (error) { error.diagnostic={records,witness}; throw error; }
    finally { bot.close?.(); }
}
module.exports = {fixture,assertExpected,assertRegroupExpected,assertOrdinaryRegroupExpected,dependencies:['lab/kessel-reference/pipeline/terminal-continuation-probe-fixture.js',
    'lab/kessel-reference/pipeline/probe-fixture.js','engine/env.js','engine/view.js','bots/omni/rs/state.js',
    'bots/omni/rs/state-evidence.js','bots/omni/rs/support-state.js','bots/omni/rs/pool.js','bots/players/index.js',
    'kessel:cards/pipeline/terminal-continuation-probes.js']};
