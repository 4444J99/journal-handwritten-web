/**
 * Optional T04 reader boundary. Supply only records from notes-model.mjs
 * projectPreview/projectRecords, never stored revisions or private dossiers.
 * This renderer cannot grant clearance; the caller owns projection policy.
 *
 * Integration: reserve an empty host, pass focusedEntry()'s stable piece and
 * version IDs, and call reveal(existingControl) only on explicit activation.
 * Call setContext on every source/version/projection change. T04's integrator
 * must include isOpen/hide in its panel, Escape, outside-click and UI-timeout
 * handling before production wiring. No hash, network or source mutation here.
 */

const FIELDS = new Set([
  'id', 'revisionId', 'family', 'kind', 'pieceId', 'versionId', 'lineId',
  'word', 'text', 'citations', 'credit', 'poemDate', 'noteDate', 'fixture',
]);
const LABELS = {
  footnote: 'Footnote', endnote: 'Endnote', reflection: 'Reflection',
  'factual-citation': 'Factual citation', 'critical-note': 'Critical note',
  'response-poem': 'Response poem', prompt: 'Prompt', reading: 'Reading',
  music: 'Music', 'hand-copy': 'Hand-copy', 'co-writing-proposal': 'Co-writing proposal',
};
const text = value => typeof value === 'string';
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const only = (value, keys) => object(value) && Object.keys(value).every(key => keys.includes(key));

// Fail closed on raw revision documents or extra/private fields. Shape checks
// are not a substitute for the model's revision, anchor and release checks.
function projection(record) {
  if (!object(record) || Object.keys(record).some(key => !FIELDS.has(key))) return null;
  if (!['note', 'contribution'].includes(record.family) || record.kind === 'research-dossier') return null;
  for (const key of ['id', 'revisionId', 'kind', 'pieceId', 'versionId', 'text', 'credit', 'noteDate']) {
    if (!text(record[key]) || !record[key].trim()) return null;
  }
  if (record.lineId !== null && !text(record.lineId)) return null;
  if (typeof record.fixture !== 'boolean') return null;
  if (!only(record.poemDate, ['certainty', 'value']) || !text(record.poemDate.certainty)) return null;
  if (record.poemDate.value !== null && !text(record.poemDate.value)) return null;
  if (record.word !== null && (!only(record.word, ['quote', 'start', 'end']) ||
    !text(record.word.quote) || !Number.isInteger(record.word.start) ||
    !Number.isInteger(record.word.end) || record.word.start < 0 || record.word.end <= record.word.start)) return null;
  if (!Array.isArray(record.citations) || record.citations.some(c =>
    !only(c, ['label', 'url', 'locator']) || !text(c.label) ||
    (c.url !== undefined && !text(c.url)) || (c.locator !== undefined && !text(c.locator)))) return null;
  // Copy accepted public fields so later caller mutations cannot change a
  // revealed record without an explicit context/projection update.
  return {
    ...record, poemDate: { ...record.poemDate },
    word: record.word && { ...record.word },
    citations: record.citations.map(c => ({ ...c })),
  };
}

export function mountNotesReader(host, initial = {}) {
  if (!host?.ownerDocument || typeof host.replaceChildren !== 'function') {
    throw new TypeError('Notes reader requires a dedicated DOM host.');
  }
  const doc = host.ownerDocument;
  let records = [], pieceId = '', versionId = '', trigger = null, opened = false, destroyed = false;

  function element(tag, content, className) {
    const node = doc.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (className) node.className = className;
    return node;
  }
  function close(restoreFocus) {
    opened = false;
    host.replaceChildren();
    host.hidden = true;
    host.setAttribute('aria-hidden', 'true');
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    const previous = trigger;
    trigger = null;
    if (restoreFocus && previous?.isConnected && typeof previous.focus === 'function') previous.focus();
  }
  function hide() { close(true); }
  function setContext(next = {}) {
    if (destroyed) return;
    close(false);
    pieceId = text(next.pieceId) ? next.pieceId : '';
    versionId = text(next.versionId) ? next.versionId : '';
    records = Array.isArray(next.records) ? next.records.map(projection).filter(Boolean) : [];
  }
  function detail(list, label, value) {
    list.append(element('dt', label), element('dd', value));
  }
  function renderRecord(record) {
    const article = element('article', undefined, 'notes-reader-record');
    article.append(element('h3', LABELS[record.kind] || record.kind.replaceAll('-', ' ')));
    if (record.fixture) article.append(element('p', 'Technical fixture · private preview only', 'notes-reader-fixture'));
    const body = element('p', record.text, 'notes-reader-text');
    body.style.whiteSpace = 'pre-wrap';
    article.append(body);
    const details = element('dl');
    detail(details, 'Credit', record.credit);
    const date = record.poemDate;
    detail(details, 'Poem date', !date.value || date.certainty === 'unknown' ? 'Unknown' :
      date.certainty === 'approximate' ? `${date.value} (approximate)` : date.value);
    detail(details, record.family === 'contribution' ? 'Contribution date' : 'Note date', record.noteDate);
    let source = `${record.pieceId} · ${record.versionId}`;
    if (record.lineId) source += ` · ${record.lineId}`;
    if (record.word) source += ` · “${record.word.quote}”`;
    detail(details, 'Source', source);
    article.append(details);
    if (record.citations.length) {
      article.append(element('h4', 'Citations'));
      const citations = element('ul');
      for (const citation of record.citations) {
        citations.append(element('li', [citation.label, citation.locator, citation.url].filter(Boolean).join(' · ')));
      }
      article.append(citations);
    }
    return article;
  }
  function reveal(control) {
    if (destroyed || opened) return;
    trigger = control || doc.activeElement;
    if (trigger === doc.body || !trigger?.setAttribute) trigger = null;
    if (trigger) trigger.setAttribute('aria-expanded', 'true');
    const panel = element('section', undefined, 'notes-reader-panel');
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', 'Notes and contributions');
    panel.tabIndex = -1;
    panel.append(element('h2', 'Notes and contributions'));
    const dismiss = element('button', 'Hide notes');
    dismiss.type = 'button';
    dismiss.addEventListener('click', hide);
    panel.append(dismiss);
    const scoped = pieceId && versionId ? records.filter(r => r.pieceId === pieceId && r.versionId === versionId) : [];
    if (scoped.length) scoped.forEach(record => panel.append(renderRecord(record)));
    else panel.append(element('p', 'No cleared notes for this source version.'));
    host.replaceChildren(panel);
    host.hidden = false;
    host.removeAttribute('aria-hidden');
    opened = true;
    panel.focus();
  }
  function onKey(event) {
    if (opened && event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      hide();
    }
  }
  // Scope Escape to this panel, leaving the surrounding reader's key handling
  // in charge when focus is elsewhere. The integrator can also call hide().
  host.addEventListener('keydown', onKey);
  setContext(initial);
  return {
    reveal, hide, setContext, switchContext: setContext,
    get isOpen() { return opened; },
    destroy() {
      if (destroyed) return;
      close(true);
      records = [];
      host.removeEventListener('keydown', onKey);
      destroyed = true;
    },
  };
}
