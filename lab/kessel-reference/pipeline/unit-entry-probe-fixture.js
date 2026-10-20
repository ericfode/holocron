'use strict';
const { terminalCompletion } = require('./terminal-completion');
// Real printed-card token creation/removal witnesses; generation is not conformance.
const fs = require('node:fs'), path = require('node:path'), zlib = require('node:zlib'), crypto = require('node:crypto'), assert = require('node:assert/strict');
const { Env, seededRng } = require('../../../engine/env'), { loadPool } = require('../../../bots/omni/rs/pool'), { canonicalAction, fullState, expandActions } = require('../../../bots/omni/rs/state'), { makeBot } = require('../../../bots/players');
const unit = (key, code, owner = 'own', damage = 0) => ({ key, code, owner, damage });
const matches = (c, code) => [c.cardData.setId, ...(c.cardData.setCodes ?? [])].some(s => s.set + '_' + String(s.number).padStart(3, '0') === code);
const arena = c => c.cardData.arena === 'space' ? 'spaceArena' : 'groundArena';
const plain = [];
function deckFor(pool, scenario) {
    const codes = [...new Set([...(scenario.units ?? plain).map((u) => u.code), ...scenario.plan.filter((s) => s.from !== 'leader').map((s) => s.code), ...(scenario.extraCodes ?? [])])];
    assert.ok(codes.length <= 17);
    for (const code of [...codes, scenario.leaderCode ?? 'SOR_014', scenario.baseCode ?? 'SOR_023'])
        assert.ok(pool.cards.some((c) => c.setCode === code), `Missing ${code} in oracle input pool`);
    const filler = pool.cards.filter((c) => c.types.includes('unit') && !c.text && !codes.includes(c.setCode)).slice(0, 17 - codes.length).map((c) => c.setCode);
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
    const own = eg.player(eg.ids[scenario.sourceSeat - 1]), enemy = eg.player(eg.ids[2 - scenario.sourceSeat]), targets = { ownBase: own.base, enemyBase: enemy.base };
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
        for (const c of p.drawDeck.slice(0, 30)) {
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
    const initialRound = eg.round, observed = {}, scratch = {}, initialState = fullState(eg), records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['scripted-group-fixture', 'scripted-group-fixture'], decks: [deck, deck], scenario: scenario.name,
            evidenceStatus: 'Engine observation; native/Wasm conformance unassessed', fixtureConstruction: (scenario.emptyOwnDeck ? 'Empty-deck scenario additionally moves all remaining p1 draw-deck cards into discard before initial state capture. ' : '') + (scenario.emptyOwnHand ? 'Empty-hand scenario additionally moves every initial p1 hand card into ready resources before initial state capture. ' : '') + 'At first natural action window, move specified real deck units into their printed arenas with specified exhaustion, move script cards into p1 hand, move30 remaining deck cards perplayer into ready resources, ready all resources, set bases damage24(orprintedHP-1 forbothLethal), resolve game state, then set disclosed survivingunitdamage and refreshprompts. Specified initial Shields are created with pinned game.generateToken and attached before state resolution. No later state edits.', constructionParameters: { emptyOwnDeck: !!scenario.emptyOwnDeck, emptyOwnHand: !!scenario.emptyOwnHand, units: scenario.units ?? plain, plan: scenario.plan, bothLethal: !!scenario.bothLethal, leaderCode: scenario.leaderCode, deployedLeader: !!scenario.deployedLeader, baseDamage: scenario.baseDamage, initiative: scenario.initiative } }];
    let step = 0, index = 0, pending = null, scriptObserved = false, laterObserved = false;
    const completion = terminalCompletion(eg, 4000);
    try {
        while (true) {
            const pid = completion.nextActor(step); if (!pid) break;
            const actions = expandActions(eg, eg.legalActions(pid)), atWindow = eg.isActionWindow(pid), ctx = { eg, own, enemy, targets, actions, pid, atWindow, index, pending, step, observed, scratch, initialState };
            if (atWindow && scriptObserved && !laterObserved && eg.round > initialRound && scenario.assertLater) {
                scenario.assertLater(ctx);
                observed.laterRoundAssertion = true;
                laterObserved = true;
            }
            scenario.beforeWindow?.(ctx);
            if (atWindow) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (!scriptObserved && index === scenario.plan.length) {
                    scenario.assertAfter(ctx);
                    observed.postAction = true;
                    scriptObserved = true;
                }
            }
            let chosen;
            if (atWindow && !scriptObserved) {
                if (pid === own.id && index < scenario.plan.length && eg.round >= initialRound + (scenario.plan[index].roundOffset ?? 0)) {
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
            else if (!atWindow && pending && !scriptObserved) {
                chosen = scenario.choose?.(ctx);
                if (!chosen && pid === own.id && pending.target)
                    chosen = actions.find((a) => a.cardUuid === targets[pending.target]?.uuid);
                chosen ??= actions.find((a) => a.kind === 'button' && /trigger|resolve|play|deal|heal|give/i.test(a.label ?? '') && !/pass|cancel|no/i.test(a.label ?? ''));
            }
            if (scriptObserved && scenario.assertLater && !laterObserved) chosen ??= atWindow ? actions.find(a => a.arg === 'pass') : actions.find(a => a.arg === 'done');
            chosen ??= scenario.chooseLater?.(ctx);
            if (eg.over && !atWindow && /resourc/i.test(eg.player(pid).currentPrompt().menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done') ?? chosen;
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
        observed.terminalCompletion = completion.assertComplete();
        assert.ok(eg.over, 'Oracle game did not complete');
        assert.equal(index, scenario.plan.length, 'Script incomplete');
        if (!scriptObserved) {
            scenario.assertAfter({ eg, own, enemy, targets, observed, scratch, initialState });
            observed.postAction = true;
        }
        if (scenario.assertLater)
            assert.ok(laterObserved, 'Missing later-round assertion');
        scenario.assertWitness?.({ observed, scratch, records, eg, own, enemy, targets, initialState });
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        return { records, witness: { scenario: scenario.name, family: scenario.family, observed, decisions: step, winner: eg.winner } };
    }
    catch(error) { error.diagnostic = { records, observed }; throw error; }
    finally {
        bot.close?.();
    }
}

const U=(key,code,owner='own',extra={})=>({key,code,owner,...extra});
function snap(c){return {id:c.uuid,name:c.internalName,title:c.title,owner:c.owner?.id,controller:c.controller?.id,zone:c.zoneName,inPlayId:c.canBeInPlay?.()&&c.isInPlay()?c.inPlayId:null,power:c.isUnit()&&c.isInPlay()?c.getPower():null,hp:c.isUnit()&&c.isInPlay()?c.getHp():null,damage:c.isUnit?.()&&c.isInPlay()?c.damage:null,upgrades:c.isUnit?.()&&c.isInPlay()?c.upgrades.map(x=>({id:x.uuid,name:x.internalName})):[]};}
function setup(c){c.targets.sourceEventLog=[];for(const name of ['onUnitEntersPlay','onCardPlayed','onCardDefeated','onCardMoved','onEffectApplied'])c.eg.game.on(name,e=>{c.targets.sourceEventLog.push({name,card:e.card?snap(e.card):null,eventId:e.id??e.uuid??null,entryType:e.entryType??null,newController:e.newController?.id??null,source:e.context?.source?.uuid??null,contextPlayer:e.context?.player?.id??null,lki:e.lastKnownInformation?{title:e.lastKnownInformation.title,power:e.lastKnownInformation.power,controller:e.lastKnownInformation.controller?.id,inPlayId:e.lastKnownInformation.inPlayId}:null});});}
function after(c,checks){checks(c);c.observed.scriptState=fullState(c.eg);assert.equal(c.observed.scriptState.unitEntryStateVersion,1);assert.ok(Array.isArray(c.observed.scriptState.inactiveUnitEntryStats));c.observed.snapshots=Object.fromEntries(Object.entries(c.targets).filter(([k,v])=>v?.uuid).map(([k,v])=>[k,snap(v)]));c.observed.events=c.targets.sourceEventLog.slice();c.observed.allUnits=c.eg.game.getPlayers().flatMap(p=>p.getArenaUnits().map(snap));}
const variants = [
{name:'piloting-no-entry',units:[U('source','ASH_041'),U('host','LOF_192')],plan:[{code:'JTL_211',target:'host'}],choose:c=>c.actions.find(a=>/Play Independent Smuggler with Piloting/.test(a.label??'')),assertAfter:c=>after(c,c=>{assert.equal(c.targets.host.getPower(),4);assert.ok(c.targets.host.upgrades.some(u=>u.internalName==='independent-smuggler'));assert.equal(c.targets.sourceEventLog.filter(e=>e.name==='onUnitEntersPlay').length,0);assert.equal(c.targets.sourceEventLog.filter(e=>e.name==='onEffectApplied').length,0);})},
{name:'token-identity-no-leak',units:[U('source','ASH_041'),U('snoke','SHD_037','enemy')],plan:[{code:'ASH_111'},{code:'ASH_111'}],assertAfter:c=>after(c,c=>{const es=c.targets.sourceEventLog,entries=es.filter(x=>x.name==='onUnitEntersPlay'&&x.card?.name==='mandalorian'),effects=es.filter(x=>x.name==='onEffectApplied'&&x.card?.name==='mandalorian');assert.equal(entries.length,4);assert.equal(new Set(entries.map(x=>x.card.id)).size,4);assert.equal(effects.length,4);assert.deepEqual(effects.map(x=>x.card.id).sort(),entries.map(x=>x.card.id).sort());const registry=c.eg.game.ongoingEffectEngine.effects.filter(e=>e.duration==='untilEndOfPhase'&&entries.some(x=>x.card.id===e.matchTarget?.uuid));assert.equal(registry.length,4);assert.equal(new Set(registry.map(e=>e.matchTarget.uuid)).size,4);c.observed.tokenRegistry=registry.map(e=>({source:e.source.uuid,target:e.matchTarget.uuid,targetZone:e.matchTarget.zoneName,targets:e.targets.map(x=>x.uuid)}));})},

...[false,true].map(expire=>({name:'dead-target-physical-direct-reentry-'+(expire?'after-expiry':'same-phase'),units:[U('source','ASH_041')],plan:[{code:'ASH_041'},{code:'TWI_226',target:'source'},{code:'JTL_121',target:'recipient',roundOffset:expire?1:0}],beforeWindow:c=>{if(c.atWindow&&c.index===1&&!c.targets.recipient)c.targets.recipient=c.scratch.incoming;if(c.atWindow&&!c.observed.postAction){(c.observed.registries??=[]).push({index:c.index,round:c.eg.round,recipient:c.targets.recipient?snap(c.targets.recipient):null,effects:c.eg.game.ongoingEffectEngine.effects.filter(e=>e.duration==='untilEndOfPhase').map(e=>({source:e.source.uuid,sourceZone:e.source.zoneName,type:e.impl?.type,duration:e.duration,matchTarget:e.matchTarget?.uuid??null,targets:e.targets?.map(x=>({id:x.uuid,zone:x.zoneName}))}))});}},choose:c=>c.eg.player(c.pid).currentPrompt().menuTitle?.includes('which copy')?c.actions.find(a=>a.cardUuid===c.scratch.incoming?.uuid):c.eg.player(c.pid).currentPrompt().promptType==='resource'?c.actions.find(a=>a.arg==='done'):undefined,assertAfter:c=>after(c,c=>{assert.equal(c.targets.recipient.zoneName,'spaceArena');c.observed.reentryPower=c.targets.recipient.getPower();assert.equal(c.targets.recipient.getPower(),2);assert.equal(c.targets.recipient.damage,1);})})),

...[false,true].map(expire=>({name:'dead-target-physical-reentry-'+(expire?'after-expiry':'same-phase'),units:[U('source','ASH_041')],plan:[{code:'ASH_041'},{code:'TWI_226',target:'source'},{code:'SEC_105',target:'recipient',roundOffset:expire?1:0},{code:'ASH_041',from:'recipient',roundOffset:expire?1:0}],beforeWindow:c=>{if(c.atWindow&&c.index===1&&!c.targets.recipient)c.targets.recipient=c.scratch.incoming;if(c.atWindow&&!c.observed.postAction){(c.observed.registries??=[]).push({index:c.index,round:c.eg.round,recipient:c.targets.recipient?snap(c.targets.recipient):null,effects:c.eg.game.ongoingEffectEngine.effects.filter(e=>e.duration==='untilEndOfPhase').map(e=>({source:e.source.uuid,sourceZone:e.source.zoneName,type:e.impl?.type,duration:e.duration,matchTarget:e.matchTarget?.uuid??null,targets:e.targets?.map(x=>({id:x.uuid,zone:x.zoneName}))}))});}},choose:c=>c.eg.player(c.pid).currentPrompt().menuTitle?.includes('which copy')?c.actions.find(a=>a.cardUuid===c.scratch.incoming?.uuid):c.eg.player(c.pid).currentPrompt().promptType==='resource'?c.actions.find(a=>a.arg==='done'):undefined,assertAfter:c=>after(c,c=>{assert.equal(c.targets.source.zoneName,'hand');assert.equal(c.targets.recipient.zoneName,'spaceArena');c.observed.reentryPower=c.targets.recipient.getPower();assert.equal(c.targets.recipient.getPower(),2);})})),

{name:'buffed-combat',units:[U('source','ASH_041')],plan:[{code:'SOR_095'},{code:'LAW_043',target:'recipient'},{code:'SOR_095',from:'recipient',target:'enemyBase'}],beforeWindow:c=>{if(c.atWindow&&c.index===1&&!c.targets.recipient)c.targets.recipient=c.scratch.incoming;},assertAfter:c=>after(c,c=>{assert.equal(c.enemy.base.damage,4);assert.equal(c.targets.recipient.getPower(),4);})},
{name:'two-droid-resolve-all',units:[U('source','ASH_041')],plan:[{code:'TWI_237'}],choose:c=>c.actions.find(a=>a.arg==='all'),assertAfter:c=>after(c,c=>{const ts=c.own.getArenaUnits().filter(x=>x.internalName==='battle-droid');assert.equal(ts.length,2);assert(ts.every(x=>x.getPower()===2));})},
{name:'target-bounce-reentry',units:[U('source','ASH_041')],plan:[{code:'SOR_095'},{code:'TWI_226',target:'recipient'},{code:'SOR_095',from:'recipient'}],beforeWindow:c=>{if(c.atWindow&&c.index===1&&!c.targets.recipient)c.targets.recipient=c.scratch.incoming;},assertAfter:c=>after(c,c=>{assert.equal(c.targets.recipient.getPower(),4);assert.equal(c.targets.recipient.zoneName,'groundArena');})},
{name:'cobb-first-order',units:[U('source','ASH_041'),U('cobb','ASH_060')],plan:[{code:'SOR_095'}],choose:c=>c.actions.find(a=>/^Deal 2 damage to Cobb Vanth/.test(a.label??'')),assertAfter:c=>after(c,c=>{assert.equal(c.scratch.incoming.getPower(),4);assert.equal(c.targets.cobb.damage,2);assert(c.scratch.incoming.upgrades.some(x=>x.internalName==='shield'));})},
{name:'friendly-marine',units:[U('source','ASH_041')],plan:[{code:'SOR_095'}],assertAfter:c=>after(c,c=>assert.equal(c.scratch.incoming.getPower(),4)),assertLater:c=>{assert.equal(c.scratch.incoming.getPower(),3);c.observed.expired=true;}},
{name:'self-entry',units:[],plan:[{code:'ASH_041'}],assertAfter:c=>after(c,c=>assert.equal(c.scratch.incoming.getPower(),2)),assertLater:c=>{assert.equal(c.scratch.incoming.getPower(),1);c.observed.expired=true;}},
{name:'enemy-source-no-buff',units:[U('source','ASH_041','enemy')],plan:[{code:'SOR_095'}],assertAfter:c=>after(c,c=>assert.equal(c.scratch.incoming.getPower(),3))},
{name:'two-droid-entries',units:[U('source','ASH_041')],plan:[{code:'TWI_237'}],assertAfter:c=>after(c,c=>{const ts=c.own.getArenaUnits().filter(x=>x.internalName==='battle-droid');assert.equal(ts.length,2);assert(ts.every(x=>x.getPower()===2));})},
{name:'mandalorian-shielded-snoke-death',units:[U('source','ASH_041'),U('snoke','SHD_037','enemy')],plan:[{code:'ASH_111'}],assertAfter:c=>after(c,c=>{assert.equal(c.own.getArenaUnits().filter(x=>x.internalName==='mandalorian').length,0);assert.equal(c.scratch.incoming.getPower(),2);})},
{name:'leader-deploy',units:[U('source','ASH_041')],plan:[{code:'SOR_014',from:'leader'}],choose:c=>c.actions.find(a=>/Deploy Sabine/.test(a.label??'')),assertAfter:c=>after(c,c=>assert.equal(c.targets.leader.getPower(),3))},
{name:'cobb-and-entry-order',units:[U('source','ASH_041'),U('cobb','ASH_060')],plan:[{code:'SOR_095'}],assertAfter:c=>after(c,c=>{assert.equal(c.scratch.incoming.getPower(),4);assert.equal(c.targets.cobb.damage,2);assert(c.scratch.incoming.upgrades.some(x=>x.internalName==='shield'));})},
{name:'unique-keep-incoming',units:[U('source','ASH_041')],plan:[{code:'ASH_041'}],choose:c=>c.actions.find(a=>a.cardUuid===c.targets.source.uuid),assertAfter:c=>after(c,c=>{assert.equal(c.targets.source.zoneName,'discard');assert.equal(c.scratch.incoming.zoneName,'spaceArena');assert.equal(c.scratch.incoming.getPower(),3);})},
{name:'unique-keep-old',units:[U('source','ASH_041')],plan:[{code:'ASH_041'}],choose:c=>c.actions.find(a=>a.cardUuid===c.scratch.incoming?.uuid),assertAfter:c=>after(c,c=>{assert.equal(c.targets.source.zoneName,'spaceArena');assert.equal(c.scratch.incoming.zoneName,'discard');assert.equal(c.targets.source.getPower(),1);})},
{name:'source-departure-persists',units:[U('source','ASH_041')],plan:[{code:'SOR_095'},{code:'TWI_226',target:'source'}],assertAfter:c=>after(c,c=>{assert.equal(c.targets.source.zoneName,'hand');const marine=c.own.getArenaUnits().find(x=>x.internalName==='battlefield-marine');assert.equal(marine.getPower(),4);})}
];

// These cases deliberately use the exact donor set-codes exercised by the source
// oracle. A reprint sharing a source class is not an admission witness.
const variantMap = {
 'piloting-no-entry':'piloting-no-entry',
 'self-entry':'self-entry', 'friendly-entry':'friendly-marine', 'enemy-entry':'enemy-source-no-buff',
 'multiple-entrants-next':'two-droid-entries', 'multiple-entrants-all':'two-droid-resolve-all',
 'unique-keep-incoming':'unique-keep-incoming', 'unique-keep-old':'unique-keep-old',
 'dead-mandalorian-batch':'mandalorian-shielded-snoke-death', 'repeated-dead-token-batch':'token-identity-no-leak',
 'renewed-friendship-replay':'dead-target-physical-reentry-same-phase',
 'salvage-replay':'dead-target-physical-direct-reentry-same-phase',
 'renewed-friendship-expired':'dead-target-physical-reentry-after-expiry',
 'salvage-expired':'dead-target-physical-direct-reentry-after-expiry',
 'phase-expiry':'friendly-marine', 'source-departure':'source-departure-persists',
 'recipient-reentry':'target-bounce-reentry', 'leader-deploy':'leader-deploy', 'buffed-combat':'buffed-combat',
 'mixed-trigger-order-outcast-first':'cobb-and-entry-order', 'mixed-trigger-order-cobb-first':'cobb-first-order'
};
function definition(probe) {
 assert.equal(probe.family, 'unit-entry'); assert.equal(probe.cardId, 'ASH_041');
 assert.ok([1,2].includes(probe.sourceSeat));
 const name=variantMap[probe.scenario]; assert.ok(name, 'Unsupported unit-entry scenario: '+probe.scenario);
 const original=variants.find(v=>v.name===name); assert.ok(original);
 return {...original, name:probe.scenario, sourceSeat:probe.sourceSeat, family:'unit-entry', baseDamage:0,
   setup:original.setup??setup,
   assertAfter:c=>{
    original.assertAfter(c);
    const rows=c.observed.scriptState.inactiveUnitEntryStats;
    if(probe.scenario==='unique-keep-old'){
      assert.equal(rows.length,1);assert.equal(rows[0].card.id,c.eg.cardId(c.scratch.incoming.uuid));assert.equal(rows[0].power,2);assert.equal(rows[0].hp,0);
      assert.equal(rows[0].card.owner,c.eg.seatOf(c.own.id));assert.equal(rows[0].card.controller,c.eg.seatOf(c.own.id));
    }
    if(['dead-mandalorian-batch','repeated-dead-token-batch'].includes(probe.scenario)){
      const n=probe.scenario==='dead-mandalorian-batch'?2:4;assert.equal(rows.length,n);
      assert.ok(rows.every(r=>r.card.setCode==='TOKEN_MANDALORIAN'&&r.card.name==='mandalorian'&&r.power===1&&r.hp===0));
      assert.equal(new Set(rows.map(r=>r.card.id)).size,n);assert.ok(rows.every(r=>r.card.owner===c.eg.seatOf(c.own.id)&&r.card.controller===c.eg.seatOf(c.own.id)));
    }
   },
   choose:c=>original.choose?.(c)??(c.eg.player(c.pid).currentPrompt().promptType==='resource'?c.actions.find(a=>a.arg==='done'):undefined),
   assertWitness:c=>{
    const entryEvents=c.observed.events.filter(e=>e.name==='onUnitEntersPlay');
    const effects=c.observed.events.filter(e=>e.name==='onEffectApplied');
    c.observed.entryIdentities=entryEvents.map(e=>e.card.id);
    c.observed.appliedEffectTargets=effects.map(e=>e.card.id);
    c.observed.triggerMenus=c.records.filter(r=>r.type==='decision'&&['triggerWindow','batchTriggerResolution'].includes(r.prompt.type)).map(r=>({actor:r.actor,title:r.prompt.title,actions:r.actions,chosen:r.chosen}));
    c.observed.unitEntryState=fullState(c.eg);
    assert.ok(c.observed.postAction); assert.equal(c.records.at(-1)?.type==='result',false,'Runner appends terminal receipt after witness');
   }
 };
}
function donorCodes(scenario) {
 const d=definition({family:'unit-entry',cardId:'ASH_041',scenario,sourceSeat:1});
 return [...new Set([...(d.units??[]).map(u=>u.code),...d.plan.map(p=>p.code),d.leaderCode??'SOR_014'])].filter(c=>c!=='ASH_041').sort();
}
const diagnosticVariants = ['piloting-no-entry','renewed-friendship-replay','salvage-replay','renewed-friendship-expired','salvage-expired','mixed-trigger-order-outcast-first','mixed-trigger-order-cobb-first'];
async function fixture(env,pool,scenario,seed) {
 const p=scenario.probe;
 if(diagnosticVariants.includes(p.scenario)) assert.equal(p.engineOnlyDiagnostic,true,'Rejected setup donor requires explicit engineOnlyDiagnostic:true; no native admission claim');
 const d={...definition(p),name:scenario.name};
 const r=await tokenFixture(env,pool,d,seed);
 r.witness.scenario=scenario.name; r.witness.engineOnlyDiagnostic=!!p.engineOnlyDiagnostic;
 r.witness.coverageObligationIds=p.engineOnlyDiagnostic?[]:[...(scenario.coverageObligationIds??[])];
 r.records[0].engineOnlyDiagnostic=!!p.engineOnlyDiagnostic;
 if(p.engineOnlyDiagnostic) r.records[0].evidenceStatus='Engine-only diagnostic; setup donor or action protocol not native admitted; no conformance credit';
 return r;
}
module.exports={fixture,definition,donorCodes,diagnosticVariants,variants:Object.keys(variantMap).filter(v=>!diagnosticVariants.includes(v)),dependencies:['lab/kessel-reference/pipeline/terminal-completion.js',
 'lab/kessel-reference/pipeline/unit-entry-probe-fixture.js','engine/env.js','engine/rng.js',
 'bots/omni/rs/state.js','bots/omni/rs/unit-entry-state.js','bots/omni/rs/state-evidence.js',
 'bots/omni/rs/support-state.js','bots/players/index.js'
]};
