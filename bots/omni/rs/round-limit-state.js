"use strict";

// Observation only: current native limit objects, never inferred round history.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { isDeepStrictEqual: equal } = require('node:util');
const profiles = [
    {
        "setCode": "ASH_047",
        "card": {
            "title": "Gar Saxon",
            "subtitle": "Coveting Power",
            "cost": 3,
            "hp": 4,
            "power": 3,
            "text": "When you play an upgrade on this unit: You may create a Mandalorian token. Use this ability only once each round.",
            "deployBox": null,
            "epicAction": "",
            "unique": true,
            "rules": "Attaching a token upgrade is not considered playing an upgrade and does not trigger Gar Saxon's ability.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "6754905608",
            "aspects": [
                "vigilance",
                "villainy"
            ],
            "traits": [
                "mandalorian",
                "trooper"
            ],
            "arena": "ground",
            "keywords": [],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "ASH",
                "number": 47
            },
            "setCodes": [
                {
                    "set": "ASH",
                    "number": 47
                }
            ],
            "internalName": "gar-saxon#coveting-power"
        },
        "sourcePath": "game/cards/08_ASH/units/GarSaxonCovetingPower.ts",
        "sourceHash": "6032937d56a8afdcc23ef689beb5401d85efd22460b2f2defef91089a17992c5",
        "className": "GarSaxonCovetingPower",
        "ordinal": 0,
        "properties": [
            {
                "abilityIdentifier": "gar-saxon#coveting-power_triggered_0",
                "cardName": "Gar Saxon",
                "immediateEffect": {
                    "class": "CreateTokenUnitSystem",
                    "name": "createTokenUnit",
                    "eventName": "onTokensCreated",
                    "properties": {
                        "tokenType": "mandalorian"
                    },
                    "defaultProperties": {
                        "amount": 1,
                        "entersReady": false
                    },
                    "propertyFactory": {
                        "undefined": true
                    },
                    "getDefaultTargets": {
                        "functionHash": "685c7a5bf67272fb27a80bcaeeef1b9454b2601d01964596e50ddcaf18d1e8f9"
                    }
                },
                "limit": {
                    "class": "RepeatableAbilityLimit",
                    "max": 1,
                    "eventName": [
                        "onRoundEnded"
                    ]
                },
                "optional": true,
                "printedAbility": true,
                "title": "Create a Mandalorian token",
                "when": {
                    "onCardPlayed": {
                        "functionHash": "d5523e28522d972edfb070a0f6738fc72ad9e7e1793b30f50a84b732a5afd298"
                    }
                }
            }
        ]
    },
    {
        "setCode": "ASH_032",
        "card": {
            "title": "Rancor Keeper",
            "subtitle": "",
            "cost": 2,
            "hp": 4,
            "power": 2,
            "text": "When a friendly unit is dealt damage and survives: Deal 1 damage to any number of bases. Use this ability only once each round.",
            "deployBox": null,
            "epicAction": "",
            "unique": false,
            "rules": "All damage dealt by Rancor Keeper's ability is dealt simultaneously.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "1069133190",
            "aspects": [
                "vigilance",
                "aggression"
            ],
            "traits": [
                "underworld"
            ],
            "arena": "ground",
            "keywords": [],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "ASH",
                "number": 32
            },
            "setCodes": [
                {
                    "set": "ASH",
                    "number": 32
                }
            ],
            "internalName": "rancor-keeper"
        },
        "sourcePath": "game/cards/08_ASH/units/RancorKeeper.ts",
        "sourceHash": "6f8746448d1845b9f91f796cbc9531e6f966957ac71264b0859861bd7b7a5b72",
        "className": "RancorKeeper",
        "ordinal": 0,
        "properties": [
            {
                "abilityIdentifier": "rancor-keeper_triggered_0",
                "cardName": "Rancor Keeper",
                "limit": {
                    "class": "RepeatableAbilityLimit",
                    "max": 1,
                    "eventName": [
                        "onRoundEnded"
                    ]
                },
                "printedAbility": true,
                "targetResolver": {
                    "activePromptTitle": "Choose bases to deal 1 damage to",
                    "canChooseNoCards": true,
                    "cardTypeFilter": "base",
                    "immediateEffect": {
                        "class": "DamageSystem",
                        "name": "damage",
                        "eventName": "onDamageDealt",
                        "properties": {
                            "amount": 1,
                            "type": "ability"
                        },
                        "defaultProperties": {
                            "amount": null,
                            "isIndirect": false,
                            "isUnpreventable": false,
                            "type": "ability"
                        },
                        "propertyFactory": {
                            "undefined": true
                        },
                        "getDefaultTargets": {
                            "functionHash": "d5dd2c85908aa432f23e5a3ee7362be1491b643569e41594de641a37e848fd1e"
                        }
                    },
                    "mode": "unlimited"
                },
                "title": "Deal 1 damage to any number of bases",
                "when": {
                    "onDamageDealt": {
                        "functionHash": "dae4106381939451b78877a8f75fbf320f87074f5d36f6b26de5ede1f534677a"
                    }
                }
            }
        ]
    },
    {
        "setCode": "ASH_160",
        "card": {
            "title": "Kachirho Militia",
            "subtitle": "",
            "cost": 5,
            "hp": 6,
            "power": 4,
            "text": "Hidden (This unit can't be attacked if it was played this phase.)\nWhen an enemy ground unit attacks your base: Ready this unit. Use this ability only once each round.",
            "deployBox": null,
            "epicAction": "",
            "unique": false,
            "rules": "If a unit has Hidden and Sentinel at the same time, it can be attacked.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "6989468664",
            "aspects": [
                "aggression",
                "heroism"
            ],
            "traits": [
                "wookiee",
                "trooper"
            ],
            "arena": "ground",
            "keywords": [
                "hidden"
            ],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "ASH",
                "number": 160
            },
            "setCodes": [
                {
                    "set": "ASH",
                    "number": 160
                }
            ],
            "internalName": "kachirho-militia"
        },
        "sourcePath": "game/cards/08_ASH/units/KachirhoMilitia.ts",
        "sourceHash": "4eb45048fce01d0b58d176e200af035b4d60525e105e28df84a3fd0443e25e17",
        "className": "KachirhoMilitia",
        "ordinal": 0,
        "properties": [
            {
                "abilityIdentifier": "kachirho-militia_triggered_0",
                "cardName": "Kachirho Militia",
                "immediateEffect": {
                    "class": "ReadySystem",
                    "name": "ready",
                    "eventName": "onCardReadied",
                    "properties": {},
                    "defaultProperties": {
                        "isRegroupPhaseReadyStep": false
                    },
                    "propertyFactory": {
                        "undefined": true
                    },
                    "getDefaultTargets": {
                        "functionHash": "685c7a5bf67272fb27a80bcaeeef1b9454b2601d01964596e50ddcaf18d1e8f9"
                    }
                },
                "limit": {
                    "class": "RepeatableAbilityLimit",
                    "max": 1,
                    "eventName": [
                        "onRoundEnded"
                    ]
                },
                "printedAbility": true,
                "title": "Ready Kachirho Militia",
                "when": {
                    "onAttackDeclared": {
                        "functionHash": "2a7278bc0a7a3527919a7601f9843e6836877e0f5aa06f5ed3dd5abc33764b59"
                    }
                }
            }
        ]
    },
    {
        "setCode": "HMW_062",
        "card": {
            "title": "Nuvo Vindi",
            "subtitle": "Blue Shadow Perfected",
            "cost": 3,
            "hp": 4,
            "power": 1,
            "text": "When Played: You may give a Weakness token to a unit.\nWhen an enemy unit with a Weakness token on it is defeated: You may give a Weakness token to a unit. Use this ability only once each round.",
            "deployBox": null,
            "epicAction": "",
            "unique": true,
            "rules": null,
            "upgradePower": null,
            "upgradeHp": null,
            "id": "9689400738",
            "aspects": [
                "vigilance",
                "villainy"
            ],
            "traits": [
                "separatist"
            ],
            "arena": "ground",
            "keywords": [],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "HMW",
                "number": 62
            },
            "setCodes": [
                {
                    "set": "HMW",
                    "number": 62
                }
            ],
            "internalName": "nuvo-vindi#blue-shadow-perfected"
        },
        "sourcePath": "game/cards/09_HMW/units/NuvoVindiBlueShadowPerfected.ts",
        "sourceHash": "33a11f826279ca2c6e8e1e3a5ead0fa3753d0548ffc9cbf54d7018c6a0d31af3",
        "className": "NuvoVindiBlueShadowPerfected",
        "ordinal": 1,
        "properties": [
            {
                "abilityIdentifier": "nuvo-vindi#blue-shadow-perfected_triggered_0",
                "cardName": "Nuvo Vindi",
                "optional": true,
                "printedAbility": true,
                "targetResolver": {
                    "cardTypeFilter": "unit",
                    "immediateEffect": {
                        "class": "GiveTokenUpgradeSystem",
                        "name": "giveTokenUpgrade",
                        "eventName": "onTokensCreated",
                        "properties": {
                            "tokenType": "weakness"
                        },
                        "defaultProperties": {
                            "amount": 1,
                            "createdBy": "self"
                        },
                        "propertyFactory": {
                            "undefined": true
                        },
                        "getDefaultTargets": {
                            "functionHash": "d5dd2c85908aa432f23e5a3ee7362be1491b643569e41594de641a37e848fd1e"
                        }
                    }
                },
                "title": "Give a Weakness token to a unit",
                "when": {
                    "whenPlayed": true
                }
            },
            {
                "abilityIdentifier": "nuvo-vindi#blue-shadow-perfected_triggered_1",
                "cardName": "Nuvo Vindi",
                "limit": {
                    "class": "RepeatableAbilityLimit",
                    "max": 1,
                    "eventName": [
                        "onRoundEnded"
                    ]
                },
                "optional": true,
                "printedAbility": true,
                "targetResolver": {
                    "cardTypeFilter": "unit",
                    "immediateEffect": {
                        "class": "GiveTokenUpgradeSystem",
                        "name": "giveTokenUpgrade",
                        "eventName": "onTokensCreated",
                        "properties": {
                            "tokenType": "weakness"
                        },
                        "defaultProperties": {
                            "amount": 1,
                            "createdBy": "self"
                        },
                        "propertyFactory": {
                            "undefined": true
                        },
                        "getDefaultTargets": {
                            "functionHash": "d5dd2c85908aa432f23e5a3ee7362be1491b643569e41594de641a37e848fd1e"
                        }
                    }
                },
                "title": "Give a Weakness token to a unit",
                "when": {
                    "onCardDefeated": {
                        "functionHash": "ef9790ffe9f711942e7fe8970c34992252cc9c3de726fdd6b34886c44ee7cb7d"
                    }
                }
            }
        ]
    },
    {
        "setCode": "SOR_115",
        "card": {
            "title": "Agent Kallus",
            "subtitle": "Seeking the Rebels",
            "cost": 5,
            "hp": 4,
            "power": 4,
            "text": "Ambush (After you play this unit, he may ready and attack an enemy unit.)\n\nWhen another unique unit is defeated: You may draw a card. Use this ability only once each round.",
            "deployBox": null,
            "epicAction": null,
            "unique": true,
            "rules": "If Agent Kallus is defeated simultaneously with other unique units, you still may draw a card.\nAmbush is an ability that triggers at the same time as \u201cWhen Played\u201d abilities. If there is no enemy unit that can be attacked, the unit does not ready.\n(ERRATA) Templating update: \u201cUnique\u201d becomes \u201c<uq>\u201d.\n",
            "upgradePower": null,
            "upgradeHp": null,
            "id": "2649829005",
            "aspects": [
                "command"
            ],
            "traits": [
                "imperial",
                "trooper"
            ],
            "arena": "ground",
            "keywords": [
                "ambush"
            ],
            "types": [
                "unit"
            ],
            "setId": {
                "set": "SOR",
                "number": 115
            },
            "setCodes": [
                {
                    "set": "SOR",
                    "number": 115
                }
            ],
            "internalName": "agent-kallus#seeking-the-rebels"
        },
        "sourcePath": "game/cards/01_SOR/units/AgentKallusSeekingTheRebels.ts",
        "sourceHash": "9c20159591599b89b2f78b68c076ee9bb0321e1efb22dc631af847392318155b",
        "className": "AgentKallusSeekingTheRebels",
        "ordinal": 0,
        "properties": [
            {
                "abilityIdentifier": "agent-kallus#seeking-the-rebels_triggered_0",
                "cardName": "Agent Kallus",
                "immediateEffect": {
                    "class": "DrawSystem",
                    "name": "draw",
                    "eventName": "onCardsDrawn",
                    "properties": {},
                    "defaultProperties": {
                        "amount": 1
                    },
                    "propertyFactory": {
                        "undefined": true
                    },
                    "getDefaultTargets": {
                        "functionHash": "685c7a5bf67272fb27a80bcaeeef1b9454b2601d01964596e50ddcaf18d1e8f9"
                    }
                },
                "limit": {
                    "class": "RepeatableAbilityLimit",
                    "max": 1,
                    "eventName": [
                        "onRoundEnded"
                    ]
                },
                "optional": true,
                "printedAbility": true,
                "title": "Draw a card",
                "when": {
                    "onCardDefeated": {
                        "functionHash": "1bba8a297a5070477109a73411f5b36c9c545b7a6264610172f19e77d504ede2"
                    }
                }
            }
        ]
    }
];
const proof = (condition, message) => { if (!condition) throw new Error('Unsupported round limit state: ' + message); };
const exact = (value, keys) => value && equal(Object.keys(value).sort(), keys.slice().sort());
const hashFunction = fn => createHash('sha256').update(Function.prototype.toString.call(fn).replace(/\s+/g, '')).digest('hex');
// Data-only fingerprints of the full printed registration envelopes under the
// pinned physical engine build. Hash callbacks without evaluating or exporting them.
function shape(value, seen = new Set()) {
    const { RepeatableAbilityLimit } = require('../../../forceteki/build/server/game/core/ability/AbilityLimit');
    if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) return value;
    if (value === undefined) return { undefined: true };
    if (typeof value === 'function') return { functionHash: hashFunction(value) };
    if (Array.isArray(value)) return value.map(v => shape(v, seen));
    if (value instanceof Set) return { set: [...value].sort() };
    proof(!seen.has(value), 'cyclic registration properties'); seen.add(value);
    let result;
    if (value instanceof RepeatableAbilityLimit) {
        proof(value.eventName instanceof Set, 'printed limit reset scope');
        result = { class: value.constructor.name, max: value.max, eventName: [...value.eventName].sort() };
    }
    else if (typeof value.generatePropertiesFromContext === 'function') {
        const known = ['CreateTokenUnitSystem','DamageSystem','ReadySystem','GiveTokenUpgradeSystem','DrawSystem'];
        proof(known.includes(value.constructor.name), 'unknown registration system');
        const Native = require('../../../forceteki/build/server/game/gameSystems/' + value.constructor.name)[value.constructor.name];
        proof(value instanceof Native, 'native registration system class');
        result = { class: value.constructor.name, name: value.name, eventName: value.eventName, properties: shape(value.properties, seen), defaultProperties: shape(value.defaultProperties, seen), propertyFactory: shape(value.propertyFactory, seen), getDefaultTargets: shape(value.getDefaultTargets, seen) };
    } else {
        proof(Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null, 'unknown registration property object');
        result = {}; for (const key of Object.keys(value).sort()) result[key] = shape(value[key], seen);
    }
    seen.delete(value); return result;
}
function pendingLimit(game) {
    const { RepeatableAbilityLimit } = require('../../../forceteki/build/server/game/core/ability/AbilityLimit');
    const seen = new Set();
    const limited = context => (context?.getProps?.().limit ?? context?.limit) instanceof RepeatableAbilityLimit;
    const inspect = step => {
        if (!step || typeof step !== 'object' || seen.has(step)) return false;
        seen.add(step);
        if (limited(step.context)) return true;
        if (Array.isArray(step.triggeredAbilities) && step.triggeredAbilities.some(limited)) return true;
        if (step.pipeline && !Array.isArray(step.pipeline) && inspect(step.pipeline)) return true;
        return ['pipeline', 'stepsQueuedDuringCurrentStep'].some(key => Array.isArray(step[key]) && step[key].some(inspect));
    };
    return inspect(game.currentAbilityResolver) || inspect(game.pipeline);
}
function roundLimitState(eg) {
    const { RepeatableAbilityLimit, UnlimitedAbilityLimit } = require('../../../forceteki/build/server/game/core/ability/AbilityLimit');
    const { TriggeredAbility } = require('../../../forceteki/build/server/game/core/ability/TriggeredAbility');
    const { PlayerOrCardAbility } = require('../../../forceteki/build/server/game/core/ability/PlayerOrCardAbility');
    proof(!pendingLimit(eg.game), 'pending current or retired limit context');
    const players = eg.ids.map(id => eg.player(id));
    proof(players.length === 2 && new Set(players.map(p => p.name)).size === 2, 'engine player identities');
    const names = new Set(players.map(p => p.name));
    const registrations = [], current = new Set(), claimedAbilities = new Set();
    for (const card of eg.game.allCards) {
        const profile = profiles.find(p => equal(card.cardData, p.card) || card.constructor.name === p.className || card.internalName === p.card.internalName);
        if (!profile) continue;
        proof(equal(card.cardData, profile.card), 'whole physical source metadata');
        const Native = require('../../../forceteki/build/server/' + profile.sourcePath.replace(/\.ts$/, '')) .default;
        proof(card instanceof Native && card.constructor.name === profile.className, 'whole physical source class');
        const source = fs.readFileSync(path.join(__dirname, '../../../forceteki/server', profile.sourcePath));
        proof(createHash('sha256').update(source).digest('hex') === profile.sourceHash, 'changed printed source');
        proof(Array.isArray(card.triggeredAbilities) && card.triggeredAbilities.length === profile.properties.length && (card.actionAbilities ?? []).length === 0 && (card.constantAbilities ?? []).length === 0, 'complete printed registration set');
        const id = eg.cardId(card.uuid);
        proof(eg.game.state.allCards.includes(card.uuid) && /^c(?:0|[1-9][0-9]*)$/.test(id), 'allocated physical source');
        proof(!card.getOngoingEffects().some(e => e.type === 'increaseLimitOnAbilities'), 'modified limit maximum');
        for (const [ordinal, ability] of card.triggeredAbilities.entries()) {
            proof(ability instanceof TriggeredAbility && ability.card === card && ability.printedAbility === true && ability.gainAbilitySource === undefined && ability.abilityIdentifier === profile.card.internalName + '_triggered_' + ordinal, 'printed registration identity');
            proof(equal(shape(ability.properties), profile.properties[ordinal]), 'closed printed registration envelope');
            proof(ability.captureLimit === PlayerOrCardAbility.prototype.captureLimit, 'native current limit accessor');
            const limit = ability.captureLimit();
            proof(limit && limit === ability.limit && limit.ability === ability, 'current registration limit binding');
            if (ordinal !== profile.ordinal) { proof(limit instanceof UnlimitedAbilityLimit, 'nonlimited printed registration'); continue; }
            proof(limit instanceof RepeatableAbilityLimit && limit.constructor.name === 'RepeatableAbilityLimit' && limit.max === 1 && limit.eventName instanceof Set && equal([...limit.eventName], ['onRoundEnded']) && limit.isRegistered === true && limit.reset === RepeatableAbilityLimit.prototype.reset && limit.currentForPlayer === RepeatableAbilityLimit.prototype.currentForPlayer, 'current registered perRound1 object');
            proof(!current.has(limit), 'shared current limit object'); current.add(limit); claimedAbilities.add(ability);
            proof(Array.isArray(limit.eventRegistrations) && limit.eventRegistrations.length === 1 && exact(limit.eventRegistrations[0], ['name', 'handler']) && limit.eventRegistrations[0].name === 'onRoundEnded' && typeof limit.eventRegistrations[0].handler === 'function' && Function.prototype.toString.call(limit.eventRegistrations[0].handler).replace(/\s+/g, '') === '()=>this.reset()' && eg.game.listeners('onRoundEnded').includes(limit.eventRegistrations[0].handler), 'native current reset listener');
            proof(limit.useCount instanceof Map && [...limit.useCount].every(([name, count]) => names.has(name) && Number.isInteger(count) && count >= 0 && count <= 1), 'actual per-player use map');
            const used = players.map(player => limit.useCount.get(player.name) ?? 0);
            proof(players.every((player, i) => limit.currentForPlayer(player) === used[i]), 'actual current count getter');
            registrations.push({ card: id, side: 'card', ordinal, used });
        }
    }
    // Profiles are mandatory, not a heuristic: unknown or substituted repeatable
    // registrations must not disappear merely because their card failed a match.
    for (const card of eg.game.allCards) {
        for (const ability of [...(card.triggeredAbilities ?? []), ...(card.actionAbilities ?? [])]) {
            const limit = ability.limit;
            if (limit instanceof RepeatableAbilityLimit) proof(claimedAbilities.has(ability) && current.has(limit), 'unreviewed copied gained or substituted repeatable registration');
        }
    }
    registrations.sort((a, b) => Number(a.card.slice(1)) - Number(b.card.slice(1)) || a.ordinal - b.ordinal);
    return { roundLimitState: { version: 1, registrations } };
}
module.exports = { roundLimitState };
