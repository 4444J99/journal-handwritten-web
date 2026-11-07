// Pure publication compiler. No credentials, network access, storage or git.
// The Python posting path remains the reference; atlas tiles are prepared offline.
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
    pc.V.forEach((v,i) => { if(v.P.some(([pg,bs])=>bs.some(b=>doc.choice === `${pg}-${b}`)))found.add(i); });
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

// A stopped candidate returns diagnostic IDs and gate results but no files or
// public data. This prevents an accidental preview route bypassing the stops.
export async function buildCandidate({source,db,shell,pieces=[],allVersions=[],accepted=[],force=false,publicPieces=pieces}) {
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
      gate(pid,'verified',lids !== null && !bad.length, bad?.length ? `${bad.length} unverified line(s)` : '');
      gate(pid,'filed',db.decisions['gruw-policy']?.choice === 'skip' || Object.values(db.batches).some(b=>Array.isArray(b.items) && b.items.includes(pid) && ['filed','registered'].includes(b.status)));
      const sel=selection(pc,db.decisions,allVersions.includes(pid));
      if (!sel.indices.length || sel.indices.some(i=>!Number.isInteger(i) || !pc.V[i] || !pc.st.includes(i))) throw new Error('invalid_version_selection');
      chosen.set(pid,sel.indices); versions[pid]={...sel,total:pc.V.length,newest:pc.V.length-1,top:pc.top,unpublishedCorrected:0};
      const newv = new Map(sel.indices.map((i,n)=>[i,n]));
      const st=pc.st.filter(i=>newv.has(i)).map(i=>newv.get(i));
      for (const vi of sel.indices) {
        const v=pc.V[vi];
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
    const outPieces=want.map(pid=>{const pc=pcs.get(pid),sel=chosen.get(pid),nv=new Map(sel.map((v,i)=>[v,i])),st=pc.st.filter(i=>nv.has(i)).map(i=>nv.get(i));return {...clone(pc),V:sel.map(i=>clone(pc.V[i])),st,top:nv.has(pc.top)?nv.get(pc.top):st[0]};});
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
    return {...result(),data,files:dedup,published:[...owners.keys()],pieces:want,allVersions:allVersions.filter(p=>want.includes(p)),readerStrings:{title:'versforms',font:'ajp-scribbles',fontRecords:source.fontRecords || [],reviewStatus:'omitted',info:data.prov}};
  } catch(e) {stop('',e.message || 'invalid_source');return result();}
}
