'use strict';
const assert=require('node:assert/strict'),same=require('node:util').isDeepStrictEqual;
const reviewedProbes=[
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "higher-enemy",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "higher-own",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "no-higher",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_131",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 0,
      "damageTarget": null,
      "handCost": 6,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "no-unit-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 0,
      "damage": 0,
      "damageTarget": null,
      "handCost": null,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "empty-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_061",
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
      "ASH_131",
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 0,
      "damage": 0,
      "damageTarget": null,
      "handCost": null,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 0,
    "mode": "discard-higher",
    "scenario": "selection-domains",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "other",
        "code": "ASH_131",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "higher-enemy",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "higher-own",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "no-higher",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_131",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 0,
      "damageTarget": null,
      "handCost": 6,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "no-unit-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 0,
      "damage": 0,
      "damageTarget": null,
      "handCost": null,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "empty-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [],
    "scripts": [
      {
        "code": "ASH_163",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_061",
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
      "ASH_131",
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 0,
      "damage": 0,
      "damageTarget": null,
      "handCost": null,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_163",
    "owner": 1,
    "mode": "discard-higher",
    "scenario": "selection-domains",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equal",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "other",
        "code": "ASH_131",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_163",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "higher"
      }
    ],
    "deckCardIds": [
      "ASH_131",
      "IBH_007",
      "ASH_201",
      "ASH_163",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_163",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 2,
      "discardCount": 1,
      "damage": 5,
      "damageTarget": "higher",
      "handCost": 2,
      "sourceZoneAfter": "discard"
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "paid-wp-enemy-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "paid-wp-own-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalOwn"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "wp-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "wp-no-unit-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "TWI_174",
      "ASH_061",
      "ASH_190",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": null,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "wp-no-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "HMW_174",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "HMW_174",
      "TWI_174",
      "ASH_061",
      "ASH_190",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_132",
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
      "HMW_174",
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 0,
      "handCost": 4,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "on-attack-repeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "target": "enemyBase",
        "nextRound": true,
        "handTarget": "chosen",
        "damageTarget": "second"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 2,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "reentry-hooks",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "nextRound": true,
        "handTarget": "chosen",
        "damageTarget": "second"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "TWI_226",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174",
      "TWI_226"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 2,
      "revealCount": 2,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "on-attack-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "target": "enemyBase",
        "nextRound": true,
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 0,
    "mode": "reveal-equal",
    "scenario": "revealed-card-paid",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "from": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": false
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "paid-wp-enemy-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "paid-wp-own-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalOwn"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "wp-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "wp-no-unit-hand",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "TWI_174",
      "ASH_061",
      "ASH_190",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": null,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "wp-no-equal",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "HMW_174",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "HMW_174",
      "TWI_174",
      "ASH_061",
      "ASH_190",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_132",
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
      "HMW_174",
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 0,
      "handCost": 4,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "on-attack-repeat",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "target": "enemyBase",
        "nextRound": true,
        "handTarget": "chosen",
        "damageTarget": "second"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 2,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "reentry-hooks",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "code": "TWI_226",
        "owner": "enemy",
        "target": "focus"
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "nextRound": true,
        "handTarget": "chosen",
        "damageTarget": "second"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "TWI_226",
      "ASH_190",
      "TWI_174",
      "ASH_061",
      "ASH_242",
      "ASH_261",
      "HMW_082",
      "HMW_093",
      "HMW_116",
      "HMW_128",
      "HMW_135",
      "HMW_155"
    ],
    "selectedCardIds": [
      "ASH_061",
      "ASH_131",
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174",
      "TWI_226"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 2,
      "revealCount": 2,
      "damage": 3,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "on-attack-decline",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": null,
        "damageTarget": null
      },
      {
        "from": "focus",
        "code": "ASH_132",
        "owner": "own",
        "target": "enemyBase",
        "nextRound": true,
        "handTarget": null,
        "damageTarget": null
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 0,
      "damage": 0,
      "handCost": 2,
      "retainedHand": true
    }
  },
  {
    "family": "captured-hand-cost",
    "cardId": "ASH_132",
    "owner": 1,
    "mode": "reveal-equal",
    "scenario": "revealed-card-paid",
    "resourceCount": 24,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "stagedUnits": [
      {
        "key": "equalEnemy",
        "code": "IBH_007",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "equalOwn",
        "code": "IBH_007",
        "owner": "own",
        "exhausted": true
      },
      {
        "key": "second",
        "code": "SOR_095",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "lower",
        "code": "ASH_201",
        "owner": "enemy",
        "exhausted": true
      },
      {
        "key": "higher",
        "code": "ASH_131",
        "owner": "enemy",
        "exhausted": true
      }
    ],
    "handCards": [
      {
        "key": "chosen",
        "code": "ASH_190",
        "owner": "own"
      },
      {
        "key": "nonunit",
        "code": "TWI_174",
        "owner": "own"
      },
      {
        "key": "foreignHand",
        "code": "ASH_131",
        "owner": "enemy"
      }
    ],
    "nativeTokenRefs": [
      {
        "key": "noCost",
        "tokenType": "mandalorian",
        "owner": "enemy",
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
        "code": "ASH_132",
        "owner": "own",
        "handTarget": "chosen",
        "damageTarget": "equalEnemy"
      },
      {
        "from": "chosen",
        "code": "ASH_190",
        "owner": "own"
      }
    ],
    "deckCardIds": [
      "IBH_007",
      "SOR_095",
      "ASH_201",
      "ASH_131",
      "ASH_132",
      "ASH_190",
      "TWI_174",
      "ASH_061",
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
      "ASH_132",
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
      "IBH_007",
      "SOR_014",
      "SOR_023",
      "SOR_095",
      "TOKEN_MANDALORIAN",
      "TOKEN_SHIELD",
      "TWI_174"
    ],
    "expect": {
      "focusPaid": 6,
      "focusPlayCount": 1,
      "revealCount": 1,
      "damage": 3,
      "handCost": 2,
      "retainedHand": false
    }
  }
];
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
    "title": "Reckless Sacrifice",
    "subtitle": "",
    "cost": 2,
    "hp": null,
    "power": null,
    "text": "Discard a unit from your hand. Deal 5 damage to a unit that costs more than the discarded card.",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": "Abilities that refer to a card’s cost always refer to its printed cost, regardless of modifiers.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "8814113279",
    "aspects": [
      "aggression",
      "heroism"
    ],
    "traits": [
      "gambit"
    ],
    "keywords": [],
    "types": [
      "event"
    ],
    "setId": {
      "set": "ASH",
      "number": 163
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 163
      }
    ],
    "internalName": "reckless-sacrifice",
    "setCode": "ASH_163"
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
    "title": "Echo Coordinator",
    "subtitle": "",
    "cost": 2,
    "hp": 5,
    "power": 1,
    "text": "",
    "deployBox": null,
    "epicAction": "",
    "unique": false,
    "rules": null,
    "upgradePower": null,
    "upgradeHp": null,
    "id": "8073149642",
    "aspects": [
      "command",
      "heroism"
    ],
    "traits": [
      "rebel"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "IBH",
      "number": 7
    },
    "setCodes": [
      {
        "set": "IBH",
        "number": 7
      },
      {
        "set": "IBH",
        "number": 43
      },
      {
        "set": "IBH",
        "number": 47
      }
    ],
    "internalName": "echo-coordinator",
    "setCode": "IBH_007"
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
    "title": "Queen Soruna",
    "subtitle": "Willing to Fight",
    "cost": 6,
    "hp": 7,
    "power": 5,
    "text": "When Played/On Attack: You may reveal a unit from your hand. If you do, deal 3 damage to a unit with the same cost as the revealed unit.",
    "deployBox": null,
    "epicAction": "",
    "unique": true,
    "rules": "Abilities that refer to a card’s cost always refer to its printed cost, regardless of modifiers.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "2299349302",
    "aspects": [
      "command"
    ],
    "traits": [
      "naboo",
      "official"
    ],
    "arena": "ground",
    "keywords": [],
    "types": [
      "unit"
    ],
    "setId": {
      "set": "ASH",
      "number": 132
    },
    "setCodes": [
      {
        "set": "ASH",
        "number": 132
      }
    ],
    "internalName": "queen-soruna#willing-to-fight",
    "setCode": "ASH_132"
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
    "title": "Waylay",
    "subtitle": null,
    "cost": 3,
    "hp": null,
    "power": null,
    "text": "Return a non-leader unit to its owner's hand.",
    "deployBox": null,
    "epicAction": null,
    "unique": false,
    "rules": "Abilities that return a card to hand must choose a card in play unless otherwise specified.\n",
    "upgradePower": null,
    "upgradeHp": null,
    "id": "7202133736",
    "aspects": [
      "cunning"
    ],
    "traits": [
      "trick"
    ],
    "keywords": [],
    "types": [
      "event"
    ],
    "setId": {
      "set": "TWI",
      "number": 226
    },
    "setCodes": [
      {
        "set": "SOR",
        "number": 222
      },
      {
        "set": "TWI",
        "number": 226
      }
    ],
    "internalName": "waylay",
    "setCode": "TWI_226"
  }
];
function validateProbe(p){assert.ok(reviewedProbes.some(q=>same(p,q)),'Complete closed source construction probe required');}
function validatePool(pool,p){for(const id of p.selectedCardIds){const rows=pool.cards.filter(e=>e.setCode===id);assert.equal(rows.length,1,'One selected full definition '+id);assert.ok(same(rows[0],reviewedPoolDefinitions.find(e=>e.setCode===id)),'Complete selected definition '+id);}}

function printedPayment(card){const aspects=[...card.controller.getAspectsForCosts()];let n=card.cost;for(const a of card.cardData.aspects){const i=aspects.indexOf(a);if(i<0)n+=2;else aspects.splice(i,1);}return n;}
async function fixture(env,pool,scenario,seed){const p=scenario.probe;validateProbe(p);validatePool(pool,p);const {sourceHarness:{tokenFixture}}=require('./round-limit-probe-fixture');let focus=null,events=[],menus=[],payments=[],acks=[],declines=[],pendingPayment=null,stopped=false,retainedBeforePay=false;const setupIds={};
const ss={name:scenario.name,family:p.family,seat:p.owner,leaderCode:p.leaderCode,baseCode:p.baseCode,fillerCodes:[],extraCodes:p.deckCardIds,units:p.stagedUnits,plan:p.scripts,baseDamage:0,
setup(c){const {eg,own,enemy,targets:t}=c,id=x=>eg.cardId(x.uuid),allocated=new Set(Object.values(t).filter(x=>x?.uuid).map(x=>x.uuid));const matches=(x,code)=>[x.cardData.setId,...(x.cardData.setCodes??[])].some(s=>s.set+'_'+String(s.number).padStart(3,'0')===code);const find=(pl,code)=>[...pl.drawDeck,...pl.getCardsInZone('hand'),...pl.getCardsInZone('resource')].find(x=>!allocated.has(x.uuid)&&matches(x,code));for(const row of p.handCards){const pl=row.owner==='enemy'?enemy:own,card=find(pl,row.code);assert.ok(card,'Declared physical hand card '+row.key);allocated.add(card.uuid);card.moveTo('hand');t[row.key]=card;setupIds[row.key]=id(card);}const keep=new Set(p.handCards.map(row=>t[row.key].uuid));for(const pl of [own,enemy])for(const code of new Set(p.scripts.filter(s=>!s.from&&(s.owner==='enemy'?enemy:own)===pl).map(s=>s.code))){const count=p.scripts.filter(s=>!s.from&&s.code===code&&(s.owner==='enemy'?enemy:own)===pl).length;const cards=pl.getCardsInZone('hand').filter(x=>!keep.has(x.uuid)&&matches(x,code)).slice(0,count);assert.equal(cards.length,count);for(const x of cards)keep.add(x.uuid);}for(const pl of [own,enemy])for(const card of pl.getCardsInZone('hand').slice())if(!keep.has(card.uuid)){card.moveTo('resource');card.exhausted=false;}for(const row of p.nativeTokenRefs){const pl=row.owner==='enemy'?enemy:own,card=eg.game.generateToken(pl,row.tokenType);card.moveTo(row.zone+'Arena');card.exhausted=row.exhausted;for(const a of row.attachments)eg.game.generateToken(pl,a.tokenType).attachTo(card);t[row.key]=card;setupIds[row.key]=id(card);}for(const row of p.stagedUnits)setupIds[row.key]=id(t[row.key]);for(const name of ['onCardPlayed','onCardDiscarded','onCardsDiscardedFromHand','onCardRevealed','onDamageDealt','onCardDefeated','onCardMoved'])eg.game.on(name,e=>{if(stopped)return;events.push({name,step:eg._handCostStep??null,card:e.card?.uuid?id(e.card):null,cards:(e.cards??[]).filter(x=>x?.uuid).map(id),source:e.context?.source?.uuid?id(e.context.source):null,player:e.context?.player?eg.seatOf(e.context.player.id):null,cardZone:e.card?.zoneName??null,printedCost:e.card?.printedCost??null,amount:e.damageDealt??null,type:e.damageSource?.type??null,from:e.discardedFromZone??e.revealedFromZone??null});});},
beforeWindow(c){c.eg._handCostStep=c.step;if(c.atWindow&&pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost,'Ordinary paid card cost');payments.push({code:pendingPayment.code,card:c.eg.cardId(pendingPayment.card.uuid),actual,actor:c.eg.seatOf(pendingPayment.actor.id)});pendingPayment=null;}},
beforeApply(c){if(c.atWindow&&c.scratch.incoming&&c.chosen.cardUuid===c.scratch.incoming.uuid&&c.scratch.incoming.zoneName==='hand'){const card=c.scratch.incoming;pendingPayment={card,code:c.pending.code,actor:card.controller,before:card.controller.readyResourceCount,cost:printedPayment(card)};if(c.pending.code===p.cardId){focus??=card;assert.equal(card,focus,'Reentry retains exact physical source');c.targets.focus=focus;}if(p.scenario==='revealed-card-paid'&&card===c.targets.chosen){assert.equal(card.zoneName,'hand');assert.ok(events.some(e=>e.name==='onCardRevealed'&&e.cards.includes(c.eg.cardId(card.uuid))));retainedBeforePay=true;}}},
choose(c){const prompt=c.eg.player(c.pid).currentPrompt(),title=prompt.menuTitle??'',id=x=>c.eg.cardId(x.uuid);menus.push({step:c.step,title,actor:c.eg.seatOf(c.pid),actions:c.actions.map(a=>({arg:a.arg??null,label:a.label??null,card:a.cardUuid?c.eg.cardId(a.cardUuid):null})),displayCards:(prompt.displayCards??[]).map(x=>x.cardUuid?c.eg.cardId(x.cardUuid):x.uuid?c.eg.cardId(x.uuid):null)});if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(/View cards for .*Queen Soruna.*ability/i.test(title)){assert.equal(c.pid,c.enemy.id,'Actual opponent acknowledges reveal display');assert.deepEqual((prompt.displayCards??[]).map(x=>c.eg.cardId(x.cardUuid)),[id(c.targets.chosen)],'Opponent display contains exact revealed physical hand card');const a=c.actions.find(a=>a.arg==='done');assert.ok(a);acks.push({step:c.step,actor:c.eg.seatOf(c.pid),handId:id(c.targets.chosen),zone:c.targets.chosen.zoneName});return a;}if(title==='Choose a target for attack')return c.actions.find(a=>a.cardUuid===c.enemy.base.uuid);if(/discard for Reckless Sacrifice/i.test(title)){assert.equal(c.pid,c.own.id);assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.foreignHand?.uuid),'Other controller hand excluded');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.nonunit?.uuid),'Nonunit excluded from discard effect');assert.ok(!c.actions.some(a=>a.arg==='cancel'),'Discard effect is committed and cannot refund event');const a=c.actions.find(a=>a.cardUuid===c.targets[c.pending.handTarget]?.uuid);assert.ok(a,'Exact declared unit hand discard');return a;}if(/Reveal a unit from your hand/.test(title)){assert.equal(c.pid,c.own.id);assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.foreignHand?.uuid),'Other controller hand excluded');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.nonunit?.uuid),'Nonunit cannot be revealed');if(!c.pending.handTarget){const a=c.actions.find(a=>['noTarget','done','passAbility'].includes(a.arg));assert.ok(a,'Actual hidden-zone decline option');declines.push({step:c.step,arg:a.arg,label:a.label});return a;}const a=c.actions.find(a=>a.cardUuid===c.targets[c.pending.handTarget]?.uuid);assert.ok(a,'Exact declared revealed unit');return a;}if(/^Deal [35] damage to a unit that costs/.test(title)){const chosen=c.targets.chosen;assert.ok(chosen);assert.equal(chosen.cost,p.expect.handCost,'Captured printed cost');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.noCost?.uuid),'Cost-zero Mandalorian is excluded by the cost comparison');if(p.mode==='discard-higher'){assert.equal(chosen.zoneName,'discard');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.equal?.uuid),'Equal cost excluded');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.lower?.uuid),'Lower cost excluded');}else{assert.equal(chosen.zoneName,'hand');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.lower?.uuid),'Lower cost excluded');assert.ok(!c.actions.some(a=>a.cardUuid===c.targets.higher?.uuid),'Higher cost excluded');}const target=c.targets[c.pending.damageTarget];const a=c.actions.find(a=>a.cardUuid===target?.uuid);assert.ok(a,'Exact new physical damage recipient');assert.notEqual(target,chosen);return a;}return undefined;},
assertAfter(c){if(pendingPayment){const actual=pendingPayment.before-pendingPayment.actor.readyResourceCount;assert.equal(actual,pendingPayment.cost);payments.push({code:pendingPayment.code,card:c.eg.cardId(pendingPayment.card.uuid),actual,actor:c.eg.seatOf(pendingPayment.actor.id)});pendingPayment=null;}const id=x=>c.eg.cardId(x.uuid),focusId=id(focus),ownSeat=c.eg.seatOf(c.own.id);assert.equal(payments[0].actual,p.expect.focusPaid);assert.equal(payments.filter(x=>x.code===p.cardId).length,p.expect.focusPlayCount??1);const fromFocus=events.filter(e=>e.source===focusId),discard=fromFocus.filter(e=>e.name==='onCardDiscarded'),reveal=fromFocus.filter(e=>e.name==='onCardRevealed'),damage=fromFocus.filter(e=>e.name==='onDamageDealt'&&e.type==='ability');if(p.mode==='discard-higher'){assert.equal(focus.zoneName,'discard');assert.equal(discard.length,p.expect.discardCount);assert.equal(fromFocus.filter(e=>e.name==='onCardsDiscardedFromHand').length,p.expect.discardCount,'Zero eligible own hand emits neither specific nor overall discard event');assert.equal(damage.length,p.expect.damage?1:0);if(p.expect.discardCount){assert.equal(discard[0].card,id(c.targets.chosen));assert.equal(discard[0].from,'hand');assert.equal(c.targets.chosen.zoneName,'discard');const overall=fromFocus.find(e=>e.name==='onCardsDiscardedFromHand');assert.ok(overall&&events.indexOf(overall)>events.indexOf(discard[0]));}if(damage.length){assert.equal(damage[0].card,id(c.targets[p.expect.damageTarget]));assert.equal(damage[0].amount,5);assert.equal(c.targets[p.expect.damageTarget].damage,5);}}else{assert.equal(reveal.length,p.expect.revealCount);assert.equal(acks.length,p.expect.revealCount);for(const e of reveal){assert.deepEqual(e.cards,[id(c.targets.chosen)]);assert.equal(e.from,'hand');assert.equal(e.player,ownSeat);}if(c.targets.chosen)assert.equal(c.targets.chosen.zoneName,p.expect.retainedHand?'hand':'groundArena');assert.equal(damage.length,p.scenario==='on-attack-repeat'||p.scenario==='reentry-hooks'?2:p.expect.damage?1:0);assert.ok(damage.every(e=>e.amount===3));if(p.scenario==='wp-decline'||p.scenario==='on-attack-decline')assert.equal(declines.length,p.scenario==='on-attack-decline'?2:1);if(p.scenario==='revealed-card-paid'){assert.ok(retainedBeforePay);assert.equal(payments.find(x=>x.card===id(c.targets.chosen)).actual,6,'Revealed printed2 unit later actually pays6 aspect cost');}}
for(const e of fromFocus)assert.equal(e.player,ownSeat,'Captured source player throughout effect');if(c.targets.chosen){assert.equal(c.targets.chosen.cost,p.expect.handCost);if(p.expect.handCost===2)assert.equal(printedPayment(c.targets.chosen),6,'Aspect penalties do not alter printed cost query');}c.observed={focusId,physicalSetupIds:setupIds,events,menus,payments,acks,declines,retainedBeforePay,sourceMode:p.mode,sourceScenario:p.scenario,coverageStatus:'source-only; native/Wasm unassessed',handIds:p.handCards.map(row=>({key:row.key,id:id(c.targets[row.key]),owner:row.owner,zone:c.targets[row.key].zoneName})),deckCardIds:p.deckCardIds,selectedCardIds:p.selectedCardIds};stopped=true;c.targets.stopped=true;},
chooseLater(c){if(c.atWindow)return c.actions.find(a=>a.cardUuid&&c.eg.game.allCards.some(x=>x.uuid===a.cardUuid&&x.isUnit?.()&&x.isInPlay()&&x.controller.id===c.pid))??c.actions.find(a=>a.arg==='pass');const title=c.eg.player(c.pid).currentPrompt().menuTitle??'';if(/resourc/i.test(title))return c.actions.find(a=>a.arg==='done');if(title==='Choose a target for attack')return c.actions.find(a=>a.cardUuid===c.eg.player(c.pid).opponent.base.uuid)??c.actions.find(a=>a.cardUuid);return c.actions.find(a=>a.arg==='passAbility')??c.actions.find(a=>a.arg==='noTarget')??c.actions.find(a=>a.arg==='all')??c.actions.find(a=>a.arg==='done');}};
const game=await tokenFixture(env,pool,ss,seed);game.records[0].constructionParameters=structuredClone(p);game.records[0].fixtureConstruction='At the initial real action window use the literal deckCardIds, stage declared units, move declared physical hand cards and script cards into hand, move all other initial hand cards into resources, stage declared native Mandalorian/Shield references with generateToken/attachTo, and stage up to24 additional deck cards into ready resources through the existing harness. Native token references are setup, not entry-lifecycle claims. All focus plays, reveal acknowledgements, discards, damage, attacks, Waylay and reentry thereafter are actual legal actions. No later game-state edits.';game.witness.coverageObligationIds=[...scenario.coverageObligationIds];return game;}
module.exports={fixture,validateProbe,validatePool,dependencies:["lab/kessel-reference/pipeline/round-limit-interaction-fixture.js","lab/kessel-reference/pipeline/round-limit-probe-fixture.js","lab/kessel-reference/pipeline/probe-fixture.js","lab/kessel-reference/pipeline/terminal-completion.js","engine/env.js","engine/rng.js","engine/view.js","engine/stdio.js","engine/recorder.js","bots/omni/rs/state.js","bots/omni/rs/state-evidence.js","bots/omni/rs/unit-entry-state.js","bots/omni/rs/support-state.js","bots/omni/rs/round-limit-state.js","bots/omni/rs/pool.js","bots/players/index.js","bots/players/random.js","bots/players/rush.js","bots/players/heuristic.js","bots/players/profiles.js","bots/players/ismcts.js","bots/players/belief.js","bots/players/omniscient.js","bots/examples/random-bot.js","bots/examples/search-bot.js","bots/omni/search.js","bots/omni/evaluate.js","kessel:cards/pipeline/round-limit-probes.js","lab/kessel-reference/pipeline/captured-hand-cost-fixture.js","kessel:cards/pipeline/captured-hand-cost-probes.js"]};
