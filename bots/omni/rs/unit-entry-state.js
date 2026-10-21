'use strict';
/** Inactive entry grants are real lasting effects on a physical card, not an arena buff.
 * Read the engine's attached effects; do not infer history from a defeat or card type. */
function unitEntryProjection(eg, phaseStats, support, ref, inactivePhaseCompanion = null) {
    const rows = [];
    for (const card of eg.game.allCards) {
        if (['groundArena', 'spaceArena'].includes(card.zoneName)) continue;
        const effects = card.getOngoingEffects?.() ?? [];
        if (!effects.some(e => e.duration === 'untilEndOfPhase' && e.type === 'modifyStats')) continue;
        const stats = phaseStats(card, support);
        // Keep the original keyword guard unless a current private source receipt
        // proves these exact keywords on this same allocated physical card.
        const provenKeywords = stats.phaseKeywords && inactivePhaseCompanion !== null &&
            require('./inactive-phase-keyword-state').validatesInactivePhaseKeywordCompanion(inactivePhaseCompanion, eg, card, stats.phaseKeywords);
        if (!card.isUnit?.() || !stats.phaseStats || (stats.phaseKeywords && !provenKeywords) || stats.phaseLostKeywords ||
            !Number.isSafeInteger(stats.phaseStats.power) || stats.phaseStats.power < 1 || stats.phaseStats.power > 65535 || stats.phaseStats.hp !== 0) {
            throw new Error('Unsupported inactive unit-entry stat effect on ' + card.internalName);
        }
        if (card.zoneName !== 'discard' && !(card.zoneName === 'outsideTheGame' && card.isToken?.())) {
            throw new Error('Unsupported inactive unit-entry target zone ' + card.zoneName);
        }
        const owner = eg.seatOf(card.owner?.id), controller = eg.seatOf(card.controller?.id);
        if (!['p1', 'p2'].includes(owner) || !['p1', 'p2'].includes(controller)) throw new Error('Invalid inactive unit-entry ownership');
        const descriptor = { ...ref(eg, card), owner, controller };
        if (!/^c(?:0|[1-9][0-9]*)$/.test(descriptor.id) || !descriptor.setCode) throw new Error('Invalid inactive unit-entry physical identity');
        rows.push({ card: descriptor, power: stats.phaseStats.power, hp: 0 });
    }
    rows.sort((a, b) => Number(a.card.id.slice(1)) - Number(b.card.id.slice(1)));
    if (new Set(rows.map(row => row.card.id)).size !== rows.length) throw new Error('Duplicate inactive unit-entry identity');
    return { unitEntryStateVersion: 1, inactiveUnitEntryStats: rows };
}
module.exports = { unitEntryProjection };
