'use strict';
const { terminalCompletion } = require('./terminal-completion');
// Source-engine construction only. Runtime admission and native/Wasm conformance are separate.
const assert = require('node:assert/strict');
const { isDeepStrictEqual } = require('node:util');
const { createHash } = require('node:crypto');
const { seededRng } = require('../../../engine/env');
const { canonicalAction, fullState, expandActions } = require('../../../bots/omni/rs/state');
const { makeBot } = require('../../../bots/players');

// A protocol state certifies an actual action window. Pending post-winner
// snapshots belong in witnesses or the completed result, never this record type.
function actionWindowState(eg, pid, step) {
    assert.equal(eg.isActionWindow(pid), true, 'State record requires an actual action window');
    return { type: 'state', step, state: fullState(eg, pid) };
}
function assertActionWindowRecords(records) {
    const decisions = new Map(records.filter(r => r.type === 'decision').map(r => [r.step, r]));
    for (const record of records.filter(r => r.type === 'state'))
        assert.equal(decisions.get(record.step)?.prompt.actionWindow, true, 'State record requires an actual action-window decision');
}
const reviewedDesigns = [
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "empty-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 5,
        "sourceHp": 12,
        "ownAdvantageRecipients": [],
        "sourceExhausted": true
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "empty-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 5,
        "sourceHp": 12,
        "ownAdvantageRecipients": [],
        "sourceExhausted": true
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "both-arenas-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "advantageBatchCount": 1,
        "advantageGeneratedCount": 2,
        "ownAdvantageRecipients": [
          "marine",
          "spacer"
        ],
        "enemyUpgradeCount": 0,
        "sourceUpgradeCount": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "both-arenas-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "advantageBatchCount": 1,
        "advantageGeneratedCount": 2,
        "ownAdvantageRecipients": [
          "marine",
          "spacer"
        ],
        "enemyUpgradeCount": 0,
        "sourceUpgradeCount": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "mixed-inventory-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [
        {
          "host": "marine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "own"
        },
        {
          "host": "marine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "marine",
          "code": "IC27_052",
          "owner": "own"
        },
        {
          "host": "spacer",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "enemyMarine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "enemy"
        },
        {
          "host": "enemyMarine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "enemy"
        }
      ],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 11,
        "marineUpgradeCount": 4,
        "spacerUpgradeCount": 2,
        "enemyUpgradeCount": 2
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "mixed-inventory-normal-play",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [
        {
          "host": "marine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "own"
        },
        {
          "host": "marine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "marine",
          "code": "IC27_052",
          "owner": "own"
        },
        {
          "host": "spacer",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "enemyMarine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "enemy"
        },
        {
          "host": "enemyMarine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "enemy"
        }
      ],
      "plan": [
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 11,
        "marineUpgradeCount": 4,
        "spacerUpgradeCount": 2,
        "enemyUpgradeCount": 2
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "shield-consumption-live-recompute",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [
        {
          "host": "marine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "own"
        },
        {
          "host": "marine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "marine",
          "code": "IC27_052",
          "owner": "own"
        },
        {
          "host": "spacer",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "enemyMarine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "enemy"
        },
        {
          "host": "enemyMarine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "enemy"
        }
      ],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "TWI_174",
          "target": "marine"
        }
      ],
      "expected": {
        "sourcePower": 10,
        "sourcePowerAfterPlay": 11,
        "marineDamage": 0,
        "marineShieldCount": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "shield-consumption-live-recompute",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [
        {
          "host": "marine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "own"
        },
        {
          "host": "marine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "marine",
          "code": "IC27_052",
          "owner": "own"
        },
        {
          "host": "spacer",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "own"
        },
        {
          "host": "enemyMarine",
          "token": "experience",
          "code": "TOKEN_EXPERIENCE",
          "owner": "enemy"
        },
        {
          "host": "enemyMarine",
          "token": "shield",
          "code": "TOKEN_SHIELD",
          "owner": "enemy"
        }
      ],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "TWI_174",
          "target": "marine"
        }
      ],
      "expected": {
        "sourcePower": 10,
        "sourcePowerAfterPlay": 11,
        "marineDamage": 0,
        "marineShieldCount": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "advantage-attack-expiry",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "LAW_043",
          "target": "marine"
        },
        {
          "code": "SOR_095",
          "from": "marine",
          "target": "enemyBase"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "sourcePowerAfterPlay": 7,
        "sourcePowerBeforeAttack": 8,
        "marineAdvantageCount": 0,
        "marineShieldCount": 1,
        "spacerAdvantageCount": 1,
        "enemyBaseDamage": 4
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "advantage-attack-expiry",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "LAW_043",
          "target": "marine"
        },
        {
          "code": "SOR_095",
          "from": "marine",
          "target": "enemyBase"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "sourcePowerAfterPlay": 7,
        "sourcePowerBeforeAttack": 8,
        "marineAdvantageCount": 0,
        "marineShieldCount": 1,
        "spacerAdvantageCount": 1,
        "enemyBaseDamage": 4
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "ordinary-upgrade-self-exclusion",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "IC27_052",
          "target": "executor"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "sourceHp": 15,
        "sourceUpgradeCount": 1
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "ordinary-upgrade-self-exclusion",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "IC27_052",
          "target": "executor"
        }
      ],
      "expected": {
        "sourcePower": 7,
        "sourceHp": 15,
        "sourceUpgradeCount": 1
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "host-defeat-attachment-cleanup",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "TWI_174",
          "target": "marine"
        }
      ],
      "expected": {
        "sourcePower": 6,
        "marineZone": "discard",
        "marineAttachmentCountAfterCleanup": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "host-defeat-attachment-cleanup",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "TWI_174",
          "target": "marine"
        }
      ],
      "expected": {
        "sourcePower": 6,
        "marineZone": "discard",
        "marineAttachmentCountAfterCleanup": 0
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "unique-keep-old",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 10,
        "survivor": "old",
        "defeated": "incoming",
        "survivorAdvantageCount": 1,
        "marineAdvantageCount": 2,
        "spacerAdvantageCount": 2,
        "totalFocusPlayCost": 24,
        "capturedDeadIncomingWhenPlayed": true
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "unique-keep-old",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 10,
        "survivor": "old",
        "defeated": "incoming",
        "survivorAdvantageCount": 1,
        "marineAdvantageCount": 2,
        "spacerAdvantageCount": 2,
        "totalFocusPlayCost": 24,
        "capturedDeadIncomingWhenPlayed": true
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 0,
    "scenario": "unique-keep-incoming",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 9,
        "survivor": "incoming",
        "defeated": "old",
        "survivorAdvantageCount": 0,
        "marineAdvantageCount": 2,
        "spacerAdvantageCount": 2,
        "totalFocusPlayCost": 24
      }
    }
  },
  {
    "family": "executor-upgrade-count",
    "cardId": "ASH_197",
    "owner": 1,
    "scenario": "unique-keep-incoming",
    "resourceCount": 30,
    "leaderCode": "SOR_014",
    "baseCode": "SOR_023",
    "baseDamage": 0,
    "expectedFocusPlayCost": 12,
    "design": {
      "units": [
        {
          "key": "marine",
          "code": "SOR_095",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "spacer",
          "code": "SOR_178",
          "owner": "own",
          "exhausted": false
        },
        {
          "key": "enemyMarine",
          "code": "SOR_095",
          "owner": "enemy",
          "exhausted": false
        }
      ],
      "initialAttachments": [],
      "plan": [
        {
          "code": "ASH_197"
        },
        {
          "code": "ASH_197"
        }
      ],
      "expected": {
        "sourcePower": 9,
        "survivor": "incoming",
        "defeated": "old",
        "survivorAdvantageCount": 0,
        "marineAdvantageCount": 2,
        "spacerAdvantageCount": 2,
        "totalFocusPlayCost": 24
      }
    }
  }
];
const designHash = probe => createHash('sha256').update(JSON.stringify(probe)).digest('hex');
function validateExecutorUpgradeCountProbe(probe) {
    const reviewed = reviewedDesigns.find(p => p.owner === probe?.owner && p.scenario === probe?.scenario);
    assert(reviewed && isDeepStrictEqual(reviewed, probe), 'Unsupported or changed Executor construction');
    return probe;
}
const matches = (c, code) => [c.cardData.setId, ...(c.cardData.setCodes ?? [])].some(s => s.set + '_' + String(s.number).padStart(3, '0') === code);
const arena = c => c.cardData.arena === 'space' ? 'spaceArena' : 'groundArena';
const plain = [];
function deckFor(pool, scenario) {
    const codes = [...new Set([...(scenario.units ?? plain).map((u) => u.code), ...scenario.plan.filter((s) => s.from !== 'leader').map((s) => s.code), ...(scenario.extraCodes ?? [])])];
    assert.ok(codes.length <= 17);
    for (const code of [...codes, scenario.leaderCode ?? 'SOR_014', scenario.baseCode ?? 'SOR_023'])
        assert.ok(pool.cards.some((c) => c.setCode === code), `Missing ${code} in oracle input pool`);
    const filler = pool.cards.filter((c) => c.types.includes('unit') && !c.text && !codes.includes(c.setCode)).slice(0, 17 - codes.length).map((c) => c.setCode);
    assert.equal(filler.length, 17 - codes.length);
    return { metadata: { name: 'Event group oracle', author: 'omni-rs fixture' }, leader: { id: scenario.leaderCode ?? 'SOR_014', count: 1 }, base: { id: scenario.baseCode ?? 'SOR_023', count: 1 }, deck: [...codes, ...filler].map((id, i) => ({ id, count: i === 16 ? 2 : 3 })), isPresentInDb: false };
}
async function tokenFixture(env, pool, scenario, seed) {
    const deck = deckFor(pool, scenario), eg = env.newGame({ selectionToggles: true, seed, deck1: deck, deck2: deck }), rng = seededRng('group-fixture-' + seed), bot = makeBot('random');
    await eg.start();
    while (!eg.ids.some((pid) => eg.isActionWindow(pid))) {
        const pid = eg.ids.find((id) => eg.legalActions(id).length), actions = expandActions(eg, eg.legalActions(pid));
        const initiativeChoice = scenario.initiative && actions.find(a => a.label === (pid === eg.ids[scenario.initiative === 'own' ? 0 : 1] ? 'Yourself' : 'Opponent'));
        eg.apply(pid, initiativeChoice ?? bot.choose({ game: eg, pid, actions, rng }), rng);
    }
    const own = eg.player(eg.ids[scenario.seat ?? 0]), enemy = eg.player(eg.ids[1-(scenario.seat ?? 0)]), targets = { ownBase: own.base, enemyBase: enemy.base };
    targets.leader = own.getAllDeckLeaders()[0];
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
    for (const code of new Set(scenario.plan.filter((s) => !s.from).map((s) => s.code))) {
        const count = scenario.plan.filter((s) => !s.from && s.code === code).length;
        while (own.getCardsInZone('hand').filter((c) => matches(c, code)).length < count) {
            const c = all(own).find((c) => matches(c, code) && c.zoneName !== 'hand');
            assert.ok(c, `Not enough real script copies ${code}`);
            c.moveTo('hand');
        }
    }
    for (const p of [own, enemy]) {
        for (const c of p.drawDeck.slice(0, 30)) {
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
    const initialRound = eg.round, observed = {}, scratch = {}, initialState = fullState(eg), records = [{ type: 'meta', schema: 'omni-rs-trace-v1', pool: pool.provenance, seed, bots: ['scripted-group-fixture', 'scripted-group-fixture'], decks: [deck, deck], scenario: scenario.name,
            evidenceStatus: pool.oracleOnly ? 'PROTOTYPE engine observation; admission/conformance unassessed' : 'Engine observation; native/Wasm conformance unassessed', fixtureConstruction: (scenario.emptyOwnDeck ? 'Empty-deck scenario additionally moves all remaining p1 draw-deck cards into discard before initial state capture. ' : '') + (scenario.emptyOwnHand ? 'Empty-hand scenario additionally moves every initial p1 hand card into ready resources before initial state capture. ' : '') + 'At first natural action window, move specified real deck units into their printed arenas with specified exhaustion, move script cards into p1 hand, move up to30 remaining deck cards perplayer into ready resources, ready all resources, set bases damage24(orprintedHP-1 forbothLethal), resolve game state, then set disclosed survivingunitdamage and refreshprompts. Specified initial Shields are created with pinned game.generateToken and attached before state resolution. No later state edits.', constructionParameters: { emptyOwnDeck: !!scenario.emptyOwnDeck, emptyOwnHand: !!scenario.emptyOwnHand, units: scenario.units ?? plain, plan: scenario.plan, bothLethal: !!scenario.bothLethal, leaderCode: scenario.leaderCode, deployedLeader: !!scenario.deployedLeader, baseDamage: scenario.baseDamage, initiative: scenario.initiative } }];
    let step = 0, index = 0, pending = null, scriptObserved = false, laterObserved = false;
    const completion = terminalCompletion(eg, 4000);
    try {
        while (true) {
            const pid = completion.nextActor(step); if (!pid) break;
            const actions = expandActions(eg, eg.legalActions(pid)), atWindow = eg.isActionWindow(pid), ctx = { eg, own, enemy, targets, actions, pid, atWindow, index, pending, step, observed, scratch, initialState };
            if (atWindow && scriptObserved && !laterObserved && eg.round > initialRound && scenario.assertLater) {
                scenario.assertLater(ctx);
                observed.laterRoundAssertion = true;
                laterObserved = true;
            }
            scenario.beforeWindow?.(ctx);
            if (atWindow) {
                records.push(actionWindowState(eg, pid, step));
                if (!scriptObserved && index === scenario.plan.length && eg.round === initialRound) {
                    scenario.assertAfter(ctx);
                    observed.postAction = true;
                    scriptObserved = true;
                }
            }
            let chosen;
            if (eg.round === initialRound && atWindow) {
                if (pid === own.id && index < scenario.plan.length) {
                    pending = scenario.plan[index++];
                    ctx.pending = pending;
                    ctx.index = index;
                    const c = pending.from ? targets[pending.from] : own.getCardsInZone('hand').find((c) => matches(c, pending.code));
                    assert.ok(c, `Missing script ${pending.code}`);
                    chosen = actions.find((a) => a.cardUuid === c.uuid);
                    assert.ok(chosen, `Illegal script ${pending.code}`);
                    scratch.incoming = c;
                }
                else
                    chosen = actions.find((a) => a.arg === 'pass');
            }
            else if (eg.round === initialRound && !atWindow && pending && !scriptObserved) {
                chosen = scenario.choose?.(ctx);
                if (!chosen && pid === own.id && pending.target)
                    chosen = actions.find((a) => a.cardUuid === targets[pending.target]?.uuid);
                chosen ??= actions.find((a) => a.kind === 'button' && /trigger|resolve|play|deal|heal|give/i.test(a.label ?? '') && !/pass|cancel|no/i.test(a.label ?? ''));
            }
            chosen ??= scenario.chooseLater?.(ctx);
            if (eg.over && !atWindow && /resourc/i.test(eg.player(pid).currentPrompt().menuTitle ?? '')) chosen = actions.find(a => a.arg === 'done') ?? chosen;
            chosen ??= bot.choose({ game: eg, pid, actions, rng });
            assert.ok(chosen);
            const prompt = eg.player(pid).currentPrompt();
            records.push({ type: 'decision', step, actor: eg.seatOf(pid), prompt: { type: prompt.promptType ?? null, title: prompt.menuTitle ?? null, selected: (eg.player(pid).promptState.selectedCards ?? []).map((c) => eg.cardId(c.uuid)), actionWindow: atWindow }, actions: actions.map((a) => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key, events: [] });
            if (process.env.GROUP_FIXTURE_DEBUG && step < 35)
                console.error(JSON.stringify({ step, actor: eg.seatOf(pid), title: prompt.menuTitle, selected: (eg.player(pid).promptState.selectedCards ?? []).map(c => eg.cardId(c.uuid)), chosen: canonicalAction(eg, chosen) }));
            scenario.beforeApply?.({ ...ctx, chosen });
            eg.apply(pid, chosen, rng);
            step++;
        }
        observed.terminalCompletion = completion.assertComplete();
        assert.ok(eg.over, 'Oracle game did not complete');
        assert.equal(index, scenario.plan.length, 'Script incomplete');
        if (!scriptObserved) {
            scenario.assertAfter({ eg, own, enemy, targets, observed, scratch, initialState });
            observed.postAction = true;
        }
        if (scenario.assertLater)
            assert.ok(laterObserved, 'Missing later-round assertion');
        scenario.assertWitness?.({ observed, scratch, records, eg, own, enemy, targets, initialState });
        records.push({ type: 'result', step, winner: eg.winner, state: fullState(eg) });
        return { records, witness: { scenario: scenario.name, family: scenario.family, observed, decisions: step, winner: eg.winner } };
    }
    catch(e){e.diagnostic={records,observed,index,step};throw e;}
    finally {
        bot.close?.();
    }
}
function snapshot(card, eg) {
    return { id: eg.cardId(card.uuid), name: card.internalName, zone: card.zoneName,
        owner: eg.seatOf(card.owner.id), controller: eg.seatOf(card.controller.id),
        power: card.isUnit?.() && card.isInPlay() ? card.getPower() : null,
        hp: card.isUnit?.() && card.isInPlay() ? card.getHp() : null,
        exhausted: card.isUnit?.() && card.isInPlay() ? card.exhausted : null,
        damage: card.isUnit?.() && card.isInPlay() ? card.damage : null,
        upgrades: card.isUnit?.() && card.isInPlay() ? card.upgrades.map(u => ({id:eg.cardId(u.uuid),name:u.internalName,owner:eg.seatOf(u.owner.id),controller:eg.seatOf(u.controller.id)})) : [] };
}
function constructScenario(probe, name) {
    validateExecutorUpgradeCountProbe(probe);
    const unique = probe.scenario.startsWith('unique-');
    return {
        name, family: 'executor-upgrade-count', seat: probe.owner, baseDamage: probe.baseDamage,
        leaderCode: probe.leaderCode, baseCode: probe.baseCode,
        units: probe.design.units, plan: probe.design.plan,
        extraCodes: probe.design.initialAttachments.filter(a => !a.token).map(a => a.code),
        setup(c) {
            c.targets.events = []; c.targets.samples = []; c.targets.initialUpgrades = [];
            const id = card => card ? c.eg.cardId(card.uuid) : null;
            for (const eventName of ['onTokensCreated','onCardPlayed','onCardDefeated','onUpgradeAttached','onDamageDealt','onAttackEnd','onEffectApplied']) {
                c.eg.game.on(eventName, event => c.targets.events.push({name:eventName, card:id(event.card),
                    source:id(event.context?.source), sourceZone:event.context?.source?.zoneName ?? null,
                    player:event.player ? c.eg.seatOf(event.player.id) : null, amount:event.amount ?? null,
                    cards:event.cards?.map(id) ?? null, tokenType:event.tokenType ?? null,
                    generatedTokens:event.generatedTokens?.map(id) ?? null,
                    parent:id(event.parentCard), upgrade:id(event.upgradeCard)}));
            }
            const all = p => [...p.drawDeck,...p.getCardsInZone('hand'),...p.getCardsInZone('resource')];
            for (const attachment of probe.design.initialAttachments) {
                const host = c.targets[attachment.host], owner = attachment.owner === 'enemy' ? c.enemy : c.own;
                assert(host && owner === host.owner, 'Standard construction excludes foreign attachments');
                const upgrade = attachment.token ? c.eg.game.generateToken(owner, attachment.token) : all(owner).find(x => matches(x,attachment.code));
                assert(upgrade, 'Missing actual initial attachment');
                upgrade.attachTo(host);
                c.targets.initialUpgrades.push({id:id(upgrade),host:id(host),name:upgrade.internalName});
            }
        },
        beforeWindow(c) {
            if (!c.atWindow || c.observed.postAction) return;
            if(c.index >= 1 && !c.targets.executor) c.targets.executor = c.scratch.incoming;
            c.targets.samples.push({index:c.index,resources:c.own.readyResourceCount,
                executor:c.targets.executor ? snapshot(c.targets.executor,c.eg) : null,
                units:c.own.getArenaUnits().map(x => snapshot(x,c.eg))});
        },
        beforeApply(c) {
            if (!c.atWindow || c.pid !== c.own.id || c.pending?.code !== 'ASH_197') return;
            c.scratch.focusPlays ??= [];
            if(c.scratch.focusPlays.some(x=>x.id===c.eg.cardId(c.scratch.incoming.uuid)))return;
            const source = c.scratch.incoming;
            const recipients = c.own.getArenaUnits({otherThan:source}).map(x=>c.eg.cardId(x.uuid));
            c.scratch.focusPlays.push({id:c.eg.cardId(source.uuid),readyBefore:c.own.readyResourceCount,allocationStart:c.eg.game.state.allCards.length,recipientsBeforeUnique:recipients});
            c.scratch.source ??= source;
            c.scratch.initialReady ??= c.own.readyResourceCount;
        },
        choose(c) {
            const title=c.eg.player(c.pid).currentPrompt().menuTitle ?? '';
            if(title.includes('which copy')) {
                const defeated=probe.scenario==='unique-keep-incoming'?c.targets.executor:c.scratch.incoming;
                const action=c.actions.find(a=>a.cardUuid===defeated?.uuid);
                assert(action,'Exact physical unique choice must be legal');
                c.observed.uniqueChoice={defeated:c.eg.cardId(defeated.uuid),incoming:c.eg.cardId(c.scratch.incoming.uuid),old:c.eg.cardId(c.targets.executor.uuid)};
                return action;
            }
            return c.pending?.target ? c.actions.find(a=>a.cardUuid===c.targets[c.pending.target]?.uuid) : undefined;
        },
        assertAfter(c) {
            const expected=probe.design.expected, source=unique&&probe.scenario==='unique-keep-incoming'?c.scratch.incoming:c.targets.executor;
            const count=(key,name)=>c.targets[key].upgrades.filter(x=>x.internalName===name).length;
            assert.equal(source.zoneName,'spaceArena');
            assert.equal(source.getPower(),expected.sourcePower,'Live whole attachment inventory power');
            if(expected.sourceHp!==undefined)assert.equal(source.getHp(),expected.sourceHp);
            if(expected.sourceExhausted!==undefined)assert.equal(source.exhausted,expected.sourceExhausted);
            if(expected.sourceUpgradeCount!==undefined)assert.equal(source.upgrades.length,expected.sourceUpgradeCount);
            for(const [field,key] of [['marineUpgradeCount','marine'],['spacerUpgradeCount','spacer'],['enemyUpgradeCount','enemyMarine']])
                if(expected[field]!==undefined)assert.equal(c.targets[key].upgrades.length,expected[field]);
            for(const [field,key,token] of [['marineShieldCount','marine','shield'],['marineAdvantageCount','marine','advantage'],['spacerAdvantageCount','spacer','advantage']])
                if(expected[field]!==undefined)assert.equal(count(key,token),expected[field]);
            if(expected.marineDamage!==undefined)assert.equal(c.targets.marine.damage,expected.marineDamage);
            if(expected.marineZone!==undefined)assert.equal(c.targets.marine.zoneName,expected.marineZone);
            if(expected.marineAttachmentCountAfterCleanup!==undefined)assert.equal(c.targets.marine.isInPlay() ? c.targets.marine.upgrades.length : 0,expected.marineAttachmentCountAfterCleanup);
            if(expected.enemyBaseDamage!==undefined)assert.equal(c.enemy.base.damage,expected.enemyBaseDamage);
            const first=c.targets.samples.find(x=>x.index===1);
            assert(first,'First paid play settled');
            assert.equal(c.scratch.initialReady-first.resources,probe.expectedFocusPlayCost,'Real ordinary cost including aspect penalty');
            if(expected.sourcePowerAfterPlay!==undefined)assert.equal(first.executor.power,expected.sourcePowerAfterPlay);
            if(expected.sourcePowerBeforeAttack!==undefined)assert.equal(c.targets.samples.find(x=>x.index===2).executor.power,expected.sourcePowerBeforeAttack);
            if(unique) {
                const old=c.targets.executor,incoming=c.scratch.incoming,dead=source===old?incoming:old;
                assert.notEqual(old.uuid,incoming.uuid,'Unique copies have distinct physical IDs');
                assert.equal(dead.zoneName,'discard');
                assert.equal(source === old ? 'old' : 'incoming',expected.survivor);
                assert.equal(dead === old ? 'old' : 'incoming',expected.defeated);
                assert.equal(c.scratch.initialReady-c.own.readyResourceCount,expected.totalFocusPlayCost);
                assert.equal(count('marine','advantage'),expected.marineAdvantageCount);
                assert.equal(count('spacer','advantage'),expected.spacerAdvantageCount);
                assert.equal(source.upgrades.filter(x=>x.internalName==='advantage').length,expected.survivorAdvantageCount);
                c.observed.defeated=snapshot(dead,c.eg);
            }
            // Check each complete WhenPlayed batch, including the dead incoming source.
            const batches=c.targets.events.filter(e=>e.name==='onTokensCreated'&&e.tokenType==='advantage'&&c.scratch.focusPlays.some(p=>p.id===e.source));
            if(expected.advantageBatchCount!==undefined)assert.equal(batches.length,expected.advantageBatchCount);
            if(expected.advantageGeneratedCount!==undefined)assert.equal(batches.flatMap(b=>b.generatedTokens).length,expected.advantageGeneratedCount);
            if(expected.ownAdvantageRecipients!==undefined)assert.deepEqual(batches.flatMap(b=>b.cards).sort(),expected.ownAdvantageRecipients.map(key=>c.eg.cardId(c.targets[key].uuid)).sort());
            for(const [index,play] of c.scratch.focusPlays.entries()) {
                const batch=batches.filter(e=>e.source===play.id);
                const recipients=index===0?probe.design.units.filter(u=>u.owner==='own').map(u=>c.eg.cardId(c.targets[u.key].uuid)):
                    [...probe.design.units.filter(u=>u.owner==='own').map(u=>c.eg.cardId(c.targets[u.key].uuid)),...(source===c.targets.executor?[c.eg.cardId(source.uuid)]:[])];
                assert.equal(batch.length,recipients.length?1:0,'One creation event for entire nonempty recipient set');
                if(!recipients.length)continue;
                assert.deepEqual([...batch[0].cards].sort(),[...recipients].sort(),'Exact other friendly physical recipients');
                assert.equal(batch[0].amount,1);assert.equal(batch[0].player,c.eg.seatOf(c.own.id));
                assert.equal(batch[0].generatedTokens.length,recipients.length);
                assert.equal(new Set(batch[0].generatedTokens).size,recipients.length);
                assert.deepEqual(batch[0].generatedTokens,recipients.map((_,i)=>'c'+(play.allocationStart+i)),'Fresh token IDs allocate contiguously in recipient order');
                assert(!batch[0].cards.includes(play.id),'Source physical identity excluded');
                for(const tokenId of batch[0].generatedTokens) {
                    const token=c.eg.game.allCards.find(t=>c.eg.cardId(t.uuid)===tokenId);
                    assert(token); assert.equal(token.internalName,'advantage');
                    assert.equal(token.owner,c.own);assert.equal(token.controller,c.own);
                    const attach=c.targets.events.filter(e=>e.name==='onUpgradeAttached'&&e.upgrade===tokenId&&e.source===play.id);
                    assert.equal(attach.length,1);assert.equal(attach[0].parent,batch[0].cards[batch[0].generatedTokens.indexOf(tokenId)],'Generated-token order binds exact host');
                }
            }
            if(expected.capturedDeadIncomingWhenPlayed) {
                const batch=batches.find(e=>e.source===c.eg.cardId(c.scratch.incoming.uuid));
                assert.equal(batch.sourceZone,'discard','Captured dead incoming source still resolves');
                assert(batch.cards.includes(c.eg.cardId(source.uuid)));
            }
            if(probe.scenario==='shield-consumption-live-recompute') {
                const shield=c.targets.initialUpgrades.find(u=>u.host===c.eg.cardId(c.targets.marine.uuid)&&u.name==='shield');
                assert(shield);assert.equal(c.eg.game.allCards.find(t=>c.eg.cardId(t.uuid)===shield.id).zoneName,'outsideTheGame');
                c.observed.consumedShield=shield.id;
            }
            if(probe.scenario==='host-defeat-attachment-cleanup') {
                const marine=c.eg.cardId(c.targets.marine.uuid);
                for(const tokenId of batches.flatMap(b=>b.generatedTokens).filter(id=>c.targets.events.some(e=>e.name==='onUpgradeAttached'&&e.parent===marine&&e.upgrade===id)))
                    assert.equal(c.eg.game.allCards.find(t=>c.eg.cardId(t.uuid)===tokenId).zoneName,'outsideTheGame','Host departure removes exact attached token');
            }
            if(probe.scenario==='advantage-attack-expiry') {
                const marineId=c.eg.cardId(c.targets.marine.uuid),expired=batches[0].generatedTokens.find(t=>c.targets.events.some(e=>e.name==='onUpgradeAttached'&&e.parent===marineId&&e.upgrade===t));
                const token=c.eg.game.allCards.find(t=>c.eg.cardId(t.uuid)===expired);
                assert.equal(token.zoneName,'outsideTheGame','Exact Advantage expires on attack end');
                c.observed.expiredAdvantage=expired;
            }
            c.observed.source=snapshot(source,c.eg);
            c.observed.hosts=Object.fromEntries(probe.design.units.map(u=>[u.key,snapshot(c.targets[u.key],c.eg)]));
            c.observed.focusPlays=c.scratch.focusPlays;c.observed.batches=batches;
            c.observed.samples=c.targets.samples;c.observed.events=c.targets.events;
            c.observed.actualFocusPlayCost=probe.expectedFocusPlayCost;
        }
    };
}
async function executorUpgradeCountFixture(env,pool,scenario,seed) {
    const probe=validateExecutorUpgradeCountProbe(scenario.probe);
    const game=await tokenFixture(env,pool,constructScenario(probe,scenario.name??probe.scenario+'-seat'+probe.owner),seed);
    game.records[0].constructionParameters.rawProbe=JSON.parse(JSON.stringify(probe));
    game.records[0].constructionParameters.rawProbeSha256=designHash(probe);
    game.records[0].fixtureConstruction='At first natural action window, stage disclosed real deck hosts in printed arenas, declared initial token/ordinary upgrades on hosts, script cards in source-owner hand, move up to30 remaining deck cards into ready resources and ready existing resources, set both bases damage0, resolve state. All later actions are actual legal engine actions; recorded full-game continuation reaches terminal winner.';
    game.witness.rawProbe=JSON.parse(JSON.stringify(probe));game.witness.rawProbeSha256=designHash(probe);
    // tokenFixture returns only after assertAfter has checked the focused physical
    // effects, the script has completed, and the terminal recording is complete.
    // Read caller coverage only here: a rejected construction or failed effect
    // assertion must never expose credited obligation IDs.
    const coverageObligationIds = [...(scenario.coverageObligationIds ?? [])];
    assert(coverageObligationIds.length === 0 || (coverageObligationIds.length === 1 && coverageObligationIds[0] === 'ASH_197:executor-upgrade-count:' + probe.scenario + '-seat' + probe.owner), 'Only the observed Executor construction obligation may be credited');
    game.witness.coverageObligationIds = coverageObligationIds;
    return game;
}
module.exports={actionWindowState,assertActionWindowRecords,fixture:executorUpgradeCountFixture,validateProbe:validateExecutorUpgradeCountProbe,executorUpgradeCountFixture,validateExecutorUpgradeCountProbe,dependencies:['lab/kessel-reference/pipeline/terminal-completion.js',
 'kessel:cards/pipeline/executor-upgrade-count-probes.js',
 'lab/kessel-reference/pipeline/executor-upgrade-count-probe-fixture.js',
 'engine/env.js','engine/rng.js','bots/omni/rs/state.js','bots/omni/rs/state-evidence.js',
 'bots/omni/rs/support-state.js','bots/omni/rs/unit-entry-state.js','kessel:crates/kessel/src/executor_upgrade_count_contract.rs','bots/players/index.js'
]};
