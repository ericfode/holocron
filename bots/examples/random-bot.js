'use strict';
// Random bot speaking the bot protocol (spec/protocol.md). The same object plays in process or as a program:
//   in process:  playGame(env, { seed, bots: [require('./bots/examples/random-bot').create(), other] })
//   as a program: register {"cmd": "node", "args": ["bots/examples/random-bot.js"]} in bots/external-bots.json
const { seededRng } = require('../../engine/rng');
const { serve } = require('../../engine/stdio');

function create(name = 'js-random') {
    let rng = null; // seeded at hello
    return {
        name,
        hello(msg) {
            rng = seededRng(msg.seed);
            return { t: 'ready', v: 2, name };
        },
        decide(msg) {
            return { t: 'act', i: Math.floor(rng() * msg.actions.length) };
        }
    };
}

module.exports = { create };
if (require.main === module) {
    serve(create(process.argv[2]));
}
