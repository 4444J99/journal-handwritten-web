// T05 proposed notes contract. Existing piece/version/line IDs are preserved;
// fingerprints and word selectors await T02 acceptance. No publication authority
// is conferred by these local filters (see the proposed T03 clearance contract).
export const NOTE_KINDS = Object.freeze(['footnote', 'endnote', 'reflection', 'research-dossier', 'critical-note', 'factual-citation']);
export const CONTRIBUTION_TYPES = Object.freeze(['response-poem', 'prompt', 'reading', 'music', 'hand-copy', 'critical-note', 'co-writing-proposal']);
export const PARTICIPATION_DEFAULT = Object.freeze({
  placement: 'around', countsTowardsAuthor100: false, format: 'pending-author',
  provenance: Object.freeze({
    kind: 'claude-derived', authorAdopted: false,
    source: 'exports/derived-decisions-2026-11-05/decisions/participation.json',
    at: '2026-11-05T20:03:35.000Z'
  })
});

const ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const validID = value => typeof value === 'string' && ID.test(value);
const HASH = /^sha256:[a-f0-9]{64}$/;
const clone = value => JSON.parse(JSON.stringify(value));
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
const object = value => !!value && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function uuid(prefix) {
  if (!globalThis.crypto?.randomUUID) throw new Error('Supply an explicit ID when crypto.randomUUID is unavailable.');
  return prefix + '-' + globalThis.crypto.randomUUID();
}
export function stableJSON(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJSON).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stableJSON(value[k])).join(',') + '}';
  return JSON.stringify(value);
}

// Synchronous SHA-256 keeps source construction identical in browsers and Node.
// It is a change detector, not a signature or evidence of author clearance.
export function sha256(text) {
  const bytes = new TextEncoder().encode(text), length = bytes.length;
  const padded = new Uint8Array(Math.ceil((length + 9) / 64) * 64);
  padded.set(bytes); padded[length] = 128;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 8, Math.floor(length / 0x20000000));
  view.setUint32(padded.length - 4, (length * 8) >>> 0);
  const k = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const h = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]), w = new Uint32Array(64);
  const r = (n, bits) => (n >>> bits) | (n << (32 - bits));
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + 4 * i);
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15], b = w[i - 2];
      w[i] = (w[i - 16] + (r(a,7) ^ r(a,18) ^ (a >>> 3)) + w[i - 7] + (r(b,17) ^ r(b,19) ^ (b >>> 10))) >>> 0;
    }
    let [a,b,c,d,e,f,g,z] = h;
    for (let i = 0; i < 64; i++) {
      const t1 = (z + (r(e,6) ^ r(e,11) ^ r(e,25)) + ((e & f) ^ (~e & g)) + k[i] + w[i]) >>> 0;
      const t2 = ((r(a,2) ^ r(a,13) ^ r(a,22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      z=g; g=f; f=e; e=(d+t1)>>>0; d=c; c=b; b=a; a=(t1+t2)>>>0;
    }
    [a,b,c,d,e,f,g,z].forEach((n,i) => { h[i] = (h[i] + n) >>> 0; });
  }
  return 'sha256:' + [...h].map(n => n.toString(16).padStart(8,'0')).join('');
}
const digest = value => sha256(stableJSON(value));

function dateValue(value) {
  if (typeof value !== 'string' || !/^\d{4}(?:-\d{2}(?:-\d{2})?)?$/.test(value)) return false;
  const full = value.length === 4 ? value + '-01-01' : value.length === 7 ? value + '-01' : value;
  const d = new Date(full + 'T00:00:00.000Z');
  return !Number.isNaN(d.valueOf()) && d.toISOString().slice(0, 10) === full;
}
function instant(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0,19) === value.slice(0,19);
}

/** Build only from existing exact V[].P membership; review stack order is unused. */
export function buildSourceCatalog(site, review, { reviews = {} } = {}) {
  if (!Array.isArray(site?.pieces) || !Array.isArray(review?.pages)) throw new Error('Existing pieces and review pages are required.');
  const pages = new Map(), lineCounts = new Map();
  for (const page of review.pages) {
    if (pages.has(page.id)) throw new Error('Duplicate source page ID: ' + page.id);
    pages.set(page.id, page);
    for (const block of page.blocks || []) for (const line of block.lines || []) lineCounts.set(line.id, (lineCounts.get(line.id) || 0) + 1);
  }
  const pieceIds = new Set(), versionIds = new Set();
  const pieces = site.pieces.map(piece => {
    if (!validID(piece.id) || pieceIds.has(piece.id) || !Array.isArray(piece.V)) throw new Error('Invalid or duplicate piece ID.');
    pieceIds.add(piece.id);
    const versions = piece.V.map(version => {
      if (!validID(version.id) || versionIds.has(version.id) || !Array.isArray(version.P)) throw new Error('Invalid or duplicate version ID.');
      versionIds.add(version.id);
      const members = clone(version.P), lines = [], issues = [], seen = new Set();
      for (const member of members) {
        if (!Array.isArray(member) || member.length !== 2 || !validID(member[0]) || !Array.isArray(member[1]) || !member[1].every(i => Number.isInteger(i) && i >= 0)) { issues.push('invalid-membership'); continue; }
        const [pageId, blockIndexes] = member, page = pages.get(pageId);
        if (!page) { issues.push('missing-page:' + pageId); continue; }
        for (const blockIndex of blockIndexes) {
          const key = pageId + '/' + blockIndex, block = page.blocks?.[blockIndex];
          if (!block || seen.has(key)) { issues.push('missing-or-duplicate-block:' + key); continue; }
          seen.add(key);
          for (const line of block.lines || []) {
            if (!validID(line.id) || lineCounts.get(line.id) !== 1 || typeof line.tx !== 'string') { issues.push('invalid-or-duplicate-line:' + line.id); continue; }
            let text = line.tx;
            const correction = own(reviews, line.id) ? reviews[line.id] : null;
            if (block.t !== 'quotation' && correction?.status === 'corrected') {
              if (typeof correction.text !== 'string' || typeof correction.original !== 'string') issues.push('invalid-review:' + line.id);
              else if (correction.original !== line.tx && correction.text !== line.tx) issues.push('stale-review:' + line.id);
              else text = correction.text;
            }
            lines.push({ lineId: line.id, text, originalText: line.tx, pageId, blockIndex, blockType: block.t || 'text' });
          }
        }
      }
      if (!lines.length) issues.push('empty-version');
      const fingerprint = digest({ pieceId: piece.id, versionId: version.id, members, lines: lines.map(({lineId,text,blockType}) => ({lineId,text,blockType})) });
      const sourceDate = version.d ?? null;
      return { pieceId: piece.id, versionId: version.id, members, lines, fingerprint, issues,
        poemDate: dateValue(sourceDate) ? {certainty:'recorded',value:sourceDate} : {certainty:'unknown',value:null}, sourceDate };
    });
    return { pieceId: piece.id, versions };
  });
  return freeze({ format: 'versforms-notes-sources', version: 1, pieces,
    fingerprint: digest(pieces.map(p => ({pieceId:p.pieceId,versions:p.versions.map(v => ({versionId:v.versionId,fingerprint:v.fingerprint,issues:v.issues}))}))),
    provenance: clone(site.provenance || {kind:'existing-source-catalog'}) });
}

function findVersion(catalog, pieceId, versionId) {
  const pieces = catalog?.pieces?.filter(p => p.pieceId === pieceId) || [];
  const versions = pieces.length === 1 ? pieces[0].versions.filter(v => v.versionId === versionId) : [];
  return versions.length === 1 ? versions[0] : null;
}
function wordSelector(text, word) {
  if (!object(word) || !nonempty(word.quote)) throw new Error('A word anchor requires an exact nonempty quote.');
  const points = Array.from(text), quote = Array.from(word.quote);
  let {start, end} = word;
  if (start == null && end == null) {
    const matches = [];
    for (let i = 0; i <= points.length - quote.length; i++) if (points.slice(i,i+quote.length).join('') === word.quote) matches.push(i);
    if (matches.length !== 1) throw new Error(matches.length ? 'Ambiguous word anchor: supply explicit codepoint start/end.' : 'The exact quote is absent from this source line.');
    start = matches[0]; end = start + quote.length;
  }
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || end > points.length || points.slice(start,end).join('') !== word.quote) throw new Error('Invalid codepoint selector for the captured source line.');
  return {quote:word.quote,start,end};
}
export function createAnchor(catalog, {pieceId,versionId,lineId=null,word=null}) {
  const version = findVersion(catalog, pieceId, versionId);
  if (!version) throw new Error('Unknown exact piece/version association.');
  if (version.issues.length) throw new Error('Source version is unresolved: ' + version.issues.join(', '));
  const line = lineId === null ? null : version.lines.find(l => l.lineId === lineId);
  if (lineId !== null && !line) throw new Error('Line is not a member of this source version.');
  if (word && !line) throw new Error('A word selector requires an exact source line.');
  return freeze({ schemaVersion:1, pieceId, versionId, versionFingerprint:version.fingerprint,
    members:clone(version.members), lineId, lineText:line?.text ?? null,
    word:word ? wordSelector(line.text,word) : null, sourceProvenance:clone(catalog.provenance) });
}
export function validateAnchor(catalog, anchor) {
  const reasons = anchorErrors(anchor);
  if (!reasons.length) {
    const version = findVersion(catalog, anchor.pieceId, anchor.versionId);
    if (!version) reasons.push('missing-source-version');
    else {
      reasons.push(...version.issues);
      if (stableJSON(anchor.members) !== stableJSON(version.members)) reasons.push('source-membership-changed');
      if (anchor.versionFingerprint !== version.fingerprint) reasons.push('source-version-changed');
      if (anchor.lineId !== null) {
        const line = version.lines.find(l => l.lineId === anchor.lineId);
        if (!line) reasons.push('line-no-longer-in-version');
        else if (line.text !== anchor.lineText) reasons.push('source-line-changed');
      }
    }
  }
  return {valid:!reasons.length,status:reasons.length ? 'invalidated' : 'valid',reasons};
}

function keys(value, allowed, path, errors) {
  if (!object(value)) { errors.push(path + ' must be a plain object'); return false; }
  for (const key of Object.keys(value)) if (!allowed.includes(key)) errors.push(path + ': unknown field ' + key);
  return true;
}
function plainJSON(value, errors, path='$', seen=new Set()) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string' || (typeof value === 'number' && Number.isFinite(value))) return;
  if ((!Array.isArray(value) && !object(value)) || seen.has(value)) { errors.push(path + ': not plain JSON'); return; }
  seen.add(value);
  for (const [key, child] of Object.entries(value)) {
    if (['__proto__','prototype','constructor'].includes(key)) errors.push(path + ': unsafe key ' + key);
    plainJSON(child,errors,path+'.'+key,seen);
  }
  seen.delete(value);
}
function anchorErrors(anchor) {
  const errors = [];
  if (!keys(anchor,['schemaVersion','pieceId','versionId','versionFingerprint','members','lineId','lineText','word','sourceProvenance'],'anchor',errors)) return errors;
  if (anchor.schemaVersion !== 1 || !validID(anchor.pieceId) || !validID(anchor.versionId) || !HASH.test(anchor.versionFingerprint)) errors.push('invalid anchor identity/fingerprint');
  if (!Array.isArray(anchor.members) || !anchor.members.length || !anchor.members.every(m => Array.isArray(m) && m.length === 2 && typeof m[0] === 'string' && ID.test(m[0]) && Array.isArray(m[1]) && m[1].length && m[1].every(i => Number.isInteger(i) && i >= 0))) errors.push('invalid anchor membership');
  if (anchor.lineId === null) {
    if (anchor.lineText !== null || anchor.word !== null) errors.push('whole-version anchor must not carry a line/word');
  } else if (typeof anchor.lineId !== 'string' || !ID.test(anchor.lineId) || typeof anchor.lineText !== 'string') errors.push('invalid captured line');
  if (anchor.word !== null) {
    if (keys(anchor.word,['quote','start','end'],'anchor.word',errors)) {
      try { wordSelector(anchor.lineText,anchor.word); } catch (error) { errors.push(error.message); }
      if (!Number.isInteger(anchor.word.start) || !Number.isInteger(anchor.word.end)) errors.push('stored word selector needs explicit codepoint offsets');
    }
  }
  if (!object(anchor.sourceProvenance)) errors.push('source provenance must be an object');
  return errors;
}

export function contentDigest(revision) {
  const {revisionId, parents, editedAt, editedBy, changeReason, editorial, release, ...content} = revision;
  return digest(content);
}
function approvalErrors(approval, revision, path, errors) {
  if (approval === null) return;
  if (!keys(approval,['revisionId','by','at','contentDigest','evidence'],path,errors)) return;
  if (typeof approval.revisionId !== 'string' || !ID.test(approval.revisionId) || !nonempty(approval.by) || !instant(approval.at) || !HASH.test(approval.contentDigest)) errors.push(path + ' is invalid');
  if (own(approval,'evidence') && !nonempty(approval.evidence)) errors.push(path + ' evidence must be nonempty');
  if (approval.contentDigest !== contentDigest(revision)) errors.push(path + ' does not cover this content');
}

/** Structural/content validation is separate from graph and live source checks. */
export function validateRevision(doc) {
  const errors = [];
  plainJSON(doc,errors);
  if (errors.length) return {valid:false,errors};
  const common = ['schemaVersion','family','recordId','revisionId','parents','author','poemDate','noteDate','editedAt','editedBy','anchor','text','citations','visibility','editorial','release','fixture','changeReason'];
  if (!keys(doc,[...common,'kind','type','permission','participation'],'revision',errors)) return {valid:false,errors};
  for (const field of common) if (!own(doc,field)) errors.push('missing ' + field);
  if (doc.schemaVersion !== 1 || !['note','contribution'].includes(doc.family)) errors.push('unsupported revision schema/family');
  for (const field of ['recordId','revisionId']) if (typeof doc[field] !== 'string' || !ID.test(doc[field])) errors.push('invalid ' + field);
  if (!Array.isArray(doc.parents) || !doc.parents.every(id => typeof id === 'string' && ID.test(id) && id !== doc.revisionId) || new Set(doc.parents).size !== doc.parents.length) errors.push('invalid parents');
  if (keys(doc.author,['id','credit','provenance','sourceIds'],'author',errors)) {
    if (!nonempty(doc.author.id) || typeof doc.author.credit !== 'string' || !['author-supplied','contributor-supplied','technical-fixture'].includes(doc.author.provenance)) errors.push('invalid author identity/provenance');
    if (!Array.isArray(doc.author.sourceIds) || !doc.author.sourceIds.every(nonempty)) errors.push('invalid author source IDs');
    if ((doc.author.provenance === 'technical-fixture') !== doc.fixture) errors.push('fixture flag must match technical-fixture provenance');
  }
  if (keys(doc.poemDate,['certainty','value'],'poemDate',errors)) {
    if (!['unknown','recorded','approximate'].includes(doc.poemDate.certainty) || (doc.poemDate.certainty === 'unknown' ? doc.poemDate.value !== null : !dateValue(doc.poemDate.value))) errors.push('invalid poem date/certainty');
  }
  if (typeof doc.noteDate !== 'string' || doc.noteDate.length !== 10 || !dateValue(doc.noteDate) || !instant(doc.editedAt)) errors.push('invalid note/edit date');
  if (!nonempty(doc.editedBy) || typeof doc.changeReason !== 'string') errors.push('invalid revision authorship/reason');
  errors.push(...anchorErrors(doc.anchor));
  if (!nonempty(doc.text)) errors.push('note/contribution text is required');
  if (!Array.isArray(doc.citations)) errors.push('citations must be an array');
  else for (const citation of doc.citations) if (keys(citation,['label','url','locator'],'citation',errors)) {
    if (!nonempty(citation.label) || (own(citation,'locator') && typeof citation.locator !== 'string')) errors.push('invalid citation label/locator');
    if (own(citation,'url')) {
      try { const url = new URL(citation.url); if (!['https:','http:'].includes(url.protocol) || url.username || url.password) throw new Error(); }
      catch { errors.push('citation URL must use http(s) without credentials'); }
    }
  }
  if (!['private','public-candidate'].includes(doc.visibility) || typeof doc.fixture !== 'boolean') errors.push('invalid visibility/fixture');
  if (doc.family === 'note') {
    if (!NOTE_KINDS.includes(doc.kind) || ['type','permission','participation'].some(k => own(doc,k))) errors.push('invalid note kind or contribution fields on note');
  } else if (doc.family === 'contribution') {
    if (!CONTRIBUTION_TYPES.includes(doc.type) || own(doc,'kind')) errors.push('invalid contribution type');
    if (stableJSON(doc.participation) !== stableJSON(PARTICIPATION_DEFAULT)) errors.push('contributions must retain the around-the-author default and provenance');
    if (keys(doc.permission,['status','scopes','evidence','recordedBy','recordedAt'],'permission',errors)) {
      const permission = doc.permission;
      if (!['pending','granted','revoked'].includes(permission.status) || !Array.isArray(permission.scopes) || !permission.scopes.every(s => ['web','print'].includes(s)) || new Set(permission.scopes).size !== permission.scopes.length || typeof permission.evidence !== 'string') errors.push('invalid contribution permission');
      if (permission.status !== 'pending' && (!nonempty(permission.recordedBy) || !instant(permission.recordedAt) || !nonempty(permission.evidence))) errors.push('granted/revoked permission requires recorded actor, date and evidence');
      if (permission.recordedBy !== null && !nonempty(permission.recordedBy)) errors.push('invalid permission actor');
      if (permission.recordedAt !== null && !instant(permission.recordedAt)) errors.push('invalid permission date');
    }
  }
  if (keys(doc.editorial,['status','approval'],'editorial',errors)) {
    if (!['draft','in-review','accepted','rejected'].includes(doc.editorial.status)) errors.push('invalid editorial state');
    if (['accepted','rejected'].includes(doc.editorial.status) ? doc.editorial.approval === null : doc.editorial.approval !== null) errors.push('editorial state/approval mismatch');
    approvalErrors(doc.editorial.approval,doc,'editorial.approval',errors);
  }
  if (keys(doc.release,['status','clearance','publication','revocation'],'release',errors)) {
    if (!['held','cleared','released','revoked'].includes(doc.release.status)) errors.push('invalid release state');
    for (const field of ['clearance','publication','revocation']) approvalErrors(doc.release[field],doc,'release.'+field,errors);
    if (doc.release.status === 'held' && [doc.release.clearance,doc.release.publication,doc.release.revocation].some(v => v !== null)) errors.push('held content must have no clearance/publication/revocation');
    if (['cleared','released'].includes(doc.release.status) && !doc.release.clearance) errors.push('clearance is required');
    if (doc.release.status === 'cleared' && (doc.release.publication !== null || doc.release.revocation !== null)) errors.push('cleared is not released/revoked');
    if (doc.release.status === 'released' && (!doc.release.publication?.evidence || doc.release.revocation !== null)) errors.push('release requires a recorded publication reference');
    if (doc.release.status === 'revoked' && !doc.release.revocation) errors.push('revocation requires an attributable event');
  }
  if (new TextEncoder().encode(JSON.stringify(doc)).length > 64 * 1024) errors.push('revision exceeds 64 KiB document limit');
  return {valid:!errors.length,errors};
}
export function assertRevision(collection, doc) {
  if (!['notes','contributions'].includes(collection) || doc?.family !== (collection === 'notes' ? 'note' : 'contribution')) throw new Error('Revision family/collection mismatch.');
  const result = validateRevision(doc);
  if (!result.valid) throw new Error('Invalid revision: ' + result.errors.join('; '));
  return doc;
}

/** Every content edit starts a new held draft; no former approval is inherited. */
export function createRevision(input, {previous=null,at=input.editedAt || new Date().toISOString(),revisionId=input.revisionId} = {}) {
  if (previous) assertRevision(previous.family === 'note' ? 'notes' : 'contributions',previous);
  const value = {...(previous || {}),...input}, family = value.family || 'note';
  if (previous && (family !== previous.family || (input.recordId && input.recordId !== previous.recordId))) throw new Error('A revision cannot change record identity or family.');
  const author = value.author || {}, doc = {
    schemaVersion:1, family, recordId:value.recordId || uuid(family), revisionId:revisionId || uuid('rev'),
    parents:clone(input.parents || (previous ? [previous.revisionId] : [])),
    author:{id:author.id,credit:author.credit ?? '',provenance:author.provenance || 'author-supplied',sourceIds:clone(author.sourceIds || [])},
    poemDate:clone(value.poemDate || {certainty:'unknown',value:null}), noteDate:value.noteDate || at.slice(0,10),
    editedAt:at,editedBy:input.editedBy || author.id,anchor:clone(value.anchor),text:value.text,
    citations:clone(value.citations || []),visibility:input.visibility || 'private',
    editorial:{status:'draft',approval:null},release:{status:'held',clearance:null,publication:null,revocation:null},
    fixture:value.fixture === true,changeReason:input.changeReason || ''
  };
  if (previous?.fixture && (!doc.fixture || doc.author.provenance !== 'technical-fixture')) throw new Error('Technical-fixture provenance cannot be removed from its revision history.');
  if (previous && !doc.parents.includes(previous.revisionId)) throw new Error('An edit must retain its previous revision as a parent.');
  if (family === 'note') doc.kind = value.kind || 'footnote';
  else {
    doc.type = value.type || value.kind || 'response-poem';
    doc.permission = clone(value.permission || {status:'pending',scopes:[],evidence:'',recordedBy:null,recordedAt:null});
    doc.participation = clone(PARTICIPATION_DEFAULT);
  }
  assertRevision(family === 'note' ? 'notes' : 'contributions',doc);
  return freeze(doc);
}
function makeApproval(doc, by, at) { return {revisionId:doc.revisionId,by,at,contentDigest:contentDigest(doc)}; }
export function transitionRevision(previous, action, {actor,at=new Date().toISOString(),revisionId=uuid('rev')} = {}) {
  assertRevision(previous.family === 'note' ? 'notes' : 'contributions',previous);
  const by = typeof actor === 'string' ? actor : actor?.id;
  if (!nonempty(by)) throw new Error('An attributable reviewer is required.');
  const doc = clone(previous);
  doc.revisionId=revisionId; doc.parents=[previous.revisionId]; doc.editedAt=at; doc.editedBy=by; doc.changeReason=action;
  const held = () => { doc.release={status:'held',clearance:null,publication:null,revocation:null}; };
  if (action === 'submit') { doc.editorial={status:'in-review',approval:null}; held(); }
  else if (action === 'accept' || action === 'reject') { doc.editorial={status:action === 'accept' ? 'accepted' : 'rejected',approval:makeApproval(doc,by,at)}; held(); }
  else if (action === 'clear') {
    if (doc.editorial.status !== 'accepted' || doc.visibility !== 'public-candidate' || !nonempty(doc.author.credit) || doc.kind === 'research-dossier') throw new Error('Preview clearance needs accepted public-candidate content with explicit credit; dossiers stay private.');
    if (doc.family === 'contribution' && (doc.permission.status !== 'granted' || !doc.permission.scopes.includes('web'))) throw new Error('Contribution preview requires recorded web permission.');
    doc.release={status:'cleared',clearance:makeApproval(doc,by,at),publication:null,revocation:null};
  } else if (action === 'hold') held();
  else if (action === 'revoke') doc.release={...doc.release,status:'revoked',revocation:makeApproval(doc,by,at)};
  else throw new Error('Unsupported transition. Publication is a separate T03 integration gate.');
  assertRevision(doc.family === 'note' ? 'notes' : 'contributions',doc);
  return freeze(doc);
}

function documents(value) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value.notes) && Array.isArray(value.contributions)) return [...value.notes,...value.contributions];
  throw new Error('Expected revision documents or a notes/contributions snapshot.');
}
/** No last-write-wins: each record reports every head and unresolved graph errors. */
export function heads(value) {
  const groups = new Map(), revisions = new Map();
  for (const doc of documents(value)) {
    const key = doc?.recordId || '(invalid-record)';
    if (!groups.has(key)) groups.set(key,{recordId:key,revisions:[],heads:[],conflicted:false,errors:[]});
    const group=groups.get(key), validation=validateRevision(doc);
    if (!validation.valid) { group.errors.push(...validation.errors); continue; }
    if (revisions.has(doc.revisionId)) {
      const existing=revisions.get(doc.revisionId);
      if (stableJSON(existing) !== stableJSON(doc)) {
        group.errors.push('revision collision: ' + doc.revisionId);
        if (existing.recordId !== key) groups.get(existing.recordId).errors.push('revision collision: ' + doc.revisionId);
      }
      continue;
    }
    revisions.set(doc.revisionId,doc); group.revisions.push(doc);
  }
  for (const group of groups.values()) {
    const children=new Set(), visited=new Set(), visiting=new Set();
    function visit(doc) {
      if (visiting.has(doc.revisionId)) { group.errors.push('revision cycle'); return; }
      if (visited.has(doc.revisionId)) return;
      visiting.add(doc.revisionId);
      for (const id of doc.parents) {
        const parent=revisions.get(id);
        if (!parent || parent.recordId !== doc.recordId || parent.family !== doc.family) group.errors.push('missing or foreign parent: ' + id);
        else {
          if (parent.fixture && !doc.fixture) group.errors.push('technical-fixture provenance was removed');
          children.add(id); visit(parent);
        }
      }
      visiting.delete(doc.revisionId); visited.add(doc.revisionId);
    }
    group.revisions.forEach(visit);
    if (new Set(group.revisions.map(d => d.family)).size > 1) group.errors.push('mixed record families');
    group.heads=group.revisions.filter(d => !children.has(d.revisionId));
    group.errors=[...new Set(group.errors)];
    group.conflicted=group.heads.length !== 1 || !!group.errors.length;
  }
  return [...groups.values()];
}
export const summarizeRecords = heads;

import {evaluateRelease, contractDigest} from './release-contract.mjs';

function verifiedApproval(doc, approval, group, field) {
  if (!approval || approval.contentDigest !== contentDigest(doc)) return false;
  const byId=new Map(group.revisions.map(r => [r.revisionId,r])), ancestors=new Set();
  function walk(id) { if (ancestors.has(id)) return; ancestors.add(id); byId.get(id)?.parents.forEach(walk); }
  walk(doc.revisionId);
  const reference=byId.get(approval.revisionId);
  return !!reference && ancestors.has(approval.revisionId) && contentDigest(reference) === approval.contentDigest && stableJSON(field(reference)) === stableJSON(approval);
}
/** A local eligibility filter only. It never grants publication authority. */
export function projectRecords(value, catalog, {mode='preview',versions,allowFixtures=false,releaseContext} = {}) {
  if (!['preview','public'].includes(mode)) throw new Error('Unknown projection mode.');
  if (versions !== undefined && (!Array.isArray(versions) || !versions.every(v => object(v) && typeof v.pieceId === 'string' && typeof v.versionId === 'string'))) throw new Error('Use an exact piece/version allowlist.');
  const allowed=versions ? new Set(versions.map(v => v.pieceId + '/' + v.versionId)) : null;
  const records=[],excluded=[];
  for (const group of heads(value)) {
    const reasons=[...group.errors], doc=group.heads[0];
    if (group.heads.length !== 1) reasons.push('unresolved revision fork or missing head');
    if (!reasons.length && doc) {
      if (doc.visibility !== 'public-candidate') reasons.push('private visibility');
      if (doc.kind === 'research-dossier') reasons.push('private research dossier');
      if (!nonempty(doc.author.credit)) reasons.push('explicit public credit is missing');
      if (doc.fixture && (mode === 'public' || !allowFixtures)) reasons.push('technical fixture excluded');
      if (doc.editorial.status !== 'accepted' || !verifiedApproval(doc,doc.editorial.approval,group,r => r.editorial.approval)) reasons.push('editorial acceptance is missing or unbound');
      if (!(mode === 'public' ? doc.release.status === 'released' : ['cleared','released'].includes(doc.release.status)) || !verifiedApproval(doc,doc.release.clearance,group,r => r.release.clearance)) reasons.push('release clearance is missing or unbound');
      if (mode === 'public' && !verifiedApproval(doc,doc.release.publication,group,r => r.release.publication)) reasons.push('explicit release is missing or unbound');
      if ((mode === 'public' && !allowed) || (allowed && !allowed.has(doc.anchor.pieceId + '/' + doc.anchor.versionId))) reasons.push('exact source version is not allowed');
      if (doc.family === 'contribution' && (doc.permission.status !== 'granted' || !doc.permission.scopes.includes('web'))) reasons.push('web permission is not granted');
      reasons.push(...validateAnchor(catalog,doc.anchor).reasons);
      if (mode === 'public') {
        const {manifest,clearance,event}=releaseContext || {};
        const approved=manifest?.components?.find(c => c.kind === doc.family && c.id === doc.recordId);
        const source=catalog.pieces.find(p => p.pieceId === doc.anchor.pieceId)?.versions.find(v => v.versionId === doc.anchor.versionId);
        const currentSources=manifest?.sources?.map(s => ({...s,sourceFingerprint:catalog.pieces.find(p => p.pieceId === s.pieceId)?.versions.find(v => v.versionId === s.versionId)?.fingerprint ?? null}));
        const component=approved && {...approved,revisionDigest:contentDigest(doc),fixture:doc.fixture,
          pieceId:doc.anchor.pieceId,versionId:doc.anchor.versionId,sourceFingerprint:source?.fingerprint};
        if (!component || !event) reasons.push('exact output and observed publication event are required');
        else {
          const checked=evaluateRelease(manifest,clearance,{currentSources,component,event});
          reasons.push(...checked.reasons);
          if (doc.release.publication?.evidence !== 'release-event:'+contractDigest(event)) reasons.push('publication event is unbound');
        }
      }
    }
    if (reasons.length || !doc) { excluded.push({recordId:group.recordId,reasons:[...new Set(reasons)]}); continue; }
    records.push({id:doc.recordId,revisionId:doc.revisionId,family:doc.family,kind:doc.family === 'note' ? doc.kind : doc.type,
      pieceId:doc.anchor.pieceId,versionId:doc.anchor.versionId,lineId:doc.anchor.lineId,word:clone(doc.anchor.word),
      text:doc.text,citations:clone(doc.citations),credit:doc.author.credit,poemDate:clone(doc.poemDate),noteDate:doc.noteDate,fixture:doc.fixture});
  }
  // A serialized public result must not reveal even the IDs/statuses of withheld
  // records. Studio-only preview retains diagnostics for the author.
  return freeze({records,excluded:mode === 'public' ? [] : excluded});
}
export function projectPreview(value,catalog,options={}) { return projectRecords(value,catalog,{...options,mode:'preview'}); }

export function restoreEnvelope(envelope, existing={notes:[],contributions:[]}) {
  const envelopeErrors=[];
  plainJSON(envelope,envelopeErrors);
  keys(envelope,['format','version','exportedAt','notes','contributions'],'backup',envelopeErrors);
  if (envelopeErrors.length) throw new Error('Invalid notes backup: ' + envelopeErrors.join('; '));
  if (!object(envelope) || envelope.format !== 'versforms-notes-backup' || envelope.version !== 1 || (own(envelope,'exportedAt') && !instant(envelope.exportedAt))) throw new Error('Unsupported or invalid notes backup.');
  const result={notes:[],contributions:[]}, seen=new Map();
  for (const collection of ['notes','contributions']) {
    if (!Array.isArray(envelope[collection]) || !Array.isArray(existing[collection])) throw new Error('Missing backup collection: ' + collection);
    for (const doc of [...existing[collection],...envelope[collection]]) {
      assertRevision(collection,doc);
      const prior=seen.get(doc.revisionId);
      if (prior && stableJSON(prior) !== stableJSON(doc)) throw new Error('Revision collision; existing history was preserved: ' + doc.revisionId);
      if (!prior) { seen.set(doc.revisionId,doc); result[collection].push(clone(doc)); }
    }
  }
  const errors=heads(result).flatMap(g => g.errors);
  if (errors.length) throw new Error('Invalid revision history: ' + errors.join('; '));
  return result;
}
export function exportEnvelope(snapshot={notes:[],contributions:[]}, at=new Date().toISOString()) {
  const envelope={format:'versforms-notes-backup',version:1,exportedAt:at,notes:snapshot.notes || [],contributions:snapshot.contributions || []};
  const checked=restoreEnvelope(envelope);
  return {...envelope,...checked};
}
