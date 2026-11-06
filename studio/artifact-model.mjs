// Private immutable evidence for audio, pronunciation and script realizations.
// This storage model creates no text, recording, clearance or publication event.
import {stableJSON,sha256} from './source-fingerprint.mjs';
import {validUTCInstant} from './release-contract.mjs';
export const ARTIFACT_KINDS=Object.freeze(['audio-feedback','pronunciation','audio-render','realization','release-evidence']);
const ID=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/, HASH=/^sha256:[a-f0-9]{64}$/;
const id=value=>typeof value==='string'&&ID.test(value), hash=value=>typeof value==='string'&&HASH.test(value);
const object=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const text=v=>typeof v==='string'&&v.trim().length>0;
const copy=v=>JSON.parse(JSON.stringify(v));
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
export function artifactDigest(value) {const {revisionDigest,...body}=value;return sha256(stableJSON(body));}

function assertLosslessJSON(value, visiting=new Set()) {
  if(value===null||typeof value==='boolean')return;
  if(typeof value==='string') {
    for(const point of value) {const code=point.codePointAt(0);if(code>=0xd800&&code<=0xdfff)throw new Error('Artifact payload must be lossless JSON.');}
    return;
  }
  if(typeof value==='number'&&Number.isFinite(value)&&(!Number.isInteger(value)||Number.isSafeInteger(value)))return;
  const array=Array.isArray(value);
  if(!value||typeof value!=='object'||Object.getPrototypeOf(value)!==(array?Array.prototype:Object.prototype)||visiting.has(value))throw new Error('Artifact payload must be lossless JSON.');
  const keys=Reflect.ownKeys(value);
  if(array&&(keys.length!==value.length+1||keys.some(k=>k!=='length'&&(typeof k!=='string'||!/^(0|[1-9][0-9]*)$/.test(k)||Number(k)>=value.length))))throw new Error('Artifact arrays must be dense JSON without extra properties.');
  visiting.add(value);
  try {
    for(const key of keys) {
      if(array&&key==='length')continue;
      const descriptor=Object.getOwnPropertyDescriptor(value,key);
      if(typeof key!=='string'||!descriptor.enumerable||!Object.hasOwn(descriptor,'value'))throw new Error('Artifact payload must be lossless JSON.');
      assertLosslessJSON(key,visiting);
      assertLosslessJSON(descriptor.value,visiting);
    }
  } finally {visiting.delete(value);}
}

export function assertArtifact(_collection,doc) {
  assertLosslessJSON(doc);
  if (_collection !== 'artifacts' || !object(doc) || doc.schemaVersion !== 1 || doc.family !== 'artifact') throw new Error('Invalid artifact envelope.');
  const fields=['schemaVersion','family','kind','recordId','revisionId','parents','source','payload','fixture','at','by','reason','revisionDigest'];
  if (Object.keys(doc).sort().join(',') !== fields.sort().join(',')) throw new Error('Unknown or missing artifact fields.');
  for(const field of ['recordId','revisionId'])if(!id(doc[field]))throw new Error('Invalid artifact identity.');
  if(!ARTIFACT_KINDS.includes(doc.kind)||typeof doc.fixture!=='boolean'||!text(doc.by)||typeof doc.reason!=='string'||!validUTCInstant(doc.at))throw new Error('Invalid artifact provenance.');
  if(!Array.isArray(doc.parents)||new Set(doc.parents).size!==doc.parents.length||doc.parents.some(p=>typeof p!=='string'||!ID.test(p)||p===doc.revisionId))throw new Error('Invalid artifact parents.');
  if(!object(doc.source)||Object.keys(doc.source).sort().join(',')!=='pieceId,sourceFingerprint,versionId'||!id(doc.source.pieceId)||!id(doc.source.versionId)||!hash(doc.source.sourceFingerprint))throw new Error('Invalid artifact source binding.');
  if(!object(doc.payload))throw new Error('Artifact payload must be an object.');
  if(new TextEncoder().encode(JSON.stringify(doc)).length>64*1024)throw new Error('Artifact exceeds 64 KiB.');
  if(!hash(doc.revisionDigest)||artifactDigest(doc)!==doc.revisionDigest)throw new Error('Artifact digest changed.');
  if(doc.kind==='audio-feedback') {
    const p=doc.payload;
    if(!text(p.sampleId)||!['unreviewed','keep','revise','reject'].includes(p.decision)||typeof p.notes!=='string'||['renderDigest','pronunciationDigest','bankDigest'].some(k=>!hash(p[k])))throw new Error('Feedback must bind a render, pronunciation and bank.');
  }
  if(doc.kind==='pronunciation'&&(!Array.isArray(doc.payload.entries)||doc.payload.entries.some(e=>!object(e)||!id(e.lineId)||!text(e.token)||!text(e.pronunciation))))throw new Error('Pronunciation entries need source line IDs and supplied readings.');
  if(doc.kind==='realization') {
    const r=doc.payload.realization,last=r?.revisions?.at(-1);
    if(!r||r.pieceId!==doc.source.pieceId||r.versionId!==doc.source.versionId||last?.source?.versionFingerprint!==doc.source.sourceFingerprint)throw new Error('Realization source does not match its storage binding.');
  }
  return doc;
}

export function createArtifactRevision(input,{previous=null,revisionId=input.revisionId,at=input.at||new Date().toISOString(),by=input.by}={}) {
  if(previous)assertArtifact('artifacts',previous);
  // Validate before JSON cloning: serialization must never turn supplied NaN
  // into null, drop fields, execute getters/toJSON, or fill sparse arrays.
  assertLosslessJSON(input.source);assertLosslessJSON(input.payload);
  const parents=input.parents===undefined?(previous?[previous.revisionId]:[]):input.parents;
  assertLosslessJSON(parents);
  const doc={schemaVersion:1,family:'artifact',kind:input.kind,recordId:input.recordId||previous?.recordId,
    revisionId,parents:copy(parents),source:copy(input.source),payload:copy(input.payload),
    fixture:input.fixture??previous?.fixture??true,at,by,reason:input.reason||'initial',revisionDigest:''};
  if(previous&&(doc.recordId!==previous.recordId||doc.kind!==previous.kind||previous.fixture&&!doc.fixture))throw new Error('Artifact identity or fixture history cannot be replaced.');
  if(previous&&!doc.parents.includes(previous.revisionId))throw new Error('Artifact edit must retain its previous revision as a parent.');
  if(previous&&stableJSON(previous.source)!==stableJSON(doc.source)&&doc.reason!=='source-rebind')throw new Error('Source edits require an explicit artifact source-rebind.');
  doc.revisionDigest=artifactDigest(doc);assertArtifact('artifacts',doc);return freeze(doc);
}

export function artifactHeads(revisions,currentSources=[]) {
  const groups=new Map(),ids=new Map();
  for(const r of revisions){assertArtifact('artifacts',r);if(ids.has(r.revisionId)&&stableJSON(ids.get(r.revisionId))!==stableJSON(r))throw new Error('Artifact revision collision.');ids.set(r.revisionId,r);}
  for(const r of ids.values()){const g=groups.get(r.recordId)||{recordId:r.recordId,revisions:[],errors:[]};g.revisions.push(r);groups.set(r.recordId,g);}
  for(const g of groups.values()) {
    const parents=new Set(),visited=new Set(),visiting=new Set();
    function visit(r) {
      if(visiting.has(r.revisionId)){g.errors.push('revision-cycle');return;}if(visited.has(r.revisionId))return;visiting.add(r.revisionId);
      for(const id of r.parents){const p=ids.get(id);if(!p||p.recordId!==r.recordId||p.kind!==r.kind)g.errors.push('missing-or-foreign-parent');else{parents.add(id);if(p.fixture&&!r.fixture)g.errors.push('fixture-history-removed');if(stableJSON(p.source)!==stableJSON(r.source)&&r.reason!=='source-rebind')g.errors.push('source-rebind-required');visit(p);}}
      visiting.delete(r.revisionId);visited.add(r.revisionId);
    }
    g.revisions.forEach(visit);g.heads=g.revisions.filter(r=>!parents.has(r.revisionId));
    if(g.heads.length!==1)g.errors.push('unresolved-revision-fork');
    const h=g.heads[0],source=h&&currentSources.find(s=>s.pieceId===h.source.pieceId&&s.versionId===h.source.versionId);
    g.stale=!source||source.sourceFingerprint!==h.source.sourceFingerprint;
    g.errors=[...new Set(g.errors)];g.conflicted=!!g.errors.length;
  }
  return [...groups.values()];
}
