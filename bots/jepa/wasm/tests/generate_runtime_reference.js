'use strict';
// Actual checkpoints, synthetic positions and a bounded toy simulator. No engine games or training.
const fs = require('node:fs');
const path = require('node:path');
const helperPath = process.env.JEPA_REFERENCE_HELPERS || path.join(__dirname, 'reference-fixtures.js');
const modulePath = process.env.JEPA_REFERENCE_JS || path.resolve(__dirname, '../../js/jepa.js');
const modelDir = process.env.JEPA_REFERENCE_MODELS || path.resolve(__dirname, '../../models');
const { generateReference } = require(helperPath);

generateReference({ modulePath, modelDir }).then((reference) => {
    for (const vector of reference.vectors) {
        for (const network of Object.values(vector.networks)) {
            network.context = { valueLogit: network.context.valueLogit };
            for (const [horizon, prediction] of Object.entries(network.predictions)) {
                network.predictions[horizon] = { logits: prediction.logits };
            }
        }
    }
    const file = path.join(__dirname, 'fixtures/runtime-reference.json');
    fs.writeFileSync(file, `${JSON.stringify(reference)}\n`);
    const tensors = reference.vectors.reduce((n, v) => n + Object.values(v.networks).reduce((m, net) => m + Object.keys(net.predictions).length, 0), 0);
    console.log(JSON.stringify({ file, vectors: reference.vectors.length, tensorCases: tensors, behaviorCases: reference.behaviors.length, gates: reference.behaviors.map((b) => b.settings.plan.gate), provenance: reference.provenance }));
}).catch((error) => { console.error(error); process.exitCode = 1; });
