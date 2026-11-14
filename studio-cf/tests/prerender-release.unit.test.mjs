import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, existsSync, writeFileSync, mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {buildCandidate, digest} from '../../studio/publish-compiler.mjs';
import {render, write, verifySite, headersFile, contentTypeRules} from '../prerender_release.mjs';
import {readPublic} from '../lib/public-reader.js';
import {fixture} from './helpers/publish-fixture.mjs';

// The shared fixture has placeholder hashes; give every asset real bytes so the hash check is real.
async function prepared() {
  const f = fixture(), bytes = {};
  for (const [path, a] of Object.entries(f.source.assets)) {
    const b = new TextEncoder().encode('bytes:' + path);
    bytes[path] = b; a.sha256 = await digest(b); a.size = b.length;
    if (path.startsWith('tiles/')) a.contentType = 'image/png';
  }
  return {...f, bytes, readAsset: async p => bytes[p]};
}
const build = async (p, pieces = ['p001', 'p002']) => buildCandidate({source: p.source, db: p.db, shell: p.shell, pieces, target: 'staging'});

test('pre-render writes exactly the candidate files plus _headers and no Worker entry point', async () => {
  const p = await prepared(), c = await build(p);
  assert.equal(c.blocked, false);
  const r = await render(c, p.readAsset), dir = join(mkdtempSync(join(tmpdir(), 'prerender-')), 'site');
  write(r, dir);
  assert.deepEqual(await verifySite(dir, r), []);
  for (const e of r.entries) assert.deepEqual(readFileSync(join(dir, e.path)), Buffer.from(e.bytes));
  for (const n of ['_worker.js', '_routes.json', 'functions']) assert.equal(existsSync(join(dir, n)), false, n);
  assert.match(readFileSync(join(dir, 'index.html'), 'utf8'), /<title>versforms<\/title>/);
});

test('the static site serves the same bytes and manifest the R2 reader serves (parity)', async () => {
  const p = await prepared(), c = await build(p), r = await render(c, p.readAsset);
  const id = 'a'.repeat(64), prefix = `snapshots/${id}/`, store = {'current.json': {id}};
  const files = r.entries.map(e => ({path: e.path, sha256: e.sha256, size: e.size, contentType: e.contentType, key: e.path.startsWith('img/') ? `img/${e.sha256}.jpg` : prefix + e.path}));
  store[prefix + 'manifest.json'] = {id, files};
  for (const [e, f] of r.entries.map((e, i) => [e, files[i]])) store[f.key] = e.bytes;
  const env = {PUBLIC: {async get(k) { const v = store[k]; if (v === undefined) return null; return {body: v, json: async () => v}; }}};
  for (const e of r.entries) {
    if (e.path === 'index.html') continue; // the reader adds a <base>; the static site needs none
    const res = await readPublic(new Request('https://x.invalid/_snapshot/' + id + '/' + e.path), env);
    assert.equal(res.status, 200, e.path);
    assert.deepEqual(new Uint8Array(await res.arrayBuffer()), e.bytes, e.path);
    assert.equal(res.headers.get('content-type'), e.contentType, e.path);
  }
});

test('release id is deterministic and changes with content', async () => {
  const p = await prepared(), a = await render(await build(p), p.readAsset), b = await render(await build(p), p.readAsset);
  assert.equal(a.id, b.id);
  const c = await render(await build(p, ['p001']), p.readAsset);
  assert.notEqual(a.id, c.id);
});

test('a blocked candidate, a tampered asset and a non-empty output directory write nothing', async () => {
  const p = await prepared();
  p.db.release.p001.pool = 'reserve';
  const blocked = await build(p);
  assert.equal(blocked.blocked, true);
  await assert.rejects(render(blocked, p.readAsset), /candidate_blocked/);
  const q = await prepared(), c = await build(q);
  await assert.rejects(render(c, async path => new TextEncoder().encode('tampered ' + path)), /asset_hash_mismatch/);
  const r = await render(c, q.readAsset), dir = mkdtempSync(join(tmpdir(), 'prerender-'));
  writeFileSync(join(dir, 'stale.html'), 'x');
  assert.throws(() => write(r, dir), /output_not_empty/);
});

test('verifySite flags a Worker entry point, a stray file and an edited byte', async () => {
  const p = await prepared(), r = await render(await build(p), p.readAsset), dir = join(mkdtempSync(join(tmpdir(), 'prerender-')), 'site');
  write(r, dir);
  writeFileSync(join(dir, '_worker.js'), 'export default {}');
  mkdirSync(join(dir, 'private')); writeFileSync(join(dir, 'private/notes.txt'), 'n');
  writeFileSync(join(dir, 'index.html'), 'edited');
  const problems = await verifySite(dir, r);
  assert.ok(problems.includes('worker_entry_present:_worker.js'));
  assert.ok(problems.includes('unexpected_file:private/notes.txt'));
  assert.ok(problems.includes('hash_mismatch:index.html'));
});

test('PNG bytes under .jpg routes get one splat Content-Type rule and the rule count stays within Pages limits', () => {
  const files = [{path: 'index.html', contentType: 'text/html; charset=utf-8'}, {path: 'data/j.json', contentType: 'application/json; charset=utf-8'},
    {path: 'img/p/pg1.jpg', contentType: 'image/jpeg'}];
  for (let n = 0; n < 300; n++) files.push({path: `img/a/t${n}.jpg`, contentType: 'image/png'}, {path: `img/a/k${n}.jpg`, contentType: 'image/png'});
  assert.deepEqual([...contentTypeRules(files)], [['/img/a/*', 'image/png']]);
  const h = headersFile(files);
  assert.match(h, /^\/\*\n  X-Robots-Tag: noindex\n/);
  assert.match(h, /\/img\/a\/\*\n  Content-Type: image\/png\n/);
  assert.doesNotMatch(h, /pg1/);
  const mixed = Array.from({length: 300}, (_, n) => ({path: `img/a/m${n}.jpg`, contentType: n % 2 ? 'image/png' : 'image/jpeg'}));
  assert.throws(() => headersFile(mixed), /too_many_header_rules/);
});

test('every output path passes the reader allow-list and name leaks are refused', async () => {
  const p = await prepared(), c = await build(p);
  c.files.push({path: 'notes/secret.txt', text: 'x', sha256: await digest('x'), size: 1, contentType: 'text/plain'});
  await assert.rejects(render(c, p.readAsset), /unsafe_path/);
});

test('nothing is cached without revalidation, because asset URLs name different bytes in different releases', async () => {
  const p = await prepared(), r = await render(await build(p, ['p001']), p.readAsset), q = await render(await build(p, ['p002']), p.readAsset);
  const a = r.entries.find(e => e.path === 'img/a/t0.jpg'), b = q.entries.find(e => e.path === 'img/a/t0.jpg');
  assert.notEqual(a.sha256, b.sha256, 'same URL, different bytes across releases');
  for (const h of [r.headers, q.headers]) {
    assert.match(h, /Cache-Control: public, max-age=0, must-revalidate/);
    assert.doesNotMatch(h, /max-age=[1-9]/);
  }
});

test('loadPrepared refuses a shell that differs from the recorded hash and resolves photos only from the photo directory', async () => {
  const {loadPrepared} = await import('../prerender_release.mjs');
  const dir = mkdtempSync(join(tmpdir(), 'prep-')), photos = mkdtempSync(join(tmpdir(), 'photos-'));
  const shell = '<html>shell</html>';
  writeFileSync(join(dir, 'shell.html'), shell);
  writeFileSync(join(dir, 'source.json'), JSON.stringify({shellSha256: await digest(shell), assets: {}}));
  writeFileSync(join(photos, 'asset1'), 'PHOTO');
  const ok = await loadPrepared(dir, photos);
  assert.equal(new TextDecoder().decode(await ok.readAsset('photos/asset1')), 'PHOTO');
  await assert.rejects(ok.readAsset('photos/../source.json'), /unknown_asset/);
  await assert.rejects(ok.readAsset('photos/.hidden'), /photo_input_missing/);
  await assert.rejects((await loadPrepared(dir)).readAsset('photos/asset1'), /photo_input_missing/);
  writeFileSync(join(dir, 'shell.html'), shell + ' changed');
  await assert.rejects(loadPrepared(dir, photos), /shell_hash_mismatch/);
});

test('encoded names in reader JavaScript are refused by the text scan, not only the byte scan', async () => {
  const p = await prepared();
  const js = new TextEncoder().encode('export const n="\\u0065tceter4";');
  const path = 'reader-features.js';
  p.source.assets[path] = {sha256: await digest(js), size: js.length, contentType: 'text/javascript; charset=utf-8'};
  p.bytes[path] = js;
  const c = await build(p);
  assert.equal(c.blocked, false);
  assert.ok(c.files.some(f => f.path === path));
  await assert.rejects(render(c, async x => p.bytes[x]), /name_leak/);
});
