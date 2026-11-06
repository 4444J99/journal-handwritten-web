import * as Model from './notes-model.mjs';
import { createRevisionStore } from './notes-store.mjs';
import { mountNotesReader } from './notes-reader.mjs';

const $ = id => document.getElementById(id);
const NOTE_TYPES = ['footnote', 'endnote', 'reflection', 'factual-citation', 'critical-note', 'research-dossier'];
const CONTRIBUTION_TYPES = ['response-poem', 'prompt', 'reading', 'music', 'hand-copy', 'critical-note', 'co-writing-proposal'];
const S = { versionMap: null, review: null, catalog: null, reviews: {}, sourceReady: false, canWrite: false, store: null,
  records: { notes: [], contributions: [] }, selected: null, busy: false, dirty: false, blocked: false, reader: null };

function element(tag, text, attrs = {}) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}
function status(id, message, error = false) { $(id).textContent = message; $(id).classList.toggle('error', error); }
function label(value) { return String(value).replaceAll('-', ' '); }
function today() {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  const get = k => parts.find(p => p.type === k).value;
  return get('year') + '-' + get('month') + '-' + get('day');
}
function newId(prefix) { return prefix + '-' + crypto.randomUUID(); }
function allDocs() { return [...S.records.notes, ...S.records.contributions]; }
function group(recordId) { return Model.heads(allDocs()).find(g => g.recordId === recordId); }
function headOf(g) {
  if (!g || g.conflicted || g.errors?.length || g.heads.length !== 1) return null;
  return typeof g.heads[0] === 'string' ? allDocs().find(d => d.revisionId === g.heads[0]) : g.heads[0];
}
function currentVersion() { return S.catalog?.pieces.find(p => p.pieceId === $('piece').value)?.versions.find(v => v.versionId === $('version').value); }
function setOptions(select, options, desired) {
  select.replaceChildren(...options.map(([value, title]) => { const option = element('option', title); option.value = value; return option; }));
  if (options.some(([v]) => v === desired)) select.value = desired;
}
function updateEnabled() {
  const ready = !!S.store?.ready && S.sourceReady;
  $('editing').disabled = !S.canWrite || !ready || S.busy || S.blocked;
  const latest = S.selected && headOf(group(S.selected.recordId));
  const current = latest && latest.revisionId === S.selected.revisionId;
  $('reviewing').disabled = !S.canWrite || !ready || S.busy || S.dirty || S.blocked || !current;
  $('reviewer').disabled = !S.canWrite || !ready || S.busy;
  $('record').disabled = S.busy || S.dirty;
  $('new-note').disabled = S.busy || S.dirty;
  $('discard-draft').disabled = S.busy || !S.dirty;
  for (const id of ['piece', 'version', 'line', 'word-quote', 'word-start', 'word-end']) $(id).disabled = S.busy;
  $('export-notes').disabled = !S.store?.ready || S.busy;
  $('restore-notes').disabled = !S.canWrite || !ready || S.busy;
  $('clear-note').disabled = !current || latest?.editorial.status !== 'accepted' || latest?.visibility !== 'public-candidate';
}
async function run(action, field = 'save-status') {
  if (S.busy) return;
  S.busy = true; updateEnabled();
  try { await action(); }
  catch (e) { status(field, e.message || String(e), true); }
  finally { S.busy = false; updateEnabled(); }
}

function rebuildCatalog() {
  S.catalog = Model.buildSourceCatalog(S.versionMap, S.review, { reviews: S.reviews });
  const prior = $('piece').value;
  const titles = new Map(S.review.items.map(i => [i.id, i.first]));
  setOptions($('piece'), S.catalog.pieces.map(p => [p.pieceId, p.pieceId + (titles.get(p.pieceId) ? ' · ' + titles.get(p.pieceId) : '')]), prior);
  renderVersions($('version').value); refreshRecords();
}
function renderVersions(desired) {
  const piece = S.catalog.pieces.find(p => p.pieceId === $('piece').value);
  setOptions($('version'), (piece?.versions || []).map(v => [v.versionId, v.versionId]), desired);
  renderLines($('line').value);
}
function renderLines(desired = '') {
  const version = currentVersion();
  setOptions($('line'), [['', 'Whole source version'], ...(version?.lines || []).map(l => [l.lineId, l.lineId + ' · ' + l.text])], desired);
  $('source-lines').replaceChildren(...(version?.lines || []).map(l => {
    const li = element('li', l.text); li.classList.toggle('selected', l.lineId === $('line').value); return li;
  }));
  status('source-status', version?.issues?.length ? 'Source needs review: ' + version.issues.join('; ') : 'Existing IDs preserved. Anchors do not depend on page position.', !!version?.issues?.length);
  updateAnchorStatus(); refreshPreview();
}
function updateTypes(desired) {
  const contribution = $('family').value === 'contribution';
  setOptions($('kind'), (contribution ? CONTRIBUTION_TYPES : NOTE_TYPES).map(k => [k, label(k)]), desired);
  $('contribution-fields').hidden = !contribution;
}
function updateAnchorStatus() {
  if (!S.selected) { $('anchor-warning').textContent = ''; return; }
  const result = Model.validateAnchor(S.catalog, S.selected.anchor);
  const selectedChanged = S.selected.anchor.pieceId !== $('piece').value || S.selected.anchor.versionId !== $('version').value || (S.selected.anchor.lineId || '') !== $('line').value
    || (S.selected.anchor.word?.quote || '') !== $('word-quote').value
    || String(S.selected.anchor.word?.start ?? '') !== $('word-start').value
    || String(S.selected.anchor.word?.end ?? '') !== $('word-end').value;
  status('anchor-warning', !result.valid
    ? 'Stored anchor ' + result.status + ': ' + result.reasons.join('; ') + '. It is preserved. Review the source and explicitly choose a new anchor to reattach this note.'
    : selectedChanged ? 'The selected source differs. The stored anchor is kept unless you explicitly choose to re-anchor.' : 'The stored anchor still matches this source.', !result.valid);
}
function refreshRecords() {
  const prior = $('record').value;
  const groups = Model.heads(allDocs());
  setOptions($('record'), [['', 'New note or contribution'], ...groups.map(g => {
    const h = headOf(g);
    return [g.recordId, (g.conflicted || g.errors?.length ? '[Needs reconciliation] ' : '') + g.recordId + (h ? ' · ' + label(h.kind || h.type) : '')];
  })], prior);
  if (S.selected) {
    const latest = headOf(group(S.selected.recordId));
    status('record-status', latest?.revisionId === S.selected.revisionId
      ? `Selected ${S.selected.revisionId} · ${S.selected.editorial.status} · ${S.selected.release.status}`
      : 'This record changed or has conflicting heads. Your text is retained; reselect the record before saving or reviewing.', latest?.revisionId !== S.selected.revisionId);
  }
  renderHistory(); updateAnchorStatus(); refreshPreview(); updateEnabled();
}
function resetEditor() {
  if (S.dirty) { status('save-status', 'Save or explicitly discard your unsaved edits first.', true); return; }
  S.blocked = false;
  S.selected = null; $('record').value = '';
  $('note-form').reset(); $('note-date').value = today(); $('family').value = 'note'; updateTypes('footnote');
  $('reanchor-label').hidden = true; $('reanchor').checked = false;
  for (const id of ['word-quote', 'word-start', 'word-end']) $(id).value = '';
  $('record-status').textContent = ''; $('anchor-warning').textContent = ''; $('save-status').textContent = '';
  renderHistory(); updateEnabled();
}
function selectRecord(recordId) {
  if (S.dirty) { $('record').value = S.selected?.recordId || ''; status('save-status', 'Save or explicitly discard your unsaved edits first.', true); return; }
  if (!recordId) return resetEditor();
  const g = group(recordId), record = headOf(g);
  if (!record) {
    S.selected = null; S.blocked = true; $('note-text').value = ''; $('editing').disabled = true; $('reviewing').disabled = true;
    status('record-status', 'This record has an unresolved revision fork or incomplete history. All revisions remain in the private export. Reconcile the history explicitly before continuing.', true);
    renderHistory(g); return;
  }
  S.blocked = false; S.selected = structuredClone(record); $('record').value = recordId;
  $('family').value = record.family; updateTypes(record.kind || record.type);
  $('author-id').value = record.author.id; $('credit').value = record.author.credit;
  $('poem-date').value = record.poemDate.value || ''; $('date-certainty').value = record.poemDate.certainty;
  $('note-date').value = record.noteDate; $('note-text').value = record.text;
  $('content-provenance').value = record.author.provenance;
  $('visibility').value = record.visibility; $('change-reason').value = 'Revision';
  const citation = record.citations?.[0];
  $('citation-label').value = citation?.label || ''; $('citation-url').value = citation?.url || ''; $('citation-locator').value = citation?.locator || '';
  if (record.permission) {
    $('permission-state').value = record.permission.status;
    $('permission-web').checked = record.permission.scopes.includes('web'); $('permission-print').checked = record.permission.scopes.includes('print');
    $('permission-evidence').value = record.permission.evidence || '';
  }
  $('reanchor-label').hidden = false; $('reanchor').checked = false;
  $('piece').value = record.anchor.pieceId; renderVersions(record.anchor.versionId); renderLines(record.anchor.lineId || '');
  $('word-quote').value = record.anchor.word?.quote || '';
  $('word-start').value = record.anchor.word?.start ?? ''; $('word-end').value = record.anchor.word?.end ?? '';
  refreshRecords();
}
function renderHistory(g = S.selected && group(S.selected.recordId)) {
  const host = $('history-content'); host.replaceChildren();
  if (!g) { host.append(element('p', 'Select a saved record to inspect its history.')); return; }
  const revisions = (g.revisions || []).map(r => typeof r === 'string' ? allDocs().find(d => d.revisionId === r) : r).filter(Boolean);
  for (const r of [...revisions].sort((a, b) => a.editedAt.localeCompare(b.editedAt) || a.revisionId.localeCompare(b.revisionId))) {
    const details = element('details', null, { class: 'history-item' });
    details.append(element('summary', `${r.editedAt} · ${r.author.credit} · ${r.editorial.status} / ${r.release.status}`));
    details.append(element('p', `Poem date: ${r.poemDate.value || 'unknown'} (${r.poemDate.certainty}). Note date: ${r.noteDate}.`));
    details.append(element('code', `${r.revisionId} · source ${r.anchor.versionId}${r.anchor.lineId ? ' / ' + r.anchor.lineId : ''}`));
    details.append(element('pre', r.text));
    if (r.fixture) details.append(element('p', 'TECHNICAL FIXTURE · excluded from public output'));
    host.append(details);
  }
}
function sourceSelection() {
  const word = $('word-quote').value ? { quote: $('word-quote').value } : null;
  if (word && ($('word-start').value !== '' || $('word-end').value !== '')) {
    if ($('word-start').value === '' || $('word-end').value === '') throw new Error('Supply both start and end for a word selection.');
    word.start = Number($('word-start').value); word.end = Number($('word-end').value);
  }
  return Model.createAnchor(S.catalog, { pieceId: $('piece').value, versionId: $('version').value, lineId: $('line').value || null, word });
}
function assertSelectedCurrent() {
  if (!S.selected) return;
  const h = headOf(group(S.selected.recordId));
  if (!h || h.revisionId !== S.selected.revisionId) throw new Error('The record changed elsewhere. Your draft is still here; export or copy it before reselecting the current revision.');
}
function draftInput() {
  assertSelectedCurrent();
  const family = $('family').value;
  if (S.selected && family !== S.selected.family) throw new Error('A revision cannot change its record family. Create a new record instead.');
  const certainty = $('date-certainty').value, poemDate = $('poem-date').value.trim();
  if (certainty === 'unknown' && poemDate) throw new Error('Choose recorded or approximate for a supplied poem date.');
  if (certainty !== 'unknown' && !poemDate) throw new Error('Supply the poem date or leave its certainty unknown.');
  const citations = structuredClone(S.selected?.citations || []);
  const first = $('citation-label').value.trim();
  if (first) citations[0] = { label: first, ...($('citation-url').value.trim() ? { url: $('citation-url').value.trim() } : {}), ...($('citation-locator').value.trim() ? { locator: $('citation-locator').value.trim() } : {}) };
  else if ($('citation-url').value.trim() || $('citation-locator').value.trim()) throw new Error('Supply a citation label for the source reference.');
  else if (citations.length) citations.shift();
  const input = {
    family, recordId: S.selected?.recordId || newId(family === 'note' ? 'note' : 'contribution'),
    editedBy: $('reviewer').value.trim(),
    author: { id: $('author-id').value.trim(), credit: $('credit').value.trim(), provenance: $('content-provenance').value, sourceIds: structuredClone(S.selected?.author.sourceIds || []) },
    poemDate: { certainty, value: certainty === 'unknown' ? null : poemDate }, noteDate: $('note-date').value,
    anchor: S.selected && !$('reanchor').checked ? S.selected.anchor : sourceSelection(),
    text: $('note-text').value, citations, visibility: $('kind').value === 'research-dossier' ? 'private' : $('visibility').value,
    fixture: $('content-provenance').value === 'technical-fixture', changeReason: $('change-reason').value.trim(),
    ...(family === 'note' ? { kind: $('kind').value } : { type: $('kind').value }),
  };
  if (family === 'contribution') {
    const permission = { status: $('permission-state').value,
      scopes: [$('permission-web').checked && 'web', $('permission-print').checked && 'print'].filter(Boolean),
      evidence: $('permission-evidence').value.trim(), recordedBy: null, recordedAt: null };
    if (permission.status !== 'pending') {
      permission.recordedBy = $('reviewer').value.trim(); permission.recordedAt = new Date().toISOString();
    }
    const prior = S.selected?.permission;
    const samePermission = prior && prior.status === permission.status && prior.evidence === permission.evidence
      && [...prior.scopes].sort().join(',') === [...permission.scopes].sort().join(',');
    input.permission = samePermission ? structuredClone(prior) : permission;
  }
  return input;
}
async function saveRevision() {
  const doc = Model.createRevision(draftInput(), { previous: S.selected, at: new Date().toISOString(), revisionId: newId('rev') });
  await S.store.append(doc.family === 'note' ? 'notes' : 'contributions', doc);
  S.dirty = false;
  selectRecord(doc.recordId);
  status('save-status', 'Saved and read back. Earlier revisions are preserved.');
}
async function review(action) {
  if (S.dirty) throw new Error('Save or explicitly discard your unsaved edits before reviewing a revision.');
  if (!S.selected) throw new Error('Select a saved revision first.');
  assertSelectedCurrent();
  const doc = Model.transitionRevision(S.selected, action, { actor: $('reviewer').value.trim(), at: new Date().toISOString(), revisionId: newId('rev') });
  if (action === 'clear') {
    const candidate = Model.projectRecords([...allDocs(), doc], S.catalog, { mode: 'preview', versions: [{ pieceId: doc.anchor.pieceId, versionId: doc.anchor.versionId }], allowFixtures: true });
    if (!candidate.records.some(r => r.id === doc.recordId)) throw new Error('Clearance is blocked: ' + (candidate.excluded.find(r => r.recordId === doc.recordId)?.reasons || ['record is not eligible']).join('; '));
  }
  await S.store.append(doc.family === 'note' ? 'notes' : 'contributions', doc);
  selectRecord(doc.recordId);
  status('save-status', action === 'clear' ? 'Clearance recorded for this revision. It is available in the private preview; nothing was published.' : 'Review state saved as a new revision.');
}
function refreshPreview() {
  if (!S.catalog || !S.reader) return;
  const v = currentVersion();
  $('reader-poem').textContent = (v?.lines || []).map(l => l.text).join('\n');
  if (!S.sourceReady || !S.store?.ready) {
    S.reader.setContext({ records: [], pieceId: v?.pieceId || '', versionId: v?.versionId || '' });
    status('preview-status', 'Preview unavailable until both source and notes finish syncing.');
    return;
  }
  try {
    const projected = Model.projectRecords(allDocs(), S.catalog, { mode: 'preview', versions: v ? [{ pieceId: v.pieceId, versionId: v.versionId }] : [], allowFixtures: true });
    S.reader.setContext({ records: projected.records, pieceId: v?.pieceId || '', versionId: v?.versionId || '' });
    status('preview-status', 'Notes are hidden. Use Reveal notes to inspect cleared records for this version.');
  } catch (e) {
    S.reader.setContext({ records: [], pieceId: v?.pieceId || '', versionId: v?.versionId || '' });
    status('preview-status', e.message, true);
  }
}

async function exportNotes() {
  const envelope = S.store.exportBackup();
  const blob = new Blob([JSON.stringify(envelope, null, 2) + '\n'], { type: 'application/json' });
  if (blob.size > 32 * 1024 * 1024) throw new Error('Backup exceeds 32 MiB. Use the existing per-document exporter for larger archives.');
  const url = URL.createObjectURL(blob), a = element('a'); a.href = url; a.download = 'notes-private-' + today() + '.json';
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  status('backup-status', `Exported ${envelope.notes.length} note revisions and ${envelope.contributions.length} contribution revisions. The file contains private material.`);
}
async function restoreNotes(file) {
  if (!file) return;
  if (file.size > 32 * 1024 * 1024) throw new Error('Backup exceeds 32 MiB. Use the existing per-document importer for larger archives.');
  const envelope = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()));
  Model.restoreEnvelope(envelope, S.records); // Validate the whole graph before the first write.
  const result = await S.store.restore(envelope);
  status('backup-status', `Restored ${result.added} revisions; ${result.unchanged} identical revisions were already present. Nothing was overwritten.`);
}
async function boot() {
  $('note-date').value = today(); updateTypes('footnote');
  S.reader = mountNotesReader($('reader-notes'), { records: [], pieceId: '', versionId: '' });
  $('piece').addEventListener('change', () => renderVersions());
  $('version').addEventListener('change', () => renderLines());
  $('line').addEventListener('change', () => renderLines($('line').value));
  $('family').addEventListener('change', () => updateTypes());
  $('record').addEventListener('change', () => selectRecord($('record').value));
  $('new-note').addEventListener('click', resetEditor);
  $('discard-draft').addEventListener('click', () => { S.dirty = false; S.selected ? selectRecord(S.selected.recordId) : resetEditor(); });
  for (const event of ['input', 'change']) $('note-form').addEventListener(event, () => { S.dirty = true; updateEnabled(); status('save-status', 'Unsaved edits · save a revision before changing records or reviewing.'); });
  window.addEventListener('beforeunload', e => { if (S.dirty) { e.preventDefault(); e.returnValue = ''; } });
  for (const id of ['word-quote', 'word-start', 'word-end']) $(id).addEventListener('input', () => { S.dirty = true; updateAnchorStatus(); updateEnabled(); });
  $('note-form').addEventListener('submit', e => { e.preventDefault(); run(saveRevision); });
  $('accept-note').addEventListener('click', () => run(() => review('accept')));
  $('clear-note').addEventListener('click', () => run(() => review('clear')));
  $('hold-note').addEventListener('click', () => run(() => review('hold')));
  $('reveal-notes').addEventListener('click', () => { S.reader.reveal($('reveal-notes')); status('preview-status', 'Cleared preview shown. Escape or Hide notes closes it.'); });
  $('hide-notes').addEventListener('click', () => { S.reader.hide(); status('preview-status', 'Notes hidden.'); });
  $('preview-placement').addEventListener('change', () => { $('reader-surface').dataset.placement = $('preview-placement').value; });
  $('export-notes').addEventListener('click', () => run(exportNotes, 'backup-status'));
  $('restore-notes').addEventListener('change', () => run(() => restoreNotes($('restore-notes').files[0]), 'backup-status'));
  try {
    const responses = await Promise.all([fetch('data/notes-versions.json', { cache: 'no-store' }), fetch('data/review.json', { cache: 'no-store' })]);
    if (responses.some(r => !r.ok)) throw new Error('Could not load the source version map and review data.');
    const [versionText, reviewText] = await Promise.all(responses.map(r => r.text()));
    S.versionMap = JSON.parse(versionText); S.review = JSON.parse(reviewText);
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(reviewText)))].map(x => x.toString(16).padStart(2, '0')).join('');
    if (S.versionMap.provenance.sources.find(x => x.path === 'studio/data/review.json')?.sha256 !== digest) throw new Error('Source version map is stale. Rebuild it before authoring notes.');
    rebuildCatalog();
    const provider = window.claude;
    if (!provider?.use) throw new Error('Studio persistence is unavailable.');
    const [db, user] = await Promise.all([provider.use('db'), provider.use('user')]);
    S.canWrite = (await user.can('data.write')) === true;
    S.store = createRevisionStore({ db, canWrite: S.canWrite, validate: Model.assertRevision,
      onChange(records, ready) { S.records = records; refreshRecords(); if (ready && S.sourceReady) status('connection', S.canWrite ? 'Connected · private studio storage' : 'Connected · read-only'); },
      onError(e) { status('connection', 'Storage unavailable: ' + (e.message || e.code), true); refreshPreview(); updateEnabled(); },
    });
    S.store.start();
    db.collection('reviews').onSnapshot(snapshot => {
      S.reviews = Object.fromEntries(snapshot.docs.filter(d => d.exists).map(d => [d.id, d.data()]));
      S.sourceReady = true; rebuildCatalog(); updateEnabled();
      if (S.store.ready) status('connection', S.canWrite ? 'Connected · private studio storage' : 'Connected · read-only');
    }, e => { S.sourceReady = false; status('connection', 'Review source sync unavailable. Notes remain private; authoring is paused. ' + (e.code || ''), true); refreshPreview(); updateEnabled(); });
  } catch (e) { S.canWrite = false; status('connection', e.message || String(e), true); updateEnabled(); }
}
boot();
