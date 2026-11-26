// Logic test for the reader fold-in model and the source-reveal gate.
// No DOM, no browser: foldInModel is pure data, sourceRevealAllowed is an
// exact-value check on the pool string.
//
//   node --test tests/test_reader_cut_up.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { foldInModel } from '../site/reader-features.js';
import { sourceRevealAllowed } from '../site/reader-packages.js';

// One page, two blocks of three lines: pg1-0-* and pg1-1-*.
const PAGES = { pg1: { B: [{ L: ['a', 'b', 'c'] }, { L: ['d', 'e', 'f'] }] } };
const PIECES = [{ id: 'p001', V: [
  { id: 'p001-0', P: [['pg1', [0, 1]]] },
  { id: 'p001-1', method: 'cut-up', P: [['pg1', [0]]],
    src: [{ piece: 'p002', line: 'pg2-0-0' }, null, null] },
  { id: 'p001-2', method: 'erasure', sourceVersion: 'p001-0', P: [['pg1', [0]]],
    src: [null, null, null] },
] }];

test('source reveal allows exactly series and nothing else', () => {
  assert.equal(sourceRevealAllowed('series'), true);
  for (const pool of ['reserve', 'archive', 'unsorted', 'unknown', 'Series', ' series', '', null, undefined])
    assert.equal(sourceRevealAllowed(pool), false, JSON.stringify(pool));
});

test('fold-in model lists kept lines with their source', () => {
  const model = foldInModel(PIECES[0].V[1], { pieces: PIECES, pages: PAGES }, pid => pid === 'p002' ? 'series' : 'unknown');
  assert.equal(model.versionId, 'p001-1');
  assert.equal(model.method, 'cut-up');
  assert.deepEqual(model.dropped, []);
  assert.equal(model.lines.length, 3);
  assert.deepEqual(model.lines[0].src, { piece: 'p002', line: 'pg2-0-0' });
  assert.equal(model.lines[0].revealed, true);
  assert.equal(model.lines[0].withheld, false);
  assert.equal(model.lines[0].id, 'pg1-0-0');
  assert.equal(model.lines[1].src, null);
  assert.equal(model.lines[1].revealed, false);
  assert.equal(model.lines[1].withheld, false);
});

test('a non-Series source is withheld, never surfaced', () => {
  const model = foldInModel(PIECES[0].V[1], { pieces: PIECES, pages: PAGES }, () => 'reserve');
  assert.equal(model.lines[0].revealed, false);
  assert.equal(model.lines[0].withheld, true);
  // The src entry is still in the model (the studio needs it); only the
  // rendering withholds it. The public build gate refuses such a version
  // outright, so a withheld entry here means a stale or corrupt file.
  assert.deepEqual(model.lines[0].src, { piece: 'p002', line: 'pg2-0-0' });
});

test('erasure lists the source version lines it dropped', () => {
  const model = foldInModel(PIECES[0].V[2], { pieces: PIECES, pages: PAGES }, () => 'series');
  assert.equal(model.method, 'erasure');
  assert.deepEqual(model.dropped.map(l => l.id), ['pg1-1-0', 'pg1-1-1', 'pg1-1-2']);
  assert.equal(model.lines.length, 3);
});

test('erasure without a recorded source version lists no dropped lines', () => {
  const version = { id: 'p001-2', method: 'erasure', P: [['pg1', [0]]], src: [null, null, null] };
  const model = foldInModel(version, { pieces: PIECES, pages: PAGES }, () => 'series');
  assert.deepEqual(model.dropped, []);
});

test('unknown method throws', () => {
  assert.throws(() => foldInModel({ id: 'v', method: 'remix', P: [] }, { pieces: [], pages: {} }), /unknown version method/);
});
