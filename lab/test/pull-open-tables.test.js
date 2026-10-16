'use strict';
// lab/tools/pull-open-tables.js against a fake arena window: paging, only new games, sha256 checks, the token.
const test = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pull } = require('../tools/pull-open-tables');

const TOKEN = `swu_r_${'a'.repeat(48)}`;
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');

/** A window with `games` ({id, playedAt, body}); a page holds at most `page` rows. */
function arena(games, { page = 2 } = {}) {
    const asked = [];
    const fetchImpl = async (url, { headers }) => {
        const u = new URL(url);
        asked.push(u.pathname + u.search);
        const json = (status, body) => ({ ok: status === 200, status, json: async () => body, arrayBuffer: async () => Buffer.from(JSON.stringify(body)) });
        if (headers.authorization !== `Bearer ${TOKEN}`) {
            return json(401, { error: { code: 'unauthorized', message: 'not a reader token' } });
        }
        if (u.pathname === '/api/open/games') {
            const since = u.searchParams.get('since');
            const after = games.filter((g) => !since || g.playedAt > since);
            const rows = after.slice(0, page).map((g) => ({ id: g.id, p1: 'pl_aaaaaa', p2: 'tinybot-v2', outcome: 'won', winner: 'pl_aaaaaa', playedAt: g.playedAt, sha256: g.sha === undefined ? sha(g.body) : g.sha }));
            return json(200, { result: { games: rows, next: after.length > page ? rows.at(-1).playedAt : null } });
        }
        const g = games.find((x) => u.pathname === `/api/open/games/${x.id}.jsonl`);
        return g ? { ok: true, status: 200, arrayBuffer: async () => Buffer.from(g.body) } : json(404, { error: { message: 'no game' } });
    };
    return { fetchImpl, asked };
}

test('pulls every game page by page, then only the new ones, refuses a replay whose sha256 is not the listed one, and asks for it again', async () => {
    const out = fs.mkdtempSync(path.join(os.tmpdir(), 'open-tables-'));
    try {
        const games = [1, 2, 3].map((n) => ({ id: `open-0000000${n}-0000000${n}`, playedAt: `2026-10-16T00:0${n}:00.000Z`, body: `{"t":"header","n":${n}}\n` }));
        const a = arena(games);
        assert.deepStrictEqual(await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl }), { added: 3, games: 3, failed: [] });
        assert.strictEqual(fs.readFileSync(path.join(out, 'games', `${games[2].id}.jsonl`), 'utf8'), games[2].body);
        const index = JSON.parse(fs.readFileSync(path.join(out, 'index.json'), 'utf8'));
        assert.deepStrictEqual([index.kind, index.games.map((g) => g.id)], ['tables', games.map((g) => g.id)]);

        // game 4 fails and game 5, played after it, comes through
        games.push({ id: 'open-00000004-00000004', playedAt: '2026-10-16T00:04:00.000Z', body: 'x\n', sha: 'f'.repeat(64) }, { id: 'open-00000005-00000005', playedAt: '2026-10-16T00:05:00.000Z', body: 'y\n' });
        a.asked.length = 0;
        const again = await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl });
        assert.deepStrictEqual([again.added, again.games], [1, 4]);
        assert.match(again.failed[0], /open-00000004-00000004: sha256 .* is not the listed/);
        assert.ok(a.asked[0].includes('since=2026-10-16T00%3A03'), 'asks only after the newest game it has');
        assert.ok(!fs.existsSync(path.join(out, 'games', 'open-00000004-00000004.jsonl')));

        // next time, it asks again from before game 4 and gets it; game 5 is not downloaded twice
        delete games[3].sha;
        a.asked.length = 0;
        assert.deepStrictEqual(await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl }), { added: 1, games: 5, failed: [] });
        assert.ok(a.asked[0].includes('since=2026-10-16T00%3A03'), 'asks from before the game that failed');
        assert.deepStrictEqual(a.asked.filter((q) => q.endsWith('.jsonl')), ['/api/open/games/open-00000004-00000004.jsonl']);
        a.asked.length = 0;
        await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl });
        assert.ok(a.asked[0].includes('since=2026-10-16T00%3A05'), 'then after the newest game again');

        // a game listed with no sha256 is not kept
        games.push({ id: 'open-00000006-00000006', playedAt: '2026-10-16T00:06:00.000Z', body: 'z\n', sha: null });
        const unchecked = await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl });
        assert.deepStrictEqual([unchecked.added, unchecked.games], [0, 5]);
        assert.match(unchecked.failed[0], /open-00000006-00000006: the listing has no sha256/);
        // nor one whose id is not a game id
        games.splice(5, 1, { id: '../x', playedAt: '2026-10-16T00:06:00.000Z', body: 'z\n' });
        assert.match((await pull({ base: 'http://w', token: TOKEN, out, fetchImpl: a.fetchImpl })).failed[0], /^\.\.\/x: not a game id/);
    } finally {
        fs.rmSync(out, { recursive: true, force: true });
    }
});

test('a missing or wrong token says where to get one', async () => {
    const out = fs.mkdtempSync(path.join(os.tmpdir(), 'open-tables-'));
    try {
        await assert.rejects(pull({ token: undefined, out, fetchImpl: arena([]).fetchImpl }), /tables\/logs/);
        await assert.rejects(pull({ base: 'http://w', token: `swu_r_${'b'.repeat(48)}`, out, fetchImpl: arena([]).fetchImpl }), /HTTP 401 \(not a reader token\)/);
    } finally {
        fs.rmSync(out, { recursive: true, force: true });
    }
});
