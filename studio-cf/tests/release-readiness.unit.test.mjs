import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {fixture} from './helpers/publish-fixture.mjs';
import {assess, advice, loadDb, summarize, format, reviewProgress} from '../../tools/release_readiness.mjs';
import {normalizeLanes, laneEntries, lanesReadyCount, weekLanes} from '../../studio/release-lanes.mjs';

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

// Lanes (JHW #41): the week view model the Calendar renders, and the proof
// that lane state never moves the poem's readiness. The DOM rendering itself
// (one poem row plus five quiet lines, two lane rows when work exists) is
// covered by the Playwright phone check in the plan's step 6; these tests
// pin the view model that rendering consumes.
test('a week with only the poem lane has five quiet lanes and 0/5 ready', () => {
  const w = weekLanes({pool: 'series'});
  assert.equal(w.total, 5);
  assert.equal(w.readyCount, 0);
  assert.deepEqual(w.lanes.map(l => [l.kind, l.state]), [['process', 'absent'], ['translation', 'absent'], ['audio', 'absent'], ['animation', 'absent'], ['reflection', 'absent']]);
  assert.equal(lanesReadyCount({}), 0);
});

test('a week with translation and audio present shows those two lanes with their dates', () => {
  const rec = {pool: 'series', lanes: {
    translation: {state: 'ready', date: '2026-11-20'},
    audio: {state: 'posted', url: 'https://example.test/audio', date: '2026-11-21'},
  }};
  const w = weekLanes(rec);
  assert.equal(w.readyCount, 2);
  const shown = w.lanes.filter(l => l.state !== 'absent');
  assert.deepEqual(shown.map(l => l.kind), ['translation', 'audio']);
  assert.equal(shown[0].date, '2026-11-20');
  assert.equal(shown[1].url, 'https://example.test/audio');
  assert.equal(shown[1].date, '2026-11-21');
  assert.deepEqual(w.lanes.filter(l => l.state === 'absent').map(l => l.kind), ['process', 'animation', 'reflection']);
});

test('an old record with no lanes key reads as all absent, and stray lane data is sanitised', () => {
  assert.deepEqual(Object.values(normalizeLanes({pool: 'series'})).map(e => e.state), ['absent', 'absent', 'absent', 'absent', 'absent', 'absent']);
  const dirty = normalizeLanes({lanes: {
    translation: {state: 'ready', url: 'javascript:alert(1)', date: 'not-a-date'},
    audio: {state: 'bogus'},
    nope: {state: 'ready'},
    poem: {state: 'posted', url: 'https://example.test/poem'},
  }});
  assert.equal(dirty.translation.state, 'ready');
  // Stored verbatim; the calendar only renders a link when checkPostUrl says
  // the URL is http(s), the same guard as for posted URLs.
  assert.equal(dirty.translation.url, 'javascript:alert(1)');
  assert.equal(dirty.translation.date, undefined);
  assert.equal(dirty.audio.state, 'absent');
  assert.equal(dirty.nope, undefined);
  // A stored poem entry is tolerated but never rendered from or counted.
  assert.equal(dirty.poem.state, 'posted');
  assert.equal(lanesReadyCount({lanes: {poem: {state: 'posted'}}}), 0);
  assert.deepEqual(laneEntries(null).map(l => l.state), ['absent', 'absent', 'absent', 'absent', 'absent']);
});

test('lane state never moves the poem readiness computation', async () => {
  const f = fixture();
  const plain = await assess({...f, pieces: ['p001']});
  assert.equal(plain[0].ready, true);
  f.db.release.p001.lanes = {
    translation: {state: 'posted', url: 'https://example.test/t', date: '2026-11-20'},
    audio: {state: 'ready'},
  };
  assert.deepEqual(await assess({...f, pieces: ['p001']}), plain);
  // And a blocked piece stays blocked with lanes present.
  const g = fixture();
  g.db.batches = {};
  const blockedPlain = await assess({...g, pieces: ['p001']});
  assert.equal(blockedPlain[0].ready, false);
  g.db.release.p001.lanes = {audio: {state: 'posted', date: '2026-11-21'}};
  assert.deepEqual(await assess({...g, pieces: ['p001']}), blockedPlain);
});

test('the three Oct 27 gates pass on a ready piece and each has its own next step', async () => {
  const f = fixture();
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, true);
  for (const n of ['alt_text', 'note_anchors', 'links']) assert.notEqual(advice(n), n);
});

test('alt_text blocks when the reader shell has no page-image alt template', async () => {
  const f = fixture();
  f.shell = f.shell.replace('<img src="img/p/pg1.jpg" alt="Page 1">', '');
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, false);
  const b = r.blockers.find(b => b.name === 'alt_text');
  assert.match(b.detail, /no page-image alt template/);
  assert.match(b.advice, /alt label/);
});

test('note_anchors blocks on an anchor to a line that is not in the version', async () => {
  const f = fixture();
  f.db.notes = {n1: {kind: 'footnote', anchor: {pieceId: 'p001', versionId: 'v0', lineId: 'pg1-0-9'}}};
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, false);
  const b = r.blockers.find(b => b.name === 'note_anchors');
  assert.match(b.detail, /unresolvable: pg1-0-9/);
  assert.match(b.advice, /Rebind the note anchor/);
});

test('note_anchors passes when every anchor resolves, and ignores other pieces', async () => {
  const f = fixture();
  f.db.notes = {
    n1: {kind: 'footnote', anchor: {pieceId: 'p001', versionId: 'v0', lineId: 'pg1-0-0'}},
    n2: {kind: 'reflection', anchor: {pieceId: 'p002', versionId: 'v1', lineId: 'pg2-0-9'}},
    n3: {kind: 'research-dossier', text: 'no anchor on this one'},
  };
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, true);
});

test('links blocks on a malformed URL in the published text and passes a valid one', async () => {
  const setLine = (f, text) => {
    f.source.j.pages[0].B[0].L[0] = text;
    f.source.review.pages[0].blocks[0].lines[0].tx = text;
    f.db.reviews['pg1-0-0'].original = text;
  };
  const bad = fixture();
  setLine(bad, 'see https://?x for the source');
  const [rb] = await assess({...bad, pieces: ['p001']});
  assert.equal(rb.ready, false);
  const b = rb.blockers.find(b => b.name === 'links');
  assert.match(b.detail, /invalid: https:\/\/\?x/);
  assert.match(b.advice, /well-formed http/);
  const good = fixture();
  setLine(good, 'see https://example.com/notes for the source');
  const [rg] = await assess({...good, pieces: ['p001']});
  assert.equal(rg.ready, true);
});

test('note gates judge head revisions: a rebound anchor clears the block its old revision caused', async () => {
  const f = fixture();
  const anchor = lineId => ({pieceId: 'p001', versionId: 'v0', lineId});
  f.db.notes = {
    r1: {recordId: 'rec', revisionId: 'r1', parents: [], kind: 'footnote', anchor: anchor('pg1-0-9')},
    r2: {recordId: 'rec', revisionId: 'r2', parents: ['r1'], kind: 'footnote', anchor: anchor('pg1-0-0')},
  };
  const [r] = await assess({...f, pieces: ['p001']});
  assert.equal(r.ready, true);
  // The head itself still blocks when it is the one that is broken.
  f.db.notes.r3 = {recordId: 'rec', revisionId: 'r3', parents: ['r2'], kind: 'footnote', anchor: anchor('pg1-0-9')};
  const [b] = await assess({...f, pieces: ['p001']});
  assert.equal(b.ready, false);
  assert.match(b.blockers.find(x => x.name === 'note_anchors').detail, /1 anchor\(s\) checked; unresolvable: pg1-0-9/);
});

test('links gate ignores private notes and the research dossier, and still checks a public note', async () => {
  const f = fixture();
  const base = {recordId: 'a', revisionId: 'a1', parents: [], anchor: {pieceId: 'p001', versionId: 'v0', lineId: 'pg1-0-0'}};
  f.db.notes = {
    a: {...base, kind: 'reflection', visibility: 'private', text: 'see https://?x'},
    b: {...base, recordId: 'b', revisionId: 'b1', kind: 'research-dossier', text: 'see https://?y'},
  };
  const [ok] = await assess({...f, pieces: ['p001']});
  assert.equal(ok.ready, true);
  f.db.notes.c = {...base, recordId: 'c', revisionId: 'c1', kind: 'footnote', visibility: 'public-candidate', text: 'see https://?z'};
  const [bad] = await assess({...f, pieces: ['p001']});
  assert.equal(bad.ready, false);
  assert.match(bad.blockers.find(x => x.name === 'links').detail, /invalid: https:\/\/\?z/);
});
