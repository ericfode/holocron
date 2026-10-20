'use strict';
const { terminalCompletion } = require('./terminal-completion');
const assert = require('node:assert/strict');
const { constructProbeFixture } = require('./probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');

function validateProbe(p) {
    assert.equal(p.family, 'variable-payment');
    assert.equal(p.cardId, 'LOF_255');
    assert.ok([0, 1].includes(p.owner));
    assert.ok(['normal', 'captured-source-dead'].includes(p.scenario));
    assert.equal(p.sourceArena, 'ground');
    assert.equal(p.resourceCount, 12);
    assert.ok([0, 2, 6, 9].includes(p.readyAfterPlay));
    assert.ok(Number.isInteger(p.paymentAmount) && p.paymentAmount >= 0 && p.paymentAmount <= Math.min(6, p.readyAfterPlay));
    if (p.scenario === 'captured-source-dead') {
        assert.equal(p.snokeCode, 'SHD_037');
        assert.equal(p.paymentAmount, 3);
        assert.equal(p.readyAfterPlay, 9);
    } else assert.ok(p.snokeCode == null);
}
// A non-prefix ready layout makes resource identity/order observable, while the
// engine remains responsible for both normal play and unadjusted effect payment.
function resourceLayout(length, readyCount) {
    assert.ok(Number.isInteger(length) && Number.isInteger(readyCount) && length >= readyCount && readyCount >= 0);
    const order = [...Array(length).keys()].filter(i => i % 3 !== 1)
        .concat([...Array(length).keys()].filter(i => i % 3 === 1));
    const ready = new Set(order.slice(0, readyCount));
    return [...Array(length).keys()].map(i => !ready.has(i));
}
function validateExperience(pool) {
    const definitions = pool.cards.filter(c => c.setCode === 'TOKEN_EXPERIENCE');
    assert.equal(definitions.length, 1, 'Exact native Experience definition required by input pool');
    const token = definitions[0];
    assert.equal(token.internalName, 'experience'); assert.equal(token.cost, 0); assert.equal(token.unique, false);
    assert.deepEqual([...token.types].sort(), ['token', 'upgrade']);
    assert.deepEqual(token.traits, ['learned']); assert.deepEqual(token.keywords, []); assert.deepEqual(token.aspects, []);
    assert.equal(token.power, 1); assert.equal(token.hp, 1); assert.equal(token.upgradePower, 1); assert.equal(token.upgradeHp, 1);
    assert.ok(!token.text && !token.deployBox && !token.epicAction, 'Experience cannot acquire an unreviewed native ability');
}
async function fixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    validateProbe(p);
    validateExperience(pool);
    const death = p.scenario === 'captured-source-dead';
    // constructProbeFixture allocates a real source for p1. For the mirrored
    // case select another real Flock owned by p2; no controller/owner rewriting.
    const rows = [];
    if (p.owner === 1) rows.push({ code: p.cardId, owner: 'opponent', zone: 'hand' });
    if (death) rows.push({ code: p.snokeCode, owner: p.owner ? 'self' : 'opponent', arena: 'ground', exhausted: true });
    const built = await constructProbeFixture(env, pool, { probe: {
        cardId: p.cardId, sourceArena: 'ground', sourceInPlay: false,
        sourceDamage: 0, targets: rows, resourceCount: p.resourceCount,
    } }, seed);
    const { eg, rng, bot, decks } = built;
    const own = p.owner ? built.enemy : built.own, enemy = p.owner ? built.own : built.enemy;
    const source = p.owner ? built.targets[0] : built.source;
    assert.equal(source.owner, own); assert.equal(source.controller, own);
    assert.equal(source.zoneName, 'hand'); assert.equal(source.cardData.cost, 1);
    assert.deepEqual(source.cardData.aspects, []);
    const resources = own.getCardsInZone('resource'), otherResources = enemy.getCardsInZone('resource');
    const initialLayout = resourceLayout(resources.length, p.readyAfterPlay + 1);
    resources.forEach((r, i) => { r.exhausted = initialLayout[i]; });
    otherResources.forEach((r, i) => { r.exhausted = i % 2 === 0; });
    eg.game.resolveGameState(true); eg.game.continue();
    const id = c => eg.cardId(c.uuid);
    const beforeReady = resources.filter(r => !r.exhausted).map(id);
    const enemyLayout = otherResources.map(r => r.exhausted);
    assert.equal(beforeReady.length, p.readyAfterPlay + 1);
    const initialTokenIndex = eg.game.state.allCards.length;
    const witness = { scenario: scenario.name, source: id(source), owner: eg.seatOf(own.id),
        initialResources: resources.map(r => ({ id: id(r), exhausted: r.exhausted })),
        initialReady: beforeReady, expectedNumberValues: [...Array(Math.min(6, p.readyAfterPlay) + 1).keys()],
        numberPrompts: [], events: [], observations: [], coverageObligationIds: [] };
    const records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed,
        bots: ['variable-payment-probe', 'variable-payment-probe'], decks,
        scenario: scenario.name, evidenceStatus: 'Real engine observation; source-only oracle until independent native/Wasm validation',
        fixtureConstruction: 'At first natural action window stage real hand source and optional enemy Snoke, twelve more real resources per player; mirror source by physical p2-owned copy; set disclosed mixed ready/exhausted resource layout. Thereafter ordinary legal inputs only, including paid hand play; no source resurrection or source ability replacement.',
        constructionParameters: p }];
    let started = false, played = false, settled = false, step = 0;
    eg.game.on('onCardPlayed', e => { if (started && !settled && e.card === source) played = true; });
    for (const name of ['onExhaustResources', 'onTokensCreated', 'onCardDefeated']) eg.game.on(name, e => {
        if (!started || settled || (name === 'onExhaustResources' && !played) || (e.context?.source !== source && e.card !== source)) return;
        witness.events.push({ name, amount: e.amount ?? null, tokenType: e.tokenType ?? null,
            source: e.context?.source ? id(e.context.source) : null, sourceZone: source.zoneName,
            card: e.card?.uuid ? id(e.card) : null, ready: own.readyResourceCount,
            generatedTokens: (e.generatedTokens ?? []).map(id) });
    });
    function check() {
        assert.ok(played, 'Ordinary source play event occurred');
        assert.equal(witness.numberPrompts.length, p.readyAfterPlay ? 1 : 0,
            'Equal endpoints automatically select zero; nonempty range offers one number decision');
        assert.equal(own.readyResourceCount, p.readyAfterPlay - p.paymentAmount);
        const expectedSpent = new Set(beforeReady.slice(0, p.paymentAmount + 1));
        assert.deepEqual(resources.map(r => r.exhausted), resources.map((r, i) => initialLayout[i] || expectedSpent.has(id(r))),
            'Normal cost then variable payment exhaust the first ready physical resources in engine list order');
        assert.deepEqual(otherResources.map(r => r.exhausted), enemyLayout, 'No opponent resources paid');
        const created = eg.game.state.allCards.slice(initialTokenIndex).map(uuid => eg.game.findAnyCardInAnyList(uuid));
        assert.equal(created.length, death ? 0 : p.paymentAmount, 'Only successful source XP allocation creates identities');
        if (death) {
            assert.equal(source.zoneName, 'discard', 'Snoke framework defeat precedes captured WhenPlayed payment');
            assert.ok(witness.events.some(e => e.name === 'onCardDefeated' && e.card === id(source)));
        } else {
            assert.equal(source.zoneName, 'groundArena');
            assert.equal(source.getPower(), 1 + p.paymentAmount); assert.equal(source.getHp(), 1 + p.paymentAmount);
            assert.equal(source.upgrades.length, p.paymentAmount);
            assert.deepEqual(source.upgrades.map(id), created.map(id));
            for (const token of created) {
                assert.equal(token.internalName, 'experience'); assert.equal(token.owner, own); assert.equal(token.controller, own);
                assert.equal(token.parentCard, source); assert.equal(token.cardData.upgradePower, 1); assert.equal(token.cardData.upgradeHp, 1);
            }
        }
        const payments = witness.events.filter(e => e.name === 'onExhaustResources');
        assert.deepEqual(payments.map(e => e.amount), p.paymentAmount ? [p.paymentAmount] : [], 'Zero generates no unadjusted exhaustion event');
        const xpEvents = witness.events.filter(e => e.name === 'onTokensCreated');
        assert.equal(xpEvents.length, !death && p.paymentAmount ? 1 : 0, 'Experience is one creation event with contingent attachments');
        if (xpEvents.length) {
            assert.equal(xpEvents[0].tokenType, 'experience'); assert.equal(xpEvents[0].amount, p.paymentAmount);
            assert.ok(witness.events.indexOf(payments[0]) < witness.events.indexOf(xpEvents[0]), 'Payment window precedes XP creation');
            assert.deepEqual(xpEvents[0].generatedTokens, created.map(id));
        }
        witness.createdIds = created.map(id);
        witness.after = fullState(eg);
        settled = true;
    }
    const completion = terminalCompletion(eg, 5000);
    try {
        while (true) {
            const pid = completion.nextActor(step); if (!pid) break;
            const actions = expandActions(eg, eg.legalActions(pid)), window = eg.isActionWindow(pid), prompt = eg.player(pid).currentPrompt();
            let chosen;
            if (window) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (started && played && !settled) check();
                if (!started && pid === own.id) {
                    chosen = actions.find(a => a.cardUuid === source.uuid); assert.ok(chosen, 'Actual ordinary hand play must be legal'); started = true;
                } else if (!settled) chosen = actions.find(a => a.arg === 'pass');
            } else if (started && !settled) {
                const numeric = actions.filter(a => a.kind === 'option' && /^\d+$/.test(a.arg ?? ''));
                assert.equal(pid, own.id, 'Number selection belongs to the captured ability player');
                assert.equal(own.readyResourceCount, p.readyAfterPlay, 'Printed play cost is paid before live number range evaluation');
                assert.deepEqual(resources.map(r => r.exhausted), resources.map((r, i) => initialLayout[i] || id(r) === beforeReady[0]));
                assert.deepEqual(numeric.map(a => Number(a.arg)), witness.expectedNumberValues, 'Complete inclusive live range, bounded at six');
                assert.equal(numeric.length, actions.length, 'Number prompt has no cancel, decline, credit or cost-adjustment choices');
                witness.numberPrompts.push({ actor: eg.seatOf(pid), title: prompt.menuTitle, actions: actions.map(a => canonicalAction(eg, a)),
                    sourceZone: source.zoneName, ready: own.readyResourceCount, state: fullState(eg) });
                assert.equal(source.zoneName, death ? 'discard' : 'groundArena');
                chosen = numeric.find(a => a.arg === String(p.paymentAmount)); assert.ok(chosen);
            }
            if (eg.over && !window && /resourc/i.test(prompt.menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done') ?? chosen;
            chosen ??= bot.choose({ game: eg, pid, actions, rng }); assert.ok(chosen);
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null,
                title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window },
                actions: actions.map(a => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            eg.apply(pid, chosen, rng); step++;
        }
        assert.ok(settled, 'Focused variable-payment assertions completed'); assert.ok(eg.over, 'Actual complete terminal game required');
        witness.terminalCompletion = completion.assertComplete();
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        witness.coverageObligationIds = [...(scenario.coverageObligationIds ?? [])]; witness.decisions = step; witness.winner = eg.winner;
        return { records, witness };
    } catch (error) { error.diagnostic = { records, witness }; throw error; }
    finally { bot.close?.(); }
}
module.exports = { fixture, validateProbe, resourceLayout, validateExperience, dependencies: ['lab/kessel-reference/pipeline/terminal-completion.js',
    'kessel:cards/pipeline/variable-payment-probes.js', 'lab/kessel-reference/pipeline/variable-payment-probe-fixture.js',
    'lab/kessel-reference/pipeline/probe-fixture.js', 'engine/env.js', 'engine/rng.js', 'bots/omni/rs/state.js',
    'bots/omni/rs/state-evidence.js', 'bots/omni/rs/support-state.js', 'bots/players/index.js'
] };
