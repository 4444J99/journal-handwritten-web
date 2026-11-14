import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {reviewQueue, renderHtml, plan, checkOutputPath} from '../tools/release_report.mjs';

const source = {
  review: {
    pages: [
      {id: 'pg1', blocks: [{lines: [{id: 'a', tx: 'one'}, {id: 'b', tx: 'two <b>'}]}, {lines: [{id: 'c', tx: 'three'}]}]},
      {id: 'pg2', blocks: [{lines: [{id: 'd', tx: 'four'}]}]},
    ],
    items: [{id: 'p9', versions: [{page: 'pg1', blocks: [0, 1]}, {page: 'pg1', blocks: [0]}, {page: 'pg2', blocks: [0]}]}],
  },
};
const db = {reviews: {a: {status: 'confirmed'}, b: {status: 'corrected', text: 'x'}, c: {status: 'corrected'}}};

test('reviewQueue counts each line once per page and names the first waiting line', () => {
  const q = reviewQueue(source, db, 'p9');
  assert.deepEqual(q.map(r => [r.page, r.lines, r.confirmed, r.corrected, r.waiting, r.next]), [['pg1', 3, 1, 1, 1, 'three'], ['pg2', 1, 0, 0, 1, 'four']]);
  assert.deepEqual(reviewQueue(source, db, 'nope'), []);
});

const rows = [
  {piece: 'p9', first: 'A <poem>', pool: null, versions: 2, how: 'top of the stack', review: {lines: 4, confirmed: 1, corrected: 1}, ready: false, warnings: ['w & w'],
    blockers: [{name: 'series', detail: '', advice: 'Sort'}, {name: 'verified', detail: '2 unverified', advice: 'Read'}, {name: 'shared_scan:p8', detail: '', advice: 'Release p8'}]},
  {piece: 'p8', first: 'ok', pool: 'series', versions: 1, review: {lines: 1, confirmed: 1, corrected: 0}, ready: true, blockers: [], warnings: []},
];

test('plan orders steps cheapest first and groups pieces', () => {
  assert.deepEqual(plan(rows).map(s => [s.name, s.pieces]), [['series', ['p9']], ['shared_scan', ['p9']], ['verified', ['p9']]]);
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
});
