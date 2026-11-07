// Free-plan path: the browser compiles the whole candidate. Each request here
// independently checks ONE piece or page against a pinned private source slice.
// Untrusted browser output never advances the public pointer by itself.
import {buildCandidate,selection,filterMetadata,canonical,digest,encode,BLANK,assembleEffectiveSource,publicVersion,projectPublicVariorum} from './publish.js';
import {json} from './api.js';
import {revisionStatement,revisionValues} from './publish-fence.js';
import {target,pointer,condition,immutable,candidate,progress,setProgress,summary,bytesOf,checked,recoverCurrent,movePointer,publicManifest,fail,check,fileKey,stateKey,draftKey,doc,wasPublished} from './publish-api.js';

const COLLECTIONS=['reviews','decisions','versions','release','batches','rconfig','parts','composites'];
const ID=/^[a-f0-9]{64}$/;
const STUB='<!doctype html><html><head><title>versforms</title><meta name="robots" content="noindex"></head><body><script>const PAL = []; const HF = [];</script></body></html>';
const object=x=>x!==null && typeof x==='object' && !Array.isArray(x);
async function staticText(env,path,limit=4*1024*1024) {
  const r=await env.ASSETS.fetch(new Request('https://studio.invalid/publish/'+(path==='shell.html'?'shell':path)));
  if(!r.ok)fail(503,'prepared_assets_missing');
  const text=await r.text();if(encode(text).length>limit)fail(503,'prepared_asset_too_large');
  return text;
}
async function pin(env) {
  const p=JSON.parse(await staticText(env,'pin.json',1024));
  if(!ID.test(env.PUBLISH_SHELL_SHA256 || '') || p.shellSha256!==env.PUBLISH_SHELL_SHA256 || !ID.test(p.sourceSha256) || !ID.test(p.catalogSha256))fail(503,'shell_pin_mismatch');
  return p;
}
async function revisions(env) {
  const rows=await env.DB.prepare('SELECT collection, rev FROM vf_revs WHERE collection IN (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) ORDER BY collection').bind(...COLLECTIONS).all();
  return Object.fromEntries(COLLECTIONS.map(c=>[c,rows.results.find(r=>r.collection===c)?.rev || 0]));
}
export async function assertFresh(env,c) {
  const [p,revs]=await Promise.all([pin(env),revisions(env)]);
  check(p.sourceSha256===c.sourceHash && p.catalogSha256===c.catalogHash && p.shellSha256===c.shellSha256 && canonical(revs)===canonical(c.revisions),'source_changed_rebuild');
}

export async function browserContext(env,user,name) {
  const {bucket}=target(env,name);await recoverCurrent(env,bucket);
  const p=await pin(env),base=(await pointer(bucket)).value;
  const results=await env.DB.batch([
    ...COLLECTIONS.map(c=>env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(c)),
    env.DB.prepare('SELECT collection, rev FROM vf_revs WHERE collection IN (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) ORDER BY collection').bind(...COLLECTIONS),
  ]);
  const revs=Object.fromEntries(COLLECTIONS.map(c=>[c,results[COLLECTIONS.length].results.find(r=>r.collection===c)?.rev || 0]));
  const db=Object.fromEntries(COLLECTIONS.map((c,i)=>[c,Object.fromEntries(results[i].results.map(r=>[r.id,JSON.parse(r.data)]))]));
  const id=await digest(crypto.randomUUID()),context={id,owner:user.email,target:name,base,revisions:revs,sourceHash:p.sourceSha256,catalogHash:p.catalogSha256,shellSha256:p.shellSha256,createdAt:new Date().toISOString()};
  await immutable(env.PHOTOS,`contexts/${id}.json`,JSON.stringify(context));
  const current=base?.id ? await doc(env,'snapshot.'+base.id) : null;
  return json({id,mode:'browser',db,sourceUrl:'/publish/source.json',shellUrl:'/publish/shell',sourceHash:p.sourceSha256,shellSha256:p.shellSha256,base,current});
}

function selectedPiece(pc,decisions,whole) {
  const {indices,how}=selection(pc,decisions,whole),nv=new Map(indices.map((vi,i)=>[vi,i]));
  check(indices.length>0 && indices.every(i=>Number.isInteger(i) && pc.V[i] && pc.st.includes(i)),'invalid_version_selection');
  const st=pc.st.filter(i=>nv.has(i)).map(i=>nv.get(i));
  const piece={...pc,V:indices.map(i=>publicVersion(pc.V[i])),st,top:nv.has(pc.top)?nv.get(pc.top):st[0]};delete piece.variorum;const spread=projectPublicVariorum(pc.variorum,indices.map(i=>pc.V[i]));if(spread)piece.variorum=spread;return {piece,indices,how};
}
function ownersOf(c) {
  const owners=new Map();
  c.selectedPieces.forEach((p,pi)=>p.V.forEach((v,vi)=>{for(const [pg,bs]of v.P)for(const b of bs)owners.set(`${pg}/${b}`,[pi,vi,p.st.indexOf(vi)]);}));
  return owners;
}
async function trustedFragment(env,c,path) {
  const text=await staticText(env,path);
  check(c.fragmentHashes[path] && await digest(text)===c.fragmentHashes[path],'source_fragment_changed');
  return JSON.parse(text);
}
async function pieceDb(env,source,pid) {
  const item=source.review.items.find(i=>i.id===pid),rpages=new Map(source.review.pages.map(p=>[p.id,p]));
  const ids=[...new Set(item?item.versions.flatMap(v=>v.blocks.flatMap(b=>rpages.get(v.page).blocks[b].lines.map(l=>l.id))):[])];
  // Corrections on selected blocks use the original posting script's IDs.
  for(const p of source.j.pages)if(p.a)for(const [bi,b]of p.B.entries())for(let li=0;li<(b.L || []).length;li++)ids.push(`${p.id}-${bi}-${li}`);
  const revIds=[...new Set(ids)],statements=[];
  for(let i=0;i<revIds.length;i+=80) {
    const chunk=revIds.slice(i,i+80),marks=chunk.map((_,n)=>'?'+(n+2)).join(',');
    statements.push(env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 AND id IN ('+marks+')').bind('reviews',...chunk));
  }
  const others=COLLECTIONS.filter(c=>c!=='reviews');
  const rows=await env.DB.batch([...statements,...others.map(c=>env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(c))]);
  return {reviews:Object.fromEntries(rows.slice(0,statements.length).flatMap(r=>r.results.map(r=>[r.id,JSON.parse(r.data)]))),
    ...Object.fromEntries(others.map((c,i)=>[c,Object.fromEntries(rows[statements.length+i].results.map(r=>[r.id,JSON.parse(r.data)]))]))};
}

async function capturedDb(env){
 const rows=await env.DB.batch(COLLECTIONS.map(c=>env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind(c)));
 return Object.fromEntries(COLLECTIONS.map((c,i)=>[c,Object.fromEntries(rows[i].results.map(r=>[r.id,JSON.parse(r.data)]))]));
}
async function hydratedPiece(env,hashes,pid,db){
 const promotion=Object.values(db.composites || {}).find(r=>r.family==='promotion'&&r.pieceId===pid),origin=promotion&&db.composites[promotion.originComposite?.revisionId];
 const dependencies=new Set([origin?.pieceId || pid]);
 for(const r of Object.values(db.composites || {}))if(r.family==='composite'&&(r.pieceId===pid||r===origin))for(const x of r.sourceSnapshots || [])dependencies.add(x.pieceId);
 for(const r of Object.values(db.parts || {}))if(r.family==='parts'&&r.pieceId===pid)for(const id of r.linkedPieces || [])dependencies.add(id);
 check(dependencies.size<=200,'source_dependency_limit');
 const fragments=[];
 for(const id of dependencies){check(/^p[0-9]+$/.test(id),'invalid_source_dependency');const path=`pieces/${id}.json`,text=await staticText(env,path);check(hashes[path]&&await digest(text)===hashes[path],'source_fragment_changed');fragments.push(JSON.parse(text));}
 const source=fragments[0],pages=new Map(source.j.pages.map(p=>[p.id,p])),reviewPages=new Map();
 for(const f of fragments){for(const p of f.review.pages)reviewPages.set(p.id,p);for(const p of f.j.pages)if(p.B?.some(b=>Array.isArray(b.L)))pages.set(p.id,p);}
 // Prepared accepted readings and anchors are partitioned with page text. A
 // linked source needs the same authoritative inputs as the full source path.
 for(const field of ['acceptedReadings','sourceAnchors'])if(fragments.some(f=>f.j[field]))source.j[field]=Object.assign({},...fragments.map(f=>f.j[field] || {}));
 if(fragments.some(f=>f.review.acceptedReviews))source.review.acceptedReviews=Object.assign({},...fragments.map(f=>f.review.acceptedReviews || {}));
 source.j.pages=source.j.pages.map(p=>pages.get(p.id));source.review.pages=[...reviewPages.values()];
 return {source,paths:[...dependencies].map(id=>`pieces/${id}.json`)};
}

export async function proposeBrowser(env,user,body) {
  check(ID.test(body.context || ''),'invalid_context');
  const obj=await env.PHOTOS.get(`contexts/${body.context}.json`);if(!obj)fail(404,'context_not_found');
  const ctx=await obj.json();check(ctx.owner===user.email,'candidate_owner_mismatch');
  check(Date.now()-Date.parse(ctx.createdAt)<60*60*1000,'context_expired');await assertFresh(env,ctx);
  const {bucket}=target(env,ctx.target);check(canonical((await pointer(bucket)).value)===canonical(ctx.base),'current_snapshot_changed');
  check(Array.isArray(body.pieces) && body.pieces.length<=200 && new Set(body.pieces).size===body.pieces.length,'invalid_pieces');
  check(Array.isArray(body.allVersions) && body.allVersions.every(p=>body.pieces.includes(p)) && Array.isArray(body.accepted) && body.accepted.every(id=>typeof id==='string'),'invalid_options');
  const text=await staticText(env,'catalog.json');check(await digest(text)===ctx.catalogHash,'source_catalog_changed');
  const cat=JSON.parse(text),byId=new Map(cat.pieces.map(p=>[p.id,p]));
  const db=await capturedDb(env),dependencyPaths=new Set();
  for(const pid of body.pieces){{const h=await hydratedPiece(env,cat.fragments,pid,db);h.paths.forEach(p=>dependencyPaths.add(p));const effective=assembleEffectiveSource(h.source,db,{pieces:[pid]});byId.set(pid,effective.j.pieces.find(p=>p.id===pid));}}
  check(body.pieces.every(p=>byId.has(p)),'unknown_piece');
  const decisionRows=await env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind('decisions').all();
  const decisions=Object.fromEntries(decisionRows.results.map(r=>[r.id,JSON.parse(r.data)]));
  const selected=body.pieces.map(pid=>selectedPiece(byId.get(pid),decisions,body.allVersions.includes(pid)));
  const selectedPieces=selected.map(v=>v.piece),owner=ownersOf({selectedPieces});
  const usedPages=new Set([...owner.keys()].map(k=>k.split('/')[0]));
  const pageOrder=cat.pageOrder.filter(p=>usedPages.has(p));
  const expected=[];
  function asset(path,sourcePath=path) {const a=cat.assets[sourcePath];check(a && ID.test(a.sha256),'source_asset_missing');expected.push({path,sourcePath,...a});}
  for(const [n,pg]of pageOrder.entries()) {
    check(cat.tiles[pg],'missing_atlas_tile');
    for(const kind of ['t','k'])asset(`img/a/${kind}${n}.jpg`,cat.tiles[pg].files[kind]);
    for(const kind of ['p','i','m'])asset(`img/${kind}/${pg}.jpg`);
    if(cat.assets[`img/h/${pg}.jpg`])asset(`img/h/${pg}.jpg`);
  }
  for(const p of selectedPieces)for(const v of p.V)for(const [pg]of v.P) {
    // Spread files are derived from the trusted per-piece source on verification,
    // but their complete path set is prepared in the catalogue below.
    for(const path of cat.spreadAssets?.[pg] || [])asset(path);
  }
  for(const x of selected)for(const vi of x.indices){const v=byId.get(x.piece.id).V[vi],photo=v.compositeEvidence?.photo;if(v.render==='photo'){check(photo&&ID.test(photo.sha256),'composite_photo_evidence_missing');expected.push({path:`img/p/${v.id}.jpg`,sourcePath:'photos/'+photo.assetId,sha256:photo.sha256,size:photo.size,contentType:photo.contentType});}}
  if(body.pieces.length)for(const path of ['reader-features.js','reader-packages.js'])if(cat.assets[path])asset(path);
  check(Array.isArray(body.files) && body.files.length<=1000 && body.files.every(f=>object(f)),'invalid_file_list');
  for(const path of body.pieces.length?['index.html','data/j.json']:['index.html']) {
    const f=body.files.find(f=>f.path===path),type=path==='index.html'?'text/html; charset=utf-8':'application/json; charset=utf-8';
    check(f && ID.test(f.sha256) && Number.isSafeInteger(f.size) && f.size>0 && f.size<=512*1024 && f.contentType===type && !f.sourcePath,'invalid_generated_file');
    expected.push({path,sha256:f.sha256,size:f.size,contentType:type});
  }
  const files=[...new Map(expected.map(f=>[f.path,f])).values()].sort((a,b)=>a.path.localeCompare(b.path));
  check(canonical(files)===canonical(body.files),'unapproved_file_list');
  const selectedLines=new Set([...owner.keys()].flatMap(k=>cat.lineIdsByBlock[k] || []));
  const anchors=Object.fromEntries(Object.entries(cat.sourceAnchors || {}).filter(([id])=>selectedLines.has(id)));
  const bindingKeys=selectedPieces.flatMap(p=>p.V.map(v=>`${p.id}/${v.id}`));
  const fragmentPaths=[...new Set([...dependencyPaths,...pageOrder.map(p=>`pages/${p}.json`)])];
  const c={mode:'browser',target:ctx.target,base:ctx.base,owner:user.email,createdAt:new Date().toISOString(),nonce:crypto.randomUUID(),
    sourceHash:ctx.sourceHash,catalogHash:ctx.catalogHash,shellSha256:ctx.shellSha256,revisions:ctx.revisions,
    pieces:body.pieces,allVersions:body.allVersions,accepted:body.accepted,force:body.force===true,files,
    gates:body.gates || [],stops:[],shared:body.shared || [],warnings:body.warnings || [],versions:body.versions || {},
    sourceDependencies:[...new Set(selected.flatMap(x=>x.indices.flatMap(vi=>byId.get(x.piece.id).V[vi].compositeEvidence?.sourcePieces || [])))].sort(),
    selectedPieces,pageOrder,metadata:cat.metadata,sharedPieceIds:[...new Set((body.shared || []).filter(s=>byId.has(s.id)).map(s=>s.id))],
    pageBlockCounts:Object.fromEntries(cat.pageOrder.map(pg=>[pg,Object.keys(cat.lineIdsByBlock).filter(k=>k.startsWith(pg+'/')).length])),
    fragmentHashes:Object.fromEntries(fragmentPaths.map(p=>[p,cat.fragments[p]])),
    header:{v:cat.v,groups:cat.groups.map(g=>g.filter(p=>usedPages.has(p))).filter(g=>g.length),atlas:pageOrder.map(p=>cat.tiles[p].size),prov:cat.prov,bindingKeys,anchors},
    readerStrings:{title:'versforms',font:'ajp-scribbles',fontRecords:cat.fontRecords || [],reviewStatus:'omitted',info:cat.prov}};
  const id=await digest(canonical(c));
  await immutable(env.PHOTOS,draftKey(id),canonical(c));
  await immutable(env.PHOTOS,stateKey(id),JSON.stringify({phase:'verify',cursor:0}));
  return json(summary(id,c));
}

export async function uploadData(env,user,body) {
  const c=await candidate(env,user,body.id,body.hash),p=await progress(env,body.id);
  check(c.mode==='browser' && p.value.phase==='verify' && p.value.cursor===0,'upload_already_closed');
  const file=c.files.find(f=>f.path==='data/j.json');
  if(!file){check(body.text===undefined || body.text==='','unexpected_data_file');return json({ok:true});}
  check(typeof body.text==='string','data_file_required');
  const bytes=encode(body.text);await checked(bytes,file);
  try{JSON.parse(body.text);}catch{fail(400,'invalid_data_json');}
  await immutable(env.PHOTOS,fileKey(body.id,file.path),bytes,{httpMetadata:{contentType:file.contentType},customMetadata:{sha256:file.sha256}});
  return json({ok:true});
}

async function storedData(env,id,c) {
  if(!c.pieces.length)return null;
  const file=c.files.find(f=>f.path==='data/j.json'),obj=await env.PHOTOS.get(fileKey(id,file.path));
  if(!obj)fail(409,'data_upload_required');
  check(obj.size===file.size,'data_file_size_mismatch');
  return obj.json();
}
function compareHeader(c,data) {
  if(!c.pieces.length){check(data===null && c.files.length===1,'empty_snapshot_has_assets');return;}
  const expectedKeys=['v','pages','groups','atlas','pieces','prov'];
  if(c.header.bindingKeys.length)expectedKeys.push('sourceBindings');
  if(Object.keys(c.header.anchors).length)expectedKeys.push('sourceAnchors');
  check(object(data) && canonical(Object.keys(data).sort())===canonical(expectedKeys.sort()),'unapproved_data_fields');
  check(canonical(data.pages.map(p=>p.id))===canonical(c.pageOrder) && canonical(data.pieces.map(p=>p.id))===canonical(c.pieces),'output_membership_mismatch');
  for(const k of ['v','groups','atlas','prov'])check(canonical(data[k])===canonical(c.header[k]),'output_header_mismatch');
  check(canonical(Object.keys(data.sourceBindings || {}).sort())===canonical([...c.header.bindingKeys].sort()),'source_binding_keys_mismatch');
  check(canonical(data.sourceAnchors || {})===canonical(c.header.anchors),'source_anchor_mismatch');
  check(c.gates.length===c.pieces.length*3,'gate_list_mismatch');
}
async function verifyPiece(env,id,c,pid,data) {
  const db=await capturedDb(env),source=(await hydratedPiece(env,c.fragmentHashes,pid,db)).source;
  const out=await buildCandidate({source,db,shell:STUB,pieces:[pid],allVersions:c.allVersions,accepted:c.accepted,force:c.force,publicPieces:c.pieces,target:c.target});
  check(!out.blocked,'server_gate_or_hard_stop');
  const i=c.pieces.indexOf(pid);
  check(canonical(out.data.pieces[0])===canonical(c.selectedPieces[i]) && canonical(data.pieces[i])===canonical(c.selectedPieces[i]),'version_selection_mismatch');
  check(canonical(out.gates)===canonical(c.gates.filter(g=>g.piece===pid)) && canonical(out.versions[pid])===canonical(c.versions[pid]),'gate_or_version_audit_mismatch');
  check(canonical(out.shared)===canonical(c.shared.filter(g=>g.piece===pid)),'shared_scan_audit_mismatch');
  for(const [k,v]of Object.entries(out.data.sourceBindings || {}))check(canonical(data.sourceBindings?.[k])===canonical(v),'source_binding_mismatch');
}
async function verifyPage(env,id,c,pg,data) {
  const fragment=await trustedFragment(env,c,`pages/${pg}.json`),page=fragment.page;
  const owner=ownersOf(c),ids=page.B.flatMap((b,bi)=>b.L.map((_,li)=>`${pg}-${bi}-${li}`)),reviews={};
  for(let i=0;i<ids.length;i+=80) {
    const chunk=ids.slice(i,i+80),marks=chunk.map((_,n)=>'?'+(n+2)).join(',');
    const rows=await env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 AND id IN ('+marks+')').bind('reviews',...chunk).all();
    for(const row of rows.results)reviews[row.id]=JSON.parse(row.data);
  }
  const p=JSON.parse(JSON.stringify(page)),n=c.pageOrder.indexOf(pg);
  check(Array.isArray(p.a) && p.a.length===5 && c.header.atlas[n][0]===p.a[3] && c.header.atlas[n][1]===p.a[4],'atlas_geometry_mismatch');
  p.a=[n,0,0,p.a[3],p.a[4]];
  p.B.forEach((b,bi)=>{
    const own=owner.get(`${pg}/${bi}`);
    if(!own){b.L=[];for(const k of ['g','v','u','lineIds','transcriptionStatus','sourceAnchor'])delete b[k];return;}
    if(b.g)b.g=[own[0],own[2],...b.g.slice(2)];if('v' in b)b.v=own[1];
    b.L=b.L.map((text,li)=>{if(b.t===4)return text;const lid=`${pg}-${bi}-${li}`,r=reviews[lid],explicit=b.lineIds?.[li] || lid;if(r)check(r.original===text,'stale_transcript');return r?.status==='corrected' && typeof r.text==='string'?r.text:fragment.acceptedReadings?.[explicit] ?? text;});
  });
  p.u=[];p.x=(p.x || []).filter(e=>owner.has(`${pg}/${e[0]}`));
  check(canonical(data.pages[n])===canonical(p),'unapproved_output_page');
}
async function verifyShell(env,id,c) {
  let html=BLANK;
  if(c.pieces.length) {
    const raw=await staticText(env,'shell.html');check(await digest(raw)===c.shellSha256,'shell_pin_mismatch');
    const pages=Object.entries(c.pageBlockCounts).map(([id,n])=>({id,B:Array.from({length:n},()=>({}))}));
    html=filterMetadata(raw,c.metadata,pages,ownersOf(c));
  }
  const f=c.files.find(f=>f.path==='index.html'),bytes=encode(html);await checked(bytes,f);
  await immutable(env.PHOTOS,fileKey(id,f.path),bytes,{httpMetadata:{contentType:f.contentType},customMetadata:{sha256:f.sha256}});
}

export async function verifyAndMaterialize(env,user,body,c,p) {
  await assertFresh(env,c);
  if(['ready','copying','stored'].includes(p.value.phase))return json({ready:true,cursor:c.files.length,total:c.files.length});
  const jobs=[{kind:'header'},...c.pieces.map(id=>({kind:'piece',id})),...c.pageOrder.map(id=>({kind:'page',id})),{kind:'shell'}];
  if(p.value.phase==='verify') {
    const job=jobs[p.value.cursor];check(job,'invalid_validation_cursor');
    if(job.kind==='shell')await verifyShell(env,body.id,c);
    else {
      const data=await storedData(env,body.id,c);
      if(job.kind==='header')compareHeader(c,data);
      else if(job.kind==='piece')await verifyPiece(env,body.id,c,job.id,data);
      else await verifyPage(env,body.id,c,job.id,data);
    }
    const cursor=p.value.cursor+1;
    await setProgress(env,body.id,p,{phase:cursor===jobs.length?'materialize':'verify',cursor:cursor===jobs.length?0:cursor});
    return json({ready:false,phase:'verifying',cursor,total:jobs.length+c.files.length});
  }
  check(p.value.phase==='materialize','invalid_candidate_phase');
  const cursor=p.value.cursor,file=c.files[cursor];check(file,'invalid_copy_cursor');
  let bytes;
  if(!file.sourcePath)bytes=await bytesOf(await env.PHOTOS.get(fileKey(body.id,file.path)));
  else {
    if(/^photos\/(?:[a-f0-9]{32}|[a-f0-9]{64})$/.test(file.sourcePath))bytes=await bytesOf(await env.PHOTOS.get(file.sourcePath.slice(7)));
    else {const r=await env.ASSETS.fetch(new Request('https://studio.invalid/publish/assets/'+file.sourcePath));if(!r.ok)fail(409,'source_asset_missing');bytes=new Uint8Array(await r.arrayBuffer());}
  }
  await checked(bytes,file);
  await immutable(env.PHOTOS,fileKey(body.id,file.path),bytes,{httpMetadata:{contentType:file.contentType},customMetadata:{sha256:file.sha256}});
  const ready=cursor+1===c.files.length;
  await setProgress(env,body.id,p,{phase:ready?'ready':'materialize',cursor:ready?0:cursor+1});
  return json({ready,phase:'preparing',cursor:jobs.length+cursor+1,total:jobs.length+c.files.length});
}

export async function rollbackBrowser(env,user,body,c) {
  const {bucket,url}=target(env,body.target);check(c.target===body.target,'target_mismatch');
  check(await doc(env,'snapshot.'+body.id),'snapshot_not_confirmed');
  check(await wasPublished(env,body.id),'snapshot_not_confirmed');
  const source=await pin(env);check(source.sourceSha256===c.sourceHash,'source_changed_rebuild');
  const [rows,revs]=await env.DB.batch([env.DB.prepare('SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id').bind('release'),revisionStatement(env)]);
  const currentRevisions=revisionValues(revs.results);
  const release=Object.fromEntries(rows.results.map(r=>[r.id,JSON.parse(r.data)]));
  for(const pid of c.pieces)check(release[pid]?.pool==='series','own_pool_not_series');
  for(const pid of c.sourceDependencies || [])check(!['reserve','archive'].includes(release[pid]?.pool),'composite_source_pool_changed');
  // Only the recorded, already accepted shared scans are candidates for rollback.
  // A once-Series co-resident cannot silently become Reserve in an old scan.
  for(const pid of c.sharedPieceIds)check(release[pid]?.pool==='series','shared_scan_pool_changed');
  await recoverCurrent(env,bucket);const cur=await pointer(bucket);
  if(!body.job) {
    check(Object.hasOwn(body,'expectedCurrent') && canonical(body.expectedCurrent)===canonical(cur.value),'current_snapshot_changed');
    const m=await bucket.get(`snapshots/${body.id}/manifest.json`);check(m,'snapshot_missing');
    check(canonical(await m.json())===canonical(publicManifest(body.id,c)),'snapshot_manifest_mismatch');
    const job=await digest(crypto.randomUUID());
    await immutable(env.PHOTOS,`rollbacks/${job}/job.json`,JSON.stringify({snapshot:body.id,target:body.target,base:cur.value,owner:user.email,revisions:currentRevisions}));
    await immutable(env.PHOTOS,`rollbacks/${job}/state.json`,JSON.stringify({cursor:0,done:false}));
    return json({done:false,job,cursor:0,total:c.files.length});
  }
  check(ID.test(body.job),'invalid_rollback_job');
  const obj=await env.PHOTOS.get(`rollbacks/${body.job}/job.json`);check(obj,'rollback_job_missing');
  const job=await obj.json();check(job.owner===user.email && job.snapshot===body.id && job.target===body.target,'rollback_job_mismatch');
  const stateObj=await env.PHOTOS.get(`rollbacks/${body.job}/state.json`);check(stateObj,'rollback_state_missing');
  const state=await stateObj.json(),event='event.rollback.'+body.job;
  if(state.done)return json({done:true,job:body.job,id:body.id,url});
  if(cur.value?.event===event) {
    check(await recoverCurrent(env,bucket),'release_records_pending_retry');
    return json({done:true,job:body.job,id:body.id,url});
  }
  check(canonical(cur.value)===canonical(job.base),'current_snapshot_changed');
  check(canonical(currentRevisions)===canonical(job.revisions),'source_changed_rebuild');
  const manifest=publicManifest(body.id,c),file=manifest.files[state.cursor];check(file,'invalid_rollback_cursor');
  await checked(await bytesOf(await bucket.get(file.key)),file);
  const next={cursor:state.cursor+1,done:false};
  if(next.cursor===manifest.files.length) {
    await movePointer(env,user,{...c,base:job.base,revisions:job.revisions},body.id,bucket,'rollback',event);next.done=true;
  }
  const saved=await env.PHOTOS.put(`rollbacks/${body.job}/state.json`,JSON.stringify(next),condition(stateObj.etag));
  check(saved,'rollback_busy_retry');
  return json({done:next.done,job:body.job,id:body.id,url,cursor:next.cursor,total:c.files.length});
}

// Also exercised by the synthetic hosted CPU spike. These do not move pointers.
export {compareHeader,verifyPiece,verifyPage,verifyShell};
