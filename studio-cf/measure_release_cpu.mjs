#!/usr/bin/env node
// Per-request CPU of serving a release, local and offline: the R2-backed reader Worker
// (lib/public-reader.js) against the pre-rendered static site (prerender_release.mjs).
//
//   node studio-cf/measure_release_cpu.mjs --prepared P --db D --pieces p001 [--force-gates] [--runs 200]
//        [--serve-check] [--json out.json]
//
// What it measures: process.cpuUsage() around each call, in this Node process. That is a PROXY for
// Workers CPU time, not the same clock: V8 is shared but the Workers runtime differs, and R2 here is
// an in-memory stub (real R2 reads add no Worker CPU while awaiting I/O, but the JSON parse and body
// copy are counted). Use it to compare designs and to see how far each is from the 10 ms free-plan
// budget, not as a guarantee. The static site has no Worker, so its Worker CPU is zero by
// construction; --serve-check starts `wrangler pages dev` on it to prove the bytes, headers and
// absence of any Functions build.
//
// --force-gates builds the candidate although review gates fail. It exists only so real-sized data
// can be measured before the author has released anything; the build is held in memory, never
// written or published, and the report says it was forced.
import {writeFileSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import {buildCandidate, digest} from '../studio/publish-compiler.mjs';
import {readPublic} from './lib/public-reader.js';
import {render, write, verifySite, loadPrepared} from './prerender_release.mjs';

export const BUDGET_MS = 10;
const cpuMs = t => { const u = process.cpuUsage(t); return (u.user + u.system) / 1000; };
export function summarize(xs) {
  const s = [...xs].sort((a, b) => a - b), q = p => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return {n: s.length, first: xs[0], p50: q(0.5), p95: q(0.95), max: s[s.length - 1], mean: s.reduce((a, b) => a + b, 0) / s.length};
}
const round = o => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, typeof v === 'number' ? Math.round(v * 1000) / 1000 : v]));

async function timed(fn, runs) {
  const xs = [];
  for (let i = 0; i < runs; i++) { const t = process.cpuUsage(); await fn(); xs.push(cpuMs(t)); }
  return summarize(xs);
}

export function r2Stub(rendered) {
  const id = 'a'.repeat(64), prefix = `snapshots/${id}/`, store = {'current.json': {id}};
  const files = rendered.entries.map(e => ({path: e.path, sha256: e.sha256, size: e.size, contentType: e.contentType, key: e.path.startsWith('img/') ? `img/${e.sha256}.jpg` : prefix + e.path}));
  store[prefix + 'manifest.json'] = {id, files};
  rendered.entries.forEach((e, i) => { store[files[i].key] = e.bytes; });
  // R2 returns JSON as text it must parse; keep that cost real by storing the serialized form.
  const raw = Object.fromEntries(Object.entries(store).map(([k, v]) => [k, v instanceof Uint8Array ? v : JSON.stringify(v)]));
  const env = {PUBLIC: {async get(k) {
    const v = raw[k]; if (v === undefined) return null;
    return v instanceof Uint8Array ? {body: new Response(v).body, json: async () => JSON.parse(new TextDecoder().decode(v))} : {body: new Response(v).body, json: async () => JSON.parse(v)};
  }}};
  return {id, env, files};
}

export async function serveCheck(rendered, dir) {
  const {wranglerEnv, freePort, SCRATCH} = await import('./tests/helpers/wrangler.mjs');
  const port = await freePort(), cwd = mkdtempSync(join(tmpdir(), 'serve-cwd-'));
  const child = spawn(process.env.WRANGLER_BIN || '/opt/homebrew/bin/wrangler', ['pages', 'dev', dir, '--cwd', cwd, '--ip', '127.0.0.1', '--port', String(port), '--inspector-port', String(await freePort())], {cwd, env: wranglerEnv(), stdio: ['ignore', 'pipe', 'pipe']});
  let log = '';
  try {
    await new Promise((res, rej) => {
      const t = setTimeout(() => rej(new Error('wrangler not ready:\n' + log)), 90000);
      const on = d => { log += d; if (log.includes(`Ready on http://127.0.0.1:${port}`)) { clearTimeout(t); res(); } };
      child.stdout.on('data', on); child.stderr.on('data', on);
      child.on('exit', c => { clearTimeout(t); rej(new Error('wrangler exited ' + c + '\n' + log)); });
    });
    const results = [];
    for (const e of rendered.entries) {
      const url = `http://127.0.0.1:${port}/${e.path === 'index.html' ? '' : e.path}`;
      const t0 = performance.now(), r = await fetch(url), body = new Uint8Array(await r.arrayBuffer());
      results.push({path: e.path, status: r.status, hashOk: await digest(body) === e.sha256, contentType: r.headers.get('content-type'), expected: e.contentType,
        noindex: r.headers.get('x-robots-tag') === 'noindex', nosniff: r.headers.get('x-content-type-options') === 'nosniff', wallMs: performance.now() - t0});
    }
    return {results, functionsBuilt: !/No Functions/.test(log) && /Compiled Worker|_worker/i.test(log), noFunctionsReported: /No Functions/.test(log), log: log.split('\n').slice(0, 12)};
  } finally { child.kill('SIGTERM'); setTimeout(() => child.kill('SIGKILL'), 3000).unref(); rmSync(cwd, {recursive: true, force: true}); }
}

export async function main(argv) {
  const a = {pieces: [], runs: 200};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = () => argv[++i];
    if (k === '--prepared') a.prepared = v(); else if (k === '--db') a.db = v();
    else if (k === '--pieces') a.pieces = v().split(',').filter(Boolean); else if (k === '--runs') a.runs = Number(v());
    else if (k === '--force-gates') a.force = true; else if (k === '--serve-check') a.serve = true; else if (k === '--json') a.json = v();
    else throw new Error('bad argument ' + k);
  }
  if (!a.prepared || !a.db || !a.pieces.length) { process.stderr.write('usage: measure_release_cpu.mjs --prepared DIR --db DIR --pieces p001 [--force-gates] [--runs N] [--serve-check] [--json FILE]\n'); return 2; }
  const {loadDb} = await import('../tools/release_readiness.mjs');
  const {source, shell, readAsset} = await loadPrepared(a.prepared), db = loadDb(a.db);
  const compile = await timed(async () => { const c = await buildCandidate({source, db, shell, pieces: a.pieces, target: 'staging', force: !!a.force}); if (c.blocked) throw new Error('blocked: ' + [...c.stops, ...c.gates.filter(g => !g.ok && !g.overridden)].map(g => g.name)); }, 5);
  const candidate = await buildCandidate({source, db, shell, pieces: a.pieces, target: 'staging', force: !!a.force});
  if (candidate.blocked) { process.stderr.write('blocked (use --force-gates for measurement only)\n'); return 1; }
  const rendered = await render(candidate, readAsset), {id, env} = r2Stub(rendered);
  const reader = {};
  const paths = [...new Set(rendered.entries.map(e => e.path))];
  const biggest = rendered.entries.filter(e => e.path.startsWith('img/')).sort((x, y) => y.size - x.size)[0];
  const sample = ['index.html', 'data/j.json', biggest?.path].filter(Boolean);
  for (const p of sample) {
    const url = `https://x.invalid/_snapshot/${id}/${p === 'index.html' ? '' : p}`;
    const size = rendered.entries.find(e => e.path === p).size;
    reader[p] = {bytes: size, ...round(await timed(async () => { const r = await readPublic(new Request(url), env); await r.arrayBuffer(); }, a.runs))};
  }
  const etag = `"${id}:index.html"`;
  reader['304 revalidation'] = round(await timed(async () => { await readPublic(new Request(`https://x.invalid/_snapshot/${id}/`, {headers: {'if-none-match': etag}}), env); }, a.runs));
  const out = join(mkdtempSync(join(tmpdir(), 'measure-')), 'site');
  write(rendered, out);
  const problems = await verifySite(out, rendered);
  const report = {
    note: 'Node process.cpuUsage proxy, in-memory R2 stub; not Workers CPU. Gates forced: ' + !!a.force,
    budgetMs: BUDGET_MS, pieces: a.pieces, files: paths.length, totalBytes: rendered.entries.reduce((n, e) => n + e.size, 0),
    studioServerCompileMs: round(compile),
    readerWorkerMsPerRequest: reader,
    readerOverBudget: Object.entries(reader).filter(([, v]) => v.max > BUDGET_MS || v.p95 > BUDGET_MS).map(([k]) => k),
    prerendered: {workerInvocationsPerRequest: 0, workerCpuMs: 0, siteProblems: problems},
  };
  if (a.serve) {
    const s = await serveCheck(rendered, out);
    report.prerendered.served = {functionsBuilt: s.functionsBuilt, noFunctionsReported: s.noFunctionsReported, allOk: s.results.every(r => r.status === 200 && r.hashOk && r.noindex && r.nosniff && baseEq(r.contentType, r.expected)),
      files: s.results.map(r => ({path: r.path, status: r.status, hashOk: r.hashOk, contentType: r.contentType, expected: r.expected})), log: s.log};
  }
  rmSync(join(out, '..'), {recursive: true, force: true});
  const text = JSON.stringify(report, null, 2) + '\n';
  if (a.json) writeFileSync(a.json, text); else process.stdout.write(text);
  return 0;
}
// text/javascript and application/javascript are the same media type for script loading.
const norm = t => String(t || '').split(';')[0].trim().toLowerCase().replace('application/javascript', 'text/javascript');
export const baseEq = (a, b) => norm(a) === norm(b);
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2)).then(c => process.exit(c), e => { process.stderr.write(String(e.stack || e) + '\n'); process.exit(2); });
