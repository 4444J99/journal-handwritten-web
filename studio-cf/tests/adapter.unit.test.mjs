// Unit tests for studio/cf-adapter.js with a fake fetch and a fake clock.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const adapterPath = path.resolve(here, '..', '..', 'studio', 'cf-adapter.js');
const { createAdapter, dbCode, assetCode } = createRequire(import.meta.url)(adapterPath);

const flush = async () => { for (let i = 0; i < 12; i++) await new Promise(r => setImmediate(r)); };

function harness({ hidden = false } = {}) {
  const h = {
    now: 0, timers: [], seq: 0, hidden, visibleCbs: [], calls: [],
    routes: [], // [{match(fn), reply(fn)}]
  };
  h.env = {
    fetch: async (url, init = {}) => {
      h.calls.push({ url, method: init.method || 'GET', init });
      for (let i = h.routes.length - 1; i >= 0; i--) {
        const r = h.routes[i];
        if (r.match(url, init)) {
          const out = typeof r.reply === 'function' ? r.reply(url, init) : r.reply;
          if (out instanceof Error) throw out;
          return out;
        }
      }
      throw new Error('no route for ' + url);
    },
    setTimeout: (fn, ms) => { const id = ++h.seq; h.timers.push({ id, at: h.now + ms, fn }); return id; },
    clearTimeout: id => { h.timers = h.timers.filter(t => t.id !== id); },
    random: () => 0.5, // jitter factor exactly 1.0
    isHidden: () => h.hidden,
    onVisible: cb => h.visibleCbs.push(cb),
  };
  h.on = (match, reply) => { h.routes.push({ match, reply }); };
  h.advance = async ms => {
    const end = h.now + ms;
    for (;;) {
      await flush();
      const due = h.timers.filter(t => t.at <= end).sort((a, b) => a.at - b.at)[0];
      if (!due) break;
      h.timers = h.timers.filter(t => t !== due);
      h.now = due.at; due.fn();
    }
    h.now = end; await flush();
  };
  h.pending = () => h.timers.map(t => t.at - h.now).sort((a, b) => a - b);
  h.polls = name => h.calls.filter(c => c.method === 'GET' && c.url.startsWith('/api/db/' + name));
  return h;
}
const ok = body => ({ ok: true, status: 200, type: 'basic', json: async () => body });
const status = (code, body = {}) => ({ ok: code >= 200 && code < 300, status: code, type: 'basic', json: async () => body });
const ME = (canWrite = true) => ok({ email: 'a@example.test', canWrite });

describe('status mapping', () => {
  test('database codes', () => {
    const cases = { 401: 'revoked', 403: 'not_granted', 429: 'resource_exhausted', 400: 'invalid_argument', 413: 'invalid_argument', 500: 'unavailable', 502: 'unavailable', 503: 'unavailable', 507: 'quota_exceeded' };
    for (const [s, c] of Object.entries(cases)) assert.equal(dbCode(Number(s)), c, s);
  });
  test('asset codes', () => {
    const cases = { 413: 'too_large', 415: 'unsupported_type', 429: 'rate_limited', 507: 'quota_or_state', 500: 'store_unavailable', 503: 'store_unavailable', 401: 'not_granted', 403: 'not_granted' };
    for (const [s, c] of Object.entries(cases)) assert.equal(assetCode(Number(s)), c, s);
  });
});

describe('use()', () => {
  test('returns promises; db, user, assets resolve; unknown capability rejects', async () => {
    const h = harness(); h.on(u => u === '/api/me', () => ME());
    const a = createAdapter(h.env);
    const p = a.use('db'); assert.equal(typeof p.catch, 'function');
    const db = await p; assert.equal(typeof db.collection, 'function');
    assert.equal(typeof (await a.use('user')).can, 'function');
    assert.equal(typeof (await a.use('assets')).upload, 'function');
    await assert.rejects(a.use('nope'), e => e.code === 'capability_disabled');
    assert.equal(h.calls.filter(c => c.url === '/api/me').length, 1, '/api/me is fetched once and shared');
  });

  test('user.can reflects canWrite', async () => {
    for (const w of [true, false]) {
      const h = harness(); h.on(u => u === '/api/me', () => ME(w));
      const u = await createAdapter(h.env).use('user');
      assert.equal(await u.can('data.write'), w);
      assert.equal(await u.can('data.read'), true);
      assert.equal(await u.can('something.else'), false);
    }
  });

  test('a failing /api/me rejects use() so the page shows its offline state; a later call retries', async () => {
    const h = harness(); let fail = true;
    h.on(u => u === '/api/me', () => (fail ? status(403) : ME()));
    const a = createAdapter(h.env);
    await assert.rejects(a.use('db'), e => e.code === 'not_granted');
    fail = false;
    assert.ok(await a.use('db'));
  });

  test('a redirect to the Access login is reported as revoked', async () => {
    const h = harness(); h.on(u => u === '/api/me', () => ({ ok: false, status: 0, type: 'opaqueredirect' }));
    await assert.rejects(createAdapter(h.env).use('db'), e => e.code === 'revoked');
  });
});

describe('snapshots and polling', () => {
  async function open(h, name = 'reviews') {
    h.on(u => u === '/api/me', () => ME());
    const a = createAdapter(h.env);
    const db = await a.use('db');
    return db.collection(name);
  }

  test('snapshot shape: docs[] with id, exists, data(); first snapshot delivered even when empty', async () => {
    const h = harness(); let rev = 0, docs = [];
    h.on(u => u.startsWith('/api/db/reviews'), () => ok({ rev, docs }));
    const coll = await open(h);
    const snaps = [];
    coll.onSnapshot(s => snaps.push(s), () => assert.fail('no error expected'));
    await h.advance(0);
    assert.equal(snaps.length, 1);
    assert.deepEqual(snaps[0].docs, []);
    assert.equal(snaps[0].size, 0);
    rev = 1; docs = [{ id: 'd1', data: { a: 1, n: { b: [1] } } }];
    await h.advance(4100);
    assert.equal(snaps.length, 2);
    const d = snaps[1].docs[0];
    assert.equal(d.id, 'd1'); assert.equal(d.exists, true);
    assert.deepEqual(d.data(), { a: 1, n: { b: [1] } });
    d.data().a = 99; assert.equal(d.data().a, 1, 'data() returns a fresh copy');
    assert.deepEqual(h.polls('reviews').map(c => c.url), ['/api/db/reviews', '/api/db/reviews?since=0']);
  });

  test('unchanged polls use ?since and do not call back', async () => {
    const h = harness();
    h.on(u => u.startsWith('/api/db/reviews'), u => (u.includes('since=7') ? ok({ rev: 7, changed: false }) : ok({ rev: 7, docs: [{ id: 'x', data: {} }] })));
    const coll = await open(h); let n = 0;
    coll.onSnapshot(() => n++);
    await h.advance(0); assert.equal(n, 1);
    await h.advance(4100 * 5);
    assert.equal(n, 1);
    assert.ok(h.polls('reviews').length >= 5);
    assert.ok(h.polls('reviews').slice(1).every(c => c.url === '/api/db/reviews?since=7'));
  });

  test('polls about every 4 s', async () => {
    const h = harness();
    h.on(u => u.startsWith('/api/db/'), () => ok({ rev: 1, changed: false, docs: [] }));
    const coll = await open(h);
    coll.onSnapshot(() => {});
    await h.advance(0);
    const before = h.polls('reviews').length;
    await h.advance(20000);
    const n = h.polls('reviews').length - before;
    assert.ok(n >= 4 && n <= 6, 'polls in 20 s: ' + n);
  });

  test('pause while hidden, immediate poll when visible again', async () => {
    const h = harness(); h.on(u => u.startsWith('/api/db/'), () => ok({ rev: 1, docs: [] }));
    const coll = await open(h);
    coll.onSnapshot(() => {});
    await h.advance(0);
    h.hidden = true;
    await h.advance(5000); // the poll in flight at 4 s ends the loop because the tab is hidden
    const frozen = h.polls('reviews').length;
    await h.advance(60000);
    assert.equal(h.polls('reviews').length, frozen, 'no polling while hidden');
    assert.deepEqual(h.pending(), []);
    h.hidden = false; h.visibleCbs.forEach(f => f());
    await h.advance(0);
    assert.equal(h.polls('reviews').length, frozen + 1, 'one poll as soon as the tab is visible');
    await h.advance(4100);
    assert.equal(h.polls('reviews').length, frozen + 2, 'normal cadence resumes');
  });

  test('exponential backoff on failure, reset after success; last snapshot is kept; no error callback after the first success', async () => {
    const h = harness(); let mode = 'ok';
    h.on(u => u.startsWith('/api/db/'), () => (mode === 'ok' ? ok({ rev: 1, docs: [{ id: 'k', data: {} }] }) : status(503)));
    const coll = await open(h); let snaps = 0, errs = 0;
    coll.onSnapshot(() => snaps++, () => errs++);
    await h.advance(0); assert.equal(snaps, 1);
    mode = 'bad';
    await h.advance(4100); // fails (1)
    assert.deepEqual(h.pending(), [7900], 'next try 8 s after the failed poll (100 ms already elapsed)');
    await h.advance(8100); // fails (2)
    assert.deepEqual(h.pending(), [15800], 'then 16 s (200 ms already elapsed)');
    for (let i = 0; i < 8; i++) await h.advance(70000);
    assert.ok(h.pending()[0] <= 60000, 'capped at 60 s');
    assert.equal(errs, 0, 'a listener that already had data is not told about transient failures');
    mode = 'ok';
    await h.advance(61000);
    await h.advance(0);
    assert.ok(h.pending()[0] <= 4000, 'cadence returns to 4 s after success: ' + h.pending()[0]);
  });

  test('initial failures: errCb(unavailable) after 3 tries, and the listener is dropped', async () => {
    const h = harness(); h.on(u => u.startsWith('/api/db/'), () => status(503));
    const coll = await open(h); const errs = [];
    coll.onSnapshot(() => assert.fail('no snapshot'), e => errs.push(e.code));
    await h.advance(0); assert.deepEqual(errs, []);
    await h.advance(10000); assert.deepEqual(errs, []);
    await h.advance(20000);
    assert.deepEqual(errs, ['unavailable']);
    const n = h.polls('reviews').length;
    await h.advance(120000);
    assert.equal(h.polls('reviews').length, n, 'polling stopped with its last listener');
    assert.equal(h.pending().length, 0);
  });

  test('terminal errors are reported once, immediately, with the right code', async () => {
    for (const [s, code] of [[401, 'revoked'], [403, 'not_granted']]) {
      const h = harness(); h.on(u => u.startsWith('/api/db/'), () => status(s));
      const coll = await open(h); const errs = [];
      coll.onSnapshot(() => {}, e => errs.push(e.code));
      await h.advance(0);
      assert.deepEqual(errs, [code]);
      await h.advance(60000);
      assert.deepEqual(errs, [code]);
    }
  });

  test('a redirect during polling is revoked', async () => {
    const h = harness(); h.on(u => u.startsWith('/api/db/'), () => ({ ok: false, status: 0, type: 'opaqueredirect' }));
    const coll = await open(h); const errs = [];
    coll.onSnapshot(() => {}, e => errs.push(e.code));
    await h.advance(0);
    assert.deepEqual(errs, ['revoked']);
  });

  test('resubscribing after an error starts a fresh poller (no duplicates)', async () => {
    const h = harness(); let bad = true;
    h.on(u => u.startsWith('/api/db/'), () => (bad ? status(403) : ok({ rev: 1, docs: [] })));
    const coll = await open(h); let snaps = 0, errs = 0;
    coll.onSnapshot(() => snaps++, () => errs++);
    await h.advance(0); assert.equal(errs, 1);
    bad = false;
    coll.onSnapshot(() => snaps++, () => errs++);
    await h.advance(0); assert.equal(snaps, 1);
    const before = h.polls('reviews').length;
    await h.advance(40000);
    const n = h.polls('reviews').length - before;
    assert.ok(n <= 11, 'one poller only: ' + n);
  });

  test('unsubscribe stops polling; two listeners share one poller', async () => {
    const h = harness(); h.on(u => u.startsWith('/api/db/'), () => ok({ rev: 1, docs: [] }));
    const coll = await open(h); let a = 0, b = 0;
    const ua = coll.onSnapshot(() => a++);
    const ub = coll.onSnapshot(() => b++);
    await h.advance(0);
    assert.equal(a, 1); assert.equal(b, 1);
    const c0 = h.polls('reviews').length;
    await h.advance(8100);
    assert.ok(h.polls('reviews').length - c0 <= 3, 'shared poller');
    ua(); ub();
    const c1 = h.polls('reviews').length;
    await h.advance(60000);
    assert.equal(h.polls('reviews').length, c1);
  });

  test('the page\'s own write triggers an immediate poll', async () => {
    const h = harness(); let rev = 1;
    h.on(u => u.startsWith('/api/db/reviews') && !u.includes('/reviews/'), () => ok({ rev, docs: [{ id: 'w', data: { v: rev } }] }));
    h.on((u, i) => u.startsWith('/api/db/reviews/') && (i.method === 'PUT'), () => { rev = 2; return ok({ ok: true, rev: 2 }); });
    const coll = await open(h); const seen = [];
    coll.onSnapshot(s => seen.push(s.docs[0].data().v));
    await h.advance(0);
    await coll.doc('w').set({ v: 2 });
    await h.advance(50); // far less than 4 s
    assert.deepEqual(seen, [1, 2]);
    const put = h.calls.find(c => c.method === 'PUT');
    assert.equal(put.url, '/api/db/reviews/w');
    assert.equal(put.init.body, '{"v":2}');
  });
});

describe('writes and errors', () => {
  async function open(h) { h.on(u => u === '/api/me', () => ME()); return (await createAdapter(h.env).use('db')).collection('decisions'); }

  test('set, delete and get map to PUT, DELETE, GET', async () => {
    const h = harness();
    h.on(u => u.startsWith('/api/db/decisions/'), (u, i) => {
      if (i.method === 'GET') return u.endsWith('/gone') ? status(404) : ok({ id: 'there', data: { z: 1 } });
      return ok({ ok: true, rev: 1 });
    });
    const coll = await open(h);
    await coll.doc('there').set({ q: 1 });
    await coll.doc('there').delete();
    const got = await coll.doc('there').get(); assert.equal(got.exists, true); assert.deepEqual(got.data(), { z: 1 });
    const none = await coll.doc('gone').get(); assert.equal(none.exists, false);
    assert.deepEqual(h.calls.filter(c => c.url.includes('/decisions/')).map(c => c.method), ['PUT', 'DELETE', 'GET', 'GET']);
  });

  test('document ids are URL-encoded', async () => {
    const h = harness(); h.on(u => u.startsWith('/api/db/'), () => ok({ ok: true }));
    const coll = await open(h);
    await coll.doc('a b/c').set({});
    assert.equal(h.calls.at(-1).url, '/api/db/decisions/a%20b%2Fc');
  });

  test('write errors carry the codes the page retries on', async () => {
    const cases = [[503, 'unavailable'], [500, 'unavailable'], [429, 'resource_exhausted'], [400, 'invalid_argument'], [413, 'invalid_argument'], [401, 'revoked'], [403, 'not_granted'], [507, 'quota_exceeded']];
    for (const [s, code] of cases) {
      const h = harness(); const coll = await open(h);
      h.on(u => u.startsWith('/api/db/decisions/'), () => status(s));
      await assert.rejects(coll.doc('x').set({}), e => e.code === code && e.status === s, `${s}`);
    }
  });

  test('a network failure on a write is unavailable', async () => {
    const h = harness(); const coll = await open(h);
    h.on(u => u.startsWith('/api/db/decisions/'), () => new TypeError('fetch failed'));
    await assert.rejects(coll.doc('x').set({}), e => e.code === 'unavailable');
  });

  test('unknown collections are invalid_argument', async () => {
    const h = harness(); h.on(u => u === '/api/me', () => ME());
    const db = await createAdapter(h.env).use('db');
    assert.throws(() => db.collection('nope'), e => e.code === 'invalid_argument');
    for (const c of ['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig']) assert.ok(db.collection(c));
  });
});

describe('assets.upload', () => {
  async function open(h) { h.on(u => u === '/api/me', () => ME()); return await createAdapter(h.env).use('assets'); }

  test('posts the blob with its type and returns {id}', async () => {
    const h = harness(); h.on(u => u === '/api/assets', () => ok({ id: 'a'.repeat(32) }));
    const assets = await open(h);
    const blob = { type: 'image/jpeg', size: 3 };
    const r = await assets.upload(blob, { type: 'image/png' });
    assert.deepEqual(r, { id: 'a'.repeat(32) });
    const c = h.calls.find(x => x.url === '/api/assets');
    assert.equal(c.method, 'POST'); assert.equal(c.init.headers['content-type'], 'image/png'); assert.equal(c.init.body, blob);
  });

  test('error codes the page switches on', async () => {
    const cases = [[413, 'too_large'], [415, 'unsupported_type'], [429, 'rate_limited'], [507, 'quota_or_state'], [503, 'store_unavailable'], [500, 'store_unavailable'], [403, 'not_granted'], [401, 'not_granted']];
    for (const [s, code] of cases) {
      const h = harness(); const assets = await open(h);
      h.on(u => u === '/api/assets', () => status(s));
      await assert.rejects(assets.upload({}, { type: 'image/jpeg' }), e => e.code === code, `${s}`);
    }
    const h = harness(); const assets = await open(h);
    h.on(u => u === '/api/assets', () => new TypeError('fetch failed'));
    await assert.rejects(assets.upload({}, { type: 'image/jpeg' }), e => e.code === 'store_unavailable');
  });
});

describe('browser install', () => {
  const src = fs.readFileSync(adapterPath, 'utf8');
  function run(windowObj) {
    const ctx = { window: windowObj, document: { hidden: false, addEventListener() {} }, console, Math, Map, Set, Promise, Error, JSON, Array, Object, TypeError, setTimeout, clearTimeout, URL };
    windowObj.window = windowObj;
    vm.runInNewContext(src, ctx, { filename: 'cf-adapter.js' });
    return windowObj;
  }

  test('defines window.claude.use when absent', () => {
    const w = run({ fetch: async () => { throw new Error('unused'); }, setTimeout, clearTimeout });
    assert.equal(typeof w.claude.use, 'function');
  });

  test('does nothing when window.claude already has use()', () => {
    const existing = { use: () => 'original' };
    const w = run({ claude: existing, fetch: async () => { throw new Error('unused'); }, setTimeout, clearTimeout });
    assert.equal(w.claude, existing);
    assert.equal(w.claude.use(), 'original');
  });
});
