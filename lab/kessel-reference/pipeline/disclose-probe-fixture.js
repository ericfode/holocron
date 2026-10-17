"use strict";
const assert = require("node:assert/strict");
const {constructProbeFixture} = require("./probe-fixture");
const {fullState, expandActions, canonicalAction} = require("../../../bots/omni/rs/state");
const numeric = (card, keyword) => card.getKeywordsWithNumericValues(keyword).reduce((sum, k) => sum + k.value, 0);
// Construction stages physical cards before genuine paid actions. The lifecycle
// owns action/trigger progression and terminal recording; the builder owns the
// disclosure chooser and source-specific assertions. Observe disclosure/reveal
// events separately from the continuation: a declined or masked selection must
// leave those events absent, while an earlier Spy-creation step stays resolved.
// A task completes only after returning to an action window, so nested prompts
// and opponent acknowledgements cannot be mistaken for a finished continuation.
async function runDiscloseLifecycle(env, pool, scenario, seed, builder) {
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
    const records = [{type: "meta", schema: "omni-rs-trace-v1", pool: pool.provenance, seed, bots: ["presence-probe", "presence-probe"],
        decks: setup.decks, scenario: scenario.name, constructionParameters: p,
        fixtureConstruction: "Normal source play, genuine leader decks/deployment, disclosed initial quiet recipients; actual paid actions and full terminal continuation"}];
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
            if (window) records.push({type: "state", step, actor: eg.seatOf(pid), state: fullState(eg, pid)});
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
            } else chosen = bot.choose({game: eg, pid, actions, rng});
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
        records.push({type: "result", step, winner: eg.winner, state: fullState(eg)});
        return {records, witness: frame.witness};
    } catch (error) {
        error.diagnostic = {records, witness: frame.witness, state: fullState(eg), taskAt};
        throw error;
    } finally {bot.close?.();}
}
const counts = aspects => aspects.reduce((out, aspect) => (out[aspect] = (out[aspect] ?? 0) + 1, out), {});
function missing(required, selected) {
    const have = counts(selected.flatMap(card => card.aspects));
    return Object.entries(counts(required)).filter(([a,n]) => (have[a] ?? 0) < n).map(([a]) => a);
}
function builder() {
    return {
        declare({p,append}) {
            const d = p.donors, out = {};
            out.ground = append(d.ground,'self',{exhausted:false,damage:2});
            out.space = append(d.space,'opponent',{exhausted:false,damage:2});
            out.attacker = append(d.attacker,'opponent',{exhausted:false});
            out.neutral = [0,1,2].map(() => append(d.neutral,'self',{zone:'hand'}));
            out.enemyHand = [0,1].map(() => append(d.neutral,'opponent',{zone:'hand'}));
            out.reveal = (p.variant === 'split-toggle' || !d.single ? p.aspects.map(a => d.singles[a]) : [d.single])
                .map(code => append(code,'self',{zone:'hand'}));
            out.fire = append(d.fire,'self',{zone:'hand'});
            out.defeat = append(d.defeat,'self',{zone:'hand'});
            return out;
        },
        activate(f) {
            const {p,declaration:d,targets:t,own,enemy,source:s} = f;
            f.focusTrigger = p.variant === 'death-positive' ? 'whenDefeated' : p.trigger;
            f.reveal = t.filter((_,i) => d.reveal.includes(i));
            f.wrong = t[d.neutral[0]];
            f.ground = t[d.ground]; f.space = t[d.space]; f.attacker = t[d.attacker];
            f.recipient = p.mode === 'event-defeat' || p.mode === 'event-damage' ? f.space : f.ground;
            f.handDonors = f.reveal.slice();
            const keep = new Set([s,...(f.focusTrigger === 'onAttack' ? [t[d.fire]] : []),...(f.focusTrigger === 'whenDefeated' ? [t[d.defeat]] : []),...f.reveal,...d.neutral.map(i => t[i])]);
            for (const card of own.hand.slice()) if (!keep.has(card)) card.moveTo('deckBottom');
            const enemyKeep = new Set(d.enemyHand.map(i => t[i]));
            for (const card of enemy.hand.slice()) if (!enemyKeep.has(card)) card.moveTo('deckBottom');
            if (p.variant === 'impossible') {
                for (const card of f.reveal) card.moveTo('deckBottom');
                f.reveal = [];
            }
            // The attack/defense cases pass a real regroup. Its real two-card
            // draw is bound to neutral cards staged before recording begins.
            for (const i of d.neutral.slice(1)) t[i].moveTo('deckTop');
            own.base.damage = 5; enemy.base.damage = 5;
            egResolve(f);
            f.disclosed = []; f.revealed = []; f.created = []; f.prompts = [];
            f.focused = false; f.masked = 0; f.acks = 0; f.declined = 0;
            f.selectSteps = 0; f.toggleSteps = 0; f.selectedHistory = [];
            f.eg.game.on('onAspectsDisclosed', event => {
                if (!f.focused || event.context.source !== s) return;
                assert.equal(event.player, own);
                const cards = event.disclosedCards ?? [];
                assert.equal(missing(p.aspects,cards).length,0,'Disclosed cards satisfy exact aspect multiplicities');
                for (const card of cards) {
                    assert.equal(card.controller,own); assert.equal(card.zoneName,'hand','Disclosure never discards the revealed card');
                }
                f.disclosed.push(cards.map(f.id));
            });
            f.eg.game.on('onCardRevealed', event => {
                if (!f.focused || event.context.source !== s) return;
                f.revealed.push((event.cards ?? []).map(f.id));
            });
            if (f.focusTrigger === 'whenPlayed' || f.focusTrigger === 'event') {
                f.play(s,null,{stage:'focus'});
            } else {
                f.play(s,null,{stage:'source'});
                if (f.focusTrigger === 'whenDefeated') {
                    f.play(t[d.defeat],s,{stage:'focus'});
                } else {
                    f.phase();
                    if (f.focusTrigger === 'onAttack') {
                        f.play(t[d.fire],enemy.base,{stage:'resource-cost'});
                        f.attack(own,s,enemy.base,{stage:'focus'});
                    } else {
                        f.attack(enemy,f.attacker,s,{stage:'focus'});
                    }
                }
            }
        },
        start(f,task) {
            if (task.stage !== 'focus') return;
            f.focused = true;
            f.before = {ownHand:f.own.hand.length,enemyHand:f.enemy.hand.length,
                ownBase:f.own.base.damage,enemyBase:f.enemy.base.damage,ready:f.ready(f.own),
                ground:{hp:f.ground.getHp(),power:f.ground.getPower(),damage:f.ground.damage,xp:f.ground.upgrades.filter(u=>u.isExperience()).map(f.id)},
                space:{hp:f.space.getHp(),power:f.space.getPower(),damage:f.space.damage,xp:f.space.upgrades.filter(u=>u.isExperience()).map(f.id)},
                resourceIds:f.own.resources.map(f.id)};
        },
        tokens(f,event) {
            if (!f.focused || event.context.source !== f.source) return;
            f.created.push({type:event.tokenType,tokens:event.generatedTokens.slice(),ids:event.generatedTokens.map(f.id)});
        },
        declared(f,task,event) {
            if (task.stage === 'focus') f.witness.observations.push({stage:'actual-attack-declaration',attacker:f.id(event.attack.attacker),defender:f.id(task.target)});
        },
        menu(f,task,actions,prompt,pid) {
            const title = prompt.menuTitle ?? '', focused = task.stage === 'focus';
            const snapshot = () => f.prompts.push({actor:f.eg.seatOf(pid),title,type:prompt.promptType ?? null,
                selected:(f.eg.player(pid).promptState.selectedCards ?? []).map(f.id),actions:actions.map(a=>canonicalAction(f.eg,a))});
            if (/target for attack/i.test(title)) return actions.find(a=>a.cardUuid===task.target.uuid);
            if (focused && f.focusTrigger==='whenDefeated' && f.source.isInPlay() && actions.some(a=>a.cardUuid===f.source.uuid)) return actions.find(a=>a.cardUuid===f.source.uuid);
            if (/no effect/i.test(title)) {
                assert.equal(task.role,'play'); assert.equal(task.card.zoneName,'hand');
                if (focused) {assert.equal(f.p.variant,'impossible'); snapshot();}
                return actions.find(a=>a.label==='Play anyway');
            }
            if (/Pausing for Disclose/i.test(title)) {
                assert.equal(pid,f.own.id); snapshot();
                if (focused) {assert.equal(f.p.variant,'impossible'); f.masked++;}
                assert.deepEqual(actions.map(a=>({label:a.label,arg:a.arg})),[{label:'Skip',arg:'done'}]);
                return actions[0];
            }
            const hand = f.own.hand, offered = actions.filter(a=>a.cardUuid && hand.some(c=>c.uuid===a.cardUuid));
            if (offered.length && pid === f.own.id && /Disclose|hidden zone/i.test(title)) {
                snapshot();
                const selected = f.own.promptState.selectedCards ?? [];
                const absent = missing(f.p.aspects,selected);
                // Actual click handler permits selected toggles and an
                // unselected card only when it contributes a missing aspect.
                const expected = hand.filter(c=>selected.includes(c)||c.aspects.some(a=>absent.includes(a))).map(c=>c.uuid).sort();
                assert.deepEqual(offered.map(a=>a.cardUuid).sort(),expected,'Complete hand click domain including selected toggles');
                assert.ok(!offered.some(a=>a.cardUuid===f.wrong.uuid),'Wrong aspect stays unselectable');
                if (!focused || f.p.variant === 'decline') {
                    if (focused) f.declined++;
                    const decline = actions.find(a=>/Choose nothing|Cancel/i.test(a.label ?? ''));
                    assert.ok(decline,'Disclosure offers a real decline action');
                    return decline;
                }
                if (f.p.variant === 'split-toggle' && f.toggleSteps < 3) {
                    const first=f.reveal[0];
                    if (f.toggleSteps===1) assert.ok(selected.includes(first),'First real click selected card');
                    if (f.toggleSteps===2) assert.ok(!selected.includes(first),'Second real click removed selected card');
                    f.toggleSteps++;f.selectSteps++;
                    return actions.find(a=>a.cardUuid===first.uuid);
                }
                if (!absent.length) {
                    const done=actions.find(a=>a.arg==='done');assert.ok(done,'Split-card All selection requires Done');return done;
                }
                const target=f.reveal.find(c=>!selected.includes(c)&&c.aspects.some(a=>absent.includes(a)));
                assert.ok(target,'Scripted physical hand contains the missing aspect');
                f.selectSteps++;
                return actions.find(a=>a.cardUuid===target.uuid);
            }
            // Reveal has an opponent-facing view-only acknowledgement.
            if (prompt.displayCards?.length || prompt.promptType === 'displayCards' || /Opponent discloses/i.test(title)) {
                snapshot();
                assert.equal(pid,f.enemy.id,'Opponent acknowledges disclosure');
                assert.ok(actions.some(a=>a.arg==='done'));
                assert.ok(actions.every(a=>a.arg==='done'),'View-only reveal does not offer another card selection');
                if (focused) f.acks++;
                return actions.find(a=>a.arg==='done');
            }
            if (focused && f.p.mode==='death-discard' && pid===f.enemy.id && actions.some(a=>a.cardUuid && f.enemy.hand.some(c=>c.uuid===a.cardUuid))) {
                snapshot();assert.equal(f.p.mode,'death-discard');
                const selected=f.enemy.promptState.selectedCards ?? [];
                if (selected.length===Math.min(2,f.enemy.hand.length)) return actions.find(a=>a.arg==='done');
                return actions.find(a=>a.cardUuid && f.enemy.hand.some(c=>c.uuid===a.cardUuid && !selected.includes(c)));
            }
            if (focused && f.p.mode==='attack-multiple-xp' && actions.some(a=>a.cardUuid)) {
                snapshot();
                assert.ok(!actions.some(a=>a.cardUuid===f.source.uuid),'Other-unit XP excludes source');
                assert.ok(!actions.some(a=>a.cardUuid===f.own.base.uuid||a.cardUuid===f.enemy.base.uuid),'XP cannot attach to bases');
                const selected=f.own.promptState.selectedCards ?? [];
                if (selected.length===2) return actions.find(a=>a.arg==='done');
                const next=[f.ground,f.space].find(c=>!selected.includes(c));
                return actions.find(a=>a.cardUuid===next.uuid);
            }
            if (task.target && actions.some(a=>a.cardUuid===task.target.uuid) && !focused) return actions.find(a=>a.cardUuid===task.target.uuid);
            if (focused && actions.some(a=>a.cardUuid===f.recipient.uuid)) {
                snapshot(); return actions.find(a=>a.cardUuid===f.recipient.uuid);
            }
            // Resolve source trigger separately when it shares a menu with
            // Restore; both are real captured registrations.
            if (actions.some(a=>/Disclose/.test(a.label ?? ''))) return actions.find(a=>/Disclose/.test(a.label));
        },
        checkTask(f,task) {
            if (task.stage !== 'focus') return;
            const positive = !['decline','impossible'].includes(f.p.variant), before=f.before, mode=f.p.mode;
            assert.equal(f.disclosed.length,positive?1:0,'Only actual disclosure resolves its event');
            assert.equal(f.acks,positive?1:0,'Exactly one opponent acknowledgement per disclosure');
            if (f.focusTrigger !== 'event' && f.p.variant==='impossible') assert.equal(f.masked,1);
            if (f.p.variant==='decline') assert.equal(f.declined,1);
            if (positive) {
                assert.deepEqual(f.revealed,f.disclosed,'The actual disclosed physical cards are revealed');
                for (const card of f.reveal) assert.equal(card.zoneName,'hand','Revealed cards remain in hand');
                if (f.p.variant==='split-toggle') assert.equal(f.toggleSteps,3);
                if (f.p.variant==='positive' && f.p.donors.single) assert.equal(f.selectSteps,1,'Single satisfying physical card completes without a second hand selection or Done');
            }
            const expectedXp=positive&&['death-xp','attack-multiple-xp'].includes(mode)?1:0;
            assert.equal(f.ground.upgrades.filter(u=>u.isExperience()).length,before.ground.xp.length+expectedXp);
            assert.equal(f.ground.getPower(),before.ground.power+expectedXp);
            assert.equal(f.ground.getHp(),before.ground.hp+expectedXp);
            if (mode==='attack-multiple-xp') assert.equal(f.space.upgrades.filter(u=>u.isExperience()).length,before.space.xp.length+(positive?1:0));
            if (mode==='play-death-sentinel'||mode==='attack-sentinel') assert.equal(f.ground.hasSomeKeyword('sentinel'),positive);
            if (mode==='defense-base-heal') assert.equal(f.own.base.damage,before.ownBase-(positive?1:0));
            if (mode==='event-defeat') assert.equal(f.space.zoneName,positive?'discard':'spaceArena');
            if (mode==='event-damage') {
                if (positive && before.space.damage+5>=before.space.hp) assert.equal(f.space.zoneName,'discard');
                else assert.equal(f.space.damage,before.space.damage+(positive?5:0));
            }
            if (mode==='death-discard') assert.equal(f.enemy.hand.length,Math.max(0,before.enemyHand-(positive?2:0)));
            if (mode==='death-draw'||mode==='play-draw') assert.equal(f.own.hand.length,before.ownHand-1+(positive?1:0));
            if (mode==='attack-ready-resources') assert.equal(f.ready(f.own),before.ready+(positive?Math.min(2,f.own.resources.length-before.ready):0));
            const spies=f.created.filter(e=>e.type==='spy').flatMap(e=>e.tokens);
            const expectedSpies=mode==='play-three-spies'?(positive?3:0):mode==='death-ready-spy'?(positive?1:0):mode==='event-two-spies'?1+(positive?1:0):0;
            assert.equal(spies.length,expectedSpies);
            assert.equal(new Set(spies.map(f.id)).size,spies.length);
            for (const spy of spies) {assert.equal(spy.controller,f.own);assert.equal(spy.owner,f.own);assert.equal(spy.zoneName,'groundArena');assert.equal(spy.exhausted,mode!=='death-ready-spy');}
            if (f.focusTrigger==='event') assert.equal(f.source.zoneName,'discard');
            if (f.focusTrigger==='whenDefeated') assert.equal(f.source.zoneName,'discard');
            f.witness.observations.push({stage:'disclose-and-real-continuation-complete',mode,variant:f.p.variant,
                source:f.id(f.source),disclosed:f.disclosed,revealed:f.revealed,acks:f.acks,masked:f.masked,prompts:f.prompts,
                tokenIds:spies.map(f.id),sourceZone:f.source.zoneName,ownHand:f.own.hand.length,enemyHand:f.enemy.hand.length});
            f.focused=false;
        },
        finish(f) { assert.ok(f.witness.observations.some(o=>o.stage==='disclose-and-real-continuation-complete')); }
    };
}
function egResolve(f) { f.eg.game.resolveGameState(true); f.eg.game.continue(); }
async function fixture(env,pool,scenario,seed) {
    assert.equal(scenario.probe.family,'disclose');
    return runDiscloseLifecycle(env,pool,scenario,seed,builder());
}
module.exports={fixture,dependencies:['kessel:cards/pipeline/disclose-probes.js','lab/kessel-reference/pipeline/disclose-probe-fixture.js',
    'lab/kessel-reference/pipeline/probe-fixture.js','kessel:cards/pipeline/arena-presence-probes.js','kessel:cards/pipeline/arena-query-probes.js',
    'kessel:cards/pipeline/base-zone-probes.js','kessel:cards/pipeline/arena-token-probes.js','engine/env.js','bots/omni/rs/state.js','bots/players/index.js']};
