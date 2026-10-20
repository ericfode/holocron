'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { validateProbe, resourceLayout, validateExperience, dependencies, fixture } = require('../pipeline/variable-payment-probe-fixture');
const normal = { family: 'variable-payment', cardId: 'LOF_255', owner: 0, scenario: 'normal',
    paymentAmount: 3, readyAfterPlay: 9, resourceCount: 12, sourceArena: 'ground' };

test('all eight source-derived constructions validate for both physical owners', () => {
    const variants = [[0,9,'normal'],[1,9,'normal'],[3,9,'normal'],[6,9,'normal'],
        [0,0,'normal'],[2,2,'normal'],[6,6,'normal'],[3,9,'captured-source-dead']];
    for (const owner of [0,1]) for (const [paymentAmount,readyAfterPlay,scenario] of variants)
        assert.doesNotThrow(() => validateProbe({ ...normal, owner, paymentAmount, readyAfterPlay, scenario,
            ...(scenario === 'captured-source-dead' ? { snokeCode: 'SHD_037' } : {}) }));
});
test('number bounds reject fractional, negative, unaffordable and above-six choices', () => {
    for (const paymentAmount of [-1, 0.5, 7, NaN, Infinity, '3'])
        assert.throws(() => validateProbe({ ...normal, paymentAmount }));
    assert.throws(() => validateProbe({ ...normal, readyAfterPlay: 2, paymentAmount: 3 }));
    assert.throws(() => validateProbe({ ...normal, readyAfterPlay: 0, paymentAmount: 1 }));
});
test('cost-first endpoint setups and source-death donor remain explicit', () => {
    for (const patch of [{ owner: 2 }, { resourceCount: 0 }, { sourceArena: 'space' },
        { cardId: 'HMW_036' }, { scenario: 'synthetic-death' }, { snokeCode: 'SHD_037' }])
        assert.throws(() => validateProbe({ ...normal, ...patch }));
    for (const snokeCode of [undefined, 'SOR_095'])
        assert.throws(() => validateProbe({ ...normal, scenario: 'captured-source-dead', snokeCode }));
});
test('mixed physical resource layout is deterministic and not a ready prefix', () => {
    assert.deepEqual(resourceLayout(8, 3), [false,true,false,false,true,true,true,true]);
    assert.deepEqual(resourceLayout(4, 0), [true,true,true,true]);
    assert.deepEqual(resourceLayout(4, 4), [false,false,false,false]);
    for (const n of [1,3,7,10]) {
        const layout = resourceLayout(14,n);
        assert.equal(layout.filter(x => !x).length,n);
        assert.deepEqual(resourceLayout(14,n),layout);
    }
});
test('invalid resource layouts fail instead of rounding or saturating', () => {
    for (const pair of [[2,3],[-1,0],[4,-1],[4,1.5],[3.5,1]])
        assert.throws(() => resourceLayout(...pair));
});
test('missing reviewed Experience dependency rejects before any engine construction', async () => {
    await assert.rejects(fixture(null,{cards:[]},{probe:normal},1),/Experience/);
});
test('fixture dependency list binds shared constructor, state exporter and pure planner', () => {
    for (const file of ['lab/kessel-reference/pipeline/probe-fixture.js','bots/omni/rs/state.js',
        'bots/omni/rs/support-state.js','kessel:cards/pipeline/variable-payment-probes.js'])
        assert.ok(dependencies.includes(file));
});

test('native Experience metadata guard rejects missing, duplicate and altered definitions', () => {
 const token={setCode:'TOKEN_EXPERIENCE',internalName:'experience',cost:0,unique:false,types:['token','upgrade'],traits:['learned'],keywords:[],aspects:[],power:1,hp:1,upgradePower:1,upgradeHp:1,text:null};
 assert.doesNotThrow(()=>validateExperience({cards:[token]}));
 assert.throws(()=>validateExperience({cards:[token,token]}));
 for(const patch of [{power:2},{upgradeHp:0},{traits:[]},{keywords:['shielded']},{text:'Draw a card'},{types:['unit']}])assert.throws(()=>validateExperience({cards:[{...token,...patch}]}));
});
