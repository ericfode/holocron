'use strict';
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');

// These expectations come from the two source windows: own base first, then
// one captured global arena batch. Construction never replaces a registration.
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.equal(p.family, 'self-base-arena-damage');
    assert.equal(p.cardId, 'ASH_151');
    assert.equal(p.amount, 5);
    assert.ok([1, 2].includes(p.sourceSeat));
    const names = ['empty', 'mixed-shields-global-order', 'multi-owner-shield-menus', 'aura-death', 'own-base-lethal-death-heal', 'winner-latched-then-mandatory-choice', 'enemy-base-lethal-death-trigger', 'death-draw-order'];
    assert.ok(names.includes(p.scenario), 'Known source-distinguishing scenario');
    const reverse = p.sourceSeat === 2, swap = owner => owner === 'self' ? 'opponent' : 'self';
    const construction = reverse ? { ...scenario, probe: { ...p, initiative: 'opponent', targets: [...p.targets.map(t => ({ ...t, owner: swap(t.owner), attachments: t.attachments?.map(a => ({ ...a, ...(a.owner ? { owner: swap(a.owner) } : {}) })) })), { code: p.cardId, owner: 'opponent', zone: 'hand' }] } } : scenario;
    const setup = await constructProbeFixture(env, pool, construction, seed);
    const { eg, rng, bot, deck } = setup;
    const own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const targets = setup.targets.slice(), source = reverse ? targets.pop() : setup.source;
    const id = card => eg.cardId(card.uuid), ready = () => own.getCardsInZone('resource').filter(c => !c.exhausted).length;
    assert.equal(source.controller, own);
    own.base.damage = p.baseDamage ?? 0;
    enemy.base.damage = p.enemyBaseDamage ?? 0;
    eg.game.resolveGameState(true); eg.game.continue();
    const initialBases = [own.base.damage, enemy.base.damage];
    const initialGlobalOrder = eg.game.getArenaUnits().slice();
    assert.equal(initialGlobalOrder.length, targets.length, 'No undeclared in-play recipients');
    const baseline = new Map(targets.map(c => [c, { damage: c.damage, hp: c.getHp(), controller: c.controller, shields: c.upgrades.filter(u => u.isShield?.()).slice() }]));
    const scout = targets.find(c => c.cardData.internalName === 'star-wing-scout');
    const initialHand = own.getCardsInZone('hand').slice(), initialDeck = own.drawDeck.slice();
    const witness = { observations: [], events: [], coverageObligationIds: [] };
    const records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['self-base-arena-damage-probe', 'self-base-arena-damage-probe'], decks: [deck, deck], scenario: scenario.name, constructionParameters: p, fixtureConstruction: 'Stage declared physical admitted recipients, native Shields and base damage; normally pay and play actual Operation Cinder; resolve mandatory choices even after winner latch; complete the ordinary game.' }];
    let started = false, played = false, settled = false, step = 0, paidBefore = 0, recipientDepartureChecked = false;
    const damage = [], deaths = [], heals = [], draws = [], shieldMenus = [], ownerMenus = [], terminalChoices = [];
    const state = () => ({ winner: eg.winner ?? null, bases: [own.base.damage, enemy.base.damage], units: targets.map(c => ({ id: id(c), zone: c.zoneName, damage: c.isInPlay() ? c.damage : null, hp: c.isInPlay() ? c.getHp() : null, shields: c.isInPlay() ? c.upgrades.filter(u => u.isShield?.()).map(id) : [] })), globalOrder: eg.game.getArenaUnits().map(id) });
    const event = (name, e) => witness.events.push({ name, card: e.card ? id(e.card) : null, amount: e.amount ?? null, changed: e.damageDealt ?? e.damageHealed ?? null, state: state() });
    eg.game.on('onCardPlayed', e => { if (started && e.card === source && !e.isCancelledOrReplaced) played = true; });
    eg.game.on('onDamageDealt', e => {
        if (!played || settled || e.isCancelledOrReplaced) return;
        if (e.damageSource?.card === source) damage.push(e);
        event('onDamageDealt', e);
    });
    eg.game.on('onCardDefeated', e => {
        if (!played || settled || e.isCancelledOrReplaced) return;
        if (baseline.has(e.card) && !recipientDepartureChecked) {
            for (const [card, b] of baseline) {
                if (!b.shields.length && card.isInPlay()) assert.equal(card.damage, b.damage + Math.min(5, b.hp - b.damage), 'All primary damage exists before first recipient departure');
            }
            recipientDepartureChecked = true;
        }
        deaths.push(e.card); event('onCardDefeated', e);
    });
    eg.game.on('onDamageHealed', e => { if (played && !settled && !e.isCancelledOrReplaced) { heals.push(e); event('onDamageHealed', e); } });
    eg.game.on('onCardsDrawn', e => {
        if (!played || settled || e.isCancelledOrReplaced || e.context?.source !== scout) return;
        assert.equal(damage.filter(d => baseline.has(d.card)).length, baseline.size, 'Printed death draw follows the whole primary batch');
        assert.equal(scout.zoneName, 'discard');
        draws.push(e); witness.events.push({ name: 'onCardsDrawn', source: id(scout), player: eg.seatOf(e.player.id), cards: (e.cards ?? []).map(id), state: state() });
    });
    function playedCost() {
        const aspects = [...own.getAspectsForCosts()]; let cost = source.cardData.cost;
        for (const aspect of source.cardData.aspects) { const i = aspects.indexOf(aspect); if (i < 0) cost += 2; else aspects.splice(i, 1); }
        return cost;
    }
    function check() {
        assert.ok(played, 'Normally paid and played pinned focus event');
        assert.equal(ready(), paidBefore - playedCost(), 'Exact printed plus aspect resource payment');
        assert.equal(damage[0]?.card, own.base, 'Own base damage precedes the unit window');
        assert.equal(damage[0].damageDealt, 5);
        assert.equal(damage.filter(e => e.card === own.base).length, 1);
        assert.ok(!damage.some(e => e.card === enemy.base), 'Cinder never targets the opposing base');
        assert.deepEqual(damage.slice(1).map(e => id(e.card)), initialGlobalOrder.filter(c => !baseline.get(c).shields.length).map(id), 'Exact captured physical mixed-controller arena order');
        for (const [card, b] of baseline) {
            const rows = damage.filter(e => e.card === card);
            assert.equal(rows.length, b.shields.length ? 0 : 1, 'One unprevented primary event per unit');
            if (rows.length) assert.equal(rows[0].damageDealt, Math.min(5, b.hp - b.damage));
            const consumed = b.shields.filter(t => deaths.includes(t));
            // ReplacementEffectWindow reconsolidates with stashed alternates
            // before unresolved selected shields. In the two-owner batch each
            // owner's first unit spends its original selection; its later unit
            // spends the stashed alternate. This is observable physical identity.
            const sameOwner = initialGlobalOrder.filter(c => baseline.get(c).controller === b.controller);
            const shieldIndex = p.scenario === 'multi-owner-shield-menus' && b.shields.length > 1 && sameOwner.indexOf(card) > 0 ? 1 : 0;
            const expectedShield = b.shields[shieldIndex];
            assert.deepEqual(consumed.map(id), expectedShield ? [id(expectedShield)] : [], 'Exact source-stash-selected Shield consumed');
            const remaining = card.isInPlay() ? card.upgrades.filter(u => u.isShield?.()).map(id) : [];
            assert.deepEqual(remaining, b.shields.filter(t => t !== expectedShield).map(id), 'Exact surviving Shield identities');
            if (b.shields.length) { assert.ok(card.isInPlay()); assert.equal(card.damage, b.damage); }
            else if (b.damage + 5 >= b.hp) assert.equal(card.zoneName, 'discard');
        }
        if (p.scenario === 'empty') { assert.equal(damage.length, 1); assert.deepEqual([own.base.damage, enemy.base.damage], [5, 0]); }
        if (p.scenario === 'multi-owner-shield-menus') {
            assert.ok(ownerMenus.length, 'Both owners require replacement ordering');
            assert.equal(new Set(shieldMenus.map(x => x.actor)).size, 2, 'Both owners resolve their actual Shield batches');
            for (const menu of shieldMenus.filter(x => x.actions.some(a => a.label === 'Resolve all (2)'))) {
                assert.ok(menu.actions.some(a => a.label === 'Resolve next'));
            }
            assert.equal(shieldMenus.filter(x => x.actions.some(a => a.label === 'Resolve all (2)')).length, 2);
        }
        if (p.scenario === 'aura-death') {
            const aura = targets.find(c => c.cardData.internalName.startsWith('victor-leader#'));
            const recipient = targets.find(c => c.cardData.internalName === 'bwing-rearguard');
            assert.ok(aura && recipient, 'Actual Victor/B-Wing source definitions');
            assert.equal(baseline.get(recipient).hp, 6);
            const row = witness.events.find(e => e.name === 'onDamageDealt' && e.card === id(recipient));
            assert.ok(row.state.units.some(u => u.id === id(recipient) && u.damage === 5 && u.hp === 6), 'Aura still applies during primary damage');
            assert.equal(aura.zoneName, 'discard'); assert.equal(recipient.zoneName, 'discard');
        }
        if (p.scenario === 'own-base-lethal-death-heal') {
            assert.deepEqual([own.base.damage, enemy.base.damage], [28, 0]);
            assert.equal(eg.winner, eg.seatOf(enemy.id), 'Winner remains latched despite mandatory heal below lethal');
            assert.equal(heals.length, 1); assert.equal(heals[0].card, own.base); assert.equal(heals[0].damageHealed, 2);
        }
        if (p.scenario === 'winner-latched-then-mandatory-choice') {
            assert.deepEqual([own.base.damage, enemy.base.damage], [30, 30]);
            assert.equal(eg.winner, eg.seatOf(enemy.id), 'Earlier opponent winner survives later enemy-base lethal');
            assert.ok(terminalChoices.some(x => x.winner === eg.seatOf(enemy.id)), 'Real mandatory death target picker remains after winner latch');
        }
        if (p.scenario === 'enemy-base-lethal-death-trigger') {
            assert.deepEqual([own.base.damage, enemy.base.damage], [5, 30]);
            assert.equal(eg.winner, eg.seatOf(own.id));
        }
        if (p.scenario === 'death-draw-order') {
            assert.ok(scout); assert.equal(draws.length, 1); assert.equal(draws[0].amount, 2);
            assert.equal(own.drawDeck.length, initialDeck.length - 2);
            assert.equal(own.getCardsInZone('hand').length, initialHand.length - 1 + 2);
            assert.ok(initialDeck.slice(0, 2).every(c => own.getCardsInZone('hand').includes(c)));
            assert.equal(heals.length, 1); assert.deepEqual([own.base.damage, enemy.base.damage], [3, 0]);
        }
        const expectedEnemy = ['winner-latched-then-mandatory-choice', 'enemy-base-lethal-death-trigger'].includes(p.scenario) ? 30 : initialBases[1];
        assert.equal(enemy.base.damage, expectedEnemy, 'Only actual Cavern Angels death effect can change opposing base');
        witness.observations.push({ stage: 'resolved-own-base-then-arena', state: fullState(eg), summary: state(), source: id(source), targets: targets.map(id), shieldMenus, ownerMenus, terminalChoices });
        settled = true;
    }
    try {
        while (step < 5000) {
            const pid = eg.ids.find(pid => eg.legalActions(pid).length);
            if (!pid) { assert.ok(eg.over, 'No actor only after completed terminal resolution'); if (!settled) check(); break; }
            const actions = expandActions(eg, eg.legalActions(pid)), window = eg.isActionWindow(pid), prompt = eg.player(pid).currentPrompt();
            if (window && played && !settled) check();
            if (window && eg.over) break; // Winner alone is insufficient: mandatory non-window choices above still run.
            let chosen;
            if (window) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (!started && pid === own.id) { chosen = actions.find(a => a.cardUuid === source.uuid); assert.ok(chosen, 'Actual ordinary paid source hand play'); paidBefore = ready(); started = true; }
                else if (!settled) chosen = actions.find(a => a.arg === 'pass');
            } else if (started && !settled) {
                const menu = { actor: eg.seatOf(pid), title: prompt.menuTitle, actions: actions.map(a => canonicalAction(eg, a)), winner: eg.winner ?? null };
                if (prompt.menuTitle?.includes('Both players')) { ownerMenus.push(menu); chosen = actions.find(a => a.label === ((p.replacementOrder === 'opponent-first') === (pid === own.id) ? 'Opponent' : 'You')); }
                if (actions.some(a => /^Resolve all \(/.test(a.label ?? ''))) { shieldMenus.push(menu); chosen ??= actions.find(a => p.resolveMode === 'next' ? a.label === 'Resolve next' : /^Resolve all \(/.test(a.label ?? '')); }
                if (prompt.menuTitle === 'Deal 2 damage to a base') { terminalChoices.push(menu); chosen = actions.find(a => a.cardUuid === enemy.base.uuid); assert.ok(chosen, 'Real Cavern Angels chooses enemy base'); }
                chosen ??= actions.find(a => a.label === 'Trigger' || a.label === 'Resolve' || a.label === 'Resolve all');
                chosen ??= actions.find(a => a.arg === 'done');
            }
            chosen ??= bot.choose({ game: eg, pid, actions, rng }); assert.ok(chosen);
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window }, actions: actions.map(a => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            eg.apply(pid, chosen, rng); step++;
        }
        assert.ok(settled && eg.over, 'Source assertions followed by complete ordinary game');
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        witness.coverageObligationIds = [...scenario.coverageObligationIds];
        return { records, witness };
    } catch (error) { error.diagnostic = { records, witness, summary: state() }; throw error; }
    finally { bot.close?.(); }
}
module.exports = { fixture, dependencies: ['kessel:cards/pipeline/self-base-arena-damage-probes.js', 'lab/kessel-reference/pipeline/self-base-arena-damage-probe-fixture.js', 'lab/kessel-reference/pipeline/probe-fixture.js', 'bots/omni/rs/make-pool.js', 'engine/env.js', 'bots/omni/rs/state.js', 'bots/players/index.js'] };
