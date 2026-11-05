// Run the review studio ("workbench") on its Cloudflare code path, entirely on this machine.
//
//   node studio-cf/demo.mjs          ->  http://127.0.0.1:8790/     (Ctrl-C stops it)
//
// What runs: the real Pages Functions and API on `wrangler pages dev` with a LOCAL D1/R2
// simulation (nothing talks to Cloudflare), the studio's real page and scans (build_dist.py),
// a copy of the committed exports (the author's reviews plus the derived decisions), and a
// small proxy on 127.0.0.1 that adds a freshly signed TEST token, because a browser cannot
// send the Access header itself. That token stands in for Cloudflare Access; this is not
// access control and must never be exposed beyond this machine.
//
// State lives in studio-cf/.demo-state (git-ignored) and persists between runs, so what you
// click is kept; delete that folder to start again from the exports. The real database is
// never touched. Needs: node, python3, wrangler (/opt/homebrew/bin/wrangler or WRANGLER_BIN).
// Environment: DEMO_PORT (default 8790), DEMO_STATE (default studio-cf/.demo-state).
import { spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const PORT = Number(process.env.DEMO_PORT || 8790);
const BASE_DIR = path.resolve(process.env.DEMO_STATE || path.join(HERE, '.demo-state'));
const STATE = path.join(BASE_DIR, 'd1');
const DIST = path.join(BASE_DIR, 'dist');
const EXPORTS = [
  path.join(REPO, 'exports', 'studio-db-2026-11-05'),
  path.join(REPO, 'exports', 'derived-decisions-2026-11-05'),
];
process.env.STUDIO_CF_SCRATCH = path.join(BASE_DIR, 'scratch');

const AUD = 'demo-aud-0123456789abcdef';
const OWNER = 'owner@demo.test';

const run = (cmd, args) => {
  const r = spawnSync(cmd, args, { stdio: 'inherit' });
  if (r.status !== 0) { console.error(`failed: ${cmd} ${args.join(' ')} (exit ${r.status})`); process.exit(1); }
};
const load = rel => import(pathToFileURL(path.join(HERE, rel)).href);

fs.mkdirSync(BASE_DIR, { recursive: true });
const { makeKey, signRS256, claims, startJwks } = await load('tests/helpers/jwt.mjs');
const { startPagesDev } = await load('tests/helpers/wrangler.mjs');

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
  run('python3', [path.join(HERE, 'build_dist.py'), '--out', DIST]);
}
if (!fs.existsSync(STATE)) {
  fs.mkdirSync(STATE, { recursive: true });
  for (const dir of EXPORTS) {
    if (fs.existsSync(dir)) run('python3', [path.join(HERE, 'import_export.py'), dir, '--local', STATE]);
  }
}

const key = makeKey('demo-kid');
const jwks = await startJwks({ keys: [key] });
const team = `127.0.0.1:${jwks.port}`;
const iss = `https://${team}`;
const srv = await startPagesDev({
  ACCESS_TEAM_DOMAIN: team,
  ACCESS_AUD: AUD,
  OWNER_EMAILS: OWNER,
  ACCESS_JWKS_URL_TEST: `http://${team}/cdn-cgi/access/certs`,
}, 'demo', { persist: STATE, dir: DIST });

const token = () => signRS256(key, claims({ iss, aud: AUD, email: OWNER }));
const proxy = http.createServer((req, res) => {
  const headers = { ...req.headers, host: `127.0.0.1:${srv.port}`, 'cf-access-jwt-assertion': token() };
  const up = http.request({ host: '127.0.0.1', port: srv.port, method: req.method, path: req.url, headers }, r => {
    res.writeHead(r.statusCode, r.headers);
    r.pipe(res);
  });
  up.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('upstream error'); });
  req.pipe(up);
});
await new Promise(r => proxy.listen(PORT, '127.0.0.1', r));
console.log(`WORKBENCH READY: http://127.0.0.1:${PORT}/  (local copy in ${BASE_DIR}; delete it to reset)`);

const stop = async () => { proxy.close(); await srv.stop(); await jwks.close(); process.exit(0); };
process.on('SIGTERM', stop);
process.on('SIGINT', stop);
