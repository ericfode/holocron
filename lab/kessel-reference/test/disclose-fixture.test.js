"use strict";
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
// Load the actual private chooser without starting or substituting an engine game.
// These are protocol unit checks; the coordinator owns real engine recordings.
const file = path.join(__dirname, '../pipeline/disclose-probe-fixture.js');
const fixtureModule = {exports: {}};
new Function('require', 'module', 'exports', fs.readFileSync(file, 'utf8') +
    '\nmodule.exports.testInternals = {builder, missing};')((name) => {
    if (name === 'node:assert/strict') return assert;
    if (name === './probe-fixture') return {};
    if (name === '../../../bots/omni/rs/state') return {canonicalAction: (_eg, action) => action};
    throw new Error('Unexpected fixture dependency: ' + name);
}, fixtureModule, fixtureModule.exports);
const {builder, missing} = fixtureModule.exports.testInternals;
const card = (uuid, aspects) => ({uuid, aspects});
function selection(required, reveal, variant = 'positive') {
    const wrong = card('wrong', []), own = {id: 'self', hand: [...reveal, wrong], promptState: {selectedCards: []}};
    const f = {p: {aspects: required, variant}, own, enemy: {id: 'enemy'}, reveal, wrong,
        declined: 0, prompts: [], id: c => c.uuid, selectSteps: 0, toggleSteps: 0,
        eg: {seatOf: p => p === 'self' ? 1 : 2, player: () => own}};
    return {f, choose: (actions, title = 'Disclose') => builder().menu(f, {stage: 'focus'}, actions, {menuTitle: title}, 'self')};
}
test('all aspects are a multiset, including double icons on one physical card', () => {
    assert.deepEqual(missing(['vigilance', 'vigilance'], [card('a', ['vigilance'])]), ['vigilance']);
    assert.deepEqual(missing(['vigilance', 'vigilance'], [card('a', ['vigilance', 'vigilance'])]), []);
    assert.deepEqual(missing(['command', 'command', 'heroism'], [card('a', ['command']), card('b', ['command', 'heroism'])]), []);
});
test('real selected membership drives toggles and Done after a complete split selection', () => {
    const a = card('a', ['vigilance']), b = card('b', ['vigilance']);
    const {f, choose} = selection(['vigilance', 'vigilance'], [a, b], 'split-toggle');
    const actions = [{cardUuid: 'a'}, {cardUuid: 'b'}, {arg: 'done'}];
    assert.equal(choose(actions).cardUuid, 'a');
    f.own.promptState.selectedCards = [a];
    assert.equal(choose(actions).cardUuid, 'a');
    f.own.promptState.selectedCards = [];
    assert.equal(choose(actions).cardUuid, 'a');
    f.own.promptState.selectedCards = [a];
    assert.equal(choose(actions).cardUuid, 'b');
    f.own.promptState.selectedCards = [a, b];
    assert.equal(choose(actions).arg, 'done');
    assert.equal(f.toggleSteps, 3);
});
test('decline and masked no-match use real buttons without disclosure events', () => {
    const {f, choose} = selection(['vigilance'], [card('a', ['vigilance'])], 'decline');
    assert.equal(choose([{cardUuid: 'a'}, {arg: 'done', label: 'Choose nothing'}]).label, 'Choose nothing');
    assert.equal(f.declined, 1);
    f.p.variant = 'impossible'; f.masked = 0;
    const skip = {arg: 'done', label: 'Skip'};
    assert.equal(choose([skip], 'Pausing for Disclose'), skip);
    assert.equal(f.masked, 1);
});
test('opponent-facing disclosure is view-only acknowledgement', () => {
    const {f} = selection(['heroism'], [card('a', ['heroism', 'heroism'])]);
    f.acks = 0;
    const done = {arg: 'done'};
    assert.equal(builder().menu(f, {stage: 'focus'}, [done], {menuTitle: 'Opponent discloses Heroism', displayCards: [{}]}, 'enemy'), done);
    assert.equal(f.acks, 1);
    assert.throws(() => builder().menu(f, {stage: 'focus'}, [done, {cardUuid: 'a'}], {menuTitle: 'Opponent discloses Heroism', displayCards: [{}]}, 'enemy'), /View-only reveal/);
});
