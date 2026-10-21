'use strict';
const assert=require('node:assert/strict');
const same=require('node:util').isDeepStrictEqual;
const causes=['combat','ability-damage','direct-defeat','attack-ability-damage','framework-weakness','unique-rule','simultaneous-defeat'];
const fillerCodes=['ASH_061','ASH_131','ASH_190','ASH_201','ASH_242','ASH_261','HMW_082','HMW_093','HMW_116','HMW_128','HMW_135','HMW_155','HMW_163','HMW_174','HMW_178','HMW_219','HMW_258'];
function validateProbe(p){assert.deepEqual(Object.keys(p).sort(),['family','cardId','owner','cause','resourceCount','sourceArena','leaderCode','baseCode'].sort());assert.equal(p.family,'defeat-token-creation');assert.ok([0,1].includes(p.owner));assert.ok(causes.includes(p.cause));assert.equal(p.resourceCount,24);assert.equal(p.sourceArena,'ground');assert.equal(p.leaderCode,'SOR_014');assert.equal(p.baseCode,'SOR_023');}
const reviewedPoolDefinitions=[
  {
    "title": "Strike Team Vanguard",
    "subtitle": "",
    "cost": 4,
    "hp": 5,
    "power": 5,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "1029172801",
    "aspects": [
      "vigilance",
      "heroism"
    ],
    "traits": [
      "rebel",
      "trooper"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 61
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 61
      }
    ],
    "internalName": "strike-team-vanguard",
    "setCode": "ASH_061"
  },
  {
    "title": "Dinosaur Turtle",
    "subtitle": "",
    "cost": 6,
    "hp": 7,
    "power": 7,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9890561214",
    "aspects": [
      "command"
    ],
    "traits": [
      "creature"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 131
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 131
      }
    ],
    "internalName": "dinosaur-turtle",
    "setCode": "ASH_131"
  },
  {
    "title": "Peridea Bandit",
    "subtitle": "",
    "cost": 2,
    "hp": 1,
    "power": 4,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "4344365271",
    "aspects": [
      "cunning",
      "villainy"
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
      "number": 190
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 190
      }
    ],
    "internalName": "peridea-bandit",
    "setCode": "ASH_190"
  },
  {
    "title": "Open Circle Ace",
    "subtitle": "",
    "cost": 1,
    "hp": 2,
    "power": 2,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9620848758",
    "aspects": [
      "cunning",
      "heroism"
    ],
    "traits": [
      "republic",
      "vehicle",
      "fighter"
    ],
    "arena": "space",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 201
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 201
      }
    ],
    "internalName": "open-circle-ace",
    "setCode": "ASH_201"
  },
  {
    "title": "Death Trooper Squad",
    "subtitle": "",
    "cost": 4,
    "hp": 4,
    "power": 5,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9011599796",
    "aspects": [
      "villainy"
    ],
    "traits": [
      "imperial",
      "trooper"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 242
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 242
      }
    ],
    "internalName": "death-trooper-squad",
    "setCode": "ASH_242"
  },
  {
    "title": "Noti Mobile Pod",
    "subtitle": "",
    "cost": 3,
    "hp": 4,
    "power": 3,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "5556203656",
    "aspects": [],
    "traits": [
      "vehicle",
      "transport"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 261
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 261
      }
    ],
    "internalName": "noti-mobile-pod",
    "setCode": "ASH_261"
  },
  {
    "title": "Nala Se",
    "subtitle": "Silent Survivor",
    "cost": 2,
    "hp": 7,
    "power": 1,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "5691187672",
    "aspects": [
      "vigilance",
      "vigilance"
    ],
    "traits": [
      "kaminoan"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 82
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 82
      }
    ],
    "internalName": "nala-se#silent-survivor",
    "setCode": "HMW_082"
  },
  {
    "title": "Coastal Catamarans",
    "subtitle": "",
    "cost": 7,
    "hp": 8,
    "power": 8,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "1226993616",
    "aspects": [
      "vigilance"
    ],
    "traits": [
      "vehicle",
      "transport"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 93
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 93
      }
    ],
    "internalName": "coastal-catamarans",
    "setCode": "HMW_093"
  },
  {
    "title": "Ewok Brigade",
    "subtitle": "",
    "cost": 2,
    "hp": 4,
    "power": 2,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "8382448205",
    "aspects": [
      "command",
      "heroism"
    ],
    "traits": [
      "ewok"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 116
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 116
      }
    ],
    "internalName": "ewok-brigade",
    "setCode": "HMW_116"
  },
  {
    "title": "Mace Windu",
    "subtitle": "Austere Centrist",
    "cost": 3,
    "hp": 5,
    "power": 4,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "0886129762",
    "aspects": [
      "command",
      "command"
    ],
    "traits": [
      "force",
      "jedi"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 128
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 128
      }
    ],
    "internalName": "mace-windu#austere-centrist",
    "setCode": "HMW_128"
  },
  {
    "title": "Arena Reek",
    "subtitle": "Fixture of Ceremony",
    "cost": 3,
    "hp": 4,
    "power": 4,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "0212754007",
    "aspects": [
      "command"
    ],
    "traits": [
      "creature"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 135
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 135
      }
    ],
    "internalName": "arena-reek#fixture-of-ceremony",
    "setCode": "HMW_135"
  },
  {
    "title": "Filthy Dianoga",
    "subtitle": "",
    "cost": 4,
    "hp": 5,
    "power": 5,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "7827651708",
    "aspects": [
      "aggression",
      "villainy"
    ],
    "traits": [
      "creature"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 155
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 155
      }
    ],
    "internalName": "filthy-dianoga",
    "setCode": "HMW_155"
  },
  {
    "title": "Champions of Endor",
    "subtitle": "",
    "cost": 2,
    "hp": 3,
    "power": 3,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "4516882765",
    "aspects": [
      "aggression",
      "heroism"
    ],
    "traits": [
      "ewok"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 163
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 163
      }
    ],
    "internalName": "champions-of-endor",
    "setCode": "HMW_163"
  },
  {
    "title": "Maul",
    "subtitle": "Only Revenge Remains",
    "cost": 4,
    "hp": 6,
    "power": 6,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "3460896271",
    "aspects": [
      "aggression",
      "aggression"
    ],
    "traits": [
      "force",
      "underworld"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 174
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 174
      }
    ],
    "internalName": "maul#only-revenge-remains",
    "setCode": "HMW_174"
  },
  {
    "title": "Desperate Nantex",
    "subtitle": "",
    "cost": 2,
    "hp": 3,
    "power": 2,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "5508530442",
    "aspects": [
      "aggression"
    ],
    "traits": [
      "separatist",
      "vehicle",
      "fighter"
    ],
    "arena": "space",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 178
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 178
      }
    ],
    "internalName": "desperate-nantex",
    "setCode": "HMW_178"
  },
  {
    "title": "Jaxxon",
    "subtitle": "I Can Hear You Breathing!",
    "cost": 1,
    "hp": 3,
    "power": 3,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9427322990",
    "aspects": [
      "cunning",
      "cunning"
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
      "set": "HMW",
      "number": 219
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 219
      }
    ],
    "internalName": "jaxxon#i-can-hear-you-breathing",
    "setCode": "HMW_219"
  },
  {
    "title": "Ryloth Revolutionary Rider",
    "subtitle": "",
    "cost": 3,
    "hp": 3,
    "power": 4,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9859570567",
    "aspects": [
      "heroism"
    ],
    "traits": [
      "creature",
      "twi'lek",
      "trooper"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "HMW",
      "number": 258
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 258
      }
    ],
    "internalName": "ryloth-revolutionary-rider",
    "setCode": "HMW_258"
  },
  {
    "title": "Sabine Wren",
    "subtitle": "Galvanized Revolutionary",
    "cost": 4,
    "hp": 5,
    "power": 2,
    "text": "Action [exhaust]: Deal 1 damage to each base.",
    "deployBox": "On Attack: Deal 1 damage to each enemy base.",
    "epicAction": "Epic Action: If you control 4 or more resources, deploy this leader.",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "4841169874",
    "aspects": [
      "aggression",
      "heroism"
    ],
    "traits": [
      "mandalorian",
      "rebel",
      "spectre"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "leader"
    ],
    "setId": {
      "set": "SOR",
      "number": 14
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 14
      }
    ],
    "internalName": "sabine-wren#galvanized-revolutionary",
    "setCode": "SOR_014"
  },
  {
    "title": "Command Center",
    "subtitle": null,
    "cost": null,
    "hp": 30,
    "power": null,
    "text": null,
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "0507674993",
    "aspects": [
      "command"
    ],
    "traits": [
      "death star"
    ],
    "keywords": [],
    "types": [
      "base"
    ],
    "setId": {
      "set": "SOR",
      "number": 23
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 23
      }
    ],
    "internalName": "command-center",
    "setCode": "SOR_023"
  },
  {
    "title": "Mandalorian",
    "subtitle": "",
    "cost": 0,
    "hp": 2,
    "power": 2,
    "text": "Shielded (When you create this token, give a Shield token to it.)",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "8192010342",
    "aspects": [
      "vigilance"
    ],
    "traits": [
      "mandalorian"
    ],
    "arena": "ground",
    "keywords": [
      "shielded"
    ],
    "types": [
      "token",
      "unit"
    ],
    "setId": {
      "set": "ASH"
    },
    "internalName": "mandalorian",
    "setCode": "TOKEN_MANDALORIAN"
  },
  {
    "title": "Shield",
    "subtitle": null,
    "cost": 0,
    "hp": 0,
    "power": 0,
    "text": "If damage would be dealt to attached unit, prevent that damage. If you do, defeat a Shield token on it.",
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": 0,
    "upgradeHp": 0,
    "id": "8752877738",
    "aspects": [],
    "traits": [
      "armor"
    ],
    "keywords": [],
    "types": [
      "token",
      "upgrade"
    ],
    "setId": {
      "set": "SOR"
    },
    "internalName": "shield",
    "setCode": "TOKEN_SHIELD"
  },
  {
    "title": "Paz Vizsla",
    "subtitle": "For a Brighter Future",
    "cost": 5,
    "hp": 7,
    "power": 4,
    "text": "Sentinel\nWhen Defeated: If this unit wasn't defeated by combat damage, create 2 Mandalorian tokens.",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": "“Combat damage” is only the damage dealt during the “End attack” step of an attack.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "7107655724",
    "aspects": [
      "vigilance",
      "command",
      "heroism"
    ],
    "traits": [
      "mandalorian"
    ],
    "arena": "ground",
    "keywords": [
      "sentinel"
    ],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 28
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 28
      }
    ],
    "internalName": "paz-vizsla#for-a-brighter-future",
    "setCode": "ASH_028"
  },
  {
    "title": "Open Fire",
    "subtitle": null,
    "cost": 3,
    "hp": null,
    "power": null,
    "text": "Deal 4 damage to a unit.",
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "8148673131",
    "aspects": [
      "aggression"
    ],
    "traits": [
      "tactic"
    ],
    "keywords": [],
    "types": [
      "event"
    ],
    "setId": {
      "set": "TWI",
      "number": 174
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 172
      },
      {
        "set": "TWI",
        "number": 174
      }
    ],
    "internalName": "open-fire",
    "setCode": "TWI_174"
  },
  {
    "title": "Vanquish",
    "subtitle": null,
    "cost": 5,
    "hp": null,
    "power": null,
    "text": "Defeat a non-leader unit.",
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "6472095064",
    "aspects": [
      "vigilance"
    ],
    "traits": [
      "tactic"
    ],
    "keywords": [],
    "types": [
      "event"
    ],
    "setId": {
      "set": "TWI",
      "number": 77
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 78
      },
      {
        "set": "TWI",
        "number": 77
      }
    ],
    "internalName": "vanquish",
    "setCode": "TWI_077"
  },
  {
    "title": "K-2SO",
    "subtitle": "Locking the Vault",
    "cost": 5,
    "hp": 5,
    "power": 3,
    "text": "Ambush\nOn Attack: You may deal 3 damage to a damaged ground unit.",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": "Ambush is an ability that triggers at the same time as “When Played” abilities. The unit does not have to be ready in order to attack.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "6386443776",
    "aspects": [
      "aggression",
      "cunning",
      "heroism"
    ],
    "traits": [
      "rebel",
      "droid"
    ],
    "arena": "ground",
    "keywords": [
      "ambush"
    ],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "LAW",
      "number": 79
    },
    "setCodes": [
      {
        "set": "LAW",
        "number": 79
      }
    ],
    "internalName": "k2so#locking-the-vault",
    "setCode": "LAW_079"
  },
  {
    "title": "Dire Prowess",
    "subtitle": "",
    "cost": 2,
    "hp": 1,
    "power": 1,
    "text": "When Played: You may give a Weakness token to a unit.",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": 1,
    "upgradeHp": 1,
    "id": "3828978526",
    "aspects": [
      "vigilance"
    ],
    "traits": [
      "learned"
    ],
    "keywords": [],
    "types": [
      "upgrade"
    ],
    "setId": {
      "set": "HMW",
      "number": 97
    },
    "setCodes": [
      {
        "set": "HMW",
        "number": 97
      }
    ],
    "internalName": "dire-prowess",
    "setCode": "HMW_097"
  },
  {
    "title": "Battlefield Marine",
    "subtitle": null,
    "cost": 2,
    "hp": 3,
    "power": 3,
    "text": null,
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "4317911650",
    "aspects": [
      "command",
      "heroism"
    ],
    "traits": [
      "rebel",
      "trooper"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "SOR",
      "number": 95
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 95
      }
    ],
    "internalName": "battlefield-marine",
    "setCode": "SOR_095"
  },
  {
    "title": "Weakness",
    "subtitle": "",
    "cost": 0,
    "hp": -1,
    "power": -1,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": -1,
    "upgradeHp": -1,
    "id": "7816991190",
    "aspects": [],
    "traits": [
      "condition"
    ],
    "keywords": [],
    "types": [
      "token",
      "upgrade"
    ],
    "setId": {
      "set": "HMW"
    },
    "internalName": "weakness",
    "setCode": "TOKEN_WEAKNESS"
  },
  {
    "title": "Superlaser Blast",
    "subtitle": null,
    "cost": 8,
    "hp": null,
    "power": null,
    "text": "Defeat all units.",
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "1353201082",
    "aspects": [
      "villainy",
      "vigilance"
    ],
    "traits": [
      "tactic",
      "disaster"
    ],
    "keywords": [],
    "types": [
      "event"
    ],
    "setId": {
      "set": "SOR",
      "number": 43
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 43
      }
    ],
    "internalName": "superlaser-blast",
    "setCode": "SOR_043"
  }
];
function validatePool(pool,scenario){assert.ok(Array.isArray(pool?.cards));for(const code of [...scenario.focusCardIds,...scenario.setupCardIds]){const rows=pool.cards.filter(c=>c.setCode===code);assert.equal(rows.length,1,'Exact selected definition '+code);assert.ok(same(rows[0],reviewedPoolDefinitions.find(c=>c.setCode===code)),'Full reviewed pool metadata '+code);}}
function expected(p){return {cause:p.cause==='combat'?'attack':['ability-damage','attack-ability-damage'].includes(p.cause)?'nonCombatDamage':p.cause==='unique-rule'?'uniqueRule':p.cause==='framework-weakness'?'frameworkEffect':'ability',events:p.cause==='combat'?0:p.cause==='simultaneous-defeat'?2:1,units:p.cause==='combat'?0:p.cause==='simultaneous-defeat'?4:2};}
function protocol(p){validateProbe(p);const plan=[{code:p.cardId}],units=[];if(p.cause==='combat'){units.push({key:'a',code:'ASH_131',owner:'enemy'});plan.push({from:'a',code:'ASH_131',owner:'enemy',target:'focus'});}if(p.cause==='ability-damage')plan.push({code:'TWI_174',owner:'enemy',target:'focus'},{code:'TWI_174',owner:'enemy',target:'focus'});if(p.cause==='direct-defeat')plan.push({code:'TWI_077',owner:'enemy',target:'focus'});if(p.cause==='attack-ability-damage'){units.push({key:'attacker',code:'LAW_079',owner:'enemy'});plan.push({code:'TWI_174',owner:'enemy',target:'focus'},{from:'attacker',code:'LAW_079',owner:'enemy',target:'focus'});}if(p.cause==='framework-weakness'){units.push({key:'host',code:'SOR_095',owner:'enemy'});plan.push({code:'TWI_174',owner:'enemy',target:'focus'},...Array.from({length:3},()=>({code:'HMW_097',owner:'enemy',target:'host'})));}if(p.cause==='unique-rule')plan.push({code:p.cardId});if(p.cause==='simultaneous-defeat')plan.push({code:p.cardId,owner:'enemy'},{code:'SOR_043'});return {plan,units};}
async function fixture(env,pool,scenario,seed){const {sourceHarness:{tokenFixture}}=require('./round-limit-probe-fixture');const p=scenario.probe;validateProbe(p);validatePool(pool,scenario);const ex=expected(p),{plan,units}=protocol(p);let events=[],defeats=[],payments=[],damage=[],prompts=[],createdUnits=[],shieldIds=[],focus=null,other=null,pendingPayment=null,stopped=false,sentinelChecked=false;function payment(card){const aspects=[...card.controller.getAspectsForCosts()];let n=card.cardData.cost;for(const a of card.cardData.aspects){const i=aspects.indexOf(a);if(i<0)n+=2;else aspects.splice(i,1);}return n;}
const sourceScenario={name:scenario.name,family:p.family,seat:p.owner,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes,plan,units,baseDamage:0,
setup(c){const {eg}=c,id=x=>eg.cardId(x.uuid);for(const name of ['onCardDefeated','onTokensCreated','onDamageDealt','onCardPlayed','onUnitEntersPlay','onUpgradeAttached'])eg.game.on(name,e=>{if(stopped)return;const row={name,card:e.card?id(e.card):null,source:e.context?.source?.uuid?id(e.context.source):null,sourceZone:e.context?.source?.zoneName??null,player:e.context?.player?eg.seatOf(e.context.player.id):null,type:e.defeatSource?.type??e.damageSource?.type??null,amount:e.amount??null,tokenType:e.tokenType??null,generated:(e.generatedTokens??[]).map(id),activeAttack:eg.game.currentAttack?.getAttackId?.()??eg.game.currentAttack?.attackId??eg.game.currentAttack?.id??null};events.push(row);if(name==='onCardDefeated'&&(e.card===focus||e.card===other)){row.lastKnown={controller:eg.seatOf(e.lastKnownInformation.controller.id),hp:e.lastKnownInformation.hp,damage:e.lastKnownInformation.damage};defeats.push({event:e,row});}if(name==='onTokensCreated'&&e.tokenType==='mandalorian'){createdUnits.push(...(e.generatedTokens??[]));}if(name==='onTokensCreated'&&e.tokenType==='shield')shieldIds.push(...(e.generatedTokens??[]).map(id));if(name==='onDamageDealt'&&e.card===focus)damage.push({type:e.damageSource.type,amount:e.damageDealt,activeAttack:!!eg.game.currentAttack});});},
beforeWindow(c){if(c.atWindow&&pendingPayment){const paid=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(paid,pendingPayment.cost,'Actual ordinary card payment');payments.push({card:c.eg.cardId(pendingPayment.card.uuid),code:pendingPayment.code,paid,actor:c.eg.seatOf(pendingPayment.actor.id)});pendingPayment=null;}},
beforeApply(c){if(c.atWindow&&c.scratch.incoming&&c.chosen.cardUuid===c.scratch.incoming.uuid&&c.scratch.incoming.zoneName==='hand'){const card=c.scratch.incoming;pendingPayment={card,code:c.pending.code,actor:card.controller,before:card.controller.readyResourceCount,cost:payment(card)};if(c.pending.code===p.cardId){if(!focus){focus=card;c.targets.focus=card;}else other=card;}}},
choose(c){const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';prompts.push({title,actor:c.eg.seatOf(c.pid),labels:c.actions.map(a=>a.label??null),sourceZone:focus?.zoneName});if(/weakness/i.test(title))return c.actions.find(a=>a.cardUuid===focus.uuid);if(p.cause==='unique-rule'&&/unique|copy|copies|defeat/i.test(title)){const a=c.actions.find(a=>a.cardUuid===focus.uuid);if(a)return a;}if(title==='Choose a target for attack'&&p.cause==='combat'){assert.ok(c.actions.some(a=>a.cardUuid===focus.uuid),'Sentinel source is a legal defender');assert.ok(!c.actions.some(a=>a.cardUuid===c.own.base.uuid),'Actual Sentinel removes base from complete target set');sentinelChecked=true;}return undefined;},
assertAfter(c){if(pendingPayment){const paid=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(paid,pendingPayment.cost);payments.push({card:c.eg.cardId(pendingPayment.card.uuid),code:pendingPayment.code,paid,actor:c.eg.seatOf(pendingPayment.actor.id)});pendingPayment=null;}assert.ok(focus);assert.equal(focus.zoneName,'discard','Captured physical source is offboard');assert.equal(payments[0].code,p.cardId);assert.equal(payments[0].paid,7,'Printed5 with actual missing command aspect');const fd=defeats.find(x=>x.event.card===focus);assert.ok(fd,'Actual source defeat event');assert.equal(fd.event.defeatSource.type,ex.cause);assert.equal(fd.event.lastKnownInformation.controller,c.own,'Captured source controller');const id=x=>c.eg.cardId(x.uuid);const creation=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='mandalorian');assert.deepEqual(creation.flatMap(e=>e.generated),createdUnits.map(id),'Batch physical identity/order preserved');for(const batch of creation){const pos=events.indexOf(batch);const enters=events.filter(e=>e.name==='onUnitEntersPlay'&&batch.generated.includes(e.card));assert.deepEqual(enters.map(e=>e.card),batch.generated,'Both native entries retain generated order');assert.ok(enters.every(e=>events.indexOf(e)>pos));const firstShield=events.find(e=>e.name==='onTokensCreated'&&e.tokenType==='shield'&&batch.generated.includes(e.source));assert.ok(firstShield&&enters.every(e=>events.indexOf(e)<events.indexOf(firstShield)),'Complete pair entry precedes native Shielded child creation');}assert.equal(creation.length,ex.events,'Combat false branch emits no onTokensCreated event');assert.equal(createdUnits.length,ex.units);assert.equal(new Set(createdUnits).size,ex.units);assert.equal(new Set(createdUnits.map(id)).size,ex.units);for(const e of creation){assert.equal(e.amount,2);assert.equal(e.sourceZone,'discard');assert.ok([id(focus),other?id(other):null].includes(e.source));}for(const token of createdUnits){assert.equal(token.zoneName,'groundArena');assert.equal(token.exhausted,true);assert.equal(token.getPower(),2);assert.equal(token.getHp(),2);assert.equal(token.upgrades.length,1);const shield=token.upgrades[0];assert.ok(shield.isShield());assert.equal(shield.parentCard,token);assert.equal(shield.owner,token.controller);assert.equal(shield.controller,token.controller);}const actualShieldIds=createdUnits.map(t=>id(t.upgrades[0]));assert.equal(new Set(actualShieldIds).size,ex.units);assert.deepEqual(new Set(shieldIds),new Set(actualShieldIds),'All native Shielded events allocated the exact attached physical Shields');if(p.cause==='combat'){assert.ok(sentinelChecked);assert.ok(damage.some(d=>d.type==='attack'));}if(p.cause==='attack-ability-damage')assert.ok(damage.some(d=>d.type==='ability'&&d.activeAttack),'Ability damage during actual active attack is noncombat');if(p.cause==='framework-weakness'){assert.equal(fd.event.lastKnownInformation.damage,4);assert.equal(fd.event.lastKnownInformation.hp,4);}if(p.cause==='simultaneous-defeat'){assert.equal(other.zoneName,'discard');assert.equal(defeats.length,2);assert.deepEqual(createdUnits.map(t=>c.eg.seatOf(t.controller.id)).sort(),['p1','p1','p2','p2']);}else for(const token of createdUnits)assert.equal(token.controller,c.own);c.observed={sourceId:id(focus),otherSourceId:other?id(other):null,sourceCause:ex.cause,creationEvents:creation,createdUnitIds:createdUnits.map(id),shieldIds:actualShieldIds,payments,damage,events,prompts,sentinelChecked,constructionDisclosure:'Only ordinary admitted cause donors staged. Focus Paz and every event/upgrade paid normally; damage is produced by real actions. No later game-state edits.'};stopped=true;c.targets.stopped=true;},
chooseLater(c){if(c.atWindow)return c.actions.find(a=>a.cardUuid&&c.eg.game.allCards.some(x=>x.uuid===a.cardUuid&&x.isUnit?.()&&x.isInPlay()&&x.controller.id===c.pid))??c.actions.find(a=>a.arg==='pass');const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(title==='Choose a target for attack')return c.actions.find(a=>a.cardUuid===c.eg.player(c.pid).opponent.base.uuid)??c.actions.find(a=>a.cardUuid);return c.actions.find(a=>a.arg==='passAbility')??c.actions.find(a=>a.arg==='all')??c.actions.find(a=>a.arg==='done');}};
const result=await tokenFixture(env,pool,sourceScenario,seed);result.witness.coverageObligationIds=[...scenario.coverageObligationIds];return result;}
module.exports={fixture,validateProbe,validatePool,expected,protocol,dependencies:['lab/kessel-reference/pipeline/defeat-token-creation-fixture.js','lab/kessel-reference/pipeline/round-limit-probe-fixture.js','lab/kessel-reference/pipeline/terminal-completion.js','engine/env.js','bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/unit-entry-state.js','engine/rng.js','bots/players/index.js','kessel:cards/pipeline/defeat-token-creation-probes.js']};
