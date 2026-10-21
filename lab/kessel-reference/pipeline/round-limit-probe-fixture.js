'use strict';
// Source-engine oracle only. Limits are actual registration/player counters.
const assert=require('node:assert/strict');
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
    const codes = [...new Set([...(scenario.units ?? plain).map((u) => u.code), ...scenario.plan.filter((s) => s.from !== 'leader'&&s.from !== 'enemyLeader').map((s) => s.code), ...(scenario.extraCodes ?? [])])];
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
    require('../../../bots/omni/rs/inactive-phase-keyword-state').observeInactivePhaseKeywords(eg);
    await eg.start();
    while (!eg.ids.some((pid) => eg.isActionWindow(pid))) {
        const pid = eg.ids.find((id) => eg.legalActions(id).length), actions = expandActions(eg, eg.legalActions(pid));
        const initiativeChoice = scenario.initiative && actions.find(a => a.label === (pid === eg.ids[scenario.initiative === 'own' ? 0 : 1] ? 'Yourself' : 'Opponent'));
        eg.apply(pid, initiativeChoice ?? bot.choose({ game: eg, pid, actions, rng }), rng);
    }
    const own = eg.player(eg.ids[scenario.seat]), enemy = eg.player(eg.ids[1-scenario.seat]), targets = { ownBase: own.base, enemyBase: enemy.base };
    targets.leader = own.getAllDeckLeaders()[0];targets.enemyLeader=enemy.getAllDeckLeaders()[0];
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
                    Object.assign(observed,ctx.observed);
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
            chosen ??= actions.find(a=>/play anyway/i.test(a.label??''));
            const completionActions=targets.stopped?actions.filter(a=>{const card=a.cardUuid&&eg.game.allCards.find(c=>c.uuid===a.cardUuid);return !(card?.zoneName==='hand'&&card.cardData?.keywords?.includes('support'));}):actions;
            chosen ??= bot.choose({ game: eg, pid, actions:completionActions, rng });
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
            const finalContext={ eg, own, enemy, targets, observed, scratch, initialState };
            scenario.assertAfter(finalContext);
            Object.assign(observed,finalContext.observed);
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
const modes={ASH_047:'played-upgrade',ASH_032:'nonlethal-damage',ASH_160:'enemy-ground-attack',HMW_062:'enemy-weakness-defeat',SOR_115:'other-unique-defeat'};
const names={
 ASH_047:['paid-first-second','decline-then-use','round-reset','reentry','token-other-host-negative','enemy-play-negative','opposing-copies'],
 ASH_032:['bases-both','bases-own','bases-enemy','bases-none','lethal-negative','shield-then-survive','enemy-then-friendly','multiple-copies-round-reset'],
 ASH_160:['paid-hidden-first-second-round-reset','predicate-negatives','already-ready-no-consume','multiple-copies'],
 HMW_062:['paid-wp-first-second-death','decline-then-use','round-reset','predicate-negatives','captured-source-cinder-death'],
 SOR_115:['paid-ambush-first-second','draw-decline-then-use','round-reset','nonunique-then-captured-mass-death','ambush-no-target','ambush-decline','self-death-negative']
};
function validateProbe(p){if(p&&Object.hasOwn(p,'interaction'))return require('./round-limit-interaction-fixture').validateProbe(p);assert(p&&Object.keys(p).sort().join(',')==='baseCode,cardId,enemyBaseCode,enemyLeaderCode,family,fillerCodes,leaderCode,mode,owner,resourceCount,scenario','Malformed round-limit construction');assert.equal(p.family,'round-limit');assert([0,1].includes(p.owner));assert.equal(p.mode,modes[p.cardId]);assert(names[p.cardId]?.includes(p.scenario),'Unsupported round-limit source scenario');assert.equal(p.resourceCount,24);assert.equal(p.leaderCode,'SOR_014');assert.equal(p.enemyLeaderCode,'SOR_014');assert.equal(p.baseCode,'SOR_023');assert.equal(p.enemyBaseCode,'SOR_023');assert.deepEqual(p.fillerCodes,fillerCodes);return p;}
function profile(p){
 const n=p.scenario,F=()=>U('focus',p.cardId),W=key=>U(key,'LOF_164'),fire=key=>({code:'TWI_174',target:key}),kill=key=>({code:'TWI_077',target:key}),upgrade={code:'IC27_052',target:'focus'};
 if(p.cardId==='ASH_047'){
  if(n==='paid-first-second')return{units:[],plan:[{code:p.cardId},upgrade,upgrade],mandos:1};
  if(n==='round-reset')return{units:[F()],plan:[upgrade,upgrade,{...upgrade,nextRound:true}],mandos:2};
  if(n==='reentry')return{units:[F()],plan:[upgrade,{code:'TWI_226',target:'focus'},{code:p.cardId,from:'focus'},upgrade],mandos:2};
  if(n==='token-other-host-negative')return{units:[F(),U('ownGround','SOR_095')],plan:[{code:'IC27_184',target:'focus'},{...upgrade,target:'ownGround'},upgrade],mandos:1};
  if(n==='enemy-play-negative')return{units:[F()],plan:[{...upgrade,owner:'enemy'},upgrade],mandos:1};
  if(n==='opposing-copies')return{units:[F(),U('otherFocus',p.cardId,'enemy')],plan:[upgrade,{...upgrade,target:'otherFocus',owner:'enemy'}],mandos:1,enemyMandos:1};
  return{units:[F()],plan:[upgrade,upgrade],mandos:1};
 }
 if(p.cardId==='ASH_032'){
  if(n==='lethal-negative')return{units:[F(),U('victim','SOR_095')],plan:[fire('victim')],baseDamage:0};
  if(n==='shield-then-survive')return{units:[F(),U('victim','LOF_164','own',{shields:1})],plan:[fire('victim'),fire('victim')],baseDamage:1};
  if(n==='enemy-then-friendly')return{units:[F(),W('victim'),U('enemyVictim','LOF_164','enemy')],plan:[fire('enemyVictim'),fire('victim')],baseDamage:1};
  if(n==='multiple-copies-round-reset')return{units:[F(),U('otherFocus',p.cardId),W('victim'),W('victim2'),W('victim3')],plan:[fire('victim'),fire('victim2'),{...fire('victim3'),nextRound:true}],baseDamage:4};
  return{units:[F(),W('victim'),W('victim2')],plan:[fire('victim'),fire('victim2')],baseDamage:n==='bases-none'?0:1};
 }
 if(p.cardId==='ASH_160'){
  const A=U('attacker','SOR_095','enemy'),B=U('attacker2','SOR_095','enemy'),attack=(from,target,owner='enemy',nextRound=false)=>({code:from==='focus'?p.cardId:from==='space'?'SOR_178':'SOR_095',from,target,owner,...(nextRound?{nextRound:true}:{})});
  if(n==='paid-hidden-first-second-round-reset')return{units:[A,B],plan:[{code:p.cardId},attack('attacker','ownBase'),attack('focus','enemyBase','own'),attack('attacker2','ownBase'),attack('focus','enemyBase','own',true),attack('attacker','ownBase','enemy',true)],ready:true};
  if(n==='predicate-negatives')return{units:[U('focus',p.cardId,'own',{exhausted:true}),A,B,U('space','SOR_178','enemy'),W('victim'),U('ownGround','SOR_095')],plan:[attack('space','ownBase'),attack('attacker','victim'),attack('ownGround','enemyBase','own'),attack('attacker2','ownBase')],ready:true};
  if(n==='already-ready-no-consume')return{units:[F(),A,B],plan:[attack('attacker','ownBase'),attack('focus','enemyBase','own'),attack('attacker2','ownBase')],ready:true};
  return{units:[U('focus',p.cardId,'own',{exhausted:true}),U('otherFocus',p.cardId,'own',{exhausted:true}),A],plan:[attack('attacker','ownBase')],ready:true};
 }
 if(p.cardId==='HMW_062'){
  const V=(key,owner='enemy',weakness=1)=>U(key,'LOF_164',owner,{weakness});
  if(n==='paid-wp-first-second-death')return{units:[V('victim','enemy',0),V('victim2','enemy',0),U('ownGround','SOR_095')],plan:[{code:p.cardId},kill('victim'),kill('victim2')],weaknessGrants:2};
  if(n==='round-reset')return{units:[F(),V('victim'),V('victim2'),V('victim3'),U('ownGround','SOR_095')],plan:[kill('victim'),kill('victim2'),{...kill('victim3'),nextRound:true}],weaknessGrants:2};
  if(n==='predicate-negatives')return{units:[F(),V('friendly','own'),V('unweak','enemy',0),V('victim'),U('ownGround','SOR_095')],plan:[kill('friendly'),kill('unweak'),kill('victim')],weaknessGrants:1};
  if(n==='captured-source-cinder-death')return{units:[F(),V('victim'),U('ownGround','ASH_131')],plan:[{code:'ASH_151'}],weaknessGrants:1};
  return{units:[F(),V('victim'),V('victim2'),U('ownGround','SOR_095')],plan:[kill('victim'),kill('victim2')],weaknessGrants:1};
 }
 const uniques=[U('ownUnique','ASH_036'),U('enemyUnique','ASH_036','enemy')];
 if(n==='paid-ambush-first-second')return{units:uniques,plan:[{code:p.cardId},kill('enemyUnique'),kill('ownUnique')],draws:1,ambushTarget:'enemyUnique'};
 if(n==='ambush-no-target')return{units:[],plan:[{code:p.cardId}],draws:0};
 if(n==='ambush-decline')return{units:[U('enemyVictim','SOR_095','enemy')],plan:[{code:p.cardId}],draws:0};
 if(n==='round-reset')return{units:[F(),...uniques,U('snoke','SHD_037','enemy')],plan:[kill('enemyUnique'),kill('ownUnique'),{...kill('snoke'),nextRound:true}],draws:2};
 if(n==='nonunique-then-captured-mass-death')return{units:[F(),U('ownUnique','ASH_036'),U('enemyVictim','SOR_095','enemy')],plan:[kill('enemyVictim'),{code:'SOR_043'}],draws:1};
 if(n==='self-death-negative')return{units:[F()],plan:[kill('focus')],draws:0};
 return{units:[F(),...uniques],plan:[kill('enemyUnique'),kill('ownUnique')],draws:1};
}
function limits(c){const out=[];for(const source of c.targets.sources)for(const ability of source.getTriggeredAbilities())if(ability.limit?.max===1){const l=ability.limit;out.push({source:c.eg.cardId(source.uuid),zone:source.zoneName,inPlayId:source.isInPlay()?source.inPlayId:null,ability:ability.uuid,limit:l.uuid,uses:c.eg.ids.map(pid=>l.currentForPlayer(c.eg.player(pid)))});}return out;}
function setup(c,p){const t=c.targets;t.sources=t.focus?[t.focus]:[];if(t.otherFocus)t.sources.push(t.otherFocus);t.events=[];t.prompts=[];t.samples=[];t.stopped=false;t.playChecks=[];t.pendingPlay=null;t.firstRound=c.eg.round;t.optionalAttempts=0;
 for(const unit of profile(p).units)for(let i=0;i<(unit.weakness??0);i++){const host=t[unit.key];c.eg.game.generateToken(host.controller,'weakness').attachTo(host);}
 const id=x=>x?c.eg.cardId(x.uuid):null,wids=new Map(),wid=w=>{if(!w)return null;if(!wids.has(w))wids.set(w,wids.size+1);return wids.get(w);};t.wid=wid;
 for(const name of ['onCardPlayed','onTokensCreated','onUpgradeAttached','onDamageDealt','onCardDefeated','onCardsDrawn','onAttackDeclared','onCardReadied','onPhaseEnded','onRoundEnded'])c.eg.game.on(name,e=>{if(t.stopped)return;const ctx=e.context,limit=ctx?.getProps?.().limit;t.events.push({name,id:e.eventId,window:wid(e.window),round:c.eg.round,phase:c.eg.game.currentPhase,eventPhase:e.phase??null,card:id(e.card),cardZone:e.card?.zoneName??null,player:e.player?c.eg.seatOf(e.player.id):null,source:id(ctx?.source),sourceZone:ctx?.source?.zoneName??null,contextPlayer:ctx?.player?c.eg.seatOf(ctx.player.id):null,ability:ctx?.ability?.uuid??null,limit:limit?.uuid??null,limited:limit?.max===1,triggerEvent:ctx?.event?.eventId??null,amount:e.amount??null,damageDealt:e.damageDealt??null,willDefeat:e.willDefeat??null,attachTarget:id(e.attachTarget),parent:id(e.parentCard),upgrade:id(e.upgradeCard),tokenType:e.tokenType??null,cards:e.cards?.map(id)??null,generated:(e.generatedTokens??[]).map(card=>({id:id(card),name:card.internalName,owner:c.eg.seatOf(card.owner.id),controller:c.eg.seatOf(card.controller.id)})),lki:e.lastKnownInformation?{card:id(e.lastKnownInformation.card),controller:c.eg.seatOf(e.lastKnownInformation.controller.id),type:e.lastKnownInformation.type,hp:e.lastKnownInformation.hp,damage:e.lastKnownInformation.damage,upgrades:e.lastKnownInformation.upgrades?.map(u=>({id:id(u),weakness:u.isWeakness()}))??null}:null,attacker:e.attack?{card:id(e.attack.attacker),controller:e.attackerLastKnownInformation?c.eg.seatOf(e.attackerLastKnownInformation.controller.id):null,arena:e.attackerLastKnownInformation?.arena??null,targets:e.attack.getAllTargets().map(id)}:null,counters:limits(c)});});
}
function payment(card){const available={aggression:1,heroism:1,command:1},need={};let extra=0;for(const a of card.cardData.aspects??[])if((need[a]=(need[a]??0)+1)>(available[a]??0))extra+=2;return card.cost+extra;}
function checkPendingPlay(c){const t=c.targets,play=t.pendingPlay;if(!play)return;const event=t.events.find(e=>e.name==='onCardPlayed'&&e.card===play.id);assert(event,'Every planned play must emit actual onCardPlayed, never silently cancel');assert.equal(event.player,c.eg.seatOf(play.owner.id));assert.equal(play.ready-play.owner.readyResourceCount,play.cost,'Actual printed/aspect payment before advancing planned play');const card=play.card;assert.equal(card.zoneName,card.isEvent()?'discard':card.cardData.arena==='space'?'spaceArena':'groundArena','Played physical card reaches appropriate actual zone');if(card.isUpgrade()){assert(card.parentCard);assert.equal(c.eg.cardId(card.parentCard.uuid),c.eg.cardId(c.targets[play.target].uuid));}t.playChecks.push({id:play.id,code:play.code,event:event.id,paid:play.cost,zone:card.zoneName,owner:c.eg.seatOf(play.owner.id)});t.pendingPlay=null;}
function makeScenario(p,scenario){const s=profile(p),n=p.scenario;return{...s,name:scenario.name??n+'-seat'+p.owner,seat:p.owner,family:p.family,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes:p.fillerCodes,baseDamage:0,
 setup:c=>setup(c,p),beforeWindow(c){if(c.atWindow){checkPendingPlay(c);c.targets.samples.push({index:c.index,round:c.eg.round,focusExhausted:c.targets.focus?.isInPlay()?c.targets.focus.exhausted:null,ownBase:c.own.base.damage,enemyBase:c.enemy.base.damage,counters:limits(c)});}},
 beforeApply(c){if(!c.atWindow||!c.pending||!c.scratch.incoming||c.chosen.cardUuid!==c.scratch.incoming.uuid)return;const card=c.scratch.incoming;if(card.zoneName!=='hand')return;const t=c.targets;if(matches(card,p.cardId)&&!t.sources.includes(card)){t.focus??=card;t.sources.push(card);}const actor=card.controller;t.pendingPlay={card,id:c.eg.cardId(card.uuid),code:c.pending.code,target:c.pending.target,owner:actor,ready:actor.readyResourceCount,cost:payment(card)};},
 choose(c){const t=c.targets,title=c.eg.player(c.pid).currentPrompt().menuTitle??'',ctx=c.eg.game.currentAbilityResolver?.context,captured=ctx?.getProps?.().limit,limited=captured?.max===1,isFocus=ctx?.source&&t.sources.includes(ctx.source);let chosen;
  chosen=c.actions.find(a=>/play anyway/i.test(a.label??''));if(chosen)return chosen;
  if(title==='You may trigger this ability'&&p.cardId==='SOR_115'&&n==='ambush-decline'&&t.pendingPlay){chosen=c.actions.find(a=>a.arg==='pass');assert(chosen,'Actual Ambush optional prompt must expose Pass');}
  else if(title==='Choose bases to deal 1 damage to'){
   const desired=n==='bases-none'?[]:n==='bases-own'?[c.own.base]:n==='bases-enemy'?[c.enemy.base]:[c.own.base,c.enemy.base],selected=c.eg.player(c.pid).promptState.selectedCards??[];
   chosen=c.actions.find(a=>desired.some(b=>b.uuid===a.cardUuid)&&!selected.some(b=>b.uuid===a.cardUuid))??c.actions.find(a=>a.arg==='done');assert(chosen,'Complete unlimited base selector must finish without toggling preferred cards');
  }else if(title==='Give a Weakness token to a unit'&&isFocus){
   const skip=n==='decline-then-use'&&limited&&t.optionalAttempts===0;if(skip)chosen=c.actions.find(a=>a.arg==='passAbility');else{let target=t.ownGround;if(!limited&&p.cardId==='HMW_062')target=t.victim;else if(n==='paid-wp-first-second-death')target=t.victim2;chosen=c.actions.find(a=>a.cardUuid===target?.uuid);}t.optionalAttempts++;
  }else if(title==='You may trigger this ability'&&isFocus){
   const ambush=ctx.ability.keyword==='ambush',decline=ambush?n==='ambush-decline':limited&&((n==='decline-then-use'||n==='draw-decline-then-use')&&t.optionalAttempts===0);chosen=c.actions.find(a=>a.arg===(decline?'pass':'trigger')||a.arg===(decline?'passAbility':'trigger'));if(limited)t.optionalAttempts++;
  }else if(/Choose a target for attack/.test(title)){
   const target=c.pending?.target??s.ambushTarget;if(target)chosen=c.actions.find(a=>a.cardUuid===t[target]?.uuid);
   if(p.cardId==='ASH_160'&&n==='paid-hidden-first-second-round-reset'&&c.pid===c.enemy.id){const contains=c.actions.some(a=>a.cardUuid===t.focus.uuid);assert.equal(contains,c.eg.round>t.firstRound,'Native Hidden protects only actual played phase; real later round removes protection');}
  }
  if(!chosen&&/Both players have triggered/.test(title))chosen=c.actions.find(a=>a.label==='You');
  if(chosen)t.prompts.push({step:c.step,title,actor:c.eg.seatOf(c.pid),source:ctx?.source?c.eg.cardId(ctx.source.uuid):null,ability:ctx?.ability?.uuid??null,limit:captured?.uuid??null,limited,usesBefore:captured?.currentForPlayer?.(ctx.player)??null,actions:c.actions.map(a=>canonicalAction(c.eg,a)),chosen:canonicalAction(c.eg,chosen)});
  return chosen??(c.pending?.target?c.actions.find(a=>a.cardUuid===t[c.pending.target]?.uuid):undefined);
 },assertAfter:c=>verify(c,p,s)};}
function verify(c,p,s){
 checkPendingPlay(c);const t=c.targets,f=t.focus,ids=t.sources.map(x=>c.eg.cardId(x.uuid)),id=x=>c.eg.cardId(x.uuid),owner=c.eg.seatOf(c.own.id),effects=t.events.filter(e=>e.limited&&ids.includes(e.source));const live=limits(c).filter(l=>l.source===id(f));
 if(p.cardId==='ASH_047'){
  const made=effects.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='mandalorian');const tokens=c.eg.game.allCards.filter(card=>card.internalName==='mandalorian'&&card.owner===c.own);assert.equal(tokens.length,s.mandos);for(const card of tokens){assert.equal(card.zoneName,'groundArena');const creation=made.find(e=>e.generated.some(x=>x.id===c.eg.cardId(card.uuid)));assert(creation);assert.equal(card.exhausted,creation.round===c.eg.round);assert.equal(card.getPower(),2);assert.equal(card.getHp(),2);assert.equal(card.controller,c.own);assert.equal(card.upgrades.filter(u=>u.internalName==='shield').length,1);assert.equal(card.upgrades[0].owner,c.own);}
  assert.equal(made.filter(e=>e.contextPlayer===owner).length,s.mandos);assert(made.every(e=>e.amount===1));const plays=t.events.filter(e=>e.name==='onCardPlayed'&&e.attachTarget===id(f));if(p.scenario==='token-other-host-negative'){assert.equal(plays.length,1);assert(t.events.some(e=>e.name==='onUpgradeAttached'&&e.parent===id(f)));}if(p.scenario==='enemy-play-negative'){assert(plays.some(e=>e.player!==owner));assert.equal(made.length,1);}if(s.enemyMandos){assert.equal(c.eg.game.allCards.filter(card=>card.internalName==='mandalorian'&&card.owner===c.enemy).length,1);assert.equal(made.length,2);assert.equal(new Set(made.map(e=>e.source)).size,2);}if(p.scenario==='decline-then-use'){assert(t.prompts.some(pr=>pr.chosen.label==='Pass'));assert(t.samples.some(sample=>sample.index===1&&sample.counters.some(l=>l.source===id(f)&&l.uses[p.owner]===0)));}if(p.scenario==='reentry'){const before=t.samples.find(x=>x.index===1).counters.find(l=>l.source===id(f)),after=t.samples.find(x=>x.index===3).counters.find(l=>l.source===id(f));assert.notEqual(before.limit,after.limit);assert.equal(before.uses[p.owner],1);assert.equal(after.uses[p.owner],0);}
 }else if(p.cardId==='ASH_032'){
  const hits=effects.filter(e=>e.name==='onDamageDealt'),n=p.scenario;const ownExpected=n==='bases-enemy'?0:s.baseDamage,enemyExpected=n==='bases-own'?0:s.baseDamage;assert.equal(c.own.base.damage,ownExpected);assert.equal(c.enemy.base.damage,enemyExpected);assert(hits.every(e=>e.amount===1));
  if(n==='lethal-negative'){assert.equal(t.victim.zoneName,'discard');assert(t.events.some(e=>e.name==='onDamageDealt'&&e.card===id(t.victim)&&e.willDefeat===true));assert.equal(hits.length,0);}else{assert(live.length);assert.equal(live[0].uses[p.owner],1);if(n==='bases-none')assert.equal(hits.length,0);}
  if(n==='shield-then-survive'){assert.equal(t.victim.damage,4);assert.equal(t.events.filter(e=>e.name==='onDamageDealt'&&e.card===id(t.victim)).length,1);}if(n==='multiple-copies-round-reset'){assert.equal(new Set(hits.map(e=>e.source)).size,2);assert.equal(hits.length,8);}const basePrompts=t.prompts.filter(pr=>pr.title==='Choose bases to deal 1 damage to');assert(basePrompts.every(pr=>pr.actions.some(a=>a.arg==='done')));
 }else if(p.cardId==='ASH_160'){
  assert.equal(f.exhausted,!s.ready);const ready=effects.filter(e=>e.name==='onCardReadied');assert.equal(ready.length,p.scenario==='multiple-copies'||p.scenario==='paid-hidden-first-second-round-reset'?2:1);assert(ready.every(e=>{const attack=t.events.find(a=>a.id===e.triggerEvent);return attack?.name==='onAttackDeclared'&&attack.attacker.controller!==owner&&attack.attacker.arena==='groundArena'&&attack.attacker.targets.includes(id(c.own.base));}));
  if(p.scenario==='paid-hidden-first-second-round-reset'){assert.equal(t.samples.find(x=>x.index===2).focusExhausted,false);assert.equal(t.samples.find(x=>x.index===4).focusExhausted,true);assert.equal(c.eg.round,t.firstRound+1);}if(p.scenario==='already-ready-no-consume'){assert.equal(t.samples.find(x=>x.index===1).counters.find(l=>l.source===id(f)).uses[p.owner],0);}if(p.scenario==='multiple-copies'){assert.equal(t.otherFocus.exhausted,false);assert.equal(new Set(ready.map(e=>e.source)).size,2);}
 }else if(p.cardId==='HMW_062'){
  const grants=t.events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='weakness'&&e.source===id(f));assert.equal(grants.length,s.weaknessGrants);assert(grants.every(e=>e.amount===1));const restricted=grants.filter(e=>e.limited);assert.equal(restricted.length,p.scenario==='round-reset'?2:1);
  for(const grant of restricted){const death=t.events.find(e=>e.id===grant.triggerEvent);assert(death?.name==='onCardDefeated');assert.notEqual(death.lki.controller,owner);assert(death.lki.upgrades.some(u=>u.weakness));}
  if(p.scenario==='paid-wp-first-second-death')assert.equal(grants.filter(e=>!e.limited).length,1);if(p.scenario==='decline-then-use'){assert(t.prompts.some(pr=>pr.chosen.arg==='passAbility'));assert(t.samples.some(sample=>sample.index===1&&sample.counters.some(l=>l.source===id(f)&&l.uses[p.owner]===0)));}if(p.scenario==='captured-source-cinder-death'){assert.equal(f.zoneName,'discard');assert.equal(restricted[0].sourceZone,'discard');assert.equal(t.ownGround.damage,5);assert.equal(t.ownGround.getHp(),6);}
 }else{
  const draws=effects.filter(e=>e.name==='onCardsDrawn');assert.equal(draws.length,s.draws);assert(draws.every(e=>e.amount===1&&e.cards.length===1&&e.contextPlayer===owner));for(const draw of draws){const death=t.events.find(e=>e.id===draw.triggerEvent);assert(death?.name==='onCardDefeated');assert.notEqual(death.card,id(f));const actual=c.eg.game.allCards.find(card=>id(card)===death.card);assert(actual.unique);}
  if(p.scenario==='paid-ambush-first-second'){assert(t.events.some(e=>e.name==='onAttackDeclared'&&e.attacker.card===id(f)&&e.attacker.targets.includes(id(t.enemyUnique))));assert.equal(f.damage,1);}if(p.scenario==='ambush-no-target'||p.scenario==='ambush-decline'){assert.equal(f.exhausted,true);assert(!t.events.some(e=>e.name==='onAttackDeclared'&&e.attacker.card===id(f)));}if(p.scenario==='draw-decline-then-use'){assert(t.prompts.some(pr=>pr.chosen.label==='Pass'));assert(t.samples.some(sample=>sample.index===1&&sample.counters.some(l=>l.source===id(f)&&l.uses[p.owner]===0)));}if(p.scenario==='nonunique-then-captured-mass-death'){assert.equal(f.zoneName,'discard');assert.equal(draws[0].sourceZone,'discard');}if(p.scenario==='self-death-negative'){assert.equal(f.zoneName,'discard');assert.equal(draws.length,0);}
 }
 if(p.scenario==='round-reset'||p.scenario==='multiple-copies-round-reset'||p.scenario==='paid-hidden-first-second-round-reset'){
  assert(t.events.some(e=>e.name==='onPhaseEnded'&&e.counters.some(l=>l.source===id(f)&&l.uses[p.owner]===1)),'Phase end does not reset per-round use');assert(t.events.some(e=>e.name==='onRoundEnded'));assert(t.samples.some(e=>e.round>t.firstRound&&e.index===s.plan.length-1&&e.counters.some(l=>l.source===id(f)&&l.uses[p.owner]===0)),'Next-round actionable window has reset registration before next qualifier');
 }
 c.observed={...c.observed,rawProbe:JSON.parse(JSON.stringify(p)),events:t.events.slice(),prompts:t.prompts.slice(),samples:t.samples.slice(),plannedPlayChecks:t.playChecks.slice(),currentLimits:limits(c),focus:{id:id(f),zone:f.zoneName,exhausted:f.isInPlay()?f.exhausted:null}};t.stopped=true;
}
async function fixture(env,pool,scenario,seed){if(scenario.probe&&Object.hasOwn(scenario.probe,'interaction'))return require('./round-limit-interaction-fixture').fixture(env,pool,scenario,seed);const p=validateProbe(scenario.probe),game=await tokenFixture(env,pool,makeScenario(p,scenario),seed);game.records[0].constructionParameters.rawProbe=JSON.parse(JSON.stringify(p));game.records[0].fixtureConstruction='At first natural action window stage disclosed physical deck units in printed arenas, optional nativeShield/Weakness tokens, all planned hand cards in actual actor hand, up to24 remaining deck cards as ready resources per seat and ready existing resources, both bases damage0; no later state edits. Planned plays require real onCardPlayed+correct physical zone/parent+exact printed/aspect payment before script advances. Choose legal Play anyway on no-effect confirmation. Later scripts, regroup and committed terminal choices are real engine inputs. Completion policy excludes actual hand Support plays after focus assertions because generic Support donation projection is unsupported; full metadata and all legal action sets remain unchanged. Staged Rukh witnesses other-unique defeat only and make no Support lifecycle claim. Limits/window/registration IDs are read-only native observations.';game.witness.rawProbe=JSON.parse(JSON.stringify(p));game.witness.coverageObligationIds=[...(scenario.coverageObligationIds??[])];return game;}
module.exports={fixture,validateProbe,sourceHarness:{tokenFixture},dependencies:['bots/omni/rs/inactive-phase-keyword-state.js', 'lab/kessel-reference/pipeline/round-limit-interaction-fixture.js','lab/kessel-reference/pipeline/round-limit-probe-fixture.js', 'lab/kessel-reference/pipeline/probe-fixture.js', 'lab/kessel-reference/pipeline/terminal-completion.js', 'engine/env.js', 'engine/rng.js', 'engine/view.js', 'engine/stdio.js', 'engine/recorder.js', 'bots/omni/rs/state.js', 'bots/omni/rs/state-evidence.js', 'bots/omni/rs/unit-entry-state.js', 'bots/omni/rs/support-state.js', 'bots/omni/rs/round-limit-state.js', 'bots/omni/rs/pool.js', 'bots/players/index.js', 'bots/players/random.js', 'bots/players/rush.js', 'bots/players/heuristic.js', 'bots/players/profiles.js', 'bots/players/ismcts.js', 'bots/players/belief.js', 'bots/players/omniscient.js', 'bots/examples/random-bot.js', 'bots/examples/search-bot.js', 'bots/omni/search.js', 'bots/omni/evaluate.js', 'kessel:cards/pipeline/round-limit-probes.js']};
