// Throwaway RSA keys, JWT signing and a local JWKS server for the tests.
import crypto from 'node:crypto';
import http from 'node:http';

const b64u = b => Buffer.from(b).toString('base64url');

export function makeKey(kid) {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
  const jwk = publicKey.export({ format: 'jwk' });
  return { kid, publicKey, privateKey, jwk: { ...jwk, kid, use: 'sig', alg: 'RS256' } };
}

export function signRS256(key, payload, headerExtra = {}) {
  const header = { alg: 'RS256', typ: 'JWT', kid: key.kid, ...headerExtra };
  const input = b64u(JSON.stringify(header)) + '.' + b64u(JSON.stringify(payload));
  const sig = crypto.sign('sha256', Buffer.from(input), key.privateKey);
  return input + '.' + b64u(sig);
}

export function unsigned(payload, kid) {
  return b64u(JSON.stringify({ alg: 'none', typ: 'JWT', kid })) + '.' + b64u(JSON.stringify(payload)) + '.';
}

export function signHS256WithPublicKey(key, payload) {
  const secret = key.publicKey.export({ type: 'spki', format: 'pem' });
  const input = b64u(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: key.kid })) + '.' + b64u(JSON.stringify(payload));
  return input + '.' + b64u(crypto.createHmac('sha256', secret).update(input).digest());
}

export function claims({ iss, aud, email, now = Math.floor(Date.now() / 1000), exp, nbf, extra = {} }) {
  const p = { iss, aud: [aud], email, iat: now, exp: exp === undefined ? now + 3600 : exp, ...extra };
  if (nbf !== undefined) p.nbf = nbf;
  return p;
}

// A JWKS endpoint on 127.0.0.1 that serves whatever `state.keys` holds.
export async function startJwks(state) {
  const server = http.createServer((req, res) => {
    state.hits = (state.hits || 0) + 1;
    if (req.url === '/cdn-cgi/access/certs') {
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ keys: state.keys.map(k => k.jwk), public_cert: {}, public_certs: [] }));
    } else { res.statusCode = 404; res.end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  return { server, port: server.address().port, close: () => new Promise(r => server.close(r)) };
}
