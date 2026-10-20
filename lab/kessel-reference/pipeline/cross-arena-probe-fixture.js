"use strict";
const assert = require("node:assert/strict");
const {constructProbeFixture} = require("./probe-fixture");
const {fullState, expandActions, canonicalAction} = require("../../../bots/omni/rs/state");
const numeric = (card, keyword) => card.getKeywordsWithNumericValues(keyword).reduce((sum, k) => sum + k.value, 0);
async function runSupportLifecycle(env, pool, scenario, seed, builder) {
    const p = scenario.probe, reverse = p.sourceSeat === 2;
    const relative = owner => reverse ? owner === "self" ? "opponent" : "self" : owner;
    const specs = [], append = (code, owner = "self", fields = {}) => {
        const printed = pool.cards.find(c => c.setCode === code);
        assert.ok(printed, code);
        const index = specs.length;
        specs.push({code, owner: relative(owner), ...(fields.zone ? {} : {arena: printed.arena}), exhausted: true, ...fields});
        return index;
    };
    const handCopy = append(p.cardId, "opponent", {zone: "hand"});
    specs[handCopy].owner = "opponent";
    const declaration = builder.declare({p, specs, append, pool});
    const ownLeader = declaration.ownLeader ?? p.donors.leader;
    const enemyLeader = declaration.enemyLeader ?? p.donors.leader;
    const construction = {...scenario, probe: {...p, cardId: p.cardId, initiative: relative("self"), targets: specs,
        leaderCode: reverse ? enemyLeader : ownLeader, enemyLeaderCode: reverse ? ownLeader : enemyLeader}};
    const setup = await constructProbeFixture(env, pool, construction, seed);
    const {eg, rng, bot, targets} = setup, own = reverse ? setup.enemy : setup.own, enemy = reverse ? setup.own : setup.enemy;
    const source = reverse ? targets[handCopy] : setup.source;
    const id = card => eg.cardId(card.uuid), live = card => card?.isUnit?.() && card.isInPlay();
    const ready = player => player.resources.filter(c => !c.exhausted).length;
    const frame = {p, eg, own, enemy, source, targets, declaration, pool, id, live, ready, numeric,
        printed: code => pool.cards.find(c => c.setCode === code), tasks: [], played: new Set(), witness: {coverageObligationIds: [], events: [], observations: []}};
    const tasks = frame.tasks;
    frame.play = (card, target = null, extra = {}) => tasks.push({role: "play", player: card.owner, card, target, ...extra});
    frame.phase = () => tasks.push({role: "phase", round: null});
    frame.deploy = player => tasks.push({role: "deploy", player, card: player.getAllDeckLeaders()[0]});
    frame.attack = (player, card, target, extra = {}) => tasks.push({role: "attack", player, card, target, ended: false, ...extra});
    builder.activate(frame);
    frame.initialShields = targets.flatMap(card => live(card) ? card.upgrades.filter(token => token.cardData.internalName === "shield").map(token => ({host: card, token, id: id(token)})) : []);
    const baseline = targets.filter(live).map(card => ({card, hp: card.getHp(), power: card.getPower(), damage: card.damage, exhausted: card.exhausted}));
    frame.baseline = baseline;
    const records = [{type: "meta", schema: "omni-rs-trace-v1", pool: pool.provenance, seed, bots: ["support-probe", "support-probe"],
        decks: setup.decks, scenario: scenario.name, constructionParameters: p,
        fixtureConstruction: "Paid Support source play, disclosed physical host/donor construction, real nested attack and full terminal continuation"}];
    let taskAt = 0, step = 0, settled = false, pendingPayment = null;
    const current = () => tasks[taskAt];
    eg.game.on("onCardPlayed", event => {
        if (settled || event.isCancelledOrReplaced) return;
        frame.played.add(event.card);
        if (pendingPayment?.card === event.card) {
            const expected = event.card.cost + 2 * pendingPayment.player.getPenaltyAspects(event.card.aspects).length;
            assert.equal(pendingPayment.ready - ready(pendingPayment.player), expected, "Exact printed/aspect payment");
            frame.witness.events.push({name: "paidPlay", card: id(event.card), amount: expected});
            pendingPayment = null;
        }
    });
    eg.game.on("onTokensCreated", event => {
        if (!settled) builder.tokens?.(frame, event);
    });
    eg.game.on("onCardDefeated", event => {
        if (!settled) frame.witness.events.push({name: "onCardDefeated", card: id(event.card)});
    });
    eg.game.on("onAttackDeclared", event => {
        const task = current();
        if(p.terminalFatigue&&settled)assert.fail('Natural fatigue continuation must never declare an attack');
        if (!settled) builder.anyDeclared?.(frame, task, event);
        if (settled || task?.role !== "attack" || event.attack.attacker !== task.card) return;
        task.before = {targetDamage: task.target.damage, targetHp: task.target.getHp(), targetPower: task.target.isUnit() ? task.target.getPower() : 0,
            attackerDamage: task.card.damage, attackerHp: task.card.getHp(), combatPower: event.attack.getAttackerCombatDamage(event.context),
            hand: task.player.hand.length, baseDamage: task.player.base.damage, defendingBaseDamage: task.target.isBase() ? task.target.damage : task.target.controller.base.damage, raid: numeric(task.card, "raid"), restore: numeric(task.card, "restore")};
        frame.witness.events.push({name: "onAttackDeclared", attacker: id(task.card), target: id(task.target), ...task.before});
        builder.declared?.(frame, task, event);
    });
    eg.game.on("onAttackEnd", event => {
        const task = current();
        if (!settled && task?.role === "attack" && event.attack.attacker === task.card) {
            task.ended = true;
            frame.witness.events.push({name: "onAttackEnd", attacker: id(task.card)});
        }
    });
    function complete(task) {
        if (task.role === "phase") return task.round != null && eg.round > task.round;
        if (task.role === "deploy") return task.card.deployed;
        if (task.role === "attack") return task.ended || task.before && !live(task.card);
        return frame.played.has(task.card);
    }
    try {
        while (!eg.over && step < 5000) {
            const pid = eg.ids.find(player => eg.legalActions(player).length);
            assert.ok(pid);
            const actions = expandActions(eg, eg.legalActions(pid)), window = eg.isActionWindow(pid), prompt = eg.player(pid).currentPrompt();
            if (window && !settled) {
                while (taskAt < tasks.length && complete(current())) {
                    builder.checkTask(frame, current());
                    taskAt++;
                }
                if (taskAt === tasks.length) {
                    builder.finish(frame);
                    settled = true;
                }
            }
            if(window){const state=fullState(eg,pid);if(settled&&p.terminalFatigue){assert.equal(state.supportGrants.length,1,'Cancelled grant survives every natural subsequent phase');frame.witness.observations.push({stage:'fatigue-continuation-action-window',round:eg.round,grants:state.supportGrants,baseDamage:[own.base.damage,enemy.base.damage]});}records.push({type:'state',step,actor:eg.seatOf(pid),state});}
            const task = current();
            if (window && task && !task.started && !settled) { task.started = true; builder.start?.(frame, task); }
            let chosen;
            if (!settled) {
                if (task.role === "phase" && task.round == null) task.round = eg.round;
                if (window) {
                    if (task.player?.id === pid && task.role !== "phase" && (task.role !== "attack" || !task.card.exhausted)) {
                        chosen = actions.find(action => action.cardUuid === task.card.uuid);
                        if (chosen && task.role === "play") pendingPayment = {card: task.card, player: task.player, ready: ready(task.player)};
                    }
                    chosen ??= actions.find(action => action.arg === "pass");
                } else {
                    chosen = builder.menu?.(frame, task, actions, prompt, pid);
                    if (task.role === "deploy") chosen = actions.find(action => /deploy/i.test(action.label ?? ""));
                    else {
                        if (task.decline) chosen = actions.find(action => action.arg === "passAbility" || action.label === "Pass" || action.label === "Choose nothing");
                        const target = task.role === "attack" ? task.before ? task.abilityTarget : task.target : task.target;
                        if (!chosen && target) chosen = actions.find(action => action.cardUuid === target.uuid);
                        if (chosen?.cardUuid && task.before) task.abilitySelected = true;
                        chosen ??= actions.find(action => action.label === "Trigger" || action.label === "Resolve" || action.label === "Resolve all" || /Saboteur|Restore/.test(action.label ?? ""));
                    }
                    chosen ??= actions.find(action => action.arg === "done");
                    chosen ??= actions.length === 1 ? actions[0] : undefined;
                }
            } else {chosen = p.terminalFatigue&&window?actions.find(a=>a.arg==='pass')??actions.find(a=>a.arg==='claimInitiative'):bot.choose({game: eg, pid, actions, rng});if(p.terminalFatigue&&window)assert.ok(chosen,'Natural fatigue continuation uses only legal Pass or Claim Initiative'); if(chosen?.arg==='passAbility'&&chosen?.label==='Pass attack')chosen=actions.find(a=>a.cardUuid)??chosen;}
            assert.ok(chosen, JSON.stringify({case: scenario.id, role: task?.role, title: prompt.menuTitle, actions: actions.map(action => canonicalAction(eg, action))}));
            records.push({type: "decision", step, actor: eg.seatOf(pid), prompt: {type: prompt.promptType ?? null, title: prompt.menuTitle ?? null,
                selected: (eg.player(pid).promptState.selectedCards ?? []).map(id), actionWindow: window},
                actions: actions.map(action => canonicalAction(eg, action)), chosen: canonicalAction(eg, chosen).key, events: []});
            eg.apply(pid, chosen, rng);
            if (!settled) builder.afterApply?.(frame, task, chosen);
            step++;
        }
        assert.ok(settled, "Focused source stages complete");
        assert.ok(eg.over, "Actual terminal result");
        frame.witness.coverageObligationIds = [...scenario.coverageObligationIds];
        if(p.terminalFatigue)frame.witness.observations.push({stage:'natural-fatigue-before-terminal-export',round:eg.round,winner:eg.winner,actionWindow:eg.ids.some(id=>eg.isActionWindow(id)),deckSizes:[own.drawDeck.length,enemy.drawDeck.length],baseDamage:[own.base.damage,enemy.base.damage]});const terminal=fullState(eg);if(p.terminalFatigue){assert.equal(eg.ids.some(id=>eg.isActionWindow(id)),false,'True terminal has no action window');assert.equal(terminal.supportGrants.length,1,'Natural fatigue terminal retains cancelled grant');assert.ok(eg.round>2);assert.ok([own,enemy].some(p=>p.drawDeck.length===0),'Terminal arises after natural deck exhaustion');frame.witness.observations.push({stage:'natural-fatigue-terminal-retained-grant',round:eg.round,winner:eg.winner,grants:terminal.supportGrants});}records.push({type:'result',step,winner:eg.winner,state:terminal});
        return {records, witness: frame.witness};
    } catch (error) {
        let state; try {state=fullState(eg);}catch(exportError){state={exportError:exportError.message};} error.diagnostic = {records, witness: frame.witness, state, taskAt};
        throw error;
    } finally {bot.close?.();}
}
// The ordinary paid-play/task runner above is adapted from the pre-migration
// support-probe-fixture runSupportLifecycle helper; this module owns its checks.
function crossBuilder(){return {
 declare({p,append}) {return {donor2:p.multipleCancellations?append(p.cardId,'self',{zone:'hand'}):null,host:append(p.recipientCode,'self',{exhausted:false,attachments:p.recipientAttachments??[]}), defenders:(p.defenders??[]).map(t=>append(t.code,'opponent',{exhausted:!!t.exhausted,damage:t.damage??0}))};},
 activate(f){const {p,targets:t,declaration:d}=f;f.host=t[d.host];f.donor2=d.donor2==null?null:t[d.donor2];f.defenders=d.defenders.map(i=>t[i]);f.menus=[];f.supported=0;f.attackEnds=0;
 f.eg.game.on('onAttackEnd',e=>{if(!f.focusDone&&e.attack.attacker===f.host)f.attackEnds++;});
 if(p.mode==='printed'){f.play(f.source,null,{stage:'printed-play',decline:true});f.phase();f.attack(f.own,f.source,p.baseTarget?f.enemy.base:f.defenders[p.defenderIndex??0],{stage:'printed'});}
 else {f.play(f.source,null,{stage:'support'});if(p.multipleCancellations){f.phase();f.play(f.donor2,null,{stage:'support2'});}if(!p.decline&&p.expectedBase&&!p.terminalFatigue){f.phase();f.attack(f.own,f.host,p.cancelDefender?f.defenders[p.defenderIndex??0]:f.enemy.base,{stage:'followup'});if(p.cancelDefender){f.phase();f.attack(f.own,f.host,f.enemy.base,{stage:'after-cleanup'});}}}
 },
 menu(f,task,actions,prompt){const title=prompt.menuTitle??'';const cards=actions.filter(a=>a.kind==='card');f.menus.push({stage:task.stage,title,actions:actions.map(a=>canonicalAction(f.eg,a))});
 if(title.startsWith('Choose which copy of Red Leader'))return cards.find(a=>a.cardUuid===f.source.uuid);
 if(title.includes('Attack with another unit.')){if(task.stage==='printed-play')return actions.find(a=>['passAbility','done'].includes(a.arg)||['Pass','Choose nothing'].includes(a.label));assert.ok(!cards.some(a=>a.cardUuid===f.source.uuid));assert.ok(cards.some(a=>a.cardUuid===f.host.uuid),'Prospective copied cross-arena permission makes recipient selectable');if(f.p.decline)return actions.find(a=>['passAbility','done'].includes(a.arg)||['Pass','Choose nothing'].includes(a.label));return cards.find(a=>a.cardUuid===f.host.uuid);}
 if(title==='Choose a target for attack'){
 const printed=task.stage==='printed',followup=['followup','after-cleanup'].includes(task.stage);const attacker=printed?f.source:f.host;
 const expected=followup?f.defenders.filter(c=>c.isInPlay()&&(task.stage==='followup'&&f.p.cancelDefender||c.zoneName===attacker.zoneName)).concat(f.enemy.base):f.p.expectedDefenderIndices.map(i=>f.defenders[i]).concat(f.p.expectedBase?[f.enemy.base]:[]);
 assert.deepEqual(cards.map(a=>f.id(f.eg.game.allCards.find(c=>c.uuid===a.cardUuid))),expected.map(f.id),'Exact pinned engine target order and legality');
 if(!followup&&!printed){const donor=task.card;const copied=f.host.getConstantAbilities().filter(a=>a.gainAbilitySource===donor);assert.equal(copied.length,1);f.witness.observations.push({stage:'copied-registration',attacker:f.id(f.host),donor:f.id(donor),copiedTitles:copied.map(a=>a.getTitle())});}
 if(f.p.cancelDefender&&!printed&&!followup){const cancel=actions.find(a=>a.arg==='passAbility'&&a.label==='Pass attack');assert.ok(cancel,'Actual defender cancellation option');f.witness.observations.push({stage:'cancel-defender-after-grant',copied:f.host.getConstantAbilities().filter(a=>a.gainAbilitySource===f.source).map(a=>a.getTitle()),actions:actions.map(a=>canonicalAction(f.eg,a))});return cancel;}
 const target=followup?task.target:f.p.baseTarget?f.enemy.base:f.defenders[f.p.defenderIndex??0];return actions.find(a=>a.cardUuid===target.uuid);
 }
 return actions.find(a=>a.arg==='all'&&/^Resolve all/.test(a.label??''))??actions.find(a=>['Trigger','Resolve'].includes(a.label));
 },
 anyDeclared(f,task,event){if(task.stage!=='support'||event.attack.attacker!==f.host)return;f.supported++;const target=event.attack.getAllTargets()[0];assert.equal(target,f.p.baseTarget?f.enemy.base:f.defenders[f.p.defenderIndex??0]);f.supportBefore={damage:target.damage,power:f.host.getPower(),retaliation:target.isUnit()?target.getPower():0,attackerDamage:f.host.damage};f.witness.events.push({name:'supported-declared',attacker:f.id(f.host),target:f.id(target),donor:f.id(f.source)});},
 checkTask(f,task){if(task.stage==='support2'){assert.equal(f.source.zoneName,'discard','Normal unique replacement defeats departed first donor');assert.equal(f.donor2.zoneName,'spaceArena');const grants=fullState(f.eg).supportGrants;assert.equal(grants.length,2,'Two paid cancellations retain two distinct source rows');assert.deepEqual(grants.map(g=>g.donor),[f.id(f.source),f.id(f.donor2)]);assert.ok(grants.every(g=>g.target===f.id(f.host)));f.witness.observations.push({stage:'two-cancelled-grants-after-unique-departure',grants,donorZone:f.source.zoneName});}
 if(task.stage==='support'){if(!f.host.isInPlay())f.tasks.splice(f.tasks.indexOf(task)+1);assert.equal(f.source.zoneName,'spaceArena');assert.equal(f.supported,f.p.decline||f.p.noEligibleSupport||f.p.cancelDefender?0:1);if(f.p.noEligibleSupport){assert.equal(f.host.getConstantAbilities().filter(a=>a.gainAbilitySource===f.source).length,0,'No early grant is installed when prospective attacker has no target');assert.ok(!f.menus.some(m=>m.title.includes('Attack with another unit.')),'No eligible pre-grant attacker: Support selector never opens');f.witness.observations.push({stage:'no-eligible-support-before-grant',host:f.id(f.host),exhausted:f.host.exhausted,attached:f.host.upgrades.map(f.id),menus:f.menus});}if(!f.p.decline&&!f.p.noEligibleSupport&&!f.p.cancelDefender){assert.equal(f.attackEnds,1);const target=f.p.baseTarget?f.enemy.base:f.defenders[f.p.defenderIndex??0];if(target.isInPlay())assert.equal(target.damage,f.supportBefore.damage+f.supportBefore.power,'Actual supported combat deals recipient power');if(f.host.isInPlay()){assert.equal(f.host.damage,f.supportBefore.attackerDamage+f.supportBefore.retaliation);assert.equal(f.host.getConstantAbilities().filter(a=>a.gainAbilitySource===f.source).length,0,'Copied registration cleaned after attack');}}if(f.p.cancelDefender){const grants=fullState(f.eg).supportGrants;assert.equal(grants.length,1);assert.equal(grants[0].target,f.id(f.host));assert.equal(grants[0].donor,f.id(f.source));assert.equal(f.host.exhausted,false,'Cancelled attack pays no exhaust');f.witness.observations.push({stage:'cancelled-grant-action-window',grants});}f.witness.observations.push({stage:'support-complete',supported:f.supported,menus:f.menus});}
 if(['followup','after-cleanup'].includes(task.stage)) {if(task.target.isBase()||task.target.isInPlay())assert.equal(task.target.damage-task.before.targetDamage,task.before.combatPower);assert.equal(fullState(f.eg).supportGrants.length,0,'Completed actual attack globally expires retained rows');if(f.host.isInPlay())for(const donor of [f.source,f.donor2].filter(Boolean))assert.equal(f.host.getConstantAbilities().filter(a=>a.gainAbilitySource===donor).length,0);f.witness.observations.push({stage:task.stage==='followup'?'retained-cross-attack-cleanup':'later-normal-attack-no-grant',grants:fullState(f.eg).supportGrants});if(!f.host.isInPlay())f.tasks.splice(f.tasks.indexOf(task)+1);}
 if(task.stage==='printed'){if(task.target.isBase()||task.target.isInPlay())assert.equal(task.target.damage-task.before.targetDamage,task.before.combatPower);f.witness.observations.push({stage:'printed-complete',menus:f.menus});}
 },finish(f){f.focusDone=true;}
};}
// Construction donors are deliberately limited to plain intrinsic Sentinel units.
// Card-data keyword mentions alone do not establish an intrinsic keyword.
function sentinelDonor(card){return card?.types?.length===1&&card.types[0]==='unit'&&card.keywords?.length===1&&card.keywords[0]==='sentinel'&&/^Sentinel(?: \([^()]*\))?\.?$/.test(card.text??'');}
function normalize(p,pool){if(p.recipientCode)return p;const arena=p.mode==='printed'?'space':p.recipientArena, sab=p.scenario==='saboteur', ownSent=p.scenario==='both-sentinels'||p.scenario===arena+'-sentinel';const defs=[];for(const a of ['ground','space']){if(['cross-unit-only','entrenched-only-cross-defender','wicket-only-cross-defender'].includes(p.scenario)&&a===arena)continue;defs.push({code:p[a+'Code']});if(p.scenario==='both-sentinels'||p.scenario===a+'-sentinel')defs.push({code:p[a+'SentinelCode']});}const ordered=defs.map((d,i)=>i);const eligible=ordered.filter(i=>!ownSent||sab||sentinelDonor(pool.cards.find(c=>c.setCode===defs[i].code)));return {...p,sourceSeat:p.owner+1,recipientCode:p.scenario==='wicket-only-cross-defender'?(p.wicketCode??'ASH_034'):sab?p.saboteurCode:p[p.recipientArena+'Code'],defenders:defs,expectedDefenderIndices:eligible,noEligibleSupport:['entrenched-only-cross-defender','wicket-only-cross-defender'].includes(p.scenario),recipientAttachments:p.scenario==='entrenched-only-cross-defender'?[{code:'SOR_072'}]:[],expectedBase:['entrenched-only-cross-defender','wicket-only-cross-defender'].includes(p.scenario)?false:!ownSent||sab,defenderIndex:p.cancelDefender?eligible.find(i=>pool.cards.find(c=>c.setCode===defs[i].code).arena!==arena):eligible[0],decline:p.scenario==='decline',donors:{leader:pool.cards.find(c=>c.types.includes('leader')).setCode}};}
async function fixture(env,pool,scenario,seed){scenario={...scenario,probe:normalize(scenario.probe,pool)};assert.equal(scenario.probe.family,'cross-arena');return runSupportLifecycle(env,pool,scenario,seed,crossBuilder());}
module.exports={fixture,dependencies:['kessel:cards/pipeline/cross-arena-probes.js','lab/kessel-reference/pipeline/cross-arena-probe-fixture.js','lab/kessel-reference/pipeline/probe-fixture.js','engine/env.js','bots/omni/rs/state.js','bots/players/index.js']};
