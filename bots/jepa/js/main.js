#!/usr/bin/env node
'use strict';
/**
 * The JavaScript JEPA bot as a bot program (protocol v2 over stdio), with jepa_bot.py's options:
 *
 *   node bots/jepa/js/main.js --model bots/jepa/models/tx-t10.safetensors --window-model bots/jepa/models/tx-t10-e.safetensors \
 *       --window-horizon s --follow-horizon s --mix 0 --resource c-clock --score plan --plan-model bots/jepa/models/tx-t10.safetensors \
 *       --plan gate=0.04 --name jepa-tx-gate-js
 *
 * Card data comes from SWU_CARD_DATA (default forceteki/test/json), as the Python bot reads it.
 */

const fs = require('fs');
const path = require('path');
const { serve } = require('../../../engine/stdio');
const { JepaBot, loadModel, cardTables } = require('./jepa');

function parseArgs(argv) {
    const a = { model: path.join(__dirname, '..', 'models', 'jepa-v1.safetensors'), mix: 0.5, temp: 0, name: 'jepa', score: 'imagined', plan: '',
        resource: null, windowModel: null, planModel: null, windowHorizon: '1', followHorizon: '1' };
    const keys = { '--model': 'model', '--mix': 'mix', '--temp': 'temp', '--name': 'name', '--score': 'score', '--plan': 'plan', '--resource': 'resource',
        '--window-model': 'windowModel', '--plan-model': 'planModel', '--window-horizon': 'windowHorizon', '--follow-horizon': 'followHorizon' };
    for (let k = 0; k < argv.length; k++) {
        const key = keys[argv[k]];
        if (!key || k + 1 >= argv.length) {
            throw new Error(`unknown option or missing value: ${argv[k]}`);
        }
        a[key] = argv[++k];
    }
    a.mix = Number(a.mix);
    a.temp = Number(a.temp);
    // planner settings k=v,...: secs and gate are numbers, the rest whole numbers (jepa_bot.py main)
    a.plan = Object.fromEntries(String(a.plan).split(',').filter(Boolean).map((kv) => {
        const [k, v] = kv.split('=');
        return [k, ['secs', 'gate'].includes(k) ? Number(v) : Math.trunc(Number(v))];
    }));
    return a;
}

/** Every card file of the engine's card data, parsed (features.load_cards reads the same). */
function readCards(dir = process.env.SWU_CARD_DATA || 'forceteki/test/json') {
    const d = fs.existsSync(path.join(dir, 'Card')) ? path.join(dir, 'Card') : dir;
    if (!fs.existsSync(d)) {
        return [];
    }
    const out = [];
    for (const name of fs.readdirSync(d)) {
        try {
            out.push(JSON.parse(fs.readFileSync(path.join(d, name), 'utf8')));
        } catch {
            // a file that is not JSON is skipped, as in the Python
        }
    }
    return out;
}

function makeBot(a, cards = cardTables(readCards())) {
    const read = (p) => (p ? loadModel(fs.readFileSync(p)) : null);
    const model = read(a.model);
    return new JepaBot({ name: a.name, model, windowModel: read(a.windowModel), planModel: read(a.planModel), cards, score: a.score, mix: a.mix,
        temp: a.temp, windowHorizon: a.windowHorizon === 's' ? 's' : 1, followHorizon: a.followHorizon === 's' ? 's' : 1,
        resource: a.resource ? (['c-clock', 'rule'].includes(a.resource) ? a.resource : JSON.parse(fs.readFileSync(a.resource, 'utf8'))) : null, plan: a.plan });
}

if (require.main === module) {
    const bot = makeBot(parseArgs(process.argv.slice(2)));
    process.stderr.write(`jepa-js: ${bot.db.size} card codes, score ${bot.score}\n`);
    serve(bot).catch((e) => {
        process.stderr.write(`jepa-js: ${e.stack || e}\n`);
        process.exit(1);
    });
}

module.exports = { parseArgs, readCards, makeBot };
