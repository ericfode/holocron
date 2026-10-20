'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const {fixture,assertExpected,assertRegroupExpected,assertOrdinaryRegroupExpected,dependencies}=require('../pipeline/terminal-continuation-probe-fixture');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
test('terminal fixture refuses an unadmitted activation dependency before constructing a game',async()=>{
    const scenario={probe:{family:'terminal-continuation',sourceSeat:1,cardId:'JTL_104',activationCode:'ASH_151',targets:[]}};
    await assert.rejects(fixture({newGame(){throw Error('must not construct');}},{cards:[{setCode:'JTL_104'}]},scenario,1),/actual admitted definition: ASH_151/);
});
test('paid regroup construction refuses an unadmitted preparation instead of enriching its pool',async()=>{
    const scenario={probe:{family:'terminal-continuation',scenario:'expiry-cavern-regroup',sourceSeat:1,cardId:'ASH_151',activationCode:'ASH_151',preparationCode:'SHD_130',emptyDecks:true,initiallyExhaustResource:true,targets:[{code:'LAW_189'}]}};
    await assert.rejects(fixture({newGame(){throw Error('must not construct');}},{cards:[{setCode:'ASH_151'},{setCode:'LAW_189'}]},scenario,1),/actual admitted definition: SHD_130/);
});
test('terminal fixture dependency inventory binds exporter, physical source construction and planner',()=>{
    for(const file of ['engine/env.js','bots/omni/rs/state.js','bots/omni/rs/state-evidence.js','bots/omni/rs/support-state.js','lab/kessel-reference/pipeline/probe-fixture.js','kessel:cards/pipeline/terminal-continuation-probes.js'])assert.ok(dependencies.includes(file));
});
test('terminal expectations reject same-total wrong damage, owner, domain, base and unknown fields',()=>{
    const expected={winner:'opponent',terminalPromptOwner:'self',promptTitle:'Two hits',targetIndices:[0],optionalPass:false,targetDamageEvents:[5,5],targetFinalDamage:10,ownBaseFinalDamage:30};
    const w={initial:{},final:{winner:'p2',bases:[30,0],targets:[{id:'c1',damage:10}]},observations:[{stage:'post-winner-public-choice',actor:'p1',title:'Two hits',actions:[{kind:'card',card:'c1'}]}],events:[{event:'onDamageDealt',card:'c1',amount:5},{event:'onDamageDealt',card:'c1',amount:5}]};
    const context={ownSeat:'p1',enemySeat:'p2',focusOwner:'self'};
    assert.equal(assertExpected(expected,w,context).length,Object.keys(expected).length);
    for(const mutate of [x=>{x.events[0].amount=3;x.events[1].amount=7;},x=>{x.observations[0].actor='p2';},x=>{x.observations[0].actions[0].card='c2';},x=>{x.final.bases[0]=29;},x=>{x.observations[0].actions.push({kind:'button',arg:'passAbility',label:'Pass'});}]){const wrong=structuredClone(w);mutate(wrong);assert.throws(()=>assertExpected(expected,wrong,context));}
    assert.throws(()=>assertExpected({...expected,unassertedFutureField:true},w,context),/Unasserted terminal expectation/);
});
test('terminal expectations bind exact button arguments, focus departure and focus-owner hand delta',()=>{
    const expected={winner:'self',terminalPromptOwner:'opponent',promptTitle:'Optional',optionalPass:true,exactButtons:[{arg:'trigger',label:'Trigger'},{arg:'pass',label:'Pass'}],focusFinalZone:'discard',focusOwnerHandDelta:1,ownBaseFinalDamage:5,enemyBaseFinalDamage:30};
    const w={initial:{enemyHand:['c1']},final:{winner:'p1',bases:[5,30],source:{zone:'discard'},enemyHand:['c1','c2']},events:[],observations:[{stage:'post-winner-public-choice',actor:'p2',title:'Optional',actions:[{kind:'button',arg:'trigger',label:'Trigger'},{kind:'button',arg:'pass',label:'Pass'}]}]};
    const context={ownSeat:'p1',enemySeat:'p2',focusOwner:'opponent'};assertExpected(expected,w,context);
    for(const mutate of [x=>{x.observations[0].actions[0].arg='wrong';},x=>{x.final.source.zone='spaceArena';},x=>{x.final.enemyHand.pop();},x=>{x.final.bases[1]=29;}]){const wrong=structuredClone(w);mutate(wrong);assert.throws(()=>assertExpected(expected,wrong,context));}
});
test('terminal mandatory discard binds the accepted selected card to its actual departure',()=>{
    const expected={winner:'opponent',terminalPromptOwner:'self',promptTitle:'Discard',optionalPass:false,mandatoryHandDiscard:1,ownBaseFinalDamage:30};
    const w={initial:{},final:{winner:'p2',bases:[30,0],ownHand:['c2']},observations:[{stage:'post-winner-public-choice',actor:'p1',title:'Discard',actions:[{kind:'card',card:'c1'},{kind:'card',card:'c2'}],chosen:{card:'c1'},state:{ownHand:['c1','c2']}}],events:[{event:'onCardDiscarded',card:'c1',state:{winner:'p2'}}]};
    const context={ownSeat:'p1',enemySeat:'p2',focusOwner:'self'};assertExpected(expected,w,context);
    for(const mutate of [x=>{x.observations[0].chosen.card='c2';},x=>{x.events[0].card='c9';},x=>{x.events=[];}]){const wrong=structuredClone(w);mutate(wrong);assert.throws(()=>assertExpected(expected,wrong,context));}
});
test('actual admitted terminal continuations retain post-winner actors, exact actions and completed results',{
    skip:!process.env.TERMINAL_CONTINUATION_POOL||!process.env.TERMINAL_CONTINUATION_PLANS,
},async()=>{
    const {Env}=require('../../../engine/env'),{loadPool}=require('../../../bots/omni/rs/pool');
    const {verifyPreparedEngine,sourceIdentity}=require('../reference/generate');
    const engine=path.resolve(__dirname,'../../../forceteki');
    const buildReceipt=JSON.parse(fs.readFileSync(path.join(engine,'build/.swu-reference-build.json')));
    verifyPreparedEngine(buildReceipt);const before=sourceIdentity();
    const poolBytes=fs.readFileSync(process.env.TERMINAL_CONTINUATION_POOL),planBytes=fs.readFileSync(process.env.TERMINAL_CONTINUATION_PLANS);
    const pool=loadPool(process.env.TERMINAL_CONTINUATION_POOL),raw=JSON.parse(planBytes);
    const cases=Array.isArray(raw)?raw.flatMap(x=>x.cases??[x]):raw.cases;
    assert.ok(cases.length);const receipts=[],poolBefore=JSON.stringify(pool),plansBefore=JSON.stringify(raw),env=new Env();
    const output=process.env.TERMINAL_CONTINUATION_RECORDINGS;if(output)fs.mkdirSync(output,{recursive:true});
    for(const [i,c]of cases.entries())try{
        const result=await fixture(env,pool,c,210000+i);assert.ok(result.records.at(-1).winner);
        assert.ok(result.witness.observations.some(o=>o.stage==='post-winner-public-choice'));
        for(let n=0;n<result.records.length;n++)if(result.records[n].type==='state'){
            assert.equal(result.records[n+1].type,'decision');assert.equal(result.records[n+1].prompt.actionWindow,true);
            assert.equal(result.records[n].state.actor,result.records[n+1].actor);
        }
        assert.equal(result.records.at(-1).state.actor,null,'No invented action-window actor on terminal result');
        assert.deepEqual([...result.witness.expectedAssertions].sort(),Object.keys(c.expected).sort(),'Every declared expected field asserted');
        if(c.probe.scenario==='expiry-cavern-regroup')for(const mutate of [w=>{w.final.round--;},w=>{w.final.resources[0][0].exhausted=true;},w=>{w.observations=w.observations.filter(o=>o.actor!=='p2');}]){
            const wrong=structuredClone(result.witness);mutate(wrong);assert.throws(()=>assertRegroupExpected(c.expected,wrong,'p'+c.probe.sourceSeat));
        }
        if(c.probe.scenario==='ordinary-regroup-fatigue')for(const mutate of [w=>{w.final.round--;},w=>{w.final.players[0].leaderExhausted=true;},w=>{w.events=w.events.filter(e=>e.event!=='onDamageDealt');},w=>{w.final.players[0].resources.pop();}]){
            const wrong=structuredClone(result.witness);mutate(wrong);assert.throws(()=>assertOrdinaryRegroupExpected(c.expected,wrong));
        }
        const bytes=Buffer.from(result.records.map(r=>JSON.stringify(r)).join('\n')+'\n');
        receipts.push({id:c.id,decisions:result.records.filter(r=>r.type==='decision').length,winner:result.records.at(-1).winner,traceSha256:sha(bytes)});
        if(output){fs.writeFileSync(path.join(output,i+'.json'),JSON.stringify(result,null,2));fs.writeFileSync(path.join(output,i+'.jsonl.gz'),zlib.gzipSync(bytes));}
    }catch(error){if(output)fs.writeFileSync(path.join(output,i+'-failed.json'),JSON.stringify({error:error.message,stack:error.stack,diagnostic:error.diagnostic},null,2));throw error;}
    assert.equal(JSON.stringify(pool),poolBefore);assert.equal(JSON.stringify(raw),plansBefore);
    verifyPreparedEngine(buildReceipt);assert.deepEqual(sourceIdentity(),before,'Source/build/data identities remain frozen');
    if(output)fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({schema:'terminal-continuation-fixture-receipt/v1',poolSha256:sha(poolBytes),plansSha256:sha(planBytes),sourceIdentity:before,buildReceipt,receipts,admissionCredit:0},null,2));
});
