'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {fullState,phaseStats}=require('../omni/rs/state');
const {observeStateEvidence,instrumentStateEvidence}=require('../omni/rs/state-evidence');
const {EventEmitter}=require('node:events');
require('../../forceteki/build/server/game/core/Game');
const {NonLeaderUnitCard}=require('../../forceteki/build/server/game/core/card/NonLeaderUnitCard');
test('versioned snapshots export pinned watcher evidence for all units before Hidden exists',()=>{
 const units=[];
 const make=(uuid)=>({uuid,internalName:uuid,cardData:{power:1,hp:2},getSummary:()=>({}),isToken:()=>false});
 const fresh={wasPlayedDeployedOrCreatedThisPhase:NonLeaderUnitCard.prototype.wasPlayedDeployedOrCreatedThisPhase,isToken:()=>false,title:"unit"};
 Object.defineProperties(fresh,{uuid:{value:'unit'},internalName:{value:'unit'},inPlayId:{value:7},cardData:{value:{power:1,hp:2}},upgrades:{value:[]}});
 fresh.getSummary=()=>({});fresh.getOngoingEffects=()=>[];fresh.isUnit=()=>true;
 fresh._cardsPlayedThisWatcher={someCardPlayed:cb=>cb({card:fresh,inPlayId:7})};fresh._leadersDeployedThisPhaseWatcher={someLeaderDeployed:()=>false};fresh._tokensCreatedThisPhaseWatcher={someTokenCreated:()=>false};
 const players=Object.fromEntries(['p1','p2'].map(id=>[id,{name:id,hasTheForce:false,base:make(id+'base'),getAllDeckLeaders:()=>[make(id+'leader')],getCardsInZone:z=>id==='p1'&&z==='groundArena'?units:[],drawDeck:[]}]));
 const forceTokens=Object.entries(players).map(([id,p])=>({uuid:id+'force',owner:p,isForceToken:()=>true,zoneName:'outsideTheGame'}));
 fresh.zoneName='hand';fresh.resolveAbilitiesForNewZone=()=>{};
 const allCards=[...forceTokens,fresh];
 const game=Object.assign(new EventEmitter(),{allCards,state:{allCards:allCards.map(c=>c.uuid)},ongoingEffectEngine:{effects:[]},getArenaUnits:({arena})=>arena==='groundArena'?units:[]});
 const eg={ids:['p1','p2'],player:id=>players[id],seatOf:id=>id,cardId:id=>id,phase:'action',round:1,winner:null,game};
 // Supply the exporter's required evidence lifecycle without inventing Hidden
 // qualification: the pinned card method below still reads its own watchers.
 const emptyWatcher=()=>({getCurrentValue:()=>[]});
 observeStateEvidence(eg,{cardsEnteredPlayThisPhase:emptyWatcher,cardsPlayedThisPhase:emptyWatcher});instrumentStateEvidence(eg);
 units.push(fresh);fresh.zoneName='groundArena';game.emit('onCardMoved',{card:fresh,originalZone:'hand',newZone:'groundArena'});fresh.resolveAbilitiesForNewZone();
 let state=fullState(eg);assert.deepEqual(state.roundLimitState,{version:1,registrations:[]});assert.equal(state.hiddenHistoryVersion,1);assert.equal(state.players.p1.ground[0].hiddenQualified,true);
 fresh._cardsPlayedThisWatcher={someCardPlayed:cb=>cb({card:fresh,inPlayId:6})};state=fullState(eg);assert.equal(state.players.p1.ground[0].hiddenQualified,false);
 fresh._cardsPlayedThisWatcher={someCardPlayed:()=>false};fresh._leadersDeployedThisPhaseWatcher={someLeaderDeployed:cb=>cb({card:fresh})};assert.equal(fullState(eg).players.p1.ground[0].hiddenQualified,true);
});
test('Hidden phase export is boolean and preserves simultaneous loss',()=>{
 const card={internalName:'test',getOngoingEffects:()=>[{duration:'untilEndOfPhase',type:'gainKeyword',getValue:()=> 'hidden'},{duration:'untilEndOfPhase',type:'loseKeyword',getValue:()=> 'hidden'}]};
 assert.deepEqual(phaseStats(card),{phaseKeywords:{hidden:1},phaseLostKeywords:['hidden']});
});
