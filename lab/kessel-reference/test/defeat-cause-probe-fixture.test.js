'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const { Env } = require('../../../engine/env');
const { loadPool } = require('../../../bots/omni/rs/pool');
const { fixture, actionWindowState, assertActionWindowRecords, dependencies } = require('../pipeline/defeat-cause-probe-fixture');
const { fullState, canonicalAction, expandActions } = require('../../../bots/omni/rs/state');
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

test('immutable raw defeat-cause plans execute all actual intended effects and complete games', { skip: !process.env.DEFEAT_CAUSE_POOL || !process.env.DEFEAT_CAUSE_PLANS }, async () => {
    const poolBytes = fs.readFileSync(process.env.DEFEAT_CAUSE_POOL), planBytes = fs.readFileSync(process.env.DEFEAT_CAUSE_PLANS), pool = loadPool(process.env.DEFEAT_CAUSE_POOL), plan = JSON.parse(planBytes);
    const cases = plan.cases, beforePool = JSON.stringify(pool), beforePlan = JSON.stringify(plan), receipts = [], env = observeEnv();
    assert.equal(cases.length, 30); assert.ok(pool.cards.every(c => !Object.hasOwn(c, 'keywordValues')), 'No metadata enrichment');
    assert.equal(crypto.createHash('sha256').update(planBytes).digest('hex'), '2649d93059d030ec600b9f15196616fcd3699a34e96fcc2b80ffc9e39a2bbd9f', 'Use the immutable sealed planner objects');
    for (const [i, scenario] of cases.entries()) {
        try {
            const result = await fixture(env, pool, scenario, 419100 + i);
            assert.ok(result.records.at(-1).winner); verifyLiveProtocol(result, env); assertActionWindowRecords(result.records);
            const observation = result.witness.observations.find(o => o.stage === 'resolved-advantage'); assert.ok(observation);
            { assert.ok(result.witness.observations.some(o => o.stage === 'phase-boundary')); assert.ok(result.witness.observations.some(o => o.stage === 'recipient-attack-end')); }
            const death = result.witness.events.find(e => e.name === 'source-defeat'); assert.ok(death); assert.equal(death.sourceZone, 'discard');
            if (scenario.probe.cause === 'attack-ability-damage') { assert.notEqual(death.activeAttackId, null); assert.notEqual(death.activeAttackId, undefined); assert.equal(death.activeAttackId,0,'First real attack ID zero must not collapse to absence'); assert.equal(death.cause, 'nonCombatDamage'); }
            receipts.push({ id: scenario.id, owner: scenario.probe.owner, cause: scenario.probe.cause, recipient: scenario.probe.recipient, decline: scenario.probe.decline, winner: result.records.at(-1).winner });
            if (process.env.DEFEAT_CAUSE_RECORDINGS) { fs.mkdirSync(process.env.DEFEAT_CAUSE_RECORDINGS, { recursive: true }); fs.writeFileSync(path.join(process.env.DEFEAT_CAUSE_RECORDINGS, i + '.json'), JSON.stringify(result)); }
        } catch (error) {
            if (process.env.DEFEAT_CAUSE_RECORDINGS) { fs.mkdirSync(process.env.DEFEAT_CAUSE_RECORDINGS, { recursive: true }); fs.writeFileSync(path.join(process.env.DEFEAT_CAUSE_RECORDINGS, i + '-failed.json'), JSON.stringify({ error: error.message, stack: error.stack, diagnostic: error.diagnostic })); }
            throw error;
        }
    }
    assert.equal(JSON.stringify(pool), beforePool); assert.equal(JSON.stringify(plan), beforePlan);
    if (process.env.DEFEAT_CAUSE_RECORDINGS) fs.writeFileSync(path.join(process.env.DEFEAT_CAUSE_RECORDINGS, 'receipt.json'), JSON.stringify({ poolSha256: crypto.createHash('sha256').update(poolBytes).digest('hex'), plansSha256: crypto.createHash('sha256').update(planBytes).digest('hex'), receipts }, null, 2));
});

test('Fiend state protocol rejects manufactured post-winner windows before snapshotting',()=>{assert.throws(()=>actionWindowState({isActionWindow:()=>false},'111',1),/actual action window/);assert.throws(()=>assertActionWindowRecords([{type:'state',step:1},{type:'decision',step:1,prompt:{actionWindow:false}}]),/actual action-window/);});
test('Fiend dependencies bind terminal helper, transitive exporter and portable pure source contract',()=>{for(const p of ['lab/kessel-reference/pipeline/terminal-completion.js','bots/omni/rs/unit-entry-state.js','bots/omni/rs/state-evidence.js','kessel:crates/kessel/src/defeat_cause_contract.rs'])assert.ok(dependencies.includes(p),p);});

test('fiend rejects every immutable760 synthetic nonwindow state while retaining prior valid windows',{skip:!process.env.DEFEAT_CAUSE_PRIOR_RECORDINGS},()=>{const z=require('node:zlib'),dir=process.env.DEFEAT_CAUSE_PRIOR_RECORDINGS,files=fs.readdirSync(dir).filter(p=>/^fiend-\d+\.json\.gz$/.test(p));assert.equal(files.length,30);let rejected=0;for(const f of files){const records=JSON.parse(z.gunzipSync(fs.readFileSync(path.join(dir,f)))).records;try{assertActionWindowRecords(records);}catch(e){assert.match(e.message,/actual action-window/);rejected++;}}assert.equal(rejected,8);});

test('both-seat native Shoot First windows attribute Attack2 and Shield cancellation captures no Fiend trigger',{skip:!process.env.FIEND_FIRST_STRIKE_CASES||!process.env.FIEND_FIRST_STRIKE_POOL},async()=>{const bytes=fs.readFileSync(process.env.FIEND_FIRST_STRIKE_CASES),cases=JSON.parse(bytes),pool=loadPool(process.env.FIEND_FIRST_STRIKE_POOL),poolBefore=JSON.stringify(pool),casesBefore=JSON.stringify(cases),env=observeEnv();assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),'6ef99d494f9e22d7dc0d9f9ec1a852d83188706708ea6871868e3876d9a15087');assert.equal(cases.length,6);for(const[i,scenario]of cases.entries()){let result;try{result=await fixture(env,pool,scenario,419200+i);}catch(error){if(process.env.FIEND_FIRST_STRIKE_RECORDINGS){fs.mkdirSync(process.env.FIEND_FIRST_STRIKE_RECORDINGS,{recursive:true});fs.writeFileSync(path.join(process.env.FIEND_FIRST_STRIKE_RECORDINGS,i+'-failed.json'),JSON.stringify({error:error.message,stack:error.stack,diagnostic:error.diagnostic}));}throw error;}verifyLiveProtocol(result,env);assertActionWindowRecords(result.records);const death=result.witness.events.find(e=>e.name==='source-defeat');if(scenario.probe.expectedAmount){assert.equal(death.cause,'attack');assert.ok(result.witness.observations.some(e=>e.stage==='recipient-attack-end'));assert.ok(result.witness.events.some(e=>e.name==='advantage-created'&&e.ids.length===2));if(scenario.probe.cause==='first-strike-return')assert.ok(result.witness.events.some(e=>e.name==='first-strike-survivor'&&e.defenderDamage===4&&e.defenderHp===12&&e.sourceDamage===0));}else{assert.equal(death,undefined);const shield=result.witness.observations.find(e=>e.stage==='shield-cancels-first-strike-no-death-trigger');assert.ok(shield);assert.equal(shield.shieldZone,'outsideTheGame');assert.equal(shield.shieldAttached,false);assert.equal(shield.sourceDamage,0);assert.equal(shield.sourceAlive,true);assert.equal(shield.sourceTriggerCount,0);assert.deepEqual(shield.generatedAdvantageIds,[]);assert.ok(result.witness.events.some(e=>e.name==='first-strike-shield-removed'&&e.shield===shield.shieldId));assert.ok(!result.witness.events.some(e=>e.name==='advantage-created'));}if(process.env.FIEND_FIRST_STRIKE_RECORDINGS){fs.mkdirSync(process.env.FIEND_FIRST_STRIKE_RECORDINGS,{recursive:true});fs.writeFileSync(path.join(process.env.FIEND_FIRST_STRIKE_RECORDINGS,i+'.json'),JSON.stringify(result));}}assert.equal(JSON.stringify(pool),poolBefore);assert.equal(JSON.stringify(cases),casesBefore);});
