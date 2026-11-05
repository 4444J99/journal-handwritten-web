// Unit tests for lib/auth.js: configuration rules, the test-hook restriction, and
// JWKS caching / key rotation. No network, no wrangler.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readConfig, createVerifier, authenticate } from '../lib/auth.js';
import { makeKey, signRS256, claims } from './helpers/jwt.mjs';

const BASE_ENV = { ACCESS_TEAM_DOMAIN: 'team.example.test', ACCESS_AUD: 'aud1', OWNER_EMAILS: 'Owner@Example.test' };

describe('readConfig', () => {
  test('missing pieces give null (the middleware answers 503)', () => {
    assert.equal(readConfig(null), null);
    assert.equal(readConfig({}), null);
    for (const k of Object.keys(BASE_ENV)) {
      const e = { ...BASE_ENV }; delete e[k];
      assert.equal(readConfig(e), null, k);
      assert.equal(readConfig({ ...BASE_ENV, [k]: '   ' }), null, k + ' blank');
    }
    assert.equal(readConfig({ ...BASE_ENV, OWNER_EMAILS: ' , ; ' }), null);
    assert.equal(readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: 'bad host/with path' }), null);
  });

  test('team domain is normalised and the issuer derived from it', () => {
    for (const v of ['team.example.test', 'https://team.example.test', 'https://team.example.test/', ' TEAM.example.test ']) {
      const c = readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: v });
      assert.equal(c.issuer, 'https://team.example.test', v);
      assert.equal(c.jwksUrl, 'https://team.example.test/cdn-cgi/access/certs');
    }
  });

  test('email lists are lowercased and split on commas, spaces and semicolons', () => {
    const c = readConfig({ ...BASE_ENV, OWNER_EMAILS: 'A@x.test, B@x.test;c@x.test', READONLY_EMAILS: 'R@x.test' });
    assert.deepEqual([...c.owners], ['a@x.test', 'b@x.test', 'c@x.test']);
    assert.deepEqual([...c.readonly], ['r@x.test']);
  });

  test('the JWKS override is ignored unless the configured host is localhost or 127.0.0.1', () => {
    const ovr = 'http://127.0.0.1:9999/cdn-cgi/access/certs';
    assert.equal(readConfig({ ...BASE_ENV, ACCESS_JWKS_URL_TEST: ovr }).jwksUrl, 'https://team.example.test/cdn-cgi/access/certs');
    assert.equal(readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: 'evil.example.test', ACCESS_JWKS_URL_TEST: ovr }).jwksUrl, 'https://evil.example.test/cdn-cgi/access/certs');
    assert.equal(readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: '127.0.0.1:9999', ACCESS_JWKS_URL_TEST: ovr }).jwksUrl, ovr);
    assert.equal(readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: 'localhost:9999', ACCESS_JWKS_URL_TEST: 'http://localhost:9999/x' }).jwksUrl, 'http://localhost:9999/x');
  });

  test('even on a local team domain the override URL itself must be local', () => {
    const c = readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: '127.0.0.1:9999', ACCESS_JWKS_URL_TEST: 'https://attacker.example.test/keys' });
    assert.equal(c.jwksUrl, 'https://127.0.0.1:9999/cdn-cgi/access/certs');
    const d = readConfig({ ...BASE_ENV, ACCESS_TEAM_DOMAIN: '127.0.0.1:9999', ACCESS_JWKS_URL_TEST: 'http://127.0.0.1.attacker.example.test/keys' });
    assert.equal(d.jwksUrl, 'https://127.0.0.1:9999/cdn-cgi/access/certs');
  });
});

function fakeJwksFetch(state) {
  return async url => {
    state.calls.push(url);
    if (state.fail) return new Response('nope', { status: 500 });
    return new Response(JSON.stringify({ keys: state.keys.map(k => k.jwk) }), { status: 200, headers: { 'content-type': 'application/json' } });
  };
}

describe('JWKS cache and rotation', () => {
  const cfg = readConfig(BASE_ENV);
  const good = (key, extra = {}) => signRS256(key, claims({ iss: cfg.issuer, aud: 'aud1', email: 'owner@example.test', ...extra }));

  test('a key set is fetched once and cached', async () => {
    const k1 = makeKey('k1');
    const st = { keys: [k1], calls: [] }; let t = 1_000_000;
    const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => t });
    for (let i = 0; i < 3; i++) assert.equal((await v.verifyToken(good(k1), cfg)).ok, true);
    assert.equal(st.calls.length, 1);
  });

  test('rotation: a token with a new kid triggers one refetch, rate limited to once per 30 s', async () => {
    const k1 = makeKey('k1'), k2 = makeKey('k2');
    const st = { keys: [k1], calls: [] }; let t = 1_000_000;
    const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => t });
    assert.equal((await v.verifyToken(good(k1), cfg)).ok, true);
    st.keys = [k1, k2]; // the provider rotates in k2
    t += 5_000; // less than 30 s after the last fetch: no refetch, request is denied
    assert.deepEqual(await v.verifyToken(good(k2), cfg), { ok: false, status: 403 });
    assert.equal(st.calls.length, 1);
    t += 30_000; // past the minimum interval: the unknown kid causes one refetch
    assert.equal((await v.verifyToken(good(k2), cfg)).ok, true);
    assert.equal(st.calls.length, 2);
    // a kid that never appears cannot force more than one fetch per 30 s
    const ghost = makeKey('ghost');
    for (let i = 0; i < 20; i++) assert.equal((await v.verifyToken(good(ghost), cfg)).ok, false);
    assert.equal(st.calls.length, 2);
    t += 31_000;
    await v.verifyToken(good(ghost), cfg);
    await v.verifyToken(good(ghost), cfg);
    assert.equal(st.calls.length, 3);
  });

  test('removed keys stop working after the cache expires', async () => {
    const k1 = makeKey('k1'), k2 = makeKey('k2');
    const st = { keys: [k1, k2], calls: [] }; let t = 1_000_000;
    const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => t });
    assert.equal((await v.verifyToken(good(k1), cfg)).ok, true);
    st.keys = [k2];
    t += 11 * 60 * 1000; // past the 10 minute TTL
    assert.equal((await v.verifyToken(good(k1), cfg)).ok, false);
    assert.equal((await v.verifyToken(good(k2), cfg)).ok, true);
  });

  test('an unreachable key set fails closed with 503', async () => {
    const k1 = makeKey('k1');
    const st = { keys: [k1], calls: [], fail: true };
    const origErr = console.error; console.error = () => {};
    try {
      const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => 1_000_000 });
      assert.deepEqual(await v.verifyToken(good(k1), cfg), { ok: false, status: 503 });
    } finally { console.error = origErr; }
  });

  test('claims: iss, aud (array or string), exp, nbf, email', async () => {
    const k1 = makeKey('k1');
    const st = { keys: [k1], calls: [] }; const now = 1_800_000_000_000;
    const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => now });
    const nowS = now / 1000;
    const sign = p => signRS256(k1, p);
    const base = { iss: cfg.issuer, aud: ['aud1'], email: 'owner@example.test', exp: nowS + 60 };
    assert.equal((await v.verifyToken(sign(base), cfg)).ok, true);
    assert.equal((await v.verifyToken(sign({ ...base, aud: 'aud1' }), cfg)).ok, true);
    assert.equal((await v.verifyToken(sign({ ...base, aud: ['x', 'aud1'] }), cfg)).ok, true);
    assert.equal((await v.verifyToken(sign({ ...base, aud: ['other'] }), cfg)).ok, false);
    assert.equal((await v.verifyToken(sign({ ...base, aud: undefined }), cfg)).ok, false);
    assert.equal((await v.verifyToken(sign({ ...base, iss: 'https://team.example.test/' }), cfg)).ok, false);
    assert.equal((await v.verifyToken(sign({ ...base, exp: nowS }), cfg)).ok, false, 'exp == now is expired');
    assert.equal((await v.verifyToken(sign({ ...base, exp: undefined }), cfg)).ok, false, 'exp is required');
    assert.equal((await v.verifyToken(sign({ ...base, exp: String(nowS + 60) }), cfg)).ok, false, 'exp must be a number');
    assert.equal((await v.verifyToken(sign({ ...base, nbf: nowS + 10 }), cfg)).ok, true, 'small nbf skew tolerated');
    assert.equal((await v.verifyToken(sign({ ...base, nbf: nowS + 120 }), cfg)).ok, false);
    assert.equal((await v.verifyToken(sign({ ...base, email: undefined }), cfg)).ok, false, 'service tokens have no email');
  });

  test('header checks: alg must be RS256, kid required, no extra segments', async () => {
    const k1 = makeKey('k1');
    const st = { keys: [k1], calls: [] };
    const v = createVerifier({ fetchImpl: fakeJwksFetch(st), now: () => 1_000_000 });
    const p = claims({ iss: cfg.issuer, aud: 'aud1', email: 'owner@example.test', now: 1000 });
    assert.equal((await v.verifyToken(signRS256(k1, p, { alg: 'RS512' }), cfg)).ok, false);
    assert.equal((await v.verifyToken(signRS256(k1, p, { alg: 'rs256' }), cfg)).ok, false);
    assert.equal((await v.verifyToken(signRS256(k1, p, { kid: undefined }), cfg)).ok, false);
    assert.equal((await v.verifyToken(signRS256(k1, p) + '.extra', cfg)).ok, false);
    assert.equal((await v.verifyToken('', cfg)).ok, false);
    assert.equal((await v.verifyToken('a'.repeat(9000), cfg)).ok, false);
    assert.equal(st.calls.length, 0, 'bad headers are rejected before any key lookup');
  });
});

describe('authenticate()', () => {
  test('allowlist outcomes and status codes', async () => {
    const k1 = makeKey('k1');
    const st = { keys: [k1], calls: [] };
    const verifier = createVerifier({ fetchImpl: fakeJwksFetch(st) });
    const env = { ...BASE_ENV, READONLY_EMAILS: 'reader@example.test' };
    const cfg = readConfig(env);
    const req = t => new Request('https://x.test/', { headers: t ? { 'Cf-Access-Jwt-Assertion': t } : {} });
    const tok = email => signRS256(k1, claims({ iss: cfg.issuer, aud: 'aud1', email }));
    assert.deepEqual(await authenticate(req(tok('owner@example.test')), env, verifier), { status: 200, email: 'owner@example.test', canWrite: true });
    assert.deepEqual(await authenticate(req(tok('Reader@example.test')), env, verifier), { status: 200, email: 'reader@example.test', canWrite: false });
    assert.deepEqual(await authenticate(req(tok('nobody@example.test')), env, verifier), { status: 403 });
    assert.deepEqual(await authenticate(req(null), env, verifier), { status: 403 });
    assert.deepEqual(await authenticate(req(tok('owner@example.test')), { ...env, OWNER_EMAILS: '' }, verifier), { status: 503 });
    assert.deepEqual(await authenticate(req(null), {}, verifier), { status: 503 }, 'missing configuration is 503 even without a token');
  });
});
