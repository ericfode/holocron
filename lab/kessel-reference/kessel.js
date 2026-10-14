'use strict';
// The reference generator and the probe fixtures drive the forceteki engine from Holocron, but the case index,
// the corpus library, the planners, the review and coverage code and the card catalogue belong to Kessel
// (ericfode/kessel). This finds a Kessel checkout: KESSEL_DIR, or a `kessel` folder next to this repository.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const holocron = path.resolve(__dirname, '../..');

function kesselDir() {
    const dir = path.resolve(process.env.KESSEL_DIR ?? path.join(holocron, '..', 'kessel'));
    if (!fs.existsSync(path.join(dir, 'cards', 'reference', 'library.js')))
        throw new Error(`This needs a Kessel checkout (ericfode/kessel): set KESSEL_DIR (looked in ${dir})`);
    return dir;
}
const hasKessel = () => { try { return !!kesselDir(); } catch { return false; } };
/** A path inside Kessel, named the way Kessel names it (e.g. 'cards/reference/library'). */
const kesselPath = (relative) => path.join(kesselDir(), relative);
const kessel = (relative) => require(kesselPath(relative));

/** The forceteki commit a repository pins, or null outside Git. */
function pinnedEngine(repo) {
    try { return execFileSync('git', ['-C', repo, 'ls-tree', 'HEAD', 'forceteki'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).match(/commit ([a-f0-9]+)/)?.[1] ?? null; }
    catch { return null; }
}

module.exports = { holocron, kesselDir, hasKessel, kesselPath, kessel, pinnedEngine };
