import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import {
  validateSidecar, indexSidecar, numberEndnotes, marksForLine,
  apparatusForPiece, markHTML, markGlyph, recordLabel, dualDateText,
} from '../site/notes-layer.mjs';
import {
  buildSourceCatalog, createAnchor, validateAnchor, createRevision,
  validateRevision, restoreEnvelope, transitionRevision, projectPreview,
} from '../studio/notes-model.mjs';

// journal-handwritten-web #17: the public notes layer. All authored bodies
// below are explicit synthetic technical fixtures. The compact source is
// independent of the author's poetry and is never emitted to site/.
// The real-repository checks at the end only read existing files.

const AT = '2026-11-27T15:33:01.000Z';
const source = {
  provenance: { kind: 'technical-fixture', source: 'tests/test_notes_layer.mjs' },
  pieces: [{ id: 'p001', V: [
    { id: 'p001-diary1-0', P: [['diary1', [0, 1]]], d: '2000-01-01' },
    { id: 'p001-diary2-0', P: [['diary2', [0]]], d: null },
  ] }, { id: 'p002', V: [{ id: 'p002-diary3-0', P: [['diary3', [0]]], d: null }] }],
};
const review = {
  items: [{ id: 'p001', versions: [{ page: 'diary2', blocks: [0] }, { page: 'diary1', blocks: [0, 1] }] }],
  pages: [
    { id: 'diary1', w: 100, h: 200, blocks: [
      { t: 'text', lines: [
        { id: 'diary1-0-0', tx: '[TECHNICAL FIXTURE] first source line', box: [0, 0, 10, 10] },
        { id: 'diary1-0-1', tx: '[TECHNICAL FIXTURE] second source line', box: [0, 20, 10, 10] },
      ] },
      { t: 'quotation', lines: [
        { id: 'diary1-1-0', tx: '[TECHNICAL FIXTURE] immutable quotation block', box: [0, 40, 10, 10] },
      ] },
    ] },
    { id: 'diary2', blocks: [{ t: 'text', lines: [{ id: 'diary2-0-0', tx: '[TECHNICAL FIXTURE] other version' }] }] },
    { id: 'diary3', blocks: [{ t: 'text', lines: [{ id: 'diary3-0-0', tx: '[TECHNICAL FIXTURE] other piece' }] }] },
  ],
};
const catalog = buildSourceCatalog(source, review);
const anchor = createAnchor(catalog, { pieceId: 'p001', versionId: 'p001-diary1-0', lineId: 'diary1-0-0' });

let sequence = 0;
function sidecarRecord(changes = {}) {
  const id = 'fixture-' + (++sequence);
  return {
    id, revisionId: 'rev-' + id, family: 'note', kind: 'footnote',
    pieceId: 'p001', versionId: 'p001-diary1-0', lineId: 'diary1-0-0', word: null,
    text: '[TECHNICAL FIXTURE — not author text] Note placement test.',
    citations: [], credit: 'Technical fixture author',
    poemDate: { certainty: 'unknown', value: null }, noteDate: '2026-11-27',
    fixture: false, ...changes,
  };
}
function sidecar(records) {
  return { format: 'versforms-notes-sidecar', version: 1, generatedAt: AT, provenance: {}, records };
}

test('empty sidecar validates with no records and no errors', () => {
  const { records, errors } = validateSidecar(sidecar([]));
  assert.deepEqual(records, []);
  assert.deepEqual(errors, []);
});

test('valid footnote, endnote and critical-note records all validate', () => {
  const { records, errors } = validateSidecar(sidecar([
    sidecarRecord(),
    sidecarRecord({ kind: 'endnote' }),
    sidecarRecord({ kind: 'critical-note', lineId: null }),
    sidecarRecord({ kind: 'critical-note', pieceId: null, versionId: null, lineId: null }),
  ]));
  assert.equal(records.length, 4);
  assert.deepEqual(errors, []);
});

test('the plan word "essay" is not a sidecar kind', () => {
  // notes-v1 has no "essay" kind; the apparatus type is critical-note.
  const { records, errors } = validateSidecar(sidecar([sidecarRecord({ kind: 'essay' })]));
  assert.equal(records.length, 0);
  assert.match(errors.join('; '), /kind must be one of/);
});

test('fixtures and research dossiers never project to the sidecar', () => {
  const { records: withFixture } = validateSidecar(sidecar([sidecarRecord({ fixture: true })]));
  assert.equal(withFixture.length, 0);
  const { records: dossier } = validateSidecar(sidecar([sidecarRecord({ kind: 'research-dossier' })]));
  assert.equal(dossier.length, 0);
});

test('bad dates, citations and word selectors are dropped', () => {
  const cases = [
    sidecarRecord({ noteDate: '2026-02-30' }),
    sidecarRecord({ noteDate: '27 November 2026' }),
    sidecarRecord({ citations: [{ url: 'https://example.test' }] }),
    sidecarRecord({ citations: [{ label: 'x', url: 'https://user:pass@example.test/' }] }),
    sidecarRecord({ word: { quote: 'first', start: 5, end: 5 } }),
    sidecarRecord({ word: { quote: 'first', start: 0, end: 3 }, lineId: null, kind: 'critical-note' }),
    sidecarRecord({ kind: 'critical-note', versionId: null }),
    sidecarRecord({ kind: 'footnote', lineId: null }),
    sidecarRecord({ text: '   ' }),
  ];
  for (const rec of cases) {
    const { records, errors } = validateSidecar(sidecar([rec]));
    assert.equal(records.length, 0, JSON.stringify(rec));
    assert.ok(errors.length > 0, JSON.stringify(rec));
  }
});

test('a wrong envelope trusts no record', () => {
  const { records, errors } = validateSidecar({ format: 'versforms-notes-sidecar', version: 2, records: [sidecarRecord()] });
  assert.equal(records.length, 0);
  assert.match(errors.join('; '), /version must be 1/);
});

test('endnotes number across the series in catalog order, not sidecar order', () => {
  const a = sidecarRecord({ kind: 'endnote', pieceId: 'p002', versionId: 'p002-diary3-0', lineId: 'diary3-0-0' });
  const b = sidecarRecord({ kind: 'endnote', pieceId: 'p001', versionId: 'p001-diary1-0', lineId: 'diary1-0-1' });
  const c = sidecarRecord({ kind: 'endnote', pieceId: 'p001', versionId: 'p001-diary1-0', lineId: 'diary1-0-0' });
  const numbers = numberEndnotes([a, b, c], ['p001', 'p002']);
  assert.equal(numbers.get(c.id), 1);
  assert.equal(numbers.get(b.id), 2);
  assert.equal(numbers.get(a.id), 3);
  // Inserting a later endnote leaves earlier numbers alone.
  const d = sidecarRecord({ kind: 'endnote', pieceId: 'p002', versionId: 'p002-diary3-0', lineId: 'diary3-0-0' });
  const renumbered = numberEndnotes([a, b, c, d], ['p001', 'p002']);
  assert.equal(renumbered.get(c.id), 1);
  assert.equal(renumbered.get(a.id), 3);
  assert.equal(renumbered.get(d.id), 4);
});

test('marks group by exact line; apparatus groups by piece and series', () => {
  const foot = sidecarRecord();
  const end = sidecarRecord({ kind: 'endnote', lineId: 'diary1-0-1' });
  const pieceEssay = sidecarRecord({ kind: 'critical-note', lineId: null });
  const seriesEssay = sidecarRecord({ kind: 'critical-note', pieceId: null, versionId: null, lineId: null });
  const index = indexSidecar([foot, end, pieceEssay, seriesEssay]);
  assert.deepEqual(marksForLine(index, 'p001', 'p001-diary1-0', 'diary1-0-0').map(r => r.id), [foot.id]);
  assert.deepEqual(marksForLine(index, 'p001', 'p001-diary1-0', 'diary1-0-1').map(r => r.id), [end.id]);
  assert.deepEqual(marksForLine(index, 'p001', 'p001-diary1-0', 'diary1-1-0'), []);
  assert.deepEqual(marksForLine(index, 'p001', 'p001-diary2-0', 'diary1-0-0'), []);
  const ap = apparatusForPiece(index, 'p001');
  assert.deepEqual(ap.piece.map(r => r.id), [pieceEssay.id]);
  assert.deepEqual(ap.series.map(r => r.id), [seriesEssay.id]);
  assert.deepEqual(apparatusForPiece(index, 'p002'), { piece: [], series: [seriesEssay] });
});

test('mark glyphs: footnote dagger, endnote number, critical-note section sign', () => {
  const numbers = new Map();
  const end = sidecarRecord({ kind: 'endnote' });
  numbers.set(end.id, 3);
  assert.equal(markGlyph(sidecarRecord(), numbers), '†');
  assert.equal(markGlyph(end, numbers), '3');
  assert.equal(markGlyph(sidecarRecord({ kind: 'critical-note' }), numbers), '§');
  assert.equal(recordLabel(end, numbers), 'Endnote 3');
  assert.equal(recordLabel(sidecarRecord(), numbers), 'Footnote');
});

test('mark HTML escapes record ids and labels', () => {
  const html = markHTML([{ ...sidecarRecord(), id: 'a"b<c' }], new Map());
  assert.match(html, /data-note-mark="a&quot;b&lt;c"/);
  assert.doesNotMatch(html, /<script/);
});

test('reference file: the committed envelope is empty and restores clean', () => {
  const envelope = JSON.parse(readFileSync(new URL('../studio/data/reading-notes.json', import.meta.url), 'utf8'));
  assert.equal(envelope.format, 'versforms-notes-backup');
  assert.equal(envelope.version, 1);
  const restored = restoreEnvelope(envelope);
  assert.deepEqual(restored, { notes: [], contributions: [] });
});

test('reference file: a well-formed fixture note restores; bad citations and dangling anchors fail', () => {
  let n = 0;
  const note = (changes = {}) => createRevision({
    family: 'note', recordId: 'fixture-ref-' + (++n), revisionId: 'rev-fixture-ref-' + n,
    author: { id: 'private-fixture-identity', credit: 'Technical fixture author', provenance: 'technical-fixture', sourceIds: ['tests/test_notes_layer.mjs'] },
    poemDate: { certainty: 'unknown', value: null }, noteDate: '2026-11-27', anchor,
    kind: 'footnote', text: '[TECHNICAL FIXTURE — not author text] Reference-file note.',
    fixture: true, ...changes,
  }, { at: AT });
  const restored = restoreEnvelope({ format: 'versforms-notes-backup', version: 1, exportedAt: AT, notes: [note()], contributions: [] });
  assert.equal(restored.notes.length, 1);

  // A note with an invented citation (no label) is not a valid revision:
  // build it literally, since createRevision itself refuses it.
  const good = note();
  const badCitation = { ...good, citations: [{ url: 'https://example.test' }] };
  const checked = validateRevision(badCitation);
  assert.equal(checked.valid, false);
  assert.match(checked.errors.join('; '), /invalid citation label/);
  assert.throws(() => restoreEnvelope({
    format: 'versforms-notes-backup', version: 1, exportedAt: AT,
    notes: [badCitation], contributions: [],
  }), /Invalid revision/);

  // A dangling anchor fails at creation: the line is not in the version.
  assert.throws(
    () => createAnchor(catalog, { pieceId: 'p001', versionId: 'p001-diary1-0', lineId: 'diary1-9-9' }),
    /Line is not a member of this source version/,
  );
  const tampered = { ...anchor, versionFingerprint: 'sha256:' + '0'.repeat(64) };
  assert.equal(validateAnchor(catalog, tampered).valid, false);
  assert.ok(validateAnchor(catalog, tampered).reasons.includes('source-version-changed'));
});

test('live sidecar: the committed file validates with no dropped records', () => {
  const data = JSON.parse(readFileSync(new URL('../site/data/notes.json', import.meta.url), 'utf8'));
  const { records, errors } = validateSidecar(data);
  assert.deepEqual(errors, []);
  assert.equal(records.length, data.records.length);
});

test('studio tab wiring: the Notes tab loads the workbench', () => {
  const html = readFileSync(new URL('../studio/index.html', import.meta.url), 'utf8');
  assert.match(html, /<button role="tab" data-view="notes" aria-selected="false">Notes<\/button>/);
  assert.match(html, /<section id="v-notes" class="view" hidden><\/section>/);
  assert.match(html, /if \(v === 'notes'\) renderNotesTab\(\);/);
  assert.match(html, /function renderNotesTab\(\)/);
  assert.match(html, /frame\.src = 'notes\.html'/);
  // The standalone workbench link stays: the verify_notes harness clicks it.
  assert.match(html, /<a href="notes\.html">Notes &amp; contributions<\/a>/);
});

test('reader wiring: sidecar loads at boot and marks render on all three surfaces', () => {
  const html = readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
  assert.match(html, /await Promise\.all\(\[loadData\(\), loadPools\(\), loadNotes\(\)/);
  assert.match(html, /prepData\(d\);\s*initNotes\(\);/);
  assert.match(html, /function lineNotesHTML\(p, bi, li\)/);
  assert.match(html, /\$\{lineNotesHTML\(p, bi, li\)\}/);
  assert.match(html, /rectMarkSVG\(p, b, l, x1, y0, y1\)/);
  assert.match(html, /e\.target\.closest\("\[data-note-mark\]"\)/);
  assert.match(html, /hitEl\.closest\("\[data-note-mark\]"\)/);
  assert.match(html, /<div class="panel" id="notes-panel" role="dialog"/);
  assert.match(html, /function openNotesPanel\(recordId, trigger\)/);
  assert.match(html, /function apparatusHTML\(p\)/);
  assert.match(html, /\$\{apparatusHTML\(p\)\}/);
  assert.match(html, /<section class="apparatus" aria-label="Critical apparatus">/);
});

test('reader wiring: no invitation or submission UI in the apparatus', () => {
  const html = readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
  const start = html.indexOf('function apparatusHTML(p)');
  assert.notEqual(start, -1);
  const block = html.slice(start, html.indexOf('function applyFocus', start));
  // No interactive controls at all: the section only renders records. (The
  // disclaimer sentence itself names invitations/submissions to say there
  // are none, so the check is on controls, not words.)
  assert.doesNotMatch(block, /<form|<input|<button|<a href|<select|<textarea/);
});

test('dual dates: recorded, approximate and unknown poem dates (JHW #18)', () => {
  assert.equal(
    dualDateText({ poemDate: { certainty: 'recorded', value: '2015-03' }, noteDate: '2026-11-05' }),
    'Poem 2015-03 · Note 2026-11-05');
  assert.equal(
    dualDateText({ poemDate: { certainty: 'approximate', value: '2015' }, noteDate: '2026-11-05' }),
    'Poem c. 2015 · Note 2026-11-05');
  assert.equal(
    dualDateText({ poemDate: { certainty: 'unknown', value: null }, noteDate: '2026-11-05' }),
    'Poem undated · Note 2026-11-05');
  // An unknown poem date never renders as a guessed year.
  assert.doesNotMatch(
    dualDateText({ poemDate: { certainty: 'unknown', value: null }, noteDate: '2026-11-05' }),
    /2015|2016/);
  // A malformed poem date degrades to undated instead of throwing.
  assert.equal(dualDateText({ noteDate: '2026-11-05' }), 'Poem undated · Note 2026-11-05');
  assert.equal(dualDateText({ poemDate: { certainty: 'recorded', value: '' }, noteDate: '2026-11-05' }),
    'Poem undated · Note 2026-11-05');
});

test('a cleared reflection reaches the sidecar as a numbered endnote (JHW #18)', () => {
  // Build the reflection through the model (private kind 'reflection'),
  // clear it, and project: the public record must arrive as kind
  // 'endnote' with both dates, or the sidecar validator drops it.
  const draft = createRevision({
    family: 'note', recordId: 'fixture-refl-layer', revisionId: 'rev-fixture-refl-layer',
    author: { id: 'private-fixture-identity', credit: 'Technical fixture author', provenance: 'technical-fixture', sourceIds: ['tests/test_notes_layer.mjs'] },
    poemDate: { certainty: 'recorded', value: '2015-03' }, noteDate: '2026-11-05', anchor,
    kind: 'reflection', visibility: 'public-candidate',
    text: '[TECHNICAL FIXTURE — not author text] Retrospective reflection fixture.',
    fixture: true,
  }, { at: AT });
  const accepted = transitionRevision(draft, 'accept', { actor: 'fixture-reviewer', at: AT, revisionId: 'event-fixture-refl-accept' });
  const cleared = transitionRevision(accepted, 'clear', { actor: 'fixture-reviewer', at: AT, revisionId: 'event-fixture-refl-clear' });
  const projected = projectPreview([draft, accepted, cleared], catalog,
    { versions: [{ pieceId: 'p001', versionId: 'p001-diary1-0' }], allowFixtures: true });
  assert.equal(projected.records.length, 1);
  assert.equal(projected.records[0].kind, 'endnote');
  // The boundary, pinned: a record that still says kind 'reflection'
  // is not a sidecar kind and is dropped.
  const unmapped = validateSidecar(sidecar([{ ...projected.records[0], kind: 'reflection', fixture: false }]));
  assert.equal(unmapped.records.length, 0);
  assert.match(unmapped.errors.join('; '), /kind must be one of/);
  // The mapped record validates and numbers as an endnote.
  const { records, errors } = validateSidecar(sidecar([{ ...projected.records[0], fixture: false }]));
  assert.deepEqual(errors, []);
  assert.equal(records.length, 1);
  const numbers = numberEndnotes(records, ['p001', 'p002']);
  assert.equal(numbers.get(records[0].id), 1);
  assert.equal(recordLabel(records[0], numbers), 'Endnote 1');
  assert.equal(markGlyph(records[0], numbers), '1');
  assert.equal(dualDateText(records[0]), 'Poem 2015-03 · Note 2026-11-05');
});

test('reader wiring: reveal panel and apparatus show both dates on tap (JHW #18)', () => {
  const html = readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
  // Both meta sites format through the shared dual-date helper, not
  // through a bare noteDate: the poem date must be visible on tap.
  assert.match(html, /NOTES_LAYER\.dualDateText\(rec\)/);
  const apparatus = html.slice(html.indexOf('function apparatusHTML(p)'), html.indexOf('function applyFocus', html.indexOf('function apparatusHTML(p)')));
  assert.match(apparatus, /dualDateText\(rec\)/);
  assert.doesNotMatch(apparatus, /rec\.noteDate/);
  const panel = html.slice(html.indexOf('function openNotesPanel'), html.indexOf('function closeNotesPanel'));
  assert.match(panel, /dualDateText\(rec\)/);
  assert.doesNotMatch(panel, /rec\.noteDate/);
});
