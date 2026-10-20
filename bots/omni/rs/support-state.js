"use strict";

// This is a source-registration reference, never executable simulator IR.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const profile = {
    "arena": "space",
    "aspects": [
        "command",
        "cunning",
        "heroism"
    ],
    "cost": 7,
    "deployBox": null,
    "epicAction": "",
    "hp": 6,
    "id": "0770708432",
    "internalName": "red-leader#strike-the-reactor",
    "keywords": [
        "support"
    ],
    "power": 6,
    "rules": null,
    "setCodes": [
        {
            "number": 37,
            "set": "ASH"
        }
    ],
    "setId": {
        "number": 37,
        "set": "ASH"
    },
    "subtitle": "Strike the Reactor",
    "text": "Support (When you play this unit, you may attack with another unit. It gains this unit's other abilities for this attack.)\nThis unit may attack units in either arena.",
    "title": "Red Leader",
    "traits": [
        "rebel",
        "vehicle",
        "fighter"
    ],
    "types": [
        "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
};
const permissionTypes = ['canAttackGroundArenaFromSpaceArena', 'canAttackSpaceArenaFromGroundArena'];
const keywordOrder = ['sentinel', 'overwhelm', 'saboteur', 'ambush', 'grit', 'shielded', 'raid', 'restore', 'hidden'];
const receipts = new WeakMap();
function receipt(eg, grants, consumed) {
    const result = Object.freeze({});
    receipts.set(result, { eg, grants, consumed, registry: eg.game.ongoingEffectEngine.effects.slice() });
    return result;
}
function supportGrants(eg, result) {
    const value = receipts.get(result);
    check(value?.eg === eg && value.registry.length === eg.game.ongoingEffectEngine.effects.length && value.registry.every((effect, i) => effect === eg.game.ongoingEffectEngine.effects[i]), 'stale or foreign projection receipt');
    return structuredClone(value.grants);
}
function consumesSupportEffect(result, effect) { return effect.type === 'gainKeyword' && (receipts.get(result)?.consumed.has(effect) ?? false); }
const arena = c => ['groundArena', 'spaceArena'].includes(c?.zoneName);
const fail = message => { throw new Error('Unsupported Support projection: ' + message); };
const check = (condition, message) => { if (!condition) fail(message); };
const keys = (object, expected) => object && isDeepStrictEqual(Object.keys(object).sort(), expected.slice().sort());
const sameTargets = (effect, target) => effect.targets?.length === 1 && effect.targets[0] === target;
function sourceProfile(donor) {
    check(isDeepStrictEqual(donor.cardData, profile) && donor.isUnit?.() && !donor.isToken?.() && !donor.isLeader?.(), 'whole physical donor profile');
    // Validate the pinned definition behind this whole-registration reference.
    // The emitted code below comes from the physical object, never this profile.
    const source = fs.readFileSync(path.join(__dirname, '../../../forceteki/server/game/cards/08_ASH/units/RedLeaderStrikeTheReactor.ts'));
    check(createHash('sha256').update(source).digest('hex') === '18e9249374f7431bad5024b6c0fa9de21dcd834eca63d33cbeae5a110a601d28', 'pinned source changed');
}
function keywordSnapshot(effect, target) {
    const values = effect.getValue(target);
    check(Array.isArray(values), 'keyword snapshot must be a captured property list');
    const keywords = Array(9).fill(0); let presence = 0;
    for (const value of values) {
        const name = value?.keyword, index = keywordOrder.indexOf(name);
        check(index >= 0, 'unrepresented keyword snapshot');
        const numeric = name === 'raid' || name === 'restore';
        check(keys(value, numeric ? ['keyword', 'amount'] : ['keyword']), 'keyword snapshot properties');
        const amount = numeric ? value.amount : 1;
        check(Number.isSafeInteger(amount) && amount >= 0 && amount <= 65535, 'keyword snapshot amount');
        keywords[index] = numeric ? keywords[index] + amount : 1;
        check(keywords[index] <= 65535, 'keyword snapshot overflow'); presence |= 1 << index;
    }
    return { keywords, presence };
}
function lasting(effect, target, ability) {
    check(effect.duration === 'untilEndOfAttack' && effect.source === target && effect.matchTarget === target && sameTargets(effect, target), 'lasting target binding');
    const p = effect.ongoingEffect;
    check(keys(p, ['matchTarget', 'sourceZoneFilter', 'isLastingEffect', 'ability', 'target', 'duration', 'ongoingEffectDescription']), 'lasting envelope');
    check(p.matchTarget === target && Array.isArray(p.target) && p.target.length === 1 && p.target[0] === target && p.sourceZoneFilter === 'any' && p.isLastingEffect === true && p.ability === ability && p.duration === 'untilEndOfAttack' && p.ongoingEffectDescription === null, 'lasting properties');
    check(effect.sourceZoneFilter === 'any' && effect.targetsSourceOnly === false && effect.targetController === 'self' && effect.targetZoneFilter === 'any' && isDeepStrictEqual(effect.targetCardTypeFilter, ['unit']) && !effect.impl.isConditional, 'lasting scope');
}
function capturedConstant(copy, target, donor, registry) {
    const wrapper = copy.impl.valueWrapper;
    check(wrapper?.constructor.name === 'GainNonKeywordAbilitiesFromUnitEffect', 'copy wrapper');
    const maps = ['_triggeredAbilityUuidsByTargetCard', '_actionAbilityUuidsByTargetCard', '_constantAbilityUuidsByTargetCard'].map(name => wrapper[name]);
    for (const map of maps) check(map instanceof Map && map.size === 1 && map.has(target.uuid) && Array.isArray(map.get(target.uuid)), 'captured UUID map');
    check(maps[0].get(target.uuid).length === 0 && maps[1].get(target.uuid).length === 0 && maps[2].get(target.uuid).length === 1, 'closed captured registration set');
    const uuid = maps[2].get(target.uuid)[0];
    const matches = target.getConstantAbilities().filter(a => a.uuid === uuid);
    check(matches.length === 1, 'captured constant identity');
    const a = matches[0], p = a.properties;
    check(keys(p, ['cardName', 'abilityIdentifier', 'title', 'ongoingEffect', 'printedAbility', 'gainAbilitySource']), 'captured constant properties');
    check(a.sourceCard === target && a.gainAbilitySource === donor && a.printedAbility === false && a.duration === 'persistent' && a.sourceZoneFilter === 'anyAttackable', 'captured constant provenance');
    check(p.cardName === profile.title && p.abilityIdentifier === profile.internalName + '_constant_0' && p.title === 'This unit can attack units in either arena' && Array.isArray(p.ongoingEffect) && p.ongoingEffect.length === 2 && p.ongoingEffect.every(f => typeof f === 'function'), 'closed registration envelope');
    check(a.registeredEffects.length === 2, 'closed permission count');
    a.registeredEffects.forEach((effect, i) => {
        const e = effect.ongoingEffect;
        check(registry.includes(effect) && effect.type === permissionTypes[i] && effect.duration === 'persistent' && effect.source === target && sameTargets(effect, target) && effect.targetsSourceOnly === true && effect.sourceZoneFilter === 'anyAttackable' && !effect.impl.isConditional && effect.getValue(target) === true, 'captured permission binding');
        check(keys(e, ['sourceZoneFilter', 'duration', 'cardName', 'abilityIdentifier', 'gainAbilitySource']) && e.sourceZoneFilter === 'anyAttackable' && e.duration === 'persistent' && e.cardName === p.cardName && e.abilityIdentifier === p.abilityIdentifier && e.gainAbilitySource === donor, 'captured permission scope');
    });
    return uuid;
}
// The receipt is generated before phaseStats. Only its exact recognized keyword
// objects may be omitted there; all unrelated attack-duration effects still fail.
function supportProjection(eg) {
    const registry = eg.game.ongoingEffectEngine.effects;
    const effects = registry.filter(e => e.duration === 'untilEndOfAttack');
    const grants = [], consumed = new Set(), captured = new Set();
    if (!effects.length) return receipt(eg, grants, consumed);
    // A terminal result may retain cancelled grants through regroup fatigue.
    // It has no continuation to import; all captured-grant proof below still applies.
    // Never admit an in-progress resolver or attack as a terminal shortcut.
    const terminal = eg.over === true && eg.game.winnerNames.length > 0 &&
        !eg.game.currentAbilityResolver && !eg.game.currentAttack;
    check(terminal || (eg.phase === 'action' && eg.ids.some(pid => eg.isActionWindow(pid))), 'grant outside action window');
    const allocated = card => card && eg.game.allCards.includes(card) && eg.game.state.allCards.includes(card.uuid);
    for (const copy of effects.filter(e => e.type === 'gainNonKeywordAbilitiesFromUnit')) {
        const target = copy.source, donor = copy.getValue(target), ability = copy.ongoingEffect?.ability;
        check(allocated(target) && allocated(donor) && target !== donor && arena(target) && target.isUnit?.() && target.controller === donor.controller && eg.ids.includes(target.controller?.id), 'physical friendly identities');
        sourceProfile(donor);
        check(ability?.constructor.name === 'InitiateAttackAction' && ability.card === target && ability.initiateAttackSource === donor && typeof ability.uuid === 'string', 'originating Support attack identity');
        lasting(copy, target, ability);
        check(copy.impl.constructor.name === 'StaticOngoingEffectImpl', 'copy implementation');
        const companions = effects.filter(e => e.type === 'gainKeyword' && e.ongoingEffect?.ability === ability && e.source === target);
        check(companions.length === 1 && effects.filter(e => e.type === 'gainNonKeywordAbilitiesFromUnit' && e.ongoingEffect?.ability === ability).length === 1, 'ambiguous originating attack pairing');
        const keyword = companions[0]; lasting(keyword, target, ability);
        check(keyword.impl.constructor.name === 'DynamicOngoingEffectImpl' && !consumed.has(keyword), 'captured keyword implementation');
        const uuid = capturedConstant(copy, target, donor, registry);
        check(!captured.has(uuid), 'duplicate captured registration'); captured.add(uuid);
        const setId = donor.cardData.setId;
        grants.push({ kind: 'sourcePrograms', target: eg.cardId(target.uuid), donor: eg.cardId(donor.uuid), sourcePrograms: { setCode: setId.set + '_' + String(setId.number).padStart(3, '0'), side: 'card' }, ...keywordSnapshot(keyword, target) });
        consumed.add(copy); consumed.add(keyword);
    }
    check(effects.every(e => consumed.has(e)), 'unaccounted attack-duration effect');
    for (const target of new Set(effects.filter(e => e.type === 'gainNonKeywordAbilitiesFromUnit').map(e => e.source))) {
        const donors = new Set(effects.filter(e => e.type === 'gainNonKeywordAbilitiesFromUnit' && e.source === target).map(e => e.getValue(target)));
        check(target.getConstantAbilities().filter(a => donors.has(a.gainAbilitySource)).every(a => captured.has(a.uuid)) && target.getTriggeredAbilities().every(a => !donors.has(a.gainAbilitySource)) && target.getActionAbilities().every(a => !donors.has(a.gainAbilitySource)), 'unaccounted gained registration');
    }
    return receipt(eg, grants, consumed);
}
module.exports = { supportProjection, supportGrants, consumesSupportEffect };
