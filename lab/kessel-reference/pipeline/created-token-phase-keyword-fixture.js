'use strict';
const assert=require('node:assert/strict'),same=require('node:util').isDeepStrictEqual;
const reviewedProbes=[
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "ground-sentinel",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_061",
        "owner": "enemy",
        "from": "attacker",
        "target": "created0"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "saboteur-bypass-base",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_173",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_173",
        "owner": "enemy",
        "from": "attacker",
        "target": "ownBase"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_173",
      "ASH_091",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
      "ASH_131",
      "ASH_173",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "saboteur-shield-defeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_173",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_173",
        "owner": "enemy",
        "from": "attacker",
        "target": "created0"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_173",
      "ASH_091",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
      "ASH_131",
      "ASH_173",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "other-arena-negative",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": false
      },
      {
        "key": "ownSpace",
        "code": "ASH_201",
        "owner": "own",
        "exhausted": true
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_201",
        "owner": "enemy",
        "from": "attacker",
        "target": "ownSpace"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_201",
      "ASH_091",
      "ASH_061",
      "ASH_131",
      "ASH_190",
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
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "phase-expiry-no-attacks-terminal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "repeated-events",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "departure-new-creation",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "created0"
      },
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
      "TWI_226",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_226"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 0,
    "scenario": "framework-death-before-then",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "snoke",
        "code": "SHD_037",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SHD_037",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SHD_037",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "ground-sentinel",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_061",
        "owner": "enemy",
        "from": "attacker",
        "target": "created0"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "saboteur-bypass-base",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_173",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_173",
        "owner": "enemy",
        "from": "attacker",
        "target": "ownBase"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_173",
      "ASH_091",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
      "ASH_131",
      "ASH_173",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "saboteur-shield-defeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_173",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_173",
        "owner": "enemy",
        "from": "attacker",
        "target": "created0"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_173",
      "ASH_091",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
      "ASH_131",
      "ASH_173",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "other-arena-negative",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": false
      },
      {
        "key": "ownSpace",
        "code": "ASH_201",
        "owner": "own",
        "exhausted": true
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_201",
        "owner": "enemy",
        "from": "attacker",
        "target": "ownSpace"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_201",
      "ASH_091",
      "ASH_061",
      "ASH_131",
      "ASH_190",
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
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "phase-expiry-no-attacks-terminal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "repeated-events",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "departure-new-creation",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "marine",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "oldMando",
        "tokenType": "mandalorian",
        "owner": "own",
        "zone": "ground",
        "exhausted": true,
        "attachments": [
          {
            "tokenType": "shield"
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "created0"
      },
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_061",
      "ASH_091",
      "TWI_226",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_226"
    ]
  },
  {
    "family": "created-token-phase-keyword",
    "cardId": "ASH_091",
    "owner": 1,
    "scenario": "framework-death-before-then",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "snoke",
        "code": "SHD_037",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_091",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "SHD_037",
      "ASH_091",
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
      "HMW_178"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_091",
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
      "SHD_037",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD"
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
    "title": "Buy Time",
    "subtitle": "",
    "cost": 3,
    "hp": null,
    "power": null,
    "text": "Create a Mandalorian token and give it Sentinel for this phase. (Enemy units in its arena must attack a Sentinel when they attack you.)",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "6201936455",
    "aspects": [
      "vigilance"
    ],
    "traits": [
      "tactic"
    ],
    "keywords": [
      "sentinel"
    ],
    "types": [
      "event"
    ],
    "setId": {
      "set": "ASH",
      "number": 91
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 91
      }
    ],
    "internalName": "buy-time",
    "setCode": "ASH_091"
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
    "arena": "ground",
    "aspects": [
      "command",
      "heroism"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": null,
    "hp": 3,
    "id": "4317911650",
    "internalName": "battlefield-marine",
    "keywords": [],
    "power": 3,
    "rules": null,
    "setCode": "SOR_095",
    "setCodes": [
      {
        "number": 95,
        "set": "SOR"
      }
    ],
    "setId": {
      "number": 95,
      "set": "SOR"
    },
    "subtitle": null,
    "text": null,
    "title": "Battlefield Marine",
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
      "vigilance"
    ],
    "cost": 0,
    "deployBox": null,
    "epicAction": "",
    "hp": 2,
    "id": "8192010342",
    "internalName": "mandalorian",
    "keywords": [
      "shielded"
    ],
    "power": 2,
    "rules": null,
    "setCode": "TOKEN_MANDALORIAN",
    "setId": {
      "set": "ASH"
    },
    "subtitle": "",
    "text": "Shielded (When you create this token, give a Shield token to it.)",
    "title": "Mandalorian",
    "traits": [
      "mandalorian"
    ],
    "types": [
      "token",
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
    "arena": "ground",
    "aspects": [
      "aggression"
    ],
    "cost": 4,
    "deployBox": null,
    "epicAction": "",
    "hp": 5,
    "id": "4513422222",
    "internalName": "shydopp-pirate-skiff",
    "keywords": [
      "saboteur"
    ],
    "power": 4,
    "rules": null,
    "setCode": "ASH_173",
    "setCodes": [
      {
        "number": 173,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 173,
      "set": "ASH"
    },
    "subtitle": "",
    "text": "Saboteur (When this unit attacks, ignore Sentinel and defeat the defender's Shields.)",
    "title": "Shydopp Pirate Skiff",
    "traits": [
      "underworld",
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
  },
  {
    "arena": "ground",
    "aspects": [
      "villainy",
      "vigilance"
    ],
    "cost": 8,
    "deployBox": null,
    "epicAction": null,
    "hp": 6,
    "id": "3731235174",
    "internalName": "supreme-leader-snoke#shadow-ruler",
    "keywords": [],
    "power": 6,
    "rules": null,
    "setCode": "SHD_037",
    "setCodes": [
      {
        "number": 37,
        "set": "SHD"
      }
    ],
    "setId": {
      "number": 37,
      "set": "SHD"
    },
    "subtitle": "Shadow Ruler",
    "text": "Each enemy non-leader unit gets –2/–2.",
    "title": "Supreme Leader Snoke",
    "traits": [
      "force",
      "first order",
      "official"
    ],
    "types": [
      "unit"
    ],
    "unique": true,
    "upgradeHp": null,
    "upgradePower": null
  }
];
function validateProbe(p){assert.ok(reviewedProbes.some(q=>same(p,q)),'Complete closed source construction probe required');}
function validatePool(pool,p){for(const id of p.selectedCardIds){const rows=pool.cards.filter(e=>e.setCode===id);assert.equal(rows.length,1,'One selected full definition '+id);assert.ok(same(rows[0],reviewedPoolDefinitions.find(e=>e.setCode===id)),'Complete selected definition '+id);}}
function payment(card){const aspects=[...card.controller.getAspectsForCosts()];let n=card.cost;for(const a of card.cardData.aspects){const i=aspects.indexOf(a);if(i<0)n+=2;else aspects.splice(i,1);}return n;}
async function fixture(env,pool,scenario,seed){const p=scenario.probe;validateProbe(p);validatePool(pool,p);const {sourceHarness:{tokenFixture}}=require('./round-limit-probe-fixture');let stopped=false,pendingPayment=null,events=[],menus=[],payments=[],created=[],focus=[],initialGrant=null;const id=(eg,c)=>c?.uuid?eg.cardId(c.uuid):null, snap=(eg,c)=>({id:id(eg,c),zone:c.zoneName,pendingDefeat:c.isInPlay()?c.pendingDefeat:null,sentinel:c.isUnit?.()?c.hasSomeKeyword('sentinel'):false,shielded:c.isUnit?.()?c.hasSomeKeyword('shielded'):false,shields:c.isUnit?.()&&c.isInPlay()?(c.upgrades??[]).map(x=>id(eg,x)):[],hp:c.isUnit?.()&&c.isInPlay()?c.getHp():null,damage:c.isUnit?.()&&c.isInPlay()?c.damage:null});
const ss={name:scenario.name,family:p.family,seat:p.owner,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes:[],extraCodes:p.deckCardIds,units:p.stagedUnits,plan:p.scripts,baseDamage:0,waitForRegroup:p.scenario==='phase-expiry-no-attacks-terminal',
setup(c){const {eg,own,enemy,targets:t}=c;const keep=new Set();for(const pl of [own,enemy])for(const code of new Set(p.scripts.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===pl).map(s=>s.code))){let count=p.scripts.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===pl).length;for(const card of pl.getCardsInZone('hand').filter(x=>[x.cardData.setId,...(x.cardData.setCodes??[])].some(s=>s.set+'_'+String(s.number).padStart(3,'0')===code)).slice(0,count))keep.add(card.uuid);}for(const pl of [own,enemy])for(const card of pl.getCardsInZone('hand').slice())if(!keep.has(card.uuid)){card.moveTo('resource');card.exhausted=false;}for(const row of p.nativeTokenRefs){const pl=row.owner==='enemy'?enemy:own,card=eg.game.generateToken(pl,row.tokenType);card.moveTo(row.zone+'Arena');card.exhausted=row.exhausted;for(const a of row.attachments)eg.game.generateToken(pl,a.tokenType).attachTo(card);t[row.key]=card;}for(const name of ['onTokensCreated','onUnitEntersPlay','onEffectApplied','onCardDefeated','onCardPlayed','onCardMoved','onPhaseEnded','onDamageDealt'])eg.game.on(name,e=>{if(stopped)return;if(name==='onTokensCreated'&&e.tokenType==='mandalorian'){for(const card of e.generatedTokens??[]){if(!created.includes(card)){t['created'+created.length]=card;created.push(card);}}}events.push({name,card:id(eg,e.card),source:id(eg,e.context?.source),player:e.context?.player?eg.seatOf(e.context.player.id):null,generated:(e.generatedTokens??[]).map(x=>id(eg,x)),tokenType:e.tokenType??null,amount:e.amount??null,damage:e.damageDealt??null,created:created.map(x=>snap(eg,x)),sourceZone:e.context?.source?.zoneName??null});});},
beforeWindow(c){if(c.atWindow&&pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost,'Actual ordinary printed+aspect resource cost');payments.push({code:pendingPayment.code,id:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}if(c.atWindow&&created.length&&!initialGrant&&created[0].isInPlay()){initialGrant=created.map(x=>snap(c.eg,x));assert.ok(initialGrant[0].sentinel,'Resolved create result gained Sentinel before next action');assert.equal(initialGrant[0].shields.length,1,'Native Shielded produced physical Shield');}},
beforeApply(c){if(c.atWindow&&c.scratch.incoming&&c.chosen.cardUuid===c.scratch.incoming.uuid&&c.scratch.incoming.zoneName==='hand'){const card=c.scratch.incoming;pendingPayment={card,code:c.pending.code,actor:card.controller,before:card.controller.readyResourceCount,cost:payment(card)};if(c.pending.code===p.cardId)focus.push(card);}},
choose(c){const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';menus.push({title,actor:c.eg.seatOf(c.pid),created:created.map(x=>snap(c.eg,x)),actions:c.actions.map(a=>({arg:a.arg??null,label:a.label??null,card:a.cardUuid?c.eg.cardId(a.cardUuid):null}))});if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(title==='Choose a target for attack'){const cards=c.actions.filter(a=>a.cardUuid).map(a=>a.cardUuid);if(p.scenario==='ground-sentinel')assert.deepEqual(cards,[c.targets.created0.uuid],'Ground Sentinel is exact sole legal defender');if(p.scenario.startsWith('saboteur')){assert.ok(cards.includes(c.own.base.uuid),'Native Saboteur bypasses Sentinel');assert.ok(cards.includes(c.targets.created0.uuid));}if(p.scenario==='other-arena-negative'){assert.ok(cards.includes(c.own.base.uuid));assert.ok(cards.includes(c.targets.ownSpace.uuid));assert.ok(!cards.includes(c.targets.created0.uuid));}return c.actions.find(a=>a.cardUuid===c.targets[c.pending.target]?.uuid);}return undefined;},
assertAfter(c){if(pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost);payments.push({code:pendingPayment.code,id:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}const count=p.scenario==='repeated-events'||p.scenario==='departure-new-creation'?2:1;assert.equal(created.length,count);assert.equal(focus.length,count);assert.ok(focus.every(x=>x.zoneName==='discard'),'Real event source has left play area');assert.ok(payments.filter(x=>x.code==='ASH_091').every(x=>x.actual===5));if(c.targets.oldMando)assert.equal(c.targets.oldMando.hasSomeKeyword('sentinel'),false,'Existing same-title token never granted');for(const card of created)for(const u of card.isInPlay()?card.upgrades:[])assert.equal(u.hasSomeKeyword?.('sentinel')??false,false,'New Shield never substitutes for captured created unit');const current=created.map(x=>snap(c.eg,x));if(p.scenario==='framework-death-before-then'){assert.equal(current[0].zone,'outsideTheGame');assert.equal(current[0].shields.length,0);assert.equal(current[0].sentinel,true,'Captured physical retired token still receives phase Sentinel');assert.equal(events.filter(e=>e.name==='onEffectApplied'&&e.source===id(c.eg,focus[0])).length,1,'Continuation applies to exact retired generated token');}else if(p.scenario==='saboteur-shield-defeat'||p.scenario==='departure-new-creation'){assert.equal(current[0].zone,'outsideTheGame');assert.equal(current[0].sentinel,false);assert.equal(current[0].shields.length,0);if(count===2){assert.notEqual(created[0],created[1]);assert.equal(current[1].sentinel,true);assert.equal(current[1].shields.length,1);}}else if(p.scenario==='phase-expiry-no-attacks-terminal'){assert.ok(initialGrant?.[0].sentinel);assert.equal(current[0].sentinel,false,'Natural phase boundary removes Sentinel');assert.equal(current[0].shields.length,1);assert.equal(current[0].zone,'groundArena');}else {assert.ok(current.every(x=>x.sentinel));assert.equal(current[0].shields.length,p.scenario==='ground-sentinel'?0:1);assert.equal(current[0].damage,0);if(p.scenario==='saboteur-bypass-base')assert.equal(c.own.base.damage,4);}
assert.ok(created.every(card=>card.owner===c.own&&card.controller===c.own),'Generated physical token owner/controller are actual affected player');for(const [i,card]of created.entries()){const physical=id(c.eg,card),entry=events.findIndex(e=>e.name==='onUnitEntersPlay'&&e.card===physical),applied=events.findIndex(e=>e.name==='onEffectApplied'&&e.card===physical&&e.source===id(c.eg,focus[i]));assert.ok(entry>=0&&applied>entry,'Exact generated physical card is continuation target after entry');const shields=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='shield'&&e.card===physical);if(p.scenario==='framework-death-before-then'){const death=events.findIndex(e=>e.name==='onCardDefeated'&&e.card===physical);assert.ok(death>entry&&applied>death,'Actual framework defeat precedes continuation on retired token');assert.equal(shields.length,0,'Dead token gets no native Shield');}else{assert.equal(shields.length,1);assert.equal(shields[0].generated.length,1);assert.notEqual(shields[0].generated[0],physical);assert.ok(events.indexOf(shields[0])>applied,'Phase continuation precedes native Shielded Shield allocation');assert.equal(shields[0].created.find(x=>x.id===physical).sentinel,true,'Sentinel active by actual Shield creation');}}const creation=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='mandalorian');assert.equal(creation.length,count);assert.deepEqual(creation.flatMap(e=>e.generated),created.map(x=>id(c.eg,x)));c.observed={created:current,initialGrant,focusIds:focus.map(x=>id(c.eg,x)),oldMando:c.targets.oldMando?snap(c.eg,c.targets.oldMando):null,events,menus,payments,selectedCardIds:p.selectedCardIds,deckCardIds:p.deckCardIds,status:'source-only; native/Wasm unassessed'};stopped=true;c.targets.stopped=true;},
assertLater:p.scenario==='framework-death-before-then'?function(c){assert.equal(created[0].zoneName,undefined,'Retired token removed completely by native end-round cleanup');assert.ok(!created[0].owner.outsideTheGameZone.cards.includes(created[0]),'Native cleanup removes token from its zone (registry may retain historical object)');assert.equal(created[0].hasSomeKeyword('sentinel'),false,'Retired physical token phase keyword expires before next action phase');c.observed.retiredTokenPhaseExpiry=snap(c.eg,created[0]);}:undefined,
assertWitness(c){if(p.scenario==='phase-expiry-no-attacks-terminal'){assert.equal(created[0].zoneName,'groundArena');assert.equal(created[0].hasSomeKeyword('sentinel'),false);assert.equal(created[0].upgrades.length,1);c.observed.retainedAtTerminal=snap(c.eg,created[0]);}},
chooseLater(c){if(c.atWindow)return c.actions.find(a=>a.arg==='pass');const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');return c.actions.find(a=>a.arg==='passAbility')??c.actions.find(a=>a.arg==='noTarget')??c.actions.find(a=>a.arg==='all')??c.actions.find(a=>a.arg==='done');}};
let game;try{game=await tokenFixture(env,pool,ss,seed);}catch(e){e.diagnostic??={};e.diagnostic.sourceTimeline={events,menus,payments,created:created.map(x=>snap({cardId:u=>u},x))};throw e;}game.records[0].constructionParameters=structuredClone(p);game.records[0].fixtureConstruction='At initial action window use exact literal deckCardIds; stage declared real units and native token/Shield references, stage declared script handcards, move other initial handcards to resources and up to24 deckcards to ready resources. Existing token references are setup only. All BuyTime/Waylay plays, payments, native token entry/Shielded, attacks, phase transitions and subsequent terminal passes are actual engine choices; no later synthetic edits.';game.witness.coverageObligationIds=[...scenario.coverageObligationIds];return game;}
module.exports={fixture,validateProbe,validatePool,dependencies:['bots/omni/rs/inactive-phase-keyword-state.js', "lab/kessel-reference/pipeline/round-limit-interaction-fixture.js","lab/kessel-reference/pipeline/round-limit-probe-fixture.js","lab/kessel-reference/pipeline/probe-fixture.js","lab/kessel-reference/pipeline/terminal-completion.js","engine/env.js","engine/rng.js","engine/view.js","engine/stdio.js","engine/recorder.js","bots/omni/rs/state.js","bots/omni/rs/state-evidence.js","bots/omni/rs/unit-entry-state.js","bots/omni/rs/support-state.js","bots/omni/rs/round-limit-state.js","bots/omni/rs/pool.js","bots/players/index.js","bots/players/random.js","bots/players/rush.js","bots/players/heuristic.js","bots/players/profiles.js","bots/players/ismcts.js","bots/players/belief.js","bots/players/omniscient.js","bots/examples/random-bot.js","bots/examples/search-bot.js","bots/omni/search.js","bots/omni/evaluate.js","kessel:cards/pipeline/round-limit-probes.js","lab/kessel-reference/pipeline/created-token-phase-keyword-fixture.js","kessel:cards/pipeline/created-token-phase-keyword-probes.js"]};
