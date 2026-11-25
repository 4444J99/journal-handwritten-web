// Logic test for the Cut tab cut-up helpers. No DOM, no browser.
// It slices the real helper block out of studio/index.html and runs it in a vm,
// so the test exercises the code the page ships, not a copy.
//
//   node --test tests/test_cut_up.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, '..', 'studio', 'index.html'), 'utf8');
const begin = '/* cut-up helpers begin */';
const end = '/* cut-up helpers end */';
const i = html.indexOf(begin), j = html.indexOf(end);
assert.ok(i >= 0 && j > i, 'helper block markers not found in studio/index.html');
assert.equal(html.indexOf(begin, i + 1), -1, 'helper block appears more than once');

const ctx = vm.createContext({ URL });
vm.runInContext(html.slice(i + begin.length, j) + '\nthis.CUT_UP_METHODS = CUT_UP_METHODS; this.CUT_UP_WITHHELD_POOLS = CUT_UP_WITHHELD_POOLS; this.cutUpMethod = cutUpMethod; this.cutUpValidate = cutUpValidate; this.cutUpReserveSources = cutUpReserveSources; this.cutUpRecord = cutUpRecord; this.cutUpWarningText = cutUpWarningText; this.cutUpBadVersions = cutUpBadVersions;', ctx);
const { CUT_UP_METHODS, CUT_UP_WITHHELD_POOLS, cutUpMethod, cutUpValidate, cutUpReserveSources, cutUpRecord, cutUpWarningText, cutUpBadVersions } = ctx;

// Pages for the length check: one block of three lines each.
const PAGES = { pg2: { B: [{ L: ['a', 'b', 'c'] }] }, pg3: { B: [{ L: ['a', 'b', 'c'] }] } };
const version = (src, method = 'cut-up') => ({ id: 'p001-1', P: [['pg2', [0]]], method, src });

test('method defaults to original and unknown methods throw', () => {
  assert.equal(cutUpMethod({ id: 'v' }), 'original');
  assert.deepEqual([...CUT_UP_METHODS], ['original', 'cut-up', 'erasure']);
  assert.throws(() => cutUpMethod({ id: 'v', method: 'remix' }), /unknown version method/);
});

test('validate rejects src on original, bad entries, and wrong lengths', () => {
  assert.throws(() => cutUpValidate(version([null, null, null], 'original')), /carries src provenance/);
  assert.throws(() => cutUpValidate(version('nope')), /not a list/);
  assert.throws(() => cutUpValidate(version([{ piece: 'p006' }, null, null])), /bad src entry/);
  assert.throws(() => cutUpValidate(version([null, null]), PAGES), /2 entries for 3 lines/);
  assert.equal(cutUpValidate(version([null, null, null]), PAGES), 'cut-up');
});

test('reserve sources flags every non-Series pool', () => {
  const poolOf = pid => ({ p006: 'reserve', p004: 'archive', p007: 'unsorted', p008: 'unknown' }[pid] || 'series');
  const v = { id: 'p001-1', P: [['pg2', [0]], ['pg3', [0]]], method: 'cut-up',
    src: [{ piece: 'p006', line: 'diary54-0-0' }, { piece: 'p004', line: 'pg1-2-0' },
          { piece: 'p007', line: 'pg5-0-0' }, { piece: 'p008', line: 'pg5-1-0' },
          { piece: 'p003', line: 'pg3-0-0' }, null] };
  assert.deepEqual([...cutUpReserveSources(v, poolOf, PAGES).map(b => b.pool)],
    ['reserve', 'archive', 'unsorted', 'unknown']);
  // The pool definition is #65's: all four non-Series pools are withheld.
  assert.deepEqual([...CUT_UP_WITHHELD_POOLS], ['reserve', 'archive', 'unsorted', 'unknown']);
});

test('series sources and own lines pass', () => {
  // Length checks, not deepEqual: vm-realm arrays carry a different Array
  // prototype, and strict deepEqual rejects them (same reason the
  // mark-posted test spreads its results into this realm first).
  assert.equal(cutUpReserveSources(version([{ piece: 'p003', line: 'pg3-0-0' }, null, null]), () => 'series', PAGES).length, 0);
  assert.equal(cutUpReserveSources({ id: 'v' }, () => 'reserve').length, 0);
});

test('record requires parallel src and carries method and source version', () => {
  assert.throws(() => cutUpRecord('p001', ['a'], [null, null]), /must parallel/);
  const rec = cutUpRecord('p001', ['pg2-0-0'], [null], '2026-11-25T00:00:00Z', { method: 'erasure', sourceVersion: 'p001-0' });
  assert.equal(rec.method, 'erasure');
  assert.equal(rec.sourceVersion, 'p001-0');
  assert.equal(cutUpRecord('p001', ['pg2-0-0'], [null]).method, 'cut-up');
});

test('warning names the piece, line, and pool', () => {
  const text = cutUpWarningText('p001', [{ src: { piece: 'p006', line: 'diary54-0-0' }, pool: 'reserve' }]);
  assert.match(text, /p006 line diary54-0-0 \(pool is reserve\)/);
  assert.match(text, /Mark posted is refused/);
});

test('release warning trigger: a Series piece reusing a Reserve line', () => {
  // Synthetic versions-collection docs, as the Cut tab saves them: a
  // cut-up of p001 reusing a Reserve line, an erasure of p001 with only
  // Series sources, a cut-up of another piece, and an original version.
  // The trigger fires exactly on the Reserve reuse — that is the warning
  // firing in the Release tab (calDetail shows it and disables Mark
  // posted while the returned list is non-empty).
  const poolOf = pid => ({ p006: 'reserve', p003: 'series' }[pid] || 'unsorted');
  const versions = [
    { pieceId: 'p001', method: 'cut-up', lines: ['pg2-0-0'], src: [{ piece: 'p006', line: 'diary54-0-0' }] },
    { pieceId: 'p001', method: 'erasure', lines: ['pg2-0-1'], src: [{ piece: 'p003', line: 'pg3-0-0' }] },
    { pieceId: 'p002', method: 'cut-up', lines: ['pg2-1-0'], src: [{ piece: 'p006', line: 'diary54-0-0' }] },
    { pieceId: 'p001', method: 'original', lines: ['pg2-0-2'], src: undefined },
  ];
  const bad = cutUpBadVersions(versions, poolOf, 'p001');
  assert.equal(bad.length, 1);
  assert.equal(bad[0].src.piece, 'p006');
  assert.equal(bad[0].pool, 'reserve');
  assert.equal(cutUpBadVersions(versions, () => 'series', 'p001').length, 0);
  assert.equal(cutUpBadVersions(versions, poolOf, 'p002').length, 1);
});
