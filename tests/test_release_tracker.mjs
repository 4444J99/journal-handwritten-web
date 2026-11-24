import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { trackerRows, trackerCsv, unsortedPieces, TRACKER_SLOTS, TRACKER_CSV_HEADER, isPublicAppearance, addDaysISO, shortDateISO } from '../studio/release-tracker.mjs';

const SERIES = (over = {}) => ({
  key: 'p001', title: 'First poem', pool: 'series', verified: true, num: null,
  exposures: [], prepDone: 7, prepTotal: 7, batchStatus: 'filed', ...over,
});

test('exactly 100 rows; slots past the queue are blank and unassigned', () => {
  const rows = trackerRows({ series: [SERIES()], mode: 'fixed', start: '2026-11-02' });
  assert.equal(rows.length, TRACKER_SLOTS);
  assert.equal(rows[0].slot, 1);
  assert.equal(rows[0].pieceId, 'p001');
  assert.equal(rows[0].status, 'ready');
  for (const r of rows.slice(1)) {
    assert.equal(r.pieceId, '');
    assert.equal(r.title, '');
    assert.equal(r.status, 'unassigned');
    assert.equal(r.number, null);
    assert.equal(r.url, '');
    assert.equal(r.dateISO, '');
  }
});

test('fixed numbering assigns queue position; as-posted uses the recorded number only once posted', () => {
  const posted = SERIES({ key: 'p002', num: 4, exposures: [{ type: 'social', date: '2026-11-09', url: 'https://example.test/p002' }] });
  const fixed = trackerRows({ series: [SERIES(), posted], mode: 'fixed', start: '' });
  assert.equal(fixed[0].number, 1);
  assert.equal(fixed[1].number, 2);
  const asPosted = trackerRows({ series: [SERIES(), posted], mode: 'as-posted', start: '' });
  assert.equal(asPosted[0].number, null); // unposted in as-posted mode shows no number
  assert.equal(asPosted[1].number, 4);
  const undecided = trackerRows({ series: [SERIES(), posted], mode: '', start: '' });
  assert.equal(undecided[0].number, null);
  assert.equal(undecided[1].number, 4);
});

test('a Reserve piece can never receive a slot number', () => {
  const reserve = SERIES({ key: 'p099', title: 'Reserve poem', pool: 'reserve' });
  const rows = trackerRows({ series: [SERIES(), reserve, SERIES({ key: 'p003' })], mode: 'fixed', start: '' });
  const ids = rows.map(r => r.pieceId).filter(Boolean);
  assert.deepEqual(ids, ['p001', 'p003']); // the Reserve piece takes no slot; the queue compacts
  assert.ok(!rows.some(r => r.pieceId === 'p099'));
});

test('status follows the Calendar gates: posted, ready, in queue', () => {
  const posted = SERIES({ key: 'p010', exposures: [{ type: 'site', target: 'live', date: '2026-11-16', url: 'https://example.test/p010' }] });
  const stagingOnly = SERIES({ key: 'p011', exposures: [{ type: 'site', target: 'staging', date: '2026-11-16' }] });
  const unverified = SERIES({ key: 'p012', verified: false });
  const noBatch = SERIES({ key: 'p013', batchStatus: 'draft' });
  const prepOpen = SERIES({ key: 'p014', prepDone: 3 });
  const rows = trackerRows({ series: [posted, stagingOnly, unverified, noBatch, prepOpen], mode: 'fixed', start: '' });
  assert.equal(rows[0].status, 'posted');
  assert.equal(rows[1].status, 'ready'); // a staging exposure is not a public appearance, but the gates still pass
  assert.equal(rows[2].status, 'in queue');
  assert.equal(rows[3].status, 'in queue');
  assert.equal(rows[4].status, 'in queue');
});

test('posted rows carry the exposure date and URL; a bad URL is dropped, not shown', () => {
  const good = SERIES({ exposures: [{ type: 'social', date: '2026-11-09', url: 'https://example.test/x' }] });
  const bad = SERIES({ key: 'p020', exposures: [{ type: 'social', date: '2026-11-09', url: 'not a url' }] });
  const rows = trackerRows({ series: [good, bad], mode: 'fixed', start: '2026-11-02' });
  assert.equal(rows[0].status, 'posted');
  assert.equal(rows[0].dateISO, '2026-11-09');
  assert.equal(rows[0].url, 'https://example.test/x');
  assert.equal(rows[1].status, 'posted');
  assert.equal(rows[1].url, '');
});

test('unposted Series rows project the week date from the First-post date', () => {
  const rows = trackerRows({ series: [SERIES(), SERIES({ key: 'p002' }), SERIES({ key: 'p003' })], mode: 'fixed', start: '2026-11-02' });
  assert.equal(rows[0].dateISO, '2026-11-02');
  assert.equal(rows[1].dateISO, '2026-11-09');
  assert.equal(rows[2].dateISO, '2026-11-16');
  assert.equal(rows[0].dateLabel, 'Nov 2');
  const noStart = trackerRows({ series: [SERIES()], mode: 'fixed', start: '' });
  assert.equal(noStart[0].dateISO, '');
  assert.equal(noStart[0].dateLabel, '');
});

test('isPublicAppearance and date helpers match the studio rules', () => {
  assert.equal(isPublicAppearance({ type: 'social' }), true);
  assert.equal(isPublicAppearance({ type: 'site', target: 'staging' }), false);
  assert.equal(isPublicAppearance({ type: 'site', target: 'live' }), true);
  assert.equal(isPublicAppearance({ type: 'members' }), false);
  assert.equal(addDaysISO('2026-11-02', 7), '2026-11-09');
  assert.equal(addDaysISO('2026-12-28', 7), '2027-01-04');
  assert.equal(addDaysISO('', 7), '');
  assert.equal(addDaysISO('nope', 7), '');
  assert.equal(shortDateISO('2026-11-02'), 'Nov 2');
});

test('CSV export uses the packet schema and matches the derived rows', () => {
  const rows = trackerRows({ series: [SERIES({ key: 'p001', exposures: [{ type: 'social', date: '2026-11-09', url: 'https://example.test/p001' }] })], mode: 'fixed', start: '2026-11-02' });
  const csv = trackerCsv(rows);
  const lines = csv.trimEnd().split(/\r?\n/);
  assert.equal(lines.length, 101);
  assert.equal(lines[0], TRACKER_CSV_HEADER);
  assert.equal(lines[0], 'planning_slot,assigned_number,piece_id,status,confirmed_date,public_url');
  assert.equal(lines[1], '1,1,p001,posted,2026-11-09,https://example.test/p001');
  assert.equal(lines[2], '2,,,unassigned,,');
  // CRLF line endings, matching the packet CSVs byte for byte.
  assert.ok(csv.endsWith('\r\n'));
  assert.equal(csv.split('\r\n').length, 102);
  // Every line round-trips the row it was generated from.
  for (let i = 0; i < rows.length; i++) {
    const fields = lines[i + 1].split(',');
    assert.equal(Number(fields[0]), rows[i].slot);
    assert.equal(fields[2], rows[i].pieceId);
    assert.equal(fields[3], rows[i].status);
    assert.equal(fields[4], rows[i].dateISO);
    assert.equal(fields[5], rows[i].url);
  }
  // The packet CSV in the repo uses exactly this shape for unassigned slots.
  const packet = readFileSync(new URL('../release/packets/2026-11-05-t03-current/release-tracker-100-slots.csv', import.meta.url), 'utf8');
  const packetLines = packet.trimEnd().split(/\r?\n/);
  assert.equal(packetLines[0], TRACKER_CSV_HEADER);
  assert.equal(packetLines[1], '1,,,unassigned,,');
  assert.equal(packetLines.length, 101);
  assert.ok(packet.includes('\r\n'));
});

test('CSV fields with commas or quotes are escaped', () => {
  const rows = [{ slot: 1, number: 1, pieceId: 'p,001', status: 'ready', dateISO: '2026-11-02', url: 'https://example.test/a"b' }];
  const csv = trackerCsv(rows);
  assert.equal(csv.split('\r\n')[1], '1,1,"p,001",ready,2026-11-02,"https://example.test/a""b"');
});

test('unsortedPieces lists only pieces with no pool', () => {
  const out = unsortedPieces([
    { key: 'a', title: 'A', pool: '' },
    { key: 'b', title: 'B', pool: 'series' },
    { key: 'c', title: 'C', pool: 'reserve' },
    { key: 'd', title: 'D' },
  ]);
  assert.deepEqual(out, [
    { key: 'a', title: 'A', status: 'unsorted' },
    { key: 'd', title: 'D', status: 'unsorted' },
  ]);
});
