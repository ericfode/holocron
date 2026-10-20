'use strict';
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.equal(p.family, 'distributed-damage');
    const reverse = p.sourceSeat === 2;
    const swap = owner => owner === 'self' ? 'opponent' : 'self';
    const relocated = reverse || p.foreignControl;
    const construction = relocated ? { ...scenario, probe: { ...p, sourceInPlay: false, targets: [...p.targets.map(t => ({ ...t, owner: reverse ? swap(t.owner) : t.owner, attachments: t.attachments?.map(a => ({ ...a, ...(a.owner && reverse ? { owner: swap(a.owner) } : {}) })) })), { code: p.cardId, owner: p.foreignControl ? (reverse ? 'self' : 'opponent') : 'opponent', ...(p.sourceInPlay ? { arena: p.sourceArena, damage: p.sourceDamage ?? 0 } : { zone: 'hand' }) }, ...(reverse && p.activationCode ? [{ code: p.activationCode, owner: 'opponent', zone: 'hand' }] : [])] } } : scenario;
    const setup = await constructProbeFixture(env, pool, construction, seed);
    const { eg, rng, bot, deck } = setup;
    const own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const targets = setup.targets.slice();
    const activation = reverse && p.activationCode ? targets.pop() : setup.activation;
    const source = relocated ? targets.pop() : setup.source;
    if (p.foreignControl) {
        assert.equal(source.owner, enemy, 'Staged source physical ownership');
        source.takeControl(own);
        eg.game.resolveGameState(true); eg.game.continue();
        assert.equal(source.controller, own, 'Construction stages control using engine API');
    }
    const id = c => eg.cardId(c.uuid), live = c => c.isInPlay();
    const witness = { observations: [], events: [], coverageObligationIds: [] };
    const records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['distributed-damage-probe', 'distributed-damage-probe'], decks: [deck, deck], scenario: scenario.name, constructionParameters: p, fixtureConstruction: 'Stage explicit admitted recipients and native Shields; normally pay for source or defeat event; finish ordinary game.' }];
    let attackStarted = false, attackEnded = false, checkedDistribution = false;
    let started = false, played = false, defeated = false, settled = false, distribution = false, uniqueChosen = false, step = 0, paidBefore = 0;
    const ready = () => own.getCardsInZone('resource').filter(c => !c.exhausted).length;
    const playedCost = card => { const aspects = [...own.getAspectsForCosts()]; let amount = card.cardData.cost; for (const aspect of card.cardData.aspects) { const i = aspects.indexOf(aspect); if (i < 0) amount += 2; else aspects.splice(i, 1); } return amount; };
    const baseline = new Map(targets.map(c => [c, { damage: c.damage, hp: c.getHp(), shields: c.upgrades.filter(u => u.isShield?.()).slice(), controller: c.controller }]));
    const drawBefore = { hand: enemy.getCardsInZone('hand').slice(), deck: enemy.drawDeck.slice() };
    const drawEvents = [];
    const damage = [], metas = [], deaths = [];
    let submittedOrder = [];
    const assignedAmounts = new Map((p.assignments ?? []).map(a => [targets[a.index], a.amount]));
    eg.game.on('onAttackEnd', () => { if (attackStarted && !settled) attackEnded = true; });
    const observe = (stage, pid, actions) => witness.observations.push({ stage, actor: pid ? eg.seatOf(pid) : null, actions: actions?.map(a => canonicalAction(eg, a)), ...(stage === 'unique-source-choice' ? {} : { state: fullState(eg, pid) }) });
    eg.game.on('onCardPlayed', e => { if (started && e.card === (p.trigger === 'whenPlayed' ? source : activation) && !e.isCancelledOrReplaced) played = true; });
    eg.game.on('onCardDefeated', e => { if (!started || settled || e.isCancelledOrReplaced) return; if (e.card === source) defeated = true; if (assignedAmounts.has(e.card)) {
            for (const [card, amount] of assignedAmounts) {
                const b = baseline.get(card);
                if (card !== e.card && live(card) && !b.shields.length) {
                    const combat = p.liveAttack && targets[p.attackTargetIndex] === card ? source.cardData.power : 0;
                    assert.equal(card.damage, Math.min(b.hp, b.damage + amount + combat), 'Every primary assignment applied before first recipient leaves play');
                }
            }
        }
        deaths.push(e.card); witness.events.push({ name: 'onCardDefeated', card: id(e.card) }); });
    eg.game.on('onDamageDealt', e => { if (!started || settled || e.isCancelledOrReplaced || e.damageSource?.card !== source || e.damageSource?.type !== 'ability') return; damage.push(e); witness.events.push({ name: 'onDamageDealt', card: id(e.card), amount: e.damageDealt, source: id(source) }); });
    eg.game.on('distributeDamage', e => { if (!started || settled || e.context?.source !== source) return; metas.push(e); witness.events.push({ name: 'distributeDamage', totalDistributed: e.totalDistributed, resolved: e.isResolved }); });
    eg.game.on('onCardsDrawn', e => {
        if (!started || settled || p.deathDrawIndex == null || e.context?.source !== targets[p.deathDrawIndex] || e.isCancelledOrReplaced) return;
        const droid = targets[p.deathDrawIndex];
        assert.equal(droid.zoneName, 'discard', 'Printed draw callback runs after physical Ant Droid defeat');
        assert.equal(damage.length, assignedAmounts.size, 'All primary child damage precedes printed death-trigger draw');
        for (const [card, amount] of assignedAmounts) {
            const b = baseline.get(card);
            if (live(card) && !b.shields.length) assert.equal(card.damage, Math.min(b.hp, b.damage + amount));
        }
        assert.equal(enemy.getCardsInZone('hand').length, drawBefore.hand.length + 1, 'Printed callback adds exactly one real hand card');
        assert.equal(enemy.drawDeck.length, drawBefore.deck.length - 1, 'Printed callback removes one real top deck card');
        assert.ok(enemy.getCardsInZone('hand').includes(drawBefore.deck[0]), 'Actual prior deck top enters hand');
        drawEvents.push(e);
        witness.events.push({ name: 'onCardsDrawn', source: id(droid), cards: e.cards.map(id), player: eg.seatOf(e.player.id), primaryDamageCount: damage.length });
    });
    function check() {
        if (!p.liveAttack) assert.ok(played, 'Ordinary paid hand play occurred');
        else assert.ok(attackStarted && attackEnded, 'Actual lethal attack completes with death ability');
        if (!p.liveAttack) assert.equal(ready(), paidBefore - playedCost(p.trigger === 'whenPlayed' ? source : activation), 'Exact printed and aspect resource payment');
        if (p.foreignControl) { assert.equal(source.controller, enemy, 'Departure restores printed owner'); assert.equal(source.owner, enemy); }
        if (p.trigger === 'whenDefeated') assert.ok(defeated && source.zoneName === 'discard', 'Actual defeat captures source ability');
        if (p.oldIndex != null) { assert.ok(uniqueChosen); assert.equal(source.zoneName, p.keep === 'old' ? 'discard' : 'groundArena'); }
        const eligible = targets.filter(c => baseline.get(c).controller === enemy && p.oldIndex !== targets.indexOf(c));
        assert.equal(distribution, eligible.length > 1, 'Only multiple legal targets require distribution prompt');
        const assignments = new Map((p.assignments ?? []).map(a => [targets[a.index], a.amount]));
        if (eligible.length === 1) assignments.set(eligible[0], 6);
        if (eligible.length) assert.equal([...assignments.values()].reduce((a,b) => a+b, 0), 6);
        let total = 0;
        for (const [card, b] of baseline) {
            if (p.oldIndex === targets.indexOf(card)) continue;
            const amount = assignments.get(card) ?? 0, applied = amount && !b.shields.length ? Math.min(amount, b.hp - b.damage) : 0;
            total += applied;
            const events = damage.filter(e => e.card === card);
            assert.equal(events.length, applied ? 1 : 0, 'Exactly one successful child per unprevented positive assignment');
            if (applied) assert.equal(events[0].damageDealt, applied, 'Damage capped on application, never allocation');
            const combatDamage = p.liveAttack && targets[p.attackTargetIndex] === card ? source.cardData.power : 0;
            const finalHp = p.auraRecipientIndex === targets.indexOf(card) ? b.hp - 1 : b.hp;
            if (b.damage + applied + combatDamage >= finalHp) assert.equal(card.zoneName, card.isLeader?.() ? 'base' : 'discard', 'Lethal assigned recipient defeated to correct zone');
            else { assert.ok(live(card)); assert.equal(card.damage, b.damage + applied + combatDamage, 'Exact assigned and nonrecipient wounds'); }
            const lost = amount && b.shields.length ? 1 : 0;
            assert.equal(b.shields.filter(t => deaths.includes(t)).length, lost, 'One exact Shield replaced assigned damage');
            assert.deepEqual((live(card) ? card.upgrades : []).filter(u => u.isShield?.()).map(id), b.shields.filter(t => !deaths.includes(t)).map(id), 'Unconsumed Shield identities and order survive');
        }
        if (p.deathDrawIndex != null) assert.equal(drawEvents.length, 1, 'Exactly one actual printed death-trigger draw');
        if (p.auraIndex != null) {
            assert.equal(targets[p.auraIndex].zoneName, 'discard');
            assert.equal(baseline.get(targets[p.auraRecipientIndex]).hp, targets[p.auraRecipientIndex].cardData.hp + 1, 'Live printed HP aura present during allocation');
            assert.equal(targets[p.auraRecipientIndex].zoneName, 'discard', 'Lost printed HP aura makes the already damaged recipient lethal');
        }
        assert.equal(metas.length, eligible.length ? 1 : 0, 'No-target skips meta; nonempty distribution resolves once');
        if (metas.length) { assert.equal(metas[0].totalDistributed, total, 'Meta totals successful children, including zero when all Shielded'); assert.equal(metas[0].isResolved, true, 'All prevented distribution still resolves its meta event'); }
        const executionOrder = eligible.length === 1 ? eligible : submittedOrder.slice().reverse();
        assert.deepEqual(damage.map(e => id(e.card)), executionOrder.filter(c => !baseline.get(c).shields.length).map(id), 'Pinned negative-order children reverse submitted Map insertion order');
        assert.deepEqual(deaths.filter(c => assignments.has(c) && !baseline.get(c).shields.length).map(id), damage.filter(e => baseline.get(e.card).damage + e.damageDealt + (p.liveAttack && targets[p.attackTargetIndex] === e.card ? source.cardData.power : 0) >= baseline.get(e.card).hp - (p.auraRecipientIndex === targets.indexOf(e.card) ? 1 : 0)).map(e => id(e.card)), 'Lethal primary recipients leave in damage event order');
        observe('resolved-distribution');
        checkedDistribution = true;
        settled = !p.combatAfterPlay;
    }
    try {
        while (!eg.over && step < 5000) {
            const pid = eg.ids.find(pid => eg.legalActions(pid).length); assert.ok(pid);
            const actions = expandActions(eg, eg.legalActions(pid)), window = eg.isActionWindow(pid), prompt = eg.player(pid).currentPrompt();
            let chosen;
            if (window) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (!checkedDistribution && started && !settled && (p.liveAttack ? attackEnded : played)) check();
                if (!settled && checkedDistribution && p.combatAfterPlay && attackEnded) {
                    const defender = targets[p.attackTargetIndex], b = baseline.get(defender), assigned = p.assignments.find(a => a.index === p.attackTargetIndex)?.amount ?? 0;
                    assert.equal(defender.zoneName, 'discard');
                    assert.equal(enemy.base.damage, source.cardData.power - (b.hp - b.damage - assigned), 'Actual printed Overwhelm excess after distribution');
                    observe('printed-overwhelm-combat'); settled = true;
                }
                if (!started && pid === own.id && (!p.liveAttack || !source.exhausted)) { chosen = actions.find(a => a.cardUuid === (p.liveAttack || p.trigger === 'whenPlayed' ? source : activation).uuid); assert.ok(chosen, 'Ordinary paid focus activation'); paidBefore = ready(); started = true; if (p.liveAttack) attackStarted = true; }
                else if (!settled && checkedDistribution && p.combatAfterPlay && !attackStarted && pid === own.id && !source.exhausted) { chosen = actions.find(a => a.cardUuid === source.uuid); assert.ok(chosen); attackStarted = true; }
                else if (!settled) chosen = actions.find(a => a.arg === 'pass');
            } else if (started && !settled) {
                if (attackStarted && /target for attack/i.test(prompt.menuTitle ?? '')) { chosen = actions.find(a => a.cardUuid === targets[p.attackTargetIndex].uuid); assert.ok(chosen, 'Actual legal attack target'); }
                else if (actions.some(a => a.kind === 'distribute')) {
                    const expected = (p.assignments ?? []).map(a => [targets[a.index].uuid, a.amount]);
                    chosen = actions.find(a => a.kind === 'distribute' && a.split.length === expected.length && a.split.every(s => expected.some(([uuid,amount]) => s.id === uuid && s.amount === amount)));
                    assert.ok(chosen, 'Printed exact allocation exists in complete action set');
                    const legalTargets = targets.filter(c => baseline.get(c).controller === enemy && p.oldIndex !== targets.indexOf(c));
                    const rows = actions.filter(a => a.kind === 'distribute');
                    let count = 1; for (let i = 1; i <= 6; i++) count = count * (legalTargets.length + i - 1) / i;
                    assert.equal(rows.length, count, 'Complete six-damage integer composition domain');
                    for (const row of rows) {
                        assert.equal(row.split.reduce((n,s) => n+s.amount,0), 6);
                        assert.equal(new Set(row.split.map(s => s.id)).size, row.split.length);
                        assert.ok(row.split.every(s => Number.isInteger(s.amount) && s.amount > 0 && legalTargets.some(c => c.uuid === s.id)));
                    }
                    submittedOrder = chosen.split.map(s => targets.find(c => c.uuid === s.id));
                    assert.equal(pid, own.id); distribution = true; observe('distribution-choice', pid, actions);
                } else if (p.oldIndex != null && actions.some(a => a.cardUuid === source.uuid) && actions.some(a => a.cardUuid === targets[p.oldIndex].uuid)) { chosen = actions.find(a => a.cardUuid === (p.keep === 'old' ? source : targets[p.oldIndex]).uuid); uniqueChosen = true; observe('unique-source-choice',pid,actions); }
                else if (p.trigger === 'whenDefeated' && !defeated) chosen = actions.find(a => a.cardUuid === source.uuid);
                chosen ??= actions.find(a => a.cardUuid && targets.some(c => live(c) && c.upgrades.some(u => u.isShield?.() && u.uuid === a.cardUuid)));
                chosen ??= actions.find(a => a.kind === 'button' && /trigger|resolve|play|yes/i.test(a.label ?? ''));
                chosen ??= actions.find(a => a.arg === 'done');
            }
            chosen ??= bot.choose({ game: eg, pid, actions, rng }); assert.ok(chosen);
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window }, actions: actions.map(a => canonicalAction(eg,a)), chosen: canonicalAction(eg,chosen).key, events: [] });
            eg.apply(pid,chosen,rng); step++;
        }
        assert.ok(settled && eg.over, 'Source assertion and complete ordinary terminal game');
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) }); witness.coverageObligationIds = [...scenario.coverageObligationIds];
        return { records, witness };
    } catch (error) { error.diagnostic = { records, witness }; throw error; } finally { bot.close?.(); }
}
module.exports = { fixture, dependencies: ['kessel:cards/pipeline/distributed-damage-probes.js', 'lab/kessel-reference/pipeline/distributed-damage-probe-fixture.js', 'lab/kessel-reference/pipeline/probe-fixture.js', 'bots/omni/rs/make-pool.js', 'engine/env.js', 'bots/omni/rs/state.js', 'bots/players/index.js'] };
