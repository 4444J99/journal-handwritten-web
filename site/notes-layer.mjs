// Public notes layer (journal-handwritten-web #17).
//
// The reader-side half of the notes sidecar (site/data/notes.json): pure
// functions over the sidecar JSON -- no DOM, no fetch -- so `node --test`
// covers them directly and the reader (site/index.html) owns fetch + DOM.
//
// A sidecar record is a projected public-candidate note (notes-model
// projectPreview allowlist): only what the author wrote in the studio
// Notes tab, had editorially accepted, and cleared for release review.
// Technical fixtures and research dossiers never project. The sidecar
// carries no stored endnote numbers: endnotes are numbered at render time,
// in series order, so a number is stable for a given set of records.
//
// Kinds: footnote / endnote / critical-note. The #17 plan's word "essay"
// for the apparatus type is the schema's critical-note kind -- notes-v1
// has no "essay" kind, so the sidecar does not invent one. A critical-note
// anchored to a line renders as a mark like the others; one anchored to a
// whole version or to the whole series (all three ids null) renders in the
// apparatus section only.

export const SIDECAR_FORMAT = 'versforms-notes-sidecar';
export const SIDECAR_VERSION = 1;

export const SIDECAR_KINDS = Object.freeze(['footnote', 'endnote', 'critical-note']);

export const SIDECAR_FIELDS = Object.freeze([
  'id', 'revisionId', 'family', 'kind', 'pieceId', 'versionId', 'lineId',
  'word', 'text', 'citations', 'credit', 'poemDate', 'noteDate', 'fixture',
]);

const ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const CERTAINTIES = new Set(['unknown', 'recorded', 'approximate']);

const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isNonEmptyString = value => typeof value === 'string' && value.trim().length > 0;

function isRealDate(value) {
  if (!DATE.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

// The model's rule: http(s) only, and no credentials in the URL.
function validCitationUrl(value) {
  if (!isNonEmptyString(value)) return false;
  try {
    const url = new URL(value);
    return (url.protocol === 'http:' || url.protocol === 'https:') && !url.username && !url.password;
  } catch {
    return false;
  }
}

// Shape-only validation. Anchor membership (does this version/line exist in
// the frozen id-map?) is the build-time gate's job
// (tools/notes_sidecar.py --check); the reader must never break on a stale
// file, so invalid records are dropped here with their reasons collected.
export function validateSidecar(data) {
  const errors = [];
  if (!isObject(data)) return { records: [], errors: ['sidecar is not an object'] };
  if (data.format !== SIDECAR_FORMAT) errors.push(`format must be '${SIDECAR_FORMAT}'`);
  if (data.version !== SIDECAR_VERSION) errors.push(`version must be ${SIDECAR_VERSION}`);
  if (!Array.isArray(data.records)) {
    errors.push('records must be an array');
    return { records: [], errors };
  }
  // A wrong envelope is not a sidecar: no record from it is trusted.
  if (errors.length) return { records: [], errors };
  const records = [];
  const seen = new Set();
  for (const [i, rec] of data.records.entries()) {
    const where = `records[${i}]`;
    const errorCount = errors.length;
    if (!isObject(rec)) { errors.push(`${where}: not an object`); continue; }
    const bad = [];
    for (const key of Object.keys(rec)) if (!SIDECAR_FIELDS.includes(key)) bad.push(key);
    if (bad.length) errors.push(`${where}: unknown fields: ${bad.join(', ')}`);
    if (!isNonEmptyString(rec.id) || !ID.test(rec.id)) errors.push(`${where}: bad id`);
    if (!isNonEmptyString(rec.revisionId) || !ID.test(rec.revisionId)) errors.push(`${where}: bad revisionId`);
    if (seen.has(rec.id)) errors.push(`${where}: duplicate record id ${rec.id}`);
    seen.add(rec.id);
    if (rec.family !== 'note') errors.push(`${where}: family must be 'note'`);
    if (!SIDECAR_KINDS.includes(rec.kind)) errors.push(`${where}: kind must be one of ${SIDECAR_KINDS.join(', ')}`);
    if (rec.fixture !== false) errors.push(`${where}: fixture must be false in the public sidecar`);
    if (!isNonEmptyString(rec.text)) errors.push(`${where}: text must be non-empty`);
    if (!isNonEmptyString(rec.credit)) errors.push(`${where}: credit must be non-empty`);
    if (!isRealDate(rec.noteDate)) errors.push(`${where}: noteDate must be a real YYYY-MM-DD date`);
    if (!isObject(rec.poemDate) || !CERTAINTIES.has(rec.poemDate.certainty) ||
        (rec.poemDate.value !== null && !isNonEmptyString(rec.poemDate.value))) {
      errors.push(`${where}: poemDate must be {certainty, value}`);
    }
    if (!Array.isArray(rec.citations) ||
        rec.citations.some(c => !isObject(c) || Object.keys(c).some(k => !['label', 'url', 'locator'].includes(k)) ||
          !isNonEmptyString(c.label) ||
          (c.url !== undefined && !validCitationUrl(c.url)) ||
          (c.locator !== undefined && !isNonEmptyString(c.locator)))) {
      errors.push(`${where}: citations must be [{label, url?, locator?}] with non-empty labels`);
    }
    for (const key of ['pieceId', 'versionId', 'lineId']) {
      if (rec[key] !== null && !isNonEmptyString(rec[key])) errors.push(`${where}: ${key} must be a string or null`);
    }
    const { pieceId, versionId, lineId, kind } = rec;
    if (kind === 'footnote' || kind === 'endnote') {
      if (!isNonEmptyString(pieceId) || !isNonEmptyString(versionId) || !isNonEmptyString(lineId)) {
        errors.push(`${where}: ${kind} needs pieceId, versionId and lineId`);
      }
    } else if (kind === 'critical-note') {
      const series = pieceId === null && versionId === null && lineId === null;
      const versioned = isNonEmptyString(pieceId) && isNonEmptyString(versionId);
      if (!series && !versioned) errors.push(`${where}: critical-note anchor must be a line, a version, or the series`);
    }
    if (rec.word !== null) {
      if (!isObject(rec.word) || Object.keys(rec.word).sort().join(',') !== 'end,quote,start' ||
          !isNonEmptyString(rec.word.quote) || !Number.isInteger(rec.word.start) ||
          !Number.isInteger(rec.word.end) || rec.word.start < 0 || rec.word.end <= rec.word.start) {
        errors.push(`${where}: word must be {quote, start, end} with 0 <= start < end`);
      } else if (!isNonEmptyString(lineId)) {
        errors.push(`${where}: a word selector needs a line anchor`);
      }
    }
    // A record is kept only if this pass added no error naming it.
    const before = errorCount;
    if (errors.length === before) records.push(rec);
  }
  return { records, errors };
}

// Index records for the reader: marks by line, apparatus by piece/series.
export function indexSidecar(records) {
  const byLine = new Map();
  const byPiece = new Map();
  const series = [];
  for (const rec of records) {
    if (rec.kind === 'critical-note' && rec.pieceId === null) { series.push(rec); continue; }
    if (rec.kind === 'critical-note' && rec.lineId === null) {
      if (!byPiece.has(rec.pieceId)) byPiece.set(rec.pieceId, []);
      byPiece.get(rec.pieceId).push(rec);
      continue;
    }
    const key = `${rec.pieceId}\0${rec.versionId}\0${rec.lineId ?? ''}`;
    if (!byLine.has(key)) byLine.set(key, []);
    byLine.get(key).push(rec);
  }
  return { byLine, byPiece, series };
}

export function marksForLine(index, pieceId, versionId, lineId) {
  return index.byLine.get(`${pieceId}\0${versionId}\0${lineId ?? ''}`) || [];
}

export function apparatusForPiece(index, pieceId) {
  return { piece: index.byPiece.get(pieceId) || [], series: index.series };
}

// Endnotes are numbered across the series: piece order in the catalog,
// then version, then line, then record order. Footnotes and critical
// notes take marks, not numbers. The numbering is derived, never stored,
// so inserting a record renumbers only what follows it.
export function numberEndnotes(records, pieceOrder) {
  const order = new Map(pieceOrder.map((id, i) => [id, i]));
  const endnotes = records
    .filter(r => r.kind === 'endnote')
    .sort((a, b) => {
      const pa = order.has(a.pieceId) ? order.get(a.pieceId) : Infinity;
      const pb = order.has(b.pieceId) ? order.get(b.pieceId) : Infinity;
      if (pa !== pb) return pa - pb;
      if (a.versionId !== b.versionId) return a.versionId < b.versionId ? -1 : 1;
      if ((a.lineId ?? '') !== (b.lineId ?? '')) return (a.lineId ?? '') < (b.lineId ?? '') ? -1 : 1;
      return 0; // stable sort keeps sidecar order within one line
    });
  const numbers = new Map();
  endnotes.forEach((rec, i) => numbers.set(rec.id, i + 1));
  return numbers;
}

export const KIND_LABELS = Object.freeze({
  footnote: 'Footnote',
  endnote: 'Endnote',
  'critical-note': 'Critical note',
});

export function recordLabel(record, numbers) {
  if (record.kind === 'endnote') return `Endnote ${numbers.get(record.id) ?? '?'}`;
  return KIND_LABELS[record.kind] || record.kind;
}

// The mark glyph for a line: a number for endnotes, a dagger for
// footnotes, a section sign for critical notes. Marks add no text to the
// poem itself; the note text lives in the reveal panel only.
export function markGlyph(record, numbers) {
  if (record.kind === 'endnote') return String(numbers.get(record.id) ?? '?');
  if (record.kind === 'footnote') return '†';
  return '§';
}

const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;');

// Mark buttons for one line's records, as an HTML string. The reader
// inserts this after the line text; the buttons are the only new marks.
export function markHTML(records, numbers) {
  return records.map(rec => {
    const label = `${recordLabel(rec, numbers)} — tap to reveal`;
    return `<button type="button" class="note-mark" data-note-mark="${esc(rec.id)}" aria-label="${esc(label)}">${esc(markGlyph(rec, numbers))}</button>`;
  }).join('');
}
