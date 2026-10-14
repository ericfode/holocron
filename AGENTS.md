# Working on Holocron

Read `CLAUDE.md` for what lives where, the rules carried over from the arena project, and how `engine/env.js` drives
the engine; it applies to Codex work too. `README.md` has setup and the daily commands.

- Use Node 22. `git submodule update --init`, then build the pinned engine once inside `forceteki/`
  (`npm ci --ignore-scripts && npm run get-cards && npm run build`), then `npm ci` at the root.
- Checks, as CI runs them: `npm test`, `npm run test:py`, `npm run analysis:test`, `node engine/random-run.js 3 1`
  (seeds 1-3 give 594/342/486 steps, p2 wins), `make -C bots/c`, `cargo build --release && cargo test`.
- Never edit files inside `forceteki/`; engine bug workarounds go in `engine/` or the bot. Rated games belong to the
  arena (`ericfode/swu_bot`): nothing here sends it results.
- Keep tokens and `.env` files out of Git. Karabast opponents' names never go in this repo.
