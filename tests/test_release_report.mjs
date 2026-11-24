import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {reviewQueue, renderHtml, plan, checkOutputPath} from '../tools/release_report.mjs';
import {assess} from '../tools/release_readiness.mjs';
import {fixture} from '../studio-cf/tests/helpers/publish-fixture.mjs';

const source = {
  review: {
    pages: [
      {id: 'pg1', blocks: [{lines: [{id: 'a', tx: 'one'}, {id: 'b', tx: 'two <b>'}]}, {lines: [{id: 'c', tx: 'three'}]}]},
      {id: 'pg2', blocks: [{lines: [{id: 'd', tx: 'four'}]}]},
    ],
    items: [{id: 'p9', versions: [{page: 'pg1', blocks: [0, 1]}, {page: 'pg1', blocks: [0]}, {page: 'pg2', blocks: [0]}]}],
  },
};
const db = {reviews: {a: {status: 'confirmed', original: 'one'}, b: {status: 'corrected', text: 'x', original: 'two <b>'}, c: {status: 'corrected', original: 'three'}}};

test('reviewQueue counts each line once per page and names the first waiting line', () => {
  const q = reviewQueue(source, db, 'p9');
  assert.deepEqual(q.map(r => [r.page, r.lines, r.confirmed, r.corrected, r.waiting, r.next]), [['pg1', 3, 1, 1, 1, 'three'], ['pg2', 1, 0, 0, 1, 'four']]);
  assert.deepEqual(reviewQueue(source, db, 'nope'), []);
});

test('a review of since-changed text goes back to waiting, as the gate stops it as stale', () => {
  const stale = {reviews: {...db.reviews, a: {status: 'confirmed', original: 'older wording'}}};
  const q = reviewQueue(source, stale, 'p9');
  assert.deepEqual([q[0].confirmed, q[0].waiting, q[0].next], [0, 2, 'one']);
});

const rows = [
  {piece: 'p9', first: 'A <poem>', pool: null, versions: 2, how: 'top of the stack', review: {lines: 4, confirmed: 1, corrected: 1}, ready: false, warnings: ['w & w'],
    blockers: [{name: 'series', detail: '', advice: 'Sort'}, {name: 'verified', detail: '2 unverified', advice: 'Read'}, {name: 'shared_scan:p8', detail: '', advice: 'Release p8'}]},
  {piece: 'p8', first: 'ok', pool: 'series', versions: 1, review: {lines: 1, confirmed: 1, corrected: 0}, ready: true, blockers: [], warnings: []},
];

test('plan orders steps cheapest first and groups pieces', () => {
  assert.deepEqual(plan(rows).map(s => [s.name, s.pieces]), [['series', ['p9']], ['shared_scan:p8', ['p9']], ['verified', ['p9']]]);
  const two = [{piece: 'a', blockers: [{name: 'shared_scan:p8', advice: 'Release p8'}]}, {piece: 'b', blockers: [{name: 'shared_scan:p11', advice: 'Release p11'}]}];
  assert.deepEqual(plan(two).map(s => [s.advice, s.pieces]), [['Release p8', ['a']], ['Release p11', ['b']]]);
});

test('renderHtml escapes text, is noindex, and loads nothing external', () => {
  const html = renderHtml({rows, queues: {p9: reviewQueue(source, db, 'p9')}, meta: {target: 'staging', db: 'exp<1>'}});
  assert.match(html, /noindex/);
  assert.match(html, /1 of 2 pieces pass every gate/);
  assert.ok(!html.includes('<poem>') && !html.includes('<b>') && !html.includes('exp<1>'));
  assert.ok(html.includes('A &lt;poem&gt;') && html.includes('w &amp; w'));
  assert.ok(!/(src|href)=|<script|@import|url\(/.test(html));
});

test('checkOutputPath refuses tracked destinations inside the repo and allows outside or ignored ones', () => {
  const root = mkdtempSync(join(tmpdir(), 'rr-repo-'));
  spawnSync('git', ['init', '-q', root]);
  mkdirSync(join(root, 'site'));
  spawnSync('sh', ['-c', `printf '/readiness-report/\\n' > '${root}/.gitignore'`]);
  assert.equal(checkOutputPath(join(root, 'site/x.html'), root).ok, false);
  assert.equal(checkOutputPath(join(root, 'readiness-report/index.html'), root).ok, true);
  assert.equal(checkOutputPath(join(tmpdir(), 'elsewhere.html'), root).ok, true);
  const outside = mkdtempSync(join(tmpdir(), 'rr-out-'));
  symlinkSync(join(root, 'site'), join(outside, 'link'));
  assert.equal(checkOutputPath(join(outside, 'link', 'x.html'), root).ok, false);
  assert.equal(checkOutputPath(join(outside, 'link', 'new', 'x.html'), root).ok, false);
});

// Lanes (JHW #41): lane data on a release record changes neither the
// readiness assessment nor the report that renders it.
test('the report renders unchanged when a release record carries lane data', async () => {
  const f = fixture();
  const plain = await assess({...f, pieces: ['p001']});
  assert.equal(plain[0].ready, true);
  f.db.release.p001.lanes = {
    translation: {state: 'ready', date: '2026-11-20'},
    audio: {state: 'posted', url: 'https://example.test/audio', date: '2026-11-21'},
  };
  const withLanes = await assess({...f, pieces: ['p001']});
  assert.deepEqual(withLanes, plain);
  const html = renderHtml({rows: withLanes, queues: {}, meta: {target: 'staging', db: 'fixture'}});
  assert.match(html, /p001/);
  assert.match(html, /Ready/);
  assert.match(html, /1 of 1 pieces pass every gate/);
});
