// Cloudflare Access JWT verification for the review studio.
//
// Fail-closed contract:
//   - every problem (no token, bad token, bad config, not on an allowlist)
//     produces a status code and NO response detail;
//   - there is no request-controlled bypass: nothing in the request other than
//     the signed token influences the decision;
//   - the only test hook is ACCESS_JWKS_URL_TEST, honoured solely when the
//     configured team domain AND the override URL are both localhost or
//     127.0.0.1. Production must never set it.

const JWKS_TTL_MS = 10 * 60 * 1000; // cache lifetime for a fetched key set
const JWKS_MIN_REFETCH_MS = 30 * 1000; // at most one forced refetch per 30 s (unknown kid)
const NBF_LEEWAY_S = 30;
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1']);

export const AUTH = Object.freeze({ OK: 200, DENIED: 403, MISCONFIGURED: 503 });

function b64urlToBytes(s) {
  if (typeof s !== 'string' || !/^[A-Za-z0-9_-]*$/.test(s)) throw new Error('b64');
  const pad = s.length % 4 === 0 ? '' : '='.repeat(4 - (s.length % 4));
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function b64urlToJson(s) {
  const v = JSON.parse(new TextDecoder().decode(b64urlToBytes(s)));
  if (v === null || typeof v !== 'object' || Array.isArray(v)) throw new Error('json');
  return v;
}

function splitList(v) {
  if (typeof v !== 'string') return [];
  return v.split(/[\s,;]+/).map(x => x.trim().toLowerCase()).filter(Boolean);
}

// Returns {teamHost, aud, owners:Set, readonly:Set, jwksUrl} or null when the
// configuration is missing or malformed (the caller answers 503).
export function readConfig(env) {
  if (!env) return null;
  let team = typeof env.ACCESS_TEAM_DOMAIN === 'string' ? env.ACCESS_TEAM_DOMAIN.trim() : '';
  team = team.replace(/^https?:\/\//i, '').replace(/\/+$/, '').toLowerCase();
  const aud = typeof env.ACCESS_AUD === 'string' ? env.ACCESS_AUD.trim() : '';
  const owners = new Set(splitList(env.OWNER_EMAILS));
  const readonly = new Set(splitList(env.READONLY_EMAILS));
  if (!team || !aud || owners.size === 0) return null;
  if (!/^[a-z0-9]([a-z0-9.-]*[a-z0-9])?(:[0-9]{1,5})?$/.test(team)) return null;
  let host;
  try { host = new URL('https://' + team).hostname; } catch { return null; }
  let jwksUrl = `https://${team}/cdn-cgi/access/certs`;
  const override = typeof env.ACCESS_JWKS_URL_TEST === 'string' ? env.ACCESS_JWKS_URL_TEST.trim() : '';
  if (override && LOCAL_HOSTS.has(host)) {
    try {
      const u = new URL(override);
      if ((u.protocol === 'http:' || u.protocol === 'https:') && LOCAL_HOSTS.has(u.hostname)) jwksUrl = u.toString();
    } catch { /* ignore: keep the production URL */ }
  }
  return { teamHost: team, issuer: 'https://' + team, aud, owners, readonly, jwksUrl };
}

// A verifier owns the JWKS cache. The default instance (below) is shared by the
// isolate; tests build their own with a fake fetch and clock.
export function createVerifier({ fetchImpl, now } = {}) {
  const doFetch = fetchImpl || ((...a) => fetch(...a));
  const clock = now || (() => Date.now());
  const caches = new Map(); // jwksUrl -> { keys: Map(kid -> CryptoKey), fetchedAt, lastAttempt, inflight }

  async function loadKeys(url) {
    let c = caches.get(url);
    if (!c) { c = { keys: new Map(), fetchedAt: 0, lastAttempt: 0, inflight: null }; caches.set(url, c); }
    if (c.inflight) return c.inflight;
    c.lastAttempt = clock();
    c.inflight = (async () => {
      try {
        const res = await doFetch(url, { headers: { accept: 'application/json' }, redirect: 'manual' });
        if (!res.ok) throw new Error('jwks status');
        const body = await res.json();
        if (!body || !Array.isArray(body.keys)) throw new Error('jwks shape');
        const next = new Map();
        for (const jwk of body.keys) {
          if (!jwk || jwk.kty !== 'RSA' || typeof jwk.kid !== 'string' || typeof jwk.n !== 'string') continue;
          if (jwk.use && jwk.use !== 'sig') continue;
          if (jwk.alg && jwk.alg !== 'RS256') continue;
          try {
            if (b64urlToBytes(jwk.n).length < 256) continue; // < 2048-bit modulus
            const key = await crypto.subtle.importKey(
              'jwk', { kty: 'RSA', n: jwk.n, e: jwk.e, alg: 'RS256', ext: true },
              { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
            next.set(jwk.kid, key);
          } catch { /* skip an unusable key */ }
        }
        c.keys = next; c.fetchedAt = clock();
      } finally { c.inflight = null; }
    })();
    return c.inflight;
  }

  // Resolve the verification key for a kid. Refetches on expiry, and once (rate
  // limited) when the kid is unknown, which covers key rotation.
  async function keyFor(url, kid) {
    const c = caches.get(url);
    const fresh = c && clock() - c.fetchedAt < JWKS_TTL_MS && c.fetchedAt > 0;
    if (!fresh) await loadKeys(url);
    let k = caches.get(url).keys.get(kid);
    if (!k) {
      const cc = caches.get(url);
      if (clock() - cc.lastAttempt >= JWKS_MIN_REFETCH_MS) {
        await loadKeys(url);
        k = caches.get(url).keys.get(kid);
      }
    }
    return k || null;
  }

  // Returns { ok:true, email } or { ok:false, status } with status 403 or 503.
  async function verifyToken(token, cfg) {
    try {
      if (typeof token !== 'string' || token.length === 0 || token.length > 8192) return { ok: false, status: 403 };
      const parts = token.split('.');
      if (parts.length !== 3 || parts.some(p => p.length === 0)) return { ok: false, status: 403 };
      const header = b64urlToJson(parts[0]);
      if (header.alg !== 'RS256') return { ok: false, status: 403 }; // rejects none, HS*, ES*, ...
      if (typeof header.kid !== 'string' || header.kid.length === 0 || header.kid.length > 200) return { ok: false, status: 403 };
      let key;
      try { key = await keyFor(cfg.jwksUrl, header.kid); } catch (e) {
        // operator log only (never in the response, never the token)
        console.error('studio-auth: key set unavailable:', String((e && e.message) || e));
        return { ok: false, status: 503 };
      }
      if (!key) return { ok: false, status: 403 };
      const data = new TextEncoder().encode(parts[0] + '.' + parts[1]);
      const valid = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64urlToBytes(parts[2]), data);
      if (!valid) return { ok: false, status: 403 };
      const p = b64urlToJson(parts[1]);
      const nowS = Math.floor(clock() / 1000);
      if (p.iss !== cfg.issuer) return { ok: false, status: 403 };
      const auds = Array.isArray(p.aud) ? p.aud : [p.aud];
      if (!auds.includes(cfg.aud)) return { ok: false, status: 403 };
      if (typeof p.exp !== 'number' || !(p.exp > nowS)) return { ok: false, status: 403 };
      if (p.nbf !== undefined && (typeof p.nbf !== 'number' || p.nbf > nowS + NBF_LEEWAY_S)) return { ok: false, status: 403 };
      if (typeof p.email !== 'string' || !p.email) return { ok: false, status: 403 }; // service tokens carry no email
      return { ok: true, email: p.email.trim().toLowerCase() };
    } catch {
      return { ok: false, status: 403 };
    }
  }

  return { verifyToken, _caches: caches };
}

const defaultVerifier = createVerifier();

// Authenticate a request. Returns { status, email?, canWrite? }; status 200 on success.
export async function authenticate(request, env, verifier = defaultVerifier) {
  const cfg = readConfig(env);
  if (!cfg) return { status: AUTH.MISCONFIGURED };
  const token = request.headers.get('Cf-Access-Jwt-Assertion');
  if (!token) return { status: AUTH.DENIED };
  const r = await verifier.verifyToken(token, cfg);
  if (!r.ok) return { status: r.status };
  if (cfg.owners.has(r.email)) return { status: AUTH.OK, email: r.email, canWrite: true };
  if (cfg.readonly.has(r.email)) return { status: AUTH.OK, email: r.email, canWrite: false };
  return { status: AUTH.DENIED };
}
