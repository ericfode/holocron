'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {validateExecutorUpgradeCountProbe,executorUpgradeCountFixture,actionWindowState,assertActionWindowRecords,dependencies}=require('../pipeline/executor-upgrade-count-probe-fixture');
const empty=owner=>({family:'executor-upgrade-count',cardId:'ASH_197',owner,scenario:'empty-normal-play',resourceCount:30,leaderCode:'SOR_014',baseCode:'SOR_023',baseDamage:0,expectedFocusPlayCost:12,design:{units:[],initialAttachments:[],plan:[{code:'ASH_197'}],expected:{sourcePower:5,sourceHp:12,ownAdvantageRecipients:[],sourceExhausted:true}}});
test('exact closed construction accepts either seat without mutating input',()=>{
 for(const owner of [0,1]){const probe=empty(owner),before=structuredClone(probe);assert.equal(validateExecutorUpgradeCountProbe(probe),probe);assert.deepEqual(probe,before);}
});
test('unknown family, source, scenario and seat are rejected',()=>{
 for(const change of [{family:'other'},{cardId:'JTL_090'},{scenario:'foreign-attachment'},{owner:2}])assert.throws(()=>validateExecutorUpgradeCountProbe({...empty(0),...change}),/Unsupported/);
 assert.throws(()=>validateExecutorUpgradeCountProbe(null),/Unsupported/);
});
test('resource and aspect setup cannot silently change',()=>{
 for(const change of [{resourceCount:12},{leaderCode:'SOR_001'},{baseCode:'SOR_025'},{baseDamage:24},{expectedFocusPlayCost:8}])assert.throws(()=>validateExecutorUpgradeCountProbe({...empty(0),...change}),/Unsupported/);
});
test('nested plan, expectations and attachment inventories remain packet bound',()=>{
 for(const mutate of [p=>p.design.plan.push({code:'TWI_174'}),p=>p.design.expected.sourcePower=6,p=>p.design.initialAttachments.push({host:'source',token:'shield'}),p=>p.design.units.push({key:'foreign',code:'SOR_095',owner:'enemy'})]){const p=empty(0);mutate(p);assert.throws(()=>validateExecutorUpgradeCountProbe(p),/Unsupported/);}
});
test('unknown data fields fail before engine construction',async()=>{
 const probe=empty(0);probe.synthetic=true;
 await assert.rejects(executorUpgradeCountFixture({newGame(){throw Error('engine touched');}},null,{probe},'test'),/Unsupported or changed/);
});

const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {Env}=require('../../../engine/env');
const {loadPool}=require('../../../bots/omni/rs/pool');
const {fullState,canonicalAction,expandActions}=require('../../../bots/omni/rs/state');
function observeEnv() {
    const env = new Env(), newGame = env.newGame.bind(env);
    env.newGame = (...args) => {
        const eg = newGame(...args), apply = eg.apply.bind(eg), calls = [];
        env.latest = { eg, calls };
        eg.apply = (pid, chosen, ...rest) => {
            calls.push({ actor: eg.seatOf(pid), window: eg.isActionWindow(pid), over: eg.over,
                actions: expandActions(eg, eg.legalActions(pid)).map(a => canonicalAction(eg, a)), chosen: canonicalAction(eg, chosen).key });
            return apply(pid, chosen, ...rest);
        };
        return eg;
    };
    return env;
}
function verifyLiveProtocol(result, env) {
    const decisions = result.records.filter(r => r.type === 'decision'), states = result.records.filter(r => r.type === 'state');
    const calls = env.latest.calls.slice(-decisions.length);
    assert.equal(calls.length, decisions.length);
    for (let i = 0; i < decisions.length; i++) {
        assert.equal(decisions[i].actor, calls[i].actor); assert.equal(decisions[i].prompt.actionWindow, calls[i].window);
        assert.deepEqual(decisions[i].actions, calls[i].actions, 'Complete canonical legal choices must match the live engine before each apply');
        assert.equal(decisions[i].chosen, calls[i].chosen);
        if (calls[i].over) assert.equal(calls[i].window, false, 'Drain committed choices without opening another action turn');
    }
    for (const state of states) assert.equal(calls[state.step]?.window, true, 'Every state record certifies an independently observed actual action window');
    assert.equal(states.length, calls.filter(c => c.window).length);
    assert.deepEqual(result.records.at(-1).state, fullState(env.latest.eg), 'Completed result retains actual final state after drain');
    const completion = result.witness.terminalCompletion ?? result.witness.observed.terminalCompletion;
    assert.equal(completion.postWinnerChoices, calls.filter(c => c.over).length);
    for (const pid of env.latest.eg.ids) assert.ok(!env.latest.eg.legalActions(pid).length || env.latest.eg.isActionWindow(pid), 'No pending committed terminal choices');
    result.witness.protocolAudit = { decisions: decisions.length, states: states.length, allStateRecordsAtActualWindows: true, completeCanonicalChoiceSets: true, postWinnerChoices: completion.postWinnerChoices };
}

test('Executor state protocol rejects post-winner nonwindows before snapshotting',()=>{assert.throws(()=>actionWindowState({isActionWindow:()=>false},'111',1),/actual action window/);assert.throws(()=>assertActionWindowRecords([{type:'state',step:1},{type:'decision',step:1,prompt:{actionWindow:false}}]),/actual action-window/);});
test('Executor dependency inventory binds source contract and transitive unit-entry exporter',()=>{for(const p of ['lab/kessel-reference/pipeline/terminal-completion.js','bots/omni/rs/unit-entry-state.js','kessel:crates/kessel/src/executor_upgrade_count_contract.rs'])assert.ok(dependencies.includes(p),p);});
test('all18 immutable raw Executor cases preserve actual choice sets and action-window state protocol',{skip:!process.env.EXECUTOR_RAW_POOL||!process.env.EXECUTOR_RAW_PLANS},async()=>{const pb=fs.readFileSync(process.env.EXECUTOR_RAW_PLANS),plan=JSON.parse(pb),pool=loadPool(process.env.EXECUTOR_RAW_POOL),beforePool=JSON.stringify(pool),beforePlan=JSON.stringify(plan),env=observeEnv();assert.equal(crypto.createHash('sha256').update(pb).digest('hex'),'636ac1ac454c2f32cb6f9a0d81a506f7ff587841a4f0d9c84719e8b71bd8fc50');const cases=Array.isArray(plan)?plan:plan.cases;assert.equal(cases.length,18);for(const[i,probe]of cases.entries()){const name=probe.scenario+'-seat'+probe.owner,coverageObligationIds=['ASH_197:executor-upgrade-count:'+name],scenario={name,probe,coverageObligationIds};const result=await executorUpgradeCountFixture(env,pool,scenario,'executor-fixture-'+name);assert.deepEqual(result.witness.coverageObligationIds,coverageObligationIds);assert.notEqual(result.witness.coverageObligationIds,coverageObligationIds);assert.equal(result.witness.observed.postAction,true);assert.equal(result.records.at(-1).type,'result');verifyLiveProtocol(result,env);assertActionWindowRecords(result.records);if(process.env.EXECUTOR_RECORDINGS){fs.mkdirSync(process.env.EXECUTOR_RECORDINGS,{recursive:true});fs.writeFileSync(path.join(process.env.EXECUTOR_RECORDINGS,i+'.json'),JSON.stringify(result));}}assert.equal(JSON.stringify(pool),beforePool);assert.equal(JSON.stringify(plan),beforePlan);});

test('executor rejects every immutable760 synthetic nonwindow state while retaining prior valid windows',{skip:!process.env.EXECUTOR_PRIOR_RECORDINGS},()=>{const z=require('node:zlib'),dir=process.env.EXECUTOR_PRIOR_RECORDINGS,files=fs.readdirSync(dir).filter(p=>/^executor-\d+\.json\.gz$/.test(p));assert.equal(files.length,18);let rejected=0;for(const f of files){const records=JSON.parse(z.gunzipSync(fs.readFileSync(path.join(dir,f)))).records;try{assertActionWindowRecords(records);}catch(e){assert.match(e.message,/actual action-window/);rejected++;}}assert.equal(rejected,13);});


test('canonical generated Executor obligation IDs bind only the18 unchanged raw constructions',{skip:!process.env.EXECUTOR_COVERAGE_PLANS||!process.env.EXECUTOR_RAW_PLANS},()=>{
 const plans=JSON.parse(fs.readFileSync(process.env.EXECUTOR_COVERAGE_PLANS)),plan=plans.find(p=>p.cardId==='ASH_197'),raw=JSON.parse(fs.readFileSync(process.env.EXECUTOR_RAW_PLANS));
 assert.equal(plan.cases.length,18);assert.deepEqual(plan.cases.map(c=>c.probe),raw);
 for(const c of plan.cases){const name=c.probe.scenario+'-seat'+c.probe.owner;assert.equal(c.id,'auto/ASH_197/executor-upgrade-count-'+name);assert.deepEqual(c.coverageObligationIds,['ASH_197:executor-upgrade-count:'+name]);assert(plan.obligations.some(o=>o.id===c.coverageObligationIds[0]));assert(!plan.uncovered.some(o=>c.coverageObligationIds.includes(o.id)));}
});
test('malformed Executor construction cannot read or credit caller coverage',async()=>{
 let coverageReads=0;const scenario={probe:{...empty(0),expectedFocusPlayCost:8},get coverageObligationIds(){coverageReads++;return ['ASH_197:executor-upgrade-count:source-review'];}};
 await assert.rejects(executorUpgradeCountFixture({newGame(){throw Error('engine touched');}},null,scenario,'malformed'),/Unsupported/);assert.equal(coverageReads,0);
});
test('failed physical Executor assertion cannot read or credit caller coverage',{skip:!process.env.EXECUTOR_RAW_POOL},async()=>{
 const pool=loadPool(process.env.EXECUTOR_RAW_POOL),env=observeEnv(),create=env.newGame.bind(env);let coverageReads=0;
 env.newGame=(...args)=>{const eg=create(...args);eg.game.on('onCardPlayed',event=>{if(event.card?.internalName==='executor#final-destruction-of-the-alliance')event.card.getPower=()=>999;});return eg;};
 const scenario={name:'failed-physical-assertion',probe:empty(0),get coverageObligationIds(){coverageReads++;return ['ASH_197:executor-upgrade-count:empty-normal-play-seat0'];}};
 await assert.rejects(executorUpgradeCountFixture(env,pool,scenario,'failed-physical-assertion'),error=>{assert.match(error.message,/Live whole attachment inventory power/);assert.equal(error.diagnostic.observed.postAction,undefined);assert.equal(error.diagnostic.observed.coverageObligationIds,undefined);return true;});assert.equal(coverageReads,0);
});
