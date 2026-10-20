'use strict';
// Source-engine evidence only; collective batching is actual event-window identity.
const assert=require('node:assert/strict'),crypto=require('node:crypto');
const {seededRng}=require('../../../engine/env');
const {canonicalAction,fullState,expandActions}=require('../../../bots/omni/rs/state');
const {makeBot}=require('../../../bots/players');
const {terminalCompletion}=require('./terminal-completion');
const U=(key,code,owner='own',extra={})=>({key,code,owner,...extra});
const fillerCodes=['ASH_061','ASH_131','ASH_190','ASH_201','ASH_242','ASH_261','HMW_082','HMW_093','HMW_116','HMW_128','HMW_135','HMW_155','HMW_163','HMW_174','HMW_178','HMW_219','HMW_258'];
const matches = (c, code) => [c.cardData.setId, ...(c.cardData.setCodes ?? [])].some(s => s.set + '_' + String(s.number).padStart(3, '0') === code);
const arena = c => c.cardData.arena === 'space' ? 'spaceArena' : 'groundArena';
const plain = [];
function deckFor(pool, scenario) {
    const codes = [...new Set([...(scenario.units ?? plain).map((u) => u.code), ...scenario.plan.filter((s) => s.from !== 'leader').map((s) => s.code), ...(scenario.extraCodes ?? [])])];
    assert.ok(codes.length <= 17);
    for (const code of [...codes, scenario.leaderCode ?? 'SOR_014', scenario.baseCode ?? 'SOR_023'])
        assert.ok(pool.cards.some((c) => c.setCode === code), `Missing ${code} in oracle input pool`);
    const filler = scenario.fillerCodes.filter(code=>!codes.includes(code)).slice(0,17-codes.length);
    for(const code of filler)assert(pool.cards.some(c=>c.setCode===code&&c.types.includes('unit')&&!c.text),'Missing reviewed quiet filler '+code);
    assert.equal(filler.length, 17 - codes.length);
    return { metadata: { name: 'Event group oracle', author: 'omni-rs fixture' }, leader: { id: scenario.leaderCode ?? 'SOR_014', count: 1 }, base: { id: scenario.baseCode ?? 'SOR_023', count: 1 }, deck: [...codes, ...filler].map((id, i) => ({ id, count: i === 16 ? 2 : 3 })), isPresentInDb: false };
}
async function tokenFixture(env, pool, scenario, seed) {
    const deck = deckFor(pool, scenario), eg = env.newGame({ selectionToggles: true, seed, deck1: deck, deck2: deck }), rng = seededRng('group-fixture-' + seed), bot = makeBot('random');
    await eg.start();
    while (!eg.ids.some((pid) => eg.isActionWindow(pid))) {
        const pid = eg.ids.find((id) => eg.legalActions(id).length), actions = expandActions(eg, eg.legalActions(pid));
        const initiativeChoice = scenario.initiative && actions.find(a => a.label === (pid === eg.ids[scenario.initiative === 'own' ? 0 : 1] ? 'Yourself' : 'Opponent'));
        eg.apply(pid, initiativeChoice ?? bot.choose({ game: eg, pid, actions, rng }), rng);
    }
    const own = eg.player(eg.ids[scenario.seat]), enemy = eg.player(eg.ids[1-scenario.seat]), targets = { ownBase: own.base, enemyBase: enemy.base };
    targets.leader = own.getAllDeckLeaders()[0];
    if (scenario.deployedLeader) {
        targets.leader.deploy({ type: 'leaderUnit' });
        targets.leader.deployEpicActionLimit.increment(own);
        targets.leader.exhausted = false;
    }
    const all = (p) => [...p.drawDeck, ...p.getCardsInZone('hand'), ...p.getCardsInZone('resource')];
    const take = (p, code) => { const c = all(p).find((c) => matches(c, code)); assert.ok(c, `No real ${code}`); return c; };
    for (const u of scenario.units ?? plain) {
        const p = u.owner === 'enemy' ? enemy : own, c = take(p, u.code);
        c.moveTo(arena(c));
        c.exhausted = !!u.exhausted;
        targets[u.key] = c;
        for (let i = 0; i < (u.shields ?? 0); i++)
            eg.game.generateToken(p, 'shield').attachTo(c);
    }
    for(const p of [own,enemy])for(const code of new Set(scenario.plan.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===p).map(s=>s.code))){
        const count=scenario.plan.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===p).length;
        while(p.getCardsInZone('hand').filter(c=>matches(c,code)).length<count){const card=all(p).find(c=>matches(c,code)&&c.zoneName!=='hand');assert(card,'Missing actual script '+code);card.moveTo('hand');}
    }
    for (const p of [own, enemy]) {
        for (const c of p.drawDeck.slice(0, 24)) {
            c.moveTo('resource');
            c.exhausted = false;
        }
        for (const c of p.getCardsInZone('resource'))
            c.exhausted = false;
        p.base.damage = scenario.baseDamage ?? (scenario.bothLethal ? p.base.cardData.hp - 1 : Math.min(24, p.base.cardData.hp - 6));
    }
    if (scenario.ownBaseUndamaged)
        own.base.damage = 0;
    if (scenario.emptyOwnHand) {
        for (const c of own.getCardsInZone('hand')) {
            c.moveTo('resource');
            c.exhausted = false;
        }
    }
    if (scenario.emptyOwnDeck) {
        for (const c of own.drawDeck.slice())
            c.moveTo('discard');
    }
    scenario.setup?.({eg,own,enemy,targets});
    eg.game.resolveGameState(true);
    for (const u of scenario.units ?? plain)
        if (u.damage)
            targets[u.key].damage = u.damage;
    eg.game.continue();
    for (const u of scenario.units ?? plain)
        if (u.shields) {
            assert.equal(targets[u.key].upgrades.length, u.shields);
            assert.ok(targets[u.key].damage < targets[u.key].getHp(), 'Constructed Shield unit must survive initial damage');
        }
    const completion = terminalCompletion(eg, 4000);
    const initialRound = eg.round, observed = {}, scratch = {}, initialState = fullState(eg), records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['scripted-group-fixture', 'scripted-group-fixture'], decks: [deck, deck], scenario: scenario.name,
            evidenceStatus: pool.oracleOnly ? 'PROTOTYPE engine observation; admission/conformance unassessed' : 'Engine observation; native/Wasm conformance unassessed', fixtureConstruction: (scenario.emptyOwnDeck ? 'Empty-deck scenario additionally moves all remaining p1 draw-deck cards into discard before initial state capture. ' : '') + (scenario.emptyOwnHand ? 'Empty-hand scenario additionally moves every initial p1 hand card into ready resources before initial state capture. ' : '') + 'At first natural action window, move specified real deck units into their printed arenas with specified exhaustion, move script cards into p1 hand, move12 remaining deck cards perplayer into ready resources, ready all resources, set bases damage24(orprintedHP-1 forbothLethal), resolve game state, then set disclosed survivingunitdamage and refreshprompts. Specified initial Shields are created with pinned game.generateToken and attached before state resolution. No later state edits.', constructionParameters: { emptyOwnDeck: !!scenario.emptyOwnDeck, emptyOwnHand: !!scenario.emptyOwnHand, units: scenario.units ?? plain, plan: scenario.plan, bothLethal: !!scenario.bothLethal, leaderCode: scenario.leaderCode, deployedLeader: !!scenario.deployedLeader, baseDamage: scenario.baseDamage, initiative: scenario.initiative } }];
    let step = 0, index = 0, pending = null, scriptObserved = false, laterObserved = false;
    try {
        while (true) {
            const pid = completion.nextActor(step);
            if (pid === null) break;
            const actions = expandActions(eg, eg.legalActions(pid)), atWindow = eg.isActionWindow(pid), ctx = { eg, own, enemy, targets, actions, pid, atWindow, index, pending, step, observed, scratch, initialState };
            if (atWindow && scriptObserved && !laterObserved && eg.round > initialRound && scenario.assertLater) {
                scenario.assertLater(ctx);
                observed.laterRoundAssertion = true;
                laterObserved = true;
            }
            scenario.beforeWindow?.(ctx);
            if (atWindow) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (!scriptObserved && index === scenario.plan.length && (!scenario.waitForRegroup || eg.round > initialRound)) {
                    scenario.assertAfter(ctx);
                    observed.postAction = true;
                    scriptObserved = true;
                }
            }
            let chosen;
            if (!scriptObserved && atWindow) {
                if (pid === (scenario.plan[index]?.owner==='enemy'?enemy:own).id && index < scenario.plan.length && (!scenario.plan[index].nextRound || eg.round>initialRound)) {
                    pending = scenario.plan[index++];
                    ctx.pending = pending;
                    ctx.index = index;
                    const c = pending.from ? targets[pending.from] : (pending.owner==='enemy'?enemy:own).getCardsInZone('hand').find((c) => matches(c, pending.code));
                    assert.ok(c, `Missing script ${pending.code}`);
                    chosen = actions.find((a) => a.cardUuid === c.uuid);
                    assert.ok(chosen, `Illegal script ${pending.code}`);
                    scratch.incoming = c;
                }
                else
                    chosen = actions.find((a) => a.arg === 'pass');
            }
            else if (!atWindow && !scriptObserved) {
                chosen = scenario.choose?.(ctx);
                if (!chosen && pending?.target)
                    chosen = actions.find((a) => a.cardUuid === targets[pending.target]?.uuid);
                chosen ??= actions.find((a) => a.kind === 'button' && /trigger|resolve|play|deal|heal|give/i.test(a.label ?? '') && !/pass|cancel|no/i.test(a.label ?? ''));
            }
            if(scriptObserved&&scenario.assertLater&&!laterObserved)chosen??=atWindow?actions.find(a=>a.arg==='pass'):actions.find(a=>a.arg==='done');
            if(!scriptObserved && !atWindow)chosen ??= actions.find(a=>a.arg==='done');
            chosen ??= scenario.chooseLater?.(ctx);
            if(eg.over)chosen ??= actions.find(a=>a.label==='You') ?? actions.find(a=>a.arg==='all');
            chosen ??= bot.choose({ game: eg, pid, actions, rng });
            assert.ok(chosen);
            const prompt = eg.player(pid).currentPrompt();
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map((c) => eg.cardId(c.uuid)), actionWindow: atWindow }, actions: actions.map((a) => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            if (process.env.GROUP_FIXTURE_DEBUG && step < 35)
                console.error(JSON.stringify({ step, actor: eg.seatOf(pid), title: prompt.menuTitle, selected: (eg.player(pid).promptState.selectedCards ?? []).map(c => eg.cardId(c.uuid)), chosen: canonicalAction(eg, chosen) }));
            scenario.beforeApply?.({ ...ctx, chosen });
            eg.apply(pid, chosen, rng);
            step++;
        }
        assert.ok(eg.over, 'Oracle game did not complete');
        assert.equal(index, scenario.plan.length, 'Script incomplete');
        if (!scriptObserved) {
            scenario.assertAfter({ eg, own, enemy, targets, observed, scratch, initialState });
            observed.postAction = true;
        }
        if (scenario.assertLater)
            assert.ok(laterObserved, 'Missing later-round assertion');
        scenario.assertWitness?.({ observed, scratch, records, eg, own, enemy, targets, initialState });
        observed.terminalCompletion = completion.assertComplete();
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        return { records, witness: { scenario: scenario.name, family: scenario.family, observed, decisions: step, winner: eg.winner } };
    }
    catch(e){e.diagnostic={records,observed};throw e;}
    finally {
        bot.close?.();
    }
}
const axeNames=['paid-play-draw3','sequential-draw-windows','opponent-draw-negative','natural-regroup-draw','empty-deck-fatigue','source-gone-before-draw','both-owners-regroup'];
const sabineNames=['shielded-play-own-ground','shielded-play-enemy-ground','shielded-decline','shielded-space-negative','shielded-exhausted-ground','multi-xp-one-window','sequential-upgrade-windows','other-parent-negative','phase-reset-second-window','source-gone-before-attach','unique-keep-old','unique-keep-incoming','weakness-source-death','same-action-sequential-attachment-windows'];
function validateProbe(p){
 assert(p&&Object.keys(p).sort().join(',')==='baseCode,cardId,enemyBaseCode,enemyLeaderCode,family,fillerCodes,leaderCode,mode,owner,resourceCount,scenario','Malformed collective construction');
 assert.equal(p.family,'collective-trigger');assert([0,1].includes(p.owner));assert.equal(p.resourceCount,24);
 assert.equal(p.leaderCode,'SOR_014');assert.equal(p.enemyLeaderCode,'SOR_014');assert.equal(p.baseCode,'SOR_023');assert.equal(p.enemyBaseCode,'SOR_023');assert.deepEqual(p.fillerCodes,fillerCodes);
 assert((p.cardId==='ASH_169'&&p.mode==='draw'&&axeNames.includes(p.scenario))||(p.cardId==='ASH_208'&&p.mode==='attachment'&&sabineNames.includes(p.scenario)),'Unsupported collective source/scenario');return p;
}
function profile(p){
 const n=p.scenario,marine=()=>[U('ownGround','SOR_095'),U('enemyGround','SOR_095','enemy'),U('space','SOR_178')];
 if(p.mode==='draw'){
  const staged=[U('focus',p.cardId)],draw={code:'TWI_175'};
  if(n==='paid-play-draw3')return{units:[],plan:[{code:p.cardId},draw],expectedAdvantages:1,paid:3};
  if(n==='sequential-draw-windows')return{units:staged,plan:[draw,draw],expectedAdvantages:2};
  if(n==='opponent-draw-negative')return{units:staged,plan:[{...draw,owner:'enemy'}],expectedAdvantages:0};
  if(n==='natural-regroup-draw')return{units:staged,plan:[],waitForRegroup:true,expectedAdvantages:1};
  if(n==='empty-deck-fatigue')return{units:staged,plan:[draw],emptyOwnDeck:true,expectedAdvantages:1};
  if(n==='source-gone-before-draw')return{units:staged,plan:[{code:'TWI_226',target:'focus'},draw],expectedAdvantages:0};
  return{units:[...staged,U('enemyFocus',p.cardId,'enemy')],plan:[],waitForRegroup:true,expectedAdvantages:1};
 }
 if(n==='weakness-source-death')return{units:[U('focus',p.cardId,'own',{damage:4,shields:1}),...marine()],plan:[{code:'HMW_097',target:'ownGround'}]};
 const staged=[U('focus',p.cardId),...marine()];
 if(n==='same-action-sequential-attachment-windows')return{units:staged,plan:[{code:'HMW_097',target:'focus'}]};
 if(n.startsWith('shielded-'))return{units:marine().map(u=>n==='shielded-exhausted-ground'&&u.key==='ownGround'?{...u,exhausted:true}:u),plan:[{code:p.cardId}],paid:7};
 if(n==='multi-xp-one-window')return{units:staged,plan:[{code:'IC27_184',target:'focus'}]};
 if(n==='sequential-upgrade-windows'||n==='phase-reset-second-window')return{units:staged,plan:[{code:'IC27_052',target:'focus'},{code:'IC27_052',target:'focus',...(n==='phase-reset-second-window'?{nextRound:true}:{})}]};
 if(n==='other-parent-negative')return{units:staged,plan:[{code:'IC27_184',target:'ownGround'}]};
 if(n==='source-gone-before-attach')return{units:staged,plan:[{code:'TWI_226',target:'focus'},{code:'IC27_184',target:'ownGround'}]};
 return{units:marine(),plan:[{code:p.cardId},{code:p.cardId}],paid:14};
}
function install(c,p,s){
 const t=c.targets;t.events=[];t.prompts=[];t.stopped=false;t.focusSources=t.focus?[t.focus]:[];t.initialReady=c.own.readyResourceCount;t.initialHand=c.own.getCardsInZone('hand').length;t.initialRound=c.eg.round;
 const windows=new Map(),wid=w=>{if(!w)return null;if(!windows.has(w))windows.set(w,windows.size+1);return windows.get(w);};t.windowId=wid;
 const id=x=>x?c.eg.cardId(x.uuid):null;
 for(const name of ['onCardsDrawn','onUpgradeAttached','onTokensCreated','onDamageDealt','onCardPlayed','onCardDefeated','onCardExhausted','onUpgradeUnattached'])c.eg.game.on(name,e=>{
  if(t.stopped)return;
  const contexts=[];for(let w=c.eg.game.currentEventWindow;w;w=w.parentWindow)for(const ctx of w._triggeredAbilityWindow?.triggeredAbilities??[])if(t.focusSources.includes(ctx.source)||ctx.source===t.enemyFocus)contexts.push({source:id(ctx.source),sourceZone:ctx.source.zoneName,player:c.eg.seatOf(ctx.player.id),ability:ctx.ability.uuid,title:ctx.ability.getTitle(ctx),event:ctx.event?.eventId,eventWindow:wid(ctx.event?.window),triggerWindow:wid(w)});
  t.events.push({resolved:e.isResolved,cancelled:e.isCancelledOrReplaced,sourceZone:e.context?.source?.zoneName??null,lastKnown:e.lastKnownInformation?{card:id(e.lastKnownInformation.card),controller:c.eg.seatOf(e.lastKnownInformation.controller.id),arena:e.lastKnownInformation.arena,power:e.lastKnownInformation.power??null,hp:e.lastKnownInformation.hp??null,damage:e.lastKnownInformation.damage??null,upgrades:e.lastKnownInformation.upgrades?.map(id)??null,parent:id(e.lastKnownInformation.parentCard)}:null,name,id:e.eventId,window:wid(e.window),round:c.eg.round,phase:c.eg.game.currentPhase,source:id(e.context?.source),triggerEvent:e.context?.event?.eventId??null,triggerEventWindow:wid(e.context?.event?.window),contextTitle:e.context?.ability?.getTitle(e.context)??null,collective:e.context?.ability?.collectiveTrigger??null,contextPlayer:e.context?.player?c.eg.seatOf(e.context.player.id):null,player:e.player?c.eg.seatOf(e.player.id):null,card:id(e.card),parent:id(e.parentCard),upgrade:id(e.upgradeCard),amount:e.amount??null,cards:e.cards?.map(id)??null,tokenType:e.tokenType??null,generated:(e.generatedTokens??[]).map(token=>({id:id(token),owner:c.eg.seatOf(token.owner.id),controller:c.eg.seatOf(token.controller.id),name:token.internalName})),contexts});
 });
}
const advantages=c=>c.targets.focus.isInPlay()?c.targets.focus.upgrades.filter(u=>u.internalName==='advantage'):[];
function verify(c,p,s){
 const t=c.targets,f=t.focus,id=x=>c.eg.cardId(x.uuid),events=t.events,owner=c.eg.seatOf(c.own.id),fids=t.focusSources.map(id);
 const draws=events.filter(e=>e.name==='onCardsDrawn'),grants=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='advantage'&&fids.includes(e.source));
 if(p.mode==='draw'){
  assert.equal(advantages(c).length,s.expectedAdvantages);
  assert.equal(grants.length,s.expectedAdvantages,'One Advantage creation per eligible draw window');
  for(const grant of grants){assert.equal(grant.amount,1);assert.deepEqual(grant.cards,[id(f)]);assert.equal(grant.generated.length,1);assert.equal(grant.generated[0].owner,owner);assert.equal(grant.generated[0].controller,owner);assert.equal(grant.contextPlayer,owner);assert.equal(grant.collective,true);assert.equal(grant.contextTitle,'Give an Advantage token to '+f.title);const draw=draws.find(d=>d.id===grant.triggerEvent);assert(draw,'Grant retains actual originating draw event');assert.equal(draw.player,owner);assert.equal(draw.window,grant.triggerEventWindow);}
  if(p.scenario==='paid-play-draw3'||p.scenario==='sequential-draw-windows'){const ownDraws=draws.filter(e=>e.player===owner);assert.equal(ownDraws.length,s.expectedAdvantages);assert(ownDraws.every(e=>e.amount===3&&e.cards.length===3));assert.equal(new Set(ownDraws.map(e=>e.window)).size,ownDraws.length);}
  if(p.scenario==='opponent-draw-negative'){assert.equal(draws.length,1);assert.notEqual(draws[0].player,owner);assert.equal(draws[0].cards.length,3);}
  if(p.scenario==='natural-regroup-draw'||p.scenario==='both-owners-regroup'){assert.equal(c.eg.round,t.initialRound+1);assert(draws.some(e=>e.player===owner&&e.amount===2&&e.cards.length===2&&e.phase==='regroup'));}
  if(p.scenario==='empty-deck-fatigue'){assert.equal(draws.length,1);assert.equal(draws[0].amount,3);assert.deepEqual(draws[0].cards,[]);assert.equal(c.own.base.damage,9);}
  if(p.scenario==='source-gone-before-draw'){assert.equal(f.zoneName,'hand');assert.equal(draws.length,1);assert.equal(draws[0].cards.length,3);}
  if(p.scenario==='both-owners-regroup'){const other=t.enemyFocus,otherGrants=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='advantage'&&e.source===id(other));assert.equal(other.upgrades.filter(u=>u.internalName==='advantage').length,1);assert.equal(otherGrants.length,1);assert.equal(otherGrants[0].contextPlayer,c.eg.seatOf(c.enemy.id));assert.notEqual(otherGrants[0].source,id(f));assert(t.prompts.some(pr=>/Both players have triggered/.test(pr.title)));}
 }else{
  const prompts=t.prompts.filter(pr=>pr.title==='Exhaust a ground unit'&&pr.actions.some(a=>a.kind==='card'));
  const attachments=events.filter(e=>e.name==='onUpgradeAttached'&&fids.includes(e.parent));
  for(const pr of prompts){assert.equal(pr.actor,owner);assert.deepEqual(pr.actions.filter(a=>a.kind==='card').map(a=>a.card).sort(),[...pr.expectedGroundIds].sort(),'Complete own/enemy ground domain including exhausted candidates');assert.equal(pr.actions.filter(a=>a.arg==='passAbility').length,1);assert(!pr.actions.some(a=>/cancel/i.test(a.label??'')));assert(pr.actions.every(a=>a.kind!=='card'||!pr.spaceIds.includes(a.card)),'Space excluded from exact target domain');}
  const n=p.scenario;
  if(n==='weakness-source-death'){
   assert.equal(f.zoneName,'discard');assert.equal(t.enemyGround.exhausted,true);assert.equal(t.ownGround.exhausted,false);
   assert.equal(prompts.length,1);assert.equal(prompts[0].source,id(f));
   const weak=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='weakness');assert.equal(weak.length,1);assert.equal(weak[0].amount,1);assert.deepEqual(weak[0].cards,[id(f)]);assert.equal(weak[0].generated.length,1);assert.equal(weak[0].generated[0].owner,owner);assert.equal(weak[0].generated[0].controller,owner);assert.equal(weak[0].generated[0].name,'weakness');
   const weaknessId=weak[0].generated[0].id,shieldId=t.weaknessInitial.shield;
   const attach=events.find(e=>e.name==='onUpgradeAttached'&&e.upgrade===weaknessId);assert(attach&&attach.resolved&&!attach.cancelled);assert.equal(attach.parent,id(f));assert.equal(prompts[0].event,attach.id);assert.equal(prompts[0].eventWindow,attach.window);
   const dead=events.find(e=>e.name==='onCardDefeated'&&e.card===id(f));assert(dead);assert.equal(dead.lastKnown.card,id(f));assert.equal(dead.lastKnown.controller,owner);assert.equal(dead.lastKnown.hp,4);assert.equal(dead.lastKnown.damage,4);assert(dead.lastKnown.upgrades.includes(shieldId));assert(dead.lastKnown.upgrades.includes(weaknessId));
   assert(dead.contexts.some(ctx=>ctx.source===id(f)&&ctx.sourceZone==='discard'&&ctx.player===owner&&ctx.event===attach.id&&ctx.title==='Exhaust a ground unit'),'Actual resolved attachment context survives source defeat');
   const exhaust=events.find(e=>e.name==='onCardExhausted'&&e.source===id(f));assert(exhaust);assert.equal(exhaust.card,id(t.enemyGround));assert.equal(exhaust.sourceZone,'discard');assert.equal(exhaust.contextPlayer,owner);assert(events.indexOf(exhaust)>events.indexOf(dead));
   const cleanup=events.filter(e=>e.name==='onCardDefeated'&&[id(f),shieldId,weaknessId].includes(e.card));assert.deepEqual(cleanup.map(e=>e.card),[weaknessId,shieldId,id(f)],'Pinned complete attachment cleanup order precedes committed parent defeat');
   for(const tokenId of [shieldId,weaknessId])assert.equal(c.eg.game.allCards.find(card=>id(card)===tokenId).zoneName,'outsideTheGame');
   const dire=events.find(e=>e.name==='onCardPlayed'&&e.card!==id(f));assert(dire);const physicalDire=c.eg.game.allCards.find(card=>id(card)===dire.card);assert(matches(physicalDire,'HMW_097'));assert.equal(physicalDire.parentCard,t.ownGround);assert.equal(physicalDire.owner,c.own);assert.equal(physicalDire.controller,c.own);assert.equal(t.ownGround.getPower(),4);assert.equal(t.ownGround.getHp(),4);assert(events.some(e=>e.name==='onUpgradeAttached'&&e.parent===id(t.ownGround)&&e.upgrade===dire.card));assert.equal(t.weaknessInitial.ready-c.own.readyResourceCount,4,'Actual paid Dire Prowess includes missing vigilance aspect');
   c.observed.weaknessBoundary={initial:t.weaknessInitial,weaknessId,shieldId,attachmentEvent:attach.id,capturedExhaustSource:id(f),cleanup:cleanup.map(e=>e.card)};
  }else if(n==='same-action-sequential-attachment-windows'){
   assert.equal(f.zoneName,'groundArena');assert.equal(f.getHp(),5);assert.equal(f.getPower(),4);assert.equal(f.damage,0);assert.equal(f.upgrades.length,2);assert.equal(t.ownGround.exhausted,true);assert.equal(t.enemyGround.exhausted,true);
   assert.equal(attachments.length,2);assert.equal(new Set(attachments.map(e=>e.window)).size,2,'One paid play produces two actual sequential attachment windows');assert.equal(prompts.length,2);assert.equal(new Set(prompts.map(pr=>pr.ability)).size,1);assert(prompts.every(pr=>pr.source===id(f)));
   const weak=events.find(e=>e.name==='onTokensCreated'&&e.tokenType==='weakness');assert(weak);assert.equal(weak.generated.length,1);assert.equal(weak.generated[0].owner,owner);const weaknessAttach=attachments.find(e=>e.upgrade===weak.generated[0].id),ordinaryAttach=attachments.find(e=>e!==weaknessAttach);assert(weaknessAttach&&ordinaryAttach);assert.equal(prompts[0].event,weaknessAttach.id);assert.equal(prompts[1].event,ordinaryAttach.id);assert.notEqual(prompts[0].eventWindow,prompts[1].eventWindow);assert(t.prompts.some(pr=>pr.chosen.label==='Give a Weakness token to a unit'),'Actual combined trigger menu chooses DireProwess WP before outer Sabine exhaust');
   const played=events.filter(e=>e.name==='onCardPlayed');assert.equal(played.length,1);assert.equal(t.initialReady-c.own.readyResourceCount,4,'Actual one paid Dire Prowess play');const dire=c.eg.game.allCards.find(card=>id(card)===played[0].card);assert(matches(dire,'HMW_097'));assert.equal(ordinaryAttach.upgrade,id(dire));assert.equal(dire.parentCard,f);
   const exhausted=events.filter(e=>e.name==='onCardExhausted'&&e.source===id(f));assert.equal(exhausted.length,2);assert.deepEqual(exhausted.map(e=>e.card),[id(t.enemyGround),id(t.ownGround)]);c.observed.sameActionWindows={ordinary:ordinaryAttach.window,weakness:weaknessAttach.window,resolutionOrder:prompts.map(pr=>pr.eventWindow),paidPlays:played.map(e=>e.card)};
  }else if(n.startsWith('shielded-')){
   assert.equal(f.upgrades.filter(u=>u.internalName==='shield').length,1,'Native normal-play Shielded creates one real Shield');
   assert.equal(attachments.length,1);assert.equal(prompts.length,1);
   if(n==='shielded-play-own-ground')assert(t.ownGround.exhausted);
   if(n==='shielded-play-enemy-ground')assert(t.enemyGround.exhausted);
   if(n==='shielded-decline'||n==='shielded-space-negative'){assert.equal(t.ownGround.exhausted,false);assert.equal(t.enemyGround.exhausted,false);assert(prompts[0].chosen.arg==='passAbility'||prompts[0].chosen.label==='Pass');}
   if(n==='shielded-exhausted-ground'){assert.equal(t.ownGround.exhausted,true);assert.equal(t.enemyGround.exhausted,false);assert.equal(prompts[0].chosen.card,id(t.ownGround));}
  }else if(n==='multi-xp-one-window'){
   assert.equal(attachments.length,2);assert.equal(new Set(attachments.map(e=>e.window)).size,1,'Both actual XP attachment events share the same real event window');assert.equal(prompts.length,1,'Collective ability resolves once for two attachment events');
   const uniqueContexts=[...new Map(attachments.flatMap(e=>e.contexts).filter(ctx=>ctx.source===id(f)&&ctx.eventWindow===attachments[0].window).map(ctx=>[ctx.ability+':'+ctx.event,ctx])).values()];assert.equal(uniqueContexts.length,2,'Two captured contexts, ignoring repeated parent-window references');assert.equal(new Set(uniqueContexts.map(ctx=>ctx.ability)).size,1);assert.equal(prompts[0].event,uniqueContexts[0].event,'Collective reduction preserves first captured context');assert.equal(prompts[0].eventWindow,attachments[0].window);assert.equal(prompts[0].source,id(f));
   assert.equal(f.upgrades.filter(u=>u.internalName==='experience').length,2);assert.equal(f.getPower(),6);assert.equal(f.getHp(),7);assert.equal(f.damage,2);assert(t.enemyGround.exhausted);
   const xp=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='experience');assert.equal(xp.length,1);assert.equal(xp[0].generated.length,2);assert.deepEqual(xp[0].cards,[id(f)]);assert(xp[0].generated.every(x=>x.owner===owner&&x.controller===owner));
  }else if(n==='sequential-upgrade-windows'||n==='phase-reset-second-window'){
   assert.equal(attachments.length,2);assert.equal(new Set(attachments.map(e=>e.window)).size,2);assert.equal(prompts.length,2);assert.equal(f.getHp(),11);
   if(n==='phase-reset-second-window'){assert.equal(c.eg.round,t.initialRound+1);assert.notEqual(attachments[0].round,attachments[1].round);}else assert.equal(attachments[0].round,attachments[1].round);
  }else if(n==='other-parent-negative'||n==='source-gone-before-attach'){assert.equal(attachments.length,0);assert.equal(prompts.length,0);assert.equal(t.ownGround.upgrades.filter(u=>u.internalName==='experience').length,2);if(n==='source-gone-before-attach')assert.equal(f.zoneName,'hand');}
  else{
   const old=t.focusSources[0],incoming=t.focusSources[1],survivor=n==='unique-keep-old'?old:incoming,dead=survivor===old?incoming:old;assert.notEqual(old.uuid,incoming.uuid);assert.equal(survivor.zoneName,'groundArena');assert.equal(dead.zoneName,'discard');assert.equal(survivor.upgrades.filter(u=>u.internalName==='shield').length,1);assert.equal(prompts.length,n==='unique-keep-old'?1:2);assert.equal(attachments.length,n==='unique-keep-old'?1:2);assert(attachments.every(e=>e.source===e.parent),'Each native Shielded attachment uses the same physical source/parent');if(n==='unique-keep-old')assert(events.some(e=>e.name==='onCardDefeated'&&e.card===id(dead)&&e.contexts.some(ctx=>ctx.source===id(dead)&&ctx.sourceZone==='discard'&&ctx.player===owner&&ctx.title==='Shielded')),'Defeated incoming source retains captured Shielded context without ghost attachment');
  }
 }
 if(s.paid){const focusPlays=events.filter(e=>e.name==='onCardPlayed'&&fids.includes(e.card));assert.equal(focusPlays.length,p.scenario.startsWith('unique-')?2:1);assert.equal(t.paidFocus,s.paid,'Actual focus-only ordinary printed/aspect cost');}
 c.observed.focus={id:id(f),zone:f.zoneName,power:f.isInPlay()?f.getPower():null,hp:f.isInPlay()?f.getHp():null,upgrades:f.isInPlay()?f.upgrades.map(u=>({id:id(u),name:u.internalName,owner:c.eg.seatOf(u.owner.id)})):[]};c.observed.events=events.slice();c.observed.prompts=t.prompts.slice();c.observed.rawProbe=JSON.parse(JSON.stringify(p));t.stopped=true;
}
function makeScenario(p,scenario){
 const s=profile(p),n=p.scenario;return{...s,name:scenario.name??n+'-seat'+p.owner,seat:p.owner,family:p.family,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes:p.fillerCodes,baseDamage:0,
 setup:c=>install(c,p,s),
 beforeWindow(c){const t=c.targets;if(c.atWindow&&t.focusPlayBefore!==undefined){t.paidFocus=(t.paidFocus??0)+(t.focusPlayBefore-c.own.readyResourceCount);delete t.focusPlayBefore;}},
 beforeApply(c){if(p.scenario==='weakness-source-death'&&c.atWindow&&c.pid===c.own.id&&!c.targets.weaknessInitial){const f=c.targets.focus;assert.equal(f.damage,4);assert.equal(f.getHp(),5);assert.equal(f.upgrades.filter(u=>u.internalName==='shield').length,1);c.targets.weaknessInitial={source:c.eg.cardId(f.uuid),damage:f.damage,hp:f.getHp(),shield:c.eg.cardId(f.upgrades[0].uuid),ready:c.own.readyResourceCount,owner:c.eg.seatOf(f.owner.id),controller:c.eg.seatOf(f.controller.id),construction:'Disclosed initial4wounds and generated nativeShield; not a paid-wounds or paidShielded claim'};}if(c.atWindow&&c.pending?.code===p.cardId&&c.pid===c.own.id&&c.scratch.incoming&&!c.targets.focusSources.includes(c.scratch.incoming)){c.targets.focus??=c.scratch.incoming;c.targets.focusSources.push(c.scratch.incoming);c.targets.focusPlayBefore=c.own.readyResourceCount;}},
 choose(c){const t=c.targets,title=c.eg.player(c.pid).currentPrompt().menuTitle??'',ctx=c.eg.game.currentAbilityResolver?.context;
  if(title.includes('which copy'))return c.actions.find(a=>a.cardUuid===(n==='unique-keep-incoming'?t.focusSources[0]:t.focusSources[1])?.uuid);
  if(n==='same-action-sequential-attachment-windows'&&c.actions.some(a=>a.label==='Give a Weakness token to a unit')){const chosen=c.actions.find(a=>a.label==='Give a Weakness token to a unit');t.prompts.push({step:c.step,title,actor:c.eg.seatOf(c.pid),actions:c.actions.map(a=>canonicalAction(c.eg,a)),chosen:canonicalAction(c.eg,chosen)});return chosen;}
  if((n==='weakness-source-death'||n==='same-action-sequential-attachment-windows')&&title==='Give a Weakness token to a unit'){const chosen=c.actions.find(a=>a.cardUuid===t.focus.uuid);assert(chosen,'Physical Sabine must be legal optional Weakness target');return chosen;}
  if(title==='Exhaust a ground unit'&&c.actions.some(a=>a.kind==='card')){
   let chosen;if(n==='shielded-decline'||n==='shielded-space-negative')chosen=c.actions.find(a=>a.arg==='passAbility');
   else{const target=(n==='shielded-play-own-ground'||n==='shielded-exhausted-ground'||(n==='same-action-sequential-attachment-windows'&&t.prompts.filter(pr=>pr.title==='Exhaust a ground unit').length===1))?t.ownGround:t.enemyGround;chosen=c.actions.find(a=>a.cardUuid===target?.uuid);}
   assert(chosen,'Actual requested optional exhaustion choice must be legal');t.prompts.push({step:c.step,title,actor:c.eg.seatOf(c.pid),source:ctx?.source?c.eg.cardId(ctx.source.uuid):null,ability:ctx?.ability?.uuid??null,event:ctx?.event?.eventId??null,eventWindow:t.windowId(ctx?.event?.window),spaceIds:[t.space].filter(Boolean).map(x=>c.eg.cardId(x.uuid)),expectedGroundIds:c.eg.game.getArenaUnits().filter(x=>x.zoneName==='groundArena').map(x=>c.eg.cardId(x.uuid)),actions:c.actions.map(a=>canonicalAction(c.eg,a)),chosen:canonicalAction(c.eg,chosen)});return chosen;
  }
  if(/Both players have triggered/.test(title)){const chosen=c.actions.find(a=>a.label==='You');t.prompts.push({step:c.step,title,actor:c.eg.seatOf(c.pid),actions:c.actions.map(a=>canonicalAction(c.eg,a)),chosen:canonicalAction(c.eg,chosen)});return chosen;}
  if(title==='You may trigger this ability')return c.actions.find(a=>a.arg==='trigger');
  return c.pending?.target?c.actions.find(a=>a.cardUuid===t[c.pending.target]?.uuid):undefined;
 },assertAfter:c=>verify(c,p,s)};
}
async function fixture(env,pool,scenario,seed){const p=validateProbe(scenario.probe),game=await tokenFixture(env,pool,makeScenario(p,scenario),seed);game.records[0].constructionParameters.rawProbe=JSON.parse(JSON.stringify(p));game.records[0].fixtureConstruction='At first natural action window, stage declared actual units, move declared script cards into their actual acting-owner hand, place up to24 remaining deck cards as resources and ready existing resources, set bases damage0. Empty-deck draw variant additionally stages own remaining deck in discard. No later state edits; all script, regroup and committed post-winner choices are legal engine inputs. Read-only event-window IDs are object identities, not action counters.';game.witness.rawProbe=JSON.parse(JSON.stringify(p));game.witness.coverageObligationIds=[...(scenario.coverageObligationIds??[])];return game;}
module.exports={fixture,validateProbe,dependencies:['kessel:cards/pipeline/collective-trigger-probes.js','lab/kessel-reference/pipeline/collective-trigger-probe-fixture.js','lab/kessel-reference/pipeline/terminal-completion.js','engine/env.js','engine/rng.js','bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/unit-entry-state.js','bots/omni/rs/support-state.js','bots/players/index.js','bots/players/random.js']};
