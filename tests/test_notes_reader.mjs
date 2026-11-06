import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mountNotesReader } from '../studio/notes-reader.mjs';
import * as Model from '../studio/notes-model.mjs';

// Small DOM harness for deterministic component tests. The private workbench
// provides the separate browser integration surface; no dependency or fetch.
class Node {
  constructor(document, tag) {
    this.ownerDocument = document; this.tagName = tag.toUpperCase();
    this.children = []; this.attributes = new Map(); this.listeners = new Map();
    this.style = {}; this.hidden = false; this.parentNode = null; this.value = '';
  }
  set textContent(value) { this.children = []; this.value = value; }
  get textContent() { return this.value + this.children.map(c => c.textContent).join(''); }
  get isConnected() { return this === this.ownerDocument.body || !!this.parentNode?.isConnected; }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  getAttribute(key) { return this.attributes.get(key) ?? null; }
  removeAttribute(key) { this.attributes.delete(key); }
  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  replaceChildren(...nodes) {
    for (const node of this.children) node.parentNode = null;
    this.children = []; this.value = ''; this.append(...nodes);
  }
  addEventListener(type, fn) { if (!this.listeners.has(type)) this.listeners.set(type, new Set()); this.listeners.get(type).add(fn); }
  removeEventListener(type, fn) { this.listeners.get(type)?.delete(fn); }
  dispatch(type, event = {}) { for (const fn of this.listeners.get(type) || []) fn(event); }
  focus() { this.ownerDocument.activeElement = this; }
  contains(other) { return other === this || this.children.some(child => child.contains(other)); }
  querySelector() { return this.children[0] || null; }
}
function dom() {
  const document = { createElement(tag) { return new Node(this, tag); }, listeners: new Map(),
    addEventListener:Node.prototype.addEventListener, removeEventListener:Node.prototype.removeEventListener,
    dispatch:Node.prototype.dispatch };
  document.body = new Node(document, 'body'); document.activeElement = document.body;
  const host = document.createElement('div'), trigger = document.createElement('button');
  document.body.append(trigger, host);
  return { document, host, trigger };
}
function descendants(root, tag) {
  return root.children.flatMap(node => [...(node.tagName === tag.toUpperCase() ? [node] : []), ...descendants(node, tag)]);
}
const record = (patch = {}) => ({
  id: 'fixture-note', revisionId: 'fixture-r2', family: 'note', kind: 'footnote',
  pieceId: 'p-fixture', versionId: 'v-original', lineId: 'line-1', word: null,
  text: 'TECHNICAL FIXTURE: revised note', citations: [{ label: 'Fixture source', url: 'https://example.invalid/source', locator: 'Section 1' }],
  credit: 'Fixture author', poemDate: { certainty: 'approximate', value: '2020-03' },
  noteDate: '2026-11-05', fixture: true, ...patch,
});
const context = records => ({ records, pieceId: 'p-fixture', versionId: 'v-original' });

test('empty at rest; explicit reveal scopes to exact piece and version and displays both dates and credit', () => {
  const { host, trigger, document } = dom();
  const reader = mountNotesReader(host, context([record(), record({ id: 'elsewhere', pieceId: 'other', text: 'DO NOT SHOW OTHER PIECE' }), record({ id: 'new-source', versionId: 'v-revised', text: 'DO NOT SHOW OTHER VERSION' })]));
  assert.equal(host.hidden, true); assert.equal(host.textContent, ''); assert.equal(host.children.length, 0);
  reader.reveal(trigger);
  assert.equal(reader.isOpen, true); assert.equal(host.hidden, false);
  assert.match(host.textContent, /TECHNICAL FIXTURE: revised note/);
  assert.match(host.textContent, /Fixture author/);
  assert.match(host.textContent, /2020-03 \(approximate\)/);
  assert.match(host.textContent, /2026-11-05/);
  assert.match(host.textContent, /Fixture source/);
  assert.match(host.textContent, /p-fixture · v-original · line-1/);
  assert.doesNotMatch(host.textContent, /DO NOT SHOW/);
  assert.equal(descendants(host, 'article').length, 1);
  assert.equal(document.activeElement, host.children[0]);
  reader.hide();
  assert.equal(host.hidden, true); assert.equal(host.textContent, '');
  assert.equal(trigger.getAttribute('aria-expanded'), 'false');
  assert.equal(document.activeElement, trigger);
});

test('stored revisions and private/unknown fields fail closed; citations and text never become markup or links', () => {
  const { host } = dom();
  const payload = '<img src="https://example.invalid/private" onerror="alert(1)">';
  const reader = mountNotesReader(host, context([
    record({ id: 'raw', author: { id: 'private-id' }, text: 'PRIVATE RAW REVISION' }),
    record({ id: 'dossier', kind: 'research-dossier', text: 'PRIVATE DOSSIER' }),
    record({ id: 'audit', citations: [{ label: 'PRIVATE AUDIT', permissionEvidence: 'private' }] }),
    record({ id: 'unsafe', text: payload, credit: '<script>private()</script>', citations: [{ label: payload, url: 'javascript:alert(1)' }] }),
  ]));
  reader.reveal();
  assert.doesNotMatch(host.textContent, /PRIVATE RAW|PRIVATE DOSSIER|PRIVATE AUDIT/);
  assert.ok(host.textContent.includes(payload));
  assert.equal(descendants(host, 'img').length, 0);
  assert.equal(descendants(host, 'script').length, 0);
  assert.equal(descendants(host, 'a').length, 0);
  assert.equal(descendants(host, 'article').length, 1);
});

test('source/projection changes clear stale content and require a fresh request', () => {
  const { host, trigger, document } = dom(), old = record();
  const reader = mountNotesReader(host, context([old]));
  old.text = 'MUTATED WITHOUT PROJECTION UPDATE';
  reader.reveal(trigger);
  assert.doesNotMatch(host.textContent, /MUTATED/);
  document.activeElement = document.body;
  reader.setContext({ records: [record({ versionId: 'v-revised', text: 'REVISED SOURCE FIXTURE' })], pieceId: 'p-fixture', versionId: 'v-revised' });
  assert.equal(reader.isOpen, false); assert.equal(host.hidden, true); assert.equal(host.textContent, '');
  assert.equal(document.activeElement, document.body);
  reader.reveal(trigger);
  assert.match(host.textContent, /REVISED SOURCE FIXTURE/);
  assert.doesNotMatch(host.textContent, /revised note/);
  reader.switchContext(context([]));
  reader.reveal(trigger);
  assert.match(host.textContent, /No cleared notes for this source version/);
  assert.equal(descendants(host, 'article').length, 0);
});

test('Escape and dismiss restore focus; destroy removes listeners and cannot reopen', () => {
  const { host, trigger, document } = dom();
  const reader = mountNotesReader(host, context([record()]));
  reader.reveal(trigger);
  let prevented = false, stopped = false;
  host.dispatch('keydown', { key: 'Escape', preventDefault() { prevented = true; }, stopPropagation() { stopped = true; } });
  assert.ok(prevented && stopped); assert.equal(host.textContent, ''); assert.equal(document.activeElement, trigger);
  reader.reveal(trigger);
  descendants(host, 'button')[0].dispatch('click');
  assert.equal(host.hidden, true); assert.equal(document.activeElement, trigger);
  reader.reveal(trigger); reader.destroy();
  assert.equal(host.textContent, ''); assert.equal(host.listeners.get('keydown').size, 0);
  reader.setContext(context([record()])); reader.reveal(trigger);
  assert.equal(reader.isOpen, false); assert.equal(host.textContent, '');
});

test('a contribution credits its contributor and preserves distinct note/poem dates without writing source records', () => {
  const { host } = dom();
  const input = record({ family: 'contribution', kind: 'critical-note', credit: 'Fixture contributor', poemDate: { certainty: 'unknown', value: null } });
  const before = JSON.stringify(input);
  const reader = mountNotesReader(host, context([input])); reader.reveal();
  assert.match(host.textContent, /Critical note/);
  assert.match(host.textContent, /CreditFixture contributor/);
  assert.match(host.textContent, /Poem dateUnknown/);
  assert.match(host.textContent, /Contribution date2026-11-05/);
  assert.equal(JSON.stringify(input), before);
});

test('real model projection renders a cleared contribution without permission evidence; source invalidation removes it', () => {
  const source = { pieces: [{ id: 'p-fixture', V: [{ id: 'v-original', P: [['page-fixture', [0]]] }] }] };
  const review = { pages: [{ id: 'page-fixture', blocks: [{ t: 'text', lines: [{ id: 'line-1', tx: 'TECHNICAL FIXTURE source line' }] }] }] };
  const catalog = Model.buildSourceCatalog(source, review);
  const draft = Model.createRevision({
    recordId: 'fixture-contribution', family: 'contribution', type: 'critical-note',
    author: { id: 'private-fixture-person-id', credit: 'Fixture contributor', provenance: 'technical-fixture' },
    poemDate: { certainty: 'recorded', value: '2020-03-01' }, noteDate: '2026-11-05',
    anchor: Model.createAnchor(catalog, { pieceId: 'p-fixture', versionId: 'v-original', lineId: 'line-1' }),
    text: 'TECHNICAL FIXTURE contribution text', citations: [{ label: 'Fixture citation without a URL' }],
    visibility: 'public-candidate', fixture: true, changeReason: 'Fixture initialization',
    permission: { status: 'granted', scopes: ['web'], evidence: 'PRIVATE PERMISSION EVIDENCE', recordedBy: 'private-reviewer-id', recordedAt: '2026-11-05T12:00:00Z' },
  }, { revisionId: 'fixture-draft', at: '2026-11-05T12:00:00Z' });
  const accepted = Model.transitionRevision(draft, 'accept', { revisionId: 'fixture-accepted', actor: 'private-reviewer-id', at: '2026-11-05T12:01:00Z' });
  const cleared = Model.transitionRevision(accepted, 'clear', { revisionId: 'fixture-cleared', actor: 'private-reviewer-id', at: '2026-11-05T12:02:00Z' });
  const revisions = [draft, accepted, cleared];
  const options = { versions: [{ pieceId: 'p-fixture', versionId: 'v-original' }], allowFixtures: true };
  const projected = Model.projectPreview(revisions, catalog, options);
  assert.equal(projected.records.length, 1);
  const { host } = dom(), reader = mountNotesReader(host, context(projected.records));
  reader.reveal();
  assert.match(host.textContent, /Fixture contributor/);
  assert.match(host.textContent, /Fixture citation without a URL/);
  assert.doesNotMatch(host.textContent, /PRIVATE PERMISSION|private-fixture-person|private-reviewer/);
  assert.equal(Model.projectRecords(revisions, catalog, { ...options, mode: 'public' }).records.length, 0);
  const changed = Model.buildSourceCatalog(source, review, { reviews: { 'line-1': { status: 'corrected', original: 'TECHNICAL FIXTURE source line', text: 'TECHNICAL FIXTURE changed source' } } });
  const invalidated = Model.projectPreview(revisions, changed, options);
  assert.equal(invalidated.records.length, 0);
  assert.ok(invalidated.excluded[0].reasons.includes('source-version-changed'));
  reader.setContext(context(invalidated.records));
  assert.equal(host.hidden, true); assert.equal(host.textContent, '');
  reader.reveal();
  assert.equal(descendants(host, 'article').length, 0);
  assert.doesNotMatch(host.textContent, /contribution text/);
});
