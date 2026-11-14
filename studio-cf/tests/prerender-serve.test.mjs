import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {buildCandidate, digest} from '../../studio/publish-compiler.mjs';
import {render, write} from '../prerender_release.mjs';
import {serveCheck, baseEq, summarize, r2Stub} from '../measure_release_cpu.mjs';
import {fixture} from './helpers/publish-fixture.mjs';

async function site() {
  const f = fixture(), bytes = {};
  for (const [path, a] of Object.entries(f.source.assets)) {
    const b = new TextEncoder().encode('bytes:' + path); bytes[path] = b; a.sha256 = await digest(b); a.size = b.length;
    if (path.startsWith('tiles/')) a.contentType = 'image/png';
  }
  const c = await buildCandidate({source: f.source, db: f.db, shell: f.shell, pieces: ['p001', 'p002'], target: 'staging'});
  const r = await render(c, async p => bytes[p]), root = mkdtempSync(join(tmpdir(), 'prerender-serve-')), dir = join(root, 'site');
  write(r, dir);
  return {r, dir, root};
}

test('wrangler pages dev serves the pre-rendered site from static assets with no Functions build', async () => {
  const {r, dir, root} = await site();
  try {
    const s = await serveCheck(r, dir);
    assert.equal(s.noFunctionsReported, true);
    assert.equal(s.functionsBuilt, false);
    for (const x of s.results) {
      assert.equal(x.status, 200, x.path); assert.equal(x.hashOk, true, x.path);
      assert.equal(x.noindex && x.nosniff, true, x.path); assert.ok(baseEq(x.contentType, x.expected), `${x.path}: ${x.contentType} vs ${x.expected}`);
    }
  } finally { rmSync(root, {recursive: true, force: true}); }
});

test('measurement helpers', async () => {
  const q = summarize([1, 2, 3, 4, 100]);
  assert.equal(q.p50, 3); assert.equal(q.max, 100); assert.equal(q.first, 1);
  const {r} = await site();
  assert.equal(r2Stub(r).files.length, r.entries.length);
});

test('a failed serve check leaves no rendered release in the temporary directory', async () => {
  const {mkdirSync, writeFileSync, readdirSync} = await import('node:fs');
  const {main} = await import('../measure_release_cpu.mjs');
  const f = fixture(), root = mkdtempSync(join(tmpdir(), 'measure-fail-')), prep = join(root, 'prepared'), dbDir = join(root, 'db'), tmp = join(root, 'tmp');
  mkdirSync(join(prep, 'assets'), {recursive: true}); mkdirSync(dbDir); mkdirSync(tmp);
  for (const [path, a] of Object.entries(f.source.assets)) {
    const b = new TextEncoder().encode('bytes:' + path); a.sha256 = await digest(b); a.size = b.length;
    mkdirSync(join(prep, 'assets', path, '..'), {recursive: true}); writeFileSync(join(prep, 'assets', path), b);
  }
  f.source.shellSha256 = await digest(f.shell);
  writeFileSync(join(prep, 'source.json'), JSON.stringify(f.source)); writeFileSync(join(prep, 'shell.html'), f.shell);
  for (const [c, docs] of Object.entries(f.db)) { mkdirSync(join(dbDir, c)); for (const [id, d] of Object.entries(docs)) writeFileSync(join(dbDir, c, id + '.json'), JSON.stringify(d)); }
  const oldTmp = process.env.TMPDIR, oldBin = process.env.WRANGLER_BIN;
  process.env.TMPDIR = tmp; process.env.WRANGLER_BIN = join(root, 'no-such-wrangler');
  try {
    await assert.rejects(main(['--prepared', prep, '--db', dbDir, '--pieces', 'p001', '--runs', '3', '--serve-check']));
    assert.deepEqual(readdirSync(tmp).filter(n => n.startsWith('measure-')), []);
  } finally { process.env.TMPDIR = oldTmp; if (oldBin === undefined) delete process.env.WRANGLER_BIN; else process.env.WRANGLER_BIN = oldBin; rmSync(root, {recursive: true, force: true}); }
});
