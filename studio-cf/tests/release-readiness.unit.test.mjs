import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {fixture} from './helpers/publish-fixture.mjs';
import {assess, advice, loadDb, summarize, format, reviewProgress} from '../../tools/release_readiness.mjs';

const CLI = join(dirname(fileURLToPath(import.meta.url)), '../../tools/release_readiness.mjs');
const names = r => r.blockers.map(b => b.name);

test('a fully gated piece is ready and reports no blockers', async () => {
  const f = fixture();
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, true);
  assert.deepEqual(r.blockers, []);
  assert.deepEqual(r.review, {lines: 1, confirmed: 1, corrected: 0});
  assert.equal(r.pool, 'series');
});

test('each missing gate is reported with its own next step', async () => {
  const f = fixture();
  delete f.db.release.p001; f.db.reviews = {}; f.db.batches = {};
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, false);
  assert.deepEqual(names(r).sort(), ['filed', 'series', 'verified']);
  assert.match(r.blockers.find(b => b.name === 'verified').detail, /1 unverified/);
  for (const b of r.blockers) assert.notEqual(b.advice, b.name);
});

test('a recorded gruw-policy skip satisfies filing; a non-Series pool is a stop', async () => {
  const f = fixture();
  f.db.batches = {}; f.db.decisions['gruw-policy'] = {choice: 'skip'}; f.db.release.p001.pool = 'reserve';
  const [r] = await assess({...f, pieces: ['p001']});
  assert.ok(!names(r).includes('filed'));
  assert.ok(names(r).includes('own_pool_not_series'));
});

test('shared scans name the other piece and are never accepted or forced by the report', async () => {
  const f = fixture();
  f.source.j.pieces[1].V[0].P = [['pg1', [0]]];
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, false);
  const b = r.blockers.find(b => b.name === 'shared_scan:p002');
  assert.match(b.advice, /piece p002/);
});

test('corrected lines count toward progress and corrections on unpublished versions warn', async () => {
  const f = fixture();
  f.db.reviews['pg1-0-0'] = {status: 'corrected', original: 'machine-pg1', text: 'fixed'};
  assert.deepEqual(reviewProgress(f.source, f.db, 'p001'), {lines: 1, confirmed: 0, corrected: 1});
  const [r] = await assess({...f, pieces: ['p001', 'p999']});
  assert.equal(r.ready, true);
  const missing = (await assess({...f, pieces: ['p999']}))[0];
  assert.equal(missing.ready, false);
  assert.equal(missing.blockers[0].name, 'unknown_piece');
});

test('advice covers the known gate names and passes unknown ones through', () => {
  for (const n of ['series', 'verified', 'filed', 'own_pool_not_series', 'shared_scan:p002', 'shared_scan:x-diary2', 'stale_transcript:pg1-0-0'])
    assert.notEqual(advice(n), n);
  assert.equal(advice('something_new'), 'something_new');
  assert.match(advice('shared_scan:x-diary2'), /other lines/);
});

test('summary and text report agree', async () => {
  const f = fixture();
  delete f.db.release.p002;
  const rows = await assess({...f, pieces: ['p001', 'p002', 'p003']});
  const s = summarize(rows);
  assert.equal(s.pieces, 3); assert.equal(s.ready, 2); assert.deepEqual(s.blockedBy, {series: 1});
  const text = format(rows);
  assert.match(text, /2\/3 pieces pass every gate/);
  assert.match(text, /p002  blocked/);
  assert.doesNotMatch(format(rows, {detail: false}), /Sort the piece/);
});

test('CLI reads a prepared directory and an export layout, writes only the requested JSON, and exits by --require', () => {
  const dir = mkdtempSync(join(tmpdir(), 'readiness-'));
  try {
    const f = fixture();
    delete f.db.release.p002;
    mkdirSync(join(dir, 'prepared'));
    writeFileSync(join(dir, 'prepared/source.json'), JSON.stringify(f.source));
    writeFileSync(join(dir, 'prepared/shell.html'), f.shell);
    for (const c of ['release', 'reviews', 'batches']) {
      mkdirSync(join(dir, 'db', c), {recursive: true});
      for (const [id, d] of Object.entries(f.db[c])) writeFileSync(join(dir, 'db', c, id + '.json'), JSON.stringify(d));
    }
    const db = loadDb(join(dir, 'db'));
    assert.deepEqual(Object.keys(db.release).sort(), ['p001', 'p003']);
    assert.deepEqual(db.decisions, {});
    const run = (...a) => spawnSync(process.execPath, [CLI, '--prepared', join(dir, 'prepared'), '--db', join(dir, 'db'), ...a], {encoding: 'utf8'});
    let r = run('--pieces', 'p001,p002', '--json', join(dir, 'out.json'));
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /1\/2 pieces pass/);
    r = run('--pieces', 'p001', '--require', 'p001');
    assert.equal(r.status, 0, r.stderr);
    r = run('--pieces', 'p001,p002', '--require', 'p002');
    assert.equal(r.status, 1);
    r = run('--pieces', 'p001', '--require', 'p003');
    assert.equal(r.status, 2);
    assert.match(r.stderr, /not assessed/);
    assert.equal(spawnSync(process.execPath, [CLI], {encoding: 'utf8'}).status, 2);
    assert.equal(run('--target', 'nowhere').status, 2);
  } finally { rmSync(dir, {recursive: true, force: true}); }
});
