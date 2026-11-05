// End-to-end tests against `wrangler pages dev` (local D1 + R2 simulation).
// Uses synthetic data only. Run: node --test --test-concurrency=1 tests/server.test.mjs
import { test, before, after, describe } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import http from 'node:http';
import { makeKey, signRS256, unsigned, signHS256WithPublicKey, claims, startJwks } from './helpers/jwt.mjs';
import { startPagesDev } from './helpers/wrangler.mjs';

const AUD = 'test-aud-0123456789abcdef';
const OWNER = 'owner@example.test';
const READER = 'reader@example.test';
const STRANGER = 'stranger@example.test';

let jwks, srv, goodKey, otherKey, ISS, BASE;

const tok = (email, o = {}) => signRS256(o.key || goodKey, claims({ iss: o.iss || ISS, aud: o.aud || AUD, email, exp: o.exp, nbf: o.nbf }));
const owner = () => tok(OWNER);
const hdr = (t, extra = {}) => ({ ...(t ? { 'Cf-Access-Jwt-Assertion': t } : {}), ...extra });
const call = (path, { method = 'GET', token, headers = {}, body } = {}) =>
  fetch(BASE + path, { method, headers: hdr(token, headers), body, redirect: 'manual' });
const putDoc = (coll, id, obj, token = owner()) =>
  call(`/api/db/${coll}/${id}`, { method: 'PUT', token, headers: { 'content-type': 'application/json' }, body: JSON.stringify(obj) });

// A tiny but structurally valid JPEG-signature payload with random filler.
const fakeJpeg = n => Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), crypto.randomBytes(n)]);

before(async () => {
  goodKey = makeKey('good-kid-1');
  otherKey = makeKey('good-kid-1'); // same kid, different key material: wrong signature
  const state = { keys: [goodKey] };
  jwks = await startJwks(state);
  const team = `127.0.0.1:${jwks.port}`;
  ISS = `https://${team}`;
  srv = await startPagesDev({
    ACCESS_TEAM_DOMAIN: team,
    ACCESS_AUD: AUD,
    OWNER_EMAILS: OWNER,
    READONLY_EMAILS: READER,
    ACCESS_JWKS_URL_TEST: `http://${team}/cdn-cgi/access/certs`,
  }, 'server');
  BASE = srv.base;
}, { timeout: 120000 });

after(async () => { if (srv) await srv.stop(); if (jwks) await jwks.close(); });

const ROUTES = [
  ['GET', '/'], ['GET', '/index.html'], ['GET', '/data/review.json'], ['GET', '/img/thumbs/diary1.jpg'],
  ['GET', '/cf-adapter.js'], ['GET', '/api/me'], ['GET', '/api/db/reviews'], ['GET', '/_blob/x'], ['POST', '/api/assets'],
];

describe('every route is closed without a valid token', () => {
  const wrong = {
    'no token': () => null,
    'garbage token': () => 'not.a.jwt',
    'wrong signature': () => tok(OWNER, { key: otherKey }),
    'wrong aud': () => tok(OWNER, { aud: 'some-other-aud' }),
    'wrong iss': () => tok(OWNER, { iss: 'https://evil.example.test' }),
    'expired': () => tok(OWNER, { exp: Math.floor(Date.now() / 1000) - 3600 }),
    'not yet valid (nbf)': () => tok(OWNER, { nbf: Math.floor(Date.now() / 1000) + 3600 }),
    'alg none': () => unsigned(claims({ iss: ISS, aud: AUD, email: OWNER }), goodKey.kid),
    'HS256 with the public key as secret': () => signHS256WithPublicKey(goodKey, claims({ iss: ISS, aud: AUD, email: OWNER })),
    'unknown kid': () => signRS256({ ...goodKey, kid: 'no-such-kid' }, claims({ iss: ISS, aud: AUD, email: OWNER })),
    'valid token, email on no allowlist': () => tok(STRANGER),
  };
  for (const [name, make] of Object.entries(wrong)) {
    test(name, async () => {
      for (const [method, path] of ROUTES) {
        const r = await call(path, { method, token: make(), body: method === 'POST' ? fakeJpeg(32) : undefined, headers: method === 'POST' ? { 'content-type': 'image/jpeg' } : {} });
        assert.equal(r.status, 403, `${method} ${path}`);
        assert.equal((await r.text()).length, 0, `${method} ${path} body must be empty`);
      }
    });
  }

  test('cookie, query string and look-alike headers are not credentials', async () => {
    const t = owner();
    for (const init of [
      { headers: { cookie: `CF_Authorization=${t}` } },
      { headers: { 'x-forwarded-user': OWNER, 'cf-access-authenticated-user-email': OWNER } },
      { headers: { authorization: `Bearer ${t}` } },
    ]) {
      const r = await fetch(BASE + '/api/me', init);
      assert.equal(r.status, 403);
    }
    assert.equal((await fetch(BASE + `/api/me?token=${t}&cf-access-jwt-assertion=${t}`)).status, 403);
  });
});

describe('owner token', () => {
  test('static files are served with private caching', async () => {
    let r = await call('/', { token: owner() });
    assert.equal(r.status, 200);
    const html = await r.text();
    assert.match(html, /<script src="cf-adapter\.js"><\/script>/);
    assert.match(r.headers.get('cache-control'), /private/);
    r = await call('/data/review.json', { token: owner() });
    assert.equal(r.status, 200);
    assert.ok(Array.isArray((await r.json()).pages));
    r = await call('/img/thumbs/diary1.jpg', { token: owner() });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get('content-type'), 'image/jpeg');
    r = await call('/cf-adapter.js', { token: owner() });
    assert.equal(r.status, 200);
    assert.match(r.headers.get('x-robots-tag'), /noindex/);
  });

  test('/api/me', async () => {
    const r = await call('/api/me', { token: owner() });
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), { email: OWNER, canWrite: true });
    assert.match(r.headers.get('cache-control'), /no-store/);
  });

  test('CRUD round trip, rev increments and ?since', async () => {
    let r = await call('/api/db/decisions', { token: owner() });
    assert.deepEqual(await r.json(), { rev: 0, docs: [] });

    r = await putDoc('decisions', 'doc-1', { status: 'ok', n: 1, nested: { a: [1, 2, 3] } });
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), { ok: true, rev: 1 });

    r = await call('/api/db/decisions', { token: owner() });
    assert.deepEqual(await r.json(), { rev: 1, docs: [{ id: 'doc-1', data: { status: 'ok', n: 1, nested: { a: [1, 2, 3] } } }] });

    r = await call('/api/db/decisions?since=1', { token: owner() });
    assert.deepEqual(await r.json(), { rev: 1, changed: false });

    r = await putDoc('decisions', 'doc-1', { status: 'replaced' }); // set replaces, not merges
    assert.deepEqual(await r.json(), { ok: true, rev: 2 });
    r = await call('/api/db/decisions/doc-1', { token: owner() });
    assert.deepEqual(await r.json(), { id: 'doc-1', data: { status: 'replaced' } });

    r = await call('/api/db/decisions?since=1', { token: owner() });
    const body = await r.json();
    assert.equal(body.rev, 2);
    assert.equal(body.docs.length, 1);

    r = await putDoc('decisions', 'doc-2', { x: 1 });
    assert.equal((await r.json()).rev, 3);

    r = await call('/api/db/decisions/doc-1', { method: 'DELETE', token: owner() });
    assert.deepEqual(await r.json(), { ok: true, rev: 4 });
    r = await call('/api/db/decisions/doc-1', { token: owner() });
    assert.equal(r.status, 404);
    r = await call('/api/db/decisions?since=3', { token: owner() });
    const after = await r.json();
    assert.equal(after.rev, 4);
    assert.deepEqual(after.docs.map(d => d.id), ['doc-2']);

    // a stale future rev (database reset on the server) still gets the data
    r = await call('/api/db/decisions?since=999', { token: owner() });
    assert.equal((await r.json()).docs.length, 1);
  });

  test('revs are per collection', async () => {
    await putDoc('batches', 'b1', { a: 1 });
    await putDoc('batches', 'b2', { a: 2 });
    const r = await call('/api/db/rconfig', { token: owner() });
    assert.equal((await r.json()).rev, 0);
    assert.equal((await (await call('/api/db/batches', { token: owner() })).json()).rev, 2);
  });

  test('all six collections accept writes; anything else is 404', async () => {
    for (const c of ['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig']) {
      assert.equal((await putDoc(c, 'probe', { c })).status, 200, c);
    }
    assert.equal((await putDoc('secrets', 'probe', {})).status, 404);
    assert.equal((await call('/api/db/secrets', { token: owner() })).status, 404);
    assert.equal((await call('/api/db/docs', { token: owner() })).status, 404);
  });

  test('id validation', async () => {
    assert.equal((await putDoc('reviews', 'a'.repeat(128), { ok: 1 })).status, 200);
    for (const id of ['a'.repeat(129), 'has space', 'semi;colon', 'sl%2Fash', 'quo%22te', 'uni%C3%A9']) {
      const r = await call(`/api/db/reviews/${id}`, { method: 'PUT', token: owner(), body: '{}' });
      assert.equal(r.status, 400, id);
    }
    assert.equal((await call('/api/db/reviews/a.b-c_d', { method: 'PUT', token: owner(), body: '{}' })).status, 200);
  });

  test('body validation and the 64 KiB limit', async () => {
    const put = body => call('/api/db/reviews/limit', { method: 'PUT', token: owner(), body });
    assert.equal((await put('[1,2]')).status, 400);
    assert.equal((await put('null')).status, 400);
    assert.equal((await put('"str"')).status, 400);
    assert.equal((await put('{not json')).status, 400);
    assert.equal((await put('')).status, 400);
    const wrap = n => JSON.stringify({ s: 'x'.repeat(n) });
    const overhead = Buffer.byteLength(wrap(0));
    assert.equal((await put(wrap(65536 - overhead))).status, 200, 'exactly 64 KiB is accepted');
    assert.equal((await put(wrap(65536 - overhead + 1))).status, 413, '64 KiB + 1 is refused');
    // multi-byte characters count as bytes, not characters
    assert.equal((await put(JSON.stringify({ s: 'é'.repeat(33000) }))).status, 413);
    // a chunked body with no Content-Length is counted too
    const big = Buffer.from(wrap(70000));
    const stream = new ReadableStream({ start(c) { c.enqueue(big.subarray(0, 40000)); c.enqueue(big.subarray(40000)); c.close(); } });
    const r = await fetch(BASE + '/api/db/reviews/limit', { method: 'PUT', headers: hdr(owner()), body: stream, duplex: 'half' });
    assert.equal(r.status, 413);
  });

  test('bad ?since and bad methods', async () => {
    assert.equal((await call('/api/db/reviews?since=abc', { token: owner() })).status, 400);
    assert.equal((await call('/api/db/reviews?since=-1', { token: owner() })).status, 400);
    assert.equal((await call('/api/db/reviews', { method: 'POST', token: owner(), body: '{}' })).status, 405);
    assert.equal((await call('/api/db/reviews/x', { method: 'POST', token: owner(), body: '{}' })).status, 405);
    assert.equal((await call('/api/me', { method: 'PUT', token: owner(), body: '{}' })).status, 405);
    assert.equal((await call('/api/nothing', { token: owner() })).status, 404);
  });

  test('cross-site browser writes are refused', async () => {
    const r = await call('/api/db/reviews/xs', { method: 'PUT', token: owner(), headers: { 'sec-fetch-site': 'cross-site' }, body: '{}' });
    assert.equal(r.status, 403);
    const r2 = await call('/api/db/reviews/xs', { method: 'PUT', token: owner(), headers: { origin: 'https://evil.example.test' }, body: '{}' });
    assert.equal(r2.status, 403);
    const r3 = await call('/api/db/reviews/xs', { method: 'PUT', token: owner(), headers: { origin: BASE, 'sec-fetch-site': 'same-origin' }, body: '{}' });
    assert.equal(r3.status, 200);
  });

  test('asset upload and download round trip', async () => {
    const bytes = fakeJpeg(5000);
    let r = await call('/api/assets', { method: 'POST', token: owner(), headers: { 'content-type': 'image/jpeg' }, body: bytes });
    assert.equal(r.status, 201);
    const { id } = await r.json();
    assert.match(id, /^[a-f0-9]{32}$/);

    r = await call('/_blob/' + id, { token: owner() });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get('content-type'), 'image/jpeg');
    assert.equal(r.headers.get('cache-control'), 'private, max-age=31536000, immutable');
    assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
    assert.ok(Buffer.from(await r.arrayBuffer()).equals(bytes));

    // PNG with a parameter on the content type
    const png = Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), crypto.randomBytes(100)]);
    r = await call('/api/assets', { method: 'POST', token: owner(), headers: { 'content-type': 'image/PNG; charset=binary' }, body: png });
    assert.equal(r.status, 201);
    const pid = (await r.json()).id;
    const got = await call('/_blob/' + pid, { token: owner() });
    assert.equal(got.headers.get('content-type'), 'image/png');

    assert.equal((await call('/_blob/' + 'f'.repeat(32), { token: owner() })).status, 404);
    assert.equal((await call('/_blob/not-a-valid-id', { token: owner() })).status, 404);
    assert.equal((await call('/_blob/' + id + '/extra', { token: owner() })).status, 404);
  });

  test('unusual paths: 403 without a token, a clean 404 (never 502) with one', async () => {
    const rawGet = (path, token) => new Promise((resolve, reject) => {
      const u = new URL(BASE);
      const req = http.request({ host: u.hostname, port: u.port, path, method: 'GET', headers: hdr(token) }, res => {
        const chunks = []; res.on('data', d => chunks.push(d)); res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString() }));
      });
      req.on('error', reject); req.end();
    });
    const cases = ['/%00', '/a%00b.jpg', '/' + 'x'.repeat(300), '/' + 'x'.repeat(3000), '/index.html/', '/index.html//', '/data/review.json/', '/cf-adapter.js/', '/%01', '/a/%1f'];
    for (const p of cases) {
      const anon = await rawGet(p);
      assert.equal(anon.status, 403, 'no token ' + p.slice(0, 30));
      assert.equal(anon.body.length, 0);
      const bad = await rawGet(p, tok(STRANGER));
      assert.equal(bad.status, 403, 'wrong user ' + p.slice(0, 30));
      const ok = await rawGet(p, owner());
      assert.equal(ok.status, 404, 'owner ' + p.slice(0, 30));
      assert.ok(!/wrangler|Could not serve|ENOTDIR|ENAMETOOLONG|\/Volumes\//.test(ok.body), 'no simulator or path detail in the body');
    }
    // Paths that try to leave the served directory. The simulator's static layer decodes
    // "%2f" after routing, so "..%2f" used to read files one level up (studio-cf/wrangler.toml,
    // studio-cf/README.md). Every form must be a bodyless 404 for the owner, and a 403 for anyone else.
    const escapes = [
      '/..%2fstudio-cf%2fwrangler.toml', '/..%2Fstudio-cf%2FREADME.md', '/..%2f..%2fetc/passwd',
      '/..%5cstudio-cf%5cwrangler.toml', '/%2e%2e%2fstudio-cf%2fwrangler.toml', '/..%252fstudio-cf%252fwrangler.toml',
      '/data%2f..%2f..%2fstudio-cf%2fwrangler.toml', '/a%2fb',
    ];
    for (const p of escapes) {
      assert.equal((await rawGet(p)).status, 403, 'no token ' + p);
      assert.equal((await rawGet(p, tok(STRANGER))).status, 403, 'wrong user ' + p);
      const ok = await rawGet(p, owner());
      assert.equal(ok.status, 404, 'owner ' + p);
      assert.equal(ok.body.length, 0, 'no body for ' + p);
    }
    // ordinary odd-but-valid paths still behave
    for (const p of ['/%zz', '//', '/a%20b']) assert.ok([200, 404].includes((await rawGet(p, owner())).status), p);
    // the guard must not refuse real files
    assert.equal((await rawGet('/', owner())).status, 200);
    assert.equal((await rawGet('/data/review.json', owner())).status, 200);
    assert.equal((await rawGet('/img/thumbs/diary1.jpg', owner())).status, 200);
    assert.equal((await rawGet('/cf-adapter.js', owner())).status, 200);
  });

  test('the API path is classified case-insensitively: no static caching header on /API/me', async () => {
    const r = await call('/API/me', { token: owner() });
    assert.equal(r.status, 200);
    assert.equal(r.headers.get('cache-control'), 'no-store');
  });

  test('asset validation', async () => {
    const post = (type, body) => call('/api/assets', { method: 'POST', token: owner(), headers: type ? { 'content-type': type } : {}, body });
    assert.equal((await post('text/html', '<script>1</script>')).status, 415);
    // the page can send gif (studio/index.html toUploadable): accepted when the bytes are a GIF
    assert.equal((await post('image/gif', fakeJpeg(10))).status, 415, 'gif type with jpeg bytes');
    for (const sig of ['GIF89a', 'GIF87a']) {
      const g = await post('image/gif', Buffer.concat([Buffer.from(sig), crypto.randomBytes(64)]));
      assert.equal(g.status, 201, sig);
      const back = await call('/_blob/' + (await g.json()).id, { token: owner() });
      assert.equal(back.headers.get('content-type'), 'image/gif');
    }
    assert.equal((await post('image/svg+xml', '<svg/>')).status, 415);
    assert.equal((await post('image/jpeg', Buffer.from('this is not a jpeg at all'))).status, 415, 'signature must match the declared type');
    assert.equal((await post('image/jpeg', Buffer.alloc(0))).status, 400);
    const atLimit = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(15 * 1024 * 1024 - 3)]);
    assert.equal((await post('image/jpeg', atLimit)).status, 201, 'exactly 15 MiB is accepted');
    const over = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(15 * 1024 * 1024 - 2)]);
    assert.equal((await post('image/jpeg', over)).status, 413, '15 MiB + 1 is refused');
  });
});

describe('read-only email', () => {
  test('canWrite is false and every write is 403', async () => {
    const t = tok(READER);
    let r = await call('/api/me', { token: t });
    assert.deepEqual(await r.json(), { email: READER, canWrite: false });
    await putDoc('reviews', 'ro-doc', { v: 1 });
    r = await call('/api/db/reviews', { token: t });
    assert.equal(r.status, 200);
    assert.ok((await r.json()).docs.some(d => d.id === 'ro-doc'));
    r = await call('/api/db/reviews/ro-doc', { token: t });
    assert.equal(r.status, 200);
    assert.equal((await putDoc('reviews', 'ro-doc', { v: 2 }, t)).status, 403);
    assert.equal((await call('/api/db/reviews/ro-doc', { method: 'DELETE', token: t })).status, 403);
    assert.equal((await call('/api/assets', { method: 'POST', token: t, headers: { 'content-type': 'image/jpeg' }, body: fakeJpeg(10) })).status, 403);
    const still = await (await call('/api/db/reviews/ro-doc', { token: owner() })).json();
    assert.deepEqual(still.data, { v: 1 });
    assert.equal((await call('/', { token: t })).status, 200, 'read-only users can load the page');
  });

  test('email comparison is case-insensitive', async () => {
    const r = await call('/api/me', { token: tok('OWNER@Example.TEST') });
    assert.equal(r.status, 200);
    assert.equal((await r.json()).canWrite, true);
  });
});
