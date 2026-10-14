#!/usr/bin/env node
'use strict';
// The engine-driving half of Kessel's `cards:reference`: index the named cases and record new reference games in
// the forceteki engine. Kessel's own CLI verifies, lists, checks and imports what this writes:
//   npm run cards:reference -- check --corpus DIR, then -- import --corpus DIR   (in the Kessel checkout)
const USAGE = 'Usage: npm run kessel:reference -- index | generate --out NEW_DIR (--case ID | --card SET_NNN [--play] [--include-setup] | --behavior ID) ' +
    '[--diagnostics] [--engine-only] [--pool FILE] [--catalogue FILE] [--seed N]\n' +
    'Needs a Kessel checkout (KESSEL_DIR, default ../kessel) and the built engine (forceteki/build).';
function options(args) {
    const o = {};
    const names = { '--case': 'case', '--card': 'card', '--behavior': 'behavior', '--out': 'out', '--pool': 'pool', '--seed': 'seed', '--catalogue': 'catalogue' };
    const flags = { '--engine-only': 'engineOnly', '--include-setup': 'includeSetup', '--diagnostics': 'diagnostics', '--play': 'play' };
    while (args.length) {
        const arg = args.shift();
        if (flags[arg]) o[flags[arg]] = true;
        else if (names[arg]) { const value = args.shift(); if (!value || value.startsWith('--')) throw Error(arg + ' needs a value'); o[names[arg]] = value; }
        else throw Error('Unknown option ' + arg);
    }
    return o;
}
async function main(args) {
    const command = args.shift();
    if (!command || command === '--help' || command === 'help') return console.log(USAGE);
    const o = options(args);
    let result;
    if (command === 'index') result = require('./index').build();
    else if (command === 'generate') result = await require('./generate').generate(o);
    else throw Error(USAGE);
    console.log(JSON.stringify(result, null, 2));
}
if (require.main === module) main(process.argv.slice(2)).catch(e => { console.error(e.stack); process.exitCode = 1; });
module.exports = { main, options };
