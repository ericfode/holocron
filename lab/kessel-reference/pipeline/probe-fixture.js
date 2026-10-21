'use strict';
const assert = require('node:assert/strict');
const { seededRng } = require('../../../engine/env');
const { makeBot } = require('../../../bots/players');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');
function matches(card, code) {
    return [card.cardData.setId, ...(card.cardData.setCodes ?? [])].some(
        (s) => s.set + '_' + String(s.number).padStart(3, '0') === code,
    );
}
function buildDeck(pool, probe) {
    const codes = [
        ...new Set([
            probe.cardId,
            ...(probe.activationCode ? [probe.activationCode] : []),
            ...probe.targets.map((t) => t.code),
            ...probe.targets.flatMap(t => (t.attachments ?? []).map(a => a.code)),
        ]),
    ];
    const leaders = pool.cards
        .filter((c) => c.types.includes('leader'))
        .sort((a, b) => a.setCode.localeCompare(b.setCode));
    const bases = pool.cards
        .filter((c) => c.types.includes('base') && !c.text)
        .sort((a, b) => a.setCode.localeCompare(b.setCode));
    // Quiet filler is selected deterministically from portable card metadata.
    const filler = pool.cards
        .filter(
            (c) =>
                c.types.includes('unit') &&
                !c.types.includes('leader') &&
                !c.text &&
                !c.keywords?.length &&
                !c.unique &&
                !codes.includes(c.setCode),
        )
        .sort((a, b) => a.setCode.localeCompare(b.setCode));
    assert.ok(leaders.length && bases.length, 'Probe requires an available leader and plain base');
    for (const code of codes)
        assert.ok(
            pool.cards.some((c) => c.setCode === code),
            'Probe card missing from pool: ' + code,
        );
    const deckCodes = [...codes.filter(code => !pool.cards.find(c => c.setCode===code).types.some(t => ['token','leader'].includes(t))), ...filler.map((c) => c.setCode)].slice(0, 17);
    assert.equal(deckCodes.length, 17, 'Probe requires seventeen distinct deck cards');
    return {
        metadata: { name: 'Automatic IR probe', author: 'card pipeline' },
        leader: { id: probe.leaderCode ?? leaders[0].setCode, count: 1 },
        base: { id: probe.baseCode ?? bases[0].setCode, count: 1 },
        deck: deckCodes.map((id, i) => ({ id, count: i === 16 ? 2 : 3 })),
        isPresentInDb: false,
    };
}
async function constructProbeFixture(env, pool, scenario, seed) {
    const p = scenario.probe;
    assert.ok(p, 'Missing pure probe construction');
    const deck = buildDeck(pool, p),
        enemyDeck = {...deck, base:{id:p.enemyBaseCode ?? deck.base.id,count:1},
            leader:{id:p.enemyLeaderCode ?? deck.leader.id,count:1}},
        eg = env.newGame({ selectionToggles: true, seed, deck1: deck, deck2: enemyDeck });
    const rng = seededRng('automatic-probe-' + seed),
        bot = makeBot('random');
    await eg.start();
    for (let i = 0; !eg.ids.some((id) => eg.isActionWindow(id)); i++) {
        assert.ok(i < 100, 'Startup did not reach action window');
        const pid = eg.ids.find((id) => eg.legalActions(id).length),
            actions = expandActions(eg, eg.legalActions(pid));
        const desiredInitiative=p.initiative==='self'?eg.ids[0]:eg.ids[1];
        const initiativeChoice=p.initiative&&actions.find(a=>a.label===(pid===desiredInitiative?'Yourself':'Opponent'));
        eg.apply(pid, initiativeChoice??bot.choose({ game: eg, pid, actions, rng }), rng);
    }
    const own = eg.player(eg.ids[0]),
        enemy = eg.player(eg.ids[1]);
    const allocated = new Set();
    const claim = (card) => {
        assert.ok(card, 'Missing physical construction card');
        assert.ok(!allocated.has(card.uuid), 'Construction card identity already allocated');
        allocated.add(card.uuid);
        return card;
    };
    const take = (player, code) => {
        const card = [...player.drawDeck, ...player.getCardsInZone('hand'), ...player.getCardsInZone('resource')].find(
            (c) => !allocated.has(c.uuid) && matches(c, code),
        );
        assert.ok(card, 'Cannot construct unused copy of ' + code);
        return claim(card);
    };
    const token = (player, name) => {
        const keys = Object.keys(eg.game.tokenFactories).filter(key => key.replace(/-/g,'').toLowerCase() === name.replace(/-/g,'').toLowerCase());
        assert.equal(keys.length,1,'Token metadata name must resolve exactly one engine factory');
        return claim(eg.game.generateToken(player,keys[0]));
    };
    const source = take(own, p.cardId);
    source.moveTo(p.sourceInPlay ? p.sourceArena + 'Arena' : 'hand');
    if (p.sourceInPlay) {
        source.exhausted = true;
        source.damage = p.sourceDamage ?? 0;
    }
    const activation = p.activationCode ? take(own, p.activationCode) : source;
    if (p.activationCode) activation.moveTo('hand');
    const constructionAttachments = [];
    const targets = p.targets.map((t) => {
        const player = t.owner === 'self' ? own : enemy;
        const card = (t.deployedLeader || t.leader) ? player.getAllDeckLeaders().find(c=>!allocated.has(c.uuid)&&matches(c,t.code)) : t.token ? token(player,t.token) : take(player,t.code);
        if (t.deployedLeader || t.leader) {
            assert.ok(card,'Missing unused chosen deck leader');
            claim(card);
            card.deploy({type:'leaderUnit'});
            card.deployEpicActionLimit.increment(player);
        } else card.moveTo(t.zone ?? t.arena + 'Arena');
        if (!t.zone) {
            card.exhausted = t.exhausted ?? true;
            card.damage = t.damage ?? 0;
        }
        for (const attachment of t.attachments ?? []) {
            const owner = attachment.owner === 'opponent' ? enemy : attachment.owner === 'self' ? own : player;
            const upgrade = attachment.token ? token(owner,attachment.token) : take(owner,attachment.code);
            upgrade.attachTo(card);
            constructionAttachments.push(upgrade);
        }
        return card;
    });
    const constructionCards = [source, ...(activation === source ? [] : [activation]), ...targets, ...constructionAttachments];
    assert.equal(new Set(constructionCards.map(card => card.uuid)).size, constructionCards.length,
        'Source, activation, targets and attachments require distinct physical identities');
    for (const player of [own, enemy]) {
        for (const card of player.drawDeck.slice(0, p.resourceCount ?? 12)) {
            card.moveTo('resource');
            card.exhausted = false;
        }
        for (const card of player.getCardsInZone('resource')) card.exhausted = false;
    }
    eg.game.resolveGameState(true);
    eg.game.continue();
    for (let i = 0; i < targets.length; i++) {
        if (!p.targets[i].zone)
            assert.equal(targets[i].damage, p.targets[i].damage ?? 0, 'Initial damage must survive construction');
        assert.equal(targets[i].zoneName, p.targets[i].zone ?? p.targets[i].arena + 'Arena');
    }
    if (p.sourceInPlay) {
        assert.equal(source.zoneName, p.sourceArena + 'Arena');
        assert.equal(source.damage, p.sourceDamage ?? 0);
    }
    return { eg, rng, bot, deck, decks:[deck,enemyDeck], own, enemy, source, activation, targets };
}
function observe(card, eg) {
    const active = ['groundArena', 'spaceArena'].includes(card.zoneName) || (card.zoneName === 'base' && card.isBase?.());
    return {
        id: eg.cardId(card.uuid),
        zone: card.zoneName,
        damage: active ? card.damage ?? 0 : null,
        power: active && card.isUnit?.() ? card.getPower() : null,
        hp: active && card.isUnit?.() ? card.getHp() : null,
    };
}
async function fixture(env, pool, scenario, seed) {
    if (scenario.probe?.family === 'named-exhaust-contingent') return require('./named-exhaust-contingent-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'captured-hand-cost') return require('./captured-hand-cost-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'exhaustedLiveCount') return require('./exhausted-live-count-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'defeat-token-creation') return require('./defeat-token-creation-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'chosen-hand-discard') return require('./chosen-hand-discard-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'distributed-damage') return require('./distributed-damage-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-query') return require('./arena-query-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'base-zone') return require('./base-zone-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-token') return require('./arena-token-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'keyword-inventory') return require('./keyword-inventory-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'parent-upgrade') return require('./parent-upgrade-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'force-continuation') return require('./force-continuation-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'weakness-continuation') return require('./weakness-continuation-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-keyword-set') return require('./arena-keyword-set-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-defeat-attack') return require('./arena-defeat-attack-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'blade-base-damage') return require('./blade-base-damage-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'round-limit') return require('./round-limit-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'collective-trigger') return require('./collective-trigger-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'defeat-cause') return require('./defeat-cause-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'executor-upgrade-count') return require('./executor-upgrade-count-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'variable-payment') return require('./variable-payment-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'unit-entry') return require('./unit-entry-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'ambush-context') return require('./ambush-context-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'self-base-arena-damage') return require('./self-base-arena-damage-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'terminal-continuation') return require('./terminal-continuation-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-damage') return require('./arena-damage-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'recipient-heal') return require('./recipient-heal-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'cross-arena') return require('./cross-arena-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'han-advantage') return require('./han-advantage-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'selection-exhaust') return require('./selection-exhaust-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'exhaust-resources') return require('./exhaust-resources-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'resource-self') return require('./resource-self-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'force-triggers') return require('./force-trigger-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'force-presence') return require('./force-presence-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'force-followon') return require('./force-followon-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'force') return require('./force-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-stat-filter') return require('./arena-stat-filter-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'weakness-upgrade') return require('./weakness-upgrade-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'weakness') return require('./weakness-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'named-chooser') return require('./named-chooser-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'named-target') return require('./named-target-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'arena-keyword') return require('./arena-keyword-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'hidden') return require('./hidden-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'hidden-keyword-only') return require('./hidden-keyword-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'on-defense') return require('./on-defense-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'upgrade-return') return require('./upgrade-return-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'cost-query') return require('./cost-probe-fixture').fixture(env, pool, scenario, seed);
    if (scenario.probe?.family === 'disclose') return require('./disclose-probe-fixture').fixture(env, pool, scenario, seed);
    const setup = await constructProbeFixture(env, pool, scenario, seed);
    const { eg, rng, bot, deck, own, enemy, source, activation, targets } = setup,
        p = scenario.probe;
    const records = [
        {
            type: 'meta',
            schema: 'omni-rs-trace-v1',
            pool: pool.provenance,
            seed,
            bots: ['automatic-probe', 'automatic-probe'],
            decks: [deck, deck],
            scenario: scenario.name,
            fixtureConstruction:
                'Deterministic metadata-selected deck; at first natural action window move real source/target deck cards to specified zones, initialize disclosed damage and exhausted state; create declared unit/upgrade tokens with game.generateToken and attach declared real upgrades, deploy declared leaders with spent epic action before capture; twelve real cards to resources; thereafter normal engine inputs only.',
            constructionParameters: p,
        },
    ];
    const witness = {
        scenario: scenario.name,
        coverageObligationIds: [],
        initial: {
            source: observe(source, eg),
            targets: targets.map((c) => observe(c, eg)),
            bases: [observe(own.base, eg), observe(enemy.base, eg)],
            handCounts: [own.getCardsInZone('hand').length, enemy.getCardsInZone('hand').length],
            attachments: targets.flatMap(c => (['groundArena','spaceArena'].includes(c.zoneName) ? c.upgrades : []).map(u => observe(u,eg))),
        },
        observations: [],
        played: false,
        targetSelected: false,
        negativeChecked: false,
        expired: false,
        defeatedIds: [],
        drawnCounts: [0,0],
    };
    const attachmentIdsByTarget = targets.map(card => (['groundArena','spaceArena'].includes(card.zoneName) ? card.upgrades : []).map(u => eg.cardId(u.uuid)));
    const round = eg.round;
    let step = 0,
        activated = false,
        settled = false,
        selectionObserved = false;
    eg.game.on('onCardDefeated', event => { if (activated && !settled && !event.isCancelledOrReplaced) witness.defeatedIds.push(eg.cardId(event.card.uuid)); });
    eg.game.on('onCardsDrawn', event => { if (activated && !settled && !event.isCancelledOrReplaced) {
        const seat = eg.ids.indexOf(event.player?.id); if (seat >= 0) witness.drawnCounts[seat] += event.amount ?? event.cards?.length ?? 0;
    }});
    eg.game.on('onCardPlayed', (event) => {
        if (activated && !settled && event.card === activation && !event.isCancelledOrReplaced) witness.played = true;
    });
    try {
        while (!eg.over && step < 4000) {
            const pid = eg.ids.find((id) => eg.legalActions(id).length);
            assert.ok(pid, 'No actor');
            const actions = expandActions(eg, eg.legalActions(pid));
            assert.ok(actions.length);
            const atWindow = eg.isActionWindow(pid);
            if (atWindow) {
                const state = fullState(eg, pid);
                records.push({ type: 'state', step, state });
                if (p.observeOnly && !settled) {
                    witness.observations.push({ stage: 'initial-live-stats', source: observe(source, eg) });
                    settled = true;
                }
                if (activated && witness.played && !settled) {
                    if (p.negativeOnly && !selectionObserved) {
                        witness.negativeChecked = true;
                        witness.observations.push({
                            stage: 'resolved-without-target-selector',
                            targetSelectionSeen: selectionObserved,
                        });
                    }
                    witness.observations.push({
                        stage: 'after-resolution',
                        handCounts: [own.getCardsInZone('hand').length,enemy.getCardsInZone('hand').length],
                        attachments: targets.flatMap(c => (['groundArena','spaceArena'].includes(c.zoneName) ? c.upgrades : []).map(u => observe(u,eg))),
                        source: observe(source, eg),
                        targets: targets.map((c) => observe(c, eg)),
                        bases: [observe(own.base, eg), observe(enemy.base, eg)],
                    });
                    settled = true;
                }
                if (settled && p.waitForExpiry && eg.round > round && !witness.expired) {
                    witness.observations.push({ stage: 'after-expiry', targets: targets.map((c) => observe(c, eg)) });
                    witness.expired = true;
                }
            }
            let chosen;
            if (atWindow && eg.round === round) {
                if (pid === own.id && !activated && !p.observeOnly) {
                    const play = actions.find((a) => a.cardUuid === activation.uuid);
                    if (!play && p.negativeOnly) {
                        witness.negativeChecked = true;
                        settled = true;
                        activated = true;
                        witness.observations.push({ stage: 'unplayable-with-no-eligible-target', sourceLegal: false });
                    } else {
                        assert.ok(play, 'Probe source not playable');
                        chosen = play;
                        activated = true;
                    }
                }
                chosen ??= actions.find((a) => a.arg === 'pass');
            } else if (!atWindow && pid === own.id && activated && !settled) {
                const target = p.mutateSource
                    ? source
                    : p.chosenBase
                    ? p.chosenBase === 'self'
                        ? own.base
                        : enemy.base
                    : targets[p.chosenTarget ?? 0];
                // Candidate observations come directly from the oracle's action protocol.
                if (actions.some((a) => a.kind === 'card') && !selectionObserved) {
                    selectionObserved = true;
                    witness.observations.push({
                        stage: 'target-prompt',
                        candidateIds: actions.filter((a) => a.kind === 'card').map((a) => eg.cardId(a.cardUuid)),
                        targets: targets.map((c) => observe(c, eg)),
                    });
                    if (p.negativeOnly) {
                        for (const card of targets)
                            assert.ok(
                                !actions.some((a) => a.cardUuid === card.uuid),
                                'Invalid target was offered by engine',
                            );
                        if (p.inspectBaseInvalid)
                            for (const base of [own.base, enemy.base])
                                assert.ok(
                                    !actions.some((a) => a.cardUuid === base.uuid),
                                    'Base offered to unit-only probe',
                                );
                        witness.negativeChecked = true;
                    } else {
                        assert.ok(
                            target && actions.some((a) => a.cardUuid === target.uuid),
                            'Constructed positive target was not offered',
                        );
                    }
                }
                if (!p.negativeOnly && target) {
                    chosen = actions.find((a) => a.cardUuid === target.uuid);
                    if (chosen) witness.targetSelected = true;
                }
                chosen ??= actions.find((a) => a.kind === 'button' && /play|resolve|trigger/i.test(a.label ?? ''));
                chosen ??= actions.find((a) => a.arg === 'done');
                if (p.negativeOnly) chosen ??= actions.find((a) => a.kind === 'card' && a.cardUuid !== source.uuid);
            }
            if (p.resolveDeathDraws && activated && !settled && !atWindow) chosen = actions.find(a => a.kind === 'button' && /resolve all|trigger|draw a card|yes/i.test(a.label ?? '')) ?? chosen;
            chosen ??= bot.choose({ game: eg, pid, actions, rng });
            assert.ok(chosen);
            const prompt = eg.player(pid).currentPrompt();
            records.push({
                type: 'decision',
                step,
                actor: eg.seatOf(pid),
                prompt: {
                    type: prompt.promptType ?? null,
                    title: prompt.menuTitle ?? null,
                    selected: (eg.player(pid).promptState.selectedCards ?? []).map((c) => eg.cardId(c.uuid)),
                    actionWindow: atWindow,
                },
                actions: actions.map((a) => canonicalAction(eg, a)),
                chosen: canonicalAction(eg, chosen).key,
                events: [],
            });
            eg.apply(pid, chosen, rng);
            step++;
        }
        assert.ok(eg.over, 'Automatic probe game did not complete');
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        assert.ok(settled, 'No post-activation experiment observation');
        if (!p.observeOnly && !p.negativeOnly) {
            assert.ok(witness.played, 'Missing actual source onCardPlayed');
            if (!p.autoTargets) assert.ok(witness.targetSelected, 'Missing positive target selection');
        }
        if (p.negativeOnly) assert.ok(witness.negativeChecked, 'No invalidity observation');
        if (p.waitForExpiry) assert.ok(witness.expired, 'Phase expiry not reached');
        if (!p.observeOnly && !p.negativeOnly) {
            const after = witness.observations.find((o) => o.stage === 'after-resolution');
            const before = p.mutateSource
                ? witness.initial.source
                : p.chosenBase
                ? witness.initial.bases[p.chosenBase === 'self' ? 0 : 1]
                : witness.initial.targets[p.chosenTarget ?? 0];
            const observed = p.mutateSource
                ? after.source
                : p.chosenBase
                ? after.bases[p.chosenBase === 'self' ? 0 : 1]
                : after.targets[p.chosenTarget ?? 0];
            if (p.autoTargets) {
                for (const [i, initial] of witness.initial.targets.entries()) {
                    const current = after.targets[i];
                    if (p.selectedTargetIndices.includes(i)) {
                        assert.notDeepEqual(current, initial, 'Selected auto-target must change');
                        if (p.expectDefeated) assert.equal(current.zone, p.targets[i].deployedLeader ? 'base' : p.targets[i].token ? 'outsideTheGame' : 'discard', 'Explicit defeat must leave arena');
                    }
                    else assert.deepEqual(current, initial, 'Excluded auto-target must stay unchanged');
                }
            } else assert.notDeepEqual(observed, before, 'Positive experiment must change observed target state');
            if (p.expectDraws) {
                // Each selected mandatory donor registers draw1; event is discarded from p1 hand during play.
                assert.deepEqual(after.handCounts, witness.initial.handCounts.map((n,i) => n + p.expectDraws[i] - (i === 0 ? 1 : 0)), 'All selected death draws resolve before the next action window');
            }
            if (p.expectDefeated && witness.initial.attachments.length) {
                const selectedUnits = p.selectedTargetIndices.map(i => witness.initial.targets[i].id);
                const attachmentIds = p.selectedTargetIndices.flatMap(i => attachmentIdsByTarget[i]);
                // CardTargetSystem creates all upgrade contingents before parent handlers; negative-order comparator reverses their combined entry order.
                assert.deepEqual(witness.defeatedIds.filter(id => attachmentIds.includes(id)), attachmentIds.toReversed(), 'Complete attachment batch reverses combined insertion order');
                for (const attachmentId of attachmentIds) assert.ok(witness.defeatedIds.indexOf(attachmentId) < Math.min(...selectedUnits.map(id => witness.defeatedIds.indexOf(id))), 'Every attachment resolves before any parent');
            }
            if (p.mutateSource) {
                assert.notEqual(observed.damage, before.damage, 'Live mutation must change source damage');
                assert.notEqual(observed.power, before.power, 'Live damage expression must change observed power');
            }
            if (p.waitForExpiry) {
                const expiry = witness.observations.find((o) => o.stage === 'after-expiry');
                assert.notDeepEqual(
                    expiry.targets,
                    after.targets,
                    'Expiry must change the post-effect target observation',
                );
            }
        }
        witness.coverageObligationIds = [...scenario.coverageObligationIds];
        return { records, witness };
    } finally {
        bot.close?.();
    }
}
module.exports = {
    fixture,
    constructProbeFixture,
    buildDeck,
    dependencies: [
        'kessel:cards/pipeline/named-exhaust-contingent-probes.js',
        'kessel:cards/pipeline/captured-hand-cost-probes.js',
        'lab/kessel-reference/pipeline/named-exhaust-contingent-fixture.js',
        'lab/kessel-reference/pipeline/captured-hand-cost-fixture.js',
        'kessel:cards/pipeline/exhausted-live-count-probes.js',
        'kessel:cards/pipeline/defeat-token-creation-probes.js',
        'lab/kessel-reference/pipeline/exhausted-live-count-fixture.js',
        'lab/kessel-reference/pipeline/defeat-token-creation-fixture.js',
        'lab/kessel-reference/pipeline/round-limit-probe-fixture.js',
        'engine/view.js',
        'engine/stdio.js',
        'engine/recorder.js',
        'bots/omni/rs/round-limit-state.js',
        'bots/omni/rs/pool.js',
        'bots/players/rush.js',
        'bots/players/heuristic.js',
        'bots/players/profiles.js',
        'bots/players/ismcts.js',
        'bots/players/belief.js',
        'bots/players/omniscient.js',
        'bots/examples/random-bot.js',
        'bots/examples/search-bot.js',
        'bots/omni/search.js',
        'bots/omni/evaluate.js',
        'kessel:cards/pipeline/round-limit-probes.js',

        'kessel:cards/pipeline/disclose-probes.js',
        'lab/kessel-reference/pipeline/disclose-probe-fixture.js',
        'kessel:cards/pipeline/keyword-inventory-probes.js',
        'lab/kessel-reference/pipeline/keyword-inventory-probe-fixture.js',
        'bots/omni/rs/make-pool.js',
        'kessel:cards/pipeline/parent-upgrade-probes.js',
        'lab/kessel-reference/pipeline/parent-upgrade-probe-fixture.js',
        'kessel:cards/pipeline/force-continuation-probes.js',
        'lab/kessel-reference/pipeline/force-continuation-probe-fixture.js',
        'kessel:cards/pipeline/weakness-continuation-probes.js',
        'lab/kessel-reference/pipeline/weakness-continuation-probe-fixture.js',
        'bots/omni/rs/make-pool.js',
        'kessel:cards/pipeline/arena-keyword-set-probes.js',
        'lab/kessel-reference/pipeline/arena-keyword-set-probe-fixture.js',
        'kessel:cards/pipeline/arena-query-probes.js',
        'lab/kessel-reference/pipeline/arena-query-probe-fixture.js',
        'kessel:cards/pipeline/base-zone-probes.js',
        'lab/kessel-reference/pipeline/base-zone-probe-fixture.js',
        'kessel:cards/pipeline/arena-token-probes.js',
        'lab/kessel-reference/pipeline/arena-token-probe-fixture.js',
        'kessel:cards/pipeline/chosen-hand-discard-probes.js',
        'lab/kessel-reference/pipeline/chosen-hand-discard-probe-fixture.js',
        'kessel:cards/pipeline/distributed-damage-probes.js',
        'lab/kessel-reference/pipeline/distributed-damage-probe-fixture.js',
        'kessel:cards/pipeline/arena-defeat-attack-probes.js',
        'lab/kessel-reference/pipeline/arena-defeat-attack-probe-fixture.js',
        'kessel:crates/kessel/src/arena_defeat_attack_contract.rs',
        'kessel:cards/pipeline/blade-base-damage-probes.js',
        'lab/kessel-reference/pipeline/blade-base-damage-probe-fixture.js',
        'kessel:crates/kessel/src/blade_base_damage_contract.rs',
        'kessel:cards/pipeline/collective-trigger-probes.js',
        'lab/kessel-reference/pipeline/collective-trigger-probe-fixture.js',
        'kessel:crates/kessel/src/collective_trigger_contract.rs',
        'bots/players/random.js',
        'kessel:cards/pipeline/defeat-cause-probes.js',
        'lab/kessel-reference/pipeline/defeat-cause-probe-fixture.js',
        'kessel:crates/kessel/src/defeat_cause_contract.rs',
        'kessel:cards/pipeline/executor-upgrade-count-probes.js',
        'lab/kessel-reference/pipeline/executor-upgrade-count-probe-fixture.js',
        'kessel:crates/kessel/src/executor_upgrade_count_contract.rs',
        'kessel:cards/pipeline/variable-payment-probes.js',
        'lab/kessel-reference/pipeline/variable-payment-probe-fixture.js',
        'lab/kessel-reference/pipeline/terminal-completion.js',
        'kessel:crates/kessel/src/variable_payment_contract.rs',
        'kessel:cards/pipeline/unit-entry-probes.js',
        'lab/kessel-reference/pipeline/unit-entry-probe-fixture.js',
        'bots/omni/rs/unit-entry-state.js',
        'kessel:crates/kessel/src/unit_entry_contract.rs',
        'kessel:cards/pipeline/ambush-context-probes.js',
        'lab/kessel-reference/pipeline/ambush-context-probe-fixture.js',
        'kessel:crates/kessel/src/ambush_context_contract.rs',
        'kessel:cards/pipeline/self-base-arena-damage-probes.js',
        'lab/kessel-reference/pipeline/self-base-arena-damage-probe-fixture.js',
        'kessel:crates/kessel/src/cinder_contract.rs',
        'kessel:cards/pipeline/terminal-continuation-probes.js',
        'lab/kessel-reference/pipeline/terminal-continuation-probe-fixture.js',
        'kessel:cards/pipeline/arena-damage-probes.js',
        'lab/kessel-reference/pipeline/arena-damage-probe-fixture.js',
        'kessel:cards/pipeline/probes.js',
        'kessel:cards/pipeline/recipient-heal-probes.js',
        'lab/kessel-reference/pipeline/recipient-heal-probe-fixture.js',
        'kessel:cards/pipeline/cross-arena-probes.js',
        'lab/kessel-reference/pipeline/cross-arena-probe-fixture.js',
        'kessel:cards/pipeline/han-advantage-probes.js',
        'lab/kessel-reference/pipeline/han-advantage-probe-fixture.js',
        'kessel:cards/pipeline/selection-exhaust-probes.js',
        'lab/kessel-reference/pipeline/selection-exhaust-probe-fixture.js',
        'kessel:cards/pipeline/exhaust-resources-probes.js',
        'lab/kessel-reference/pipeline/exhaust-resources-probe-fixture.js',
        'kessel:cards/pipeline/resource-self-probes.js',
        'lab/kessel-reference/pipeline/resource-self-probe-fixture.js',
        'kessel:cards/pipeline/force-trigger-probes.js',
        'lab/kessel-reference/pipeline/force-trigger-probe-fixture.js',
        'kessel:cards/pipeline/force-presence-probes.js',
        'lab/kessel-reference/pipeline/force-presence-probe-fixture.js',
        'kessel:cards/pipeline/force-followon-probes.js',
        'lab/kessel-reference/pipeline/force-followon-probe-fixture.js',
        'kessel:cards/pipeline/force-probes.js',
        'lab/kessel-reference/pipeline/force-probe-fixture.js',
        'kessel:cards/pipeline/arena-stat-filter-probes.js',
        'lab/kessel-reference/pipeline/arena-stat-filter-probe-fixture.js',
        'kessel:cards/pipeline/weakness-upgrade-probes.js',
        'lab/kessel-reference/pipeline/weakness-upgrade-probe-fixture.js',
        'kessel:cards/pipeline/weakness-probes.js',
        'lab/kessel-reference/pipeline/weakness-probe-fixture.js',
        'kessel:cards/pipeline/named-chooser-probes.js',
        'lab/kessel-reference/pipeline/named-chooser-probe-fixture.js',
        'kessel:cards/pipeline/named-target-probes.js',
        'lab/kessel-reference/pipeline/named-target-probe-fixture.js',
        'kessel:cards/pipeline/arena-keyword-probes.js',
        'lab/kessel-reference/pipeline/arena-keyword-probe-fixture.js',
        'lab/kessel-reference/pipeline/probe-fixture.js',
        'kessel:cards/pipeline/hidden-probes.js',
        'lab/kessel-reference/pipeline/hidden-probe-fixture.js',
        'lab/kessel-reference/pipeline/hidden-source-fixture.js',
        'kessel:cards/pipeline/hidden-keyword-probes.js',
        'lab/kessel-reference/pipeline/hidden-keyword-probe-fixture.js',
        'kessel:cards/pipeline/on-defense-probes.js',
        'lab/kessel-reference/pipeline/on-defense-probe-fixture.js',
        'kessel:cards/pipeline/cost-probes.js',
        'lab/kessel-reference/pipeline/cost-probe-fixture.js',
        'kessel:cards/pipeline/upgrade-return-probes.js',
        'lab/kessel-reference/pipeline/upgrade-return-probe-fixture.js',
        'engine/env.js',
        'engine/rng.js',
        'bots/omni/rs/state.js',
        'bots/omni/rs/state-evidence.js',
        'bots/omni/rs/support-state.js',
        'bots/players/index.js',
    ],
};
