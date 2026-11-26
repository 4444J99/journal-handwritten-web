/** Private, bounded package readers. A digest detects change; it grants no release authority. */
const HASH = /^sha256:[a-f0-9]{64}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const MAX_FILE = 16 * 1024 * 1024, MAX_TOTAL = 32 * 1024 * 1024;
const TEMPLATE = 'versforms.t10-static-preview.v1';
const CSP = "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'";
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const hash = value => typeof value === 'string' && HASH.test(value);
const id = value => typeof value === 'string' && ID.test(value);
const fail = message => { throw new Error(message); };
export const packageJSON = value => Array.isArray(value) ? '[' + value.map(packageJSON).join(',') + ']'
  : object(value) ? '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + packageJSON(value[key])).join(',') + '}' : JSON.stringify(value);
function keys(value, names, label) {
  if (!object(value) || Object.keys(value).sort().join(',') !== [...names].sort().join(',')) fail('Invalid ' + label + ' fields.');
}
export function assertSourceBinding(source) {
  keys(source, ['pieceId','versionId','sourceFingerprint'], 'source binding');
  if (!id(source.pieceId) || !id(source.versionId) || !hash(source.sourceFingerprint)) fail('An exact source version and fingerprint are required.');
}
export function sameSource(a, b) {
  assertSourceBinding(a); assertSourceBinding(b);
  return a.pieceId === b.pieceId && a.versionId === b.versionId && a.sourceFingerprint === b.sourceFingerprint;
}
export function sameOriginAsset(value, doc) {
  if (typeof value !== 'string' || !value.trim()) fail('A preview asset URL is required.');
  const url = new URL(value, doc.baseURI);
  if (url.origin !== new URL(doc.baseURI).origin || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash) fail('Preview assets must be served from the same origin without credentials or fragments.');
  return url.href;
}
export function assertPackageReference(value, doc) {
  keys(value, ['manifestUrl','sha256'], 'package reference');
  if (!hash(value.sha256)) fail('A package digest must be a SHA256 string.');
  return sameOriginAsset(value.manifestUrl, doc);
}
function policy(value) {
  keys(value, ['pool','visibility'], 'current source policy');
  if (!['unsorted','series','reserve','archive'].includes(value.pool) || !['private','public','withheld'].includes(value.visibility)) fail('Unknown current source policy.');
  return value;
}
// Cut-up source reveal (journal-handwritten-web #55 step 4): a source line
// may be surfaced in public output only when its piece's pool is exactly
// 'series'. The comparison is the same exact-value rule pool_of() in
// tools/post_poem.py uses — 'Series', ' series', null, and every other
// value are withheld, never revealed. The private studio may show all
// sources; this gate is the public side.
export function sourceRevealAllowed(pool) {
  return pool === 'series';
}
function contextGuard(options, scope) {
  if (typeof options.getCurrentSource !== 'function' || typeof options.getCurrentPolicy !== 'function') fail('Package previews require current source and policy providers.');
  assertSourceBinding(options.source);
  return expectedPolicy => {
    if (!scope.current() || scope.signal.aborted) throw new DOMException('Preview closed.', 'AbortError');
    if (!sameSource(options.source, options.getCurrentSource())) fail('Source changed while the package was loading.');
    const currentPolicy = policy(options.getCurrentPolicy());
    if (currentPolicy.visibility === 'withheld') fail('The current source policy withholds this preview.');
    if (expectedPolicy && packageJSON(currentPolicy) !== packageJSON(policy(expectedPolicy))) fail('Source policy changed; export a fresh private package.');
    return currentPolicy;
  };
}
async function digest(bytes, doc) {
  const result = await doc.defaultView.crypto.subtle.digest('SHA-256', bytes);
  return 'sha256:' + [...new Uint8Array(result)].map(x => x.toString(16).padStart(2,'0')).join('');
}
async function jsonDigest(value, doc) { return digest(new TextEncoder().encode(packageJSON(value)), doc); }
async function logicalSource(snapshot, expected, doc) {
  if (!object(snapshot) || snapshot.pieceId !== expected.pieceId || snapshot.versionId !== expected.versionId || snapshot.versionFingerprint !== expected.sourceFingerprint || !Array.isArray(snapshot.members) || !snapshot.members.length || !Array.isArray(snapshot.lines) || !snapshot.lines.length) fail('Invalid package logical source.');
  const ids = new Set();
  for (const member of snapshot.members) if (!Array.isArray(member) || member.length !== 2 || !id(member[0]) || !Array.isArray(member[1]) || !member[1].length || member[1].some(i => !Number.isSafeInteger(i) || i < 0)) fail('Invalid package source membership.');
  const lines = snapshot.lines.map(line => {
    if (!object(line) || !id(line.lineId) || ids.has(line.lineId) || typeof line.text !== 'string' || typeof line.blockType !== 'string' || typeof line.breakBefore !== 'boolean') fail('Invalid package logical source line.');
    ids.add(line.lineId); return {lineId:line.lineId,text:line.text,blockType:line.blockType,breakBefore:line.breakBefore};
  });
  if (await jsonDigest({pieceId:snapshot.pieceId,versionId:snapshot.versionId,members:snapshot.members,lines},doc) !== expected.sourceFingerprint) fail('Package source is not the current canonical v2 reading.');
  return ids;
}
function decode(bytes) { return new TextDecoder('utf-8', {fatal:true}).decode(bytes); }
function json(bytes) { return JSON.parse(decode(bytes)); }
async function fetchBytes(url, expected, limit, scope, doc, current) {
  current();
  const response = await doc.defaultView.fetch(url, {signal:scope.signal, cache:'no-store', credentials:'same-origin', redirect:'error'});
  try { current(); } catch (error) { await response.body?.cancel().catch(() => {}); throw error; }
  if (response.url !== url) { await response.body?.cancel().catch(() => {}); fail('Private package response URL changed.'); }
  if (!response.ok || !response.body) fail('Private package file could not be loaded.');
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > limit)) { await response.body.cancel(); current(); fail('Private package file exceeds its byte limit.'); }
  const reader = response.body.getReader(), chunks = [];
  let length = 0;
  try {
    for (;;) {
      const {done,value} = await reader.read(); current();
      if (done) break;
      length += value.byteLength;
      if (length > limit) fail('Private package file exceeds its byte limit.');
      chunks.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  if (expected.bytes !== undefined && length !== expected.bytes) fail('Private package file length changed.');
  if (await digest(bytes, doc) !== expected.sha256) fail('Private package file digest changed.');
  current(); return bytes;
}
function filePath(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*$/.test(value) || value.split('/').some(p => p === '.' || p === '..')) fail('Invalid package file path.');
  return value;
}
async function packageFiles(manifest, manifestURL, scope, doc, current, withMediaType = true) {
  if (!Array.isArray(manifest.files) || !manifest.files.length || manifest.files.length > 20) fail('Invalid package file inventory.');
  const paths = new Set(); let total = 0;
  for (const file of manifest.files) {
    keys(file, withMediaType ? ['path','bytes','mediaType','sha256'] : ['path','bytes','sha256'], 'package file');
    filePath(file.path);
    if (paths.has(file.path) || !hash(file.sha256) || !Number.isSafeInteger(file.bytes) || file.bytes < 1 || file.bytes > MAX_FILE || (withMediaType && typeof file.mediaType !== 'string')) fail('Invalid or duplicate package file.');
    paths.add(file.path); total += file.bytes;
  }
  if (total > MAX_TOTAL) fail('Private package exceeds its total byte limit.');
  const files = new Map();
  for (const file of manifest.files) {
    // Pages serves index.html at its directory URL and redirects an explicit
    // index.html request. Request that single known canonical entry directly;
    // redirects remain forbidden for it and every other package dependency.
    const url = new URL(file.path === 'index.html' ? './' : file.path, manifestURL).href;
    sameOriginAsset(url, doc);
    files.set(file.path, {entry:file, bytes:await fetchBytes(url, file, file.bytes, scope, doc, current)});
  }
  return files;
}
function byteBase64(bytes, win) {
  let value = '';
  for (let offset = 0; offset < bytes.length; offset += 32768) value += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
  return win.btoa(value);
}
function styleFor(fontURL, writing) {
  return `
@font-face{font-family:ajp-scribbles;src:url('${fontURL}');font-display:block}
:root{color-scheme:light dark;--paper:#f2eee6;--ink:#25241e;--rule:#b4ad9d}
@media(prefers-color-scheme:dark){:root{--paper:#181a1b;--ink:#e7e1d5;--rule:#66645c}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}
main{max-width:900px;margin:auto;padding:70px 6vw 120px;overflow:auto}
#realization{font-size:clamp(19px,3vw,32px);line-height:1.65;writing-mode:${writing};text-align:start;unicode-bidi:isolate}
.line{white-space:pre-wrap;overflow-wrap:normal;word-break:normal;hyphens:none;min-height:1.65em}
.stanza{margin-block-start:1.1em}.author-font{font-family:ajp-scribbles,serif;font-kerning:normal;font-variant-ligatures:normal}
.fallback{font-family:serif}details{position:absolute;right:18px;top:18px;max-width:min(92vw,680px);max-height:80vh;overflow:auto;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:10px}
summary{cursor:pointer;list-style:none;font-size:21px}details[open]{padding:20px}details p{line-height:1.5}pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}h1{font-size:18px}
.qa{font-size:40px;line-height:1.8}@media print{details{position:static}main{padding:1cm}}
`;
}
function attributes(element, expected) {
  if (!element || packageJSON(Object.fromEntries([...element.attributes].map(a => [a.name,a.value]))) !== packageJSON(expected)) fail('Generated preview attributes differ from the static template.');
}
function children(element, names) {
  if (!element || [...element.children].map(e => e.tagName.toLowerCase()).join(',') !== names.join(',')) fail('Generated preview structure differs from the static template.');
  if ([...element.childNodes].some(n => n.nodeType !== 1 && (n.nodeType !== 3 || n.textContent.trim()))) fail('Generated preview has undeclared content.');
  return [...element.children];
}
function leaf(element, text, attrs = {}) {
  attributes(element, attrs);
  if (element.children.length || element.textContent !== text) fail('Generated preview text differs from its stored realization.');
}
function validateStaticHTML(markup, realization, revision, font, doc) {
  const writing = revision.layout?.writingMode;
  if (!['horizontal-tb','vertical-rl','vertical-lr'].includes(writing) || !['ltr','rtl'].includes(revision.layout?.direction) || typeof revision.language !== 'string' || !/^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/.test(revision.language) || typeof revision.script !== 'string' || !/^[A-Z][a-z]{3}$/.test(revision.script)) fail('Invalid stored realization layout.');
  const fontURL = 'data:' + font.entry.mediaType + ';base64,' + byteBase64(font.bytes, doc.defaultView);
  const style = styleFor(fontURL, writing);
  // Check the sole CSS payload before parsing. No attacker-controlled URL is
  // ever attached to a document; the font URL contains only verified bytes.
  const styles = [...markup.matchAll(/<style>([\s\S]*?)<\/style>/g)];
  if (styles.length !== 1 || styles[0][1] !== style || /<!--|<\?/.test(markup)) fail('Generated preview CSS differs from the bounded T10 template.');
  if (!Array.isArray(revision.lines) || !revision.lines.length || revision.lines.some(row => !id(row.id) || typeof row.text !== 'string' || typeof row.breakBefore !== 'boolean')) fail('Invalid stored logical lines.');
  // The exporter has a deliberately fixed vocabulary, attribute spelling and
  // quoting. Validate raw start tags before DOMParser so even legacy fetching
  // attributes (body background, refresh, etc.) never reach a parsed document.
  const tags = new Set(['<!doctype html>',`<html lang="en" data-template="${TEMPLATE}">`,'<head>','<body>','<meta charset="utf-8">','<meta name="viewport" content="width=device-width,initial-scale=1">','<meta name="robots" content="noindex,nofollow">',`<meta http-equiv="Content-Security-Policy" content="${CSP}">`,'<title>','<style>','<main>',`<article id="realization" lang="${revision.language}" dir="${revision.layout.direction}" data-script="${revision.script}" aria-label="Private script realization">`,'<details id="details">','<summary aria-label="Show fixture details">','<h1>','<p>','<pre id="metadata">','<div class="qa fallback" id="nfd-probe" lang="en" dir="ltr">','<div class="qa fallback" id="nfc-probe" lang="en" dir="ltr">','<br>']);
  for (const tag of ['html','head','body','title','style','main','article','details','summary','h1','p','pre','div']) tags.add('</' + tag + '>');
  for (const line of revision.lines) for (const face of ['author-font','fallback']) tags.add(`<div class="line ${line.breakBefore ? 'stanza ' : ''}${face}" data-line-id="${line.id}">`);
  const remainder = markup.replace(/<[^>]*>/g,tag => { if (!tags.has(tag)) fail('Generated preview contains an undeclared element or attribute.'); return ''; });
  if (remainder.includes('<') || remainder.includes('>')) fail('Malformed static preview markup.');
  const parsed = new doc.defaultView.DOMParser().parseFromString(markup, 'text/html');
  if (parsed.doctype?.name !== 'html') fail('Invalid static preview document.');
  attributes(parsed.documentElement, {lang:'en','data-template':TEMPLATE});
  attributes(parsed.head, {}); attributes(parsed.body, {});
  const head = children(parsed.head, ['meta','meta','meta','meta','title','style']);
  attributes(head[0], {charset:'utf-8'});
  attributes(head[1], {name:'viewport',content:'width=device-width,initial-scale=1'});
  attributes(head[2], {name:'robots',content:'noindex,nofollow'});
  attributes(head[3], {'http-equiv':'Content-Security-Policy',content:CSP});
  leaf(head[4], 'T10 private technical preview'); leaf(head[5], style);
  const [main,details] = children(parsed.body, ['main','details']); attributes(main, {});
  const [article] = children(main, ['article']);
  attributes(article, {id:'realization',lang:revision.language,dir:revision.layout.direction,'data-script':revision.script,'aria-label':'Private script realization'});
  attributes(details, {id:'details'});
  const detail = children(details, ['summary','h1','p','pre','p','div','div','p']);
  leaf(detail[0], '⋯', {'aria-label':'Show fixture details'});
  leaf(detail[1], revision.fixture ? 'Technical fixture — verbatim source; no translation or language adoption' : 'Private author-supplied realization — not cleared for release');
  leaf(detail[2], 'Source readings and exported corrections are preserved. This is a private tooling preview, not a final poem selection. This evidence panel is hidden until requested.');
  attributes(detail[3], {id:'metadata'});
  if (detail[3].children.length) fail('Invalid realization metadata.');
  const metadata = JSON.parse(detail[3].textContent);
  keys(metadata, ['id','revisionId','revisionDigest','pieceId','versionId','language','script','mode','fixture','fallbackRuns'], 'preview metadata');
  const {fallbackRuns,...identity} = metadata;
  const expected = {id:realization.id,revisionId:revision.id,revisionDigest:revision.digest,pieceId:realization.pieceId,versionId:realization.versionId,language:revision.language,script:revision.script,mode:revision.mode,fixture:revision.fixture};
  if (packageJSON(identity) !== packageJSON(expected) || !Array.isArray(fallbackRuns)) fail('Generated preview metadata does not match its stored realization.');
  const fallback = new Set();
  for (const run of fallbackRuns) {
    keys(run, ['lineId','codepoints'], 'fallback run');
    const line = revision.lines.find(l => l.id === run.lineId);
    if (!line || fallback.has(run.lineId) || !Array.isArray(run.codepoints) || !run.codepoints.length || run.codepoints.some(cp => typeof cp !== 'string' || !/^U\+[0-9A-F]{4,6}$/.test(cp) || ![...line.text].some(c => c.codePointAt(0) === Number.parseInt(cp.slice(2),16)))) fail('Invalid whole-line fallback declaration.');
    fallback.add(run.lineId);
  }
  if (!Array.isArray(revision.lines) || !revision.lines.length) fail('Stored realization has no lines.');
  const lines = children(article, revision.lines.map(() => 'div'));
  for (let i=0; i<lines.length; i++) {
    const row = revision.lines[i], element = lines[i];
    if (!id(row.id) || typeof row.text !== 'string' || typeof row.breakBefore !== 'boolean') fail('Invalid stored logical line.');
    attributes(element, {class:'line ' + (row.breakBefore ? 'stanza ' : '') + (fallback.has(row.id) ? 'fallback' : 'author-font'),'data-line-id':row.id});
    if (element.textContent !== row.text) fail('Generated preview changed a logical Unicode line.');
    if (row.text === '') { const [br] = children(element,['br']); attributes(br,{}); }
    else if (element.children.length) fail('Generated preview split a logical Unicode line.');
  }
  leaf(detail[4], 'Unicode diagnostics below are test characters, separate from the poem. Neither test adds characters to the author font. The complete run uses the system serif fallback where author coverage is absent.');
  leaf(detail[5], 'A\u0301', {class:'qa fallback',id:'nfd-probe',lang:'en',dir:'ltr'});
  leaf(detail[6], '\u00c1', {class:'qa fallback',id:'nfc-probe',lang:'en',dir:'ltr'});
  leaf(detail[7], 'NFD: U+0041 U+0301 · NFC: U+00C1. Stored text is not normalized. Both runs remain intact for browser shaping. RTL and vertical layouts require a script-specific acceptance pass after author selection.');
  return {lineCount:lines.length,fallbackRuns};
}

export async function loadRealizationPackage(options) {
  const {descriptor,source,scope,doc,getStoredArtifact} = options;
  const manifestURL = assertPackageReference(descriptor.package, doc);
  if (!id(descriptor.revisionId) || typeof getStoredArtifact !== 'function') fail('Realization packages require an exact current stored artifact revision.');
  const guard = contextGuard(options, scope);
  const stored = JSON.parse(JSON.stringify(getStoredArtifact()));
  if (!object(stored) || stored.family !== 'artifact' || stored.kind !== 'realization' || !id(stored.recordId) || !id(stored.revisionId) || !hash(stored.revisionDigest) || stored.revisionId !== descriptor.revisionId || !sameSource(stored.source, source)) fail('The selected stored artifact does not match this realization package.');
  const {revisionDigest,...body} = stored;
  if (await jsonDigest(body,doc) !== revisionDigest) fail('The selected stored artifact digest changed.');
  const current = expectedPolicy => {
    const currentPolicy = guard(expectedPolicy), latest = getStoredArtifact();
    if (!latest || latest.revisionId !== stored.revisionId || latest.revisionDigest !== stored.revisionDigest || packageJSON(latest) !== packageJSON(stored)) fail('Stored artifact changed while the package was loading.');
    if (['reserve','archive'].includes(currentPolicy.pool)) fail('The current source pool excludes this realization preview.');
    return currentPolicy;
  };
  current();
  const manifest = json(await fetchBytes(manifestURL,descriptor.package,64*1024,scope,doc,current));
  keys(manifest,['schema','schemaVersion','template','source','policy','artifactRevisionId','artifactDigest','realization','entry','model','artifact','fixture','may_publish','files'],'realization package');
  if (manifest.schema !== 'versforms.realization-preview-package.v1' || manifest.schemaVersion !== 1 || manifest.template !== TEMPLATE || manifest.entry !== 'index.html' || manifest.model !== 'realization.json' || manifest.artifact !== 'artifact.json' || typeof manifest.fixture !== 'boolean' || manifest.may_publish !== false) fail('Unsupported or publishable realization package.');
  assertSourceBinding(manifest.source);
  keys(manifest.realization,['id','revisionId','revisionDigest'],'realization identity');
  if (!id(manifest.artifactRevisionId) || !hash(manifest.artifactDigest) || !id(manifest.realization.id) || !id(manifest.realization.revisionId) || !hash(manifest.realization.revisionDigest) || !sameSource(manifest.source,source) || manifest.artifactRevisionId !== stored.revisionId || manifest.artifactDigest !== stored.revisionDigest) fail('Package does not bind the selected stored artifact and source.');
  const realization = stored.payload?.realization, revision = realization?.revisions?.at(-1);
  if (!realization || !revision || realization.id !== manifest.realization.id || realization.pieceId !== source.pieceId || realization.versionId !== source.versionId || revision.id !== manifest.realization.revisionId || revision.digest !== manifest.realization.revisionDigest || revision.source?.versionFingerprint !== source.sourceFingerprint || typeof revision.fixture !== 'boolean' || typeof stored.fixture !== 'boolean' || manifest.fixture !== (stored.fixture || revision.fixture) || !['private','public-proposed'].includes(revision.visibility)) fail('Package does not bind the current stored realization revision.');
  const guardPackage = () => current(manifest.policy);
  guardPackage();
  await logicalSource(revision.source,source,doc); guardPackage();
  if (!Array.isArray(revision.glyphAssets) || revision.glyphAssets.length > 16) fail('Invalid glyph asset inventory.');
  let parent = null;
  for (const saved of realization.revisions) {
    if (typeof saved.fixture !== 'boolean' || saved.fixture && !stored.fixture) fail('Stored artifact cannot remove realization fixture history.');
    if (!id(saved.id) || !hash(saved.digest) || saved.parent !== parent) fail('Invalid immutable realization history.');
    const {digest:expectedDigest,...revisionBody} = saved;
    if (await jsonDigest(revisionBody,doc) !== expectedDigest) fail('Stored realization revision digest changed.');
    guardPackage(); parent = saved.digest;
  }
  const required = new Set([manifest.entry,manifest.model,manifest.artifact]);
  for (const asset of revision.glyphAssets) {
    if (!object(asset) || !id(asset.id) || !hash(asset.sha256) || typeof asset.path !== 'string' || !/^assets\/[A-Za-z0-9_.-]+$/.test(asset.path) || !['font','capture-manifest'].includes(asset.kind) || !['private','public-proposed'].includes(asset.visibility)) fail('Invalid stored glyph asset.');
    filePath(asset.path); required.add(asset.path);
    if (!Array.isArray(manifest.files) || manifest.files.find(f => f?.path === asset.path)?.sha256 !== asset.sha256) fail('Package glyph asset differs from the stored realization.');
  }
  if (!Array.isArray(manifest.files) || manifest.files.length !== required.size || manifest.files.some(file => !required.has(file?.path))) fail('Realization package has missing or undeclared dependencies.');
  const files = await packageFiles(manifest,manifestURL,scope,doc,guardPackage);
  if (files.get(manifest.entry).entry.mediaType !== 'text/html' || files.get(manifest.model).entry.mediaType !== 'application/json' || files.get(manifest.artifact).entry.mediaType !== 'application/json') fail('Invalid realization package media type.');
  const model = json(files.get(manifest.model).bytes), artifact = json(files.get(manifest.artifact).bytes);
  keys(model,['format','schemaVersion','realizations'],'realization model');
  if (model.format !== 'versforms-script-realizations' || model.schemaVersion !== 1 || !Array.isArray(model.realizations) || model.realizations.length !== 1 || packageJSON(model.realizations[0]) !== packageJSON(realization) || packageJSON(artifact) !== packageJSON(stored)) fail('Package model or artifact bytes do not match the stored immutable revision.');
  const fonts = revision.glyphAssets.filter(a => a.kind === 'font');
  if (fonts.length !== 1) fail('The bounded T10 template requires one font.');
  const font = files.get(fonts[0].path);
  const media = {otf:'font/otf',ttf:'font/ttf',woff:'font/woff',woff2:'font/woff2'}[fonts[0].path.split('.').at(-1).toLowerCase()];
  if (!media || font.entry.mediaType !== media) fail('Invalid package font media type.');
  for (const asset of revision.glyphAssets.filter(a => a.kind === 'capture-manifest')) if (files.get(asset.path).entry.mediaType !== 'application/json') fail('Invalid capture provenance media type.');
  const html = decode(files.get(manifest.entry).bytes);
  const rendering = validateStaticHTML(html,realization,revision,font,doc);
  guardPackage();
  return {html,manifest,rendering,assertCurrent:guardPackage};
}

function scoped(entry) {
  if (!object(entry)) fail('Invalid region policy entry.');
  const scopes = entry.scopes === undefined || (Array.isArray(entry.scopes) && !entry.scopes.length) ? ['all'] : entry.scopes;
  if (!Array.isArray(scopes) || scopes.some(s => typeof s !== 'string' || !['all','private-local','author-cut-private','public-release','cipher-public'].includes(s))) fail('Invalid region policy scope.');
  return scopes.includes('all') || scopes.includes('private-local');
}
function stringArray(value, label) {
  if (!Array.isArray(value) || value.some(v => typeof v !== 'string' || !v)) fail('Invalid ' + label + '.');
  return value;
}
function validateRegionPolicy(manifest, rules) {
  // A separate release gate may retain author permissions. This private route
  // grants none: its own manifest scope and publication flag must stay disabled.
  if (manifest.schema !== 'versforms.source-region-manifest.v1' || manifest.scope?.distribution !== 'private-local' || manifest.scope?.may_publish !== false || rules.schema !== 'versforms.visibility-policy.v1' || rules.publication?.enabled !== false) fail('Region scope is not a private, nonpublishing preview.');
  if (!Array.isArray(manifest.atoms) || !manifest.atoms.length || !Array.isArray(manifest.source_assets) || !object(rules.pieces)) fail('Invalid region manifest or policy.');
  const withheldAssets = stringArray(rules.withheld_assets || [],'withheld assets'), withheldPages = stringArray(rules.withheld_pages || [],'withheld pages');
  for (const asset of manifest.source_assets) if (asset.withheld === true || withheldAssets.includes(asset.asset_id) || withheldAssets.includes(asset.path)) fail('Region policy withholds a source asset.');
  const ids = new Set();
  for (const atom of manifest.atoms) {
    if (!object(atom) || typeof atom.atom_id !== 'string' || !atom.atom_id || ids.has(atom.atom_id) || !id(atom.piece_id) || !id(atom.version_id) || !id(atom.page_id)) fail('Invalid or duplicate source atom.');
    ids.add(atom.atom_id);
    const piece = rules.pieces[atom.piece_id];
    if (!object(piece) || !['unassigned','series','reserve','archive'].includes(piece.pool) || withheldPages.includes(atom.page_id) || stringArray(piece.withheld_versions || [],'withheld versions').includes(atom.version_id)) fail('Region policy withholds this source.');
    if (!Array.isArray(piece.excluded_versions || []) || !Array.isArray(piece.piece_vetoes || []) || !Array.isArray(piece.strike_through_vetoes || [])) fail('Invalid source-region vetoes.');
    for (const exclusion of piece.excluded_versions || []) if (scoped(exclusion) && exclusion.version_id === atom.version_id) fail('Region version is excluded for private inspection.');
    for (const veto of piece.piece_vetoes || []) if (scoped(veto) && (veto.version_id == null || veto.version_id === atom.version_id)) fail('A piece veto excludes this private region.');
    for (const veto of piece.strike_through_vetoes || []) {
      if (!scoped(veto) || veto.version_id && veto.version_id !== atom.version_id) continue;
      const atomIds = stringArray(veto.atom_ids || [],'veto atom IDs'), lineIds = stringArray(veto.line_ids || [],'veto line IDs');
      const sourceLines = [...(atom.lineage?.source_line_ids || []),atom.source_ids?.line_id];
      if (!atomIds.length && !lineIds.length || atomIds.includes(atom.atom_id) || sourceLines.some(l => lineIds.includes(l))) fail('A source-line veto excludes this private region.');
    }
  }
}
function validBox(box) { return Array.isArray(box) && box.length === 4 && box.every(n => typeof n === 'number' && Number.isFinite(n)) && box[0] >= 0 && box[1] >= 0 && box[2] <= 1 && box[3] <= 1 && box[2] > box[0] && box[3] > box[1]; }
function regionGeometry(geometry, anchor, options) {
  const {getCurrentReviewGeometry,getCurrentReaderGeometry} = options;
  if (typeof getCurrentReviewGeometry !== 'function' && typeof getCurrentReaderGeometry !== 'function') fail('Region packages require current source geometry.');
  const review = geometry.reviewPageGeometry, canonical = geometry.canonicalPage;
  if (!object(review) || !object(canonical) || review.pageId !== anchor.pageId || canonical.pageId !== anchor.pageId || !Array.isArray(review.blocks) || !Array.isArray(canonical.lines) || canonical.dimensions?.width !== review.width || canonical.dimensions?.height !== review.height) fail('Invalid region geometry proof.');
  if (typeof getCurrentReviewGeometry === 'function' && packageJSON(getCurrentReviewGeometry(anchor.pageId)) !== packageJSON(review)) fail('Current review geometry changed; export a fresh region package.');
  const allLines = review.blocks.flatMap(b => b.lines || []), line = allLines.find(l => l.lineId === anchor.lineId);
  const block = review.blocks.find(b => b.lines?.some(l => l.lineId === anchor.lineId));
  const canonicalLine = canonical.lines.find(l => l.lineId === anchor.lineId);
  if (!line || !block || !canonicalLine || canonical.lines.length !== allLines.length || canonical.lines.some(l => !allLines.some(r => r.lineId === l.lineId && packageJSON(r.box) === packageJSON(l.geometry?.studioBox)))) fail('Canonical and review geometry disagree.');
  const blockAvailable = block.lines.every(l => validBox(l.box) && l.sourceAnchor?.status !== 'unavailable' && canonical.lines.find(c => c.lineId === l.lineId)?.geometry?.status === 'available');
  if (anchor.status === 'available') {
    if (!blockAvailable || !validBox(anchor.box) || packageJSON(anchor.box) !== packageJSON(line.box) || canonicalLine.geometry.status !== 'available') fail('Region anchor substitutes incomplete or unavailable geometry.');
  } else if (anchor.status !== 'unavailable' || anchor.box !== null || blockAvailable) fail('Invalid unavailable region anchor.');
  if (typeof getCurrentReaderGeometry === 'function') {
    const current = getCurrentReaderGeometry(anchor.pageId);
    if (!object(current) || current.pageId !== canonical.pageId || current.width !== canonical.dimensions.width || current.height !== canonical.dimensions.height || !Array.isArray(current.lines) || current.lines.length !== canonical.lines.length) fail('Current reader geometry is unavailable.');
    for (const row of current.lines) {
      const saved = canonical.lines.find(l => l.lineId === row.lineId);
      if (!saved || packageJSON(row.readerRow) !== packageJSON(saved.geometry.readerRow)) fail('Current reader geometry changed; export a fresh region package.');
    }
    const selected = current.lines.find(l => l.lineId === anchor.lineId);
    if (!selected || anchor.status === 'available' && selected.available !== true) fail('Current reader alignment is unavailable.');
  }
}

export async function loadRegionPackage(options) {
  const {descriptor,source,scope,doc,getCurrentRegionMedia} = options;
  const manifestURL = assertPackageReference(descriptor.package,doc), guard = contextGuard(options,scope);
  if (typeof descriptor.atomId !== 'string' || !/^vf:atom:[A-Za-z0-9_./:-]+$/.test(descriptor.atomId) || ['manifestDigest','geometryDigest','mediaDigest','policyDigest'].some(k => !hash(descriptor[k])) || typeof getCurrentRegionMedia !== 'function') fail('Region packages require exact region, geometry, media and policy identities and a current media provider.');
  guard();
  const manifest = json(await fetchBytes(manifestURL,descriptor.package,64*1024,scope,doc,guard));
  keys(manifest,['schema','audience','fixture','mayPublish','scope','source','sourcePolicy','atomId','manifestDigest','geometryDigest','mediaDigest','policyDigest','sourceAnchor','files','image'],'private region package');
  if (manifest.schema !== 'versforms.private-region-preview.v1' || manifest.audience !== 'private' || manifest.fixture !== true || manifest.mayPublish !== false || manifest.scope !== 'private-local' || !sameSource(manifest.source,source) || manifest.atomId !== descriptor.atomId || ['manifestDigest','geometryDigest','mediaDigest','policyDigest'].some(k => !hash(manifest[k]) || manifest[k] !== descriptor[k])) fail('Region package identity or private scope changed.');
  if (descriptor.sourcePolicy !== undefined && packageJSON(policy(descriptor.sourcePolicy)) !== packageJSON(policy(manifest.sourcePolicy))) fail('Region source policy differs from its selected snapshot.');
  keys(manifest.sourceAnchor,['lineId','pageId','status','box','reason'],'source anchor');
  const anchor = manifest.sourceAnchor;
  if (!id(anchor.lineId) || !id(anchor.pageId) || !['available','unavailable'].includes(anchor.status) || anchor.reason !== null && typeof anchor.reason !== 'string') fail('Invalid region source anchor.');
  keys(manifest.image,['path','width','height','display'],'region image');
  if (manifest.image.path !== 'assets/source.jpg' || manifest.image.display !== 'full-source-image-no-crop' || !Number.isSafeInteger(manifest.image.width) || !Number.isSafeInteger(manifest.image.height) || manifest.image.width < 1 || manifest.image.height < 1 || manifest.image.width * manifest.image.height > 40_000_000) fail('Invalid bounded source image.');
  const initialReviewGeometry = typeof options.getCurrentReviewGeometry === 'function' ? packageJSON(options.getCurrentReviewGeometry(anchor.pageId)) : null;
  const initialReaderGeometry = typeof options.getCurrentReaderGeometry === 'function' ? packageJSON(options.getCurrentReaderGeometry(anchor.pageId)) : null;
  const mediaURL = sameOriginAsset(getCurrentRegionMedia(anchor.pageId),doc);
  let geometry = null;
  const current = () => {
    guard(manifest.sourcePolicy);
    if (initialReviewGeometry !== null && packageJSON(options.getCurrentReviewGeometry(anchor.pageId)) !== initialReviewGeometry || initialReaderGeometry !== null && packageJSON(options.getCurrentReaderGeometry(anchor.pageId)) !== initialReaderGeometry || sameOriginAsset(getCurrentRegionMedia(anchor.pageId),doc) !== mediaURL) fail('Current region geometry or media selection changed while loading.');
    if (geometry) regionGeometry(geometry,anchor,options);
  };
  current();
  const required = ['assets/source.jpg','geometry.json','policy.json','region-manifest.json','source.json'];
  if (!Array.isArray(manifest.files) || manifest.files.length !== required.length || manifest.files.some(file => !required.includes(file?.path))) fail('Region package dependency inventory changed.');
  const files = await packageFiles(manifest,manifestURL,scope,doc,current,false);
  if (files.size !== required.length || required.some(p => !files.has(p)) || files.get('assets/source.jpg').entry.sha256 !== manifest.mediaDigest || files.get('geometry.json').entry.sha256 !== manifest.geometryDigest || files.get('policy.json').entry.sha256 !== manifest.policyDigest || files.get('region-manifest.json').entry.sha256 !== manifest.manifestDigest) fail('Region package dependency inventory changed.');
  const sourceProof = json(files.get('source.json').bytes), regionManifest = json(files.get('region-manifest.json').bytes), rules = json(files.get('policy.json').bytes);
  keys(sourceProof,['snapshot','sourcePolicy'],'region source proof');
  if (packageJSON(policy(sourceProof.sourcePolicy)) !== packageJSON(policy(manifest.sourcePolicy))) fail('Region policy proof changed.');
  const sourceIds = await logicalSource(sourceProof.snapshot,source,doc); current();
  validateRegionPolicy(regionManifest,rules);
  const atoms = regionManifest.atoms.filter(a => a.atom_id === manifest.atomId);
  if (atoms.length !== 1) fail('Selected atom is not unique in the original region manifest.');
  const atom = atoms[0];
  if (atom.piece_id !== source.pieceId || atom.version_id !== source.versionId || atom.page_id !== anchor.pageId || atom.source_ids?.line_id !== anchor.lineId || !sourceIds.has(anchor.lineId) || !sourceProof.snapshot.members.some(m => m[0] === anchor.pageId && m[1].includes(atom.source_ids.block_index))) fail('Selected region is outside the current exact source version.');
  for (const a of regionManifest.atoms) if (a.piece_id !== source.pieceId || a.version_id !== source.versionId || a.source_ids?.line_id && !sourceIds.has(a.source_ids.line_id) || (a.lineage?.source_line_ids || []).some(l => !sourceIds.has(l))) fail('Region lineage contains an unavailable source.');
  geometry = json(files.get('geometry.json').bytes);
  keys(geometry,['atomId','region','authorBox','canonicalPage','reviewPageGeometry','sourceAnchor'],'region geometry proof');
  if (geometry.atomId !== atom.atom_id || packageJSON(geometry.region) !== packageJSON(atom.region) || packageJSON(geometry.authorBox) !== packageJSON(atom.author_box ?? null) || packageJSON(geometry.sourceAnchor) !== packageJSON(anchor)) fail('Selected region geometry differs from its original manifest.');
  current();
  const assets = regionManifest.source_assets.filter(a => a.page_id === anchor.pageId && a.kind === 'page-scan' && a.tier === 'p');
  if (assets.length !== 1 || typeof assets[0].sha256 !== 'string' || 'sha256:' + assets[0].sha256 !== manifest.mediaDigest || assets[0].size !== files.get('assets/source.jpg').entry.bytes || !geometry.canonicalPage.assets?.some(a => a.id === 'asset:' + assets[0].path && a.sha256 === manifest.mediaDigest) || geometry.canonicalPage.dimensions.width !== manifest.image.width || geometry.canonicalPage.dimensions.height !== manifest.image.height) fail('Source image differs from the original and canonical media identities.');
  // Independently read current source media; an old copied package is not proof
  // that the source image still has these bytes.
  await fetchBytes(mediaURL,{sha256:manifest.mediaDigest,bytes:files.get('assets/source.jpg').entry.bytes},MAX_FILE,scope,doc,current);
  current();
  const bytes = files.get('assets/source.jpg').bytes;
  const bitmap = await doc.defaultView.createImageBitmap(new Blob([bytes],{type:'image/jpeg'}));
  try { if (bitmap.width !== manifest.image.width || bitmap.height !== manifest.image.height) fail('Source image dimensions changed.'); }
  finally { bitmap.close(); }
  current();
  return {bytes,manifest,assertCurrent:current};
}
