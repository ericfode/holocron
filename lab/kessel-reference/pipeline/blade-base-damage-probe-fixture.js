'use strict';
// Actual source-engine construction; native/Wasm admission is separate.
const assert=require('node:assert/strict'),crypto=require('node:crypto');
const {seededRng}=require('../../../engine/env');
const {canonicalAction,fullState,expandActions}=require('../../../bots/omni/rs/state');
const {makeBot}=require('../../../bots/players');
const {terminalCompletion}=require('./terminal-completion');
const fillerCodes=['ASH_061','ASH_131','ASH_190','ASH_201','ASH_242','ASH_261','HMW_082','HMW_093','HMW_116','HMW_128','HMW_135','HMW_155','HMW_163','HMW_174','HMW_178','HMW_219','HMW_258'];
const U=(key,code,owner='own',extra={})=>({key,code,owner,...extra});
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
    for (const code of new Set(scenario.plan.filter((s) => !s.from).map((s) => s.code))) {
        const count = scenario.plan.filter((s) => !s.from && s.code === code).length;
        while (own.getCardsInZone('hand').filter((c) => matches(c, code)).length < count) {
            const c = all(own).find((c) => matches(c, code) && c.zoneName !== 'hand');
            assert.ok(c, `Not enough real script copies ${code}`);
            c.moveTo('hand');
        }
    }
    for (const p of [own, enemy]) {
        for (const c of p.drawDeck.slice(0, 12)) {
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
                if (!scriptObserved && index === scenario.plan.length && eg.round === initialRound) {
                    scenario.assertAfter(ctx);
                    observed.postAction = true;
                    scriptObserved = true;
                }
            }
            let chosen;
            if (eg.round === initialRound && atWindow) {
                if (pid === (scenario.plan[index]?.owner==='enemy'?enemy:own).id && index < scenario.plan.length) {
                    pending = scenario.plan[index++];
                    ctx.pending = pending;
                    ctx.index = index;
                    const c = pending.from ? targets[pending.from] : own.getCardsInZone('hand').find((c) => matches(c, pending.code));
                    assert.ok(c, `Missing script ${pending.code}`);
                    chosen = actions.find((a) => a.cardUuid === c.uuid);
                    assert.ok(chosen, `Illegal script ${pending.code}`);
                    scratch.incoming = c;
                }
                else
                    chosen = actions.find((a) => a.arg === 'pass');
            }
            else if (eg.round === initialRound && !atWindow && pending && !scriptObserved) {
                chosen = scenario.choose?.(ctx);
                if (!chosen && pending.target)
                    chosen = actions.find((a) => a.cardUuid === targets[pending.target]?.uuid);
                chosen ??= actions.find((a) => a.kind === 'button' && /trigger|resolve|play|deal|heal|give/i.test(a.label ?? '') && !/pass|cancel|no/i.test(a.label ?? ''));
            }
            if(scriptObserved&&scenario.assertLater&&!laterObserved)chosen??=atWindow?actions.find(a=>a.arg==='pass'):actions.find(a=>a.arg==='done');
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
function setup(c){const t=c.targets; t.focus??=c.own.getCardsInZone('hand').find(x=>x.internalName==='blade-three#bane-of-the-devastator');assert(t.focus);t.events=[];t.done=false;t.baseStart=c.own.base.damage;t.tokenStart=c.eg.game.state.allCards.length;t.readyStart=c.own.readyResourceCount;if(c.ownBaseLethal)c.own.base.damage=29;for(const name of ['onDamageDealt','onTokensCreated','onCardDefeated','onCardMoved','onAttackEnd'])c.eg.game.on(name,e=>{if(t.done)return;const windows=[];for(let w=c.eg.game.currentEventWindow,depth=0;w&&depth<8;w=w.parentWindow,depth++){const contexts=w._triggeredAbilityWindow?.triggeredAbilities??[];windows.push({depth,contexts:contexts.filter(x=>x.source===t.focus).map(x=>({source:x.source.uuid,sourceZone:x.source.zoneName,title:x.ability.title,capturedPlayer:x.player?.id??null,event:x.event?.name,eventCard:x.event?.card?.uuid}))});}t.events.push({name,card:e.card?.uuid??null,cardName:e.card?.internalName??null,targetZone:e.card?.zoneName??null,source:e.context?.source?.uuid??null,amount:e.amount??null,damageDealt:e.damageDealt??null,type:e.type??null,tokenType:e.tokenType??null,cards:e.cards?.map(x=>x.uuid)??null,generated:(e.generatedTokens??[]).map(x=>({id:x.uuid,owner:x.owner.id,name:x.internalName,controller:x.controller.id,canonicalId:c.eg.cardId(x.uuid)})),focusZone:t.focus.zoneName,focusUpgrades:t.focus.isInPlay()?t.focus.upgrades.map(x=>({id:x.uuid,name:x.internalName})):[],winner:c.eg.winner,windows});});}
function adv(c){return c.targets.focus.isInPlay()?c.targets.focus.upgrades.filter(x=>x.internalName==='advantage'):[];}
function check(c,n,ownDamage,{gone=false,expired=false}={}){const t=c.targets,f=t.focus;assert.equal(adv(c).length,n);assert.equal(c.own.base.damage,ownDamage);if(!gone){assert.equal(f.getPower(),2+n);assert.equal(f.getHp(),4);}const allocations=t.events.filter(e=>e.name==='onTokensCreated'&&e.source===f.uuid&&e.tokenType==='advantage');const total=allocations.flatMap(e=>e.generated);assert.equal(new Set(total.map(x=>x.id)).size,total.length);assert(total.every(x=>x.owner===c.own.id&&x.controller===c.own.id&&x.name==='advantage'));assert.deepEqual(total.map(x=>x.canonicalId),total.map((_,i)=>'c'+(t.tokenStart+i)),'Fresh physical Advantage allocation order');assert(allocations.every(e=>e.cards.length===1&&e.cards[0]===f.uuid),'Every actual batch targets the physical source');assert(allocations.every(e=>e.amount===1),'One token per resolved damage event, independent of point amount');c.observed.baseIdentities={own:{uuid:c.own.base.uuid,id:c.eg.cardId(c.own.base.uuid),seat:c.eg.seatOf(c.own.id)},enemy:{uuid:c.enemy.base.uuid,id:c.eg.cardId(c.enemy.base.uuid),seat:c.eg.seatOf(c.enemy.id)}};c.observed.ownBaseDamageEvents=t.events.filter(e=>e.name==='onDamageDealt'&&e.card===c.own.base.uuid);if(!gone)assert.equal(c.observed.ownBaseDamageEvents.length,total.length,'Exactly one allocated Advantage per actual resolved event on the physical own base');c.observed.events=t.events.slice();c.observed.focus={id:f.uuid,zone:f.zoneName,power:f.isInPlay()?f.getPower():null,upgrades:adv(c).map(x=>x.uuid)};c.observed.allocations=total;c.observed.scriptState=fullState(c.eg);t.done=true;}
const choose=c=>c.actions.find(a=>a.kind==='button'&&a.label==='Deal 1 damage to each base');const variants=[
{name:'paid-play-damage1',units:[],plan:[{code:'ASH_204'},{code:'SOR_014',from:'leader'}],choose,assertAfter:c=>{check(c,1,1);assert.equal(c.targets.readyStart-c.own.readyResourceCount,3);assert.equal(c.observed.allocations.length,1);}},
{name:'damage3',units:[U('focus','ASH_204'),U('attacker','SOR_095','enemy')],plan:[{code:'SOR_095',from:'attacker',target:'ownBase',owner:'enemy'}],assertAfter:c=>{check(c,1,3);assert.equal(c.observed.allocations.length,1);}},
{name:'separate-events',units:[U('focus','ASH_204'),U('attacker','LOF_254','enemy'),U('attacker2','LOF_254','enemy')],plan:[{code:'LOF_254',from:'attacker',target:'ownBase',owner:'enemy'},{code:'LOF_254',from:'attacker2',target:'ownBase',owner:'enemy'}],assertAfter:c=>{check(c,2,2);assert.equal(c.observed.allocations.length,2);}},
{name:'enemy-base-negative',units:[U('focus','ASH_204'),U('attacker','SOR_095')],plan:[{code:'SOR_095',from:'attacker',target:'enemyBase'}],assertAfter:c=>{check(c,0,0);assert.equal(c.enemy.base.damage,3);}},
{name:'friendly-unit-negative',units:[U('focus','ASH_204'),U('recipient','SOR_095'),U('attacker','SOR_095','enemy')],plan:[{code:'SOR_095',from:'attacker',target:'recipient',owner:'enemy'}],assertAfter:c=>check(c,0,0)},
{name:'shield-cancel-unit',units:[U('focus','ASH_204'),U('recipient','SOR_095','own',{shields:1}),U('attacker','SOR_095','enemy')],plan:[{code:'SOR_095',from:'attacker',target:'recipient',owner:'enemy'}],assertAfter:c=>{check(c,0,0);assert.equal(c.targets.recipient.damage,0);assert.equal(c.targets.recipient.upgrades.length,0);assert(!c.observed.events.some(e=>e.name==='onDamageDealt'&&e.card===c.targets.recipient.uuid));}},
{name:'zero-base-combat',units:[U('focus','ASH_204'),U('snoke','SHD_037'),U('attacker','IBH_063','enemy')],plan:[{code:'IBH_063',from:'attacker',target:'ownBase',owner:'enemy'}],assertAfter:c=>{check(c,0,0);assert.equal(c.targets.attacker.getPower(),0);assert(!c.observed.events.some(e=>e.name==='onDamageDealt'&&e.card===c.own.base.uuid));}},
{name:'source-gone-before',units:[U('focus','ASH_204')],plan:[{code:'TWI_226',target:'focus'},{code:'SOR_014',from:'leader'}],choose,assertAfter:c=>{check(c,0,1,{gone:true});assert.equal(c.targets.focus.zoneName,'hand');assert.equal(c.observed.allocations.length,0);}},
{name:'source-gone-within-cinder',units:[U('focus','ASH_204')],plan:[{code:'ASH_151'}],assertAfter:c=>{check(c,0,5,{gone:true});assert.equal(c.targets.focus.zoneName,'discard');assert.equal(c.observed.allocations.length,0);assert(c.observed.events.some(e=>e.windows.some(w=>w.contexts.some(x=>x.event==='onDamageDealt'&&x.eventCard===c.own.base.uuid&&x.capturedPlayer===c.own.id&&x.source===c.targets.focus.uuid))),'Native read-only window evidence captures Blade before its departure');}},
{name:'terminal-own-base',units:[U('focus','ASH_204')],plan:[{code:'SOR_014',from:'leader'}],choose,setup:c=>{setup(c);c.own.base.damage=29;},assertAfter:c=>{check(c,1,30);assert.equal(c.eg.winner,c.eg.seatOf(c.enemy.id));assert.equal(c.observed.allocations.length,1);assert(c.observed.events.some(e=>e.name==='onTokensCreated'&&e.source===c.targets.focus.uuid&&e.winner===c.eg.seatOf(c.enemy.id)),'Mandatory physical-source grant resolves with own-base lethal winner already latched');}},
{name:'advantage-attack-expiry',units:[],plan:[{code:'ASH_204'},{code:'SOR_014',from:'leader'},{code:'LAW_043',target:'focus'},{code:'ASH_204',from:'focus',target:'enemyBase'}],choose,assertAfter:c=>{check(c,0,1);assert.equal(c.enemy.base.damage,4);assert.equal(c.observed.allocations.length,1);const old=c.eg.game.findAnyCardInAnyList(c.observed.allocations[0].id);assert.equal(old.zoneName,'outsideTheGame');assert(c.targets.focus.upgrades.some(x=>x.internalName==='shield'));}},
{name:'advantage-phase-persistence',units:[U('focus','ASH_204')],plan:[{code:'SOR_014',from:'leader'}],choose,assertAfter:c=>check(c,1,1),assertLater:c=>{assert.equal(adv(c).length,1);assert.equal(adv(c)[0].uuid,c.observed.allocations[0].id);c.observed.sameTokenAcrossPhase=true;}},
];

const scenarios=variants.map(v=>v.name);
function validateProbe(probe){
 assert(probe&&Object.keys(probe).sort().join(',')==='baseCode,cardId,enemyBaseCode,enemyLeaderCode,family,fillerCodes,leaderCode,owner,resourceCount,scenario,sourceArena','Malformed Blade construction');
 assert.deepEqual(probe.fillerCodes,fillerCodes,'Exact ordered quiet filler inventory');
 assert.equal(probe.family,'blade-base-damage');assert.equal(probe.cardId,'ASH_204');assert([0,1].includes(probe.owner));
 assert(scenarios.includes(probe.scenario),'Unsupported Blade scenario');assert.equal(probe.sourceArena,'space');assert.equal(probe.resourceCount,12);
 assert.equal(probe.leaderCode,'SOR_014');assert.equal(probe.enemyLeaderCode,'SOR_014');assert.equal(probe.baseCode,'ASH_025');assert.equal(probe.enemyBaseCode,'ASH_025');
 return probe;
}
async function fixture(env,pool,scenario,seed){
 const probe=validateProbe(scenario.probe),variant=variants.find(v=>v.name===probe.scenario);
 const game=await tokenFixture(env,pool,{...variant,name:scenario.name??probe.scenario+'-seat'+probe.owner,seat:probe.owner,family:probe.family,leaderCode:probe.leaderCode,baseCode:probe.baseCode,fillerCodes:probe.fillerCodes,baseDamage:0,setup:variant.setup??setup},seed);
 game.records[0].fixtureConstruction='At first natural action window, stage declared real deck units in printed arenas, real script cards in the source-owner hand, up to12 additional remaining deck cards as resources for each seat, ready existing resources, set both bases damage0 (own29 only terminal case), generate declared initial Shields, and resolve state. Later steps are actual legal engine actions through complete terminal mandatory choices; no action-window action after winner.';
 game.records[0].constructionParameters.rawProbe=JSON.parse(JSON.stringify(probe));
 game.records[0].constructionParameters.rawProbeSha256=crypto.createHash('sha256').update(JSON.stringify(probe)).digest('hex');
 game.witness.rawProbe=JSON.parse(JSON.stringify(probe));
 game.witness.coverageObligationIds=[...(scenario.coverageObligationIds??[])];
 return game;
}
module.exports={fixture,validateProbe,dependencies:[
 'kessel:cards/pipeline/blade-base-damage-probes.js','lab/kessel-reference/pipeline/blade-base-damage-probe-fixture.js',
 'lab/kessel-reference/pipeline/terminal-completion.js','engine/env.js','engine/rng.js',
 'bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/support-state.js','bots/omni/rs/unit-entry-state.js','bots/players/index.js','bots/players/random.js'
]};
