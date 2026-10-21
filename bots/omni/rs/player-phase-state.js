'use strict';
// Projection of current native player lasting-effect ownership. Spent rows come
// from retained wrappers, never payment observers or reconstructed history.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { isDeepStrictEqual: equal } = require('node:util');
const profiles = [
    {
        "kind": "imperialDiscount",
        "className": "MouseDroid",
        "card": {
            "title": "Mouse Droid",
            "subtitle": "",
            "cost": 1,
            "hp": 1,
            "power": 1,
            "text": "Raid 1 (This unit gets +1/+0 while attacking.)\nWhen Played: The next Imperial unit you play this phase costs 1 resource less.",
            "deployBox": null,
            "epicAction": "",
            "unique": false,
            "rules": "Once Mouse Droid's \u201cWhen Played\u201d ability resolves, it remains active even if it is defeated before you play your next Imperial unit.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "2588977937",
            "aspects": [
                "villainy"
            ],
            "traits": [
                "imperial",
                "droid"
            ],
            "arena": "ground",
            "keywords": [
                "raid"
            ],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "ASH",
                "number": 237
            },
            "setCodes": [
                {
                    "set": "ASH",
                    "number": 237
                }
            ],
            "internalName": "mouse-droid"
        },
        "sourcePath": "game/cards/08_ASH/units/MouseDroid.ts",
        "sourceHash": "62deb9ca7463987af7ca1af68a4778562e0ed283edca5d0d19885703525eb85c",
        "abilityProps": {
            "cardName": "Mouse Droid",
            "abilityIdentifier": "mouse-droid_triggered_0",
            "title": "The next unit Imperial you play this phase costs 1 resource less",
            "immediateEffect": {
                "class": "PlayerPhaseLastingEffectSystem",
                "name": "applyPlayerPhaseLastingEffect",
                "eventName": "onEffectApplied",
                "props": {
                    "ongoingEffectDescription": "discount the next Imperial unit played by",
                    "ongoingEffectTargetDescription": "them",
                    "effect": "(game, source, props) => new OngoingPlayerEffect_1.OngoingPlayerEffect(game, source, props, new StaticOngoingEffectImpl_1.StaticOngoingEffectImpl(game, type, new DetachedOngoingEffectValueWrapper_1.default(game, value.apply, value.unapply)))",
                    "duration": "untilEndOfPhase"
                },
                "defaults": {
                    "duration": null,
                    "effect": []
                }
            },
            "when": {
                "whenPlayed": true
            },
            "printedAbility": true
        }
    },
    {
        "kind": "lowPrintedPowerReady",
        "className": "NeelTheCutestBoy",
        "card": {
            "title": "Neel",
            "subtitle": "The Cutest Boy",
            "cost": 1,
            "hp": 4,
            "power": 1,
            "text": "When Played/On Attack: The next unit you play this phase with 1 or less power enters play ready.",
            "deployBox": null,
            "epicAction": "",
            "unique": true,
            "rules": "(ERRATA) When Played/On Attack: The next unit you play this phase with 1 or less printed power enters play ready.\nOnce Neel's \u201cWhen Played/On Attack\u201d ability resolves, it remains active even if it is defeated before you play your next unit with 1 or less printed power.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "8371755043",
            "aspects": [
                "heroism"
            ],
            "traits": [
                "fringe"
            ],
            "arena": "ground",
            "keywords": [],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "ASH",
                "number": 248
            },
            "setCodes": [
                {
                    "set": "ASH",
                    "number": 248
                }
            ],
            "internalName": "neel#the-cutest-boy"
        },
        "sourcePath": "game/cards/08_ASH/units/NeelTheCutestBoy.ts",
        "sourceHash": "89edabd6669728db5736536685918f69d4a36de7c3152c11760f5c9c84dcc547",
        "abilityProps": {
            "cardName": "Neel",
            "abilityIdentifier": "neel#the-cutest-boy_triggered_0",
            "title": "The next unit you play this phase with 1 or less power enters play ready",
            "when": {
                "whenPlayed": true,
                "onAttack": true
            },
            "immediateEffect": {
                "class": "PlayerPhaseLastingEffectSystem",
                "name": "applyPlayerPhaseLastingEffect",
                "eventName": "onEffectApplied",
                "props": {
                    "effect": "(game, source, props) => new OngoingPlayerEffect_1.OngoingPlayerEffect(game, source, props, new StaticOngoingEffectImpl_1.StaticOngoingEffectImpl(game, type, TypeHelpers_1.is.function(value) ? value(game) : value))",
                    "duration": "untilEndOfPhase"
                },
                "defaults": {
                    "duration": null,
                    "effect": []
                }
            },
            "printedAbility": true
        }
    }
];
const proof = (ok, reason) => { if (!ok) throw new Error('Unsupported player phase state: ' + reason); };
const exact = (object, keys) => object && equal(Object.keys(object).sort(), keys.slice().sort());
const fingerprint = fn => typeof fn === 'function' ? Function.prototype.toString.call(fn) : null;
// Selected-pool presence policy only; this cannot create a grant or card fact.
function reviewedPhasePoolRequirement(pool) {
    let required = false;
    for (const definition of pool.cards) {
        const p = profiles.find(p => {
            const codes = [p.card.setId, ...(p.card.setCodes ?? [])].map(x => x.set + '_' + String(x.number).padStart(3, '0'));
            return definition.id === p.card.id || definition.internalName === p.card.internalName || codes.includes(definition.setCode);
        });
        if (!p) continue;
        const { setCode, ...card } = definition;
        const codes = [p.card.setId, ...(p.card.setCodes ?? [])].map(x => x.set + '_' + String(x.number).padStart(3, '0'));
        proof(codes.includes(setCode) && equal(card, p.card), 'whole selected Phase source profile/alias');
        proof(createHash('sha256').update(fs.readFileSync(path.join(__dirname, '../../../forceteki/server', p.sourcePath))).digest('hex') === p.sourceHash, 'changed selected pinned Phase source');
        required = true;
    }
    return required;
}
function phaseStateRequired(eg, projection) {
    if (projection.playerPhaseState.effects.length || eg.game.allCards.some(c => sourceProfile(c))) return true;
    return require('./direct-play-credit-state').nativePoolRequirements(eg)?.playerPhaseState === true;
}
function sourceProfile(card) {
    const p = profiles.find(p => card?.internalName === p.card.internalName || card?.constructor?.name === p.className);
    if (!p) return null;
    const Native = require('../../../forceteki/build/server/' + p.sourcePath.replace(/\.ts$/, '')).default;
    proof(card instanceof Native && card.constructor.name === p.className && equal(card.cardData, p.card), 'whole physical source class and metadata');
    proof(createHash('sha256').update(fs.readFileSync(path.join(__dirname, '../../../forceteki/server', p.sourcePath))).digest('hex') === p.sourceHash, 'changed pinned source');
    proof(card.triggeredAbilities?.length === 1 && (card.actionAbilities ?? []).length === 0 && (card.constantAbilities ?? []).length === 0, 'whole source registration set');
    origin(card.triggeredAbilities[0], card, p);
    return p;
}
function origin(ability, source, p) {
    const { TriggeredAbility } = require('../../../forceteki/build/server/game/core/ability/TriggeredAbility');
    const { UnlimitedAbilityLimit } = require('../../../forceteki/build/server/game/core/ability/AbilityLimit');
    const { PlayerPhaseLastingEffectSystem } = require('../../../forceteki/build/server/game/gameSystems/PlayerPhaseLastingEffectSystem');
    const expected = p.abilityProps, a = ability?.properties;
    proof(ability instanceof TriggeredAbility && ability.constructor.name === 'TriggeredAbility' && ability.card === source && ability.printedAbility === true && ability.gainAbilitySource === undefined, 'direct printed originating registration');
    proof(exact(a, Object.keys(expected)) && a.cardName === expected.cardName && a.abilityIdentifier === expected.abilityIdentifier && ability.abilityIdentifier === expected.abilityIdentifier && a.title === expected.title && equal(a.when, expected.when) && a.printedAbility === true, 'whole captured originating registration');
    proof(ability.limit instanceof UnlimitedAbilityLimit && ability.limit.ability === ability, 'origin native unlimited limit');
    proof(ability.optional === false && ability.cost.length === 0 && Object.keys(ability.targetResolvers).length === 0, 'origin optionality and targets');
    proof(ability.handler === ability.executeGameActions, 'origin custom handler');
    const system = a.immediateEffect, shape = expected.immediateEffect;
    proof(system instanceof PlayerPhaseLastingEffectSystem && system.name === shape.name && system.eventName === shape.eventName && system.propertyFactory === undefined && exact(system.properties, Object.keys(shape.props)) && equal(system.defaultProperties, shape.defaults), 'closed phase installer system');
    for (const key of Object.keys(shape.props)) proof(key === 'effect' ? fingerprint(system.properties[key]) === shape.props[key] : equal(system.properties[key], shape.props[key]), 'installer field ' + key);
    proof(ability.immediateEffect === system && system.defaultTargets === PlayerPhaseLastingEffectSystem.prototype.defaultTargets && fingerprint(system.getDefaultTargets)?.replace(/\s+/g, '') === '(context)=>this.defaultTargets(context)', 'actual originating installer identity and default player target');
}
function uses(limit, players, limitPlayer) {
    const { PerPlayerPerGameAbilityLimit } = require('../../../forceteki/build/server/game/core/ability/AbilityLimit');
    proof(limit instanceof PerPlayerPerGameAbilityLimit && limit.constructor.name === 'PerPlayerPerGameAbilityLimit' && limit.max === 1 && limit.ability == null && limit.isRepeatable() === false && limit.useCount instanceof Map && limit.currentForPlayer === PerPlayerPerGameAbilityLimit.prototype.currentForPlayer && limit.isRepeatable === PerPlayerPerGameAbilityLimit.prototype.isRepeatable && limit.increment === PerPlayerPerGameAbilityLimit.prototype.increment, 'native cloned unattached one-use limit');
    const names = players.map(p => p.name);
    for (const [key, value] of limit.useCount) proof(names.includes(key) && Number.isInteger(value) && (value === 0 || value === 1) && (key === limitPlayer.name || value === 0), 'unexpected limit counter key or value');
    const result = players.map(p => limit.useCount.get(p.name) ?? 0);
    proof(players.every((p, i) => limit.currentForPlayer(p) === result[i]), 'authoritative counter disagreement');
    return result;
}
function projectPlayerPhaseState(eg, inspection = false) {
    const registry = eg.game?.ongoingEffectEngine?.effects, all = eg.game?.allCards;
    proof(Array.isArray(registry) && Array.isArray(all), 'missing actual registry inventory');
    const { OngoingPlayerEffect } = require('../../../forceteki/build/server/game/core/ongoingEffect/OngoingPlayerEffect');
    const phase = registry.filter(e => (e instanceof OngoingPlayerEffect && e.duration === 'untilEndOfPhase') || (['costAdjuster', 'unitsEnterPlayReady'].includes(e.type) && (e.duration === 'untilEndOfPhase' || profiles.some(p => e.source?.internalName === p.card.internalName))));
    const producers = all.filter(c => sourceProfile(c));
    if (!phase.length && !producers.length) return inspection ? { adjusterRows: new Map(), effects: [] } : { playerPhaseState: { version: 1, effects: [] } };
    const players = eg.ids.map(id => eg.player(id));
    proof(players.length === 2 && new Set(players).size === 2 && players.every((p, i) => typeof p.name === 'string' && p.name.length > 0 && p.id === eg.ids[i]) && new Set(players.map(p => p.name)).size === 2, 'engine player identities');
    const terminal = eg.over === true && eg.game.winnerNames.length > 0 && eg.game.currentAbilityResolver == null && eg.game.currentAttack == null && eg.ids.every(pid => !eg.legalActions(pid).length || eg.isActionWindow(pid));
    if (!inspection) proof(eg.game.currentAbilityResolver == null && eg.game.currentAttack == null && (terminal || (eg.phase === 'action' && eg.ids.some(pid => eg.isActionWindow(pid)))), 'pending player-phase continuation');
    proof(phase.length <= 64 && new Set(phase).size === phase.length, 'phase capacity or duplicate application');
    const { StaticOngoingEffectImpl } = require('../../../forceteki/build/server/game/core/ongoingEffect/effectImpl/StaticOngoingEffectImpl');
    const Detached = require('../../../forceteki/build/server/game/core/ongoingEffect/effectImpl/DetachedOngoingEffectValueWrapper').default;
    const { SimpleCostAdjuster } = require('../../../forceteki/build/server/game/core/cost/SimpleCostAdjuster');
    const { UnitsEnterPlayReadyForPlayer } = require('../../../forceteki/build/server/game/core/playerEffect/UnitsEnterPlayReadyForPlayer');
    const objects = new Set(), limits = new Set(), adjusters = new Set(), effects = [], adjusterRows = new Map();
    for (const effect of phase) {
        const source = effect.source, p = sourceProfile(source), props = effect.ongoingEffect, target = effect.matchTarget;
        proof(effect instanceof OngoingPlayerEffect && effect.duration === 'untilEndOfPhase', 'native lasting phase wrapper class and duration');
        proof(p && all.includes(source) && eg.game.state.allCards.includes(source.uuid), 'unreviewed or unallocated physical origin');
        const sourceId = eg.cardId(source.uuid);
        proof(/^c(?:0|[1-9][0-9]*)$/.test(sourceId) && Number(sourceId.slice(1)) < eg.game.state.allCards.length && eg.game.state.allCards[Number(sourceId.slice(1))] === source.uuid, 'physical source binding');
        proof(players.includes(target) && effect.targets.length === 1 && effect.targets[0] === target && target.getOngoingEffects().includes(effect), 'actual player target membership');
        const mouse = p.kind === 'imperialDiscount';
        const keys = ['matchTarget', 'isLastingEffect', 'ability', 'target', 'duration', ...(mouse ? ['ongoingEffectDescription', 'ongoingEffectTargetDescription'] : [])];
        proof(exact(props, keys) && props.matchTarget === target && equal(props.target, [target]) && props.isLastingEffect === true && props.duration === 'untilEndOfPhase' && effect.sourceZoneFilter === 'anyArena' && fingerprint(effect.condition) === '() => true' && equal(effect.until, {}), 'closed lasting application envelope');
        if (mouse) proof(props.ongoingEffectDescription === p.abilityProps.immediateEffect.props.ongoingEffectDescription && props.ongoingEffectTargetDescription === 'them', 'closed cost effect description');
        proof(effect.context?.source === source && effect.context.player === target && effect.context.ongoingEffect === props, 'captured origin and recipient context');
        origin(props.ability, source, p);
        const impl = effect.impl;
        proof(impl instanceof StaticOngoingEffectImpl, 'native static implementation');
        const wrapper = impl.valueWrapper;
        proof(wrapper && typeof wrapper === 'object', 'native value wrapper');
        proof(impl instanceof StaticOngoingEffectImpl && impl.isConditional === false && impl.context === effect.context && wrapper.context === effect.context && wrapper.game === eg.game && !objects.has(wrapper), 'actual static wrapper context and unique application');
        objects.add(wrapper);
        let limit, limitPlayer;
        if (mouse) {
            proof(fingerprint(wrapper.applyFunc) === "(player, context) => {\n            // since the properties object of modifyCost is generated once and then captured, need to copy the limit every\n            // time the properties are used so that each instance of the cost adjuster has a unique limit\n            const propertiesWithClonedLimit = Object.assign(properties, { limit: properties.limit?.clone() });\n            const adjuster = CostAdjusterFactory.create(context.game, context.source, propertiesWithClonedLimit);\n            player.addCostAdjuster(adjuster);\n            return adjuster;\n        }" && fingerprint(wrapper.unapplyFunc) === "(player, context, adjuster) => player.removeCostAdjuster(adjuster)", 'closed detached apply and unapply');
            proof(effect.type === 'costAdjuster' && wrapper instanceof Detached && wrapper.targetStates instanceof Map && wrapper.targetStates.size === 1 && wrapper.targetStates.has(target.uuid) && wrapper.value === true && wrapper.getValue() === true && wrapper.effectDescription === undefined, 'actual detached adjuster ownership');
            const value = wrapper.targetStates.get(target.uuid);
            proof(value instanceof SimpleCostAdjuster && value.constructor.name === 'SimpleCostAdjuster' && value.sourceCard === source && players.includes(value.sourcePlayer) && value.costAdjustStage === 'standard_0' && value.costAdjustType === 'decrease' && value.amount === 1 && value.cardTypeFilter === 'unit' && value.playType === null && value.attachTargetCondition === undefined && value.matchAbilityCosts === false && value.matchCardEffectResourcePayments === false && fingerprint(value.match) === '(card) => card.hasSomeTrait(Constants_1.Trait.Imperial)', 'whole native cost adjuster');
            proof(!adjusters.has(value), 'multiply owned adjuster'); adjusters.add(value); adjusterRows.set(value, effects.length + 1);
            limit = value.limit; limitPlayer = value.sourcePlayer;
            const counts = uses(limit, players, limitPlayer), spent = counts[players.indexOf(limitPlayer)] === 1;
            proof(spent ? value.isCancelled === true && players.every(player => !player.getCostAdjusters().includes(value)) : value.isCancelled === undefined && target.getCostAdjusters().includes(value) && players.filter(player => player !== target).every(player => !player.getCostAdjusters().includes(value)), 'spent or unspent authoritative list state');
        } else {
            proof(effect.type === 'unitsEnterPlayReady' && wrapper instanceof UnitsEnterPlayReadyForPlayer && effect.getValue(target) === wrapper && wrapper.cardTypeFilter === 'unit' && wrapper.entryTypes instanceof Set && equal([...wrapper.entryTypes], ['played']) && fingerprint(wrapper.match) === '(unit) => unit.getPrintedPower() <= 1', 'whole native ready matcher');
            limit = wrapper.limit; limitPlayer = target;
        }
        proof(!limits.has(limit), 'shared application limit'); limits.add(limit);
        effects.push({ id: effects.length + 1, source: sourceId, side: 'card', ordinal: 0, kind: p.kind, target: 'p' + (players.indexOf(target) + 1), limitPlayer: 'p' + (players.indexOf(limitPlayer) + 1), used: uses(limit, players, limitPlayer) });
    }
    for (const player of players) for (const effect of player.getOngoingEffects()) if (effect instanceof OngoingPlayerEffect && effect.duration === 'untilEndOfPhase') proof(phase.includes(effect), 'unaccounted target player wrapper');
    // A removed global wrapper cannot be replaced with remembered cost history.
    for (const player of players) for (const value of player.getCostAdjusters()) if (sourceProfile(value.sourceCard) && value instanceof SimpleCostAdjuster) proof(adjusters.has(value), 'unaccounted live source adjuster');
    return inspection ? { adjusterRows, effects } : { playerPhaseState: { version: 1, effects } };
}
// Conservative routing only. A candidate must still pass the full direct-Credit
// origin/stage/owner proof; failure never falls back to the legacy projection.
function actualCreditCandidate(eg) {
    const game = eg.game;
    const { AbilityResolver } = require('../../../forceteki/build/server/game/core/gameSteps/AbilityResolver');
    const { EventWindow } = require('../../../forceteki/build/server/game/core/event/EventWindow');
    const HandlerMenuPrompt = require('../../../forceteki/build/server/game/core/gameSteps/prompts/HandlerMenuPrompt');
    const { NumberPrompt } = require('../../../forceteki/build/server/game/core/gameSteps/prompts/NumberPrompt');
    const seen = new Set(); let candidate = false;
    function visit(step, owner = null, window = null, pipelinePath = new Set()) {
        if (step == null) return;
        proof(!pipelinePath.has(step), 'cyclic active pipeline');
        if (seen.has(step)) return;
        proof(typeof step === 'object' && seen.size < 256, 'ambiguous active pending graph');
        seen.add(step);
        if (step instanceof AbilityResolver) {
            owner = step; window = null;
            const matching = step.costResults?.costAdjustments?.matchingAdjusters;
            if (step.context?.stage === 'cost' && matching instanceof Map) {
                const refs = matching.get('defeatCredits_7');
                // Malformed nonempty references route to strict rejection too.
                if (refs != null && (!Array.isArray(refs) || refs.length > 0)) candidate = true;
            }
            visit(step.currentAbilityResolver);
        }
        if (step instanceof EventWindow) window = step;
        const nativePrompt = Object.getPrototypeOf(step) === HandlerMenuPrompt.prototype || Object.getPrototypeOf(step) === NumberPrompt.prototype;
        if (nativePrompt && owner && window && step.game === game && owner.game === game && window.game === game && owner.context?.game === game && window._events?.some(event => event.context === owner.context)) {
            // These unique pinned native writer signatures are only a rejection
            // route if stored refs/stage were corrupted, never origin authority.
            if ((Object.getPrototypeOf(step) === HandlerMenuPrompt.prototype && typeof step.properties?.activePromptTitle === 'string' && step.properties.activePromptTitle.startsWith('Use Credit tokens to pay for ')) ||
                (Object.getPrototypeOf(step) === NumberPrompt.prototype && step.properties?.promptTitle === 'Select amount of Credit tokens')) candidate = true;
        }
        visit(step.pipeline?.currentStep, owner, window, new Set([...pipelinePath, step]));
    }
    visit(game.pipeline?.currentStep);
    visit(game.currentAbilityResolver);
    return candidate;
}
function playerPhaseState(eg) {
    if (actualCreditCandidate(eg)) {
        let credit;
        try { credit = require('./direct-play-credit-state').directUnitPlayCreditState(eg); }
        catch (error) { proof(false, 'pending resolver: ' + error.message); }
        const { effects } = projectPlayerPhaseState(eg, true);
        const projection = { playerPhaseState: { version: 1, effects } };
        // Direct Credit ownership does not imply Phase-ledger presence.
        // Apply the same selected/physical/effect requirement at every boundary.
        return { ...(phaseStateRequired(eg, projection) ? projection : {}), directUnitPlayCreditState: credit };
    }
    const projection = projectPlayerPhaseState(eg);
    return phaseStateRequired(eg, projection) ? projection : {};
}
// Internal inspection only: this never authorizes pending serialization.
function inspectPlayerPhaseApplications(eg) { const { adjusterRows } = projectPlayerPhaseState(eg, true); return { adjusterRows }; }
module.exports = { playerPhaseState, inspectPlayerPhaseApplications, reviewedPhasePoolRequirement };
