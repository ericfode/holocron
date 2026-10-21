'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),crypto=require('node:crypto');
const leaf=require('./inactive-phase-keyword-state');
test('observation starts once before initialization and missing history never becomes proof',()=>{
    assert.throws(()=>leaf.observeInactivePhaseKeywords({started:true}),/before initialization/);
    assert.throws(()=>leaf.inactivePhaseKeywordProjection({},{}),/preplay observation missing/);
    assert.equal(leaf.validatesInactivePhaseKeywordCompanion({inactivePhaseKeywordStateVersion:1,inactiveAllocatedCards:[]},{},{},{sentinel:1}),false);
});
test('serialized or foreign projection cannot manufacture a companion receipt',()=>{
    const raw={inactivePhaseKeywordStateVersion:1,inactiveAllocatedCards:[{id:'c106',name:'mandalorian',setCode:'TOKEN_MANDALORIAN',owner:'p1',controller:'p1',phaseKeywords:{sentinel:1}}]};
    assert.equal(leaf.validatesInactivePhaseKeywordCompanion(raw,{},{},{sentinel:1}),false);
    assert.equal(leaf.validatesInactivePhaseKeywordCompanion(structuredClone(raw),{},{},{sentinel:1}),false);
});
test('source-gated marker does not allocate unrelated retired tokens or virtual identities',()=>{
    // Synthetic API boundary, not a source-game or native-equivalence claim.
    require('../../../engine/env');
    const {EventEmitter}=require('node:events'),game=new EventEmitter();
    const shield={uuid:'existing-shield',internalName:'shield',cardData:{id:'not-buy-time'},zoneName:undefined,getOngoingEffects:()=>[]};
    game.isUndoEnabled=false;game.state={allCards:['existing-shield']};game.getFromId=id=>id==='existing-shield'?shield:null;game.ongoingEffectEngine={effects:[]};
    const eg={started:false,game,ids:['p1','p2'],isActionWindow:()=>true};leaf.observeInactivePhaseKeywords(eg);
    assert.deepEqual(leaf.inactivePhaseKeywordProjection(eg,{}),{});
    assert.deepEqual(game.state.allCards,['existing-shield']);
    shield.internalName='buy-time';assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,{}),/complete allocated source profile/);
});
// Source fixture input is an immutable external source-only artifact. It is compiled
// unchanged with this snapshot's dependency resolution, never registered in dispatch.
const sourceGate=!!process.env.INACTIVE_PHASE_SOURCE_FIXTURE;
test('all sixteen unchanged source games retain physical complement through expiry',{skip:!sourceGate},async()=>{
    for(const name of ['INACTIVE_PHASE_SOURCE_CASES','INACTIVE_PHASE_SOURCE_POOL','INACTIVE_PHASE_SOURCE_RESULTS'])assert.ok(process.env[name],name+' required');
    const {Env}=require('../../../engine/env'),{loadPool}=require('./pool'),{fullState}=require('./state');
    const source=fs.readFileSync(process.env.INACTIVE_PHASE_SOURCE_FIXTURE),filename=path.resolve(__dirname,'../../../lab/kessel-reference/pipeline/created-token-phase-keyword-fixture.js');
    const m=new Module(filename);m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));m._compile(source.toString(),filename);
    const caseBytes=fs.readFileSync(process.env.INACTIVE_PHASE_SOURCE_CASES),cases=JSON.parse(caseBytes),pool=loadPool(process.env.INACTIVE_PHASE_SOURCE_POOL),poolBytes=fs.readFileSync(process.env.INACTIVE_PHASE_SOURCE_POOL);
    const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),out=process.env.INACTIVE_PHASE_SOURCE_RESULTS;fs.mkdirSync(out,{recursive:true});
    const summary=[];let positiveRetired=0,companionNegatives=0,expiry=0;
    for(const [i,c]of cases.entries()){
        const env=new Env(),newGame=env.newGame.bind(env),windows=[];let eg;
        env.newGame=args=>{eg=newGame(args);leaf.observeInactivePhaseKeywords(eg);assert.throws(()=>leaf.observeInactivePhaseKeywords(eg),/once/);const apply=eg.apply.bind(eg);eg.apply=(...args)=>{const result=apply(...args);if(eg.ids.some(pid=>eg.isActionWindow(pid))){
            const players=fullState(eg).players,before={nextCardId:eg.game.state.allCards.length,idx:[...eg.idx]},projection=leaf.inactivePhaseKeywordProjection(eg,players);
            assert.deepEqual({nextCardId:eg.game.state.allCards.length,idx:[...eg.idx]},before,'Leaf reads never allocate/cache IDs');
            assert.equal(projection.inactivePhaseKeywordStateVersion,1,'Allocated Buy Time selects mandatory version');
            assert.ok(projection.inactiveAllocatedCards.every((r,n,rs)=>n===0||Number(rs[n-1].id.slice(1))<Number(r.id.slice(1))));
            for(const row of projection.inactiveAllocatedCards){assert.ok(Object.hasOwn(row,'phaseKeywords'),'Empty rows carry required map');assert.ok(!Object.hasOwn(row,'source')&&!Object.hasOwn(row,'origin'),'No unretained provenance serialized');const card=eg.game.getFromId(eg.game.state.allCards[Number(row.id.slice(1))]);assert.equal(card.internalName,row.name);assert.ok(!card.isForceToken?.(),'Force already has live identity');
                if(row.phaseKeywords.sentinel){positiveRetired++;assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,eg,card,{sentinel:1}),true);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(structuredClone(projection),eg,card,{sentinel:1}),false);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,{},card,{sentinel:1}),false);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,eg,card,{saboteur:1}),false);
                    const saved=row.owner;row.owner=saved==='p1'?'p2':'p1';assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,eg,card,{sentinel:1}),false);row.owner=saved;companionNegatives+=4;
                }
            }
            const bad=structuredClone(players);bad.p1.deck.push(structuredClone(bad.p1.base));assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,bad),/duplicate live identity/);
            const missing=structuredClone(players);delete missing.p1.base;assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,missing),/omitted live\/unsupported identity/);
            const wrongDefinition=structuredClone(players);wrongDefinition.p1.base.name='foreign';assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,wrongDefinition),/contradictory live name/);
            const fakeDeployment=structuredClone(players);fakeDeployment.p1.ground.push(structuredClone(fakeDeployment.p1.leader));assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,fakeDeployment),/duplicate live identity/);
            const future=structuredClone(players);future.p1.deck.push({id:'c'+before.nextCardId});assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,future),/exceeds allocation/);
            windows.push({round:eg.round,nextCardId:before.nextCardId,projection});
        }return result;};return eg;};
        const game=await m.exports.fixture(env,pool,c,183000+i);assert.equal(game.records.at(-1).type,'result');assert.ok(game.witness.observed.terminalCompletion.winner);const terminal=leaf.inactivePhaseKeywordProjection(eg,fullState(eg).players);
        if(c.probe.scenario==='framework-death-before-then'){
            const active=windows.find(w=>w.projection.inactiveAllocatedCards.some(r=>r.phaseKeywords.sentinel));assert.ok(active);const row=active.projection.inactiveAllocatedCards.find(r=>r.phaseKeywords.sentinel),later=windows.find(w=>w.round>active.round&&w.projection.inactiveAllocatedCards.some(r=>r.id===row.id&&!Object.keys(r.phaseKeywords).length));assert.ok(later,'Natural phase expiry retains exact retired identity');assert.equal(terminal.inactiveAllocatedCards.find(r=>r.id===row.id)?.name,row.name);assert.deepEqual(terminal.inactiveAllocatedCards.find(r=>r.id===row.id)?.phaseKeywords,{});assert.ok(later.nextCardId>=active.nextCardId);expiry++;
        }
        fs.writeFileSync(path.join(out,i+'.json'),JSON.stringify({case:c,windows,terminal,game}));summary.push({name:c.name,winner:game.witness.winner,windows:windows.length});
    }
    assert.equal(cases.length,16);assert.equal(expiry,2);assert.ok(positiveRetired>=2);assert.ok(companionNegatives>=8);
    fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({sourceFixtureSha256:hash(source),caseSha256:hash(caseBytes),poolSha256:hash(poolBytes),sourceCases:summary.length,positiveRetired,expiry,companionNegatives,summary,scope:'new leaf source-only; central state/unit-entry helper unchanged; no native admission/conformance'},null,2));
});

test('synthetic boundary rejects unserialized phase keywords on non-arena live refs',()=>{
    require('../../../engine/env');
    const {EventEmitter}=require('node:events'),BuyTime=require('../../../forceteki/build/server/game/cards/08_ASH/events/BuyTime').default;
    const profile=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../forceteki/test/json/Card/buy-time.json'))),game=new EventEmitter();
    game.isUndoEnabled=false;game.state={allCards:['source','target']};game.ongoingEffectEngine={effects:[]};
    const source=Object.create(BuyTime.prototype),who={id:'p1'};
    Object.defineProperties(source,Object.fromEntries(Object.entries({uuid:'source',internalName:'buy-time',cardData:profile,game,owner:who,controller:who,zoneName:'hand',isToken:()=>false,isUnit:()=>false,getOngoingEffects:()=>[]}).map(([key,value])=>[key,{value,configurable:true}])));
    const effect={type:'gainKeyword',duration:'untilEndOfPhase'},target={uuid:'target',internalName:'fixture-unit',cardData:{setId:{set:'ASH',number:61}},owner:who,controller:who,zoneName:'hand',isToken:()=>false,isUnit:()=>true,getOngoingEffects:()=>[effect]};
    game.getFromId=id=>id==='source'?source:target;const eg={started:false,game,ids:['p1','p2'],seatOf:id=>id,isActionWindow:()=>true};leaf.observeInactivePhaseKeywords(eg);
    const players={p1:{hand:[{id:'c0',name:'buy-time',setCode:'ASH_091'},{id:'c1',name:'fixture-unit',setCode:'ASH_061'}]},p2:{hand:[]}};
    for(const zone of ['hand','deck','discard','base']){target.zoneName=zone;assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/unserialized phase keyword/);}
    target.zoneName='groundArena';assert.deepEqual(leaf.inactivePhaseKeywordProjection(eg,players),{inactivePhaseKeywordStateVersion:1,inactiveAllocatedCards:[]},'Existing arena-unit phase serializer is unchanged');
    target.isUnit=()=>false;assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/unserialized phase keyword/,'Attached upgrade refs do not serialize phase keywords');
});
test('real undo-enabled installation and public late-enable/restore are rejected',{skip:!sourceGate},async()=>{
    const {Env}=require('../../../engine/env'),{loadPool}=require('./pool'),{fullState}=require('./state');
    const cases=JSON.parse(fs.readFileSync(process.env.INACTIVE_PHASE_SOURCE_CASES)),probe=cases[0].probe;
    const deck={metadata:{name:'Undo API boundary only'},leader:{id:probe.leaderCode,count:1},base:{id:probe.baseCode,count:1},deck:probe.deckCardIds.map((id,i)=>({id,count:i===16?2:3}))};
    const env=new Env(),enabled=env.newGame({seed:189000,deck1:deck,deck2:deck,undo:true}),before=enabled.game.listenerCount('onTokensCreated');
    assert.equal(enabled.game.isUndoEnabled,true);assert.throws(()=>leaf.observeInactivePhaseKeywords(enabled),/undo-enabled/);assert.equal(enabled.game.listenerCount('onTokensCreated'),before);assert.equal(enabled.started,false);
    const receipt={early:{isUndoEnabled:true,started:false,observerRejected:true,noListenerAdded:true},late:null};
    const originalNew=env.newGame.bind(env);let tested=false,eg,lateProof,lateCard,latePlayers;
    env.newGame=args=>{eg=originalNew(args);leaf.observeInactivePhaseKeywords(eg);const apply=eg.apply.bind(eg);eg.apply=(...args)=>{const result=apply(...args);if(!tested&&eg.ids.some(pid=>eg.isActionWindow(pid))){const players=fullState(eg).players,projection=leaf.inactivePhaseKeywordProjection(eg,players),row=projection.inactiveAllocatedCards.find(r=>r.phaseKeywords.sentinel);if(row){tested=true;const card=eg.game.getFromId(eg.game.state.allCards[Number(row.id.slice(1))]);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,eg,card,{sentinel:1}),true);const allocated=eg.game.state.allCards.slice();eg.game.setUndoConfirmationRequired(true);assert.equal(eg.game.isUndoEnabled,true);assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/undo-enabled/);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(projection,eg,card,{sentinel:1}),false);eg.game.setUndoConfirmationRequired(false);assert.equal(eg.game.isUndoEnabled,true);lateProof=projection;lateCard=card;latePlayers=players;receipt.late={publicEnable:'setUndoConfirmationRequired(true)',publicFreeMode:'setUndoConfirmationRequired(false)',restored:false,projectionRejected:true,companionRejected:true,token:row.id,markFailures:[]};}}if(tested&&!receipt.late.restored&&eg.ids.some(pid=>eg.isActionWindow(pid))){const allocated=eg.game.state.allCards.slice(),pid=eg.ids.find(pid=>eg.isActionWindow(pid));let mark;try{mark=eg.mark(pid);}catch(e){receipt.late.markFailures.push(e.message);}if(mark!==undefined){assert.ok(mark>=0);eg.restore(pid,mark);assert.deepEqual(eg.game.state.allCards,allocated);assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,latePlayers),/undo-enabled/);assert.equal(leaf.validatesInactivePhaseKeywordCompanion(lateProof,eg,lateCard,{sentinel:1}),false);receipt.late.snapshotId=mark;receipt.late.restored=true;receipt.late.allocatedIdsUnchanged=true;receipt.late.allocatedIdsBefore=allocated;receipt.late.allocatedIdsAfter=eg.game.state.allCards.slice();receipt.late.engineUndoEnabledAfterRestore=eg.game.isUndoEnabled;const restoredCard=eg.game.getFromId(allocated[Number(receipt.late.token.slice(1))]);receipt.late.restoredTarget={uuid:restoredCard.uuid,sentinel:restoredCard.hasSomeKeyword('sentinel')};}}return result;};return eg;};
    const filename=path.resolve(__dirname,'../../../lab/kessel-reference/pipeline/created-token-phase-keyword-fixture.js'),m=new Module(filename);m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));m._compile(fs.readFileSync(process.env.INACTIVE_PHASE_SOURCE_FIXTURE,'utf8'),filename);
    const game=await m.exports.fixture(env,loadPool(process.env.INACTIVE_PHASE_SOURCE_POOL),cases.find(c=>c.probe.owner===0&&c.probe.scenario==='framework-death-before-then'),189001);assert.ok(tested);assert.equal(receipt.late.restored,true);assert.equal(game.records.at(-1).type,'result');assert.equal(game.records.at(-1).state.actor,null);receipt.terminalWinner=game.witness.winner;receipt.scope='Undo API negative diagnostic only; mark/restore are explicit controls, not standard source actions or admission/game credit';fs.mkdirSync(process.env.INACTIVE_PHASE_SOURCE_RESULTS,{recursive:true});fs.writeFileSync(path.join(process.env.INACTIVE_PHASE_SOURCE_RESULTS,'undo-api-negative.json'),JSON.stringify({receipt,game},null,2));
});

test('synthetic closed195 eligibility never authorizes Sentinel or altered profiles',()=>{
    require('../../../engine/env');const {EventEmitter}=require('node:events'),registry=require('../../../forceteki/build/server/game/cards/Index').cards;
    const hp=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../forceteki/test/json/Card/helgait#dooku-was-a-visionary.json'))),ap=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../forceteki/test/json/Card/advantage.json'))),mp=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../forceteki/test/json/Card/mandalorian.json'))),game=new EventEmitter(),who={id:'p1'};
    game.isUndoEnabled=false;game.state={allCards:['helgait','token']};game.ongoingEffectEngine={effects:[]};let reviewedAdvantage=ap;game.cardDataGetter={getCardSync:()=>reviewedAdvantage};
    const source=Object.create(registry.get(hp.id).prototype);Object.defineProperties(source,Object.fromEntries(Object.entries({uuid:'helgait',game,cardData:hp,internalName:hp.internalName,owner:who,controller:who,zoneName:'hand',isUnit:()=>true,isToken:()=>false,isLeader:()=>false,getOngoingEffects:()=>[]}).map(([key,value])=>[key,{value,writable:true,configurable:true}])));
    let effects=[],target={uuid:'token',game,cardData:mp,internalName:'mandalorian',owner:who,controller:who,zoneName:'outsideTheGame',isToken:()=>true,isForceToken:()=>false,isUnit:()=>true,getOngoingEffects:()=>effects};
    game.getFromId=id=>id==='helgait'?source:target;const eg={started:false,game,ids:['p1','p2'],seatOf:id=>id,isActionWindow:()=>true};leaf.observeInactivePhaseKeywords(eg);const players={p1:{hand:[{id:'c0',name:hp.internalName,setCode:'ASH_195'}]},p2:{hand:[]}};
    assert.deepEqual(leaf.inactivePhaseKeywordProjection(eg,players).inactiveAllocatedCards[0].phaseKeywords,{});
    effects=[{type:'gainKeyword',duration:'untilEndOfPhase',source}];assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/unproved inactive keyword origin/,'Physical195 cannot authorize Sentinel');effects=[];
    source.cardData={...hp,keywords:['sentinel']};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/complete allocated Helgait profile/);source.cardData=hp;
    source.setupCardAbilities=()=>{};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/closed Helgait registration/);delete source.setupCardAbilities;
    reviewedAdvantage={...ap,types:['token','unit']};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/reviewed raw Advantage definition/);reviewedAdvantage=ap;
    target.controller={id:'p2'};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/inactive physical control transfer/);target.controller=who;
    const advantage=Object.create(registry.get(ap.id).prototype);Object.defineProperties(advantage,Object.fromEntries(Object.entries({uuid:'token',game,cardData:ap,internalName:'advantage',owner:who,controller:who,zoneName:'outsideTheGame',isToken:()=>true,isForceToken:()=>false,isUpgrade:()=>true,isAttached:()=>false,getOngoingEffects:()=>effects}).map(([key,value])=>[key,{value,writable:true,configurable:true}])));target=advantage;
    assert.equal(leaf.inactivePhaseKeywordProjection(eg,players).inactiveAllocatedCards[0].setCode,'TOKEN_ADVANTAGE');advantage.cardData={...ap,power:2};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/complete detached Advantage profile/);advantage.cardData=ap;effects=[{type:'modifyStats',duration:'untilEndOfPhase'}];assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/unrepresented retired Advantage effect state/);effects=[];
    source.controller={id:'p2'};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/allocated inventory source control transfer/);
});
test('actual195 six-token expiry and both091 coexistence orders retain exact identities',{skip:!process.env.INACTIVE_INVENTORY_195_DRIVER},async()=>{
    assert.ok(process.env.INACTIVE_INVENTORY_195_POOL);assert.ok(process.env.INACTIVE_INVENTORY_195_PROTOCOL);assert.ok(process.env.INACTIVE_INVENTORY_195_OUT);
    const {run195}=require(process.env.INACTIVE_INVENTORY_195_DRIVER),result=await run195({holocronRoot:path.resolve(__dirname,'../../..'),poolPath:process.env.INACTIVE_INVENTORY_195_POOL,protocolPath:process.env.INACTIVE_INVENTORY_195_PROTOCOL,outDir:process.env.INACTIVE_INVENTORY_195_OUT});assert.equal(result.results.length,6);for(const r of result.results){assert.ok(r.winner);assert.equal(r.retiredAdvantages.length,6);assert.ok(r.paid.some(p=>p.code==='ASH_195'&&p.paid===9));}
});

test('routing hints require strict observed profiles for all four physical sources',()=>{
 require('../../../engine/env');const {EventEmitter}=require('node:events'),registry=require('../../../forceteki/build/server/game/cards/Index').cards;
 const names=['buy-time','helgait#dooku-was-a-visionary','razor-crest#outfitted-armament','full-of-surprises'],tokens=['shield','experience','advantage','weakness'],raw=n=>JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../forceteki/test/json/Card/'+n+'.json'))),tokenProfiles=tokens.map(raw),who={id:'p1'};
 for(const name of names){const profile=raw(name),game=new EventEmitter();game.isUndoEnabled=false;game.state={allCards:['source']};game.ongoingEffectEngine={effects:[]};game.cardDataGetter={getCardSync:id=>tokenProfiles.find(p=>p.id===id)};
  let source={uuid:'source',internalName:'unrelated',cardData:{id:'unrelated'},owner:who,controller:who,zoneName:'hand'};game.getFromId=()=>source;const eg={started:false,game,ids:['p1','p2'],seatOf:id=>id,isActionWindow:()=>true};assert.equal(leaf.hasInactiveInventorySource(eg),false);
  const code=profile.setId.set+'_'+String(profile.setId.number).padStart(3,'0');
  for(const zone of ['hand','deck','discard']){source=Object.create(registry.get(profile.id).prototype);Object.defineProperties(source,Object.fromEntries(Object.entries({uuid:'source',game,cardData:profile,internalName:profile.internalName,owner:who,controller:who,zoneName:zone,isUnit:()=>profile.types.includes('unit'),isToken:()=>false,isLeader:()=>false,isEvent:()=>profile.types.includes('event'),isUpgrade:()=>false,getOngoingEffects:()=>[]}).map(([k,value])=>[k,{value,writable:true,configurable:true}])));assert.equal(leaf.hasInactiveInventorySource(eg),true);assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,{}),/preplay observation missing/);}
  leaf.observeInactivePhaseKeywords(eg);const players={p1:{hand:[{id:'c0',name:profile.internalName,setCode:code}]},p2:{hand:[]}};assert.deepEqual(leaf.inactivePhaseKeywordProjection(eg,players),{inactivePhaseKeywordStateVersion:1,inactiveAllocatedCards:[]});
  if(['ASH_172','ASH_232'].includes(code)){source.setupCardAbilities=()=>{};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/registration methods/);delete source.setupCardAbilities;source.cardData={...profile,unknown:true};assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/complete allocated/);source.cardData=profile;const get=game.cardDataGetter.getCardSync;game.cardDataGetter.getCardSync=id=>({...get(id),power:999});assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/reviewed raw token/);game.cardDataGetter.getCardSync=get;}
  for(const hint of [{id:profile.id},{internalName:profile.internalName},{setId:profile.setId},{setCodes:[profile.setId]},{setCode:code}]){source={uuid:'source',owner:who,controller:who,cardData:hint,internalName:'foreign',zoneName:'hand'};assert.equal(leaf.hasInactiveInventorySource(eg),true);assert.throws(()=>leaf.inactivePhaseKeywordProjection(eg,players),/complete allocated/);}
 }
});
test('actual paid172 Shield defeat and all four232 token returns preserve retired identities',{skip:!process.env.INACTIVE_INVENTORY_FOUR_DRIVER},async()=>{
 for(const n of ['INACTIVE_INVENTORY_FOUR_POOL','INACTIVE_INVENTORY_FOUR_DEPS','INACTIVE_INVENTORY_FOUR_OUT'])assert.ok(process.env[n],n);
 const options={holocronRoot:path.resolve(__dirname,'../../..'),poolPath:process.env.INACTIVE_INVENTORY_FOUR_POOL,dependencies:process.env.INACTIVE_INVENTORY_FOUR_DEPS,outDir:process.env.INACTIVE_INVENTORY_FOUR_OUT};
 // Each external producer has its own CommonJS graph; a previous adapter must
 // never supply this run's captured state functions through a cached harness.
 require('node:child_process').execFileSync(process.execPath,['-e',"require(process.env.INACTIVE_INVENTORY_FOUR_DRIVER).runFour(JSON.parse(process.env.FOUR_RUN_OPTIONS)).catch(e=>{console.error(e);process.exitCode=1;})"],{env:{...process.env,FOUR_RUN_OPTIONS:JSON.stringify(options)},stdio:'pipe'});const r=JSON.parse(fs.readFileSync(path.join(options.outDir,'result.json')));assert.equal(r.results.length,10);assert.equal(r.results.filter(x=>x.kind==='172-paid-saboteur'&&x.paid===4).length,2);for(const x of r.results){assert.ok(x.winner);assert.deepEqual(x.retired.phaseKeywords,{});}
});
