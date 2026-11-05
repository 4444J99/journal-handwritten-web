// Rules of the demo proxy (studio-cf/demo-proxy.mjs), tested against a fake upstream that records
// exactly what it receives. No wrangler, no Chrome, nothing talks to Cloudflare.
//   node --test studio-cf/tests/demo-proxy.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createProxy } from '../demo-proxy.mjs';

let upstream, proxy, upstreamPort, ownPort, seen;
const TOKEN = 'proxy-injected-test-token';

const listen = srv => new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv.address().port)));

before(async () => {
  upstream = http.createServer((req, res) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      seen.push({ method: req.method, url: req.url, headers: req.headers, body: Buffer.concat(chunks).toString() });
      res.writeHead(200, { 'content-type': 'text/plain' });
      res.end('upstream ok');
    });
  });
  upstreamPort = await listen(upstream);
  proxy = createProxy({ upstreamPort, token: () => TOKEN });
  ownPort = await listen(proxy);
});
after(async () => { await new Promise(r => proxy.close(r)); await new Promise(r => upstream.close(r)); });

// Send a request to the proxy with explicit headers (Host included).
function send({ method = 'GET', path = '/', headers = {}, body }) {
  seen = [];
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port: ownPort, method, path, headers }, res => {
      let text = '';
      res.on('data', c => { text += c; });
      res.on('end', () => resolve({ status: res.statusCode, text }));
    });
    req.on('error', reject);
    if (body !== undefined) req.write(body);
    req.end();
  });
}

test('the proxy\'s own origin is translated to the upstream origin, and the token is added', async () => {
  const r = await send({ method: 'PUT', path: '/api/db/rconfig/x', body: '{"a":1}', headers: {
    host: `127.0.0.1:${ownPort}`, origin: `http://127.0.0.1:${ownPort}`, 'sec-fetch-site': 'same-origin', 'content-type': 'application/json' } });
  assert.equal(r.status, 200);
  assert.equal(seen.length, 1);
  assert.equal(seen[0].headers.origin, `http://127.0.0.1:${upstreamPort}`);
  assert.equal(seen[0].headers.host, `127.0.0.1:${upstreamPort}`);
  assert.equal(seen[0].headers['cf-access-jwt-assertion'], TOKEN);
  assert.equal(seen[0].headers['sec-fetch-site'], 'same-origin'); // fetch metadata is forwarded untouched
  assert.equal(seen[0].body, '{"a":1}');                           // the body streams through
});

test('localhost is accepted as the proxy\'s own name too', async () => {
  const r = await send({ headers: { host: `localhost:${ownPort}`, origin: `http://localhost:${ownPort}` } });
  assert.equal(r.status, 200);
  assert.equal(seen[0].headers.origin, `http://127.0.0.1:${upstreamPort}`);
});

test('a foreign Origin is forwarded unchanged, so the API\'s cross-origin protection still applies', async () => {
  const r = await send({ method: 'PUT', body: '{}', headers: { host: `127.0.0.1:${ownPort}`, origin: 'http://evil.example', 'sec-fetch-site': 'cross-site' } });
  assert.equal(r.status, 200); // the fake upstream does not judge; the real API would answer 403
  assert.equal(seen[0].headers.origin, 'http://evil.example');
  assert.equal(seen[0].headers['sec-fetch-site'], 'cross-site');
});

test('the origin of a different port on this machine is not mistaken for the proxy\'s own', async () => {
  await send({ method: 'PUT', body: '{}', headers: { host: `127.0.0.1:${ownPort}`, origin: `http://127.0.0.1:${ownPort + 1}` } });
  assert.equal(seen[0].headers.origin, `http://127.0.0.1:${ownPort + 1}`);
});

test('a request for any other Host is refused with 421 and never reaches the upstream', async () => {
  // (An empty Host cannot be sent from node's client, which substitutes the default; a missing Host
  // is already refused by node's own HTTP server before the proxy sees the request.)
  for (const host of ['evil.example', `evil.example:${ownPort}`, `127.0.0.1.evil.example:${ownPort}`, `127.0.0.1:${ownPort + 1}`]) {
    const r = await send({ headers: { host } });
    assert.equal(r.status, 421, `Host ${JSON.stringify(host)}`);
    assert.equal(seen.length, 0, `Host ${JSON.stringify(host)} reached the upstream`);
  }
});

test('an Access header supplied by the client is overwritten', async () => {
  await send({ headers: { host: `127.0.0.1:${ownPort}`, 'cf-access-jwt-assertion': 'client-forged' } });
  assert.equal(seen[0].headers['cf-access-jwt-assertion'], TOKEN);
});

test('an unreachable upstream gives 502, not a crash', async () => {
  const dead = createProxy({ upstreamPort: 1, token: () => TOKEN });
  const port = await listen(dead);
  try {
    const status = await new Promise((resolve, reject) => {
      http.get({ host: '127.0.0.1', port, path: '/', headers: { host: `127.0.0.1:${port}` } }, res => { res.resume(); resolve(res.statusCode); }).on('error', reject);
    });
    assert.equal(status, 502);
  } finally { await new Promise(r => dead.close(r)); }
});
