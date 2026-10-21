'use strict';
const assert=require('node:assert/strict'),same=require('node:util').isDeepStrictEqual;
const reviewedProbes=[
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "paid-single-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own"
      },
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_195",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "decline-none-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "split-a2-b4",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 2
          },
          {
            "target": "b",
            "amount": 4
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "reverse-b4-a2",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "b",
            "amount": 4
          },
          {
            "target": "a",
            "amount": 2
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "modified-xp-eight",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "IC27_184",
        "owner": "own",
        "target": "focus"
      },
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 8,
        "allocation": [
          {
            "target": "a",
            "amount": 3
          },
          {
            "target": "b",
            "amount": 5
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "IC27_184",
      "TWI_077",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_184",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "temporary-advantage-combat-nine",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceAdvantage",
        "tokenType": "advantage",
        "amount": 3,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "from": "focus",
        "target": "attacker"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 9,
        "allocation": [
          {
            "target": "a",
            "amount": 9
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "zero-power",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 6,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 0,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "negative-underlying-power-zero",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      },
      {
        "key": "hpUpgrade1",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 7,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 0,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "no-friendly-units",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "leader-recipient-attack-expiry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": true,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "SOR_014",
        "owner": "own",
        "from": "leader",
        "target": "enemyBase"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "leader",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "token-recipient-defense-expiry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
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
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "mando",
        "tokenType": "mandalorian",
        "amount": 1,
        "owner": "own",
        "zone": "ground",
        "exhausted": false,
        "attachments": [
          {
            "tokenType": "shield",
            "amount": 1
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "ASH_061",
        "owner": "enemy",
        "from": "attacker",
        "target": "mando"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "mando",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "opposing-combat-both-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "otherFocus",
        "code": "ASH_195",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "enemyA",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "from": "focus",
        "target": "otherFocus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 6
          }
        ]
      },
      {
        "sourceKey": "otherFocus",
        "owner": "enemy",
        "amount": 6,
        "allocation": [
          {
            "target": "enemyA",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "cross-arena-split",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_201",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 3
          },
          {
            "target": "b",
            "amount": 3
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_201",
      "TWI_077",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "unique-keep-incoming-eight",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceExperience",
        "tokenType": "experience",
        "amount": 2,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "uniqueDefeatKey": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 8,
        "allocation": [
          {
            "target": "incoming",
            "amount": 8
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "unique-keep-old-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceExperience",
        "tokenType": "experience",
        "amount": 2,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "uniqueDefeatKey": "incoming"
      }
    ],
    "distributions": [
      {
        "sourceKey": "incoming",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "focus",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "low-positive-one",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 5,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 1,
        "allocation": [
          {
            "target": "a",
            "amount": 1
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "paid-single-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own"
      },
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "SOR_095",
      "ASH_195",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "decline-none-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "split-a2-b4",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 2
          },
          {
            "target": "b",
            "amount": 4
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "reverse-b4-a2",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "b",
            "amount": 4
          },
          {
            "target": "a",
            "amount": 2
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "modified-xp-eight",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_061",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "IC27_184",
        "owner": "own",
        "target": "focus"
      },
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 8,
        "allocation": [
          {
            "target": "a",
            "amount": 3
          },
          {
            "target": "b",
            "amount": 5
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "IC27_184",
      "TWI_077",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_184",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "temporary-advantage-combat-nine",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "attacker",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceAdvantage",
        "tokenType": "advantage",
        "amount": 3,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "from": "focus",
        "target": "attacker"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 9,
        "allocation": [
          {
            "target": "a",
            "amount": 9
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "zero-power",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 6,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 0,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "negative-underlying-power-zero",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      },
      {
        "key": "hpUpgrade1",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 7,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 0,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "no-friendly-units",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": []
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "leader-recipient-attack-expiry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": true,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "SOR_014",
        "owner": "own",
        "from": "leader",
        "target": "enemyBase"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "leader",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "token-recipient-defense-expiry",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
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
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "mando",
        "tokenType": "mandalorian",
        "amount": 1,
        "owner": "own",
        "zone": "ground",
        "exhausted": false,
        "attachments": [
          {
            "tokenType": "shield",
            "amount": 1
          }
        ]
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "code": "ASH_061",
        "owner": "enemy",
        "from": "attacker",
        "target": "mando"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "mando",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "opposing-combat-both-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": false
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "otherFocus",
        "code": "ASH_195",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "enemyA",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "from": "focus",
        "target": "otherFocus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 6
          }
        ]
      },
      {
        "sourceKey": "otherFocus",
        "owner": "enemy",
        "amount": 6,
        "allocation": [
          {
            "target": "enemyA",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "cross-arena-split",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "b",
        "code": "ASH_201",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 3
          },
          {
            "target": "b",
            "amount": 3
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "ASH_201",
      "TWI_077",
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
      "HMW_174"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "unique-keep-incoming-eight",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceExperience",
        "tokenType": "experience",
        "amount": 2,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "uniqueDefeatKey": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 8,
        "allocation": [
          {
            "target": "incoming",
            "amount": 8
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "unique-keep-old-six",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [
      {
        "key": "sourceExperience",
        "tokenType": "experience",
        "amount": 2,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "ASH_195",
        "owner": "own",
        "uniqueDefeatKey": "incoming"
      }
    ],
    "distributions": [
      {
        "sourceKey": "incoming",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "focus",
            "amount": 6
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
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
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "TOKEN_ADVANTAGE",
      "TOKEN_EXPERIENCE"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "low-positive-one",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      }
    ],
    "handCards": [],
    "attachedUpgrades": [
      {
        "key": "hpUpgrade0",
        "code": "IC27_052",
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "sourceWeakness",
        "tokenType": "weakness",
        "amount": 5,
        "owner": "own",
        "attachTo": "focus"
      }
    ],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 1,
        "allocation": [
          {
            "target": "a",
            "amount": 1
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "SOR_095",
      "TWI_077",
      "IC27_052",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
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
      "IC27_052",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_WEAKNESS",
      "TWI_077"
    ]
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 0,
    "scenario": "sabine-collective-split",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "ASH_208",
        "owner": "own",
        "exhausted": true,
        "shields": 1
      },
      {
        "key": "b",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "enemyReady",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 2
          },
          {
            "target": "b",
            "amount": 4
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "ASH_208",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
      "ASH_201",
      "ASH_208",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_SHIELD",
      "TWI_077"
    ],
    "recipientTrigger": {
      "sourceKey": "a",
      "targetKey": "enemyReady",
      "expectedOptionalChoices": 1,
      "assertAllRecipientAttachmentsBeforeChoice": true
    }
  },
  {
    "family": "defeat-advantage-distribution",
    "cardId": "ASH_195",
    "owner": 1,
    "scenario": "sabine-collective-split",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "deployedLeader": false,
    "stagedUnits": [
      {
        "key": "focus",
        "code": "ASH_195",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "a",
        "code": "ASH_208",
        "owner": "own",
        "exhausted": true,
        "shields": 1
      },
      {
        "key": "b",
        "code": "SOR_095",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "enemyReady",
        "code": "ASH_061",
        "owner": "enemy",
        "exhausted": false
      }
    ],
    "handCards": [],
    "attachedUpgrades": [],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "TWI_077",
        "owner": "enemy",
        "target": "focus"
      }
    ],
    "distributions": [
      {
        "sourceKey": "focus",
        "owner": "own",
        "amount": 6,
        "allocation": [
          {
            "target": "a",
            "amount": 2
          },
          {
            "target": "b",
            "amount": 4
          }
        ]
      }
    ],
    "deckCardIds": [
      "ASH_195",
      "ASH_208",
      "SOR_095",
      "ASH_061",
      "TWI_077",
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
      "HMW_163"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_190",
      "ASH_195",
      "ASH_201",
      "ASH_208",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155",
      "HMW_163",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_ADVANTAGE",
      "TOKEN_SHIELD",
      "TWI_077"
    ],
    "recipientTrigger": {
      "sourceKey": "a",
      "targetKey": "enemyReady",
      "expectedOptionalChoices": 1,
      "assertAllRecipientAttachmentsBeforeChoice": true
    }
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
    "title": "Helgait",
    "subtitle": "Dooku Was a Visionary",
    "cost": 5,
    "hp": 4,
    "power": 6,
    "text": "When Defeated: You may distribute a number of Advantage tokens equal to this unit's power among friendly units (divided as you choose).",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": "Abilities that refer to a card’s power include temporary modifiers.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "9419144933",
    "aspects": [
      "cunning",
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
      "set": "ASH",
      "number": 195
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 195
      }
    ],
    "internalName": "helgait#dooku-was-a-visionary",
    "setCode": "ASH_195"
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
    "aspects": [],
    "cost": 0,
    "deployBox": null,
    "epicAction": "",
    "hp": 0,
    "id": "5844562972",
    "internalName": "advantage",
    "keywords": [],
    "power": 1,
    "rules": "When Attack Ends/When Defense Ends abilities trigger at the same time as units deal combat damage.\n",
    "setCode": "TOKEN_ADVANTAGE",
    "setId": {
      "set": "ASH"
    },
    "subtitle": "",
    "text": "When attached unit's attack or defense ends: Defeat this upgrade.",
    "title": "Advantage",
    "traits": [
      "innate"
    ],
    "types": [
      "token",
      "upgrade"
    ],
    "unique": false,
    "upgradeHp": 0,
    "upgradePower": 1
  },
  {
    "aspects": [
      "vigilance"
    ],
    "cost": 5,
    "deployBox": null,
    "epicAction": null,
    "hp": null,
    "id": "6472095064",
    "internalName": "vanquish",
    "keywords": [],
    "power": null,
    "rules": null,
    "setCode": "TWI_077",
    "setCodes": [
      {
        "number": 78,
        "set": "SOR"
      },
      {
        "number": 77,
        "set": "TWI"
      }
    ],
    "setId": {
      "number": 77,
      "set": "TWI"
    },
    "subtitle": null,
    "text": "Defeat a non-leader unit.",
    "title": "Vanquish",
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
    "aspects": [
      "villainy"
    ],
    "cost": 2,
    "deployBox": null,
    "epicAction": "",
    "hp": null,
    "id": "8621390428",
    "internalName": "consumed-by-the-dark-side",
    "keywords": [],
    "power": null,
    "rules": null,
    "setCode": "IC27_184",
    "setCodes": [
      {
        "number": 239,
        "set": "LOF"
      },
      {
        "number": 184,
        "set": "IC27"
      }
    ],
    "setId": {
      "number": 184,
      "set": "IC27"
    },
    "subtitle": "",
    "text": "Give 2 Experience tokens to a unit, then deal 2 damage to it.",
    "title": "Consumed by the Dark Side",
    "traits": [
      "force"
    ],
    "types": [
      "event"
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
    "hp": 1,
    "id": "2007868442",
    "internalName": "experience",
    "keywords": [],
    "power": 1,
    "rules": null,
    "setCode": "TOKEN_EXPERIENCE",
    "setId": {
      "set": "SOR"
    },
    "subtitle": null,
    "text": null,
    "title": "Experience",
    "traits": [
      "learned"
    ],
    "types": [
      "token",
      "upgrade"
    ],
    "unique": false,
    "upgradeHp": 1,
    "upgradePower": 1
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
    "aspects": [
      "vigilance"
    ],
    "cost": 1,
    "deployBox": null,
    "epicAction": null,
    "hp": 3,
    "id": "9059202647",
    "internalName": "resilient",
    "keywords": [],
    "power": 0,
    "rules": null,
    "setCode": "IC27_052",
    "setCodes": [
      {
        "number": 69,
        "set": "SOR"
      },
      {
        "number": 70,
        "set": "SHD"
      },
      {
        "number": 52,
        "set": "IC27"
      }
    ],
    "setId": {
      "number": 52,
      "set": "IC27"
    },
    "subtitle": null,
    "text": null,
    "title": "Resilient",
    "traits": [
      "innate"
    ],
    "types": [
      "upgrade"
    ],
    "unique": false,
    "upgradeHp": 3,
    "upgradePower": 0
  },
  {
    "aspects": [],
    "cost": 0,
    "deployBox": null,
    "epicAction": "",
    "hp": -1,
    "id": "7816991190",
    "internalName": "weakness",
    "keywords": [],
    "power": -1,
    "rules": null,
    "setCode": "TOKEN_WEAKNESS",
    "setId": {
      "set": "HMW"
    },
    "subtitle": "",
    "text": "",
    "title": "Weakness",
    "traits": [
      "condition"
    ],
    "types": [
      "token",
      "upgrade"
    ],
    "unique": false,
    "upgradeHp": -1,
    "upgradePower": -1
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
      "cunning",
      "heroism"
    ],
    "cost": 5,
    "deployBox": null,
    "epicAction": "",
    "hp": 5,
    "id": "6033198879",
    "internalName": "sabine-wren#i-learned-the-hard-way",
    "keywords": [
      "shielded"
    ],
    "power": 4,
    "rules": null,
    "setCode": "ASH_208",
    "setCodes": [
      {
        "number": 208,
        "set": "ASH"
      }
    ],
    "setId": {
      "number": 208,
      "set": "ASH"
    },
    "subtitle": "I Learned the Hard Way",
    "text": "Shielded (When you play this unit, give a Shield token to her.)\nWhen 1 or more upgrades attach to this unit (including from Shielded): You may exhaust a ground unit.",
    "title": "Sabine Wren",
    "traits": [
      "jedi",
      "mandalorian",
      "spectre"
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
// Token allocation preserves submitted Map order; damage retains the existing canonical grammar.
function canonicalSourceAction(eg,a){return require('../../../bots/omni/rs/state').canonicalAction(eg,a);}
function expandSourceActions(eg,actions,maxAllocations=100000){return require('../../../bots/omni/rs/state').expandActions(eg,actions,maxAllocations);}
const U=(key,code,owner='own',extra={})=>({key,code,owner,...extra});
const fillerCodes=['ASH_061','ASH_131','ASH_190','ASH_201','ASH_242','ASH_261','HMW_082','HMW_093','HMW_116','HMW_128','HMW_135','HMW_155','HMW_163','HMW_174','HMW_178','HMW_219','HMW_258'];
const matches = (c, code) => [c.cardData.setId, ...(c.cardData.setCodes ?? [])].some(s => s.set + '_' + String(s.number).padStart(3, '0') === code);
const arena = c => c.cardData.arena === 'space' ? 'spaceArena' : 'groundArena';
const plain = [];
function deckFor(pool, scenario) {
    const codes = [...new Set([...(scenario.units ?? plain).map((u) => u.code), ...scenario.plan.filter((s) => s.from !== 'leader'&&s.from !== 'enemyLeader').map((s) => s.code), ...(scenario.extraCodes ?? [])])];
    assert.ok(codes.length <= 17);
    for (const code of [...codes, scenario.leaderCode ?? 'SOR_014', scenario.baseCode ?? 'SOR_023'])
        assert.ok(pool.cards.some((c) => c.setCode === code), `Missing ${code} in oracle input pool`);
    const filler = scenario.fillerCodes.filter(code=>!codes.includes(code)).slice(0,17-codes.length);
    for(const code of filler)assert(pool.cards.some(c=>c.setCode===code&&c.types.includes('unit')&&!c.text),'Missing reviewed quiet filler '+code);
    assert.equal(filler.length, 17 - codes.length);
    return { metadata: { name: 'Event group oracle', author: 'omni-rs fixture' }, leader: { id: scenario.leaderCode ?? 'SOR_014', count: 1 }, base: { id: scenario.baseCode ?? 'SOR_023', count: 1 }, deck: [...codes, ...filler].map((id, i) => ({ id, count: i === 16 ? 2 : 3 })), isPresentInDb: false };
}
async function sourceTokenFixture(env, pool, scenario, seed) {
 const {seededRng}=require('../../../engine/env'),{fullState}=require('../../../bots/omni/rs/state'),{makeBot}=require('../../../bots/players'),{terminalCompletion}=require('./terminal-completion');
    const deck = deckFor(pool, scenario), eg = env.newGame({ selectionToggles: true, seed, deck1: deck, deck2: deck }), rng = seededRng('group-fixture-' + seed), bot = makeBot('random');
    require('../../../bots/omni/rs/inactive-phase-keyword-state').observeInactivePhaseKeywords(eg);
    if(Object.hasOwn(pool,'provenance'))require('../../../bots/omni/rs/direct-play-credit-state').bindNativePool(eg,pool);
    await eg.start();
    while (!eg.ids.some((pid) => eg.isActionWindow(pid))) {
        const pid = eg.ids.find((id) => eg.legalActions(id).length), actions = expandSourceActions(eg, eg.legalActions(pid));
        const initiativeChoice = scenario.initiative && actions.find(a => a.label === (pid === eg.ids[scenario.initiative === 'own' ? 0 : 1] ? 'Yourself' : 'Opponent'));
        eg.apply(pid, initiativeChoice ?? bot.choose({ game: eg, pid, actions, rng }), rng);
    }
    const own = eg.player(eg.ids[scenario.seat]), enemy = eg.player(eg.ids[1-scenario.seat]), targets = { ownBase: own.base, enemyBase: enemy.base };
    targets.leader = own.getAllDeckLeaders()[0];targets.enemyLeader=enemy.getAllDeckLeaders()[0];
    if (scenario.deployedLeader) {
        targets.leader.deploy({ type: 'leaderUnit' });
        targets.leader.deployEpicActionLimit.increment(own);
        targets.leader.exhausted = false;
    }
    const all = (p) => [...p.drawDeck, ...p.getCardsInZone('hand'), ...p.getCardsInZone('resource')];
    const take = (p, code) => { const c = all(p).find((c) => matches(c, code)); assert.ok(c, `No real ${code}`); return c; };
    for (const u of scenario.units ?? plain) {
        const p = u.owner === 'enemy' ? enemy : own, c = take(p, u.code);
        c.moveTo(arena(c));
        c.exhausted = !!u.exhausted;
        targets[u.key] = c;
        for (let i = 0; i < (u.shields ?? 0); i++)
            eg.game.generateToken(p, 'shield').attachTo(c);
    }
    for(const p of [own,enemy])for(const code of new Set(scenario.plan.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===p).map(s=>s.code))){
        const count=scenario.plan.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===p).length;
        while(p.getCardsInZone('hand').filter(c=>matches(c,code)).length<count){const card=all(p).find(c=>matches(c,code)&&c.zoneName!=='hand');assert(card,'Missing actual script '+code);card.moveTo('hand');}
    }
    for (const p of [own, enemy]) {
        for (const c of p.drawDeck.slice(0, 24)) {
            c.moveTo('resource');
            c.exhausted = false;
        }
        for (const c of p.getCardsInZone('resource'))
            c.exhausted = false;
        p.base.damage = scenario.baseDamage ?? (scenario.bothLethal ? p.base.cardData.hp - 1 : Math.min(24, p.base.cardData.hp - 6));
    }
    if (scenario.ownBaseUndamaged)
        own.base.damage = 0;
    if (scenario.emptyOwnHand) {
        for (const c of own.getCardsInZone('hand')) {
            c.moveTo('resource');
            c.exhausted = false;
        }
    }
    if (scenario.emptyOwnDeck) {
        for (const c of own.drawDeck.slice())
            c.moveTo('discard');
    }
    scenario.setup?.({eg,own,enemy,targets});
    eg.game.resolveGameState(true);
    for (const u of scenario.units ?? plain)
        if (u.damage)
            targets[u.key].damage = u.damage;
    eg.game.continue();
    for (const u of scenario.units ?? plain)
        if (u.shields) {
            assert.equal(targets[u.key].upgrades.length, u.shields);
            assert.ok(targets[u.key].damage < targets[u.key].getHp(), 'Constructed Shield unit must survive initial damage');
        }
    const completion = terminalCompletion(eg, 4000);
    const initialRound = eg.round, observed = {}, scratch = {}, initialState = fullState(eg), records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['scripted-group-fixture', 'scripted-group-fixture'], decks: [deck, deck], scenario: scenario.name,
            evidenceStatus: pool.oracleOnly ? 'PROTOTYPE engine observation; admission/conformance unassessed' : 'Engine observation; native/Wasm conformance unassessed', fixtureConstruction: (scenario.emptyOwnDeck ? 'Empty-deck scenario additionally moves all remaining p1 draw-deck cards into discard before initial state capture. ' : '') + (scenario.emptyOwnHand ? 'Empty-hand scenario additionally moves every initial p1 hand card into ready resources before initial state capture. ' : '') + 'At first natural action window, move specified real deck units into their printed arenas with specified exhaustion, move script cards into p1 hand, move12 remaining deck cards perplayer into ready resources, ready all resources, set bases damage24(orprintedHP-1 forbothLethal), resolve game state, then set disclosed survivingunitdamage and refreshprompts. Specified initial Shields are created with pinned game.generateToken and attached before state resolution. No later state edits.', constructionParameters: { emptyOwnDeck: !!scenario.emptyOwnDeck, emptyOwnHand: !!scenario.emptyOwnHand, units: scenario.units ?? plain, plan: scenario.plan, bothLethal: !!scenario.bothLethal, leaderCode: scenario.leaderCode, deployedLeader: !!scenario.deployedLeader, baseDamage: scenario.baseDamage, initiative: scenario.initiative } }];
    let step = 0, index = 0, pending = null, scriptObserved = false, laterObserved = false;
    try {
        while (true) {
            const pid = completion.nextActor(step);
            if (pid === null) break;
            const actions = expandSourceActions(eg, eg.legalActions(pid)), atWindow = eg.isActionWindow(pid), ctx = { eg, own, enemy, targets, actions, pid, atWindow, index, pending, step, observed, scratch, initialState };
            if (atWindow && scriptObserved && !laterObserved && eg.round > initialRound && scenario.assertLater) {
                scenario.assertLater(ctx);
                observed.laterRoundAssertion = true;
                laterObserved = true;
            }
            scenario.beforeWindow?.(ctx);
            if (atWindow) {
                records.push({ type: 'state', step, state: fullState(eg, pid) });
                if (!scriptObserved && index === scenario.plan.length && (!scenario.waitForRegroup || eg.round > initialRound)) {
                    scenario.assertAfter(ctx);
                    Object.assign(observed,ctx.observed);
                    observed.postAction = true;
                    scriptObserved = true;
                }
            }
            let chosen;
            if (!scriptObserved && atWindow) {
                if (pid === (scenario.plan[index]?.owner==='enemy'?enemy:own).id && index < scenario.plan.length && (!scenario.plan[index].nextRound || eg.round>initialRound)) {
                    pending = scenario.plan[index++];
                    ctx.pending = pending;
                    ctx.index = index;
                    const c = pending.from ? targets[pending.from] : (pending.owner==='enemy'?enemy:own).getCardsInZone('hand').find((c) => matches(c, pending.code));
                    assert.ok(c, `Missing script ${pending.code}`);
                    chosen = actions.find((a) => a.cardUuid === c.uuid);
                    assert.ok(chosen, `Illegal script ${pending.code}`);
                    scratch.incoming = c;
                }
                else
                    chosen = actions.find((a) => a.arg === 'pass');
            }
            else if (!atWindow && !scriptObserved) {
                chosen = scenario.choose?.(ctx);
                if (!chosen && pending?.target)
                    chosen = actions.find((a) => a.cardUuid === targets[pending.target]?.uuid);
                chosen ??= actions.find((a) => a.kind === 'button' && /trigger|resolve|play|deal|heal|give/i.test(a.label ?? '') && !/pass|cancel|no/i.test(a.label ?? ''));
            }
            if(scriptObserved&&scenario.assertLater&&!laterObserved)chosen??=atWindow?actions.find(a=>a.arg==='pass'):actions.find(a=>a.arg==='done');
            if(!scriptObserved && !atWindow)chosen ??= actions.find(a=>a.arg==='done');
            chosen ??= scenario.chooseLater?.(ctx);
            if(eg.over)chosen ??= actions.find(a=>a.label==='You') ?? actions.find(a=>a.arg==='all');
            chosen ??= actions.find(a=>/play anyway/i.test(a.label??''));
            const completionActions=targets.stopped?actions.filter(a=>{const card=a.cardUuid&&eg.game.allCards.find(c=>c.uuid===a.cardUuid);return !(card?.zoneName==='hand'&&card.cardData?.keywords?.includes('support'));}):actions;
            chosen ??= bot.choose({ game: eg, pid, actions:completionActions, rng });
            assert.ok(chosen);
            const prompt = eg.player(pid).currentPrompt();
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map((c) => eg.cardId(c.uuid)), actionWindow: atWindow }, actions: actions.map((a) => canonicalSourceAction(eg, a)), chosen: canonicalSourceAction(eg, chosen).key, events: [] });
            if (process.env.GROUP_FIXTURE_DEBUG && step < 35)
                console.error(JSON.stringify({ step, actor: eg.seatOf(pid), title: prompt.menuTitle, selected: (eg.player(pid).promptState.selectedCards ?? []).map(c => eg.cardId(c.uuid)), chosen: canonicalSourceAction(eg, chosen) }));
            scenario.beforeApply?.({ ...ctx, chosen });
            eg.apply(pid, chosen, rng);
            step++;
        }
        assert.ok(eg.over, 'Oracle game did not complete');
        assert.equal(index, scenario.plan.length, 'Script incomplete');
        if (!scriptObserved) {
            const finalContext={ eg, own, enemy, targets, observed, scratch, initialState };
            scenario.assertAfter(finalContext);
            Object.assign(observed,finalContext.observed);
            observed.postAction = true;
        }
        if (scenario.assertLater)
            assert.ok(laterObserved, 'Missing later-round assertion');
        scenario.assertWitness?.({ observed, scratch, records, eg, own, enemy, targets, initialState });
        observed.terminalCompletion = completion.assertComplete();
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        return { records, witness: { scenario: scenario.name, family: scenario.family, observed, decisions: step, winner: eg.winner } };
    }
    catch(e){e.diagnostic={records,observed};throw e;}
    finally {
        bot.close?.();
    }
}
function payment(card){const aspects=[...card.controller.getAspectsForCosts()];let n=card.cost;for(const a of card.cardData.aspects){const i=aspects.indexOf(a);if(i<0)n+=2;else aspects.splice(i,1);}return n;}
async function fixture(env,pool,scenario,seed){const p=scenario.probe;validateProbe(p);validatePool(pool,p);let stopped=false,pendingPayment=null,events=[],menus=[],payments=[],defeats=[],createdTokens=[],grantSnapshots=[],recipientPrompts=[],setupIds={},lastSeen={};const id=(eg,x)=>x?.uuid?eg.cardId(x.uuid):null,matches=(x,code)=>[x.cardData.setId,...(x.cardData.setCodes??[])].some(s=>s.set+'_'+String(s.number).padStart(3,'0')===code),isFocus=x=>x?.cardData?.id==='9419144933';const snap=(eg,x)=>x?{id:id(eg,x),zone:x.zoneName,power:x.isUnit?.()&&x.isInPlay()?x.getPower():null,hp:x.isUnit?.()&&x.isInPlay()?x.getHp():null,printedPower:x.cardData.power,controller:eg.seatOf(x.controller.id),upgrades:x.isUnit?.()&&x.isInPlay()?x.upgrades.map(u=>id(eg,u)):[]}:null;
const ss={name:scenario.name,family:p.family,seat:p.owner,leaderCode:p.leaderCode,baseCode:p.baseCode,deployedLeader:p.deployedLeader,fillerCodes:[],extraCodes:p.deckCardIds,units:p.stagedUnits,plan:p.scripts,baseDamage:0,
setup(c){const {eg,own,enemy,targets:t}=c,allocated=new Set(Object.values(t).filter(x=>x?.uuid).map(x=>x.uuid)),keep=new Set();for(const row of p.attachedUpgrades){const pl=row.owner==='enemy'?enemy:own,card=[...pl.drawDeck,...pl.getCardsInZone('hand'),...pl.getCardsInZone('resource')].find(x=>!allocated.has(x.uuid)&&matches(x,row.code));assert.ok(card);allocated.add(card.uuid);card.attachTo(t[row.attachTo]);t[row.key]=card;setupIds[row.key]=id(eg,card);}for(const row of p.nativeTokenRefs){const pl=row.owner==='enemy'?enemy:own;for(let i=0;i<row.amount;i++){const token=eg.game.generateToken(pl,row.tokenType);if(row.attachTo)token.attachTo(t[row.attachTo]);else{token.moveTo(row.zone+'Arena');token.exhausted=row.exhausted;for(const attachment of row.attachments??[])for(let j=0;j<attachment.amount;j++)eg.game.generateToken(pl,attachment.tokenType).attachTo(token);}if(i===0)t[row.key]=token;setupIds[row.key+i]=id(eg,token);}}for(const pl of [own,enemy])for(const code of new Set(p.scripts.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===pl).map(s=>s.code))){const count=p.scripts.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===pl).length;for(const card of pl.getCardsInZone('hand').filter(x=>matches(x,code)).slice(0,count))keep.add(card.uuid);}for(const pl of [own,enemy])for(const card of pl.getCardsInZone('hand').slice())if(!keep.has(card.uuid)){card.moveTo('resource');card.exhausted=false;}for(const row of p.stagedUnits)setupIds[row.key]=id(eg,t[row.key]);for(const name of ['onCardPlayed','onCardDefeated','onTokensCreated','onUpgradeAttached','distributeTokenUpgrade','onDamageDealt','onAttackEnd','onCardExhausted'])eg.game.on(name,e=>{if(stopped)return;const row={name,card:id(eg,e.card),source:id(eg,e.context?.source),actor:e.context?.player?eg.seatOf(e.context.player.id):null,player:e.player?eg.seatOf(e.player.id):null,parent:id(eg,e.parentCard),upgrade:id(eg,e.upgradeCard),amount:e.amount??null,totalDistributed:e.totalDistributed??null,tokenType:e.tokenType??null,generated:(e.generatedTokens??[]).map(x=>id(eg,x)),lkiPower:e.lastKnownInformation?.power??null,lkiController:e.lastKnownInformation?.controller?eg.seatOf(e.lastKnownInformation.controller.id):null,defeatType:e.defeatSource?.type??null,sourceZone:e.context?.source?.zoneName??null};if(name==='onCardDefeated'&&isFocus(e.card)){defeats.push({source:e.card,id:id(eg,e.card),power:e.lastKnownInformation.power,printedPower:e.card.cardData.power,eventActor:row.actor,lkiController:row.lkiController,defeatType:row.defeatType,controller:eg.seatOf(e.card.controller.id),preDeath:lastSeen[e.card.uuid]??null});}if(name==='onTokensCreated'&&e.tokenType==='advantage'&&isFocus(e.context?.source))for(const token of e.generatedTokens){createdTokens.push(token);}events.push(row);});},
beforeWindow(c){if(c.atWindow&&pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost,'Ordinary actual payment');payments.push({code:pendingPayment.code,card:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}for(const key of ['focus','incoming','otherFocus']){const card=c.targets[key];if(card?.isInPlay())lastSeen[card.uuid]=snap(c.eg,card);}if(c.atWindow&&createdTokens.length&&createdTokens.every(x=>x.isAttached?.())){const signature=createdTokens.map(x=>id(c.eg,x)).join(',');if(!grantSnapshots.some(x=>x.signature===signature))grantSnapshots.push({signature,targets:Object.fromEntries([...new Set(p.distributions.flatMap(d=>d.allocation.map(a=>a.target)))].map(k=>[k,snap(c.eg,c.targets[k])])),tokens:createdTokens.map(x=>({id:id(c.eg,x),parent:id(c.eg,x.parentCard),owner:c.eg.seatOf(x.owner.id)}))});}},
beforeApply(c){if(c.atWindow&&c.scratch.incoming&&c.chosen.cardUuid===c.scratch.incoming.uuid&&c.scratch.incoming.zoneName==='hand'){const card=c.scratch.incoming;pendingPayment={card,code:c.pending.code,actor:card.controller,before:card.controller.readyResourceCount,cost:payment(card)};if(c.pending.code===p.cardId){if(c.targets.focus)c.targets.incoming=card;else c.targets.focus=card;}}},
choose(c){const prompt=c.eg.player(c.pid).currentPrompt(),title=prompt.menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(title.startsWith('Choose which copy of Helgait')){const card=c.targets[c.pending.uniqueDefeatKey];assert.ok(card);return c.actions.find(a=>a.cardUuid===card.uuid);}if(title==='Choose a target for attack')return c.actions.find(a=>a.cardUuid===c.targets[c.pending.target]?.uuid);if(p.recipientTrigger&&title==='You may trigger this ability')assert.fail('Unexpected separate optional popup; source integrates Pass into target resolver');if(p.recipientTrigger&&title==='Exhaust a ground unit'){assert.equal(c.pid,c.own.id);const recipient=c.targets[p.recipientTrigger.sourceKey],other=c.targets.b;assert.equal(recipient.upgrades.filter(t=>t.cardData.internalName==='advantage').length,2);assert.equal(other.upgrades.filter(t=>t.cardData.internalName==='advantage').length,4,'Other recipient already has all4 before Sabine choice: one shared attachment window');assert.equal(other.getPower(),7);assert.ok(c.actions.some(a=>a.arg==='passAbility'),'Actual optional decline is integrated in target menu');recipientPrompts.push({title,actor:c.eg.seatOf(c.pid),recipient:snap(c.eg,recipient),other:snap(c.eg,other),allCreatedTokenIds:createdTokens.map(t=>id(c.eg,t)),actions:c.actions.map(a=>canonicalSourceAction(c.eg,a))});const action=c.actions.find(a=>a.cardUuid===c.targets[p.recipientTrigger.targetKey].uuid);assert.ok(action);return action;}if(prompt.distributeAmongTargets?.type==='distributeTokenUpgrade'){const side=c.pid===c.own.id?'own':'enemy',d=p.distributions.find(d=>d.owner===side);assert.ok(d,'Declared captured-source/player distribution');assert.equal(prompt.distributeAmongTargets.amount,d.amount);assert.equal(prompt.distributeAmongTargets.canChooseNoTargets,true);assert.equal(prompt.distributeAmongTargets.canDistributeLess,false);const first=c.actions[0];assert.ok(c.actions.every(a=>a.kind==='distribute'),'Mandatory distribution, no optional popup or cancel action');const legal=c.eg.player(c.pid).getArenaUnits().filter(x=>!x.pendingDefeat).map(x=>x.uuid).sort();assert.deepEqual([...first.targets].sort(),legal,'Every friendly inplay unit, any arena/leader/token, no enemy/base/dead source');assert.ok(c.actions.some(a=>a.split.length===0),'Actual empty allocation remains legal even with one target');assert.ok(c.actions.every(a=>!a.split.length||a.split.reduce((n,x)=>n+x.amount,0)===d.amount),'Every nonempty action distributes full amount');const wanted=d.allocation.map(a=>({id:c.targets[a.target].uuid,amount:a.amount})),chosen=c.actions.find(a=>same(a.split,wanted));assert.ok(chosen,'Exact submitted allocation and insertion order are legal');menus.push({title,actor:c.eg.seatOf(c.pid),amount:d.amount,sourceKey:d.sourceKey,sourceZone:c.targets[d.sourceKey].zoneName,sourcePrintedPower:c.targets[d.sourceKey].cardData.power,legalTargets:first.targets.map(u=>c.eg.cardId(u)),actionCount:c.actions.length,chosen:canonicalSourceAction(c.eg,chosen),spec:structuredClone(prompt.distributeAmongTargets)});return chosen;}return undefined;},
assertAfter(c){if(pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost);payments.push({code:pendingPayment.code,card:id(c.eg,pendingPayment.card),actual});pendingPayment=null;}assert.equal(defeats.length,p.distributions.length);let expectedTokens=0;const allocationEvidence=[];for(const d of p.distributions){const source=c.targets[d.sourceKey],sourceId=id(c.eg,source),death=defeats.find(x=>x.source===source);assert.ok(death,'Exact physical defeated source captured');assert.equal(source.zoneName,'discard');assert.equal(death.power,d.amount,'Amount from defeated source LKI, never printed/current source');assert.equal(death.printedPower,6);const actual=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='advantage'&&e.source===sourceId),meta=events.filter(e=>e.name==='distributeTokenUpgrade'&&e.source===sourceId);assert.equal(actual.length,d.allocation.length,'One original creation event per positive recipient, not one batched event');assert.deepEqual(actual.map(e=>e.card),d.allocation.map(a=>id(c.eg,c.targets[a.target])).reverse(),'Pinned negative-order sibling creation emit order reverses submitted recipient order');assert.equal(death.lkiController,c.eg.seatOf((d.owner==='enemy'?c.enemy:c.own).id));assert.equal(meta.length,d.amount===0||p.scenario==='no-friendly-units'?0:1);if(meta.length){assert.equal(meta[0].totalDistributed,d.allocation.reduce((n,a)=>n+a.amount,0));assert.equal(meta[0].card,sourceId,'Meta event keeps defeated source as default target even though actual recipients are separate');}const ordered=[];for(const a of d.allocation){const targetId=id(c.eg,c.targets[a.target]),e=actual.find(x=>x.card===targetId);assert.ok(e);assert.equal(e.amount,a.amount);assert.equal(e.generated.length,a.amount);assert.equal(e.actor,c.eg.seatOf((d.owner==='enemy'?c.enemy:c.own).id));ordered.push(...e.generated);expectedTokens+=a.amount;}assert.deepEqual([...ordered].sort((a,b)=>Number(a.slice(1))-Number(b.slice(1))),ordered,'Physical token registry allocation follows submitted Map recipient order');const attached=events.filter(e=>e.name==='onUpgradeAttached'&&ordered.includes(e.upgrade));assert.deepEqual(attached.map(e=>e.upgrade),ordered,'Contingent attachment order follows generated physical token order');if(attached.length){const metaIndex=events.indexOf(meta[0]);assert.ok(actual.every(e=>events.indexOf(e)<metaIndex),'All perrecipient original creation emits precede meta');assert.ok(attached.every(e=>events.indexOf(e)>metaIndex),'Order-zero attachment contingents emit after meta');}allocationEvidence.push({source:sourceId,lkiPower:death.power,orderedGenerated:ordered,creationEmitterRecipientOrder:actual.map(e=>e.card),attachmentOrder:attached.map(e=>e.upgrade)});if(d.amount===0||p.scenario==='no-friendly-units')assert.equal(menus.filter(m=>m.sourceKey===d.sourceKey).length,0);}assert.equal(createdTokens.length,expectedTokens);if(expectedTokens)assert.ok(grantSnapshots.length,'Physical token attachment snapshot before any later attack/defense');assert.ok(createdTokens.every(t=>t.owner===t.controller));if(p.scenario==='paid-single-six'||p.scenario.startsWith('unique-'))assert.equal(payments.find(x=>x.code===p.cardId).actual,9,'Printed5 +missing cunning/villainy2each');if(p.scenario==='modified-xp-eight'){const xp=events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='experience');assert.equal(xp.length,1);assert.equal(xp[0].generated.length,2);assert.ok(xp[0].generated.every(u=>events.some(e=>e.name==='onCardDefeated'&&e.card===u)),'Actual XP tokens removed with source, while captured distribution remains8');assert.equal(p.distributions[0].amount,8);}if(p.scenario==='negative-underlying-power-zero'||p.scenario==='zero-power'||p.scenario==='low-positive-one'){const death=defeats[0];assert.equal(death.preDeath.power,p.distributions[0].amount);assert.ok(death.preDeath.hp>0);}
if(p.scenario==='leader-recipient-attack-expiry'||p.scenario==='token-recipient-defense-expiry'){assert.ok(createdTokens.every(t=>t.zoneName==='outsideTheGame'),'Native Advantage expires on actual recipient attack/defense end');if(p.scenario==='leader-recipient-attack-expiry'){assert.equal(c.enemy.base.damage,9,'Leader printed2 +6Advantage combat and native OnAttack1');assert.equal(c.targets.leader.getPower(),2);}else{assert.equal(c.targets.mando.getPower(),2);assert.equal(c.targets.mando.upgrades.length,0,'Physical Shield prevents incoming damage and is defeated; Advantage expires');assert.equal(c.targets.mando.damage,0);assert.equal(c.targets.attacker.zoneName,'discard');}}else assert.ok(createdTokens.every(t=>t.isAttached()),'Every created token physically attached');if(p.recipientTrigger){assert.equal(recipientPrompts.length,1,'Collective Sabine optional fires once for2 attachments in same eventwindow');assert.equal(c.targets[p.recipientTrigger.targetKey].exhausted,true);const exhausts=events.filter(e=>e.name==='onCardExhausted'&&e.source===id(c.eg,c.targets[p.recipientTrigger.sourceKey])&&e.card===id(c.eg,c.targets[p.recipientTrigger.targetKey]));assert.equal(exhausts.length,1,'Actual Sabine ability exhausts exact enemy physical ground unit');}c.observed={recipientPrompts,defeatedSources:defeats.map(({source,...d})=>d),events,menus,payments,setupIds,grantSnapshots,allocationEvidence,createdTokens:createdTokens.map(t=>({id:id(c.eg,t),zone:t.zoneName,owner:c.eg.seatOf(t.owner.id),parent:t.isAttached?.()?id(c.eg,t.parentCard):null})),selectedCardIds:p.selectedCardIds,deckCardIds:p.deckCardIds,sourceOnlyActionGrammar:'Token ordered positive full allocations+empty; local complete action enumeration, no native import claim',status:'source-only; zero native/Wasm admission/conformance credit'};stopped=true;c.targets.stopped=true;},
chooseLater(c){if(c.atWindow)return c.actions.find(a=>a.arg==='pass');const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');return c.actions.find(a=>a.arg==='all')??c.actions.find(a=>a.arg==='passAbility')??c.actions.find(a=>a.arg==='pass')??c.actions.find(a=>a.arg==='noTarget')??c.actions.find(a=>a.arg==='done');}};
let game;try{game=await sourceTokenFixture(env,pool,ss,seed);}catch(e){e.diagnostic??={};e.diagnostic.sourceTimeline={events,menus,payments,grantSnapshots,recipientPrompts,defeatedSources:defeats.map(({source,...d})=>d)};throw e;}game.records[0].constructionParameters=structuredClone(p);game.records[0].fixtureConstruction='Exact literal17-card deck, declared arena units, deployed leader/native tokens/ordinary attached upgrades and script handcards staged once at initial actionwindow; up to24 deckcards and other initial handcards to ready resources. Staged token/upgrade/leader setup makes no paid-entry claim. Actual subsequent plays/payments/attacks/uniqueness choices/defeats/ordered token allocations/native Advantage expiry thereafter; no later state edits. Quiet actual passes/resourcing complete the game. Token action enumeration is a local source protocol, shared exporter/native admission pending.';game.witness.coverageObligationIds=[...scenario.coverageObligationIds];return game;}

module.exports={fixture,validateProbe,validatePool,canonicalSourceAction,expandSourceActions,dependencies:['bots/omni/rs/player-phase-state.js', 'bots/omni/rs/direct-play-credit-state.js', 'bots/omni/rs/inactive-phase-keyword-state.js', "lab/kessel-reference/pipeline/round-limit-interaction-fixture.js","lab/kessel-reference/pipeline/round-limit-probe-fixture.js","lab/kessel-reference/pipeline/probe-fixture.js","lab/kessel-reference/pipeline/terminal-completion.js","engine/env.js","engine/rng.js","engine/view.js","engine/stdio.js","engine/recorder.js","bots/omni/rs/state.js","bots/omni/rs/state-evidence.js","bots/omni/rs/unit-entry-state.js","bots/omni/rs/support-state.js","bots/omni/rs/round-limit-state.js","bots/omni/rs/pool.js","bots/players/index.js","bots/players/random.js","bots/players/rush.js","bots/players/heuristic.js","bots/players/profiles.js","bots/players/ismcts.js","bots/players/belief.js","bots/players/omniscient.js","bots/examples/random-bot.js","bots/examples/search-bot.js","bots/omni/search.js","bots/omni/evaluate.js","kessel:cards/pipeline/round-limit-probes.js","lab/kessel-reference/pipeline/defeat-advantage-distribution-fixture.js","kessel:cards/pipeline/defeat-advantage-distribution-probes.js"]};
