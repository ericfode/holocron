'use strict';
const { terminalCompletion } = require('./terminal-completion');
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.equal(p.family, 'ambush-context');
    assert.ok(p.targets.every(t => (t.damage ?? 0) >= 0), 'Physical construction never uses negative damage');
    const reverse = p.sourceSeat === 2;
    const construction = reverse ? { ...scenario, probe: { ...p, targets: [...p.targets.map(t => ({ ...t, owner: t.owner === 'self' ? 'opponent' : 'self' })), { code: p.cardId, owner: 'opponent', zone: 'hand' }] } } : scenario;
    const setup = await constructProbeFixture(env, pool, construction, seed);
    const { eg, rng, bot, deck } = setup;
    const own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const targets = setup.targets.slice(), source = reverse ? targets.pop() : setup.source;
    const id = card => eg.cardId(card.uuid), live = card => card.isInPlay?.();
    const records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['ambush-context-probe', 'ambush-context-probe'], decks: [deck, deck], scenario: scenario.name, constructionParameters: p,
        fixtureConstruction: 'Stage explicit nonnegative physical targets; normally pay for Heroic Purrgil, accept/decline actual Ambush, naturally ready for ordinary attack/cancel/retry, then complete an ordinary game.' }];
    const witness = { observations: [], events: [], coverageObligationIds: [] };
    let step = 0, started = false, played = false, entryChecked = false, offered = false, accepted = false, normalStarted = false, normalFinished = false, cancelled = false, settled = false, paidBefore = 0, pendingSeen = false;
    const combats = [], damage = [], defeats = [];
    const ready = () => own.getCardsInZone('resource').filter(card => !card.exhausted).length;
    const cost = () => { const aspects = [...own.getAspectsForCosts()]; let total = source.cardData.cost; for (const a of source.cardData.aspects) { const i = aspects.indexOf(a); if (i < 0) total += 2; else aspects.splice(i, 1); } return total; };
    const observe = (stage, pid, actions, snapshot = true) => witness.observations.push({ stage, actor: pid ? eg.seatOf(pid) : null, actions: actions?.map(a => canonicalAction(eg, a)), ...(snapshot ? { state: fullState(eg, pid) } : {}) });
    eg.game.on('onCardPlayed', e => { if (e.card === source && !e.isCancelledOrReplaced) { played = true; assert.equal(paidBefore - ready(), cost(), 'Actual printed/aspect resource payment'); witness.events.push({ name: 'onCardPlayed', card: id(source), paid: paidBefore - ready() }); } });
    eg.game.on('onAttackDamageResolved:preResolve', e => {
        if (e.attack.attacker !== source || settled) return;
        const ambush = e.attack.isAmbush, power = source.getPower();
        assert.equal(power, ambush ? 5 : 3, 'Persistent +2 is derived only for the actual Ambush attack');
        assert.equal(source.isAttacking(), true); assert.equal(source.activeAttack, e.attack);
        const defender=e.attack.getAllTargets()[0];
        const row = { name: 'combat-context', ambush, power, target: id(defender), defenderPower: defender.isUnit?.()?defender.getPower():null, defenderAttacking: defender.isUnit?.()?defender.isAttacking():false, defenderAmbushContext: defender.isUnit?.()?defender.activeAttack?.isAmbush??false:false };
        if(ambush&&p.assertDefenderNoBonus){assert.equal(defender.getPower(),3,'Defending Purrgil never gains the attacker Ambush bonus');assert.equal(defender.isAttacking(),false);assert.equal(defender.activeAttack,e.attack);assert.equal(defender.activeAttack.isAmbush,true,'Shared Ambush context alone is insufficient');}
        combats.push(row); witness.events.push(row);
    });
    eg.game.on('onDamageDealt', e => { if (!started || settled || e.isCancelledOrReplaced) return; damage.push(e); witness.events.push({ name: 'onDamageDealt', card: id(e.card), amount: e.damageDealt, type: e.damageSource?.type, source: e.damageSource?.card ? id(e.damageSource.card) : null, combatSources: e.damageSource?.damageDealtBy?.map(id) ?? [] }); });
    eg.game.on('onCardDefeated', e => { if (!started || settled || e.isCancelledOrReplaced) return; defeats.push(e.card); witness.events.push({ name: 'onCardDefeated', card: id(e.card) }); });
    eg.game.on('onAttackEnd', e => { if (e.attack.attacker === source && !settled) { if (!e.attack.isAmbush) normalFinished = true; witness.events.push({ name: 'onAttackEnd', ambush: e.attack.isAmbush }); } });
    function checkEntry() {
        const declined = p.decline || ['decline', 'cancel-retry'].includes(p.scenario), empty = p.scenario === 'no-enemy';
        assert.equal(combats.filter(c => c.ambush).length, declined || empty ? 0 : 1, 'Exact actual Ambush acceptance/decline/no-target path');
        assert.equal(offered, !empty, 'No impossible Ambush offer without an enemy target');
        if (live(source)) { assert.equal(source.getPower(), 3, 'Ambush context ends and no phase-stat boost remains'); assert.equal(source.exhausted, true); }
        if (p.scenario === 'attacker-death') { assert.equal(source.zoneName, 'discard'); assert.equal(targets[p.defenderIndex ?? 0].damage, 5); }
        if (p.scenario.startsWith('defender-death')) {
            assert.equal(targets[p.defenderIndex ?? 0].zoneName, 'discard'); assert.ok(pendingSeen, 'Real Legacy Run trigger suspends the live Ambush attack');
            const assignment = p.deathDistribution ?? [{ index: 'source', amount: p.scenario.endsWith('lethal') ? 6 : 2 }, ...(p.scenario.endsWith('lethal') ? [] : [{ index: 1, amount: 4 }])];
            for (const part of assignment) {
                const card = part.index === 'source' ? source : targets[part.index];
                const events = damage.filter(e => e.card === card && e.damageSource?.type === 'ability');
                assert.equal(events.length, 1); assert.equal(events[0].damageSource.card, targets[p.defenderIndex ?? 0]);
                assert.equal(events[0].damageDealt, Math.min(part.amount, card === source ? 3 : card.cardData.hp), 'Actual requested distribution caps applied wounds');
            }
            if (p.scenario.endsWith('lethal')) assert.equal(source.zoneName, 'discard'); else { assert.ok(live(source)); assert.equal(source.damage, 5); assert.equal(targets[1].damage, 4); }
        }
        if (!declined && !empty) {
            const defender = targets[p.sentinelIndex ?? p.defenderIndex ?? 0];
            const hits = damage.filter(e => e.card === defender && e.damageSource?.type === 'attack' && e.damageSource.damageDealtBy?.includes(source));
            assert.equal(hits.length, 1); assert.equal(hits[0].damageDealt, Math.min(5, defender.cardData.hp), 'Actual Ambush damage uses power5 and real HP cap');
            const retaliation=damage.filter(e=>e.card===source&&e.damageSource?.type==='attack'&&e.damageSource.damageDealtBy?.includes(defender));
            assert.equal(retaliation.length,1,'Physical defender deals one actual retaliation event');
            assert.equal(retaliation[0].damageDealt,Math.min(defender.cardData.power,source.cardData.hp),'Defender uses printed power without attacker-only bonus');
            if(p.assertDefenderNoBonus){assert.equal(defender.damage,5);assert.equal(source.damage,3);assert.equal(retaliation[0].damageDealt,3);}
        }
        observe('resolved-entry-ambush'); entryChecked = true;
        if (!live(source) || p.laterNormal === false) settled = true;
    }
    function checkNormal() {
        assert.equal(combats.filter(c => !c.ambush).length, 1);
        const hit = damage.filter(e => e.card === enemy.base && e.damageSource?.type === 'attack' && e.damageSource.damageDealtBy?.includes(source));
        assert.equal(hit.length, 1); assert.equal(hit[0].damageDealt, 3, 'Later ordinary attack deals printed3');
        if (p.cancelRetry || p.scenario === 'cancel-retry') assert.ok(cancelled, 'Actual normal target cancellation and retry');
        assert.equal(source.getPower(), 3); assert.equal(source.isAttacking(), false);
        observe('normal-attack-after-ambush'); settled = true;
    }
    const completion = terminalCompletion(eg, 5000);
    try {
        while (true) {
            const pid = completion.nextActor(step); if (!pid) break;
            const actions = expandActions(eg, eg.legalActions(pid)), window = eg.isActionWindow(pid), prompt = eg.player(pid).currentPrompt(); let chosen;
            if (window) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (played && !entryChecked) checkEntry();
                if (normalFinished && !settled) checkNormal();
                if (!started && pid === own.id) { chosen = actions.find(a => a.cardUuid === source.uuid); assert.ok(chosen, 'Ordinary paid focus play'); paidBefore = ready(); started = true; }
                else if (!settled && entryChecked && pid === own.id && live(source) && !source.exhausted) { if(cancelled&&!normalFinished){assert.equal(source.isAttacking(),false,'Cancelled ordinary attack leaves no live attack');assert.equal(source.getPower(),3);observe('normal-ready-after-cancel',pid,actions);} chosen = actions.find(a => a.cardUuid === source.uuid); assert.ok(chosen); normalStarted = true; }
                else if (!settled) chosen = actions.find(a => a.arg === 'pass');
                if (settled) { chosen = actions.find(a => a.arg === 'pass'); assert.ok(chosen, 'Settled focus completes through actual legal Pass actions'); }
            } else if (!settled) {
                if (/resourc/i.test(prompt.menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done');
                else if (played && !entryChecked && actions.some(a => a.label === 'Trigger') && actions.some(a => a.label === 'Pass')) {
                    assert.equal(source.exhausted, true); assert.equal(source.getPower(), 3);
                    assert.deepEqual(actions.map(a => a.label).sort(), ['Pass', 'Trigger']);
                    offered = true; accepted = !(p.decline || ['decline', 'cancel-retry'].includes(p.scenario)); chosen = actions.find(a => a.label === (accepted ? 'Trigger' : 'Pass'));
                    observe('actual-ambush-offer', pid, actions, false);
                } else if (prompt.menuTitle === 'Choose a target for attack') {
                    const cards = actions.filter(a => a.kind === 'card');
                    if (!normalStarted) {
                        assert.ok(accepted); assert.equal(actions.some(a => a.arg === 'cancel' || a.label === 'Pass attack'), false, 'Accepted Ambush target choice is mandatory');
                        assert.equal(cards.some(a => a.cardUuid === enemy.base.uuid), false);
                        const eligible = p.sentinelIndex != null ? [targets[p.sentinelIndex]] : targets.filter(c => live(c) && c.controller === enemy && c.cardData.arena === 'space');
                        assert.deepEqual(new Set(cards.map(a => a.cardUuid)), new Set(eligible.map(c => c.uuid)), 'Exact enemy space targets and live Sentinel precedence');
                        chosen = cards.find(a => a.cardUuid === targets[p.sentinelIndex ?? p.defenderIndex ?? 0].uuid); assert.ok(chosen);
                        observe('mandatory-ambush-target', pid, actions, false);
                    } else {
                        assert.equal(source.getPower(), 3);
                        if ((p.cancelRetry || p.scenario === 'cancel-retry') && !cancelled) { chosen = actions.find(a => a.arg === 'cancel'); assert.ok(chosen); cancelled = true; observe('normal-cancel', pid, actions, false); }
                        else { chosen = cards.find(a => a.cardUuid === enemy.base.uuid); assert.ok(chosen); observe('normal-target', pid, actions, false); }
                    }
                } else if (actions.some(a => a.kind === 'distribute')) {
                    assert.ok(p.scenario.startsWith('defender-death')); assert.equal(pid, enemy.id);
                    assert.equal(targets[p.defenderIndex ?? 0].zoneName, 'discard');
                    assert.equal(source.getPower(), 5); assert.equal(source.isAttacking(), true); assert.equal(eg.game.currentAttack.isAmbush, true); assert.equal(source.activeAttack, eg.game.currentAttack);
                    const assignment = p.deathDistribution ?? [{ index: 'source', amount: p.scenario.endsWith('lethal') ? 6 : 2 }, ...(p.scenario.endsWith('lethal') ? [] : [{ index: 1, amount: 4 }])];
                    chosen = actions.find(a => a.kind === 'distribute' && a.split.length === assignment.length && a.split.every(s => assignment.some(part => (part.index === 'source' ? source : targets[part.index]).uuid === s.id && part.amount === s.amount)));
                    assert.ok(chosen, 'Exact ordinary Legacy Run distribution action'); pendingSeen = true;
                    witness.observations.push({ stage: 'pending-real-defender-death', actor: eg.seatOf(pid), source: id(source), sourcePower: source.getPower(), attacking: source.isAttacking(), isAmbush: eg.game.currentAttack.isAmbush, actions: actions.map(a => canonicalAction(eg, a)) });
                }
                chosen ??= actions.find(a => a.arg === 'all'); chosen ??= actions.find(a => a.kind === 'button' && /trigger|resolve|yes/i.test(a.label ?? '')); chosen ??= actions.find(a => a.arg === 'done');
            }
            if ((settled || eg.over) && !window && /resourc/i.test(prompt.menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done') ?? chosen;
            chosen ??= bot.choose({ game: eg, pid, actions, rng }); assert.ok(chosen);
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window }, actions: actions.map(a => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            eg.apply(pid, chosen, rng); step++;
        }
        assert.ok(settled && eg.over, 'Actual source-focused behavior and complete ordinary terminal game');
        witness.terminalCompletion = completion.assertComplete();
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) }); witness.coverageObligationIds = [...scenario.coverageObligationIds]; return { records, witness };
    } catch (error) { error.diagnostic = { records, witness }; throw error; } finally { bot.close?.(); }
}
module.exports = { fixture, dependencies: ['lab/kessel-reference/pipeline/terminal-completion.js','lab/kessel-reference/pipeline/ambush-context-probe-fixture.js', 'lab/kessel-reference/pipeline/probe-fixture.js', 'bots/omni/rs/state.js', 'bots/omni/rs/support-state.js', 'engine/env.js', 'bots/players/index.js', 'kessel:cards/pipeline/ambush-context-probes.js'] };
