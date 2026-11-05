// import_export.py --local writes the same local D1 that `wrangler pages dev` reads.
// Synthetic documents only (38 reviews, the shape and count of the real export).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { makeKey, signRS256, claims, startJwks } from './helpers/jwt.mjs';
import { startPagesDev, SCRATCH, STUDIO_CF } from './helpers/wrangler.mjs';

const AUD = 'import-aud';
const OWNER = 'owner@example.test';
let jwks, srv, key, iss, work;

function runPython(args) {
  return new Promise((resolve, reject) => {
    const p = spawn('python3', ['-B', path.join(STUDIO_CF, 'import_export.py'), ...args], { stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, WRANGLER_SEND_METRICS: 'false' } });
    let out = ''; p.stdout.on('data', d => out += d); p.stderr.on('data', d => out += d);
    p.on('exit', code => code === 0 ? resolve(out) : reject(new Error('import_export failed (' + code + '):\n' + out)));
  });
}

before(async () => {
  work = path.join(SCRATCH, `import-test-${process.pid}-${Date.now()}`);
  const exp = path.join(work, 'export');
  fs.mkdirSync(path.join(exp, 'reviews'), { recursive: true });
  for (let i = 0; i < 38; i++) {
    fs.writeFileSync(path.join(exp, 'reviews', `synthetic-${i}.json`), JSON.stringify({ at: '2026-01-01T00:00:00Z', original: `it's line ${i}\nsecond "line"`, status: 'ok' }));
  }
  key = makeKey('imp-kid');
  jwks = await startJwks({ keys: [key] });
  const team = `127.0.0.1:${jwks.port}`;
  iss = `https://${team}`;
  const persist = path.join(work, 'state');
  const out = await runPython([exp, '--local', persist]);
  assert.match(out, /reviews\s+38/);
  srv = await startPagesDev({ ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: AUD, OWNER_EMAILS: OWNER, ACCESS_JWKS_URL_TEST: `http://${team}/cdn-cgi/access/certs` }, 'import', { persist });
}, { timeout: 180000 });

after(async () => { if (srv) await srv.stop(); if (jwks) await jwks.close(); });

test('imported documents are served by the API, rev bumped once', async () => {
  const t = signRS256(key, claims({ iss, aud: AUD, email: OWNER }));
  const r = await fetch(srv.base + '/api/db/reviews', { headers: { 'Cf-Access-Jwt-Assertion': t } });
  assert.equal(r.status, 200);
  const body = await r.json();
  assert.equal(body.rev, 1);
  assert.equal(body.docs.length, 38);
  assert.deepEqual(body.docs.find(d => d.id === 'synthetic-7').data, { at: '2026-01-01T00:00:00Z', original: "it's line 7\nsecond \"line\"", status: 'ok' });
  for (const c of ['decisions', 'versions', 'release', 'batches', 'rconfig']) {
    const rr = await (await fetch(srv.base + '/api/db/' + c, { headers: { 'Cf-Access-Jwt-Assertion': t } })).json();
    assert.deepEqual(rr, { rev: 0, docs: [] }, c);
  }
});
