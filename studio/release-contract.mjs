// Pure exact-output checks shared by private feature adapters. A hash is not a
// signature; independently supplied author evidence remains the authority.
// No fetch, storage write, publication or account change happens here.
import { stableJSON, sha256 } from './source-fingerprint.mjs';
import { canonicalJSON } from './release-canonical.mjs';

export const OUTPUT_SCHEMA = 'versforms.release-output.v1';
export const CLEARANCE_SCHEMA = 'versforms.release-clearance.v1';
export const EVENT_SCHEMA = 'versforms.release-event.v1';
export const contractDigest = value => sha256(canonicalJSON(value));
const HASH = /^sha256:[a-f0-9]{64}$/;
const hash = value => typeof value === 'string' && HASH.test(value);
const text = v => typeof v === 'string' && v.trim().length > 0;
const object = v => !!v && typeof v === 'object' && !Array.isArray(v);
const same = (a,b) => {try{return canonicalJSON(a) === canonicalJSON(b);}catch{return false;}};
export function validUTCInstant(value) {
  if (typeof value !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$/.test(value) || Number(value.slice(0,4)) < 1) return false;
  const time = Date.parse(value);
  return Number.isFinite(time) && new Date(time).toISOString().slice(0,19) === value.slice(0,19);
}
const instant = validUTCInstant;
function publicationURL(value) {
  if (!text(value) || /[\s\u0000-\u001f\u007f]/.test(value)) return false;
  try { const url = new URL(value); return url.protocol === 'https:' && !!url.hostname && !url.username && !url.password; }
  catch { return false; }
}
const safePath = p => text(p) && !/[\\\u0000-\u001f\u007f]/.test(p) &&
  p.split('/').every(x => x && !['.','..','.git'].includes(x));

export function validateOutputManifest(manifest) {
  if (!object(manifest) || manifest.schema !== OUTPUT_SCHEMA) return ['unsupported-output-manifest'];
  const errors = [], {manifestDigest, ...body} = manifest;
  let calculated;try{calculated=contractDigest(body);}catch{return ['invalid-output-json'];}
  if (manifestDigest !== calculated) errors.push('output-manifest-changed');
  if (!Array.isArray(manifest.files) || !manifest.files.length) return [...errors,'empty-output-inventory'];
  const paths = new Set();
  for (const f of manifest.files) {
    if (!object(f) || !same(Object.keys(f).sort(),['bytes','path','sha256']) || !safePath(f.path) ||
        !Number.isSafeInteger(f.bytes) || f.bytes < 0 || !hash(f.sha256)) errors.push('invalid-output-entry');
    else { if (paths.has(f.path)) errors.push('duplicate-output-path'); paths.add(f.path); }
  }
  if (!Array.isArray(manifest.sources) || !manifest.sources.length) return [...errors,'missing-source-bindings'];
  const sourceKeys = new Set(), fingerprints = new Map();
  for (const s of manifest.sources) {
    if (!object(s) || !text(s.pieceId) || !text(s.versionId) || !hash(s.sourceFingerprint)) { errors.push('invalid-source-binding'); continue; }
    const key = stableJSON([s.pieceId,s.versionId]);
    if (sourceKeys.has(key)) errors.push('duplicate-source-binding');
    sourceKeys.add(key);
    fingerprints.set(key,s.sourceFingerprint);
  }
  if (!Array.isArray(manifest.components)) return [...errors,'invalid-component-list'];
  const seen = new Set();
  for (const c of manifest.components) {
    if (!object(c)) { errors.push('invalid-component'); continue; }
    const key = stableJSON([c.kind,c.id]), sourceKey=stableJSON([c.pieceId,c.versionId]);
    if (!['note','contribution','audio','realization','regions','media'].includes(c.kind) || !text(c.id) || seen.has(key) ||
        !hash(c.revisionDigest) || !hash(c.sourceFingerprint) || typeof c.fixture !== 'boolean' ||
        !sourceKeys.has(sourceKey) || fingerprints.get(sourceKey) !== c.sourceFingerprint) errors.push('invalid-component-binding');
    seen.add(key);
    const file = manifest.files.find(f => f?.path === c.path);
    if (!file || file.sha256 !== c.sha256) errors.push('component-output-not-in-manifest');
  }
  return [...new Set(errors)];
}

export function evaluateRelease(manifest, clearance, {currentSources,component,event} = {}) {
  const reasons = validateOutputManifest(manifest);
  if (reasons.length) return {eligible:false,reasons};
  if (!currentSources || !same(currentSources,manifest.sources)) reasons.push('current-source-bindings-changed-or-missing');
  if (!object(clearance) || clearance.schema !== CLEARANCE_SCHEMA) reasons.push('missing-author-clearance');
  else {
    if (clearance.status !== 'approved' || clearance.manifestDigest !== manifest.manifestDigest) reasons.push('clearance-does-not-cover-output');
    const a = clearance.author_clearance;
    if (!object(a) || !text(a.actor) || !text(a.source) || !instant(a.at) || a.manifestDigest !== manifest.manifestDigest) reasons.push('unattributable-author-clearance');
    if (clearance.execution_authority !== false) reasons.push('record-must-not-imply-execution-authority');
    const pools = clearance.pool_clearance;
    const selected = manifest.sources.map(s => stableJSON([s.pieceId,s.versionId])).sort();
    if (!Array.isArray(pools) || pools.length !== selected.length || !same([...new Set(pools.map(p => stableJSON([p?.pieceId,p?.versionId])))].sort(),selected)) reasons.push('incomplete-pool-clearance');
    else if (pools.some(p => !object(p) || p.pool !== 'series' || !text(p.source))) reasons.push('excluded-or-unattributed-pool');
    if (!object(clearance.evidence) || ['filing_workflow','image_exposure','identity_metadata','device_acceptance'].some(k => !text(clearance.evidence[k]))) reasons.push('incomplete-release-evidence');
  }
  if (component !== undefined) {
    const found = manifest.components.find(c => c.kind === component?.kind && c.id === component?.id);
    if (!found || !same(found,component)) reasons.push('component-changed-or-not-cleared');
    if (component?.fixture !== false) reasons.push('technical-fixture-excluded');
  }
  if (manifest.components.some(c => c.fixture !== false)) reasons.push('technical-fixture-excluded');
  if (event !== undefined) {
    if (!object(event) || event.schema !== EVENT_SCHEMA || event.manifestDigest !== manifest.manifestDigest || event.state !== 'posted' ||
        !text(event.source) || !text(event.recordedBy) || !instant(event.at) || !['site','social'].includes(event.channel)) reasons.push('unbound-publication-event');
    else if (!publicationURL(event.url)) reasons.push('invalid-publication-url');
  }
  return {eligible:!reasons.length,reasons:[...new Set(reasons)],manifestDigest:manifest.manifestDigest,execution_authority:false};
}

export function eventChannels(record) {
  let host; try { host = new URL(record.url).hostname; } catch {}
  const channel = ['site','social'].includes(record.channel) ? record.channel :
    ['versforms.pages.dev','vers.forms','www.vers.forms'].includes(host) ? 'site' : record.type === 'social' ? 'social' : null;
  return {recordedType:record.type ?? null,channel,url:record.url ?? null,publicationClassification:null,classificationProvenance:'author-decision-pending'};
}
