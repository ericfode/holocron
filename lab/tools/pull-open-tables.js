#!/usr/bin/env node
'use strict';
/**
 * Keeps a local copy of the arena's open-table games: people against people and people against arena bots, played on
 * the arena window's /tables page and kept there for training (the arena's spec/open-tables.md). Players appear by a
 * random id (pl_ and 6 hex digits); every game was played in a player's browser and is unrated, with both players
 * trusted: use the games for training, not for ratings.
 *
 *   SWU_TABLES_TOKEN=swu_r_... node lab/tools/pull-open-tables.js [--out replays/open-tables] [--url https://swu-arena.fly.dev]
 *
 * A reader token comes from https://swu-arena.fly.dev/tables/logs (anyone signed in with GitHub). The folder is a
 * tournament folder Holotable opens and the lab's readers take (index.json and games/<id>.jsonl). Each run asks only
 * for the games after the newest one it has, and checks every replay against the sha256 the arena lists. A game that
 * fails (a download error, a wrong sha256) is asked for again on the next run, even when later games came through.
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const BASE = 'https://swu-arena.fly.dev';
const ID = /^open-[0-9a-f]{8}-[0-9a-f]{8}$/;
const PAGE = 1000;

function writeAtomic(file, data) {
    fs.writeFileSync(`${file}.tmp`, data);
    fs.renameSync(`${file}.tmp`, file);
}

/** Pulls every game the arena lists after the newest in `out`; returns {added, games, failed}. */
async function pull({ base = BASE, token, out, fetchImpl = globalThis.fetch, log = () => undefined }) {
    if (!/^swu_r_[0-9a-f]{48}$/.test(String(token ?? ''))) {
        throw new Error('set SWU_TABLES_TOKEN to a reader token (make one at https://swu-arena.fly.dev/tables/logs)');
    }
    const get = async (p) => {
        const r = await fetchImpl(`${base}${p}`, { headers: { authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(60000) });
        if (!r.ok) {
            const j = await r.json().catch(() => null);
            throw new Error(`${p}: HTTP ${r.status}${j?.error?.message ? ` (${j.error.message})` : ''}`);
        }
        return r;
    };
    fs.mkdirSync(path.join(out, 'games'), { recursive: true });
    const indexFile = path.join(out, 'index.json');
    const index = fs.existsSync(indexFile) ? JSON.parse(fs.readFileSync(indexFile, 'utf8')) : { id: path.basename(out), kind: 'tables', source: `${base}/api/open/games`, games: [] };
    const have = new Map(index.games.map((g) => [g.id, g]));
    // after the newest game it has, or, when a game failed last time, after the newest game it has from before that one
    const before = index.retryFrom ?? '\uffff';
    let since = index.games.reduce((m, g) => (String(g.playedAt) > m && String(g.playedAt) < before ? String(g.playedAt) : m), '');
    const rows = [];
    for (;;) {
        const q = new URLSearchParams({ limit: String(PAGE), ...(since ? { since } : {}) });
        const { result } = await (await get(`/api/open/games?${q}`)).json();
        rows.push(...result.games);
        if (!result.next) {
            break;
        }
        since = result.next;
    }
    let added = 0;
    let retryFrom = null;
    const failed = [];
    for (const row of rows) {
        if (!ID.test(String(row.id)) || have.has(row.id)) {
            continue;
        }
        const file = path.join(out, 'games', `${row.id}.jsonl`);
        try {
            const buf = Buffer.from(await (await get(`/api/open/games/${row.id}.jsonl`)).arrayBuffer());
            const sha = crypto.createHash('sha256').update(buf).digest('hex');
            if (row.sha256 && sha !== row.sha256) {
                throw new Error(`sha256 ${sha.slice(0, 12)} is not the listed ${String(row.sha256).slice(0, 12)}`);
            }
            writeAtomic(file, buf);
            have.set(row.id, row);
            index.games.push(row);
            added++;
            log(`${row.id}  ${row.p1} vs ${row.p2}  ${row.outcome}${row.winner ? ` (${row.winner})` : ''}`);
        } catch (e) {
            failed.push(`${row.id}: ${e.message}`);
            const at = String(row.playedAt);
            retryFrom = retryFrom === null || at < retryFrom ? at : retryFrom;
        }
    }
    index.retryFrom = retryFrom;
    index.games.sort((a, b) => String(a.playedAt).localeCompare(String(b.playedAt)));
    index.pulledAt = new Date().toISOString();
    writeAtomic(indexFile, `${JSON.stringify(index, null, 1)}\n`);
    return { added, games: index.games.length, failed };
}

module.exports = { pull };

if (require.main === module) {
    const args = process.argv.slice(2);
    const opt = (name, dflt) => {
        const i = args.indexOf(name);
        return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
    };
    const out = path.resolve(opt('--out', path.join(ROOT, 'replays', 'open-tables')));
    pull({ base: opt('--url', BASE).replace(/\/$/, ''), token: process.env.SWU_TABLES_TOKEN, out, log: (l) => console.log(l) }).then((r) => {
        console.log(`${r.added} new games, ${r.games} in ${path.relative(process.cwd(), out) || '.'}`);
        for (const f of r.failed) {
            console.error(`not pulled: ${f}`);
        }
        process.exitCode = r.failed.length ? 1 : 0;
    }, (e) => {
        console.error(e.message);
        process.exitCode = 2;
    });
}
