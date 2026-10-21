"use strict";
const test=require('node:test'),assert=require('node:assert/strict');
const {Env}=require('../../../engine/env');
const {constructProbeFixture}=require('../../../lab/kessel-reference/pipeline/probe-fixture');
const {roundLimitState}=require('./round-limit-state');
const {fullState}=require('./state');
const metadata=[
  {
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
    "internalName": "gar-saxon#coveting-power",
    "setCode": "ASH_047",
    "keywordValues": {}
  },
  {
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
    "internalName": "rancor-keeper",
    "setCode": "ASH_032",
    "keywordValues": {}
  },
  {
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
    "internalName": "kachirho-militia",
    "setCode": "ASH_160",
    "keywordValues": {
      "hidden": 1
    }
  },
  {
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
    "internalName": "nuvo-vindi#blue-shadow-perfected",
    "setCode": "HMW_062",
    "keywordValues": {}
  },
  {
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
    "internalName": "agent-kallus#seeking-the-rebels",
    "setCode": "SOR_115",
    "keywordValues": {
      "ambush": 1
    }
  }
];
function poolFor(){const pool=structuredClone(require('./pool.json'));for(const card of metadata)if(!pool.cards.some(c=>c.setCode===card.setCode))pool.cards.push(card);return pool;}
function change(object,key,value,eg){const existed=key in object,old=object[key];object[key]=value;try{assert.throws(()=>roundLimitState(eg),/Unsupported round limit state/);}finally{if(existed)object[key]=old;else delete object[key];}}
for(const owner of [0,1])for(const card of metadata)test('native current registration '+card.setCode+' owner '+owner,async()=>{
    const {eg,source,targets}=await constructProbeFixture(new Env(),poolFor(),{probe:{cardId:card.setCode,sourceInPlay:owner===0,sourceArena:'ground',leaderCode:'SOR_014',enemyLeaderCode:'SOR_014',baseCode:'SOR_023',initiative:owner===0?'self':'opponent',targets:owner===1?[{code:card.setCode,owner:'opponent',arena:'ground'}]:[]}},47700+owner);
    const focus=owner===0?source:targets[0],ordinal=card.setCode==='HMW_062'?1:0,ability=focus.triggeredAbilities[ordinal],limit=ability.limit,players=eg.ids.map(id=>eg.player(id));
    const read=()=>roundLimitState(eg).roundLimitState;
    const row=()=>read().registrations.find(r=>r.card===eg.cardId(focus.uuid));
    assert.deepEqual(row(),{card:eg.cardId(focus.uuid),side:'card',ordinal,used:[0,0]});
    assert.deepEqual(fullState(eg).roundLimitState,read());
    assert.ok(read().registrations.some(r=>eg.game.allCards.find(c=>eg.cardId(c.uuid)===r.card).zoneName!=='groundArena'),'offboard allocated producers are explicit');
    assert.notEqual(limit,ability.properties.limit,'current native clone differs from original printed property object');
    ability.properties.limit.increment(players[1-owner]);assert.deepEqual(row().used,[0,0],'stale original counts are not current counts');
    limit.increment(players[owner]);assert.equal(row().used[owner],1);assert.equal(row().used[1-owner],0);
    change(focus.cardData,'hp',focus.cardData.hp+1,eg);
    change(ability,'limit',undefined,eg);
    change(ability,'captureLimit',()=>limit,eg);
    change(ability,'limit',ability.properties.limit,eg);
    change(ability,'gainAbilitySource',focus,eg);
    change(ability.properties,'optional','unreviewed',eg);
    const hook=Object.keys(ability.properties.when)[0];change(ability.properties.when,hook,()=>true,eg);
    change(limit,'max',2,eg);change(limit,'eventName',new Set(['onPhaseEnded']),eg);change(limit,'isRegistered',false,eg);
    change(limit,'useCount',undefined,eg);change(limit,'useCount',new Map([['foreign-player',1]]),eg);
    for(const count of [-1,2,0.5])change(limit,'useCount',new Map([[players[owner].name,count]]),eg);
    const handler=limit.eventRegistrations[0].handler;eg.game.removeListener('onRoundEnded',handler);
    assert.throws(()=>read(),/native current reset listener/);eg.game.on('onRoundEnded',handler);
    const another=eg.game.allCards.flatMap(c=>c.triggeredAbilities??[]).find(a=>a!==ability&&a.limit?.max===1);
    assert.ok(another);change(another,'limit',limit,eg);
    const previous=ability.limit;focus.moveTo('spaceArena');eg.game.resolveGameState(true);
    assert.equal(ability.limit,previous);assert.equal(row().used[owner],1,'arena transfer preserves the real object');
    focus.moveTo('discard');eg.game.resolveGameState(true);
    assert.notEqual(ability.limit,previous);assert.equal(previous.isRegistered,false);
    assert.deepEqual(row().used,[0,0]);assert.ok(row(),'offboard current clone is exported');
    const offboard=ability.limit;focus.moveTo('hand');eg.game.resolveGameState(true);focus.moveTo('groundArena');eg.game.resolveGameState(true);
    assert.notEqual(ability.limit,offboard);assert.deepEqual(row().used,[0,0]);
});
test('real pending limit context retains retired handle and cannot export',async()=>{
    const {eg,source}=await constructProbeFixture(new Env(),poolFor(),{probe:{cardId:'ASH_032',sourceInPlay:true,sourceArena:'ground',leaderCode:'SOR_014',baseCode:'SOR_023',targets:[]}},47709);
    const {TriggerHandlingMode}=require('../../../forceteki/build/server/game/core/event/EventWindow');
    const context=eg.game.getFrameworkContext(source.controller);context.source=source.controller.base;
    eg.game.abilityHelper.immediateEffects.damage({amount:1,target:source}).resolve(source,context,TriggerHandlingMode.ResolvesTriggers);eg.game.continue();
    const captured=eg.game.currentAbilityResolver.context.getProps().limit;
    assert.equal(captured,source.triggeredAbilities[0].limit);
    assert.throws(()=>fullState(eg),/pending current or retired limit context/);
    source.moveTo('discard');eg.game.resolveGameState(true);
    assert.notEqual(captured,source.triggeredAbilities[0].limit);assert.equal(captured.isRegistered,false);
    assert.equal(eg.game.currentAbilityResolver.context.getProps().limit,captured);
    assert.throws(()=>roundLimitState(eg),/pending current or retired limit context/);
});
