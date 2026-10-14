# Kessel reference generator

The engine-driving half of Kessel's card checks. Kessel (`ericfode/kessel`) runs every supported card against games
recorded from the forceteki engine; those games are recorded here, because recording them plays the engine through
Holocron's game player (`engine/env.js`), the bot registry (`bots/players/`) and the state exporter
(`bots/omni/rs/state.js`). Kessel checks and imports what this writes; it never depends on Holocron.

It was `bot/cards/` in swu_bot (the part Kessel did not take), and keeps Kessel's `cards/` layout so the case index
stays valid: case definitions name their modules relative to the reference folder (`./scenarios/x.js`,
`../pipeline/probe-fixture.js`).

| Path | What it is |
| --- | --- |
| `reference/scenarios/` | named reference cases: setup, scripted inputs and engine assertions |
| `reference/generate.js` | records selected cases into a fresh content-addressed corpus (traces, pools, `manifest.json.gz`) |
| `reference/index.js` | rebuilds Kessel's case index (`cards/reference/cases.json`, `cards/behaviors.json`) from the scenarios |
| `reference/cli.js` | `npm run kessel:reference -- index` and `-- generate` |
| `pipeline/*-fixture.js` | constructors for the automatic probe experiments that Kessel's planners (`cards/pipeline/*-probes.js`) plan |
| `pipeline/run.js`, `prepared.js`, `fanout.js`, `cli.js` | the card pipeline: plan, prepare one build, run the engine experiments and both Kessel runtimes, fan out up to 20 cards, and Kessel's work queue and checkpoints (`npm run kessel:pipeline`) |
| `kessel.js` | finds the Kessel checkout |

## Kessel checkout

Kessel's code is loaded from a checkout of `ericfode/kessel`: `KESSEL_DIR`, or `../kessel` next to this repository.
The case index, the corpus library, the planners, coverage, review and mutation code, the catalogue and the native and
Wasm builds are Kessel's. Both repositories must pin the same forceteki commit; `generate` refuses otherwise.

## Commands

```bash
npm run kessel:reference -- index                                  # after changing a scenario; commit Kessel's cases.json
npm run kessel:reference -- generate --case phase-stats/zero-power-from-pain --out /tmp/new-ref
npm run kessel:reference -- generate --card TWI_124 --play --out /tmp/play-ref
npm run kessel:pipeline -- run --cards TWI_124,TWI_170 --out /tmp/new-card-run   # Kessel's cards/PIPELINE.md
```

Then, in the Kessel checkout: `npm run cards:reference -- check --corpus /tmp/new-ref` and
`npm run cards:reference -- import --corpus /tmp/new-ref`.

`generate` binds every recording to the engine source and build. When `forceteki/build/.swu-reference-build.json` is
missing or stale it rebuilds `forceteki/build/server` first, and it refuses a `forceteki/build` that belongs to another
checkout (a symlink).

## Tests

`test/load.test.js` runs in `npm test`: every fixture and scenario loads from here, and both CLIs parse their options.
The rest need a Kessel checkout and run by hand:

```bash
KESSEL_DIR=../kessel npm run kessel-reference:test
```

- `fixtures.test.js`: plans with Kessel's planners and plays the experiments in the engine (about 90 s).
- `generate.test.js`: corpus generation with a stubbed engine, and that Kessel's `cases.json` indexes these scenarios.
- `prepared.test.js`: prepared-build manifests (needs `forceteki/build` from this checkout, not a symlink).
- `fanout.test.js`: the 20-card coordinator. Its descendant-timeout test needs process groups that some sandboxes lack.
