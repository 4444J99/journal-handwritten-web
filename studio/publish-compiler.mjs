// Pure publication compiler. No credentials, network access, storage or git.
// The Python posting path remains the reference; atlas tiles are prepared offline.
import {buildVariorumCatalog,materializeComposite} from './variorum-model.mjs';
import { stableJSON, logicalSourcePayload } from './source-fingerprint.mjs';

export const BLANK = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>versforms</title><meta name="robots" content="noindex"><style>:root{--paper:#e6dfd2;color-scheme:light}@media(prefers-color-scheme:dark){:root{--paper:#16171a;color-scheme:dark}}html,body{margin:0;height:100%;background:var(--paper)}</style></head><body></body></html>';
export const canonical = stableJSON;
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const clone = x => JSON.parse(JSON.stringify(x));
const unique = xs => [...new Set(xs)];
const pools = ['series', 'reserve', 'archive'];
const key = (pg, bi) => `${pg}/${bi}`;
export const encode = x => new TextEncoder().encode(x);
export async function digest(bytes) {
  const out = await crypto.subtle.digest('SHA-256', typeof bytes === 'string' ? encode(bytes) : bytes);
  return [...new Uint8Array(out)].map(x => x.toString(16).padStart(2, '0')).join('');
}

// Assemble only the requested pieces. Historical revisions are versions, not
// replacement source; their materialized text stays frozen even after retagging.
export function assembleEffectiveSource(source,db,{pieces=[]}={}) {
  const effective=clone(source), records=Object.values(db.composites || {}).filter(r=>r.family==='composite' && pieces.includes(r.pieceId));
  for(const p of Object.values(db.composites || {}))if(p.family==='promotion'&&pieces.includes(p.pieceId)){
    const r=db.composites[p.originComposite?.revisionId];if(!r||r.family!=='composite')throw new Error('promotion_source_missing');
    if(effective.j.pieces.some(pc=>pc.id===p.pieceId))throw new Error('promotion_piece_collision');
    effective.j.pieces.push({id:p.pieceId,V:[],st:[],top:0});records.push({...r,pieceId:p.pieceId,versionId:p.pieceId+'-'+r.versionId});
  }
  const needs=(source.variorumSupplement?.sources || []).some(s=>pieces.includes(s.pieceId)) || records.length || Object.values(db.parts || {}).some(r=>r.family==='parts' && pieces.includes(r.pieceId));
  if(!needs)return effective;
  const catalog=buildVariorumCatalog({versionMap:source.j,review:source.review,reviews:db.reviews,supplement:source.variorumSupplement || {schemaVersion:1,sources:[]}});
  for(const p of catalog.pieces)for(const v of p.versions)v.exposures=[...new Map([...(v.exposures || []),...(db.release?.[p.pieceId]?.exposures || []),...Object.entries(db.versions || {}).filter(([id,x])=>id===v.versionId||x.versionId===v.versionId).flatMap(([,x])=>x.exposures || x.exposure || [])].map(e=>[canonical(e),clone(e)])).values()];
  for(const pc of effective.j.pieces){
    if(!pieces.includes(pc.id))continue;
    const head=db.parts?.['h.'+pc.id],origin=records.find(r=>r.pieceId===pc.id),parts=db.parts?.[head?.revisionId]||db.parts?.[origin?.partsRevisionId];
    if(parts)pc.variorum=clone(parts);
    for(const src of (source.variorumSupplement?.sources || []).filter(s=>s.pieceId===pc.id)){
      const imported=catalog.pieces.find(p=>p.pieceId===pc.id)?.versions.find(v=>v.versionId===src.versionId);
      if(!imported||pc.V.some(v=>v.id===src.versionId))throw new Error('invalid_supplemental_version');
      const lines=imported.lines.map((l,i)=>({lineId:src.versionId+'-L'+(i+1),text:l.text,breakBefore:l.breakBefore}));
      pc.V.push({id:src.versionId,P:[],render:'typeset',lines,_lineIdMap:Object.fromEntries(imported.lines.map((l,i)=>[l.lineId,lines[i].lineId])),text:lines.map(l=>(l.breakBefore?'\n':'')+l.text).join('\n'),
        compositeEvidence:{error:imported.available?null:'source_unavailable',verified:imported.lines.length>0&&imported.lines.every(l=>l.verified===true),sourcePieces:[src.pieceId],exposures:imported.exposures || []}});
      pc.st.push(pc.V.length-1);
    }
    for(const r of records.filter(r=>r.pieceId===pc.id)){
      const map=db.parts?.[r.partsRevisionId];let error=null,resolved;
      try{if(!map)throw new Error('parts_revision_missing');resolved=materializeComposite(catalog,map,r.recipe,r.caseMode);if(canonical(resolved.sourceSnapshots)!==canonical(r.sourceSnapshots)||resolved.text!==r.text||canonical(resolved.lines)!==canonical(r.lines))throw new Error('stale_composite_source');}catch(e){error=e.message;}
      if(!['typeset','photo'].includes(r.render))error='invalid_composite_render';
      if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(r.versionId || '')||pc.V.some(v=>v.id===r.versionId))throw new Error('invalid_composite_version');
      const lines=(r.lines || []).map((l,i)=>({lineId:r.versionId+'-L'+(i+1),text:l.text,breakBefore:l.breakBefore}));
      const photo=r.photo;
      const v={id:r.versionId,P:[],render:r.render,lines,text:r.text,compositeRevision:r.revisionId,
        compositeEvidence:{error,verified:resolved?.verified===true,sourcePieces:(r.sourceSnapshots || []).map(x=>x.pieceId),exposures:resolved?.exposures || []}};
      if(photo){v.photo={url:'img/p/'+r.versionId+'.jpg'};v.compositeEvidence.photo=clone(photo);}
      if(pc.variorum && map){
        const segments={},order=[];let offset=0;
        for(const step of r.recipe || []){const occurrence=step.occurrence,key=step.partId;const count=map.maps?.[step.from]?.segments?.[key]?.find(o=>o.occurrence===occurrence)?.lines.length || 0;
          if(!pc.variorum.parts.some(p=>p.id===key)){const part=map.parts.find(p=>p.id===key);if(part){pc.variorum.parts.push(clone(part));pc.variorum.canonicalOrder.push(key);}}
          const outputOccurrence=step.occurrence;if(segments[key]?.some(o=>o.occurrence===outputOccurrence))throw new Error('duplicate_recipe_occurrence');(segments[key] ||= []).push({occurrence:outputOccurrence,lines:lines.slice(offset,offset+count).map(l=>l.lineId),accepted:true});order.push({partId:key,occurrence:outputOccurrence});offset+=count;
        }
        pc.variorum.maps[r.versionId]={segments,version_part_order:order};
      }
      pc.V.push(v);pc.st.push(pc.V.length-1);
    }
  }
  return effective;
}
export function publicVersion(version){
  const v=clone(version);delete v.compositeEvidence;delete v.compositeRevision;delete v._lineIdMap;
  return v;
}
export function projectPublicVariorum(record,visibleVersions){
  if(!record)return undefined;
  const ids=new Set(visibleVersions.map(v=>v.id));
  const maps={};
  for(const [id,map] of Object.entries(record.maps || {}))if(ids.has(id)){
    const remap=visibleVersions.find(v=>v.id===id)?._lineIdMap || {};
    const segments={};for(const [part,occurrences]of Object.entries(map.segments || {}))segments[part]=occurrences.filter(o=>o.accepted).map(o=>({occurrence:o.occurrence,lines:o.lines.map(lid=>remap[lid] || lid)}));
    maps[id]={segments,version_part_order:(map.version_part_order || []).filter(k=>segments[k.partId]?.some(o=>o.occurrence===k.occurrence))};
  }
  const used=new Set(Object.values(maps).flatMap(m=>Object.keys(m.segments)));
  return {parts:record.parts.filter(p=>used.has(p.id)).map(p=>({id:p.id,name:p.name})),canonicalOrder:record.canonicalOrder.filter(id=>used.has(id)),maps};
}
function checkComposite(v,source,db,target){
 const e=v.compositeEvidence;if(!e)return [];
 const errors=[];if(e.error)errors.push(e.error);if(!e.verified)errors.push('unverified_composite');
 if(e.sourcePieces.some(id=>['reserve','archive'].includes(db.release[id]?.pool)))errors.push('source_pool_withheld');
 if(e.exposures.some(x=>x.type==='download') && db.release[e.sourcePieces[0]]?.pool==='reserve')errors.push('reserve_exposure');
 if(v.render==='typeset' && target!=='staging'){
  const f=source.variorumFontEvidence,points=new Set(f?.codepoints || []);
  if(f?.approved!==true||f.coversShellSha256!==source.shellSha256||typeof f.approvalRef!=='string'||!f.approvalRef||[...v.text].some(c=>!/[\s]/u.test(c)&&!points.has(c.codePointAt(0))))errors.push('composite_glyph_evidence_missing');
 }
 if(v.render==='photo' && (!e.photo || !/^[a-f0-9]{64}$/.test(e.photo.sha256 || '') || !Number.isSafeInteger(e.photo.size)))errors.push('composite_photo_evidence_missing');
 return errors;
}

// Decode common textual encodings before the byte scan. Embedded compressed
// fonts are covered by the separately decoded, pinned shell, never by this scan.
export function hasNameLeak(value) {
  let text = typeof value === 'string' ? value : new TextDecoder().decode(value);
  for (let i = 0; i < 5; i++) {
    text = text.normalize('NFKC').replace(/[\u0000-\u001f\u007f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/g, '');
    if (/etceter4/i.test(text)) return true;
    const old = text;
    text = text.replace(/\\u([a-f\d]{4})|\\x([a-f\d]{2})/gi, (_, a, b) => String.fromCodePoint(parseInt(a || b, 16)))
      .replace(/&#(x[a-f\d]+|\d+);?/gi, (m, n) => { const c = n[0].toLowerCase() === 'x' ? parseInt(n.slice(1),16) : Number(n); return c <= 0x10ffff ? String.fromCodePoint(c) : m; });
    try { text = decodeURIComponent(text); } catch { text = text.replace(/%([a-f\d]{2})/gi, (_, n) => String.fromCharCode(parseInt(n,16))); }
    if (old === text) break;
  }
  if (/etceter4/i.test(text)) return true;
  for (const m of text.matchAll(/data:[^,;]+;base64,([a-z\d+/=]+)/gi)) {
    try { if (/etceter4/i.test(atob(m[1]).replace(/\x00/g, ''))) return true; } catch { return true; }
  }
  return false;
}

// Match the Python raw_has_old_name contract on binary files: ASCII/Mac Roman,
// UTF-16BE and UTF-16LE, in any case. Unicode/escape normalization belongs to
// text files; doing it to multi-megabyte JPEG/PNG streams wastes the free CPU
// budget and adds no protection to immutable, hash-catalogued source images.
export function hasByteNameLeak(bytes) {
  const text=new TextDecoder('latin1').decode(bytes).toLowerCase();
  return text.includes('etceter4') || text.includes('e\0t\0c\0e\0t\0e\0r\u00004\0') || text.includes('\0e\0t\0c\0e\0t\0e\0r\u00004');
}

export function filterMetadata(html, metadata, pages, owners) {
  const byId = new Map(pages.map(p => [p.id, p]));
  const member = m => Array.isArray(m) && m.length === 2 && byId.has(m[0]) &&
    (() => { const bs = m[1] === 'all' ? byId.get(m[0]).B.map((_, i) => i) : m[1];
      return Array.isArray(bs) && bs.length > 0 && bs.every(b => Number.isInteger(b) && owners.has(key(m[0],b))); })();
  const pal = [];
  for (const v of metadata.PAL || []) {
    if (!object(v) || Object.keys(v).sort().join(',') !== 'id,witnesses' || !Array.isArray(v.witnesses)) throw new Error('unsupported_reader_metadata');
    const witnesses = v.witnesses.filter(w => Array.isArray(w) && w.length && w.every(member));
    if (witnesses.length >= 2) pal.push({id:v.id,witnesses});
  }
  const hf = (metadata.HF || []).filter(p => typeof p === 'string' && member([p,'all']));
  for (const [name,value] of [['PAL',pal],['HF',hf]]) {
    const re = new RegExp('\\bconst\\s+' + name + '\\s*=\\s*(\\[[\\s\\S]*?\\]);');
    if (!re.test(html) && value.length) throw new Error('missing_reader_metadata');
    html = html.replace(re, (_, literal) => 'const ' + name + ' = ' + JSON.stringify(value) + ';');
  }
  return html;
}

export function selection(pc, decisions, whole) {
  if (whole) return {indices:pc.V.map((_,i)=>i),how:'whole stack'};
  const found = new Set();
  for (const [id,doc] of Object.entries(decisions)) {
    if (!id.endsWith('-final') || typeof doc.choice !== 'string' || doc.choice === 'layers') continue;
    pc.V.forEach((v,i) => { if(doc.choice===v.id || v.P.some(([pg,bs])=>bs.some(b=>doc.choice === `${pg}-${b}`)))found.add(i); });
  }
  if (found.size > 1) throw new Error('conflicting_final_decisions');
  return {indices:found.size ? [...found] : [pc.top],how:found.size ? 'decided final' : 'top of the stack; no decided final'};
}

function facing(source, direct) {
  const mates = new Set();
  for (const pg of direct) {
    const p = source.j.pages.find(p=>p.id===pg), sp = p.sp || {};
    let found = [];
    if (sp.f) found = source.j.pages.filter(q=>q.id !== pg && ((sp.k && q.sp?.k === sp.k) || q.sp?.f === sp.f || q.id === sp.f));
    else if (Object.keys(sp).length && (sp.s === 'whole spread' || sp.cb == null)) found = source.j.pages.filter(q=>q.id !== pg && sp.k && q.sp?.k === sp.k);
    if ((sp.f || (Object.keys(sp).length && (sp.s === 'whole spread' || sp.cb == null))) && !found.length) throw new Error('unknown_facing_page');
    for(const q of found)mates.add(q.id);
    for(const q of source.twins?.[pg] || [])mates.add(q);
  }
  return [...mates].filter(p=>!direct.includes(p));
}

// Gates buildCandidate reports per piece, in order. The free-plan browser
// path (studio-cf/lib/publish-browser.js) checks the count against this list,
// and tools/release_readiness.mjs documents the same names in advice(); keep
// all three in step when a gate is added or removed.
export const GATE_NAMES = ['series', 'verified', 'filed', 'alt_text', 'note_anchors', 'links'];
// alt text on every published page image, note anchors resolving to a real
// line, and links validating. They run here, per piece, on the chosen
// versions only, so a piece blocked on another gate still reports them.
function extraGates({pid, pc, sel, pages, db, shell}) {
  const out = [];
  // alt_text: the reader renders each page image as <img alt="Page <label>">
  // with label = page id minus a leading 'diary' (site/index.html). No stored
  // alt text exists in the tree, so the gate guards the derivation: it fails
  // when the prepared shell has no such alt template (a reader change dropped
  // alt attributes) or when a selected page yields a blank label.
  const direct = unique(sel.indices.flatMap(i => pc.V[i].P.map(([pg]) => pg)));
  const altOk = typeof shell === 'string' && shell.includes('alt="Page');
  const blank = direct.filter(pg => pg.replace(/^diary/, '') === '');
  out.push({name: 'alt_text', ok: altOk && !blank.length,
    detail: !altOk ? 'reader shell has no page-image alt template'
      : blank.length ? `blank alt label for ${blank.join(', ')}` : `${direct.length} page image(s)`});
  // note_anchors: every note anchor for this piece must name a version of the
  // piece and a line of that version. Docs without an anchor are not anchors
  // and are skipped; when the export has no notes collection there is nothing
  // to check and the gate passes with that detail (never a silent pass: the
  // detail says what was checked).
  const notes = db.notes && typeof db.notes === 'object' ? Object.values(db.notes) : [];
  const anchors = [];
  for (const doc of notes) {
    if (!doc || typeof doc !== 'object') continue;
    const a = doc.anchor;
    if (!a || typeof a !== 'object') continue;
    if ((a.pieceId ?? doc.pieceId) !== pid) continue;
    anchors.push(a);
  }
  const lineIds = new Map(); // versionId -> Set(lineId)
  for (const vi of sel.indices) {
    const ids = new Set();
    for (const [pg, bs] of pc.V[vi].P) {
      const p = pages.get(pg);
      if (!p) continue;
      for (const bi of bs) for (let li = 0; li < (p.B[bi]?.L?.length ?? 0); li++) ids.add(`${pg}-${bi}-${li}`);
    }
    lineIds.set(pc.V[vi].id, ids);
  }
  const badAnchors = anchors.filter(a => {
    if (!lineIds.has(a.versionId)) return true;
    return a.lineId != null && !lineIds.get(a.versionId).has(a.lineId);
  });
  out.push({name: 'note_anchors', ok: !badAnchors.length,
    detail: anchors.length ? `${anchors.length} anchor(s) checked${badAnchors.length ? `; unresolvable: ${badAnchors.slice(0, 3).map(a => a.lineId ?? a.versionId).join(', ')}` : ''}` : 'no note anchors to check'});
  // links: every http(s) URL in the published text (corrected lines) and in
  // this piece's note docs must be a well-formed absolute URL. Today the tree
  // carries no links in piece text, so the gate passes with '0 links' and
  // guards the day a note carries one.
  const urls = [];
  const scan = text => { if (typeof text !== 'string') return; for (const m of text.matchAll(/https?:\/\/[^\s"'<>`]+/g)) urls.push(m[0]); };
  for (const vi of sel.indices) for (const [pg, bs] of pc.V[vi].P) {
    const p = pages.get(pg);
    if (!p) continue;
    for (const bi of bs) (p.B[bi]?.L ?? []).forEach((text, li) => {
      const lid = `${pg}-${bi}-${li}`, review = db.reviews[lid];
      scan(review?.status === 'corrected' && typeof review.text === 'string' ? review.text : text);
    });
  }
  for (const doc of notes) {
    if (!doc || typeof doc !== 'object') continue;
    const a = doc.anchor;
    if (a && typeof a === 'object' && (a.pieceId ?? doc.pieceId) === pid) scan(JSON.stringify(doc));
  }
  const badUrls = urls.filter(u => { try { const x = new URL(u); return (x.protocol !== 'http:' && x.protocol !== 'https:') || !x.hostname; } catch { return true; } });
  out.push({name: 'links', ok: !badUrls.length,
    detail: urls.length ? `${urls.length} link(s)${badUrls.length ? `; invalid: ${badUrls.slice(0, 3).join(', ')}` : ', all valid'}` : '0 links'});
  return out;
}

// A stopped candidate returns diagnostic IDs and gate results but no files or
// public data. This prevents an accidental preview route bypassing the stops.
export async function buildCandidate({source,db,shell,pieces=[],allVersions=[],accepted=[],force=false,publicPieces=pieces,target='production'}) {
  const gates=[],stops=[],shared=[],warnings=[],versions={};
  const result = () => ({gates,stops,shared,warnings,versions,blocked:stops.length > 0 || gates.some(g=>!g.ok && !g.overridden),files:[],data:null});
  const stop = (piece,name) => stops.push({piece,name,ok:false});
  const gate = (piece,name,ok,detail='') => gates.push({piece,name,ok,detail,overridden:!ok && force === true});
  try {
    if (!source || !object(db) || !object(source.j) || !object(source.review) || !Array.isArray(pieces) || !Array.isArray(allVersions) || !Array.isArray(accepted)) throw new Error('invalid_inputs');
    for (const c of ['release','reviews','batches','decisions','versions','rconfig']) {
      if (!object(db[c])) throw new Error('invalid_collection_'+c);
      if (Object.values(db[c]).some(d=>!object(d))) throw new Error('malformed_document_'+c);
    }
    if (db.notes !== undefined && !object(db.notes)) throw new Error('invalid_collection_notes');
    source=assembleEffectiveSource(source,db,{pieces});
    const pcs = new Map(source.j.pieces.map(p=>[p.id,p]));
    const pages = new Map(source.j.pages.map(p=>[p.id,p]));
    const rpages = new Map(source.review.pages.map(p=>[p.id,p]));
    for (const id of Object.keys(db.release)) if (!/^p[0-9]+$/.test(id) || !pcs.has(id)) throw new Error('invalid_release_id');
    const want = unique(pieces);
    if (want.some(id=>typeof id !== 'string' || !pcs.has(id))) throw new Error('unknown_piece');
    const owners = new Map(), chosen = new Map(), corrections = new Map();
    for (const [pi,pid] of want.entries()) {
      const pc=pcs.get(pid), rel=db.release[pid];
      const pool=rel?.pool;
      if (rel && pool !== 'series') stop(pid,'own_pool_not_series');
      gate(pid,'series',pool === 'series');
      const item=source.review.items.find(i=>i.id===pid);
      const lids = item ? unique(item.versions.flatMap(v=>v.blocks.flatMap(b=>rpages.get(v.page).blocks[b].lines.map(l=>l.id)))) : null;
      const bad = lids?.filter(l=>!(db.reviews[l]?.status === 'confirmed' || (db.reviews[l]?.status === 'corrected' && typeof db.reviews[l]?.text === 'string')));
      const sel=selection(pc,db.decisions,allVersions.includes(pid));
      const onlyDerived=sel.indices.length>0&&sel.indices.every(i=>pc.V[i]?.compositeEvidence);
      gate(pid,'verified',onlyDerived ? sel.indices.every(i=>pc.V[i].compositeEvidence.verified) : lids !== null && !bad.length, onlyDerived?'derived source verification':bad?.length ? `${bad.length} unverified line(s)` : '');
      gate(pid,'filed',db.decisions['gruw-policy']?.choice === 'skip' || Object.values(db.batches).some(b=>Array.isArray(b.items) && b.items.includes(pid) && ['filed','registered'].includes(b.status)));
      if (!sel.indices.length || sel.indices.some(i=>!Number.isInteger(i) || !pc.V[i] || !pc.st.includes(i))) throw new Error('invalid_version_selection');
      chosen.set(pid,sel.indices); versions[pid]={...sel,total:pc.V.length,newest:pc.V.length-1,top:pc.top,unpublishedCorrected:0};
      for (const g of extraGates({pid, pc, sel, pages, db, shell})) gate(pid, g.name, g.ok, g.detail);
      const newv = new Map(sel.indices.map((i,n)=>[i,n]));
      const st=pc.st.filter(i=>newv.has(i)).map(i=>newv.get(i));
      for (const vi of sel.indices) {
        const v=pc.V[vi];
        for(const issue of checkComposite(v,source,db,target))stop(pid,issue);
        if(v.sourceStatus === 'staged-untranscribed')throw new Error('untranscribed_version');
        for(const [pg,bs] of v.P) {
          const p=pages.get(pg);
          if (!p || p.sourceStatus === 'staged-untranscribed' || !Array.isArray(p.a) || p.a.length !== 5) throw new Error('untranscribed_source');
          for(const bi of bs) {
            const b=p.B[bi];
            if (!b || b.transcriptionStatus === 'untranscribed')throw new Error('untranscribed_block');
            owners.set(key(pg,bi),[pi,newv.get(vi),st.indexOf(newv.get(vi))]);
            if(b.t === 4)continue;
            b.L.forEach((text,li)=>{
              const lid=`${pg}-${bi}-${li}`, review=db.reviews[lid];
              if (review && review.original !== text)stop(pid,'stale_transcript:'+lid);
              if(review?.status === 'corrected' && typeof review.text === 'string') corrections.set(lid,review.text);
            });
          }
        }
      }
      const unseen=new Set();
      pc.V.forEach((v,vi)=>{if(!sel.indices.includes(vi)) for(const [pg,bs] of v.P)for(const bi of bs)if(!owners.has(key(pg,bi))) pages.get(pg).B[bi].L.forEach((_,li)=>{const lid=`${pg}-${bi}-${li}`;if(db.reviews[lid]?.status==='corrected' && typeof db.reviews[lid]?.text==='string')unseen.add(lid);});});
      versions[pid].unpublishedCorrected=unseen.size;
      if(unseen.size)warnings.push(`${pid}: ${unseen.size} correction(s) on unpublished versions`);
      if(Object.values(db.versions).some(v=>v.pieceId===pid)) warnings.push(`${pid}: studio photo version not in the source`);
    }
    for (const pid of want) {
      const direct=unique(chosen.get(pid).flatMap(i=>pcs.get(pid).V[i].P.map(([pg])=>pg))), mates=facing(source,direct), visible=new Set([...direct,...mates]),seen=new Set();
      for (const pc of source.j.pieces) {
        const on=unique(pc.V.flatMap(v=>v.P.map(([pg])=>pg))).filter(pg=>visible.has(pg));
        if(pc.id === pid){for(const pg of on)if(mates.includes(pg))seen.add(pg);continue;}
        for (const pg of on) {
          seen.add(pg);
          const pool=db.release[pc.id]?.pool;
          const status=publicPieces.includes(pc.id) ? 'ok' : pool === 'series' ? accepted.includes(pc.id) ? 'accepted' : 'needs-accept' : 'stop';
          shared.push({piece:pid,id:pc.id,page:pg,status,facing:mates.includes(pg)});
          if(status === 'stop' || status === 'needs-accept')stop(pid,'shared_scan:'+pc.id);
        }
      }
      for(const item of source.review.items)if(!pcs.has(item.id)) for(const v of item.versions)if(visible.has(v.page)) {
        seen.add(v.page);const status=accepted.includes(item.id)?'accepted':'needs-accept';
        shared.push({piece:pid,id:item.id,page:v.page,status,facing:mates.includes(v.page)});
        if(status==='needs-accept')stop(pid,'shared_scan:'+item.id);
      }
      for(const pg of mates)if(!seen.has(pg)) {
        const status=accepted.includes(pg)?'accepted':'needs-accept';shared.push({piece:pid,id:pg,page:pg,status,facing:true});
        if(status==='needs-accept')stop(pid,'shared_scan:'+pg);
      }
    }
    if(result().blocked)return result();
    const selectedPages=source.j.pages.filter(p=>[...owners.keys()].some(k=>k.startsWith(p.id+'/')));
    const outPieces=want.map(pid=>{const pc=pcs.get(pid),sel=chosen.get(pid),nv=new Map(sel.map((v,i)=>[v,i])),st=pc.st.filter(i=>nv.has(i)).map(i=>nv.get(i));const out={...clone(pc),V:sel.map(i=>publicVersion(pc.V[i])),st,top:nv.has(pc.top)?nv.get(pc.top):st[0]};delete out.variorum;const spread=projectPublicVariorum(pc.variorum,sel.map(i=>pc.V[i]));if(spread)out.variorum=spread;return out;});
    const outPages=[],atlas=[],files=[],bindings={},selectedLineIds=new Set();
    const addAsset=(path,sourcePath=path)=>{const a=source.assets[sourcePath];if(!a || !/^[a-f0-9]{64}$/.test(a.sha256))throw new Error('missing_asset:'+path);files.push({path,sourcePath,...a});};
    for(const [n,original] of selectedPages.entries()) {
      const p=clone(original),tile=source.tiles[p.id];
      if(!tile || tile.size[0] !== p.a[3] || tile.size[1] !== p.a[4])throw new Error('missing_atlas_tile');
      p.a=[n,0,0,...tile.size];atlas.push(tile.size);
      for(const k of ['t','k'])addAsset(`img/a/${k}${n}.jpg`,tile.files[k]);
      p.B.forEach((b,bi)=>{
        const own=owners.get(key(p.id,bi));
        if(!own){b.L=[];for(const k of ['g','v','u','lineIds','transcriptionStatus','sourceAnchor'])delete b[k];return;}
        if(b.g)b.g=[own[0],own[2],...b.g.slice(2)];if('v' in b)b.v=own[1];
        b.L=b.L.map((text,li)=>{const lid=`${p.id}-${bi}-${li}`,explicit=b.lineIds?.[li] || lid;selectedLineIds.add(explicit);return b.t === 4 ? text : corrections.get(lid) ?? source.j.acceptedReadings?.[explicit] ?? text;});
      });
      p.u=[];p.x=(p.x || []).filter(e=>owners.has(key(p.id,e[0])));outPages.push(p);
      for(const k of ['p','i','m'])addAsset(`img/${k}/${p.id}.jpg`);
      if(p.sp?.f)addAsset(`img/s/${p.sp.f}.jpg`);
      if(source.assets[`img/h/${p.id}.jpg`])addAsset(`img/h/${p.id}.jpg`);
    }
    for (const pid of want) for(const vi of chosen.get(pid)) {
      const v=pcs.get(pid).V[vi],lines=[];
      if(v.render){
        if(v.render==='photo'){const photo=v.compositeEvidence.photo;const path='img/p/'+v.id+'.jpg';files.push({path,sourcePath:'photos/'+photo.assetId,sha256:photo.sha256,size:photo.size,contentType:photo.contentType});}
        bindings[`${pid}/${v.id}`]={pieceId:pid,versionId:v.id,sourceFingerprint:'sha256:'+await digest(canonical(logicalSourcePayload({pieceId:pid,versionId:v.id,members:[],lines:v.lines.map(l=>({...l,blockType:'text'}))})))};continue;
      }
      for(const [pg,bs] of v.P)for(const bi of bs) {
        const b=rpages.get(pg)?.blocks[bi],out=outPages.find(p=>p.id===pg).B[bi];
        if(!b || b.lines.length !== out.L.length)throw new Error('review_source_mismatch');
        for(const [li,l] of b.lines.entries()) {
          if(l.transcriptionStatus === 'untranscribed' || (b.t !== 'quotation' && l.tx !== pages.get(pg).B[bi].L[li]))throw new Error('review_source_mismatch');
          lines.push({lineId:l.id,text:b.t === 'quotation'?l.tx:out.L[li],blockType:b.t || 'text',breakBefore:l.breakBefore ?? (lines.length>0 && li===0)});
        }
      }
      if(!lines.length || unique(lines.map(l=>l.lineId)).length !== lines.length)throw new Error('invalid_source_lines');
      bindings[`${pid}/${v.id}`]={pieceId:pid,versionId:v.id,sourceFingerprint:'sha256:'+await digest(canonical(logicalSourcePayload({pieceId:pid,versionId:v.id,members:v.P,lines})))};
    }
    const ids=new Set(outPages.map(p=>p.id));
    const data={v:source.j.v,pages:outPages,groups:source.j.groups.map(g=>g.filter(p=>ids.has(p))).filter(g=>g.length),atlas,pieces:outPieces,prov:Object.fromEntries(Object.entries(source.j.prov).filter(([k])=>['tdate','verified'].includes(k)))};
    if(Object.keys(bindings).length)data.sourceBindings=bindings;
    const unavailable=Object.fromEntries(Object.entries(source.j.sourceAnchors || {}).filter(([id,a])=>selectedLineIds.has(id) && a.status==='unavailable').map(([id])=>[id,{status:'unavailable'}]));
    if(Object.keys(unavailable).length)data.sourceAnchors=unavailable;
    const html=want.length ? filterMetadata(shell,source.metadata || {},source.j.pages,owners) : BLANK;
    files.push({path:'index.html',text:html,contentType:'text/html; charset=utf-8'});
    if(want.length){files.push({path:'data/j.json',text:JSON.stringify(data),contentType:'application/json; charset=utf-8'});for(const a of ['reader-features.js','reader-packages.js'])if(source.assets[a])addAsset(a);}
    const dedup=[...new Map(files.map(f=>[f.path,f])).values()].sort((a,b)=>a.path.localeCompare(b.path));
    for(const f of dedup)if(f.text !== undefined){f.sha256=await digest(f.text);f.size=encode(f.text).length;if(hasNameLeak(f.text))stop('', 'name_leak');}
    if(!/<title>versforms<\/title>/.test(html) || !/<meta[^>]+name=["']?robots["']?[^>]+noindex/i.test(html))stop('','invalid_shell');
    if(result().blocked)return result();
    return {...result(),data,files:dedup,sourceDependencies:unique(want.flatMap(pid=>chosen.get(pid).flatMap(vi=>pcs.get(pid).V[vi].compositeEvidence?.sourcePieces || []))).sort(),published:[...owners.keys()],pieces:want,allVersions:allVersions.filter(p=>want.includes(p)),readerStrings:{title:'versforms',font:'ajp-scribbles',fontRecords:source.fontRecords || [],reviewStatus:'omitted',info:data.prov}};
  } catch(e) {stop('',e.message || 'invalid_source');return result();}
}
