'use strict';
const assert=require('node:assert/strict'),same=require('node:util').isDeepStrictEqual;
const reviewedProbes=[
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "paid-discard-unit",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "paid-discard-event",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "TWI_174",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "paid-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "empty-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": null
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "single-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "saboteur-sentinel-base",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "sentinel",
        "code": "ASH_117",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "defender",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true,
        "shields": 1
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_117",
      "ASH_201",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_117",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "saboteur-shield-defeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "sentinel",
        "code": "ASH_117",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "defender",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true,
        "shields": 1
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "defender",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_117",
      "ASH_201",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_117",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "combat-death",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "defender",
        "code": "JTL_251",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "defender",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "JTL_251",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "JTL_251",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "repeated-attacks",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 0,
    "scenario": "bounce-reentry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "TWI_226",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_226"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "paid-discard-unit",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "paid-discard-event",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "TWI_174",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "paid-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "otherOwn",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_190",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "discardKey": "chosen",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "empty-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": null
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "single-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "saboteur-sentinel-base",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "sentinel",
        "code": "ASH_117",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "defender",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true,
        "shields": 1
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_117",
      "ASH_201",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_117",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "saboteur-shield-defeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "sentinel",
        "code": "ASH_117",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "defender",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true,
        "shields": 1
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "defender",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_117",
      "ASH_201",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_117",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "combat-death",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "defender",
        "code": "JTL_251",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "defender",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "JTL_251",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "JTL_251",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "repeated-attacks",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "HMW_219",
      "SOR_014",
      "SOR_023"
    ]
  },
  {
    "family": "discard-attack-stat",
    "cardId": "ASH_172",
    "owner": 1,
    "scenario": "bounce-reentry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_172",
        "owner": "own",
        "exhausted": false
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "accept",
        "discardKey": "chosen"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus"
      },
      {
        "code": "ASH_172",
        "owner": "own",
        "from": "focus",
        "target": "enemyBase",
        "abilityChoice": "decline",
        "nextRound": true
      }
    ],
    "deckCardIds": [
      "ASH_172",
      "TWI_226",
      "ASH_190",
      "ASH_061",
      "ASH_131",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_172",
      "ASH_190",
      "ASH_201",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "HMW_174",
      "HMW_178",
      "SOR_014",
      "SOR_023",
      "TWI_226"
    ]
  }
];
const reviewedPoolDefinitions=[
  {
    "arena": "ground",
    "aspects": [
      "vigilance",
      "heroism"
    ],
    "cost": 4,
    "deployBox": null,
    "epicAction": "",
    "hp": 5,
    "id": "1029172801",
    "internalName": "strike-team-vanguard",
    "keywords": [],
    "power": 5,
    "rules": null,
    "setCode": "ASH_061",
    "setCodes": [
      {
        "number": 61,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 61,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Strike Team Vanguard",
    "traits": [
      "rebel",
      "trooper"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "command"
    ],
    "cost": 6,
    "deployBox": null,
    "epicAction": "",
    "hp": 7,
    "id": "9890561214",
    "internalName": "dinosaur-turtle",
    "keywords": [],
    "power": 7,
    "rules": null,
    "setCode": "ASH_131",
    "setCodes": [
      {
        "number": 131,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 131,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Dinosaur Turtle",
    "traits": [
      "creature"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "title": "Razor Crest",
    "subtitle": "Outfitted Armament",
    "cost": 4,
    "hp": 5,
    "power": 3,
    "text": "Saboteur (When this unit attacks, ignore Sentinel and defeat the defender's Shields.)\nOn Attack: You may discard a card from your hand. If you do, this unit gets +2/+0 for this attack.",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "4046328280",
    "aspects": [
      "aggression"
    ],
    "traits": [
      "mandalorian",
      "vehicle",
      "transport"
    ],
    "arena": "space",
    "keywords": [
      "saboteur"
    ],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 172
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 172
      }
    ],
    "internalName": "razor-crest#outfitted-armament",
    "setCode": "ASH_172"
  },
  {
    "arena": "ground",
    "aspects": [
      "cunning",
      "villainy"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": 1,
    "id": "4344365271",
    "internalName": "peridea-bandit",
    "keywords": [],
    "power": 4,
    "rules": null,
    "setCode": "ASH_190",
    "setCodes": [
      {
        "number": 190,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 190,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Peridea Bandit",
    "traits": [
      "fringe"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "space",
    "aspects": [
      "cunning",
      "heroism"
    ],
    "cost": 1,
    "deployBox": null,
    "epicAction": "",
    "hp": 2,
    "id": "9620848758",
    "internalName": "open-circle-ace",
    "keywords": [],
    "power": 2,
    "rules": null,
    "setCode": "ASH_201",
    "setCodes": [
      {
        "number": 201,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 201,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Open Circle Ace",
    "traits": [
      "republic",
      "vehicle",
      "fighter"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "villainy"
    ],
    "cost": 4,
    "deployBox": null,
    "epicAction": "",
    "hp": 4,
    "id": "9011599796",
    "internalName": "death-trooper-squad",
    "keywords": [],
    "power": 5,
    "rules": null,
    "setCode": "ASH_242",
    "setCodes": [
      {
        "number": 242,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 242,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Death Trooper Squad",
    "traits": [
      "imperial",
      "trooper"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [],
    "cost": 3,
    "deployBox": null,
    "epicAction": "",
    "hp": 4,
    "id": "5556203656",
    "internalName": "noti-mobile-pod",
    "keywords": [],
    "power": 3,
    "rules": null,
    "setCode": "ASH_261",
    "setCodes": [
      {
        "number": 261,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 261,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "",
    "title": "Noti Mobile Pod",
    "traits": [
      "vehicle",
      "transport"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "vigilance",
      "vigilance"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": 7,
    "id": "5691187672",
    "internalName": "nala-se#silent-survivor",
    "keywords": [],
    "power": 1,
    "rules": null,
    "setCode": "HMW_082",
    "setCodes": [
      {
        "number": 82,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 82,
      "set": "HMW"
    },
    "subtitle": "Silent Survivor",
    "text": "",
    "title": "Nala Se",
    "traits": [
      "kaminoan"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "vigilance"
    ],
    "cost": 7,
    "deployBox": null,
    "epicAction": "",
    "hp": 8,
    "id": "1226993616",
    "internalName": "coastal-catamarans",
    "keywords": [],
    "power": 8,
    "rules": null,
    "setCode": "HMW_093",
    "setCodes": [
      {
        "number": 93,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 93,
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Coastal Catamarans",
    "traits": [
      "vehicle",
      "transport"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "command",
      "heroism"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": 4,
    "id": "8382448205",
    "internalName": "ewok-brigade",
    "keywords": [],
    "power": 2,
    "rules": null,
    "setCode": "HMW_116",
    "setCodes": [
      {
        "number": 116,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 116,
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Ewok Brigade",
    "traits": [
      "ewok"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "command",
      "command"
    ],
    "cost": 3,
    "deployBox": null,
    "epicAction": "",
    "hp": 5,
    "id": "0886129762",
    "internalName": "mace-windu#austere-centrist",
    "keywords": [],
    "power": 4,
    "rules": null,
    "setCode": "HMW_128",
    "setCodes": [
      {
        "number": 128,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 128,
      "set": "HMW"
    },
    "subtitle": "Austere Centrist",
    "text": "",
    "title": "Mace Windu",
    "traits": [
      "force",
      "jedi"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "command"
    ],
    "cost": 3,
    "deployBox": null,
    "epicAction": "",
    "hp": 4,
    "id": "0212754007",
    "internalName": "arena-reek#fixture-of-ceremony",
    "keywords": [],
    "power": 4,
    "rules": null,
    "setCode": "HMW_135",
    "setCodes": [
      {
        "number": 135,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 135,
      "set": "HMW"
    },
    "subtitle": "Fixture of Ceremony",
    "text": "",
    "title": "Arena Reek",
    "traits": [
      "creature"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "aggression",
      "villainy"
    ],
    "cost": 4,
    "deployBox": null,
    "epicAction": "",
    "hp": 5,
    "id": "7827651708",
    "internalName": "filthy-dianoga",
    "keywords": [],
    "power": 5,
    "rules": null,
    "setCode": "HMW_155",
    "setCodes": [
      {
        "number": 155,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 155,
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Filthy Dianoga",
    "traits": [
      "creature"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "aggression",
      "heroism"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": 3,
    "id": "4516882765",
    "internalName": "champions-of-endor",
    "keywords": [],
    "power": 3,
    "rules": null,
    "setCode": "HMW_163",
    "setCodes": [
      {
        "number": 163,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 163,
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Champions of Endor",
    "traits": [
      "ewok"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "aggression",
      "aggression"
    ],
    "cost": 4,
    "deployBox": null,
    "epicAction": "",
    "hp": 6,
    "id": "3460896271",
    "internalName": "maul#only-revenge-remains",
    "keywords": [],
    "power": 6,
    "rules": null,
    "setCode": "HMW_174",
    "setCodes": [
      {
        "number": 174,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 174,
      "set": "HMW"
    },
    "subtitle": "Only Revenge Remains",
    "text": "",
    "title": "Maul",
    "traits": [
      "force",
      "underworld"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "space",
    "aspects": [
      "aggression"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": 3,
    "id": "5508530442",
    "internalName": "desperate-nantex",
    "keywords": [],
    "power": 2,
    "rules": null,
    "setCode": "HMW_178",
    "setCodes": [
      {
        "number": 178,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 178,
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Desperate Nantex",
    "traits": [
      "separatist",
      "vehicle",
      "fighter"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "aggression",
      "heroism"
    ],
    "cost": 4,
    "deployBox": "On Attack: Deal 1 damage to each enemy base.",
    "epicAction": "Epic Action: If you control 4 or more resources, deploy this leader.",
    "hp": 5,
    "id": "4841169874",
    "internalName": "sabine-wren#galvanized-revolutionary",
    "keywords": [],
    "power": 2,
    "rules": null,
    "setCode": "SOR_014",
    "setCodes": [
      {
        "number": 14,
        "set": "SOR"
      }
    ],
    "setId": {
      "number": 14,
      "set": "SOR"
    },
    "subtitle": "Galvanized Revolutionary",
    "text": "Action [exhaust]: Deal 1 damage to each base.",
    "title": "Sabine Wren",
    "traits": [
      "mandalorian",
      "rebel",
      "spectre"
    ],
    "types": [
      "leader"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "aspects": [
      "command"
    ],
    "cost": null,
    "deployBox": null,
    "epicAction": null,
    "hp": 30,
    "id": "0507674993",
    "internalName": "command-center",
    "keywords": [],
    "power": null,
    "rules": null,
    "setCode": "SOR_023",
    "setCodes": [
      {
        "number": 23,
        "set": "SOR"
      }
    ],
    "setId": {
      "number": 23,
      "set": "SOR"
    },
    "subtitle": null,
    "text": null,
    "title": "Command Center",
    "traits": [
      "death star"
    ],
    "types": [
      "base"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "aspects": [
      "aggression"
    ],
    "cost": 3,
    "deployBox": null,
    "epicAction": null,
    "hp": null,
    "id": "8148673131",
    "internalName": "open-fire",
    "keywords": [],
    "power": null,
    "rules": null,
    "setCode": "TWI_174",
    "setCodes": [
      {
        "number": 172,
        "set": "SOR"
      },
      {
        "number": 174,
        "set": "TWI"
      }
    ],
    "setId": {
      "number": 174,
      "set": "TWI"
    },
    "subtitle": null,
    "text": "Deal 4 damage to a unit.",
    "title": "Open Fire",
    "traits": [
      "tactic"
    ],
    "types": [
      "event"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "ground",
    "aspects": [
      "cunning",
      "cunning"
    ],
    "cost": 1,
    "deployBox": null,
    "epicAction": "",
    "hp": 3,
    "id": "9427322990",
    "internalName": "jaxxon#i-can-hear-you-breathing",
    "keywords": [],
    "power": 3,
    "rules": null,
    "setCode": "HMW_219",
    "setCodes": [
      {
        "number": 219,
        "set": "HMW"
      }
    ],
    "setId": {
      "number": 219,
      "set": "HMW"
    },
    "subtitle": "I Can Hear You Breathing!",
    "text": "",
    "title": "Jaxxon",
    "traits": [
      "underworld"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "arena": "space",
    "aspects": [
      "command"
    ],
    "cost": 1,
    "deployBox": null,
    "epicAction": "",
    "hp": 2,
    "id": "7969469465",
    "internalName": "outland-protector",
    "keywords": [
      "sentinel"
    ],
    "power": 1,
    "rules": null,
    "setCode": "ASH_117",
    "setCodes": [
      {
        "number": 117,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 117,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "Sentinel (Enemy units in this arena must attack a Sentinel when they attack you.)",
    "title": "Outland Protector",
    "traits": [
      "imperial",
      "vehicle",
      "fighter"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "aspects": [],
    "cost": 0,
    "deployBox": null,
    "epicAction": null,
    "hp": 0,
    "id": "8752877738",
    "internalName": "shield",
    "keywords": [],
    "power": 0,
    "rules": null,
    "setCode": "TOKEN_SHIELD",
    "setId": {
      "set": "SOR"
    },
    "subtitle": null,
    "text": "If damage would be dealt to attached unit, prevent that damage. If you do, defeat a Shield token on it.",
    "title": "Shield",
    "traits": [
      "armor"
    ],
    "types": [
      "token",
      "upgrade"
    ],
    "unique": false,
    "upgradeHp": 0,
    "upgradePower": 0
  },
  {
    "arena": "space",
    "aspects": [
      "heroism"
    ],
    "cost": 6,
    "deployBox": null,
    "epicAction": "",
    "hp": 7,
    "id": "1271289335",
    "internalName": "jedi-light-cruiser",
    "keywords": [],
    "power": 6,
    "rules": null,
    "setCode": "JTL_251",
    "setCodes": [
      {
        "number": 251,
        "set": "JTL"
      }
    ],
    "setId": {
      "number": 251,
      "set": "JTL"
    },
    "subtitle": "",
    "text": "",
    "title": "Jedi Light Cruiser",
    "traits": [
      "jedi",
      "republic",
      "vehicle",
      "capital ship"
    ],
    "types": [
      "unit"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  },
  {
    "aspects": [
      "cunning"
    ],
    "cost": 3,
    "deployBox": null,
    "epicAction": null,
    "hp": null,
    "id": "7202133736",
    "internalName": "waylay",
    "keywords": [],
    "power": null,
    "rules": "Abilities that return a card to hand must choose a card in play unless otherwise specified.\n",
    "setCode": "TWI_226",
    "setCodes": [
      {
        "number": 222,
        "set": "SOR"
      },
      {
        "number": 226,
        "set": "TWI"
      }
    ],
    "setId": {
      "number": 226,
      "set": "TWI"
    },
    "subtitle": null,
    "text": "Return a non-leader unit to its owner's hand.",
    "title": "Waylay",
    "traits": [
      "trick"
    ],
    "types": [
      "event"
    ],
    "unique": false,
    "upgradeHp": null,
    "upgradePower": null
  }
];
function validateProbe(p){assert.ok(reviewedProbes.some(q=>same(p,q)),'Complete closed source construction probe required');}
function validatePool(pool,p){for(const id of p.selectedCardIds){const rows=pool.cards.filter(e=>e.setCode===id);assert.equal(rows.length,1,'One selected full definition '+id);assert.ok(same(rows[0],reviewedPoolDefinitions.find(e=>e.setCode===id)),'Complete selected definition '+id);}}
function payment(card){const aspects=[...card.controller.getAspectsForCosts()];let n=card.cost;for(const a of card.cardData.aspects){const i=aspects.indexOf(a);if(i<0)n+=2;else aspects.splice(i,1);}return n;}
async function fixture(env,pool,scenario,seed){const p=scenario.probe;validateProbe(p);validatePool(pool,p);const {sourceHarness:{tokenFixture}}=require('./round-limit-probe-fixture');let stopped=false,pendingPayment=null,events=[],menus=[],payments=[],declines=[],attackStarts=[],postAttack=[],focus=null,setupIds={};const id=(eg,c)=>c?.uuid?eg.cardId(c.uuid):null,snap=(eg,c)=>c?{id:id(eg,c),zone:c.zoneName,pendingDefeat:c.isInPlay()?c.pendingDefeat:null,power:c.isInPlay()?c.getPower():null,hp:c.isInPlay()?c.getHp():null,damage:c.isInPlay()?c.damage:null,activeAttack:c.isInPlay()?c.activeAttack?.id??null:null,modifiers:c.getOngoingEffectValues('modifyStats').map(v=>({power:v.power??null,hp:v.hp??null})),controller:eg.seatOf(c.controller.id)}:null;
const ss={name:scenario.name,family:p.family,seat:p.owner,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes:[],extraCodes:p.deckCardIds,units:p.stagedUnits,plan:p.scripts,baseDamage:0,
setup(c){const {eg,own,enemy,targets:t}=c,allocated=new Set(Object.values(t).filter(x=>x?.uuid).map(x=>x.uuid));focus=t.focus??null;const matches=(x,code)=>[x.cardData.setId,...(x.cardData.setCodes??[])].some(s=>s.set+'_'+String(s.number).padStart(3,'0')===code),keep=new Set();for(const row of p.handCards){const pl=row.owner==='enemy'?enemy:own,card=[...pl.drawDeck,...pl.getCardsInZone('hand'),...pl.getCardsInZone('resource')].find(x=>!allocated.has(x.uuid)&&matches(x,row.code));assert.ok(card,'Literal physical hand reference '+row.key);allocated.add(card.uuid);keep.add(card.uuid);card.moveTo('hand');t[row.key]=card;setupIds[row.key]=id(eg,card);}for(const pl of [own,enemy])for(const code of new Set(p.scripts.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===pl).map(s=>s.code))){const count=p.scripts.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===pl).length;for(const card of pl.getCardsInZone('hand').filter(x=>!keep.has(x.uuid)&&matches(x,code)).slice(0,count))keep.add(card.uuid);}for(const pl of [own,enemy])for(const card of pl.getCardsInZone('hand').slice())if(!keep.has(card.uuid)){card.moveTo('resource');card.exhausted=false;}for(const row of p.stagedUnits)setupIds[row.key]=id(eg,t[row.key]);if(t.defender?.upgrades?.length)setupIds.defenderShield=id(eg,t.defender.upgrades[0]);for(const name of ['onAttackDeclared','onAttackEnd','onCardDiscarded','onCardsDiscardedFromHand','onEffectApplied','onDamageDealt','onCardDefeated','onCardPlayed','onCardMoved'])eg.game.on(name,e=>{if(stopped)return;events.push({name,card:id(eg,e.card),source:id(eg,e.context?.source),player:e.context?.player?eg.seatOf(e.context.player.id):null,discardedFrom:e.discardedFromZone??null,amount:e.damageDealt??null,requestedAmount:e.amount??null,type:e.damageSource?.type??null,attackId:e.attack?.id??e.damageSource?.attack?.id??null,damageDealtBy:(e.damageSource?.damageDealtBy??[]).map(x=>id(eg,x)),focus:snap(eg,focus),resourceCount:own.readyResourceCount});});},
beforeWindow(c){if(c.atWindow&&pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost,'Ordinary actual resource cost');payments.push({code:pendingPayment.code,card:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}if(c.atWindow&&focus&&events.some(e=>e.name==='onAttackEnd')){const s=snap(c.eg,focus);if(!postAttack.some(x=>x.step===c.step))postAttack.push({step:c.step,...s});if(focus.isInPlay()){assert.equal(focus.getPower(),3,'Attack duration buff gone before next action');assert.equal(focus.getOngoingEffectValues('modifyStats').length,0);}}},
beforeApply(c){if(!c.atWindow||!c.scratch.incoming||c.chosen.cardUuid!==c.scratch.incoming.uuid)return;const card=c.scratch.incoming;if(card.zoneName==='hand'){pendingPayment={card,code:c.pending.code,actor:card.controller,before:card.controller.readyResourceCount,cost:payment(card)};if(c.pending.code===p.cardId){if(focus)assert.equal(card,focus,'Same physical source returns and is actually replayed');focus=card;c.targets.focus=card;}}else if(card===focus){assert.equal(focus.getPower(),3,'Every real attack starts at printed power');assert.equal(focus.getOngoingEffectValues('modifyStats').length,0);attackStarts.push({step:c.step,source:snap(c.eg,focus),hand:c.own.getCardsInZone('hand').map(x=>id(c.eg,x)),readyResources:c.own.readyResourceCount,choice:c.pending.abilityChoice});}},
choose(c){const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';menus.push({title,actor:c.eg.seatOf(c.pid),focus:snap(c.eg,focus),actions:c.actions.map(a=>({arg:a.arg??null,label:a.label??null,card:a.cardUuid?c.eg.cardId(a.cardUuid):null}))});if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(title==='Choose a target for attack'){if(p.scenario.startsWith('saboteur')){assert.ok(c.actions.some(a=>a.cardUuid===c.enemy.base.uuid),'Native Saboteur ignores space Sentinel');assert.ok(c.actions.some(a=>a.cardUuid===c.targets.sentinel.uuid));assert.ok(c.actions.some(a=>a.cardUuid===c.targets.defender.uuid));}return c.actions.find(a=>a.cardUuid===c.targets[c.pending.target]?.uuid);}if(title==='You may trigger this ability'){assert.equal(c.pid,c.own.id,'Captured attacking player chooses optional self ability');assert.deepEqual(c.actions.map(a=>a.arg).sort(),['pass','trigger'],'Exact source optional menu, no cancel action');const decline=c.pending.abilityChoice==='decline',a=c.actions.find(a=>a.arg===(decline?'pass':'trigger'));assert.ok(a,'Actual optional ability choice');if(decline)declines.push({step:c.step,arg:a.arg,label:a.label});return a;}if(/discard for Razor Crest's effect/.test(title)){assert.equal(c.pid,c.own.id);assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.foreignHand?.uuid),'Enemy hand is never eligible');assert.ok(!c.actions.some(a=>a.cardUuid===focus.uuid),'Attacker is not discarded as a cost');assert.ok(!c.actions.some(a=>a.arg==='cancel'),'Committed hand discard effect has no cancellation/refund');assert.deepEqual(c.actions.filter(a=>a.cardUuid).map(a=>a.cardUuid).sort(),c.own.getCardsInZone('hand').map(x=>x.uuid).sort(),'Complete own hand including every unit/event, no cardtype filter');const a=c.actions.find(a=>a.cardUuid===c.targets[c.pending.discardKey]?.uuid);assert.ok(a,'Exact declared physical own hand selection');return a;}return undefined;},
assertAfter(c){if(pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost);payments.push({code:pendingPayment.code,card:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}assert.ok(focus);const focusId=id(c.eg,focus),fromFocus=events.filter(e=>e.source===focusId),discard=fromFocus.filter(e=>e.name==='onCardDiscarded'),overall=fromFocus.filter(e=>e.name==='onCardsDiscardedFromHand'),buff=fromFocus.filter(e=>e.name==='onEffectApplied'&&e.card===focusId),hits=events.filter(e=>e.name==='onDamageDealt'&&e.damageDealtBy.includes(focusId));const accepted=p.scenario!=='paid-decline'&&p.scenario!=='empty-hand';assert.equal(discard.length,accepted?1:0);assert.equal(overall.length,discard.length);assert.equal(buff.length,discard.length,'ifYouDo is tied to actual discard event resolution');if(discard.length){assert.equal(discard[0].card,id(c.eg,c.targets.chosen));assert.equal(discard[0].discardedFrom,'hand');assert.equal(discard[0].player,c.eg.seatOf(c.own.id));assert.equal(c.targets.chosen.zoneName,'discard');assert.ok(events.indexOf(overall[0])>events.indexOf(discard[0]));assert.ok(events.indexOf(buff[0])>events.indexOf(overall[0]));assert.equal(discard[0].resourceCount,attackStarts[0].readyResources,'Discard is effect, spends no resource cost');assert.equal(buff[0].focus.activeAttack,0,'First attack identity0 retained, not truthiness');}const expectedHits=p.scenario==='repeated-attacks'||p.scenario==='bounce-reentry'?[5,3]:[accepted?5:3];assert.deepEqual(hits.map(e=>e.requestedAmount),expectedHits,'Actual combat requested damage reflects attack buff');assert.deepEqual(hits.map(e=>e.amount),p.scenario==='saboteur-shield-defeat'?[2]:expectedHits,'Actual dealt damage respects target remaining HP');assert.ok(hits.every(e=>e.type==='attack'));assert.ok(hits.every((e,i)=>e.focus?.power===expectedHits[i]));assert.equal(attackStarts.length,expectedHits.length);const ends=events.filter(e=>e.name==='onAttackEnd');assert.deepEqual(ends.map(e=>e.focus.power),expectedHits,'Buff remains through actual attack-end event before cleanup, including combat-lethal source whose defeat is deferred');if(p.scenario==='paid-decline')assert.equal(declines.length,1);if(['repeated-attacks','bounce-reentry'].includes(p.scenario))assert.equal(declines.length,1);if(p.scenario==='empty-hand'){assert.equal(attackStarts[0].hand.length,0);assert.equal(menus.filter(x=>x.title==='You may trigger this ability').length,0,'No eligible hand suppresses optional prompt, not optional Skip/noeffect confirmation');assert.equal(menus.filter(x=>/discard for Razor Crest/.test(x.title)).length,0);}if(p.scenario==='single-hand')assert.equal(menus.find(x=>/discard for Razor Crest/.test(x.title)).actions.filter(x=>x.card).length,1,'One card still produces actual selection prompt');if(p.scenario==='paid-decline')assert.equal(c.targets.chosen.zoneName,'hand','Decline retains declared physical hand card');const paid=payments.filter(x=>x.code===p.cardId);assert.equal(paid.length,p.scenario.startsWith('paid-')||p.scenario==='bounce-reentry'?1:0);assert.ok(paid.every(x=>x.actual===4));if(p.scenario==='combat-death'){assert.equal(focus.zoneName,'discard');assert.equal(c.targets.defender.damage,5);assert.ok(events.findIndex(e=>e.name==='onCardDefeated'&&e.card===focusId)>events.findIndex(e=>e.name==='onAttackEnd'),'Actual combat-lethal source defeat is deferred until after attack-end event');assert.equal(focus.getOngoingEffectValues('modifyStats').length,0,'Death removes scoped buff');}else{assert.equal(focus.zoneName,'spaceArena');assert.equal(focus.getPower(),3);assert.equal(focus.getOngoingEffectValues('modifyStats').length,0);}if(p.scenario==='saboteur-shield-defeat'){assert.equal(c.targets.defender.zoneName,'discard');const shieldDefeat=events.findIndex(e=>e.name==='onCardDefeated'&&e.card===setupIds.defenderShield),damage=events.findIndex(e=>e.name==='onDamageDealt'&&e.damageDealtBy.includes(focusId));assert.ok(shieldDefeat>=0&&shieldDefeat<damage,'Native Saboteur defeats exact physical Shield before combat damage');assert.equal(focus.damage,2);}if(p.scenario==='saboteur-sentinel-base'){assert.equal(c.enemy.base.damage,5);assert.equal(c.targets.defender.upgrades.length,1,'Unchosen unit Shield unaffected');}c.observed={focus:snap(c.eg,focus),setupIds,events,menus,payments,declines,attackStarts,postAttack,sourceScenario:p.scenario,selectedCardIds:p.selectedCardIds,deckCardIds:p.deckCardIds,status:'source-only; native/Wasm unassessed'};stopped=true;c.targets.stopped=true;},
chooseLater(c){if(c.atWindow)return c.actions.find(a=>a.arg==='pass');const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');return c.actions.find(a=>a.arg==='passAbility')??c.actions.find(a=>a.arg==='pass')??c.actions.find(a=>a.arg==='noTarget')??c.actions.find(a=>a.arg==='all')??c.actions.find(a=>a.arg==='done');}};
let game;try{game=await tokenFixture(env,pool,ss,seed);}catch(e){e.diagnostic??={};e.diagnostic.sourceTimeline={events,menus,payments,attackStarts,postAttack};throw e;}game.records[0].constructionParameters=structuredClone(p);game.records[0].fixtureConstruction='At initial real actionwindow use literal deckCardIds, stage declared physical units and initial Shields, move declared physical handcards and scripts to hand, other initial handcards to resources, and up to24 deckcards into readyresources. Existing units/Shields are setup not paid/nativeentry claims. All declared RazorCrest/Waylay plays, attacks, optional/discard choices, combat and natural phase transitions thereafter are actual engine actions; no later synthetic mutations. Terminal completion uses quiet pass/resourcing decisions.';game.witness.coverageObligationIds=[...scenario.coverageObligationIds];return game;}

module.exports={fixture,validateProbe,validatePool,dependencies:['bots/omni/rs/inactive-phase-keyword-state.js', "lab/kessel-reference/pipeline/round-limit-interaction-fixture.js","lab/kessel-reference/pipeline/round-limit-probe-fixture.js","lab/kessel-reference/pipeline/probe-fixture.js","lab/kessel-reference/pipeline/terminal-completion.js","engine/env.js","engine/rng.js","engine/view.js","engine/stdio.js","engine/recorder.js","bots/omni/rs/state.js","bots/omni/rs/state-evidence.js","bots/omni/rs/unit-entry-state.js","bots/omni/rs/support-state.js","bots/omni/rs/round-limit-state.js","bots/omni/rs/pool.js","bots/players/index.js","bots/players/random.js","bots/players/rush.js","bots/players/heuristic.js","bots/players/profiles.js","bots/players/ismcts.js","bots/players/belief.js","bots/players/omniscient.js","bots/examples/random-bot.js","bots/examples/search-bot.js","bots/omni/search.js","bots/omni/evaluate.js","kessel:cards/pipeline/round-limit-probes.js","lab/kessel-reference/pipeline/discard-attack-stat-fixture.js","kessel:cards/pipeline/discard-attack-stat-probes.js"]};
