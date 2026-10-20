'use strict';
const { terminalCompletion } = require('./terminal-completion');
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');

// A protocol state certifies an actual action window. Pending post-winner
// snapshots belong in witnesses or the completed result, never this record type.
function actionWindowState(eg, pid, step) {
    assert.equal(eg.isActionWindow(pid), true, 'State record requires an actual action window');
    return { type: 'state', step, state: fullState(eg, pid) };
}
function assertActionWindowRecords(records) {
    const decisions = new Map(records.filter(r => r.type === 'decision').map(r => [r.step, r]));
    for (const record of records.filter(r => r.type === 'state'))
        assert.equal(decisions.get(record.step)?.prompt.actionWindow, true, 'State record requires an actual action-window decision');
}
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    const firstStrike = ['first-strike-incoming','first-strike-return','first-strike-shield'].includes(p.cause), firstReturn = p.cause === 'first-strike-return', shieldCase = p.cause === 'first-strike-shield';
    if(firstStrike){assert.equal(p.firstStrikeCode,'IC27_175');assert.equal(p.expectedAmount,shieldCase?0:2);assert.equal(p.recipient,'self');assert.equal(p.decline,false);assert.equal(firstReturn?p.defenderCode:p.attackerCode,firstReturn?'ASH_197':'LAW_253');}
    assert.equal(p.family, 'defeat-cause');
    const reverse = p.owner === 1, relative = owner => reverse ? (owner === 'self' ? 'opponent' : 'self') : owner;
    const rows = [{ code: p.recipientCode, owner: relative(p.recipient), arena: 'ground', exhausted: true }];
    if (p.combatCode) rows.push({ code: p.combatCode, owner: relative('opponent'), arena: 'space' });
    if (p.attackerCode) rows.push({ code: p.attackerCode, owner: relative(firstStrike?'opponent':'self'), arena: 'space', exhausted: false });
    if (p.defenderCode) rows.push({ code:p.defenderCode,owner:relative('opponent'),arena:'space',exhausted:false });
    if (p.statCode) rows.push({ code: p.statCode, owner: relative('opponent'), arena: 'ground' });
    if (reverse) rows.push({ code: p.cardId, owner: 'opponent', ...(p.cause === 'stat-death' ? { zone: 'hand' } : { arena: 'space', exhausted: false }) });
    if (reverse && p.activationCode) rows.push({ code: p.activationCode, owner: 'opponent', zone: 'hand' });
    if(firstStrike) rows.push({code:p.firstStrikeCode,owner:relative(firstReturn?'self':'opponent'),zone:'hand'});
    const construction = { ...scenario, probe: { ...p, sourceInPlay: !reverse && p.cause !== 'stat-death', targets: rows, initiative: firstStrike ? ((firstReturn?p.owner:1-p.owner)===1?'opponent':'self') : reverse ? 'opponent' : 'self', leaderCode: 'SOR_014', enemyLeaderCode: 'SOR_014' } };
    const setup = await constructProbeFixture(env, pool, construction, seed);
    const { eg, rng, bot, deck } = setup, own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const sourceIndex = 1 + Number(!!p.combatCode || !!p.attackerCode || !!p.statCode || !!p.defenderCode);
    const source = reverse ? setup.targets[sourceIndex] : setup.source;
    const activation = firstStrike ? setup.targets.at(-1) : p.activationCode ? (reverse ? setup.targets[sourceIndex + 1] : setup.activation) : source;
    const recipient = setup.targets[0], donor = setup.targets[1];
    let initialShield=null; if(shieldCase){initialShield=eg.game.generateToken(own,'shield');initialShield.attachTo(source);}
    if (p.cause !== 'stat-death') { source.exhausted = false; eg.game.resolveGameState(true); eg.game.continue(); }
    const id = card => eg.cardId(card.uuid), live = card => card.isUnit?.() && card.isInPlay();
    const advantages = () => recipient.upgrades.filter(card => card.isAdvantage?.());
    const ready = player => player.getCardsInZone('resource').filter(card => !card.exhausted).length;
    const cost = card => { const aspects = [...card.controller.getAspectsForCosts()]; let n = card.cardData.cost; for (const a of card.cardData.aspects) { const i = aspects.indexOf(a); if (i < 0) n += 2; else aspects.splice(i, 1); } return n; };
    const paymentPlayer=firstStrike?activation.controller:own, attackPlayer=paymentPlayer;
    const firstAttacker=firstReturn?source:setup.targets[1], firstDefender=firstReturn?setup.targets[1]:source;
    const expectedCause = firstStrike ? 'attack' : { combat: 'attack', 'direct-damage': 'nonCombatDamage', 'direct-defeat': 'ability', 'attack-ability-damage': 'nonCombatDamage', 'stat-death': 'frameworkEffect' }[p.cause];
    assert.ok(expectedCause); assert.equal(p.expectedAmount, firstStrike?(shieldCase?0:2):p.cause === 'combat' ? 2 : 3);
    const initialAdvantageIds=new Set(eg.game.allCards.filter(card=>card.isAdvantage?.()).map(id));
    assert.equal(advantages().length, 0); assert.equal(source.owner, own); assert.equal(recipient.controller, p.recipient === 'self' ? own : enemy);
    const recipientPower = recipient.getPower(), recipientHp = recipient.getHp(), grantedAmount=p.decline?0:p.expectedAmount;
    const witness = { events: [], observations: [], coverageObligationIds: [] }, records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['defeat-cause-probe', 'defeat-cause-probe'], decks: setup.decks ?? [deck, deck], scenario: scenario.name, constructionParameters: p,
        fixtureConstruction: 'Stage actual recipient and admitted cause donors. Combat/direct events attack or pay normally; stat death normally plays Fiend under native Snoke. Give actual native Advantage, cross regroup, attack with recipient, then finish ordinary existing-unit play/fatigue. No additional hand plays introduce unassessed Fiend copies.'+(firstStrike?' Actual canonical Shoot First (SOR217 implementation, IC27_175 printing) supplies both first-strike windows; Shield case uses disclosed native game.generateToken/attachTo setup.':'') }];
    let step = 0, started = false, dead = false, grantChecked = false, titleSeen = false, phaseChecked = false, recipientAttack = false, recipientAttackEnded = false, settled = false, roundOfGrant = null, initialReady = 0;
    let firstAttackEnded=false, firstWindowSurvivor=false;
    let paidCard = null, defeatEvent = null, tokens = [], recipientAttackPower = null;
    const created = [], tokenDefeats = [], damages = [];
    function observe(stage, pid, actions, state = true) { witness.observations.push({ stage, actor: pid ? eg.seatOf(pid) : null, actions: actions?.map(a => canonicalAction(eg, a)), ...(state ? { state: fullState(eg, pid) } : {}) }); }
    observe('construction');
    eg.game.on('onCardPlayed', e => { if (started && e.card === paidCard && !e.isCancelledOrReplaced) { assert.equal(initialReady - ready(paymentPlayer), cost(paidCard), 'Exact ordinary printed/aspect resource payment'); witness.events.push({ name: 'paid-activation', card: id(e.card), paid: initialReady - ready(paymentPlayer) }); } });
    eg.game.on('onCardDefeated', e => {
        if (!started || settled || e.isCancelledOrReplaced) return;
        if (e.card === source) {
            if(shieldCase) assert.fail('Shield-cancelled first combat must not defeat Fiend or capture its trigger');
            if(firstStrike){assert.deepEqual(e.defeatSource.damageDealtBy,[firstReturn?firstDefender:firstAttacker]);if(firstReturn)assert.ok(firstWindowSurvivor,'Actual first damage leaves both participants before return combat death');}
            assert.equal(e.defeatSource.type, expectedCause, 'Actual physical defeat cause controls 2 versus 3');
            assert.equal(source.zoneName, 'discard'); assert.equal(e.lastKnownInformation.controller, own, 'Captured last-known controller survives departure');
            const activeAttackId = eg.game.currentAttack?.id ?? null;
            if (p.cause === 'attack-ability-damage') { assert.notEqual(activeAttackId, null, 'On Attack ability damage occurs inside an actual attack, including ID zero'); assert.equal(e.defeatSource.card, donor); }
            if (p.cause === 'direct-damage' || p.cause === 'direct-defeat') assert.equal(e.defeatSource.card, activation);
            dead = true; defeatEvent = e;
            witness.events.push({ name: 'source-defeat', card: id(source), sourceZone: source.zoneName, cause: e.defeatSource.type, activeAttackId, lkiController: eg.seatOf(e.lastKnownInformation.controller.id) });
        }
        if(shieldCase&&e.card===initialShield)witness.events.push({name:'first-strike-shield-removed',shield:id(initialShield),host:id(source),sourceDamage:source.damage,shieldZone:initialShield.zoneName});
        if (tokens.includes(e.card)) { tokenDefeats.push(e.card); witness.events.push({ name: 'advantage-defeat', card: id(e.card) }); }
    });
    eg.game.on('onTokensCreated', e => {
        if (!started || settled || e.isCancelledOrReplaced || e.context?.source !== source) return;
        assert.equal(source.zoneName, 'discard', 'Actual give resolves from captured offboard source');
        const actual = (e.generatedTokens ?? []).filter(card => card.isAdvantage?.());
        created.push(...actual); witness.events.push({ name: 'advantage-created', source: id(source), sourceZone: source.zoneName, ids: actual.map(id), owners: actual.map(card => eg.seatOf(card.owner.id)) });
    });
    eg.game.on('onDamageDealt', e => {
        if(firstStrike&&started&&!settled&&!e.isCancelledOrReplaced&&e.card===firstDefender&&e.damageSource.type==='attack'){
            assert.equal(firstAttacker.getPower(),firstReturn?4:3);assert.equal(e.damageDealt,firstReturn?4:1,'Actual damage is capped by remaining HP');
            if(firstReturn){assert.equal(source.isInPlay(),true);assert.equal(source.damage,0);assert.equal(firstDefender.getHp(),12);assert.equal(firstDefender.damage,4);firstWindowSurvivor=true;witness.events.push({name:'first-strike-survivor',source:id(source),sourceDamage:source.damage,defender:id(firstDefender),defenderDamage:firstDefender.damage,defenderHp:firstDefender.getHp()});}
        }
 if (started && !settled && !e.isCancelledOrReplaced) { damages.push(e); witness.events.push({ name: 'damage', card: id(e.card), amount: e.damageDealt, type: e.damageSource.type }); } });
    eg.game.on('onAttackDamageResolved:preResolve', e => { if (!settled && recipientAttack && e.attack.attacker === recipient) { recipientAttackPower = recipient.getPower(); assert.equal(recipientAttackPower, recipientPower + grantedAmount, 'Actual Advantage power stacks on native current recipient stats'); } });
    eg.game.on('onAttackEnd', e => { if(firstStrike&&!settled&&e.attack.attacker===firstAttacker)firstAttackEnded=true; if (!settled && recipientAttack && e.attack.attacker === recipient) recipientAttackEnded = true; });
    function checkGrant(pid) {
        assert.ok(dead && defeatEvent && titleSeen, 'Actual source defeat and exact context title witnessed'); assert.equal(source.zoneName, 'discard');
        tokens = advantages().slice(); const count = p.decline ? 0 : p.expectedAmount;
        assert.equal(eg.game.allCards.filter(card=>card.isAdvantage?.()&&!initialAdvantageIds.has(id(card))).length,count,'No unused or declined extra Advantage identities allocated');
        assert.equal(tokens.length, count); assert.equal(created.length, count, 'Only this captured source creates the expected native tokens');
        assert.equal(new Set(tokens).size, count); assert.equal(new Set(tokens.map(id)).size, count);
        assert.deepEqual(new Set(tokens), new Set(created), 'Attached identities are the actual generated identities');
        for (const token of tokens) { assert.equal(token.owner, recipient.controller); assert.equal(token.controller, recipient.controller); assert.equal(token.parentCard, recipient); }
        assert.equal(recipient.getPower(), recipientPower + count); assert.equal(recipient.getHp(), recipientHp);
        if (p.cause === 'combat') { assert.ok(damages.some(e => e.card === source && e.damageSource.type === 'attack')); assert.equal(donor.zoneName, 'discard', 'Actual source combat also defeats its X-Wing defender'); }
        if (p.cause === 'direct-damage' || p.cause === 'attack-ability-damage') assert.ok(damages.some(e => e.card === source && e.damageSource.type === 'ability'));
        observe('resolved-advantage', pid); grantChecked = true; roundOfGrant = eg.round;
    }
    function checkExpiry(pid) {
        assert.equal(recipientAttackPower, recipientPower + grantedAmount); assert.equal(advantages().length, 0);
        assert.deepEqual(new Set(tokenDefeats), new Set(tokens), 'Each exact original token expires on this recipient attack end');
        for (const token of tokens) { assert.equal(token.zoneName, 'outsideTheGame'); assert.equal(token.isAttached(), false); }
        assert.equal(recipient.getPower(), recipientPower); observe('recipient-attack-end', pid); settled = true;
    }
    const completion = terminalCompletion(eg, 6000);
    try {
        while (true) {
            const pid = completion.nextActor(step); if (!pid) break;
            const actions = expandActions(eg, eg.legalActions(pid)), prompt = eg.player(pid).currentPrompt(), window = eg.isActionWindow(pid); let chosen;
            if (window) {
                records.push(actionWindowState(eg, pid, step));
                if(shieldCase&&firstAttackEnded&&!settled){assert.equal(dead,false);assert.equal(titleSeen,false);assert.equal(source.isInPlay(),true);assert.equal(source.damage,0);assert.equal(initialShield.zoneName,'outsideTheGame');assert.equal(initialShield.isAttached(),false);assert.equal(donor.zoneName,'discard');assert.equal(created.length,0);assert.equal(advantages().length,0);assert.ok(!damages.some(e=>e.card===source));observe('shield-cancels-first-strike-no-death-trigger',pid);Object.assign(witness.observations.at(-1),{shieldId:id(initialShield),shieldZone:initialShield.zoneName,shieldAttached:initialShield.isAttached(),sourceDamage:source.damage,sourceAlive:source.isInPlay(),sourceTriggerCount:0,generatedAdvantageIds:created.map(id)});settled=true;}
                if (dead && !grantChecked) checkGrant(pid);
                if (grantChecked && !phaseChecked && eg.round > roundOfGrant) { assert.deepEqual(advantages().map(id), tokens.map(id), 'Exact Advantage identities persist across regroup'); assert.equal(recipient.getPower(), recipientPower + grantedAmount); observe('phase-boundary', pid); phaseChecked = true; }
                if (recipientAttackEnded && !settled) checkExpiry(pid);
                if (!started && pid === attackPlayer.id) {
                    const card = firstStrike ? activation : p.cause === 'combat' ? source : p.cause === 'attack-ability-damage' ? donor : activation;
                    chosen = actions.find(a => a.cardUuid === card.uuid); assert.ok(chosen, 'Real ordinary attack or paid cause activation'); started = true;
                    if (!['combat', 'attack-ability-damage'].includes(p.cause)) { paidCard = card; initialReady = ready(paymentPlayer); }
                } else if (!settled && phaseChecked && !recipientAttack && pid === recipient.controller.id && !recipient.exhausted) { chosen = actions.find(a => a.cardUuid === recipient.uuid); assert.ok(chosen); recipientAttack = true; }
                else if (!settled) chosen = actions.find(a => a.arg === 'pass');
                else {
                    // Complete with existing ordinary units only. Extra Fiend hand
                    // copies could introduce intentionally uncovered unique causes.
                    chosen = actions.find(a => a.cardUuid && eg.game.allCards.some(c => c.uuid === a.cardUuid && live(c) && c.controller.id === pid));
                    chosen ??= actions.find(a => a.arg === 'pass');
                }
            } else {
                if (/resourc/i.test(prompt.menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done');
                else if (!settled && dead && !grantChecked) {
                    const title = `Give ${p.expectedAmount} Advantage tokens to a unit`;
                    if (prompt.menuTitle === title || actions.some(a => a.label === title)) { titleSeen = true; assert.equal(source.zoneName, 'discard'); observe('captured-source-selector', pid, actions, false); }
                    if (titleSeen) {
                        chosen = p.decline ? actions.find(a => a.arg === 'passAbility') ?? actions.find(a => a.arg === 'pass') : actions.find(a => a.cardUuid === recipient.uuid);
                        assert.ok(chosen, 'Actual optional decline or physical own/enemy recipient');
                    }
                }
                if(!chosen&&firstStrike&&!settled&&!dead) chosen=actions.find(a=>a.cardUuid===firstAttacker.uuid)??actions.find(a=>a.cardUuid===firstDefender.uuid);
                if (!chosen && prompt.menuTitle === 'Choose a target for attack') {
                    const defender = recipientAttack ? recipient.controller.opponent.base : p.cause === 'combat' && !dead ? donor : enemy.base;
                    chosen = actions.find(a => a.cardUuid === defender.uuid);
                    if (settled) chosen ??= actions.find(a => a.cardUuid && eg.game.allCards.some(c => c.uuid === a.cardUuid && c.controller.id !== pid));
                    assert.ok(chosen, 'Actual legal combat/base defender');
                }
                if (!chosen && !dead && ['direct-damage', 'direct-defeat', 'attack-ability-damage'].includes(p.cause)) chosen = actions.find(a => a.cardUuid === source.uuid);
                chosen ??= actions.find(a => a.arg === 'all'); chosen ??= actions.find(a => /trigger|resolve/i.test(a.label ?? '')); chosen ??= actions.find(a => a.arg === 'done'); chosen ??= actions.find(a => a.arg === 'passAbility');
            }
            chosen ??= bot.choose({ game: eg, pid, actions, rng }); assert.ok(chosen);
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window }, actions: actions.map(a => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            eg.apply(pid, chosen, rng); step++;
        }
        assert.ok(settled && eg.over, 'Intended source effect and complete ordinary terminal game');
        witness.terminalCompletion = completion.assertComplete();
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) }); witness.coverageObligationIds = [...scenario.coverageObligationIds]; return { records, witness };
    } catch (error) { error.diagnostic = { records, witness }; throw error; } finally { bot.close?.(); }
}
module.exports = { fixture, actionWindowState, assertActionWindowRecords, dependencies: ['lab/kessel-reference/pipeline/terminal-completion.js','lab/kessel-reference/pipeline/defeat-cause-probe-fixture.js', 'lab/kessel-reference/pipeline/probe-fixture.js', 'engine/env.js', 'bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/unit-entry-state.js','engine/rng.js','kessel:crates/kessel/src/defeat_cause_contract.rs', 'bots/omni/rs/support-state.js', 'bots/players/index.js', 'kessel:cards/pipeline/defeat-cause-probes.js'] };
