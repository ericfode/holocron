'use strict';
const assert = require('node:assert/strict');
// A latched winner does not cancel already committed public choices. The
// recorder owns the choices; this guard never starts another action turn.
function terminalCompletion(eg, limit) {
    let latched = null, start = null, postWinnerChoices = 0;
    const actors = () => eg.ids.filter(pid => eg.legalActions(pid).length && (!eg.over || !eg.isActionWindow(pid)));
    function latch() {
        if (latched !== null) assert.equal(eg.winner, latched, 'Committed continuation changed latched winner');
        if (eg.over && latched === null) { latched = eg.winner; assert.ok(latched != null); start = { round: eg.round, phase: eg.game.currentPhase }; }
    }
    return {
        nextActor(step) {
            latch(); assert.ok(step < limit, 'Terminal completion step limit exceeded');
            const pid = actors()[0];
            if (!pid) { assert.ok(eg.over, 'No public actor before terminal winner'); return null; }
            if (eg.over) postWinnerChoices++;
            return pid;
        },
        assertComplete() {
            latch(); assert.ok(eg.over, 'Terminal winner required');
            assert.equal(actors().length, 0, 'Pending committed public choices after winner');
            return { winner: latched, winnerLatchedAt: start, completedAt: { round: eg.round, phase: eg.game.currentPhase }, postWinnerChoices };
        }
    };
}
module.exports = { terminalCompletion };
