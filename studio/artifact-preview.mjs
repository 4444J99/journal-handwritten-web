import * as Notes from './notes-model.mjs';
import {createArtifactRevision, artifactHeads} from './artifact-model.mjs';
import {createArtifactStore} from './artifact-store.mjs';
import {mountNotesReader} from './notes-reader.mjs';
import {mountPrivateFeaturePreview} from '../site/reader-features.js';

const $ = id => document.getElementById(id);
const S = {catalog:null, store:null, canWrite:false, ready:false, sourceReady:false, artifacts:[], notes:[], contributions:[], selected:null, preview:null, busy:false, reviews:{}};
function status(id, message) { $(id).textContent = message; }
function el(tag, text) { const node = document.createElement(tag); node.textContent = text; return node; }
function options(select, rows, prior = select.value) { select.replaceChildren(...rows.map(([value, label]) => { const option = el('option', label); option.value = value; return option; })); if (rows.some(([value]) => value === prior)) select.value = prior; }
function version() { return S.catalog?.pieces.find(p => p.pieceId === $('piece').value)?.versions.find(v => v.versionId === $('version').value); }
function source() { const v = version(); return v && {pieceId:$('piece').value, versionId:v.versionId, sourceFingerprint:v.sourceFingerprint || v.fingerprint}; }
function sources() { return S.catalog?.pieces.flatMap(p => p.versions.map(v => ({pieceId:p.pieceId, versionId:v.versionId, sourceFingerprint:v.sourceFingerprint || v.fingerprint}))) || []; }
function groups() { return artifactHeads(S.artifacts, sources()); }
function chosen() { return groups().find(g => g.recordId === $('record').value); }
function enable() { $('editing').disabled = !S.canWrite || !S.ready || !S.sourceReady || S.busy || !version() || !!chosen()?.conflicted; $('export-artifacts').disabled = !S.ready; }
function clearPreview() { S.preview?.destroy(); S.preview = null; status('preview-status', 'Preview closed after a source or revision change.'); }
function renderHistory() {
  const group = chosen(); $('artifact-history').replaceChildren();
  if (!group) return;
  if (group.conflicted || group.stale) $('artifact-history').append(el('p', group.conflicted ? 'Conflicting history: reconcile before editing or previewing.' : 'Source changed: this artifact is stale. Review and explicitly rebind before previewing.'));
  for (const item of group.revisions) { const details = el('details', ''), pre = el('pre', JSON.stringify(item, null, 2)); details.append(el('summary', `${item.at} · ${item.revisionId}`), pre); $('artifact-history').append(details); }
}
function updateRecords() {
  options($('record'), [['', 'New record'], ...groups().map(g => [g.recordId, `${g.recordId}${g.conflicted ? ' · conflict' : g.stale ? ' · stale' : ''}`])]); renderHistory(); enable();
}
function updateVersions() {
  const piece = S.catalog?.pieces.find(p => p.pieceId === $('piece').value);
  options($('version'), (piece?.versions || []).map(v => [v.versionId, v.versionId]));
  status('source-status', source()?.sourceFingerprint || 'Source unavailable'); clearPreview(); updateRecords();
}
function rebuild() {
  S.catalog = Notes.buildSourceCatalog(S.map, S.review, {reviews:S.reviews});
  options($('piece'), S.catalog.pieces.map(p => [p.pieceId, p.pieceId])); updateVersions();
}
$('piece').addEventListener('change', updateVersions);
$('version').addEventListener('change', () => { status('source-status', source()?.sourceFingerprint || 'Source unavailable'); clearPreview(); updateRecords(); });
$('record').addEventListener('change', () => {
  clearPreview(); const group = chosen(); S.selected = group && !group.conflicted ? group.heads[0] : null;
  if (S.selected) { const item = S.selected; $('kind').value = item.kind; $('payload').value = JSON.stringify(item.payload, null, 2); $('by').value = item.by; $('fixture').checked = item.fixture; $('reason').value = 'revision'; }
  else { $('payload').value = '{}'; $('reason').value = 'initial'; }
  $('kind').disabled = !!S.selected; $('rebind').checked = false; renderHistory(); enable();
});
$('artifact-form').addEventListener('submit', async event => {
  event.preventDefault(); if (S.busy || !S.canWrite || !S.ready || !S.sourceReady) return;
  S.busy = true; enable();
  try {
    const group = chosen(); if (group?.conflicted) throw new Error('Resolve the artifact fork before editing.');
    const previous = group?.heads[0] || null;
    if (previous && S.selected?.revisionId !== previous.revisionId) throw new Error('The record changed. Reselect it before saving.');
    const payload = JSON.parse($('payload').value);
    if ($('kind').value === 'pronunciation' && payload.entries?.some(entry => !version().lines.some(line => line.lineId === entry.lineId && line.text.includes(entry.token)))) throw new Error('Pronunciation entries must refer to a token in the selected source line.');
    const revision = createArtifactRevision({kind:$('kind').value, recordId:previous?.recordId || 'artifact-' + crypto.randomUUID(), source:source(), payload, fixture:$('fixture').checked, reason:$('rebind').checked ? 'source-rebind' : $('reason').value}, {previous, revisionId:'artifact-rev-' + crypto.randomUUID(), by:$('by').value.trim()});
    await S.store.append('artifacts', revision);
    S.selected = revision; updateRecords(); $('record').value = revision.recordId; $('kind').disabled = true; renderHistory(); clearPreview();
    status('save-status', 'Saved and read back ' + revision.revisionId);
  } catch (error) { status('save-status', error.message); }
  finally { S.busy = false; enable(); }
});
$('export-artifacts').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(S.store.exportBackup(), null, 2)], {type:'application/json'}));
  const a = el('a', ''); a.href = url; a.download = 'versforms-private-artifacts.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 0);
});
$('enable-preview').addEventListener('change', () => { if (!$('enable-preview').checked) clearPreview(); });
$('mount-preview').addEventListener('click', () => {
  clearPreview();
  try {
    if (!$('enable-preview').checked) throw new Error('Enable the private preview first.');
    const group = chosen(); if (group && (group.conflicted || group.stale)) throw new Error('Resolve the stored artifact source and history before previewing.');
    const exactSource = source(); if (!S.sourceReady || !exactSource || version().issues?.length) throw new Error('The selected source needs review.');
    const config = JSON.parse($('preview-config').value);
    if (group) for (const descriptor of [config.audio, config.regions, config.realization]) {
      if (descriptor && descriptor.revisionId !== group.heads[0].revisionId) throw new Error('Preview asset references must identify the selected stored artifact revision.');
    }
    const notes = Notes.projectPreview([...S.notes, ...S.contributions], S.catalog, {versions:[exactSource], allowFixtures:true}).records;
    S.preview = mountPrivateFeaturePreview($('feature-preview'), {enabled:true, source:exactSource, notes, renderNotes:mountNotesReader, audio:config.audio, regions:config.regions, realization:config.realization});
    status('preview-status', 'Controls prepared. Choose a feature to reveal it; audio and realizations do not start automatically.');
  } catch (error) { status('preview-status', error.message); }
});
addEventListener('pagehide', () => { S.preview?.destroy(); S.store?.stop(); });
try {
  const responses = await Promise.all([fetch('data/notes-versions.json', {cache:'no-store'}), fetch('data/review.json', {cache:'no-store'})]);
  if (responses.some(r => !r.ok)) throw new Error('Source catalog unavailable.');
  const [mapText, reviewText] = await Promise.all(responses.map(r => r.text()));
  S.map = JSON.parse(mapText); S.review = JSON.parse(reviewText);
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(reviewText)))].map(x => x.toString(16).padStart(2,'0')).join('');
  if (S.map.provenance.sources.find(x => x.path === 'studio/data/review.json')?.sha256 !== digest) throw new Error('Source version map is stale. Rebuild it before saving artifacts.');
  rebuild();
  const [db, user] = await Promise.all([window.claude.use('db'), window.claude.use('user')]);
  S.canWrite = await user.can('data.write') === true;
  S.store = createArtifactStore({db, canWrite:S.canWrite, onChange(records, ready) { S.artifacts = records.artifacts; S.ready = ready; updateRecords(); if (ready) status('connection', S.canWrite ? 'Connected · private artifact storage' : 'Connected · read-only'); }, onError(error) { S.ready = false; enable(); status('connection', 'Artifact storage unavailable: ' + error.message); }});
  S.store.start();
  db.collection('reviews').onSnapshot(snapshot => {
    const next = Object.fromEntries(snapshot.docs.filter(d => d.exists).map(d => [d.id, d.data()]));
    if (S.sourceReady && Notes.stableJSON(next) === Notes.stableJSON(S.reviews)) return;
    S.reviews = next; S.sourceReady = true; rebuild();
  }, error => { S.sourceReady = false; clearPreview(); enable(); status('connection', 'Source review sync unavailable: ' + error.message); });
  for (const family of ['notes', 'contributions']) db.collection(family).onSnapshot(snapshot => { const next = snapshot.docs.filter(d => d.exists).map(d => d.data()); if (Notes.stableJSON(next) !== Notes.stableJSON(S[family])) { S[family] = next; clearPreview(); } });
} catch (error) { S.canWrite = false; status('connection', error.message); enable(); }
